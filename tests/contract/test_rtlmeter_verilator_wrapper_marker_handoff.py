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

    def _generated_main(self) -> str:
        return "\n".join(
            [
                "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
                '#include "verilated.h"',
                '#include "Vsim.h"',
                "int main(int argc, char** argv, char**) {",
                "    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};",
                "    contextp->commandArgs(argc, argv);",
                '    const std::unique_ptr<Vsim> topp{new Vsim{contextp.get(), ""}};',
                "    // Simulate until $finish",
                "    while (VL_LIKELY(!contextp->gotFinish())) {",
                "        topp->eval();",
                "    }",
                "    topp->final();",
                "    contextp->statsPrintSummary();",
                "}",
                "",
            ]
        )

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
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan, rtlmeter_compile_dir
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN, PHASE_SIDECAR_VERILATE
        from rtlmeter_verilator_wrapper_runtime import (
            SIDECAR_CONTEXT_JSON_ENV,
            run_rtlmeter_verilator_wrapper,
            strip_sidecar_only_verilator_options,
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
            compile_dir = root / rtlmeter_compile_dir(
                Path(str(plan["gpu_candidate"]["work_root"])),
                str(plan["seed"]),
            )
            ordinary_vsim = compile_dir / "obj_dir" / "Vsim"

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                ordinary_vsim.parent.mkdir(parents=True)
                ordinary_vsim.write_text("#!/bin/sh\n", encoding="utf-8")
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
        self.assertEqual(
            calls[0][0], [str(real), *strip_sidecar_only_verilator_options(argv)]
        )
        self.assertEqual(calls[0][1]["env"][PHASE_ENV], PHASE_SIDECAR_VERILATE)
        self.assertEqual(marker_payload["schema_role"], "rtlmeter_sidecar_proxy_marker")
        self.assertEqual(marker_payload["producer"], "rtlmeter_verilator_wrapper_runtime")
        self.assertEqual(marker_payload["direct_sidecar_proxy_marker_status"], "rtlmeter_direct_sidecar_proxy_marker_blocked")
        self.assertEqual(marker_payload["direct_sidecar_proxy_readiness_status"], "rtlmeter_direct_sidecar_proxy_not_installed")
        self.assertEqual(marker_payload["direct_sidecar_execute_proxy_status"], "rtlmeter_vsim_execute_proxy_blocked_by_source_patch")
        self.assert_no_local_absolute_paths(json.dumps(marker_payload, sort_keys=True))
        self.assertFalse(marker_payload["cpu_as_gpu_fallback"])
        self.assertEqual((marker_payload["ordinary_vsim_output"], marker_payload["execute_proxy_installed_by_wrapper_branch"], marker_payload["wrapper_executed_obj_dir_vsim"]), (False, False, False))
        self.assertEqual(
            (
                marker_payload["wrapper_executed_obj_dir_vsim"],
                marker_payload["obj_dir_vsim_execution_observed"],
                marker_payload["runtime_execution_authority"],
                marker_payload["vsim_runtime_execution_claimed"],
                marker_payload["missing_runtime_execution_context"],
            ),
            (False, False, False, False, ["wrapper_executed_obj_dir_vsim"]),
        )
        readiness = marker_payload["direct_sidecar_proxy_readiness"]
        self.assertEqual(readiness["status"], "rtlmeter_direct_sidecar_proxy_not_installed")
        self.assertEqual(readiness["rtlmeter_compile_dir"], compile_dir.relative_to(root).as_posix())
        self.assertEqual(readiness["expected_vsim_path"], ordinary_vsim.relative_to(root).as_posix())
        self.assertTrue(readiness["expected_vsim_present"])
        self.assertFalse(readiness["proxy_installable"])
        self.assertFalse(readiness["proxy_installed_by_wrapper_branch"])
        self.assertEqual((readiness["vsim_binary_proxy_installed_by_wrapper_branch"], readiness["vsim_main_source_patch_applied_by_wrapper_branch"], readiness["wrapper_executed_obj_dir_vsim"]), (False, False, False))
        self.assertTrue(readiness["ordinary_vsim_unclaimable"])
        self.assertFalse(readiness["reviewed_proxy_metadata_observed"])
        self.assertIn("vsim_main_proxy_patch.reviewed_proxy_metadata_observed", readiness["missing_proxy_context"])

    def test_rtlmeter_run_phase_marks_proxy_installed_when_generated_main_is_patched(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import MARKER_FILENAME
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan, rtlmeter_compile_dir
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN
        from rtlmeter_verilator_wrapper_runtime import SIDECAR_CONTEXT_JSON_ENV, run_rtlmeter_verilator_wrapper
        from rtlmeter_vsim_main_proxy_patch import PROXY_ENV

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
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            marker = root / plan["gpu_candidate"]["observable_execute_dir"] / MARKER_FILENAME
            compile_dir = root / rtlmeter_compile_dir(
                Path(str(plan["gpu_candidate"]["work_root"])),
                str(plan["seed"]),
            )
            main_cpp = compile_dir / "obj_dir" / "Vsim__main.cpp"
            vsim = compile_dir / "obj_dir" / "Vsim"
            proxy = root / "proxy" / "rtlmeter-vsim-proxy"
            proxy.parent.mkdir(); self._touch_executable(proxy)
            (proxy.parent / f"{proxy.name}.review.json").write_text(json.dumps({"schema_role": "rtlmeter_vsim_sidecar_proxy_target_review", "target_path": proxy.relative_to(root).as_posix(), "reviewed_proxy_target": True}) + "\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                main_cpp.parent.mkdir(parents=True)
                main_cpp.write_text(self._generated_main(), encoding="utf-8")
                vsim.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                vsim.chmod(0o755)
                return subprocess.CompletedProcess(command, 0)

            code = run_rtlmeter_verilator_wrapper(
                argv,
                executable=wrapper,
                environ={
                    SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._sidecar_context()),
                    PHASE_ENV: PHASE_RTL_METER_RUN,
                    PROXY_ENV: proxy.as_posix(),
                    "PWD": str(root),
                    "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}",
                },
                runner=fake_runner,
            )
            marker_payload = json.loads(marker.read_text(encoding="utf-8"))
            patched_main = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        self.assertTrue(marker_payload["execute_proxy_installed_by_wrapper_branch"])
        self.assertTrue(marker_payload["execute_proxy_authorized_by_wrapper_branch"])
        self.assertEqual(marker_payload["direct_sidecar_proxy_marker_status"], "rtlmeter_direct_sidecar_proxy_marker_authorized")
        self.assertEqual(marker_payload["direct_sidecar_proxy_readiness_status"], "rtlmeter_direct_sidecar_proxy_installed")
        self.assertEqual(marker_payload["direct_sidecar_execute_proxy_status"], "rtlmeter_vsim_execute_proxy_installed")
        self.assertEqual((marker_payload["vsim_binary_proxy_installed_by_wrapper_branch"], marker_payload["vsim_main_source_patch_applied_by_wrapper_branch"], marker_payload["wrapper_executed_obj_dir_vsim"]), (True, True, False))
        self.assertEqual(
            (
                marker_payload["wrapper_executed_obj_dir_vsim"],
                marker_payload["obj_dir_vsim_execution_observed"],
                marker_payload["runtime_execution_authority"],
                marker_payload["vsim_runtime_execution_claimed"],
                marker_payload["missing_runtime_execution_context"],
            ),
            (False, False, False, False, ["wrapper_executed_obj_dir_vsim"]),
        )
        self.assert_no_local_absolute_paths(json.dumps(marker_payload, sort_keys=True))
        readiness = marker_payload["direct_sidecar_proxy_readiness"]
        self.assertEqual(readiness["status"], "rtlmeter_direct_sidecar_proxy_installed")
        self.assertTrue(readiness["proxy_installed_by_wrapper_branch"])
        self.assertEqual((readiness["vsim_binary_proxy_installed_by_wrapper_branch"], readiness["vsim_main_source_patch_applied_by_wrapper_branch"], readiness["wrapper_executed_obj_dir_vsim"]), (True, True, False))
        self.assertTrue(readiness["reviewed_proxy_metadata_observed"])
        self.assertTrue(readiness["vsim_sidecar_proxy_target"]["reviewed_proxy_target"])
        self.assertTrue(readiness["vsim_main_proxy_patch"]["reviewed_proxy_metadata_observed"])
        self.assertTrue(readiness["vsim_execute_proxy"]["reviewed_proxy_metadata_observed"])
        self.assertIn("RTLMETER_VSIM_SIDECAR_PROXY", patched_main)

    def test_failed_direct_verilate_does_not_write_proxy_authority_marker(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import MARKER_FILENAME
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan, rtlmeter_compile_dir
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN
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
            compile_dir = root / rtlmeter_compile_dir(Path(str(plan["gpu_candidate"]["work_root"])), str(plan["seed"]))
            main_cpp = compile_dir / "obj_dir" / "Vsim__main.cpp"
            vsim = compile_dir / "obj_dir" / "Vsim"

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                main_cpp.parent.mkdir(parents=True)
                main_cpp.write_text(self._generated_main(), encoding="utf-8")
                vsim.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                vsim.chmod(0o755)
                return subprocess.CompletedProcess(command, 9)

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
            marker_exists = marker.exists()
            patched_main = main_cpp.read_text(encoding="utf-8")
            vsim_text = vsim.read_text(encoding="utf-8")

        self.assertEqual(code, 9)
        self.assertEqual(calls[0][1]["env"][PHASE_ENV], "sidecar_verilate")
        self.assertFalse(marker_exists)
        self.assertNotIn("RTLMETER_VSIM_SIDECAR_PROXY", patched_main)
        self.assertEqual(vsim_text, "#!/bin/sh\nexit 0\n")
