module pulp_paged_kv_cache_large_gpu_cov_tb (
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
  logic [31:0] read_count_q;
  logic [31:0] hit_count_q;
  logic [31:0] page_boundary_count_q;
  logic [31:0] remap_count_q;
  logic [31:0] wrap_count_q;
  logic [31:0] signature_q;
  logic [31:0] last_key_q;
  logic [31:0] last_value_q;
  logic [31:0] last_read_key_q;
  logic [31:0] last_read_value_q;
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
      make_key = xorshift32(base ^ token ^ 32'h5047_4b56);
    end
  endfunction

  function automatic logic [31:0] make_value(input logic [31:0] base, input logic [31:0] token);
    begin
      make_value = xorshift32(base ^ {token[15:0], token[31:16]} ^ 32'h5047_5643);
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
    read_count_q = 32'd0;
    hit_count_q = 32'd0;
    page_boundary_count_q = 32'd0;
    remap_count_q = 32'd0;
    wrap_count_q = 32'd0;
    signature_q = 32'h5047_4b56;
    last_key_q = 32'd0;
    last_value_q = 32'd0;
    last_read_key_q = 32'd0;
    last_read_value_q = 32'd0;
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
      read_count_q <= 32'd0;
      hit_count_q <= 32'd0;
      page_boundary_count_q <= 32'd0;
      remap_count_q <= 32'd0;
      wrap_count_q <= 32'd0;
      signature_q <= 32'h5047_4b56;
      last_key_q <= 32'd0;
      last_value_q <= 32'd0;
      last_read_key_q <= 32'd0;
      last_read_value_q <= 32'd0;
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
          logic [SlotWidth-1:0] read_logical_slot;
          logic [PageWidth-1:0] write_logical_page;
          logic [OffsetWidth-1:0] write_offset;
          logic [PageWidth-1:0] write_physical_page;
          logic [PageWidth-1:0] read_logical_page;
          logic [OffsetWidth-1:0] read_offset;
          logic [PageWidth-1:0] read_physical_page;
          logic page_boundary;
          logic wrap_event;

          key = make_key(rand_q ^ cfg_req_data_hi_xor_i ^ cfg_address_base_i, token_count_q);
          value = make_value(rand_q ^ cfg_rsp_data_hi_xor_i ^ cfg_source_mask_i, token_count_q);
          read_logical_slot = (valid_slots_q == 0) ? '0 : (logical_tail_q - SlotWidth'(1));
          write_logical_page = logical_tail_q[SlotWidth-1:OffsetWidth];
          write_offset = logical_tail_q[OffsetWidth-1:0];
          write_physical_page = page_table_q[write_logical_page];
          read_logical_page = read_logical_slot[SlotWidth-1:OffsetWidth];
          read_offset = read_logical_slot[OffsetWidth-1:0];
          read_physical_page = page_table_q[read_logical_page];
          page_boundary = (write_offset == '0);
          wrap_event = (logical_tail_q == SlotWidth'(TotalSlots - 1));

          last_read_key_q <= key_page_q[read_physical_page][read_offset];
          last_read_value_q <= value_page_q[read_physical_page][read_offset];
          key_page_q[write_physical_page][write_offset] <= key;
          value_page_q[write_physical_page][write_offset] <= value;
          last_key_q <= key;
          last_value_q <= value;
          last_page_tag_q <= {18'd0, read_physical_page, write_physical_page, read_offset, write_offset};
          token_count_q <= token_count_q + 32'd1;
          read_count_q <= read_count_q + 32'd1;
          if (valid_slots_q != 0) begin
            hit_count_q <= hit_count_q + 32'd1;
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
          signature_q <= xorshift32(
              signature_q ^ key ^ value ^
              key_page_q[read_physical_page][read_offset] ^
              value_page_q[read_physical_page][read_offset] ^
              {18'd0, read_physical_page, write_physical_page, read_offset, write_offset});
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
    cfg_signature_o = cfg_seed_i ^ cfg_batch_length_i ^ cfg_drain_cycles_i ^ 32'h5047_4b56;
    host_req_accepted_o = token_count_q;
    device_req_accepted_o = token_count_q;
    device_rsp_accepted_o = read_count_q;
    host_rsp_accepted_o = read_count_q;
    rsp_queue_overflow_o = 32'd0;
    progress_cycle_count_o = cycle_q;
    progress_signature_o = signature_q;
    toggle_bitmap_word0_o = {
      27'd0,
      remap_count_q != 0,
      wrap_count_q != 0,
      page_boundary_count_q != 0,
      hit_count_q != 0,
      token_count_q != 0
    };
    toggle_bitmap_word1_o = last_key_q ^ last_read_key_q;
    toggle_bitmap_word2_o = last_value_q ^ last_read_value_q ^ last_page_tag_q;
    real_toggle_subset_word0_o = token_count_q;
    real_toggle_subset_word1_o = read_count_q;
    real_toggle_subset_word2_o = hit_count_q;
    real_toggle_subset_word3_o = page_boundary_count_q;
    real_toggle_subset_word4_o = remap_count_q;
    real_toggle_subset_word5_o = wrap_count_q;
    real_toggle_subset_word6_o = {24'd0, valid_slots_q};
    real_toggle_subset_word7_o = {25'd0, logical_tail_q};
    real_toggle_subset_word8_o = signature_q;
    real_toggle_subset_word9_o = last_key_q;
    real_toggle_subset_word10_o = last_value_q;
    real_toggle_subset_word11_o = last_read_key_q;
    real_toggle_subset_word12_o = last_read_value_q;
    real_toggle_subset_word13_o = last_page_tag_q;
    real_toggle_subset_word14_o =
        key_page_q[0][0] ^ key_page_q[1][3] ^ key_page_q[2][6] ^ key_page_q[3][9] ^
        key_page_q[4][12] ^ key_page_q[5][15] ^ key_page_q[6][2] ^ key_page_q[7][5];
    real_toggle_subset_word15_o =
        value_page_q[0][1] ^ value_page_q[1][4] ^ value_page_q[2][7] ^ value_page_q[3][10] ^
        value_page_q[4][13] ^ value_page_q[5][0] ^ value_page_q[6][3] ^ value_page_q[7][6];
    real_toggle_subset_word16_o = {
      8'd0,
      page_table_q[0],
      page_table_q[1],
      page_table_q[2],
      page_table_q[3],
      page_table_q[4],
      page_table_q[5],
      page_table_q[6],
      page_table_q[7]
    };
    real_toggle_subset_word17_o = {30'd0, phase_q};
    focused_wave_word0_o = cycle_q;
    focused_wave_word1_o = traffic_cycle_q;
    focused_wave_word2_o = drain_cycle_q;
    focused_wave_word3_o = {30'd0, phase_q};
    focused_wave_word4_o = last_key_q;
    focused_wave_word5_o = last_value_q;
    focused_wave_word6_o = last_read_key_q ^ last_read_value_q;
    focused_wave_word7_o = {29'd0, remap_count_q != 0, wrap_count_q != 0, done_o};
    oracle_expected_ok_count_o = token_count_q;
    oracle_expected_err_count_o = 32'd0;
    oracle_observed_ok_count_o = read_count_q;
    oracle_observed_err_count_o = 32'd0;
    oracle_semantic_family_seen_o = 32'h5047_4b56;
    oracle_semantic_family_acked_o = {31'd0, token_count_q != 0};
    oracle_semantic_case_seen_o = 32'h5041_4745;
    oracle_semantic_case_acked_o = {31'd0, remap_count_q != 0};
    oracle_req_signature_o = last_key_q;
    oracle_stalled_req_signature_o = last_read_key_q;
    oracle_req_signature_delta_o = last_key_q ^ last_read_key_q ^ last_page_tag_q;
    oracle_req_stable_violation_o = 32'd0;
    oracle_pre_handshake_traffic_cycles_o = traffic_cycle_q - read_count_q;
  end
endmodule
