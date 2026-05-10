// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// Minimal GPU-toggle-ready standalone coverage target for prim_fifo_sync_cnt.

module prim_fifo_sync_cnt_gpu_cov_tb (
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
  localparam int unsigned Depth = 4;
  localparam int unsigned PtrW = 2;
  localparam int unsigned DepthW = 3;
  localparam int unsigned WrapPtrW = 3;

  logic clk_i;
  logic rst_ni;
  logic clr_i;
  logic incr_wptr_i;
  logic incr_rptr_i;
  logic [PtrW-1:0] wptr_o;
  logic [PtrW-1:0] rptr_o;
  logic full_o;
  logic empty_o;
  logic [DepthW-1:0] depth_o;
  logic err_o;

  logic [31:0] global_cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] write_count_q;
  logic [31:0] read_count_q;
  logic [31:0] clear_count_q;
  logic [31:0] full_count_q;
  logic [31:0] empty_count_q;
  logic [31:0] mismatch_count_q;
  logic [31:0] depth_sum_q;
  logic [31:0] signature_q;
  logic [31:0] stalled_signature_q;
  logic [31:0] seen_q;
  logic [WrapPtrW-1:0] exp_wptr_wrap_q;
  logic [WrapPtrW-1:0] exp_rptr_wrap_q;
  logic [1:0] phase_w;
  logic [31:0] case_mix_w;
  logic [2:0] case_w;
  logic exp_full_w;
  logic exp_empty_w;
  logic [DepthW-1:0] exp_depth_w;
  logic observed_match_w;
  logic wptr_wrap_set_w;
  logic rptr_wrap_set_w;

  initial clk_i = 1'b0;
  always #5 clk_i = ~clk_i;

  prim_fifo_sync_cnt #(
    .Depth(Depth),
    .Secure(1'b0)
  ) dut (
    .clk_i,
    .rst_ni,
    .clr_i,
    .incr_wptr_i,
    .incr_rptr_i,
    .wptr_o,
    .rptr_o,
    .full_o,
    .empty_o,
    .depth_o,
    .err_o
  );

  function automatic logic [31:0] prng_next(input logic [31:0] state);
    return state * 32'd1664525 + 32'd1013904223;
  endfunction

  assign rst_ni = cfg_valid_i && (global_cycle_q >= cfg_reset_cycles_i);
  assign phase_w = (!cfg_valid_i || !rst_ni) ? 2'd0 :
                   (traffic_cycle_q < cfg_batch_length_i) ? 2'd1 :
                   (drain_cycle_q < cfg_drain_cycles_i) ? 2'd2 : 2'd3;
  assign case_mix_w = rand_q ^ traffic_cycle_q ^ cfg_req_family_i ^ cfg_rsp_family_i;
  assign case_w = case_mix_w[2:0];
  assign exp_full_w = exp_wptr_wrap_q == (exp_rptr_wrap_q ^ 3'b100);
  assign exp_empty_w = exp_wptr_wrap_q == exp_rptr_wrap_q;
  assign exp_depth_w = exp_full_w ? DepthW'(Depth) :
                       exp_wptr_wrap_q[2] == exp_rptr_wrap_q[2] ?
                           DepthW'(exp_wptr_wrap_q[1:0]) - DepthW'(exp_rptr_wrap_q[1:0]) :
                           DepthW'(Depth) - DepthW'(exp_rptr_wrap_q[1:0]) +
                               DepthW'(exp_wptr_wrap_q[1:0]);
  assign observed_match_w = (wptr_o == exp_wptr_wrap_q[1:0]) &&
                            (rptr_o == exp_rptr_wrap_q[1:0]) &&
                            (full_o == exp_full_w) &&
                            (empty_o == exp_empty_w) &&
                            (depth_o == exp_depth_w) &&
                            (err_o == 1'b0);
  assign wptr_wrap_set_w = incr_wptr_i && (exp_wptr_wrap_q[1:0] == PtrW'(Depth - 1));
  assign rptr_wrap_set_w = incr_rptr_i && (exp_rptr_wrap_q[1:0] == PtrW'(Depth - 1));

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      global_cycle_q <= 32'd0;
    end else if (phase_w != 2'd3) begin
      global_cycle_q <= global_cycle_q + 32'd1;
    end

    if (!rst_ni) begin
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= cfg_seed_i ^ 32'hf1f0_c017;
      clr_i <= 1'b0;
      incr_wptr_i <= 1'b0;
      incr_rptr_i <= 1'b0;
      exp_wptr_wrap_q <= '0;
      exp_rptr_wrap_q <= '0;
      write_count_q <= 32'd0;
      read_count_q <= 32'd0;
      clear_count_q <= 32'd0;
      full_count_q <= 32'd0;
      empty_count_q <= 32'd0;
      mismatch_count_q <= 32'd0;
      depth_sum_q <= 32'd0;
      signature_q <= cfg_seed_i ^ 32'hc017_5afe;
      stalled_signature_q <= 32'd0;
      seen_q <= 32'd0;
    end else if (phase_w != 2'd3) begin
      rand_q <= prng_next(rand_q ^ global_cycle_q ^ cfg_source_mask_i);

      if (phase_w == 2'd1 || phase_w == 2'd2) begin
        if (phase_w == 2'd1) traffic_cycle_q <= traffic_cycle_q + 32'd1;
        else drain_cycle_q <= drain_cycle_q + 32'd1;

        unique case (case_w)
          3'd0: begin clr_i <= 1'b0; incr_wptr_i <= 1'b1; incr_rptr_i <= 1'b0; end
          3'd1: begin clr_i <= 1'b0; incr_wptr_i <= 1'b0; incr_rptr_i <= 1'b1; end
          3'd2: begin clr_i <= 1'b0; incr_wptr_i <= 1'b1; incr_rptr_i <= 1'b1; end
          3'd3: begin clr_i <= 1'b1; incr_wptr_i <= 1'b0; incr_rptr_i <= 1'b0; end
          default: begin
            clr_i <= rand_q[4] & (phase_w == 2'd2);
            incr_wptr_i <= rand_q[0];
            incr_rptr_i <= rand_q[1];
          end
        endcase

        if (clr_i) begin
          exp_wptr_wrap_q <= '0;
          exp_rptr_wrap_q <= '0;
        end else begin
          if (wptr_wrap_set_w) exp_wptr_wrap_q <= {~exp_wptr_wrap_q[2], 2'b00};
          else if (incr_wptr_i) exp_wptr_wrap_q <= exp_wptr_wrap_q + 3'd1;
          if (rptr_wrap_set_w) exp_rptr_wrap_q <= {~exp_rptr_wrap_q[2], 2'b00};
          else if (incr_rptr_i) exp_rptr_wrap_q <= exp_rptr_wrap_q + 3'd1;
        end

        write_count_q <= write_count_q + {31'd0, incr_wptr_i};
        read_count_q <= read_count_q + {31'd0, incr_rptr_i};
        clear_count_q <= clear_count_q + {31'd0, clr_i};
        full_count_q <= full_count_q + {31'd0, full_o};
        empty_count_q <= empty_count_q + {31'd0, empty_o};
        mismatch_count_q <= mismatch_count_q + {31'd0, ~observed_match_w};
        depth_sum_q <= depth_sum_q + {29'd0, depth_o};
        seen_q[0] <= 1'b1;
        seen_q[1] <= seen_q[1] | incr_wptr_i;
        seen_q[2] <= seen_q[2] | incr_rptr_i;
        seen_q[3] <= seen_q[3] | clr_i;
        seen_q[4] <= seen_q[4] | full_o;
        seen_q[5] <= seen_q[5] | empty_o;
        seen_q[6] <= seen_q[6] | observed_match_w;
        signature_q <= {signature_q[30:0], signature_q[31]} ^
                       {24'd0, wptr_o, rptr_o, depth_o, full_o} ^ rand_q;
        stalled_signature_q <= stalled_signature_q ^
                               {24'd0, exp_wptr_wrap_q, exp_rptr_wrap_q, clr_i, incr_wptr_i};
      end
    end
  end

  assign done_o = cfg_valid_i && (phase_w == 2'd3);
  assign cfg_signature_o = signature_q ^ stalled_signature_q ^ 32'h51c0_017c;
  assign progress_cycle_count_o = traffic_cycle_q + drain_cycle_q;
  assign progress_signature_o = signature_q;
  assign host_req_accepted_o = traffic_cycle_q;
  assign device_req_accepted_o = write_count_q;
  assign device_rsp_accepted_o = read_count_q;
  assign host_rsp_accepted_o = full_count_q + empty_count_q;
  assign rsp_queue_overflow_o = 32'd0;

  assign real_toggle_subset_word0_o = write_count_q;
  assign real_toggle_subset_word1_o = read_count_q;
  assign real_toggle_subset_word2_o = clear_count_q;
  assign real_toggle_subset_word3_o = full_count_q;
  assign real_toggle_subset_word4_o = empty_count_q;
  assign real_toggle_subset_word5_o = mismatch_count_q;
  assign real_toggle_subset_word6_o = depth_sum_q;
  assign real_toggle_subset_word7_o = {30'd0, wptr_o};
  assign real_toggle_subset_word8_o = {30'd0, rptr_o};
  assign real_toggle_subset_word9_o = {29'd0, depth_o};
  assign real_toggle_subset_word10_o = traffic_cycle_q;
  assign real_toggle_subset_word11_o = drain_cycle_q;
  assign real_toggle_subset_word12_o = rand_q;
  assign real_toggle_subset_word13_o = signature_q;
  assign real_toggle_subset_word14_o = stalled_signature_q;
  assign real_toggle_subset_word15_o = seen_q;
  assign real_toggle_subset_word16_o = cfg_batch_length_i ^ cfg_seed_i;
  assign real_toggle_subset_word17_o = {31'd0, done_o};

  assign toggle_bitmap_word0_o = {14'd0, observed_match_w, exp_empty_w, exp_full_w,
                                  err_o, empty_o, full_o, depth_o, rptr_o, wptr_o,
                                  incr_rptr_i, incr_wptr_i, clr_i, rst_ni, cfg_valid_i};
  assign toggle_bitmap_word1_o = seen_q;
  assign toggle_bitmap_word2_o = signature_q ^ stalled_signature_q;

  assign focused_wave_word0_o = {23'd0, clr_i, incr_wptr_i, incr_rptr_i, full_o,
                                 empty_o, wptr_o, rptr_o};
  assign focused_wave_word1_o = {29'd0, depth_o};
  assign focused_wave_word2_o = write_count_q;
  assign focused_wave_word3_o = read_count_q;
  assign focused_wave_word4_o = full_count_q;
  assign focused_wave_word5_o = empty_count_q;
  assign focused_wave_word6_o = mismatch_count_q;
  assign focused_wave_word7_o = signature_q;

  assign oracle_expected_ok_count_o = write_count_q + read_count_q;
  assign oracle_expected_err_count_o = 32'd0;
  assign oracle_observed_ok_count_o = full_count_q + empty_count_q;
  assign oracle_observed_err_count_o = mismatch_count_q;
  assign oracle_semantic_family_seen_o = seen_q;
  assign oracle_semantic_family_acked_o = {31'd0, observed_match_w};
  assign oracle_semantic_case_seen_o = {29'd0, case_w};
  assign oracle_semantic_case_acked_o = {31'd0, phase_w == 2'd1 || phase_w == 2'd2};
  assign oracle_req_signature_o = signature_q;
  assign oracle_stalled_req_signature_o = stalled_signature_q;
  assign oracle_req_signature_delta_o = signature_q ^ stalled_signature_q;
  assign oracle_req_stable_violation_o = mismatch_count_q;
  assign oracle_pre_handshake_traffic_cycles_o = 32'd0;
endmodule
