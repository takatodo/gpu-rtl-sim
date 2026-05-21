from __future__ import annotations

from hybrid_benchmark_specs import (
    BENCHMARKS,
    CORRECTNESS_POLICY_COVERAGE_OUTPUT,
    KIND_MOBILE_VIT_IMAGENET,
    KIND_SLICE_TEMPLATE,
    MODE_PERSISTENT_RESIDENT_STATE_ABI,
    MODE_RESIDENT_STATE_REUSE,
    MODE_TEMPLATE,
    SIDECAR_ACCEL,
    STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_READY_FOR_TEMPLATE_SHAPE,
    BenchmarkSpec,
)
from hybrid_benchmark_paths import (
    default_summary_path,
    display_path,
    format_report_command,
    repo_path,
    sanitize_local_absolute_paths,
    shape_tag,
)
from results_reproduction import (
    ReproductionCommand,
    mobile_vit_imagenet_128_plan,
)


def _template_command(*, template: str, shape: str) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "python3",
            "src/tools/run_hybrid_template.py",
            template,
            "--shape",
            shape,
        ]
    )


def _resident_state_reuse_command(*, shape: str, phases: int) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "python3",
            "src/tools/run_results_reproduction.py",
            "--resident-state-reuse",
            shape,
            "--resident-state-reuse-phases",
            str(phases),
        ]
    )


def _persistent_resident_state_abi_command(*, shape: str, phases: int) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "python3",
            "src/tools/run_results_reproduction.py",
            "--persistent-resident-state-abi",
            shape,
            "--persistent-resident-state-abi-phases",
            str(phases),
        ]
    )


def benchmark_plan(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> list[ReproductionCommand]:
    try:
        spec = BENCHMARKS[target]
    except KeyError as exc:
        supported = ", ".join(sorted(BENCHMARKS))
        raise ValueError(f"unsupported benchmark target: {target}; supported: {supported}") from exc

    if phases <= 0:
        raise ValueError("--phases must be positive")

    if mode not in spec.modes:
        raise ValueError(f"{target} does not support --mode {mode}")

    if spec.kind == KIND_SLICE_TEMPLATE:
        if shape is None:
            raise ValueError(f"{target} requires --shape")
        if limit is not None:
            raise ValueError(f"{target} does not accept --limit")
        if mode == MODE_RESIDENT_STATE_REUSE:
            return [_resident_state_reuse_command(shape=shape, phases=phases)]
        if mode == MODE_PERSISTENT_RESIDENT_STATE_ABI:
            return [_persistent_resident_state_abi_command(shape=shape, phases=phases)]
        assert spec.template is not None
        return [_template_command(template=spec.template, shape=shape)]

    if spec.kind == KIND_MOBILE_VIT_IMAGENET:
        if shape is not None:
            raise ValueError("mobile_vit does not accept --shape")
        if limit != 128:
            raise ValueError("mobile_vit currently supports --limit 128 only")
        return mobile_vit_imagenet_128_plan()

    raise ValueError(f"unsupported benchmark kind: {spec.kind}")


def target_list_report() -> dict[str, object]:
    targets = []
    for name in sorted(BENCHMARKS):
        spec = BENCHMARKS[name]
        entry: dict[str, object] = {
            "name": name,
            "canonical_target": spec.target,
            "kind": spec.kind,
            "requires": list(spec.requires),
            "modes": list(spec.modes),
        }
        if spec.kind == KIND_SLICE_TEMPLATE:
            entry["template"] = spec.template
            entry["sidecar_gpu"] = {
                "sim_accel": SIDECAR_ACCEL,
                "option_shim_status": STATUS_READY_FOR_TEMPLATE_SHAPE,
                "requires": ["--sim-accel-states", "--sim-accel-steps"],
                "ready_modes": [MODE_TEMPLATE],
                "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
                "non_claims": [
                    "readiness is a discovery hint, not execution evidence",
                    "readiness does not mean Verilator itself implements --sim-accel",
                ],
            }
        else:
            entry["sidecar_gpu"] = {
                "sim_accel": SIDECAR_ACCEL,
                "option_shim_status": STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
                "reason": "dataset-backed targets expose host preprocessing as a stage but are not ready for a direct Verilator option",
                "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
                "non_claims": [
                    "not-ready status is not a correctness or timing result",
                    "coverage-output equivalence remains separate from performance estimates",
                ],
            }
        targets.append(entry)
    return {
        "schema_version": 1,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "targets": targets,
    }
