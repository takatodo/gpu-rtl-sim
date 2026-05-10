// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_edge_detector.

module prim_edge_detector_gpu_cov_tb (
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
  localparam int unsigned Width = 4;
  localparam logic [Width-1:0] ResetValue = 4'b0011;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [Width-1:0] d_i;
  logic [Width-1:0] q_sync_o;
  logic [Width-1:0] q_posedge_pulse_o;
  logic [Width-1:0] q_negedge_pulse_o;
  logic [Width-1:0] edge_mask_w;
  logic [1:0] phase_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] input_toggle_count_q;
  logic [31:0] input_stable_count_q;
  logic [31:0] posedge_count_q;
  logic [31:0] negedge_count_q;
  logic [31:0] sync_seen_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_edge_cycles_q;
  logic [Width-1:0] d_q;
  logic [Width-1:0] last_sync_q;
  logic edge_before_sync_violation_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_edge_detector #(
    .Width(Width),
    .ResetValue(ResetValue),
    .EnSync(1'b1)
  ) dut (
    .clk_i,
    .rst_ni,
    .d_i,
    .q_sync_o,
    .q_posedge_pulse_o,
    .q_negedge_pulse_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [31:0] clamp_pct(input logic [31:0] pct_raw);
    return (pct_raw > 32'd100) ? 32'd100 : pct_raw;
  endfunction

  function automatic logic pct_hit(input logic [31:0] state, input logic [31:0] pct_raw);
    return ((state % 32'd100) < clamp_pct(pct_raw));
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign d_i = d_q;

  always_comb begin
    edge_mask_w[0] = pct_hit(rand_q ^ cfg_seed_i, cfg_req_valid_pct_i);
    edge_mask_w[1] = pct_hit({rand_q[15:0], rand_q[31:16]} ^ cfg_req_data_mode_i,
                             cfg_rsp_valid_pct_i);
    edge_mask_w[2] = pct_hit(rand_q ^ cfg_req_data_hi_xor_i ^ cfg_req_family_i,
                             cfg_host_d_ready_pct_i);
    edge_mask_w[3] = pct_hit(~rand_q ^ cfg_rsp_family_i ^ cfg_rsp_data_mode_i,
                             cfg_device_a_ready_pct_i);
  end

  always_comb begin
    if (!cfg_valid_i || !rst_ni) begin
      phase_w = ResetPhase;
    end else if (traffic_cycle_q < cfg_batch_length_i) begin
      phase_w = TrafficPhase;
    end else if (drain_cycle_q < cfg_drain_cycles_i) begin
      phase_w = DrainPhase;
    end else begin
      phase_w = DonePhase;
    end
  end

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      global_cycle_q <= global_cycle_q + 32'd1;
    end

    if (!rst_ni) begin
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'h2468_1357;
      input_toggle_count_q <= 32'd0;
      input_stable_count_q <= 32'd0;
      posedge_count_q <= 32'd0;
      negedge_count_q <= 32'd0;
      sync_seen_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h4455_6677;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_edge_cycles_q <= 32'd0;
      d_q <= ResetValue;
      last_sync_q <= ResetValue;
      edge_before_sync_violation_q <= 1'b0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i);
      last_sync_q <= q_sync_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        if (edge_mask_w != '0) begin
          d_q <= d_q ^ edge_mask_w;
          input_toggle_count_q <= input_toggle_count_q + 32'd1;
          signature_q <= {signature_q[30:0], signature_q[31]} ^
                         {28'd0, edge_mask_w} ^ rand_q ^ cfg_address_mask_i;
          seen_q[0] <= 1'b1;
        end else begin
          input_stable_count_q <= input_stable_count_q + 32'd1;
          if (posedge_count_q == 32'd0 && negedge_count_q == 32'd0) begin
            pre_edge_cycles_q <= pre_edge_cycles_q + 32'd1;
          end
          seen_q[1] <= 1'b1;
        end
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        d_q <= (cfg_rsp_delay_mode_i[0]) ? ResetValue : ~ResetValue;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[2] <= 1'b1;
      end

      if (q_sync_o != last_sync_q) begin
        sync_seen_count_q <= sync_seen_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (q_posedge_pulse_o != '0) begin
        posedge_count_q <= posedge_count_q + 32'd1;
        signature_q <= signature_q ^ {24'd0, q_posedge_pulse_o, d_q};
        seen_q[4] <= 1'b1;
      end
      if (q_negedge_pulse_o != '0) begin
        negedge_count_q <= negedge_count_q + 32'd1;
        signature_q <= signature_q ^ {20'd0, q_negedge_pulse_o, q_sync_o, d_q};
        seen_q[5] <= 1'b1;
      end
      if ((q_posedge_pulse_o & q_negedge_pulse_o) != '0) begin
        edge_before_sync_violation_q <= 1'b1;
        seen_q[6] <= 1'b1;
      end
      if (phase_w == DrainPhase && q_sync_o == d_q) begin
        seen_q[7] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i;
  assign host_req_accepted_o = posedge_count_q;
  assign device_req_accepted_o = negedge_count_q;
  assign device_rsp_accepted_o = sync_seen_count_q;
  assign host_rsp_accepted_o = input_toggle_count_q;
  assign rsp_queue_overflow_o = {31'd0, edge_before_sync_violation_q};
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    16'd0,
    seen_q[7:0],
    q_negedge_pulse_o,
    q_posedge_pulse_o
  };
	  assign toggle_bitmap_word1_o = {
	    8'd0,
	    d_q,
	    q_sync_o,
	    edge_mask_w,
	    2'd0,
	    phase_w,
	    global_cycle_q[7:0]
	  };
	  assign toggle_bitmap_word2_o = {
	    posedge_count_q[7:0],
	    negedge_count_q[7:0],
	    input_toggle_count_q[7:0],
	    sync_seen_count_q[7:0]
	  };

  assign real_toggle_subset_word0_o = {28'd0, d_q};
  assign real_toggle_subset_word1_o = {28'd0, q_sync_o};
  assign real_toggle_subset_word2_o = {28'd0, q_posedge_pulse_o};
  assign real_toggle_subset_word3_o = {28'd0, q_negedge_pulse_o};
  assign real_toggle_subset_word4_o = input_toggle_count_q;
  assign real_toggle_subset_word5_o = input_stable_count_q;
  assign real_toggle_subset_word6_o = posedge_count_q;
  assign real_toggle_subset_word7_o = negedge_count_q;
  assign real_toggle_subset_word8_o = sync_seen_count_q;
  assign real_toggle_subset_word9_o = traffic_cycle_q;
  assign real_toggle_subset_word10_o = drain_cycle_q;
  assign real_toggle_subset_word11_o = rand_q;
  assign real_toggle_subset_word12_o = signature_q;
  assign real_toggle_subset_word13_o = stalled_signature_q;
  assign real_toggle_subset_word14_o = {24'd0, seen_q[7:0]};
  assign real_toggle_subset_word15_o = pre_edge_cycles_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {28'd0, d_q};
  assign focused_wave_word1_o = {28'd0, q_sync_o};
  assign focused_wave_word2_o = {28'd0, edge_mask_w};
  assign focused_wave_word3_o = {28'd0, q_posedge_pulse_o};
  assign focused_wave_word4_o = {28'd0, q_negedge_pulse_o};
  assign focused_wave_word5_o = {30'd0, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = input_toggle_count_q;
  assign oracle_expected_err_count_o = {31'd0, edge_before_sync_violation_q};
  assign oracle_observed_ok_count_o = posedge_count_q + negedge_count_q;
  assign oracle_observed_err_count_o = rsp_queue_overflow_o;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {24'd0, seen_q[7:0]};
  assign oracle_semantic_case_seen_o = {28'd0, d_q ^ q_sync_o};
  assign oracle_semantic_case_acked_o = {28'd0, q_posedge_pulse_o ^ q_negedge_pulse_o};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_edge_cycles_q;
endmodule : prim_edge_detector_gpu_cov_tb
