"""Command spelling helpers for sidecar benchmark discovery."""

from __future__ import annotations

from hybrid_benchmark_specs import SIDECAR_ACCEL
from hybrid_template_types import parse_shape


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
