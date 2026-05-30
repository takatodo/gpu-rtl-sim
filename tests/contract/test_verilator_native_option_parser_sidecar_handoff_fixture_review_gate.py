import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json"
)


class VerilatorNativeOptionParserSidecarHandoffFixtureReviewGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_only_non_executing_adapter_fixture(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_sidecar_handoff_fixture_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("not yet resolved into the existing sidecar stage plan", gate["review_decision"]["weakest_point"])

        scope = gate["accepted_scope"]
        self.assertEqual(scope["module"], "src/tools/verilator_native_option_parser_sidecar_handoff.py")
        self.assertEqual(scope["primary_entrypoint_function"], "native_parser_values_to_sidecar_adapter_payload")
        self.assertFalse(scope["public_cli_added"])
        self.assertFalse(scope["sidecar_stage_plan_invoked"])
        self.assertFalse(scope["sidecar_handoff_contract_invoked"])
        self.assertFalse(scope["new_execution_added"])
        self.assertFalse(scope["new_measurement_added"])

    def test_review_confirms_parser_boundary_and_reference_only_correctness(self) -> None:
        gate = self.read_gate()
        decisions = gate["validated_implementation_decisions"]

        self.assertTrue(decisions["helper_is_adapter_authority_not_sidecar_stage_plan_output"])
        self.assertTrue(decisions["parser_owned_fields_are_preserved_without_source_closure_inference"])
        self.assertTrue(decisions["filelists_are_preserved_not_expanded"])
        self.assertTrue(decisions["sidecar_owned_resolved_fields_are_absent"])
        self.assertTrue(decisions["sidecar_owned_resolved_fields_are_rejected_when_present_in_parser_values"])
        self.assertTrue(decisions["coverage_output_equivalence_is_reference_only"])
        self.assertTrue(decisions["unexpected_correctness_policy_refs_are_rejected"])
        self.assertTrue(decisions["execution_and_compare_stay_out_of_scope"])

        scope = gate["accepted_scope"]
        self.assertEqual(scope["correctness_policy_reference_field"], "correctness_policy_ref")
        self.assertEqual(
            scope["correctness_policy_reference_status"],
            "adapter_default_reference_only_not_parser_populated_compare_evidence",
        )
        self.assertEqual(scope["sidecar_owned_resolution_status"], "unresolved_by_native_parser_adapter_fixture")

    def test_next_gate_defines_plan_resolution_before_execution(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate",
        )
        self.assertIn(
            "how the accepted adapter payload will be resolved into the existing sidecar stage-plan surface without making the native parser infer source closure, coverage targets, host-probe metadata, state paths, report paths, or compare labels",
            next_gate["must_define"],
        )
        for forbidden in (
            "native Verilator parser implementation",
            "sidecar runtime handoff validation",
            "RTL simulation execution",
            "coverage-output equivalence for a native-parser flow",
            "automatic optimal GPU allocation",
        ):
            self.assertIn(forbidden, next_gate["must_not_claim"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["implementation_accepted"])
        self.assertTrue(policy["next_boundary_definition_allowed"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_validation_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate")


if __name__ == "__main__":
    unittest.main()
