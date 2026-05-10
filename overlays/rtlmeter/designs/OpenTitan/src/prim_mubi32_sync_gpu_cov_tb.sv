// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_mubi32_sync.

module prim_mubi32_sync_gpu_cov_tb (
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
  import prim_mubi_pkg::*;

  localparam int unsigned NumCopies = 2;
  localparam mubi32_t ResetValue = MuBi32False;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  mubi32_t mubi_i;
  mubi32_t [NumCopies-1:0] mubi_o;
  logic [31:0] mubi_raw_q;
  logic [31:0] last_mubi_raw_q;
  logic [31:0] expected_stage1_q;
  logic [31:0] expected_stage2_q;
  logic [31:0] last_expected_stage2_q;
  logic [31:0] last_output0_q;
  logic [31:0] last_output1_q;
  logic [1:0] phase_w;
  logic post_reset_seen_q;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] input_transition_count_q;
  logic [31:0] true_input_count_q;
  logic [31:0] false_input_count_q;
  logic [31:0] invalid_input_count_q;
  logic [31:0] output0_change_count_q;
  logic [31:0] output1_change_count_q;
  logic [31:0] output_follow_count_q;
  logic [31:0] output_mismatch_count_q;
  logic [31:0] copy_mismatch_count_q;
  logic [31:0] reset_value_seen_count_q;
  logic [31:0] pipeline_delay_seen_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_update_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign mubi_i = mubi32_t'(mubi_raw_q);

  prim_mubi32_sync #(
    .NumCopies(NumCopies),
    .AsyncOn(1'b1),
    .StabilityCheck(1'b0),
    .ResetValue(ResetValue)
  ) dut (
    .clk_i,
    .rst_ni,
    .mubi_i,
    .mubi_o
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

  function automatic logic [31:0] choose_mubi_raw(input logic [31:0] state);
    logic [31:0] candidate;
    if (pct_hit(state ^ cfg_req_family_i, cfg_req_valid_pct_i)) begin
      return MuBi32Width'(MuBi32True);
    end
    if (pct_hit(state ^ cfg_rsp_family_i, cfg_rsp_valid_pct_i)) begin
      return MuBi32Width'(MuBi32False);
    end
    candidate = state[31:0] ^ cfg_req_data_mode_i[31:0] ^ cfg_rsp_data_mode_i[31:0];
    if (candidate == MuBi32Width'(MuBi32True)) begin
      return 32'h3c3c_3c3c;
    end
    if (candidate == MuBi32Width'(MuBi32False)) begin
      return 32'hc3c3_c3c3;
    end
    return candidate;
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
      rand_q <= cfg_seed_i ^ 32'h32c5_5001;
      mubi_raw_q <= MuBi32Width'(ResetValue);
      last_mubi_raw_q <= MuBi32Width'(ResetValue);
      expected_stage1_q <= MuBi32Width'(ResetValue);
      expected_stage2_q <= MuBi32Width'(ResetValue);
      last_expected_stage2_q <= MuBi32Width'(ResetValue);
      last_output0_q <= MuBi32Width'(ResetValue);
      last_output1_q <= MuBi32Width'(ResetValue);
      post_reset_seen_q <= 1'b0;
      input_transition_count_q <= 32'd0;
      true_input_count_q <= 32'd0;
      false_input_count_q <= 32'd0;
      invalid_input_count_q <= 32'd0;
      output0_change_count_q <= 32'd0;
      output1_change_count_q <= 32'd0;
      output_follow_count_q <= 32'd0;
      output_mismatch_count_q <= 32'd0;
      copy_mismatch_count_q <= 32'd0;
      reset_value_seen_count_q <= 32'd0;
      pipeline_delay_seen_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h32c5_5eed;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_update_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i ^
                          cfg_address_mask_i ^ cfg_source_mask_i);
      last_mubi_raw_q <= mubi_raw_q;
      last_expected_stage2_q <= expected_stage2_q;
      last_output0_q <= MuBi32Width'(mubi_o[0]);
      last_output1_q <= MuBi32Width'(mubi_o[1]);
      expected_stage1_q <= mubi_raw_q;
      expected_stage2_q <= expected_stage1_q;
      post_reset_seen_q <= 1'b1;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        mubi_raw_q <= choose_mubi_raw(rand_q ^ traffic_cycle_q ^ cfg_req_fill_target_i);
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        mubi_raw_q <= (drain_cycle_q[0]) ? MuBi32Width'(MuBi32True) : MuBi32Width'(MuBi32False);
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q ^
                               cfg_rsp_delay_max_i ^ cfg_rsp_fill_target_i;
        seen_q[1] <= 1'b1;
      end

      if (mubi_raw_q != last_mubi_raw_q) begin
        input_transition_count_q <= input_transition_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        pre_update_cycles_q <= pre_update_cycles_q + 32'd1;
      end

      if (mubi_raw_q == MuBi32Width'(MuBi32True)) begin
        true_input_count_q <= true_input_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end else if (mubi_raw_q == MuBi32Width'(MuBi32False)) begin
        false_input_count_q <= false_input_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        invalid_input_count_q <= invalid_input_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end

      if (MuBi32Width'(mubi_o[0]) != last_output0_q) begin
        output0_change_count_q <= output0_change_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (MuBi32Width'(mubi_o[1]) != last_output1_q) begin
        output1_change_count_q <= output1_change_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (post_reset_seen_q && MuBi32Width'(mubi_o[0]) == expected_stage2_q &&
          MuBi32Width'(mubi_o[1]) == expected_stage2_q) begin
        output_follow_count_q <= output_follow_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (post_reset_seen_q && (MuBi32Width'(mubi_o[0]) != expected_stage2_q ||
                                MuBi32Width'(mubi_o[1]) != expected_stage2_q)) begin
        output_mismatch_count_q <= output_mismatch_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (MuBi32Width'(mubi_o[0]) != MuBi32Width'(mubi_o[1])) begin
        copy_mismatch_count_q <= copy_mismatch_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (MuBi32Width'(mubi_o[0]) == MuBi32Width'(ResetValue) &&
          MuBi32Width'(mubi_o[1]) == MuBi32Width'(ResetValue)) begin
        reset_value_seen_count_q <= reset_value_seen_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (post_reset_seen_q && expected_stage2_q != last_expected_stage2_q) begin
        pipeline_delay_seen_count_q <= pipeline_delay_seen_count_q + 32'd1;
        seen_q[12] <= 1'b1;
      end

      signature_q <= {signature_q[27:0], signature_q[31:28]} ^
                     mubi_raw_q ^ MuBi32Width'(mubi_o[0]) ^ MuBi32Width'(mubi_o[1]) ^
                     rand_q ^ cfg_req_data_hi_xor_i ^ cfg_rsp_data_hi_xor_i;
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q;
  assign progress_signature_o = signature_q ^ mubi_raw_q ^
                                MuBi32Width'(mubi_o[0]) ^ MuBi32Width'(mubi_o[1]);
  assign cfg_signature_o = progress_signature_o ^ cfg_seed_i ^ 32'h32c5_5eed;

  assign host_req_accepted_o = true_input_count_q;
  assign device_req_accepted_o = false_input_count_q;
  assign device_rsp_accepted_o = invalid_input_count_q;
  assign host_rsp_accepted_o = output_follow_count_q;
  assign rsp_queue_overflow_o = output_mismatch_count_q + copy_mismatch_count_q;

  assign real_toggle_subset_word0_o = input_transition_count_q;
  assign real_toggle_subset_word1_o = true_input_count_q;
  assign real_toggle_subset_word2_o = false_input_count_q;
  assign real_toggle_subset_word3_o = invalid_input_count_q;
  assign real_toggle_subset_word4_o = output0_change_count_q;
  assign real_toggle_subset_word5_o = output1_change_count_q;
  assign real_toggle_subset_word6_o = output_follow_count_q;
  assign real_toggle_subset_word7_o = output_mismatch_count_q;
  assign real_toggle_subset_word8_o = copy_mismatch_count_q;
  assign real_toggle_subset_word9_o = reset_value_seen_count_q;
  assign real_toggle_subset_word10_o = pipeline_delay_seen_count_q;
  assign real_toggle_subset_word11_o = progress_cycle_count_o;
  assign real_toggle_subset_word12_o = progress_signature_o;
  assign real_toggle_subset_word13_o = stalled_signature_q;
  assign real_toggle_subset_word14_o = mubi_raw_q ^ expected_stage2_q ^
                                       MuBi32Width'(mubi_o[0]);
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = {30'd0, done_o, rst_ni};
  assign real_toggle_subset_word17_o = output0_change_count_q + output1_change_count_q +
                                       output_follow_count_q;

  assign toggle_bitmap_word0_o = seen_q;
  assign toggle_bitmap_word1_o = {30'd0, phase_w} ^ mubi_raw_q ^
                                 expected_stage1_q ^ expected_stage2_q;
  assign toggle_bitmap_word2_o = MuBi32Width'(mubi_o[0]) ^ MuBi32Width'(mubi_o[1]) ^
                                 last_output0_q ^ last_output1_q;

  assign focused_wave_word0_o = mubi_raw_q;
  assign focused_wave_word1_o = expected_stage2_q;
  assign focused_wave_word2_o = MuBi32Width'(mubi_o[0]);
  assign focused_wave_word3_o = MuBi32Width'(mubi_o[1]);
  assign focused_wave_word4_o = signature_q;
  assign focused_wave_word5_o = stalled_signature_q;
  assign focused_wave_word6_o = {30'd0, done_o, rst_ni};
  assign focused_wave_word7_o = progress_cycle_count_o;

  assign oracle_expected_ok_count_o = progress_cycle_count_o - output_mismatch_count_q;
  assign oracle_expected_err_count_o = output_mismatch_count_q;
  assign oracle_observed_ok_count_o = output_follow_count_q;
  assign oracle_observed_err_count_o = copy_mismatch_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = expected_stage2_q;
  assign oracle_semantic_case_seen_o = mubi_raw_q;
  assign oracle_semantic_case_acked_o = MuBi32Width'(mubi_o[0]) ^ MuBi32Width'(mubi_o[1]);
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = output_mismatch_count_q + copy_mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_update_cycles_q;

endmodule : prim_mubi32_sync_gpu_cov_tb
