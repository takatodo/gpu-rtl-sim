import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json"
)
REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarLauncherRunBoundaryGateTest(unittest.TestCase):
    def test_definition_is_scoped_and_non_executing(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate",
        )
        self.assertTrue(gate["definition_decision"]["definition_only"])
        boundary = gate["future_run_boundary"]
        self.assertEqual(
            (
                boundary["eligible_input_surface"],
                boundary["required_sidecar_launcher_entrypoint"],
                boundary["required_target"],
                boundary["required_template"],
                boundary["required_shape"],
                boundary["required_state_count"],
                boundary["required_step_count"],
            ),
            (
                "native_verilator_parser_direct_command_path_sidecar_launcher_bridge_fixture",
                "src/tools/run_hybrid_template.py",
                "pulp_ita_mha",
                "config/slice_launch_templates/pulp_ita_mha.json",
                "64x1",
                64,
                1,
            ),
        )
        self.assertTrue(boundary["must_invoke_sidecar_launcher_from_native_path"])
        self.assertTrue(boundary["must_run_coverage_output_compare_after_sidecar_path"])
        compare = gate["future_compare_boundary"]
        self.assertEqual((compare["correctness_policy"], compare["total_words_per_state"], compare["required_mismatch_count_for_success"]), ("coverage_output_equivalence", 29, 0))
        self.assertFalse(compare["raw_full_state_equality_required"])
        failures = gate["failure_class_boundary"]
        for name in ("sidecar_launcher_bridge_failure", "sidecar_stage_failure", "compare_failure"):
            self.assertIn(name, failures)
        policy = gate["acceptance_policy"]
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_launcher_invocation_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(gate["required_next_gate"]["name"], gate["next_task"])

    def test_review_accepts_boundary_without_execution_claims(self) -> None:
        review = json.loads(REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json",
        )
        self.assertEqual(
            review["current_priority"],
            "run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_gate",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("review-only", review["review_decision"]["weakest_point"])
        accepted = review["accepted_boundary"]
        self.assertEqual(
            (
                accepted["selected_target"],
                accepted["selected_template"],
                accepted["selected_shape"],
                accepted["required_sidecar_launcher_entrypoint"],
            ),
            ("pulp_ita_mha", "config/slice_launch_templates/pulp_ita_mha.json", "64x1", "src/tools/run_hybrid_template.py"),
        )
        self.assertTrue(accepted["future_run_gate_allowed"])
        self.assertFalse(accepted["generated_reports_and_artifacts_are_source_of_truth"])
        failures = review["accepted_failure_classes"]
        self.assertTrue(failures["sidecar_launcher_bridge_failure"])
        self.assertTrue(failures["sidecar_stage_failure"])
        self.assertTrue(failures["compare_failure"])
        policy = review["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_launcher_invocation_claim_allowed_by_gate_alone"])
        self.assertEqual(review["required_next_gate"]["name"], review["next_task"])
