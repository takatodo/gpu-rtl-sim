"""Independent-state stimulus contract helpers for scientific CIRCT rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class BatchStimulusSpec:
    """Deterministic independent-state stimulus contract for one promoted row.

    One state slot is one independent test case. This is a runner input
    contract, not runtime ABI authority; correctness still comes from exact
    selected-output equality against an oracle.
    """

    module: str
    source_variant: str
    candidate: str
    shape: str
    steps: int
    state_count: int
    slot_stride: str
    inner_repeat: int
    input_element_type: str
    input_element_count: int
    output_element_type: str
    output_element_count: int
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    fill_a: int
    fill_b: int
    fill_c: int
    fill_mask: int
    mix_j_mult: int
    mix_mask: int
    stimulus_kind: str = "affine_index"
    oracle_kind: str = "same_eval_reference"
    comparison_mode: str = "exact_selected_outputs"
    checksum_authority: bool = False

    def fill_value(self, state_index: int, port_index: int) -> int:
        """Return the deterministic uint8 input value for state/port indices."""
        return (
            state_index * self.fill_a + port_index * self.fill_b + self.fill_c
        ) & self.fill_mask

    def mix_value(self, repeat_index: int, port_index: int) -> int:
        """Return the deterministic inner-repeat mix value used by the bridge."""
        return (repeat_index + port_index * self.mix_j_mult) & self.mix_mask

    def as_dict(self) -> dict[str, Any]:
        """Return a review-friendly sidecar payload without claiming an ABI."""
        return {
            "module": self.module,
            "source_variant": self.source_variant,
            "candidate": self.candidate,
            "shape": self.shape,
            "batch": {
                "state_count": self.state_count,
                "steps": self.steps,
                "slot_stride": self.slot_stride,
                "one_state_slot_is_one_independent_test_case": True,
            },
            "state_entries": {
                "input": {
                    "element_type": self.input_element_type,
                    "element_count": self.input_element_count,
                    "ports": list(self.input_ports),
                },
                "output": {
                    "element_type": self.output_element_type,
                    "element_count": self.output_element_count,
                    "ports": list(self.output_ports),
                },
            },
            "stimulus": {
                "kind": self.stimulus_kind,
                "formula": "(i * fill_a + j * fill_b + fill_c) & fill_mask",
                "fill_a": self.fill_a,
                "fill_b": self.fill_b,
                "fill_c": self.fill_c,
                "fill_mask": self.fill_mask,
            },
            "inner_repeat_mix": {
                "inner_repeat": self.inner_repeat,
                "formula": "(r + j * mix_j_mult) & mix_mask",
                "mix_j_mult": self.mix_j_mult,
                "mix_mask": self.mix_mask,
            },
            "oracle": {"kind": self.oracle_kind},
            "comparison": {
                "mode": self.comparison_mode,
                "checksum_authority": self.checksum_authority,
            },
            "non_claims": [
                "no_arbitrary_systemverilog_testbench",
                "no_stable_runtime_abi",
                "no_arcilator_gpu_backend",
                "no_broad_speedup_claim",
            ],
        }


def _parse_shape_counts(
    shape: str, *, error: Callable[[str], Exception]
) -> tuple[int, int]:
    parts = shape.split("x")
    if len(parts) != 2:
        raise error(f"unsupported shape spelling {shape!r}")
    try:
        state_count = int(parts[0])
        steps = int(parts[1])
    except ValueError as exc:
        raise error(f"unsupported shape spelling {shape!r}") from exc
    if state_count <= 0 or steps <= 0:
        raise error(f"shape must have positive state and step counts: {shape!r}")
    return state_count, steps


def batch_stimulus_spec_from_bridge(
    row: dict[str, Any],
    bridge: Any,
    *,
    error: Callable[[str], Exception],
    state_count: int | None = None,
    steps: int | None = None,
    slot_stride: str = "align_up(numStateBytes, 16)",
) -> BatchStimulusSpec:
    """Derive the FC-085 independent-state stimulus contract from a BridgeSpec."""
    shape_state_count, shape_steps = _parse_shape_counts(bridge.shape, error=error)
    if state_count is None:
        state_count = shape_state_count
    if steps is None:
        steps = shape_steps
    if state_count <= 0:
        raise error("state_count must be positive")
    if steps <= 0:
        raise error("steps must be positive")

    dimensions = row.get("dimensions") if isinstance(row.get("dimensions"), dict) else {}
    inner_repeat = dimensions.get("inner_repeat")
    if not isinstance(inner_repeat, int) or inner_repeat <= 0:
        raise error("metadata row missing positive dimensions.inner_repeat")

    module = row.get("module")
    if module is None:
        module = bridge.source_variant
    if not isinstance(module, str) or not module:
        raise error("metadata row has invalid module")

    return BatchStimulusSpec(
        module=module,
        source_variant=bridge.source_variant,
        candidate=bridge.candidate,
        shape=bridge.shape,
        steps=steps,
        state_count=state_count,
        slot_stride=slot_stride,
        inner_repeat=inner_repeat,
        input_element_type=bridge.input_element_type,
        input_element_count=bridge.input_element_count,
        output_element_type=bridge.output_element_type,
        output_element_count=bridge.output_element_count,
        input_ports=bridge.input_ports,
        output_ports=bridge.output_ports,
        fill_a=bridge.fill_a,
        fill_b=bridge.fill_b,
        fill_c=bridge.fill_c,
        fill_mask=bridge.fill_mask,
        mix_j_mult=bridge.mix_j_mult,
        mix_mask=bridge.mix_mask,
    )
