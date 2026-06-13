"""Bridge a recognized native sidecar closure to the build_vl_gpu pipeline.

This is the repo-side driver invoked from the generated Makefile hook when
``verilator --sim-accel sidecar-gpu`` is used. It recognizes the filelist/top
pair against the tracked known closures and, only for a recognized closure,
hands the verilated ``mdir`` to the existing ``build_vl_gpu`` GPU pipeline.

Recognition and plan construction are compile-side metadata only: they never
claim GPU execution, never fall back to CPU, and fail closed for any
unrecognized closure or missing verilated ``mdir``.
"""

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
    "only a tracked known closure can reach the build_vl_gpu pipeline",
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
    """Recognize the closure and resolve the build_vl_gpu mdir without building.

    ``mdir_override`` lets the generated Makefile hook pass the directory
    Verilator actually emitted into (``--Mdir``); when absent the canonical
    mdir is taken from the recognized closure template.
    """
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
        # The Makefile hook passes the directory make is running in (e.g. "."),
        # so a relative override resolves against the current working directory,
        # not the repo root.
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
        diagnostic="recognized closure resolved to a verilated mdir ready for the build_vl_gpu pipeline",
    )


def run_native_sidecar_build(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
    mdir_override: str | Path | None = None,
    builder=None,
) -> dict[str, object]:
    """Plan, then drive build_vl_gpu only when the plan is ready. Fail closed otherwise."""
    root = (repo_root or Path.cwd()).resolve()
    plan = plan_native_sidecar_build(
        filelist_path=filelist_path,
        top_module=top_module,
        repo_root=root,
        registry_path=registry_path,
        mdir_override=mdir_override,
    )
    plan["build_invoked"] = False
    if plan["status"] != STATUS_BUILD_PLAN_READY:
        return plan

    if builder is None:
        from build_vl_gpu import build_vl_gpu as builder  # noqa: PLC0415

    cubin, storage_size = builder(root / str(plan["mdir"]))
    plan["build_invoked"] = True
    plan["cubin"] = _display_path(Path(cubin), root)
    plan["syms_storage_size"] = int(storage_size)
    return plan


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--filelist", required=True)
    parser.add_argument("--top-module", required=True)
    parser.add_argument("--mdir", default=None)
    parser.add_argument("--registry", default=None)
    parser.add_argument("--summary-out", default=None)
    # Accepted for forward compatibility with the Makefile hook; recognition,
    # not these values, decides the closure.
    parser.add_argument("--sim-accel", default=None)
    parser.add_argument("--sim-accel-states", default=None)
    parser.add_argument("--sim-accel-steps", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    import json as _json

    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    kwargs = dict(
        filelist_path=args.filelist,
        top_module=args.top_module,
        repo_root=repo_root,
        registry_path=args.registry,
        mdir_override=args.mdir,
    )
    report = plan_native_sidecar_build(**kwargs) if args.command == "plan" else run_native_sidecar_build(**kwargs)
    serialized = _json.dumps(report, indent=2)
    print(serialized)
    if args.summary_out:
        # The Makefile hook runs in the obj_dir and passes a bare filename, so a
        # relative summary path resolves against the current working directory.
        summary_path = Path(args.summary_out)
        if not summary_path.is_absolute():
            summary_path = Path.cwd() / summary_path
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(serialized + "\n", encoding="utf-8")
    if args.command == "plan":
        return 0 if report["status"] == STATUS_BUILD_PLAN_READY else 1
    return 0 if report.get("build_invoked") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
