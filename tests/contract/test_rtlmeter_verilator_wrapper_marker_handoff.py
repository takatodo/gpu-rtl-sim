import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVerilatorWrapperMarkerHandoffTest(HybridCliTestCase):
    def _touch_executable(self, path: Path) -> None:
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)

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

    def _sidecar_context(self) -> dict[str, object]:
        return {
            "target": "rtlmeter_example_kind_hello",
            "mode": "rtlmeter_first_seed",
            "template_or_target_registry_entry": (
                "config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json"
            ),
            "source_gate_or_manifest_ref": "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md",
            "host_probe_metadata": {"clock_field": "top__DOT__clk", "reset_field": "none"},
            "coverage_output_target": "rtlmeter_stdout_and_cycles_equivalence",
            "coverage_manifest": {"outputs": ["normalized_stdout", "rtlmeter_cycles"]},
            "state_and_report_path_rules": {"root": "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"},
            "compare_labels": {"cpu": "rtlmeter_cpu", "gpu": "rtlmeter_sidecar_candidate"},
            "source_closure": self._reviewed_source_closure(),
        }

    def test_rtlmeter_run_phase_writes_proxy_marker_when_direct_verilate_runs(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import MARKER_FILENAME
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN, PHASE_SIDECAR_VERILATE
        from rtlmeter_verilator_wrapper_runtime import (
            SIDECAR_CONTEXT_JSON_ENV,
            run_rtlmeter_verilator_wrapper,
        )

        argv = [
            "--cc",
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
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = root / "wrapper" / "verilator"
            real = root / "real" / "verilator"
            wrapper.parent.mkdir()
            real.parent.mkdir()
            self._touch_executable(wrapper)
            self._touch_executable(real)
            calls: list[tuple[list[str], dict[str, object]]] = []
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            marker = root / plan["gpu_candidate"]["observable_execute_dir"] / MARKER_FILENAME

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 0)

            code = run_rtlmeter_verilator_wrapper(
                argv,
                executable=wrapper,
                environ={
                    SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._sidecar_context()),
                    PHASE_ENV: PHASE_RTL_METER_RUN,
                    "PWD": str(root),
                    "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}",
                },
                runner=fake_runner,
            )
            marker_payload = json.loads(marker.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][0], [str(real), *argv])
        self.assertEqual(calls[0][1]["env"][PHASE_ENV], PHASE_SIDECAR_VERILATE)
        self.assertEqual(marker_payload["schema_role"], "rtlmeter_sidecar_proxy_marker")
        self.assertEqual(marker_payload["producer"], "rtlmeter_verilator_wrapper_runtime")
        self.assertFalse(marker_payload["cpu_as_gpu_fallback"])
        self.assertFalse(marker_payload["ordinary_vsim_output"])
