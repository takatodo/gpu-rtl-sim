"""Static checks for the full-grid Ibex #2188 boundary observations runner."""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "tools"
SCRIPTS = REPO_ROOT / "scripts"
CONTRACT_PATH = REPO_ROOT / "evidence" / "ibex2188_boundary_profile_inputs_v1" / "experiment_contract.json"
BAD_REVISION = "668233699df9ec2a40413e69e0de0a5b10185980"
FIXED_REVISION = "9e4a950aa6aa0e20eb638aeeb78743d4a9ddaaeb"


class Ibex2188BoundaryObservationsRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, TOOLS.as_posix())
        sys.path.insert(0, SCRIPTS.as_posix())
        cls.runner_io = importlib.import_module("ibex2188_boundary_runner_io")
        cls.run_result = importlib.import_module("build_ibex2188_boundary_run_result")
        cls.observations = importlib.import_module("run_ibex2188_boundary_observations")

    def test_runner_pins_the_public_revisions(self) -> None:
        self.assertEqual(self.runner_io.BAD_REVISION, BAD_REVISION)
        self.assertEqual(self.runner_io.FIXED_REVISION, FIXED_REVISION)

    def test_contract_has_the_ordered_axis_and_ordered_refinement(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        axes = {axis["name"]: axis for axis in contract["sweep_space"]["axes"]}
        self.assertIn("load_response_delay_cycles", axes)
        self.assertEqual(axes["load_response_delay_cycles"]["kind"], "ordered")
        self.assertEqual(axes["load_response_delay_cycles"]["values"], [0, 1])
        self.assertEqual(len(contract["action_domain"]), 4)
        ordered = next(
            trial
            for trial in contract["trials"]
            if trial["trial_id"] == "ordered_refinement_gpu"
        )
        self.assertEqual(ordered["policy"]["kind"], "ordered_refinement")
        gpu = next(backend for backend in contract["backends"] if backend["backend_id"] == "gpu")
        self.assertNotEqual(gpu["executor_identity"], "ibex2188-gpu-profile:pending-v1")

    def test_patch_schedule_is_bounded_and_batched(self) -> None:
        disabled = {"fault_enable": "disabled", "load_response_delay_cycles": 0}
        guarded = {"fault_enable": "guarded_bit0", "load_response_delay_cycles": 1}
        single = self.runner_io.single_state_patch(guarded)
        self.assertEqual(len(single), 23)
        self.assertIn("106:1", single[0])
        self.assertIn("109:1", single[0])
        disabled_single = self.runner_io.single_state_patch(disabled)
        self.assertIn("106:0", disabled_single[0])
        actions = {
            "a": {"parameters": disabled},
            "b": {"parameters": guarded},
        }
        script, steps = self.runner_io.batch_patch_script(
            actions_by_point=actions,
            group=[(0, "a", "bad", "bad_search"), (0, "b", "bad", "bad_search")],
        )
        self.assertEqual(steps, 23)
        first = script.splitlines()[0]
        self.assertIn("@0:106:0", first)
        self.assertIn("@1:106:1", first)

    def test_run_result_timing_rows_are_strict(self) -> None:
        validator = self.run_result._timing_rows
        with self.assertRaises(ValueError):
            validator([{"trial_id": "random_gpu", "launch_index": 0, "cycle_evals": 1,
                        "start_offset_ns": 10, "end_offset_ns": 5}])
        rows = validator(
            [{"trial_id": "random_gpu", "launch_index": 0, "cycle_evals": 23,
              "start_offset_ns": 0, "end_offset_ns": 100}]
        )
        self.assertEqual(rows[0]["cycle_evals"], 23)


if __name__ == "__main__":
    unittest.main()
