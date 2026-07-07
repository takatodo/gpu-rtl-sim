import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_runtime_dispatcher as dispatcher  # noqa: E402


class ScientificCirctSourceVariantRuntimeDispatcherTest(HybridCliTestCase):
    def _matrix(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hybrid_dispatch_matrix",
            "selected_next_source_variant_runtime_boundary": {
                "candidate": "microgpt_inference_slice",
                "source_variant": "inference2_hls_friendly",
                "shape": "1024x1",
                "rank": 3,
                "selection_reason": "fuller token/cache slice",
            },
            "source_variant_runtime_integration_queue": [
                {
                    "candidate": "microgpt_attention_head",
                    "source_variant": "attention_head4_hls_friendly",
                    "shape": "1024x1",
                    "rank": 1,
                    "variant_speedup": 13.3,
                },
                {
                    "candidate": "microgpt_mlp_slice",
                    "source_variant": "mlp4_hls_friendly",
                    "shape": "1024x1",
                    "rank": 2,
                    "variant_speedup": 9.9,
                },
                {
                    "candidate": "microgpt_inference_slice",
                    "source_variant": "inference2_hls_friendly",
                    "shape": "1024x1",
                    "rank": 3,
                    "variant_speedup": 9.8,
                },
            ],
        }

    def _summary(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hls_mlp_block_variants_summary",
            "variants": [
                {
                    "variant": "block2_hls_friendly",
                    "candidate": "microgpt_block_slice",
                    "shape": "1024x1",
                    "status": "hls_variant_measured_no_speedup_improvement",
                    "comparison": {"baseline_speedup": 5.7, "variant_speedup": 5.5, "speedup_improved": False},
                }
            ],
        }

    def _metadata_row(
        self,
        source_variant: str,
        candidate: str,
        entrypoint: str,
        runtime_boundary_kind: str,
        policy: str,
    ) -> dict[str, object]:
        return {
            "source_variant": source_variant,
            "candidate": candidate,
            "shape": "1024x1",
            "entrypoint_kind": entrypoint,
            "runtime_boundary_kind": runtime_boundary_kind,
            "policy": policy,
            "boundary": {
                "candidate": candidate,
                "source_variant": source_variant,
                "shape": "1024x1",
                "rank": 1,
                "steps": 1,
                "variant_speedup": 9.9,
            },
            "artifacts": {
                "src_hybrid_bridge_source": {
                    "path": "src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp",
                    "present": True,
                },
                "src_hybrid_out_dir": {
                    "path": "artifacts/scientific_circt/source_variant_verilator_entrypoint",
                    "present": True,
                },
            },
            "layout": {
                "input": {"struct": "In", "element_type": "uint8_t", "element_count": 8, "bytes_per_state": 8},
                "output": {"struct": "Out", "element_type": "uint64_t", "element_count": 6, "bytes_per_state": 48},
            },
            "gpu_symbols": {
                "run_gpu_outputs": f"{source_variant}_run_gpu_outputs",
                "run_hybrid_json": f"{source_variant}_run_hybrid_json",
            },
            "metadata_complete": True,
            "fallback_reason": "source_variant_is_equality_checked_but_does_not_improve_baseline_speedup"
            if entrypoint == "fallback-baseline"
            else None,
        }

    def _metadata(self) -> dict[str, object]:
        rows = [
            self._metadata_row(
                "attention_head4_hls_friendly",
                "microgpt_attention_head",
                "direct-binary",
                "direct_callsite_hls_source_variant_boundary",
                "promote_to_hls_gpu",
            ),
            self._metadata_row(
                "mlp4_hls_friendly",
                "microgpt_mlp_slice",
                "direct-binary",
                "direct_callsite_hls_source_variant_boundary",
                "promote_to_hls_gpu",
            ),
            self._metadata_row(
                "inference2_hls_friendly",
                "microgpt_inference_slice",
                "src-hybrid-verilator",
                "src_hybrid_verilator_callsite_bridge",
                "promote_to_hls_gpu",
            ),
            self._metadata_row(
                "block2_hls_friendly",
                "microgpt_block_slice",
                "fallback-baseline",
                "cpu_or_baseline_fallback",
                "fallback_baseline_no_speedup_improvement",
            ),
        ]
        return {
            "surface": "scientific_circt_source_variant_metadata",
            "status": "source_variant_metadata_ready",
            "requested_source_variants": [row["source_variant"] for row in rows],
            "rows": rows,
        }

    def test_dispatch_invokes_registered_runtime_boundary(self) -> None:
        handoff = {
            "status": "src_hybrid_verilator_runtime_handoff_measured",
            "source_variant": "inference2_hls_friendly",
            "entrypoint_kind": "src-hybrid-verilator",
            "cpu_vs_gpu_output_equal": True,
            "cpu_vs_gpu_control_checksum_equal": True,
            "average": {"cpu_to_bridge_hybrid_wall_speedup": 9.9},
        }
        with mock.patch.object(dispatcher, "build_runtime_handoff_report", return_value=handoff) as build:
            report = dispatcher.dispatch_source_variant_runtime(self._matrix(), self._summary(), metadata=self._metadata())

        self.assertEqual(report["status"], "runtime_dispatch_measured")
        self.assertEqual(report["runtime_handoff"], handoff)
        self.assertEqual(report["entrypoint"], "src-hybrid-verilator")
        self.assertEqual(report["source_metadata_status"], "source_variant_metadata_ready")
        self.assertEqual(report["selected_boundary"]["source_variant"], "inference2_hls_friendly")
        build.assert_called_once()
        self.assertEqual(build.call_args.kwargs["metadata_row"]["source_variant"], "inference2_hls_friendly")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_dispatch_invokes_registered_non_selected_promoted_boundary(self) -> None:
        handoff = {
            "status": "runtime_handoff_boundary_measured",
            "source_variant": "mlp4_hls_friendly",
            "entrypoint_kind": "direct-binary",
            "cpu_vs_gpu_output_equal": True,
            "cpu_vs_gpu_control_checksum_equal": True,
            "average": {"cpu_to_bridge_hybrid_wall_speedup": 9.9},
        }
        with mock.patch.object(dispatcher, "build_runtime_handoff_report", return_value=handoff) as build:
            report = dispatcher.dispatch_source_variant_runtime(
                self._matrix(),
                self._summary(),
                source_variant="mlp4_hls_friendly",
                execute=False,
                metadata=self._metadata(),
            )

        self.assertEqual(report["status"], "runtime_dispatch_measured")
        self.assertEqual(report["dispatch_boundary"]["source_variant"], "mlp4_hls_friendly")
        self.assertEqual(report["entrypoint"], "direct-binary")
        build.assert_called_once()
        self.assertEqual(build.call_args.kwargs["metadata_row"]["source_variant"], "mlp4_hls_friendly")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_rejects_unknown_variant(self) -> None:
        report = dispatcher.dispatch_source_variant_runtime(
            self._matrix(),
            self._summary(),
            source_variant="unknown_hls_friendly",
            execute=False,
            metadata=self._metadata(),
        )

        self.assertEqual(report["status"], "dispatcher_rejected_unknown_source_variant")
        self.assertEqual(report["reason"], "requested_source_variant_not_found_in_dispatch_matrix_or_hls_summary")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_fallback_baseline_for_non_improving_variant(self) -> None:
        report = dispatcher.dispatch_source_variant_runtime(
            self._matrix(),
            self._summary(),
            source_variant="block2_hls_friendly",
            execute=False,
            metadata=self._metadata(),
        )

        self.assertEqual(report["status"], "runtime_dispatch_fallback_baseline")
        self.assertEqual(report["runtime_boundary_kind"], "cpu_or_baseline_fallback")
        self.assertEqual(report["policy"], "fallback_baseline_no_speedup_improvement")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_dispatch_all_known_source_variants(self) -> None:
        def handoff(*args, selected_boundary=None, entrypoint=None, **kwargs):
            return {
                "status": "src_hybrid_verilator_runtime_handoff_measured"
                if entrypoint == "src-hybrid-verilator"
                else "runtime_handoff_boundary_measured",
                "source_variant": selected_boundary["source_variant"],
                "entrypoint_kind": entrypoint,
                "cpu_vs_gpu_output_equal": True,
                "cpu_vs_gpu_control_checksum_equal": True,
            }

        with mock.patch.object(dispatcher, "build_runtime_handoff_report", side_effect=handoff):
            report = dispatcher.dispatch_all_source_variant_runtimes(
                self._matrix(),
                self._summary(),
                execute=False,
                metadata=self._metadata(),
            )

        self.assertEqual(report["status"], "multi_source_variant_dispatch_ready")
        self.assertEqual(report["measured_count"], 3)
        self.assertEqual(report["fallback_count"], 1)
        self.assertEqual(report["source_metadata_status"], "source_variant_metadata_ready")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_rejects_metadata_boundary_policy_mismatch(self) -> None:
        metadata = self._metadata()
        metadata["rows"][2]["shape"] = "256x1"
        report = dispatcher.dispatch_source_variant_runtime(
            self._matrix(),
            self._summary(),
            execute=False,
            metadata=metadata,
        )

        self.assertEqual(report["status"], "dispatcher_rejected_policy_mismatch")
        self.assertEqual(report["reason"], "metadata_boundary_does_not_match_selection_matrix_candidate_or_shape")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_rejects_entrypoint_runtime_boundary_kind_mismatch_before_handoff(self) -> None:
        metadata = self._metadata()
        metadata["rows"][2]["runtime_boundary_kind"] = "direct_callsite_hls_source_variant_boundary"
        with mock.patch.object(dispatcher, "build_runtime_handoff_report") as build:
            report = dispatcher.dispatch_source_variant_runtime(
                self._matrix(),
                self._summary(),
                execute=False,
                metadata=metadata,
            )

        self.assertEqual(report["status"], "dispatcher_rejected_policy_mismatch")
        self.assertEqual(report["reason"], "metadata_entrypoint_and_runtime_boundary_kind_do_not_match")
        build.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_rejects_incomplete_metadata_before_handoff(self) -> None:
        metadata = self._metadata()
        metadata["rows"][2]["metadata_complete"] = False
        with mock.patch.object(dispatcher, "build_runtime_handoff_report") as build:
            report = dispatcher.dispatch_source_variant_runtime(
                self._matrix(),
                self._summary(),
                execute=False,
                metadata=metadata,
            )

        self.assertEqual(report["status"], "dispatcher_rejected_incomplete_metadata")
        self.assertEqual(report["reason"], "metadata_row_is_not_complete_for_runtime_dispatch")
        build.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cpu_fallback_for_unsupported_requested_shape(self) -> None:
        with mock.patch.object(dispatcher, "build_runtime_handoff_report") as build:
            report = dispatcher.dispatch_source_variant_runtime(
                self._matrix(),
                self._summary(),
                shape="256x1",
                execute=False,
                metadata=self._metadata(),
            )

        self.assertEqual(report["status"], "runtime_dispatch_cpu_fallback_unsupported_shape")
        self.assertEqual(report["reason"], "requested_shape_not_in_measured_source_variant_boundary")
        self.assertTrue(report["cpu_fallback"])
        self.assertEqual(report["supported_shape"], "1024x1")
        build.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cpu_fallback_for_unsupported_requested_steps(self) -> None:
        with mock.patch.object(dispatcher, "build_runtime_handoff_report") as build:
            report = dispatcher.dispatch_source_variant_runtime(
                self._matrix(),
                self._summary(),
                steps=2,
                execute=False,
                metadata=self._metadata(),
            )

        self.assertEqual(report["status"], "runtime_dispatch_cpu_fallback_unsupported_steps")
        self.assertEqual(report["reason"], "requested_steps_not_in_measured_source_variant_boundary")
        self.assertTrue(report["cpu_fallback"])
        self.assertEqual(report["supported_steps"], 1)
        build.assert_not_called()
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_dispatch_report(self) -> None:
        handoff = {
            "status": "src_hybrid_verilator_runtime_handoff_measured",
            "source_variant": "inference2_hls_friendly",
            "entrypoint_kind": "src-hybrid-verilator",
            "cpu_vs_gpu_output_equal": True,
            "cpu_vs_gpu_control_checksum_equal": True,
        }
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(dispatcher, "build_runtime_handoff_report", return_value=handoff):
            root = Path(temp_dir)
            matrix = root / "matrix.json"
            summary = root / "summary.json"
            metadata = root / "metadata.json"
            out = root / "dispatch.json"
            matrix.write_text(json.dumps(self._matrix()), encoding="utf-8")
            summary.write_text(json.dumps(self._summary()), encoding="utf-8")
            metadata.write_text(json.dumps(self._metadata()), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = dispatcher.main(
                    [
                        "--matrix",
                        matrix.as_posix(),
                        "--hls-variant-report",
                        summary.as_posix(),
                        "--metadata-report",
                        metadata.as_posix(),
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "runtime_dispatch_measured")
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
