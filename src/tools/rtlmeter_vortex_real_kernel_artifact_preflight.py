#!/usr/bin/env python3
"""Check whether a real Vortex GPU kernel artifact exists for materialized runtime launch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_SEARCH_ROOTS = [
    Path("artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare"),
    Path("artifacts/rtlmeter_vortex_mini_hello_hybrid_candidate"),
    Path("artifacts/rtlmeter_vortex_mini_hello_hybrid_candidate_direct_native"),
]
KERNEL_ARTIFACT_NAMES = {"vl_batch_gpu.cubin", "vl_batch_gpu.ptx"}
METADATA_NAMES = {"vl_batch_gpu.meta.json"}


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _candidate_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and (path.name in KERNEL_ARTIFACT_NAMES or path.name in METADATA_NAMES):
            out.append(path)
    return sorted(out)


def build_preflight(
    repo_root: Path,
    *,
    search_roots: list[Path] | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    roots = search_roots if search_roots is not None else DEFAULT_SEARCH_ROOTS
    resolved_roots = [path if path.is_absolute() else root / path for path in roots]
    files: list[Path] = []
    for item in resolved_roots:
        files.extend(_candidate_files(item))
    artifacts = [path for path in files if path.name in KERNEL_ARTIFACT_NAMES]
    metadata = [path for path in files if path.name in METADATA_NAMES]
    cubins = [path for path in artifacts if path.suffix == ".cubin"]
    ptx = [path for path in artifacts if path.suffix == ".ptx"]
    ready = bool(cubins or ptx) and bool(metadata)
    status = "real_vortex_kernel_artifact_ready" if ready else "real_vortex_kernel_artifact_missing"
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_real_kernel_artifact_preflight",
        "status": status,
        "case": "Vortex:mini:hello",
        "search_roots": [_display_path(path, repo_root=root) for path in resolved_roots],
        "kernel_artifact_ready": ready,
        "kernel_artifact_format": "cubin" if cubins else "ptx" if ptx else None,
        "cubin_count": len(cubins),
        "ptx_count": len(ptx),
        "metadata_count": len(metadata),
        "kernel_artifacts": [_display_path(path, repo_root=root) for path in artifacts],
        "metadata_artifacts": [_display_path(path, repo_root=root) for path in metadata],
        "next_required_boundary": (
            "wire_real_vortex_kernel_artifact_into_materialized_runtime_callback"
            if ready
            else "build_real_vortex_kernel_artifact_for_materialized_runtime_callback"
        ),
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "artifact_presence_is_not_kernel_execution",
            "missing_artifact_preflight_is_not_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--search-root", action="append", dest="search_roots")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_real_kernel_artifact_preflight.json")
    args = parser.parse_args(argv)

    report = build_preflight(
        Path(args.repo_root),
        search_roots=[Path(item) for item in args.search_roots] if args.search_roots else None,
    )
    if args.write_report:
        out = Path(args.report_out)
        if not out.is_absolute():
            out = Path(args.repo_root) / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
