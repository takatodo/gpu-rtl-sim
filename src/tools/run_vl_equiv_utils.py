"""Shared helpers for GPU/CPU equivalence scripts."""

from __future__ import annotations


def infer_last_clk(script: str, clk_offset: int) -> int:
    last = script.strip().splitlines()[-1]
    search_prefix = f"{clk_offset}:"
    for token in reversed(last.split()):
        if token.startswith(search_prefix):
            return int(token.split(":", 1)[1], 0)
    raise ValueError("clock token missing from action patch script")


def one_eval_patch(clk_offset: int, *, final_clk: int) -> str:
    return f"{clk_offset}:{1 - final_clk}\n"


def decode_state_values(image: bytes, base: int, offsets: dict[str, int]) -> dict[str, int]:
    values = {name: image[base + offsets[name]] for name in ("done", "oracle_violation", "d_error", "intg_error", "action_coverage")}
    values["d_data"] = int.from_bytes(image[base + offsets["d_data"] : base + offsets["d_data"] + 4], "little")
    return values


def batch_observables(image: bytes, state_count: int, storage_size: int, offsets: dict[str, int]) -> list[dict[str, int]]:
    if len(image) != storage_size * state_count:
        raise RuntimeError(f"unexpected batch dump bytes={len(image)} storage={storage_size}")
    return [decode_state_values(image, state_index * storage_size, offsets) for state_index in range(state_count)]


def all_states_match(image: bytes, state_count: int, storage_size: int, offsets: dict[str, int], expected: dict[str, int] | None) -> bool:
    if expected is None or len(image) != storage_size * state_count:
        return False
    return all(decode_state_values(image, state_index * storage_size, offsets) == expected for state_index in range(state_count))
