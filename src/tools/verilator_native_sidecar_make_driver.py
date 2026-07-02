"""Repo-side driver for the native ``verilator --sim-accel sidecar-gpu`` make hook."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from verilator_native_known_closure import (
    STATUS_RECOGNIZED,
    recognize_verilator_native_known_closure,
)

SURFACE = "verilator_native_sidecar_make_driver"
STATUS_BUILD_PLAN_READY = "verilator_native_sidecar_build_plan_ready"
STATUS_BLOCKED_UNRECOGNIZED = "verilator_native_sidecar_blocked_unrecognized_closure"
STATUS_BLOCKED_MISSING_MDIR = "verilator_native_sidecar_blocked_missing_verilated_mdir"
STATUS_BLOCKED_TEMPLATE = "verilator_native_sidecar_blocked_launch_template"
NON_CLAIMS = (
    "recognition and plan construction are compile-side metadata, not GPU execution evidence",
    "the driver never falls back to CPU when the GPU pipeline is unavailable",
    "no speedup, timing, or arbitrary-RTL claim is made",
    "only a tracked known closure can reach sidecar make-time prep or the reviewed template GPU flow",
    "direct shim smoke is not GPU artifact load, kernel launch, or coverage-output equivalence",
)


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>"


def _load_json(path: Path) -> Mapping[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, Mapping) else None


def _classes_mk_present(mdir: Path) -> bool:
    return mdir.is_dir() and bool(list(mdir.glob("*_classes.mk")))


def _report(
    *,
    status: str,
    recognition: Mapping[str, object],
    mdir_display: str | None,
    mdir_verilated: bool,
    missing_context: list[str],
    diagnostic: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": status,
        "build_plan_ready": status == STATUS_BUILD_PLAN_READY,
        "recognition": dict(recognition),
        "target": recognition.get("target"),
        "top_module": recognition.get("top_module"),
        "launch_template": recognition.get("launch_template"),
        "mdir": mdir_display,
        "mdir_verilated": mdir_verilated,
        "fail_closed": True,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_build_context": missing_context,
        "diagnostic": diagnostic,
        "non_claims": list(NON_CLAIMS),
    }


def plan_native_sidecar_build(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
) -> dict[str, object]:
    """Recognize the closure and resolve the make mdir without running anything."""
    root = (repo_root or Path.cwd()).resolve()
    recognition = recognize_verilator_native_known_closure(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
    )
    if recognition["status"] != STATUS_RECOGNIZED:
        return _report(
            status=STATUS_BLOCKED_UNRECOGNIZED,
            recognition=recognition,
            mdir_display=None,
            mdir_verilated=False,
            missing_context=["recognized_known_closure"],
            diagnostic="native sidecar build is blocked: the filelist/top pair is not a tracked known closure",
        )

    if mdir_override is not None:
        mdir = Path(mdir_override)
        if not mdir.is_absolute():
            mdir = Path.cwd() / mdir
        mdir_value = mdir.as_posix()
    else:
        template = _load_json(root / str(recognition["launch_template"]))
        build = template.get("build") if isinstance(template, Mapping) else None
        mdir_value = build.get("mdir") if isinstance(build, Mapping) else None
        if not isinstance(mdir_value, str) or not mdir_value:
            return _report(
                status=STATUS_BLOCKED_TEMPLATE,
                recognition=recognition,
                mdir_display=None,
                mdir_verilated=False,
                missing_context=["launch_template.build.mdir"],
                diagnostic="native sidecar build is blocked: the recognized closure template has no build mdir",
            )

    mdir = Path(mdir_value)
    if not mdir.is_absolute():
        mdir = root / mdir
    mdir_display = _display_path(mdir, root)
    mdir_verilated = _classes_mk_present(mdir)
    if not mdir_verilated:
        return _report(
            status=STATUS_BLOCKED_MISSING_MDIR,
            recognition=recognition,
            mdir_display=mdir_display,
            mdir_verilated=False,
            missing_context=["verilated_mdir_classes_mk"],
            diagnostic="native sidecar build is blocked: the verilated mdir has no *_classes.mk yet",
        )

    return _report(
        status=STATUS_BUILD_PLAN_READY,
        recognition=recognition,
        mdir_display=mdir_display,
        mdir_verilated=True,
        missing_context=[],
        diagnostic="recognized closure resolved to a verilated mdir ready for sidecar make-time prep",
    )


def run_native_sidecar_build(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
    shape: str = "64x1",
    template_runner=None,
) -> dict[str, object]:
    """Plan, then delegate a recognized closure to the reviewed template flow (FC-055)."""
    root = (repo_root or Path.cwd()).resolve()
    plan = plan_native_sidecar_build(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
        mdir_override=mdir_override,
    )
    plan["template_flow_shape"] = shape
    plan["template_flow_invoked"] = False
    plan["template_flow_passed"] = False
    plan["diagnostic_native_exe_is_cpu_only"] = (
        "the make-emitted --main executable is a CPU binary; GPU execution and "
        "coverage-output equivalence are produced by the delegated template flow"
    )
    if plan["status"] != STATUS_BUILD_PLAN_READY:
        return plan

    launch_template = str(plan["launch_template"])
    if template_runner is None:
        from run_hybrid_template import main as template_runner  # noqa: PLC0415

    returncode = template_runner([str(root / launch_template), "--shape", shape])
    plan["template_flow_invoked"] = True
    plan["template_flow_returncode"] = int(returncode)
    plan["template_flow_passed"] = returncode == 0
    return plan


def prepare_direct_shim_smoke(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
) -> dict[str, object]:
    """FC-059 make-time prep for the direct executable sidecar shim."""
    plan = plan_native_sidecar_build(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=repo_root,
        registry_path=registry_path,
        mdir_override=mdir_override,
    )
    plan["mode"] = "prepare_direct_shim_smoke"
    plan["template_flow_invoked"] = False
    plan["run_hybrid_template_invoked"] = False
    plan["direct_shim_link_prepared"] = plan["status"] == STATUS_BUILD_PLAN_READY
    plan["runtime_evidence_written_by"] = "native_sidecar_shim executable at run time, not this build-time step"
    if plan["status"] == STATUS_BUILD_PLAN_READY:
        plan["diagnostic"] = "recognized closure is ready to link the direct executable shim smoke object"
    return plan


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run", "prepare-direct-shim-smoke"))
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--filelist", required=True)
    parser.add_argument("--top-module", required=True)
    parser.add_argument("--mdir", default=None)
    parser.add_argument("--registry", default=None)
    parser.add_argument("--summary-out", default=None)
    parser.add_argument("--sim-accel", default=None)
    parser.add_argument("--sim-accel-states", default=None)
    parser.add_argument("--sim-accel-steps", default=None)
    return parser


def _shape_from_args(states: str | None, steps: str | None) -> str:
    n = int(states) if states else 64
    s = int(steps) if steps else 1
    return f"{n}x{s}"


def main(argv: list[str] | None = None) -> int:
    import json as _json

    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    if args.command == "plan":
        report = plan_native_sidecar_build(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
        )
    elif args.command == "prepare-direct-shim-smoke":
        report = prepare_direct_shim_smoke(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
        )
    else:
        report = run_native_sidecar_build(
            filelist_path=args.filelist,
            top_module=args.top_module,
            repo_root=repo_root,
            registry_path=args.registry,
            mdir_override=args.mdir,
            shape=_shape_from_args(args.sim_accel_states, args.sim_accel_steps),
        )
    serialized = _json.dumps(report, indent=2)
    print(serialized)
    if args.summary_out:
        summary_path = Path(args.summary_out)
        if not summary_path.is_absolute():
            summary_path = Path.cwd() / summary_path
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(serialized + "\n", encoding="utf-8")
    if args.command == "plan":
        return 0 if report["status"] == STATUS_BUILD_PLAN_READY else 1
    if args.command == "prepare-direct-shim-smoke":
        return 0 if report["status"] == STATUS_BUILD_PLAN_READY else 1
    return 0 if report.get("template_flow_passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
