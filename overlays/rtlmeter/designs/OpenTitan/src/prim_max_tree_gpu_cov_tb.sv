// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_max_tree.

module prim_max_tree_gpu_cov_tb (
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
  localparam int unsigned SrcWidth = 2;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [NumSrc-1:0][Width-1:0] values_i;
  logic [NumSrc-1:0] valid_i;
  logic [Width-1:0] max_value_o;
  logic [SrcWidth-1:0] max_idx_o;
  logic max_valid_o;
  logic [1:0] phase_w;
  logic [NumSrc-1:0][Width-1:0] next_values_w;
  logic [NumSrc-1:0] next_valid_w;
  logic [Width-1:0] expected_value_w;
  logic [SrcWidth-1:0] expected_idx_w;
  logic expected_valid_w;
  logic value_match_w;
  logic idx_match_w;
  logic valid_match_w;
  logic all_match_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] any_valid_count_q;
  logic [31:0] no_valid_count_q;
  logic [31:0] value_match_count_q;
  logic [31:0] value_mismatch_count_q;
  logic [31:0] idx_match_count_q;
  logic [31:0] idx_mismatch_count_q;
  logic [31:0] valid_match_count_q;
  logic [31:0] valid_mismatch_count_q;
  logic [31:0] lane0_win_count_q;
  logic [31:0] lane1_win_count_q;
  logic [31:0] lane2_win_count_q;
  logic [31:0] lane3_win_count_q;
  logic [31:0] tie_case_count_q;
  logic [31:0] max_zero_count_q;
  logic [31:0] max_f_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_max_tree #(
    .NumSrc(NumSrc),
    .Width(Width)
  ) dut (
    .clk_i,
    .rst_ni,
    .values_i,
    .valid_i,
    .max_value_o,
    .max_idx_o,
    .max_valid_o
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
            (32'h9e37_1001 * (lane + 1));
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

  function automatic logic [Width-1:0] expected_max_value(
      input logic [NumSrc-1:0][Width-1:0] values,
      input logic [NumSrc-1:0] valid);
    logic [Width-1:0] value;
    value = '0;
    for (int unsigned lane = 0; lane < NumSrc; lane++) begin
      if (valid[lane] && values[lane] > value) begin
        value = values[lane];
      end
    end
    return (|valid) ? value : values[0];
  endfunction

  function automatic logic [SrcWidth-1:0] expected_max_idx(
      input logic [NumSrc-1:0][Width-1:0] values,
      input logic [NumSrc-1:0] valid);
    logic [Width-1:0] value;
    logic [SrcWidth-1:0] idx;
    value = '0;
    idx = '0;
    for (int signed lane = NumSrc - 1; lane >= 0; lane--) begin
      if (valid[lane] && values[lane] >= value) begin
        value = values[lane];
        idx = SrcWidth'(lane);
      end
    end
    return (|valid) ? idx : '0;
  endfunction

  function automatic logic has_tie(input logic [NumSrc-1:0][Width-1:0] values,
                                   input logic [NumSrc-1:0] valid);
    logic tied;
    tied = 1'b0;
    for (int unsigned i = 0; i < NumSrc; i++) begin
      for (int unsigned j = i + 1; j < NumSrc; j++) begin
        if (valid[i] && valid[j] && values[i] == values[j]) begin
          tied = 1'b1;
        end
      end
    end
    return tied;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign expected_value_w = expected_max_value(values_i, valid_i);
  assign expected_idx_w = expected_max_idx(values_i, valid_i);
  assign expected_valid_w = |valid_i;
  assign value_match_w = max_value_o == expected_value_w;
  assign idx_match_w = max_idx_o == expected_idx_w;
  assign valid_match_w = max_valid_o == expected_valid_w;
  assign all_match_w = value_match_w && idx_match_w && valid_match_w;

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
      rand_q <= cfg_seed_i ^ 32'h6d61_7801;
      valid_i <= '0;
      for (int unsigned lane = 0; lane < NumSrc; lane++) begin
        values_i[lane] <= choose_value(cfg_seed_i ^ 32'hda7a_0000, lane);
      end
      any_valid_count_q <= 32'd0;
      no_valid_count_q <= 32'd0;
      value_match_count_q <= 32'd0;
      value_mismatch_count_q <= 32'd0;
      idx_match_count_q <= 32'd0;
      idx_mismatch_count_q <= 32'd0;
      valid_match_count_q <= 32'd0;
      valid_mismatch_count_q <= 32'd0;
      lane0_win_count_q <= 32'd0;
      lane1_win_count_q <= 32'd0;
      lane2_win_count_q <= 32'd0;
      lane3_win_count_q <= 32'd0;
      tie_case_count_q <= 32'd0;
      max_zero_count_q <= 32'd0;
      max_f_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h4a7e_e000;
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
          values_i[lane] <= choose_value(rand_q ^ drain_cycle_q ^ 32'h5eed_0000, lane);
        end
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      if (|valid_i) begin
        any_valid_count_q <= any_valid_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        no_valid_count_q <= no_valid_count_q + 32'd1;
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (value_match_w) begin
        value_match_count_q <= value_match_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        value_mismatch_count_q <= value_mismatch_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (idx_match_w) begin
        idx_match_count_q <= idx_match_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end else begin
        idx_mismatch_count_q <= idx_mismatch_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (valid_match_w) begin
        valid_match_count_q <= valid_match_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end else begin
        valid_mismatch_count_q <= valid_mismatch_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (max_valid_o && max_idx_o == 2'd0) begin lane0_win_count_q <= lane0_win_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (max_valid_o && max_idx_o == 2'd1) begin lane1_win_count_q <= lane1_win_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (max_valid_o && max_idx_o == 2'd2) begin lane2_win_count_q <= lane2_win_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (max_valid_o && max_idx_o == 2'd3) begin lane3_win_count_q <= lane3_win_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (has_tie(values_i, valid_i)) begin tie_case_count_q <= tie_case_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (max_value_o == '0) begin max_zero_count_q <= max_zero_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (&max_value_o) begin max_f_count_q <= max_f_count_q + 32'd1; seen_q[16] <= 1'b1; end
      signature_q <= {signature_q[28:0], signature_q[31:29]} ^
                     {28'd0, valid_i} ^ {28'd0, max_value_o} ^
                     {30'd0, max_idx_o} ^ {31'd0, max_valid_o};
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_req_valid_pct_i ^
                           cfg_rsp_valid_pct_i ^ cfg_access_ack_data_pct_i ^
                           32'h4a7e_e001;
  assign host_req_accepted_o = any_valid_count_q;
  assign device_req_accepted_o = value_match_count_q;
  assign device_rsp_accepted_o = idx_match_count_q;
  assign host_rsp_accepted_o = valid_match_count_q;
  assign rsp_queue_overflow_o = value_mismatch_count_q + idx_mismatch_count_q +
                                valid_mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    2'd0, seen_q[16:0], valid_i, max_value_o, max_idx_o, max_valid_o, rst_ni, done_o
  };
  assign toggle_bitmap_word1_o = {
    1'b0, expected_value_w, expected_idx_w, expected_valid_w,
    value_match_w, idx_match_w, valid_match_w, all_match_w,
    phase_w, valid_i, max_value_o, max_idx_o, max_valid_o, cfg_valid_i, global_cycle_q[5:0]
  };
  assign toggle_bitmap_word2_o = {
    value_match_count_q[7:0],
    idx_match_count_q[7:0],
    valid_match_count_q[7:0],
    any_valid_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = any_valid_count_q;
  assign real_toggle_subset_word1_o = no_valid_count_q;
  assign real_toggle_subset_word2_o = value_match_count_q;
  assign real_toggle_subset_word3_o = value_mismatch_count_q;
  assign real_toggle_subset_word4_o = idx_match_count_q;
  assign real_toggle_subset_word5_o = idx_mismatch_count_q;
  assign real_toggle_subset_word6_o = valid_match_count_q;
  assign real_toggle_subset_word7_o = valid_mismatch_count_q;
  assign real_toggle_subset_word8_o = lane0_win_count_q;
  assign real_toggle_subset_word9_o = lane1_win_count_q;
  assign real_toggle_subset_word10_o = lane2_win_count_q;
  assign real_toggle_subset_word11_o = lane3_win_count_q;
  assign real_toggle_subset_word12_o = tie_case_count_q;
  assign real_toggle_subset_word13_o = max_zero_count_q;
  assign real_toggle_subset_word14_o = max_f_count_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {12'd0, valid_i, values_i[0], values_i[1], values_i[2], values_i[3]};
  assign focused_wave_word1_o = {28'd0, max_value_o};
  assign focused_wave_word2_o = {28'd0, expected_value_w};
  assign focused_wave_word3_o = {30'd0, max_idx_o};
  assign focused_wave_word4_o = {30'd0, expected_idx_w};
  assign focused_wave_word5_o = {26'd0, phase_w, max_valid_o, expected_valid_w, all_match_w, done_o};
  assign focused_wave_word6_o = rsp_queue_overflow_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = value_match_count_q + idx_match_count_q + valid_match_count_q;
  assign oracle_expected_err_count_o = rsp_queue_overflow_o;
  assign oracle_observed_ok_count_o = any_valid_count_q;
  assign oracle_observed_err_count_o = no_valid_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    lane0_win_count_q[7:0],
    lane1_win_count_q[7:0],
    lane2_win_count_q[7:0],
    lane3_win_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {12'd0, valid_i, values_i[0], values_i[1], values_i[2], values_i[3]};
  assign oracle_semantic_case_acked_o = {24'd0, max_value_o, expected_value_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_max_tree_gpu_cov_tb
