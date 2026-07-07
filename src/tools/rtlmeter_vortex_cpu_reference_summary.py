#!/usr/bin/env python3
"""Summarize the Vortex mini:hello RTLMeter CPU reference run."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DEFAULT_WORK_ROOT = Path("artifacts/rtlmeter_vortex_mini_hello_cpu_reference")
CASE = "Vortex:mini:hello"
DESIGN_CONFIG = "Vortex:mini"


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _status_ok(path: Path) -> bool:
    return path.is_file() and path.read_text(encoding="utf-8").strip() == "success"


def _nested_metric(payload: Mapping[str, Any], case: str, step: str) -> Mapping[str, Any]:
    case_payload = payload.get(case)
    if not isinstance(case_payload, Mapping):
        return {}
    step_payload = case_payload.get(step)
    return step_payload if isinstance(step_payload, Mapping) else {}


def build_summary(repo_root: Path, *, work_root: Path = DEFAULT_WORK_ROOT) -> dict[str, Any]:
    root = repo_root.resolve()
    work = _resolve(work_root, repo_root=root)
    compile_dir = work / "Vortex" / "mini" / "compile-0"
    execute_dir = work / "Vortex" / "mini" / "execute-0" / "hello"
    obj_dir = compile_dir / "obj_dir"
    simulator = obj_dir / "Vsim"
    execute_stdout_path = execute_dir / "_execute" / "stdout.log"
    execute_stdout = execute_stdout_path.read_text(encoding="utf-8") if execute_stdout_path.is_file() else ""

    verilate_metrics = _nested_metric(_load_json(compile_dir / "_verilate" / "metrics.json"), DESIGN_CONFIG, "verilate")
    cppbuild_metrics = _nested_metric(_load_json(compile_dir / "_cppbuild" / "metrics.json"), DESIGN_CONFIG, "cppbuild")
    compile_metrics = _nested_metric(_load_json(compile_dir / "_cppbuild" / "metrics.json"), DESIGN_CONFIG, "compile")
    execute_metrics = _nested_metric(_load_json(execute_dir / "_execute" / "metrics.json"), CASE, "execute")

    statuses = {
        "files": _status_ok(compile_dir / "_files" / "status"),
        "verilate": _status_ok(compile_dir / "_verilate" / "status"),
        "cppbuild": _status_ok(compile_dir / "_cppbuild" / "status"),
        "execute": _status_ok(execute_dir / "_execute" / "status"),
        "post_hook": _status_ok(execute_dir / "_postHook" / "status"),
    }
    stdout_test_passed = "TEST PASSED" in execute_stdout
    finish_observed = "Verilog $finish" in execute_stdout
    dcr_write_count = execute_stdout.count("DCR write:")
    thread_line_count = execute_stdout.count("Thread")
    passed = all(statuses.values()) and stdout_test_passed and finish_observed

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_cpu_reference_summary",
        "status": "cpu_reference_passed" if passed else "cpu_reference_incomplete",
        "case": CASE,
        "work_root": _display_path(work, repo_root=root),
        "compile_dir": _display_path(compile_dir, repo_root=root),
        "execute_dir": _display_path(execute_dir, repo_root=root),
        "simulator": _display_path(simulator, repo_root=root) if simulator.is_file() else None,
        "statuses": statuses,
        "stdout_test_passed": stdout_test_passed,
        "finish_observed": finish_observed,
        "dcr_write_count": dcr_write_count,
        "thread_line_count": thread_line_count,
        "metrics": {
            "verilate_elapsed_s": verilate_metrics.get("elapsed"),
            "verilate_peak_memory_mb": verilate_metrics.get("memory"),
            "cppbuild_elapsed_s": cppbuild_metrics.get("elapsed"),
            "compile_elapsed_s": compile_metrics.get("elapsed"),
            "compile_peak_memory_mb": compile_metrics.get("memory"),
            "execute_elapsed_s": execute_metrics.get("elapsed"),
            "execute_peak_memory_mb": execute_metrics.get("memory"),
            "execute_clocks": execute_metrics.get("clocks"),
            "execute_speed_khz": execute_metrics.get("speed"),
        },
        "cpu_reference_ready_for_hybrid_compare": passed,
        "readiness_delta": {
            "cpu_reference_exists": passed,
            "stdout_TEST_PASSED_observed": stdout_test_passed,
            "rtlmeter_post_hook_passed": statuses["post_hook"],
            "still_missing_for_measurement": [
                "hybrid_candidate_execution",
                "hybrid_observable_authority",
                "cpu_vs_hybrid_timing_report",
            ],
        },
        "non_claims": [
            "not_hybrid_execution",
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--work-root", default=DEFAULT_WORK_ROOT.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_summary(Path(args.repo_root), work_root=Path(args.work_root))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        report_path = Path(args.report_out)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
