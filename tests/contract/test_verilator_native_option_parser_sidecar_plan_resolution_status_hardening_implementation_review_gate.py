import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionStatusHardeningImplementationReviewGateTest(
    unittest.TestCase
):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_in_place_status_hardening(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("matches the reviewed readiness contract", gate["review_decision"]["reason"])
        self.assertIn("ready_for_verilator_option_shim can still be over-read", gate["review_decision"]["weakest_point"])

        accepted = gate["accepted_implementation"]
        self.assertEqual(accepted["module"], "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py")
        self.assertEqual(accepted["helper_added"], "_plan_resolution_readiness")
        self.assertTrue(accepted["outer_status_is_readiness_classification"])
        self.assertTrue(accepted["nested_stage_plan_status_preserved"])
        self.assertTrue(accepted["plan_resolution_readiness_added"])
        self.assertFalse(accepted["sidecar_handoff_contract_invoked"])
        self.assertFalse(accepted["command_synthesis_invoked"])
        self.assertFalse(accepted["execution_performed"])
        self.assertFalse(accepted["measurement_performed"])

    def test_review_accepts_readiness_mapping_without_losing_stage_status(self) -> None:
        gate = self.read_gate()
        mapping = gate["accepted_status_mapping"]

        self.assertEqual(
            mapping["stage_plan_planned_with_ready_readiness"]["outer_status"],
            "ready_for_verilator_option_shim",
        )
        self.assertTrue(mapping["stage_plan_planned_with_ready_readiness"]["ready_for_direct_verilator_option"])

        resident = mapping["stage_plan_planned_not_ready_for_verilator_option_shim"]
        self.assertEqual(resident["outer_status"], "not_ready_for_verilator_option_shim")
        self.assertEqual(resident["preserved_stage_plan_status"], "planned_not_ready_for_verilator_option_shim")
        self.assertFalse(resident["ready_for_direct_verilator_option"])

        unsupported = mapping["stage_plan_unsupported_for_stage_plan"]
        self.assertEqual(unsupported["outer_status"], "unsupported_for_stage_plan")
        self.assertEqual(unsupported["preserved_stage_plan_status"], "unsupported_for_stage_plan")
        self.assertFalse(unsupported["ready_for_direct_verilator_option"])

    def test_review_pins_readiness_summary_as_readiness_only(self) -> None:
        gate = self.read_gate()
        summary = gate["accepted_readiness_summary"]

        self.assertEqual(summary["field"], "plan_resolution_readiness")
        for field in (
            "stage_plan_status",
            "verilator_option_readiness_status",
            "ready_for_direct_verilator_option",
            "not_ready_reason",
            "status_source",
            "missing_readiness_inputs",
        ):
            self.assertIn(field, summary["required_fields"])
        self.assertIn("readiness only", summary["readiness_only_non_claim"])
        self.assertIn("not native Verilator execution", summary["readiness_only_non_claim"])

    def test_review_selects_handoff_contract_boundary_without_execution_claims(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate",
        )
        for required in (
            "the minimal ready plan-resolution fields that may be used to build a sidecar_handoff_contract",
            "the precondition that handoff-contract production is allowed only for ready_for_verilator_option_shim with ready_for_direct_verilator_option true",
            "the rejection or fallback behavior for not_ready_for_verilator_option_shim and unsupported_for_stage_plan plan-resolution outputs",
        ):
            self.assertIn(required, next_gate["must_define"])
        for forbidden in (
            "sidecar runtime handoff validation",
            "execution of sidecar_handoff_contract",
            "command synthesis from native parser payload",
            "RTL simulation execution",
            "coverage-output equivalence for a native-parser flow",
            "automatic optimal GPU allocation",
        ):
            self.assertIn(forbidden, next_gate["must_not_claim"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["implementation_accepted"])
        self.assertTrue(policy["next_handoff_contract_boundary_definition_allowed"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_handoff_contract_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate",
        )


if __name__ == "__main__":
    unittest.main()
