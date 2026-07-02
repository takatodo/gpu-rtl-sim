import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVortexPtxEntrySliceTest(HybridCliTestCase):
    def test_writes_single_entry_slice_without_runtime_claims(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_entry_slice import build_slice

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "artifacts" / "obj" / "vl_batch_gpu.ptx"
            out = root / "artifacts" / "slice" / "vl_eval_batch_gpu.ptx"
            source.parent.mkdir(parents=True)
            source.write_text(
                "\n".join(
                    [
                        ".version 8.0",
                        ".target sm_89",
                        ".address_size 64",
                        ".func helper() { ret; }",
                        ".visible .entry vl_eval_batch_gpu() {",
                        "ret;",
                        "}",
                        ".visible .entry huge_unused_gpu() {",
                        "ret;",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = build_slice(root, ptx_path=source, out_path=out, write_slice=True)
            sliced = out.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "entry_slice_written")
        self.assertEqual(report["source_entry_count"], 2)
        self.assertEqual(report["removed_entry_count"], 1)
        self.assertEqual(report["target_entry_line_count"], 3)
        self.assertIn(".func helper", sliced)
        self.assertIn(".visible .entry vl_eval_batch_gpu", sliced)
        self.assertNotIn("huge_unused_gpu", sliced)
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["kernel_execution_observed"])
        self.assertFalse(report["timing_measured"])
        self.assertIn("entry_slice_is_not_kernel_execution", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_reports_missing_entry(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_entry_slice import build_slice

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            source.write_text(".visible .entry other_gpu() {\nret;\n}\n", encoding="utf-8")
            report = build_slice(root, ptx_path=source, entry="missing_gpu")

        self.assertEqual(report["status"], "entry_missing")
        self.assertEqual(report["available_entries"], ["other_gpu"])
        self.assertFalse(report["slice_written"])

    def test_prunes_unreferenced_funcs_when_requested(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_entry_slice import build_slice

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out = root / "slice.ptx"
            source.write_text(
                "\n".join(
                    [
                        ".version 8.0",
                        ".target sm_89",
                        ".address_size 64",
                        ".func used_helper() {",
                        "ret;",
                        "}",
                        ".func unused_helper() {",
                        "ret;",
                        "}",
                        ".visible .entry vl_eval_batch_gpu() {",
                        "call.uni",
                        "used_helper,",
                        "();",
                        "ret;",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = build_slice(
                root,
                ptx_path=source,
                out_path=out,
                prune_unreferenced_funcs=True,
                write_slice=True,
            )
            sliced = out.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "entry_slice_written")
        self.assertTrue(report["prune_unreferenced_funcs"])
        self.assertEqual(report["removed_func_count"], 1)
        self.assertIn(".func used_helper", sliced)
        self.assertNotIn("unused_helper", sliced)

    def test_does_not_treat_func_declarations_as_bodies(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_entry_slice import build_slice

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out = root / "slice.ptx"
            source.write_text(
                "\n".join(
                    [
                        ".version 8.0",
                        ".target sm_89",
                        ".address_size 64",
                        ".visible .func declared_helper",
                        "(",
                        "  .param .b64 declared_helper_param_0",
                        ")",
                        ";",
                        ".global .align 1 .b8 huge_const[4] = {1, 2, 3, 4};",
                        ".visible .func (.param .b64 func_retval0) real_helper() {",
                        "ret;",
                        "}",
                        ".visible .entry vl_eval_batch_gpu() {",
                        "ret;",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = build_slice(
                root,
                ptx_path=source,
                out_path=out,
                prune_unreferenced_funcs=True,
                write_slice=True,
            )
            sliced = out.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "entry_slice_written")
        self.assertEqual(report["source_func_count"], 1)
        self.assertEqual(report["removed_func_count"], 1)
        self.assertEqual(report["removed_func_declaration_count"], 1)
        self.assertIn("huge_const", sliced)
        self.assertNotIn("declared_helper_param_0", sliced)
        self.assertNotIn("real_helper", sliced)

    def test_can_stub_reachable_func_for_ptxas_surface_diagnosis(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_entry_slice import build_slice

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out = root / "slice.ptx"
            source.write_text(
                "\n".join(
                    [
                        ".version 8.0",
                        ".target sm_89",
                        ".address_size 64",
                        ".visible .func huge_helper() {",
                        "add.u64 %rd1, %rd2, %rd3;",
                        "ret;",
                        "}",
                        ".visible .entry vl_eval_batch_gpu() {",
                        "call.uni",
                        "huge_helper,",
                        "();",
                        "ret;",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = build_slice(
                root,
                ptx_path=source,
                out_path=out,
                prune_unreferenced_funcs=True,
                stub_funcs=["huge_helper"],
                write_slice=True,
            )
            sliced = out.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "entry_slice_written")
        self.assertEqual(report["stub_func_count"], 1)
        self.assertEqual(report["stub_func_names"], ["huge_helper"])
        self.assertIn(".visible .func huge_helper", sliced)
        self.assertIn("call.uni", sliced)
        self.assertNotIn("add.u64", sliced)
        self.assertIn("\tret;\n}\n", sliced)

    def test_writes_multi_entry_slice_for_patch_and_eval(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vortex_ptx_entry_slice import build_slice

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out = root / "slice.ptx"
            source.write_text(
                "\n".join(
                    [
                        ".version 8.0",
                        ".target sm_89",
                        ".address_size 64",
                        ".visible .entry vl_apply_patch_schedule_gpu() {",
                        "ret;",
                        "}",
                        ".visible .entry vl_eval_batch_gpu() {",
                        "ret;",
                        "}",
                        ".visible .entry unused_gpu() {",
                        "ret;",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            report = build_slice(
                root,
                ptx_path=source,
                out_path=out,
                keep_entries=["vl_apply_patch_schedule_gpu", "vl_eval_batch_gpu"],
                surface="rtlmeter_veer_eh2_ptx_entry_slice",
                case="VeeR-EH2:default:hello",
                next_required_boundary="run_bounded_ptxas_probe_on_veer_eh2_entry_slice",
                write_slice=True,
            )
            sliced = out.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "entry_slice_written")
        self.assertEqual(report["surface"], "rtlmeter_veer_eh2_ptx_entry_slice")
        self.assertEqual(report["case"], "VeeR-EH2:default:hello")
        self.assertEqual(report["kept_entry_count"], 2)
        self.assertEqual(report["removed_entry_count"], 1)
        self.assertIn(".visible .entry vl_apply_patch_schedule_gpu", sliced)
        self.assertIn(".visible .entry vl_eval_batch_gpu", sliced)
        self.assertNotIn("unused_gpu", sliced)
        self.assertEqual(
            report["next_required_boundary"],
            "run_bounded_ptxas_probe_on_veer_eh2_entry_slice",
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report_and_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vl_batch_gpu.ptx"
            out = root / "slice.ptx"
            report_out = root / "reports" / "slice.json"
            source.write_text(
                ".version 8.0\n.visible .entry vl_eval_batch_gpu() {\nret;\n}\n",
                encoding="utf-8",
            )
            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_ptx_entry_slice.py",
                "--repo-root",
                root.as_posix(),
                "--ptx",
                source.relative_to(root).as_posix(),
                "--out",
                out.relative_to(root).as_posix(),
                "--write-slice",
                "--write-report",
                "--report-out",
                report_out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(report_out.read_text(encoding="utf-8"))
            slice_exists = out.is_file()

        self.assertEqual(stdout_payload, report_payload)
        self.assertTrue(slice_exists)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_ptx_entry_slice")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
