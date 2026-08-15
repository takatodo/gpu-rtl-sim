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

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_object(path: Path, label: str) -> dict[str, Any]:
    def reject_constant(token: str) -> None:
        raise ValueError(f"{label} contains non-finite JSON token {token}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_repo(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        env=dict(env) if env is not None else None,
        text=True,
        capture_output=True,
    )


def require_success(completed: subprocess.CompletedProcess[str], label: str) -> None:
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit {completed.returncode}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )


def revision_sha(checkout: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    require_success(completed, f"git rev-parse {checkout}")
    return completed.stdout.strip()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()
