#!/usr/bin/env python3
"""Run the patched Vortex Vsim far enough to validate real-CUDA materialized args."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_VSIM = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/Vsim"
)
STATUS_RE = re.compile(r"rtlmeter_vortex_materialized_runtime_args_probe_status=(?P<status>-?\d+)")
SEQUENCE_FAILURE_RE = re.compile(
    r"rtlmeter_vortex_runtime_sequence_failed stage=(?P<stage>\S+) result=(?P<result>-?\d+) index=(?P<index>-?\d+)"
)
ROOT_KERNEL_FAILURE_RE = re.compile(
    r"rtlmeter_vortex_root_storage_kernel_failed stage=(?P<stage>\S+) result=(?P<result>-?\d+)"
)
ROOT_KERNEL_STAGE_RE = re.compile(
    r"rtlmeter_vortex_root_storage_kernel_stage stage=(?P<stage>\S+)"
)
ROOT_RELOCATION_COUNT_RE = re.compile(
    r"rtlmeter_vortex_root_storage_relocation_count count=(?P<count>\d+)"
)
AUTHORITY_RE = re.compile(
    r"rtlmeter_vortex_runtime_authority "
    r"authority_report_ready=(?P<authority_report_ready>-?\d+) "
    r"authority_passed=(?P<authority_passed>-?\d+) "
    r"authority_source=(?P<authority_source>\S+) "
    r"memory_post_condition_passed=(?P<memory_post_condition_passed>-?\d+) "
    r"stdout_test_passed_observed=(?P<stdout_test_passed_observed>-?\d+) "
    r"observable_export_invoked=(?P<observable_export_invoked>-?\d+) "
    r"kernel_launch_invoked=(?P<kernel_launch_invoked>-?\d+) "
    r"dcr_applied_count=(?P<dcr_applied_count>\d+)"
)


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _snippet(text: str, *, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n<truncated>\n"


def _timeout_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return ""


def _authority_diagnostic(stderr: str) -> dict[str, Any] | None:
    match = AUTHORITY_RE.search(stderr)
    if not match:
        return None
    return {
        "authority_report_ready": int(match.group("authority_report_ready")),
        "authority_passed": int(match.group("authority_passed")),
        "authority_source": match.group("authority_source"),
        "memory_post_condition_passed": int(match.group("memory_post_condition_passed")),
        "stdout_test_passed_observed": int(match.group("stdout_test_passed_observed")),
        "observable_export_invoked": int(match.group("observable_export_invoked")),
        "kernel_launch_invoked": int(match.group("kernel_launch_invoked")),
        "dcr_applied_count": int(match.group("dcr_applied_count")),
    }


def _runtime_authority_ready(passed: bool, diagnostic: dict[str, Any] | None) -> bool:
    return (
        passed
        and isinstance(diagnostic, dict)
        and diagnostic.get("authority_report_ready") == 1
        and diagnostic.get("authority_passed") == 1
        and diagnostic.get("observable_export_invoked") == 1
        and diagnostic.get("kernel_launch_invoked") == 1
        and diagnostic.get("dcr_applied_count") == 9
        and diagnostic.get("authority_source") not in {None, "", "none"}
    )


def run_smoke(
    repo_root: Path,
    *,
    vsim: Path = DEFAULT_VSIM,
    proxy: str = "/bin/true",
    module: Path | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    root = repo_root.resolve()
    vsim_path = vsim if vsim.is_absolute() else root / vsim
    cwd = vsim_path.parent
    env = os.environ.copy()
    env["RTLMETER_VSIM_SIDECAR_PROXY"] = proxy
    module_path = None
    if module is not None:
        resolved_module = module if module.is_absolute() else root / module
        module_path = _display_path(resolved_module, repo_root=root)
        env["RTLMETER_VORTEX_VL_BATCH_GPU_MODULE"] = (
            resolved_module.as_posix() if resolved_module.is_absolute() else module_path
        )

    if not vsim_path.is_file():
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke",
            "status": "missing_vsim",
            "case": "Vortex:mini:hello",
            "vsim": _display_path(vsim_path, repo_root=root),
            "cwd": _display_path(cwd, repo_root=root),
            "proxy": proxy,
            "module": module_path,
            "returncode": None,
            "materialized_runtime_args_probe_passed": False,
            "proxy_handoff_reached": False,
            "materialized_runtime_args_probe_status": None,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
        }

    try:
        completed = subprocess.run(
            ["./" + vsim_path.name],
            cwd=cwd,
            env=env,
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

    match = STATUS_RE.search(stderr)
    probe_status = int(match.group("status")) if match else None
    failure_match = SEQUENCE_FAILURE_RE.search(stderr)
    root_failure_match = ROOT_KERNEL_FAILURE_RE.search(stderr)
    root_stage_trace = [match.group("stage") for match in ROOT_KERNEL_STAGE_RE.finditer(stderr)]
    relocation_match = ROOT_RELOCATION_COUNT_RE.search(stderr)
    relocation_count = int(relocation_match.group("count")) if relocation_match else None
    authority = _authority_diagnostic(stderr)
    root_kernel_failure = (
        {
            "stage": root_failure_match.group("stage"),
            "result": int(root_failure_match.group("result")),
        }
        if root_failure_match
        else None
    )
    sequence_failure = (
        {
            "stage": failure_match.group("stage"),
            "result": int(failure_match.group("result")),
            "index": int(failure_match.group("index")),
        }
        if failure_match
        else None
    )
    passed = returncode == 0 and probe_status is None and not timed_out
    runtime_authority = _runtime_authority_ready(passed, authority)
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke",
        "status": "passed" if passed else "failed",
        "case": "Vortex:mini:hello",
        "vsim": _display_path(vsim_path, repo_root=root),
        "cwd": _display_path(cwd, repo_root=root),
        "proxy": proxy,
        "module": module_path,
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout": _snippet(stdout),
        "stderr": _snippet(stderr),
        "materialized_runtime_args_probe_passed": passed,
        "proxy_handoff_reached": passed,
        "materialized_runtime_args_probe_status": probe_status,
        "runtime_sequence_failure": sequence_failure,
        "runtime_sequence_failed_stage": sequence_failure.get("stage") if sequence_failure else None,
        "runtime_sequence_failed_result": sequence_failure.get("result") if sequence_failure else None,
        "root_storage_kernel_failure": root_kernel_failure,
        "root_storage_kernel_failed_stage": root_kernel_failure.get("stage") if root_kernel_failure else None,
        "root_storage_kernel_failed_result": root_kernel_failure.get("result") if root_kernel_failure else None,
        "root_storage_kernel_stage_trace": root_stage_trace,
        "root_storage_kernel_last_stage": root_stage_trace[-1] if root_stage_trace else None,
        "root_storage_relocation_count": relocation_count,
        "authority_report_ready": authority.get("authority_report_ready") if authority else None,
        "authority_passed": authority.get("authority_passed") if authority else None,
        "authority_source": authority.get("authority_source") if authority else None,
        "memory_post_condition_passed": (
            authority.get("memory_post_condition_passed") if authority else None
        ),
        "stdout_test_passed_observed": authority.get("stdout_test_passed_observed") if authority else None,
        "observable_export_invoked": authority.get("observable_export_invoked") if authority else None,
        "kernel_launch_invoked": authority.get("kernel_launch_invoked") if authority else None,
        "dcr_applied_count": authority.get("dcr_applied_count") if authority else None,
        "runtime_authority": runtime_authority,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "proxy_handoff_to_bin_true_is_not_vortex_kernel_execution"
            if not runtime_authority
            else "runtime_authority_is_not_cpu_vs_hybrid_timing",
            "materialized_runtime_args_smoke_is_not_cpu_vs_hybrid_timing",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--vsim", default=DEFAULT_VSIM.as_posix())
    parser.add_argument("--proxy", default="/bin/true")
    parser.add_argument("--module")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument(
        "--report-out",
        default="reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.json",
    )
    args = parser.parse_args(argv)

    report = run_smoke(
        Path(args.repo_root),
        vsim=Path(args.vsim),
        proxy=args.proxy,
        module=Path(args.module) if args.module else None,
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
