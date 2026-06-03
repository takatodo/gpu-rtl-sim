import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase, REPO_ROOT


REGISTRY_PATH = "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"


class RtlmeterSidecarAuthorityRegistryTest(HybridCliTestCase):
    def _expanded_sidecar_argv(self) -> list[str]:
        return [
            "--cc",
            "-Mdir",
            "obj_dir",
            "--top-module",
            "top",
            "-f",
            "filelist",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
        ]

    def _reviewed_source_closure(self) -> dict[str, object]:
        return {
            "status": "complete",
            "authority": "reviewed_hybrid_execution_source_closure",
            "authority_scope": "rtlmeter_stdout_cycles_sidecar_runner",
            "target": "rtlmeter_example_kind_hello",
            "mode": "rtlmeter_first_seed",
            "rtlmeter_case": "Example:kind:hello",
            "source_gate_or_manifest_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            "source_files": [
                "third_party/rtlmeter/designs/Example/src/top.v",
                "third_party/rtlmeter/rtl/__rtlmeter_utils.sv",
            ],
            "include_files": ["third_party/rtlmeter/rtl/__rtlmeter_top_include.vh"],
            "filelist_entries": [
                "verilogSourceFiles/top.v",
                "rtl/__rtlmeter_utils.sv",
                "rtl/__rtlmeter_top_include.vh",
            ],
            "observables": ["normalized_stdout", "rtlmeter_cycles"],
            "runner_strategy": "rtlmeter_stdout_cycles_direct_wrapper",
            "host_probe_contract_status": "reviewed_for_rtlmeter_sidecar",
            "cpu_as_gpu_fallback_allowed": False,
            "review_evidence": {
                "reviewed": True,
                "review_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            },
        }

    def _complete_context_for_registry(self) -> dict[str, object]:
        return {
            "target": "rtlmeter_example_kind_hello",
            "mode": "rtlmeter_first_seed",
            "template_or_target_registry_entry": REGISTRY_PATH,
            "source_gate_or_manifest_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            "host_probe_metadata": {"clock_field": "top__DOT__clk", "reset_field": "none"},
            "coverage_output_target": "rtlmeter_stdout_and_cycles_equivalence",
            "coverage_manifest": {"outputs": ["normalized_stdout", "rtlmeter_cycles"]},
            "state_and_report_path_rules": {"root": "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"},
            "compare_labels": {"cpu": "rtlmeter_cpu", "gpu": "rtlmeter_sidecar_candidate"},
            "source_closure": self._reviewed_source_closure(),
        }

    def test_registry_is_metadata_only_and_path_clean(self) -> None:
        payload = json.loads((REPO_ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_role"], "rtlmeter_sidecar_authority")
        self.assertFalse(payload["runtime_launchable"])
        self.assertIsNone(payload["runtime_launch_template"])
        self.assertEqual(payload["source_closure"]["status"], "frontend_metadata_only_not_source_closure")
        self.assertNotIn("authority", payload["source_closure"])
        self.assertEqual(
            payload["source_closure"]["required_authority"],
            "reviewed_hybrid_execution_source_closure",
        )
        self.assertEqual(payload["source_closure"]["authority_scope"], "rtlmeter_stdout_cycles_sidecar_runner")
        self.assertFalse(payload["source_closure"]["cpu_as_gpu_fallback_allowed"])
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))

    def test_registry_blocks_launcher_materialization_until_runtime_template_exists(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import (
            build_rtlmeter_sidecar_handoff,
            build_rtlmeter_sidecar_launcher_invocation,
        )

        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv(),
            sidecar_context=self._complete_context_for_registry(),
        )
        invocation = build_rtlmeter_sidecar_launcher_invocation(handoff, repo_root=REPO_ROOT)

        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_metadata_ready")
        self.assertEqual(invocation["status"], "rtlmeter_sidecar_launcher_invocation_blocked")
        self.assertEqual(invocation["authority_registry_entry"], REGISTRY_PATH)
        self.assertIn("runtime_launch_template", invocation["missing_invocation_context"])
        self.assertIn("authority_registry.source_closure.status", invocation["missing_invocation_context"])
        self.assertIn("authority_registry.source_closure.authority", invocation["missing_invocation_context"])
        self.assertIn("authority_registry.source_closure.host_probe_contract_status", invocation["missing_invocation_context"])
        self.assertIn("authority_registry.source_closure.review_evidence", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["runtime_launch_template"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["execution_performed"])
