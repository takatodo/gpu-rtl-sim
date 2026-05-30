import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionStatusHardeningReviewGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_definition_and_selects_in_place_implementation(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("planned can hide nested unsupported", gate["review_decision"]["reason"])
        self.assertIn("ready_for_verilator_option_shim can still be over-read", gate["review_decision"]["weakest_point"])

        next_impl = gate["required_next_implementation"]
        self.assertEqual(next_impl["name"], "implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate")
        self.assertIn(
            "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py",
            next_impl["allowed_files"],
        )
        self.assertIn(
            "tests/contract/test_verilator_native_option_parser_sidecar_plan_resolution_fixture.py",
            next_impl["allowed_files"],
        )

    def test_review_pins_readiness_status_mapping(self) -> None:
        gate = self.read_gate()
        accepted = gate["accepted_definition"]

        self.assertEqual(
            accepted["status_authority"],
            "src/tools/hybrid_benchmark_sidecar_plan.py::sidecar_stage_plan",
        )
        self.assertTrue(accepted["outer_status_is_readiness_classification"])
        self.assertTrue(accepted["nested_stage_plan_status_preserved"])
        self.assertTrue(accepted["outer_status_default_planned_for_all_modes_rejected"])
        self.assertTrue(accepted["readiness_summary_required"])

        mapping = accepted["accepted_outer_status_mapping"]
        self.assertEqual(mapping["stage_plan_planned_with_ready_readiness"], "ready_for_verilator_option_shim")
        self.assertEqual(
            mapping["stage_plan_planned_not_ready_for_verilator_option_shim"],
            "not_ready_for_verilator_option_shim",
        )
        self.assertEqual(mapping["stage_plan_unsupported_for_stage_plan"], "unsupported_for_stage_plan")

    def test_review_requires_explicit_readiness_summary_fields(self) -> None:
        gate = self.read_gate()
        accepted = gate["accepted_definition"]

        self.assertEqual(accepted["accepted_readiness_summary_field"], "plan_resolution_readiness")
        for field in (
            "stage_plan_status",
            "verilator_option_readiness_status",
            "ready_for_direct_verilator_option",
            "not_ready_reason",
            "status_source",
        ):
            self.assertIn(field, accepted["required_readiness_summary_fields"])

    def test_next_implementation_scope_stays_non_executing(self) -> None:
        gate = self.read_gate()
        next_impl = gate["required_next_implementation"]

        for requirement in (
            "derive outer status from sidecar_stage_plan status plus nested verilator_option_readiness status",
            "set outer status ready_for_verilator_option_shim only for stage_plan.status planned with nested readiness ready_for_verilator_option_shim",
            "set outer status not_ready_for_verilator_option_shim for stage_plan.status planned_not_ready_for_verilator_option_shim",
            "set outer status unsupported_for_stage_plan for stage_plan.status unsupported_for_stage_plan",
            "preserve stage_plan_status separately from outer status",
            "add plan_resolution_readiness with stage_plan_status, verilator_option_readiness_status, ready_for_direct_verilator_option, not_ready_reason, and status_source",
        ):
            self.assertIn(requirement, next_impl["must_implement"])

        for forbidden in (
            "change the Verilator overlay patch",
            "add a public CLI",
            "call sidecar_handoff_contract",
            "call synthesized Verilator command helpers",
            "run RTL simulation",
            "run coverage-output compare",
            "measure timing",
            "claim automatic optimal GPU allocation",
        ):
            self.assertIn(forbidden, next_impl["must_not_do"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["definition_accepted"])
        self.assertTrue(policy["in_place_helper_hardening_allowed_next"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_handoff_contract_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate")


if __name__ == "__main__":
    unittest.main()
