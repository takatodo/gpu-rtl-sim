import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_hls_attention_head_variant as hls  # noqa: E402


class ScientificCirctHlsAttentionHeadVariantTest(HybridCliTestCase):
    def test_shape_validation(self) -> None:
        self.assertEqual(hls._shape("1024x1"), (1024, 1))
        with self.assertRaises(ValueError):
            hls._shape("1024")

    def test_firrtl_materializes_four_explicit_heads(self) -> None:
        firrtl = hls._firrtl()
        self.assertIn("public module MicrogptAttentionHeadHls4", firrtl)
        self.assertIn("input h0_x0", firrtl)
        self.assertIn("input h3_x19", firrtl)
        self.assertIn("output h3_y3", firrtl)
        self.assertIn("connect h2_y1", firrtl)

    def test_materialize_and_measure_compares_against_baseline(self) -> None:
        observed = {
            "status": "hls_variant_measured",
            "variant": "attention_head4_hls_friendly",
            "nstates": 1024,
            "repeat": 5,
            "inner_repeat": 1000,
            "integration_batches": 15,
            "head_count": 4,
            "input_bytes": 81920,
            "output_bytes": 131072,
            "mismatch_count": 0,
            "cpu_control_checksum": 11,
            "gpu_control_checksum": 11,
            "cpu_vs_gpu_output_equal": True,
            "cpu_vs_gpu_control_checksum_equal": True,
            "cpu_ms": 3.0,
            "gpu_end_to_end_ms": 0.3,
            "gpu_kernel_ms": 0.05,
            "bridge_hybrid_wall_ms_per_integration_batch": 0.3,
            "cpu_to_gpu_end_to_end_speedup": 10.0,
            "cpu_to_gpu_kernel_speedup": 60.0,
            "cpu_to_bridge_hybrid_wall_speedup": 10.0,
        }

        def fake_run(argv: list[str]) -> dict[str, object]:
            stdout = json.dumps(observed) if argv and argv[0].endswith("attention_head4_hls_friendly_direct") else ""
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
            baseline = root / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "status": "direct_verilator_callsite_entrypoint_timing_measured",
                        "candidate": "microgpt_attention_head",
                        "shape": "1024x1",
                        "cpu_to_bridge_hybrid_wall_speedup": 6.0,
                        "adapter_average": {
                            "cpu_ms": 1.0,
                            "gpu_end_to_end_ms": 0.16,
                            "gpu_kernel_ms": 0.03,
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = hls.materialize_and_measure(out_dir=root / "out", baseline_report=baseline)

        self.assertEqual(report["status"], "hls_variant_improved")
        self.assertEqual(report["variant"], "attention_head4_hls_friendly")
        self.assertEqual(report["head_count"], 4)
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertTrue(report["cpu_vs_gpu_control_checksum_equal"])
        self.assertTrue(report["comparison"]["speedup_improved"])
        self.assertEqual(report["comparison"]["baseline_speedup"], 6.0)
        self.assertEqual(report["comparison"]["variant_speedup"], 10.0)
        self.assertEqual(report["comparison"]["variant_gpu_end_to_end_speedup"], 10.0)
        self.assertEqual(report["lowering_evidence"]["firrtl_to_systemverilog"], True)
        self.assertEqual(report["lowering_evidence"]["gpu_library_build"], True)
        self.assertEqual(report["lowering_evidence"]["direct_callsite_bridge_build"], True)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_failed_stage_fails_closed(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            return {
                "argv": [hls._sanitize(arg) for arg in argv],
                "returncode": 1,
                "stdout": "",
                "stderr": "failed",
                "process_wall_ms": 1.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(hls.shutil, "which", return_value="/usr/bin/tool"), \
             mock.patch.object(hls, "_verilator_root_command", return_value=(Path("/verilator"), None)), \
             mock.patch.object(hls, "_run", side_effect=fake_run):
            report = hls.materialize_and_measure(out_dir=Path(temp_dir) / "out")

        self.assertEqual(report["status"], "failed_firtool")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
