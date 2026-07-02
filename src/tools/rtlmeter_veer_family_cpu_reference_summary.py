#!/usr/bin/env python3
"""Summarize VeeR EH1/EH2 RTLMeter CPU reference observables."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


TARGETS = {
    "VeeR-EH1": {
        "case": "VeeR-EH1:default:hello",
        "configuration": "default",
        "test": "hello",
        "default_work_root": Path("artifacts/rtlmeter_veer_eh1_cpu_reference"),
        "default_report": Path("reports/rtlmeter_veer_eh1_cpu_reference_summary.json"),
    },
    "VeeR-EH2": {
        "case": "VeeR-EH2:default:hello",
        "configuration": "default",
        "test": "hello",
        "default_work_root": Path("artifacts/rtlmeter_veer_eh2_cpu_reference"),
        "default_report": Path("reports/rtlmeter_veer_eh2_cpu_reference_summary.json"),
    },
}
FINISHED_RE = re.compile(r"Finished(?:\s+hart(?P<hart>\d+))?\s*:\s*minstret\s*=\s*(?P<minstret>\d+),\s*mcycle\s*=\s*(?P<mcycle>\d+)")


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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_cycles(path: Path) -> int | None:
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    try:
        return int(raw)
    except ValueError:
        return None


def _finished_records(stdout: str) -> list[dict[str, int | None]]:
    records: list[dict[str, int | None]] = []
    for match in FINISHED_RE.finditer(stdout):
        records.append(
            {
                "hart": int(match.group("hart")) if match.group("hart") is not None else None,
                "minstret": int(match.group("minstret")),
                "mcycle": int(match.group("mcycle")),
            }
        )
    return records


def build_summary(repo_root: Path, *, design: str, work_root: Path | None = None) -> dict[str, Any]:
    if design not in TARGETS:
        raise ValueError(f"unsupported design {design!r}; expected one of {', '.join(TARGETS)}")
    root = repo_root.resolve()
    target = TARGETS[design]
    work = _resolve(work_root or target["default_work_root"], repo_root=root)
    configuration = str(target["configuration"])
    test = str(target["test"])
    case = str(target["case"])
    design_config = f"{design}:{configuration}"
    compile_dir = work / design / configuration / "compile-0"
    execute_dir = work / design / configuration / "execute-0" / test
    obj_dir = compile_dir / "obj_dir"
    simulator = obj_dir / "Vsim"
    stdout_path = execute_dir / "_execute" / "stdout.log"
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    verilate_metrics = _nested_metric(_load_json(compile_dir / "_verilate" / "metrics.json"), design_config, "verilate")
    cppbuild_payload = _load_json(compile_dir / "_cppbuild" / "metrics.json")
    cppbuild_metrics = _nested_metric(cppbuild_payload, design_config, "cppbuild")
    compile_metrics = _nested_metric(cppbuild_payload, design_config, "compile")
    execute_metrics = _nested_metric(_load_json(execute_dir / "_execute" / "metrics.json"), case, "execute")
    statuses = {
        "files": _status_ok(compile_dir / "_files" / "status"),
        "verilate": _status_ok(compile_dir / "_verilate" / "status"),
        "cppbuild": _status_ok(compile_dir / "_cppbuild" / "status"),
        "execute_files": _status_ok(execute_dir / "_files" / "status"),
        "execute": _status_ok(execute_dir / "_execute" / "status"),
        "post_hook": _status_ok(execute_dir / "_postHook" / "status"),
    }
    cycles_file = _parse_cycles(execute_dir / "_rtlmeter_cycles.txt")
    stdout_test_passed = "TEST_PASSED" in stdout or "TEST PASSED" in stdout
    finish_observed = "Verilog $finish" in stdout
    records = _finished_records(stdout)
    passed = all(statuses.values()) and stdout_test_passed and finish_observed and cycles_file is not None
    return {
        "schema_version": 1,
        "surface": "rtlmeter_veer_family_cpu_reference_summary",
        "status": "cpu_reference_passed" if passed else "cpu_reference_incomplete",
        "case": case,
        "design": design,
        "configuration": configuration,
        "test": test,
        "work_root": _display_path(work, repo_root=root),
        "compile_dir": _display_path(compile_dir, repo_root=root),
        "execute_dir": _display_path(execute_dir, repo_root=root),
        "simulator": _display_path(simulator, repo_root=root) if simulator.is_file() else None,
        "statuses": statuses,
        "stdout_test_passed": stdout_test_passed,
        "finish_observed": finish_observed,
        "finished_records": records,
        "rtlmeter_cycles": cycles_file,
        "normalized_stdout_sha256": _sha256_text(stdout),
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
            "cpu_reference_observables_ready": passed,
            "stdout_TEST_PASSED_observed": stdout_test_passed,
            "rtlmeter_cycles_file_observed": cycles_file is not None,
            "rtlmeter_post_hook_passed": statuses["post_hook"],
            "still_missing_for_measurement": [
                "reviewed_root_field_offsets",
                "reviewed_sidecar_executable",
                "sidecar_stdout_cycles_comparison",
                "cpu_vs_hybrid_timing_report",
            ],
        },
        "non_claims": [
            "not_hybrid_execution",
            "not_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--design", required=True, choices=sorted(TARGETS))
    parser.add_argument("--work-root")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out")
    args = parser.parse_args(argv)
    target = TARGETS[args.design]
    try:
        summary = build_summary(
            Path(args.repo_root),
            design=args.design,
            work_root=Path(args.work_root) if args.work_root else target["default_work_root"],
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.write_report:
        report_path = Path(args.report_out) if args.report_out else target["default_report"]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
