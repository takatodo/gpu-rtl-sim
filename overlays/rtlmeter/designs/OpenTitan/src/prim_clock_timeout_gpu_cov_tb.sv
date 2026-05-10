// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_clock_timeout.

module prim_clock_timeout_gpu_cov_tb (
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
  localparam int unsigned TimeOutCnt = 4;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic clk_chk_i;
  logic rst_ni;
  logic rst_chk_ni;
  logic en_i;
  logic timeout_o;
  logic chk_clk_enable_q;
  logic last_timeout_q;
  logic last_en_q;
  logic last_chk_enable_q;
  logic [1:0] phase_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] en_high_count_q;
  logic [31:0] en_low_count_q;
  logic [31:0] chk_run_count_q;
  logic [31:0] chk_stop_count_q;
  logic [31:0] timeout_high_count_q;
  logic [31:0] timeout_low_count_q;
  logic [31:0] timeout_rise_count_q;
  logic [31:0] timeout_fall_count_q;
  logic [31:0] en_rise_count_q;
  logic [31:0] en_fall_count_q;
  logic [31:0] chk_run_rise_count_q;
  logic [31:0] chk_run_fall_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
    clk_chk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;
  always #7 begin
    if (chk_clk_enable_q) begin
      clk_chk_i = ~clk_chk_i;
    end
  end

  prim_clock_timeout #(
    .TimeOutCnt(TimeOutCnt)
  ) dut (
    .clk_chk_i(clk_chk_i),
    .rst_chk_ni(rst_chk_ni),
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .en_i(en_i),
    .timeout_o(timeout_o)
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign rst_chk_ni = rst_ni;

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
      rand_q <= cfg_seed_i ^ 32'hc10c_7001;
      en_i <= 1'b0;
      chk_clk_enable_q <= 1'b1;
      last_timeout_q <= 1'b0;
      last_en_q <= 1'b0;
      last_chk_enable_q <= 1'b1;
      en_high_count_q <= 32'd0;
      en_low_count_q <= 32'd0;
      chk_run_count_q <= 32'd0;
      chk_stop_count_q <= 32'd0;
      timeout_high_count_q <= 32'd0;
      timeout_low_count_q <= 32'd0;
      timeout_rise_count_q <= 32'd0;
      timeout_fall_count_q <= 32'd0;
      en_rise_count_q <= 32'd0;
      en_fall_count_q <= 32'd0;
      chk_run_rise_count_q <= 32'd0;
      chk_run_fall_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h7001_c10c;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i ^
                          cfg_req_fill_target_i ^ cfg_rsp_delay_max_i);
      last_timeout_q <= timeout_o;
      last_en_q <= en_i;
      last_chk_enable_q <= chk_clk_enable_q;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        en_i <= rand_q[0] | cfg_req_valid_pct_i[0] | cfg_rsp_valid_pct_i[0];
        chk_clk_enable_q <= !(rand_q[3] ^ cfg_req_data_mode_i[0] ^
                              cfg_rsp_delay_mode_i[0] ^ traffic_cycle_q[1]);
        seen_q[8] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        en_i <= 1'b1;
        chk_clk_enable_q <= cfg_rsp_family_i[0];
        stalled_signature_q <= stalled_signature_q ^ signature_q ^
                               drain_cycle_q ^ cfg_rsp_fill_target_i;
        seen_q[9] <= 1'b1;
      end

      if (en_i) begin
        en_high_count_q <= en_high_count_q + 32'd1;
        seen_q[0] <= 1'b1;
      end else begin
        en_low_count_q <= en_low_count_q + 32'd1;
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
        seen_q[1] <= 1'b1;
      end
      if (chk_clk_enable_q) begin
        chk_run_count_q <= chk_run_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        chk_stop_count_q <= chk_stop_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (timeout_o) begin
        timeout_high_count_q <= timeout_high_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        timeout_low_count_q <= timeout_low_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (timeout_o && !last_timeout_q) begin
        timeout_rise_count_q <= timeout_rise_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (!timeout_o && last_timeout_q) begin
        timeout_fall_count_q <= timeout_fall_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (en_i && !last_en_q) begin
        en_rise_count_q <= en_rise_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (!en_i && last_en_q) begin
        en_fall_count_q <= en_fall_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (chk_clk_enable_q && !last_chk_enable_q) begin
        chk_run_rise_count_q <= chk_run_rise_count_q + 32'd1;
        seen_q[12] <= 1'b1;
      end
      if (!chk_clk_enable_q && last_chk_enable_q) begin
        chk_run_fall_count_q <= chk_run_fall_count_q + 32'd1;
        seen_q[13] <= 1'b1;
      end
      signature_q <= {signature_q[30:0], signature_q[31]} ^
                     {28'd0, timeout_o, chk_clk_enable_q, en_i, phase_w[0]} ^
                     rand_q ^ cfg_address_mask_i ^ cfg_source_mask_i;
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i;
  assign host_req_accepted_o = en_high_count_q;
  assign device_req_accepted_o = chk_stop_count_q;
  assign device_rsp_accepted_o = timeout_high_count_q;
  assign host_rsp_accepted_o = timeout_rise_count_q;
  assign rsp_queue_overflow_o = 32'd0;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    2'd0,
    seen_q[13:0],
    13'd0,
    timeout_o,
    chk_clk_enable_q,
    en_i
  };
  assign toggle_bitmap_word1_o = {
    12'd0,
    phase_w,
    last_chk_enable_q,
    last_en_q,
    last_timeout_q,
    global_cycle_q[14:0]
  };
  assign toggle_bitmap_word2_o = {
    timeout_rise_count_q[7:0],
    timeout_high_count_q[7:0],
    chk_stop_count_q[7:0],
    en_high_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = en_high_count_q;
  assign real_toggle_subset_word1_o = en_low_count_q;
  assign real_toggle_subset_word2_o = chk_run_count_q;
  assign real_toggle_subset_word3_o = chk_stop_count_q;
  assign real_toggle_subset_word4_o = timeout_high_count_q;
  assign real_toggle_subset_word5_o = timeout_low_count_q;
  assign real_toggle_subset_word6_o = timeout_rise_count_q;
  assign real_toggle_subset_word7_o = timeout_fall_count_q;
  assign real_toggle_subset_word8_o = en_rise_count_q;
  assign real_toggle_subset_word9_o = en_fall_count_q;
  assign real_toggle_subset_word10_o = chk_run_rise_count_q;
  assign real_toggle_subset_word11_o = chk_run_fall_count_q;
  assign real_toggle_subset_word12_o = traffic_cycle_q;
  assign real_toggle_subset_word13_o = drain_cycle_q;
  assign real_toggle_subset_word14_o = rand_q;
  assign real_toggle_subset_word15_o = progress_signature_o;
  assign real_toggle_subset_word16_o = seen_q;
  assign real_toggle_subset_word17_o = {29'd0, timeout_o, chk_clk_enable_q, en_i};

  assign focused_wave_word0_o = {29'd0, timeout_o, chk_clk_enable_q, en_i};
  assign focused_wave_word1_o = en_high_count_q;
  assign focused_wave_word2_o = chk_stop_count_q;
  assign focused_wave_word3_o = timeout_high_count_q;
  assign focused_wave_word4_o = timeout_rise_count_q;
  assign focused_wave_word5_o = {30'd0, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = timeout_high_count_q;
  assign oracle_expected_err_count_o = 32'd0;
  assign oracle_observed_ok_count_o = timeout_rise_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {18'd0, seen_q[13:0]};
  assign oracle_semantic_case_seen_o = {29'd0, timeout_o, chk_clk_enable_q, en_i};
  assign oracle_semantic_case_acked_o = {29'd0, last_timeout_q, last_chk_enable_q, last_en_q};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_clock_timeout_gpu_cov_tb
