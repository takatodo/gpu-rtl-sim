// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Minimal deterministic coverage harness for tlul_adapter_reg_racl.

module tlul_adapter_reg_racl_gpu_cov_tb (
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

  prim_mubi_pkg::mubi4_t en_ifetch_w;
  top_racl_pkg::racl_policy_vec_t racl_policies_w;
  logic racl_error_w;
  top_racl_pkg::racl_error_log_t racl_error_log_w;
  logic intg_error_w;
  logic re_w;
  logic we_w;
  logic [7:0] addr_w;
  logic [TL_DW-1:0] wdata_w;
  logic [TL_DBW-1:0] be_w;
  logic busy_w;
  logic [TL_DW-1:0] rdata_w;
  logic error_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_state_q;
  logic first_handshake_seen_q;
  logic [31:0] read_req_count_q;
  logic [31:0] write_req_count_q;
  logic [31:0] full_write_count_q;
  logic [31:0] partial_write_count_q;
  logic [31:0] busy_cycle_count_q;
  logic [31:0] error_rsp_count_q;
  logic [31:0] intg_error_count_q;
  logic [31:0] register_read_count_q;
  logic [31:0] register_write_count_q;
  logic [31:0] racl_error_count_q;
  logic [31:0] racl_allowed_count_q;
  logic [31:0] racl_denied_count_q;
  logic [31:0] racl_role_signature_q;
  logic [31:0] racl_policy_signature_q;
  logic [31:0] last_req_digest_q;
  logic [31:0] last_rsp_digest_q;
  logic [31:0] addr_signature_q;
  logic [31:0] data_signature_q;
  logic [31:0] reg_signature_q;
  logic [31:0] mask_signature_q;

  logic req_fire_w;
  logic rsp_fire_w;
  logic host_stall_w;
  logic is_read_w;
  logic is_full_write_w;
  logic is_partial_write_w;
  logic [31:0] req_digest_w;
  logic [31:0] rsp_digest_w;

  initial clk_i = 1'b0;
  always #5 clk_i = ~clk_i;

  tlul_adapter_reg_racl #(
    .CmdIntgCheck(0),
    .EnableRspIntgGen(1),
    .EnableDataIntgGen(1),
    .RegAw(8),
    .RegDw(32),
    .AccessLatency(1),
    .EnableRacl(1),
    .RaclErrorRsp(1),
    .RaclPolicySelVec(0)
  ) dut (
    .clk_i,
    .rst_ni,
    .tl_i,
    .tl_o,
    .en_ifetch_i (en_ifetch_w),
    .intg_error_o(intg_error_w),
    .racl_policies_i(racl_policies_w),
    .racl_error_o(racl_error_w),
    .racl_error_log_o(racl_error_log_w),
    .re_o        (re_w),
    .we_o        (we_w),
    .addr_o      (addr_w),
    .wdata_o     (wdata_w),
    .be_o        (be_w),
    .busy_i      (busy_w),
    .rdata_i     (rdata_w),
    .error_i     (error_w)
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
    addr[7:0] = addr[7:0] ^ 8'(cfg_req_family_i);
    if ((cfg_req_address_mode_i[0]) && pct_hit(state ^ 32'h3b4d_1171, 32'd15)) begin
      return addr;
    end
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
      return TL_DBW'(4'b0011);
    end
    if (&mask) begin
      return TL_DBW'(4'b0111);
    end
    return mask;
  endfunction

  function automatic prim_mubi_pkg::mubi4_t choose_mubi(input logic [31:0] state,
                                                        input logic [31:0] pct_raw);
    if (pct_hit(state, pct_raw)) begin
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
    digest ^= 32'(tl.a_user.instr_type);
    digest ^= 32'(tl.a_user.rsvd);
    return digest;
  endfunction

  function automatic logic [31:0] response_digest(input tl_d2h_t tl);
    logic [31:0] digest;
    digest = 32'(tl.d_opcode) ^ 32'(tl.d_size) ^
             {29'd0, tl.d_error, tl.d_valid, tl.a_ready};
    digest ^= tl.d_data;
    digest ^= 32'(tl.d_source) ^ 32'(tl.d_sink) ^ 32'(tl.d_param);
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
    tl_i.d_ready = pct_hit(rand_state_q ^ 32'h7d66_19b3, cfg_host_d_ready_pct_i) ||
                   (phase_w == DrainPhase);
    if (phase_w == TrafficPhase) begin
      tl_i.a_valid = pct_hit(rand_state_q ^ 32'h2152_8f47, cfg_req_valid_pct_i);
      tl_i.a_opcode = choose_opcode(rand_state_q ^ 32'h4f1b_9a5d);
      tl_i.a_param = '0;
      tl_i.a_size = TL_SZW'(2);
      tl_i.a_source = TL_AIW'((rand_state_q ^ cfg_req_family_i) & cfg_source_mask_i);
      tl_i.a_address = choose_address(rand_state_q ^ cfg_address_base_i);
      tl_i.a_mask = choose_mask(rand_state_q ^ cfg_req_fill_target_i, tl_i.a_opcode);
      tl_i.a_data = (rand_state_q ^ {cfg_req_data_hi_xor_i[15:0], cfg_req_data_mode_i[15:0]}) +
                    cfg_seed_i;
      tl_i.a_user = TL_A_USER_DEFAULT;
      tl_i.a_user.instr_type = choose_mubi(rand_state_q ^ 32'h1159_f00d, 32'd8);
      tl_i.a_user.rsvd = '0;
      tl_i.a_user.rsvd[0] = rand_state_q[4] ^ cfg_req_family_i[0];
      tl_i.a_user.data_intg = get_data_intg(tl_i.a_data);
    end

    racl_policies_w = top_racl_pkg::RACL_POLICY_VEC_DEFAULT;
    racl_policies_w[0].read_perm = pct_hit(rand_state_q ^ 32'h41ac_0711, 32'd55) ? 2'b01 : 2'b10;
    racl_policies_w[0].write_perm = pct_hit(rand_state_q ^ 32'h7e3d_9205, 32'd50) ? 2'b10 : 2'b01;

    busy_w = (phase_w == TrafficPhase) &&
             !pct_hit(rand_state_q ^ 32'h0b47_cafe, cfg_device_a_ready_pct_i);
    rdata_w = prng_next(rand_state_q ^ cfg_rsp_data_mode_i) ^ cfg_rsp_data_hi_xor_i;
    error_w = pct_hit(rand_state_q ^ 32'h6a41_2f09, cfg_rsp_error_pct_i);
    en_ifetch_w = choose_mubi(rand_state_q ^ 32'h55aa_7301, cfg_access_ack_data_pct_i);
  end

  assign req_fire_w = tl_i.a_valid && tl_o.a_ready;
  assign rsp_fire_w = tl_o.d_valid && tl_i.d_ready;
  assign host_stall_w = tl_i.a_valid && !tl_o.a_ready;
  assign is_read_w = tl_i.a_opcode == Get;
  assign is_full_write_w = tl_i.a_opcode == PutFullData;
  assign is_partial_write_w = tl_i.a_opcode == PutPartialData;
  assign req_digest_w = request_digest(tl_i);
  assign rsp_digest_w = response_digest(tl_o);

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= '0;
      traffic_cycle_q <= '0;
      drain_cycle_q <= '0;
      rand_state_q <= cfg_seed_i ^ 32'h2476_b8d1;
      first_handshake_seen_q <= 1'b0;
      read_req_count_q <= '0;
      write_req_count_q <= '0;
      full_write_count_q <= '0;
      partial_write_count_q <= '0;
      busy_cycle_count_q <= '0;
      error_rsp_count_q <= '0;
      intg_error_count_q <= '0;
      register_read_count_q <= '0;
      register_write_count_q <= '0;
      racl_error_count_q <= '0;
      racl_allowed_count_q <= '0;
      racl_denied_count_q <= '0;
      racl_role_signature_q <= '0;
      racl_policy_signature_q <= '0;
      last_req_digest_q <= '0;
      last_rsp_digest_q <= '0;
      addr_signature_q <= '0;
      data_signature_q <= '0;
      reg_signature_q <= '0;
      mask_signature_q <= '0;
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
      oracle_req_signature_delta_o <= '0;
      oracle_req_stable_violation_o <= '0;
      oracle_pre_handshake_traffic_cycles_o <= '0;
    end else begin
      global_cycle_q <= global_cycle_q + 32'd1;
      rand_state_q <= prng_next(rand_state_q ^ cfg_seed_i);
      if (!rst_ni) begin
        traffic_cycle_q <= '0;
        drain_cycle_q <= '0;
      end else begin
        if (phase_w == TrafficPhase) begin
          traffic_cycle_q <= traffic_cycle_q + 32'd1;
          if (!first_handshake_seen_q) begin
            oracle_pre_handshake_traffic_cycles_o <= oracle_pre_handshake_traffic_cycles_o + 32'd1;
          end
          if (busy_w) begin
            busy_cycle_count_q <= busy_cycle_count_q + 32'd1;
          end
        end
        if (phase_w == DrainPhase) begin
          drain_cycle_q <= drain_cycle_q + 32'd1;
        end
        if (host_stall_w) begin
          rsp_queue_overflow_o <= rsp_queue_overflow_o + 32'd1;
          oracle_stalled_req_signature_o <= oracle_stalled_req_signature_o ^ req_digest_w;
        end
        if (req_fire_w) begin
          first_handshake_seen_q <= 1'b1;
          host_req_accepted_o <= host_req_accepted_o + 32'd1;
          device_req_accepted_o <= device_req_accepted_o + 32'd1;
          oracle_req_signature_o <= oracle_req_signature_o ^ req_digest_w;
          oracle_req_signature_delta_o <= oracle_req_signature_delta_o ^ (req_digest_w ^ last_req_digest_q);
          last_req_digest_q <= req_digest_w;
          addr_signature_q <= addr_signature_q ^ tl_i.a_address;
          data_signature_q <= data_signature_q ^ tl_i.a_data;
          mask_signature_q <= mask_signature_q ^ {28'd0, tl_i.a_mask};
          oracle_semantic_family_seen_o <= oracle_semantic_family_seen_o |
                                           {21'd0, racl_policies_w[0].write_perm,
                                            racl_policies_w[0].read_perm,
                                            tl_i.a_user.rsvd[0],
                                            tl_i.a_user.instr_type == prim_mubi_pkg::MuBi4True,
                                            error_w, is_partial_write_w, is_full_write_w,
                                            is_read_w, req_fire_w};
          oracle_semantic_case_seen_o <= oracle_semantic_case_seen_o |
                                         {23'd0, busy_w, tl_i.d_ready, tl_i.a_address[1:0],
                                          tl_i.a_mask, 1'b1};
          if (is_read_w) begin
            read_req_count_q <= read_req_count_q + 32'd1;
          end else begin
            write_req_count_q <= write_req_count_q + 32'd1;
          end
          if (is_full_write_w) begin
            full_write_count_q <= full_write_count_q + 32'd1;
          end
          if (is_partial_write_w) begin
            partial_write_count_q <= partial_write_count_q + 32'd1;
          end
          if (racl_error_w) begin
            racl_error_count_q <= racl_error_count_q + 32'd1;
            racl_denied_count_q <= racl_denied_count_q + 32'd1;
          end else begin
            racl_allowed_count_q <= racl_allowed_count_q + 32'd1;
          end
          racl_role_signature_q <= racl_role_signature_q ^
                                   {30'd0, racl_error_log_w.racl_role, tl_i.a_user.rsvd[0]};
          racl_policy_signature_q <= racl_policy_signature_q ^
                                     {28'd0, racl_policies_w[0].write_perm,
                                      racl_policies_w[0].read_perm};
        end
        if (re_w) begin
          register_read_count_q <= register_read_count_q + 32'd1;
          reg_signature_q <= reg_signature_q ^ {24'd0, addr_w};
        end
        if (we_w) begin
          register_write_count_q <= register_write_count_q + 32'd1;
          reg_signature_q <= reg_signature_q ^ wdata_w ^ {28'd0, be_w};
        end
        if (intg_error_w) begin
          intg_error_count_q <= intg_error_count_q + 32'd1;
        end
        if (rsp_fire_w) begin
          device_rsp_accepted_o <= device_rsp_accepted_o + 32'd1;
          host_rsp_accepted_o <= host_rsp_accepted_o + 32'd1;
          last_rsp_digest_q <= rsp_digest_w;
          oracle_semantic_family_acked_o <= oracle_semantic_family_acked_o |
                                            {28'd0, tl_o.d_error, tl_o.d_opcode == AccessAckData,
                                             tl_o.d_valid, rsp_fire_w};
          oracle_semantic_case_acked_o <= oracle_semantic_case_acked_o |
                                          {23'd0, tl_o.d_size, tl_o.d_source[3:0], tl_o.d_error,
                                           tl_o.d_opcode == AccessAckData, rsp_fire_w};
          if (tl_o.d_error) begin
            error_rsp_count_q <= error_rsp_count_q + 32'd1;
            oracle_expected_err_count_o <= oracle_expected_err_count_o + 32'd1;
            oracle_observed_err_count_o <= oracle_observed_err_count_o + 32'd1;
          end else begin
            oracle_expected_ok_count_o <= oracle_expected_ok_count_o + 32'd1;
            oracle_observed_ok_count_o <= oracle_observed_ok_count_o + 32'd1;
          end
        end
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_req_family_i ^ cfg_rsp_family_i ^
                           cfg_req_address_mode_i ^ cfg_req_data_mode_i;
  assign progress_cycle_count_o = traffic_cycle_q + host_rsp_accepted_o + device_req_accepted_o;
  assign progress_signature_o = oracle_req_signature_o ^ last_rsp_digest_q ^ reg_signature_q ^
                                racl_role_signature_q ^ racl_policy_signature_q ^
                                {31'd0, done_o};

  assign toggle_bitmap_word0_o = {
    14'd0,
    racl_error_w,
    racl_error_log_w.read_access,
    racl_error_log_w.racl_role,
    intg_error_w,
    error_w,
    busy_w,
    we_w,
    re_w,
    rsp_fire_w,
    req_fire_w,
    tl_i.a_valid,
    tl_o.a_ready,
    tl_o.d_valid,
    tl_i.d_ready,
    is_partial_write_w,
    is_full_write_w,
    is_read_w,
    done_o
  };
  assign toggle_bitmap_word1_o = oracle_semantic_family_seen_o ^ oracle_semantic_family_acked_o;
  assign toggle_bitmap_word2_o = addr_signature_q ^ data_signature_q ^ mask_signature_q;

  assign real_toggle_subset_word0_o = host_req_accepted_o;
  assign real_toggle_subset_word1_o = host_rsp_accepted_o;
  assign real_toggle_subset_word2_o = read_req_count_q;
  assign real_toggle_subset_word3_o = write_req_count_q;
  assign real_toggle_subset_word4_o = full_write_count_q;
  assign real_toggle_subset_word5_o = partial_write_count_q;
  assign real_toggle_subset_word6_o = busy_cycle_count_q;
  assign real_toggle_subset_word7_o = error_rsp_count_q;
  assign real_toggle_subset_word8_o = register_read_count_q;
  assign real_toggle_subset_word9_o = register_write_count_q;
  assign real_toggle_subset_word10_o = racl_error_count_q;
  assign real_toggle_subset_word11_o = racl_allowed_count_q;
  assign real_toggle_subset_word12_o = racl_denied_count_q;
  assign real_toggle_subset_word13_o = racl_role_signature_q;
  assign real_toggle_subset_word14_o = racl_policy_signature_q;
  assign real_toggle_subset_word15_o = reg_signature_q;
  assign real_toggle_subset_word16_o = mask_signature_q;
  assign real_toggle_subset_word17_o = intg_error_count_q ^ oracle_req_signature_delta_o;

  assign focused_wave_word0_o = global_cycle_q;
  assign focused_wave_word1_o = traffic_cycle_q;
  assign focused_wave_word2_o = {16'd0, tl_i.a_valid, tl_o.a_ready, tl_o.d_valid, tl_i.d_ready,
                                 racl_error_w, we_w, re_w, busy_w, error_w, addr_w[6:0]};
  assign focused_wave_word3_o = tl_i.a_address;
  assign focused_wave_word4_o = tl_i.a_data;
  assign focused_wave_word5_o = tl_o.d_data;
  assign focused_wave_word6_o = last_req_digest_q;
  assign focused_wave_word7_o = last_rsp_digest_q;

endmodule
