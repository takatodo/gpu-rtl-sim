import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractFixtureGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_gate_records_existing_module_helper_implementation(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate",
        )
        surface = gate["implemented_surface"]
        self.assertEqual(surface["module"], "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py")
        self.assertEqual(
            surface["support_module"],
            "src/tools/verilator_native_option_parser_sidecar_handoff_contract.py",
        )
        self.assertEqual(
            surface["primary_entrypoint_function"],
            "resolve_native_parser_plan_resolution_to_sidecar_handoff_contract",
        )
        self.assertEqual(surface["support_entrypoint_function"], "resolve_plan_resolution_to_handoff_contract")
        self.assertTrue(surface["line_guard_split"])
        self.assertTrue(surface["ready_only"])
        self.assertTrue(surface["metadata_only"])
        self.assertFalse(surface["new_public_cli_added"])
        self.assertFalse(surface["command_synthesis_invoked"])
        self.assertFalse(surface["operator_plan_invoked"])
        self.assertFalse(surface["new_execution_added"])
        self.assertFalse(surface["new_measurement_added"])

    def test_gate_records_ready_checks_before_handoff_contract(self) -> None:
        gate = self.read_gate()
        checks = gate["implemented_ready_checks"]

        self.assertEqual(checks["surface"], "native_verilator_parser_sidecar_plan_resolution_fixture")
        self.assertEqual(checks["status"], "ready_for_verilator_option_shim")
        self.assertTrue(checks["plan_resolution_readiness.ready_for_direct_verilator_option"])
        self.assertEqual(checks["plan_resolution_readiness.stage_plan_status"], "planned")
        self.assertEqual(
            checks["plan_resolution_readiness.verilator_option_readiness_status"],
            "ready_for_verilator_option_shim",
        )
        self.assertEqual(checks["stage_plan.status"], "planned")
        self.assertEqual(checks["stage_plan.verilator_option_readiness.status"], "ready_for_verilator_option_shim")
        self.assertTrue(checks["parser_schedule_constraints.shape_matches_state_step"])
        self.assertTrue(checks["parser_schedule_constraints.shape_equals_stage_plan.shape"])
        self.assertTrue(checks["hybrid_sidecar_run.shape_equals_parser_shape"])
        self.assertEqual(checks["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(checks["correctness_policy_ref_status"], "reference_only_not_compare_evidence")
        for forbidden in ("handoff_contract", "operator_plan", "verilator_command_argv", "timing"):
            self.assertIn(forbidden, checks["forbidden_prepopulated_fields"])

    def test_gate_records_stage_detail_validation_and_fail_closed_behavior(self) -> None:
        gate = self.read_gate()
        details = gate["required_stage_detail_validation"]

        for field in ("nstates", "steps", "init_state"):
            self.assertIn(field, details["hybrid_sidecar_run"])
        for field in (
            "reference_dump",
            "candidate_dump",
            "acceptance_policy",
            "reference_label",
            "candidate_label",
            "coverage_output_target",
            "json_out",
        ):
            self.assertIn(field, details["coverage_output_compare"])

        fail_closed = gate["implemented_fail_closed_behavior"]
        not_ready = fail_closed["not_ready_for_verilator_option_shim"]
        self.assertTrue(not_ready["returns_structured_closed_result"])
        self.assertFalse(not_ready["handoff_contract_metadata_allowed"])
        self.assertFalse(not_ready["sidecar_handoff_contract_invoked"])
        self.assertIn("missing_readiness_inputs", not_ready["preserves"])

        unsupported = fail_closed["unsupported_for_stage_plan"]
        self.assertTrue(unsupported["returns_structured_closed_result"])
        self.assertFalse(unsupported["handoff_contract_metadata_allowed"])
        self.assertFalse(unsupported["sidecar_handoff_contract_invoked"])

        malformed = fail_closed["malformed_or_inconsistent_ready_input"]
        self.assertEqual(malformed["raises"], "NativeParserSidecarPlanResolutionError")
        self.assertFalse(malformed["sidecar_handoff_contract_invoked_before_validation"])

    def test_gate_records_focused_tests_and_selects_review(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["verification"]["focused_contract_test_command"],
            "python3 -m unittest tests.contract.test_verilator_native_option_parser_sidecar_plan_resolution_fixture -q",
        )
        self.assertEqual(gate["verification"]["focused_contract_test_exit_code"], 0)
        self.assertEqual(gate["verification"]["focused_contract_test_count"], 14)

        next_gate = gate["required_next_gate"]
        self.assertEqual(
            next_gate["name"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate",
        )
        self.assertIn(
            "whether not-ready and unsupported results fail closed without calling sidecar_handoff_contract",
            next_gate["must_decide"],
        )
        self.assertIn("executed sidecar_handoff_contract evidence", next_gate["must_not_claim"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate",
        )

    def test_acceptance_policy_blocks_execution_and_allocation_claims(self) -> None:
        gate = self.read_gate()
        policy = gate["acceptance_policy"]

        self.assertTrue(policy["implementation_only"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_handoff_validation_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_contract_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["operator_plan_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertIn("not sidecar runtime handoff validation", gate["non_claims"])
        self.assertIn("not operator-plan production from native parser payload", gate["non_claims"])
        self.assertIn("not automatic optimal GPU allocation for any design", gate["non_claims"])


if __name__ == "__main__":
    unittest.main()
