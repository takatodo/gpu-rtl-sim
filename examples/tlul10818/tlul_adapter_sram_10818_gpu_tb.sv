// Device-clean, clock-driven form of the OpenTitan #10818 reproducer.
//
// There are deliberately no initial blocks, delays, DPI calls, or pass/fail
// system tasks.  A host or GPU patch schedule owns clk_i/rst_ni/start_i.  The
// observable oracle_violation_o is state, not stdout authority.
module tlul_adapter_sram_10818_gpu_tb (
  input logic clk_i,
  input logic rst_ni,
  input logic start_i,
  input logic d_backpressure_i,
  output logic done_o,
  output logic oracle_violation_o,
  output logic [31:0] observed_d_data_o,
  output logic observed_d_error_o,
  output logic observed_intg_error_o
);
  import tlul_pkg::*;

  typedef enum logic [1:0] {Idle, Send, WaitD, Done} phase_e;
  phase_e phase_q;
  tl_h2d_t tl_i;
  tl_d2h_t tl_o;
  logic req_o;
  logic we_o;
  logic [3:0] addr_o;
  logic [31:0] wdata_o;
  logic [31:0] wmask_o;
  logic intg_error_o;

  always_comb begin
    tl_i = TL_H2D_DEFAULT;
    tl_i.d_ready = !d_backpressure_i && phase_q == WaitD;
    if (phase_q == Send) begin
      tl_i.a_valid = 1'b1;
      tl_i.a_opcode = Get;
      tl_i.a_size = 2'd2;
      tl_i.a_source = 8'h2a;
      tl_i.a_address = '0;
      tl_i.a_mask = 4'hf;
      tl_i.a_user = TL_A_USER_DEFAULT;
      tl_i.a_user.cmd_intg = '0; // malformed command integrity, issue #10818 trigger
    end
  end

  tlul_adapter_sram #(
    .SramAw(4), .SramDw(32), .Outstanding(1), .ByteAccess(1'b0),
    .CmdIntgCheck(1'b1), .DataWhenError(32'hffff_ffff)
  ) dut (
    .clk_i, .rst_ni, .tl_i, .tl_o,
    .en_ifetch_i(prim_mubi_pkg::MuBi4False),
    .req_o, .req_type_o(), .gnt_i(1'b1), .we_o, .addr_o, .wdata_o, .wmask_o,
    .intg_error_o, .rdata_i(32'h1234_5678), .rvalid_i(1'b0), .rerror_i(2'b00)
  );

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      phase_q <= Idle;
      done_o <= 1'b0;
      oracle_violation_o <= 1'b0;
      observed_d_data_o <= '0;
      observed_d_error_o <= 1'b0;
      observed_intg_error_o <= 1'b0;
    end else begin
      unique case (phase_q)
        Idle: if (start_i) phase_q <= Send;
        Send: if (tl_o.a_ready) phase_q <= WaitD;
        WaitD: if (tl_o.d_valid) begin
          observed_d_data_o <= tl_o.d_data;
          observed_d_error_o <= tl_o.d_error;
          observed_intg_error_o <= intg_error_o;
          oracle_violation_o <= !tl_o.d_error || tl_o.d_data != 32'hffff_ffff ||
                                req_o || !intg_error_o;
          done_o <= 1'b1;
          phase_q <= Done;
        end
        default: phase_q <= Done;
      endcase
    end
  end
endmodule
