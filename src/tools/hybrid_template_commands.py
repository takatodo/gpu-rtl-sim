"""Command planning and execution for hybrid template plans."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

from hybrid_template_normalize import normalize_template_payload
from hybrid_template_types import HybridTemplatePlan
from results_reproduction_io import sanitize_local_absolute_paths


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_STAGE_NAMES = ("verilator_build", "host_probe_build", "cpu_init_state", "cpu_reference_output", "gpu_artifact_build", "hybrid_sidecar_run", "coverage_output_compare")
TEMPLATE_STAGE_LABELS = {
    "verilator_build": "Verilator build",
    "host_probe_build": "Host-probe build",
    "cpu_init_state": "CPU init-state capture",
    "cpu_reference_output": "CPU reference capture",
    "gpu_artifact_build": "GPU artifact build",
    "hybrid_sidecar_run": "Hybrid sidecar run",
    "coverage_output_compare": "Coverage-output compare",
}


class HybridTemplateStageError(RuntimeError):
    pass


def _display_path(path: Path) -> str:
    return _display_path_with_root(path, repo_root=REPO_ROOT)


def resident_template_plan(plan: HybridTemplatePlan, *, resident_label: str = "resident_multistep") -> HybridTemplatePlan:
    shape = f"{plan.nstates}x{plan.steps}"
    return replace(
        plan,
        gpu_candidate_state=plan.mdir / f"{plan.target_name}_gpu_{resident_label}_{shape}.bin",
        hybrid_report=REPO_ROOT / "reports" / f"{plan.target_name}_{resident_label}_{shape}.txt",
        compare_report=REPO_ROOT
        / "reports"
        / f"{plan.target_name}_cpu_vs_{resident_label}_{shape}_coverage_output_compare.json",
    )


def _compare_command_impl(
    plan: HybridTemplatePlan,
    *,
    repo_root: Path,
    candidate_label_prefix: str = "hybrid_from_cpu_init",
) -> list[str]:
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
        f"{candidate_label_prefix}_{shape}",
        "--acceptance-policy",
        "coverage_output_equivalence",
        "--json-out",
        _display_path_with_root(plan.compare_report, repo_root=repo_root),
    ]
    if plan.source_gate is not None:
        compare += [
            "--coverage-output-gate",
            _display_path_with_root(plan.source_gate, repo_root=repo_root),
            "--coverage-output-target",
            plan.target_name,
        ]
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


def _hybrid_command(plan: HybridTemplatePlan, *, resident_patch_script: Path | None = None) -> list[str]:
    command = [
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
    if resident_patch_script is not None:
        command += [
            "--resident-steps",
            "--patch-script",
            _display_path(resident_patch_script),
        ]
    return command


def _compare_command(plan: HybridTemplatePlan, *, candidate_label_prefix: str = "hybrid_from_cpu_init") -> list[str]:
    return _compare_command_impl(plan, repo_root=REPO_ROOT, candidate_label_prefix=candidate_label_prefix)


def command_plan(
    plan: HybridTemplatePlan,
    *,
    resident_patch_script: Path | None = None,
    resident_label: str = "resident_multistep",
) -> list[list[str]]:
    effective_plan = resident_template_plan(plan, resident_label=resident_label) if resident_patch_script else plan
    verilator = _verilator_command(plan)
    make_probe = _make_probe_command(plan)
    cpu_init = _host_probe_repeat_command(plan=plan, nstates=1, steps=1, output=plan.cpu_init_state)
    cpu_ref = _host_probe_repeat_command(
        plan=plan,
        nstates=plan.nstates,
        steps=plan.steps,
        output=plan.cpu_reference_state,
    )
    candidate_label_prefix = f"{resident_label}_from_cpu_init" if resident_patch_script else "hybrid_from_cpu_init"
    return [
        verilator,
        make_probe,
        cpu_init,
        cpu_ref,
        _gpu_build_command(plan),
        _hybrid_command(effective_plan, resident_patch_script=resident_patch_script),
        _compare_command(effective_plan, candidate_label_prefix=candidate_label_prefix),
    ]


def staged_command_plan(
    plan: HybridTemplatePlan,
    *,
    resident_patch_script: Path | None = None,
    resident_label: str = "resident_multistep",
) -> list[tuple[str, list[str]]]:
    commands = command_plan(plan, resident_patch_script=resident_patch_script, resident_label=resident_label)
    return list(zip(TEMPLATE_STAGE_NAMES, commands, strict=True))


def _shape_tag(plan: HybridTemplatePlan) -> str:
    return f"{plan.nstates}x{plan.steps}"


def _stage_log_path(plan: HybridTemplatePlan, stage: str) -> Path:
    return REPO_ROOT / "reports" / f"{plan.target_name}_{_shape_tag(plan)}_{stage}.log"


def _command_text(command: list[str], *, sanitize: bool = False) -> str:
    rendered = " ".join(command)
    return sanitize_local_absolute_paths(rendered) if sanitize else rendered


def _log_text(text: str | None) -> str:
    return sanitize_local_absolute_paths(text) if text else ""


def _classified_failure_note(exc: subprocess.CalledProcessError) -> str:
    text = _log_text("\n".join(part for part in (exc.stderr, exc.output) if part))
    for line in text.splitlines():
        if any(key in line for key in ("gpu_runtime_unavailable", "CUDA error", "cuInit")):
            return "; classified_failure: gpu_runtime_unavailable: " + line.strip()
    return ""


def _stage_stdout_report(plan: HybridTemplatePlan, index: int) -> Path | None:
    return {3: plan.cpu_init_report, 4: plan.cpu_report, 6: plan.hybrid_report}.get(index)


def _stage_success_note(plan: HybridTemplatePlan, index: int, log_path: Path | None) -> str:
    parts = []
    if log_path is not None:
        parts.append(f"log: {_display_path(log_path)}")
    stdout_report = _stage_stdout_report(plan, index)
    if stdout_report is not None:
        parts.append(f"report: {_display_path(stdout_report)}")
    if not parts:
        return ""
    return " (" + ", ".join(parts) + ")"


def _stage_failure_note(plan: HybridTemplatePlan, index: int, stage: str) -> str:
    parts = [f"log: {_display_path(_stage_log_path(plan, stage))}"]
    stdout_report = _stage_stdout_report(plan, index)
    if stdout_report is not None:
        parts.append(f"report: {_display_path(stdout_report)}")
    return "; " + "; ".join(parts)


def _run_stage(
    *,
    plan: HybridTemplatePlan,
    index: int,
    stage: str,
    command: list[str],
    verbose: bool,
) -> Path | None:
    stdout_report = _stage_stdout_report(plan, index)
    if verbose:
        env = os.environ.copy()
        if stage == "hybrid_sidecar_run":
            env["RUN_VL_HYBRID_VERBOSE_SANITIZE"] = "1"
        if stdout_report is not None:
            stdout_report.parent.mkdir(parents=True, exist_ok=True)
            with stdout_report.open("w", encoding="utf-8") as out:
                subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=out, env=env)
        else:
            subprocess.run(command, cwd=REPO_ROOT, check=True, env=env)
        return None

    log_path = _stage_log_path(plan, stage)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + _command_text(command, sanitize=True) + "\n\n")
        log.flush()
        if stdout_report is not None:
            stdout_report.parent.mkdir(parents=True, exist_ok=True)
            with stdout_report.open("w", encoding="utf-8") as out:
                completed = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    check=False,
                    stdout=out,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            log.write(_log_text(completed.stderr))
        else:
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            log.write(_log_text(completed.stdout))
        if completed.returncode != 0:
            raise subprocess.CalledProcessError(completed.returncode, command, output=completed.stdout, stderr=completed.stderr)
    return log_path


def run_plan(
    plan: HybridTemplatePlan,
    *,
    dry_run: bool = False,
    verbose: bool = False,
    resident_patch_script: Path | None = None,
    resident_label: str = "resident_multistep",
) -> None:
    effective_plan = resident_template_plan(plan, resident_label=resident_label) if resident_patch_script else plan
    staged_commands = staged_command_plan(
        plan,
        resident_patch_script=resident_patch_script,
        resident_label=resident_label,
    )
    total = len(staged_commands)
    for index, (stage, command) in enumerate(staged_commands, start=1):
        if dry_run or verbose:
            print("+ " + _command_text(command))
        if dry_run:
            continue
        label = TEMPLATE_STAGE_LABELS[stage]
        if not verbose:
            print(f"[{index}/{total}] {label}: start", flush=True)
        try:
            log_path = _run_stage(plan=effective_plan, index=index, stage=stage, command=command, verbose=verbose)
        except FileNotFoundError as exc:
            raise HybridTemplateStageError(f"{label} failed: command not found: {command[0]}") from exc
        except subprocess.CalledProcessError as exc:
            failure_note = ""
            log_note = ""
            if not verbose:
                failure_note = _classified_failure_note(exc)
                log_note = _stage_failure_note(effective_plan, index, stage)
            raise HybridTemplateStageError(
                f"{label} failed with exit code {exc.returncode}{failure_note}{log_note}"
            ) from exc
        if not verbose:
            print(f"[{index}/{total}] {label}: ok{_stage_success_note(effective_plan, index, log_path)}", flush=True)
