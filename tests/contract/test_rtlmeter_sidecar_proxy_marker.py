import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterSidecarProxyMarkerTest(HybridCliTestCase):
    def _runtime_non_claim_context(self) -> dict[str, object]:
        return {
            "wrapper_executed_obj_dir_vsim": False,
            "obj_dir_vsim_execution_observed": False,
            "runtime_execution_authority": False,
            "vsim_runtime_execution_claimed": False,
            "missing_runtime_execution_context": ["wrapper_executed_obj_dir_vsim"],
        }

    def _write_observables(self, path: Path) -> None:
        (path / "_execute").mkdir(parents=True, exist_ok=True)
        (path / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
        (path / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")

    def _observable_dir(self) -> str:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        return str(build_rtlmeter_stdout_cycles_execution_plan()["gpu_candidate"]["observable_execute_dir"])

    def _observed_report(self, root: Path, marker_payload: dict[str, object] | None = None) -> dict[str, object]:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import MARKER_FILENAME
        from rtlmeter_stdout_cycles_execution_observation import (
            build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation,
        )
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner import materialize_rtlmeter_stdout_cycles_sidecar_runner_command

        plan = build_rtlmeter_stdout_cycles_execution_plan()
        observable_dir = plan["gpu_candidate"]["observable_execute_dir"]
        out = root / observable_dir
        self._write_observables(out)
        if marker_payload is not None:
            (out / MARKER_FILENAME).write_text(json.dumps(marker_payload) + "\n", encoding="utf-8")
        return build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation(
            stdout_cycles_plan=plan,
            command_result={
                "command": materialize_rtlmeter_stdout_cycles_sidecar_runner_command(plan),
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            },
            repo_root=root,
        )

    def test_missing_proxy_marker_keeps_gpu_execution_claim_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self._observed_report(Path(temp_dir))

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_observables_ready")
        self.assertTrue(report["execution_performed"])
        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_missing")
        self.assertFalse(report["sidecar_proxy_marker_present"])
        self.assertFalse(report["sidecar_proxy_marker_valid"])
        self.assertTrue(report["gpu_execution_claim_requires_valid_proxy_marker"])
        self.assertEqual((report["reviewed_proxy_metadata_observed"], report["rtlmeter_vsim_proxy_handoff_status"], report["rtlmeter_vsim_proxy_handoff_reached"]), (False, "blocked", False))
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertEqual(
            report["sidecar_proxy_evidence"]["surface"],
            "rtlmeter_sidecar_proxy_marker_evidence",
        )
        self.assertEqual(
            report["sidecar_proxy_evidence"]["sidecar_proxy_marker_status"],
            "rtlmeter_sidecar_proxy_marker_missing",
        )
        self.assertFalse(report["sidecar_proxy_evidence"]["sidecar_execute_proxy_authorized_by_wrapper_branch"])
        execution_evidence = report["sidecar_proxy_execution_evidence"]
        self.assertEqual(execution_evidence["surface"], "rtlmeter_stdout_cycles_sidecar_proxy_execution_evidence")
        self.assertEqual(execution_evidence["status"], "blocked")
        self.assertTrue(execution_evidence["observables_ready"])
        self.assertTrue(execution_evidence["runner_command_observed"])
        self.assertIn("marker_file", execution_evidence["blocking_context"])
        self.assertEqual((execution_evidence["reviewed_proxy_metadata_observed"], execution_evidence["rtlmeter_vsim_proxy_handoff_status"], execution_evidence["rtlmeter_vsim_proxy_handoff_reached"]), (False, "blocked", False))
        self.assertFalse(report["gpu_execution_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_invalid_proxy_marker_is_observed_but_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "ordinary_cpu_vsim",
                    "phase": "sidecar_verilate",
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": True,
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_invalid")
        self.assertTrue(report["sidecar_proxy_marker_present"])
        self.assertFalse(report["sidecar_proxy_marker_valid"])
        self.assertIn("producer", report["sidecar_proxy_marker_missing_context"])
        self.assertIn("ordinary_vsim_output", report["sidecar_proxy_marker_missing_context"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertEqual(
            report["sidecar_proxy_evidence"]["sidecar_proxy_marker_status"],
            "rtlmeter_sidecar_proxy_marker_invalid",
        )
        self.assertIn("producer", report["sidecar_proxy_evidence"]["sidecar_proxy_marker_missing_context"])
        self.assertFalse(report["sidecar_proxy_evidence"]["sidecar_execute_proxy_authorized_by_wrapper_branch"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_legacy_proxy_marker_without_runtime_non_claim_context_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "execute_proxy_installed_by_wrapper_branch": False,
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_invalid")
        self.assertFalse(report["sidecar_proxy_marker_valid"])
        self.assertTrue(
            {
                "wrapper_executed_obj_dir_vsim",
                "obj_dir_vsim_execution_observed",
                "runtime_execution_authority",
                "vsim_runtime_execution_claimed",
                "missing_runtime_execution_context",
            }.issubset(report["sidecar_proxy_marker_missing_context"])
        )
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_valid_proxy_marker_is_metadata_only_in_this_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            observable_dir = self._observable_dir()
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "observable_execute_dir": observable_dir,
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "execute_proxy_installed_by_wrapper_branch": False,
                    **self._runtime_non_claim_context(),
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_valid")
        self.assertTrue(report["sidecar_proxy_marker_present"])
        self.assertTrue(report["sidecar_proxy_marker_valid"])
        self.assertEqual(report["sidecar_proxy_marker_missing_context"], [])
        self.assertTrue(report["execution_performed"])
        self.assertFalse(report["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["measurement_performed"])
        execution_evidence = report["sidecar_proxy_execution_evidence"]
        self.assertEqual(execution_evidence["status"], "blocked")
        self.assertTrue(execution_evidence["sidecar_proxy_marker_valid"])
        self.assertIn(
            "sidecar_execute_proxy_installed_by_wrapper_branch",
            execution_evidence["blocking_context"],
        )
        self.assertFalse(report["gpu_execution_claimed"])

    def test_writer_creates_observable_valid_proxy_marker(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import (
            MARKER_FILENAME,
            write_rtlmeter_sidecar_proxy_marker,
        )
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            marker = write_rtlmeter_sidecar_proxy_marker(
                observable_execute_dir=plan["gpu_candidate"]["observable_execute_dir"],
                repo_root=root,
            )
            report = self._observed_report(root)
            marker_payload = json.loads(marker.read_text(encoding="utf-8"))

        self.assertEqual(marker.name, MARKER_FILENAME)
        self.assertEqual(marker_payload["observable_execute_dir"], plan["gpu_candidate"]["observable_execute_dir"])
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
        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_valid")
        self.assertTrue(report["sidecar_proxy_marker_valid"])
        self.assertFalse(report["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_writer_requires_observable_execute_dir(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import write_rtlmeter_sidecar_proxy_marker

        with self.assertRaises(ValueError):
            write_rtlmeter_sidecar_proxy_marker(observable_execute_dir=None, repo_root=None)

    def test_proxy_installed_marker_grants_reviewed_proxy_metadata_observed_without_gpu_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            observable_dir = self._observable_dir()
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "observable_execute_dir": observable_dir,
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "direct_sidecar_proxy_marker_status": "rtlmeter_direct_sidecar_proxy_marker_authorized",
                    "direct_sidecar_proxy_readiness_status": "rtlmeter_direct_sidecar_proxy_installed",
                    "direct_sidecar_execute_proxy_status": "rtlmeter_vsim_execute_proxy_installed",
                    "execute_proxy_installed_by_wrapper_branch": True,
                    "execute_proxy_source_patch_by_wrapper_branch": True,
                    **self._runtime_non_claim_context(),
                    "direct_sidecar_proxy_readiness": {
                        "status": "rtlmeter_direct_sidecar_proxy_installed",
                        "proxy_installed_by_wrapper_branch": True,
                        "proxy_authorized_by_wrapper_branch": True,
                        "reviewed_proxy_metadata_observed": True,
                        "vsim_execute_proxy": {"status": "rtlmeter_vsim_execute_proxy_installed", "reviewed_proxy_metadata_observed": True},
                        "vsim_sidecar_proxy_target": {"reviewed_proxy_target": True},
                        "vsim_main_proxy_patch": {"patched_by_wrapper_branch": True, "reviewed_proxy_metadata_observed": True},
                    },
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_valid")
        self.assertTrue(report["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertEqual((report["reviewed_proxy_metadata_observed"], report["rtlmeter_vsim_proxy_handoff_status"], report["rtlmeter_vsim_proxy_handoff_reached"], report["runtime_execution_authority"], report["obj_dir_vsim_execution_observed"]), (True, "ready", True, False, False))
        self.assertTrue(report["reviewed_proxy_metadata_requires_source_patch_marker"])
        self.assertTrue(report["rtlmeter_proxy_handoff_observed"])
        evidence = report["sidecar_proxy_evidence"]
        self.assertEqual(evidence["surface"], "rtlmeter_sidecar_proxy_marker_evidence")
        self.assertEqual(evidence["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_valid")
        self.assertTrue(evidence["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertTrue(evidence["sidecar_execute_proxy_source_patch_by_wrapper_branch"])
        self.assertTrue(evidence["sidecar_execute_proxy_authorized_by_wrapper_branch"])
        self.assertEqual((evidence["gpu_execution_claimed"], evidence["vsim_runtime_execution_claimed"], evidence["runtime_execution_authority"]), (False, False, False))
        execution_evidence = report["sidecar_proxy_execution_evidence"]
        self.assertEqual(execution_evidence["status"], "ready")
        self.assertTrue(execution_evidence["observables_ready"])
        self.assertTrue(execution_evidence["runner_command_observed"])
        self.assertEqual((execution_evidence["reviewed_proxy_metadata_observed"], execution_evidence["rtlmeter_vsim_proxy_handoff_status"], execution_evidence["rtlmeter_vsim_proxy_handoff_reached"]), (True, "ready", True))
        self.assertEqual((execution_evidence["rtlmeter_proxy_handoff_observed"], execution_evidence["runtime_execution_authority"], execution_evidence["obj_dir_vsim_execution_observed"]), (True, False, False))
        self.assertEqual(execution_evidence["blocking_context"], [])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_proxy_marker_for_different_observable_dir_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "observable_execute_dir": "artifacts/other/execute-dir",
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "direct_sidecar_proxy_marker_status": "rtlmeter_direct_sidecar_proxy_marker_authorized",
                    "direct_sidecar_proxy_readiness_status": "rtlmeter_direct_sidecar_proxy_installed",
                    "direct_sidecar_execute_proxy_status": "rtlmeter_vsim_execute_proxy_installed",
                    "execute_proxy_installed_by_wrapper_branch": True,
                    "execute_proxy_source_patch_by_wrapper_branch": True,
                    **self._runtime_non_claim_context(),
                    "direct_sidecar_proxy_readiness": {
                        "status": "rtlmeter_direct_sidecar_proxy_installed",
                        "proxy_installed_by_wrapper_branch": True,
                        "proxy_authorized_by_wrapper_branch": True,
                        "reviewed_proxy_metadata_observed": True,
                        "vsim_execute_proxy": {"status": "rtlmeter_vsim_execute_proxy_installed", "reviewed_proxy_metadata_observed": True},
                        "vsim_sidecar_proxy_target": {"reviewed_proxy_target": True},
                        "vsim_main_proxy_patch": {"patched_by_wrapper_branch": True, "reviewed_proxy_metadata_observed": True},
                    },
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_invalid")
        self.assertIn("observable_execute_dir", report["sidecar_proxy_marker_missing_context"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_installed_proxy_marker_without_source_patch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            observable_dir = self._observable_dir()
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "observable_execute_dir": observable_dir,
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "execute_proxy_installed_by_wrapper_branch": True,
                    "execute_proxy_authorized_by_wrapper_branch": True,
                    **self._runtime_non_claim_context(),
                    "direct_sidecar_proxy_readiness": {
                        "proxy_installed_by_wrapper_branch": True,
                        "reviewed_proxy_metadata_observed": True,
                    },
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_invalid")
        self.assertIn(
            "execute_proxy_source_patch_by_wrapper_branch",
            report["sidecar_proxy_marker_missing_context"],
        )
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["sidecar_execute_proxy_authorized_by_wrapper_branch"])
        self.assertEqual(report["sidecar_proxy_execution_evidence"]["status"], "blocked")
        self.assertIn(
            "execute_proxy_source_patch_by_wrapper_branch",
            report["sidecar_proxy_execution_evidence"]["blocking_context"],
        )
        self.assertFalse(report["gpu_execution_claimed"])

    def test_forged_proxy_authorized_marker_without_installed_proxy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            observable_dir = self._observable_dir()
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "observable_execute_dir": observable_dir,
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "execute_proxy_installed_by_wrapper_branch": False,
                    "execute_proxy_authorized_by_wrapper_branch": True,
                    **self._runtime_non_claim_context(),
                    "wrapper_executed_obj_dir_vsim": True,
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_invalid")
        self.assertIn(
            "execute_proxy_installed_by_wrapper_branch",
            report["sidecar_proxy_marker_missing_context"],
        )
        self.assertTrue({"direct_sidecar_proxy_readiness", "wrapper_executed_obj_dir_vsim"}.issubset(report["sidecar_proxy_marker_missing_context"]))
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["sidecar_execute_proxy_authorized_by_wrapper_branch"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_authorized_marker_with_readiness_authority_disagreement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            observable_dir = self._observable_dir()
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "observable_execute_dir": observable_dir,
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "direct_sidecar_proxy_marker_status": "rtlmeter_direct_sidecar_proxy_marker_authorized",
                    "direct_sidecar_proxy_readiness_status": "rtlmeter_direct_sidecar_proxy_installed",
                    "direct_sidecar_execute_proxy_status": "rtlmeter_vsim_execute_proxy_installed",
                    "execute_proxy_installed_by_wrapper_branch": True,
                    "execute_proxy_source_patch_by_wrapper_branch": True,
                    "execute_proxy_authorized_by_wrapper_branch": True,
                    **self._runtime_non_claim_context(),
                    "direct_sidecar_proxy_readiness": {
                        "status": "rtlmeter_direct_sidecar_proxy_installed",
                        "proxy_authorized_by_wrapper_branch": False,
                        "reviewed_proxy_metadata_observed": True,
                        "proxy_installed_by_wrapper_branch": True,
                        "vsim_execute_proxy": {"status": "rtlmeter_vsim_execute_proxy_installed", "reviewed_proxy_metadata_observed": True},
                        "vsim_main_proxy_patch": {"patched_by_wrapper_branch": True, "reviewed_proxy_metadata_observed": True},
                    },
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_invalid")
        self.assertIn("direct_sidecar_proxy_readiness.proxy_authorized_by_wrapper_branch", report["sidecar_proxy_marker_missing_context"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])

    def test_authorized_marker_with_execute_proxy_status_disagreement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            observable_dir = self._observable_dir()
            report = self._observed_report(
                Path(temp_dir),
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_proxy_marker",
                    "producer": "rtlmeter_verilator_wrapper_runtime",
                    "phase": "sidecar_verilate",
                    "observable_execute_dir": observable_dir,
                    "cpu_as_gpu_fallback": False,
                    "ordinary_vsim_output": False,
                    "direct_sidecar_proxy_marker_status": "rtlmeter_direct_sidecar_proxy_marker_authorized",
                    "direct_sidecar_proxy_readiness_status": "rtlmeter_direct_sidecar_proxy_installed",
                    "direct_sidecar_execute_proxy_status": "rtlmeter_vsim_execute_proxy_blocked_by_source_patch",
                    "execute_proxy_installed_by_wrapper_branch": True,
                    "execute_proxy_source_patch_by_wrapper_branch": True,
                    "execute_proxy_authorized_by_wrapper_branch": True,
                    **self._runtime_non_claim_context(),
                    "direct_sidecar_proxy_readiness": {
                        "status": "rtlmeter_direct_sidecar_proxy_installed",
                        "proxy_authorized_by_wrapper_branch": True,
                        "reviewed_proxy_metadata_observed": True,
                        "proxy_installed_by_wrapper_branch": True,
                        "vsim_execute_proxy": {"status": "rtlmeter_vsim_execute_proxy_installed", "reviewed_proxy_metadata_observed": False},
                        "vsim_sidecar_proxy_target": {"reviewed_proxy_target": True},
                        "vsim_main_proxy_patch": {"patched_by_wrapper_branch": True, "reviewed_proxy_metadata_observed": True},
                    },
                },
            )

        self.assertEqual(report["sidecar_proxy_marker_status"], "rtlmeter_sidecar_proxy_marker_invalid")
        self.assertIn("direct_sidecar_execute_proxy_status", report["sidecar_proxy_marker_missing_context"])
        self.assertIn("direct_sidecar_proxy_readiness.vsim_execute_proxy.reviewed_proxy_metadata_observed", report["sidecar_proxy_marker_missing_context"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["rtlmeter_proxy_handoff_observed"])
        self.assertFalse(report["gpu_execution_claimed"])
