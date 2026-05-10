// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Minimal deterministic coverage harness for tlul_adapter_sram.

module tlul_adapter_sram_gpu_cov_tb (
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
  logic sram_req_w;
  prim_mubi_pkg::mubi4_t sram_req_type_w;
  logic sram_gnt_w;
  logic sram_we_w;
  logic [7:0] sram_addr_w;
  logic [TL_DW-1:0] sram_wdata_w;
  logic [TL_DW-1:0] sram_wmask_w;
  logic intg_error_w;
  logic [RsvdWidth-1:0] user_rsvd_w;
  logic [TL_DW-1:0] sram_rdata_w;
  logic sram_rvalid_w;
  logic [1:0] sram_rerror_w;
  logic compound_txn_w;
  prim_mubi_pkg::mubi4_t readback_en_w;
  logic readback_error_w;
  logic wr_collision_w;
  logic write_pending_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_state_q;
  logic first_handshake_seen_q;
  logic sram_rsp_pending_q;
  logic [1:0] sram_rsp_delay_q;
  logic [TL_DW-1:0] sram_rsp_data_q;
  logic [1:0] sram_rsp_error_q;
  logic [31:0] read_req_count_q;
  logic [31:0] write_req_count_q;
  logic [31:0] full_write_count_q;
  logic [31:0] partial_write_count_q;
  logic [31:0] host_stall_count_q;
  logic [31:0] sram_req_count_q;
  logic [31:0] sram_read_count_q;
  logic [31:0] sram_write_count_q;
  logic [31:0] sram_rsp_count_q;
  logic [31:0] error_rsp_count_q;
  logic [31:0] intg_error_count_q;
  logic [31:0] compound_count_q;
  logic [31:0] readback_error_count_q;
  logic [31:0] wr_collision_count_q;
  logic [31:0] write_pending_count_q;
  logic [31:0] last_req_digest_q;
  logic [31:0] last_rsp_digest_q;
  logic [31:0] last_sram_digest_q;
  logic [31:0] addr_signature_q;
  logic [31:0] data_signature_q;
  logic [31:0] sram_signature_q;
  logic [31:0] mask_signature_q;

  logic req_fire_w;
  logic rsp_fire_w;
  logic host_stall_w;
  logic is_read_w;
  logic is_full_write_w;
  logic is_partial_write_w;
  logic sram_accept_w;
  logic sram_read_accept_w;
  logic sram_write_accept_w;
  logic [31:0] req_digest_w;
  logic [31:0] rsp_digest_w;
  logic [31:0] sram_digest_w;

  initial clk_i = 1'b0;
  always #5 clk_i = ~clk_i;

  tlul_adapter_sram #(
    .SramAw(8),
    .SramDw(32),
    .Outstanding(1),
    .SramBusBankAW(8),
    .ByteAccess(1),
    .ErrOnWrite(0),
    .ErrOnRead(0),
    .CmdIntgCheck(0),
    .EnableRspIntgGen(1),
    .EnableDataIntgGen(1),
    .EnableDataIntgPt(0),
    .SecFifoPtr(0),
    .EnableReadback(0),
    .DataXorAddr(0)
  ) dut (
    .clk_i,
    .rst_ni,
    .tl_i,
    .tl_o,
    .en_ifetch_i              (en_ifetch_w),
    .req_o                    (sram_req_w),
    .req_type_o               (sram_req_type_w),
    .gnt_i                    (sram_gnt_w),
    .we_o                     (sram_we_w),
    .addr_o                   (sram_addr_w),
    .wdata_o                  (sram_wdata_w),
    .wmask_o                  (sram_wmask_w),
    .intg_error_o             (intg_error_w),
    .user_rsvd_o              (user_rsvd_w),
    .rdata_i                  (sram_rdata_w),
    .rvalid_i                 (sram_rvalid_w),
    .rerror_i                 (sram_rerror_w),
    .compound_txn_in_progress_o(compound_txn_w),
    .readback_en_i            (readback_en_w),
    .readback_error_o         (readback_error_w),
    .wr_collision_i           (wr_collision_w),
    .write_pending_i          (write_pending_w)
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
    if ((cfg_req_address_mode_i[0]) && pct_hit(state ^ 32'h11d0_a551, 32'd20)) begin
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
      return TL_DBW'(4'b0001);
    end
    if (&mask) begin
      return TL_DBW'(4'b1011);
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

  function automatic logic [31:0] sram_digest(
    input logic req,
    input logic we,
    input logic [7:0] addr,
    input logic [TL_DW-1:0] wdata,
    input logic [TL_DW-1:0] wmask,
    input logic rvalid,
    input logic [TL_DW-1:0] rdata,
    input logic [1:0] rerror
  );
    logic [31:0] digest;
    digest = {19'd0, rerror, rvalid, we, req, addr};
    digest ^= wdata ^ wmask ^ rdata;
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
      tl_i.a_user.data_intg = get_data_intg(tl_i.a_data);
    end

    sram_gnt_w = (phase_w != ResetPhase) && (phase_w != DonePhase) &&
                 !sram_rsp_pending_q &&
                 (pct_hit(rand_state_q ^ 32'h0b47_cafe, cfg_device_a_ready_pct_i) ||
                  (phase_w == DrainPhase));
    sram_rvalid_w = sram_rsp_pending_q && (sram_rsp_delay_q == 2'd0);
    sram_rdata_w = sram_rsp_data_q;
    sram_rerror_w = sram_rsp_error_q;
    en_ifetch_w = choose_mubi(rand_state_q ^ 32'h55aa_7301, cfg_access_ack_data_pct_i);
    readback_en_w = prim_mubi_pkg::MuBi4False;
    wr_collision_w = pct_hit(rand_state_q ^ 32'h8b37_4ce1,
                             cfg_rsp_fill_target_i & 32'h0000_00ff);
    write_pending_w = pct_hit(rand_state_q ^ 32'hc0de_5eed, cfg_rsp_valid_pct_i);
  end

  assign req_fire_w = tl_i.a_valid && tl_o.a_ready;
  assign rsp_fire_w = tl_o.d_valid && tl_i.d_ready;
  assign host_stall_w = tl_i.a_valid && !tl_o.a_ready;
  assign is_read_w = tl_i.a_opcode == Get;
  assign is_full_write_w = tl_i.a_opcode == PutFullData;
  assign is_partial_write_w = tl_i.a_opcode == PutPartialData;
  assign sram_accept_w = sram_req_w && sram_gnt_w;
  assign sram_read_accept_w = sram_accept_w && !sram_we_w;
  assign sram_write_accept_w = sram_accept_w && sram_we_w;
  assign req_digest_w = request_digest(tl_i);
  assign rsp_digest_w = response_digest(tl_o);
  assign sram_digest_w = sram_digest(sram_req_w, sram_we_w, sram_addr_w, sram_wdata_w, sram_wmask_w,
                                     sram_rvalid_w, sram_rdata_w, sram_rerror_w);

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= '0;
      traffic_cycle_q <= '0;
      drain_cycle_q <= '0;
      rand_state_q <= cfg_seed_i ^ 32'h2476_b8d1;
      first_handshake_seen_q <= 1'b0;
      sram_rsp_pending_q <= 1'b0;
      sram_rsp_delay_q <= '0;
      sram_rsp_data_q <= '0;
      sram_rsp_error_q <= '0;
      read_req_count_q <= '0;
      write_req_count_q <= '0;
      full_write_count_q <= '0;
      partial_write_count_q <= '0;
      host_stall_count_q <= '0;
      sram_req_count_q <= '0;
      sram_read_count_q <= '0;
      sram_write_count_q <= '0;
      sram_rsp_count_q <= '0;
      error_rsp_count_q <= '0;
      intg_error_count_q <= '0;
      compound_count_q <= '0;
      readback_error_count_q <= '0;
      wr_collision_count_q <= '0;
      write_pending_count_q <= '0;
      last_req_digest_q <= '0;
      last_rsp_digest_q <= '0;
      last_sram_digest_q <= '0;
      addr_signature_q <= '0;
      data_signature_q <= '0;
      sram_signature_q <= '0;
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
        sram_rsp_pending_q <= 1'b0;
        sram_rsp_delay_q <= '0;
        sram_rsp_data_q <= '0;
        sram_rsp_error_q <= '0;
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
        if (sram_rsp_pending_q) begin
          if (sram_rsp_delay_q != 2'd0) begin
            sram_rsp_delay_q <= sram_rsp_delay_q - 2'd1;
          end else if (sram_rvalid_w) begin
            sram_rsp_pending_q <= 1'b0;
          end
        end
        if (sram_read_accept_w) begin
          sram_rsp_pending_q <= 1'b1;
          sram_rsp_delay_q <= 2'((rand_state_q ^ cfg_rsp_delay_mode_i) & cfg_rsp_delay_max_i);
          sram_rsp_data_q <= prng_next(rand_state_q ^ cfg_rsp_data_mode_i) ^
                             cfg_rsp_data_hi_xor_i ^ {24'd0, sram_addr_w};
          sram_rsp_error_q <= pct_hit(rand_state_q ^ 32'h6a41_2f09, cfg_rsp_error_pct_i) ?
                              2'b10 : 2'b00;
        end
        if (host_stall_w) begin
          host_stall_count_q <= host_stall_count_q + 32'd1;
          rsp_queue_overflow_o <= rsp_queue_overflow_o + 32'd1;
          oracle_stalled_req_signature_o <= oracle_stalled_req_signature_o ^ req_digest_w;
        end
        if (req_fire_w) begin
          first_handshake_seen_q <= 1'b1;
          host_req_accepted_o <= host_req_accepted_o + 32'd1;
          oracle_req_signature_o <= oracle_req_signature_o ^ req_digest_w;
          oracle_req_signature_delta_o <= oracle_req_signature_delta_o ^ (req_digest_w ^ last_req_digest_q);
          last_req_digest_q <= req_digest_w;
          addr_signature_q <= addr_signature_q ^ tl_i.a_address;
          data_signature_q <= data_signature_q ^ tl_i.a_data;
          mask_signature_q <= mask_signature_q ^ {28'd0, tl_i.a_mask};
          oracle_semantic_family_seen_o <= oracle_semantic_family_seen_o |
                                           {26'd0, tl_i.a_user.instr_type == prim_mubi_pkg::MuBi4True,
                                            |sram_rsp_error_q, is_partial_write_w, is_full_write_w,
                                            is_read_w, req_fire_w};
          oracle_semantic_case_seen_o <= oracle_semantic_case_seen_o |
                                         {23'd0, host_stall_w, tl_i.d_ready, tl_i.a_address[1:0],
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
        end
        if (sram_accept_w) begin
          device_req_accepted_o <= device_req_accepted_o + 32'd1;
          sram_req_count_q <= sram_req_count_q + 32'd1;
          last_sram_digest_q <= sram_digest_w;
          sram_signature_q <= sram_signature_q ^ sram_digest_w ^ {24'd0, sram_addr_w};
          if (sram_read_accept_w) begin
            sram_read_count_q <= sram_read_count_q + 32'd1;
          end
          if (sram_write_accept_w) begin
            sram_write_count_q <= sram_write_count_q + 32'd1;
          end
        end
        if (sram_rvalid_w) begin
          device_rsp_accepted_o <= device_rsp_accepted_o + 32'd1;
          sram_rsp_count_q <= sram_rsp_count_q + 32'd1;
          sram_signature_q <= sram_signature_q ^ sram_digest_w ^ sram_rdata_w;
        end
        if (intg_error_w) begin
          intg_error_count_q <= intg_error_count_q + 32'd1;
        end
        if (compound_txn_w) begin
          compound_count_q <= compound_count_q + 32'd1;
        end
        if (readback_error_w) begin
          readback_error_count_q <= readback_error_count_q + 32'd1;
        end
        if (wr_collision_w) begin
          wr_collision_count_q <= wr_collision_count_q + 32'd1;
        end
        if (write_pending_w) begin
          write_pending_count_q <= write_pending_count_q + 32'd1;
        end
        if (rsp_fire_w) begin
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
  assign progress_signature_o = oracle_req_signature_o ^ last_rsp_digest_q ^ sram_signature_q ^
                                last_sram_digest_q ^ {31'd0, done_o};

  assign toggle_bitmap_word0_o = {
    16'd0,
    readback_error_w,
    intg_error_w,
    compound_txn_w,
    write_pending_w,
    wr_collision_w,
    sram_rvalid_w,
    sram_gnt_w,
    sram_req_w,
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
  assign toggle_bitmap_word2_o = addr_signature_q ^ data_signature_q ^ sram_signature_q;

  assign real_toggle_subset_word0_o = host_req_accepted_o;
  assign real_toggle_subset_word1_o = host_rsp_accepted_o;
  assign real_toggle_subset_word2_o = read_req_count_q;
  assign real_toggle_subset_word3_o = write_req_count_q;
  assign real_toggle_subset_word4_o = sram_req_count_q;
  assign real_toggle_subset_word5_o = sram_read_count_q;
  assign real_toggle_subset_word6_o = sram_write_count_q;
  assign real_toggle_subset_word7_o = sram_rsp_count_q;
  assign real_toggle_subset_word8_o = host_stall_count_q;
  assign real_toggle_subset_word9_o = error_rsp_count_q;
  assign real_toggle_subset_word10_o = {24'd0, sram_addr_w};
  assign real_toggle_subset_word11_o = sram_wdata_w;
  assign real_toggle_subset_word12_o = sram_rdata_w;
  assign real_toggle_subset_word13_o = addr_signature_q;
  assign real_toggle_subset_word14_o = data_signature_q;
  assign real_toggle_subset_word15_o = sram_signature_q;
  assign real_toggle_subset_word16_o = mask_signature_q;
  assign real_toggle_subset_word17_o = intg_error_count_q ^ compound_count_q ^
                                       readback_error_count_q ^ oracle_req_signature_delta_o;

  assign focused_wave_word0_o = global_cycle_q;
  assign focused_wave_word1_o = traffic_cycle_q;
  assign focused_wave_word2_o = {12'd0, sram_req_type_w, sram_req_w, sram_gnt_w, sram_we_w,
                                 sram_rvalid_w, compound_txn_w, wr_collision_w,
                                 write_pending_w, readback_error_w, sram_addr_w};
  assign focused_wave_word3_o = tl_i.a_address;
  assign focused_wave_word4_o = tl_i.a_data;
  assign focused_wave_word5_o = tl_o.d_data;
  assign focused_wave_word6_o = last_req_digest_q;
  assign focused_wave_word7_o = last_rsp_digest_q ^ last_sram_digest_q;

endmodule
