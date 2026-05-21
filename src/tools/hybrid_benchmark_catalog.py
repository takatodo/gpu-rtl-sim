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
    STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
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
from hybrid_template_types import parse_shape
from results_reproduction import (
    ReproductionCommand,
    mobile_vit_imagenet_128_plan,
)

OPERATOR_PLAN_EXAMPLE_SHAPE = "64x1"
OPERATOR_PLAN_EXAMPLE_TARGET = "paged_attention_kv_score"
SIDECAR_RECOMMENDED_ENTRYPOINT = "--sim-accel-shape <NxS>"
SIDECAR_COMPATIBILITY_ENTRYPOINT = (
    f"--sim-accel {SIDECAR_ACCEL} --sim-accel-states <N> --sim-accel-steps <S>"
)


def operator_plan_command(*, target: str, shape: str) -> str:
    return (
        f"python3 src/tools/run_hybrid_benchmark.py {target} "
        f"--sim-accel-shape {shape} --print-operator-plan"
    )


def verilator_estimate_command(*, target: str, shape: str) -> str:
    return (
        f"python3 src/tools/run_hybrid_benchmark.py {target} "
        f"--sim-accel-shape {shape} --print-verilator-estimate-command"
    )


def operator_plan_json_command(*, target: str, shape: str) -> str:
    return (
        f"python3 src/tools/run_hybrid_benchmark.py {target} "
        f"--sim-accel-shape {shape} --operator-plan-json"
    )


def compatibility_entrypoint_for_shape(shape: str | None) -> str | None:
    if shape is None:
        return None
    nstates, steps = parse_shape(shape)
    return f"--sim-accel {SIDECAR_ACCEL} --sim-accel-states {nstates} --sim-accel-steps {steps}"


def shortest_operator_path() -> list[str]:
    return [
        "python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu",
        operator_plan_command(target=OPERATOR_PLAN_EXAMPLE_TARGET, shape=OPERATOR_PLAN_EXAMPLE_SHAPE),
        operator_plan_json_command(target=OPERATOR_PLAN_EXAMPLE_TARGET, shape=OPERATOR_PLAN_EXAMPLE_SHAPE),
    ]


def operator_discovery_hint(*, target: str, requested_shape: str | None) -> dict[str, object]:
    return {
        "source": "src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu",
        "requested_shape": requested_shape,
        "recommended_shape": OPERATOR_PLAN_EXAMPLE_SHAPE,
        "recommended_shape_matches_request": requested_shape == OPERATOR_PLAN_EXAMPLE_SHAPE,
        "recommended_entrypoint": SIDECAR_RECOMMENDED_ENTRYPOINT,
        "compatibility_entrypoint": SIDECAR_COMPATIBILITY_ENTRYPOINT,
        "requested_compatibility_entrypoint": compatibility_entrypoint_for_shape(requested_shape),
        "operator_plan_example_command": operator_plan_command(
            target=target,
            shape=OPERATOR_PLAN_EXAMPLE_SHAPE,
        ),
        "verilator_estimate_command_example_command": verilator_estimate_command(
            target=target,
            shape=OPERATOR_PLAN_EXAMPLE_SHAPE,
        ),
        "operator_plan_json_example_command": operator_plan_json_command(
            target=target,
            shape=OPERATOR_PLAN_EXAMPLE_SHAPE,
        ),
        "non_claims": [
            "recommended shape is an operator starting point, not timing evidence",
            "example command is non-executing unless the operator runs it explicitly",
        ],
    }


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
                "recommended_entrypoint": SIDECAR_RECOMMENDED_ENTRYPOINT,
                "compatibility_entrypoint": SIDECAR_COMPATIBILITY_ENTRYPOINT,
                "shape_spellings": [
                    "--sim-accel-states <N> --sim-accel-steps <S>",
                    "--sim-accel-shape <NxS>",
                    "--shape <NxS>",
                ],
                "operator_plan_command_template": (
                    operator_plan_command(target=name, shape="<NxS>")
                ),
                "verilator_estimate_command_template": (
                    verilator_estimate_command(target=name, shape="<NxS>")
                ),
                "operator_plan_json_command_template": (
                    operator_plan_json_command(target=name, shape="<NxS>")
                ),
                "recommended_shape": OPERATOR_PLAN_EXAMPLE_SHAPE,
                "operator_plan_example_command": (
                    operator_plan_command(target=name, shape=OPERATOR_PLAN_EXAMPLE_SHAPE)
                ),
                "verilator_estimate_example_command": (
                    verilator_estimate_command(target=name, shape=OPERATOR_PLAN_EXAMPLE_SHAPE)
                ),
                "operator_plan_json_example_command": (
                    operator_plan_json_command(target=name, shape=OPERATOR_PLAN_EXAMPLE_SHAPE)
                ),
                "ready_modes": [MODE_TEMPLATE],
                "ready_stage_names": [
                    "verilator_build",
                    "host_probe_build",
                    "cpu_init_state",
                    "cpu_reference_output",
                    "gpu_artifact_build",
                    "hybrid_sidecar_run",
                    "coverage_output_compare",
                ],
                "not_ready_modes": {
                    MODE_RESIDENT_STATE_REUSE: {
                        "stage_plan_status": STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
                        "stage_names": ["resident_state_reuse_workflow"],
                        "missing": ["direct_verilator_resident_sidecar_handoff"],
                    },
                    MODE_PERSISTENT_RESIDENT_STATE_ABI: {
                        "stage_plan_status": STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
                        "stage_names": ["persistent_resident_state_abi_workflow"],
                        "missing": ["direct_verilator_resident_sidecar_handoff"],
                    },
                }
                if MODE_RESIDENT_STATE_REUSE in spec.modes
                else {},
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
                "stage_plan_status": STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
                "stage_names": ["host_preprocess", "rtl_sidecar_proxy_eval"],
                "missing": ["direct_verilator_rtl_sidecar_handoff"],
                "inspect_stage_command": (
                    "python3 src/tools/verilator_sidecar_shim.py --target mobile_vit --limit 128 "
                    "--stage host_preprocess --emit-command"
                ),
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


def sidecar_target_list_report() -> dict[str, object]:
    full_report = target_list_report()
    return {
        "schema_version": 1,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "view": "sidecar_gpu",
        "shortest_operator_path": shortest_operator_path(),
        "targets": [
            {
                "name": target["name"],
                "canonical_target": target["canonical_target"],
                "kind": target["kind"],
                "modes": target["modes"],
                "sidecar_gpu": target["sidecar_gpu"],
            }
            for target in full_report["targets"]
        ],
        "non_claims": [
            "sidecar discovery is not execution evidence",
            "sidecar discovery does not mean Verilator itself implements --sim-accel",
        ],
    }
