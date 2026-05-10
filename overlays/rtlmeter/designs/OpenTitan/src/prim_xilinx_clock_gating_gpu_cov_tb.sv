// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_xilinx_clock_gating.

module prim_xilinx_clock_gating_gpu_cov_tb (
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
  logic en_i;
  logic test_en_i;
  logic clk_o;
  logic [1:0] phase_w;
  logic enable_request_w;
  logic latched_enable_seen_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] en_high_count_q;
  logic [31:0] en_low_count_q;
  logic [31:0] test_en_count_q;
  logic [31:0] test_override_count_q;
  logic [31:0] gated_high_count_q;
  logic [31:0] gated_low_count_q;
  logic [31:0] enable_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] disabled_low_match_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_enable_cycles_q;
  logic last_en_q;
  logic last_clk_o_q;
  logic disabled_high_violation_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_xilinx_clock_gating #(
    .NoFpgaGate(1'b1),
    .FpgaBufGlobal(1'b1)
  ) dut (
    .clk_i,
    .en_i,
    .test_en_i,
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
  assign enable_request_w = en_i || test_en_i;
  assign latched_enable_seen_w = clk_o || (!clk_i && enable_request_w);

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
      rand_q <= cfg_seed_i ^ 32'hc10c_6a7e;
      en_i <= 1'b0;
      test_en_i <= 1'b0;
      en_high_count_q <= 32'd0;
      en_low_count_q <= 32'd0;
      test_en_count_q <= 32'd0;
      test_override_count_q <= 32'd0;
      gated_high_count_q <= 32'd0;
      gated_low_count_q <= 32'd0;
      enable_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      disabled_low_match_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h9e37_79b9;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_enable_cycles_q <= 32'd0;
      last_en_q <= 1'b0;
      last_clk_o_q <= 1'b0;
      disabled_high_violation_q <= 1'b0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i);
      last_en_q <= enable_request_w;
      last_clk_o_q <= clk_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        en_i <= pct_hit(rand_q ^ cfg_req_family_i ^ cfg_source_mask_i,
                        cfg_req_valid_pct_i + cfg_put_full_pct_i);
        test_en_i <= pct_hit({rand_q[15:0], rand_q[31:16]} ^
                             cfg_rsp_family_i ^ cfg_req_data_hi_xor_i,
                             cfg_rsp_valid_pct_i + cfg_put_partial_pct_i);
        signature_q <= {signature_q[30:0], signature_q[31]} ^
                       rand_q ^ {30'd0, en_i, test_en_i} ^
                       cfg_address_mask_i;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        en_i <= cfg_rsp_delay_mode_i[0];
        test_en_i <= cfg_rsp_data_mode_i[0] && (drain_cycle_q[0] == 1'b0);
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      if (enable_request_w) begin
        en_high_count_q <= en_high_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        en_low_count_q <= en_low_count_q + 32'd1;
        if (en_high_count_q == 32'd0) begin
          pre_enable_cycles_q <= pre_enable_cycles_q + 32'd1;
        end
        seen_q[3] <= 1'b1;
      end
      if (test_en_i) begin
        test_en_count_q <= test_en_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end
      if (test_en_i && !en_i) begin
        test_override_count_q <= test_override_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (clk_o) begin
        gated_high_count_q <= gated_high_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end else begin
        gated_low_count_q <= gated_low_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (enable_request_w != last_en_q) begin
        enable_change_count_q <= enable_change_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (clk_o != last_clk_o_q) begin
        output_change_count_q <= output_change_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (!enable_request_w && !clk_o) begin
        disabled_low_match_count_q <= disabled_low_match_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (!enable_request_w && clk_o) begin
        disabled_high_violation_q <= 1'b1;
        seen_q[11] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'hc10c_6a7e;
  assign host_req_accepted_o = en_high_count_q;
  assign device_req_accepted_o = test_en_count_q;
  assign device_rsp_accepted_o = gated_high_count_q;
  assign host_rsp_accepted_o = output_change_count_q;
  assign rsp_queue_overflow_o = {31'd0, disabled_high_violation_q};
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    4'd0,
    seen_q[11:0],
    en_i,
    test_en_i,
    clk_o,
    clk_i,
    rst_ni,
    done_o,
    phase_w,
    global_cycle_q[7:0]
  };
  assign toggle_bitmap_word1_o = {
    3'd0,
    latched_enable_seen_w,
    enable_request_w,
    last_clk_o_q,
    phase_w,
    global_cycle_q[7:0],
    en_high_count_q[7:0],
    gated_high_count_q[7:0]
  };
  assign toggle_bitmap_word2_o = {
    test_override_count_q[7:0],
    enable_change_count_q[7:0],
    output_change_count_q[7:0],
    disabled_low_match_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = en_high_count_q;
  assign real_toggle_subset_word1_o = en_low_count_q;
  assign real_toggle_subset_word2_o = test_en_count_q;
  assign real_toggle_subset_word3_o = test_override_count_q;
  assign real_toggle_subset_word4_o = gated_high_count_q;
  assign real_toggle_subset_word5_o = gated_low_count_q;
  assign real_toggle_subset_word6_o = enable_change_count_q;
  assign real_toggle_subset_word7_o = output_change_count_q;
  assign real_toggle_subset_word8_o = disabled_low_match_count_q;
  assign real_toggle_subset_word9_o = {31'd0, disabled_high_violation_q};
  assign real_toggle_subset_word10_o = traffic_cycle_q;
  assign real_toggle_subset_word11_o = drain_cycle_q;
  assign real_toggle_subset_word12_o = rand_q;
  assign real_toggle_subset_word13_o = {20'd0, seen_q[11:0]};
  assign real_toggle_subset_word14_o = {29'd0, clk_i, clk_o, enable_request_w};
  assign real_toggle_subset_word15_o = {30'd0, phase_w};
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {30'd0, en_i, test_en_i};
  assign focused_wave_word1_o = {31'd0, clk_o};
  assign focused_wave_word2_o = en_high_count_q;
  assign focused_wave_word3_o = test_en_count_q;
  assign focused_wave_word4_o = gated_high_count_q;
  assign focused_wave_word5_o = output_change_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = en_high_count_q + test_override_count_q;
  assign oracle_expected_err_count_o = {31'd0, disabled_high_violation_q};
  assign oracle_observed_ok_count_o = gated_high_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {20'd0, seen_q[11:0]};
  assign oracle_semantic_case_seen_o = {29'd0, clk_i, en_i, test_en_i};
  assign oracle_semantic_case_acked_o = {30'd0, clk_o, latched_enable_seen_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_enable_cycles_q;
endmodule : prim_xilinx_clock_gating_gpu_cov_tb
