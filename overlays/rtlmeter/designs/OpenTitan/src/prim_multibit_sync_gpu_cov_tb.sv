// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_multibit_sync.

module prim_multibit_sync_gpu_cov_tb (
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
  localparam int unsigned Width = 8;
  localparam int unsigned NumChecks = 2;
  localparam logic [Width-1:0] ResetValue = 8'h3c;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [Width-1:0] d_i;
  logic [Width-1:0] q_o;
  logic [Width-1:0] d_q;
  logic [Width-1:0] last_d_q;
  logic [Width-1:0] last_q_q;
  logic [Width-1:0] expected_stage1_q;
  logic [Width-1:0] expected_stage2_q;
  logic [Width-1:0] last_expected_stage2_q;
  logic [Width-1:0] data_mask_w;
  logic [1:0] phase_w;
  logic post_reset_seen_q;
  logic q_mismatch_flag_q;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] data_toggle_count_q;
  logic [31:0] data_stable_count_q;
  logic [31:0] q_change_count_q;
  logic [31:0] q_follow_count_q;
  logic [31:0] q_mismatch_count_q;
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

  prim_multibit_sync #(
    .Width(Width),
    .NumChecks(NumChecks),
    .ResetValue(ResetValue)
  ) dut (
    .clk_i,
    .rst_ni,
    .data_i(d_i),
    .data_o(q_o)
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

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign d_i = d_q;

  always_comb begin
    data_mask_w[0] = pct_hit(rand_q ^ cfg_seed_i, cfg_req_valid_pct_i);
    data_mask_w[1] = pct_hit({rand_q[15:0], rand_q[31:16]} ^ cfg_req_data_mode_i,
                             cfg_rsp_valid_pct_i);
    data_mask_w[2] = pct_hit(rand_q ^ cfg_req_data_hi_xor_i ^ cfg_req_family_i,
                             cfg_host_d_ready_pct_i);
    data_mask_w[3] = pct_hit(~rand_q ^ cfg_rsp_family_i ^ cfg_rsp_data_mode_i,
                             cfg_device_a_ready_pct_i);
    data_mask_w[4] = pct_hit(rand_q ^ cfg_put_full_pct_i ^ cfg_address_base_i,
                             cfg_put_full_pct_i);
    data_mask_w[5] = pct_hit(~rand_q ^ cfg_put_partial_pct_i ^ cfg_address_mask_i,
                             cfg_put_partial_pct_i);
    data_mask_w[6] = pct_hit(rand_q ^ cfg_access_ack_data_pct_i ^ cfg_source_mask_i,
                             cfg_access_ack_data_pct_i);
    data_mask_w[7] = pct_hit(~rand_q ^ cfg_rsp_error_pct_i ^ cfg_rsp_delay_mode_i,
                             cfg_rsp_error_pct_i);
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
      rand_q <= cfg_seed_i ^ 32'h2c2c_5150;
      data_toggle_count_q <= 32'd0;
      data_stable_count_q <= 32'd0;
      q_change_count_q <= 32'd0;
      q_follow_count_q <= 32'd0;
      q_mismatch_count_q <= 32'd0;
      reset_value_seen_count_q <= 32'd0;
      pipeline_delay_seen_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5a5a_2c2c;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_update_cycles_q <= 32'd0;
      d_q <= ResetValue;
      last_d_q <= ResetValue;
      last_q_q <= ResetValue;
      expected_stage1_q <= ResetValue;
      expected_stage2_q <= ResetValue;
      last_expected_stage2_q <= ResetValue;
      post_reset_seen_q <= 1'b0;
      q_mismatch_flag_q <= 1'b0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i ^
                          cfg_req_fill_target_i ^ cfg_req_burst_len_max_i);
      last_d_q <= d_q;
      last_q_q <= q_o;
      last_expected_stage2_q <= expected_stage2_q;
      expected_stage1_q <= d_q;
      expected_stage2_q <= expected_stage1_q;
      post_reset_seen_q <= 1'b1;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        seen_q[8] <= 1'b1;
        if (data_mask_w != '0) begin
          d_q <= d_q ^ data_mask_w;
          data_toggle_count_q <= data_toggle_count_q + 32'd1;
          signature_q <= {signature_q[30:0], signature_q[31]} ^
                         {24'd0, data_mask_w} ^ rand_q ^ cfg_address_mask_i;
          seen_q[0] <= 1'b1;
        end else begin
          data_stable_count_q <= data_stable_count_q + 32'd1;
          pre_update_cycles_q <= pre_update_cycles_q + {31'd0, !post_reset_seen_q};
          seen_q[1] <= 1'b1;
        end
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        d_q <= (cfg_rsp_delay_mode_i[0]) ? ResetValue : ~ResetValue;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q ^
                               cfg_rsp_delay_max_i ^ cfg_rsp_fill_target_i;
        seen_q[9] <= 1'b1;
      end

      if (q_o != last_q_q) begin
        q_change_count_q <= q_change_count_q + 32'd1;
        signature_q <= signature_q ^ {16'd0, q_o, last_q_q};
        seen_q[2] <= 1'b1;
      end
      if (post_reset_seen_q && q_o == expected_stage2_q) begin
        q_follow_count_q <= q_follow_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (post_reset_seen_q && q_o != expected_stage2_q) begin
        q_mismatch_count_q <= q_mismatch_count_q + 32'd1;
        q_mismatch_flag_q <= 1'b1;
        seen_q[4] <= 1'b1;
      end
      if (q_o == ResetValue) begin
        reset_value_seen_count_q <= reset_value_seen_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (q_o != d_q) begin
        pipeline_delay_seen_count_q <= pipeline_delay_seen_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (q_o == last_q_q && post_reset_seen_q) begin
        seen_q[7] <= 1'b1;
      end
      if (post_reset_seen_q) begin
        seen_q[10] <= 1'b1;
      end
      if (traffic_cycle_q >= cfg_batch_length_i) begin
        seen_q[11] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i;
  assign host_req_accepted_o = data_toggle_count_q;
  assign device_req_accepted_o = data_stable_count_q;
  assign device_rsp_accepted_o = q_change_count_q;
  assign host_rsp_accepted_o = q_follow_count_q;
  assign rsp_queue_overflow_o = q_mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    4'd0,
    seen_q[11:0],
    data_mask_w,
    q_o
  };
  assign toggle_bitmap_word1_o = {
    4'd0,
    q_mismatch_flag_q,
    post_reset_seen_q,
    phase_w,
    global_cycle_q[7:0],
    expected_stage1_q,
    expected_stage2_q
  };
  assign toggle_bitmap_word2_o = {
    q_follow_count_q[7:0],
    q_mismatch_count_q[7:0],
    q_change_count_q[7:0],
    data_toggle_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = {24'd0, d_q};
  assign real_toggle_subset_word1_o = {24'd0, q_o};
  assign real_toggle_subset_word2_o = {24'd0, expected_stage1_q};
  assign real_toggle_subset_word3_o = {24'd0, expected_stage2_q};
  assign real_toggle_subset_word4_o = {24'd0, data_mask_w};
  assign real_toggle_subset_word5_o = data_toggle_count_q;
  assign real_toggle_subset_word6_o = data_stable_count_q;
  assign real_toggle_subset_word7_o = q_change_count_q;
  assign real_toggle_subset_word8_o = q_follow_count_q;
  assign real_toggle_subset_word9_o = q_mismatch_count_q;
  assign real_toggle_subset_word10_o = reset_value_seen_count_q;
  assign real_toggle_subset_word11_o = pipeline_delay_seen_count_q;
  assign real_toggle_subset_word12_o = traffic_cycle_q;
  assign real_toggle_subset_word13_o = drain_cycle_q;
  assign real_toggle_subset_word14_o = rand_q;
  assign real_toggle_subset_word15_o = {20'd0, seen_q[11:0]};
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {24'd0, d_q};
  assign focused_wave_word1_o = {24'd0, q_o};
  assign focused_wave_word2_o = {24'd0, expected_stage1_q};
  assign focused_wave_word3_o = {24'd0, expected_stage2_q};
  assign focused_wave_word4_o = q_follow_count_q ^ q_mismatch_count_q;
  assign focused_wave_word5_o = {30'd0, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = q_follow_count_q;
  assign oracle_expected_err_count_o = q_mismatch_count_q;
  assign oracle_observed_ok_count_o = q_change_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {20'd0, seen_q[11:0]};
  assign oracle_semantic_case_seen_o = {16'd0, d_q, q_o};
  assign oracle_semantic_case_acked_o = {16'd0, expected_stage1_q, expected_stage2_q};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_update_cycles_q;
endmodule : prim_multibit_sync_gpu_cov_tb
