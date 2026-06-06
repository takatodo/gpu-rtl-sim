import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterMaterializedVsimProxyHandoffTest(HybridCliTestCase):
    def _write_executable(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

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

    def test_materialized_wrapper_executes_installed_vsim_proxy(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import MARKER_FILENAME
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan, rtlmeter_compile_dir
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN
        from rtlmeter_verilator_wrapper_runtime import SIDECAR_CONTEXT_JSON_ENV, write_rtlmeter_verilator_wrapper
        from rtlmeter_vsim_main_proxy_patch import PROXY_ENV

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = write_rtlmeter_verilator_wrapper(
                root / "wrapper" / "verilator",
                python_executable=sys.executable,
            )
            real = root / "real" / "verilator"
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            marker = root / plan["gpu_candidate"]["observable_execute_dir"] / MARKER_FILENAME
            compile_dir = root / rtlmeter_compile_dir(
                Path(str(plan["gpu_candidate"]["work_root"])),
                str(plan["seed"]),
            )
            obj_dir = compile_dir / "obj_dir"
            main_cpp = obj_dir / "Vsim__main.cpp"
            vsim = obj_dir / "Vsim"
            ordinary_log = root / "ordinary-vsim.log"
            proxy_log = root / "proxy.log"
            proxy = root / "proxy" / "rtlmeter-vsim-proxy"
            real.parent.mkdir(); proxy.parent.mkdir()
            self._write_executable(
                real,
                "#!/bin/sh\n"
                f"mkdir -p {shlex.quote(obj_dir.as_posix())}\n"
                f"cat > {shlex.quote(main_cpp.as_posix())} <<'EOF_MAIN'\n"
                f"{self._generated_main()}"
                "EOF_MAIN\n"
                f"cat > {shlex.quote(vsim.as_posix())} <<'EOF_VSIM'\n"
                "#!/bin/sh\n"
                f"echo ordinary-vsim-ran \"$@\" >> {shlex.quote(ordinary_log.as_posix())}\n"
                "exit 0\n"
                "EOF_VSIM\n"
                f"chmod +x {shlex.quote(vsim.as_posix())}\n"
                "exit 0\n",
            )
            self._write_executable(
                proxy,
                "#!/bin/sh\n"
                f"echo proxy-ran \"$@\" >> {shlex.quote(proxy_log.as_posix())}\n"
                "exit 0\n",
            )
            (proxy.parent / f"{proxy.name}.review.json").write_text(json.dumps({"schema_role": "rtlmeter_vsim_sidecar_proxy_target_review", "target_path": proxy.relative_to(root).as_posix(), "reviewed_proxy_target": True}) + "\n", encoding="utf-8")
            env = {
                **os.environ,
                SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._sidecar_context()),
                PHASE_ENV: PHASE_RTL_METER_RUN,
                PROXY_ENV: proxy.as_posix(),
                "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}{os.pathsep}{os.environ.get('PATH', '')}",
                "PWD": root.as_posix(),
            }
            wrapper_completed = subprocess.run(
                [str(wrapper), *self._expanded_sidecar_argv()], cwd=root, env=env, text=True, capture_output=True, check=False
            )
            vsim_completed = subprocess.run(
                [str(vsim), "--from-test"],
                env={**os.environ, PROXY_ENV: proxy.as_posix()},
                text=True,
                capture_output=True,
                check=False,
            )
            marker_payload = json.loads(marker.read_text(encoding="utf-8"))
            ordinary_log_exists = ordinary_log.exists()
            proxy_log_text = proxy_log.read_text(encoding="utf-8")

        self.assertEqual(wrapper_completed.returncode, 0, wrapper_completed.stderr)
        self.assertEqual(vsim_completed.returncode, 0, vsim_completed.stderr)
        self.assertFalse(ordinary_log_exists)
        self.assertEqual(proxy_log_text, "proxy-ran --from-test\n")
        self.assertEqual((marker_payload["execute_proxy_installed_by_wrapper_branch"], marker_payload["wrapper_executed_obj_dir_vsim"], marker_payload["runtime_execution_authority"], marker_payload["obj_dir_vsim_execution_observed"]), (True, False, False, False))
        readiness = marker_payload["direct_sidecar_proxy_readiness"]
        self.assertEqual(readiness["status"], "rtlmeter_direct_sidecar_proxy_installed")
        self.assertTrue(readiness["vsim_main_proxy_patch"]["execution_authority"])
        self.assertTrue(readiness["vsim_execute_proxy"]["execution_authority"])
        self.assertTrue(readiness["execution_authority"])

    def test_materialized_vsim_proxy_fails_closed_without_proxy_env(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan, rtlmeter_compile_dir
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN
        from rtlmeter_verilator_wrapper_runtime import SIDECAR_CONTEXT_JSON_ENV, write_rtlmeter_verilator_wrapper; from rtlmeter_vsim_main_proxy_patch import PROXY_ENV

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = write_rtlmeter_verilator_wrapper(root / "wrapper" / "verilator", python_executable=sys.executable)
            real = root / "real" / "verilator"; plan = build_rtlmeter_stdout_cycles_execution_plan()
            compile_dir = root / rtlmeter_compile_dir(Path(str(plan["gpu_candidate"]["work_root"])), str(plan["seed"]))
            obj_dir = compile_dir / "obj_dir"
            main_cpp = obj_dir / "Vsim__main.cpp"
            vsim = obj_dir / "Vsim"
            ordinary_log = root / "ordinary-vsim.log"
            real.parent.mkdir()
            real_script = (
                "#!/bin/sh\n"
                f"mkdir -p {shlex.quote(obj_dir.as_posix())}\n"
                f"cat > {shlex.quote(main_cpp.as_posix())} <<'EOF_MAIN'\n{self._generated_main()}EOF_MAIN\n"
                f"cat > {shlex.quote(vsim.as_posix())} <<'EOF_VSIM'\n"
                "#!/bin/sh\n"
                f"echo ordinary-vsim-ran \"$@\" >> {shlex.quote(ordinary_log.as_posix())}\n"
                "exit 0\nEOF_VSIM\n"
                f"chmod +x {shlex.quote(vsim.as_posix())}\nexit 0\n"
            )
            self._write_executable(real, real_script)

            wrapper_completed = subprocess.run(
                [str(wrapper), *self._expanded_sidecar_argv()],
                cwd=root,
                env={
                    **os.environ,
                    SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._sidecar_context()),
                    PHASE_ENV: PHASE_RTL_METER_RUN,
                    "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}{os.pathsep}{os.environ.get('PATH', '')}",
                    "PWD": root.as_posix(),
                },
                text=True,
                capture_output=True,
                check=False,
            )
            vsim_completed = subprocess.run([str(vsim), "--from-test"], text=True, capture_output=True, check=False)
            missing_proxy_completed = subprocess.run([str(vsim), "--from-test"], env={**os.environ, PROXY_ENV: (root / "missing-proxy").as_posix()}, text=True, capture_output=True, check=False)

        self.assertEqual(wrapper_completed.returncode, 0, wrapper_completed.stderr)
        self.assertEqual((vsim_completed.returncode, missing_proxy_completed.returncode), (125, 127))
        for needle, stderr in (("missing RTLMETER_VSIM_SIDECAR_PROXY", vsim_completed.stderr), ("missing-proxy", missing_proxy_completed.stderr)): self.assertIn(needle, stderr)
        self.assertFalse(ordinary_log.exists())

    def test_materialized_wrapper_uses_repo_root_env_when_rtlmeter_runs_from_compile_dir(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import MARKER_FILENAME
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan, rtlmeter_compile_dir
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN, REPO_ROOT_ENV
        from rtlmeter_verilator_wrapper_runtime import SIDECAR_CONTEXT_JSON_ENV, write_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = write_rtlmeter_verilator_wrapper(
                root / "wrapper" / "verilator",
                python_executable=sys.executable,
            )
            real = root / "real" / "verilator"
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            marker = root / plan["gpu_candidate"]["observable_execute_dir"] / MARKER_FILENAME
            misplaced_marker = (
                root
                / rtlmeter_compile_dir(Path(str(plan["gpu_candidate"]["work_root"])), str(plan["seed"]))
                / plan["gpu_candidate"]["observable_execute_dir"]
                / MARKER_FILENAME
            )
            compile_dir = root / rtlmeter_compile_dir(
                Path(str(plan["gpu_candidate"]["work_root"])),
                str(plan["seed"]),
            )
            obj_dir = compile_dir / "obj_dir"
            main_cpp = obj_dir / "Vsim__main.cpp"
            real.parent.mkdir()
            compile_dir.mkdir(parents=True)
            self._write_executable(
                real,
                "#!/bin/sh\n"
                "mkdir -p obj_dir\n"
                "cat > obj_dir/Vsim__main.cpp <<'EOF_MAIN'\n"
                f"{self._generated_main()}"
                "EOF_MAIN\n"
                "exit 0\n",
            )

            completed = subprocess.run(
                [str(wrapper), *self._expanded_sidecar_argv()],
                cwd=compile_dir,
                env={
                    **os.environ,
                    SIDECAR_CONTEXT_JSON_ENV: json.dumps(self._sidecar_context()),
                    PHASE_ENV: PHASE_RTL_METER_RUN,
                    REPO_ROOT_ENV: root.as_posix(),
                    "PATH": f"{wrapper.parent}{os.pathsep}{real.parent}{os.pathsep}{os.environ.get('PATH', '')}",
                },
                text=True,
                capture_output=True,
                check=False,
            )
            marker_payload = json.loads(marker.read_text(encoding="utf-8"))
            patched_main = main_cpp.read_text(encoding="utf-8")
            marker_exists = marker.exists()
            misplaced_marker_exists = misplaced_marker.exists()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(marker_exists)
        self.assertFalse(misplaced_marker_exists)
        self.assertFalse(marker_payload["execute_proxy_installed_by_wrapper_branch"])
        self.assertEqual(
            marker_payload["direct_sidecar_proxy_readiness"]["vsim_main_proxy_patch"]["status"],
            "rtlmeter_vsim_main_proxy_patch_applied",
        )
        self.assertIn("RTLMETER_VSIM_SIDECAR_PROXY", patched_main)
