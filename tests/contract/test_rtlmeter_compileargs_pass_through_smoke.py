import json
import tempfile

from tests.contract.hybrid_cli_helpers import HybridCliTestCase, REPO_ROOT


class RtlmeterCompileArgsPassThroughSmokeTest(HybridCliTestCase):
    def test_compileargs_use_gpu_reaches_wrapper_visible_argv_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_compileargs_pass_through

        descriptor = REPO_ROOT / "third_party" / "rtlmeter" / "designs" / "Example" / "descriptor.yaml"
        before = descriptor.read_text(encoding="utf-8")

        report = inspect_rtlmeter_compileargs_pass_through(
            "Example:kind:hello",
            '--use-gpu',
        )

        after = descriptor.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(report["surface"], "rtlmeter_compileargs_pass_through_smoke")
        self.assertTrue(report["gpu_intent_reaches_wrapper"])
        self.assertFalse(report["runtime_abi"])
        self.assertFalse(report["execution_authority"])

        capture = report["command_capture"]
        wrapper = report["wrapper_inspection"]
        self.assertIn("--use-gpu", capture["verilator_command_argv"])
        self.assertIn("--use-gpu", wrapper["gpu_intent_flags"])
        self.assertEqual(wrapper["status"], "gpu_intent_captured_not_ready")
        self.assertIn("compileArgs smoke proves pass-through only", " ".join(report["non_claims"]))
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_compileargs_shlex_split_matches_rtlmeter_single_string_contract(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_compileargs_pass_through

        report = inspect_rtlmeter_compileargs_pass_through(
            "Example:kind:hello",
            '--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1',
        )

        self.assertEqual(
            report["extra_args"],
            ["--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"],
        )
        self.assertEqual(
            report["wrapper_inspection"]["status"],
            "ready_for_rtlmeter_sidecar_planning",
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_missing_rtlmeter_source_returns_clear_non_executing_status(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_compileargs_pass_through

        with tempfile.TemporaryDirectory() as tmpdir:
            report = inspect_rtlmeter_compileargs_pass_through(
                "Example:kind:hello",
                "--use-gpu",
                rtlmeter_root=tmpdir,
            )

        self.assertEqual(report["status"], "rtlmeter_source_unavailable")
        self.assertFalse(report["gpu_intent_reaches_wrapper"])
        self.assertIsNone(report["command_capture"])
        self.assertIsNone(report["wrapper_inspection"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))
