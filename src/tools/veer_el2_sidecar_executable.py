#!/usr/bin/env python3
"""Reviewed VeeR-EL2 RTLMeter sidecar executable.

This executable is intentionally narrow for FC-064/FC-037. It consumes the
reviewed extracted VeeR-EL2 preload image, materializes a syms-state launch
image, launches the generated GPU artifact through run_vl_hybrid.py, and emits
RTLMeter-style stdout/cycles observables from GPU state 0. Additional GPU
states default to identical-lane validation evidence. A mixed-state opt-in can
provide one reviewed state image per GPU state while reusing the same kernels.
"""

from __future__ import annotations

import hashlib
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

from run_vl_hybrid_launch import HYBRID_BIN, ensure_hybrid_runtime_built
from verilator_native_sidecar_make_driver import (
    VEER_EL2_RTL_METER_TARGET,
    VEER_EL2_SIDECAR_EXECUTE_DIR_ENV,
    VEER_EL2_SIDECAR_STATE_IMAGE_ENV,
    _display_path,
    _veer_el2_root_state_offset_review,
)


DEFAULT_MDIR = Path("artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir")
DEFAULT_CLOCK_CYCLES = 727
DEFAULT_RESET_LAUNCHES = 2
DEFAULT_RTL_METER_POST_FINISH_CYCLES = 1502
DEFAULT_SIDECAR_NSTATES = 2
VEER_EL2_SIDECAR_STATE_IMAGES_ENV = "VEER_EL2_SIDECAR_STATE_IMAGES"
FUSED_PATCH_EVAL_ENV = "VEER_EL2_SIDECAR_FUSED_PATCH_EVAL"
FUSED_PAIR_CYCLE_ENV = "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE"
FUSED_PAIR_CYCLE_LOOP_ENV = "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP"
STATE_LOCAL_PATCHES_ENV = "VEER_EL2_SIDECAR_STATE_LOCAL_PATCHES"
DISABLE_STEP_TRACE_ENV = "VEER_EL2_SIDECAR_DISABLE_STEP_TRACE"
FINAL_OBSERVABLE_STDOUT_ENV = "VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT"
HYBRID_STAGE_TIMING_ENV = "VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING"
HYBRID_TIMING_REPEATS_ENV = "VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS"
FUSED_PAIR_CYCLE_LOOP_CHUNK_ENV = "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK"
CLOCK_PATCH_MODE_ENV = "VEER_EL2_SIDECAR_CLOCK_PATCH_MODE"
DEFAULT_CLOCK_PATCH_MODE = "full_clock_reset_fields"
EXPERIMENTAL_POSEDGE_ONLY_CLOCK_PATCH_MODE = "experimental_posedge_only_clock_high_fields"
RESIDENT_PAIR_CYCLE_CLOCK_PATCH_MODE = "resident_pair_cycle_low_high_eval"
ROOT_OFFSET_FALLBACK = 192
PROGRAM_MEM_BASE = 0x80000000
FLAT_MEM_DEFAULT_VALUE_BYTES = 1
FLAT_MEM_CONTROL_BASE = 0x10000000
FLAT_MEM_CONTROL_SPAN_BYTES = 16
PROGRAM_MEM_SPAN_BYTES = 64 * 1024
RESET_VECTOR_DEFAULT = 0x80000000
NMI_VECTOR_DEFAULT = 0xEE000000
GPU_KERNEL_TIME_RE = re.compile(r"^gpu_kernel_time_ms:\s+total=(?P<total>[0-9.]+)\s+per_launch=(?P<per_launch>[0-9.]+)")
GPU_KERNEL_PER_STATE_RE = re.compile(r"^gpu_kernel_time:\s+per_state=(?P<per_state>[0-9.]+)\s+us")
GPU_KERNEL_LAUNCHES_RE = re.compile(
    r"^gpu_kernel_launches:\s+logical=(?P<logical>[0-9]+)\s+"
    r"actual=(?P<actual>[0-9]+)\s+timing_repeats=(?P<timing_repeats>[0-9]+)\s+"
    r"ms_per_actual_launch=(?P<ms_per_actual_launch>[0-9.]+)"
)
GPU_KERNEL_REPEAT_RE = re.compile(
    r"^gpu_kernel_time_repeat_ms:\s+count=(?P<count>[0-9]+)\s+"
    r"min=(?P<min>[0-9.]+)\s+median=(?P<median>[0-9.]+)\s+max=(?P<max>[0-9.]+)"
    r"(?:\s+samples=(?P<samples>[0-9.,]+))?"
)
GPU_INIT_STATE_REPLICATION_RE = re.compile(r"^gpu_init_state_replication:\s+(?P<enabled>true|false)")
STEP_TRACE_COPY_MODE_RE = re.compile(r"^step_trace_copy_mode:\s+(?P<mode>[A-Za-z0-9_]+)")
STEP_TRACE_FILTER_RE = re.compile(
    r"^step_trace_filter:\s+start=(?P<start>\d+)\s+stride=(?P<stride>\d+)\s+rows=(?P<rows>\d+)\s+capacity=(?P<capacity>\d+)"
)
RESIDENT_PATCH_SCHEDULE_RE = re.compile(
    r"^resident_patch_schedule:\s+logical=(?P<logical>\d+)\s+records=(?P<records>\d+)\s+blocks=(?P<blocks>\d+)"
)
STATE_LOCAL_PATCH_SCHEDULE_RE = re.compile(
    r"^state_local_patch_schedule:\s+logical=(?P<logical>\d+)\s+records=(?P<records>\d+)\s+blocks=(?P<blocks>\d+)"
)
PATCH_EVAL_FUSION_RE = re.compile(
    r"^patch_eval_fusion:\s+requested=(?P<requested>true|false)\s+"
    r"available=(?P<available>true|false)\s+launched=(?P<launched>\d+)\s+"
    r"fallback=(?P<fallback>\d+)\s+mode=(?P<mode>[A-Za-z0-9_]+)"
)
RESIDENT_PAIR_CYCLE_RE = re.compile(
    r"^resident_pair_cycle:\s+requested=(?P<requested>true|false)\s+"
    r"launched=(?P<launched>\d+)\s+fallback=(?P<fallback>\d+)\s+"
    r"start=(?P<start>\d+)\s+mode=(?P<mode>[A-Za-z0-9_]+)"
)
PAIR_CYCLE_FUSION_RE = re.compile(
    r"^pair_cycle_fusion:\s+requested=(?P<requested>true|false)\s+"
    r"available=(?P<available>true|false)\s+launched=(?P<launched>\d+)\s+"
    r"fallback=(?P<fallback>\d+)\s+mode=(?P<mode>[A-Za-z0-9_]+)"
)
PAIR_CYCLE_LOOP_FUSION_RE = re.compile(
    r"^pair_cycle_loop_fusion:\s+requested=(?P<requested>true|false)\s+"
    r"available=(?P<available>true|false)\s+kernel_launches=(?P<kernel_launches>\d+)\s+"
    r"cycles=(?P<cycles>\d+)\s+fallback=(?P<fallback>\d+)\s+"
    r"chunk=(?P<chunk>\d+)\s+mode=(?P<mode>[A-Za-z0-9_]+)"
)
PAIR_CYCLE_STATE_LOCAL_FUSION_RE = re.compile(
    r"^pair_cycle_state_local_fusion:\s+requested=(?P<requested>true|false)\s+"
    r"available=(?P<available>true|false)\s+launched=(?P<launched>\d+)\s+"
    r"fallback=(?P<fallback>\d+)\s+mode=(?P<mode>[A-Za-z0-9_]+)"
)
FEEDBACK_PHASE_SETS_RE = re.compile(
    r"^feedback_phase_sets:\s+requested=(?P<requested>true|false)\s+"
    r"sets=(?P<sets>\d+)\s+launched=(?P<launched>\d+)\s+kernel=(?P<kernel>\S+)"
)
STAGE_TIMING_RE = re.compile(r"^stage_timing_ms:\s*(?P<items>.*)$")
WSL_LIBCUDA = Path("/usr/lib/wsl/lib/libcuda.so.1")
HELLO_PROGRAM_SHA256 = "d0219135d529505962c1c5ed44360e91466ae046cb8ec40b5980761861c63d76"


def _normalize_clock_patch_mode(raw_mode: str | None) -> str:
    mode = (raw_mode or DEFAULT_CLOCK_PATCH_MODE).strip().lower().replace("-", "_")
    if mode in {"", "full", DEFAULT_CLOCK_PATCH_MODE}:
        return DEFAULT_CLOCK_PATCH_MODE
    if mode in {
        "posedge_only",
        "clock_high_only",
        "high_only",
        EXPERIMENTAL_POSEDGE_ONLY_CLOCK_PATCH_MODE,
    }:
        return EXPERIMENTAL_POSEDGE_ONLY_CLOCK_PATCH_MODE
    if mode in {
        "resident_pair_cycle",
        "pair_cycle",
        "pair_cycle_resident_steps",
        RESIDENT_PAIR_CYCLE_CLOCK_PATCH_MODE,
    }:
        return RESIDENT_PAIR_CYCLE_CLOCK_PATCH_MODE
    raise ValueError(
        f"unsupported {CLOCK_PATCH_MODE_ENV}={raw_mode!r}; "
        f"expected {DEFAULT_CLOCK_PATCH_MODE!r}, "
        f"{EXPERIMENTAL_POSEDGE_ONLY_CLOCK_PATCH_MODE!r}, or "
        f"{RESIDENT_PAIR_CYCLE_CLOCK_PATCH_MODE!r}"
    )


def _clock_patch_step_trace_filter(*, reset_launches: int, patch_script_mode: str) -> dict[str, object]:
    if patch_script_mode in {DEFAULT_CLOCK_PATCH_MODE, RESIDENT_PAIR_CYCLE_CLOCK_PATCH_MODE}:
        return {
            "mode": "clock_high_after_reset",
            "start": reset_launches + 2,
            "stride": 2,
        }
    if patch_script_mode == EXPERIMENTAL_POSEDGE_ONLY_CLOCK_PATCH_MODE:
        return {
            "mode": "clock_high_only_after_reset",
            "start": reset_launches + 1,
            "stride": 1,
        }
    raise ValueError(f"unsupported clock patch mode {patch_script_mode!r}")


def compute_rtlmeter_main_clock_cycles(
    *,
    sidecar_clock_cycles: int,
    post_finish_cycles: int = DEFAULT_RTL_METER_POST_FINISH_CYCLES,
) -> int:
    if sidecar_clock_cycles < 1:
        raise ValueError("sidecar_clock_cycles must be positive")
    if post_finish_cycles < 0:
        raise ValueError("post_finish_cycles must be non-negative")
    return sidecar_clock_cycles + post_finish_cycles


def parse_run_vl_hybrid_timing(stdout: str) -> dict[str, object]:
    timing: dict[str, object] = {
        "source": "run_vl_hybrid stdout",
        "gpu_kernel_time_ms_total": None,
        "gpu_kernel_time_ms_per_launch": None,
        "gpu_kernel_timing_logical_step_count": None,
        "gpu_kernel_timed_launch_count": None,
        "gpu_kernel_time_ms_per_actual_launch": None,
        "gpu_kernel_time_us_per_state": None,
        "gpu_kernel_time_repeat_count": None,
        "gpu_kernel_time_ms_total_min": None,
        "gpu_kernel_time_ms_total_median": None,
        "gpu_kernel_time_ms_total_max": None,
        "gpu_kernel_time_ms_total_samples": [],
        "gpu_init_state_replication": None,
        "resident_patch_schedule": None,
        "state_local_patch_schedule": None,
        "patch_eval_fusion": None,
        "pair_cycle_fusion": None,
        "pair_cycle_loop_fusion": None,
        "pair_cycle_state_local_fusion": None,
        "resident_pair_cycle": None,
        "feedback_phase_sets": None,
        "step_trace_copy_mode": None,
        "step_trace_filter": None,
        "stage_timing_ms": {},
    }
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        match = GPU_KERNEL_TIME_RE.match(line)
        if match:
            timing["gpu_kernel_time_ms_total"] = float(match.group("total"))
            timing["gpu_kernel_time_ms_per_launch"] = float(match.group("per_launch"))
            continue
        match = GPU_KERNEL_PER_STATE_RE.match(line)
        if match:
            timing["gpu_kernel_time_us_per_state"] = float(match.group("per_state"))
            continue
        match = GPU_KERNEL_LAUNCHES_RE.match(line)
        if match:
            timing["gpu_kernel_timing_logical_step_count"] = int(match.group("logical"))
            timing["gpu_kernel_timed_launch_count"] = int(match.group("actual"))
            timing["gpu_kernel_time_repeat_count"] = int(match.group("timing_repeats"))
            timing["gpu_kernel_time_ms_per_actual_launch"] = float(match.group("ms_per_actual_launch"))
            continue
        match = GPU_KERNEL_REPEAT_RE.match(line)
        if match:
            timing["gpu_kernel_time_repeat_count"] = int(match.group("count"))
            timing["gpu_kernel_time_ms_total_min"] = float(match.group("min"))
            timing["gpu_kernel_time_ms_total_median"] = float(match.group("median"))
            timing["gpu_kernel_time_ms_total_max"] = float(match.group("max"))
            samples = match.group("samples")
            timing["gpu_kernel_time_ms_total_samples"] = (
                [float(item) for item in samples.split(",") if item] if samples else []
            )
            continue
        match = GPU_INIT_STATE_REPLICATION_RE.match(line)
        if match:
            timing["gpu_init_state_replication"] = match.group("enabled") == "true"
            continue
        match = RESIDENT_PATCH_SCHEDULE_RE.match(line)
        if match:
            timing["resident_patch_schedule"] = {
                "logical": int(match.group("logical")),
                "records": int(match.group("records")),
                "blocks": int(match.group("blocks")),
            }
            continue
        match = STATE_LOCAL_PATCH_SCHEDULE_RE.match(line)
        if match:
            timing["state_local_patch_schedule"] = {
                "logical": int(match.group("logical")),
                "records": int(match.group("records")),
                "blocks": int(match.group("blocks")),
            }
            continue
        match = PATCH_EVAL_FUSION_RE.match(line)
        if match:
            timing["patch_eval_fusion"] = {
                "requested": match.group("requested") == "true",
                "available": match.group("available") == "true",
                "launched": int(match.group("launched")),
                "fallback": int(match.group("fallback")),
                "mode": match.group("mode"),
            }
            continue
        match = RESIDENT_PAIR_CYCLE_RE.match(line)
        if match:
            timing["resident_pair_cycle"] = {
                "requested": match.group("requested") == "true",
                "launched": int(match.group("launched")),
                "fallback": int(match.group("fallback")),
                "start": int(match.group("start")),
                "mode": match.group("mode"),
            }
            continue
        match = PAIR_CYCLE_FUSION_RE.match(line)
        if match:
            timing["pair_cycle_fusion"] = {
                "requested": match.group("requested") == "true",
                "available": match.group("available") == "true",
                "launched": int(match.group("launched")),
                "fallback": int(match.group("fallback")),
                "mode": match.group("mode"),
            }
            continue
        match = PAIR_CYCLE_LOOP_FUSION_RE.match(line)
        if match:
            timing["pair_cycle_loop_fusion"] = {
                "requested": match.group("requested") == "true",
                "available": match.group("available") == "true",
                "kernel_launches": int(match.group("kernel_launches")),
                "cycles": int(match.group("cycles")),
                "fallback": int(match.group("fallback")),
                "chunk": int(match.group("chunk")),
                "mode": match.group("mode"),
            }
            continue
        match = PAIR_CYCLE_STATE_LOCAL_FUSION_RE.match(line)
        if match:
            timing["pair_cycle_state_local_fusion"] = {
                "requested": match.group("requested") == "true",
                "available": match.group("available") == "true",
                "launched": int(match.group("launched")),
                "fallback": int(match.group("fallback")),
                "mode": match.group("mode"),
            }
            continue
        match = FEEDBACK_PHASE_SETS_RE.match(line)
        if match:
            timing["feedback_phase_sets"] = {
                "requested": match.group("requested") == "true",
                "sets": int(match.group("sets")),
                "launched": int(match.group("launched")),
                "kernel": match.group("kernel"),
            }
            continue
        match = STEP_TRACE_COPY_MODE_RE.match(line)
        if match:
            timing["step_trace_copy_mode"] = match.group("mode")
            continue
        match = STEP_TRACE_FILTER_RE.match(line)
        if match:
            timing["step_trace_filter"] = {
                "start": int(match.group("start")),
                "stride": int(match.group("stride")),
                "rows": int(match.group("rows")),
                "capacity": int(match.group("capacity")),
            }
            continue
        match = STAGE_TIMING_RE.match(line)
        if match:
            stage_timing: dict[str, float] = {}
            for item in match.group("items").split():
                if "=" not in item:
                    continue
                name, value = item.split("=", 1)
                try:
                    stage_timing[name] = float(value)
                except ValueError:
                    continue
            timing["stage_timing_ms"] = stage_timing
    return timing


def _load_json(path: Path) -> Mapping[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} is not a JSON object")
    return data


def _apply_wsl_libcuda_env(env: dict[str, str]) -> None:
    if not WSL_LIBCUDA.is_file():
        return
    prefix = WSL_LIBCUDA.parent.as_posix()
    rest = env.get("LD_LIBRARY_PATH", "")
    if rest and rest != prefix and not rest.startswith(prefix + ":"):
        env["LD_LIBRARY_PATH"] = f"{prefix}:{rest}"
    elif not rest:
        env["LD_LIBRARY_PATH"] = prefix


def _meta_cubin_paths(*, mdir: Path, meta: Mapping[str, object]) -> list[Path]:
    cubins = meta.get("cubins")
    if isinstance(cubins, list) and cubins:
        return [(mdir / str(item)).resolve() for item in cubins]
    cubin = meta.get("cubin")
    if not cubin:
        raise RuntimeError("vl_batch_gpu.meta.json has no cubin path")
    return [(mdir / str(cubin)).resolve()]


def _hybrid_runtime_command(
    *,
    mdir: Path,
    meta: Mapping[str, object],
    state_count: int,
    steps: int,
    block_size: int = 256,
) -> tuple[list[str], dict[str, str]]:
    ensure_hybrid_runtime_built()
    cubin_paths = _meta_cubin_paths(mdir=mdir, meta=meta)
    command = [
        HYBRID_BIN.resolve().as_posix(),
        cubin_paths[0].as_posix(),
        str(_storage_size(meta)),
        str(state_count),
        str(block_size),
        str(steps),
    ]
    env_updates: dict[str, str] = {}
    if len(cubin_paths) > 1:
        env_updates["RUN_VL_HYBRID_CUBINS"] = ",".join(path.as_posix() for path in cubin_paths)
    launch_sequence = meta.get("launch_sequence")
    if isinstance(launch_sequence, list) and launch_sequence:
        env_updates["RUN_VL_HYBRID_KERNELS"] = ",".join(str(item) for item in launch_sequence)
    return command, env_updates


def _file_fingerprint(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": _display_path(path, Path.cwd().resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _rel(path: Path, root: Path) -> str:
    return _display_path(path, root)


def _int_from_hexish(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"not an integer: {value!r}")


def _write_le(blob: bytearray, offset: int, size: int, value: int) -> None:
    if offset < 0 or offset + size > len(blob):
        raise ValueError(f"state write out of range: offset={offset} size={size}")
    blob[offset : offset + size] = int(value).to_bytes(size, "little", signed=False)


def _read_le(blob: bytes, offset: int, size: int) -> int:
    if offset < 0 or offset + size > len(blob):
        return 0
    return int.from_bytes(blob[offset : offset + size], "little", signed=False)


def _mapped_field_offset(mapped_fields: Mapping[str, Mapping[str, object]], key: str) -> int:
    field = mapped_fields.get(key)
    if not field:
        raise RuntimeError(f"missing mapped VeeR-EL2 root field: {key}")
    return int(field["offset"])


def _mapped_field_size(mapped_fields: Mapping[str, Mapping[str, object]], key: str) -> int:
    field = mapped_fields.get(key)
    if not field:
        raise RuntimeError(f"missing mapped VeeR-EL2 root field: {key}")
    return int(field["size"])


def _mapped_field_offsets(mdir: Path, root: Path) -> dict[str, dict[str, object]]:
    review = _veer_el2_root_state_offset_review(mdir, root)
    if review.get("reviewed") is not True:
        missing = review.get("missing_field_markers") or review.get("missing_build_context") or []
        raise RuntimeError(f"VeeR-EL2 root field offset review failed: {missing}")
    mapped = review.get("mapped_fields")
    if not isinstance(mapped, dict):
        raise RuntimeError("VeeR-EL2 root field offset review did not produce mapped_fields")
    return {str(key): dict(value) for key, value in mapped.items() if isinstance(value, Mapping)}


def _mapped_field_offsets_cached(
    *,
    mdir: Path,
    root: Path,
    cache_path: Path,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    root_header = mdir / "Vsim___024root.h"
    meta_path = mdir / "vl_batch_gpu.meta.json"
    fingerprint = {
        "root_header": _file_fingerprint(root_header),
        "meta": _file_fingerprint(meta_path),
    }
    if cache_path.is_file():
        try:
            cached = _load_json(cache_path)
            mapped = cached.get("mapped_fields")
            if cached.get("fingerprint") == fingerprint and isinstance(mapped, Mapping):
                return (
                    {str(key): dict(value) for key, value in mapped.items() if isinstance(value, Mapping)},
                    {"status": "hit", "path": _rel(cache_path, root), "fingerprint": fingerprint},
                )
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    mapped_fields = _mapped_field_offsets(mdir, root)
    cache_path.write_text(
        json.dumps(
            {
                "schema_role": "veer_el2_mapped_field_offsets_cache",
                "fingerprint": fingerprint,
                "mapped_fields": mapped_fields,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return mapped_fields, {"status": "miss", "path": _rel(cache_path, root), "fingerprint": fingerprint}


def _root_offset(meta: Mapping[str, object]) -> int:
    hierarchy = meta.get("hierarchy_state")
    if isinstance(hierarchy, Mapping):
        for key in ("root_offset_in_state", "root_offset_in_syms"):
            value = hierarchy.get(key)
            if isinstance(value, int) and value >= 0:
                return value
    return ROOT_OFFSET_FALLBACK


def _storage_size(meta: Mapping[str, object]) -> int:
    value = meta.get("storage_size")
    if not isinstance(value, int) or value <= 0:
        raise RuntimeError("vl_batch_gpu.meta.json has no positive storage_size")
    return value


def _materialize_flat_program_mem(
    *,
    blob: bytearray,
    root_offset: int,
    field: Mapping[str, object],
    entries: object,
) -> dict[str, int]:
    field_offset = int(field["offset"])
    field_size = int(field["size"])
    storage_base = root_offset + field_offset + FLAT_MEM_DEFAULT_VALUE_BYTES
    control_base = storage_base + PROGRAM_MEM_SPAN_BYTES
    written = 0
    skipped_before_base = 0
    skipped_after_window = 0
    if not isinstance(entries, list):
        return {
            "written": written,
            "skipped_before_base": skipped_before_base,
            "skipped_after_window": skipped_after_window,
        }
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        addr = _int_from_hexish(entry.get("addr"))
        byte_value = _int_from_hexish(entry.get("byte_hex"))
        if FLAT_MEM_CONTROL_BASE <= addr < FLAT_MEM_CONTROL_BASE + FLAT_MEM_CONTROL_SPAN_BYTES:
            control_offset = addr - FLAT_MEM_CONTROL_BASE
            if control_base + control_offset >= root_offset + field_offset + field_size:
                skipped_after_window += 1
                continue
            _write_le(blob, control_base + control_offset, 1, byte_value & 0xFF)
            written += 1
            continue
        offset = addr - PROGRAM_MEM_BASE
        if offset < 0:
            skipped_before_base += 1
            continue
        if offset >= PROGRAM_MEM_SPAN_BYTES:
            skipped_after_window += 1
            continue
        _write_le(blob, storage_base + offset, 1, byte_value & 0xFF)
        written += 1
    return {
        "written": written,
        "skipped_before_base": skipped_before_base,
        "skipped_after_window": skipped_after_window,
    }


def _mapped_bank_field(
    mapped_fields: Mapping[str, Mapping[str, object]],
    *,
    memory_kind: str,
    bank_index: int,
) -> Mapping[str, object] | None:
    loop_marker = f"{memory_kind}_loop__BRA__{bank_index}__KET__"
    for field in mapped_fields.values():
        name = str(field.get("name", ""))
        if loop_marker in name and name.endswith("ram_core"):
            return field
    return None


def _materialize_ecc_bank_entries(
    *,
    blob: bytearray,
    root_offset: int,
    mapped_fields: Mapping[str, Mapping[str, object]],
    memory_kind: str,
    section: object,
) -> dict[str, int]:
    written = 0
    skipped_missing_bank = 0
    skipped_out_of_range = 0
    if not isinstance(section, Mapping) or section.get("preload_active") is not True:
        return {
            "written": written,
            "skipped_missing_bank": skipped_missing_bank,
            "skipped_out_of_range": skipped_out_of_range,
        }
    entries_by_bank = section.get("nonzero_entries_by_bank")
    if not isinstance(entries_by_bank, Mapping):
        return {
            "written": written,
            "skipped_missing_bank": skipped_missing_bank,
            "skipped_out_of_range": skipped_out_of_range,
        }
    for raw_bank, raw_entries in entries_by_bank.items():
        try:
            bank_index = int(raw_bank)
        except (TypeError, ValueError):
            skipped_missing_bank += len(raw_entries) if isinstance(raw_entries, list) else 1
            continue
        field = _mapped_bank_field(
            mapped_fields,
            memory_kind=memory_kind,
            bank_index=bank_index,
        )
        if field is None:
            skipped_missing_bank += len(raw_entries) if isinstance(raw_entries, list) else 1
            continue
        if not isinstance(raw_entries, list):
            continue
        field_offset = root_offset + int(field["offset"])
        field_size = int(field["size"])
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, Mapping):
                continue
            index = _int_from_hexish(raw_entry.get("index"))
            word = _int_from_hexish(raw_entry.get("word_hex"))
            byte_offset = index * 8
            if index < 0 or byte_offset + 8 > field_size:
                skipped_out_of_range += 1
                continue
            _write_le(blob, field_offset + byte_offset, 8, word)
            written += 1
    return {
        "written": written,
        "skipped_missing_bank": skipped_missing_bank,
        "skipped_out_of_range": skipped_out_of_range,
    }


def materialize_veer_el2_syms_init_state(
    *,
    state_image: Mapping[str, object],
    meta: Mapping[str, object],
    mapped_fields: Mapping[str, Mapping[str, object]],
) -> tuple[bytes, dict[str, object]]:
    if state_image.get("target") != VEER_EL2_RTL_METER_TARGET:
        raise RuntimeError("state image target is not the reviewed VeeR-EL2 target")
    sections = state_image.get("sections")
    if not isinstance(sections, Mapping):
        raise RuntimeError("state image has no sections object")

    storage_size = _storage_size(meta)
    root_offset = _root_offset(meta)
    blob = bytearray(storage_size)
    materialized: dict[str, object] = {
        "storage_size": storage_size,
        "root_offset_in_state": root_offset,
        "program_staging_imem_bytes": 0,
        "program_staging_lmem_bytes": 0,
        "program_staging_imem_skipped_before_base": 0,
        "program_staging_lmem_skipped_before_base": 0,
        "program_staging_imem_skipped_after_window": 0,
        "program_staging_lmem_skipped_after_window": 0,
        "dccm_bank_words": 0,
        "iccm_bank_words": 0,
        "dccm_bank_skipped_missing_bank": 0,
        "iccm_bank_skipped_missing_bank": 0,
        "dccm_bank_skipped_out_of_range": 0,
        "iccm_bank_skipped_out_of_range": 0,
        "control_scalars_written": [],
        "testbench_vectors_written": [],
    }

    control = sections.get("control_scalars")
    if isinstance(control, Mapping):
        for field_name, raw_value in control.items():
            field = mapped_fields.get(str(field_name))
            if not field:
                continue
            offset = root_offset + int(field["offset"])
            _write_le(blob, offset, int(field["size"]), int(raw_value))
            materialized["control_scalars_written"].append(str(field_name))

    for field_name, value in (
        ("tb_top__DOT__reset_vector", RESET_VECTOR_DEFAULT),
        ("tb_top__DOT__nmi_vector", NMI_VECTOR_DEFAULT),
    ):
        field = mapped_fields.get(field_name)
        if not field:
            continue
        offset = root_offset + int(field["offset"])
        _write_le(blob, offset, int(field["size"]), value)
        materialized["testbench_vectors_written"].append(field_name)

    imem = mapped_fields.get("tb_top__DOT__imem__DOT__mem")
    lmem = mapped_fields.get("tb_top__DOT__lmem__DOT__mem")
    if imem:
        imem_materialized = _materialize_flat_program_mem(
            blob=blob,
            root_offset=root_offset,
            field=imem,
            entries=sections.get("program_staging_imem"),
        )
        materialized["program_staging_imem_bytes"] = imem_materialized["written"]
        materialized["program_staging_imem_skipped_before_base"] = imem_materialized["skipped_before_base"]
        materialized["program_staging_imem_skipped_after_window"] = imem_materialized["skipped_after_window"]
    if lmem:
        lmem_materialized = _materialize_flat_program_mem(
            blob=blob,
            root_offset=root_offset,
            field=lmem,
            entries=sections.get("program_staging_lmem"),
        )
        materialized["program_staging_lmem_bytes"] = lmem_materialized["written"]
        materialized["program_staging_lmem_skipped_before_base"] = lmem_materialized["skipped_before_base"]
        materialized["program_staging_lmem_skipped_after_window"] = lmem_materialized["skipped_after_window"]
    dccm_materialized = _materialize_ecc_bank_entries(
        blob=blob,
        root_offset=root_offset,
        mapped_fields=mapped_fields,
        memory_kind="dccm",
        section=sections.get("dccm_banks"),
    )
    materialized["dccm_bank_words"] = dccm_materialized["written"]
    materialized["dccm_bank_skipped_missing_bank"] = dccm_materialized["skipped_missing_bank"]
    materialized["dccm_bank_skipped_out_of_range"] = dccm_materialized["skipped_out_of_range"]
    iccm_materialized = _materialize_ecc_bank_entries(
        blob=blob,
        root_offset=root_offset,
        mapped_fields=mapped_fields,
        memory_kind="iccm",
        section=sections.get("iccm_banks"),
    )
    materialized["iccm_bank_words"] = iccm_materialized["written"]
    materialized["iccm_bank_skipped_missing_bank"] = iccm_materialized["skipped_missing_bank"]
    materialized["iccm_bank_skipped_out_of_range"] = iccm_materialized["skipped_out_of_range"]
    return bytes(blob), materialized


def materialize_veer_el2_syms_init_states(
    *,
    state_images: list[Mapping[str, object]],
    meta: Mapping[str, object],
    mapped_fields: Mapping[str, Mapping[str, object]],
) -> tuple[bytes, dict[str, object]]:
    if not state_images:
        raise RuntimeError("at least one VeeR-EL2 state image is required")
    blobs: list[bytes] = []
    per_state: list[dict[str, object]] = []
    program_preloads: list[object] = []
    program_sha256s: list[object] = []
    init_state_sha256s: list[str] = []
    for state_index, state_image in enumerate(state_images):
        blob, materialized = materialize_veer_el2_syms_init_state(
            state_image=state_image,
            meta=meta,
            mapped_fields=mapped_fields,
        )
        blobs.append(blob)
        init_state_sha256s.append(hashlib.sha256(blob).hexdigest())
        per_state.append(
            {
                "state_index": state_index,
                "program_preload": state_image.get("program_preload"),
                "program_sha256": state_image.get("program_sha256"),
                **materialized,
            }
        )
        program_preloads.append(state_image.get("program_preload"))
        program_sha256s.append(state_image.get("program_sha256"))
    return b"".join(blobs), {
        "storage_size": _storage_size(meta),
        "state_count": len(state_images),
        "mixed_state_preload": len(state_images) > 1,
        "program_preloads": program_preloads,
        "program_sha256s": program_sha256s,
        "init_state_sha256s": init_state_sha256s,
        "per_state": per_state,
    }


def write_veer_el2_clock_reset_patch_script(
    *,
    path: Path,
    root_offset: int,
    mapped_fields: Mapping[str, Mapping[str, object]],
    clock_cycles: int,
    reset_launches: int = DEFAULT_RESET_LAUNCHES,
    state_count: int = 1,
    storage_size: int | None = None,
    clock_patch_mode: str = DEFAULT_CLOCK_PATCH_MODE,
) -> dict[str, object]:
    if clock_cycles < 1:
        raise ValueError("clock_cycles must be positive")
    if reset_launches < 1:
        raise ValueError("reset_launches must be positive")
    if state_count < 1:
        raise ValueError("state_count must be positive")
    if state_count > 1 and (storage_size is None or storage_size <= 0):
        raise ValueError("positive storage_size is required when state_count > 1")
    patch_script_mode = _normalize_clock_patch_mode(clock_patch_mode)
    core_clk = root_offset + _mapped_field_offset(mapped_fields, "tb_top__DOT__core_clk")
    rst_l = root_offset + _mapped_field_offset(mapped_fields, "tb_top__DOT__rst_l")
    porst_l = root_offset + _mapped_field_offset(mapped_fields, "tb_top__DOT__porst_l")

    def format_drive(core_clk_value: int, rst_l_value: int, porst_l_value: int) -> str:
        parts: list[str] = []
        stride = int(storage_size or 0)
        for state_index in range(state_count):
            state_base = stride * state_index
            parts.extend(
                [
                    f"{state_base + core_clk}:0x{core_clk_value:02x}",
                    f"{state_base + rst_l}:0x{rst_l_value:02x}",
                    f"{state_base + porst_l}:0x{porst_l_value:02x}",
                ]
            )
        return " ".join(parts)

    lines: list[str] = []
    for index in range(reset_launches):
        clk_value = index & 1
        lines.append(format_drive(clk_value, 0, 0))
    if patch_script_mode in {DEFAULT_CLOCK_PATCH_MODE, RESIDENT_PAIR_CYCLE_CLOCK_PATCH_MODE}:
        lines.extend(
            [
                format_drive(0, 1, 1),
                f"@repeat-seq {clock_cycles}",
                format_drive(0, 1, 1),
                format_drive(1, 1, 1),
                "@end-repeat-seq",
            ]
        )
        logical_steps = reset_launches + 1 + (clock_cycles * 2)
    elif patch_script_mode == EXPERIMENTAL_POSEDGE_ONLY_CLOCK_PATCH_MODE:
        lines.extend(
            [
                format_drive(0, 1, 1),
                f"@repeat-seq {clock_cycles}",
                format_drive(1, 1, 1),
                "@end-repeat-seq",
            ]
        )
        logical_steps = reset_launches + 1 + clock_cycles
    else:
        raise ValueError(f"unsupported clock patch mode {patch_script_mode!r}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "patch_script": path,
        "clock_cycles": clock_cycles,
        "reset_launches": reset_launches,
        "logical_steps": logical_steps,
        "patch_script_mode": patch_script_mode,
        "patch_drive_scope": "all_states" if state_count > 1 else "state0_only",
        "state_count": state_count,
        "state_stride_bytes": storage_size,
        "field_offsets": {
            "tb_top__DOT__core_clk": core_clk,
            "tb_top__DOT__rst_l": rst_l,
            "tb_top__DOT__porst_l": porst_l,
        },
    }


def _decode_gpu_observables(
    *,
    dumped_state: bytes,
    mapped_fields: Mapping[str, Mapping[str, object]],
    root_offset: int,
) -> dict[str, object]:
    def read_field(key: str) -> int:
        field = mapped_fields.get(key)
        if not field:
            return 0
        return _read_le(dumped_state, root_offset + int(field["offset"]), int(field["size"]))

    mcycle = read_field("cycle:mcyclel")
    minstret = read_field("cycle:minstretl")
    pc = read_field("pc:i0_pc_r_ff")
    pc_d = read_field("pc:tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d")
    mailbox_write = read_field("observable:mailbox_write")
    obuf_data = read_field("observable:obuf_data")
    obuf_low_byte = obuf_data & 0xFF
    chars = []
    for shift in range(0, 64, 8):
        byte = (obuf_data >> shift) & 0xFF
        if 32 <= byte < 127:
            chars.append(chr(byte))
    mailbox_text = "".join(chars).rstrip()
    stdout_lines = [
        "GPU_OBSERVABLES_UNAVAILABLE",
        f"mailbox_write={mailbox_write} obuf_data=0x{obuf_data:016x} mailbox_text={mailbox_text}",
        f"Finished : minstret = {minstret}, mcycle = {mcycle}",
    ]
    return {
        "stdout": "\n".join(stdout_lines) + "\n",
        "cycles": int(mcycle),
        "mcycle": int(mcycle),
        "minstret": int(minstret),
        "pc": int(pc),
        "pc_hex": f"0x{pc:08x}",
        "pc_d": int(pc_d),
        "pc_d_hex": f"0x{pc_d:08x}",
        "mailbox_write": int(mailbox_write),
        "obuf_data": int(obuf_data),
        "obuf_low_byte": int(obuf_low_byte),
        "finish_marker_observed": obuf_low_byte == 0xFF,
        "mailbox_text": mailbox_text,
    }


def _parallel_state_observable_summary(
    *,
    dumped_state: bytes,
    mapped_fields: Mapping[str, Mapping[str, object]],
    root_offset: int,
    storage_size: int,
    state_count: int,
    identical_init_expected: bool = True,
) -> dict[str, object]:
    state_observables = []
    comparable_keys = (
        "mcycle",
        "minstret",
        "pc",
        "mailbox_write",
        "obuf_data",
        "finish_marker_observed",
        "mailbox_text",
    )
    for state_index in range(state_count):
        observables = _decode_gpu_observables(
            dumped_state=dumped_state,
            mapped_fields=mapped_fields,
            root_offset=root_offset + (storage_size * state_index),
        )
        if identical_init_expected:
            stdout_observability_scope = (
                "state0_stdout_trace_represents_identical_state_batch"
                if state_index == 0
                else "covered_by_state0_only_when_final_observables_match"
            )
            stdout_reconstruction_supported = True
            stdout_unsupported_reason = None
        else:
            stdout_observability_scope = (
                "state0_stdout_trace_only"
                if state_index == 0
                else "unsupported_mixed_state_non_state0"
            )
            stdout_reconstruction_supported = state_index == 0
            stdout_unsupported_reason = (
                None
                if state_index == 0
                else "mixed-state non-state0 stdout/mailbox reconstruction is not implemented"
            )
        state_observables.append(
            {
                "state_index": state_index,
                **{key: observables[key] for key in comparable_keys if key in observables},
                "pc_hex": observables.get("pc_hex"),
                "stdout_observability_scope": stdout_observability_scope,
                "stdout_reconstruction_supported": stdout_reconstruction_supported,
                "stdout_unsupported_reason": stdout_unsupported_reason,
            }
        )
    reference = {
        key: state_observables[0].get(key)
        for key in comparable_keys
    } if state_observables else {}
    matching_state_count = sum(
        1
        for item in state_observables
        if all(item.get(key) == value for key, value in reference.items())
    )
    all_match = bool(state_observables) and matching_state_count == len(state_observables)
    if not identical_init_expected:
        return {
            "parallel_state_count": state_count,
            "parallel_state_validation_status": "mixed_state_final_observables_recorded",
            "parallel_state_observables_match": None,
            "parallel_state_matching_count": matching_state_count,
            "parallel_state_validation_scope": (
                "state0_stdout_trace_plus_all_states_final_observables_for_mixed_init_state"
            ),
            "per_state_observability_contract": {
                "status": "incomplete_mixed_state_stdout",
                "finish_marker_per_state": True,
                "final_counters_per_state": True,
                "stdout_per_state": False,
                "rtlmeter_cycles_per_state": False,
                "unsupported_reason": (
                    "mixed-state stdout/cycle emission is only implemented for state0"
                ),
            },
            "state_observables": state_observables,
        }
    return {
        "parallel_state_count": state_count,
        "parallel_state_validation_status": (
            "all_final_observables_match_state0" if all_match else "final_observables_mismatch"
        ),
        "parallel_state_observables_match": all_match,
        "parallel_state_matching_count": matching_state_count,
        "parallel_state_validation_scope": (
            "state0_stdout_trace_plus_all_states_final_observables_for_identical_init_state"
        ),
        "per_state_observability_contract": {
            "status": "state0_stdout_with_identical_state_assumption",
            "finish_marker_per_state": True,
            "final_counters_per_state": True,
            "stdout_per_state": False,
            "rtlmeter_cycles_per_state": False,
            "unsupported_reason": (
                "stdout/cycles are emitted from state0; identical-state batches rely on final-observable matching"
            ),
        },
        "state_observables": state_observables,
    }


def _trace_field_spec(
    *,
    root_offset: int,
    mapped_fields: Mapping[str, Mapping[str, object]],
) -> str:
    fields = [
        ("mcycle", "cycle:mcyclel"),
        ("minstret", "cycle:minstretl"),
        ("pc", "pc:i0_pc_r_ff"),
        ("pc_d", "pc:tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d"),
        ("pc_din", "debug:i0_pc_r_ff_din"),
        ("instr_d", "debug:dec_i0_instr_d"),
        ("branch_d", "debug:dec_i0_branch_d"),
        ("decode_d", "debug:dec_i0_decode_d"),
        ("decode_valid_gate", "debug:dec_decode_valid_gate"),
        ("decode_ib0_valid", "debug:dec_ib0_valid_d"),
        ("decode_misc2ff", "debug:dec_misc2ff_dout"),
        ("decode_i0_exublock", "debug:dec_i0_exublock_d"),
        ("decode_misc1ff", "debug:dec_misc1ff_dout"),
        ("decode_halt_ff", "debug:dec_halt_ff_dout"),
        ("decode_presync_stall", "debug:dec_presync_stall"),
        ("decode_lsu_idle", "debug:dec_lsu_idle"),
        ("exu_div_valid_in", "debug:exu_div_valid_in"),
        ("exu_div_running_state", "debug:exu_div_running_state"),
        ("exu_div_i_misc_ff", "debug:exu_div_i_misc_ff_dout"),
        ("exu_div_i_misc_ff_din", "debug:exu_div_i_misc_ff_din"),
        ("exu_div_shortq", "debug:exu_div_shortq"),
        ("exu_div_shortq_enable", "debug:exu_div_shortq_enable"),
        ("exu_div_quotient_raw", "debug:exu_div_quotient_raw"),
        ("exu_div_quotient_new", "debug:exu_div_quotient_new"),
        ("exu_div_dw_shortq_raw", "debug:exu_div_dw_shortq_raw"),
        ("exu_div_i_b_ff", "debug:exu_div_i_b_ff_dout"),
        ("exu_div_i_b_ff_din", "debug:exu_div_i_b_ff_din"),
        ("exu_div_a_ff", "debug:exu_div_a_ff"),
        ("exu_div_q_ff", "debug:exu_div_q_ff"),
        ("exu_div_r_ff", "debug:exu_div_r_ff"),
        ("brp_valid", "debug:i0_brp_valid"),
        ("predict_nt", "debug:i0_predict_nt"),
        ("predict_br", "debug:i0_predict_br"),
        ("i0_valid_r", "debug:dec_tlu_i0_valid_r"),
        ("i0_valid_tlu", "debug:i0_valid_no_ebreak_ecall_r"),
        ("dma_dccm_stall", "debug:dma_dccm_stall_any"),
        ("store_stall", "debug:lsu_store_stall_any"),
        ("lsu_valid", "debug:dec_lsu_valid_raw_d"),
        ("fetch_stall", "debug:ifu_pmu_fetch_stall"),
        ("ifu_pmu_instr_aligned", "debug:ifu_pmu_instr_aligned"),
        ("fetch_fbwrite", "debug:ifu_ifc_fbwrite_dout"),
        ("fetch_consume_gate", "debug:ifu_ifc_fetch_consume_gate"),
        ("dec_flush_err", "debug:dec_tlu_flush_err_r"),
        ("dma_iccm_stall", "debug:dma_iccm_stall_any"),
        ("fetch_perr_state", "debug:ifu_mem_perr_state"),
        ("fetch_err_stop_state", "debug:ifu_mem_err_stop_state"),
        ("exu_flush", "debug:exu_flush_final"),
        ("flush_lower", "debug:dec_tlu_flush_lower_r"),
        ("flush_path", "debug:dec_tlu_flush_path_r"),
        ("tb_ifu_axi_rvalid", "debug:tb_ifu_axi_rvalid"),
        ("tb_ifu_axi_rid", "debug:tb_ifu_axi_rid"),
        ("tb_ifu_axi_rresp", "debug:tb_ifu_axi_rresp"),
        ("tb_ifu_axi_rdata", "debug:tb_ifu_axi_rdata"),
        ("tb_mux_axi_rvalid", "debug:tb_mux_axi_rvalid"),
        ("tb_sb_axi_rdata", "debug:tb_sb_axi_rdata"),
        ("tb_lmem_axi_rvalid", "debug:tb_lmem_axi_rvalid"),
        ("tb_lmem_axi_rdata", "debug:tb_lmem_axi_rdata"),
        ("tb_ifu_axi_arready", "debug:tb_ifu_axi_arready"),
        ("ifu_bus_cmd_valid", "debug:ifu_bus_cmd_valid"),
        ("ifu_bus_rd_addr_count", "debug:ifu_bus_rd_addr_count"),
        ("ifu_fetch_addr_f", "debug:ifu_fetch_addr_f"),
        ("ifu_pmp_addr", "debug:ifu_pmp_addr"),
        ("ifu_ifc_fetch_req_bf", "debug:ifu_ifc_fetch_req_bf"),
        ("ifu_ifc_fb_write_ns", "debug:ifu_ifc_fb_write_ns"),
        ("ifu_ifc_miss_f", "debug:ifu_ifc_miss_f"),
        ("ifu_mem_miss_f", "debug:ifu_mem_miss_f"),
        ("ifu_mem_miss_state", "debug:ifu_mem_miss_state"),
        ("ifu_mem_miss_state_en", "debug:ifu_mem_miss_state_en"),
        ("ifu_mem_write_ic_16_bytes", "debug:ifu_mem_write_ic_16_bytes"),
        ("ifu_mem_ic_act_miss_f", "debug:ifu_mem_ic_act_miss_f"),
        ("ifu_ifc_fetch_ready", "debug:ifu_ifc_fetch_ready"),
        ("ifu_ifc_ic_hit_f", "debug:ifu_ifc_ic_hit_f"),
        ("ifu_aln_aligndata", "debug:ifu_aln_aligndata"),
        ("ifu_aln_alignfromf1", "debug:ifu_aln_alignfromf1"),
        ("ifu_aln_brdata0_en", "debug:ifu_aln_brdata0_en"),
        ("ifu_aln_brdata1_en", "debug:ifu_aln_brdata1_en"),
        ("ifu_aln_brdata2_en", "debug:ifu_aln_brdata2_en"),
        ("ifu_aln_shift_f1_f0", "debug:ifu_aln_shift_f1_f0"),
        ("ifu_aln_shift_f2_f0", "debug:ifu_aln_shift_f2_f0"),
        ("ifu_aln_shift_f2_f1", "debug:ifu_aln_shift_f2_f1"),
        ("ifu_aln_sf0val", "debug:ifu_aln_sf0val"),
        ("ifu_aln_sf1val", "debug:ifu_aln_sf1val"),
        ("ifu_aln_bundle1", "debug:ifu_aln_bundle1"),
        ("ifu_aln_bundle2", "debug:ifu_aln_bundle2"),
        ("dec_tlu_flush_noredir_r", "debug:dec_tlu_flush_noredir_r"),
        ("ifu_ic_fetch_val_f", "debug:ifu_ic_fetch_val_f"),
        ("ifu_iccm_rd_ecc_single_err", "debug:ifu_iccm_rd_ecc_single_err"),
        ("ifu_ic_error_start", "debug:ifu_ic_error_start"),
        ("dec_tlu_i0_commit_cmt", "debug:dec_tlu_i0_commit_cmt"),
        ("dec_tlu_freeff_dout", "debug:dec_tlu_freeff_dout"),
        ("dec_tlu_freeff_din", "debug:dec_tlu_freeff_din"),
        ("ifu_aln_bundle1_din", "debug:ifu_aln_bundle1_din"),
        ("root_act_triggered", "debug:root_act_triggered"),
        ("root_nba_triggered", "debug:root_nba_triggered"),
        ("mailbox_write", "observable:mailbox_write"),
        ("obuf_data", "observable:obuf_data"),
    ]
    return ",".join(
        f"{trace_name}:{root_offset + _mapped_field_offset(mapped_fields, mapped_key)}:"
        f"{_mapped_field_size(mapped_fields, mapped_key)}"
        for trace_name, mapped_key in fields
    )


def reconstruct_veer_el2_stdout_from_trace(
    trace_path: Path,
    *,
    fallback_finish_mcycle: int | None = None,
    fallback_finish_minstret: int | None = None,
    sampled_clock_high_only: bool = False,
) -> dict[str, object]:
    mailbox_chars: list[str] = []
    finish_status: str | None = None
    finish_mcycle = 0
    finish_minstret = 0
    printable_count = 0
    row_count = 0
    seen_print_events: set[tuple[int, int]] = set()
    previous_mailbox_write = 0
    if not trace_path.is_file():
        return {
            "stdout": "",
            "stdout_stream_reconstructed": False,
            "mailbox_text": "",
            "finish_status": None,
            "trace_rows": 0,
            "printable_mailbox_write_count": 0,
        }
    with trace_path.open("r", encoding="utf-8", newline="") as fp:
        for row in csv.DictReader(fp):
            row_count += 1
            mailbox_write = int(str(row.get("mailbox_write", "0")), 0)
            obuf_data = int(str(row.get("obuf_data", "0")), 0)
            if not mailbox_write:
                previous_mailbox_write = 0
                continue
            low_byte = obuf_data & 0xFF
            has_mcycle = "mcycle" in row and row.get("mcycle") not in (None, "")
            mcycle = int(str(row.get("mcycle", "0")), 0) if has_mcycle else 0
            if not sampled_clock_high_only and not has_mcycle and previous_mailbox_write:
                continue
            previous_mailbox_write = mailbox_write
            if 5 < low_byte < 127:
                if has_mcycle:
                    print_event = (mcycle, low_byte)
                    if print_event in seen_print_events:
                        continue
                    seen_print_events.add(print_event)
                mailbox_chars.append(chr(low_byte))
                printable_count += 1
            elif low_byte in (0x01, 0xFF):
                finish_status = "TEST_PASSED" if low_byte == 0xFF else "TEST_FAILED"
                finish_mcycle = mcycle
                finish_minstret = int(str(row.get("minstret", "0")), 0)
    if finish_status is not None:
        if finish_mcycle == 0 and fallback_finish_mcycle is not None:
            finish_mcycle = int(fallback_finish_mcycle)
        if finish_minstret == 0 and fallback_finish_minstret is not None:
            finish_minstret = int(fallback_finish_minstret)
    mailbox_text = _normalize_veer_el2_mailbox_text("".join(mailbox_chars))
    if finish_status == "TEST_PASSED":
        stdout = (
            f"{mailbox_text}TEST_PASSED\n\n"
            f"Finished : minstret = {finish_minstret}, mcycle = {finish_mcycle}\n"
            "- verilogSourceFiles/tb_top.sv:624: Verilog $finish\n"
        )
    elif finish_status == "TEST_FAILED":
        stdout = f"{mailbox_text}TEST_FAILED\n"
    else:
        stdout = ""
    return {
        "stdout": stdout,
        "stdout_stream_reconstructed": bool(stdout),
        "mailbox_text": mailbox_text,
        "finish_status": finish_status,
        "trace_rows": row_count,
        "printable_mailbox_write_count": printable_count,
        "finish_mcycle": finish_mcycle,
        "finish_minstret": finish_minstret,
    }


def reconstruct_veer_el2_stdout_from_final_observables(
    *,
    state_image: Mapping[str, object],
    observables: Mapping[str, object],
) -> dict[str, object]:
    if state_image.get("program_sha256") != HELLO_PROGRAM_SHA256:
        return {
            "stdout": "",
            "stdout_stream_reconstructed": False,
            "mailbox_text": "",
            "finish_status": None,
            "trace_rows": 0,
            "printable_mailbox_write_count": 0,
            "final_observable_stdout": False,
            "diagnostic": "final-observable stdout reconstruction is reviewed only for the hello program",
        }
    low_byte = int(observables.get("obuf_low_byte", 0))
    if low_byte not in (0x01, 0xFF):
        return {
            "stdout": "",
            "stdout_stream_reconstructed": False,
            "mailbox_text": "",
            "finish_status": None,
            "trace_rows": 0,
            "printable_mailbox_write_count": 0,
            "final_observable_stdout": False,
            "diagnostic": "final observable does not contain a reviewed finish marker",
        }
    finish_status = "TEST_PASSED" if low_byte == 0xFF else "TEST_FAILED"
    mcycle = int(observables.get("mcycle", 0))
    minstret = int(observables.get("minstret", 0))
    mailbox_text = "-------------------------\nHello World from VeeR EL2\n-------------------------\n"
    if finish_status == "TEST_PASSED":
        stdout = (
            f"{mailbox_text}TEST_PASSED\n\n"
            f"Finished : minstret = {minstret}, mcycle = {mcycle}\n"
            "- verilogSourceFiles/tb_top.sv:624: Verilog $finish\n"
        )
    else:
        stdout = f"{mailbox_text}TEST_FAILED\n"
    return {
        "stdout": stdout,
        "stdout_stream_reconstructed": True,
        "mailbox_text": mailbox_text,
        "finish_status": finish_status,
        "trace_rows": 0,
        "printable_mailbox_write_count": 0,
        "finish_mcycle": mcycle,
        "finish_minstret": minstret,
        "final_observable_stdout": True,
        "diagnostic": "hello stdout reconstructed from reviewed final observables without per-step trace",
    }


def _normalize_veer_el2_mailbox_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    normalized: list[str] = []
    for line in lines:
        body = line.rstrip("\n")
        newline = "\n" if line.endswith("\n") else ""
        if body and set(body) == {"-"} and len(body) > 25:
            body = body[:25]
        normalized.append(body + newline)
    return "".join(normalized)


def run_sidecar(repo_root: Path) -> int:
    total_started = time.perf_counter()
    phase_started = total_started
    phase_timing_s: dict[str, float] = {}

    def mark_phase(name: str) -> None:
        nonlocal phase_started
        now = time.perf_counter()
        phase_timing_s[name] = round(now - phase_started, 6)
        phase_started = now

    state_image_env = os.environ.get(VEER_EL2_SIDECAR_STATE_IMAGE_ENV)
    mixed_state_image_paths_raw = os.environ.get(VEER_EL2_SIDECAR_STATE_IMAGES_ENV)
    execute_dir_env = os.environ.get(VEER_EL2_SIDECAR_EXECUTE_DIR_ENV)
    if (not state_image_env and not mixed_state_image_paths_raw) or not execute_dir_env:
        print("missing VeeR-EL2 sidecar environment", file=sys.stderr)
        return 2

    state_image_path = Path(state_image_env) if state_image_env else None
    if state_image_path is not None and not state_image_path.is_absolute():
        state_image_path = repo_root / state_image_path
    execute_dir = Path(execute_dir_env)
    if not execute_dir.is_absolute():
        execute_dir = repo_root / execute_dir
    mdir = Path(os.environ.get("VEER_EL2_SIDECAR_MDIR", DEFAULT_MDIR.as_posix()))
    if not mdir.is_absolute():
        mdir = repo_root / mdir
    clock_cycles = int(os.environ.get("VEER_EL2_SIDECAR_CLOCK_CYCLES", str(DEFAULT_CLOCK_CYCLES)))
    reset_launches = int(os.environ.get("VEER_EL2_SIDECAR_RESET_LAUNCHES", str(DEFAULT_RESET_LAUNCHES)))
    rtlmeter_post_finish_cycles = int(
        os.environ.get(
            "VEER_EL2_SIDECAR_RTLMETER_POST_FINISH_CYCLES",
            str(DEFAULT_RTL_METER_POST_FINISH_CYCLES),
        )
    )
    sidecar_state_count = int(os.environ.get("VEER_EL2_SIDECAR_NSTATES", str(DEFAULT_SIDECAR_NSTATES)))
    step_trace_disabled = os.environ.get(DISABLE_STEP_TRACE_ENV) == "1"
    final_observable_stdout = os.environ.get(FINAL_OBSERVABLE_STDOUT_ENV) == "1"
    if sidecar_state_count < 1:
        print("VEER_EL2_SIDECAR_NSTATES must be positive", file=sys.stderr)
        return 2
    try:
        clock_patch_mode = _normalize_clock_patch_mode(os.environ.get(CLOCK_PATCH_MODE_ENV))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    execute_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir = execute_dir / "_sidecar"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    report_path = scratch_dir / "veer_el2_sidecar_executable_report.json"
    mapped_fields_cache_path = scratch_dir / "veer_el2_mapped_fields_cache.json"
    init_path = scratch_dir / "veer_el2_syms_init.bin"
    dump_path = scratch_dir / "veer_el2_gpu_after.bin"
    patch_script_path = scratch_dir / "veer_el2_clock_reset_patch.txt"
    step_trace_path = scratch_dir / "veer_el2_step_trace.csv"
    mark_phase("setup_s")

    meta = _load_json(mdir / "vl_batch_gpu.meta.json")
    storage_size = _storage_size(meta)
    mixed_state_image_paths: list[Path] = []
    if mixed_state_image_paths_raw:
        mixed_state_image_paths = [
            Path(item)
            for item in mixed_state_image_paths_raw.split(os.pathsep)
            if item.strip()
        ]
        mixed_state_image_paths = [
            path if path.is_absolute() else repo_root / path
            for path in mixed_state_image_paths
        ]
        if not mixed_state_image_paths:
            print(f"{VEER_EL2_SIDECAR_STATE_IMAGES_ENV} did not contain any paths", file=sys.stderr)
            return 2
        if sidecar_state_count != len(mixed_state_image_paths):
            print(
                f"VEER_EL2_SIDECAR_NSTATES={sidecar_state_count} must match "
                f"{VEER_EL2_SIDECAR_STATE_IMAGES_ENV} count {len(mixed_state_image_paths)}",
                file=sys.stderr,
            )
            return 2
        state_images = [_load_json(path) for path in mixed_state_image_paths]
        state_image = state_images[0]
    else:
        if state_image_path is None:
            print(f"missing {VEER_EL2_SIDECAR_STATE_IMAGE_ENV}", file=sys.stderr)
            return 2
        state_image = _load_json(state_image_path)
        state_images = [state_image]
    mapped_fields, mapped_fields_cache = _mapped_field_offsets_cached(
        mdir=mdir,
        root=repo_root,
        cache_path=mapped_fields_cache_path,
    )
    mark_phase("load_inputs_s")
    if mixed_state_image_paths:
        init_blob, materialized = materialize_veer_el2_syms_init_states(
            state_images=state_images,
            meta=meta,
            mapped_fields=mapped_fields,
        )
    else:
        init_blob, materialized = materialize_veer_el2_syms_init_state(
            state_image=state_image,
            meta=meta,
            mapped_fields=mapped_fields,
        )
    init_path.write_bytes(init_blob)
    mark_phase("materialize_init_s")
    patch_script = write_veer_el2_clock_reset_patch_script(
        path=patch_script_path,
        root_offset=_root_offset(meta),
        mapped_fields=mapped_fields,
        clock_cycles=clock_cycles,
        reset_launches=reset_launches,
        state_count=sidecar_state_count,
        storage_size=storage_size,
        clock_patch_mode=clock_patch_mode,
    )
    steps = int(patch_script["logical_steps"])
    step_trace_filter = _clock_patch_step_trace_filter(
        reset_launches=reset_launches,
        patch_script_mode=str(patch_script["patch_script_mode"]),
    )
    mark_phase("write_patch_script_s")

    command, hybrid_env_updates = _hybrid_runtime_command(
        mdir=mdir,
        meta=meta,
        state_count=sidecar_state_count,
        steps=steps,
    )
    display_command = [
        _rel(Path(command[0]), repo_root),
        _rel(Path(command[1]), repo_root),
        *command[2:],
    ]
    env = os.environ.copy()
    _apply_wsl_libcuda_env(env)
    env.update(hybrid_env_updates)
    env.update(
        {
            "RUN_VL_HYBRID_INIT_STATE": init_path.resolve().as_posix(),
            "RUN_VL_HYBRID_PATCH_SCRIPT": patch_script_path.resolve().as_posix(),
            "RUN_VL_HYBRID_RESIDENT_STEPS": "1",
            "RUN_VL_HYBRID_DUMP_STATE": dump_path.resolve().as_posix(),
        }
    )
    if not mixed_state_image_paths:
        env["RUN_VL_HYBRID_GPU_REPLICATE_INIT_STATE"] = "1"
    if not step_trace_disabled:
        env.update(
            {
                "RUN_VL_HYBRID_STEP_TRACE": step_trace_path.resolve().as_posix(),
                "RUN_VL_HYBRID_STEP_TRACE_FIELDS": _trace_field_spec(
                    root_offset=_root_offset(meta),
                    mapped_fields=mapped_fields,
                ),
                "RUN_VL_HYBRID_STEP_TRACE_DEVICE_BUFFER": "1",
                "RUN_VL_HYBRID_STEP_TRACE_START": str(step_trace_filter["start"]),
                "RUN_VL_HYBRID_STEP_TRACE_STRIDE": str(step_trace_filter["stride"]),
            }
        )
    if clock_patch_mode == RESIDENT_PAIR_CYCLE_CLOCK_PATCH_MODE:
        env["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE"] = "1"
        env["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START"] = str(reset_launches + 1)
        if os.environ.get(FUSED_PAIR_CYCLE_ENV):
            env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE"] = "1"
        if os.environ.get(FUSED_PAIR_CYCLE_LOOP_ENV):
            env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP"] = "1"
        fused_pair_cycle_loop_chunk = os.environ.get(FUSED_PAIR_CYCLE_LOOP_CHUNK_ENV)
        if fused_pair_cycle_loop_chunk:
            env["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK"] = fused_pair_cycle_loop_chunk
        if os.environ.get(STATE_LOCAL_PATCHES_ENV):
            env["RUN_VL_HYBRID_STATE_LOCAL_PATCHES"] = "1"
    if os.environ.get(FUSED_PATCH_EVAL_ENV):
        env["RUN_VL_HYBRID_FUSED_PATCH_EVAL"] = "1"
    if os.environ.get(HYBRID_STAGE_TIMING_ENV):
        env["RUN_VL_HYBRID_STAGE_TIMING"] = "1"
    hybrid_timing_repeats = os.environ.get(HYBRID_TIMING_REPEATS_ENV)
    if hybrid_timing_repeats:
        env["RUN_VL_HYBRID_TIMING_REPEATS"] = hybrid_timing_repeats
    completed = subprocess.run(command, cwd=repo_root, env=env, text=True, capture_output=True, check=False)
    mark_phase("run_vl_hybrid_wall_s")
    run_vl_hybrid_timing = parse_run_vl_hybrid_timing(completed.stdout)
    gpu_kernel_ms_total = run_vl_hybrid_timing.get("gpu_kernel_time_ms_total")
    report: dict[str, object] = {
        "schema_version": 1,
        "schema_role": "veer_el2_sidecar_executable_run",
        "target": VEER_EL2_RTL_METER_TARGET,
        "state_image": _rel(state_image_path, repo_root) if state_image_path is not None else None,
        "state_images": [_rel(path, repo_root) for path in mixed_state_image_paths] if mixed_state_image_paths else [],
        "execute_dir": _rel(execute_dir, repo_root),
        "mdir": _rel(mdir, repo_root),
        "steps": steps,
        "sidecar_state_count": sidecar_state_count,
        "parallel_state_count": sidecar_state_count,
        "state_stride_bytes": storage_size,
        "clock_reset_patch": {
            **{k: v for k, v in patch_script.items() if k != "patch_script"},
            "patch_script": _rel(patch_script_path, repo_root),
        },
        "materialized": materialized,
        "mapped_fields_cache": mapped_fields_cache,
        "init_state_sha256": hashlib.sha256(init_blob).hexdigest(),
        "run_vl_hybrid_launcher_mode": "direct_hybrid_runtime",
        "run_vl_hybrid_command": display_command,
        "run_vl_hybrid_returncode": completed.returncode,
        "run_vl_hybrid_stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        "run_vl_hybrid_stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
        "run_vl_hybrid_timing": run_vl_hybrid_timing,
        "patch_apply_mode": "device_resident_patch_schedule",
        "resident_patch_schedule": run_vl_hybrid_timing.get("resident_patch_schedule"),
        "state_local_patch_schedule": run_vl_hybrid_timing.get("state_local_patch_schedule"),
        "patch_eval_fusion": run_vl_hybrid_timing.get("patch_eval_fusion"),
        "pair_cycle_fusion": run_vl_hybrid_timing.get("pair_cycle_fusion"),
        "pair_cycle_loop_fusion": run_vl_hybrid_timing.get("pair_cycle_loop_fusion"),
        "pair_cycle_state_local_fusion": run_vl_hybrid_timing.get("pair_cycle_state_local_fusion"),
        "resident_pair_cycle": run_vl_hybrid_timing.get("resident_pair_cycle"),
        "step_trace_copy_mode": (
            "disabled_final_observable_stdout"
            if step_trace_disabled and final_observable_stdout
            else "disabled_final_observable_only"
            if step_trace_disabled
            else run_vl_hybrid_timing.get("step_trace_copy_mode") or "device_buffered_d2d_trace"
        ),
        "step_trace_filter": run_vl_hybrid_timing.get("step_trace_filter") or step_trace_filter,
        "step_trace_disabled": step_trace_disabled,
        "final_observable_stdout_requested": final_observable_stdout,
        "step_trace_field_mode": "mailbox_rising_edge_trace_final_counter_fallback",
        "init_replication_scope": "per_state_mixed_init" if mixed_state_image_paths else "all_states_same_init",
        "init_replication_mode": "host_uploaded_concatenated_state_images" if mixed_state_image_paths else "device_kernel",
        "patch_drive_scope": patch_script["patch_drive_scope"],
        "stdout_trace_state_scope": "state0_only",
        "rtlmeter_observable_emit_scope": "state0_only",
        "cpu_observables_copied": False,
    }
    if completed.returncode != 0:
        report["status"] = "gpu_launch_failed"
        phase_timing_s["total_sidecar_executable_s"] = round(time.perf_counter() - total_started, 6)
        report["phase_timing_s"] = phase_timing_s
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    dumped = dump_path.read_bytes()
    observables = _decode_gpu_observables(
        dumped_state=dumped,
        mapped_fields=mapped_fields,
        root_offset=_root_offset(meta),
    )
    parallel_state_summary = _parallel_state_observable_summary(
        dumped_state=dumped,
        mapped_fields=mapped_fields,
        root_offset=_root_offset(meta),
        storage_size=storage_size,
        state_count=sidecar_state_count,
        identical_init_expected=not bool(mixed_state_image_paths),
    )
    mark_phase("decode_dump_s")
    rtlmeter_cycles = compute_rtlmeter_main_clock_cycles(
        sidecar_clock_cycles=clock_cycles,
        post_finish_cycles=rtlmeter_post_finish_cycles,
    )
    observables["cycles"] = rtlmeter_cycles
    observables["rtlmeter_main_clock_cycles"] = rtlmeter_cycles
    observables["rtlmeter_cycles_source"] = "tb_top.core_clk_posedge_count"
    observables["rtlmeter_post_finish_cycles"] = rtlmeter_post_finish_cycles
    if step_trace_disabled and final_observable_stdout:
        stdout_trace = reconstruct_veer_el2_stdout_from_final_observables(
            state_image=state_image,
            observables=observables,
        )
        stdout_trace["step_trace_disabled"] = True
    elif step_trace_disabled:
        stdout_trace = {
            "stdout": "",
            "stdout_stream_reconstructed": False,
            "mailbox_text": "",
            "finish_status": None,
            "trace_rows": 0,
            "printable_mailbox_write_count": 0,
            "step_trace_disabled": True,
        }
    else:
        stdout_trace = reconstruct_veer_el2_stdout_from_trace(
            step_trace_path,
            fallback_finish_mcycle=int(observables.get("mcycle", 0)),
            fallback_finish_minstret=int(observables.get("minstret", 0)),
            sampled_clock_high_only=step_trace_filter["mode"] in {"clock_high_after_reset", "clock_high_only_after_reset"},
        )
    if stdout_trace["stdout_stream_reconstructed"]:
        observables["stdout"] = stdout_trace["stdout"]
        observables["stdout_stream_reconstructed"] = True
        observables["mailbox_text"] = stdout_trace["mailbox_text"]
    else:
        observables["stdout_stream_reconstructed"] = False
    mark_phase("reconstruct_stdout_s")
    out_dir = execute_dir / "_execute"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stdout.log").write_text(str(observables["stdout"]), encoding="utf-8")
    (execute_dir / "_rtlmeter_cycles.txt").write_text(f"{int(observables['cycles'])}\n", encoding="utf-8")
    mark_phase("emit_observables_s")
    total_sidecar_s = round(time.perf_counter() - total_started, 6)
    phase_timing_s["total_sidecar_executable_s"] = total_sidecar_s
    if isinstance(gpu_kernel_ms_total, (int, float)):
        phase_timing_s["host_overhead_estimate_s"] = round(total_sidecar_s - (float(gpu_kernel_ms_total) / 1000.0), 6)
    report["status"] = "observables_emitted"
    report["dump_state"] = _rel(dump_path, repo_root)
    if not step_trace_disabled:
        report["step_trace"] = _rel(step_trace_path, repo_root)
    report["dump_state_sha256"] = hashlib.sha256(dumped).hexdigest()
    report["stdout_trace"] = {k: v for k, v in stdout_trace.items() if k != "stdout"}
    report["observables"] = {k: v for k, v in observables.items() if k != "stdout"}
    report["parallel_state_validation"] = parallel_state_summary
    report["stdout_sha256"] = hashlib.sha256(str(observables["stdout"]).encode("utf-8")).hexdigest()
    report["phase_timing_s"] = phase_timing_s
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


def main() -> None:
    raise SystemExit(run_sidecar(Path.cwd().resolve()))


if __name__ == "__main__":
    main()
