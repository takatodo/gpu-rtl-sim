import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractOperatorPlanBoundaryReviewGateTest(
    unittest.TestCase
):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_definition_and_selects_fixture_implementation(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("planning metadata", gate["review_decision"]["reason"])
        self.assertIn("efficiency_estimate metadata", gate["review_decision"]["weakest_point"])
        self.assertIn("must not execute generated commands", gate["review_decision"]["weakest_point"])
        self.assertEqual(
            gate["next_task"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_gate",
        )

    def test_accepted_boundary_is_metadata_only_and_non_executing(self) -> None:
        gate = self.read_gate()
        boundary = gate["accepted_boundary"]

        self.assertEqual(
            boundary["selected_surface"],
            "native_parser_handoff_contract_to_sidecar_operator_plan_metadata_boundary",
        )
        self.assertIn("synthesized_verilator_command_argv", boundary["command_argv_authority"])
        self.assertIn("synthesized_verilator_estimate_command_argv", boundary["estimate_command_argv_authority"])
        self.assertIn("sidecar_operator_plan", boundary["operator_plan_authority"])
        self.assertIn("efficiency_estimate", boundary["efficiency_estimate_authority"])
        self.assertTrue(boundary["metadata_only"])
        self.assertTrue(boundary["ready_only"])
        self.assertTrue(boundary["command_synthesis_metadata"])
        self.assertTrue(boundary["estimate_command_metadata"])
        self.assertTrue(boundary["efficiency_estimate_metadata"])
        self.assertTrue(boundary["operator_plan_metadata"])
        self.assertFalse(boundary["execute_command_argv"])
        self.assertFalse(boundary["execute_estimate_command"])
        self.assertFalse(boundary["execute_operator_plan"])
        self.assertFalse(boundary["execute_runtime_handoff"])
        self.assertFalse(boundary["execute_rtl_simulation"])
        self.assertFalse(boundary["run_coverage_output_compare"])
        self.assertFalse(boundary["measurement"])
        self.assertFalse(boundary["timing"])
        self.assertFalse(boundary["automatic_gpu_allocation"])

    def test_review_pins_ready_handoff_contract_input_preconditions(self) -> None:
        gate = self.read_gate()
        preconditions = gate["accepted_input_preconditions"]

        self.assertEqual(
            preconditions["surface"],
            "native_verilator_parser_sidecar_plan_resolution_handoff_contract_fixture",
        )
        self.assertEqual(preconditions["status"], "ready_for_sidecar_handoff_contract_metadata")
        self.assertEqual(preconditions["input_status"], "ready_for_verilator_option_shim")
        self.assertTrue(preconditions["sidecar_handoff_contract_invoked"])
        self.assertFalse(preconditions["command_synthesis_invoked"])
        self.assertFalse(preconditions["operator_plan_invoked"])
        self.assertFalse(preconditions["efficiency_estimate_invoked"])
        self.assertFalse(preconditions["execution_performed"])
        self.assertFalse(preconditions["measurement_performed"])
        self.assertFalse(preconditions["timing_measured"])
        self.assertFalse(preconditions["runtime_or_abi_changed"])
        self.assertFalse(preconditions["source_closure_inferred"])
        self.assertFalse(preconditions["filelists_expanded"])
        self.assertFalse(preconditions["automatic_gpu_allocation_used"])
        self.assertEqual(preconditions["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(preconditions["correctness_policy_ref_status"], "reference_only_not_compare_evidence")

    def test_future_output_shape_marks_metadata_without_timing_claim(self) -> None:
        gate = self.read_gate()
        output = gate["accepted_future_output_shape"]

        self.assertEqual(output["surface"], "native_verilator_parser_sidecar_operator_plan_fixture")
        self.assertEqual(output["ready_status"], "ready_for_sidecar_operator_plan_metadata")
        for field in (
            "command_argv",
            "estimate_command",
            "efficiency_estimate",
            "handoff_contract",
            "operator_plan",
        ):
            self.assertIn(field, output["required_ready_metadata"])

        marks = output["must_mark"]
        self.assertTrue(marks["command_synthesis_invoked"])
        self.assertTrue(marks["operator_plan_invoked"])
        self.assertTrue(marks["efficiency_estimate_invoked"])
        self.assertFalse(marks["execution_performed"])
        self.assertFalse(marks["measurement_performed"])
        self.assertFalse(marks["timing_measured"])
        self.assertFalse(marks["runtime_or_abi_changed"])
        self.assertFalse(marks["source_closure_inferred"])
        self.assertFalse(marks["filelists_expanded"])
        self.assertFalse(marks["automatic_gpu_allocation_used"])
        self.assertIn("not be presented as measured timing", output["estimate_metadata_boundary"])

    def test_rejection_behavior_blocks_authority_calls_before_metadata_construction(self) -> None:
        gate = self.read_gate()
        behavior = gate["accepted_rejection_behavior"]

        for status in ("closed_handoff_contract_metadata", "unsupported_handoff_contract_metadata"):
            self.assertFalse(behavior[status]["operator_plan_metadata_allowed"])
            self.assertFalse(behavior[status]["command_authorities_allowed"])
            self.assertIn("status", behavior[status]["must_preserve"])
            self.assertIn("plan_resolution_readiness", behavior[status]["must_preserve"])

        prepopulated = behavior["malformed_or_prepopulated_handoff_contract_metadata"]
        self.assertFalse(prepopulated["operator_plan_metadata_allowed"])
        self.assertFalse(prepopulated["command_authorities_allowed"])
        for authority in (
            "synthesized_verilator_command_argv",
            "synthesized_verilator_estimate_command_argv",
            "efficiency_estimate",
            "sidecar_operator_plan",
        ):
            self.assertIn(authority, prepopulated["must_raise_before"])

    def test_next_implementation_is_importable_helper_without_cli_or_execution(self) -> None:
        gate = self.read_gate()
        implementation = gate["required_next_implementation"]

        self.assertEqual(
            implementation["name"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_gate",
        )
        self.assertEqual(
            implementation["allowed_primary_module"],
            "src/tools/verilator_native_option_parser_sidecar_operator_plan.py",
        )
        self.assertIn(
            "add an importable helper that consumes handoff-contract fixture metadata",
            implementation["must_implement"],
        )
        self.assertIn(
            "call synthesized_verilator_command_argv, synthesized_verilator_estimate_command_argv, efficiency_estimate, and sidecar_operator_plan only after all ready-only checks pass",
            implementation["must_implement"],
        )

        for forbidden in (
            "add a new public CLI",
            "execute synthesized command argv",
            "execute estimate command",
            "execute operator plan",
            "execute runtime handoff",
            "execute RTL simulation",
            "run coverage-output compare",
            "measure timing",
            "change runtime or ABI",
            "infer source closure",
            "expand arbitrary filelists",
            "perform automatic GPU allocation",
        ):
            self.assertIn(forbidden, implementation["must_not_do"])

    def test_acceptance_policy_blocks_overclaims(self) -> None:
        gate = self.read_gate()
        policy = gate["acceptance_policy"]

        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["definition_accepted"])
        self.assertTrue(policy["next_operator_plan_fixture_implementation_allowed"])
        self.assertTrue(policy["efficiency_estimate_metadata_allowed"])
        self.assertFalse(policy["efficiency_estimate_timing_claim_allowed"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["operator_plan_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertIn("not timing or speedup evidence", gate["non_claims"])
        self.assertIn("not operator-plan execution", gate["non_claims"])


if __name__ == "__main__":
    unittest.main()
