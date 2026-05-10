// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_xilinx_ram_1p.

module prim_xilinx_ram_1p_gpu_cov_tb
  import prim_ram_1p_pkg::*;
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
  logic req_i;
  logic write_i;
  logic [3:0] addr_i;
  logic [7:0] wdata_i;
  logic [7:0] wmask_i;
  logic [7:0] rdata_o;
  ram_1p_cfg_t cfg_i;
  ram_1p_cfg_rsp_t cfg_rsp_o;
  logic [1:0] phase_w;
  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] write_count_q;
  logic [31:0] read_count_q;
  logic [31:0] read_response_count_q;
  logic [31:0] read_match_count_q;
  logic [31:0] data_change_count_q;
  logic [31:0] signature_q;
  logic [31:0] seen_q;
  logic [7:0] last_wdata_q;
  logic [7:0] expected_rdata_q;
  logic [7:0] last_rdata_q;
  logic [3:0] last_addr_q;
  logic read_rsp_valid_q;

  prim_xilinx_ram_1p #(
    .Width(8),
    .Depth(16),
    .DataBitsPerMask(1),
    .MemInitFile("")
  ) dut (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .req_i(req_i),
    .write_i(write_i),
    .addr_i(addr_i),
    .wdata_i(wdata_i),
    .wmask_i(wmask_i),
    .rdata_o(rdata_o),
    .cfg_i(cfg_i),
    .cfg_rsp_o(cfg_rsp_o)
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign cfg_i = RAM_1P_CFG_DEFAULT;
  assign req_i = (phase_w == TrafficPhase) ||
                 ((phase_w == DrainPhase) && (drain_cycle_q < 32'd2));
  assign write_i = (phase_w == TrafficPhase) && !traffic_cycle_q[0];
  assign addr_i = ((phase_w == DrainPhase) ? last_addr_q :
                   (traffic_cycle_q[4:1] ^ cfg_address_base_i[3:0])) &
                  (cfg_address_mask_i[3:0] | 4'hf);
  assign wdata_i = rand_q[7:0] ^ traffic_cycle_q[7:0] ^
                   cfg_req_data_hi_xor_i[7:0] ^ {4'h0, addr_i};
  assign wmask_i = write_i ? 8'hff : 8'h00;

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
      rand_q <= cfg_seed_i ^ 32'h5100_1a1d;
      write_count_q <= 32'd0;
      read_count_q <= 32'd0;
      read_response_count_q <= 32'd0;
      read_match_count_q <= 32'd0;
      data_change_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h0000_1a1d;
      seen_q <= 32'd0;
      last_wdata_q <= 8'd0;
      expected_rdata_q <= 8'd0;
      last_rdata_q <= 8'd0;
      last_addr_q <= 4'd0;
      read_rsp_valid_q <= 1'b0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ cfg_address_base_i ^ cfg_req_family_i ^
                          cfg_rsp_family_i ^ global_cycle_q ^ {24'd0, last_rdata_q});
      signature_q <= {signature_q[30:0], signature_q[31]} ^
                     {24'd0, (read_rsp_valid_q ? rdata_o : last_rdata_q)} ^
                     {24'd0, wdata_i} ^ {28'd0, addr_i} ^
                     {30'd0, phase_w} ^ {31'd0, write_i};
      last_rdata_q <= read_rsp_valid_q ? rdata_o : last_rdata_q;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        seen_q[1] <= 1'b1;
      end

      if (req_i && write_i) begin
        write_count_q <= write_count_q + 32'd1;
        last_wdata_q <= wdata_i;
        expected_rdata_q <= wdata_i;
        last_addr_q <= addr_i;
        seen_q[2] <= 1'b1;
      end
      if (req_i && !write_i) begin
        read_count_q <= read_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (read_rsp_valid_q) begin
        read_response_count_q <= read_response_count_q + 32'd1;
        if (rdata_o == expected_rdata_q) read_match_count_q <= read_match_count_q + 32'd1;
        if (rdata_o != last_rdata_q) data_change_count_q <= data_change_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end
      if (addr_i != last_addr_q) seen_q[5] <= 1'b1;
      if (wmask_i == 8'hff) seen_q[6] <= 1'b1;
      if (cfg_rsp_o.done == 1'b0) seen_q[7] <= 1'b1;
      if (req_i && !write_i && (addr_i == last_addr_q)) seen_q[8] <= 1'b1;

      read_rsp_valid_q <= req_i && !write_i;
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^ 32'h0000_1a1d;
  assign host_req_accepted_o = write_count_q;
  assign device_req_accepted_o = read_count_q;
  assign device_rsp_accepted_o = read_response_count_q;
  assign host_rsp_accepted_o = read_match_count_q;
  assign rsp_queue_overflow_o = read_response_count_q - read_match_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ {24'd0, last_rdata_q} ^ {24'd0, expected_rdata_q} ^
                                {28'd0, addr_i} ^ {30'd0, phase_w} ^ {31'd0, req_i};

  assign toggle_bitmap_word0_o = seen_q ^ {24'd0, last_rdata_q};
  assign toggle_bitmap_word1_o = {23'd0, req_i, write_i, read_rsp_valid_q, phase_w, addr_i};
  assign toggle_bitmap_word2_o = signature_q;

  assign real_toggle_subset_word0_o = {24'd0, rdata_o};
  assign real_toggle_subset_word1_o = {24'd0, last_rdata_q};
  assign real_toggle_subset_word2_o = {24'd0, wdata_i};
  assign real_toggle_subset_word3_o = {24'd0, expected_rdata_q};
  assign real_toggle_subset_word4_o = {28'd0, addr_i};
  assign real_toggle_subset_word5_o = {24'd0, wmask_i};
  assign real_toggle_subset_word6_o = write_count_q;
  assign real_toggle_subset_word7_o = read_count_q;
  assign real_toggle_subset_word8_o = read_response_count_q;
  assign real_toggle_subset_word9_o = read_match_count_q;
  assign real_toggle_subset_word10_o = data_change_count_q;
  assign real_toggle_subset_word11_o = global_cycle_q;
  assign real_toggle_subset_word12_o = rand_q;
  assign real_toggle_subset_word13_o = signature_q;
  assign real_toggle_subset_word14_o = seen_q;
  assign real_toggle_subset_word15_o = progress_signature_o;
  assign real_toggle_subset_word16_o = {28'd0, cfg_rsp_o.done, req_i, write_i, read_rsp_valid_q};
  assign real_toggle_subset_word17_o = progress_signature_o ^ {31'd0, done_o};

  assign focused_wave_word0_o = {24'd0, rdata_o};
  assign focused_wave_word1_o = {24'd0, wdata_i};
  assign focused_wave_word2_o = {28'd0, addr_i};
  assign focused_wave_word3_o = write_count_q;
  assign focused_wave_word4_o = read_count_q;
  assign focused_wave_word5_o = read_match_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = read_response_count_q;
  assign oracle_expected_err_count_o = 32'd0;
  assign oracle_observed_ok_count_o = read_match_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {24'd0, last_wdata_q};
  assign oracle_semantic_case_seen_o = {24'd0, last_rdata_q};
  assign oracle_semantic_case_acked_o = {24'd0, expected_rdata_q};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = 32'd0;
  assign oracle_req_signature_delta_o = progress_signature_o ^ signature_q;
  assign oracle_req_stable_violation_o = 32'd0;
  assign oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q;
endmodule : prim_xilinx_ram_1p_gpu_cov_tb
