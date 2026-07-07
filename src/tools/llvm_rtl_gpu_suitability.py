#!/usr/bin/env python3
"""Classify lowered RTL LLVM IR for GPU execution strategy.

This is an analysis surface only. It does not execute RTL, change runtime ABI,
or claim speedup. The goal is to make the "GPU, CPU parallel, or new mapping"
decision reproducible from LLVM IR features.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Mapping

from llvm_ir_parse import called_global_names, external_calls, extract_functions, reachable_from


BRANCH_RE = re.compile(r"\b(br\s+i1|switch\s+|indirectbr\s+)")
CALL_RE = re.compile(r"\b(?:call|tail\s+call|invoke)\b")
GEP_RE = re.compile(r"\bgetelementptr\b")
LOAD_RE = re.compile(r"\bload\b")
STORE_RE = re.compile(r"\bstore\b")
MEMORY_RE = re.compile(r"\b(load|store|getelementptr)\b")
ATOMIC_RE = re.compile(r"\b(atomicrmw|cmpxchg|fence)\b")
VOLATILE_RE = re.compile(r"\bvolatile\b")
INLINE_ASM_RE = re.compile(r"\basm\b")

STATE_TOKENS = (
    "state",
    "state_id",
    "stateidx",
    "state_index",
    "nstates",
    "state_stride",
    "stride",
    "storage",
)
OBSERVABLE_TOKENS = (
    "stdout",
    "mailbox",
    "finish",
    "trace",
    "vcd",
    "printf",
    "fprintf",
    "mcycle",
    "minstret",
    "pc",
    "observable",
)
IRREGULAR_MEMORY_TOKENS = (
    "inttoptr",
    "ptrtoint",
    "addrspacecast",
    "phi ptr",
    "select ptr",
)
RTL_CPU_TOKENS = (
    "veer",
    "ifu",
    "dec_",
    "exu",
    "lsu",
    "dccm",
    "iccm",
    "mcycle",
    "minstret",
)
STATE_PARALLEL_TOKENS = (
    "ita",
    "mha",
    "attention",
    "kv",
    "score",
    "state_parallel",
)


def _nonempty_ir_lines(ir_text: str) -> list[str]:
    return [
        line.strip()
        for line in ir_text.splitlines()
        if line.strip() and not line.lstrip().startswith(";")
    ]


def _count_token_lines(lines: list[str], tokens: tuple[str, ...]) -> int:
    lowered = [line.lower() for line in lines]
    return sum(1 for line in lowered if any(token in line for token in tokens))


def _parse_shape(shape: str | None) -> tuple[int | None, int | None]:
    if not shape:
        return None, None
    match = re.fullmatch(r"(\d+)x(\d+)", shape.strip())
    if not match:
        raise ValueError(f"shape must use NxS form, got {shape!r}")
    return int(match.group(1)), int(match.group(2))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _memory_regularity(lines: list[str]) -> tuple[float, dict[str, int]]:
    memory_lines = [line for line in lines if MEMORY_RE.search(line)]
    if not memory_lines:
        return 1.0, {
            "memory_instruction_count": 0,
            "regular_memory_hint_count": 0,
            "irregular_memory_hint_count": 0,
        }
    lowered = [line.lower() for line in memory_lines]
    regular = sum(
        1
        for line in lowered
        if "getelementptr inbounds" in line
        or any(token in line for token in ("state", "stride", "storage", "idxprom"))
    )
    irregular = sum(1 for line in lowered if any(token in line for token in IRREGULAR_MEMORY_TOKENS))
    score = (regular + max(0, len(memory_lines) - irregular)) / (2 * len(memory_lines))
    score = max(0.0, min(1.0, score))
    return round(score, 6), {
        "memory_instruction_count": len(memory_lines),
        "regular_memory_hint_count": regular,
        "irregular_memory_hint_count": irregular,
    }


def analyze_llvm_rtl_gpu_suitability(
    ir_text: str,
    *,
    target: str,
    shape: str | None = None,
    workload: str | None = None,
    entry: str | None = None,
) -> dict[str, object]:
    reachable_function_count = None
    reachable_functions = None
    external_call_names: list[str] = []
    llvm_intrinsic_call_names: list[str] = []
    if entry:
        funcs = extract_functions(ir_text)
        if entry not in funcs:
            raise ValueError(f"entry function {entry!r} was not found in LLVM IR")
        reachable_functions = sorted(reachable_from(entry, funcs))
        ir_text = "\n".join(funcs[name] for name in reachable_functions)
        reachable_function_count = len(reachable_functions)
        external_call_names = sorted(external_calls(set(reachable_functions), funcs))
        llvm_intrinsic_call_names = sorted(
            {
                callee
                for name in reachable_functions
                for callee in called_global_names(funcs[name])
                if callee.startswith("llvm.")
            }
        )
    nstates, steps = _parse_shape(shape)
    lines = _nonempty_ir_lines(ir_text)
    instruction_count = len(lines)
    lowered_text = "\n".join(lines).lower()

    branch_count = sum(1 for line in lines if BRANCH_RE.search(line))
    call_count = sum(1 for line in lines if CALL_RE.search(line))
    load_count = sum(1 for line in lines if LOAD_RE.search(line))
    store_count = sum(1 for line in lines if STORE_RE.search(line))
    gep_count = sum(1 for line in lines if GEP_RE.search(line))
    atomic_count = sum(1 for line in lines if ATOMIC_RE.search(line))
    volatile_count = sum(1 for line in lines if VOLATILE_RE.search(line))
    inline_asm_count = sum(1 for line in lines if INLINE_ASM_RE.search(line))
    state_token_lines = _count_token_lines(lines, STATE_TOKENS)
    observable_token_lines = _count_token_lines(lines, OBSERVABLE_TOKENS)
    rtl_cpu_token_lines = _count_token_lines(lines, RTL_CPU_TOKENS)
    state_parallel_token_lines = _count_token_lines(lines, STATE_PARALLEL_TOKENS)
    memory_regularity_score, memory_detail = _memory_regularity(lines)

    branch_density = _ratio(branch_count, instruction_count)
    observable_pressure = _ratio(observable_token_lines + call_count, instruction_count)
    state_parallel_shape = bool(nstates and nstates >= 16 and (steps == 1 or steps is None))
    repeated_step_shape = bool(steps and steps > 1 and (nstates or 1) <= 1)
    state_independence_score = 0.0
    if state_token_lines:
        state_independence_score += 0.45
    if state_parallel_shape:
        state_independence_score += 0.35
    if atomic_count == 0:
        state_independence_score += 0.15
    if observable_pressure < 0.08:
        state_independence_score += 0.05
    state_independence_score = round(min(1.0, state_independence_score), 6)

    workload_text = f"{target} {workload or ''}".lower()
    rtl_cpu_like = rtl_cpu_token_lines > 0 or any(token in workload_text for token in RTL_CPU_TOKENS)
    state_parallel_like = state_parallel_token_lines > 0 or any(
        token in workload_text for token in STATE_PARALLEL_TOKENS
    )

    poor_reasons: list[str] = []
    good_reasons: list[str] = []
    if branch_density >= 0.07:
        poor_reasons.append("high_branch_density")
    if atomic_count:
        poor_reasons.append("unsupported_atomic_or_fence")
    if volatile_count or inline_asm_count:
        poor_reasons.append("unsupported_volatile_or_inline_asm")
    if external_call_names:
        poor_reasons.append("external_side_effect_call")
    if memory_regularity_score < 0.55:
        poor_reasons.append("irregular_memory_access")
    if observable_pressure >= 0.08:
        poor_reasons.append("high_observable_pressure")
    if state_independence_score < 0.55:
        poor_reasons.append("weak_state_independence")
    if repeated_step_shape:
        poor_reasons.append("single_state_repeated_step_shape")
    if rtl_cpu_like and observable_pressure >= 0.05:
        poor_reasons.append("rtl_cpu_core_with_observable_pressure")

    if state_parallel_shape:
        good_reasons.append("state_parallel_shape")
    if memory_regularity_score >= 0.70:
        good_reasons.append("regular_memory_access")
    if branch_density < 0.06:
        good_reasons.append("low_branch_density")
    if observable_pressure < 0.08:
        good_reasons.append("low_observable_pressure")
    if state_independence_score >= 0.55:
        good_reasons.append("state_independence_hints_present")
    if state_parallel_like:
        good_reasons.append("state_parallel_workload_hint")

    if (
        state_parallel_shape
        and state_parallel_like
        and memory_regularity_score >= 0.60
        and branch_density < 0.10
        and observable_pressure < 0.10
    ):
        verdict = "good_state_parallel"
        recommended_path = "gpu_state_parallel"
    elif poor_reasons:
        verdict = "poor_requires_new_implementation"
        recommended_path = "cpu_parallel_or_gem_like_mapping"
    else:
        verdict = "uncertain_requires_definition_gate"
        recommended_path = "define_measurement_before_gpu_execution"

    return {
        "schema_version": 1,
        "surface": "llvm_rtl_gpu_suitability",
        "schema_role": "llvm_rtl_gpu_suitability_analysis",
        "target": target,
        "workload": workload,
        "entry": entry,
        "reachable_function_count": reachable_function_count,
        "reachable_functions": reachable_functions,
        "shape": shape,
        "status": "analyzed",
        "verdict": verdict,
        "recommended_path": recommended_path,
        "metrics": {
            "instruction_count": instruction_count,
            "branch_count": branch_count,
            "branch_density": branch_density,
            "load_count": load_count,
            "store_count": store_count,
            "gep_count": gep_count,
            "call_count": call_count,
            "atomic_count": atomic_count,
            "volatile_count": volatile_count,
            "inline_asm_count": inline_asm_count,
            "external_call_count": len(external_call_names),
            "external_calls": external_call_names,
            "llvm_intrinsic_call_count": len(llvm_intrinsic_call_names),
            "llvm_intrinsic_calls": llvm_intrinsic_call_names,
            "memory_regularity_score": memory_regularity_score,
            **memory_detail,
            "state_token_line_count": state_token_lines,
            "state_independence_score": state_independence_score,
            "observable_token_line_count": observable_token_lines,
            "observable_pressure": observable_pressure,
            "rtl_cpu_token_line_count": rtl_cpu_token_lines,
            "state_parallel_token_line_count": state_parallel_token_lines,
        },
        "classification_inputs": {
            "state_parallel_shape": state_parallel_shape,
            "repeated_step_shape": repeated_step_shape,
            "rtl_cpu_like": rtl_cpu_like,
            "state_parallel_like": state_parallel_like,
        },
        "reasons": {
            "positive": good_reasons,
            "negative": poor_reasons,
        },
        "non_claims": [
            "no_speedup_claim",
            "no_runtime_abi_change",
            "no_gpu_execution",
            "no_correctness_equivalence_claim",
        ],
    }


def _load_ir(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _write_report(path: str, report: Mapping[str, object]) -> None:
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", required=True, help="LLVM IR text file to analyze")
    parser.add_argument("--entry", help="Optional LLVM function entry to analyze")
    parser.add_argument("--target", required=True, help="Target or design name")
    parser.add_argument("--shape", help="Optional workload shape in NxS form, for example 64x1")
    parser.add_argument("--workload", help="Optional workload/case label")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        report = analyze_llvm_rtl_gpu_suitability(
            _load_ir(args.ir),
            target=args.target,
            shape=args.shape,
            workload=args.workload,
            entry=args.entry,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        _write_report(args.report_out, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
