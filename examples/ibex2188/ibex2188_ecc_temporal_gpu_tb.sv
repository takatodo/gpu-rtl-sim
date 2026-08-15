// Device-clean, clock-driven form of the Ibex #2188 reproducer.
//
// Deliberately no initial blocks, delays, DPI calls, or pass/fail system
// tasks.  A host or GPU patch schedule owns clk_i/rst_ni.  The oracle and
// semantic observables are state, not stdout authority.  The instruction
// memory is a combinational ROM and the register file is reset to the ECC
// encoding of zero so the bad/fixed register-file alert predicates run.
// FuseSoC normally generates this implementation-selection wrapper.  Keeping
// the generic mapping local makes the direct GPU runner independent of a
// FuseSoC installation without changing the pinned Ibex checkout.
module prim_buf #(
  parameter int Width = 1
) (
  input [Width-1:0] in_i,
  output logic [Width-1:0] out_o
);
  prim_generic_buf #(.Width(Width)) impl (.in_i, .out_o);
endmodule

module ibex2188_ecc_temporal_gpu_tb (
  input logic clk_i,
  input logic rst_ni,
  input logic fault_enable_i,
  input logic [4:0] fault_bit_i,
  input logic [1:0] load_response_delay_i,
  input logic inject_port_b_i,
  output logic done_o,
  output logic oracle_violation_o,
  output logic fault_seen_o,
  output logic alert_seen_o,
  output logic rf_read_enable_o,
  output logic rf_wb_match_o,
  output logic rf_write_wb_o,
  output logic rf_ecc_error_id_o,
  output logic instruction_valid_id_o,
  output logic alert_major_internal_o
);
  import ibex_pkg::*;

  logic instr_req_o;
  logic instr_gnt_i;
  logic instr_rvalid_i;
  logic [31:0] instr_addr_o;
  logic [31:0] instr_rdata_i;
  logic instr_err_i;
  logic instr_pending_q;
  logic [31:0] instr_addr_q;

  logic data_req_o;
  logic data_gnt_i;
  logic data_rvalid_i;
  logic data_we_o;
  logic [3:0] data_be_o;
  logic [31:0] data_addr_o;
  logic [31:0] data_wdata_o;
  logic [31:0] data_rdata_i;
  logic data_err_i;
  logic data_pending_q;

  logic dummy_instr_id_o;
  logic dummy_instr_wb_o;
  logic [4:0] rf_raddr_a_o;
  logic [4:0] rf_raddr_b_o;
  logic [4:0] rf_waddr_wb_o;
  logic rf_we_wb_o;
  logic [38:0] rf_wdata_wb_ecc_o;
  logic [38:0] rf_rdata_a_ecc_i;
  logic [38:0] rf_rdata_b_ecc_i;
  logic [31:0][38:0] register_file;

  logic [IC_NUM_WAYS-1:0] ic_tag_req_o;
  logic ic_tag_write_o;
  logic [IC_INDEX_W-1:0] ic_tag_addr_o;
  logic [IC_TAG_SIZE-1:0] ic_tag_wdata_o;
  logic [IC_TAG_SIZE-1:0] ic_tag_rdata_i [IC_NUM_WAYS];
  logic [IC_NUM_WAYS-1:0] ic_data_req_o;
  logic ic_data_write_o;
  logic [IC_INDEX_W-1:0] ic_data_addr_o;
  logic [IC_LINE_SIZE-1:0] ic_data_wdata_o;
  logic [IC_LINE_SIZE-1:0] ic_data_rdata_i [IC_NUM_WAYS];
  logic ic_scr_key_valid_i;
  logic ic_scr_key_req_o;

  logic irq_software_i;
  logic irq_timer_i;
  logic irq_external_i;
  logic [14:0] irq_fast_i;
  logic irq_nm_i;
  logic irq_pending_o;
  logic debug_req_i;
  crash_dump_t crash_dump_o;
  logic double_fault_seen_o;
  ibex_mubi_t fetch_enable_i;
  logic alert_minor_o;
  logic alert_major_internal_int;
  logic alert_major_bus_o;
  ibex_mubi_t core_busy_o;

  logic fault_active;
  logic fault_seen_q;
  logic alert_seen_q;
  logic load_writeback_seen_q;
  logic observed_rf_read_enable_q;
  logic observed_rf_wb_match_q;
  logic observed_rf_write_wb_q;
  logic observed_rf_ecc_error_id_q;
  logic observed_instruction_valid_id_q;
  logic observed_alert_major_internal_q;
  logic [38:0] rf_a_clean;
  logic [38:0] rf_b_clean;

  function automatic logic [31:0] instruction_word(input logic [31:0] address);
    case (address)
      // addi x8, x0, 256; addi x15, x0, 2
      32'h0000_0080: instruction_word = 32'h1000_0413;
      32'h0000_0084: instruction_word = 32'h0020_0793;
      // lw x14, -20(x8); blt x14, x15, +8
      32'h0000_0088: instruction_word = 32'hfec4_2703;
      32'h0000_008c: instruction_word = 32'h00f7_4463;
      32'h0000_0090: instruction_word = 32'h0000_0513;
      32'h0000_0094: instruction_word = 32'h0000_006f;
      default: instruction_word = 32'h0000_0013;
    endcase
  endfunction

  assign instr_gnt_i = instr_req_o;
  assign instr_rvalid_i = instr_pending_q;
  assign instr_rdata_i = instruction_word(instr_addr_q);
  assign instr_err_i = 1'b0;
  assign data_gnt_i = data_req_o;
  assign data_rvalid_i = load_response_delay_i == 0 ? data_req_o : data_pending_q;
  assign data_rdata_i = 32'h0000_0001;
  assign data_err_i = 1'b0;
  assign rf_a_clean = register_file[rf_raddr_a_o];
  assign rf_b_clean = register_file[rf_raddr_b_o];

  always_comb begin
    rf_rdata_a_ecc_i = rf_a_clean;
    rf_rdata_b_ecc_i = rf_b_clean;
    fault_active = 1'b0;
    if (fault_enable_i && !fault_seen_q && core_i.rf_write_wb == 1'b0) begin
      if (!inject_port_b_i && core_i.rf_ren_a && core_i.rf_rd_a_wb_match) begin
        rf_rdata_a_ecc_i = rf_a_clean ^ ({38'b0, 1'b1} << fault_bit_i);
        fault_active = 1'b1;
      end
      if (inject_port_b_i && core_i.rf_ren_b && core_i.rf_rd_b_wb_match) begin
        rf_rdata_b_ecc_i = rf_b_clean ^ ({38'b0, 1'b1} << fault_bit_i);
        fault_active = 1'b1;
      end
    end
  end

  // Fixed control inputs that the CPU wrapper drove in its initial block.
  assign fetch_enable_i = IbexMuBiOn;
  assign ic_scr_key_valid_i = 1'b0;
  assign irq_software_i = 1'b0;
  assign irq_timer_i = 1'b0;
  assign irq_external_i = 1'b0;
  assign irq_fast_i = '0;
  assign irq_nm_i = 1'b0;
  assign debug_req_i = 1'b0;

  ibex_core #(
    .BranchTargetALU (1'b1),
    .WritebackStage (1'b1),
    .SecureIbex     (1'b1),
    .RegFileECC     (1'b1),
    .RegFileDataWidth(39)
  ) core_i (
    .clk_i,
    .rst_ni,
    .hart_id_i(32'b0),
    .boot_addr_i(32'h0000_0080),
    .instr_req_o,
    .instr_gnt_i,
    .instr_rvalid_i,
    .instr_addr_o,
    .instr_rdata_i,
    .instr_err_i,
    .data_req_o,
    .data_gnt_i,
    .data_rvalid_i,
    .data_we_o,
    .data_be_o,
    .data_addr_o,
    .data_wdata_o,
    .data_rdata_i,
    .data_err_i,
    .dummy_instr_id_o,
    .dummy_instr_wb_o,
    .rf_raddr_a_o,
    .rf_raddr_b_o,
    .rf_waddr_wb_o,
    .rf_we_wb_o,
    .rf_wdata_wb_ecc_o,
    .rf_rdata_a_ecc_i,
    .rf_rdata_b_ecc_i,
    .ic_tag_req_o,
    .ic_tag_write_o,
    .ic_tag_addr_o,
    .ic_tag_wdata_o,
    .ic_tag_rdata_i,
    .ic_data_req_o,
    .ic_data_write_o,
    .ic_data_addr_o,
    .ic_data_wdata_o,
    .ic_data_rdata_i,
    .ic_scr_key_valid_i,
    .ic_scr_key_req_o,
    .irq_software_i,
    .irq_timer_i,
    .irq_external_i,
    .irq_fast_i,
    .irq_nm_i,
    .irq_pending_o,
    .debug_req_i,
    .crash_dump_o,
    .double_fault_seen_o,
    .fetch_enable_i,
    .alert_minor_o,
    .alert_major_internal_o(alert_major_internal_int),
    .alert_major_bus_o,
    .core_busy_o
  );

  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      instr_pending_q <= 1'b0;
      instr_addr_q <= 32'b0;
      data_pending_q <= 1'b0;
      fault_seen_q <= 1'b0;
      alert_seen_q <= 1'b0;
      load_writeback_seen_q <= 1'b0;
      observed_rf_read_enable_q <= 1'b0;
      observed_rf_wb_match_q <= 1'b0;
      observed_rf_write_wb_q <= 1'b0;
      observed_rf_ecc_error_id_q <= 1'b0;
      observed_instruction_valid_id_q <= 1'b0;
      observed_alert_major_internal_q <= 1'b0;
      for (int unsigned index = 0; index < 32; index++) begin
        register_file[index] <= prim_secded_pkg::prim_secded_inv_39_32_enc(32'b0);
      end
    end else begin
      instr_pending_q <= instr_req_o;
      if (instr_req_o) instr_addr_q <= instr_addr_o;
      data_pending_q <= data_req_o;
      if (rf_we_wb_o && (rf_waddr_wb_o != 5'b0)) begin
        register_file[rf_waddr_wb_o] <= rf_wdata_wb_ecc_o;
      end
      if (fault_active) fault_seen_q <= 1'b1;
      if (alert_major_internal_int) alert_seen_q <= 1'b1;
      if (core_i.rf_write_wb && rf_waddr_wb_o == 5'd14) load_writeback_seen_q <= 1'b1;
      if (fault_active) begin
        observed_rf_read_enable_q <= inject_port_b_i ? core_i.rf_ren_b : core_i.rf_ren_a;
        observed_rf_wb_match_q <= inject_port_b_i ? core_i.rf_rd_b_wb_match : core_i.rf_rd_a_wb_match;
        observed_rf_write_wb_q <= core_i.rf_write_wb;
        observed_rf_ecc_error_id_q <= inject_port_b_i ?
            core_i.gen_regfile_ecc.rf_ecc_err_b_id : core_i.gen_regfile_ecc.rf_ecc_err_a_id;
        observed_instruction_valid_id_q <= core_i.instr_valid_id;
        observed_alert_major_internal_q <= alert_major_internal_int;
      end
    end
  end

  // done_o is a bounded schedule end: the fault was injected (or the load
  // writeback completed) and the oracle/observables are latched.  The host
  // keeps clocking until done_o; there is no $finish.
  assign done_o = fault_enable_i ?
      (fault_seen_q || (load_writeback_seen_q && core_i.rf_write_wb)) :
      load_writeback_seen_q;

  assign oracle_violation_o = fault_seen_q && !alert_seen_q;
  assign fault_seen_o = fault_seen_q;
  assign alert_seen_o = alert_seen_q;
  assign rf_read_enable_o = observed_rf_read_enable_q;
  assign rf_wb_match_o = observed_rf_wb_match_q;
  assign rf_write_wb_o = observed_rf_write_wb_q;
  assign rf_ecc_error_id_o = observed_rf_ecc_error_id_q;
  assign instruction_valid_id_o = observed_instruction_valid_id_q;
  assign alert_major_internal_o = observed_alert_major_internal_q;

endmodule
