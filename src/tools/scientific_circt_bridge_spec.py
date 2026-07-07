#!/usr/bin/env python3
"""Derive metadata-driven source-variant bridge specs and gate headers.

Correctness authority remains runtime CPU/GPU equality; this module only
derives compile-time specialization and argv metadata gates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

import scientific_circt_hls_attention_head_variant as attention_head_variant
from scientific_circt_batch_stimulus_spec import (
    BatchStimulusSpec,
    batch_stimulus_spec_from_bridge,
)
import scientific_circt_hls_mlp_block_variants as mlp_block_variants

BYTES_BY_TYPE = {
    "uint8_t": 1,
    "uint16_t": 2,
    "uint32_t": 4,
    "uint64_t": 8,
    "int8_t": 1,
    "int16_t": 2,
    "int32_t": 4,
    "int64_t": 8,
}

RUNTIME_BOUNDARY_BY_ENTRYPOINT = {
    "direct-binary": "direct_callsite_hls_source_variant_boundary",
    "src-hybrid-verilator": "src_hybrid_verilator_callsite_bridge",
}


class BridgeSpecError(ValueError):
    """Raised when a metadata row cannot yield a fail-closed BridgeSpec."""


@dataclass(frozen=True)
class BridgeSpec:
    source_variant: str
    candidate: str
    shape: str
    entrypoint_kind: str
    runtime_boundary_kind: str
    input_element_type: str
    input_element_count: int
    output_element_type: str
    output_element_count: int
    run_gpu_outputs_symbol: str
    run_hybrid_json_symbol: str
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    fill_a: int
    fill_b: int
    fill_c: int
    fill_mask: int
    mix_j_mult: int
    mix_mask: int

def _mlp_block_ports(source_variant: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    variant = mlp_block_variants.VARIANTS[source_variant]
    return mlp_block_variants.input_port_names(variant), mlp_block_variants.output_port_names(variant)


def _attention_head4_ports() -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        attention_head_variant.input_port_names(4),
        attention_head_variant.output_port_names(4),
    )


PORT_NAMING: dict[str, Callable[[], tuple[tuple[str, ...], tuple[str, ...]]]] = {
    "attention_head4_hls_friendly": _attention_head4_ports,
    "mlp4_hls_friendly": lambda: _mlp_block_ports("mlp4_hls_friendly"),
    "block2_hls_friendly": lambda: _mlp_block_ports("block2_hls_friendly"),
    "inference2_hls_friendly": lambda: _mlp_block_ports("inference2_hls_friendly"),
}

SYMBOL_STEMS: dict[str, str] = {
    "attention_head4_hls_friendly": attention_head_variant.GPU_SYMBOL_STEM,
    "mlp4_hls_friendly": mlp_block_variants.VARIANTS["mlp4_hls_friendly"].name,
    "block2_hls_friendly": mlp_block_variants.VARIANTS["block2_hls_friendly"].name,
    "inference2_hls_friendly": mlp_block_variants.VARIANTS["inference2_hls_friendly"].name,
}


def expected_gpu_symbols(source_variant: str) -> tuple[str, str]:
    """Return the exact (run_gpu_outputs, run_hybrid_json) symbol names for a variant."""
    stem = SYMBOL_STEMS[source_variant]
    return f"{stem}_run_gpu_outputs", f"{stem}_run_hybrid_json"


def _mlp_fill_params(source_variant: str) -> tuple[int, int, int, int]:
    variant = mlp_block_variants.VARIANTS[source_variant]
    return variant.fill_a, variant.fill_b, variant.fill_c, variant.fill_mask


FILL_PARAMS: dict[str, Callable[[], tuple[int, int, int, int]]] = {
    "attention_head4_hls_friendly": lambda: (
        attention_head_variant.FILL_A,
        attention_head_variant.FILL_B,
        attention_head_variant.FILL_C,
        attention_head_variant.FILL_MASK,
    ),
    "mlp4_hls_friendly": lambda: _mlp_fill_params("mlp4_hls_friendly"),
    "block2_hls_friendly": lambda: _mlp_fill_params("block2_hls_friendly"),
    "inference2_hls_friendly": lambda: _mlp_fill_params("inference2_hls_friendly"),
}

MIX_PARAMS: dict[str, Callable[[], tuple[int, int]]] = {
    "attention_head4_hls_friendly": lambda: (
        attention_head_variant.MIX_J_MULT,
        attention_head_variant.MIX_MASK,
    ),
    "mlp4_hls_friendly": lambda: (mlp_block_variants.MIX_J_MULT, mlp_block_variants.MIX_MASK),
    "block2_hls_friendly": lambda: (mlp_block_variants.MIX_J_MULT, mlp_block_variants.MIX_MASK),
    "inference2_hls_friendly": lambda: (mlp_block_variants.MIX_J_MULT, mlp_block_variants.MIX_MASK),
}


def bridge_spec_from_metadata_row(row: dict[str, Any], *, selected: dict[str, Any] | None = None) -> BridgeSpec:
    """Derive a fail-closed BridgeSpec from one source-variant metadata row."""
    if row.get("metadata_complete") is not True:
        raise BridgeSpecError("metadata row is not metadata_complete")

    entrypoint_kind = row.get("entrypoint_kind")
    if entrypoint_kind not in RUNTIME_BOUNDARY_BY_ENTRYPOINT:
        raise BridgeSpecError(f"unsupported entrypoint_kind {entrypoint_kind!r}")

    runtime_boundary_kind = row.get("runtime_boundary_kind")
    if runtime_boundary_kind != RUNTIME_BOUNDARY_BY_ENTRYPOINT[entrypoint_kind]:
        raise BridgeSpecError(
            f"runtime_boundary_kind {runtime_boundary_kind!r} does not match entrypoint_kind {entrypoint_kind!r}"
        )

    if row.get("policy") != "promote_to_hls_gpu":
        raise BridgeSpecError(f"source variant policy {row.get('policy')!r} is not promote_to_hls_gpu")

    symbols = row.get("gpu_symbols") if isinstance(row.get("gpu_symbols"), dict) else {}
    run_gpu_outputs_symbol = symbols.get("run_gpu_outputs")
    run_hybrid_json_symbol = symbols.get("run_hybrid_json")
    layout = row.get("layout") if isinstance(row.get("layout"), dict) else {}
    input_layout = layout.get("input") if isinstance(layout.get("input"), dict) else {}
    output_layout = layout.get("output") if isinstance(layout.get("output"), dict) else {}
    input_element_type = input_layout.get("element_type")
    output_element_type = output_layout.get("element_type")
    if input_element_type not in BYTES_BY_TYPE:
        raise BridgeSpecError(f"unsupported input element type {input_element_type!r}")
    if output_element_type not in BYTES_BY_TYPE:
        raise BridgeSpecError(f"unsupported output element type {output_element_type!r}")

    input_element_count = input_layout.get("element_count")
    output_element_count = output_layout.get("element_count")
    if not isinstance(input_element_count, int) or input_element_count <= 0:
        raise BridgeSpecError("invalid input element count")
    if not isinstance(output_element_count, int) or output_element_count <= 0:
        raise BridgeSpecError("invalid output element count")

    source_variant = row.get("source_variant")
    if not isinstance(source_variant, str) or source_variant not in PORT_NAMING:
        raise BridgeSpecError(f"no port naming registered for source variant {source_variant!r}")
    expected_run_gpu_outputs, expected_run_hybrid_json = expected_gpu_symbols(source_variant)
    if run_gpu_outputs_symbol != expected_run_gpu_outputs:
        raise BridgeSpecError("run_gpu_outputs symbol does not match source variant")
    if run_hybrid_json_symbol != expected_run_hybrid_json:
        raise BridgeSpecError("run_hybrid_json symbol does not match source variant")
    input_ports, output_ports = PORT_NAMING[source_variant]()
    fill_a, fill_b, fill_c, fill_mask = FILL_PARAMS[source_variant]()
    mix_j_mult, mix_mask = MIX_PARAMS[source_variant]()
    if len(input_ports) != input_element_count:
        raise BridgeSpecError(
            f"derived input port count {len(input_ports)} != input element count {input_element_count}"
        )
    if len(output_ports) != output_element_count:
        raise BridgeSpecError(
            f"derived output port count {len(output_ports)} != output element count {output_element_count}"
        )

    candidate = row.get("candidate")
    shape = row.get("shape")
    if not isinstance(candidate, str) or not isinstance(shape, str):
        raise BridgeSpecError("metadata row missing candidate or shape")

    if selected is not None:
        if selected.get("candidate") != candidate:
            raise BridgeSpecError("selected boundary candidate does not match metadata row")
        if selected.get("source_variant") != source_variant:
            raise BridgeSpecError("selected boundary source_variant does not match metadata row")
        if selected.get("shape") != shape:
            raise BridgeSpecError("selected boundary shape does not match metadata row")

    return BridgeSpec(
        source_variant=source_variant,
        candidate=candidate,
        shape=shape,
        entrypoint_kind=str(entrypoint_kind),
        runtime_boundary_kind=str(runtime_boundary_kind),
        input_element_type=str(input_element_type),
        input_element_count=int(input_element_count),
        output_element_type=str(output_element_type),
        output_element_count=int(output_element_count),
        run_gpu_outputs_symbol=run_gpu_outputs_symbol,
        run_hybrid_json_symbol=run_hybrid_json_symbol,
        input_ports=tuple(input_ports),
        output_ports=tuple(output_ports),
        fill_a=fill_a,
        fill_b=fill_b,
        fill_c=fill_c,
        fill_mask=fill_mask,
        mix_j_mult=mix_j_mult,
        mix_mask=mix_mask,
    )


def batch_stimulus_spec_from_metadata_row(
    row: dict[str, Any],
    *,
    selected: dict[str, Any] | None = None,
    state_count: int | None = None,
    steps: int | None = None,
    slot_stride: str = "align_up(numStateBytes, 16)",
) -> BatchStimulusSpec:
    """Derive the FC-085 independent-state stimulus contract from metadata."""
    bridge = bridge_spec_from_metadata_row(row, selected=selected)
    return batch_stimulus_spec_from_bridge(
        row,
        bridge,
        error=BridgeSpecError,
        state_count=state_count,
        steps=steps,
        slot_stride=slot_stride,
    )


def _cxx_string_literal(value: object) -> str:
    return json.dumps(str(value))


def _render_apply_inputs_macro(input_ports: tuple[str, ...]) -> str:
    assignments = " ".join(f"top.{port} = in.x[{k}];" for k, port in enumerate(input_ports))
    return f"#define SCI_CIRCT_BRIDGE_APPLY_INPUTS(top, in) {assignments}"


def _render_read_outputs_macro(output_ports: tuple[str, ...]) -> str:
    assignments = " ".join(f"base.y[{k}] = top.{port};" for k, port in enumerate(output_ports))
    return f"#define SCI_CIRCT_BRIDGE_READ_OUTPUTS(top, base) {assignments}"


def _render_fill_value_macro(spec: BridgeSpec) -> str:
    return (
        "#define SCI_CIRCT_BRIDGE_FILL_VALUE(i, j) "
        f"((uint8_t)(((i) * {spec.fill_a}u + (j) * {spec.fill_b}u + {spec.fill_c}u) & {spec.fill_mask:#x}u))"
    )


def _render_mix_value_macro(spec: BridgeSpec) -> str:
    return (
        "#define SCI_CIRCT_BRIDGE_MIX_VALUE(r, j) "
        f"((uint64_t)(((r) + (j) * {spec.mix_j_mult}) & {spec.mix_mask}))"
    )


def render_bridge_gate_header(spec: BridgeSpec) -> str:
    """Render the generated bridge gate header for one BridgeSpec."""
    lines = [
        "/* Generated from source-variant metadata by scientific_circt_source_variant_runtime_handoff.py. */",
        "#pragma once",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_CANDIDATE {_cxx_string_literal(spec.candidate)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_SOURCE_VARIANT {_cxx_string_literal(spec.source_variant)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_SHAPE {_cxx_string_literal(spec.shape)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_RUN_GPU_OUTPUTS {_cxx_string_literal(spec.run_gpu_outputs_symbol)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_RUN_HYBRID_JSON {_cxx_string_literal(spec.run_hybrid_json_symbol)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_TYPE {_cxx_string_literal(spec.input_element_type)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_COUNT {_cxx_string_literal(spec.input_element_count)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_TYPE {_cxx_string_literal(spec.output_element_type)}",
        f"#define SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_COUNT {_cxx_string_literal(spec.output_element_count)}",
        f"#define SCI_CIRCT_BRIDGE_INPUT_ELEMENT_TYPE {spec.input_element_type}",
        f"#define SCI_CIRCT_BRIDGE_INPUT_ELEMENT_COUNT {spec.input_element_count}",
        f"#define SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_TYPE {spec.output_element_type}",
        f"#define SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_COUNT {spec.output_element_count}",
        "",
        _render_apply_inputs_macro(spec.input_ports),
        "",
        _render_read_outputs_macro(spec.output_ports),
        "",
        _render_fill_value_macro(spec),
        "",
        _render_mix_value_macro(spec),
        "",
    ]
    return "\n".join(lines)
