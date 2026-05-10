// Minimal GPU-toggle-ready standalone coverage target for NVDLA
// NV_NVDLA_RT_cmac_a2cacc. This is a scoped CMAC-to-CACC routing seed, not a
// full NVDLA accelerator or neural-network model harness.

module nvdla_cmac_a2cacc_gpu_cov_tb (
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

  logic nvdla_core_clk;
  logic nvdla_core_rstn;

  logic        mac2accu_src_pvld;
  logic [7:0]  mac2accu_src_mask;
  logic [7:0]  mac2accu_src_mode;
  logic [175:0] mac2accu_src_data0;
  logic [175:0] mac2accu_src_data1;
  logic [175:0] mac2accu_src_data2;
  logic [175:0] mac2accu_src_data3;
  logic [175:0] mac2accu_src_data4;
  logic [175:0] mac2accu_src_data5;
  logic [175:0] mac2accu_src_data6;
  logic [175:0] mac2accu_src_data7;
  logic [8:0]  mac2accu_src_pd;
  logic        mac2accu_dst_pvld;
  logic [7:0]  mac2accu_dst_mask;
  logic [7:0]  mac2accu_dst_mode;
  logic [175:0] mac2accu_dst_data0;
  logic [175:0] mac2accu_dst_data1;
  logic [175:0] mac2accu_dst_data2;
  logic [175:0] mac2accu_dst_data3;
  logic [175:0] mac2accu_dst_data4;
  logic [175:0] mac2accu_dst_data5;
  logic [175:0] mac2accu_dst_data6;
  logic [175:0] mac2accu_dst_data7;
  logic [8:0]  mac2accu_dst_pd;

  logic [1:0]  phase_q;
  logic [31:0] cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] valid_in_count_q;
  logic [31:0] valid_out_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] data_toggle_count_q;
  logic [31:0] mask_toggle_count_q;
  logic [31:0] mode_toggle_count_q;
  logic [31:0] signature_q;
  logic [31:0] last_dst_low_q;
  logic [7:0]  last_dst_mask_q;
  logic [7:0]  last_dst_mode_q;
  logic        last_dst_pvld_q;
  logic [31:0] expected_low_pipe_q [0:2];
  logic [7:0]  expected_mask_pipe_q [0:2];
  logic [7:0]  expected_mode_pipe_q [0:2];
  logic        expected_valid_pipe_q [0:2];

  function automatic logic [31:0] xorshift32(input logic [31:0] value);
    logic [31:0] x;
    begin
      x = value ^ (value << 13);
      x = x ^ (x >> 17);
      xorshift32 = x ^ (x << 5);
    end
  endfunction

  function automatic logic [175:0] make_payload(input logic [31:0] base, input logic [3:0] lane);
    logic [31:0] mixed;
    begin
      mixed = base ^ {24'h0, lane, lane};
      make_payload = {mixed, mixed ^ 32'h9e3779b9, mixed + 32'h13579bdf,
                      mixed ^ 32'h2468ace0, mixed + 32'h10203040, mixed[15:0]};
    end
  endfunction

  initial begin
    nvdla_core_clk = 1'b0;
    phase_q = ResetPhase;
    cycle_q = 32'd0;
    traffic_cycle_q = 32'd0;
    drain_cycle_q = 32'd0;
    rand_q = 32'h1;
    valid_in_count_q = 32'd0;
    valid_out_count_q = 32'd0;
    mismatch_count_q = 32'd0;
    data_toggle_count_q = 32'd0;
    mask_toggle_count_q = 32'd0;
    mode_toggle_count_q = 32'd0;
    signature_q = 32'h6e76646c;
    last_dst_low_q = 32'd0;
    last_dst_mask_q = 8'd0;
    last_dst_mode_q = 8'd0;
    last_dst_pvld_q = 1'b0;
    expected_low_pipe_q[0] = 32'd0;
    expected_low_pipe_q[1] = 32'd0;
    expected_low_pipe_q[2] = 32'd0;
    expected_mask_pipe_q[0] = 8'd0;
    expected_mask_pipe_q[1] = 8'd0;
    expected_mask_pipe_q[2] = 8'd0;
    expected_mode_pipe_q[0] = 8'd0;
    expected_mode_pipe_q[1] = 8'd0;
    expected_mode_pipe_q[2] = 8'd0;
    expected_valid_pipe_q[0] = 1'b0;
    expected_valid_pipe_q[1] = 1'b0;
    expected_valid_pipe_q[2] = 1'b0;
  end

  always #5 nvdla_core_clk = ~nvdla_core_clk;

  NV_NVDLA_RT_cmac_a2cacc dut (
    .nvdla_core_clk,
    .nvdla_core_rstn,
    .mac2accu_src_pvld,
    .mac2accu_src_mask,
    .mac2accu_src_mode,
    .mac2accu_src_data0,
    .mac2accu_src_data1,
    .mac2accu_src_data2,
    .mac2accu_src_data3,
    .mac2accu_src_data4,
    .mac2accu_src_data5,
    .mac2accu_src_data6,
    .mac2accu_src_data7,
    .mac2accu_src_pd,
    .mac2accu_dst_pvld,
    .mac2accu_dst_mask,
    .mac2accu_dst_mode,
    .mac2accu_dst_data0,
    .mac2accu_dst_data1,
    .mac2accu_dst_data2,
    .mac2accu_dst_data3,
    .mac2accu_dst_data4,
    .mac2accu_dst_data5,
    .mac2accu_dst_data6,
    .mac2accu_dst_data7,
    .mac2accu_dst_pd
  );

  always_comb begin
    mac2accu_src_pvld = (phase_q == TrafficPhase) && cfg_valid_i;
    mac2accu_src_mask = 8'hff;
    mac2accu_src_mode = 8'hff;
    mac2accu_src_pd = rand_q[8:0] ^ 9'h12a;
    mac2accu_src_data0 = make_payload(rand_q ^ 32'h00000000, 4'd0);
    mac2accu_src_data1 = make_payload(rand_q ^ 32'h11111111, 4'd1);
    mac2accu_src_data2 = make_payload(rand_q ^ 32'h22222222, 4'd2);
    mac2accu_src_data3 = make_payload(rand_q ^ 32'h33333333, 4'd3);
    mac2accu_src_data4 = make_payload(rand_q ^ 32'h44444444, 4'd4);
    mac2accu_src_data5 = make_payload(rand_q ^ 32'h55555555, 4'd5);
    mac2accu_src_data6 = make_payload(rand_q ^ 32'h66666666, 4'd6);
    mac2accu_src_data7 = make_payload(rand_q ^ 32'h77777777, 4'd7);
  end

  always_ff @(posedge nvdla_core_clk) begin
    if (!nvdla_core_rstn) begin
      phase_q <= ResetPhase;
      cycle_q <= cycle_q + 32'd1;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= 32'h1;
      valid_in_count_q <= 32'd0;
      valid_out_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      data_toggle_count_q <= 32'd0;
      mask_toggle_count_q <= 32'd0;
      mode_toggle_count_q <= 32'd0;
      signature_q <= 32'h6e76646c;
      last_dst_low_q <= 32'd0;
      last_dst_mask_q <= 8'd0;
      last_dst_mode_q <= 8'd0;
      last_dst_pvld_q <= 1'b0;
      expected_low_pipe_q[0] <= 32'd0;
      expected_low_pipe_q[1] <= 32'd0;
      expected_low_pipe_q[2] <= 32'd0;
      expected_mask_pipe_q[0] <= 8'd0;
      expected_mask_pipe_q[1] <= 8'd0;
      expected_mask_pipe_q[2] <= 8'd0;
      expected_mode_pipe_q[0] <= 8'd0;
      expected_mode_pipe_q[1] <= 8'd0;
      expected_mode_pipe_q[2] <= 8'd0;
      expected_valid_pipe_q[0] <= 1'b0;
      expected_valid_pipe_q[1] <= 1'b0;
      expected_valid_pipe_q[2] <= 1'b0;
    end else begin
      rand_q <= xorshift32(rand_q ^ cfg_seed_i ^ cycle_q);
      cycle_q <= cycle_q + 32'd1;
      expected_low_pipe_q[0] <= mac2accu_src_data0[31:0];
      expected_low_pipe_q[1] <= expected_low_pipe_q[0];
      expected_low_pipe_q[2] <= expected_low_pipe_q[1];
      expected_mask_pipe_q[0] <= mac2accu_src_mask;
      expected_mask_pipe_q[1] <= expected_mask_pipe_q[0];
      expected_mask_pipe_q[2] <= expected_mask_pipe_q[1];
      expected_mode_pipe_q[0] <= mac2accu_src_mode;
      expected_mode_pipe_q[1] <= expected_mode_pipe_q[0];
      expected_mode_pipe_q[2] <= expected_mode_pipe_q[1];
      expected_valid_pipe_q[0] <= mac2accu_src_pvld;
      expected_valid_pipe_q[1] <= expected_valid_pipe_q[0];
      expected_valid_pipe_q[2] <= expected_valid_pipe_q[1];

      if (phase_q == ResetPhase) begin
        traffic_cycle_q <= 32'd0;
        drain_cycle_q <= 32'd0;
        if (cycle_q >= cfg_reset_cycles_i) begin
          phase_q <= TrafficPhase;
        end
      end else if (phase_q == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        if (mac2accu_src_pvld) begin
          valid_in_count_q <= valid_in_count_q + 32'd1;
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

      if (mac2accu_dst_pvld) begin
        valid_out_count_q <= valid_out_count_q + 32'd1;
        signature_q <= signature_q ^ mac2accu_dst_data0[31:0] ^ {16'h0, mac2accu_dst_mask, mac2accu_dst_mode};
        if (mac2accu_dst_data0[31:0] != expected_low_pipe_q[1] ||
            mac2accu_dst_mask != expected_mask_pipe_q[1] ||
            mac2accu_dst_mode != expected_mode_pipe_q[1] ||
            expected_valid_pipe_q[1] != 1'b1) begin
          mismatch_count_q <= mismatch_count_q + 32'd1;
        end
      end
      if (last_dst_pvld_q && mac2accu_dst_pvld && (last_dst_low_q != mac2accu_dst_data0[31:0])) begin
        data_toggle_count_q <= data_toggle_count_q + 32'd1;
      end
      if (last_dst_mask_q != mac2accu_dst_mask) begin
        mask_toggle_count_q <= mask_toggle_count_q + 32'd1;
      end
      if (last_dst_mode_q != mac2accu_dst_mode) begin
        mode_toggle_count_q <= mode_toggle_count_q + 32'd1;
      end
      last_dst_low_q <= mac2accu_dst_data0[31:0];
      last_dst_mask_q <= mac2accu_dst_mask;
      last_dst_mode_q <= mac2accu_dst_mode;
      last_dst_pvld_q <= mac2accu_dst_pvld;
    end
  end

  always_comb begin
    nvdla_core_rstn = (cycle_q >= cfg_reset_cycles_i);
    done_o = (phase_q == DonePhase);
    cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_drain_cycles_i ^ 32'hcacc_a2c;
    host_req_accepted_o = valid_in_count_q;
    device_req_accepted_o = valid_in_count_q;
    device_rsp_accepted_o = valid_out_count_q;
    host_rsp_accepted_o = valid_out_count_q;
    rsp_queue_overflow_o = mismatch_count_q;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q;
    toggle_bitmap_word0_o = {29'd0, mode_toggle_count_q != 0, mask_toggle_count_q != 0, data_toggle_count_q != 0};
    toggle_bitmap_word1_o = {24'd0, mac2accu_dst_mask};
    toggle_bitmap_word2_o = {24'd0, mac2accu_dst_mode};
    real_toggle_subset_word0_o = valid_in_count_q;
    real_toggle_subset_word1_o = valid_out_count_q;
    real_toggle_subset_word2_o = mismatch_count_q;
    real_toggle_subset_word3_o = data_toggle_count_q;
    real_toggle_subset_word4_o = mask_toggle_count_q;
    real_toggle_subset_word5_o = mode_toggle_count_q;
    real_toggle_subset_word6_o = mac2accu_dst_data0[31:0];
    real_toggle_subset_word7_o = mac2accu_dst_data1[31:0];
    real_toggle_subset_word8_o = mac2accu_dst_data2[31:0];
    real_toggle_subset_word9_o = mac2accu_dst_data3[31:0];
    real_toggle_subset_word10_o = mac2accu_dst_data4[31:0];
    real_toggle_subset_word11_o = mac2accu_dst_data5[31:0];
    real_toggle_subset_word12_o = mac2accu_dst_data6[31:0];
    real_toggle_subset_word13_o = mac2accu_dst_data7[31:0];
    real_toggle_subset_word14_o = {23'd0, mac2accu_dst_pd};
    real_toggle_subset_word15_o = {24'd0, mac2accu_dst_mask};
    real_toggle_subset_word16_o = {24'd0, mac2accu_dst_mode};
    real_toggle_subset_word17_o = {31'd0, mac2accu_dst_pvld};
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = traffic_cycle_q;
    focused_wave_word2_o = drain_cycle_q;
    focused_wave_word3_o = {30'd0, phase_q};
    focused_wave_word4_o = expected_low_pipe_q[1];
    focused_wave_word5_o = last_dst_low_q;
    focused_wave_word6_o = signature_q;
    focused_wave_word7_o = rand_q;
    oracle_expected_ok_count_o = valid_in_count_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = valid_out_count_q - mismatch_count_q;
    oracle_observed_err_count_o = mismatch_count_q;
    oracle_semantic_family_seen_o = 32'h4e56444c;
    oracle_semantic_family_acked_o = {31'd0, valid_out_count_q != 0};
    oracle_semantic_case_seen_o = 32'h43414343;
    oracle_semantic_case_acked_o = {31'd0, mismatch_count_q == 0};
    oracle_req_signature_o = expected_low_pipe_q[1];
    oracle_stalled_req_signature_o = last_dst_low_q;
    oracle_req_signature_delta_o = expected_low_pipe_q[1] ^ last_dst_low_q;
    oracle_req_stable_violation_o = mismatch_count_q;
    oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q - valid_out_count_q;
  end
endmodule
