// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_msb_extend.

module prim_msb_extend_gpu_cov_tb (
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
  localparam int unsigned InWidth = 8;
  localparam int unsigned OutWidth = 16;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [InWidth-1:0] in_i;
  logic [OutWidth-1:0] out_o;
  logic [OutWidth-1:0] expected_out_w;
  logic [OutWidth-1:0] next_expected_out_w;
  logic [InWidth-1:0] next_in_w;
  logic [OutWidth-1:0] last_out_q;
  logic [InWidth-1:0] last_in_q;
  logic [1:0] phase_w;
  logic observed_match_w;
  logic next_observed_match_w;
  logic output_any_w;
  logic next_output_any_w;
  logic input_changed_w;
  logic output_changed_w;
  logic input_sign_w;
  logic sign_extend_match_w;
  logic upper_all_ones_w;
  logic upper_all_zero_w;
  logic lower_nonzero_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] positive_input_count_q;
  logic [31:0] negative_input_count_q;
  logic [31:0] zero_out_count_q;
  logic [31:0] nonzero_out_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] input_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] in_bit0_count_q;
  logic [31:0] in_bit1_count_q;
  logic [31:0] in_bit2_count_q;
  logic [31:0] in_bit3_count_q;
  logic [31:0] input_msb_count_q;
  logic [31:0] upper_ones_count_q;
  logic [31:0] upper_zero_count_q;
  logic [31:0] lower_nonzero_count_q;
  logic [31:0] sign_match_count_q;
  logic [31:0] out_low_activity_count_q;
  logic [31:0] out_high_activity_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_msb_extend #(
    .InWidth(InWidth),
    .OutWidth(OutWidth)
  ) dut (
    .in_i,
    .out_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [InWidth-1:0] mix_word(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [31:0] mixed;
    mixed = state ^ {state[15:0], state[31:16]} ^ salt;
    return mixed[InWidth-1:0];
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_in_w = mix_word(rand_q ^ traffic_cycle_q,
                              cfg_address_base_i ^ cfg_req_family_i ^
                              cfg_source_mask_i);
  assign expected_out_w = {{(OutWidth-InWidth){in_i[InWidth-1]}}, in_i};
  assign next_expected_out_w = {{(OutWidth-InWidth){next_in_w[InWidth-1]}},
                                next_in_w};
  assign observed_match_w = out_o == expected_out_w;
  assign next_observed_match_w = next_expected_out_w ==
                                 {{(OutWidth-InWidth){next_in_w[InWidth-1]}},
                                  next_in_w};
  assign output_any_w = |out_o;
  assign next_output_any_w = |next_expected_out_w;
  assign input_changed_w = in_i != last_in_q;
  assign output_changed_w = out_o != last_out_q;
  assign input_sign_w = in_i[InWidth-1];
  assign upper_all_ones_w = &out_o[OutWidth-1:InWidth];
  assign upper_all_zero_w = ~|out_o[OutWidth-1:InWidth];
  assign sign_extend_match_w = input_sign_w ? upper_all_ones_w : upper_all_zero_w;
  assign lower_nonzero_w = |out_o[InWidth-1:0];

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
      rand_q <= cfg_seed_i ^ 32'hb1e5_0001;
      in_i <= '0;
      last_out_q <= '0;
      last_in_q <= '0;
      positive_input_count_q <= 32'd0;
      negative_input_count_q <= 32'd0;
      zero_out_count_q <= 32'd0;
      nonzero_out_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      in_bit0_count_q <= 32'd0;
      in_bit1_count_q <= 32'd0;
      in_bit2_count_q <= 32'd0;
      in_bit3_count_q <= 32'd0;
      input_msb_count_q <= 32'd0;
      upper_ones_count_q <= 32'd0;
      upper_zero_count_q <= 32'd0;
      lower_nonzero_count_q <= 32'd0;
      sign_match_count_q <= 32'd0;
      out_low_activity_count_q <= 32'd0;
      out_high_activity_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5e10_b1e5;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_req_data_hi_xor_i);
      last_out_q <= out_o;
      last_in_q <= in_i;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        in_i <= next_in_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        in_i <= drain_cycle_q[InWidth-1:0] ^ cfg_seed_i[InWidth-1:0];
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[26:0], signature_q[31:27]} ^
                     rand_q ^ {24'd0, in_i} ^ {16'd0, out_o} ^
                     {26'd0, input_sign_w, sign_extend_match_w,
                      output_any_w, observed_match_w, phase_w};

      if (input_sign_w) begin
        negative_input_count_q <= negative_input_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        positive_input_count_q <= positive_input_count_q + 32'd1;
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
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
      if (in_i[0]) begin in_bit0_count_q <= in_bit0_count_q + 32'd1; seen_q[9] <= 1'b1; end
      if (in_i[1]) begin in_bit1_count_q <= in_bit1_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (in_i[2]) begin in_bit2_count_q <= in_bit2_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (in_i[3]) begin in_bit3_count_q <= in_bit3_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (input_sign_w) begin input_msb_count_q <= input_msb_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (upper_all_ones_w) begin upper_ones_count_q <= upper_ones_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (upper_all_zero_w) begin upper_zero_count_q <= upper_zero_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (lower_nonzero_w) begin lower_nonzero_count_q <= lower_nonzero_count_q + 32'd1; seen_q[16] <= 1'b1; end
      if (sign_extend_match_w) begin sign_match_count_q <= sign_match_count_q + 32'd1; seen_q[17] <= 1'b1; end
      if (|out_o[InWidth-1:0]) begin out_low_activity_count_q <= out_low_activity_count_q + 32'd1; seen_q[18] <= 1'b1; end
      if (|out_o[OutWidth-1:InWidth]) begin out_high_activity_count_q <= out_high_activity_count_q + 32'd1; seen_q[19] <= 1'b1; end
      if (next_output_any_w) begin
        seen_q[20] <= 1'b1;
      end
      if (next_observed_match_w) begin
        seen_q[21] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'hb1e5_0001;
  assign host_req_accepted_o = positive_input_count_q;
  assign device_req_accepted_o = negative_input_count_q;
  assign device_rsp_accepted_o = nonzero_out_count_q;
  assign host_rsp_accepted_o = output_change_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    seen_q[7:0],
    out_o[7:0],
    in_i,
    output_any_w,
    observed_match_w,
    rst_ni,
    done_o,
    phase_w,
    cfg_valid_i,
    input_changed_w
  };
  assign toggle_bitmap_word1_o = {
    seen_q[22:8],
    next_expected_out_w[7:0],
    output_changed_w,
    next_output_any_w,
    next_observed_match_w,
    sign_extend_match_w,
    input_sign_w,
    phase_w,
    done_o,
    cfg_valid_i
  };
  assign toggle_bitmap_word2_o = {
    positive_input_count_q[7:0],
    negative_input_count_q[7:0],
    nonzero_out_count_q[7:0],
    mismatch_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = positive_input_count_q;
  assign real_toggle_subset_word1_o = negative_input_count_q;
  assign real_toggle_subset_word2_o = zero_out_count_q;
  assign real_toggle_subset_word3_o = nonzero_out_count_q;
  assign real_toggle_subset_word4_o = mismatch_count_q;
  assign real_toggle_subset_word5_o = input_change_count_q;
  assign real_toggle_subset_word6_o = output_change_count_q;
  assign real_toggle_subset_word7_o = in_bit0_count_q;
  assign real_toggle_subset_word8_o = in_bit1_count_q;
  assign real_toggle_subset_word9_o = in_bit2_count_q;
  assign real_toggle_subset_word10_o = in_bit3_count_q;
  assign real_toggle_subset_word11_o = input_msb_count_q;
  assign real_toggle_subset_word12_o = upper_ones_count_q;
  assign real_toggle_subset_word13_o = upper_zero_count_q;
  assign real_toggle_subset_word14_o = sign_match_count_q;
  assign real_toggle_subset_word15_o = lower_nonzero_count_q ^ out_low_activity_count_q;
  assign real_toggle_subset_word16_o = out_high_activity_count_q;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {24'd0, in_i};
  assign focused_wave_word1_o = {16'd0, out_o};
  assign focused_wave_word2_o = {16'd0, expected_out_w};
  assign focused_wave_word3_o = {26'd0, input_sign_w, sign_extend_match_w,
                                 output_any_w, observed_match_w, phase_w};
  assign focused_wave_word4_o = positive_input_count_q ^ negative_input_count_q;
  assign focused_wave_word5_o = sign_match_count_q ^ mismatch_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = positive_input_count_q +
                                      negative_input_count_q - mismatch_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = nonzero_out_count_q;
  assign oracle_observed_err_count_o = zero_out_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    in_bit0_count_q[7:0],
    in_bit1_count_q[7:0],
    input_msb_count_q[7:0],
    sign_match_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {24'd0, in_i};
  assign oracle_semantic_case_acked_o = {16'd0, expected_out_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_msb_extend_gpu_cov_tb
