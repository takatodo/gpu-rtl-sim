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
REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_implementation_gate.json"
)
HARDENING_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json"
)
REVIEW_HARDENING_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json"
)
IMPLEMENT_HARDENING_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json"
)
REVIEW_IMPLEMENT_HARDENING_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_implementation_gate.json"
)
EXECUTION_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionHandoffContractOperatorPlanFixtureGateTest(
    unittest.TestCase
):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def read_review_gate(self) -> dict[str, object]:
        return json.loads(REVIEW_GATE.read_text(encoding="utf-8"))

    def read_hardening_gate(self) -> dict[str, object]:
        return json.loads(HARDENING_GATE.read_text(encoding="utf-8"))

    def read_review_hardening_gate(self) -> dict[str, object]:
        return json.loads(REVIEW_HARDENING_GATE.read_text(encoding="utf-8"))

    def read_implement_hardening_gate(self) -> dict[str, object]:
        return json.loads(IMPLEMENT_HARDENING_GATE.read_text(encoding="utf-8"))

    def read_review_implement_hardening_gate(self) -> dict[str, object]:
        return json.loads(REVIEW_IMPLEMENT_HARDENING_GATE.read_text(encoding="utf-8"))

    def read_execution_boundary_gate(self) -> dict[str, object]:
        return json.loads(EXECUTION_BOUNDARY_GATE.read_text(encoding="utf-8"))

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

    def test_review_gate_accepts_metadata_only_fixture(self) -> None:
        review = self.read_review_gate()

        self.assertEqual(
            review["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate",
        )
        implementation = review["accepted_implementation"]
        self.assertEqual(implementation["module"], "src/tools/verilator_native_option_parser_sidecar_operator_plan.py")
        self.assertEqual(implementation["primary_entrypoint_function"], "resolve_handoff_contract_to_operator_plan")
        self.assertTrue(implementation["ready_only"])
        self.assertTrue(implementation["metadata_only"])
        self.assertFalse(implementation["new_public_cli_added"])
        self.assertFalse(implementation["new_execution_added"])
        self.assertTrue(implementation["line_guard_compliant"])
        self.assertFalse(implementation["complete_adversarial_mapping_schema_validation"])

    def test_review_gate_keeps_hardening_boundary_open(self) -> None:
        review = self.read_review_gate()
        metadata = review["accepted_ready_metadata"]

        self.assertTrue(metadata["command_synthesis_invoked"])
        self.assertTrue(metadata["operator_plan_invoked"])
        self.assertTrue(metadata["efficiency_estimate_invoked"])
        self.assertFalse(metadata["execution_performed"])
        self.assertFalse(metadata["measurement_performed"])
        self.assertFalse(metadata["timing_measured"])
        self.assertFalse(metadata["runtime_or_abi_changed"])
        self.assertFalse(metadata["source_closure_inferred"])
        self.assertFalse(metadata["filelists_expanded"])
        self.assertFalse(metadata["automatic_gpu_allocation_used"])
        self.assertIn("not new measured timing", metadata["estimate_metadata_boundary"])
        gaps = review["known_hardening_gaps"]
        self.assertTrue(gaps["bool_is_not_rejected_by_positive_int_checks"])
        self.assertFalse(gaps["adversarial_mapping_schema_validation_complete"])
        self.assertTrue(gaps["efficiency_estimate_object_may_reference_existing_reports"])
        self.assertFalse(gaps["efficiency_estimate_new_timing_evidence_allowed"])
        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate",
        )
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["next_execution_boundary_definition_allowed"])
        self.assertFalse(review["acceptance_policy"]["operator_plan_execution_claim_allowed_by_gate_alone"])
        self.assertIn("not operator-plan execution", review["non_claims"])
        self.assertIn("not complete adversarial Mapping schema validation", review["non_claims"])

    def test_hardening_gate_defines_bool_and_mapping_scope(self) -> None:
        gate = self.read_hardening_gate()

        self.assertEqual(
            gate["source_fixture_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate",
        )
        hardening = gate["positive_integer_hardening"]
        self.assertEqual(
            hardening["existing_helper"],
            "src/tools/verilator_native_option_parser_sidecar_operator_plan.py::_positive_int",
        )
        self.assertFalse(hardening["required_rejection"]["true_allowed"])
        self.assertFalse(hardening["required_rejection"]["false_allowed"])
        self.assertFalse(hardening["required_rejection"]["zero_allowed"])
        self.assertFalse(hardening["required_rejection"]["negative_allowed"])
        field_paths = {item["field_path"] for item in hardening["required_fields"]}
        self.assertEqual(
            field_paths,
            {
                "handoff_contract.nstates",
                "handoff_contract.steps",
                "stage_plan.phases",
                "stage_plan.limit",
                "stage_plan.stages[hybrid_sidecar_run].details.nstates",
                "stage_plan.stages[hybrid_sidecar_run].details.steps",
                "parser_schedule_cross_check.state_count",
                "parser_schedule_cross_check.step_count",
            },
        )

        mapping = gate["malformed_mapping_boundary"]
        self.assertFalse(mapping["complete_adversarial_mapping_schema_validation_required"])
        self.assertIn(
            "bool nstates, steps, phases, limit, hybrid_sidecar_run nstates/steps, or parser_schedule_cross_check counts",
            mapping["must_fail_before_authorities"],
        )
        self.assertIn(
            "src/tools/hybrid_benchmark_efficiency.py::efficiency_estimate",
            mapping["authorities_that_must_not_be_called_before_validation"],
        )
        self.assertIn("complete arbitrary Mapping schema validation", mapping["explicitly_not_required"])

    def test_hardening_gate_keeps_estimate_and_execution_non_claims(self) -> None:
        gate = self.read_hardening_gate()
        estimate = gate["efficiency_estimate_boundary"]

        self.assertEqual(estimate["metadata_status"], "non_executing_planning_metadata")
        self.assertTrue(estimate["existing_report_values_allowed_as_references"])
        self.assertFalse(estimate["new_timing_or_speedup_evidence_allowed"])
        self.assertIn("not new measured timing", estimate["required_output_wording"])
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate",
        )
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertFalse(policy["implementation_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["next_execution_boundary_definition_allowed"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["complete_adversarial_mapping_schema_validation_claim_allowed_by_gate_alone"])
        self.assertIn("not timing or speedup evidence", gate["non_claims"])
        self.assertIn("not complete adversarial Mapping schema validation", gate["non_claims"])

    def test_hardening_review_accepts_definition_and_selects_implementation(self) -> None:
        review = self.read_review_hardening_gate()

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("phase/limit wording is weaker", review["review_decision"]["weakest_point"])
        self.assertEqual(
            review["current_priority"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate",
        )
        accepted = review["accepted_definition"]
        self.assertEqual(
            accepted["primary_module"],
            "src/tools/verilator_native_option_parser_sidecar_operator_plan.py",
        )
        self.assertFalse(accepted["bool_values_are_positive_ints"])
        self.assertFalse(accepted["complete_adversarial_mapping_schema_validation_required"])
        self.assertFalse(accepted["new_timing_or_speedup_evidence_allowed"])
        self.assertEqual(
            review["required_next_implementation"]["name"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate",
        )

    def test_hardening_review_requires_all_authorities_before_phase_limit_bool(self) -> None:
        review = self.read_review_hardening_gate()
        required = review["required_next_implementation"]

        self.assertIn(
            "reject bool stage_plan.phases and stage_plan.limit before command, estimate, efficiency, or operator-plan authorities",
            required["must_implement"],
        )
        self.assertIn(
            "bool stage_plan.phases rejects before command, estimate, efficiency, or operator-plan authorities",
            required["must_test"],
        )
        self.assertIn(
            "bool stage_plan.limit rejects before command, estimate, efficiency, or operator-plan authorities",
            required["must_test"],
        )
        mapping = review["accepted_scoped_mapping_boundary"]
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["next_execution_boundary_definition_allowed"])
        self.assertIn(
            "src/tools/hybrid_benchmark_sidecar_operator.py::synthesized_verilator_command_argv",
            mapping["authorities_that_must_not_be_called_before_validation"],
        )
        self.assertIn(
            "not complete adversarial Mapping schema validation",
            review["non_claims"],
        )

    def test_hardening_implementation_records_strict_integer_scope(self) -> None:
        gate = self.read_implement_hardening_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_implementation_gate",
        )
        surface = gate["implemented_surface"]
        self.assertEqual(surface["module"], "src/tools/verilator_native_option_parser_sidecar_operator_plan.py")
        self.assertEqual(surface["primary_entrypoint_function"], "resolve_handoff_contract_to_operator_plan")
        self.assertTrue(surface["ready_only"])
        self.assertTrue(surface["metadata_only"])
        self.assertFalse(surface["new_public_cli_added"])
        self.assertFalse(surface["new_execution_added"])
        self.assertLessEqual(surface["line_count_after_change"], 300)

        hardening = gate["implemented_hardening"]
        self.assertTrue(hardening["positive_int_helper_rejects_bool"])
        self.assertTrue(hardening["optional_int_helper_rejects_bool"])
        self.assertTrue(hardening["stage_plan_phase_and_limit_validated_before_authorities"])
        self.assertTrue(hardening["hybrid_sidecar_run_details_validated_before_command_builder"])
        self.assertTrue(hardening["parser_schedule_cross_check_counts_validated_before_equality_comparison"])
        self.assertFalse(hardening["complete_adversarial_mapping_schema_validation_added"])

    def test_hardening_implementation_records_verification_and_non_claims(self) -> None:
        gate = self.read_implement_hardening_gate()

        self.assertEqual(gate["verification"]["focused_contract_test_exit_code"], 0)
        self.assertEqual(gate["verification"]["focused_contract_test_count"], 21)
        self.assertEqual(gate["verification"]["bool_field_subtest_count"], 8)
        self.assertEqual(
            set(gate["verification"]["counting_stub_authorities"]),
            {"command_builder", "estimate_command_builder", "efficiency_builder", "operator_plan_builder"},
        )
        ordering = gate["authority_ordering"]
        self.assertTrue(ordering["bool_rejection_before_command_builder"])
        self.assertTrue(ordering["bool_rejection_before_estimate_command_builder"])
        self.assertTrue(ordering["bool_rejection_before_efficiency_builder"])
        self.assertTrue(ordering["bool_rejection_before_operator_plan_builder"])
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["next_execution_boundary_definition_allowed"])
        self.assertFalse(gate["acceptance_policy"]["complete_adversarial_mapping_schema_validation_claim_allowed_by_gate_alone"])
        self.assertIn("not command execution", gate["non_claims"])
        self.assertIn("not complete adversarial Mapping schema validation", gate["non_claims"])

    def test_hardening_implementation_review_accepts_strict_metadata_boundary(self) -> None:
        review = self.read_review_implement_hardening_gate()

        self.assertEqual(
            review["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate",
        )
        accepted = review["accepted_hardening"]
        self.assertTrue(accepted["positive_int_helper_rejects_bool"])
        self.assertTrue(accepted["optional_int_helper_rejects_bool"])
        self.assertTrue(accepted["stage_plan_phases_validated_before_authorities"])
        self.assertTrue(accepted["stage_plan_limit_validated_before_authorities"])
        self.assertTrue(accepted["hybrid_sidecar_run_details_validated_before_command_builder"])
        self.assertTrue(accepted["parser_schedule_cross_check_counts_validated_before_equality_comparison"])
        self.assertIn("stage_plan.limit", accepted["strict_integer_fields"])

    def test_hardening_implementation_review_allows_definition_only_execution_boundary(self) -> None:
        review = self.read_review_implement_hardening_gate()

        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate",
        )
        policy = review["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["implementation_accepted"])
        self.assertTrue(policy["next_execution_boundary_definition_allowed"])
        self.assertTrue(policy["next_gate_must_be_definition_only"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["arbitrary_filelist_support_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertIn("not command execution", review["non_claims"])
        self.assertIn("not coverage-output equivalence for a native-parser flow", review["non_claims"])

    def test_execution_boundary_definition_selects_review_without_execution(self) -> None:
        gate = self.read_execution_boundary_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate",
        )
        decision = gate["definition_decision"]
        self.assertTrue(decision["defined"])
        self.assertEqual(
            decision["selected_surface"],
            "native_parser_operator_plan_metadata_to_reviewed_sidecar_execution_boundary",
        )
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertTrue(policy["execution_boundary_defined"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_execution_boundary_definition_requires_reviewed_stage_plan_before_run(self) -> None:
        gate = self.read_execution_boundary_gate()
        boundary = gate["future_execution_boundary"]

        self.assertTrue(boundary["definition_only"])
        self.assertFalse(boundary["execution_allowed_by_this_gate"])
        self.assertEqual(
            boundary["required_stage_order_for_future_run"],
            [
                "verilator_build",
                "host_probe_build",
                "cpu_init_state",
                "cpu_reference_output",
                "gpu_artifact_build",
                "hybrid_sidecar_run",
                "coverage_output_compare",
            ],
        )
        self.assertIn("not by itself sidecar runtime execution", boundary["direct_verilator_command_status"])
        self.assertIn("not sufficient authority", boundary["stage_plan_source_requirement"])
        self.assertIn("future compare result", boundary["coverage_output_equivalence_status"])
        roles = gate["required_ready_metadata_fields"]["parser_preserved_build_inputs_role"]
        self.assertEqual(roles["source_files"], "preserved_parser_input_not_source_closure")
        self.assertEqual(roles["filelists"], "preserved_parser_input_not_filelist_expansion")
        self.assertIn(
            "not coverage-output equivalence for a native-parser flow",
            gate["non_claims"],
        )


if __name__ == "__main__":
    unittest.main()
