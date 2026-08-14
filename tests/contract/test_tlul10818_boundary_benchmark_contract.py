from __future__ import annotations

import itertools
import json
import re
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from tlul10818_gpu_schedule import ACTION_DOMAIN  # noqa: E402


CONTRACT = REPO_ROOT / "config" / "tlul10818_boundary_benchmark.json"
DOC = REPO_ROOT / "docs" / "tlul10818_boundary_benchmark.md"
HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")


def _load_contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


class Tlul10818BoundaryBenchmarkContractTest(unittest.TestCase):
    def test_target_identity_and_external_authority_are_fixed(self) -> None:
        contract = _load_contract()
        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(contract["surface"], "tlul10818_boundary_benchmark_target")
        self.assertEqual(contract["status"], "pending_external_full_grid_evidence")
        target = contract["target"]
        self.assertEqual(target["target_id"], "tlul10818")
        self.assertEqual(target["issue"], "https://github.com/lowRISC/opentitan/issues/10818")
        self.assertRegex(target["bad_revision"], HEX40)
        self.assertRegex(target["fixed_revision"], HEX40)
        self.assertNotEqual(target["bad_revision"], target["fixed_revision"])
        authority = contract["authority"]
        self.assertIs(authority["codex_runtime_execution"], False)
        self.assertEqual(authority["runtime_owner"], "external_operator_or_ci")
        self.assertIn("rtl_boundary_pipeline_result", authority["required_adjudicator_surfaces"])

    def test_current_wrapper_grid_matches_existing_action_domain(self) -> None:
        contract = _load_contract()
        sweep_space = contract["current_wrapper_sweep_space"]
        axes = sweep_space["axes"]
        self.assertEqual(sweep_space["surface"], "rtl_boundary_sweep_space")
        self.assertEqual([axis["kind"] for axis in axes], ["categorical", "categorical"])
        axis_names = [axis["name"] for axis in axes]
        values = [axis["values"] for axis in axes]
        expected_parameters = [
            dict(zip(axis_names, combination))
            for combination in itertools.product(*values)
        ]
        mapping = contract["current_wrapper_action_mapping"]
        self.assertEqual(
            sorted(json.dumps(item["parameters"], sort_keys=True) for item in mapping),
            sorted(json.dumps(parameters, sort_keys=True) for parameters in expected_parameters),
        )
        self.assertEqual(
            sorted(item["action"] for item in mapping),
            sorted(ACTION_DOMAIN),
        )

    def test_completion_requirements_reject_runtime_and_algorithm_overclaims(self) -> None:
        requirements = _load_contract()["completion_requirements"]
        self.assertIs(requirements["current_wrapper_is_not_full_boundary_benchmark"], True)
        self.assertIs(requirements["external_runner_must_generate_complete_ground_truth"], True)
        self.assertIs(requirements["external_runner_must_record_raw_trial_executions_and_launches"], True)
        self.assertIs(requirements["no_unknown_bug_discovery_claim"], True)
        self.assertIs(requirements["no_ppo_or_rl_superiority_claim"], True)
        self.assertIs(requirements["no_gpu_selector_algorithm_superiority_claim"], True)

    def test_expected_artifacts_are_generated_outputs_not_source_of_truth(self) -> None:
        artifacts = _load_contract()["expected_artifacts"]
        self.assertEqual(len(artifacts), len(set(artifacts.values())))
        for relative in artifacts.values():
            self.assertFalse(Path(relative).is_absolute())
            self.assertTrue(relative.startswith("artifacts/tlul10818_boundary_benchmark/"))
        self.assertTrue(DOC.is_file())
        doc_text = DOC.read_text(encoding="utf-8")
        self.assertIn("not contain runtime evidence", doc_text)
        self.assertIn("Codex must not", doc_text)


if __name__ == "__main__":
    unittest.main()
