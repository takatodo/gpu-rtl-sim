// Device-clean, clock-driven form of the OpenTitan #23526 EDN reproducer.
//
// The direct CPU reproducer uses initial blocks and wait statements.  This
// wrapper exposes the same protocol scenario as explicit clocked state so the
// hybrid runtime can drive it with a resident patch schedule.
module edn_csrng_23526_gpu_tb (
  input logic clk_i,
  input logic rst_ni,
  input logic start_i,
  output logic done_o,
  output logic protocol_violation_o,
  output logic valid_after_error_o,
  output logic csrng_req_valid_seen_o,
  output logic [0:0] action_coverage_o
);
  import prim_mubi_pkg::*;
  import csrng_pkg::*;

  typedef enum logic [2:0] {Idle, EnableWait, SendSwCmd, WaitValid, InjectError, Check, Done} phase_e;

  phase_e phase_q;
  logic [2:0] enable_wait_q;
  edn_reg_pkg::edn_reg2hw_t reg2hw;
  edn_reg_pkg::edn_hw2reg_t hw2reg;
  edn_pkg::edn_req_t [3:0] edn_i;
  edn_pkg::edn_rsp_t [3:0] edn_o;
  csrng_req_t csrng_cmd_o;
  csrng_rsp_t csrng_cmd_i;
  logic recov_alert_test_o, fatal_alert_test_o, recov_alert_o, fatal_alert_o;
  logic intr_edn_cmd_req_done_o, intr_edn_fatal_err_o;

  always_comb begin
    reg2hw = '0;
    reg2hw.ctrl.edn_enable.q = MuBi4True;
    reg2hw.ctrl.cmd_fifo_rst.q = MuBi4False;
    reg2hw.ctrl.auto_req_mode.q = MuBi4False;
    reg2hw.ctrl.boot_req_mode.q = MuBi4False;
    reg2hw.sw_cmd_req.q = 32'h0000_0001;
    reg2hw.sw_cmd_req.qe = (phase_q == SendSwCmd);
    edn_i = '{default: '0};
    csrng_cmd_i = CSRNG_RSP_DEFAULT;
    if (phase_q == InjectError || phase_q == Check) begin
      csrng_cmd_i.csrng_rsp_ack = 1'b1;
      csrng_cmd_i.csrng_rsp_sts = CMD_STS_INVALID_CMD_SEQ;
      csrng_cmd_i.csrng_req_ready = 1'b0;
    end
  end

  edn_core dut (
    .clk_i, .rst_ni, .reg2hw, .hw2reg, .edn_i, .edn_o, .csrng_cmd_o, .csrng_cmd_i,
    .recov_alert_test_o, .fatal_alert_test_o, .recov_alert_o, .fatal_alert_o,
    .intr_edn_cmd_req_done_o, .intr_edn_fatal_err_o
  );

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      phase_q <= Idle;
      enable_wait_q <= '0;
      done_o <= 1'b0;
      protocol_violation_o <= 1'b0;
      valid_after_error_o <= 1'b0;
      csrng_req_valid_seen_o <= 1'b0;
      action_coverage_o <= '0;
    end else begin
      unique case (phase_q)
        Idle: if (start_i) begin
          action_coverage_o <= 1'b1;
          phase_q <= EnableWait;
          enable_wait_q <= '0;
        end
        EnableWait: begin
          if (enable_wait_q == 3'd4) begin
            phase_q <= SendSwCmd;
          end else begin
            enable_wait_q <= enable_wait_q + 3'd1;
          end
        end
        SendSwCmd: phase_q <= WaitValid;
        WaitValid: if (csrng_cmd_o.csrng_req_valid) begin
          csrng_req_valid_seen_o <= 1'b1;
          phase_q <= InjectError;
        end
        InjectError: phase_q <= Check;
        Check: begin
          valid_after_error_o <= csrng_cmd_o.csrng_req_valid;
          protocol_violation_o <= csrng_req_valid_seen_o && !csrng_cmd_i.csrng_req_ready &&
                                  !csrng_cmd_o.csrng_req_valid;
          done_o <= 1'b1;
          phase_q <= Done;
        end
        default: phase_q <= Done;
      endcase
    end
  end
endmodule
