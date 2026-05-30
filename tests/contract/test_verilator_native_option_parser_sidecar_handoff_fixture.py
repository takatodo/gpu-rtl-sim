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
    / "implement_verilator_native_option_parser_sidecar_handoff_fixture_gate.json"
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


class VerilatorNativeOptionParserSidecarHandoffFixtureTest(unittest.TestCase):
    def test_implementation_gate_records_non_executing_fixture_scope(self) -> None:
        import json

        gate = json.loads(IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate",
        )
        implemented = gate["implemented_surface"]
        self.assertEqual(implemented["module"], "src/tools/verilator_native_option_parser_sidecar_handoff.py")
        self.assertEqual(
            implemented["primary_entrypoint_function"],
            "native_parser_values_to_sidecar_adapter_payload",
        )
        self.assertFalse(implemented["sidecar_stage_plan_invoked"])
        self.assertFalse(implemented["sidecar_handoff_contract_invoked"])
        self.assertFalse(gate["acceptance_policy"]["new_execution_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["coverage_output_equivalence_claim_allowed_by_gate_alone"])

    def test_adapter_preserves_parser_owned_fields_without_expansion(self) -> None:
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
                "-Irtl/include",
                "+incdir+common",
                "-Wall",
                "rtl/top.sv",
                "--ordinary-extra",
            ]
        )

        payload = sidecar_handoff.native_parser_values_to_sidecar_adapter_payload(parser_values)

        self.assertEqual(tuple(payload), sidecar_handoff.ADAPTER_PAYLOAD_FIELDS)
        self.assertEqual(payload["surface"], "native_verilator_parser_sidecar_handoff_fixture")
        self.assertEqual(payload["adapter_source_surface"], parser_values["surface"])
        self.assertEqual(payload["accelerator_mode"], "sidecar-gpu")
        self.assertEqual(payload["state_count"], 64)
        self.assertEqual(payload["step_count"], 1)
        self.assertEqual(payload["shape"], "64x1")
        self.assertEqual(payload["mdir"], "artifacts/example_obj_dir")
        self.assertEqual(payload["top_module"], "example_top")
        self.assertEqual(payload["source_files"], ["rtl/top.sv"])
        self.assertEqual(payload["filelists"], ["rtl/files.f"])
        self.assertIn("-DTRACE=1", payload["defines"])
        self.assertEqual(payload["include_dirs"], ["include", "-Irtl/include", "+incdir+common"])
        self.assertEqual(payload["warning_flags"], ["-Wall"])
        self.assertIn("--ordinary-extra", payload["ordinary_verilator_args"])

    def test_adapter_does_not_populate_sidecar_owned_resolved_fields(self) -> None:
        (sidecar_handoff,) = _load_tool_modules(
            "verilator_native_option_parser_sidecar_handoff",
        )

        payload = sidecar_handoff.parse_verilator_native_option_sidecar_handoff(
            [
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "2",
                "--sim-accel-steps",
                "3",
                "rtl/top.sv",
            ]
        )

        self.assertFalse(sidecar_handoff.FORBIDDEN_RESOLVED_SIDECAR_FIELDS.intersection(payload))
        self.assertEqual(payload["correctness_policy_ref"], "coverage_output_equivalence")
        self.assertEqual(
            payload["correctness_policy_reference_status"],
            "adapter_default_reference_only_not_parser_populated_compare_evidence",
        )
        self.assertEqual(payload["sidecar_owned_resolution_status"], "unresolved_by_native_parser_adapter_fixture")
        self.assertNotIn("correctness_policy", payload)
        self.assertIn("coverage output target", payload["unresolved_sidecar_responsibilities"])
        self.assertIn("host-probe metadata", payload["unresolved_sidecar_responsibilities"])
        self.assertIn("compare labels", payload["unresolved_sidecar_responsibilities"])

    def test_adapter_rejects_parser_values_that_already_contain_sidecar_outputs(self) -> None:
        sidecar_handoff, parser_stub = _load_tool_modules(
            "verilator_native_option_parser_sidecar_handoff",
            "verilator_native_option_parser_stub_fixture",
        )

        parser_values = parser_stub.parse_verilator_native_option_stub(
            [
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "1",
                "--sim-accel-steps",
                "1",
            ]
        )
        parser_values["state_files"] = {"init_state": "artifacts/init.bin"}

        with self.assertRaises(sidecar_handoff.NativeParserSidecarHandoffError):
            sidecar_handoff.native_parser_values_to_sidecar_adapter_payload(parser_values)


if __name__ == "__main__":
    unittest.main()
