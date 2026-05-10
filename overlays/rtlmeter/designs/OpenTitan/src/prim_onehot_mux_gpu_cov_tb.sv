// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_onehot_mux.

module prim_onehot_mux_gpu_cov_tb (
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
  localparam int unsigned Width = 8;
  localparam int unsigned Inputs = 4;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [Width-1:0] in_i [Inputs];
  logic [Inputs-1:0] sel_i;
  logic [Width-1:0] out_o;
  logic [Width-1:0] expected_out_w;
  logic [Width-1:0] next_expected_out_w;
  logic [Width-1:0] next_in0_w;
  logic [Width-1:0] next_in1_w;
  logic [Width-1:0] next_in2_w;
  logic [Width-1:0] next_in3_w;
  logic [Inputs-1:0] next_sel_w;
  logic [Width-1:0] last_out_q;
  logic [Width-1:0] last_in0_q;
  logic [1:0] phase_w;
  logic observed_match_w;
  logic next_observed_match_w;
  logic output_any_w;
  logic next_output_any_w;
  logic input_changed_w;
  logic output_changed_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] selected_count_q;
  logic [31:0] zero_select_count_q;
  logic [31:0] zero_out_count_q;
  logic [31:0] nonzero_out_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] input_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] sel0_count_q;
  logic [31:0] sel1_count_q;
  logic [31:0] sel2_count_q;
  logic [31:0] sel3_count_q;
  logic [31:0] bit0_count_q;
  logic [31:0] bit1_count_q;
  logic [31:0] bit2_count_q;
  logic [31:0] bit3_count_q;
  logic [31:0] bit4_count_q;
  logic [31:0] bit5_count_q;
  logic [31:0] bit6_count_q;
  logic [31:0] bit7_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] zero_select_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_onehot_mux #(
    .Width(Width),
    .Inputs(Inputs)
  ) dut (
    .clk_i,
    .rst_ni,
    .in_i,
    .sel_i,
    .out_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [Width-1:0] mix_word(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [31:0] mixed;
    mixed = state ^ {state[15:0], state[31:16]} ^ salt;
    return mixed[Width-1:0];
  endfunction

  function automatic logic [Inputs-1:0] select_onehot0(input logic [31:0] state);
    unique case (state[2:0])
      3'd0: return 4'b0000;
      3'd1: return 4'b0001;
      3'd2: return 4'b0010;
      3'd3: return 4'b0100;
      3'd4: return 4'b1000;
      3'd5: return 4'b0001;
      3'd6: return 4'b0010;
      default: return 4'b0100;
    endcase
  endfunction

  function automatic logic [Width-1:0] mux_expected(
      input logic [Width-1:0] in0,
      input logic [Width-1:0] in1,
      input logic [Width-1:0] in2,
      input logic [Width-1:0] in3,
      input logic [Inputs-1:0] sel);
    logic [Width-1:0] value;
    value = '0;
    if (sel[0]) value |= in0;
    if (sel[1]) value |= in1;
    if (sel[2]) value |= in2;
    if (sel[3]) value |= in3;
    return value;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_in0_w = mix_word(rand_q ^ traffic_cycle_q, cfg_address_base_i);
  assign next_in1_w = mix_word(rand_q ^ cfg_req_data_hi_xor_i, cfg_address_mask_i);
  assign next_in2_w = mix_word(rand_q ^ cfg_rsp_data_hi_xor_i, cfg_source_mask_i);
  assign next_in3_w = mix_word(rand_q ^ cfg_req_family_i ^ cfg_rsp_family_i,
                               cfg_req_address_mode_i ^ cfg_rsp_delay_mode_i);
  assign next_sel_w = (phase_w == DrainPhase) ? select_onehot0(drain_cycle_q) :
                                                select_onehot0(rand_q ^ cfg_req_valid_pct_i);
  assign expected_out_w = mux_expected(in_i[0], in_i[1], in_i[2], in_i[3], sel_i);
  assign next_expected_out_w = mux_expected(next_in0_w, next_in1_w, next_in2_w,
                                            next_in3_w, next_sel_w);
  assign observed_match_w = out_o == expected_out_w;
  assign next_observed_match_w = next_expected_out_w == mux_expected(next_in0_w,
                                                                     next_in1_w,
                                                                     next_in2_w,
                                                                     next_in3_w,
                                                                     next_sel_w);
  assign output_any_w = |out_o;
  assign next_output_any_w = |next_expected_out_w;
  assign input_changed_w = in_i[0] != last_in0_q;
  assign output_changed_w = out_o != last_out_q;

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
      rand_q <= cfg_seed_i ^ 32'h1e0c_cafe;
      in_i[0] <= '0;
      in_i[1] <= '0;
      in_i[2] <= '0;
      in_i[3] <= '0;
      sel_i <= '0;
      last_out_q <= '0;
      last_in0_q <= '0;
      selected_count_q <= 32'd0;
      zero_select_count_q <= 32'd0;
      zero_out_count_q <= 32'd0;
      nonzero_out_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      sel0_count_q <= 32'd0;
      sel1_count_q <= 32'd0;
      sel2_count_q <= 32'd0;
      sel3_count_q <= 32'd0;
      bit0_count_q <= 32'd0;
      bit1_count_q <= 32'd0;
      bit2_count_q <= 32'd0;
      bit3_count_q <= 32'd0;
      bit4_count_q <= 32'd0;
      bit5_count_q <= 32'd0;
      bit6_count_q <= 32'd0;
      bit7_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5e1e_c710;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      zero_select_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_req_data_hi_xor_i);
      last_out_q <= out_o;
      last_in0_q <= in_i[0];

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        in_i[0] <= next_in0_w;
        in_i[1] <= next_in1_w;
        in_i[2] <= next_in2_w;
        in_i[3] <= next_in3_w;
        sel_i <= next_sel_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        in_i[0] <= drain_cycle_q[Width-1:0];
        in_i[1] <= ~drain_cycle_q[Width-1:0];
        in_i[2] <= {drain_cycle_q[3:0], drain_cycle_q[7:4]};
        in_i[3] <= cfg_seed_i[Width-1:0] ^ drain_cycle_q[Width-1:0];
        sel_i <= next_sel_w;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[26:0], signature_q[31:27]} ^
                     rand_q ^ {24'd0, out_o} ^ {28'd0, sel_i} ^
                     {28'd0, output_any_w, observed_match_w, phase_w};

      if (|sel_i) begin
        selected_count_q <= selected_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        zero_select_count_q <= zero_select_count_q + 32'd1;
        zero_select_cycles_q <= zero_select_cycles_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (output_any_w) begin
        nonzero_out_count_q <= nonzero_out_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        zero_out_count_q <= zero_out_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (!observed_match_w) begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (input_changed_w) begin
        input_change_count_q <= input_change_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (output_changed_w) begin
        output_change_count_q <= output_change_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (sel_i[0]) begin sel0_count_q <= sel0_count_q + 32'd1; seen_q[9] <= 1'b1; end
      if (sel_i[1]) begin sel1_count_q <= sel1_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (sel_i[2]) begin sel2_count_q <= sel2_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (sel_i[3]) begin sel3_count_q <= sel3_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (out_o[0]) begin bit0_count_q <= bit0_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (out_o[1]) begin bit1_count_q <= bit1_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (out_o[2]) begin bit2_count_q <= bit2_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (out_o[3]) begin bit3_count_q <= bit3_count_q + 32'd1; seen_q[16] <= 1'b1; end
      if (out_o[4]) begin bit4_count_q <= bit4_count_q + 32'd1; seen_q[17] <= 1'b1; end
      if (out_o[5]) begin bit5_count_q <= bit5_count_q + 32'd1; seen_q[18] <= 1'b1; end
      if (out_o[6]) begin bit6_count_q <= bit6_count_q + 32'd1; seen_q[19] <= 1'b1; end
      if (out_o[7]) begin bit7_count_q <= bit7_count_q + 32'd1; seen_q[20] <= 1'b1; end
      if (next_output_any_w) begin
        seen_q[21] <= 1'b1;
      end
      if (next_observed_match_w) begin
        seen_q[22] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'h1e0c_cafe;
  assign host_req_accepted_o = selected_count_q;
  assign device_req_accepted_o = zero_select_count_q;
  assign device_rsp_accepted_o = nonzero_out_count_q;
  assign host_rsp_accepted_o = output_change_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    5'd0,
    seen_q[7:0],
    out_o,
    sel_i,
    output_any_w,
    observed_match_w,
    rst_ni,
    done_o,
    phase_w,
    cfg_valid_i
  };
  assign toggle_bitmap_word1_o = {
    seen_q[23:8],
    next_sel_w,
    input_changed_w,
    output_changed_w,
    next_output_any_w,
    next_observed_match_w,
    phase_w,
    cfg_valid_i,
    done_o,
    global_cycle_q[3:0]
  };
  assign toggle_bitmap_word2_o = {
    selected_count_q[7:0],
    zero_select_count_q[7:0],
    nonzero_out_count_q[7:0],
    mismatch_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = selected_count_q;
  assign real_toggle_subset_word1_o = zero_select_count_q;
  assign real_toggle_subset_word2_o = zero_out_count_q;
  assign real_toggle_subset_word3_o = nonzero_out_count_q;
  assign real_toggle_subset_word4_o = mismatch_count_q;
  assign real_toggle_subset_word5_o = input_change_count_q;
  assign real_toggle_subset_word6_o = output_change_count_q;
  assign real_toggle_subset_word7_o = sel0_count_q;
  assign real_toggle_subset_word8_o = sel1_count_q;
  assign real_toggle_subset_word9_o = sel2_count_q;
  assign real_toggle_subset_word10_o = sel3_count_q;
  assign real_toggle_subset_word11_o = bit0_count_q;
  assign real_toggle_subset_word12_o = bit1_count_q;
  assign real_toggle_subset_word13_o = bit2_count_q;
  assign real_toggle_subset_word14_o = bit3_count_q;
  assign real_toggle_subset_word15_o = bit4_count_q ^ bit5_count_q;
  assign real_toggle_subset_word16_o = bit6_count_q ^ bit7_count_q;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {24'd0, out_o};
  assign focused_wave_word1_o = {28'd0, sel_i};
  assign focused_wave_word2_o = {29'd0, output_any_w, observed_match_w, |sel_i};
  assign focused_wave_word3_o = selected_count_q ^ zero_select_count_q;
  assign focused_wave_word4_o = zero_out_count_q ^ nonzero_out_count_q;
  assign focused_wave_word5_o = sel0_count_q ^ sel1_count_q ^ sel2_count_q ^ sel3_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = selected_count_q + zero_select_count_q - mismatch_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = nonzero_out_count_q;
  assign oracle_observed_err_count_o = zero_out_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    sel0_count_q[7:0],
    sel1_count_q[7:0],
    sel2_count_q[7:0],
    sel3_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {20'd0, out_o, sel_i};
  assign oracle_semantic_case_acked_o = {24'd0, next_expected_out_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = zero_select_cycles_q;
endmodule : prim_onehot_mux_gpu_cov_tb
