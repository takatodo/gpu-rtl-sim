// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_arbiter_fixed.

module prim_arbiter_fixed_gpu_cov_tb (
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
  localparam int unsigned N = 4;
  localparam int unsigned DW = 16;
  localparam int unsigned IdxW = 2;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [N-1:0] req_i;
  logic [DW-1:0] data_i [N];
  logic [N-1:0] gnt_o;
  logic [IdxW-1:0] idx_o;
  logic valid_o;
  logic [DW-1:0] data_o;
  logic ready_i;
  logic [1:0] phase_w;
  logic [N-1:0] next_req_w;
  logic [DW-1:0] next_data_w [N];
  logic [IdxW-1:0] expected_idx_w;
  logic [DW-1:0] expected_data_w;
  logic [N-1:0] expected_gnt_w;
  logic accepted_w;
  logic priority_match_w;
  logic data_match_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] valid_count_q;
  logic [31:0] grant_count_q;
  logic [31:0] stall_count_q;
  logic [31:0] ready_idle_count_q;
  logic [31:0] data_match_count_q;
  logic [31:0] data_mismatch_count_q;
  logic [31:0] priority_match_count_q;
  logic [31:0] priority_mismatch_count_q;
  logic [31:0] lane0_grant_count_q;
  logic [31:0] lane1_grant_count_q;
  logic [31:0] lane2_grant_count_q;
  logic [31:0] lane3_grant_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_handshake_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_arbiter_fixed #(
    .N(N),
    .DW(DW),
    .EnDataPort(1'b1)
  ) dut (
    .clk_i,
    .rst_ni,
    .req_i,
    .data_i,
    .gnt_o,
    .idx_o,
    .valid_o,
    .data_o,
    .ready_i
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

  function automatic logic [N-1:0] choose_req(input logic [31:0] state);
    logic [N-1:0] req;
    req[0] = pct_hit(state ^ cfg_req_family_i, cfg_req_valid_pct_i);
    req[1] = pct_hit({state[15:0], state[31:16]} ^ cfg_rsp_family_i, cfg_rsp_valid_pct_i);
    req[2] = pct_hit(state ^ cfg_req_fill_target_i ^ cfg_address_base_i,
                     cfg_put_full_pct_i + cfg_host_d_ready_pct_i);
    req[3] = pct_hit(~state ^ cfg_rsp_fill_target_i ^ cfg_address_mask_i,
                     cfg_put_partial_pct_i + cfg_device_a_ready_pct_i);
    if (req == '0 && pct_hit(state ^ cfg_seed_i, cfg_req_valid_pct_i + cfg_rsp_valid_pct_i)) begin
      req[state[1:0]] = 1'b1;
    end
    return req;
  endfunction

  function automatic logic [DW-1:0] choose_data(input logic [31:0] state, input int unsigned lane);
    logic [31:0] mixed;
    mixed = state ^ (cfg_req_data_mode_i << lane) ^
            ({cfg_rsp_data_mode_i[15:0], cfg_req_data_hi_xor_i[15:0]} >> lane) ^
            (32'h9e37_0001 * (lane + 1));
    return mixed[DW-1:0] ^ mixed[31:16];
  endfunction

  function automatic logic [IdxW-1:0] first_req_idx(input logic [N-1:0] req);
    if (req[0]) begin
      return 2'd0;
    end
    if (req[1]) begin
      return 2'd1;
    end
    if (req[2]) begin
      return 2'd2;
    end
    return 2'd3;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign ready_i = cfg_valid_i &&
                   rst_ni &&
                   (phase_w == DrainPhase ||
                    pct_hit(rand_q ^ cfg_access_ack_data_pct_i ^ cfg_rsp_delay_max_i,
                            cfg_access_ack_data_pct_i + cfg_device_a_ready_pct_i));
  assign accepted_w = valid_o && ready_i;
  assign expected_idx_w = first_req_idx(req_i);
  assign expected_data_w = data_i[expected_idx_w];
  assign priority_match_w = !valid_o || idx_o == expected_idx_w;
  assign data_match_w = !valid_o || data_o == expected_data_w;

  always_comb begin
    next_req_w = choose_req(rand_q ^ traffic_cycle_q ^ cfg_source_mask_i);
    for (int unsigned lane = 0; lane < N; lane++) begin
      next_data_w[lane] = choose_data(rand_q ^ traffic_cycle_q ^ cfg_seed_i, lane);
    end
    expected_gnt_w = '0;
    if (accepted_w) begin
      expected_gnt_w[expected_idx_w] = 1'b1;
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
      rand_q <= cfg_seed_i ^ 32'ha4b1_7001;
      req_i <= '0;
      for (int unsigned lane = 0; lane < N; lane++) begin
        data_i[lane] <= choose_data(cfg_seed_i ^ 32'hdada_0000, lane);
      end
      valid_count_q <= 32'd0;
      grant_count_q <= 32'd0;
      stall_count_q <= 32'd0;
      ready_idle_count_q <= 32'd0;
      data_match_count_q <= 32'd0;
      data_mismatch_count_q <= 32'd0;
      priority_match_count_q <= 32'd0;
      priority_mismatch_count_q <= 32'd0;
      lane0_grant_count_q <= 32'd0;
      lane1_grant_count_q <= 32'd0;
      lane2_grant_count_q <= 32'd0;
      lane3_grant_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'hab17_e000;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_handshake_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i);

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        req_i <= next_req_w;
        for (int unsigned lane = 0; lane < N; lane++) begin
          data_i[lane] <= next_data_w[lane];
        end
        if (req_i == '0) begin
          pre_handshake_cycles_q <= pre_handshake_cycles_q + 32'd1;
        end
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        req_i <= (drain_cycle_q < N) ? (N'(1'b1) << drain_cycle_q[1:0]) : '0;
        for (int unsigned lane = 0; lane < N; lane++) begin
          data_i[lane] <= choose_data(rand_q ^ drain_cycle_q ^ 32'h5eed_0000, lane);
        end
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      if (valid_o) begin
        valid_count_q <= valid_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end
      if (accepted_w) begin
        grant_count_q <= grant_count_q + 32'd1;
        signature_q <= {signature_q[28:0], signature_q[31:29]} ^
                       {28'd0, gnt_o} ^ {30'd0, idx_o} ^ data_o;
        seen_q[3] <= 1'b1;
      end
      if (valid_o && !ready_i) begin
        stall_count_q <= stall_count_q + 32'd1;
        stalled_signature_q <= stalled_signature_q ^ global_cycle_q ^ {28'd0, req_i};
        seen_q[4] <= 1'b1;
      end
      if (!valid_o && ready_i) begin
        ready_idle_count_q <= ready_idle_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (priority_match_w && valid_o) begin
        priority_match_count_q <= priority_match_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (!priority_match_w || (accepted_w && gnt_o != expected_gnt_w)) begin
        priority_mismatch_count_q <= priority_mismatch_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (data_match_w && valid_o) begin
        data_match_count_q <= data_match_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (!data_match_w) begin
        data_mismatch_count_q <= data_mismatch_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (gnt_o[0]) begin
        lane0_grant_count_q <= lane0_grant_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (gnt_o[1]) begin
        lane1_grant_count_q <= lane1_grant_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (gnt_o[2]) begin
        lane2_grant_count_q <= lane2_grant_count_q + 32'd1;
        seen_q[12] <= 1'b1;
      end
      if (gnt_o[3]) begin
        lane3_grant_count_q <= lane3_grant_count_q + 32'd1;
        seen_q[13] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_req_valid_pct_i ^
                           cfg_rsp_valid_pct_i ^ cfg_access_ack_data_pct_i ^
                           32'ha4b1_7000;
  assign host_req_accepted_o = grant_count_q;
  assign device_req_accepted_o = valid_count_q;
  assign device_rsp_accepted_o = data_match_count_q;
  assign host_rsp_accepted_o = priority_match_count_q;
  assign rsp_queue_overflow_o = priority_mismatch_count_q + data_mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    4'd0,
    seen_q[13:0],
    req_i,
    gnt_o,
    idx_o,
    valid_o,
    ready_i,
    rst_ni,
    done_o
  };
  assign toggle_bitmap_word1_o = {
    4'd0,
    expected_gnt_w,
    expected_idx_w,
    priority_match_w,
    data_match_w,
    phase_w,
    req_i,
    gnt_o,
    idx_o,
    valid_o,
    ready_i,
    accepted_w,
    cfg_valid_i,
    global_cycle_q[5:0]
  };
  assign toggle_bitmap_word2_o = {
    grant_count_q[7:0],
    stall_count_q[7:0],
    data_match_count_q[7:0],
    priority_match_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = valid_count_q;
  assign real_toggle_subset_word1_o = grant_count_q;
  assign real_toggle_subset_word2_o = stall_count_q;
  assign real_toggle_subset_word3_o = ready_idle_count_q;
  assign real_toggle_subset_word4_o = data_match_count_q;
  assign real_toggle_subset_word5_o = data_mismatch_count_q;
  assign real_toggle_subset_word6_o = priority_match_count_q;
  assign real_toggle_subset_word7_o = priority_mismatch_count_q;
  assign real_toggle_subset_word8_o = lane0_grant_count_q;
  assign real_toggle_subset_word9_o = lane1_grant_count_q;
  assign real_toggle_subset_word10_o = lane2_grant_count_q;
  assign real_toggle_subset_word11_o = lane3_grant_count_q;
  assign real_toggle_subset_word12_o = traffic_cycle_q;
  assign real_toggle_subset_word13_o = drain_cycle_q;
  assign real_toggle_subset_word14_o = rand_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {24'd0, req_i, gnt_o};
  assign focused_wave_word1_o = {30'd0, idx_o};
  assign focused_wave_word2_o = {16'd0, data_o};
  assign focused_wave_word3_o = {16'd0, expected_data_w};
  assign focused_wave_word4_o = {26'd0, phase_w, ready_i, valid_o, accepted_w, done_o};
  assign focused_wave_word5_o = grant_count_q ^ stall_count_q;
  assign focused_wave_word6_o = priority_mismatch_count_q ^ data_mismatch_count_q;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = grant_count_q;
  assign oracle_expected_err_count_o = priority_mismatch_count_q;
  assign oracle_observed_ok_count_o = data_match_count_q;
  assign oracle_observed_err_count_o = data_mismatch_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    lane0_grant_count_q[7:0],
    lane1_grant_count_q[7:0],
    lane2_grant_count_q[7:0],
    lane3_grant_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {16'd0, data_o};
  assign oracle_semantic_case_acked_o = {16'd0, expected_data_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = rsp_queue_overflow_o;
  assign oracle_pre_handshake_traffic_cycles_o = pre_handshake_cycles_q;
endmodule : prim_arbiter_fixed_gpu_cov_tb
