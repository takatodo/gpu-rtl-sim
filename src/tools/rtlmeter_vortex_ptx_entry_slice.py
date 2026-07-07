#!/usr/bin/env python3
"""Create a small PTX entry slice for bounded module-load diagnosis."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_PTX = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/vl_batch_gpu.ptx"
)
DEFAULT_OUT = Path("artifacts/rtlmeter_vortex_ptx_entry_slice/vl_eval_batch_gpu.ptx")
ENTRY_RE = re.compile(r"^\s*\.visible\s+\.entry\s+([A-Za-z_.$][A-Za-z0-9_.$]*)\s*\(")
FUNC_RE = re.compile(
    r"^\s*(?:\.visible\s+)?\.func\s+(?:\([^)]*\)\s+)?"
    r"([A-Za-z_.$][A-Za-z0-9_.$]*)(?:\s*\(|\s*$)"
)
CALL_TARGET_RE = re.compile(
    r"\bcall(?:\.[A-Za-z0-9_]+)*\s*(?:\([^)]*\)\s*,\s*)?"
    r"([A-Za-z_.$][A-Za-z0-9_.$]*)\s*,",
    re.MULTILINE,
)


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _entry_name(line: str) -> str | None:
    match = ENTRY_RE.match(line)
    return match.group(1) if match else None


def _func_name(line: str) -> str | None:
    match = FUNC_RE.match(line)
    return match.group(1) if match else None


def _find_entry_block_end(lines: list[str], start: int) -> tuple[int, bool]:
    depth = 0
    saw_open = False
    for index in range(start, len(lines)):
        line = lines[index]
        depth += line.count("{")
        if "{" in line:
            saw_open = True
        depth -= line.count("}")
        if saw_open and depth <= 0:
            return index + 1, True
    return len(lines), False


def _find_func_declaration_end(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        line = lines[index]
        if "{" in line:
            return None
        if ";" in line:
            return index + 1
    return None


def _func_declaration_spans(lines: list[str]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        name = _func_name(line)
        if name is None:
            continue
        end = _find_func_declaration_end(lines, index)
        if end is None:
            continue
        spans.append(
            {
                "kind": "func_declaration",
                "name": name,
                "start_line": index + 1,
                "end_line_exclusive": end + 1,
                "line_count": end - index,
            }
        )
    return spans


def _definition_spans(lines: list[str]) -> list[dict[str, Any]]:
    starts: list[tuple[str, str, int]] = []
    for index, line in enumerate(lines):
        name = _entry_name(line)
        if name is not None:
            starts.append(("entry", name, index))
            continue
        name = _func_name(line)
        if name is not None:
            starts.append(("func", name, index))
    spans: list[dict[str, Any]] = []
    for kind, name, start in starts:
        if kind == "func" and _find_func_declaration_end(lines, start) is not None:
            continue
        end, has_body = _find_entry_block_end(lines, start)
        if kind == "func" and not has_body:
            continue
        spans.append(
            {
                "kind": kind,
                "name": name,
                "start_line": start + 1,
                "end_line_exclusive": end + 1,
                "line_count": end - start,
            }
        )
    return spans


def _entry_spans(lines: list[str]) -> list[dict[str, Any]]:
    return [span for span in _definition_spans(lines) if span["kind"] == "entry"]


def _block_text(lines: list[str], span: dict[str, Any]) -> str:
    start = int(span["start_line"]) - 1
    end = int(span["end_line_exclusive"]) - 1
    return "".join(lines[start:end])


def _stubbed_function_lines(lines: list[str], span: dict[str, Any]) -> list[str]:
    start = int(span["start_line"]) - 1
    end = int(span["end_line_exclusive"]) - 1
    header: list[str] = []
    for index in range(start, end):
        header.append(lines[index])
        if "{" in lines[index]:
            break
    if not header or "{" not in header[-1]:
        return lines[start:end]
    return header + ["\tret;\n", "}\n"]


def _call_targets(block: str) -> set[str]:
    return {match.group(1) for match in CALL_TARGET_RE.finditer(block)}


def _reachable_function_names(
    lines: list[str],
    definition_spans: list[dict[str, Any]],
    roots: set[str],
) -> set[str]:
    definitions = {str(span["name"]): span for span in definition_spans}
    reachable: set[str] = set(roots)
    queue = list(roots)
    while queue:
        name = queue.pop()
        span = definitions.get(name)
        if span is None:
            continue
        for target in _call_targets(_block_text(lines, span)):
            if target not in definitions or target in reachable:
                continue
            reachable.add(target)
            queue.append(target)
    return reachable


def build_slice(
    repo_root: Path,
    *,
    ptx_path: Path = DEFAULT_PTX,
    out_path: Path = DEFAULT_OUT,
    entry: str = "vl_eval_batch_gpu",
    keep_entries: list[str] | None = None,
    prune_unreferenced_funcs: bool = False,
    stub_funcs: list[str] | None = None,
    write_slice: bool = False,
    case: str = "Vortex:mini:hello",
    surface: str = "rtlmeter_vortex_ptx_entry_slice",
    next_required_boundary: str = "run_bounded_ptxas_probe_on_vortex_entry_slice",
) -> dict[str, Any]:
    root = repo_root.resolve()
    ptx = ptx_path if ptx_path.is_absolute() else root / ptx_path
    out = out_path if out_path.is_absolute() else root / out_path
    if not ptx.is_file():
        return {
            "schema_version": 1,
            "surface": surface,
            "case": case,
            "status": "ptx_missing",
            "source_ptx": _display_path(ptx, repo_root=root),
            "entry": entry,
            "keep_entries": keep_entries or [entry],
            "slice_written": False,
            "next_required_boundary": "build_vortex_ptx_before_entry_slice",
            "runtime_authority": False,
            "kernel_execution_observed": False,
            "timing_measured": False,
            "speedup_claimed": False,
        }
    lines = ptx.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    definition_spans = _definition_spans(lines)
    spans = [span for span in definition_spans if span["kind"] == "entry"]
    requested_entries = keep_entries or [entry]
    requested_entry_set = set(requested_entries)
    found_entries = {str(span["name"]) for span in spans}
    missing_entries = [name for name in requested_entries if name not in found_entries]
    if missing_entries:
        return {
            "schema_version": 1,
            "surface": surface,
            "case": case,
            "status": "entry_missing",
            "source_ptx": _display_path(ptx, repo_root=root),
            "entry": entry,
            "keep_entries": requested_entries,
            "missing_entries": missing_entries,
            "available_entries": [str(span["name"]) for span in spans],
            "slice_written": False,
            "next_required_boundary": "select_existing_vortex_ptx_entry_for_slice",
            "runtime_authority": False,
            "kernel_execution_observed": False,
            "timing_measured": False,
            "speedup_claimed": False,
        }
    reachable_names = (
        _reachable_function_names(lines, definition_spans, requested_entry_set)
        if prune_unreferenced_funcs
        else set()
    )
    func_declaration_spans = _func_declaration_spans(lines)
    removed_func_declaration_spans = [
        span
        for span in func_declaration_spans
        if prune_unreferenced_funcs and str(span["name"]) not in reachable_names
    ]
    removed_func_spans = [
        span
        for span in definition_spans
        if span["kind"] == "func" and prune_unreferenced_funcs and str(span["name"]) not in reachable_names
    ]
    stub_func_set = set(stub_funcs or [])
    stub_func_spans = [
        span
        for span in definition_spans
        if span["kind"] == "func"
        and str(span["name"]) in stub_func_set
        and str(span["name"]) in reachable_names
    ]
    stub_func_starts = {
        int(span["start_line"]) - 1: span for span in stub_func_spans
    }
    remove_spans = [
        span for span in spans if str(span["name"]) not in requested_entry_set
    ] + removed_func_spans + removed_func_declaration_spans
    remove_ranges = [
        (int(span["start_line"]) - 1, int(span["end_line_exclusive"]) - 1)
        for span in remove_spans
    ]
    remove_ranges.sort()
    sliced_lines: list[str] = []
    cursor = 0
    for start, end in remove_ranges:
        while cursor < start:
            span = stub_func_starts.get(cursor)
            if span is not None:
                span_end = int(span["end_line_exclusive"]) - 1
                sliced_lines.extend(_stubbed_function_lines(lines, span))
                cursor = span_end
            else:
                sliced_lines.append(lines[cursor])
                cursor += 1
        cursor = max(cursor, end)
    while cursor < len(lines):
        span = stub_func_starts.get(cursor)
        if span is not None:
            span_end = int(span["end_line_exclusive"]) - 1
            sliced_lines.extend(_stubbed_function_lines(lines, span))
            cursor = span_end
        else:
            sliced_lines.append(lines[cursor])
            cursor += 1
    slice_text = "".join(sliced_lines)
    slice_content_sha256 = hashlib.sha256(slice_text.encode("utf-8")).hexdigest()
    existing_slice_content_unchanged = False
    if out.is_file():
        existing_slice_content_unchanged = (
            out.read_text(encoding="utf-8", errors="replace") == slice_text
        )
    if write_slice:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(slice_text, encoding="utf-8")
    kept_spans = [span for span in spans if str(span["name"]) in requested_entry_set]
    return {
        "schema_version": 1,
        "surface": surface,
        "case": case,
        "status": "entry_slice_written" if write_slice else "entry_slice_planned",
        "source_ptx": _display_path(ptx, repo_root=root),
        "slice_ptx": _display_path(out, repo_root=root),
        "entry": entry,
        "keep_entries": requested_entries,
        "source_line_count": len(lines),
        "source_entry_count": len(spans),
        "source_func_count": sum(1 for span in definition_spans if span["kind"] == "func"),
        "source_entries": spans,
        "preserved_prefix_line_count": min(int(span["start_line"]) for span in spans) - 1,
        "kept_entry_count": len(kept_spans),
        "prune_unreferenced_funcs": prune_unreferenced_funcs,
        "reachable_definition_count": len(reachable_names) if prune_unreferenced_funcs else None,
        "removed_func_count": len(removed_func_spans),
        "removed_func_line_count": sum(int(span["line_count"]) for span in removed_func_spans),
        "stub_func_count": len(stub_func_spans),
        "stub_func_line_count": sum(int(span["line_count"]) for span in stub_func_spans),
        "stub_func_names": [str(span["name"]) for span in stub_func_spans],
        "removed_func_declaration_count": len(removed_func_declaration_spans),
        "removed_func_declaration_line_count": sum(
            int(span["line_count"]) for span in removed_func_declaration_spans
        ),
        "kept_entry_line_count": sum(int(span["line_count"]) for span in kept_spans),
        "target_entry_line_count": int(kept_spans[0]["line_count"]) if kept_spans else 0,
        "slice_line_count": len(sliced_lines),
        "slice_content_sha256": slice_content_sha256,
        "existing_slice_content_unchanged": existing_slice_content_unchanged,
        "removed_entry_count": max(0, len(spans) - len(kept_spans)),
        "removed_line_count": len(lines) - len(sliced_lines),
        "slice_written": write_slice,
        "slice_exists": out.is_file(),
        "next_required_boundary": next_required_boundary,
        "runtime_authority": False,
        "kernel_execution_observed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "entry_slice_is_not_kernel_execution",
            "entry_slice_is_not_cpu_vs_hybrid_timing",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ptx", default=DEFAULT_PTX.as_posix())
    parser.add_argument("--entry", default="vl_eval_batch_gpu")
    parser.add_argument(
        "--keep-entry",
        action="append",
        dest="keep_entries",
        help="PTX entry to keep; may be repeated. Defaults to --entry.",
    )
    parser.add_argument(
        "--prune-unreferenced-funcs",
        action="store_true",
        help="Drop .func blocks that are not reachable from the kept entries.",
    )
    parser.add_argument(
        "--stub-func",
        action="append",
        dest="stub_funcs",
        help=(
            "Replace a reachable .func body with a ret-only diagnostic stub. "
            "May be repeated; this is ptxas-surface evidence, not runtime authority."
        ),
    )
    parser.add_argument("--out", default=DEFAULT_OUT.as_posix())
    parser.add_argument("--case", default="Vortex:mini:hello")
    parser.add_argument("--surface", default="rtlmeter_vortex_ptx_entry_slice")
    parser.add_argument("--next-required-boundary", default="run_bounded_ptxas_probe_on_vortex_entry_slice")
    parser.add_argument("--write-slice", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_ptx_entry_slice.json")
    args = parser.parse_args(argv)
    report = build_slice(
        Path(args.repo_root),
        ptx_path=Path(args.ptx),
        out_path=Path(args.out),
        entry=args.entry,
        keep_entries=args.keep_entries,
        prune_unreferenced_funcs=args.prune_unreferenced_funcs,
        stub_funcs=args.stub_funcs,
        write_slice=args.write_slice,
        case=args.case,
        surface=args.surface,
        next_required_boundary=args.next_required_boundary,
    )
    if args.write_report:
        out = Path(args.report_out)
        if not out.is_absolute():
            out = Path(args.repo_root) / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"entry_slice_planned", "entry_slice_written"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
