"""Shared option mapping for the planned Verilator sidecar GPU interface."""

from __future__ import annotations

from dataclasses import dataclass

from hybrid_template_types import parse_shape


@dataclass(frozen=True)
class SidecarShape:
    nstates: int
    steps: int

    @property
    def shape(self) -> str:
        return f"{self.nstates}x{self.steps}"


def parse_positive_count(raw: str, *, option_name: str) -> int:
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError(f"{option_name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{option_name} must be a positive integer")
    return value


def shape_from_states_steps(*, states: str | int, steps: str | int) -> SidecarShape:
    nstates = states if isinstance(states, int) else parse_positive_count(states, option_name="--sim-accel-states")
    step_count = steps if isinstance(steps, int) else parse_positive_count(steps, option_name="--sim-accel-steps")
    if nstates <= 0:
        raise ValueError("--sim-accel-states must be a positive integer")
    if step_count <= 0:
        raise ValueError("--sim-accel-steps must be a positive integer")
    return SidecarShape(nstates=nstates, steps=step_count)


def shape_from_compact(raw: str) -> SidecarShape:
    nstates, steps = parse_shape(raw)
    return SidecarShape(nstates=nstates, steps=steps)


def resolve_sidecar_shape(
    *,
    shape: str | None,
    sim_accel_shape: str | None,
    sim_accel_states: str | int | None,
    sim_accel_steps: str | int | None,
) -> str | None:
    spelled_shapes = sum(
        1
        for has_shape in (
            shape is not None,
            sim_accel_shape is not None,
            sim_accel_states is not None or sim_accel_steps is not None,
        )
        if has_shape
    )
    if spelled_shapes > 1:
        raise ValueError("use only one shape spelling: --shape, --sim-accel-shape, or --sim-accel-states/--sim-accel-steps")
    if shape is not None:
        nstates, steps = parse_shape(shape)
        return SidecarShape(nstates=nstates, steps=steps).shape
    if sim_accel_shape is not None:
        return shape_from_compact(sim_accel_shape).shape
    if sim_accel_states is None and sim_accel_steps is None:
        return None
    if sim_accel_states is None or sim_accel_steps is None:
        raise ValueError("--sim-accel-states and --sim-accel-steps must be provided together")
    return shape_from_states_steps(states=sim_accel_states, steps=sim_accel_steps).shape


def validate_sim_accel_mode(sim_accel: str | None) -> None:
    if sim_accel is None:
        return
    if sim_accel != "sidecar-gpu":
        raise ValueError("--sim-accel currently supports only sidecar-gpu")
