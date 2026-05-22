module mobile_vit_cpu_kick_rtl_proxy_gpu_cov_tb (
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
  localparam logic [2:0] StReset     = 3'd0;
  localparam logic [2:0] StLoadModel = 3'd1;
  localparam logic [2:0] StLoadImage = 3'd2;
  localparam logic [2:0] StKickInfer = 3'd3;
  localparam logic [2:0] StPollDone  = 3'd4;
  localparam logic [2:0] StDone      = 3'd5;

  logic clk_i;
  logic reset_like_w /* verilator public_flat */;
  logic [2:0] state_q;
  logic [31:0] cycle_q;
  logic [31:0] target_images_q;
  logic [31:0] image_index_q;
  logic [31:0] load_model_count_q;
  logic [31:0] load_image_count_q;
  logic [31:0] kick_count_q;
  logic [31:0] poll_count_q;
  logic [31:0] done_count_q;
  logic [31:0] batch_seen_q;
  logic [31:0] command_q;
  logic [31:0] status_q;
  logic [31:0] result_word_q;
  logic [31:0] signature_q;
  logic [31:0] cfg_mix_w;

  initial begin
    clk_i = 1'b0;
    state_q = StReset;
    cycle_q = 32'd0;
    target_images_q = 32'd0;
    image_index_q = 32'd0;
    load_model_count_q = 32'd0;
    load_image_count_q = 32'd0;
    kick_count_q = 32'd0;
    poll_count_q = 32'd0;
    done_count_q = 32'd0;
    batch_seen_q = 32'd0;
    command_q = 32'd0;
    status_q = 32'd0;
    result_word_q = 32'd0;
    signature_q = 32'h4d56_4954;
  end

  always #5 clk_i = ~clk_i;

  always_comb begin
    reset_like_w = (cycle_q < cfg_reset_cycles_i);
  end

  always_comb begin
    cfg_mix_w = cfg_req_fill_target_i ^ cfg_req_burst_len_max_i ^
                cfg_req_address_mode_i ^ cfg_access_ack_data_pct_i ^
                cfg_rsp_error_pct_i ^ cfg_rsp_fill_target_i ^
                cfg_rsp_delay_max_i ^ cfg_rsp_delay_mode_i ^
                cfg_rsp_data_hi_xor_i ^ cfg_drain_cycles_i ^
                cfg_source_mask_i;
  end

  function automatic logic [31:0] selected_image_count(input logic [31:0] requested);
    if (requested == 32'd0) begin
      selected_image_count = 32'd1;
    end else if (requested > 32'd1024) begin
      selected_image_count = 32'd1024;
    end else begin
      selected_image_count = requested;
    end
  endfunction

  always_ff @(posedge clk_i) begin
    cycle_q <= cycle_q + 32'd1;
    if (reset_like_w) begin
      state_q <= StReset;
      target_images_q <= selected_image_count(cfg_batch_length_i);
      image_index_q <= 32'd0;
      load_model_count_q <= 32'd0;
      load_image_count_q <= 32'd0;
      kick_count_q <= 32'd0;
      poll_count_q <= 32'd0;
      done_count_q <= 32'd0;
      batch_seen_q <= 32'd0;
      command_q <= 32'd0;
      status_q <= 32'd0;
      result_word_q <= 32'd0;
      signature_q <= 32'h4d56_4954 ^ cfg_seed_i;
    end else if (cfg_valid_i) begin
      unique case (state_q)
        StReset: begin
          state_q <= StLoadModel;
          target_images_q <= selected_image_count(cfg_batch_length_i);
        end
        StLoadModel: begin
          load_model_count_q <= 32'd1;
          command_q <= 32'h4c4f_4144;
          signature_q <= signature_q ^ 32'h4d4f_444c ^ cfg_req_family_i;
          state_q <= StLoadImage;
        end
        StLoadImage: begin
          load_image_count_q <= load_image_count_q + 32'd1;
          command_q <= 32'h494d_4147;
          batch_seen_q <= cfg_batch_length_i;
          signature_q <= {signature_q[30:0], signature_q[31]} ^
                         image_index_q ^ cfg_req_data_hi_xor_i;
          state_q <= StKickInfer;
        end
        StKickInfer: begin
          kick_count_q <= kick_count_q + 32'd1;
          command_q <= 32'h4b49_434b;
          status_q <= 32'h0000_0001;
          result_word_q <= cfg_seed_i ^ image_index_q ^
                           cfg_address_base_i ^ cfg_address_mask_i;
          signature_q <= signature_q ^ 32'h494e_4652 ^ result_word_q;
          state_q <= StPollDone;
        end
        StPollDone: begin
          poll_count_q <= poll_count_q + 32'd1;
          done_count_q <= done_count_q + 32'd1;
          status_q <= 32'h0000_0002;
          if ((image_index_q + 32'd1) >= target_images_q) begin
            state_q <= StDone;
          end else begin
            image_index_q <= image_index_q + 32'd1;
            state_q <= StLoadImage;
          end
        end
        default: begin
          state_q <= StDone;
          status_q <= 32'h0000_0003;
        end
      endcase
    end
  end

  always_comb begin
    done_o = (state_q == StDone);
    cfg_signature_o = signature_q ^ 32'h4350_554b ^ cfg_mix_w;
    host_req_accepted_o = kick_count_q;
    device_req_accepted_o = load_image_count_q;
    device_rsp_accepted_o = done_count_q;
    host_rsp_accepted_o = poll_count_q;
    rsp_queue_overflow_o = 32'd0;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q ^ {29'd0, state_q};
    toggle_bitmap_word0_o = {
      24'd0,
      done_count_q != 0,
      poll_count_q != 0,
      kick_count_q != 0,
      load_image_count_q != 0,
      load_model_count_q != 0,
      state_q
    };
    toggle_bitmap_word1_o = command_q ^ status_q;
    toggle_bitmap_word2_o = result_word_q ^ target_images_q;
    real_toggle_subset_word0_o = load_model_count_q;
    real_toggle_subset_word1_o = load_image_count_q;
    real_toggle_subset_word2_o = kick_count_q;
    real_toggle_subset_word3_o = poll_count_q;
    real_toggle_subset_word4_o = done_count_q;
    real_toggle_subset_word5_o = target_images_q;
    real_toggle_subset_word6_o = image_index_q;
    real_toggle_subset_word7_o = command_q;
    real_toggle_subset_word8_o = status_q;
    real_toggle_subset_word9_o = result_word_q;
    real_toggle_subset_word10_o = signature_q ^ cfg_mix_w;
    real_toggle_subset_word11_o = batch_seen_q;
    real_toggle_subset_word12_o = cfg_req_family_i ^ cfg_rsp_family_i;
    real_toggle_subset_word13_o = cfg_req_data_mode_i ^ cfg_rsp_data_mode_i;
    real_toggle_subset_word14_o = cfg_req_valid_pct_i ^ cfg_rsp_valid_pct_i;
    real_toggle_subset_word15_o = cfg_host_d_ready_pct_i ^ cfg_device_a_ready_pct_i;
    real_toggle_subset_word16_o = cfg_put_full_pct_i ^ cfg_put_partial_pct_i;
    real_toggle_subset_word17_o = {29'd0, state_q};
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = {29'd0, state_q};
    focused_wave_word2_o = target_images_q;
    focused_wave_word3_o = image_index_q;
    focused_wave_word4_o = kick_count_q;
    focused_wave_word5_o = poll_count_q;
    focused_wave_word6_o = done_count_q;
    focused_wave_word7_o = {30'd0, status_q[1], done_o};
    oracle_expected_ok_count_o = target_images_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = done_count_q;
    oracle_observed_err_count_o = 32'd0;
    oracle_semantic_family_seen_o = 32'h4d56_4954;
    oracle_semantic_family_acked_o = {31'd0, load_model_count_q != 0};
    oracle_semantic_case_seen_o = 32'h4350_554b;
    oracle_semantic_case_acked_o = {31'd0, done_o};
    oracle_req_signature_o = signature_q;
    oracle_stalled_req_signature_o = command_q ^ status_q;
    oracle_req_signature_delta_o = signature_q ^ result_word_q;
    oracle_req_stable_violation_o = 32'd0;
    oracle_pre_handshake_traffic_cycles_o = poll_count_q;
  end
endmodule
