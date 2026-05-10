// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_count.

module prim_count_gpu_cov_tb (
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
  localparam logic [Width-1:0] ResetValue = 4'h0;
  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] TrafficPhase = 3'd1;
  localparam logic [2:0] DrainPhase   = 3'd2;
  localparam logic [2:0] DonePhase    = 3'd3;

  logic clk_i;
  logic rst_ni;
  logic clr_i;
  logic set_i;
  logic [Width-1:0] set_cnt_i;
  logic incr_en_i;
  logic decr_en_i;
  logic [Width-1:0] step_i;
  logic commit_i;
  logic [Width-1:0] cnt_o;
  logic [Width-1:0] cnt_after_commit_o;
  logic err_o;

  logic [Width-1:0] next_set_cnt_w;
  logic [Width-1:0] next_step_w;
  logic next_clr_w;
  logic next_set_w;
  logic next_incr_w;
  logic next_decr_w;
  logic next_commit_w;
  logic [31:0] action_mix_w;
  logic [2:0] action_sel_w;
  logic [Width-1:0] expected_after_w;
  logic observed_match_w;
  logic count_changed_w;
  logic after_changed_w;
  logic count_zero_w;
  logic count_max_w;
  logic [2:0] phase_w;

  logic [Width-1:0] expected_cnt_q;
  logic [Width-1:0] last_cnt_q;
  logic [Width-1:0] last_after_q;
  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] clear_count_q;
  logic [31:0] set_count_q;
  logic [31:0] incr_count_q;
  logic [31:0] decr_count_q;
  logic [31:0] commit_count_q;
  logic [31:0] no_commit_count_q;
  logic [31:0] count_zero_count_q;
  logic [31:0] count_nonzero_count_q;
  logic [31:0] count_max_count_q;
  logic [31:0] after_change_count_q;
  logic [31:0] after_same_count_q;
  logic [31:0] count_change_count_q;
  logic [31:0] step_nonzero_count_q;
  logic [31:0] set_nonzero_count_q;
  logic [31:0] match_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] err_seen_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_count #(
    .Width(Width),
    .ResetValue(ResetValue),
    .EnableAlertTriggerSVA(1'b0),
    .PossibleActions(prim_count_pkg::action_mask_t'(
        prim_count_pkg::Clr | prim_count_pkg::Set |
        prim_count_pkg::Incr | prim_count_pkg::Decr))
  ) dut (
    .clk_i,
    .rst_ni,
    .clr_i,
    .set_i,
    .set_cnt_i,
    .incr_en_i,
    .decr_en_i,
    .step_i,
    .commit_i,
    .cnt_o,
    .cnt_after_commit_o,
    .err_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [Width-1:0] mix_nibble(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [31:0] mixed;
    mixed = state ^ {state[8:0], state[31:9]} ^ salt;
    return mixed[Width-1:0];
  endfunction

  function automatic logic [Width-1:0] mix_step(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [Width-1:0] mixed;
    mixed = mix_nibble(state, salt);
    return (mixed == '0) ? {{(Width-1){1'b0}}, 1'b1} : mixed;
  endfunction

  function automatic logic [Width-1:0] next_count(
      input logic [Width-1:0] current,
      input logic do_clr,
      input logic do_set,
      input logic do_incr,
      input logic do_decr,
      input logic [Width-1:0] set_value,
      input logic [Width-1:0] step_value);
    logic [Width:0] ext_cnt;
    logic [Width-1:0] cnt_sat;
    logic cnt_en;
    if (do_clr) begin
      next_count = ResetValue;
    end else if (do_set) begin
      next_count = set_value;
    end else begin
      ext_cnt = do_decr ? {1'b0, current} - {1'b0, step_value} :
                do_incr ? {1'b0, current} + {1'b0, step_value} :
                {1'b0, current};
      cnt_sat = (do_decr && ext_cnt[Width]) ? '0 :
                (do_incr && ext_cnt[Width]) ? {Width{1'b1}} :
                ext_cnt[Width-1:0];
      cnt_en = (do_incr ^ do_decr) &&
               ((do_incr && !(&current)) || (do_decr && !(current == '0)));
      next_count = cnt_en ? cnt_sat : current;
    end
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_set_cnt_w = mix_nibble(rand_q ^ traffic_cycle_q,
                                     cfg_address_base_i ^ cfg_req_data_hi_xor_i);
  assign next_step_w = mix_step(rand_q ^ {traffic_cycle_q[15:0], drain_cycle_q[15:0]},
                                cfg_source_mask_i ^ cfg_rsp_data_hi_xor_i);
  assign action_mix_w = rand_q ^ traffic_cycle_q ^ cfg_req_family_i;
  assign action_sel_w = action_mix_w[2:0];

  always_comb begin
    next_clr_w = 1'b0;
    next_set_w = 1'b0;
    next_incr_w = 1'b0;
    next_decr_w = 1'b0;
    unique case (action_sel_w)
      3'd0: next_set_w = 1'b1;
      3'd1: next_incr_w = 1'b1;
      3'd2: next_decr_w = 1'b1;
      3'd3: begin next_incr_w = 1'b1; next_decr_w = 1'b1; end
      3'd4: next_incr_w = 1'b1;
      3'd5: next_decr_w = 1'b1;
      3'd6: next_set_w = 1'b1;
      default: ;
    endcase
    if (traffic_cycle_q[5:0] == 6'd0) begin
      next_clr_w = 1'b1;
      next_set_w = 1'b0;
      next_incr_w = 1'b0;
      next_decr_w = 1'b0;
    end
  end

  assign next_commit_w = (rand_q[7] == 1'b1) || (cfg_req_valid_pct_i > 32'd0) ||
                         (traffic_cycle_q[2:0] == 3'd0);
  assign expected_after_w = next_count(expected_cnt_q, clr_i, set_i, incr_en_i, decr_en_i,
                                       set_cnt_i, step_i);
  assign observed_match_w = (cnt_o == expected_cnt_q) &&
                            (cnt_after_commit_o == expected_after_w) &&
                            !err_o;
  assign count_changed_w = cnt_o != last_cnt_q;
  assign after_changed_w = cnt_after_commit_o != last_after_q;
  assign count_zero_w = cnt_o == '0;
  assign count_max_w = &cnt_o;

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
      clr_i <= 1'b0;
      set_i <= 1'b0;
      set_cnt_i <= '0;
      incr_en_i <= 1'b0;
      decr_en_i <= 1'b0;
      step_i <= {{(Width-1){1'b0}}, 1'b1};
      commit_i <= 1'b0;
      expected_cnt_q <= ResetValue;
      last_cnt_q <= '0;
      last_after_q <= '0;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'hc001_3501;
      clear_count_q <= 32'd0;
      set_count_q <= 32'd0;
      incr_count_q <= 32'd0;
      decr_count_q <= 32'd0;
      commit_count_q <= 32'd0;
      no_commit_count_q <= 32'd0;
      count_zero_count_q <= 32'd0;
      count_nonzero_count_q <= 32'd0;
      count_max_count_q <= 32'd0;
      after_change_count_q <= 32'd0;
      after_same_count_q <= 32'd0;
      count_change_count_q <= 32'd0;
      step_nonzero_count_q <= 32'd0;
      set_nonzero_count_q <= 32'd0;
      match_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      err_seen_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'hc0a7_a55a;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_rsp_data_hi_xor_i ^
                          cfg_req_family_i);
      last_cnt_q <= cnt_o;
      last_after_q <= cnt_after_commit_o;
      if (commit_i) begin
        expected_cnt_q <= expected_after_w;
      end

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        clr_i <= next_clr_w;
        set_i <= next_set_w;
        incr_en_i <= next_incr_w;
        decr_en_i <= next_decr_w;
        set_cnt_i <= next_set_cnt_w;
        step_i <= next_step_w;
        commit_i <= next_commit_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        clr_i <= drain_cycle_q == 32'd0;
        set_i <= drain_cycle_q == 32'd1;
        incr_en_i <= drain_cycle_q[1:0] == 2'd2;
        decr_en_i <= drain_cycle_q[1:0] == 2'd3;
        set_cnt_i <= mix_nibble(cfg_address_mask_i ^ drain_cycle_q, cfg_seed_i);
        step_i <= mix_step(cfg_source_mask_i ^ drain_cycle_q, cfg_rsp_family_i);
        commit_i <= 1'b1;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[24:0], signature_q[31:25]} ^
                     rand_q ^ {28'd0, cnt_o} ^ {28'd0, cnt_after_commit_o} ^
                     {23'd0, err_o, commit_i, decr_en_i, incr_en_i, set_i, clr_i, phase_w};

      if (clr_i) begin clear_count_q <= clear_count_q + 32'd1; seen_q[2] <= 1'b1; end
      if (set_i) begin set_count_q <= set_count_q + 32'd1; seen_q[3] <= 1'b1; end
      if (incr_en_i) begin incr_count_q <= incr_count_q + 32'd1; seen_q[4] <= 1'b1; end
      if (decr_en_i) begin decr_count_q <= decr_count_q + 32'd1; seen_q[5] <= 1'b1; end
      if (commit_i) begin commit_count_q <= commit_count_q + 32'd1; seen_q[6] <= 1'b1; end
      if (!commit_i) begin no_commit_count_q <= no_commit_count_q + 32'd1; seen_q[7] <= 1'b1; end
      if (count_zero_w) begin count_zero_count_q <= count_zero_count_q + 32'd1; seen_q[8] <= 1'b1; end
      if (!count_zero_w) begin count_nonzero_count_q <= count_nonzero_count_q + 32'd1; seen_q[9] <= 1'b1; end
      if (count_max_w) begin count_max_count_q <= count_max_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (after_changed_w) begin after_change_count_q <= after_change_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (!after_changed_w) begin after_same_count_q <= after_same_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (count_changed_w) begin count_change_count_q <= count_change_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (step_i != '0) begin step_nonzero_count_q <= step_nonzero_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (set_cnt_i != '0) begin set_nonzero_count_q <= set_nonzero_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (observed_match_w) begin match_count_q <= match_count_q + 32'd1; seen_q[16] <= 1'b1; end
      if (!observed_match_w) begin mismatch_count_q <= mismatch_count_q + 32'd1; seen_q[17] <= 1'b1; end
      if (err_o) begin err_seen_count_q <= err_seen_count_q + 32'd1; seen_q[18] <= 1'b1; end
      if (phase_w == ResetPhase) begin
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = signature_q ^ {31'd0, done_o} ^ progress_cycle_count_o;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {29'd0, phase_w};
  assign host_req_accepted_o = commit_count_q;
  assign device_req_accepted_o = count_change_count_q;
  assign device_rsp_accepted_o = clear_count_q + set_count_q;
  assign host_rsp_accepted_o = match_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q + err_seen_count_q;

  assign toggle_bitmap_word0_o = {
    4'd0,
    cnt_o,
    cnt_after_commit_o,
    expected_cnt_q,
    expected_after_w,
    set_cnt_i,
    step_i,
    phase_w,
    commit_i
  };
  assign toggle_bitmap_word1_o = {
    seen_q[15:0],
    7'd0,
    err_o,
    observed_match_w,
    decr_en_i,
    incr_en_i,
    set_i,
    clr_i,
    phase_w
  };
  assign toggle_bitmap_word2_o = {
    clear_count_q[3:0],
    set_count_q[3:0],
    incr_count_q[3:0],
    decr_count_q[3:0],
    commit_count_q[3:0],
    cnt_o,
    cnt_after_commit_o,
    err_o,
    phase_w
  };

  assign real_toggle_subset_word0_o = clear_count_q;
  assign real_toggle_subset_word1_o = set_count_q;
  assign real_toggle_subset_word2_o = incr_count_q;
  assign real_toggle_subset_word3_o = decr_count_q;
  assign real_toggle_subset_word4_o = commit_count_q;
  assign real_toggle_subset_word5_o = no_commit_count_q;
  assign real_toggle_subset_word6_o = count_zero_count_q;
  assign real_toggle_subset_word7_o = count_nonzero_count_q;
  assign real_toggle_subset_word8_o = count_max_count_q;
  assign real_toggle_subset_word9_o = after_change_count_q;
  assign real_toggle_subset_word10_o = after_same_count_q;
  assign real_toggle_subset_word11_o = count_change_count_q;
  assign real_toggle_subset_word12_o = step_nonzero_count_q;
  assign real_toggle_subset_word13_o = set_nonzero_count_q;
  assign real_toggle_subset_word14_o = match_count_q;
  assign real_toggle_subset_word15_o = mismatch_count_q;
  assign real_toggle_subset_word16_o = err_seen_count_q;
  assign real_toggle_subset_word17_o = progress_signature_o;

  assign focused_wave_word0_o = {28'd0, cnt_o};
  assign focused_wave_word1_o = {28'd0, cnt_after_commit_o};
  assign focused_wave_word2_o = {28'd0, expected_cnt_q};
  assign focused_wave_word3_o = {28'd0, expected_after_w};
  assign focused_wave_word4_o = {24'd0, set_cnt_i, step_i};
  assign focused_wave_word5_o = {22'd0, err_o, observed_match_w, commit_i,
                                 decr_en_i, incr_en_i, set_i, clr_i, phase_w};
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = commit_count_q;
  assign oracle_expected_err_count_o = 32'd0;
  assign oracle_observed_ok_count_o = match_count_q;
  assign oracle_observed_err_count_o = mismatch_count_q + err_seen_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    clear_count_q[7:0],
    set_count_q[7:0],
    incr_count_q[7:0],
    decr_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {13'd0, cnt_o, cnt_after_commit_o, set_cnt_i, step_i, phase_w};
  assign oracle_semantic_case_acked_o = {24'd0, expected_after_w, expected_cnt_q};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q + err_seen_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_count_gpu_cov_tb
