#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from hybrid_template_commands import command_plan, run_plan
from hybrid_template_normalize import normalize_template_payload
from hybrid_template_types import HybridTemplatePlan, parse_shape


REPO_ROOT = Path(__file__).resolve().parents[2]


def _repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def load_template_plan(
    template_path: Path,
    *,
    shape: str,
    cfg_batch_length: int = 64,
    cfg_reset_cycles: int = 2,
    cfg_drain_cycles: int = 8,
    cfg_seed: int = 1,
) -> HybridTemplatePlan:
    template_path = _repo_path(template_path)
    payload = normalize_template_payload(json.loads(template_path.read_text(encoding="utf-8")))
    target = str(payload["target"])
    target_name = target.split(".")[-1]
    top_module = str(payload["top_module"])
    build = payload["build"]
    mdir = _repo_path(str(build["mdir"]))
    host_probe_target = str(build["host_probe_target"])
    nstates, steps = parse_shape(shape)

    source_files = [_repo_path(item) for item in payload.get("source_files") or []]
    planned_overlay = payload.get("planned_overlay") or {}
    overlay_path = planned_overlay.get("coverage_tb_path")
    if overlay_path:
        overlay = _repo_path(str(overlay_path))
        if overlay not in source_files:
            source_files.append(overlay)
    if not source_files:
        raise ValueError(f"template has no source_files or planned_overlay.coverage_tb_path: {template_path}")

    source_gate = payload.get("source_gate")
    source_gate_path = _repo_path(str(source_gate)) if source_gate else None
    shape_tag = f"{nstates}x{steps}"
    return HybridTemplatePlan(
        template_path=template_path,
        target=target,
        target_name=target_name,
        top_module=top_module,
        mdir=mdir,
        host_probe_target=host_probe_target,
        source_gate=source_gate_path,
        source_files=source_files,
        verilator_defines=[str(item) for item in payload.get("verilator_defines") or []],
        verilator_args=[str(item) for item in payload.get("verilator_args") or []],
        cpu_init_state=mdir / f"{target_name}_cpu_repeat_1x1.bin",
        cpu_reference_state=mdir / f"{target_name}_cpu_repeat_{shape_tag}.bin",
        gpu_candidate_state=mdir / f"{target_name}_gpu_from_cpu_init_{shape_tag}.bin",
        cpu_init_report=REPO_ROOT / "reports" / f"{target_name}_cpu_repeat_1x1.json",
        cpu_report=REPO_ROOT / "reports" / f"{target_name}_cpu_repeat_{shape_tag}.json",
        hybrid_report=REPO_ROOT / "reports" / f"{target_name}_hybrid_{shape_tag}.txt",
        compare_report=REPO_ROOT / "reports" / f"{target_name}_cpu_vs_hybrid_{shape_tag}_coverage_output_compare.json",
        nstates=nstates,
        steps=steps,
        cfg_batch_length=cfg_batch_length,
        cfg_reset_cycles=cfg_reset_cycles,
        cfg_drain_cycles=cfg_drain_cycles,
        cfg_seed=cfg_seed,
    )
