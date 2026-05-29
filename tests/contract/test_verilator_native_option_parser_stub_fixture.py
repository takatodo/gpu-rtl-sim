import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "tools"
IMPLEMENTATION_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "implement_verilator_native_option_parser_stub_fixture_gate.json"
)
REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_stub_fixture_implementation_gate.json"
)
SOURCE_PATCH_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_source_patch_boundary_gate.json"
)


sys.path.insert(0, str(TOOLS))
try:
    from verilator_native_option_parser_stub_fixture import (
        HANDOFF_FIELDS,
        NativeOptionParserStubError,
        parse_verilator_native_option_stub,
    )
finally:
    sys.path.pop(0)


BASE_NATIVE_ARGS = [
    "--cc",
    "--timing",
    "-Mdir",
    "obj_dir",
    "--top-module",
    "demo_top",
    "-DTRACE=1",
    "-Wno-fatal",
    "-Irtl/include",
    "-f",
    "rtl/filelist.f",
    "rtl/demo_top.sv",
]


class VerilatorNativeOptionParserStubFixtureTest(unittest.TestCase):
    def parse_base(self) -> dict[str, object]:
        return parse_verilator_native_option_stub(
            [
                *BASE_NATIVE_ARGS,
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ]
        )

    def expect_rejection(self, argv: list[str], code: str) -> NativeOptionParserStubError:
        with self.assertRaises(NativeOptionParserStubError) as raised:
            parse_verilator_native_option_stub(argv)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(raised.exception.rejection_layer, "parser_stub_validation_contract")
        return raised.exception

    def test_accepts_expanded_sidecar_gpu_shape_and_serializes_handoff(self) -> None:
        handoff = self.parse_base()

        self.assertEqual(list(handoff.keys()), list(HANDOFF_FIELDS))
        self.assertEqual(handoff["surface"], "native_verilator_parser_stub_fixture")
        self.assertEqual(handoff["accelerator_mode"], "sidecar-gpu")
        self.assertEqual(handoff["state_count"], 64)
        self.assertEqual(handoff["step_count"], 1)
        self.assertEqual(handoff["shape"], "64x1")
        self.assertEqual(handoff["ordinary_verilator_args"], BASE_NATIVE_ARGS)
        self.assertEqual(handoff["mdir"], "obj_dir")
        self.assertEqual(handoff["top_module"], "demo_top")
        self.assertEqual(handoff["source_files"], ["rtl/demo_top.sv"])
        self.assertEqual(handoff["filelists"], ["rtl/filelist.f"])
        self.assertEqual(handoff["defines"], ["-DTRACE=1"])
        self.assertEqual(handoff["include_dirs"], ["-Irtl/include"])
        self.assertEqual(handoff["warning_flags"], ["-Wno-fatal"])
        self.assertEqual(handoff["source_boundary_status"], "preserved_only_not_resolved")
        self.assertEqual(handoff["correctness_policy"], "coverage_output_equivalence")

    def test_rejects_unknown_accelerator_without_argparse_choices(self) -> None:
        error = self.expect_rejection(
            [
                *BASE_NATIVE_ARGS,
                "--sim-accel",
                "cuda",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ],
            "invalid_sim_accel",
        )

        self.assertEqual(error.unsupported_value, "cuda")
        payload = error.to_dict()
        self.assertEqual(payload["unsupported_value"], "cuda")
        self.assertIn("cuda", str(error))
        self.assertIn("sidecar-gpu", str(error))
        self.assertNotIn("invalid choice", str(error))

    def test_rejects_missing_shape_half(self) -> None:
        self.expect_rejection(
            [*BASE_NATIVE_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64"],
            "missing_sim_accel_shape_half",
        )
        self.expect_rejection(
            [*BASE_NATIVE_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-steps", "1"],
            "missing_sim_accel_shape_half",
        )

    def test_rejects_nonpositive_state_or_step_counts(self) -> None:
        self.expect_rejection(
            [
                *BASE_NATIVE_ARGS,
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "0",
                "--sim-accel-steps",
                "1",
            ],
            "nonpositive_sim_accel_count",
        )
        self.expect_rejection(
            [
                *BASE_NATIVE_ARGS,
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "0",
            ],
            "nonpositive_sim_accel_count",
        )

    def test_rejects_compact_shape_and_mixed_shape_with_native_minimum_error(self) -> None:
        compact_error = self.expect_rejection(
            [*BASE_NATIVE_ARGS, "--sim-accel", "sidecar-gpu", "--sim-accel-shape", "64x1"],
            "compact_shape_spelling_outside_native_minimum",
        )
        mixed_error = self.expect_rejection(
            [
                *BASE_NATIVE_ARGS,
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
                "--sim-accel-shape",
                "64x1",
            ],
            "compact_shape_spelling_outside_native_minimum",
        )

        self.assertIn("wrapper compatibility", str(compact_error))
        self.assertIn("native parser-stub minimum", str(compact_error))
        self.assertEqual(mixed_error.code, compact_error.code)

    def test_preserves_remaining_ordinary_verilator_args(self) -> None:
        argv = [
            "--cc",
            "--trace",
            "-Wall",
            "rtl/other.v",
            "--sim-accel=sidecar-gpu",
            "--sim-accel-states=64",
            "--sim-accel-steps=1",
        ]
        handoff = parse_verilator_native_option_stub(argv)

        self.assertEqual(handoff["ordinary_verilator_args"], ["--cc", "--trace", "-Wall", "rtl/other.v"])
        self.assertEqual(handoff["source_files"], ["rtl/other.v"])
        self.assertEqual(handoff["warning_flags"], ["-Wall"])
        self.assertEqual(handoff["shape"], "64x1")

    def test_implementation_gate_records_parser_only_scope(self) -> None:
        gate = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["current_priority"], "review_verilator_native_option_parser_stub_fixture_implementation_gate")
        self.assertEqual(gate["implemented_surface"]["module"], "src/tools/verilator_native_option_parser_stub_fixture.py")
        self.assertEqual(gate["implemented_surface"]["entrypoint_function"], "parse_verilator_native_option_stub")
        self.assertEqual(gate["implemented_surface"]["unknown_accelerator_rejection_layer"], "parser_stub_validation_contract")
        self.assertTrue(gate["implemented_surface"]["unknown_accelerator_preserves_unsupported_value"])
        self.assertTrue(gate["implemented_surface"]["unknown_accelerator_does_not_use_argparse_choices"])
        self.assertEqual(len(gate["serialized_handoff_fields"]), 18)
        self.assertEqual(gate["field_rules"]["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(gate["verification"]["focused_contract_test_exit_code"], 0)
        self.assertFalse(gate["acceptance_policy"]["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "review_verilator_native_option_parser_stub_fixture_implementation_gate")

    def test_review_gate_accepts_helper_and_selects_source_patch_boundary(self) -> None:
        review = json.loads(REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(review["source_implementation_gate"], "config/scaling_gates/implement_verilator_native_option_parser_stub_fixture_gate.json")
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("not a Verilator source patch", review["review_decision"]["weakest_point"])
        self.assertEqual(review["current_priority"], "define_verilator_native_option_parser_source_patch_boundary_gate")
        self.assertEqual(review["required_next_gate"]["name"], "define_verilator_native_option_parser_source_patch_boundary_gate")
        accepted = review["accepted_scope"]
        self.assertEqual(accepted["unknown_accelerator_rejection_layer"], "parser_stub_validation_contract")
        self.assertTrue(accepted["unknown_accelerator_preserves_unsupported_value"])
        self.assertEqual(accepted["serialized_handoff_field_count"], 18)
        decisions = review["validated_implementation_decisions"]
        self.assertTrue(decisions["argparse_choices_are_not_used_as_success_evidence"])
        self.assertTrue(decisions["filelists_are_preserved_not_expanded"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertEqual(review["next_task"], "define_verilator_native_option_parser_source_patch_boundary_gate")

    def test_source_patch_boundary_defines_overlay_descriptor_without_implementation(self) -> None:
        gate = json.loads(SOURCE_PATCH_BOUNDARY_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["source_review_gate"], "config/scaling_gates/review_verilator_native_option_parser_stub_fixture_implementation_gate.json")
        self.assertEqual(gate["current_priority"], "review_verilator_native_option_parser_source_patch_boundary_gate")
        patch_boundary = gate["patch_boundary"]
        self.assertEqual(patch_boundary["selected_representation"], "repo_overlay_patch_boundary_without_vendored_verilator_source")
        self.assertEqual(patch_boundary["future_patch_root"], "overlays/verilator/patches/")
        self.assertEqual(patch_boundary["future_patch_artifact_status"], "not_added_by_this_gate")
        self.assertEqual(patch_boundary["vendored_verilator_source_status"], "not_allowed_by_this_gate")
        self.assertEqual(gate["native_parser_option_surface"]["accepted_accelerators"], ["sidecar-gpu"])
        validation = gate["validation_mapping"]["invalid_sim_accel"]
        self.assertTrue(validation["must_preserve_unsupported_value"])
        self.assertFalse(validation["argparse_choices_success_evidence_allowed"])
        self.assertIn("source closure inference", gate["handoff_boundary"]["parser_must_not_perform"])
        self.assertEqual(gate["required_next_gate"]["name"], "review_verilator_native_option_parser_source_patch_boundary_gate")
        self.assertFalse(gate["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["patch_file_added_by_this_gate"])


if __name__ == "__main__":
    unittest.main()
