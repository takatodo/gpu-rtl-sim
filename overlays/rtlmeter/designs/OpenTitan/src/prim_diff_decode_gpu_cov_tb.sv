// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_diff_decode.

module prim_diff_decode_gpu_cov_tb (
  input  logic        cfg_valid_i,
  input  logic [31:0] cfg_batch_length_i,
  input  logic [31:0] cfg_req_valid_pct_i,
  input  logic [31:0] cfg_rsp_valid_pct_i,
  input  logic [31:0] cfg_host_d_ready_pct_i,
  input  logic [31:0] cfg_device_a_ready_pct_i,
  input  logic [31:0] cfg_put_full_pct_i,
  input  logic [31:0] cfg_put_partial_pct_i,
  input  logic [31:0] cfg_req_fill_target_i,
  input  logic [31:0] cfg_req_burst_len_max_i,
  input  logic [31:0] cfg_req_family_i,
  input  logic [31:0] cfg_req_address_mode_i,
  input  logic [31:0] cfg_req_data_mode_i,
  input  logic [31:0] cfg_req_data_hi_xor_i,
  input  logic [31:0] cfg_access_ack_data_pct_i,
  input  logic [31:0] cfg_rsp_error_pct_i,
  input  logic [31:0] cfg_rsp_fill_target_i,
  input  logic [31:0] cfg_rsp_delay_max_i,
  input  logic [31:0] cfg_rsp_family_i,
  input  logic [31:0] cfg_rsp_delay_mode_i,
  input  logic [31:0] cfg_rsp_data_mode_i,
  input  logic [31:0] cfg_rsp_data_hi_xor_i,
  input  logic [31:0] cfg_reset_cycles_i,
  input  logic [31:0] cfg_drain_cycles_i,
  input  logic [31:0] cfg_seed_i,
  input  logic [31:0] cfg_address_base_i,
  input  logic [31:0] cfg_address_mask_i,
  input  logic [31:0] cfg_source_mask_i,
  output logic [31:0] cfg_signature_o,
  output logic        done_o,
  output logic [31:0] host_req_accepted_o,
  output logic [31:0] device_req_accepted_o,
  output logic [31:0] device_rsp_accepted_o,
  output logic [31:0] host_rsp_accepted_o,
  output logic [31:0] rsp_queue_overflow_o,
  output logic [31:0] progress_cycle_count_o,
  output logic [31:0] progress_signature_o,
  output logic [31:0] toggle_bitmap_word0_o,
  output logic [31:0] toggle_bitmap_word1_o,
  output logic [31:0] toggle_bitmap_word2_o,
  output logic [31:0] real_toggle_subset_word0_o,
  output logic [31:0] real_toggle_subset_word1_o,
  output logic [31:0] real_toggle_subset_word2_o,
  output logic [31:0] real_toggle_subset_word3_o,
  output logic [31:0] real_toggle_subset_word4_o,
  output logic [31:0] real_toggle_subset_word5_o,
  output logic [31:0] real_toggle_subset_word6_o,
  output logic [31:0] real_toggle_subset_word7_o,
  output logic [31:0] real_toggle_subset_word8_o,
  output logic [31:0] real_toggle_subset_word9_o,
  output logic [31:0] real_toggle_subset_word10_o,
  output logic [31:0] real_toggle_subset_word11_o,
  output logic [31:0] real_toggle_subset_word12_o,
  output logic [31:0] real_toggle_subset_word13_o,
  output logic [31:0] real_toggle_subset_word14_o,
  output logic [31:0] real_toggle_subset_word15_o,
  output logic [31:0] real_toggle_subset_word16_o,
  output logic [31:0] real_toggle_subset_word17_o,
  output logic [31:0] focused_wave_word0_o,
  output logic [31:0] focused_wave_word1_o,
  output logic [31:0] focused_wave_word2_o,
  output logic [31:0] focused_wave_word3_o,
  output logic [31:0] focused_wave_word4_o,
  output logic [31:0] focused_wave_word5_o,
  output logic [31:0] focused_wave_word6_o,
  output logic [31:0] focused_wave_word7_o,
  output logic [31:0] oracle_expected_ok_count_o,
  output logic [31:0] oracle_expected_err_count_o,
  output logic [31:0] oracle_observed_ok_count_o,
  output logic [31:0] oracle_observed_err_count_o,
  output logic [31:0] oracle_semantic_family_seen_o,
  output logic [31:0] oracle_semantic_family_acked_o,
  output logic [31:0] oracle_semantic_case_seen_o,
  output logic [31:0] oracle_semantic_case_acked_o,
  output logic [31:0] oracle_req_signature_o,
  output logic [31:0] oracle_stalled_req_signature_o,
  output logic [31:0] oracle_req_signature_delta_o,
  output logic [31:0] oracle_req_stable_violation_o,
  output logic [31:0] oracle_pre_handshake_traffic_cycles_o
);
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic diff_pi;
  logic diff_ni;
  logic level_o;
  logic rise_o;
  logic fall_o;
  logic event_o;
  logic sigint_o;
  logic expected_level_w;
  logic expected_rise_w;
  logic expected_fall_w;
  logic expected_event_w;
  logic expected_sigint_w;
  logic observed_match_w;
  logic next_diff_p_w;
  logic next_diff_n_w;
  logic [1:0] phase_w;
  logic [31:0] case_mix_w;
  logic [2:0] case_w;
  logic [2:0] next_case_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] legal_level_count_q;
  logic [31:0] sigint_count_q;
  logic [31:0] rise_count_q;
  logic [31:0] fall_count_q;
  logic [31:0] event_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] level_high_count_q;
  logic [31:0] level_low_count_q;
  logic [31:0] legal_pair_count_q;
  logic [31:0] illegal_pair_count_q;
  logic [31:0] transition_case_count_q;
  logic [31:0] stable_case_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_sigint_cycles_q;
  logic expected_diff_pq;
  logic expected_level_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_diff_decode #(
    .AsyncOn(1'b0)
  ) dut (
    .clk_i,
    .rst_ni,
    .diff_pi,
    .diff_ni,
    .level_o,
    .rise_o,
    .fall_o,
    .event_o,
    .sigint_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  always_comb begin
    unique case (next_case_w)
      3'd0: begin
        next_diff_p_w = 1'b0;
        next_diff_n_w = 1'b1;
      end
      3'd1: begin
        next_diff_p_w = 1'b1;
        next_diff_n_w = 1'b0;
      end
      3'd2: begin
        next_diff_p_w = 1'b0;
        next_diff_n_w = 1'b0;
      end
      3'd3: begin
        next_diff_p_w = 1'b1;
        next_diff_n_w = 1'b1;
      end
      3'd4: begin
        next_diff_p_w = ~diff_pi;
        next_diff_n_w = diff_pi;
      end
      3'd5: begin
        next_diff_p_w = diff_pi;
        next_diff_n_w = diff_ni;
      end
      default: begin
        next_diff_p_w = rand_q[0];
        next_diff_n_w = rand_q[1];
      end
    endcase
  end

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign case_mix_w = rand_q ^ traffic_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i;
  assign case_w = case_mix_w[2:0];
  assign next_case_w = (phase_w == DrainPhase) ? drain_cycle_q[2:0] : case_w;
  assign expected_sigint_w = ~(diff_pi ^ diff_ni);
  assign expected_level_w = expected_sigint_w ? expected_level_q : diff_pi;
  assign expected_rise_w = (~expected_diff_pq & diff_pi) & ~expected_sigint_w;
  assign expected_fall_w = (expected_diff_pq & ~diff_pi) & ~expected_sigint_w;
  assign expected_event_w = expected_rise_w | expected_fall_w;
  assign observed_match_w = (level_o == expected_level_w) &&
                            (rise_o == expected_rise_w) &&
                            (fall_o == expected_fall_w) &&
                            (event_o == expected_event_w) &&
                            (sigint_o == expected_sigint_w);

  always_comb begin
    if (!cfg_valid_i || !rst_ni) begin
      phase_w = ResetPhase;
    end else if (traffic_cycle_q < cfg_batch_length_i) begin
      phase_w = TrafficPhase;
    end else if (drain_cycle_q < cfg_drain_cycles_i) begin
      phase_w = DrainPhase;
    end else begin
      phase_w = DonePhase;
    end
  end

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      global_cycle_q <= global_cycle_q + 32'd1;
    end

    if (!rst_ni) begin
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'hd1ff_dec0;
      diff_pi <= 1'b0;
      diff_ni <= 1'b1;
      expected_diff_pq <= 1'b0;
      expected_level_q <= 1'b0;
      legal_level_count_q <= 32'd0;
      sigint_count_q <= 32'd0;
      rise_count_q <= 32'd0;
      fall_count_q <= 32'd0;
      event_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      level_high_count_q <= 32'd0;
      level_low_count_q <= 32'd0;
      legal_pair_count_q <= 32'd0;
      illegal_pair_count_q <= 32'd0;
      transition_case_count_q <= 32'd0;
      stable_case_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'hc0de_d1ff;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_sigint_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_source_mask_i);

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        diff_pi <= next_diff_p_w;
        diff_ni <= next_diff_n_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        diff_pi <= next_diff_p_w;
        diff_ni <= next_diff_n_w;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      expected_diff_pq <= diff_pi;
      expected_level_q <= expected_level_w;
      signature_q <= {signature_q[26:0], signature_q[31:27]} ^
                     {24'd0, case_w, diff_pi, diff_ni, level_o, rise_o, fall_o} ^
                     {27'd0, event_o, sigint_o, expected_event_w, expected_sigint_w, rst_ni} ^
                     rand_q;

      if (!expected_sigint_w) begin
        legal_level_count_q <= legal_level_count_q + 32'd1;
        legal_pair_count_q <= legal_pair_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        sigint_count_q <= sigint_count_q + 32'd1;
        illegal_pair_count_q <= illegal_pair_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (rise_o) begin
        rise_count_q <= rise_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end
      if (fall_o) begin
        fall_count_q <= fall_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (event_o) begin
        event_count_q <= event_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (!observed_match_w) begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (level_o) begin
        level_high_count_q <= level_high_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end else begin
        level_low_count_q <= level_low_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (expected_rise_w || expected_fall_w) begin
        transition_case_count_q <= transition_case_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end else begin
        stable_case_count_q <= stable_case_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (sigint_count_q == 32'd0 && !expected_sigint_w) begin
        pre_sigint_cycles_q <= pre_sigint_cycles_q + 32'd1;
      end
      if (next_case_w == 3'd6) begin
        seen_q[12] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'hd1ff_0ace;
  assign host_req_accepted_o = legal_level_count_q;
  assign device_req_accepted_o = sigint_count_q;
  assign device_rsp_accepted_o = rise_count_q + fall_count_q;
  assign host_rsp_accepted_o = event_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    7'd0,
    seen_q[11:0],
    diff_pi,
    diff_ni,
    level_o,
    rise_o,
    fall_o,
    event_o,
    sigint_o,
    rst_ni,
    done_o,
    phase_w,
    cfg_valid_i,
    global_cycle_q[0]
  };
  assign toggle_bitmap_word1_o = {
    4'd0,
    seen_q[27:12],
    case_w,
    next_case_w,
    expected_level_w,
    expected_rise_w,
    expected_fall_w,
    expected_event_w,
    expected_sigint_w,
    observed_match_w
  };
  assign toggle_bitmap_word2_o = {
    legal_level_count_q[7:0],
    sigint_count_q[7:0],
    rise_count_q[7:0],
    fall_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = legal_level_count_q;
  assign real_toggle_subset_word1_o = sigint_count_q;
  assign real_toggle_subset_word2_o = rise_count_q;
  assign real_toggle_subset_word3_o = fall_count_q;
  assign real_toggle_subset_word4_o = event_count_q;
  assign real_toggle_subset_word5_o = mismatch_count_q;
  assign real_toggle_subset_word6_o = level_high_count_q;
  assign real_toggle_subset_word7_o = level_low_count_q;
  assign real_toggle_subset_word8_o = legal_pair_count_q;
  assign real_toggle_subset_word9_o = illegal_pair_count_q;
  assign real_toggle_subset_word10_o = transition_case_count_q;
  assign real_toggle_subset_word11_o = stable_case_count_q;
  assign real_toggle_subset_word12_o = traffic_cycle_q;
  assign real_toggle_subset_word13_o = drain_cycle_q;
  assign real_toggle_subset_word14_o = rand_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {24'd0, case_w, diff_pi, diff_ni, level_o, rise_o, fall_o};
  assign focused_wave_word1_o = {27'd0, event_o, sigint_o, expected_event_w,
                                 expected_sigint_w, observed_match_w};
  assign focused_wave_word2_o = {27'd0, expected_level_w, expected_rise_w,
                                 expected_fall_w, expected_event_w, expected_sigint_w};
  assign focused_wave_word3_o = legal_level_count_q ^ sigint_count_q;
  assign focused_wave_word4_o = rise_count_q ^ fall_count_q ^ event_count_q;
  assign focused_wave_word5_o = legal_pair_count_q ^ illegal_pair_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = legal_level_count_q;
  assign oracle_expected_err_count_o = sigint_count_q;
  assign oracle_observed_ok_count_o = rise_count_q + fall_count_q;
  assign oracle_observed_err_count_o = mismatch_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    legal_pair_count_q[7:0],
    illegal_pair_count_q[7:0],
    transition_case_count_q[7:0],
    stable_case_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {24'd0, case_w, next_case_w, diff_pi, diff_ni};
  assign oracle_semantic_case_acked_o = {27'd0, event_o, sigint_o, expected_event_w,
                                         expected_sigint_w, observed_match_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_sigint_cycles_q;
endmodule : prim_diff_decode_gpu_cov_tb
