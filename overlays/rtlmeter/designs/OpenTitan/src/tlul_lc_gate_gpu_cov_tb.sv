// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Minimal deterministic coverage harness for tlul_lc_gate.

module tlul_lc_gate_gpu_cov_tb (
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
  import lc_ctrl_pkg::*;

  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] TrafficPhase = 3'd1;
  localparam logic [2:0] DrainPhase   = 3'd2;
  localparam logic [2:0] DonePhase    = 3'd3;

  logic clk_i;
  logic rst_ni;
  logic [2:0] phase_w;

  tl_h2d_t tl_h2d_i;
  tl_d2h_t tl_d2h_o;
  tl_h2d_t tl_h2d_device_w;
  tl_d2h_t tl_d2h_device_pre_w;
  tl_d2h_t tl_d2h_device_w;

  lc_tx_t lc_en_w;
  logic flush_req_w;
  logic flush_ack_w;
  logic resp_pending_w;
  logic err_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_state_q;
  logic first_handshake_seen_q;
  logic device_rsp_pending_q;
  tl_a_op_e device_rsp_opcode_q;
  logic [TL_SZW-1:0] device_rsp_size_q;
  logic [TL_AIW-1:0] device_rsp_source_q;
  logic [TL_DW-1:0] device_rsp_data_q;
  logic device_rsp_error_q;
  logic [31:0] lc_off_cycle_count_q;
  logic [31:0] flush_req_count_q;
  logic [31:0] flush_ack_count_q;
  logic [31:0] resp_pending_count_q;
  logic [31:0] lc_error_count_q;
  logic [31:0] gated_req_count_q;
  logic [31:0] passthrough_req_count_q;
  logic [31:0] device_stall_count_q;
  logic [31:0] host_stall_count_q;
  logic [31:0] last_req_digest_q;
  logic [31:0] last_rsp_digest_q;
  logic [31:0] gate_signature_q;
  logic [31:0] device_signature_q;

  logic host_req_fire_w;
  logic device_req_fire_w;
  logic device_rsp_fire_w;
  logic host_rsp_fire_w;
  logic host_stall_w;
  logic device_stall_w;
  logic lc_off_w;
  logic [31:0] req_digest_w;
  logic [31:0] device_req_digest_w;
  logic [31:0] rsp_digest_w;

  initial begin
    clk_i = 1'b0;
    rst_ni = 1'b0;
  end
  always #5 clk_i = ~clk_i;

  tlul_lc_gate #(
    .NumGatesPerDirection(2),
    .ReturnBlankResp(0),
    .Outstanding(2)
  ) dut (
    .clk_i,
    .rst_ni,
    .tl_h2d_i      (tl_h2d_i),
    .tl_d2h_o      (tl_d2h_o),
    .tl_h2d_o      (tl_h2d_device_w),
    .tl_d2h_i      (tl_d2h_device_w),
    .flush_req_i   (flush_req_w),
    .flush_ack_o   (flush_ack_w),
    .resp_pending_o(resp_pending_w),
    .lc_en_i       (lc_en_w),
    .err_o         (err_w)
  );

  tlul_rsp_intg_gen device_rsp_intg (
    .tl_i(tl_d2h_device_pre_w),
    .tl_o(tl_d2h_device_w)
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
    logic [31:0] put_full_limit;
    logic [31:0] put_any_limit;
    logic [31:0] bucket;
    put_full_limit = clamp_pct(cfg_put_full_pct_i);
    put_any_limit = clamp_pct(cfg_put_full_pct_i) + clamp_pct(cfg_put_partial_pct_i);
    bucket = state % 32'd100;
    if (bucket < put_full_limit) begin
      return PutFullData;
    end
    if (bucket < put_any_limit) begin
      return PutPartialData;
    end
    return Get;
  endfunction

  function automatic logic [TL_AW-1:0] choose_address(input logic [31:0] state);
    logic [TL_AW-1:0] addr;
    addr = TL_AW'(cfg_address_base_i | ((state ^ cfg_req_address_mode_i) & cfg_address_mask_i));
    return {addr[TL_AW-1:2], 2'b00};
  endfunction

  function automatic logic [TL_DBW-1:0] choose_mask(
    input logic [31:0] state,
    input tl_a_op_e opcode
  );
    logic [TL_DBW-1:0] mask;
    if (opcode == Get || opcode == PutFullData) begin
      return TL_DBW'(4'b1111);
    end
    mask = TL_DBW'(state[TL_DBW-1:0]);
    if (mask == '0) begin
      return TL_DBW'(4'b0001);
    end
    if (&mask) begin
      return TL_DBW'(4'b0111);
    end
    return mask;
  endfunction

  function automatic logic [31:0] request_digest(input tl_h2d_t tl);
    logic [31:0] digest;
    digest = 32'(tl.a_opcode) ^ 32'(tl.a_size) ^ 32'(tl.a_param);
    digest ^= tl.a_address;
    digest ^= tl.a_data;
    digest ^= 32'(tl.a_mask) ^ 32'(tl.a_source);
    digest ^= 32'(tl.a_user.instr_type);
    return digest;
  endfunction

  function automatic logic [31:0] response_digest(input tl_d2h_t tl);
    logic [31:0] digest;
    digest = 32'(tl.d_opcode) ^ 32'(tl.d_size) ^ 32'(tl.d_param);
    digest ^= tl.d_data;
    digest ^= 32'(tl.d_source) ^ 32'(tl.d_sink);
    digest ^= {29'd0, tl.d_error, tl.d_valid, tl.a_ready};
    return digest;
  endfunction

  always_comb begin
    if (!rst_ni) begin
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
    tl_h2d_i = TL_H2D_DEFAULT;
    tl_h2d_i.a_valid = (phase_w == TrafficPhase) && pct_hit(rand_state_q, cfg_req_valid_pct_i);
    tl_h2d_i.a_opcode = choose_opcode(rand_state_q ^ cfg_req_family_i);
    tl_h2d_i.a_param = 3'd0;
    tl_h2d_i.a_size = TL_SZW'(2);
    tl_h2d_i.a_source = TL_AIW'((rand_state_q >> 8) & cfg_source_mask_i);
    tl_h2d_i.a_address = choose_address(rand_state_q);
    tl_h2d_i.a_mask = choose_mask(rand_state_q >> 4, tl_h2d_i.a_opcode);
    tl_h2d_i.a_data = rand_state_q ^ cfg_req_data_mode_i ^ {cfg_req_data_hi_xor_i[15:0], 16'h51c7};
    tl_h2d_i.a_user = TL_A_USER_DEFAULT;
    tl_h2d_i.a_user.instr_type = pct_hit(rand_state_q ^ 32'h1357_2468, 32'd8) ?
                                 prim_mubi_pkg::MuBi4True : prim_mubi_pkg::MuBi4False;
    tl_h2d_i.d_ready = (phase_w == DrainPhase) ||
                       pct_hit(rand_state_q ^ 32'h0d1e_5eed, cfg_host_d_ready_pct_i);
  end

  always_comb begin
    lc_en_w = pct_hit(rand_state_q ^ cfg_rsp_family_i ^ 32'h1c9a_7e11, cfg_rsp_error_pct_i) ?
              Off : On;
    flush_req_w = (phase_w == TrafficPhase) &&
                  pct_hit(rand_state_q ^ cfg_rsp_delay_mode_i ^ 32'h51a5_0001,
                          cfg_rsp_delay_max_i);
  end

  always_comb begin
    tl_d2h_device_pre_w = TL_D2H_DEFAULT;
    tl_d2h_device_pre_w.a_ready = pct_hit(rand_state_q ^ 32'hd00d_5eed,
                                          cfg_device_a_ready_pct_i);
    tl_d2h_device_pre_w.d_valid = device_rsp_pending_q &&
                                  ((phase_w == DrainPhase) ||
                                   pct_hit(rand_state_q ^ cfg_rsp_family_i,
                                           cfg_rsp_valid_pct_i));
    tl_d2h_device_pre_w.d_opcode = (device_rsp_opcode_q == Get) ? AccessAckData : AccessAck;
    tl_d2h_device_pre_w.d_param = 3'd0;
    tl_d2h_device_pre_w.d_size = device_rsp_size_q;
    tl_d2h_device_pre_w.d_source = device_rsp_source_q;
    tl_d2h_device_pre_w.d_sink = '0;
    tl_d2h_device_pre_w.d_data = device_rsp_data_q ^ cfg_rsp_data_mode_i ^
                                 {cfg_rsp_data_hi_xor_i[15:0], 16'hac71};
    tl_d2h_device_pre_w.d_user = TL_D_USER_DEFAULT;
    tl_d2h_device_pre_w.d_error = device_rsp_error_q;
  end

  assign host_req_fire_w = tl_h2d_i.a_valid && tl_d2h_o.a_ready;
  assign device_req_fire_w = tl_h2d_device_w.a_valid && tl_d2h_device_w.a_ready;
  assign device_rsp_fire_w = tl_d2h_device_w.d_valid && tl_h2d_device_w.d_ready;
  assign host_rsp_fire_w = tl_d2h_o.d_valid && tl_h2d_i.d_ready;
  assign host_stall_w = tl_h2d_i.a_valid && !tl_d2h_o.a_ready;
  assign device_stall_w = tl_h2d_device_w.a_valid && !tl_d2h_device_w.a_ready;
  assign lc_off_w = lc_tx_test_false_loose(lc_en_w);
  assign req_digest_w = request_digest(tl_h2d_i);
  assign device_req_digest_w = request_digest(tl_h2d_device_w);
  assign rsp_digest_w = response_digest(tl_d2h_o);

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      rst_ni <= 1'b0;
      global_cycle_q <= 32'd0;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_state_q <= (cfg_seed_i == 32'd0) ? 32'h1bad_f00d : cfg_seed_i;
      first_handshake_seen_q <= 1'b0;
      device_rsp_pending_q <= 1'b0;
      device_rsp_opcode_q <= Get;
      device_rsp_size_q <= '0;
      device_rsp_source_q <= '0;
      device_rsp_data_q <= '0;
      device_rsp_error_q <= 1'b0;
      host_req_accepted_o <= 32'd0;
      device_req_accepted_o <= 32'd0;
      device_rsp_accepted_o <= 32'd0;
      host_rsp_accepted_o <= 32'd0;
      rsp_queue_overflow_o <= 32'd0;
      oracle_expected_ok_count_o <= 32'd0;
      oracle_expected_err_count_o <= 32'd0;
      oracle_observed_ok_count_o <= 32'd0;
      oracle_observed_err_count_o <= 32'd0;
      oracle_semantic_family_seen_o <= 32'd0;
      oracle_semantic_family_acked_o <= 32'd0;
      oracle_semantic_case_seen_o <= 32'd0;
      oracle_semantic_case_acked_o <= 32'd0;
      oracle_req_signature_o <= 32'd0;
      oracle_stalled_req_signature_o <= 32'd0;
      oracle_pre_handshake_traffic_cycles_o <= 32'd0;
      lc_off_cycle_count_q <= 32'd0;
      flush_req_count_q <= 32'd0;
      flush_ack_count_q <= 32'd0;
      resp_pending_count_q <= 32'd0;
      lc_error_count_q <= 32'd0;
      gated_req_count_q <= 32'd0;
      passthrough_req_count_q <= 32'd0;
      device_stall_count_q <= 32'd0;
      host_stall_count_q <= 32'd0;
      last_req_digest_q <= 32'd0;
      last_rsp_digest_q <= 32'd0;
      gate_signature_q <= 32'd0;
      device_signature_q <= 32'd0;
    end else begin
      global_cycle_q <= global_cycle_q + 32'd1;
      rand_state_q <= prng_next(rand_state_q ^ cfg_req_fill_target_i ^ cfg_rsp_fill_target_i);
      rst_ni <= (global_cycle_q >= cfg_reset_cycles_i);

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
      end

      if (rst_ni) begin
        if (lc_off_w) begin
          lc_off_cycle_count_q <= lc_off_cycle_count_q + 32'd1;
        end
        if (flush_req_w) begin
          flush_req_count_q <= flush_req_count_q + 32'd1;
        end
        if (flush_ack_w) begin
          flush_ack_count_q <= flush_ack_count_q + 32'd1;
        end
        if (resp_pending_w) begin
          resp_pending_count_q <= resp_pending_count_q + 32'd1;
        end
        if (err_w) begin
          lc_error_count_q <= lc_error_count_q + 32'd1;
        end
        if (host_stall_w) begin
          host_stall_count_q <= host_stall_count_q + 32'd1;
          oracle_stalled_req_signature_o <= oracle_stalled_req_signature_o ^ req_digest_w;
        end
        if (device_stall_w) begin
          device_stall_count_q <= device_stall_count_q + 32'd1;
          rsp_queue_overflow_o <= rsp_queue_overflow_o + 32'd1;
        end
        if (!first_handshake_seen_q && (phase_w == TrafficPhase)) begin
          oracle_pre_handshake_traffic_cycles_o <= oracle_pre_handshake_traffic_cycles_o + 32'd1;
        end
        if (host_req_fire_w) begin
          first_handshake_seen_q <= 1'b1;
          host_req_accepted_o <= host_req_accepted_o + 32'd1;
          oracle_req_signature_o <= oracle_req_signature_o ^ req_digest_w;
          last_req_digest_q <= req_digest_w;
          if (lc_off_w || err_w) begin
            gated_req_count_q <= gated_req_count_q + 32'd1;
            oracle_expected_err_count_o <= oracle_expected_err_count_o + 32'd1;
          end else begin
            oracle_expected_ok_count_o <= oracle_expected_ok_count_o + 32'd1;
          end
          oracle_semantic_family_seen_o[0] <= 1'b1;
          oracle_semantic_family_seen_o[1] <= oracle_semantic_family_seen_o[1] | lc_off_w;
          oracle_semantic_family_seen_o[2] <= oracle_semantic_family_seen_o[2] | flush_req_w;
          oracle_semantic_family_seen_o[3] <= oracle_semantic_family_seen_o[3] | err_w;
          oracle_semantic_case_seen_o <= oracle_semantic_case_seen_o |
                                         {26'd0, err_w, flush_req_w, lc_off_w,
                                          tl_h2d_i.a_opcode == Get, tl_h2d_i.a_valid,
                                          tl_d2h_o.a_ready};
        end
        if (device_req_fire_w) begin
          passthrough_req_count_q <= passthrough_req_count_q + 32'd1;
          device_req_accepted_o <= device_req_accepted_o + 32'd1;
          device_rsp_pending_q <= 1'b1;
          device_rsp_opcode_q <= tl_h2d_device_w.a_opcode;
          device_rsp_size_q <= tl_h2d_device_w.a_size;
          device_rsp_source_q <= tl_h2d_device_w.a_source;
          device_rsp_data_q <= device_req_digest_w ^ cfg_access_ack_data_pct_i;
          device_rsp_error_q <= pct_hit(rand_state_q ^ 32'hea77_0001, cfg_rsp_error_pct_i);
          device_signature_q <= device_signature_q ^ device_req_digest_w;
        end
        if (device_rsp_fire_w) begin
          device_rsp_pending_q <= 1'b0;
          device_rsp_accepted_o <= device_rsp_accepted_o + 32'd1;
        end
        if (host_rsp_fire_w) begin
          host_rsp_accepted_o <= host_rsp_accepted_o + 32'd1;
          last_rsp_digest_q <= rsp_digest_w;
          if (tl_d2h_o.d_error) begin
            oracle_observed_err_count_o <= oracle_observed_err_count_o + 32'd1;
          end else begin
            oracle_observed_ok_count_o <= oracle_observed_ok_count_o + 32'd1;
          end
          oracle_semantic_family_acked_o[0] <= 1'b1;
          oracle_semantic_family_acked_o[1] <= oracle_semantic_family_acked_o[1] |
                                               tl_d2h_o.d_error;
          oracle_semantic_family_acked_o[2] <= oracle_semantic_family_acked_o[2] |
                                               flush_ack_w;
          oracle_semantic_family_acked_o[3] <= oracle_semantic_family_acked_o[3] |
                                               resp_pending_w;
          oracle_semantic_case_acked_o <= oracle_semantic_case_acked_o |
                                          {26'd0, resp_pending_w, flush_ack_w,
                                           tl_d2h_o.d_error,
                                           tl_d2h_o.d_opcode == AccessAckData,
                                           tl_d2h_o.d_valid, host_rsp_fire_w};
          gate_signature_q <= gate_signature_q ^ rsp_digest_w ^ {31'd0, err_w};
        end
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_batch_length_i ^ cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           cfg_host_d_ready_pct_i ^ cfg_device_a_ready_pct_i ^
                           cfg_put_full_pct_i ^ cfg_put_partial_pct_i ^ cfg_seed_i ^
                           cfg_rsp_error_pct_i ^ cfg_rsp_delay_max_i;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q + host_rsp_accepted_o;
  assign progress_signature_o = oracle_req_signature_o ^ last_rsp_digest_q ^
                                gate_signature_q ^ device_signature_q ^ {29'd0, phase_w};
  assign oracle_req_signature_delta_o = oracle_req_signature_o ^ oracle_stalled_req_signature_o;
  assign oracle_req_stable_violation_o = 32'd0;

  assign toggle_bitmap_word0_o = {
    1'b0,
    done_o,
    tl_h2d_i.a_valid,
    tl_d2h_o.a_ready,
    tl_h2d_device_w.a_valid,
    tl_d2h_device_w.a_ready,
    tl_d2h_o.d_valid,
    tl_h2d_i.d_ready,
    lc_off_w,
    flush_req_w,
    flush_ack_w,
    resp_pending_w,
    err_w,
    host_req_accepted_o[7:0],
    host_rsp_accepted_o[7:0],
    phase_w
  };
  assign toggle_bitmap_word1_o = oracle_semantic_family_seen_o ^
                                 oracle_semantic_family_acked_o ^
                                 lc_off_cycle_count_q;
  assign toggle_bitmap_word2_o = gate_signature_q ^ device_signature_q ^
                                 oracle_req_signature_delta_o;

  assign real_toggle_subset_word0_o = host_req_accepted_o;
  assign real_toggle_subset_word1_o = device_req_accepted_o;
  assign real_toggle_subset_word2_o = device_rsp_accepted_o;
  assign real_toggle_subset_word3_o = host_rsp_accepted_o;
  assign real_toggle_subset_word4_o = gated_req_count_q;
  assign real_toggle_subset_word5_o = passthrough_req_count_q;
  assign real_toggle_subset_word6_o = lc_off_cycle_count_q;
  assign real_toggle_subset_word7_o = flush_req_count_q;
  assign real_toggle_subset_word8_o = flush_ack_count_q;
  assign real_toggle_subset_word9_o = resp_pending_count_q;
  assign real_toggle_subset_word10_o = lc_error_count_q;
  assign real_toggle_subset_word11_o = host_stall_count_q;
  assign real_toggle_subset_word12_o = device_stall_count_q;
  assign real_toggle_subset_word13_o = oracle_req_signature_o;
  assign real_toggle_subset_word14_o = oracle_stalled_req_signature_o;
  assign real_toggle_subset_word15_o = gate_signature_q;
  assign real_toggle_subset_word16_o = last_req_digest_q;
  assign real_toggle_subset_word17_o = last_rsp_digest_q;

  assign focused_wave_word0_o = global_cycle_q;
  assign focused_wave_word1_o = progress_cycle_count_o;
  assign focused_wave_word2_o = {22'd0, phase_w, lc_en_w, flush_req_w, flush_ack_w, err_w};
  assign focused_wave_word3_o = last_req_digest_q;
  assign focused_wave_word4_o = last_rsp_digest_q;
  assign focused_wave_word5_o = cfg_signature_o;
  assign focused_wave_word6_o = progress_signature_o;
  assign focused_wave_word7_o = {24'd0, tl_d2h_o.d_error, tl_d2h_o.d_valid, tl_d2h_o.a_ready,
                                 tl_h2d_i.a_valid, tl_h2d_i.d_ready, resp_pending_w,
                                 lc_off_w, flush_req_w};

endmodule
