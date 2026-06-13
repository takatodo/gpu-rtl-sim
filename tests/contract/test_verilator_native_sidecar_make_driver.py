import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from verilator_native_sidecar_make_driver import (  # noqa: E402
    STATUS_BLOCKED_MISSING_MDIR,
    STATUS_BLOCKED_UNRECOGNIZED,
    STATUS_BUILD_PLAN_READY,
    main as make_driver_main,
    plan_native_sidecar_build,
    run_native_sidecar_build,
)

KNOWN_TOP = "pulp_ita_mha_gpu_cov_tb"
KNOWN_TEMPLATE = "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json"


class VerilatorNativeSidecarMakeDriverTest(HybridCliTestCase):
    def _known_entries(self) -> list[str]:
        template = json.loads((REPO_ROOT / KNOWN_TEMPLATE).read_text(encoding="utf-8"))
        return [str(item) for item in template["source_files"]]

    def _write_filelist(self, directory: Path, lines: list[str]) -> Path:
        filelist = directory / "native_known.f"
        filelist.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return filelist

    def _assert_fail_closed_non_claims(self, report: dict) -> None:
        self.assertTrue(report["fail_closed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["speedup_claimed"])
        self.assertTrue(report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_unrecognized_closure_blocks_build_plan(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = plan_native_sidecar_build(
                filelist_path=self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"]),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_UNRECOGNIZED)
        self.assertFalse(report["build_plan_ready"])
        self.assertIn("recognized_known_closure", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_recognized_closure_without_verilated_mdir_blocks(self) -> None:
        # A recognized closure still fails closed until the mdir has *_classes.mk.
        # Use a controlled registry pointing at an empty mdir so the result does
        # not depend on leftover local verilated obj_dirs under artifacts/.
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, _mdir = self._registry_with_local_mdir(tmp_path)
            report = plan_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_MISSING_MDIR)
        self.assertEqual(report["target"], "pulp_ita_mha")
        self.assertIn("verilated_mdir_classes_mk", report["missing_build_context"])
        self.assertFalse(report["mdir_verilated"])
        self._assert_fail_closed_non_claims(report)

    def test_recognized_closure_with_verilated_mdir_is_plan_ready(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = plan_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
            )
        self.assertEqual(report["status"], STATUS_BUILD_PLAN_READY)
        self.assertTrue(report["build_plan_ready"])
        self.assertTrue(report["mdir_verilated"])
        self.assertEqual(report["missing_build_context"], [])
        self._assert_fail_closed_non_claims(report)

    def test_run_does_not_invoke_template_flow_when_blocked(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(argv):
            calls.append(argv)
            return 0

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = run_native_sidecar_build(
                filelist_path=self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"]),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                template_runner=fake_runner,
            )
        self.assertEqual(calls, [])
        self.assertFalse(report["template_flow_invoked"])
        self.assertFalse(report["template_flow_passed"])
        self.assertEqual(report["status"], STATUS_BLOCKED_UNRECOGNIZED)

    def test_run_delegates_recognized_closure_to_template_flow(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(argv):
            calls.append(argv)
            return 0

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = run_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                shape="64x1",
                template_runner=fake_runner,
            )
        self.assertEqual(len(calls), 1)
        argv = calls[0]
        self.assertIn("--shape", argv)
        self.assertEqual(argv[argv.index("--shape") + 1], "64x1")
        self.assertTrue(argv[0].endswith(".json"))
        self.assertTrue(report["template_flow_invoked"])
        self.assertTrue(report["template_flow_passed"])

    def test_run_records_template_flow_failure_without_passing(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = run_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                template_runner=lambda argv: 1,
            )
        self.assertTrue(report["template_flow_invoked"])
        self.assertFalse(report["template_flow_passed"])
        self.assertEqual(report["template_flow_returncode"], 1)

    def test_cli_plan_returns_nonzero_for_unrecognized_closure(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            filelist = self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"])
            rc = make_driver_main([
                "plan", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", filelist.as_posix(), "--top-module", KNOWN_TOP,
            ])
        self.assertEqual(rc, 1)

    def test_cli_plan_succeeds_and_writes_summary_with_mdir_override(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            filelist = self._write_filelist(tmp_path, self._known_entries())
            summary = tmp_path / "native_sidecar_build.json"
            rc = make_driver_main([
                "plan", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", filelist.as_posix(), "--top-module", KNOWN_TOP,
                "--mdir", mdir.as_posix(), "--summary-out", summary.as_posix(),
                "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1",
            ])
            self.assertEqual(rc, 0)
            written = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(written["status"], STATUS_BUILD_PLAN_READY)
        self.assertTrue(written["mdir_verilated"])

    def _registry_with_local_mdir(self, tmp_path: Path) -> tuple[str, Path]:
        """Build a registry whose closure template points its build mdir into tmp."""
        mdir = tmp_path / "obj_dir"
        mdir.mkdir()
        template = json.loads((REPO_ROOT / KNOWN_TEMPLATE).read_text(encoding="utf-8"))
        template["build"]["mdir"] = mdir.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        template_rel = (tmp_path / "template.json").resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        (REPO_ROOT / template_rel).write_text(json.dumps(template), encoding="utf-8")
        registry = {
            "schema_version": 1,
            "schema_role": "verilator_native_known_closures",
            "closures": [
                {"target": "pulp_ita_mha", "top_module": KNOWN_TOP, "launch_template": template_rel}
            ],
        }
        registry_rel = (tmp_path / "registry.json").resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        (REPO_ROOT / registry_rel).write_text(json.dumps(registry), encoding="utf-8")
        return registry_rel, mdir
