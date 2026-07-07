#!/usr/bin/env python3
"""Build the Vortex mini:hello RTLMeter sidecar context JSON."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SOURCE_CLOSURE_REPORT = Path("reports/rtlmeter_vortex_source_closure.json")
TARGET = "rtlmeter_vortex_mini_hello"
CASE = "Vortex:mini:hello"
AUTHORITY_REGISTRY = "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json"
ARTIFACT_ROOT = "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare"


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _paths(payload: object, field: str) -> list[str]:
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"source closure report is missing {field}")
    paths = []
    for index, item in enumerate(payload):
        if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
            raise ValueError(f"source closure report {field}[{index}] is missing path")
        paths.append(str(item["path"]))
    return paths


def _filelist_entries(payload: object, prefix: str, field: str) -> list[str]:
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"source closure report is missing {field}")
    entries = []
    for index, item in enumerate(payload):
        if not isinstance(item, Mapping) or not isinstance(item.get("descriptor_path"), str):
            raise ValueError(f"source closure report {field}[{index}] is missing descriptor_path")
        entries.append(f"{prefix}/{Path(str(item['descriptor_path'])).name}")
    return entries


def build_context(repo_root: Path, *, source_closure_report: Path = SOURCE_CLOSURE_REPORT) -> dict[str, Any]:
    report_path = source_closure_report if source_closure_report.is_absolute() else repo_root / source_closure_report
    source = _load_json(report_path)
    if source.get("status") != "descriptor_source_closure_complete" or source.get("all_sources_exist") is not True:
        raise ValueError("Vortex descriptor source closure must be complete before building sidecar context")

    source_files = _paths(source.get("source_files"), "source_files")
    include_files = _paths(source.get("include_files"), "include_files")
    filelist_entries = [
        *_filelist_entries(source.get("source_files"), "verilogSourceFiles", "source_files"),
        *_filelist_entries(source.get("include_files"), "verilogIncludeFiles", "include_files"),
    ]
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_sidecar_context",
        "status": "vortex_sidecar_context_metadata_ready",
        "target": TARGET,
        "mode": "rtlmeter_non_veer_candidate",
        "rtlmeter_case": CASE,
        "template_or_target_registry_entry": AUTHORITY_REGISTRY,
        "source_gate_or_manifest_ref": "reports/rtlmeter_vortex_first_gate_readiness.json",
        "host_probe_metadata": {
            "top_module": "tb",
            "main_clock": "tb.clk",
            "status": "captured_from_vortex_descriptor",
        },
        "coverage_output_target": "rtlmeter_stdout_and_cycles_equivalence",
        "coverage_manifest": {"outputs": ["normalized_stdout", "rtlmeter_cycles"]},
        "state_and_report_path_rules": {
            "artifact_root": ARTIFACT_ROOT,
            "report": "reports/rtlmeter_vortex_mini_hello_cpu_gpu_compare.json",
            "status": "path_rules_declared_not_executed",
        },
        "compare_labels": {
            "cpu": "rtlmeter_cpu_reference",
            "gpu": "rtlmeter_vortex_sidecar_candidate",
        },
        "source_closure": {
            "status": "complete",
            "authority": "reviewed_hybrid_execution_source_closure",
            "authority_scope": "rtlmeter_stdout_cycles_sidecar_runner",
            "target": TARGET,
            "mode": "rtlmeter_non_veer_candidate",
            "rtlmeter_case": CASE,
            "source_gate_or_manifest_ref": "reports/rtlmeter_vortex_first_gate_readiness.json",
            "source_files": source_files,
            "include_files": include_files,
            "filelist_entries": filelist_entries,
            "observables": ["normalized_stdout", "rtlmeter_cycles"],
            "runner_strategy": "rtlmeter_stdout_cycles_direct_wrapper",
            "host_probe_contract_status": "reviewed_for_rtlmeter_sidecar",
            "cpu_as_gpu_fallback_allowed": False,
            "review_evidence": {
                "reviewed": True,
                "review_ref": "reports/rtlmeter_vortex_first_gate_readiness.json",
            },
        },
        "execution_authority": False,
        "sidecar_execution_invoked": False,
        "measurement_performed": False,
        "non_claims": [
            "context metadata does not execute Verilator or the sidecar",
            "context metadata does not make the authority registry source closure complete",
            "context metadata does not prove Vortex correctness, timing, or speedup",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-closure-report", default=SOURCE_CLOSURE_REPORT.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out")
    args = parser.parse_args(argv)

    context = build_context(Path(args.repo_root), source_closure_report=Path(args.source_closure_report))
    if args.write_report:
        if not args.report_out:
            parser.error("--write-report requires --report-out")
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(context, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
