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
    / "implement_verilator_native_option_parser_direct_command_path_fixture_gate.json"
)
REVIEW_IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_direct_command_path_fixture_implementation_gate.json"
)
PAYLOAD_VALIDATION_HARDENING_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json"
)
PAYLOAD_VALIDATION_HARDENING_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json"
)
PAYLOAD_VALIDATION_HARDENING_IMPLEMENT_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json"
)
PAYLOAD_VALIDATION_HARDENING_IMPLEMENT_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_implementation_gate.json"
)
SIDECAR_STAGE_PLAN_MATERIALIZATION_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate.json"
)

BASE_DIRECT_ARGS = [
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
    added = False
    if tools_s not in sys.path:
        sys.path.insert(0, tools_s)
        added = True
    try:
        return tuple(importlib.import_module(name) for name in names)
    finally:
        if added:
            sys.path.remove(tools_s)


def _expanded_argv() -> list[str]:
    return [
        *BASE_DIRECT_ARGS,
        "--sim-accel",
        "sidecar-gpu",
        "--sim-accel-states",
        "64",
        "--sim-accel-steps",
        "1",
    ]


def _sidecar_context() -> dict[str, object]:
    return {
        "target": "pulp_ita_mha",
        "mode": "template",
        "template_or_target_registry_entry": "config/slice_launch_templates/pulp_ita_mha.json",
        "source_gate_or_manifest_ref": (
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_gate.json"
        ),
    }


class VerilatorNativeOptionParserDirectCommandPathFixtureTest(unittest.TestCase):
    def test_implementation_gate_records_non_executing_fixture_scope(self) -> None:
        gate = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_fixture_implementation_gate",
        )
        implemented = gate["implemented_surface"]
        self.assertEqual(
            implemented["module"],
            "src/tools/verilator_native_option_parser_direct_command_path_fixture.py",
        )
        self.assertEqual(implemented["primary_entrypoint_function"], "define_direct_command_path_sidecar_plan_fixture")
        self.assertFalse(implemented["public_cli_added"])
        self.assertFalse(implemented["sidecar_stage_plan_invoked"])
        self.assertFalse(implemented["new_execution_added"])
        self.assertFalse(gate["acceptance_policy"]["coverage_output_equivalence_claim_allowed_by_gate_alone"])

    def test_review_gate_accepts_helper_but_requires_payload_validation_hardening(self) -> None:
        review = json.loads(REVIEW_IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate",
        )
        self.assertEqual(
            review["accepted_followup_gap"]["name"],
            "parser_payload_required_field_validation_gap",
        )
        self.assertFalse(
            review["validated_implementation_decisions"]["parser_payload_required_identity_fields_are_strictly_validated"]
        )
        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate",
        )
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])

    def test_payload_validation_hardening_definition_requires_full_parser_stub_payload(self) -> None:
        gate = json.loads(PAYLOAD_VALIDATION_HARDENING_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_implementation_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate",
        )
        authority = gate["parser_payload_schema_authority"]
        self.assertEqual(authority["source_field_tuple"], "HANDOFF_FIELDS")
        self.assertEqual(authority["canonical_surface"], "native_verilator_parser_stub_fixture")
        self.assertTrue(authority["exact_parser_stub_keyset_required"])

        required = gate["required_parser_payload_fields"]["complete_required_keyset"]
        for field in (
            "schema_version",
            "surface",
            "mdir",
            "top_module",
            "source_boundary_status",
            "state_and_report_naming_rules",
            "non_claims",
        ):
            self.assertIn(field, required)
        rejections = gate["required_rejections_before_boundary_metadata"]
        self.assertIn("missing any complete_required_keyset field", rejections)
        self.assertIn("unknown parser_payload keys outside the parser-stub handoff keyset", rejections)
        self.assertIn("mdir or top_module missing, null, empty, or non-string", rejections)
        self.assertFalse(gate["acceptance_policy"]["implementation_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate",
        )

    def test_payload_validation_hardening_review_accepts_implementation_gate(self) -> None:
        review = json.loads(PAYLOAD_VALIDATION_HARDENING_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("Exact parser-stub keyset validation is deliberately rigid", review["review_decision"]["weakest_point"])
        self.assertEqual(
            review["current_priority"],
            "implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate",
        )
        accepted = review["accepted_definition"]
        self.assertEqual(accepted["parser_payload_schema_authority"], "src/tools/verilator_native_option_parser_stub_fixture.py::HANDOFF_FIELDS")
        self.assertTrue(accepted["exact_parser_stub_keyset_required"])
        required = review["required_next_implementation"]
        self.assertEqual(
            required["name"],
            "implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate",
        )
        self.assertIn("src/tools/verilator_native_option_parser_direct_command_payload_validation.py", required["allowed_files"])
        self.assertIn("missing schema_version rejects before sidecar_plan_boundary metadata", required["must_test"])
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_option_claim_allowed_by_gate_alone"])

    def test_payload_validation_hardening_implementation_records_split_helper(self) -> None:
        gate = json.loads(PAYLOAD_VALIDATION_HARDENING_IMPLEMENT_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_implementation_gate",
        )
        implemented = gate["implemented_surface"]
        self.assertEqual(
            implemented["validation_module"],
            "src/tools/verilator_native_option_parser_direct_command_payload_validation.py",
        )
        self.assertFalse(implemented["new_public_cli_added"])
        self.assertFalse(implemented["new_execution_added"])
        decisions = gate["implementation_decisions"]
        self.assertTrue(decisions["split_validation_helper_added"])
        self.assertTrue(decisions["exact_parser_stub_handoff_keyset_required"])
        self.assertTrue(decisions["unknown_non_sidecar_parser_payload_keys_reject"])
        self.assertTrue(decisions["bool_state_count_and_step_count_reject_before_shape_compare"])
        self.assertEqual(gate["verified_commands"]["focused_contract_test_count"], 11)
        self.assertFalse(gate["acceptance_policy"]["native_verilator_option_claim_allowed_by_gate_alone"])

    def test_payload_validation_hardening_implementation_review_selects_materialization_boundary(self) -> None:
        review = json.loads(PAYLOAD_VALIDATION_HARDENING_IMPLEMENT_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("Exact parser-stub keyset validation", review["review_decision"]["weakest_point"])
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate",
        )
        accepted = review["accepted_surface"]
        self.assertEqual(
            accepted["validation_module"],
            "src/tools/verilator_native_option_parser_direct_command_payload_validation.py",
        )
        self.assertFalse(accepted["sidecar_stage_plan_invoked"])
        contract = review["reviewed_validation_contract"]
        self.assertTrue(contract["exact_parser_stub_handoff_keyset_required"])
        self.assertTrue(contract["bool_state_count_and_step_count_reject_before_shape_compare"])
        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate",
        )
        self.assertFalse(review["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["sidecar_stage_execution_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["timing_or_speedup_claim_allowed_by_gate_alone"])

    def test_sidecar_stage_plan_materialization_boundary_requires_reviewed_bridge(self) -> None:
        gate = json.loads(SIDECAR_STAGE_PLAN_MATERIALIZATION_BOUNDARY_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_implementation_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate",
        )
        route = gate["allowed_materialization_route"]
        self.assertTrue(route["direct_fixture_must_not_call_sidecar_stage_plan_directly"])
        self.assertIn(
            "src/tools/verilator_native_option_parser_sidecar_handoff.py::build_native_parser_sidecar_handoff(parser_payload)",
            route["first_allowed_bridge"],
        )
        self.assertIn(
            "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py::resolve_native_parser_adapter_payload_to_sidecar_plan(adapter_payload, sidecar_context=<normalized_context>)",
            route["first_allowed_bridge"],
        )
        normalization = gate["sidecar_context_normalization_boundary"]
        self.assertIn("template_or_target_registry_entry", normalization["required_direct_fixture_context_fields"])
        self.assertEqual(
            normalization["normalization_rules"]["template_or_target_registry_entry_string"],
            "map to plan-resolution context field template",
        )
        status_mapping = gate["materialized_stage_plan_status_mapping"]
        self.assertEqual(status_mapping["ready_mapping"]["outer_status"], "ready_for_verilator_option_shim")
        self.assertEqual(status_mapping["unsupported_mapping"]["outer_status"], "unsupported_for_stage_plan")
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate",
        )
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["sidecar_stage_plan_materialization_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["coverage_output_equivalence_claim_allowed_by_gate_alone"])

    def test_accepts_expanded_64x1_and_returns_reference_only_boundary(self) -> None:
        (fixture,) = _load_tool_modules("verilator_native_option_parser_direct_command_path_fixture")

        result = fixture.define_direct_command_path_sidecar_plan_fixture(
            _expanded_argv(),
            sidecar_context=_sidecar_context(),
        )

        self.assertEqual(tuple(result), fixture.DIRECT_COMMAND_PATH_FIXTURE_FIELDS)
        self.assertEqual(result["surface"], "native_verilator_parser_direct_command_path_fixture")
        self.assertEqual(result["status"], "fixture_contract_ready_for_sidecar_plan_boundary")
        self.assertEqual(result["accelerator_mode"], "sidecar-gpu")
        self.assertEqual(result["state_count"], 64)
        self.assertEqual(result["step_count"], 1)
        self.assertEqual(result["shape"], "64x1")
        self.assertEqual(result["ordinary_verilator_args"], BASE_DIRECT_ARGS)
        self.assertEqual(result["mdir"], "artifacts/pulp_ita_mha_obj_dir")
        self.assertEqual(result["top_module"], "pulp_ita_mha_gpu_cov_tb")
        self.assertEqual(result["source_files"], ["overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv"])
        self.assertEqual(result["filelists"], ["config/slice_launch_templates/pulp_ita_mha.filelist"])
        self.assertEqual(result["defines"], ["-DTRACE=1"])
        self.assertEqual(result["include_dirs"], ["-Ioverlays/ITA/src"])
        self.assertEqual(result["warning_flags"], ["-Wno-fatal"])
        boundary = result["sidecar_plan_boundary"]
        self.assertEqual(boundary["source_boundary_status"], "preserved_only_not_resolved")
        self.assertEqual(boundary["coverage_output_target"], "pulp_ita_mha")
        self.assertEqual(boundary["stage_order_required"], list(fixture.DIRECT_COMMAND_STAGE_ORDER))
        self.assertEqual(result["correctness_policy_ref"], "coverage_output_equivalence")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["measurement_performed"])
        self.assertFalse(result["timing_measured"])
        self.assertFalse(result["runtime_or_abi_changed"])
        self.assertFalse(result["source_closure_inferred"])
        self.assertFalse(result["filelists_expanded"])
        self.assertFalse(result["automatic_gpu_allocation_used"])

    def test_accepts_exact_parser_stub_payload_directly(self) -> None:
        fixture, parser_stub = _load_tool_modules(
            "verilator_native_option_parser_direct_command_path_fixture",
            "verilator_native_option_parser_stub_fixture",
        )
        parser_payload = parser_stub.parse_verilator_native_option_stub(_expanded_argv())

        result = fixture.direct_command_parser_payload_to_sidecar_plan_fixture(
            parser_payload,
            sidecar_context=_sidecar_context(),
        )

        self.assertEqual(result["parser_payload"]["surface"], "native_verilator_parser_stub_fixture")
        self.assertEqual(result["parser_payload"]["source_boundary_status"], "preserved_only_not_resolved")
        self.assertEqual(result["parser_preserved_build_inputs"]["mdir"], "artifacts/pulp_ita_mha_obj_dir")
        self.assertEqual(result["parser_preserved_build_inputs"]["top_module"], "pulp_ita_mha_gpu_cov_tb")
        self.assertEqual(result["shape"], "64x1")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["measurement_performed"])
        self.assertFalse(result["source_closure_inferred"])

    def test_rejects_malformed_parser_payloads_before_boundary_metadata(self) -> None:
        fixture, parser_stub = _load_tool_modules(
            "verilator_native_option_parser_direct_command_path_fixture",
            "verilator_native_option_parser_stub_fixture",
        )
        base_payload = parser_stub.parse_verilator_native_option_stub(_expanded_argv())

        cases = {
            "missing_schema_version": lambda payload: payload.pop("schema_version"),
            "wrong_surface": lambda payload: payload.__setitem__("surface", "wrong_surface"),
            "missing_mdir": lambda payload: payload.pop("mdir"),
            "empty_top_module": lambda payload: payload.__setitem__("top_module", ""),
            "bool_state_count": lambda payload: payload.__setitem__("state_count", True),
            "bool_step_count": lambda payload: payload.__setitem__("step_count", True),
            "bad_source_files": lambda payload: payload.__setitem__("source_files", [1]),
            "unknown_field": lambda payload: payload.__setitem__("unexpected_parser_field", "x"),
            "missing_non_claims": lambda payload: payload.pop("non_claims"),
        }

        for name, mutate in cases.items():
            malformed = dict(base_payload)
            mutate(malformed)
            with self.subTest(name=name):
                with self.assertRaises(fixture.NativeParserDirectCommandPathFixtureError) as raised:
                    fixture.direct_command_parser_payload_to_sidecar_plan_fixture(
                        malformed,
                        sidecar_context=_sidecar_context(),
                    )
                self.assertEqual(raised.exception.code, "invalid_parser_payload")
                self.assertEqual(raised.exception.rejection_layer, "direct_command_path_fixture_contract")

    def test_shape_rejections_use_direct_fixture_layer(self) -> None:
        (fixture,) = _load_tool_modules("verilator_native_option_parser_direct_command_path_fixture")
        cases = [
            (
                [*BASE_DIRECT_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64"],
                "missing_sim_accel_shape_half",
            ),
            (
                [*BASE_DIRECT_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-steps", "1"],
                "missing_sim_accel_shape_half",
            ),
            (
                [
                    *BASE_DIRECT_ARGS,
                    "--sim-accel",
                    "sidecar-gpu",
                    "--sim-accel-states",
                    "0",
                    "--sim-accel-steps",
                    "1",
                ],
                "nonpositive_sim_accel_count",
            ),
            (
                [*BASE_DIRECT_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-shape", "64x1"],
                "compact_shape_spelling_outside_native_minimum",
            ),
            (
                [
                    *_expanded_argv(),
                    "--sim-accel-shape",
                    "64x1",
                ],
                "mixed_sim_accel_shape_spelling",
            ),
        ]

        for argv, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(fixture.NativeParserDirectCommandPathFixtureError) as raised:
                    fixture.define_direct_command_path_sidecar_plan_fixture(
                        argv,
                        sidecar_context=_sidecar_context(),
                    )
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(raised.exception.rejection_layer, "direct_command_path_fixture_contract")

    def test_rejects_missing_context_before_boundary_reference(self) -> None:
        (fixture,) = _load_tool_modules("verilator_native_option_parser_direct_command_path_fixture")

        for missing in fixture.REQUIRED_CONTEXT_FIELDS:
            context = _sidecar_context()
            context.pop(missing)
            with self.subTest(missing=missing):
                with self.assertRaises(fixture.NativeParserDirectCommandPathFixtureError) as raised:
                    fixture.define_direct_command_path_sidecar_plan_fixture(
                        _expanded_argv(),
                        sidecar_context=context,
                    )
                self.assertEqual(raised.exception.code, "missing_explicit_sidecar_context")
                self.assertEqual(raised.exception.rejection_layer, "direct_command_path_fixture_contract")

    def test_rejects_prepopulated_sidecar_owned_parser_fields(self) -> None:
        fixture, parser_stub = _load_tool_modules(
            "verilator_native_option_parser_direct_command_path_fixture",
            "verilator_native_option_parser_stub_fixture",
        )
        parser_payload = parser_stub.parse_verilator_native_option_stub(_expanded_argv())

        for field, value in (
            ("state_files", {"init": "artifacts/init.bin"}),
            ("verilator_command_argv", ["verilator", "--cc"]),
        ):
            mutated = dict(parser_payload)
            mutated[field] = value
            with self.subTest(field=field):
                with self.assertRaises(fixture.NativeParserDirectCommandPathFixtureError) as raised:
                    fixture.direct_command_parser_payload_to_sidecar_plan_fixture(
                        mutated,
                        sidecar_context=_sidecar_context(),
                    )
                self.assertEqual(raised.exception.code, "sidecar_owned_field_prepopulated_by_parser")
                self.assertEqual(raised.exception.rejection_layer, "direct_command_path_fixture_contract")


if __name__ == "__main__":
    unittest.main()
