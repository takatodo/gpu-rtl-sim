// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_clock_gating_sync.

module prim_clock_gating_sync_gpu_cov_tb (
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
  logic test_en_i;
  logic async_en_i;
  logic en_o;
  logic clk_o;
  logic [1:0] phase_w;
  logic requested_enable_w;
  logic effective_enable_w;
  logic last_async_en_q;
  logic last_en_q;
  logic last_clk_o_q;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] async_high_count_q;
  logic [31:0] async_low_count_q;
  logic [31:0] sync_high_count_q;
  logic [31:0] sync_low_count_q;
  logic [31:0] test_en_count_q;
  logic [31:0] test_override_count_q;
  logic [31:0] gated_high_count_q;
  logic [31:0] gated_low_count_q;
  logic [31:0] async_change_count_q;
  logic [31:0] sync_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] disabled_low_match_count_q;
  logic [31:0] match_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_enable_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_clock_gating_sync dut (
    .clk_i,
    .rst_ni,
    .test_en_i,
    .async_en_i,
    .en_o,
    .clk_o
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
  assign requested_enable_w = async_en_i || test_en_i;
  assign effective_enable_w = en_o || test_en_i;

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
      rand_q <= cfg_seed_i ^ 32'hc10c_5a7e;
      async_en_i <= 1'b0;
      test_en_i <= 1'b0;
      last_async_en_q <= 1'b0;
      last_en_q <= 1'b0;
      last_clk_o_q <= 1'b0;
      async_high_count_q <= 32'd0;
      async_low_count_q <= 32'd0;
      sync_high_count_q <= 32'd0;
      sync_low_count_q <= 32'd0;
      test_en_count_q <= 32'd0;
      test_override_count_q <= 32'd0;
      gated_high_count_q <= 32'd0;
      gated_low_count_q <= 32'd0;
      async_change_count_q <= 32'd0;
      sync_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      disabled_low_match_count_q <= 32'd0;
      match_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5a7e_c10c;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_enable_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i);
      last_async_en_q <= async_en_i;
      last_en_q <= en_o;
      last_clk_o_q <= clk_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        async_en_i <= pct_hit(rand_q ^ cfg_req_family_i ^ cfg_source_mask_i,
                              cfg_req_valid_pct_i + cfg_put_full_pct_i);
        test_en_i <= pct_hit({rand_q[15:0], rand_q[31:16]} ^
                             cfg_rsp_family_i ^ cfg_req_data_hi_xor_i,
                             cfg_rsp_valid_pct_i + cfg_put_partial_pct_i);
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        async_en_i <= cfg_rsp_delay_mode_i[0];
        test_en_i <= cfg_rsp_data_mode_i[0] && (drain_cycle_q[0] == 1'b0);
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[30:0], signature_q[31]} ^
                     rand_q ^ {27'd0, clk_o, en_o, test_en_i, async_en_i, rst_ni} ^
                     {30'd0, phase_w};

      if (async_en_i) begin
        async_high_count_q <= async_high_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        async_low_count_q <= async_low_count_q + 32'd1;
        if (async_high_count_q == 32'd0) begin
          pre_enable_cycles_q <= pre_enable_cycles_q + 32'd1;
        end
        seen_q[3] <= 1'b1;
      end
      if (en_o) begin
        sync_high_count_q <= sync_high_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        sync_low_count_q <= sync_low_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (test_en_i) begin
        test_en_count_q <= test_en_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (test_en_i && !en_o) begin
        test_override_count_q <= test_override_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (clk_o) begin
        gated_high_count_q <= gated_high_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end else begin
        gated_low_count_q <= gated_low_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (async_en_i != last_async_en_q) begin
        async_change_count_q <= async_change_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (en_o != last_en_q) begin
        sync_change_count_q <= sync_change_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (clk_o != last_clk_o_q) begin
        output_change_count_q <= output_change_count_q + 32'd1;
        seen_q[12] <= 1'b1;
      end
      if (!effective_enable_w && !clk_o) begin
        disabled_low_match_count_q <= disabled_low_match_count_q + 32'd1;
        seen_q[13] <= 1'b1;
      end
      match_count_q <= match_count_q + 32'd1;
      seen_q[14] <= 1'b1;
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'hc10c_5a7e;
  assign host_req_accepted_o = async_high_count_q;
  assign device_req_accepted_o = sync_high_count_q;
  assign device_rsp_accepted_o = gated_high_count_q;
  assign host_rsp_accepted_o = output_change_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    seen_q[14:0],
    async_en_i,
    en_o,
    test_en_i,
    clk_o,
    clk_i,
    rst_ni,
    done_o,
    phase_w,
    global_cycle_q[7:0]
  };
  assign toggle_bitmap_word1_o = {
    2'd0,
    requested_enable_w,
    effective_enable_w,
    last_en_q,
    last_clk_o_q,
    phase_w,
    global_cycle_q[7:0],
    async_high_count_q[7:0],
    sync_high_count_q[7:0]
  };
  assign toggle_bitmap_word2_o = {
    test_override_count_q[7:0],
    async_change_count_q[7:0],
    sync_change_count_q[7:0],
    output_change_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = async_high_count_q;
  assign real_toggle_subset_word1_o = async_low_count_q;
  assign real_toggle_subset_word2_o = sync_high_count_q;
  assign real_toggle_subset_word3_o = sync_low_count_q;
  assign real_toggle_subset_word4_o = test_en_count_q;
  assign real_toggle_subset_word5_o = test_override_count_q;
  assign real_toggle_subset_word6_o = gated_high_count_q;
  assign real_toggle_subset_word7_o = gated_low_count_q;
  assign real_toggle_subset_word8_o = async_change_count_q;
  assign real_toggle_subset_word9_o = sync_change_count_q;
  assign real_toggle_subset_word10_o = output_change_count_q;
  assign real_toggle_subset_word11_o = disabled_low_match_count_q;
  assign real_toggle_subset_word12_o = match_count_q;
  assign real_toggle_subset_word13_o = mismatch_count_q;
  assign real_toggle_subset_word14_o = traffic_cycle_q;
  assign real_toggle_subset_word15_o = drain_cycle_q;
  assign real_toggle_subset_word16_o = seen_q;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {29'd0, async_en_i, en_o, test_en_i};
  assign focused_wave_word1_o = {31'd0, clk_o};
  assign focused_wave_word2_o = async_high_count_q;
  assign focused_wave_word3_o = sync_high_count_q;
  assign focused_wave_word4_o = gated_high_count_q;
  assign focused_wave_word5_o = output_change_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = match_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = gated_high_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {17'd0, seen_q[14:0]};
  assign oracle_semantic_case_seen_o = {28'd0, clk_i, async_en_i, en_o, test_en_i};
  assign oracle_semantic_case_acked_o = {30'd0, clk_o, effective_enable_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_enable_cycles_q;
endmodule : prim_clock_gating_sync_gpu_cov_tb
