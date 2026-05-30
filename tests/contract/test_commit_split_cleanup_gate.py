import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "config" / "scaling_gates" / "define_commit_split_and_public_pack_cleanup_gate.json"
REVIEW_GATE = REPO_ROOT / "config" / "scaling_gates" / "review_commit_split_and_public_pack_cleanup_gate.json"
RESOLUTION_GATE = REPO_ROOT / "config" / "scaling_gates" / "resolve_commit_split_line_guard_risks_gate.json"
COMPLETION_GATE = REPO_ROOT / "config" / "scaling_gates" / "execute_commit_split_index_rewrite_gate.json"
PARSER_BOUNDARY_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "define_verilator_native_option_parser_boundary_gate.json"
)
PARSER_BOUNDARY_REVIEW_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "review_verilator_native_option_parser_boundary_gate.json"
)
PARSER_BOUNDARY_DRY_RUN_RESULT_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "verilator_native_option_parser_boundary_dry_run_result_gate.json"
)
PARSER_BOUNDARY_DRY_RUN_REVIEW_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "review_verilator_native_option_parser_boundary_dry_run_gate.json"
)
PARSER_STUB_BOUNDARY_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "define_verilator_native_option_parser_stub_boundary_gate.json"
)
PARSER_STUB_BOUNDARY_REVIEW_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "review_verilator_native_option_parser_stub_boundary_gate.json"
)
PARSER_STUB_FIXTURE_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "define_verilator_native_option_parser_stub_fixture_gate.json"
)
PARSER_STUB_FIXTURE_REVIEW_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "review_verilator_native_option_parser_stub_fixture_gate.json"
)
SELECTION = REPO_ROOT / "config" / "selection.json"
TOOLS = REPO_ROOT / "src" / "tools"
REGISTRY_NEXT_SELECTION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "next_measurement_selection_after_verilator_native_option_prototype_filelist_registry_public_pack_refresh_gate.json"
)


class CommitSplitCleanupGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def read_review_gate(self) -> dict[str, object]:
        return json.loads(REVIEW_GATE.read_text(encoding="utf-8"))

    def read_resolution_gate(self) -> dict[str, object]:
        return json.loads(RESOLUTION_GATE.read_text(encoding="utf-8"))

    def read_completion_gate(self) -> dict[str, object]:
        return json.loads(COMPLETION_GATE.read_text(encoding="utf-8"))

    def read_parser_boundary_gate(self) -> dict[str, object]:
        return json.loads(PARSER_BOUNDARY_GATE.read_text(encoding="utf-8"))

    def read_parser_boundary_review_gate(self) -> dict[str, object]:
        return json.loads(PARSER_BOUNDARY_REVIEW_GATE.read_text(encoding="utf-8"))

    def read_parser_boundary_dry_run_result_gate(self) -> dict[str, object]:
        return json.loads(PARSER_BOUNDARY_DRY_RUN_RESULT_GATE.read_text(encoding="utf-8"))

    def read_parser_boundary_dry_run_review_gate(self) -> dict[str, object]:
        return json.loads(PARSER_BOUNDARY_DRY_RUN_REVIEW_GATE.read_text(encoding="utf-8"))

    def read_parser_stub_boundary_gate(self) -> dict[str, object]:
        return json.loads(PARSER_STUB_BOUNDARY_GATE.read_text(encoding="utf-8"))

    def read_parser_stub_boundary_review_gate(self) -> dict[str, object]:
        return json.loads(PARSER_STUB_BOUNDARY_REVIEW_GATE.read_text(encoding="utf-8"))

    def read_parser_stub_fixture_gate(self) -> dict[str, object]:
        return json.loads(PARSER_STUB_FIXTURE_GATE.read_text(encoding="utf-8"))

    def read_parser_stub_fixture_review_gate(self) -> dict[str, object]:
        return json.loads(PARSER_STUB_FIXTURE_REVIEW_GATE.read_text(encoding="utf-8"))

    def test_registry_next_selection_gate_chooses_commit_split_cleanup(self) -> None:
        selection = json.loads(REGISTRY_NEXT_SELECTION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(selection["current_priority"], "define_commit_split_and_public_pack_cleanup_gate")
        self.assertEqual(selection["decision"]["selected_next_workstream"], "commit_split_and_public_pack_cleanup")
        self.assertEqual(selection["required_next_gate"]["name"], "define_commit_split_and_public_pack_cleanup_gate")
        self.assertEqual(selection["accepted_evidence"]["target_count"], 2)
        self.assertEqual(selection["accepted_evidence"]["preview_and_plan_command_count"], 5)
        self.assertEqual(selection["accepted_evidence"]["documented_commit_guard_staged_file_limit"], 100)
        self.assertEqual(selection["accepted_evidence"]["observed_staged_file_count_before_selection"], 262)
        self.assertFalse(selection["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(selection["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(selection["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(selection["acceptance_policy"]["arbitrary_filelist_support_claim_allowed_by_gate_alone"])
        self.assertFalse(selection["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_definition_pins_file_and_line_guard_risks(self) -> None:
        gate = self.read_gate()

        self.assertEqual(gate["current_priority"], "review_commit_split_and_public_pack_cleanup_gate")
        observed = gate["observed_state"]
        self.assertEqual(observed["documented_commit_guard_staged_file_limit"], 100)
        self.assertEqual(observed["documented_script_added_line_limit"], 250)
        self.assertEqual(observed["documented_contract_test_added_line_limit"], 250)
        self.assertEqual(observed["staged_file_count_before_definition_gate"], 263)
        self.assertEqual(observed["projected_staged_file_count_after_definition_gate"], 265)
        self.assertEqual(observed["projected_records_scaling_gate_json_count_after_definition_gate"], 800)

        risks = {risk["path"]: risk for risk in gate["line_guard_risks_before_split"]}
        self.assertEqual(risks["src/tools/results_reproduction_gpu_allocation_policy.py"]["added_lines"], 300)
        self.assertEqual(risks["tests/contract/test_hybrid_verilator_like_cli.py"]["added_lines"], 443)
        self.assertEqual(risks["tests/contract/test_public_pack_repeat_median_refresh_gates.py"]["added_lines"], 264)

    def test_split_groups_stay_below_file_limit_and_require_review(self) -> None:
        gate = self.read_gate()

        counts = [group["estimated_file_count_after_definition_gate"] for group in gate["split_plan"]]
        self.assertEqual(counts, [15, 26, 71, 30, 24, 59, 28, 25])
        self.assertLessEqual(max(counts), gate["observed_state"]["documented_commit_guard_staged_file_limit"])
        self.assertTrue(gate["split_execution_policy"]["definition_only"])
        self.assertTrue(gate["split_execution_policy"]["requires_review_before_index_rewrite"])
        self.assertEqual(gate["required_next_gate"]["name"], "review_commit_split_and_public_pack_cleanup_gate")
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])

    def test_review_gate_accepts_split_but_keeps_line_guard_work_open(self) -> None:
        review = self.read_review_gate()

        self.assertEqual(review["current_priority"], "resolve_commit_split_line_guard_risks_gate")
        self.assertEqual(review["source_definition_gate"], "config/scaling_gates/define_commit_split_and_public_pack_cleanup_gate.json")
        self.assertEqual(review["accepted_split_plan"]["commit_group_count"], 8)
        self.assertEqual(review["accepted_split_plan"]["max_estimated_file_count"], 71)
        self.assertTrue(review["accepted_split_plan"]["all_groups_below_file_limit"])
        self.assertFalse(review["accepted_split_plan"]["index_rewrite_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["line_guard_resolution_complete"])
        self.assertEqual(
            {risk["path"] for risk in review["unresolved_line_guard_risks"]},
            {
                "src/tools/results_reproduction_gpu_allocation_policy.py",
                "tests/contract/test_hybrid_verilator_like_cli.py",
                "tests/contract/test_public_pack_repeat_median_refresh_gates.py",
            },
        )

    def test_resolution_gate_closes_line_guard_risks_and_selects_index_rewrite(self) -> None:
        resolution = self.read_resolution_gate()
        self.assertEqual(resolution["current_priority"], "execute_commit_split_index_rewrite_gate")
        self.assertEqual(resolution["source_review_gate"], "config/scaling_gates/review_commit_split_and_public_pack_cleanup_gate.json")
        self.assertTrue(resolution["acceptance_policy"]["line_guard_resolution_complete"])
        self.assertTrue(resolution["acceptance_policy"]["file_count_split_still_required"])
        self.assertEqual(resolution["observed_state"]["line_guard_check_exit_code"], 0)
        self.assertEqual(resolution["observed_state"]["projected_records_scaling_gate_json_count_after_resolution_gate"], 802)
        resolved_paths = {
            file["path"]
            for risk in resolution["resolved_risks"]
            for file in risk["resolved_files"]
        }
        self.assertIn("src/tools/results_reproduction_gpu_allocation_policy_data.py", resolved_paths)
        self.assertIn("tests/contract/test_filelist_gpu_allocation_policy_cli.py", resolved_paths)
        self.assertIn("tests/contract/test_filelist_public_pack_manifest_paths.py", resolved_paths)

    def test_completion_gate_closes_index_rewrite_and_selects_parser_boundary(self) -> None:
        completion = self.read_completion_gate()
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))

        self.assertEqual(completion["current_priority"], "define_verilator_native_option_parser_boundary_gate")
        self.assertEqual(
            completion["source_resolution_gate"],
            "config/scaling_gates/resolve_commit_split_line_guard_risks_gate.json",
        )
        self.assertTrue(completion["completion_decision"]["achieved"])
        self.assertTrue(completion["acceptance_policy"]["commit_split_complete"])
        self.assertEqual(completion["observed_state"]["payload_commit_count"], 8)
        self.assertEqual(completion["observed_state"]["prerequisite_commit_count"], 1)
        self.assertLessEqual(
            completion["observed_state"]["max_payload_commit_file_count"],
            completion["observed_state"]["documented_commit_guard_staged_file_limit"],
        )
        self.assertEqual(completion["observed_state"]["full_check_exit_code"], 0)
        self.assertEqual(completion["observed_state"]["contract_test_count"], 221)
        self.assertEqual(
            completion["selected_next_workstream"]["first_gate"],
            "define_verilator_native_option_parser_boundary_gate",
        )
        self.assertFalse(completion["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(completion["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(completion["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertEqual(
            selection["current_priority"],
            "define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate.json",
        )
        self.assertEqual(selection["repository_cleanup"]["records_scaling_gate_json_count"], 844)

    def test_parser_boundary_definition_keeps_native_scope_parser_only(self) -> None:
        gate = self.read_parser_boundary_gate()

        self.assertEqual(gate["current_priority"], "review_verilator_native_option_parser_boundary_gate")
        self.assertEqual(
            gate["source_commit_split_completion_gate"],
            "config/scaling_gates/execute_commit_split_index_rewrite_gate.json",
        )
        boundary = gate["parser_boundary"]
        self.assertEqual(boundary["selected_surface"], "native_verilator_option_parser_to_sidecar_plan_contract")
        self.assertIn("--sim-accel sidecar-gpu", boundary["future_verilator_facing_spelling"]["minimal_option"])
        self.assertEqual(
            boundary["future_verilator_facing_spelling"]["required_shape_options"],
            ["--sim-accel-states <N>", "--sim-accel-steps <S>"],
        )
        self.assertFalse(boundary["future_verilator_facing_spelling"]["wrapper_compatibility_shape_native_minimal_scope"])
        self.assertIn("--sim-accel-shape <NxS>", boundary["native_parser_minimal_scope_exclusions"])
        self.assertIn("--operator-plan-json", boundary["native_parser_minimal_scope_exclusions"])
        self.assertFalse(boundary["readiness_limits"]["resident_modes_ready_for_native_parser_handoff"])
        self.assertFalse(boundary["readiness_limits"]["mobile_vit_dataset_backed_flow_ready_for_native_parser_handoff"])
        self.assertFalse(gate["acceptance_policy"]["native_verilator_parser_implementation_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertEqual(gate["required_next_gate"]["name"], "review_verilator_native_option_parser_boundary_gate")

    def test_parser_boundary_review_accepts_no_execution_definition(self) -> None:
        review = self.read_parser_boundary_review_gate()

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_boundary_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("no Verilator source tree", review["review_decision"]["weakest_point"])
        self.assertEqual(review["current_priority"], "run_verilator_native_option_parser_boundary_dry_run_gate")
        self.assertEqual(review["required_next_gate"]["name"], "run_verilator_native_option_parser_boundary_dry_run_gate")
        self.assertTrue(review["validated_definition_decisions"]["parser_only_boundary"])
        self.assertTrue(review["validated_definition_decisions"]["expanded_spelling_is_native_minimum"])
        self.assertTrue(review["validated_definition_decisions"]["compact_shape_spelling_stays_wrapper_compatibility"])
        self.assertFalse(review["accepted_scope"]["parser_infers_handoff_fields"])
        self.assertFalse(review["accepted_scope"]["runtime_or_abi_changed"])
        self.assertFalse(review["accepted_scope"]["new_execution_added"])
        self.assertFalse(review["accepted_scope"]["new_measurement_added"])
        self.assertIn("not parser inference of coverage manifests, host-probe metadata, source closure, state paths, or report paths", review["non_claims"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["new_measurement_allowed_by_this_gate"])

    def test_parser_boundary_dry_run_result_keeps_preview_scope(self) -> None:
        result = self.read_parser_boundary_dry_run_result_gate()

        self.assertEqual(
            result["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_boundary_gate.json",
        )
        self.assertEqual(result["current_priority"], "review_verilator_native_option_parser_boundary_dry_run_gate")
        self.assertEqual(
            result["required_next_gate"]["name"],
            "review_verilator_native_option_parser_boundary_dry_run_gate",
        )
        self.assertEqual(result["shape"], "64x1")
        self.assertEqual(result["command_count"], 12)
        self.assertTrue(result["expected_exit_code_summary"]["all_commands_matched_expected_exit_codes"])
        scope = result["dry_run_scope"]
        self.assertEqual(scope["ready_json_preview_command_count"], 2)
        self.assertEqual(scope["operator_plan_json_command_count"], 2)
        self.assertEqual(scope["command_only_preview_command_count"], 2)
        self.assertEqual(scope["invalid_input_rejection_command_count"], 4)
        self.assertEqual(scope["not_ready_rejection_command_count"], 2)
        self.assertFalse(scope["generated_reports_or_artifacts_written"])
        self.assertTrue(scope["filelist_targets_directly_supported_by_shim"])
        self.assertEqual(scope["native_verilator_parser_status"], "not_implemented")

        observed = result["observed_summary"]
        self.assertTrue(observed["expanded_future_verilator_spelling_observed"])
        self.assertTrue(observed["estimate_flag_kept_separate_from_command_only_preview"])
        self.assertTrue(observed["invalid_missing_steps_rejected"])
        self.assertTrue(observed["invalid_mixed_shape_spelling_rejected"])
        self.assertTrue(observed["invalid_nonpositive_count_rejected"])
        self.assertTrue(observed["invalid_accelerator_name_rejected"])
        self.assertEqual(observed["invalid_accelerator_rejection_layer"], "argparse_choices")
        self.assertEqual(
            observed["shared_mapper_rejections_observed"],
            [
                "missing_states_or_steps_pair",
                "mixed_shape_spelling",
                "nonpositive_state_count",
            ],
        )
        self.assertTrue(observed["resident_modes_remain_not_ready_for_direct_native_handoff"])
        self.assertTrue(observed["dataset_backed_targets_remain_not_ready_for_direct_native_handoff"])
        self.assertFalse(result["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(result["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(result["acceptance_policy"]["new_measurement_allowed_by_this_gate"])

    def test_parser_boundary_dry_run_review_accepts_validation_layer_caveat(self) -> None:
        review = self.read_parser_boundary_dry_run_review_gate()

        self.assertEqual(
            review["source_result_gate"],
            "config/scaling_gates/verilator_native_option_parser_boundary_dry_run_result_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("argparse choices", review["review_decision"]["weakest_point"])
        self.assertEqual(review["current_priority"], "define_verilator_native_option_parser_stub_boundary_gate")
        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_stub_boundary_gate",
        )
        must_define = review["required_next_gate"]["must_define"]
        self.assertIn(
            "where unknown accelerator validation belongs: native parser, shared mapper, or explicit compatibility wrapper layer",
            must_define,
        )
        self.assertIn(
            "the structured handoff fields that the stub must produce or call before any execution",
            must_define,
        )
        accepted = review["accepted_scope"]
        self.assertEqual(accepted["invalid_accelerator_rejection_layer"], "argparse_choices")
        self.assertTrue(accepted["unknown_accelerator_validation_layer_caveat_accepted_for_this_dry_run"])
        self.assertEqual(
            accepted["shared_mapper_rejections_observed"],
            [
                "missing_states_or_steps_pair",
                "mixed_shape_spelling",
                "nonpositive_state_count",
            ],
        )
        decisions = review["validated_result_decisions"]
        self.assertTrue(decisions["argparse_unknown_accelerator_layer_must_not_be_called_shared_mapper_validation"])
        self.assertTrue(decisions["validation_layer_caveat_must_be_resolved_or_explicitly_assigned_by_next_gate"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["new_measurement_allowed_by_this_gate"])

    def test_parser_stub_boundary_defines_validation_owner_and_handoff(self) -> None:
        gate = self.read_parser_stub_boundary_gate()

        self.assertEqual(
            gate["source_dry_run_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_boundary_dry_run_gate.json",
        )
        self.assertEqual(gate["current_priority"], "review_verilator_native_option_parser_stub_boundary_gate")
        self.assertEqual(gate["required_next_gate"]["name"], "review_verilator_native_option_parser_stub_boundary_gate")
        boundary = gate["parser_stub_boundary"]
        validation = boundary["validation_ownership"]
        self.assertEqual(validation["canonical_unknown_accelerator_owner"], "native_parser_stub_validation_contract")
        self.assertEqual(validation["allowed_accelerators"], ["sidecar-gpu"])
        self.assertEqual(
            validation["current_wrapper_argparse_choices_status"],
            "compatibility_wrapper_behavior_only_not_canonical_stub_validation",
        )
        self.assertTrue(validation["current_wrapper_argparse_choices_must_not_be_used_as_native_parser_evidence"])
        self.assertIn("correctness policy set to coverage_output_equivalence", boundary["structured_handoff_fields"])
        self.assertIn("--sim-accel-shape <NxS>", boundary["native_parser_stub_minimal_scope_exclusions"])
        self.assertFalse(boundary["readiness_limits"]["native_verilator_source_tree_available"])
        must_decide = gate["required_next_gate"]["must_decide"]
        self.assertIn(
            "whether unknown accelerator validation is correctly assigned to the parser-stub validation contract",
            must_decide,
        )
        self.assertFalse(gate["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])

    def test_parser_stub_boundary_review_accepts_definition_and_selects_fixture(self) -> None:
        review = self.read_parser_stub_boundary_review_gate()

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_stub_boundary_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("no Verilator source tree", review["review_decision"]["weakest_point"])
        self.assertIn("argparse choices", review["review_decision"]["weakest_point"])
        self.assertEqual(review["current_priority"], "define_verilator_native_option_parser_stub_fixture_gate")
        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_stub_fixture_gate",
        )
        accepted = review["accepted_scope"]
        self.assertEqual(accepted["canonical_unknown_accelerator_owner"], "native_parser_stub_validation_contract")
        self.assertEqual(accepted["allowed_accelerators"], ["sidecar-gpu"])
        self.assertEqual(
            accepted["wrapper_argparse_choices_status"],
            "compatibility_wrapper_behavior_only_not_canonical_stub_validation",
        )
        self.assertFalse(accepted["native_verilator_source_tree_available"])
        self.assertFalse(accepted["runtime_or_abi_changed"])
        self.assertFalse(accepted["new_execution_added"])
        self.assertFalse(accepted["new_measurement_added"])
        decisions = review["validated_definition_decisions"]
        self.assertTrue(decisions["validation_owner_assigned_to_parser_stub_contract"])
        self.assertTrue(decisions["argparse_choices_not_native_parser_evidence"])
        self.assertTrue(decisions["structured_handoff_fields_sufficient_for_fixture_definition"])
        must_define = review["required_next_gate"]["must_define"]
        self.assertIn("a non-executing parser-stub fixture input and output contract", must_define)
        self.assertIn(
            "a fixture case that rejects an unknown accelerator through the parser-stub validation contract, not wrapper argparse choices",
            must_define,
        )
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["new_measurement_allowed_by_this_gate"])

    def test_parser_stub_fixture_definition_pins_non_executing_cases(self) -> None:
        gate = self.read_parser_stub_fixture_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_stub_boundary_gate.json",
        )
        self.assertEqual(gate["current_priority"], "review_verilator_native_option_parser_stub_fixture_gate")
        self.assertEqual(gate["required_next_gate"]["name"], "review_verilator_native_option_parser_stub_fixture_gate")
        fixture = gate["fixture_contract"]
        self.assertEqual(fixture["fixture_kind"], "importable_helper_contract_not_public_cli")
        self.assertEqual(fixture["implementation_status"], "not_implemented_by_this_gate")
        self.assertFalse(fixture["native_verilator_source_tree_required"])
        self.assertEqual(fixture["allowed_accelerators"], ["sidecar-gpu"])
        accepted = fixture["accepted_minimal_case"]
        self.assertEqual(accepted["expected_shape"], "64x1")
        self.assertEqual(accepted["expected_state_count"], 64)
        self.assertEqual(accepted["expected_step_count"], 1)
        self.assertTrue(accepted["ordinary_verilator_args_must_be_preserved"])
        self.assertEqual(
            fixture["canonical_unknown_accelerator_error"]["rejection_layer"],
            "parser_stub_validation_contract",
        )
        self.assertIn(
            "the unsupported accelerator value",
            fixture["canonical_unknown_accelerator_error"]["message_must_include"],
        )
        rejection_cases = {case["name"]: case for case in fixture["required_rejection_cases"]}
        self.assertEqual(rejection_cases["reject_unknown_accelerator"]["expected_error_code"], "invalid_sim_accel")
        self.assertEqual(rejection_cases["reject_missing_steps"]["expected_error_code"], "missing_sim_accel_shape_half")
        self.assertEqual(rejection_cases["reject_nonpositive_states"]["expected_error_code"], "nonpositive_sim_accel_count")
        compact = rejection_cases["reject_compact_shape_spelling_outside_native_minimum"]
        self.assertEqual(compact["expected_error_code"], "compact_shape_spelling_outside_native_minimum")
        self.assertEqual(compact["expected_rejection_layer"], "parser_stub_validation_contract")
        self.assertIn("wrapper compatibility", compact["message_requirement"])
        self.assertIn("-Wno-fatal", accepted["argv"])
        self.assertEqual(len(fixture["serialized_handoff_fields"]), 18)
        self.assertEqual(fixture["field_rules"]["correctness_policy"], "coverage_output_equivalence")
        self.assertIn("target registry lookup", fixture["must_not_call_or_infer"])
        self.assertIn("automatic optimal GPU allocation", fixture["must_not_call_or_infer"])
        self.assertFalse(gate["acceptance_policy"]["implementation_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])

    def test_parser_stub_fixture_review_accepts_contract_and_selects_implementation(self) -> None:
        review = self.read_parser_stub_fixture_review_gate()

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_stub_fixture_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("argparse choices", review["review_decision"]["weakest_point"])
        self.assertEqual(review["current_priority"], "implement_verilator_native_option_parser_stub_fixture_gate")
        self.assertEqual(
            review["required_next_gate"]["name"],
            "implement_verilator_native_option_parser_stub_fixture_gate",
        )
        accepted = review["accepted_scope"]
        self.assertEqual(accepted["fixture_kind"], "importable_helper_contract_not_public_cli")
        self.assertEqual(accepted["candidate_module"], "src/tools/verilator_native_option_parser_stub_fixture.py")
        self.assertEqual(accepted["candidate_entrypoint_function"], "parse_verilator_native_option_stub")
        self.assertEqual(accepted["accepted_case"]["shape"], "64x1")
        self.assertTrue(accepted["accepted_case"]["warning_flag_preserved"])
        self.assertFalse(accepted["accepted_case"]["source_closure_inferred"])
        self.assertIn("reject_unknown_accelerator", accepted["accepted_rejection_cases"])
        self.assertEqual(
            accepted["canonical_unknown_accelerator_error"]["rejection_layer"],
            "parser_stub_validation_contract",
        )
        self.assertTrue(accepted["canonical_unknown_accelerator_error"]["must_not_depend_on_python_argparse_choices"])
        self.assertEqual(
            accepted["compact_shape_spelling_status"],
            "wrapper_compatibility_outside_native_parser_stub_minimum",
        )
        self.assertEqual(
            accepted["mixed_expanded_and_compact_shape_spelling_status"],
            "must_reject_because_compact_shape_spelling_is_outside_native_parser_stub_minimum",
        )
        self.assertEqual(accepted["serialized_handoff_field_count"], 18)
        self.assertEqual(accepted["parser_stub_helper_status"], "not_implemented")
        decisions = review["validated_definition_decisions"]
        self.assertTrue(decisions["unknown_accelerator_rejection_is_testable_outside_argparse_choices"])
        self.assertTrue(decisions["compact_shape_spelling_rejected_as_wrapper_compatibility_not_native_minimum"])
        self.assertTrue(decisions["execution_and_compare_stay_out_of_scope"])
        must_implement = review["required_next_gate"]["must_implement"]
        self.assertIn(
            "mixed expanded --sim-accel-states/--sim-accel-steps plus compact --sim-accel-shape rejection through the same native-minimum rule",
            must_implement,
        )
        self.assertFalse(review["acceptance_policy"]["implementation_allowed_by_this_gate"])
        self.assertTrue(review["acceptance_policy"]["implementation_allowed_next"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["new_measurement_allowed_by_this_gate"])

    def test_public_pack_manifest_includes_definition_gate(self) -> None:
        sys.path.insert(0, str(TOOLS))
        try:
            from results_reproduction_manifest import PUBLIC_PACK_ARCHIVE_PATHS
        finally:
            sys.path.pop(0)

        self.assertIn(
            "records/scaling_gates/define_commit_split_and_public_pack_cleanup_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_commit_split_and_public_pack_cleanup_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/resolve_commit_split_line_guard_risks_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/execute_commit_split_index_rewrite_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/verilator_native_option_parser_boundary_dry_run_result_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_boundary_dry_run_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_stub_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_stub_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_stub_fixture_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_stub_fixture_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/implement_verilator_native_option_parser_stub_fixture_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_stub_fixture_implementation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_source_patch_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_source_patch_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_implementation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/run_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/implement_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_run_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/implement_verilator_native_option_parser_sidecar_handoff_fixture_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "records/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )
        self.assertIn(
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch",
            PUBLIC_PACK_ARCHIVE_PATHS,
        )


if __name__ == "__main__":
    unittest.main()
