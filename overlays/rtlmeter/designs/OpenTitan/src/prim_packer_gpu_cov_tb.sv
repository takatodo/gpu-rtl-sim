// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_packer.

module prim_packer_gpu_cov_tb (
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
  localparam int unsigned InW = 8;
  localparam int unsigned OutW = 16;
  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] TrafficPhase = 3'd1;
  localparam logic [2:0] FlushPhase   = 3'd2;
  localparam logic [2:0] DrainPhase   = 3'd3;
  localparam logic [2:0] DonePhase    = 3'd4;

  logic clk_i;
  logic rst_ni;
  logic valid_i;
  logic [InW-1:0] data_i;
  logic [InW-1:0] mask_i;
  logic ready_o;
  logic valid_o;
  logic [OutW-1:0] data_o;
  logic [OutW-1:0] mask_o;
  logic ready_i;
  logic flush_i;
  logic flush_done_o;
  logic err_o;

  logic [InW-1:0] next_data_w;
  logic [InW-1:0] next_mask_w;
  logic next_valid_w;
  logic next_ready_w;
  logic ack_in_w;
  logic ack_out_w;
  logic input_changed_w;
  logic output_changed_w;
  logic mask_changed_w;
  logic partial_mask_w;
  logic full_mask_w;
  logic upper_mask_w;
  logic lower_mask_w;
  logic output_any_w;
  logic output_mask_any_w;
  logic [2:0] phase_w;

  logic [InW-1:0] last_data_q;
  logic [InW-1:0] last_mask_q;
  logic [OutW-1:0] last_data_o_q;
  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] flush_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] input_valid_count_q;
  logic [31:0] input_ready_count_q;
  logic [31:0] input_accept_count_q;
  logic [31:0] output_valid_count_q;
  logic [31:0] output_ready_count_q;
  logic [31:0] output_accept_count_q;
  logic [31:0] flush_request_count_q;
  logic [31:0] flush_done_count_q;
  logic [31:0] full_mask_count_q;
  logic [31:0] partial_mask_count_q;
  logic [31:0] upper_mask_count_q;
  logic [31:0] lower_mask_count_q;
  logic [31:0] data_nonzero_count_q;
  logic [31:0] output_nonzero_count_q;
  logic [31:0] output_mask_nonzero_count_q;
  logic [31:0] input_change_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_active_cycles_q;
  logic flush_done_seen_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_packer #(
    .InW(InW),
    .OutW(OutW),
    .HintByteData(0),
    .EnProtection(1'b0)
  ) dut (
    .clk_i,
    .rst_ni,
    .valid_i,
    .data_i,
    .mask_i,
    .ready_o,
    .valid_o,
    .data_o,
    .mask_o,
    .ready_i,
    .flush_i,
    .flush_done_o,
    .err_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [InW-1:0] mix_data(
      input logic [31:0] state,
      input logic [31:0] salt);
    logic [31:0] mixed;
    mixed = state ^ {state[10:0], state[31:11]} ^ salt;
    return mixed[InW-1:0];
  endfunction

  function automatic logic [InW-1:0] contiguous_mask(input logic [31:0] state);
    unique case (state[3:0])
      4'h0: contiguous_mask = 8'h03;
      4'h1: contiguous_mask = 8'h07;
      4'h2: contiguous_mask = 8'h0f;
      4'h3: contiguous_mask = 8'h1f;
      4'h4: contiguous_mask = 8'h3f;
      4'h5: contiguous_mask = 8'h7f;
      4'h6: contiguous_mask = 8'hff;
      4'h7: contiguous_mask = 8'hc0;
      4'h8: contiguous_mask = 8'he0;
      4'h9: contiguous_mask = 8'hf0;
      4'ha: contiguous_mask = 8'hf8;
      4'hb: contiguous_mask = 8'hfc;
      default: contiguous_mask = 8'hff;
    endcase
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign next_data_w = mix_data(rand_q ^ traffic_cycle_q,
                                cfg_address_base_i ^ cfg_req_data_hi_xor_i ^
                                cfg_source_mask_i);
  assign next_mask_w = contiguous_mask(rand_q ^ cfg_req_family_i ^
                                       cfg_put_partial_pct_i ^ traffic_cycle_q);
  assign next_valid_w = ((rand_q[2:0] < 3'd6) || (cfg_req_valid_pct_i > 32'd0) ||
                         (traffic_cycle_q[1:0] == 2'd0));
  assign next_ready_w = ((rand_q[6:4] < 3'd6) || (cfg_host_d_ready_pct_i > 32'd0) ||
                         (traffic_cycle_q[2:0] == 3'd0));
  assign ack_in_w = valid_i & ready_o;
  assign ack_out_w = valid_o & ready_i;
  assign input_changed_w = data_i != last_data_q;
  assign output_changed_w = data_o != last_data_o_q;
  assign mask_changed_w = mask_i != last_mask_q;
  assign partial_mask_w = valid_i && (mask_i != {InW{1'b1}});
  assign full_mask_w = valid_i && (mask_i == {InW{1'b1}});
  assign upper_mask_w = |mask_i[InW-1:InW/2];
  assign lower_mask_w = |mask_i[(InW/2)-1:0];
  assign output_any_w = |data_o;
  assign output_mask_any_w = |mask_o;

  always_comb begin
    if (!cfg_valid_i || !rst_ni) begin
      phase_w = ResetPhase;
    end else if (traffic_cycle_q < cfg_batch_length_i) begin
      phase_w = TrafficPhase;
    end else if (!flush_done_seen_q) begin
      phase_w = FlushPhase;
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
      valid_i <= 1'b0;
      data_i <= '0;
      mask_i <= '0;
      ready_i <= 1'b1;
      flush_i <= 1'b0;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      flush_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'hc0de_3501;
      last_data_q <= '0;
      last_mask_q <= '0;
      last_data_o_q <= '0;
      input_valid_count_q <= 32'd0;
      input_ready_count_q <= 32'd0;
      input_accept_count_q <= 32'd0;
      output_valid_count_q <= 32'd0;
      output_ready_count_q <= 32'd0;
      output_accept_count_q <= 32'd0;
      flush_request_count_q <= 32'd0;
      flush_done_count_q <= 32'd0;
      full_mask_count_q <= 32'd0;
      partial_mask_count_q <= 32'd0;
      upper_mask_count_q <= 32'd0;
      lower_mask_count_q <= 32'd0;
      data_nonzero_count_q <= 32'd0;
      output_nonzero_count_q <= 32'd0;
      output_mask_nonzero_count_q <= 32'd0;
      input_change_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h5a1c_0de5;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_active_cycles_q <= 32'd0;
      flush_done_seen_q <= 1'b0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_rsp_data_hi_xor_i);
      last_data_q <= data_i;
      last_mask_q <= mask_i;
      last_data_o_q <= data_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        valid_i <= next_valid_w;
        data_i <= next_data_w;
        mask_i <= next_mask_w;
        ready_i <= next_ready_w;
        flush_i <= 1'b0;
        seen_q[0] <= 1'b1;
      end else if (phase_w == FlushPhase) begin
        valid_i <= 1'b0;
        ready_i <= 1'b1;
        flush_i <= !flush_done_o;
        flush_cycle_q <= flush_cycle_q + 32'd1;
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ flush_cycle_q;
        seen_q[1] <= 1'b1;
        if (flush_done_o) begin
          flush_done_seen_q <= 1'b1;
          seen_q[2] <= 1'b1;
        end
      end else if (phase_w == DrainPhase) begin
        valid_i <= 1'b0;
        ready_i <= 1'b1;
        flush_i <= 1'b0;
        drain_cycle_q <= drain_cycle_q + 32'd1;
        seen_q[3] <= 1'b1;
      end

      signature_q <= {signature_q[24:0], signature_q[31:25]} ^
                     rand_q ^ {24'd0, data_i} ^ {24'd0, mask_i} ^
                     {16'd0, data_o} ^ {16'd0, mask_o} ^
                     {22'd0, err_o, flush_done_o, flush_i, ready_i, valid_o,
                      ready_o, valid_i, phase_w};

      if (valid_i) begin input_valid_count_q <= input_valid_count_q + 32'd1; seen_q[4] <= 1'b1; end
      if (ready_o) begin input_ready_count_q <= input_ready_count_q + 32'd1; seen_q[5] <= 1'b1; end
      if (ack_in_w) begin input_accept_count_q <= input_accept_count_q + 32'd1; seen_q[6] <= 1'b1; end
      if (valid_o) begin output_valid_count_q <= output_valid_count_q + 32'd1; seen_q[7] <= 1'b1; end
      if (ready_i) begin output_ready_count_q <= output_ready_count_q + 32'd1; seen_q[8] <= 1'b1; end
      if (ack_out_w) begin output_accept_count_q <= output_accept_count_q + 32'd1; seen_q[9] <= 1'b1; end
      if (flush_i) begin flush_request_count_q <= flush_request_count_q + 32'd1; seen_q[10] <= 1'b1; end
      if (flush_done_o) begin flush_done_count_q <= flush_done_count_q + 32'd1; seen_q[11] <= 1'b1; end
      if (full_mask_w) begin full_mask_count_q <= full_mask_count_q + 32'd1; seen_q[12] <= 1'b1; end
      if (partial_mask_w) begin partial_mask_count_q <= partial_mask_count_q + 32'd1; seen_q[13] <= 1'b1; end
      if (upper_mask_w) begin upper_mask_count_q <= upper_mask_count_q + 32'd1; seen_q[14] <= 1'b1; end
      if (lower_mask_w) begin lower_mask_count_q <= lower_mask_count_q + 32'd1; seen_q[15] <= 1'b1; end
      if (|data_i) begin data_nonzero_count_q <= data_nonzero_count_q + 32'd1; seen_q[16] <= 1'b1; end
      if (output_any_w) begin output_nonzero_count_q <= output_nonzero_count_q + 32'd1; seen_q[17] <= 1'b1; end
      if (output_mask_any_w) begin output_mask_nonzero_count_q <= output_mask_nonzero_count_q + 32'd1; seen_q[18] <= 1'b1; end
      if (input_changed_w || mask_changed_w) begin input_change_count_q <= input_change_count_q + 32'd1; seen_q[19] <= 1'b1; end
      if (output_changed_w) begin output_change_count_q <= output_change_count_q + 32'd1; seen_q[20] <= 1'b1; end
      if (phase_w == ResetPhase) begin
        pre_active_cycles_q <= pre_active_cycles_q + 32'd1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = signature_q ^ {31'd0, done_o} ^ progress_cycle_count_o;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q + flush_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {29'd0, phase_w};
  assign host_req_accepted_o = input_accept_count_q;
  assign device_req_accepted_o = output_accept_count_q;
  assign device_rsp_accepted_o = flush_done_count_q;
  assign host_rsp_accepted_o = output_valid_count_q;
  assign rsp_queue_overflow_o = {31'd0, err_o};

  assign toggle_bitmap_word0_o = {
    data_i,
    mask_i,
    data_o[7:0],
    mask_o[7:0]
  };
  assign toggle_bitmap_word1_o = {
    seen_q[15:0],
    data_o[15:8],
    mask_o[15:8]
  };
  assign toggle_bitmap_word2_o = {
    input_valid_count_q[5:0],
    output_valid_count_q[5:0],
    flush_done_count_q[5:0],
    4'd0,
    err_o,
    flush_done_o,
    flush_i,
    ready_i,
    valid_o,
    ready_o,
    valid_i,
    phase_w
  };

  assign real_toggle_subset_word0_o = input_valid_count_q;
  assign real_toggle_subset_word1_o = input_ready_count_q;
  assign real_toggle_subset_word2_o = input_accept_count_q;
  assign real_toggle_subset_word3_o = output_valid_count_q;
  assign real_toggle_subset_word4_o = output_ready_count_q;
  assign real_toggle_subset_word5_o = output_accept_count_q;
  assign real_toggle_subset_word6_o = flush_request_count_q;
  assign real_toggle_subset_word7_o = flush_done_count_q;
  assign real_toggle_subset_word8_o = full_mask_count_q;
  assign real_toggle_subset_word9_o = partial_mask_count_q;
  assign real_toggle_subset_word10_o = upper_mask_count_q;
  assign real_toggle_subset_word11_o = lower_mask_count_q;
  assign real_toggle_subset_word12_o = data_nonzero_count_q;
  assign real_toggle_subset_word13_o = output_nonzero_count_q;
  assign real_toggle_subset_word14_o = output_mask_nonzero_count_q;
  assign real_toggle_subset_word15_o = input_change_count_q;
  assign real_toggle_subset_word16_o = output_change_count_q;
  assign real_toggle_subset_word17_o = progress_signature_o;

  assign focused_wave_word0_o = {24'd0, data_i};
  assign focused_wave_word1_o = {24'd0, mask_i};
  assign focused_wave_word2_o = {16'd0, data_o};
  assign focused_wave_word3_o = {16'd0, mask_o};
  assign focused_wave_word4_o = {22'd0, err_o, flush_done_o, flush_i, ready_i,
                                 valid_o, ready_o, valid_i, phase_w};
  assign focused_wave_word5_o = input_accept_count_q ^ output_accept_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = input_accept_count_q + flush_done_count_q;
  assign oracle_expected_err_count_o = {31'd0, err_o};
  assign oracle_observed_ok_count_o = output_accept_count_q;
  assign oracle_observed_err_count_o = 32'd0;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    input_accept_count_q[7:0],
    output_accept_count_q[7:0],
    flush_done_count_q[7:0],
    partial_mask_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {16'd0, data_i, mask_i};
  assign oracle_semantic_case_acked_o = {data_o, mask_o};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = {31'd0, err_o};
  assign oracle_pre_handshake_traffic_cycles_o = pre_active_cycles_q;
endmodule : prim_packer_gpu_cov_tb
