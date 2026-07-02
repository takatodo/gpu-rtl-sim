`include "bsg_noc_links.svh"
`include "bsg_wormhole_router.svh"

module bsg_wormhole_router_gpu_cov_tb #(
  parameter int unsigned CoverageWords = 32
) (
  input  logic        clk_i,
  input  logic        cfg_valid_i,
  input  logic [31:0] cfg_seed_i,
  input  logic [31:0] cfg_cycles_i,
  input  logic [31:0] cfg_batch_length_i,
  input  logic [31:0] cfg_req_family_i,
  input  logic [31:0] cfg_req_valid_pct_i,
  input  logic [31:0] cfg_device_a_ready_pct_i,
  input  logic [31:0] cfg_host_d_ready_pct_i,
  input  logic [31:0] cfg_rsp_valid_pct_i,
  input  logic [31:0] cfg_put_full_pct_i,
  input  logic [31:0] cfg_put_partial_pct_i,
  input  logic [31:0] cfg_req_fill_target_i,
  input  logic [31:0] cfg_req_burst_len_max_i,
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
  input  logic [31:0] cfg_address_base_i,
  input  logic [31:0] cfg_address_mask_i,
  input  logic [31:0] cfg_source_mask_i,
  output logic        reset_like_w,
  output logic        done_o,
  output logic [31:0] cfg_signature_o,
  output logic [31:0] cycle_count_o,
  output logic [31:0] host_req_accepted_o,
  output logic [31:0] device_req_accepted_o,
  output logic [31:0] device_rsp_accepted_o,
  output logic [31:0] host_rsp_accepted_o,
  output logic [31:0] rsp_queue_overflow_o,
  output logic [31:0] progress_cycle_count_o,
  output logic [31:0] progress_signature_o,
  output logic [31:0] oracle_expected_ok_o,
  output logic [31:0] oracle_observed_ok_o,
  output logic [31:0] oracle_mismatch_count_o,
  output logic [31:0] oracle_semantic_family_seen_o,
  output logic [31:0] oracle_semantic_family_acked_o,
  output logic [31:0] oracle_semantic_case_seen_o,
  output logic [31:0] oracle_semantic_case_acked_o,
  output logic [31:0] oracle_req_signature_o,
  output logic [31:0] oracle_stalled_req_signature_o,
  output logic [31:0] oracle_req_signature_delta_o,
  output logic [31:0] oracle_pre_handshake_traffic_cycles_o,
  output logic [31:0] toggle_bitmap_word0_o,
  output logic [31:0] toggle_bitmap_word1_o,
  output logic [31:0] toggle_bitmap_word2_o,
  output logic [31:0] toggle_bitmap_word3_o,
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
  output logic [31:0] focused_wave_word7_o
);

  localparam int unsigned Dims = 1;
  localparam int unsigned Dirs = Dims * 2 + 1;
  localparam int unsigned FlitWidth = 16;
  localparam int unsigned LenWidth = 2;
  localparam int CordDims = 1;
  localparam int CordMarkers [CordDims:0] = '{1, 0};
  localparam int unsigned LinkWidth = `bsg_ready_and_link_sif_width(FlitWidth);

  `declare_bsg_ready_and_link_sif_s(FlitWidth, bsg_ready_and_link_sif_s);

  bsg_ready_and_link_sif_s [Dirs-1:0] link_i_cast;
  bsg_ready_and_link_sif_s [Dirs-1:0] link_o_cast;
  logic [Dirs-1:0][LinkWidth-1:0] link_i_w;
  logic [Dirs-1:0][LinkWidth-1:0] link_o_w;
  logic [0:0] my_cord_w;

  assign link_i_w = link_i_cast;
  assign link_o_cast = link_o_w;
  assign my_cord_w = 1'b0;
  assign reset_like_w = cfg_valid_i && (cycle_count_o < cfg_reset_cycles_i);

  bsg_wormhole_router #(
    .flit_width_p(FlitWidth),
    .dims_p(Dims),
    .cord_dims_p(CordDims),
    .cord_markers_pos_p(CordMarkers),
    .len_width_p(LenWidth),
    .hold_on_valid_p(1)
  ) dut (
    .clk_i(clk_i),
    .reset_i(reset_like_w),
    .link_i(link_i_w),
    .link_o(link_o_w),
    .my_cord_i(my_cord_w)
  );

  logic [31:0] lfsr_q;
  logic [31:0] accepted_q;
  logic [31:0] output_q;
  logic [31:0] stalled_q;
  logic [31:0] ready_seen_q;
  logic [31:0] local_seen_q;
  logic [31:0] east_seen_q;
  logic [31:0] west_seen_q;
  logic [31:0] payload_seen_q;
  logic [31:0] signature_q;
  logic [31:0] last_req_sig_q;
  logic [31:0] stalled_sig_q;
  logic [31:0] mismatch_q;

  function automatic logic [31:0] lfsr_next(input logic [31:0] state);
    begin
      lfsr_next = {state[30:0], state[31] ^ state[21] ^ state[1] ^ state[0]} ^ 32'h45d9_f3b;
    end
  endfunction

  function automatic logic pct_hit(input logic [31:0] value, input logic [31:0] pct);
    logic [31:0] bounded_pct;
    begin
      bounded_pct = (pct > 32'd100) ? 32'd100 : pct;
      pct_hit = ((value % 32'd100) < bounded_pct);
    end
  endfunction

  function automatic logic [0:0] choose_dest(input logic [31:0] state);
    begin
      choose_dest = state[1] ^ cfg_req_family_i[0];
    end
  endfunction

  function automatic logic [FlitWidth-1:0] make_header(input logic [31:0] state);
    logic [LenWidth-1:0] len;
    logic [0:0] cord;
    begin
      len = LenWidth'(state[3:2] % 3);
      cord = choose_dest(state);
      make_header = {state[FlitWidth-1:LenWidth+1], len, cord};
    end
  endfunction

  function automatic logic [FlitWidth-1:0] make_payload(input logic [31:0] state);
    begin
      make_payload = FlitWidth'(state ^ cfg_req_data_hi_xor_i ^ 32'hb105_f00d);
    end
  endfunction

  logic traffic_en_w;
  logic local_send_w;
  logic [FlitWidth-1:0] flit_w;
  logic local_fire_w;
  logic east_fire_w;
  logic west_fire_w;
  logic any_output_fire_w;

  assign traffic_en_w = cfg_valid_i && !done_o && !reset_like_w;
  assign local_send_w = traffic_en_w && pct_hit(lfsr_q ^ cfg_seed_i, cfg_req_valid_pct_i);
  assign flit_w = cycle_count_o[0] ? make_payload(lfsr_q) : make_header(lfsr_q);
  assign local_fire_w = link_i_cast[0].v && link_o_cast[0].ready_and_rev;
  assign west_fire_w = link_o_cast[1].v && link_i_cast[1].ready_and_rev;
  assign east_fire_w = link_o_cast[2].v && link_i_cast[2].ready_and_rev;
  assign any_output_fire_w = west_fire_w || east_fire_w || (link_o_cast[0].v && link_i_cast[0].ready_and_rev);

  always_comb begin
    for (int i = 0; i < Dirs; i++) begin
      link_i_cast[i].v = 1'b0;
      link_i_cast[i].data = '0;
      link_i_cast[i].ready_and_rev = 1'b1;
    end
    link_i_cast[0].v = local_send_w;
    link_i_cast[0].data = flit_w;
    link_i_cast[1].ready_and_rev = pct_hit(lfsr_q ^ 32'h1001, cfg_host_d_ready_pct_i);
    link_i_cast[2].ready_and_rev = pct_hit(lfsr_q ^ 32'h2002, cfg_device_a_ready_pct_i);
  end

  always_ff @(posedge clk_i) begin
    if (!cfg_valid_i) begin
      cycle_count_o <= 32'd0;
      lfsr_q <= 32'h1;
      accepted_q <= 32'd0;
      output_q <= 32'd0;
      stalled_q <= 32'd0;
      ready_seen_q <= 32'd0;
      local_seen_q <= 32'd0;
      east_seen_q <= 32'd0;
      west_seen_q <= 32'd0;
      payload_seen_q <= 32'd0;
      signature_q <= 32'd0;
      last_req_sig_q <= 32'd0;
      stalled_sig_q <= 32'd0;
      mismatch_q <= 32'd0;
    end else begin
      cycle_count_o <= cycle_count_o + 32'd1;
      lfsr_q <= lfsr_next(lfsr_q ^ cfg_seed_i ^ cycle_count_o);
      if (reset_like_w) begin
        accepted_q <= 32'd0;
        output_q <= 32'd0;
        stalled_q <= 32'd0;
        ready_seen_q <= 32'd0;
        local_seen_q <= 32'd0;
        east_seen_q <= 32'd0;
        west_seen_q <= 32'd0;
        payload_seen_q <= 32'd0;
        signature_q <= cfg_seed_i ^ 32'hb105_cafe;
        last_req_sig_q <= 32'd0;
        stalled_sig_q <= 32'd0;
        mismatch_q <= 32'd0;
      end else begin
        if (local_send_w && !link_o_cast[0].ready_and_rev) begin
          stalled_q <= stalled_q + 32'd1;
          stalled_sig_q <= stalled_sig_q ^ {16'h51a1, flit_w};
        end
        if (local_fire_w) begin
          accepted_q <= accepted_q + 32'd1;
          local_seen_q <= local_seen_q + 32'd1;
          last_req_sig_q <= {15'd0, choose_dest(lfsr_q), flit_w};
          payload_seen_q <= payload_seen_q + {31'd0, cycle_count_o[0]};
          signature_q <= {signature_q[30:0], signature_q[31]} ^ {16'hace1, flit_w};
        end
        if (west_fire_w) begin
          output_q <= output_q + 32'd1;
          west_seen_q <= west_seen_q + 32'd1;
          signature_q <= signature_q ^ {16'h0a0b, link_o_cast[1].data};
        end
        if (east_fire_w) begin
          output_q <= output_q + 32'd1;
          east_seen_q <= east_seen_q + 32'd1;
          signature_q <= signature_q ^ {16'h0c0d, link_o_cast[2].data};
        end
        if (any_output_fire_w) begin
          ready_seen_q <= ready_seen_q + 32'd1;
        end
      end
    end
  end

  assign done_o = cfg_valid_i && (cycle_count_o >= ((cfg_cycles_i != 32'd0) ? cfg_cycles_i : cfg_batch_length_i));
  assign cfg_signature_o = signature_q ^ cfg_req_family_i ^ cfg_rsp_family_i;
  assign host_req_accepted_o = accepted_q;
  assign device_req_accepted_o = output_q;
  assign device_rsp_accepted_o = east_seen_q;
  assign host_rsp_accepted_o = west_seen_q;
  assign rsp_queue_overflow_o = stalled_q;
  assign progress_cycle_count_o = cycle_count_o;
  assign progress_signature_o = signature_q ^ accepted_q ^ {output_q[15:0], stalled_q[15:0]};
  assign oracle_expected_ok_o = accepted_q;
  assign oracle_observed_ok_o = output_q;
  assign oracle_mismatch_count_o = mismatch_q;
  assign oracle_semantic_family_seen_o = {east_seen_q[15:0], west_seen_q[15:0]};
  assign oracle_semantic_family_acked_o = ready_seen_q;
  assign oracle_semantic_case_seen_o = payload_seen_q;
  assign oracle_semantic_case_acked_o = output_q;
  assign oracle_req_signature_o = last_req_sig_q;
  assign oracle_stalled_req_signature_o = stalled_sig_q;
  assign oracle_req_signature_delta_o = last_req_sig_q ^ stalled_sig_q;
  assign oracle_pre_handshake_traffic_cycles_o = stalled_q;

  assign toggle_bitmap_word0_o = {done_o, reset_like_w, local_send_w, local_fire_w,
                                  west_fire_w, east_fire_w, link_o_cast[0].ready_and_rev,
                                  link_i_cast[1].ready_and_rev, link_i_cast[2].ready_and_rev,
                                  23'd0};
  assign toggle_bitmap_word1_o = accepted_q ^ output_q ^ stalled_q;
  assign toggle_bitmap_word2_o = signature_q;
  assign toggle_bitmap_word3_o = {payload_seen_q[15:0], ready_seen_q[15:0]};

  assign real_toggle_subset_word0_o = accepted_q;
  assign real_toggle_subset_word1_o = output_q;
  assign real_toggle_subset_word2_o = stalled_q;
  assign real_toggle_subset_word3_o = ready_seen_q;
  assign real_toggle_subset_word4_o = local_seen_q;
  assign real_toggle_subset_word5_o = east_seen_q;
  assign real_toggle_subset_word6_o = west_seen_q;
  assign real_toggle_subset_word7_o = payload_seen_q;
  assign real_toggle_subset_word8_o = last_req_sig_q;
  assign real_toggle_subset_word9_o = stalled_sig_q;
  assign real_toggle_subset_word10_o = signature_q;
  assign real_toggle_subset_word11_o = {31'd0, link_o_cast[0].ready_and_rev};
  assign real_toggle_subset_word12_o = {31'd0, link_i_cast[1].ready_and_rev};
  assign real_toggle_subset_word13_o = {31'd0, link_i_cast[2].ready_and_rev};
  assign real_toggle_subset_word14_o = {16'd0, link_o_cast[1].data};
  assign real_toggle_subset_word15_o = {16'd0, link_o_cast[2].data};
  assign real_toggle_subset_word16_o = cycle_count_o;
  assign real_toggle_subset_word17_o = cfg_signature_o;

  assign focused_wave_word0_o = {31'd0, local_send_w};
  assign focused_wave_word1_o = {31'd0, local_fire_w};
  assign focused_wave_word2_o = {31'd0, west_fire_w};
  assign focused_wave_word3_o = {31'd0, east_fire_w};
  assign focused_wave_word4_o = {16'd0, flit_w};
  assign focused_wave_word5_o = {31'd0, choose_dest(lfsr_q)};
  assign focused_wave_word6_o = lfsr_q;
  assign focused_wave_word7_o = progress_signature_o;

endmodule
