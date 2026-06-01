import json
import tempfile

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVerilatorCommandCaptureTest(HybridCliTestCase):
    def test_captures_example_case_without_execution_authority(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_command_capture import capture_rtlmeter_verilator_command

        capture = capture_rtlmeter_verilator_command(
            "Example:kind:hello",
            extra_args=("--use-gpu",),
        )

        self.assertEqual(capture["surface"], "rtlmeter_verilator_command_capture")
        self.assertEqual(capture["compile_case"], "Example:kind")
        self.assertEqual(capture["test"], "hello")
        self.assertEqual(capture["sidecar_contract_role"], "frontend_owned_build_metadata")
        self.assertEqual(capture["top_module"], "top")
        self.assertEqual(capture["main_clock"], "top.clk")
        self.assertFalse(capture["runtime_abi"])
        self.assertFalse(capture["execution_authority"])

        command = capture["verilator_command_argv"]
        self.assertEqual(command[0], "verilator")
        self.assertIn("--top-module", command)
        self.assertIn("top", command)
        self.assertIn("-f", command)
        self.assertIn("filelist", command)
        self.assertIn("--use-gpu", command)

        self.assertIn("verilogSourceFiles/top.v", capture["filelist_entries"])
        self.assertIn("verilogSourceFiles/__rtlmeter_utils.sv", capture["filelist_entries"])
        self.assertIn("designs/Example/src/top.v", capture["verilog_source_files"])
        self.assertIn("rtl/__rtlmeter_utils.sv", capture["verilog_source_files"])

        self.assert_no_local_absolute_paths(json.dumps(capture, sort_keys=True))

    def test_matches_rtlmeter_trace_define_injection_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_command_capture import capture_rtlmeter_verilator_command

        capture = capture_rtlmeter_verilator_command(
            "Example:kind:hello",
            extra_args=("--trace",),
        )

        command = capture["verilator_command_argv"]
        self.assertIn("--trace", command)
        self.assertIn("+define+__RTLMETER_TRACE_VCD", command)
        self.assertEqual(capture["rtlmeter_trace_define"], "+define+__RTLMETER_TRACE_VCD")
        self.assert_no_local_absolute_paths(json.dumps(capture, sort_keys=True))

    def test_missing_rtlmeter_source_error_avoids_absolute_paths(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_command_capture import (
            RtlmeterCommandCaptureError,
            capture_rtlmeter_verilator_command,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(RtlmeterCommandCaptureError, "source directory is missing") as ctx:
                capture_rtlmeter_verilator_command("Example:kind:hello", rtlmeter_root=tmpdir)

        self.assert_no_local_absolute_paths(str(ctx.exception))

    def test_rejects_unknown_case_before_sidecar_planning(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_command_capture import (
            RtlmeterCommandCaptureError,
            capture_rtlmeter_verilator_command,
        )

        with self.assertRaisesRegex(RtlmeterCommandCaptureError, "descriptor is missing"):
            capture_rtlmeter_verilator_command("Missing:default:hello")

        with self.assertRaisesRegex(RtlmeterCommandCaptureError, "config is missing"):
            capture_rtlmeter_verilator_command("Example:missing:hello")
