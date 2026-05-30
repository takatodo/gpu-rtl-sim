import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionBoundaryReviewGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_review_accepts_only_explicit_context_plan_resolution_boundary(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_definition_gate"],
            "config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json",
        )
        self.assertEqual(
            gate["source_fixture_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate",
        )
        self.assertTrue(gate["review_decision"]["accepted"])
        self.assertIn("No helper yet combines adapter payload", gate["review_decision"]["weakest_point"])

        boundary = gate["accepted_boundary"]
        self.assertEqual(
            boundary["selected_surface"],
            "native_parser_adapter_payload_to_existing_sidecar_stage_plan_resolution_boundary",
        )
        self.assertEqual(boundary["plan_resolution_implementation_status"], "not_implemented")
        self.assertFalse(boundary["sidecar_stage_plan_invoked_by_this_gate"])
        self.assertFalse(boundary["sidecar_handoff_contract_invoked_by_this_gate"])
        self.assertFalse(boundary["new_execution_added"])
        self.assertFalse(boundary["new_measurement_added"])

    def test_review_keeps_parser_inputs_separate_from_sidecar_resolution(self) -> None:
        gate = self.read_gate()
        boundary = gate["accepted_boundary"]

        for parser_input in (
            "accelerator_mode",
            "state_count",
            "step_count",
            "shape",
            "ordinary_verilator_args",
            "filelists",
        ):
            self.assertIn(parser_input, boundary["accepted_parser_owned_inputs"])
        for guard_field in (
            "correctness_policy_ref",
            "sidecar_owned_resolution_status",
            "unresolved_sidecar_responsibilities",
        ):
            self.assertIn(guard_field, boundary["accepted_guard_metadata_only"])
        for context_field in (
            "target",
            "mode",
            "template or target registry entry",
            "source gate or manifest reference when coverage-output target selection needs one",
        ):
            self.assertIn(context_field, boundary["required_explicit_sidecar_context_before_resolution"])
        for sidecar_field in (
            "source closure",
            "filelist expansion",
            "coverage output target",
            "host-probe metadata",
            "state authority",
            "compare labels",
            "sidecar handoff contract",
        ):
            self.assertIn(sidecar_field, boundary["sidecar_owned_resolution_fields"])

        self.assertEqual(boundary["correctness_policy_ref_status"], "reference_only_not_compare_evidence")
        self.assertEqual(boundary["accepted_correctness_policy_ref"], "coverage_output_equivalence")

    def test_review_validates_non_inference_and_non_execution_decisions(self) -> None:
        gate = self.read_gate()
        decisions = gate["validated_definition_decisions"]

        self.assertTrue(decisions["adapter_payload_alone_is_insufficient_for_plan_resolution"])
        self.assertTrue(decisions["explicit_target_mode_template_context_required"])
        self.assertTrue(decisions["parser_owned_inputs_remain_schedule_and_preserved_build_inputs"])
        self.assertTrue(decisions["adapter_guard_metadata_is_not_resolved_plan_data"])
        self.assertTrue(decisions["source_closure_inference_stays_out_of_parser_payload"])
        self.assertTrue(decisions["filelist_expansion_requires_reviewed_sidecar_policy"])
        self.assertTrue(decisions["coverage_output_selection_stays_out_of_parser_payload"])
        self.assertTrue(decisions["host_probe_metadata_selection_stays_out_of_parser_payload"])
        self.assertTrue(decisions["correctness_policy_ref_is_not_compare_evidence"])
        self.assertTrue(decisions["sidecar_handoff_contract_stays_out_of_parser_adapter"])
        self.assertTrue(decisions["runtime_or_abi_change_stays_out_of_scope"])
        self.assertTrue(decisions["rtl_simulation_execution_stays_out_of_scope"])
        self.assertTrue(decisions["automatic_gpu_allocation_stays_out_of_scope"])

    def test_next_gate_is_non_executing_fixture_only(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate",
        )
        self.assertIn(
            "an importable, non-executing helper that accepts the reviewed adapter payload plus explicit sidecar context",
            next_gate["must_implement"],
        )
        self.assertIn(
            "tests proving the helper rejects missing target, mode, and template or registry context",
            next_gate["must_implement"],
        )
        for forbidden in (
            "run RTL simulation",
            "change runtime or GPU ABI",
            "infer arbitrary source closure or filelist dependencies",
            "run coverage-output compare",
            "measure timing",
            "add a public CLI",
            "claim arbitrary RTL or arbitrary filelist support",
            "claim automatic optimal GPU allocation",
        ):
            self.assertIn(forbidden, next_gate["must_not_do"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertTrue(policy["definition_accepted"])
        self.assertTrue(policy["non_executing_plan_resolution_fixture_allowed_next"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["arbitrary_filelist_support_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate")


if __name__ == "__main__":
    unittest.main()
