import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from veer_eh_sidecar_executable import (  # noqa: E402
    _decode_observables,
    _hybrid_runtime_command,
    _materialize_root_init_state,
    _process_text,
    _sanitize_process_text,
    _stage_trace_summary,
    _write_clock_reset_patch_script,
    _tail_lines,
    build_bridge_execution_report,
    build_preflight_report,
)


class VeerEhSidecarExecutableTest(HybridCliTestCase):
    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _write_ready_inputs(
        self,
        root: Path,
        target: str,
        design_stem: str,
        *,
        prelaunch_rejection_required: bool = False,
    ) -> None:
        artifact = f"artifacts/rtlmeter_{design_stem}_state_image/{design_stem}_extracted_state_image.json"
        self._write_json(
            root / f"reports/rtlmeter_{design_stem}_state_image_materializer.json",
            {
                "state_image_materialized": True,
                "state_image_artifact": artifact,
                "gpu_execution_claimed": False,
                "timing_measured": False,
            },
        )
        self._write_json(root / artifact, {"target": target})
        self._write_json(
            root / f"reports/rtlmeter_{design_stem}_root_offset_review.json",
            {
                "root_field_offsets_reviewed_for_target": True,
                "reviewed_root_offset_abi": {
                    field: {"offset": index, "size": 4, "name": field}
                    for index, field in enumerate(
                        [
                            "core_clk",
                            "rst_l",
                            "porst_l",
                            "pc",
                            "mcycle",
                            "minstret",
                            "mailbox_write",
                            "mailbox_data",
                            "gpr_debug",
                        ]
                    )
                },
            },
        )
        self._write_json(
            root / f"reports/rtlmeter_{design_stem}_cpu_reference_summary.json",
            {
                "status": "cpu_reference_passed",
                "cpu_reference_ready_for_hybrid_compare": True,
            },
        )
        design_name = "VeeR-EH1" if design_stem == "veer_eh1" else "VeeR-EH2"
        gpu_obj_dir = (
            root
            / f"artifacts/rtlmeter_{design_stem}_cpu_reference_mailbox_public_flat"
            / design_name
            / "default/compile-0/obj_dir"
        )
        (gpu_obj_dir / "vl_batch_gpu.ptx").parent.mkdir(parents=True, exist_ok=True)
        (gpu_obj_dir / "vl_batch_gpu.ptx").write_text("// ptx\n", encoding="utf-8")
        self._write_json(
            gpu_obj_dir / "vl_batch_gpu.meta.json",
            {
                "storage_size": 4096,
                "cubin": "vl_batch_gpu.ptx",
                "hierarchy_state": {
                    "state_image_kind": "root_image",
                    "prelaunch_rejection_required": prelaunch_rejection_required,
                    "unsafe_syms_gep_count": 0 if not prelaunch_rejection_required else 7,
                    "residual_std_tree_detected": True,
                },
            },
        )

    def test_ready_preflight_does_not_claim_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_ready_inputs(root, "rtlmeter_veer_eh1_default_hello", "veer_eh1")

            report = build_preflight_report(root, "rtlmeter_veer_eh1_default_hello")

        self.assertEqual(report["status"], "ready_for_bridge_execution_fail_closed")
        self.assertTrue(report["sidecar_executable_ready_for_bridge"])
        self.assertEqual(report["missing_build_context"], [])
        self.assertEqual(report["root_offset_abi_field_count"], 9)
        self.assertTrue(report["gpu_artifact_ready"])
        self.assertEqual(report["gpu_artifact_storage_size"], 4096)
        self.assertFalse(report["sidecar_bridge_invoked"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["timing_measured"])
        self.assertFalse(report["speedup_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_missing_abi_field_blocks_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_ready_inputs(root, "rtlmeter_veer_eh2_default_hello", "veer_eh2")
            review_path = root / "reports/rtlmeter_veer_eh2_root_offset_review.json"
            review = json.loads(review_path.read_text())
            del review["reviewed_root_offset_abi"]["mailbox_data"]
            self._write_json(review_path, review)

            report = build_preflight_report(root, "rtlmeter_veer_eh2_default_hello")

        self.assertEqual(report["status"], "blocked_missing_eh_sidecar_inputs")
        self.assertFalse(report["sidecar_executable_ready_for_bridge"])
        self.assertIn("mailbox_data_root_offset_abi", report["missing_build_context"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_prelaunch_rejection_blocks_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_ready_inputs(
                root,
                "rtlmeter_veer_eh2_default_hello",
                "veer_eh2",
                prelaunch_rejection_required=True,
            )

            report = build_preflight_report(root, "rtlmeter_veer_eh2_default_hello")

        self.assertEqual(report["status"], "blocked_missing_eh_sidecar_inputs")
        self.assertFalse(report["sidecar_executable_ready_for_bridge"])
        self.assertFalse(report["gpu_artifact_ready"])
        self.assertTrue(report["gpu_artifact_prelaunch_rejection_required"])
        self.assertEqual(
            report["gpu_artifact_prelaunch_blockers"],
            [
                "unsafe_syms_gep_not_covered_by_state_image",
                "root_image_cannot_cover_syms_gep",
                "syms_storage_size_missing_for_auto_promotion",
                "root_offset_in_syms_missing_for_auto_promotion",
                "residual_std_tree_detected",
            ],
        )
        self.assertFalse(report["gpu_artifact_syms_auto_promotion_possible"])
        self.assertEqual(
            report["gpu_artifact_recommended_prelaunch_boundary"],
            "repair_gpu_hierarchy_metadata_or_lowering_before_bridge",
        )
        self.assertIn("gpu_artifact_prelaunch_rejection_required", report["missing_build_context"])
        self.assertIn("gpu_artifact_root_offset_in_syms_missing_for_auto_promotion", report["missing_build_context"])

    def test_prelaunch_rejection_blocks_bridge_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_ready_inputs(
                root,
                "rtlmeter_veer_eh2_default_hello",
                "veer_eh2",
                prelaunch_rejection_required=True,
            )

            report = build_bridge_execution_report(root, "rtlmeter_veer_eh2_default_hello")

        self.assertEqual(report["status"], "blocked_before_bridge_execution")
        self.assertFalse(report["sidecar_bridge_invoked"])
        self.assertFalse(report["sidecar_observables_ready"])
        self.assertIn("gpu_artifact_prelaunch_rejection_required", report["missing_build_context"])

    def test_syms_state_image_uses_root_offset_for_state_patch_and_decode(self) -> None:
        root_abi = {
            "core_clk": {"offset": 0, "size": 1, "name": "core_clk"},
            "rst_l": {"offset": 1, "size": 1, "name": "rst_l"},
            "porst_l": {"offset": 2, "size": 1, "name": "porst_l"},
            "pc": {"offset": 4, "size": 4, "name": "pc"},
            "mcycle": {"offset": 8, "size": 4, "name": "mcycle"},
            "minstret": {"offset": 12, "size": 4, "name": "minstret"},
            "mailbox_write": {"offset": 16, "size": 1, "name": "mailbox_write"},
            "mailbox_data": {"offset": 24, "size": 8, "name": "mailbox_data"},
            "gpr_debug": {"offset": 40, "size": 4, "name": "gpr_debug"},
        }
        meta = {
            "storage_size": 128,
            "hierarchy_state": {
                "state_image_kind": "verilator_syms_image",
                "root_offset_in_state": 16,
            },
        }
        state_image = {
            "sections": {
                "control_scalars": {"core_clk": 1, "rst_l": 0, "porst_l": 0},
                "program_staging_imem": [{"addr": "0x80000000", "byte_hex": "0xaa"}],
            }
        }
        flat_fields = {"tb_top__DOT__imem__DOT__mem": {"offset": 48, "size": 80}}

        blob, materialized = _materialize_root_init_state(
            state_image=state_image,
            meta=meta,
            root_abi=root_abi,
            flat_fields=flat_fields,
        )

        self.assertEqual(materialized["root_offset_in_state"], 16)
        self.assertEqual(blob[16], 1)
        self.assertEqual(blob[17], 0)
        self.assertEqual(blob[18], 0)
        self.assertEqual(blob[16 + 48 + 1], 0xAA)
        with tempfile.TemporaryDirectory() as temp_dir:
            patch_path = Path(temp_dir) / "patch.txt"
            patch = _write_clock_reset_patch_script(
                path=patch_path,
                root_abi=root_abi,
                clock_cycles=1,
                reset_launches=1,
                root_offset=16,
            )
            patch_text = patch_path.read_text(encoding="utf-8")
        self.assertEqual(patch["field_offsets"]["core_clk"], 16)
        self.assertIn("16:0x00 17:0x01 18:0x01", patch_text)

        dumped = bytearray(128)
        dumped[16 + 8 : 16 + 12] = (123).to_bytes(4, "little")
        dumped[16 + 12 : 16 + 16] = (45).to_bytes(4, "little")
        dumped[16 + 24 : 16 + 32] = (0xFF).to_bytes(8, "little")
        observables = _decode_observables(bytes(dumped), root_abi, root_offset=16)
        self.assertEqual(observables["mcycle"], 123)
        self.assertEqual(observables["minstret"], 45)
        self.assertTrue(observables["finish_marker_observed"])

    def test_timeout_diagnostics_preserve_stage_trace_from_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = (
                f"{root}/artifacts/tool_bins/hybrid/run_vl_hybrid\n"
                "run_vl_hybrid: stage=before_cuInit\n"
                "run_vl_hybrid: stage=after_cuInit\n"
                "run_vl_hybrid: stage=before_cuModuleLoad\n"
            ).encode("utf-8")

            text = _sanitize_process_text(_process_text(raw), root)
            trace = _stage_trace_summary(text)

        self.assertNotIn(temp_dir, text)
        self.assertEqual(trace["stage_count"], 3)
        self.assertEqual(trace["last_stage"], "before_cuModuleLoad")
        self.assertEqual(_tail_lines("a\nb\nc\n", max_lines=2), ["b", "c"])

    def test_hybrid_runtime_command_accepts_module_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            override = root / "artifacts" / "entry_pruned.cubin"
            override.parent.mkdir(parents=True)
            override.write_bytes(b"cubin")
            with mock.patch("veer_eh_sidecar_executable.ensure_hybrid_runtime_built"):
                command = _hybrid_runtime_command(
                    repo_root=root,
                    obj_dir=root / "obj_dir",
                    meta={"storage_size": 4096, "cubin": "vl_batch_gpu.ptx"},
                    nstates=1,
                    steps=7,
                    module_override=override,
                )

        self.assertEqual(command[1], override.resolve().as_posix())
        self.assertEqual(command[2:], ["4096", "1", "256", "7"])


if __name__ == "__main__":
    import unittest

    unittest.main()
