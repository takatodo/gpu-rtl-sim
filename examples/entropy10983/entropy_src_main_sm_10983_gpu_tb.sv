// Device-clean, clock-driven form of the OpenTitan #10983 reproducer.
//
// A host or GPU patch schedule owns clk_i/rst_ni/start_i.  The wrapper drives
// the same two passing health-test pulses used by the direct CPU reproducer and
// exposes the oracle as state rather than stdout.
module entropy_src_main_sm_10983_gpu_tb (
  input logic clk_i,
  input logic rst_ni,
  input logic start_i,
  output logic done_o,
  output logic early_sha3_process_o,
  output logic sha3_process_o,
  output logic fw_start_o,
  output logic main_sm_err_o,
  output logic [8:0] state_o,
  output logic action_coverage_o
);
  typedef enum logic [3:0] {Idle, Warmup0, Warmup1, Pulse0, Gap0, Pulse1, Gap1, Drain, Done} phase_e;

  phase_e phase_q;
  logic [2:0] drain_count_q;
  logic enable_i;
  logic fw_ov_sha3_start_i;
  logic ht_done_pulse_i;
  logic rst_alert_cntr_o;
  logic main_stage_push_o;
  logic bypass_stage_pop_o;
  logic boot_phase_done_o;
  logic sha3_start_o;
  logic sha3_done_o;
  logic cs_aes_halt_req_o;
  logic main_sm_alert_o;
  logic main_sm_idle_o;

  assign enable_i = (phase_q != Idle);
  assign fw_ov_sha3_start_i = 1'b0;
  assign fw_start_o = fw_ov_sha3_start_i;
  assign ht_done_pulse_i = (phase_q == Pulse0) || (phase_q == Pulse1);

  entropy_src_main_sm dut (
    .clk_i,
    .rst_ni,
    .enable_i,
`ifdef ENTROPY_SRC_10983_FIXED
    .fw_ov_ent_insert_i(1'b1),
    .fw_ov_sha3_start_i,
`endif
    .ht_done_pulse_i,
    .ht_fail_pulse_i(1'b0),
    .alert_thresh_fail_i(1'b0),
    .sfifo_esfinal_full_i(1'b0),
    .rst_alert_cntr_o,
    .bypass_mode_i(1'b0),
    .main_stage_rdy_i(1'b1),
    .bypass_stage_rdy_i(1'b0),
    .sha3_state_vld_i(1'b1),
    .main_stage_push_o,
    .bypass_stage_pop_o,
    .boot_phase_done_o,
    .sha3_start_o,
    .sha3_process_o,
    .sha3_done_o,
    .cs_aes_halt_req_o,
    .cs_aes_halt_ack_i(1'b1),
    .local_escalate_i(1'b0),
    .main_sm_alert_o,
    .main_sm_idle_o,
    .main_sm_state_o(state_o),
    .main_sm_err_o
  );

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      phase_q <= Idle;
      drain_count_q <= '0;
      done_o <= 1'b0;
      early_sha3_process_o <= 1'b0;
      action_coverage_o <= 1'b0;
    end else begin
      if (!fw_ov_sha3_start_i && sha3_process_o) begin
        early_sha3_process_o <= 1'b1;
      end
      unique case (phase_q)
        Idle: if (start_i) begin
          action_coverage_o <= 1'b1;
          phase_q <= Warmup0;
        end
        Warmup0: phase_q <= Warmup1;
        Warmup1: phase_q <= Pulse0;
        Pulse0: phase_q <= Gap0;
        Gap0: phase_q <= Pulse1;
        Pulse1: phase_q <= Gap1;
        Gap1: begin
          drain_count_q <= '0;
          phase_q <= Drain;
        end
        Drain: begin
          if (drain_count_q == 3'd5) begin
            done_o <= 1'b1;
            phase_q <= Done;
          end else begin
            drain_count_q <= drain_count_q + 3'd1;
          end
        end
        default: phase_q <= Done;
      endcase
    end
  end
endmodule
