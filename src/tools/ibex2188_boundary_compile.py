"""Verilator + GPU sidecar compile helpers for the pinned Ibex #2188 revisions."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from compare_vl_hybrid_root_layout import probe_root_layout

from ibex2188_boundary_runner_io import (
    BUILD_VL_GPU,
    CPU_DRIVER,
    GPU_TB,
    HYBRID_RUNNER,
    INPUT_OFFSETS,
    OBSERVABLE_OFFSETS,
    REPO_ROOT,
    TOP,
    read_object,
    require_success,
    revision_sha,
    run_repo,
)


def layout_offsets(mdir: Path) -> dict[str, int]:
    """Verify the probe-discovered root layout matches the pinned offsets."""
    fields = probe_root_layout(mdir)
    discovered: dict[str, int] = {}
    for entry in fields:
        name = str(entry["name"])
        for key in INPUT_OFFSETS:
            if name == key and key not in discovered:
                discovered[key] = int(entry["offset"])
        for key in OBSERVABLE_OFFSETS:
            if name == f"{key}_o" and key not in discovered:
                discovered[key] = int(entry["offset"])
    for key, expected in {**INPUT_OFFSETS, **OBSERVABLE_OFFSETS}.items():
        if discovered.get(key) != expected:
            raise RuntimeError(
                f"layout offset drift for {key}: discovered {discovered.get(key)} expected {expected}"
            )
    return dict({**INPUT_OFFSETS, **OBSERVABLE_OFFSETS})


def _core_sources(checkout: Path) -> list[Path]:
    names = [
        "ibex_alu.sv",
        "ibex_branch_predict.sv",
        "ibex_compressed_decoder.sv",
        "ibex_controller.sv",
        "ibex_cs_registers.sv",
        "ibex_csr.sv",
        "ibex_counter.sv",
        "ibex_decoder.sv",
        "ibex_ex_block.sv",
        "ibex_fetch_fifo.sv",
        "ibex_id_stage.sv",
        "ibex_if_stage.sv",
        "ibex_load_store_unit.sv",
        "ibex_multdiv_fast.sv",
        "ibex_multdiv_slow.sv",
        "ibex_prefetch_buffer.sv",
        "ibex_pmp.sv",
        "ibex_wb_stage.sv",
        "ibex_dummy_instr.sv",
        "ibex_icache.sv",
        "ibex_core.sv",
    ]
    sources = [checkout / "rtl" / name for name in names]
    missing = [path for path in sources if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing Ibex core sources: {missing}")
    return sources


def _primitive_sources(checkout: Path) -> list[Path]:
    primitive_dir = checkout / "vendor" / "lowrisc_ip" / "ip" / "prim" / "rtl"
    generic_dir = checkout / "vendor" / "lowrisc_ip" / "ip" / "prim_generic" / "rtl"
    dv_utils_dir = checkout / "vendor" / "lowrisc_ip" / "dv" / "sv" / "dv_utils"
    sources = sorted(
        path
        for path in primitive_dir.glob("*.sv")
        if not path.name.startswith("prim_lc_")
        and path.name not in {"prim_mubi_pkg.sv", "prim_secded_pkg.sv"}
    )
    extra = [
        primitive_dir / "prim_mubi_pkg.sv",
        primitive_dir / "prim_secded_pkg.sv",
        checkout / "rtl" / "ibex_pkg.sv",
        generic_dir / "prim_generic_buf.sv",
        generic_dir / "prim_generic_clock_gating.sv",
    ]
    for path in sources + extra:
        if not path.is_file():
            raise RuntimeError(f"missing primitive source: {path}")
    if not dv_utils_dir.is_dir():
        raise RuntimeError(f"missing DV utils directory: {dv_utils_dir}")
    return sources


def compile_revision(
    *,
    label: str,
    checkout: Path,
    expected_revision: str,
    verilator: Path,
    verilator_root: Path,
    work_dir: Path,
) -> dict[str, Any]:
    observed_revision = revision_sha(checkout)
    if observed_revision != expected_revision:
        raise ValueError(
            f"{label} checkout revision mismatch: expected {expected_revision}, got {observed_revision}"
        )
    revision_dir = work_dir / label
    gpu_mdir = revision_dir / "gpu_obj"
    cpu_mdir = revision_dir / "cpu_obj"
    revision_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["VERILATOR_ROOT"] = str(verilator_root)
    env["PYTHONPATH"] = str(REPO_ROOT / "src" / "tools")

    primitive_dir = checkout / "vendor" / "lowrisc_ip" / "ip" / "prim" / "rtl"
    generic_dir = checkout / "vendor" / "lowrisc_ip" / "ip" / "prim_generic" / "rtl"
    dv_utils_dir = checkout / "vendor" / "lowrisc_ip" / "dv" / "sv" / "dv_utils"
    primitive_sources = _primitive_sources(checkout)

    base = [
        str(verilator),
        "--cc",
        "-Wno-fatal",
        "--public-flat-rw",
        "-DSYNTHESIS",
        "--top-module",
        TOP,
        f"-I{checkout / 'rtl'}",
        f"-I{primitive_dir}",
        f"-I{dv_utils_dir}",
        str(primitive_dir / "prim_mubi_pkg.sv"),
        str(primitive_dir / "prim_secded_pkg.sv"),
        str(checkout / "rtl" / "ibex_pkg.sv"),
        str(generic_dir / "prim_generic_buf.sv"),
        str(generic_dir / "prim_generic_clock_gating.sv"),
    ]
    base.extend(str(source) for source in primitive_sources)
    base.extend(str(source) for source in _core_sources(checkout))
    base.append(str(GPU_TB))

    require_success(run_repo([*base, "--Mdir", str(gpu_mdir)], env=env), f"{label} GPU Verilator compile")
    require_success(
        run_repo([*base, "--exe", str(CPU_DRIVER), "--build", "--Mdir", str(cpu_mdir)], env=env),
        f"{label} CPU Verilator build",
    )
    require_success(
        run_repo(
            [sys.executable, str(BUILD_VL_GPU), str(gpu_mdir), "--sm", "sm_89", "--force"],
            env=env,
        ),
        f"{label} GPU sidecar build",
    )
    meta = read_object(gpu_mdir / "vl_batch_gpu.meta.json", f"{label} GPU metadata")
    storage_size = meta.get("storage_size")
    if isinstance(storage_size, bool) or not isinstance(storage_size, int) or storage_size <= 0:
        raise ValueError(f"{label} GPU storage_size is invalid")
    return {
        "label": label,
        "checkout": checkout,
        "revision": observed_revision,
        "revision_dir": revision_dir,
        "gpu_mdir": gpu_mdir,
        "cpu_binary": cpu_mdir / f"V{TOP}",
        "offsets": layout_offsets(gpu_mdir),
        "storage_size": storage_size,
        "hybrid_runner": HYBRID_RUNNER,
        "env": env,
    }
