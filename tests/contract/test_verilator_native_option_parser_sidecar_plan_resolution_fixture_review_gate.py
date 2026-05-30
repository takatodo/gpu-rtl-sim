import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionFixtureReviewGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_only_non_executing_plan_resolution_fixture(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("outer status of planned", gate["review_decision"]["weakest_point"])

        scope = gate["accepted_scope"]
        self.assertEqual(scope["module"], "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py")
        self.assertEqual(
            scope["primary_entrypoint_function"],
            "resolve_native_parser_adapter_payload_to_sidecar_plan",
        )
        self.assertTrue(scope["sidecar_stage_plan_invoked_after_explicit_context"])
        self.assertFalse(scope["sidecar_handoff_contract_invoked"])
        self.assertFalse(scope["command_synthesis_invoked"])
        self.assertFalse(scope["operator_plan_invoked"])
        self.assertFalse(scope["new_execution_added"])
        self.assertFalse(scope["new_measurement_added"])

    def test_review_keeps_parser_inputs_as_constraints_and_preserved_inputs(self) -> None:
        gate = self.read_gate()
        decisions = gate["validated_implementation_decisions"]

        self.assertTrue(decisions["helper_is_plan_resolution_fixture_not_native_parser_execution"])
        self.assertTrue(decisions["adapter_payload_alone_is_rejected"])
        self.assertTrue(decisions["explicit_target_mode_template_context_required"])
        self.assertTrue(decisions["source_gate_or_manifest_reference_required"])
        self.assertTrue(decisions["template_or_registry_entry_must_match_reviewed_slice_template"])
        self.assertTrue(decisions["parser_owned_inputs_remain_schedule_and_preserved_build_inputs"])
        self.assertTrue(decisions["source_files_remain_preserved_inputs_not_source_closure"])
        self.assertTrue(decisions["filelists_remain_preserved_inputs_not_dependency_expansion"])
        self.assertTrue(decisions["correctness_policy_ref_is_reference_only"])
        self.assertTrue(decisions["stage_plan_correctness_policy_must_match_adapter_ref"])
        self.assertTrue(decisions["sidecar_handoff_contract_stays_out_of_scope"])
        self.assertTrue(decisions["command_synthesis_stays_out_of_scope"])
        self.assertTrue(decisions["execution_and_measurement_stay_out_of_scope"])

    def test_review_selects_status_hardening_before_handoff_contract(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate",
        )
        for required in (
            "whether the outer plan-resolution fixture status must mirror sidecar_stage_plan readiness status",
            "how unsupported_for_stage_plan and planned_not_ready_for_verilator_option_shim should be represented before any handoff-contract boundary",
            "tests that prove resident or not-ready modes cannot be mistaken for ready direct-Verilator plan-resolution evidence",
        ):
            self.assertIn(required, next_gate["must_define"])
        for forbidden in (
            "sidecar_handoff_contract from native parser payload",
            "command synthesis from native parser payload",
            "RTL simulation execution",
            "coverage-output equivalence for a native-parser flow",
            "automatic optimal GPU allocation",
        ):
            self.assertIn(forbidden, next_gate["must_not_claim"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["implementation_accepted"])
        self.assertTrue(policy["next_status_hardening_boundary_allowed"])
        self.assertFalse(policy["sidecar_handoff_contract_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate")


if __name__ == "__main__":
    unittest.main()
