"""Direct validation of the pinned Ibex #2188 GPU boundary profile."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = REPO_ROOT / "evidence" / "ibex2188_boundary_profile_v1"
INPUTS_DIR = REPO_ROOT / "evidence" / "ibex2188_boundary_profile_inputs_v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


class Ibex2188BoundaryProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
        self.adjudication = json.loads(
            (PROFILE_DIR / "adjudication.json").read_text(encoding="utf-8")
        )
        self.report_bundle = json.loads(
            (PROFILE_DIR / "report_bundle.json").read_text(encoding="utf-8")
        )

    def test_profile_is_pinned_and_hash_linked(self) -> None:
        self.assertEqual(self.profile["surface"], "ibex2188_boundary_profile")
        self.assertEqual(self.profile["status"], "pinned")
        self.assertEqual(
            self.profile["adjudication_sha256"],
            sha256_json(self.adjudication),
        )
        self.assertEqual(
            self.profile["report_bundle_sha256"],
            sha256_json(self.report_bundle),
        )
        contract = json.loads((INPUTS_DIR / "experiment_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(self.profile["experiment_contract_sha256"], sha256_json(contract))
        evidence = json.loads((INPUTS_DIR / "evidence_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(self.profile["evidence_bundle_sha256"], sha256_json(evidence))

    def test_adjudication_is_a_passing_full_grid_result(self) -> None:
        self.assertEqual(self.adjudication["surface"], "rtl_boundary_adjudication")
        self.assertEqual(self.adjudication["status"], "pass")
        self.assertEqual(self.adjudication["issues"], [])
        self.assertEqual(self.adjudication["verified_identity"]["point_count"], 4)
        self.assertEqual(
            self.adjudication["verified_identity"]["target"]["target_id"], "ibex2188"
        )
        bad = self.adjudication["ground_truth_analysis"]["revisions"]["bad"]
        fixed = self.adjudication["ground_truth_analysis"]["revisions"]["fixed"]
        self.assertEqual(bad["fail_point_count"], 1)
        self.assertEqual(fixed["fail_point_count"], 0)
        self.assertEqual(
            len(self.adjudication["ground_truth_analysis"]["bad_to_fixed"]["disappeared_failure_point_ids"]),
            1,
        )
        trial_ids = {trial["trial_id"] for trial in self.adjudication["trial_results"]}
        self.assertEqual(
            trial_ids,
            {"random_gpu", "stratified_gpu", "ordered_refinement_gpu", "novelty_gpu", "random_cpu"},
        )

    def test_report_bundle_reproduces_graph_and_markdown(self) -> None:
        self.assertEqual(self.report_bundle["surface"], "rtl_boundary_report_bundle")
        self.assertEqual(
            self.report_bundle["source_adjudication_sha256"],
            sha256_json(self.adjudication),
        )
        self.assertEqual(
            (PROFILE_DIR / "report.md").read_text(encoding="utf-8"),
            self.report_bundle["markdown_report"],
        )
        self.assertEqual(
            (PROFILE_DIR / "graph.svg").read_text(encoding="utf-8"),
            self.report_bundle["graph_svg"],
        )


if __name__ == "__main__":
    unittest.main()
