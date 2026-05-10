// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_packer_fifo.

module prim_packer_fifo_gpu_cov_tb (
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
  localparam int unsigned InW = 8;
  localparam int unsigned OutW = 16;
  localparam int unsigned DepthW = 1;
  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] TrafficPhase = 3'd1;
  localparam logic [2:0] DrainPhase   = 3'd2;
  localparam logic [2:0] ClearPhase   = 3'd3;
  localparam logic [2:0] DonePhase    = 3'd4;

  logic clk_i;
  logic rst_ni;
  logic clr_i;
  logic wvalid_i;
  logic [InW-1:0] wdata_i;
  logic wready_o;
  logic rvalid_o;
  logic [OutW-1:0] rdata_o;
  logic rready_i;
  logic [DepthW:0] depth_o;

  logic [InW-1:0] next_wdata_w;
  logic next_wvalid_w;
  logic next_rready_w;
  logic write_accept_w;
  logic read_accept_w;
  logic full_w;
  logic empty_w;
  logic input_changed_w;
  logic output_changed_w;
  logic stalled_write_w;
  logic stalled_read_w;
  logic [OutW-1:0] expected_rdata_w;
  logic observed_match_w;
  logic [2:0] phase_w;

  logic [InW-1:0] last_wdata_q;
  logic [OutW-1:0] last_rdata_q;
  logic [InW-1:0] pack_low_q;
  logic [InW-1:0] pack_high_q;
  logic [1:0] pack_count_q;
  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] clear_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] wvalid_count_q;
  logic [31:0] wready_count_q;
  logic [31:0] write_accept_count_q;
  logic [31:0] rvalid_count_q;
  logic [31:0] rready_count_q;
  logic [31:0] read_accept_count_q;
  logic [31:0] depth_zero_count_q;
  logic [31:0] depth_one_count_q;
  logic [31:0] depth_full_count_q;
  logic [31:0] stalled_write_count_q;
  logic [31:0] stalled_read_count_q;
  logic [31:0] clear_count_q;
  logic [31:0] input_nonzero_count_q;
  logic [31:0] output_nonzero_count_q;
  logic [31:0] input_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] match_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_packer_fifo #(
    .InW(InW),
    .OutW(OutW),
    .ClearOnRead(1'b1)
  ) dut (
    .clk_i,
    .rst_ni,
    .clr_i,
    .wvalid_i,
    .wdata_i,
    .wready_o,
    .rvalid_o,
    .rdata_o,
    .rready_i,
    .depth_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [InW-1:0] mix_data(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [31:0] mixed;
    mixed = state ^ {state[12:0], state[31:13]} ^ salt;
    return mixed[InW-1:0];
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_wdata_w = mix_data(rand_q ^ traffic_cycle_q,
                                 cfg_address_base_i ^ cfg_req_data_hi_xor_i ^
                                 cfg_source_mask_i);
  assign next_wvalid_w = ((rand_q[2:0] < 3'd6) || (cfg_req_valid_pct_i > 32'd0) ||
                          (traffic_cycle_q[0] == 1'b0));
  assign next_rready_w = ((rand_q[6:4] < 3'd5) || (cfg_host_d_ready_pct_i > 32'd0) ||
                          (cfg_rsp_valid_pct_i > 32'd0) ||
                          (traffic_cycle_q[2:0] == 3'd3));
  assign write_accept_w = wvalid_i & wready_o;
  assign read_accept_w = rvalid_o & rready_i;
  assign full_w = depth_o == 2'd2;
  assign empty_w = depth_o == 2'd0;
  assign input_changed_w = wdata_i != last_wdata_q;
  assign output_changed_w = rdata_o != last_rdata_q;
  assign stalled_write_w = wvalid_i & !wready_o;
  assign stalled_read_w = rvalid_o & !rready_i;
  assign expected_rdata_w = {pack_high_q, pack_low_q};
  assign observed_match_w = !rvalid_o || (rdata_o == expected_rdata_w);

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
      rready_i <= 1'b1;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      clear_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'hf1f0_3501;
      last_wdata_q <= '0;
      last_rdata_q <= '0;
      pack_low_q <= '0;
      pack_high_q <= '0;
      pack_count_q <= '0;
      wvalid_count_q <= 32'd0;
      wready_count_q <= 32'd0;
      write_accept_count_q <= 32'd0;
      rvalid_count_q <= 32'd0;
      rready_count_q <= 32'd0;
      read_accept_count_q <= 32'd0;
      depth_zero_count_q <= 32'd0;
      depth_one_count_q <= 32'd0;
      depth_full_count_q <= 32'd0;
      stalled_write_count_q <= 32'd0;
      stalled_read_count_q <= 32'd0;
      clear_count_q <= 32'd0;
      input_nonzero_count_q <= 32'd0;
      output_nonzero_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      match_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'hf1f0_a55a;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_rsp_data_hi_xor_i ^
                          cfg_req_family_i);
      last_wdata_q <= wdata_i;
      last_rdata_q <= rdata_o;

      if (read_accept_w || clr_i) begin
        pack_low_q <= '0;
        pack_high_q <= '0;
        pack_count_q <= '0;
      end else if (write_accept_w && pack_count_q == 2'd0) begin
        pack_low_q <= wdata_i;
        pack_count_q <= 2'd1;
      end else if (write_accept_w && pack_count_q == 2'd1) begin
        pack_high_q <= wdata_i;
        pack_count_q <= 2'd2;
      end

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        clr_i <= 1'b0;
        wvalid_i <= next_wvalid_w;
        wdata_i <= next_wdata_w;
        rready_i <= next_rready_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        clr_i <= 1'b0;
        wvalid_i <= 1'b0;
        wdata_i <= cfg_address_mask_i[7:0] ^ drain_cycle_q[7:0];
        rready_i <= 1'b1;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end else if (phase_w == ClearPhase) begin
        clear_cycle_q <= clear_cycle_q + 32'd1;
        clr_i <= clear_cycle_q == 32'd0;
        wvalid_i <= 1'b0;
        wdata_i <= cfg_seed_i[7:0] ^ clear_cycle_q[7:0];
        rready_i <= 1'b1;
        seen_q[2] <= 1'b1;
      end

      signature_q <= {signature_q[24:0], signature_q[31:25]} ^
                     rand_q ^ {24'd0, wdata_i} ^ {16'd0, rdata_o} ^
                     {22'd0, full_w, empty_w, clr_i, rready_i, rvalid_o,
                      wready_o, wvalid_i, phase_w};

      if (wvalid_i) begin wvalid_count_q <= wvalid_count_q + 32'd1; seen_q[3] <= 1'b1; end
      if (wready_o) begin wready_count_q <= wready_count_q + 32'd1; seen_q[4] <= 1'b1; end
      if (write_accept_w) begin write_accept_count_q <= write_accept_count_q + 32'd1; seen_q[5] <= 1'b1; end
      if (rvalid_o) begin rvalid_count_q <= rvalid_count_q + 32'd1; seen_q[6] <= 1'b1; end
      if (rready_i) begin rready_count_q <= rready_count_q + 32'd1; seen_q[7] <= 1'b1; end
      if (read_accept_w) begin read_accept_count_q <= read_accept_count_q + 32'd1; seen_q[8] <= 1'b1; end
      if (empty_w) begin depth_zero_count_q <= depth_zero_count_q + 32'd1; seen_q[9] <= 1'b1; end
      if (depth_o == 2'd1) begin depth_one_count_q <= depth_one_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (full_w) begin depth_full_count_q <= depth_full_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (stalled_write_w) begin stalled_write_count_q <= stalled_write_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (stalled_read_w) begin stalled_read_count_q <= stalled_read_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (clr_i) begin clear_count_q <= clear_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (|wdata_i) begin input_nonzero_count_q <= input_nonzero_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (|rdata_o) begin output_nonzero_count_q <= output_nonzero_count_q + 32'd1; seen_q[16] <= 1'b1; end
      if (input_changed_w) begin input_change_count_q <= input_change_count_q + 32'd1; seen_q[17] <= 1'b1; end
      if (output_changed_w) begin output_change_count_q <= output_change_count_q + 32'd1; seen_q[18] <= 1'b1; end
      if (observed_match_w) begin match_count_q <= match_count_q + 32'd1; seen_q[19] <= 1'b1; end
      if (!observed_match_w) begin mismatch_count_q <= mismatch_count_q + 32'd1; seen_q[20] <= 1'b1; end
      if (phase_w == ResetPhase) begin
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = signature_q ^ {31'd0, done_o} ^ progress_cycle_count_o;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q + clear_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {29'd0, phase_w};
  assign host_req_accepted_o = write_accept_count_q;
  assign device_req_accepted_o = read_accept_count_q;
  assign device_rsp_accepted_o = clear_count_q;
  assign host_rsp_accepted_o = rvalid_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;

  assign toggle_bitmap_word0_o = {
    wdata_i,
    rdata_o[7:0],
    rdata_o[15:8],
    6'd0,
    depth_o
  };
  assign toggle_bitmap_word1_o = {
    seen_q[15:0],
    6'd0,
    clr_i,
    rready_i,
    rvalid_o,
    wready_o,
    wvalid_i,
    depth_o,
    phase_w
  };
  assign toggle_bitmap_word2_o = {
    write_accept_count_q[5:0],
    read_accept_count_q[5:0],
    clear_count_q[5:0],
    depth_full_count_q[5:0],
    depth_o,
    phase_w,
    clr_i,
    rready_i,
    wvalid_i
  };

  assign real_toggle_subset_word0_o = wvalid_count_q;
  assign real_toggle_subset_word1_o = wready_count_q;
  assign real_toggle_subset_word2_o = write_accept_count_q;
  assign real_toggle_subset_word3_o = rvalid_count_q;
  assign real_toggle_subset_word4_o = rready_count_q;
  assign real_toggle_subset_word5_o = read_accept_count_q;
  assign real_toggle_subset_word6_o = depth_zero_count_q;
  assign real_toggle_subset_word7_o = depth_one_count_q;
  assign real_toggle_subset_word8_o = depth_full_count_q;
  assign real_toggle_subset_word9_o = stalled_write_count_q;
  assign real_toggle_subset_word10_o = stalled_read_count_q;
  assign real_toggle_subset_word11_o = clear_count_q;
  assign real_toggle_subset_word12_o = input_nonzero_count_q;
  assign real_toggle_subset_word13_o = output_nonzero_count_q;
  assign real_toggle_subset_word14_o = input_change_count_q;
  assign real_toggle_subset_word15_o = output_change_count_q;
  assign real_toggle_subset_word16_o = match_count_q;
  assign real_toggle_subset_word17_o = progress_signature_o;

  assign focused_wave_word0_o = {24'd0, wdata_i};
  assign focused_wave_word1_o = {16'd0, rdata_o};
  assign focused_wave_word2_o = {30'd0, depth_o};
  assign focused_wave_word3_o = {24'd0, expected_rdata_w[7:0]};
  assign focused_wave_word4_o = {16'd0, expected_rdata_w};
  assign focused_wave_word5_o = {21'd0, observed_match_w, full_w, empty_w,
                                 clr_i, rready_i, rvalid_o, wready_o,
                                 wvalid_i, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = write_accept_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = read_accept_count_q;
  assign oracle_observed_err_count_o = 32'd0;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    write_accept_count_q[7:0],
    read_accept_count_q[7:0],
    depth_full_count_q[7:0],
    clear_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {13'd0, wdata_i, 6'd0, depth_o, phase_w};
  assign oracle_semantic_case_acked_o = {rdata_o, expected_rdata_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_packer_fifo_gpu_cov_tb
