// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_rst_sync.

module prim_rst_sync_gpu_cov_tb (
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
  logic raw_rst_low_i;
  logic raw_rst_high_i;
  logic q_low_o;
  logic q_high_o;
  logic scan_rst_ni;
  prim_mubi_pkg::mubi4_t scanmode_i;
  logic reset_hit_w;
  logic [1:0] phase_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] reset_assert_count_q;
  logic [31:0] reset_release_count_q;
  logic [31:0] low_sync_release_count_q;
  logic [31:0] high_sync_release_count_q;
  logic [31:0] low_assert_hold_count_q;
  logic [31:0] high_assert_hold_count_q;
  logic [31:0] dual_polarity_match_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_release_cycles_q;
  logic last_raw_low_q;
  logic last_raw_high_q;
  logic last_q_low_q;
  logic last_q_high_q;
  logic assert_violation_q;
  logic polarity_violation_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_rst_sync #(
    .ActiveHigh(1'b0),
    .SkipScan(1'b1)
  ) dut_active_low (
    .clk_i,
    .d_i(raw_rst_low_i),
    .q_o(q_low_o),
    .scan_rst_ni,
    .scanmode_i
  );

  prim_rst_sync #(
    .ActiveHigh(1'b1),
    .SkipScan(1'b1)
  ) dut_active_high (
    .clk_i,
    .d_i(raw_rst_high_i),
    .q_o(q_high_o),
    .scan_rst_ni,
    .scanmode_i
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

  assign scan_rst_ni = 1'b1;
  assign scanmode_i = prim_mubi_pkg::MuBi4False;

  always_comb begin
    if (!cfg_valid_i || global_cycle_q < cfg_reset_cycles_i) begin
      phase_w = ResetPhase;
    end else if (traffic_cycle_q < cfg_batch_length_i) begin
      phase_w = TrafficPhase;
    end else if (drain_cycle_q < cfg_drain_cycles_i) begin
      phase_w = DrainPhase;
    end else begin
      phase_w = DonePhase;
    end
  end

  assign reset_hit_w = cfg_valid_i &&
                       phase_w == TrafficPhase &&
                       pct_hit(rand_q ^ cfg_seed_i ^ cfg_req_family_i,
                               cfg_req_valid_pct_i);

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= 32'd0;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= 32'd0;
      reset_assert_count_q <= 32'd0;
      reset_release_count_q <= 32'd0;
      low_sync_release_count_q <= 32'd0;
      high_sync_release_count_q <= 32'd0;
      low_assert_hold_count_q <= 32'd0;
      high_assert_hold_count_q <= 32'd0;
      dual_polarity_match_count_q <= 32'd0;
      signature_q <= 32'd0;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_release_cycles_q <= 32'd0;
      raw_rst_low_i <= 1'b0;
      raw_rst_high_i <= 1'b1;
      last_raw_low_q <= 1'b0;
      last_raw_high_q <= 1'b1;
      last_q_low_q <= 1'b0;
      last_q_high_q <= 1'b1;
      assert_violation_q <= 1'b0;
      polarity_violation_q <= 1'b0;
    end else begin
      last_raw_low_q <= raw_rst_low_i;
      last_raw_high_q <= raw_rst_high_i;
      last_q_low_q <= q_low_o;
      last_q_high_q <= q_high_o;

      if (phase_w != DonePhase) begin
        global_cycle_q <= global_cycle_q + 32'd1;
        rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i);
      end

      if (phase_w == ResetPhase) begin
        raw_rst_low_i <= 1'b0;
        raw_rst_high_i <= 1'b1;
        rand_q <= cfg_seed_i ^ 32'h5150_1234;
        signature_q <= cfg_seed_i ^ 32'h0bad_cafe;
        stalled_signature_q <= 32'd0;
        seen_q[0] <= 1'b1;
      end else if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        if (reset_hit_w) begin
          raw_rst_low_i <= 1'b0;
          raw_rst_high_i <= 1'b1;
          reset_assert_count_q <= reset_assert_count_q + 32'd1;
          signature_q <= {signature_q[30:0], signature_q[31]} ^
                         rand_q ^ cfg_address_mask_i ^ 32'h0000_00a5;
          seen_q[1] <= 1'b1;
        end else begin
          raw_rst_low_i <= 1'b1;
          raw_rst_high_i <= 1'b0;
          reset_release_count_q <= reset_release_count_q + 32'd1;
          if (reset_release_count_q == 32'd0) begin
            pre_release_cycles_q <= pre_release_cycles_q + 32'd1;
          end
          signature_q <= signature_q ^ rand_q ^ cfg_source_mask_i ^ 32'h0000_005a;
          seen_q[2] <= 1'b1;
        end
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        raw_rst_low_i <= 1'b1;
        raw_rst_high_i <= 1'b0;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[3] <= 1'b1;
      end

      if (q_low_o && !last_q_low_q) begin
        low_sync_release_count_q <= low_sync_release_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end
      if (!q_high_o && last_q_high_q) begin
        high_sync_release_count_q <= high_sync_release_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (!raw_rst_low_i && !q_low_o) begin
        low_assert_hold_count_q <= low_assert_hold_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (raw_rst_high_i && q_high_o) begin
        high_assert_hold_count_q <= high_assert_hold_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (q_low_o == !q_high_o) begin
        dual_polarity_match_count_q <= dual_polarity_match_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if ((!raw_rst_low_i && q_low_o) || (raw_rst_high_i && !q_high_o)) begin
        assert_violation_q <= 1'b1;
        seen_q[9] <= 1'b1;
      end
      if (raw_rst_low_i != raw_rst_high_i) begin
        seen_q[10] <= 1'b1;
      end
      if (last_raw_low_q != raw_rst_low_i || last_raw_high_q != raw_rst_high_i) begin
        seen_q[11] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_delay_mode_i;
  assign host_req_accepted_o = reset_assert_count_q;
  assign device_req_accepted_o = reset_release_count_q;
  assign device_rsp_accepted_o = low_sync_release_count_q;
  assign host_rsp_accepted_o = high_sync_release_count_q;
  assign rsp_queue_overflow_o = {30'd0, polarity_violation_q, assert_violation_q};
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    16'd0,
    seen_q[11:0],
    raw_rst_low_i,
    raw_rst_high_i,
    q_low_o,
    q_high_o
  };
  assign toggle_bitmap_word1_o = {
    12'd0,
    assert_violation_q,
    polarity_violation_q,
    4'd0,
    phase_w,
    global_cycle_q[7:0],
    raw_rst_low_i,
    raw_rst_high_i,
    q_low_o,
    q_high_o
  };
  assign toggle_bitmap_word2_o = {
    reset_assert_count_q[7:0],
    reset_release_count_q[7:0],
    low_sync_release_count_q[7:0],
    high_sync_release_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = {31'd0, raw_rst_low_i};
  assign real_toggle_subset_word1_o = {31'd0, raw_rst_high_i};
  assign real_toggle_subset_word2_o = {31'd0, q_low_o};
  assign real_toggle_subset_word3_o = {31'd0, q_high_o};
  assign real_toggle_subset_word4_o = reset_assert_count_q;
  assign real_toggle_subset_word5_o = reset_release_count_q;
  assign real_toggle_subset_word6_o = low_sync_release_count_q;
  assign real_toggle_subset_word7_o = high_sync_release_count_q;
  assign real_toggle_subset_word8_o = low_assert_hold_count_q;
  assign real_toggle_subset_word9_o = high_assert_hold_count_q;
  assign real_toggle_subset_word10_o = dual_polarity_match_count_q;
  assign real_toggle_subset_word11_o = traffic_cycle_q;
  assign real_toggle_subset_word12_o = drain_cycle_q;
  assign real_toggle_subset_word13_o = rand_q;
  assign real_toggle_subset_word14_o = signature_q;
  assign real_toggle_subset_word15_o = {20'd0, seen_q[11:0]};
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {30'd0, raw_rst_low_i, raw_rst_high_i};
  assign focused_wave_word1_o = {30'd0, q_low_o, q_high_o};
  assign focused_wave_word2_o = reset_assert_count_q;
  assign focused_wave_word3_o = reset_release_count_q;
  assign focused_wave_word4_o = low_sync_release_count_q ^ high_sync_release_count_q;
  assign focused_wave_word5_o = {30'd0, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = reset_release_count_q;
  assign oracle_expected_err_count_o = {30'd0, polarity_violation_q, assert_violation_q};
  assign oracle_observed_ok_count_o = low_sync_release_count_q + high_sync_release_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {20'd0, seen_q[11:0]};
  assign oracle_semantic_case_seen_o = {28'd0, raw_rst_low_i, raw_rst_high_i, q_low_o, q_high_o};
  assign oracle_semantic_case_acked_o = {
    28'd0,
    last_raw_low_q ^ raw_rst_low_i,
    last_raw_high_q ^ raw_rst_high_i,
    last_q_low_q ^ q_low_o,
    last_q_high_q ^ q_high_o
  };
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_release_cycles_q;
endmodule : prim_rst_sync_gpu_cov_tb
