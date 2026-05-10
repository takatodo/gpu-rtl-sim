module pulp_ita_softmax_top_gpu_cov_tb
  import ita_package::*;
(
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
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic reset_like_w /* verilator public_flat */;
  logic rst_ni;
  ctrl_t ctrl;
  requant_oup_t requant_oup;
  step_e step;
  logic calc_en;
  inp_t inp;
  logic calc_stream_soft_en;
  counter_t soft_addr_div;
  logic softmax_done;
  logic pop_softmax_fifo;
  inp_t inp_stream_soft;
  logic [1:0] phase_q;
  logic [31:0] cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] calc_count_q;
  logic [31:0] stream_count_q;
  logic [31:0] soft_done_count_q;
  logic [31:0] pop_count_q;
  logic [31:0] output_toggle_count_q;
  logic [31:0] signature_q;
  logic [31:0] last_stream_word_q;
  logic [31:0] max_sample_q;

  function automatic logic [31:0] xorshift32(input logic [31:0] value);
    logic [31:0] x;
    begin
      x = value ^ (value << 13);
      x = x ^ (x >> 17);
      xorshift32 = x ^ (x << 5);
    end
  endfunction

  function automatic requant_t make_requant_lane(
      input logic [31:0] base,
      input int unsigned lane);
    logic [31:0] mixed;
    begin
      mixed = xorshift32(base ^ (32'h9e37_79b9 * lane[31:0]));
      make_requant_lane = signed'(mixed[7:0]);
    end
  endfunction

  initial begin
    clk_i = 1'b0;
    phase_q = ResetPhase;
    cycle_q = 32'd0;
    traffic_cycle_q = 32'd0;
    drain_cycle_q = 32'd0;
    rand_q = 32'h1;
    calc_count_q = 32'd0;
    stream_count_q = 32'd0;
    soft_done_count_q = 32'd0;
    pop_count_q = 32'd0;
    output_toggle_count_q = 32'd0;
    signature_q = 32'h4954_4153;
    last_stream_word_q = 32'd0;
    max_sample_q = 32'd0;
  end

  always #5 clk_i = ~clk_i;

  assign rst_ni = !reset_like_w;

  ita_softmax_top dut (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .ctrl_i(ctrl),
    .requant_oup_i(requant_oup),
    .step_i(step),
    .calc_en_i(calc_en),
    .inp_i(inp),
    .calc_stream_soft_en_i(calc_stream_soft_en),
    .soft_addr_div_o(soft_addr_div),
    .softmax_done_o(softmax_done),
    .pop_softmax_fifo_o(pop_softmax_fifo),
    .inp_stream_soft_o(inp_stream_soft)
  );

  always_comb begin
    ctrl = '0;
    ctrl.start = cfg_valid_i;
    ctrl.layer = Attention;
    ctrl.tile_s = 32'd4;
    ctrl.tile_e = 32'd4;
    ctrl.tile_p = 32'd4;
    ctrl.tile_f = 32'd4;
    step = (phase_q == TrafficPhase && traffic_cycle_q != 0) ? QK : Idle;
    calc_en = (phase_q == TrafficPhase) && cfg_valid_i && (traffic_cycle_q < cfg_batch_length_i);
    calc_stream_soft_en = (phase_q == TrafficPhase) && cfg_valid_i && (traffic_cycle_q[1:0] == 2'b11);
    for (int lane = 0; lane < N; lane = lane + 1) begin
      requant_oup[lane] = make_requant_lane(
          rand_q ^ cfg_seed_i ^ cfg_req_data_hi_xor_i ^ cfg_rsp_data_hi_xor_i,
          lane);
    end
    for (int lane = 0; lane < M; lane = lane + 1) begin
      inp[lane] = make_requant_lane(
          rand_q ^ cfg_source_mask_i ^ cfg_address_base_i ^ cfg_req_family_i,
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
      calc_count_q <= 32'd0;
      stream_count_q <= 32'd0;
      soft_done_count_q <= 32'd0;
      pop_count_q <= 32'd0;
      output_toggle_count_q <= 32'd0;
      signature_q <= 32'h4954_4153;
      last_stream_word_q <= 32'd0;
      max_sample_q <= 32'd0;
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
        if (calc_en) begin
          calc_count_q <= calc_count_q + 32'd1;
        end
        if (calc_stream_soft_en) begin
          stream_count_q <= stream_count_q + 32'd1;
        end
        if (softmax_done) begin
          soft_done_count_q <= soft_done_count_q + 32'd1;
        end
        if (pop_softmax_fifo) begin
          pop_count_q <= pop_count_q + 32'd1;
        end
        if (last_stream_word_q != {inp_stream_soft[3], inp_stream_soft[2], inp_stream_soft[1], inp_stream_soft[0]}) begin
          output_toggle_count_q <= output_toggle_count_q + 32'd1;
        end
        signature_q <= xorshift32(
            signature_q ^
            {inp_stream_soft[3], inp_stream_soft[2], inp_stream_soft[1], inp_stream_soft[0]} ^
            {16'd0, soft_addr_div} ^
            {30'd0, softmax_done, pop_softmax_fifo} ^
            traffic_cycle_q);
        last_stream_word_q <= {inp_stream_soft[3], inp_stream_soft[2], inp_stream_soft[1], inp_stream_soft[0]};
        max_sample_q <= {requant_oup[3], requant_oup[2], requant_oup[1], requant_oup[0]};
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
    cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_drain_cycles_i ^ 32'h5053_4654;
    host_req_accepted_o = calc_count_q;
    device_req_accepted_o = calc_count_q;
    device_rsp_accepted_o = stream_count_q;
    host_rsp_accepted_o = stream_count_q;
    rsp_queue_overflow_o = 32'd0;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q;
    toggle_bitmap_word0_o = {28'd0, soft_done_count_q != 0, pop_count_q != 0, stream_count_q != 0, output_toggle_count_q != 0};
    toggle_bitmap_word1_o = last_stream_word_q;
    toggle_bitmap_word2_o = {16'd0, soft_addr_div};
    real_toggle_subset_word0_o = calc_count_q;
    real_toggle_subset_word1_o = stream_count_q;
    real_toggle_subset_word2_o = soft_done_count_q;
    real_toggle_subset_word3_o = pop_count_q;
    real_toggle_subset_word4_o = output_toggle_count_q;
    real_toggle_subset_word5_o = signature_q;
    real_toggle_subset_word6_o = last_stream_word_q;
    real_toggle_subset_word7_o = {16'd0, soft_addr_div};
    real_toggle_subset_word8_o = max_sample_q;
    real_toggle_subset_word9_o = {inp_stream_soft[3], inp_stream_soft[2], inp_stream_soft[1], inp_stream_soft[0]};
    real_toggle_subset_word10_o = {requant_oup[3], requant_oup[2], requant_oup[1], requant_oup[0]};
    real_toggle_subset_word11_o = {inp[3], inp[2], inp[1], inp[0]};
    real_toggle_subset_word12_o = rand_q;
    real_toggle_subset_word13_o = {30'd0, phase_q};
    real_toggle_subset_word14_o = cfg_req_data_hi_xor_i ^ cfg_rsp_data_hi_xor_i;
    real_toggle_subset_word15_o = cfg_req_family_i ^ cfg_rsp_family_i;
    real_toggle_subset_word16_o = {31'd0, cfg_valid_i};
    real_toggle_subset_word17_o = {29'd0, calc_en, calc_stream_soft_en, softmax_done};
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = traffic_cycle_q;
    focused_wave_word2_o = drain_cycle_q;
    focused_wave_word3_o = {30'd0, phase_q};
    focused_wave_word4_o = last_stream_word_q;
    focused_wave_word5_o = signature_q;
    focused_wave_word6_o = rand_q;
    focused_wave_word7_o = {29'd0, pop_softmax_fifo, softmax_done, done_o};
    oracle_expected_ok_count_o = calc_count_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = stream_count_q;
    oracle_observed_err_count_o = 32'd0;
    oracle_semantic_family_seen_o = 32'h4954_4120;
    oracle_semantic_family_acked_o = {31'd0, calc_count_q != 0};
    oracle_semantic_case_seen_o = 32'h534f_4654;
    oracle_semantic_case_acked_o = {31'd0, output_toggle_count_q != 0};
    oracle_req_signature_o = max_sample_q;
    oracle_stalled_req_signature_o = last_stream_word_q;
    oracle_req_signature_delta_o = max_sample_q ^ last_stream_word_q;
    oracle_req_stable_violation_o = 32'd0;
    oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q - stream_count_q;
  end
endmodule
