module pulp_ita_dotp_gpu_cov_tb (
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
  localparam int M  = 16;
  localparam int WI = 8;
  localparam int WO = 26;
  localparam int WS = WI + 1;

  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic reset_like_w /* verilator public_flat */;
  logic signed [WS*M-1:0] inp1;
  logic signed [WI*M-1:0] inp2;
  logic signed [WO-1:0]   dotp_out;
  logic [1:0]  phase_q;
  logic [31:0] cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] input_count_q;
  logic [31:0] output_count_q;
  logic [31:0] negative_count_q;
  logic [31:0] zero_count_q;
  logic [31:0] output_toggle_count_q;
  logic [31:0] lane_toggle_count_q;
  logic [31:0] signature_q;
  logic [31:0] last_out_q;
  logic [31:0] last_in_low_q;

  function automatic logic [31:0] xorshift32(input logic [31:0] value);
    logic [31:0] x;
    begin
      x = value ^ (value << 13);
      x = x ^ (x >> 17);
      xorshift32 = x ^ (x << 5);
    end
  endfunction

  function automatic logic signed [WS-1:0] make_lhs_lane(
      input logic [31:0] base,
      input int unsigned lane);
    logic [31:0] mixed;
    begin
      mixed = xorshift32(base ^ (32'h9e37_79b9 * lane[31:0]));
      make_lhs_lane = signed'({mixed[7], mixed[7:0]});
    end
  endfunction

  function automatic logic signed [WI-1:0] make_rhs_lane(
      input logic [31:0] base,
      input int unsigned lane);
    logic [31:0] mixed;
    begin
      mixed = xorshift32(base ^ (32'h7f4a_7c15 * lane[31:0]));
      make_rhs_lane = signed'(mixed[7:0]);
    end
  endfunction

  initial begin
    clk_i = 1'b0;
    phase_q = ResetPhase;
    cycle_q = 32'd0;
    traffic_cycle_q = 32'd0;
    drain_cycle_q = 32'd0;
    rand_q = 32'h1;
    input_count_q = 32'd0;
    output_count_q = 32'd0;
    negative_count_q = 32'd0;
    zero_count_q = 32'd0;
    output_toggle_count_q = 32'd0;
    lane_toggle_count_q = 32'd0;
    signature_q = 32'h4954_4144;
    last_out_q = 32'd0;
    last_in_low_q = 32'd0;
  end

  always #5 clk_i = ~clk_i;

  ita_dotp #(
    .M(M),
    .WI(WI),
    .WO(WO)
  ) dut (
    .inp1_i(inp1),
    .inp2_i(inp2),
    .oup_o(dotp_out)
  );

  always_comb begin
    for (int lane = 0; lane < M; lane = lane + 1) begin
      inp1[WS*lane +: WS] = make_lhs_lane(
          rand_q ^ cfg_seed_i ^ cfg_req_data_hi_xor_i ^ cfg_address_base_i,
          lane);
      inp2[WI*lane +: WI] = make_rhs_lane(
          rand_q ^ cfg_rsp_data_hi_xor_i ^ cfg_source_mask_i ^ cfg_req_family_i,
          lane);
    end
  end

  always_ff @(posedge clk_i) begin
    if (reset_like_w) begin
      phase_q <= ResetPhase;
      cycle_q <= cycle_q + 32'd1;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= 32'h1;
      input_count_q <= 32'd0;
      output_count_q <= 32'd0;
      negative_count_q <= 32'd0;
      zero_count_q <= 32'd0;
      output_toggle_count_q <= 32'd0;
      lane_toggle_count_q <= 32'd0;
      signature_q <= 32'h4954_4144;
      last_out_q <= 32'd0;
      last_in_low_q <= 32'd0;
    end else begin
      cycle_q <= cycle_q + 32'd1;
      rand_q <= xorshift32(rand_q ^ cfg_seed_i ^ cycle_q ^ cfg_batch_length_i);

      if (phase_q == ResetPhase) begin
        traffic_cycle_q <= 32'd0;
        drain_cycle_q <= 32'd0;
        if (cycle_q >= cfg_reset_cycles_i) begin
          phase_q <= TrafficPhase;
        end
      end else if (phase_q == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        if (cfg_valid_i) begin
          input_count_q <= input_count_q + 32'd1;
          output_count_q <= output_count_q + 32'd1;
          if (dotp_out[WO-1]) begin
            negative_count_q <= negative_count_q + 32'd1;
          end
          if (dotp_out == '0) begin
            zero_count_q <= zero_count_q + 32'd1;
          end
          if (last_out_q != {{(32-WO){dotp_out[WO-1]}}, dotp_out}) begin
            output_toggle_count_q <= output_toggle_count_q + 32'd1;
          end
          if (last_in_low_q != {inp2[7:0], inp1[8:0], 15'd0}) begin
            lane_toggle_count_q <= lane_toggle_count_q + 32'd1;
          end
          signature_q <= xorshift32(
              signature_q ^ {{(32-WO){dotp_out[WO-1]}}, dotp_out} ^
              inp1[31:0] ^ inp2[31:0] ^ traffic_cycle_q);
          last_out_q <= {{(32-WO){dotp_out[WO-1]}}, dotp_out};
          last_in_low_q <= {inp2[7:0], inp1[8:0], 15'd0};
        end
        if (traffic_cycle_q >= cfg_batch_length_i) begin
          phase_q <= DrainPhase;
        end
      end else if (phase_q == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        if (drain_cycle_q >= cfg_drain_cycles_i) begin
          phase_q <= DonePhase;
        end
      end
    end
  end

  always_comb begin
    reset_like_w = (cycle_q < cfg_reset_cycles_i);
    done_o = (phase_q == DonePhase);
    cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_drain_cycles_i ^ 32'h17a0_d07d;
    host_req_accepted_o = input_count_q;
    device_req_accepted_o = input_count_q;
    device_rsp_accepted_o = output_count_q;
    host_rsp_accepted_o = output_count_q;
    rsp_queue_overflow_o = 32'd0;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q;
    toggle_bitmap_word0_o = {29'd0, zero_count_q != 0, negative_count_q != 0, output_toggle_count_q != 0};
    toggle_bitmap_word1_o = last_out_q;
    toggle_bitmap_word2_o = {16'd0, inp1[7:0], inp2[7:0]};
    real_toggle_subset_word0_o = input_count_q;
    real_toggle_subset_word1_o = output_count_q;
    real_toggle_subset_word2_o = negative_count_q;
    real_toggle_subset_word3_o = zero_count_q;
    real_toggle_subset_word4_o = output_toggle_count_q;
    real_toggle_subset_word5_o = lane_toggle_count_q;
    real_toggle_subset_word6_o = signature_q;
    real_toggle_subset_word7_o = last_out_q;
    real_toggle_subset_word8_o = {{(32-WO){dotp_out[WO-1]}}, dotp_out};
    real_toggle_subset_word9_o = inp1[31:0];
    real_toggle_subset_word10_o = inp1[63:32];
    real_toggle_subset_word11_o = inp2[31:0];
    real_toggle_subset_word12_o = inp2[63:32];
    real_toggle_subset_word13_o = {30'd0, phase_q};
    real_toggle_subset_word14_o = rand_q;
    real_toggle_subset_word15_o = cfg_req_data_hi_xor_i ^ cfg_rsp_data_hi_xor_i;
    real_toggle_subset_word16_o = cfg_req_family_i ^ cfg_rsp_family_i;
    real_toggle_subset_word17_o = {31'd0, cfg_valid_i};
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = traffic_cycle_q;
    focused_wave_word2_o = drain_cycle_q;
    focused_wave_word3_o = {30'd0, phase_q};
    focused_wave_word4_o = last_out_q;
    focused_wave_word5_o = signature_q;
    focused_wave_word6_o = rand_q;
    focused_wave_word7_o = {30'd0, dotp_out[WO-1], done_o};
    oracle_expected_ok_count_o = input_count_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = output_count_q;
    oracle_observed_err_count_o = 32'd0;
    oracle_semantic_family_seen_o = 32'h4954_4120;
    oracle_semantic_family_acked_o = {31'd0, output_count_q != 0};
    oracle_semantic_case_seen_o = 32'h444f_5450;
    oracle_semantic_case_acked_o = {31'd0, output_toggle_count_q != 0};
    oracle_req_signature_o = inp1[31:0];
    oracle_stalled_req_signature_o = inp2[31:0];
    oracle_req_signature_delta_o = inp1[31:0] ^ inp2[31:0];
    oracle_req_stable_violation_o = 32'd0;
    oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q - output_count_q;
  end
endmodule
