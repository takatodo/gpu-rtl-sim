// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_lc_or_hardened.

module prim_lc_or_hardened_gpu_cov_tb (
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
  import lc_ctrl_pkg::*;

  localparam int unsigned LcTxWidth = lc_ctrl_pkg::TxWidth;
  localparam logic [LcTxWidth-1:0] LcOnRaw = lc_ctrl_pkg::On;
  localparam logic [LcTxWidth-1:0] LcOffRaw = lc_ctrl_pkg::Off;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  lc_tx_t lc_en_a_i;
  lc_tx_t lc_en_b_i;
  lc_tx_t lc_en_o;
  logic [LcTxWidth-1:0] lc_a_raw_q;
  logic [LcTxWidth-1:0] lc_b_raw_q;
  logic [LcTxWidth-1:0] last_lc_a_raw_q;
  logic [LcTxWidth-1:0] last_lc_b_raw_q;
  logic [LcTxWidth-1:0] expected_output_w;
  logic [LcTxWidth-1:0] output_w;
  logic [LcTxWidth-1:0] last_output_q;
  logic [1:0] phase_w;
  logic post_reset_seen_q;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] input_transition_count_q;
  logic [31:0] a_on_count_q;
  logic [31:0] b_on_count_q;
  logic [31:0] both_off_count_q;
  logic [31:0] invalid_pair_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] output_expected_count_q;
  logic [31:0] output_mismatch_count_q;
  logic [31:0] act_output_count_q;
  logic [31:0] inv_output_count_q;
  logic [31:0] no_flop_follow_count_q;
  logic [31:0] branch_guard_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_update_cycles_q;

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign lc_en_a_i = lc_tx_t'(lc_a_raw_q);
  assign lc_en_b_i = lc_tx_t'(lc_b_raw_q);
  assign output_w = LcTxWidth'(lc_en_o);
  assign expected_output_w = expected_or_raw(lc_a_raw_q, lc_b_raw_q);

  prim_lc_or_hardened #(
    .ActVal(lc_ctrl_pkg::On)
  ) dut (
    .clk_i,
    .rst_ni,
    .lc_en_a_i,
    .lc_en_b_i,
    .lc_en_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [31:0] clamp_pct(input logic [31:0] pct_raw);
    return (pct_raw > 32'd100) ? 32'd100 : pct_raw;
  endfunction

  function automatic logic pct_hit(input logic [31:0] state, input logic [31:0] pct_raw);
    return ((state % 32'd100) < clamp_pct(pct_raw));
  endfunction

  function automatic logic [LcTxWidth-1:0] choose_lc_raw(input logic [31:0] state);
    logic [LcTxWidth-1:0] candidate;
    if (pct_hit(state ^ cfg_req_family_i, cfg_req_valid_pct_i)) begin
      return LcOnRaw;
    end
    if (pct_hit(state ^ cfg_rsp_family_i, cfg_rsp_valid_pct_i)) begin
      return LcOffRaw;
    end
    candidate = state[LcTxWidth-1:0] ^ cfg_req_data_mode_i[LcTxWidth-1:0] ^
                cfg_rsp_data_mode_i[LcTxWidth-1:0];
    if (candidate == LcOnRaw) begin
      return 4'h3;
    end
    if (candidate == LcOffRaw) begin
      return 4'hc;
    end
    return candidate;
  endfunction

  function automatic logic [LcTxWidth-1:0] expected_or_raw(
    input logic [LcTxWidth-1:0] a_raw,
    input logic [LcTxWidth-1:0] b_raw
  );
    if (a_raw == LcOnRaw || b_raw == LcOnRaw) begin
      return LcOnRaw;
    end
    return LcOffRaw;
  endfunction

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
      rand_q <= cfg_seed_i ^ 32'h1c0a_5001;
      lc_a_raw_q <= LcOffRaw;
      lc_b_raw_q <= LcOffRaw;
      last_lc_a_raw_q <= LcOffRaw;
      last_lc_b_raw_q <= LcOffRaw;
      last_output_q <= LcOffRaw;
      post_reset_seen_q <= 1'b0;
      input_transition_count_q <= 32'd0;
      a_on_count_q <= 32'd0;
      b_on_count_q <= 32'd0;
      both_off_count_q <= 32'd0;
      invalid_pair_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      output_expected_count_q <= 32'd0;
      output_mismatch_count_q <= 32'd0;
      act_output_count_q <= 32'd0;
      inv_output_count_q <= 32'd0;
      no_flop_follow_count_q <= 32'd0;
      branch_guard_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h1c0a_5eed;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_update_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i ^
                          cfg_address_mask_i ^ cfg_source_mask_i);
      last_lc_a_raw_q <= lc_a_raw_q;
      last_lc_b_raw_q <= lc_b_raw_q;
      last_output_q <= output_w;
      post_reset_seen_q <= 1'b1;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        lc_a_raw_q <= choose_lc_raw(rand_q ^ traffic_cycle_q ^ cfg_req_fill_target_i);
        lc_b_raw_q <= choose_lc_raw({rand_q[15:0], rand_q[31:16]} ^
                                    cfg_rsp_fill_target_i ^ traffic_cycle_q);
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        lc_a_raw_q <= (drain_cycle_q[0]) ? LcOnRaw : LcOffRaw;
        lc_b_raw_q <= (drain_cycle_q[1]) ? LcOnRaw : LcOffRaw;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q ^
                               cfg_rsp_delay_max_i ^ cfg_rsp_fill_target_i;
        seen_q[1] <= 1'b1;
      end

      if (lc_a_raw_q != last_lc_a_raw_q || lc_b_raw_q != last_lc_b_raw_q) begin
        input_transition_count_q <= input_transition_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        pre_update_cycles_q <= pre_update_cycles_q + 32'd1;
      end

      if (lc_a_raw_q == LcOnRaw) begin
        a_on_count_q <= a_on_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (lc_b_raw_q == LcOnRaw) begin
        b_on_count_q <= b_on_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end
      if (lc_a_raw_q == LcOffRaw && lc_b_raw_q == LcOffRaw) begin
        both_off_count_q <= both_off_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if ((lc_a_raw_q != LcOnRaw && lc_a_raw_q != LcOffRaw) ||
          (lc_b_raw_q != LcOnRaw && lc_b_raw_q != LcOffRaw)) begin
        invalid_pair_count_q <= invalid_pair_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end

      if (output_w != last_output_q) begin
        output_change_count_q <= output_change_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (post_reset_seen_q && output_w == expected_output_w) begin
        output_expected_count_q <= output_expected_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (post_reset_seen_q && output_w != expected_output_w) begin
        output_mismatch_count_q <= output_mismatch_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (output_w == LcOnRaw) begin
        act_output_count_q <= act_output_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (output_w == LcOffRaw) begin
        inv_output_count_q <= inv_output_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (post_reset_seen_q &&
          (lc_a_raw_q != last_lc_a_raw_q || lc_b_raw_q != last_lc_b_raw_q) &&
          output_w == expected_output_w) begin
        no_flop_follow_count_q <= no_flop_follow_count_q + 32'd1;
        seen_q[12] <= 1'b1;
      end

      branch_guard_count_q <= branch_guard_count_q +
                              {31'd0, cfg_host_d_ready_pct_i[0] ^ cfg_device_a_ready_pct_i[0] ^
                                      cfg_put_full_pct_i[0] ^ cfg_put_partial_pct_i[0] ^
                                      cfg_req_burst_len_max_i[0] ^ cfg_req_address_mode_i[0] ^
                                      cfg_access_ack_data_pct_i[0] ^ cfg_rsp_error_pct_i[0] ^
                                      cfg_rsp_delay_mode_i[0]};

      signature_q <= {signature_q[27:0], signature_q[31:28]} ^
                     {20'd0, lc_a_raw_q, lc_b_raw_q, output_w} ^
                     rand_q ^ cfg_req_data_hi_xor_i ^ cfg_rsp_data_hi_xor_i;
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q;
  assign progress_signature_o = signature_q ^ {20'd0, lc_a_raw_q, lc_b_raw_q, output_w};
  assign cfg_signature_o = progress_signature_o ^ cfg_seed_i ^ 32'h1c0a_5eed;

  assign host_req_accepted_o = a_on_count_q;
  assign device_req_accepted_o = b_on_count_q;
  assign device_rsp_accepted_o = invalid_pair_count_q;
  assign host_rsp_accepted_o = output_expected_count_q;
  assign rsp_queue_overflow_o = output_mismatch_count_q;

  assign real_toggle_subset_word0_o = input_transition_count_q;
  assign real_toggle_subset_word1_o = a_on_count_q;
  assign real_toggle_subset_word2_o = b_on_count_q;
  assign real_toggle_subset_word3_o = both_off_count_q;
  assign real_toggle_subset_word4_o = invalid_pair_count_q;
  assign real_toggle_subset_word5_o = output_change_count_q;
  assign real_toggle_subset_word6_o = output_expected_count_q;
  assign real_toggle_subset_word7_o = output_mismatch_count_q;
  assign real_toggle_subset_word8_o = act_output_count_q;
  assign real_toggle_subset_word9_o = inv_output_count_q;
  assign real_toggle_subset_word10_o = no_flop_follow_count_q;
  assign real_toggle_subset_word11_o = progress_cycle_count_o;
  assign real_toggle_subset_word12_o = progress_signature_o;
  assign real_toggle_subset_word13_o = stalled_signature_q ^ branch_guard_count_q;
  assign real_toggle_subset_word14_o = {16'd0, lc_a_raw_q, lc_b_raw_q, output_w, expected_output_w};
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = {28'd0, phase_w, done_o, rst_ni};
  assign real_toggle_subset_word17_o = pre_update_cycles_q + output_mismatch_count_q;

  assign toggle_bitmap_word0_o = seen_q;
  assign toggle_bitmap_word1_o = {
    14'd0,
    phase_w,
    lc_a_raw_q,
    lc_b_raw_q,
    output_w,
    expected_output_w
  };
  assign toggle_bitmap_word2_o = {
    18'd0,
    last_lc_a_raw_q,
    last_lc_b_raw_q,
    last_output_q,
    done_o,
    rst_ni
  };

  assign focused_wave_word0_o = {28'd0, lc_a_raw_q};
  assign focused_wave_word1_o = {28'd0, lc_b_raw_q};
  assign focused_wave_word2_o = {28'd0, expected_output_w};
  assign focused_wave_word3_o = {28'd0, output_w};
  assign focused_wave_word4_o = signature_q;
  assign focused_wave_word5_o = stalled_signature_q;
  assign focused_wave_word6_o = {30'd0, done_o, rst_ni};
  assign focused_wave_word7_o = progress_cycle_count_o;

  assign oracle_expected_ok_count_o = progress_cycle_count_o - output_mismatch_count_q;
  assign oracle_expected_err_count_o = output_mismatch_count_q;
  assign oracle_observed_ok_count_o = output_expected_count_q;
  assign oracle_observed_err_count_o = invalid_pair_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {28'd0, expected_output_w};
  assign oracle_semantic_case_seen_o = {24'd0, lc_a_raw_q, lc_b_raw_q};
  assign oracle_semantic_case_acked_o = {28'd0, output_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = output_mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_update_cycles_q;

endmodule : prim_lc_or_hardened_gpu_cov_tb
