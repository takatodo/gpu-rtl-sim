import importlib
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "tools"
REVIEW_GATE = REPO_ROOT / "config" / "scaling_gates" / "review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_run_gate.json"
DEFINE_AUTHORITY_GATE = REPO_ROOT / "config" / "scaling_gates" / "define_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json"
REVIEW_AUTHORITY_GATE = REPO_ROOT / "config" / "scaling_gates" / "review_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json"
REVIEW_FIRST_SCOPED_EXECUTION_BOUNDARY_GATE = REPO_ROOT / "config" / "scaling_gates" / "review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate.json"
RUN_FIRST_SCOPED_EXECUTION_GATE = REPO_ROOT / "config" / "scaling_gates" / "run_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_gate.json"
RUN_GATE = "config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_gate.json"
RUN_FIRST_SCOPED_EXECUTION_GATE_NAME = "run_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_gate"
REVIEW_FIRST_SCOPED_EXECUTION_RUN_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_run_gate"
DIRECT_SIDECAR_LAUNCH_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate"
REVIEW_DIRECT_SIDECAR_LAUNCH_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate"
RUN_DIRECT_SIDECAR_LAUNCH_GATE_NAME = "run_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_gate"
REVIEW_DIRECT_SIDECAR_LAUNCH_RUN_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_run_gate"
DIRECT_LAUNCH_HANDOFF_IMPLEMENTATION_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_IMPLEMENTATION_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate"
IMPLEMENT_DIRECT_LAUNCH_HANDOFF_FIXTURE_GATE_NAME = "implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_FIXTURE_IMPLEMENTATION_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_implementation_gate"
DIRECT_LAUNCH_HANDOFF_RUN_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_RUN_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate"
RUN_DIRECT_LAUNCH_HANDOFF_GATE_NAME = "run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_RUN_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_gate"
DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate"
IMPLEMENT_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_FIXTURE_GATE_NAME = "implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_FIXTURE_IMPLEMENTATION_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_implementation_gate"
DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_RUN_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_RUN_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate"
RUN_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_GATE_NAME = "run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_RUN_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_gate"
DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate"
IMPLEMENT_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_FIXTURE_GATE_NAME = "implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_fixture_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_FIXTURE_IMPLEMENTATION_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_fixture_implementation_gate"
DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_RUN_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate"
REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_RUN_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate"
DEFINE_AUTHORITY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate"
REVIEW_AUTHORITY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate"
FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME = "define_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate"
REVIEW_FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME = "review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate"
PUBLIC_PACK_RECORDS = (
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_run_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate.json",
    "records/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_run_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate.json",
    "records/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_run_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json",
    "records/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_implementation_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate.json",
    "records/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate.json",
    "records/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_implementation_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json",
    "records/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate.json",
    "records/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_fixture_gate.json",
    "records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_fixture_implementation_gate.json",
    "records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate.json",
)


def _load_public_pack_paths() -> tuple[str, ...]:
    tools_s = str(TOOLS)
    added = tools_s not in sys.path
    if added:
        sys.path.insert(0, tools_s)
    try:
        module = importlib.import_module("results_reproduction_manifest")
        return module.PUBLIC_PACK_ARCHIVE_PATHS
    finally:
        if added:
            sys.path.remove(tools_s)


class VerilatorNativeOptionParserPatchedBinaryRetryReviewGateTest(unittest.TestCase):
    def test_selection_points_at_first_scoped_execution_boundary_review_after_definition(self) -> None:
        selection = json.loads((REPO_ROOT / "config" / "selection.json").read_text(encoding="utf-8"))

        self.assertEqual(selection["current_priority"], REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_RUN_BOUNDARY_GATE_NAME)
        self.assertEqual(selection["current_priority_source_artifact"], f"config/scaling_gates/{DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_INVOCATION_RUN_BOUNDARY_GATE_NAME}.json")
        self.assertEqual(selection["repository_cleanup"]["records_scaling_gate_json_count"], 925)

    def test_review_accepts_only_parser_only_patched_binary_success(self) -> None:
        gate = json.loads(REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["source_run_gate"], RUN_GATE)
        self.assertEqual(gate["current_priority"], DEFINE_AUTHORITY_GATE_NAME)
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("generated artifact", gate["review_decision"]["weakest_point"])
        self.assertEqual(gate["required_next_gate"]["name"], DEFINE_AUTHORITY_GATE_NAME)
        self.assertEqual(gate["next_task"], DEFINE_AUTHORITY_GATE_NAME)

        setup = gate["accepted_setup"]
        self.assertTrue(setup["patched_binary_exists_and_is_executable"])
        self.assertTrue(setup["verilator_root_set_for_run"])
        self.assertFalse(setup["generated_artifact_is_source_of_truth"])
        self.assertFalse(setup["equivalent_rebuild_performed_for_this_gate"])
        self.assertTrue(setup["equivalent_rebuild_required_if_artifact_missing"])

        result = gate["accepted_result"]
        self.assertEqual(result["validation_kind"], "patched_binary_parser_only_smoke_parse_success")
        self.assertTrue(result["direct_patched_binary_invoked"])
        self.assertFalse(result["wrapper_execution_used"])
        self.assertFalse(result["path_verilator_used"])
        self.assertEqual(result["observed_exit_code"], 0)
        self.assertTrue(result["native_option_parse_accepted"])
        self.assertEqual(result["failure_class"], "none")
        self.assertTrue(result["timing_option_is_parser_build_input_not_timing_evidence"])
        self.assertIn("--sim-accel", result["expanded_option_spelling_tested"])
        self.assertIn("--sim-accel-states", result["expanded_option_spelling_tested"])
        self.assertIn("--sim-accel-steps", result["expanded_option_spelling_tested"])

        for flag in (
            "sidecar_stage_execution_performed",
            "build_stage_performed",
            "run_stage_performed",
            "compare_stage_performed",
            "coverage_output_equivalence_recorded",
            "timing_measured",
            "uses_generated_reports_as_source_of_truth",
            "uses_generated_artifacts_as_source_of_truth",
        ):
            with self.subTest(flag=flag):
                self.assertFalse(result[flag])

    def test_review_rejects_broader_execution_and_measurement_claims(self) -> None:
        gate = json.loads(REVIEW_GATE.read_text(encoding="utf-8"))

        scope = gate["accepted_claim_scope"]
        self.assertTrue(scope["parser_only_native_option_parse_success_accepted"])
        self.assertTrue(scope["patched_binary_direct_invocation_accepted"])
        for flag in (
            "native_verilator_option_support_accepted",
            "native_verilator_parser_integration_complete",
            "sidecar_stage_execution_accepted",
            "build_or_run_stage_execution_accepted",
            "compare_execution_accepted",
            "coverage_output_equivalence_accepted",
            "timing_or_speedup_evidence_accepted",
            "raw_full_state_equality_accepted",
            "arbitrary_rtl_or_filelist_support_accepted",
            "source_closure_or_dependency_inference_accepted",
            "automatic_gpu_allocation_accepted",
            "runtime_or_abi_change_accepted",
            "production_llm_serving_throughput_accepted",
        ):
            with self.subTest(flag=flag):
                self.assertFalse(scope[flag])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["source_run_gate_accepted"])
        self.assertTrue(policy["next_sidecar_authority_definition_allowed"])
        self.assertFalse(policy["sidecar_stage_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])

    def test_public_pack_manifest_includes_review_gate_record(self) -> None:
        paths = _load_public_pack_paths()
        for record in PUBLIC_PACK_RECORDS:
            self.assertIn(record, paths)

    def test_sidecar_authority_boundary_definition_is_non_executing(self) -> None:
        gate = json.loads(DEFINE_AUTHORITY_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_run_gate.json",
        )
        self.assertEqual(gate["current_priority"], REVIEW_AUTHORITY_GATE_NAME)
        self.assertTrue(gate["definition_decision"]["definition_only"])
        self.assertFalse(gate["accepted_input_scope"]["parser_success_alone_authorizes_sidecar_execution"])
        self.assertFalse(gate["accepted_input_scope"]["parser_success_alone_authorizes_compare"])
        self.assertFalse(gate["accepted_input_scope"]["parser_success_alone_authorizes_timing"])
        self.assertFalse(gate["required_sidecar_authority_before_execution"]["native_command_alone_execution_authority"])
        self.assertTrue(gate["required_sidecar_authority_before_execution"]["explicit_sidecar_context_required"])
        self.assertTrue(gate["required_sidecar_authority_before_execution"]["reviewed_stage_authority_required"])
        self.assertTrue(gate["artifact_provenance_boundary"]["patched_binary_is_generated_evidence"])
        self.assertFalse(gate["artifact_provenance_boundary"]["patched_binary_is_source_of_truth"])
        self.assertTrue(
            gate["artifact_provenance_boundary"]["future_execution_must_record_artifact_presence_or_equivalent_rebuild"]
        )
        self.assertTrue(gate["compare_authority_boundary"]["coverage_output_equivalence_policy_required_before_compare_claim"])
        self.assertFalse(gate["compare_authority_boundary"]["raw_full_state_equality_policy_allowed"])
        self.assertFalse(gate["compare_authority_boundary"]["compare_claim_allowed_by_definition_gate"])

        failure_classes = gate["failure_class_boundary"]
        for name in ("process_parse_failure", "sidecar_authority_failure", "sidecar_stage_failure", "compare_failure"):
            with self.subTest(name=name):
                self.assertIn(name, failure_classes)

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_stage_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["required_next_gate"]["name"], REVIEW_AUTHORITY_GATE_NAME)

    def test_sidecar_authority_boundary_review_accepts_definition_only(self) -> None:
        gate = json.loads(REVIEW_AUTHORITY_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json",
        )
        self.assertEqual(gate["current_priority"], FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME)
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("parser-only", gate["review_decision"]["weakest_point"])
        accepted = gate["accepted_authority_boundary"]
        self.assertTrue(accepted["definition_only"])
        self.assertFalse(accepted["native_option_parse_success_is_execution_authority"])
        self.assertTrue(accepted["reviewed_sidecar_context_required"])
        self.assertTrue(accepted["compare_output_words_must_be_explicit"])
        self.assertFalse(accepted["generated_command_text_is_authority"])
        self.assertFalse(accepted["future_execution_allowed_by_this_gate"])
        artifact = gate["accepted_artifact_policy"]
        self.assertTrue(artifact["patched_binary_is_generated_evidence"])
        self.assertFalse(artifact["generated_artifact_is_source_of_truth"])
        self.assertTrue(artifact["future_execution_must_record_artifact_presence_or_equivalent_rebuild"])
        for name in ("process_parse_failure", "sidecar_authority_failure", "sidecar_stage_failure", "compare_failure"):
            self.assertTrue(gate["accepted_failure_class_boundary"][name])
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["next_execution_boundary_definition_allowed"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["compare_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["required_next_gate"]["name"], FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME)

    def test_first_scoped_sidecar_execution_boundary_definition_is_non_executing(self) -> None:
        gate = json.loads(
            (REPO_ROOT / "config" / "scaling_gates" / f"{FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME}.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(gate["source_review_gate"], str(REVIEW_AUTHORITY_GATE.relative_to(REPO_ROOT)))
        self.assertEqual(gate["current_priority"], REVIEW_FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME)
        self.assertEqual(gate["source_prior_scoped_sidecar_execution_review_role"], "reference_only_not_native_invocation_execution_evidence")
        self.assertTrue(gate["definition_decision"]["definition_only"])
        attempt = gate["selected_first_scoped_attempt"]
        self.assertEqual((attempt["target"], attempt["template"], attempt["shape"]), ("pulp_ita_mha", "config/slice_launch_templates/pulp_ita_mha.json", "64x1"))
        self.assertTrue(attempt["patched_binary_policy"]["reviewed_patched_binary_or_equivalent_rebuild_required"])
        self.assertTrue(gate["required_sidecar_context_before_future_run"]["reviewed_stage_authority_required"])
        self.assertFalse(gate["required_sidecar_context_before_future_run"]["generated_command_text_is_authority"])
        self.assertEqual(gate["future_compare_boundary"]["correctness_policy"], "coverage_output_equivalence")
        self.assertFalse(gate["future_compare_boundary"]["compare_claim_allowed_by_definition_gate"])
        self.assertFalse(gate["future_generated_evidence_boundary"]["reports_and_artifacts_are_source_of_truth"])
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["future_run_gate_allowed_after_review"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["required_next_gate"]["name"], REVIEW_FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME)

    def test_first_scoped_sidecar_execution_boundary_review_accepts_definition_only(self) -> None:
        gate = json.loads(REVIEW_FIRST_SCOPED_EXECUTION_BOUNDARY_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["source_definition_gate"], f"config/scaling_gates/{FIRST_SCOPED_EXECUTION_BOUNDARY_GATE_NAME}.json")
        self.assertEqual(gate["current_priority"], RUN_FIRST_SCOPED_EXECUTION_GATE_NAME)
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("execution_boundary", gate["review_decision"]["weakest_point"])
        accepted = gate["accepted_boundary"]
        self.assertTrue(accepted["definition_only_boundary_confirmed"])
        self.assertEqual((accepted["selected_target"], accepted["selected_template"], accepted["selected_shape"]), ("pulp_ita_mha", "config/slice_launch_templates/pulp_ita_mha.json", "64x1"))
        self.assertTrue(accepted["future_run_gate_allowed"])
        self.assertFalse(accepted["execution_allowed_by_this_gate"])
        self.assertFalse(accepted["generated_reports_and_artifacts_are_source_of_truth"])
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["required_next_gate"]["name"], RUN_FIRST_SCOPED_EXECUTION_GATE_NAME)

    def test_first_scoped_sidecar_execution_run_records_scoped_success(self) -> None:
        gate = json.loads(RUN_FIRST_SCOPED_EXECUTION_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["source_review_gate"], str(REVIEW_FIRST_SCOPED_EXECUTION_BOUNDARY_GATE.relative_to(REPO_ROOT)))
        self.assertEqual((gate["current_priority"], gate["observed_result"]["failure_class"]), (REVIEW_FIRST_SCOPED_EXECUTION_RUN_GATE_NAME, "none"))
        self.assertEqual((gate["patched_verilator_parse_evidence"]["native_option_parse_accepted"], gate["sidecar_execution_scope"]["all_reviewed_sidecar_stages_executed"], gate["sidecar_execution_scope"]["direct_verilator_command_executed_sidecar"]), (True, True, False))
        compare = gate["compare_result"]
        self.assertTrue(compare["coverage_output_equivalence_passed"])
        self.assertEqual((compare["coverage_output_mismatch_count"], compare["compared_state_pair_count"]), (0, 64))
        policy = gate["acceptance_policy"]
        self.assertEqual((policy["scoped_sidecar_build_run_compare_claim_allowed"], policy["direct_verilator_command_sidecar_execution_claim_allowed"]), (True, False))
        self.assertEqual(gate["required_next_gate"]["name"], REVIEW_FIRST_SCOPED_EXECUTION_RUN_GATE_NAME)
        review = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{REVIEW_FIRST_SCOPED_EXECUTION_RUN_GATE_NAME}.json").read_text(encoding="utf-8"))
        self.assertEqual((review["source_run_gate"], review["current_priority"], review["next_task"]), (str(RUN_FIRST_SCOPED_EXECUTION_GATE.relative_to(REPO_ROOT)), DIRECT_SIDECAR_LAUNCH_BOUNDARY_GATE_NAME, DIRECT_SIDECAR_LAUNCH_BOUNDARY_GATE_NAME))
        direct = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{DIRECT_SIDECAR_LAUNCH_BOUNDARY_GATE_NAME}.json").read_text(encoding="utf-8")); review_direct = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{REVIEW_DIRECT_SIDECAR_LAUNCH_BOUNDARY_GATE_NAME}.json").read_text(encoding="utf-8")); run_direct = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{RUN_DIRECT_SIDECAR_LAUNCH_GATE_NAME}.json").read_text(encoding="utf-8")); review_run_direct = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{REVIEW_DIRECT_SIDECAR_LAUNCH_RUN_GATE_NAME}.json").read_text(encoding="utf-8")); handoff = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{DIRECT_LAUNCH_HANDOFF_IMPLEMENTATION_BOUNDARY_GATE_NAME}.json").read_text(encoding="utf-8")); review_handoff = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{REVIEW_DIRECT_LAUNCH_HANDOFF_IMPLEMENTATION_BOUNDARY_GATE_NAME}.json").read_text(encoding="utf-8")); implement_handoff = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{IMPLEMENT_DIRECT_LAUNCH_HANDOFF_FIXTURE_GATE_NAME}.json").read_text(encoding="utf-8")); run_handoff = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{RUN_DIRECT_LAUNCH_HANDOFF_GATE_NAME}.json").read_text(encoding="utf-8")); review_run_handoff = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{REVIEW_DIRECT_LAUNCH_HANDOFF_RUN_GATE_NAME}.json").read_text(encoding="utf-8")); bridge_boundary = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME}.json").read_text(encoding="utf-8")); review_bridge = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME}.json").read_text(encoding="utf-8")); review_bridge_fixture = json.loads((REPO_ROOT / "config" / "scaling_gates" / f"{REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_FIXTURE_IMPLEMENTATION_GATE_NAME}.json").read_text(encoding="utf-8")); self.assertEqual((review["accepted_claim_scope"]["scoped_sidecar_build_run_compare_accepted"], review["accepted_claim_scope"]["direct_verilator_sidecar_execution_accepted"], direct["current_priority"], review_direct["current_priority"], review_direct["acceptance_policy"]["direct_verilator_sidecar_execution_claim_allowed_by_gate_alone"], run_direct["current_priority"], run_direct["observed_result"]["failure_class"], run_direct["direct_launch_authority_chain"]["sidecar_launch_reached_from_native_path"], run_direct["compare_result"]["coverage_output_mismatch_count"], review_run_direct["current_priority"], review_run_direct["accepted_run_result"]["failure_class"], review_run_direct["accepted_claim_scope"]["direct_verilator_sidecar_execution_accepted"], handoff["source_review_gate"], handoff["current_priority"], handoff["implementation_boundary"]["execution_allowed_by_this_definition_gate"], handoff["implementation_boundary"]["runtime_or_abi_change_allowed_by_this_definition_gate"], handoff["acceptance_policy"]["direct_verilator_sidecar_execution_claim_allowed_by_gate_alone"], review_handoff["source_definition_gate"], review_handoff["current_priority"], review_handoff["accepted_boundary"]["future_implementation_kind"], review_handoff["accepted_boundary"]["direct_execution_claim_allowed"], review_handoff["acceptance_policy"]["new_execution_allowed_by_this_gate"], implement_handoff["current_priority"], implement_handoff["implemented_surface"]["primary_entrypoint_function"], implement_handoff["output_contract"]["sidecar_launch_reached_from_native_path"], implement_handoff["acceptance_policy"]["new_execution_allowed_by_this_gate"], run_handoff["current_priority"], run_handoff["observed_result"]["failure_class"], run_handoff["direct_launch_handoff_fixture_evidence"]["handoff_ready"], run_handoff["compare_result"]["coverage_output_mismatch_count"], review_run_handoff["current_priority"], review_run_handoff["accepted_run_result"]["failure_class"], review_run_handoff["accepted_claim_scope"]["direct_verilator_sidecar_execution_accepted"], review_run_handoff["required_next_gate"]["name"], review_run_handoff["acceptance_policy"]["new_execution_allowed_by_this_gate"], bridge_boundary["source_review_gate"], bridge_boundary["current_priority"], bridge_boundary["bridge_boundary"]["execution_allowed_by_this_definition_gate"], bridge_boundary["acceptance_policy"]["direct_verilator_sidecar_execution_claim_allowed_by_gate_alone"], bridge_boundary["bridge_boundary"]["future_primary_launcher_entrypoint"], bridge_boundary["required_inputs_for_future_bridge"]["handoff_fixture_metadata"]["handoff_ready_required"], "sidecar_launcher_bridge_failure" in bridge_boundary["failure_class_boundary"], review_bridge["source_definition_gate"], review_bridge["current_priority"], review_bridge["accepted_boundary"]["future_implementation_kind"], review_bridge["accepted_failure_classes_to_preserve"]["sidecar_launcher_bridge_failure"], review_bridge["acceptance_policy"]["new_execution_allowed_by_this_gate"], review_bridge_fixture["source_implementation_gate"], review_bridge_fixture["current_priority"], review_bridge_fixture["review_decision"]["accepted"], review_bridge_fixture["accepted_implementation"]["metadata_only"], review_bridge_fixture["accepted_implementation"]["sidecar_launcher_invocation_added"], review_bridge_fixture["accepted_output_contract"]["sidecar_launcher_entrypoint_role"], review_bridge_fixture["accepted_output_contract"]["execution_performed"], review_bridge_fixture["accepted_failure_classes_to_preserve"]["sidecar_launcher_bridge_failure"], review_bridge_fixture["required_next_gate"]["name"], review_bridge_fixture["acceptance_policy"]["new_execution_allowed_by_this_gate"]), (True, False, REVIEW_DIRECT_SIDECAR_LAUNCH_BOUNDARY_GATE_NAME, RUN_DIRECT_SIDECAR_LAUNCH_GATE_NAME, False, REVIEW_DIRECT_SIDECAR_LAUNCH_RUN_GATE_NAME, "direct_launch_handoff_failure", False, 0, DIRECT_LAUNCH_HANDOFF_IMPLEMENTATION_BOUNDARY_GATE_NAME, "direct_launch_handoff_failure", False, f"config/scaling_gates/{REVIEW_DIRECT_SIDECAR_LAUNCH_RUN_GATE_NAME}.json", REVIEW_DIRECT_LAUNCH_HANDOFF_IMPLEMENTATION_BOUNDARY_GATE_NAME, False, False, False, f"config/scaling_gates/{DIRECT_LAUNCH_HANDOFF_IMPLEMENTATION_BOUNDARY_GATE_NAME}.json", IMPLEMENT_DIRECT_LAUNCH_HANDOFF_FIXTURE_GATE_NAME, "non_executing_direct_launch_handoff_fixture", False, False, REVIEW_DIRECT_LAUNCH_HANDOFF_FIXTURE_IMPLEMENTATION_GATE_NAME, "define_direct_launch_handoff_fixture", False, False, REVIEW_DIRECT_LAUNCH_HANDOFF_RUN_GATE_NAME, "direct_launch_handoff_failure", True, 0, DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME, "direct_launch_handoff_failure", False, DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME, False, f"config/scaling_gates/{REVIEW_DIRECT_LAUNCH_HANDOFF_RUN_GATE_NAME}.json", REVIEW_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME, False, False, "src/tools/run_hybrid_template.py", True, True, f"config/scaling_gates/{DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_BOUNDARY_GATE_NAME}.json", IMPLEMENT_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_FIXTURE_GATE_NAME, "non_executing_sidecar_launcher_bridge_fixture", True, False, f"config/scaling_gates/{IMPLEMENT_DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_BRIDGE_FIXTURE_GATE_NAME}.json", DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_RUN_BOUNDARY_GATE_NAME, True, True, False, "reference_only_not_invoked_by_fixture", False, True, DIRECT_LAUNCH_HANDOFF_SIDECAR_LAUNCHER_RUN_BOUNDARY_GATE_NAME, False))
