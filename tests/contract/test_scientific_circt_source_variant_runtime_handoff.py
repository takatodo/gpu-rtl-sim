import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_runtime_handoff as handoff  # noqa: E402


class ScientificCirctSourceVariantRuntimeHandoffTest(HybridCliTestCase):
    def _matrix(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hybrid_dispatch_matrix",
            "selected_next_source_variant_runtime_boundary": {
                "rank": 3,
                "candidate": "microgpt_inference_slice",
                "source_variant": "inference2_hls_friendly",
                "shape": "1024x1",
                "steps": 1,
                "cpu_owner": "microgpt_token_loop_sampler_and_full_kv_cache_authority",
                "gpu_subsystem": "microgpt_inference_hls_friendly_arithmetic",
                "baseline_speedup": 3.6,
                "variant_speedup": 9.8,
                "speedup_delta": 6.2,
                "selection_reason": "fuller token/cache slice",
            },
        }

    def _summary(self, root: Path) -> dict[str, object]:
        binary = root / "inference2_hls_friendly_direct"
        library = root / "libinference2_hls_friendly_gpu.so"
        binary.write_text("fake", encoding="utf-8")
        library.write_text("fake", encoding="utf-8")
        binary.chmod(0o755)
        library.chmod(0o755)
        return {
            "surface": "scientific_circt_hls_mlp_block_variants_summary",
            "variants": [
                {
                    "variant": "inference2_hls_friendly",
                    "candidate": "microgpt_inference_slice",
                    "shape": "1024x1",
                    "repeat": 5,
                    "inner_repeat": 1000,
                    "integration_batches": 15,
                    "artifacts": {
                        "direct_callsite_binary": binary.as_posix(),
                        "gpu_library": library.as_posix(),
                        "systemverilog": (root / "inference2.sv").as_posix(),
                        "verilator_mdir": (root / "obj_dir").as_posix(),
                    },
                },
            ],
        }

    def _metadata_row(self) -> dict[str, object]:
        return {
            "source_variant": "inference2_hls_friendly",
            "candidate": "microgpt_inference_slice",
            "shape": "1024x1",
            "entrypoint_kind": "src-hybrid-verilator",
            "runtime_boundary_kind": "src_hybrid_verilator_callsite_bridge",
            "policy": "promote_to_hls_gpu",
            "boundary": {
                "candidate": "microgpt_inference_slice",
                "source_variant": "inference2_hls_friendly",
                "shape": "1024x1",
                "steps": 1,
            },
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 8, "bytes_per_state": 8},
                "output": {"element_type": "uint64_t", "element_count": 6, "bytes_per_state": 48},
            },
            "gpu_symbols": {
                "run_gpu_outputs": "inference2_hls_friendly_run_gpu_outputs",
                "run_hybrid_json": "inference2_hls_friendly_run_hybrid_json",
            },
            "metadata_complete": True,
        }

    def test_build_report_measures_selected_boundary(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            self.assertEqual(argv[-4:], ["1024", "5", "1000", "15"])
            return {
                "argv": [handoff._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "status": "hls_variant_measured",
                        "variant": "inference2_hls_friendly",
                        "input_bytes": 8192,
                        "output_bytes": 49152,
                        "mismatch_count": 0,
                        "cpu_vs_gpu_output_equal": True,
                        "cpu_vs_gpu_control_checksum_equal": True,
                        "cpu_ms": 4.0,
                        "gpu_end_to_end_ms": 0.4,
                        "gpu_kernel_ms": 0.1,
                        "bridge_hybrid_wall_ms_per_integration_batch": 0.41,
                        "cpu_to_gpu_end_to_end_speedup": 10.0,
                        "cpu_to_gpu_kernel_speedup": 40.0,
                        "cpu_to_bridge_hybrid_wall_speedup": 9.8,
                    }
                ),
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(handoff, "_run", side_effect=fake_run):
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                self._summary(Path(temp_dir)),
                metadata_row=self._metadata_row(),
            )

        self.assertEqual(report["status"], "runtime_handoff_boundary_measured")
        self.assertEqual(report["source_variant"], "inference2_hls_friendly")
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertTrue(report["cpu_vs_gpu_control_checksum_equal"])
        self.assertTrue(report["selected_speedup_matches_observed"])
        self.assertEqual(report["average"]["cpu_to_bridge_hybrid_wall_speedup"], 9.8)
        self.assertIn("kv_cache_state_authority", report["runtime_boundary"]["cpu_resident_authority"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_no_execute_marks_artifacts_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                self._summary(Path(temp_dir)),
                execute=False,
                metadata_row=self._metadata_row(),
            )

        self.assertEqual(report["status"], "runtime_handoff_artifacts_ready")
        self.assertNotIn("observed", report)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_src_hybrid_verilator_entrypoint_builds_and_measures(self) -> None:
        def fake_verilator_root() -> tuple[Path, None]:
            return Path("/verilator"), None

        def fake_compile(
            source: Path,
            binary: Path,
            mdir: Path,
            verilator_root: Path,
            gate_header: Path | None = None,
        ) -> dict[str, object]:
            self.assertEqual(source.name, "bridge.cpp")
            self.assertEqual(mdir.name, "obj_dir")
            self.assertEqual(verilator_root, Path("/verilator"))
            self.assertIsNotNone(gate_header)
            self.assertEqual(gate_header.name, "scientific_circt_source_variant_bridge_gate.h")
            header = gate_header.read_text(encoding="utf-8")
            self.assertIn("SCI_CIRCT_BRIDGE_EXPECTED_CANDIDATE", header)
            self.assertIn('"microgpt_inference_slice"', header)
            self.assertIn("SCI_CIRCT_BRIDGE_EXPECTED_RUN_GPU_OUTPUTS", header)
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text("fake", encoding="utf-8")
            binary.chmod(0o755)
            return {
                "argv": ["g++", handoff._display_path(source), "-o", handoff._display_path(binary)],
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        def fake_run(argv: list[str]) -> dict[str, object]:
            self.assertTrue(argv[0].endswith("scientific_circt_source_variant_verilator_bridge"))
            self.assertEqual(
                argv[2:11],
                [
                    "microgpt_inference_slice",
                    "inference2_hls_friendly",
                    "1024x1",
                    "inference2_hls_friendly_run_gpu_outputs",
                    "inference2_hls_friendly_run_hybrid_json",
                    "uint8_t",
                    "8",
                    "uint64_t",
                    "6",
                ],
            )
            self.assertEqual(argv[-4:], ["1024", "5", "1000", "15"])
            return {
                "argv": [handoff._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "status": "src_hybrid_verilator_callsite_passed",
                        "entrypoint": "src_hybrid_verilator_callsite",
                        "verilator_callsite_used": True,
                        "cpu_vs_gpu_output_equal": True,
                        "cpu_vs_gpu_control_checksum_equal": True,
                        "cpu_ms": 4.0,
                        "gpu_end_to_end_ms": 0.4,
                        "gpu_kernel_ms": 0.1,
                        "bridge_hybrid_wall_ms_per_integration_batch": 0.42,
                        "cpu_to_gpu_end_to_end_speedup": 10.0,
                        "cpu_to_gpu_kernel_speedup": 40.0,
                        "cpu_to_bridge_hybrid_wall_speedup": 9.5,
                    }
                ),
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(handoff, "_verilator_root", side_effect=fake_verilator_root), \
             mock.patch.object(handoff, "_compile_src_hybrid_bridge", side_effect=fake_compile), \
             mock.patch.object(handoff, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            summary = self._summary(root)
            mdir = root / "obj_dir"
            mdir.mkdir()
            for name in ("Vsim.h", "Vsim__ALL.a", "verilated.o", "verilated_threads.o"):
                (mdir / name).write_text("fake", encoding="utf-8")
            summary["variants"][0]["artifacts"]["verilator_mdir"] = mdir.as_posix()
            bridge = root / "bridge.cpp"
            bridge.write_text("fake", encoding="utf-8")
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                summary,
                entrypoint="src-hybrid-verilator",
                src_hybrid_bridge=bridge,
                src_hybrid_out_dir=root / "out",
                metadata_row=self._metadata_row(),
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_runtime_handoff_measured")
        self.assertEqual(report["entrypoint_kind"], "src-hybrid-verilator")
        self.assertEqual(report["metadata_gate"]["candidate"], "microgpt_inference_slice")
        self.assertEqual(report["metadata_gate"]["source"], "source_variant_metadata")
        self.assertTrue(report["metadata_gate"]["generated_header"]["present"])
        self.assertIsNotNone(report["metadata_gate"]["generated_header"]["path"])
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertEqual(report["average"]["cpu_to_bridge_hybrid_wall_speedup"], 9.5)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_src_hybrid_verilator_rejects_metadata_candidate_mismatch_before_compile(self) -> None:
        metadata = self._metadata_row()
        metadata["candidate"] = "microgpt_mlp_slice"
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(handoff, "_compile_src_hybrid_bridge") as compile_bridge, \
             mock.patch.object(handoff, "_run") as run:
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                self._summary(Path(temp_dir)),
                entrypoint="src-hybrid-verilator",
                metadata_row=metadata,
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("candidate", report["metadata_gate"]["failed_checks"])
        compile_bridge.assert_not_called()
        run.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_src_hybrid_verilator_rejects_layout_mismatch_before_run(self) -> None:
        metadata = self._metadata_row()
        metadata["layout"]["input"]["element_count"] = 16
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(handoff, "_compile_src_hybrid_bridge") as compile_bridge, \
             mock.patch.object(handoff, "_run") as run:
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                self._summary(Path(temp_dir)),
                entrypoint="src-hybrid-verilator",
                metadata_row=metadata,
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("input_layout", report["metadata_gate"]["failed_checks"])
        compile_bridge.assert_not_called()
        run.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_src_hybrid_verilator_rejects_symbol_mismatch_before_run(self) -> None:
        metadata = self._metadata_row()
        metadata["gpu_symbols"]["run_gpu_outputs"] = "wrong_symbol"
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(handoff, "_compile_src_hybrid_bridge") as compile_bridge, \
             mock.patch.object(handoff, "_run") as run:
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                self._summary(Path(temp_dir)),
                entrypoint="src-hybrid-verilator",
                metadata_row=metadata,
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("run_gpu_outputs_symbol", report["metadata_gate"]["failed_checks"])
        compile_bridge.assert_not_called()
        run.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_no_metadata_source_variant_handoff_is_rejected_before_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(handoff, "_run") as run:
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                self._summary(Path(temp_dir)),
                execute=False,
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_metadata_row_missing")
        self.assertIsNone(report["metadata_gate"])
        run.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_selected_hls_shape_mismatch_is_rejected_before_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(handoff, "_run") as run:
            summary = self._summary(Path(temp_dir))
            summary["variants"][0]["shape"] = "2048x1"
            report = handoff.build_runtime_handoff_report(
                self._matrix(),
                summary,
                metadata_row=self._metadata_row(),
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("hls_shape", report["metadata_gate"]["failed_checks"])
        run.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_steps_not_one_is_rejected_before_run(self) -> None:
        matrix = self._matrix()
        matrix["selected_next_source_variant_runtime_boundary"]["steps"] = 2
        metadata = self._metadata_row()
        metadata["boundary"]["steps"] = 2
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(handoff, "_run") as run:
            report = handoff.build_runtime_handoff_report(
                matrix,
                self._summary(Path(temp_dir)),
                metadata_row=metadata,
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("steps", report["metadata_gate"]["failed_checks"])
        self.assertIn("boundary_steps", report["metadata_gate"]["failed_checks"])
        run.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            return {
                "argv": [handoff._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "status": "hls_variant_measured",
                        "cpu_vs_gpu_output_equal": True,
                        "cpu_vs_gpu_control_checksum_equal": True,
                        "cpu_to_bridge_hybrid_wall_speedup": 9.8,
                    }
                ),
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(handoff, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            matrix = root / "matrix.json"
            summary = root / "summary.json"
            out = root / "handoff.json"
            matrix.write_text(json.dumps(self._matrix()), encoding="utf-8")
            summary.write_text(json.dumps(self._summary(root)), encoding="utf-8")
            metadata_report = root / "metadata.json"
            metadata_report.write_text(json.dumps({"rows": [self._metadata_row()]}), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = handoff.main(
                    [
                        "--matrix",
                        matrix.as_posix(),
                        "--hls-variant-report",
                        summary.as_posix(),
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                        "--metadata-report",
                        metadata_report.as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "runtime_handoff_boundary_measured")
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))

    def test_src_hybrid_bridge_uses_verilator_and_inference_symbols(self) -> None:
        source = (
            REPO_ROOT / "src" / "hybrid" / "scientific_circt_source_variant_verilator_bridge.cpp"
        ).read_text(encoding="utf-8")
        self.assertIn("#include \"Vsim.h\"", source)
        self.assertIn("Vsim top", source)
        self.assertIn("top.eval()", source)
        self.assertIn("SCI_CIRCT_BRIDGE_EXPECTED_RUN_GPU_OUTPUTS", source)
        self.assertIn("SCI_CIRCT_BRIDGE_EXPECTED_RUN_HYBRID_JSON", source)
        self.assertIn("failed_metadata_gate", source)
        self.assertIn("metadata_gate_header_missing", source)

    def _matrix_for(self, candidate: str, source_variant: str) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hybrid_dispatch_matrix",
            "selected_next_source_variant_runtime_boundary": {
                "candidate": candidate,
                "source_variant": source_variant,
                "shape": "1024x1",
                "steps": 1,
            },
        }

    def _summary_for(self, root: Path, source_variant: str, candidate: str) -> dict[str, object]:
        binary = root / f"{source_variant}_direct"
        library = root / f"lib{source_variant}_gpu.so"
        binary.write_text("fake", encoding="utf-8")
        library.write_text("fake", encoding="utf-8")
        binary.chmod(0o755)
        library.chmod(0o755)
        return {
            "surface": "scientific_circt_hls_mlp_block_variants_summary",
            "variants": [
                {
                    "variant": source_variant,
                    "candidate": candidate,
                    "shape": "1024x1",
                    "repeat": 5,
                    "inner_repeat": 1000,
                    "integration_batches": 15,
                    "artifacts": {
                        "direct_callsite_binary": binary.as_posix(),
                        "gpu_library": library.as_posix(),
                        "systemverilog": (root / f"{source_variant}.sv").as_posix(),
                        "verilator_mdir": (root / "obj_dir").as_posix(),
                    },
                },
            ],
        }

    def _attention_head4_metadata_row(self) -> dict[str, object]:
        return {
            "source_variant": "attention_head4_hls_friendly",
            "candidate": "microgpt_attention_head",
            "shape": "1024x1",
            "entrypoint_kind": "direct-binary",
            "runtime_boundary_kind": "direct_callsite_hls_source_variant_boundary",
            "policy": "promote_to_hls_gpu",
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 80, "bytes_per_state": 80},
                "output": {"element_type": "uint64_t", "element_count": 16, "bytes_per_state": 128},
            },
            "gpu_symbols": {
                "run_gpu_outputs": "attention_head4_hls_friendly_run_gpu_outputs",
                "run_hybrid_json": "attention_head4_hls_friendly_run_hybrid_json",
            },
            "boundary": {
                "candidate": "microgpt_attention_head",
                "source_variant": "attention_head4_hls_friendly",
                "shape": "1024x1",
                "steps": 1,
            },
            "metadata_complete": True,
        }

    def _mlp4_metadata_row(self) -> dict[str, object]:
        return {
            "source_variant": "mlp4_hls_friendly",
            "candidate": "microgpt_mlp_slice",
            "shape": "1024x1",
            "entrypoint_kind": "direct-binary",
            "runtime_boundary_kind": "direct_callsite_hls_source_variant_boundary",
            "policy": "promote_to_hls_gpu",
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 16, "bytes_per_state": 16},
                "output": {"element_type": "uint64_t", "element_count": 8, "bytes_per_state": 64},
            },
            "gpu_symbols": {
                "run_gpu_outputs": "mlp4_hls_friendly_run_gpu_outputs",
                "run_hybrid_json": "mlp4_hls_friendly_run_hybrid_json",
            },
            "boundary": {
                "candidate": "microgpt_mlp_slice",
                "source_variant": "mlp4_hls_friendly",
                "shape": "1024x1",
                "steps": 1,
            },
            "metadata_complete": True,
        }

    def _block2_metadata_row(self) -> dict[str, object]:
        return {
            "source_variant": "block2_hls_friendly",
            "candidate": "microgpt_block_slice",
            "shape": "1024x1",
            "entrypoint_kind": "fallback-baseline",
            "runtime_boundary_kind": "cpu_or_baseline_fallback",
            "policy": "fallback_baseline_no_speedup_improvement",
            "layout": {
                "input": {"element_type": "uint8_t", "element_count": 24, "bytes_per_state": 24},
                "output": {"element_type": "uint64_t", "element_count": 4, "bytes_per_state": 32},
            },
            "gpu_symbols": {
                "run_gpu_outputs": "block2_hls_friendly_run_gpu_outputs",
                "run_hybrid_json": "block2_hls_friendly_run_hybrid_json",
            },
            "boundary": {
                "candidate": "microgpt_block_slice",
                "source_variant": "block2_hls_friendly",
                "shape": "1024x1",
                "steps": 1,
            },
            "metadata_complete": True,
        }

    def test_attention_head4_gate_accepted_at_no_execute_direct_binary(self) -> None:
        # Under the pre-FC-074 hardcoded inference2-only gate, this row would
        # have been rejected (candidate/source_variant mismatch). The
        # spec-driven gate now accepts any promoted row.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = handoff.build_runtime_handoff_report(
                self._matrix_for("microgpt_attention_head", "attention_head4_hls_friendly"),
                self._summary_for(root, "attention_head4_hls_friendly", "microgpt_attention_head"),
                entrypoint="direct-binary",
                metadata_row=self._attention_head4_metadata_row(),
                execute=False,
            )

        self.assertEqual(report["status"], "runtime_handoff_artifacts_ready")
        self.assertIsNotNone(report["metadata_gate"])
        self.assertEqual(report["metadata_gate"]["source"], "source_variant_metadata")
        self.assertNotIn("failed_checks", report["metadata_gate"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_mlp4_gate_accepted_at_no_execute_direct_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = handoff.build_runtime_handoff_report(
                self._matrix_for("microgpt_mlp_slice", "mlp4_hls_friendly"),
                self._summary_for(root, "mlp4_hls_friendly", "microgpt_mlp_slice"),
                entrypoint="direct-binary",
                metadata_row=self._mlp4_metadata_row(),
                execute=False,
            )

        self.assertEqual(report["status"], "runtime_handoff_artifacts_ready")
        self.assertIsNotNone(report["metadata_gate"])
        self.assertEqual(report["metadata_gate"]["source"], "source_variant_metadata")
        self.assertNotIn("failed_checks", report["metadata_gate"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_block2_gate_rejected_before_dlopen(self) -> None:
        # block2 is fallback-baseline (not promoted): the metadata gate must
        # reject it before dlopen/execution regardless of entrypoint kind.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = handoff.build_runtime_handoff_report(
                self._matrix_for("microgpt_block_slice", "block2_hls_friendly"),
                self._summary_for(root, "block2_hls_friendly", "microgpt_block_slice"),
                entrypoint="direct-binary",
                metadata_row=self._block2_metadata_row(),
                execute=False,
            )

        self.assertEqual(report["status"], "src_hybrid_verilator_metadata_gate_rejected")
        self.assertIn("entrypoint_kind", report["metadata_gate"]["failed_checks"])
        self.assertIn("policy", report["metadata_gate"]["failed_checks"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
