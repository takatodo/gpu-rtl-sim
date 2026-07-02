"""Review the Vortex lowered-TB runtime sequence invocation smoke boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


LOWERED_TB_HEADER = Path("src/hybrid/vortex_lowered_tb_runtime_sequence.h")
RUNTIME_INVOCATION_PLAN_REPORT = Path("reports/rtlmeter_vortex_runtime_invocation_plan.json")


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _contains_all(text: str, patterns: list[str]) -> dict[str, bool]:
    return {pattern: pattern in text for pattern in patterns}


def build_smoke(repo_root: Path) -> dict[str, Any]:
    header_path = repo_root / LOWERED_TB_HEADER
    invocation_plan_path = repo_root / RUNTIME_INVOCATION_PLAN_REPORT
    header_text = header_path.read_text(encoding="utf-8") if header_path.is_file() else ""
    invocation_plan = _load_json_if_exists(invocation_plan_path)
    header_features = _contains_all(
        header_text,
        [
            "VortexLoweredTbRuntimeSummary",
            "vortex_lowered_tb_invoke_runtime_sequence",
            "vortex_run_runtime_sequence",
            "runtime_sequence_called",
            "runtime_sequence_passed",
            "authority_report_ready",
            "authority_passed",
            "authority_source",
        ],
    )
    invocation_plan_ready = (
        isinstance(invocation_plan, dict)
        and invocation_plan.get("status") == "runtime_sequence_invocation_plan_ready_not_invoked"
        and invocation_plan.get("plan_ready") is True
    )
    smoke_ready = header_path.is_file() and all(header_features.values()) and invocation_plan_ready
    missing = []
    if not header_path.is_file() or not all(header_features.values()):
        missing.append("lowered_tb_runtime_sequence_header_features")
    if not invocation_plan_ready:
        missing.append("runtime_invocation_plan_ready")

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_lowered_tb_invocation_smoke",
        "status": "lowered_tb_invocation_smoke_ready_not_integrated" if smoke_ready else "blocked_missing_lowered_tb_invocation_smoke",
        "case": "Vortex:mini:hello",
        "lowered_tb_header": _display_path(header_path, repo_root=repo_root),
        "runtime_invocation_plan_report": _display_path(invocation_plan_path, repo_root=repo_root),
        "runtime_launchable": False,
        "header_features": header_features,
        "runtime_invocation_plan_ready": invocation_plan_ready,
        "smoke_ready": smoke_ready,
        "missing_prerequisites": missing,
        "still_missing_for_execution": [
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "runtime_sequence_reports_memory_post_or_stdout_TEST_PASSED_authority",
            "cpu_vs_hybrid_timing_report.vortex",
        ],
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_generated_lowered_tb_integration",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "lowered_tb_invocation_smoke_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_smoke(Path(args.repo_root))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
