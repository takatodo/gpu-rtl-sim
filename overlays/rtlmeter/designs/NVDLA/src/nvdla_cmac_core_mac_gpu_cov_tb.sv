// Minimal GPU-toggle-ready standalone coverage target for NVDLA
// NV_NVDLA_CMAC_CORE_mac. This is a scoped CMAC MAC datapath seed, not a full
// NVDLA accelerator, model harness, or complete arithmetic validator.

module nvdla_cmac_core_mac_gpu_cov_tb (
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
  logic nvdla_wg_clk;
  logic nvdla_core_rstn /* verilator public_flat */;

  logic cfg_is_fp16;
  logic cfg_is_int16;
  logic cfg_is_int8;
  logic cfg_is_wg;
  logic cfg_reg_en;
  logic [1023:0] dat_actv_data;
  logic [63:0] dat_actv_nan;
  logic [127:0] dat_actv_nz;
  logic [103:0] dat_actv_pvld;
  logic [191:0] dat_pre_exp;
  logic [63:0] dat_pre_mask;
  logic dat_pre_pvld;
  logic dat_pre_stripe_end;
  logic dat_pre_stripe_st;
  logic [1023:0] wt_actv_data;
  logic [63:0] wt_actv_nan;
  logic [127:0] wt_actv_nz;
  logic [103:0] wt_actv_pvld;
  logic [191:0] wt_sd_exp;
  logic [63:0] wt_sd_mask;
  logic wt_sd_pvld;
  logic [175:0] mac_out_data;
  logic mac_out_nan;
  logic mac_out_pvld;

  logic [1:0]  phase_q;
  logic [31:0] cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] valid_in_count_q;
  logic [31:0] valid_out_count_q;
  logic [31:0] nan_out_count_q;
  logic [31:0] data_toggle_count_q;
  logic [31:0] pvld_toggle_count_q;
  logic [31:0] signature_q;
  logic [31:0] last_out_low_q;
  logic        last_out_pvld_q;
  logic        last_out_nan_q;

  function automatic logic [31:0] xorshift32(input logic [31:0] value);
    logic [31:0] x;
    begin
      x = value ^ (value << 13);
      x = x ^ (x >> 17);
      xorshift32 = x ^ (x << 5);
    end
  endfunction

  function automatic logic [1023:0] make_wide(input logic [31:0] base, input logic [31:0] salt);
    logic [1023:0] result;
    logic [31:0] mixed;
    integer lane;
    begin
      for (lane = 0; lane < 32; lane = lane + 1) begin
        mixed = xorshift32(base ^ salt ^ (32'h9e3779b9 * lane[31:0]));
        result[lane * 32 +: 32] = mixed;
      end
      make_wide = result;
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
    nan_out_count_q = 32'd0;
    data_toggle_count_q = 32'd0;
    pvld_toggle_count_q = 32'd0;
    signature_q = 32'h636d6163;
    last_out_low_q = 32'd0;
    last_out_pvld_q = 1'b0;
    last_out_nan_q = 1'b0;
  end

  always #5 nvdla_core_clk = ~nvdla_core_clk;
  assign nvdla_wg_clk = nvdla_core_clk;

  NV_NVDLA_CMAC_CORE_mac dut (
    .nvdla_core_clk,
    .nvdla_wg_clk,
    .nvdla_core_rstn,
    .cfg_is_fp16,
    .cfg_is_int16,
    .cfg_is_int8,
    .cfg_is_wg,
    .cfg_reg_en,
    .dat_actv_data,
    .dat_actv_nan,
    .dat_actv_nz,
    .dat_actv_pvld,
    .dat_pre_exp,
    .dat_pre_mask,
    .dat_pre_pvld,
    .dat_pre_stripe_end,
    .dat_pre_stripe_st,
    .wt_actv_data,
    .wt_actv_nan,
    .wt_actv_nz,
    .wt_actv_pvld,
    .wt_sd_exp,
    .wt_sd_mask,
    .wt_sd_pvld,
    .mac_out_data,
    .mac_out_nan,
    .mac_out_pvld
  );

  always_comb begin
    cfg_is_fp16 = 1'b0;
    cfg_is_int16 = 1'b0;
    cfg_is_int8 = 1'b1;
    cfg_is_wg = cfg_req_family_i[0];
    cfg_reg_en = (phase_q != ResetPhase);
    dat_actv_data = make_wide(rand_q ^ cfg_seed_i, 32'hda7a_ac7a);
    wt_actv_data = make_wide(rand_q ^ cfg_req_data_hi_xor_i, 32'hc0a1_5eed);
    dat_actv_nan = 64'd0;
    wt_actv_nan = 64'd0;
    dat_actv_nz = (phase_q == TrafficPhase) ? {128{1'b1}} : 128'd0;
    wt_actv_nz = (phase_q == TrafficPhase) ? {128{1'b1}} : 128'd0;
    dat_actv_pvld = (phase_q == TrafficPhase && cfg_valid_i) ? {104{1'b1}} : 104'd0;
    wt_actv_pvld = (phase_q == TrafficPhase && cfg_valid_i) ? {104{1'b1}} : 104'd0;
    dat_pre_exp = {6{rand_q ^ 32'h1357_9bdf}};
    wt_sd_exp = {6{rand_q ^ 32'h2468_ace0}};
    dat_pre_mask = (phase_q == TrafficPhase) ? 64'hffff_ffff_ffff_ffff : 64'd0;
    wt_sd_mask = (phase_q == TrafficPhase) ? 64'hffff_ffff_ffff_ffff : 64'd0;
    dat_pre_pvld = (phase_q == TrafficPhase) && cfg_valid_i;
    wt_sd_pvld = (phase_q == TrafficPhase) && cfg_valid_i;
    dat_pre_stripe_st = (traffic_cycle_q == 32'd0);
    dat_pre_stripe_end = (traffic_cycle_q >= cfg_batch_length_i);
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
      nan_out_count_q <= 32'd0;
      data_toggle_count_q <= 32'd0;
      pvld_toggle_count_q <= 32'd0;
      signature_q <= 32'h636d6163;
      last_out_low_q <= 32'd0;
      last_out_pvld_q <= 1'b0;
      last_out_nan_q <= 1'b0;
    end else begin
      rand_q <= xorshift32(rand_q ^ cfg_seed_i ^ cycle_q);
      cycle_q <= cycle_q + 32'd1;

      if (phase_q == ResetPhase) begin
        traffic_cycle_q <= 32'd0;
        drain_cycle_q <= 32'd0;
        if (cycle_q >= cfg_reset_cycles_i) begin
          phase_q <= TrafficPhase;
        end
      end else if (phase_q == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        if (cfg_valid_i) begin
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

      if (mac_out_pvld) begin
        valid_out_count_q <= valid_out_count_q + 32'd1;
        signature_q <= signature_q ^ mac_out_data[31:0] ^ mac_out_data[63:32] ^
                       {30'd0, mac_out_nan, mac_out_pvld};
        if (last_out_pvld_q && (last_out_low_q != mac_out_data[31:0])) begin
          data_toggle_count_q <= data_toggle_count_q + 32'd1;
        end
      end
      if (mac_out_nan) begin
        nan_out_count_q <= nan_out_count_q + 32'd1;
      end
      if (last_out_pvld_q != mac_out_pvld || last_out_nan_q != mac_out_nan) begin
        pvld_toggle_count_q <= pvld_toggle_count_q + 32'd1;
      end
      if (mac_out_pvld) begin
        last_out_low_q <= mac_out_data[31:0];
      end
      last_out_pvld_q <= mac_out_pvld;
      last_out_nan_q <= mac_out_nan;
    end
  end

  always_comb begin
    nvdla_core_rstn = (cycle_q >= cfg_reset_cycles_i);
    done_o = (phase_q == DonePhase);
    cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_drain_cycles_i ^ 32'hc0de_c0ac;
    host_req_accepted_o = valid_in_count_q;
    device_req_accepted_o = valid_in_count_q;
    device_rsp_accepted_o = valid_out_count_q;
    host_rsp_accepted_o = valid_out_count_q;
    rsp_queue_overflow_o = 32'd0;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q;
    toggle_bitmap_word0_o = {29'd0, mac_out_nan, mac_out_pvld, data_toggle_count_q != 0};
    toggle_bitmap_word1_o = mac_out_pvld ? mac_out_data[31:0] : 32'd0;
    toggle_bitmap_word2_o = {30'd0, cfg_is_wg, cfg_is_int8};
    real_toggle_subset_word0_o = valid_in_count_q;
    real_toggle_subset_word1_o = valid_out_count_q;
    real_toggle_subset_word2_o = nan_out_count_q;
    real_toggle_subset_word3_o = data_toggle_count_q;
    real_toggle_subset_word4_o = pvld_toggle_count_q;
    real_toggle_subset_word5_o = signature_q;
    real_toggle_subset_word6_o = mac_out_pvld ? mac_out_data[31:0] : 32'd0;
    real_toggle_subset_word7_o = mac_out_pvld ? mac_out_data[63:32] : 32'd0;
    real_toggle_subset_word8_o = mac_out_pvld ? mac_out_data[95:64] : 32'd0;
    real_toggle_subset_word9_o = mac_out_pvld ? mac_out_data[127:96] : 32'd0;
    real_toggle_subset_word10_o = mac_out_pvld ? mac_out_data[159:128] : 32'd0;
    real_toggle_subset_word11_o = mac_out_pvld ? {16'd0, mac_out_data[175:160]} : 32'd0;
    real_toggle_subset_word12_o = {31'd0, mac_out_pvld};
    real_toggle_subset_word13_o = {31'd0, mac_out_nan};
    real_toggle_subset_word14_o = dat_actv_data[31:0];
    real_toggle_subset_word15_o = wt_actv_data[31:0];
    real_toggle_subset_word16_o = {30'd0, cfg_is_wg, cfg_is_int8};
    real_toggle_subset_word17_o = {30'd0, phase_q};
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = traffic_cycle_q;
    focused_wave_word2_o = drain_cycle_q;
    focused_wave_word3_o = {30'd0, phase_q};
    focused_wave_word4_o = last_out_low_q;
    focused_wave_word5_o = signature_q;
    focused_wave_word6_o = rand_q;
    focused_wave_word7_o = {30'd0, mac_out_nan, mac_out_pvld};
    oracle_expected_ok_count_o = valid_in_count_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = valid_out_count_q;
    oracle_observed_err_count_o = 32'd0;
    oracle_semantic_family_seen_o = 32'h4e56444c;
    oracle_semantic_family_acked_o = {31'd0, valid_out_count_q != 0};
    oracle_semantic_case_seen_o = 32'h434d4143;
    oracle_semantic_case_acked_o = {31'd0, mac_out_pvld};
    oracle_req_signature_o = dat_actv_data[31:0];
    oracle_stalled_req_signature_o = wt_actv_data[31:0];
    oracle_req_signature_delta_o = dat_actv_data[31:0] ^ wt_actv_data[31:0];
    oracle_req_stable_violation_o = 32'd0;
    oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q - valid_out_count_q;
  end
endmodule
