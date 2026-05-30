import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarHandoffReviewGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_only_adapter_boundary(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "implement_verilator_native_option_parser_sidecar_handoff_fixture_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("reviewed boundary", gate["review_decision"]["weakest_point"])

        boundary = gate["accepted_boundary"]
        self.assertEqual(boundary["selected_surface"], "native_parser_values_to_sidecar_plan_adapter_boundary")
        self.assertEqual(
            boundary["selected_contract"],
            "native_parser_adapter_payload_before_existing_sidecar_stage_plan",
        )
        self.assertEqual(boundary["adapter_implementation_status"], "not_implemented")

    def test_review_qualifies_correctness_policy_and_sidecar_owned_fields(self) -> None:
        gate = self.read_gate()
        boundary = gate["accepted_boundary"]

        self.assertEqual(
            boundary["correctness_policy_reference_status"],
            "adapter_default_reference_only_not_parser_populated_compare_evidence",
        )
        for field in (
            "state_authority",
            "coverage_output_target",
            "host_probe_build_metadata_ref",
            "init_state_path_or_rule",
            "compare_report_path_or_rule",
            "compare_labels",
        ):
            self.assertIn(field, boundary["accepted_sidecar_owned_fields_referenced_not_populated_by_parser"])
        for field in ("source_files", "filelists", "defines", "include_dirs", "warning_flags"):
            self.assertIn(field, boundary["accepted_parser_owned_fields"])

    def test_next_gate_remains_non_executing_fixture_only(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "implement_verilator_native_option_parser_sidecar_handoff_fixture_gate",
        )
        self.assertIn(
            "tests proving the helper output does not contain resolved state_files, generated_reports, compare labels, coverage target, manifest refs, or host-probe metadata",
            next_gate["must_implement"],
        )
        for forbidden in (
            "run RTL simulation",
            "change runtime or GPU ABI",
            "infer arbitrary source closure or filelist dependencies",
            "run coverage-output compare",
            "measure timing",
            "add a public CLI",
        ):
            self.assertIn(forbidden, next_gate["must_not_do"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["definition_accepted"])
        self.assertTrue(policy["non_executing_fixture_allowed_next"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_validation_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "implement_verilator_native_option_parser_sidecar_handoff_fixture_gate")


if __name__ == "__main__":
    unittest.main()
