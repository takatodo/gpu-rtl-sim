import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_dense_matmul_tile_gpu_timing as timing  # noqa: E402


class ScientificCirctDenseMatmulTileGpuTimingTest(HybridCliTestCase):
    def test_parse_shape_rejects_non_n_by_one_shapes(self) -> None:
        self.assertEqual(timing.parse_shape("64x1"), (64, 1))
        with self.assertRaises(ValueError):
            timing.parse_shape("64")

    def test_summarize_measurements_reports_medians_and_match_status(self) -> None:
        summary = timing.summarize_measurements(
            [
                {"match": True, "cpu_ms": 4.0, "gpu_end_to_end_ms": 2.0, "gpu_kernel_ms": 1.0,
                 "cpu_to_gpu_end_to_end_speedup": 2.0, "cpu_to_gpu_kernel_speedup": 4.0},
                {"match": True, "cpu_ms": 6.0, "gpu_end_to_end_ms": 3.0, "gpu_kernel_ms": 2.0,
                 "cpu_to_gpu_end_to_end_speedup": 2.0, "cpu_to_gpu_kernel_speedup": 3.0},
            ]
        )
        self.assertEqual(summary["status"], "measured")
        self.assertEqual(summary["median"]["cpu_ms"], 5.0)
        self.assertEqual(summary["median"]["cpu_to_gpu_kernel_speedup"], 3.5)

    def test_measure_uses_nvcc_and_sanitizes_report_paths(self) -> None:
        sample = {
            "status": "measured", "nstates": 64, "repeat": 5, "inner_repeat": 1000,
            "match": True, "cpu_ms": 1.0, "gpu_end_to_end_ms": 2.0, "gpu_kernel_ms": 0.5,
            "cpu_to_gpu_end_to_end_speedup": 0.5, "cpu_to_gpu_kernel_speedup": 2.0,
        }

        def fake_run(argv: list[str]) -> dict[str, object]:
            stage_stdout = json.dumps(sample) if argv[0].endswith("dense_matmul_tile_gpu_timing") else ""
            return {"argv": [timing._sanitize(arg) for arg in argv], "returncode": 0, "stdout": stage_stdout, "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(timing.shutil, "which", return_value="/usr/bin/nvcc"), \
             mock.patch.object(timing, "_run", side_effect=fake_run):
            report = timing.measure(shape="64x1", repeat=5, inner_repeat=1000, out_dir=Path(temp_dir))

        self.assertEqual(report["status"], "measured")
        self.assertEqual(report["median"]["cpu_to_gpu_kernel_speedup"], 2.0)
        self.assertIn("<out_dir>/", report["artifacts"]["cuda_source"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
