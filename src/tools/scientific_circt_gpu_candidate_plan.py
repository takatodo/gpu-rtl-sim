#!/usr/bin/env python3
"""Plan scientific-compute candidates for a CIRCT-to-Verilator GPU search.

This is a planning and triage surface only. It does not run CIRCT, Verilator,
CUDA, or claim speedup. The plan makes the next useful experiment explicit:
lower scientific kernels to SystemVerilog through CIRCT, run them through the
existing Verilator sidecar path, then use LLVM-IR suitability plus measured
CPU/hybrid runs to identify GPU-useful sub-systems.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

DEFAULT_CANDIDATES = (
    {
        "id": "dense_matmul_tile",
        "scientific_shape": "batched dense matmul tile",
        "expected_gpu_bucket": "gpu_state_parallel",
        "why": [
            "regular_memory_access",
            "high_arithmetic_intensity",
            "low_observable_pressure",
            "many_independent_tiles_or_states",
        ],
        "first_shapes": ["64x1", "256x1", "1024x1"],
    },
    {
        "id": "stencil_2d_tile",
        "scientific_shape": "batched 2D stencil tile",
        "expected_gpu_bucket": "gpu_state_parallel_if_boundary_exchange_is_local",
        "why": [
            "regular_neighbor_access",
            "state_batching_possible",
            "small_control_surface",
        ],
        "first_shapes": ["128x1", "512x1"],
    },
    {
        "id": "batched_reduction",
        "scientific_shape": "batched vector reduction",
        "expected_gpu_bucket": "hybrid_or_specialized_gpu_kernel",
        "why": [
            "regular_memory_access",
            "tree_reduction_needs_structured_mapping",
            "generic_RTL_eval_may_be_synchronization_limited",
        ],
        "first_shapes": ["256x1", "1024x1", "1024x8"],
    },
    {
        "id": "softmax_exp_pipeline",
        "scientific_shape": "batched exp/softmax style pipeline",
        "expected_gpu_bucket": "gpu_state_parallel_or_math_kernel_mapping",
        "why": [
            "exp_unit_like_hot_ss_candidate",
            "regular_vector_memory",
            "benefit_depends_on_math_unit_lowering_not_whole_design_cpu_eval",
        ],
        "first_shapes": ["256x1", "1024x1"],
    },
    {
        "id": "sparse_branchy_solver",
        "scientific_shape": "sparse/branch-heavy iterative solver control",
        "expected_gpu_bucket": "cpu_parallel_or_new_mapping",
        "why": [
            "irregular_memory_access",
            "branch_heavy_control",
            "weak_state_independence_without_batching",
        ],
        "first_shapes": ["64x1"],
    },
)

def _tool(name: str) -> dict[str, Any]:
    return {"command": name, "available_on_path": shutil.which(name) is not None}


def _command(argv: list[str]) -> str:
    return " ".join(argv)

def build_plan(*, candidate_filter: str | None = None, repeat: int = 3) -> dict[str, Any]:
    candidates = [
        dict(candidate)
        for candidate in DEFAULT_CANDIDATES
        if candidate_filter is None or candidate["id"] == candidate_filter
    ]
    if candidate_filter and not candidates:
        raise ValueError(f"unknown candidate id: {candidate_filter}")
    if repeat <= 0:
        raise ValueError("repeat must be positive")

    toolchain = {
        "circt_opt": _tool("circt-opt"),
        "circt_translate": _tool("circt-translate"),
        "firtool": _tool("firtool"),
        "verilator": _tool("verilator"),
        "clangxx": _tool("clang++"),
    }
    circt_ready = any(
        toolchain[name]["available_on_path"]
        for name in ("circt_opt", "circt_translate", "firtool")
    )
    verilator_ready = bool(toolchain["verilator"]["available_on_path"])
    status = "planned_not_run"
    if not circt_ready:
        status = "blocked_circt_toolchain_missing"
    elif not verilator_ready:
        status = "blocked_verilator_missing"

    planned = []
    for order, candidate in enumerate(candidates, start=1):
        candidate_id = candidate["id"]
        mlir = f"artifacts/scientific_circt/{candidate_id}/{candidate_id}.mlir"
        sv = f"artifacts/scientific_circt/{candidate_id}/{candidate_id}.sv"
        obj_dir = f"artifacts/scientific_circt/{candidate_id}/obj_dir"
        ir = f"artifacts/scientific_circt/{candidate_id}/{candidate_id}.ll"
        suitability = f"reports/scientific_circt_{candidate_id}_llvm_rtl_gpu_suitability.json"
        template = f"config/slice_launch_templates/scientific_circt_{candidate_id}.json"
        measurements = [
            {
                "shape": shape,
                "repeat": repeat,
                "command": _command(
                    [
                        "PYTHONDONTWRITEBYTECODE=1",
                        "python3",
                        "src/tools/hybrid_template_repeat_median.py",
                        template,
                        "--shape",
                        shape,
                        "--repeat",
                        str(repeat),
                        "--write-report",
                        "--report-out",
                        f"reports/scientific_circt_{candidate_id}_repeat_median_{shape}.json",
                    ]
                ),
            }
            for shape in candidate["first_shapes"]
        ]
        planned.append(
            {
                **candidate,
                "order": order,
                "pipeline": [
                    {
                        "stage": "author_mlir_or_circt_input",
                        "output": mlir,
                        "acceptance": "small reviewed scientific kernel with explicit memories and control",
                    },
                    {
                        "stage": "circt_lower_to_systemverilog",
                        "output": sv,
                        "acceptance": "SystemVerilog generated without hand-authored RTL semantics changes",
                    },
                    {
                        "stage": "verilator_build",
                        "output": obj_dir,
                        "acceptance": "Verilator build passes and CPU reference observables are defined",
                    },
                    {
                        "stage": "emit_lowered_llvm_ir",
                        "output": ir,
                        "acceptance": "lowered IR is available for suitability analysis",
                    },
                    {
                        "stage": "static_gpu_suitability",
                        "command": _command(
                            [
                                "PYTHONDONTWRITEBYTECODE=1", "python3",
                                "src/tools/llvm_rtl_gpu_suitability_cli.py", "--ir", ir,
                                "--target", f"scientific_circt_{candidate_id}",
                                "--workload", candidate["scientific_shape"],
                                "--shape", candidate["first_shapes"][0],
                                "--write-report", "--report-out", suitability,
                            ]
                        ),
                        "output": suitability,
                        "acceptance": "recommended_path is recorded before GPU execution is attempted",
                    },
                    {
                        "stage": "measured_cpu_hybrid_repeat_median",
                        "measurements": measurements,
                        "acceptance": "coverage_output_equivalence passes and CPU/hybrid medians are recorded",
                    },
                ],
            }
        )

    return {
        "schema_version": 1,
        "surface": "scientific_circt_gpu_candidate_plan",
        "status": status,
        "objective": "lower scientific-compute kernels through CIRCT SystemVerilog, Verilator, and GPU suitability/timing gates",
        "toolchain": toolchain,
        "candidate_count": len(planned),
        "candidates": planned,
        "next_action": (
            "install_or_point_to_circt_then_materialize_dense_matmul_tile_first"
            if not circt_ready
            else "materialize_dense_matmul_tile_circt_sv_and_run_verilator_cpu_reference"
        ),
        "selection_policy": [
            "prefer regular-memory low-observable kernels before branch-heavy control",
            "require static suitability before GPU execution",
            "require coverage_output_equivalence before timing claims",
            "promote only repeat-median CPU-vs-hybrid evidence to usefulness claims",
        ],
        "non_claims": [
            "plan_only_not_circt_execution",
            "no_systemverilog_generated_by_this_plan",
            "no_verilator_build_by_this_plan",
            "no_gpu_execution",
            "no_speedup_claim",
            "no_automatic_partition_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", help="Limit the plan to one candidate id")
    parser.add_argument("--repeat", type=int, default=3, help="Planned repeat count for later timing")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        plan = build_plan(candidate_filter=args.candidate, repeat=args.repeat)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
