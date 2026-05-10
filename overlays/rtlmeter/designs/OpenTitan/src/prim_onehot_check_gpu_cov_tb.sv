// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_onehot_check.

module prim_onehot_check_gpu_cov_tb (
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
  localparam int unsigned AddrWidth = 3;
  localparam int unsigned OneHotWidth = 8;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [OneHotWidth-1:0] oh_i;
  logic [AddrWidth-1:0] addr_i;
  logic en_i;
  logic err_o;
  logic [1:0] phase_w;
  logic [31:0] case_mix_w;
  logic [31:0] addr_mix_w;
  logic [2:0] case_w;
  logic [2:0] next_case_w;
  logic [AddrWidth-1:0] next_addr_w;
  logic [OneHotWidth-1:0] next_oh_w;
  logic next_en_w;
  logic onehot0_err_w;
  logic enable_err_w;
  logic addr_err_w;
  logic expected_err_w;
  logic expected_ok_w;
  logic observed_match_w;
  logic addr_selected_w;
  logic any_oh_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] expected_ok_count_q;
  logic [31:0] expected_err_count_q;
  logic [31:0] observed_ok_count_q;
  logic [31:0] observed_err_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] onehot0_err_count_q;
  logic [31:0] enable_err_count_q;
  logic [31:0] addr_err_count_q;
  logic [31:0] zero_enabled_count_q;
  logic [31:0] zero_disabled_count_q;
  logic [31:0] addr_match_count_q;
  logic [31:0] addr_mismatch_count_q;
  logic [31:0] multi_hot_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_error_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_onehot_check #(
    .AddrWidth(AddrWidth),
    .OneHotWidth(OneHotWidth),
    .AddrCheck(1'b1),
    .EnableCheck(1'b1),
    .StrictCheck(1'b1),
    .EnableAlertTriggerSVA(1'b0)
  ) dut (
    .clk_i,
    .rst_ni,
    .oh_i,
    .addr_i,
    .en_i,
    .err_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [OneHotWidth-1:0] onehot_for_addr(
      input logic [AddrWidth-1:0] addr);
    logic [OneHotWidth-1:0] value;
    value = '0;
    value[addr] = 1'b1;
    return value;
  endfunction

  function automatic int unsigned count_ones8(input logic [OneHotWidth-1:0] bits);
    int unsigned count;
    count = 0;
    for (int unsigned bit_idx = 0; bit_idx < OneHotWidth; bit_idx++) begin
      if (bits[bit_idx]) begin
        count++;
      end
    end
    return count;
  endfunction

  function automatic logic [OneHotWidth-1:0] choose_oh(
      input logic [31:0] state,
      input logic [2:0] case_id,
      input logic [AddrWidth-1:0] addr);
    logic [OneHotWidth-1:0] base;
    logic [OneHotWidth-1:0] alternate;
    logic [OneHotWidth-1:0] noise;
    base = onehot_for_addr(addr);
    alternate = onehot_for_addr(addr + 3'd1);
    noise = state[OneHotWidth-1:0];
    unique case (case_id)
      3'd0: return base;
      3'd1: return '0;
      3'd2: return '0;
      3'd3: return alternate;
      3'd4: return base | alternate;
      3'd5: return base;
      3'd6: return (noise == '0) ? (base | alternate) : noise;
      default: return base;
    endcase
  endfunction

  function automatic logic choose_en(input logic [31:0] state, input logic [2:0] case_id);
    unique case (case_id)
      3'd1: return 1'b0;
      3'd5: return 1'b0;
      3'd6: return state[8];
      default: return 1'b1;
    endcase
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign case_mix_w = rand_q ^ traffic_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i;
  assign addr_mix_w = rand_q ^ cfg_address_base_i ^ cfg_address_mask_i;
  assign case_w = case_mix_w[2:0];
  assign next_case_w = (phase_w == DrainPhase) ? drain_cycle_q[2:0] : case_w;
  assign next_addr_w = addr_mix_w[AddrWidth-1:0];
  assign next_oh_w = choose_oh(rand_q ^ cfg_req_data_hi_xor_i, next_case_w, next_addr_w);
  assign next_en_w = choose_en(rand_q ^ cfg_rsp_error_pct_i, next_case_w);
  assign any_oh_w = |oh_i;
  assign addr_selected_w = oh_i[addr_i];
  assign onehot0_err_w = count_ones8(oh_i) > 1;
  assign enable_err_w = any_oh_w ^ en_i;
  assign addr_err_w = any_oh_w ^ addr_selected_w;
  assign expected_err_w = onehot0_err_w || enable_err_w || addr_err_w;
  assign expected_ok_w = !expected_err_w;
  assign observed_match_w = expected_err_w == err_o;

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
      rand_q <= cfg_seed_i ^ 32'h1ace_0abc;
      oh_i <= '0;
      addr_i <= '0;
      en_i <= 1'b0;
      expected_ok_count_q <= 32'd0;
      expected_err_count_q <= 32'd0;
      observed_ok_count_q <= 32'd0;
      observed_err_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      onehot0_err_count_q <= 32'd0;
      enable_err_count_q <= 32'd0;
      addr_err_count_q <= 32'd0;
      zero_enabled_count_q <= 32'd0;
      zero_disabled_count_q <= 32'd0;
      addr_match_count_q <= 32'd0;
      addr_mismatch_count_q <= 32'd0;
      multi_hot_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'hc001_0ace;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_error_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_source_mask_i);

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        oh_i <= next_oh_w;
        addr_i <= next_addr_w;
        en_i <= next_en_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        oh_i <= next_oh_w;
        addr_i <= drain_cycle_q[AddrWidth-1:0];
        en_i <= next_en_w;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[26:0], signature_q[31:27]} ^
                     {24'd0, oh_i} ^ {29'd0, addr_i} ^
                     {29'd0, en_i, err_o, expected_err_w} ^ rand_q;

      if (expected_ok_w) begin
        expected_ok_count_q <= expected_ok_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        expected_err_count_q <= expected_err_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (!err_o) begin
        observed_ok_count_q <= observed_ok_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        observed_err_count_q <= observed_err_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (!observed_match_w) begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (onehot0_err_w) begin
        onehot0_err_count_q <= onehot0_err_count_q + 32'd1;
        multi_hot_count_q <= multi_hot_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (enable_err_w) begin
        enable_err_count_q <= enable_err_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (addr_err_w) begin
        addr_err_count_q <= addr_err_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (!any_oh_w && en_i) begin
        zero_enabled_count_q <= zero_enabled_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (!any_oh_w && !en_i) begin
        zero_disabled_count_q <= zero_disabled_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (any_oh_w && addr_selected_w) begin
        addr_match_count_q <= addr_match_count_q + 32'd1;
        seen_q[12] <= 1'b1;
      end
      if (any_oh_w && !addr_selected_w) begin
        addr_mismatch_count_q <= addr_mismatch_count_q + 32'd1;
        seen_q[13] <= 1'b1;
      end
      if (expected_err_count_q == 32'd0 && expected_ok_w) begin
        pre_error_cycles_q <= pre_error_cycles_q + 32'd1;
      end
      if (next_case_w == 3'd6) begin
        seen_q[14] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'h01e0_0ace;
  assign host_req_accepted_o = expected_ok_count_q;
  assign device_req_accepted_o = expected_err_count_q;
  assign device_rsp_accepted_o = observed_ok_count_q;
  assign host_rsp_accepted_o = observed_err_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    seen_q[11:0],
    oh_i,
    addr_i,
    en_i,
    err_o,
    expected_err_w,
    rst_ni,
    done_o,
    phase_w,
    cfg_valid_i,
    global_cycle_q[0]
  };
  assign toggle_bitmap_word1_o = {
    seen_q[27:12],
    case_w,
    next_case_w,
    addr_selected_w,
    any_oh_w,
    onehot0_err_w,
    enable_err_w,
    addr_err_w,
    observed_match_w,
    phase_w,
    cfg_valid_i,
    done_o
  };
  assign toggle_bitmap_word2_o = {
    expected_ok_count_q[7:0],
    expected_err_count_q[7:0],
    observed_ok_count_q[7:0],
    observed_err_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = expected_ok_count_q;
  assign real_toggle_subset_word1_o = expected_err_count_q;
  assign real_toggle_subset_word2_o = observed_ok_count_q;
  assign real_toggle_subset_word3_o = observed_err_count_q;
  assign real_toggle_subset_word4_o = mismatch_count_q;
  assign real_toggle_subset_word5_o = onehot0_err_count_q;
  assign real_toggle_subset_word6_o = enable_err_count_q;
  assign real_toggle_subset_word7_o = addr_err_count_q;
  assign real_toggle_subset_word8_o = zero_enabled_count_q;
  assign real_toggle_subset_word9_o = zero_disabled_count_q;
  assign real_toggle_subset_word10_o = addr_match_count_q;
  assign real_toggle_subset_word11_o = addr_mismatch_count_q;
  assign real_toggle_subset_word12_o = traffic_cycle_q;
  assign real_toggle_subset_word13_o = drain_cycle_q;
  assign real_toggle_subset_word14_o = rand_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {24'd0, oh_i};
  assign focused_wave_word1_o = {29'd0, addr_i};
  assign focused_wave_word2_o = {29'd0, en_i, err_o, expected_err_w};
  assign focused_wave_word3_o = expected_ok_count_q ^ expected_err_count_q;
  assign focused_wave_word4_o = observed_ok_count_q ^ observed_err_count_q;
  assign focused_wave_word5_o = onehot0_err_count_q ^ enable_err_count_q ^ addr_err_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = expected_ok_count_q;
  assign oracle_expected_err_count_o = expected_err_count_q;
  assign oracle_observed_ok_count_o = observed_ok_count_q;
  assign oracle_observed_err_count_o = observed_err_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    zero_enabled_count_q[7:0],
    zero_disabled_count_q[7:0],
    addr_match_count_q[7:0],
    addr_mismatch_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {18'd0, case_w, next_case_w, oh_i};
  assign oracle_semantic_case_acked_o = {29'd0, en_i, err_o, expected_err_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_error_cycles_q;
endmodule : prim_onehot_check_gpu_cov_tb
