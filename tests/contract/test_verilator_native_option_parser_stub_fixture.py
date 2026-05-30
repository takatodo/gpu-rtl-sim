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
OVERLAY_PATCH_BUILD_ONLY_VALIDATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json"
)
OVERLAY_PATCH_BUILD_ONLY_VALIDATION_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json"
)
OVERLAY_PATCH_BUILD_ONLY_VALIDATION_RUN_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "run_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json"
)
OVERLAY_PATCH_COMPILE_FIX_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_overlay_patch_compile_fix_gate.json"
)
OVERLAY_PATCH_COMPILE_FIX_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json"
)
OVERLAY_PATCH_COMPILE_FIX_IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_overlay_patch_compile_fix_gate.json"
)
OVERLAY_PATCH_COMPILE_FIX_BUILD_ONLY_VALIDATION_RUN_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json"
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
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
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
        self.assertEqual(descriptor["patch_behavior"]["hunk_policy"], "contextual_hunks_only")
        self.assertEqual(
            descriptor["patch_behavior"]["compile_fix_source_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
        )
        self.assertTrue(descriptor["patch_behavior"]["does_not_launch_sidecar_runtime"])
        self.assertFalse(descriptor["compile_fix_anchor_policy"]["zero_context_hunks_allowed"])
        self.assertTrue(descriptor["compile_fix_anchor_policy"]["v3options_h_fields_and_accessors_inside_class"])
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

    def test_overlay_patch_build_only_validation_gate_defines_external_verilator_bin_build(self) -> None:
        gate = json.loads(OVERLAY_PATCH_BUILD_ONLY_VALIDATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_build_only_validation_gate",
        )
        boundary = gate["build_only_validation_boundary"]
        self.assertEqual(boundary["selected_build_target"], "verilator_bin")
        self.assertFalse(boundary["requires_verilator_source_in_repository"])
        self.assertFalse(boundary["writes_under_third_party"])
        self.assertIn("make -j", boundary["command_sequence"][-1])
        self.assertIn("verilator_bin", boundary["command_sequence"][-1])
        self.assertIn("git -C \"$VERILATOR_CHECKOUT\" apply", "\n".join(boundary["command_sequence"]))
        self.assertIn("parser_behavior_execution", gate["explicitly_deferred_validation"])
        self.assertFalse(gate["acceptance_policy"]["build_executed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["verilator_build_success_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["parser_behavior_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_build_only_validation_gate",
        )

    def test_overlay_patch_build_only_validation_review_accepts_run_gate_without_parser_claim(self) -> None:
        review = json.loads(OVERLAY_PATCH_BUILD_ONLY_VALIDATION_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(
            review["current_priority"],
            "run_verilator_native_option_parser_overlay_patch_build_only_validation_gate",
        )
        boundary = review["reviewed_boundary"]
        self.assertEqual(boundary["selected_build_target"], "verilator_bin")
        self.assertFalse(boundary["requires_verilator_source_in_repository"])
        self.assertFalse(boundary["writes_under_third_party"])
        self.assertTrue(boundary["command_sequence_review"]["builds_verilator_bin"])
        self.assertTrue(boundary["command_sequence_review"]["verilator_install_prefix_requires_run_gate_decision"])
        self.assertIn("VERILATOR_INSTALL", "\n".join(review["required_next_gate"]["must_run"]))
        self.assertFalse(review["acceptance_policy"]["build_executed_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["verilator_build_success_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["parser_behavior_claim_allowed_by_gate_alone"])
        self.assertEqual(
            review["next_task"],
            "run_verilator_native_option_parser_overlay_patch_build_only_validation_gate",
        )

    def test_overlay_patch_build_only_validation_run_records_compile_failure(self) -> None:
        gate = json.loads(OVERLAY_PATCH_BUILD_ONLY_VALIDATION_RUN_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json",
        )
        self.assertEqual(gate["status"], "failed_verilator_bin_build_only_validation")
        self.assertEqual(
            gate["current_priority"],
            "define_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )
        self.assertEqual(gate["execution_boundary"]["selected_build_target"], "verilator_bin")
        self.assertTrue(gate["verilator_install"]["mechanically_defaulted"])
        result = gate["observed_result"]
        self.assertEqual(result["apply_check_exit_code"], 0)
        self.assertTrue(result["make_verilator_bin_reached"])
        self.assertEqual(result["make_verilator_bin_exit_code"], 2)
        self.assertFalse(result["build_only_validation_passed"])
        self.assertEqual(result["failure_class"], "patch_compile_link_failure")
        self.assertIn("V3Options.h", result["failure_summary"])
        self.assertIn("artifacts/", result["primary_log_path"])
        self.assertFalse(gate["command_boundary_note"]["initial_full_sequence_wrapper_exit_code_accepted"])
        self.assertIn("#endif", gate["root_cause_evidence"]["observed_bad_region"])
        self.assertFalse(gate["acceptance_policy"]["verilator_build_success_claim_allowed"])
        self.assertFalse(gate["acceptance_policy"]["parser_behavior_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "define_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )
        self.assertEqual(
            gate["next_task"],
            "define_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )

    def test_overlay_patch_compile_fix_gate_defines_contextual_patch_repair(self) -> None:
        gate = json.loads(OVERLAY_PATCH_COMPILE_FIX_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_run_gate"],
            "config/scaling_gates/run_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )
        self.assertEqual(gate["definition_decision"]["selected_fix_strategy"], "fix_existing_overlay_patch_in_place")
        self.assertFalse(gate["definition_decision"]["replacement_descriptor_required"])
        self.assertIn("zero-context", gate["definition_decision"]["weakest_point"])
        failure = gate["observed_failure"]
        self.assertEqual(failure["make_verilator_bin_exit_code"], 2)
        self.assertIn("V3Options.cpp", failure["cpp_failure"])
        shape = gate["required_patch_shape"]
        self.assertTrue(shape["must_use_contextual_hunks"])
        self.assertTrue(shape["must_not_use_zero_context_hunks"])
        self.assertIn("m_verilateJobs", shape["v3options_h_private_count_fields_anchor"]["insert_after"])
        self.assertIn("m_protectKey", shape["v3options_h_private_string_field_anchor"]["insert_after"])
        self.assertIn("verilateJobs()", shape["v3options_h_public_count_accessors_anchor"]["insert_after"])
        self.assertIn("protectKeyDefaulted()", shape["v3options_h_public_string_accessor_anchor"]["insert_after"])
        self.assertIn("V3Options::notify()", shape["v3options_cpp_notify_anchor"]["required_context"])
        self.assertIn("V3Options::parseOptsList()", shape["v3options_cpp_option_registration_anchor"]["required_context"])
        self.assertTrue(gate["rerun_boundary_after_fix"]["requires_fail_fast_wrapper"])
        self.assertFalse(gate["acceptance_policy"]["patch_modified_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["verilator_build_success_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "review_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )

    def test_overlay_patch_compile_fix_review_accepts_implementation_scope(self) -> None:
        review = json.loads(OVERLAY_PATCH_COMPILE_FIX_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            review["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
        )
        self.assertTrue(review["review_decision"]["accepted"])
        self.assertEqual(
            review["current_priority"],
            "implement_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )
        payload = review["reviewed_source_payload"]
        self.assertEqual(payload["selected_fix_strategy"], "fix_existing_overlay_patch_in_place")
        self.assertFalse(payload["replacement_descriptor_required"])
        self.assertEqual(payload["allowed_touched_files"], ["src/V3Options.h", "src/V3Options.cpp"])
        policy = review["reviewed_anchor_policy"]
        self.assertFalse(policy["zero_context_hunks_allowed"])
        self.assertTrue(policy["contextual_hunks_required"])
        self.assertTrue(policy["v3options_h"]["accepted"])
        self.assertTrue(policy["v3options_cpp"]["accepted"])
        self.assertIn("bare '};' anchor is not accepted", policy["v3options_cpp"]["positive_count_parser_anchor_caveat"])
        next_gate = review["required_next_gate"]
        self.assertEqual(
            next_gate["name"],
            "implement_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )
        self.assertIn(
            "overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch",
            next_gate["may_modify"],
        )
        self.assertIn("post-apply location sanity that sim-accel header additions are before the header guard end", next_gate["must_run_or_record"])
        self.assertFalse(review["acceptance_policy"]["patch_modified_by_this_gate"])
        self.assertFalse(review["acceptance_policy"]["verilator_build_success_claim_allowed_by_gate_alone"])
        self.assertFalse(review["acceptance_policy"]["parser_behavior_claim_allowed_by_gate_alone"])
        self.assertEqual(
            review["next_task"],
            "implement_verilator_native_option_parser_overlay_patch_compile_fix_gate",
        )

    def test_overlay_patch_compile_fix_implementation_records_apply_and_location_sanity(self) -> None:
        gate = json.loads(OVERLAY_PATCH_COMPILE_FIX_IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate",
        )
        payload = gate["implemented_payload"]
        self.assertTrue(payload["descriptor_modified_by_this_gate"])
        self.assertTrue(payload["patch_modified_by_this_gate"])
        self.assertFalse(payload["vendored_verilator_source_added"])
        repair = gate["patch_repair_summary"]
        self.assertEqual(repair["hunk_policy"], "contextual_hunks_only")
        self.assertTrue(repair["zero_context_hunks_removed"])
        self.assertEqual(repair["allowed_touched_files"], ["src/V3Options.h", "src/V3Options.cpp"])
        self.assertEqual(repair["observed_touched_files_after_apply"], ["src/V3Options.cpp", "src/V3Options.h"])
        verification = gate["verification"]
        self.assertEqual(verification["descriptor_validation_exit_code"], 0)
        self.assertEqual(verification["apply_check_exit_code"], 0)
        self.assertEqual(verification["apply_exit_code"], 0)
        self.assertEqual(verification["location_sanity_exit_code"], 0)
        self.assertIn("artifacts/", verification["generated_sanity_log"])
        sanity = gate["post_apply_location_sanity"]
        self.assertTrue(all(sanity.values()))
        build = gate["build_only_validation_decision"]
        self.assertFalse(build["make_verilator_bin_executed_by_this_gate"])
        self.assertTrue(build["deferred_to_next_gate"])
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate",
        )
        self.assertFalse(gate["acceptance_policy"]["verilator_build_success_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["parser_behavior_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate",
        )

    def test_overlay_patch_compile_fix_build_only_validation_records_success_scope(self) -> None:
        gate = json.loads(OVERLAY_PATCH_COMPILE_FIX_BUILD_ONLY_VALIDATION_RUN_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_implementation_gate"],
            "config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_compile_fix_gate.json",
        )
        self.assertEqual(gate["status"], "passed_verilator_bin_build_only_validation_after_compile_fix")
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate",
        )
        boundary = gate["execution_boundary"]
        self.assertEqual(boundary["selected_build_target"], "verilator_bin")
        self.assertFalse(boundary["writes_under_third_party"])
        self.assertFalse(boundary["requires_verilator_source_in_repository"])
        self.assertFalse(boundary["parser_behavior_executed"])
        self.assertFalse(boundary["sidecar_runtime_executed"])
        install = gate["verilator_install"]
        self.assertFalse(install["provided_by_environment"])
        self.assertTrue(install["mechanically_defaulted"])
        self.assertIn("artifacts/", install["install_prefix_rel"])
        observed = gate["observed_result"]
        self.assertTrue(observed["descriptor_json_validated"])
        self.assertEqual(observed["descriptor_validation_exit_code"], 0)
        self.assertEqual(observed["apply_check_exit_code"], 0)
        self.assertTrue(observed["patch_applied"])
        self.assertEqual(observed["apply_exit_code"], 0)
        self.assertTrue(observed["autoconf_reached"])
        self.assertEqual(observed["autoconf_exit_code"], 0)
        self.assertTrue(observed["configure_reached"])
        self.assertEqual(observed["configure_exit_code"], 0)
        self.assertTrue(observed["make_verilator_bin_reached"])
        self.assertEqual(observed["make_verilator_bin_exit_code"], 0)
        self.assertTrue(observed["build_only_validation_passed"])
        self.assertIsNone(observed["failure_class"])
        self.assertTrue(observed["primary_log_path"].startswith("artifacts/"))
        self.assertEqual(observed["changed_files_after_apply"], ["src/V3Options.cpp", "src/V3Options.h"])
        next_gate = gate["required_next_gate"]
        self.assertEqual(
            next_gate["name"],
            "review_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate",
        )
        policy = gate["acceptance_policy"]
        self.assertTrue(policy["run_executed"])
        self.assertTrue(policy["build_only_validation_passed"])
        self.assertTrue(policy["compile_link_compatibility_evidence_recorded"])
        self.assertTrue(policy["verilator_build_success_claim_allowed"])
        self.assertFalse(policy["native_verilator_parser_support_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["parser_behavior_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["upstream_regression_success_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["arbitrary_filelist_support_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate",
        )


if __name__ == "__main__":
    unittest.main()
