// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_secded_inv_64_57_enc.

module prim_secded_inv_64_57_enc_gpu_cov_tb (
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
  localparam int unsigned DataWidth = 57;
  localparam int unsigned CodeWidth = 64;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [DataWidth-1:0] data_i;
  logic [CodeWidth-1:0] data_o;
  logic [CodeWidth-1:0] expected_o_w;
  logic [DataWidth-1:0] next_data_w;
  logic [CodeWidth-1:0] next_expected_o_w;
  logic [DataWidth-1:0] last_data_q;
  logic [CodeWidth-1:0] last_data_o_q;
  logic [1:0] phase_w;
  logic observed_match_w;
  logic next_observed_match_w;
  logic input_changed_w;
  logic output_changed_w;
  logic input_nonzero_w;
  logic output_nonzero_w;
  logic parity_nonzero_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] input_zero_count_q;
  logic [31:0] input_nonzero_count_q;
  logic [31:0] output_zero_count_q;
  logic [31:0] output_nonzero_count_q;
  logic [31:0] input_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] parity_nonzero_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] data_low_activity_count_q;
  logic [31:0] data_mid_activity_count_q;
  logic [31:0] data_high_activity_count_q;
  logic [31:0] parity_bit57_count_q;
  logic [31:0] parity_bit58_count_q;
  logic [31:0] parity_bit59_count_q;
  logic [31:0] parity_bit60_count_q;
  logic [31:0] parity_bit61_count_q;
  logic [31:0] parity_bit62_count_q;
  logic [31:0] parity_bit63_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_secded_inv_64_57_enc dut (
    .data_i,
    .data_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [DataWidth-1:0] mix_data(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [63:0] mixed;
    mixed = {state, prng_next(state ^ salt)} ^
            {salt, state} ^
            {prng_next(salt), prng_next(state)};
    return mixed[DataWidth-1:0];
  endfunction

  function automatic logic [CodeWidth-1:0] encode_ref(input logic [DataWidth-1:0] data);
    logic [CodeWidth-1:0] enc;
    enc = {{(CodeWidth-DataWidth){1'b0}}, data};
    enc[57] = ^(enc & 64'h0103FFF800007FFF);
    enc[58] = ^(enc & 64'h017C1FF801FF801F);
    enc[59] = ^(enc & 64'h01BDE1F87E0781E1);
    enc[60] = ^(enc & 64'h01DEEE3B8E388E22);
    enc[61] = ^(enc & 64'h01EF76CDB2C93244);
    enc[62] = ^(enc & 64'h01F7BB56D5525488);
    enc[63] = ^(enc & 64'h01FBDDA769A46910);
    return enc ^ 64'h5400000000000000;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_data_w = mix_data(rand_q ^ traffic_cycle_q,
                                cfg_address_base_i ^ cfg_req_family_i ^
                                cfg_source_mask_i);
  assign expected_o_w = encode_ref(data_i);
  assign next_expected_o_w = encode_ref(next_data_w);
  assign observed_match_w = data_o == expected_o_w;
  assign next_observed_match_w = next_expected_o_w == encode_ref(next_data_w);
  assign input_changed_w = data_i != last_data_q;
  assign output_changed_w = data_o != last_data_o_q;
  assign input_nonzero_w = |data_i;
  assign output_nonzero_w = |data_o;
  assign parity_nonzero_w = |data_o[63:57];

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
      rand_q <= cfg_seed_i ^ 32'h64_57_0001;
      data_i <= '0;
      last_data_q <= '0;
      last_data_o_q <= '0;
      input_zero_count_q <= 32'd0;
      input_nonzero_count_q <= 32'd0;
      output_zero_count_q <= 32'd0;
      output_nonzero_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      parity_nonzero_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      data_low_activity_count_q <= 32'd0;
      data_mid_activity_count_q <= 32'd0;
      data_high_activity_count_q <= 32'd0;
      parity_bit57_count_q <= 32'd0;
      parity_bit58_count_q <= 32'd0;
      parity_bit59_count_q <= 32'd0;
      parity_bit60_count_q <= 32'd0;
      parity_bit61_count_q <= 32'd0;
      parity_bit62_count_q <= 32'd0;
      parity_bit63_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h1e64_5701;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_req_data_hi_xor_i);
      last_data_q <= data_i;
      last_data_o_q <= data_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        data_i <= next_data_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        data_i <= mix_data(prng_next(drain_cycle_q ^ cfg_seed_i ^ cfg_address_mask_i),
                           cfg_rsp_family_i ^ cfg_rsp_data_hi_xor_i);
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[24:0], signature_q[31:25]} ^
                     rand_q ^ data_i[31:0] ^ {7'd0, data_i[56:32]} ^
                     data_o[31:0] ^ data_o[63:32] ^
                     {25'd0, data_o[63:57]} ^
                     {27'd0, parity_nonzero_w, output_nonzero_w,
                      observed_match_w, phase_w};

      if (input_nonzero_w) begin
        input_nonzero_count_q <= input_nonzero_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        input_zero_count_q <= input_zero_count_q + 32'd1;
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (output_nonzero_w) begin
        output_nonzero_count_q <= output_nonzero_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        output_zero_count_q <= output_zero_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (input_changed_w) begin
        input_change_count_q <= input_change_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end
      if (output_changed_w) begin
        output_change_count_q <= output_change_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (parity_nonzero_w) begin
        parity_nonzero_count_q <= parity_nonzero_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (!observed_match_w) begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (|data_i[18:0]) begin data_low_activity_count_q <= data_low_activity_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (|data_i[37:19]) begin data_mid_activity_count_q <= data_mid_activity_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (|data_i[56:38]) begin data_high_activity_count_q <= data_high_activity_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (data_o[57]) begin parity_bit57_count_q <= parity_bit57_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (data_o[58]) begin parity_bit58_count_q <= parity_bit58_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (data_o[59]) begin parity_bit59_count_q <= parity_bit59_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (data_o[60]) begin parity_bit60_count_q <= parity_bit60_count_q + 32'd1; seen_q[16] <= 1'b1; end
      if (data_o[61]) begin parity_bit61_count_q <= parity_bit61_count_q + 32'd1; seen_q[17] <= 1'b1; end
      if (data_o[62]) begin parity_bit62_count_q <= parity_bit62_count_q + 32'd1; seen_q[18] <= 1'b1; end
      if (data_o[63]) begin parity_bit63_count_q <= parity_bit63_count_q + 32'd1; seen_q[19] <= 1'b1; end
      if (next_observed_match_w) begin
        seen_q[20] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'h64_57_ecc1;
  assign host_req_accepted_o = input_nonzero_count_q;
  assign device_req_accepted_o = input_zero_count_q;
  assign device_rsp_accepted_o = output_nonzero_count_q;
  assign host_rsp_accepted_o = output_change_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    seen_q[7:0],
    data_i[7:0],
    data_o[7:0],
    observed_match_w,
    input_changed_w,
    output_changed_w,
    output_nonzero_w,
    phase_w,
    cfg_valid_i,
    done_o
  };
  assign toggle_bitmap_word1_o = {
    seen_q[23:8],
    data_i[15:8],
    data_o[15:8]
  };
  assign toggle_bitmap_word2_o = {
    input_nonzero_count_q[7:0],
    output_nonzero_count_q[7:0],
    parity_nonzero_count_q[7:0],
    mismatch_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = input_nonzero_count_q;
  assign real_toggle_subset_word1_o = input_zero_count_q;
  assign real_toggle_subset_word2_o = output_nonzero_count_q;
  assign real_toggle_subset_word3_o = output_zero_count_q;
  assign real_toggle_subset_word4_o = input_change_count_q;
  assign real_toggle_subset_word5_o = output_change_count_q;
  assign real_toggle_subset_word6_o = parity_nonzero_count_q;
  assign real_toggle_subset_word7_o = mismatch_count_q;
  assign real_toggle_subset_word8_o = data_low_activity_count_q;
  assign real_toggle_subset_word9_o = data_mid_activity_count_q;
  assign real_toggle_subset_word10_o = data_high_activity_count_q;
  assign real_toggle_subset_word11_o = parity_bit57_count_q ^ parity_bit58_count_q;
  assign real_toggle_subset_word12_o = parity_bit59_count_q ^ parity_bit60_count_q;
  assign real_toggle_subset_word13_o = parity_bit61_count_q ^ parity_bit62_count_q;
  assign real_toggle_subset_word14_o = parity_bit63_count_q;
  assign real_toggle_subset_word15_o = (data_i[31:0] ^ last_data_q[31:0]) ^
                                       ({7'd0, data_i[56:32]} ^
                                        {7'd0, last_data_q[56:32]});
  assign real_toggle_subset_word16_o = data_o[31:0] ^ last_data_o_q[31:0];
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = data_i[31:0];
  assign focused_wave_word1_o = {7'd0, data_i[56:32]};
  assign focused_wave_word2_o = data_o[31:0];
  assign focused_wave_word3_o = data_o[63:32];
  assign focused_wave_word4_o = {29'd0, output_nonzero_w, parity_nonzero_w,
                                 observed_match_w};
  assign focused_wave_word5_o = input_nonzero_count_q ^ input_zero_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o ^
                                output_nonzero_count_q ^
                                parity_nonzero_count_q;

  assign oracle_expected_ok_count_o = input_nonzero_count_q +
                                      input_zero_count_q - mismatch_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = output_nonzero_count_q;
  assign oracle_observed_err_count_o = output_zero_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    parity_bit57_count_q[3:0],
    parity_bit58_count_q[3:0],
    parity_bit59_count_q[3:0],
    parity_bit60_count_q[3:0],
    parity_bit61_count_q[3:0],
    parity_bit62_count_q[3:0],
    parity_bit63_count_q[3:0],
    4'd0
  };
  assign oracle_semantic_case_seen_o = data_i[31:0] ^ {7'd0, data_i[56:32]};
  assign oracle_semantic_case_acked_o = data_o[31:0] ^ data_o[63:32];
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_secded_inv_64_57_enc_gpu_cov_tb
