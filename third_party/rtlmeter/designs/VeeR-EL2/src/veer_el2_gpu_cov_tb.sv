// SPDX-License-Identifier: Apache-2.0
//
// GPU-oriented coverage wrapper for VeeR-EL2.
// This is a first-pass contract target that reuses tb_top and exports
// lightweight progress/toggle proxies through fixed output words.

module veer_el2_gpu_cov_tb (
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
  output logic [31:0] focused_wave_word7_o
);

  tb_top dut();

  logic [31:0] host_req_accepted_q;
  logic [31:0] device_req_accepted_q;
  logic [31:0] device_rsp_accepted_q;
  logic [31:0] host_rsp_accepted_q;
  logic [17:0] seen_bits_q;
  logic        pass_seen_q;
  logic        fail_seen_q;
  logic [31:0] cycle_count_q;
  logic [31:0] commit_count_q;
  logic [31:0] cfg_signature_q;

  logic if_req_accept;
  logic if_rsp_accept;
  logic lsu_req_accept;
  logic lsu_rsp_accept;
  logic lsu_write_accept;
  logic lsu_read_accept;

`ifdef RV_BUILD_AXI4
  always_comb begin
    if_req_accept  = dut.ifu_axi_arvalid && dut.ifu_axi_arready;
    if_rsp_accept  = dut.ifu_axi_rvalid && dut.ifu_axi_rready;
    lsu_req_accept = (dut.lsu_axi_arvalid && dut.lsu_axi_arready)
                  || (dut.lsu_axi_awvalid && dut.lsu_axi_awready);
    lsu_rsp_accept = (dut.lsu_axi_rvalid && dut.lsu_axi_rready)
                  || (dut.lsu_axi_bvalid && dut.lsu_axi_bready);
    lsu_write_accept = dut.lsu_axi_awvalid && dut.lsu_axi_awready;
    lsu_read_accept  = dut.lsu_axi_arvalid && dut.lsu_axi_arready;
  end
`else
  always_comb begin
    if_req_accept  = dut.ic_htrans[1] && dut.ic_hready;
    if_rsp_accept  = dut.ic_htrans[1] && dut.ic_hready;
    lsu_req_accept = dut.lsu_htrans[1] && dut.lsu_hready;
    lsu_rsp_accept = dut.lsu_htrans[1] && dut.lsu_hready;
    lsu_write_accept = dut.lsu_htrans[1] && dut.lsu_hready && dut.lsu_hwrite;
    lsu_read_accept  = dut.lsu_htrans[1] && dut.lsu_hready && !dut.lsu_hwrite;
  end
`endif

  logic [31:0] debug_status_word_q;
  logic [31:0] debug_bus_word_q;
  logic [31:0] debug_mailbox_word_q;
  logic [31:0] debug_counter_word_q;

  always_comb begin
    cfg_signature_q = cfg_batch_length_i ^ cfg_seed_i ^ cfg_reset_cycles_i ^ cfg_drain_cycles_i
                    ^ cfg_req_family_i ^ cfg_rsp_family_i ^ cfg_address_base_i ^ cfg_address_mask_i
                    ^ cfg_source_mask_i ^ {31'd0, cfg_valid_i};
  end

  always_ff @(posedge dut.core_clk or negedge dut.rst_l) begin
    if (!dut.rst_l) begin
      host_req_accepted_q   <= '0;
      device_req_accepted_q <= '0;
      device_rsp_accepted_q <= '0;
      host_rsp_accepted_q   <= '0;
      seen_bits_q           <= '0;
      pass_seen_q           <= 1'b0;
      fail_seen_q           <= 1'b0;
    end else begin
      if (if_req_accept) begin
        host_req_accepted_q <= host_req_accepted_q + 32'd1;
        seen_bits_q[0] <= 1'b1;
      end
      if (if_rsp_accept) begin
        host_rsp_accepted_q <= host_rsp_accepted_q + 32'd1;
        seen_bits_q[1] <= 1'b1;
      end
      if (lsu_req_accept) begin
        device_req_accepted_q <= device_req_accepted_q + 32'd1;
        seen_bits_q[2] <= 1'b1;
      end
      if (lsu_rsp_accept) begin
        device_rsp_accepted_q <= device_rsp_accepted_q + 32'd1;
        seen_bits_q[3] <= 1'b1;
      end
      if (dut.trace_rv_i_valid_ip) begin
        seen_bits_q[4] <= 1'b1;
      end
      if (dut.wb_valid) begin
        seen_bits_q[5] <= 1'b1;
      end
      if (dut.mailbox_write) begin
        seen_bits_q[6] <= 1'b1;
      end
      if (dut.trace_rv_i_exception_ip) begin
        seen_bits_q[7] <= 1'b1;
      end
      if (dut.trace_rv_i_interrupt_ip) begin
        seen_bits_q[8] <= 1'b1;
      end
      if (dut.trace_rv_i_address_ip[31:16] != 16'h0) begin
        seen_bits_q[9] <= 1'b1;
      end
      if (dut.trace_rv_i_insn_ip[31:16] != 16'h0) begin
        seen_bits_q[10] <= 1'b1;
      end
      if (lsu_write_accept) begin
        seen_bits_q[11] <= 1'b1;
      end
      if (lsu_read_accept) begin
        seen_bits_q[12] <= 1'b1;
      end
      if (dut.commit_count >= 32) begin
        seen_bits_q[13] <= 1'b1;
      end
      if (dut.commit_count >= 128) begin
        seen_bits_q[14] <= 1'b1;
      end
      if (dut.mailbox_write && dut.mailbox_data[7:0] == 8'hff) begin
        seen_bits_q[15] <= 1'b1;
        pass_seen_q <= 1'b1;
      end
      if (dut.mailbox_write && dut.mailbox_data[7:0] == 8'h01) begin
        seen_bits_q[16] <= 1'b1;
        fail_seen_q <= 1'b1;
      end
      if (dut.mailbox_data_val) begin
        seen_bits_q[17] <= 1'b1;
      end
    end
  end

  always_comb begin
    cycle_count_q  = dut.cycleCnt[31:0];
    commit_count_q = dut.commit_count[31:0];
    debug_status_word_q = dut.gpu_cov_debug_status_word;
    debug_bus_word_q = dut.gpu_cov_debug_bus_word;
    debug_mailbox_word_q = dut.gpu_cov_debug_mailbox_word;
    debug_counter_word_q = {
      host_req_accepted_q[7:0],
      host_rsp_accepted_q[7:0],
      device_req_accepted_q[7:0],
      device_rsp_accepted_q[7:0]
    };
  end

  assign cfg_signature_o       = cfg_signature_q;
  assign done_o                = pass_seen_q | fail_seen_q;
  assign host_req_accepted_o   = host_req_accepted_q;
  assign device_req_accepted_o = device_req_accepted_q;
  assign device_rsp_accepted_o = device_rsp_accepted_q;
  assign host_rsp_accepted_o   = host_rsp_accepted_q;
  assign rsp_queue_overflow_o  = 32'd0;
  assign progress_cycle_count_o = cycle_count_q;
  assign progress_signature_o   = cfg_signature_q
                                ^ cycle_count_q
                                ^ commit_count_q
                                ^ host_req_accepted_q
                                ^ device_req_accepted_q
                                ^ device_rsp_accepted_q
                                ^ host_rsp_accepted_q
                                ^ {14'd0, seen_bits_q};

  assign toggle_bitmap_word0_o = {26'd0, seen_bits_q[5:0]};
  assign toggle_bitmap_word1_o = {26'd0, seen_bits_q[11:6]};
  assign toggle_bitmap_word2_o = {26'd0, seen_bits_q[17:12]};

  assign real_toggle_subset_word0_o  = {31'd0, seen_bits_q[0]};
  assign real_toggle_subset_word1_o  = {31'd0, seen_bits_q[1]};
  assign real_toggle_subset_word2_o  = {31'd0, seen_bits_q[2]};
  assign real_toggle_subset_word3_o  = {31'd0, seen_bits_q[3]};
  assign real_toggle_subset_word4_o  = {31'd0, seen_bits_q[4]};
  assign real_toggle_subset_word5_o  = {31'd0, seen_bits_q[5]};
  assign real_toggle_subset_word6_o  = {31'd0, seen_bits_q[6]};
  assign real_toggle_subset_word7_o  = {31'd0, seen_bits_q[7]};
  assign real_toggle_subset_word8_o  = {31'd0, seen_bits_q[8]};
  assign real_toggle_subset_word9_o  = {31'd0, seen_bits_q[9]};
  assign real_toggle_subset_word10_o = {31'd0, seen_bits_q[10]};
  assign real_toggle_subset_word11_o = {31'd0, seen_bits_q[11]};
  assign real_toggle_subset_word12_o = {31'd0, seen_bits_q[12]};
  assign real_toggle_subset_word13_o = {31'd0, seen_bits_q[13]};
  assign real_toggle_subset_word14_o = {31'd0, seen_bits_q[14]};
  assign real_toggle_subset_word15_o = {31'd0, seen_bits_q[15]};
  assign real_toggle_subset_word16_o = {31'd0, seen_bits_q[16]};
  assign real_toggle_subset_word17_o = {31'd0, seen_bits_q[17]};

  assign focused_wave_word0_o = cycle_count_q;
  assign focused_wave_word1_o = commit_count_q;
  assign focused_wave_word2_o = dut.trace_rv_i_address_ip;
  assign focused_wave_word3_o = dut.trace_rv_i_insn_ip;
  // Keep debug words direct and sparse so dead-coverage bring-up can be read
  // without reverse-engineering packed status fields.
  assign focused_wave_word4_o = {
    19'd0,
    dut.gpu_cov_reset_phase_q,
    dut.gpu_cov_program_loaded_q,
    dut.gpu_cov_iterations_valid_q,
    dut.gpu_cov_halt_req_q,
    dut.gpu_cov_halt_done_q,
    dut.o_cpu_halt_ack,
    dut.o_cpu_halt_status,
    dut.gpu_cov_run_req_q,
    dut.gpu_cov_run_done_q
  };
  assign focused_wave_word5_o = {
    24'd0,
    dut.o_cpu_run_ack,
    dut.rst_l,
    dut.porst_l,
    dut.debug_brkpt_status,
    dut.mailbox_write,
    dut.mailbox_data_val,
    dut.trace_rv_i_valid_ip,
    dut.wb_valid
  };
  // Dead-coverage bring-up for VeeR is dominated by reset/run/fetch gating.
  // Expose core reset and IFU handshake directly so a single compact dump can
  // distinguish "run never issued", "core held in reset", and "fetch issued
  // but never accepted/responded".
  assign focused_wave_word6_o = {
    dut.ifu_axi_araddr[21:0],
    dut.wb_valid,
    dut.trace_rv_i_valid_ip,
    dut.gpu_cov_if_rsp_accept,
    dut.gpu_cov_if_req_accept,
    dut.ifu_axi_rready,
    dut.ifu_axi_rvalid,
    dut.ifu_axi_arready,
    dut.ifu_axi_arvalid,
    dut.rvtop_wrapper.rvtop.core_rst_l,
    dut.rvtop_wrapper.rvtop.veer.dbg_core_rst_l
  };
  // For dead-coverage bring-up, expose sticky handoff/activity state instead of
  // traffic counters so a single compact dump shows whether run/fetch ever
  // pulsed.
  assign focused_wave_word7_o = {16'd0, dut.gpu_cov_debug_sticky_q};

endmodule
