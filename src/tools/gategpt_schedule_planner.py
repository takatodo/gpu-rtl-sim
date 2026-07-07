#!/usr/bin/env python3
"""Compatibility wrapper for the frozen gateGPT schedule planner."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gategpt_schedule_lowering_plan import (  # noqa: E402
    ORDERING_AWARE_CHUNKED_CONTINUATION_BLOCKED_STATUS,
    ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES,
    ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP,
    PAIR_CYCLE_LOOP_ENV,
    REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS,
    REQUIRED_PADDED_START_ENTRYPOINTS,
    validate_ordering_aware_phase_resident_token_loop_lowering_plan,
    validate_padded_start_lowering_plan,
)
from src.diagnostics.frozen.gategpt_fc069_073.schedule_planner import (  # noqa: E402
    build_authoritative_dynamic_mask_contract,
    build_authoritative_dynamic_mask_readiness,
    build_dynamic_cold_partition_predicate_contract,
    build_ordering_aware_phase_resident_token_loop_contract,
    build_ordering_aware_phase_resident_token_loop_lowering_plan,
    build_padded_start_pair_cycle_loop_lowering_plan,
    build_phase_set_start_control_patch_lines,
    build_schedule_lowered_run_vl_hybrid_args,
    load_lowering_plan_artifact,
    validate_authoritative_dynamic_mask_contract,
    validate_authoritative_dynamic_mask_readiness,
    validate_dynamic_cold_partition_predicate_contract,
    validate_ordering_aware_phase_resident_token_loop_contract,
    write_lowering_plan_artifact,
)


__all__ = [
    "ORDERING_AWARE_CHUNKED_CONTINUATION_BLOCKED_STATUS",
    "ORDERING_AWARE_FULL_LOGICAL_PHASE_PAIR_CYCLES",
    "ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP",
    "PAIR_CYCLE_LOOP_ENV",
    "REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS",
    "REQUIRED_PADDED_START_ENTRYPOINTS",
    "build_authoritative_dynamic_mask_contract",
    "build_authoritative_dynamic_mask_readiness",
    "build_dynamic_cold_partition_predicate_contract",
    "build_ordering_aware_phase_resident_token_loop_contract",
    "build_ordering_aware_phase_resident_token_loop_lowering_plan",
    "build_padded_start_pair_cycle_loop_lowering_plan",
    "build_phase_set_start_control_patch_lines",
    "build_schedule_lowered_run_vl_hybrid_args",
    "load_lowering_plan_artifact",
    "validate_authoritative_dynamic_mask_contract",
    "validate_authoritative_dynamic_mask_readiness",
    "validate_dynamic_cold_partition_predicate_contract",
    "validate_ordering_aware_phase_resident_token_loop_contract",
    "validate_ordering_aware_phase_resident_token_loop_lowering_plan",
    "validate_padded_start_lowering_plan",
    "write_lowering_plan_artifact",
]
