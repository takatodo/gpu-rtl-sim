from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from run_vl_hybrid_persistent_env import configure_persistent_resident_env
from run_vl_hybrid_state_sanitize import _prepare_sanitized_init_state
from results_reproduction_io import sanitize_local_absolute_paths


_CUBIN_CHAIN_ENV = "RUN_VL_HYBRID_CUBINS"
_RESIDENT_STEPS_ENV = "RUN_VL_HYBRID_RESIDENT_STEPS"
_GPU_REPLICATE_INIT_STATE_ENV = "RUN_VL_HYBRID_GPU_REPLICATE_INIT_STATE"
_TIMING_REPEATS_ENV = "RUN_VL_HYBRID_TIMING_REPEATS"
_PATCH_SCRIPT_ENV = "RUN_VL_HYBRID_PATCH_SCRIPT"


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


def configure_launch_env(
    args: argparse.Namespace,
    resolution: Any,
) -> dict[str, str]:
    env = os.environ.copy()
    configure_kernel_env(env, args, resolution)
    configure_state_io_env(env, args)
    configure_runtime_mode_env(env, args)
    configure_persistent_resident_env(env, args)
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
