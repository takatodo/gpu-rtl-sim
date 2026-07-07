#!/usr/bin/env python3
"""Diagnose the Vortex PTX module-load/JIT blocker without claiming timing."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PTX = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/vl_batch_gpu.ptx"
)
DEFAULT_META = DEFAULT_PTX.with_name("vl_batch_gpu.meta.json")
DEFAULT_CUBIN_OUT = Path(
    "artifacts/rtlmeter_vortex_ptx_module_load_diagnostic/vl_batch_gpu.ptxas_probe.cubin"
)


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _sanitize_text(text: str, *, repo_root: Path) -> str:
    return text.replace(repo_root.as_posix(), "<repo-root>")


def _ptx_stats(ptx: Path) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "ptx_exists": ptx.is_file(),
        "ptx_bytes": 0,
        "ptx_lines": 0,
        "ptx_target": None,
        "ptx_address_size": None,
        "entry_count": 0,
        "visible_entry_count": 0,
        "func_count": 0,
        "global_decl_count": 0,
        "shared_decl_count": 0,
        "reg_decl_count": 0,
        "max_line_length": 0,
    }
    if not ptx.is_file():
        return stats
    stats["ptx_bytes"] = ptx.stat().st_size
    with ptx.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            stats["ptx_lines"] += 1
            stats["max_line_length"] = max(stats["max_line_length"], len(raw_line.rstrip("\n")))
            if line.startswith(".target "):
                stats["ptx_target"] = line.removeprefix(".target ").rstrip(",")
            elif line.startswith(".address_size "):
                stats["ptx_address_size"] = line.removeprefix(".address_size ")
            if ".entry " in line:
                stats["entry_count"] += 1
            if ".visible .entry " in line:
                stats["visible_entry_count"] += 1
            if ".func " in line or ".visible .func " in line:
                stats["func_count"] += 1
            if line.startswith(".global "):
                stats["global_decl_count"] += 1
            if line.startswith(".shared "):
                stats["shared_decl_count"] += 1
            if line.startswith(".reg "):
                stats["reg_decl_count"] += 1
    return stats


def _load_meta(meta: Path) -> dict[str, Any]:
    if not meta.is_file():
        return {"meta_exists": False, "meta_keys": []}
    try:
        payload = json.loads(meta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"meta_exists": True, "meta_parse_error": str(exc), "meta_keys": []}
    if isinstance(payload, dict):
        return {
            "meta_exists": True,
            "meta_keys": sorted(str(key) for key in payload.keys()),
            "meta_kernel_count": len(payload.get("kernels", [])) if isinstance(payload.get("kernels"), list) else None,
            "meta_unsafe_syms_gep_count": payload.get("unsafe_syms_gep_count"),
        }
    return {"meta_exists": True, "meta_keys": [], "meta_payload_type": type(payload).__name__}


def _classify_ptxas(stdout: str, stderr: str, returncode: int | None, timed_out: bool) -> tuple[str, str]:
    combined = stdout + "\n" + stderr
    if timed_out:
        return ("ptxas_timeout", "split_or_precompile_vortex_ptx_before_cuModuleLoad_retry")
    if returncode == 0:
        return ("ptxas_passed", "retry_cuModuleLoad_with_cubin_or_driver_jit_options")
    if "ptxas fatal" in combined.lower() or "ptxas error" in combined.lower():
        return ("ptxas_failed", "inspect_ptxas_error_before_cuModuleLoad_retry")
    return ("ptxas_failed", "inspect_ptxas_failure_before_cuModuleLoad_retry")


def _run_ptxas_probe(
    root: Path,
    *,
    ptx: Path,
    cubin_out: Path,
    timeout_seconds: float,
    gpu_name: str | None,
) -> dict[str, Any]:
    ptxas = shutil.which("ptxas")
    if ptxas is None:
        return {
            "ptxas_status": "ptxas_missing",
            "ptxas_command": None,
            "ptxas_returncode": None,
            "ptxas_timed_out": False,
            "ptxas_stdout_tail": "",
            "ptxas_stderr_tail": "",
            "next_required_boundary": "install_or_select_cuda_ptxas_for_vortex_ptx_probe",
        }
    cubin_out.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ptxas",
        "-O0",
        "--verbose",
    ]
    if gpu_name:
        command.append(f"-arch={gpu_name}")
    command.extend(
        [
            _display_path(ptx, repo_root=root),
            "-o",
            _display_path(cubin_out, repo_root=root),
        ]
    )
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode: int | None = int(completed.returncode)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout = _timeout_text(exc.stdout)
        stderr = _timeout_text(exc.stderr)
        returncode = None
        timed_out = True
    status, next_boundary = _classify_ptxas(stdout, stderr, returncode, timed_out)
    return {
        "ptxas_status": status,
        "ptxas_command": command,
        "ptxas_returncode": returncode,
        "ptxas_timed_out": timed_out,
        "ptxas_timeout_seconds": timeout_seconds,
        "ptxas_stdout_tail": _sanitize_text(_tail(stdout), repo_root=root),
        "ptxas_stderr_tail": _sanitize_text(_tail(stderr), repo_root=root),
        "ptxas_cubin_exists": cubin_out.is_file(),
        "ptxas_cubin_out": _display_path(cubin_out, repo_root=root),
        "next_required_boundary": next_boundary,
    }


def build_diagnostic(
    repo_root: Path,
    *,
    ptx_path: Path = DEFAULT_PTX,
    meta_path: Path | None = DEFAULT_META,
    run_ptxas: bool = False,
    ptxas_timeout_seconds: float = 30.0,
    gpu_name: str | None = None,
    cubin_out: Path = DEFAULT_CUBIN_OUT,
    case: str = "Vortex:mini:hello",
    surface: str = "rtlmeter_vortex_ptx_module_load_diagnostic",
    missing_ptx_boundary: str = "build_real_vortex_kernel_artifact_for_materialized_runtime_callback",
    ptxas_not_run_boundary: str = "run_bounded_ptxas_probe_for_vortex_cuModuleLoad_jit_timeout",
    ptxas_timeout_boundary: str = "split_or_precompile_vortex_ptx_before_cuModuleLoad_retry",
    ptxas_passed_boundary: str = "retry_cuModuleLoad_with_cubin_or_driver_jit_options",
) -> dict[str, Any]:
    root = repo_root.resolve()
    ptx = ptx_path if ptx_path.is_absolute() else root / ptx_path
    meta = None if meta_path is None else meta_path if meta_path.is_absolute() else root / meta_path
    cubin = cubin_out if cubin_out.is_absolute() else root / cubin_out
    stats = _ptx_stats(ptx)
    meta_report = _load_meta(meta) if meta is not None else {"meta_exists": False, "meta_keys": []}
    inferred_gpu_name = gpu_name or stats.get("ptx_target")
    if not stats["ptx_exists"]:
        status = "ptx_missing"
        next_boundary = missing_ptx_boundary
        ptxas_report = {
            "ptxas_status": "not_run_missing_ptx",
            "ptxas_command": None,
            "ptxas_returncode": None,
            "ptxas_timed_out": False,
        }
    elif run_ptxas:
        ptxas_report = _run_ptxas_probe(
            root,
            ptx=ptx,
            cubin_out=cubin,
            timeout_seconds=ptxas_timeout_seconds,
            gpu_name=inferred_gpu_name if isinstance(inferred_gpu_name, str) else None,
        )
        status = ptxas_report["ptxas_status"]
        next_boundary = ptxas_report["next_required_boundary"]
        if status == "ptxas_timeout":
            next_boundary = ptxas_timeout_boundary
            ptxas_report["next_required_boundary"] = next_boundary
        elif status == "ptxas_passed":
            next_boundary = ptxas_passed_boundary
            ptxas_report["next_required_boundary"] = next_boundary
    else:
        status = "ptx_ready_ptxas_probe_not_run"
        next_boundary = ptxas_not_run_boundary
        ptxas_report = {
            "ptxas_status": "not_run",
            "ptxas_command": [
                "ptxas",
                "-O0",
                "--verbose",
                *( [f"-arch={inferred_gpu_name}"] if inferred_gpu_name else [] ),
                _display_path(ptx, repo_root=root),
                "-o",
                _display_path(cubin, repo_root=root),
            ],
            "ptxas_returncode": None,
            "ptxas_timed_out": False,
            "ptxas_timeout_seconds": ptxas_timeout_seconds,
        }
    return {
        "schema_version": 1,
        "surface": surface,
        "case": case,
        "status": status,
        "ptx_path": _display_path(ptx, repo_root=root),
        "meta_path": _display_path(meta, repo_root=root) if meta is not None else None,
        **stats,
        **meta_report,
        **ptxas_report,
        "ptxas_gpu_name": inferred_gpu_name,
        "next_required_boundary": next_boundary,
        "runtime_authority": False,
        "kernel_execution_observed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "ptx_module_load_diagnostic_is_not_kernel_execution",
            "ptxas_probe_is_not_cpu_vs_hybrid_timing",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ptx", default=DEFAULT_PTX.as_posix())
    parser.add_argument("--meta", default=DEFAULT_META.as_posix())
    parser.add_argument("--no-meta", action="store_true")
    parser.add_argument("--run-ptxas", action="store_true")
    parser.add_argument("--ptxas-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--gpu-name")
    parser.add_argument("--cubin-out", default=DEFAULT_CUBIN_OUT.as_posix())
    parser.add_argument("--case", default="Vortex:mini:hello")
    parser.add_argument("--surface", default="rtlmeter_vortex_ptx_module_load_diagnostic")
    parser.add_argument(
        "--missing-ptx-boundary",
        default="build_real_vortex_kernel_artifact_for_materialized_runtime_callback",
    )
    parser.add_argument(
        "--ptxas-not-run-boundary",
        default="run_bounded_ptxas_probe_for_vortex_cuModuleLoad_jit_timeout",
    )
    parser.add_argument(
        "--ptxas-timeout-boundary",
        default="split_or_precompile_vortex_ptx_before_cuModuleLoad_retry",
    )
    parser.add_argument(
        "--ptxas-passed-boundary",
        default="retry_cuModuleLoad_with_cubin_or_driver_jit_options",
    )
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_ptx_module_load_diagnostic.json")
    args = parser.parse_args(argv)

    report = build_diagnostic(
        Path(args.repo_root),
        ptx_path=Path(args.ptx),
        meta_path=None if args.no_meta else Path(args.meta),
        run_ptxas=args.run_ptxas,
        ptxas_timeout_seconds=args.ptxas_timeout_seconds,
        gpu_name=args.gpu_name,
        cubin_out=Path(args.cubin_out),
        case=args.case,
        surface=args.surface,
        missing_ptx_boundary=args.missing_ptx_boundary,
        ptxas_not_run_boundary=args.ptxas_not_run_boundary,
        ptxas_timeout_boundary=args.ptxas_timeout_boundary,
        ptxas_passed_boundary=args.ptxas_passed_boundary,
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
