from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from run_vl_hybrid_launch_env import (
    configure_kernel_env,
    configure_launch_env,
    configure_persistent_resident_env,
    configure_runtime_mode_env,
    configure_state_io_env,
    prepare_init_state_env,
)
from run_vl_hybrid_state_sanitize import (
    _detect_unsupported_nonflat_syms_state,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
HYBRID_BIN = REPO_ROOT / "artifacts" / "tool_bins" / "hybrid" / "run_vl_hybrid"


def _hybrid_src_dir() -> Path:
    return REPO_ROOT / "src" / "hybrid"


@dataclass(frozen=True)
class LaunchResolution:
    mdir: Path | None
    meta: dict[str, object] | None
    cubin_paths: list[Path]
    cubin: Path
    storage: int
    launch_sequence: object | None


def _parse_path_list(raw: str | None) -> list[Path] | None:
    if raw is None:
        return None
    items = [part.strip() for part in raw.split(",")]
    return [Path(item).resolve() for item in items if item]


def _resolve_meta_cubins(mdir: Path, meta: dict[str, object]) -> list[Path]:
    cubins = meta.get("cubins")
    if isinstance(cubins, list) and cubins:
        return [(mdir / str(item)).resolve() for item in cubins]
    return [(mdir / str(meta["cubin"])).resolve()]


def ensure_hybrid_runtime_built() -> None:
    if HYBRID_BIN.is_file():
        return
    src_dir = _hybrid_src_dir()
    command = ["make", "-C", str(src_dir), "--no-print-directory"]
    print(f"info: building missing hybrid runtime: {' '.join(command)}", file=sys.stderr)
    try:
        subprocess.run(command, cwd=REPO_ROOT, check=True)
    except FileNotFoundError:
        print("error: make not found while building hybrid runtime", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(
            f"error: failed to build hybrid runtime with exit code {exc.returncode}",
            file=sys.stderr,
        )
        sys.exit(1)


def resolve_launch_inputs(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> LaunchResolution:
    cubin_override = _parse_path_list(args.cubins)
    if args.mdir:
        mdir = args.mdir.resolve()
        meta_path = mdir / "vl_batch_gpu.meta.json"
        if not meta_path.is_file():
            print(f"error: {meta_path} not found — run build_vl_gpu.py first", file=sys.stderr)
            sys.exit(1)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("schema_version") is None:
            print("warning: meta.json missing schema_version (older build)", file=sys.stderr)
        cubin_paths = cubin_override if cubin_override is not None else _resolve_meta_cubins(mdir, meta)
        return LaunchResolution(
            mdir=mdir,
            meta=meta,
            cubin_paths=cubin_paths,
            cubin=cubin_paths[0],
            storage=int(meta["storage_size"]),
            launch_sequence=meta.get("launch_sequence"),
        )
    if args.storage_size is None:
        parser.error("either --mdir or --storage-size is required")
    if cubin_override is not None:
        cubin_paths = cubin_override
    elif args.cubin:
        cubin_paths = [args.cubin.resolve()]
    else:
        parser.error("either --mdir, --cubin, or --cubins is required")
    return LaunchResolution(
        mdir=None,
        meta=None,
        cubin_paths=cubin_paths,
        cubin=cubin_paths[0],
        storage=int(args.storage_size),
        launch_sequence=None,
    )


def require_launch_files(resolution: LaunchResolution) -> None:
    for cubin_path in resolution.cubin_paths:
        if not cubin_path.is_file():
            print(f"error: cubin not found: {cubin_path}", file=sys.stderr)
            sys.exit(1)
    ensure_hybrid_runtime_built()
    if not HYBRID_BIN.is_file():
        print(
            f"error: {HYBRID_BIN} not found — run: make -C {_hybrid_src_dir()}",
            file=sys.stderr,
        )
        sys.exit(1)
    if resolution.mdir is not None:
        unsupported = _detect_unsupported_nonflat_syms_state(resolution.mdir, resolution.meta)
        if unsupported is not None:
            print("error: unsupported_hybrid_target", file=sys.stderr)
            print(json.dumps(unsupported, sort_keys=True), file=sys.stderr)
            sys.exit(2)


def build_runner_command(args: argparse.Namespace, resolution: LaunchResolution) -> list[str]:
    cmd = [
        str(HYBRID_BIN),
        str(resolution.cubin),
        str(resolution.storage),
        str(args.nstates),
        str(args.block_size),
        str(args.steps),
    ]
    for pat in args.patch:
        cmd.append(pat)
    return cmd
