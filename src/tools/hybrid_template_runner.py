#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class HybridTemplatePlan:
    template_path: Path
    target: str
    target_name: str
    top_module: str
    mdir: Path
    host_probe_target: str
    source_gate: Path | None
    source_files: list[Path]
    verilator_args: list[str]
    cpu_init_state: Path
    cpu_reference_state: Path
    gpu_candidate_state: Path
    cpu_init_report: Path
    cpu_report: Path
    hybrid_report: Path
    compare_report: Path
    nstates: int
    steps: int
    cfg_batch_length: int
    cfg_reset_cycles: int
    cfg_drain_cycles: int
    cfg_seed: int


def _repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_shape(raw: str) -> tuple[int, int]:
    parts = raw.lower().split("x")
    if len(parts) != 2:
        raise ValueError("shape must be formatted as NxS, for example 64x1")
    nstates, steps = int(parts[0]), int(parts[1])
    if nstates <= 0 or steps <= 0:
        raise ValueError("shape values must be positive")
    return nstates, steps


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
    payload = json.loads(template_path.read_text(encoding="utf-8"))
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


def command_plan(plan: HybridTemplatePlan) -> list[list[str]]:
    shape = f"{plan.nstates}x{plan.steps}"
    verilator = [
        "verilator",
        "--cc",
        "--timing",
        "-Mdir",
        _display_path(plan.mdir),
        *plan.verilator_args,
        *[_display_path(path) for path in plan.source_files],
        "--top-module",
        plan.top_module,
    ]
    template_payload = json.loads(plan.template_path.read_text(encoding="utf-8"))
    build = template_payload.get("build") or {}
    host_probe_builder = build.get("host_probe_builder")
    if host_probe_builder:
        make_probe = ["python3", str(host_probe_builder), _display_path(plan.template_path)]
    else:
        make_probe = ["make", "-C", "src/hybrid", plan.host_probe_target]
    cpu_init = [
        _display_path(plan.mdir / "tlul_slice_host_probe"),
        "--repeat-states",
        "1",
        "--repeat-eval-steps",
        "1",
        "--set",
        "cfg_valid_i=1",
        "--set",
        f"cfg_batch_length_i={plan.cfg_batch_length}",
        "--set",
        f"cfg_reset_cycles_i={plan.cfg_reset_cycles}",
        "--set",
        f"cfg_drain_cycles_i={plan.cfg_drain_cycles}",
        "--set",
        f"cfg_seed_i={plan.cfg_seed}",
        "--repeat-state-out",
        _display_path(plan.cpu_init_state),
    ]
    cpu_ref = [
        _display_path(plan.mdir / "tlul_slice_host_probe"),
        "--repeat-states",
        str(plan.nstates),
        "--repeat-eval-steps",
        str(plan.steps),
        "--set",
        "cfg_valid_i=1",
        "--set",
        f"cfg_batch_length_i={plan.cfg_batch_length}",
        "--set",
        f"cfg_reset_cycles_i={plan.cfg_reset_cycles}",
        "--set",
        f"cfg_drain_cycles_i={plan.cfg_drain_cycles}",
        "--set",
        f"cfg_seed_i={plan.cfg_seed}",
        "--repeat-state-out",
        _display_path(plan.cpu_reference_state),
    ]
    gpu_build = ["python3", "src/tools/build_vl_gpu.py", _display_path(plan.mdir), "--force"]
    hybrid = [
        "python3",
        "src/tools/run_vl_hybrid.py",
        "--mdir",
        _display_path(plan.mdir),
        "--nstates",
        str(plan.nstates),
        "--steps",
        str(plan.steps),
        "--init-state",
        _display_path(plan.cpu_init_state),
        "--sanitize-host-only-internals",
        "--dump-state",
        _display_path(plan.gpu_candidate_state),
    ]
    compare = [
        "python3",
        "src/tools/compare_vl_hybrid_modes.py",
        _display_path(plan.mdir),
        "--compare-dumps",
        _display_path(plan.cpu_reference_state),
        _display_path(plan.gpu_candidate_state),
        "--reference-label",
        f"cpu_repeat_{shape}",
        "--candidate-label",
        f"hybrid_from_cpu_init_{shape}",
        "--acceptance-policy",
        "coverage_output_equivalence",
        "--json-out",
        _display_path(plan.compare_report),
    ]
    if plan.source_gate is not None:
        compare.extend(
            [
                "--coverage-output-gate",
                _display_path(plan.source_gate),
                "--coverage-output-target",
                plan.target_name,
            ]
        )
    return [verilator, make_probe, cpu_init, cpu_ref, gpu_build, hybrid, compare]


def run_plan(plan: HybridTemplatePlan, *, dry_run: bool = False) -> None:
    commands = command_plan(plan)
    for index, command in enumerate(commands, start=1):
        print("+ " + " ".join(command))
        if dry_run:
            continue
        if index == 3:
            plan.cpu_init_report.parent.mkdir(parents=True, exist_ok=True)
            with plan.cpu_init_report.open("w", encoding="utf-8") as out:
                subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=out)
        elif index == 4:
            plan.cpu_report.parent.mkdir(parents=True, exist_ok=True)
            # Keep the shape-specific report separate from the 1x1 init report.
            with plan.cpu_report.open("w", encoding="utf-8") as out:
                subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=out)
        elif index == 6:
            plan.hybrid_report.parent.mkdir(parents=True, exist_ok=True)
            with plan.hybrid_report.open("w", encoding="utf-8") as out:
                subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=out)
        else:
            subprocess.run(command, cwd=REPO_ROOT, check=True)
