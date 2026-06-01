from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterCpuGpuComparePolicyTest(HybridCliTestCase):
    def test_first_seed_compare_policy_preserves_rtlmeter_metrics(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_policy import rtlmeter_cpu_gpu_compare_policy

        policy = rtlmeter_cpu_gpu_compare_policy()

        self.assertEqual(policy["surface"], "rtlmeter_cpu_gpu_compare_policy")
        self.assertEqual(policy["status"], "policy_defined_not_executed")
        self.assertEqual(policy["seed"], "Example:kind:hello")
        self.assertEqual(policy["compile_args"], "--use-gpu")
        self.assertEqual(policy["policy_scope"], "policy_only_not_execution_integration")
        self.assertFalse(policy["canonical_project_state_changed"])
        self.assertFalse(policy["policy_is_source_of_truth"])
        self.assertEqual(policy["cpu_execution_owner"], "rtlmeter")
        self.assertEqual(policy["gpu_execution_owner"], "sidecar")
        self.assertEqual(policy["frontend_metadata_source"], "rtlmeter_sidecar_contract_mapping")
        self.assertTrue(policy["rtlmeter_metrics_preserved"])
        self.assertFalse(policy["rtlmeter_timing_conflated_with_sidecar_timing"])
        self.assertFalse(policy["generated_report_is_source_of_truth"])
        self.assertEqual(
            policy["generated_report_path_rule"],
            "reports/rtlmeter_example_kind_hello_cpu_gpu_compare.json",
        )
        self.assertEqual(policy["report_schema_role"], "rtlmeter_cpu_gpu_compare_report")
        self.assertEqual(policy["report_generation_status"], "planned_not_implemented")
        self.assertIn("--compileArgs", policy["report_regeneration_command"])
        self.assertIn("--use-gpu", policy["report_regeneration_command"])
        self.assertIn("normalized stdout transcript", policy["compare_policy"]["required_matches"])
        self.assertIn("GPU kernel timing", policy["compare_policy"]["diagnostic_only"])

    def test_seed_is_explicitly_parameterized(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_policy import rtlmeter_cpu_gpu_compare_policy

        policy = rtlmeter_cpu_gpu_compare_policy(
            "OtherDesign:cfg:test",
            compile_args="--sim-accel sidecar-gpu --sim-accel-states 8 --sim-accel-steps 1",
        )

        self.assertEqual(policy["seed"], "OtherDesign:cfg:test")
        self.assertEqual(
            policy["generated_report_path_rule"],
            "reports/rtlmeter_otherdesign_cfg_test_cpu_gpu_compare.json",
        )
        self.assertIn("OtherDesign:cfg:test", policy["report_regeneration_command"])
        self.assertIn("--sim-accel sidecar-gpu", policy["report_regeneration_command"])

    def test_policy_does_not_claim_execution_or_speedup(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_policy import rtlmeter_cpu_gpu_compare_policy

        policy = rtlmeter_cpu_gpu_compare_policy()
        non_claims = " ".join(policy["non_claims"])

        self.assertIn("does not run RTLMeter", non_claims)
        self.assertIn("does not run GPU sidecar execution", non_claims)
        self.assertIn("does not create a compare report", non_claims)
        self.assertIn("planned documentation", non_claims)
        self.assertIn("does not claim speedup", non_claims)
