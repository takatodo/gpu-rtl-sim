// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_secded_hamming_76_68_dec.

module prim_secded_hamming_76_68_dec_gpu_cov_tb (
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
  localparam int unsigned DataWidth = 68;
  localparam int unsigned CodeWidth = 76;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic [CodeWidth-1:0] data_i;
  logic [DataWidth-1:0] data_o;
  logic [7:0] syndrome_o;
  logic [1:0] err_o;
  logic [DataWidth-1:0] expected_o_w;
  logic [CodeWidth-1:0] next_data_w;
  logic [DataWidth-1:0] next_expected_o_w;
  logic [CodeWidth-1:0] last_data_q;
  logic [DataWidth-1:0] last_data_o_q;
  logic [1:0] phase_w;
  logic observed_match_w;
  logic next_observed_match_w;
  logic input_changed_w;
  logic output_changed_w;
  logic input_nonzero_w;
  logic output_nonzero_w;
  logic syndrome_nonzero_w;
  logic single_error_w;
  logic double_error_w;

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
  logic [31:0] syndrome_nonzero_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] data_low_activity_count_q;
  logic [31:0] data_mid_activity_count_q;
  logic [31:0] data_high_activity_count_q;
  logic [31:0] syndrome_bit0_count_q;
  logic [31:0] syndrome_bit1_count_q;
  logic [31:0] syndrome_bit2_count_q;
  logic [31:0] syndrome_bit3_count_q;
  logic [31:0] syndrome_bit4_count_q;
  logic [31:0] syndrome_bit5_count_q;
  logic [31:0] syndrome_bit6_count_q;
  logic [31:0] syndrome_bit7_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_secded_hamming_76_68_dec dut (
    .data_i,
    .data_o,
    .syndrome_o,
    .err_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [DataWidth-1:0] mix_data(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [95:0] mixed;
    mixed = {state, prng_next(state ^ salt), prng_next(state + salt)} ^
            {salt, state, prng_next(salt)} ^
            {prng_next(salt), prng_next(state), state ^ salt};
    return mixed[DataWidth-1:0];
  endfunction

  function automatic logic [CodeWidth-1:0] encode_ref(input logic [DataWidth-1:0] data);
    logic [CodeWidth-1:0] enc;
    enc = {{(CodeWidth-DataWidth){1'b0}}, data};
    enc[68] = ^(enc & 76'h01AAB55555556AAAD5B);
    enc[69] = ^(enc & 76'h02CCD9999999B33366D);
    enc[70] = ^(enc & 76'h040F1E1E1E1E3C3C78E);
    enc[71] = ^(enc & 76'h08F01FE01FE03FC07F0);
    enc[72] = ^(enc & 76'h10001FFFE0003FFF800);
    enc[73] = ^(enc & 76'h20001FFFFFFFC000000);
    enc[74] = ^(enc & 76'h40FFE00000000000000);
    enc[75] = ^(enc & 76'h7FFFFFFFFFFFFFFFFFF);
    return enc;
  endfunction

  function automatic logic [7:0] syndrome_ref(input logic [CodeWidth-1:0] code);
    logic [7:0] syn;
    syn[0] = ^(code & 76'h01AAB55555556AAAD5B);
    syn[1] = ^(code & 76'h02CCD9999999B33366D);
    syn[2] = ^(code & 76'h040F1E1E1E1E3C3C78E);
    syn[3] = ^(code & 76'h08F01FE01FE03FC07F0);
    syn[4] = ^(code & 76'h10001FFFE0003FFF800);
    syn[5] = ^(code & 76'h20001FFFFFFFC000000);
    syn[6] = ^(code & 76'h40FFE00000000000000);
    syn[7] = ^(code & 76'hFFFFFFFFFFFFFFFFFFF);
    return syn;
  endfunction

  function automatic logic [DataWidth-1:0] decode_data_ref(input logic [CodeWidth-1:0] code);
    logic [7:0] syn;
    logic [DataWidth-1:0] dec;
    syn = syndrome_ref(code);
    dec[0] = (syn == 8'h83) ^ code[0];
    dec[1] = (syn == 8'h85) ^ code[1];
    dec[2] = (syn == 8'h86) ^ code[2];
    dec[3] = (syn == 8'h87) ^ code[3];
    dec[4] = (syn == 8'h89) ^ code[4];
    dec[5] = (syn == 8'h8a) ^ code[5];
    dec[6] = (syn == 8'h8b) ^ code[6];
    dec[7] = (syn == 8'h8c) ^ code[7];
    dec[8] = (syn == 8'h8d) ^ code[8];
    dec[9] = (syn == 8'h8e) ^ code[9];
    dec[10] = (syn == 8'h8f) ^ code[10];
    dec[11] = (syn == 8'h91) ^ code[11];
    dec[12] = (syn == 8'h92) ^ code[12];
    dec[13] = (syn == 8'h93) ^ code[13];
    dec[14] = (syn == 8'h94) ^ code[14];
    dec[15] = (syn == 8'h95) ^ code[15];
    dec[16] = (syn == 8'h96) ^ code[16];
    dec[17] = (syn == 8'h97) ^ code[17];
    dec[18] = (syn == 8'h98) ^ code[18];
    dec[19] = (syn == 8'h99) ^ code[19];
    dec[20] = (syn == 8'h9a) ^ code[20];
    dec[21] = (syn == 8'h9b) ^ code[21];
    dec[22] = (syn == 8'h9c) ^ code[22];
    dec[23] = (syn == 8'h9d) ^ code[23];
    dec[24] = (syn == 8'h9e) ^ code[24];
    dec[25] = (syn == 8'h9f) ^ code[25];
    dec[26] = (syn == 8'ha1) ^ code[26];
    dec[27] = (syn == 8'ha2) ^ code[27];
    dec[28] = (syn == 8'ha3) ^ code[28];
    dec[29] = (syn == 8'ha4) ^ code[29];
    dec[30] = (syn == 8'ha5) ^ code[30];
    dec[31] = (syn == 8'ha6) ^ code[31];
    dec[32] = (syn == 8'ha7) ^ code[32];
    dec[33] = (syn == 8'ha8) ^ code[33];
    dec[34] = (syn == 8'ha9) ^ code[34];
    dec[35] = (syn == 8'haa) ^ code[35];
    dec[36] = (syn == 8'hab) ^ code[36];
    dec[37] = (syn == 8'hac) ^ code[37];
    dec[38] = (syn == 8'had) ^ code[38];
    dec[39] = (syn == 8'hae) ^ code[39];
    dec[40] = (syn == 8'haf) ^ code[40];
    dec[41] = (syn == 8'hb0) ^ code[41];
    dec[42] = (syn == 8'hb1) ^ code[42];
    dec[43] = (syn == 8'hb2) ^ code[43];
    dec[44] = (syn == 8'hb3) ^ code[44];
    dec[45] = (syn == 8'hb4) ^ code[45];
    dec[46] = (syn == 8'hb5) ^ code[46];
    dec[47] = (syn == 8'hb6) ^ code[47];
    dec[48] = (syn == 8'hb7) ^ code[48];
    dec[49] = (syn == 8'hb8) ^ code[49];
    dec[50] = (syn == 8'hb9) ^ code[50];
    dec[51] = (syn == 8'hba) ^ code[51];
    dec[52] = (syn == 8'hbb) ^ code[52];
    dec[53] = (syn == 8'hbc) ^ code[53];
    dec[54] = (syn == 8'hbd) ^ code[54];
    dec[55] = (syn == 8'hbe) ^ code[55];
    dec[56] = (syn == 8'hbf) ^ code[56];
    dec[57] = (syn == 8'hc1) ^ code[57];
    dec[58] = (syn == 8'hc2) ^ code[58];
    dec[59] = (syn == 8'hc3) ^ code[59];
    dec[60] = (syn == 8'hc4) ^ code[60];
    dec[61] = (syn == 8'hc5) ^ code[61];
    dec[62] = (syn == 8'hc6) ^ code[62];
    dec[63] = (syn == 8'hc7) ^ code[63];
    dec[64] = (syn == 8'hc8) ^ code[64];
    dec[65] = (syn == 8'hc9) ^ code[65];
    dec[66] = (syn == 8'hca) ^ code[66];
    dec[67] = (syn == 8'hcb) ^ code[67];
    return dec;
  endfunction

  function automatic logic [CodeWidth-1:0] inject_error(
      input logic [CodeWidth-1:0] code,
      input logic [31:0] selector);
    logic [CodeWidth-1:0] out;
    int unsigned bit_idx;
    out = code;
    bit_idx = selector % CodeWidth;
    unique case (selector[3:0])
      4'h0: out = code;
      4'h1: out[0] = ~code[0];
      4'h2: out[5] = ~code[5];
      4'h3: out[15] = ~code[15];
      4'h4: out[37] = ~code[37];
      4'h5: out[67] = ~code[67];
      4'h6: begin out[0] = ~code[0]; out[1] = ~code[1]; end
      4'h7: begin out[3] = ~code[3]; out[68] = ~code[68]; end
      default: out[bit_idx] = ~code[bit_idx];
    endcase
    return out;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_data_w = inject_error(
      encode_ref(mix_data(rand_q ^ traffic_cycle_q,
                          cfg_address_base_i ^ cfg_req_family_i ^
                          cfg_source_mask_i)),
      rand_q ^ traffic_cycle_q ^ cfg_req_data_hi_xor_i);
  assign expected_o_w = decode_data_ref(data_i);
  assign next_expected_o_w = decode_data_ref(next_data_w);
  assign observed_match_w = data_o == expected_o_w;
  assign next_observed_match_w = next_expected_o_w == decode_data_ref(next_data_w);
  assign input_changed_w = data_i != last_data_q;
  assign output_changed_w = data_o != last_data_o_q;
  assign input_nonzero_w = |data_i;
  assign output_nonzero_w = |data_o;
  assign syndrome_nonzero_w = |syndrome_o;
  assign single_error_w = err_o[0];
  assign double_error_w = err_o[1];

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
      rand_q <= cfg_seed_i ^ 32'h76_68_00a5;
      data_i <= '0;
      last_data_q <= '0;
      last_data_o_q <= '0;
      input_zero_count_q <= 32'd0;
      input_nonzero_count_q <= 32'd0;
      output_zero_count_q <= 32'd0;
      output_nonzero_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      syndrome_nonzero_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      data_low_activity_count_q <= 32'd0;
      data_mid_activity_count_q <= 32'd0;
      data_high_activity_count_q <= 32'd0;
      syndrome_bit0_count_q <= 32'd0;
      syndrome_bit1_count_q <= 32'd0;
      syndrome_bit2_count_q <= 32'd0;
      syndrome_bit3_count_q <= 32'd0;
      syndrome_bit4_count_q <= 32'd0;
      syndrome_bit5_count_q <= 32'd0;
      syndrome_bit6_count_q <= 32'd0;
      syndrome_bit7_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h1e76_68a5;
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
        data_i <= inject_error(
            encode_ref(mix_data(prng_next(drain_cycle_q ^ cfg_seed_i ^ cfg_address_mask_i),
                                cfg_rsp_family_i ^ cfg_rsp_data_hi_xor_i)),
            drain_cycle_q ^ rand_q ^ cfg_rsp_data_hi_xor_i);
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      signature_q <= {signature_q[24:0], signature_q[31:25]} ^
                     rand_q ^ data_i[31:0] ^ data_i[63:32] ^ {24'd0, data_i[75:68]} ^
                     data_o[31:0] ^ data_o[63:32] ^ {28'd0, data_o[67:64]} ^
                     {24'd0, syndrome_o} ^ {30'd0, err_o} ^
                     {27'd0, syndrome_nonzero_w, output_nonzero_w,
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
      if (syndrome_nonzero_w) begin
        syndrome_nonzero_count_q <= syndrome_nonzero_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (!observed_match_w) begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end
      if (|data_i[7:0]) begin data_low_activity_count_q <= data_low_activity_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (|data_i[37:8]) begin data_mid_activity_count_q <= data_mid_activity_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (|data_i[75:38]) begin data_high_activity_count_q <= data_high_activity_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (syndrome_o[0]) begin syndrome_bit0_count_q <= syndrome_bit0_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (syndrome_o[1]) begin syndrome_bit1_count_q <= syndrome_bit1_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (syndrome_o[2]) begin syndrome_bit2_count_q <= syndrome_bit2_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (syndrome_o[3]) begin syndrome_bit3_count_q <= syndrome_bit3_count_q + 32'd1; seen_q[16] <= 1'b1; end
      if (syndrome_o[4]) begin syndrome_bit4_count_q <= syndrome_bit4_count_q + 32'd1; seen_q[17] <= 1'b1; end
      if (syndrome_o[5]) begin syndrome_bit5_count_q <= syndrome_bit5_count_q + 32'd1; seen_q[18] <= 1'b1; end
      if (syndrome_o[6]) begin syndrome_bit6_count_q <= syndrome_bit6_count_q + 32'd1; seen_q[20] <= 1'b1; end
      if (syndrome_o[7]) begin syndrome_bit7_count_q <= syndrome_bit7_count_q + 32'd1; seen_q[21] <= 1'b1; end
      if (next_observed_match_w) begin
        seen_q[19] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'h76_68_eca5;
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
    syndrome_nonzero_count_q[7:0],
    mismatch_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = input_nonzero_count_q;
  assign real_toggle_subset_word1_o = input_zero_count_q;
  assign real_toggle_subset_word2_o = output_nonzero_count_q;
  assign real_toggle_subset_word3_o = output_zero_count_q;
  assign real_toggle_subset_word4_o = input_change_count_q;
  assign real_toggle_subset_word5_o = output_change_count_q;
  assign real_toggle_subset_word6_o = syndrome_nonzero_count_q;
  assign real_toggle_subset_word7_o = mismatch_count_q;
  assign real_toggle_subset_word8_o = data_low_activity_count_q;
  assign real_toggle_subset_word9_o = data_mid_activity_count_q;
  assign real_toggle_subset_word10_o = data_high_activity_count_q;
  assign real_toggle_subset_word11_o = syndrome_bit0_count_q ^ syndrome_bit1_count_q;
  assign real_toggle_subset_word12_o = syndrome_bit2_count_q ^ syndrome_bit3_count_q;
  assign real_toggle_subset_word13_o = syndrome_bit4_count_q ^ syndrome_bit5_count_q ^
                                       syndrome_bit6_count_q ^ syndrome_bit7_count_q;
  assign real_toggle_subset_word14_o = {30'd0, single_error_w, double_error_w};
  assign real_toggle_subset_word15_o = data_i[31:0] ^ last_data_q[31:0];
  assign real_toggle_subset_word16_o = (data_o[31:0] ^ last_data_o_q[31:0]) ^
                                      (data_o[63:32] ^ last_data_o_q[63:32]) ^
                                      {28'd0, data_o[67:64] ^ last_data_o_q[67:64]};
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = data_i[31:0];
  assign focused_wave_word1_o = data_o[31:0] ^ data_o[63:32] ^ {28'd0, data_o[67:64]};
  assign focused_wave_word2_o = {24'd0, syndrome_o};
  assign focused_wave_word3_o = {29'd0, output_nonzero_w, syndrome_nonzero_w,
                                 observed_match_w};
  assign focused_wave_word4_o = input_nonzero_count_q ^ input_zero_count_q;
  assign focused_wave_word5_o = output_nonzero_count_q ^ syndrome_nonzero_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = input_nonzero_count_q +
                                      input_zero_count_q - mismatch_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = output_nonzero_count_q;
  assign oracle_observed_err_count_o = output_zero_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    syndrome_bit0_count_q[3:0],
    syndrome_bit1_count_q[3:0],
    syndrome_bit2_count_q[3:0],
    syndrome_bit3_count_q[3:0],
    syndrome_bit4_count_q[3:0],
    syndrome_bit5_count_q[3:0],
    syndrome_bit6_count_q[3:0],
    syndrome_bit7_count_q[3:0]
  };
  assign oracle_semantic_case_seen_o = data_i[31:0];
  assign oracle_semantic_case_acked_o = data_o[31:0] ^ data_o[63:32] ^ {28'd0, data_o[67:64]};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_secded_hamming_76_68_dec_gpu_cov_tb
