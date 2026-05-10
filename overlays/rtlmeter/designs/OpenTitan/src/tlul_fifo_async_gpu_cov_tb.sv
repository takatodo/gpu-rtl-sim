// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for tlul_fifo_async.

module tlul_fifo_async_gpu_cov_tb (
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

  logic clk_h_i;
  logic rst_h_ni;
  logic clk_d_i;
  logic rst_d_ni;
  logic [2:0] phase_h_w;
  logic [2:0] phase_d_w;

  tl_h2d_t tl_h_i;
  tl_d2h_t tl_h_o;
  tl_h2d_t tl_d_o;
  tl_d2h_t tl_d_i;

  logic host_req_fire_w;
  logic device_req_fire_w;
  logic device_rsp_fire_w;
  logic host_rsp_fire_w;
  logic host_req_blocked_w;
  logic device_rsp_blocked_w;
  logic [31:0] req_digest_w;
  logic [31:0] device_req_digest_w;
  logic [31:0] rsp_digest_w;

  logic [31:0] global_h_cycle_q;
  logic [31:0] global_d_cycle_q;
  logic [31:0] traffic_h_cycle_q;
  logic [31:0] traffic_d_cycle_q;
  logic [31:0] drain_h_cycle_q;
  logic [31:0] drain_d_cycle_q;
  logic [31:0] rand_h_q;
  logic [31:0] rand_d_q;
  logic [31:0] host_req_blocked_count_q;
  logic [31:0] device_rsp_blocked_count_q;
  logic [31:0] last_host_req_digest_q;
  logic [31:0] last_device_req_digest_q;
  logic [31:0] last_device_rsp_digest_q;
  logic [31:0] last_host_rsp_digest_q;
  logic [31:0] device_req_signature_q;
  logic [31:0] device_rsp_signature_q;
  logic [31:0] host_rsp_signature_q;
  logic [31:0] first_device_req_latency_q;
  logic [31:0] first_host_rsp_latency_q;
  logic [31:0] last_device_req_source_q;
  logic [31:0] last_device_req_data_q;
  logic [TL_SZW-1:0] last_device_req_size_q;
  tl_a_op_e last_device_req_opcode_q;

  initial begin
    clk_h_i = 1'b0;
    clk_d_i = 1'b0;
  end

  always #5 clk_h_i = ~clk_h_i;
  always #7 clk_d_i = ~clk_d_i;

  tlul_fifo_async #(
    .ReqDepth(4),
    .RspDepth(4)
  ) dut (
    .clk_h_i,
    .rst_h_ni,
    .clk_d_i,
    .rst_d_ni,
    .tl_h_i,
    .tl_h_o,
    .tl_d_o,
    .tl_d_i
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
    logic [31:0] mode_mix;
    mode_mix = cfg_req_address_mode_i ^ {cfg_req_family_i[15:0], cfg_rsp_family_i[15:0]};
    return TL_AW'(cfg_address_base_i | ((state ^ mode_mix) & cfg_address_mask_i));
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
    if (opcode == Get) begin
      return TL_DBW'(4'b1111);
    end
    return mask;
  endfunction

  function automatic logic [31:0] request_digest(input tl_h2d_t tl);
    logic [31:0] digest;
    digest = 32'(tl.a_opcode) ^ 32'(tl.a_size) ^ 32'(tl.a_param);
    digest ^= tl.a_address;
    digest ^= tl.a_data;
    digest ^= 32'(tl.a_mask) ^ 32'(tl.a_source);
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

  assign rst_h_ni = cfg_valid_i && (global_h_cycle_q >= cfg_reset_cycles_i);
  assign rst_d_ni = cfg_valid_i && (global_d_cycle_q >= (cfg_reset_cycles_i + 32'd1));

  always_comb begin
    if (!cfg_valid_i || !rst_h_ni) begin
      phase_h_w = ResetPhase;
    end else if (traffic_h_cycle_q < cfg_batch_length_i) begin
      phase_h_w = TrafficPhase;
    end else if (drain_h_cycle_q < cfg_drain_cycles_i) begin
      phase_h_w = DrainPhase;
    end else begin
      phase_h_w = DonePhase;
    end
  end

  always_comb begin
    if (!cfg_valid_i || !rst_d_ni) begin
      phase_d_w = ResetPhase;
    end else if (traffic_d_cycle_q < cfg_batch_length_i) begin
      phase_d_w = TrafficPhase;
    end else if (drain_d_cycle_q < cfg_drain_cycles_i) begin
      phase_d_w = DrainPhase;
    end else begin
      phase_d_w = DonePhase;
    end
  end

  always_comb begin
    tl_h_i = TL_H2D_DEFAULT;
    tl_h_i.d_ready = pct_hit(rand_h_q ^ 32'h99aa_7733, cfg_host_d_ready_pct_i);
    if (cfg_valid_i && phase_h_w == TrafficPhase && pct_hit(rand_h_q, cfg_req_valid_pct_i)) begin
      tl_h_i.a_valid = 1'b1;
      tl_h_i.a_opcode = choose_opcode(rand_h_q ^ 32'h0f0f_aaaa);
      tl_h_i.a_param = '0;
      tl_h_i.a_size = TL_SZW'((rand_h_q >> 2) % 3);
      tl_h_i.a_source = TL_AIW'((rand_h_q >> 8) & cfg_source_mask_i[TL_AIW-1:0]);
      tl_h_i.a_address = choose_address(rand_h_q ^ 32'h1234_5678);
      tl_h_i.a_mask = choose_mask(rand_h_q ^ 32'h3333_6666, tl_h_i.a_opcode);
      tl_h_i.a_data = (rand_h_q ^ cfg_req_data_hi_xor_i ^ cfg_req_data_mode_i) + 32'h5566_7788;
      tl_h_i.a_user = TL_A_USER_DEFAULT;
    end
  end

  always_comb begin
    tl_d_i = TL_D2H_DEFAULT;
    tl_d_i.a_ready = pct_hit(rand_d_q ^ 32'h51c3_900d, cfg_device_a_ready_pct_i);
    tl_d_i.d_valid = cfg_valid_i &&
                     (phase_d_w == TrafficPhase || phase_d_w == DrainPhase) &&
                     pct_hit(rand_d_q ^ 32'h0c5a_aa13, cfg_rsp_valid_pct_i);
    tl_d_i.d_opcode =
        ((tl_d_o.a_valid && tl_d_o.a_opcode == Get) ||
         pct_hit(rand_d_q ^ 32'h45dd_aacc, cfg_access_ack_data_pct_i)) ? AccessAckData : AccessAck;
    tl_d_i.d_param = '0;
    tl_d_i.d_size = tl_d_o.a_valid ? tl_d_o.a_size : last_device_req_size_q;
    tl_d_i.d_source = tl_d_o.a_valid ? tl_d_o.a_source : TL_AIW'(last_device_req_source_q);
    tl_d_i.d_sink = TL_DIW'(rand_d_q[TL_DIW-1:0]);
    tl_d_i.d_data = (tl_d_o.a_valid ? tl_d_o.a_data : last_device_req_data_q) ^
                    cfg_rsp_data_hi_xor_i ^ cfg_rsp_data_mode_i ^ 32'h6d39_ba21;
    tl_d_i.d_user = TL_D_USER_DEFAULT;
    tl_d_i.d_error = pct_hit(rand_d_q ^ 32'he771_1024, cfg_rsp_error_pct_i);
  end

  assign host_req_fire_w = tl_h_i.a_valid && tl_h_o.a_ready;
  assign device_req_fire_w = tl_d_o.a_valid && tl_d_i.a_ready;
  assign device_rsp_fire_w = tl_d_i.d_valid && tl_d_o.d_ready;
  assign host_rsp_fire_w = tl_h_o.d_valid && tl_h_i.d_ready;
  assign host_req_blocked_w = tl_h_i.a_valid && !tl_h_o.a_ready;
  assign device_rsp_blocked_w = tl_d_i.d_valid && !tl_d_o.d_ready;
  assign req_digest_w = request_digest(tl_h_i);
  assign device_req_digest_w = request_digest(tl_d_o);
  assign rsp_digest_w = response_digest(tl_h_o);

  always_ff @(posedge clk_h_i) begin
    if (!cfg_valid_i) begin
      global_h_cycle_q <= '0;
      traffic_h_cycle_q <= '0;
      drain_h_cycle_q <= '0;
      rand_h_q <= cfg_seed_i ^ 32'h1357_9bdf;
      host_req_accepted_o <= '0;
      host_rsp_accepted_o <= '0;
      host_req_blocked_count_q <= '0;
      oracle_req_signature_o <= '0;
      oracle_stalled_req_signature_o <= '0;
      oracle_observed_ok_count_o <= '0;
      oracle_observed_err_count_o <= '0;
      oracle_semantic_family_seen_o <= '0;
      oracle_semantic_family_acked_o <= '0;
      oracle_semantic_case_seen_o <= '0;
      oracle_semantic_case_acked_o <= '0;
      oracle_pre_handshake_traffic_cycles_o <= '0;
      last_host_req_digest_q <= '0;
      last_host_rsp_digest_q <= '0;
      host_rsp_signature_q <= '0;
      first_host_rsp_latency_q <= '0;
    end else begin
      global_h_cycle_q <= global_h_cycle_q + 32'd1;
      rand_h_q <= prng_next(rand_h_q);
      if (!rst_h_ni) begin
        traffic_h_cycle_q <= '0;
        drain_h_cycle_q <= '0;
        host_req_accepted_o <= '0;
        host_rsp_accepted_o <= '0;
        host_req_blocked_count_q <= '0;
        oracle_req_signature_o <= '0;
        oracle_stalled_req_signature_o <= '0;
        oracle_observed_ok_count_o <= '0;
        oracle_observed_err_count_o <= '0;
        oracle_semantic_family_seen_o <= '0;
        oracle_semantic_family_acked_o <= '0;
        oracle_semantic_case_seen_o <= '0;
        oracle_semantic_case_acked_o <= '0;
        oracle_pre_handshake_traffic_cycles_o <= '0;
        last_host_req_digest_q <= '0;
        last_host_rsp_digest_q <= '0;
        host_rsp_signature_q <= '0;
        first_host_rsp_latency_q <= '0;
      end else begin
        if (phase_h_w == TrafficPhase) begin
          traffic_h_cycle_q <= traffic_h_cycle_q + 32'd1;
          if (host_req_accepted_o == 32'd0) begin
            oracle_pre_handshake_traffic_cycles_o <= oracle_pre_handshake_traffic_cycles_o + 32'd1;
          end
        end
        if (phase_h_w == DrainPhase) begin
          drain_h_cycle_q <= drain_h_cycle_q + 32'd1;
        end
        if (host_req_blocked_w) begin
          host_req_blocked_count_q <= host_req_blocked_count_q + 32'd1;
          oracle_stalled_req_signature_o <= oracle_stalled_req_signature_o ^ req_digest_w;
        end
        if (host_req_fire_w) begin
          host_req_accepted_o <= host_req_accepted_o + 32'd1;
          oracle_req_signature_o <= oracle_req_signature_o ^ req_digest_w;
          last_host_req_digest_q <= req_digest_w;
          oracle_semantic_family_seen_o[0] <= 1'b1;
          oracle_semantic_family_seen_o[1] <= oracle_semantic_family_seen_o[1] |
                                              (tl_h_i.a_opcode == Get);
          oracle_semantic_family_seen_o[2] <= oracle_semantic_family_seen_o[2] |
                                              (tl_h_i.a_opcode != Get);
          oracle_semantic_case_seen_o <= oracle_semantic_case_seen_o |
                                         {27'd0, rst_d_ni, tl_h_i.a_opcode == Get,
                                          tl_h_i.a_valid, tl_h_o.a_ready, host_req_fire_w};
        end
        if (host_rsp_fire_w) begin
          host_rsp_accepted_o <= host_rsp_accepted_o + 32'd1;
          host_rsp_signature_q <= host_rsp_signature_q ^ rsp_digest_w;
          last_host_rsp_digest_q <= rsp_digest_w;
          if (first_host_rsp_latency_q == 32'd0) begin
            first_host_rsp_latency_q <= global_h_cycle_q;
          end
          if (tl_h_o.d_error) begin
            oracle_observed_err_count_o <= oracle_observed_err_count_o + 32'd1;
          end else begin
            oracle_observed_ok_count_o <= oracle_observed_ok_count_o + 32'd1;
          end
          oracle_semantic_family_acked_o[0] <= 1'b1;
          oracle_semantic_family_acked_o[1] <= oracle_semantic_family_acked_o[1] | tl_h_o.d_error;
          oracle_semantic_family_acked_o[2] <= oracle_semantic_family_acked_o[2] |
                                               (tl_h_o.d_opcode == AccessAckData);
          oracle_semantic_case_acked_o <= oracle_semantic_case_acked_o |
                                          {27'd0, rst_h_ni ^ rst_d_ni, tl_h_o.d_error,
                                           tl_h_o.d_opcode == AccessAckData,
                                           tl_h_o.d_valid, host_rsp_fire_w};
        end
      end
    end
  end

  always_ff @(posedge clk_d_i) begin
    if (!cfg_valid_i) begin
      global_d_cycle_q <= '0;
      traffic_d_cycle_q <= '0;
      drain_d_cycle_q <= '0;
      rand_d_q <= cfg_seed_i ^ 32'h2468_ace0;
      device_req_accepted_o <= '0;
      device_rsp_accepted_o <= '0;
      device_rsp_blocked_count_q <= '0;
      oracle_expected_ok_count_o <= '0;
      oracle_expected_err_count_o <= '0;
      device_req_signature_q <= '0;
      device_rsp_signature_q <= '0;
      last_device_req_digest_q <= '0;
      last_device_rsp_digest_q <= '0;
      last_device_req_source_q <= '0;
      last_device_req_data_q <= '0;
      last_device_req_size_q <= '0;
      last_device_req_opcode_q <= Get;
      first_device_req_latency_q <= '0;
    end else begin
      global_d_cycle_q <= global_d_cycle_q + 32'd1;
      rand_d_q <= prng_next(rand_d_q ^ 32'h9e37_79b9);
      if (!rst_d_ni) begin
        traffic_d_cycle_q <= '0;
        drain_d_cycle_q <= '0;
        device_req_accepted_o <= '0;
        device_rsp_accepted_o <= '0;
        device_rsp_blocked_count_q <= '0;
        oracle_expected_ok_count_o <= '0;
        oracle_expected_err_count_o <= '0;
        device_req_signature_q <= '0;
        device_rsp_signature_q <= '0;
        last_device_req_digest_q <= '0;
        last_device_rsp_digest_q <= '0;
        last_device_req_source_q <= '0;
        last_device_req_data_q <= '0;
        last_device_req_size_q <= '0;
        last_device_req_opcode_q <= Get;
        first_device_req_latency_q <= '0;
      end else begin
        if (phase_d_w == TrafficPhase) begin
          traffic_d_cycle_q <= traffic_d_cycle_q + 32'd1;
        end
        if (phase_d_w == DrainPhase) begin
          drain_d_cycle_q <= drain_d_cycle_q + 32'd1;
        end
        if (device_req_fire_w) begin
          device_req_accepted_o <= device_req_accepted_o + 32'd1;
          device_req_signature_q <= device_req_signature_q ^ device_req_digest_w;
          last_device_req_digest_q <= device_req_digest_w;
          last_device_req_source_q <= 32'(tl_d_o.a_source);
          last_device_req_data_q <= tl_d_o.a_data;
          last_device_req_size_q <= tl_d_o.a_size;
          last_device_req_opcode_q <= tl_d_o.a_opcode;
          if (first_device_req_latency_q == 32'd0) begin
            first_device_req_latency_q <= global_d_cycle_q;
          end
        end
        if (device_rsp_blocked_w) begin
          device_rsp_blocked_count_q <= device_rsp_blocked_count_q + 32'd1;
        end
        if (device_rsp_fire_w) begin
          device_rsp_accepted_o <= device_rsp_accepted_o + 32'd1;
          device_rsp_signature_q <= device_rsp_signature_q ^ response_digest(tl_d_i);
          last_device_rsp_digest_q <= response_digest(tl_d_i);
          if (tl_d_i.d_error) begin
            oracle_expected_err_count_o <= oracle_expected_err_count_o + 32'd1;
          end else begin
            oracle_expected_ok_count_o <= oracle_expected_ok_count_o + 32'd1;
          end
        end
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_h_w == DonePhase) && (phase_d_w == DonePhase);
  assign cfg_signature_o = cfg_batch_length_i ^ cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           cfg_host_d_ready_pct_i ^ cfg_device_a_ready_pct_i ^
                           cfg_put_full_pct_i ^ cfg_put_partial_pct_i ^ cfg_seed_i ^
                           cfg_reset_cycles_i ^ cfg_drain_cycles_i;
  assign rsp_queue_overflow_o = host_req_blocked_count_q + device_rsp_blocked_count_q;
  assign progress_cycle_count_o = traffic_h_cycle_q + traffic_d_cycle_q +
                                  host_req_accepted_o + host_rsp_accepted_o;
  assign oracle_req_signature_delta_o = oracle_req_signature_o ^ device_req_signature_q ^
                                        oracle_stalled_req_signature_o;
  assign oracle_req_stable_violation_o = 32'd0;
  assign progress_signature_o = oracle_req_signature_o ^ host_rsp_signature_q ^
                                device_req_signature_q ^ device_rsp_signature_q ^
                                {26'd0, phase_h_w, phase_d_w};

  assign toggle_bitmap_word0_o = {
    done_o,
    rst_h_ni,
    rst_d_ni,
    tl_h_i.a_valid,
    tl_h_o.a_ready,
    tl_d_o.a_valid,
    tl_d_i.a_ready,
    tl_d_i.d_valid,
    tl_d_o.d_ready,
    tl_h_o.d_valid,
    tl_h_i.d_ready,
    host_req_fire_w,
    device_req_fire_w,
    device_rsp_fire_w,
    host_rsp_fire_w,
    oracle_semantic_family_seen_o[7:0],
    host_req_accepted_o[7:0],
    phase_h_w[0]
  };
  assign toggle_bitmap_word1_o = host_rsp_accepted_o ^ device_rsp_accepted_o ^
                                 oracle_expected_err_count_o ^ oracle_observed_err_count_o ^
                                 {16'd0, global_h_cycle_q[7:0], global_d_cycle_q[7:0]};
  assign toggle_bitmap_word2_o = oracle_req_signature_o ^ oracle_stalled_req_signature_o ^
                                 device_req_signature_q ^ progress_signature_o;

  assign real_toggle_subset_word0_o = host_req_accepted_o;
  assign real_toggle_subset_word1_o = device_req_accepted_o;
  assign real_toggle_subset_word2_o = device_rsp_accepted_o;
  assign real_toggle_subset_word3_o = host_rsp_accepted_o;
  assign real_toggle_subset_word4_o = host_req_blocked_count_q;
  assign real_toggle_subset_word5_o = device_rsp_blocked_count_q;
  assign real_toggle_subset_word6_o = first_device_req_latency_q;
  assign real_toggle_subset_word7_o = first_host_rsp_latency_q;
  assign real_toggle_subset_word8_o = oracle_semantic_family_seen_o;
  assign real_toggle_subset_word9_o = oracle_semantic_family_acked_o;
  assign real_toggle_subset_word10_o = oracle_semantic_case_seen_o;
  assign real_toggle_subset_word11_o = oracle_semantic_case_acked_o;
  assign real_toggle_subset_word12_o = oracle_req_signature_o;
  assign real_toggle_subset_word13_o = device_req_signature_q;
  assign real_toggle_subset_word14_o = oracle_req_signature_delta_o;
  assign real_toggle_subset_word15_o = oracle_pre_handshake_traffic_cycles_o;
  assign real_toggle_subset_word16_o = last_host_req_digest_q ^ last_device_req_digest_q;
  assign real_toggle_subset_word17_o = last_device_rsp_digest_q ^ last_host_rsp_digest_q;

  assign focused_wave_word0_o = global_h_cycle_q;
  assign focused_wave_word1_o = global_d_cycle_q;
  assign focused_wave_word2_o = last_host_req_digest_q;
  assign focused_wave_word3_o = last_device_req_digest_q;
  assign focused_wave_word4_o = last_device_rsp_digest_q;
  assign focused_wave_word5_o = last_host_rsp_digest_q;
  assign focused_wave_word6_o = progress_signature_o;
  assign focused_wave_word7_o = {20'd0, phase_h_w, phase_d_w, tl_h_o.d_opcode, tl_d_i.d_opcode};

endmodule
