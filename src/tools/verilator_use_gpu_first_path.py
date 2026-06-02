#!/usr/bin/env python3
"""First scoped Verilator-facing --use-gpu adapter."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

try:
    from hybrid_template_runner import load_template_plan, run_plan, validate_source_closure_for_execution
except ImportError:  # pragma: no cover
    from .hybrid_template_runner import load_template_plan, run_plan, validate_source_closure_for_execution


REPO_ROOT = Path(__file__).resolve().parents[2]
SURFACE = "verilator_use_gpu_first_path"
TEMPLATE = Path("config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json")
TARGET = "PULP_ITA.filelist_known_template_pulp_ita_mha"
TOP = "pulp_ita_mha_gpu_cov_tb"
ACCEL = "sidecar-gpu"
STATES = "64"
STEPS = "1"
SHAPE = "64x1"
POLICY = "coverage_output_equivalence"

READY, DRY_READY, EXECUTED, REJECTED, LAUNCHER_FAILED, COMPARE_FAILED = "verilator_use_gpu_first_path_ready", "verilator_use_gpu_first_path_dry_run_ready", "verilator_use_gpu_first_path_executed", "verilator_use_gpu_first_path_rejected", "verilator_use_gpu_first_path_launcher_failed", "verilator_use_gpu_first_path_compare_failed"
DRY_RUN_FLAG = "--first-use-gpu-dry-run"
NON_CLAIMS = ["only the reviewed PULP ITA MHA 64x1 filelist/template path is supported", "not arbitrary RTL or arbitrary filelist support", "not automatic dependency inference", "not automatic GPU allocation or timing evidence", "not raw full-state equality", "not a JSON runtime ABI"]


def _norm(raw: object, root: Path) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return None
    if ".." in path.parts:
        return None
    return path.as_posix().removeprefix("./")


def _values(argv: Sequence[str], option: str) -> list[str]:
    values: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == option and index + 1 < len(argv):
            values.append(argv[index + 1])
            index += 2
            continue
        if arg.startswith(f"{option}="):
            values.append(arg.split("=", 1)[1])
        elif option == "-f" and arg.startswith("-f") and arg != "-f":
            values.append(arg[2:])
        index += 1
    return values


def _has(argv: Sequence[str], option: str) -> bool:
    return option in argv or any(arg.startswith(f"{option}=") for arg in argv)


def _template_missing(root: Path) -> list[str]:
    path = root / TEMPLATE
    if not path.is_file():
        return ["sidecar_context.template_file"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["sidecar_context.template_json"]
    if not isinstance(payload, Mapping):
        return ["sidecar_context.template_payload"]

    missing: list[str] = []
    if payload.get("target") != TARGET:
        missing.append("sidecar_context.target")
    if payload.get("top_module") != TOP:
        missing.append("sidecar_context.top_module")
    if not payload.get("source_files"):
        missing.append("sidecar_context.source_files")
    closure = payload.get("source_closure")
    if not isinstance(closure, Mapping):
        missing.append("sidecar_context.source_closure")
    else:
        if closure.get("status") != "complete":
            missing.append("sidecar_context.source_closure.status")
        if closure.get("missing_required_sources") not in ([], None):
            missing.append("sidecar_context.source_closure.missing_required_sources")
    return missing


def launcher_command_argv() -> list[str]:
    return ["python3", "src/tools/run_hybrid_template.py", TEMPLATE.as_posix(), "--shape", SHAPE]


def _report(argv: Sequence[str], status: str, **extra: object) -> dict[str, object]:
    report: dict[str, object] = {
        "schema_version": 1,
        "surface": SURFACE,
        "status": status,
        "argv": list(argv),
        "target": TARGET,
        "top_module": TOP,
        "shape": SHAPE,
        "coverage_policy": POLICY,
        "cpu_as_gpu_fallback": False,
        "sidecar_execution_invoked": False,
        "sidecar_launcher_command_argv": launcher_command_argv(),
        "non_claims": NON_CLAIMS,
    }
    report.update(extra)
    return report


def resolve_verilator_use_gpu_first_path(
    argv: Sequence[str],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, object]:
    root = Path(repo_root).resolve() if repo_root is not None else REPO_ROOT
    args = [str(arg) for arg in argv]
    missing: list[str] = []

    if not _has(args, "--use-gpu"):
        missing.append("--use-gpu")
    if _has(args, "--sim-accel-shape"):
        missing.append("unsupported.--sim-accel-shape")
    top_values = _values(args, "--top-module")
    if top_values[-1:] != [TOP]:
        missing.append("top_module_match" if top_values else "--top-module")
    if _values(args, "--sim-accel")[-1:] != [ACCEL]:
        missing.append("--sim-accel sidecar-gpu")
    if _values(args, "--sim-accel-states")[-1:] != [STATES]:
        missing.append("--sim-accel-states 64")
    if _values(args, "--sim-accel-steps")[-1:] != [STEPS]:
        missing.append("--sim-accel-steps 1")

    missing.extend(_template_missing(root))
    filelists = [path for raw in _values(args, "-f") if (path := _norm(raw, root)) is not None]
    if filelists != [TEMPLATE.as_posix()]:
        missing.append("reviewed_filelist_authority" if filelists else "reviewed_filelist_or_source_closure_authority")
    if missing:
        return _report(
            args,
            REJECTED,
            fail_closed=True,
            execution_authority=False,
            accepted_source_authority=None,
            missing_required_inputs=missing,
            diagnostic="unsupported or incomplete --use-gpu request; failing closed before sidecar launch",
        )
    return _report(
        args,
        READY,
        fail_closed=False,
        execution_authority=True,
        accepted_source_authority="reviewed_materialized_filelist_template",
        template=TEMPLATE.as_posix(),
        diagnostic="first reviewed --use-gpu path resolved to the existing sidecar template runner",
    )


def _coverage_ok(report: Mapping[str, object]) -> bool:
    selected = report.get("selected_acceptance_policy")
    policy = report.get("coverage_output_policy")
    return (
        isinstance(selected, Mapping)
        and isinstance(policy, Mapping)
        and selected.get("name") == POLICY
        and selected.get("passed") is True
        and policy.get("mismatch_count") == 0
    )


def _default_launcher(_resolution: Mapping[str, object], _root_path: Path) -> dict[str, object]:
    plan = load_template_plan(TEMPLATE, shape=SHAPE)
    validate_source_closure_for_execution(plan)
    run_plan(plan, dry_run=False, verbose=False)
    compare = json.loads(Path(plan.compare_report).read_text(encoding="utf-8"))
    return {"returncode": 0, "compare_report_path": plan.compare_report.as_posix(), "compare_report": compare}


def execute_verilator_use_gpu_first_path(
    argv: Sequence[str],
    *,
    repo_root: str | Path | None = None,
    launcher=None,
    dry_run: bool = False,
) -> dict[str, object]:
    root = Path(repo_root).resolve() if repo_root is not None else REPO_ROOT
    resolution = resolve_verilator_use_gpu_first_path(argv, repo_root=root)
    if resolution["status"] != READY:
        return resolution
    if dry_run:
        return {**resolution, "status": DRY_READY, "execution_authority": False}

    try:
        launched = dict((launcher or _default_launcher)(resolution, root))
    except Exception as exc:  # noqa: BLE001 - adapter boundary must fail closed.
        return {
            **resolution,
            "status": LAUNCHER_FAILED,
            "fail_closed": True,
            "execution_authority": False,
            "sidecar_execution_invoked": True,
            "diagnostic": f"sidecar launcher failed: {exc}",
        }

    report = {**resolution, "sidecar_execution_invoked": True, "launcher_report": launched}
    report["sidecar_launcher_returncode"] = launched.get("returncode")
    if launched.get("returncode") != 0:
        report.update(
            status=LAUNCHER_FAILED,
            fail_closed=True,
            execution_authority=False,
            diagnostic="sidecar launcher returned nonzero; no CPU-only fallback is accepted as GPU evidence",
        )
    elif not isinstance(launched.get("compare_report"), Mapping) or not _coverage_ok(launched["compare_report"]):
        report.update(
            status=COMPARE_FAILED,
            fail_closed=True,
            execution_authority=False,
            diagnostic="coverage_output_equivalence was not proven with mismatch_count 0",
        )
    else:
        report.update(
            status=EXECUTED,
            fail_closed=False,
            execution_authority=True,
            diagnostic="sidecar template runner completed and coverage_output_equivalence passed",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry_run = DRY_RUN_FLAG in args
    args = [arg for arg in args if arg != DRY_RUN_FLAG]
    report = execute_verilator_use_gpu_first_path(args, dry_run=dry_run)
    print(json.dumps(report, indent=2), file=sys.stdout if report["status"] in {DRY_READY, EXECUTED} else sys.stderr)
    return 0 if report["status"] in {DRY_READY, EXECUTED} else 2


if __name__ == "__main__":
    raise SystemExit(main())
