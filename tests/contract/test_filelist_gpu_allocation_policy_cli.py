import json
import unittest

from tests.contract.hybrid_cli_helpers import REPO_ROOT, HybridCliTestCase


GATES = REPO_ROOT / "records" / "scaling_gates"


def read_gate(name: str) -> dict[str, object]:
    return json.loads((GATES / name).read_text(encoding="utf-8"))


class FilelistGpuAllocationPolicyCliTest(HybridCliTestCase):
    def test_filelist_shape_breadth_gpu_allocation_policy_is_dry_run_only(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_results_reproduction.py",
            "--filelist-shape-breadth-gpu-allocation-policy",
            "--dry-run",
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed_filelist_shape_breadth_gpu_allocation_policy_dry_run")
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["writes_files"])
        self.assertEqual(payload["source_evidence"]["repeat_count"], 3)
        recommendations = {item["target"]: item for item in payload["recommendations"]}
        self.assertEqual(
            sorted(recommendations),
            ["filelist_known_template_pulp_ita_mha", "filelist_paged_attention_kv_score"],
        )
        for recommendation in recommendations.values():
            self.assertEqual(recommendation["recommended_shape"], "32x1")
            self.assertEqual(recommendation["recommended_nstates"], 32)
            self.assertEqual(recommendation["recommended_steps"], 1)
            self.assertEqual(recommendation["confidence"], "high")
            self.assertEqual(recommendation["source_closure_status"], "complete")
            self.assertEqual(recommendation["timing_evidence"], "repeat_median_present")
            self.assertEqual(recommendation["evidence"]["coverage_output_mismatch_count"], 0)

        case_confidence = {
            item["case"]: item["confidence"]
            for item in payload["refusals_or_low_confidence"]
        }
        self.assertEqual(case_confidence["target_not_in_reviewed_filelist_set"], "refused")
        self.assertEqual(case_confidence["source_closure_not_complete"], "refused")
        self.assertEqual(case_confidence["missing_repeat_median_timing_evidence"], "low")
        self.assertEqual(case_confidence["operator_requests_single_state_repeated_step_workload"], "low")
        self.assertIn("not automatic optimal GPU allocation for any design", payload["non_claims"])
        self.assert_no_local_absolute_paths(result.stdout)

        result = self.run_python_tool(
            "src/tools/run_results_reproduction.py",
            "--filelist-shape-breadth-gpu-allocation-policy",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dry-run only", result.stderr)

    def test_filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_commands_pass(self) -> None:
        commands = (
            (
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/filelist_paged_attention_kv_score.json",
                "--shape",
                "32x1",
                "--dry-run",
            ),
            (
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
                "--shape",
                "32x1",
                "--dry-run",
            ),
        )

        for command in commands:
            with self.subTest(command=" ".join(command)):
                stdout = self.run_python_tool(*command).stdout
                self.assertIn("--nstates 32 --steps 1", stdout)
                self.assertIn("--acceptance-policy coverage_output_equivalence", stdout)
                self.assertIn("--json-out reports/", stdout)
                self.assert_no_local_absolute_paths(stdout)

    def test_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_gate_selects_both_commands(self) -> None:
        gate = read_gate("define_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json")

        self.assertEqual(
            gate["current_priority"],
            "run_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate",
        )
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["execute_both_reviewed_policy_selected_commands_next"])
        self.assertEqual(policy["selected_shape"], "32x1")
        self.assertEqual(policy["later_mismatch_count_required"], 0)
        commands = gate["execution_scope"]["commands"]
        self.assertEqual(len(commands), 2)
        self.assertEqual(
            [command["target"] for command in commands],
            ["filelist_paged_attention_kv_score", "filelist_known_template_pulp_ita_mha"],
        )
        for command in commands:
            self.assertIn("--shape 32x1", command["command"])
            self.assertTrue(command["expected_compare_report"].startswith("reports/"))
            self.assertEqual(command["expected_output_words_per_state"], 29)
            self.assertEqual(command["expected_output_bytes_per_state"], 116)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_and_review(self) -> None:
        result_gate = read_gate("filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json")
        review_gate = read_gate("filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json")

        self.assertEqual(result_gate["current_priority"], "review_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate")
        self.assertTrue(result_gate["execution_result"]["all_commands_exited_zero"])
        self.assertTrue(result_gate["execution_result"]["all_compare_reports_passed_coverage_output_equivalence"])
        self.assertEqual(result_gate["execution_result"]["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(result_gate["execution_result"]["strict_output_word_count_per_state"], 29)
        self.assertEqual(result_gate["execution_result"]["strict_output_byte_count_per_state"], 116)
        self.assertEqual(len(result_gate["reports"]), 2)
        for report in result_gate["reports"]:
            self.assertTrue(report["report"].startswith("reports/"))
            self.assertEqual(report["selected_acceptance_policy"], "coverage_output_equivalence")
            self.assertTrue(report["selected_acceptance_policy_passed"])
            self.assertEqual(report["coverage_output_mismatch_count"], 0)
            self.assertFalse(report["raw_match"])
            self.assertTrue(report["normalized_final_state_equivalence"])

        self.assertTrue(review_gate["review_decision"]["accepted"])
        self.assertEqual(
            review_gate["current_priority"],
            "define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate",
        )
        self.assertFalse(review_gate["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_filelist_gpu_allocation_public_pack_and_next_selection(self) -> None:
        definition = read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json")
        result = read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json")
        review = read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json")
        completion = read_gate("public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json")
        selection = read_gate("next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_public_pack_refresh_gate.json")

        self.assertEqual(definition["evidence_summary"]["command_count"], 2)
        self.assertEqual(definition["evidence_summary"]["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(definition["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["acceptance_policy"]["archive_created"])
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertTrue(completion["decision"]["externalization_boundary_complete"])
        self.assertEqual(completion["closed_scope"]["shape"], "32x1")
        self.assertEqual(completion["closed_scope"]["command_count"], 2)
        self.assertEqual(completion["closed_scope"]["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(selection["current_priority"], "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate")
        self.assertEqual(selection["decision"]["selected_next_workstream"], "broader_filelist_shape_sweep")
        self.assertFalse(selection["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])


if __name__ == "__main__":
    unittest.main()
