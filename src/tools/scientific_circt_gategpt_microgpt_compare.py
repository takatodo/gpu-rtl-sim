#!/usr/bin/env python3
"""Compare direct microGPT-style CIRCT math evidence with gateGPT RTL evidence."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

REPORT = Path("reports/scientific_circt_gategpt_microgpt_compare.json")
MICROGPT_SOURCE = Path("third_party/microgpt.py")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path) -> str:
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", path.as_posix())


def _median(path: Path) -> dict[str, Any]:
    payload = _load(path)
    median = payload.get("median")
    if not isinstance(median, dict):
        raise ValueError(f"{path}: missing median")
    return {
        "report": _display_path(path),
        "candidate": payload.get("candidate"),
        "shape": payload.get("shape"),
        "status": payload.get("status"),
        "cpu_ms": median.get("cpu_ms"),
        "gpu_end_to_end_ms": median.get("gpu_end_to_end_ms"),
        "gpu_kernel_ms": median.get("gpu_kernel_ms"),
        "end_to_end_speedup": median.get("cpu_to_gpu_end_to_end_speedup"),
        "kernel_speedup": median.get("cpu_to_gpu_kernel_speedup"),
    }


def _get(mapping: dict[str, Any], key: str) -> Any:
    return mapping.get(key)


def _scan_microgpt_source(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    constants: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant):
                constants[node.targets[0].id] = node.value.value
    return {
        "source": _display_path(path),
        "line_count": len(text.splitlines()),
        "license_file_present": any(path.parent.glob("*LICENSE*")) or any(path.parent.glob("*COPYING*")),
        "functions": functions,
        "model_constants": {key: constants.get(key) for key in ("n_layer", "n_embd", "block_size", "n_head")},
        "detected_kernel_shapes": {
            "linear": "linear" in functions,
            "softmax": "softmax" in functions and ".exp()" in text,
            "rmsnorm": "rmsnorm" in functions,
            "attention": "attn_wq" in text and "attn_wk" in text and "attn_wv" in text,
            "mlp": "mlp_fc1" in text and "mlp_fc2" in text,
            "autograd_training": "class Value" in text and "loss.backward()" in text,
        },
    }


def build_comparison(selection: dict[str, Any], microgpt_reports: list[Path], microgpt_source: Path = MICROGPT_SOURCE) -> dict[str, Any]:
    external = selection.get("external_testbench_candidates")
    gategpt = external.get("gategpt") if isinstance(external, dict) else {}
    if not isinstance(gategpt, dict):
        gategpt = {}
    scientific = selection.get("scientific_circt_gpu_candidate_search")
    micro_cfg = scientific.get("microgpt_math_block") if isinstance(scientific, dict) else {}
    if not isinstance(micro_cfg, dict):
        micro_cfg = {}
    micro_measurements = [_median(path) for path in microgpt_reports]
    best_micro = max(micro_measurements, key=lambda row: float(row.get("end_to_end_speedup") or -1)) if micro_measurements else None
    source_scan = _scan_microgpt_source(microgpt_source)
    candidates = sorted({str(row.get("candidate")) for row in micro_measurements})
    systemverilog_by_candidate: dict[str, str | None] = {}
    verilator_reference_by_candidate: dict[str, Any] = {}
    if isinstance(scientific, dict):
        for candidate in candidates:
            cfg = scientific.get(candidate)
            if isinstance(cfg, dict):
                systemverilog_by_candidate[candidate] = cfg.get("systemverilog")
                verilator_reference_by_candidate[candidate] = cfg.get("verilator_cpu_reference")
    tb_core_wall_speedup = _get(gategpt, "gateGPT_tb_core_ordering_aware_cpu_compare_wall_speedup_vs_cpu_observed")
    if tb_core_wall_speedup is None:
        tb_core_wall_speedup = _get(gategpt, "gateGPT_tb_core_distinct_state_pair_cycle_loop_repeat_cpu_compare_wall_speedup_vs_cpu_observed")
    return {
        "schema_version": 1,
        "surface": "scientific_circt_gategpt_microgpt_compare",
        "status": "compared",
        "microgpt_direct_circt_sv": {
            "scope": "source_derived_circt_slices",
            "source_scan": source_scan,
            "candidates": candidates,
            "systemverilog_by_candidate": systemverilog_by_candidate,
            "verilator_cpu_reference_by_candidate": verilator_reference_by_candidate,
            "measurements": micro_measurements,
            "best_end_to_end": best_micro,
            "interpretation": "actual microgpt.py exposes linear, softmax, rmsnorm, attention, and MLP structure; measured CIRCT slices cover regular arithmetic, attention-head, MLP, block-level, and two-token inference subsets with candidate-specific GPU-favorable batch thresholds",
        },
        "gategpt_rtl": {
            "scope": "external_fpga_oriented_rtl_testbench_lane",
            "checkout_path": gategpt.get("checkout_path"),
            "cpu_testbench_count": gategpt.get("gateGPT_cpu_output_manifest_testbench_count"),
            "gpu_kernel_launch_smoke_status": gategpt.get("gpu_kernel_launch_smoke_status"),
            "gpu_kernel_launch_smoke_testbenches": gategpt.get("gpu_kernel_launch_smoke_testbenches"),
            "bench_specific_gpu_output_manifest_status": gategpt.get("gateGPT_gpu_output_mapping_plan_status"),
            "general_stdout_finish_export_claimed": gategpt.get("gateGPT_gpu_output_mapping_plan_gpu_stdout_finish_export_claimed"),
            "pass_fail_equivalence_on_gpu": gategpt.get("gateGPT_pass_fail_equivalence_on_gpu"),
            "tb_exp": {
                "classification": "narrow_regular_datapath_gpu_favorable",
                "case_count": gategpt.get("gateGPT_tb_exp_distinct_state_resident_repeat_median_case_count"),
                "cpu_wall_ms_median": gategpt.get("gateGPT_tb_exp_cpu_baseline_wall_ms_median"),
                "gpu_wall_ms_median": gategpt.get("gateGPT_tb_exp_distinct_state_resident_repeat_median_wall_ms_median"),
                "wall_speedup_observed": gategpt.get("gateGPT_tb_exp_distinct_resident_repeat_gpu_cpu_compare_wall_speedup_observed"),
                "speedup_claimed": gategpt.get("gateGPT_tb_exp_distinct_resident_repeat_gpu_cpu_compare_speedup_claimed"),
            },
            "tb_core": {
                "classification": "stateful_token_control_cpu_negative",
                "cpu_wall_ms_median": gategpt.get("gateGPT_tb_core_cpu_baseline_wall_ms_median"),
                "gpu_wall_ms_median": gategpt.get("gateGPT_tb_core_ordering_aware_cpu_compare_gpu_wall_ms_median")
                or gategpt.get("gateGPT_tb_core_distinct_state_pair_cycle_loop_repeat_cpu_compare_gpu_wall_ms_median"),
                "wall_speedup_vs_cpu_observed": tb_core_wall_speedup,
                "speedup_claimed": gategpt.get("gateGPT_tb_core_ordering_aware_cpu_compare_speedup_claimed")
                or gategpt.get("gateGPT_tb_core_distinct_state_pair_cycle_loop_repeat_cpu_compare_speedup_claimed"),
            },
            "interpretation": "useful for realistic RTL integration and negative/control evidence; noisier for first-pass GPU partition discovery because FPGA-oriented RTL/control has already lowered structure into root-state sequencing",
        },
        "comparison": {
            "gpu_partition_discovery_preference": "microgpt_direct_ir_circt",
            "integration_testbench_preference": "gateGPT_rtl",
            "reason": "microGPT-style CIRCT slices prove source-derived regular arithmetic can be measured directly with candidate-specific GPU thresholds; gateGPT proves representative RTL correctness surfaces but tb_core remains CPU-negative and lacks broad GPU PASS/stdout/finish authority",
        },
        "non_claims": [
            "not_full_microgpt_execution",
            "not_gateGPT_broad_pass_fail_equivalence",
            "not_a_general_rtl_speedup_claim",
            "not_automatic_partitioning",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=Path("config/selection.json"))
    parser.add_argument("--microgpt-source", type=Path, default=MICROGPT_SOURCE)
    parser.add_argument("--microgpt-report", action="append", type=Path, required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = build_comparison(_load(args.selection), args.microgpt_report, args.microgpt_source)
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
