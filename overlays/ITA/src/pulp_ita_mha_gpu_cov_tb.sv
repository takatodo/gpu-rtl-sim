module pulp_ita_mha_gpu_cov_tb
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
  logic [1:0] phase_q;
  logic [31:0] cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] signature_q;
  logic [31:0] inp_handshake_q;
  logic [31:0] weight_handshake_q;
  logic [31:0] bias_handshake_q;
  logic [31:0] output_handshake_q;
  logic [31:0] busy_count_q;
  logic [31:0] valid_count_q;
  logic [31:0] ready_backpressure_q;
  logic [31:0] last_output_word_q;
  logic [31:0] output_checksum_q;
  logic [31:0] accepted_mix_q;

  ctrl_t ctrl;
  inp_t inp;
  inp_weight_t inp_weight;
  bias_t inp_bias;
  requant_oup_t oup;
  logic inp_valid;
  logic inp_ready;
  logic weight_valid;
  logic weight_ready;
  logic bias_valid;
  logic bias_ready;
  logic valid;
  logic ready;
  logic busy;

  function automatic logic [31:0] xorshift32(input logic [31:0] value);
    logic [31:0] x;
    begin
      x = value ^ (value << 13);
      x = x ^ (x >> 17);
      xorshift32 = x ^ (x << 5);
    end
  endfunction

  initial begin
    clk_i = 1'b0;
    phase_q = ResetPhase;
    cycle_q = 32'd0;
    traffic_cycle_q = 32'd0;
    drain_cycle_q = 32'd0;
    signature_q = 32'h4954_414d;
    inp_handshake_q = 32'd0;
    weight_handshake_q = 32'd0;
    bias_handshake_q = 32'd0;
    output_handshake_q = 32'd0;
    busy_count_q = 32'd0;
    valid_count_q = 32'd0;
    ready_backpressure_q = 32'd0;
    last_output_word_q = 32'd0;
    output_checksum_q = 32'd0;
    accepted_mix_q = 32'd0;
  end

  always #5 clk_i = ~clk_i;
  assign rst_ni = !reset_like_w;

  always_comb begin
    ctrl = '0;
    ctrl.start = cfg_valid_i && (phase_q == TrafficPhase);
    ctrl.layer = Attention;
    ctrl.activation = Identity;
    ctrl.tile_s = 32'd16;
    ctrl.tile_e = 32'd16;
    ctrl.tile_p = 32'd16;
    ctrl.tile_f = 32'd16;
    ctrl.gelu_b = gelu_const_t'(16'sd0);
    ctrl.gelu_c = gelu_const_t'(16'sd0);
    ctrl.activation_requant_mult = requant_const_t'(8'd1);
    ctrl.activation_requant_shift = requant_const_t'(8'd0);
    ctrl.activation_requant_add = requant_t'(8'sd0);
    for (int idx = 0; idx < N_REQUANT_CONSTS; idx = idx + 1) begin
      ctrl.eps_mult[idx] = requant_const_t'(8'd1);
      ctrl.right_shift[idx] = requant_const_t'(8'd0);
      ctrl.add[idx] = requant_t'(8'sd0);
    end

    for (int idx = 0; idx < M; idx = idx + 1) begin
      inp[idx] = logic'(cfg_seed_i[idx % 32] ^ traffic_cycle_q[idx % 32]) ? WI'(8'sd3) : WI'(8'sd1);
    end
    for (int idx = 0; idx < (N * M / N_WRITE_EN); idx = idx + 1) begin
      inp_weight[idx] = logic'(cfg_req_data_hi_xor_i[idx % 32] ^ cycle_q[idx % 32]) ? WI'(8'sd2) : WI'(8'sd1);
    end
    for (int idx = 0; idx < N; idx = idx + 1) begin
      inp_bias[idx] = '0;
    end
  end

  assign inp_valid = cfg_valid_i && (phase_q == TrafficPhase);
  assign weight_valid = cfg_valid_i && (phase_q == TrafficPhase);
  assign bias_valid = cfg_valid_i && (phase_q == TrafficPhase);
  assign ready = 1'b1;

  ita i_ita (
    .clk_i              (clk_i),
    .rst_ni             (rst_ni),
    .ctrl_i             (ctrl),
    .inp_valid_i        (inp_valid),
    .inp_ready_o        (inp_ready),
    .inp_weight_valid_i (weight_valid),
    .inp_weight_ready_o (weight_ready),
    .inp_bias_valid_i   (bias_valid),
    .inp_bias_ready_o   (bias_ready),
    .valid_o            (valid),
    .ready_i            (ready),
    .busy_o             (busy),
    .inp_i              (inp),
    .inp_weight_i       (inp_weight),
    .inp_bias_i         (inp_bias),
    .oup_o              (oup)
  );

  always_ff @(posedge clk_i) begin
    if (reset_like_w) begin
      phase_q <= ResetPhase;
      cycle_q <= cycle_q + 32'd1;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      signature_q <= 32'h4954_414d;
      inp_handshake_q <= 32'd0;
      weight_handshake_q <= 32'd0;
      bias_handshake_q <= 32'd0;
      output_handshake_q <= 32'd0;
      busy_count_q <= 32'd0;
      valid_count_q <= 32'd0;
      ready_backpressure_q <= 32'd0;
      last_output_word_q <= 32'd0;
      output_checksum_q <= 32'd0;
      accepted_mix_q <= 32'd0;
    end else begin
      cycle_q <= cycle_q + 32'd1;
      if (phase_q == ResetPhase) begin
        if (cycle_q >= cfg_reset_cycles_i) begin
          phase_q <= TrafficPhase;
        end
      end else if (phase_q == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        if (inp_valid && inp_ready) begin
          inp_handshake_q <= inp_handshake_q + 32'd1;
        end
        if (weight_valid && weight_ready) begin
          weight_handshake_q <= weight_handshake_q + 32'd1;
        end
        if (bias_valid && bias_ready) begin
          bias_handshake_q <= bias_handshake_q + 32'd1;
        end
        if (busy) begin
          busy_count_q <= busy_count_q + 32'd1;
        end
        if (valid) begin
          valid_count_q <= valid_count_q + 32'd1;
        end
        if (valid && !ready) begin
          ready_backpressure_q <= ready_backpressure_q + 32'd1;
        end
        if (valid && ready) begin
          output_handshake_q <= output_handshake_q + 32'd1;
          last_output_word_q <= 32'(oup[0]);
          output_checksum_q <= xorshift32(output_checksum_q ^ 32'(oup[0]) ^ traffic_cycle_q);
        end
        accepted_mix_q <= xorshift32(
            accepted_mix_q ^ inp_handshake_q ^ (weight_handshake_q << 1) ^
            (bias_handshake_q << 2) ^ (output_handshake_q << 3) ^ {31'd0, busy});
        signature_q <= xorshift32(signature_q ^ accepted_mix_q ^ cycle_q);
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
    cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ 32'h4954_414d;
    host_req_accepted_o = inp_handshake_q;
    device_req_accepted_o = weight_handshake_q;
    device_rsp_accepted_o = output_handshake_q;
    host_rsp_accepted_o = valid_count_q;
    rsp_queue_overflow_o = 32'd0;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q;
    toggle_bitmap_word0_o = {
      26'd0,
      output_handshake_q != 0,
      valid_count_q != 0,
      busy_count_q != 0,
      bias_handshake_q != 0,
      weight_handshake_q != 0,
      inp_handshake_q != 0
    };
    toggle_bitmap_word1_o = accepted_mix_q;
    toggle_bitmap_word2_o = output_checksum_q ^ last_output_word_q;
    real_toggle_subset_word0_o = inp_handshake_q;
    real_toggle_subset_word1_o = weight_handshake_q;
    real_toggle_subset_word2_o = bias_handshake_q;
    real_toggle_subset_word3_o = output_handshake_q;
    real_toggle_subset_word4_o = busy_count_q;
    real_toggle_subset_word5_o = valid_count_q;
    real_toggle_subset_word6_o = ready_backpressure_q;
    real_toggle_subset_word7_o = traffic_cycle_q;
    real_toggle_subset_word8_o = signature_q;
    real_toggle_subset_word9_o = accepted_mix_q;
    real_toggle_subset_word10_o = output_checksum_q;
    real_toggle_subset_word11_o = last_output_word_q;
    real_toggle_subset_word12_o = {31'd0, busy};
    real_toggle_subset_word13_o = {31'd0, valid};
    real_toggle_subset_word14_o = 32'(oup[0]);
    real_toggle_subset_word15_o = 32'(oup[1]);
    real_toggle_subset_word16_o = {30'd0, phase_q};
    real_toggle_subset_word17_o = cfg_batch_length_i;
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = traffic_cycle_q;
    focused_wave_word2_o = drain_cycle_q;
    focused_wave_word3_o = {30'd0, phase_q};
    focused_wave_word4_o = inp_handshake_q;
    focused_wave_word5_o = weight_handshake_q;
    focused_wave_word6_o = output_handshake_q;
    focused_wave_word7_o = {29'd0, busy, valid, done_o};
    oracle_expected_ok_count_o = inp_handshake_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = output_handshake_q;
    oracle_observed_err_count_o = 32'd0;
    oracle_semantic_family_seen_o = 32'h4954_414d;
    oracle_semantic_family_acked_o = {31'd0, inp_handshake_q != 0};
    oracle_semantic_case_seen_o = 32'h4d48_4131;
    oracle_semantic_case_acked_o = {31'd0, output_handshake_q != 0};
    oracle_req_signature_o = accepted_mix_q;
    oracle_stalled_req_signature_o = output_checksum_q;
    oracle_req_signature_delta_o = accepted_mix_q ^ output_checksum_q;
    oracle_req_stable_violation_o = 32'd0;
    oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q - inp_handshake_q;
  end

endmodule
