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
    / "implement_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_gate.json"
)
REVIEW_IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_implementation_gate.json"
)
RUN_EXECUTION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "run_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_gate.json"
)
STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE = (
    "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_"
    "direct_launch_handoff_sidecar_launcher_invocation_run_gate.json"
)
BASE_ARGS = [
    "verilator",
    "--cc",
    "--timing",
    "-Mdir",
    "artifacts/pulp_ita_mha_obj_dir",
    "--top-module",
    "pulp_ita_mha_gpu_cov_tb",
    "-DTRACE=1",
    "-Wno-fatal",
    "-Ioverlays/ITA/src",
    "-f",
    "config/slice_launch_templates/pulp_ita_mha.filelist",
    "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv",
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


def _argv(states: str = "64", steps: str = "1") -> list[str]:
    return [*BASE_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-states", states, "--sim-accel-steps", steps]


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


class VerilatorNativeOptionParserProcessToLauncherCliFixtureTest(unittest.TestCase):
    def assert_error_code(self, fn, code: str) -> None:
        with self.assertRaises(Exception) as raised:
            fn()
        self.assertEqual(raised.exception.code, code)

    def test_materializes_launcher_argv_without_execution(self) -> None:
        cli, = _load_tool_modules("verilator_native_option_parser_process_to_launcher_cli_fixture")

        result = cli.define_process_to_launcher_cli_fixture(
            _argv(),
            sidecar_context=_sidecar_context(),
            source_review_gate=cli.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
        )

        self.assertEqual(tuple(result.keys()), cli.PROCESS_TO_LAUNCHER_CLI_FIELDS)
        self.assertEqual(result["surface"], cli.PROCESS_TO_LAUNCHER_CLI_FIXTURE_SURFACE)
        self.assertEqual(result["status"], cli.PROCESS_TO_LAUNCHER_CLI_STATUS)
        self.assertTrue(result["process_to_launcher_cli_bridge_ready"])
        self.assertEqual(result["source_structured_invocation_review_gate"], STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE)
        self.assertEqual(result["launcher_command_argv"], cli.EXPECTED_LAUNCHER_COMMAND_ARGV)
        self.assertEqual(result["launcher_command_role"], "materialized_for_later_run_not_invoked_by_fixture")
        self.assertEqual(
            result["parser_schedule"],
            {
                "accelerator_mode": "sidecar-gpu",
                "state_count": 64,
                "step_count": 1,
                "shape": "64x1",
                "correctness_policy": "coverage_output_equivalence",
            },
        )
        authority = result["source_or_template_authority"]
        self.assertFalse(authority["payload_only_execution_authority"])
        self.assertFalse(authority["generated_command_text_execution_authority"])
        self.assertFalse(authority["structured_invocation_review_gate_alone_is_current_authority"])
        for flag in (
            "launcher_cli_invoked",
            "launcher_process_invoked",
            "sidecar_stage_execution_performed",
            "compare_execution_performed",
            "direct_verilator_sidecar_execution_proven",
            "execution_performed",
            "measurement_performed",
            "timing_measured",
            "runtime_or_abi_changed",
            "automatic_gpu_allocation_used",
            "generated_reports_and_artifacts_source_of_truth",
        ):
            with self.subTest(flag=flag):
                self.assertFalse(result[flag])

    def test_rejects_wrong_authority_and_payload_execution_fields(self) -> None:
        cli, direct = _load_tool_modules(
            "verilator_native_option_parser_process_to_launcher_cli_fixture",
            "verilator_native_option_parser_direct_command_path_fixture",
        )

        self.assert_error_code(
            lambda: cli.define_process_to_launcher_cli_fixture(
                _argv(),
                sidecar_context=_sidecar_context(),
                source_review_gate=cli.REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF,
            ),
            "source_or_template_authority_failure",
        )
        parser_payload = direct.define_direct_command_path_sidecar_plan_fixture(
            _argv(), sidecar_context=_sidecar_context()
        )["parser_payload"]
        mutated = {**parser_payload, "generated_command_text_execution_authority": True}
        self.assert_error_code(
            lambda: cli.define_process_to_launcher_cli_fixture(
                sidecar_context=_sidecar_context(),
                source_review_gate=cli.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
                parser_payload=mutated,
            ),
            "payload_authority_field_prepopulated_by_parser",
        )

    def test_rejects_out_of_scope_inputs_and_mutated_invocation_metadata(self) -> None:
        cli, native = _load_tool_modules(
            "verilator_native_option_parser_process_to_launcher_cli_fixture",
            "verilator_native_option_parser_direct_native_invocation_fixture",
        )

        for bad_argv, expected_code in (
            (["python3", "src/tools/run_hybrid_template.py", *_argv()[1:]], "non_verilator_native_invocation"),
            (_argv("1", "64"), "unsupported_direct_launch_handoff_scope"),
        ):
            with self.subTest(expected_code=expected_code):
                self.assert_error_code(
                    lambda bad_argv=bad_argv: cli.define_process_to_launcher_cli_fixture(
                        bad_argv,
                        sidecar_context=_sidecar_context(),
                        source_review_gate=cli.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
                    ),
                    expected_code,
                )
        bridge = native.define_sidecar_launcher_bridge_fixture(_argv(), sidecar_context=_sidecar_context())
        mutated = dict(bridge)
        mutated["execution_performed"] = True
        self.assert_error_code(
            lambda: cli.define_process_to_launcher_cli_fixture(
                _argv(),
                sidecar_context=_sidecar_context(),
                source_review_gate=cli.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
                bridge_metadata=mutated,
            ),
            "sidecar_launcher_bridge_failure",
        )

    def test_gate_records_keep_process_to_launcher_claim_boundary(self) -> None:
        implementation = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))
        review = json.loads(REVIEW_IMPLEMENTATION_GATE.read_text(encoding="utf-8"))
        run = json.loads(RUN_EXECUTION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(implementation["implemented_surface"]["primary_entrypoint_function"], "define_process_to_launcher_cli_fixture")
        self.assertFalse(implementation["implemented_surface"]["new_public_cli_added"])
        self.assertFalse(implementation["implemented_surface"]["launcher_process_execution_added"])
        output = implementation["output_contract"]
        self.assertTrue(output["process_to_launcher_cli_bridge_ready"])
        self.assertFalse(output["launcher_process_invoked"])
        self.assertFalse(output["sidecar_stage_execution_performed"])
        self.assertFalse(output["compare_execution_performed"])
        self.assertTrue(review["accepted_implementation"]["metadata_only"])
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["process_to_launcher_cli_execution_claim_allowed_by_gate_alone"])
        attempt = run["native_path_launcher_invocation_attempt"]
        self.assertTrue(attempt["launcher_command_started_from_materialized_argv"])
        self.assertFalse(attempt["direct_verilator_sidecar_execution_proven"])
        self.assertFalse(run["acceptance_policy"]["direct_verilator_sidecar_execution_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
