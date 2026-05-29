import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATES = REPO_ROOT / "config" / "scaling_gates"
TOOLS = REPO_ROOT / "src" / "tools"

PREFIX = (
    "public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_"
    "broader_shape_sweep_repeat_median"
)
RESULT_GATE = GATES / f"{PREFIX}_result_gate.json"
REVIEW_GATE = GATES / f"{PREFIX}_review_gate.json"


def gate(name: str) -> Path:
    return GATES / name


COMPLETION_GATE = gate("public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json")
SELECTION_GATE = gate("next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_public_pack_refresh_gate.json")
POLICY_GATE = gate("define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json")
WORKFLOW_GATE = gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_workflow_gate.json")
POLICY_DRY_RUN_RESULT_GATE = gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_result_gate.json")
POLICY_DRY_RUN_REVIEW_GATE = gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_review_gate.json")
POLICY_PUBLIC_REFRESH_GATE = gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json")
REPORTS = (
    "reports/filelist_broader_shape_repeat_median_summary.json",
    "reports/filelist_broader_shape_repeat_filelist_paged_attention_kv_score_64x1_median.json",
    "reports/filelist_broader_shape_repeat_filelist_paged_attention_kv_score_1x64_median.json",
    "reports/filelist_broader_shape_repeat_filelist_known_template_pulp_ita_mha_64x1_median.json",
    "reports/filelist_broader_shape_repeat_filelist_known_template_pulp_ita_mha_1x64_median.json",
)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class PublicPackRepeatMedianRefreshGatesTest(unittest.TestCase):
    def test_result_and_review_gate_accept_packaging_only_dry_run(self) -> None:
        result = read_json(RESULT_GATE)
        review = read_json(REVIEW_GATE)

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["next_task"], f"review_{PREFIX}_gate")
        self.assertEqual(review["source_result_gate"], f"config/scaling_gates/{PREFIX}_result_gate.json")
        self.assertEqual(review["current_priority"], "define_public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate")
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertFalse(result["acceptance_policy"]["archive_created"])
        self.assertFalse(review["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_option_claim_allowed_by_gate_alone"])

        for report in REPORTS:
            self.assertIn(report, result["observed_generated_report_includes"])

    def test_externalization_completion_gate_closes_scoped_refresh(self) -> None:
        completion = read_json(COMPLETION_GATE)

        self.assertTrue(completion["decision"]["externalization_boundary_complete"])
        self.assertEqual(completion["closed_scope"]["repeat_count"], 3)
        self.assertEqual(completion["closed_scope"]["total_sample_count"], 12)
        self.assertEqual(completion["closed_scope"]["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(completion["next_task"], "select_next_measurement_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_public_pack_refresh")
        self.assertFalse(completion["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertFalse(completion["acceptance_policy"]["gem_comparison_claim_allowed_by_gate_alone"])

    def test_next_selection_gate_chooses_scoped_policy_broadening(self) -> None:
        selection = read_json(SELECTION_GATE)

        self.assertEqual(selection["current_priority"], "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate")
        self.assertEqual(selection["accepted_evidence"]["repeat_count"], 3)
        self.assertEqual(selection["accepted_evidence"]["total_sample_count"], 12)
        self.assertEqual(selection["accepted_evidence"]["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(selection["decision"]["selected_next_workstream"], "scoped_broader_filelist_gpu_allocation_policy")
        self.assertFalse(selection["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(selection["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_broader_policy_definition_keeps_scope_and_fallbacks_explicit(self) -> None:
        policy = read_json(POLICY_GATE)

        self.assertEqual(policy["current_priority"], "add_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_workflow")
        self.assertEqual(policy["policy_boundary"]["input_evidence"]["repeat_count"], 3)
        self.assertEqual(policy["policy_boundary"]["input_evidence"]["target_shape_pair_count"], 8)
        self.assertEqual(policy["policy_boundary"]["input_evidence"]["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(policy["policy_boundary"]["initial_policy_rules"][0]["recommendation"]["recommended_shape"], "64x1")
        self.assertEqual(policy["policy_boundary"]["initial_policy_rules"][2]["recommendation"]["recommended_shape"], "32x1")
        self.assertFalse(policy["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_broader_policy_workflow_adds_distinct_dry_run_surface(self) -> None:
        workflow = read_json(WORKFLOW_GATE)

        self.assertEqual(workflow["current_priority"], "run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_gate")
        self.assertEqual(workflow["public_interface"]["dry_run_command"], "python3 src/tools/run_results_reproduction.py --filelist-broader-shape-gpu-allocation-policy --dry-run")
        self.assertTrue(workflow["public_interface"]["dry_run_only"])
        self.assertFalse(workflow["public_interface"]["writes_files"])
        self.assertEqual(workflow["workflow_scope"]["target_shape_pair_count"], 8)
        self.assertEqual(workflow["workflow_scope"]["recommendation_policy"][0]["recommended_shape"], "64x1")
        self.assertEqual(workflow["workflow_scope"]["recommendation_policy"][0]["fallback_shape"], "32x1")
        self.assertFalse(workflow["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(workflow["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

    def test_broader_policy_cli_is_json_only_and_dry_run_only(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--filelist-broader-shape-gpu-allocation-policy",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed_filelist_broader_shape_gpu_allocation_policy_dry_run")
        self.assertEqual(payload["source_policy_gate"], "config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json")
        self.assertEqual(payload["source_evidence"]["target_shape_pair_count"], 8)
        self.assertEqual([item["recommended_shape"] for item in payload["recommendations"]], ["64x1", "64x1"])
        self.assertEqual([item["confidence"] for item in payload["fallback_recommendations"]], ["medium", "medium"])
        self.assertNotIn(str(REPO_ROOT), result.stdout)

        refused = subprocess.run(
            [sys.executable, "src/tools/run_results_reproduction.py", "--filelist-broader-shape-gpu-allocation-policy"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("dry-run only", refused.stderr)

    def test_broader_policy_dry_run_review_selects_public_refresh(self) -> None:
        result = read_json(POLICY_DRY_RUN_RESULT_GATE)
        review = read_json(POLICY_DRY_RUN_REVIEW_GATE)
        refresh = read_json(POLICY_PUBLIC_REFRESH_GATE)
        refresh_result = read_json(
            GATES / "public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_result_gate.json"
        )
        refresh_review = read_json(
            GATES / "public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_review_gate.json"
        )
        completion = read_json(
            GATES / "public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json"
        )
        selection = read_json(GATES / "next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_public_pack_refresh_gate.json")
        definition = read_json(GATES / "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json")
        execution_result = read_json(GATES / "filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json")
        execution_review = read_json(GATES / "filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json")
        execution_public_refresh = read_json(GATES / "public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json")
        execution_public_refresh_result = read_json(GATES / "public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json")
        execution_public_refresh_review = read_json(GATES / "public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json")
        execution_public_completion = read_json(GATES / "public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json")
        execution_next_selection = read_json(gate("next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_public_pack_refresh_gate.json"))
        policy_repeat_definition = read_json(gate("define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate.json"))
        policy_repeat_workflow = read_json(gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_workflow_gate.json"))
        policy_repeat_dry_run_result = read_json(gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_result_gate.json"))
        policy_repeat_dry_run_review = read_json(gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_review_gate.json"))
        policy_repeat_measurement = read_json(gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_measurement_gate.json")); policy_repeat_review = read_json(gate("filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json")); policy_repeat_public = read_json(gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json")); policy_repeat_public_result = read_json(gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_result_gate.json")); policy_repeat_public_review = read_json(gate("public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json")); policy_repeat_completion = read_json(gate("public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json")); native_option_boundary = read_json(gate("define_verilator_native_option_prototype_boundary_gate.json")); native_option_result = read_json(gate("verilator_native_option_prototype_boundary_dry_run_result_gate.json")); native_option_review = read_json(gate("verilator_native_option_prototype_boundary_dry_run_review_gate.json")); filelist_resolution = read_json(gate("define_verilator_native_option_prototype_filelist_target_resolution_gate.json")); registry_result = read_json(gate("verilator_native_option_prototype_filelist_registry_result_gate.json")); registry_review = read_json(gate("verilator_native_option_prototype_filelist_registry_review_gate.json")); registry_public = read_json(gate("public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate.json")); registry_public_result = read_json(gate("public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_result_gate.json")); registry_public_review = read_json(gate("public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_review_gate.json")); registry_completion = read_json(gate("public_benchmark_pack_externalization_completion_after_verilator_native_option_prototype_filelist_registry_gate.json"))

        self.assertEqual(result["current_priority"], "review_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_gate")
        self.assertEqual([item["recommended_shape"] for item in result["observed_policy"]["recommendations"]], ["64x1", "64x1"])
        self.assertEqual([item["recommended_shape"] for item in result["observed_policy"]["fallback_recommendations"]], ["32x1", "32x1"])
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(review["current_priority"], "define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate")
        self.assertFalse(refresh["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual((refresh_result["exit_code"], refresh_result["next_task"]), (0, "review_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate"))
        self.assertEqual((refresh_review["source_result_gate"], refresh_review["current_priority"]), ("config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_result_gate.json", "define_public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate"))
        self.assertTrue(completion["decision"]["externalization_boundary_complete"])
        self.assertEqual((completion["closed_scope"]["recommended_shape"], completion["closed_scope"]["fallback_shape"]), ("64x1", "32x1"))
        self.assertFalse(completion["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual((selection["current_priority"], selection["decision"]["selected_next_workstream"], selection["required_next_gate"]["name"]), ("define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate", "scoped_broader_filelist_gpu_allocation_policy_execution", "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate"))
        self.assertFalse(selection["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual((definition["current_priority"], definition["execution_scope"]["recommended_shape"], definition["execution_scope"]["fallback_shape"]), ("run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate", "64x1", "32x1"))
        self.assertFalse(definition["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual((execution_result["command_count"], execution_result["shape"], execution_result["fallback_executed"]), (2, "64x1", False))
        self.assertEqual((execution_result["result_summary"]["max_coverage_output_mismatch_count"], execution_result["result_summary"]["strict_output_word_count_per_state"], execution_result["result_summary"]["strict_output_byte_count_per_state"]), (0, 29, 116))
        self.assertEqual([item["raw_full_state_mismatch_count"] for item in execution_result["executed_commands"]], [2823, 2369])
        self.assertEqual((execution_review["review_decision"]["accepted"], execution_review["current_priority"]), (True, "define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate"))
        self.assertFalse(execution_review["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual((execution_public_refresh["current_priority"], execution_public_refresh["evidence_summary"]["command_count"], execution_public_refresh["evidence_summary"]["shape"]), ("run_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate", 2, "64x1"))
        self.assertEqual((execution_public_refresh["evidence_summary"]["max_coverage_output_mismatch_count"], execution_public_refresh["evidence_summary"]["raw_full_state_mismatch_counts"]), (0, [2823, 2369]))
        self.assertFalse(execution_public_refresh["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertEqual((execution_public_refresh_result["exit_code"], execution_public_refresh_result["archive_created"]), (0, False))
        self.assertEqual((execution_public_refresh_result["observed_output_summary"]["include_count"], execution_public_refresh_result["observed_output_summary"]["exclude_count"]), (521, 2))
        self.assertEqual((execution_public_refresh_result["accepted_execution_payload"]["command_count"], execution_public_refresh_result["accepted_execution_payload"]["raw_full_state_mismatch_counts"]), (2, [2823, 2369]))
        self.assertEqual((execution_public_refresh_review["review_decision"]["accepted"], execution_public_refresh_review["current_priority"]), (True, "define_public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate"))
        self.assertFalse(execution_public_refresh_review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertTrue(execution_public_completion["decision"]["externalization_boundary_complete"])
        self.assertEqual((execution_public_completion["closed_scope"]["shape"], execution_public_completion["closed_scope"]["fallback_shape"], execution_public_completion["closed_scope"]["command_count"]), ("64x1", "32x1", 2))
        self.assertEqual((execution_public_completion["closed_scope"]["max_coverage_output_mismatch_count"], execution_public_completion["closed_scope"]["raw_full_state_mismatch_counts"]), (0, [2823, 2369]))
        self.assertEqual(execution_public_completion["next_task"], "select_next_measurement_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_public_pack_refresh")
        self.assertFalse(execution_public_completion["acceptance_policy"]["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual((execution_next_selection["decision"]["selected_next_workstream"], execution_next_selection["current_priority"]), ("policy_selected_broader_filelist_repeat_median_timing", "define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate"))
        self.assertFalse(execution_next_selection["acceptance_policy"]["native_verilator_option_claim_allowed_by_gate_alone"])
        self.assertEqual((policy_repeat_definition["current_priority"], policy_repeat_definition["measurement_boundary"]["target_count"], policy_repeat_definition["measurement_boundary"]["total_sample_count"]), ("add_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_workflow", 2, 6))
        self.assertEqual(policy_repeat_definition["workflow_gap"]["required_shapes"], ["64x1"])
        self.assertFalse(policy_repeat_definition["acceptance_policy"]["repeat_median_claim_allowed_by_gate_alone"])
        self.assertEqual((policy_repeat_workflow["current_priority"], policy_repeat_workflow["workflow_scope"]["target_count"], policy_repeat_workflow["workflow_scope"]["shape"]), ("run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_gate", 2, "64x1"))
        self.assertFalse(policy_repeat_workflow["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertEqual((policy_repeat_dry_run_result["current_priority"], policy_repeat_dry_run_result["observed_dry_run_contract"]["target_count"], policy_repeat_dry_run_result["observed_dry_run_contract"]["compare_command_count"]), ("review_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_gate", 2, 6))
        self.assertEqual((policy_repeat_dry_run_review["current_priority"], policy_repeat_dry_run_review["accepted_result"]["shape"], policy_repeat_dry_run_review["accepted_result"]["total_sample_count"]), ("run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate", "64x1", 6))
        self.assertEqual((policy_repeat_measurement["current_priority"], policy_repeat_measurement["measurement_scope"]["target_count"], policy_repeat_measurement["measurement_scope"]["total_sample_count"], policy_repeat_measurement["measured_result"]["all_coverage_output_passed"], policy_repeat_measurement["measurement_scope"]["public_pack_reports_limited_to_aggregate_and_median_json"]), ("review_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate", 2, 6, True, True)); self.assertEqual((policy_repeat_review["current_priority"], policy_repeat_review["review_result"]["total_sample_count"], policy_repeat_review["acceptance_policy"]["per_sample_stdout_reports_claim_allowed_by_this_gate"]), ("define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate", 6, False))
        self.assertEqual((policy_repeat_public["next_task"], policy_repeat_public["evidence_summary"]["total_sample_count"], policy_repeat_public["acceptance_policy"]["per_sample_stdout_reports_claim_allowed_by_this_gate"]), ("run_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate", 6, False)); self.assertEqual((policy_repeat_public_result["exit_code"], policy_repeat_public_result["observed_output_summary"]["include_count"], policy_repeat_public_result["observed_output_summary"]["per_sample_stdout_reports_included"]), (0, 535, False)); self.assertEqual((policy_repeat_public_review["review_decision"]["accepted"], policy_repeat_public_review["current_priority"], policy_repeat_completion["next_task"]), (True, "define_public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate", "select_next_measurement_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_public_pack_refresh")); self.assertEqual((native_option_boundary["current_priority"], native_option_boundary["required_next_gate"]["name"], native_option_boundary["prototype_boundary"]["known_gap_before_native_or_filelist_direct_claim"]["current_registered_equivalent_targets"]), ("run_verilator_native_option_prototype_boundary_dry_run_gate", "run_verilator_native_option_prototype_boundary_dry_run_gate", ["paged_attention_kv_score", "pulp_ita_mha"])); self.assertEqual((native_option_result["exit_code"], native_option_result["command_count"], native_option_result["dry_run_scope"]["filelist_targets_directly_supported_by_shim"]), (0, 4, False)); self.assertEqual((native_option_review["review_decision"]["accepted"], native_option_review["current_priority"], native_option_review["required_next_gate"]["name"]), (True, "define_verilator_native_option_prototype_filelist_target_resolution_gate", "define_verilator_native_option_prototype_filelist_target_resolution_gate")); self.assertEqual((filelist_resolution["decision"]["selected_resolution"], filelist_resolution["current_priority"], filelist_resolution["required_next_gate"]["name"]), ("static_registry_entries_for_tracked_filelist_templates", "add_verilator_native_option_prototype_filelist_targets_to_sidecar_registry_gate", "add_verilator_native_option_prototype_filelist_targets_to_sidecar_registry_gate")); self.assertEqual((registry_result["implementation"]["new_planner_added"], registry_result["commands"][0]["exit_code"], registry_review["current_priority"]), (False, 0, "define_public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate")); self.assertEqual((registry_public["current_priority"], registry_public["next_task"], registry_public["evidence_summary"]["command_count"]), ("run_public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate", "run_public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate", 5)); self.assertFalse(registry_public["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"]); self.assertFalse(registry_public["acceptance_policy"]["arbitrary_rtl_dependency_inference_claim_allowed_by_gate_alone"]); self.assertEqual((registry_public_result["exit_code"], registry_public_result["observed_output_summary"]["include_count"], registry_public_result["observed_output_summary"]["exclude_count"]), (0, 546, 2)); self.assertEqual((registry_public_review["review_decision"]["accepted"], registry_public_review["current_priority"]), (True, "define_public_benchmark_pack_externalization_completion_after_verilator_native_option_prototype_filelist_registry_gate")); self.assertEqual((registry_completion["decision"]["externalization_boundary_complete"], registry_completion["closed_scope"]["preview_and_plan_command_count"], registry_completion["next_task"]), (True, 5, "select_next_measurement_after_verilator_native_option_prototype_filelist_registry_public_pack_refresh"))

    def test_public_pack_manifest_includes_refresh_result_review_and_reports(self) -> None:
        sys.path.insert(0, str(TOOLS))
        try:
            from results_reproduction_manifest import PUBLIC_PACK_ARCHIVE_PATHS
        finally:
            sys.path.pop(0)

        self.assertIn(f"records/scaling_gates/{PREFIX}_result_gate.json", PUBLIC_PACK_ARCHIVE_PATHS)
        self.assertIn(f"records/scaling_gates/{PREFIX}_review_gate.json", PUBLIC_PACK_ARCHIVE_PATHS)
        for record in (
            "records/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json",
            "records/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_public_pack_refresh_gate.json",
            "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json",
            "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_workflow_gate.json",
            "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_result_gate.json",
            "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_review_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_result_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_review_gate.json",
            "records/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json",
            "records/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_public_pack_refresh_gate.json",
            "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json",
            "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json", "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json",
            "records/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json",
            "records/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_public_pack_refresh_gate.json",
            "records/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate.json",
            "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_workflow_gate.json",
            "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_result_gate.json",
            "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_review_gate.json", "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_measurement_gate.json", "records/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json", "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json", "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_result_gate.json", "records/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json", "records/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json", "records/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_public_pack_refresh_gate.json", "records/scaling_gates/define_verilator_native_option_prototype_boundary_gate.json", "records/scaling_gates/verilator_native_option_prototype_boundary_dry_run_result_gate.json", "records/scaling_gates/verilator_native_option_prototype_boundary_dry_run_review_gate.json", "records/scaling_gates/define_verilator_native_option_prototype_filelist_target_resolution_gate.json", "records/scaling_gates/verilator_native_option_prototype_filelist_registry_result_gate.json", "records/scaling_gates/verilator_native_option_prototype_filelist_registry_review_gate.json", "records/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate.json", "records/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_result_gate.json", "records/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_review_gate.json", "records/scaling_gates/public_benchmark_pack_externalization_completion_after_verilator_native_option_prototype_filelist_registry_gate.json", "records/scaling_gates/next_measurement_selection_after_verilator_native_option_prototype_filelist_registry_public_pack_refresh_gate.json",
        ):
            self.assertIn(record, PUBLIC_PACK_ARCHIVE_PATHS)
        for report in ("reports/filelist_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json", "reports/filelist_known_template_pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json", *REPORTS):
            self.assertIn(report, PUBLIC_PACK_ARCHIVE_PATHS)
