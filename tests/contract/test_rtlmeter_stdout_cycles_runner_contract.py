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

    def _implementation_boundary(self) -> dict[str, object]:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_runner_adapter import (
            build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata,
        )
        from rtlmeter_stdout_cycles_runner_implementation import (
            build_rtlmeter_stdout_cycles_runner_implementation_boundary,
        )

        return build_rtlmeter_stdout_cycles_runner_implementation_boundary(
            runner_contract=self._contract(),
            runner_adapter_entrypoint_metadata=build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata(),
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

    def test_implementation_boundary_waits_for_adapter_without_materializing_command(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_runner_implementation import (
            build_rtlmeter_stdout_cycles_runner_implementation_boundary,
        )

        boundary = build_rtlmeter_stdout_cycles_runner_implementation_boundary(
            runner_contract=self._contract(),
        )

        self.assertEqual(boundary["surface"], "rtlmeter_stdout_cycles_runner_implementation")
        self.assertEqual(boundary["status"], "rtlmeter_stdout_cycles_runner_implementation_blocked_missing_adapter")
        self.assertEqual(boundary["missing_implementation_context"], ["runner_adapter_entrypoint"])
        self.assertEqual(boundary["observables"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertTrue(boundary["acceptance_policy"]["normalized_stdout_match"])
        self.assertTrue(boundary["acceptance_policy"]["cycle_count_match"])
        self.assertFalse(boundary["acceptance_policy"]["raw_state_equality_required"])
        self.assertFalse(boundary["uses_run_hybrid_template"])
        self.assertFalse(boundary["requires_runtime_launch_template"])
        self.assertFalse(boundary["run_hybrid_template_compatible"])
        self.assertIsNone(boundary["launcher_command_argv"])
        self.assertIsNone(boundary["runner_command_argv"])
        self.assertEqual(boundary["runner_command_role"], "not_materialized")
        self.assertFalse(boundary["execution_authority"])
        self.assertFalse(boundary["runtime_abi"])
        self.assertFalse(boundary["sidecar_runner_invoked"])
        self.assertFalse(boundary["sidecar_execution_invoked"])
        self.assertFalse(boundary["coverage_output_compare_reached"])
        self.assertFalse(boundary["execution_performed"])
        self.assertFalse(boundary["measurement_performed"])
        self.assertFalse(boundary["cpu_as_gpu_fallback"])

    def test_implementation_boundary_keeps_unready_contract_blocked(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_runner_implementation import (
            build_rtlmeter_stdout_cycles_runner_implementation_boundary,
        )

        authority_registry = json.loads((REPO_ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
        boundary = build_rtlmeter_stdout_cycles_runner_implementation_boundary(
            runner_contract=self._contract(authority_registry=authority_registry),
        )

        self.assertEqual(boundary["status"], "rtlmeter_stdout_cycles_runner_implementation_blocked_contract")
        self.assertIn("runner_contract_missing_context", boundary["missing_implementation_context"])
        self.assertIn(
            "runner_contract.authority_registry.source_closure.status",
            boundary["missing_implementation_context"],
        )
        self.assertIn(
            "runner_contract.rtlmeter_stdout_cycles_runner_implementation",
            boundary["missing_implementation_context"],
        )
        self.assertIsNone(boundary["runner_command_argv"])
        self.assertEqual(boundary["runner_command_role"], "not_materialized")
        self.assertFalse(boundary["execution_performed"])
        self.assertFalse(boundary["measurement_performed"])
        self.assertFalse(boundary["sidecar_execution_invoked"])

    def test_adapter_entrypoint_metadata_is_descriptive_only(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_runner_adapter import (
            build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata,
        )

        adapter_metadata = build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata()

        self.assertEqual(adapter_metadata["surface"], "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata")
        self.assertEqual(adapter_metadata["status"], "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata_ready")
        self.assertEqual(
            adapter_metadata["runner_adapter_entrypoint"],
            "rtlmeter_stdout_cycles_sidecar_runner_entrypoint",
        )
        self.assertEqual(
            adapter_metadata["runner_adapter_entrypoint_role"],
            "declared_future_entrypoint_not_materialized",
        )
        self.assertEqual(adapter_metadata["outputs"]["observables"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertTrue(adapter_metadata["acceptance_policy"]["normalized_stdout_match"])
        self.assertTrue(adapter_metadata["acceptance_policy"]["cycle_count_match"])
        self.assertFalse(adapter_metadata["acceptance_policy"]["raw_state_equality_required"])
        self.assertFalse(adapter_metadata["uses_run_hybrid_template"])
        self.assertFalse(adapter_metadata["requires_runtime_launch_template"])
        self.assertFalse(adapter_metadata["run_hybrid_template_compatible"])
        self.assertIsNone(adapter_metadata["launcher_command_argv"])
        self.assertIsNone(adapter_metadata["runner_command_argv"])
        self.assertEqual(adapter_metadata["runner_command_role"], "not_materialized")
        self.assertFalse(adapter_metadata["execution_authority"])
        self.assertFalse(adapter_metadata["runtime_abi"])
        self.assertFalse(adapter_metadata["adapter_invoked"])
        self.assertFalse(adapter_metadata["sidecar_runner_invoked"])
        self.assertFalse(adapter_metadata["sidecar_execution_invoked"])
        self.assertFalse(adapter_metadata["coverage_output_compare_reached"])
        self.assertFalse(adapter_metadata["execution_performed"])
        self.assertFalse(adapter_metadata["measurement_performed"])
        self.assertFalse(adapter_metadata["cpu_as_gpu_fallback"])

    def test_implementation_boundary_accepts_adapter_metadata_without_materializing_command(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_runner_adapter import (
            build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata,
        )
        from rtlmeter_stdout_cycles_runner_implementation import (
            build_rtlmeter_stdout_cycles_runner_implementation_boundary,
        )

        adapter_metadata = build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata()
        boundary = build_rtlmeter_stdout_cycles_runner_implementation_boundary(
            runner_contract=self._contract(),
            runner_adapter_entrypoint_metadata=adapter_metadata,
        )

        self.assertEqual(
            boundary["status"],
            "rtlmeter_stdout_cycles_runner_implementation_adapter_entrypoint_metadata_ready",
        )
        self.assertEqual(boundary["missing_implementation_context"], [])
        self.assertEqual(
            boundary["runner_adapter_entrypoint"],
            "rtlmeter_stdout_cycles_sidecar_runner_entrypoint",
        )
        self.assertEqual(boundary["runner_adapter_entrypoint_metadata"], adapter_metadata)
        self.assertIsNone(boundary["launcher_command_argv"])
        self.assertIsNone(boundary["runner_command_argv"])
        self.assertEqual(boundary["runner_command_role"], "not_materialized")
        self.assertFalse(boundary["execution_authority"])
        self.assertFalse(boundary["runtime_abi"])
        self.assertFalse(boundary["sidecar_runner_invoked"])
        self.assertFalse(boundary["sidecar_execution_invoked"])
        self.assertFalse(boundary["coverage_output_compare_reached"])
        self.assertFalse(boundary["execution_performed"])
        self.assertFalse(boundary["measurement_performed"])
        self.assertFalse(boundary["cpu_as_gpu_fallback"])

    def test_sidecar_runner_source_argv_boundary_materializes_argv_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_sidecar_runner import (
            build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary,
        )
        from rtlmeter_stdout_cycles_plan import (
            build_rtlmeter_stdout_cycles_execution_plan,
        )

        boundary = build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary(
            runner_implementation_boundary=self._implementation_boundary(),
            stdout_cycles_plan=build_rtlmeter_stdout_cycles_execution_plan(),
        )

        self.assertEqual(boundary["surface"], "rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary")
        self.assertEqual(boundary["status"], "rtlmeter_stdout_cycles_sidecar_runner_argv_metadata_ready")
        self.assertEqual(boundary["missing_runner_source_context"], [])
        self.assertEqual(boundary["rejected_runner_source_context"], [])
        self.assertEqual(boundary["observables"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertEqual(boundary["runner_command_role"], "materialized_for_later_run_not_invoked")
        self.assertEqual(boundary["runner_command_argv"][0], "python3")
        self.assertEqual(boundary["runner_command_argv"][1], "src/tools/rtlmeter_stdout_cycles_sidecar_runner.py")
        self.assertIn("--observable-execute-dir", boundary["runner_command_argv"])
        self.assertIn("--", boundary["runner_command_argv"])
        self.assertIn("third_party/rtlmeter/rtlmeter", boundary["runner_command_argv"])
        self.assertNotIn("--execute", boundary["runner_command_argv"])
        self.assertIsNone(boundary["launcher_command_argv"])
        self.assertFalse(boundary["runner_source_cli_implemented"])
        self.assertFalse(boundary["subprocess_invoked"])
        self.assertFalse(boundary["rtlmeter_invoked"])
        self.assertFalse(boundary["adapter_invoked"])
        self.assertFalse(boundary["sidecar_runner_invoked"])
        self.assertFalse(boundary["sidecar_execution_invoked"])
        self.assertFalse(boundary["coverage_output_compare_reached"])
        self.assertFalse(boundary["execution_performed"])
        self.assertFalse(boundary["measurement_performed"])
        self.assertFalse(boundary["execution_authority"])
        self.assertFalse(boundary["runtime_abi"])
        self.assertFalse(boundary["cpu_as_gpu_fallback"])
        self.assertFalse(boundary["gpu_execution_claimed"])
        self.assertNotIn("command_result", boundary)
        self.assertNotIn("output_status", boundary)
        self.assertNotIn("cycle_count", boundary)

    def test_sidecar_runner_source_argv_boundary_rejects_run_hybrid_template(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_sidecar_runner import (
            build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary,
        )
        from rtlmeter_stdout_cycles_plan import (
            build_rtlmeter_stdout_cycles_execution_plan,
        )

        plan = build_rtlmeter_stdout_cycles_execution_plan()
        gpu_candidate = dict(plan["gpu_candidate"])
        gpu_candidate["command"] = ["python3", "src/tools/run_hybrid_template.py"]
        plan["gpu_candidate"] = gpu_candidate

        boundary = build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary(
            runner_implementation_boundary=self._implementation_boundary(),
            stdout_cycles_plan=plan,
        )

        self.assertEqual(boundary["status"], "rtlmeter_stdout_cycles_sidecar_runner_blocked_rejected_command")
        self.assertIn("run_hybrid_template.py", boundary["rejected_runner_source_context"])
        self.assertIsNone(boundary["runner_command_argv"])
        self.assertEqual(boundary["runner_command_role"], "not_materialized")
        self.assertFalse(boundary["subprocess_invoked"])
        self.assertFalse(boundary["execution_performed"])
        self.assertFalse(boundary["measurement_performed"])
        self.assertFalse(boundary["cpu_as_gpu_fallback"])

    def test_sidecar_runner_source_argv_boundary_blocks_cpu_reference_command(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_sidecar_runner import (
            build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary,
        )
        from rtlmeter_stdout_cycles_plan import (
            build_rtlmeter_stdout_cycles_execution_plan,
        )

        plan = build_rtlmeter_stdout_cycles_execution_plan()
        gpu_candidate = dict(plan["cpu_reference"])
        gpu_candidate["cpu_as_gpu_fallback_allowed"] = False
        plan["gpu_candidate"] = gpu_candidate
        boundary = build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary(
            runner_implementation_boundary=self._implementation_boundary(),
            stdout_cycles_plan=plan,
        )

        self.assertEqual(boundary["status"], "rtlmeter_stdout_cycles_sidecar_runner_blocked_plan")
        self.assertIn(
            "stdout_cycles_plan.gpu_candidate.compile_args.sidecar_accel",
            boundary["missing_runner_source_context"],
        )
        self.assertIsNone(boundary["runner_command_argv"])
        self.assertFalse(boundary["execution_performed"])
        self.assertFalse(boundary["cpu_as_gpu_fallback"])

    def test_implementation_boundary_rejects_unready_adapter_metadata(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_runner_implementation import (
            build_rtlmeter_stdout_cycles_runner_implementation_boundary,
        )

        boundary = build_rtlmeter_stdout_cycles_runner_implementation_boundary(
            runner_contract=self._contract(),
            runner_adapter_entrypoint_metadata={
                "surface": "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata",
                "runner_adapter_entrypoint": "rtlmeter_stdout_cycles_runner_adapter_entrypoint",
            },
        )

        self.assertEqual(boundary["status"], "rtlmeter_stdout_cycles_runner_implementation_blocked_missing_adapter")
        self.assertEqual(boundary["missing_implementation_context"], ["runner_adapter_entrypoint_metadata.status"])
        self.assertIsNone(boundary["runner_command_argv"])
        self.assertEqual(boundary["runner_command_role"], "not_materialized")
        self.assertFalse(boundary["execution_performed"])
        self.assertFalse(boundary["measurement_performed"])

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
