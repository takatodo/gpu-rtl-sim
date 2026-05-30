import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractBoundaryReviewGateTest(
    unittest.TestCase
):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_definition_and_selects_fixture_implementation(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("metadata construction", gate["review_decision"]["reason"])
        self.assertIn("over-read as sidecar runtime handoff validation", gate["review_decision"]["weakest_point"])
        self.assertEqual(
            gate["next_task"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate",
        )

    def test_review_boundary_keeps_handoff_contract_metadata_non_executing(self) -> None:
        gate = self.read_gate()
        boundary = gate["accepted_boundary"]

        self.assertEqual(
            boundary["input_authority"],
            "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py::resolve_native_parser_adapter_payload_to_sidecar_plan",
        )
        self.assertEqual(
            boundary["metadata_authority"],
            "src/tools/hybrid_benchmark_sidecar_operator.py::sidecar_handoff_contract",
        )
        self.assertTrue(boundary["metadata_only"])
        self.assertTrue(boundary["ready_only"])
        self.assertFalse(boundary["runtime_handoff_execution"])
        self.assertFalse(boundary["command_synthesis"])
        self.assertFalse(boundary["operator_plan"])
        self.assertFalse(boundary["execution"])
        self.assertFalse(boundary["measurement"])
        self.assertFalse(boundary["runtime_or_abi_change"])
        self.assertFalse(boundary["arbitrary_filelist_expansion"])
        self.assertFalse(boundary["automatic_gpu_allocation"])

    def test_review_pins_ready_only_preconditions(self) -> None:
        gate = self.read_gate()
        preconditions = gate["accepted_ready_preconditions"]

        self.assertEqual(preconditions["surface"], "native_verilator_parser_sidecar_plan_resolution_fixture")
        self.assertEqual(preconditions["status"], "ready_for_verilator_option_shim")
        self.assertTrue(preconditions["plan_resolution_readiness.ready_for_direct_verilator_option"])
        self.assertEqual(preconditions["plan_resolution_readiness.stage_plan_status"], "planned")
        self.assertEqual(
            preconditions["plan_resolution_readiness.verilator_option_readiness_status"],
            "ready_for_verilator_option_shim",
        )
        self.assertEqual(preconditions["stage_plan.status"], "planned")
        self.assertEqual(
            preconditions["stage_plan.verilator_option_readiness.status"],
            "ready_for_verilator_option_shim",
        )
        self.assertTrue(preconditions["parser_schedule_constraints.shape_equals_stage_plan.shape"])
        self.assertEqual(preconditions["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(preconditions["correctness_policy_ref_status"], "reference_only_not_compare_evidence")

    def test_review_requires_not_ready_and_unsupported_outputs_to_fail_closed(self) -> None:
        gate = self.read_gate()
        behavior = gate["accepted_fail_closed_behavior"]

        not_ready = behavior["not_ready_for_verilator_option_shim"]
        self.assertFalse(not_ready["handoff_contract_metadata_allowed"])
        self.assertIn("plan_resolution_readiness.not_ready_reason", not_ready["must_preserve"])
        self.assertIn("plan_resolution_readiness.missing_readiness_inputs", not_ready["must_preserve"])
        self.assertIn("stage_plan.status", not_ready["must_preserve"])

        unsupported = behavior["unsupported_for_stage_plan"]
        self.assertFalse(unsupported["handoff_contract_metadata_allowed"])
        self.assertIn("plan_resolution_readiness.not_ready_reason", unsupported["must_preserve"])
        self.assertIn("stage_plan.status", unsupported["must_preserve"])

    def test_next_implementation_scope_is_existing_helper_without_cli_or_execution(self) -> None:
        gate = self.read_gate()
        implementation = gate["required_next_implementation"]

        self.assertEqual(
            implementation["name"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate",
        )
        self.assertEqual(
            implementation["allowed_primary_module"],
            "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py",
        )
        for required in (
            "add an importable helper in the existing plan-resolution module that consumes a resolved plan-resolution mapping",
            "reject results whose outer status is not ready_for_verilator_option_shim",
            "reject results whose parser_schedule_constraints.shape does not equal stage_plan.shape",
            "call sidecar_handoff_contract(stage_plan) only after all ready-only checks pass",
        ):
            self.assertIn(required, implementation["must_implement"])

        for forbidden in (
            "add a new public CLI",
            "call synthesized_verilator_command_argv",
            "call sidecar_operator_plan",
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

    def test_acceptance_policy_and_non_claims_block_overclaims(self) -> None:
        gate = self.read_gate()
        policy = gate["acceptance_policy"]

        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["definition_accepted"])
        self.assertTrue(policy["next_handoff_contract_fixture_implementation_allowed"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_handoff_validation_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_contract_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["operator_plan_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

        self.assertIn("not sidecar runtime handoff validation", gate["non_claims"])
        self.assertIn("not operator-plan production from native parser payload", gate["non_claims"])
        self.assertIn("not automatic optimal GPU allocation for any design", gate["non_claims"])


if __name__ == "__main__":
    unittest.main()
