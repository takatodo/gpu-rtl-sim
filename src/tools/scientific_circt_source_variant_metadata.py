#!/usr/bin/env python3
"""Generate source-variant runtime bridge metadata from existing reports."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scientific_circt_bridge_spec import (
    BYTES_BY_TYPE,
    PORT_NAMING,
    RUNTIME_BOUNDARY_BY_ENTRYPOINT as PROMOTED_RUNTIME_BOUNDARY_BY_ENTRYPOINT,
    BridgeSpecError,
    bridge_spec_from_metadata_row,
)

REPORT = Path("reports/scientific_circt_source_variant_metadata.json")
SRC_HYBRID_BRIDGE = "src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp"
SRC_HYBRID_OUT_DIR = "artifacts/scientific_circt/source_variant_verilator_entrypoint"

DEFAULT_SOURCE_VARIANTS = [
    "attention_head4_hls_friendly",
    "mlp4_hls_friendly",
    "inference2_hls_friendly",
    "block2_hls_friendly",
]

ENTRYPOINT_BY_VARIANT = {
    "attention_head4_hls_friendly": "direct-binary",
    "mlp4_hls_friendly": "direct-binary",
    "inference2_hls_friendly": "src-hybrid-verilator",
    "block2_hls_friendly": "fallback-baseline",
}

RUNTIME_BOUNDARY_BY_ENTRYPOINT = {
    "direct-binary": "direct_callsite_hls_source_variant_boundary",
    "src-hybrid-verilator": "src_hybrid_verilator_callsite_bridge",
    "fallback-baseline": "cpu_or_baseline_fallback",
}

def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def variants(summary: dict[str, Any]) -> list[dict[str, Any]]:
    payload = summary.get("variants")
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(summary.get("variant"), str):
        return [summary]
    return []


def combined_hls_summary(primary: dict[str, Any], extras: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    by_name: dict[str, dict[str, Any]] = {}
    for summary in [primary, *(extras or [])]:
        for variant in variants(summary):
            name = variant.get("variant")
            if isinstance(name, str):
                by_name[name] = variant
    combined = dict(primary)
    combined["schema_version"] = 1
    combined["surface"] = "scientific_circt_combined_hls_source_variant_summary"
    combined["variants"] = [by_name[name] for name in sorted(by_name)]
    return combined


def variant_report(summary: dict[str, Any], source_variant: str) -> dict[str, Any] | None:
    for variant in variants(summary):
        if variant.get("variant") == source_variant:
            return variant
    return None


def boundary_rows(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    selected = matrix.get("selected_next_source_variant_runtime_boundary")
    if isinstance(selected, dict):
        rows.append(selected)
    queue = matrix.get("source_variant_runtime_integration_queue")
    if isinstance(queue, list):
        for row in queue:
            if isinstance(row, dict) and row not in rows:
                rows.append(row)
    return rows


def boundary_for_variant(matrix: dict[str, Any], hls_summary: dict[str, Any], source_variant: str) -> dict[str, Any] | None:
    for row in boundary_rows(matrix):
        if row.get("source_variant") == source_variant:
            return row
    variant = variant_report(hls_summary, source_variant)
    if variant is None:
        return None
    comparison = variant.get("comparison") if isinstance(variant.get("comparison"), dict) else {}
    return {
        "candidate": variant.get("candidate"),
        "source_variant": source_variant,
        "shape": variant.get("shape"),
        "rank": None,
        "selection_reason": "fallback_or_non_promoted_source_variant_from_hls_variant_report",
        "baseline_speedup": comparison.get("baseline_speedup"),
        "variant_speedup": comparison.get("variant_speedup"),
        "speedup_delta": comparison.get("speedup_delta"),
        "steps": 1,
    }


def _rel_path(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return Path(value).as_posix()


def _artifact_record(value: object) -> dict[str, Any]:
    path = _rel_path(value)
    if path is None:
        return {"path": None, "present": False}
    return {"path": path, "present": Path(path).exists()}


def _parse_array_struct(source: str, name: str) -> dict[str, Any] | None:
    match = re.search(rf"struct\s+{re.escape(name)}\s*\{{\s*([A-Za-z0-9_:]+)\s+([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\];\s*\}};", source)
    if not match:
        return None
    c_type, field, count = match.groups()
    count_i = int(count)
    bytes_by_type = {
        "uint8_t": 1,
        "uint16_t": 2,
        "uint32_t": 4,
        "uint64_t": 8,
        "int8_t": 1,
        "int16_t": 2,
        "int32_t": 4,
        "int64_t": 8,
    }
    element_bytes = bytes_by_type.get(c_type)
    return {
        "struct": name,
        "field": field,
        "element_type": c_type,
        "element_count": count_i,
        "bytes_per_state": count_i * element_bytes if element_bytes is not None else None,
    }


def extract_gpu_metadata(gpu_source: object) -> dict[str, Any]:
    path = _rel_path(gpu_source)
    if path is None:
        return {"gpu_source": {"path": None, "present": False}, "symbols": {}, "layout": {}}
    source_path = Path(path)
    if not source_path.exists():
        return {"gpu_source": {"path": path, "present": False}, "symbols": {}, "layout": {}}
    text = source_path.read_text(encoding="utf-8")
    symbols = re.findall(r'extern\s+"C"\s+int\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(', text)
    run_outputs = next((symbol for symbol in symbols if symbol.endswith("_run_gpu_outputs")), None)
    run_hybrid_json = next((symbol for symbol in symbols if symbol.endswith("_run_hybrid_json")), None)
    layout = {
        "input": _parse_array_struct(text, "In"),
        "output": _parse_array_struct(text, "Out"),
    }
    return {
        "gpu_source": {"path": path, "present": True},
        "symbols": {
            "extern_c": symbols,
            "run_gpu_outputs": run_outputs,
            "run_hybrid_json": run_hybrid_json,
        },
        "layout": layout,
    }


def _policy_for_variant(variant: dict[str, Any], entrypoint: str) -> str:
    if entrypoint == "fallback-baseline":
        return "fallback_baseline_no_speedup_improvement"
    comparison = variant.get("comparison") if isinstance(variant.get("comparison"), dict) else {}
    if variant.get("status") == "hls_variant_improved" or comparison.get("speedup_improved") is True:
        return "promote_to_hls_gpu"
    return "fallback_baseline_no_speedup_improvement"


def source_variant_metadata_row(
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    source_variant: str,
) -> dict[str, Any]:
    variant = variant_report(hls_summary, source_variant)
    if variant is None:
        raise ValueError(f"HLS source variant report missing {source_variant}")
    boundary = boundary_for_variant(matrix, hls_summary, source_variant)
    if boundary is None:
        raise ValueError(f"dispatch matrix and HLS report missing boundary for {source_variant}")
    artifacts = variant.get("artifacts") if isinstance(variant.get("artifacts"), dict) else {}
    entrypoint = ENTRYPOINT_BY_VARIANT.get(source_variant)
    if entrypoint is None:
        comparison = variant.get("comparison") if isinstance(variant.get("comparison"), dict) else {}
        entrypoint = "direct-binary" if comparison.get("speedup_improved") is True else "fallback-baseline"
    gpu = extract_gpu_metadata(artifacts.get("gpu_library_source"))
    runtime_boundary_kind = RUNTIME_BOUNDARY_BY_ENTRYPOINT[entrypoint]
    row: dict[str, Any] = {
        "source_variant": source_variant,
        "candidate": boundary.get("candidate") or variant.get("candidate"),
        "shape": boundary.get("shape") or variant.get("shape"),
        "rank": boundary.get("rank"),
        "selection_reason": boundary.get("selection_reason"),
        "variant_status": variant.get("status"),
        "entrypoint_kind": entrypoint,
        "runtime_boundary_kind": runtime_boundary_kind,
        "policy": _policy_for_variant(variant, entrypoint),
        "boundary": {
            "candidate": boundary.get("candidate") or variant.get("candidate"),
            "source_variant": source_variant,
            "shape": boundary.get("shape") or variant.get("shape"),
            "rank": boundary.get("rank"),
            "steps": boundary.get("steps"),
            "baseline_speedup": boundary.get("baseline_speedup"),
            "variant_speedup": boundary.get("variant_speedup"),
            "speedup_delta": boundary.get("speedup_delta"),
            "cpu_owner": boundary.get("cpu_owner"),
            "gpu_subsystem": boundary.get("gpu_subsystem"),
        },
        "comparison": variant.get("comparison") if isinstance(variant.get("comparison"), dict) else None,
        "dimensions": {
            "repeat": variant.get("repeat"),
            "inner_repeat": variant.get("inner_repeat"),
            "integration_batches": variant.get("integration_batches"),
        },
        "artifacts": {
            "direct_callsite_binary": _artifact_record(artifacts.get("direct_callsite_binary")),
            "direct_callsite_bridge_source": _artifact_record(artifacts.get("direct_callsite_bridge_source")),
            "gpu_library": _artifact_record(artifacts.get("gpu_library")),
            "gpu_library_source": gpu["gpu_source"],
            "systemverilog": _artifact_record(artifacts.get("systemverilog")),
            "verilator_mdir": _artifact_record(artifacts.get("verilator_mdir")),
            "src_hybrid_bridge_source": _artifact_record(SRC_HYBRID_BRIDGE),
            "src_hybrid_out_dir": _artifact_record(SRC_HYBRID_OUT_DIR),
        },
        "gpu_symbols": gpu["symbols"],
        "layout": gpu["layout"],
        "fallback_reason": None,
    }
    if entrypoint == "fallback-baseline":
        row["fallback_reason"] = "source_variant_is_equality_checked_but_does_not_improve_baseline_speedup"
    row["metadata_complete"] = metadata_row_complete(row)
    return row


def metadata_row_complete(row: dict[str, Any]) -> bool:
    artifacts = row.get("artifacts") if isinstance(row.get("artifacts"), dict) else {}
    symbols = row.get("gpu_symbols") if isinstance(row.get("gpu_symbols"), dict) else {}
    layout = row.get("layout") if isinstance(row.get("layout"), dict) else {}
    required_artifacts = ["gpu_library", "gpu_library_source", "systemverilog", "verilator_mdir"]
    if row.get("entrypoint_kind") != "fallback-baseline":
        required_artifacts.append("direct_callsite_binary")
    return (
        isinstance(row.get("source_variant"), str)
        and isinstance(row.get("candidate"), str)
        and isinstance(row.get("shape"), str)
        and isinstance(row.get("entrypoint_kind"), str)
        and isinstance(row.get("runtime_boundary_kind"), str)
        and all(isinstance(artifacts.get(key), dict) and artifacts[key].get("path") for key in required_artifacts)
        and isinstance(symbols.get("run_gpu_outputs"), str)
        and isinstance(symbols.get("run_hybrid_json"), str)
        and isinstance(layout.get("input"), dict)
        and isinstance(layout.get("output"), dict)
    )


def _derived_port_counts(source_variant: object) -> tuple[int, int] | None:
    if not isinstance(source_variant, str) or source_variant not in PORT_NAMING:
        return None
    try:
        input_ports, output_ports = PORT_NAMING[source_variant]()
    except Exception:
        return None
    return len(input_ports), len(output_ports)


def _valid_layout_section(layout: dict[str, Any], name: str, expected_count: int | None) -> bool:
    section = layout.get(name)
    if not (
        isinstance(section, dict)
        and section.get("element_type") in BYTES_BY_TYPE
        and isinstance(section.get("element_count"), int)
        and section.get("element_count") > 0
    ):
        return False
    return expected_count is None or section.get("element_count") == expected_count


def _valid_symbol(value: object, suffix: str) -> bool:
    return isinstance(value, str) and value.endswith(suffix)


def src_hybrid_verilator_bridge_gate(
    selected: dict[str, Any],
    metadata_row: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Derive the source-variant bridge gate from the row's own metadata.

    Expected values are spec-driven: they come from the metadata row itself
    (checked for internal consistency and agreement with the dispatch-matrix
    `selected` boundary), not from one hardcoded candidate/source-variant
    constant. This accepts any promoted row (`entrypoint_kind` in
    `direct-binary`/`src-hybrid-verilator` with a matching
    `runtime_boundary_kind` and `policy: promote_to_hls_gpu`), and rejects
    fallback-baseline/unknown rows before dlopen.
    """
    if metadata_row is None:
        return None, "src_hybrid_verilator_metadata_row_missing"

    candidate = metadata_row.get("candidate")
    source_variant = metadata_row.get("source_variant")
    shape = metadata_row.get("shape")
    entrypoint_kind = metadata_row.get("entrypoint_kind")
    runtime_boundary_kind = metadata_row.get("runtime_boundary_kind")
    symbols = metadata_row.get("gpu_symbols") if isinstance(metadata_row.get("gpu_symbols"), dict) else {}
    layout = metadata_row.get("layout") if isinstance(metadata_row.get("layout"), dict) else {}
    derived_counts = _derived_port_counts(source_variant)
    expected_input_count, expected_output_count = derived_counts if derived_counts is not None else (None, None)

    checks = {
        "candidate": isinstance(candidate, str) and candidate == selected.get("candidate"),
        "source_variant": isinstance(source_variant, str) and source_variant == selected.get("source_variant"),
        "shape": isinstance(shape, str) and shape == selected.get("shape"),
        "entrypoint_kind": entrypoint_kind in PROMOTED_RUNTIME_BOUNDARY_BY_ENTRYPOINT,
        "runtime_boundary_kind": runtime_boundary_kind == PROMOTED_RUNTIME_BOUNDARY_BY_ENTRYPOINT.get(entrypoint_kind),
        "policy": metadata_row.get("policy") == "promote_to_hls_gpu",
        "input_layout": _valid_layout_section(layout, "input", expected_input_count),
        "output_layout": _valid_layout_section(layout, "output", expected_output_count),
        "run_gpu_outputs_symbol": _valid_symbol(symbols.get("run_gpu_outputs"), "_run_gpu_outputs"),
        "run_hybrid_json_symbol": _valid_symbol(symbols.get("run_hybrid_json"), "_run_hybrid_json"),
    }

    gate: dict[str, Any] = {
        "candidate": candidate,
        "source_variant": source_variant,
        "shape": shape,
        "entrypoint_kind": entrypoint_kind,
        "runtime_boundary_kind": runtime_boundary_kind,
        "input_element_type": (layout.get("input") or {}).get("element_type"),
        "input_element_count": (layout.get("input") or {}).get("element_count"),
        "output_element_type": (layout.get("output") or {}).get("element_type"),
        "output_element_count": (layout.get("output") or {}).get("element_count"),
        "run_gpu_outputs_symbol": symbols.get("run_gpu_outputs"),
        "run_hybrid_json_symbol": symbols.get("run_hybrid_json"),
        "checks": checks,
        "metadata_complete": metadata_row.get("metadata_complete") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed or not gate["metadata_complete"]:
        gate["failed_checks"] = failed
        return gate, "src_hybrid_verilator_metadata_gate_rejected"

    # The named checks above catch every field FC-074 promotion depends on;
    # this is a final fail-closed safety net for anything they did not,
    # such as a port-name/element-count mismatch inside the row.
    try:
        bridge_spec_from_metadata_row(metadata_row, selected=selected)
    except BridgeSpecError:
        gate["failed_checks"] = ["bridge_spec"]
        return gate, "src_hybrid_verilator_metadata_gate_rejected"

    gate["source"] = "source_variant_metadata"
    return gate, None


def build_source_variant_metadata_report(
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    *,
    source_variants: list[str] | None = None,
) -> dict[str, Any]:
    requested = source_variants or DEFAULT_SOURCE_VARIANTS
    rows = [source_variant_metadata_row(matrix, hls_summary, variant) for variant in requested]
    complete = [row for row in rows if row.get("metadata_complete") is True]
    return {
        "schema_version": 1,
        "surface": "scientific_circt_source_variant_metadata",
        "status": "source_variant_metadata_ready" if len(complete) == len(rows) else "source_variant_metadata_incomplete",
        "source_matrix_surface": matrix.get("surface"),
        "source_hls_summary_surface": hls_summary.get("surface"),
        "requested_source_variants": requested,
        "row_count": len(rows),
        "metadata_complete_count": len(complete),
        "rows": rows,
        "non_claims": [
            "not_full_microgpt_execution",
            "not_training_or_autograd",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
            "not_automatic_hls_rewrite",
            "not_production_runtime_dispatcher",
        ],
    }


def metadata_rows_by_variant(metadata_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = metadata_report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("source variant metadata report missing rows array")
    by_variant: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("source_variant"), str):
            by_variant[str(row["source_variant"])] = row
    return by_variant


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=Path("reports/scientific_circt_hybrid_dispatch_matrix.json"))
    parser.add_argument(
        "--hls-variant-report",
        type=Path,
        default=Path("reports/scientific_circt_hls_mlp_block_variants.json"),
    )
    parser.add_argument("--extra-hls-variant-report", type=Path, action="append", default=[])
    parser.add_argument("--source-variant", action="append", default=[])
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        summary = combined_hls_summary(
            load_json(args.hls_variant_report),
            [load_json(path) for path in args.extra_hls_variant_report],
        )
        report = build_source_variant_metadata_report(
            load_json(args.matrix),
            summary,
            source_variants=args.source_variant or None,
        )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "source_variant_metadata_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
