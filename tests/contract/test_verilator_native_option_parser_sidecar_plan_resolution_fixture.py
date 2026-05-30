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
        self.assertFalse(resolved["efficiency_estimate_invoked"])
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

    def assert_non_executing_handoff_contract_fixture(self, resolved: dict[str, object]) -> None:
        self.assertTrue(resolved["sidecar_handoff_contract_invoked"])
        self.assertFalse(resolved["command_synthesis_invoked"])
        self.assertFalse(resolved["operator_plan_invoked"])
        self.assertFalse(resolved["execution_performed"])
        self.assertFalse(resolved["measurement_performed"])
        self.assertFalse(resolved["timing_measured"])
        self.assertFalse(resolved["runtime_or_abi_changed"])
        self.assertFalse(resolved["source_closure_inferred"])
        self.assertFalse(resolved["filelists_expanded"])
        self.assertFalse(resolved["automatic_gpu_allocation_used"])
        for field in (
            "operator_plan",
            "verilator_command",
            "verilator_command_argv",
            "timing",
            "efficiency_estimate",
        ):
            self.assertNotIn(field, resolved)

    def assert_non_executing_operator_plan_fixture(self, resolved: dict[str, object]) -> None:
        self.assertTrue(resolved["sidecar_handoff_contract_invoked"])
        self.assertTrue(resolved["command_synthesis_invoked"])
        self.assertTrue(resolved["operator_plan_invoked"])
        self.assertTrue(resolved["efficiency_estimate_invoked"])
        self.assertFalse(resolved["execution_performed"])
        self.assertFalse(resolved["measurement_performed"])
        self.assertFalse(resolved["timing_measured"])
        self.assertFalse(resolved["runtime_or_abi_changed"])
        self.assertFalse(resolved["source_closure_inferred"])
        self.assertFalse(resolved["filelists_expanded"])
        self.assertFalse(resolved["automatic_gpu_allocation_used"])
        self.assertEqual(resolved["correctness_policy_ref_status"], "reference_only_not_compare_evidence")

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

    def test_ready_plan_resolution_builds_handoff_contract_metadata_only(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )

        handoff = plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)

        self.assertEqual(
            handoff["surface"],
            "native_verilator_parser_sidecar_plan_resolution_handoff_contract_fixture",
        )
        self.assertEqual(handoff["status"], "ready_for_sidecar_handoff_contract_metadata")
        self.assertEqual(handoff["input_surface"], "native_verilator_parser_sidecar_plan_resolution_fixture")
        self.assertEqual(handoff["input_status"], "ready_for_verilator_option_shim")
        self.assert_non_executing_handoff_contract_fixture(handoff)
        self.assertEqual(handoff["correctness_policy_ref_status"], "reference_only_not_compare_evidence")
        self.assertEqual(handoff["correctness_policy"], "coverage_output_equivalence")
        self.assertTrue(handoff["parser_schedule_cross_check"]["shape_matches_handoff_contract"])

        contract = handoff["handoff_contract"]
        self.assertEqual(contract["shape"], "64x1")
        self.assertEqual(contract["nstates"], 64)
        self.assertEqual(contract["steps"], 1)
        self.assertEqual(contract["state_authority"], "cpu_init_state_to_hybrid_candidate_dump")
        self.assertIn("init_state", contract["state_files"])
        self.assertIn("reference_dump", contract["state_files"])
        self.assertIn("candidate_dump", contract["state_files"])
        self.assertEqual(contract["compare"]["correctness_policy"], "coverage_output_equivalence")
        self.assertIn("compare_report", contract["generated_reports"])
        self.assertIn("stage_plan", handoff)
        self.assertEqual(
            handoff["parser_input_resolution_role"]["source_files"],
            "preserved_parser_input_not_source_closure",
        )

    def test_ready_handoff_contract_builds_operator_plan_metadata_only(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        handoff = plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)

        operator_metadata = plan_resolution.resolve_native_parser_handoff_contract_to_sidecar_operator_plan(handoff)

        self.assertEqual(operator_metadata["surface"], "native_verilator_parser_sidecar_operator_plan_fixture")
        self.assertEqual(operator_metadata["status"], "ready_for_sidecar_operator_plan_metadata")
        self.assertTrue(operator_metadata["operator_plan_metadata_allowed"])
        self.assert_non_executing_operator_plan_fixture(operator_metadata)
        self.assertEqual(operator_metadata["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(operator_metadata["handoff_contract"]["shape"], "64x1")
        self.assertEqual(operator_metadata["efficiency_estimate"]["target"], "pulp_ita_mha")
        self.assertEqual(operator_metadata["efficiency_estimate"]["shape"], "64x1")
        self.assertEqual(operator_metadata["efficiency_estimate"]["speedup_class"], "high")
        self.assertEqual(operator_metadata["operator_plan"]["command_argv"], operator_metadata["command_argv"])
        self.assertEqual(
            operator_metadata["operator_plan"]["estimate_command_argv"],
            operator_metadata["estimate_command_argv"],
        )
        self.assertIn("--sim-accel sidecar-gpu", operator_metadata["requested_compatibility_entrypoint"])
        self.assertIn("--sim-accel-estimate-efficiency", operator_metadata["estimate_command"])
        self.assertIn("not measured timing", operator_metadata["estimate_metadata_boundary"])
        self.assertEqual(
            operator_metadata["parser_input_resolution_role"]["filelists"],
            "preserved_parser_input_not_filelist_expansion",
        )

    def test_not_ready_and_unsupported_handoff_contracts_fail_closed_before_operator_plan(self) -> None:
        (operator_plan_module, plan_resolution) = _load_tool_modules(
            "verilator_native_option_parser_sidecar_operator_plan",
            "verilator_native_option_parser_sidecar_plan_resolution",
        )
        calls = []

        def fail_authority(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("operator-plan authorities must not be called for closed handoff metadata")

        for mode in ("resident-state-reuse", "persistent-resident-state-abi", "unknown-mode"):
            context = _sidecar_context()
            context["mode"] = mode
            resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                _adapter_payload(),
                sidecar_context=context,
            )
            handoff = plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)
            with self.subTest(mode=mode):
                closed = operator_plan_module.resolve_handoff_contract_to_operator_plan(
                    handoff,
                    command_builder=fail_authority,
                    estimate_command_builder=fail_authority,
                    efficiency_builder=fail_authority,
                    operator_plan_builder=fail_authority,
                )
                self.assertFalse(closed["operator_plan_metadata_allowed"])
                self.assertFalse(closed["command_synthesis_invoked"])
                self.assertFalse(closed["operator_plan_invoked"])
                self.assertFalse(closed["efficiency_estimate_invoked"])
                self.assertIn(closed["status"], {
                    "not_ready_for_sidecar_operator_plan_metadata",
                    "unsupported_for_sidecar_operator_plan_metadata",
                })
                self.assertIn("handoff-contract metadata is not ready", closed["fail_closed_reason"])
                self.assertNotIn("operator_plan", closed)
        self.assertEqual(calls, [])

    def test_handoff_contract_operator_plan_rejects_prepopulated_fields_before_authorities(self) -> None:
        (operator_plan_module, plan_resolution) = _load_tool_modules(
            "verilator_native_option_parser_sidecar_operator_plan",
            "verilator_native_option_parser_sidecar_plan_resolution",
        )
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        handoff = plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)
        handoff["operator_plan"] = {"status": "prepopulated"}
        calls = []

        def fail_authority(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("operator-plan authorities must not be called for prepopulated metadata")

        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "already contains"):
            operator_plan_module.resolve_handoff_contract_to_operator_plan(
                handoff,
                error_factory=plan_resolution.NativeParserSidecarPlanResolutionError,
                command_builder=fail_authority,
                estimate_command_builder=fail_authority,
                efficiency_builder=fail_authority,
                operator_plan_builder=fail_authority,
            )
        self.assertEqual(calls, [])

    def test_handoff_contract_operator_plan_requires_stage_plan_before_authorities(self) -> None:
        (operator_plan_module, plan_resolution) = _load_tool_modules(
            "verilator_native_option_parser_sidecar_operator_plan",
            "verilator_native_option_parser_sidecar_plan_resolution",
        )
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        handoff = plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)
        handoff.pop("stage_plan")
        calls = []

        def fail_authority(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("operator-plan authorities must not be called before stage-plan validation")

        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "stage_plan"):
            operator_plan_module.resolve_handoff_contract_to_operator_plan(
                handoff,
                error_factory=plan_resolution.NativeParserSidecarPlanResolutionError,
                command_builder=fail_authority,
                estimate_command_builder=fail_authority,
                efficiency_builder=fail_authority,
                operator_plan_builder=fail_authority,
            )
        self.assertEqual(calls, [])

    def test_handoff_contract_operator_plan_rejects_stage_plan_mismatch_before_authorities(self) -> None:
        (operator_plan_module, plan_resolution) = _load_tool_modules(
            "verilator_native_option_parser_sidecar_operator_plan",
            "verilator_native_option_parser_sidecar_plan_resolution",
        )
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        handoff = plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)
        stage_plan = dict(handoff["stage_plan"])
        stage_plan["shape"] = "1x64"
        handoff["stage_plan"] = stage_plan
        calls = []

        def fail_authority(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("operator-plan authorities must not be called before shape validation")

        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "stage_plan.shape"):
            operator_plan_module.resolve_handoff_contract_to_operator_plan(
                handoff,
                error_factory=plan_resolution.NativeParserSidecarPlanResolutionError,
                command_builder=fail_authority,
                estimate_command_builder=fail_authority,
                efficiency_builder=fail_authority,
                operator_plan_builder=fail_authority,
            )
        self.assertEqual(calls, [])

    def test_not_ready_and_unsupported_results_fail_closed_before_handoff_contract(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        original = plan_resolution.sidecar_handoff_contract
        calls = []

        def fail_if_called(plan):
            calls.append(plan)
            raise AssertionError("sidecar_handoff_contract must not be called for not-ready results")

        plan_resolution.sidecar_handoff_contract = fail_if_called
        try:
            for mode in ("resident-state-reuse", "persistent-resident-state-abi", "unknown-mode"):
                context = _sidecar_context()
                context["mode"] = mode
                resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
                    _adapter_payload(),
                    sidecar_context=context,
                )
                with self.subTest(mode=mode):
                    closed = plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)
                    self.assertEqual(
                        closed["surface"],
                        "native_verilator_parser_sidecar_plan_resolution_handoff_contract_fixture",
                    )
                    self.assertFalse(closed["handoff_contract_metadata_allowed"])
                    self.assertFalse(closed["sidecar_handoff_contract_invoked"])
                    self.assertIn(closed["status"], {
                        "not_ready_for_sidecar_handoff_contract_metadata",
                        "unsupported_for_sidecar_handoff_contract_metadata",
                    })
                    self.assertIn("not ready", closed["fail_closed_reason"])
                    self.assertIn("stage_plan_status", closed)
                    self.assertIn("plan_resolution_readiness", closed)
                    self.assertNotIn("handoff_contract", closed)
            self.assertEqual(calls, [])
        finally:
            plan_resolution.sidecar_handoff_contract = original

    def test_handoff_contract_rejects_prepopulated_execution_fields(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        resolved["handoff_contract"] = {"shape": "64x1"}

        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "already contains"):
            plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)

    def test_handoff_contract_rejects_efficiency_estimate_before_metadata(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        resolved["efficiency_estimate_invoked"] = True

        original = plan_resolution.sidecar_handoff_contract
        calls = []

        def fail_if_called(plan):
            calls.append(plan)
            raise AssertionError("sidecar_handoff_contract must not be called after estimate metadata")

        plan_resolution.sidecar_handoff_contract = fail_if_called
        try:
            with self.assertRaisesRegex(
                plan_resolution.NativeParserSidecarPlanResolutionError,
                "efficiency_estimate_invoked",
            ):
                plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)
            self.assertEqual(calls, [])
        finally:
            plan_resolution.sidecar_handoff_contract = original

    def test_handoff_contract_rejects_shape_mismatch_before_metadata(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        resolved["stage_plan"] = dict(resolved["stage_plan"])
        resolved["stage_plan"]["shape"] = "1x64"

        with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "does not match"):
            plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)

    def test_handoff_contract_validates_required_stage_details_before_calling_authority(self) -> None:
        (plan_resolution,) = _load_tool_modules("verilator_native_option_parser_sidecar_plan_resolution")
        resolved = plan_resolution.resolve_native_parser_adapter_payload_to_sidecar_plan(
            _adapter_payload(),
            sidecar_context=_sidecar_context(),
        )
        resolved["stage_plan"] = dict(resolved["stage_plan"])
        copied_stages = []
        for stage in resolved["stage_plan"]["stages"]:
            stage_copy = dict(stage)
            if stage_copy.get("stage") == "coverage_output_compare":
                details = dict(stage_copy["details"])
                details.pop("json_out")
                stage_copy["details"] = details
            copied_stages.append(stage_copy)
        resolved["stage_plan"]["stages"] = copied_stages

        original = plan_resolution.sidecar_handoff_contract
        calls = []

        def fail_if_called(plan):
            calls.append(plan)
            raise AssertionError("sidecar_handoff_contract must not be called before detail validation")

        plan_resolution.sidecar_handoff_contract = fail_if_called
        try:
            with self.assertRaisesRegex(plan_resolution.NativeParserSidecarPlanResolutionError, "missing detail fields"):
                plan_resolution.resolve_native_parser_plan_resolution_to_sidecar_handoff_contract(resolved)
            self.assertEqual(calls, [])
        finally:
            plan_resolution.sidecar_handoff_contract = original


if __name__ == "__main__":
    unittest.main()
