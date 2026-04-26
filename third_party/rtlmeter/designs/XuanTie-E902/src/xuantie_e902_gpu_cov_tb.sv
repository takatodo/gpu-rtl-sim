// SPDX-License-Identifier: Apache-2.0
//
// Coarse gpu_cov wrapper for XuanTie-E902.
// Reuses the stock tb and exports progress/toggle proxies through the
// fixed output contract expected by the metrics-driven gpu toggle flow.

module xuantie_e902_gpu_cov_tb (
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

  tb dut();

  logic        retire_seen_w;
  logic        bus_access_w;
  logic        read_access_w;
  logic        write_access_w;
  logic        finish_addr_write_w;
  logic        pass_write_w;
  logic        fail_write_w;
  logic        char_write_w;
  logic [31:0] cfg_signature_q;
  logic [17:0] seen_bits_q;
  logic        done_q;
  logic [31:0] retire_count_q;
  logic [31:0] bus_access_count_q;
  logic [31:0] read_count_q;
  logic [31:0] write_count_q;
  logic [31:0] finish_count_q;
  logic [31:0] simaccel_mem_loaded_q;

  always_comb begin
    retire_seen_w      = dut.x_soc.x_cpu_sub_system_ahb.biu_pad_retire;
    bus_access_w       = dut.cpu_trans[1];
    read_access_w      = dut.cpu_trans[1] && !dut.cpu_write;
    write_access_w     = dut.cpu_trans[1] && dut.cpu_write;
    finish_addr_write_w = (dut.cpu_trans == 2'b10)
                       && dut.cpu_write
                       && (dut.cpu_addr == 32'h6000fff8);
    pass_write_w       = finish_addr_write_w
                       && ((dut.cpu_wdata == 32'h00000fff) || (dut.cpu_wdata == 32'hffff0000));
    fail_write_w       = finish_addr_write_w
                       && ((dut.cpu_wdata == 32'h00000eee) || (dut.cpu_wdata == 32'heeee0000));
    char_write_w       = finish_addr_write_w && !pass_write_w && !fail_write_w;
    cfg_signature_q    = cfg_batch_length_i
                       ^ cfg_seed_i
                       ^ cfg_reset_cycles_i
                       ^ cfg_drain_cycles_i
                       ^ cfg_req_family_i
                       ^ cfg_rsp_family_i
                       ^ cfg_address_base_i
                       ^ cfg_address_mask_i
                       ^ cfg_source_mask_i
                       ^ {31'd0, cfg_valid_i};
    // The stock XuanTie-E902 tb does not expose a simaccel-specific memory-load
    // flag. Use a constant loaded state so focused-wave packing still compiles.
    simaccel_mem_loaded_q = 32'd1;
  end

  always_ff @(posedge dut.clk or negedge dut.rst_b) begin
    if (!dut.rst_b) begin
      seen_bits_q        <= '0;
      done_q             <= 1'b0;
      retire_count_q     <= '0;
      bus_access_count_q <= '0;
      read_count_q       <= '0;
      write_count_q      <= '0;
      finish_count_q     <= '0;
    end else begin
      seen_bits_q[0] <= 1'b1;
      if (retire_seen_w) begin
        retire_count_q <= retire_count_q + 32'd1;
        seen_bits_q[1] <= 1'b1;
      end
      if (retire_count_q >= 32'd16) begin
        seen_bits_q[2] <= 1'b1;
      end
      if (bus_access_w) begin
        bus_access_count_q <= bus_access_count_q + 32'd1;
        seen_bits_q[3] <= 1'b1;
      end
      if (read_access_w) begin
        read_count_q <= read_count_q + 32'd1;
        seen_bits_q[4] <= 1'b1;
      end
      if (write_access_w) begin
        write_count_q <= write_count_q + 32'd1;
        seen_bits_q[5] <= 1'b1;
      end
      if (finish_addr_write_w) begin
        finish_count_q <= finish_count_q + 32'd1;
        seen_bits_q[6] <= 1'b1;
      end
      if (pass_write_w) begin
        done_q <= 1'b1;
        seen_bits_q[7] <= 1'b1;
      end
      if (fail_write_w) begin
        done_q <= 1'b1;
        seen_bits_q[8] <= 1'b1;
      end
      if (char_write_w) begin
        seen_bits_q[9] <= 1'b1;
      end
      if (dut.cpu_addr[31:16] != 16'h0) begin
        seen_bits_q[10] <= 1'b1;
      end
      if (dut.cpu_wdata[31:16] != 16'h0) begin
        seen_bits_q[11] <= 1'b1;
      end
      if (dut.cpu_trans == 2'b11) begin
        seen_bits_q[12] <= 1'b1;
      end
      if ((dut.cpu_trans[1]) && (dut.cpu_addr[7:0] != 8'h0)) begin
        seen_bits_q[13] <= 1'b1;
      end
      if (dut.cycle_count >= 32'd1000) begin
        seen_bits_q[14] <= 1'b1;
      end
      if (finish_count_q >= 32'd4) begin
        seen_bits_q[15] <= 1'b1;
      end
      if (cfg_valid_i) begin
        seen_bits_q[16] <= 1'b1;
      end
      if (^cfg_signature_q) begin
        seen_bits_q[17] <= 1'b1;
      end
    end
  end

  assign cfg_signature_o        = cfg_signature_q;
  assign done_o                 = done_q;
  assign host_req_accepted_o    = bus_access_count_q;
  assign device_req_accepted_o  = read_count_q;
  assign device_rsp_accepted_o  = write_count_q;
  assign host_rsp_accepted_o    = retire_count_q;
  assign rsp_queue_overflow_o   = 32'd0;
  assign progress_cycle_count_o = dut.cycle_count;
  assign progress_signature_o   = cfg_signature_q
                                ^ dut.cycle_count
                                ^ retire_count_q
                                ^ bus_access_count_q
                                ^ read_count_q
                                ^ write_count_q
                                ^ finish_count_q
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

  assign focused_wave_word0_o = dut.cycle_count;
  assign focused_wave_word1_o = retire_count_q;
  assign focused_wave_word2_o = bus_access_count_q;
  assign focused_wave_word3_o = finish_count_q;
  assign focused_wave_word4_o = {
    28'd0,
    dut.rst_b,
    dut.x_soc.x_cpu_sub_system_ahb.x_e902.trst_b,
    dut.x_soc.x_cpu_sub_system_ahb.x_e902.hadrst_b,
    dut.x_soc.x_cpu_sub_system_ahb.biu_pad_retire
  };
  assign focused_wave_word5_o = {28'd0, simaccel_mem_loaded_q[1:0], dut.cpu_trans[1:0]};
  assign focused_wave_word6_o = dut.cpu_addr;
  assign focused_wave_word7_o = progress_signature_o;

endmodule
