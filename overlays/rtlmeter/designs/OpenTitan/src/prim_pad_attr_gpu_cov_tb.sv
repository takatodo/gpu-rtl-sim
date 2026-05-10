// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_pad_attr.

module prim_pad_attr_gpu_cov_tb
  import prim_pad_wrapper_pkg::*;
(
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
  pad_attr_t attr_warl_o;
  logic [AttrDw-1:0] attr_bits_w;
  logic [1:0] phase_w;
  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] attr_signature_q;
  logic [31:0] stable_count_q;
  logic [31:0] active_count_q;
  logic [31:0] drain_count_q;
  logic [31:0] seen_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_pad_attr #(
    .PadType(BidirStd)
  ) dut (
    .attr_warl_o(attr_warl_o)
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign attr_bits_w = attr_warl_o;

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
      rand_q <= cfg_seed_i ^ 32'h0bad_a770;
      attr_signature_q <= {18'd0, attr_bits_w} ^ cfg_seed_i;
      stable_count_q <= 32'd0;
      active_count_q <= 32'd0;
      drain_count_q <= 32'd0;
      seen_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ cfg_address_base_i ^ cfg_req_family_i ^
                          cfg_rsp_family_i ^ global_cycle_q);
      attr_signature_q <= {attr_signature_q[30:0], attr_signature_q[31]} ^
                          {18'd0, attr_bits_w} ^ rand_q ^ cfg_address_mask_i;
      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        active_count_q <= active_count_q + 32'd1;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        drain_count_q <= drain_count_q + 32'd1;
        seen_q[1] <= 1'b1;
      end
      if (attr_bits_w != '0) begin
        stable_count_q <= stable_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end
      if (attr_warl_o.input_disable) seen_q[3] <= 1'b1;
      if (attr_warl_o.virt_od_en) seen_q[4] <= 1'b1;
      if (attr_warl_o.pull_en) seen_q[5] <= 1'b1;
      if (attr_warl_o.pull_select) seen_q[6] <= 1'b1;
      if (attr_warl_o.invert) seen_q[7] <= 1'b1;
      if (phase_w == DonePhase) seen_q[8] <= 1'b1;
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i;
  assign host_req_accepted_o = active_count_q;
  assign device_req_accepted_o = stable_count_q;
  assign device_rsp_accepted_o = drain_count_q;
  assign host_rsp_accepted_o = global_cycle_q;
  assign rsp_queue_overflow_o = 32'd0;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = attr_signature_q ^ {18'd0, attr_bits_w} ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {9'd0, seen_q[8:0], attr_bits_w};
  assign toggle_bitmap_word1_o = {16'd0, phase_w, attr_bits_w};
  assign toggle_bitmap_word2_o = attr_signature_q;

  assign real_toggle_subset_word0_o = {18'd0, attr_bits_w};
  assign real_toggle_subset_word1_o = {31'd0, attr_warl_o.input_disable};
  assign real_toggle_subset_word2_o = {31'd0, attr_warl_o.virt_od_en};
  assign real_toggle_subset_word3_o = {31'd0, attr_warl_o.pull_en};
  assign real_toggle_subset_word4_o = {31'd0, attr_warl_o.pull_select};
  assign real_toggle_subset_word5_o = {31'd0, attr_warl_o.invert};
  assign real_toggle_subset_word6_o = active_count_q;
  assign real_toggle_subset_word7_o = stable_count_q;
  assign real_toggle_subset_word8_o = drain_count_q;
  assign real_toggle_subset_word9_o = traffic_cycle_q;
  assign real_toggle_subset_word10_o = drain_cycle_q;
  assign real_toggle_subset_word11_o = global_cycle_q;
  assign real_toggle_subset_word12_o = rand_q;
  assign real_toggle_subset_word13_o = attr_signature_q;
  assign real_toggle_subset_word14_o = seen_q;
  assign real_toggle_subset_word15_o = progress_signature_o;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {18'd0, attr_bits_w};
  assign focused_wave_word1_o = active_count_q;
  assign focused_wave_word2_o = stable_count_q;
  assign focused_wave_word3_o = drain_count_q;
  assign focused_wave_word4_o = seen_q;
  assign focused_wave_word5_o = {30'd0, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = stable_count_q;
  assign oracle_expected_err_count_o = 32'd0;
  assign oracle_observed_ok_count_o = active_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {18'd0, attr_bits_w};
  assign oracle_semantic_case_seen_o = {18'd0, attr_bits_w};
  assign oracle_semantic_case_acked_o = {18'd0, attr_bits_w};
  assign oracle_req_signature_o = attr_signature_q;
  assign oracle_stalled_req_signature_o = 32'd0;
  assign oracle_req_signature_delta_o = attr_signature_q;
  assign oracle_req_stable_violation_o = 32'd0;
  assign oracle_pre_handshake_traffic_cycles_o = stable_count_q;
endmodule : prim_pad_attr_gpu_cov_tb
