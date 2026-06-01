import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterSidecarContractMappingTest(HybridCliTestCase):
    def test_maps_command_capture_to_frontend_owned_sidecar_metadata(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract

        mapping = map_rtlmeter_case_to_sidecar_contract(
            "Example:kind:hello",
            compile_args=("--use-gpu",),
        )

        self.assertEqual(mapping["surface"], "rtlmeter_sidecar_contract_mapping")
        self.assertEqual(mapping["status"], "frontend_metadata_mapped_sidecar_unresolved")
        self.assertEqual(mapping["frontend"], "rtlmeter/verilator")
        self.assertFalse(mapping["runtime_abi"])
        self.assertFalse(mapping["execution_authority"])
        self.assertFalse(mapping["requires_rtlmeter_launch_template"])
        self.assertEqual(mapping["correctness_policy_ref"], "coverage_output_equivalence")
        self.assertEqual(mapping["correctness_policy_ref_status"], "reference_only_not_compare_evidence")

        metadata = mapping["frontend_owned_build_metadata"]
        self.assertEqual(metadata["top_module"], "top")
        self.assertEqual(metadata["main_clock"], "top.clk")
        self.assertIn("verilogSourceFiles/top.v", metadata["filelist_entries"])
        self.assertIn("rtl/__rtlmeter_utils.sv", metadata["verilog_source_files"])
        self.assertIn("--use-gpu", metadata["extra_args"])
        self.assertIn("--use-gpu", metadata["verilator_command_argv"])

        self.assertIn("GPU build artifacts", mapping["sidecar_owned_responsibilities"])
        self.assertIn("coverage-output selection", mapping["sidecar_owned_responsibilities"])
        self.assertIn("generated compare reports", mapping["sidecar_owned_responsibilities"])
        self.assert_no_local_absolute_paths(json.dumps(mapping, sort_keys=True))

    def test_rejects_wrong_surface_and_prepopulated_sidecar_fields(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import (
            RtlmeterSidecarContractMappingError,
            map_rtlmeter_capture_to_sidecar_contract,
        )
        from rtlmeter_verilator_command_capture import capture_rtlmeter_verilator_command

        with self.assertRaisesRegex(RtlmeterSidecarContractMappingError, "surface"):
            map_rtlmeter_capture_to_sidecar_contract({"surface": "wrong"})

        capture = capture_rtlmeter_verilator_command("Example:kind:hello")
        capture["generated_reports"] = ["reports/should_not_be_here.json"]
        with self.assertRaisesRegex(RtlmeterSidecarContractMappingError, "sidecar-owned"):
            map_rtlmeter_capture_to_sidecar_contract(capture)
