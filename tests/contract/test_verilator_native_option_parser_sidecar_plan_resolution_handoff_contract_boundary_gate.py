import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractBoundaryGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_definition_uses_status_hardening_review_and_selects_review_next(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate",
        )
        self.assertTrue(gate["definition_decision"]["defined"])
        self.assertIn("metadata object", gate["definition_decision"]["weakest_point"])

        next_gate = gate["required_next_gate"]
        self.assertEqual(
            next_gate["name"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate",
        )
        self.assertIn(
            "whether ready-only metadata construction is the correct next boundary after status hardening",
            next_gate["must_decide"],
        )

    def test_boundary_separates_metadata_from_runtime_execution_and_commands(self) -> None:
        gate = self.read_gate()
        authority = gate["handoff_contract_metadata_authority"]

        self.assertEqual(
            authority["existing_authority"],
            "src/tools/hybrid_benchmark_sidecar_operator.py::sidecar_handoff_contract",
        )
        self.assertEqual(
            authority["input_authority"],
            "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py::resolve_native_parser_adapter_payload_to_sidecar_plan",
        )
        self.assertTrue(authority["metadata_only"])
        self.assertFalse(authority["runtime_handoff_execution"])
        self.assertIn("sidecar_operator_plan", authority["operator_plan_authority_not_invoked_by_this_boundary"])
        self.assertIn(
            "synthesized_verilator_command_argv",
            authority["command_synthesis_authority_not_invoked_by_this_boundary"],
        )

    def test_ready_preconditions_require_readiness_not_stage_plan_alone(self) -> None:
        gate = self.read_gate()
        preconditions = gate["eligible_plan_resolution_preconditions"]

        self.assertEqual(preconditions["surface"], "native_verilator_parser_sidecar_plan_resolution_fixture")
        self.assertEqual(preconditions["top_level_status"], "ready_for_verilator_option_shim")
        self.assertTrue(preconditions["plan_resolution_readiness.ready_for_direct_verilator_option"])
        self.assertEqual(preconditions["plan_resolution_readiness.stage_plan_status"], "planned")
        self.assertEqual(
            preconditions["plan_resolution_readiness.verilator_option_readiness_status"],
            "ready_for_verilator_option_shim",
        )
        self.assertEqual(preconditions["stage_plan.status"], "planned")
        self.assertEqual(preconditions["stage_plan.verilator_option_readiness.status"], "ready_for_verilator_option_shim")
        self.assertTrue(preconditions["sidecar_stage_plan_invoked"])
        self.assertFalse(preconditions["sidecar_handoff_contract_invoked"])
        self.assertFalse(preconditions["command_synthesis_invoked"])
        self.assertFalse(preconditions["operator_plan_invoked"])
        self.assertFalse(preconditions["execution_performed"])
        self.assertFalse(preconditions["measurement_performed"])
        self.assertTrue(preconditions["parser_schedule_constraints.shape_equals_stage_plan.shape"])
        self.assertEqual(preconditions["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(preconditions["correctness_policy_ref_status"], "reference_only_not_compare_evidence")

    def test_minimal_fields_and_authority_split_keep_parser_from_inference(self) -> None:
        gate = self.read_gate()
        fields = gate["minimal_plan_resolution_fields_for_future_helper"]

        for field in (
            "status",
            "plan_resolution_readiness",
            "stage_plan",
            "sidecar_context",
            "parser_schedule_constraints",
            "correctness_policy",
        ):
            self.assertIn(field, fields["resolution_top_level_fields"])
        self.assertEqual(fields["required_stage_plan_stages"], ["hybrid_sidecar_run", "coverage_output_compare"])
        for field in ("nstates", "steps", "init_state"):
            self.assertIn(field, fields["required_hybrid_run_detail_fields"])
        for field in (
            "reference_dump",
            "candidate_dump",
            "acceptance_policy",
            "reference_label",
            "candidate_label",
            "coverage_output_target",
            "json_out",
        ):
            self.assertIn(field, fields["required_compare_detail_fields"])

        split = gate["authority_split"]
        self.assertIn("shape", split["parser_owned_inputs_remain"])
        self.assertIn("source_files", split["parser_owned_inputs_remain"])
        self.assertIn("coverage_output_target", split["sidecar_owned_fields_remain"])
        self.assertIn("host_probe_build_metadata_ref", split["sidecar_owned_fields_remain"])
        self.assertIn("source closure", split["parser_must_not_infer"])
        self.assertIn("automatic GPU allocation", split["parser_must_not_infer"])

    def test_not_ready_and_unsupported_outputs_do_not_produce_handoff_metadata(self) -> None:
        gate = self.read_gate()
        behavior = gate["not_ready_and_unsupported_behavior"]

        self.assertFalse(behavior["not_ready_for_verilator_option_shim"]["handoff_contract_metadata_allowed"])
        self.assertEqual(
            behavior["not_ready_for_verilator_option_shim"]["example_stage_plan_status"],
            "planned_not_ready_for_verilator_option_shim",
        )
        self.assertFalse(behavior["unsupported_for_stage_plan"]["handoff_contract_metadata_allowed"])
        self.assertEqual(
            behavior["unsupported_for_stage_plan"]["example_stage_plan_status"],
            "unsupported_for_stage_plan",
        )

    def test_definition_keeps_execution_operator_plan_and_allocation_out_of_scope(self) -> None:
        gate = self.read_gate()
        prohibited = gate["prohibited_by_this_definition"]

        self.assertFalse(prohibited["new_public_cli"])
        self.assertFalse(prohibited["call_synthesized_verilator_command_argv"])
        self.assertFalse(prohibited["call_sidecar_operator_plan"])
        self.assertFalse(prohibited["execute_runtime_handoff"])
        self.assertFalse(prohibited["execute_rtl_simulation"])
        self.assertFalse(prohibited["run_coverage_output_compare"])
        self.assertFalse(prohibited["measure_timing"])
        self.assertFalse(prohibited["change_runtime_or_abi"])
        self.assertFalse(prohibited["expand_arbitrary_filelists"])
        self.assertFalse(prohibited["automatic_gpu_allocation"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertTrue(policy["metadata_boundary_defined"])
        self.assertTrue(policy["handoff_contract_metadata_allowed_by_future_gate_only"])
        self.assertFalse(policy["runtime_handoff_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["operator_plan_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate",
        )


if __name__ == "__main__":
    unittest.main()
