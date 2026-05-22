from __future__ import annotations

from pathlib import Path

from build_vl_gpu_inputs import detect_storage_size
from build_vl_gpu_stage_env import VLGPUGEN, run
from build_vl_gpu_state import resolve_existing_storage_size


def analyze_phase_ir(*, mdir: Path, merged_ll: Path) -> None:
    phase_json = (mdir / "vl_phase_analysis.json").resolve()
    print("  [analyze-phases] vlgpugen --analyze-phases merged.ll", flush=True)
    run(
        [
            str(VLGPUGEN),
            str(merged_ll),
            "--analyze-phases",
            f"--analyze-phases-json={phase_json}",
        ]
    )


def resolve_build_storage_size(
    *,
    mdir: Path,
    prefix: str,
    existing_meta: dict | None,
    reuse_gpu_patched_ll: bool,
    syms_state_image: bool,
    syms_storage_size: int | None,
    state_root_offset: int | None,
) -> tuple[int, int | None]:
    existing_storage_size = resolve_existing_storage_size(existing_meta)
    if reuse_gpu_patched_ll and existing_storage_size is not None:
        print(f"  [meta] reuse storage_size = {existing_storage_size} bytes")
        return existing_storage_size, None

    print("  [probe] detecting storage_size...")
    root_storage_size = detect_storage_size(mdir, prefix)
    storage_size = syms_storage_size if syms_state_image else root_storage_size
    print(f"  root_storage_size = {root_storage_size} bytes")
    if syms_state_image:
        print(
            f"  syms_storage_size = {storage_size} bytes; "
            f"root_offset_in_state = {state_root_offset} bytes"
        )
    else:
        print(f"  storage_size = {storage_size} bytes")
    return storage_size, root_storage_size
