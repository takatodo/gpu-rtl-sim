import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "config" / "scaling_gates" / "define_commit_split_and_public_pack_cleanup_gate.json"
REVIEW_GATE = REPO_ROOT / "config" / "scaling_gates" / "review_commit_split_and_public_pack_cleanup_gate.json"
RESOLUTION_GATE = REPO_ROOT / "config" / "scaling_gates" / "resolve_commit_split_line_guard_risks_gate.json"
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
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))

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
        self.assertEqual(selection["current_priority"], "execute_commit_split_index_rewrite_gate")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/resolve_commit_split_line_guard_risks_gate.json",
        )
        self.assertEqual(selection["repository_cleanup"]["records_scaling_gate_json_count"], 802)

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


if __name__ == "__main__":
    unittest.main()
