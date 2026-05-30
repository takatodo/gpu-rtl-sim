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
    / "implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json"
)


def _load_tool_modules(*names: str) -> tuple[object, ...]:
    tools_s = str(TOOLS)
    added = False
    if tools_s not in sys.path:
        sys.path.insert(0, tools_s)
        added = True
    try:
        return tuple(importlib.import_module(name) for name in names)
    finally:
        if added:
            sys.path.remove(tools_s)


def _adapter_payload() -> dict[str, object]:
    sidecar_handoff, parser_stub = _load_tool_modules(
        "verilator_native_option_parser_sidecar_handoff",
        "verilator_native_option_parser_stub_fixture",
    )
    parser_values = parser_stub.parse_verilator_native_option_stub(
        [
            "--cc",
            "--timing",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
            "-Mdir",
            "artifacts/example_obj_dir",
            "--top-module",
            "example_top",
            "-f",
            "rtl/files.f",
            "-DTRACE=1",
            "-I",
            "include",
            "rtl/top.sv",
        ]
    )
    return sidecar_handoff.native_parser_values_to_sidecar_adapter_payload(parser_values)


def _sidecar_context() -> dict[str, object]:
    return {
        "target": "pulp_ita_mha",
        "mode": "template",
        "template": "config/slice_launch_templates/pulp_ita_mha.json",
        "source_gate_or_manifest_ref": (
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json"
        ),
    }


class VerilatorNativeOptionParserSidecarPlanResolutionFixtureTest(unittest.TestCase):
    def assert_non_executing_plan_resolution(self, resolved: dict[str, object]) -> None:
        self.assertFalse(resolved["sidecar_handoff_contract_invoked"])
        self.assertFalse(resolved["command_synthesis_invoked"])
        self.assertFalse(resolved["execution_performed"])
        self.assertFalse(resolved["measurement_performed"])
        self.assertEqual(resolved["correctness_policy_ref_status"], "reference_only_not_compare_evidence")
        for field in (
            "sidecar_handoff_contract",
            "operator_plan",
            "verilator_command",
            "verilator_command_argv",
            "timing",
        ):
            self.assertNotIn(field, resolved)

    def test_implementation_gate_records_non_executing_fixture_scope(self) -> None:
        gate = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate",
        )
        implemented = gate["implemented_surface"]
        self.assertEqual(
            implemented["module"],
            "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py",
        )
        self.assertEqual(
            implemented["primary_entrypoint_function"],
            "resolve_native_parser_adapter_payload_to_sidecar_plan",
        )
        self.assertTrue(implemented["sidecar_stage_plan_invoked_after_explicit_context"])
        self.assertFalse(implemented["sidecar_handoff_contract_invoked"])
        self.assertFalse(implemented["command_synthesis_invoked"])
        self.assertFalse(implemented["new_public_cli_added"])
        self.assertFalse(implemented["new_execution_added"])
        self.assertFalse(implemented["new_measurement_added"])

    def test_resolves_adapter_payload_with_explicit_context_to_non_executing_plan(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")

        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )

        self.assertEqual(resolved["surface"], "native_verilator_parser_sidecar_plan_resolution_fixture")
        self.assertEqual(resolved["status"], "ready_for_verilator_option_shim")
        self.assertTrue(resolved["sidecar_stage_plan_invoked"])
        self.assert_non_executing_plan_resolution(resolved)
        self.assertEqual(resolved["stage_plan"]["status"], "planned")
        readiness = resolved["plan_resolution_readiness"]
        self.assertEqual(readiness["stage_plan_status"], "planned")
        self.assertEqual(readiness["verilator_option_readiness_status"], "ready_for_verilator_option_shim")
        self.assertTrue(readiness["ready_for_direct_verilator_option"])
        self.assertIsNone(readiness["not_ready_reason"])
        self.assertEqual(resolved["stage_plan"]["target"], "pulp_ita_mha")
        self.assertEqual(resolved["stage_plan"]["shape"], "64x1")
        self.assertEqual(resolved["stage_plan"]["template"], "config/slice_launch_templates/pulp_ita_mha.json")

    def test_rejects_missing_target_mode_template_or_source_reference_context(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        payload = _adapter_payload()

        for missing in ("target", "mode", "template", "source_gate_or_manifest_ref"):
            context = _sidecar_context()
            context.pop(missing)
            with self.subTest(missing=missing):
                with self.assertRaises(plan_resolution.NativeParserSidecarPlanResolutionError):
                    plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                        payload,
                        sidecar_context=context,
                    )

    def test_allows_registry_entry_as_explicit_template_context(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        context = _sidecar_context()
        template = context.pop("template")
        context["target_registry_entry"] = {
            "target": "pulp_ita_mha",
            "template": template,
        }

        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=context,
        )

        self.assertTrue(resolved["sidecar_context"]["target_registry_entry_supplied"])
        self.assertEqual(resolved["sidecar_context"]["template"], template)

    def test_rejects_template_or_shape_mismatch_before_plan_resolution_claims(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        payload = _adapter_payload()
        wrong_template_context = _sidecar_context()
        wrong_template_context["template"] = "config/slice_launch_templates/pulp_paged_attention_kv_score.json"

        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "template"):
            plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                payload,
                sidecar_context=wrong_template_context,
            )

        mismatched_payload = dict(payload)
        mismatched_payload["shape"] = "1x64"
        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "shape"):
            plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                mismatched_payload,
                sidecar_context=_sidecar_context(),
            )

    def test_parser_files_remain_preserved_inputs_not_source_closure(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")

        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )

        preserved = resolved["parser_preserved_build_inputs"]
        self.assertEqual(preserved["source_files"], ["rtl/top.sv"])
        self.assertEqual(preserved["filelists"], ["rtl/files.f"])
        self.assertEqual(
            resolved["parser_input_resolution_role"]["source_files"],
            "preserved_parser_input_not_source_closure",
        )
        self.assertEqual(
            resolved["parser_input_resolution_role"]["filelists"],
            "preserved_parser_input_not_filelist_expansion",
        )

    def test_rejects_payload_with_resolved_sidecar_outputs_or_policy_mismatch(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        payload = _adapter_payload()

        with_sidecar_output = dict(payload)
        with_sidecar_output["state_files"] = {"init_state": "artifacts/init.bin"}
        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "sidecar-owned"):
            plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                with_sidecar_output,
                sidecar_context=_sidecar_context(),
            )

        wrong_policy = dict(payload)
        wrong_policy["correctness_policy_ref"] = "raw_state_equality"
        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "correctness_policy_ref"):
            plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                wrong_policy,
                sidecar_context=_sidecar_context(),
            )

    def test_resident_modes_are_not_ready_direct_verilator_plan_resolution(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")

        for mode in ("resident-state-reuse", "persistent-resident-state-abi"):
            context = _sidecar_context()
            context["mode"] = mode
            with self.subTest(mode=mode):
                resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                    _adapter_payload(),
                    sidecar_context=context,
                )

                self.assertEqual(resolved["status"], "not_ready_for_verilator_option_shim")
                self.assert_non_executing_plan_resolution(resolved)
                self.assertEqual(resolved["stage_plan"]["status"], "planned_not_ready_for_verilator_option_shim")
                readiness = resolved["plan_resolution_readiness"]
                self.assertEqual(readiness["stage_plan_status"], "planned_not_ready_for_verilator_option_shim")
                self.assertEqual(readiness["verilator_option_readiness_status"], "not_ready_for_verilator_option_shim")
                self.assertFalse(readiness["ready_for_direct_verilator_option"])
                self.assertIn("direct Verilator resident sidecar handoff is not ready", readiness["not_ready_reason"])
                self.assertIn(
                    "direct_verilator_resident_sidecar_handoff",
                    resolved["stage_plan"]["verilator_option_readiness"]["missing"],
                )

    def test_unsupported_mode_is_not_planned_native_verilator_evidence(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        context = _sidecar_context()
        context["mode"] = "unknown-mode"

        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=context,
        )

        self.assertEqual(resolved["status"], "unsupported_for_stage_plan")
        self.assert_non_executing_plan_resolution(resolved)
        self.assertEqual(resolved["stage_plan"]["status"], "unsupported_for_stage_plan")
        readiness = resolved["plan_resolution_readiness"]
        self.assertEqual(readiness["stage_plan_status"], "unsupported_for_stage_plan")
        self.assertIsNone(readiness["verilator_option_readiness_status"])
        self.assertFalse(readiness["ready_for_direct_verilator_option"])
        self.assertIn("not the template sidecar build/run/compare plan", readiness["not_ready_reason"])


if __name__ == "__main__":
    unittest.main()
