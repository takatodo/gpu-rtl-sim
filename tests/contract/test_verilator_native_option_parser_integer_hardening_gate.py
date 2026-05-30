import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json"
)
REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json"
)
IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json"
)
RUN_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json"
)
RUN_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate.json"
)
DESCRIPTOR = (
    REPO_ROOT
    / "overlays"
    / "verilator"
    / "patches"
    / "verilator_native_option_parser_sidecar_gpu_v5_048.json"
)
PATCH = (
    REPO_ROOT
    / "overlays"
    / "verilator"
    / "patches"
    / "verilator_native_option_parser_sidecar_gpu_v5_048.patch"
)


class VerilatorNativeOptionParserIntegerHardeningGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def read_review_gate(self) -> dict[str, object]:
        return json.loads(REVIEW_GATE.read_text(encoding="utf-8"))

    def read_implementation_gate(self) -> dict[str, object]:
        return json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

    def read_run_gate(self) -> dict[str, object]:
        return json.loads(RUN_GATE.read_text(encoding="utf-8"))

    def read_run_review_gate(self) -> dict[str, object]:
        return json.loads(RUN_REVIEW_GATE.read_text(encoding="utf-8"))

    def test_definition_selects_strict_integer_hardening_boundary(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_run_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )
        decision = gate["definition_decision"]
        self.assertEqual(decision["selected_strategy"], "define_hardening_cases_before_patch_change")
        self.assertIn("std::atoi", decision["weakest_point"])

        boundary = gate["hardening_boundary"]
        self.assertEqual(boundary["validation_kind"], "built_verilator_binary_parser_integer_hardening_smoke")
        self.assertFalse(boundary["requires_verilator_source_in_repository"])
        self.assertFalse(boundary["uses_generated_artifacts_as_source_of_truth"])

    def test_definition_pins_negative_and_suffix_cases_without_claiming_success(self) -> None:
        gate = self.read_gate()
        cases = {case["name"]: case for case in gate["required_hardening_cases"]}

        self.assertEqual(
            cases["reject_negative_states_separate_token"]["argv_suffix"],
            ["--sim-accel", "sidecar-gpu", "--sim-accel-states", "-1", "--sim-accel-steps", "1"],
        )
        self.assertIn("tokenizer behavior", cases["reject_negative_steps_separate_token"]["reason"])
        self.assertIn("64abc", cases["reject_non_numeric_states_suffix"]["argv_suffix"])
        self.assertIn("std::atoi", cases["reject_non_numeric_steps_suffix"]["reason"])

        deferred = gate["explicitly_deferred_behavior"]
        self.assertEqual(deferred["equals_form_negative_values"]["status"], "optional_tokenization_control_case")
        self.assertEqual(deferred["compact_shape_spelling"]["status"], "outside_native_minimum")

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertTrue(policy["parser_integer_hardening_boundary_defined"])
        self.assertFalse(policy["hardening_smoke_executed_by_this_gate"])
        self.assertFalse(policy["strict_integer_parsing_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_claim_allowed_by_gate_alone"])

    def test_next_gate_reviews_before_patch_or_execution_claims(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )
        self.assertIn("strict integer parsing is implemented", next_gate["must_not_claim"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )

    def test_review_accepts_implementation_not_run_only_gate(self) -> None:
        review = self.read_review_gate()

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
        )
        self.assertEqual(
            review["current_priority"],
            "implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )
        self.assertTrue(review["accepted_boundary"]["suffix_cases_require_patch_change_before_success_claim"])
        self.assertTrue(review["accepted_boundary"]["negative_cases_may_report_tokenizer_behavior"])

        implementation = review["accepted_implementation_boundary"]
        self.assertTrue(implementation["next_implementation_allowed"])
        self.assertEqual(implementation["allowed_patch_strategy"], "update_existing_overlay_patch_in_place")
        self.assertEqual(implementation["primary_upstream_file"], "src/V3Options.cpp")
        self.assertIn("replace std::atoi", implementation["candidate_parser_change"])

        policy = review["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["strict_integer_parsing_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_claim_allowed_by_gate_alone"])
        self.assertEqual(
            review["next_task"],
            "implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )

    def test_implementation_replaces_prefix_parsing_and_selects_run_gate(self) -> None:
        gate = self.read_implementation_gate()
        descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
        patch_text = PATCH.read_text(encoding="utf-8")

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )
        self.assertEqual(
            descriptor["source_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
        )

        parser = descriptor["patch_behavior"]["positive_count_parser"]
        self.assertEqual(
            descriptor["patch_behavior"]["parser_integer_hardening_source_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
        )
        self.assertEqual(parser["implementation"], "manual_full_token_decimal_digit_validation")
        self.assertTrue(parser["rejects_suffix_bearing_values"])
        self.assertTrue(parser["rejects_int_overflow"])
        self.assertTrue(parser["replaces_std_atoi_prefix_parsing"])

        self.assertIn("parsePositiveSimAccelCount", patch_text)
        self.assertIn("std::isdigit(static_cast<unsigned char>(*cp))", patch_text)
        self.assertIn("214748364", patch_text)
        self.assertNotIn("std::atoi", patch_text)

        verification = gate["verification"]
        self.assertEqual(verification["descriptor_validation_exit_code"], 0)
        self.assertEqual(verification["apply_check_exit_code"], 0)
        self.assertEqual(verification["apply_exit_code"], 0)
        self.assertEqual(verification["changed_files_after_apply"], ["src/V3Options.cpp", "src/V3Options.h"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["std_atoi_replaced_for_sim_accel_count_parser"])
        self.assertFalse(policy["build_executed_by_this_gate"])
        self.assertFalse(policy["hardening_smoke_executed_by_this_gate"])
        self.assertFalse(policy["strict_integer_parsing_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )

    def test_run_gate_records_rebuilt_binary_and_hardening_smoke(self) -> None:
        gate = self.read_run_gate()

        self.assertEqual(
            gate["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate",
        )

        build = gate["build_result"]
        self.assertEqual(build["descriptor_validation_exit_code"], 0)
        self.assertEqual(build["apply_check_exit_code"], 0)
        self.assertEqual(build["apply_exit_code"], 0)
        self.assertEqual(build["autoconf_exit_code"], 0)
        self.assertEqual(build["configure_exit_code"], 0)
        self.assertEqual(build["make_verilator_bin_exit_code"], 0)

        observed = gate["observed_result"]
        self.assertEqual(observed["command_count"], 6)
        self.assertTrue(observed["all_positive_cases_passed"])
        self.assertTrue(observed["all_hardening_rejection_cases_failed_as_expected"])
        self.assertTrue(observed["suffix_cases_prove_std_atoi_prefix_behavior_rejected"])
        self.assertTrue(observed["negative_separate_token_cases_reached_value_validation"])
        self.assertFalse(observed["negative_separate_token_cases_rejected_by_tokenizer"])

        cases = {case["name"]: case for case in gate["case_results"]}
        self.assertEqual(cases["accept_sidecar_gpu_64x1"]["observed_exit_code"], 0)
        self.assertEqual(cases["accept_sidecar_gpu_1x64"]["observed_exit_code"], 0)
        self.assertEqual(
            cases["reject_negative_states_separate_token"]["classification"],
            "strict_integer_validation_rejection",
        )
        self.assertIn("-1", cases["reject_negative_steps_separate_token"]["observed_diagnostic_summary"])
        self.assertIn("64abc", cases["reject_non_numeric_states_suffix"]["observed_diagnostic_summary"])
        self.assertIn("1abc", cases["reject_non_numeric_steps_suffix"]["observed_diagnostic_summary"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["verilator_bin_rebuilt_for_current_hardening_patch"])
        self.assertTrue(policy["parser_integer_hardening_smoke_passed"])
        self.assertFalse(policy["sidecar_handoff_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["rtl_simulation_execution_allowed_by_this_gate"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate",
        )

    def test_run_review_accepts_scoped_hardening_and_selects_handoff_boundary(self) -> None:
        review = self.read_run_review_gate()

        self.assertEqual(
            review["source_run_gate"],
            "config/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json",
        )
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_sidecar_handoff_boundary_gate",
        )
        self.assertTrue(review["review_decision"]["accepted"])

        accepted = review["accepted_result"]
        self.assertTrue(accepted["parser_integer_hardening_smoke_passed"])
        self.assertTrue(accepted["suffix_cases_prove_std_atoi_prefix_behavior_rejected"])
        self.assertTrue(accepted["negative_separate_token_cases_reached_value_validation"])
        self.assertFalse(accepted["negative_separate_token_cases_rejected_by_tokenizer"])

        scope = review["accepted_claim_scope"]
        self.assertTrue(scope["scoped_parser_only_strict_integer_validation_accepted"])
        self.assertEqual(scope["accepted_options"], ["--sim-accel-states", "--sim-accel-steps"])
        self.assertFalse(scope["sidecar_handoff_accepted"])
        self.assertFalse(scope["coverage_output_equivalence_accepted"])

        next_workstream = review["selected_next_workstream"]
        self.assertEqual(
            next_workstream["name"],
            "define_verilator_native_option_parser_sidecar_handoff_boundary_gate",
        )
        self.assertIn("parsed native option fields", next_workstream["reason"])

        policy = review["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["scoped_strict_integer_parsing_result_accepted"])
        self.assertTrue(policy["next_sidecar_handoff_boundary_definition_allowed"])
        self.assertFalse(policy["sidecar_handoff_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertEqual(
            review["next_task"],
            "define_verilator_native_option_parser_sidecar_handoff_boundary_gate",
        )


if __name__ == "__main__":
    unittest.main()
