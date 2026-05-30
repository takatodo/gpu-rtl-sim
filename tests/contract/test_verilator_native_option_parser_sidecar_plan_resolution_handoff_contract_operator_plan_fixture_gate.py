import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractOperatorPlanFixtureGateTest(
    unittest.TestCase
):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_gate_records_importable_operator_plan_fixture(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_implementation_gate",
        )
        surface = gate["implemented_surface"]
        self.assertEqual(surface["module"], "src/tools/verilator_native_option_parser_sidecar_operator_plan.py")
        self.assertEqual(surface["primary_entrypoint_function"], "resolve_handoff_contract_to_operator_plan")
        self.assertEqual(
            surface["wrapper_entrypoint_function"],
            "resolve_native_parser_handoff_contract_to_sidecar_operator_plan",
        )
        self.assertTrue(surface["ready_only"])
        self.assertTrue(surface["metadata_only"])
        self.assertFalse(surface["new_public_cli_added"])
        self.assertFalse(surface["new_execution_added"])
        self.assertFalse(surface["new_measurement_added"])

    def test_ready_checks_precede_command_and_operator_authorities(self) -> None:
        gate = self.read_gate()
        checks = gate["implemented_ready_checks"]

        self.assertEqual(checks["surface"], "native_verilator_parser_sidecar_plan_resolution_handoff_contract_fixture")
        self.assertEqual(checks["status"], "ready_for_sidecar_handoff_contract_metadata")
        self.assertEqual(checks["input_status"], "ready_for_verilator_option_shim")
        self.assertTrue(checks["sidecar_handoff_contract_invoked"])
        self.assertFalse(checks["command_synthesis_invoked"])
        self.assertFalse(checks["operator_plan_invoked"])
        self.assertFalse(checks["efficiency_estimate_invoked"])
        self.assertFalse(checks["execution_performed"])
        self.assertFalse(checks["measurement_performed"])
        self.assertFalse(checks["timing_measured"])
        self.assertFalse(checks["runtime_or_abi_changed"])
        self.assertFalse(checks["source_closure_inferred"])
        self.assertFalse(checks["filelists_expanded"])
        self.assertFalse(checks["automatic_gpu_allocation_used"])
        self.assertEqual(checks["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(checks["correctness_policy_ref_status"], "reference_only_not_compare_evidence")
        self.assertTrue(checks["parser_schedule_cross_check.shape_matches_handoff_contract"])
        self.assertTrue(checks["plan_resolution_readiness.ready_for_direct_verilator_option"])
        self.assertEqual(checks["stage_plan.status"], "planned")
        self.assertEqual(checks["stage_plan.verilator_option_readiness.status"], "ready_for_verilator_option_shim")
        for field in ("command_argv", "estimate_command", "efficiency_estimate", "operator_plan", "timing"):
            self.assertIn(field, checks["forbidden_prepopulated_fields"])

    def test_output_shape_is_non_executing_metadata_only(self) -> None:
        gate = self.read_gate()
        output = gate["implemented_output_shape"]

        self.assertEqual(output["surface"], "native_verilator_parser_sidecar_operator_plan_fixture")
        self.assertEqual(output["ready_status"], "ready_for_sidecar_operator_plan_metadata")
        for field in (
            "command_argv",
            "command",
            "estimate_command_argv",
            "estimate_command",
            "efficiency_estimate",
            "handoff_contract",
            "operator_plan",
        ):
            self.assertIn(field, output["ready_metadata"])

        flags = output["ready_flags"]
        self.assertTrue(flags["command_synthesis_invoked"])
        self.assertTrue(flags["operator_plan_invoked"])
        self.assertTrue(flags["efficiency_estimate_invoked"])
        self.assertFalse(flags["execution_performed"])
        self.assertFalse(flags["measurement_performed"])
        self.assertFalse(flags["timing_measured"])
        self.assertFalse(flags["runtime_or_abi_changed"])
        self.assertFalse(flags["source_closure_inferred"])
        self.assertFalse(flags["filelists_expanded"])
        self.assertFalse(flags["automatic_gpu_allocation_used"])
        self.assertIn("not measured timing", output["estimate_metadata_boundary"])

    def test_fail_closed_and_verification_records_review_next(self) -> None:
        gate = self.read_gate()
        fail_closed = gate["implemented_fail_closed_behavior"]

        for status in (
            "not_ready_for_sidecar_handoff_contract_metadata",
            "unsupported_for_sidecar_handoff_contract_metadata",
        ):
            self.assertTrue(fail_closed[status]["returns_structured_closed_result"])
            self.assertFalse(fail_closed[status]["operator_plan_metadata_allowed"])
            self.assertFalse(fail_closed[status]["command_authorities_called"])

        malformed = fail_closed["malformed_or_prepopulated_handoff_contract_metadata"]
        self.assertEqual(malformed["raises"], "NativeParserSidecarPlanResolutionError")
        self.assertFalse(malformed["command_authorities_called_before_validation"])
        self.assertFalse(malformed["efficiency_estimate_called_before_validation"])
        self.assertFalse(malformed["operator_plan_called_before_validation"])

        verification = gate["verification"]
        self.assertEqual(
            verification["focused_contract_test_command"],
            "python3 -m unittest tests.contract.test_verilator_native_option_parser_sidecar_plan_resolution_fixture -q",
        )
        self.assertEqual(verification["focused_contract_test_exit_code"], 0)
        self.assertEqual(verification["focused_contract_test_count"], 20)
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_implementation_gate",
        )

    def test_acceptance_policy_blocks_overclaims(self) -> None:
        gate = self.read_gate()
        policy = gate["acceptance_policy"]

        self.assertTrue(policy["implementation_only"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_validation_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["operator_plan_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["arbitrary_filelist_support_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertIn("not operator-plan execution", gate["non_claims"])
        self.assertIn("not timing or speedup evidence", gate["non_claims"])


if __name__ == "__main__":
    unittest.main()
