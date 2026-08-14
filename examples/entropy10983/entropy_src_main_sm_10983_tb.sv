// Direct CPU reproducer for OpenTitan #10983.
//
// In FW override entropy-insert mode, the main state machine must not start
// SHA3 processing before firmware has explicitly started and completed the
// insert window.  The pre-fix state machine has no FW insert handshake input,
// so ordinary health-test pulses can advance it to sha3_process_o early.
module entropy_src_main_sm_10983_tb;
  logic clk_i = 1'b0;
  logic rst_ni = 1'b0;
  logic enable_i = 1'b0;
  logic fw_ov_sha3_start_i = 1'b0;
  logic ht_done_pulse_i = 1'b0;
  logic ht_fail_pulse_i = 1'b0;
  logic alert_thresh_fail_i = 1'b0;
  logic sfifo_esfinal_full_i = 1'b0;
  logic rst_alert_cntr_o;
  logic bypass_mode_i = 1'b0;
  logic main_stage_rdy_i = 1'b1;
  logic bypass_stage_rdy_i = 1'b0;
  logic sha3_state_vld_i = 1'b1;
  logic main_stage_push_o;
  logic bypass_stage_pop_o;
  logic boot_phase_done_o;
  logic sha3_start_o;
  logic sha3_process_o;
  logic sha3_done_o;
  logic cs_aes_halt_req_o;
  logic cs_aes_halt_ack_i = 1'b1;
  logic local_escalate_i = 1'b0;
  logic main_sm_alert_o;
  logic main_sm_idle_o;
  logic [8:0] main_sm_state_o;
  logic main_sm_err_o;
  logic early_sha3_process;

  always #5 clk_i = ~clk_i;

  entropy_src_main_sm dut (
    .clk_i,
    .rst_ni,
    .enable_i,
`ifdef ENTROPY_SRC_10983_FIXED
    .fw_ov_ent_insert_i(1'b1),
    .fw_ov_sha3_start_i,
`endif
    .ht_done_pulse_i,
    .ht_fail_pulse_i,
    .alert_thresh_fail_i,
    .sfifo_esfinal_full_i,
    .rst_alert_cntr_o,
    .bypass_mode_i,
    .main_stage_rdy_i,
    .bypass_stage_rdy_i,
    .sha3_state_vld_i,
    .main_stage_push_o,
    .bypass_stage_pop_o,
    .boot_phase_done_o,
    .sha3_start_o,
    .sha3_process_o,
    .sha3_done_o,
    .cs_aes_halt_req_o,
    .cs_aes_halt_ack_i,
    .local_escalate_i,
    .main_sm_alert_o,
    .main_sm_idle_o,
    .main_sm_state_o,
    .main_sm_err_o
  );

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      early_sha3_process <= 1'b0;
    end else if (!fw_ov_sha3_start_i && sha3_process_o) begin
      early_sha3_process <= 1'b1;
    end
  end

  task automatic tick;
    @(posedge clk_i);
    @(negedge clk_i);
  endtask

  task automatic pulse_ht_pass;
    ht_done_pulse_i = 1'b1;
    tick();
    ht_done_pulse_i = 1'b0;
    tick();
  endtask

  initial begin
    repeat (2) tick();
    rst_ni = 1'b1;
    enable_i = 1'b1;
    repeat (2) tick();
    pulse_ht_pass();
    pulse_ht_pass();
    repeat (6) tick();
    $display("RESULT early_sha3_process=%0d sha3_process=%0d fw_start=%0d main_sm_err=%0d state=%0h",
             early_sha3_process, sha3_process_o, fw_ov_sha3_start_i, main_sm_err_o,
             main_sm_state_o);
    $finish;
  end
endmodule
