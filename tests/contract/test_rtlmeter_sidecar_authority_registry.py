import json

from tests.contract.hybrid_cli_helpers import HybridCliTestCase, REPO_ROOT


REGISTRY_PATH = "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
VEER_REGISTRY_PATH = "config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json"
VEER_EH1_REGISTRY_PATH = "config/rtlmeter_sidecar_authorities/rtlmeter_veer_eh1_default_hello.json"
VEER_EH2_REGISTRY_PATH = "config/rtlmeter_sidecar_authorities/rtlmeter_veer_eh2_default_hello.json"
VORTEX_REGISTRY_PATH = "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json"


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
        self.assertEqual(payload["status"], "blocked_sidecar_verilate_execution")
        self.assertFalse(payload["runtime_launchable"])
        self.assertIsNone(payload["runtime_launch_template"])
        self.assertEqual(payload["runner_handoff"]["status"], "implemented_thin_cli_subprocess_handoff")
        self.assertEqual(
            payload["next_required_boundary"],
            "sidecar-capable RTLMeter Verilator wrapper execution for stdout/cycles evidence",
        )
        self.assertEqual(payload["source_closure"]["status"], "complete")
        self.assertEqual(payload["source_closure"]["authority"], "reviewed_hybrid_execution_source_closure")
        self.assertEqual(payload["source_closure"]["authority_scope"], "rtlmeter_stdout_cycles_sidecar_runner")
        self.assertEqual(payload["source_closure"]["host_probe_contract_status"], "reviewed_for_rtlmeter_sidecar")
        self.assertTrue(payload["source_closure"]["review_evidence"]["reviewed"])
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
        self.assertNotIn("authority_registry.source_closure.status", invocation["missing_invocation_context"])
        self.assertNotIn("authority_registry.source_closure.authority", invocation["missing_invocation_context"])
        self.assertNotIn("authority_registry.source_closure.review_evidence", invocation["missing_invocation_context"])
        self.assertIsNone(invocation["runtime_launch_template"])
        self.assertIsNone(invocation["launcher_command_argv"])
        self.assertFalse(invocation["execution_performed"])

    def test_context_candidate_can_adopt_reviewed_registry_source_closure(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_context_candidate, build_rtlmeter_sidecar_handoff

        sidecar_contract = map_rtlmeter_case_to_sidecar_contract("Example:kind:hello")
        context = build_rtlmeter_sidecar_context_candidate(
            sidecar_contract,
            template_or_target_registry_entry=REGISTRY_PATH,
            repo_root=REPO_ROOT,
        )
        handoff = build_rtlmeter_sidecar_handoff(self._expanded_sidecar_argv(), sidecar_context=context)

        self.assertEqual(context["status"], "candidate_context_with_reviewed_source_closure")
        self.assertEqual(context["source_closure"]["status"], "complete")
        self.assertEqual(context["source_closure"]["authority"], "reviewed_hybrid_execution_source_closure")
        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_metadata_ready")
        self.assertNotIn("source_closure", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_execution_invoked"])

    def test_veer_el2_context_candidate_can_adopt_reviewed_registry_source_closure(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_context_candidate, build_rtlmeter_sidecar_handoff

        sidecar_contract = map_rtlmeter_case_to_sidecar_contract("VeeR-EL2:default:hello")
        context = build_rtlmeter_sidecar_context_candidate(
            sidecar_contract,
            source_gate_or_manifest_ref="for_codex/issues/FC-064-rtlmeter-veer-el2-design-cpu-known-closure.md",
            template_or_target_registry_entry=VEER_REGISTRY_PATH,
            repo_root=REPO_ROOT,
        )
        handoff = build_rtlmeter_sidecar_handoff(
            [
                "--cc",
                "-Mdir",
                "obj_dir",
                "--top-module",
                "tb_top",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ],
            sidecar_context=context,
        )

        self.assertEqual(context["target"], "rtlmeter_veer_el2_default_hello")
        self.assertEqual(context["status"], "candidate_context_with_reviewed_source_closure")
        self.assertEqual(context["source_closure"]["rtlmeter_case"], "VeeR-EL2:default:hello")
        self.assertEqual(context["source_closure"]["source_gate_or_manifest_ref"], "for_codex/issues/FC-064-rtlmeter-veer-el2-design-cpu-known-closure.md")
        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_metadata_ready")
        self.assertNotIn("source_closure", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_execution_invoked"])

    def test_veer_el2_registry_rejects_non_default_context(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_context_candidate

        sidecar_contract = map_rtlmeter_case_to_sidecar_contract("VeeR-EL2:hiperf:cmark")
        context = build_rtlmeter_sidecar_context_candidate(
            sidecar_contract,
            template_or_target_registry_entry=VEER_REGISTRY_PATH,
            repo_root=REPO_ROOT,
        )

        self.assertEqual(context["target"], "rtlmeter_veer_el2_hiperf_cmark")
        self.assertEqual(context["status"], "candidate_context_without_source_closure")
        self.assertEqual(context["source_closure"]["status"], "frontend_metadata_only_not_source_closure")

    def test_veer_eh_authorities_are_fail_closed_reviewed_source_closures(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_authority_registry import reviewed_registry_source_closure

        for registry_path, expected_target, expected_case in (
            (VEER_EH1_REGISTRY_PATH, "rtlmeter_veer_eh1_default_hello", "VeeR-EH1:default:hello"),
            (VEER_EH2_REGISTRY_PATH, "rtlmeter_veer_eh2_default_hello", "VeeR-EH2:default:hello"),
        ):
            payload = json.loads((REPO_ROOT / registry_path).read_text(encoding="utf-8"))
            closure = payload["source_closure"]

            self.assertEqual(payload["schema_role"], "rtlmeter_sidecar_authority")
            self.assertEqual(payload["target"], expected_target)
            self.assertEqual(payload["rtlmeter_case"], expected_case)
            self.assertFalse(payload["runtime_launchable"])
            self.assertIsNone(payload["runtime_launch_template"])
            self.assertEqual(payload["coverage_manifest"]["outputs"], ["normalized_stdout", "rtlmeter_cycles"])
            self.assertEqual(closure["authority"], "reviewed_hybrid_execution_source_closure")
            self.assertEqual(closure["authority_scope"], "rtlmeter_stdout_cycles_sidecar_runner")
            self.assertEqual(closure["runner_strategy"], "rtlmeter_stdout_cycles_direct_wrapper")
            self.assertFalse(closure["cpu_as_gpu_fallback_allowed"])
            self.assertIn("state_layout_report", closure["execution_blockers"])
            self.assertIsNotNone(
                reviewed_registry_source_closure(
                    registry_path,
                    repo_root=REPO_ROOT,
                    target=expected_target,
                    case=expected_case,
                    source_files=closure["source_files"],
                    include_files=closure["include_files"],
                    filelist_entries=closure["filelist_entries"],
                )
            )
            self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))

    def test_vortex_registry_has_reviewed_source_closure_without_execution_claim(self) -> None:
        payload = json.loads((REPO_ROOT / VORTEX_REGISTRY_PATH).read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_role"], "rtlmeter_sidecar_authority")
        self.assertEqual(payload["target"], "rtlmeter_vortex_mini_hello")
        self.assertFalse(payload["runtime_launchable"])
        self.assertIsNone(payload["runtime_launch_template"])
        self.assertEqual(payload["coverage_manifest"]["outputs"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertEqual(payload["source_closure"]["status"], "complete")
        self.assertEqual(payload["source_closure"]["authority"], "reviewed_hybrid_execution_source_closure")
        self.assertEqual(payload["source_closure"]["authority_scope"], "rtlmeter_stdout_cycles_sidecar_runner")
        self.assertEqual(payload["source_closure"]["runner_strategy"], "rtlmeter_stdout_cycles_direct_wrapper")
        self.assertEqual(payload["source_closure"]["host_probe_contract_status"], "reviewed_for_rtlmeter_sidecar")
        self.assertEqual(payload["source_closure"]["observables"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertTrue(payload["source_closure"]["review_evidence"]["reviewed"])
        self.assertFalse(payload["source_closure"]["cpu_as_gpu_fallback_allowed"])
        self.assertIn(
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            payload["source_closure"]["execution_blockers"],
        )
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))

    def test_vortex_context_candidate_can_adopt_reviewed_registry_source_closure(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_context_candidate, build_rtlmeter_sidecar_handoff

        sidecar_contract = map_rtlmeter_case_to_sidecar_contract("Vortex:mini:hello")
        context = build_rtlmeter_sidecar_context_candidate(
            sidecar_contract,
            source_gate_or_manifest_ref="reports/rtlmeter_vortex_first_gate_readiness.json",
            template_or_target_registry_entry=VORTEX_REGISTRY_PATH,
            repo_root=REPO_ROOT,
        )
        handoff = build_rtlmeter_sidecar_handoff(
            [
                "--cc",
                "-Mdir",
                "obj_dir",
                "--top-module",
                "tb",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "1",
                "--sim-accel-steps",
                "1",
            ],
            sidecar_context=context,
        )

        self.assertEqual(context["target"], "rtlmeter_vortex_mini_hello")
        self.assertEqual(context["status"], "candidate_context_with_reviewed_source_closure")
        self.assertEqual(context["source_closure"]["rtlmeter_case"], "Vortex:mini:hello")
        self.assertEqual(context["source_closure"]["source_gate_or_manifest_ref"], "reports/rtlmeter_vortex_first_gate_readiness.json")
        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_metadata_ready")
        self.assertNotIn("source_closure", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_execution_invoked"])
