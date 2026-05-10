// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Minimal deterministic coverage harness for tlul_socket_m1.

module tlul_socket_m1_gpu_cov_tb #(
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

  import tlul_pkg::*;

  localparam int unsigned HostCount = 2;

  tl_h2d_t tl_h_i [HostCount];
  tl_d2h_t tl_h_o [HostCount];
  tl_h2d_t tl_d_o;
  tl_d2h_t tl_d_i;

  logic [31:0] rand_state_q;
  logic [31:0] next_rand_state_w;
  logic [31:0] cycle_count_q;
  logic [31:0] host0_req_count_q;
  logic [31:0] host1_req_count_q;
  logic [31:0] device_req_count_q;
  logic [31:0] device_rsp_count_q;
  logic [31:0] host0_rsp_count_q;
  logic [31:0] host1_rsp_count_q;
  logic [31:0] arbitration_switch_count_q;
  logic [31:0] simultaneous_req_count_q;
  logic [31:0] expected_ok_q;
  logic [31:0] observed_ok_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] semantic_family_seen_q;
  logic [31:0] semantic_family_acked_q;
  logic [31:0] semantic_case_seen_q;
  logic [31:0] semantic_case_acked_q;
  logic [31:0] req_signature_q;
  logic [31:0] stalled_req_signature_q;
  logic [31:0] req_signature_delta_q;
  logic [31:0] pre_handshake_traffic_cycles_q;
  logic [31:0] last_req_digest_q;
  logic [31:0] last_rsp_digest_q;
  logic        first_handshake_seen_q;
  logic        device_host_seen_q;
  logic        last_device_host_id_q;

  logic traffic_en_w;
  logic drain_en_w;
  logic [31:0] cfg_effective_cycles_w;
  logic host0_req_fire_w;
  logic host1_req_fire_w;
  logic device_req_fire_w;
  logic device_rsp_fire_w;
  logic host0_rsp_fire_w;
  logic host1_rsp_fire_w;
  logic any_host_valid_w;
  logic any_host_stalled_w;
  logic both_hosts_valid_w;
  logic device_req_host_id_w;
  logic [2:0] phase_w;

  assign traffic_en_w = cfg_valid_i && !done_o;
  assign drain_en_w = cfg_valid_i && done_o;
  assign cfg_effective_cycles_w = (cfg_cycles_i != 32'd0) ? cfg_cycles_i : cfg_batch_length_i;
  assign host0_req_fire_w = tl_h_i[0].a_valid && tl_h_o[0].a_ready;
  assign host1_req_fire_w = tl_h_i[1].a_valid && tl_h_o[1].a_ready;
  assign device_req_fire_w = tl_d_o.a_valid && tl_d_i.a_ready;
  assign device_rsp_fire_w = tl_d_i.d_valid && tl_d_o.d_ready;
  assign host0_rsp_fire_w = tl_h_o[0].d_valid && tl_h_i[0].d_ready;
  assign host1_rsp_fire_w = tl_h_o[1].d_valid && tl_h_i[1].d_ready;
  assign any_host_valid_w = tl_h_i[0].a_valid || tl_h_i[1].a_valid;
  assign any_host_stalled_w = (tl_h_i[0].a_valid && !tl_h_o[0].a_ready) ||
                              (tl_h_i[1].a_valid && !tl_h_o[1].a_ready);
  assign both_hosts_valid_w = tl_h_i[0].a_valid && tl_h_i[1].a_valid;
  assign device_req_host_id_w = tl_d_o.a_source[0];
  assign phase_w = cycle_count_q[4:2];

  function automatic logic pct_hit(input logic [31:0] value, input logic [31:0] pct);
    logic [31:0] bounded_pct;
    begin
      bounded_pct = (pct > 32'd100) ? 32'd100 : pct;
      pct_hit = ((value % 32'd100) < bounded_pct);
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

  function automatic tl_a_op_e choose_opcode(input logic [31:0] state);
    logic [31:0] opcode_pick;
    logic [31:0] put_full_pct;
    logic [31:0] put_partial_pct;
    begin
      opcode_pick = (state ^ cfg_req_family_i) % 32'd100;
      put_full_pct = (cfg_put_full_pct_i > 32'd100) ? 32'd100 : cfg_put_full_pct_i;
      put_partial_pct = (cfg_put_partial_pct_i > (32'd100 - put_full_pct)) ?
                        (32'd100 - put_full_pct) : cfg_put_partial_pct_i;
      if (opcode_pick < put_full_pct) begin
        choose_opcode = PutFullData;
      end else if (opcode_pick < (put_full_pct + put_partial_pct)) begin
        choose_opcode = PutPartialData;
      end else begin
        choose_opcode = Get;
      end
    end
  endfunction

  function automatic logic [top_pkg::TL_SZW-1:0] choose_size(input logic [31:0] state);
    begin
      unique case ((state >> 4) & 32'h3)
        32'd0: choose_size = top_pkg::TL_SZW'(0);
        32'd1: choose_size = top_pkg::TL_SZW'(1);
        default: choose_size = top_pkg::TL_SZW'(2);
      endcase
    end
  endfunction

  function automatic logic [top_pkg::TL_AIW-1:0] choose_source(input logic [31:0] state);
    logic [31:0] masked_source;
    begin
      masked_source = ((state >> 8) & cfg_source_mask_i) & 32'h3f;
      choose_source = top_pkg::TL_AIW'(masked_source);
    end
  endfunction

  function automatic logic [31:0] host_req_digest(input int unsigned host_idx,
                                                  input tl_h2d_t tl,
                                                  input logic accepted);
    begin
      host_req_digest = {host_idx[0],
                         accepted,
                         5'(tl.a_size),
                         4'(tl.a_opcode),
                         tl.a_source[6:0],
                         tl.a_address[13:0]};
    end
  endfunction

  function automatic logic [31:0] device_rsp_digest(input tl_d2h_t tl, input logic accepted);
    begin
      device_rsp_digest = {accepted,
                           tl.d_error,
                           4'(tl.d_opcode),
                           tl.d_source[6:0],
                           tl.d_data[18:0]};
    end
  endfunction

  function automatic logic [31:0] semantic_case_for_req(input int unsigned host_idx,
                                                        input tl_h2d_t tl);
    logic [31:0] host_bit;
    logic [31:0] opcode_bit;
    logic [31:0] size_bit;
    begin
      host_bit = 32'h1 << (host_idx & 32'h1);
      opcode_bit = 32'h1 << (4 + 32'(tl.a_opcode));
      size_bit = 32'h1 << (12 + 32'(tl.a_size[1:0]));
      semantic_case_for_req = host_bit | opcode_bit | size_bit;
    end
  endfunction

  always_comb begin
    next_rand_state_w = lfsr_next(rand_state_q ^ cycle_count_q ^ cfg_seed_i);

    tl_h_i[0] = TL_H2D_DEFAULT;
    tl_h_i[1] = TL_H2D_DEFAULT;
    tl_d_i = TL_D2H_DEFAULT;

    for (int unsigned i = 0; i < HostCount; i++) begin
      logic [31:0] host_state;
      logic [31:0] ready_state;
      host_state = lfsr_mix(rand_state_q, 32'h5100_0000 ^ (32'(i) << 16) ^ cycle_count_q);
      ready_state = lfsr_mix(rand_state_q, 32'ha300_0000 ^ (32'(i) << 16) ^ cycle_count_q);

      tl_h_i[i].a_valid = traffic_en_w && pct_hit(host_state, cfg_req_valid_pct_i);
      tl_h_i[i].a_opcode = choose_opcode(host_state ^ (32'(i) << 4));
      tl_h_i[i].a_param = 3'b000;
      tl_h_i[i].a_size = choose_size(host_state);
      tl_h_i[i].a_source = choose_source(host_state);
      tl_h_i[i].a_address = top_pkg::TL_AW'(cfg_address_base_i ^
                                            (32'(i) << 12) ^
                                            ({12'd0, host_state[17:0], 2'b00} &
                                             cfg_address_mask_i));
      tl_h_i[i].a_mask = top_pkg::TL_DBW'((host_state[7:0] == 8'h00) ? 8'h0f : host_state[7:0]);
      tl_h_i[i].a_data = top_pkg::TL_DW'({host_state, lfsr_next(host_state)});
      tl_h_i[i].a_user = TL_A_USER_DEFAULT;
      tl_h_i[i].d_ready = (traffic_en_w || drain_en_w) &&
                          pct_hit(ready_state, cfg_host_d_ready_pct_i);
    end

    tl_d_i.a_ready = (traffic_en_w || drain_en_w) &&
                     pct_hit(rand_state_q ^ 32'h6d1c_e001, cfg_device_a_ready_pct_i);
    tl_d_i.d_valid = (traffic_en_w || drain_en_w) &&
                     tl_d_o.a_valid &&
                     pct_hit(rand_state_q ^ 32'h7a17_d002, cfg_rsp_valid_pct_i);
    tl_d_i.d_opcode = pct_hit(rand_state_q ^ 32'h4655_cafe, cfg_access_ack_data_pct_i) ?
                      AccessAckData : AccessAck;
    tl_d_i.d_param = 3'b000;
    tl_d_i.d_size = tl_d_o.a_size;
    tl_d_i.d_source = tl_d_o.a_source;
    tl_d_i.d_sink = top_pkg::TL_DIW'(rand_state_q[15:0]);
    tl_d_i.d_data = top_pkg::TL_DW'({tl_d_o.a_address[31:0],
                                     rand_state_q ^ tl_d_o.a_data[31:0]});
    tl_d_i.d_user = TL_D_USER_DEFAULT;
    tl_d_i.d_error = pct_hit(rand_state_q ^ 32'hbad0_0bad, cfg_rsp_error_pct_i);
  end

  tlul_socket_m1 #(
    .M(HostCount)
  ) dut (
    .clk_i,
    .rst_ni,
    .tl_h_i,
    .tl_h_o,
    .tl_d_o,
    .tl_d_i
  );

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      rand_state_q <= 32'h1;
      cycle_count_q <= 32'd0;
      host0_req_count_q <= 32'd0;
      host1_req_count_q <= 32'd0;
      device_req_count_q <= 32'd0;
      device_rsp_count_q <= 32'd0;
      host0_rsp_count_q <= 32'd0;
      host1_rsp_count_q <= 32'd0;
      arbitration_switch_count_q <= 32'd0;
      simultaneous_req_count_q <= 32'd0;
      expected_ok_q <= 32'd0;
      observed_ok_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      semantic_family_seen_q <= 32'd0;
      semantic_family_acked_q <= 32'd0;
      semantic_case_seen_q <= 32'd0;
      semantic_case_acked_q <= 32'd0;
      req_signature_q <= 32'd0;
      stalled_req_signature_q <= 32'd0;
      req_signature_delta_q <= 32'd0;
      pre_handshake_traffic_cycles_q <= 32'd0;
      last_req_digest_q <= 32'd0;
      last_rsp_digest_q <= 32'd0;
      first_handshake_seen_q <= 1'b0;
      device_host_seen_q <= 1'b0;
      last_device_host_id_q <= 1'b0;
      done_o <= 1'b0;
    end else if (!clk_i) begin
      // The GPU lowering may call this eval body without a real posedge; hold sequential state.
    end else if (!cfg_valid_i) begin
      rand_state_q <= cfg_seed_i ^ 32'hc001_ba5e;
      cycle_count_q <= 32'd0;
      host0_req_count_q <= 32'd0;
      host1_req_count_q <= 32'd0;
      device_req_count_q <= 32'd0;
      device_rsp_count_q <= 32'd0;
      host0_rsp_count_q <= 32'd0;
      host1_rsp_count_q <= 32'd0;
      arbitration_switch_count_q <= 32'd0;
      simultaneous_req_count_q <= 32'd0;
      expected_ok_q <= 32'd0;
      observed_ok_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      semantic_family_seen_q <= 32'd0;
      semantic_family_acked_q <= 32'd0;
      semantic_case_seen_q <= 32'd0;
      semantic_case_acked_q <= 32'd0;
      req_signature_q <= 32'd0;
      stalled_req_signature_q <= 32'd0;
      req_signature_delta_q <= 32'd0;
      pre_handshake_traffic_cycles_q <= 32'd0;
      last_req_digest_q <= 32'd0;
      last_rsp_digest_q <= 32'd0;
      first_handshake_seen_q <= 1'b0;
      device_host_seen_q <= 1'b0;
      last_device_host_id_q <= 1'b0;
      done_o <= 1'b0;
    end else begin
      rand_state_q <= next_rand_state_w;

      if (!done_o) begin
        cycle_count_q <= cycle_count_q + 32'd1;
        if (cycle_count_q + 32'd1 >= cfg_effective_cycles_w) begin
          done_o <= 1'b1;
        end
      end

      if (both_hosts_valid_w && traffic_en_w) begin
        simultaneous_req_count_q <= simultaneous_req_count_q + 32'd1;
      end

      if (any_host_valid_w && !first_handshake_seen_q) begin
        pre_handshake_traffic_cycles_q <= pre_handshake_traffic_cycles_q + 32'd1;
      end

      if (host0_req_fire_w) begin
        host0_req_count_q <= host0_req_count_q + 32'd1;
        first_handshake_seen_q <= 1'b1;
        semantic_family_seen_q <= semantic_family_seen_q | 32'h0000_0001;
        semantic_case_seen_q <= semantic_case_seen_q | semantic_case_for_req(0, tl_h_i[0]);
        req_signature_q <= req_signature_q ^ host_req_digest(0, tl_h_i[0], 1'b1);
        req_signature_delta_q <= req_signature_delta_q +
                                 (host_req_digest(0, tl_h_i[0], 1'b1) ^ last_req_digest_q);
        last_req_digest_q <= host_req_digest(0, tl_h_i[0], 1'b1);
      end

      if (host1_req_fire_w) begin
        host1_req_count_q <= host1_req_count_q + 32'd1;
        first_handshake_seen_q <= 1'b1;
        semantic_family_seen_q <= semantic_family_seen_q | 32'h0000_0002;
        semantic_case_seen_q <= semantic_case_seen_q | semantic_case_for_req(1, tl_h_i[1]);
        req_signature_q <= req_signature_q ^ host_req_digest(1, tl_h_i[1], 1'b1);
        req_signature_delta_q <= req_signature_delta_q +
                                 (host_req_digest(1, tl_h_i[1], 1'b1) ^ last_req_digest_q);
        last_req_digest_q <= host_req_digest(1, tl_h_i[1], 1'b1);
      end

      if (any_host_stalled_w) begin
        stalled_req_signature_q <= stalled_req_signature_q ^
                                   {29'd0, tl_h_i[1].a_valid, tl_h_i[0].a_valid, traffic_en_w};
      end

      if (device_req_fire_w) begin
        device_req_count_q <= device_req_count_q + 32'd1;
        if (device_host_seen_q && (last_device_host_id_q != device_req_host_id_w)) begin
          arbitration_switch_count_q <= arbitration_switch_count_q + 32'd1;
        end
        device_host_seen_q <= 1'b1;
        last_device_host_id_q <= device_req_host_id_w;
        semantic_family_acked_q <= semantic_family_acked_q |
                                   (device_req_host_id_w ? 32'h0000_0002 : 32'h0000_0001);
      end

      if (device_rsp_fire_w) begin
        device_rsp_count_q <= device_rsp_count_q + 32'd1;
        if (!tl_d_i.d_error) begin
          expected_ok_q <= expected_ok_q + 32'd1;
        end
        semantic_case_acked_q <= semantic_case_acked_q |
                                 (32'h1 << 5'(tl_d_i.d_source[0]));
        last_rsp_digest_q <= device_rsp_digest(tl_d_i, 1'b1);
      end

      if (host0_rsp_fire_w) begin
        host0_rsp_count_q <= host0_rsp_count_q + 32'd1;
        if (!tl_h_o[0].d_error) begin
          observed_ok_q <= observed_ok_q + 32'd1;
        end
      end

      if (host1_rsp_fire_w) begin
        host1_rsp_count_q <= host1_rsp_count_q + 32'd1;
        if (!tl_h_o[1].d_error) begin
          observed_ok_q <= observed_ok_q + 32'd1;
        end
      end

      if ((host0_rsp_fire_w || host1_rsp_fire_w) &&
          ((observed_ok_q > expected_ok_q) ||
           ((host0_rsp_fire_w && tl_h_o[0].d_error) ||
            (host1_rsp_fire_w && tl_h_o[1].d_error)))) begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
      end
    end
  end

  assign cycle_count_o = cycle_count_q;
  assign cfg_signature_o = cfg_seed_i ^ cfg_effective_cycles_w ^ cfg_req_family_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i;
  assign host_req_accepted_o = host0_req_count_q + host1_req_count_q;
  assign device_req_accepted_o = device_req_count_q;
  assign device_rsp_accepted_o = device_rsp_count_q;
  assign host_rsp_accepted_o = host0_rsp_count_q + host1_rsp_count_q;
  assign rsp_queue_overflow_o = 32'd0;
  assign progress_cycle_count_o = cycle_count_q;
  assign progress_signature_o = req_signature_q ^ last_req_digest_q ^ last_rsp_digest_q ^
                                {30'd0, last_device_host_id_q, device_host_seen_q};
  assign oracle_expected_ok_o = expected_ok_q;
  assign oracle_observed_ok_o = observed_ok_q;
  assign oracle_mismatch_count_o = mismatch_count_q;
  assign oracle_semantic_family_seen_o = semantic_family_seen_q;
  assign oracle_semantic_family_acked_o = semantic_family_acked_q;
  assign oracle_semantic_case_seen_o = semantic_case_seen_q;
  assign oracle_semantic_case_acked_o = semantic_case_acked_q;
  assign oracle_req_signature_o = req_signature_q;
  assign oracle_stalled_req_signature_o = stalled_req_signature_q;
  assign oracle_req_signature_delta_o = req_signature_delta_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_handshake_traffic_cycles_q;

  assign toggle_bitmap_word0_o = {done_o,
                                  rst_ni,
                                  first_handshake_seen_q,
                                  device_host_seen_q,
                                  last_device_host_id_q,
                                  3'd0,
                                  semantic_family_seen_q[7:0],
                                  host_req_accepted_o[7:0],
                                  device_req_accepted_o[7:0]};
  assign toggle_bitmap_word1_o = req_signature_q;
  assign toggle_bitmap_word2_o = {device_req_count_q[15:0], host_req_accepted_o[15:0]};
  assign toggle_bitmap_word3_o = {host_rsp_accepted_o[15:0], simultaneous_req_count_q[15:0]};

  assign real_toggle_subset_word0_o = host0_req_count_q;
  assign real_toggle_subset_word1_o = host1_req_count_q;
  assign real_toggle_subset_word2_o = device_req_count_q;
  assign real_toggle_subset_word3_o = device_rsp_count_q;
  assign real_toggle_subset_word4_o = host0_rsp_count_q;
  assign real_toggle_subset_word5_o = host1_rsp_count_q;
  assign real_toggle_subset_word6_o = arbitration_switch_count_q;
  assign real_toggle_subset_word7_o = simultaneous_req_count_q;
  assign real_toggle_subset_word8_o = semantic_family_seen_q;
  assign real_toggle_subset_word9_o = semantic_family_acked_q;
  assign real_toggle_subset_word10_o = semantic_case_seen_q;
  assign real_toggle_subset_word11_o = semantic_case_acked_q;
  assign real_toggle_subset_word12_o = req_signature_q;
  assign real_toggle_subset_word13_o = stalled_req_signature_q;
  assign real_toggle_subset_word14_o = req_signature_delta_q;
  assign real_toggle_subset_word15_o = pre_handshake_traffic_cycles_q;
  assign real_toggle_subset_word16_o = last_req_digest_q;
  assign real_toggle_subset_word17_o = last_rsp_digest_q;

  assign focused_wave_word0_o = rand_state_q;
  assign focused_wave_word1_o = cycle_count_q;
  assign focused_wave_word2_o = {host0_req_count_q[15:0], host1_req_count_q[15:0]};
  assign focused_wave_word3_o = {device_req_count_q[15:0], host_rsp_accepted_o[15:0]};
  assign focused_wave_word4_o = {23'd0, phase_w, 3'(tl_d_i.d_opcode), 3'(tl_d_o.a_opcode)};
  assign focused_wave_word5_o = last_req_digest_q;
  assign focused_wave_word6_o = last_rsp_digest_q;
  assign focused_wave_word7_o = {host_req_accepted_o[7:0],
                                 device_req_accepted_o[7:0],
                                 host_rsp_accepted_o[7:0],
                                 5'd0,
                                 last_device_host_id_q,
                                 device_host_seen_q,
                                 first_handshake_seen_q};

endmodule
