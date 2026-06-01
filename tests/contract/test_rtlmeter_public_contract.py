import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterPublicContractTest(HybridCliTestCase):
    def test_public_contract_preserves_rtlmeter_user_path(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_compileargs_pass_through

        pass_through = inspect_rtlmeter_compileargs_pass_through(
            "Example:kind:hello",
            "--use-gpu",
        )
        mapping = map_rtlmeter_case_to_sidecar_contract(
            "Example:kind:hello",
            compile_args=("--use-gpu",),
        )

        self.assertTrue(pass_through["gpu_intent_reaches_wrapper"])
        self.assertFalse(mapping["requires_rtlmeter_launch_template"])
        self.assertEqual(mapping["frontend"], "rtlmeter/verilator")
        self.assertIn("--use-gpu", mapping["frontend_owned_build_metadata"]["verilator_command_argv"])
        self.assert_no_local_absolute_paths(json.dumps(pass_through, sort_keys=True))
        self.assert_no_local_absolute_paths(json.dumps(mapping, sort_keys=True))

    def test_public_contract_fails_closed_for_unsupported_gpu_request(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_verilator_wrapper_argv

        report = inspect_rtlmeter_verilator_wrapper_argv(["--cc", "--use-gpu"])

        self.assertEqual(report["status"], "unsupported_rtlmeter_sidecar_request")
        self.assertTrue(report["gpu_intent_detected"])
        self.assertIn("--top-module <top>", report["missing_required_inputs"])
        self.assertIn("-f <filelist>", report["missing_required_inputs"])
        self.assertFalse(report["execution_authority"])

    def test_debug_json_is_optional_not_execution_authority(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_verilator_command_capture import capture_rtlmeter_verilator_command
        from rtlmeter_verilator_path_wrapper import inspect_rtlmeter_compileargs_pass_through

        reports = [
            capture_rtlmeter_verilator_command("Example:kind:hello", extra_args=("--use-gpu",)),
            inspect_rtlmeter_compileargs_pass_through("Example:kind:hello", "--use-gpu"),
            map_rtlmeter_case_to_sidecar_contract("Example:kind:hello", compile_args=("--use-gpu",)),
        ]

        for report in reports:
            self.assertEqual(report["json_flow_role"], "debug_inspection")
            self.assertFalse(report["runtime_abi"])
            self.assertFalse(report["execution_authority"])
            self.assertIsInstance(report, dict)
