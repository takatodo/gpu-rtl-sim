// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_xoshiro256pp.

module prim_xoshiro256pp_gpu_cov_tb (
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
  logic seed_en_i;
  logic xoshiro_en_i;
  logic [255:0] seed_i;
  logic [255:0] entropy_i;
  logic [63:0] data_o;
  logic all_zero_o;
  logic [1:0] phase_w;
  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] seed_count_q;
  logic [31:0] enable_count_q;
  logic [31:0] all_zero_count_q;
  logic [31:0] data_change_count_q;
  logic [31:0] signature_q;
  logic [31:0] seen_q;
  logic [63:0] last_data_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_xoshiro256pp #(
    .OutputDw(64),
    .DefaultSeed(256'h1)
  ) dut (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .seed_en_i(seed_en_i),
    .seed_i(seed_i),
    .xoshiro_en_i(xoshiro_en_i),
    .entropy_i(entropy_i),
    .data_o(data_o),
    .all_zero_o(all_zero_o)
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [63:0] mix64(input logic [31:0] lo, input logic [31:0] hi);
    return {hi ^ 32'h9e37_79b9, lo ^ 32'h85eb_ca6b} ^
           {lo[15:0], hi[31:16], hi[15:0], lo[31:16]};
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);

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

  assign seed_en_i = (phase_w == TrafficPhase) &&
                     (((rand_q ^ traffic_cycle_q ^ cfg_req_valid_pct_i) & 32'h0000_000f) == 32'h0);
  assign xoshiro_en_i = (phase_w == TrafficPhase) ||
                        ((phase_w == DrainPhase) && (drain_cycle_q[0] || cfg_rsp_valid_pct_i[0]));

  assign seed_i = {
    mix64(rand_q ^ cfg_seed_i, cfg_address_base_i ^ traffic_cycle_q) | 64'h1,
    mix64(rand_q ^ cfg_req_data_hi_xor_i, cfg_address_mask_i ^ cfg_rsp_data_hi_xor_i),
    mix64(rand_q ^ cfg_req_family_i, cfg_rsp_family_i ^ global_cycle_q),
    mix64(rand_q ^ cfg_source_mask_i, cfg_req_fill_target_i ^ cfg_rsp_fill_target_i)
  };

  assign entropy_i = {
    mix64(rand_q ^ cfg_put_full_pct_i, cfg_put_partial_pct_i ^ global_cycle_q),
    mix64(rand_q ^ cfg_req_burst_len_max_i, cfg_rsp_delay_max_i ^ traffic_cycle_q),
    mix64(rand_q ^ cfg_req_address_mode_i, cfg_rsp_delay_mode_i ^ drain_cycle_q),
    mix64(rand_q ^ cfg_req_data_mode_i, cfg_rsp_data_mode_i ^ cfg_access_ack_data_pct_i)
  };

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      global_cycle_q <= global_cycle_q + 32'd1;
    end

    if (!rst_ni) begin
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'h2052_5620;
      seed_count_q <= 32'd0;
      enable_count_q <= 32'd0;
      all_zero_count_q <= 32'd0;
      data_change_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h2560_0256;
      seen_q <= 32'd0;
      last_data_q <= 64'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ cfg_address_base_i ^ cfg_req_family_i ^
                          cfg_rsp_family_i ^ global_cycle_q ^ data_o[31:0]);
      signature_q <= {signature_q[30:0], signature_q[31]} ^ data_o[31:0] ^
                     data_o[63:32] ^ {30'd0, phase_w} ^
                     {31'd0, all_zero_o} ^ {31'd0, seed_en_i};
      last_data_q <= data_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        seen_q[1] <= 1'b1;
      end
      if (seed_en_i) begin
        seed_count_q <= seed_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end
      if (xoshiro_en_i) begin
        enable_count_q <= enable_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (all_zero_o) begin
        all_zero_count_q <= all_zero_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end
      if (data_o != last_data_q) begin
        data_change_count_q <= data_change_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (|entropy_i) seen_q[6] <= 1'b1;
      if (|seed_i) seen_q[7] <= 1'b1;
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^ 32'h2560_0256;
  assign host_req_accepted_o = enable_count_q;
  assign device_req_accepted_o = seed_count_q;
  assign device_rsp_accepted_o = data_change_count_q;
  assign host_rsp_accepted_o = global_cycle_q;
  assign rsp_queue_overflow_o = all_zero_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ data_o[31:0] ^ data_o[63:32] ^
                                {30'd0, phase_w} ^ {31'd0, all_zero_o};

  assign toggle_bitmap_word0_o = seen_q ^ {24'd0, data_o[7:0]};
  assign toggle_bitmap_word1_o = {24'd0, seed_en_i, xoshiro_en_i, all_zero_o, phase_w, seen_q[2:0]};
  assign toggle_bitmap_word2_o = signature_q;

  assign real_toggle_subset_word0_o = data_o[31:0];
  assign real_toggle_subset_word1_o = data_o[63:32];
  assign real_toggle_subset_word2_o = last_data_q[31:0];
  assign real_toggle_subset_word3_o = last_data_q[63:32];
  assign real_toggle_subset_word4_o = {29'd0, seed_en_i, xoshiro_en_i, all_zero_o};
  assign real_toggle_subset_word5_o = entropy_i[31:0] ^ seed_i[31:0];
  assign real_toggle_subset_word6_o = enable_count_q;
  assign real_toggle_subset_word7_o = seed_count_q;
  assign real_toggle_subset_word8_o = all_zero_count_q;
  assign real_toggle_subset_word9_o = data_change_count_q;
  assign real_toggle_subset_word10_o = traffic_cycle_q;
  assign real_toggle_subset_word11_o = drain_cycle_q;
  assign real_toggle_subset_word12_o = global_cycle_q;
  assign real_toggle_subset_word13_o = rand_q;
  assign real_toggle_subset_word14_o = signature_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = progress_signature_o;

  assign focused_wave_word0_o = data_o[31:0];
  assign focused_wave_word1_o = data_o[63:32];
  assign focused_wave_word2_o = enable_count_q;
  assign focused_wave_word3_o = seed_count_q;
  assign focused_wave_word4_o = data_change_count_q;
  assign focused_wave_word5_o = {30'd0, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = enable_count_q;
  assign oracle_expected_err_count_o = all_zero_count_q;
  assign oracle_observed_ok_count_o = data_change_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {29'd0, seed_en_i, xoshiro_en_i, all_zero_o};
  assign oracle_semantic_case_seen_o = data_o[31:0];
  assign oracle_semantic_case_acked_o = data_o[63:32];
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = 32'd0;
  assign oracle_req_signature_delta_o = progress_signature_o ^ signature_q;
  assign oracle_req_stable_violation_o = 32'd0;
  assign oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q;
endmodule : prim_xoshiro256pp_gpu_cov_tb
