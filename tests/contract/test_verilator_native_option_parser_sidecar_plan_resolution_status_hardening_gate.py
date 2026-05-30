import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionStatusHardeningGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_definition_uses_fixture_review_as_source_and_selects_review_next(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_fixture_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate",
        )
        self.assertTrue(gate["definition_decision"]["defined"])
        self.assertIn("outer result status to planned", gate["definition_decision"]["weakest_point"])

        next_gate = gate["required_next_gate"]
        self.assertEqual(
            next_gate["name"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate",
        )
        self.assertIn(
            "whether readiness-classifying the outer status while preserving sidecar_stage_plan.status is the correct minimum contract",
            next_gate["must_decide"],
        )

    def test_outer_status_must_be_readiness_classification(self) -> None:
        gate = self.read_gate()
        authority = gate["stage_plan_status_authority"]

        self.assertEqual(
            authority["existing_authority"],
            "src/tools/hybrid_benchmark_sidecar_plan.py::sidecar_stage_plan",
        )
        self.assertTrue(authority["outer_status_must_derive_from_stage_plan_status_and_readiness"])
        self.assertTrue(authority["outer_status_must_be_readiness_classification"])
        self.assertTrue(authority["outer_status_default_planned_is_forbidden"])
        self.assertEqual(
            set(authority["allowed_stage_plan_statuses"]),
            {"planned", "unsupported_for_stage_plan", "planned_not_ready_for_verilator_option_shim"},
        )

        mapping = authority["status_mapping"]
        self.assertEqual(mapping["planned"]["outer_status"], "ready_for_verilator_option_shim")
        self.assertEqual(mapping["unsupported_for_stage_plan"]["outer_status"], "unsupported_for_stage_plan")
        self.assertEqual(
            mapping["planned_not_ready_for_verilator_option_shim"]["outer_status"],
            "not_ready_for_verilator_option_shim",
        )
        self.assertEqual(
            mapping["planned_not_ready_for_verilator_option_shim"]["preserve_stage_plan_status"],
            "planned_not_ready_for_verilator_option_shim",
        )
        self.assertFalse(mapping["unsupported_for_stage_plan"]["ready_for_direct_verilator_option"])
        self.assertFalse(mapping["planned_not_ready_for_verilator_option_shim"]["ready_for_direct_verilator_option"])

    def test_required_readiness_summary_prevents_not_ready_misread(self) -> None:
        gate = self.read_gate()
        summary = gate["required_readiness_summary"]

        self.assertEqual(summary["field_name"], "plan_resolution_readiness")
        for field in (
            "stage_plan_status",
            "verilator_option_readiness_status",
            "ready_for_direct_verilator_option",
            "not_ready_reason",
            "status_source",
        ):
            self.assertIn(field, summary["required_fields"])
        self.assertIn("direct Verilator option readiness classification", summary["outer_status_rule"])
        self.assertIn("stage_plan.status is planned", summary["ready_condition"])
        self.assertIn("ready_for_verilator_option_shim", summary["ready_condition"])
        self.assertIn("unsupported_for_stage_plan", summary["not_ready_condition"])
        self.assertIn("planned_not_ready_for_verilator_option_shim", summary["not_ready_condition"])

    def test_negative_cases_cover_unsupported_and_resident_modes(self) -> None:
        gate = self.read_gate()
        cases = gate["required_negative_cases"]

        self.assertEqual(cases["unsupported_mode"]["expected_outer_status"], "unsupported_for_stage_plan")
        self.assertFalse(cases["unsupported_mode"]["expected_ready_for_direct_verilator_option"])

        for name in ("resident_not_ready_mode", "persistent_resident_not_ready_mode"):
            with self.subTest(name=name):
                case = cases[name]
                self.assertEqual(case["expected_outer_status"], "not_ready_for_verilator_option_shim")
                self.assertEqual(case["expected_stage_plan_status"], "planned_not_ready_for_verilator_option_shim")
                self.assertEqual(
                    case["expected_verilator_option_readiness_status"],
                    "not_ready_for_verilator_option_shim",
                )
                self.assertFalse(case["expected_ready_for_direct_verilator_option"])

    def test_scope_stays_non_executing_and_no_allocation_claim(self) -> None:
        gate = self.read_gate()
        scope = gate["allowed_implementation_scope"]

        self.assertEqual(scope["module"], "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py")
        self.assertTrue(scope["in_place_helper_hardening_allowed"])
        self.assertFalse(scope["new_public_cli_allowed"])
        self.assertFalse(scope["sidecar_handoff_contract_invoked"])
        self.assertFalse(scope["command_synthesis_invoked"])
        self.assertFalse(scope["operator_plan_invoked"])
        self.assertFalse(scope["efficiency_estimate_invoked"])
        self.assertFalse(scope["new_execution_allowed"])
        self.assertFalse(scope["new_measurement_allowed"])
        self.assertFalse(scope["runtime_or_abi_change_allowed"])
        self.assertFalse(scope["source_closure_inference_allowed"])
        self.assertFalse(scope["filelist_expansion_allowed"])
        self.assertFalse(scope["automatic_gpu_allocation_allowed"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertTrue(policy["in_place_helper_hardening_allowed_by_next_gate_only"])
        self.assertFalse(policy["sidecar_handoff_contract_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["coverage_output_equivalence_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate")


if __name__ == "__main__":
    unittest.main()
