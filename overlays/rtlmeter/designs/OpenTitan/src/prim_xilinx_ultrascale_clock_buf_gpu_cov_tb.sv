// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_xilinx_ultrascale_clock_buf.

module prim_xilinx_ultrascale_clock_buf_gpu_cov_tb (
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
  logic dut_clk_i;
  logic clk_o;
  logic next_dut_clk_w;
  logic last_dut_clk_q;
  logic last_clk_o_q;
  logic [1:0] phase_w;
  logic observed_match_w;
  logic input_rise_w;
  logic input_fall_w;
  logic output_rise_w;
  logic output_fall_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] input_high_count_q;
  logic [31:0] input_low_count_q;
  logic [31:0] output_high_count_q;
  logic [31:0] output_low_count_q;
  logic [31:0] input_rise_count_q;
  logic [31:0] input_fall_count_q;
  logic [31:0] output_rise_count_q;
  logic [31:0] output_fall_count_q;
  logic [31:0] match_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] traffic_high_count_q;
  logic [31:0] traffic_low_count_q;
  logic [31:0] drain_high_count_q;
  logic [31:0] drain_low_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_xilinx_ultrascale_clock_buf #(
    .NoFpgaBuf(1'b1),
    .RegionSel(1'b0)
  ) dut (
    .clk_i(dut_clk_i),
    .clk_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_dut_clk_w = rand_q[0] ^ rand_q[5] ^ traffic_cycle_q[0] ^
                          cfg_req_family_i[0] ^ cfg_rsp_family_i[0];
  assign observed_match_w = clk_o == dut_clk_i;
  assign input_rise_w = dut_clk_i && !last_dut_clk_q;
  assign input_fall_w = !dut_clk_i && last_dut_clk_q;
  assign output_rise_w = clk_o && !last_clk_o_q;
  assign output_fall_w = !clk_o && last_clk_o_q;

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
      rand_q <= cfg_seed_i ^ 32'hc10c_1d01;
      dut_clk_i <= 1'b0;
      last_dut_clk_q <= 1'b0;
      last_clk_o_q <= 1'b0;
      input_high_count_q <= 32'd0;
      input_low_count_q <= 32'd0;
      output_high_count_q <= 32'd0;
      output_low_count_q <= 32'd0;
      input_rise_count_q <= 32'd0;
      input_fall_count_q <= 32'd0;
      output_rise_count_q <= 32'd0;
      output_fall_count_q <= 32'd0;
      match_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      traffic_high_count_q <= 32'd0;
      traffic_low_count_q <= 32'd0;
      drain_high_count_q <= 32'd0;
      drain_low_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'hb0ff_1d01;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_req_data_hi_xor_i);
      last_dut_clk_q <= dut_clk_i;
      last_clk_o_q <= clk_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        dut_clk_i <= next_dut_clk_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        dut_clk_i <= drain_cycle_q[0] ^ cfg_address_mask_i[0];
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[26:0], signature_q[31:27]} ^
                     rand_q ^ {30'd0, clk_o, dut_clk_i} ^
                     {28'd0, output_fall_w, output_rise_w,
                      input_fall_w, input_rise_w} ^ {30'd0, phase_w};

      if (dut_clk_i) begin
        input_high_count_q <= input_high_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        input_low_count_q <= input_low_count_q + 32'd1;
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (clk_o) begin
        output_high_count_q <= output_high_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        output_low_count_q <= output_low_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (input_rise_w) begin input_rise_count_q <= input_rise_count_q + 32'd1; seen_q[6] <= 1'b1; end
      if (input_fall_w) begin input_fall_count_q <= input_fall_count_q + 32'd1; seen_q[7] <= 1'b1; end
      if (output_rise_w) begin output_rise_count_q <= output_rise_count_q + 32'd1; seen_q[8] <= 1'b1; end
      if (output_fall_w) begin output_fall_count_q <= output_fall_count_q + 32'd1; seen_q[9] <= 1'b1; end
      if (observed_match_w) begin
        match_count_q <= match_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end else begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (phase_w == TrafficPhase && dut_clk_i) begin traffic_high_count_q <= traffic_high_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (phase_w == TrafficPhase && !dut_clk_i) begin traffic_low_count_q <= traffic_low_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (phase_w == DrainPhase && dut_clk_i) begin drain_high_count_q <= drain_high_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (phase_w == DrainPhase && !dut_clk_i) begin drain_low_count_q <= drain_low_count_q + 32'd1; seen_q[15] <= 1'b1; end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'hc10c_1d01;
  assign host_req_accepted_o = input_high_count_q;
  assign device_req_accepted_o = input_low_count_q;
  assign device_rsp_accepted_o = output_high_count_q;
  assign host_rsp_accepted_o = output_low_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    seen_q[7:0],
    11'd0,
    output_fall_w,
    output_rise_w,
    input_fall_w,
    input_rise_w,
    observed_match_w,
    clk_o,
    dut_clk_i,
    rst_ni,
    done_o,
    phase_w,
    cfg_valid_i,
    next_dut_clk_w
  };
  assign toggle_bitmap_word1_o = {
    seen_q[23:8],
    input_high_count_q[3:0],
    input_low_count_q[3:0],
    output_high_count_q[3:0],
    output_low_count_q[3:0]
  };
  assign toggle_bitmap_word2_o = {
    match_count_q[7:0],
    mismatch_count_q[7:0],
    traffic_cycle_q[7:0],
    drain_cycle_q[7:0]
  };

  assign real_toggle_subset_word0_o = input_high_count_q;
  assign real_toggle_subset_word1_o = input_low_count_q;
  assign real_toggle_subset_word2_o = output_high_count_q;
  assign real_toggle_subset_word3_o = output_low_count_q;
  assign real_toggle_subset_word4_o = input_rise_count_q;
  assign real_toggle_subset_word5_o = input_fall_count_q;
  assign real_toggle_subset_word6_o = output_rise_count_q;
  assign real_toggle_subset_word7_o = output_fall_count_q;
  assign real_toggle_subset_word8_o = match_count_q;
  assign real_toggle_subset_word9_o = mismatch_count_q;
  assign real_toggle_subset_word10_o = traffic_high_count_q;
  assign real_toggle_subset_word11_o = traffic_low_count_q;
  assign real_toggle_subset_word12_o = drain_high_count_q;
  assign real_toggle_subset_word13_o = drain_low_count_q;
  assign real_toggle_subset_word14_o = traffic_cycle_q;
  assign real_toggle_subset_word15_o = drain_cycle_q;
  assign real_toggle_subset_word16_o = seen_q;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {31'd0, dut_clk_i};
  assign focused_wave_word1_o = {31'd0, clk_o};
  assign focused_wave_word2_o = {28'd0, output_fall_w, output_rise_w,
                                 input_fall_w, input_rise_w};
  assign focused_wave_word3_o = {29'd0, observed_match_w, clk_o, dut_clk_i};
  assign focused_wave_word4_o = input_high_count_q ^ input_low_count_q;
  assign focused_wave_word5_o = output_high_count_q ^ output_low_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = match_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = output_high_count_q + output_low_count_q;
  assign oracle_observed_err_count_o = mismatch_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    input_rise_count_q[7:0],
    input_fall_count_q[7:0],
    output_rise_count_q[7:0],
    output_fall_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {30'd0, clk_o, dut_clk_i};
  assign oracle_semantic_case_acked_o = {31'd0, observed_match_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_xilinx_ultrascale_clock_buf_gpu_cov_tb
