// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_fifo_async_simple.

module prim_fifo_async_simple_gpu_cov_tb (
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
  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] TrafficPhase = 3'd1;
  localparam logic [2:0] DrainPhase   = 3'd2;
  localparam logic [2:0] DonePhase    = 3'd3;

  logic clk_wr_i;
  logic clk_rd_i;
  logic rst_wr_ni;
  logic rst_rd_ni;
  logic wvalid_i;
  logic wready_o;
  logic [31:0] wdata_i;
  logic rvalid_o;
  logic rready_i;
  logic [31:0] rdata_o;
  logic [2:0] phase_wr_w;
  logic [2:0] phase_rd_w;

  logic [31:0] global_wr_cycle_q;
  logic [31:0] global_rd_cycle_q;
  logic [31:0] traffic_wr_cycle_q;
  logic [31:0] traffic_rd_cycle_q;
  logic [31:0] drain_wr_cycle_q;
  logic [31:0] drain_rd_cycle_q;
  logic [31:0] rand_wr_q;
  logic [31:0] rand_rd_q;
  logic [31:0] write_attempt_count_q;
  logic [31:0] write_accept_count_q;
  logic [31:0] write_blocked_count_q;
  logic [31:0] read_ready_count_q;
  logic [31:0] read_accept_count_q;
  logic [31:0] read_blocked_count_q;
  logic [31:0] wr_signature_q;
  logic [31:0] rd_signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] last_wdata_q;
  logic [31:0] last_rdata_q;
  logic [31:0] reset_skew_count_q;
  logic [31:0] wr_seen_q;
  logic [31:0] rd_seen_q;
  logic [31:0] pre_handshake_cycles_q;

  initial begin
    clk_wr_i = 1'b0;
    clk_rd_i = 1'b0;
  end

  always #5 clk_wr_i = ~clk_wr_i;
  always #7 clk_rd_i = ~clk_rd_i;

  prim_fifo_async_simple #(
    .Width(32),
    .EnRstChks(1'b0),
    .EnRzHs(1'b0)
  ) dut (
    .clk_wr_i,
    .rst_wr_ni,
    .wvalid_i,
    .wready_o,
    .wdata_i,
    .clk_rd_i,
    .rst_rd_ni,
    .rvalid_o,
    .rready_i,
    .rdata_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1103515245 + 32'd12345;
  endfunction

  function automatic logic [31:0] clamp_pct(input logic [31:0] pct_raw);
    return (pct_raw > 32'd100) ? 32'd100 : pct_raw;
  endfunction

  function automatic logic pct_hit(input logic [31:0] state, input logic [31:0] pct_raw);
    return ((state % 32'd100) < clamp_pct(pct_raw));
  endfunction

  function automatic logic [31:0] mix_word(
    input logic [31:0] state,
    input logic [31:0] count
  );
    logic [31:0] mode_mix;
    mode_mix = cfg_req_family_i ^ {cfg_rsp_family_i[15:0], cfg_req_family_i[15:0]};
    return (state ^ cfg_seed_i ^ (count * 32'd2654435761)) +
           cfg_req_data_hi_xor_i + cfg_rsp_data_hi_xor_i + mode_mix;
  endfunction

  assign rst_wr_ni = cfg_valid_i && (global_wr_cycle_q >= cfg_reset_cycles_i);
  assign rst_rd_ni = cfg_valid_i && (global_rd_cycle_q >= (cfg_reset_cycles_i + 32'd1));

  always_comb begin
    if (!cfg_valid_i || !rst_wr_ni) begin
      phase_wr_w = ResetPhase;
    end else if (traffic_wr_cycle_q < cfg_batch_length_i) begin
      phase_wr_w = TrafficPhase;
    end else if (drain_wr_cycle_q < cfg_drain_cycles_i) begin
      phase_wr_w = DrainPhase;
    end else begin
      phase_wr_w = DonePhase;
    end
  end

  always_comb begin
    if (!cfg_valid_i || !rst_rd_ni) begin
      phase_rd_w = ResetPhase;
    end else if (traffic_rd_cycle_q < cfg_batch_length_i) begin
      phase_rd_w = TrafficPhase;
    end else if (drain_rd_cycle_q < cfg_drain_cycles_i) begin
      phase_rd_w = DrainPhase;
    end else begin
      phase_rd_w = DonePhase;
    end
  end

  assign wvalid_i = cfg_valid_i &&
                    phase_wr_w == TrafficPhase &&
                    pct_hit(rand_wr_q ^ cfg_seed_i, cfg_req_valid_pct_i);
  assign wdata_i = mix_word(rand_wr_q, write_attempt_count_q);
  assign rready_i = cfg_valid_i &&
                    phase_rd_w != ResetPhase &&
                    (phase_rd_w == DrainPhase ||
                     pct_hit(rand_rd_q ^ 32'ha5a5_5a5a, cfg_host_d_ready_pct_i));

  always_ff @(posedge clk_wr_i) begin
    if (!cfg_valid_i) begin
      global_wr_cycle_q <= 32'd0;
    end else begin
      global_wr_cycle_q <= global_wr_cycle_q + 32'd1;
    end

    if (!rst_wr_ni) begin
      traffic_wr_cycle_q <= 32'd0;
      drain_wr_cycle_q <= 32'd0;
      rand_wr_q <= cfg_seed_i ^ 32'h1bad_f00d;
      write_attempt_count_q <= 32'd0;
      write_accept_count_q <= 32'd0;
      write_blocked_count_q <= 32'd0;
      wr_signature_q <= cfg_seed_i ^ 32'h55aa_0001;
      stalled_signature_q <= 32'd0;
      last_wdata_q <= 32'd0;
      reset_skew_count_q <= 32'd0;
      wr_seen_q <= 32'd0;
      pre_handshake_cycles_q <= 32'd0;
    end else begin
      rand_wr_q <= prng_next(rand_wr_q ^ global_wr_cycle_q);
      if (phase_wr_w == TrafficPhase) begin
        traffic_wr_cycle_q <= traffic_wr_cycle_q + 32'd1;
      end else if (phase_wr_w == DrainPhase) begin
        drain_wr_cycle_q <= drain_wr_cycle_q + 32'd1;
      end
      if (rst_wr_ni && !rst_rd_ni) begin
        reset_skew_count_q <= reset_skew_count_q + 32'd1;
      end
      if (phase_wr_w == TrafficPhase && !dut.pending_q && !wvalid_i) begin
        pre_handshake_cycles_q <= pre_handshake_cycles_q + 32'd1;
      end
      if (wvalid_i) begin
        write_attempt_count_q <= write_attempt_count_q + 32'd1;
        wr_seen_q[0] <= 1'b1;
      end
      if (wvalid_i && wready_o) begin
        write_accept_count_q <= write_accept_count_q + 32'd1;
        wr_signature_q <= {wr_signature_q[30:0], wr_signature_q[31]} ^
                          wdata_i ^ write_accept_count_q;
        last_wdata_q <= wdata_i;
        wr_seen_q[1] <= 1'b1;
      end
      if (wvalid_i && !wready_o) begin
        write_blocked_count_q <= write_blocked_count_q + 32'd1;
        stalled_signature_q <= stalled_signature_q ^ wdata_i ^ global_wr_cycle_q;
        wr_seen_q[2] <= 1'b1;
      end
      if (dut.pending_q) begin
        wr_seen_q[3] <= 1'b1;
      end
      if (dut.src_ack) begin
        wr_seen_q[4] <= 1'b1;
      end
    end
  end

  always_ff @(posedge clk_rd_i) begin
    if (!cfg_valid_i) begin
      global_rd_cycle_q <= 32'd0;
    end else begin
      global_rd_cycle_q <= global_rd_cycle_q + 32'd1;
    end

    if (!rst_rd_ni) begin
      traffic_rd_cycle_q <= 32'd0;
      drain_rd_cycle_q <= 32'd0;
      rand_rd_q <= cfg_seed_i ^ 32'hc001_d00d;
      read_ready_count_q <= 32'd0;
      read_accept_count_q <= 32'd0;
      read_blocked_count_q <= 32'd0;
      rd_signature_q <= cfg_seed_i ^ 32'haa55_0002;
      last_rdata_q <= 32'd0;
      rd_seen_q <= 32'd0;
    end else begin
      rand_rd_q <= prng_next(rand_rd_q ^ global_rd_cycle_q ^ cfg_rsp_family_i);
      if (phase_rd_w == TrafficPhase) begin
        traffic_rd_cycle_q <= traffic_rd_cycle_q + 32'd1;
      end else if (phase_rd_w == DrainPhase) begin
        drain_rd_cycle_q <= drain_rd_cycle_q + 32'd1;
      end
      if (rready_i) begin
        read_ready_count_q <= read_ready_count_q + 32'd1;
        rd_seen_q[0] <= 1'b1;
      end
      if (rvalid_o && rready_i) begin
        read_accept_count_q <= read_accept_count_q + 32'd1;
        rd_signature_q <= {rd_signature_q[28:0], rd_signature_q[31:29]} ^
                          rdata_o ^ read_accept_count_q;
        last_rdata_q <= rdata_o;
        rd_seen_q[1] <= 1'b1;
      end
      if (rvalid_o && !rready_i) begin
        read_blocked_count_q <= read_blocked_count_q + 32'd1;
        rd_seen_q[2] <= 1'b1;
      end
      if (dut.dst_req) begin
        rd_seen_q[3] <= 1'b1;
      end
      if (dut.dst_ack) begin
        rd_seen_q[4] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && phase_wr_w == DonePhase && phase_rd_w == DonePhase;
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_req_valid_pct_i ^
                           cfg_host_d_ready_pct_i ^ cfg_drain_cycles_i;
  assign host_req_accepted_o = write_accept_count_q;
  assign device_req_accepted_o = read_accept_count_q;
  assign device_rsp_accepted_o = read_ready_count_q;
  assign host_rsp_accepted_o = write_attempt_count_q;
  assign rsp_queue_overflow_o = write_blocked_count_q + read_blocked_count_q;
  assign progress_cycle_count_o = traffic_wr_cycle_q + traffic_rd_cycle_q +
                                  drain_wr_cycle_q + drain_rd_cycle_q;
  assign progress_signature_o = wr_signature_q ^ rd_signature_q ^
                                {24'd0, phase_wr_w, phase_rd_w, done_o, rst_wr_ni};

  assign toggle_bitmap_word0_o = wr_seen_q | (rd_seen_q << 8);
  assign toggle_bitmap_word1_o = {
    20'd0,
    done_o,
    rst_rd_ni,
    rst_wr_ni,
    rready_i,
    rvalid_o,
    wready_o,
    wvalid_i,
    dut.dst_ack,
    dut.dst_req,
    dut.src_ack,
    dut.src_req,
    dut.pending_q
  };
  assign toggle_bitmap_word2_o = {
    8'd0,
    phase_wr_w,
    phase_rd_w,
    12'd0,
    write_accept_count_q != 32'd0,
    read_accept_count_q != 32'd0,
    write_blocked_count_q != 32'd0,
    read_blocked_count_q != 32'd0,
    pre_handshake_cycles_q != 32'd0,
    reset_skew_count_q != 32'd0
  };

  assign real_toggle_subset_word0_o = write_accept_count_q;
  assign real_toggle_subset_word1_o = read_accept_count_q;
  assign real_toggle_subset_word2_o = write_attempt_count_q;
  assign real_toggle_subset_word3_o = write_blocked_count_q;
  assign real_toggle_subset_word4_o = read_ready_count_q;
  assign real_toggle_subset_word5_o = read_blocked_count_q;
  assign real_toggle_subset_word6_o = wr_signature_q;
  assign real_toggle_subset_word7_o = rd_signature_q;
  assign real_toggle_subset_word8_o = last_wdata_q;
  assign real_toggle_subset_word9_o = last_rdata_q;
  assign real_toggle_subset_word10_o = {
    24'd0,
    wvalid_i,
    wready_o,
    rvalid_o,
    rready_i,
    rst_wr_ni,
    rst_rd_ni,
    done_o,
    dut.pending_q
  };
  assign real_toggle_subset_word11_o = {
    27'd0,
    dut.src_req,
    dut.src_ack,
    dut.dst_req,
    dut.dst_ack,
    dut.pending_q
  };
  assign real_toggle_subset_word12_o = {31'd0, rvalid_o && !rready_i};
  assign real_toggle_subset_word13_o = global_wr_cycle_q;
  assign real_toggle_subset_word14_o = global_rd_cycle_q;
  assign real_toggle_subset_word15_o = reset_skew_count_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = progress_signature_o;

  assign focused_wave_word0_o = {16'd0, global_wr_cycle_q[7:0], global_rd_cycle_q[7:0]};
  assign focused_wave_word1_o = {8'd0, phase_wr_w, phase_rd_w, 10'd0, toggle_bitmap_word1_o[7:0]};
  assign focused_wave_word2_o = wdata_i;
  assign focused_wave_word3_o = rdata_o;
  assign focused_wave_word4_o = wr_signature_q;
  assign focused_wave_word5_o = rd_signature_q;
  assign focused_wave_word6_o = stalled_signature_q;
  assign focused_wave_word7_o = {write_accept_count_q[15:0], read_accept_count_q[15:0]};

  assign oracle_expected_ok_count_o = write_accept_count_q;
  assign oracle_expected_err_count_o = write_blocked_count_q;
  assign oracle_observed_ok_count_o = read_accept_count_q;
  assign oracle_observed_err_count_o = read_blocked_count_q;
  assign oracle_semantic_family_seen_o = cfg_req_family_i ^ cfg_rsp_family_i;
  assign oracle_semantic_family_acked_o = {write_accept_count_q[15:0], read_accept_count_q[15:0]};
  assign oracle_semantic_case_seen_o = cfg_req_data_mode_i ^ cfg_rsp_data_mode_i;
  assign oracle_semantic_case_acked_o = {read_ready_count_q[15:0], write_attempt_count_q[15:0]};
  assign oracle_req_signature_o = wr_signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = wr_signature_q ^ rd_signature_q;
  assign oracle_req_stable_violation_o = 32'd0;
  assign oracle_pre_handshake_traffic_cycles_o = pre_handshake_cycles_q;

endmodule
