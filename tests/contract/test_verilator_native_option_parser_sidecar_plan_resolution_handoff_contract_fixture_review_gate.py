import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractFixtureReviewGateTest(
    unittest.TestCase
):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_metadata_only_fixture_after_blocker_fix(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("ready-only metadata boundary", gate["review_decision"]["reason"])
        self.assertIn("sidecar_handoff_contract can still be over-read", gate["review_decision"]["weakest_point"])

        accepted = gate["accepted_implementation"]
        self.assertEqual(accepted["wrapper_module"], "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py")
        self.assertEqual(
            accepted["support_module"],
            "src/tools/verilator_native_option_parser_sidecar_handoff_contract.py",
        )
        self.assertEqual(
            accepted["primary_entrypoint_function"],
            "resolve_native_parser_plan_resolution_to_sidecar_handoff_contract",
        )
        self.assertTrue(accepted["ready_only"])
        self.assertTrue(accepted["metadata_only"])
        self.assertTrue(accepted["thin_wrapper_kept"])
        self.assertFalse(accepted["new_public_cli_added"])
        self.assertFalse(accepted["command_synthesis_invoked"])
        self.assertFalse(accepted["operator_plan_invoked"])
        self.assertFalse(accepted["efficiency_estimate_invoked"])
        self.assertFalse(accepted["execution_performed"])
        self.assertFalse(accepted["measurement_performed"])
        self.assertFalse(accepted["runtime_or_abi_changed"])

        blocker = gate["accepted_blocker_fix"]
        self.assertEqual(blocker["status"], "fixed_before_review_acceptance")
        self.assertIn("efficiency_estimate_invoked", blocker["required_check"])
        self.assertEqual(blocker["test_case"], "handoff_contract_rejects_efficiency_estimate_before_metadata")

    def test_review_pins_ready_only_checks_and_fail_closed_results(self) -> None:
        gate = self.read_gate()
        checks = gate["accepted_ready_only_checks"]

        self.assertEqual(checks["required_input_surface"], "native_verilator_parser_sidecar_plan_resolution_fixture")
        self.assertEqual(checks["required_input_status"], "ready_for_verilator_option_shim")
        self.assertTrue(checks["plan_resolution_readiness.ready_for_direct_verilator_option"])
        self.assertEqual(checks["plan_resolution_readiness.stage_plan_status"], "planned")
        self.assertEqual(checks["stage_plan.status"], "planned")
        self.assertTrue(checks["parser_schedule_constraints.shape_matches_state_step"])
        self.assertTrue(checks["parser_schedule_constraints.shape_equals_stage_plan.shape"])
        self.assertTrue(checks["hybrid_sidecar_run.shape_equals_parser_shape"])
        self.assertFalse(checks["efficiency_estimate_invoked"])
        self.assertEqual(checks["correctness_policy_ref_status"], "reference_only_not_compare_evidence")

        closed = gate["accepted_fail_closed_behavior"]
        for status in ("not_ready_for_verilator_option_shim", "unsupported_for_stage_plan"):
            self.assertTrue(closed[status]["returns_structured_closed_result"])
            self.assertFalse(closed[status]["handoff_contract_metadata_allowed"])
            self.assertFalse(closed[status]["sidecar_handoff_contract_invoked"])
            self.assertTrue(closed[status]["handoff_contract_key_absent"])
        self.assertEqual(
            closed["malformed_or_inconsistent_ready_input"]["raises"],
            "NativeParserSidecarPlanResolutionError",
        )
        self.assertFalse(closed["malformed_or_inconsistent_ready_input"]["sidecar_handoff_contract_invoked_before_validation"])

    def test_review_records_tests_and_selects_operator_plan_boundary_definition(self) -> None:
        gate = self.read_gate()
        reviewed_tests = gate["reviewed_tests"]

        self.assertEqual(
            reviewed_tests["focused_fixture_test_command"],
            "python3 -m unittest tests.contract.test_verilator_native_option_parser_sidecar_plan_resolution_fixture -q",
        )
        self.assertEqual(reviewed_tests["focused_fixture_test_exit_code"], 0)
        self.assertEqual(reviewed_tests["focused_fixture_test_count"], 15)
        self.assertEqual(reviewed_tests["implementation_gate_test_exit_code"], 0)

        next_gate = gate["required_next_gate"]
        self.assertEqual(
            next_gate["name"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate",
        )
        self.assertIn(
            "whether a ready handoff-contract metadata result may feed synthesized Verilator command metadata",
            next_gate["must_define"],
        )
        self.assertIn(
            "tests that prove command/operator-plan production remains separate from RTL execution, compare execution, timing, runtime/ABI changes, arbitrary filelist expansion, and automatic allocation",
            next_gate["must_define"],
        )
        self.assertIn("operator-plan execution", next_gate["must_not_claim"])
        self.assertEqual(
            gate["next_task"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate",
        )

    def test_acceptance_policy_blocks_execution_timing_and_allocation_claims(self) -> None:
        gate = self.read_gate()
        policy = gate["acceptance_policy"]

        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["implementation_accepted"])
        self.assertTrue(policy["next_operator_plan_boundary_definition_allowed"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_contract_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["operator_plan_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertIn("not sidecar runtime handoff validation", gate["non_claims"])
        self.assertIn("not operator-plan production from native parser payload", gate["non_claims"])


if __name__ == "__main__":
    unittest.main()
