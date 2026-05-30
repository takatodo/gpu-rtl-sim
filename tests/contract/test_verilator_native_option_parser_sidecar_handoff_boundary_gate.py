import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json"
)


class VerilatorNativeOptionParserSidecarHandoffBoundaryGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_definition_selects_adapter_boundary_before_existing_sidecar_plan(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_run_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_handoff_boundary_gate",
        )

        decision = gate["definition_decision"]
        self.assertEqual(decision["selected_surface"], "native_parser_values_to_sidecar_plan_adapter_boundary")
        self.assertIn("V3Options values", decision["weakest_point"])

        boundary = gate["handoff_boundary"]
        self.assertEqual(
            boundary["selected_contract"],
            "native_parser_adapter_payload_before_existing_sidecar_stage_plan",
        )
        self.assertIn("src/tools/hybrid_benchmark_sidecar_plan.py", boundary["contract_modules"])
        self.assertIn("src/tools/hybrid_benchmark_sidecar_operator.py", boundary["contract_modules"])
        self.assertTrue(boundary["adapter_not_implemented_by_this_gate"])
        self.assertEqual(boundary["correctness_policy"], "coverage_output_equivalence")

    def test_definition_separates_parser_fields_from_sidecar_owned_work(self) -> None:
        gate = self.read_gate()
        inputs = gate["native_parser_inputs"]
        boundary = gate["handoff_boundary"]

        self.assertEqual(inputs["accepted_accelerator"], "sidecar-gpu")
        self.assertEqual(
            inputs["parser_field_candidates"],
            ["V3Options::simAccel()", "V3Options::simAccelStates()", "V3Options::simAccelSteps()"],
        )
        self.assertIn("--sim-accel-shape <NxS>", inputs["parser_input_non_goals"])
        self.assertIn("--sim-accel-estimate-efficiency", inputs["parser_input_non_goals"])

        self.assertEqual(
            boundary["minimum_parser_owned_fields"],
            ["accelerator_mode", "state_count", "step_count", "shape", "ordinary_verilator_args"],
        )
        for field in ("mdir", "top_module", "source_files", "filelists", "defines", "include_dirs", "warning_flags"):
            self.assertIn(field, boundary["minimum_preserved_verilator_build_fields"])
        for adapter_field in (
            "schema_version",
            "accelerator_mode",
            "state_count",
            "step_count",
            "ordinary_verilator_args",
            "source_files",
            "filelists",
            "correctness_policy",
            "non_claims",
        ):
            self.assertIn(adapter_field, boundary["minimum_adapter_payload_fields"])
        for sidecar_field in (
            "state_authority",
            "init_state_path_or_rule",
            "reference_dump_path_or_rule",
            "candidate_dump_path_or_rule",
            "compare_report_path_or_rule",
            "coverage_output_target",
        ):
            self.assertIn(sidecar_field, boundary["minimum_sidecar_owned_fields_referenced_not_populated_by_parser"])
        for forbidden in (
            "source closure expansion",
            "filelist dependency inference",
            "coverage manifest selection",
            "hybrid sidecar execution",
            "automatic GPU allocation",
        ):
            self.assertIn(forbidden, boundary["forbidden_parser_work"])

    def test_definition_selects_review_without_execution_or_claim_expansion(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(next_gate["name"], "review_verilator_native_option_parser_sidecar_handoff_boundary_gate")
        self.assertIn(
            "whether the minimum parser-owned and preserved Verilator build fields are sufficient",
            next_gate["must_decide"],
        )
        self.assertIn("sidecar runtime or ABI integration", next_gate["must_not_claim"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertTrue(policy["handoff_boundary_defined"])
        self.assertFalse(policy["adapter_implemented_by_this_gate"])
        self.assertFalse(policy["sidecar_handoff_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["new_execution_allowed_by_this_gate"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertEqual(gate["next_task"], "review_verilator_native_option_parser_sidecar_handoff_boundary_gate")


if __name__ == "__main__":
    unittest.main()
