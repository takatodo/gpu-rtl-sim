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
SOURCE_PATCH_BOUNDARY_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_source_patch_boundary_gate.json"
)
OVERLAY_PATCH_DESCRIPTOR_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json"
)
OVERLAY_PATCH_DESCRIPTOR_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json"
)
OVERLAY_PATCH_DESCRIPTOR_IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json"
)
OVERLAY_PATCH_DESCRIPTOR_IMPLEMENTATION_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_implementation_gate.json"
)
OVERLAY_DESCRIPTOR_FILE = (
    REPO_ROOT
    / "overlays"
    / "verilator"
    / "patches"
    / "verilator_native_option_parser_sidecar_gpu_v5_048.json"
)
OVERLAY_PATCH_FILE = (
    REPO_ROOT
    / "overlays"
    / "verilator"
    / "patches"
    / "verilator_native_option_parser_sidecar_gpu_v5_048.patch"
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

    def test_source_patch_boundary_review_requires_descriptor_apply_check_next(self) -> None:
        review = json.loads(SOURCE_PATCH_BOUNDARY_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_source_patch_boundary_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("no descriptor schema", review["review_decision"]["weakest_point"])
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate",
        )
        self.assertEqual(
            review["required_next_gate"]["name"],
            "define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate",
        )
        scope = review["accepted_scope"]
        self.assertEqual(scope["future_patch_root"], "overlays/verilator/patches/")
        self.assertFalse(scope["patch_file_added_by_this_gate"])
        self.assertFalse(scope["vendored_verilator_source_required"])
        self.assertTrue(review["validated_boundary_decisions"]["reproducible_apply_check_required_before_patch_implementation_claim"])
        self.assertTrue(review["validated_boundary_decisions"]["sim_accel_estimate_efficiency_outside_first_source_patch_minimum_until_next_gate_decides"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertEqual(review["next_task"], "define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate")

    def test_overlay_patch_descriptor_gate_pins_apply_check_without_patch_file(self) -> None:
        gate = json.loads(OVERLAY_PATCH_DESCRIPTOR_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_source_patch_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate",
        )
        upstream = gate["upstream_verilator_ref"]
        self.assertEqual(upstream["selected_ref"], "v5.048")
        self.assertEqual(upstream["selected_commit"], "d0aa828c217410fffc73d92077b6f4f54830357c")
        descriptor = gate["overlay_descriptor_boundary"]
        self.assertEqual(descriptor["future_patch_root"], "overlays/verilator/patches/")
        self.assertIn("source_gate", descriptor["required_descriptor_fields"])
        self.assertIn("handoff_contract_ref", descriptor["required_descriptor_fields"])
        self.assertEqual(descriptor["descriptor_status"], "not_added_by_this_gate")
        self.assertEqual(descriptor["patch_file_status"], "not_added_by_this_gate")
        touched_files = gate["allowed_touched_files"]
        self.assertEqual(
            touched_files["required_source_candidates_for_first_patch"],
            ["src/V3Options.h", "src/V3Options.cpp"],
        )
        self.assertIn(
            "src/V3OptionParser.cpp",
            touched_files["inspected_context_files_not_allowed_without_review_expansion"],
        )
        self.assertEqual(gate["apply_check_boundary"]["expected_apply_check_exit_code"], 0)
        self.assertIn(
            "--sim-accel-estimate-efficiency",
            gate["native_parser_option_surface"]["explicitly_deferred_from_first_patch"],
        )
        self.assertTrue(gate["descriptor_definition_decisions"]["upstream_ref_pinned"])
        self.assertFalse(gate["acceptance_policy"]["patch_file_allowed_by_this_gate"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate",
        )

    def test_overlay_patch_descriptor_review_allows_only_next_descriptor_and_patch(self) -> None:
        review = json.loads(OVERLAY_PATCH_DESCRIPTOR_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertIn("not proof that a patch applies", review["review_decision"]["weakest_point"])
        self.assertEqual(
            review["reviewed_upstream_ref"]["selected_commit_kind"],
            "peeled_release_tag_commit",
        )
        self.assertEqual(
            review["current_priority"],
            "implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate",
        )
        descriptor = review["accepted_descriptor_boundary"]
        self.assertEqual(
            descriptor["future_descriptor_path"],
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json",
        )
        self.assertEqual(
            descriptor["future_patch_file"],
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch",
        )
        self.assertFalse(descriptor["descriptor_file_added_by_review_gate"])
        self.assertFalse(descriptor["patch_file_added_by_review_gate"])
        patch_scope = review["accepted_patch_scope"]
        self.assertEqual(
            patch_scope["allowed_upstream_source_files_for_first_patch"],
            ["src/V3Options.h", "src/V3Options.cpp"],
        )
        self.assertIn("src/V3OptionParser.cpp", patch_scope["not_allowed_without_new_review"])
        self.assertIn("--sim-accel-shape <NxS>", patch_scope["deferred_from_first_patch"])
        write_set = review["next_gate_write_set"]
        self.assertIn(
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json",
            write_set["may_add"],
        )
        self.assertIn(
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch",
            write_set["may_add"],
        )
        self.assertIn("third_party/verilator", write_set["must_not_add"])
        self.assertTrue(review["acceptance_policy"]["descriptor_file_allowed_by_next_gate"])
        self.assertTrue(review["acceptance_policy"]["patch_file_allowed_by_next_gate"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertEqual(
            review["next_task"],
            "implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate",
        )

    def test_overlay_patch_descriptor_and_patch_match_accepted_boundary(self) -> None:
        descriptor = json.loads(OVERLAY_DESCRIPTOR_FILE.read_text(encoding="utf-8"))
        patch_text = OVERLAY_PATCH_FILE.read_text(encoding="utf-8")

        self.assertEqual(
            descriptor["source_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json",
        )
        self.assertEqual(descriptor["upstream_ref"], "v5.048")
        self.assertEqual(descriptor["upstream_commit"], "d0aa828c217410fffc73d92077b6f4f54830357c")
        self.assertEqual(descriptor["upstream_commit_kind"], "peeled_release_tag_commit")
        self.assertEqual(
            descriptor["descriptor_path"],
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json",
        )
        self.assertEqual(
            descriptor["patch_path"],
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch",
        )
        self.assertEqual(descriptor["allowed_touched_files"], ["src/V3Options.h", "src/V3Options.cpp"])
        self.assertEqual(descriptor["native_parser_option_surface"]["registration_visibility"], "undocumented")
        self.assertEqual(descriptor["patch_behavior"]["scope"], "parse_store_and_validate_only")
        self.assertTrue(descriptor["patch_behavior"]["does_not_launch_sidecar_runtime"])
        self.assertIn("src/V3OptionParser.cpp", descriptor["scope_exclusions"])
        self.assertIn("not upstream build or regression-test evidence", descriptor["non_claims"])
        self.assertIn("diff --git a/src/V3Options.cpp b/src/V3Options.cpp", patch_text)
        self.assertIn("diff --git a/src/V3Options.h b/src/V3Options.h", patch_text)
        self.assertIn('DECL_OPTION("-sim-accel"', patch_text)
        self.assertIn('}).undocumented();', patch_text)
        self.assertIn("m_simAccelStates", patch_text)
        self.assertNotIn("diff --git a/src/V3OptionParser.cpp", patch_text)
        self.assertNotIn("diff --git a/docs/guide/exe_verilator.rst", patch_text)

    def test_overlay_patch_descriptor_apply_check_implementation_records_verification(self) -> None:
        gate = json.loads(OVERLAY_PATCH_DESCRIPTOR_IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_implementation_gate",
        )
        payload = gate["implemented_payload"]
        self.assertTrue(payload["descriptor_added_by_this_gate"])
        self.assertTrue(payload["patch_file_added_by_this_gate"])
        self.assertFalse(payload["vendored_verilator_source_added"])
        self.assertFalse(payload["public_cli_added"])
        self.assertEqual(gate["descriptor_contract"]["allowed_touched_files"], ["src/V3Options.h", "src/V3Options.cpp"])
        self.assertEqual(gate["verification"]["descriptor_validation_exit_code"], 0)
        self.assertEqual(gate["verification"]["apply_check_exit_code"], 0)
        self.assertIn("patch applicability only", gate["verification"]["verification_scope"])
        self.assertEqual(gate["patch_summary"]["registration_visibility"], "undocumented_to_keep_docs_and_upstream_regression_files_out_of_first_patch_scope")
        self.assertFalse(gate["acceptance_policy"]["verilator_build_success_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_implementation_gate",
        )

    def test_overlay_patch_descriptor_apply_check_implementation_review_selects_build_only_validation(self) -> None:
        review = json.loads(OVERLAY_PATCH_DESCRIPTOR_IMPLEMENTATION_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(
            review["current_priority"],
            "define_verilator_native_option_parser_overlay_patch_build_only_validation_gate",
        )
        self.assertEqual(
            review["reviewed_payload"]["descriptor_path"],
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json",
        )
        self.assertEqual(
            review["reviewed_patch_scope"]["touched_upstream_files"],
            ["src/V3Options.h", "src/V3Options.cpp"],
        )
        self.assertIn("std::atoi", review["reviewed_patch_scope"]["known_validation_caveat"])
        self.assertEqual(review["reviewed_verification"]["apply_check_exit_code"], 0)
        self.assertFalse(review["acceptance_policy"]["verilator_build_success_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["native_verilator_parser_support_claim_allowed_by_gate_alone"])
        self.assertEqual(
            review["next_task"],
            "define_verilator_native_option_parser_overlay_patch_build_only_validation_gate",
        )


if __name__ == "__main__":
    unittest.main()
