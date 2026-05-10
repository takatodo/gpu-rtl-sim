// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Minimal deterministic coverage harness for tlul_cmd_intg_chk.

module tlul_cmd_intg_chk_gpu_cov_tb (
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

  tl_h2d_t raw_tl;
  tl_h2d_t gen_tl;
  tl_h2d_t chk_tl;
  logic err_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_state_q;
  logic first_handshake_seen_q;
  logic [31:0] last_req_digest_q;
  logic [31:0] last_rsp_digest_q;
  logic [31:0] cmd_corrupt_count_q;
  logic [31:0] data_corrupt_count_q;
  logic [31:0] both_corrupt_count_q;
  logic [31:0] clean_req_count_q;
  logic [31:0] write_req_count_q;

  logic req_fire_w;
  logic op_get_w;
  logic op_write_w;
  logic cmd_corrupt_w;
  logic data_corrupt_w;
  logic both_corrupt_w;
  logic expected_err_w;
  logic [31:0] req_digest_w;
  logic [31:0] rsp_digest_w;

  initial clk_i = 1'b0;
  always #5 clk_i = ~clk_i;

  tlul_cmd_intg_gen u_ref_gen (
    .tl_i (raw_tl),
    .tl_o (gen_tl)
  );

  tlul_cmd_intg_chk dut (
    .tl_i  (chk_tl),
    .err_o (err_w)
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

  function automatic logic [TL_SZW-1:0] choose_size(input logic [31:0] state);
    if (pct_hit(state ^ 32'hca11_51e0, cfg_access_ack_data_pct_i)) begin
      return TL_SZW'(2);
    end
    return TL_SZW'((state >> 2) % 3);
  endfunction

  function automatic logic [TL_DBW-1:0] choose_mask(
    input logic [31:0] state,
    input tl_a_op_e opcode,
    input logic [TL_SZW-1:0] size
  );
    logic [TL_DBW-1:0] mask;
    if (opcode == Get || opcode == PutFullData) begin
      return size == TL_SZW'(0) ? TL_DBW'(4'b0001) :
             size == TL_SZW'(1) ? TL_DBW'(4'b0011) :
                                  TL_DBW'(4'b1111);
    end
    mask = TL_DBW'(state[TL_DBW-1:0]);
    return (mask == '0) ? TL_DBW'(4'b0001) : mask;
  endfunction

  function automatic prim_mubi_pkg::mubi4_t choose_instr_type(input logic [31:0] state);
    if ((state % 32'd100) < 32'd12) begin
      return prim_mubi_pkg::MuBi4True;
    end
    return prim_mubi_pkg::MuBi4False;
  endfunction

  function automatic logic [31:0] request_digest(input tl_h2d_t tl);
    logic [31:0] digest;
    digest = 32'(tl.a_opcode) ^ 32'(tl.a_size) ^ 32'(tl.a_param);
    digest ^= tl.a_address;
    digest ^= tl.a_data;
    digest ^= 32'(tl.a_mask) ^ 32'(tl.a_source);
    digest ^= 32'(tl.a_user.cmd_intg) ^ 32'(tl.a_user.data_intg);
    digest ^= 32'(tl.a_user.instr_type);
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
    raw_tl = TL_H2D_DEFAULT;
    if (cfg_valid_i && phase_w == TrafficPhase &&
        pct_hit(rand_state_q ^ cfg_req_family_i, cfg_req_valid_pct_i)) begin
      raw_tl.a_valid = 1'b1;
      raw_tl.a_opcode = choose_opcode(rand_state_q ^ 32'h0f0f_aaaa);
      raw_tl.a_param = 3'd0;
      raw_tl.a_size = choose_size(rand_state_q ^ cfg_rsp_family_i);
      raw_tl.a_source = TL_AIW'((rand_state_q >> 8) & cfg_source_mask_i[TL_AIW-1:0]);
      raw_tl.a_address = TL_AW'(cfg_address_base_i |
                                ((rand_state_q ^ cfg_req_address_mode_i) &
                                 cfg_address_mask_i));
      raw_tl.a_mask = choose_mask(rand_state_q ^ 32'h3333_6666,
                                  raw_tl.a_opcode,
                                  raw_tl.a_size);
      raw_tl.a_data = rand_state_q ^ cfg_req_data_mode_i ^
                      {cfg_req_data_hi_xor_i[15:0], 16'hc1c1};
      raw_tl.a_user = TL_A_USER_DEFAULT;
      raw_tl.a_user.instr_type = choose_instr_type(rand_state_q ^ 32'hdead_beef);
    end
  end

  assign req_fire_w = gen_tl.a_valid;
  assign op_get_w = req_fire_w && (gen_tl.a_opcode == Get);
  assign op_write_w = req_fire_w && ((gen_tl.a_opcode == PutFullData) ||
                                     (gen_tl.a_opcode == PutPartialData));
  assign cmd_corrupt_w = req_fire_w &&
                         pct_hit(rand_state_q ^ 32'hc0de_c0de, cfg_rsp_error_pct_i);
  assign data_corrupt_w = req_fire_w &&
                          pct_hit(rand_state_q ^ 32'hdada_1a7a, cfg_rsp_fill_target_i);
  assign both_corrupt_w = cmd_corrupt_w && data_corrupt_w;
  assign expected_err_w = req_fire_w && (cmd_corrupt_w || data_corrupt_w);

  always_comb begin
    chk_tl = gen_tl;
    if (cmd_corrupt_w) begin
      chk_tl.a_user.cmd_intg[0] = ~gen_tl.a_user.cmd_intg[0];
    end
    if (data_corrupt_w) begin
      chk_tl.a_user.data_intg[0] = ~gen_tl.a_user.data_intg[0];
    end
  end

  assign req_digest_w = request_digest(chk_tl);
  assign rsp_digest_w = req_digest_w ^ {30'd0, expected_err_w, err_w};

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= 32'd0;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_state_q <= cfg_seed_i ^ 32'hc1c0_0001;
      first_handshake_seen_q <= 1'b0;
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
      last_req_digest_q <= 32'd0;
      last_rsp_digest_q <= 32'd0;
      cmd_corrupt_count_q <= 32'd0;
      data_corrupt_count_q <= 32'd0;
      both_corrupt_count_q <= 32'd0;
      clean_req_count_q <= 32'd0;
      write_req_count_q <= 32'd0;
    end else begin
      global_cycle_q <= global_cycle_q + 32'd1;
      rand_state_q <= prng_next(rand_state_q);
      if (!rst_ni) begin
        traffic_cycle_q <= 32'd0;
        drain_cycle_q <= 32'd0;
      end else begin
        if (phase_w == TrafficPhase) begin
          traffic_cycle_q <= traffic_cycle_q + 32'd1;
          if (!first_handshake_seen_q) begin
            oracle_pre_handshake_traffic_cycles_o <=
              oracle_pre_handshake_traffic_cycles_o + 32'd1;
          end
        end
        if (phase_w == DrainPhase) begin
          drain_cycle_q <= drain_cycle_q + 32'd1;
        end
        if (!req_fire_w && phase_w == TrafficPhase) begin
          rsp_queue_overflow_o <= rsp_queue_overflow_o + 32'd1;
          oracle_stalled_req_signature_o <= oracle_stalled_req_signature_o ^ rand_state_q;
        end
        if (req_fire_w) begin
          first_handshake_seen_q <= 1'b1;
          host_req_accepted_o <= host_req_accepted_o + 32'd1;
          device_req_accepted_o <= device_req_accepted_o + 32'd1;
          device_rsp_accepted_o <= device_rsp_accepted_o + 32'd1;
          host_rsp_accepted_o <= host_rsp_accepted_o + 32'd1;
          oracle_req_signature_o <= oracle_req_signature_o ^ req_digest_w;
          last_req_digest_q <= req_digest_w;
          last_rsp_digest_q <= rsp_digest_w;
          if (expected_err_w) begin
            oracle_expected_err_count_o <= oracle_expected_err_count_o + 32'd1;
          end else begin
            oracle_expected_ok_count_o <= oracle_expected_ok_count_o + 32'd1;
          end
          if (err_w) begin
            oracle_observed_err_count_o <= oracle_observed_err_count_o + 32'd1;
          end else begin
            oracle_observed_ok_count_o <= oracle_observed_ok_count_o + 32'd1;
          end
          if (cmd_corrupt_w) begin
            cmd_corrupt_count_q <= cmd_corrupt_count_q + 32'd1;
          end
          if (data_corrupt_w) begin
            data_corrupt_count_q <= data_corrupt_count_q + 32'd1;
          end
          if (both_corrupt_w) begin
            both_corrupt_count_q <= both_corrupt_count_q + 32'd1;
          end
          if (!expected_err_w) begin
            clean_req_count_q <= clean_req_count_q + 32'd1;
          end
          if (op_write_w) begin
            write_req_count_q <= write_req_count_q + 32'd1;
          end
          oracle_semantic_family_seen_o[0] <= 1'b1;
          oracle_semantic_family_seen_o[1] <= oracle_semantic_family_seen_o[1] | op_get_w;
          oracle_semantic_family_seen_o[2] <= oracle_semantic_family_seen_o[2] | op_write_w;
          oracle_semantic_family_seen_o[3] <= oracle_semantic_family_seen_o[3] | cmd_corrupt_w;
          oracle_semantic_family_seen_o[4] <= oracle_semantic_family_seen_o[4] | data_corrupt_w;
          oracle_semantic_family_seen_o[5] <= oracle_semantic_family_seen_o[5] | both_corrupt_w;
          oracle_semantic_family_seen_o[6] <= oracle_semantic_family_seen_o[6] | err_w;
          oracle_semantic_family_acked_o <= oracle_semantic_family_seen_o |
                                            {25'd0, err_w, both_corrupt_w,
                                             data_corrupt_w, cmd_corrupt_w,
                                             op_write_w, op_get_w, req_fire_w};
          oracle_semantic_case_seen_o <= oracle_semantic_case_seen_o |
              {25'd0, err_w, both_corrupt_w, data_corrupt_w, cmd_corrupt_w,
               op_write_w, op_get_w, req_fire_w};
          oracle_semantic_case_acked_o <= oracle_semantic_case_acked_o |
              {25'd0, chk_tl.a_user.cmd_intg[0], chk_tl.a_user.data_intg[0],
               err_w, both_corrupt_w, data_corrupt_w, cmd_corrupt_w, req_fire_w};
        end
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_batch_length_i ^ cfg_req_valid_pct_i ^ cfg_seed_i ^
                           cfg_put_full_pct_i ^ cfg_put_partial_pct_i ^ cfg_req_family_i;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q + host_req_accepted_o;
  assign progress_signature_o = oracle_req_signature_o ^ last_rsp_digest_q ^
                                {28'd0, err_w, phase_w};
  assign oracle_req_signature_delta_o = oracle_req_signature_o ^ oracle_stalled_req_signature_o;
  assign oracle_req_stable_violation_o = {31'd0, err_w ^ expected_err_w};

  assign toggle_bitmap_word0_o = {
    done_o,
    chk_tl.a_valid,
    1'b1,
    err_w,
    expected_err_w,
    req_fire_w,
    op_get_w,
    op_write_w,
    oracle_semantic_family_seen_o[7:0],
    oracle_semantic_family_acked_o[7:0],
    host_req_accepted_o[7:0]
  };
  assign toggle_bitmap_word1_o = host_req_accepted_o ^ oracle_expected_err_count_o ^
                                 oracle_observed_err_count_o ^ cmd_corrupt_count_q;
  assign toggle_bitmap_word2_o = oracle_req_signature_o ^ oracle_stalled_req_signature_o ^
                                 progress_signature_o ^ data_corrupt_count_q;

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
  assign real_toggle_subset_word16_o = last_req_digest_q ^ cmd_corrupt_count_q ^
                                       data_corrupt_count_q;
  assign real_toggle_subset_word17_o = last_rsp_digest_q ^ both_corrupt_count_q ^
                                       clean_req_count_q ^ write_req_count_q;

  assign focused_wave_word0_o = global_cycle_q;
  assign focused_wave_word1_o = progress_cycle_count_o;
  assign focused_wave_word2_o = last_req_digest_q;
  assign focused_wave_word3_o = last_rsp_digest_q;
  assign focused_wave_word4_o = {19'd0, phase_w, chk_tl.a_opcode, chk_tl.a_size,
                                 cmd_corrupt_w, data_corrupt_w, both_corrupt_w,
                                 err_w, rst_ni};
  assign focused_wave_word5_o = cfg_signature_o;
  assign focused_wave_word6_o = progress_signature_o;
  assign focused_wave_word7_o = {24'd0, err_w, both_corrupt_w, data_corrupt_w,
                                 cmd_corrupt_w, op_write_w, op_get_w, req_fire_w, rst_ni};

  logic unused_cfg;
  assign unused_cfg = ^{cfg_rsp_valid_pct_i, cfg_host_d_ready_pct_i,
                        cfg_device_a_ready_pct_i, cfg_req_fill_target_i,
                        cfg_req_burst_len_max_i, cfg_rsp_delay_max_i,
                        cfg_rsp_family_i, cfg_rsp_delay_mode_i,
                        cfg_rsp_data_mode_i, cfg_rsp_data_hi_xor_i};

endmodule
