"""State-local action schedule for the device-clean entropy_src #10983 wrapper."""

from __future__ import annotations


ACTION_DOMAIN = ("health_tests_before_fw_sha3_start",)


def patch_script(offsets: dict[str, int], *, drive_cycles: int) -> str:
    def patch(**values: int) -> str:
        return " ".join(f"{offsets[name]}:{value}" for name, value in values.items())

    lines = [
        patch(clk_i=0, rst_ni=0, start_i=0),
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
