#!/usr/bin/env python3
"""Summarize why RTLMeter hybrid measurements are difficult per target."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_MATRIX = Path("reports/rtlmeter_vortex_veer_hybrid_measurement_matrix.json")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix() if not path.is_absolute() else "<local-absolute-path>"


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _classify_blockers(row: dict[str, Any]) -> tuple[list[str], list[str], int]:
    blockers: list[str] = []
    immediate: list[str] = []
    score = 0
    missing = _as_list(row.get("missing_prerequisites"))
    hybrid_candidate = row.get("hybrid_candidate") if isinstance(row.get("hybrid_candidate"), dict) else {}
    sidecar_bridge = row.get("sidecar_bridge_preflight") if isinstance(row.get("sidecar_bridge_preflight"), dict) else {}
    surface = row.get("hybrid_surface_audit") if isinstance(row.get("hybrid_surface_audit"), dict) else {}
    authority_ready = hybrid_candidate.get("real_runtime_observable_authority_ready") is True
    timing_measured = row.get("timing_status") == "measured"

    if row.get("timing_status") != "measured":
        blockers.append("timing_report_missing")
        score += 1
    if row.get("correctness_status") != "passed":
        blockers.append("correctness_not_measured_or_not_passed")
        score += 1
    if row.get("measurement_status") in {"blocked_before_hybrid_measurement", "sidecar_bridge_preflight_hybrid_surface_missing"}:
        blockers.append(str(row.get("measurement_status")))
        score += 2

    if hybrid_candidate.get("probe_or_marker_boundary_observed") is True and not authority_ready and not timing_measured:
        blockers.append("probe_or_marker_boundary_still_in_execution_path")
        score += 2
    if hybrid_candidate.get("fake_driver_materialized_runtime_args_call_observed") is True and not authority_ready and not timing_measured:
        blockers.append("fake_driver_materialized_runtime_args_call_still_in_execution_path")
        score += 1
    if hybrid_candidate.get("real_cuda_materialized_runtime_args_call_observed") is True and not authority_ready and not timing_measured:
        blockers.append("real_cuda_materialized_args_root_storage_callback_not_authority")
        score += 1
    if hybrid_candidate.get("real_vortex_kernel_artifact_ready") is False and not timing_measured:
        blockers.append("real_vortex_kernel_artifact_missing")
        score += 1
    if hybrid_candidate.get("kernel_artifact_build_landingpad_blocked") is True and not timing_measured:
        blockers.append("vortex_lowered_ir_landingpad_personality_fix_required")
        score += 2
    if hybrid_candidate.get("kernel_callback_prelaunch_rejection_required") is True and not timing_measured:
        blockers.append("vortex_kernel_callback_prelaunch_rejection_required")
        score += 2
    if hybrid_candidate.get("kernel_callback_wiring_ready") is False and not timing_measured:
        blockers.append("vortex_kernel_callback_not_wired")
        score += 1
    if hybrid_candidate.get("real_cuda_materialized_runtime_smoke_timed_out") is True and not timing_measured:
        if hybrid_candidate.get("real_cuda_root_storage_kernel_last_stage") == "before_cuModuleLoad":
            blockers.append("real_vortex_cuModuleLoad_jit_timeout")
        else:
            blockers.append("real_vortex_ptx_module_load_or_jit_timeout")
        score += 2
    if hybrid_candidate.get("ptx_module_load_ptxas_status") == "ptxas_timeout" and not timing_measured:
        blockers.append("vortex_ptxas_timeout_reproduces_cuModuleLoad_jit_cost")
        score += 2
    elif hybrid_candidate.get("ptx_module_load_ptxas_status") == "ptxas_failed" and not timing_measured:
        blockers.append("vortex_ptxas_failed_before_cuModuleLoad_retry")
        score += 1
    if hybrid_candidate.get("real_cuda_materialized_runtime_smoke_failed_stage") == "kernel_launch" and not timing_measured:
        if hybrid_candidate.get("real_cuda_root_storage_kernel_failed_stage") == "cuModuleLoad":
            blockers.append("real_vortex_ptx_module_load_failed")
        elif (
            hybrid_candidate.get("real_cuda_root_storage_kernel_failed_stage") == "cuLaunchOrSync"
            and hybrid_candidate.get("real_cuda_root_storage_kernel_failed_result") == 700
        ):
            blockers.append(
                "real_runtime_observable_authority_missing_after_canonical_std_ref_fix"
                if hybrid_candidate.get("real_cuda_canonical_std_ref_fix_smoke_passed") is True
                else "vortex_std_ref_device_lowering_fix_not_promoted_to_canonical_artifact"
                if hybrid_candidate.get("real_cuda_all_std_ref_returns_arg_smoke_passed") is True
                else "real_vortex_eval_internal_kernel_illegal_memory_access"
                if hybrid_candidate.get("real_cuda_return_before_eval_smoke_passed") is True
                else "real_vortex_relocated_syms_image_kernel_illegal_memory_access"
                if isinstance(hybrid_candidate.get("real_cuda_root_storage_relocation_count"), int)
                and hybrid_candidate.get("real_cuda_root_storage_relocation_count") > 0
                else "real_vortex_root_storage_kernel_illegal_memory_access"
            )
        else:
            blockers.append("real_vortex_root_storage_kernel_launch_failed")
        score += 2
    if hybrid_candidate.get("real_runtime_observable_authority_ready") is False and not timing_measured:
        blockers.append("real_runtime_observable_authority_missing")
        score += 2
    if hybrid_candidate.get("real_cuda_runtime_sequence_preflight_passed") is True and not timing_measured:
        blockers.append("cuda_sequence_preflight_only_not_vortex_kernel_execution")
        score += 1
    if hybrid_candidate.get("real_cuda_memory_transport_passed") is True and not timing_measured:
        blockers.append("memory_transport_validated_but_not_timed_as_hybrid")

    sidecar_missing = _as_list(sidecar_bridge.get("missing_build_context"))
    if "gpu_artifact_prelaunch_rejection_required" in missing or "gpu_artifact_prelaunch_rejection_required" in sidecar_missing:
        blockers.append("gpu_artifact_rejected_before_launch")
        score += 2
    if (
        "gpu_artifact_root_offset_in_syms_missing_for_auto_promotion" in missing
        or "gpu_artifact_root_offset_in_syms_missing_for_auto_promotion" in sidecar_missing
    ):
        blockers.append("root_offset_in_syms_missing_blocks_syms_state_image_rebuild")
        score += 1
    if (
        "gpu_artifact_unsafe_syms_gep_not_covered_by_state_image" in missing
        or "gpu_artifact_unsafe_syms_gep_not_covered_by_state_image" in sidecar_missing
    ):
        blockers.append("unsafe_syms_gep_not_covered_by_current_state_image")
        score += 1
    if "gpu_artifact_residual_std_tree_detected" in missing or "gpu_artifact_residual_std_tree_detected" in sidecar_missing:
        blockers.append("residual_std_tree_in_generated_gpu_ir")
        score += 1
    entry_pruned_probe = (
        sidecar_bridge.get("entry_pruned_module_probe")
        if isinstance(sidecar_bridge.get("entry_pruned_module_probe"), dict)
        else {}
    )
    static_residue_probe = (
        entry_pruned_probe.get("static_ptx_runtime_residue_probe")
        if isinstance(entry_pruned_probe.get("static_ptx_runtime_residue_probe"), dict)
        else {}
    )
    if (
        "entry_pruned_cpp_verilator_runtime_residue_detected" in missing
        or "entry_pruned_cpp_verilator_runtime_residue_detected" in sidecar_missing
        or static_residue_probe.get("runtime_residue_detected") is True
    ):
        blockers.append("entry_pruned_cpp_verilator_runtime_residue_in_gpu_ptx")
        score += 1
    host_cleanup_probe = (
        entry_pruned_probe.get("host_cleanup_eval_only_probe")
        if isinstance(entry_pruned_probe.get("host_cleanup_eval_only_probe"), dict)
        else {}
    )
    if (
        "eh2_host_cleanup_eval_only_did_not_clear_eval_fault" in missing
        or "eh2_host_cleanup_eval_only_did_not_clear_eval_fault" in sidecar_missing
        or host_cleanup_probe.get("status") == "host_cleanup_eval_only_still_illegal_memory_access"
    ):
        blockers.append("eh2_existing_host_cleanup_still_faults_at_first_eval")
        score += 1
    host_cleanup_v2_probe = (
        entry_pruned_probe.get("host_cleanup_v2_eval_only_probe")
        if isinstance(entry_pruned_probe.get("host_cleanup_v2_eval_only_probe"), dict)
        else {}
    )
    return_before_eval_probe = (
        entry_pruned_probe.get("return_before_eval_probe")
        if isinstance(entry_pruned_probe.get("return_before_eval_probe"), dict)
        else {}
    )
    return_before_eval_call_probe = (
        entry_pruned_probe.get("return_before_eval_call_probe")
        if isinstance(entry_pruned_probe.get("return_before_eval_call_probe"), dict)
        else {}
    )
    trigger_orinto_entry_probe = (
        entry_pruned_probe.get("trigger_orinto_return_before_first_ix_probe")
        if isinstance(entry_pruned_probe.get("trigger_orinto_return_before_first_ix_probe"), dict)
        else {}
    )
    trigger_orinto_stack64k_probe = (
        entry_pruned_probe.get("trigger_orinto_return_before_first_ix_stack64k_probe")
        if isinstance(entry_pruned_probe.get("trigger_orinto_return_before_first_ix_stack64k_probe"), dict)
        else {}
    )
    inline_return_after_probe = (
        entry_pruned_probe.get("inline_orinto_return_after_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_return_after_probe"), dict)
        else {}
    )
    inline_noop_probe = (
        entry_pruned_probe.get("inline_orinto_noop_return_after_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_noop_return_after_probe"), dict)
        else {}
    )
    inline_dst_load_probe = (
        entry_pruned_probe.get("inline_orinto_after_dst_load_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_after_dst_load_probe"), dict)
        else {}
    )
    inline_src_load_probe = (
        entry_pruned_probe.get("inline_orinto_after_src_load_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_after_src_load_probe"), dict)
        else {}
    )
    inline_before_store_probe = (
        entry_pruned_probe.get("inline_orinto_before_store_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_before_store_probe"), dict)
        else {}
    )
    inline_store_u32_dst_probe = (
        entry_pruned_probe.get("inline_orinto_store_u32_dst_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_store_u32_dst_probe"), dict)
        else {}
    )
    inline_store_u8_dst_probe = (
        entry_pruned_probe.get("inline_orinto_store_u8_dst_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_store_u8_dst_probe"), dict)
        else {}
    )
    inline_store_u64_src_probe = (
        entry_pruned_probe.get("inline_orinto_store_u64_src_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_store_u64_src_probe"), dict)
        else {}
    )
    entry_store_nba_probe = (
        entry_pruned_probe.get("entry_store_nba_trigger_return_probe")
        if isinstance(entry_pruned_probe.get("entry_store_nba_trigger_return_probe"), dict)
        else {}
    )
    store_vnba_before_triggers_probe = (
        entry_pruned_probe.get("store_vnba_before_triggers_probe")
        if isinstance(entry_pruned_probe.get("store_vnba_before_triggers_probe"), dict)
        else {}
    )
    store_vnba_after_triggers_direct_root_probe = (
        entry_pruned_probe.get("store_vnba_after_triggers_direct_root_probe")
        if isinstance(entry_pruned_probe.get("store_vnba_after_triggers_direct_root_probe"), dict)
        else {}
    )
    store_next472416_after_triggers_probe = (
        entry_pruned_probe.get("store_next472416_after_triggers_probe")
        if isinstance(entry_pruned_probe.get("store_next472416_after_triggers_probe"), dict)
        else {}
    )
    inline_store_vnba_cvta_global_probe = (
        entry_pruned_probe.get("inline_orinto_store_vnba_cvta_global_probe")
        if isinstance(entry_pruned_probe.get("inline_orinto_store_vnba_cvta_global_probe"), dict)
        else {}
    )
    minimal_store_vnba_probe = (
        entry_pruned_probe.get("minimal_store_vnba_probe")
        if isinstance(entry_pruned_probe.get("minimal_store_vnba_probe"), dict)
        else {}
    )
    std_ref_get_canonical_eval_only_probe = (
        entry_pruned_probe.get("std_ref_get_canonical_eval_only_probe")
        if isinstance(entry_pruned_probe.get("std_ref_get_canonical_eval_only_probe"), dict)
        else {}
    )
    std_ref_get_canonical_eval_return_before_phase_act_probe = (
        entry_pruned_probe.get("std_ref_get_canonical_eval_return_before_phase_act_probe")
        if isinstance(entry_pruned_probe.get("std_ref_get_canonical_eval_return_before_phase_act_probe"), dict)
        else {}
    )
    std_ref_get_canonical_eval_return_after_one_phase_act_probe = (
        entry_pruned_probe.get("std_ref_get_canonical_eval_return_after_one_phase_act_probe")
        if isinstance(entry_pruned_probe.get("std_ref_get_canonical_eval_return_after_one_phase_act_probe"), dict)
        else {}
    )
    std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe = (
        entry_pruned_probe.get("std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe")
        if isinstance(entry_pruned_probe.get("std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe"), dict)
        else {}
    )
    std_ref_get_canonical_trigger_orinto_return_before_store_probe = (
        entry_pruned_probe.get("std_ref_get_canonical_trigger_orinto_return_before_store_probe")
        if isinstance(entry_pruned_probe.get("std_ref_get_canonical_trigger_orinto_return_before_store_probe"), dict)
        else {}
    )
    std_ref_get_canonical_trigger_orinto_return_after_store_probe = (
        entry_pruned_probe.get("std_ref_get_canonical_trigger_orinto_return_after_store_probe")
        if isinstance(entry_pruned_probe.get("std_ref_get_canonical_trigger_orinto_return_after_store_probe"), dict)
        else {}
    )
    vlunpacked_lm1_canonical_eval_only_probe = (
        entry_pruned_probe.get("vlunpacked_lm1_canonical_eval_only_probe")
        if isinstance(entry_pruned_probe.get("vlunpacked_lm1_canonical_eval_only_probe"), dict)
        else {}
    )
    vlunpacked_lm1_phase_act_return_before_orinto_probe = (
        entry_pruned_probe.get("vlunpacked_lm1_phase_act_return_before_orinto_probe")
        if isinstance(entry_pruned_probe.get("vlunpacked_lm1_phase_act_return_before_orinto_probe"), dict)
        else {}
    )
    vlunpacked_lm1_trigger_orinto_return_immediate_probe = (
        entry_pruned_probe.get("vlunpacked_lm1_trigger_orinto_return_immediate_probe")
        if isinstance(entry_pruned_probe.get("vlunpacked_lm1_trigger_orinto_return_immediate_probe"), dict)
        else {}
    )
    vlunpacked_lm1_orinto_rewrite_eval_only_probe = (
        entry_pruned_probe.get("vlunpacked_lm1_orinto_rewrite_eval_only_probe")
        if isinstance(entry_pruned_probe.get("vlunpacked_lm1_orinto_rewrite_eval_only_probe"), dict)
        else {}
    )
    orinto_store_skip_eval_only_probe = (
        entry_pruned_probe.get("orinto_store_skip_eval_only_probe")
        if isinstance(entry_pruned_probe.get("orinto_store_skip_eval_only_probe"), dict)
        else {}
    )
    orinto_store_zero_eval_only_probe = (
        entry_pruned_probe.get("orinto_store_zero_eval_only_probe")
        if isinstance(entry_pruned_probe.get("orinto_store_zero_eval_only_probe"), dict)
        else {}
    )
    orinto_store_dst_eval_only_probe = (
        entry_pruned_probe.get("orinto_store_dst_eval_only_probe")
        if isinstance(entry_pruned_probe.get("orinto_store_dst_eval_only_probe"), dict)
        else {}
    )
    skip_store_return_after_timing_resume_probe = (
        entry_pruned_probe.get("skip_store_return_after_timing_resume_probe")
        if isinstance(entry_pruned_probe.get("skip_store_return_after_timing_resume_probe"), dict)
        else {}
    )
    skip_store_return_after_eval_act_probe = (
        entry_pruned_probe.get("skip_store_return_after_eval_act_probe")
        if isinstance(entry_pruned_probe.get("skip_store_return_after_eval_act_probe"), dict)
        else {}
    )
    eval_act_callseq_probes = (
        entry_pruned_probe.get("eval_act_return_after_callseq_probes")
        if isinstance(entry_pruned_probe.get("eval_act_return_after_callseq_probes"), dict)
        else {}
    )
    eval_act_callseq_951_probe = (
        eval_act_callseq_probes.get("951") if isinstance(eval_act_callseq_probes.get("951"), dict) else {}
    )
    eval_act_callseq_952_probe = (
        eval_act_callseq_probes.get("952") if isinstance(eval_act_callseq_probes.get("952"), dict) else {}
    )
    dec_cam0_minimal_body_ret_probe = (
        entry_pruned_probe.get("dec_cam0_minimal_body_ret_probe")
        if isinstance(entry_pruned_probe.get("dec_cam0_minimal_body_ret_probe"), dict)
        else {}
    )
    eval_act_skip_first_three_submodule_calls_probe = (
        entry_pruned_probe.get("eval_act_skip_callseq_952_953_954_return_after_954_probe")
        if isinstance(entry_pruned_probe.get("eval_act_skip_callseq_952_953_954_return_after_954_probe"), dict)
        else {}
    )
    vlwide_pointer_conversion_canonical_probe = (
        entry_pruned_probe.get("vlwide_pointer_conversion_canonical_eval_only_probe")
        if isinstance(entry_pruned_probe.get("vlwide_pointer_conversion_canonical_eval_only_probe"), dict)
        else {}
    )
    vlwide_phase_act_before_trigger_merge_store_probe = (
        entry_pruned_probe.get("vlwide_phase_act_before_trigger_merge_store_probe")
        if isinstance(entry_pruned_probe.get("vlwide_phase_act_before_trigger_merge_store_probe"), dict)
        else {}
    )
    vlwide_phase_act_after_trigger_merge_store_probe = (
        entry_pruned_probe.get("vlwide_phase_act_after_trigger_merge_store_probe")
        if isinstance(entry_pruned_probe.get("vlwide_phase_act_after_trigger_merge_store_probe"), dict)
        else {}
    )
    vlwide_phase_act_store_one_nba_before_eval_nba_probe = (
        entry_pruned_probe.get("vlwide_phase_act_store_one_nba_before_eval_nba_probe")
        if isinstance(entry_pruned_probe.get("vlwide_phase_act_store_one_nba_before_eval_nba_probe"), dict)
        else {}
    )
    vlwide_phase_act_store_one_nba_after_eval_nba_probe = (
        entry_pruned_probe.get("vlwide_phase_act_store_one_nba_after_eval_nba_probe")
        if isinstance(entry_pruned_probe.get("vlwide_phase_act_store_one_nba_after_eval_nba_probe"), dict)
        else {}
    )
    if (
        "eh2_host_cleanup_v2_eval_only_did_not_clear_eval_fault" in missing
        or "eh2_host_cleanup_v2_eval_only_did_not_clear_eval_fault" in sidecar_missing
        or host_cleanup_v2_probe.get("status") == "host_cleanup_v2_eval_only_still_illegal_memory_access"
    ):
        blockers.append("eh2_extended_host_cleanup_still_faults_at_eval_callee")
        score += 1
    if (
        "eh2_return_before_eval_launch_infrastructure_passed" in missing
        or "eh2_prologue_pointer_setup_passed_before_eval_call" in missing
        or return_before_eval_probe.get("status") == "return_before_eval_passed"
        or return_before_eval_call_probe.get("status") == "prologue_only_return_before_eval_call_passed"
    ):
        blockers.append("eh2_launch_and_prologue_pass_eval_callee_internal_fault")
    if (
        "eh2_trigger_orinto_device_call_entry_fault" in missing
        or "eh2_trigger_orinto_device_call_entry_fault" in sidecar_missing
        or trigger_orinto_entry_probe.get("status")
        == "trigger_orinto_return_before_first_ix_still_illegal_memory_access"
    ):
        blockers.append("eh2_trigger_orinto_device_call_abi_fault")
        score += 1
    if (
        "eh2_trigger_orinto_entry_fault_not_stack_limit" in missing
        or "eh2_trigger_orinto_entry_fault_not_stack_limit" in sidecar_missing
        or trigger_orinto_stack64k_probe.get("status")
        == "trigger_orinto_return_before_first_ix_stack64k_still_illegal_memory_access"
    ):
        blockers.append("eh2_trigger_orinto_stack_limit_override_did_not_clear_fault")
    inline_loads_pass = (
        "eh2_inline_orinto_loads_before_store_pass" in missing
        or "eh2_inline_orinto_loads_before_store_pass" in sidecar_missing
        or (
            inline_noop_probe.get("status") == "inline_orinto_noop_return_after_passed"
            and inline_dst_load_probe.get("status") == "inline_orinto_after_dst_load_passed"
            and inline_src_load_probe.get("status") == "inline_orinto_after_src_load_passed"
            and inline_before_store_probe.get("status") == "inline_orinto_before_store_passed"
        )
    )
    eval_phase_vnba_store_fault = (
        "eh2_inline_orinto_store_to_vnba_triggered_fault" in missing
        or "eh2_inline_orinto_store_to_vnba_triggered_fault" in sidecar_missing
        or inline_return_after_probe.get("status") == "inline_orinto_return_after_still_illegal_memory_access"
        or inline_store_u32_dst_probe.get("status") == "inline_orinto_store_u32_dst_still_illegal_memory_access"
        or inline_store_u8_dst_probe.get("status") == "inline_orinto_store_u8_dst_still_illegal_memory_access"
    )
    adjacent_and_entry_stores_pass = (
        "eh2_adjacent_vact_triggered_store_passes" in missing
        or "eh2_entry_context_vnba_triggered_store_passes" in missing
        or "eh2_adjacent_vact_triggered_store_passes" in sidecar_missing
        or "eh2_entry_context_vnba_triggered_store_passes" in sidecar_missing
        or (
            inline_store_u64_src_probe.get("status") == "inline_orinto_store_u64_src_passed"
            and entry_store_nba_probe.get("status") == "entry_store_nba_trigger_return_passed"
        )
    )
    if inline_loads_pass and eval_phase_vnba_store_fault:
        blockers.append("eh2_eval_phase_vnba_triggered_store_context_fault")
        score += 1
    if eval_phase_vnba_store_fault and adjacent_and_entry_stores_pass:
        blockers.append("eh2_vnba_store_fault_is_context_sensitive_not_raw_address")
    if (
        "eh2_eval_phase_vnba_store_passes_with_direct_root" in missing
        or "eh2_eval_phase_vnba_store_passes_with_direct_root" in sidecar_missing
        or store_vnba_after_triggers_direct_root_probe.get("status")
        == "eval_phase_act_store_vnba_after_triggers_direct_root_passed"
    ):
        blockers.append("eh2_vnba_store_passes_when_root_is_recomputed_directly")
    if (
        "eh2_reference_wrapper_get_cvta_vnba_store_still_faults" in missing
        or "eh2_reference_wrapper_get_cvta_vnba_store_still_faults" in sidecar_missing
        or inline_store_vnba_cvta_global_probe.get("status")
        == "inline_orinto_store_vnba_cvta_global_still_illegal_memory_access"
    ):
        blockers.append("eh2_reference_wrapper_get_pointer_store_path_still_faults")
        score += 1
    if (
        "eh2_minimal_eval_phase_vnba_store_passes" in missing
        or "eh2_eval_phase_vnba_store_passes_before_triggers" in missing
        or "eh2_eval_phase_adjacent_next_store_passes_after_triggers" in missing
        or "eh2_minimal_eval_phase_vnba_store_passes" in sidecar_missing
        or "eh2_eval_phase_vnba_store_passes_before_triggers" in sidecar_missing
        or "eh2_eval_phase_adjacent_next_store_passes_after_triggers" in sidecar_missing
        or minimal_store_vnba_probe.get("status") == "eval_phase_act_minimal_store_vnba_passed"
        or store_vnba_before_triggers_probe.get("status") == "eval_phase_act_store_vnba_before_triggers_passed"
        or store_next472416_after_triggers_probe.get("status")
        == "eval_phase_act_store_next472416_after_triggers_passed"
    ):
        blockers.append("eh2_vnba_fault_requires_full_eval_context_not_plain_store")
    if (
        "eh2_std_ref_get_canonical_eval_only_still_faults" in missing
        or "eh2_std_ref_get_canonical_eval_only_still_faults" in sidecar_missing
        or std_ref_get_canonical_eval_only_probe.get("status")
        == "std_ref_get_canonical_eval_only_still_illegal_memory_access"
    ):
        blockers.append("eh2_std_ref_get_canonicalization_did_not_clear_eval_fault")
        score += 2
    if (
        "eh2_std_ref_get_canonical_eval_prologue_passes_before_phase_act" in missing
        or "eh2_std_ref_get_canonical_eval_prologue_passes_before_phase_act" in sidecar_missing
        or std_ref_get_canonical_eval_return_before_phase_act_probe.get("status")
        == "std_ref_get_canonical_eval_return_before_phase_act_passed"
    ):
        blockers.append("eh2_std_ref_get_canonical_eval_prologue_passes")
    if (
        "eh2_std_ref_get_canonical_one_phase_act_still_faults" in missing
        or "eh2_std_ref_get_canonical_one_phase_act_still_faults" in sidecar_missing
        or std_ref_get_canonical_eval_return_after_one_phase_act_probe.get("status")
        == "std_ref_get_canonical_eval_return_after_one_phase_act_still_illegal_memory_access"
    ):
        blockers.append("eh2_std_ref_get_canonical_fault_is_in_phase_act")
        score += 1
    if (
        "eh2_std_ref_get_canonical_phase_act_orinto_still_faults" in missing
        or "eh2_std_ref_get_canonical_phase_act_orinto_still_faults" in sidecar_missing
        or std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe.get("status")
        == "std_ref_get_canonical_phase_act_return_after_orinto_ret0_still_illegal_memory_access"
    ):
        blockers.append("eh2_std_ref_get_canonical_trigger_orinto_still_faults")
        score += 1
    if (
        "eh2_std_ref_get_canonical_trigger_orinto_before_store_passes" in missing
        or "eh2_std_ref_get_canonical_trigger_orinto_before_store_passes" in sidecar_missing
        or std_ref_get_canonical_trigger_orinto_return_before_store_probe.get("status")
        == "std_ref_get_canonical_trigger_orinto_return_before_store_passed"
    ):
        blockers.append("eh2_std_ref_get_canonical_trigger_orinto_loads_and_or_pass")
    if (
        "eh2_std_ref_get_canonical_trigger_orinto_dst_store_fault" in missing
        or "eh2_std_ref_get_canonical_trigger_orinto_dst_store_fault" in sidecar_missing
        or std_ref_get_canonical_trigger_orinto_return_after_store_probe.get("status")
        == "std_ref_get_canonical_trigger_orinto_return_after_store_still_illegal_memory_access"
    ):
        blockers.append("eh2_std_ref_get_canonical_trigger_orinto_dst_store_fault")
        score += 1
    if (
        "eh2_vlunpacked_lm1_canonicalization_did_not_clear_eval_fault" in missing
        or "eh2_vlunpacked_lm1_canonicalization_did_not_clear_eval_fault" in sidecar_missing
        or vlunpacked_lm1_canonical_eval_only_probe.get("status")
        == "vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access"
    ):
        blockers.append("eh2_vlunpacked_lm1_canonicalization_did_not_clear_eval_fault")
        score += 1
    if (
        "eh2_vlunpacked_lm1_phase_act_before_orinto_passes" in missing
        or "eh2_vlunpacked_lm1_phase_act_before_orinto_passes" in sidecar_missing
        or vlunpacked_lm1_phase_act_return_before_orinto_probe.get("status")
        == "vlunpacked_lm1_phase_act_return_before_orinto_passed"
    ):
        blockers.append("eh2_vlunpacked_lm1_phase_act_before_orinto_passes")
    if (
        "eh2_vlunpacked_lm1_trigger_orinto_helper_call_entry_fault" in missing
        or "eh2_vlunpacked_lm1_trigger_orinto_helper_call_entry_fault" in sidecar_missing
        or vlunpacked_lm1_trigger_orinto_return_immediate_probe.get("status")
        == "vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access"
    ):
        blockers.append("eh2_vlunpacked_lm1_trigger_orinto_helper_call_entry_fault")
        score += 1
    if (
        "eh2_vlunpacked_lm1_orinto_rewrite_did_not_clear_eval_fault" in missing
        or "eh2_vlunpacked_lm1_orinto_rewrite_did_not_clear_eval_fault" in sidecar_missing
        or vlunpacked_lm1_orinto_rewrite_eval_only_probe.get("status")
        == "vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access"
    ):
        blockers.append("eh2_vlunpacked_lm1_inlined_orinto_store_context_fault")
        score += 1
    if (
        "eh2_orinto_store_value_or_store_itself_is_not_only_fault" in missing
        or "eh2_orinto_store_value_or_store_itself_is_not_only_fault" in sidecar_missing
        or (
            orinto_store_skip_eval_only_probe.get("status")
            == "orinto_store_skip_eval_only_still_illegal_memory_access"
            and orinto_store_zero_eval_only_probe.get("status")
            == "orinto_store_zero_eval_only_still_illegal_memory_access"
            and orinto_store_dst_eval_only_probe.get("status")
            == "orinto_store_dst_eval_only_still_illegal_memory_access"
        )
    ):
        blockers.append("eh2_orinto_store_value_or_store_itself_is_not_only_fault")
    if (
        "eh2_skip_store_timing_resume_passes" in missing
        or "eh2_skip_store_timing_resume_passes" in sidecar_missing
        or skip_store_return_after_timing_resume_probe.get("status")
        == "skip_store_return_after_timing_resume_passed"
    ):
        blockers.append("eh2_skip_store_timing_resume_passes")
    if (
        "eh2_skip_store_eval_act_boundary_fault" in missing
        or "eh2_skip_store_eval_act_boundary_fault" in sidecar_missing
        or skip_store_return_after_eval_act_probe.get("status")
        == "skip_store_return_after_eval_act_still_illegal_memory_access"
    ):
        blockers.append("eh2_post_vlunpacked_lm1_eval_act_boundary_fault")
        score += 1
    if (
        "eh2_eval_act_dec_cam0_act_sequent_boundary_fault" in missing
        or "eh2_eval_act_dec_cam0_act_sequent_boundary_fault" in sidecar_missing
        or (
            eval_act_callseq_951_probe.get("status") == "eval_act_return_after_callseq_951_passed"
            and eval_act_callseq_952_probe.get("status")
            == "eval_act_return_after_callseq_952_still_illegal_memory_access"
        )
    ):
        blockers.append("eh2_eval_act_dec_cam0_act_sequent_boundary_fault")
        score += 1
    if (
        "eh2_eval_act_submodule_act_call_boundary_fault" in missing
        or "eh2_eval_act_submodule_act_call_boundary_fault" in sidecar_missing
        or (
            dec_cam0_minimal_body_ret_probe.get("status")
            == "dec_cam0_minimal_body_ret_still_illegal_memory_access"
            and eval_act_skip_first_three_submodule_calls_probe.get("status")
            == "eval_act_skip_callseq_952_953_954_return_after_954_passed"
        )
    ):
        blockers.append("eh2_eval_act_submodule_act_call_boundary_fault")
        score += 1
    if (
        "eh2_vlwide_pointer_conversion_canonicalization_did_not_clear_eval_fault" in missing
        or "eh2_vlwide_pointer_conversion_canonicalization_did_not_clear_eval_fault" in sidecar_missing
        or vlwide_pointer_conversion_canonical_probe.get("status")
        == "vlwide_pointer_conversion_canonical_eval_only_still_illegal_memory_access"
    ):
        blockers.append("eh2_vlwide_pointer_conversion_canonicalization_did_not_clear_eval_fault")
        score += 1
    if (
        "eh2_vlwide_phase_act_trigger_merge_store_fault" in missing
        or "eh2_vlwide_phase_act_trigger_merge_store_fault" in sidecar_missing
        or (
            vlwide_phase_act_before_trigger_merge_store_probe.get("status")
            == "vlwide_phase_act_before_trigger_merge_store_passed"
            and vlwide_phase_act_after_trigger_merge_store_probe.get("status")
            == "vlwide_phase_act_after_trigger_merge_store_still_illegal_memory_access"
        )
    ):
        blockers.append("eh2_vlwide_phase_act_trigger_merge_store_fault")
        score += 1
    if (
        "eh2_vlwide_eval_phase_nba_eval_nba_fault" in missing
        or "eh2_vlwide_eval_phase_nba_eval_nba_fault" in sidecar_missing
        or (
            vlwide_phase_act_store_one_nba_before_eval_nba_probe.get("status")
            == "vlwide_phase_act_store_one_nba_before_eval_nba_passed"
            and vlwide_phase_act_store_one_nba_after_eval_nba_probe.get("status")
            == "vlwide_phase_act_store_one_nba_after_eval_nba_still_illegal_memory_access"
        )
    ):
        blockers.append("eh2_vlwide_eval_phase_nba_eval_nba_fault")
        score += 1
    if (
        "eh2_padded2m_does_not_clear_eval_phase_vnba_store_fault" in missing
        or "eh2_padded2m_does_not_clear_eval_phase_vnba_store_fault" in sidecar_missing
    ):
        blockers.append("eh2_padded_storage_does_not_clear_vnba_store_fault")
    if (
        "eh2_maxr128_does_not_clear_eval_phase_vnba_store_fault" in missing
        or "eh2_maxr128_does_not_clear_eval_phase_vnba_store_fault" in sidecar_missing
    ):
        blockers.append("eh2_register_cap_does_not_clear_vnba_store_fault")
    if surface.get("ready_to_port_from_descriptor") is True and "timing_report" in missing:
        blockers.append("descriptor_portable_but_measurement_surface_missing")
        score += 1
    if surface.get("program_sha256_matches_el2") is False:
        blockers.append("cannot_reuse_el2_program_or_authority_as_is")
        score += 1

    if row.get("timing_status") == "measured":
        best = row.get("best_timing_report") if isinstance(row.get("best_timing_report"), dict) else {}
        if isinstance(best.get("hybrid_vs_cpu_ratio"), (int, float)) and best.get("hybrid_vs_cpu_ratio") > 1:
            blockers.append("measured_hybrid_slower_than_cpu_reference")
            score += 1
        if best.get("serial_cpu_wall_time_outcome") == "sidecar_slower_than_serial_cpu":
            blockers.append("measured_sidecar_slower_than_serial_cpu")
            score += 1
        if best.get("cpu_parallel_wall_time_outcome") == "sidecar_faster_than_comparable_cpu_parallel_baseline":
            blockers.append("parallel_cpu_baseline_is_the_relevant_positive_comparison")

    for item in missing:
        if item not in immediate:
            immediate.append(item)
    next_action = row.get("next_action")
    if isinstance(next_action, str) and next_action and next_action not in immediate:
        immediate.insert(0, next_action)

    blockers = list(dict.fromkeys(blockers))
    immediate = list(dict.fromkeys(immediate))
    return blockers, immediate, score


def _transfer_summary(row: dict[str, Any]) -> dict[str, Any]:
    candidate = row.get("hybrid_candidate") if isinstance(row.get("hybrid_candidate"), dict) else {}
    h2d = candidate.get("real_cuda_runtime_sequence_preflight_h2d_bytes")
    d2h = candidate.get("real_cuda_runtime_sequence_preflight_d2h_initial_bytes")
    out: dict[str, Any] = {
        "h2d_bytes": h2d if isinstance(h2d, int) else None,
        "d2h_initial_bytes": d2h if isinstance(d2h, int) else None,
        "pcie_likely_first_order_risk": False,
        "reason": "not_quantified_for_this_row",
    }
    if isinstance(h2d, int) and isinstance(d2h, int):
        out["total_known_transfer_bytes"] = h2d + d2h
        out["pcie_likely_first_order_risk"] = h2d + d2h > 0 and row.get("timing_status") != "measured"
        out["reason"] = "known_cuda_transfer_bytes_without_cpu_vs_hybrid_timing"
    return out


def build_summary(repo_root: Path, *, matrix_path: Path = DEFAULT_MATRIX) -> dict[str, Any]:
    root = repo_root.resolve()
    matrix_file = matrix_path if matrix_path.is_absolute() else root / matrix_path
    matrix = _load_json(matrix_file)
    rows = matrix.get("rows")
    if not isinstance(rows, list):
        raise ValueError("matrix rows must be a list")

    difficulty_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        blockers, immediate, score = _classify_blockers(row)
        best = row.get("best_timing_report") if isinstance(row.get("best_timing_report"), dict) else {}
        difficulty_rows.append(
            {
                "case": row.get("case"),
                "design": row.get("design"),
                "measurement_status": row.get("measurement_status"),
                "timing_status": row.get("timing_status"),
                "correctness_status": row.get("correctness_status"),
                "speedup_claimed": row.get("speedup_claimed") is True,
                "difficulty_score": score,
                "difficulty_class": "high" if score >= 6 else "medium" if score >= 3 else "measured_or_low",
                "primary_blockers": blockers,
                "immediate_next_requirements": immediate[:6],
                "transfer": _transfer_summary(row),
                "best_measured_ratio": best.get("sidecar_vs_cpu_parallel_ratio"),
                "best_hybrid_vs_cpu_ratio": best.get("hybrid_vs_cpu_ratio"),
                "best_cpu_vs_hybrid_speedup": best.get("cpu_vs_hybrid_speedup"),
                "serial_cpu_outcome": best.get("serial_cpu_wall_time_outcome"),
                "cpu_parallel_outcome": best.get("cpu_parallel_wall_time_outcome"),
            }
        )

    unmeasured = [row for row in difficulty_rows if row["timing_status"] != "measured"]
    measured = [row for row in difficulty_rows if row["timing_status"] == "measured"]
    return {
        "schema_version": 1,
        "surface": "rtlmeter_hybrid_measurement_difficulty",
        "status": "hybrid_measurement_difficulty_summarized",
        "matrix_report": _display_path(matrix_file, repo_root=root),
        "target_count": len(difficulty_rows),
        "measured_count": len(measured),
        "unmeasured_count": len(unmeasured),
        "highest_difficulty_cases": [
            row["case"] for row in sorted(difficulty_rows, key=lambda item: item["difficulty_score"], reverse=True)
        ],
        "rows": difficulty_rows,
        "non_claims": [
            "not_new_measurement",
            "not_speedup_claim",
            "not_runtime_authority",
            "difficulty_score_is_triage_metadata_not_performance_metric",
        ],
    }


def to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "| case | status | difficulty | first blockers | transfer risk | measured comparison |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in summary.get("rows", []):
        if not isinstance(row, dict):
            continue
        primary = row.get("primary_blockers", []) if isinstance(row.get("primary_blockers"), list) else []
        immediate = (
            row.get("immediate_next_requirements", [])
            if isinstance(row.get("immediate_next_requirements"), list)
            else []
        )
        blocker_source = list(immediate) + list(primary) if row.get("timing_status") != "measured" else list(primary)
        specific = [
            item
            for item in blocker_source
            if isinstance(item, str)
            and item
            and item
            not in {
                "timing_report_missing",
                "timing_report",
                "correctness_not_measured_or_not_passed",
                "sidecar_bridge_preflight_hybrid_surface_missing",
                "gpu_artifact_prelaunch_rejection_required",
            }
        ]
        blocker_items = specific[:3] if specific else primary[:3]
        blockers = ", ".join(str(item) for item in blocker_items)
        transfer = row.get("transfer") if isinstance(row.get("transfer"), dict) else {}
        transfer_text = (
            f"{transfer.get('total_known_transfer_bytes')} bytes known"
            if transfer.get("total_known_transfer_bytes") is not None
            else str(transfer.get("reason"))
        )
        ratio = row.get("best_measured_ratio")
        hybrid_ratio = row.get("best_hybrid_vs_cpu_ratio")
        speedup = row.get("best_cpu_vs_hybrid_speedup")
        if ratio is not None:
            comparison = f"parallel ratio {ratio}"
        elif hybrid_ratio is not None:
            comparison = f"hybrid/cpu {hybrid_ratio}, speedup {speedup}"
        else:
            comparison = "not measured"
        lines.append(
            "| {case} | {status} | {score} {klass} | {blockers} | {transfer} | {comparison} |".format(
                case=row.get("case"),
                status=row.get("measurement_status"),
                score=row.get("difficulty_score"),
                klass=row.get("difficulty_class"),
                blockers=blockers,
                transfer=transfer_text,
                comparison=comparison,
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--matrix", default=DEFAULT_MATRIX.as_posix())
    parser.add_argument("--report-out", default="reports/rtlmeter_hybrid_measurement_difficulty.json")
    parser.add_argument("--markdown-out", default="reports/rtlmeter_hybrid_measurement_difficulty.md")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    summary = build_summary(root, matrix_path=Path(args.matrix))
    if args.write_report:
        report_out = Path(args.report_out)
        report_path = report_out if report_out.is_absolute() else root / report_out
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        markdown_out = Path(args.markdown_out)
        markdown_path = markdown_out if markdown_out.is_absolute() else root / markdown_out
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(to_markdown(summary), encoding="utf-8")
    print(to_markdown(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
