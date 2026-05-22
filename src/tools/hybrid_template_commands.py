"""Command planning and execution for hybrid template plans."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from hybrid_template_normalize import normalize_template_payload
from hybrid_template_types import HybridTemplatePlan


REPO_ROOT = Path(__file__).resolve().parents[2]


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _compare_command_impl(plan: HybridTemplatePlan, *, repo_root: Path) -> list[str]:
    shape = f"{plan.nstates}x{plan.steps}"
    compare = [
        "python3",
        "src/tools/compare_vl_hybrid_modes.py",
        _display_path_with_root(plan.mdir, repo_root=repo_root),
        "--compare-dumps",
        _display_path_with_root(plan.cpu_reference_state, repo_root=repo_root),
        _display_path_with_root(plan.gpu_candidate_state, repo_root=repo_root),
        "--reference-label",
        f"cpu_repeat_{shape}",
        "--candidate-label",
        f"hybrid_from_cpu_init_{shape}",
        "--acceptance-policy",
        "coverage_output_equivalence",
        "--json-out",
        _display_path_with_root(plan.compare_report, repo_root=repo_root),
    ]
    if plan.source_gate is not None:
        compare.extend(
            [
                "--coverage-output-gate",
                _display_path_with_root(plan.source_gate, repo_root=repo_root),
                "--coverage-output-target",
                plan.target_name,
            ]
        )
    return compare


def _display_path_with_root(path: Path, *, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root))
    except ValueError:
        return str(path)


def _verilator_command(plan: HybridTemplatePlan) -> list[str]:
    return [
        "verilator",
        "--cc",
        "--timing",
        "-Mdir",
        _display_path(plan.mdir),
        *[f"-D{define}" for define in plan.verilator_defines],
        *plan.verilator_args,
        *[_display_path(path) for path in plan.source_files],
        "--top-module",
        plan.top_module,
    ]


def _make_probe_command(plan: HybridTemplatePlan) -> list[str]:
    template_payload = normalize_template_payload(
        json.loads(plan.template_path.read_text(encoding="utf-8"))
    )
    build = template_payload.get("build") or {}
    host_probe_builder = build.get("host_probe_builder")
    if host_probe_builder:
        return ["python3", str(host_probe_builder), _display_path(plan.template_path)]
    return ["make", "-C", "src/hybrid", plan.host_probe_target]


def _host_probe_repeat_command(
    *,
    plan: HybridTemplatePlan,
    nstates: int,
    steps: int,
    output: Path,
) -> list[str]:
    return [
        _display_path(plan.mdir / "tlul_slice_host_probe"),
        "--repeat-states",
        str(nstates),
        "--repeat-eval-steps",
        str(steps),
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
        _display_path(output),
    ]


def _gpu_build_command(plan: HybridTemplatePlan) -> list[str]:
    return ["python3", "src/tools/build_vl_gpu.py", _display_path(plan.mdir), "--force"]


def _hybrid_command(plan: HybridTemplatePlan) -> list[str]:
    return [
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


def _compare_command(plan: HybridTemplatePlan) -> list[str]:
    return _compare_command_impl(plan, repo_root=REPO_ROOT)


def command_plan(plan: HybridTemplatePlan) -> list[list[str]]:
    verilator = _verilator_command(plan)
    make_probe = _make_probe_command(plan)
    cpu_init = _host_probe_repeat_command(plan=plan, nstates=1, steps=1, output=plan.cpu_init_state)
    cpu_ref = _host_probe_repeat_command(
        plan=plan,
        nstates=plan.nstates,
        steps=plan.steps,
        output=plan.cpu_reference_state,
    )
    return [
        verilator,
        make_probe,
        cpu_init,
        cpu_ref,
        _gpu_build_command(plan),
        _hybrid_command(plan),
        _compare_command(plan),
    ]


def run_plan(plan: HybridTemplatePlan, *, dry_run: bool = False) -> None:
    for index, command in enumerate(command_plan(plan), start=1):
        print("+ " + " ".join(command))
        if dry_run:
            continue
        if index == 3:
            plan.cpu_init_report.parent.mkdir(parents=True, exist_ok=True)
            with plan.cpu_init_report.open("w", encoding="utf-8") as out:
                subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=out)
        elif index == 4:
            plan.cpu_report.parent.mkdir(parents=True, exist_ok=True)
            with plan.cpu_report.open("w", encoding="utf-8") as out:
                subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=out)
        elif index == 6:
            plan.hybrid_report.parent.mkdir(parents=True, exist_ok=True)
            with plan.hybrid_report.open("w", encoding="utf-8") as out:
                subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=out)
        else:
            subprocess.run(command, cwd=REPO_ROOT, check=True)
