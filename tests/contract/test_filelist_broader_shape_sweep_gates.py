import json
import unittest

from tests.contract.hybrid_cli_helpers import REPO_ROOT


GATES = REPO_ROOT / "records" / "scaling_gates"


def read_gate(name: str) -> dict[str, object]:
    return json.loads((GATES / name).read_text(encoding="utf-8"))


class FilelistBroaderShapeSweepGatesTest(unittest.TestCase):
    def test_filelist_gpu_allocation_broader_shape_sweep_definition_gate(self) -> None:
        gate = read_gate("define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate.json")

        self.assertEqual(
            gate["current_priority"],
            "run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_gate",
        )
        boundary = gate["sweep_boundary"]
        self.assertEqual(boundary["selected_dry_run_command_count"], 4)
        self.assertEqual(boundary["correctness_policy"], "coverage_output_equivalence")
        roles = {item["shape"]: item["role"] for item in boundary["shape_roles"]}
        self.assertEqual(roles["64x1"], "larger_state_parallel_probe")
        self.assertEqual(roles["1x64"], "larger_repeated_step_probe")
        commands = [
            command
            for target in boundary["selected_targets"]
            for command in target["selected_dry_run_commands"]
        ]
        self.assertEqual(len(commands), 4)
        self.assertTrue(all("--dry-run" in command for command in commands))
        self.assertTrue(all("--shape 64x1" in command or "--shape 1x64" in command for command in commands))
        self.assertFalse(gate["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_filelist_gpu_allocation_broader_shape_sweep_dry_run_result_and_review(self) -> None:
        result_gate = read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_result_gate.json")
        review_gate = read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_review_gate.json")
        definition_gate = read_gate("define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json")

        self.assertEqual(result_gate["command_count"], 4)
        self.assertEqual(result_gate["shapes"], ["64x1", "1x64"])
        self.assertEqual(result_gate["generated_reports"], [])
        self.assertTrue(result_gate["result_summary"]["all_commands_exited_zero"])
        self.assertFalse(result_gate["mutation_policy"]["generated_reports_or_artifacts_written"])
        self.assertEqual(review_gate["current_priority"], "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate")
        self.assertTrue(review_gate["review_decision"]["accepted"])
        self.assertEqual(definition_gate["current_priority"], "run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate")
        self.assertEqual({command["shape"] for command in definition_gate["execution_scope"]["commands"]}, {"64x1", "1x64"})

    def test_filelist_broader_shape_sweep_execution_public_pack_and_timing_chain(self) -> None:
        run_result = read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json")
        run_review = read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_review_gate.json")
        public_result = read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json")
        completion = read_gate("public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json")
        timing_gate = read_gate("define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json")

        self.assertEqual(run_result["command_count"], 4)
        self.assertTrue(run_result["result_summary"]["all_coverage_output_equivalence_passed"])
        self.assertEqual(run_result["result_summary"]["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(run_result["result_summary"]["raw_full_state_all_matched"])
        self.assertEqual(run_review["current_priority"], "define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate")
        self.assertTrue(public_result["acceptance_policy"]["public_pack_archive_dry_run_exited_zero"])
        self.assertEqual(len(public_result["observed_generated_report_includes"]), 4)
        self.assertEqual(completion["next_task"], "select_next_measurement_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_public_pack_refresh")
        self.assertEqual(timing_gate["current_priority"], "run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate")
        self.assertEqual(timing_gate["measurement_boundary"]["selected_shapes"], ["64x1", "1x64"])
        self.assertFalse(timing_gate["acceptance_policy"]["timing_or_speedup_claim_allowed_by_gate_alone"])

    def test_filelist_broader_shape_sweep_timing_repeat_chain(self) -> None:
        timing_result = read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json")
        timing_review = read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json")
        timing_public = read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json")
        refresh = (
            read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json"),
            read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json"),
            read_gate("public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json"),
            read_gate("next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_public_pack_refresh_gate.json"),
            read_gate("define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate.json"),
            read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_workflow_gate.json"),
            read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_measurement_gate.json"),
            read_gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json"),
            read_gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json"),
        )

        self.assertEqual((timing_result["current_priority"], len(timing_result["measured_shapes"])), ("review_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate", 4))
        self.assertTrue(timing_result["measurement_scope"]["all_coverage_output_passed"])
        self.assertEqual(refresh[0]["exit_code"], 0)
        self.assertEqual(refresh[3]["current_priority"], "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate")
        self.assertEqual(refresh[6]["measurement_scope"]["total_sample_count"], 12)
        self.assertEqual(refresh[6]["measurement_scope"]["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(refresh[8]["next_task"], "run_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate")
        self.assertFalse(timing_review["acceptance_policy"]["repeat_median_claim_allowed_by_gate_alone"])
        self.assertFalse(timing_public["acceptance_policy"]["repeat_median_claim_allowed_by_gate_alone"])
        self.assertFalse(refresh[8]["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])


if __name__ == "__main__":
    unittest.main()
