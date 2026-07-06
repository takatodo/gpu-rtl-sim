#!/usr/bin/env python3
"""Regenerate the gateGPT tb_core ordering-aware entry-sliced CUBIN chain."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TOOLS_DIR = _REPO_ROOT / "src" / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from rtlmeter_vortex_ptx_entry_slice import build_slice


DEFAULT_SOURCE_PTX = Path(
    "artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ptx"
)
DEFAULT_OUT_DIR = Path("artifacts/gategpt_tb_core_ptx_entry_slice")
DEFAULT_REPORT = Path(
    "reports/gategpt_tb_core_entry_sliced_cubin_chain_regeneration.json"
)
DEFAULT_GPU_NAME = "sm_89"
DEFAULT_PTXAS_TIMEOUT_SECONDS = 180.0

SLICE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "vl_eval_patch_feedback_support",
        "entries": [
            "vl_apply_patch_schedule_gpu",
            "vl_apply_feedback_edges_gpu",
            "vl_apply_feedback_increments_gpu",
        ],
    },
    {
        "name": "vl_feedback_pair_cycle_loop",
        "entries": [
            "vl_apply_feedback_sets_gpu",
            "vl_apply_feedback_combined_gpu",
        ],
    },
    {
        "name": "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu",
        "entries": [
            "vl_eval_batch_gpu",
            "vl_apply_patch_schedule_gpu",
            "vl_apply_feedback_edges_gpu",
            "vl_apply_feedback_increments_gpu",
            "vl_apply_feedback_sets_gpu",
            "vl_apply_feedback_combined_gpu",
            "vl_patch_eval_batch_gpu",
            "vl_patch_eval_pair_cycle_batch_gpu",
            "vl_patch_eval_pair_cycle_loop_batch_gpu",
            "vl_probe_u64_load_gpu",
            "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu",
        ],
    },
)


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _tail(text: str, *, max_lines: int = 20) -> str:
    return "\n".join(text.splitlines()[-max_lines:])


def _sanitize_text(text: str, *, repo_root: Path) -> str:
    root = repo_root.resolve().as_posix()
    return text.replace(root, "<repo>")


def _ptxas_command(
    *,
    ptxas: str,
    gpu_name: str,
    ptxas_opt_level: int | None,
    ptx: Path,
    cubin: Path,
) -> list[str]:
    command = [ptxas, f"--gpu-name={gpu_name}"]
    if ptxas_opt_level is not None:
        command.extend(["--opt-level", str(ptxas_opt_level)])
    command.extend([str(ptx), "-o", str(cubin)])
    return command


def _run_ptxas(
    *,
    repo_root: Path,
    ptxas: str,
    gpu_name: str,
    ptxas_opt_level: int | None,
    ptx: Path,
    cubin: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    command = _ptxas_command(
        ptxas=ptxas,
        gpu_name=gpu_name,
        ptxas_opt_level=ptxas_opt_level,
        ptx=ptx,
        cubin=cubin,
    )
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        timed_out = False
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        returncode = None

    cubin_exists = cubin.is_file()
    if timed_out:
        status = "ptxas_timeout"
    elif returncode != 0:
        status = "ptxas_failed"
    elif not cubin_exists:
        status = "ptxas_output_missing"
    else:
        status = "ptxas_passed"
    return {
        "status": status,
        "command": [
            _sanitize_text(str(item), repo_root=repo_root) for item in command
        ],
        "returncode": returncode,
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "stdout_tail": _sanitize_text(_tail(stdout), repo_root=repo_root),
        "stderr_tail": _sanitize_text(_tail(stderr), repo_root=repo_root),
        "cubin": _display_path(cubin, repo_root=repo_root),
        "cubin_exists": cubin_exists,
    }


def _slice_manifest_path(cubin: Path) -> Path:
    return cubin.with_suffix(".cubin.slice.json")


def _slice_manifest_payload(
    *,
    repo_root: Path,
    ptx: Path,
    cubin: Path,
    slice_content_sha256: str,
    ptxas: str,
    gpu_name: str,
    ptxas_opt_level: int | None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "surface": "gategpt_tb_core_ordering_aware_entry_sliced_cubin_chain",
        "ptx": _display_path(ptx, repo_root=repo_root),
        "cubin": _display_path(cubin, repo_root=repo_root),
        "slice_content_sha256": slice_content_sha256,
        "ptxas": ptxas,
        "gpu_name": gpu_name,
        "ptxas_opt_level": ptxas_opt_level,
    }


def _write_slice_manifest(
    *,
    repo_root: Path,
    ptx: Path,
    cubin: Path,
    slice_content_sha256: str,
    ptxas: str,
    gpu_name: str,
    ptxas_opt_level: int | None,
) -> None:
    manifest = _slice_manifest_path(cubin)
    manifest.write_text(
        json.dumps(
            _slice_manifest_payload(
                repo_root=repo_root,
                ptx=ptx,
                cubin=cubin,
                slice_content_sha256=slice_content_sha256,
                ptxas=ptxas,
                gpu_name=gpu_name,
                ptxas_opt_level=ptxas_opt_level,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _slice_manifest_matches(
    *,
    repo_root: Path,
    ptx: Path,
    cubin: Path,
    slice_content_sha256: str,
    ptxas: str,
    gpu_name: str,
    ptxas_opt_level: int | None,
) -> bool:
    manifest = _slice_manifest_path(cubin)
    if not manifest.is_file():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected = _slice_manifest_payload(
        repo_root=repo_root,
        ptx=ptx,
        cubin=cubin,
        slice_content_sha256=slice_content_sha256,
        ptxas=ptxas,
        gpu_name=gpu_name,
        ptxas_opt_level=ptxas_opt_level,
    )
    return all(payload.get(key) == value for key, value in expected.items())


def _reuse_existing_cubin(
    *,
    repo_root: Path,
    ptx: Path,
    cubin: Path,
    ptxas: str,
    gpu_name: str,
    ptxas_opt_level: int | None,
    slice_content_sha256: str,
) -> dict[str, Any]:
    manifest = _slice_manifest_path(cubin)
    if not _slice_manifest_matches(
        repo_root=repo_root,
        ptx=ptx,
        cubin=cubin,
        slice_content_sha256=slice_content_sha256,
        ptxas=ptxas,
        gpu_name=gpu_name,
        ptxas_opt_level=ptxas_opt_level,
    ):
        return {
            "status": "not_reused_slice_manifest_missing_or_mismatch",
            "command": [
                _sanitize_text(str(item), repo_root=repo_root)
                for item in _ptxas_command(
                    ptxas=ptxas,
                    gpu_name=gpu_name,
                    ptxas_opt_level=ptxas_opt_level,
                    ptx=ptx,
                    cubin=cubin,
                )
            ],
            "returncode": None,
            "timed_out": False,
            "timeout_seconds": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "cubin": _display_path(cubin, repo_root=repo_root),
            "cubin_exists": cubin.is_file(),
            "manifest": _display_path(manifest, repo_root=repo_root),
            "manifest_matches": False,
        }
    now = None
    try:
        now = max(ptx.stat().st_mtime, cubin.stat().st_mtime, manifest.stat().st_mtime)
        os.utime(cubin, (now, now))
        os.utime(manifest, (now, now))
    except OSError:
        pass
    return {
        "status": "ptxas_reused_existing_cubin",
        "command": [
            _sanitize_text(str(item), repo_root=repo_root)
            for item in _ptxas_command(
                ptxas=ptxas,
                gpu_name=gpu_name,
                ptxas_opt_level=ptxas_opt_level,
                ptx=ptx,
                cubin=cubin,
            )
        ],
        "returncode": 0,
        "timed_out": False,
        "timeout_seconds": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "cubin": _display_path(cubin, repo_root=repo_root),
        "cubin_exists": cubin.is_file(),
        "manifest": _display_path(manifest, repo_root=repo_root),
        "manifest_matches": True,
        "reuse_reason": "slice_ptx_content_unchanged",
        "reused_cubin_mtime": now,
    }


def regenerate_chain(
    repo_root: Path,
    *,
    source_ptx: Path = DEFAULT_SOURCE_PTX,
    out_dir: Path = DEFAULT_OUT_DIR,
    write_slices: bool = True,
    run_ptxas: bool = True,
    ptxas: str = "ptxas",
    gpu_name: str = DEFAULT_GPU_NAME,
    ptxas_opt_level: int | None = 0,
    ptxas_timeout_seconds: float = DEFAULT_PTXAS_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = repo_root.resolve()
    source = source_ptx if source_ptx.is_absolute() else root / source_ptx
    out = out_dir if out_dir.is_absolute() else root / out_dir
    ptxas_available = shutil.which(ptxas) is not None if run_ptxas else None
    slices: list[dict[str, Any]] = []

    for spec in SLICE_SPECS:
        name = str(spec["name"])
        ptx_out = out / f"{name}.ptx"
        cubin_out = out / f"{name}.cubin"
        slice_report = build_slice(
            root,
            ptx_path=source,
            out_path=ptx_out,
            entry=str(spec["entries"][0]),
            keep_entries=list(spec["entries"]),
            prune_unreferenced_funcs=True,
            write_slice=write_slices,
            case="gateGPT:tb_core",
            surface="gategpt_tb_core_ordering_aware_entry_sliced_cubin_chain",
            next_required_boundary=(
                "run_2state_ordering_aware_full_phase_after_sliced_cubin_regeneration"
            ),
        )
        entry: dict[str, Any] = {
            "name": name,
            "entries": list(spec["entries"]),
            "ptx": _display_path(ptx_out, repo_root=root),
            "cubin": _display_path(cubin_out, repo_root=root),
            "slice": slice_report,
        }
        if run_ptxas:
            if not ptxas_available:
                entry["ptxas"] = {
                    "status": "ptxas_missing",
                    "command": None,
                    "cubin_exists": cubin_out.is_file(),
                }
            elif slice_report.get("status") != "entry_slice_written":
                entry["ptxas"] = {
                    "status": "not_run_slice_not_written",
                    "command": None,
                    "cubin_exists": cubin_out.is_file(),
                }
            elif (
                slice_report.get("existing_slice_content_unchanged")
                and cubin_out.is_file()
            ):
                reuse = _reuse_existing_cubin(
                    repo_root=root,
                    ptx=ptx_out,
                    cubin=cubin_out,
                    ptxas=ptxas,
                    gpu_name=gpu_name,
                    ptxas_opt_level=ptxas_opt_level,
                    slice_content_sha256=str(
                        slice_report.get("slice_content_sha256", "")
                    ),
                )
                if reuse["status"] == "ptxas_reused_existing_cubin":
                    entry["ptxas"] = reuse
                else:
                    ptxas_report = _run_ptxas(
                        repo_root=root,
                        ptxas=ptxas,
                        gpu_name=gpu_name,
                        ptxas_opt_level=ptxas_opt_level,
                        ptx=ptx_out,
                        cubin=cubin_out,
                        timeout_seconds=ptxas_timeout_seconds,
                    )
                    ptxas_report["reuse_attempt"] = reuse
                    if ptxas_report["status"] == "ptxas_passed":
                        _write_slice_manifest(
                            repo_root=root,
                            ptx=ptx_out,
                            cubin=cubin_out,
                            slice_content_sha256=str(
                                slice_report.get("slice_content_sha256", "")
                            ),
                            ptxas=ptxas,
                            gpu_name=gpu_name,
                            ptxas_opt_level=ptxas_opt_level,
                        )
                    entry["ptxas"] = ptxas_report
            else:
                ptxas_report = _run_ptxas(
                    repo_root=root,
                    ptxas=ptxas,
                    gpu_name=gpu_name,
                    ptxas_opt_level=ptxas_opt_level,
                    ptx=ptx_out,
                    cubin=cubin_out,
                    timeout_seconds=ptxas_timeout_seconds,
                )
                if ptxas_report["status"] == "ptxas_passed":
                    _write_slice_manifest(
                        repo_root=root,
                        ptx=ptx_out,
                        cubin=cubin_out,
                        slice_content_sha256=str(
                            slice_report.get("slice_content_sha256", "")
                        ),
                        ptxas=ptxas,
                        gpu_name=gpu_name,
                        ptxas_opt_level=ptxas_opt_level,
                    )
                entry["ptxas"] = ptxas_report
        else:
            entry["ptxas"] = {
                "status": "not_run",
                "command": [
                    _sanitize_text(str(item), repo_root=root)
                    for item in _ptxas_command(
                        ptxas=ptxas,
                        gpu_name=gpu_name,
                        ptxas_opt_level=ptxas_opt_level,
                        ptx=ptx_out,
                        cubin=cubin_out,
                    )
                ],
                "cubin_exists": cubin_out.is_file(),
            }
        slices.append(entry)

    slice_statuses = [str(item["slice"].get("status")) for item in slices]
    ptxas_statuses = [str(item["ptxas"].get("status")) for item in slices]
    if any(status != "entry_slice_written" for status in slice_statuses):
        status = "entry_slice_regeneration_failed"
    elif run_ptxas and any(
        status not in {"ptxas_passed", "ptxas_reused_existing_cubin"}
        for status in ptxas_statuses
    ):
        status = "entry_sliced_cubin_regeneration_failed"
    elif run_ptxas:
        status = "entry_sliced_cubin_chain_regenerated"
    else:
        status = "entry_sliced_ptx_chain_regenerated_ptxas_not_run"

    return {
        "schema_version": 1,
        "surface": "gategpt_tb_core_ordering_aware_entry_sliced_cubin_chain",
        "status": status,
        "source_ptx": _display_path(source, repo_root=root),
        "out_dir": _display_path(out, repo_root=root),
        "slice_count": len(slices),
        "slices": slices,
        "gpu_name": gpu_name,
        "ptxas_opt_level": ptxas_opt_level,
        "ptxas_timeout_seconds": ptxas_timeout_seconds,
        "next_required_boundary": (
            "run_2state_ordering_aware_full_phase_after_sliced_cubin_regeneration"
        ),
        "runtime_authority": False,
        "kernel_execution_observed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "usefulness_claimed": False,
        "non_claims": [
            "entry_slice_regeneration_is_not_kernel_execution",
            "entry_slice_regeneration_is_not_cpu_vs_hybrid_timing",
            "not_speedup_or_usefulness_claim",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ptx", default=DEFAULT_SOURCE_PTX.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--ptxas", default="ptxas")
    parser.add_argument("--gpu-name", default=DEFAULT_GPU_NAME)
    parser.add_argument("--ptxas-opt-level", type=int, default=0)
    parser.add_argument(
        "--ptxas-timeout-seconds",
        type=float,
        default=DEFAULT_PTXAS_TIMEOUT_SECONDS,
    )
    parser.add_argument("--skip-ptxas", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default=DEFAULT_REPORT.as_posix())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root)
    report = regenerate_chain(
        root,
        source_ptx=Path(args.ptx),
        out_dir=Path(args.out_dir),
        run_ptxas=not args.skip_ptxas,
        ptxas=args.ptxas,
        gpu_name=args.gpu_name,
        ptxas_opt_level=args.ptxas_opt_level,
        ptxas_timeout_seconds=args.ptxas_timeout_seconds,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write_report:
        out = Path(args.report_out)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] in {
        "entry_sliced_cubin_chain_regenerated",
        "entry_sliced_ptx_chain_regenerated_ptxas_not_run",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
