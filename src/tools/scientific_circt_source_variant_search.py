#!/usr/bin/env python3
"""Closed-loop source-variant rewrite search core for scientific CIRCT probes."""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Any, Callable

import scientific_circt_source_variant_regression as regression

INTERMEDIATE_ABS_DELTA = 3.0
FALSIFICATION_RELATIVE_BAND = 0.10
FALSIFICATION_ABS_FLOOR = 0.05


@dataclass(frozen=True)
class BlockDescriptor:
    candidate: str
    source_variant_stem: str
    module_stem: str
    kind: str
    eval_unit_cpp: str
    fill_a: int
    fill_b: int
    fill_c: int
    fill_mask: int
    mix_j_mult: int
    mix_mask: int
    unit_inputs: int
    unit_outputs: int
    output_width: int = 64
    input_permutation: tuple[int, ...] | None = None
    shared_accumulator: bool = False


@dataclass(frozen=True)
class Replicate:
    n: int


@dataclass(frozen=True)
class UnrollDensity:
    m: int


@dataclass(frozen=True)
class PackInputs:
    width: str


Transform = Replicate | UnrollDensity | PackInputs


@dataclass(frozen=True)
class VariantPlan:
    transforms: tuple[Transform, ...] = ()


@dataclass(frozen=True)
class PlanShape:
    units: int = 1
    inner_repeat: int = 1000
    packing: str = "uint8"


def plan_shape(plan: VariantPlan) -> PlanShape:
    shape = PlanShape()
    for transform in plan.transforms:
        if isinstance(transform, Replicate):
            shape = PlanShape(transform.n, shape.inner_repeat, shape.packing)
        elif isinstance(transform, UnrollDensity):
            shape = PlanShape(shape.units, transform.m, shape.packing)
        elif isinstance(transform, PackInputs):
            shape = PlanShape(shape.units, shape.inner_repeat, transform.width)
    return shape


def plan_name(descriptor: BlockDescriptor, plan: VariantPlan) -> str:
    shape = plan_shape(plan)
    return f"{descriptor.source_variant_stem}{shape.units}_u{shape.inner_repeat}_{shape.packing}"


def enumerate_plans(gate: str) -> list[VariantPlan]:
    if gate not in {"intermediate", "falsification"}:
        raise ValueError("gate must be intermediate or falsification")
    plans = [VariantPlan()]
    plans.extend(VariantPlan((Replicate(n),)) for n in (1, 2, 3, 4, 6, 8))
    plans.extend(VariantPlan((Replicate(4), UnrollDensity(m))) for m in (250, 500, 2000))
    plans.append(VariantPlan((Replicate(4), PackInputs("uint32"))))
    return plans


def _speedup(report: dict[str, Any]) -> float | None:
    for key in ("cpu_to_bridge_hybrid_wall_speedup", "observed_speedup"):
        value = report.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
    observed = report.get("observed") if isinstance(report.get("observed"), dict) else {}
    average = report.get("average") if isinstance(report.get("average"), dict) else {}
    for payload in (observed, average):
        value = payload.get("cpu_to_bridge_hybrid_wall_speedup")
        if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
    return None


def _samples(result: dict[str, Any]) -> list[dict[str, Any]]:
    samples = result.get("samples")
    if isinstance(samples, list):
        return [sample for sample in samples if isinstance(sample, dict)]
    return [result]


def _oracle_ok(sample: dict[str, Any]) -> bool:
    status = sample.get("status")
    output_ok = sample.get("cpu_vs_gpu_output_equal", sample.get("output_equal")) is True
    checksum_ok = sample.get("cpu_vs_gpu_control_checksum_equal", sample.get("checksum_equal")) is True
    return status in regression.DISPATCHED_STATUSES | {"hls_variant_measured"} and output_ok and checksum_ok


def _median_result(result: dict[str, Any]) -> float | None:
    values = [_speedup(sample) for sample in _samples(result)]
    numeric = [value for value in values if value is not None]
    return float(statistics.median(numeric)) if numeric else None


def rank_variants(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for result in results:
        median = _median_result(result)
        if median is not None:
            ranked.append({**result, "median_cpu_to_bridge_hybrid_wall_speedup": median})
    return sorted(ranked, key=lambda item: (-item["median_cpu_to_bridge_hybrid_wall_speedup"], str(item.get("variant"))))


def _any_oracle_mismatch(results: list[dict[str, Any]]) -> bool:
    return any(not _oracle_ok(sample) for result in results for sample in _samples(result))


def decide_intermediate_gate(baseline_median: float, results: list[dict[str, Any]]) -> tuple[bool, str]:
    if _any_oracle_mismatch(results):
        return False, "oracle_mismatch_in_search"
    ranked = rank_variants(results)
    if not ranked:
        return False, "speedup_out_of_band"
    top = ranked[0]["median_cpu_to_bridge_hybrid_wall_speedup"]
    return (True, "passed") if top >= baseline_median + INTERMEDIATE_ABS_DELTA else (False, "below_intermediate_delta")


def decide_falsification_gate(reference_median: float, results: list[dict[str, Any]]) -> tuple[bool, str]:
    if _any_oracle_mismatch(results):
        return False, "oracle_mismatch_in_search"
    ranked = rank_variants(results)
    if not ranked:
        return False, "speedup_out_of_band"
    band = max(FALSIFICATION_ABS_FLOOR, reference_median * FALSIFICATION_RELATIVE_BAND)
    top = ranked[0]["median_cpu_to_bridge_hybrid_wall_speedup"]
    return (True, "passed") if abs(top - reference_median) <= band else (False, "speedup_out_of_band")


def _pack_roundtrip(values: list[int], width: str) -> bool:
    if width == "uint8":
        return list(values) == values
    if width != "uint32":
        return False
    packed = []
    for idx in range(0, len(values), 4):
        word = 0
        for lane, value in enumerate(values[idx : idx + 4]):
            word |= (value & 0xFF) << (lane * 8)
        packed.append(word)
    unpacked = [(word >> (lane * 8)) & 0xFF for word in packed for lane in range(4)]
    return unpacked[: len(values)] == values


def _mix(base: list[int], repeat: int, j_mult: int, mask: int) -> list[int]:
    out = [0 for _ in base]
    for r in range(repeat):
        for j, value in enumerate(base):
            out[j] = (out[j] + value) ^ ((r + j * j_mult) & mask)
    return out


def transform_obligation_holds(
    descriptor: BlockDescriptor,
    plan: VariantPlan,
    py_reference_eval: Callable[[list[int]], list[int]],
) -> bool:
    shape = plan_shape(plan)
    if shape.units <= 0 or shape.inner_repeat <= 0:
        return False
    total_inputs = descriptor.unit_inputs * shape.units
    values = [(i * descriptor.fill_a + j * descriptor.fill_b + descriptor.fill_c) & descriptor.fill_mask for i in range(2) for j in range(total_inputs)]
    if not _pack_roundtrip(values, shape.packing):
        return False
    first_actual: list[int] | None = None
    base_outputs: list[int] = []
    for unit in range(shape.units):
        start = unit * descriptor.unit_inputs
        local = values[start : start + descriptor.unit_inputs]
        expected = py_reference_eval(local)
        if len(expected) != descriptor.unit_outputs:
            return False
        actual_input = local
        if descriptor.input_permutation is not None:
            if sorted(descriptor.input_permutation) != list(range(descriptor.unit_inputs)):
                return False
            actual_input = [local[idx] for idx in descriptor.input_permutation]
        actual = py_reference_eval(actual_input)
        if descriptor.shared_accumulator:
            first_actual = actual if first_actual is None else first_actual
            actual = first_actual
        if actual != expected:
            return False
        base_outputs.extend(actual)
    return _mix(base_outputs, shape.inner_repeat, descriptor.mix_j_mult, descriptor.mix_mask) == _mix(
        base_outputs, shape.inner_repeat, descriptor.mix_j_mult, descriptor.mix_mask
    )


ATTENTION_EVAL_UNIT_CPP = r'''__host__ __device__ static void eval_head(const uint8_t* x, uint64_t* y) {
  uint64_t score0 = 0, score1 = 0;
  for (int j = 0; j < 4; ++j) {
    score0 += uint64_t(x[j]) * x[4 + j];
    score1 += uint64_t(x[j]) * x[8 + j];
  }
  uint64_t w0 = (score0 + 1) * (score0 + 1);
  uint64_t w1 = (score1 + 1) * (score1 + 1);
  for (int j = 0; j < 4; ++j) y[j] = w0 * x[12 + j] + w1 * x[16 + j];
}'''


ATTENTION_DESCRIPTOR = BlockDescriptor(
    candidate="microgpt_attention_head",
    source_variant_stem="attention_head",
    module_stem="MicrogptAttentionHeadHls",
    kind="attention",
    eval_unit_cpp=ATTENTION_EVAL_UNIT_CPP,
    fill_a=17,
    fill_b=11,
    fill_c=1,
    fill_mask=0x7F,
    mix_j_mult=1,
    mix_mask=31,
    unit_inputs=20,
    unit_outputs=4,
    output_width=56,
)
