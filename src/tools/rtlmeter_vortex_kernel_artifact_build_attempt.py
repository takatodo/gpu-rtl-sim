#!/usr/bin/env python3
"""Attempt to build a Vortex GPU kernel artifact and classify the first blocker."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_OBJ_DIR = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir"
)


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def _sanitize_text(text: str, *, repo_root: Path) -> str:
    return text.replace(repo_root.as_posix(), "<repo-root>")


def _classify(output: str, returncode: int | None) -> tuple[str, str]:
    if "LandingPadInst needs to be in a function with a personality" in output:
        return (
            "failed_broken_module_landingpad_personality",
            "fix_vortex_lowered_ir_landingpad_personality_before_kernel_artifact",
        )
    if "LLVM ERROR: Broken module found" in output:
        return (
            "failed_broken_module",
            "fix_vortex_lowered_ir_verifier_errors_before_kernel_artifact",
        )
    if returncode == 0:
        return ("passed", "wire_real_vortex_kernel_artifact_into_materialized_runtime_callback")
    return ("failed", "inspect_vortex_kernel_artifact_build_failure")


def run_attempt(
    repo_root: Path,
    *,
    obj_dir: Path = DEFAULT_OBJ_DIR,
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    root = repo_root.resolve()
    resolved_obj_dir = obj_dir if obj_dir.is_absolute() else root / obj_dir
    command = [
        "python3",
        "src/tools/build_vl_gpu.py",
        _display_path(resolved_obj_dir, repo_root=root),
        "--clang-O",
        "O0",
        "--gpu-opt-level",
        "O0",
        "--emit-ptx-module",
        "--jobs",
        "4",
    ]
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
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        returncode = None
        timed_out = True
    combined = stdout + "\n" + stderr
    status, next_boundary = (
        ("timeout", "reduce_or_slice_vortex_kernel_artifact_build_before_retry")
        if timed_out
        else _classify(combined, returncode)
    )
    ptx = resolved_obj_dir / "vl_batch_gpu.ptx"
    cubin = resolved_obj_dir / "vl_batch_gpu.cubin"
    meta = resolved_obj_dir / "vl_batch_gpu.meta.json"
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_kernel_artifact_build_attempt",
        "status": status,
        "case": "Vortex:mini:hello",
        "obj_dir": _display_path(resolved_obj_dir, repo_root=root),
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout_tail": _sanitize_text(_tail(stdout), repo_root=root),
        "stderr_tail": _sanitize_text(_tail(stderr), repo_root=root),
        "landingpad_personality_error_observed": (
            "LandingPadInst needs to be in a function with a personality" in combined
        ),
        "broken_module_observed": "LLVM ERROR: Broken module found" in combined,
        "ptx_exists": ptx.is_file(),
        "cubin_exists": cubin.is_file(),
        "meta_exists": meta.is_file(),
        "kernel_artifact_ready": cubin.is_file() or ptx.is_file(),
        "next_required_boundary": next_boundary,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "build_attempt_is_not_kernel_execution",
            "build_attempt_is_not_cpu_vs_hybrid_timing",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--obj-dir", default=DEFAULT_OBJ_DIR.as_posix())
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_kernel_artifact_build_attempt.json")
    args = parser.parse_args(argv)
    report = run_attempt(
        Path(args.repo_root),
        obj_dir=Path(args.obj_dir),
        timeout_seconds=args.timeout_seconds,
    )
    if args.write_report:
        out = Path(args.report_out)
        if not out.is_absolute():
            out = Path(args.repo_root) / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
