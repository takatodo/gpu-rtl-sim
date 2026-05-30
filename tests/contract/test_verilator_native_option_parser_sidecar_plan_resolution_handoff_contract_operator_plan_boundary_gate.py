import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractOperatorPlanBoundaryGateTest(
    unittest.TestCase
):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_definition_selects_review_and_limits_scope_to_metadata(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate",
        )
        decision = gate["definition_decision"]
        self.assertTrue(decision["defined"])
        self.assertIn("non-executing metadata", decision["weakest_point"])
        self.assertIn("estimate metadata separated from timing", decision["weakest_point"])

        authorities = gate["metadata_authorities"]
        self.assertFalse(authorities["definition_invokes_authorities"])
        self.assertTrue(authorities["metadata_only"])
        self.assertIn("synthesized_verilator_command_argv", authorities["command_argv_authority_for_future_helper"])
        self.assertIn("sidecar_operator_plan", authorities["operator_plan_authority_for_future_helper"])

    def test_ready_input_preconditions_require_accepted_handoff_metadata(self) -> None:
        gate = self.read_gate()
        preconditions = gate["eligible_handoff_contract_input_preconditions"]

        self.assertEqual(
            preconditions["surface"],
            "native_verilator_parser_sidecar_plan_resolution_handoff_contract_fixture",
        )
        self.assertEqual(preconditions["status"], "ready_for_sidecar_handoff_contract_metadata")
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
        self.assertTrue(preconditions["parser_schedule_cross_check.shape_matches_handoff_contract"])

    def test_required_fields_and_prepopulated_outputs_are_pinned(self) -> None:
        gate = self.read_gate()
        fields = gate["required_input_metadata_fields"]

        for field in ("surface", "status", "handoff_contract", "parser_schedule_cross_check"):
            self.assertIn(field, fields["top_level_fields"])
        for field in ("shape", "nstates", "steps", "state_files", "compare", "generated_reports"):
            self.assertIn(field, fields["handoff_contract_fields"])
        for field in ("init_state", "reference_dump", "candidate_dump"):
            self.assertIn(field, fields["handoff_contract_state_files"])
        for field in ("correctness_policy", "acceptance_policy", "coverage_output_target"):
            self.assertIn(field, fields["handoff_contract_compare_fields"])
        for forbidden in (
            "operator_plan",
            "command_argv",
            "verilator_command_argv",
            "estimate_command",
            "efficiency_estimate",
            "timing",
        ):
            self.assertIn(forbidden, fields["metadata_must_not_already_contain"])

    def test_future_output_marks_metadata_but_blocks_execution_claims(self) -> None:
        gate = self.read_gate()
        future = gate["future_operator_plan_metadata_shape"]

        self.assertEqual(future["surface"], "native_verilator_parser_sidecar_operator_plan_fixture")
        self.assertEqual(future["ready_status"], "ready_for_sidecar_operator_plan_metadata")
        for field in (
            "command_argv",
            "estimate_command",
            "efficiency_estimate",
            "handoff_contract",
            "operator_plan",
        ):
            self.assertIn(field, future["may_include_when_ready"])

        marks = future["must_mark"]
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
        self.assertIn("planning metadata only", future["estimate_metadata_boundary"])

    def test_closed_inputs_and_acceptance_policy_keep_next_gate_safe(self) -> None:
        gate = self.read_gate()
        closed = gate["closed_or_rejected_input_behavior"]

        self.assertFalse(closed["not_ready_for_sidecar_handoff_contract_metadata"]["operator_plan_metadata_allowed"])
        self.assertFalse(closed["unsupported_for_sidecar_handoff_contract_metadata"]["operator_plan_metadata_allowed"])
        self.assertFalse(closed["malformed_or_prepopulated_handoff_contract_metadata"]["operator_plan_metadata_allowed"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertTrue(policy["operator_plan_metadata_boundary_defined"])
        self.assertTrue(policy["future_importable_helper_allowed_after_review"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["command_synthesis_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["operator_plan_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertIn("not operator-plan execution", gate["non_claims"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate",
        )


if __name__ == "__main__":
    unittest.main()
