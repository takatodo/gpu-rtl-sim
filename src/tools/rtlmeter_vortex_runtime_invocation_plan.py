"""Review the fail-closed Vortex mini:hello runtime sequence invocation plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


TEMPLATE = Path("config/slice_launch_templates/vortex_mini_hello.json")
BRIDGE_REVIEW_REPORT = Path("reports/rtlmeter_vortex_dpi_memory_bridge_review.json")
RUNTIME_SEQUENCE_HEADER = Path("src/hybrid/vortex_runtime_sequence.h")


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _contains_all(text: str, patterns: list[str]) -> dict[str, bool]:
    return {pattern: pattern in text for pattern in patterns}


def build_invocation_plan(repo_root: Path) -> dict[str, Any]:
    template_path = repo_root / TEMPLATE
    bridge_path = repo_root / BRIDGE_REVIEW_REPORT
    runtime_header_path = repo_root / RUNTIME_SEQUENCE_HEADER
    template = _load_json(template_path)
    bridge = _load_json(bridge_path) if bridge_path.is_file() else {}
    runtime_header = runtime_header_path.read_text(encoding="utf-8") if runtime_header_path.is_file() else ""

    planned_overlay = template.get("planned_overlay") if isinstance(template.get("planned_overlay"), dict) else {}
    invocation_plan = (
        planned_overlay.get("runtime_sequence_invocation_plan")
        if isinstance(planned_overlay.get("runtime_sequence_invocation_plan"), dict)
        else {}
    )
    acceptance = template.get("acceptance") if isinstance(template.get("acceptance"), dict) else {}
    source_closure = template.get("source_closure") if isinstance(template.get("source_closure"), dict) else {}
    missing_required_sources = source_closure.get("missing_required_sources")
    if not isinstance(missing_required_sources, list):
        missing_required_sources = []

    header_features = _contains_all(
        runtime_header,
        [
            "vortex_run_runtime_sequence",
            "vortex_upload_runtime_buffers",
            "vortex_export_observables",
            "vortex_release_runtime_buffers",
            "VortexDcrApplyFn",
            "VortexKernelLaunchFn",
        ],
    )
    expected_order = [
        "vortex_upload_runtime_buffers",
        "apply_ordered_dcr_writes_while_reset_asserted",
        "vortex_kernel_launch_callback",
        "vortex_export_observables",
        "vortex_release_runtime_buffers",
    ]
    actual_order = invocation_plan.get("required_order")
    if not isinstance(actual_order, list):
        actual_order = []

    plan_ready = (
        template.get("runtime_launchable") is False
        and source_closure.get("status") == "incomplete"
        and invocation_plan.get("status") == "planned_not_invoked"
        and invocation_plan.get("entrypoint") == "vortex_run_runtime_sequence"
        and actual_order == expected_order
        and planned_overlay.get("runtime_sequence_header") == RUNTIME_SEQUENCE_HEADER.as_posix()
        and acceptance.get("next_gate_must_invoke_runtime_sequence_helper") is True
        and all(header_features.values())
        and bridge.get("runtime_sequence_helper_ready") is True
    )

    missing = []
    if invocation_plan.get("entrypoint") != "vortex_run_runtime_sequence":
        missing.append("template_runtime_sequence_entrypoint")
    if actual_order != expected_order:
        missing.append("template_runtime_sequence_required_order")
    if planned_overlay.get("runtime_sequence_header") != RUNTIME_SEQUENCE_HEADER.as_posix():
        missing.append("template_runtime_sequence_header")
    if acceptance.get("next_gate_must_invoke_runtime_sequence_helper") is not True:
        missing.append("template_acceptance_runtime_sequence_gate")
    if bridge.get("runtime_sequence_helper_ready") is not True:
        missing.append("bridge_runtime_sequence_helper_ready")
    if not all(header_features.values()):
        missing.append("runtime_sequence_header_features")
    if "lowered_tb_runtime_sequence_helper_invocation" not in missing_required_sources:
        missing.append("source_closure_runtime_sequence_invocation_marker")
    if "observable_authority_reporting" not in missing_required_sources:
        missing.append("source_closure_observable_authority_marker")

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_runtime_invocation_plan",
        "status": "runtime_sequence_invocation_plan_ready_not_invoked" if plan_ready and not missing else "blocked_missing_runtime_sequence_invocation_plan",
        "case": "Vortex:mini:hello",
        "template": _display_path(template_path, repo_root=repo_root),
        "bridge_review_report": _display_path(bridge_path, repo_root=repo_root),
        "runtime_sequence_header": _display_path(runtime_header_path, repo_root=repo_root),
        "runtime_launchable": False,
        "template_runtime_launchable": template.get("runtime_launchable"),
        "source_closure_status": source_closure.get("status"),
        "entrypoint": invocation_plan.get("entrypoint"),
        "required_order": actual_order,
        "header_features": header_features,
        "bridge_runtime_sequence_helper_ready": bridge.get("runtime_sequence_helper_ready"),
        "plan_ready": plan_ready and not missing,
        "missing_prerequisites": missing,
        "still_missing_for_execution": [
            "lowered_tb_invokes_vortex_run_runtime_sequence",
            "runtime_sequence_reports_memory_post_or_stdout_TEST_PASSED_authority",
            "cpu_vs_hybrid_timing_report.vortex",
        ],
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_runtime_invocation",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "template_plan_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_invocation_plan(Path(args.repo_root))
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
