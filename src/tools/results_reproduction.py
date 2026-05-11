#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ReproductionCommand:
    argv: list[str]
    stdout: Path | None = None


@dataclass(frozen=True)
class MedianWorkload:
    name: str
    target_name: str
    obj_dir: Path
    nstates: int
    steps: int
    source_gate: str
    coverage_target: str
    resident: bool = False
    report_tag: str | None = None


def _median_workload_stem(workload: MedianWorkload) -> str:
    return workload.report_tag or workload.name


DEFAULT_RESIDENT_SWEEP_STATES = (1, 8, 16, 32)
GPU_TOTAL_RE = re.compile(r"gpu_kernel_time_ms:\s+total=([0-9.]+)\s+per_launch=([0-9.]+)")
GPU_PER_STATE_RE = re.compile(r"gpu_kernel_time:\s+per_state=([0-9.]+)\s+us")
WALL_RE = re.compile(r"wall_time_ms:\s+([0-9.]+)")
LOCAL_ABSOLUTE_PATH_RE = re.compile(r"(?<!\S)/(?:home|tmp|Users|var|mnt|workspace|root)/\S+")
DEFAULT_HF_CACHE_DATASET_DIR = Path.home() / ".cache" / "huggingface" / "hub" / "datasets--ILSVRC--imagenet-1k"
PUBLIC_PACK_ARCHIVE_PATHS = (
    "README.md",
    "config/selection.json",
    "docs/status.md",
    "docs/roadmap.md",
    "docs/results.md",
    "records/scaling_gates/public_results_packaging_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json",
    "records/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json",
    "records/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json",
    "records/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_completion_gate.json",
    "records/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json",
    "records/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json",
    "records/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json",
    "records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json",
    "records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
    "records/scaling_gates/public_benchmark_pack_goal_completion_audit.json",
    "records/scaling_gates/generic_hybrid_benchmark_cli_gate.json",
    "records/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
    "records/scaling_gates/pulp_ita_mha_shape_expansion_gate.json",
    "records/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json",
    "src/tools/run_results_reproduction.py",
    "src/tools/results_reproduction.py",
    "src/tools/run_hybrid_benchmark.py",
    "src/tools/hybrid_benchmark.py",
    "src/tools/run_hybrid_template.py",
    "config/slice_launch_templates/pulp_ita_mha.json",
    "config/slice_launch_templates/pulp_paged_kv_cache_large.json",
    "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
    "config/slice_launch_templates/mobile_vit_cpu_kick_rtl_proxy.json",
    "tests/contract/test_full_ita_mha_larger_paged_kv_next.py",
    "tests/contract/test_hybrid_verilator_like_cli.py",
    "reports/results_reproduction_median_summary.json",
    "reports/persistent_resident_state_abi_probe_summary.json",
    "reports/persistent_resident_state_abi_repeat_median_summary.json",
    "reports/mobile_vit_hybrid_128_summary.json",
    "reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json",
    "reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
    "reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json",
    "reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json",
    "reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json",
    "reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json",
    "reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json",
    "reports/paged_attention_kv_cache_repeat_median_summary.json",
    "reports/paged_kv_repeat_pulp_paged_kv_cache_large_256x1_median.json",
    "reports/paged_kv_repeat_pulp_paged_kv_cache_large_1x64_median.json",
    "reports/paged_kv_repeat_pulp_paged_attention_kv_score_64x1_median.json",
    "reports/paged_kv_repeat_pulp_paged_attention_kv_score_1x64_median.json",
    "reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json",
    "reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json",
    "reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json",
    "reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json",
    "reports/hybrid_benchmark_mobile_vit_template_limit128.json",
)


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _mha_obj(path: str) -> Path:
    return REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir" / path


def _report(path: str) -> Path:
    return REPO_ROOT / "reports" / path


def _json_report(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _host_probe_repeat_command(*, nstates: int, steps: int, state_out: Path) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "artifacts/pulp_ita_mha_obj_dir/tlul_slice_host_probe",
            "--repeat-states",
            str(nstates),
            "--repeat-eval-steps",
            str(steps),
            "--set",
            "cfg_valid_i=1",
            "--set",
            "cfg_batch_length_i=64",
            "--set",
            "cfg_reset_cycles_i=2",
            "--set",
            "cfg_drain_cycles_i=8",
            "--set",
            "cfg_seed_i=1",
            "--repeat-state-out",
            _display_path(state_out),
        ],
        stdout=_report(f"pulp_ita_mha_cpu_repeat_{nstates}x{steps}.json"),
    )


def _resident_hybrid_command(*, nstates: int, steps: int, state_out: Path) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "python3",
            "src/tools/run_vl_hybrid.py",
            "--mdir",
            "artifacts/pulp_ita_mha_obj_dir",
            "--nstates",
            str(nstates),
            "--steps",
            str(steps),
            "--resident-steps",
            "--init-state",
            "artifacts/pulp_ita_mha_obj_dir/pulp_ita_mha_cpu_repeat_1x1.bin",
            "--sanitize-host-only-internals",
            "--dump-state",
            _display_path(state_out),
        ],
        stdout=_report(f"pulp_ita_mha_hybrid_{nstates}x{steps}_resident.txt"),
    )


def _resident_compare_command(*, nstates: int, steps: int, cpu_state: Path, gpu_state: Path) -> ReproductionCommand:
    shape = f"{nstates}x{steps}"
    return ReproductionCommand(
        [
            "python3",
            "src/tools/compare_vl_hybrid_modes.py",
            "artifacts/pulp_ita_mha_obj_dir",
            "--compare-dumps",
            _display_path(cpu_state),
            _display_path(gpu_state),
            "--reference-label",
            f"cpu_repeat_{shape}",
            "--candidate-label",
            f"hybrid_resident_from_cpu_init_{shape}",
            "--acceptance-policy",
            "coverage_output_equivalence",
            "--json-out",
            f"reports/pulp_ita_mha_cpu_vs_hybrid_{shape}_resident_coverage_output_compare.json",
            "--coverage-output-gate",
            "config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            "--coverage-output-target",
            "pulp_ita_mha",
        ]
    )


def reproduction_plan() -> list[ReproductionCommand]:
    commands = [
        ReproductionCommand(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_mha.json",
                "--shape",
                "64x1",
            ]
        ),
        ReproductionCommand(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_mha.json",
                "--shape",
                "1x64",
            ]
        ),
    ]
    for nstates in (1, 32):
        steps = 64
        cpu_state = _mha_obj(f"pulp_ita_mha_cpu_repeat_{nstates}x{steps}.bin")
        gpu_state = _mha_obj(f"pulp_ita_mha_gpu_from_cpu_init_{nstates}x{steps}_resident.bin")
        if nstates != 1:
            commands.append(_host_probe_repeat_command(nstates=nstates, steps=steps, state_out=cpu_state))
        commands.append(_resident_hybrid_command(nstates=nstates, steps=steps, state_out=gpu_state))
        commands.append(_resident_compare_command(nstates=nstates, steps=steps, cpu_state=cpu_state, gpu_state=gpu_state))
    commands.append(
        ReproductionCommand(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
                "--shape",
                "64x1",
            ]
        )
    )
    return commands


def format_command(command: ReproductionCommand) -> str:
    rendered = " ".join(command.argv)
    if command.stdout is not None:
        rendered = f"{rendered} > {_display_path(command.stdout)}"
    return LOCAL_ABSOLUTE_PATH_RE.sub("<local-absolute-path>", rendered)


def run_reproduction_plan(*, dry_run: bool) -> None:
    for command in reproduction_plan():
        print("+ " + format_command(command))
        if dry_run:
            continue
        if command.stdout is None:
            subprocess.run(command.argv, cwd=REPO_ROOT, check=True)
            continue
        command.stdout.parent.mkdir(parents=True, exist_ok=True)
        with command.stdout.open("w", encoding="utf-8") as out:
            subprocess.run(command.argv, cwd=REPO_ROOT, check=True, stdout=out)


def run_public_pack_archive_plan(*, dry_run: bool) -> None:
    if not dry_run:
        raise ValueError("public pack archive planning is dry-run only; do not create archive outputs as source of truth")
    print("# public_pack_archive_ready")
    print("# dry-run only: no archive is created")
    print("# include:")
    for path in PUBLIC_PACK_ARCHIVE_PATHS:
        print(f"include: {path}")
    print("# exclude:")
    print("exclude: artifacts/")
    print("exclude: reports/* except listed evidence snapshots")
    print("# archive command is intentionally not executed")
    print("tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>")


def mobile_vit_imagenet_128_plan() -> list[ReproductionCommand]:
    return [
        ReproductionCommand(
            [
                "artifacts/mobile_vit/venv/bin/python",
                "src/tools/mobile_vit_imagenet_manifest.py",
                "--hf-cache-dir",
                str(DEFAULT_HF_CACHE_DATASET_DIR),
                "--hf-output-dir",
                "artifacts/mobile_vit/apple_mobilevit_small/hf_imagenet_val_128",
                "--dataset-scope",
                "scoped_subset:imagenet_local_cache_128",
                "--output",
                "artifacts/mobile_vit/apple_mobilevit_small/imagenet_manifest_128.json",
                "--limit",
                "128",
            ]
        ),
        ReproductionCommand(
            [
                "env",
                "HF_HUB_OFFLINE=1",
                "TRANSFORMERS_OFFLINE=1",
                "artifacts/mobile_vit/venv/bin/python",
                "src/tools/mobile_vit_hybrid_imagenet_eval.py",
                "--manifest",
                "artifacts/mobile_vit/apple_mobilevit_small/imagenet_manifest_128.json",
                "--cpu-kick-predictions",
                "reports/mobile_vit_hybrid_128_cpu_kick_predictions.json",
                "--accuracy-report",
                "reports/mobile_vit_hybrid_128_accuracy.json",
                "--summary",
                "reports/mobile_vit_hybrid_128_summary.json",
                "--run-cpu-kick-infer",
                "--cpu-kick-batch-size",
                "16",
                "--hybrid-batch-size",
                "128",
            ]
        ),
    ]


def run_mobile_vit_imagenet_128_reproduction(*, dry_run: bool) -> None:
    for command in mobile_vit_imagenet_128_plan():
        _run_command(command, dry_run=dry_run)


def median_workloads() -> list[MedianWorkload]:
    return [
        MedianWorkload(
            name="pulp_ita_mha_64x1",
            target_name="pulp_ita_mha",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir",
            nstates=64,
            steps=1,
            source_gate="config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            coverage_target="pulp_ita_mha",
        ),
        MedianWorkload(
            name="pulp_ita_mha_1x64",
            target_name="pulp_ita_mha",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir",
            nstates=1,
            steps=64,
            source_gate="config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            coverage_target="pulp_ita_mha",
        ),
        MedianWorkload(
            name="pulp_ita_mha_1x64_resident",
            target_name="pulp_ita_mha",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir",
            nstates=1,
            steps=64,
            source_gate="config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            coverage_target="pulp_ita_mha",
            resident=True,
        ),
        MedianWorkload(
            name="pulp_ita_mha_32x64_resident",
            target_name="pulp_ita_mha",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir",
            nstates=32,
            steps=64,
            source_gate="config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            coverage_target="pulp_ita_mha",
            resident=True,
        ),
        MedianWorkload(
            name="pulp_paged_attention_kv_score_64x1",
            target_name="pulp_paged_attention_kv_score",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_paged_attention_kv_score_obj_dir",
            nstates=64,
            steps=1,
            source_gate="config/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json",
            coverage_target="pulp_paged_attention_kv_score",
        ),
    ]


def paged_attention_kv_cache_repeat_median_workloads() -> list[MedianWorkload]:
    return [
        MedianWorkload(
            name="pulp_paged_kv_cache_large_256x1",
            target_name="pulp_paged_kv_cache_large",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_paged_kv_cache_large_obj_dir",
            nstates=256,
            steps=1,
            source_gate="config/scaling_gates/neural_network_rtl_paged_kv_cache_large_scaleup_gate.json",
            coverage_target="pulp_paged_kv_cache_large",
            report_tag="paged_kv_repeat_pulp_paged_kv_cache_large_256x1",
        ),
        MedianWorkload(
            name="pulp_paged_kv_cache_large_1x64",
            target_name="pulp_paged_kv_cache_large",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_paged_kv_cache_large_obj_dir",
            nstates=1,
            steps=64,
            source_gate="config/scaling_gates/neural_network_rtl_paged_kv_cache_large_scaleup_gate.json",
            coverage_target="pulp_paged_kv_cache_large",
            report_tag="paged_kv_repeat_pulp_paged_kv_cache_large_1x64",
        ),
        MedianWorkload(
            name="pulp_paged_attention_kv_score_64x1",
            target_name="pulp_paged_attention_kv_score",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_paged_attention_kv_score_obj_dir",
            nstates=64,
            steps=1,
            source_gate="config/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json",
            coverage_target="pulp_paged_attention_kv_score",
            report_tag="paged_kv_repeat_pulp_paged_attention_kv_score_64x1",
        ),
        MedianWorkload(
            name="pulp_paged_attention_kv_score_1x64",
            target_name="pulp_paged_attention_kv_score",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_paged_attention_kv_score_obj_dir",
            nstates=1,
            steps=64,
            source_gate="config/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json",
            coverage_target="pulp_paged_attention_kv_score",
            report_tag="paged_kv_repeat_pulp_paged_attention_kv_score_1x64",
        ),
    ]


def _cpu_repeat_command(
    workload: MedianWorkload,
    *,
    state_out: Path,
    report: Path,
    nstates: int | None = None,
    steps: int | None = None,
) -> ReproductionCommand:
    return ReproductionCommand(
        [
            _display_path(workload.obj_dir / "tlul_slice_host_probe"),
            "--repeat-states",
            str(workload.nstates if nstates is None else nstates),
            "--repeat-eval-steps",
            str(workload.steps if steps is None else steps),
            "--set",
            "cfg_valid_i=1",
            "--set",
            "cfg_batch_length_i=64",
            "--set",
            "cfg_reset_cycles_i=2",
            "--set",
            "cfg_drain_cycles_i=8",
            "--set",
            "cfg_seed_i=1",
            "--repeat-state-out",
            _display_path(state_out),
        ],
        stdout=report,
    )


def _hybrid_command(workload: MedianWorkload, *, cpu_init_state: Path, gpu_state: Path, report: Path) -> ReproductionCommand:
    command = [
        "python3",
        "src/tools/run_vl_hybrid.py",
        "--mdir",
        _display_path(workload.obj_dir),
        "--nstates",
        str(workload.nstates),
        "--steps",
        str(workload.steps),
    ]
    if workload.resident:
        command.append("--resident-steps")
    command.extend(
        [
            "--init-state",
            _display_path(cpu_init_state),
            "--sanitize-host-only-internals",
            "--dump-state",
            _display_path(gpu_state),
        ]
    )
    return ReproductionCommand(command, stdout=report)


def _compare_command(workload: MedianWorkload, *, cpu_state: Path, gpu_state: Path, report: Path) -> ReproductionCommand:
    shape = f"{workload.nstates}x{workload.steps}"
    suffix = "_resident" if workload.resident else ""
    stdout = report.with_name(report.stem + "_stdout.txt")
    return ReproductionCommand(
        [
            "python3",
            "src/tools/compare_vl_hybrid_modes.py",
            _display_path(workload.obj_dir),
            "--compare-dumps",
            _display_path(cpu_state),
            _display_path(gpu_state),
            "--reference-label",
            f"cpu_repeat_{shape}",
            "--candidate-label",
            f"hybrid{suffix}_from_cpu_init_{shape}",
            "--acceptance-policy",
            "coverage_output_equivalence",
            "--json-out",
            _display_path(report),
            "--coverage-output-gate",
            workload.source_gate,
            "--coverage-output-target",
            workload.coverage_target,
        ],
        stdout=stdout,
    )


def _run_command(command: ReproductionCommand, *, dry_run: bool) -> None:
    print("+ " + format_command(command))
    if dry_run:
        return
    if command.stdout is None:
        subprocess.run(command.argv, cwd=REPO_ROOT, check=True)
        return
    command.stdout.parent.mkdir(parents=True, exist_ok=True)
    with command.stdout.open("w", encoding="utf-8") as out:
        subprocess.run(command.argv, cwd=REPO_ROOT, check=True, stdout=out)


def _parse_hybrid_report(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    total_match = GPU_TOTAL_RE.search(text)
    per_state_match = GPU_PER_STATE_RE.search(text)
    wall_match = WALL_RE.search(text)
    if total_match is None or per_state_match is None or wall_match is None:
        raise ValueError(f"failed to parse hybrid timing report: {_display_path(path)}")
    return {
        "gpu_kernel_total_ms": float(total_match.group(1)),
        "gpu_kernel_per_launch_ms": float(total_match.group(2)),
        "gpu_kernel_per_state_us": float(per_state_match.group(1)),
        "hybrid_wall_ms": float(wall_match.group(1)),
    }


def _summarize_numbers(values: list[float]) -> dict[str, object]:
    return {
        "samples": values,
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def _median_report_path(workload: MedianWorkload) -> Path:
    return _report(f"{_median_workload_stem(workload)}_median.json")


def _sample_paths(workload: MedianWorkload, sample_index: int) -> dict[str, Path]:
    shape = f"{workload.nstates}x{workload.steps}"
    suffix = "_resident" if workload.resident else ""
    if workload.report_tag is None:
        stem = f"{workload.target_name}_{shape}{suffix}_median_sample_{sample_index}"
    else:
        stem = f"{workload.report_tag}_median_sample_{sample_index}"
    return {
        "cpu_state": workload.obj_dir / f"{stem}_cpu.bin",
        "gpu_state": workload.obj_dir / f"{stem}_gpu.bin",
        "cpu_report": _report(f"{stem}_cpu.json"),
        "hybrid_report": _report(f"{stem}_hybrid.txt"),
        "compare_report": _report(f"{stem}_compare.json"),
        "compare_stdout_report": _report(f"{stem}_compare_stdout.txt"),
    }


def _init_state_paths(workload: MedianWorkload, *, tag: str) -> dict[str, Path]:
    stem = workload.report_tag or workload.target_name
    return {
        "state": workload.obj_dir / f"{stem}_cpu_repeat_1x1.bin",
        "report": _report(f"{stem}_{tag}_init_1x1_cpu.json"),
    }


def _run_init_state(workload: MedianWorkload, *, tag: str, dry_run: bool) -> Path:
    paths = _init_state_paths(workload, tag=tag)
    _run_command(
        _cpu_repeat_command(workload, state_out=paths["state"], report=paths["report"], nstates=1, steps=1),
        dry_run=dry_run,
    )
    return paths["state"]


def _run_workload_sample(
    workload: MedianWorkload,
    *,
    sample_index: int,
    cpu_init_state: Path,
    dry_run: bool,
) -> dict[str, object] | None:
    paths = _sample_paths(workload, sample_index)
    commands = [
        _cpu_repeat_command(workload, state_out=paths["cpu_state"], report=paths["cpu_report"]),
        _hybrid_command(workload, cpu_init_state=cpu_init_state, gpu_state=paths["gpu_state"], report=paths["hybrid_report"]),
        _compare_command(workload, cpu_state=paths["cpu_state"], gpu_state=paths["gpu_state"], report=paths["compare_report"]),
    ]
    for command in commands:
        _run_command(command, dry_run=dry_run)
    if dry_run:
        return None

    cpu = _json_report(paths["cpu_report"])
    compare = _json_report(paths["compare_report"])
    coverage = compare["coverage_output_policy"]
    hybrid = _parse_hybrid_report(paths["hybrid_report"])
    state_step_count = workload.nstates * workload.steps
    sample = {
        "sample_index": sample_index,
        "state_step_count": state_step_count,
        "cpu_elapsed_ms": cpu["elapsed_ms"],
        "cpu_state_steps_per_second": cpu.get("state_steps_per_second"),
        **hybrid,
        "gpu_kernel_total_ms_per_state_step": hybrid["gpu_kernel_total_ms"] / state_step_count,
        "hybrid_wall_ms_per_state_step": hybrid["hybrid_wall_ms"] / state_step_count,
        "coverage_output_passed": coverage["passed"],
        "coverage_output_mismatch_count": coverage["mismatch_count"],
        "compared_state_pair_count": coverage["compared_state_pair_count"],
        "reports": {key: _display_path(value) for key, value in paths.items() if key.endswith("_report")},
    }
    return sample


def _run_median_workload_set(
    *,
    repeat_count: int,
    dry_run: bool,
    workloads: list[MedianWorkload],
    aggregate_status: str,
    aggregate_report: str,
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for workload in workloads:
        cpu_init_state = _run_init_state(workload, tag="median", dry_run=dry_run)
        samples = []
        for sample_index in range(1, repeat_count + 1):
            sample = _run_workload_sample(
                workload,
                sample_index=sample_index,
                cpu_init_state=cpu_init_state,
                dry_run=dry_run,
            )
            if sample is not None:
                samples.append(sample)
        if dry_run:
            continue
        summary = {
            "schema_version": 1,
            "workload": workload.name,
            "target": workload.target_name,
            "shape": f"{workload.nstates}x{workload.steps}",
            "resident_mode": workload.resident,
            "source_gate": workload.source_gate,
            "repeat_count": repeat_count,
            "acceptance_policy": "coverage_output_equivalence",
            "all_coverage_output_passed": all(sample["coverage_output_passed"] for sample in samples),
            "max_coverage_output_mismatch_count": max(sample["coverage_output_mismatch_count"] for sample in samples),
            "metrics": {
                "cpu_elapsed_ms": _summarize_numbers([float(sample["cpu_elapsed_ms"]) for sample in samples]),
                "gpu_kernel_total_ms": _summarize_numbers(
                    [float(sample["gpu_kernel_total_ms"]) for sample in samples]
                ),
                "hybrid_wall_ms": _summarize_numbers([float(sample["hybrid_wall_ms"]) for sample in samples]),
                "gpu_kernel_total_ms_per_state_step": _summarize_numbers(
                    [float(sample["gpu_kernel_total_ms_per_state_step"]) for sample in samples]
                ),
                "hybrid_wall_ms_per_state_step": _summarize_numbers(
                    [float(sample["hybrid_wall_ms_per_state_step"]) for sample in samples]
                ),
            },
            "source_reports": {
                "cpu": [sample["reports"]["cpu_report"] for sample in samples],
                "hybrid": [sample["reports"]["hybrid_report"] for sample in samples],
                "compare": [sample["reports"]["compare_report"] for sample in samples],
                "compare_stdout": [sample["reports"]["compare_stdout_report"] for sample in samples],
            },
            "samples": samples,
        }
        path = _median_report_path(workload)
        path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        summaries.append({**summary, "report": _display_path(path)})
    if dry_run:
        print(f"+ write {_display_path(_report(aggregate_report))}")
    else:
        aggregate = {
            "schema_version": 1,
            "status": aggregate_status,
            "repeat_count": repeat_count,
            "reports": [entry["report"] for entry in summaries],
            "workloads": summaries,
        }
        _report(aggregate_report).write_text(
            json.dumps(aggregate, indent=2) + "\n",
            encoding="utf-8",
        )
    return summaries


def run_median_measurements(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    if repeat_count <= 0:
        raise ValueError("--repeat-median must be positive")
    return _run_median_workload_set(
        repeat_count=repeat_count,
        dry_run=dry_run,
        workloads=median_workloads(),
        aggregate_status="measured_representative_repeat_median",
        aggregate_report="results_reproduction_median_summary.json",
    )


def run_paged_attention_kv_cache_repeat_median(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    if repeat_count <= 0:
        raise ValueError("--paged-kv-repeat-median must be positive")
    return _run_median_workload_set(
        repeat_count=repeat_count,
        dry_run=dry_run,
        workloads=paged_attention_kv_cache_repeat_median_workloads(),
        aggregate_status="measured_paged_attention_kv_cache_repeat_median",
        aggregate_report="paged_attention_kv_cache_repeat_median_summary.json",
    )


def resident_batch_sweep_workloads(batch_states: list[int]) -> list[MedianWorkload]:
    return [
        MedianWorkload(
            name=f"pulp_ita_mha_{nstates}x64_resident_batch_sweep",
            target_name="pulp_ita_mha",
            obj_dir=REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir",
            nstates=nstates,
            steps=64,
            source_gate="config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            coverage_target="pulp_ita_mha",
            resident=True,
        )
        for nstates in batch_states
    ]


def parse_resident_batch_states(text: str) -> list[int]:
    values = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if value <= 0:
            raise ValueError("--resident-batch-sweep values must be positive")
        values.append(value)
    if not values:
        raise ValueError("--resident-batch-sweep requires at least one positive state count")
    return values


def parse_shape(text: str) -> tuple[int, int]:
    parts = text.lower().split("x")
    if len(parts) != 2:
        raise ValueError("shape must be formatted as NSTATESxSTEPS, for example 16x64")
    try:
        nstates = int(parts[0])
        steps = int(parts[1])
    except ValueError as exc:
        raise ValueError("shape must contain positive integer NSTATES and STEPS") from exc
    if nstates <= 0 or steps <= 0:
        raise ValueError("shape must contain positive integer NSTATES and STEPS")
    return nstates, steps


def run_resident_batch_sweep(*, repeat_count: int, batch_states: list[int], dry_run: bool) -> list[dict[str, object]]:
    if repeat_count <= 0:
        raise ValueError("--resident-batch-sweep-repeat must be positive")
    summaries: list[dict[str, object]] = []
    for workload in resident_batch_sweep_workloads(batch_states):
        cpu_init_state = _run_init_state(workload, tag="resident_batch_sweep", dry_run=dry_run)
        samples = []
        for sample_index in range(1, repeat_count + 1):
            sample = _run_workload_sample(
                workload,
                sample_index=sample_index,
                cpu_init_state=cpu_init_state,
                dry_run=dry_run,
            )
            if sample is not None:
                samples.append(sample)
        if dry_run:
            continue
        summary = {
            "schema_version": 1,
            "workload": workload.name,
            "target": workload.target_name,
            "shape": f"{workload.nstates}x{workload.steps}",
            "resident_mode": True,
            "source_gate": workload.source_gate,
            "repeat_count": repeat_count,
            "acceptance_policy": "coverage_output_equivalence",
            "all_coverage_output_passed": all(sample["coverage_output_passed"] for sample in samples),
            "max_coverage_output_mismatch_count": max(sample["coverage_output_mismatch_count"] for sample in samples),
            "metrics": {
                "cpu_elapsed_ms": _summarize_numbers([float(sample["cpu_elapsed_ms"]) for sample in samples]),
                "gpu_kernel_total_ms": _summarize_numbers(
                    [float(sample["gpu_kernel_total_ms"]) for sample in samples]
                ),
                "hybrid_wall_ms": _summarize_numbers([float(sample["hybrid_wall_ms"]) for sample in samples]),
                "gpu_kernel_total_ms_per_state_step": _summarize_numbers(
                    [float(sample["gpu_kernel_total_ms_per_state_step"]) for sample in samples]
                ),
                "hybrid_wall_ms_per_state_step": _summarize_numbers(
                    [float(sample["hybrid_wall_ms_per_state_step"]) for sample in samples]
                ),
            },
            "source_reports": {
                "cpu": [sample["reports"]["cpu_report"] for sample in samples],
                "hybrid": [sample["reports"]["hybrid_report"] for sample in samples],
                "compare": [sample["reports"]["compare_report"] for sample in samples],
                "compare_stdout": [sample["reports"]["compare_stdout_report"] for sample in samples],
            },
            "samples": samples,
        }
        path = _report(f"{workload.name}.json")
        path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        summaries.append({**summary, "report": _display_path(path)})
    if not dry_run:
        aggregate = {
            "schema_version": 1,
            "status": "measured_resident_batch_sweep",
            "repeat_count": repeat_count,
            "batch_states": batch_states,
            "reports": [entry["report"] for entry in summaries],
            "workloads": summaries,
        }
        _report("resident_batch_sweep_summary.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    return summaries


def _resident_state_reuse_paths(*, nstates: int, steps: int, phase: int) -> dict[str, Path]:
    cumulative_steps = steps * phase
    stem = f"pulp_ita_mha_{nstates}x{steps}_resident_state_reuse_phase_{phase}"
    return {
        "cpu_state": _mha_obj(f"{stem}_cpu_{nstates}x{cumulative_steps}.bin"),
        "gpu_state": _mha_obj(f"{stem}_gpu_{nstates}x{cumulative_steps}.bin"),
        "cpu_report": _report(f"{stem}_cpu_{nstates}x{cumulative_steps}.json"),
        "hybrid_report": _report(f"{stem}_hybrid_{nstates}x{cumulative_steps}.txt"),
        "compare_report": _report(f"{stem}_compare_{nstates}x{cumulative_steps}.json"),
    }


def _mha_reuse_workload(*, nstates: int, steps: int) -> MedianWorkload:
    return MedianWorkload(
        name=f"pulp_ita_mha_{nstates}x{steps}_resident_state_reuse",
        target_name="pulp_ita_mha",
        obj_dir=REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir",
        nstates=nstates,
        steps=steps,
        source_gate="config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
        coverage_target="pulp_ita_mha",
        resident=True,
    )


def _resident_state_reuse_compare_command(
    workload: MedianWorkload,
    *,
    phase: int,
    cumulative_steps: int,
    cpu_state: Path,
    gpu_state: Path,
    report: Path,
) -> ReproductionCommand:
    stdout = report.with_name(report.stem + "_stdout.txt")
    return ReproductionCommand(
        [
            "python3",
            "src/tools/compare_vl_hybrid_modes.py",
            _display_path(workload.obj_dir),
            "--compare-dumps",
            _display_path(cpu_state),
            _display_path(gpu_state),
            "--reference-label",
            f"cpu_repeat_{workload.nstates}x{cumulative_steps}",
            "--candidate-label",
            f"hybrid_resident_state_reuse_phase_{phase}_{workload.nstates}x{cumulative_steps}",
            "--acceptance-policy",
            "coverage_output_equivalence",
            "--json-out",
            _display_path(report),
            "--coverage-output-gate",
            workload.source_gate,
            "--coverage-output-target",
            workload.coverage_target,
        ],
        stdout=stdout,
    )


def run_resident_state_reuse_experiment(
    *,
    nstates: int,
    steps: int,
    phases: int,
    dry_run: bool,
) -> dict[str, object] | None:
    if phases <= 0:
        raise ValueError("--resident-state-reuse-phases must be positive")
    workload = _mha_reuse_workload(nstates=nstates, steps=steps)
    init_state = _run_init_state(workload, tag="resident_state_reuse", dry_run=dry_run)
    phase_summaries: list[dict[str, object]] = []
    previous_gpu_state = init_state
    for phase in range(1, phases + 1):
        cumulative_steps = steps * phase
        paths = _resident_state_reuse_paths(nstates=nstates, steps=steps, phase=phase)
        phase_cpu_command = _cpu_repeat_command(
            workload,
            state_out=paths["cpu_state"],
            report=paths["cpu_report"],
            nstates=nstates,
            steps=cumulative_steps,
        )
        phase_hybrid_command = _hybrid_command(
            workload,
            cpu_init_state=previous_gpu_state,
            gpu_state=paths["gpu_state"],
            report=paths["hybrid_report"],
        )
        phase_compare_command = _resident_state_reuse_compare_command(
            workload,
            phase=phase,
            cumulative_steps=cumulative_steps,
            cpu_state=paths["cpu_state"],
            gpu_state=paths["gpu_state"],
            report=paths["compare_report"],
        )
        for command in (phase_cpu_command, phase_hybrid_command, phase_compare_command):
            _run_command(command, dry_run=dry_run)
        previous_gpu_state = paths["gpu_state"]
        if dry_run:
            continue

        cpu = _json_report(paths["cpu_report"])
        compare = _json_report(paths["compare_report"])
        coverage = compare["coverage_output_policy"]
        hybrid = _parse_hybrid_report(paths["hybrid_report"])
        state_step_count = nstates * cumulative_steps
        phase_summaries.append(
            {
                "phase": phase,
                "shape": f"{nstates}x{cumulative_steps}",
                "phase_step_count": steps,
                "cumulative_step_count": cumulative_steps,
                "state_step_count": state_step_count,
                "cpu_elapsed_ms": cpu["elapsed_ms"],
                **hybrid,
                "gpu_kernel_total_ms_per_state_step": hybrid["gpu_kernel_total_ms"] / state_step_count,
                "hybrid_wall_ms_per_state_step": hybrid["hybrid_wall_ms"] / state_step_count,
                "coverage_output_passed": coverage["passed"],
                "coverage_output_mismatch_count": coverage["mismatch_count"],
                "reports": {
                    "cpu_report": _display_path(paths["cpu_report"]),
                    "hybrid_report": _display_path(paths["hybrid_report"]),
                    "compare_report": _display_path(paths["compare_report"]),
                    "compare_stdout_report": _display_path(
                        paths["compare_report"].with_name(paths["compare_report"].stem + "_stdout.txt")
                    ),
                },
            }
        )
    if dry_run:
        return None

    summary = {
        "schema_version": 1,
        "status": "measured_resident_state_reuse_experiment",
        "target": workload.target_name,
        "shape": f"{nstates}x{steps}",
        "phases": phases,
        "acceptance_policy": "coverage_output_equivalence",
        "all_coverage_output_passed": all(phase["coverage_output_passed"] for phase in phase_summaries),
        "max_coverage_output_mismatch_count": max(
            phase["coverage_output_mismatch_count"] for phase in phase_summaries
        ),
        "phase_reports": phase_summaries,
    }
    _report("resident_state_reuse_experiment_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def _persistent_resident_state_abi_paths(
    *,
    nstates: int,
    steps: int,
    phase: int,
    sample_tag: str | None = None,
) -> dict[str, Path]:
    cumulative_steps = steps * phase
    tag = f"_{sample_tag}" if sample_tag else ""
    stem = f"pulp_ita_mha_{nstates}x{steps}_persistent_resident_state_abi{tag}_phase_{phase}"
    return {
        "cpu_state": _mha_obj(f"{stem}_cpu_{nstates}x{cumulative_steps}.bin"),
        "gpu_state": _mha_obj(f"{stem}_gpu_dump_{nstates}x{cumulative_steps}.bin"),
        "cpu_report": _report(f"{stem}_cpu_{nstates}x{cumulative_steps}.json"),
        "hybrid_report": _report(f"{stem}_hybrid_{nstates}x{cumulative_steps}.txt"),
        "compare_report": _report(f"{stem}_compare_{nstates}x{cumulative_steps}.json"),
    }


def _persistent_resident_state_abi_phase_command(
    workload: MedianWorkload,
    *,
    phase: int,
    cpu_init_state: Path,
    gpu_state: Path,
    report: Path,
) -> ReproductionCommand:
    command = [
        "python3",
        "src/tools/run_vl_hybrid.py",
        "--mdir",
        _display_path(workload.obj_dir),
        "--nstates",
        str(workload.nstates),
        "--steps",
        str(workload.steps),
        "--resident-steps",
        "--persistent-resident-state-abi-handle",
        f"pulp_ita_mha_{workload.nstates}x{workload.steps}",
        "--persistent-resident-state-abi-phase",
        str(phase),
    ]
    if phase == 1:
        command.extend(
            [
                "--init-state",
                _display_path(cpu_init_state),
                "--sanitize-host-only-internals",
            ]
        )
    command.extend(
        [
            "--dump-state",
            _display_path(gpu_state),
        ]
    )
    return ReproductionCommand(command, stdout=report)


def _persistent_resident_state_abi_multiphase_command(
    workload: MedianWorkload,
    *,
    phases: int,
    cpu_init_state: Path,
    gpu_states: list[Path],
    report: Path,
) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "python3",
            "src/tools/run_vl_hybrid.py",
            "--mdir",
            _display_path(workload.obj_dir),
            "--nstates",
            str(workload.nstates),
            "--steps",
            str(workload.steps),
            "--resident-steps",
            "--persistent-resident-state-abi-handle",
            f"pulp_ita_mha_{workload.nstates}x{workload.steps}",
            "--persistent-resident-state-abi-phase",
            "1",
            "--persistent-resident-state-abi-phases",
            str(phases),
            "--persistent-resident-state-abi-phase-dumps",
            ",".join(_display_path(path) for path in gpu_states),
            "--init-state",
            _display_path(cpu_init_state),
            "--sanitize-host-only-internals",
        ],
        stdout=report,
    )


def run_persistent_resident_state_abi_probe(
    *,
    nstates: int,
    steps: int,
    phases: int,
    dry_run: bool,
    sample_tag: str | None = None,
    summary_report: Path | None = None,
) -> None:
    if phases <= 0:
        raise ValueError("--persistent-resident-state-abi-phases must be positive")

    workload = _mha_reuse_workload(nstates=nstates, steps=steps)
    init_tag = "persistent_resident_state_abi" + (f"_{sample_tag}" if sample_tag else "")
    init_state = _run_init_state(workload, tag=init_tag, dry_run=dry_run)
    phase_paths = [
        _persistent_resident_state_abi_paths(
            nstates=nstates,
            steps=steps,
            phase=phase,
            sample_tag=sample_tag,
        )
        for phase in range(1, phases + 1)
    ]
    phase_summaries: list[dict[str, object]] = []
    for phase in range(1, phases + 1):
        cumulative_steps = steps * phase
        paths = phase_paths[phase - 1]
        phase_cpu_command = _cpu_repeat_command(
            workload,
            state_out=paths["cpu_state"],
            report=paths["cpu_report"],
            nstates=nstates,
            steps=cumulative_steps,
        )
        _run_command(phase_cpu_command, dry_run=dry_run)

    tag = f"_{sample_tag}" if sample_tag else ""
    hybrid_report = _report(f"pulp_ita_mha_{nstates}x{steps}_persistent_resident_state_abi{tag}_multiphase_hybrid.txt")
    hybrid_command = _persistent_resident_state_abi_multiphase_command(
        workload,
        phases=phases,
        cpu_init_state=init_state,
        gpu_states=[paths["gpu_state"] for paths in phase_paths],
        report=hybrid_report,
    )
    _run_command(hybrid_command, dry_run=dry_run)

    for phase in range(1, phases + 1):
        cumulative_steps = steps * phase
        paths = phase_paths[phase - 1]
        phase_compare_command = _resident_state_reuse_compare_command(
            workload,
            phase=phase,
            cumulative_steps=cumulative_steps,
            cpu_state=paths["cpu_state"],
            gpu_state=paths["gpu_state"],
            report=paths["compare_report"],
        )
        _run_command(phase_compare_command, dry_run=dry_run)
        if dry_run:
            continue

        cpu = _json_report(paths["cpu_report"])
        compare = _json_report(paths["compare_report"])
        coverage = compare["coverage_output_policy"]
        state_step_count = nstates * cumulative_steps
        phase_summaries.append(
            {
                "phase": phase,
                "shape": f"{nstates}x{cumulative_steps}",
                "phase_step_count": steps,
                "cumulative_step_count": cumulative_steps,
                "state_step_count": state_step_count,
                "cpu_elapsed_ms": cpu["elapsed_ms"],
                "coverage_output_passed": coverage["passed"],
                "coverage_output_mismatch_count": coverage["mismatch_count"],
                "reports": {
                    "cpu_report": _display_path(paths["cpu_report"]),
                    "hybrid_report": _display_path(hybrid_report),
                    "compare_report": _display_path(paths["compare_report"]),
                    "compare_stdout_report": _display_path(
                        paths["compare_report"].with_name(paths["compare_report"].stem + "_stdout.txt")
                    ),
                },
            }
        )
    if dry_run:
        print(f"+ write {_display_path(summary_report or _report('persistent_resident_state_abi_probe_summary.json'))}")
        return

    summary = {
        "schema_version": 1,
        "status": "measured_persistent_resident_state_abi_probe",
        "target": workload.target_name,
        "shape": f"{nstates}x{steps}",
        "phases": phases,
        "acceptance_policy": "coverage_output_equivalence",
        "state_authority": "in_process_gpu_d_storage_after_phase_1",
        "all_coverage_output_passed": all(phase["coverage_output_passed"] for phase in phase_summaries),
        "max_coverage_output_mismatch_count": max(
            phase["coverage_output_mismatch_count"] for phase in phase_summaries
        ),
        "hybrid_report": _display_path(hybrid_report),
        "phase_reports": phase_summaries,
    }
    (summary_report or _report("persistent_resident_state_abi_probe_summary.json")).write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


def run_persistent_resident_state_abi_repeat_median(
    *,
    nstates: int,
    steps: int,
    phases: int,
    repeat_count: int,
    dry_run: bool,
) -> None:
    if repeat_count <= 0:
        raise ValueError("--persistent-resident-state-abi-repeat-median must be positive")
    if phases <= 0:
        raise ValueError("--persistent-resident-state-abi-phases must be positive")

    samples: list[dict[str, object]] = []
    for sample_index in range(1, repeat_count + 1):
        if dry_run:
            print(f"# persistent_resident_state_abi_repeat_median sample {sample_index}/{repeat_count}")
        run_persistent_resident_state_abi_probe(
            nstates=nstates,
            steps=steps,
            phases=phases,
            dry_run=dry_run,
            sample_tag=f"repeat_median_sample_{sample_index}",
            summary_report=_report(f"persistent_resident_state_abi_repeat_median_sample_{sample_index}.json"),
        )
        if dry_run:
            continue

        base_summary_path = _report(f"persistent_resident_state_abi_repeat_median_sample_{sample_index}.json")
        base_summary = _json_report(base_summary_path)
        hybrid_report = REPO_ROOT / str(base_summary["hybrid_report"])
        hybrid = _parse_hybrid_report(hybrid_report)
        final_state_step_count = nstates * steps * phases
        sample = {
            "sample_index": sample_index,
            "state_authority": base_summary["state_authority"],
            "phase_shapes": [phase["shape"] for phase in base_summary["phase_reports"]],
            "all_coverage_output_passed": base_summary["all_coverage_output_passed"],
            "max_coverage_output_mismatch_count": base_summary["max_coverage_output_mismatch_count"],
            "final_state_step_count": final_state_step_count,
            **hybrid,
            "gpu_kernel_total_ms_per_final_state_step": hybrid["gpu_kernel_total_ms"] / final_state_step_count,
            "hybrid_wall_ms_per_final_state_step": hybrid["hybrid_wall_ms"] / final_state_step_count,
            "source_summary_report": _display_path(base_summary_path),
            "hybrid_report": base_summary["hybrid_report"],
        }
        base_summary["repeat_median_sample"] = sample
        base_summary_path.write_text(json.dumps(base_summary, indent=2) + "\n", encoding="utf-8")
        samples.append({**sample, "sample_report": _display_path(base_summary_path)})

    if dry_run:
        print("+ write reports/persistent_resident_state_abi_repeat_median_summary.json")
        return

    summary = {
        "schema_version": 1,
        "status": "measured_persistent_resident_state_abi_repeat_median",
        "target": "pulp_ita_mha",
        "shape": f"{nstates}x{steps}",
        "phases": phases,
        "repeat_count": repeat_count,
        "acceptance_policy": "coverage_output_equivalence",
        "source_gate": "config/scaling_gates/persistent_resident_device_handle_storage_gate.json",
        "state_authority": "in_process_gpu_d_storage_after_phase_1",
        "all_coverage_output_passed": all(sample["all_coverage_output_passed"] for sample in samples),
        "max_coverage_output_mismatch_count": max(
            int(sample["max_coverage_output_mismatch_count"]) for sample in samples
        ),
        "metrics": {
            "gpu_kernel_total_ms": _summarize_numbers([float(sample["gpu_kernel_total_ms"]) for sample in samples]),
            "hybrid_wall_ms": _summarize_numbers([float(sample["hybrid_wall_ms"]) for sample in samples]),
            "gpu_kernel_total_ms_per_final_state_step": _summarize_numbers(
                [float(sample["gpu_kernel_total_ms_per_final_state_step"]) for sample in samples]
            ),
            "hybrid_wall_ms_per_final_state_step": _summarize_numbers(
                [float(sample["hybrid_wall_ms_per_final_state_step"]) for sample in samples]
            ),
        },
        "sample_reports": [sample["sample_report"] for sample in samples],
        "samples": samples,
        "non_claims": [
            "not a new workload",
            "not a runtime or ABI change",
            "not production LLM serving throughput",
            "not paper-grade statistical confidence beyond the selected repeat count",
            "not raw full-state equality",
        ],
    }
    _report("persistent_resident_state_abi_repeat_median_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
