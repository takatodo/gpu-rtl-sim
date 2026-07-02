from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from gategpt_schedule_planner import (
    ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP,
    validate_ordering_aware_phase_resident_token_loop_lowering_plan,
    validate_padded_start_lowering_plan,
)
from run_vl_hybrid_persistent_env import configure_persistent_resident_env
from run_vl_hybrid_state_sanitize import _prepare_sanitized_init_state
from results_reproduction_io import sanitize_local_absolute_paths


_CUBIN_CHAIN_ENV = "RUN_VL_HYBRID_CUBINS"
_RESIDENT_STEPS_ENV = "RUN_VL_HYBRID_RESIDENT_STEPS"
_GPU_REPLICATE_INIT_STATE_ENV = "RUN_VL_HYBRID_GPU_REPLICATE_INIT_STATE"
_TIMING_REPEATS_ENV = "RUN_VL_HYBRID_TIMING_REPEATS"
_PATCH_SCRIPT_ENV = "RUN_VL_HYBRID_PATCH_SCRIPT"
_FEEDBACK_EDGES_ENV = "RUN_VL_HYBRID_FEEDBACK_EDGES"
_FEEDBACK_EDGE_MODE_ENV = "RUN_VL_HYBRID_FEEDBACK_EDGE_MODE"
_FEEDBACK_INCREMENTS_ENV = "RUN_VL_HYBRID_FEEDBACK_INCREMENTS"
_FEEDBACK_PHASE_SETS_ENV = "RUN_VL_HYBRID_FEEDBACK_PHASE_SETS"
_SCHEDULE_LOWERING_PLAN_ENV = "RUN_VL_HYBRID_SCHEDULE_LOWERING_PLAN"
_SCHEDULE_LOWERING_SHAPE_ENV = "RUN_VL_HYBRID_SCHEDULE_LOWERING_SHAPE"
_ORDERING_AWARE_PROBE_PLAN_ENV = "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_PROBE_PLAN_ONLY"
_MODULE_LOAD_SYMBOL_CHECK_ENV = "RUN_VL_HYBRID_MODULE_LOAD_SYMBOL_CHECK"


def _parse_kernel_list(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    items = [part.strip() for part in raw.split(",")]
    return [item for item in items if item]


def configure_kernel_env(
    env: dict[str, str],
    args: argparse.Namespace,
    resolution: Any,
) -> None:
    kernel_override = _parse_kernel_list(args.kernels)
    if kernel_override is not None:
        env["RUN_VL_HYBRID_KERNELS"] = ",".join(kernel_override)
    elif resolution.launch_sequence:
        env["RUN_VL_HYBRID_KERNELS"] = ",".join(str(x) for x in resolution.launch_sequence)
    else:
        env.pop("RUN_VL_HYBRID_KERNELS", None)
    if len(resolution.cubin_paths) > 1:
        env[_CUBIN_CHAIN_ENV] = ",".join(str(path) for path in resolution.cubin_paths)
    else:
        env.pop(_CUBIN_CHAIN_ENV, None)


def configure_module_load_symbol_check_env(
    env: dict[str, str],
    args: argparse.Namespace,
) -> None:
    symbol = getattr(args, "module_load_symbol_check", None)
    if symbol:
        env[_MODULE_LOAD_SYMBOL_CHECK_ENV] = str(symbol)
    else:
        env.pop(_MODULE_LOAD_SYMBOL_CHECK_ENV, None)


def configure_state_io_env(
    env: dict[str, str],
    args: argparse.Namespace,
) -> None:
    if args.dump_state:
        dump_state = args.dump_state.resolve()
        dump_state.parent.mkdir(parents=True, exist_ok=True)
        env["RUN_VL_HYBRID_DUMP_STATE"] = str(dump_state)
    else:
        env.pop("RUN_VL_HYBRID_DUMP_STATE", None)
    if args.patch_script:
        patch_script = args.patch_script.resolve()
        if not patch_script.is_file():
            print(f"error: patch script not found: {patch_script}", file=sys.stderr)
            sys.exit(1)
        env[_PATCH_SCRIPT_ENV] = str(patch_script)
    else:
        env.pop(_PATCH_SCRIPT_ENV, None)
    if args.trace_stages:
        env["RUN_VL_HYBRID_TRACE_STAGES"] = "1"
    else:
        env.pop("RUN_VL_HYBRID_TRACE_STAGES", None)


def configure_runtime_mode_env(
    env: dict[str, str],
    args: argparse.Namespace,
) -> None:
    if args.resident_steps:
        env[_RESIDENT_STEPS_ENV] = "1"
    else:
        env.pop(_RESIDENT_STEPS_ENV, None)
    if args.gpu_replicate_init_state:
        env[_GPU_REPLICATE_INIT_STATE_ENV] = "1"
    else:
        env.pop(_GPU_REPLICATE_INIT_STATE_ENV, None)
    if args.timing_repeats > 1:
        env[_TIMING_REPEATS_ENV] = str(args.timing_repeats)
    else:
        env.pop(_TIMING_REPEATS_ENV, None)
    feedback_edges = getattr(args, "feedback_edges", None)
    feedback_edge_mode = getattr(args, "feedback_edge_mode", None)
    if feedback_edges:
        env[_FEEDBACK_EDGES_ENV] = feedback_edges
    else:
        env.pop(_FEEDBACK_EDGES_ENV, None)
    feedback_increments = getattr(args, "feedback_increments", None)
    if feedback_increments:
        env[_FEEDBACK_INCREMENTS_ENV] = feedback_increments
    else:
        env.pop(_FEEDBACK_INCREMENTS_ENV, None)
    feedback_phase_sets = getattr(args, "feedback_phase_sets", None)
    if feedback_phase_sets:
        env[_FEEDBACK_PHASE_SETS_ENV] = feedback_phase_sets
    else:
        env.pop(_FEEDBACK_PHASE_SETS_ENV, None)
    if feedback_edge_mode:
        env[_FEEDBACK_EDGE_MODE_ENV] = feedback_edge_mode
    else:
        env.pop(_FEEDBACK_EDGE_MODE_ENV, None)


def configure_schedule_lowering_plan_env(
    env: dict[str, str],
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    plan_path = getattr(args, "schedule_lowering_plan", None)
    if not plan_path:
        env.pop(_SCHEDULE_LOWERING_PLAN_ENV, None)
        env.pop(_SCHEDULE_LOWERING_SHAPE_ENV, None)
        env.pop(_ORDERING_AWARE_PROBE_PLAN_ENV, None)
        return None

    resolved = Path(plan_path).resolve()
    if not resolved.is_file():
        print(f"error: schedule lowering plan not found: {resolved}", file=sys.stderr)
        sys.exit(1)
    try:
        plan = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: schedule lowering plan is not valid JSON: {resolved}: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(plan, dict):
        print(f"error: schedule lowering plan must be a JSON object: {resolved}", file=sys.stderr)
        sys.exit(1)

    schedule_shape = plan.get("schedule_shape")
    if schedule_shape == "padded_start_pair_cycle_loop":
        validation = validate_padded_start_lowering_plan(plan)
        env.pop(_ORDERING_AWARE_PROBE_PLAN_ENV, None)
    elif schedule_shape == ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP:
        validation = validate_ordering_aware_phase_resident_token_loop_lowering_plan(plan)
        if not validation["valid"]:
            details = "; ".join(str(item) for item in validation["errors"])
            print(f"error: invalid schedule lowering plan: {details}", file=sys.stderr)
            sys.exit(1)
        if not validation.get("runtime_supported", False):
            reason = validation.get("blocking_reason") or validation.get("status")
            print(f"error: unsupported schedule lowering plan: {reason}", file=sys.stderr)
            sys.exit(1)
        if getattr(args, "allow_ordering_aware_token_loop_probe_plan", False):
            env[_ORDERING_AWARE_PROBE_PLAN_ENV] = "1"
        else:
            env.pop(_ORDERING_AWARE_PROBE_PLAN_ENV, None)
    else:
        print(f"error: unsupported schedule lowering shape: {schedule_shape}", file=sys.stderr)
        sys.exit(1)
    if not validation["valid"]:
        details = "; ".join(str(item) for item in validation["errors"])
        print(f"error: invalid schedule lowering plan: {details}", file=sys.stderr)
        sys.exit(1)

    env_overrides = plan.get("env_overrides")
    if not isinstance(env_overrides, dict):
        print("error: schedule lowering plan env_overrides must be a JSON object", file=sys.stderr)
        sys.exit(1)
    for key, value in env_overrides.items():
        if not isinstance(key, str) or not isinstance(value, (str, int, float, bool)):
            print("error: schedule lowering plan env_overrides must be scalar string keys/values", file=sys.stderr)
            sys.exit(1)
        env[key] = str(value)
    env[_SCHEDULE_LOWERING_PLAN_ENV] = str(resolved)
    env[_SCHEDULE_LOWERING_SHAPE_ENV] = str(schedule_shape)
    return validation


def configure_launch_env(
    args: argparse.Namespace,
    resolution: Any,
) -> dict[str, str]:
    env = os.environ.copy()
    configure_kernel_env(env, args, resolution)
    configure_module_load_symbol_check_env(env, args)
    configure_state_io_env(env, args)
    configure_runtime_mode_env(env, args)
    configure_persistent_resident_env(env, args)
    configure_schedule_lowering_plan_env(env, args)
    return env


def prepare_init_state_env(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    resolution: Any,
    env: dict[str, str],
) -> Path | None:
    sanitized_init_tmp: Path | None = None
    if args.init_state:
        init_state = args.init_state.resolve()
        if args.sanitize_host_only_internals:
            if resolution.mdir is None:
                parser.error("--sanitize-host-only-internals requires --mdir")
            sanitized = _prepare_sanitized_init_state(mdir=resolution.mdir, init_state=init_state)
            if sanitized is not None:
                sanitized_init_tmp, applied = sanitized
                init_state = sanitized_init_tmp
                verbose_sanitize = env.get("RUN_VL_HYBRID_VERBOSE_SANITIZE") == "1"
                if verbose_sanitize:
                    details = ", ".join(
                        f"{entry['field_name']}[{entry['sanitized_start']}:{entry['sanitized_end']}]"
                        for entry in applied
                    )
                    message = f"{details} -> {sanitized_init_tmp}"
                else:
                    sanitized_output = sanitize_local_absolute_paths(str(sanitized_init_tmp))
                    message = (
                        f"count={len(applied)} output={sanitized_output} "
                        "(set RUN_VL_HYBRID_VERBOSE_SANITIZE=1 for region details)"
                    )
                print(f"info: sanitized host-only init-state regions: {message}", file=sys.stderr)
        env["RUN_VL_HYBRID_INIT_STATE"] = str(init_state)
    else:
        env.pop("RUN_VL_HYBRID_INIT_STATE", None)
    return sanitized_init_tmp
