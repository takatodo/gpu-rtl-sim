import json
import stat
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


ENTRY_NAMES = [
    "vl_eval_batch_gpu",
    "vl_apply_patch_schedule_gpu",
    "vl_apply_feedback_edges_gpu",
    "vl_apply_feedback_increments_gpu",
    "vl_apply_feedback_sets_gpu",
    "vl_apply_feedback_combined_gpu",
    "vl_patch_eval_batch_gpu",
    "vl_patch_eval_pair_cycle_batch_gpu",
    "vl_patch_eval_pair_cycle_loop_batch_gpu",
    "vl_probe_u64_load_gpu",
    "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu",
    "unused_gpu",
]


def write_source_ptx(path: Path) -> None:
    lines = [".version 8.0", ".target sm_89", ".address_size 64"]
    for name in ENTRY_NAMES:
        lines.extend([f".visible .entry {name}() {{", "ret;", "}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class GateGptEntrySlicedCubinChainTest(HybridCliTestCase):
    def test_regenerates_three_ptx_slices_without_runtime_claims(self) -> None:
        self.add_tools_to_path()
        from gategpt_entry_sliced_cubin_chain import regenerate_chain

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "artifacts" / "gategpt_local_eval" / "gateGPT" / "obj_tb_core" / "vl_batch_gpu.ptx"
            out_dir = root / "artifacts" / "gategpt_tb_core_ptx_entry_slice"
            write_source_ptx(source)

            report = regenerate_chain(
                root,
                source_ptx=source,
                out_dir=out_dir,
                run_ptxas=False,
            )
            support = (out_dir / "vl_eval_patch_feedback_support.ptx").read_text(
                encoding="utf-8"
            )
            feedback = (out_dir / "vl_feedback_pair_cycle_loop.ptx").read_text(
                encoding="utf-8"
            )
            token_loop = (
                out_dir / "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu.ptx"
            ).read_text(encoding="utf-8")

        self.assertEqual(
            report["status"], "entry_sliced_ptx_chain_regenerated_ptxas_not_run"
        )
        self.assertEqual(report["slice_count"], 3)
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["kernel_execution_observed"])
        self.assertFalse(report["timing_measured"])
        self.assertFalse(report["speedup_claimed"])
        self.assertFalse(report["usefulness_claimed"])
        self.assertNotIn("vl_eval_batch_gpu", support)
        self.assertIn("vl_apply_feedback_increments_gpu", support)
        self.assertNotIn("vl_apply_feedback_sets_gpu", support)
        self.assertIn("vl_apply_feedback_sets_gpu", feedback)
        self.assertNotIn("vl_patch_eval_pair_cycle_loop_batch_gpu", feedback)
        self.assertNotIn("vl_eval_batch_gpu", feedback)
        self.assertIn("vl_tb_core_ordering_aware_phase_resident_token_loop_gpu", token_loop)
        self.assertIn("vl_eval_batch_gpu", token_loop)
        self.assertIn("vl_probe_u64_load_gpu", token_loop)
        self.assertIn("vl_patch_eval_pair_cycle_batch_gpu", token_loop)
        self.assertIn("vl_patch_eval_pair_cycle_loop_batch_gpu", token_loop)
        self.assertNotIn("unused_gpu", token_loop)
        self.assertIn(
            "entry_slice_regeneration_is_not_kernel_execution",
            report["non_claims"],
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_regenerates_cubins_with_bounded_ptxas(self) -> None:
        self.add_tools_to_path()
        from gategpt_entry_sliced_cubin_chain import regenerate_chain

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out_dir = root / "slice"
            fake_ptxas = root / "fake_ptxas"
            write_source_ptx(source)
            fake_ptxas.write_text(
                "#!/usr/bin/env sh\n"
                "out=''\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  if [ \"$1\" = '-o' ]; then shift; out=\"$1\"; fi\n"
                "  shift\n"
                "done\n"
                "printf cubin > \"$out\"\n",
                encoding="utf-8",
            )
            fake_ptxas.chmod(fake_ptxas.stat().st_mode | stat.S_IXUSR)

            report = regenerate_chain(
                root,
                source_ptx=source,
                out_dir=out_dir,
                ptxas=fake_ptxas.as_posix(),
                run_ptxas=True,
                ptxas_timeout_seconds=5.0,
            )

        self.assertEqual(report["status"], "entry_sliced_cubin_chain_regenerated")
        self.assertTrue(all(item["ptxas"]["cubin_exists"] for item in report["slices"]))
        self.assertEqual(
            [item["ptxas"]["status"] for item in report["slices"]],
            ["ptxas_passed", "ptxas_passed", "ptxas_passed"],
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_reuses_existing_cubin_when_slice_content_is_unchanged(self) -> None:
        self.add_tools_to_path()
        from gategpt_entry_sliced_cubin_chain import regenerate_chain

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out_dir = root / "slice"
            call_log = root / "ptxas_calls.txt"
            fake_ptxas = root / "fake_ptxas"
            write_source_ptx(source)
            fake_ptxas.write_text(
                "#!/usr/bin/env sh\n"
                f"printf 'called\\n' >> {call_log.as_posix()!r}\n"
                "out=''\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  if [ \"$1\" = '-o' ]; then shift; out=\"$1\"; fi\n"
                "  shift\n"
                "done\n"
                "printf cubin > \"$out\"\n",
                encoding="utf-8",
            )
            fake_ptxas.chmod(fake_ptxas.stat().st_mode | stat.S_IXUSR)

            first = regenerate_chain(
                root,
                source_ptx=source,
                out_dir=out_dir,
                ptxas=fake_ptxas.as_posix(),
                run_ptxas=True,
                ptxas_timeout_seconds=5.0,
            )
            second = regenerate_chain(
                root,
                source_ptx=source,
                out_dir=out_dir,
                ptxas=fake_ptxas.as_posix(),
                run_ptxas=True,
                ptxas_timeout_seconds=5.0,
            )
            call_count = len(call_log.read_text(encoding="utf-8").splitlines())

        self.assertEqual(first["status"], "entry_sliced_cubin_chain_regenerated")
        self.assertEqual(second["status"], "entry_sliced_cubin_chain_regenerated")
        self.assertEqual(call_count, 3)
        self.assertEqual(
            [item["ptxas"]["status"] for item in second["slices"]],
            [
                "ptxas_reused_existing_cubin",
                "ptxas_reused_existing_cubin",
                "ptxas_reused_existing_cubin",
            ],
        )
        self.assertTrue(
            all(
                item["slice"]["existing_slice_content_unchanged"]
                for item in second["slices"]
            )
        )
        self.assert_no_local_absolute_paths(json.dumps(second, sort_keys=True))

    def test_cli_writes_report_and_slices(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out_dir = root / "slice"
            report_out = root / "reports" / "gategpt_slices.json"
            write_source_ptx(source)

            result = self.run_python_tool(
                "src/tools/gategpt_entry_sliced_cubin_chain.py",
                "--repo-root",
                root.as_posix(),
                "--ptx",
                source.relative_to(root).as_posix(),
                "--out-dir",
                out_dir.relative_to(root).as_posix(),
                "--skip-ptxas",
                "--write-report",
                "--report-out",
                report_out.relative_to(root).as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(report_out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(
            report_payload["status"],
            "entry_sliced_ptx_chain_regenerated_ptxas_not_run",
        )
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
