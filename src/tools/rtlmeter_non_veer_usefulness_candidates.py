"""Summarize non-VeeR RTLMeter GPU usefulness candidates.

This helper intentionally separates existing measured evidence from candidate
descriptors. NVDLA has scoped hybrid timing evidence in this repository; Vortex
currently has RTLMeter descriptor coverage but no CPU-vs-hybrid measurement.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from rtlmeter_vortex_first_gate_readiness import build_readiness as build_vortex_readiness


NVDLA_GATE_PATHS = [
    Path("records/scaling_gates/nvdla_cmac_core_mac_minimal_build_run_compare_gate.json"),
    Path("records/scaling_gates/nvdla_cmac_core_mac_template_shape_expansion_gate.json"),
    Path("records/scaling_gates/neural_network_rtl_nvdla_cmac_a2cacc_first_hybrid_benchmark_gate.json"),
]


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _load_yaml(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected YAML object")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _descriptor_summary(path: Path, *, repo_root: Path) -> dict[str, Any]:
    descriptor = _load_yaml(path)
    compile_section = descriptor.get("compile")
    execute_section = descriptor.get("execute")
    configurations = descriptor.get("configurations")
    compile_map = compile_section if isinstance(compile_section, Mapping) else {}
    execute_map = execute_section if isinstance(execute_section, Mapping) else {}
    config_map = configurations if isinstance(configurations, Mapping) else {}

    common_tests = execute_map.get("tests")
    tests = sorted(common_tests) if isinstance(common_tests, Mapping) else []
    config_tests: dict[str, list[str]] = {}
    for config_name, config_value in config_map.items():
        if not isinstance(config_value, Mapping):
            continue
        config_execute = config_value.get("execute")
        if not isinstance(config_execute, Mapping):
            continue
        tests_map = config_execute.get("tests")
        if isinstance(tests_map, Mapping):
            config_tests[str(config_name)] = sorted(str(name) for name in tests_map)

    return {
        "descriptor": _display_path(path, repo_root=repo_root),
        "top_module": compile_map.get("topModule"),
        "main_clock": compile_map.get("mainClock"),
        "verilog_source_count": len(compile_map.get("verilogSourceFiles", []) or []),
        "cpp_source_count": len(compile_map.get("cppSourceFiles", []) or []),
        "common_tests": tests,
        "configuration_tests": config_tests,
        "configurations": sorted(str(name) for name in config_map),
    }


def _measured_shapes_from_gate(gate: Mapping[str, Any]) -> list[dict[str, Any]]:
    shapes: list[dict[str, Any]] = []
    measured_shape = gate.get("measured_shape")
    if isinstance(measured_shape, Mapping):
        shapes.append(dict(measured_shape))
    measured_shapes = gate.get("measured_shapes")
    if isinstance(measured_shapes, list):
        shapes.extend(dict(item) for item in measured_shapes if isinstance(item, Mapping))
    result = gate.get("result")
    if isinstance(result, Mapping):
        result_shapes = result.get("measured_shapes")
        if isinstance(result_shapes, list):
            shapes.extend(dict(item) for item in result_shapes if isinstance(item, Mapping))
    return shapes


def _shape_record(shape: Mapping[str, Any], *, source: str, target: str) -> dict[str, Any]:
    cpu_ms = _number(shape.get("cpu_elapsed_ms"))
    wall_ms = _number(shape.get("hybrid_wall_time_ms"))
    kernel_ms = _number(shape.get("hybrid_gpu_kernel_time_ms_total"))
    wall_speedup = _number(shape.get("cpu_to_hybrid_wall_speedup_ratio"))
    if wall_speedup is None and cpu_ms is not None and wall_ms not in (None, 0):
        wall_speedup = cpu_ms / wall_ms
    kernel_speedup = _number(shape.get("cpu_to_gpu_kernel_speedup_ratio"))
    if kernel_speedup is None and cpu_ms is not None and kernel_ms not in (None, 0):
        kernel_speedup = cpu_ms / kernel_ms
    nstates = shape.get("nstates")
    steps = shape.get("steps")
    shape_name = shape.get("shape")
    if not isinstance(shape_name, str) and isinstance(nstates, int) and isinstance(steps, int):
        shape_name = f"{nstates}x{steps}"

    return {
        "source": source,
        "target": target,
        "name": shape.get("name"),
        "shape": shape_name,
        "nstates": nstates,
        "steps": steps,
        "coverage_output_equivalence_passed": shape.get("coverage_output_equivalence_passed"),
        "coverage_output_mismatch_count": shape.get("coverage_output_mismatch_count"),
        "cpu_elapsed_ms": cpu_ms,
        "hybrid_wall_time_ms": wall_ms,
        "hybrid_gpu_kernel_time_ms_total": kernel_ms,
        "cpu_to_hybrid_wall_speedup_ratio": wall_speedup,
        "cpu_to_gpu_kernel_speedup_ratio": kernel_speedup,
    }


def _nvdla_evidence(repo_root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for rel_path in NVDLA_GATE_PATHS:
        path = repo_root / rel_path
        if not path.exists():
            continue
        gate = _load_json(path)
        target = str(gate.get("target_full_name") or gate.get("target") or "NVDLA")
        source = _display_path(path, repo_root=repo_root)
        for shape in _measured_shapes_from_gate(gate):
            records.append(_shape_record(shape, source=source, target=target))

    passed = [record for record in records if record.get("coverage_output_equivalence_passed") is True]
    favorable = [
        record
        for record in passed
        if (record.get("cpu_to_hybrid_wall_speedup_ratio") or 0) > 1.0
    ]
    best_wall = max(
        favorable,
        key=lambda record: record.get("cpu_to_hybrid_wall_speedup_ratio") or 0,
        default=None,
    )
    best_kernel = max(
        favorable,
        key=lambda record: record.get("cpu_to_gpu_kernel_speedup_ratio") or 0,
        default=None,
    )
    return {
        "status": "measured" if records else "missing_measured_evidence",
        "measured_shape_count": len(records),
        "coverage_passed_shape_count": len(passed),
        "gpu_favorable_shape_count": len(favorable),
        "best_wall_speedup": best_wall,
        "best_kernel_speedup": best_kernel,
        "records": records,
        "classification": (
            "best_non_veer_measured_usefulness_candidate"
            if favorable
            else "candidate_without_favorable_measurement"
        ),
    }


def build_summary(repo_root: Path) -> dict[str, Any]:
    nvdla_descriptor = _descriptor_summary(
        repo_root / "third_party/rtlmeter/designs/NVDLA/descriptor.yaml",
        repo_root=repo_root,
    )
    vortex_descriptor = _descriptor_summary(
        repo_root / "third_party/rtlmeter/designs/Vortex/descriptor.yaml",
        repo_root=repo_root,
    )
    nvdla = _nvdla_evidence(repo_root)
    vortex_readiness = build_vortex_readiness(repo_root)
    vortex_bridge_ready = isinstance(vortex_readiness.get("dpi_memory_bridge_review"), dict)
    vortex_status = (
        "fail_closed_first_gate_no_cpu_vs_hybrid_measurement"
        if vortex_bridge_ready
        else "descriptor_only_no_cpu_vs_hybrid_measurement"
    )
    vortex = {
        "status": vortex_status,
        "descriptor": vortex_descriptor,
        "first_gate_readiness": vortex_readiness,
        "suggested_first_measurement": "Vortex:mini:hello_build_run_compare_then_sgemm_or_saxpy",
        "classification": "promising_but_unmeasured_parallel_architecture_candidate",
        "why_not_first": [
            "no existing CPU-vs-hybrid report in this repository",
            "requires first source-closure/build/run/observable contract",
        ],
    }

    if nvdla["gpu_favorable_shape_count"]:
        recommended_next = "refresh_or_extend_nvdla_cmac_core_mac_repeat_median_before_vortex"
    else:
        recommended_next = "define_vortex_mini_hello_first_build_run_compare"
    vortex_reason = (
        "NVDLA already has scoped coverage-output-equivalent hybrid timing evidence; Vortex has a fail-closed first gate but no CPU-vs-hybrid timing yet."
        if vortex_bridge_ready
        else "NVDLA already has scoped coverage-output-equivalent hybrid timing evidence; Vortex is architecturally interesting but still descriptor-only here."
    )

    return {
        "schema_version": 1,
        "surface": "rtlmeter_non_veer_usefulness_candidates",
        "status": "analyzed",
        "scope": "non_veer_rtlmeter_designs",
        "nvdla": {
            "descriptor": nvdla_descriptor,
            "evidence": nvdla,
        },
        "vortex": vortex,
        "recommendation": {
            "recommended_next": recommended_next,
            "reason": vortex_reason,
            "non_claims": [
                "not_full_nvdla_accelerator_execution",
                "not_vortex_gpu_measurement",
                "not_broad_rtlmeter_speedup_claim",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        repo_root = Path(args.repo_root)
        summary = build_summary(repo_root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
