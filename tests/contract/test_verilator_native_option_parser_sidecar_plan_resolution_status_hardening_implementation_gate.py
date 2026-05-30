import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json"
)


class VerilatorNativeOptionParserSidecarPlanResolutionStatusHardeningImplementationGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_gate_records_in_place_helper_hardening(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate",
        )
        surface = gate["implemented_surface"]
        self.assertEqual(surface["module"], "src/tools/verilator_native_option_parser_sidecar_plan_resolution.py")
        self.assertEqual(surface["helper_added"], "_plan_resolution_readiness")
        self.assertTrue(surface["outer_status_is_readiness_classification"])
        self.assertTrue(surface["nested_stage_plan_status_preserved"])
        self.assertTrue(surface["plan_resolution_readiness_added"])
        self.assertFalse(surface["sidecar_handoff_contract_invoked"])
        self.assertFalse(surface["command_synthesis_invoked"])
        self.assertFalse(surface["new_execution_added"])
        self.assertFalse(surface["new_measurement_added"])

    def test_gate_records_status_mapping(self) -> None:
        gate = self.read_gate()
        mapping = gate["implemented_status_mapping"]

        ready = mapping["stage_plan_planned_with_ready_readiness"]
        self.assertEqual(ready["outer_status"], "ready_for_verilator_option_shim")
        self.assertTrue(ready["ready_for_direct_verilator_option"])

        resident = mapping["stage_plan_planned_not_ready_for_verilator_option_shim"]
        self.assertEqual(resident["outer_status"], "not_ready_for_verilator_option_shim")
        self.assertEqual(resident["preserved_stage_plan_status"], "planned_not_ready_for_verilator_option_shim")
        self.assertFalse(resident["ready_for_direct_verilator_option"])

        unsupported = mapping["stage_plan_unsupported_for_stage_plan"]
        self.assertEqual(unsupported["outer_status"], "unsupported_for_stage_plan")
        self.assertEqual(unsupported["preserved_stage_plan_status"], "unsupported_for_stage_plan")
        self.assertFalse(unsupported["ready_for_direct_verilator_option"])

    def test_gate_records_readiness_contract_and_focused_tests(self) -> None:
        gate = self.read_gate()
        readiness = gate["plan_resolution_readiness_contract"]

        self.assertEqual(readiness["field"], "plan_resolution_readiness")
        for field in (
            "stage_plan_status",
            "verilator_option_readiness_status",
            "ready_for_direct_verilator_option",
            "not_ready_reason",
            "status_source",
            "missing_readiness_inputs",
        ):
            self.assertIn(field, readiness["fields"])
        self.assertIn("readiness only", readiness["readiness_only_non_claim"])

        self.assertEqual(
            gate["verification"]["focused_contract_test_command"],
            "python3 -m unittest tests.contract.test_verilator_native_option_parser_sidecar_plan_resolution_fixture -q",
        )
        self.assertEqual(gate["verification"]["focused_contract_test_exit_code"], 0)
        self.assertEqual(gate["verification"]["focused_contract_test_count"], 9)

    def test_gate_selects_review_and_keeps_non_claims(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate",
        )
        self.assertIn("whether plan_resolution_readiness makes not-ready and unsupported cases unambiguous", next_gate["must_decide"])
        for forbidden in (
            "sidecar_handoff_contract from native parser payload",
            "command synthesis from native parser payload",
            "RTL simulation execution",
            "coverage-output equivalence for a native-parser flow",
            "automatic optimal GPU allocation",
        ):
            self.assertIn(forbidden, next_gate["must_not_claim"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["implementation_only"])
        self.assertFalse(policy["new_public_cli_allowed_by_this_gate"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["sidecar_handoff_contract_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["command_synthesis_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["automatic_optimal_gpu_allocation_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate")


if __name__ == "__main__":
    unittest.main()
