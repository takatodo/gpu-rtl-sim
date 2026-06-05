import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterStdoutCyclesRunnerAdapterTest(HybridCliTestCase):
    def _runner_contract(self) -> dict[str, object]:
        from rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES

        return {
            "surface": "rtlmeter_stdout_cycles_runner_contract",
            "status": "rtlmeter_stdout_cycles_runner_contract_blocked",
            "missing_runner_context": ["rtlmeter_stdout_cycles_runner_implementation"],
            "acceptance_policy": {
                "normalized_stdout_match": True,
                "cycle_count_match": True,
                "raw_state_equality_required": False,
            },
            "observables": list(EXPECTED_OBSERVABLES),
        }

    def test_adapter_implementation_materializes_runner_command_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_runner_adapter import (
            STATUS_ADAPTER_IMPLEMENTATION_RUNNER_ARGV_READY,
            build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata,
            build_rtlmeter_stdout_cycles_runner_adapter_implementation_boundary,
        )
        from rtlmeter_stdout_cycles_runner_implementation import (
            build_rtlmeter_stdout_cycles_runner_implementation_boundary,
        )

        adapter_metadata = build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata()
        implementation = build_rtlmeter_stdout_cycles_runner_implementation_boundary(
            runner_contract=self._runner_contract(),
            runner_adapter_entrypoint_metadata=adapter_metadata,
        )
        report = build_rtlmeter_stdout_cycles_runner_adapter_implementation_boundary(
            runner_implementation_boundary=implementation,
            stdout_cycles_plan=build_rtlmeter_stdout_cycles_execution_plan(),
            repo_root=Path.cwd(),
        )

        self.assertEqual(report["status"], STATUS_ADAPTER_IMPLEMENTATION_RUNNER_ARGV_READY)
        self.assertEqual(report["missing_adapter_implementation_context"], [])
        self.assertEqual(report["runner_command_argv"][0], "python3")
        self.assertEqual(report["runner_command_argv"][1], "src/tools/rtlmeter_stdout_cycles_sidecar_runner.py")
        self.assertIn("third_party/rtlmeter/rtlmeter", report["runner_command_argv"])
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["execution_performed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_adapter_implementation_requires_tracked_runner_source_file(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_runner_adapter import (
            STATUS_ADAPTER_IMPLEMENTATION_BLOCKED_CONTRACT,
            build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata,
            build_rtlmeter_stdout_cycles_runner_adapter_implementation_boundary,
        )
        from rtlmeter_stdout_cycles_runner_implementation import (
            build_rtlmeter_stdout_cycles_runner_implementation_boundary,
        )

        adapter_metadata = build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata()
        implementation = build_rtlmeter_stdout_cycles_runner_implementation_boundary(
            runner_contract=self._runner_contract(),
            runner_adapter_entrypoint_metadata=adapter_metadata,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_rtlmeter_stdout_cycles_runner_adapter_implementation_boundary(
                runner_implementation_boundary=implementation,
                stdout_cycles_plan=build_rtlmeter_stdout_cycles_execution_plan(),
                repo_root=Path(temp_dir),
            )

        self.assertEqual(report["status"], STATUS_ADAPTER_IMPLEMENTATION_BLOCKED_CONTRACT)
        self.assertIn("runner_adapter_source_file", report["missing_adapter_implementation_context"])
        self.assertIsNone(report["runner_command_argv"])
        self.assertFalse(report["execution_authority"])
