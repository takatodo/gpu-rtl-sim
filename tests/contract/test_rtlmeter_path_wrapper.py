from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterPathWrapperTest(HybridCliTestCase):
    def test_detects_use_gpu_without_rtlmeter_source_patch(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_verilator_wrapper_argv

        report = inspect_rtlmeter_verilator_wrapper_argv(
            [
                "--cc",
                "--main",
                "--exe",
                "--top-module",
                "top",
                "-f",
                "filelist",
                "--use-gpu",
            ]
        )

        self.assertEqual(report["surface"], "rtlmeter_verilator_path_wrapper")
        self.assertEqual(report["status"], "gpu_intent_captured_not_ready")
        self.assertTrue(report["gpu_intent_detected"])
        self.assertIn("--use-gpu", report["gpu_intent_flags"])
        self.assertFalse(report["requires_rtlmeter_source_patch"])
        self.assertFalse(report["execution_authority"])
        self.assertEqual(report["prototype_behavior"], "inspect_only_no_delegate_or_exec")
        self.assertTrue(report["prototype_exits_without_delegation"])
        self.assertFalse(report["delegate_to_real_verilator_required"])
        self.assertIn("--cc", report["minimal_supported_argv_surface_for_first_run"])
        self.assertIn("not the delegating runtime", " ".join(report["non_claims"]))
        self.assertIn("not prove RTLMeter acceleration", " ".join(report["non_claims"]))

    def test_ready_for_planning_requires_expanded_sidecar_schedule(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_verilator_wrapper_argv

        report = inspect_rtlmeter_verilator_wrapper_argv(
            [
                "--cc",
                "--top-module",
                "top",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ]
        )

        self.assertEqual(report["status"], "ready_for_rtlmeter_sidecar_planning")
        self.assertEqual(report["sidecar_accel"], "sidecar-gpu")
        self.assertEqual(report["sidecar_states"], "64")
        self.assertEqual(report["sidecar_steps"], "1")
        self.assertEqual(report["missing_required_inputs"], [])

    def test_unsupported_gpu_request_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_verilator_wrapper_argv

        report = inspect_rtlmeter_verilator_wrapper_argv(["--cc", "--use-gpu"])

        self.assertEqual(report["status"], "unsupported_rtlmeter_sidecar_request")
        self.assertIn("--top-module <top>", report["missing_required_inputs"])
        self.assertIn("-f <filelist>", report["missing_required_inputs"])
        self.assertIn("missing", report["diagnostic"])

    def test_no_gpu_intent_requires_real_wrapper_delegation_but_prototype_does_not_delegate(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_verilator_wrapper_argv

        report = inspect_rtlmeter_verilator_wrapper_argv(["--cc", "--top-module", "top", "-f", "filelist"])

        self.assertEqual(report["status"], "delegate_to_real_verilator")
        self.assertTrue(report["delegate_to_real_verilator_required"])
        self.assertTrue(report["prototype_exits_without_delegation"])
        self.assertFalse(report["gpu_intent_detected"])
