from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from hybrid_benchmark_specs import CORRECTNESS_POLICY_COVERAGE_OUTPUT


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_BENCHMARK = "python3 src/tools/run_hybrid_benchmark.py"
RUN_TEMPLATE = "python3 src/tools/run_hybrid_template.py"
MHA_TEMPLATE = "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json"
DEBUG_OPERATOR_PLAN_COMMAND = f"{RUN_BENCHMARK} paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json"
STATE_PARALLEL_COMMAND = f"{RUN_BENCHMARK} paged_attention_kv_score --sim-accel-shape 64x1 --dry-run --estimate-efficiency-json"
SINGLE_STATE_COMMAND = f"{RUN_BENCHMARK} paged_attention_kv_score --sim-accel-shape 1x64 --dry-run --estimate-efficiency-json"
RESIDENT_COMMAND = f"{RUN_BENCHMARK} pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run --estimate-efficiency"
MHA_COPY_COMMAND = f"{RUN_TEMPLATE} {MHA_TEMPLATE} --shape 1x1"
MHA_COPY_EVIDENCE = "config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_result_gate.json"


def minimal_bench_suite_report() -> dict[str, object]:
    """Return the minimal suite for judging debug surfaces and GPU-hybrid fit."""
    return {
        "schema_version": 1,
        "schema_role": "verilator_compatible_gpu_hybrid_minimal_bench_suite",
        "status": "defined",
        "objective": (
            "Measure how simple and how effective the GPU hybrid path is from "
            "Verilator-compatible inputs before claiming broader RTL support."
        ),
        "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
        "input_surfaces": [
            {
                "name": "target_first_verilator_compatible_option",
                "example": DEBUG_OPERATOR_PLAN_COMMAND,
                "purpose": "debug inspection of the target-first path toward a future Verilator option",
            },
            {
                "name": "filelist_materialized_template",
                "example": MHA_COPY_COMMAND,
                "purpose": "filelist-derived source-closure path with existing execution evidence",
            },
        ],
        "benchmarks": [
            {
                "name": "operator_plan_debug_json",
                "command": DEBUG_OPERATOR_PLAN_COMMAND,
                "executes": False,
                "measures": ["debug_inspection_surface", "verilator_compatible_command_preview"],
                "expected_efficiency_class": "high",
            },
            {
                "name": "state_parallel_dry_run_estimate",
                "command": STATE_PARALLEL_COMMAND,
                "executes": False,
                "measures": ["state_parallel_shape_fit", "planned_gpu_sidecar_flow"],
                "expected_efficiency_class": "high",
            },
            {
                "name": "single_state_repeated_step_dry_run_estimate",
                "command": SINGLE_STATE_COMMAND,
                "executes": False,
                "measures": ["launch_overhead_risk", "weak_shape_detection"],
                "expected_efficiency_class": "low",
            },
            {
                "name": "resident_decode_like_dry_run",
                "command": RESIDENT_COMMAND,
                "executes": False,
                "measures": ["resident_execution_need", "decode_like_repeated_step_mitigation"],
                "expected_efficiency_class": "medium",
            },
            {
                "name": "filelist_materialized_mha_copy_execution_evidence",
                "command": MHA_COPY_COMMAND,
                "executes": True,
                "evidence_gate": MHA_COPY_EVIDENCE,
                "measures": ["filelist_to_hybrid_execution", "coverage_output_equivalence"],
                "known_result": {
                    "coverage_output_mismatch_count": 0,
                    "compared_words": 29,
                    "compared_bytes": 116,
                    "raw_full_state_equality_required": False,
                },
            },
        ],
        "acceptance_metrics": [
            "every executing benchmark must pass coverage_output_equivalence with mismatch count 0",
            "debug JSON commands must exit 0 and expose a Verilator-compatible sidecar command",
            "high and low efficiency classes must remain distinguishable by shape",
            "filelist-derived execution evidence must stay tied to explicit source closure",
        ],
        "non_claims": [
            "not arbitrary RTL support",
            "not a Verilator-native option implementation",
            "not automatic optimal GPU allocation",
            "not timing or speedup evidence by itself",
            "not raw full-state equality",
            "not production LLM-serving throughput",
        ],
    }


def _json_after_marker(stdout: str, marker: str) -> dict[str, object]:
    try:
        _, after = stdout.split(marker, 1)
    except ValueError as exc:
        raise ValueError(f"missing marker in command output: {marker}") from exc
    return json.loads(after.strip())


def _run_command(command: str, *, repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(shlex.split(command), cwd=repo_root, capture_output=True, text=True)


def _validate_evidence(benchmark: dict[str, object], *, repo_root: Path) -> dict[str, object]:
    evidence_gate = benchmark.get("evidence_gate")
    if not isinstance(evidence_gate, str):
        return {"name": benchmark["name"], "status": "failed", "reason": "missing evidence_gate"}
    path = repo_root / evidence_gate
    data = json.loads(path.read_text(encoding="utf-8"))
    coverage = data.get("coverage_output_result", {})
    metadata = data.get("template_metadata", {})
    expected = benchmark.get("known_result")
    expected = expected if isinstance(expected, dict) else {}
    passed = (
        data.get("exit_code") == 0
        and coverage.get("mismatch_count") == expected.get("coverage_output_mismatch_count")
        and coverage.get("compared_word_count") == expected.get("compared_words")
        and coverage.get("compared_byte_count") == expected.get("compared_bytes")
        and metadata.get("source_closure_status") == "complete"
        and isinstance(metadata.get("reference_template"), str)
        and isinstance(metadata.get("source_files_sha256"), str)
    )
    return {
        "name": benchmark["name"],
        "status": "passed" if passed else "failed",
        "execution": "evidence_gate_validation",
        "evidence_gate": evidence_gate,
        "observed": {
            "exit_code": data.get("exit_code"),
            "coverage_output_mismatch_count": coverage.get("mismatch_count"),
            "compared_words": coverage.get("compared_word_count"),
            "compared_bytes": coverage.get("compared_byte_count"),
            "source_closure_status": metadata.get("source_closure_status"),
            "reference_template": metadata.get("reference_template"),
            "source_files_sha256": metadata.get("source_files_sha256"),
        },
    }


def _summarize_command_result(
    benchmark: dict[str, object],
    completed: subprocess.CompletedProcess[str],
) -> dict[str, object]:
    name = benchmark["name"]
    summary: dict[str, object] = {
        "name": name,
        "status": "passed" if completed.returncode == 0 else "failed",
        "execution": "command",
        "exit_code": completed.returncode,
    }
    if completed.returncode != 0:
        summary["stderr_excerpt"] = completed.stderr[:400]
        return summary

    if name == "operator_plan_debug_json":
        payload = json.loads(completed.stdout)
        summary["observed"] = {
            "schema_role": payload.get("schema_role"),
            "json_flow_role": payload.get("json_flow_role"),
            "runtime_abi": payload.get("runtime_abi"),
            "status": payload.get("status"),
            "correctness_policy": payload.get("correctness_policy"),
            "command_has_sim_accel": "--sim-accel sidecar-gpu" in payload.get("command", ""),
        }
        if not summary["observed"]["command_has_sim_accel"] or summary["observed"]["runtime_abi"] is not False:
            summary["status"] = "failed"
        return summary

    if name in {
        "state_parallel_dry_run_estimate",
        "single_state_repeated_step_dry_run_estimate",
    }:
        payload = _json_after_marker(completed.stdout, "# efficiency_estimate_json")
        summary["observed"] = {
            "status": payload.get("status"),
            "speedup_class": payload.get("speedup_class"),
            "source": payload.get("source", "estimate_only"),
            "cpu_to_hybrid_wall_speedup": payload.get("cpu_to_hybrid_wall_speedup"),
            "reports": payload.get("reports"),
        }
        expected = benchmark.get("expected_efficiency_class")
        if payload.get("speedup_class") != expected:
            summary["status"] = "failed"
            summary["reason"] = f"expected speedup_class {expected}"
        return summary

    if name == "resident_decode_like_dry_run":
        summary["observed"] = {
            "has_efficiency_estimate": "# efficiency_estimate" in completed.stdout,
            "has_persistent_resident_command": "--persistent-resident-state-abi 16x64" in completed.stdout,
            "speedup_class": "medium" if "speedup_class: medium" in completed.stdout else None,
        }
        if not all(summary["observed"].values()):
            summary["status"] = "failed"
        return summary

    return summary


def _observed_result_value(results: list[dict[str, object]], name: str, key: str) -> object:
    return next(
        (item.get("observed", {}).get(key) for item in results if item.get("name") == name),
        None,
    )


def run_minimal_bench_suite(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    suite = minimal_bench_suite_report()
    results = []
    for benchmark in suite["benchmarks"]:
        if benchmark.get("executes") is True:
            results.append(_validate_evidence(benchmark, repo_root=repo_root))
            continue
        command = benchmark["command"]
        if not isinstance(command, str):
            results.append({"name": benchmark["name"], "status": "failed", "reason": "missing command"})
            continue
        results.append(_summarize_command_result(benchmark, _run_command(command, repo_root=repo_root)))

    passed = all(item.get("status") == "passed" for item in results)
    high = _observed_result_value(results, "state_parallel_dry_run_estimate", "cpu_to_hybrid_wall_speedup")
    low = _observed_result_value(results, "single_state_repeated_step_dry_run_estimate", "cpu_to_hybrid_wall_speedup")
    high_class = _observed_result_value(results, "state_parallel_dry_run_estimate", "speedup_class")
    low_class = _observed_result_value(results, "single_state_repeated_step_dry_run_estimate", "speedup_class")
    shape_classes_distinguishable = (
        (high is not None and low is not None and high > low)
        or (high_class == "high" and low_class == "low")
    )
    return {
        "schema_version": 1,
        "schema_role": "verilator_compatible_gpu_hybrid_minimal_bench_suite_run",
        "status": "passed" if passed else "failed",
        "correctness_policy": suite["correctness_policy"],
        "benchmark_count": len(results),
        "results": results,
        "summary": {
            "debug_json_preview_passed": results[0].get("status") == "passed" if results else False,
            "state_parallel_speedup": high,
            "single_state_repeated_step_speedup": low,
            "shape_classes_distinguishable": shape_classes_distinguishable,
            "filelist_execution_evidence_validated": results[-1].get("status") == "passed" if results else False,
        },
        "non_claims": suite["non_claims"],
    }
