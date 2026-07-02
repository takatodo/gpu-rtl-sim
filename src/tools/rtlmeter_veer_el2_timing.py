#!/usr/bin/env python3
"""Opt-in RTLMeter VeeR-EL2 sidecar timing/usefulness report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from verilator_native_sidecar_make_driver import (
    STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED,
    run_veer_el2_sidecar_execution_bridge,
)
from rtlmeter_stdout_cycles_observables import normalized_rtlmeter_stdout


SURFACE = "rtlmeter_veer_el2_timing"
OPT_IN_ENV = "RTLMETER_VEER_EL2_TIMING_EXECUTE"
DEFAULT_REPORT = "reports/rtlmeter_veer_el2_timing.json"
DEFAULT_CPU_EXECUTE_DIR = "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/VeeR-EL2/default/execute-0/hello"
DEFAULT_SIDECAR_EXECUTE_DIR = "artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/hello"
DEFAULT_STATE_IMAGE = "artifacts/veer_el2_direct_verilator_sidecar_probe/veer_el2_extracted_state_image.json"
DEFAULT_MDIR = "artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir"
DEFAULT_SIDECAR_EXECUTABLE = "src/tools/veer_el2_sidecar_executable.py"
DEFAULT_CPU_PARALLEL_REPORT = "reports/rtlmeter_cpu_parallel_hello_baseline.json"
CASE = "VeeR-EL2:default:hello"
DEFAULT_RTL_METER_POST_FINISH_CYCLES = 1502
DEFAULT_RESET_LAUNCHES = 2
DEFAULT_MAX_PAIR_CYCLE_FUSED_LAUNCHES = 100000
DEFAULT_MIN_BOUNDED_PROGRESS_MCYCLE = 1
DEFAULT_MIN_BOUNDED_PROGRESS_MINSTRET = 1
DEFAULT_MIN_TRACE_EQUIVALENCE_ROWS = 1
DEFAULT_MIN_TRACE_EQUIVALENCE_FIELDS = 1
DEFAULT_BOUNDED_PROJECTION_MIN_PROGRESS_FRACTION = 0.01
DEFAULT_NEGATIVE_USEFULNESS_RATIO_THRESHOLD = 10.0
MATERIALLY_DIFFERENT_DEFINITION_REQUIREMENTS = [
    "resident_execution_many_design_cpu_cycles_per_device_operation",
    "per_state_finish_stdout_cycle_observability",
    "superstep_entry_exit_and_unsupported_side_effect_checks",
    "named_gem_like_or_data_parallel_lowering_candidate_for_llvm_pass_work",
    "mixed_program_cpu_parallel_baseline_comparison_floor",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _display_path(path: str | Path, repo_root: Path) -> str:
    p = Path(path)
    try:
        return p.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>"


def _report_arg_path(path: str | Path, repo_root: Path) -> str:
    p = Path(path)
    if p.is_absolute():
        return _display_path(p, repo_root)
    if ".." in p.parts:
        return "<local-relative-parent-path>"
    return p.as_posix()


def _sanitize_report_value(value: object, repo_root: Path) -> object:
    if isinstance(value, str):
        root_text = repo_root.resolve().as_posix()
        if value.startswith(root_text + "/"):
            return value.replace(root_text + "/", "")
        if value == root_text:
            return "."
        if value.startswith("/"):
            return "<local-absolute-path>"
        return value
    if isinstance(value, list):
        return [_sanitize_report_value(item, repo_root) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_report_value(item, repo_root) for key, item in value.items()}
    return value


def _validated_output_path(path: str | Path, *, required_root: str, default: str) -> tuple[str, list[str]]:
    candidate = Path(str(path))
    errors: list[str] = []
    if candidate.is_absolute():
        errors.append(f"{required_root}_path.absolute")
    if ".." in candidate.parts:
        errors.append(f"{required_root}_path.parent_reference")
    if not candidate.parts or candidate.parts[0] != required_root:
        errors.append(f"{required_root}_path.outside_{required_root}")
    return (default if errors else str(path), errors)


def _load_json(path: Path) -> Mapping[str, object] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else None


def _cpu_metrics(cpu_execute_dir: Path, *, case: str = CASE) -> dict[str, object]:
    metrics = _load_json(cpu_execute_dir / "_execute" / "metrics.json")
    if not isinstance(metrics, Mapping):
        return {"status": "missing_metrics", "path": _display_path(cpu_execute_dir / "_execute" / "metrics.json", _repo_root())}
    case_metrics = metrics.get(case)
    execute = case_metrics.get("execute") if isinstance(case_metrics, Mapping) else None
    if not isinstance(execute, Mapping):
        return {"status": "missing_execute_metrics"}
    return {
        "status": "ready",
        "source": "_execute/metrics.json",
        "elapsed_s": execute.get("elapsed"),
        "user_s": execute.get("user"),
        "system_s": execute.get("system"),
        "memory_mb": execute.get("memory"),
        "rtlmeter_clocks": execute.get("clocks"),
        "rtlmeter_speed_clocks_per_s": execute.get("speed"),
    }


def _observables_from_execute_dir(execute_dir: Path, repo_root: Path) -> dict[str, object]:
    stdout_path = execute_dir / "_execute" / "stdout.log"
    cycles_path = execute_dir / "_rtlmeter_cycles.txt"
    missing = []
    if not stdout_path.is_file():
        missing.append("stdout.log")
    if not cycles_path.is_file():
        missing.append("_rtlmeter_cycles.txt")
    if missing:
        return {"status": "missing_observables", "execute_dir": _display_path(execute_dir, repo_root), "missing": missing}
    stdout = normalized_rtlmeter_stdout(stdout_path.read_text(encoding="utf-8"))
    return {
        "status": "observables_ready",
        "execute_dir": _display_path(execute_dir, repo_root),
        "normalized_stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "rtlmeter_cycles": int(cycles_path.read_text(encoding="utf-8").strip()),
    }


def _cpu_parallel_summary(path: Path, repo_root: Path, *, case: str = CASE) -> dict[str, object]:
    report = _load_json(path)
    if not isinstance(report, Mapping):
        return {"status": "missing", "path": _display_path(path, repo_root)}
    summary = report.get("summary")
    if not isinstance(summary, Mapping):
        return {"status": str(report.get("status", "missing_summary")), "path": _display_path(path, repo_root)}
    cases = report.get("cases")
    case_list = [str(item) for item in cases] if isinstance(cases, list) else []
    duplicate_case_instances = [
        item
        for item in report.get("case_instances", [])
        if isinstance(item, Mapping) and item.get("case") == case
    ] if isinstance(report.get("case_instances"), list) else []
    comparable = bool(case_list) and all(item == case for item in case_list) and len(duplicate_case_instances) >= 2
    return {
        "status": str(report.get("status")),
        "path": _display_path(path, repo_root),
        "cases": case_list,
        "matching_case_instance_count": len(duplicate_case_instances),
        "comparable_to_case": comparable,
        "case_count": summary.get("case_count"),
        "max_workers": summary.get("max_workers"),
        "serial_sum_case_wall_s": summary.get("serial_sum_case_wall_s"),
        "parallel_wall_s": summary.get("parallel_wall_s"),
        "parallel_speedup_vs_serial_sum": summary.get("parallel_speedup_vs_serial_sum"),
        "parallel_efficiency": summary.get("parallel_efficiency"),
        "all_runs_passed": summary.get("all_runs_passed"),
        "all_observables_match": summary.get("all_observables_match"),
    }


def _pair_cycle_launch_count_feasibility(
    *,
    rtlmeter_cycles: object,
    post_finish_cycles: int = DEFAULT_RTL_METER_POST_FINISH_CYCLES,
    reset_launches: int = DEFAULT_RESET_LAUNCHES,
    max_pair_cycle_fused_launches: int = DEFAULT_MAX_PAIR_CYCLE_FUSED_LAUNCHES,
) -> dict[str, object]:
    if not isinstance(rtlmeter_cycles, int):
        return {
            "status": "missing_rtlmeter_cycles",
            "feasible": False,
            "reason": "RTLMeter cycle count is required before estimating current pair-cycle launch count",
        }
    sidecar_clock_cycles = rtlmeter_cycles - post_finish_cycles
    if sidecar_clock_cycles < 1:
        return {
            "status": "invalid_sidecar_clock_cycles",
            "feasible": False,
            "rtlmeter_cycles": rtlmeter_cycles,
            "post_finish_cycles": post_finish_cycles,
            "sidecar_clock_cycles": sidecar_clock_cycles,
            "reason": "RTLMeter cycles must exceed post-finish cycles for this VeeR-EL2 sidecar model",
        }
    estimated_pair_cycle_fusion_launched = sidecar_clock_cycles
    estimated_actual_timed_launches = sidecar_clock_cycles + (2 * (reset_launches + 1))
    feasible = estimated_actual_timed_launches <= max_pair_cycle_fused_launches
    return {
        "status": "passed" if feasible else "blocked_pair_cycle_launch_count",
        "feasible": feasible,
        "model": "resident_pair_cycle_fused_current_runtime",
        "rtlmeter_cycles": rtlmeter_cycles,
        "post_finish_cycles": post_finish_cycles,
        "sidecar_clock_cycles": sidecar_clock_cycles,
        "reset_launches": reset_launches,
        "estimated_pair_cycle_fusion_launched": estimated_pair_cycle_fusion_launched,
        "estimated_actual_timed_launches": estimated_actual_timed_launches,
        "max_pair_cycle_fused_launches": max_pair_cycle_fused_launches,
        "reason": (
            "estimated launch count is within the current bounded timing gate"
            if feasible
            else "estimated launch count is too high for the current per-pair-cycle launch model"
        ),
    }


def build_bounded_progress_summary(
    *,
    report_paths: Sequence[str | Path],
    repo_root: Path | None = None,
    min_mcycle: int = DEFAULT_MIN_BOUNDED_PROGRESS_MCYCLE,
    min_minstret: int = DEFAULT_MIN_BOUNDED_PROGRESS_MINSTRET,
    max_actual_launches: int = DEFAULT_MAX_PAIR_CYCLE_FUSED_LAUNCHES,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    items: list[dict[str, object]] = []
    missing: list[str] = []
    for raw_path in report_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        loaded = _load_json(path)
        display = _display_path(path, root)
        if not isinstance(loaded, Mapping):
            missing.append(display)
            items.append({"path": display, "status": "missing_report", "passed": False})
            continue
        observables = loaded.get("observables")
        timing = loaded.get("run_vl_hybrid_timing")
        parallel = loaded.get("parallel_state_validation")
        pair_cycle = loaded.get("pair_cycle_fusion")
        pair_cycle_loop = loaded.get("pair_cycle_loop_fusion")
        materialized = loaded.get("materialized")
        stdout_trace = loaded.get("stdout_trace")
        mcycle = observables.get("mcycle") if isinstance(observables, Mapping) else None
        minstret = observables.get("minstret") if isinstance(observables, Mapping) else None
        actual_launches = (
            timing.get("gpu_kernel_timed_launch_count")
            if isinstance(timing, Mapping)
            else None
        )
        parallel_match = (
            parallel.get("parallel_state_observables_match")
            if isinstance(parallel, Mapping)
            else None
        )
        finish_marker = (
            observables.get("finish_marker_observed")
            if isinstance(observables, Mapping)
            else None
        )
        passed = (
            loaded.get("status") == "observables_emitted"
            and isinstance(mcycle, int)
            and mcycle >= min_mcycle
            and isinstance(minstret, int)
            and minstret >= min_minstret
            and parallel_match is True
            and isinstance(actual_launches, int)
            and actual_launches <= max_actual_launches
        )
        items.append(
            {
                "path": display,
                "status": str(loaded.get("status")),
                "passed": passed,
                "steps": loaded.get("steps"),
                "sidecar_state_count": loaded.get("sidecar_state_count"),
                "mcycle": mcycle,
                "minstret": minstret,
                "pc_hex": observables.get("pc_hex") if isinstance(observables, Mapping) else None,
                "finish_marker_observed": finish_marker,
                "stdout_stream_reconstructed": (
                    observables.get("stdout_stream_reconstructed")
                    if isinstance(observables, Mapping)
                    else None
                ),
                "stdout_trace_stream_reconstructed": (
                    stdout_trace.get("stdout_stream_reconstructed")
                    if isinstance(stdout_trace, Mapping)
                    else None
                ),
                "stdout_trace_diagnostic": (
                    stdout_trace.get("diagnostic")
                    if isinstance(stdout_trace, Mapping)
                    else None
                ),
                "stdout_trace_rows": (
                    stdout_trace.get("trace_rows") if isinstance(stdout_trace, Mapping) else None
                ),
                "step_trace_disabled": loaded.get("step_trace_disabled"),
                "final_observable_stdout_requested": loaded.get("final_observable_stdout_requested"),
                "gpu_kernel_timed_launch_count": actual_launches,
                "pair_cycle_fusion_launched": (
                    pair_cycle.get("launched") if isinstance(pair_cycle, Mapping) else None
                ),
                "pair_cycle_fusion_fallback": (
                    pair_cycle.get("fallback") if isinstance(pair_cycle, Mapping) else None
                ),
                "pair_cycle_loop_fusion_kernel_launches": (
                    pair_cycle_loop.get("kernel_launches")
                    if isinstance(pair_cycle_loop, Mapping)
                    else None
                ),
                "pair_cycle_loop_fusion_cycles": (
                    pair_cycle_loop.get("cycles") if isinstance(pair_cycle_loop, Mapping) else None
                ),
                "pair_cycle_loop_fusion_fallback": (
                    pair_cycle_loop.get("fallback") if isinstance(pair_cycle_loop, Mapping) else None
                ),
                "dccm_bank_words": (
                    materialized.get("dccm_bank_words") if isinstance(materialized, Mapping) else None
                ),
                "iccm_bank_words": (
                    materialized.get("iccm_bank_words") if isinstance(materialized, Mapping) else None
                ),
                "dccm_bank_skipped_missing_bank": (
                    materialized.get("dccm_bank_skipped_missing_bank")
                    if isinstance(materialized, Mapping)
                    else None
                ),
                "iccm_bank_skipped_missing_bank": (
                    materialized.get("iccm_bank_skipped_missing_bank")
                    if isinstance(materialized, Mapping)
                    else None
                ),
                "dccm_bank_skipped_out_of_range": (
                    materialized.get("dccm_bank_skipped_out_of_range")
                    if isinstance(materialized, Mapping)
                    else None
                ),
                "iccm_bank_skipped_out_of_range": (
                    materialized.get("iccm_bank_skipped_out_of_range")
                    if isinstance(materialized, Mapping)
                    else None
                ),
                "parallel_state_observables_match": parallel_match,
                "parallel_state_matching_count": (
                    parallel.get("parallel_state_matching_count")
                    if isinstance(parallel, Mapping)
                    else None
                ),
            }
        )
    failed = [item["path"] for item in items if item.get("passed") is not True]
    return {
        "schema_version": 1,
        "surface": f"{SURFACE}.bounded_progress_summary",
        "status": "passed" if items and not failed else "incomplete",
        "report_count": len(items),
        "passed_report_count": len(items) - len(failed),
        "min_mcycle": min_mcycle,
        "min_minstret": min_minstret,
        "max_actual_launches": max_actual_launches,
        "reports": items,
        "missing_reports": missing,
        "failed_reports": failed,
        "bounded_progress_evidence": bool(items and not failed),
        "timing_measured": False,
        "gpu_execution_claimed": bool(items and not failed),
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "generated_report_is_source_of_truth": False,
        "interpretation": (
            "bounded reports show reviewed non-hello images advance architectural counters on the GPU sidecar path"
            if items and not failed
            else "one or more bounded reports are missing or do not meet the configured progress thresholds"
        ),
        "non_claims": [
            "bounded progress is not full RTLMeter correctness",
            "bounded progress is not a full-program timing measurement",
            "bounded progress is not a speedup or usefulness claim",
        ],
    }


def _first_matching_serial_result(
    report: Mapping[str, object],
    *,
    case: str,
) -> Mapping[str, object] | None:
    serial_results = report.get("serial_results")
    if not isinstance(serial_results, Sequence) or isinstance(serial_results, (str, bytes)):
        return None
    for result in serial_results:
        if isinstance(result, Mapping) and result.get("case") == case:
            return result
    return None


def build_bounded_projection_usefulness_summary(
    *,
    sidecar_report_path: str | Path,
    cpu_baseline_report_path: str | Path,
    case: str,
    repo_root: Path | None = None,
    min_progress_fraction: float = DEFAULT_BOUNDED_PROJECTION_MIN_PROGRESS_FRACTION,
    negative_ratio_threshold: float = DEFAULT_NEGATIVE_USEFULNESS_RATIO_THRESHOLD,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    sidecar_path = Path(sidecar_report_path)
    cpu_path = Path(cpu_baseline_report_path)
    if not sidecar_path.is_absolute():
        sidecar_path = root / sidecar_path
    if not cpu_path.is_absolute():
        cpu_path = root / cpu_path

    sidecar = _load_json(sidecar_path)
    cpu_report = _load_json(cpu_path)
    sidecar_display = _display_path(sidecar_path, root)
    cpu_display = _display_path(cpu_path, root)
    errors: list[str] = []

    cpu_serial = _first_matching_serial_result(cpu_report, case=case) if isinstance(cpu_report, Mapping) else None
    cpu_observables = cpu_serial.get("observables") if isinstance(cpu_serial, Mapping) else None
    cpu_rtlmeter_cycles = (
        cpu_observables.get("rtlmeter_cycles") if isinstance(cpu_observables, Mapping) else None
    )
    cpu_wall_s = cpu_serial.get("wall_s") if isinstance(cpu_serial, Mapping) else None
    if not isinstance(cpu_report, Mapping):
        errors.append("cpu_baseline_report.missing")
    if not isinstance(cpu_serial, Mapping):
        errors.append("cpu_baseline_report.matching_serial_result_missing")
    if not isinstance(cpu_rtlmeter_cycles, int) or cpu_rtlmeter_cycles <= 0:
        errors.append("cpu_baseline_report.rtlmeter_cycles_missing")
    if not isinstance(cpu_wall_s, (int, float)) or float(cpu_wall_s) <= 0.0:
        errors.append("cpu_baseline_report.wall_s_missing")

    observables = sidecar.get("observables") if isinstance(sidecar, Mapping) else None
    timing = sidecar.get("run_vl_hybrid_timing") if isinstance(sidecar, Mapping) else None
    phases = sidecar.get("phase_timing_s") if isinstance(sidecar, Mapping) else None
    stdout_trace = sidecar.get("stdout_trace") if isinstance(sidecar, Mapping) else None
    pair_cycle_loop = sidecar.get("pair_cycle_loop_fusion") if isinstance(sidecar, Mapping) else None
    resident_pair_cycle = sidecar.get("resident_pair_cycle") if isinstance(sidecar, Mapping) else None
    parallel = sidecar.get("parallel_state_validation") if isinstance(sidecar, Mapping) else None

    gpu_status = sidecar.get("status") if isinstance(sidecar, Mapping) else None
    gpu_mcycle = observables.get("mcycle") if isinstance(observables, Mapping) else None
    gpu_minstret = observables.get("minstret") if isinstance(observables, Mapping) else None
    finish_marker_observed = (
        observables.get("finish_marker_observed") if isinstance(observables, Mapping) else None
    )
    stdout_stream_reconstructed = (
        observables.get("stdout_stream_reconstructed") if isinstance(observables, Mapping) else None
    )
    stdout_trace_reconstructed = (
        stdout_trace.get("stdout_stream_reconstructed") if isinstance(stdout_trace, Mapping) else None
    )
    gpu_kernel_ms_total = (
        timing.get("gpu_kernel_time_ms_total") if isinstance(timing, Mapping) else None
    )
    actual_launches = (
        timing.get("gpu_kernel_timed_launch_count") if isinstance(timing, Mapping) else None
    )
    run_vl_hybrid_wall_s = (
        phases.get("run_vl_hybrid_wall_s") if isinstance(phases, Mapping) else None
    )
    if not isinstance(sidecar, Mapping):
        errors.append("sidecar_report.missing")
    if gpu_status != "observables_emitted":
        errors.append("sidecar_report.status_not_observables_emitted")
    if not isinstance(gpu_mcycle, int) or gpu_mcycle <= 0:
        errors.append("sidecar_report.mcycle_missing")
    if not isinstance(gpu_kernel_ms_total, (int, float)) or float(gpu_kernel_ms_total) <= 0.0:
        errors.append("sidecar_report.gpu_kernel_time_ms_total_missing")
    if not isinstance(run_vl_hybrid_wall_s, (int, float)) or float(run_vl_hybrid_wall_s) <= 0.0:
        errors.append("sidecar_report.run_vl_hybrid_wall_s_missing")

    scale = None
    progress_fraction = None
    projected_gpu_kernel_s = None
    projected_run_vl_hybrid_wall_s = None
    projected_gpu_kernel_vs_cpu_serial_ratio = None
    projected_run_vl_hybrid_wall_vs_cpu_serial_ratio = None
    if (
        isinstance(cpu_rtlmeter_cycles, int)
        and cpu_rtlmeter_cycles > 0
        and isinstance(gpu_mcycle, int)
        and gpu_mcycle > 0
    ):
        scale = float(cpu_rtlmeter_cycles) / float(gpu_mcycle)
        progress_fraction = float(gpu_mcycle) / float(cpu_rtlmeter_cycles)
    if isinstance(gpu_kernel_ms_total, (int, float)) and isinstance(scale, float):
        projected_gpu_kernel_s = (float(gpu_kernel_ms_total) / 1000.0) * scale
    if isinstance(run_vl_hybrid_wall_s, (int, float)) and isinstance(scale, float):
        projected_run_vl_hybrid_wall_s = float(run_vl_hybrid_wall_s) * scale
    if isinstance(cpu_wall_s, (int, float)) and float(cpu_wall_s) > 0.0:
        if isinstance(projected_gpu_kernel_s, float):
            projected_gpu_kernel_vs_cpu_serial_ratio = projected_gpu_kernel_s / float(cpu_wall_s)
        if isinstance(projected_run_vl_hybrid_wall_s, float):
            projected_run_vl_hybrid_wall_vs_cpu_serial_ratio = (
                projected_run_vl_hybrid_wall_s / float(cpu_wall_s)
            )

    bounded_projection_evidence = (
        not errors
        and isinstance(progress_fraction, float)
        and progress_fraction >= min_progress_fraction
        and finish_marker_observed is False
        and stdout_stream_reconstructed is False
        and stdout_trace_reconstructed is False
        and isinstance(projected_gpu_kernel_vs_cpu_serial_ratio, float)
    )
    negative_usefulness_decision = (
        bounded_projection_evidence
        and projected_gpu_kernel_vs_cpu_serial_ratio >= negative_ratio_threshold
    )

    if errors:
        status = "incomplete"
        interpretation = "required CPU baseline or GPU bounded timing fields are missing"
    elif negative_usefulness_decision:
        status = "negative_usefulness_projected"
        interpretation = (
            "bounded GPU timing projects far slower than the matching CPU serial RTLMeter baseline; "
            "this is a reviewed negative-usefulness decision, not a full-program timing result"
        )
    else:
        status = "incomplete"
        interpretation = (
            "bounded projection evidence is present but does not meet the configured progress or negative-ratio threshold"
        )

    return {
        "schema_version": 1,
        "surface": f"{SURFACE}.bounded_projection_usefulness_summary",
        "status": status,
        "case": case,
        "sidecar_report": sidecar_display,
        "cpu_baseline_report": cpu_display,
        "errors": errors,
        "cpu_cycle_source": "serial_results[].observables.rtlmeter_cycles",
        "cpu_rtlmeter_cycles": cpu_rtlmeter_cycles,
        "cpu_serial_wall_s": cpu_wall_s,
        "gpu_status": gpu_status,
        "gpu_mcycle": gpu_mcycle,
        "gpu_minstret": gpu_minstret,
        "gpu_finish_marker_observed": finish_marker_observed,
        "gpu_stdout_stream_reconstructed": stdout_stream_reconstructed,
        "gpu_stdout_trace_stream_reconstructed": stdout_trace_reconstructed,
        "gpu_kernel_time_ms_total": gpu_kernel_ms_total,
        "gpu_actual_timed_launches": actual_launches,
        "run_vl_hybrid_wall_s": run_vl_hybrid_wall_s,
        "progress_fraction_of_cpu_rtlmeter_cycles": progress_fraction,
        "projection_scale_to_cpu_rtlmeter_cycles": scale,
        "projected_gpu_kernel_s_to_cpu_rtlmeter_cycles": projected_gpu_kernel_s,
        "projected_run_vl_hybrid_wall_s_to_cpu_rtlmeter_cycles": projected_run_vl_hybrid_wall_s,
        "projected_gpu_kernel_vs_cpu_serial_ratio": projected_gpu_kernel_vs_cpu_serial_ratio,
        "projected_run_vl_hybrid_wall_vs_cpu_serial_ratio": projected_run_vl_hybrid_wall_vs_cpu_serial_ratio,
        "min_progress_fraction": min_progress_fraction,
        "negative_usefulness_ratio_threshold": negative_ratio_threshold,
        "pair_cycle_loop_fusion_kernel_launches": (
            pair_cycle_loop.get("kernel_launches") if isinstance(pair_cycle_loop, Mapping) else None
        ),
        "pair_cycle_loop_fusion_cycles": (
            pair_cycle_loop.get("cycles") if isinstance(pair_cycle_loop, Mapping) else None
        ),
        "pair_cycle_loop_fusion_fallback": (
            pair_cycle_loop.get("fallback") if isinstance(pair_cycle_loop, Mapping) else None
        ),
        "pair_cycle_loop_fusion_chunk": (
            pair_cycle_loop.get("chunk") if isinstance(pair_cycle_loop, Mapping) else None
        ),
        "resident_pair_cycle_launched": (
            resident_pair_cycle.get("launched") if isinstance(resident_pair_cycle, Mapping) else None
        ),
        "resident_pair_cycle_fallback": (
            resident_pair_cycle.get("fallback") if isinstance(resident_pair_cycle, Mapping) else None
        ),
        "parallel_state_observables_match": (
            parallel.get("parallel_state_observables_match") if isinstance(parallel, Mapping) else None
        ),
        "bounded_projection_evidence": bounded_projection_evidence,
        "negative_usefulness_decision": negative_usefulness_decision,
        "timing_measured": False,
        "bounded_timing_measured": bounded_projection_evidence,
        "full_program_timing_measured": False,
        "gpu_execution_claimed": bool(isinstance(sidecar, Mapping) and gpu_status == "observables_emitted"),
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "generated_report_is_source_of_truth": False,
        "interpretation": interpretation,
        "non_claims": [
            "bounded projection is not full RTLMeter correctness",
            "bounded projection is not full-program GPU timing",
            "bounded projection is not stdout correctness",
            "negative usefulness does not imply every possible future GPU implementation is slow",
            "no speedup or positive usefulness claim is made",
        ],
    }


def build_mixed_state_gpu_cpu_summary(
    *,
    sidecar_report_path: str | Path,
    cpu_baseline_report_path: str | Path,
    repo_root: Path | None = None,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    sidecar_path = Path(sidecar_report_path)
    cpu_path = Path(cpu_baseline_report_path)
    if not sidecar_path.is_absolute():
        sidecar_path = root / sidecar_path
    if not cpu_path.is_absolute():
        cpu_path = root / cpu_path
    sidecar = _load_json(sidecar_path)
    cpu = _load_json(cpu_path)
    errors: list[str] = []
    if not isinstance(sidecar, Mapping):
        errors.append("sidecar_report.missing")
        sidecar = {}
    if not isinstance(cpu, Mapping):
        errors.append("cpu_baseline_report.missing")
        cpu = {}

    materialized = sidecar.get("materialized") if isinstance(sidecar, Mapping) else None
    per_state = materialized.get("per_state") if isinstance(materialized, Mapping) else None
    state_images = sidecar.get("state_images") if isinstance(sidecar, Mapping) else None
    timing = sidecar.get("run_vl_hybrid_timing") if isinstance(sidecar, Mapping) else None
    phases = sidecar.get("phase_timing_s") if isinstance(sidecar, Mapping) else None
    parallel_state_validation = (
        sidecar.get("parallel_state_validation") if isinstance(sidecar, Mapping) else None
    )
    cpu_summary = cpu.get("summary") if isinstance(cpu, Mapping) else None
    cpu_cases = cpu.get("cases") if isinstance(cpu, Mapping) else None
    cpu_comparison = cpu.get("comparison") if isinstance(cpu, Mapping) else None

    mixed_state_preload = (
        isinstance(materialized, Mapping)
        and materialized.get("mixed_state_preload") is True
        and isinstance(per_state, list)
        and len(per_state) > 1
    )
    if sidecar.get("status") != "observables_emitted":
        errors.append("sidecar_report.status_not_observables_emitted")
    if not mixed_state_preload:
        errors.append("sidecar_report.mixed_state_preload_missing")
    if sidecar.get("init_replication_mode") != "host_uploaded_concatenated_state_images":
        errors.append("sidecar_report.concatenated_init_upload_missing")
    if not isinstance(cpu_summary, Mapping) or cpu_summary.get("all_runs_passed") is not True:
        errors.append("cpu_baseline_report.not_all_runs_passed")
    if not isinstance(cpu_summary, Mapping) or cpu_summary.get("all_observables_match") is not True:
        errors.append("cpu_baseline_report.observables_not_matched")

    gpu_program_preloads = (
        materialized.get("program_preloads")
        if isinstance(materialized, Mapping) and isinstance(materialized.get("program_preloads"), list)
        else []
    )
    gpu_state_count = sidecar.get("sidecar_state_count") if isinstance(sidecar, Mapping) else None
    cpu_case_count = cpu_summary.get("case_count") if isinstance(cpu_summary, Mapping) else None
    if isinstance(cpu_cases, list) and gpu_program_preloads and len(cpu_cases) != len(gpu_program_preloads):
        errors.append("cpu_gpu_program_count_mismatch")
    if isinstance(gpu_state_count, int) and isinstance(cpu_case_count, int) and gpu_state_count != cpu_case_count:
        errors.append("cpu_gpu_state_case_count_mismatch")

    gpu_wall_s = phases.get("run_vl_hybrid_wall_s") if isinstance(phases, Mapping) else None
    gpu_kernel_ms = timing.get("gpu_kernel_time_ms_total") if isinstance(timing, Mapping) else None
    cpu_parallel_wall_s = cpu_summary.get("parallel_wall_s") if isinstance(cpu_summary, Mapping) else None
    gpu_wall_vs_cpu_parallel_ratio = (
        float(gpu_wall_s) / float(cpu_parallel_wall_s)
        if isinstance(gpu_wall_s, (int, float))
        and isinstance(cpu_parallel_wall_s, (int, float))
        and float(cpu_parallel_wall_s) > 0.0
        else None
    )
    state_observables = (
        parallel_state_validation.get("state_observables")
        if isinstance(parallel_state_validation, Mapping)
        else None
    )
    per_state_observability_contract = (
        parallel_state_validation.get("per_state_observability_contract")
        if isinstance(parallel_state_validation, Mapping)
        else None
    )
    per_state_stdout_complete = (
        per_state_observability_contract.get("stdout_per_state") is True
        if isinstance(per_state_observability_contract, Mapping)
        else False
    )
    per_state_cycles_complete = (
        per_state_observability_contract.get("rtlmeter_cycles_per_state") is True
        if isinstance(per_state_observability_contract, Mapping)
        else False
    )
    gpu_mcycles: list[int] = []
    if isinstance(state_observables, list):
        for item in state_observables:
            if isinstance(item, Mapping) and isinstance(item.get("mcycle"), int) and int(item["mcycle"]) > 0:
                gpu_mcycles.append(int(item["mcycle"]))
    cpu_parallel_cycles: list[int] = []
    if isinstance(cpu_comparison, list):
        for item in cpu_comparison:
            if (
                isinstance(item, Mapping)
                and isinstance(item.get("parallel_cycles"), int)
                and int(item["parallel_cycles"]) > 0
            ):
                cpu_parallel_cycles.append(int(item["parallel_cycles"]))
    min_gpu_mcycle = min(gpu_mcycles) if gpu_mcycles else None
    max_cpu_parallel_cycles = max(cpu_parallel_cycles) if cpu_parallel_cycles else None
    projection_scale_to_cpu_max_cycles = (
        float(max_cpu_parallel_cycles) / float(min_gpu_mcycle)
        if isinstance(max_cpu_parallel_cycles, int)
        and isinstance(min_gpu_mcycle, int)
        and min_gpu_mcycle > 0
        else None
    )
    mixed_progress_fraction_of_cpu_max_cycles = (
        float(min_gpu_mcycle) / float(max_cpu_parallel_cycles)
        if isinstance(max_cpu_parallel_cycles, int)
        and isinstance(min_gpu_mcycle, int)
        and max_cpu_parallel_cycles > 0
        else None
    )
    projected_gpu_kernel_s_to_cpu_max_cycles = (
        (float(gpu_kernel_ms) / 1000.0) * projection_scale_to_cpu_max_cycles
        if isinstance(gpu_kernel_ms, (int, float))
        and isinstance(projection_scale_to_cpu_max_cycles, float)
        else None
    )
    projected_gpu_wall_s_to_cpu_max_cycles = (
        float(gpu_wall_s) * projection_scale_to_cpu_max_cycles
        if isinstance(gpu_wall_s, (int, float))
        and isinstance(projection_scale_to_cpu_max_cycles, float)
        else None
    )
    projected_gpu_kernel_vs_cpu_parallel_ratio = (
        projected_gpu_kernel_s_to_cpu_max_cycles / float(cpu_parallel_wall_s)
        if isinstance(projected_gpu_kernel_s_to_cpu_max_cycles, float)
        and isinstance(cpu_parallel_wall_s, (int, float))
        and float(cpu_parallel_wall_s) > 0.0
        else None
    )
    projected_gpu_wall_vs_cpu_parallel_ratio = (
        projected_gpu_wall_s_to_cpu_max_cycles / float(cpu_parallel_wall_s)
        if isinstance(projected_gpu_wall_s_to_cpu_max_cycles, float)
        and isinstance(cpu_parallel_wall_s, (int, float))
        and float(cpu_parallel_wall_s) > 0.0
        else None
    )
    passed = not errors
    mixed_state_negative_projection_decision = (
        passed
        and isinstance(mixed_progress_fraction_of_cpu_max_cycles, float)
        and mixed_progress_fraction_of_cpu_max_cycles >= DEFAULT_BOUNDED_PROJECTION_MIN_PROGRESS_FRACTION
        and isinstance(projected_gpu_kernel_vs_cpu_parallel_ratio, float)
        and projected_gpu_kernel_vs_cpu_parallel_ratio >= DEFAULT_NEGATIVE_USEFULNESS_RATIO_THRESHOLD
    )

    status = "incomplete"
    if mixed_state_negative_projection_decision:
        status = "mixed_state_gpu_negative_projection"
    elif passed:
        status = "mixed_state_gpu_smoke_passed"
    recommended_action = (
        "stop_current_gpu_path_or_define_materially_different_implementation"
        if mixed_state_negative_projection_decision
        else (
            "continue_only_after_full_finish_stdout_or_definition_gate"
            if passed
            else "fail_closed_collect_missing_evidence"
        )
    )
    return {
        "schema_version": 1,
        "surface": f"{SURFACE}.mixed_state_gpu_cpu_summary",
        "status": status,
        "recommended_action": recommended_action,
        "sidecar_report": _display_path(sidecar_path, root),
        "cpu_baseline_report": _display_path(cpu_path, root),
        "errors": errors,
        "gpu_status": sidecar.get("status"),
        "gpu_state_count": gpu_state_count,
        "gpu_state_images": _sanitize_report_value(state_images, root),
        "gpu_program_preloads": _sanitize_report_value(gpu_program_preloads, root),
        "gpu_program_sha256s": (
            materialized.get("program_sha256s")
            if isinstance(materialized, Mapping)
            else None
        ),
        "gpu_init_replication_scope": sidecar.get("init_replication_scope"),
        "gpu_init_replication_mode": sidecar.get("init_replication_mode"),
        "gpu_mixed_state_preload": mixed_state_preload,
        "gpu_per_state_materialized": _sanitize_report_value(per_state, root),
        "gpu_parallel_state_validation": _sanitize_report_value(parallel_state_validation, root),
        "gpu_per_state_observability_contract": _sanitize_report_value(
            per_state_observability_contract, root
        ),
        "gpu_per_state_stdout_complete": per_state_stdout_complete,
        "gpu_per_state_cycles_complete": per_state_cycles_complete,
        "gpu_kernel_time_ms_total": gpu_kernel_ms,
        "gpu_run_vl_hybrid_wall_s": gpu_wall_s,
        "gpu_actual_timed_launches": (
            timing.get("gpu_kernel_timed_launch_count") if isinstance(timing, Mapping) else None
        ),
        "gpu_pair_cycle_loop_fusion": (
            timing.get("pair_cycle_loop_fusion") if isinstance(timing, Mapping) else None
        ),
        "cpu_cases": _sanitize_report_value(cpu_cases, root),
        "cpu_case_count": cpu_case_count,
        "cpu_parallel_wall_s": cpu_parallel_wall_s,
        "cpu_serial_sum_case_wall_s": (
            cpu_summary.get("serial_sum_case_wall_s") if isinstance(cpu_summary, Mapping) else None
        ),
        "cpu_parallel_speedup_vs_serial_sum": (
            cpu_summary.get("parallel_speedup_vs_serial_sum") if isinstance(cpu_summary, Mapping) else None
        ),
        "cpu_max_parallel_cycles": max_cpu_parallel_cycles,
        "cpu_all_runs_passed": (
            cpu_summary.get("all_runs_passed") if isinstance(cpu_summary, Mapping) else None
        ),
        "cpu_all_observables_match": (
            cpu_summary.get("all_observables_match") if isinstance(cpu_summary, Mapping) else None
        ),
        "gpu_min_mcycle": min_gpu_mcycle,
        "mixed_progress_fraction_of_cpu_max_cycles": mixed_progress_fraction_of_cpu_max_cycles,
        "projection_scale_to_cpu_max_cycles": projection_scale_to_cpu_max_cycles,
        "projected_gpu_kernel_s_to_cpu_max_cycles": projected_gpu_kernel_s_to_cpu_max_cycles,
        "projected_gpu_wall_s_to_cpu_max_cycles": projected_gpu_wall_s_to_cpu_max_cycles,
        "projected_gpu_kernel_vs_cpu_parallel_ratio": projected_gpu_kernel_vs_cpu_parallel_ratio,
        "projected_gpu_wall_vs_cpu_parallel_ratio": projected_gpu_wall_vs_cpu_parallel_ratio,
        "gpu_wall_vs_cpu_parallel_ratio": gpu_wall_vs_cpu_parallel_ratio,
        "mixed_state_gpu_execution_claimed": passed,
        "mixed_state_negative_projection_decision": mixed_state_negative_projection_decision,
        "materially_different_definition_gate": {
            "required_before_more_gpu_performance_work": mixed_state_negative_projection_decision,
            "requirements": MATERIALLY_DIFFERENT_DEFINITION_REQUIREMENTS,
            "owner": "FC-037 / GitHub #2",
            "current_observability_gap": (
                None
                if per_state_stdout_complete and per_state_cycles_complete
                else "per-state mixed-program stdout/cycle observability is incomplete"
            ),
        },
        "timing_measured": False,
        "bounded_timing_measured": passed,
        "full_program_timing_measured": False,
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "generated_report_is_source_of_truth": False,
        "interpretation": (
            "mixed GPU state preload reached the sidecar path and is paired with the CPU mixed parallel baseline"
            if passed
            else "mixed GPU state preload evidence or CPU mixed baseline evidence is incomplete"
        ),
        "non_claims": [
            "mixed-state smoke is not full RTLMeter correctness",
            "mixed-state smoke is not full-program timing",
            "state0 stdout does not prove stdout correctness for other mixed states",
            "no speedup or positive usefulness claim is made",
        ],
    }


def build_same_window_trace_equivalence_summary(
    *,
    report_paths: Sequence[str | Path],
    repo_root: Path | None = None,
    min_aligned_rows: int = DEFAULT_MIN_TRACE_EQUIVALENCE_ROWS,
    min_compared_fields: int = DEFAULT_MIN_TRACE_EQUIVALENCE_FIELDS,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    items: list[dict[str, object]] = []
    missing: list[str] = []
    for raw_path in report_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        loaded = _load_json(path)
        display = _display_path(path, root)
        if not isinstance(loaded, Mapping):
            missing.append(display)
            items.append({"path": display, "status": "missing_report", "passed": False})
            continue
        aligned_rows = loaded.get("aligned_rows")
        compared_field_count = loaded.get("compared_field_count")
        mismatch_count = loaded.get("total_mismatched_field_observations")
        first_mismatch = loaded.get("first_mismatch")
        passed = (
            loaded.get("status") == "match"
            and isinstance(aligned_rows, int)
            and aligned_rows >= min_aligned_rows
            and isinstance(compared_field_count, int)
            and compared_field_count >= min_compared_fields
            and mismatch_count == 0
            and first_mismatch is None
        )
        range_info = loaded.get("range")
        items.append(
            {
                "path": display,
                "status": str(loaded.get("status")),
                "passed": passed,
                "aligned_rows": aligned_rows,
                "compared_field_count": compared_field_count,
                "total_mismatched_field_observations": mismatch_count,
                "first_mismatch": _sanitize_report_value(first_mismatch, root),
                "alignment": loaded.get("alignment"),
                "gpu_step_start": (
                    range_info.get("gpu_step_start")
                    if isinstance(range_info, Mapping)
                    else None
                ),
                "gpu_step_end": (
                    range_info.get("gpu_step_end")
                    if isinstance(range_info, Mapping)
                    else None
                ),
                "cpu_report": _sanitize_report_value(loaded.get("cpu_report"), root),
                "gpu_trace": _sanitize_report_value(loaded.get("gpu_trace"), root),
                "excluded_fields": _sanitize_report_value(loaded.get("excluded_fields"), root),
            }
        )
    failed = [item["path"] for item in items if item.get("passed") is not True]
    return {
        "schema_version": 1,
        "surface": f"{SURFACE}.same_window_trace_equivalence_summary",
        "status": "passed" if items and not failed else "incomplete",
        "report_count": len(items),
        "passed_report_count": len(items) - len(failed),
        "min_aligned_rows": min_aligned_rows,
        "min_compared_fields": min_compared_fields,
        "reports": items,
        "missing_reports": missing,
        "failed_reports": failed,
        "same_window_trace_equivalence_evidence": bool(items and not failed),
        "timing_measured": False,
        "gpu_execution_claimed": bool(items and not failed),
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "generated_report_is_source_of_truth": False,
        "interpretation": (
            "same-window CPU/GPU trace reports match under the configured row and field thresholds"
            if items and not failed
            else "one or more same-window CPU/GPU trace reports are missing or do not meet the configured match thresholds"
        ),
        "non_claims": [
            "same-window trace equivalence is not full RTLMeter finish evidence",
            "same-window trace equivalence is not stdout correctness",
            "same-window trace equivalence is not a full-program timing measurement",
            "same-window trace equivalence is not a speedup or usefulness claim",
        ],
    }


def _sidecar_run_report(sidecar_execute_dir: Path, repo_root: Path) -> dict[str, object]:
    path = sidecar_execute_dir / "_sidecar" / "veer_el2_sidecar_executable_report.json"
    report = _load_json(path)
    if not isinstance(report, Mapping):
        return {"status": "missing", "path": _display_path(path, repo_root)}
    return {
        "status": str(report.get("status")),
        "path": _display_path(path, repo_root),
        "mapped_fields_cache": _sanitize_report_value(report.get("mapped_fields_cache"), repo_root),
        "run_vl_hybrid_launcher_mode": _sanitize_report_value(report.get("run_vl_hybrid_launcher_mode"), repo_root),
        "run_vl_hybrid_command": _sanitize_report_value(report.get("run_vl_hybrid_command"), repo_root),
        "run_vl_hybrid_timing": _sanitize_report_value(report.get("run_vl_hybrid_timing"), repo_root),
        "phase_timing_s": _sanitize_report_value(report.get("phase_timing_s"), repo_root),
        "resident_patch_schedule": _sanitize_report_value(report.get("resident_patch_schedule"), repo_root),
        "state_local_patch_schedule": _sanitize_report_value(report.get("state_local_patch_schedule"), repo_root),
        "clock_reset_patch": _sanitize_report_value(report.get("clock_reset_patch"), repo_root),
        "observables": _sanitize_report_value(report.get("observables"), repo_root),
        "stdout_trace": _sanitize_report_value(report.get("stdout_trace"), repo_root),
        "sidecar_state_count": _sanitize_report_value(report.get("sidecar_state_count"), repo_root),
        "parallel_state_count": _sanitize_report_value(report.get("parallel_state_count"), repo_root),
        "state_stride_bytes": _sanitize_report_value(report.get("state_stride_bytes"), repo_root),
        "parallel_state_validation": _sanitize_report_value(report.get("parallel_state_validation"), repo_root),
        "init_replication_scope": _sanitize_report_value(report.get("init_replication_scope"), repo_root),
        "init_replication_mode": _sanitize_report_value(report.get("init_replication_mode"), repo_root),
        "patch_drive_scope": _sanitize_report_value(report.get("patch_drive_scope"), repo_root),
        "stdout_trace_state_scope": _sanitize_report_value(report.get("stdout_trace_state_scope"), repo_root),
        "rtlmeter_observable_emit_scope": _sanitize_report_value(report.get("rtlmeter_observable_emit_scope"), repo_root),
        "patch_apply_mode": _sanitize_report_value(report.get("patch_apply_mode"), repo_root),
        "patch_eval_fusion": _sanitize_report_value(report.get("patch_eval_fusion"), repo_root),
        "pair_cycle_fusion": _sanitize_report_value(report.get("pair_cycle_fusion"), repo_root),
        "pair_cycle_loop_fusion": _sanitize_report_value(report.get("pair_cycle_loop_fusion"), repo_root),
        "pair_cycle_state_local_fusion": _sanitize_report_value(
            report.get("pair_cycle_state_local_fusion"), repo_root
        ),
        "resident_pair_cycle": _sanitize_report_value(report.get("resident_pair_cycle"), repo_root),
        "step_trace_copy_mode": _sanitize_report_value(report.get("step_trace_copy_mode"), repo_root),
        "step_trace_disabled": _sanitize_report_value(report.get("step_trace_disabled"), repo_root),
        "final_observable_stdout_requested": _sanitize_report_value(
            report.get("final_observable_stdout_requested"), repo_root
        ),
        "step_trace_filter": _sanitize_report_value(report.get("step_trace_filter"), repo_root),
        "step_trace_field_mode": _sanitize_report_value(report.get("step_trace_field_mode"), repo_root),
    }


def _median(values: Sequence[float]) -> float | None:
    return round(float(statistics.median(values)), 6) if values else None


def _outcome_from_ratio(
    ratio: object,
    *,
    faster: str,
    slower: str,
    insufficient: str,
) -> str:
    if isinstance(ratio, (int, float)) and ratio > 1.0:
        return faster
    if isinstance(ratio, (int, float)) and ratio < 1.0:
        return slower
    return insufficient


def _summarize_samples(
    sample_reports: Sequence[Mapping[str, object]],
    *,
    cpu_elapsed: object,
    parallel_wall: object,
    cpu_parallel_case_count: object = None,
) -> dict[str, object]:
    all_passed = all(sample.get("sidecar_bridge_status") == STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED for sample in sample_reports)
    wall_values = [float(sample["sidecar_wall_s"]) for sample in sample_reports]
    kernel_values: list[float] = []
    kernel_timed_launch_counts: list[int] = []
    kernel_logical_step_counts: list[int] = []
    kernel_ms_per_actual_launch: list[float] = []
    kernel_timing_repeat_counts: list[int] = []
    phase_values: dict[str, list[float]] = {}
    bridge_phase_values: dict[str, list[float]] = {}
    hybrid_stage_timing_values: dict[str, list[float]] = {}
    mapped_cache_status_counts: dict[str, int] = {}
    launcher_mode_counts: dict[str, int] = {}
    sidecar_invocation_mode_counts: dict[str, int] = {}
    sidecar_state_counts: list[int] = []
    init_replication_mode_counts: dict[str, int] = {}
    patch_drive_scope_counts: dict[str, int] = {}
    clock_patch_mode_counts: dict[str, int] = {}
    step_trace_copy_mode_counts: dict[str, int] = {}
    step_trace_filter_counts: dict[str, int] = {}
    step_trace_filter_rows: list[int] = []
    step_trace_filter_capacity: list[int] = []
    resident_patch_records: list[int] = []
    resident_patch_logical_steps: list[int] = []
    state_local_patch_records: list[int] = []
    state_local_patch_logical_steps: list[int] = []
    patch_eval_fusion_mode_counts: dict[str, int] = {}
    patch_eval_fusion_available_counts: dict[str, int] = {}
    patch_eval_fusion_launched: list[int] = []
    patch_eval_fusion_fallback: list[int] = []
    pair_cycle_fusion_mode_counts: dict[str, int] = {}
    pair_cycle_fusion_available_counts: dict[str, int] = {}
    pair_cycle_fusion_launched: list[int] = []
    pair_cycle_fusion_fallback: list[int] = []
    pair_cycle_loop_fusion_mode_counts: dict[str, int] = {}
    pair_cycle_loop_fusion_available_counts: dict[str, int] = {}
    pair_cycle_loop_fusion_kernel_launches: list[int] = []
    pair_cycle_loop_fusion_cycles: list[int] = []
    pair_cycle_loop_fusion_fallback: list[int] = []
    pair_cycle_loop_fusion_chunks: list[int] = []
    pair_cycle_state_local_fusion_mode_counts: dict[str, int] = {}
    pair_cycle_state_local_fusion_available_counts: dict[str, int] = {}
    pair_cycle_state_local_fusion_launched: list[int] = []
    pair_cycle_state_local_fusion_fallback: list[int] = []
    resident_pair_cycle_mode_counts: dict[str, int] = {}
    resident_pair_cycle_launched: list[int] = []
    resident_pair_cycle_fallback: list[int] = []
    parallel_validation_status_counts: dict[str, int] = {}
    for sample in sample_reports:
        bridge_phases = sample.get("sidecar_bridge_phase_timing_s")
        if isinstance(bridge_phases, Mapping):
            for key, value in bridge_phases.items():
                if isinstance(value, (int, float)):
                    bridge_phase_values.setdefault(str(key), []).append(float(value))
        invocation_mode = sample.get("sidecar_executable_invocation_mode")
        if invocation_mode is not None:
            mode = str(invocation_mode)
            sidecar_invocation_mode_counts[mode] = sidecar_invocation_mode_counts.get(mode, 0) + 1
        run_report = sample.get("sidecar_run_report")
        timing = run_report.get("run_vl_hybrid_timing") if isinstance(run_report, Mapping) else None
        if isinstance(timing, Mapping) and timing.get("gpu_kernel_time_ms_total") is not None:
            kernel_values.append(float(timing["gpu_kernel_time_ms_total"]))
            timed_launch_count = timing.get("gpu_kernel_timed_launch_count")
            logical_step_count = timing.get("gpu_kernel_timing_logical_step_count")
            ms_per_actual_launch = timing.get("gpu_kernel_time_ms_per_actual_launch")
            if isinstance(timed_launch_count, int):
                kernel_timed_launch_counts.append(timed_launch_count)
            if isinstance(logical_step_count, int):
                kernel_logical_step_counts.append(logical_step_count)
            timing_repeat_count = timing.get("gpu_kernel_time_repeat_count")
            if isinstance(timing_repeat_count, int):
                kernel_timing_repeat_counts.append(timing_repeat_count)
            if isinstance(ms_per_actual_launch, (int, float)):
                kernel_ms_per_actual_launch.append(float(ms_per_actual_launch))
            stage_timing = timing.get("stage_timing_ms")
            if isinstance(stage_timing, Mapping):
                for key, value in stage_timing.items():
                    if isinstance(value, (int, float)):
                        hybrid_stage_timing_values.setdefault(str(key), []).append(float(value))
        phases = run_report.get("phase_timing_s") if isinstance(run_report, Mapping) else None
        if isinstance(phases, Mapping):
            for key, value in phases.items():
                if isinstance(value, (int, float)):
                    phase_values.setdefault(str(key), []).append(float(value))
        mapped_cache = run_report.get("mapped_fields_cache") if isinstance(run_report, Mapping) else None
        if isinstance(mapped_cache, Mapping):
            status = str(mapped_cache.get("status", "unknown"))
            mapped_cache_status_counts[status] = mapped_cache_status_counts.get(status, 0) + 1
        launcher_mode = run_report.get("run_vl_hybrid_launcher_mode") if isinstance(run_report, Mapping) else None
        if launcher_mode is not None:
            mode = str(launcher_mode)
            launcher_mode_counts[mode] = launcher_mode_counts.get(mode, 0) + 1
        state_count = run_report.get("parallel_state_count") if isinstance(run_report, Mapping) else None
        if isinstance(state_count, int):
            sidecar_state_counts.append(state_count)
        init_replication_mode = run_report.get("init_replication_mode") if isinstance(run_report, Mapping) else None
        if init_replication_mode is not None:
            mode = str(init_replication_mode)
            init_replication_mode_counts[mode] = init_replication_mode_counts.get(mode, 0) + 1
        patch_drive_scope = run_report.get("patch_drive_scope") if isinstance(run_report, Mapping) else None
        if patch_drive_scope is not None:
            scope = str(patch_drive_scope)
            patch_drive_scope_counts[scope] = patch_drive_scope_counts.get(scope, 0) + 1
        clock_reset_patch = run_report.get("clock_reset_patch") if isinstance(run_report, Mapping) else None
        if isinstance(clock_reset_patch, Mapping):
            clock_patch_mode = clock_reset_patch.get("patch_script_mode")
            if clock_patch_mode is not None:
                mode = str(clock_patch_mode)
                clock_patch_mode_counts[mode] = clock_patch_mode_counts.get(mode, 0) + 1
        step_trace_copy_mode = run_report.get("step_trace_copy_mode") if isinstance(run_report, Mapping) else None
        if step_trace_copy_mode is not None:
            mode = str(step_trace_copy_mode)
            step_trace_copy_mode_counts[mode] = step_trace_copy_mode_counts.get(mode, 0) + 1
        step_trace_filter = run_report.get("step_trace_filter") if isinstance(run_report, Mapping) else None
        if isinstance(step_trace_filter, Mapping):
            start = step_trace_filter.get("start")
            stride = step_trace_filter.get("stride")
            mode = step_trace_filter.get("mode")
            key = f"start={start},stride={stride}" if mode is None else f"{mode}:start={start},stride={stride}"
            step_trace_filter_counts[key] = step_trace_filter_counts.get(key, 0) + 1
            rows = step_trace_filter.get("rows")
            capacity = step_trace_filter.get("capacity")
            if isinstance(rows, int):
                step_trace_filter_rows.append(rows)
            if isinstance(capacity, int):
                step_trace_filter_capacity.append(capacity)
        resident_patch_schedule = (
            run_report.get("resident_patch_schedule") if isinstance(run_report, Mapping) else None
        )
        if isinstance(resident_patch_schedule, Mapping):
            records = resident_patch_schedule.get("records")
            logical_steps = resident_patch_schedule.get("logical")
            if isinstance(records, int):
                resident_patch_records.append(records)
            if isinstance(logical_steps, int):
                resident_patch_logical_steps.append(logical_steps)
        state_local_patch_schedule = (
            run_report.get("state_local_patch_schedule") if isinstance(run_report, Mapping) else None
        )
        if isinstance(state_local_patch_schedule, Mapping):
            records = state_local_patch_schedule.get("records")
            logical_steps = state_local_patch_schedule.get("logical")
            if isinstance(records, int):
                state_local_patch_records.append(records)
            if isinstance(logical_steps, int):
                state_local_patch_logical_steps.append(logical_steps)
        patch_eval_fusion = (
            run_report.get("patch_eval_fusion") if isinstance(run_report, Mapping) else None
        )
        if isinstance(patch_eval_fusion, Mapping):
            mode = str(patch_eval_fusion.get("mode", "unknown"))
            patch_eval_fusion_mode_counts[mode] = patch_eval_fusion_mode_counts.get(mode, 0) + 1
            available = str(bool(patch_eval_fusion.get("available"))).lower()
            patch_eval_fusion_available_counts[available] = (
                patch_eval_fusion_available_counts.get(available, 0) + 1
            )
            launched = patch_eval_fusion.get("launched")
            fallback = patch_eval_fusion.get("fallback")
            if isinstance(launched, int):
                patch_eval_fusion_launched.append(launched)
            if isinstance(fallback, int):
                patch_eval_fusion_fallback.append(fallback)
        pair_cycle_fusion = (
            run_report.get("pair_cycle_fusion") if isinstance(run_report, Mapping) else None
        )
        if isinstance(pair_cycle_fusion, Mapping):
            mode = str(pair_cycle_fusion.get("mode", "unknown"))
            pair_cycle_fusion_mode_counts[mode] = pair_cycle_fusion_mode_counts.get(mode, 0) + 1
            available = str(bool(pair_cycle_fusion.get("available"))).lower()
            pair_cycle_fusion_available_counts[available] = (
                pair_cycle_fusion_available_counts.get(available, 0) + 1
            )
            launched = pair_cycle_fusion.get("launched")
            fallback = pair_cycle_fusion.get("fallback")
            if isinstance(launched, int):
                pair_cycle_fusion_launched.append(launched)
            if isinstance(fallback, int):
                pair_cycle_fusion_fallback.append(fallback)
        pair_cycle_loop_fusion = (
            run_report.get("pair_cycle_loop_fusion") if isinstance(run_report, Mapping) else None
        )
        if isinstance(pair_cycle_loop_fusion, Mapping):
            mode = str(pair_cycle_loop_fusion.get("mode", "unknown"))
            pair_cycle_loop_fusion_mode_counts[mode] = (
                pair_cycle_loop_fusion_mode_counts.get(mode, 0) + 1
            )
            available = str(bool(pair_cycle_loop_fusion.get("available"))).lower()
            pair_cycle_loop_fusion_available_counts[available] = (
                pair_cycle_loop_fusion_available_counts.get(available, 0) + 1
            )
            kernel_launches = pair_cycle_loop_fusion.get("kernel_launches")
            cycles = pair_cycle_loop_fusion.get("cycles")
            fallback = pair_cycle_loop_fusion.get("fallback")
            chunk = pair_cycle_loop_fusion.get("chunk")
            if isinstance(kernel_launches, int):
                pair_cycle_loop_fusion_kernel_launches.append(kernel_launches)
            if isinstance(cycles, int):
                pair_cycle_loop_fusion_cycles.append(cycles)
            if isinstance(fallback, int):
                pair_cycle_loop_fusion_fallback.append(fallback)
            if isinstance(chunk, int):
                pair_cycle_loop_fusion_chunks.append(chunk)
        pair_cycle_state_local_fusion = (
            run_report.get("pair_cycle_state_local_fusion") if isinstance(run_report, Mapping) else None
        )
        if isinstance(pair_cycle_state_local_fusion, Mapping):
            mode = str(pair_cycle_state_local_fusion.get("mode", "unknown"))
            pair_cycle_state_local_fusion_mode_counts[mode] = (
                pair_cycle_state_local_fusion_mode_counts.get(mode, 0) + 1
            )
            available = str(bool(pair_cycle_state_local_fusion.get("available"))).lower()
            pair_cycle_state_local_fusion_available_counts[available] = (
                pair_cycle_state_local_fusion_available_counts.get(available, 0) + 1
            )
            launched = pair_cycle_state_local_fusion.get("launched")
            fallback = pair_cycle_state_local_fusion.get("fallback")
            if isinstance(launched, int):
                pair_cycle_state_local_fusion_launched.append(launched)
            if isinstance(fallback, int):
                pair_cycle_state_local_fusion_fallback.append(fallback)
        resident_pair_cycle = (
            run_report.get("resident_pair_cycle") if isinstance(run_report, Mapping) else None
        )
        if isinstance(resident_pair_cycle, Mapping):
            mode = str(resident_pair_cycle.get("mode", "unknown"))
            resident_pair_cycle_mode_counts[mode] = resident_pair_cycle_mode_counts.get(mode, 0) + 1
            launched = resident_pair_cycle.get("launched")
            fallback = resident_pair_cycle.get("fallback")
            if isinstance(launched, int):
                resident_pair_cycle_launched.append(launched)
            if isinstance(fallback, int):
                resident_pair_cycle_fallback.append(fallback)
        parallel_validation = (
            run_report.get("parallel_state_validation") if isinstance(run_report, Mapping) else None
        )
        if isinstance(parallel_validation, Mapping):
            validation_status = str(parallel_validation.get("parallel_state_validation_status", "unknown"))
            parallel_validation_status_counts[validation_status] = (
                parallel_validation_status_counts.get(validation_status, 0) + 1
            )
    sidecar_wall_median = _median(wall_values)
    sidecar_state_count = sidecar_state_counts[0] if sidecar_state_counts and len(set(sidecar_state_counts)) == 1 else None
    summary = {
        "all_sidecar_samples_passed_correctness": all_passed,
        "sidecar_wall_s_min": round(min(wall_values), 6),
        "sidecar_wall_s_median": sidecar_wall_median,
        "sidecar_wall_s_max": round(max(wall_values), 6),
        "gpu_kernel_ms_total_median": _median(kernel_values),
        "gpu_kernel_timing_sample_count": len(kernel_values),
        "gpu_kernel_timed_launch_count_median": _median(kernel_timed_launch_counts),
        "gpu_kernel_timing_logical_step_count_median": _median(kernel_logical_step_counts),
        "gpu_kernel_time_repeat_count_median": _median(kernel_timing_repeat_counts),
        "gpu_kernel_time_ms_per_actual_launch_median": _median(kernel_ms_per_actual_launch),
        "phase_timing_s_median": {key: _median(values) for key, values in sorted(phase_values.items())},
        "hybrid_stage_timing_ms_median": {
            key: _median(values) for key, values in sorted(hybrid_stage_timing_values.items())
        },
        "bridge_phase_timing_s_median": {
            key: _median(values) for key, values in sorted(bridge_phase_values.items())
        },
        "sidecar_executable_invocation_mode_counts": sidecar_invocation_mode_counts,
        "mapped_fields_cache_status_counts": mapped_cache_status_counts,
        "run_vl_hybrid_launcher_mode_counts": launcher_mode_counts,
        "sidecar_parallel_state_count": sidecar_state_count,
        "init_replication_mode_counts": init_replication_mode_counts,
        "patch_drive_scope_counts": patch_drive_scope_counts,
        "clock_patch_mode_counts": clock_patch_mode_counts,
        "step_trace_copy_mode_counts": step_trace_copy_mode_counts,
        "step_trace_filter_counts": step_trace_filter_counts,
        "step_trace_filter_rows_median": _median(step_trace_filter_rows),
        "step_trace_filter_capacity_median": _median(step_trace_filter_capacity),
        "resident_patch_records_median": _median(resident_patch_records),
        "resident_patch_logical_steps_median": _median(resident_patch_logical_steps),
        "state_local_patch_records_median": _median(state_local_patch_records),
        "state_local_patch_logical_steps_median": _median(state_local_patch_logical_steps),
        "patch_eval_fusion_mode_counts": patch_eval_fusion_mode_counts,
        "patch_eval_fusion_available_counts": patch_eval_fusion_available_counts,
        "patch_eval_fusion_launched_median": _median(patch_eval_fusion_launched),
        "patch_eval_fusion_fallback_median": _median(patch_eval_fusion_fallback),
        "pair_cycle_fusion_mode_counts": pair_cycle_fusion_mode_counts,
        "pair_cycle_fusion_available_counts": pair_cycle_fusion_available_counts,
        "pair_cycle_fusion_launched_median": _median(pair_cycle_fusion_launched),
        "pair_cycle_fusion_fallback_median": _median(pair_cycle_fusion_fallback),
        "pair_cycle_loop_fusion_mode_counts": pair_cycle_loop_fusion_mode_counts,
        "pair_cycle_loop_fusion_available_counts": pair_cycle_loop_fusion_available_counts,
        "pair_cycle_loop_fusion_kernel_launches_median": _median(
            pair_cycle_loop_fusion_kernel_launches
        ),
        "pair_cycle_loop_fusion_cycles_median": _median(pair_cycle_loop_fusion_cycles),
        "pair_cycle_loop_fusion_fallback_median": _median(pair_cycle_loop_fusion_fallback),
        "pair_cycle_loop_fusion_chunk_median": _median(pair_cycle_loop_fusion_chunks),
        "pair_cycle_state_local_fusion_mode_counts": pair_cycle_state_local_fusion_mode_counts,
        "pair_cycle_state_local_fusion_available_counts": pair_cycle_state_local_fusion_available_counts,
        "pair_cycle_state_local_fusion_launched_median": _median(
            pair_cycle_state_local_fusion_launched
        ),
        "pair_cycle_state_local_fusion_fallback_median": _median(
            pair_cycle_state_local_fusion_fallback
        ),
        "resident_pair_cycle_mode_counts": resident_pair_cycle_mode_counts,
        "resident_pair_cycle_launched_median": _median(resident_pair_cycle_launched),
        "resident_pair_cycle_fallback_median": _median(resident_pair_cycle_fallback),
        "sidecar_parallel_validation_status_counts": parallel_validation_status_counts,
        "cpu_reference_elapsed_s": cpu_elapsed,
        "cpu_parallel_wall_s": parallel_wall,
        "sidecar_vs_serial_cpu_ratio": (
            round(float(cpu_elapsed) / sidecar_wall_median, 6)
            if isinstance(cpu_elapsed, (int, float)) and sidecar_wall_median and sidecar_wall_median > 0
            else None
        ),
        "sidecar_vs_cpu_parallel_ratio": (
            round(float(parallel_wall) / sidecar_wall_median, 6)
            if isinstance(parallel_wall, (int, float)) and sidecar_wall_median and sidecar_wall_median > 0
            else None
        ),
    }
    if sidecar_state_count and sidecar_wall_median and sidecar_wall_median > 0:
        summary["sidecar_parallel_states_per_s_median"] = round(sidecar_state_count / sidecar_wall_median, 6)
        summary["sidecar_wall_s_per_parallel_state_median"] = round(sidecar_wall_median / sidecar_state_count, 6)
    else:
        summary["sidecar_parallel_states_per_s_median"] = None
        summary["sidecar_wall_s_per_parallel_state_median"] = None
    summary["parallel_state_validation_complete"] = (
        parallel_validation_status_counts.get("all_final_observables_match_state0") == len(sample_reports)
        and patch_drive_scope_counts.get("all_states") == len(sample_reports)
        and bool(sample_reports)
    )
    summary["cpu_parallel_case_instance_count"] = cpu_parallel_case_count
    repeated_hybrid_timing = any(count > 1 for count in kernel_timing_repeat_counts)
    if repeated_hybrid_timing:
        summary["timing_comparison_scope"] = "in_process_hybrid_repeat_diagnostic"
        summary["timing_comparison_blocked_reason"] = (
            "hybrid timing repeats execute the GPU sidecar workload multiple "
            "times inside one CUDA context, so sidecar wall time is not "
            "comparable to a single CPU RTLMeter run"
        )
    else:
        summary["timing_comparison_scope"] = "single_sidecar_invocation"
        summary["timing_comparison_blocked_reason"] = None
    summary["gpu_cpu_parallel_comparison_valid"] = (
        summary["sidecar_vs_cpu_parallel_ratio"] is not None
        and summary["parallel_state_validation_complete"] is True
        and isinstance(sidecar_state_count, int)
        and isinstance(cpu_parallel_case_count, int)
        and sidecar_state_count == cpu_parallel_case_count
        and not repeated_hybrid_timing
    )
    summary["serial_cpu_wall_time_outcome"] = _outcome_from_ratio(
        summary["sidecar_vs_serial_cpu_ratio"] if not repeated_hybrid_timing else None,
        faster="sidecar_faster_than_serial_cpu",
        slower="sidecar_slower_than_serial_cpu",
        insufficient="insufficient_serial_cpu_baseline",
    )
    summary["cpu_parallel_wall_time_outcome"] = _outcome_from_ratio(
        summary["sidecar_vs_cpu_parallel_ratio"] if summary["gpu_cpu_parallel_comparison_valid"] else None,
        faster="sidecar_faster_than_comparable_cpu_parallel_baseline",
        slower="sidecar_slower_than_comparable_cpu_parallel_baseline",
        insufficient="insufficient_comparable_cpu_parallel_baseline",
    )
    summary["preliminary_outcome"] = (
        summary["serial_cpu_wall_time_outcome"]
        if summary["serial_cpu_wall_time_outcome"] != "insufficient_serial_cpu_baseline"
        else summary["cpu_parallel_wall_time_outcome"]
    )
    summary["cpu_parallel_comparison_valid"] = summary["gpu_cpu_parallel_comparison_valid"]
    return summary


def _summarize_batches(batch_summaries: Sequence[Mapping[str, object]], *, samples_per_batch: int) -> dict[str, object]:
    cpu_parallel_outcomes = [str(summary.get("cpu_parallel_wall_time_outcome")) for summary in batch_summaries]
    serial_outcomes = [str(summary.get("serial_cpu_wall_time_outcome")) for summary in batch_summaries]
    wall_medians = [
        float(summary["sidecar_wall_s_median"])
        for summary in batch_summaries
        if isinstance(summary.get("sidecar_wall_s_median"), (int, float))
    ]
    cpu_parallel_faster_count = cpu_parallel_outcomes.count("sidecar_faster_than_comparable_cpu_parallel_baseline")
    cpu_parallel_slower_count = cpu_parallel_outcomes.count("sidecar_slower_than_comparable_cpu_parallel_baseline")
    mixed_cpu_parallel = cpu_parallel_faster_count > 0 and cpu_parallel_slower_count > 0
    stable_cpu_parallel = len(set(cpu_parallel_outcomes)) == 1
    stable_serial = len(set(serial_outcomes)) == 1
    return {
        "batch_count": len(batch_summaries),
        "samples_per_batch": samples_per_batch,
        "total_sample_count": len(batch_summaries) * samples_per_batch,
        "batch_sidecar_wall_s_medians": [round(value, 6) for value in wall_medians],
        "sidecar_wall_s_median_of_batch_medians": _median(wall_medians),
        "sidecar_wall_s_batch_median_min": round(min(wall_medians), 6) if wall_medians else None,
        "sidecar_wall_s_batch_median_max": round(max(wall_medians), 6) if wall_medians else None,
        "cpu_parallel_faster_batch_count": cpu_parallel_faster_count,
        "cpu_parallel_slower_batch_count": cpu_parallel_slower_count,
        "cpu_parallel_outcomes": cpu_parallel_outcomes,
        "serial_cpu_outcomes": serial_outcomes,
        "stable_cpu_parallel_outcome": stable_cpu_parallel,
        "stable_serial_cpu_outcome": stable_serial,
        "timing_stability_outcome": (
            "unstable_mixed_cpu_parallel_outcomes"
            if mixed_cpu_parallel
            else (
                "stable_repeated_batch_outcome"
                if stable_cpu_parallel and stable_serial
                else "unstable_or_insufficient_repeated_batch_outcome"
            )
        ),
    }


def _bridge_command(
    *,
    state_image: str,
    cpu_execute_dir: str,
    sidecar_execute_dir: str,
    sidecar_executable: str,
    mdir: str,
    sidecar_nstates: int | None,
    sidecar_env: Mapping[str, str] | None = None,
    repo_root: Path,
) -> list[str]:
    command = [
        "python3",
        "src/tools/verilator_native_sidecar_make_driver.py",
        "run-veer-el2-sidecar-bridge",
        "--repo-root",
        ".",
        "--filelist",
        "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist",
        "--top-module",
        "tb_top",
        "--mdir",
        _report_arg_path(mdir, repo_root),
        "--state-image",
        _report_arg_path(state_image, repo_root),
        "--cpu-execute-dir",
        _report_arg_path(cpu_execute_dir, repo_root),
        "--sidecar-execute-dir",
        _report_arg_path(sidecar_execute_dir, repo_root),
        "--sidecar-executable",
        _report_arg_path(sidecar_executable, repo_root),
        "--summary-out",
        "reports/rtlmeter_veer_el2_sidecar_bridge.json",
    ]
    env_prefix = [f"{key}={value}" for key, value in sorted((sidecar_env or {}).items())]
    if env_prefix:
        command = [*env_prefix, *command]
    return command


def build_veer_el2_timing_report(
    *,
    case: str = CASE,
    samples: int = 3,
    batches: int = 1,
    execute: bool = False,
    repo_root: Path | None = None,
    cpu_execute_dir: str = DEFAULT_CPU_EXECUTE_DIR,
    sidecar_execute_dir: str = DEFAULT_SIDECAR_EXECUTE_DIR,
    state_image: str = DEFAULT_STATE_IMAGE,
    mdir: str = DEFAULT_MDIR,
    sidecar_executable: str = DEFAULT_SIDECAR_EXECUTABLE,
    sidecar_nstates: int | None = None,
    cpu_parallel_report: str = DEFAULT_CPU_PARALLEL_REPORT,
    rtlmeter_post_finish_cycles: int = DEFAULT_RTL_METER_POST_FINISH_CYCLES,
    max_pair_cycle_fused_launches: int = DEFAULT_MAX_PAIR_CYCLE_FUSED_LAUNCHES,
    bridge_runner: Callable[..., Mapping[str, object]] = run_veer_el2_sidecar_execution_bridge,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    sidecar_env: dict[str, str] = {}
    if sidecar_nstates is not None:
        sidecar_env["VEER_EL2_SIDECAR_NSTATES"] = str(sidecar_nstates)
    clock_patch_mode = os.environ.get("VEER_EL2_SIDECAR_CLOCK_PATCH_MODE")
    if clock_patch_mode:
        sidecar_env["VEER_EL2_SIDECAR_CLOCK_PATCH_MODE"] = clock_patch_mode
    fused_pair_cycle = os.environ.get("VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE")
    if fused_pair_cycle:
        sidecar_env["VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE"] = fused_pair_cycle
    fused_pair_cycle_loop = os.environ.get("VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP")
    if fused_pair_cycle_loop:
        sidecar_env["VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP"] = fused_pair_cycle_loop
    fused_pair_cycle_loop_chunk = os.environ.get("VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK")
    if fused_pair_cycle_loop_chunk:
        sidecar_env["VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK"] = fused_pair_cycle_loop_chunk
    disable_step_trace = os.environ.get("VEER_EL2_SIDECAR_DISABLE_STEP_TRACE")
    if disable_step_trace:
        sidecar_env["VEER_EL2_SIDECAR_DISABLE_STEP_TRACE"] = disable_step_trace
    final_observable_stdout = os.environ.get("VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT")
    if final_observable_stdout:
        sidecar_env["VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT"] = final_observable_stdout
    hybrid_stage_timing = os.environ.get("VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING")
    if hybrid_stage_timing:
        sidecar_env["VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING"] = hybrid_stage_timing
    hybrid_timing_repeats = os.environ.get("VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS")
    if hybrid_timing_repeats:
        sidecar_env["VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS"] = hybrid_timing_repeats
    state_local_patches = os.environ.get("VEER_EL2_SIDECAR_STATE_LOCAL_PATCHES")
    if state_local_patches:
        sidecar_env["VEER_EL2_SIDECAR_STATE_LOCAL_PATCHES"] = state_local_patches
    fused_patch_eval = os.environ.get("VEER_EL2_SIDECAR_FUSED_PATCH_EVAL")
    if fused_patch_eval:
        sidecar_env["VEER_EL2_SIDECAR_FUSED_PATCH_EVAL"] = fused_patch_eval
    report: dict[str, object] = {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "opt_in_required" if not execute else "preflight_pending",
        "case": case,
        "sample_count": samples,
        "batch_count": batches,
        "total_sample_count": samples * batches if samples > 0 and batches > 0 else None,
        "methodology": {
            "repeated_samples_required": True,
            "central_tendency": "median",
            "stability_gate": "multiple batches compare per-batch medians and baseline outcomes",
            "serial_cpu_source": "RTLMeter _execute/metrics.json",
            "cpu_parallel_source": _report_arg_path(cpu_parallel_report, root),
            "sidecar_wall_source": "monotonic wall time around direct sidecar bridge with invocation mode recorded per sample",
            "gpu_kernel_source": "run_vl_hybrid stdout parsed by sidecar executable report",
            "gpu_parallel_validation_source": (
                "all launched states require all-state clock/reset patching and final observables matching state 0"
            ),
            "stdout_trace_scope": "state0_only",
            "sidecar_nstates_override": sidecar_nstates,
            "launch_count_gate": "current resident_pair_cycle fused model must stay below max_pair_cycle_fused_launches before execution",
        },
        "sidecar_env": sidecar_env,
        "command": _bridge_command(
            state_image=state_image,
            cpu_execute_dir=cpu_execute_dir,
            sidecar_execute_dir=sidecar_execute_dir,
            sidecar_executable=sidecar_executable,
            mdir=mdir,
            sidecar_nstates=sidecar_nstates,
            sidecar_env=sidecar_env,
            repo_root=root,
        ),
        "cpu_reference": _cpu_metrics(root / cpu_execute_dir, case=case),
        "cpu_observables": _observables_from_execute_dir(root / cpu_execute_dir, root),
        "cpu_parallel_baseline": _cpu_parallel_summary(root / cpu_parallel_report, root, case=case),
        "launch_count_feasibility": None,
        "sidecar_samples": [],
        "summary": None,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "generated_report_is_source_of_truth": False,
        "missing_prerequisites": [],
        "non_claims": [
            "this report does not broaden RTLMeter support beyond reviewed VeeR-EL2 program preloads",
            "sidecar timing is not a speedup claim until repeated samples and CPU-parallel comparison are reviewed",
            "CPU fallback is never reported as GPU execution",
            "multi-state GPU validation does not provide independent stdout streams for states beyond state 0",
        ],
    }
    rtlmeter_cycles = None
    if isinstance(report["cpu_reference"], Mapping):
        rtlmeter_cycles = report["cpu_reference"].get("rtlmeter_clocks")
    if not isinstance(rtlmeter_cycles, int) and isinstance(report["cpu_observables"], Mapping):
        rtlmeter_cycles = report["cpu_observables"].get("rtlmeter_cycles")
    report["launch_count_feasibility"] = _pair_cycle_launch_count_feasibility(
        rtlmeter_cycles=rtlmeter_cycles,
        post_finish_cycles=rtlmeter_post_finish_cycles,
        reset_launches=DEFAULT_RESET_LAUNCHES,
        max_pair_cycle_fused_launches=max_pair_cycle_fused_launches,
    )
    if samples < 1:
        report["status"] = "invalid_sample_count"
        report["missing_prerequisites"] = ["samples"]
        return report
    if batches < 1:
        report["status"] = "invalid_batch_count"
        report["missing_prerequisites"] = ["batches"]
        return report
    if sidecar_nstates is not None and sidecar_nstates < 1:
        report["status"] = "invalid_sidecar_nstates"
        report["missing_prerequisites"] = ["sidecar_nstates"]
        return report
    if not execute:
        return report

    feasibility = report.get("launch_count_feasibility")
    if isinstance(feasibility, Mapping) and feasibility.get("status") == "blocked_pair_cycle_launch_count":
        report["status"] = "blocked_launch_count_feasibility"
        report["missing_prerequisites"] = ["pair_cycle_launch_count_feasibility"]
        return report

    sidecar_dir = root / sidecar_execute_dir
    sidecar_env = report["sidecar_env"] if isinstance(report.get("sidecar_env"), Mapping) else {}
    sample_reports: list[dict[str, object]] = []
    batch_reports: list[dict[str, object]] = []
    for batch_index in range(batches):
        batch_samples: list[dict[str, object]] = []
        for sample_index in range(samples):
            started = time.monotonic()
            bridge = dict(
                bridge_runner(
                    state_image_path=state_image,
                    cpu_execute_dir=cpu_execute_dir,
                    sidecar_execute_dir=sidecar_execute_dir,
                    sidecar_executable=sidecar_executable,
                    mdir=mdir,
                    sidecar_env=sidecar_env,
                    repo_root=root,
                )
            )
            wall_s = time.monotonic() - started
            sample = {
                "batch": batch_index + 1,
                "sample": sample_index + 1,
                "global_sample": len(sample_reports) + 1,
                "sidecar_bridge_status": bridge.get("status"),
                "sidecar_executable_invocation_mode": bridge.get("sidecar_executable_invocation_mode"),
                "sidecar_bridge_phase_timing_s": bridge.get("phase_timing_s"),
                "sidecar_wall_s": round(wall_s, 6),
                "comparison": bridge.get("comparison"),
                "missing_build_context": bridge.get("missing_build_context"),
                "sidecar_run_report": _sidecar_run_report(sidecar_dir, root),
            }
            sample_reports.append(sample)
            batch_samples.append(sample)
        batch_reports.append({"batch": batch_index + 1, "samples": batch_samples})
    report["sidecar_samples"] = sample_reports
    report["sidecar_batches"] = batch_reports
    cpu_elapsed = report["cpu_reference"].get("elapsed_s") if isinstance(report["cpu_reference"], Mapping) else None
    cpu_reference_ready = (
        isinstance(report["cpu_reference"], Mapping)
        and report["cpu_reference"].get("status") == "ready"
        and isinstance(cpu_elapsed, (int, float))
    )
    cpu_observables_ready = (
        isinstance(report["cpu_observables"], Mapping)
        and report["cpu_observables"].get("status") == "observables_ready"
    )
    cpu_parallel_ready = (
        isinstance(report["cpu_parallel_baseline"], Mapping)
        and report["cpu_parallel_baseline"].get("status") == "passed"
        and report["cpu_parallel_baseline"].get("comparable_to_case") is True
        and report["cpu_parallel_baseline"].get("all_runs_passed") is True
        and report["cpu_parallel_baseline"].get("all_observables_match") is True
    )
    parallel_wall = (
        report["cpu_parallel_baseline"].get("parallel_wall_s")
        if isinstance(report["cpu_parallel_baseline"], Mapping)
        and report["cpu_parallel_baseline"].get("comparable_to_case") is True
        else None
    )
    cpu_parallel_case_count = (
        report["cpu_parallel_baseline"].get("matching_case_instance_count")
        if isinstance(report["cpu_parallel_baseline"], Mapping)
        else None
    )
    summary = _summarize_samples(
        sample_reports,
        cpu_elapsed=cpu_elapsed,
        parallel_wall=parallel_wall,
        cpu_parallel_case_count=cpu_parallel_case_count,
    )
    batch_summaries = [
        _summarize_samples(
            batch["samples"],
            cpu_elapsed=cpu_elapsed,
            parallel_wall=parallel_wall,
            cpu_parallel_case_count=cpu_parallel_case_count,
        )
        for batch in batch_reports
    ]
    for batch, batch_summary in zip(batch_reports, batch_summaries, strict=True):
        batch["summary"] = batch_summary
    summary["batch_summaries"] = [
        {"batch": batch["batch"], **batch_summary}
        for batch, batch_summary in zip(batch_reports, batch_summaries, strict=True)
    ]
    summary["timing_stability"] = _summarize_batches(batch_summaries, samples_per_batch=samples)
    gpu_kernel_ready = (
        summary["gpu_kernel_timing_sample_count"] == len(sample_reports)
        if isinstance(summary.get("gpu_kernel_timing_sample_count"), int)
        else False
    )
    report["summary"] = summary
    missing_prerequisites = []
    if not summary["all_sidecar_samples_passed_correctness"]:
        missing_prerequisites.append("sidecar_correctness_samples")
    if not cpu_reference_ready:
        missing_prerequisites.append("serial_cpu_metrics")
    if not cpu_observables_ready:
        missing_prerequisites.append("serial_cpu_observables")
    if not cpu_parallel_ready:
        missing_prerequisites.append("cpu_parallel_baseline")
    if not gpu_kernel_ready:
        missing_prerequisites.append("gpu_kernel_timing")
    if not summary.get("parallel_state_validation_complete"):
        missing_prerequisites.append("parallel_state_validation")
    report["missing_prerequisites"] = missing_prerequisites
    report["timing_measured"] = not missing_prerequisites
    report["status"] = (
        "passed"
        if not missing_prerequisites
        else ("failed" if not summary["all_sidecar_samples_passed_correctness"] else "incomplete")
    )
    return report


def write_report(report: Mapping[str, object], report_path: str | Path, *, repo_root: Path) -> Path:
    path_text, errors = _validated_output_path(report_path, required_root="reports", default=DEFAULT_REPORT)
    if errors:
        raise ValueError(",".join(errors))
    path = repo_root / path_text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=CASE)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--batches", type=int, default=1)
    parser.add_argument("--execute", action="store_true", help="Run sidecar timing; also enabled by opt-in env")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default=DEFAULT_REPORT)
    parser.add_argument("--cpu-execute-dir", default=DEFAULT_CPU_EXECUTE_DIR)
    parser.add_argument("--sidecar-execute-dir", default=DEFAULT_SIDECAR_EXECUTE_DIR)
    parser.add_argument("--state-image", default=DEFAULT_STATE_IMAGE)
    parser.add_argument("--mdir", default=DEFAULT_MDIR)
    parser.add_argument("--sidecar-executable", default=DEFAULT_SIDECAR_EXECUTABLE)
    parser.add_argument("--sidecar-nstates", type=int, default=None)
    parser.add_argument("--cpu-parallel-report", default=DEFAULT_CPU_PARALLEL_REPORT)
    parser.add_argument("--rtlmeter-post-finish-cycles", type=int, default=DEFAULT_RTL_METER_POST_FINISH_CYCLES)
    parser.add_argument("--max-pair-cycle-fused-launches", type=int, default=DEFAULT_MAX_PAIR_CYCLE_FUSED_LAUNCHES)
    parser.add_argument(
        "--bounded-progress-reports",
        nargs="*",
        default=None,
        help="Summarize existing VeeR-EL2 sidecar bounded progress reports instead of running timing",
    )
    parser.add_argument("--bounded-progress-min-mcycle", type=int, default=DEFAULT_MIN_BOUNDED_PROGRESS_MCYCLE)
    parser.add_argument("--bounded-progress-min-minstret", type=int, default=DEFAULT_MIN_BOUNDED_PROGRESS_MINSTRET)
    parser.add_argument(
        "--same-window-compare-reports",
        nargs="*",
        default=None,
        help="Summarize existing same-window CPU/GPU trace compare reports instead of running timing",
    )
    parser.add_argument("--same-window-min-aligned-rows", type=int, default=DEFAULT_MIN_TRACE_EQUIVALENCE_ROWS)
    parser.add_argument("--same-window-min-compared-fields", type=int, default=DEFAULT_MIN_TRACE_EQUIVALENCE_FIELDS)
    parser.add_argument(
        "--bounded-projection-sidecar-report",
        default=None,
        help="Project an existing bounded GPU sidecar report to a CPU serial RTLMeter baseline",
    )
    parser.add_argument(
        "--bounded-projection-cpu-baseline-report",
        default=None,
        help="CPU serial baseline report for --bounded-projection-sidecar-report",
    )
    parser.add_argument(
        "--bounded-projection-min-progress-fraction",
        type=float,
        default=DEFAULT_BOUNDED_PROJECTION_MIN_PROGRESS_FRACTION,
    )
    parser.add_argument(
        "--negative-usefulness-ratio-threshold",
        type=float,
        default=DEFAULT_NEGATIVE_USEFULNESS_RATIO_THRESHOLD,
    )
    parser.add_argument(
        "--mixed-state-sidecar-report",
        default=None,
        help="Summarize a mixed-state GPU sidecar report against a CPU mixed parallel baseline",
    )
    parser.add_argument(
        "--mixed-state-cpu-baseline-report",
        default=None,
        help="CPU mixed parallel baseline report for --mixed-state-sidecar-report",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = _repo_root()
    if args.bounded_progress_reports is not None:
        report = build_bounded_progress_summary(
            report_paths=args.bounded_progress_reports,
            repo_root=root,
            min_mcycle=args.bounded_progress_min_mcycle,
            min_minstret=args.bounded_progress_min_minstret,
            max_actual_launches=args.max_pair_cycle_fused_launches,
        )
        if args.write_report:
            write_report(report, args.report_out, repo_root=root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "passed" else 1
    if args.same_window_compare_reports is not None:
        report = build_same_window_trace_equivalence_summary(
            report_paths=args.same_window_compare_reports,
            repo_root=root,
            min_aligned_rows=args.same_window_min_aligned_rows,
            min_compared_fields=args.same_window_min_compared_fields,
        )
        if args.write_report:
            write_report(report, args.report_out, repo_root=root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "passed" else 1
    if args.bounded_projection_sidecar_report is not None:
        if args.bounded_projection_cpu_baseline_report is None:
            parser_error = {
                "schema_version": 1,
                "surface": f"{SURFACE}.bounded_projection_usefulness_summary",
                "status": "incomplete",
                "errors": ["bounded_projection_cpu_baseline_report.required"],
                "timing_measured": False,
                "speedup_claimed": False,
                "usefulness_claimed": False,
            }
            print(json.dumps(parser_error, indent=2, sort_keys=True))
            return 1
        report = build_bounded_projection_usefulness_summary(
            sidecar_report_path=args.bounded_projection_sidecar_report,
            cpu_baseline_report_path=args.bounded_projection_cpu_baseline_report,
            case=args.case,
            repo_root=root,
            min_progress_fraction=args.bounded_projection_min_progress_fraction,
            negative_ratio_threshold=args.negative_usefulness_ratio_threshold,
        )
        if args.write_report:
            write_report(report, args.report_out, repo_root=root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "negative_usefulness_projected" else 1
    if args.mixed_state_sidecar_report is not None:
        if args.mixed_state_cpu_baseline_report is None:
            parser_error = {
                "schema_version": 1,
                "surface": f"{SURFACE}.mixed_state_gpu_cpu_summary",
                "status": "incomplete",
                "errors": ["mixed_state_cpu_baseline_report.required"],
                "timing_measured": False,
                "speedup_claimed": False,
                "usefulness_claimed": False,
            }
            print(json.dumps(parser_error, indent=2, sort_keys=True))
            return 1
        report = build_mixed_state_gpu_cpu_summary(
            sidecar_report_path=args.mixed_state_sidecar_report,
            cpu_baseline_report_path=args.mixed_state_cpu_baseline_report,
            repo_root=root,
        )
        if args.write_report:
            write_report(report, args.report_out, repo_root=root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] in {"mixed_state_gpu_smoke_passed", "mixed_state_gpu_negative_projection"} else 1
    execute = args.execute or os.environ.get(OPT_IN_ENV) == "1"
    report = build_veer_el2_timing_report(
        case=args.case,
        samples=args.samples,
        batches=args.batches,
        execute=execute,
        repo_root=root,
        cpu_execute_dir=args.cpu_execute_dir,
        sidecar_execute_dir=args.sidecar_execute_dir,
        state_image=args.state_image,
        mdir=args.mdir,
        sidecar_executable=args.sidecar_executable,
        sidecar_nstates=args.sidecar_nstates,
        cpu_parallel_report=args.cpu_parallel_report,
        rtlmeter_post_finish_cycles=args.rtlmeter_post_finish_cycles,
        max_pair_cycle_fused_launches=args.max_pair_cycle_fused_launches,
    )
    if args.write_report:
        write_report(report, args.report_out, repo_root=root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"opt_in_required", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
