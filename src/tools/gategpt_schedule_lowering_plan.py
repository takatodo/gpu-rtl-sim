#!/usr/bin/env python3
"""Active gateGPT schedule-lowering constants and plan validators."""

from __future__ import annotations

from typing import Any


PAIR_CYCLE_LOOP_ENV = {
    "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE": "1",
    "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START": "0",
    "RUN_VL_HYBRID_FUSED_PAIR_CYCLE": "1",
    "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP": "1",
}

REQUIRED_PADDED_START_ENTRYPOINTS = [
    "vl_apply_feedback_sets_gpu",
    "vl_apply_feedback_combined_gpu",
    "vl_patch_eval_pair_cycle_loop_batch_gpu",
]

ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP = "ordering_aware_phase_resident_token_loop"
ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES = 1701
ORDERING_AWARE_CHUNKED_CONTINUATION_BLOCKED_STATUS = (
    "blocked_phase_control_chunk_continuation_requires_generated_continuation_abi"
)
REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS = [
    "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu",
]
ORDERING_AWARE_IMPLEMENTATION_STAGE = (
    "prototype_entrypoint_phase_feedback_terminal_mask_body_available_runtime_owner_available_cpu_comparison_pending"
)


def validate_padded_start_lowering_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate a padded-start lowering plan as a consumable schedule artifact."""
    errors: list[str] = []
    if plan.get("status") != "ready_for_schedule_lowering":
        errors.append("status must be ready_for_schedule_lowering")
    if plan.get("schedule_shape") != "padded_start_pair_cycle_loop":
        errors.append("schedule_shape must be padded_start_pair_cycle_loop")
    if plan.get("pad_start_pulse_for_loop") is not True:
        errors.append("pad_start_pulse_for_loop must be true")
    if plan.get("hold_start_after_phase_set") is not False:
        errors.append("hold_start_after_phase_set must be false")
    if plan.get("requires_resident_steps") is not True:
        errors.append("requires_resident_steps must be true")
    if plan.get("requires_multi_phase_persistent_resident_abi") is not True:
        errors.append("requires_multi_phase_persistent_resident_abi must be true")

    entrypoints = plan.get("required_runtime_entrypoints")
    if not isinstance(entrypoints, list):
        errors.append("required_runtime_entrypoints must be a list")
    else:
        missing = [name for name in REQUIRED_PADDED_START_ENTRYPOINTS if name not in entrypoints]
        if missing:
            errors.append(f"missing required_runtime_entrypoints: {', '.join(missing)}")

    env = plan.get("env_overrides")
    if not isinstance(env, dict):
        errors.append("env_overrides must be a dict")
    else:
        expected_env = {
            **PAIR_CYCLE_LOOP_ENV,
            "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK": str(plan.get("loop_chunk")),
        }
        for key, value in expected_env.items():
            if env.get(key) != value:
                errors.append(f"env_overrides.{key} must be {value}")

    expected = plan.get("expected_launch_shape")
    phase_count = plan.get("phase_count")
    if not isinstance(phase_count, int) or phase_count < 1:
        errors.append("phase_count must be a positive integer")
    if not isinstance(expected, dict):
        errors.append("expected_launch_shape must be a dict")
    elif isinstance(phase_count, int):
        expected_values = {
            "phase_set_launches": phase_count,
            "combined_feedback_launches": max(phase_count - 1, 0),
            "pair_cycle_fusion_launches": 0,
            "pair_cycle_loop_kernel_launches": phase_count,
            "pair_cycle_loop_fallbacks": 0,
        }
        for key, value in expected_values.items():
            if expected.get(key) != value:
                errors.append(f"expected_launch_shape.{key} must be {value}")

    return {
        "status": "valid" if not errors else "invalid",
        "valid": not errors,
        "errors": errors,
        "runtime_env": dict(sorted(env.items())) if isinstance(env, dict) else {},
        "required_runtime_entrypoints": list(entrypoints) if isinstance(entrypoints, list) else [],
        "expected_launch_shape": dict(expected) if isinstance(expected, dict) else {},
    }


def validate_ordering_aware_phase_resident_token_loop_lowering_plan(
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Validate the #69 lowering-plan artifact as a runtime-consumable gate."""
    errors: list[str] = []
    if plan.get("schedule_shape") != ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        errors.append(f"schedule_shape must be {ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP}")
    if plan.get("implementation_stage") != ORDERING_AWARE_IMPLEMENTATION_STAGE:
        errors.append(f"implementation_stage must be {ORDERING_AWARE_IMPLEMENTATION_STAGE}")
    for claim in ("runtime_correctness_claimed", "speedup_claimed", "usefulness_claimed"):
        if plan.get(claim) is not False:
            errors.append(f"{claim} must be false")

    nstates = plan.get("nstates")
    phase_count = plan.get("phase_count")
    loop_chunk = plan.get("loop_chunk")
    if not isinstance(nstates, int) or nstates < 1:
        errors.append("nstates must be a positive integer")
    if not isinstance(phase_count, int) or phase_count < 1:
        errors.append("phase_count must be a positive integer")
    if not isinstance(loop_chunk, int) or loop_chunk < 1:
        errors.append("loop_chunk must be a positive integer")

    full_chunk = (
        isinstance(loop_chunk, int)
        and loop_chunk >= ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES
    )
    continuation_required = isinstance(loop_chunk, int) and loop_chunk > 0 and not full_chunk
    expected_status = (
        "ready_for_schedule_integrated_cpu_comparison"
        if full_chunk
        else ORDERING_AWARE_CHUNKED_CONTINUATION_BLOCKED_STATUS
    )
    if plan.get("status") != expected_status:
        errors.append(f"status must be {expected_status}")
    if plan.get("full_logical_phase_pair_cycles") != ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES:
        errors.append(
            "full_logical_phase_pair_cycles must be "
            f"{ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES}"
        )
    if isinstance(loop_chunk, int) and loop_chunk > 0:
        if plan.get("full_logical_phase_chunk") is not full_chunk:
            errors.append("full_logical_phase_chunk must match loop_chunk")
        if plan.get("phase_control_continuation_required") is not continuation_required:
            errors.append("phase_control_continuation_required must match loop_chunk")
    if plan.get("phase_control_continuation_abi_available") is not False:
        errors.append("phase_control_continuation_abi_available must be false")

    entrypoints = plan.get("required_runtime_entrypoints")
    if not isinstance(entrypoints, list):
        errors.append("required_runtime_entrypoints must be a list")
    else:
        missing = [
            name for name in REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS if name not in entrypoints
        ]
        if missing:
            errors.append(f"missing required_runtime_entrypoints: {', '.join(missing)}")

    required_fields = plan.get("required_runtime_plan_fields")
    expected_fields = {
        "phase_control_records",
        "feedback_copy_records",
        "feedback_increment_records",
        "pair_cycle_loop_records",
        "per_state_terminal_mask",
    }
    if not isinstance(required_fields, list) or set(required_fields) != expected_fields:
        errors.append("required_runtime_plan_fields must cover phase controls, feedback, loop records, and terminal mask")

    env = plan.get("env_overrides")
    if not isinstance(env, dict):
        errors.append("env_overrides must be a dict")
    else:
        if env.get("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE") != "1":
            errors.append("env_overrides must request the ordering-aware ABI probe")
        expected_owner_env = {
            "RUN_VL_HYBRID_FUSED_PAIR_CYCLE": "1",
            "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP": "1",
            "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE": "1",
            "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START": "0",
        }
        for key, value in expected_owner_env.items():
            if env.get(key) != value:
                errors.append(f"env_overrides.{key} must be {value}")
        if isinstance(loop_chunk, int) and env.get("RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK") != str(loop_chunk):
            errors.append("env_overrides must pass RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK matching loop_chunk")
        terminal_mask = env.get("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK")
        if terminal_mask is not None and not isinstance(terminal_mask, str):
            errors.append("terminal-mask env override must be a string when present")

    target = plan.get("target_launch_shape")
    if not isinstance(target, dict):
        errors.append("target_launch_shape must be a dict")
    else:
        expected_target = {
            "phase_set_launches": 0,
            "combined_feedback_launches": 0,
            "pair_cycle_loop_kernel_launches": 0,
            "ordering_aware_token_loop_kernel_launches": 1,
            "pair_cycle_loop_fallbacks": 0,
        }
        for key, value in expected_target.items():
            if target.get(key) != value:
                errors.append(f"target_launch_shape.{key} must be {value}")
        if isinstance(phase_count, int) and isinstance(loop_chunk, int) and loop_chunk > 0:
            expected_max = phase_count * (
                (ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES + loop_chunk - 1)
                // loop_chunk
            )
            if target.get("ordering_aware_token_loop_kernel_launches_max") != expected_max:
                errors.append(
                    "target_launch_shape.ordering_aware_token_loop_kernel_launches_max "
                    f"must be {expected_max}"
                )

    return {
        "status": expected_status if not errors else "invalid",
        "valid": not errors,
        "runtime_supported": not errors and not continuation_required,
        "errors": errors,
        "schedule_shape": plan.get("schedule_shape"),
        "required_runtime_entrypoints": list(entrypoints) if isinstance(entrypoints, list) else [],
        "required_runtime_plan_fields": list(required_fields) if isinstance(required_fields, list) else [],
        "env_overrides": dict(env) if isinstance(env, dict) else {},
        "target_launch_shape": dict(target) if isinstance(target, dict) else {},
        "blocking_reason": plan.get("blocking_reason"),
        "full_logical_phase_chunk": plan.get("full_logical_phase_chunk"),
        "phase_control_continuation_required": plan.get("phase_control_continuation_required"),
        "phase_control_continuation_abi_available": plan.get("phase_control_continuation_abi_available"),
    }
