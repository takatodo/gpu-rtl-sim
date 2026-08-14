"""State-local action schedules for the device-clean TL-UL #10818 wrapper."""

from __future__ import annotations

from tlul10818_boundary_schedule import (
    RUNNER_CONTROL_AXES,
    boundary_action_mapping,
    boundary_action_name,
    boundary_contract_projection,
    boundary_patch_script,
    boundary_patch_script_for_parameters,
    boundary_sweep_space,
)


ACTION_DOMAIN = (
    "valid_d_immediate",
    "valid_d_backpressured",
    "malformed_d_immediate",
    "malformed_d_backpressured",
)
RESIDENT_SCALE_STATES = 4096


def patch_script(offsets: dict[str, int], *, malformed: bool, backpressure: bool) -> str:
    """Return the CPU driver's transition sequence as resident patch steps."""
    return boundary_patch_script(
        offsets,
        request_integrity="malformed" if malformed else "valid",
        backpressure_cycles=1 if backpressure else 0,
        response_delay_cycles=0,
    )


def batch_patch_script(offsets: dict[str, int]) -> str:
    """Return one synchronized schedule for all four action states."""
    specs = ((False, False), (False, True), (True, False), (True, True))
    individual = [
        [
            line.split()
            for line in patch_script(
                offsets, malformed=malformed, backpressure=backpressure
            ).splitlines()
        ]
        for malformed, backpressure in specs
    ]
    lines: list[str] = []
    for step_index in range(max(len(steps) for steps in individual)):
        tokens = []
        for state_index, steps in enumerate(individual):
            if step_index >= len(steps):
                continue
            tokens.extend(
                f"@{state_index}:{offset}:{value}"
                for offset, value in (
                    token.split(":", 1) for token in steps[step_index]
                )
            )
        lines.append(" ".join(tokens))
    return "\n".join(lines) + "\n"


def uniform_scale_patch_script(offsets: dict[str, int], state_count: int) -> str:
    """Return a state-0 patch script to be replicated by the hybrid runtime."""
    if isinstance(state_count, bool) or not isinstance(state_count, int) or state_count <= 0:
        raise ValueError("state_count must be a positive integer")
    return patch_script(offsets, malformed=True, backpressure=True)
