// Reproducer for OpenTitan issue #10818.
//
// The bad revision returns zero rather than DataWhenError for an integrity
// failed TL-UL Get.  `action=0` accepts D immediately and `action=1` holds
// D ready until the response is visible, so both forms exercise the response
// state while keeping the assertion independent of coverage instrumentation.
module tlul_adapter_sram_10818_tb;
  import tlul_pkg::*;

  logic clk_i = 1'b0;
  logic rst_ni = 1'b0;
  tl_h2d_t tl_i;
  tl_d2h_t tl_o;
  logic req_o;
  logic we_o;
  logic [3:0] addr_o;
  logic [31:0] wdata_o;
  logic [31:0] wmask_o;
  logic intg_error_o;
  integer action;

  always #5 clk_i = ~clk_i;

  tlul_adapter_sram #(
    .SramAw(4), .SramDw(32), .Outstanding(1), .ByteAccess(1'b0),
    .CmdIntgCheck(1'b1), .DataWhenError(32'hffff_ffff)
  ) dut (
    .clk_i, .rst_ni, .tl_i, .tl_o,
    .en_ifetch_i(prim_mubi_pkg::MuBi4False),
    .req_o, .req_type_o(), .gnt_i(1'b1), .we_o, .addr_o, .wdata_o, .wmask_o,
    .intg_error_o, .rdata_i(32'h1234_5678), .rvalid_i(1'b0), .rerror_i(2'b00)
  );

  initial begin
    if (!$value$plusargs("action=%d", action)) action = 0;
    if (action < 0 || action > 1) $fatal(1, "unsupported action=%0d", action);
    tl_i = TL_H2D_DEFAULT;
    tl_i.d_ready = (action == 0);
    repeat (2) @(posedge clk_i);
    rst_ni = 1'b1;
    @(negedge clk_i);
    tl_i.a_valid = 1'b1;
    tl_i.a_opcode = Get;
    tl_i.a_size = 2'd2;
    tl_i.a_source = 8'h2a;
    tl_i.a_address = '0;
    tl_i.a_mask = 4'hf;
    tl_i.a_data = '0;
    tl_i.a_user = TL_A_USER_DEFAULT;
    tl_i.a_user.cmd_intg = '0;
    do @(posedge clk_i); while (!tl_o.a_ready);
    @(negedge clk_i);
    tl_i.a_valid = 1'b0;
    do @(posedge clk_i); while (!tl_o.d_valid);
    if (action == 1) @(posedge clk_i);
    if (!tl_o.d_valid || !tl_o.d_error || tl_o.d_data !== 32'hffff_ffff ||
        req_o || !intg_error_o) begin
      $display("RESULT status=fail action=%0d d_valid=%0d d_error=%0d d_data=%08x req_o=%0d intg_error_o=%0d",
               action, tl_o.d_valid, tl_o.d_error, tl_o.d_data, req_o, intg_error_o);
      $fatal(1, "TLUL10818 oracle violation");
    end
    $display("RESULT status=pass action=%0d d_data=%08x", action, tl_o.d_data);
    $finish;
  end
endmodule
