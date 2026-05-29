import json
import unittest

from tests.contract.hybrid_cli_helpers import REPO_ROOT, HybridCliTestCase


class FilelistRepeatMedianCliTest(HybridCliTestCase):
    def test_filelist_shape_breadth_repeat_median_dry_run_command_passes(self) -> None:
        specs = (
            (
                "--filelist-shape-breadth-repeat-median",
                "32",
                "32",
                "filelist_shape_breadth_repeat_median_summary.json",
            ),
            (
                "--filelist-broader-shape-repeat-median",
                "64",
                "64",
                "filelist_broader_shape_repeat_median_summary.json",
            ),
        )
        for option, state_count, step_count, summary in specs:
            with self.subTest(option=option):
                result = self.run_python_tool(
                    "src/tools/run_results_reproduction.py",
                    option,
                    "3",
                    "--dry-run",
                )
                stdout = result.stdout
                self.assertIn("filelist_paged_attention_kv_score", stdout)
                self.assertIn("filelist_known_template_pulp_ita_mha", stdout)
                self.assertIn(f"--nstates {state_count} --steps 1", stdout)
                self.assertIn(f"--nstates 1 --steps {step_count}", stdout)
                self.assertEqual(stdout.count("_compare.json"), 12)
                self.assertIn(f"+ write reports/{summary}", stdout)
                self.assert_no_local_absolute_paths(stdout)

    def test_filelist_broader_policy_repeat_median_dry_run_command_passes(self) -> None:
        result = self.run_python_tool(
            "src/tools/run_results_reproduction.py",
            "--filelist-broader-policy-repeat-median",
            "3",
            "--dry-run",
        )
        stdout = result.stdout
        self.assertIn("filelist_paged_attention_kv_score", stdout)
        self.assertIn("filelist_known_template_pulp_ita_mha", stdout)
        self.assertIn("--nstates 64 --steps 1", stdout)
        self.assertNotIn("--nstates 1 --steps 64", stdout)
        self.assertEqual(stdout.count("_compare.json"), 6)
        self.assertIn("+ write reports/filelist_broader_policy_repeat_median_summary.json", stdout)
        self.assert_no_local_absolute_paths(stdout)

    def test_filelist_shape_breadth_repeat_median_rejects_non_positive_repeat(self) -> None:
        for option in (
            "--filelist-shape-breadth-repeat-median",
            "--filelist-broader-shape-repeat-median",
            "--filelist-broader-policy-repeat-median",
        ):
            with self.subTest(option=option):
                result = self.run_python_tool(
                    "src/tools/run_results_reproduction.py",
                    option,
                    "0",
                    "--dry-run",
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{option} must be positive", result.stderr)

    def test_filelist_shape_breadth_repeat_median_workloads_match_tracked_templates(self) -> None:
        self.add_tools_to_path()
        from results_reproduction_workloads import (
            filelist_broader_policy_repeat_median_workloads,
            filelist_broader_shape_repeat_median_workloads,
            filelist_shape_breadth_repeat_median_workloads,
        )

        workload_sets = (
            (filelist_shape_breadth_repeat_median_workloads(), {"32x1", "1x32"}, 4),
            (filelist_broader_shape_repeat_median_workloads(), {"64x1", "1x64"}, 4),
            (filelist_broader_policy_repeat_median_workloads(), {"64x1"}, 2),
        )
        expected_templates = {
            "filelist_paged_attention_kv_score": "filelist_paged_attention_kv_score.json",
            "filelist_known_template_pulp_ita_mha": "filelist_known_template_pulp_ita_mha.json",
        }
        for workloads, shapes, expected_count in workload_sets:
            self.assertEqual(len(workloads), expected_count)
            self.assertEqual({f"{workload.nstates}x{workload.steps}" for workload in workloads}, shapes)
            self.assertEqual(
                {workload.target_name for workload in workloads},
                {"filelist_paged_attention_kv_score", "filelist_known_template_pulp_ita_mha"},
            )
            for workload in workloads:
                with self.subTest(workload=workload.name):
                    self.assertEqual(workload.coverage_target, workload.target_name)
                    self.assertTrue(workload.source_gate.startswith("config/scaling_gates/"))
                    self.assertTrue((REPO_ROOT / workload.source_gate).is_file())
                    self.assertEqual(
                        workload.obj_dir,
                        REPO_ROOT / "artifacts" / f"{workload.target_name}_obj_dir",
                    )
                    template = json.loads(
                        (
                            REPO_ROOT
                            / "config"
                            / "slice_launch_templates"
                            / expected_templates[workload.target_name]
                        ).read_text(encoding="utf-8")
                    )
                    self.assertEqual(template["source_closure"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
