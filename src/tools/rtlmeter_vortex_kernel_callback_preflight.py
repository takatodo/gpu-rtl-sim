#!/usr/bin/env python3
"""Preflight wiring the Vortex PTX artifact into the materialized runtime callback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OBJ_DIR = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir"
)
DEFAULT_VSIM_MAIN = DEFAULT_OBJ_DIR / "Vsim__main.cpp"
DEFAULT_META = DEFAULT_OBJ_DIR / "vl_batch_gpu.meta.json"
NOOP_CALLBACK = "rtlmeter_vortex_real_cuda_noop_kernel"
ROOT_STORAGE_CALLBACK = "rtlmeter_vortex_real_cuda_launch_root_storage_kernel"
MATERIALIZED_CALL = "vortex_lowered_tb_invoke_runtime_sequence(&args"
CUDA_MODULE_LOAD_MARKERS = ("cuModuleLoad", "cuModuleLoadData", "cuModuleLoadDataEx")
ROOT_STORAGE_MARKERS = (
    "rtlmeter_vortex_root_storage",
    "storage_base",
    "vl_eval_batch_gpu",
)


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _artifact_path(meta: dict[str, Any], *, meta_path: Path) -> Path | None:
    value = meta.get("cubin")
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else meta_path.parent / path


def _positive_int(value: object) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def build_preflight(
    repo_root: Path,
    *,
    obj_dir: Path = DEFAULT_OBJ_DIR,
    vsim_main: Path | None = None,
    meta: Path | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    obj = obj_dir if obj_dir.is_absolute() else root / obj_dir
    main_path = vsim_main if vsim_main is not None else obj / "Vsim__main.cpp"
    meta_path = meta if meta is not None else obj / "vl_batch_gpu.meta.json"
    main_path = main_path if main_path.is_absolute() else root / main_path
    meta_path = meta_path if meta_path.is_absolute() else root / meta_path

    metadata = _load_json(meta_path)
    main_text = main_path.read_text(encoding="utf-8", errors="replace") if main_path.is_file() else ""
    artifact = _artifact_path(metadata, meta_path=meta_path) if metadata is not None else None
    artifact_exists = artifact.is_file() if artifact is not None else False
    hierarchy = metadata.get("hierarchy_state") if isinstance(metadata, dict) else None
    hierarchy = hierarchy if isinstance(hierarchy, dict) else {}
    prelaunch_rejection_required = hierarchy.get("prelaunch_rejection_required") is True
    unsafe_syms_gep_count = hierarchy.get("unsafe_syms_gep_count")
    unsafe_syms_gep_count = unsafe_syms_gep_count if isinstance(unsafe_syms_gep_count, int) else None
    storage_size = _positive_int(metadata.get("storage_size")) if metadata is not None else None
    kernel_name = metadata.get("kernel") if isinstance(metadata, dict) else None
    kernel_name = kernel_name if isinstance(kernel_name, str) and kernel_name else None

    noop_callback_observed = NOOP_CALLBACK in main_text
    root_storage_callback_observed = ROOT_STORAGE_CALLBACK in main_text
    materialized_runtime_call_observed = MATERIALIZED_CALL in main_text
    cuda_module_loader_observed = any(marker in main_text for marker in CUDA_MODULE_LOAD_MARKERS)
    root_storage_launch_abi_observed = (
        kernel_name is not None
        and kernel_name in main_text
        and any(marker in main_text for marker in ROOT_STORAGE_MARKERS)
    )

    missing: list[str] = []
    if metadata is None:
        missing.append("vl_batch_gpu.meta.json")
    if not artifact_exists:
        missing.append("vl_batch_gpu.ptx_or_cubin")
    if not main_path.is_file():
        missing.append("Vsim__main.cpp")
    if not materialized_runtime_call_observed:
        missing.append("materialized_runtime_sequence_call")
    if not noop_callback_observed and not root_storage_callback_observed:
        missing.append("kernel_launch_callback")
    if storage_size is None:
        missing.append("positive_storage_size")
    if kernel_name is None:
        missing.append("kernel_name")
    if prelaunch_rejection_required:
        missing.append("safe_root_or_syms_storage_launch_abi")
    if not root_storage_launch_abi_observed:
        missing.append("root_storage_backed_kernel_launch_callback")

    artifact_ready = metadata is not None and artifact_exists and storage_size is not None and kernel_name is not None
    callback_wiring_ready = (
        artifact_ready
        and main_path.is_file()
        and materialized_runtime_call_observed
        and root_storage_callback_observed
        and not prelaunch_rejection_required
        and root_storage_launch_abi_observed
    )
    if not artifact_ready:
        status = "missing_kernel_artifact_or_metadata"
        next_boundary = "build_real_vortex_kernel_artifact_for_materialized_runtime_callback"
    elif prelaunch_rejection_required:
        status = "blocked_by_gpu_artifact_prelaunch_rejection"
        next_boundary = "clear_vortex_gpu_artifact_prelaunch_rejection_or_build_root_syms_storage_launch_abi"
    elif not root_storage_launch_abi_observed:
        status = "blocked_by_missing_root_storage_launch_callback"
        next_boundary = "wire_root_storage_backed_vl_eval_batch_gpu_callback"
    elif callback_wiring_ready:
        status = "ready_to_run_real_kernel_callback_smoke"
        next_boundary = "run_real_vortex_kernel_callback_smoke_and_observable_export"
    else:
        status = "blocked_by_materialized_callback_context"
        next_boundary = "repair_materialized_runtime_callback_context"

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_kernel_callback_preflight",
        "status": status,
        "case": "Vortex:mini:hello",
        "obj_dir": _display_path(obj, repo_root=root),
        "vsim_main": _display_path(main_path, repo_root=root),
        "meta": _display_path(meta_path, repo_root=root),
        "artifact": _display_path(artifact, repo_root=root) if artifact is not None else None,
        "artifact_exists": artifact_exists,
        "artifact_ready": artifact_ready,
        "cuda_module_format": metadata.get("cuda_module_format") if isinstance(metadata, dict) else None,
        "kernel_name": kernel_name,
        "storage_size": storage_size,
        "root_storage_size": hierarchy.get("root_storage_size"),
        "syms_storage_size": hierarchy.get("syms_storage_size"),
        "prelaunch_rejection_required": prelaunch_rejection_required,
        "unsafe_syms_gep_count": unsafe_syms_gep_count,
        "noop_callback_observed": noop_callback_observed,
        "root_storage_callback_observed": root_storage_callback_observed,
        "materialized_runtime_call_observed": materialized_runtime_call_observed,
        "cuda_module_loader_observed": cuda_module_loader_observed,
        "root_storage_launch_abi_observed": root_storage_launch_abi_observed,
        "callback_wiring_ready": callback_wiring_ready,
        "missing_prerequisites": list(dict.fromkeys(missing)),
        "next_required_boundary": next_boundary,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "callback_preflight_is_not_kernel_execution",
            "ptx_artifact_presence_is_not_observable_authority",
            "prelaunch_rejection_blocks_runtime_authority",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--obj-dir", default=DEFAULT_OBJ_DIR.as_posix())
    parser.add_argument("--vsim-main")
    parser.add_argument("--meta")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_kernel_callback_preflight.json")
    args = parser.parse_args(argv)

    report = build_preflight(
        Path(args.repo_root),
        obj_dir=Path(args.obj_dir),
        vsim_main=Path(args.vsim_main) if args.vsim_main else None,
        meta=Path(args.meta) if args.meta else None,
    )
    if args.write_report:
        out = Path(args.report_out)
        if not out.is_absolute():
            out = Path(args.repo_root) / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
