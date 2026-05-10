// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_pulse_sync.

module prim_pulse_sync_gpu_cov_tb (
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

  logic clk_src_i;
  logic clk_dst_i;
  logic rst_src_ni;
  logic rst_dst_ni;
  logic src_pulse_i;
  logic dst_pulse_o;
  logic [1:0] phase_src_w;
  logic [1:0] phase_dst_w;
  logic pulse_fire_w;

  logic [31:0] global_src_cycle_q;
  logic [31:0] global_dst_cycle_q;
  logic [31:0] traffic_src_cycle_q;
  logic [31:0] traffic_dst_cycle_q;
  logic [31:0] drain_src_cycle_q;
  logic [31:0] drain_dst_cycle_q;
  logic [31:0] rand_src_q;
  logic [31:0] rand_dst_q;
  logic [31:0] src_pulse_count_q;
  logic [31:0] src_idle_count_q;
  logic [31:0] src_cooldown_count_q;
  logic [31:0] dst_pulse_count_q;
  logic [31:0] dst_idle_count_q;
  logic [31:0] dst_gap_count_q;
  logic [31:0] src_signature_q;
  logic [31:0] dst_signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] reset_skew_count_q;
  logic [31:0] src_seen_q;
  logic [31:0] dst_seen_q;
  logic [31:0] pre_pulse_traffic_cycles_q;
  logic [7:0] cooldown_q;
  logic last_dst_pulse_q;
  logic spacing_violation_q;

  initial begin
    clk_src_i = 1'b0;
    clk_dst_i = 1'b0;
  end

  always #5 clk_src_i = ~clk_src_i;
  always #7 clk_dst_i = ~clk_dst_i;

  prim_pulse_sync dut (
    .clk_src_i,
    .rst_src_ni,
    .src_pulse_i,
    .clk_dst_i,
    .rst_dst_ni,
    .dst_pulse_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1103515245 + 32'd12345;
  endfunction

  function automatic logic [31:0] clamp_pct(input logic [31:0] pct_raw);
    return (pct_raw > 32'd100) ? 32'd100 : pct_raw;
  endfunction

  function automatic logic pct_hit(input logic [31:0] state, input logic [31:0] pct_raw);
    return ((state % 32'd100) < clamp_pct(pct_raw));
  endfunction

  function automatic logic [7:0] cooldown_cycles(input logic [31:0] raw);
    logic [7:0] bounded;
    bounded = raw[7:0];
    if (bounded < 8'd5) begin
      return 8'd5;
    end
    if (bounded > 8'd31) begin
      return 8'd31;
    end
    return bounded;
  endfunction

  assign rst_src_ni = cfg_valid_i && (global_src_cycle_q >= cfg_reset_cycles_i);
  assign rst_dst_ni = cfg_valid_i && (global_dst_cycle_q >= (cfg_reset_cycles_i + 32'd1));

  always_comb begin
    if (!cfg_valid_i || !rst_src_ni) begin
      phase_src_w = ResetPhase;
    end else if (traffic_src_cycle_q < cfg_batch_length_i) begin
      phase_src_w = TrafficPhase;
    end else if (drain_src_cycle_q < cfg_drain_cycles_i) begin
      phase_src_w = DrainPhase;
    end else begin
      phase_src_w = DonePhase;
    end
  end

  always_comb begin
    if (!cfg_valid_i || !rst_dst_ni) begin
      phase_dst_w = ResetPhase;
    end else if (traffic_dst_cycle_q < cfg_batch_length_i) begin
      phase_dst_w = TrafficPhase;
    end else if (drain_dst_cycle_q < cfg_drain_cycles_i) begin
      phase_dst_w = DrainPhase;
    end else begin
      phase_dst_w = DonePhase;
    end
  end

  assign pulse_fire_w = cfg_valid_i &&
                        rst_src_ni &&
                        phase_src_w == TrafficPhase &&
                        cooldown_q == 8'd0 &&
                        pct_hit(rand_src_q ^ cfg_seed_i ^ cfg_req_family_i,
                                cfg_req_valid_pct_i);
  assign src_pulse_i = pulse_fire_w;

  always_ff @(posedge clk_src_i) begin
    if (!cfg_valid_i) begin
      global_src_cycle_q <= 32'd0;
    end else if (phase_src_w != DonePhase) begin
      global_src_cycle_q <= global_src_cycle_q + 32'd1;
    end

    if (!rst_src_ni) begin
      traffic_src_cycle_q <= 32'd0;
      drain_src_cycle_q <= 32'd0;
      rand_src_q <= cfg_seed_i ^ 32'h1357_2468;
      src_pulse_count_q <= 32'd0;
      src_idle_count_q <= 32'd0;
      src_cooldown_count_q <= 32'd0;
      src_signature_q <= cfg_seed_i ^ 32'h1020_3040;
      stalled_signature_q <= 32'd0;
      reset_skew_count_q <= 32'd0;
      src_seen_q <= 32'd0;
      pre_pulse_traffic_cycles_q <= 32'd0;
      cooldown_q <= 8'd0;
      spacing_violation_q <= 1'b0;
    end else if (phase_src_w != DonePhase) begin
      rand_src_q <= prng_next(rand_src_q ^ global_src_cycle_q ^ cfg_req_data_hi_xor_i);
      if (phase_src_w == TrafficPhase) begin
        traffic_src_cycle_q <= traffic_src_cycle_q + 32'd1;
      end else if (phase_src_w == DrainPhase) begin
        drain_src_cycle_q <= drain_src_cycle_q + 32'd1;
      end
      if (rst_src_ni && !rst_dst_ni) begin
        reset_skew_count_q <= reset_skew_count_q + 32'd1;
      end
      if (phase_src_w == TrafficPhase && !pulse_fire_w) begin
        src_idle_count_q <= src_idle_count_q + 32'd1;
        if (src_pulse_count_q == 32'd0) begin
          pre_pulse_traffic_cycles_q <= pre_pulse_traffic_cycles_q + 32'd1;
        end
        src_seen_q[2] <= 1'b1;
      end
      if (cooldown_q != 8'd0) begin
        cooldown_q <= cooldown_q - 8'd1;
        src_cooldown_count_q <= src_cooldown_count_q + 32'd1;
        src_seen_q[1] <= 1'b1;
      end
      if (pulse_fire_w) begin
        if (cooldown_q != 8'd0) begin
          spacing_violation_q <= 1'b1;
        end
        cooldown_q <= cooldown_cycles(cfg_req_burst_len_max_i + cfg_rsp_delay_max_i);
        src_pulse_count_q <= src_pulse_count_q + 32'd1;
        src_signature_q <= {src_signature_q[30:0], src_signature_q[31]} ^
                           rand_src_q ^ src_pulse_count_q ^ cfg_req_data_mode_i;
        src_seen_q[0] <= 1'b1;
      end
      if (rst_src_ni && rst_dst_ni) begin
        src_seen_q[3] <= 1'b1;
      end
      if (phase_src_w == DrainPhase) begin
        stalled_signature_q <= stalled_signature_q ^ src_signature_q ^ drain_src_cycle_q;
      end
    end
  end

  always_ff @(posedge clk_dst_i) begin
    if (!cfg_valid_i) begin
      global_dst_cycle_q <= 32'd0;
    end else if (phase_dst_w != DonePhase) begin
      global_dst_cycle_q <= global_dst_cycle_q + 32'd1;
    end

    if (!rst_dst_ni) begin
      traffic_dst_cycle_q <= 32'd0;
      drain_dst_cycle_q <= 32'd0;
      rand_dst_q <= cfg_seed_i ^ 32'h2468_1357;
      dst_pulse_count_q <= 32'd0;
      dst_idle_count_q <= 32'd0;
      dst_gap_count_q <= 32'd0;
      dst_signature_q <= cfg_seed_i ^ 32'h5060_7080;
      dst_seen_q <= 32'd0;
      last_dst_pulse_q <= 1'b0;
    end else if (phase_dst_w != DonePhase) begin
      rand_dst_q <= prng_next(rand_dst_q ^ global_dst_cycle_q ^ cfg_rsp_data_hi_xor_i);
      if (phase_dst_w == TrafficPhase) begin
        traffic_dst_cycle_q <= traffic_dst_cycle_q + 32'd1;
      end else if (phase_dst_w == DrainPhase) begin
        drain_dst_cycle_q <= drain_dst_cycle_q + 32'd1;
      end
      if (dst_pulse_o) begin
        dst_pulse_count_q <= dst_pulse_count_q + 32'd1;
        dst_signature_q <= {dst_signature_q[28:0], dst_signature_q[31:29]} ^
                           rand_dst_q ^ dst_pulse_count_q ^ cfg_rsp_data_mode_i;
        dst_seen_q[0] <= 1'b1;
      end else begin
        dst_idle_count_q <= dst_idle_count_q + 32'd1;
        dst_seen_q[2] <= 1'b1;
      end
      if (dst_pulse_o && !last_dst_pulse_q) begin
        dst_seen_q[1] <= 1'b1;
      end
      if (!dst_pulse_o && last_dst_pulse_q) begin
        dst_seen_q[3] <= 1'b1;
      end
      if (phase_dst_w == DrainPhase && !dst_pulse_o) begin
        dst_gap_count_q <= dst_gap_count_q + 32'd1;
      end
      last_dst_pulse_q <= dst_pulse_o;
    end
  end

  assign done_o = cfg_valid_i && phase_src_w == DonePhase && phase_dst_w == DonePhase;
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_req_valid_pct_i ^
                           cfg_reset_cycles_i ^ cfg_drain_cycles_i;
  assign host_req_accepted_o = src_pulse_count_q;
  assign device_req_accepted_o = dst_pulse_count_q;
  assign device_rsp_accepted_o = dst_idle_count_q;
  assign host_rsp_accepted_o = src_idle_count_q;
  assign rsp_queue_overflow_o = (src_pulse_count_q > dst_pulse_count_q) ?
                                (src_pulse_count_q - dst_pulse_count_q) : 32'd0;
  assign progress_cycle_count_o = traffic_src_cycle_q + traffic_dst_cycle_q +
                                  drain_src_cycle_q + drain_dst_cycle_q;
  assign progress_signature_o = src_signature_q ^ dst_signature_q ^
                                {27'd0, phase_src_w, phase_dst_w, done_o};

  assign toggle_bitmap_word0_o = src_seen_q | (dst_seen_q << 8);
  assign toggle_bitmap_word1_o = {
    21'd0,
    done_o,
    rst_dst_ni,
    rst_src_ni,
    dst_pulse_o,
    src_pulse_i,
    cooldown_q != 8'd0,
    last_dst_pulse_q,
    phase_src_w == TrafficPhase,
    phase_dst_w == TrafficPhase,
    spacing_violation_q,
    cfg_valid_i
  };
  assign toggle_bitmap_word2_o = {
    8'd0,
    phase_src_w,
    phase_dst_w,
    14'd0,
    src_pulse_count_q != 32'd0,
    dst_pulse_count_q != 32'd0,
    src_cooldown_count_q != 32'd0,
    dst_gap_count_q != 32'd0,
    pre_pulse_traffic_cycles_q != 32'd0,
    reset_skew_count_q != 32'd0
  };

  assign real_toggle_subset_word0_o = src_pulse_count_q;
  assign real_toggle_subset_word1_o = src_idle_count_q;
  assign real_toggle_subset_word2_o = src_cooldown_count_q;
  assign real_toggle_subset_word3_o = dst_pulse_count_q;
  assign real_toggle_subset_word4_o = dst_idle_count_q;
  assign real_toggle_subset_word5_o = dst_gap_count_q;
  assign real_toggle_subset_word6_o = src_signature_q;
  assign real_toggle_subset_word7_o = dst_signature_q;
  assign real_toggle_subset_word8_o = {31'd0, src_pulse_i};
  assign real_toggle_subset_word9_o = {31'd0, dst_pulse_o};
  assign real_toggle_subset_word10_o = {
    24'd0,
    src_pulse_i,
    dst_pulse_o,
    cooldown_q != 8'd0,
    last_dst_pulse_q,
    rst_src_ni,
    rst_dst_ni,
    done_o,
    spacing_violation_q
  };
  assign real_toggle_subset_word11_o = toggle_bitmap_word1_o;
  assign real_toggle_subset_word12_o = {31'd0, dst_pulse_o && !last_dst_pulse_q};
  assign real_toggle_subset_word13_o = global_src_cycle_q;
  assign real_toggle_subset_word14_o = global_dst_cycle_q;
  assign real_toggle_subset_word15_o = reset_skew_count_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = progress_signature_o;

  assign focused_wave_word0_o = {16'd0, global_src_cycle_q[7:0], global_dst_cycle_q[7:0]};
  assign focused_wave_word1_o = {12'd0, phase_src_w, phase_dst_w, toggle_bitmap_word1_o[15:0]};
  assign focused_wave_word2_o = src_pulse_count_q;
  assign focused_wave_word3_o = dst_pulse_count_q;
  assign focused_wave_word4_o = src_signature_q;
  assign focused_wave_word5_o = dst_signature_q;
  assign focused_wave_word6_o = stalled_signature_q;
  assign focused_wave_word7_o = {src_pulse_count_q[15:0], dst_pulse_count_q[15:0]};

  assign oracle_expected_ok_count_o = src_pulse_count_q;
  assign oracle_expected_err_count_o = rsp_queue_overflow_o;
  assign oracle_observed_ok_count_o = dst_pulse_count_q;
  assign oracle_observed_err_count_o = dst_gap_count_q;
  assign oracle_semantic_family_seen_o = cfg_req_family_i ^ cfg_rsp_family_i;
  assign oracle_semantic_family_acked_o = {src_pulse_count_q[15:0], dst_pulse_count_q[15:0]};
  assign oracle_semantic_case_seen_o = cfg_req_data_mode_i ^ cfg_rsp_data_mode_i;
  assign oracle_semantic_case_acked_o = {dst_gap_count_q[15:0], src_cooldown_count_q[15:0]};
  assign oracle_req_signature_o = src_signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = src_signature_q ^ dst_signature_q;
  assign oracle_req_stable_violation_o = {31'd0, spacing_violation_q};
  assign oracle_pre_handshake_traffic_cycles_o = pre_pulse_traffic_cycles_q;

endmodule
