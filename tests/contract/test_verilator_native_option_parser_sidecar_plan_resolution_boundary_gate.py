import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from verilator_native_option_parser_sidecar_handoff import (  # noqa: E402
    ADAPTER_PAYLOAD_FIELDS,
    CORRECTNESS_POLICY_REFERENCE_STATUS,
    SIDECAR_OWNED_RESOLUTION_STATUS,
)


GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionBoundaryGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_definition_requires_explicit_sidecar_context_before_plan_resolution(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_implementation_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate",
        )
        decision = gate["definition_decision"]
        self.assertTrue(decision["defined"])
        self.assertIn("no target, mode, template identity", decision["weakest_point"])

        context = gate["required_explicit_sidecar_context"]
        for required in (
            "target",
            "mode",
            "template or target registry entry",
            "source gate or manifest reference when coverage-output target selection needs one",
        ):
            self.assertIn(required, context["required_before_plan_resolution"])
        self.assertIn("sidecar_stage_plan", context["first_allowed_plan_call_after_context_exists"])
        self.assertIn("remain preserved input paths", context["filelist_rule"])

    def test_parser_payload_is_limited_to_adapter_fields_and_guards(self) -> None:
        gate = self.read_gate()
        boundary = gate["accepted_input_boundary"]

        parser_owned = set(boundary["parser_owned_inputs_available_to_plan_resolution"])
        guard_only = set(boundary["adapter_metadata_for_guards_only"])
        self.assertLessEqual(parser_owned | guard_only, set(ADAPTER_PAYLOAD_FIELDS))
        self.assertEqual(
            guard_only & parser_owned,
            set(),
            "guard metadata should not become parser-owned plan data",
        )
        for parser_field in (
            "accelerator_mode",
            "state_count",
            "step_count",
            "shape",
            "ordinary_verilator_args",
            "filelists",
        ):
            self.assertIn(parser_field, parser_owned)
        for forbidden in (
            "target",
            "template",
            "coverage_manifest",
            "host_probe_metadata",
            "state_files",
            "generated_reports",
            "compare",
            "verilator_command_argv",
        ):
            self.assertIn(forbidden, boundary["parser_payload_must_not_supply"])

    def test_sidecar_owns_resolution_outputs_and_correctness_mapping(self) -> None:
        gate = self.read_gate()
        sidecar = gate["sidecar_owned_resolution_fields"]

        for resolved in (
            "source closure",
            "filelist expansion",
            "coverage output target",
            "host-probe metadata",
            "state authority",
            "compare labels",
            "sidecar handoff contract",
        ):
            self.assertIn(resolved, sidecar["resolved_only_by_sidecar_plan_or_operator_layer"])
        self.assertIn("src/tools/hybrid_benchmark_sidecar_plan.py::sidecar_stage_plan", sidecar["existing_authorities"])
        self.assertIn("src/tools/hybrid_benchmark_sidecar_operator.py::sidecar_handoff_contract", sidecar["existing_authorities"])

        mapping = sidecar["correctness_policy_ref_mapping"]
        self.assertEqual(mapping["adapter_field"], "correctness_policy_ref")
        self.assertEqual(mapping["accepted_value"], "coverage_output_equivalence")
        self.assertTrue(mapping["not_evidence"])
        self.assertTrue(mapping["must_match_later_sidecar_policy"])

        guard_statuses = set(gate["accepted_input_boundary"]["adapter_metadata_for_guards_only"])
        self.assertIn("correctness_policy_reference_status", guard_statuses)
        self.assertIn("sidecar_owned_resolution_status", guard_statuses)
        self.assertEqual(
            CORRECTNESS_POLICY_REFERENCE_STATUS,
            "adapter_default_reference_only_not_parser_populated_compare_evidence",
        )
        self.assertEqual(SIDECAR_OWNED_RESOLUTION_STATUS, "unresolved_by_native_parser_adapter_fixture")

    def test_forbids_execution_operator_and_allocation_claims(self) -> None:
        gate = self.read_gate()
        forbidden = gate["forbidden_boundary_crossings"]

        for boundary_crossing in (
            "source closure inference in the parser or adapter payload",
            "filelist dependency inference before a reviewed sidecar policy",
            "coverage manifest selection by the parser",
            "calling sidecar_handoff_contract from the parser adapter",
            "calling synthesized_verilator_command_argv from the parser adapter",
            "calling sidecar_operator_plan from the parser adapter",
            "calling efficiency_estimate from the parser adapter",
            "treating correctness_policy_ref as CPU-vs-hybrid compare evidence",
            "automatic GPU allocation or optimal block-size selection",
            "RTL simulation execution",
            "timing measurement",
        ):
            self.assertIn(boundary_crossing, forbidden)

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["native_verilator_parser_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_validation_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])

        self.assertEqual(
            gate["required_next_gate"]["name"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate",
        )
        self.assertEqual(gate["next_task"], "review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate")


if __name__ == "__main__":
    unittest.main()
