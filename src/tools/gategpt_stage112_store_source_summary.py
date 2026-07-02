#!/usr/bin/env python3
"""Summarize gateGPT Stage112 store-source evidence.

This tool joins Stage112 runtime watchpoint events with the LLVM metadata map
that names candidate stores. It is intentionally evidence-only: static metadata
rows are not treated as runtime authority unless a runtime event identifies the
same source id.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any


STAGE112_ROW_RE = re.compile(
    r'!\d+ = !\{!"stage112_nested_body_store_source", i64 (?P<source_id>\d+), '
    r"i64 (?P<store_width>\d+), ptr @(?P<function>[^,]+), "
    r'!"(?P<basic_block>[^"]*)", !"(?P<pointer_operand>[^"]*)", '
    r'!"(?P<value_operand>[^"]*)"\}'
)

STAGE112_EVENT_KEYS = {
    "ordering_aware_token_loop_high_eval_callee0_nested_call_body_pair_offset_store_watchpoint_events",
    "phase1_post_sync_high_eval_callee0_nested_call_body_store_watchpoint_event",
    "high_eval_callee0_nested_call_body_store_watchpoint_latest_event",
}


def decode_stage112_control_word(control_word: int) -> dict[str, int]:
    return {
        "source_id": control_word & ((1 << 32) - 1),
        "boundary_kind_id": (control_word >> 32) & 0xFF,
        "split_result_id": (control_word >> 40) & 0xFF,
        "event_kind_id": (control_word >> 56) & 0xFF,
    }


def _newline_offsets(text: str) -> list[int]:
    return [match.start() for match in re.finditer("\n", text)]


def _line_number_from_offsets(newlines: list[int], index: int) -> int:
    return bisect.bisect_left(newlines, index) + 1


def _first_operand_line(
    text: str, newlines: list[int], pointer_operand: str
) -> int | None:
    if not pointer_operand:
        return None
    index = text.find("%" + pointer_operand)
    if index < 0:
        return None
    return _line_number_from_offsets(newlines, index)


def parse_stage112_metadata(ir_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    newlines = _newline_offsets(ir_text)
    for match in STAGE112_ROW_RE.finditer(ir_text):
        pointer_operand = match.group("pointer_operand")
        value_operand = match.group("value_operand")
        row = {
            "source_id": int(match.group("source_id")),
            "store_width": int(match.group("store_width")),
            "function": match.group("function"),
            "basic_block": match.group("basic_block"),
            "pointer_operand": pointer_operand,
            "value_operand": value_operand,
            "metadata_line": _line_number_from_offsets(newlines, match.start()),
            "expected_liveout_candidate": "expected_liveout" in pointer_operand,
            "clear_zero_candidate": value_operand == "0",
        }
        rows.append(row)
    return rows


def _with_operand_line(
    ir_text: str, newlines: list[int], row: dict[str, Any]
) -> dict[str, Any]:
    enriched = dict(row)
    if "first_operand_line" not in enriched:
        enriched["first_operand_line"] = _first_operand_line(
            ir_text, newlines, str(enriched.get("pointer_operand", ""))
        )
    return enriched


def _walk_json(value: Any) -> Iterable[tuple[str | None, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield None, item
            yield from _walk_json(item)


def _looks_like_stage112_event(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("progress_stage") == 112
        and (
            "source_id" in value
            or "control_word" in value
            or "watchpoint_complete" in value
        )
    )


def parse_stage112_runtime_events(report: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key, value in _walk_json(report):
        candidates: list[Any]
        if key in STAGE112_EVENT_KEYS and isinstance(value, list):
            candidates = value
        elif key in STAGE112_EVENT_KEYS and isinstance(value, dict):
            candidates = [value]
        elif _looks_like_stage112_event(value):
            candidates = [value]
        else:
            continue
        for item in candidates:
            if not isinstance(item, dict):
                continue
            event = dict(item)
            control_word = event.get("control_word")
            if isinstance(control_word, int):
                decoded = decode_stage112_control_word(control_word)
                event.setdefault("decoded_source_id", decoded["source_id"])
                event.setdefault("decoded_boundary_kind_id", decoded["boundary_kind_id"])
                event.setdefault("decoded_split_result_id", decoded["split_result_id"])
                event.setdefault("decoded_event_kind_id", decoded["event_kind_id"])
            identity = json.dumps(event, sort_keys=True, separators=(",", ":"))
            if identity in seen:
                continue
            seen.add(identity)
            events.append(event)
    return events


def summarize_stage112_store_sources(
    *,
    ir_text: str,
    report: dict[str, Any] | None = None,
    source_ids: Iterable[int] = (),
) -> dict[str, Any]:
    metadata_rows = parse_stage112_metadata(ir_text)
    newlines = _newline_offsets(ir_text)
    rows_by_id = {row["source_id"]: row for row in metadata_rows}
    requested_ids = list(dict.fromkeys(source_ids))
    static_candidates = [
        _with_operand_line(ir_text, newlines, rows_by_id[source_id])
        for source_id in requested_ids
        if source_id in rows_by_id
    ]
    if not static_candidates and requested_ids:
        static_candidates = [
            {"source_id": source_id, "metadata_found": False}
            for source_id in requested_ids
            if source_id not in rows_by_id
        ]

    events = parse_stage112_runtime_events(report or {})
    runtime_source_ids: list[int] = []
    runtime_clean_event_count = 0
    for event in events:
        source_id = event.get("source_id")
        if not isinstance(source_id, int) or source_id == 0:
            decoded_source_id = event.get("decoded_source_id")
            source_id = decoded_source_id if isinstance(decoded_source_id, int) else 0
        if source_id > 0:
            runtime_source_ids.append(source_id)
        elif event.get("clean_no_nested_body_store") or event.get("write_source_found") is False:
            runtime_clean_event_count += 1

    runtime_source_ids = list(dict.fromkeys(runtime_source_ids))
    runtime_mapped_sources = [
        _with_operand_line(ir_text, newlines, rows_by_id[source_id])
        for source_id in runtime_source_ids
        if source_id in rows_by_id
    ]
    runtime_unmapped_source_ids = [
        source_id for source_id in runtime_source_ids if source_id not in rows_by_id
    ]
    runtime_authority = bool(runtime_mapped_sources)
    if runtime_authority:
        status = "stage112_runtime_source_mapped"
    elif events:
        status = "stage112_runtime_clean_or_unmapped_static_candidates_only"
    elif static_candidates:
        status = "stage112_static_candidates_only"
    else:
        status = "stage112_no_runtime_or_static_source"

    return {
        "status": status,
        "runtime_authority": runtime_authority,
        "semantic_authority": False,
        "kernel_execution_observed": bool(events),
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "metadata_source_count": len(metadata_rows),
        "requested_source_ids": requested_ids,
        "static_candidate_count": len(static_candidates),
        "static_candidates": static_candidates,
        "runtime_event_count": len(events),
        "runtime_clean_event_count": runtime_clean_event_count,
        "runtime_source_ids": runtime_source_ids,
        "runtime_mapped_source_count": len(runtime_mapped_sources),
        "runtime_mapped_sources": runtime_mapped_sources,
        "runtime_unmapped_source_ids": runtime_unmapped_source_ids,
        "non_claims": [
            "static_stage112_metadata_is_not_runtime_authority",
            "clean_summary_events_do_not_identify_a_write_source",
            "no_speedup_or_usefulness_claim",
        ],
    }


def _parse_source_ids(values: list[str]) -> list[int]:
    out: list[int] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                out.append(int(part, 0))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, required=True, help="LLVM IR with Stage112 metadata")
    parser.add_argument("--report", type=Path, help="Optional JSON runtime report")
    parser.add_argument(
        "--source-id",
        action="append",
        default=[],
        help="Stage112 source id to include as a static candidate. May be repeated or comma-separated.",
    )
    parser.add_argument("--out", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8")) if args.report else None
    summary = summarize_stage112_store_sources(
        ir_text=args.ir.read_text(encoding="utf-8", errors="replace"),
        report=report,
        source_ids=_parse_source_ids(args.source_id),
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
