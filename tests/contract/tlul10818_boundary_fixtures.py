from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from tlul10818_boundary_evidence import build_boundary_trial_evidence  # noqa: E402


CONTRACT = REPO_ROOT / "config" / "tlul10818_boundary_benchmark.json"
DOC = REPO_ROOT / "docs" / "tlul10818_boundary_benchmark.md"
SCRIPT = REPO_ROOT / "scripts" / "adjudicate_tlul10818_boundary_benchmark.sh"
GPU_TB = REPO_ROOT / "examples" / "tlul10818" / "tlul_adapter_sram_10818_gpu_tb.sv"
HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")
GOLDEN_SWEEP_SHA256 = "a7672362bf1290d427e04c3e0491c866de422977ecc48058e7de6520d7caf717"
GOLDEN_POINT_DIGESTS = (
    "f22ec5a4973f85e70cf8e9f7fa8f219567820c8ec60d72301ffd3169a7d53cbe",
    "70c3cb0794251b18fa916be6fbb6c930b5aae39be60568f7f03b27d748c418af",
    "17bc545eb83558429ce22e6ccc14ff63e08a10599d76a2c5661897bc6413d24f",
    "c55973b103de2e98ab4d2831177d2ddd7199b92814f213f1da8071eaeff0b225",
    "d9fc37100bbd1c7bcffa925d7684997781276005c5457464e165038bbd42a29c",
    "6b892a4303e1de8d6df4910ebb32b851018388aff0becec21fd9ee0a231bfb0b",
    "30932a3f4f3fb7a78eb5030306f468228ebe7be3542cb943dfcfafe15b5897cc",
    "9eb30479ed9a4f5e10ffe199f1734ca44e7858f0427783a175009b2834f98148",
)


def load_contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def golden_sweep_enumerator(_sweep_space: dict) -> dict:
    parameters = [
        {
            "backpressure_cycles": bp,
            "request_integrity": integrity,
            "response_delay_cycles": delay,
        }
        for bp, integrity, delay in itertools.product(
            (0, 3), ("malformed", "valid"), (0, 2)
        )
    ]
    return {
        "schema_version": 1,
        "surface": "rtl_boundary_sweep_enumeration",
        "sweep_space_sha256": GOLDEN_SWEEP_SHA256,
        "point_count": len(GOLDEN_POINT_DIGESTS),
        "points": [
            {"point_id": f"point:v1:{point_id}", "parameters": parameter}
            for point_id, parameter in zip(GOLDEN_POINT_DIGESTS, parameters)
        ],
    }


def experiment_run_spec() -> dict:
    seed = "1" * 64
    policies = {
        "random": {
            "kind": "random",
            "algorithm_version": 1,
            "seed_sha256": seed,
            "configuration": {},
        },
        "stratified": {
            "kind": "stratified",
            "algorithm_version": 1,
            "seed_sha256": seed,
            "configuration": {"strata_axes": ["request_integrity"]},
        },
        "refinement": {
            "kind": "ordered_refinement",
            "algorithm_version": 1,
            "seed_sha256": seed,
            "configuration": {"axis": "backpressure_cycles"},
        },
        "novelty": {
            "kind": "novelty_boundary_guided",
            "algorithm_version": 1,
            "seed_sha256": seed,
            "configuration": {},
        },
    }
    trials = [
        {
            "trial_id": f"{name}_gpu",
            "backend_id": "gpu",
            "policy": policy,
            "requested_count": 2,
            "budget_logical_bad_queries": 8,
        }
        for name, policy in policies.items()
    ]
    trials.append(
        {
            "trial_id": "random_cpu",
            "backend_id": "cpu",
            "policy": policies["random"],
            "requested_count": 2,
            "budget_logical_bad_queries": 8,
        }
    )
    return {
        "experiment_id": "opentitan-tlul10818-boundary-fixture-v1",
        "finite_axis_values": {
            "backpressure_cycles": [0, 3],
            "response_delay_cycles": [0, 2],
        },
        "backends": [
            {
                "backend_id": "cpu",
                "kind": "cpu",
                "executor_identity": "cpu-reference:fixture",
                "resident_width": 1,
            },
            {
                "backend_id": "gpu",
                "kind": "gpu",
                "executor_identity": "gpu-resident:fixture",
                "resident_width": 8,
            },
        ],
        "trials": trials,
        "comparisons": [
            {
                "comparison_id": "selectors-on-gpu",
                "kind": "selector",
                "trial_ids": [f"{name}_gpu" for name in policies],
            },
            {
                "comparison_id": "random-cpu-gpu",
                "kind": "backend",
                "trial_ids": ["random_cpu", "random_gpu"],
            },
        ],
    }


def raw_run_result(contract: dict) -> dict:
    point_results = []
    for action in contract["action_domain"]:
        malformed = action["parameters"]["request_integrity"] == "malformed"
        bad = {
            "done": 1,
            "d_data": 0 if malformed else 0x12345678,
            "d_error": int(malformed),
            "intg_error": int(malformed),
            "oracle_violation": int(malformed),
        }
        fixed = {
            "done": 1,
            "d_data": 0xFFFFFFFF if malformed else 0x12345678,
            "d_error": int(malformed),
            "intg_error": int(malformed),
            "oracle_violation": 0,
        }
        point_results.append(
            {
                "point_id": action["point_id"],
                "coverage_feature_ids": [f"coverage:{action['point_id']}"],
                "revisions": {
                    "bad": {"cpu": bad, "gpu": dict(bad)},
                    "fixed": {"cpu": fixed, "gpu": dict(fixed)},
                },
            }
        )

    def selector(_sweep_space, _policy, completed_batches, requested_count):
        completed = {
            point_id
            for batch in completed_batches
            for point_id in batch["selected_point_ids"]
        }
        return [
            row["point_id"]
            for row in contract["action_domain"]
            if row["point_id"] not in completed
        ][:requested_count]

    def timing(_trial_id, launch_index, _group):
        return {
            "cycle_evals": 1,
            "start_offset_ns": launch_index,
            "end_offset_ns": launch_index + 1,
        }

    return {
        "runner": {
            "status": "pass",
            "identity": "external-ci:fixture",
            "completed_at": "2026-08-14T00:00:00Z",
        },
        "point_results": point_results,
        "trials": build_boundary_trial_evidence(
            contract, point_results, selector, timing
        ),
    }
