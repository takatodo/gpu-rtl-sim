// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_slicer.

module prim_slicer_gpu_cov_tb (
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
  localparam int unsigned InW = 16;
  localparam int unsigned OutW = 8;
  localparam int unsigned IndexW = 1;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [IndexW-1:0] sel_i;
  logic [InW-1:0] data_i;
  logic [OutW-1:0] data_o;
  logic [OutW-1:0] expected_data_w;
  logic [OutW-1:0] next_expected_data_w;
  logic [InW-1:0] next_data_w;
  logic [31:0] next_sel_mix_w;
  logic [IndexW-1:0] next_sel_w;
  logic [InW-1:0] last_data_q;
  logic [OutW-1:0] last_data_o_q;
  logic [IndexW-1:0] last_sel_q;
  logic [1:0] phase_w;
  logic observed_match_w;
  logic input_changed_w;
  logic output_changed_w;
  logic select_changed_w;
  logic low_byte_nonzero_w;
  logic high_byte_nonzero_w;
  logic output_any_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] low_select_count_q;
  logic [31:0] high_select_count_q;
  logic [31:0] data_nonzero_count_q;
  logic [31:0] zero_out_count_q;
  logic [31:0] nonzero_out_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] input_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] select_change_count_q;
  logic [31:0] low_byte_nonzero_count_q;
  logic [31:0] high_byte_nonzero_count_q;
  logic [31:0] match_count_q;
  logic [31:0] out_bit0_count_q;
  logic [31:0] out_bit1_count_q;
  logic [31:0] out_bit2_count_q;
  logic [31:0] out_bit3_count_q;
  logic [31:0] out_bit4_count_q;
  logic [31:0] out_bit5_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_slicer #(
    .InW(InW),
    .OutW(OutW),
    .IndexW(IndexW)
  ) dut (
    .sel_i,
    .data_i,
    .data_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [InW-1:0] mix_data(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [31:0] mixed;
    mixed = state ^ {state[7:0], state[31:8]} ^ salt;
    return mixed[InW-1:0];
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_data_w = mix_data(rand_q ^ traffic_cycle_q,
                                cfg_address_base_i ^ cfg_req_data_hi_xor_i ^
                                cfg_source_mask_i);
  assign next_sel_mix_w = prng_next(rand_q ^ cfg_req_family_i ^ traffic_cycle_q);
  assign next_sel_w = next_sel_mix_w[IndexW-1:0];
  assign expected_data_w = sel_i ? data_i[15:8] : data_i[7:0];
  assign next_expected_data_w = next_sel_w ? next_data_w[15:8] : next_data_w[7:0];
  assign observed_match_w = data_o == expected_data_w;
  assign input_changed_w = data_i != last_data_q;
  assign output_changed_w = data_o != last_data_o_q;
  assign select_changed_w = sel_i != last_sel_q;
  assign low_byte_nonzero_w = |data_i[7:0];
  assign high_byte_nonzero_w = |data_i[15:8];
  assign output_any_w = |data_o;

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
      rand_q <= cfg_seed_i ^ 32'h51c3_0001;
      sel_i <= '0;
      data_i <= '0;
      last_data_q <= '0;
      last_data_o_q <= '0;
      last_sel_q <= '0;
      low_select_count_q <= 32'd0;
      high_select_count_q <= 32'd0;
      data_nonzero_count_q <= 32'd0;
      zero_out_count_q <= 32'd0;
      nonzero_out_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      select_change_count_q <= 32'd0;
      low_byte_nonzero_count_q <= 32'd0;
      high_byte_nonzero_count_q <= 32'd0;
      match_count_q <= 32'd0;
      out_bit0_count_q <= 32'd0;
      out_bit1_count_q <= 32'd0;
      out_bit2_count_q <= 32'd0;
      out_bit3_count_q <= 32'd0;
      out_bit4_count_q <= 32'd0;
      out_bit5_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5151_c3a5;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_rsp_data_hi_xor_i);
      last_data_q <= data_i;
      last_data_o_q <= data_o;
      last_sel_q <= sel_i;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        data_i <= next_data_w;
        sel_i <= next_sel_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        data_i <= {cfg_seed_i[7:0] ^ drain_cycle_q[7:0],
                   cfg_address_mask_i[7:0] ^ drain_cycle_q[15:8]};
        sel_i <= drain_cycle_q[0];
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[24:0], signature_q[31:25]} ^
                     rand_q ^ {16'd0, data_i} ^ {24'd0, data_o} ^
                     {27'd0, output_any_w, observed_match_w,
                      select_changed_w, output_changed_w, input_changed_w};

      if (sel_i) begin
        high_select_count_q <= high_select_count_q + 32'd1;
      end else begin
        low_select_count_q <= low_select_count_q + 32'd1;
      end

      if (|data_i) begin
        data_nonzero_count_q <= data_nonzero_count_q + 32'd1;
      end
      if (output_any_w) begin
        nonzero_out_count_q <= nonzero_out_count_q + 32'd1;
      end else begin
        zero_out_count_q <= zero_out_count_q + 32'd1;
      end
      if (!observed_match_w) begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
      end else begin
        match_count_q <= match_count_q + 32'd1;
      end
      if (input_changed_w) input_change_count_q <= input_change_count_q + 32'd1;
      if (output_changed_w) output_change_count_q <= output_change_count_q + 32'd1;
      if (select_changed_w) select_change_count_q <= select_change_count_q + 32'd1;
      if (low_byte_nonzero_w) low_byte_nonzero_count_q <= low_byte_nonzero_count_q + 32'd1;
      if (high_byte_nonzero_w) high_byte_nonzero_count_q <= high_byte_nonzero_count_q + 32'd1;
      if (data_o[0]) out_bit0_count_q <= out_bit0_count_q + 32'd1;
      if (data_o[1]) out_bit1_count_q <= out_bit1_count_q + 32'd1;
      if (data_o[2]) out_bit2_count_q <= out_bit2_count_q + 32'd1;
      if (data_o[3]) out_bit3_count_q <= out_bit3_count_q + 32'd1;
      if (data_o[4]) out_bit4_count_q <= out_bit4_count_q + 32'd1;
      if (data_o[5]) out_bit5_count_q <= out_bit5_count_q + 32'd1;

      if (phase_w == ResetPhase) begin
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = signature_q ^ {31'd0, done_o} ^ progress_cycle_count_o;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q;
  assign progress_signature_o = signature_q;
  assign host_req_accepted_o = low_select_count_q;
  assign device_req_accepted_o = high_select_count_q;
  assign device_rsp_accepted_o = nonzero_out_count_q;
  assign host_rsp_accepted_o = match_count_q;
  assign rsp_queue_overflow_o = 32'd0;

  assign toggle_bitmap_word0_o = {data_i, data_o, 5'd0, sel_i,
                                  output_any_w, observed_match_w};
  assign toggle_bitmap_word1_o = signature_q ^
                                  {16'd0, next_expected_data_w, expected_data_w};
  assign toggle_bitmap_word2_o = {seen_q[15:0], low_byte_nonzero_w,
                                  high_byte_nonzero_w, select_changed_w,
                                  input_changed_w, output_changed_w,
                                  9'd0, phase_w};

  assign real_toggle_subset_word0_o = low_select_count_q;
  assign real_toggle_subset_word1_o = high_select_count_q;
  assign real_toggle_subset_word2_o = data_nonzero_count_q;
  assign real_toggle_subset_word3_o = zero_out_count_q;
  assign real_toggle_subset_word4_o = nonzero_out_count_q;
  assign real_toggle_subset_word5_o = mismatch_count_q;
  assign real_toggle_subset_word6_o = input_change_count_q;
  assign real_toggle_subset_word7_o = output_change_count_q;
  assign real_toggle_subset_word8_o = select_change_count_q;
  assign real_toggle_subset_word9_o = low_byte_nonzero_count_q;
  assign real_toggle_subset_word10_o = high_byte_nonzero_count_q;
  assign real_toggle_subset_word11_o = match_count_q;
  assign real_toggle_subset_word12_o = out_bit0_count_q;
  assign real_toggle_subset_word13_o = out_bit1_count_q;
  assign real_toggle_subset_word14_o = out_bit2_count_q;
  assign real_toggle_subset_word15_o = out_bit3_count_q;
  assign real_toggle_subset_word16_o = out_bit4_count_q;
  assign real_toggle_subset_word17_o = out_bit5_count_q;

  assign focused_wave_word0_o = {16'd0, data_i};
  assign focused_wave_word1_o = {24'd0, data_o};
  assign focused_wave_word2_o = {24'd0, expected_data_w};
  assign focused_wave_word3_o = {31'd0, sel_i};
  assign focused_wave_word4_o = rand_q;
  assign focused_wave_word5_o = traffic_cycle_q;
  assign focused_wave_word6_o = drain_cycle_q;
  assign focused_wave_word7_o = signature_q;

  assign oracle_expected_ok_count_o = progress_cycle_count_o;
  assign oracle_expected_err_count_o = 32'd0;
  assign oracle_observed_ok_count_o = match_count_q;
  assign oracle_observed_err_count_o = mismatch_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = seen_q;
  assign oracle_semantic_case_seen_o = {30'd0, high_select_count_q != 32'd0,
                                        low_select_count_q != 32'd0};
  assign oracle_semantic_case_acked_o = oracle_semantic_case_seen_o;
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule
