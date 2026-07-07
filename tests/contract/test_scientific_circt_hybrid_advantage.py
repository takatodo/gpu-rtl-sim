import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_hybrid_advantage import aggregate  # noqa: E402


class ScientificCirctHybridAdvantageTest(HybridCliTestCase):
    def _write_report(self, path: Path, shape: str, e2e: float, kernel: float) -> None:
        path.write_text(
            json.dumps(
                {
                    "status": "measured",
                    "candidate": "dense_matmul_tile",
                    "shape": shape,
                    "inner_repeat": 1000,
                    "median": {
                        "cpu_ms": 1.0,
                        "gpu_end_to_end_ms": 1.0 / e2e,
                        "gpu_kernel_ms": 1.0 / kernel,
                        "cpu_to_gpu_end_to_end_speedup": e2e,
                        "cpu_to_gpu_kernel_speedup": kernel,
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_aggregate_finds_first_end_to_end_favorable_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            p64 = root / "64.json"
            p256 = root / "256.json"
            p1024 = root / "1024.json"
            self._write_report(p64, "64x1", 0.4, 2.0)
            self._write_report(p256, "256x1", 1.3, 8.0)
            self._write_report(p1024, "1024x1", 4.8, 30.0)

            summary = aggregate([p64, p256, p1024])

        self.assertEqual(summary["status"], "analyzed")
        self.assertEqual(summary["counts"]["gpu_end_to_end_favorable"], 2)
        self.assertEqual(summary["counts"]["cpu_end_to_end_favorable"], 1)
        self.assertEqual(summary["counts"]["gpu_kernel_favorable"], 3)
        self.assertEqual(summary["first_gpu_end_to_end_favorable_shape"], "256x1")
        self.assertEqual(summary["best_gpu_end_to_end"]["shape"], "1024x1")
        self.assertEqual(summary["by_candidate"]["dense_matmul_tile"]["first_gpu_end_to_end_favorable_shape"], "256x1")
        self.assertEqual(summary["by_candidate"]["dense_matmul_tile"]["gpu_kernel_favorable"], 3)
        self.assertEqual(
            summary["hybrid_recommendation"]["recommended_action"],
            "use_gpu_for_state_parallel_batches_at_or_above_first_favorable_shape",
        )
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            p64 = root / "64.json"
            p256 = root / "256.json"
            out = root / "summary.json"
            self._write_report(p64, "64x1", 0.4, 2.0)
            self._write_report(p256, "256x1", 1.3, 8.0)
            result = self.run_python_tool(
                "src/tools/scientific_circt_hybrid_advantage.py",
                "--report",
                p64.as_posix(),
                "--report",
                p256.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), report_payload)
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
