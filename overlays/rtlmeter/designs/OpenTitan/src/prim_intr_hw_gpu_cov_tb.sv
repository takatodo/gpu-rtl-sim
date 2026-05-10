// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_intr_hw.

module prim_intr_hw_gpu_cov_tb (
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
  logic event_intr_i;
  logic reg2hw_intr_enable_q_i;
  logic reg2hw_intr_test_q_i;
  logic reg2hw_intr_test_qe_i;
  logic reg2hw_intr_state_q_i;
  logic hw2reg_intr_state_de_o;
  logic hw2reg_intr_state_d_o;
  logic intr_o;
  logic phase_active_w;
  logic [1:0] phase_w;
  logic [31:0] case_mix_w;
  logic [2:0] case_w;
  logic next_event_w;
  logic next_test_w;
  logic next_test_qe_w;
  logic next_enable_w;
  logic sw_clear_w;
  logic expected_new_event_w;
  logic expected_de_w;
  logic expected_d_w;
  logic expected_intr_w;
  logic observed_match_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] event_count_q;
  logic [31:0] test_count_q;
  logic [31:0] de_count_q;
  logic [31:0] d_high_count_q;
  logic [31:0] intr_high_count_q;
  logic [31:0] enable_high_count_q;
  logic [31:0] clear_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] state_high_count_q;
  logic [31:0] state_low_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic expected_intr_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_intr_hw #(
    .Width(1),
    .FlopOutput(1'b1),
    .IntrT("Event")
  ) dut (
    .clk_i,
    .rst_ni,
    .event_intr_i(event_intr_i),
    .reg2hw_intr_enable_q_i(reg2hw_intr_enable_q_i),
    .reg2hw_intr_test_q_i(reg2hw_intr_test_q_i),
    .reg2hw_intr_test_qe_i(reg2hw_intr_test_qe_i),
    .reg2hw_intr_state_q_i(reg2hw_intr_state_q_i),
    .hw2reg_intr_state_de_o(hw2reg_intr_state_de_o),
    .hw2reg_intr_state_d_o(hw2reg_intr_state_d_o),
    .intr_o(intr_o)
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign case_mix_w = rand_q ^ traffic_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i;
  assign case_w = (phase_w == DrainPhase) ? drain_cycle_q[2:0] : case_mix_w[2:0];
  assign phase_active_w = (phase_w == TrafficPhase) || (phase_w == DrainPhase);
  assign expected_new_event_w = (reg2hw_intr_test_qe_i & reg2hw_intr_test_q_i) | event_intr_i;
  assign expected_de_w = expected_new_event_w;
  assign expected_d_w = expected_new_event_w | reg2hw_intr_state_q_i;
  assign expected_intr_w = expected_intr_q;
  assign observed_match_w = (hw2reg_intr_state_de_o == expected_de_w) &&
                            (hw2reg_intr_state_d_o == expected_d_w) &&
                            (intr_o == expected_intr_w);

  always_comb begin
    unique case (case_w)
      3'd0: begin
        next_event_w = 1'b1;
        next_test_w = 1'b0;
        next_test_qe_w = 1'b0;
        next_enable_w = 1'b1;
        sw_clear_w = 1'b0;
      end
      3'd1: begin
        next_event_w = 1'b0;
        next_test_w = 1'b1;
        next_test_qe_w = 1'b1;
        next_enable_w = 1'b1;
        sw_clear_w = 1'b0;
      end
      3'd2: begin
        next_event_w = 1'b0;
        next_test_w = 1'b0;
        next_test_qe_w = 1'b0;
        next_enable_w = 1'b0;
        sw_clear_w = 1'b0;
      end
      3'd3: begin
        next_event_w = 1'b0;
        next_test_w = 1'b0;
        next_test_qe_w = 1'b0;
        next_enable_w = 1'b1;
        sw_clear_w = 1'b1;
      end
      3'd4: begin
        next_event_w = rand_q[0];
        next_test_w = rand_q[1];
        next_test_qe_w = rand_q[2];
        next_enable_w = rand_q[3];
        sw_clear_w = rand_q[4];
      end
      default: begin
        next_event_w = traffic_cycle_q[0];
        next_test_w = traffic_cycle_q[1];
        next_test_qe_w = traffic_cycle_q[2];
        next_enable_w = ~traffic_cycle_q[3];
        sw_clear_w = traffic_cycle_q[4] & ~event_intr_i;
      end
    endcase
  end

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
      rand_q <= cfg_seed_i ^ 32'h1747_cafe;
      event_intr_i <= 1'b0;
      reg2hw_intr_enable_q_i <= 1'b0;
      reg2hw_intr_test_q_i <= 1'b0;
      reg2hw_intr_test_qe_i <= 1'b0;
      reg2hw_intr_state_q_i <= 1'b0;
      expected_intr_q <= 1'b0;
      event_count_q <= 32'd0;
      test_count_q <= 32'd0;
      de_count_q <= 32'd0;
      d_high_count_q <= 32'd0;
      intr_high_count_q <= 32'd0;
      enable_high_count_q <= 32'd0;
      clear_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      state_high_count_q <= 32'd0;
      state_low_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h1a71_1234;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_source_mask_i);
      expected_intr_q <= reg2hw_intr_state_q_i & reg2hw_intr_enable_q_i;

      if (phase_active_w) begin
        if (phase_w == TrafficPhase) begin
          traffic_cycle_q <= traffic_cycle_q + 32'd1;
        end else begin
          drain_cycle_q <= drain_cycle_q + 32'd1;
        end

        event_intr_i <= next_event_w;
        reg2hw_intr_test_q_i <= next_test_w;
        reg2hw_intr_test_qe_i <= next_test_qe_w;
        reg2hw_intr_enable_q_i <= next_enable_w;
        if (sw_clear_w) begin
          reg2hw_intr_state_q_i <= 1'b0;
        end else begin
          reg2hw_intr_state_q_i <= expected_d_w;
        end

        event_count_q <= event_count_q + {31'd0, event_intr_i};
        test_count_q <= test_count_q + {31'd0, reg2hw_intr_test_qe_i & reg2hw_intr_test_q_i};
        de_count_q <= de_count_q + {31'd0, hw2reg_intr_state_de_o};
        d_high_count_q <= d_high_count_q + {31'd0, hw2reg_intr_state_d_o};
        intr_high_count_q <= intr_high_count_q + {31'd0, intr_o};
        enable_high_count_q <= enable_high_count_q + {31'd0, reg2hw_intr_enable_q_i};
        clear_count_q <= clear_count_q + {31'd0, sw_clear_w};
        mismatch_count_q <= mismatch_count_q + {31'd0, ~observed_match_w};
        state_high_count_q <= state_high_count_q + {31'd0, reg2hw_intr_state_q_i};
        state_low_count_q <= state_low_count_q + {31'd0, ~reg2hw_intr_state_q_i};
        seen_q[0] <= 1'b1;
        seen_q[1] <= seen_q[1] | event_intr_i;
        seen_q[2] <= seen_q[2] | (reg2hw_intr_test_qe_i & reg2hw_intr_test_q_i);
        seen_q[3] <= seen_q[3] | hw2reg_intr_state_de_o;
        seen_q[4] <= seen_q[4] | hw2reg_intr_state_d_o;
        seen_q[5] <= seen_q[5] | intr_o;
        seen_q[6] <= seen_q[6] | sw_clear_w;
        seen_q[7] <= seen_q[7] | observed_match_w;
        signature_q <= {signature_q[30:0], signature_q[31]} ^
                       {29'd0, event_intr_i, hw2reg_intr_state_de_o, intr_o} ^
                       rand_q;
        stalled_signature_q <= stalled_signature_q ^
                               {27'd0, reg2hw_intr_state_q_i, reg2hw_intr_enable_q_i,
                                reg2hw_intr_test_qe_i, reg2hw_intr_test_q_i, event_intr_i};
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = signature_q ^ stalled_signature_q ^ 32'h1747_1a71;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q;
  assign progress_signature_o = signature_q;
  assign host_req_accepted_o = traffic_cycle_q;
  assign device_req_accepted_o = event_count_q + test_count_q;
  assign device_rsp_accepted_o = de_count_q + d_high_count_q;
  assign host_rsp_accepted_o = intr_high_count_q + enable_high_count_q;
  assign rsp_queue_overflow_o = 32'd0;

  assign real_toggle_subset_word0_o = event_count_q;
  assign real_toggle_subset_word1_o = test_count_q;
  assign real_toggle_subset_word2_o = de_count_q;
  assign real_toggle_subset_word3_o = d_high_count_q;
  assign real_toggle_subset_word4_o = intr_high_count_q;
  assign real_toggle_subset_word5_o = enable_high_count_q;
  assign real_toggle_subset_word6_o = clear_count_q;
  assign real_toggle_subset_word7_o = mismatch_count_q;
  assign real_toggle_subset_word8_o = state_high_count_q;
  assign real_toggle_subset_word9_o = state_low_count_q;
  assign real_toggle_subset_word10_o = traffic_cycle_q;
  assign real_toggle_subset_word11_o = drain_cycle_q;
  assign real_toggle_subset_word12_o = rand_q;
  assign real_toggle_subset_word13_o = signature_q;
  assign real_toggle_subset_word14_o = stalled_signature_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_batch_length_i ^ cfg_seed_i;
  assign real_toggle_subset_word17_o = {31'd0, done_o};

  assign toggle_bitmap_word0_o = {
    17'd0,
    observed_match_w,
    sw_clear_w,
    expected_intr_w,
    intr_o,
    hw2reg_intr_state_d_o,
    hw2reg_intr_state_de_o,
    reg2hw_intr_state_q_i,
    reg2hw_intr_enable_q_i,
    reg2hw_intr_test_qe_i,
    reg2hw_intr_test_q_i,
    event_intr_i,
    phase_w,
    rst_ni,
    cfg_valid_i
  };
  assign toggle_bitmap_word1_o = seen_q;
  assign toggle_bitmap_word2_o = signature_q ^ stalled_signature_q;

  assign focused_wave_word0_o = {27'd0, event_intr_i, reg2hw_intr_test_q_i,
                                 reg2hw_intr_test_qe_i, reg2hw_intr_state_q_i, intr_o};
  assign focused_wave_word1_o = {30'd0, hw2reg_intr_state_de_o, hw2reg_intr_state_d_o};
  assign focused_wave_word2_o = event_count_q;
  assign focused_wave_word3_o = test_count_q;
  assign focused_wave_word4_o = de_count_q;
  assign focused_wave_word5_o = intr_high_count_q;
  assign focused_wave_word6_o = mismatch_count_q;
  assign focused_wave_word7_o = signature_q;

  assign oracle_expected_ok_count_o = event_count_q + test_count_q;
  assign oracle_expected_err_count_o = 32'd0;
  assign oracle_observed_ok_count_o = de_count_q + intr_high_count_q;
  assign oracle_observed_err_count_o = mismatch_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {31'd0, observed_match_w};
  assign oracle_semantic_case_seen_o = {29'd0, case_w};
  assign oracle_semantic_case_acked_o = {31'd0, phase_active_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = 32'd0;
endmodule
