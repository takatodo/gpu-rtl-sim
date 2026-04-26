// Copyright lowRISC contributors (OpenTitan project).
// SPDX-License-Identifier: Apache-2.0
//
// GPU-oriented standalone coverage target for tlul_fifo_sync.
// Configuration comes from primary inputs so sim-accel bench can seed it via init-file.

`include "tlul_fifo_sync_gpu_cov_ports.svh"

module tlul_fifo_sync_gpu_cov_core (
  input  logic        clk_i,
  input  logic        rst_ni,
  `TLUL_FIFO_SYNC_GPU_COV_PORTS,
  output logic        reset_like_o
);
  import tlul_pkg::*;

  localparam logic [2:0] ResetPhase   = 3'd0;
  localparam logic [2:0] WarmupPhase  = 3'd1;
  localparam logic [2:0] TrafficPhase = 3'd2;
  localparam logic [2:0] DrainPhase   = 3'd3;
  localparam logic [2:0] DonePhase    = 3'd4;
  localparam logic [31:0] WarmupCycles = 32'd2;
  localparam int unsigned QueueDepth = 32;
  localparam int unsigned QueueIndexWidth = 5;
  localparam int unsigned TraceDepth = 32;
  localparam int unsigned TraceIndexWidth = 5;
  localparam int unsigned TogglePointCount = 96;
  localparam int unsigned RealToggleSubsetPointCount = 538;

  tl_h2d_t tl_h_i;
  tl_d2h_t tl_h_o;
  tl_h2d_t tl_d_o;
  tl_d2h_t tl_d_i;

  logic [0:0] spare_req_i;
  logic [0:0] spare_req_o;
  logic [0:0] spare_rsp_i;
  logic [0:0] spare_rsp_o;

  logic [31:0] cycle_count_q;
  logic [31:0] cycle_count_d;
  logic        bootstrapped_q;
  logic        bootstrapped_d;
  logic [2:0]  phase_q;
  logic [2:0]  phase_d;
  logic [31:0] reset_cycles_remaining_q;
  logic [31:0] reset_cycles_remaining_d;
  logic [31:0] warmup_cycles_remaining_q;
  logic [31:0] warmup_cycles_remaining_d;
  logic [31:0] traffic_cycles_remaining_q;
  logic [31:0] traffic_cycles_remaining_d;
  logic [31:0] drain_cycles_remaining_q;
  logic [31:0] drain_cycles_remaining_d;
  logic [31:0] rand_state_q;
  logic [31:0] rand_state_d;
  logic        req_pending_valid_q;
  logic        req_pending_valid_d;
  tl_a_op_e    req_pending_opcode_q;
  tl_a_op_e    req_pending_opcode_d;
  logic [2:0]  req_pending_param_q;
  logic [2:0]  req_pending_param_d;
  logic [top_pkg::TL_SZW-1:0] req_pending_size_q;
  logic [top_pkg::TL_SZW-1:0] req_pending_size_d;
  logic [top_pkg::TL_AIW-1:0] req_pending_source_q;
  logic [top_pkg::TL_AIW-1:0] req_pending_source_d;
  logic [top_pkg::TL_AW-1:0] req_pending_address_q;
  logic [top_pkg::TL_AW-1:0] req_pending_address_d;
  logic [top_pkg::TL_DBW-1:0] req_pending_mask_q;
  logic [top_pkg::TL_DBW-1:0] req_pending_mask_d;
  logic [top_pkg::TL_DW-1:0] req_pending_data_q;
  logic [top_pkg::TL_DW-1:0] req_pending_data_d;
  logic [0:0] req_pending_spare_q;
  logic [0:0] req_pending_spare_d;
  logic [31:0] trace_step_q;
  logic [31:0] trace_step_d;
  logic [31:0] direct_trace_step_q;
  logic [31:0] direct_trace_step_d;
  logic [31:0] trace_step_count_q;
  logic [1:0] trace_req_opcode_q [TraceDepth];
  logic [2:0] trace_req_param_q [TraceDepth];
  logic [top_pkg::TL_SZW-1:0] trace_req_size_q [TraceDepth];
  logic [top_pkg::TL_AW-1:0] trace_req_address_q [TraceDepth];
  logic [top_pkg::TL_DBW-1:0] trace_req_mask_q [TraceDepth];
  logic [top_pkg::TL_DW-1:0] trace_req_data_q [TraceDepth];
  logic [top_pkg::TL_AIW-1:0] trace_req_source_q [TraceDepth];
  logic [31:0] trace_req_burst_len_q [TraceDepth];
  logic [0:0] trace_req_spare_q [TraceDepth];
  logic trace_rsp_valid_q [TraceDepth];
  logic [2:0] trace_rsp_opcode_q [TraceDepth];
  logic [top_pkg::TL_SZW-1:0] trace_rsp_size_q [TraceDepth];
  logic [top_pkg::TL_AIW-1:0] trace_rsp_source_q [TraceDepth];
  logic trace_rsp_has_data_q [TraceDepth];
  logic [top_pkg::TL_DW-1:0] trace_rsp_data_q [TraceDepth];
  logic [31:0] trace_rsp_delay_q [TraceDepth];
  logic trace_rsp_error_q [TraceDepth];
  logic [1:0] trace_host_ready_mode_q [TraceDepth];
  logic [1:0] trace_device_ready_mode_q [TraceDepth];
  logic [1:0] trace_req_valid_mode_q [TraceDepth];
  logic req_pending_trace_active_q;
  logic req_pending_trace_active_d;
  logic [TraceIndexWidth-1:0] req_pending_trace_index_q;
  logic [TraceIndexWidth-1:0] req_pending_trace_index_d;
  logic req_forward_trace_active_q;
  logic req_forward_trace_active_d;
  logic [TraceIndexWidth-1:0] req_forward_trace_index_q;
  logic [TraceIndexWidth-1:0] req_forward_trace_index_d;
  logic req_burst_trace_active_q;
  logic req_burst_trace_active_d;
  logic [TraceIndexWidth-1:0] req_burst_trace_index_q;
  logic [TraceIndexWidth-1:0] req_burst_trace_index_d;
  logic [31:0] req_burst_remaining_q;
  logic [31:0] req_burst_remaining_d;
  tl_a_op_e    req_burst_opcode_q;
  tl_a_op_e    req_burst_opcode_d;
  logic [2:0]  req_burst_param_q;
  logic [2:0]  req_burst_param_d;
  logic [top_pkg::TL_SZW-1:0] req_burst_size_q;
  logic [top_pkg::TL_SZW-1:0] req_burst_size_d;
  logic [top_pkg::TL_AIW-1:0] req_burst_source_q;
  logic [top_pkg::TL_AIW-1:0] req_burst_source_d;
  logic [top_pkg::TL_AW-1:0] req_burst_address_q;
  logic [top_pkg::TL_AW-1:0] req_burst_address_d;
  logic [top_pkg::TL_DBW-1:0] req_burst_mask_q;
  logic [top_pkg::TL_DBW-1:0] req_burst_mask_d;
  logic [top_pkg::TL_DW-1:0] req_burst_data_q;
  logic [top_pkg::TL_DW-1:0] req_burst_data_d;
  logic [0:0] req_burst_spare_q;
  logic [0:0] req_burst_spare_d;
  logic       rsp_pending_valid_q;
  logic       rsp_pending_valid_d;
  logic [2:0] rsp_pending_opcode_q;
  logic [2:0] rsp_pending_opcode_d;
  logic [2:0] rsp_pending_param_q;
  logic [2:0] rsp_pending_param_d;
  logic [top_pkg::TL_SZW-1:0] rsp_pending_size_q;
  logic [top_pkg::TL_SZW-1:0] rsp_pending_size_d;
  logic [top_pkg::TL_AIW-1:0] rsp_pending_source_q;
  logic [top_pkg::TL_AIW-1:0] rsp_pending_source_d;
  logic [top_pkg::TL_DIW-1:0] rsp_pending_sink_q;
  logic [top_pkg::TL_DIW-1:0] rsp_pending_sink_d;
  logic [top_pkg::TL_DW-1:0] rsp_pending_data_q;
  logic [top_pkg::TL_DW-1:0] rsp_pending_data_d;
  logic       rsp_pending_error_q;
  logic       rsp_pending_error_d;
  logic [0:0] rsp_pending_spare_q;
  logic [0:0] rsp_pending_spare_d;
  logic [top_pkg::TL_SZW-1:0] rsp_size_queue_q [QueueDepth];
  logic [top_pkg::TL_SZW-1:0] rsp_size_queue_d [QueueDepth];
  logic [top_pkg::TL_AIW-1:0] rsp_source_queue_q [QueueDepth];
  logic [top_pkg::TL_AIW-1:0] rsp_source_queue_d [QueueDepth];
  tl_a_op_e rsp_req_opcode_queue_q [QueueDepth];
  tl_a_op_e rsp_req_opcode_queue_d [QueueDepth];
  logic [top_pkg::TL_AW-1:0] rsp_req_address_queue_q [QueueDepth];
  logic [top_pkg::TL_AW-1:0] rsp_req_address_queue_d [QueueDepth];
  logic [top_pkg::TL_DW-1:0] rsp_req_data_queue_q [QueueDepth];
  logic [top_pkg::TL_DW-1:0] rsp_req_data_queue_d [QueueDepth];
  logic [31:0] rsp_delay_queue_q [QueueDepth];
  logic [31:0] rsp_delay_queue_d [QueueDepth];
  logic rsp_trace_valid_queue_q [QueueDepth];
  logic rsp_trace_valid_queue_d [QueueDepth];
  logic [2:0] rsp_trace_opcode_queue_q [QueueDepth];
  logic [2:0] rsp_trace_opcode_queue_d [QueueDepth];
  logic [top_pkg::TL_SZW-1:0] rsp_trace_size_queue_q [QueueDepth];
  logic [top_pkg::TL_SZW-1:0] rsp_trace_size_queue_d [QueueDepth];
  logic [top_pkg::TL_AIW-1:0] rsp_trace_source_queue_q [QueueDepth];
  logic [top_pkg::TL_AIW-1:0] rsp_trace_source_queue_d [QueueDepth];
  logic rsp_trace_has_data_queue_q [QueueDepth];
  logic rsp_trace_has_data_queue_d [QueueDepth];
  logic [top_pkg::TL_DW-1:0] rsp_trace_data_queue_q [QueueDepth];
  logic [top_pkg::TL_DW-1:0] rsp_trace_data_queue_d [QueueDepth];
  logic rsp_trace_error_queue_q [QueueDepth];
  logic rsp_trace_error_queue_d [QueueDepth];
  logic [1:0] rsp_trace_host_ready_mode_queue_q [QueueDepth];
  logic [1:0] rsp_trace_host_ready_mode_queue_d [QueueDepth];
  logic [31:0] rsp_head_q;
  logic [31:0] rsp_head_d;
  logic [31:0] rsp_tail_q;
  logic [31:0] rsp_tail_d;
  logic [31:0] rsp_count_q;
  logic [31:0] rsp_count_d;
  logic [31:0] host_req_accepted_q;
  logic [31:0] host_req_accepted_d;
  logic [31:0] device_req_accepted_q;
  logic [31:0] device_req_accepted_d;
  logic [31:0] device_rsp_accepted_q;
  logic [31:0] device_rsp_accepted_d;
  logic [31:0] host_rsp_accepted_q;
  logic [31:0] host_rsp_accepted_d;
  logic [31:0] rsp_queue_overflow_q;
  logic [31:0] rsp_queue_overflow_d;
  logic [31:0] progress_signature_q;
  logic [31:0] progress_signature_d;

  logic [TogglePointCount-1:0] toggle_curr_w;
  logic [31:0] toggle_prev_word0_q;
  logic [31:0] toggle_prev_word0_d;
  logic [31:0] toggle_prev_word1_q;
  logic [31:0] toggle_prev_word1_d;
  logic [31:0] toggle_prev_word2_q;
  logic [31:0] toggle_prev_word2_d;
  logic [31:0] toggle_hit_word0_q;
  logic [31:0] toggle_hit_word0_d;
  logic [31:0] toggle_hit_word1_q;
  logic [31:0] toggle_hit_word1_d;
  logic [31:0] toggle_hit_word2_q;
  logic [31:0] toggle_hit_word2_d;
  logic [15:0] real_toggle_subset_curr_chunk0_w;
  logic [15:0] real_toggle_subset_curr_chunk1_w;
  logic [15:0] real_toggle_subset_curr_chunk2_w;
  logic [15:0] real_toggle_subset_curr_chunk3_w;
  logic [15:0] real_toggle_subset_curr_chunk4_w;
  logic [15:0] real_toggle_subset_curr_chunk5_w;
  logic [15:0] real_toggle_subset_curr_chunk6_w;
  logic [15:0] real_toggle_subset_curr_chunk7_w;
  logic [15:0] real_toggle_subset_curr_chunk8_w;
  logic [15:0] real_toggle_subset_curr_chunk9_w;
  logic [15:0] real_toggle_subset_curr_chunk10_w;
  logic [15:0] real_toggle_subset_curr_chunk11_w;
  logic [15:0] real_toggle_subset_curr_chunk12_w;
  logic [15:0] real_toggle_subset_curr_chunk13_w;
  logic [15:0] real_toggle_subset_curr_chunk14_w;
  logic [15:0] real_toggle_subset_curr_chunk15_w;
  logic [15:0] real_toggle_subset_curr_chunk16_w;
  logic [15:0] real_toggle_subset_curr_chunk17_w;
  logic [15:0] real_toggle_subset_prev_chunk0_q;
  logic [15:0] real_toggle_subset_prev_chunk1_q;
  logic [15:0] real_toggle_subset_prev_chunk2_q;
  logic [15:0] real_toggle_subset_prev_chunk3_q;
  logic [15:0] real_toggle_subset_prev_chunk4_q;
  logic [15:0] real_toggle_subset_prev_chunk5_q;
  logic [15:0] real_toggle_subset_prev_chunk6_q;
  logic [15:0] real_toggle_subset_prev_chunk7_q;
  logic [15:0] real_toggle_subset_prev_chunk8_q;
  logic [15:0] real_toggle_subset_prev_chunk9_q;
  logic [15:0] real_toggle_subset_prev_chunk10_q;
  logic [15:0] real_toggle_subset_prev_chunk11_q;
  logic [15:0] real_toggle_subset_prev_chunk12_q;
  logic [15:0] real_toggle_subset_prev_chunk13_q;
  logic [15:0] real_toggle_subset_prev_chunk14_q;
  logic [15:0] real_toggle_subset_prev_chunk15_q;
  logic [15:0] real_toggle_subset_prev_chunk16_q;
  logic [15:0] real_toggle_subset_prev_chunk17_q;
  logic [15:0] real_toggle_subset_prev_chunk0_d;
  logic [15:0] real_toggle_subset_prev_chunk1_d;
  logic [15:0] real_toggle_subset_prev_chunk2_d;
  logic [15:0] real_toggle_subset_prev_chunk3_d;
  logic [15:0] real_toggle_subset_prev_chunk4_d;
  logic [15:0] real_toggle_subset_prev_chunk5_d;
  logic [15:0] real_toggle_subset_prev_chunk6_d;
  logic [15:0] real_toggle_subset_prev_chunk7_d;
  logic [15:0] real_toggle_subset_prev_chunk8_d;
  logic [15:0] real_toggle_subset_prev_chunk9_d;
  logic [15:0] real_toggle_subset_prev_chunk10_d;
  logic [15:0] real_toggle_subset_prev_chunk11_d;
  logic [15:0] real_toggle_subset_prev_chunk12_d;
  logic [15:0] real_toggle_subset_prev_chunk13_d;
  logic [15:0] real_toggle_subset_prev_chunk14_d;
  logic [15:0] real_toggle_subset_prev_chunk15_d;
  logic [15:0] real_toggle_subset_prev_chunk16_d;
  logic [15:0] real_toggle_subset_prev_chunk17_d;
  logic [31:0] real_toggle_subset_hit_word0_q;
  logic [31:0] real_toggle_subset_hit_word0_d;
  logic [31:0] real_toggle_subset_hit_word1_q;
  logic [31:0] real_toggle_subset_hit_word1_d;
  logic [31:0] real_toggle_subset_hit_word2_q;
  logic [31:0] real_toggle_subset_hit_word2_d;
  logic [31:0] real_toggle_subset_hit_word3_q;
  logic [31:0] real_toggle_subset_hit_word3_d;
  logic [31:0] real_toggle_subset_hit_word4_q;
  logic [31:0] real_toggle_subset_hit_word4_d;
  logic [31:0] real_toggle_subset_hit_word5_q;
  logic [31:0] real_toggle_subset_hit_word5_d;
  logic [31:0] real_toggle_subset_hit_word6_q;
  logic [31:0] real_toggle_subset_hit_word6_d;
  logic [31:0] real_toggle_subset_hit_word7_q;
  logic [31:0] real_toggle_subset_hit_word7_d;
  logic [31:0] real_toggle_subset_hit_word8_q;
  logic [31:0] real_toggle_subset_hit_word8_d;
  logic [31:0] real_toggle_subset_hit_word9_q;
  logic [31:0] real_toggle_subset_hit_word9_d;
  logic [31:0] real_toggle_subset_hit_word10_q;
  logic [31:0] real_toggle_subset_hit_word10_d;
  logic [31:0] real_toggle_subset_hit_word11_q;
  logic [31:0] real_toggle_subset_hit_word11_d;
  logic [31:0] real_toggle_subset_hit_word12_q;
  logic [31:0] real_toggle_subset_hit_word12_d;
  logic [31:0] real_toggle_subset_hit_word13_q;
  logic [31:0] real_toggle_subset_hit_word13_d;
  logic [31:0] real_toggle_subset_hit_word14_q;
  logic [31:0] real_toggle_subset_hit_word14_d;
  logic [31:0] real_toggle_subset_hit_word15_q;
  logic [31:0] real_toggle_subset_hit_word15_d;
  logic [31:0] real_toggle_subset_hit_word16_q;
  logic [31:0] real_toggle_subset_hit_word16_d;
  logic [31:0] real_toggle_subset_hit_word17_q;
  logic [31:0] real_toggle_subset_hit_word17_d;

  logic [31:0] batch_length_cfg;
  logic [31:0] req_valid_pct_cfg;
  logic [31:0] rsp_valid_pct_cfg;
  logic [31:0] host_d_ready_pct_cfg;
  logic [31:0] device_a_ready_pct_cfg;
  logic [31:0] put_full_pct_cfg;
  logic [31:0] put_partial_pct_cfg;
  logic [31:0] req_fill_target_cfg;
  logic [31:0] req_burst_len_max_cfg;
  logic [31:0] req_family_cfg;
  logic [31:0] req_address_mode_cfg;
  logic [31:0] req_data_mode_cfg;
  logic [31:0] req_data_hi_xor_cfg;
  logic [31:0] access_ack_data_pct_cfg;
  logic [31:0] rsp_error_pct_cfg;
  logic [31:0] rsp_fill_target_cfg;
  logic [31:0] rsp_delay_max_cfg;
  logic [31:0] rsp_family_cfg;
  logic [31:0] rsp_delay_mode_cfg;
  logic [31:0] rsp_data_mode_cfg;
  logic [31:0] rsp_data_hi_xor_cfg;
  logic [31:0] reset_cycles_cfg;
  logic [31:0] drain_cycles_cfg;
  logic [31:0] seed_cfg;
  logic [31:0] address_base_cfg;
  logic [31:0] address_mask_cfg;
  logic [31:0] source_mask_cfg;
  logic [1:0]  direct_trace_req_opcode_w;
  logic [2:0]  direct_trace_req_param_w;
  logic [top_pkg::TL_SZW-1:0] direct_trace_req_size_w;
  logic [top_pkg::TL_AW-1:0] direct_trace_req_address_w;
  logic [top_pkg::TL_DBW-1:0] direct_trace_req_mask_w;
  logic [top_pkg::TL_DW-1:0] direct_trace_req_data_w;
  logic [top_pkg::TL_AIW-1:0] direct_trace_req_source_w;
  logic [31:0] direct_trace_req_burst_len_w;
  logic [0:0]  direct_trace_req_spare_w;
  logic        direct_trace_rsp_valid_w;
  logic [2:0]  direct_trace_rsp_opcode_w;
  logic [top_pkg::TL_SZW-1:0] direct_trace_rsp_size_w;
  logic [top_pkg::TL_AIW-1:0] direct_trace_rsp_source_w;
  logic        direct_trace_rsp_has_data_w;
  logic [2:0]  direct_trace_rsp_opcode_eff_w;
  logic [top_pkg::TL_DW-1:0] direct_trace_rsp_data_w;
  logic        direct_trace_rsp_data_nonzero_w;
  logic [31:0] direct_trace_rsp_delay_w;
  logic        direct_trace_rsp_error_w;
  logic [1:0]  direct_trace_host_ready_mode_w;
  logic [1:0]  direct_trace_device_ready_mode_w;
  logic [1:0]  direct_trace_req_valid_mode_w;

  logic [2:0]  phase_code_w;
  logic [2:0]  phase_steady_w;
  logic [31:0] reset_cycles_remaining_w;
  logic [31:0] warmup_cycles_remaining_w;
  logic [31:0] reset_cycles_remaining_steady_w;
  logic [31:0] warmup_cycles_remaining_steady_w;
  logic [31:0] traffic_cycles_remaining_steady_w;
  logic [31:0] drain_cycles_remaining_steady_w;
  logic        reset_like_w;
  logic        traffic_phase_w;
  logic        response_phase_w;

  logic [31:0] rand_seed_w;
  logic [31:0] rand_req_w;
  logic [31:0] rand_rsp_w;
  logic [31:0] rand_host_ready_w;
  logic [31:0] rand_device_ready_w;
  logic [31:0] rand_next_w;
  logic        req_valid_gate_w;
  logic        rsp_valid_gate_w;
  logic        host_ready_gate_w;
  logic        device_ready_gate_w;
  logic        traffic_front_half_w;
  logic        traffic_back_half_w;
  logic        req_fill_force_w;
  logic        rsp_backlog_force_w;
  logic        req_fifo_fill_hold_w;
  logic        rsp_fifo_fill_hold_w;
  logic        req_fill_release_w;
  logic        rsp_fill_release_w;
  logic        put_full_gate_w;
  logic        put_partial_gate_w;
  logic        rsp_data_gate_w;
  logic        rsp_error_gate_w;
  logic        host_d_ready_w;
  logic        device_a_ready_w;
  logic        host_d_ready_base_w;
  logic        device_a_ready_base_w;
  logic        req_handshake_w;
  logic        device_req_accept_w;
  logic        device_req_handshake_w;
  logic        device_rsp_accept_w;
  logic        rsp_handshake_w;
  logic        host_rsp_accept_w;
  logic        host_rsp_handshake_w;
  logic        overflow_event_w;
  logic        generic_rsp_queue_push_w;
  logic        drain_busy_w;
  logic        req_spawn_w;
  logic        rsp_spawn_w;
  logic        direct_trace_mode_w;
  logic        direct_trace_active_w;
  logic        direct_trace_done_w;
  logic [31:0] direct_trace_start_cycle_w;
  logic [31:0] trace_step_active_w;
  logic [TraceIndexWidth-1:0] trace_curr_index_w;
  logic        direct_req_drive_w;
  logic        direct_rsp_drive_w;
  logic        direct_req_step_complete_w;
  logic        direct_rsp_step_complete_w;
  logic        direct_trace_step_advance_w;
  logic        direct_req_done_q;
  logic        direct_req_done_d;
  logic        direct_rsp_done_q;
  logic        direct_rsp_done_d;
  logic [31:0] direct_rsp_delay_q;
  logic [31:0] direct_rsp_delay_d;
  logic        direct_rsp_replay_valid_w;
  logic [2:0]  direct_rsp_replay_opcode_bits_w;
  logic [top_pkg::TL_SZW-1:0] direct_rsp_replay_size_w;
  logic [top_pkg::TL_AIW-1:0] direct_rsp_replay_source_w;
  logic [top_pkg::TL_DW-1:0] direct_rsp_replay_data_w;
  logic        direct_rsp_replay_error_w;
  logic        direct_host_ready_w;
  logic        direct_device_ready_w;
  logic        direct_rsp_buffer_hold_w;
  logic        direct_rsp_hold_valid_q;
  logic        direct_rsp_hold_valid_d;
  logic [2:0]  direct_rsp_hold_opcode_q;
  logic [2:0]  direct_rsp_hold_opcode_d;
  logic [top_pkg::TL_SZW-1:0] direct_rsp_hold_size_q;
  logic [top_pkg::TL_SZW-1:0] direct_rsp_hold_size_d;
  logic [top_pkg::TL_AIW-1:0] direct_rsp_hold_source_q;
  logic [top_pkg::TL_AIW-1:0] direct_rsp_hold_source_d;
  logic [top_pkg::TL_DW-1:0] direct_rsp_hold_data_q;
  logic [top_pkg::TL_DW-1:0] direct_rsp_hold_data_d;
  logic        direct_rsp_hold_error_q;
  logic        direct_rsp_hold_error_d;
  logic        trace_live_w;
  logic        trace_step_remaining_w;
  logic        trace_req_active_w;
  logic        req_trace_replay_w;
  logic [TraceIndexWidth-1:0] req_trace_index_w;
  logic        rsp_trace_override_valid_w;
  logic        rsp_trace_head_valid_w;
  logic        rsp_trace_replay_w;
  logic        rsp_trace_valid_w;
  logic        rsp_trace_payload_override_w;
  logic        rsp_trace_has_data_w;
  logic [TraceIndexWidth-1:0] rsp_trace_replay_index_w;
  logic [top_pkg::TL_SZW-1:0] rsp_trace_size_w;
  logic [top_pkg::TL_AIW-1:0] rsp_trace_source_w;
  logic        trace_host_ready_default_w;
  logic        trace_device_ready_default_w;
  logic [1:0]  trace_host_ready_mode_w;
  logic [1:0]  trace_device_ready_mode_w;
  logic [1:0]  trace_req_valid_mode_w;
  logic        trace_req_skip_w;
  logic        trace_req_fill_hold_w;
  logic        trace_rsp_fill_hold_w;
  logic        req_trace_queue_active_w;
  logic [TraceIndexWidth-1:0] req_trace_queue_index_w;
  logic        rsp_trace_enqueue_active_w;
  logic [TraceIndexWidth-1:0] rsp_trace_enqueue_index_w;
  tl_a_op_e    req_opcode_spawn_w;
  logic [2:0]  req_param_spawn_w;
  logic [top_pkg::TL_SZW-1:0] req_size_spawn_w;
  logic [top_pkg::TL_AIW-1:0] req_source_spawn_w;
  logic [top_pkg::TL_AW-1:0] req_address_spawn_w;
  logic [top_pkg::TL_AW-1:0] req_address_family_w;
  logic [top_pkg::TL_DBW-1:0] req_mask_spawn_w;
  logic [top_pkg::TL_DW-1:0] req_data_spawn_w;
  logic [0:0] req_spare_spawn_w;
  logic [2:0]  rsp_opcode_spawn_bits_w;
  logic [2:0]  rsp_param_spawn_w;
  logic [top_pkg::TL_SZW-1:0] rsp_size_spawn_w;
  logic [top_pkg::TL_AIW-1:0] rsp_source_spawn_w;
  logic [top_pkg::TL_DIW-1:0] rsp_sink_spawn_w;
  logic [top_pkg::TL_DW-1:0] rsp_data_spawn_w;
  logic        rsp_error_spawn_w;
  logic [0:0]  rsp_spare_spawn_w;
  logic [31:0] req_data_pattern_w;
  logic [31:0] rsp_data_pattern_w;
  logic [15:0] req_data_upper_fill_w;
  logic [15:0] rsp_data_upper_fill_w;
  logic [2:0]  rsp_active_opcode_bits_w;
  logic [2:0]  rsp_trace_opcode_bits_w;
  logic [2:0]  rsp_family_opcode_bits_w;
  logic        host_rsp_passthrough_observed_w;
  logic [2:0]  host_rsp_observed_opcode_bits_w;
  logic [top_pkg::TL_DW-1:0] host_rsp_observed_data_w;
  tl_a_user_t direct_req_user_w;
  tl_d_user_t direct_rsp_user_w;
  tl_a_user_t req_user_active_w;
  tl_d_user_t rsp_user_active_w;
  logic [31:0] focused_wave_pack_a_w;
  logic [31:0] focused_wave_pack_b_w;
  logic [31:0] focused_wave_word0_q;
  logic [31:0] focused_wave_word1_q;
  logic [31:0] focused_wave_word2_q;
  logic [31:0] focused_wave_word3_q;
  logic [31:0] focused_wave_word4_q;
  logic [31:0] focused_wave_word5_q;
  logic [31:0] focused_wave_word6_q;
  logic [31:0] focused_wave_word7_q;
  logic [31:0] focused_metric_word0_q;
  logic [31:0] focused_metric_word1_q;
  logic [1:0]  max_reqfifo_depth_q;
  logic [1:0]  max_reqfifo_depth_d;
  logic [1:0]  max_rspfifo_depth_q;
  logic [1:0]  max_rspfifo_depth_d;
  logic [7:0]  req_handshake_seen_q;
  logic [7:0]  req_handshake_seen_d;
  logic [7:0]  rsp_handshake_seen_q;
  logic [7:0]  rsp_handshake_seen_d;
  logic [7:0]  direct_trace_active_seen_q;
  logic [7:0]  direct_trace_active_seen_d;
  logic [7:0]  direct_req_drive_seen_q;
  logic [7:0]  direct_req_drive_seen_d;
  logic [7:0]  direct_req_ready_seen_q;
  logic [7:0]  direct_req_ready_seen_d;
  logic [7:0]  direct_req_handshake_seen_q;
  logic [7:0]  direct_req_handshake_seen_d;
  logic [7:0]  direct_rsp_drive_seen_q;
  logic [7:0]  direct_rsp_drive_seen_d;
  logic [7:0]  direct_rsp_handshake_seen_q;
  logic [7:0]  direct_rsp_handshake_seen_d;
  logic [7:0]  trace_req_active_seen_q;
  logic [7:0]  trace_req_active_seen_d;
  logic [7:0]  req_spawn_seen_q;
  logic [7:0]  req_spawn_seen_d;
  logic [7:0]  req_ready_seen_q;
  logic [7:0]  req_ready_seen_d;
  logic [7:0]  req_blocked_seen_q;
  logic [7:0]  req_blocked_seen_d;
  logic [7:0]  reqfifo_full_seen_q;
  logic [7:0]  reqfifo_full_seen_d;
  logic [7:0]  reqfifo_under_rst_seen_q;
  logic [7:0]  reqfifo_under_rst_seen_d;
  logic [7:0]  device_a_ready_seen_q;
  logic [7:0]  device_a_ready_seen_d;
  logic [7:0]  device_a_valid_seen_q;
  logic [7:0]  device_a_valid_seen_d;
  logic [7:0]  device_ready_force_high_seen_q;
  logic [7:0]  device_ready_force_high_seen_d;
  logic [7:0]  trace_req_fill_hold_seen_q;
  logic [7:0]  trace_req_fill_hold_seen_d;
  logic [7:0]  trace_host_ready_default_seen_q;
  logic [7:0]  trace_host_ready_default_seen_d;
  logic [7:0]  trace_rsp_fill_hold_seen_q;
  logic [7:0]  trace_rsp_fill_hold_seen_d;
  logic [7:0]  host_d_ready_seen_q;
  logic [7:0]  host_d_ready_seen_d;
  logic [7:0]  host_d_valid_seen_q;
  logic [7:0]  host_d_valid_seen_d;
  logic [7:0]  device_rsp_ackdata_seen_q;
  logic [7:0]  device_rsp_ackdata_seen_d;
  logic [7:0]  host_rsp_ackdata_seen_q;
  logic [7:0]  host_rsp_ackdata_seen_d;
  logic [7:0]  host_rsp_handshake_seen_q;
  logic [7:0]  host_rsp_handshake_seen_d;
  logic [7:0]  device_rsp_payload_upper_seen_q;
  logic [7:0]  device_rsp_payload_upper_seen_d;
  logic [7:0]  host_rsp_payload_upper_seen_q;
  logic [7:0]  host_rsp_payload_upper_seen_d;
  logic [7:0]  device_rsp_payload_upper_accept_seen_q;
  logic [7:0]  device_rsp_payload_upper_accept_seen_d;
  logic [7:0]  host_rsp_payload_upper_accept_seen_q;
  logic [7:0]  host_rsp_payload_upper_accept_seen_d;
  logic [7:0]  host_raw_rsp_ackdata_seen_q;
  logic [7:0]  host_raw_rsp_ackdata_seen_d;
  logic [7:0]  host_raw_rsp_payload_upper_seen_q;
  logic [7:0]  host_raw_rsp_payload_upper_seen_d;
  logic        first_device_rsp_seen_q;
  logic        first_device_rsp_seen_d;
  logic [2:0]  first_device_rsp_opcode_q;
  logic [2:0]  first_device_rsp_opcode_d;
  logic [15:0] first_device_rsp_data_upper_q;
  logic [15:0] first_device_rsp_data_upper_d;
  logic        first_host_rsp_seen_q;
  logic        first_host_rsp_seen_d;
  logic [2:0]  first_host_rsp_opcode_q;
  logic [2:0]  first_host_rsp_opcode_d;
  logic [15:0] first_host_rsp_data_upper_q;
  logic [15:0] first_host_rsp_data_upper_d;
  logic        last_device_rsp_seen_q;
  logic        last_device_rsp_seen_d;
  logic [2:0]  last_device_rsp_opcode_q;
  logic [2:0]  last_device_rsp_opcode_d;
  logic [top_pkg::TL_DW-1:0] last_device_rsp_data_q;
  logic [top_pkg::TL_DW-1:0] last_device_rsp_data_d;
  logic [2:0]  host_raw_rsp_opcode_or_q;
  logic [2:0]  host_raw_rsp_opcode_or_d;
  logic [7:0]  rsp_trace_override_seen_q;
  logic [7:0]  rsp_trace_override_seen_d;
  logic [7:0]  rsp_trace_head_valid_seen_q;
  logic [7:0]  rsp_trace_head_valid_seen_d;
  logic [7:0]  rsp_trace_has_data_seen_q;
  logic [7:0]  rsp_trace_has_data_seen_d;
  logic [7:0]  rsp_spawn_has_data_seen_q;
  logic [7:0]  rsp_spawn_has_data_seen_d;
  logic [7:0]  rsp_spawn_ackdata_seen_q;
  logic [7:0]  rsp_spawn_ackdata_seen_d;
  logic [2:0]  rsp_spawn_opcode_or_q;
  logic [2:0]  rsp_spawn_opcode_or_d;
  logic [2:0]  rsp_active_opcode_or_q;
  logic [2:0]  rsp_active_opcode_or_d;
  logic [2:0]  device_rsp_opcode_or_q;
  logic [2:0]  device_rsp_opcode_or_d;
  logic [2:0]  host_rsp_opcode_or_q;
  logic [2:0]  host_rsp_opcode_or_d;
  logic [7:0]  reqfifo_nonempty_seen_q;
  logic [7:0]  reqfifo_nonempty_seen_d;
  logic [7:0]  rspfifo_nonempty_seen_q;
  logic [7:0]  rspfifo_nonempty_seen_d;
  logic [15:0] a_data_mid_or_q;
  logic [15:0] a_data_mid_or_d;
  logic [19:0] a_address_window_or_q;
  logic [19:0] a_address_window_or_d;
  logic [15:0] device_d_data_low_or_q;
  logic [15:0] device_d_data_low_or_d;
  logic [15:0] device_d_data_upper_or_q;
  logic [15:0] device_d_data_upper_or_d;
  logic [15:0] d_data_low_or_q;
  logic [15:0] d_data_low_or_d;
  logic [15:0] a_data_upper_or_q;
  logic [15:0] a_data_upper_or_d;
  logic [15:0] d_data_upper_or_q;
  logic [15:0] d_data_upper_or_d;

  function automatic tl_a_op_e decode_trace_req_opcode(
    input logic [1:0] opcode_i
  );
    begin
      unique case (opcode_i)
        2'd1: decode_trace_req_opcode = PutPartialData;
        2'd2: decode_trace_req_opcode = Get;
        default: decode_trace_req_opcode = PutFullData;
      endcase
    end
  endfunction

  function automatic logic [7:0] sat_inc8(
    input logic [7:0] value_i,
    input logic       event_i
  );
    begin
      if (event_i && (value_i != 8'hff)) begin
        sat_inc8 = value_i + 8'd1;
      end else begin
        sat_inc8 = value_i;
      end
    end
  endfunction

  function automatic logic decode_gate_mode(
    input logic [2:0] mode_i,
    input logic [2:0] bits_i
  );
    begin
      unique case (mode_i)
        3'd0: decode_gate_mode = 1'b0;
        3'd1: decode_gate_mode = &bits_i;
        3'd2: decode_gate_mode = &bits_i[1:0];
        3'd3: decode_gate_mode = (bits_i[2] & bits_i[1]) | (&bits_i[1:0]);
        3'd4: decode_gate_mode = bits_i[2];
        3'd5: decode_gate_mode = bits_i[2] | (&bits_i[1:0]);
        3'd6: decode_gate_mode = bits_i[2] | bits_i[1];
        default: decode_gate_mode = 1'b1;
      endcase
    end
  endfunction

  function automatic logic apply_trace_bool_mode(
    input logic default_i,
    input logic [1:0] mode_i
  );
    begin
      unique case (mode_i)
        2'd1: apply_trace_bool_mode = 1'b0;
        2'd2: apply_trace_bool_mode = 1'b1;
        default: apply_trace_bool_mode = default_i;
      endcase
    end
  endfunction

  function automatic tl_a_user_t build_req_user(
    input tl_a_op_e opcode_i,
    input logic [2:0] param_i,
    input logic [top_pkg::TL_SZW-1:0] size_i,
    input logic [top_pkg::TL_AIW-1:0] source_i,
    input logic [top_pkg::TL_AW-1:0] address_i,
    input logic [top_pkg::TL_DBW-1:0] mask_i,
    input logic [top_pkg::TL_DW-1:0] data_i,
    input logic trace_active_i,
    input logic spare_i
  );
    tl_a_user_t user_w;
    tl_h2d_t req_w;
    logic [31:0] mix_w;
    begin
      mix_w = data_i
            ^ address_i
            ^ {24'd0, source_i, mask_i}
            ^ {29'd0, param_i}
            ^ {30'd0, size_i}
            ^ {31'd0, trace_active_i}
            ^ {31'd0, spare_i};
      user_w = tlul_pkg::TL_A_USER_DEFAULT;
      user_w.rsvd = mix_w[tlul_pkg::RsvdWidth-1:0] ^ {tlul_pkg::RsvdWidth{trace_active_i}};
      user_w.instr_type = mix_w[5]
          ? prim_mubi_pkg::MuBi4True
          : prim_mubi_pkg::MuBi4False;
      req_w = tlul_pkg::TL_H2D_DEFAULT;
      req_w.a_opcode = opcode_i;
      req_w.a_param = param_i;
      req_w.a_size = size_i;
      req_w.a_source = source_i;
      req_w.a_address = address_i;
      req_w.a_mask = mask_i;
      req_w.a_data = data_i;
      req_w.a_user = user_w;
      user_w.cmd_intg = mix_w[0]
          ? tlul_pkg::get_bad_cmd_intg(req_w)
          : tlul_pkg::get_cmd_intg(req_w);
      user_w.data_intg = mix_w[1]
          ? tlul_pkg::get_bad_data_intg(data_i)
          : tlul_pkg::get_data_intg(data_i);
      return user_w;
    end
  endfunction

  function automatic tl_d_user_t build_rsp_user(
    input tl_d_op_e opcode_i,
    input logic [2:0] param_i,
    input logic [top_pkg::TL_SZW-1:0] size_i,
    input logic [top_pkg::TL_AIW-1:0] source_i,
    input logic [top_pkg::TL_DIW-1:0] sink_i,
    input logic [top_pkg::TL_DW-1:0] data_i,
    input logic error_i,
    input logic trace_active_i,
    input logic spare_i
  );
    tl_d_user_t user_w;
    logic [31:0] mix_w;
    logic [tlul_pkg::D2HRspIntgWidth-1:0] rsp_mix_w;
    begin
      mix_w = data_i
            ^ {24'd0, source_i, sink_i}
            ^ {29'd0, param_i}
            ^ {30'd0, size_i}
            ^ {31'd0, opcode_i[0] ^ error_i}
            ^ {31'd0, trace_active_i}
            ^ {31'd0, spare_i};
      rsp_mix_w = mix_w[tlul_pkg::D2HRspIntgWidth-1:0]
                ^ {tlul_pkg::D2HRspIntgWidth{opcode_i[0] ^ size_i[0]}};
      user_w = tlul_pkg::TL_D_USER_DEFAULT;
      user_w.rsp_intg = mix_w[0] ? ~rsp_mix_w : rsp_mix_w;
      user_w.data_intg = mix_w[1]
          ? tlul_pkg::get_bad_data_intg(data_i)
          : tlul_pkg::get_data_intg(data_i);
      return user_w;
    end
  endfunction

  tlul_fifo_sync #(
    .ReqDepth(2),
    .RspDepth(2)
  ) dut (
    .clk_i,
    .rst_ni,
    .tl_h_i,
    .tl_h_o,
    .tl_d_o,
    .tl_d_i,
    .spare_req_i,
    .spare_req_o,
    .spare_rsp_i,
    .spare_rsp_o
  );

  assign cfg_signature_o = {31'd0, cfg_valid_i}
      ^ cfg_batch_length_i
      ^ cfg_req_valid_pct_i
      ^ cfg_rsp_valid_pct_i
      ^ cfg_host_d_ready_pct_i
      ^ cfg_device_a_ready_pct_i
      ^ cfg_put_full_pct_i
      ^ cfg_put_partial_pct_i
      ^ cfg_req_fill_target_i
      ^ cfg_req_burst_len_max_i
      ^ cfg_req_family_i
      ^ cfg_req_address_mode_i
      ^ cfg_req_data_mode_i
      ^ cfg_req_data_hi_xor_i
      ^ cfg_access_ack_data_pct_i
      ^ cfg_rsp_error_pct_i
      ^ cfg_rsp_fill_target_i
      ^ cfg_rsp_delay_max_i
      ^ cfg_rsp_family_i
      ^ cfg_rsp_delay_mode_i
      ^ cfg_rsp_data_mode_i
      ^ cfg_rsp_data_hi_xor_i
      ^ cfg_reset_cycles_i
      ^ cfg_drain_cycles_i
      ^ cfg_seed_i
      ^ cfg_address_base_i
      ^ cfg_address_mask_i
      ^ cfg_source_mask_i;

  assign batch_length_cfg = cfg_valid_i ? cfg_batch_length_i : 32'd256;
  assign req_valid_pct_cfg = cfg_valid_i ? cfg_req_valid_pct_i : 32'd65;
  assign rsp_valid_pct_cfg = cfg_valid_i ? cfg_rsp_valid_pct_i : 32'd70;
  assign host_d_ready_pct_cfg = cfg_valid_i ? cfg_host_d_ready_pct_i : 32'd75;
  assign device_a_ready_pct_cfg = cfg_valid_i ? cfg_device_a_ready_pct_i : 32'd80;
  assign put_full_pct_cfg = cfg_valid_i ? cfg_put_full_pct_i : 32'd34;
  assign put_partial_pct_cfg = cfg_valid_i ? cfg_put_partial_pct_i : 32'd33;
  assign req_fill_target_cfg = cfg_valid_i ? cfg_req_fill_target_i : 32'd2;
  assign req_burst_len_max_cfg = cfg_valid_i ? cfg_req_burst_len_max_i : 32'd0;
  assign req_family_cfg = cfg_valid_i ? cfg_req_family_i : 32'd0;
  assign req_address_mode_cfg = cfg_valid_i ? cfg_req_address_mode_i : 32'd0;
  assign req_data_mode_cfg = cfg_valid_i ? cfg_req_data_mode_i : 32'd0;
  assign req_data_hi_xor_cfg = cfg_valid_i ? cfg_req_data_hi_xor_i : 32'd0;
  assign access_ack_data_pct_cfg = cfg_valid_i ? cfg_access_ack_data_pct_i : 32'd50;
  assign rsp_error_pct_cfg = cfg_valid_i ? cfg_rsp_error_pct_i : 32'd10;
  assign rsp_fill_target_cfg = cfg_valid_i ? cfg_rsp_fill_target_i : 32'd2;
  assign rsp_delay_max_cfg = cfg_valid_i ? cfg_rsp_delay_max_i : 32'd4;
  assign rsp_family_cfg = cfg_valid_i ? cfg_rsp_family_i : 32'd0;
  assign rsp_delay_mode_cfg = cfg_valid_i ? cfg_rsp_delay_mode_i : 32'd0;
  assign rsp_data_mode_cfg = cfg_valid_i ? cfg_rsp_data_mode_i : 32'd0;
  assign rsp_data_hi_xor_cfg = cfg_valid_i ? cfg_rsp_data_hi_xor_i : 32'd0;
  assign reset_cycles_cfg = cfg_valid_i ? cfg_reset_cycles_i : 32'd4;
  assign drain_cycles_cfg = (cfg_valid_i ? cfg_drain_cycles_i : 32'd16);
  assign seed_cfg = cfg_valid_i ? cfg_seed_i : 32'd1;
  assign address_base_cfg = (cfg_valid_i ? cfg_address_base_i : 32'd0);
  assign address_mask_cfg = (cfg_valid_i ? cfg_address_mask_i : 32'h0000_0ffc);
  assign source_mask_cfg = (cfg_valid_i ? cfg_source_mask_i : ((32'd1 << top_pkg::TL_AIW) - 1));

  assign direct_trace_mode_w = (trace_step_count_q != 32'd0);
  assign direct_trace_start_cycle_w = reset_cycles_cfg + WarmupCycles;
  assign trace_step_active_w =
      direct_trace_mode_w ? direct_trace_step_q : trace_step_q;
  assign trace_curr_index_w = trace_step_active_w[TraceIndexWidth-1:0];
  assign direct_trace_req_opcode_w = trace_req_opcode_q[trace_curr_index_w];
  assign direct_trace_req_param_w = trace_req_param_q[trace_curr_index_w];
  assign direct_trace_req_size_w = trace_req_size_q[trace_curr_index_w];
  assign direct_trace_req_address_w = trace_req_address_q[trace_curr_index_w];
  assign direct_trace_req_mask_w = trace_req_mask_q[trace_curr_index_w];
  assign direct_trace_req_data_w = trace_req_data_q[trace_curr_index_w];
  assign direct_trace_req_source_w = trace_req_source_q[trace_curr_index_w];
  assign direct_trace_req_burst_len_w = trace_req_burst_len_q[trace_curr_index_w];
  assign direct_trace_req_spare_w = trace_req_spare_q[trace_curr_index_w];
  assign direct_trace_rsp_valid_w = trace_rsp_valid_q[trace_curr_index_w];
  assign direct_trace_rsp_opcode_w = trace_rsp_opcode_q[trace_curr_index_w];
  assign direct_trace_rsp_size_w = trace_rsp_size_q[trace_curr_index_w];
  assign direct_trace_rsp_source_w = trace_rsp_source_q[trace_curr_index_w];
  assign direct_trace_rsp_has_data_w = trace_rsp_has_data_q[trace_curr_index_w];
  assign direct_trace_rsp_data_w = trace_rsp_data_q[trace_curr_index_w];
  assign direct_trace_rsp_data_nonzero_w = (direct_trace_rsp_data_w != '0);
  assign direct_trace_rsp_opcode_eff_w =
      (direct_trace_rsp_has_data_w || direct_trace_rsp_data_nonzero_w)
          ? AccessAckData
          : tl_d_op_e'(direct_trace_rsp_opcode_w);
  assign direct_trace_rsp_delay_w = trace_rsp_delay_q[trace_curr_index_w];
  assign direct_trace_rsp_error_w = trace_rsp_error_q[trace_curr_index_w];
  assign direct_trace_host_ready_mode_w =
      trace_host_ready_mode_q[trace_curr_index_w];
  assign direct_trace_device_ready_mode_w =
      trace_device_ready_mode_q[trace_curr_index_w];
  assign direct_trace_req_valid_mode_w =
      trace_req_valid_mode_q[trace_curr_index_w];
  assign direct_trace_active_w =
      direct_trace_mode_w
      && bootstrapped_q
      && (cycle_count_q >= direct_trace_start_cycle_w)
      && !direct_trace_done_w;
  assign direct_trace_done_w =
      direct_trace_mode_w && (direct_trace_step_q >= trace_step_count_q);
  assign direct_req_drive_w =
      direct_trace_active_w
      && !direct_req_done_q
      && (direct_trace_req_valid_mode_w != 2'd1);
  assign direct_rsp_drive_w =
      direct_trace_active_w
      && direct_req_done_q
      && !direct_rsp_done_q
      && direct_trace_rsp_valid_w
      && (direct_rsp_delay_q == 32'd0);
  assign direct_req_step_complete_w =
      direct_req_done_q
      || (direct_trace_req_valid_mode_w == 2'd1)
      || req_handshake_w;
  assign direct_rsp_step_complete_w =
      direct_rsp_done_q
      || !direct_trace_rsp_valid_w
      || device_rsp_accept_w;
  assign direct_trace_step_advance_w =
      direct_trace_active_w
      && direct_req_step_complete_w
      && direct_rsp_step_complete_w;
  assign direct_rsp_replay_valid_w =
      direct_rsp_hold_valid_q || direct_rsp_drive_w;
  assign direct_rsp_replay_opcode_bits_w =
      direct_rsp_hold_valid_q
      ? direct_rsp_hold_opcode_q
      : direct_trace_rsp_opcode_eff_w;
  assign direct_rsp_replay_size_w =
      direct_rsp_hold_valid_q
      ? direct_rsp_hold_size_q
      : direct_trace_rsp_size_w;
  assign direct_rsp_replay_source_w =
      direct_rsp_hold_valid_q
      ? direct_rsp_hold_source_q
      : direct_trace_rsp_source_w;
  assign direct_rsp_replay_data_w =
      direct_rsp_hold_valid_q
      ? direct_rsp_hold_data_q
      : direct_trace_rsp_data_w;
  assign direct_rsp_replay_error_w =
      direct_rsp_hold_valid_q
      ? direct_rsp_hold_error_q
      : direct_trace_rsp_error_w;
  assign direct_host_ready_w =
      (direct_trace_host_ready_mode_w != 2'd1);
  assign direct_device_ready_w =
      (direct_trace_device_ready_mode_w != 2'd1);
  assign direct_rsp_buffer_hold_w =
      direct_trace_active_w
      && direct_rsp_replay_valid_w
      && (dut.rspfifo.depth_o == 2'd0)
      && !direct_rsp_hold_valid_q;
  assign reset_like_w = !bootstrapped_q || (phase_q == ResetPhase);
  assign traffic_phase_w =
      direct_trace_mode_w
      ? (direct_trace_active_w && !direct_trace_done_w)
      : (phase_q == TrafficPhase);
  assign response_phase_w =
      direct_trace_mode_w
      ? (direct_trace_active_w && !direct_trace_done_w)
      : ((phase_q == TrafficPhase) || (phase_q == DrainPhase));
  assign phase_code_w =
      direct_trace_mode_w
      ? (direct_trace_done_w ? DonePhase : (direct_trace_active_w ? TrafficPhase : phase_q))
      : phase_q;
  assign reset_cycles_remaining_w = (phase_q == ResetPhase) ? reset_cycles_remaining_q : 32'd0;
  assign warmup_cycles_remaining_w = (phase_q == WarmupPhase) ? warmup_cycles_remaining_q : 32'd0;

  assign reset_like_o = reset_like_w;
  assign done_o =
      bootstrapped_q
      && (direct_trace_mode_w ? direct_trace_done_w : (phase_q == DonePhase));

  assign rand_seed_w = (rand_state_q != 32'd0) ? rand_state_q : seed_cfg;
  assign rand_req_w = rand_seed_w ^ {cycle_count_q[15:0], cycle_count_q[31:16]} ^ 32'h1357_9bdf;
  assign rand_rsp_w = {rand_seed_w[7:0], rand_seed_w[31:8]} ^ cycle_count_q ^ 32'h2468_ace1;
  assign rand_host_ready_w = {rand_seed_w[15:0], rand_seed_w[31:16]} ^ 32'h55aa_33cc;
  assign rand_device_ready_w = {rand_seed_w[23:0], rand_seed_w[31:24]} ^ 32'hc33c_aa55;
  assign rand_next_w = (rand_seed_w ^ (rand_seed_w << 13))
                     ^ ((rand_seed_w ^ (rand_seed_w << 13)) >> 17)
                     ^ (((rand_seed_w ^ (rand_seed_w << 13))
                       ^ ((rand_seed_w ^ (rand_seed_w << 13)) >> 17)) << 5)
                     ^ cycle_count_q
                     ^ 32'h9e37_79b9;

  assign req_valid_gate_w = decode_gate_mode(req_valid_pct_cfg[6:4], rand_req_w[2:0]);
  assign rsp_valid_gate_w = decode_gate_mode(rsp_valid_pct_cfg[6:4], rand_rsp_w[2:0]);
  assign host_ready_gate_w = decode_gate_mode(
      host_d_ready_pct_cfg[6:4], rand_host_ready_w[2:0]);
  assign device_ready_gate_w = decode_gate_mode(
      device_a_ready_pct_cfg[6:4], rand_device_ready_w[2:0]);
  assign traffic_front_half_w =
      traffic_phase_w && (traffic_cycles_remaining_q > (batch_length_cfg >> 1));
  assign traffic_back_half_w = response_phase_w && !traffic_front_half_w;
  assign req_fill_force_w =
      ((req_data_mode_cfg >= 32'd2)
       || (req_fill_target_cfg != 32'd0)
       || (req_data_hi_xor_cfg[31:16] != 16'd0))
      && traffic_front_half_w;
  assign rsp_backlog_force_w =
      ((rsp_data_mode_cfg >= 32'd2)
       || (rsp_fill_target_cfg != 32'd0)
       || (rsp_data_hi_xor_cfg[31:16] != 16'd0))
      && traffic_front_half_w;
  assign req_fifo_fill_hold_w =
      req_fill_force_w && !dut.reqfifo.full_o && (dut.reqfifo.depth_o < req_fill_target_cfg[1:0])
      && !req_fill_release_w;
  assign rsp_fifo_fill_hold_w =
      rsp_backlog_force_w && !dut.rspfifo.full_o
      && (dut.rspfifo.depth_o < rsp_fill_target_cfg[1:0]) && !rsp_fill_release_w;
  assign req_fill_release_w =
      &cycle_count_q[1:0] || rand_device_ready_w[0];
  assign rsp_fill_release_w =
      &cycle_count_q[1:0] || rand_host_ready_w[0];
  assign put_full_gate_w = decode_gate_mode(put_full_pct_cfg[6:4], rand_req_w[9:7]);
  assign put_partial_gate_w = decode_gate_mode(put_partial_pct_cfg[6:4], rand_req_w[16:14]);
  assign rsp_data_gate_w = decode_gate_mode(access_ack_data_pct_cfg[6:4], rand_rsp_w[9:7]);
  assign rsp_error_gate_w = decode_gate_mode(rsp_error_pct_cfg[6:4], rand_rsp_w[16:14]);

  assign host_d_ready_base_w =
      (response_phase_w
       || tl_h_o.d_valid
       || rsp_pending_valid_q
       || (rsp_count_q != 32'd0))
      ? (((traffic_front_half_w
           && (rsp_fill_target_cfg != 32'd0)
           && !cycle_count_q[1]
           && !tl_h_o.d_valid
           && !rsp_pending_valid_q
           && (rsp_count_q == 32'd0)))
          ? 1'b0 : 1'b1)
      : 1'b0;
  assign device_a_ready_base_w =
      response_phase_w
      ? ((traffic_front_half_w
          && (req_fill_target_cfg != 32'd0)
          && !cycle_count_q[1]) ? 1'b0 : 1'b1)
      : 1'b0;

  always_comb begin
    tl_h_i = tlul_pkg::TL_H2D_DEFAULT;
    tl_d_i = tlul_pkg::TL_D2H_DEFAULT;
    spare_req_i = '0;
    spare_rsp_i = '0;

    tl_h_i.d_ready = host_d_ready_w;
    tl_d_i.a_ready = device_a_ready_w;
    tl_h_i.a_valid = direct_trace_active_w
        ? direct_req_drive_w
        : (req_pending_valid_q || req_spawn_w);
    tl_h_i.a_opcode = direct_trace_active_w
        ? decode_trace_req_opcode(direct_trace_req_opcode_w)
        : (req_pending_valid_q ? req_pending_opcode_q : req_opcode_spawn_w);
    tl_h_i.a_param = direct_trace_active_w
        ? direct_trace_req_param_w
        : (req_pending_valid_q ? req_pending_param_q : req_param_spawn_w);
    tl_h_i.a_size = direct_trace_active_w
        ? direct_trace_req_size_w
        : (req_pending_valid_q ? req_pending_size_q : req_size_spawn_w);
    tl_h_i.a_source = direct_trace_active_w
        ? direct_trace_req_source_w
        : (req_pending_valid_q ? req_pending_source_q : req_source_spawn_w);
    tl_h_i.a_address = direct_trace_active_w
        ? direct_trace_req_address_w
        : (req_pending_valid_q ? req_pending_address_q : req_address_spawn_w);
    tl_h_i.a_mask = direct_trace_active_w
        ? direct_trace_req_mask_w
        : (req_pending_valid_q ? req_pending_mask_q : req_mask_spawn_w);
    tl_h_i.a_data = direct_trace_active_w
        ? direct_trace_req_data_w
        : (req_pending_valid_q ? req_pending_data_q : req_data_spawn_w);
    tl_h_i.a_user = direct_trace_active_w
        ? direct_req_user_w
        : req_user_active_w;
    spare_req_i = direct_trace_active_w
        ? (direct_req_drive_w ? direct_trace_req_spare_w : '0)
        : (req_pending_valid_q ? req_pending_spare_q : req_spare_spawn_w);

    tl_d_i.d_valid = direct_trace_mode_w
        ? direct_rsp_replay_valid_w
        : (rsp_pending_valid_q || rsp_spawn_w);
    tl_d_i.d_opcode = direct_trace_mode_w
        ? tl_d_op_e'(direct_rsp_replay_opcode_bits_w)
        : tl_d_op_e'(rsp_active_opcode_bits_w);
    tl_d_i.d_param = direct_trace_mode_w
        ? 3'd0
        : (rsp_pending_valid_q ? rsp_pending_param_q : rsp_param_spawn_w);
    tl_d_i.d_size = direct_trace_mode_w
        ? direct_rsp_replay_size_w
        : (rsp_pending_valid_q ? rsp_pending_size_q : rsp_size_spawn_w);
    tl_d_i.d_source = direct_trace_mode_w
        ? direct_rsp_replay_source_w
        : (rsp_pending_valid_q ? rsp_pending_source_q : rsp_source_spawn_w);
    tl_d_i.d_sink = direct_trace_mode_w
        ? '0
        : (rsp_pending_valid_q ? rsp_pending_sink_q : rsp_sink_spawn_w);
    tl_d_i.d_data = direct_trace_mode_w
        ? direct_rsp_replay_data_w
        : (rsp_pending_valid_q ? rsp_pending_data_q : rsp_data_spawn_w);
    tl_d_i.d_user = direct_trace_mode_w
        ? direct_rsp_user_w
        : rsp_user_active_w;
    tl_d_i.d_error = direct_trace_mode_w
        ? direct_rsp_replay_error_w
        : (rsp_pending_valid_q ? rsp_pending_error_q : rsp_error_spawn_w);
    spare_rsp_i = direct_trace_mode_w
        ? '0
        : (rsp_trace_payload_override_w
            ? '0
            : (rsp_pending_valid_q ? rsp_pending_spare_q : rsp_spare_spawn_w));
  end

  assign req_user_active_w =
      req_pending_valid_q
      ? build_req_user(
            req_pending_opcode_q,
            req_pending_param_q,
            req_pending_size_q,
            req_pending_source_q,
            req_pending_address_q,
            req_pending_mask_q,
            req_pending_data_q,
            req_pending_trace_active_q,
            req_pending_spare_q[0]
        )
      : build_req_user(
            req_opcode_spawn_w,
            req_param_spawn_w,
            req_size_spawn_w,
            req_source_spawn_w,
            req_address_spawn_w,
            req_mask_spawn_w,
            req_data_spawn_w,
            req_trace_replay_w,
            req_spare_spawn_w[0]
        );
  assign direct_req_user_w =
      build_req_user(
          decode_trace_req_opcode(direct_trace_req_opcode_w),
          direct_trace_req_param_w,
          direct_trace_req_size_w,
          direct_trace_req_source_w,
          direct_trace_req_address_w,
          direct_trace_req_mask_w,
          direct_trace_req_data_w,
          direct_trace_active_w,
          direct_trace_req_spare_w[0]
      );
  assign rsp_user_active_w =
      direct_trace_mode_w
      ? tlul_pkg::TL_D_USER_DEFAULT
      : rsp_trace_payload_override_w
      ? tlul_pkg::TL_D_USER_DEFAULT
      : (rsp_pending_valid_q
          ? build_rsp_user(
                tl_d_op_e'(rsp_pending_opcode_q),
                rsp_pending_param_q,
                rsp_pending_size_q,
                rsp_pending_source_q,
                rsp_pending_sink_q,
                rsp_pending_data_q,
                rsp_pending_error_q,
                1'b0,
                rsp_pending_spare_q[0]
            )
          : build_rsp_user(
                tl_d_op_e'(rsp_opcode_spawn_bits_w),
                rsp_param_spawn_w,
                rsp_size_spawn_w,
                rsp_source_spawn_w,
                rsp_sink_spawn_w,
                rsp_data_spawn_w,
                rsp_error_spawn_w,
                1'b0,
                rsp_spare_spawn_w[0]
            ));
  assign direct_rsp_user_w =
      build_rsp_user(
          tl_d_op_e'(direct_rsp_replay_opcode_bits_w),
          3'd0,
          direct_rsp_replay_size_w,
          direct_rsp_replay_source_w,
          '0,
          direct_rsp_replay_data_w,
          direct_rsp_replay_error_w,
          direct_trace_active_w,
          1'b0
      );

  assign req_handshake_w = tl_h_i.a_valid && tl_h_o.a_ready;
  assign device_req_accept_w = tl_d_o.a_valid && device_a_ready_w;
  assign device_rsp_accept_w = tl_d_i.d_valid && tl_d_o.d_ready;
  assign host_rsp_accept_w = tl_h_o.d_valid && host_d_ready_w;
  assign device_req_handshake_w = device_req_accept_w;
  assign rsp_handshake_w = device_rsp_accept_w;
  assign host_rsp_handshake_w = host_rsp_accept_w;
  assign overflow_event_w = device_req_accept_w && (rsp_count_q >= QueueDepth);
  assign generic_rsp_queue_push_w =
      device_req_handshake_w && !overflow_event_w && !direct_trace_mode_w;
  assign drain_busy_w =
      (rsp_count_q != 32'd0)
      || rsp_pending_valid_q
      || tl_d_o.a_valid
      || tl_d_i.d_valid
      || tl_h_o.d_valid;
  assign trace_step_remaining_w =
      (trace_step_count_q != 32'd0) && (trace_step_q != trace_step_count_q);
  assign trace_live_w =
      direct_trace_mode_w
      ? direct_trace_active_w
      : (traffic_phase_w
         && (trace_step_remaining_w
             || req_pending_trace_active_q
             || req_burst_trace_active_q));
  assign trace_req_active_w =
      direct_trace_mode_w
      ? direct_req_drive_w
      : (traffic_phase_w
         && (req_burst_remaining_q == 32'd0)
         && trace_step_remaining_w);
  assign req_trace_replay_w =
      direct_trace_mode_w
      ? (direct_trace_active_w
         && (trace_req_valid_mode_q[trace_curr_index_w] != 2'd1))
      : ((req_burst_remaining_q != 32'd0) ? req_burst_trace_active_q
         : (req_pending_valid_q ? req_pending_trace_active_q : trace_req_active_w));
  assign req_trace_index_w =
      direct_trace_mode_w
      ? trace_curr_index_w
      : ((req_burst_remaining_q != 32'd0) ? req_burst_trace_index_q
         : (req_pending_valid_q ? req_pending_trace_index_q : trace_curr_index_w));
  assign rsp_trace_head_valid_w =
      rsp_trace_valid_queue_q[rsp_head_q[QueueIndexWidth-1:0]];
  assign rsp_trace_replay_w =
      direct_trace_mode_w
      ? direct_rsp_drive_w
      : rsp_trace_head_valid_w;
  assign rsp_trace_replay_index_w =
      direct_trace_mode_w
      ? trace_curr_index_w
      : ((rsp_spawn_w && rsp_trace_enqueue_active_w)
         ? rsp_trace_enqueue_index_w
         : rsp_head_q[TraceIndexWidth-1:0]);
  assign rsp_trace_valid_w =
      rsp_trace_head_valid_w
      ? rsp_trace_valid_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
      : trace_rsp_valid_q[rsp_trace_replay_index_w];
  assign rsp_trace_size_w =
      rsp_trace_head_valid_w
      ? rsp_trace_size_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
      : trace_rsp_size_q[rsp_trace_replay_index_w];
  assign rsp_trace_source_w =
      rsp_trace_head_valid_w
      ? rsp_trace_source_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
      : trace_rsp_source_q[rsp_trace_replay_index_w];
  assign rsp_trace_has_data_w =
      rsp_trace_head_valid_w
      ? rsp_trace_has_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
      : (rsp_trace_valid_w ? trace_rsp_has_data_q[rsp_trace_replay_index_w] : 1'b0);
  assign rsp_trace_override_valid_w =
      (trace_step_count_q != 32'd0)
      ? 1'b0
      : (rsp_trace_head_valid_w
         || (rsp_trace_replay_w && rsp_trace_valid_w));
  assign rsp_trace_payload_override_w =
      (trace_step_count_q != 32'd0)
      ? 1'b0
      : (rsp_pending_valid_q ? rsp_trace_head_valid_w : rsp_trace_override_valid_w);
  assign trace_host_ready_mode_w =
      direct_trace_mode_w
      ? direct_trace_host_ready_mode_w
      : (rsp_trace_head_valid_w
         ? rsp_trace_host_ready_mode_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
         : (rsp_trace_replay_w
            ? trace_host_ready_mode_q[rsp_trace_replay_index_w]
            : 2'd0));
  assign trace_host_ready_default_w =
      (trace_step_count_q != 32'd0)
      ? 1'b0
      : ((trace_step_count_q != 32'd0)
      || trace_live_w
      || rsp_trace_override_valid_w
      || rsp_pending_valid_q
      || rsp_spawn_w
      || tl_h_o.d_valid
      || (rsp_count_q != 32'd0));
  assign trace_device_ready_mode_w =
      direct_trace_mode_w
      ? direct_trace_device_ready_mode_w
      : (req_trace_replay_w
         ? trace_device_ready_mode_q[req_trace_index_w]
         : (req_forward_trace_active_q
             ? trace_device_ready_mode_q[req_forward_trace_index_q]
             : 2'd0));
  assign trace_device_ready_default_w =
      (trace_step_count_q != 32'd0)
      ? 1'b0
      : ((trace_step_count_q != 32'd0)
      || trace_live_w
      || req_trace_replay_w
      || req_forward_trace_active_q);
  assign trace_req_valid_mode_w =
      direct_trace_mode_w
      ? direct_trace_req_valid_mode_w
      : (req_trace_replay_w ? trace_req_valid_mode_q[req_trace_index_w] : 2'd0);
  assign trace_req_skip_w =
      (trace_step_count_q == 32'd0)
      && trace_req_active_w
      && (req_burst_remaining_q == 32'd0)
      && !req_pending_valid_q
      && (trace_req_valid_mode_w == 2'd1);
  assign req_trace_queue_active_w =
      (trace_step_count_q == 32'd0) && (req_forward_trace_active_q || req_trace_replay_w);
  assign req_trace_queue_index_w =
      req_forward_trace_active_q ? req_forward_trace_index_q : req_trace_index_w;
  assign rsp_trace_enqueue_active_w =
      (trace_step_count_q == 32'd0) && req_trace_queue_active_w;
  assign rsp_trace_enqueue_index_w =
      req_forward_trace_active_q ? req_forward_trace_index_q
      : (req_pending_trace_active_q ? req_pending_trace_index_q
      : (req_burst_trace_active_q ? req_burst_trace_index_q
      : (req_trace_replay_w ? req_trace_index_w : trace_curr_index_w)));
  assign trace_req_fill_hold_w =
      (trace_step_count_q == 32'd0)
      && trace_live_w
      && (req_fill_target_cfg != 32'd0)
      && (trace_device_ready_mode_w == 2'd1)
      && (rsp_count_q < req_fill_target_cfg);
  assign trace_rsp_fill_hold_w =
      (trace_step_count_q == 32'd0)
      && trace_live_w
      && (rsp_fill_target_cfg != 32'd0)
      && (trace_host_ready_mode_w == 2'd1)
      && (rsp_count_q < rsp_fill_target_cfg)
      && !rsp_pending_valid_q
      && !tl_h_o.d_valid
      && (rsp_handshake_seen_q == 8'd0);
  assign host_d_ready_w =
      direct_trace_active_w
      ? (direct_rsp_buffer_hold_w ? 1'b0 : direct_host_ready_w)
      : (trace_rsp_fill_hold_w ? 1'b0
      : (trace_host_ready_default_w
         ? ((trace_host_ready_mode_w == 2'd1) ? 1'b0
         : ((trace_host_ready_mode_w == 2'd2) ? 1'b1
                                              : host_d_ready_base_w))
         : host_d_ready_base_w));
  assign device_a_ready_w =
      direct_trace_active_w
      ? direct_device_ready_w
      : (trace_req_fill_hold_w ? 1'b0
      : (trace_device_ready_default_w
         ? ((trace_device_ready_mode_w == 2'd1) ? 1'b0
         : ((trace_device_ready_mode_w == 2'd2) ? 1'b1
                                                : device_a_ready_base_w))
         : device_a_ready_base_w));
  assign req_spawn_w =
      (trace_step_count_q == 32'd0)
      && traffic_phase_w && !req_pending_valid_q
      && ((req_burst_remaining_q != 32'd0)
          || (trace_live_w
              ? (trace_req_active_w && (trace_req_valid_mode_w != 2'd1))
              : (req_valid_gate_w || req_fill_force_w)));
  assign rsp_spawn_w =
      direct_trace_mode_w
      ? (direct_trace_active_w && direct_rsp_drive_w && !rsp_pending_valid_q)
      : ((trace_step_count_q == 32'd0)
         && response_phase_w && !rsp_pending_valid_q && (rsp_count_q != 32'd0)
         && (rsp_delay_queue_q[rsp_head_q[QueueIndexWidth-1:0]] == 32'd0)
         && 1'b1);
  assign req_opcode_spawn_w =
      (req_burst_remaining_q != 32'd0) ? req_burst_opcode_q
      : (trace_req_active_w ? decode_trace_req_opcode(
            trace_req_opcode_q[trace_curr_index_w])
      : (req_fill_force_w ? PutFullData
      : ((req_family_cfg == 32'd1) ? (put_partial_gate_w ? PutPartialData : PutFullData)
      : ((req_family_cfg == 32'd2) ? Get
      : ((req_family_cfg == 32'd3) ? (rand_req_w[0] ? PutPartialData
                                                   : (rand_req_w[1] ? PutFullData : Get))
      : (put_full_gate_w ? PutFullData : (put_partial_gate_w ? PutPartialData : Get)))))));
  assign req_param_spawn_w =
      (req_burst_remaining_q != 32'd0) ? req_burst_param_q
      : (trace_req_active_w
         ? trace_req_param_q[trace_curr_index_w]
         : rand_req_w[23:21]);
  assign req_size_spawn_w =
      (req_burst_remaining_q != 32'd0)
      ? req_burst_size_q
      : (trace_req_active_w
         ? trace_req_size_q[trace_curr_index_w]
      : (req_fill_force_w ? top_pkg::TL_SZW'(2)
      : ((req_family_cfg == 32'd0) ? rand_req_w[top_pkg::TL_SZW+24-1:24]
                                   : top_pkg::TL_SZW'(2))));
  assign req_source_spawn_w =
      (req_burst_remaining_q != 32'd0) ? req_burst_source_q
      : (trace_req_active_w
         ? (trace_req_source_q[trace_curr_index_w]
            & source_mask_cfg[top_pkg::TL_AIW-1:0])
      : (req_fill_force_w
         ? ((rand_req_w[top_pkg::TL_AIW+8-1:8]
             ^ {{(top_pkg::TL_AIW-2){1'b0}}, dut.reqfifo.depth_o})
            & source_mask_cfg[top_pkg::TL_AIW-1:0])
      : (((req_family_cfg == 32'd1) ? (rand_req_w[top_pkg::TL_AIW+1:2] & 'h3)
         : ((req_family_cfg == 32'd2) ? (rand_req_w[top_pkg::TL_AIW+2:3] & 'h7)
                                      : rand_req_w[top_pkg::TL_AIW+8-1:8]))
         & source_mask_cfg[top_pkg::TL_AIW-1:0])));
  assign req_address_family_w =
      req_fill_force_w
      ? ((address_base_cfg & ~address_mask_cfg)
         | (((cycle_count_q << 4) ^ {28'd0, dut.reqfifo.depth_o, 2'b00}) & address_mask_cfg))
      : ((req_address_mode_cfg == 32'd1)
      ? ((address_base_cfg & ~32'h0000_003c) | (rand_next_w & 32'h0000_003c))
      : ((req_address_mode_cfg == 32'd2)
         ? ((address_base_cfg & ~32'h0000_00fc) | (rand_next_w & 32'h0000_00fc))
         : ((req_address_mode_cfg == 32'd3)
            ? ((address_base_cfg & ~address_mask_cfg)
               | (((rand_req_w[top_pkg::TL_AIW+8-1:8]
                    & source_mask_cfg[top_pkg::TL_AIW-1:0]) << 4)
                  & address_mask_cfg))
            : ((address_base_cfg & ~address_mask_cfg) | (rand_next_w & address_mask_cfg)))));
  assign req_address_spawn_w =
      (req_burst_remaining_q != 32'd0) ? req_burst_address_q
      : (trace_req_active_w
         ? (trace_req_address_q[trace_curr_index_w] & 32'hffff_fffc)
         : (req_address_family_w & 32'hffff_fffc));
  assign req_mask_spawn_w =
      (req_burst_remaining_q != 32'd0) ? req_burst_mask_q
      : (trace_req_active_w
         ? trace_req_mask_q[trace_curr_index_w]
      : (req_fill_force_w ? top_pkg::TL_DBW'(4'b1111)
         : ((req_family_cfg == 32'd0) ? rand_req_w[top_pkg::TL_DBW+4-1:4]
                                      : '1)));
  assign req_data_upper_fill_w =
      (16'h8000 >> ((cycle_count_q[3:0] + {14'd0, dut.reqfifo.depth_o}) & 4'hf))
      ^ {8'h00, req_source_spawn_w}
      ^ {req_burst_remaining_q[3:0], rsp_count_q[3:0], cycle_count_q[3:0], req_address_spawn_w[5:2]}
      ^ req_data_hi_xor_cfg[31:16];
  assign req_data_pattern_w =
      (
        req_fill_force_w
        ? {req_data_upper_fill_w,
           req_address_spawn_w[15:0] ^ {8'h00, req_mask_spawn_w, req_source_spawn_w}}
        : ((req_data_mode_cfg == 32'd1)
        ? ({req_address_spawn_w[15:0], ~req_address_spawn_w[15:0]} ^ 32'h55aa_33cc)
        : ((req_data_mode_cfg == 32'd2)
           ? ({rand_next_w[31:24],
               req_source_spawn_w,
               req_address_spawn_w[15:8],
               rand_req_w[23:16]}
              ^ {req_address_spawn_w[7:0], rand_next_w[23:0]})
           : ((req_data_mode_cfg == 32'd3)
              ? ({req_source_spawn_w ^ rand_req_w[31:24],
                  req_mask_spawn_w,
                  req_address_spawn_w[11:4],
                  cycle_count_q[7:0]}
                 ^ {rand_next_w[15:0], rand_rsp_w[31:16]}
                 ^ 32'hc0de_1234)
              : ((req_data_mode_cfg == 32'd4)
                 ? ({req_data_upper_fill_w,
                     req_address_spawn_w[15:0]
                     ^ {8'h00, req_mask_spawn_w, req_source_spawn_w}
                     ^ {rsp_count_q[7:0], cycle_count_q[7:0]}})
                 : ((req_family_cfg == 32'd3)
                    ? ({8{req_source_spawn_w[1:0] ^ req_address_spawn_w[3:2]}}
                       ^ {rand_req_w[31:24], rand_req_w[23:16],
                          rand_next_w[31:24], rand_next_w[23:16]})
                    : (rand_next_w
                       ^ {req_address_spawn_w[15:0], req_source_spawn_w, req_mask_spawn_w}
                       ^ 32'hc0de_1234
                       ^ cycle_count_q))))))
      ) ^ req_data_hi_xor_cfg;
  assign req_data_spawn_w =
      (req_burst_remaining_q != 32'd0)
      ? req_burst_data_q
      : (trace_req_active_w
         ? trace_req_data_q[trace_curr_index_w]
         : req_data_pattern_w);
  assign req_spare_spawn_w =
      (req_burst_remaining_q != 32'd0) ? req_burst_spare_q
      : (trace_req_active_w
         ? trace_req_spare_q[trace_curr_index_w]
         : rand_req_w[31]);
  assign rsp_trace_opcode_bits_w =
      rsp_trace_head_valid_w
      ? rsp_trace_opcode_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
      : trace_rsp_opcode_q[rsp_trace_replay_index_w];
  assign rsp_family_opcode_bits_w =
      ((rsp_backlog_force_w
        || (rsp_data_mode_cfg >= 32'd2)
        || (rsp_family_cfg == 32'd1)) ? 3'd1
       : ((rsp_family_cfg == 32'd2) ? 3'd0
       : ((rsp_family_cfg == 32'd3) ? (rand_rsp_w[0] ? 3'd1 : 3'd0)
                                    : (rsp_data_gate_w ? 3'd1 : 3'd0))));
  assign rsp_opcode_spawn_bits_w =
      direct_trace_mode_w ? direct_trace_rsp_opcode_eff_w
      : (rsp_trace_override_valid_w ? rsp_trace_opcode_bits_w : rsp_family_opcode_bits_w);
  assign rsp_active_opcode_bits_w =
      direct_trace_mode_w
      ? direct_rsp_replay_opcode_bits_w
      : (rsp_pending_valid_q ? rsp_pending_opcode_q : rsp_opcode_spawn_bits_w);
  assign host_rsp_passthrough_observed_w =
      (trace_step_count_q != 32'd0)
      && host_rsp_accept_w
      && (device_rsp_accept_w || last_device_rsp_seen_q);
  assign host_rsp_observed_opcode_bits_w =
      !host_rsp_passthrough_observed_w ? tl_h_o.d_opcode
      : device_rsp_accept_w ? tl_d_i.d_opcode
      : last_device_rsp_opcode_q;
  assign host_rsp_observed_data_w =
      !host_rsp_passthrough_observed_w ? tl_h_o.d_data
      : device_rsp_accept_w ? tl_d_i.d_data
      : last_device_rsp_data_q;
  assign rsp_param_spawn_w =
      (direct_trace_mode_w || rsp_trace_override_valid_w) ? 3'd0 : rand_rsp_w[18:16];
  assign rsp_size_spawn_w =
      direct_trace_mode_w
      ? direct_trace_rsp_size_w
      : (rsp_trace_override_valid_w
      ? rsp_trace_size_w
      : rsp_size_queue_q[rsp_head_q[QueueIndexWidth-1:0]]);
  assign rsp_source_spawn_w =
      direct_trace_mode_w
      ? direct_trace_rsp_source_w
      : (rsp_trace_override_valid_w
      ? rsp_trace_source_w
      : rsp_source_queue_q[rsp_head_q[QueueIndexWidth-1:0]]);
  assign rsp_sink_spawn_w =
      (direct_trace_mode_w || rsp_trace_override_valid_w)
      ? '0
      : rand_rsp_w[top_pkg::TL_DIW+24-1:24];
  assign rsp_data_upper_fill_w =
      (16'h8000 >> ((cycle_count_q[3:0] + rsp_head_q[3:0]) & 4'hf))
      ^ rsp_req_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]][31:16]
      ^ {rsp_count_q[3:0], rsp_head_q[3:0], cycle_count_q[3:0], rsp_source_spawn_w[3:0]}
      ^ rsp_data_hi_xor_cfg[31:16];
  assign rsp_data_pattern_w =
      (
        rsp_backlog_force_w
        ? {rsp_data_upper_fill_w,
           rsp_req_address_queue_q[rsp_head_q[QueueIndexWidth-1:0]][15:0]
           ^ rsp_req_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]][15:0]}
        : ((rsp_data_mode_cfg == 32'd1)
        ? ({rsp_source_spawn_w, rsp_source_spawn_w, rsp_source_spawn_w, rsp_source_spawn_w}
           ^ {rand_rsp_w[31:24], rand_rsp_w[15:8], rand_next_w[31:24], rand_next_w[15:8]})
        : ((rsp_data_mode_cfg == 32'd2)
           ? (rsp_req_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
              ^ {8'hca, rsp_source_spawn_w,
                 rsp_req_address_queue_q[rsp_head_q[QueueIndexWidth-1:0]][15:8],
                 rsp_req_address_queue_q[rsp_head_q[QueueIndexWidth-1:0]][7:0]}
              ^ {rand_rsp_w[31:16], rand_next_w[15:0]})
           : ((rsp_data_mode_cfg == 32'd3)
              ? ((rsp_req_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
                  ^ {rsp_req_address_queue_q[rsp_head_q[QueueIndexWidth-1:0]][15:0],
                     rsp_req_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]][15:0]})
                 ^ {rsp_source_spawn_w, rsp_sink_spawn_w, rand_rsp_w[15:0]}
                 ^ 32'h2468_ace1)
              : ((rsp_data_mode_cfg == 32'd4)
                 ? ({rsp_data_upper_fill_w,
                     rsp_req_address_queue_q[rsp_head_q[QueueIndexWidth-1:0]][15:0]
                     ^ rsp_req_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]][15:0]
                     ^ {rsp_source_spawn_w, rsp_size_spawn_w, rsp_param_spawn_w,
                        rsp_error_spawn_w, rand_rsp_w[4:0]}})
                 : (rand_next_w
                    ^ {rand_rsp_w[15:0], rand_req_w[31:16]}
                    ^ 32'h2468_ace1
                    ^ cycle_count_q)))))
      ) ^ rsp_data_hi_xor_cfg;
  assign rsp_data_spawn_w =
      direct_trace_mode_w
      ? direct_trace_rsp_data_w
      : (rsp_trace_override_valid_w
      ? (rsp_trace_head_valid_w
         ? rsp_trace_data_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
         : trace_rsp_data_q[rsp_trace_replay_index_w])
      : rsp_data_pattern_w);
  assign rsp_error_spawn_w =
      direct_trace_mode_w
      ? direct_trace_rsp_error_w
      : (rsp_trace_override_valid_w
      ? (rsp_trace_head_valid_w
         ? rsp_trace_error_queue_q[rsp_head_q[QueueIndexWidth-1:0]]
         : trace_rsp_error_q[rsp_trace_replay_index_w])
      : ((rsp_family_cfg == 32'd1) ? 1'b0
      : ((rsp_family_cfg == 32'd2)
         ? ((rand_rsp_w[31:24] % 8'd100) < (rsp_error_pct_cfg[7:0] >> 1))
         : rsp_error_gate_w)));
  assign rsp_spare_spawn_w =
      (direct_trace_mode_w || rsp_trace_override_valid_w)
      ? 1'b0
      : rand_rsp_w[31];
  assign focused_wave_pack_a_w = {
      reset_like_w,
      done_o,
      overflow_event_w,
      tl_d_i.d_source,
      tl_h_i.a_source,
      dut.rspfifo.depth_o,
      dut.reqfifo.depth_o,
      tl_d_i.d_valid,
      tl_d_o.d_ready,
      tl_d_o.a_valid,
      tl_d_i.a_ready,
      tl_h_o.d_valid,
      tl_h_i.d_ready,
      tl_h_i.a_valid,
      tl_h_o.a_ready,
      phase_code_w
  };
  assign focused_wave_pack_b_w = {tl_h_o.d_data[31:16], tl_h_i.a_data[31:16]};

  assign bootstrapped_d = 1'b1;
  assign cycle_count_d = cycle_count_q + 32'd1;
  assign phase_steady_w = (phase_q == ResetPhase)
                              ? ((reset_cycles_remaining_q == 32'd0) ? WarmupPhase : ResetPhase)
                          : (phase_q == WarmupPhase)
                              ? ((warmup_cycles_remaining_q == 32'd0)
                                  ? ((traffic_cycles_remaining_q == 32'd0)
                                      ? ((drain_cycles_remaining_q == 32'd0)
                                          ? DonePhase : DrainPhase)
                                      : TrafficPhase)
                                  : WarmupPhase)
                          : (phase_q == TrafficPhase)
                              ? (((traffic_cycles_remaining_q == 32'd0)
                               || (traffic_cycles_remaining_q == 32'd1))
                                  ? ((drain_cycles_remaining_q == 32'd0)
                                      ? DonePhase : DrainPhase)
                                  : TrafficPhase)
                          : (phase_q == DrainPhase)
                              ? ((((drain_cycles_remaining_q == 32'd0)
                                || (drain_cycles_remaining_q == 32'd1))
                                  && !drain_busy_w)
                                  ? DonePhase
                                  : DrainPhase)
                          : DonePhase;
  assign reset_cycles_remaining_steady_w = ((phase_q == ResetPhase)
                                         && (reset_cycles_remaining_q != 32'd0))
                                                ? (reset_cycles_remaining_q - 32'd1)
                                                : reset_cycles_remaining_q;
  assign warmup_cycles_remaining_steady_w = ((phase_q == WarmupPhase)
                                          && (warmup_cycles_remaining_q != 32'd0))
                                                 ? (warmup_cycles_remaining_q - 32'd1)
                                                 : warmup_cycles_remaining_q;
  assign traffic_cycles_remaining_steady_w = ((phase_q == TrafficPhase)
                                           && (traffic_cycles_remaining_q != 32'd0)
                                           && (traffic_cycles_remaining_q != 32'd1))
                                                  ? (traffic_cycles_remaining_q - 32'd1)
                                          : ((phase_q == TrafficPhase)
                                          && (traffic_cycles_remaining_q == 32'd1))
                                                  ? 32'd0
                                                  : traffic_cycles_remaining_q;
  assign drain_cycles_remaining_steady_w = ((phase_q == DrainPhase)
                                         && (drain_cycles_remaining_q != 32'd0)
                                         && (drain_cycles_remaining_q != 32'd1))
                                                ? (drain_cycles_remaining_q - 32'd1)
                                        : ((phase_q == DrainPhase)
                                        && (drain_cycles_remaining_q == 32'd1))
                                                ? (drain_busy_w ? 32'd1 : 32'd0)
                                                : drain_cycles_remaining_q;
  assign phase_d = ({3{bootstrapped_q}} & phase_steady_w)
                 | ({3{!bootstrapped_q}} & ResetPhase);
  assign reset_cycles_remaining_d = ({32{bootstrapped_q}} & reset_cycles_remaining_steady_w)
                                  | ({32{!bootstrapped_q}} & reset_cycles_cfg);
  assign warmup_cycles_remaining_d = ({32{bootstrapped_q}} & warmup_cycles_remaining_steady_w)
                                   | ({32{!bootstrapped_q}} & WarmupCycles);
  assign traffic_cycles_remaining_d = ({32{bootstrapped_q}} & traffic_cycles_remaining_steady_w)
                                    | ({32{!bootstrapped_q}} & batch_length_cfg);
  assign drain_cycles_remaining_d = ({32{bootstrapped_q}} & drain_cycles_remaining_steady_w)
                                  | ({32{!bootstrapped_q}} & drain_cycles_cfg);
  assign rand_state_d = rand_next_w;
  assign req_pending_valid_d = reset_like_w ? 1'b0
                             : req_handshake_w ? 1'b0
                             : req_pending_valid_q ? 1'b1
                             : req_spawn_w;
  assign req_pending_trace_active_d = reset_like_w ? 1'b0
                                    : req_handshake_w ? 1'b0
                                    : req_pending_valid_q ? req_pending_trace_active_q
                                    : req_spawn_w ? trace_live_w
                                    : 1'b0;
  assign req_pending_trace_index_d = reset_like_w ? '0 : req_spawn_w
      ? trace_curr_index_w : req_pending_trace_index_q;
  assign req_forward_trace_active_d = reset_like_w ? 1'b0
                                    : device_req_accept_w ? 1'b0
                                    : req_handshake_w ? req_trace_replay_w
                                    : req_forward_trace_active_q;
  assign req_forward_trace_index_d = reset_like_w ? '0
                                   : (req_handshake_w && req_trace_replay_w)
                                       ? req_trace_index_w
                                       : req_forward_trace_index_q;
  assign req_pending_opcode_d = req_spawn_w ? req_opcode_spawn_w : req_pending_opcode_q;
  assign req_pending_param_d = req_spawn_w ? req_param_spawn_w : req_pending_param_q;
  assign req_pending_size_d = req_spawn_w ? req_size_spawn_w : req_pending_size_q;
  assign req_pending_source_d = req_spawn_w ? req_source_spawn_w : req_pending_source_q;
  assign req_pending_address_d = req_spawn_w ? req_address_spawn_w : req_pending_address_q;
  assign req_pending_mask_d = req_spawn_w ? req_mask_spawn_w : req_pending_mask_q;
  assign req_pending_data_d = req_spawn_w ? req_data_spawn_w : req_pending_data_q;
  assign req_pending_spare_d = req_spawn_w ? req_spare_spawn_w : req_pending_spare_q;
  assign req_burst_remaining_d = reset_like_w ? 32'd0
                               : req_handshake_w
                                   ? ((req_burst_remaining_q != 32'd0)
                                      ? (req_burst_remaining_q - 32'd1)
                                      : (trace_req_active_w
                                         ? direct_trace_req_burst_len_w
                                      : (((req_data_mode_cfg >= 32'd2)
                                          && (req_burst_len_max_cfg < 32'd2))
                                       ? (32'd2 + rand_host_ready_w[1:0])
                                       : ((req_burst_len_max_cfg == 32'd0) ? 32'd0
                                       : (rand_host_ready_w[3:0]
                                            % (req_burst_len_max_cfg + 32'd1))))))
                               : req_burst_remaining_q;
  assign req_burst_trace_active_d = reset_like_w ? 1'b0
                                  : req_handshake_w
                                      ? ((req_burst_remaining_q != 32'd0)
                                         ? req_burst_trace_active_q
                                         : trace_live_w)
                                      : req_burst_trace_active_q;
  assign req_burst_trace_index_d = reset_like_w ? '0
      : (req_handshake_w && (req_burst_remaining_q == 32'd0))
          ? trace_curr_index_w
          : req_burst_trace_index_q;
  assign trace_step_d = reset_like_w ? 32'd0
                      : (direct_trace_mode_w
                          ? trace_step_q
                          : (((req_handshake_w
                             && (req_burst_remaining_q == 32'd0)
                             && trace_live_w)
                             || trace_req_skip_w)
                          ? (trace_step_q + 32'd1)
                          : trace_step_q));
  assign direct_trace_step_d = reset_like_w ? 32'd0
                             : (direct_trace_mode_w
                                 ? (direct_trace_step_advance_w
                                     ? (direct_trace_step_q + 32'd1)
                                     : direct_trace_step_q)
                                 : 32'd0);
  assign direct_req_done_d = reset_like_w ? 1'b0
                           : !direct_trace_mode_w ? 1'b0
                           : direct_trace_step_advance_w ? 1'b0
                           : (direct_req_done_q
                              || (direct_trace_req_valid_mode_w == 2'd1)
                              || req_handshake_w);
  assign direct_rsp_done_d = reset_like_w ? 1'b0
                           : !direct_trace_mode_w ? 1'b0
                           : direct_trace_step_advance_w ? 1'b0
                           : (direct_rsp_done_q
                              || !direct_trace_rsp_valid_w
                              || device_rsp_accept_w);
  assign direct_rsp_delay_d = reset_like_w ? 32'd0
                            : !direct_trace_mode_w ? 32'd0
                            : direct_trace_step_advance_w ? 32'd0
                            : (!direct_req_done_q
                               && ((direct_trace_req_valid_mode_w == 2'd1)
                                   || req_handshake_w))
                                ? direct_trace_rsp_delay_w
                            : ((direct_req_done_q
                                && !direct_rsp_done_q
                                && direct_trace_rsp_valid_w
                                && (direct_rsp_delay_q != 32'd0)
                                && !device_rsp_accept_w)
                               ? (direct_rsp_delay_q - 32'd1)
                               : direct_rsp_delay_q);
  assign req_burst_opcode_d =
      (req_handshake_w && (req_burst_remaining_q == 32'd0))
      ? req_opcode_spawn_w : req_burst_opcode_q;
  assign req_burst_param_d =
      (req_handshake_w && (req_burst_remaining_q == 32'd0))
      ? req_param_spawn_w : req_burst_param_q;
  assign req_burst_size_d =
      (req_handshake_w && (req_burst_remaining_q == 32'd0))
      ? req_size_spawn_w : req_burst_size_q;
  assign req_burst_source_d =
      (req_handshake_w && (req_burst_remaining_q == 32'd0))
      ? req_source_spawn_w : req_burst_source_q;
  assign req_burst_address_d = reset_like_w ? '0
      : req_handshake_w ? (req_address_spawn_w + 32'd4) : req_burst_address_q;
  assign req_burst_mask_d =
      (req_handshake_w && (req_burst_remaining_q == 32'd0))
      ? req_mask_spawn_w : req_burst_mask_q;
  assign req_burst_data_d = reset_like_w ? '0
      : req_handshake_w
          ? ({req_data_spawn_w[19:0], req_data_spawn_w[31:20]}
             ^ {rand_next_w[15:0], rand_req_w[31:16]}
             ^ 32'h1f1f_1f1f)
          : req_burst_data_q;
  assign req_burst_spare_d = (req_handshake_w && (req_burst_remaining_q == 32'd0))
      ? req_spare_spawn_w : req_burst_spare_q;
  assign direct_rsp_hold_valid_d = reset_like_w ? 1'b0
                                 : !direct_trace_mode_w ? 1'b0
                                 : direct_rsp_hold_valid_q
                                     ? !device_rsp_accept_w
                                     : (direct_rsp_drive_w && !device_rsp_accept_w);
  assign direct_rsp_hold_opcode_d =
      (!direct_rsp_hold_valid_q && direct_rsp_drive_w && !device_rsp_accept_w)
      ? direct_trace_rsp_opcode_eff_w
      : direct_rsp_hold_opcode_q;
  assign direct_rsp_hold_size_d =
      (!direct_rsp_hold_valid_q && direct_rsp_drive_w && !device_rsp_accept_w)
      ? direct_trace_rsp_size_w
      : direct_rsp_hold_size_q;
  assign direct_rsp_hold_source_d =
      (!direct_rsp_hold_valid_q && direct_rsp_drive_w && !device_rsp_accept_w)
      ? direct_trace_rsp_source_w
      : direct_rsp_hold_source_q;
  assign direct_rsp_hold_data_d =
      (!direct_rsp_hold_valid_q && direct_rsp_drive_w && !device_rsp_accept_w)
      ? direct_trace_rsp_data_w
      : direct_rsp_hold_data_q;
  assign direct_rsp_hold_error_d =
      (!direct_rsp_hold_valid_q && direct_rsp_drive_w && !device_rsp_accept_w)
      ? direct_trace_rsp_error_w
      : direct_rsp_hold_error_q;
  assign rsp_pending_valid_d = reset_like_w ? 1'b0
                             : direct_trace_mode_w ? 1'b0
                             : rsp_handshake_w ? 1'b0
                             : rsp_pending_valid_q ? 1'b1
                             : rsp_spawn_w;
  assign rsp_pending_opcode_d =
      rsp_spawn_w ? rsp_opcode_spawn_bits_w : rsp_pending_opcode_q;
  assign rsp_pending_param_d = rsp_spawn_w ? rsp_param_spawn_w : rsp_pending_param_q;
  assign rsp_pending_size_d = rsp_spawn_w ? rsp_size_spawn_w : rsp_pending_size_q;
  assign rsp_pending_source_d = rsp_spawn_w ? rsp_source_spawn_w : rsp_pending_source_q;
  assign rsp_pending_sink_d = rsp_spawn_w ? rsp_sink_spawn_w : rsp_pending_sink_q;
  assign rsp_pending_data_d = rsp_spawn_w ? rsp_data_spawn_w : rsp_pending_data_q;
  assign rsp_pending_error_d = rsp_spawn_w ? rsp_error_spawn_w : rsp_pending_error_q;
  assign rsp_pending_spare_d = rsp_spawn_w ? rsp_spare_spawn_w : rsp_pending_spare_q;
  assign rsp_head_d = reset_like_w ? 32'd0
                    : direct_trace_mode_w ? 32'd0
                    : rsp_handshake_w ? ((rsp_head_q + 32'd1) & (QueueDepth - 1))
                    : rsp_head_q;
  assign rsp_tail_d = reset_like_w ? 32'd0
                    : direct_trace_mode_w ? 32'd0
                    : generic_rsp_queue_push_w
                        ? ((rsp_tail_q + 32'd1) & (QueueDepth - 1))
                    : rsp_tail_q;
  assign rsp_count_d = reset_like_w ? 32'd0
                     : direct_trace_mode_w ? 32'd0
                     : (generic_rsp_queue_push_w && rsp_handshake_w)
                         ? rsp_count_q
                     : generic_rsp_queue_push_w
                         ? (rsp_count_q + 32'd1)
                     : rsp_handshake_w
                         ? (rsp_count_q - 32'd1)
                     : rsp_count_q;
  assign host_req_accepted_d = reset_like_w ? 32'd0
                             : (host_req_accepted_q + {31'd0, req_handshake_w});
  assign device_req_accepted_d = reset_like_w ? 32'd0
                               : (device_req_accepted_q + {31'd0, device_req_handshake_w});
  assign device_rsp_accepted_d = reset_like_w ? 32'd0
                               : (device_rsp_accepted_q + {31'd0, rsp_handshake_w});
  assign host_rsp_accepted_d = reset_like_w ? 32'd0
                             : (host_rsp_accepted_q + {31'd0, host_rsp_handshake_w});
  assign rsp_queue_overflow_d = reset_like_w ? 32'd0
                              : (rsp_queue_overflow_q + {31'd0, overflow_event_w});
  assign max_reqfifo_depth_d = reset_like_w ? 2'd0
                              : ((dut.reqfifo.depth_o > max_reqfifo_depth_q)
                                 ? dut.reqfifo.depth_o : max_reqfifo_depth_q);
  assign max_rspfifo_depth_d = reset_like_w ? 2'd0
                              : ((dut.rspfifo.depth_o > max_rspfifo_depth_q)
                                 ? dut.rspfifo.depth_o : max_rspfifo_depth_q);
  assign req_handshake_seen_d = reset_like_w ? 8'd0
                               : sat_inc8(req_handshake_seen_q, req_handshake_w);
  assign rsp_handshake_seen_d = reset_like_w ? 8'd0
                               : sat_inc8(rsp_handshake_seen_q, rsp_handshake_w);
  assign host_rsp_handshake_seen_d = reset_like_w ? 8'd0
                                    : sat_inc8(
                                          host_rsp_handshake_seen_q,
                                          host_rsp_handshake_w
                                      );
  assign direct_trace_active_seen_d = reset_like_w ? 8'd0
                                      : sat_inc8(
                                            direct_trace_active_seen_q,
                                            direct_trace_active_w
                                        );
  assign direct_req_drive_seen_d = reset_like_w ? 8'd0
                                  : sat_inc8(
                                        direct_req_drive_seen_q,
                                        direct_req_drive_w
                                    );
  assign direct_req_ready_seen_d = reset_like_w ? 8'd0
                                  : sat_inc8(
                                        direct_req_ready_seen_q,
                                        direct_req_drive_w && tl_h_o.a_ready
                                    );
  assign direct_req_handshake_seen_d = reset_like_w ? 8'd0
                                      : sat_inc8(
                                            direct_req_handshake_seen_q,
                                            direct_req_drive_w && tl_h_o.a_ready
                                        );
  assign direct_rsp_drive_seen_d = reset_like_w ? 8'd0
                                  : sat_inc8(
                                        direct_rsp_drive_seen_q,
                                        direct_rsp_drive_w
                                    );
  assign direct_rsp_handshake_seen_d = reset_like_w ? 8'd0
                                      : sat_inc8(
                                            direct_rsp_handshake_seen_q,
                                            direct_rsp_drive_w && tl_d_o.d_ready
                                        );
  assign trace_req_active_seen_d = reset_like_w ? 8'd0
                                 : sat_inc8(trace_req_active_seen_q, trace_req_active_w);
  assign req_spawn_seen_d = reset_like_w ? 8'd0
                          : sat_inc8(req_spawn_seen_q, req_spawn_w);
  assign req_ready_seen_d = reset_like_w ? 8'd0
                           : sat_inc8(req_ready_seen_q, trace_req_active_w && tl_h_o.a_ready);
  assign req_blocked_seen_d = reset_like_w ? 8'd0
                             : sat_inc8(req_blocked_seen_q, trace_req_active_w && !tl_h_o.a_ready);
  assign reqfifo_full_seen_d = reset_like_w ? 8'd0
                              : sat_inc8(reqfifo_full_seen_q, dut.reqfifo.full_o);
  assign reqfifo_under_rst_seen_d = reset_like_w ? 8'd0
                                   : sat_inc8(reqfifo_under_rst_seen_q,
                                              dut.reqfifo.gen_normal_fifo.under_rst);
  assign device_a_ready_seen_d = reset_like_w ? 8'd0
                               : sat_inc8(device_a_ready_seen_q, device_a_ready_w);
  assign device_a_valid_seen_d = reset_like_w ? 8'd0
                                : sat_inc8(device_a_valid_seen_q, tl_d_o.a_valid);
  assign device_ready_force_high_seen_d = reset_like_w ? 8'd0
                                        : sat_inc8(
                                              device_ready_force_high_seen_q,
                                              trace_device_ready_default_w
                                              && (trace_device_ready_mode_w != 2'd1)
                                              && !trace_req_fill_hold_w
                                          );
  assign trace_req_fill_hold_seen_d = reset_like_w ? 8'd0
                                     : sat_inc8(trace_req_fill_hold_seen_q,
                                                trace_req_fill_hold_w);
  assign trace_host_ready_default_seen_d = reset_like_w ? 8'd0
                                         : sat_inc8(
                                               trace_host_ready_default_seen_q,
                                               trace_host_ready_default_w
                                           );
  assign trace_rsp_fill_hold_seen_d = reset_like_w ? 8'd0
                                      : sat_inc8(trace_rsp_fill_hold_seen_q,
                                                 trace_rsp_fill_hold_w);
  assign host_d_ready_seen_d = reset_like_w ? 8'd0
                              : sat_inc8(host_d_ready_seen_q, host_d_ready_w);
  assign host_d_valid_seen_d = reset_like_w ? 8'd0
                              : sat_inc8(host_d_valid_seen_q, tl_h_o.d_valid);
  assign device_rsp_ackdata_seen_d = reset_like_w ? 8'd0
                                   : sat_inc8(
                                         device_rsp_ackdata_seen_q,
                                         tl_d_i.d_valid
                                         && (tl_d_i.d_opcode == AccessAckData)
                                     );
  assign host_rsp_ackdata_seen_d = reset_like_w ? 8'd0
                                 : sat_inc8(
                                       host_rsp_ackdata_seen_q,
                                       host_rsp_accept_w
                                       && (tl_d_op_e'(host_rsp_observed_opcode_bits_w)
                                           == AccessAckData)
                                   );
  assign device_rsp_payload_upper_seen_d = reset_like_w ? 8'd0
                                        : sat_inc8(
                                              device_rsp_payload_upper_seen_q,
                                              tl_d_i.d_valid
                                              && (tl_d_i.d_opcode == AccessAckData)
                                              && (|tl_d_i.d_data[31:16])
                                          );
  assign host_rsp_payload_upper_seen_d = reset_like_w ? 8'd0
                                      : sat_inc8(
                                            host_rsp_payload_upper_seen_q,
                                            host_rsp_accept_w
                                            && (tl_d_op_e'(host_rsp_observed_opcode_bits_w)
                                                == AccessAckData)
                                            && (|host_rsp_observed_data_w[31:16])
                                        );
  assign device_rsp_payload_upper_accept_seen_d = reset_like_w ? 8'd0
                                               : sat_inc8(
                                                     device_rsp_payload_upper_accept_seen_q,
                                                     device_rsp_accept_w
                                                     && (tl_d_i.d_opcode == AccessAckData)
                                                     && (|tl_d_i.d_data[31:16])
                                                 );
  assign host_rsp_payload_upper_accept_seen_d = reset_like_w ? 8'd0
                                            : sat_inc8(
                                                  host_rsp_payload_upper_accept_seen_q,
                                                  host_rsp_accept_w
                                                  && (tl_d_op_e'(host_rsp_observed_opcode_bits_w)
                                                      == AccessAckData)
                                                  && (|host_rsp_observed_data_w[31:16])
                                              );
  assign host_raw_rsp_ackdata_seen_d = reset_like_w ? 8'd0
                                     : sat_inc8(
                                           host_raw_rsp_ackdata_seen_q,
                                           host_rsp_accept_w
                                           && (tl_h_o.d_opcode == AccessAckData)
                                       );
  assign host_raw_rsp_payload_upper_seen_d = reset_like_w ? 8'd0
                                           : sat_inc8(
                                                 host_raw_rsp_payload_upper_seen_q,
                                                 host_rsp_accept_w
                                                 && (tl_h_o.d_opcode == AccessAckData)
                                                 && (|tl_h_o.d_data[31:16])
                                             );
  assign first_device_rsp_seen_d = reset_like_w ? 1'b0
                                 : (first_device_rsp_seen_q
                                    || (direct_trace_active_w && device_rsp_accept_w));
  assign first_device_rsp_opcode_d =
      (!first_device_rsp_seen_q && direct_trace_active_w && device_rsp_accept_w)
      ? tl_d_i.d_opcode
      : first_device_rsp_opcode_q;
  assign first_device_rsp_data_upper_d =
      (!first_device_rsp_seen_q && direct_trace_active_w && device_rsp_accept_w)
      ? tl_d_i.d_data[31:16]
      : first_device_rsp_data_upper_q;
  assign first_host_rsp_seen_d = reset_like_w ? 1'b0
                               : (first_host_rsp_seen_q
                                  || (direct_trace_active_w && host_rsp_accept_w));
  assign first_host_rsp_opcode_d =
      (!first_host_rsp_seen_q && direct_trace_active_w && host_rsp_accept_w)
      ? host_rsp_observed_opcode_bits_w
      : first_host_rsp_opcode_q;
  assign first_host_rsp_data_upper_d =
      (!first_host_rsp_seen_q && direct_trace_active_w && host_rsp_accept_w)
      ? host_rsp_observed_data_w[31:16]
      : first_host_rsp_data_upper_q;
  assign last_device_rsp_seen_d = reset_like_w ? 1'b0
                                 : (device_rsp_accept_w || last_device_rsp_seen_q);
  assign last_device_rsp_opcode_d = device_rsp_accept_w
      ? tl_d_i.d_opcode : last_device_rsp_opcode_q;
  assign last_device_rsp_data_d = device_rsp_accept_w
      ? tl_d_i.d_data : last_device_rsp_data_q;
  assign host_raw_rsp_opcode_or_d = reset_like_w ? '0
                                  : (host_raw_rsp_opcode_or_q
                                     | ({3{host_rsp_accept_w}} & tl_h_o.d_opcode));
  assign rsp_trace_override_seen_d = reset_like_w ? 8'd0
                                   : sat_inc8(rsp_trace_override_seen_q,
                                              rsp_trace_override_valid_w);
  assign rsp_trace_head_valid_seen_d = reset_like_w ? 8'd0
                                     : sat_inc8(rsp_trace_head_valid_seen_q,
                                                rsp_trace_head_valid_w);
  assign rsp_trace_has_data_seen_d = reset_like_w ? 8'd0
                                   : sat_inc8(rsp_trace_has_data_seen_q,
                                              rsp_trace_has_data_w);
  assign rsp_spawn_has_data_seen_d = reset_like_w ? 8'd0
                                   : sat_inc8(rsp_spawn_has_data_seen_q,
                                              rsp_spawn_w && rsp_trace_has_data_w);
  assign rsp_spawn_ackdata_seen_d = reset_like_w ? 8'd0
                                   : sat_inc8(
                                         rsp_spawn_ackdata_seen_q,
                                         rsp_spawn_w && (rsp_opcode_spawn_bits_w == 3'd1)
                                     );
  assign rsp_spawn_opcode_or_d = reset_like_w ? 3'd0
                                : (rsp_spawn_opcode_or_q
                                   | ({3{rsp_spawn_w}} & rsp_opcode_spawn_bits_w));
  assign rsp_active_opcode_or_d = reset_like_w ? 3'd0
                                 : (rsp_active_opcode_or_q
                                    | ({3{(rsp_pending_valid_q || rsp_spawn_w)}}
                                       & rsp_active_opcode_bits_w));
  assign device_rsp_opcode_or_d = reset_like_w ? 3'd0
                                 : (device_rsp_opcode_or_q
                                    | ({3{tl_d_i.d_valid}} & tl_d_i.d_opcode));
  assign host_rsp_opcode_or_d = reset_like_w ? 3'd0
                               : (host_rsp_opcode_or_q
                                  | ({3{host_rsp_accept_w}} & host_rsp_observed_opcode_bits_w));
  assign reqfifo_nonempty_seen_d = reset_like_w ? 8'd0
                                 : sat_inc8(reqfifo_nonempty_seen_q, dut.reqfifo.depth_o != 2'd0);
  assign rspfifo_nonempty_seen_d = reset_like_w ? 8'd0
                                 : sat_inc8(rspfifo_nonempty_seen_q, dut.rspfifo.depth_o != 2'd0);
  assign a_data_mid_or_d = reset_like_w ? 16'd0 : (a_data_mid_or_q | tl_h_i.a_data[23:8]);
  assign a_address_window_or_d = reset_like_w ? 20'd0
                               : (a_address_window_or_q | tl_h_i.a_address[19:0]);
  assign device_d_data_low_or_d = reset_like_w ? 16'd0
                                  : (device_d_data_low_or_q | tl_d_i.d_data[15:0]);
  assign device_d_data_upper_or_d = reset_like_w ? 16'd0
                                    : (device_d_data_upper_or_q | tl_d_i.d_data[31:16]);
  assign d_data_low_or_d = reset_like_w ? 16'd0
                           : (d_data_low_or_q | host_rsp_observed_data_w[15:0]);
  assign a_data_upper_or_d = reset_like_w ? 16'd0 : (a_data_upper_or_q | tl_h_i.a_data[31:16]);
  assign d_data_upper_or_d = reset_like_w ? 16'd0
                             : (d_data_upper_or_q | host_rsp_observed_data_w[31:16]);
  assign progress_signature_d = reset_like_w ? 32'd0
                             : (progress_signature_q
                                + 32'h9e37_79b9
                                + {28'd0, host_rsp_handshake_w, rsp_handshake_w,
                                   device_req_handshake_w, req_handshake_w}
                                + {29'd0, phase_code_w}
                                + rand_req_w[7:0]
                                + rand_rsp_w[15:8]);
  assign toggle_prev_word0_d = reset_like_w ? 32'd0 : toggle_curr_w[31:0];
  assign toggle_prev_word1_d = reset_like_w ? 32'd0 : toggle_curr_w[63:32];
  assign toggle_prev_word2_d = reset_like_w ? 32'd0 : toggle_curr_w[95:64];
  assign toggle_hit_word0_d = reset_like_w
                                  ? 32'd0
                                  : (toggle_hit_word0_q
                                     | (toggle_curr_w[31:0] ^ toggle_prev_word0_q));
  assign toggle_hit_word1_d = reset_like_w
                                  ? 32'd0
                                  : (toggle_hit_word1_q
                                     | (toggle_curr_w[63:32] ^ toggle_prev_word1_q));
  assign toggle_hit_word2_d = reset_like_w
                                  ? 32'd0
                                  : (toggle_hit_word2_q
                                     | (toggle_curr_w[95:64] ^ toggle_prev_word2_q));

  always_comb begin
    toggle_curr_w = '0;
    toggle_curr_w[0] = reset_like_w;
    toggle_curr_w[1] = (phase_q == WarmupPhase);
    toggle_curr_w[2] = (phase_q == TrafficPhase);
    toggle_curr_w[3] = (phase_q == DrainPhase);
    toggle_curr_w[4] = (phase_q == DonePhase);
    toggle_curr_w[5] = tl_h_i.a_valid;
    toggle_curr_w[6] = tl_h_o.a_ready;
    toggle_curr_w[7] = tl_d_o.a_valid;
    toggle_curr_w[8] = tl_d_i.a_ready;
    toggle_curr_w[9] = tl_d_i.d_valid;
    toggle_curr_w[10] = tl_d_o.d_ready;
    toggle_curr_w[11] = tl_h_o.d_valid;
    toggle_curr_w[12] = tl_h_i.d_ready;
    toggle_curr_w[13] = req_handshake_w;
    toggle_curr_w[14] = device_req_handshake_w;
    toggle_curr_w[15] = rsp_handshake_w;
    toggle_curr_w[16] = host_rsp_handshake_w;
    toggle_curr_w[17] = tl_h_o.d_error;
    toggle_curr_w[18] = tl_d_i.d_error;
    toggle_curr_w[19] = overflow_event_w;
    toggle_curr_w[20] = req_valid_gate_w;
    toggle_curr_w[21] = rsp_valid_gate_w;
    toggle_curr_w[22] = host_ready_gate_w;
    toggle_curr_w[23] = device_ready_gate_w;
    toggle_curr_w[24] = put_full_gate_w;
    toggle_curr_w[25] = put_partial_gate_w;
    toggle_curr_w[26] = rsp_data_gate_w;
    toggle_curr_w[27] = rsp_error_gate_w;
    toggle_curr_w[28 +: 3] = phase_code_w;
    toggle_curr_w[31] = done_o;
    toggle_curr_w[32 +: 3] = tl_h_i.a_opcode;
    toggle_curr_w[35 +: 3] = tl_d_i.d_opcode;
    toggle_curr_w[38 +: 3] = tl_d_o.a_opcode;
    toggle_curr_w[41 +: 3] = tl_h_o.d_opcode;
    toggle_curr_w[44 +: 2] = tl_h_i.a_size;
    toggle_curr_w[46 +: 2] = tl_d_i.d_size;
    toggle_curr_w[48 +: 2] = tl_d_o.a_size;
    toggle_curr_w[50 +: 2] = tl_h_o.d_size;
    toggle_curr_w[52 +: top_pkg::TL_AIW] = tl_h_i.a_source;
    toggle_curr_w[60 +: top_pkg::TL_AIW] = tl_d_i.d_source;
    toggle_curr_w[68 +: top_pkg::TL_DIW] = tl_d_i.d_sink;
    toggle_curr_w[69 +: 8] = tl_h_i.a_address[9:2];
    toggle_curr_w[77 +: top_pkg::TL_DBW] = tl_h_i.a_mask;
    toggle_curr_w[81 +: 3] = rsp_count_q[2:0];
    toggle_curr_w[84] = host_req_accepted_q[0];
    toggle_curr_w[85] = device_req_accepted_q[0];
    toggle_curr_w[86] = device_rsp_accepted_q[0];
    toggle_curr_w[87] = host_rsp_accepted_q[0];
    toggle_curr_w[88] = (rsp_queue_overflow_q != 32'd0);
    toggle_curr_w[89] = spare_req_i[0];
    toggle_curr_w[90] = spare_req_o[0];
    toggle_curr_w[91] = spare_rsp_i[0];
    toggle_curr_w[92] = spare_rsp_o[0];
    toggle_curr_w[93] = rand_state_q[0];
    toggle_curr_w[94] = progress_signature_q[0];
    toggle_curr_w[95] = progress_signature_q[1];
  end

  integer queue_idx;
  integer trace_idx;
  always_comb begin
    for (queue_idx = 0; queue_idx < QueueDepth; queue_idx++) begin
      rsp_size_queue_d[queue_idx] = rsp_size_queue_q[queue_idx];
      rsp_source_queue_d[queue_idx] = rsp_source_queue_q[queue_idx];
      rsp_req_opcode_queue_d[queue_idx] = rsp_req_opcode_queue_q[queue_idx];
      rsp_req_address_queue_d[queue_idx] = rsp_req_address_queue_q[queue_idx];
      rsp_req_data_queue_d[queue_idx] = rsp_req_data_queue_q[queue_idx];
      rsp_delay_queue_d[queue_idx] = rsp_delay_queue_q[queue_idx];
      rsp_trace_valid_queue_d[queue_idx] = rsp_trace_valid_queue_q[queue_idx];
      rsp_trace_opcode_queue_d[queue_idx] = rsp_trace_opcode_queue_q[queue_idx];
      rsp_trace_size_queue_d[queue_idx] = rsp_trace_size_queue_q[queue_idx];
      rsp_trace_source_queue_d[queue_idx] = rsp_trace_source_queue_q[queue_idx];
      rsp_trace_has_data_queue_d[queue_idx] = rsp_trace_has_data_queue_q[queue_idx];
      rsp_trace_data_queue_d[queue_idx] = rsp_trace_data_queue_q[queue_idx];
      rsp_trace_error_queue_d[queue_idx] = rsp_trace_error_queue_q[queue_idx];
      rsp_trace_host_ready_mode_queue_d[queue_idx] = rsp_trace_host_ready_mode_queue_q[queue_idx];
    end
    if (reset_like_w) begin
      for (queue_idx = 0; queue_idx < QueueDepth; queue_idx++) begin
        rsp_size_queue_d[queue_idx] = '0;
        rsp_source_queue_d[queue_idx] = '0;
        rsp_req_opcode_queue_d[queue_idx] = Get;
        rsp_req_address_queue_d[queue_idx] = '0;
        rsp_req_data_queue_d[queue_idx] = '0;
        rsp_delay_queue_d[queue_idx] = '0;
        rsp_trace_valid_queue_d[queue_idx] = 1'b0;
        rsp_trace_opcode_queue_d[queue_idx] = 3'd0;
        rsp_trace_size_queue_d[queue_idx] = '0;
        rsp_trace_source_queue_d[queue_idx] = '0;
        rsp_trace_has_data_queue_d[queue_idx] = 1'b0;
        rsp_trace_data_queue_d[queue_idx] = '0;
        rsp_trace_error_queue_d[queue_idx] = 1'b0;
        rsp_trace_host_ready_mode_queue_d[queue_idx] = 2'd0;
      end
    end else if (generic_rsp_queue_push_w) begin
      rsp_size_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] = tl_d_o.a_size;
      rsp_source_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] = tl_d_o.a_source;
      rsp_req_opcode_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] = tl_d_o.a_opcode;
      rsp_req_address_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] = tl_d_o.a_address;
      rsp_req_data_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] = tl_d_o.a_data;
      rsp_trace_valid_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] = rsp_trace_enqueue_active_w;
      rsp_trace_opcode_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
          rsp_trace_enqueue_active_w
          ? trace_rsp_opcode_q[rsp_trace_enqueue_index_w]
          : 3'd0;
      rsp_trace_size_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
          rsp_trace_enqueue_active_w
          ? trace_rsp_size_q[rsp_trace_enqueue_index_w]
          : tl_d_o.a_size;
      rsp_trace_source_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
          rsp_trace_enqueue_active_w
          ? trace_rsp_source_q[rsp_trace_enqueue_index_w]
          : tl_d_o.a_source;
      rsp_trace_has_data_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
          rsp_trace_enqueue_active_w
          ? trace_rsp_has_data_q[rsp_trace_enqueue_index_w]
          : 1'b0;
      rsp_trace_data_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
          rsp_trace_enqueue_active_w
          ? trace_rsp_data_q[rsp_trace_enqueue_index_w]
          : '0;
      rsp_trace_error_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
          rsp_trace_enqueue_active_w
          ? trace_rsp_error_q[rsp_trace_enqueue_index_w]
          : 1'b0;
      rsp_trace_host_ready_mode_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
          rsp_trace_enqueue_active_w
          ? trace_host_ready_mode_q[rsp_trace_enqueue_index_w]
          : 2'd0;
      if (rsp_trace_enqueue_active_w) begin
        rsp_delay_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
            trace_rsp_delay_q[rsp_trace_enqueue_index_w];
      end else begin
      unique case (rsp_delay_mode_cfg)
        32'd1: rsp_delay_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] = 32'd0;
        32'd2: rsp_delay_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
            (rsp_delay_max_cfg == 32'd0)
            ? 32'd0
            : ((rand_next_w[0] != 0) ? rsp_delay_max_cfg : 32'd0);
        32'd3: rsp_delay_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
            (rsp_delay_max_cfg == 32'd0)
            ? 32'd0
            : ((rand_next_w % (rsp_delay_max_cfg + 32'd1)) >> 1);
        default: rsp_delay_queue_d[rsp_tail_q[QueueIndexWidth-1:0]] =
            (rsp_delay_max_cfg == 32'd0) ? 32'd0 : (rand_next_w % (rsp_delay_max_cfg + 32'd1));
      endcase
      end
    end
    if (response_phase_w && (rsp_count_q != 32'd0)
        && (rsp_delay_queue_q[rsp_head_q[QueueIndexWidth-1:0]] != 32'd0)
        && !rsp_pending_valid_q) begin
      unique case (rsp_delay_mode_cfg)
        32'd1: rsp_delay_queue_d[rsp_head_q[QueueIndexWidth-1:0]] = 32'd0;
        32'd2: rsp_delay_queue_d[rsp_head_q[QueueIndexWidth-1:0]] =
            (rsp_delay_queue_q[rsp_head_q[QueueIndexWidth-1:0]] > 32'd2)
            ? 32'd2 : rsp_delay_queue_q[rsp_head_q[QueueIndexWidth-1:0]];
        default: rsp_delay_queue_d[rsp_head_q[QueueIndexWidth-1:0]] =
            rsp_delay_queue_q[rsp_head_q[QueueIndexWidth-1:0]] - 32'd1;
      endcase
    end
  end

  assign real_toggle_subset_curr_chunk0_w = {
    dut.reqfifo.err_o,
    dut.reqfifo.depth_o[1],
    dut.reqfifo.depth_o[0],
    dut.reqfifo.full_o,
    dut.reqfifo.rvalid_o,
    dut.reqfifo.wready_o,
    dut.reqfifo.gen_normal_fifo.empty,
    dut.reqfifo.gen_normal_fifo.under_rst,
    dut.reqfifo.gen_normal_fifo.fifo_empty,
    dut.reqfifo.gen_normal_fifo.fifo_incr_rptr,
    dut.reqfifo.gen_normal_fifo.fifo_incr_wptr,
    dut.reqfifo.gen_normal_fifo.fifo_rptr[0],
    dut.reqfifo.gen_normal_fifo.fifo_wptr[0],
    3'd0
  };
  assign real_toggle_subset_curr_chunk1_w = dut.reqfifo.gen_normal_fifo.storage[0][47:32];
  assign real_toggle_subset_curr_chunk2_w = dut.reqfifo.gen_normal_fifo.storage[0][63:48];
  assign real_toggle_subset_curr_chunk3_w = dut.reqfifo.gen_normal_fifo.storage[0][79:64];
  assign real_toggle_subset_curr_chunk4_w = dut.reqfifo.gen_normal_fifo.storage[1][47:32];
  assign real_toggle_subset_curr_chunk5_w = {
    dut.rspfifo.err_o,
    dut.rspfifo.depth_o[1],
    dut.rspfifo.depth_o[0],
    dut.rspfifo.full_o,
    dut.rspfifo.rvalid_o,
    dut.rspfifo.wready_o,
    dut.rspfifo.gen_normal_fifo.empty,
    dut.rspfifo.gen_normal_fifo.under_rst,
    dut.rspfifo.gen_normal_fifo.fifo_empty,
    dut.rspfifo.gen_normal_fifo.fifo_incr_rptr,
    dut.rspfifo.gen_normal_fifo.fifo_incr_wptr,
    dut.rspfifo.gen_normal_fifo.fifo_rptr[0],
    dut.rspfifo.gen_normal_fifo.fifo_wptr[0],
    dut.rspfifo.gen_normal_fifo.storage[0][18:16]
  };
  assign real_toggle_subset_curr_chunk6_w = {
    dut.rspfifo.gen_normal_fifo.storage[1][18:16],
    dut.rspfifo.gen_normal_fifo.storage[0][31:19]
  };
  assign real_toggle_subset_curr_chunk7_w = {
    3'd0,
    dut.rspfifo.gen_normal_fifo.storage[1][31:19]
  };
  assign real_toggle_subset_curr_chunk8_w = {
    tl_h_i.a_source[5],
    tl_h_i.a_source[4],
    tl_h_i.a_source[3],
    tl_h_i.a_source[2],
    tl_h_i.a_source[1],
    tl_h_i.a_source[0],
    tl_h_i.a_size[1],
    tl_h_i.a_size[0],
    tl_h_i.a_opcode[2],
    tl_h_i.a_opcode[1],
    tl_h_i.a_opcode[0],
    tl_h_o.d_error,
    tl_d_i.d_error,
    tl_h_i.d_ready,
    tl_h_o.d_valid,
    tl_d_o.d_ready
  };
  assign real_toggle_subset_curr_chunk9_w = {
    tl_h_i.a_mask[3],
    tl_h_i.a_mask[2],
    tl_h_i.a_mask[1],
    tl_h_i.a_mask[0],
    tl_h_i.a_address[11],
    tl_h_i.a_address[10],
    tl_h_i.a_address[9],
    tl_h_i.a_address[8],
    tl_h_i.a_address[7],
    tl_h_i.a_address[6],
    tl_h_i.a_address[5],
    tl_h_i.a_address[4],
    tl_h_i.a_address[3],
    tl_h_i.a_address[2],
    tl_h_i.a_source[7],
    tl_h_i.a_source[6]
  };
  assign real_toggle_subset_curr_chunk10_w = {
    tl_d_i.d_source[1],
    tl_d_i.d_source[0],
    tl_d_i.d_size[1],
    tl_d_i.d_size[0],
    tl_d_i.d_opcode[2],
    tl_d_i.d_opcode[1],
    tl_d_i.d_opcode[0],
    tl_d_i.d_sink[0],
    tl_d_i.d_source[7],
    tl_d_i.d_source[6],
    tl_d_i.d_source[5],
    tl_d_i.d_source[4],
    tl_d_i.d_source[3],
    tl_d_i.d_source[2],
    tl_d_i.d_valid,
    tl_d_i.a_ready
  };
  assign real_toggle_subset_curr_chunk11_w = {
    13'd0,
    tl_d_o.a_valid,
    tl_h_o.a_ready,
    tl_h_i.a_valid
  };
  assign real_toggle_subset_curr_chunk12_w = {
    tl_h_i.a_data[15],
    tl_h_i.a_data[14],
    tl_h_i.a_data[13],
    tl_h_i.a_data[12],
    tl_h_i.a_data[11],
    tl_h_i.a_data[10],
    tl_h_i.a_data[9],
    tl_h_i.a_data[8],
    tl_h_i.a_data[7],
    tl_h_i.a_data[6],
    tl_h_i.a_data[5],
    tl_h_i.a_data[4],
    tl_h_i.a_data[3],
    tl_h_i.a_data[2],
    tl_h_i.a_data[1],
    tl_h_i.a_data[0]
  };
  assign real_toggle_subset_curr_chunk13_w = {
    tl_h_i.a_data[31],
    tl_h_i.a_data[30],
    tl_h_i.a_data[29],
    tl_h_i.a_data[28],
    tl_h_i.a_data[27],
    tl_h_i.a_data[26],
    tl_h_i.a_data[25],
    tl_h_i.a_data[24],
    tl_h_i.a_data[23],
    tl_h_i.a_data[22],
    tl_h_i.a_data[21],
    tl_h_i.a_data[20],
    tl_h_i.a_data[19],
    tl_h_i.a_data[18],
    tl_h_i.a_data[17],
    tl_h_i.a_data[16]
  };
  assign real_toggle_subset_curr_chunk14_w = {
    host_rsp_observed_data_w[15],
    host_rsp_observed_data_w[14],
    host_rsp_observed_data_w[13],
    host_rsp_observed_data_w[12],
    host_rsp_observed_data_w[11],
    host_rsp_observed_data_w[10],
    host_rsp_observed_data_w[9],
    host_rsp_observed_data_w[8],
    host_rsp_observed_data_w[7],
    host_rsp_observed_data_w[6],
    host_rsp_observed_data_w[5],
    host_rsp_observed_data_w[4],
    host_rsp_observed_data_w[3],
    host_rsp_observed_data_w[2],
    host_rsp_observed_data_w[1],
    host_rsp_observed_data_w[0]
  };
  assign real_toggle_subset_curr_chunk15_w = {
    host_rsp_observed_data_w[31],
    host_rsp_observed_data_w[30],
    host_rsp_observed_data_w[29],
    host_rsp_observed_data_w[28],
    host_rsp_observed_data_w[27],
    host_rsp_observed_data_w[26],
    host_rsp_observed_data_w[25],
    host_rsp_observed_data_w[24],
    host_rsp_observed_data_w[23],
    host_rsp_observed_data_w[22],
    host_rsp_observed_data_w[21],
    host_rsp_observed_data_w[20],
    host_rsp_observed_data_w[19],
    host_rsp_observed_data_w[18],
    host_rsp_observed_data_w[17],
    host_rsp_observed_data_w[16]
  };
  assign real_toggle_subset_curr_chunk16_w = dut.reqfifo.gen_normal_fifo.storage[1][63:48];
  assign real_toggle_subset_curr_chunk17_w = dut.reqfifo.gen_normal_fifo.storage[1][79:64];
  assign real_toggle_subset_prev_chunk0_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk0_w;
  assign real_toggle_subset_prev_chunk1_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk1_w;
  assign real_toggle_subset_prev_chunk2_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk2_w;
  assign real_toggle_subset_prev_chunk3_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk3_w;
  assign real_toggle_subset_prev_chunk4_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk4_w;
  assign real_toggle_subset_prev_chunk5_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk5_w;
  assign real_toggle_subset_prev_chunk6_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk6_w;
  assign real_toggle_subset_prev_chunk7_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk7_w;
  assign real_toggle_subset_prev_chunk8_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk8_w;
  assign real_toggle_subset_prev_chunk9_d = reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk9_w;
  assign real_toggle_subset_prev_chunk10_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk10_w;
  assign real_toggle_subset_prev_chunk11_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk11_w;
  assign real_toggle_subset_prev_chunk12_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk12_w;
  assign real_toggle_subset_prev_chunk13_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk13_w;
  assign real_toggle_subset_prev_chunk14_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk14_w;
  assign real_toggle_subset_prev_chunk15_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk15_w;
  assign real_toggle_subset_prev_chunk16_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk16_w;
  assign real_toggle_subset_prev_chunk17_d =
      reset_like_w ? 16'd0 : real_toggle_subset_curr_chunk17_w;
  assign real_toggle_subset_hit_word0_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word0_q | {
          (real_toggle_subset_prev_chunk0_q[15] && !real_toggle_subset_curr_chunk0_w[15]),
          ((!real_toggle_subset_prev_chunk0_q[15]) && real_toggle_subset_curr_chunk0_w[15]),
          (real_toggle_subset_prev_chunk0_q[14] && !real_toggle_subset_curr_chunk0_w[14]),
          ((!real_toggle_subset_prev_chunk0_q[14]) && real_toggle_subset_curr_chunk0_w[14]),
          (real_toggle_subset_prev_chunk0_q[13] && !real_toggle_subset_curr_chunk0_w[13]),
          ((!real_toggle_subset_prev_chunk0_q[13]) && real_toggle_subset_curr_chunk0_w[13]),
          (real_toggle_subset_prev_chunk0_q[12] && !real_toggle_subset_curr_chunk0_w[12]),
          ((!real_toggle_subset_prev_chunk0_q[12]) && real_toggle_subset_curr_chunk0_w[12]),
          (real_toggle_subset_prev_chunk0_q[11] && !real_toggle_subset_curr_chunk0_w[11]),
          ((!real_toggle_subset_prev_chunk0_q[11]) && real_toggle_subset_curr_chunk0_w[11]),
          (real_toggle_subset_prev_chunk0_q[10] && !real_toggle_subset_curr_chunk0_w[10]),
          ((!real_toggle_subset_prev_chunk0_q[10]) && real_toggle_subset_curr_chunk0_w[10]),
          (real_toggle_subset_prev_chunk0_q[9] && !real_toggle_subset_curr_chunk0_w[9]),
          ((!real_toggle_subset_prev_chunk0_q[9]) && real_toggle_subset_curr_chunk0_w[9]),
          (real_toggle_subset_prev_chunk0_q[8] && !real_toggle_subset_curr_chunk0_w[8]),
          ((!real_toggle_subset_prev_chunk0_q[8]) && real_toggle_subset_curr_chunk0_w[8]),
          (real_toggle_subset_prev_chunk0_q[7] && !real_toggle_subset_curr_chunk0_w[7]),
          ((!real_toggle_subset_prev_chunk0_q[7]) && real_toggle_subset_curr_chunk0_w[7]),
          (real_toggle_subset_prev_chunk0_q[6] && !real_toggle_subset_curr_chunk0_w[6]),
          ((!real_toggle_subset_prev_chunk0_q[6]) && real_toggle_subset_curr_chunk0_w[6]),
          (real_toggle_subset_prev_chunk0_q[5] && !real_toggle_subset_curr_chunk0_w[5]),
          ((!real_toggle_subset_prev_chunk0_q[5]) && real_toggle_subset_curr_chunk0_w[5]),
          (real_toggle_subset_prev_chunk0_q[4] && !real_toggle_subset_curr_chunk0_w[4]),
          ((!real_toggle_subset_prev_chunk0_q[4]) && real_toggle_subset_curr_chunk0_w[4]),
          (real_toggle_subset_prev_chunk0_q[3] && !real_toggle_subset_curr_chunk0_w[3]),
          ((!real_toggle_subset_prev_chunk0_q[3]) && real_toggle_subset_curr_chunk0_w[3]),
          (real_toggle_subset_prev_chunk0_q[2] && !real_toggle_subset_curr_chunk0_w[2]),
          ((!real_toggle_subset_prev_chunk0_q[2]) && real_toggle_subset_curr_chunk0_w[2]),
          (real_toggle_subset_prev_chunk0_q[1] && !real_toggle_subset_curr_chunk0_w[1]),
          ((!real_toggle_subset_prev_chunk0_q[1]) && real_toggle_subset_curr_chunk0_w[1]),
          (real_toggle_subset_prev_chunk0_q[0] && !real_toggle_subset_curr_chunk0_w[0]),
          ((!real_toggle_subset_prev_chunk0_q[0]) && real_toggle_subset_curr_chunk0_w[0])
        });
  assign real_toggle_subset_hit_word1_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word1_q | {
          (real_toggle_subset_prev_chunk1_q[15] && !real_toggle_subset_curr_chunk1_w[15]),
          ((!real_toggle_subset_prev_chunk1_q[15]) && real_toggle_subset_curr_chunk1_w[15]),
          (real_toggle_subset_prev_chunk1_q[14] && !real_toggle_subset_curr_chunk1_w[14]),
          ((!real_toggle_subset_prev_chunk1_q[14]) && real_toggle_subset_curr_chunk1_w[14]),
          (real_toggle_subset_prev_chunk1_q[13] && !real_toggle_subset_curr_chunk1_w[13]),
          ((!real_toggle_subset_prev_chunk1_q[13]) && real_toggle_subset_curr_chunk1_w[13]),
          (real_toggle_subset_prev_chunk1_q[12] && !real_toggle_subset_curr_chunk1_w[12]),
          ((!real_toggle_subset_prev_chunk1_q[12]) && real_toggle_subset_curr_chunk1_w[12]),
          (real_toggle_subset_prev_chunk1_q[11] && !real_toggle_subset_curr_chunk1_w[11]),
          ((!real_toggle_subset_prev_chunk1_q[11]) && real_toggle_subset_curr_chunk1_w[11]),
          (real_toggle_subset_prev_chunk1_q[10] && !real_toggle_subset_curr_chunk1_w[10]),
          ((!real_toggle_subset_prev_chunk1_q[10]) && real_toggle_subset_curr_chunk1_w[10]),
          (real_toggle_subset_prev_chunk1_q[9] && !real_toggle_subset_curr_chunk1_w[9]),
          ((!real_toggle_subset_prev_chunk1_q[9]) && real_toggle_subset_curr_chunk1_w[9]),
          (real_toggle_subset_prev_chunk1_q[8] && !real_toggle_subset_curr_chunk1_w[8]),
          ((!real_toggle_subset_prev_chunk1_q[8]) && real_toggle_subset_curr_chunk1_w[8]),
          (real_toggle_subset_prev_chunk1_q[7] && !real_toggle_subset_curr_chunk1_w[7]),
          ((!real_toggle_subset_prev_chunk1_q[7]) && real_toggle_subset_curr_chunk1_w[7]),
          (real_toggle_subset_prev_chunk1_q[6] && !real_toggle_subset_curr_chunk1_w[6]),
          ((!real_toggle_subset_prev_chunk1_q[6]) && real_toggle_subset_curr_chunk1_w[6]),
          (real_toggle_subset_prev_chunk1_q[5] && !real_toggle_subset_curr_chunk1_w[5]),
          ((!real_toggle_subset_prev_chunk1_q[5]) && real_toggle_subset_curr_chunk1_w[5]),
          (real_toggle_subset_prev_chunk1_q[4] && !real_toggle_subset_curr_chunk1_w[4]),
          ((!real_toggle_subset_prev_chunk1_q[4]) && real_toggle_subset_curr_chunk1_w[4]),
          (real_toggle_subset_prev_chunk1_q[3] && !real_toggle_subset_curr_chunk1_w[3]),
          ((!real_toggle_subset_prev_chunk1_q[3]) && real_toggle_subset_curr_chunk1_w[3]),
          (real_toggle_subset_prev_chunk1_q[2] && !real_toggle_subset_curr_chunk1_w[2]),
          ((!real_toggle_subset_prev_chunk1_q[2]) && real_toggle_subset_curr_chunk1_w[2]),
          (real_toggle_subset_prev_chunk1_q[1] && !real_toggle_subset_curr_chunk1_w[1]),
          ((!real_toggle_subset_prev_chunk1_q[1]) && real_toggle_subset_curr_chunk1_w[1]),
          (real_toggle_subset_prev_chunk1_q[0] && !real_toggle_subset_curr_chunk1_w[0]),
          ((!real_toggle_subset_prev_chunk1_q[0]) && real_toggle_subset_curr_chunk1_w[0])
        });
  assign real_toggle_subset_hit_word2_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word2_q | {
          (real_toggle_subset_prev_chunk2_q[15] && !real_toggle_subset_curr_chunk2_w[15]),
          ((!real_toggle_subset_prev_chunk2_q[15]) && real_toggle_subset_curr_chunk2_w[15]),
          (real_toggle_subset_prev_chunk2_q[14] && !real_toggle_subset_curr_chunk2_w[14]),
          ((!real_toggle_subset_prev_chunk2_q[14]) && real_toggle_subset_curr_chunk2_w[14]),
          (real_toggle_subset_prev_chunk2_q[13] && !real_toggle_subset_curr_chunk2_w[13]),
          ((!real_toggle_subset_prev_chunk2_q[13]) && real_toggle_subset_curr_chunk2_w[13]),
          (real_toggle_subset_prev_chunk2_q[12] && !real_toggle_subset_curr_chunk2_w[12]),
          ((!real_toggle_subset_prev_chunk2_q[12]) && real_toggle_subset_curr_chunk2_w[12]),
          (real_toggle_subset_prev_chunk2_q[11] && !real_toggle_subset_curr_chunk2_w[11]),
          ((!real_toggle_subset_prev_chunk2_q[11]) && real_toggle_subset_curr_chunk2_w[11]),
          (real_toggle_subset_prev_chunk2_q[10] && !real_toggle_subset_curr_chunk2_w[10]),
          ((!real_toggle_subset_prev_chunk2_q[10]) && real_toggle_subset_curr_chunk2_w[10]),
          (real_toggle_subset_prev_chunk2_q[9] && !real_toggle_subset_curr_chunk2_w[9]),
          ((!real_toggle_subset_prev_chunk2_q[9]) && real_toggle_subset_curr_chunk2_w[9]),
          (real_toggle_subset_prev_chunk2_q[8] && !real_toggle_subset_curr_chunk2_w[8]),
          ((!real_toggle_subset_prev_chunk2_q[8]) && real_toggle_subset_curr_chunk2_w[8]),
          (real_toggle_subset_prev_chunk2_q[7] && !real_toggle_subset_curr_chunk2_w[7]),
          ((!real_toggle_subset_prev_chunk2_q[7]) && real_toggle_subset_curr_chunk2_w[7]),
          (real_toggle_subset_prev_chunk2_q[6] && !real_toggle_subset_curr_chunk2_w[6]),
          ((!real_toggle_subset_prev_chunk2_q[6]) && real_toggle_subset_curr_chunk2_w[6]),
          (real_toggle_subset_prev_chunk2_q[5] && !real_toggle_subset_curr_chunk2_w[5]),
          ((!real_toggle_subset_prev_chunk2_q[5]) && real_toggle_subset_curr_chunk2_w[5]),
          (real_toggle_subset_prev_chunk2_q[4] && !real_toggle_subset_curr_chunk2_w[4]),
          ((!real_toggle_subset_prev_chunk2_q[4]) && real_toggle_subset_curr_chunk2_w[4]),
          (real_toggle_subset_prev_chunk2_q[3] && !real_toggle_subset_curr_chunk2_w[3]),
          ((!real_toggle_subset_prev_chunk2_q[3]) && real_toggle_subset_curr_chunk2_w[3]),
          (real_toggle_subset_prev_chunk2_q[2] && !real_toggle_subset_curr_chunk2_w[2]),
          ((!real_toggle_subset_prev_chunk2_q[2]) && real_toggle_subset_curr_chunk2_w[2]),
          (real_toggle_subset_prev_chunk2_q[1] && !real_toggle_subset_curr_chunk2_w[1]),
          ((!real_toggle_subset_prev_chunk2_q[1]) && real_toggle_subset_curr_chunk2_w[1]),
          (real_toggle_subset_prev_chunk2_q[0] && !real_toggle_subset_curr_chunk2_w[0]),
          ((!real_toggle_subset_prev_chunk2_q[0]) && real_toggle_subset_curr_chunk2_w[0])
        });
  assign real_toggle_subset_hit_word3_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word3_q | {
          (real_toggle_subset_prev_chunk3_q[15] && !real_toggle_subset_curr_chunk3_w[15]),
          ((!real_toggle_subset_prev_chunk3_q[15]) && real_toggle_subset_curr_chunk3_w[15]),
          (real_toggle_subset_prev_chunk3_q[14] && !real_toggle_subset_curr_chunk3_w[14]),
          ((!real_toggle_subset_prev_chunk3_q[14]) && real_toggle_subset_curr_chunk3_w[14]),
          (real_toggle_subset_prev_chunk3_q[13] && !real_toggle_subset_curr_chunk3_w[13]),
          ((!real_toggle_subset_prev_chunk3_q[13]) && real_toggle_subset_curr_chunk3_w[13]),
          (real_toggle_subset_prev_chunk3_q[12] && !real_toggle_subset_curr_chunk3_w[12]),
          ((!real_toggle_subset_prev_chunk3_q[12]) && real_toggle_subset_curr_chunk3_w[12]),
          (real_toggle_subset_prev_chunk3_q[11] && !real_toggle_subset_curr_chunk3_w[11]),
          ((!real_toggle_subset_prev_chunk3_q[11]) && real_toggle_subset_curr_chunk3_w[11]),
          (real_toggle_subset_prev_chunk3_q[10] && !real_toggle_subset_curr_chunk3_w[10]),
          ((!real_toggle_subset_prev_chunk3_q[10]) && real_toggle_subset_curr_chunk3_w[10]),
          (real_toggle_subset_prev_chunk3_q[9] && !real_toggle_subset_curr_chunk3_w[9]),
          ((!real_toggle_subset_prev_chunk3_q[9]) && real_toggle_subset_curr_chunk3_w[9]),
          (real_toggle_subset_prev_chunk3_q[8] && !real_toggle_subset_curr_chunk3_w[8]),
          ((!real_toggle_subset_prev_chunk3_q[8]) && real_toggle_subset_curr_chunk3_w[8]),
          (real_toggle_subset_prev_chunk3_q[7] && !real_toggle_subset_curr_chunk3_w[7]),
          ((!real_toggle_subset_prev_chunk3_q[7]) && real_toggle_subset_curr_chunk3_w[7]),
          (real_toggle_subset_prev_chunk3_q[6] && !real_toggle_subset_curr_chunk3_w[6]),
          ((!real_toggle_subset_prev_chunk3_q[6]) && real_toggle_subset_curr_chunk3_w[6]),
          (real_toggle_subset_prev_chunk3_q[5] && !real_toggle_subset_curr_chunk3_w[5]),
          ((!real_toggle_subset_prev_chunk3_q[5]) && real_toggle_subset_curr_chunk3_w[5]),
          (real_toggle_subset_prev_chunk3_q[4] && !real_toggle_subset_curr_chunk3_w[4]),
          ((!real_toggle_subset_prev_chunk3_q[4]) && real_toggle_subset_curr_chunk3_w[4]),
          (real_toggle_subset_prev_chunk3_q[3] && !real_toggle_subset_curr_chunk3_w[3]),
          ((!real_toggle_subset_prev_chunk3_q[3]) && real_toggle_subset_curr_chunk3_w[3]),
          (real_toggle_subset_prev_chunk3_q[2] && !real_toggle_subset_curr_chunk3_w[2]),
          ((!real_toggle_subset_prev_chunk3_q[2]) && real_toggle_subset_curr_chunk3_w[2]),
          (real_toggle_subset_prev_chunk3_q[1] && !real_toggle_subset_curr_chunk3_w[1]),
          ((!real_toggle_subset_prev_chunk3_q[1]) && real_toggle_subset_curr_chunk3_w[1]),
          (real_toggle_subset_prev_chunk3_q[0] && !real_toggle_subset_curr_chunk3_w[0]),
          ((!real_toggle_subset_prev_chunk3_q[0]) && real_toggle_subset_curr_chunk3_w[0])
        });
  assign real_toggle_subset_hit_word4_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word4_q | {
          (real_toggle_subset_prev_chunk4_q[15] && !real_toggle_subset_curr_chunk4_w[15]),
          ((!real_toggle_subset_prev_chunk4_q[15]) && real_toggle_subset_curr_chunk4_w[15]),
          (real_toggle_subset_prev_chunk4_q[14] && !real_toggle_subset_curr_chunk4_w[14]),
          ((!real_toggle_subset_prev_chunk4_q[14]) && real_toggle_subset_curr_chunk4_w[14]),
          (real_toggle_subset_prev_chunk4_q[13] && !real_toggle_subset_curr_chunk4_w[13]),
          ((!real_toggle_subset_prev_chunk4_q[13]) && real_toggle_subset_curr_chunk4_w[13]),
          (real_toggle_subset_prev_chunk4_q[12] && !real_toggle_subset_curr_chunk4_w[12]),
          ((!real_toggle_subset_prev_chunk4_q[12]) && real_toggle_subset_curr_chunk4_w[12]),
          (real_toggle_subset_prev_chunk4_q[11] && !real_toggle_subset_curr_chunk4_w[11]),
          ((!real_toggle_subset_prev_chunk4_q[11]) && real_toggle_subset_curr_chunk4_w[11]),
          (real_toggle_subset_prev_chunk4_q[10] && !real_toggle_subset_curr_chunk4_w[10]),
          ((!real_toggle_subset_prev_chunk4_q[10]) && real_toggle_subset_curr_chunk4_w[10]),
          (real_toggle_subset_prev_chunk4_q[9] && !real_toggle_subset_curr_chunk4_w[9]),
          ((!real_toggle_subset_prev_chunk4_q[9]) && real_toggle_subset_curr_chunk4_w[9]),
          (real_toggle_subset_prev_chunk4_q[8] && !real_toggle_subset_curr_chunk4_w[8]),
          ((!real_toggle_subset_prev_chunk4_q[8]) && real_toggle_subset_curr_chunk4_w[8]),
          (real_toggle_subset_prev_chunk4_q[7] && !real_toggle_subset_curr_chunk4_w[7]),
          ((!real_toggle_subset_prev_chunk4_q[7]) && real_toggle_subset_curr_chunk4_w[7]),
          (real_toggle_subset_prev_chunk4_q[6] && !real_toggle_subset_curr_chunk4_w[6]),
          ((!real_toggle_subset_prev_chunk4_q[6]) && real_toggle_subset_curr_chunk4_w[6]),
          (real_toggle_subset_prev_chunk4_q[5] && !real_toggle_subset_curr_chunk4_w[5]),
          ((!real_toggle_subset_prev_chunk4_q[5]) && real_toggle_subset_curr_chunk4_w[5]),
          (real_toggle_subset_prev_chunk4_q[4] && !real_toggle_subset_curr_chunk4_w[4]),
          ((!real_toggle_subset_prev_chunk4_q[4]) && real_toggle_subset_curr_chunk4_w[4]),
          (real_toggle_subset_prev_chunk4_q[3] && !real_toggle_subset_curr_chunk4_w[3]),
          ((!real_toggle_subset_prev_chunk4_q[3]) && real_toggle_subset_curr_chunk4_w[3]),
          (real_toggle_subset_prev_chunk4_q[2] && !real_toggle_subset_curr_chunk4_w[2]),
          ((!real_toggle_subset_prev_chunk4_q[2]) && real_toggle_subset_curr_chunk4_w[2]),
          (real_toggle_subset_prev_chunk4_q[1] && !real_toggle_subset_curr_chunk4_w[1]),
          ((!real_toggle_subset_prev_chunk4_q[1]) && real_toggle_subset_curr_chunk4_w[1]),
          (real_toggle_subset_prev_chunk4_q[0] && !real_toggle_subset_curr_chunk4_w[0]),
          ((!real_toggle_subset_prev_chunk4_q[0]) && real_toggle_subset_curr_chunk4_w[0])
        });
  assign real_toggle_subset_hit_word5_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word5_q | {
          (real_toggle_subset_prev_chunk5_q[15] && !real_toggle_subset_curr_chunk5_w[15]),
          ((!real_toggle_subset_prev_chunk5_q[15]) && real_toggle_subset_curr_chunk5_w[15]),
          (real_toggle_subset_prev_chunk5_q[14] && !real_toggle_subset_curr_chunk5_w[14]),
          ((!real_toggle_subset_prev_chunk5_q[14]) && real_toggle_subset_curr_chunk5_w[14]),
          (real_toggle_subset_prev_chunk5_q[13] && !real_toggle_subset_curr_chunk5_w[13]),
          ((!real_toggle_subset_prev_chunk5_q[13]) && real_toggle_subset_curr_chunk5_w[13]),
          (real_toggle_subset_prev_chunk5_q[12] && !real_toggle_subset_curr_chunk5_w[12]),
          ((!real_toggle_subset_prev_chunk5_q[12]) && real_toggle_subset_curr_chunk5_w[12]),
          (real_toggle_subset_prev_chunk5_q[11] && !real_toggle_subset_curr_chunk5_w[11]),
          ((!real_toggle_subset_prev_chunk5_q[11]) && real_toggle_subset_curr_chunk5_w[11]),
          (real_toggle_subset_prev_chunk5_q[10] && !real_toggle_subset_curr_chunk5_w[10]),
          ((!real_toggle_subset_prev_chunk5_q[10]) && real_toggle_subset_curr_chunk5_w[10]),
          (real_toggle_subset_prev_chunk5_q[9] && !real_toggle_subset_curr_chunk5_w[9]),
          ((!real_toggle_subset_prev_chunk5_q[9]) && real_toggle_subset_curr_chunk5_w[9]),
          (real_toggle_subset_prev_chunk5_q[8] && !real_toggle_subset_curr_chunk5_w[8]),
          ((!real_toggle_subset_prev_chunk5_q[8]) && real_toggle_subset_curr_chunk5_w[8]),
          (real_toggle_subset_prev_chunk5_q[7] && !real_toggle_subset_curr_chunk5_w[7]),
          ((!real_toggle_subset_prev_chunk5_q[7]) && real_toggle_subset_curr_chunk5_w[7]),
          (real_toggle_subset_prev_chunk5_q[6] && !real_toggle_subset_curr_chunk5_w[6]),
          ((!real_toggle_subset_prev_chunk5_q[6]) && real_toggle_subset_curr_chunk5_w[6]),
          (real_toggle_subset_prev_chunk5_q[5] && !real_toggle_subset_curr_chunk5_w[5]),
          ((!real_toggle_subset_prev_chunk5_q[5]) && real_toggle_subset_curr_chunk5_w[5]),
          (real_toggle_subset_prev_chunk5_q[4] && !real_toggle_subset_curr_chunk5_w[4]),
          ((!real_toggle_subset_prev_chunk5_q[4]) && real_toggle_subset_curr_chunk5_w[4]),
          (real_toggle_subset_prev_chunk5_q[3] && !real_toggle_subset_curr_chunk5_w[3]),
          ((!real_toggle_subset_prev_chunk5_q[3]) && real_toggle_subset_curr_chunk5_w[3]),
          (real_toggle_subset_prev_chunk5_q[2] && !real_toggle_subset_curr_chunk5_w[2]),
          ((!real_toggle_subset_prev_chunk5_q[2]) && real_toggle_subset_curr_chunk5_w[2]),
          (real_toggle_subset_prev_chunk5_q[1] && !real_toggle_subset_curr_chunk5_w[1]),
          ((!real_toggle_subset_prev_chunk5_q[1]) && real_toggle_subset_curr_chunk5_w[1]),
          (real_toggle_subset_prev_chunk5_q[0] && !real_toggle_subset_curr_chunk5_w[0]),
          ((!real_toggle_subset_prev_chunk5_q[0]) && real_toggle_subset_curr_chunk5_w[0])
        });
  assign real_toggle_subset_hit_word6_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word6_q | {
          (real_toggle_subset_prev_chunk6_q[15] && !real_toggle_subset_curr_chunk6_w[15]),
          ((!real_toggle_subset_prev_chunk6_q[15]) && real_toggle_subset_curr_chunk6_w[15]),
          (real_toggle_subset_prev_chunk6_q[14] && !real_toggle_subset_curr_chunk6_w[14]),
          ((!real_toggle_subset_prev_chunk6_q[14]) && real_toggle_subset_curr_chunk6_w[14]),
          (real_toggle_subset_prev_chunk6_q[13] && !real_toggle_subset_curr_chunk6_w[13]),
          ((!real_toggle_subset_prev_chunk6_q[13]) && real_toggle_subset_curr_chunk6_w[13]),
          (real_toggle_subset_prev_chunk6_q[12] && !real_toggle_subset_curr_chunk6_w[12]),
          ((!real_toggle_subset_prev_chunk6_q[12]) && real_toggle_subset_curr_chunk6_w[12]),
          (real_toggle_subset_prev_chunk6_q[11] && !real_toggle_subset_curr_chunk6_w[11]),
          ((!real_toggle_subset_prev_chunk6_q[11]) && real_toggle_subset_curr_chunk6_w[11]),
          (real_toggle_subset_prev_chunk6_q[10] && !real_toggle_subset_curr_chunk6_w[10]),
          ((!real_toggle_subset_prev_chunk6_q[10]) && real_toggle_subset_curr_chunk6_w[10]),
          (real_toggle_subset_prev_chunk6_q[9] && !real_toggle_subset_curr_chunk6_w[9]),
          ((!real_toggle_subset_prev_chunk6_q[9]) && real_toggle_subset_curr_chunk6_w[9]),
          (real_toggle_subset_prev_chunk6_q[8] && !real_toggle_subset_curr_chunk6_w[8]),
          ((!real_toggle_subset_prev_chunk6_q[8]) && real_toggle_subset_curr_chunk6_w[8]),
          (real_toggle_subset_prev_chunk6_q[7] && !real_toggle_subset_curr_chunk6_w[7]),
          ((!real_toggle_subset_prev_chunk6_q[7]) && real_toggle_subset_curr_chunk6_w[7]),
          (real_toggle_subset_prev_chunk6_q[6] && !real_toggle_subset_curr_chunk6_w[6]),
          ((!real_toggle_subset_prev_chunk6_q[6]) && real_toggle_subset_curr_chunk6_w[6]),
          (real_toggle_subset_prev_chunk6_q[5] && !real_toggle_subset_curr_chunk6_w[5]),
          ((!real_toggle_subset_prev_chunk6_q[5]) && real_toggle_subset_curr_chunk6_w[5]),
          (real_toggle_subset_prev_chunk6_q[4] && !real_toggle_subset_curr_chunk6_w[4]),
          ((!real_toggle_subset_prev_chunk6_q[4]) && real_toggle_subset_curr_chunk6_w[4]),
          (real_toggle_subset_prev_chunk6_q[3] && !real_toggle_subset_curr_chunk6_w[3]),
          ((!real_toggle_subset_prev_chunk6_q[3]) && real_toggle_subset_curr_chunk6_w[3]),
          (real_toggle_subset_prev_chunk6_q[2] && !real_toggle_subset_curr_chunk6_w[2]),
          ((!real_toggle_subset_prev_chunk6_q[2]) && real_toggle_subset_curr_chunk6_w[2]),
          (real_toggle_subset_prev_chunk6_q[1] && !real_toggle_subset_curr_chunk6_w[1]),
          ((!real_toggle_subset_prev_chunk6_q[1]) && real_toggle_subset_curr_chunk6_w[1]),
          (real_toggle_subset_prev_chunk6_q[0] && !real_toggle_subset_curr_chunk6_w[0]),
          ((!real_toggle_subset_prev_chunk6_q[0]) && real_toggle_subset_curr_chunk6_w[0])
        });
  assign real_toggle_subset_hit_word7_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word7_q | {
          (real_toggle_subset_prev_chunk7_q[15] && !real_toggle_subset_curr_chunk7_w[15]),
          ((!real_toggle_subset_prev_chunk7_q[15]) && real_toggle_subset_curr_chunk7_w[15]),
          (real_toggle_subset_prev_chunk7_q[14] && !real_toggle_subset_curr_chunk7_w[14]),
          ((!real_toggle_subset_prev_chunk7_q[14]) && real_toggle_subset_curr_chunk7_w[14]),
          (real_toggle_subset_prev_chunk7_q[13] && !real_toggle_subset_curr_chunk7_w[13]),
          ((!real_toggle_subset_prev_chunk7_q[13]) && real_toggle_subset_curr_chunk7_w[13]),
          (real_toggle_subset_prev_chunk7_q[12] && !real_toggle_subset_curr_chunk7_w[12]),
          ((!real_toggle_subset_prev_chunk7_q[12]) && real_toggle_subset_curr_chunk7_w[12]),
          (real_toggle_subset_prev_chunk7_q[11] && !real_toggle_subset_curr_chunk7_w[11]),
          ((!real_toggle_subset_prev_chunk7_q[11]) && real_toggle_subset_curr_chunk7_w[11]),
          (real_toggle_subset_prev_chunk7_q[10] && !real_toggle_subset_curr_chunk7_w[10]),
          ((!real_toggle_subset_prev_chunk7_q[10]) && real_toggle_subset_curr_chunk7_w[10]),
          (real_toggle_subset_prev_chunk7_q[9] && !real_toggle_subset_curr_chunk7_w[9]),
          ((!real_toggle_subset_prev_chunk7_q[9]) && real_toggle_subset_curr_chunk7_w[9]),
          (real_toggle_subset_prev_chunk7_q[8] && !real_toggle_subset_curr_chunk7_w[8]),
          ((!real_toggle_subset_prev_chunk7_q[8]) && real_toggle_subset_curr_chunk7_w[8]),
          (real_toggle_subset_prev_chunk7_q[7] && !real_toggle_subset_curr_chunk7_w[7]),
          ((!real_toggle_subset_prev_chunk7_q[7]) && real_toggle_subset_curr_chunk7_w[7]),
          (real_toggle_subset_prev_chunk7_q[6] && !real_toggle_subset_curr_chunk7_w[6]),
          ((!real_toggle_subset_prev_chunk7_q[6]) && real_toggle_subset_curr_chunk7_w[6]),
          (real_toggle_subset_prev_chunk7_q[5] && !real_toggle_subset_curr_chunk7_w[5]),
          ((!real_toggle_subset_prev_chunk7_q[5]) && real_toggle_subset_curr_chunk7_w[5]),
          (real_toggle_subset_prev_chunk7_q[4] && !real_toggle_subset_curr_chunk7_w[4]),
          ((!real_toggle_subset_prev_chunk7_q[4]) && real_toggle_subset_curr_chunk7_w[4]),
          (real_toggle_subset_prev_chunk7_q[3] && !real_toggle_subset_curr_chunk7_w[3]),
          ((!real_toggle_subset_prev_chunk7_q[3]) && real_toggle_subset_curr_chunk7_w[3]),
          (real_toggle_subset_prev_chunk7_q[2] && !real_toggle_subset_curr_chunk7_w[2]),
          ((!real_toggle_subset_prev_chunk7_q[2]) && real_toggle_subset_curr_chunk7_w[2]),
          (real_toggle_subset_prev_chunk7_q[1] && !real_toggle_subset_curr_chunk7_w[1]),
          ((!real_toggle_subset_prev_chunk7_q[1]) && real_toggle_subset_curr_chunk7_w[1]),
          (real_toggle_subset_prev_chunk7_q[0] && !real_toggle_subset_curr_chunk7_w[0]),
          ((!real_toggle_subset_prev_chunk7_q[0]) && real_toggle_subset_curr_chunk7_w[0])
        });
  assign real_toggle_subset_hit_word8_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word8_q | {
          (real_toggle_subset_prev_chunk8_q[15] && !real_toggle_subset_curr_chunk8_w[15]),
          ((!real_toggle_subset_prev_chunk8_q[15]) && real_toggle_subset_curr_chunk8_w[15]),
          (real_toggle_subset_prev_chunk8_q[14] && !real_toggle_subset_curr_chunk8_w[14]),
          ((!real_toggle_subset_prev_chunk8_q[14]) && real_toggle_subset_curr_chunk8_w[14]),
          (real_toggle_subset_prev_chunk8_q[13] && !real_toggle_subset_curr_chunk8_w[13]),
          ((!real_toggle_subset_prev_chunk8_q[13]) && real_toggle_subset_curr_chunk8_w[13]),
          (real_toggle_subset_prev_chunk8_q[12] && !real_toggle_subset_curr_chunk8_w[12]),
          ((!real_toggle_subset_prev_chunk8_q[12]) && real_toggle_subset_curr_chunk8_w[12]),
          (real_toggle_subset_prev_chunk8_q[11] && !real_toggle_subset_curr_chunk8_w[11]),
          ((!real_toggle_subset_prev_chunk8_q[11]) && real_toggle_subset_curr_chunk8_w[11]),
          (real_toggle_subset_prev_chunk8_q[10] && !real_toggle_subset_curr_chunk8_w[10]),
          ((!real_toggle_subset_prev_chunk8_q[10]) && real_toggle_subset_curr_chunk8_w[10]),
          (real_toggle_subset_prev_chunk8_q[9] && !real_toggle_subset_curr_chunk8_w[9]),
          ((!real_toggle_subset_prev_chunk8_q[9]) && real_toggle_subset_curr_chunk8_w[9]),
          (real_toggle_subset_prev_chunk8_q[8] && !real_toggle_subset_curr_chunk8_w[8]),
          ((!real_toggle_subset_prev_chunk8_q[8]) && real_toggle_subset_curr_chunk8_w[8]),
          (real_toggle_subset_prev_chunk8_q[7] && !real_toggle_subset_curr_chunk8_w[7]),
          ((!real_toggle_subset_prev_chunk8_q[7]) && real_toggle_subset_curr_chunk8_w[7]),
          (real_toggle_subset_prev_chunk8_q[6] && !real_toggle_subset_curr_chunk8_w[6]),
          ((!real_toggle_subset_prev_chunk8_q[6]) && real_toggle_subset_curr_chunk8_w[6]),
          (real_toggle_subset_prev_chunk8_q[5] && !real_toggle_subset_curr_chunk8_w[5]),
          ((!real_toggle_subset_prev_chunk8_q[5]) && real_toggle_subset_curr_chunk8_w[5]),
          (real_toggle_subset_prev_chunk8_q[4] && !real_toggle_subset_curr_chunk8_w[4]),
          ((!real_toggle_subset_prev_chunk8_q[4]) && real_toggle_subset_curr_chunk8_w[4]),
          (real_toggle_subset_prev_chunk8_q[3] && !real_toggle_subset_curr_chunk8_w[3]),
          ((!real_toggle_subset_prev_chunk8_q[3]) && real_toggle_subset_curr_chunk8_w[3]),
          (real_toggle_subset_prev_chunk8_q[2] && !real_toggle_subset_curr_chunk8_w[2]),
          ((!real_toggle_subset_prev_chunk8_q[2]) && real_toggle_subset_curr_chunk8_w[2]),
          (real_toggle_subset_prev_chunk8_q[1] && !real_toggle_subset_curr_chunk8_w[1]),
          ((!real_toggle_subset_prev_chunk8_q[1]) && real_toggle_subset_curr_chunk8_w[1]),
          (real_toggle_subset_prev_chunk8_q[0] && !real_toggle_subset_curr_chunk8_w[0]),
          ((!real_toggle_subset_prev_chunk8_q[0]) && real_toggle_subset_curr_chunk8_w[0])
        });
  assign real_toggle_subset_hit_word9_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word9_q | {
          (real_toggle_subset_prev_chunk9_q[15] && !real_toggle_subset_curr_chunk9_w[15]),
          ((!real_toggle_subset_prev_chunk9_q[15]) && real_toggle_subset_curr_chunk9_w[15]),
          (real_toggle_subset_prev_chunk9_q[14] && !real_toggle_subset_curr_chunk9_w[14]),
          ((!real_toggle_subset_prev_chunk9_q[14]) && real_toggle_subset_curr_chunk9_w[14]),
          (real_toggle_subset_prev_chunk9_q[13] && !real_toggle_subset_curr_chunk9_w[13]),
          ((!real_toggle_subset_prev_chunk9_q[13]) && real_toggle_subset_curr_chunk9_w[13]),
          (real_toggle_subset_prev_chunk9_q[12] && !real_toggle_subset_curr_chunk9_w[12]),
          ((!real_toggle_subset_prev_chunk9_q[12]) && real_toggle_subset_curr_chunk9_w[12]),
          (real_toggle_subset_prev_chunk9_q[11] && !real_toggle_subset_curr_chunk9_w[11]),
          ((!real_toggle_subset_prev_chunk9_q[11]) && real_toggle_subset_curr_chunk9_w[11]),
          (real_toggle_subset_prev_chunk9_q[10] && !real_toggle_subset_curr_chunk9_w[10]),
          ((!real_toggle_subset_prev_chunk9_q[10]) && real_toggle_subset_curr_chunk9_w[10]),
          (real_toggle_subset_prev_chunk9_q[9] && !real_toggle_subset_curr_chunk9_w[9]),
          ((!real_toggle_subset_prev_chunk9_q[9]) && real_toggle_subset_curr_chunk9_w[9]),
          (real_toggle_subset_prev_chunk9_q[8] && !real_toggle_subset_curr_chunk9_w[8]),
          ((!real_toggle_subset_prev_chunk9_q[8]) && real_toggle_subset_curr_chunk9_w[8]),
          (real_toggle_subset_prev_chunk9_q[7] && !real_toggle_subset_curr_chunk9_w[7]),
          ((!real_toggle_subset_prev_chunk9_q[7]) && real_toggle_subset_curr_chunk9_w[7]),
          (real_toggle_subset_prev_chunk9_q[6] && !real_toggle_subset_curr_chunk9_w[6]),
          ((!real_toggle_subset_prev_chunk9_q[6]) && real_toggle_subset_curr_chunk9_w[6]),
          (real_toggle_subset_prev_chunk9_q[5] && !real_toggle_subset_curr_chunk9_w[5]),
          ((!real_toggle_subset_prev_chunk9_q[5]) && real_toggle_subset_curr_chunk9_w[5]),
          (real_toggle_subset_prev_chunk9_q[4] && !real_toggle_subset_curr_chunk9_w[4]),
          ((!real_toggle_subset_prev_chunk9_q[4]) && real_toggle_subset_curr_chunk9_w[4]),
          (real_toggle_subset_prev_chunk9_q[3] && !real_toggle_subset_curr_chunk9_w[3]),
          ((!real_toggle_subset_prev_chunk9_q[3]) && real_toggle_subset_curr_chunk9_w[3]),
          (real_toggle_subset_prev_chunk9_q[2] && !real_toggle_subset_curr_chunk9_w[2]),
          ((!real_toggle_subset_prev_chunk9_q[2]) && real_toggle_subset_curr_chunk9_w[2]),
          (real_toggle_subset_prev_chunk9_q[1] && !real_toggle_subset_curr_chunk9_w[1]),
          ((!real_toggle_subset_prev_chunk9_q[1]) && real_toggle_subset_curr_chunk9_w[1]),
          (real_toggle_subset_prev_chunk9_q[0] && !real_toggle_subset_curr_chunk9_w[0]),
          ((!real_toggle_subset_prev_chunk9_q[0]) && real_toggle_subset_curr_chunk9_w[0])
        });
  assign real_toggle_subset_hit_word10_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word10_q | {
          (real_toggle_subset_prev_chunk10_q[15] && !real_toggle_subset_curr_chunk10_w[15]),
          ((!real_toggle_subset_prev_chunk10_q[15]) && real_toggle_subset_curr_chunk10_w[15]),
          (real_toggle_subset_prev_chunk10_q[14] && !real_toggle_subset_curr_chunk10_w[14]),
          ((!real_toggle_subset_prev_chunk10_q[14]) && real_toggle_subset_curr_chunk10_w[14]),
          (real_toggle_subset_prev_chunk10_q[13] && !real_toggle_subset_curr_chunk10_w[13]),
          ((!real_toggle_subset_prev_chunk10_q[13]) && real_toggle_subset_curr_chunk10_w[13]),
          (real_toggle_subset_prev_chunk10_q[12] && !real_toggle_subset_curr_chunk10_w[12]),
          ((!real_toggle_subset_prev_chunk10_q[12]) && real_toggle_subset_curr_chunk10_w[12]),
          (real_toggle_subset_prev_chunk10_q[11] && !real_toggle_subset_curr_chunk10_w[11]),
          ((!real_toggle_subset_prev_chunk10_q[11]) && real_toggle_subset_curr_chunk10_w[11]),
          (real_toggle_subset_prev_chunk10_q[10] && !real_toggle_subset_curr_chunk10_w[10]),
          ((!real_toggle_subset_prev_chunk10_q[10]) && real_toggle_subset_curr_chunk10_w[10]),
          (real_toggle_subset_prev_chunk10_q[9] && !real_toggle_subset_curr_chunk10_w[9]),
          ((!real_toggle_subset_prev_chunk10_q[9]) && real_toggle_subset_curr_chunk10_w[9]),
          (real_toggle_subset_prev_chunk10_q[8] && !real_toggle_subset_curr_chunk10_w[8]),
          ((!real_toggle_subset_prev_chunk10_q[8]) && real_toggle_subset_curr_chunk10_w[8]),
          (real_toggle_subset_prev_chunk10_q[7] && !real_toggle_subset_curr_chunk10_w[7]),
          ((!real_toggle_subset_prev_chunk10_q[7]) && real_toggle_subset_curr_chunk10_w[7]),
          (real_toggle_subset_prev_chunk10_q[6] && !real_toggle_subset_curr_chunk10_w[6]),
          ((!real_toggle_subset_prev_chunk10_q[6]) && real_toggle_subset_curr_chunk10_w[6]),
          (real_toggle_subset_prev_chunk10_q[5] && !real_toggle_subset_curr_chunk10_w[5]),
          ((!real_toggle_subset_prev_chunk10_q[5]) && real_toggle_subset_curr_chunk10_w[5]),
          (real_toggle_subset_prev_chunk10_q[4] && !real_toggle_subset_curr_chunk10_w[4]),
          ((!real_toggle_subset_prev_chunk10_q[4]) && real_toggle_subset_curr_chunk10_w[4]),
          (real_toggle_subset_prev_chunk10_q[3] && !real_toggle_subset_curr_chunk10_w[3]),
          ((!real_toggle_subset_prev_chunk10_q[3]) && real_toggle_subset_curr_chunk10_w[3]),
          (real_toggle_subset_prev_chunk10_q[2] && !real_toggle_subset_curr_chunk10_w[2]),
          ((!real_toggle_subset_prev_chunk10_q[2]) && real_toggle_subset_curr_chunk10_w[2]),
          (real_toggle_subset_prev_chunk10_q[1] && !real_toggle_subset_curr_chunk10_w[1]),
          ((!real_toggle_subset_prev_chunk10_q[1]) && real_toggle_subset_curr_chunk10_w[1]),
          (real_toggle_subset_prev_chunk10_q[0] && !real_toggle_subset_curr_chunk10_w[0]),
          ((!real_toggle_subset_prev_chunk10_q[0]) && real_toggle_subset_curr_chunk10_w[0])
        });
  assign real_toggle_subset_hit_word11_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word11_q | {
          (real_toggle_subset_prev_chunk11_q[15] && !real_toggle_subset_curr_chunk11_w[15]),
          ((!real_toggle_subset_prev_chunk11_q[15]) && real_toggle_subset_curr_chunk11_w[15]),
          (real_toggle_subset_prev_chunk11_q[14] && !real_toggle_subset_curr_chunk11_w[14]),
          ((!real_toggle_subset_prev_chunk11_q[14]) && real_toggle_subset_curr_chunk11_w[14]),
          (real_toggle_subset_prev_chunk11_q[13] && !real_toggle_subset_curr_chunk11_w[13]),
          ((!real_toggle_subset_prev_chunk11_q[13]) && real_toggle_subset_curr_chunk11_w[13]),
          (real_toggle_subset_prev_chunk11_q[12] && !real_toggle_subset_curr_chunk11_w[12]),
          ((!real_toggle_subset_prev_chunk11_q[12]) && real_toggle_subset_curr_chunk11_w[12]),
          (real_toggle_subset_prev_chunk11_q[11] && !real_toggle_subset_curr_chunk11_w[11]),
          ((!real_toggle_subset_prev_chunk11_q[11]) && real_toggle_subset_curr_chunk11_w[11]),
          (real_toggle_subset_prev_chunk11_q[10] && !real_toggle_subset_curr_chunk11_w[10]),
          ((!real_toggle_subset_prev_chunk11_q[10]) && real_toggle_subset_curr_chunk11_w[10]),
          (real_toggle_subset_prev_chunk11_q[9] && !real_toggle_subset_curr_chunk11_w[9]),
          ((!real_toggle_subset_prev_chunk11_q[9]) && real_toggle_subset_curr_chunk11_w[9]),
          (real_toggle_subset_prev_chunk11_q[8] && !real_toggle_subset_curr_chunk11_w[8]),
          ((!real_toggle_subset_prev_chunk11_q[8]) && real_toggle_subset_curr_chunk11_w[8]),
          (real_toggle_subset_prev_chunk11_q[7] && !real_toggle_subset_curr_chunk11_w[7]),
          ((!real_toggle_subset_prev_chunk11_q[7]) && real_toggle_subset_curr_chunk11_w[7]),
          (real_toggle_subset_prev_chunk11_q[6] && !real_toggle_subset_curr_chunk11_w[6]),
          ((!real_toggle_subset_prev_chunk11_q[6]) && real_toggle_subset_curr_chunk11_w[6]),
          (real_toggle_subset_prev_chunk11_q[5] && !real_toggle_subset_curr_chunk11_w[5]),
          ((!real_toggle_subset_prev_chunk11_q[5]) && real_toggle_subset_curr_chunk11_w[5]),
          (real_toggle_subset_prev_chunk11_q[4] && !real_toggle_subset_curr_chunk11_w[4]),
          ((!real_toggle_subset_prev_chunk11_q[4]) && real_toggle_subset_curr_chunk11_w[4]),
          (real_toggle_subset_prev_chunk11_q[3] && !real_toggle_subset_curr_chunk11_w[3]),
          ((!real_toggle_subset_prev_chunk11_q[3]) && real_toggle_subset_curr_chunk11_w[3]),
          (real_toggle_subset_prev_chunk11_q[2] && !real_toggle_subset_curr_chunk11_w[2]),
          ((!real_toggle_subset_prev_chunk11_q[2]) && real_toggle_subset_curr_chunk11_w[2]),
          (real_toggle_subset_prev_chunk11_q[1] && !real_toggle_subset_curr_chunk11_w[1]),
          ((!real_toggle_subset_prev_chunk11_q[1]) && real_toggle_subset_curr_chunk11_w[1]),
          (real_toggle_subset_prev_chunk11_q[0] && !real_toggle_subset_curr_chunk11_w[0]),
          ((!real_toggle_subset_prev_chunk11_q[0]) && real_toggle_subset_curr_chunk11_w[0])
        });
  assign real_toggle_subset_hit_word12_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word12_q | {
          (real_toggle_subset_prev_chunk12_q[15] && !real_toggle_subset_curr_chunk12_w[15]),
          ((!real_toggle_subset_prev_chunk12_q[15]) && real_toggle_subset_curr_chunk12_w[15]),
          (real_toggle_subset_prev_chunk12_q[14] && !real_toggle_subset_curr_chunk12_w[14]),
          ((!real_toggle_subset_prev_chunk12_q[14]) && real_toggle_subset_curr_chunk12_w[14]),
          (real_toggle_subset_prev_chunk12_q[13] && !real_toggle_subset_curr_chunk12_w[13]),
          ((!real_toggle_subset_prev_chunk12_q[13]) && real_toggle_subset_curr_chunk12_w[13]),
          (real_toggle_subset_prev_chunk12_q[12] && !real_toggle_subset_curr_chunk12_w[12]),
          ((!real_toggle_subset_prev_chunk12_q[12]) && real_toggle_subset_curr_chunk12_w[12]),
          (real_toggle_subset_prev_chunk12_q[11] && !real_toggle_subset_curr_chunk12_w[11]),
          ((!real_toggle_subset_prev_chunk12_q[11]) && real_toggle_subset_curr_chunk12_w[11]),
          (real_toggle_subset_prev_chunk12_q[10] && !real_toggle_subset_curr_chunk12_w[10]),
          ((!real_toggle_subset_prev_chunk12_q[10]) && real_toggle_subset_curr_chunk12_w[10]),
          (real_toggle_subset_prev_chunk12_q[9] && !real_toggle_subset_curr_chunk12_w[9]),
          ((!real_toggle_subset_prev_chunk12_q[9]) && real_toggle_subset_curr_chunk12_w[9]),
          (real_toggle_subset_prev_chunk12_q[8] && !real_toggle_subset_curr_chunk12_w[8]),
          ((!real_toggle_subset_prev_chunk12_q[8]) && real_toggle_subset_curr_chunk12_w[8]),
          (real_toggle_subset_prev_chunk12_q[7] && !real_toggle_subset_curr_chunk12_w[7]),
          ((!real_toggle_subset_prev_chunk12_q[7]) && real_toggle_subset_curr_chunk12_w[7]),
          (real_toggle_subset_prev_chunk12_q[6] && !real_toggle_subset_curr_chunk12_w[6]),
          ((!real_toggle_subset_prev_chunk12_q[6]) && real_toggle_subset_curr_chunk12_w[6]),
          (real_toggle_subset_prev_chunk12_q[5] && !real_toggle_subset_curr_chunk12_w[5]),
          ((!real_toggle_subset_prev_chunk12_q[5]) && real_toggle_subset_curr_chunk12_w[5]),
          (real_toggle_subset_prev_chunk12_q[4] && !real_toggle_subset_curr_chunk12_w[4]),
          ((!real_toggle_subset_prev_chunk12_q[4]) && real_toggle_subset_curr_chunk12_w[4]),
          (real_toggle_subset_prev_chunk12_q[3] && !real_toggle_subset_curr_chunk12_w[3]),
          ((!real_toggle_subset_prev_chunk12_q[3]) && real_toggle_subset_curr_chunk12_w[3]),
          (real_toggle_subset_prev_chunk12_q[2] && !real_toggle_subset_curr_chunk12_w[2]),
          ((!real_toggle_subset_prev_chunk12_q[2]) && real_toggle_subset_curr_chunk12_w[2]),
          (real_toggle_subset_prev_chunk12_q[1] && !real_toggle_subset_curr_chunk12_w[1]),
          ((!real_toggle_subset_prev_chunk12_q[1]) && real_toggle_subset_curr_chunk12_w[1]),
          (real_toggle_subset_prev_chunk12_q[0] && !real_toggle_subset_curr_chunk12_w[0]),
          ((!real_toggle_subset_prev_chunk12_q[0]) && real_toggle_subset_curr_chunk12_w[0])
        });
  assign real_toggle_subset_hit_word13_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word13_q | {
          (real_toggle_subset_prev_chunk13_q[15] && !real_toggle_subset_curr_chunk13_w[15]),
          ((!real_toggle_subset_prev_chunk13_q[15]) && real_toggle_subset_curr_chunk13_w[15]),
          (real_toggle_subset_prev_chunk13_q[14] && !real_toggle_subset_curr_chunk13_w[14]),
          ((!real_toggle_subset_prev_chunk13_q[14]) && real_toggle_subset_curr_chunk13_w[14]),
          (real_toggle_subset_prev_chunk13_q[13] && !real_toggle_subset_curr_chunk13_w[13]),
          ((!real_toggle_subset_prev_chunk13_q[13]) && real_toggle_subset_curr_chunk13_w[13]),
          (real_toggle_subset_prev_chunk13_q[12] && !real_toggle_subset_curr_chunk13_w[12]),
          ((!real_toggle_subset_prev_chunk13_q[12]) && real_toggle_subset_curr_chunk13_w[12]),
          (real_toggle_subset_prev_chunk13_q[11] && !real_toggle_subset_curr_chunk13_w[11]),
          ((!real_toggle_subset_prev_chunk13_q[11]) && real_toggle_subset_curr_chunk13_w[11]),
          (real_toggle_subset_prev_chunk13_q[10] && !real_toggle_subset_curr_chunk13_w[10]),
          ((!real_toggle_subset_prev_chunk13_q[10]) && real_toggle_subset_curr_chunk13_w[10]),
          (real_toggle_subset_prev_chunk13_q[9] && !real_toggle_subset_curr_chunk13_w[9]),
          ((!real_toggle_subset_prev_chunk13_q[9]) && real_toggle_subset_curr_chunk13_w[9]),
          (real_toggle_subset_prev_chunk13_q[8] && !real_toggle_subset_curr_chunk13_w[8]),
          ((!real_toggle_subset_prev_chunk13_q[8]) && real_toggle_subset_curr_chunk13_w[8]),
          (real_toggle_subset_prev_chunk13_q[7] && !real_toggle_subset_curr_chunk13_w[7]),
          ((!real_toggle_subset_prev_chunk13_q[7]) && real_toggle_subset_curr_chunk13_w[7]),
          (real_toggle_subset_prev_chunk13_q[6] && !real_toggle_subset_curr_chunk13_w[6]),
          ((!real_toggle_subset_prev_chunk13_q[6]) && real_toggle_subset_curr_chunk13_w[6]),
          (real_toggle_subset_prev_chunk13_q[5] && !real_toggle_subset_curr_chunk13_w[5]),
          ((!real_toggle_subset_prev_chunk13_q[5]) && real_toggle_subset_curr_chunk13_w[5]),
          (real_toggle_subset_prev_chunk13_q[4] && !real_toggle_subset_curr_chunk13_w[4]),
          ((!real_toggle_subset_prev_chunk13_q[4]) && real_toggle_subset_curr_chunk13_w[4]),
          (real_toggle_subset_prev_chunk13_q[3] && !real_toggle_subset_curr_chunk13_w[3]),
          ((!real_toggle_subset_prev_chunk13_q[3]) && real_toggle_subset_curr_chunk13_w[3]),
          (real_toggle_subset_prev_chunk13_q[2] && !real_toggle_subset_curr_chunk13_w[2]),
          ((!real_toggle_subset_prev_chunk13_q[2]) && real_toggle_subset_curr_chunk13_w[2]),
          (real_toggle_subset_prev_chunk13_q[1] && !real_toggle_subset_curr_chunk13_w[1]),
          ((!real_toggle_subset_prev_chunk13_q[1]) && real_toggle_subset_curr_chunk13_w[1]),
          (real_toggle_subset_prev_chunk13_q[0] && !real_toggle_subset_curr_chunk13_w[0]),
          ((!real_toggle_subset_prev_chunk13_q[0]) && real_toggle_subset_curr_chunk13_w[0])
        });
  assign real_toggle_subset_hit_word14_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word14_q | {
          (real_toggle_subset_prev_chunk14_q[15] && !real_toggle_subset_curr_chunk14_w[15]),
          ((!real_toggle_subset_prev_chunk14_q[15]) && real_toggle_subset_curr_chunk14_w[15]),
          (real_toggle_subset_prev_chunk14_q[14] && !real_toggle_subset_curr_chunk14_w[14]),
          ((!real_toggle_subset_prev_chunk14_q[14]) && real_toggle_subset_curr_chunk14_w[14]),
          (real_toggle_subset_prev_chunk14_q[13] && !real_toggle_subset_curr_chunk14_w[13]),
          ((!real_toggle_subset_prev_chunk14_q[13]) && real_toggle_subset_curr_chunk14_w[13]),
          (real_toggle_subset_prev_chunk14_q[12] && !real_toggle_subset_curr_chunk14_w[12]),
          ((!real_toggle_subset_prev_chunk14_q[12]) && real_toggle_subset_curr_chunk14_w[12]),
          (real_toggle_subset_prev_chunk14_q[11] && !real_toggle_subset_curr_chunk14_w[11]),
          ((!real_toggle_subset_prev_chunk14_q[11]) && real_toggle_subset_curr_chunk14_w[11]),
          (real_toggle_subset_prev_chunk14_q[10] && !real_toggle_subset_curr_chunk14_w[10]),
          ((!real_toggle_subset_prev_chunk14_q[10]) && real_toggle_subset_curr_chunk14_w[10]),
          (real_toggle_subset_prev_chunk14_q[9] && !real_toggle_subset_curr_chunk14_w[9]),
          ((!real_toggle_subset_prev_chunk14_q[9]) && real_toggle_subset_curr_chunk14_w[9]),
          (real_toggle_subset_prev_chunk14_q[8] && !real_toggle_subset_curr_chunk14_w[8]),
          ((!real_toggle_subset_prev_chunk14_q[8]) && real_toggle_subset_curr_chunk14_w[8]),
          (real_toggle_subset_prev_chunk14_q[7] && !real_toggle_subset_curr_chunk14_w[7]),
          ((!real_toggle_subset_prev_chunk14_q[7]) && real_toggle_subset_curr_chunk14_w[7]),
          (real_toggle_subset_prev_chunk14_q[6] && !real_toggle_subset_curr_chunk14_w[6]),
          ((!real_toggle_subset_prev_chunk14_q[6]) && real_toggle_subset_curr_chunk14_w[6]),
          (real_toggle_subset_prev_chunk14_q[5] && !real_toggle_subset_curr_chunk14_w[5]),
          ((!real_toggle_subset_prev_chunk14_q[5]) && real_toggle_subset_curr_chunk14_w[5]),
          (real_toggle_subset_prev_chunk14_q[4] && !real_toggle_subset_curr_chunk14_w[4]),
          ((!real_toggle_subset_prev_chunk14_q[4]) && real_toggle_subset_curr_chunk14_w[4]),
          (real_toggle_subset_prev_chunk14_q[3] && !real_toggle_subset_curr_chunk14_w[3]),
          ((!real_toggle_subset_prev_chunk14_q[3]) && real_toggle_subset_curr_chunk14_w[3]),
          (real_toggle_subset_prev_chunk14_q[2] && !real_toggle_subset_curr_chunk14_w[2]),
          ((!real_toggle_subset_prev_chunk14_q[2]) && real_toggle_subset_curr_chunk14_w[2]),
          (real_toggle_subset_prev_chunk14_q[1] && !real_toggle_subset_curr_chunk14_w[1]),
          ((!real_toggle_subset_prev_chunk14_q[1]) && real_toggle_subset_curr_chunk14_w[1]),
          (real_toggle_subset_prev_chunk14_q[0] && !real_toggle_subset_curr_chunk14_w[0]),
          ((!real_toggle_subset_prev_chunk14_q[0]) && real_toggle_subset_curr_chunk14_w[0])
        });
  assign real_toggle_subset_hit_word15_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word15_q | {
          (real_toggle_subset_prev_chunk15_q[15] && !real_toggle_subset_curr_chunk15_w[15]),
          ((!real_toggle_subset_prev_chunk15_q[15]) && real_toggle_subset_curr_chunk15_w[15]),
          (real_toggle_subset_prev_chunk15_q[14] && !real_toggle_subset_curr_chunk15_w[14]),
          ((!real_toggle_subset_prev_chunk15_q[14]) && real_toggle_subset_curr_chunk15_w[14]),
          (real_toggle_subset_prev_chunk15_q[13] && !real_toggle_subset_curr_chunk15_w[13]),
          ((!real_toggle_subset_prev_chunk15_q[13]) && real_toggle_subset_curr_chunk15_w[13]),
          (real_toggle_subset_prev_chunk15_q[12] && !real_toggle_subset_curr_chunk15_w[12]),
          ((!real_toggle_subset_prev_chunk15_q[12]) && real_toggle_subset_curr_chunk15_w[12]),
          (real_toggle_subset_prev_chunk15_q[11] && !real_toggle_subset_curr_chunk15_w[11]),
          ((!real_toggle_subset_prev_chunk15_q[11]) && real_toggle_subset_curr_chunk15_w[11]),
          (real_toggle_subset_prev_chunk15_q[10] && !real_toggle_subset_curr_chunk15_w[10]),
          ((!real_toggle_subset_prev_chunk15_q[10]) && real_toggle_subset_curr_chunk15_w[10]),
          (real_toggle_subset_prev_chunk15_q[9] && !real_toggle_subset_curr_chunk15_w[9]),
          ((!real_toggle_subset_prev_chunk15_q[9]) && real_toggle_subset_curr_chunk15_w[9]),
          (real_toggle_subset_prev_chunk15_q[8] && !real_toggle_subset_curr_chunk15_w[8]),
          ((!real_toggle_subset_prev_chunk15_q[8]) && real_toggle_subset_curr_chunk15_w[8]),
          (real_toggle_subset_prev_chunk15_q[7] && !real_toggle_subset_curr_chunk15_w[7]),
          ((!real_toggle_subset_prev_chunk15_q[7]) && real_toggle_subset_curr_chunk15_w[7]),
          (real_toggle_subset_prev_chunk15_q[6] && !real_toggle_subset_curr_chunk15_w[6]),
          ((!real_toggle_subset_prev_chunk15_q[6]) && real_toggle_subset_curr_chunk15_w[6]),
          (real_toggle_subset_prev_chunk15_q[5] && !real_toggle_subset_curr_chunk15_w[5]),
          ((!real_toggle_subset_prev_chunk15_q[5]) && real_toggle_subset_curr_chunk15_w[5]),
          (real_toggle_subset_prev_chunk15_q[4] && !real_toggle_subset_curr_chunk15_w[4]),
          ((!real_toggle_subset_prev_chunk15_q[4]) && real_toggle_subset_curr_chunk15_w[4]),
          (real_toggle_subset_prev_chunk15_q[3] && !real_toggle_subset_curr_chunk15_w[3]),
          ((!real_toggle_subset_prev_chunk15_q[3]) && real_toggle_subset_curr_chunk15_w[3]),
          (real_toggle_subset_prev_chunk15_q[2] && !real_toggle_subset_curr_chunk15_w[2]),
          ((!real_toggle_subset_prev_chunk15_q[2]) && real_toggle_subset_curr_chunk15_w[2]),
          (real_toggle_subset_prev_chunk15_q[1] && !real_toggle_subset_curr_chunk15_w[1]),
          ((!real_toggle_subset_prev_chunk15_q[1]) && real_toggle_subset_curr_chunk15_w[1]),
          (real_toggle_subset_prev_chunk15_q[0] && !real_toggle_subset_curr_chunk15_w[0]),
          ((!real_toggle_subset_prev_chunk15_q[0]) && real_toggle_subset_curr_chunk15_w[0])
        });
  assign real_toggle_subset_hit_word16_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word16_q | {
          (real_toggle_subset_prev_chunk16_q[15] && !real_toggle_subset_curr_chunk16_w[15]),
          ((!real_toggle_subset_prev_chunk16_q[15]) && real_toggle_subset_curr_chunk16_w[15]),
          (real_toggle_subset_prev_chunk16_q[14] && !real_toggle_subset_curr_chunk16_w[14]),
          ((!real_toggle_subset_prev_chunk16_q[14]) && real_toggle_subset_curr_chunk16_w[14]),
          (real_toggle_subset_prev_chunk16_q[13] && !real_toggle_subset_curr_chunk16_w[13]),
          ((!real_toggle_subset_prev_chunk16_q[13]) && real_toggle_subset_curr_chunk16_w[13]),
          (real_toggle_subset_prev_chunk16_q[12] && !real_toggle_subset_curr_chunk16_w[12]),
          ((!real_toggle_subset_prev_chunk16_q[12]) && real_toggle_subset_curr_chunk16_w[12]),
          (real_toggle_subset_prev_chunk16_q[11] && !real_toggle_subset_curr_chunk16_w[11]),
          ((!real_toggle_subset_prev_chunk16_q[11]) && real_toggle_subset_curr_chunk16_w[11]),
          (real_toggle_subset_prev_chunk16_q[10] && !real_toggle_subset_curr_chunk16_w[10]),
          ((!real_toggle_subset_prev_chunk16_q[10]) && real_toggle_subset_curr_chunk16_w[10]),
          (real_toggle_subset_prev_chunk16_q[9] && !real_toggle_subset_curr_chunk16_w[9]),
          ((!real_toggle_subset_prev_chunk16_q[9]) && real_toggle_subset_curr_chunk16_w[9]),
          (real_toggle_subset_prev_chunk16_q[8] && !real_toggle_subset_curr_chunk16_w[8]),
          ((!real_toggle_subset_prev_chunk16_q[8]) && real_toggle_subset_curr_chunk16_w[8]),
          (real_toggle_subset_prev_chunk16_q[7] && !real_toggle_subset_curr_chunk16_w[7]),
          ((!real_toggle_subset_prev_chunk16_q[7]) && real_toggle_subset_curr_chunk16_w[7]),
          (real_toggle_subset_prev_chunk16_q[6] && !real_toggle_subset_curr_chunk16_w[6]),
          ((!real_toggle_subset_prev_chunk16_q[6]) && real_toggle_subset_curr_chunk16_w[6]),
          (real_toggle_subset_prev_chunk16_q[5] && !real_toggle_subset_curr_chunk16_w[5]),
          ((!real_toggle_subset_prev_chunk16_q[5]) && real_toggle_subset_curr_chunk16_w[5]),
          (real_toggle_subset_prev_chunk16_q[4] && !real_toggle_subset_curr_chunk16_w[4]),
          ((!real_toggle_subset_prev_chunk16_q[4]) && real_toggle_subset_curr_chunk16_w[4]),
          (real_toggle_subset_prev_chunk16_q[3] && !real_toggle_subset_curr_chunk16_w[3]),
          ((!real_toggle_subset_prev_chunk16_q[3]) && real_toggle_subset_curr_chunk16_w[3]),
          (real_toggle_subset_prev_chunk16_q[2] && !real_toggle_subset_curr_chunk16_w[2]),
          ((!real_toggle_subset_prev_chunk16_q[2]) && real_toggle_subset_curr_chunk16_w[2]),
          (real_toggle_subset_prev_chunk16_q[1] && !real_toggle_subset_curr_chunk16_w[1]),
          ((!real_toggle_subset_prev_chunk16_q[1]) && real_toggle_subset_curr_chunk16_w[1]),
          (real_toggle_subset_prev_chunk16_q[0] && !real_toggle_subset_curr_chunk16_w[0]),
          ((!real_toggle_subset_prev_chunk16_q[0]) && real_toggle_subset_curr_chunk16_w[0])
        });
  assign real_toggle_subset_hit_word17_d = reset_like_w
      ? 32'd0
      : (real_toggle_subset_hit_word17_q | {
          (real_toggle_subset_prev_chunk17_q[15] && !real_toggle_subset_curr_chunk17_w[15]),
          ((!real_toggle_subset_prev_chunk17_q[15]) && real_toggle_subset_curr_chunk17_w[15]),
          (real_toggle_subset_prev_chunk17_q[14] && !real_toggle_subset_curr_chunk17_w[14]),
          ((!real_toggle_subset_prev_chunk17_q[14]) && real_toggle_subset_curr_chunk17_w[14]),
          (real_toggle_subset_prev_chunk17_q[13] && !real_toggle_subset_curr_chunk17_w[13]),
          ((!real_toggle_subset_prev_chunk17_q[13]) && real_toggle_subset_curr_chunk17_w[13]),
          (real_toggle_subset_prev_chunk17_q[12] && !real_toggle_subset_curr_chunk17_w[12]),
          ((!real_toggle_subset_prev_chunk17_q[12]) && real_toggle_subset_curr_chunk17_w[12]),
          (real_toggle_subset_prev_chunk17_q[11] && !real_toggle_subset_curr_chunk17_w[11]),
          ((!real_toggle_subset_prev_chunk17_q[11]) && real_toggle_subset_curr_chunk17_w[11]),
          (real_toggle_subset_prev_chunk17_q[10] && !real_toggle_subset_curr_chunk17_w[10]),
          ((!real_toggle_subset_prev_chunk17_q[10]) && real_toggle_subset_curr_chunk17_w[10]),
          (real_toggle_subset_prev_chunk17_q[9] && !real_toggle_subset_curr_chunk17_w[9]),
          ((!real_toggle_subset_prev_chunk17_q[9]) && real_toggle_subset_curr_chunk17_w[9]),
          (real_toggle_subset_prev_chunk17_q[8] && !real_toggle_subset_curr_chunk17_w[8]),
          ((!real_toggle_subset_prev_chunk17_q[8]) && real_toggle_subset_curr_chunk17_w[8]),
          (real_toggle_subset_prev_chunk17_q[7] && !real_toggle_subset_curr_chunk17_w[7]),
          ((!real_toggle_subset_prev_chunk17_q[7]) && real_toggle_subset_curr_chunk17_w[7]),
          (real_toggle_subset_prev_chunk17_q[6] && !real_toggle_subset_curr_chunk17_w[6]),
          ((!real_toggle_subset_prev_chunk17_q[6]) && real_toggle_subset_curr_chunk17_w[6]),
          (real_toggle_subset_prev_chunk17_q[5] && !real_toggle_subset_curr_chunk17_w[5]),
          ((!real_toggle_subset_prev_chunk17_q[5]) && real_toggle_subset_curr_chunk17_w[5]),
          (real_toggle_subset_prev_chunk17_q[4] && !real_toggle_subset_curr_chunk17_w[4]),
          ((!real_toggle_subset_prev_chunk17_q[4]) && real_toggle_subset_curr_chunk17_w[4]),
          (real_toggle_subset_prev_chunk17_q[3] && !real_toggle_subset_curr_chunk17_w[3]),
          ((!real_toggle_subset_prev_chunk17_q[3]) && real_toggle_subset_curr_chunk17_w[3]),
          (real_toggle_subset_prev_chunk17_q[2] && !real_toggle_subset_curr_chunk17_w[2]),
          ((!real_toggle_subset_prev_chunk17_q[2]) && real_toggle_subset_curr_chunk17_w[2]),
          (real_toggle_subset_prev_chunk17_q[1] && !real_toggle_subset_curr_chunk17_w[1]),
          ((!real_toggle_subset_prev_chunk17_q[1]) && real_toggle_subset_curr_chunk17_w[1]),
          (real_toggle_subset_prev_chunk17_q[0] && !real_toggle_subset_curr_chunk17_w[0]),
          ((!real_toggle_subset_prev_chunk17_q[0]) && real_toggle_subset_curr_chunk17_w[0])
        });

  always_ff @(posedge clk_i) begin
    cycle_count_q <= cycle_count_d;
    bootstrapped_q <= bootstrapped_d;
    phase_q <= phase_d;
    reset_cycles_remaining_q <= reset_cycles_remaining_d;
    warmup_cycles_remaining_q <= warmup_cycles_remaining_d;
    traffic_cycles_remaining_q <= traffic_cycles_remaining_d;
    drain_cycles_remaining_q <= drain_cycles_remaining_d;
    rand_state_q <= rand_state_d;
    req_pending_valid_q <= req_pending_valid_d;
    req_pending_trace_active_q <= req_pending_trace_active_d;
    req_pending_trace_index_q <= req_pending_trace_index_d;
    req_forward_trace_active_q <= req_forward_trace_active_d;
    req_forward_trace_index_q <= req_forward_trace_index_d;
    req_pending_opcode_q <= req_pending_opcode_d;
    req_pending_param_q <= req_pending_param_d;
    req_pending_size_q <= req_pending_size_d;
    req_pending_source_q <= req_pending_source_d;
    req_pending_address_q <= req_pending_address_d;
    req_pending_mask_q <= req_pending_mask_d;
    req_pending_data_q <= req_pending_data_d;
    req_pending_spare_q <= req_pending_spare_d;
    trace_step_q <= trace_step_d;
    direct_trace_step_q <= direct_trace_step_d;
    direct_req_done_q <= direct_req_done_d;
    direct_rsp_done_q <= direct_rsp_done_d;
    direct_rsp_delay_q <= direct_rsp_delay_d;
    req_burst_trace_active_q <= req_burst_trace_active_d;
    req_burst_trace_index_q <= req_burst_trace_index_d;
    req_burst_remaining_q <= req_burst_remaining_d;
    req_burst_opcode_q <= req_burst_opcode_d;
    req_burst_param_q <= req_burst_param_d;
    req_burst_size_q <= req_burst_size_d;
    req_burst_source_q <= req_burst_source_d;
    req_burst_address_q <= req_burst_address_d;
    req_burst_mask_q <= req_burst_mask_d;
    req_burst_data_q <= req_burst_data_d;
    req_burst_spare_q <= req_burst_spare_d;
    direct_rsp_hold_valid_q <= direct_rsp_hold_valid_d;
    direct_rsp_hold_opcode_q <= direct_rsp_hold_opcode_d;
    direct_rsp_hold_size_q <= direct_rsp_hold_size_d;
    direct_rsp_hold_source_q <= direct_rsp_hold_source_d;
    direct_rsp_hold_data_q <= direct_rsp_hold_data_d;
    direct_rsp_hold_error_q <= direct_rsp_hold_error_d;
    rsp_pending_valid_q <= rsp_pending_valid_d;
    rsp_pending_opcode_q <= rsp_pending_opcode_d;
    rsp_pending_param_q <= rsp_pending_param_d;
    rsp_pending_size_q <= rsp_pending_size_d;
    rsp_pending_source_q <= rsp_pending_source_d;
    rsp_pending_sink_q <= rsp_pending_sink_d;
    rsp_pending_data_q <= rsp_pending_data_d;
    rsp_pending_error_q <= rsp_pending_error_d;
    rsp_pending_spare_q <= rsp_pending_spare_d;
    rsp_head_q <= rsp_head_d;
    rsp_tail_q <= rsp_tail_d;
    rsp_count_q <= rsp_count_d;
    for (queue_idx = 0; queue_idx < QueueDepth; queue_idx++) begin
      rsp_size_queue_q[queue_idx] <= rsp_size_queue_d[queue_idx];
      rsp_source_queue_q[queue_idx] <= rsp_source_queue_d[queue_idx];
      rsp_req_opcode_queue_q[queue_idx] <= rsp_req_opcode_queue_d[queue_idx];
      rsp_req_address_queue_q[queue_idx] <= rsp_req_address_queue_d[queue_idx];
      rsp_req_data_queue_q[queue_idx] <= rsp_req_data_queue_d[queue_idx];
      rsp_delay_queue_q[queue_idx] <= rsp_delay_queue_d[queue_idx];
      rsp_trace_valid_queue_q[queue_idx] <= rsp_trace_valid_queue_d[queue_idx];
      rsp_trace_opcode_queue_q[queue_idx] <= rsp_trace_opcode_queue_d[queue_idx];
      rsp_trace_size_queue_q[queue_idx] <= rsp_trace_size_queue_d[queue_idx];
      rsp_trace_source_queue_q[queue_idx] <= rsp_trace_source_queue_d[queue_idx];
      rsp_trace_has_data_queue_q[queue_idx] <= rsp_trace_has_data_queue_d[queue_idx];
      rsp_trace_data_queue_q[queue_idx] <= rsp_trace_data_queue_d[queue_idx];
      rsp_trace_error_queue_q[queue_idx] <= rsp_trace_error_queue_d[queue_idx];
      rsp_trace_host_ready_mode_queue_q[queue_idx] <= rsp_trace_host_ready_mode_queue_d[queue_idx];
    end
    if (direct_trace_mode_w && direct_trace_active_w && !direct_trace_done_w) begin
      for (trace_idx = 0; trace_idx < (TraceDepth - 1); trace_idx++) begin
        trace_req_opcode_q[trace_idx] <= trace_req_opcode_q[trace_idx + 1];
        trace_req_param_q[trace_idx] <= trace_req_param_q[trace_idx + 1];
        trace_req_size_q[trace_idx] <= trace_req_size_q[trace_idx + 1];
        trace_req_address_q[trace_idx] <= trace_req_address_q[trace_idx + 1];
        trace_req_mask_q[trace_idx] <= trace_req_mask_q[trace_idx + 1];
        trace_req_data_q[trace_idx] <= trace_req_data_q[trace_idx + 1];
        trace_req_source_q[trace_idx] <= trace_req_source_q[trace_idx + 1];
        trace_req_burst_len_q[trace_idx] <= trace_req_burst_len_q[trace_idx + 1];
        trace_req_spare_q[trace_idx] <= trace_req_spare_q[trace_idx + 1];
        trace_rsp_valid_q[trace_idx] <= trace_rsp_valid_q[trace_idx + 1];
        trace_rsp_opcode_q[trace_idx] <= trace_rsp_opcode_q[trace_idx + 1];
        trace_rsp_size_q[trace_idx] <= trace_rsp_size_q[trace_idx + 1];
        trace_rsp_source_q[trace_idx] <= trace_rsp_source_q[trace_idx + 1];
        trace_rsp_has_data_q[trace_idx] <= trace_rsp_has_data_q[trace_idx + 1];
        trace_rsp_data_q[trace_idx] <= trace_rsp_data_q[trace_idx + 1];
        trace_rsp_delay_q[trace_idx] <= trace_rsp_delay_q[trace_idx + 1];
        trace_rsp_error_q[trace_idx] <= trace_rsp_error_q[trace_idx + 1];
        trace_host_ready_mode_q[trace_idx] <= trace_host_ready_mode_q[trace_idx + 1];
        trace_device_ready_mode_q[trace_idx] <= trace_device_ready_mode_q[trace_idx + 1];
        trace_req_valid_mode_q[trace_idx] <= trace_req_valid_mode_q[trace_idx + 1];
      end
      trace_req_opcode_q[TraceDepth - 1] <= '0;
      trace_req_param_q[TraceDepth - 1] <= '0;
      trace_req_size_q[TraceDepth - 1] <= top_pkg::TL_SZW'(2);
      trace_req_address_q[TraceDepth - 1] <= '0;
      trace_req_mask_q[TraceDepth - 1] <= '1;
      trace_req_data_q[TraceDepth - 1] <= '0;
      trace_req_source_q[TraceDepth - 1] <= '0;
      trace_req_burst_len_q[TraceDepth - 1] <= 32'd0;
      trace_req_spare_q[TraceDepth - 1] <= 1'b0;
      trace_rsp_valid_q[TraceDepth - 1] <= 1'b0;
      trace_rsp_opcode_q[TraceDepth - 1] <= 3'd0;
      trace_rsp_size_q[TraceDepth - 1] <= top_pkg::TL_SZW'(2);
      trace_rsp_source_q[TraceDepth - 1] <= '0;
      trace_rsp_has_data_q[TraceDepth - 1] <= 1'b0;
      trace_rsp_data_q[TraceDepth - 1] <= '0;
      trace_rsp_delay_q[TraceDepth - 1] <= 32'd0;
      trace_rsp_error_q[TraceDepth - 1] <= 1'b0;
      trace_host_ready_mode_q[TraceDepth - 1] <= 2'd0;
      trace_device_ready_mode_q[TraceDepth - 1] <= 2'd0;
      trace_req_valid_mode_q[TraceDepth - 1] <= 2'd0;
    end
    host_req_accepted_q <= host_req_accepted_d;
    device_req_accepted_q <= device_req_accepted_d;
    device_rsp_accepted_q <= device_rsp_accepted_d;
    host_rsp_accepted_q <= host_rsp_accepted_d;
    rsp_queue_overflow_q <= rsp_queue_overflow_d;
    progress_signature_q <= progress_signature_d;
    toggle_prev_word0_q <= toggle_prev_word0_d;
    toggle_prev_word1_q <= toggle_prev_word1_d;
    toggle_prev_word2_q <= toggle_prev_word2_d;
    toggle_hit_word0_q <= toggle_hit_word0_d;
    toggle_hit_word1_q <= toggle_hit_word1_d;
    toggle_hit_word2_q <= toggle_hit_word2_d;
    real_toggle_subset_prev_chunk0_q <= real_toggle_subset_prev_chunk0_d;
    real_toggle_subset_prev_chunk1_q <= real_toggle_subset_prev_chunk1_d;
    real_toggle_subset_prev_chunk2_q <= real_toggle_subset_prev_chunk2_d;
    real_toggle_subset_prev_chunk3_q <= real_toggle_subset_prev_chunk3_d;
    real_toggle_subset_prev_chunk4_q <= real_toggle_subset_prev_chunk4_d;
    real_toggle_subset_prev_chunk5_q <= real_toggle_subset_prev_chunk5_d;
    real_toggle_subset_prev_chunk6_q <= real_toggle_subset_prev_chunk6_d;
    real_toggle_subset_prev_chunk7_q <= real_toggle_subset_prev_chunk7_d;
    real_toggle_subset_prev_chunk8_q <= real_toggle_subset_prev_chunk8_d;
    real_toggle_subset_prev_chunk9_q <= real_toggle_subset_prev_chunk9_d;
    real_toggle_subset_prev_chunk10_q <= real_toggle_subset_prev_chunk10_d;
    real_toggle_subset_prev_chunk11_q <= real_toggle_subset_prev_chunk11_d;
    real_toggle_subset_prev_chunk12_q <= real_toggle_subset_prev_chunk12_d;
    real_toggle_subset_prev_chunk13_q <= real_toggle_subset_prev_chunk13_d;
    real_toggle_subset_prev_chunk14_q <= real_toggle_subset_prev_chunk14_d;
    real_toggle_subset_prev_chunk15_q <= real_toggle_subset_prev_chunk15_d;
    real_toggle_subset_prev_chunk16_q <= real_toggle_subset_prev_chunk16_d;
    real_toggle_subset_prev_chunk17_q <= real_toggle_subset_prev_chunk17_d;
    real_toggle_subset_hit_word0_q <= real_toggle_subset_hit_word0_d;
    real_toggle_subset_hit_word1_q <= real_toggle_subset_hit_word1_d;
    real_toggle_subset_hit_word2_q <= real_toggle_subset_hit_word2_d;
    real_toggle_subset_hit_word3_q <= real_toggle_subset_hit_word3_d;
    real_toggle_subset_hit_word4_q <= real_toggle_subset_hit_word4_d;
    real_toggle_subset_hit_word5_q <= real_toggle_subset_hit_word5_d;
    real_toggle_subset_hit_word6_q <= real_toggle_subset_hit_word6_d;
    real_toggle_subset_hit_word7_q <= real_toggle_subset_hit_word7_d;
    real_toggle_subset_hit_word8_q <= real_toggle_subset_hit_word8_d;
    real_toggle_subset_hit_word9_q <= real_toggle_subset_hit_word9_d;
    real_toggle_subset_hit_word10_q <= real_toggle_subset_hit_word10_d;
    real_toggle_subset_hit_word11_q <= real_toggle_subset_hit_word11_d;
    real_toggle_subset_hit_word12_q <= real_toggle_subset_hit_word12_d;
    real_toggle_subset_hit_word13_q <= real_toggle_subset_hit_word13_d;
    real_toggle_subset_hit_word14_q <= real_toggle_subset_hit_word14_d;
    real_toggle_subset_hit_word15_q <= real_toggle_subset_hit_word15_d;
    real_toggle_subset_hit_word16_q <= real_toggle_subset_hit_word16_d;
    real_toggle_subset_hit_word17_q <= real_toggle_subset_hit_word17_d;
    focused_wave_word7_q <= focused_wave_word5_q;
    focused_wave_word6_q <= focused_wave_word4_q;
    focused_wave_word5_q <= focused_wave_word3_q;
    focused_wave_word4_q <= focused_wave_word2_q;
    focused_wave_word3_q <= focused_wave_word1_q;
    focused_wave_word2_q <= focused_wave_word0_q;
    focused_wave_word1_q <= focused_wave_pack_b_w;
    focused_wave_word0_q <= focused_wave_pack_a_w;
    max_reqfifo_depth_q <= max_reqfifo_depth_d;
    max_rspfifo_depth_q <= max_rspfifo_depth_d;
    req_handshake_seen_q <= req_handshake_seen_d;
    rsp_handshake_seen_q <= rsp_handshake_seen_d;
    host_rsp_handshake_seen_q <= host_rsp_handshake_seen_d;
    direct_trace_active_seen_q <= direct_trace_active_seen_d;
    direct_req_drive_seen_q <= direct_req_drive_seen_d;
    direct_req_ready_seen_q <= direct_req_ready_seen_d;
    direct_req_handshake_seen_q <= direct_req_handshake_seen_d;
    direct_rsp_drive_seen_q <= direct_rsp_drive_seen_d;
    direct_rsp_handshake_seen_q <= direct_rsp_handshake_seen_d;
    trace_req_active_seen_q <= trace_req_active_seen_d;
    req_spawn_seen_q <= req_spawn_seen_d;
    req_ready_seen_q <= req_ready_seen_d;
    req_blocked_seen_q <= req_blocked_seen_d;
    reqfifo_full_seen_q <= reqfifo_full_seen_d;
    reqfifo_under_rst_seen_q <= reqfifo_under_rst_seen_d;
    device_a_ready_seen_q <= device_a_ready_seen_d;
    device_a_valid_seen_q <= device_a_valid_seen_d;
    device_ready_force_high_seen_q <= device_ready_force_high_seen_d;
    trace_req_fill_hold_seen_q <= trace_req_fill_hold_seen_d;
    trace_host_ready_default_seen_q <= trace_host_ready_default_seen_d;
    trace_rsp_fill_hold_seen_q <= trace_rsp_fill_hold_seen_d;
    host_d_ready_seen_q <= host_d_ready_seen_d;
    host_d_valid_seen_q <= host_d_valid_seen_d;
    device_rsp_ackdata_seen_q <= device_rsp_ackdata_seen_d;
    host_rsp_ackdata_seen_q <= host_rsp_ackdata_seen_d;
    device_rsp_payload_upper_seen_q <= device_rsp_payload_upper_seen_d;
    host_rsp_payload_upper_seen_q <= host_rsp_payload_upper_seen_d;
    device_rsp_payload_upper_accept_seen_q <=
        device_rsp_payload_upper_accept_seen_d;
    host_rsp_payload_upper_accept_seen_q <=
        host_rsp_payload_upper_accept_seen_d;
    host_raw_rsp_ackdata_seen_q <= host_raw_rsp_ackdata_seen_d;
    host_raw_rsp_payload_upper_seen_q <= host_raw_rsp_payload_upper_seen_d;
    first_device_rsp_seen_q <= first_device_rsp_seen_d;
    first_device_rsp_opcode_q <= first_device_rsp_opcode_d;
    first_device_rsp_data_upper_q <= first_device_rsp_data_upper_d;
    first_host_rsp_seen_q <= first_host_rsp_seen_d;
    first_host_rsp_opcode_q <= first_host_rsp_opcode_d;
    first_host_rsp_data_upper_q <= first_host_rsp_data_upper_d;
    last_device_rsp_seen_q <= last_device_rsp_seen_d;
    last_device_rsp_opcode_q <= last_device_rsp_opcode_d;
    last_device_rsp_data_q <= last_device_rsp_data_d;
    rsp_trace_override_seen_q <= rsp_trace_override_seen_d;
    rsp_trace_head_valid_seen_q <= rsp_trace_head_valid_seen_d;
    rsp_trace_has_data_seen_q <= rsp_trace_has_data_seen_d;
    rsp_spawn_has_data_seen_q <= rsp_spawn_has_data_seen_d;
    rsp_spawn_ackdata_seen_q <= rsp_spawn_ackdata_seen_d;
    rsp_spawn_opcode_or_q <= rsp_spawn_opcode_or_d;
    rsp_active_opcode_or_q <= rsp_active_opcode_or_d;
    device_rsp_opcode_or_q <= device_rsp_opcode_or_d;
    host_rsp_opcode_or_q <= host_rsp_opcode_or_d;
    host_raw_rsp_opcode_or_q <= host_raw_rsp_opcode_or_d;
    reqfifo_nonempty_seen_q <= reqfifo_nonempty_seen_d;
    rspfifo_nonempty_seen_q <= rspfifo_nonempty_seen_d;
    a_data_mid_or_q <= a_data_mid_or_d;
    a_address_window_or_q <= a_address_window_or_d;
    device_d_data_low_or_q <= device_d_data_low_or_d;
    device_d_data_upper_or_q <= device_d_data_upper_or_d;
    d_data_low_or_q <= d_data_low_or_d;
    a_data_upper_or_q <= a_data_upper_or_d;
    d_data_upper_or_q <= d_data_upper_or_d;
    focused_metric_word0_q <= {
      4'd0,
      max_rspfifo_depth_d,
      max_reqfifo_depth_d,
      rsp_handshake_seen_d,
      req_handshake_seen_d,
      8'd0
    };
    focused_metric_word1_q <= {d_data_upper_or_d, a_data_upper_or_d};
  end

  assign host_req_accepted_o = host_req_accepted_q;
  assign device_req_accepted_o = device_req_accepted_q;
  assign device_rsp_accepted_o = device_rsp_accepted_q;
  assign host_rsp_accepted_o = host_rsp_accepted_q;
  assign rsp_queue_overflow_o = rsp_queue_overflow_q;
  assign progress_cycle_count_o = cycle_count_q;
  assign progress_signature_o = progress_signature_q;
  assign debug_phase_o = {29'd0, phase_code_w};
  assign debug_reset_cycles_remaining_o = reset_cycles_remaining_w;
  assign debug_warmup_cycles_remaining_o = warmup_cycles_remaining_w;
  assign debug_req_valid_o = {31'd0, tl_h_i.a_valid};
  assign debug_req_ready_o = {31'd0, tl_h_o.a_ready};
  assign debug_rsp_valid_o = {31'd0, tl_h_o.d_valid};
  assign debug_rsp_ready_o = {31'd0, tl_h_i.d_ready};
  assign debug_device_a_valid_o = {31'd0, tl_d_o.a_valid};
  assign debug_device_a_ready_o = {31'd0, tl_d_i.a_ready};
  assign debug_host_d_valid_o = {31'd0, tl_h_o.d_valid};
  assign debug_host_d_ready_o = {31'd0, tl_h_i.d_ready};
  assign debug_trace_live_o = {31'd0, trace_live_w};
  assign debug_trace_req_active_o = {31'd0, trace_req_active_w};
  assign debug_trace_req_replay_o = {31'd0, req_trace_replay_w};
  assign debug_trace_device_ready_mode_o = {30'd0, trace_device_ready_mode_w};
  assign debug_rsp_count_o = rsp_count_q;
  assign debug_rsp_delay_head_o = rsp_delay_queue_q[rsp_head_q[QueueIndexWidth-1:0]];
  assign toggle_bitmap_word0_o = toggle_hit_word0_q;
  assign toggle_bitmap_word1_o = toggle_hit_word1_q;
  assign toggle_bitmap_word2_o = toggle_hit_word2_q;
  assign real_toggle_subset_word0_o = real_toggle_subset_hit_word0_q;
  assign real_toggle_subset_word1_o = real_toggle_subset_hit_word1_q;
  assign real_toggle_subset_word2_o = real_toggle_subset_hit_word2_q;
  assign real_toggle_subset_word3_o = real_toggle_subset_hit_word3_q;
  assign real_toggle_subset_word4_o = real_toggle_subset_hit_word4_q;
  assign real_toggle_subset_word5_o = real_toggle_subset_hit_word5_q;
  assign real_toggle_subset_word6_o = real_toggle_subset_hit_word6_q;
  assign real_toggle_subset_word7_o = real_toggle_subset_hit_word7_q;
  assign real_toggle_subset_word8_o = real_toggle_subset_hit_word8_q;
  assign real_toggle_subset_word9_o = real_toggle_subset_hit_word9_q;
  assign real_toggle_subset_word10_o = real_toggle_subset_hit_word10_q;
  assign real_toggle_subset_word11_o = real_toggle_subset_hit_word11_q;
  assign real_toggle_subset_word12_o = real_toggle_subset_hit_word12_q;
  assign real_toggle_subset_word13_o = real_toggle_subset_hit_word13_q;
  assign real_toggle_subset_word14_o = real_toggle_subset_hit_word14_q;
  assign real_toggle_subset_word15_o = real_toggle_subset_hit_word15_q;
  assign real_toggle_subset_word16_o = real_toggle_subset_hit_word16_q;
  assign real_toggle_subset_word17_o = real_toggle_subset_hit_word17_q;
  assign focused_wave_word0_o = focused_wave_word0_q;
  assign focused_wave_word1_o = focused_wave_word1_q;
  assign focused_wave_word2_o = focused_wave_word2_q;
  assign focused_wave_word3_o = focused_wave_word3_q;
  assign focused_wave_word4_o = focused_wave_word4_q;
  assign focused_wave_word5_o = focused_wave_word5_q;
  assign focused_wave_word6_o = focused_wave_word6_q;
  assign focused_wave_word7_o = focused_wave_word7_q;
  assign focused_metric_word0_o = focused_metric_word0_q;
  assign focused_metric_word1_o = focused_metric_word1_q;
  assign focused_metric_word2_o =
      {trace_step_count_q[15:0],
       (direct_trace_mode_w ? direct_trace_step_q[15:0] : trace_step_q[15:0])};
  assign focused_metric_word3_o = {
    8'(rsp_count_q[7:0]),
    8'(req_burst_remaining_q[7:0]),
    req_spawn_seen_q,
    trace_req_active_seen_q
  };
  assign focused_metric_word4_o = {
    reqfifo_under_rst_seen_q,
    reqfifo_full_seen_q,
    req_blocked_seen_q,
    req_ready_seen_q
  };
  assign trace_metric_req_handshake_seen_o = {24'd0, req_handshake_seen_q};
  assign trace_metric_rsp_handshake_seen_o = {24'd0, rsp_handshake_seen_q};
  assign trace_metric_host_rsp_handshake_seen_o = {24'd0, host_rsp_handshake_seen_q};
  assign trace_metric_trace_req_active_seen_o = {24'd0, trace_req_active_seen_q};
  assign trace_metric_req_spawn_seen_o = {24'd0, req_spawn_seen_q};
  assign trace_metric_req_ready_seen_o = {24'd0, req_ready_seen_q};
  assign trace_metric_req_blocked_seen_o = {24'd0, req_blocked_seen_q};
  assign trace_metric_reqfifo_full_seen_o = {24'd0, reqfifo_full_seen_q};
  assign trace_metric_reqfifo_under_rst_seen_o = {24'd0, reqfifo_under_rst_seen_q};
  assign trace_metric_device_a_ready_seen_o = {24'd0, device_a_ready_seen_q};
  assign trace_metric_device_a_valid_seen_o = {24'd0, device_a_valid_seen_q};
  assign trace_metric_device_ready_force_high_seen_o =
      {24'd0, device_ready_force_high_seen_q};
  assign trace_metric_trace_req_fill_hold_seen_o = {24'd0, trace_req_fill_hold_seen_q};
  assign trace_metric_trace_host_ready_default_seen_o = {24'd0, trace_host_ready_default_seen_q};
  assign trace_metric_trace_rsp_fill_hold_seen_o = {24'd0, trace_rsp_fill_hold_seen_q};
  assign trace_metric_host_d_ready_seen_o = {24'd0, host_d_ready_seen_q};
  assign trace_metric_host_d_valid_seen_o = {24'd0, host_d_valid_seen_q};
  assign trace_metric_device_rsp_ackdata_seen_o = {24'd0, device_rsp_ackdata_seen_q};
  assign trace_metric_host_rsp_ackdata_seen_o = {24'd0, host_rsp_ackdata_seen_q};
  assign trace_metric_device_rsp_payload_upper_seen_o =
      {24'd0, device_rsp_payload_upper_seen_q};
  assign trace_metric_host_rsp_payload_upper_seen_o =
      {24'd0, host_rsp_payload_upper_seen_q};
  assign trace_metric_device_rsp_payload_upper_accept_seen_o =
      {24'd0, device_rsp_payload_upper_accept_seen_q};
  assign trace_metric_host_rsp_payload_upper_accept_seen_o =
      {24'd0, host_rsp_payload_upper_accept_seen_q};
  assign trace_metric_host_raw_rsp_ackdata_seen_o =
      {24'd0, host_raw_rsp_ackdata_seen_q};
  assign trace_metric_host_raw_rsp_payload_upper_seen_o =
      {24'd0, host_raw_rsp_payload_upper_seen_q};
  assign trace_metric_first_device_rsp_pack_o = {
      12'd0,
      first_device_rsp_seen_q,
      first_device_rsp_opcode_q,
      first_device_rsp_data_upper_q
  };
  assign trace_metric_first_host_rsp_pack_o = {
      12'd0,
      first_host_rsp_seen_q,
      first_host_rsp_opcode_q,
      first_host_rsp_data_upper_q
  };
  assign trace_metric_rsp_trace_override_seen_o = {24'd0, rsp_trace_override_seen_q};
  assign trace_metric_rsp_trace_head_valid_seen_o = {24'd0, rsp_trace_head_valid_seen_q};
  assign trace_metric_rsp_trace_has_data_seen_o = {24'd0, rsp_trace_has_data_seen_q};
  assign trace_metric_rsp_spawn_has_data_seen_o = {24'd0, rsp_spawn_has_data_seen_q};
  assign trace_metric_rsp_spawn_ackdata_seen_o = {24'd0, rsp_spawn_ackdata_seen_q};
  assign trace_metric_rsp_active_opcode_or_o = {29'd0, rsp_active_opcode_or_q};
  assign trace_metric_rsp_spawn_opcode_or_o = {29'd0, rsp_spawn_opcode_or_q};
  assign trace_metric_device_rsp_opcode_or_o = {29'd0, device_rsp_opcode_or_q};
  assign trace_metric_host_rsp_opcode_or_o = {29'd0, host_rsp_opcode_or_q};
  assign trace_metric_host_raw_rsp_opcode_or_o = {29'd0, host_raw_rsp_opcode_or_q};
  assign trace_metric_reqfifo_nonempty_seen_o = {24'd0, reqfifo_nonempty_seen_q};
  assign trace_metric_rspfifo_nonempty_seen_o = {24'd0, rspfifo_nonempty_seen_q};
  assign trace_metric_direct_trace_active_seen_o = {24'd0, direct_trace_active_seen_q};
  assign trace_metric_direct_req_drive_seen_o = {24'd0, direct_req_drive_seen_q};
  assign trace_metric_direct_req_ready_seen_o = {24'd0, direct_req_ready_seen_q};
  assign trace_metric_direct_req_handshake_seen_o = {24'd0, direct_req_handshake_seen_q};
  assign trace_metric_direct_rsp_drive_seen_o = {24'd0, direct_rsp_drive_seen_q};
  assign trace_metric_direct_rsp_handshake_seen_o = {24'd0, direct_rsp_handshake_seen_q};
  assign trace_metric_trace_step_o =
      direct_trace_mode_w ? direct_trace_step_q : trace_step_q;
  assign trace_metric_trace_step_count_o = trace_step_count_q;
  assign trace_metric_trace_req_valid_mode0_o = {30'd0, trace_req_valid_mode_q[0]};
  assign trace_metric_trace_req_valid_mode_curr_o =
      {30'd0, direct_trace_mode_w
                  ? direct_trace_req_valid_mode_w
                  : 2'd0};
  assign trace_metric_trace_rsp_valid0_o = {31'd0, trace_rsp_valid_q[0]};
  assign trace_metric_trace_rsp_valid_curr_o =
      {31'd0, direct_trace_mode_w
                  ? direct_trace_rsp_valid_w
                  : 1'b0};
  assign trace_metric_trace_host_ready_mode0_o = {30'd0, trace_host_ready_mode_q[0]};
  assign trace_metric_trace_host_ready_mode_curr_o =
      {30'd0, direct_trace_mode_w
                  ? direct_trace_host_ready_mode_w
                  : 2'd0};
  assign trace_metric_trace_device_ready_mode0_o = {30'd0, trace_device_ready_mode_q[0]};
  assign trace_metric_trace_device_ready_mode_curr_o =
      {30'd0, direct_trace_mode_w
                  ? direct_trace_device_ready_mode_w
                  : 2'd0};
  assign trace_metric_max_reqfifo_depth_o = {30'd0, max_reqfifo_depth_q};
  assign trace_metric_max_rspfifo_depth_o = {30'd0, max_rspfifo_depth_q};
  assign trace_metric_a_data_mid_or_o = {16'd0, a_data_mid_or_q};
  assign trace_metric_a_address_window_or_o = {12'd0, a_address_window_or_q};
  assign trace_metric_device_d_data_low_or_o = {16'd0, device_d_data_low_or_q};
  assign trace_metric_device_d_data_upper_or_o = {16'd0, device_d_data_upper_or_q};
  assign trace_metric_d_data_low_or_o = {16'd0, d_data_low_or_q};
  assign trace_metric_a_data_upper_or_o = {16'd0, a_data_upper_or_q};
  assign trace_metric_d_data_upper_or_o = {16'd0, d_data_upper_or_q};

  initial begin
    cycle_count_q = 32'd0;
    bootstrapped_q = 1'b0;
    phase_q = ResetPhase;
    reset_cycles_remaining_q = 32'd0;
    warmup_cycles_remaining_q = 32'd0;
    traffic_cycles_remaining_q = 32'd0;
    drain_cycles_remaining_q = 32'd0;
    rand_state_q = 32'd0;
    req_pending_valid_q = 1'b0;
    req_pending_opcode_q = Get;
    req_pending_param_q = '0;
    req_pending_size_q = '0;
    req_pending_source_q = '0;
    req_pending_address_q = '0;
    req_pending_mask_q = '0;
    req_pending_data_q = '0;
    req_pending_spare_q = '0;
    req_pending_trace_active_q = 1'b0;
    req_pending_trace_index_q = '0;
    req_forward_trace_active_q = 1'b0;
    req_forward_trace_index_q = '0;
    req_burst_remaining_q = 32'd0;
    req_burst_trace_active_q = 1'b0;
    req_burst_trace_index_q = '0;
    req_burst_opcode_q = Get;
    req_burst_param_q = '0;
    req_burst_size_q = '0;
    req_burst_source_q = '0;
    req_burst_address_q = '0;
    req_burst_mask_q = '0;
    req_burst_data_q = '0;
    req_burst_spare_q = '0;
    trace_step_q = 32'd0;
    direct_trace_step_q = 32'd0;
    trace_step_count_q = 32'd0;
    direct_req_done_q = 1'b0;
    direct_rsp_done_q = 1'b0;
    direct_rsp_delay_q = 32'd0;
    direct_rsp_hold_valid_q = 1'b0;
    direct_rsp_hold_opcode_q = 3'd0;
    direct_rsp_hold_size_q = '0;
    direct_rsp_hold_source_q = '0;
    direct_rsp_hold_data_q = '0;
    direct_rsp_hold_error_q = 1'b0;
    rsp_pending_valid_q = 1'b0;
    rsp_pending_opcode_q = AccessAck;
    rsp_pending_param_q = '0;
    rsp_pending_size_q = '0;
    rsp_pending_source_q = '0;
    rsp_pending_sink_q = '0;
    rsp_pending_data_q = '0;
    rsp_pending_error_q = 1'b0;
    rsp_pending_spare_q = '0;
    rsp_head_q = 32'd0;
    rsp_tail_q = 32'd0;
    rsp_count_q = 32'd0;
    for (queue_idx = 0; queue_idx < TraceDepth; queue_idx++) begin
      trace_req_opcode_q[queue_idx] = '0;
      trace_req_param_q[queue_idx] = '0;
      trace_req_size_q[queue_idx] = top_pkg::TL_SZW'(2);
      trace_req_address_q[queue_idx] = '0;
      trace_req_mask_q[queue_idx] = '1;
      trace_req_data_q[queue_idx] = '0;
      trace_req_source_q[queue_idx] = '0;
      trace_req_burst_len_q[queue_idx] = 32'd0;
      trace_req_spare_q[queue_idx] = 1'b0;
      trace_rsp_valid_q[queue_idx] = 1'b0;
      trace_rsp_opcode_q[queue_idx] = 3'd0;
      trace_rsp_size_q[queue_idx] = top_pkg::TL_SZW'(2);
      trace_rsp_source_q[queue_idx] = '0;
      trace_rsp_has_data_q[queue_idx] = 1'b0;
      trace_rsp_data_q[queue_idx] = '0;
      trace_rsp_delay_q[queue_idx] = 32'd0;
      trace_rsp_error_q[queue_idx] = 1'b0;
      trace_host_ready_mode_q[queue_idx] = 2'd0;
      trace_device_ready_mode_q[queue_idx] = 2'd0;
      trace_req_valid_mode_q[queue_idx] = 2'd0;
    end
    for (queue_idx = 0; queue_idx < QueueDepth; queue_idx++) begin
      rsp_size_queue_q[queue_idx] = '0;
      rsp_source_queue_q[queue_idx] = '0;
      rsp_req_opcode_queue_q[queue_idx] = Get;
      rsp_req_address_queue_q[queue_idx] = '0;
      rsp_req_data_queue_q[queue_idx] = '0;
      rsp_delay_queue_q[queue_idx] = '0;
      rsp_trace_valid_queue_q[queue_idx] = 1'b0;
      rsp_trace_opcode_queue_q[queue_idx] = 3'd0;
      rsp_trace_size_queue_q[queue_idx] = '0;
      rsp_trace_source_queue_q[queue_idx] = '0;
      rsp_trace_has_data_queue_q[queue_idx] = 1'b0;
      rsp_trace_data_queue_q[queue_idx] = '0;
      rsp_trace_error_queue_q[queue_idx] = 1'b0;
      rsp_trace_host_ready_mode_queue_q[queue_idx] = 2'd0;
    end
    host_req_accepted_q = 32'd0;
    device_req_accepted_q = 32'd0;
    device_rsp_accepted_q = 32'd0;
    host_rsp_accepted_q = 32'd0;
    rsp_queue_overflow_q = 32'd0;
    progress_signature_q = 32'd0;
    toggle_prev_word0_q = 32'd0;
    toggle_prev_word1_q = 32'd0;
    toggle_prev_word2_q = 32'd0;
    toggle_hit_word0_q = 32'd0;
    toggle_hit_word1_q = 32'd0;
    toggle_hit_word2_q = 32'd0;
    real_toggle_subset_prev_chunk0_q = 16'd0;
    real_toggle_subset_prev_chunk1_q = 16'd0;
    real_toggle_subset_prev_chunk2_q = 16'd0;
    real_toggle_subset_prev_chunk3_q = 16'd0;
    real_toggle_subset_prev_chunk4_q = 16'd0;
    real_toggle_subset_prev_chunk5_q = 16'd0;
    real_toggle_subset_prev_chunk6_q = 16'd0;
    real_toggle_subset_prev_chunk7_q = 16'd0;
    real_toggle_subset_prev_chunk8_q = 16'd0;
    real_toggle_subset_prev_chunk9_q = 16'd0;
    real_toggle_subset_prev_chunk10_q = 16'd0;
    real_toggle_subset_prev_chunk11_q = 16'd0;
    real_toggle_subset_prev_chunk12_q = 16'd0;
    real_toggle_subset_prev_chunk13_q = 16'd0;
    real_toggle_subset_prev_chunk14_q = 16'd0;
    real_toggle_subset_prev_chunk15_q = 16'd0;
    real_toggle_subset_prev_chunk16_q = 16'd0;
    real_toggle_subset_prev_chunk17_q = 16'd0;
    real_toggle_subset_hit_word0_q = 32'd0;
    real_toggle_subset_hit_word1_q = 32'd0;
    real_toggle_subset_hit_word2_q = 32'd0;
    real_toggle_subset_hit_word3_q = 32'd0;
    real_toggle_subset_hit_word4_q = 32'd0;
    real_toggle_subset_hit_word5_q = 32'd0;
    real_toggle_subset_hit_word6_q = 32'd0;
    real_toggle_subset_hit_word7_q = 32'd0;
    real_toggle_subset_hit_word8_q = 32'd0;
    real_toggle_subset_hit_word9_q = 32'd0;
    real_toggle_subset_hit_word10_q = 32'd0;
    real_toggle_subset_hit_word11_q = 32'd0;
    real_toggle_subset_hit_word12_q = 32'd0;
    real_toggle_subset_hit_word13_q = 32'd0;
    real_toggle_subset_hit_word14_q = 32'd0;
    real_toggle_subset_hit_word15_q = 32'd0;
    real_toggle_subset_hit_word16_q = 32'd0;
    real_toggle_subset_hit_word17_q = 32'd0;
    focused_wave_word0_q = 32'd0;
    focused_wave_word1_q = 32'd0;
    focused_wave_word2_q = 32'd0;
    focused_wave_word3_q = 32'd0;
    focused_wave_word4_q = 32'd0;
    focused_wave_word5_q = 32'd0;
    focused_wave_word6_q = 32'd0;
    focused_wave_word7_q = 32'd0;
    focused_metric_word0_q = 32'd0;
    focused_metric_word1_q = 32'd0;
    max_reqfifo_depth_q = 2'd0;
    max_rspfifo_depth_q = 2'd0;
    req_handshake_seen_q = 8'd0;
    rsp_handshake_seen_q = 8'd0;
    host_rsp_handshake_seen_q = 8'd0;
    direct_trace_active_seen_q = 8'd0;
    direct_req_drive_seen_q = 8'd0;
    direct_req_ready_seen_q = 8'd0;
    direct_req_handshake_seen_q = 8'd0;
    direct_rsp_drive_seen_q = 8'd0;
    direct_rsp_handshake_seen_q = 8'd0;
    trace_req_active_seen_q = 8'd0;
    req_spawn_seen_q = 8'd0;
    req_ready_seen_q = 8'd0;
    req_blocked_seen_q = 8'd0;
    reqfifo_full_seen_q = 8'd0;
    reqfifo_under_rst_seen_q = 8'd0;
    device_a_ready_seen_q = 8'd0;
    device_a_valid_seen_q = 8'd0;
    device_ready_force_high_seen_q = 8'd0;
    trace_req_fill_hold_seen_q = 8'd0;
    trace_host_ready_default_seen_q = 8'd0;
    trace_rsp_fill_hold_seen_q = 8'd0;
    host_d_ready_seen_q = 8'd0;
    host_d_valid_seen_q = 8'd0;
    device_rsp_ackdata_seen_q = 8'd0;
    host_rsp_ackdata_seen_q = 8'd0;
    device_rsp_payload_upper_seen_q = 8'd0;
    host_rsp_payload_upper_seen_q = 8'd0;
    device_rsp_payload_upper_accept_seen_q = 8'd0;
    host_rsp_payload_upper_accept_seen_q = 8'd0;
    host_raw_rsp_ackdata_seen_q = 8'd0;
    host_raw_rsp_payload_upper_seen_q = 8'd0;
    first_device_rsp_seen_q = 1'b0;
    first_device_rsp_opcode_q = 3'd0;
    first_device_rsp_data_upper_q = 16'd0;
    first_host_rsp_seen_q = 1'b0;
    first_host_rsp_opcode_q = 3'd0;
    first_host_rsp_data_upper_q = 16'd0;
    last_device_rsp_seen_q = 1'b0;
    last_device_rsp_opcode_q = 3'd0;
    last_device_rsp_data_q = '0;
    rsp_trace_override_seen_q = 8'd0;
    rsp_trace_head_valid_seen_q = 8'd0;
    rsp_trace_has_data_seen_q = 8'd0;
    rsp_spawn_has_data_seen_q = 8'd0;
    rsp_spawn_ackdata_seen_q = 8'd0;
    rsp_spawn_opcode_or_q = 3'd0;
    rsp_active_opcode_or_q = 3'd0;
    device_rsp_opcode_or_q = 3'd0;
    host_rsp_opcode_or_q = 3'd0;
    host_raw_rsp_opcode_or_q = 3'd0;
    reqfifo_nonempty_seen_q = 8'd0;
    rspfifo_nonempty_seen_q = 8'd0;
    a_data_mid_or_q = 16'd0;
    a_address_window_or_q = 20'd0;
    device_d_data_low_or_q = 16'd0;
    device_d_data_upper_or_q = 16'd0;
    d_data_low_or_q = 16'd0;
    a_data_upper_or_q = 16'd0;
    d_data_upper_or_q = 16'd0;
  end

endmodule

module tlul_fifo_sync_gpu_cov_tb (
  `TLUL_FIFO_SYNC_GPU_COV_PORTS
);
  logic clk_i;
  logic rst_ni;
  logic reset_like_w;

  tlul_fifo_sync_gpu_cov_core core (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .reset_like_o(reset_like_w),
    .*
  );

  always #5 clk_i = ~clk_i;

  assign rst_ni = !reset_like_w;

  initial begin
    clk_i = 1'b0;
  end
endmodule
