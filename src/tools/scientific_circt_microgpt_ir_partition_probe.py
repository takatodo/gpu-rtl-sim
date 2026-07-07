#!/usr/bin/env python3
"""Map measured scientific CIRCT GPU policy onto a microGPT-style IR partition."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPORT = Path("reports/scientific_circt_microgpt_ir_partition_probe.json")

MICROGPT_OPS: tuple[dict[str, Any], ...] = (
    {
        "op": "qkv_projection",
        "microgpt_region": "attention",
        "candidate": "dense_matmul_tile",
        "reason": "regular dense projection with independent batch/state rows",
    },
    {
        "op": "attention_score_matmul",
        "microgpt_region": "attention",
        "candidate": "dense_matmul_tile",
        "reason": "regular dot-product tile, low observable pressure",
    },
    {
        "op": "attention_softmax",
        "microgpt_region": "attention",
        "candidate": "softmax_exp_pipeline",
        "reason": "softmax/exp-style arithmetic pipeline measured as GPU-favorable at batch scale",
    },
    {
        "op": "attention_value_weighted_sum",
        "microgpt_region": "attention",
        "candidate": "dense_matmul_tile",
        "reason": "regular weighted sum can use the same state-parallel dense tile bucket",
    },
    {
        "op": "layernorm_reduction",
        "microgpt_region": "normalization",
        "candidate": "batched_reduction",
        "reason": "mean/variance reductions are regular low-observable reductions",
    },
    {
        "op": "mlp_fc1",
        "microgpt_region": "mlp",
        "candidate": "dense_matmul_tile",
        "reason": "regular dense matrix/vector tile",
    },
    {
        "op": "mlp_activation",
        "microgpt_region": "mlp",
        "candidate": "softmax_exp_pipeline",
        "reason": "elementwise polynomial/exp-like arithmetic can share the math-pipeline bucket",
    },
    {
        "op": "mlp_fc2",
        "microgpt_region": "mlp",
        "candidate": "dense_matmul_tile",
        "reason": "regular dense matrix/vector tile",
    },
    {
        "op": "token_loop_and_sampling_control",
        "microgpt_region": "control",
        "candidate": None,
        "reason": "stateful token/control path has no measured CIRCT GPU candidate yet",
    },
    {
        "op": "kv_cache_update",
        "microgpt_region": "state",
        "candidate": None,
        "reason": "stateful memory update needs a separate transport and coherence mapping",
    },
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path) -> str:
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", path.as_posix())


def _candidate_decision(candidate: str | None, policy: dict[str, Any], nstates: int, steps: int) -> tuple[str, dict[str, Any]]:
    if candidate is None:
        return "select_cpu_or_new_mapping", {"reason": "no_measured_gpu_candidate"}
    candidates = policy.get("candidates")
    if not isinstance(candidates, dict) or candidate not in candidates:
        return "select_cpu_or_measure_first", {"reason": "candidate_missing_from_policy", "candidate": candidate}
    entry = candidates[candidate]
    if not isinstance(entry, dict):
        return "select_cpu_or_measure_first", {"reason": "candidate_policy_not_object", "candidate": candidate}
    action = str(entry.get("recommended_action"))
    min_nstates = entry.get("min_gpu_nstates")
    required_steps = entry.get("required_steps")
    if action == "select_gpu_state_parallel" and isinstance(min_nstates, int) and isinstance(required_steps, int):
        if steps == required_steps and nstates >= min_nstates:
            return "select_gpu_state_parallel", {
                "candidate": candidate,
                "min_gpu_nstates": min_nstates,
                "required_steps": required_steps,
                "reason": "measured_policy_boundary_satisfied",
            }
        return "select_cpu_below_measured_boundary", {
            "candidate": candidate,
            "min_gpu_nstates": min_nstates,
            "required_steps": required_steps,
            "reason": "shape_below_measured_gpu_boundary",
        }
    return "select_cpu_or_measure_first", {"candidate": candidate, "reason": "policy_does_not_select_gpu"}


def build_probe(policy: dict[str, Any], nstates: int, steps: int, source: Path | None = None) -> dict[str, Any]:
    if nstates <= 0 or steps <= 0:
        raise ValueError("nstates and steps must be positive")
    ops = []
    for op in MICROGPT_OPS:
        decision, evidence = _candidate_decision(op["candidate"], policy, nstates, steps)
        ops.append({**op, "recommended_action": decision, "evidence": evidence})
    gpu_ops = [op for op in ops if op["recommended_action"] == "select_gpu_state_parallel"]
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_microgpt_ir_partition_probe",
        "status": "partition_probe_ready",
        "source_policy": _display_path(source) if source else None,
        "shape": {"nstates": nstates, "steps": steps},
        "ops": ops,
        "counts": {
            "op_count": len(ops),
            "gpu_state_parallel_op_count": len(gpu_ops),
            "cpu_or_new_mapping_op_count": len(ops) - len(gpu_ops),
        },
        "recommended_partition": {
            "gpu_regions": sorted({op["microgpt_region"] for op in gpu_ops}),
            "cpu_or_new_mapping_regions": sorted({op["microgpt_region"] for op in ops if op not in gpu_ops}),
            "summary": "direct_ir_keeps_regular_math_kernels_visible_for_gpu_selection",
        },
        "non_claims": [
            "not_microgpt_execution",
            "not_circt_lowering_of_microgpt_yet",
            "not_gateGPT_pass_fail_equivalence",
            "not_automatic_partitioning",
            "not_a_general_rtl_speedup_claim",
        ],
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("reports/scientific_circt_gpu_selection_policy.json"))
    parser.add_argument("--nstates", type=int, default=256)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = build_probe(_load(args.policy), args.nstates, args.steps, args.policy)
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
