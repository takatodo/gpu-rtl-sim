import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_veer_family_surface_audit import (  # noqa: E402
    build_root_offset_review_payload,
    build_audit,
    write_authorities,
    write_root_offset_reviews,
    write_sidecar_bridge_preflights,
    write_sidecar_executable_reviews,
    write_state_images,
    write_state_layout_preflights,
)


class RtlmeterVeerFamilySurfaceAuditTest(HybridCliTestCase):
    def _write_descriptor(self, root: Path, design: str, *, program: str = "tests/hello/program.hex") -> None:
        path = root / "third_party" / "rtlmeter" / "designs" / design / "descriptor.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        source_prefix = {
            "VeeR-EH1": "",
            "VeeR-EH2": "eh2_",
            "VeeR-EL2": "el2_",
        }[design]
        core_source = "veer.sv" if not source_prefix else f"{source_prefix}veer.sv"
        wrapper = "veer_wrapper.sv" if design != "VeeR-EH2" else "eh2_veer_wrapper.sv"
        path.write_text(
            "\n".join(
                [
                    "compile:",
                    "  verilogSourceFiles:",
                    f"    - src/{wrapper}",
                    f"    - src/{core_source}",
                    "    - src/tb_top.sv",
                    "  verilogIncludeFiles:",
                    "    - src/dasm.svi",
                    "  topModule: tb_top",
                    "  mainClock: tb_top.core_clk",
                    "execute:",
                    "  tests:",
                    "    hello:",
                    "      files:",
                    f"        - {program}",
                    "configurations:",
                    "  default:",
                    "    compile:",
                    "      verilogIncludeFiles:",
                    "        - src/default/common_defines.vh",
                    "    execute:",
                    "      tests:",
                    "        hello:",
                    "          tags: [ sanity ]",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        design_root = path.parent
        for rel in [
            f"src/{wrapper}",
            f"src/{core_source}",
            "src/tb_top.sv",
            "src/dasm.svi",
            "src/default/common_defines.vh",
            program,
        ]:
            file_path = design_root / rel
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.name == "tb_top.sv":
                wrapper_instance = "rvtop_wrapper" if design == "VeeR-EL2" else "rvtop"
                file_path.write_text(
                    "\n".join(
                        [
                            "module tb_top;",
                            "bit core_clk;",
                            "logic mailbox_write;",
                            '$readmemh("program.hex", lmem.mem);',
                            "always @(negedge core_clk) begin",
                            "  if (mailbox_write && WriteData[7:0] == 8'h1) $write(\"TEST PASSED\");",
                            "end",
                            f"veer_wrapper {wrapper_instance} ();",
                            "endmodule",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            elif file_path.name == "program.hex":
                file_path.write_text("@00000000\n73 10 20 B0\n", encoding="utf-8")
            else:
                file_path.write_text("// fixture\n", encoding="utf-8")

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _write_root_header(self, root: Path, design: str, body: str, *, variant: str = "default") -> None:
        stem = design.lower().replace("-", "_")
        work_root = (
            f"artifacts/rtlmeter_{stem}_cpu_reference_mailbox_public_flat"
            if variant == "mailbox_public_flat"
            else f"artifacts/rtlmeter_{stem}_cpu_reference"
        )
        path = (
            root
            / work_root
            / design
            / "default/compile-0/obj_dir/Vsim___024root.h"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def test_audit_marks_eh_ready_to_port_but_missing_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            self._write_json(root / "config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json", {})
            self._write_json(root / "reports/rtlmeter_veer_el2_state_layout_inspection.json", {})
            self._write_json(root / "reports/rtlmeter_veer_el2_state_image_materializer.json", {})
            self._write_json(root / "reports/rtlmeter_veer_el2_sidecar_bridge.json", {})
            self._write_json(root / "reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json", {})

            report = build_audit(root)

        rows = {row["design"]: row for row in report["rows"]}
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(rows["VeeR-EH1"]["ready_to_port_from_descriptor"])
        self.assertTrue(rows["VeeR-EH2"]["ready_to_port_from_descriptor"])
        self.assertFalse(rows["VeeR-EH1"]["hybrid_measured"])
        self.assertFalse(rows["VeeR-EH2"]["hybrid_measured"])
        self.assertTrue(rows["VeeR-EL2"]["hybrid_measured"])
        self.assertIn("authority", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("el2_state_layout_and_root_symbol_paths_are_fixed", rows["VeeR-EH2"]["direct_el2_reuse_blockers"])
        self.assertIn("hello_program_sha256_differs_from_el2", rows["VeeR-EH1"]["direct_el2_reuse_blockers"])
        self.assertTrue(report["summary"]["eh1_ready_to_port_from_descriptor"])
        self.assertTrue(report["summary"]["eh2_ready_to_port_from_descriptor"])
        self.assertFalse(report["summary"]["eh1_hybrid_measured"])
        self.assertFalse(report["summary"]["eh2_hybrid_measured"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_markdown_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            out = root / "reports" / "audit.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_veer_family_surface_audit.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
                "--markdown",
            )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertIn("| Design | Status | Portable descriptor |", result.stdout)
        self.assertEqual(payload["surface"], "rtlmeter_veer_family_surface_audit")
        self.assert_no_local_absolute_paths(result.stdout)

    def test_write_authorities_creates_fail_closed_reviewed_registry_entries(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_authority_registry import reviewed_registry_source_closure

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)

            written = write_authorities(root)
            report = build_audit(root)

            eh1_path = root / "config/rtlmeter_sidecar_authorities/rtlmeter_veer_eh1_default_hello.json"
            eh2_path = root / "config/rtlmeter_sidecar_authorities/rtlmeter_veer_eh2_default_hello.json"
            eh1 = json.loads(eh1_path.read_text(encoding="utf-8"))
            eh2 = json.loads(eh2_path.read_text(encoding="utf-8"))
            closure = reviewed_registry_source_closure(
                "config/rtlmeter_sidecar_authorities/rtlmeter_veer_eh1_default_hello.json",
                repo_root=root,
                target="rtlmeter_veer_eh1_default_hello",
                case="VeeR-EH1:default:hello",
                source_files=eh1["source_closure"]["source_files"],
                include_files=eh1["source_closure"]["include_files"],
                filelist_entries=eh1["source_closure"]["filelist_entries"],
            )

        rows = {row["design"]: row for row in report["rows"]}
        self.assertEqual(
            written,
            [
                "config/rtlmeter_sidecar_authorities/rtlmeter_veer_eh1_default_hello.json",
                "config/rtlmeter_sidecar_authorities/rtlmeter_veer_eh2_default_hello.json",
            ],
        )
        self.assertEqual(eh1["schema_role"], "rtlmeter_sidecar_authority")
        self.assertFalse(eh1["runtime_launchable"])
        self.assertIsNone(eh1["runtime_launch_template"])
        self.assertEqual(eh1["coverage_manifest"]["outputs"], ["normalized_stdout", "rtlmeter_cycles"])
        self.assertEqual(eh1["source_closure"]["authority"], "reviewed_hybrid_execution_source_closure")
        self.assertEqual(eh1["source_closure"]["runner_strategy"], "rtlmeter_stdout_cycles_direct_wrapper")
        self.assertFalse(eh1["source_closure"]["cpu_as_gpu_fallback_allowed"])
        self.assertIsNotNone(closure)
        self.assertEqual(closure["rtlmeter_case"], "VeeR-EH1:default:hello")
        self.assertEqual(eh2["target"], "rtlmeter_veer_eh2_default_hello")
        self.assertNotIn("authority", rows["VeeR-EH1"]["missing_surface"])
        self.assertNotIn("authority", rows["VeeR-EH2"]["missing_surface"])
        self.assertIn("state_layout_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertFalse(rows["VeeR-EH1"]["hybrid_measured"])
        self.assert_no_local_absolute_paths(json.dumps(eh1, sort_keys=True))

    def test_write_state_layout_preflights_keeps_root_offsets_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            write_authorities(root)

            written = write_state_layout_preflights(root)
            report = build_audit(root)
            eh1_layout = json.loads((root / "reports/rtlmeter_veer_eh1_state_layout_inspection.json").read_text())
            eh2_layout = json.loads((root / "reports/rtlmeter_veer_eh2_state_layout_inspection.json").read_text())

        rows = {row["design"]: row for row in report["rows"]}
        self.assertEqual(
            written,
            [
                "reports/rtlmeter_veer_eh1_state_layout_inspection.json",
                "reports/rtlmeter_veer_eh2_state_layout_inspection.json",
            ],
        )
        self.assertEqual(eh1_layout["surface"], "rtlmeter_veer_family_state_layout_preflight")
        self.assertTrue(eh1_layout["state_layout_inspection_performed"])
        self.assertFalse(eh1_layout["state_layout_ready"])
        self.assertIn("root_layout_probe", eh1_layout["missing_build_context"])
        self.assertFalse(eh1_layout["gpu_execution_claimed"])
        self.assertEqual(eh2_layout["target"], "rtlmeter_veer_eh2_default_hello")
        self.assertNotIn("authority", rows["VeeR-EH1"]["missing_surface"])
        self.assertNotIn("state_layout_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("state_image_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("sidecar_bridge_report", rows["VeeR-EH2"]["missing_surface"])
        self.assert_no_local_absolute_paths(json.dumps(eh1_layout, sort_keys=True))

    def test_write_state_layout_preflight_records_root_header_probe_without_reviewing_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            write_authorities(root)
            self._write_root_header(
                root,
                "VeeR-EH1",
                "\n".join(
                    [
                        "CData/*0:0*/ tb_top__DOT__core_clk;",
                        "CData/*0:0*/ tb_top__DOT__rst_l;",
                        "CData/*0:0*/ tb_top__DOT__porst_l;",
                        "IData/*30:0*/ tb_top__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d;",
                        "IData/*31:0*/ tb_top__DOT__WriteData;",
                        "IData/*31:0*/ tb_top__DOT__rvtop__DOT__veer__DOT__dec__DOT__arf__DOT____Vcellout__gpr;",
                    ]
                )
                + "\n",
            )

            write_state_layout_preflights(root)
            eh1_layout = json.loads((root / "reports/rtlmeter_veer_eh1_state_layout_inspection.json").read_text())

        probe = eh1_layout["detected_layout"]["root_header_probe"]
        self.assertTrue(probe["root_header_observed"])
        self.assertTrue(probe["root_layout_probe_performed"])
        self.assertEqual(probe["root_layout_probe_kind"], "generated_verilator_root_header_marker_scan")
        self.assertFalse(probe["root_field_offsets_reviewed"])
        self.assertFalse(eh1_layout["state_layout_ready"])
        self.assertNotIn("root_layout_probe", eh1_layout["missing_build_context"])
        self.assertIn("reviewed_root_field_offsets", eh1_layout["missing_build_context"])
        self.assertIn("cycle_counters", probe["missing_marker_groups"])
        self.assert_no_local_absolute_paths(json.dumps(eh1_layout, sort_keys=True))

    def test_write_root_offset_reviews_reports_specific_missing_marker_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            write_authorities(root)
            self._write_root_header(
                root,
                "VeeR-EH1",
                "\n".join(
                    [
                        "CData/*0:0*/ tb_top__DOT__core_clk;",
                        "CData/*0:0*/ tb_top__DOT__rst_l;",
                        "CData/*0:0*/ tb_top__DOT__porst_l;",
                        "IData/*30:0*/ tb_top__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d;",
                        "IData/*31:0*/ tb_top__DOT__WriteData;",
                        "IData/*31:0*/ tb_top__DOT__rvtop__DOT__veer__DOT__dec__DOT__arf__DOT____Vcellout__gpr;",
                    ]
                )
                + "\n",
            )
            write_state_layout_preflights(root)

            written = write_root_offset_reviews(root)
            report = build_audit(root)
            eh1_review = json.loads((root / "reports/rtlmeter_veer_eh1_root_offset_review.json").read_text())

        rows = {row["design"]: row for row in report["rows"]}
        self.assertEqual(
            written,
            [
                "reports/rtlmeter_veer_eh1_root_offset_review.json",
                "reports/rtlmeter_veer_eh2_root_offset_review.json",
            ],
        )
        self.assertEqual(eh1_review["surface"], "rtlmeter_veer_family_root_offset_review")
        self.assertTrue(eh1_review["root_offset_review_performed"])
        self.assertFalse(eh1_review["root_field_offsets_reviewed_for_target"])
        self.assertFalse(eh1_review["root_observable_offset_review_ready"])
        self.assertFalse(eh1_review["root_offset_probe_performed"])
        self.assertIn("root_offset_probe", eh1_review["missing_build_context"])
        self.assertIn("control_scalars_root_offset_mapping", eh1_review["missing_build_context"])
        self.assertIn("complete_root_field_offset_abi_review", eh1_review["missing_build_context"])
        self.assertEqual(eh1_review["observed_marker_groups"], [])
        self.assertNotIn("root_offset_review_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("state_image_report", rows["VeeR-EH1"]["missing_surface"])
        self.assert_no_local_absolute_paths(json.dumps(eh1_review, sort_keys=True))

    def test_state_layout_preflight_prefers_mailbox_public_flat_root_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            write_authorities(root)
            self._write_root_header(
                root,
                "VeeR-EH1",
                "\n".join(
                    [
                        "CData/*0:0*/ tb_top__DOT__core_clk;",
                        "CData/*0:0*/ tb_top__DOT__rst_l;",
                        "CData/*0:0*/ tb_top__DOT__porst_l;",
                    ]
                )
                + "\n",
            )
            self._write_root_header(
                root,
                "VeeR-EH1",
                "\n".join(
                    [
                        "CData/*0:0*/ tb_top__DOT__core_clk;",
                        "CData/*0:0*/ tb_top__DOT__rst_l;",
                        "CData/*0:0*/ tb_top__DOT__porst_l;",
                        "CData/*0:0*/ tb_top__DOT__mailbox_write;",
                        "IData/*31:0*/ tb_top__DOT__WriteData;",
                    ]
                )
                + "\n",
                variant="mailbox_public_flat",
            )

            write_state_layout_preflights(root)
            layout = json.loads((root / "reports/rtlmeter_veer_eh1_state_layout_inspection.json").read_text())

        probe = layout["detected_layout"]["root_header_probe"]
        self.assertEqual(probe["root_obj_dir_variant"], "mailbox_public_flat")
        self.assertIn("cpu_reference_mailbox_public_flat", probe["root_obj_dir"])
        self.assertTrue(probe["root_marker_hits"]["mailbox_observables"]["observed"])
        self.assert_no_local_absolute_paths(json.dumps(layout, sort_keys=True))

    def test_root_offset_review_requires_mailbox_write_and_write_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = {
                "design": "VeeR-EH2",
                "configuration": "default",
                "test": "hello",
                "case": "VeeR-EH2:default:hello",
            }
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_state_layout_inspection.json",
                {
                    "detected_layout": {
                        "root_header_probe": {
                            "root_offset_probe_performed": True,
                            "root_header_observed": True,
                            "root_offset_marker_hits": {
                                "control_scalars": {
                                    "observed": True,
                                    "markers": {
                                        "tb_top__DOT__core_clk": [{"offset": 1}],
                                        "tb_top__DOT__rst_l": [{"offset": 2}],
                                        "tb_top__DOT__porst_l": [{"offset": 3}],
                                    },
                                },
                                "pc_candidates": {
                                    "observed": True,
                                    "markers": {"tb_top__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d": [{"offset": 4}]},
                                },
                                "cycle_counters": {
                                    "observed": True,
                                    "markers": {
                                        "tb_top__DOT__mcycle": [{"offset": 5}],
                                        "tb_top__DOT__minstret": [{"offset": 6}],
                                    },
                                },
                                "mailbox_observables": {
                                    "observed": True,
                                    "markers": {"WriteData": [{"offset": 7}], "mailbox_write": []},
                                },
                                "gpr_observables": {
                                    "observed": True,
                                    "markers": {"__DOT__gpr": [{"offset": 8}]},
                                },
                            },
                        },
                    },
                },
            )

            review = build_root_offset_review_payload(root, target)

        self.assertIn("mailbox_observables", review["observed_marker_groups"])
        self.assertNotIn("mailbox_observables", review["complete_marker_groups"])
        self.assertIn("mailbox_observables", review["missing_marker_groups"])
        self.assertIn("mailbox_observable_export_or_tb_instrumentation", review["missing_build_context"])
        self.assertFalse(review["root_observable_offset_candidates_complete"])

    def test_root_offset_review_selects_reviewed_abi_when_candidates_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = {
                "design": "VeeR-EH1",
                "configuration": "default",
                "test": "hello",
                "case": "VeeR-EH1:default:hello",
            }
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_state_layout_inspection.json",
                {
                    "detected_layout": {
                        "root_header_probe": {
                            "root_offset_probe_performed": True,
                            "root_header_observed": True,
                            "root_obj_dir_variant": "mailbox_public_flat",
                            "root_obj_dir": "artifacts/rtlmeter_veer_eh1_cpu_reference_mailbox_public_flat/VeeR-EH1/default/compile-0/obj_dir",
                            "root_offset_marker_hits": {
                                "control_scalars": {
                                    "observed": True,
                                    "markers": {
                                        "tb_top__DOT__core_clk": [{"name": "tb_top__DOT__core_clk", "offset": 0, "size": 1, "decl_type": "CData/*0:0*/"}],
                                        "tb_top__DOT__rst_l": [{"name": "tb_top__DOT__rst_l", "offset": 1, "size": 1, "decl_type": "CData/*0:0*/"}],
                                        "tb_top__DOT__porst_l": [{"name": "tb_top__DOT__porst_l", "offset": 2, "size": 1, "decl_type": "CData/*0:0*/"}],
                                    },
                                },
                                "pc_candidates": {
                                    "observed": True,
                                    "markers": {"dec_tlu_i0_pc_e4": [{"name": "pc", "offset": 10, "size": 4, "decl_type": "IData/*30:0*/"}]},
                                },
                                "cycle_counters": {
                                    "observed": True,
                                    "markers": {
                                        "mcyclel": [
                                            {"name": "wr_mcyclel_wb", "offset": 19, "size": 1, "decl_type": "CData/*0:0*/"},
                                            {"name": "mcyclel", "offset": 20, "size": 4, "decl_type": "IData/*31:0*/"},
                                        ],
                                        "minstretl": [
                                            {"name": "wr_minstretl_wb", "offset": 23, "size": 1, "decl_type": "CData/*0:0*/"},
                                            {"name": "minstretl", "offset": 24, "size": 4, "decl_type": "IData/*31:0*/"},
                                        ],
                                    },
                                },
                                "mailbox_observables": {
                                    "observed": True,
                                    "markers": {
                                        "mailbox_write": [{"name": "mailbox_write", "offset": 4, "size": 1, "decl_type": "CData/*0:0*/"}],
                                        "WriteData": [{"name": "WriteData", "offset": 32, "size": 8, "decl_type": "QData/*63:0*/"}],
                                    },
                                },
                                "gpr_observables": {
                                    "observed": True,
                                    "markers": {"gpr_banks": [{"name": "gpr1", "offset": 40, "size": 4, "decl_type": "IData/*31:0*/"}]},
                                },
                            },
                        },
                    },
                },
            )

            review = build_root_offset_review_payload(root, target)

        self.assertTrue(review["root_observable_offset_candidates_complete"])
        self.assertTrue(review["root_field_offsets_reviewed_for_target"])
        self.assertTrue(review["root_observable_offset_review_ready"])
        self.assertEqual(review["missing_marker_groups"], [])
        self.assertEqual(review["missing_reviewed_root_offset_abi_fields"], [])
        self.assertNotIn("complete_root_field_offset_abi_review", review["missing_build_context"])
        self.assertEqual(review["reviewed_root_offset_abi"]["mailbox_write"]["offset"], 4)
        self.assertEqual(review["reviewed_root_offset_abi"]["mailbox_data"]["size"], 8)
        self.assertEqual(review["reviewed_root_offset_abi"]["mcycle"]["name"], "mcyclel")
        self.assertEqual(review["reviewed_root_offset_abi"]["minstret"]["name"], "minstretl")
        self.assertFalse(review["gpu_execution_claimed"])
        self.assertFalse(review["timing_measured"])
        self.assert_no_local_absolute_paths(json.dumps(review, sort_keys=True))

    def test_write_state_images_materializes_preload_but_keeps_execution_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            write_authorities(root)
            write_state_layout_preflights(root)

            written = write_state_images(root)
            report = build_audit(root)
            eh1_report = json.loads(
                (root / "reports/rtlmeter_veer_eh1_state_image_materializer.json").read_text()
            )
            eh1_image = json.loads(
                (
                    root
                    / "artifacts/rtlmeter_veer_eh1_state_image/veer_eh1_extracted_state_image.json"
                ).read_text()
            )

        rows = {row["design"]: row for row in report["rows"]}
        self.assertEqual(
            written,
            [
                "reports/rtlmeter_veer_eh1_state_image_materializer.json",
                "reports/rtlmeter_veer_eh2_state_image_materializer.json",
            ],
        )
        self.assertEqual(eh1_report["surface"], "rtlmeter_veer_family_state_image_materializer")
        self.assertTrue(eh1_report["state_image_materialized"])
        self.assertFalse(eh1_report["state_layout_ready"])
        self.assertFalse(eh1_report["gpu_execution_claimed"])
        self.assertFalse(eh1_report["timing_measured"])
        self.assertFalse(eh1_report["speedup_claimed"])
        self.assertIn("sidecar_bridge_report", eh1_report["missing_build_context"])
        self.assertEqual(eh1_report["program_byte_count"], 4)
        self.assertEqual(eh1_image["schema_role"], "veer_eh1_extracted_preload_state_image")
        self.assertEqual(eh1_image["sections"]["control_scalars"]["tb_top__DOT__core_clk"], 0)
        self.assertEqual(eh1_image["sections"]["program_staging_lmem"][0]["addr"], "0x80000000")
        self.assertEqual(eh1_image["sections"]["program_staging_lmem"][0]["byte_hex"], "0x73")
        self.assertEqual(eh1_image["sections"]["program_staging_imem"][3]["byte_hex"], "0xb0")
        self.assertNotIn("state_image_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("sidecar_bridge_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("timing_report", rows["VeeR-EH2"]["missing_surface"])
        self.assertEqual(rows["VeeR-EH1"]["status"], "state_image_materialized_surface_missing")
        self.assert_no_local_absolute_paths(json.dumps(eh1_report, sort_keys=True))
        self.assert_no_local_absolute_paths(json.dumps(eh1_image, sort_keys=True))

    def test_write_sidecar_bridge_preflights_keeps_bridge_execution_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            write_authorities(root)
            write_state_layout_preflights(root)
            write_state_images(root)

            written = write_sidecar_bridge_preflights(root)
            report = build_audit(root)
            eh1_bridge = json.loads((root / "reports/rtlmeter_veer_eh1_sidecar_bridge.json").read_text())
            eh2_bridge = json.loads((root / "reports/rtlmeter_veer_eh2_sidecar_bridge.json").read_text())

        rows = {row["design"]: row for row in report["rows"]}
        self.assertEqual(
            written,
            [
                "reports/rtlmeter_veer_eh1_sidecar_bridge.json",
                "reports/rtlmeter_veer_eh2_sidecar_bridge.json",
            ],
        )
        self.assertEqual(eh1_bridge["surface"], "rtlmeter_veer_family_sidecar_bridge_preflight")
        self.assertTrue(eh1_bridge["sidecar_bridge_preflight_ready"])
        self.assertFalse(eh1_bridge["sidecar_bridge_invoked"])
        self.assertFalse(eh1_bridge["sidecar_observables_ready"])
        self.assertFalse(eh1_bridge["sidecar_execution_claimed"])
        self.assertFalse(eh1_bridge["gpu_execution_claimed"])
        self.assertFalse(eh1_bridge["timing_measured"])
        self.assertFalse(eh1_bridge["speedup_claimed"])
        self.assertEqual(eh1_bridge["comparison"]["status"], "not_run")
        self.assertIn("sidecar_executable_review", eh1_bridge["missing_build_context"])
        self.assertIn("timing_report", eh1_bridge["missing_build_context"])
        self.assertEqual(eh2_bridge["target"], "rtlmeter_veer_eh2_default_hello")
        self.assertNotIn("sidecar_bridge_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("timing_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertEqual(rows["VeeR-EH1"]["status"], "sidecar_bridge_preflight_surface_missing")
        self.assertFalse(rows["VeeR-EH1"]["hybrid_measured"])
        self.assert_no_local_absolute_paths(json.dumps(eh1_bridge, sort_keys=True))

    def test_write_sidecar_executable_reviews_fail_closed_on_el2_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            (root / "src/tools").mkdir(parents=True, exist_ok=True)
            (root / "src/tools/veer_el2_sidecar_executable.py").write_text(
                "\n".join(
                    [
                        "VEER_EL2_RTL_METER_TARGET = 'rtlmeter_veer_el2_default_hello'",
                        "VEER_EL2_SIDECAR_STATE_IMAGE_ENV = 'VEER_EL2_SIDECAR_STATE_IMAGE'",
                        "HELLO_PROGRAM_SHA256 = 'd0219135d529505962c1c5ed44360e91466ae046cb8ec40b5980761861c63d76'",
                        "def _veer_el2_root_state_offset_review(): pass",
                        "rvtop_wrapper = 'tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer'",
                        "raise RuntimeError('state image target is not the reviewed VeeR-EL2 target')",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            write_authorities(root)
            write_state_layout_preflights(root)
            write_state_images(root)

            written = write_sidecar_executable_reviews(root)
            report = build_audit(root)
            eh1_review = json.loads(
                (root / "reports/rtlmeter_veer_eh1_sidecar_executable_review.json").read_text()
            )
            eh2_review = json.loads(
                (root / "reports/rtlmeter_veer_eh2_sidecar_executable_review.json").read_text()
            )

        rows = {row["design"]: row for row in report["rows"]}
        self.assertEqual(
            written,
            [
                "reports/rtlmeter_veer_eh1_sidecar_executable_review.json",
                "reports/rtlmeter_veer_eh2_sidecar_executable_review.json",
            ],
        )
        self.assertEqual(eh1_review["surface"], "rtlmeter_veer_family_sidecar_executable_review")
        self.assertTrue(eh1_review["sidecar_executable_review_performed"])
        self.assertFalse(eh1_review["sidecar_executable_reviewed_for_target"])
        self.assertFalse(eh1_review["el2_executable_reusable_for_target"])
        self.assertFalse(eh1_review["design_specific_sidecar_executable_present"])
        self.assertIn("target_name_differs_from_el2", eh1_review["reuse_blockers"])
        self.assertIn("program_sha_differs_from_el2", eh1_review["reuse_blockers"])
        self.assertIn("wrapper_hierarchy_differs_from_el2", eh1_review["reuse_blockers"])
        self.assertIn("el2_root_offset_review_function_is_fixed", eh1_review["reuse_blockers"])
        self.assertIn("design_specific_sidecar_executable_implementation", eh1_review["missing_build_context"])
        self.assertFalse(eh1_review["gpu_execution_claimed"])
        self.assertFalse(eh1_review["timing_measured"])
        self.assertEqual(eh2_review["target"], "rtlmeter_veer_eh2_default_hello")
        self.assertNotIn("sidecar_executable_review_report", rows["VeeR-EH1"]["missing_surface"])
        self.assertIn("sidecar_bridge_report", rows["VeeR-EH1"]["missing_surface"])
        self.assert_no_local_absolute_paths(json.dumps(eh1_review, sort_keys=True))

    def test_sidecar_bridge_preflight_consumes_cpu_reference_observables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            write_authorities(root)
            write_state_layout_preflights(root)
            write_state_images(root)
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_cpu_reference_summary.json",
                {
                    "status": "cpu_reference_passed",
                    "cpu_reference_ready_for_hybrid_compare": True,
                    "rtlmeter_cycles": 1044,
                    "stdout_test_passed": True,
                    "metrics": {"execute_elapsed_s": 0.03},
                },
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_cpu_reference_summary.json",
                {
                    "status": "cpu_reference_passed",
                    "cpu_reference_ready_for_hybrid_compare": True,
                    "rtlmeter_cycles": 2325,
                    "stdout_test_passed": True,
                    "metrics": {"execute_elapsed_s": 0.06},
                },
            )

            write_root_offset_reviews(root)
            write_sidecar_executable_reviews(root)
            write_sidecar_bridge_preflights(root)
            eh1_bridge = json.loads((root / "reports/rtlmeter_veer_eh1_sidecar_bridge.json").read_text())
            eh2_bridge = json.loads((root / "reports/rtlmeter_veer_eh2_sidecar_bridge.json").read_text())

        self.assertTrue(eh1_bridge["cpu_reference_observables_ready"])
        self.assertEqual(eh1_bridge["cpu_reference"]["rtlmeter_cycles"], 1044)
        self.assertNotIn("cpu_reference_observables", eh1_bridge["missing_build_context"])
        self.assertNotIn("reviewed_root_field_offsets", eh1_bridge["missing_build_context"])
        self.assertIn("complete_root_field_offset_abi_review", eh1_bridge["missing_build_context"])
        self.assertNotIn("sidecar_executable_review", eh1_bridge["missing_build_context"])
        self.assertIn("design_specific_sidecar_executable_implementation", eh1_bridge["missing_build_context"])
        self.assertIn("timing_report", eh1_bridge["missing_build_context"])
        self.assertTrue(eh1_bridge["sidecar_executable_review_performed"])
        self.assertFalse(eh1_bridge["sidecar_executable_reviewed_for_target"])
        self.assertTrue(eh2_bridge["cpu_reference_observables_ready"])
        self.assertEqual(eh2_bridge["cpu_reference"]["execute_elapsed_s"], 0.06)
        self.assertFalse(eh2_bridge["sidecar_bridge_invoked"])

    def test_sidecar_bridge_preflight_advances_when_eh_executable_boundary_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            eh_executable = root / "src/tools/veer_eh_sidecar_executable.py"
            eh_executable.parent.mkdir(parents=True, exist_ok=True)
            eh_executable.write_text(
                "\n".join(
                    [
                        "SUPPORTED_TARGETS = {'rtlmeter_veer_eh1_default_hello': {}, 'rtlmeter_veer_eh2_default_hello': {}}",
                        "REQUIRED_ABI_FIELDS = []",
                        "state_image_materialized = True",
                        "cpu_reference_ready_for_hybrid_compare = True",
                        '"gpu_execution_claimed": False',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            write_authorities(root)
            write_state_layout_preflights(root)
            write_state_images(root)
            for design, cycles in (("veer_eh1", 1044), ("veer_eh2", 2325)):
                self._write_json(
                    root / f"reports/rtlmeter_{design}_cpu_reference_summary.json",
                    {
                        "status": "cpu_reference_passed",
                        "cpu_reference_ready_for_hybrid_compare": True,
                        "rtlmeter_cycles": cycles,
                    },
                )
                self._write_json(
                    root / f"reports/rtlmeter_{design}_root_offset_review.json",
                    {
                        "root_offset_review_performed": True,
                        "root_field_offsets_reviewed_for_target": True,
                    },
                )

            write_sidecar_executable_reviews(root)
            write_sidecar_bridge_preflights(root)
            eh1_review = json.loads((root / "reports/rtlmeter_veer_eh1_sidecar_executable_review.json").read_text())
            eh1_bridge = json.loads((root / "reports/rtlmeter_veer_eh1_sidecar_bridge.json").read_text())

        self.assertTrue(eh1_review["sidecar_executable_reviewed_for_target"])
        self.assertTrue(eh1_review["design_specific_sidecar_executable_present"])
        self.assertEqual(
            eh1_review["status"],
            "reviewed_veer_eh1_design_specific_sidecar_executable_boundary",
        )
        self.assertNotIn("design_specific_sidecar_executable_implementation", eh1_review["missing_build_context"])
        self.assertIn("executed_bridge_comparison", eh1_review["missing_build_context"])
        self.assertTrue(eh1_bridge["sidecar_executable_reviewed_for_target"])
        self.assertEqual(eh1_bridge["next_required_boundary"], "execute EH sidecar bridge comparison before timing")
        self.assertNotIn("design_specific_sidecar_executable_implementation", eh1_bridge["missing_build_context"])
        self.assertIn("executed_bridge_comparison", eh1_bridge["missing_build_context"])
        self.assertIn("timing_report", eh1_bridge["missing_build_context"])
        self.assertFalse(eh1_bridge["sidecar_bridge_invoked"])
        self.assertFalse(eh1_bridge["gpu_execution_claimed"])

    def test_sidecar_bridge_preflight_surfaces_eh1_ptxas_timeout_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            eh_executable = root / "src/tools/veer_eh_sidecar_executable.py"
            eh_executable.parent.mkdir(parents=True, exist_ok=True)
            eh_executable.write_text(
                "\n".join(
                    [
                        "SUPPORTED_TARGETS = {'rtlmeter_veer_eh1_default_hello': {}, 'rtlmeter_veer_eh2_default_hello': {}}",
                        "REQUIRED_ABI_FIELDS = []",
                        "state_image_materialized = True",
                        "cpu_reference_ready_for_hybrid_compare = True",
                        '"gpu_execution_claimed": False',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            write_authorities(root)
            write_state_layout_preflights(root)
            write_state_images(root)
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_cpu_reference_summary.json",
                {
                    "status": "cpu_reference_passed",
                    "cpu_reference_ready_for_hybrid_compare": True,
                    "rtlmeter_cycles": 1044,
                },
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_root_offset_review.json",
                {
                    "root_offset_review_performed": True,
                    "root_field_offsets_reviewed_for_target": True,
                },
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_sidecar_bridge_bounded8.json",
                {
                    "status": "gpu_launch_timeout",
                    "sidecar_bridge_invoked": True,
                    "sidecar_observables_ready": False,
                    "missing_build_context": ["successful_gpu_launch_without_timeout"],
                    "run_vl_hybrid_stage_trace": {"last_stage": "before_cuModuleLoad"},
                },
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_ptxas_o0_probe.json",
                {
                    "status": "ptxas_timeout",
                    "timeout_s": 180,
                    "elapsed_wall": "3:00.10",
                    "max_resident_set_kb": 6674492,
                    "cubin_exists": False,
                    "ptx_bytes": 17684220,
                    "ptx_line_count": 630613,
                },
            )

            write_sidecar_executable_reviews(root)
            write_sidecar_bridge_preflights(root)
            eh1_bridge = json.loads((root / "reports/rtlmeter_veer_eh1_sidecar_bridge.json").read_text())

        self.assertTrue(eh1_bridge["sidecar_bridge_invoked"])
        self.assertEqual(eh1_bridge["ptxas_probe"]["status"], "ptxas_timeout")
        self.assertIn("ptxas_cubin_probe_timeout", eh1_bridge["missing_build_context"])
        self.assertEqual(
            eh1_bridge["next_required_boundary"],
            "reduce EH1 generated PTX/module compile cost before bridge comparison",
        )

    def test_sidecar_bridge_preflight_prioritizes_entry_pruned_eval_fault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            eh_executable = root / "src/tools/veer_eh_sidecar_executable.py"
            eh_executable.parent.mkdir(parents=True, exist_ok=True)
            eh_executable.write_text(
                "\n".join(
                    [
                        "SUPPORTED_TARGETS = {'rtlmeter_veer_eh1_default_hello': {}, 'rtlmeter_veer_eh2_default_hello': {}}",
                        "REQUIRED_ABI_FIELDS = []",
                        "state_image_materialized = True",
                        "cpu_reference_ready_for_hybrid_compare = True",
                        '"gpu_execution_claimed": False',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            write_authorities(root)
            write_state_layout_preflights(root)
            write_state_images(root)
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_cpu_reference_summary.json",
                {"status": "cpu_reference_passed", "cpu_reference_ready_for_hybrid_compare": True},
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_root_offset_review.json",
                {"root_offset_review_performed": True, "root_field_offsets_reviewed_for_target": True},
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_sidecar_bridge_bounded8.json",
                {
                    "status": "gpu_launch_timeout",
                    "sidecar_bridge_invoked": True,
                    "sidecar_observables_ready": False,
                    "missing_build_context": ["successful_gpu_launch_without_timeout"],
                    "run_vl_hybrid_stage_trace": {"last_stage": "before_cuModuleLoad"},
                },
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh1_entry_pruned_module_probe.json",
                {
                    "ptxas_probe": {"status": "passed"},
                    "bridge_probe": {"status": "illegal_memory_access_at_first_eval_launch"},
                    "eval_only_probe": {"status": "illegal_memory_access_at_first_eval_launch"},
                    "eval_only_padded_storage_probe": {
                        "status": "padded_storage_did_not_clear_first_eval_fault",
                        "padded_storage_bytes": 2097152,
                    },
                    "eval_only_static_ptx_residue_probe": {
                        "status": "reachable_stdout_finish_cpp_runtime_residue_detected",
                        "residual_symbol_count": 17,
                        "std_allocator_allocate_returns_null": True,
                        "unsupported_device_runtime_residue": [
                            "std::string constructor/destructor",
                            "VL_WRITEF_NX",
                        ],
                    },
                    "eval_only_region_counter_global_init_probe": {
                        "status": "illegal_memory_access_at_first_eval_launch"
                    },
                    "stack_limit_probe": {
                        "status": "stack_limit_override_did_not_clear_first_eval_fault"
                    },
                    "host_io_stub_eval_only_probe": {
                        "status": "illegal_memory_access_at_first_eval_launch",
                        "cubin_bytes": 6735488,
                        "ptxas_o0_elapsed_wall_s": 15.29,
                        "stage_trace_last_stage": "before_final_sync",
                        "kernel_attrs": {
                            "num_regs": 255,
                            "local_size_bytes": 1776,
                        },
                        "storage2m_padded_init_probe": {
                            "status": "padded_storage_did_not_clear_first_eval_fault",
                            "padded_storage_bytes": 2097152,
                        },
                        "compute_sanitizer_probe": {
                            "status": "tool_environment_blocked_before_instrumented_cuda_api",
                        },
                    },
                    "entry_pruned_cubin_exists": True,
                    "entry_pruned_cubin_bytes": 11701952,
                    "entry_pruned_kept_entries": ["vl_eval_batch_gpu", "vl_apply_patch_schedule_gpu"],
                },
            )

            write_sidecar_executable_reviews(root)
            write_sidecar_bridge_preflights(root)
            eh1_bridge = json.loads((root / "reports/rtlmeter_veer_eh1_sidecar_bridge.json").read_text())

        self.assertEqual(eh1_bridge["entry_pruned_module_probe"]["bridge_status"], "illegal_memory_access_at_first_eval_launch")
        self.assertEqual(eh1_bridge["entry_pruned_module_probe"]["eval_only_status"], "illegal_memory_access_at_first_eval_launch")
        self.assertEqual(
            eh1_bridge["entry_pruned_module_probe"]["region_counter_global_init_status"],
            "illegal_memory_access_at_first_eval_launch",
        )
        self.assertEqual(
            eh1_bridge["entry_pruned_module_probe"]["padded_storage_probe_status"],
            "padded_storage_did_not_clear_first_eval_fault",
        )
        self.assertEqual(eh1_bridge["entry_pruned_module_probe"]["padded_storage_bytes"], 2097152)
        self.assertEqual(
            eh1_bridge["entry_pruned_module_probe"]["static_ptx_residue_probe_status"],
            "reachable_stdout_finish_cpp_runtime_residue_detected",
        )
        self.assertEqual(eh1_bridge["entry_pruned_module_probe"]["static_ptx_residue_symbol_count"], 17)
        self.assertIs(eh1_bridge["entry_pruned_module_probe"]["std_allocator_allocate_returns_null"], True)
        self.assertEqual(
            eh1_bridge["entry_pruned_module_probe"]["stack_limit_probe_status"],
            "stack_limit_override_did_not_clear_first_eval_fault",
        )
        self.assertEqual(
            eh1_bridge["entry_pruned_module_probe"]["host_io_stub_eval_only_status"],
            "illegal_memory_access_at_first_eval_launch",
        )
        self.assertEqual(eh1_bridge["entry_pruned_module_probe"]["host_io_stub_cubin_bytes"], 6735488)
        self.assertEqual(eh1_bridge["entry_pruned_module_probe"]["host_io_stub_num_regs"], 255)
        self.assertEqual(eh1_bridge["entry_pruned_module_probe"]["host_io_stub_local_size_bytes"], 1776)
        self.assertEqual(
            eh1_bridge["entry_pruned_module_probe"]["host_io_stub_padded_storage_probe_status"],
            "padded_storage_did_not_clear_first_eval_fault",
        )
        self.assertEqual(
            eh1_bridge["entry_pruned_module_probe"]["host_io_stub_compute_sanitizer_status"],
            "tool_environment_blocked_before_instrumented_cuda_api",
        )
        self.assertIn("entry_pruned_eval_kernel_illegal_memory_access", eh1_bridge["missing_build_context"])
        self.assertIn("entry_pruned_eval_only_fault_confirmed", eh1_bridge["missing_build_context"])
        self.assertIn("padded_storage_did_not_clear_eval_fault", eh1_bridge["missing_build_context"])
        self.assertIn("reachable_stdout_finish_cpp_runtime_residue", eh1_bridge["missing_build_context"])
        self.assertIn("host_io_stub_eval_only_fault_confirmed", eh1_bridge["missing_build_context"])
        self.assertIn(
            "host_io_stub_padded_storage_did_not_clear_eval_fault",
            eh1_bridge["missing_build_context"],
        )
        self.assertIn(
            "compute_sanitizer_tool_environment_blocked",
            eh1_bridge["missing_build_context"],
        )
        self.assertIn(
            "region_counter_global_init_did_not_clear_eval_fault",
            eh1_bridge["missing_build_context"],
        )
        self.assertIn(
            "stack_limit_override_did_not_clear_eval_fault",
            eh1_bridge["missing_build_context"],
        )
        self.assertEqual(
            eh1_bridge["next_required_boundary"],
            "fix EH1 eval-only kernel illegal memory access after entry-pruned module load",
        )

    def test_sidecar_bridge_preflight_prioritizes_eh2_first_step_sync_fault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design)
            eh_executable = root / "src/tools/veer_eh_sidecar_executable.py"
            eh_executable.parent.mkdir(parents=True, exist_ok=True)
            eh_executable.write_text(
                "\n".join(
                    [
                        "SUPPORTED_TARGETS = {'rtlmeter_veer_eh1_default_hello': {}, 'rtlmeter_veer_eh2_default_hello': {}}",
                        "REQUIRED_ABI_FIELDS = []",
                        "state_image_materialized = True",
                        "cpu_reference_ready_for_hybrid_compare = True",
                        '"gpu_execution_claimed": False',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            write_authorities(root)
            write_state_layout_preflights(root)
            write_state_images(root)
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_cpu_reference_summary.json",
                {"status": "cpu_reference_passed", "cpu_reference_ready_for_hybrid_compare": True},
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_root_offset_review.json",
                {"root_offset_review_performed": True, "root_field_offsets_reviewed_for_target": True},
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_sidecar_bridge_bounded8.json",
                {
                    "status": "gpu_launch_timeout",
                    "sidecar_bridge_invoked": True,
                    "sidecar_observables_ready": False,
                    "missing_build_context": ["successful_gpu_launch_without_timeout"],
                    "run_vl_hybrid_stage_trace": {"last_stage": "before_cuModuleLoad"},
                },
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_entry_pruned_module_probe.json",
                {
                    "schema_role": "veer_eh_sidecar_bridge_execution",
                    "status": "gpu_launch_failed",
                    "gpu_module_override": "artifacts/entry_pruned.cubin",
                    "run_vl_hybrid_sync_each_step": True,
                    "run_vl_hybrid_returncode": 1,
                    "run_vl_hybrid_stage_trace": {"last_stage": "before_first_step_sync"},
                    "run_vl_hybrid_stderr_tail": [
                        "run_vl_hybrid: launch step=0 kernel_index=-1 kernel=vl_apply_patch_schedule_gpu",
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                },
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_ptx_entry_slice.json",
                {
                    "slice_ptx": (
                        "artifacts/rtlmeter_veer_eh2_ptx_entry_slice/"
                        "vl_eval_patch_schedule_gpu.ptx"
                    )
                },
            )
            ptx_path = root / "artifacts/rtlmeter_veer_eh2_ptx_entry_slice/vl_eval_patch_schedule_gpu.ptx"
            ptx_path.parent.mkdir(parents=True, exist_ok=True)
            ptx_path.write_text(
                "\n".join(
                    [
                        ".visible .func _ZN16VlDelayScheduler4nextEv()",
                        ".weak .func _ZNSt8_Rb_tree4findEv()",
                        ".visible .func Verilated::runFlushCallbacks()",
                        ".visible .func _ZSt3refI14Vsim___024rootET_RS1_()",
                        "call.uni VL_WRITEF_NX;",
                        "call.uni VL_FINISH_MT;",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self._write_json(
                root / "reports/rtlmeter_veer_eh2_host_cleanup_module_load_diagnostic.json",
                {
                    "ptxas_status": "ptxas_passed",
                    "ptxas_cubin_exists": True,
                    "ptxas_cubin_out": "artifacts/host_cleanup.cubin",
                },
            )
            (root / "reports/rtlmeter_veer_eh2_host_cleanup_eval_only_direct_probe.exit").write_text(
                "1\n",
                encoding="utf-8",
            )
            (root / "reports/rtlmeter_veer_eh2_host_cleanup_eval_only_direct_probe.stderr").write_text(
                "\n".join(
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            for name, exit_code, lines in (
                (
                    "host_cleanup_v2_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "return_before_eval_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "return_before_eval_call_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_return_before_phase_act_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_return_after_one_phase_act_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_return_after_triggers_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_return_after_orinto_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "trigger_orinto_return_before_first_ix_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "trigger_orinto_return_before_first_ix_stack64k_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: ctx_limit STACK_SIZE updated=65536",
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_return_after_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_noop_return_after_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_after_dst_load_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_after_src_load_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_before_store_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_store_u64_src_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_store_u32_dst_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_store_u8_dst_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_store_u64_root_base_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "entry_store_nba_trigger_return_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_return_after_padded2m_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_return_after_maxr128_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: attr vl_eval_batch_gpu NUM_REGS=128",
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_store_vnba_before_triggers_return_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_store_vnba_after_triggers_direct_root_return_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_store_next472416_after_triggers_return_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_phase_act_inline_orinto_store_vnba_cvta_global_return_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_phase_act_minimal_store_vnba_return_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "std_ref_get_canonical_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vl_eval_return_before_phase_act_std_ref_get_canonical_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "vl_eval_return_after_one_phase_act_std_ref_get_canonical_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vl_eval_phase_act_return_after_orinto_ret0_std_ref_get_canonical_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vl_eval_phase_act_return_after_anyset_ret0_std_ref_get_canonical_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vl_eval_phase_act_return_after_timing_resume_ret0_std_ref_get_canonical_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vl_trigger_orinto_return_before_loop_std_ref_get_canonical_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "vl_trigger_orinto_return_after_dst_load_std_ref_get_canonical_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "vl_trigger_orinto_return_after_src_load_std_ref_get_canonical_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "vl_trigger_orinto_return_before_store_std_ref_get_canonical_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "vl_trigger_orinto_return_after_store_std_ref_get_canonical_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vlunpacked_lm1_ix0_canonical_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vl_eval_phase_act_return_before_orinto_vlunpacked_lm1_canonical_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "vl_trigger_orinto_return_immediate_vlunpacked_lm1_canonical_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "vlunpacked_lm1_orinto_rewrite_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "orinto_store_skip_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "orinto_store_zero_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "orinto_store_dst_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "skip_store_return_before_anyset_eval_only_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "skip_store_return_after_anyset_eval_only_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "skip_store_return_after_timing_resume_eval_only_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "skip_store_return_after_eval_act_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_act_return_after_callseq_950_eval_only_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_act_return_after_callseq_951_eval_only_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
                (
                    "eval_act_return_after_callseq_952_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_act_return_after_callseq_953_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_act_return_after_callseq_954_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "dec_cam0_return_after_param_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "dec_cam0_return_after_callseq_15707_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "dec_cam0_minimal_body_ret_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_act_skip_callseq_952_return_after_953_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_act_skip_callseq_952_953_return_after_954_eval_only_direct_probe",
                    "1",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ],
                ),
                (
                    "eval_act_skip_callseq_952_953_954_return_after_954_eval_only_direct_probe",
                    "0",
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid: stage=after_first_step_sync",
                    ],
                ),
            ):
                (root / f"reports/rtlmeter_veer_eh2_{name}.exit").write_text(
                    f"{exit_code}\n",
                    encoding="utf-8",
                )
                (root / f"reports/rtlmeter_veer_eh2_{name}.stderr").write_text(
                    "\n".join(lines) + "\n",
                    encoding="utf-8",
                )
                (root / f"reports/rtlmeter_veer_eh2_{name}.stdout").write_text(
                    "ok: steps=1 kernels_per_step=1\n" if exit_code == "0" else "",
                    encoding="utf-8",
                )
            (root / "reports/rtlmeter_veer_eh2_entry_pruned_eval_only_probe.exit").write_text(
                "1\n",
                encoding="utf-8",
            )
            (root / "reports/rtlmeter_veer_eh2_entry_pruned_eval_only_probe.stderr").write_text(
                "\n".join(
                    [
                        "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                        "run_vl_hybrid: stage=before_first_step_sync",
                        "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            for name in ("padded2m", "stack64k", "zero_init"):
                (root / f"reports/rtlmeter_veer_eh2_entry_pruned_eval_only_{name}_probe.exit").write_text(
                    "1\n",
                    encoding="utf-8",
                )
                (root / f"reports/rtlmeter_veer_eh2_entry_pruned_eval_only_{name}_probe.stderr").write_text(
                    "\n".join(
                        [
                            "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu",
                            "run_vl_hybrid: stage=before_first_step_sync",
                            "run_vl_hybrid.c:4704 CUDA error 700: an illegal memory access was encountered",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            write_sidecar_executable_reviews(root)
            write_sidecar_bridge_preflights(root)
            eh2_bridge = json.loads((root / "reports/rtlmeter_veer_eh2_sidecar_bridge.json").read_text())

        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["bridge_status"],
            "illegal_memory_access_at_first_step_sync",
        )
        self.assertTrue(eh2_bridge["entry_pruned_module_probe"]["entry_pruned_sidecar_sync_each_step"])
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["eval_only_status"],
            "illegal_memory_access_at_first_eval_launch",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["eval_only_variant_probes"]["zero_init"]["status"],
            "illegal_memory_access_at_first_eval_launch",
        )
        residue = eh2_bridge["entry_pruned_module_probe"]["static_ptx_runtime_residue_probe"]
        self.assertEqual(residue["status"], "cpp_verilator_runtime_residue_detected")
        self.assertEqual(residue["residue_pattern_counts"]["vl_delay_scheduler"], 1)
        self.assertEqual(residue["residue_pattern_counts"]["vl_writef"], 1)
        self.assertGreaterEqual(residue["suspicious_function_def_count"], 3)
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["host_cleanup_eval_only_probe"]["status"],
            "host_cleanup_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["host_cleanup_v2_eval_only_probe"]["status"],
            "host_cleanup_v2_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["return_before_eval_probe"]["status"],
            "return_before_eval_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["return_before_eval_call_probe"]["status"],
            "prologue_only_return_before_eval_call_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["eval_return_before_phase_act_probe"]["status"],
            "eval_return_before_phase_act_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["eval_return_after_one_phase_act_probe"]["status"],
            "eval_return_after_one_phase_act_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["eval_phase_act_return_after_triggers_probe"]["status"],
            "eval_phase_act_return_after_triggers_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["eval_phase_act_return_after_orinto_probe"]["status"],
            "eval_phase_act_return_after_orinto_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["trigger_orinto_return_before_first_ix_probe"]["status"],
            "trigger_orinto_return_before_first_ix_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "trigger_orinto_return_before_first_ix_stack64k_probe"
            ]["status"],
            "trigger_orinto_return_before_first_ix_stack64k_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["inline_orinto_noop_return_after_probe"]["status"],
            "inline_orinto_noop_return_after_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["inline_orinto_before_store_probe"]["status"],
            "inline_orinto_before_store_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["inline_orinto_return_after_probe"]["status"],
            "inline_orinto_return_after_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["inline_orinto_store_u64_src_probe"]["status"],
            "inline_orinto_store_u64_src_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["inline_orinto_store_u32_dst_probe"]["status"],
            "inline_orinto_store_u32_dst_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["entry_store_nba_trigger_return_probe"]["status"],
            "entry_store_nba_trigger_return_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["store_vnba_after_triggers_direct_root_probe"]["status"],
            "eval_phase_act_store_vnba_after_triggers_direct_root_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["inline_orinto_store_vnba_cvta_global_probe"]["status"],
            "inline_orinto_store_vnba_cvta_global_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["minimal_store_vnba_probe"]["status"],
            "eval_phase_act_minimal_store_vnba_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["std_ref_get_canonical_eval_only_probe"]["status"],
            "std_ref_get_canonical_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "std_ref_get_canonical_eval_return_before_phase_act_probe"
            ]["status"],
            "std_ref_get_canonical_eval_return_before_phase_act_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "std_ref_get_canonical_eval_return_after_one_phase_act_probe"
            ]["status"],
            "std_ref_get_canonical_eval_return_after_one_phase_act_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe"
            ]["status"],
            "std_ref_get_canonical_phase_act_return_after_orinto_ret0_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "std_ref_get_canonical_trigger_orinto_return_before_store_probe"
            ]["status"],
            "std_ref_get_canonical_trigger_orinto_return_before_store_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "std_ref_get_canonical_trigger_orinto_return_after_store_probe"
            ]["status"],
            "std_ref_get_canonical_trigger_orinto_return_after_store_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["vlunpacked_lm1_canonical_eval_only_probe"]["status"],
            "vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "vlunpacked_lm1_phase_act_return_before_orinto_probe"
            ]["status"],
            "vlunpacked_lm1_phase_act_return_before_orinto_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "vlunpacked_lm1_trigger_orinto_return_immediate_probe"
            ]["status"],
            "vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "vlunpacked_lm1_orinto_rewrite_eval_only_probe"
            ]["status"],
            "vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["orinto_store_skip_eval_only_probe"]["status"],
            "orinto_store_skip_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["orinto_store_zero_eval_only_probe"]["status"],
            "orinto_store_zero_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["orinto_store_dst_eval_only_probe"]["status"],
            "orinto_store_dst_eval_only_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["skip_store_return_before_anyset_probe"]["status"],
            "skip_store_return_before_anyset_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["skip_store_return_after_anyset_probe"]["status"],
            "skip_store_return_after_anyset_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["skip_store_return_after_timing_resume_probe"]["status"],
            "skip_store_return_after_timing_resume_passed",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["skip_store_return_after_eval_act_probe"]["status"],
            "skip_store_return_after_eval_act_still_illegal_memory_access",
        )
        callseq_probes = eh2_bridge["entry_pruned_module_probe"]["eval_act_return_after_callseq_probes"]
        self.assertEqual(callseq_probes["950"]["status"], "eval_act_return_after_callseq_950_passed")
        self.assertEqual(callseq_probes["951"]["status"], "eval_act_return_after_callseq_951_passed")
        self.assertEqual(
            callseq_probes["952"]["status"],
            "eval_act_return_after_callseq_952_still_illegal_memory_access",
        )
        self.assertEqual(
            callseq_probes["953"]["status"],
            "eval_act_return_after_callseq_953_still_illegal_memory_access",
        )
        self.assertEqual(
            callseq_probes["954"]["status"],
            "eval_act_return_after_callseq_954_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["dec_cam0_return_after_param_probe"]["status"],
            "dec_cam0_return_after_param_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["dec_cam0_return_after_callseq_15707_probe"]["status"],
            "dec_cam0_return_after_callseq_15707_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"]["dec_cam0_minimal_body_ret_probe"]["status"],
            "dec_cam0_minimal_body_ret_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "eval_act_skip_callseq_952_return_after_953_probe"
            ]["status"],
            "eval_act_skip_callseq_952_return_after_953_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "eval_act_skip_callseq_952_953_return_after_954_probe"
            ]["status"],
            "eval_act_skip_callseq_952_953_return_after_954_still_illegal_memory_access",
        )
        self.assertEqual(
            eh2_bridge["entry_pruned_module_probe"][
                "eval_act_skip_callseq_952_953_954_return_after_954_probe"
            ]["status"],
            "eval_act_skip_callseq_952_953_954_return_after_954_passed",
        )
        self.assertIn(
            "entry_pruned_cubin_first_step_sync_illegal_memory_access",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn("entry_pruned_eval_only_fault_confirmed", eh2_bridge["missing_build_context"])
        self.assertIn("entry_pruned_padded_storage_did_not_clear_eval_fault", eh2_bridge["missing_build_context"])
        self.assertIn("entry_pruned_stack64k_did_not_clear_eval_fault", eh2_bridge["missing_build_context"])
        self.assertIn("entry_pruned_zero_init_eval_only_fault_confirmed", eh2_bridge["missing_build_context"])
        self.assertIn("entry_pruned_cpp_verilator_runtime_residue_detected", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_host_cleanup_eval_only_did_not_clear_eval_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_host_cleanup_v2_eval_only_did_not_clear_eval_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_return_before_eval_launch_infrastructure_passed", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_prologue_pointer_setup_passed_before_eval_call", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_phase_act_call_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_phase_act_trigger_orinto_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_trigger_orinto_device_call_entry_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_trigger_orinto_entry_fault_not_stack_limit", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_inline_orinto_loads_before_store_pass", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_inline_orinto_store_to_vnba_triggered_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_adjacent_vact_triggered_store_passes", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_vnba_triggered_store_width_independent_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_entry_context_vnba_triggered_store_passes", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_padded2m_does_not_clear_eval_phase_vnba_store_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_maxr128_does_not_clear_eval_phase_vnba_store_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_phase_vnba_store_passes_with_direct_root", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_reference_wrapper_get_cvta_vnba_store_still_faults", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_minimal_eval_phase_vnba_store_passes", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_std_ref_get_canonical_eval_only_still_faults", eh2_bridge["missing_build_context"])
        self.assertIn(
            "eh2_std_ref_get_canonical_eval_prologue_passes_before_phase_act",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn("eh2_std_ref_get_canonical_one_phase_act_still_faults", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_std_ref_get_canonical_phase_act_orinto_still_faults", eh2_bridge["missing_build_context"])
        self.assertIn(
            "eh2_std_ref_get_canonical_trigger_orinto_before_store_passes",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn(
            "eh2_std_ref_get_canonical_trigger_orinto_dst_store_fault",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_canonicalization_did_not_clear_eval_fault",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_phase_act_before_orinto_passes",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_trigger_orinto_helper_call_entry_fault",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_orinto_rewrite_did_not_clear_eval_fault",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn(
            "eh2_orinto_store_value_or_store_itself_is_not_only_fault",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn("eh2_skip_store_before_anyset_passes", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_skip_store_trigger_anyset_passes", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_skip_store_timing_resume_passes", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_skip_store_eval_act_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_act_return_after_callseq_951_passes", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_act_return_after_callseq_952_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_act_dec_cam0_act_sequent_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_dec_cam0_minimal_body_call_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_act_dec_cam1_call_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertIn("eh2_eval_act_dec_tlu0_call_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertIn(
            "eh2_eval_act_first_three_submodule_act_calls_skipped_pass",
            eh2_bridge["missing_build_context"],
        )
        self.assertIn("eh2_eval_act_submodule_act_call_boundary_fault", eh2_bridge["missing_build_context"])
        self.assertEqual(
            eh2_bridge["next_required_boundary"],
            "fix EH2 eval_act submodule act call boundary CUDA700 before bridge comparison",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
