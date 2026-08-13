"""State-local action schedules for the device-clean TL-UL #10818 wrapper."""

from __future__ import annotations


ACTION_DOMAIN = (
    "valid_d_immediate",
    "valid_d_backpressured",
    "malformed_d_immediate",
    "malformed_d_backpressured",
)
RESIDENT_SCALE_STATES = 4096


def patch_script(offsets: dict[str, int], *, malformed: bool, backpressure: bool) -> str:
    """Return the CPU driver's transition sequence as resident patch steps."""
    def patch(**values: int) -> str:
        return " ".join(f"{offsets[name]}:{value}" for name, value in values.items())
    return "\n".join((
        patch(clk_i=0, rst_ni=0, start_i=0, malformed_i=int(malformed), d_backpressure_i=int(backpressure)),
        patch(clk_i=1), patch(clk_i=0), patch(rst_ni=1, start_i=1), patch(clk_i=1),
        patch(clk_i=0, start_i=0), patch(clk_i=1), patch(clk_i=0), patch(clk_i=1), patch(clk_i=0), patch(clk_i=1),
    )) + "\n"


def batch_patch_script(offsets: dict[str, int]) -> str:
    """Return one synchronized schedule for all four action states."""
    specs = ((False, False), (False, True), (True, False), (True, True))
    individual = [[line.split() for line in patch_script(offsets, malformed=bad, backpressure=stall).splitlines()] for bad, stall in specs]
    lines: list[str] = []
    for step_index in range(len(individual[0])):
        tokens = []
        for state_index, steps in enumerate(individual):
            tokens.extend(f"@{state_index}:{offset}:{value}" for offset, value in (token.split(":", 1) for token in steps[step_index]))
        lines.append(" ".join(tokens))
    return "\n".join(lines) + "\n"


def uniform_scale_patch_script(offsets: dict[str, int], state_count: int) -> str:
    """Broadcast malformed/backpressured action fields to every resident state."""
    fields = (
        ("clk_i", 0), ("rst_ni", 0), ("start_i", 0), ("malformed_i", 1),
        ("d_backpressure_i", 1), ("clk_i", 1), ("clk_i", 0), ("rst_ni", 1),
        ("start_i", 1), ("clk_i", 1), ("clk_i", 0), ("start_i", 0),
        ("clk_i", 1), ("clk_i", 0), ("clk_i", 1), ("clk_i", 0), ("clk_i", 1),
    )
    return "\n".join(
        " ".join(f"@{state}:{offsets[name]}:{value}" for state in range(state_count))
        for name, value in fields
    ) + "\n"
