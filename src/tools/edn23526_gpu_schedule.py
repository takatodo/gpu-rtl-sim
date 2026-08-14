"""State-local action schedule for the device-clean EDN #23526 wrapper."""

from __future__ import annotations


ACTION_DOMAIN = (
    "success_ack_ready",
    "success_ack_backpressured",
    "error_ack_ready",
    "error_ack_backpressured",
)


def action_bits(action: str) -> tuple[bool, bool]:
    if action not in ACTION_DOMAIN:
        raise ValueError(f"unknown EDN action: {action}")
    return action.startswith("error"), action.endswith("backpressured")


def patch_script(offsets: dict[str, int], *, action: str, drive_cycles: int) -> str:
    def patch(**values: int) -> str:
        return " ".join(f"{offsets[name]}:{value}" for name, value in values.items())

    inject_error, backpressure = action_bits(action)
    lines = [
        patch(
            clk_i=0,
            rst_ni=0,
            start_i=0,
            inject_error_i=int(inject_error),
            csrng_ready_i=0 if backpressure else 1,
        ),
        patch(clk_i=1),
        patch(clk_i=0),
        patch(clk_i=1),
        patch(clk_i=0),
        patch(rst_ni=1, start_i=1),
    ]
    for cycle_index in range(drive_cycles):
        lines.append(patch(clk_i=1))
        lines.append(patch(clk_i=0, start_i=0) if cycle_index == 0 else patch(clk_i=0))
    return "\n".join(lines) + "\n"
