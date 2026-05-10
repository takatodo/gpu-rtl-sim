// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_fifo_sync.

module prim_fifo_sync_gpu_cov_tb (
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
  localparam int unsigned Depth = 4;
  localparam int unsigned DepthW = prim_util_pkg::vbits(Depth + 1);
  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] TrafficPhase = 3'd1;
  localparam logic [2:0] DrainPhase   = 3'd2;
  localparam logic [2:0] ClearPhase   = 3'd3;
  localparam logic [2:0] DonePhase    = 3'd4;

  logic clk_i;
  logic rst_ni;
  logic clr_i;
  logic wvalid_i;
  logic wready_o;
  logic [Width-1:0] wdata_i;
  logic rvalid_o;
  logic rready_i;
  logic [Width-1:0] rdata_o;
  logic full_o;
  logic [DepthW-1:0] depth_o;
  logic err_o;
  logic [2:0] phase_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] clear_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] write_attempt_count_q;
  logic [31:0] write_accept_count_q;
  logic [31:0] write_blocked_count_q;
  logic [31:0] read_ready_count_q;
  logic [31:0] read_accept_count_q;
  logic [31:0] read_blocked_count_q;
  logic [31:0] full_count_q;
  logic [31:0] empty_count_q;
  logic [31:0] depth_one_count_q;
  logic [31:0] depth_mid_count_q;
  logic [31:0] clear_count_q;
  logic [31:0] under_reset_block_count_q;
  logic [31:0] input_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] last_wdata_q;
  logic [31:0] last_rdata_q;
  logic [31:0] seen_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_fifo_sync #(
    .Width(Width),
    .Pass(1'b1),
    .Depth(Depth),
    .OutputZeroIfEmpty(1'b1),
    .Secure(1'b0)
  ) dut (
    .clk_i,
    .rst_ni,
    .clr_i,
    .wvalid_i,
    .wready_o,
    .wdata_i,
    .rvalid_o,
    .rready_i,
    .rdata_o,
    .full_o,
    .depth_o,
    .err_o
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

  function automatic logic [Width-1:0] mix_data(
    input logic [31:0] state,
    input logic [31:0] count
  );
    logic [31:0] mixed;
    mixed = state ^ cfg_seed_i ^ cfg_address_base_i ^
            (count * 32'd2654435761) ^ cfg_req_data_hi_xor_i ^
            {cfg_req_family_i[15:0], cfg_rsp_family_i[15:0]};
    return mixed[Width-1:0];
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);

  always_comb begin
    if (!cfg_valid_i || !rst_ni) begin
      phase_w = ResetPhase;
    end else if (traffic_cycle_q < cfg_batch_length_i) begin
      phase_w = TrafficPhase;
    end else if (drain_cycle_q < cfg_drain_cycles_i) begin
      phase_w = DrainPhase;
    end else if (clear_cycle_q < 32'd2) begin
      phase_w = ClearPhase;
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
      clr_i <= 1'b0;
      wvalid_i <= 1'b0;
      wdata_i <= '0;
      rready_i <= 1'b0;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      clear_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'hf150_5a4e;
      write_attempt_count_q <= 32'd0;
      write_accept_count_q <= 32'd0;
      write_blocked_count_q <= 32'd0;
      read_ready_count_q <= 32'd0;
      read_accept_count_q <= 32'd0;
      read_blocked_count_q <= 32'd0;
      full_count_q <= 32'd0;
      empty_count_q <= 32'd0;
      depth_one_count_q <= 32'd0;
      depth_mid_count_q <= 32'd0;
      clear_count_q <= 32'd0;
      under_reset_block_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5163_0001;
      stalled_signature_q <= 32'd0;
      last_wdata_q <= 32'd0;
      last_rdata_q <= 32'd0;
      seen_q <= 32'd0;
    end else begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i);
      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
      end else if (phase_w == ClearPhase) begin
        clear_cycle_q <= clear_cycle_q + 32'd1;
      end

      clr_i <= phase_w == ClearPhase && clear_cycle_q == 32'd0;
      wvalid_i <= phase_w == TrafficPhase &&
                  pct_hit(rand_q ^ cfg_seed_i, cfg_req_valid_pct_i);
      wdata_i <= mix_data(rand_q, write_attempt_count_q);
      rready_i <= (phase_w == DrainPhase) ||
                  (phase_w == TrafficPhase &&
                   pct_hit(rand_q ^ 32'ha5a5_5a5a, cfg_host_d_ready_pct_i));

      if (phase_w == ResetPhase && wready_o == 1'b0) begin
        under_reset_block_count_q <= under_reset_block_count_q + 32'd1;
      end
      if (wvalid_i) begin
        write_attempt_count_q <= write_attempt_count_q + 32'd1;
        seen_q[0] <= 1'b1;
      end
      if (wvalid_i && wready_o) begin
        write_accept_count_q <= write_accept_count_q + 32'd1;
        signature_q <= {signature_q[30:0], signature_q[31]} ^
                       {24'd0, wdata_i} ^ write_accept_count_q;
        seen_q[1] <= 1'b1;
        if ({24'd0, wdata_i} != last_wdata_q) begin
          input_change_count_q <= input_change_count_q + 32'd1;
        end
        last_wdata_q <= {24'd0, wdata_i};
      end
      if (wvalid_i && !wready_o) begin
        write_blocked_count_q <= write_blocked_count_q + 32'd1;
        stalled_signature_q <= stalled_signature_q ^ {24'd0, wdata_i} ^ global_cycle_q;
        seen_q[2] <= 1'b1;
      end
      if (rready_i) begin
        read_ready_count_q <= read_ready_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (rvalid_o && rready_i) begin
        read_accept_count_q <= read_accept_count_q + 32'd1;
        signature_q <= {signature_q[28:0], signature_q[31:29]} ^
                       {24'd0, rdata_o} ^ read_accept_count_q;
        seen_q[4] <= 1'b1;
        if ({24'd0, rdata_o} != last_rdata_q) begin
          output_change_count_q <= output_change_count_q + 32'd1;
        end
        last_rdata_q <= {24'd0, rdata_o};
      end
      if (rvalid_o && !rready_i) begin
        read_blocked_count_q <= read_blocked_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (full_o) begin
        full_count_q <= full_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (depth_o == DepthW'(0)) begin
        empty_count_q <= empty_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (depth_o == DepthW'(1)) begin
        depth_one_count_q <= depth_one_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (depth_o > DepthW'(1) && !full_o) begin
        depth_mid_count_q <= depth_mid_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (clr_i) begin
        clear_count_q <= clear_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (err_o) begin
        seen_q[11] <= 1'b1;
      end
      if (rvalid_o) begin
        seen_q[12] <= 1'b1;
      end
      if (wready_o) begin
        seen_q[13] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && phase_w == DonePhase;
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_req_valid_pct_i ^
                           cfg_host_d_ready_pct_i ^ cfg_drain_cycles_i ^
                           cfg_address_base_i;
  assign host_req_accepted_o = write_accept_count_q;
  assign device_req_accepted_o = read_accept_count_q;
  assign device_rsp_accepted_o = read_ready_count_q;
  assign host_rsp_accepted_o = write_attempt_count_q;
  assign rsp_queue_overflow_o = write_blocked_count_q + read_blocked_count_q + {31'd0, err_o};
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q + clear_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^
                                {24'd0, phase_w, done_o, rst_ni, full_o, rvalid_o, wready_o};

  assign toggle_bitmap_word0_o = seen_q;
  assign toggle_bitmap_word1_o = {
    17'd0,
    done_o,
    rst_ni,
    clr_i,
    wvalid_i,
    wready_o,
    rvalid_o,
    rready_i,
    full_o,
    err_o,
    depth_o,
    phase_w
  };
  assign toggle_bitmap_word2_o = {
    16'd0,
    write_accept_count_q != 32'd0,
    read_accept_count_q != 32'd0,
    write_blocked_count_q != 32'd0,
    read_blocked_count_q != 32'd0,
    full_count_q != 32'd0,
    empty_count_q != 32'd0,
    depth_one_count_q != 32'd0,
    depth_mid_count_q != 32'd0,
    clear_count_q != 32'd0,
    input_change_count_q != 32'd0,
    output_change_count_q != 32'd0,
    under_reset_block_count_q != 32'd0,
    err_o,
    rvalid_o,
    wready_o,
    done_o
  };

  assign real_toggle_subset_word0_o = write_accept_count_q;
  assign real_toggle_subset_word1_o = read_accept_count_q;
  assign real_toggle_subset_word2_o = write_attempt_count_q;
  assign real_toggle_subset_word3_o = write_blocked_count_q;
  assign real_toggle_subset_word4_o = read_ready_count_q;
  assign real_toggle_subset_word5_o = read_blocked_count_q;
  assign real_toggle_subset_word6_o = full_count_q;
  assign real_toggle_subset_word7_o = empty_count_q;
  assign real_toggle_subset_word8_o = depth_one_count_q;
  assign real_toggle_subset_word9_o = depth_mid_count_q;
  assign real_toggle_subset_word10_o = clear_count_q;
  assign real_toggle_subset_word11_o = under_reset_block_count_q;
  assign real_toggle_subset_word12_o = input_change_count_q;
  assign real_toggle_subset_word13_o = output_change_count_q;
  assign real_toggle_subset_word14_o = signature_q;
  assign real_toggle_subset_word15_o = stalled_signature_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = progress_signature_o;

  assign focused_wave_word0_o = global_cycle_q;
  assign focused_wave_word1_o = {23'd0, phase_w, depth_o, full_o, rvalid_o, wready_o};
  assign focused_wave_word2_o = {24'd0, wdata_i};
  assign focused_wave_word3_o = {24'd0, rdata_o};
  assign focused_wave_word4_o = signature_q;
  assign focused_wave_word5_o = stalled_signature_q;
  assign focused_wave_word6_o = {write_accept_count_q[15:0], read_accept_count_q[15:0]};
  assign focused_wave_word7_o = {write_blocked_count_q[15:0], read_blocked_count_q[15:0]};

  assign oracle_expected_ok_count_o = write_accept_count_q;
  assign oracle_expected_err_count_o = write_blocked_count_q;
  assign oracle_observed_ok_count_o = read_accept_count_q;
  assign oracle_observed_err_count_o = read_blocked_count_q + {31'd0, err_o};
  assign oracle_semantic_family_seen_o = cfg_req_family_i ^ cfg_rsp_family_i;
  assign oracle_semantic_family_acked_o = {write_accept_count_q[15:0], read_accept_count_q[15:0]};
  assign oracle_semantic_case_seen_o = cfg_req_data_mode_i ^ cfg_rsp_data_mode_i;
  assign oracle_semantic_case_acked_o = {full_count_q[15:0], empty_count_q[15:0]};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = 32'd0;
  assign oracle_pre_handshake_traffic_cycles_o = under_reset_block_count_q;

endmodule
