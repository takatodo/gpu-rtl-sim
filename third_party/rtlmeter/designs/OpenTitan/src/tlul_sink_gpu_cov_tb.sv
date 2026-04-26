// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for tlul_sink.

module tlul_sink_gpu_cov_tb (
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
  import top_pkg::*;
  import tlul_pkg::*;

  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] TrafficPhase = 3'd1;
  localparam logic [2:0] DrainPhase   = 3'd2;
  localparam logic [2:0] DonePhase    = 3'd3;

  logic clk_i;
  logic rst_ni;
  logic [2:0] phase_w;

  tl_h2d_t tl_i;
  tl_d2h_t tl_o;
  logic request_err_w;
  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_state_q;
  logic [31:0] first_handshake_seen_q;
  logic [31:0] last_req_digest_q;
  logic [31:0] last_rsp_digest_q;

  logic req_fire_w;
  logic a_ack_w;
  logic d_ack_w;
  logic op_get_w;
  logic op_write_w;
  logic [31:0] req_digest_w;
  logic [31:0] rsp_digest_w;

  initial clk_i = 1'b0;
  always #5 clk_i = ~clk_i;

  tlul_sink dut (
    .clk_i,
    .rst_ni,
    .tl_i (tl_i),
    .tl_o (tl_o)
  );

  tlul_err req_oracle (
    .clk_i,
    .rst_ni,
    .tl_i  (tl_i),
    .err_o (request_err_w)
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1103515245 + 32'd12345;
  endfunction

  function automatic logic [31:0] clamp_pct(input logic [31:0] pct_raw);
    return (pct_raw > 32'd100) ? 32'd100 : pct_raw;
  endfunction

  function automatic logic pct_hit(input logic [31:0] state, input logic [31:0] pct_raw);
    return ((state % 32'd100) < clamp_pct(pct_raw));
  endfunction

  function automatic tl_a_op_e choose_opcode(input logic [31:0] state);
    logic [31:0] bucket;
    bucket = state % 32'd100;
    if (bucket < clamp_pct(cfg_put_full_pct_i)) begin
      return PutFullData;
    end
    if (bucket < (clamp_pct(cfg_put_full_pct_i) + clamp_pct(cfg_put_partial_pct_i))) begin
      return PutPartialData;
    end
    return Get;
  endfunction

  function automatic logic [TL_AW-1:0] choose_address(input logic [31:0] state);
    return TL_AW'(cfg_address_base_i | (state & cfg_address_mask_i));
  endfunction

  function automatic logic [TL_DBW-1:0] choose_mask(
    input logic [31:0] state,
    input tl_a_op_e opcode
  );
    logic [TL_DBW-1:0] mask;
    mask = TL_DBW'(state[TL_DBW-1:0]);
    if (mask == '0) begin
      mask = TL_DBW'(4'b1111);
    end
    if (opcode == Get && state[8]) begin
      mask = TL_DBW'(4'b1111);
    end
    return mask;
  endfunction

  function automatic prim_mubi_pkg::mubi4_t choose_instr_type(input logic [31:0] state);
    if ((state % 32'd100) < 32'd10) begin
      return prim_mubi_pkg::mubi4_t'(4'h0);
    end
    return prim_mubi_pkg::MuBi4False;
  endfunction

  function automatic logic [31:0] request_digest(input tl_h2d_t tl);
    logic [31:0] digest;
    digest = {24'd0, tl.a_opcode, tl.a_size, tl.a_param[0]};
    digest ^= tl.a_address;
    digest ^= tl.a_data;
    digest ^= {24'd0, tl.a_mask, tl.a_source};
    digest ^= {28'd0, tl.a_user.instr_type};
    return digest;
  endfunction

  function automatic logic [31:0] response_digest(input tl_d2h_t tl);
    logic [31:0] digest;
    digest = {24'd0, tl.d_opcode, tl.d_size, tl.d_error, tl.d_valid, tl.a_ready};
    digest ^= tl.d_data;
    digest ^= {24'd0, tl.d_source, tl.d_sink, tl.d_param[1:0]};
    return digest;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);

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

  always_comb begin
    tl_i = TL_H2D_DEFAULT;
    req_fire_w = 1'b0;
    tl_i.d_ready = pct_hit(rand_state_q ^ 32'h99aa_7733, cfg_host_d_ready_pct_i);
    if (cfg_valid_i && phase_w == TrafficPhase && tl_o.a_ready && pct_hit(rand_state_q, cfg_req_valid_pct_i)) begin
      tl_i.a_valid = 1'b1;
      tl_i.a_opcode = choose_opcode(rand_state_q ^ 32'h0f0f_aaaa);
      tl_i.a_param = '0;
      tl_i.a_size = TL_SZW'((rand_state_q >> 2) % 3);
      tl_i.a_source = TL_AIW'((rand_state_q >> 8) & cfg_source_mask_i[TL_AIW-1:0]);
      tl_i.a_address = choose_address(rand_state_q ^ 32'h1234_5678);
      tl_i.a_mask = choose_mask(rand_state_q ^ 32'h3333_6666, tl_i.a_opcode);
      tl_i.a_data = (rand_state_q ^ cfg_req_data_hi_xor_i) + 32'h5566_7788;
      tl_i.a_user = TL_A_USER_DEFAULT;
      tl_i.a_user.instr_type = choose_instr_type(rand_state_q ^ 32'hdead_beef);
      tl_i.a_user.cmd_intg = get_cmd_intg(tl_i);
      tl_i.a_user.data_intg = get_data_intg(tl_i.a_data);
      req_fire_w = 1'b1;
    end
  end

  assign a_ack_w = tl_i.a_valid && tl_o.a_ready;
  assign d_ack_w = tl_o.d_valid && tl_i.d_ready;
  assign op_get_w = a_ack_w && (tl_i.a_opcode == Get);
  assign op_write_w = a_ack_w && ((tl_i.a_opcode == PutFullData) || (tl_i.a_opcode == PutPartialData));
  assign req_digest_w = request_digest(tl_i);
  assign rsp_digest_w = response_digest(tl_o);

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= '0;
      traffic_cycle_q <= '0;
      drain_cycle_q <= '0;
      rand_state_q <= cfg_seed_i ^ 32'h2468_ace1;
      first_handshake_seen_q <= '0;
      host_req_accepted_o <= '0;
      device_req_accepted_o <= '0;
      device_rsp_accepted_o <= '0;
      host_rsp_accepted_o <= '0;
      rsp_queue_overflow_o <= '0;
      oracle_expected_ok_count_o <= '0;
      oracle_expected_err_count_o <= '0;
      oracle_observed_ok_count_o <= '0;
      oracle_observed_err_count_o <= '0;
      oracle_semantic_family_seen_o <= '0;
      oracle_semantic_family_acked_o <= '0;
      oracle_semantic_case_seen_o <= '0;
      oracle_semantic_case_acked_o <= '0;
      oracle_req_signature_o <= '0;
      oracle_stalled_req_signature_o <= '0;
      oracle_pre_handshake_traffic_cycles_o <= '0;
      last_req_digest_q <= '0;
      last_rsp_digest_q <= '0;
    end else begin
      global_cycle_q <= global_cycle_q + 32'd1;
      rand_state_q <= prng_next(rand_state_q);
      if (!rst_ni) begin
        traffic_cycle_q <= '0;
        drain_cycle_q <= '0;
      end else begin
        if (phase_w == TrafficPhase) begin
          traffic_cycle_q <= traffic_cycle_q + 32'd1;
          if (!first_handshake_seen_q) begin
            oracle_pre_handshake_traffic_cycles_o <= oracle_pre_handshake_traffic_cycles_o + 32'd1;
          end
        end
        if (phase_w == DrainPhase) begin
          drain_cycle_q <= drain_cycle_q + 32'd1;
        end
        if (tl_i.a_valid && !tl_o.a_ready) begin
          rsp_queue_overflow_o <= rsp_queue_overflow_o + 32'd1;
          oracle_stalled_req_signature_o <= oracle_stalled_req_signature_o ^ req_digest_w;
        end
        if (a_ack_w) begin
          first_handshake_seen_q <= 32'd1;
          host_req_accepted_o <= host_req_accepted_o + 32'd1;
          device_req_accepted_o <= device_req_accepted_o + 32'd1;
          oracle_req_signature_o <= oracle_req_signature_o ^ req_digest_w;
          last_req_digest_q <= req_digest_w;
          if (request_err_w) begin
            oracle_expected_err_count_o <= oracle_expected_err_count_o + 32'd1;
          end else begin
            oracle_expected_ok_count_o <= oracle_expected_ok_count_o + 32'd1;
          end
          oracle_semantic_family_seen_o[0] <= 1'b1;
          oracle_semantic_family_seen_o[1] <= oracle_semantic_family_seen_o[1] | request_err_w;
          oracle_semantic_family_seen_o[2] <= oracle_semantic_family_seen_o[2] | op_write_w;
          oracle_semantic_family_seen_o[3] <= oracle_semantic_family_seen_o[3] | op_get_w;
          oracle_semantic_family_seen_o[4] <= 1'b1;
          oracle_semantic_case_seen_o <= oracle_semantic_case_seen_o |
                                         {27'd0, op_get_w, op_write_w, request_err_w, tl_i.a_valid, a_ack_w};
        end
        if (tl_o.d_valid) begin
          device_rsp_accepted_o <= device_rsp_accepted_o + 32'd1;
          oracle_semantic_family_seen_o[3] <= 1'b1;
        end
        if (d_ack_w) begin
          host_rsp_accepted_o <= host_rsp_accepted_o + 32'd1;
          last_rsp_digest_q <= rsp_digest_w;
          if (tl_o.d_error) begin
            oracle_observed_err_count_o <= oracle_observed_err_count_o + 32'd1;
          end else begin
            oracle_observed_ok_count_o <= oracle_observed_ok_count_o + 32'd1;
          end
          oracle_semantic_family_acked_o[0] <= 1'b1;
          oracle_semantic_family_acked_o[1] <= oracle_semantic_family_acked_o[1] | tl_o.d_error;
          oracle_semantic_family_acked_o[2] <= oracle_semantic_family_acked_o[2] | (tl_o.d_opcode == AccessAckData);
          oracle_semantic_family_acked_o[3] <= 1'b1;
          oracle_semantic_family_acked_o[4] <= 1'b1;
          oracle_semantic_case_acked_o <= oracle_semantic_case_acked_o |
                                          {27'd0, tl_o.d_error, tl_o.d_opcode == AccessAckData, d_ack_w, tl_o.d_valid, tl_i.d_ready};
        end
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_batch_length_i ^ cfg_req_valid_pct_i ^ cfg_host_d_ready_pct_i ^
                           cfg_put_full_pct_i ^ cfg_put_partial_pct_i ^ cfg_seed_i;
  assign progress_cycle_count_o = traffic_cycle_q + host_rsp_accepted_o;
  assign progress_signature_o = oracle_req_signature_o ^ last_rsp_digest_q ^ {29'd0, phase_w};
  assign oracle_req_signature_delta_o = oracle_req_signature_o ^ oracle_stalled_req_signature_o;
  assign oracle_req_stable_violation_o = 32'd0;

  assign toggle_bitmap_word0_o = {
    done_o,
    tl_i.a_valid,
    tl_o.a_ready,
    tl_o.d_valid,
    tl_i.d_ready,
    a_ack_w,
    d_ack_w,
    tl_o.d_error,
    oracle_semantic_family_seen_o[7:0],
    oracle_semantic_family_acked_o[7:0],
    host_req_accepted_o[7:0]
  };
  assign toggle_bitmap_word1_o = host_rsp_accepted_o ^ device_rsp_accepted_o ^ oracle_expected_err_count_o ^
                                 oracle_observed_err_count_o;
  assign toggle_bitmap_word2_o = oracle_req_signature_o ^ oracle_stalled_req_signature_o ^ progress_signature_o;

  assign real_toggle_subset_word0_o = host_req_accepted_o;
  assign real_toggle_subset_word1_o = device_req_accepted_o;
  assign real_toggle_subset_word2_o = device_rsp_accepted_o;
  assign real_toggle_subset_word3_o = host_rsp_accepted_o;
  assign real_toggle_subset_word4_o = oracle_expected_ok_count_o;
  assign real_toggle_subset_word5_o = oracle_expected_err_count_o;
  assign real_toggle_subset_word6_o = oracle_observed_ok_count_o;
  assign real_toggle_subset_word7_o = oracle_observed_err_count_o;
  assign real_toggle_subset_word8_o = oracle_semantic_family_seen_o;
  assign real_toggle_subset_word9_o = oracle_semantic_family_acked_o;
  assign real_toggle_subset_word10_o = oracle_semantic_case_seen_o;
  assign real_toggle_subset_word11_o = oracle_semantic_case_acked_o;
  assign real_toggle_subset_word12_o = oracle_req_signature_o;
  assign real_toggle_subset_word13_o = oracle_stalled_req_signature_o;
  assign real_toggle_subset_word14_o = oracle_req_signature_delta_o;
  assign real_toggle_subset_word15_o = oracle_pre_handshake_traffic_cycles_o;
  assign real_toggle_subset_word16_o = last_req_digest_q;
  assign real_toggle_subset_word17_o = last_rsp_digest_q;

  assign focused_wave_word0_o = global_cycle_q;
  assign focused_wave_word1_o = progress_cycle_count_o;
  assign focused_wave_word2_o = last_req_digest_q;
  assign focused_wave_word3_o = last_rsp_digest_q;
  assign focused_wave_word4_o = {24'd0, phase_w, tl_o.d_opcode, tl_i.a_opcode};
  assign focused_wave_word5_o = cfg_signature_o;
  assign focused_wave_word6_o = progress_signature_o;
  assign focused_wave_word7_o = {24'd0, tl_o.d_error, tl_o.d_valid, tl_o.a_ready, tl_i.a_valid, tl_i.d_ready, a_ack_w, d_ack_w};

endmodule
