#!/usr/bin/env python3
"""Measure Vortex mini:hello CPU-vs-hybrid wall time after observable authority."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke import (
    DEFAULT_VSIM,
    run_smoke,
)


DEFAULT_CPU_REFERENCE_REPORT = Path("reports/rtlmeter_vortex_cpu_reference_summary.json")
DEFAULT_MODULE = Path("artifacts/rtlmeter_vortex_vlgpugen_std_ref_fix_probe/vl_eval_batch_gpu.cubin")
CASE = "Vortex:mini:hello"


def _resolve(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


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


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def build_timing_report(
    repo_root: Path,
    *,
    cpu_reference_report: Path = DEFAULT_CPU_REFERENCE_REPORT,
    vsim: Path = DEFAULT_VSIM,
    module: Path = DEFAULT_MODULE,
    repeats: int = 3,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    root = repo_root.resolve()
    cpu_path = _resolve(cpu_reference_report, repo_root=root)
    module_path = _resolve(module, repo_root=root)
    cpu = _load_json(cpu_path)
    cpu_metrics = cpu.get("metrics") if isinstance(cpu, dict) and isinstance(cpu.get("metrics"), dict) else {}
    cpu_elapsed = cpu_metrics.get("execute_elapsed_s") if isinstance(cpu_metrics, dict) else None
    cpu_ready = (
        isinstance(cpu, dict)
        and cpu.get("status") == "cpu_reference_passed"
        and cpu.get("cpu_reference_ready_for_hybrid_compare") is True
        and isinstance(cpu_elapsed, (int, float))
        and cpu_elapsed > 0
    )
    if repeats < 1:
        repeats = 1

    runs: list[dict[str, Any]] = []
    for index in range(repeats):
        start = time.perf_counter()
        smoke = run_smoke(root, vsim=vsim, module=module_path, timeout_seconds=timeout_seconds)
        elapsed = time.perf_counter() - start
        runs.append(
            {
                "index": index,
                "elapsed_s": elapsed,
                "status": smoke.get("status"),
                "returncode": smoke.get("returncode"),
                "runtime_authority": smoke.get("runtime_authority"),
                "authority_source": smoke.get("authority_source"),
                "root_storage_relocation_count": smoke.get("root_storage_relocation_count"),
                "root_storage_kernel_last_stage": smoke.get("root_storage_kernel_last_stage"),
            }
        )

    passed_runs = [
        run
        for run in runs
        if run.get("status") == "passed"
        and run.get("returncode") == 0
        and run.get("runtime_authority") is True
    ]
    hybrid_elapsed_values = [
        float(run["elapsed_s"])
        for run in passed_runs
        if isinstance(run.get("elapsed_s"), (int, float))
    ]
    hybrid_wall_s_median = _median(hybrid_elapsed_values)
    correctness_passed = len(passed_runs) == len(runs)
    timing_measured = cpu_ready and correctness_passed and hybrid_wall_s_median is not None
    hybrid_vs_cpu_ratio = (
        hybrid_wall_s_median / float(cpu_elapsed)
        if timing_measured and isinstance(cpu_elapsed, (int, float)) and cpu_elapsed > 0
        else None
    )
    cpu_vs_hybrid_speedup = (
        float(cpu_elapsed) / hybrid_wall_s_median
        if timing_measured and hybrid_wall_s_median and hybrid_wall_s_median > 0
        else None
    )
    speedup_claimed = bool(cpu_vs_hybrid_speedup is not None and cpu_vs_hybrid_speedup > 1.0)

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_timing",
        "status": "passed" if timing_measured else "failed",
        "case": CASE,
        "cpu_reference_report": _display_path(cpu_path, repo_root=root),
        "vsim": _display_path(_resolve(vsim, repo_root=root), repo_root=root),
        "module": _display_path(module_path, repo_root=root),
        "repeats": repeats,
        "cpu_reference_ready": cpu_ready,
        "cpu_elapsed_s": cpu_elapsed,
        "cpu_execute_clocks": cpu_metrics.get("execute_clocks") if isinstance(cpu_metrics, dict) else None,
        "hybrid_wall_s_median": hybrid_wall_s_median,
        "hybrid_wall_s_min": min(hybrid_elapsed_values) if hybrid_elapsed_values else None,
        "hybrid_wall_s_max": max(hybrid_elapsed_values) if hybrid_elapsed_values else None,
        "hybrid_vs_cpu_ratio": hybrid_vs_cpu_ratio,
        "cpu_vs_hybrid_speedup": cpu_vs_hybrid_speedup,
        "correctness_passed": correctness_passed,
        "timing_measured": timing_measured,
        "runtime_authority": correctness_passed,
        "authority_source": (
            passed_runs[0].get("authority_source") if passed_runs else None
        ),
        "speedup_claimed": speedup_claimed,
        "runs": runs,
        "non_claims": [
            "single_vortex_mini_hello_wall_time_not_broad_gpu_usefulness",
            "not_eh1_or_eh2_measurement",
        ]
        + ([] if speedup_claimed else ["not_speedup_or_usefulness_claim"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--cpu-reference-report", default=DEFAULT_CPU_REFERENCE_REPORT.as_posix())
    parser.add_argument("--vsim", default=DEFAULT_VSIM.as_posix())
    parser.add_argument("--module", default=DEFAULT_MODULE.as_posix())
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_timing.json")
    args = parser.parse_args(argv)

    report = build_timing_report(
        Path(args.repo_root),
        cpu_reference_report=Path(args.cpu_reference_report),
        vsim=Path(args.vsim),
        module=Path(args.module),
        repeats=args.repeats,
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
