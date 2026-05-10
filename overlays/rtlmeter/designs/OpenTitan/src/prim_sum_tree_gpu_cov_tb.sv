// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_sum_tree.

module prim_sum_tree_gpu_cov_tb (
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
  localparam int unsigned NumSrc = 4;
  localparam int unsigned Width = 4;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [NumSrc-1:0][Width-1:0] values_i;
  logic [NumSrc-1:0] valid_i;
  logic [Width-1:0] sum_value_o;
  logic sum_valid_o;
  logic [1:0] phase_w;
  logic [NumSrc-1:0][Width-1:0] next_values_w;
  logic [NumSrc-1:0] next_valid_w;
  logic [Width-1:0] expected_sum_w;
  logic expected_valid_w;
  logic sum_match_w;
  logic valid_match_w;
  logic all_match_w;
  logic overflow_case_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] any_valid_count_q;
  logic [31:0] no_valid_count_q;
  logic [31:0] sum_match_count_q;
  logic [31:0] sum_mismatch_count_q;
  logic [31:0] valid_match_count_q;
  logic [31:0] valid_mismatch_count_q;
  logic [31:0] lane0_valid_count_q;
  logic [31:0] lane1_valid_count_q;
  logic [31:0] lane2_valid_count_q;
  logic [31:0] lane3_valid_count_q;
  logic [31:0] multi_valid_count_q;
  logic [31:0] overflow_case_count_q;
  logic [31:0] sum_zero_count_q;
  logic [31:0] sum_f_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_sum_tree #(
    .NumSrc(NumSrc),
    .Width(Width)
  ) dut (
    .clk_i,
    .rst_ni,
    .values_i,
    .valid_i,
    .sum_value_o,
    .sum_valid_o
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

  function automatic logic [Width-1:0] choose_value(input logic [31:0] state,
                                                    input int unsigned lane);
    logic [31:0] mixed;
    mixed = state ^ (cfg_req_data_mode_i << lane) ^
            ({cfg_rsp_data_mode_i[15:0], cfg_req_data_hi_xor_i[15:0]} >> lane) ^
            (32'h9e37_3001 * (lane + 1));
    return mixed[Width-1:0] ^ mixed[7:4] ^ mixed[15:12] ^ mixed[23:20];
  endfunction

  function automatic logic [NumSrc-1:0] choose_valid(input logic [31:0] state);
    logic [NumSrc-1:0] valid;
    valid[0] = pct_hit(state ^ cfg_req_family_i, cfg_req_valid_pct_i);
    valid[1] = pct_hit({state[15:0], state[31:16]} ^ cfg_rsp_family_i, cfg_rsp_valid_pct_i);
    valid[2] = pct_hit(state ^ cfg_req_fill_target_i ^ cfg_address_base_i,
                       cfg_put_full_pct_i + cfg_host_d_ready_pct_i);
    valid[3] = pct_hit(~state ^ cfg_rsp_fill_target_i ^ cfg_address_mask_i,
                       cfg_put_partial_pct_i + cfg_device_a_ready_pct_i);
    if (valid == '0 && pct_hit(state ^ cfg_seed_i, cfg_req_valid_pct_i + cfg_rsp_valid_pct_i)) begin
      valid[state[1:0]] = 1'b1;
    end
    return valid;
  endfunction

  function automatic logic [Width-1:0] expected_sum(
      input logic [NumSrc-1:0][Width-1:0] values,
      input logic [NumSrc-1:0] valid);
    logic [Width-1:0] value;
    value = '0;
    for (int unsigned lane = 0; lane < NumSrc; lane++) begin
      if (valid[lane]) begin
        value = value + values[lane];
      end
    end
    return value;
  endfunction

  function automatic logic has_overflow(input logic [NumSrc-1:0][Width-1:0] values,
                                        input logic [NumSrc-1:0] valid);
    logic [Width:0] wide_sum;
    wide_sum = '0;
    for (int unsigned lane = 0; lane < NumSrc; lane++) begin
      if (valid[lane]) begin
        wide_sum = wide_sum + {1'b0, values[lane]};
      end
    end
    return wide_sum[Width];
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign expected_sum_w = expected_sum(values_i, valid_i);
  assign expected_valid_w = |valid_i;
  assign sum_match_w = sum_value_o == expected_sum_w;
  assign valid_match_w = sum_valid_o == expected_valid_w;
  assign all_match_w = sum_match_w && valid_match_w;
  assign overflow_case_w = has_overflow(values_i, valid_i);

  always_comb begin
    next_valid_w = choose_valid(rand_q ^ traffic_cycle_q ^ cfg_source_mask_i);
    for (int unsigned lane = 0; lane < NumSrc; lane++) begin
      next_values_w[lane] = choose_value(rand_q ^ traffic_cycle_q ^ cfg_seed_i, lane);
    end
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
      rand_q <= cfg_seed_i ^ 32'h7375_6d01;
      valid_i <= '0;
      for (int unsigned lane = 0; lane < NumSrc; lane++) begin
        values_i[lane] <= choose_value(cfg_seed_i ^ 32'h5a7a_0000, lane);
      end
      any_valid_count_q <= 32'd0;
      no_valid_count_q <= 32'd0;
      sum_match_count_q <= 32'd0;
      sum_mismatch_count_q <= 32'd0;
      valid_match_count_q <= 32'd0;
      valid_mismatch_count_q <= 32'd0;
      lane0_valid_count_q <= 32'd0;
      lane1_valid_count_q <= 32'd0;
      lane2_valid_count_q <= 32'd0;
      lane3_valid_count_q <= 32'd0;
      multi_valid_count_q <= 32'd0;
      overflow_case_count_q <= 32'd0;
      sum_zero_count_q <= 32'd0;
      sum_f_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5375_e000;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i);

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        valid_i <= next_valid_w;
        values_i <= next_values_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        valid_i <= (drain_cycle_q < NumSrc) ? (NumSrc'(1'b1) << drain_cycle_q[1:0]) : '1;
        for (int unsigned lane = 0; lane < NumSrc; lane++) begin
          values_i[lane] <= choose_value(rand_q ^ drain_cycle_q ^ 32'h5eed_3000, lane);
        end
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      if (|valid_i) begin any_valid_count_q <= any_valid_count_q + 32'd1; seen_q[2] <= 1'b1; end
      else begin no_valid_count_q <= no_valid_count_q + 32'd1; pre_active_cycles_q <= pre_active_cycles_q + 32'd1; seen_q[3] <= 1'b1; end
      if (sum_match_w) begin sum_match_count_q <= sum_match_count_q + 32'd1; seen_q[4] <= 1'b1; end
      else begin sum_mismatch_count_q <= sum_mismatch_count_q + 32'd1; seen_q[5] <= 1'b1; end
      if (valid_match_w) begin valid_match_count_q <= valid_match_count_q + 32'd1; seen_q[6] <= 1'b1; end
      else begin valid_mismatch_count_q <= valid_mismatch_count_q + 32'd1; seen_q[7] <= 1'b1; end
      if (valid_i[0]) begin lane0_valid_count_q <= lane0_valid_count_q + 32'd1; seen_q[8] <= 1'b1; end
      if (valid_i[1]) begin lane1_valid_count_q <= lane1_valid_count_q + 32'd1; seen_q[9] <= 1'b1; end
      if (valid_i[2]) begin lane2_valid_count_q <= lane2_valid_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (valid_i[3]) begin lane3_valid_count_q <= lane3_valid_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if ($countones(valid_i) > 1) begin multi_valid_count_q <= multi_valid_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (overflow_case_w) begin overflow_case_count_q <= overflow_case_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (sum_value_o == '0) begin sum_zero_count_q <= sum_zero_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (&sum_value_o) begin sum_f_count_q <= sum_f_count_q + 32'd1; seen_q[15] <= 1'b1; end
      signature_q <= {signature_q[28:0], signature_q[31:29]} ^
                     {28'd0, valid_i} ^ {28'd0, sum_value_o} ^
                     {31'd0, sum_valid_o} ^ {31'd0, overflow_case_w};
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_req_valid_pct_i ^
                           cfg_rsp_valid_pct_i ^ cfg_access_ack_data_pct_i ^
                           32'h5375_e001;
  assign host_req_accepted_o = any_valid_count_q;
  assign device_req_accepted_o = sum_match_count_q;
  assign device_rsp_accepted_o = overflow_case_count_q;
  assign host_rsp_accepted_o = valid_match_count_q;
  assign rsp_queue_overflow_o = sum_mismatch_count_q + valid_mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    1'b0, seen_q[15:0], valid_i, sum_value_o, sum_valid_o, expected_valid_w,
    sum_match_w, valid_match_w, all_match_w, rst_ni, done_o
  };
  assign toggle_bitmap_word1_o = {
    6'd0, expected_sum_w, overflow_case_w,
    sum_match_w, valid_match_w, all_match_w,
    phase_w, valid_i, sum_value_o, sum_valid_o, cfg_valid_i, global_cycle_q[5:0]
  };
  assign toggle_bitmap_word2_o = {
    sum_match_count_q[7:0],
    overflow_case_count_q[7:0],
    valid_match_count_q[7:0],
    any_valid_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = any_valid_count_q;
  assign real_toggle_subset_word1_o = no_valid_count_q;
  assign real_toggle_subset_word2_o = sum_match_count_q;
  assign real_toggle_subset_word3_o = sum_mismatch_count_q;
  assign real_toggle_subset_word4_o = valid_match_count_q;
  assign real_toggle_subset_word5_o = valid_mismatch_count_q;
  assign real_toggle_subset_word6_o = lane0_valid_count_q;
  assign real_toggle_subset_word7_o = lane1_valid_count_q;
  assign real_toggle_subset_word8_o = lane2_valid_count_q;
  assign real_toggle_subset_word9_o = lane3_valid_count_q;
  assign real_toggle_subset_word10_o = multi_valid_count_q;
  assign real_toggle_subset_word11_o = overflow_case_count_q;
  assign real_toggle_subset_word12_o = sum_zero_count_q;
  assign real_toggle_subset_word13_o = sum_f_count_q;
  assign real_toggle_subset_word14_o = {31'd0, overflow_case_w};
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {12'd0, valid_i, values_i[0], values_i[1], values_i[2], values_i[3]};
  assign focused_wave_word1_o = {28'd0, sum_value_o};
  assign focused_wave_word2_o = {28'd0, expected_sum_w};
  assign focused_wave_word3_o = {28'd0, valid_i};
  assign focused_wave_word4_o = {28'd0, {sum_valid_o, expected_valid_w, overflow_case_w, all_match_w}};
  assign focused_wave_word5_o = {26'd0, phase_w, sum_valid_o, expected_valid_w, all_match_w, done_o};
  assign focused_wave_word6_o = rsp_queue_overflow_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = sum_match_count_q + valid_match_count_q;
  assign oracle_expected_err_count_o = rsp_queue_overflow_o;
  assign oracle_observed_ok_count_o = any_valid_count_q;
  assign oracle_observed_err_count_o = no_valid_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    lane0_valid_count_q[7:0],
    lane1_valid_count_q[7:0],
    lane2_valid_count_q[7:0],
    lane3_valid_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {12'd0, valid_i, values_i[0], values_i[1], values_i[2], values_i[3]};
  assign oracle_semantic_case_acked_o = {24'd0, sum_value_o, expected_sum_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_sum_tree_gpu_cov_tb
