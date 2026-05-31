import json
import importlib
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "tools"
IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_direct_command_path_native_invocation_fixture_gate.json"
)
REVIEW_IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_direct_command_path_native_invocation_fixture_implementation_gate.json"
)
EXECUTION_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate.json"
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


def _argv() -> list[str]:
    return [*BASE_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1"]


def _sidecar_context() -> dict[str, object]:
    return {
        "target": "pulp_ita_mha",
        "mode": "template",
        "template_or_target_registry_entry": "config/slice_launch_templates/pulp_ita_mha.json",
        "source_gate_or_manifest_ref": (
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json"
        ),
    }


class VerilatorNativeOptionParserNativeInvocationFixtureTest(unittest.TestCase):
    def assert_error_code(self, fn, code: str) -> None:
        with self.assertRaises(Exception) as raised:
            fn()
        self.assertEqual(raised.exception.code, code)

    def test_accepts_expanded_64x1_native_invocation_metadata(self) -> None:
        native, = _load_tool_modules("verilator_native_option_parser_direct_native_invocation_fixture")

        result = native.define_direct_command_path_native_invocation_fixture(_argv(), sidecar_context=_sidecar_context())

        self.assertEqual(tuple(result.keys()), native.NATIVE_INVOCATION_FIELDS)
        self.assertEqual(result["surface"], native.NATIVE_INVOCATION_FIXTURE_SURFACE)
        self.assertEqual(result["status"], native.NATIVE_INVOCATION_STATUS)
        self.assertEqual(result["direct_fixture_surface"], "native_verilator_parser_direct_command_path_fixture")
        self.assertEqual(result["accelerator_mode"], "sidecar-gpu")
        self.assertEqual(result["shape"], "64x1")
        self.assertEqual(result["source_files"], ["overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv"])
        self.assertEqual(result["filelists"], ["config/slice_launch_templates/pulp_ita_mha.filelist"])
        self.assertIn("verilator_build", result["required_stage_order"])
        self.assertEqual(result["correctness_policy_ref"], "coverage_output_equivalence")
        self.assertEqual(result["native_invocation"]["argv"][0], "verilator")
        self.assertTrue(result["native_invocation"]["requires_real_verilator_process_before_execution"])
        handoff = native.define_direct_launch_handoff_fixture(_argv(), sidecar_context=_sidecar_context()); bridge = native.define_sidecar_launcher_bridge_fixture(_argv(), sidecar_context=_sidecar_context())
        self.assertEqual((handoff["surface"], handoff["status"], handoff["handoff_ready"], handoff["sidecar_launcher_entrypoint"], handoff["sidecar_launch_reached_from_native_path"], handoff["coverage_output_compare_reached_from_native_path"], bridge["surface"], bridge["status"], bridge["bridge_ready"], bridge["sidecar_launcher_entrypoint_role"], bridge["sidecar_launch_reached_from_native_path"], bridge["coverage_output_compare_reached_from_native_path"], bridge["native_path_compare_reached"], bridge["execution_performed"], bridge["measurement_performed"], bridge["timing_measured"], bridge["runtime_or_abi_changed"], bridge["automatic_gpu_allocation_used"], tuple(bridge["preserved_failure_classes"]), "sidecar launcher bridge fixture does not call the sidecar launcher" in bridge["non_claims"]), (native.DIRECT_LAUNCH_HANDOFF_FIXTURE_SURFACE, native.DIRECT_LAUNCH_HANDOFF_STATUS, True, "src/tools/run_hybrid_template.py", False, False, native.SIDECAR_LAUNCHER_BRIDGE_FIXTURE_SURFACE, native.SIDECAR_LAUNCHER_BRIDGE_STATUS, True, "reference_only_not_invoked_by_fixture", False, False, False, False, False, False, False, False, native.BRIDGE_FAILURE_CLASSES, True))
        for flag in native.FALSE_AUTHORITY_FLAGS:
            self.assertIs(result[flag], False)

    def test_accepts_parser_payload_without_command_text_authority(self) -> None:
        native, direct = _load_tool_modules(
            "verilator_native_option_parser_direct_native_invocation_fixture",
            "verilator_native_option_parser_direct_command_path_fixture",
        )
        direct_result = direct.define_direct_command_path_sidecar_plan_fixture(_argv(), sidecar_context=_sidecar_context())

        result = native.parser_payload_to_direct_command_path_native_invocation_fixture(
            direct_result["parser_payload"], sidecar_context=_sidecar_context()
        )

        self.assertEqual(result["native_invocation"]["argv"], [])
        self.assertEqual(result["native_invocation"]["argv_role"], "metadata_only_not_execution_authority")
        self.assertFalse(result["generated_command_text_source_of_truth"])
        self.assertFalse(result["generated_command_text_execution_authority"])
        self.assertFalse(result["native_command_alone_execution_authority"])

    def test_rejects_wrapper_or_ambiguous_sidecar_context(self) -> None:
        native, = _load_tool_modules("verilator_native_option_parser_direct_native_invocation_fixture")

        self.assert_error_code(
            lambda: native.define_direct_command_path_native_invocation_fixture(
                ["python3", "src/tools/run_hybrid_template.py", *_argv()[1:]], sidecar_context=_sidecar_context()
            ),
            "non_verilator_native_invocation",
        )
        ambiguous = {**_sidecar_context(), "verilator_command": "verilator --cc ..."}
        self.assert_error_code(
            lambda: native.define_direct_command_path_native_invocation_fixture(_argv(), sidecar_context=ambiguous),
            "ambiguous_explicit_sidecar_context",
        )
        missing = dict(_sidecar_context())
        del missing["source_gate_or_manifest_ref"]
        self.assert_error_code(
            lambda: native.define_direct_command_path_native_invocation_fixture(_argv(), sidecar_context=missing),
            "missing_explicit_sidecar_context",
        )
        self.assert_error_code(lambda: native.define_direct_launch_handoff_fixture(_argv(), sidecar_context={**_sidecar_context(), "source_gate_or_manifest_ref": "config/scaling_gates/review_fake_gate.json"}), "sidecar_authority_failure")

    def test_rejects_compact_shape_and_sidecar_owned_parser_fields(self) -> None:
        native, direct = _load_tool_modules(
            "verilator_native_option_parser_direct_native_invocation_fixture",
            "verilator_native_option_parser_direct_command_path_fixture",
        )

        compact = [*BASE_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-shape", "64x1"]
        self.assert_error_code(
            lambda: native.define_direct_command_path_native_invocation_fixture(compact, sidecar_context=_sidecar_context()),
            "compact_shape_spelling_outside_native_minimum",
        )
        direct_result = direct.define_direct_command_path_sidecar_plan_fixture(_argv(), sidecar_context=_sidecar_context())
        payload = {**direct_result["parser_payload"], "verilator_command_argv": _argv()}
        self.assert_error_code(
            lambda: native.parser_payload_to_direct_command_path_native_invocation_fixture(
                payload, sidecar_context=_sidecar_context()
            ),
            "sidecar_owned_field_prepopulated_by_parser",
        )

    def test_implementation_gate_records_non_executing_scope(self) -> None:
        gate = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_native_invocation_fixture_implementation_gate",
        )
        implemented = gate["implemented_surface"]
        self.assertEqual(implemented["module"], "src/tools/verilator_native_option_parser_direct_native_invocation_fixture.py")
        self.assertEqual(implemented["primary_entrypoint_function"], "define_direct_command_path_native_invocation_fixture")
        self.assertFalse(implemented["new_public_cli_added"])
        self.assertFalse(implemented["direct_verilator_command_execution_added"])
        self.assertFalse(implemented["sidecar_stage_execution_added"])
        self.assertFalse(implemented["new_measurement_added"])
        for flag in (
            "verilator_process_invoked",
            "generated_command_text_execution_authority",
            "materialized_stage_plan_metadata_execution_authority",
            "runtime_or_abi_changed",
            "automatic_gpu_allocation_used",
        ):
            self.assertFalse(gate["output_contract"][flag])

    def test_review_gate_accepts_metadata_only_fixture_and_selects_execution_boundary_definition(self) -> None:
        review = json.loads(REVIEW_IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_fixture_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate",
        )
        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate",
        )
        accepted = review["accepted_implementation"]
        self.assertEqual(accepted["module"], "src/tools/verilator_native_option_parser_direct_native_invocation_fixture.py")
        self.assertTrue(accepted["requires_verilator_facing_argv_on_argv_path"])
        self.assertFalse(accepted["verilator_process_invoked"])
        self.assertFalse(accepted["direct_verilator_command_execution_added"])
        self.assertFalse(accepted["sidecar_stage_execution_added"])
        self.assertFalse(accepted["new_measurement_added"])
        metadata = review["accepted_metadata_boundary"]
        for flag in (
            "verilator_process_invoked",
            "wrapper_execution_used",
            "generated_command_text_execution_authority",
            "native_command_alone_execution_authority",
            "sidecar_stage_plan_metadata_execution_authority",
            "execution_performed",
            "timing_measured",
            "runtime_or_abi_changed",
            "automatic_gpu_allocation_used",
        ):
            self.assertFalse(metadata[flag])
        self.assertFalse(review["acceptance_policy"]["direct_verilator_command_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["coverage_output_equivalence_claim_allowed_by_gate_alone"])

    def test_execution_boundary_definition_requires_real_process_parse_evidence(self) -> None:
        gate = json.loads(EXECUTION_BOUNDARY_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate",
        )
        eligible = gate["eligible_native_invocation_input_preconditions"]
        self.assertEqual(eligible["surface"], "native_verilator_parser_direct_command_path_native_invocation_fixture")
        self.assertFalse(eligible["verilator_process_invoked"])
        boundary = gate["real_native_execution_boundary"]
        self.assertFalse(boundary["execution_allowed_by_this_gate"])
        authority = boundary["runtime_authority_sources"]
        self.assertTrue(authority["real_verilator_process_parse_result_required"])
        self.assertTrue(authority["reviewed_sidecar_context_required"])
        for flag in ("fixture_argv_is_execution_authority", "parser_payload_only_path_is_execution_authority"):
            self.assertFalse(authority[flag])
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "review_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate",
        )
