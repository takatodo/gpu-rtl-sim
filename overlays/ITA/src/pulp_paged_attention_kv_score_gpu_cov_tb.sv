module pulp_paged_attention_kv_score_gpu_cov_tb (
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
  localparam int unsigned PageCount = 8;
  localparam int unsigned SlotsPerPage = 16;
  localparam int unsigned TotalSlots = PageCount * SlotsPerPage;
  localparam int unsigned PageWidth = 3;
  localparam int unsigned OffsetWidth = 4;
  localparam int unsigned SlotWidth = 7;
  localparam int unsigned ScoreWindow = 4;

  localparam logic [1:0] ResetPhase   = 2'd0;
  localparam logic [1:0] TrafficPhase = 2'd1;
  localparam logic [1:0] DrainPhase   = 2'd2;
  localparam logic [1:0] DonePhase    = 2'd3;

  logic clk_i;
  logic reset_like_w /* verilator public_flat */;
  logic [1:0] phase_q;
  logic [31:0] cycle_q;
  logic [31:0] traffic_cycle_q;
  logic [31:0] drain_cycle_q;
  logic [31:0] rand_q;
  logic [31:0] key_page_q [PageCount][SlotsPerPage];
  logic [31:0] value_page_q [PageCount][SlotsPerPage];
  logic [PageWidth-1:0] page_table_q [PageCount];
  logic [PageWidth-1:0] remap_ptr_q;
  logic [SlotWidth-1:0] logical_tail_q;
  logic [SlotWidth:0] valid_slots_q;
  logic [31:0] token_count_q;
  logic [31:0] kv_read_count_q;
  logic [31:0] score_count_q;
  logic [31:0] selected_count_q;
  logic [31:0] page_boundary_count_q;
  logic [31:0] remap_count_q;
  logic [31:0] wrap_count_q;
  logic [31:0] signature_q;
  logic [31:0] query_q;
  logic [31:0] last_key_q;
  logic [31:0] last_value_q;
  logic [31:0] selected_key_q;
  logic [31:0] selected_value_q;
  logic [31:0] score_accum_q;
  logic [31:0] best_score_q;
  logic [SlotWidth-1:0] best_slot_q;
  logic [31:0] last_page_tag_q;

  function automatic logic [31:0] xorshift32(input logic [31:0] value);
    logic [31:0] x;
    begin
      x = value ^ (value << 13);
      x = x ^ (x >> 17);
      xorshift32 = x ^ (x << 5);
    end
  endfunction

  function automatic logic [31:0] make_key(input logic [31:0] base, input logic [31:0] token);
    begin
      make_key = xorshift32(base ^ token ^ 32'h5041_4b45);
    end
  endfunction

  function automatic logic [31:0] make_value(input logic [31:0] base, input logic [31:0] token);
    begin
      make_value = xorshift32(base ^ {token[15:0], token[31:16]} ^ 32'h5041_5641);
    end
  endfunction

  function automatic logic [31:0] score_key(
      input logic [31:0] query,
      input logic [31:0] key,
      input logic [31:0] value,
      input logic [SlotWidth-1:0] slot);
    begin
      score_key = (query ^ key) + ({query[15:0], query[31:16]} ^ value) + {25'd0, slot};
    end
  endfunction

  initial begin
    clk_i = 1'b0;
    phase_q = ResetPhase;
    cycle_q = 32'd0;
    traffic_cycle_q = 32'd0;
    drain_cycle_q = 32'd0;
    rand_q = 32'h1;
    remap_ptr_q = '0;
    logical_tail_q = '0;
    valid_slots_q = '0;
    token_count_q = 32'd0;
    kv_read_count_q = 32'd0;
    score_count_q = 32'd0;
    selected_count_q = 32'd0;
    page_boundary_count_q = 32'd0;
    remap_count_q = 32'd0;
    wrap_count_q = 32'd0;
    signature_q = 32'h5041_5454;
    query_q = 32'd0;
    last_key_q = 32'd0;
    last_value_q = 32'd0;
    selected_key_q = 32'd0;
    selected_value_q = 32'd0;
    score_accum_q = 32'd0;
    best_score_q = 32'd0;
    best_slot_q = '0;
    last_page_tag_q = 32'd0;
    for (int page = 0; page < PageCount; page = page + 1) begin
      page_table_q[page] = PageWidth'(page);
      for (int slot = 0; slot < SlotsPerPage; slot = slot + 1) begin
        key_page_q[page][slot] = 32'd0;
        value_page_q[page][slot] = 32'd0;
      end
    end
  end

  always #5 clk_i = ~clk_i;

  always_ff @(posedge clk_i) begin
    if (reset_like_w) begin
      phase_q <= ResetPhase;
      cycle_q <= cycle_q + 32'd1;
      traffic_cycle_q <= 32'd0;
      drain_cycle_q <= 32'd0;
      rand_q <= 32'h1;
      remap_ptr_q <= '0;
      logical_tail_q <= '0;
      valid_slots_q <= '0;
      token_count_q <= 32'd0;
      kv_read_count_q <= 32'd0;
      score_count_q <= 32'd0;
      selected_count_q <= 32'd0;
      page_boundary_count_q <= 32'd0;
      remap_count_q <= 32'd0;
      wrap_count_q <= 32'd0;
      signature_q <= 32'h5041_5454;
      query_q <= 32'd0;
      last_key_q <= 32'd0;
      last_value_q <= 32'd0;
      selected_key_q <= 32'd0;
      selected_value_q <= 32'd0;
      score_accum_q <= 32'd0;
      best_score_q <= 32'd0;
      best_slot_q <= '0;
      last_page_tag_q <= 32'd0;
      for (int page = 0; page < PageCount; page = page + 1) begin
        page_table_q[page] <= PageWidth'(page);
        for (int slot = 0; slot < SlotsPerPage; slot = slot + 1) begin
          key_page_q[page][slot] <= 32'd0;
          value_page_q[page][slot] <= 32'd0;
        end
      end
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
          logic [31:0] key;
          logic [31:0] value;
          logic [31:0] query;
          logic [31:0] score;
          logic [31:0] best_score;
          logic [31:0] accum_score;
          logic [31:0] candidate_key;
          logic [31:0] candidate_value;
          logic [31:0] best_key;
          logic [31:0] best_value;
          logic [SlotWidth-1:0] candidate_slot;
          logic [SlotWidth-1:0] best_slot;
          logic [PageWidth-1:0] write_logical_page;
          logic [OffsetWidth-1:0] write_offset;
          logic [PageWidth-1:0] write_physical_page;
          logic [PageWidth-1:0] read_logical_page;
          logic [OffsetWidth-1:0] read_offset;
          logic [PageWidth-1:0] read_physical_page;
          logic page_boundary;
          logic wrap_event;
          logic any_candidate;

          key = make_key(rand_q ^ cfg_req_data_hi_xor_i ^ cfg_address_base_i, token_count_q);
          value = make_value(rand_q ^ cfg_rsp_data_hi_xor_i ^ cfg_source_mask_i, token_count_q);
          query = xorshift32(rand_q ^ cfg_seed_i ^ token_count_q ^ 32'h5155_4552);
          write_logical_page = logical_tail_q[SlotWidth-1:OffsetWidth];
          write_offset = logical_tail_q[OffsetWidth-1:0];
          write_physical_page = page_table_q[write_logical_page];
          page_boundary = (write_offset == '0);
          wrap_event = (logical_tail_q == SlotWidth'(TotalSlots - 1));
          best_score = 32'd0;
          accum_score = 32'd0;
          best_key = 32'd0;
          best_value = 32'd0;
          best_slot = '0;
          any_candidate = 1'b0;

          for (int cand = 0; cand < ScoreWindow; cand = cand + 1) begin
            if (valid_slots_q > (SlotWidth + 1)'(cand)) begin
              candidate_slot = logical_tail_q - SlotWidth'(cand + 1);
              read_logical_page = candidate_slot[SlotWidth-1:OffsetWidth];
              read_offset = candidate_slot[OffsetWidth-1:0];
              read_physical_page = page_table_q[read_logical_page];
              candidate_key = key_page_q[read_physical_page][read_offset];
              candidate_value = value_page_q[read_physical_page][read_offset];
              score = score_key(query, candidate_key, candidate_value, candidate_slot);
              accum_score = xorshift32(accum_score ^ score ^ {25'd0, candidate_slot});
              if (!any_candidate || score > best_score) begin
                best_score = score;
                best_key = candidate_key;
                best_value = candidate_value;
                best_slot = candidate_slot;
              end
              any_candidate = 1'b1;
            end
          end

          key_page_q[write_physical_page][write_offset] <= key;
          value_page_q[write_physical_page][write_offset] <= value;
          query_q <= query;
          last_key_q <= key;
          last_value_q <= value;
          selected_key_q <= best_key;
          selected_value_q <= best_value;
          best_score_q <= best_score;
          best_slot_q <= best_slot;
          score_accum_q <= xorshift32(score_accum_q ^ accum_score ^ best_score);
          last_page_tag_q <= {18'd0, page_table_q[best_slot[SlotWidth-1:OffsetWidth]], write_physical_page, best_slot[OffsetWidth-1:0], write_offset};
          token_count_q <= token_count_q + 32'd1;
          if (any_candidate) begin
            kv_read_count_q <= kv_read_count_q + ScoreWindow[31:0];
            score_count_q <= score_count_q + ScoreWindow[31:0];
            selected_count_q <= selected_count_q + 32'd1;
          end
          if (page_boundary) begin
            page_boundary_count_q <= page_boundary_count_q + 32'd1;
          end
          if (token_count_q >= TotalSlots[31:0] && page_boundary) begin
            page_table_q[write_logical_page] <= remap_ptr_q;
            remap_ptr_q <= remap_ptr_q + 1'b1;
            remap_count_q <= remap_count_q + 32'd1;
          end
          if (wrap_event) begin
            wrap_count_q <= wrap_count_q + 32'd1;
          end
          if (valid_slots_q != TotalSlots[SlotWidth:0]) begin
            valid_slots_q <= valid_slots_q + 1'b1;
          end
          logical_tail_q <= logical_tail_q + 1'b1;
          signature_q <= xorshift32(signature_q ^ key ^ value ^ query ^ accum_score ^ best_score);
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
    cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_drain_cycles_i ^ 32'h5041_5454;
    host_req_accepted_o = token_count_q;
    device_req_accepted_o = score_count_q;
    device_rsp_accepted_o = selected_count_q;
    host_rsp_accepted_o = kv_read_count_q;
    rsp_queue_overflow_o = 32'd0;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q;
    toggle_bitmap_word0_o = {
      26'd0,
      remap_count_q != 0,
      wrap_count_q != 0,
      page_boundary_count_q != 0,
      selected_count_q != 0,
      score_count_q != 0,
      token_count_q != 0
    };
    toggle_bitmap_word1_o = query_q ^ selected_key_q ^ best_score_q;
    toggle_bitmap_word2_o = selected_value_q ^ score_accum_q ^ last_page_tag_q;
    real_toggle_subset_word0_o = token_count_q;
    real_toggle_subset_word1_o = kv_read_count_q;
    real_toggle_subset_word2_o = score_count_q;
    real_toggle_subset_word3_o = selected_count_q;
    real_toggle_subset_word4_o = page_boundary_count_q;
    real_toggle_subset_word5_o = remap_count_q;
    real_toggle_subset_word6_o = wrap_count_q;
    real_toggle_subset_word7_o = {25'd0, logical_tail_q};
    real_toggle_subset_word8_o = signature_q;
    real_toggle_subset_word9_o = query_q;
    real_toggle_subset_word10_o = best_score_q;
    real_toggle_subset_word11_o = {25'd0, best_slot_q};
    real_toggle_subset_word12_o = selected_key_q;
    real_toggle_subset_word13_o = selected_value_q;
    real_toggle_subset_word14_o = score_accum_q;
    real_toggle_subset_word15_o = last_key_q ^ last_value_q;
    real_toggle_subset_word16_o = last_page_tag_q;
    real_toggle_subset_word17_o = {30'd0, phase_q};
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = traffic_cycle_q;
    focused_wave_word2_o = drain_cycle_q;
    focused_wave_word3_o = {30'd0, phase_q};
    focused_wave_word4_o = query_q;
    focused_wave_word5_o = best_score_q;
    focused_wave_word6_o = selected_key_q ^ selected_value_q;
    focused_wave_word7_o = {29'd0, selected_count_q != 0, score_count_q != 0, done_o};
    oracle_expected_ok_count_o = score_count_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = selected_count_q;
    oracle_observed_err_count_o = 32'd0;
    oracle_semantic_family_seen_o = 32'h5041_5454;
    oracle_semantic_family_acked_o = {31'd0, score_count_q != 0};
    oracle_semantic_case_seen_o = 32'h5343_4f52;
    oracle_semantic_case_acked_o = {31'd0, selected_count_q != 0};
    oracle_req_signature_o = query_q;
    oracle_stalled_req_signature_o = selected_key_q;
    oracle_req_signature_delta_o = query_q ^ selected_key_q ^ best_score_q;
    oracle_req_stable_violation_o = 32'd0;
    oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q - selected_count_q;
  end
endmodule
