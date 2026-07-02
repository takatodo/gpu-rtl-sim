#!/usr/bin/env python3
"""Reusable gateGPT schedule-shape planning helpers."""

from __future__ import annotations

import json
from pathlib import Path
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


def _offset(offsets: dict[str, dict[str, int]], field: str) -> int:
    return int(offsets[field]["offset"])


def build_phase_set_start_control_patch_lines(
    offsets: dict[str, dict[str, int]],
    *,
    clk_field: str,
    resetn_field: str,
    start_field: str,
    nstates: int = 1,
    run_cycles: int = 1700,
    trim_final_low: bool = False,
    global_start_pulse: bool = False,
    hold_start_after_phase_set: bool = False,
    pad_start_pulse_for_loop: bool = False,
) -> list[str]:
    """Build a reset/start/clock schedule that is eligible for pair-cycle loops.

    ``pad_start_pulse_for_loop`` is the reusable lowering rule: preserve the
    one-cycle start pulse by writing start=1 in both records of the first
    low/high pair, then start=0 in the repeated loop pairs. This gives the loop
    matcher equal low/high patch-record shapes without holding start high.
    """
    if nstates < 1:
        raise ValueError("nstates must be at least 1")
    if run_cycles < 0:
        raise ValueError("run_cycles must be non-negative")

    clk = _offset(offsets, clk_field)
    resetn = _offset(offsets, resetn_field)
    start = _offset(offsets, start_field)
    lines: list[str] = []

    def bpatch(offset: int, value: int) -> str:
        return f"{offset}:{value}"

    def spatch(state: int, offset: int, value: int) -> str:
        return f"@{state}:{offset}:{value}"

    def state_tokens(*pairs: tuple[int, int]) -> list[str]:
        return [
            spatch(state, offset, value)
            for state in range(nstates)
            for offset, value in pairs
        ]

    include_start_drop = not hold_start_after_phase_set
    include_first_start_high = global_start_pulse or pad_start_pulse_for_loop
    if nstates == 1:
        start_high = [bpatch(start, 1)] if include_first_start_high else []
        lines.append(" ".join([bpatch(clk, 0), bpatch(resetn, 1), *start_high]))
        lines.append(" ".join([bpatch(clk, 1), bpatch(resetn, 1), *start_high]))
        drop_tokens = [bpatch(start, 0)] if include_start_drop else []
        lines.append(" ".join([bpatch(clk, 0), bpatch(resetn, 1), *drop_tokens]))
    else:
        first_pairs = (
            ((clk, 0), (resetn, 1), (start, 1))
            if include_first_start_high
            else ((clk, 0), (resetn, 1))
        )
        high_pairs = (
            ((clk, 1), (resetn, 1), (start, 1))
            if include_first_start_high
            else ((clk, 1), (resetn, 1))
        )
        lines.append(" ".join(state_tokens(*first_pairs)))
        lines.append(" ".join(state_tokens(*high_pairs)))
        drop_pairs = (
            ((clk, 0), (resetn, 1), (start, 0))
            if include_start_drop
            else ((clk, 0), (resetn, 1))
        )
        lines.append(" ".join(state_tokens(*drop_pairs)))

    for _ in range(run_cycles):
        if nstates == 1:
            drop_tokens = [bpatch(start, 0)] if include_start_drop else []
            lines.append(" ".join([bpatch(clk, 1), bpatch(resetn, 1), *drop_tokens]))
            lines.append(" ".join([bpatch(clk, 0), bpatch(resetn, 1), *drop_tokens]))
        else:
            high_pairs = (
                ((clk, 1), (resetn, 1), (start, 0))
                if include_start_drop
                else ((clk, 1), (resetn, 1))
            )
            low_pairs = (
                ((clk, 0), (resetn, 1), (start, 0))
                if include_start_drop
                else ((clk, 0), (resetn, 1))
            )
            lines.append(" ".join(state_tokens(*high_pairs)))
            lines.append(" ".join(state_tokens(*low_pairs)))

    if trim_final_low and lines:
        lines.pop()
    return lines


def build_padded_start_pair_cycle_loop_lowering_plan(
    *,
    nstates: int,
    phase_count: int,
    loop_chunk: int = 1701,
) -> dict[str, object]:
    """Return the runtime-facing lowering plan for padded-start loop fusion."""
    if nstates < 1:
        raise ValueError("nstates must be at least 1")
    if phase_count < 1:
        raise ValueError("phase_count must be at least 1")
    if loop_chunk < 1:
        raise ValueError("loop_chunk must be at least 1")

    env = {
        **PAIR_CYCLE_LOOP_ENV,
        "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK": str(loop_chunk),
    }
    return {
        "planner": "gategpt_schedule_planner.build_padded_start_pair_cycle_loop_lowering_plan",
        "status": "ready_for_schedule_lowering",
        "schedule_shape": "padded_start_pair_cycle_loop",
        "nstates": nstates,
        "phase_count": phase_count,
        "loop_chunk": loop_chunk,
        "pad_start_pulse_for_loop": True,
        "hold_start_after_phase_set": False,
        "trim_final_low": True,
        "requires_resident_steps": True,
        "requires_multi_phase_persistent_resident_abi": True,
        "required_runtime_entrypoints": list(REQUIRED_PADDED_START_ENTRYPOINTS),
        "env_overrides": env,
        "expected_launch_shape": {
            "phase_set_launches": phase_count,
            "combined_feedback_launches": max(phase_count - 1, 0),
            "pair_cycle_fusion_launches": 0,
            "pair_cycle_loop_kernel_launches": phase_count,
            "pair_cycle_loop_fallbacks": 0,
        },
        "eligibility_rules": [
            "clk/resetn/start fields have reviewed state-local offsets",
            "the first low/high pair writes start=1 in both records",
            "subsequent loop pairs write start=0 in both records",
            "phase sets provide per-state start/smode/inv_temp and initial token/rng/pos controls",
            "combined feedback copies next_token/rng_out and increments pos between phases",
        ],
        "non_claims": [
            "does not prove stdout/PASS/$finish authority",
            "does not prove cycle-summary authority",
            "does not claim speedup or usefulness",
            "does not generalize arbitrary Verilog initial blocks",
        ],
    }


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
        missing = [
            name
            for name in REQUIRED_PADDED_START_ENTRYPOINTS
            if name not in entrypoints
        ]
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


def build_ordering_aware_phase_resident_token_loop_contract(
    *,
    nstates: int,
    phase_count: int,
    current_launch_shape: dict[str, Any],
) -> dict[str, Any]:
    """Return the #69 prototype contract for collapsing tb_core phase launches.

    This is a design/verification contract, not execution evidence. It captures
    the next runtime structure required after padded-start: one ordered resident
    token-loop surface that owns phase-set writes, feedback copy/increment, and
    pair-cycle-loop eval ordering without holding ``start`` high.
    """
    if nstates < 1:
        raise ValueError("nstates must be at least 1")
    if phase_count < 1:
        raise ValueError("phase_count must be at least 1")

    absorbed = [
        "phase_set",
        "combined_feedback",
        "pair_cycle_loop",
    ]
    return {
        "planner": "gategpt_schedule_planner.build_ordering_aware_phase_resident_token_loop_contract",
        "status": "ready_for_prototype_contract",
        "contract": ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP,
        "issue": "https://github.com/takatodo/gpu-rtl-sim/issues/69",
        "nstates": nstates,
        "phase_count": phase_count,
        "current_launch_shape": dict(current_launch_shape),
        "launch_classes_to_absorb": absorbed,
        "required_runtime_entrypoints": list(REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS),
        "target_launch_shape": {
            "phase_set_launches": 0,
            "combined_feedback_launches": 0,
            "pair_cycle_loop_kernel_launches": 0,
            "ordering_aware_token_loop_kernel_launches": 1,
            "pair_cycle_loop_fallbacks": 0,
        },
        "ordering_requirements": [
            "for each token phase, apply per-state start/smode/inv_temp controls before eval",
            "preserve one-cycle start semantics; do not hold start high after the phase-start pair",
            "run low/eval/high pair-cycle ordering for the configured loop chunk",
            "after each non-final token phase, copy next_token/rng_out and increment pos_in before the next phase controls",
            "preserve per-state token stream ordering independently across all states",
        ],
        "minimum_correctness_gate": [
            "16/16 tb_core CPU-oracle token streams match",
            "fresh CPU oracle wall comparison is recorded",
            "speedup/usefulness remain false unless the CPU comparison is positive",
            "stdout/PASS/$finish authority remains separate from this performance contract",
        ],
        "non_claims": [
            "does not prove the token-loop entrypoint exists",
            "does not execute gateGPT",
            "does not claim speedup or usefulness",
            "does not claim broad gateGPT PASS/FAIL authority",
        ],
    }


def build_ordering_aware_phase_resident_token_loop_lowering_plan(
    *,
    nstates: int,
    phase_count: int,
    loop_chunk: int = 1701,
    terminal_mask_specs: str | None = None,
) -> dict[str, Any]:
    """Return the #69 runtime-plan artifact for the schedule-owned token loop."""
    if nstates < 1:
        raise ValueError("nstates must be at least 1")
    if phase_count < 1:
        raise ValueError("phase_count must be at least 1")
    if loop_chunk < 1:
        raise ValueError("loop_chunk must be at least 1")

    full_logical_phase_chunk = loop_chunk >= ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES
    continuation_required = not full_logical_phase_chunk
    status = (
        "ready_for_schedule_integrated_cpu_comparison"
        if full_logical_phase_chunk
        else ORDERING_AWARE_CHUNKED_CONTINUATION_BLOCKED_STATUS
    )
    blocking_reason = (
        "the ordering-aware kernel body and schedule-owned runtime launch path are available; "
        "the remaining gate is the measured CPU-negative gap before any usefulness claim"
        if full_logical_phase_chunk
        else (
            "loop_chunk is smaller than one full logical tb_core phase; chunked phase-control "
            "continuation requires a generated continuation ABI, so rerun with loop_chunk >= "
            f"{ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES} or generate the continuation ABI"
        )
    )

    env_overrides = {
        "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE": "1",
        "RUN_VL_HYBRID_FUSED_PAIR_CYCLE": "1",
        "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP": "1",
        "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK": str(loop_chunk),
        "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE": "1",
        "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START": "0",
    }
    if terminal_mask_specs:
        env_overrides["RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK"] = terminal_mask_specs

    return {
        "planner": (
            "gategpt_schedule_planner."
            "build_ordering_aware_phase_resident_token_loop_lowering_plan"
        ),
        "status": status,
        "schedule_shape": ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP,
        "issue": "https://github.com/takatodo/gpu-rtl-sim/issues/69",
        "nstates": nstates,
        "phase_count": phase_count,
        "loop_chunk": loop_chunk,
        "full_logical_phase_pair_cycles": ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES,
        "full_logical_phase_chunk": full_logical_phase_chunk,
        "phase_control_continuation_required": continuation_required,
        "phase_control_continuation_abi_available": False,
        "phase_control_continuation_abi_required_when": (
            f"loop_chunk < {ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES}"
        ),
        "required_runtime_entrypoints": list(REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS),
        "required_runtime_plan_fields": [
            "phase_control_records",
            "feedback_copy_records",
            "feedback_increment_records",
            "pair_cycle_loop_records",
            "per_state_terminal_mask",
        ],
        "env_overrides": env_overrides,
        "target_launch_shape": {
            "phase_set_launches": 0,
            "combined_feedback_launches": 0,
            "pair_cycle_loop_kernel_launches": 0,
            "ordering_aware_token_loop_kernel_launches": 1,
            "ordering_aware_token_loop_kernel_launches_max": (
                phase_count
                * (
                    (
                        ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES
                        + loop_chunk
                        - 1
                    )
                    // loop_chunk
                )
            ),
            "pair_cycle_loop_fallbacks": 0,
        },
        "implementation_stage": (
            "prototype_entrypoint_phase_feedback_terminal_mask_body_available_runtime_owner_available_cpu_comparison_pending"
        ),
        "runtime_correctness_claimed": False,
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "blocking_reason": blocking_reason,
        "non_claims": [
            "the plan artifact alone does not prove 16/16 tb_core CPU-oracle token streams",
            "the plan artifact alone does not prove a positive CPU comparison",
            "does not claim speedup or usefulness",
        ],
    }


def validate_ordering_aware_phase_resident_token_loop_contract(
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Validate the #69 token-loop prototype contract as planning evidence."""
    errors: list[str] = []
    if contract.get("status") != "ready_for_prototype_contract":
        errors.append("status must be ready_for_prototype_contract")
    if contract.get("contract") != ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        errors.append(f"contract must be {ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP}")

    nstates = contract.get("nstates")
    phase_count = contract.get("phase_count")
    if not isinstance(nstates, int) or nstates < 1:
        errors.append("nstates must be a positive integer")
    if not isinstance(phase_count, int) or phase_count < 1:
        errors.append("phase_count must be a positive integer")

    entrypoints = contract.get("required_runtime_entrypoints")
    if not isinstance(entrypoints, list):
        errors.append("required_runtime_entrypoints must be a list")
    else:
        missing = [
            name
            for name in REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS
            if name not in entrypoints
        ]
        if missing:
            errors.append(f"missing required_runtime_entrypoints: {', '.join(missing)}")

    absorbed = contract.get("launch_classes_to_absorb")
    required_absorbed = {"phase_set", "combined_feedback", "pair_cycle_loop"}
    if not isinstance(absorbed, list) or set(absorbed) != required_absorbed:
        errors.append("launch_classes_to_absorb must cover phase_set, combined_feedback, and pair_cycle_loop")

    target = contract.get("target_launch_shape")
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

    ordering_requirements = contract.get("ordering_requirements")
    if not isinstance(ordering_requirements, list) or len(ordering_requirements) < 5:
        errors.append("ordering_requirements must list the phase/control/feedback ordering constraints")

    minimum_gate = contract.get("minimum_correctness_gate")
    if not isinstance(minimum_gate, list) or not any("16/16" in str(item) for item in minimum_gate):
        errors.append("minimum_correctness_gate must include the 16/16 CPU-oracle token-stream gate")

    return {
        "status": "valid" if not errors else "invalid",
        "valid": not errors,
        "errors": errors,
        "contract": contract.get("contract"),
        "required_runtime_entrypoints": list(entrypoints) if isinstance(entrypoints, list) else [],
        "target_launch_shape": dict(target) if isinstance(target, dict) else {},
        "launch_classes_to_absorb": list(absorbed) if isinstance(absorbed, list) else [],
    }


def validate_ordering_aware_phase_resident_token_loop_lowering_plan(
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Validate the #69 lowering-plan artifact as a runtime-consumable gate."""
    errors: list[str] = []
    if plan.get("schedule_shape") != ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        errors.append(f"schedule_shape must be {ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP}")
    if plan.get("implementation_stage") != "prototype_entrypoint_phase_feedback_terminal_mask_body_available_runtime_owner_available_cpu_comparison_pending":
        errors.append("implementation_stage must be prototype_entrypoint_phase_feedback_terminal_mask_body_available_runtime_owner_available_cpu_comparison_pending")
    if plan.get("runtime_correctness_claimed") is not False:
        errors.append("runtime_correctness_claimed must be false")
    if plan.get("speedup_claimed") is not False:
        errors.append("speedup_claimed must be false")
    if plan.get("usefulness_claimed") is not False:
        errors.append("usefulness_claimed must be false")

    nstates = plan.get("nstates")
    phase_count = plan.get("phase_count")
    loop_chunk = plan.get("loop_chunk")
    if not isinstance(nstates, int) or nstates < 1:
        errors.append("nstates must be a positive integer")
    if not isinstance(phase_count, int) or phase_count < 1:
        errors.append("phase_count must be a positive integer")
    if not isinstance(loop_chunk, int) or loop_chunk < 1:
        errors.append("loop_chunk must be a positive integer")
    full_logical_phase_chunk = (
        isinstance(loop_chunk, int)
        and loop_chunk >= ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES
    )
    continuation_required = isinstance(loop_chunk, int) and loop_chunk > 0 and not full_logical_phase_chunk
    expected_status = (
        "ready_for_schedule_integrated_cpu_comparison"
        if full_logical_phase_chunk
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
        if plan.get("full_logical_phase_chunk") is not full_logical_phase_chunk:
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
            name
            for name in REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS
            if name not in entrypoints
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

    env_overrides = plan.get("env_overrides")
    if not isinstance(env_overrides, dict):
        errors.append("env_overrides must be a dict")
    else:
        if env_overrides.get("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE") != "1":
            errors.append("env_overrides must request the ordering-aware ABI probe")
        expected_owner_env = {
            "RUN_VL_HYBRID_FUSED_PAIR_CYCLE": "1",
            "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP": "1",
            "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE": "1",
            "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START": "0",
        }
        for key, value in expected_owner_env.items():
            if env_overrides.get(key) != value:
                errors.append(f"env_overrides.{key} must be {value}")
        if (
            isinstance(loop_chunk, int)
            and env_overrides.get("RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK")
            != str(loop_chunk)
        ):
            errors.append(
                "env_overrides must pass RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK matching loop_chunk"
            )
        terminal_mask = env_overrides.get("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK")
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

    runtime_supported = not errors and not continuation_required
    status = expected_status if not errors else "invalid"

    return {
        "status": status,
        "valid": not errors,
        "runtime_supported": runtime_supported,
        "errors": errors,
        "schedule_shape": plan.get("schedule_shape"),
        "required_runtime_entrypoints": list(entrypoints) if isinstance(entrypoints, list) else [],
        "required_runtime_plan_fields": list(required_fields) if isinstance(required_fields, list) else [],
        "env_overrides": dict(env_overrides) if isinstance(env_overrides, dict) else {},
        "target_launch_shape": dict(target) if isinstance(target, dict) else {},
        "blocking_reason": plan.get("blocking_reason"),
        "full_logical_phase_chunk": plan.get("full_logical_phase_chunk"),
        "phase_control_continuation_required": plan.get(
            "phase_control_continuation_required"
        ),
        "phase_control_continuation_abi_available": plan.get(
            "phase_control_continuation_abi_available"
        ),
    }


def build_dynamic_cold_partition_predicate_contract(
    *,
    partition_count: int,
    active_block_gate_count: int,
    static_skip_candidate_count: int,
    static_skip_rejected_count: int,
    ordering_aware_plan: dict[str, Any],
) -> dict[str, Any]:
    """Describe the next ABI needed before attempting eval partition skipping."""
    if partition_count < 1:
        raise ValueError("partition_count must be at least 1")
    if active_block_gate_count < 1:
        raise ValueError("active_block_gate_count must be at least 1")
    if static_skip_candidate_count < 0:
        raise ValueError("static_skip_candidate_count must be non-negative")
    if static_skip_rejected_count < 0:
        raise ValueError("static_skip_rejected_count must be non-negative")
    validation = validate_ordering_aware_phase_resident_token_loop_lowering_plan(
        ordering_aware_plan
    )
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))

    existing_inputs = [
        "current_phase",
        "phase_control_records",
        "per_state_terminal_mask",
        "pair_cycle_loop_records",
    ]
    missing_inputs = [
        "eval_hot_path_partition_id_map",
        "per_phase_per_state_partition_active_mask",
        "direct_eval_callee_predicate_pointer_abi",
    ]
    return {
        "planner": "gategpt_schedule_planner.build_dynamic_cold_partition_predicate_contract",
        "status": "ready_for_dynamic_predicate_abi_design",
        "contract": "derive_dynamic_cold_partition_predicate_after_skip_safety_classification",
        "base_schedule_shape": ordering_aware_plan["schedule_shape"],
        "partition_count": partition_count,
        "active_block_gate_count": active_block_gate_count,
        "static_skip_candidate_count": static_skip_candidate_count,
        "static_skip_rejected_count": static_skip_rejected_count,
        "existing_runtime_inputs": existing_inputs,
        "missing_runtime_inputs": missing_inputs,
        "proposed_runtime_plan_fields": [
            *ordering_aware_plan["required_runtime_plan_fields"],
            "eval_hot_path_partition_id_map",
            "per_phase_per_state_partition_active_mask",
        ],
        "proposed_kernel_abi_extension": [
            "cold_partition_active_mask",
            "cold_partition_count",
        ],
        "required_pass_work": [
            "assign_stable_eval_hot_path_partition_ids",
            "expose_predicate_pointer_to_direct_eval_callees",
            "guard_only_blocks_with_authoritative_partition_active_mask",
            "preserve_cpu_token_oracle_correctness_before_any_timing_claim",
        ],
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "blocking_reason": (
            "static skip classification found no semantics-preserving continuation "
            "skip candidates, so an authoritative dynamic per-partition predicate "
            "is required before any real skip transform"
        ),
    }


def validate_dynamic_cold_partition_predicate_contract(
    contract: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if contract.get("status") != "ready_for_dynamic_predicate_abi_design":
        errors.append("status must be ready_for_dynamic_predicate_abi_design")
    if (
        contract.get("contract")
        != "derive_dynamic_cold_partition_predicate_after_skip_safety_classification"
    ):
        errors.append("contract must be derive_dynamic_cold_partition_predicate_after_skip_safety_classification")
    if contract.get("speedup_claimed") is not False:
        errors.append("speedup_claimed must be false")
    if contract.get("usefulness_claimed") is not False:
        errors.append("usefulness_claimed must be false")

    partition_count = contract.get("partition_count")
    if not isinstance(partition_count, int) or partition_count < 1:
        errors.append("partition_count must be a positive integer")
    active_gate_count = contract.get("active_block_gate_count")
    if not isinstance(active_gate_count, int) or active_gate_count < 1:
        errors.append("active_block_gate_count must be a positive integer")
    static_candidates = contract.get("static_skip_candidate_count")
    if not isinstance(static_candidates, int) or static_candidates < 0:
        errors.append("static_skip_candidate_count must be a non-negative integer")

    existing = contract.get("existing_runtime_inputs")
    required_existing = {
        "current_phase",
        "phase_control_records",
        "per_state_terminal_mask",
        "pair_cycle_loop_records",
    }
    if not isinstance(existing, list) or not required_existing.issubset(existing):
        errors.append("existing_runtime_inputs must include current phase, phase control, terminal mask, and pair-cycle records")

    missing = contract.get("missing_runtime_inputs")
    required_missing = {
        "eval_hot_path_partition_id_map",
        "per_phase_per_state_partition_active_mask",
        "direct_eval_callee_predicate_pointer_abi",
    }
    if not isinstance(missing, list) or set(missing) != required_missing:
        errors.append("missing_runtime_inputs must identify partition ids, active mask, and direct eval predicate pointer ABI")

    abi = contract.get("proposed_kernel_abi_extension")
    if not isinstance(abi, list) or set(abi) != {
        "cold_partition_active_mask",
        "cold_partition_count",
    }:
        errors.append("proposed_kernel_abi_extension must include cold_partition_active_mask and cold_partition_count")

    return {
        "status": "valid" if not errors else "invalid",
        "valid": not errors,
        "errors": errors,
        "contract": contract.get("contract"),
        "missing_runtime_inputs": list(missing) if isinstance(missing, list) else [],
        "proposed_kernel_abi_extension": list(abi) if isinstance(abi, list) else [],
    }


def build_authoritative_dynamic_mask_contract(
    *,
    dynamic_contract: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    """Describe the authority gate after the observation-only predicate ABI."""
    dynamic_validation = validate_dynamic_cold_partition_predicate_contract(
        dynamic_contract
    )
    if not dynamic_validation["valid"]:
        raise ValueError("; ".join(dynamic_validation["errors"]))
    if observation.get("requested") is not True:
        raise ValueError("observation must be requested")
    observation_only = observation.get("observation_only")
    active_mask_authority = observation.get("active_mask_authority")
    if (observation_only, active_mask_authority) not in {
        (True, False),
        (False, True),
    }:
        raise ValueError("observation must be observation-only or active-mask-authoritative")
    record_count = observation.get("record_count")
    device_record_count = observation.get("device_record_count")
    parse_error_count = observation.get("parse_error_count")
    if not isinstance(record_count, int) or record_count <= 0:
        raise ValueError("observation record_count must be positive")
    if device_record_count != record_count:
        raise ValueError("observation device_record_count must match record_count")
    if parse_error_count != 0:
        raise ValueError("observation parse_error_count must be zero")

    required_authority_inputs = [
        "stable_eval_hot_path_partition_ids",
        "per_phase_per_state_partition_active_mask",
        "direct_eval_callee_predicate_pointer_abi",
    ]
    return {
        "planner": "gategpt_schedule_planner.build_authoritative_dynamic_mask_contract",
        "status": "ready_for_authoritative_dynamic_mask_design",
        "contract": "connect_observation_only_eval_partition_predicates_to_authoritative_dynamic_mask",
        "base_contract": dynamic_contract["contract"],
        "observation_record_count": record_count,
        "observation_device_record_count": device_record_count,
        "observation_parse_error_count": parse_error_count,
        "observation_active_mask_authority": bool(active_mask_authority),
        "required_authority_inputs": required_authority_inputs,
        "required_runtime_checks": [
            "partition_ids_cover_all_active_block_gate_sites",
            "active_mask_records_match_phase_state_partition_domain",
            "direct_eval_callees_receive_predicate_pointer_without_skipping",
            "cpu_token_oracle_16_state_comparison_remains_passed",
        ],
        "allowed_next_execution_authority": "predicate_read_observation_only_no_skip",
        "forbidden_until_validated": [
            "guard_eval_partitions",
            "skip_cold_partitions",
            "claim_speedup",
            "claim_usefulness",
        ],
        "speedup_claimed": False,
        "usefulness_claimed": False,
    }


def validate_authoritative_dynamic_mask_contract(
    contract: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if contract.get("status") != "ready_for_authoritative_dynamic_mask_design":
        errors.append("status must be ready_for_authoritative_dynamic_mask_design")
    if (
        contract.get("contract")
        != "connect_observation_only_eval_partition_predicates_to_authoritative_dynamic_mask"
    ):
        errors.append("contract must be connect_observation_only_eval_partition_predicates_to_authoritative_dynamic_mask")
    if contract.get("base_contract") != "derive_dynamic_cold_partition_predicate_after_skip_safety_classification":
        errors.append("base_contract must be derive_dynamic_cold_partition_predicate_after_skip_safety_classification")
    if not isinstance(contract.get("observation_active_mask_authority"), bool):
        errors.append("observation_active_mask_authority must be a bool")
    if contract.get("speedup_claimed") is not False:
        errors.append("speedup_claimed must be false")
    if contract.get("usefulness_claimed") is not False:
        errors.append("usefulness_claimed must be false")
    record_count = contract.get("observation_record_count")
    device_count = contract.get("observation_device_record_count")
    if not isinstance(record_count, int) or record_count <= 0:
        errors.append("observation_record_count must be positive")
    if device_count != record_count:
        errors.append("observation_device_record_count must match observation_record_count")
    if contract.get("observation_parse_error_count") != 0:
        errors.append("observation_parse_error_count must be zero")
    required = {
        "stable_eval_hot_path_partition_ids",
        "per_phase_per_state_partition_active_mask",
        "direct_eval_callee_predicate_pointer_abi",
    }
    inputs = contract.get("required_authority_inputs")
    if not isinstance(inputs, list) or set(inputs) != required:
        errors.append("required_authority_inputs must identify stable ids, active mask, and direct eval predicate pointer ABI")
    if contract.get("allowed_next_execution_authority") != "predicate_read_observation_only_no_skip":
        errors.append("allowed_next_execution_authority must remain predicate_read_observation_only_no_skip")
    forbidden = contract.get("forbidden_until_validated")
    if not isinstance(forbidden, list) or "skip_cold_partitions" not in forbidden:
        errors.append("forbidden_until_validated must include skip_cold_partitions")
    return {
        "status": "valid" if not errors else "invalid",
        "valid": not errors,
        "errors": errors,
        "contract": contract.get("contract"),
        "required_authority_inputs": list(inputs) if isinstance(inputs, list) else [],
    }


def build_authoritative_dynamic_mask_readiness(
    *,
    authoritative_contract: dict[str, Any],
    stable_partition_id_map_present: bool,
    per_phase_per_state_active_mask_authoritative: bool,
    direct_eval_predicate_pointer_abi_present: bool,
) -> dict[str, Any]:
    """Classify what still blocks authoritative dynamic-mask execution.

    This is deliberately stricter than the observation-only ABI: a parsed
    predicate table proves plumbing, but it does not prove that eval callees can
    consume an authoritative mask or that any partition may be skipped.
    """
    validation = validate_authoritative_dynamic_mask_contract(
        authoritative_contract
    )
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))

    input_status = [
        {
            "input": "stable_eval_hot_path_partition_ids",
            "status": "present" if stable_partition_id_map_present else "missing",
            "required_evidence": "stable partition id map covers eval hot-path active-block gate sites",
        },
        {
            "input": "per_phase_per_state_partition_active_mask",
            "status": (
                "authoritative"
                if per_phase_per_state_active_mask_authoritative
                else "observation_only_or_missing"
            ),
            "required_evidence": "phase/state/partition mask is authoritative and record domain matches partition ids",
        },
        {
            "input": "direct_eval_callee_predicate_pointer_abi",
            "status": "present" if direct_eval_predicate_pointer_abi_present else "missing",
            "required_evidence": "direct eval callees receive a predicate pointer without changing skip control flow",
        },
    ]
    missing_inputs = [
        item["input"]
        for item in input_status
        if item["status"] not in {"present", "authoritative"}
    ]
    return {
        "planner": "gategpt_schedule_planner.build_authoritative_dynamic_mask_readiness",
        "status": (
            "ready_for_predicate_read_no_skip_validation"
            if not missing_inputs
            else "blocked_before_authoritative_mask_execution"
        ),
        "contract": authoritative_contract["contract"],
        "input_status": input_status,
        "missing_authority_inputs": missing_inputs,
        "next_missing_input": missing_inputs[0] if missing_inputs else None,
        "recommended_implementation_order": [
            "assign_stable_eval_hot_path_partition_ids",
            "materialize_per_phase_per_state_partition_active_mask",
            "thread_predicate_pointer_to_direct_eval_callees",
            "validate_predicate_read_no_skip_against_cpu_token_oracle",
            "only_then_try_guarded_cold_partition_skip",
        ],
        "allowed_next_execution_authority": (
            authoritative_contract["allowed_next_execution_authority"]
        ),
        "skip_authority_granted": False,
        "speedup_claimed": False,
        "usefulness_claimed": False,
    }


def validate_authoritative_dynamic_mask_readiness(
    readiness: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if readiness.get("contract") != "connect_observation_only_eval_partition_predicates_to_authoritative_dynamic_mask":
        errors.append("contract must be connect_observation_only_eval_partition_predicates_to_authoritative_dynamic_mask")
    if readiness.get("allowed_next_execution_authority") != "predicate_read_observation_only_no_skip":
        errors.append("allowed_next_execution_authority must remain predicate_read_observation_only_no_skip")
    if readiness.get("skip_authority_granted") is not False:
        errors.append("skip_authority_granted must be false")
    if readiness.get("speedup_claimed") is not False:
        errors.append("speedup_claimed must be false")
    if readiness.get("usefulness_claimed") is not False:
        errors.append("usefulness_claimed must be false")

    input_status = readiness.get("input_status")
    required_inputs = {
        "stable_eval_hot_path_partition_ids",
        "per_phase_per_state_partition_active_mask",
        "direct_eval_callee_predicate_pointer_abi",
    }
    if not isinstance(input_status, list):
        errors.append("input_status must be a list")
        observed_inputs: set[str] = set()
    else:
        observed_inputs = {
            item.get("input")
            for item in input_status
            if isinstance(item, dict)
        }
        if observed_inputs != required_inputs:
            errors.append("input_status must cover all authority inputs")

    missing = readiness.get("missing_authority_inputs")
    if not isinstance(missing, list):
        errors.append("missing_authority_inputs must be a list")
        missing_set: set[str] = set()
    else:
        missing_set = set(missing)
        if not missing_set.issubset(required_inputs):
            errors.append("missing_authority_inputs contains unknown inputs")

    status = readiness.get("status")
    if missing_set:
        if status != "blocked_before_authoritative_mask_execution":
            errors.append("status must be blocked_before_authoritative_mask_execution while inputs are missing")
        if readiness.get("next_missing_input") not in missing_set:
            errors.append("next_missing_input must name one missing authority input")
    else:
        if status != "ready_for_predicate_read_no_skip_validation":
            errors.append("status must be ready_for_predicate_read_no_skip_validation when no inputs are missing")
        if readiness.get("next_missing_input") is not None:
            errors.append("next_missing_input must be null when no inputs are missing")

    return {
        "status": "valid" if not errors else "invalid",
        "valid": not errors,
        "errors": errors,
        "missing_authority_inputs": list(missing) if isinstance(missing, list) else [],
        "next_missing_input": readiness.get("next_missing_input"),
    }


def build_schedule_lowered_run_vl_hybrid_args(
    *,
    plan: dict[str, Any],
    mdir: str,
    nstates: int,
    steps: int,
    patch_script: str,
    dump_state: str,
    persistent_handle: str,
    phase_dumps: list[str],
    feedback_edges: str,
    feedback_increments: str,
    feedback_phase_sets: str,
    schedule_lowering_plan: str,
    feedback_edge_mode: str = "phase",
) -> list[str]:
    """Build run_vl_hybrid args for a validated schedule-lowered run."""
    schedule_shape = plan.get("schedule_shape")
    if schedule_shape == ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        validation = validate_ordering_aware_phase_resident_token_loop_lowering_plan(plan)
    else:
        validation = validate_padded_start_lowering_plan(plan)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    if nstates != plan.get("nstates"):
        raise ValueError("nstates must match the lowering plan")
    phase_count = plan.get("phase_count")
    if len(phase_dumps) != phase_count:
        raise ValueError("phase dump count must match the lowering plan phase_count")
    if steps < 1:
        raise ValueError("steps must be positive")
    required_text = {
        "mdir": mdir,
        "patch_script": patch_script,
        "dump_state": dump_state,
        "persistent_handle": persistent_handle,
        "feedback_edges": feedback_edges,
        "feedback_increments": feedback_increments,
        "feedback_phase_sets": feedback_phase_sets,
        "schedule_lowering_plan": schedule_lowering_plan,
    }
    missing = [name for name, value in required_text.items() if not value]
    if missing:
        raise ValueError(f"missing required schedule argument(s): {', '.join(missing)}")

    args = [
        "--mdir",
        mdir,
        "--nstates",
        str(nstates),
        "--steps",
        str(steps),
        "--patch-script",
        patch_script,
        "--dump-state",
        dump_state,
        "--resident-steps",
        "--persistent-resident-state-abi-handle",
        persistent_handle,
        "--persistent-resident-state-abi-phase",
        "1",
        "--persistent-resident-state-abi-phases",
        str(phase_count),
        "--persistent-resident-state-abi-phase-dumps",
        ",".join(phase_dumps),
        "--feedback-edges",
        feedback_edges,
        "--feedback-increments",
        feedback_increments,
        "--feedback-phase-sets",
        feedback_phase_sets,
        "--feedback-edge-mode",
        feedback_edge_mode,
        "--schedule-lowering-plan",
        schedule_lowering_plan,
    ]
    if schedule_shape == ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        args.append("--allow-ordering-aware-token-loop-probe-plan")
    return args


def write_lowering_plan_artifact(path: Path, plan: dict[str, Any]) -> None:
    if plan.get("schedule_shape") == ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        validation = validate_ordering_aware_phase_resident_token_loop_lowering_plan(plan)
    else:
        validation = validate_padded_start_lowering_plan(plan)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_lowering_plan_artifact(path: Path) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise ValueError("lowering plan artifact must contain a JSON object")
    if plan.get("schedule_shape") == ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        validation = validate_ordering_aware_phase_resident_token_loop_lowering_plan(plan)
    else:
        validation = validate_padded_start_lowering_plan(plan)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    return plan
