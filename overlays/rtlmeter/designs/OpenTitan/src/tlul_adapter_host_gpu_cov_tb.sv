// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Minimal deterministic coverage harness for tlul_adapter_host.

module tlul_adapter_host_gpu_cov_tb #(
  parameter int unsigned CoverageWords = 32
) (
  input  logic        clk_i,
  input  logic        rst_ni,
  input  logic        cfg_valid_i,
  input  logic [31:0] cfg_seed_i,
  input  logic [31:0] cfg_cycles_i,
  input  logic [31:0] cfg_batch_length_i,
  input  logic [31:0] cfg_req_family_i,
  input  logic [31:0] cfg_req_valid_pct_i,
  input  logic [31:0] cfg_device_a_ready_pct_i,
  input  logic [31:0] cfg_host_d_ready_pct_i,
  input  logic [31:0] cfg_rsp_valid_pct_i,
  input  logic [31:0] cfg_put_full_pct_i,
  input  logic [31:0] cfg_put_partial_pct_i,
  input  logic [31:0] cfg_req_fill_target_i,
  input  logic [31:0] cfg_req_burst_len_max_i,
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
  input  logic [31:0] cfg_address_base_i,
  input  logic [31:0] cfg_address_mask_i,
  input  logic [31:0] cfg_source_mask_i,
  output logic        done_o,
  output logic [31:0] cfg_signature_o,
  output logic [31:0] cycle_count_o,
  output logic [31:0] host_req_accepted_o,
  output logic [31:0] device_req_accepted_o,
  output logic [31:0] device_rsp_accepted_o,
  output logic [31:0] host_rsp_accepted_o,
  output logic [31:0] rsp_queue_overflow_o,
  output logic [31:0] progress_cycle_count_o,
  output logic [31:0] progress_signature_o,
  output logic [31:0] oracle_expected_ok_o,
  output logic [31:0] oracle_observed_ok_o,
  output logic [31:0] oracle_mismatch_count_o,
  output logic [31:0] oracle_semantic_family_seen_o,
  output logic [31:0] oracle_semantic_family_acked_o,
  output logic [31:0] oracle_semantic_case_seen_o,
  output logic [31:0] oracle_semantic_case_acked_o,
  output logic [31:0] oracle_req_signature_o,
  output logic [31:0] oracle_stalled_req_signature_o,
  output logic [31:0] oracle_req_signature_delta_o,
  output logic [31:0] oracle_pre_handshake_traffic_cycles_o,
  output logic [31:0] toggle_bitmap_word0_o,
  output logic [31:0] toggle_bitmap_word1_o,
  output logic [31:0] toggle_bitmap_word2_o,
  output logic [31:0] toggle_bitmap_word3_o,
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
  output logic [31:0] focused_wave_word7_o
);

  import top_pkg::*;
  import tlul_pkg::*;

  localparam int unsigned MaxReqs = 4;

  tl_h2d_t tl_o;
  tl_d2h_t tl_i_pre_intg;
  tl_d2h_t tl_i;

  logic req_w;
  logic gnt_w;
  logic we_w;
  logic valid_w;
  logic err_w;
  logic intg_err_w;
  logic [TL_AW-1:0] addr_w;
  logic [TL_DW-1:0] wdata_w;
  logic [DataIntgWidth-1:0] wdata_intg_w;
  logic [TL_DBW-1:0] be_w;
  prim_mubi_pkg::mubi4_t instr_type_w;
  logic [RsvdWidth-1:0] user_rsvd_w;
  logic [TL_DW-1:0] rdata_w;
  logic [DataIntgWidth-1:0] rdata_intg_w;

  logic [31:0] rand_state_q;
  logic [31:0] next_rand_state_w;
  logic [31:0] cycle_count_q;
  logic [31:0] host_req_count_q;
  logic [31:0] device_req_count_q;
  logic [31:0] req_stall_count_q;
  logic [31:0] pending_block_count_q;
  logic [31:0] device_rsp_count_q;
  logic [31:0] host_rsp_count_q;
  logic [31:0] error_rsp_count_q;
  logic [31:0] intg_error_count_q;
  logic [31:0] read_req_count_q;
  logic [31:0] full_write_req_count_q;
  logic [31:0] partial_write_req_count_q;
  logic [31:0] source_switch_count_q;
  logic [31:0] expected_ok_q;
  logic [31:0] observed_ok_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] semantic_family_seen_q;
  logic [31:0] semantic_family_acked_q;
  logic [31:0] semantic_case_seen_q;
  logic [31:0] semantic_case_acked_q;
  logic [31:0] req_signature_q;
  logic [31:0] rsp_signature_q;
  logic [31:0] req_signature_delta_q;
  logic [31:0] pre_handshake_traffic_cycles_q;
  logic [31:0] last_req_digest_q;
  logic [31:0] last_rsp_digest_q;
  logic        first_handshake_seen_q;
  logic        source_seen_q;
  logic [TL_AIW-1:0] last_source_q;

  logic rsp_pending_q;
  logic rsp_is_read_q;
  logic rsp_error_q;
  logic [1:0] rsp_delay_q;
  logic [TL_SZW-1:0] rsp_size_q;
  logic [TL_AIW-1:0] rsp_source_q;
  logic [TL_DW-1:0] rsp_data_q;

  logic traffic_en_w;
  logic drain_en_w;
  logic [31:0] cfg_effective_cycles_w;
  logic host_req_fire_w;
  logic device_req_fire_w;
  logic device_rsp_fire_w;
  logic host_rsp_fire_w;
  logic req_stalled_w;
  logic pending_blocks_req_w;
  logic rsp_ready_w;
  logic write_full_w;
  logic write_partial_w;
  logic [2:0] phase_w;

  assign traffic_en_w = cfg_valid_i && !done_o;
  assign drain_en_w = cfg_valid_i && done_o;
  assign cfg_effective_cycles_w = (cfg_cycles_i != 32'd0) ? cfg_cycles_i : cfg_batch_length_i;
  assign host_req_fire_w = req_w && gnt_w;
  assign device_req_fire_w = tl_o.a_valid && tl_i.a_ready;
  assign device_rsp_fire_w = tl_i.d_valid && tl_o.d_ready;
  assign host_rsp_fire_w = valid_w;
  assign req_stalled_w = req_w && !gnt_w;
  assign pending_blocks_req_w = traffic_en_w && rsp_pending_q;
  assign write_full_w = we_w && (&be_w);
  assign write_partial_w = we_w && !(&be_w);
  assign phase_w = {done_o, rsp_pending_q, cycle_count_q[0]};

  function automatic logic [31:0] clamp_pct(input logic [31:0] pct_raw);
    begin
      clamp_pct = (pct_raw > 32'd100) ? 32'd100 : pct_raw;
    end
  endfunction

  function automatic logic pct_hit(input logic [31:0] value, input logic [31:0] pct_raw);
    begin
      pct_hit = ((value % 32'd100) < clamp_pct(pct_raw));
    end
  endfunction

  function automatic logic [31:0] lfsr_next(input logic [31:0] state);
    begin
      lfsr_next = {state[30:0], state[31] ^ state[21] ^ state[1] ^ state[0]} ^ 32'h9e37_79b9;
    end
  endfunction

  function automatic logic [31:0] lfsr_mix(input logic [31:0] state, input logic [31:0] salt);
    begin
      lfsr_mix = lfsr_next(state ^ salt) ^ {salt[15:0], salt[31:16]};
    end
  endfunction

  function automatic logic [TL_DBW-1:0] choose_be(input logic [31:0] state,
                                                  input logic full_write);
    logic [TL_DBW-1:0] mask;
    begin
      if (full_write) begin
        choose_be = {TL_DBW{1'b1}};
      end else begin
        mask = TL_DBW'(state[TL_DBW-1:0]);
        if (mask == '0) begin
          mask = TL_DBW'(4'b0011);
        end
        if (&mask) begin
          mask = TL_DBW'(4'b0111);
        end
        choose_be = mask;
      end
    end
  endfunction

  function automatic logic [31:0] request_digest(input tl_h2d_t tl,
                                                 input logic req_accepted,
                                                 input logic host_write,
                                                 input logic [TL_DBW-1:0] host_be);
    logic [31:0] digest;
    begin
      digest = tl.a_address ^ tl.a_data ^ {24'd0, tl.a_source};
      digest ^= {21'd0, tl.a_user.cmd_intg, tl.a_mask};
      digest ^= {24'd0, req_accepted, host_write, host_be, 2'(tl.a_opcode)};
      request_digest = digest;
    end
  endfunction

  function automatic logic [31:0] response_digest(input tl_d2h_t tl,
                                                  input logic host_valid,
                                                  input logic host_err,
                                                  input logic host_intg_err);
    logic [31:0] digest;
    begin
      digest = tl.d_data ^ {24'd0, tl.d_source};
      digest ^= {21'd0, tl.d_user.rsp_intg, tl.d_error, host_valid, host_err, host_intg_err};
      digest ^= {26'd0, 3'(tl.d_opcode), tl.d_size, tl.d_sink};
      response_digest = digest;
    end
  endfunction

  function automatic logic [31:0] semantic_family_for_req(input logic host_write,
                                                          input logic full_write,
                                                          input logic partial_write,
                                                          input logic instr_true);
    begin
      semantic_family_for_req = 32'd0;
      semantic_family_for_req[0] = !host_write;
      semantic_family_for_req[1] = full_write;
      semantic_family_for_req[2] = partial_write;
      semantic_family_for_req[3] = instr_true;
      semantic_family_for_req[4] = rsp_pending_q;
      semantic_family_for_req[5] = req_stalled_w;
    end
  endfunction

  function automatic logic [31:0] semantic_case_for_req(input tl_h2d_t tl,
                                                        input logic full_write,
                                                        input logic partial_write);
    logic [31:0] opcode_bit;
    logic [31:0] source_bit;
    logic [31:0] mask_bit;
    begin
      opcode_bit = 32'h1 << 32'(tl.a_opcode);
      source_bit = 32'h1 << (8 + 32'(tl.a_source[1:0]));
      mask_bit = 32'h1 << (16 + 32'(tl.a_mask[1:0]));
      semantic_case_for_req = opcode_bit | source_bit | mask_bit |
                              {28'd0, partial_write, full_write, tl.a_valid, tl.d_ready};
    end
  endfunction

  always_comb begin
    logic [31:0] host_state;
    logic [31:0] ready_state;
    logic [31:0] opcode_pick;
    logic [31:0] put_full_limit;
    logic [31:0] put_any_limit;

    next_rand_state_w = lfsr_next(rand_state_q ^ cycle_count_q ^ cfg_seed_i);
    host_state = lfsr_mix(rand_state_q, 32'h5a00_0000 ^ cycle_count_q ^ cfg_req_family_i);
    ready_state = lfsr_mix(rand_state_q, 32'h6b00_0000 ^ cycle_count_q ^ cfg_rsp_family_i);
    opcode_pick = (host_state ^ cfg_req_family_i) % 32'd100;
    put_full_limit = clamp_pct(cfg_put_full_pct_i);
    put_any_limit = put_full_limit + clamp_pct(cfg_put_partial_pct_i);
    if (put_any_limit > 32'd100) begin
      put_any_limit = 32'd100;
    end

    we_w = opcode_pick < put_any_limit;
    be_w = choose_be(host_state ^ cfg_req_fill_target_i, opcode_pick < put_full_limit);
    addr_w = TL_AW'(cfg_address_base_i ^
                    (({host_state[29:0], 2'b00} ^ cfg_req_address_mode_i) &
                     cfg_address_mask_i));
    wdata_w = TL_DW'((host_state ^ cfg_req_data_hi_xor_i) +
                     (cfg_req_data_mode_i ^ 32'h3141_5926));
    wdata_intg_w = get_data_intg(wdata_w);
    instr_type_w = prim_mubi_pkg::mubi4_bool_to_mubi(pct_hit(host_state ^ 32'h71c7_0001,
                                                             cfg_access_ack_data_pct_i));
    user_rsvd_w = RsvdWidth'(host_state ^ cfg_req_burst_len_max_i);

    req_w = traffic_en_w && !rsp_pending_q &&
            (cycle_count_q[0] || pct_hit(host_state, cfg_req_valid_pct_i));
    tl_i_pre_intg = TL_D2H_DEFAULT;
    tl_i_pre_intg.a_ready = (traffic_en_w || drain_en_w) &&
                            (cycle_count_q[0] ||
                             pct_hit(ready_state, cfg_device_a_ready_pct_i));
    tl_i_pre_intg.d_valid = (traffic_en_w || drain_en_w) && rsp_pending_q && rsp_ready_w;
    tl_i_pre_intg.d_opcode = rsp_is_read_q ? AccessAckData : AccessAck;
    tl_i_pre_intg.d_param = 3'b000;
    tl_i_pre_intg.d_size = rsp_size_q;
    tl_i_pre_intg.d_source = rsp_source_q;
    tl_i_pre_intg.d_sink = TL_DIW'(ready_state[8:0]);
    tl_i_pre_intg.d_data = rsp_data_q ^ TL_DW'(cfg_rsp_data_hi_xor_i ^ cfg_rsp_data_mode_i);
    tl_i_pre_intg.d_user = TL_D_USER_DEFAULT;
    tl_i_pre_intg.d_error = rsp_error_q;
  end

  assign rsp_ready_w = (rsp_delay_q == 2'd0) &&
                       (cycle_count_q[0] ||
                        pct_hit(rand_state_q ^ 32'hc0de_0101, cfg_rsp_valid_pct_i));

  tlul_rsp_intg_gen #(
    .EnableRspIntgGen  (1'b1),
    .EnableDataIntgGen (1'b0)
  ) u_rsp_intg_gen (
    .tl_i (tl_i_pre_intg),
    .tl_o (tl_i)
  );

  tlul_adapter_host #(
    .MAX_REQS               (MaxReqs),
    .EnableDataIntgGen      (1'b0),
    .EnableRspDataIntgCheck (1'b0)
  ) dut (
    .clk_i,
    .rst_ni,
    .req_i        (req_w),
    .gnt_o        (gnt_w),
    .addr_i       (addr_w),
    .we_i         (we_w),
    .wdata_i      (wdata_w),
    .wdata_intg_i (wdata_intg_w),
    .be_i         (be_w),
    .instr_type_i (instr_type_w),
    .user_rsvd_i  (user_rsvd_w),
    .valid_o      (valid_w),
    .rdata_o      (rdata_w),
    .rdata_intg_o (rdata_intg_w),
    .err_o        (err_w),
    .intg_err_o   (intg_err_w),
    .tl_o         (tl_o),
    .tl_i         (tl_i)
  );

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      rand_state_q <= 32'h1;
      cycle_count_q <= 32'd0;
      host_req_count_q <= 32'd0;
      device_req_count_q <= 32'd0;
      req_stall_count_q <= 32'd0;
      pending_block_count_q <= 32'd0;
      device_rsp_count_q <= 32'd0;
      host_rsp_count_q <= 32'd0;
      error_rsp_count_q <= 32'd0;
      intg_error_count_q <= 32'd0;
      read_req_count_q <= 32'd0;
      full_write_req_count_q <= 32'd0;
      partial_write_req_count_q <= 32'd0;
      source_switch_count_q <= 32'd0;
      expected_ok_q <= 32'd0;
      observed_ok_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      semantic_family_seen_q <= 32'd0;
      semantic_family_acked_q <= 32'd0;
      semantic_case_seen_q <= 32'd0;
      semantic_case_acked_q <= 32'd0;
      req_signature_q <= 32'd0;
      rsp_signature_q <= 32'd0;
      req_signature_delta_q <= 32'd0;
      pre_handshake_traffic_cycles_q <= 32'd0;
      last_req_digest_q <= 32'd0;
      last_rsp_digest_q <= 32'd0;
      first_handshake_seen_q <= 1'b0;
      source_seen_q <= 1'b0;
      last_source_q <= '0;
      rsp_pending_q <= 1'b0;
      rsp_is_read_q <= 1'b0;
      rsp_error_q <= 1'b0;
      rsp_delay_q <= 2'd0;
      rsp_size_q <= '0;
      rsp_source_q <= '0;
      rsp_data_q <= '0;
      done_o <= 1'b0;
    end else if (!clk_i) begin
      // The GPU lowering may call this eval body without a real posedge; hold sequential state.
    end else if (!cfg_valid_i) begin
      rand_state_q <= cfg_seed_i ^ 32'ha501_ada7;
      cycle_count_q <= 32'd0;
      host_req_count_q <= 32'd0;
      device_req_count_q <= 32'd0;
      req_stall_count_q <= 32'd0;
      pending_block_count_q <= 32'd0;
      device_rsp_count_q <= 32'd0;
      host_rsp_count_q <= 32'd0;
      error_rsp_count_q <= 32'd0;
      intg_error_count_q <= 32'd0;
      read_req_count_q <= 32'd0;
      full_write_req_count_q <= 32'd0;
      partial_write_req_count_q <= 32'd0;
      source_switch_count_q <= 32'd0;
      expected_ok_q <= 32'd0;
      observed_ok_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      semantic_family_seen_q <= 32'd0;
      semantic_family_acked_q <= 32'd0;
      semantic_case_seen_q <= 32'd0;
      semantic_case_acked_q <= 32'd0;
      req_signature_q <= 32'd0;
      rsp_signature_q <= 32'd0;
      req_signature_delta_q <= 32'd0;
      pre_handshake_traffic_cycles_q <= 32'd0;
      last_req_digest_q <= 32'd0;
      last_rsp_digest_q <= 32'd0;
      first_handshake_seen_q <= 1'b0;
      source_seen_q <= 1'b0;
      last_source_q <= '0;
      rsp_pending_q <= 1'b0;
      rsp_is_read_q <= 1'b0;
      rsp_error_q <= 1'b0;
      rsp_delay_q <= 2'd0;
      rsp_size_q <= '0;
      rsp_source_q <= '0;
      rsp_data_q <= '0;
      done_o <= 1'b0;
    end else begin
      rand_state_q <= next_rand_state_w;

      if (!done_o) begin
        cycle_count_q <= cycle_count_q + 32'd1;
        if (cycle_count_q + 32'd1 >= cfg_effective_cycles_w) begin
          done_o <= 1'b1;
        end
      end

      if (req_w && !first_handshake_seen_q) begin
        pre_handshake_traffic_cycles_q <= pre_handshake_traffic_cycles_q + 32'd1;
      end

      if (req_stalled_w) begin
        req_stall_count_q <= req_stall_count_q + 32'd1;
      end

      if (pending_blocks_req_w) begin
        pending_block_count_q <= pending_block_count_q + 32'd1;
      end

      if (host_req_fire_w) begin
        logic [31:0] digest;
        digest = request_digest(tl_o, 1'b1, we_w, be_w);
        host_req_count_q <= host_req_count_q + 32'd1;
        device_req_count_q <= device_req_count_q + 32'd1;
        first_handshake_seen_q <= 1'b1;
        req_signature_q <= req_signature_q ^ digest;
        req_signature_delta_q <= req_signature_delta_q + (digest ^ last_req_digest_q);
        last_req_digest_q <= digest;
        semantic_family_seen_q <= semantic_family_seen_q |
                                  semantic_family_for_req(we_w,
                                                          write_full_w,
                                                          write_partial_w,
                                                          instr_type_w ==
                                                          prim_mubi_pkg::MuBi4True);
        semantic_case_seen_q <= semantic_case_seen_q |
                                semantic_case_for_req(tl_o, write_full_w, write_partial_w);
        if (!we_w) begin
          read_req_count_q <= read_req_count_q + 32'd1;
        end else if (write_full_w) begin
          full_write_req_count_q <= full_write_req_count_q + 32'd1;
        end else begin
          partial_write_req_count_q <= partial_write_req_count_q + 32'd1;
        end
        if (source_seen_q && (last_source_q != tl_o.a_source)) begin
          source_switch_count_q <= source_switch_count_q + 32'd1;
        end
        source_seen_q <= 1'b1;
        last_source_q <= tl_o.a_source;
        rsp_pending_q <= 1'b1;
        rsp_is_read_q <= !we_w;
        rsp_error_q <= pct_hit(rand_state_q ^ 32'hbad0_0bad, cfg_rsp_error_pct_i);
        rsp_delay_q <= (cfg_rsp_delay_max_i == 32'd0) ? 2'd0 : {1'b0, rand_state_q[0]};
        rsp_size_q <= tl_o.a_size;
        rsp_source_q <= tl_o.a_source;
        rsp_data_q <= TL_DW'(tl_o.a_data ^ tl_o.a_address ^ 32'h0d15_ea5e);
      end else if (rsp_pending_q && (rsp_delay_q != 2'd0)) begin
        rsp_delay_q <= rsp_delay_q - 2'd1;
      end

      if (device_rsp_fire_w) begin
        device_rsp_count_q <= device_rsp_count_q + 32'd1;
        semantic_family_acked_q <= semantic_family_acked_q |
                                   {28'd0, tl_i.d_error, rsp_is_read_q, 2'b01};
        semantic_case_acked_q <= semantic_case_acked_q |
                                 (32'h1 << (20 + 32'(tl_i.d_source[1:0])));
        rsp_signature_q <= rsp_signature_q ^
                           response_digest(tl_i, valid_w, err_w, intg_err_w);
        last_rsp_digest_q <= response_digest(tl_i, valid_w, err_w, intg_err_w);
        if (tl_i.d_error || err_w) begin
          error_rsp_count_q <= error_rsp_count_q + 32'd1;
        end else begin
          expected_ok_q <= expected_ok_q + 32'd1;
        end
        rsp_pending_q <= 1'b0;
      end

      if (host_rsp_fire_w) begin
        host_rsp_count_q <= host_rsp_count_q + 32'd1;
        if (intg_err_w) begin
          intg_error_count_q <= intg_error_count_q + 32'd1;
        end
        if (!err_w) begin
          observed_ok_q <= observed_ok_q + 32'd1;
        end
        if ((observed_ok_q > expected_ok_q) || (err_w && !tl_i.d_error)) begin
          mismatch_count_q <= mismatch_count_q + 32'd1;
        end
      end
    end
  end

  assign cycle_count_o = cycle_count_q;
  assign cfg_signature_o = cfg_seed_i ^ cfg_effective_cycles_w ^ cfg_req_family_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           cfg_device_a_ready_pct_i;
  assign host_req_accepted_o = host_req_count_q;
  assign device_req_accepted_o = device_req_count_q;
  assign device_rsp_accepted_o = device_rsp_count_q;
  assign host_rsp_accepted_o = host_rsp_count_q;
  assign rsp_queue_overflow_o = pending_block_count_q;
  assign progress_cycle_count_o = cycle_count_q;
  assign progress_signature_o = req_signature_q ^ rsp_signature_q ^ last_req_digest_q ^
                                last_rsp_digest_q ^ {24'd0, last_source_q};
  assign oracle_expected_ok_o = expected_ok_q;
  assign oracle_observed_ok_o = observed_ok_q;
  assign oracle_mismatch_count_o = mismatch_count_q;
  assign oracle_semantic_family_seen_o = semantic_family_seen_q;
  assign oracle_semantic_family_acked_o = semantic_family_acked_q;
  assign oracle_semantic_case_seen_o = semantic_case_seen_q;
  assign oracle_semantic_case_acked_o = semantic_case_acked_q;
  assign oracle_req_signature_o = req_signature_q;
  assign oracle_stalled_req_signature_o = req_stall_count_q;
  assign oracle_req_signature_delta_o = req_signature_delta_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_handshake_traffic_cycles_q;

  assign toggle_bitmap_word0_o = {done_o,
                                  rst_ni,
                                  req_w,
                                  gnt_w,
                                  valid_w,
                                  err_w,
                                  intg_err_w,
                                  rsp_pending_q,
                                  semantic_family_seen_q[7:0],
                                  host_req_count_q[7:0],
                                  host_rsp_count_q[7:0]};
  assign toggle_bitmap_word1_o = req_signature_q;
  assign toggle_bitmap_word2_o = {device_rsp_count_q[15:0], host_rsp_count_q[15:0]};
  assign toggle_bitmap_word3_o = {error_rsp_count_q[15:0], req_stall_count_q[15:0]};

  assign real_toggle_subset_word0_o = host_req_count_q;
  assign real_toggle_subset_word1_o = device_req_count_q;
  assign real_toggle_subset_word2_o = req_stall_count_q;
  assign real_toggle_subset_word3_o = pending_block_count_q;
  assign real_toggle_subset_word4_o = device_rsp_count_q;
  assign real_toggle_subset_word5_o = host_rsp_count_q;
  assign real_toggle_subset_word6_o = error_rsp_count_q;
  assign real_toggle_subset_word7_o = intg_error_count_q;
  assign real_toggle_subset_word8_o = read_req_count_q;
  assign real_toggle_subset_word9_o = full_write_req_count_q;
  assign real_toggle_subset_word10_o = partial_write_req_count_q;
  assign real_toggle_subset_word11_o = source_switch_count_q;
  assign real_toggle_subset_word12_o = semantic_family_seen_q;
  assign real_toggle_subset_word13_o = semantic_case_seen_q;
  assign real_toggle_subset_word14_o = req_signature_q;
  assign real_toggle_subset_word15_o = rsp_signature_q;
  assign real_toggle_subset_word16_o = req_signature_delta_q;
  assign real_toggle_subset_word17_o = last_rsp_digest_q;

  assign focused_wave_word0_o = rand_state_q;
  assign focused_wave_word1_o = cycle_count_q;
  assign focused_wave_word2_o = {host_req_count_q[15:0], req_stall_count_q[15:0]};
  assign focused_wave_word3_o = {device_rsp_count_q[15:0], host_rsp_count_q[15:0]};
  assign focused_wave_word4_o = {25'd0, phase_w, rsp_pending_q, we_w, gnt_w, valid_w};
  assign focused_wave_word5_o = last_req_digest_q;
  assign focused_wave_word6_o = last_rsp_digest_q;
  assign focused_wave_word7_o = {source_switch_count_q[7:0],
                                 error_rsp_count_q[7:0],
                                 last_source_q[7:0],
                                 5'd0,
                                 source_seen_q,
                                 first_handshake_seen_q,
                                 rsp_pending_q};

  logic unused_cfg;
  assign unused_cfg = ^{32'(CoverageWords), cfg_host_d_ready_pct_i, cfg_rsp_fill_target_i,
                        cfg_rsp_delay_mode_i, cfg_reset_cycles_i, cfg_drain_cycles_i,
                        cfg_source_mask_i, rdata_w, rdata_intg_w};

endmodule
