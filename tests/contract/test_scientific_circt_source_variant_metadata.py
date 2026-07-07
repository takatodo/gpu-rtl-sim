import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_metadata as metadata  # noqa: E402


class ScientificCirctSourceVariantMetadataTest(HybridCliTestCase):
    def _matrix(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hybrid_dispatch_matrix",
            "selected_next_source_variant_runtime_boundary": {
                "candidate": "microgpt_inference_slice",
                "source_variant": "inference2_hls_friendly",
                "shape": "1024x1",
                "rank": 3,
                "steps": 1,
                "variant_speedup": 9.8,
                "speedup_delta": 6.1,
            },
            "source_variant_runtime_integration_queue": [
                {
                    "candidate": "microgpt_attention_head",
                    "source_variant": "attention_head4_hls_friendly",
                    "shape": "1024x1",
                    "rank": 1,
                    "steps": 1,
                    "variant_speedup": 13.3,
                },
                {
                    "candidate": "microgpt_mlp_slice",
                    "source_variant": "mlp4_hls_friendly",
                    "shape": "1024x1",
                    "rank": 2,
                    "steps": 1,
                    "variant_speedup": 9.9,
                },
                {
                    "candidate": "microgpt_inference_slice",
                    "source_variant": "inference2_hls_friendly",
                    "shape": "1024x1",
                    "rank": 3,
                    "steps": 1,
                    "variant_speedup": 9.8,
                },
            ],
        }

    def _gpu_source(self, root: Path, name: str, in_count: int, out_count: int) -> str:
        path = root / f"{name}.cu"
        path.write_text(
            "\n".join(
                [
                    "#include <cstdint>",
                    f"struct In {{ uint8_t x[{in_count}]; }};",
                    f"struct Out {{ uint64_t y[{out_count}]; }};",
                    f'extern "C" int {name}_run_gpu_outputs(int, int, Out*, size_t) {{ return 0; }}',
                    f'extern "C" int {name}_run_hybrid_json(int, int, int, int, char*, size_t) {{ return 0; }}',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path.relative_to(Path.cwd()).as_posix()

    def _variant(self, root: Path, source_variant: str, candidate: str, in_count: int, out_count: int, improved: bool) -> dict[str, object]:
        artifact_dir = root / source_variant
        artifact_dir.mkdir()
        direct = artifact_dir / f"{source_variant}_direct"
        direct.write_text("", encoding="utf-8")
        library = artifact_dir / f"lib{source_variant}.so"
        library.write_text("", encoding="utf-8")
        systemverilog = artifact_dir / f"{source_variant}.sv"
        systemverilog.write_text("module sim; endmodule\n", encoding="utf-8")
        mdir = artifact_dir / "obj_dir"
        mdir.mkdir()
        return {
            "variant": source_variant,
            "candidate": candidate,
            "shape": "1024x1",
            "status": "hls_variant_improved" if improved else "hls_variant_measured_no_speedup_improvement",
            "repeat": 5,
            "inner_repeat": 1000,
            "integration_batches": 15,
            "comparison": {
                "baseline_speedup": 5.0,
                "variant_speedup": 8.0 if improved else 4.8,
                "speedup_delta": 3.0 if improved else -0.2,
                "speedup_improved": improved,
            },
            "artifacts": {
                "direct_callsite_binary": direct.relative_to(Path.cwd()).as_posix(),
                "direct_callsite_bridge_source": (artifact_dir / f"{source_variant}_bridge.cpp").relative_to(Path.cwd()).as_posix(),
                "gpu_library": library.relative_to(Path.cwd()).as_posix(),
                "gpu_library_source": self._gpu_source(root, source_variant, in_count, out_count),
                "systemverilog": systemverilog.relative_to(Path.cwd()).as_posix(),
                "verilator_mdir": mdir.relative_to(Path.cwd()).as_posix(),
            },
        }

    def test_builds_four_complete_metadata_rows(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            summary = {
                "surface": "scientific_circt_hls_mlp_block_variants_summary",
                "variants": [
                    self._variant(root, "mlp4_hls_friendly", "microgpt_mlp_slice", 16, 8, True),
                    self._variant(root, "block2_hls_friendly", "microgpt_block_slice", 24, 4, False),
                    self._variant(root, "inference2_hls_friendly", "microgpt_inference_slice", 8, 6, True),
                ],
            }
            attention = {
                "surface": "scientific_circt_hls_attention_head_variant",
                **self._variant(root, "attention_head4_hls_friendly", "microgpt_attention_head", 80, 16, True),
            }
            combined = metadata.combined_hls_summary(summary, [attention])
            report = metadata.build_source_variant_metadata_report(self._matrix(), combined)

        by_variant = metadata.metadata_rows_by_variant(report)
        self.assertEqual(report["status"], "source_variant_metadata_ready")
        self.assertEqual(report["metadata_complete_count"], 4)
        self.assertEqual(by_variant["attention_head4_hls_friendly"]["layout"]["input"]["bytes_per_state"], 80)
        self.assertEqual(by_variant["mlp4_hls_friendly"]["layout"]["output"]["bytes_per_state"], 64)
        self.assertEqual(by_variant["inference2_hls_friendly"]["entrypoint_kind"], "src-hybrid-verilator")
        self.assertEqual(by_variant["block2_hls_friendly"]["policy"], "fallback_baseline_no_speedup_improvement")
        gate, rejection = metadata.src_hybrid_verilator_bridge_gate(
            self._matrix()["selected_next_source_variant_runtime_boundary"],
            by_variant["inference2_hls_friendly"],
        )
        self.assertIsNone(rejection)
        self.assertEqual(gate["source"], "source_variant_metadata")
        self.assertEqual(gate["run_gpu_outputs_symbol"], "inference2_hls_friendly_run_gpu_outputs")
        self.assertEqual(gate["input_element_count"], 8)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_src_hybrid_bridge_gate_rejects_metadata_symbol_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            summary = {
                "surface": "scientific_circt_hls_mlp_block_variants_summary",
                "variants": [
                    self._variant(root, "inference2_hls_friendly", "microgpt_inference_slice", 8, 6, True),
                ],
            }
            row = metadata.source_variant_metadata_row(self._matrix(), summary, "inference2_hls_friendly")
            row["gpu_symbols"]["run_gpu_outputs"] = "wrong_symbol"
            gate, rejection = metadata.src_hybrid_verilator_bridge_gate(
                self._matrix()["selected_next_source_variant_runtime_boundary"],
                row,
            )

        self.assertEqual(rejection, "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("run_gpu_outputs_symbol", gate["failed_checks"])

    def test_src_hybrid_bridge_gate_rejects_wrong_but_suffix_valid_symbol(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            summary = {
                "surface": "scientific_circt_hls_mlp_block_variants_summary",
                "variants": [
                    self._variant(root, "inference2_hls_friendly", "microgpt_inference_slice", 8, 6, True),
                ],
            }
            row = metadata.source_variant_metadata_row(self._matrix(), summary, "inference2_hls_friendly")
            row["gpu_symbols"]["run_gpu_outputs"] = "mlp4_hls_friendly_run_gpu_outputs"
            gate, rejection = metadata.src_hybrid_verilator_bridge_gate(
                self._matrix()["selected_next_source_variant_runtime_boundary"],
                row,
            )

        self.assertEqual(rejection, "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("run_gpu_outputs_symbol", gate["failed_checks"])

    def test_cli_writes_metadata_report(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            matrix = root / "matrix.json"
            summary = root / "summary.json"
            attention = root / "attention.json"
            out = root / "metadata.json"
            matrix.write_text(json.dumps(self._matrix()), encoding="utf-8")
            summary.write_text(
                json.dumps(
                    {
                        "surface": "scientific_circt_hls_mlp_block_variants_summary",
                        "variants": [
                            self._variant(root, "mlp4_hls_friendly", "microgpt_mlp_slice", 16, 8, True),
                            self._variant(root, "block2_hls_friendly", "microgpt_block_slice", 24, 4, False),
                            self._variant(root, "inference2_hls_friendly", "microgpt_inference_slice", 8, 6, True),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            attention.write_text(
                json.dumps(
                    {
                        "surface": "scientific_circt_hls_attention_head_variant",
                        **self._variant(root, "attention_head4_hls_friendly", "microgpt_attention_head", 80, 16, True),
                    }
                ),
                encoding="utf-8",
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = metadata.main(
                    [
                        "--matrix",
                        matrix.as_posix(),
                        "--hls-variant-report",
                        summary.as_posix(),
                        "--extra-hls-variant-report",
                        attention.as_posix(),
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "source_variant_metadata_ready")
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
