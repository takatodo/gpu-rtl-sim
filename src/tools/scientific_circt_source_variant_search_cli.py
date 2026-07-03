#!/usr/bin/env python3
"""Thin CLI for FC-075 source-variant rewrite search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
from typing import Any

import scientific_circt_source_variant_search as search
import scientific_circt_source_variant_search_build as build
import scientific_circt_source_variant_search_codegen as codegen

OUT_DIR = Path("artifacts/scientific_circt/search")
REPORT = Path("reports/scientific_circt_source_variant_search.json")
CANDIDATES = ("microgpt_attention_head", "microgpt_mlp_slice", "microgpt_inference_slice")


def _error(status: str, reason: str) -> int:
    print(json.dumps({"status": status, "reason": reason}, sort_keys=True))
    return 2


def parse_plan(text: str | None) -> search.VariantPlan | None:
    if text is None:
        return None
    key, sep, value = text.partition("=")
    if sep != "=":
        raise ValueError("--plan must use key=value form")
    if key == "replicate":
        return search.VariantPlan((search.Replicate(int(value)),))
    if key in {"unroll", "unroll_density"}:
        return search.VariantPlan((search.Replicate(4), search.UnrollDensity(int(value))))
    if key in {"pack", "pack_inputs"}:
        if value not in {"uint8", "uint32"}:
            raise ValueError("pack width must be uint8 or uint32")
        return search.VariantPlan((search.Replicate(4), search.PackInputs(value)))
    raise ValueError(f"unknown plan key: {key}")


def _paths(root: Path, descriptor: search.BlockDescriptor, plan: search.VariantPlan) -> dict[str, Path]:
    paths = build.paths_for(root, descriptor, plan)
    return {
        "dir": paths.work_dir,
        "firrtl": paths.firrtl,
        "cuda": paths.cuda,
        "bridge": paths.bridge,
    }


def emit_sources(root: Path, descriptor: search.BlockDescriptor, plan: search.VariantPlan) -> dict[str, str]:
    paths = _paths(root, descriptor, plan)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    sources = codegen.render_sources(descriptor, plan)
    paths["firrtl"].write_text(sources.firrtl, encoding="utf-8")
    paths["cuda"].write_text(sources.cuda, encoding="utf-8")
    paths["bridge"].write_text(sources.bridge, encoding="utf-8")
    return {key: path.as_posix() for key, path in paths.items() if key != "dir"}


def _sample(report: dict[str, Any]) -> dict[str, Any]:
    observed = report.get("observed") if isinstance(report.get("observed"), dict) else report
    return {
        "status": observed.get("status", report.get("status")),
        "cpu_vs_gpu_output_equal": report.get("cpu_vs_gpu_output_equal", observed.get("cpu_vs_gpu_output_equal")),
        "cpu_vs_gpu_control_checksum_equal": report.get(
            "cpu_vs_gpu_control_checksum_equal", observed.get("cpu_vs_gpu_control_checksum_equal")
        ),
        "mismatch_count": observed.get("mismatch_count", report.get("mismatch_count")),
        "cpu_to_bridge_hybrid_wall_speedup": observed.get("cpu_to_bridge_hybrid_wall_speedup"),
    }


def measure_plan(descriptor: search.BlockDescriptor, plan: search.VariantPlan, out_dir: Path, repeats: int) -> dict[str, Any]:
    samples = []
    for _ in range(repeats):
        report = build.build_and_measure(descriptor, plan, out_root=out_dir, repeat=1)
        sample = _sample(report)
        samples.append(sample)
        if sample.get("cpu_vs_gpu_output_equal") is not True or sample.get("cpu_vs_gpu_control_checksum_equal") is not True:
            break
    return {"variant": codegen.variant_name(descriptor, plan), "plan": str(plan), "samples": samples}


def _median(results: list[dict[str, Any]]) -> float | None:
    ranked = search.rank_variants(results)
    if not ranked:
        return None
    return statistics.median(item["median_cpu_to_bridge_hybrid_wall_speedup"] for item in ranked)


STOP_EARLY_REASONS = {"oracle_mismatch_in_search", "unmeasured_plan_in_search"}


def run_search(
    args: argparse.Namespace, descriptor: search.BlockDescriptor, plans: list[search.VariantPlan], *, is_full_enumeration: bool
) -> dict[str, Any]:
    results = []
    for plan in plans:
        result = measure_plan(descriptor, plan, args.out_dir, args.repeat)
        results.append(result)
        if search.decide_intermediate_gate(0.0, [result])[1] in STOP_EARLY_REASONS:
            break
    density_knob_results = (
        [measure_plan(descriptor, plan, args.out_dir, args.repeat) for plan in search.enumerate_density_probes()]
        if is_full_enumeration
        else []
    )
    baseline = results[0] if results else {}
    baseline_median = search.rank_variants([baseline])[0]["median_cpu_to_bridge_hybrid_wall_speedup"] if search.rank_variants([baseline]) else 0.0
    if args.gate == "intermediate":
        passed, reason = search.decide_intermediate_gate(baseline_median, results)
        reference_median = None
    else:
        reference = measure_plan(search.ATTENTION_DESCRIPTOR, search.VariantPlan((search.Replicate(4),)), args.out_dir, args.repeat)
        reference_median = _median([reference])
        passed, reason = (
            search.decide_falsification_gate(reference_median, results)
            if reference_median is not None
            else (False, "speedup_out_of_band")
        )
    return {
        "status": "source_variant_search_passed" if passed else "source_variant_search_failed",
        "gate": args.gate,
        "candidate": descriptor.candidate,
        "reason": reason,
        "finding": reason == "superior_variant_found",
        "baseline_median": baseline_median,
        "reference_median": reference_median,
        "results": results,
        "density_knob_results": density_knob_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=CANDIDATES, required=True)
    parser.add_argument("--gate", choices=("intermediate", "falsification"), default="intermediate")
    parser.add_argument("--plan", help="Single-plan override, e.g. replicate=4.")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--emit-only", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    if args.repeat < 1:
        return _error("failed_invalid_args", "--repeat must be >= 1")
    try:
        plan = parse_plan(args.plan)
        descriptor = codegen.descriptor_for_candidate(args.candidate)
    except Exception as exc:
        return _error("failed_invalid_args", str(exc))
    plans = [plan] if plan is not None else search.enumerate_plans(args.gate)
    if args.emit_only:
        emitted = [emit_sources(args.out_dir, descriptor, item) for item in plans]
        report = {"status": "source_variant_search_sources_emitted", "candidate": args.candidate, "emitted": emitted}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    report = run_search(args, descriptor, plans, is_full_enumeration=plan is None)
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "source_variant_search_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
