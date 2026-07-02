#!/usr/bin/env python3
"""Strip Vortex Vsim main probe/marker blocks without claiming runtime authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MAIN_CPP = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/Vsim__main.cpp"
)
RUNTIME_MARKER_BEGIN = "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_BEGIN */"
RUNTIME_MARKER_END = "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_END */"
INVOCATION_PROBE_BEGIN = "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_BEGIN */"
INVOCATION_PROBE_END = "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_END */"
INVOCATION_PROBE_CALL_BEGIN = "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_CALL_BEGIN */"
INVOCATION_PROBE_CALL_END = "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_CALL_END */"
MATERIALIZED_ARGS_PROBE_BEGIN = "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */"
STATUS_PATCHED = "rtlmeter_vsim_main_vortex_probe_marker_strip_applied"
STATUS_ALREADY_STRIPPED = "rtlmeter_vsim_main_vortex_probe_marker_strip_already_stripped"
STATUS_MISSING = "rtlmeter_vsim_main_vortex_probe_marker_strip_missing_source"
STATUS_UNSUPPORTED = "rtlmeter_vsim_main_vortex_probe_marker_strip_unsupported_source"


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _strip_block(text: str, begin: str, end: str) -> tuple[str, int]:
    count = 0
    while begin in text or end in text:
        start = text.find(begin)
        stop = text.find(end)
        if start < 0 or stop < 0 or stop < start:
            raise ValueError(f"unbalanced block markers: {begin} {end}")
        stop += len(end)
        if stop < len(text) and text[stop : stop + 1] == "\n":
            stop += 1
        text = text[:start] + text[stop:]
        count += 1
    return text, count


def _report(
    *,
    status: str,
    main_cpp: Path,
    repo_root: Path | None,
    stripped: bool,
    removed_blocks: dict[str, int] | None = None,
    missing_patch_context: list[str] | None = None,
) -> dict[str, object]:
    removed = removed_blocks or {}
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_probe_marker_strip",
        "status": status,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "probe_marker_stripped": stripped,
        "runtime_sequence_marker_removed": removed.get("runtime_sequence_marker", 0),
        "runtime_invocation_probe_removed": removed.get("runtime_invocation_probe", 0),
        "runtime_invocation_probe_call_removed": removed.get("runtime_invocation_probe_call", 0),
        "materialized_runtime_args_probe_preserved": False,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_patch_context": missing_patch_context or [],
        "non_claims": [
            "probe_marker_strip_is_not_runtime_authority",
            "materialized_fake_driver_call_may_still_remain",
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def strip_vortex_probe_markers(*, main_cpp: Path, repo_root: Path | None = None) -> dict[str, object]:
    if main_cpp.name != "Vsim__main.cpp" or main_cpp.parent.name != "obj_dir":
        return _report(
            status=STATUS_UNSUPPORTED,
            main_cpp=main_cpp,
            repo_root=repo_root,
            stripped=False,
            missing_patch_context=["rtlmeter_vsim_main_path"],
        )
    if not main_cpp.is_file():
        return _report(
            status=STATUS_MISSING,
            main_cpp=main_cpp,
            repo_root=repo_root,
            stripped=False,
            missing_patch_context=["main_cpp"],
        )

    text = main_cpp.read_text(encoding="utf-8")
    if MATERIALIZED_ARGS_PROBE_BEGIN not in text:
        return _report(
            status=STATUS_UNSUPPORTED,
            main_cpp=main_cpp,
            repo_root=repo_root,
            stripped=False,
            missing_patch_context=["materialized_runtime_args_probe_boundary"],
        )

    has_any = any(
        marker in text
        for marker in (
            RUNTIME_MARKER_BEGIN,
            RUNTIME_MARKER_END,
            INVOCATION_PROBE_BEGIN,
            INVOCATION_PROBE_END,
            INVOCATION_PROBE_CALL_BEGIN,
            INVOCATION_PROBE_CALL_END,
        )
    )
    if not has_any:
        report = _report(
            status=STATUS_ALREADY_STRIPPED,
            main_cpp=main_cpp,
            repo_root=repo_root,
            stripped=True,
        )
        report["materialized_runtime_args_probe_preserved"] = MATERIALIZED_ARGS_PROBE_BEGIN in text
        return report

    try:
        patched, marker_count = _strip_block(text, RUNTIME_MARKER_BEGIN, RUNTIME_MARKER_END)
        patched, probe_count = _strip_block(patched, INVOCATION_PROBE_BEGIN, INVOCATION_PROBE_END)
        patched, probe_call_count = _strip_block(patched, INVOCATION_PROBE_CALL_BEGIN, INVOCATION_PROBE_CALL_END)
    except ValueError as exc:
        return _report(
            status=STATUS_UNSUPPORTED,
            main_cpp=main_cpp,
            repo_root=repo_root,
            stripped=False,
            missing_patch_context=[str(exc)],
        )

    if MATERIALIZED_ARGS_PROBE_BEGIN not in patched:
        return _report(
            status=STATUS_UNSUPPORTED,
            main_cpp=main_cpp,
            repo_root=repo_root,
            stripped=False,
            missing_patch_context=["materialized_runtime_args_probe_not_preserved"],
        )

    main_cpp.write_text(patched, encoding="utf-8")
    report = _report(
        status=STATUS_PATCHED,
        main_cpp=main_cpp,
        repo_root=repo_root,
        stripped=True,
        removed_blocks={
            "runtime_sequence_marker": marker_count,
            "runtime_invocation_probe": probe_count,
            "runtime_invocation_probe_call": probe_call_count,
        },
    )
    report["materialized_runtime_args_probe_preserved"] = True
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--main-cpp", default=DEFAULT_MAIN_CPP.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vsim_main_vortex_probe_marker_strip.json")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    main_cpp = Path(args.main_cpp)
    if not main_cpp.is_absolute():
        main_cpp = repo_root / main_cpp
    report = strip_vortex_probe_markers(main_cpp=main_cpp, repo_root=repo_root)
    if args.write_report:
        report_out = Path(args.report_out)
        if not report_out.is_absolute():
            report_out = repo_root / report_out
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {STATUS_PATCHED, STATUS_ALREADY_STRIPPED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
