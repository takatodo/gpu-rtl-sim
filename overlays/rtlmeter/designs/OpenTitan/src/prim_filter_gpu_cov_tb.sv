// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_filter.

module prim_filter_gpu_cov_tb (
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
  localparam int unsigned Cycles = 4;
  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic rst_ni;
  logic enable_i;
  logic filter_i;
  logic filter_o;
  logic [1:0] phase_w;
  logic [31:0] case_mix_w;
  logic [2:0] case_w;
  logic next_enable_w;
  logic next_filter_w;
  logic [Cycles-1:0] model_stored_vector_d_w;
  logic model_update_w;
  logic expected_filter_o_w;
  logic observed_match_w;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] enable_count_q;
  logic [31:0] bypass_count_q;
  logic [31:0] input_high_count_q;
  logic [31:0] input_low_count_q;
  logic [31:0] output_high_count_q;
  logic [31:0] output_low_count_q;
  logic [31:0] output_change_count_q;
  logic [31:0] model_match_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] stable_one_update_count_q;
  logic [31:0] stable_zero_update_count_q;
  logic [31:0] enable_change_count_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [31:0] pre_update_cycles_q;
  logic [Cycles-1:0] model_stored_vector_q;
  logic model_stored_value_q;
  logic last_enable_q;
  logic last_filter_o_q;

  initial begin
    clk_i = 1'b0;
  end

  always #5 clk_i = ~clk_i;

  prim_filter #(
    .AsyncOn(1'b0),
    .Cycles(Cycles)
  ) dut (
    .clk_i,
    .rst_ni,
    .enable_i,
    .filter_i,
    .filter_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  function automatic logic [31:0] clamp_pct(input logic [31:0] pct_raw);
    return (pct_raw > 32'd100) ? 32'd100 : pct_raw;
  endfunction

  function automatic logic pct_hit(input logic [31:0] state, input logic [31:0] pct_raw);
    return ((state % 32'd100) < clamp_pct(pct_raw));
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign case_mix_w = rand_q ^ traffic_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i;
  assign case_w = case_mix_w[2:0];
  assign next_enable_w = pct_hit(rand_q ^ cfg_source_mask_i,
                                 cfg_req_valid_pct_i + cfg_host_d_ready_pct_i);
  assign next_filter_w = (case_w == 3'd0) ? 1'b0 :
                         (case_w == 3'd1) ? 1'b1 :
                         (case_w == 3'd2) ? traffic_cycle_q[2] :
                         (case_w == 3'd3) ? ~traffic_cycle_q[2] :
                         (case_w == 3'd4) ? rand_q[7] :
                         (case_w == 3'd5) ? cfg_req_data_mode_i[0] :
                         (case_w == 3'd6) ? cfg_rsp_data_mode_i[0] :
                                             rand_q[15];
  assign model_stored_vector_d_w = {model_stored_vector_q[Cycles-2:0], filter_i};
  assign model_update_w = (model_stored_vector_d_w == {Cycles{1'b0}}) ||
                          (model_stored_vector_d_w == {Cycles{1'b1}});
  assign expected_filter_o_w = enable_i ? model_stored_value_q : filter_i;
  assign observed_match_w = expected_filter_o_w == filter_o;

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
      rand_q <= cfg_seed_i ^ 32'hf17e_4a11;
      enable_i <= 1'b0;
      filter_i <= 1'b0;
      enable_count_q <= 32'd0;
      bypass_count_q <= 32'd0;
      input_high_count_q <= 32'd0;
      input_low_count_q <= 32'd0;
      output_high_count_q <= 32'd0;
      output_low_count_q <= 32'd0;
      output_change_count_q <= 32'd0;
      model_match_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      stable_one_update_count_q <= 32'd0;
      stable_zero_update_count_q <= 32'd0;
      enable_change_count_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'h4f11_7e55;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
      pre_update_cycles_q <= 32'd0;
      model_stored_vector_q <= '0;
      model_stored_value_q <= 1'b0;
      last_enable_q <= 1'b0;
      last_filter_o_q <= 1'b0;
    end else if (phase_w != DonePhase) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_address_base_i);
      last_enable_q <= enable_i;
      last_filter_o_q <= filter_o;

      if (phase_w == TrafficPhase) begin
        traffic_cycle_q <= traffic_cycle_q + 32'd1;
        enable_i <= next_enable_w;
        filter_i <= next_filter_w;
        seen_q[0] <= 1'b1;
      end else if (phase_w == DrainPhase) begin
        drain_cycle_q <= drain_cycle_q + 32'd1;
        enable_i <= cfg_rsp_delay_mode_i[0] || (drain_cycle_q[0] == 1'b0);
        filter_i <= drain_cycle_q[2];
        stalled_signature_q <= stalled_signature_q ^ signature_q ^ drain_cycle_q;
        seen_q[1] <= 1'b1;
      end

      model_stored_vector_q <= model_stored_vector_d_w;
      if (model_update_w) begin
        model_stored_value_q <= filter_i;
      end

      signature_q <= {signature_q[28:0], signature_q[31:29]} ^
                     rand_q ^ {28'd0, model_stored_vector_q} ^
                     {28'd0, enable_i, filter_i, filter_o, expected_filter_o_w};

      if (enable_i) begin
        enable_count_q <= enable_count_q + 32'd1;
        seen_q[2] <= 1'b1;
      end else begin
        bypass_count_q <= bypass_count_q + 32'd1;
        seen_q[3] <= 1'b1;
      end
      if (filter_i) begin
        input_high_count_q <= input_high_count_q + 32'd1;
        seen_q[4] <= 1'b1;
      end else begin
        input_low_count_q <= input_low_count_q + 32'd1;
        seen_q[5] <= 1'b1;
      end
      if (filter_o) begin
        output_high_count_q <= output_high_count_q + 32'd1;
        seen_q[6] <= 1'b1;
      end else begin
        output_low_count_q <= output_low_count_q + 32'd1;
        seen_q[7] <= 1'b1;
      end
      if (filter_o != last_filter_o_q) begin
        output_change_count_q <= output_change_count_q + 32'd1;
        seen_q[8] <= 1'b1;
      end
      if (observed_match_w) begin
        model_match_count_q <= model_match_count_q + 32'd1;
        seen_q[9] <= 1'b1;
      end else begin
        mismatch_count_q <= mismatch_count_q + 32'd1;
        seen_q[10] <= 1'b1;
      end
      if (model_update_w && filter_i) begin
        stable_one_update_count_q <= stable_one_update_count_q + 32'd1;
        seen_q[11] <= 1'b1;
      end
      if (model_update_w && !filter_i) begin
        stable_zero_update_count_q <= stable_zero_update_count_q + 32'd1;
        seen_q[12] <= 1'b1;
      end
      if (enable_i != last_enable_q) begin
        enable_change_count_q <= enable_change_count_q + 32'd1;
        seen_q[13] <= 1'b1;
      end
      if (!model_update_w) begin
        pre_update_cycles_q <= pre_update_cycles_q + 32'd1;
        seen_q[14] <= 1'b1;
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == DonePhase);
  assign cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_reset_cycles_i ^
                           cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i ^
                           32'hf117_e4a1;
  assign host_req_accepted_o = enable_count_q;
  assign device_req_accepted_o = bypass_count_q;
  assign device_rsp_accepted_o = output_high_count_q;
  assign host_rsp_accepted_o = output_change_count_q;
  assign rsp_queue_overflow_o = mismatch_count_q;
  assign progress_cycle_count_o = global_cycle_q;
  assign progress_signature_o = signature_q ^ stalled_signature_q ^ {30'd0, phase_w};

  assign toggle_bitmap_word0_o = {
    2'd0,
    seen_q[14:0],
    model_stored_vector_q,
    enable_i,
    filter_i,
    filter_o,
    expected_filter_o_w,
    model_update_w,
    rst_ni,
    done_o,
    phase_w,
    global_cycle_q[1:0]
  };
  assign toggle_bitmap_word1_o = {
    seen_q[30:15],
    case_w,
    last_enable_q,
    last_filter_o_q,
    observed_match_w,
    phase_w,
    cfg_valid_i,
    done_o,
    global_cycle_q[5:0]
  };
  assign toggle_bitmap_word2_o = {
    enable_count_q[7:0],
    bypass_count_q[7:0],
    output_change_count_q[7:0],
    mismatch_count_q[7:0]
  };

  assign real_toggle_subset_word0_o = enable_count_q;
  assign real_toggle_subset_word1_o = bypass_count_q;
  assign real_toggle_subset_word2_o = input_high_count_q;
  assign real_toggle_subset_word3_o = input_low_count_q;
  assign real_toggle_subset_word4_o = output_high_count_q;
  assign real_toggle_subset_word5_o = output_low_count_q;
  assign real_toggle_subset_word6_o = output_change_count_q;
  assign real_toggle_subset_word7_o = model_match_count_q;
  assign real_toggle_subset_word8_o = mismatch_count_q;
  assign real_toggle_subset_word9_o = stable_one_update_count_q;
  assign real_toggle_subset_word10_o = stable_zero_update_count_q;
  assign real_toggle_subset_word11_o = enable_change_count_q;
  assign real_toggle_subset_word12_o = traffic_cycle_q;
  assign real_toggle_subset_word13_o = drain_cycle_q;
  assign real_toggle_subset_word14_o = rand_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_signature_o;
  assign real_toggle_subset_word17_o = {31'd0, done_o} ^ progress_signature_o;

  assign focused_wave_word0_o = {28'd0, enable_i, filter_i, filter_o, expected_filter_o_w};
  assign focused_wave_word1_o = {28'd0, model_stored_vector_q};
  assign focused_wave_word2_o = enable_count_q ^ bypass_count_q;
  assign focused_wave_word3_o = input_high_count_q ^ input_low_count_q;
  assign focused_wave_word4_o = output_high_count_q ^ output_low_count_q;
  assign focused_wave_word5_o = stable_one_update_count_q ^ stable_zero_update_count_q;
  assign focused_wave_word6_o = progress_cycle_count_o;
  assign focused_wave_word7_o = progress_signature_o;

  assign oracle_expected_ok_count_o = model_match_count_q;
  assign oracle_expected_err_count_o = mismatch_count_q;
  assign oracle_observed_ok_count_o = output_high_count_q;
  assign oracle_observed_err_count_o = output_low_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {
    enable_count_q[7:0],
    bypass_count_q[7:0],
    stable_one_update_count_q[7:0],
    stable_zero_update_count_q[7:0]
  };
  assign oracle_semantic_case_seen_o = {22'd0, case_w, model_stored_vector_q, enable_i, filter_i, filter_o};
  assign oracle_semantic_case_acked_o = {28'd0, model_stored_vector_d_w};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = pre_update_cycles_q;
endmodule : prim_filter_gpu_cov_tb
