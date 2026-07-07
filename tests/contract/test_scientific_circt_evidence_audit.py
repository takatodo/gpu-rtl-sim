import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_evidence_audit import audit  # noqa: E402


class ScientificCirctEvidenceAuditTest(HybridCliTestCase):
    def _timing_report(self, root: Path, candidate: str, shape: str) -> Path:
        path = root / f"{candidate}_{shape}.json"
        path.write_text(
            json.dumps(
                {
                    "status": "measured",
                    "candidate": candidate,
                    "shape": shape,
                    "commands": [{"stage": "cpu_gpu_timing_run"}],
                    "median": {
                        "cpu_ms": 2.0,
                        "gpu_end_to_end_ms": 1.0,
                        "gpu_kernel_ms": 0.25,
                        "cpu_to_gpu_end_to_end_speedup": 2.0,
                        "cpu_to_gpu_kernel_speedup": 8.0,
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def _fixtures(self, root: Path) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
        sv = root / "candidate.sv"
        sv.write_text("module Candidate; endmodule\n", encoding="utf-8")
        reports = {
            shape: self._timing_report(root, "candidate", shape).as_posix()
            for shape in ("64x1", "256x1", "1024x1")
        }
        selection = {
            "scientific_circt_gpu_candidate_search": {
                "candidate": {
                    "systemverilog": sv.as_posix(),
                    "timing_reports": reports,
                    "verilator_cpu_reference": "cpu_reference_pass",
                }
            }
        }
        summary = {
            "counts": {"measured": 3},
            "by_candidate": {"candidate": {"first_gpu_end_to_end_favorable_shape": "256x1"}},
        }
        policy = {
            "status": "policy_ready",
            "gpu_ready_candidate_count": 1,
            "candidates": {
                "candidate": {
                    "recommended_action": "select_gpu_state_parallel",
                    "min_gpu_nstates": 256,
                }
            },
        }
        matrix = {
            "status": "matrix_ready",
            "record_count": 3,
            "measured_speedup_records_attached": 3,
            "records": [
                {
                    "candidate": "candidate",
                    "shape": shape,
                    "decision": "select_gpu_state_parallel" if shape != "64x1" else "select_cpu",
                    "reason": "measured_candidate_at_or_above_threshold" if shape != "64x1" else "below_min_gpu_nstates",
                    "timing_evidence": {
                        "status": "measured",
                        "cpu_to_gpu_end_to_end_speedup": 2.0 if shape != "64x1" else 0.5,
                        "cpu_to_gpu_kernel_speedup": 8.0,
                    },
                }
                for shape in ("64x1", "256x1", "1024x1")
            ],
        }
        return selection, summary, policy, matrix

    def test_audit_marks_complete_candidate_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = audit(*self._fixtures(Path(temp_dir)))

        self.assertEqual(report["status"], "evidence_ready")
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["ready_candidate_count"], 1)
        self.assertTrue(report["candidates"]["candidate"]["ready"])
        self.assertTrue(report["candidates"]["candidate"]["dispatch_matrix_rows_ready"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_audit_marks_missing_report_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selection, summary, policy, matrix = self._fixtures(root)
            selection["scientific_circt_gpu_candidate_search"]["candidate"]["timing_reports"]["64x1"] = (root / "missing.json").as_posix()
            report = audit(selection, summary, policy, matrix)

        self.assertEqual(report["status"], "evidence_incomplete")
        self.assertEqual(report["ready_candidate_count"], 0)

    def test_audit_marks_missing_matrix_evidence_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selection, summary, policy, matrix = self._fixtures(root)
            matrix["records"] = matrix["records"][:-1]
            matrix["record_count"] = 2
            matrix["measured_speedup_records_attached"] = 2
            report = audit(selection, summary, policy, matrix)

        self.assertEqual(report["status"], "evidence_incomplete")
        self.assertEqual(report["ready_candidate_count"], 0)
        self.assertFalse(report["candidates"]["candidate"]["dispatch_matrix_rows_ready"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selection, summary, policy, matrix = self._fixtures(root)
            selection_path = root / "selection.json"
            summary_path = root / "summary.json"
            policy_path = root / "policy.json"
            matrix_path = root / "matrix.json"
            out = root / "audit.json"
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_evidence_audit.py",
                "--selection",
                selection_path.as_posix(),
                "--summary",
                summary_path.as_posix(),
                "--policy",
                policy_path.as_posix(),
                "--dispatch-matrix",
                matrix_path.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), report_payload)
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
