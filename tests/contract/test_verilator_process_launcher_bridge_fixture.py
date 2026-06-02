import importlib
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "tools"
IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_fixture_gate.json"
)
BASE_ARGS = [
    "verilator", "--cc", "--timing", "-Mdir", "artifacts/pulp_ita_mha_obj_dir",
    "--top-module", "pulp_ita_mha_gpu_cov_tb", "-DTRACE=1", "-Wno-fatal",
    "-Ioverlays/ITA/src", "-f", "config/slice_launch_templates/pulp_ita_mha.filelist",
    "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv",
]
EXPECTED_LAUNCHER_ARGV = [
    "python3", "src/tools/run_hybrid_template.py",
    "config/slice_launch_templates/pulp_ita_mha.json", "--shape", "64x1",
]


def _load_tool_modules(*names: str) -> tuple[object, ...]:
    tools_s = str(TOOLS)
    added = tools_s not in sys.path
    if added:
        sys.path.insert(0, tools_s)
    try:
        return tuple(importlib.import_module(name) for name in names)
    finally:
        if added:
            sys.path.remove(tools_s)


def _argv() -> list[str]:
    return [*BASE_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"]


def _sidecar_context(**overrides: object) -> dict[str, object]:
    context: dict[str, object] = {
        "target": "pulp_ita_mha",
        "mode": "template",
        "template_or_target_registry_entry": "config/slice_launch_templates/pulp_ita_mha.json",
        "source_gate_or_manifest_ref": (
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_"
            "direct_launch_handoff_implementation_boundary_gate.json"
        ),
    }
    context.update(overrides)
    return context


class VerilatorProcessLauncherBridgeFixtureTest(unittest.TestCase):
    def assert_error_code(self, fn, code: str) -> None:
        with self.assertRaises(Exception) as raised:
            fn()
        self.assertEqual(raised.exception.code, code)

    def test_fixture_materializes_bridge_metadata_without_execution(self) -> None:
        bridge, = _load_tool_modules("verilator_native_option_parser_verilator_process_launcher_bridge_fixture")

        result = bridge.define_verilator_process_launcher_bridge_fixture(
            _argv(),
            sidecar_context=_sidecar_context(),
            source_review_gate=bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_BOUNDARY_REVIEW_GATE_REF,
        )

        self.assertEqual(result["surface"], bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_FIXTURE_SURFACE)
        self.assertEqual(result["status"], bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_STATUS)
        self.assertTrue(result["verilator_process_launcher_bridge_ready"])
        self.assertTrue(result["wrapper_mediated_process_launch_bridge"])
        self.assertTrue(result["process_to_launcher_cli_bridge_ready"])
        self.assertTrue(result["invocation_ready"])
        self.assertEqual(result["launcher_command_argv"], EXPECTED_LAUNCHER_ARGV)
        self.assertEqual(result["launcher_command_role"], "materialized_for_later_run_not_invoked_by_fixture")
        self.assertEqual(result["parser_schedule"]["shape"], "64x1")
        self.assertEqual(result["sidecar_context"], _sidecar_context())
        self.assertEqual(
            result["source_process_to_launcher_execution_run_review_gate"],
            bridge.PROCESS_TO_LAUNCHER_CLI_EXECUTION_RUN_REVIEW_GATE_REF,
        )
        self.assertEqual(result["bridge_materialization_status"]["failure_class"], "none")
        for flag in (
            "verilator_process_invoked",
            "launcher_process_invoked",
            "sidecar_stage_execution_performed",
            "compare_execution_performed",
            "timing_measured",
            "runtime_or_abi_changed",
            "automatic_gpu_allocation_used",
            "generated_reports_and_artifacts_source_of_truth",
        ):
            with self.subTest(flag=flag):
                self.assertFalse(result[flag])

    def test_fixture_rejects_wrong_review_gate_and_unreviewed_context(self) -> None:
        bridge, cli = _load_tool_modules(
            "verilator_native_option_parser_verilator_process_launcher_bridge_fixture",
            "verilator_native_option_parser_process_to_launcher_cli_fixture",
        )

        self.assert_error_code(
            lambda: bridge.define_verilator_process_launcher_bridge_fixture(
                _argv(),
                sidecar_context=_sidecar_context(),
                source_review_gate=cli.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
            ),
            "source_or_template_authority_failure",
        )
        metadata = cli.define_process_to_launcher_cli_fixture(
            _argv(),
            sidecar_context=_sidecar_context(),
            source_review_gate=cli.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
        )
        metadata = dict(metadata)
        metadata["sidecar_context"] = dict(metadata["sidecar_context"])
        metadata["sidecar_context"]["source_gate_or_manifest_ref"] = "config/scaling_gates/unreviewed.json"
        self.assert_error_code(
            lambda: bridge.define_verilator_process_launcher_bridge_fixture(
                _argv(),
                sidecar_context=metadata["sidecar_context"],
                source_review_gate=bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_BOUNDARY_REVIEW_GATE_REF,
                process_to_launcher_cli_metadata=metadata,
            ),
            "source_or_template_authority_failure",
        )

    def test_fixture_rejects_mutated_process_to_launcher_metadata(self) -> None:
        bridge, cli = _load_tool_modules(
            "verilator_native_option_parser_verilator_process_launcher_bridge_fixture",
            "verilator_native_option_parser_process_to_launcher_cli_fixture",
        )
        metadata = cli.define_process_to_launcher_cli_fixture(
            _argv(),
            sidecar_context=_sidecar_context(),
            source_review_gate=cli.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
        )
        mutated = dict(metadata)
        mutated["launcher_command_argv"] = ["sh", "-c", "python3 src/tools/run_hybrid_template.py"]

        self.assert_error_code(
            lambda: bridge.define_verilator_process_launcher_bridge_fixture(
                _argv(),
                sidecar_context=_sidecar_context(),
                source_review_gate=bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_BOUNDARY_REVIEW_GATE_REF,
                process_to_launcher_cli_metadata=mutated,
            ),
            "process_to_launcher_bridge_failure",
        )

    def test_implementation_gate_records_fixture_only_claim_boundary(self) -> None:
        gate = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_fixture_implementation_gate",
        )
        surface = gate["implemented_surface"]
        self.assertEqual(surface["module"], "src/tools/verilator_native_option_parser_verilator_process_launcher_bridge_fixture.py")
        self.assertEqual(surface["primary_entrypoint_function"], "define_verilator_process_launcher_bridge_fixture")
        self.assertFalse(surface["new_public_cli_added"])
        self.assertFalse(surface["verilator_process_execution_added"])
        self.assertFalse(surface["launcher_process_execution_added"])
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["implementation_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["timing_or_speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["required_next_gate"]["name"], gate["next_task"])


if __name__ == "__main__":
    unittest.main()
