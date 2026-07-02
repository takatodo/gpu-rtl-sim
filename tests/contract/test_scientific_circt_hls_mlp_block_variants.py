import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_hls_mlp_block_variants as hls  # noqa: E402


class ScientificCirctHlsMlpBlockVariantsTest(HybridCliTestCase):
    def test_shape_validation(self) -> None:
        self.assertEqual(hls._shape("1024x1"), (1024, 1))
        with self.assertRaises(ValueError):
            hls._shape("1024")

    def test_firrtl_materializes_expected_units(self) -> None:
        mlp = hls.firrtl(hls.VARIANTS["mlp4_hls_friendly"])
        self.assertIn("public module MicrogptMlpHls4", mlp)
        self.assertIn("input m3_x3", mlp)
        self.assertIn("output m3_y1", mlp)
        self.assertIn("connect m2_y0", mlp)
        block = hls.firrtl(hls.VARIANTS["block2_hls_friendly"])
        self.assertIn("public module MicrogptBlockHls2", block)
        self.assertIn("input b1_k10", block)
        self.assertIn("output b1_y1", block)
        self.assertIn("connect b0_y0", block)
        inference = hls.firrtl(hls.VARIANTS["inference2_hls_friendly"])
        self.assertIn("public module MicrogptInferenceHls2", inference)
        self.assertIn("input i1_tok1", inference)
        self.assertIn("output i1_y2", inference)
        self.assertIn("connect i0_y2", inference)

    def test_materialize_and_measure_summarizes_two_variants(self) -> None:
        observed_by_variant = {
            "mlp4_hls_friendly": {
                "status": "hls_variant_measured",
                "variant": "mlp4_hls_friendly",
                "mismatch_count": 0,
                "cpu_vs_gpu_output_equal": True,
                "cpu_vs_gpu_control_checksum_equal": True,
                "cpu_ms": 4.0,
                "gpu_end_to_end_ms": 0.4,
                "gpu_kernel_ms": 0.1,
                "cpu_to_gpu_end_to_end_speedup": 10.0,
                "cpu_to_gpu_kernel_speedup": 40.0,
                "cpu_to_bridge_hybrid_wall_speedup": 9.0,
            },
            "block2_hls_friendly": {
                "status": "hls_variant_measured",
                "variant": "block2_hls_friendly",
                "mismatch_count": 0,
                "cpu_vs_gpu_output_equal": True,
                "cpu_vs_gpu_control_checksum_equal": True,
                "cpu_ms": 5.0,
                "gpu_end_to_end_ms": 0.5,
                "gpu_kernel_ms": 0.1,
                "cpu_to_gpu_end_to_end_speedup": 10.0,
                "cpu_to_gpu_kernel_speedup": 50.0,
                "cpu_to_bridge_hybrid_wall_speedup": 8.0,
            },
        }

        def fake_run(argv: list[str]) -> dict[str, object]:
            stdout = ""
            if argv and argv[0].endswith("_direct"):
                variant = Path(argv[0]).name.removesuffix("_direct")
                stdout = json.dumps(observed_by_variant[variant])
            return {
                "argv": [hls._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": stdout,
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(hls.shutil, "which", return_value="/usr/bin/tool"), \
             mock.patch.object(hls, "_verilator_root_command", return_value=(Path("/verilator"), None)), \
             mock.patch.object(hls, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            (root / "mlp_baseline.json").write_text(
                json.dumps({"status": "measured", "candidate": "microgpt_mlp_slice", "shape": "1024x1", "median": {"cpu_to_gpu_end_to_end_speedup": 2.0}}),
                encoding="utf-8",
            )
            (root / "block_baseline.json").write_text(
                json.dumps({"status": "measured", "candidate": "microgpt_block_slice", "shape": "1024x1", "median": {"cpu_to_gpu_end_to_end_speedup": 6.0}}),
                encoding="utf-8",
            )
            with mock.patch.dict(
                hls.VARIANTS,
                {
                    "mlp4_hls_friendly": hls.Variant(
                        **{**hls.VARIANTS["mlp4_hls_friendly"].__dict__, "baseline_report": root / "mlp_baseline.json"}
                    ),
                    "block2_hls_friendly": hls.Variant(
                        **{**hls.VARIANTS["block2_hls_friendly"].__dict__, "baseline_report": root / "block_baseline.json"}
                    ),
                },
            ):
                report = hls.materialize_and_measure(
                    variants=["mlp4_hls_friendly", "block2_hls_friendly"],
                    out_dir=root / "out",
                )

        self.assertEqual(report["status"], "hls_variant_summary_ready")
        self.assertEqual(len(report["variants"]), 2)
        self.assertTrue(all(item["cpu_vs_gpu_output_equal"] for item in report["variants"]))
        self.assertTrue(all(item["comparison"]["speedup_improved"] for item in report["variants"]))
        self.assertEqual(report["source_ir_transformation_rules"][0]["rule_signal"], "favor_explicit_independent_units_when_bridge_speedup_improves")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_failed_stage_fails_closed(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            return {"argv": [hls._sanitize(arg) for arg in argv], "returncode": 1, "stdout": "", "stderr": "failed", "process_wall_ms": 1.0}

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(hls.shutil, "which", return_value="/usr/bin/tool"), \
             mock.patch.object(hls, "_verilator_root_command", return_value=(Path("/verilator"), None)), \
             mock.patch.object(hls, "_run", side_effect=fake_run):
            report = hls.materialize_and_measure(variants=["mlp4_hls_friendly"], out_dir=Path(temp_dir) / "out")

        self.assertEqual(report["status"], "hls_variant_summary_incomplete")
        self.assertEqual(report["variants"][0]["status"], "failed_firtool")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
