import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase, REPO_ROOT


REGISTRY_PATH = "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"


class RtlmeterStdoutCyclesRunnerContractTest(HybridCliTestCase):
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

    def _reviewed_source_closure(self, target: str = "rtlmeter_example_kind_hello") -> dict[str, object]:
        return {
            "status": "complete",
            "authority": "reviewed_hybrid_execution_source_closure",
            "authority_scope": "rtlmeter_stdout_cycles_sidecar_runner",
            "target": target,
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

    def _complete_context(self, entry: str = REGISTRY_PATH) -> dict[str, object]:
        return {
            "target": "rtlmeter_example_kind_hello",
            "mode": "rtlmeter_first_seed",
            "template_or_target_registry_entry": entry,
            "source_gate_or_manifest_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            "host_probe_metadata": {"clock_field": "top__DOT__clk", "reset_field": "none"},
            "coverage_output_target": "rtlmeter_stdout_and_cycles_equivalence",
            "coverage_manifest": {"outputs": ["normalized_stdout", "rtlmeter_cycles"]},
            "state_and_report_path_rules": {"root": "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"},
            "compare_labels": {"cpu": "rtlmeter_cpu", "gpu": "rtlmeter_sidecar_candidate"},
            "source_closure": self._reviewed_source_closure(),
        }

    def _complete_authority_registry(self, target: str = "rtlmeter_example_kind_hello") -> dict[str, object]:
        return {
            "schema_role": "rtlmeter_sidecar_authority",
            "runtime_launchable": False,
            "target": target,
            "source_closure": self._reviewed_source_closure(target),
        }

    def _contract(self, *, authority_registry: dict[str, object] | None = None, runner_ready: bool = False):
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_runner_contract import build_rtlmeter_stdout_cycles_runner_contract

        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv(),
            sidecar_context=self._complete_context(),
        )
        return build_rtlmeter_stdout_cycles_runner_contract(
            stdout_cycles_plan=build_rtlmeter_stdout_cycles_execution_plan(),
            handoff_metadata=handoff,
            authority_registry=authority_registry or self._complete_authority_registry(),
            runner_implementation_ready=runner_ready,
        )

    def test_contract_blocks_only_on_missing_runner_implementation(self) -> None:
        contract = self._contract()

        self.assertEqual(contract["surface"], "rtlmeter_stdout_cycles_runner_contract")
        self.assertEqual(contract["status"], "rtlmeter_stdout_cycles_runner_contract_blocked")
        self.assertEqual(contract["missing_runner_context"], ["rtlmeter_stdout_cycles_runner_implementation"])
        self.assertEqual(contract["observables"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertTrue(contract["acceptance_policy"]["normalized_stdout_match"])
        self.assertTrue(contract["acceptance_policy"]["cycle_count_match"])
        self.assertFalse(contract["acceptance_policy"]["raw_state_equality_required"])
        self.assertEqual(contract["gpu_candidate"]["owner"], "sidecar")
        self.assertEqual(contract["gpu_candidate"]["fallback_policy"], "forbidden")
        self.assertFalse(contract["gpu_candidate"]["cpu_as_gpu_fallback_allowed"])
        self.assertFalse(contract["uses_run_hybrid_template"])
        self.assertFalse(contract["requires_runtime_launch_template"])
        self.assertFalse(contract["run_hybrid_template_compatible"])
        self.assertIsNone(contract["launcher_command_argv"])
        self.assertIsNone(contract["runner_command_argv"])
        self.assertEqual(contract["runner_command_role"], "not_materialized")
        self.assertFalse(contract["execution_authority"])
        self.assertFalse(contract["runtime_abi"])
        self.assertFalse(contract["sidecar_runner_invoked"])
        self.assertFalse(contract["sidecar_execution_invoked"])
        self.assertFalse(contract["execution_performed"])
        self.assertFalse(contract["measurement_performed"])
        self.assertFalse(contract["cpu_as_gpu_fallback"])

    def test_metadata_only_tracked_registry_stays_blocked(self) -> None:
        authority_registry = json.loads((REPO_ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
        contract = self._contract(authority_registry=authority_registry)

        self.assertEqual(contract["status"], "rtlmeter_stdout_cycles_runner_contract_blocked")
        self.assertEqual(contract["authority_registry_entry"], REGISTRY_PATH)
        self.assertIn("authority_registry.source_closure.status", contract["missing_runner_context"])
        self.assertIn("authority_registry.source_closure.authority", contract["missing_runner_context"])
        self.assertIn("rtlmeter_stdout_cycles_runner_implementation", contract["missing_runner_context"])
        self.assertFalse(contract["execution_performed"])
        self.assertFalse(contract["measurement_performed"])

    def test_thin_complete_source_closure_is_not_enough(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_runner_contract import build_rtlmeter_stdout_cycles_runner_contract

        context = self._complete_context()
        context["source_closure"] = {
            "status": "complete",
            "authority": "reviewed_hybrid_execution_source_closure",
        }
        handoff = build_rtlmeter_sidecar_handoff(
            self._expanded_sidecar_argv(),
            sidecar_context=context,
        )
        contract = build_rtlmeter_stdout_cycles_runner_contract(
            stdout_cycles_plan=build_rtlmeter_stdout_cycles_execution_plan(),
            handoff_metadata=handoff,
            authority_registry=self._complete_authority_registry(),
            runner_implementation_ready=True,
        )

        self.assertEqual(contract["status"], "rtlmeter_stdout_cycles_runner_contract_blocked")
        self.assertIn("handoff_metadata_ready", contract["missing_runner_context"])
        self.assertIn("sidecar_context.source_closure.authority_scope", contract["missing_runner_context"])
        self.assertIn("sidecar_context.source_closure.rtlmeter_case", contract["missing_runner_context"])
        self.assertFalse(contract["sidecar_execution_invoked"])

    def test_reviewed_template_does_not_make_contract_run_hybrid_template_based(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff, build_rtlmeter_sidecar_launcher_invocation
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_runner_contract import build_rtlmeter_stdout_cycles_runner_contract

        template_payload = {
            "target": "rtlmeter_example_kind_hello",
            "template_execution_role": "runnable_hybrid_template",
            "source_closure": self._reviewed_source_closure(),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "config/slice_launch_templates/rtlmeter_example_kind_hello.json"
            template.parent.mkdir(parents=True)
            template.write_text(json.dumps(template_payload), encoding="utf-8")
            context = self._complete_context("config/slice_launch_templates/rtlmeter_example_kind_hello.json")
            handoff = build_rtlmeter_sidecar_handoff(self._expanded_sidecar_argv(), sidecar_context=context)
            invocation = build_rtlmeter_sidecar_launcher_invocation(handoff, repo_root=root)
            contract = build_rtlmeter_stdout_cycles_runner_contract(
                stdout_cycles_plan=build_rtlmeter_stdout_cycles_execution_plan(),
                handoff_metadata=handoff,
                authority_registry=self._complete_authority_registry(),
                runner_implementation_ready=True,
            )

        self.assertIsNotNone(invocation["launcher_command_argv"])
        self.assertEqual(contract["status"], "rtlmeter_stdout_cycles_runner_contract_ready")
        self.assertFalse(contract["uses_run_hybrid_template"])
        self.assertFalse(contract["run_hybrid_template_compatible"])
        self.assertIsNone(contract["launcher_command_argv"])
        self.assertIsNone(contract["runner_command_argv"])
        self.assertIn("src/tools/run_hybrid_template.py", contract["rejected_execution_paths"])

    def test_authority_registry_target_must_match_handoff_target(self) -> None:
        wrong_registry = self._complete_authority_registry("wrong_target")
        contract = self._contract(authority_registry=wrong_registry, runner_ready=True)

        self.assertEqual(contract["status"], "rtlmeter_stdout_cycles_runner_contract_blocked")
        self.assertIn("authority_registry.target_match", contract["missing_runner_context"])
        self.assertIn("authority_registry.source_closure.target_match", contract["missing_runner_context"])
        self.assertFalse(contract["sidecar_execution_invoked"])
