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
    / "implement_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_helper_gate.json"
)
EXECUTION_RUN_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "run_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_execution_gate.json"
)
EXECUTION_RUN_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_execution_run_gate.json"
)
BASE_ARGS = [
    "verilator", "--cc", "--timing", "-Mdir", "artifacts/pulp_ita_mha_obj_dir",
    "--top-module", "pulp_ita_mha_gpu_cov_tb", "-DTRACE=1", "-Wno-fatal",
    "-Ioverlays/ITA/src", "-f", "config/slice_launch_templates/pulp_ita_mha.filelist",
    "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv",
]
EXPECTED_EVENTS = [
    "verilator_facing_invocation_received",
    "reviewed_bridge_metadata_validated",
    "reviewed_process_to_launcher_metadata_validated",
    "explicit_sidecar_context_validated",
    "unreviewed_sidecar_context_source_ref_rejected",
    "bridge_ordering_trace_emitted_before_launcher_start",
    "launcher_start_allowed_from_structured_argv",
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


class VerilatorProcessLauncherBridgeObservableOrderingHelperTest(unittest.TestCase):
    def assert_error_code(self, fn, code: str) -> None:
        with self.assertRaises(Exception) as raised:
            fn()
        self.assertEqual(raised.exception.code, code)

    def test_helper_emits_ordering_trace_without_execution(self) -> None:
        bridge, = _load_tool_modules("verilator_native_option_parser_verilator_process_launcher_bridge_fixture")

        result = bridge.run_verilator_process_launcher_bridge_with_observable_ordering(
            _argv(),
            sidecar_context=_sidecar_context(),
            source_review_gate=bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_OBSERVABLE_ORDERING_REVIEW_GATE_REF,
        )

        self.assertEqual(result["surface"], "native_verilator_parser_direct_command_path_verilator_process_launcher_bridge_observable_ordering_helper")
        self.assertEqual(result["status"], "verilator_process_launcher_bridge_observable_ordering_helper_ready_for_review")
        self.assertTrue(result["bridge_metadata_validated"])
        self.assertTrue(result["process_to_launcher_metadata_validated"])
        self.assertTrue(result["explicit_sidecar_context_validated"])
        self.assertTrue(result["unreviewed_sidecar_context_source_ref_rejected"])
        self.assertTrue(result["structured_launcher_argv_validated"])
        self.assertEqual(
            result["launcher_command_argv"],
            ["python3", "src/tools/run_hybrid_template.py", "config/slice_launch_templates/pulp_ita_mha.json", "--shape", "64x1"],
        )
        self.assertEqual([event["event"] for event in result["observable_ordering_trace"]], EXPECTED_EVENTS)
        self.assertEqual([event["index"] for event in result["observable_ordering_trace"]], list(range(1, 8)))
        status = result["launcher_start_allowed_status"]
        self.assertTrue(status["allowed"])
        self.assertTrue(status["status_emitted_after_trace"])
        self.assertTrue(status["allowed_from_structured_argv_only"])
        self.assertFalse(status["launcher_process_started"])
        for flag in ("launcher_process_invoked", "sidecar_stage_execution_performed", "compare_execution_performed", "timing_measured", "runtime_or_abi_changed", "automatic_gpu_allocation_used", "generated_reports_and_artifacts_source_of_truth"):
            with self.subTest(flag=flag):
                self.assertFalse(result[flag])
        self.assertFalse(result["observable_ordering_trace_is_correctness_evidence"])
        self.assertFalse(result["observable_ordering_trace_is_execution_authority"])

    def test_helper_rejects_wrong_review_gate_and_unreviewed_context(self) -> None:
        bridge, = _load_tool_modules("verilator_native_option_parser_verilator_process_launcher_bridge_fixture")

        self.assert_error_code(
            lambda: bridge.run_verilator_process_launcher_bridge_with_observable_ordering(
                _argv(),
                sidecar_context=_sidecar_context(),
                source_review_gate=bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_BOUNDARY_REVIEW_GATE_REF,
            ),
            "source_or_template_authority_failure",
        )
        self.assert_error_code(
            lambda: bridge.run_verilator_process_launcher_bridge_with_observable_ordering(
                _argv(),
                sidecar_context=_sidecar_context(source_gate_or_manifest_ref="config/scaling_gates/unreviewed.json"),
                source_review_gate=bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_OBSERVABLE_ORDERING_REVIEW_GATE_REF,
            ),
            "source_or_template_authority_failure",
        )

    def test_helper_rejects_mutated_launcher_metadata(self) -> None:
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
            lambda: bridge.run_verilator_process_launcher_bridge_with_observable_ordering(
                _argv(),
                sidecar_context=_sidecar_context(),
                source_review_gate=bridge.VERILATOR_PROCESS_LAUNCHER_BRIDGE_OBSERVABLE_ORDERING_REVIEW_GATE_REF,
                process_to_launcher_cli_metadata=mutated,
            ),
            "process_to_launcher_bridge_failure",
        )

    def test_implementation_gate_records_helper_only_claim_boundary(self) -> None:
        gate = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_implementation_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_helper_implementation_gate",
        )
        surface = gate["implemented_surface"]
        self.assertEqual(surface["module"], "src/tools/verilator_native_option_parser_verilator_process_launcher_bridge_fixture.py")
        self.assertEqual(surface["primary_entrypoint_function"], "run_verilator_process_launcher_bridge_with_observable_ordering")
        self.assertFalse(surface["new_public_cli_added"])
        self.assertFalse(surface["launcher_process_execution_added"])
        output = gate["output_contract"]
        self.assertTrue(output["launcher_start_allowed_status_emitted_after_trace"])
        self.assertFalse(output["launcher_process_started"])
        self.assertFalse(output["sidecar_stage_execution_performed"])
        self.assertFalse(output["compare_execution_performed"])
        self.assertEqual(gate["observable_ordering_contract"]["required_ordering_events"], EXPECTED_EVENTS)
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["implementation_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["bridge_path_launcher_start_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_reached_from_bridge_path"])
        self.assertEqual(gate["required_next_gate"]["name"], gate["next_task"])

    def test_execution_run_gate_records_build_stage_failure_without_compare_claim(self) -> None:
        gate = json.loads(EXECUTION_RUN_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_execution_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_execution_run_gate",
        )
        self.assertEqual(gate["clean_worktree_evidence"]["helper_validation_exit_code"], 0)
        self.assertEqual(gate["clean_worktree_evidence"]["launcher_exit_code"], 1)
        precondition = gate["observable_ordering_precondition"]
        self.assertTrue(precondition["reviewed_helper_output_validated_before_runtime_attempt"])
        self.assertFalse(precondition["launcher_start_allowed_status_is_launcher_start_evidence"])
        result = gate["runtime_attempt_result"]
        self.assertTrue(result["runtime_attempt_started"])
        self.assertTrue(result["launcher_process_invoked"])
        self.assertTrue(result["launcher_command_started_from_exact_structured_argv"])
        self.assertTrue(result["verilator_build_stage_reached"])
        self.assertFalse(result["hybrid_sidecar_run_reached"])
        self.assertFalse(result["coverage_output_compare_reached"])
        self.assertFalse(result["timing_measured"])
        self.assertEqual(result["failure_class"], "sidecar_stage_failure")
        self.assertEqual(result["failure_subclass"], "verilator_build_missing_third_party_sources")
        observed = gate["observed_failure"]
        self.assertEqual(observed["missing_source_file_count_observed"], 26)
        self.assertIsNone(observed["compare_report"])
        self.assertIsNone(observed["coverage_output_mismatch_count"])
        self.assertIn("not direct Verilator internal sidecar execution", gate["accepted_non_claims"])
        self.assertIn("not bridge-path coverage-output equivalence", gate["accepted_non_claims"])
        self.assertEqual(gate["required_next_gate"]["name"], gate["next_task"])

    def test_execution_run_review_accepts_source_closure_as_next_boundary(self) -> None:
        gate = json.loads(EXECUTION_RUN_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_run_gate"],
            "config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_execution_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_source_closure_materialization_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        evidence = gate["accepted_run_evidence"]
        self.assertTrue(evidence["runtime_attempt_started"])
        self.assertTrue(evidence["launcher_process_invoked"])
        self.assertTrue(evidence["verilator_build_stage_reached"])
        self.assertFalse(evidence["coverage_output_compare_reached"])
        self.assertEqual(evidence["failure_class"], "sidecar_stage_failure")
        self.assertEqual(evidence["failure_subclass"], "verilator_build_missing_third_party_sources")
        boundary = gate["accepted_failure_boundary"]
        self.assertTrue(boundary["launcher_cli_invocation_failure_rejected"])
        self.assertTrue(boundary["compare_failure_rejected"])
        self.assertEqual(boundary["source_closure_blocker"], "third_party/common_cells and third_party/ITA source paths named by the pulp_ita_mha template are absent in the clean worktree")
        source_scope = gate["required_source_closure_scope"]
        self.assertEqual(source_scope["target"], "pulp_ita_mha")
        self.assertEqual(
            source_scope["missing_source_roots"],
            ["third_party/common_cells/src", "third_party/ITA/src"],
        )
        policy = gate["acceptance_policy"]
        self.assertFalse(policy["new_execution_allowed_by_this_review"])
        self.assertFalse(policy["coverage_output_equivalence_claim_reached_from_bridge_path"])
        self.assertEqual(gate["required_next_gate"]["name"], gate["next_task"])


if __name__ == "__main__":
    unittest.main()
