import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class VerilatorUseGpuFirstPathTest(HybridCliTestCase):
    def _supported_argv(self) -> list[str]:
        return [
            "--cc",
            "--timing",
            "-Mdir",
            "artifacts/filelist_known_template_pulp_ita_mha_obj_dir",
            "-f",
            "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
            "--top-module",
            "pulp_ita_mha_gpu_cov_tb",
            "--use-gpu",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
        ]

    def _passing_compare_report(self) -> dict[str, object]:
        return {
            "selected_acceptance_policy": {
                "name": "coverage_output_equivalence",
                "passed": True,
            },
            "coverage_output_policy": {
                "mismatch_count": 0,
            },
        }

    def test_supported_scoped_path_invokes_existing_template_launcher(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_first_path import execute_verilator_use_gpu_first_path

        calls = []

        def fake_launcher(resolution, repo_root):
            calls.append((resolution, repo_root))
            return {
                "returncode": 0,
                "compare_report_path": "reports/filelist_known_template_pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json",
                "compare_report": self._passing_compare_report(),
            }

        report = execute_verilator_use_gpu_first_path(self._supported_argv(), launcher=fake_launcher)

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_executed")
        self.assertEqual(report["accepted_source_authority"], "reviewed_materialized_filelist_template")
        self.assertEqual(
            report["sidecar_launcher_command_argv"],
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
                "--shape",
                "64x1",
            ],
        )
        self.assertEqual(len(calls), 1)
        self.assertTrue(report["sidecar_execution_invoked"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["fail_closed"])

    def test_unknown_filelist_rejects_before_launcher(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_first_path import execute_verilator_use_gpu_first_path

        argv = self._supported_argv()
        argv[argv.index("config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json")] = (
            "config/slice_launch_templates/pulp_ita_dotp.json"
        )
        report = execute_verilator_use_gpu_first_path(
            argv,
            launcher=lambda *_args: self.fail("unknown filelist must not launch sidecar"),
        )

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_rejected")
        self.assertIn("reviewed_filelist_authority", report["missing_required_inputs"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_top_mismatch_rejects_before_launcher(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_first_path import execute_verilator_use_gpu_first_path

        argv = self._supported_argv()
        argv[argv.index("pulp_ita_mha_gpu_cov_tb")] = "ita"
        report = execute_verilator_use_gpu_first_path(
            argv,
            launcher=lambda *_args: self.fail("top mismatch must not launch sidecar"),
        )

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_rejected")
        self.assertIn("top_module_match", report["missing_required_inputs"])
        self.assertFalse(report["sidecar_execution_invoked"])

    def test_missing_schedule_rejects_use_gpu_only(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_first_path import execute_verilator_use_gpu_first_path

        argv = self._supported_argv()[: self._supported_argv().index("--sim-accel")]
        report = execute_verilator_use_gpu_first_path(
            argv,
            launcher=lambda *_args: self.fail("bare --use-gpu must not launch sidecar"),
        )

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_rejected")
        self.assertIn("--sim-accel sidecar-gpu", report["missing_required_inputs"])
        self.assertIn("--sim-accel-states 64", report["missing_required_inputs"])
        self.assertIn("--sim-accel-steps 1", report["missing_required_inputs"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_missing_source_authority_rejects_before_launcher(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_first_path import execute_verilator_use_gpu_first_path

        argv = self._supported_argv()
        filelist_index = argv.index("-f")
        del argv[filelist_index : filelist_index + 2]
        report = execute_verilator_use_gpu_first_path(
            argv,
            launcher=lambda *_args: self.fail("missing source authority must not launch sidecar"),
        )

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_rejected")
        self.assertIn("reviewed_filelist_or_source_closure_authority", report["missing_required_inputs"])
        self.assertFalse(report["sidecar_execution_invoked"])

    def test_gpu_runtime_failure_is_not_cpu_as_gpu_success(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_first_path import execute_verilator_use_gpu_first_path

        report = execute_verilator_use_gpu_first_path(
            self._supported_argv(),
            launcher=lambda *_args: {
                "returncode": 1,
                "diagnostic": "classified_failure: gpu_runtime_unavailable",
            },
        )

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_launcher_failed")
        self.assertTrue(report["fail_closed"])
        self.assertTrue(report["sidecar_execution_invoked"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertEqual(report["sidecar_launcher_returncode"], 1)

    def test_compare_mismatch_rejects_launcher_success(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_first_path import execute_verilator_use_gpu_first_path

        bad_compare = self._passing_compare_report()
        bad_compare["coverage_output_policy"] = {"mismatch_count": 1}
        report = execute_verilator_use_gpu_first_path(
            self._supported_argv(),
            launcher=lambda *_args: {"returncode": 0, "compare_report": bad_compare},
        )

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_compare_failed")
        self.assertTrue(report["fail_closed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_cli_dry_run_is_json_and_does_not_execute(self) -> None:
        command = [
            "src/tools/verilator_use_gpu_first_path.py",
            *self._supported_argv(),
            "--first-use-gpu-dry-run",
        ]

        result = self.run_python_tool(*command)
        report = json.loads(result.stdout)

        self.assertEqual(report["status"], "verilator_use_gpu_first_path_dry_run_ready")
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assert_no_local_absolute_paths(result.stdout)
