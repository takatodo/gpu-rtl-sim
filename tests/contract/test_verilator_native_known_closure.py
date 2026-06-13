import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from verilator_native_known_closure import (  # noqa: E402
    RECOGNIZED_TARGET_ONLY,
    STATUS_FILELIST_MISSING,
    STATUS_RECOGNIZED,
    STATUS_REGISTRY_UNUSABLE,
    STATUS_UNRECOGNIZED,
    recognize_verilator_native_known_closure,
)

KNOWN_TOP = "pulp_ita_mha_gpu_cov_tb"
KNOWN_TEMPLATE = "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json"


class VerilatorNativeKnownClosureTest(HybridCliTestCase):
    def _known_entries(self) -> list[str]:
        template = json.loads((REPO_ROOT / KNOWN_TEMPLATE).read_text(encoding="utf-8"))
        return [str(item) for item in template["source_files"]]

    def _write_filelist(self, directory: Path, lines: list[str]) -> Path:
        filelist = directory / "native_known.f"
        filelist.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return filelist

    def _recognize(self, filelist: Path, top_module: str = KNOWN_TOP) -> dict:
        return recognize_verilator_native_known_closure(
            filelist_path=filelist,
            top_module=top_module,
            repo_root=REPO_ROOT,
        )

    def test_tracked_pulp_ita_mha_filelist_and_top_are_recognized(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            lines = ["// tracked known closure", "", *self._known_entries()]
            report = self._recognize(self._write_filelist(Path(tmp), lines))
        self.assertEqual(report["status"], STATUS_RECOGNIZED)
        self.assertTrue(report["recognized"])
        self.assertEqual(report["target"], "pulp_ita_mha")
        self.assertEqual(report["launch_template"], KNOWN_TEMPLATE)
        self.assertEqual(report["missing_recognition_context"], [])
        self._assert_fail_closed_non_claims(report)

    def test_extra_filelist_entry_fails_closed_as_unrecognized(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            lines = [*self._known_entries(), "overlays/ITA/src/unexpected_extra.sv"]
            report = self._recognize(self._write_filelist(Path(tmp), lines))
        self.assertEqual(report["status"], STATUS_UNRECOGNIZED)
        self.assertFalse(report["recognized"])
        self.assertIsNone(report["target"])
        self.assertIn("tracked_known_closure_match", report["missing_recognition_context"])
        self.assertIn("recognized target only", report["diagnostic"])
        self._assert_fail_closed_non_claims(report)

    def test_unknown_top_module_fails_closed_as_unrecognized(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = self._recognize(
                self._write_filelist(Path(tmp), self._known_entries()),
                top_module="arbitrary_unknown_top",
            )
        self.assertEqual(report["status"], STATUS_UNRECOGNIZED)
        self.assertEqual(report["diagnostic"], RECOGNIZED_TARGET_ONLY)
        self._assert_fail_closed_non_claims(report)

    def test_reordered_entries_fail_closed_without_inference(self) -> None:
        entries = self._known_entries()
        entries[0], entries[-1] = entries[-1], entries[0]
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = self._recognize(self._write_filelist(Path(tmp), entries))
        self.assertEqual(report["status"], STATUS_UNRECOGNIZED)
        self._assert_fail_closed_non_claims(report)

    def test_missing_filelist_fails_closed(self) -> None:
        report = self._recognize(REPO_ROOT / "artifacts" / "does_not_exist.f")
        self.assertEqual(report["status"], STATUS_FILELIST_MISSING)
        self.assertIn("filelist", report["missing_recognition_context"])
        self._assert_fail_closed_non_claims(report)

    def test_missing_registry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = recognize_verilator_native_known_closure(
                filelist_path=self._write_filelist(Path(tmp), self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path="config/does_not_exist_native_known_closures.json",
            )
        self.assertEqual(report["status"], STATUS_REGISTRY_UNUSABLE)
        self.assertIn("native_known_closures_registry", report["missing_recognition_context"])
        self._assert_fail_closed_non_claims(report)

    def _assert_fail_closed_non_claims(self, report: dict) -> None:
        self.assertTrue(report["fail_closed"])
        self.assertFalse(report["arbitrary_filelist_supported"])
        self.assertFalse(report["dependency_inference_performed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["speedup_claimed"])
        self.assertTrue(report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))
