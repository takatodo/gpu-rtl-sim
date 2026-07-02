#!/usr/bin/env python3
"""Thin CLI: emit a source-variant bridge gate header, or run it end-to-end.

This is the FC-074 metadata-row bridge source emitter. It reuses
`scientific_circt_bridge_spec.bridge_spec_from_metadata_row`/
`render_bridge_gate_header` for header emission, and
`scientific_circt_source_variant_runtime_handoff.build_runtime_handoff_report`
(entrypoint `src-hybrid-verilator`, reusing the shared metadata-driven bridge
at `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` against
that variant's own Verilator object directory) for the `--run` path. Rows
that are not promoted (`policy != promote_to_hls_gpu`, e.g. the
`block2_hls_friendly` fallback-baseline row) or unknown fail closed with a
non-zero exit and no header emitted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scientific_circt_bridge_spec import BridgeSpecError, bridge_spec_from_metadata_row, render_bridge_gate_header
from scientific_circt_source_variant_metadata import combined_hls_summary, metadata_rows_by_variant
from scientific_circt_source_variant_runtime_handoff import build_runtime_handoff_report

OUT_DIR = Path("artifacts/scientific_circt/source_variant_bridge_emit")
METADATA_REPORT = Path("reports/scientific_circt_source_variant_metadata.json")
MATRIX_REPORT = Path("reports/scientific_circt_hybrid_dispatch_matrix.json")
HLS_VARIANT_REPORT = Path("reports/scientific_circt_hls_mlp_block_variants.json")
EXTRA_HLS_VARIANT_REPORTS = [Path("reports/scientific_circt_hls_attention_head4.json")]

HEADER_NAME = "scientific_circt_source_variant_bridge_gate.h"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def promoted_rows(metadata_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: row
        for name, row in metadata_rows_by_variant(metadata_report).items()
        if row.get("policy") == "promote_to_hls_gpu"
    }


def emit_header_for_row(row: dict[str, Any], out_dir: Path) -> Path:
    """Render and write the bridge gate header for one metadata row.

    Raises BridgeSpecError (no header written) for a non-promoted or
    internally inconsistent row, e.g. the block2_hls_friendly fallback row.
    """
    spec = bridge_spec_from_metadata_row(row)
    header_dir = out_dir / row["source_variant"]
    header_dir.mkdir(parents=True, exist_ok=True)
    header = header_dir / HEADER_NAME
    header.write_text(render_bridge_gate_header(spec), encoding="utf-8")
    return header


def run_source_variant(
    row: dict[str, Any],
    *,
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
) -> dict[str, Any]:
    """Run one promoted source variant end-to-end through the shared bridge.

    Reuses build_runtime_handoff_report with entrypoint=src-hybrid-verilator
    against the variant's own Verilator object directory (not only
    inference2_hls_friendly's), with the row itself as the selected boundary
    so the metadata gate is checked against what was explicitly requested.
    """
    selected = {
        "candidate": row.get("candidate"),
        "source_variant": row.get("source_variant"),
        "shape": row.get("shape"),
    }
    return build_runtime_handoff_report(
        matrix,
        hls_summary,
        execute=True,
        entrypoint="src-hybrid-verilator",
        selected_boundary=selected,
        metadata_row=row,
    )


def _run_passed(report: dict[str, Any]) -> bool:
    return report.get("cpu_vs_gpu_output_equal") is True and report.get("cpu_vs_gpu_control_checksum_equal") is True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--source-variant", help="Emit/run one metadata row by source_variant name.")
    target.add_argument("--all-promoted", action="store_true", help="Emit headers for every promoted row.")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit-header", action="store_true", help="Render the bridge gate header only.")
    mode.add_argument("--run", action="store_true", help="Compile and run the shared bridge end-to-end.")

    parser.add_argument("--no-execute", action="store_true", help="Documents intent alongside --emit-header; header emission never compiles or runs anything.")
    parser.add_argument("--metadata-report", type=Path, default=METADATA_REPORT)
    parser.add_argument("--matrix", type=Path, default=MATRIX_REPORT)
    parser.add_argument("--hls-variant-report", type=Path, default=HLS_VARIANT_REPORT)
    parser.add_argument("--extra-hls-variant-report", type=Path, action="append", default=list(EXTRA_HLS_VARIANT_REPORTS))
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.run and args.no_execute:
        parser.error("--run cannot be combined with --no-execute")
    if args.all_promoted and args.run:
        parser.error("--all-promoted only supports --emit-header; use --source-variant with --run")

    try:
        metadata_report = _load(args.metadata_report)
    except Exception as exc:
        print(json.dumps({"status": "failed_metadata_report_load", "reason": str(exc)}))
        return 2

    if args.emit_header:
        if args.all_promoted:
            rows = promoted_rows(metadata_report)
            emitted: dict[str, str] = {}
            failed: dict[str, str] = {}
            for name, row in sorted(rows.items()):
                try:
                    header = emit_header_for_row(row, args.out_dir)
                except BridgeSpecError as exc:
                    failed[name] = str(exc)
                else:
                    emitted[name] = header.as_posix()
            result = {
                "status": "bridge_headers_emitted" if emitted and not failed else "bridge_header_emit_failed",
                "emitted": emitted,
                "failed": failed,
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if emitted and not failed else 1

        by_variant = metadata_rows_by_variant(metadata_report)
        row = by_variant.get(args.source_variant)
        if row is None:
            print(json.dumps({"status": "failed_unknown_source_variant", "source_variant": args.source_variant}))
            return 2
        try:
            header = emit_header_for_row(row, args.out_dir)
        except BridgeSpecError as exc:
            print(json.dumps({"status": "failed_metadata_gate", "source_variant": args.source_variant, "reason": str(exc)}))
            return 1
        print(json.dumps({"status": "bridge_header_emitted", "source_variant": args.source_variant, "header": header.as_posix()}))
        return 0

    # args.run
    by_variant = metadata_rows_by_variant(metadata_report)
    row = by_variant.get(args.source_variant)
    if row is None:
        print(json.dumps({"status": "failed_unknown_source_variant", "source_variant": args.source_variant}))
        return 2
    try:
        matrix = _load(args.matrix)
        hls_summary = combined_hls_summary(
            _load(args.hls_variant_report),
            [_load(path) for path in args.extra_hls_variant_report],
        )
    except Exception as exc:
        print(json.dumps({"status": "failed_report_load", "reason": str(exc)}))
        return 2

    report = run_source_variant(row, matrix=matrix, hls_summary=hls_summary)
    if args.write_report:
        report_out = args.report_out or (args.out_dir / row["source_variant"] / "runtime_handoff.json")
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if _run_passed(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
