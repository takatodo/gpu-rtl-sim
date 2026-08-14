// Direct CPU reproducer for OpenTitan #23526.
//
// The EDN issues a software CSRNG command.  Once valid is asserted, the
// environment injects an error ACK while ready stays low.  The valid/ready
// protocol requires valid to remain asserted until ready is observed.
module edn_csrng_23526_tb;
  import prim_mubi_pkg::*;
  import csrng_pkg::*;

  logic clk_i = 1'b0;
  logic rst_ni = 1'b0;
  edn_reg_pkg::edn_reg2hw_t reg2hw;
  edn_reg_pkg::edn_hw2reg_t hw2reg;
  edn_pkg::edn_req_t [3:0] edn_i;
  edn_pkg::edn_rsp_t [3:0] edn_o;
  csrng_req_t csrng_cmd_o;
  csrng_rsp_t csrng_cmd_i;
  logic recov_alert_test_o, fatal_alert_test_o, recov_alert_o, fatal_alert_o;
  logic intr_edn_cmd_req_done_o, intr_edn_fatal_err_o;
  logic saw_valid, protocol_violation;

  always #5 clk_i = ~clk_i;

  edn_core dut (
    .clk_i, .rst_ni, .reg2hw, .hw2reg, .edn_i, .edn_o, .csrng_cmd_o, .csrng_cmd_i,
    .recov_alert_test_o, .fatal_alert_test_o, .recov_alert_o, .fatal_alert_o,
    .intr_edn_cmd_req_done_o, .intr_edn_fatal_err_o
  );

  initial begin
    reg2hw = '0;
    edn_i = '{default: '0};
    csrng_cmd_i = CSRNG_RSP_DEFAULT;
    repeat (2) @(posedge clk_i);
    rst_ni = 1'b1;
    reg2hw.ctrl.edn_enable.q = MuBi4True;
    reg2hw.ctrl.cmd_fifo_rst.q = MuBi4False;
    reg2hw.ctrl.auto_req_mode.q = MuBi4False;
    reg2hw.ctrl.boot_req_mode.q = MuBi4False;

    // Allow the synchronized enable and SW command port to become ready.
    repeat (5) @(posedge clk_i);
    reg2hw.sw_cmd_req.q = 32'h0000_0001; // Instantiate command header.
    reg2hw.sw_cmd_req.qe = 1'b1;
    @(posedge clk_i);
    reg2hw.sw_cmd_req.qe = 1'b0;

    // Wait until EDN has emitted valid, then inject an error without ready.
    wait (csrng_cmd_o.csrng_req_valid);
    @(negedge clk_i);
    saw_valid = csrng_cmd_o.csrng_req_valid;
    csrng_cmd_i.csrng_rsp_ack = 1'b1;
    csrng_cmd_i.csrng_rsp_sts = CMD_STS_INVALID_CMD_SEQ;
    csrng_cmd_i.csrng_req_ready = 1'b0;
    @(posedge clk_i);
    @(negedge clk_i);
    protocol_violation = saw_valid && !csrng_cmd_i.csrng_req_ready &&
                         !csrng_cmd_o.csrng_req_valid;
    $display("RESULT protocol_violation=%0d valid_after_error=%0d", protocol_violation,
             csrng_cmd_o.csrng_req_valid);
    $finish;
  end
endmodule
