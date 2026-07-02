import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from verilator_native_sidecar_make_driver import (  # noqa: E402
    STATUS_BLOCKED_GPU_ARTIFACT_BUILD_FAILED,
    STATUS_BLOCKED_INIT_STATE_SANITIZE_FAILED,
    STATUS_BLOCKED_MISSING_MDIR,
    STATUS_BLOCKED_TEMPLATE,
    STATUS_BLOCKED_UNSUPPORTED_ARTIFACT,
    STATUS_BLOCKED_UNRECOGNIZED,
    STATUS_BLOCKED_VEER_EL2_GPU_STATE_IMAGE_LAUNCH,
    STATUS_BLOCKED_VEER_EL2_SIDECAR_EXECUTABLE,
    STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT,
    STATUS_BUILD_PLAN_READY,
    STATUS_VEER_EL2_SIDECAR_COMPARE_FAILED,
    STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED,
    build_direct_shim_smoke,
    inspect_veer_el2_state_layout,
    main as make_driver_main,
    materialize_veer_el2_state_image,
    plan_native_sidecar_build,
    prepare_direct_shim_smoke,
    run_veer_el2_sidecar_execution_bridge,
    run_native_sidecar_build,
    _build_vl_gpu_with_veer_el2_auto_syms_state_image,
    _veer_el2_root_image_materializer_review,
    _veer_el2_root_state_offset_review_from_layout,
)
import verilator_native_sidecar_make_driver as make_driver  # noqa: E402
from build_vl_gpu_metadata import (  # noqa: E402
    FC061_UNSUPPORTED_TRIGGER_VECTOR,
    ORDERING_AWARE_TOKEN_LOOP_SHAPE,
    PADDED_START_PAIR_CYCLE_LOOP_SHAPE,
    detect_fc061_direct_shim_artifact_compatibility,
    detect_schedule_lowering_capabilities,
)
from build_vl_gpu_hierarchy import detect_hierarchy_state_metadata  # noqa: E402
from build_vl_gpu_veer_flat_mem import patch_veer_el2_flat_program_mem  # noqa: E402
from veer_el2_sidecar_executable import (  # noqa: E402
    compute_rtlmeter_main_clock_cycles,
    materialize_veer_el2_syms_init_state,
    materialize_veer_el2_syms_init_states,
    parse_run_vl_hybrid_timing,
    reconstruct_veer_el2_stdout_from_final_observables,
    reconstruct_veer_el2_stdout_from_trace,
    write_veer_el2_clock_reset_patch_script,
)
import veer_el2_sidecar_executable as veer_sidecar_executable  # noqa: E402

KNOWN_TOP = "pulp_ita_mha_gpu_cov_tb"
KNOWN_TEMPLATE = "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json"
VEER_TOP = "tb_top"
VEER_AUTHORITY = "config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json"
VEER_PROGRAM_HEX = "third_party/rtlmeter/designs/VeeR-EL2/tests/hello/program.hex"
VEER_CMARK_PROGRAM_HEX = "third_party/rtlmeter/designs/VeeR-EL2/tests/cmark/program.hex"


class VerilatorNativeSidecarMakeDriverTest(HybridCliTestCase):
    def _known_entries(self) -> list[str]:
        template = json.loads((REPO_ROOT / KNOWN_TEMPLATE).read_text(encoding="utf-8"))
        return [str(item) for item in template["source_files"]]

    def _veer_entries(self) -> list[str]:
        authority = json.loads((REPO_ROOT / VEER_AUTHORITY).read_text(encoding="utf-8"))
        return [str(item) for item in authority["source_closure"]["filelist_entries"]]

    def _write_filelist(self, directory: Path, lines: list[str]) -> Path:
        filelist = directory / "native_known.f"
        filelist.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return filelist

    def test_veer_el2_sidecar_uses_resident_patch_schedule(self) -> None:
        mapped_fields = {
            "tb_top__DOT__core_clk": {"offset": 1, "size": 1},
            "tb_top__DOT__rst_l": {"offset": 2, "size": 1},
            "tb_top__DOT__porst_l": {"offset": 3, "size": 1},
            "observable:mailbox_write": {"offset": 4, "size": 1},
            "observable:obuf_data": {"offset": 5, "size": 1},
            "cycle:mcyclel": {"offset": 6, "size": 4},
            "cycle:minstretl": {"offset": 10, "size": 4},
            "pc:i0_pc_r_ff": {"offset": 14, "size": 4},
            "pc:tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d": {"offset": 18, "size": 4},
            "debug:i0_pc_r_ff_din": {"offset": 22, "size": 4},
            "debug:dec_i0_instr_d": {"offset": 26, "size": 4},
            "debug:dec_i0_branch_d": {"offset": 30, "size": 1},
            "debug:dec_i0_decode_d": {"offset": 31, "size": 1},
            "debug:dec_decode_valid_gate": {"offset": 32, "size": 1},
            "debug:dec_ib0_valid_d": {"offset": 33, "size": 1},
            "debug:dec_misc2ff_dout": {"offset": 34, "size": 1},
            "debug:dec_i0_exublock_d": {"offset": 35, "size": 1},
            "debug:dec_misc1ff_dout": {"offset": 156, "size": 1},
            "debug:dec_halt_ff_dout": {"offset": 157, "size": 4},
            "debug:dec_presync_stall": {"offset": 161, "size": 1},
            "debug:dec_lsu_idle": {"offset": 162, "size": 1},
            "debug:exu_div_valid_in": {"offset": 163, "size": 1},
            "debug:exu_div_running_state": {"offset": 164, "size": 1},
            "debug:exu_div_i_misc_ff_dout": {"offset": 165, "size": 4},
            "debug:exu_div_i_misc_ff_din": {"offset": 169, "size": 4},
            "debug:exu_div_shortq": {"offset": 173, "size": 1},
            "debug:exu_div_shortq_enable": {"offset": 174, "size": 1},
            "debug:exu_div_quotient_raw": {"offset": 175, "size": 2},
            "debug:exu_div_quotient_new": {"offset": 177, "size": 1},
            "debug:exu_div_dw_shortq_raw": {"offset": 178, "size": 1},
            "debug:exu_div_i_b_ff_dout": {"offset": 179, "size": 8},
            "debug:exu_div_i_b_ff_din": {"offset": 187, "size": 8},
            "debug:exu_div_a_ff": {"offset": 195, "size": 4},
            "debug:exu_div_q_ff": {"offset": 199, "size": 4},
            "debug:exu_div_r_ff": {"offset": 203, "size": 8},
            "debug:i0_brp_valid": {"offset": 36, "size": 1},
            "debug:i0_predict_nt": {"offset": 37, "size": 1},
            "debug:i0_predict_br": {"offset": 38, "size": 1},
            "debug:dec_tlu_i0_valid_r": {"offset": 39, "size": 1},
            "debug:i0_valid_no_ebreak_ecall_r": {"offset": 40, "size": 1},
            "debug:dma_dccm_stall_any": {"offset": 41, "size": 1},
            "debug:lsu_store_stall_any": {"offset": 42, "size": 1},
            "debug:dec_lsu_valid_raw_d": {"offset": 43, "size": 1},
            "debug:ifu_pmu_fetch_stall": {"offset": 44, "size": 1},
            "debug:ifu_pmu_instr_aligned": {"offset": 139, "size": 1},
            "debug:ifu_ifc_fbwrite_dout": {"offset": 45, "size": 2},
            "debug:ifu_ifc_fetch_consume_gate": {"offset": 47, "size": 1},
            "debug:dec_tlu_flush_err_r": {"offset": 48, "size": 1},
            "debug:dma_iccm_stall_any": {"offset": 49, "size": 1},
            "debug:ifu_mem_perr_state": {"offset": 50, "size": 1},
            "debug:ifu_mem_err_stop_state": {"offset": 51, "size": 1},
            "debug:exu_flush_final": {"offset": 52, "size": 1},
            "debug:dec_tlu_flush_lower_r": {"offset": 53, "size": 1},
            "debug:dec_tlu_flush_path_r": {"offset": 54, "size": 4},
            "debug:tb_ifu_axi_rvalid": {"offset": 58, "size": 1},
            "debug:tb_ifu_axi_rid": {"offset": 59, "size": 1},
            "debug:tb_ifu_axi_rresp": {"offset": 60, "size": 1},
            "debug:tb_ifu_axi_rdata": {"offset": 61, "size": 8},
            "debug:tb_mux_axi_rvalid": {"offset": 69, "size": 1},
            "debug:tb_sb_axi_rdata": {"offset": 70, "size": 8},
            "debug:tb_lmem_axi_rvalid": {"offset": 77, "size": 1},
            "debug:tb_lmem_axi_rdata": {"offset": 78, "size": 8},
            "debug:tb_ifu_axi_arready": {"offset": 86, "size": 1},
            "debug:ifu_bus_cmd_valid": {"offset": 87, "size": 1},
            "debug:ifu_bus_rd_addr_count": {"offset": 88, "size": 1},
            "debug:ifu_fetch_addr_f": {"offset": 89, "size": 4},
            "debug:ifu_pmp_addr": {"offset": 93, "size": 4},
            "debug:ifu_ifc_fetch_req_bf": {"offset": 97, "size": 1},
            "debug:ifu_ifc_fb_write_ns": {"offset": 98, "size": 1},
            "debug:ifu_ifc_miss_f": {"offset": 99, "size": 1},
            "debug:ifu_mem_miss_f": {"offset": 100, "size": 4},
            "debug:ifu_mem_miss_state": {"offset": 104, "size": 1},
            "debug:ifu_mem_miss_state_en": {"offset": 105, "size": 1},
            "debug:ifu_mem_write_ic_16_bytes": {"offset": 106, "size": 1},
            "debug:ifu_mem_ic_act_miss_f": {"offset": 107, "size": 1},
            "debug:ifu_ifc_fetch_ready": {"offset": 108, "size": 1},
            "debug:ifu_ifc_ic_hit_f": {"offset": 140, "size": 1},
            "debug:ifu_aln_aligndata": {"offset": 141, "size": 4},
            "debug:ifu_aln_alignfromf1": {"offset": 145, "size": 1},
            "debug:ifu_aln_brdata0_en": {"offset": 146, "size": 1},
            "debug:ifu_aln_brdata1_en": {"offset": 147, "size": 1},
            "debug:ifu_aln_brdata2_en": {"offset": 148, "size": 1},
            "debug:ifu_aln_shift_f1_f0": {"offset": 109, "size": 1},
            "debug:ifu_aln_shift_f2_f0": {"offset": 110, "size": 1},
            "debug:ifu_aln_shift_f2_f1": {"offset": 111, "size": 1},
            "debug:ifu_aln_sf0val": {"offset": 112, "size": 1},
            "debug:ifu_aln_sf1val": {"offset": 113, "size": 1},
            "debug:ifu_aln_bundle1": {"offset": 114, "size": 1},
            "debug:ifu_aln_bundle2": {"offset": 115, "size": 1},
            "debug:dec_tlu_flush_noredir_r": {"offset": 116, "size": 1},
            "debug:ifu_ic_fetch_val_f": {"offset": 117, "size": 1},
            "debug:ifu_iccm_rd_ecc_single_err": {"offset": 149, "size": 1},
            "debug:ifu_ic_error_start": {"offset": 150, "size": 1},
            "debug:dec_tlu_i0_commit_cmt": {"offset": 151, "size": 1},
            "debug:dec_tlu_freeff_dout": {"offset": 152, "size": 2},
            "debug:dec_tlu_freeff_din": {"offset": 154, "size": 2},
            "debug:ifu_aln_fetch_to_f0": {"offset": 118, "size": 1},
            "debug:ifu_aln_fetch_to_f1": {"offset": 119, "size": 1},
            "debug:ifu_aln_fetch_to_f2": {"offset": 120, "size": 1},
            "debug:ifu_aln_bundle1_din": {"offset": 121, "size": 1},
            "debug:ifu_aln_bundle2_din": {"offset": 122, "size": 1},
            "debug:root_act_triggered": {"offset": 123, "size": 8},
            "debug:root_nba_triggered": {"offset": 131, "size": 8},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_image = root / "state.json"
            state_image.write_text("{}\n", encoding="utf-8")
            execute_dir = root / "execute"
            mdir = root / "obj_dir"
            mdir.mkdir()
            (mdir / "vl_batch_gpu.meta.json").write_text(
                '{"storage_size": 16, "cubin": "vl_batch_gpu.cubin"}\n',
                encoding="utf-8",
            )

            captured: dict[str, object] = {}

            def fake_run(command, *, cwd, env, text, capture_output, check):
                captured["command"] = list(command)
                captured["env"] = dict(env)
                dump_path = Path(env["RUN_VL_HYBRID_DUMP_STATE"])
                dump_path.write_bytes(b"\0" * 16)
                Path(env["RUN_VL_HYBRID_STEP_TRACE"]).write_text(
                    (
                        "step,mcycle,minstret,pc,pc_d,pc_din,instr_d,branch_d,decode_d,"
                        "decode_valid_gate,decode_ib0_valid,decode_misc2ff,decode_i0_exublock,"
                        "decode_misc1ff,decode_halt_ff,decode_presync_stall,decode_lsu_idle,"
                        "exu_div_valid_in,exu_div_running_state,"
                        "exu_div_i_misc_ff,exu_div_i_misc_ff_din,exu_div_shortq,"
                        "exu_div_shortq_enable,exu_div_quotient_raw,exu_div_quotient_new,"
                        "exu_div_dw_shortq_raw,exu_div_i_b_ff,exu_div_i_b_ff_din,"
                        "exu_div_a_ff,exu_div_q_ff,exu_div_r_ff,"
                        "brp_valid,predict_nt,predict_br,i0_valid_r,i0_valid_tlu,dma_dccm_stall,"
                        "store_stall,lsu_valid,fetch_stall,ifu_pmu_instr_aligned,"
                        "fetch_fbwrite,fetch_consume_gate,"
                        "dec_flush_err,dma_iccm_stall,fetch_perr_state,fetch_err_stop_state,"
                        "exu_flush,flush_lower,flush_path,tb_ifu_axi_rvalid,tb_ifu_axi_rid,"
                        "tb_ifu_axi_rresp,tb_ifu_axi_rdata,tb_mux_axi_rvalid,tb_sb_axi_rdata,"
                        "tb_lmem_axi_rvalid,tb_lmem_axi_rdata,tb_ifu_axi_arready,"
                        "ifu_bus_cmd_valid,ifu_bus_rd_addr_count,ifu_fetch_addr_f,ifu_pmp_addr,"
                        "ifu_ifc_fetch_req_bf,ifu_ifc_fb_write_ns,ifu_ifc_miss_f,ifu_mem_miss_f,"
                        "ifu_mem_miss_state,ifu_mem_miss_state_en,ifu_mem_write_ic_16_bytes,"
                        "ifu_mem_ic_act_miss_f,ifu_ifc_fetch_ready,ifu_ifc_ic_hit_f,"
                        "ifu_aln_aligndata,ifu_aln_alignfromf1,ifu_aln_brdata0_en,"
                        "ifu_aln_brdata1_en,ifu_aln_brdata2_en,ifu_aln_shift_f1_f0,"
                        "ifu_aln_shift_f2_f0,ifu_aln_shift_f2_f1,ifu_aln_sf0val,"
                        "ifu_aln_sf1val,ifu_aln_bundle1,ifu_aln_bundle2,dec_tlu_flush_noredir_r,"
                        "ifu_ic_fetch_val_f,ifu_iccm_rd_ecc_single_err,ifu_ic_error_start,"
                        "dec_tlu_i0_commit_cmt,dec_tlu_freeff_dout,dec_tlu_freeff_din,"
                        "ifu_aln_bundle1_din,"
                        "root_act_triggered,root_nba_triggered,mailbox_write,obuf_data\n"
                    ),
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=(
                        "gpu_init_state_replication: true\n"
                        "resident_patch_schedule: logical=5 records=3 blocks=2\n"
                        "state_local_patch_schedule: logical=5 records=1 blocks=2\n"
                        "patch_eval_fusion: requested=true available=false launched=0 fallback=0 mode=state_grouped_patch_eval\n"
                        "pair_cycle_fusion: requested=true available=true launched=2 fallback=0 mode=low_eval_high_eval\n"
                        "pair_cycle_state_local_fusion: requested=true available=true launched=2 fallback=0 mode=state_local_low_eval_high_eval\n"
                        "step_trace_copy_mode: device_buffered_coalesced_d2d_trace\n"
                        "step_trace_filter: start=4 stride=2 rows=1 capacity=5\n"
                        "stage_timing_ms: after_cuInit=10.500 after_cuModuleLoad=20.250 before_launch_loop=0.125\n"
                        "gpu_kernel_time_ms: total=1.000 per_launch=0.001\n"
                    ),
                    stderr="",
                )

            with mock.patch.dict(
                veer_sidecar_executable.os.environ,
                {
                    veer_sidecar_executable.VEER_EL2_SIDECAR_STATE_IMAGE_ENV: state_image.as_posix(),
                    veer_sidecar_executable.VEER_EL2_SIDECAR_EXECUTE_DIR_ENV: execute_dir.as_posix(),
                    "VEER_EL2_SIDECAR_MDIR": mdir.as_posix(),
                    "VEER_EL2_SIDECAR_CLOCK_CYCLES": "1",
                    "VEER_EL2_SIDECAR_RTLMETER_POST_FINISH_CYCLES": "0",
                    "VEER_EL2_SIDECAR_CLOCK_PATCH_MODE": "resident_pair_cycle",
                    "VEER_EL2_SIDECAR_FUSED_PATCH_EVAL": "1",
                    "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE": "1",
                    "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP": "1",
                    "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK": "5000",
                    "VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING": "1",
                    "VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS": "3",
                },
                clear=False,
            ), mock.patch.object(
                veer_sidecar_executable,
                "_mapped_field_offsets_cached",
                return_value=(mapped_fields, {"status": "hit"}),
            ), mock.patch.object(
                veer_sidecar_executable,
                "materialize_veer_el2_syms_init_state",
                return_value=(b"\0" * 16, {}),
            ), mock.patch.object(
                veer_sidecar_executable,
                "_decode_gpu_observables",
                return_value={"mcycle": 1, "minstret": 1, "stdout": "TEST_PASSED\n"},
            ), mock.patch.object(
                veer_sidecar_executable,
                "reconstruct_veer_el2_stdout_from_trace",
                return_value={
                    "stdout": "TEST_PASSED\n",
                    "stdout_stream_reconstructed": True,
                    "mailbox_text": "TEST_PASSED\n",
                },
            ), mock.patch.object(
                veer_sidecar_executable,
                "ensure_hybrid_runtime_built",
                return_value=None,
            ), mock.patch.object(veer_sidecar_executable.subprocess, "run", side_effect=fake_run):
                self.assertEqual(veer_sidecar_executable.run_sidecar(root), 0)

            command = captured["command"]
            self.assertIsInstance(command, list)
            self.assertEqual(command[2:5], ["16", "2", "256"])
            self.assertTrue(str(command[1]).endswith("vl_batch_gpu.cubin"))
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_RESIDENT_STEPS"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_FUSED_PATCH_EVAL"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START"], "3")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_FUSED_PAIR_CYCLE"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK"], "5000")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_STAGE_TIMING"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_TIMING_REPEATS"], "3")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_GPU_REPLICATE_INIT_STATE"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_STEP_TRACE_DEVICE_BUFFER"], "1")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_STEP_TRACE_START"], "4")
            self.assertEqual(captured["env"]["RUN_VL_HYBRID_STEP_TRACE_STRIDE"], "2")
            trace_fields = captured["env"]["RUN_VL_HYBRID_STEP_TRACE_FIELDS"].split(",")
            self.assertIn("mcycle:198:4", trace_fields)
            self.assertIn("pc_d:210:4", trace_fields)
            self.assertIn("pc_din:214:4", trace_fields)
            self.assertIn("instr_d:218:4", trace_fields)
            self.assertIn("branch_d:222:1", trace_fields)
            self.assertIn("decode_valid_gate:224:1", trace_fields)
            self.assertIn("fetch_fbwrite:237:2", trace_fields)
            self.assertIn("flush_path:246:4", trace_fields)
            self.assertIn("tb_ifu_axi_rvalid:250:1", trace_fields)
            self.assertIn("tb_ifu_axi_rdata:253:8", trace_fields)
            self.assertIn("tb_lmem_axi_rdata:270:8", trace_fields)
            self.assertIn("tb_ifu_axi_arready:278:1", trace_fields)
            self.assertIn("ifu_bus_cmd_valid:279:1", trace_fields)
            self.assertIn("ifu_fetch_addr_f:281:4", trace_fields)
            self.assertIn("ifu_mem_miss_f:292:4", trace_fields)
            self.assertIn("mailbox_write:196:1", trace_fields)
            report = json.loads((execute_dir / "_sidecar/veer_el2_sidecar_executable_report.json").read_text())
            self.assertEqual(report["run_vl_hybrid_launcher_mode"], "direct_hybrid_runtime")
            self.assertTrue(report["run_vl_hybrid_timing"]["gpu_init_state_replication"])
            self.assertEqual(report["parallel_state_count"], 2)
            self.assertEqual(report["state_stride_bytes"], 16)
            self.assertEqual(report["init_replication_mode"], "device_kernel")
            self.assertEqual(report["patch_drive_scope"], "all_states")
            self.assertEqual(report["clock_reset_patch"]["patch_drive_scope"], "all_states")
            self.assertEqual(report["clock_reset_patch"]["patch_script_mode"], "resident_pair_cycle_low_high_eval")
            self.assertEqual(report["patch_apply_mode"], "device_resident_patch_schedule")
            self.assertEqual(report["run_vl_hybrid_timing"]["step_trace_copy_mode"], "device_buffered_coalesced_d2d_trace")
            self.assertEqual(
                report["run_vl_hybrid_timing"]["stage_timing_ms"]["after_cuModuleLoad"],
                20.25,
            )
            self.assertEqual(
                report["resident_patch_schedule"],
                {"logical": 5, "records": 3, "blocks": 2},
            )
            self.assertEqual(
                report["patch_eval_fusion"],
                {
                    "requested": True,
                    "available": False,
                    "launched": 0,
                    "fallback": 0,
                    "mode": "state_grouped_patch_eval",
                },
            )
            self.assertEqual(
                report["pair_cycle_fusion"],
                {
                    "requested": True,
                    "available": True,
                    "launched": 2,
                    "fallback": 0,
                    "mode": "low_eval_high_eval",
                },
            )
            self.assertEqual(
                report["run_vl_hybrid_timing"]["step_trace_filter"],
                {"start": 4, "stride": 2, "rows": 1, "capacity": 5},
            )
            self.assertEqual(report["step_trace_copy_mode"], "device_buffered_coalesced_d2d_trace")
            self.assertEqual(report["step_trace_filter"]["rows"], 1)
            self.assertEqual(report["step_trace_field_mode"], "mailbox_rising_edge_trace_final_counter_fallback")

    def test_veer_el2_sidecar_mixed_state_images_disable_device_init_replication(self) -> None:
        mapped_fields = {
            "tb_top__DOT__core_clk": {"offset": 1, "size": 1},
            "tb_top__DOT__rst_l": {"offset": 2, "size": 1},
            "tb_top__DOT__porst_l": {"offset": 3, "size": 1},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_images = []
            for name in ("dhry", "cmark", "cmark_iccm"):
                path = root / f"{name}.json"
                path.write_text(json.dumps({"program_sha256": f"sha256-{name}"}) + "\n", encoding="utf-8")
                state_images.append(path)
            execute_dir = root / "execute"
            mdir = root / "obj_dir"
            mdir.mkdir()
            (mdir / "vl_batch_gpu.meta.json").write_text(
                '{"storage_size": 16, "cubin": "vl_batch_gpu.cubin"}\n',
                encoding="utf-8",
            )

            captured: dict[str, object] = {}

            def fake_run(command, *, cwd, env, text, capture_output, check):
                captured["command"] = list(command)
                captured["env"] = dict(env)
                Path(env["RUN_VL_HYBRID_DUMP_STATE"]).write_bytes(b"\0" * 48)
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=(
                        "pair_cycle_loop_fusion: requested=true available=true kernel_launches=1 cycles=10 fallback=0 mode=low_high_eval_loop\n"
                        "gpu_kernel_time_ms: total=1.000 per_launch=0.100\n"
                    ),
                    stderr="",
                )

            with mock.patch.dict(
                veer_sidecar_executable.os.environ,
                {
                    veer_sidecar_executable.VEER_EL2_SIDECAR_STATE_IMAGES_ENV: os.pathsep.join(
                        path.as_posix() for path in state_images
                    ),
                    veer_sidecar_executable.VEER_EL2_SIDECAR_EXECUTE_DIR_ENV: execute_dir.as_posix(),
                    "VEER_EL2_SIDECAR_MDIR": mdir.as_posix(),
                    "VEER_EL2_SIDECAR_NSTATES": "3",
                    "VEER_EL2_SIDECAR_CLOCK_CYCLES": "10",
                    "VEER_EL2_SIDECAR_DISABLE_STEP_TRACE": "1",
                    "VEER_EL2_SIDECAR_CLOCK_PATCH_MODE": "resident_pair_cycle",
                    "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP": "1",
                },
                clear=True,
            ), mock.patch.object(
                veer_sidecar_executable,
                "_mapped_field_offsets_cached",
                return_value=(mapped_fields, {"status": "hit"}),
            ), mock.patch.object(
                veer_sidecar_executable,
                "materialize_veer_el2_syms_init_states",
                return_value=(
                    b"\x01" * 16 + b"\x02" * 16 + b"\x03" * 16,
                    {
                        "storage_size": 16,
                        "state_count": 3,
                        "mixed_state_preload": True,
                        "program_sha256s": ["sha256-dhry", "sha256-cmark", "sha256-cmark_iccm"],
                    },
                ),
            ), mock.patch.object(
                veer_sidecar_executable,
                "_decode_gpu_observables",
                return_value={"mcycle": 9, "minstret": 0, "stdout": ""},
            ), mock.patch.object(
                veer_sidecar_executable,
                "_parallel_state_observable_summary",
                return_value={
                    "parallel_state_validation_complete": True,
                    "parallel_state_observables_match": None,
                    "parallel_state_validation_scope": "mixed_init_all_states_final_observables",
                    "parallel_state_validation_status": "mixed_state_final_observables_recorded",
                    "states": [],
                },
            ), mock.patch.object(
                veer_sidecar_executable,
                "ensure_hybrid_runtime_built",
                return_value=None,
            ), mock.patch.object(veer_sidecar_executable.subprocess, "run", side_effect=fake_run):
                self.assertEqual(veer_sidecar_executable.run_sidecar(root), 0)

            command = captured["command"]
            env = captured["env"]
            self.assertIsInstance(command, list)
            self.assertEqual(command[2:4], ["16", "3"])
            self.assertNotIn("RUN_VL_HYBRID_GPU_REPLICATE_INIT_STATE", env)
            self.assertEqual(Path(env["RUN_VL_HYBRID_INIT_STATE"]).read_bytes(), b"\x01" * 16 + b"\x02" * 16 + b"\x03" * 16)
            report = json.loads((execute_dir / "_sidecar/veer_el2_sidecar_executable_report.json").read_text())
            self.assertIsNone(report["state_image"])
            self.assertEqual(
                report["state_images"],
                [f"{path.name}" for path in state_images],
            )
            self.assertEqual(report["parallel_state_count"], 3)
            self.assertEqual(report["init_replication_scope"], "per_state_mixed_init")
            self.assertEqual(report["init_replication_mode"], "host_uploaded_concatenated_state_images")
            self.assertTrue(report["materialized"]["mixed_state_preload"])

    def test_veer_el2_sidecar_step_trace_fields_include_progress_observables(self) -> None:
        spec = veer_sidecar_executable._trace_field_spec(
            root_offset=100,
            mapped_fields={
                "cycle:mcyclel": {"offset": 1, "size": 4},
                "cycle:minstretl": {"offset": 5, "size": 4},
                "pc:i0_pc_r_ff": {"offset": 9, "size": 4},
                "pc:tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d": {"offset": 13, "size": 4},
                "debug:i0_pc_r_ff_din": {"offset": 17, "size": 4},
                "debug:dec_i0_instr_d": {"offset": 21, "size": 4},
                "debug:dec_i0_branch_d": {"offset": 25, "size": 1},
                "debug:dec_i0_decode_d": {"offset": 26, "size": 1},
                "debug:dec_decode_valid_gate": {"offset": 27, "size": 1},
                "debug:dec_ib0_valid_d": {"offset": 28, "size": 1},
                "debug:dec_misc2ff_dout": {"offset": 29, "size": 1},
                "debug:dec_i0_exublock_d": {"offset": 30, "size": 1},
                "debug:dec_misc1ff_dout": {"offset": 154, "size": 1},
                "debug:dec_halt_ff_dout": {"offset": 155, "size": 4},
                "debug:dec_presync_stall": {"offset": 159, "size": 1},
                "debug:dec_lsu_idle": {"offset": 160, "size": 1},
                "debug:exu_div_valid_in": {"offset": 161, "size": 1},
                "debug:exu_div_running_state": {"offset": 162, "size": 1},
                "debug:exu_div_i_misc_ff_dout": {"offset": 163, "size": 4},
                "debug:exu_div_i_misc_ff_din": {"offset": 167, "size": 4},
                "debug:exu_div_shortq": {"offset": 171, "size": 1},
                "debug:exu_div_shortq_enable": {"offset": 172, "size": 1},
                "debug:exu_div_quotient_raw": {"offset": 173, "size": 2},
                "debug:exu_div_quotient_new": {"offset": 175, "size": 1},
                "debug:exu_div_dw_shortq_raw": {"offset": 176, "size": 1},
                "debug:exu_div_i_b_ff_dout": {"offset": 177, "size": 8},
                "debug:exu_div_i_b_ff_din": {"offset": 185, "size": 8},
                "debug:exu_div_a_ff": {"offset": 193, "size": 4},
                "debug:exu_div_q_ff": {"offset": 197, "size": 4},
                "debug:exu_div_r_ff": {"offset": 201, "size": 8},
                "debug:i0_brp_valid": {"offset": 31, "size": 1},
                "debug:i0_predict_nt": {"offset": 32, "size": 1},
                "debug:i0_predict_br": {"offset": 33, "size": 1},
                "debug:dec_tlu_i0_valid_r": {"offset": 34, "size": 1},
                "debug:i0_valid_no_ebreak_ecall_r": {"offset": 35, "size": 1},
                "debug:dma_dccm_stall_any": {"offset": 36, "size": 1},
                "debug:lsu_store_stall_any": {"offset": 37, "size": 1},
                "debug:dec_lsu_valid_raw_d": {"offset": 38, "size": 1},
                "debug:ifu_pmu_fetch_stall": {"offset": 39, "size": 1},
                "debug:ifu_pmu_instr_aligned": {"offset": 137, "size": 1},
                "debug:ifu_ifc_fbwrite_dout": {"offset": 40, "size": 2},
                "debug:ifu_ifc_fetch_consume_gate": {"offset": 42, "size": 1},
                "debug:dec_tlu_flush_err_r": {"offset": 43, "size": 1},
                "debug:dma_iccm_stall_any": {"offset": 44, "size": 1},
                "debug:ifu_mem_perr_state": {"offset": 45, "size": 1},
                "debug:ifu_mem_err_stop_state": {"offset": 46, "size": 1},
                "debug:exu_flush_final": {"offset": 47, "size": 1},
                "debug:dec_tlu_flush_lower_r": {"offset": 48, "size": 1},
                "debug:dec_tlu_flush_path_r": {"offset": 49, "size": 4},
                "debug:tb_ifu_axi_rvalid": {"offset": 53, "size": 1},
                "debug:tb_ifu_axi_rid": {"offset": 54, "size": 1},
                "debug:tb_ifu_axi_rresp": {"offset": 55, "size": 1},
                "debug:tb_ifu_axi_rdata": {"offset": 56, "size": 8},
                "debug:tb_mux_axi_rvalid": {"offset": 64, "size": 1},
                "debug:tb_sb_axi_rdata": {"offset": 65, "size": 8},
                "debug:tb_lmem_axi_rvalid": {"offset": 73, "size": 1},
                "debug:tb_lmem_axi_rdata": {"offset": 74, "size": 8},
                "debug:tb_ifu_axi_arready": {"offset": 82, "size": 1},
                "debug:ifu_bus_cmd_valid": {"offset": 83, "size": 1},
                "debug:ifu_bus_rd_addr_count": {"offset": 84, "size": 1},
                "debug:ifu_fetch_addr_f": {"offset": 85, "size": 4},
                "debug:ifu_pmp_addr": {"offset": 89, "size": 4},
                "debug:ifu_ifc_fetch_req_bf": {"offset": 93, "size": 1},
                "debug:ifu_ifc_fb_write_ns": {"offset": 94, "size": 1},
                "debug:ifu_ifc_miss_f": {"offset": 95, "size": 1},
                "debug:ifu_mem_miss_f": {"offset": 96, "size": 4},
                "debug:ifu_mem_miss_state": {"offset": 100, "size": 1},
                "debug:ifu_mem_miss_state_en": {"offset": 101, "size": 1},
                "debug:ifu_mem_write_ic_16_bytes": {"offset": 102, "size": 1},
                "debug:ifu_mem_ic_act_miss_f": {"offset": 103, "size": 1},
                "debug:ifu_ifc_fetch_ready": {"offset": 104, "size": 1},
                "debug:ifu_ifc_ic_hit_f": {"offset": 138, "size": 1},
                "debug:ifu_aln_aligndata": {"offset": 139, "size": 4},
                "debug:ifu_aln_alignfromf1": {"offset": 143, "size": 1},
                "debug:ifu_aln_brdata0_en": {"offset": 144, "size": 1},
                "debug:ifu_aln_brdata1_en": {"offset": 145, "size": 1},
                "debug:ifu_aln_brdata2_en": {"offset": 146, "size": 1},
                "debug:ifu_aln_shift_f1_f0": {"offset": 105, "size": 1},
                "debug:ifu_aln_shift_f2_f0": {"offset": 106, "size": 1},
                "debug:ifu_aln_shift_f2_f1": {"offset": 107, "size": 1},
                "debug:ifu_aln_sf0val": {"offset": 108, "size": 1},
                "debug:ifu_aln_sf1val": {"offset": 109, "size": 1},
                "debug:ifu_aln_bundle1": {"offset": 110, "size": 1},
                "debug:ifu_aln_bundle2": {"offset": 111, "size": 1},
                "debug:dec_tlu_flush_noredir_r": {"offset": 112, "size": 1},
                "debug:ifu_ic_fetch_val_f": {"offset": 113, "size": 1},
                "debug:ifu_iccm_rd_ecc_single_err": {"offset": 147, "size": 1},
                "debug:ifu_ic_error_start": {"offset": 148, "size": 1},
                "debug:dec_tlu_i0_commit_cmt": {"offset": 149, "size": 1},
                "debug:dec_tlu_freeff_dout": {"offset": 150, "size": 2},
                "debug:dec_tlu_freeff_din": {"offset": 152, "size": 2},
                "debug:ifu_aln_fetch_to_f0": {"offset": 114, "size": 1},
                "debug:ifu_aln_fetch_to_f1": {"offset": 115, "size": 1},
                "debug:ifu_aln_fetch_to_f2": {"offset": 116, "size": 1},
                "debug:ifu_aln_bundle1_din": {"offset": 117, "size": 1},
                "debug:ifu_aln_bundle2_din": {"offset": 118, "size": 1},
                "debug:root_act_triggered": {"offset": 119, "size": 8},
                "debug:root_nba_triggered": {"offset": 127, "size": 8},
                "observable:mailbox_write": {"offset": 135, "size": 1},
                "observable:obuf_data": {"offset": 136, "size": 1},
            },
        )

        fields = spec.split(",")
        self.assertEqual(len(fields), 96)
        self.assertIn("pc_din:117:4", fields)
        self.assertIn("instr_d:121:4", fields)
        self.assertIn("branch_d:125:1", fields)
        self.assertIn("decode_valid_gate:127:1", fields)
        self.assertIn("decode_misc1ff:254:1", fields)
        self.assertIn("decode_halt_ff:255:4", fields)
        self.assertIn("exu_div_valid_in:261:1", fields)
        self.assertIn("exu_div_running_state:262:1", fields)
        self.assertIn("exu_div_i_misc_ff:263:4", fields)
        self.assertIn("exu_div_i_misc_ff_din:267:4", fields)
        self.assertIn("exu_div_shortq:271:1", fields)
        self.assertIn("exu_div_quotient_raw:273:2", fields)
        self.assertIn("exu_div_i_b_ff:277:8", fields)
        self.assertIn("fetch_fbwrite:140:2", fields)
        self.assertIn("flush_path:149:4", fields)
        self.assertIn("tb_ifu_axi_rvalid:153:1", fields)
        self.assertIn("tb_ifu_axi_rdata:156:8", fields)
        self.assertIn("tb_lmem_axi_rdata:174:8", fields)
        self.assertIn("tb_ifu_axi_arready:182:1", fields)
        self.assertIn("ifu_bus_cmd_valid:183:1", fields)
        self.assertIn("ifu_fetch_addr_f:185:4", fields)
        self.assertIn("ifu_mem_miss_f:196:4", fields)
        self.assertIn("ifu_ifc_fetch_ready:204:1", fields)
        self.assertIn("ifu_aln_aligndata:239:4", fields)
        self.assertIn("ifu_aln_brdata2_en:246:1", fields)
        self.assertIn("ifu_aln_bundle2:211:1", fields)
        self.assertIn("dec_tlu_freeff_din:252:2", fields)
        self.assertIn("exu_div_i_b_ff_din:285:8", fields)
        self.assertIn("exu_div_a_ff:293:4", fields)
        self.assertIn("exu_div_q_ff:297:4", fields)
        self.assertIn("exu_div_r_ff:301:8", fields)
        self.assertIn("root_nba_triggered:227:8", fields)
        self.assertIn("mailbox_write:235:1", fields)

    def test_run_vl_hybrid_coalesces_device_buffered_step_trace_copies(self) -> None:
        source = (REPO_ROOT / "src/hybrid/run_vl_hybrid.c").read_text(encoding="utf-8")

        self.assertIn("CUdeviceptr d_coalesced_rows;", source)
        self.assertIn("host_coalesced_rows", source)
        self.assertIn("trace->d_coalesced_rows", source)
        self.assertIn("trace->coalesced_span", source)
        self.assertIn("RUN_VL_HYBRID_STEP_TRACE_START", source)
        self.assertIn("RUN_VL_HYBRID_STEP_TRACE_STRIDE", source)
        self.assertIn("#define MAX_STEP_TRACE_FIELDS 96", source)
        self.assertIn("should_write_step_trace", source)
        self.assertIn("cuMemcpyDtoDAsync(dst,", source)
        self.assertIn("d_storage + (CUdeviceptr)trace->coalesced_base", source)
        self.assertIn("row_base + field_base", source)

    def test_run_vl_hybrid_supports_optional_patch_eval_fusion(self) -> None:
        source = (REPO_ROOT / "src/hybrid/run_vl_hybrid.c").read_text(encoding="utf-8")

        self.assertIn("RUN_VL_HYBRID_FUSED_PATCH_EVAL", source)
        self.assertIn("RUN_VL_HYBRID_FUSED_PAIR_CYCLE", source)
        self.assertIn("RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP", source)
        self.assertIn("RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_FIRST_LAUNCH_DIAGNOSTIC", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_PROGRESS", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_PROGRESS_GLOBAL_DIAGNOSTIC", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_SYNC_AFTER_LAUNCH", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC", source)
        self.assertIn("ordering_aware_token_loop_high_patch_diagnostic:", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK", source)
        self.assertIn("ordering_aware_token_loop_progress_global:", source)
        self.assertIn("roundtrip_matches=%s", source)
        self.assertIn("resolve_optional_function_across_modules_with_index", source)
        self.assertIn("resolve_optional_global_in_module", source)
        self.assertIn("ordering_aware_token_loop_module_idx", source)
        self.assertIn("ordering_aware_progress_global_module_idx", source)
        self.assertIn("post_launch_sync_failed", source)
        self.assertIn("print_ordering_aware_token_loop_progress_snapshot", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_REGION_TIMING", source)
        self.assertIn("RUN_VL_HYBRID_ORDERING_AWARE_REGION_COUNTER_GLOBAL_INIT", source)
        self.assertIn("#define ORDERING_AWARE_REGION_TIMING_COUNTERS 16U", source)
        self.assertIn("ordering_aware_region_cycles:", source)
        self.assertIn("resolve_optional_global_across_modules", source)
        self.assertIn("__vlgpu_ordering_aware_region_cycle_counters", source)
        self.assertIn("before_ordering_aware_region_counter_global_init", source)
        self.assertIn("after_ordering_aware_region_counter_global_init", source)
        self.assertIn("memory_cluster=%llu", source)
        self.assertIn("select_mux_cluster=%llu", source)
        self.assertIn("branch_control_cluster=%llu", source)
        self.assertIn("active_eval_basic_blocks=%llu", source)
        self.assertIn("active_memory_candidate_blocks=%llu", source)
        self.assertIn("active_select_candidate_blocks=%llu", source)
        self.assertIn("select_mux_scoped_cycles=%llu", source)
        self.assertIn("select_mux_scoped_blocks=%llu", source)
        self.assertIn("d_ordering_aware_region_cycles", source)
        self.assertIn("parse_ordering_aware_terminal_mask_records", source)
        self.assertIn("OrderingAwareTerminalMaskTable", source)
        self.assertIn("upload_ordering_aware_terminal_mask_table", source)
        self.assertIn("canonical_terminal_steps", source)
        self.assertIn("launch_ordering_aware_token_loop_step", source)
        self.assertIn("current_phase_i", source)
        self.assertIn("terminal_mask_device_records", source)
        self.assertIn("device_table_launches", source)
        self.assertIn("state:terminal_step", source)
        self.assertIn("terminal_mask_parse_errors", source)
        self.assertIn("parse_unsigned_env_with_max(ENV_FUSED_PAIR_CYCLE_LOOP_CHUNK", source)
        self.assertIn("(unsigned long)INT_MAX", source)
        self.assertIn("RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE", source)
        self.assertIn("RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START", source)
        self.assertIn("RUN_VL_HYBRID_STATE_LOCAL_PATCHES", source)
        self.assertIn("vl_patch_eval_batch_gpu", source)
        self.assertIn("vl_patch_eval_pair_cycle_batch_gpu", source)
        self.assertIn("vl_patch_eval_pair_cycle_loop_batch_gpu", source)
        self.assertIn("vl_patch_eval_pair_cycle_batch_gpu_state_local", source)
        self.assertIn("resolve_optional_function_across_modules", source)
        self.assertIn("launch_fused_patch_eval_step", source)
        self.assertIn("launch_fused_pair_cycle_step", source)
        self.assertIn("launch_fused_pair_cycle_loop_step", source)
        self.assertIn("block_desc->step_count == 2U", source)
        self.assertIn("unsigned remaining_cycles = block_desc->repeat_count - repeat_idx", source)
        self.assertIn("repeat_idx += loop_cycles - 1U", source)
        self.assertIn("logical_step += loop_cycles * 2U", source)
        self.assertIn("launch_fused_pair_cycle_state_local_step", source)
        self.assertIn("patch_eval_fusion:", source)
        self.assertIn("pair_cycle_fusion:", source)
        self.assertIn("pair_cycle_loop_fusion:", source)
        self.assertIn("ordering_aware_token_loop_abi:", source)
        self.assertIn("launch_probe_count", source)
        self.assertIn("device_table_launch_count", source)
        self.assertIn("ordering_aware_token_loop_schedule_integrated_cpu_comparison_pending", source)
        self.assertIn("vl_tb_core_ordering_aware_phase_resident_token_loop_gpu", source)
        self.assertIn("runtime_launch_path_not_integrated", source)
        self.assertIn("missing_per_state_terminal_mask_records", source)
        self.assertIn("pair_cycle_state_local_fusion:", source)
        self.assertIn("state_local_patch_schedule:", source)
        self.assertIn("resident_pair_cycle:", source)
        self.assertIn("RUN_VL_HYBRID_STAGE_TIMING", source)
        self.assertIn("before_timing_repeat_snapshot", source)
        self.assertIn("cuMemcpyDtoD(d_initial_snapshot", source)
        self.assertIn("stage_timing_ms:", source)
        self.assertIn("state_grouped_patch_eval", source)
        sidecar_source = (REPO_ROOT / "src/tools/veer_el2_sidecar_executable.py").read_text(encoding="utf-8")
        self.assertIn("VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE", sidecar_source)
        self.assertIn("VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP", sidecar_source)
        self.assertIn("VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK", sidecar_source)
        self.assertIn("VEER_EL2_SIDECAR_DISABLE_STEP_TRACE", sidecar_source)
        self.assertIn("VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT", sidecar_source)
        self.assertIn("VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING", sidecar_source)
        self.assertIn("VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS", sidecar_source)
        self.assertIn("VEER_EL2_SIDECAR_STATE_LOCAL_PATCHES", sidecar_source)
        self.assertIn("RUN_VL_HYBRID_FUSED_PAIR_CYCLE", sidecar_source)
        self.assertIn("RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP", sidecar_source)
        self.assertIn("RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK", sidecar_source)
        self.assertIn("RUN_VL_HYBRID_STAGE_TIMING", sidecar_source)
        self.assertIn("RUN_VL_HYBRID_TIMING_REPEATS", sidecar_source)
        self.assertIn("RUN_VL_HYBRID_STEP_TRACE", sidecar_source)
        self.assertIn("disabled_final_observable_only", sidecar_source)
        self.assertIn("disabled_final_observable_stdout", sidecar_source)
        self.assertIn("RUN_VL_HYBRID_STATE_LOCAL_PATCHES", sidecar_source)

    def test_run_vl_hybrid_accepts_state_indexed_patch_tokens(self) -> None:
        source = (REPO_ROOT / "src/hybrid/run_vl_hybrid.c").read_text(encoding="utf-8")
        args_source = (REPO_ROOT / "src/tools/run_vl_hybrid_args.py").read_text(encoding="utf-8")

        self.assertIn("@state_index:state_local_byte_offset:value", source)
        self.assertIn("parse_state_indexed_patch", source)
        self.assertIn("parse_patch_for_storage", source)
        self.assertIn("state_index * storage", source)
        self.assertIn("want global_offset:byte or @state:local_offset:byte", source)
        self.assertIn("@STATE:LOCAL_OFF:BYTE", args_source)
        self.assertIn("#define MAX_PATCHES 4096", source)
        self.assertIn("RUN_VL_HYBRID_FEEDBACK_EDGES", source)
        self.assertIn("RUN_VL_HYBRID_FEEDBACK_EDGE_MODE", source)
        self.assertIn("RUN_VL_HYBRID_FEEDBACK_INCREMENTS", source)
        self.assertIn("RUN_VL_HYBRID_FEEDBACK_PHASE_SETS", source)
        self.assertIn("parse_feedback_edges", source)
        self.assertIn("parse_feedback_increments", source)
        self.assertIn("parse_feedback_phase_sets", source)
        self.assertIn("want phase:offset_local:value_byte or @state:phase:offset_local:value_byte", source)
        self.assertIn("feedback phase set state out of range", source)
        self.assertIn("sets->states", source)
        self.assertIn("sets->d_states", source)
        self.assertIn("upload_feedback_edge_table", source)
        self.assertIn("upload_feedback_increment_table", source)
        self.assertIn("upload_feedback_set_table", source)
        self.assertIn("launch_feedback_edges", source)
        self.assertIn("launch_feedback_increments", source)
        self.assertIn("launch_feedback_sets", source)
        self.assertIn("vl_apply_feedback_edges_gpu", source)
        self.assertIn("vl_apply_feedback_increments_gpu", source)
        self.assertIn("vl_apply_feedback_sets_gpu", source)
        self.assertIn("feedback_edges:", source)
        self.assertIn("feedback_increments:", source)
        self.assertIn("feedback_phase_sets:", source)
        self.assertIn("--feedback-edges", args_source)
        self.assertIn("--feedback-increments", args_source)
        self.assertIn("--feedback-phase-sets", args_source)
        self.assertIn("@STATE:PHASE:OFFSET_LOCAL:BYTE", args_source)
        self.assertIn("--feedback-edge-mode", args_source)

    def test_vlgpugen_emits_fused_patch_eval_kernel(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        self.assertIn("injectFusedPatchEvalKernel", source)
        self.assertIn("injectFusedPairCyclePatchEvalKernel", source)
        self.assertIn("injectFusedPairCycleLoopPatchEvalKernel", source)
        self.assertIn("injectFusedPairCyclePatchEvalStateLocalKernel", source)
        self.assertIn("vl_patch_eval_batch_gpu", source)
        self.assertIn("vl_patch_eval_pair_cycle_batch_gpu", source)
        self.assertIn("vl_patch_eval_pair_cycle_loop_batch_gpu", source)
        self.assertIn("vl_patch_eval_pair_cycle_batch_gpu_state_local", source)
        self.assertIn("patches_per_state", source)
        self.assertIn("injectFusedPatchEvalKernel(*M", source)
        self.assertIn("injectFusedPairCyclePatchEvalKernel(*M", source)
        self.assertIn("injectFusedPairCycleLoopPatchEvalKernel(", source)
        self.assertIn("injectOrderingAwarePhaseResidentTokenLoopKernel(", source)
        self.assertIn("injectFusedPairCyclePatchEvalStateLocalKernel(", source)
        self.assertIn("vl_tb_core_ordering_aware_phase_resident_token_loop_gpu", source)
        self.assertIn(
            "vl_tb_core_ordering_aware_phase_resident_token_loop_region_timing_gpu",
            source,
        )
        self.assertIn("OrderingAwareTokenLoopAbi", source)
        self.assertIn("OrderingAwareRegionTiming", source)
        self.assertIn("llvm.nvvm.read.ptx.sreg.clock64", source)
        self.assertIn("RecordRegionCycles", source)
        self.assertIn("instrumentOrderingAwareRegionClusterCounters", source)
        self.assertIn("cloneReachableEvalClosureForRegionTiming", source)
        self.assertIn(".__vlgpu_region_timing", source)
        self.assertIn("RegionTimingEvalCallees", source)
        self.assertIn("instrumentOrderingAwareRegionClusterCounters(M, RegionTimingEvalCallees)", source)
        self.assertIn("__vlgpu_ordering_aware_region_cycle_counters", source)
        self.assertIn("active_eval_basic_blocks.counter", source)
        self.assertIn("active_memory_candidate_blocks", source)
        self.assertIn("active_select_candidate_blocks", source)
        self.assertIn("select_mux_scoped_cycles.counter", source)
        self.assertIn("select_mux_scoped_blocks.counter", source)
        self.assertIn("select_mux_scoped.timing_thread", source)
        self.assertIn("vlgpu.select_mux_lowering_candidate", source)
        self.assertIn("prototype_select_mux_cluster_lowering_from_scoped_hook", source)
        self.assertIn("select_mux_scoped_cycles.prev", source)
        self.assertIn("select_mux_scoped_cycles.next", source)
        self.assertIn("select_mux_scoped_blocks.prev", source)
        self.assertIn("select_mux_scoped_blocks.next", source)
        self.assertIn("applyOrderingAwareSelectMuxClusterTransform", source)
        self.assertIn("applyOrderingAwareSelectMuxClusterTransform(M, EvalCallees)", source)
        self.assertLess(
            source.index("applyOrderingAwareSelectMuxClusterTransform(M, EvalCallees)"),
            source.index("applyOrderingAwareEvalHotPathPartitionPrototype(M, EvalCallees)"),
        )
        self.assertIn("vlgpu.select_mux.rewritten", source)
        self.assertIn("select_mux_identity_rewritten", source)
        self.assertIn("vlgpu.select_mux_cluster_transform", source)
        self.assertIn("vlgpu.select_mux_cluster_transform_summary", source)
        self.assertIn("prototype_select_mux_cluster_transform_after_isolated_cpu_gpu_probe", source)
        self.assertIn("hoisted_low_patches_per_state", source)
        self.assertIn("hoisted_high_patches_per_state", source)
        self.assertIn("hoisted_pair_record_span", source)
        self.assertIn("hoisted_low_patch_state_base", source)
        self.assertIn("hoisted_high_patch_state_base", source)
        self.assertIn("applyOrderingAwareEvalHotPathPartitionPrototype", source)
        self.assertIn("vlgpu.eval_hot_path.partition.cont", source)
        self.assertIn("vlgpu.eval_hot_path_partition", source)
        self.assertIn("vlgpu.eval_hot_path_partition_summary", source)
        self.assertIn("prototype_eval_hot_path_partition_after_select_mux_transform_cpu_negative", source)
        self.assertIn("vlgpu.eval_hot_path_active_block_gate", source)
        self.assertIn("vlgpu.eval_hot_path_active_block_gate_summary", source)
        self.assertIn("prototype_eval_hot_path_active_block_gate_after_partition_cpu_negative", source)
        self.assertIn("vlgpu.eval_hot_path_cold_partition_skip_summary", source)
        self.assertIn("vlgpu.eval_hot_path_cold_partition_skip_rejected", source)
        self.assertIn("prototype_eval_hot_path_cold_partition_skip_after_active_block_gate_cpu_negative", source)
        self.assertIn("markOrderingAwareDirectEvalPredicatePointerAbi", source)
        self.assertIn("markOrderingAwareDirectEvalPredicatePointerCall", source)
        self.assertIn("vlgpu.direct_eval_predicate_pointer_abi", source)
        self.assertIn("vlgpu.eval_predicate_pointer", source)
        self.assertIn("eval_predicate_partition_ids", source)
        self.assertIn("eval.predicate.read.no_skip", source)
        self.assertIn("vlgpu.eval_predicate_pointer_read_no_skip", source)
        self.assertIn("predicate_read_observation_only_no_skip", source)
        self.assertIn("eval.predicate.guarded_skip.scan", source)
        self.assertIn("vlgpu.eval_predicate_guarded_cold_partition_skip", source)
        self.assertIn("eval.predicate.guarded_skip.bitmap", source)
        self.assertIn("vlgpu.eval_predicate_active_bitmap_guard", source)
        self.assertIn("eval_predicate_active_bitmap", source)
        self.assertIn("eval_predicate_active_bitmap_partition_count", source)
        self.assertIn("eval_predicate_active_bitmap_partition_idx", source)
        self.assertIn("eval_predicate_active_bitmap_partition_index", source)
        self.assertIn("eval_predicate_guarded_skip_enabled", source)
        self.assertIn(
            "prototype_constant_time_phase_state_active_bitmap_guard_after_guarded_skip_cpu_negative",
            source,
        )
        self.assertIn("ClusterRegionCounterGlobal", source)
        self.assertIn('Kernel->getArg(7)->setName("current_phase")', source)
        self.assertIn("phase_control_phases", source)
        self.assertIn("feedback_copy_src_offsets", source)
        self.assertIn("terminal_mask_steps", source)
        self.assertIn("terminal.mask.direct", source)
        self.assertIn("terminal_mask_direct_step", source)
        self.assertIn("terminal.mask.cond", source)
        self.assertIn("terminal_phase_active", source)
        self.assertIn("terminal_feedback_active", source)
        self.assertIn("ArrayRef<Function *> EvalCallees", source)
        self.assertIn("PairCycleLoopCallees.push_back(IcoFn)", source)
        self.assertIn("PairCycleLoopCallees.push_back(EvalLoopWrapper)", source)
        self.assertIn("progress_low_eval_active_predicate", source)
        self.assertIn("progress_entry_prologue_progress_global_loaded", source)
        self.assertIn("progress_entry_prologue_eval_predicate_context_stored", source)
        self.assertIn("progress_entry_prologue_gid_computed", source)
        self.assertIn("progress_entry_prologue_context_globals_stored", source)
        self.assertIn("Store->setVolatile(true)", source)
        self.assertIn("progress_low_eval_predicate_gate", source)
        self.assertIn("progress_low_eval_call_path", source)
        self.assertIn("progress_low_eval_callee_count", source)
        self.assertIn("progress_low_eval_before_callee", source)
        self.assertIn("progress_low_eval_after_callee", source)
        self.assertIn("progress_low_eval_done", source)
        self.assertIn("progress_high_patch_entry", source)
        self.assertIn("progress_high_patch_cond", source)
        self.assertIn("progress_high_patch_index", source)
        self.assertIn("progress_high_patch_count", source)
        self.assertIn("progress_high_patch_cond_record", source)
        self.assertIn("progress_high_patch_body", source)
        self.assertIn("progress_high_patch_record", source)
        self.assertIn("progress_high_patch_stage70_offset_after_load", source)
        self.assertIn("progress_high_patch_offset", source)
        self.assertIn("progress_high_patch_store_done", source)
        self.assertIn("progress_high_eval_predicate_gate", source)
        self.assertIn("progress_high_eval_call_path", source)
        self.assertIn("progress_high_eval_callee_count", source)
        self.assertIn("progress_high_eval_before_callee", source)
        self.assertIn("progress_high_eval_after_callee", source)
        self.assertIn("progress_high_eval_done", source)

        runtime_source = (REPO_ROOT / "src/hybrid/run_vl_hybrid.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("eval_partition_predicate_read_no_skip", runtime_source)
        self.assertIn("volatile_read_no_control_flow", runtime_source)
        self.assertIn("int apply_phase_controls", runtime_source)
        self.assertIn("int apply_feedback", runtime_source)
        self.assertIn("ordering_chunk_starts_phase", runtime_source)
        self.assertIn("ordering_chunk_applies_feedback", runtime_source)
        self.assertIn(
            "phase controls cannot be continued across chunk boundaries",
            runtime_source,
        )
        self.assertIn(
            "apply_phase_controls && sets && sets->set_count",
            runtime_source,
        )
        self.assertIn(
            "apply_feedback && edges && edges->edge_count",
            runtime_source,
        )

    def test_vlgpugen_phase_split_uses_eval_phase_nba_loop(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        self.assertIn("createEvalLoopWrapper", source)
        self.assertIn("injectEvalLoopKernelIfReachable", source)
        self.assertIn('"___eval_loop"', source)
        self.assertIn('"vl_eval_loop_batch_gpu"', source)
        self.assertIn('"__vlgpu_eval_loop_wrapper"', source)
        self.assertIn("continue_eval_outer_loop", source)
        self.assertIn("veer-aln-post-nba-recompute", source)
        self.assertIn("collectVeeRAlnPostNbaRecomputeFns", source)
        self.assertIn("post_nba_recompute", source)
        self.assertIn('"___nba_comb__TOP__18"', source)
        self.assertIn('"___eval_phase__nba"', source)
        self.assertIn('"vl_nba_loop_batch_gpu"', source)
        self.assertIn('"__vlgpu_eval_phase_nba_loop_wrapper"', source)
        self.assertIn("if (!UsedEvalLoop && !UsedNbaLoop && EvalNba)", source)
        self.assertIn("if (!UsedEvalLoop && !UsedNbaLoop && !UsedGuardedSegments)", source)
        self.assertIn("SymsSelfPointerOffsets, Manifest", source)

    def test_vlgpugen_keeps_top_level_phase_closure_for_root_images(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        self.assertIn("collectTopLevelEvalPhaseClosures(*M, EvalFn, Reach);", source)
        self.assertNotIn(
            "if (StateRootOffset != 0)\n        collectTopLevelEvalPhaseClosures",
            source,
        )

    def test_vlgpugen_commits_selected_phi_value_to_liveout_valid_frame(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        payload_marker = (
            "entry_phi_selected_incoming_value_materialized_clone_edge_payload_store"
        )
        valid_marker = (
            "entry_phi_selected_incoming_value_valid_frame_store_for_compare_mask_no_authority"
        )
        self.assertIn(payload_marker, source)
        self.assertIn(valid_marker, source)
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_value_valid_frame_store",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_value_actual_valid_store_site_reached_sample",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_value_actual_valid_store_reload_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_value_actual_valid_store_reload_sample_after_store_no_return_compare_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_value_actual_valid_all_slot_store_site_reached_sample",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_value_actual_valid_all_slot_store_reload_sample",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_value_materialization_block_entry_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_value_materialization_block_entry_before_encode_no_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_value_materialization_block_first_entry_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_value_materialization_block_first_entry_before_body_no_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_candidate_visited_runtime_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_candidate_visited_entry_runtime_sample_no_materialize_or_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_materialize_block_selected_runtime_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_materialize_block_selected_entry_runtime_sample_no_block_entry_or_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_dispatch_before_materialize_runtime_counter",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_dispatch_before_materialize_runtime_counter_no_materialize_or_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_materialize_block_match_status_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_materialize_block_match_status_sample_no_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_materialize_block_placement_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_materialize_block_placement_sample_no_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_selected_incoming_candidate_edge_matches_materialize_edge_sample",
            source,
        )
        self.assertIn(
            "entry_phi_selected_incoming_candidate_edge_matches_materialize_edge_sample_no_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_producer_predecessor_selector_return_compare_proxy_materialize_edge_match_sample",
            source,
        )
        self.assertIn(
            "entry_phi_producer_predecessor_selector_return_compare_proxy_materialize_edge_match_sample_no_actual_valid_authority",
            source,
        )
        self.assertIn(
            "vlgpu.eval_hot_path_compact_cluster_entry_phi_producer_predecessor_selector_return_compare_proxy_candidate_runtime_while_materialize_zero_sample",
            source,
        )
        self.assertIn(
            "entry_phi_producer_predecessor_selector_return_compare_proxy_candidate_runtime_while_materialize_zero_sample_no_actual_valid_authority",
            source,
        )
        self.assertIn(
            "++BodyCloneProbeCfgCloneSelectorGatedMaterializationAuthorizedCount",
            source,
        )
        self.assertIn(
            "selector_actual_valid_value_semantic_commit_ready_no_runtime_authority",
            source,
        )
        self.assertLess(source.index(payload_marker), source.index(valid_marker))

    def test_vlgpugen_std_ref_stub_returns_referenced_pointer(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        self.assertIn("isStdReferenceWrapperRefFunction", source)
        self.assertIn("isStdReferenceWrapperGetFunction", source)
        self.assertIn("canonicalizeStdReferenceWrapperGetCalls(*M);", source)
        self.assertIn('Name.starts_with("_ZSt3refI")', source)
        self.assertIn('Name.contains("St17reference_wrapper")', source)
        self.assertIn('Name.starts_with("_ZNKSt17reference_wrapperI")', source)
        self.assertIn('Name.contains("E3getEv")', source)
        self.assertIn("findStoredStdRefArgumentForWrapper", source)
        self.assertIn("Call->replaceAllUsesWith(RootArg);", source)
        self.assertIn("F.getReturnType()->isPointerTy()", source)
        self.assertIn("F.getFunctionType()->getParamType(0)->isPointerTy()", source)
        self.assertIn("B.CreateRet(F.getArg(0));", source)

    def test_vlgpugen_canonicalizes_single_element_vlunpacked_index_calls(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        self.assertIn("isVlUnpackedSingleElementIndexFunction", source)
        self.assertIn("canonicalizeVlUnpackedSingleElementIndexCalls(*M);", source)
        self.assertIn('Name.contains("Lm1EEixE")', source)
        self.assertIn("Call->replaceAllUsesWith(Call->getArgOperand(0));", source)
        self.assertIn("VlUnpacked<T,1> index calls canonicalized", source)
        self.assertLess(
            source.index("if (isStdReferenceWrapperRefFunction(F))"),
            source.index("else if (Ret->isPointerTy())"),
        )

    def test_vlgpugen_canonicalizes_vlwide_pointer_conversion_calls(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        self.assertIn("isVlWidePointerConversionFunction", source)
        self.assertIn("canonicalizeVlWidePointerConversionCalls(*M);", source)
        self.assertIn('Name.starts_with("_ZN6VlWideI")', source)
        self.assertIn('Name.starts_with("_ZNK6VlWideI")', source)
        self.assertIn('Name.contains("EEcvPjEv")', source)
        self.assertIn('Name.contains("EEcvPKjEv")', source)
        self.assertIn("Call->replaceAllUsesWith(Call->getArgOperand(0));", source)
        self.assertIn("VlWide pointer conversions canonicalized", source)
        self.assertLess(
            source.index("canonicalizeVlUnpackedSingleElementIndexCalls(*M);"),
            source.index("canonicalizeVlWidePointerConversionCalls(*M);"),
        )
        self.assertLess(
            source.index("canonicalizeVlWidePointerConversionCalls(*M);"),
            source.index("rewriteEh2VlUnpackedLm1TriggerOrIntoCalls(*M);"),
        )

    def test_vlgpugen_rewrites_only_eh2_lm1_trigger_orinto_helper_calls(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(encoding="utf-8")

        self.assertIn("isEh2VlUnpackedLm1TriggerOrIntoFunction", source)
        self.assertIn("rewriteEh2VlUnpackedLm1TriggerOrIntoCalls(*M);", source)
        self.assertIn(
            'Name.starts_with("_Z36Vsim___024root___trigger_orInto__actR10VlUnpackedImLm1EERKS0_")',
            source,
        )
        self.assertIn("F.getReturnType()->isVoidTy()", source)
        self.assertIn("dyn_cast<CallInst>(&I)", source)
        self.assertIn("B.CreateAlignedLoad(I64Ty, Dst, Align(8),", source)
        self.assertIn("B.CreateAlignedLoad(I64Ty, Src, Align(8),", source)
        self.assertIn('B.CreateOr(DstValue, SrcValue, "eh2.orinto.or")', source)
        self.assertIn("B.CreateAlignedStore(OrValue, Dst, Align(8));", source)
        self.assertIn("EH2 VlUnpacked<T,1> trigger_orInto calls rewritten", source)
        self.assertLess(
            source.index("canonicalizeVlUnpackedSingleElementIndexCalls(*M);"),
            source.index("rewriteEh2VlUnpackedLm1TriggerOrIntoCalls(*M);"),
        )

    def _write_minimal_veer_root_header(
        self,
        mdir: Path,
        *,
        include_mailbox_data: bool = True,
        omit_gpr_indices: set[int] | None = None,
        omit_dccm_bank: int | None = None,
        omit_iccm_bank: int | None = None,
    ) -> Path:
        root_header = mdir / "Vsim___024root.h"
        mailbox_data_lines = ["QData/*63:0*/ tb_top__DOT__mailbox_data;"] if include_mailbox_data else []
        omitted = omit_gpr_indices or set()
        dccm_bank_lines = [
            "VlUnpacked<QData/*38:0*/, 4096> "
            "tb_top__DOT__Gen_dccm_enable__DOT__dccm_loop__BRA__"
            f"{index}__KET____DOT__dccm__DOT__dccm_bank__DOT__ram_core;"
            for index in range(4)
            if index != omit_dccm_bank
        ]
        iccm_bank_lines = [
            "VlUnpacked<QData/*38:0*/, 4096> "
            "tb_top__DOT__Gen_iccm_enable__DOT__iccm_loop__BRA__"
            f"{index}__KET____DOT__iccm__DOT__iccm_bank__DOT__ram_core;"
            for index in range(4)
            if index != omit_iccm_bank
        ]
        root_header.write_text(
            "\n".join([
                "CData/*0:0*/ tb_top__DOT__core_clk;",
                "CData/*0:0*/ tb_top__DOT__rst_l;",
                "CData/*0:0*/ tb_top__DOT__porst_l;",
                "CData/*0:0*/ tb_top__DOT__mailbox_write;",
                *mailbox_data_lines,
                "IData/*30:0*/ tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d;",
                "IData/*30:0*/ tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__i0_pc_r_ff__dout;",
                "IData/*31:0*/ tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__mcyclel;",
                "IData/*31:0*/ tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__minstretl;",
                *[
                    "IData/*31:0*/ tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__arf__DOT____Vcellout__gpr__BRA__"
                    f"{index}__KET____DOT__gprff__dout;"
                    for index in range(1, 32)
                    if index not in omitted
                ],
                "VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__imem__DOT__mem;",
                "VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__lmem__DOT__mem;",
                *dccm_bank_lines,
                *iccm_bank_lines,
                "",
            ]),
            encoding="utf-8",
        )
        (mdir / "Vsim___024root__memory.cpp").write_text(
            "\n".join([
                "IData tb_top___024root___get_dccm_bank(IData addr) { return addr; }",
                "IData tb_top___024root___get_iccm_bank(IData addr) { return addr; }",
                "IData preload_dccm_start = 0xfffffff8U;",
                "IData preload_iccm_start = 0xfffffff0U;",
                "IData dccm_sadr = 0xf0040000U;",
                "IData dccm_eadr = 0xf004ffffU;",
                "IData iccm_sadr = 0xee000000U;",
                "IData iccm_eadr = 0xee00ffffU;",
                "",
            ]),
            encoding="utf-8",
        )
        return root_header

    def _write_minimal_veer_observable_cpp(self, mdir: Path) -> Path:
        root_cpp = mdir / "Vsim___024root__0.cpp"
        root_cpp.write_text(
            "\n".join([
                "vlSelfRef.tb_top__DOT__mailbox_write = ((IData)(vlSelfRef.tb_top__DOT__lmem_axi_awvalid)",
                " & ((0xd0580000U == vlSelfRef.tb_top__DOT__lsu_axi_awaddr) & (IData)(vlSelfRef.tb_top__DOT__rst_l)));",
                "if ((IData)(vlSelfRef.tb_top__DOT__mailbox_write)) {",
                "  VL_WRITEF_NX(\"%c\",0,8,(0x000000ffU & (IData)(vlSelfRef.tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__lsu__DOT__bus_intf__DOT__bus_buffer__DOT__obuf_data)));",
                "  VL_WRITEF_NX(\"TEST_PASSED\\n\\nFinished : minstret = %0#, mcycle = %0#\\n\",0,",
                "    32,vlSelfRef.tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__minstretl,",
                "    32,vlSelfRef.tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__mcyclel);",
                "  VL_WRITEF_NX(\"TEST_FAILED\\n\",0);",
                "}",
                "",
            ]),
            encoding="utf-8",
        )
        return root_cpp

    def _assert_fail_closed_non_claims(self, report: dict) -> None:
        self.assertTrue(report["fail_closed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["speedup_claimed"])
        self.assertTrue(report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def _write_minimal_state_image(self, directory: Path) -> Path:
        state_image = directory / "veer_state_image.json"
        state_image.write_text(
            json.dumps(
                {
                    "schema_role": "veer_el2_extracted_preload_state_image",
                    "target": "rtlmeter_veer_el2_default_hello",
                    "state_image_kind": "veer_el2_extracted_preload_image",
                    "sections": {
                        "program_staging_lmem": [],
                        "program_staging_imem": [],
                        "dccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {}},
                        "iccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {}},
                        "control_scalars": {
                            "tb_top__DOT__core_clk": 0,
                            "tb_top__DOT__rst_l": 0,
                            "tb_top__DOT__porst_l": 0,
                        },
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return state_image

    def _write_rtlmeter_observables(self, execute_dir: Path, *, stdout_text: str, cycles: int) -> None:
        (execute_dir / "_execute").mkdir(parents=True, exist_ok=True)
        (execute_dir / "_execute" / "stdout.log").write_text(stdout_text, encoding="utf-8")
        (execute_dir / "_rtlmeter_cycles.txt").write_text(f"{cycles}\n", encoding="utf-8")

    def _write_veer_gpu_meta_with_prelaunch_rejection(self, mdir: Path) -> None:
        (mdir / "vl_batch_gpu.meta.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "cubin": "vl_batch_gpu.cubin",
                    "storage_size": 300352,
                    "kernel": "vl_eval_batch_gpu",
                    "hierarchy_state": {
                        "state_image_kind": "root_image",
                        "root_storage_size": 300352,
                        "syms_storage_size": 302528,
                        "root_offset_in_syms": 192,
                        "unsafe_syms_gep_count": 1085,
                        "unsafe_syms_gep_covered_by_state_image": False,
                        "prelaunch_rejection_required": True,
                        "metadata_source": "vl_batch_gpu_opt.ll",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_veer_gpu_meta_with_syms_state_image(self, mdir: Path) -> None:
        (mdir / "vl_batch_gpu.meta.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "cubin": "vl_batch_gpu.ptx",
                    "storage_size": 433472,
                    "kernel": "vl_eval_batch_gpu",
                    "hierarchy_state": {
                        "state_image_kind": "verilator_syms_image",
                        "root_storage_size": 431296,
                        "syms_storage_size": 433472,
                        "root_offset_in_syms": 192,
                        "root_offset_in_state": 192,
                        "unsafe_syms_gep_count": 558,
                        "unsafe_syms_gep_covered_by_state_image": True,
                        "prelaunch_rejection_required": False,
                        "nonflat_assoc_array_detected": False,
                        "assoc_array_gpu_lowering_supported": True,
                        "metadata_source": "vl_batch_gpu_opt.ll",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_veer_sidecar_executable_review(self, executable: Path) -> Path:
        review = executable.with_name(f"{executable.name}.review.json")
        review.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "schema_role": "veer_el2_sidecar_executable_review",
                    "target": "rtlmeter_veer_el2_default_hello",
                    "executable_path": executable.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
                    "state_image_env": "VEER_EL2_SIDECAR_STATE_IMAGE",
                    "execute_dir_env": "VEER_EL2_SIDECAR_EXECUTE_DIR",
                    "emits_rtlmeter_observables": True,
                    "copies_cpu_observables": False,
                    "cpu_as_gpu_fallback_allowed": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return review

    def test_unrecognized_closure_blocks_build_plan(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = plan_native_sidecar_build(
                filelist_path=self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"]),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_UNRECOGNIZED)
        self.assertFalse(report["build_plan_ready"])
        self.assertIn("recognized_known_closure", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_recognized_closure_without_verilated_mdir_blocks(self) -> None:
        # A recognized closure still fails closed until the mdir has *_classes.mk.
        # Use a controlled registry pointing at an empty mdir so the result does
        # not depend on leftover local verilated obj_dirs under artifacts/.
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, _mdir = self._registry_with_local_mdir(tmp_path)
            report = plan_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_MISSING_MDIR)
        self.assertEqual(report["target"], "pulp_ita_mha")
        self.assertIn("verilated_mdir_classes_mk", report["missing_build_context"])
        self.assertFalse(report["mdir_verilated"])
        self._assert_fail_closed_non_claims(report)

    def test_recognized_closure_with_verilated_mdir_is_plan_ready(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = plan_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
            )
        self.assertEqual(report["status"], STATUS_BUILD_PLAN_READY)
        self.assertTrue(report["build_plan_ready"])
        self.assertTrue(report["mdir_verilated"])
        self.assertEqual(report["missing_build_context"], [])
        self._assert_fail_closed_non_claims(report)

    def test_run_does_not_invoke_template_flow_when_blocked(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(argv):
            calls.append(argv)
            return 0

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = run_native_sidecar_build(
                filelist_path=self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"]),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                template_runner=fake_runner,
            )
        self.assertEqual(calls, [])
        self.assertFalse(report["template_flow_invoked"])
        self.assertFalse(report["template_flow_passed"])
        self.assertEqual(report["status"], STATUS_BLOCKED_UNRECOGNIZED)

    def test_run_delegates_recognized_closure_to_template_flow(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(argv):
            calls.append(argv)
            return 0

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = run_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                shape="64x1",
                template_runner=fake_runner,
            )
        self.assertEqual(len(calls), 1)
        argv = calls[0]
        self.assertIn("--shape", argv)
        self.assertEqual(argv[argv.index("--shape") + 1], "64x1")
        self.assertTrue(argv[0].endswith(".json"))
        self.assertTrue(report["template_flow_invoked"])
        self.assertTrue(report["template_flow_passed"])

    def test_run_records_template_flow_failure_without_passing(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = run_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                template_runner=lambda argv: 1,
            )
        self.assertTrue(report["template_flow_invoked"])
        self.assertFalse(report["template_flow_passed"])
        self.assertEqual(report["template_flow_returncode"], 1)

    def test_run_blocks_recognized_rtlmeter_closure_without_runtime_template(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(argv):
            calls.append(argv)
            return 0

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = run_native_sidecar_build(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                template_runner=fake_runner,
            )
        self.assertEqual(calls, [])
        self.assertEqual(report["status"], STATUS_BLOCKED_TEMPLATE)
        self.assertFalse(report["build_plan_ready"])
        self.assertIn("launch_template", report["missing_build_context"])
        self.assertFalse(report["template_flow_invoked"])
        self.assertFalse(report["template_flow_passed"])
        self._assert_fail_closed_non_claims(report)

    def test_inspect_veer_el2_state_layout_finds_markers_but_blocks_gpu_claim(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            report = inspect_veer_el2_state_layout(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT)
        self.assertEqual(report["target"], "rtlmeter_veer_el2_default_hello")
        self.assertFalse(report["build_plan_ready"])
        self.assertTrue(report["state_layout_inspection_performed"])
        self.assertFalse(report["state_layout_ready"])
        detected = report["detected_layout"]
        self.assertTrue(detected["reset_clock_fields_found"])
        self.assertTrue(detected["preload_memories_found"])
        self.assertTrue(detected["observable_fields_found"])
        self.assertTrue(detected["cycle_counter_fields_found"])
        self.assertTrue(detected["gpr_field_indices_1_to_31_detected"])
        self.assertTrue(detected["pc_schema_verified"])
        self.assertTrue(detected["gpr_schema_verified"])
        self.assertTrue(detected["testbench_program_preload_found"])
        self.assertTrue(detected["testbench_preload_tasks_found"])
        self.assertTrue(detected["testbench_ecc_bank_preload_found"])
        self.assertTrue(detected["testbench_observable_policy_found"])
        self.assertTrue(detected["staging_memory_schema_verified"])
        self.assertTrue(detected["dccm_schema_verified"])
        self.assertEqual(detected["dccm_bank_fields_detected"], [0, 1, 2, 3])
        self.assertTrue(detected["iccm_schema_verified"])
        self.assertEqual(detected["iccm_bank_fields_detected"], [0, 1, 2, 3])
        self.assertTrue(detected["ecc_schema_verified"])
        self.assertTrue(detected["memory_preload_schema_verified"])
        self.assertTrue(detected["gpu_state_image_initialization_schema_verified"])
        self.assertEqual(
            detected["gpu_state_image_sections"],
            [
                "control_scalars",
                "dccm_banks",
                "iccm_banks",
                "program_staging_imem",
                "program_staging_lmem",
            ],
        )
        self.assertTrue(detected["gpu_state_image_requires_materializer"])
        self.assertFalse(detected["rtlmeter_program_identity_verified"])
        self.assertNotIn("complete_gpr_field_layout_schema", report["missing_build_context"])
        self.assertNotIn("explicit_iccm_dccm_bank_ecc_layout_schema", report["missing_build_context"])
        self.assertNotIn("gpu_state_image_initialization_schema", report["missing_build_context"])
        self.assertIn("gpu_state_image_materializer", report["missing_build_context"])
        self.assertIn("rtlmeter_program_preload_identity_binding", report["missing_build_context"])
        self.assertIn("rtlmeter_stdout_cycles_gpu_compare_binding", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_inspect_veer_el2_state_layout_blocks_incomplete_gpr_schema(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir, omit_gpr_indices={17})
            report = inspect_veer_el2_state_layout(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=VEER_PROGRAM_HEX,
            )
        detected = report["detected_layout"]
        self.assertFalse(detected["gpr_field_indices_1_to_31_detected"])
        self.assertFalse(detected["gpr_schema_verified"])
        self.assertIn("complete_gpr_field_layout_schema", report["missing_build_context"])
        self.assertFalse(report["state_layout_ready"])
        self._assert_fail_closed_non_claims(report)

    def test_inspect_veer_el2_state_layout_verifies_matching_rtlmeter_program_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            report = inspect_veer_el2_state_layout(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=VEER_PROGRAM_HEX,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT)
        self.assertTrue(report["detected_layout"]["rtlmeter_program_identity_verified"])
        self.assertTrue(report["detected_layout"]["reviewed_rtlmeter_program_preload_supported"])
        self.assertEqual(report["reviewed_rtlmeter_program_preload_key"], "hello")
        self.assertEqual(report["reviewed_rtlmeter_case"], "VeeR-EL2:default:hello")
        self.assertEqual(report["rtlmeter_program_sha256"], report["accepted_program_preload_sha256"])
        self.assertNotIn("rtlmeter_program_identity_verified", report["missing_build_context"])
        self.assertNotIn("rtlmeter_program_preload_identity_binding", report["missing_build_context"])
        self.assertNotIn("complete_gpr_field_layout_schema", report["missing_build_context"])
        self.assertNotIn("explicit_iccm_dccm_bank_ecc_layout_schema", report["missing_build_context"])
        self.assertNotIn("gpu_state_image_initialization_schema", report["missing_build_context"])
        self.assertIn("gpu_state_image_materializer", report["missing_build_context"])
        self.assertFalse(report["state_layout_ready"])
        self._assert_fail_closed_non_claims(report)

    def test_inspect_veer_el2_state_layout_blocks_incomplete_dccm_bank_schema(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir, omit_dccm_bank=3)
            report = inspect_veer_el2_state_layout(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=VEER_PROGRAM_HEX,
            )
        detected = report["detected_layout"]
        self.assertFalse(detected["dccm_schema_verified"])
        self.assertEqual(detected["dccm_bank_fields_detected"], [0, 1, 2])
        self.assertTrue(detected["iccm_schema_verified"])
        self.assertFalse(detected["memory_preload_schema_verified"])
        self.assertFalse(detected["gpu_state_image_initialization_schema_verified"])
        self.assertIn("explicit_iccm_dccm_bank_ecc_layout_schema", report["missing_build_context"])
        self.assertIn("gpu_state_image_initialization_schema", report["missing_build_context"])
        self.assertFalse(report["state_layout_ready"])
        self._assert_fail_closed_non_claims(report)

    def test_inspect_veer_el2_state_layout_accepts_verilated_observable_expression_binding(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir, include_mailbox_data=False)
            self._write_minimal_veer_observable_cpp(mdir)
            report = inspect_veer_el2_state_layout(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=VEER_PROGRAM_HEX,
            )
        detected = report["detected_layout"]
        self.assertFalse(detected["observable_root_fields_found"])
        self.assertTrue(detected["observable_expression_binding_found"])
        self.assertTrue(detected["mailbox_address_expression_found"])
        self.assertTrue(detected["observable_fields_found"])
        self.assertTrue(detected["rtlmeter_stdout_cycles_gpu_compare_binding_verified"])
        self.assertNotIn("observable_fields_found", report["missing_build_context"])
        self.assertNotIn("rtlmeter_stdout_cycles_gpu_compare_binding", report["missing_build_context"])
        self.assertIn("veer_el2_sidecar_execution_bridge", report["missing_build_context"])
        self.assertFalse(report["state_layout_ready"])
        self._assert_fail_closed_non_claims(report)

    def test_materialize_veer_el2_state_image_writes_reviewed_extracted_image(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            self._write_minimal_veer_observable_cpp(mdir)
            state_image = tmp_path / "veer_state_image.json"
            report = materialize_veer_el2_state_image(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=VEER_PROGRAM_HEX,
                state_image_out=state_image,
            )
            image = json.loads(state_image.read_text(encoding="utf-8"))
        self.assertTrue(report["state_image_materialized"])
        self.assertEqual(report["state_image_path"], state_image.resolve().relative_to(REPO_ROOT.resolve()).as_posix())
        self.assertNotIn("gpu_state_image_materializer", report["missing_build_context"])
        self.assertNotIn("rtlmeter_stdout_cycles_gpu_compare_binding", report["missing_build_context"])
        self.assertIn("veer_el2_sidecar_execution_bridge", report["missing_build_context"])
        self.assertFalse(report["state_layout_ready"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertEqual(image["schema_role"], "veer_el2_extracted_preload_state_image")
        self.assertEqual(image["target"], "rtlmeter_veer_el2_default_hello")
        self.assertTrue(image["sections"]["program_staging_lmem"])
        self.assertTrue(image["sections"]["program_staging_imem"])
        self.assertFalse(image["sections"]["dccm_banks"]["preload_active"])
        self.assertFalse(image["sections"]["iccm_banks"]["preload_active"])
        self.assertEqual(report["state_image_dccm_nonzero_entry_count"], 0)
        self.assertEqual(report["state_image_iccm_nonzero_entry_count"], 0)
        self._assert_fail_closed_non_claims(report)

    def test_materialize_veer_el2_state_image_writes_reviewed_cmark_preload_image(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            self._write_minimal_veer_observable_cpp(mdir)
            state_image = tmp_path / "veer_cmark_state_image.json"
            report = materialize_veer_el2_state_image(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=VEER_CMARK_PROGRAM_HEX,
                state_image_out=state_image,
            )
            image = json.loads(state_image.read_text(encoding="utf-8"))
        self.assertTrue(report["state_image_materialized"])
        self.assertEqual(report["reviewed_rtlmeter_program_preload_key"], "cmark")
        self.assertEqual(report["reviewed_rtlmeter_case"], "VeeR-EL2:default:cmark")
        self.assertTrue(report["reviewed_rtlmeter_program_preload_supported"])
        self.assertTrue(report["detected_layout"]["rtlmeter_program_identity_verified"])
        self.assertEqual(report["accepted_program_preload"], VEER_CMARK_PROGRAM_HEX)
        self.assertEqual(report["accepted_program_preload_sha256"], report["rtlmeter_program_sha256"])
        self.assertEqual(image["program_preload"], VEER_CMARK_PROGRAM_HEX)
        self.assertEqual(image["program_sha256"], report["rtlmeter_program_sha256"])
        self.assertTrue(image["sections"]["program_staging_lmem"])
        self.assertTrue(image["sections"]["program_staging_imem"])
        self.assertGreater(report["state_image_program_byte_count"], 1000)
        self.assertIn("preload_active", image["sections"]["dccm_banks"])
        self.assertIn("preload_active", image["sections"]["iccm_banks"])
        self.assertIn("veer_el2_sidecar_execution_bridge", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_materialize_veer_el2_state_image_blocks_when_schema_unverified(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir, omit_dccm_bank=3)
            state_image = tmp_path / "veer_state_image.json"
            report = materialize_veer_el2_state_image(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=VEER_PROGRAM_HEX,
                state_image_out=state_image,
            )
        self.assertFalse(report["state_image_materialized"])
        self.assertFalse(state_image.exists())
        self.assertIn("gpu_state_image_initialization_schema", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_inspect_veer_el2_state_layout_rejects_mismatched_program_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            wrong_program = tmp_path / "program.hex"
            wrong_program.write_text("00\n", encoding="utf-8")
            report = inspect_veer_el2_state_layout(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=wrong_program,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT)
        self.assertFalse(report["detected_layout"]["rtlmeter_program_identity_verified"])
        self.assertFalse(report["detected_layout"]["reviewed_rtlmeter_program_preload_supported"])
        self.assertIsNone(report["reviewed_rtlmeter_program_preload_key"])
        self.assertNotEqual(report["rtlmeter_program_sha256"], report["accepted_program_preload_sha256"])
        self.assertIn("rtlmeter_program_identity_verified", report["missing_build_context"])
        self.assertIn("rtlmeter_program_preload_identity_binding", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_materialize_veer_el2_state_image_blocks_mismatched_program_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            self._write_minimal_veer_observable_cpp(mdir)
            wrong_program = tmp_path / "program.hex"
            wrong_program.write_text("00\n", encoding="utf-8")
            state_image = tmp_path / "veer_state_image.json"
            report = materialize_veer_el2_state_image(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                rtlmeter_program_hex=wrong_program,
                state_image_out=state_image,
            )
        self.assertFalse(report["state_image_materialized"])
        self.assertFalse(state_image.exists())
        self.assertEqual(report["status"], make_driver.STATUS_BLOCKED_VEER_EL2_STATE_IMAGE_MATERIALIZER)
        self.assertIn("rtlmeter_program_identity_verified", report["missing_build_context"])
        self.assertIn("rtlmeter_program_preload_identity_binding", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_inspect_veer_el2_state_layout_blocks_missing_root_header(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = inspect_veer_el2_state_layout(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT)
        self.assertFalse(report["state_layout_inspection_performed"])
        self.assertIn("verilated_root_header", report["missing_build_context"])
        self.assertFalse(report["gpu_execution_claimed"])
        self._assert_fail_closed_non_claims(report)

    def test_cli_inspect_veer_el2_state_layout_writes_blocked_summary(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            self._write_minimal_veer_observable_cpp(mdir)
            filelist = self._write_filelist(tmp_path, self._veer_entries())
            summary = tmp_path / "veer_state_layout.json"
            rc = make_driver_main([
                "inspect-veer-el2-state-layout", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", filelist.as_posix(), "--top-module", VEER_TOP,
                "--mdir", mdir.as_posix(), "--summary-out", summary.as_posix(),
                "--rtlmeter-program-hex", VEER_PROGRAM_HEX,
            ])
            written = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(rc, 1)
        self.assertEqual(written["status"], STATUS_BLOCKED_VEER_EL2_STATE_LAYOUT)
        self.assertTrue(written["state_layout_inspection_performed"])
        self.assertTrue(written["detected_layout"]["rtlmeter_program_identity_verified"])
        self.assertFalse(written["state_layout_ready"])
        self._assert_fail_closed_non_claims(written)

    def test_cli_materialize_veer_el2_state_image_writes_blocked_summary_and_image(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)
            self._write_minimal_veer_observable_cpp(mdir)
            filelist = self._write_filelist(tmp_path, self._veer_entries())
            state_image = tmp_path / "veer_state_image.json"
            summary = tmp_path / "veer_state_image_summary.json"
            rc = make_driver_main([
                "materialize-veer-el2-state-image", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", filelist.as_posix(), "--top-module", VEER_TOP,
                "--mdir", mdir.as_posix(), "--summary-out", summary.as_posix(),
                "--state-image-out", state_image.as_posix(),
                "--rtlmeter-program-hex", VEER_PROGRAM_HEX,
            ])
            written = json.loads(summary.read_text(encoding="utf-8"))
            image_exists = state_image.is_file()
        self.assertEqual(rc, 0)
        self.assertTrue(written["state_image_materialized"])
        self.assertTrue(image_exists)
        self.assertNotIn("rtlmeter_stdout_cycles_gpu_compare_binding", written["missing_build_context"])
        self.assertIn("veer_el2_sidecar_execution_bridge", written["missing_build_context"])
        self.assertFalse(written["state_layout_ready"])
        self._assert_fail_closed_non_claims(written)

    def test_veer_el2_sidecar_bridge_blocks_without_reviewed_executable(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            self._write_rtlmeter_observables(
                cpu_execute_dir,
                stdout_text="0.04 | TEST_PASSED\n0.04 | Finished : minstret = 330, mcycle = 726\n",
                cycles=2229,
            )
            report = run_veer_el2_sidecar_execution_bridge(
                repo_root=REPO_ROOT,
                state_image_path=state_image,
                cpu_execute_dir=cpu_execute_dir,
                sidecar_execute_dir=sidecar_execute_dir,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_SIDECAR_EXECUTABLE)
        self.assertFalse(report["sidecar_bridge_invoked"])
        self.assertFalse(report["sidecar_observables_ready"])
        self.assertIn("reviewed_veer_el2_sidecar_executable", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_veer_el2_sidecar_bridge_blocks_prelaunch_rejected_gpu_state_image(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            self._write_veer_gpu_meta_with_prelaunch_rejection(mdir)
            self._write_rtlmeter_observables(cpu_execute_dir, stdout_text="TEST_PASSED\n", cycles=1)
            report = run_veer_el2_sidecar_execution_bridge(
                repo_root=REPO_ROOT,
                state_image_path=state_image,
                cpu_execute_dir=cpu_execute_dir,
                sidecar_execute_dir=sidecar_execute_dir,
                mdir=mdir,
                runner=lambda *args, **kwargs: self.fail("prelaunch-rejected GPU state must not run"),
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_GPU_STATE_IMAGE_LAUNCH)
        self.assertFalse(report["sidecar_bridge_invoked"])
        self.assertIn("veer_el2_gpu_root_state_image_field_offset_map", report["missing_build_context"])
        self.assertIn("veer_el2_gpu_root_state_image_materializer", report["missing_build_context"])
        self.assertIn("reviewed_veer_el2_sidecar_executable", report["missing_build_context"])
        review = report["gpu_state_image_launch_review"]
        self.assertTrue(review["prelaunch_rejection_required"])
        self.assertFalse(review["unsafe_syms_gep_covered_by_state_image"])
        self.assertEqual(review["unsafe_syms_gep_count"], 1085)
        self.assertFalse(review["root_state_image_field_offset_review"]["reviewed"])
        self._assert_fail_closed_non_claims(report)

    def test_veer_el2_gpu_launch_blocker_skips_offset_review_for_safe_metadata(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp) / "obj_dir"
            mdir.mkdir()
            self._write_veer_gpu_meta_with_syms_state_image(mdir)
            original_review = make_driver._veer_el2_root_state_offset_review
            try:
                make_driver._veer_el2_root_state_offset_review = lambda *args, **kwargs: self.fail(
                    "safe metadata must not probe root layout offsets"
                )
                self.assertIsNone(make_driver._veer_el2_gpu_state_image_launch_blocker(mdir, REPO_ROOT))
            finally:
                make_driver._veer_el2_root_state_offset_review = original_review

    def test_veer_el2_root_state_offset_review_maps_required_fields(self) -> None:
        authority = {
            "state_layout": {
                "pc_schema": {"accepted_field_candidates": ["pc_field", "pc_short"]},
                "integer_register_file_schema": {
                    "explicit_register_indices": [1, 2],
                    "field_regex": r"gpr__BRA__(\d+)__KET____DOT__gprff__dout",
                },
                "memory_preload_schema": {
                    "program_staging": {"lmem_field": "lmem_mem", "imem_field": "imem_mem"},
                    "dccm": {
                        "num_banks": 1,
                        "bank_field_prefix": "dccm_bank_",
                        "bank_field_suffix": "_ram",
                    },
                    "iccm": {
                        "num_banks": 1,
                        "bank_field_prefix": "iccm_bank_",
                        "bank_field_suffix": "_ram",
                    },
                },
                "gpu_state_image_initialization_schema": {
                    "required_root_fields": ["core_clk", "rst_l"],
                    "state_image_sections": [
                        {"source_field": "lmem_mem"},
                        {"source_field": "imem_mem"},
                        {"fields": ["core_clk", "rst_l"]},
                    ],
                },
                "rtlmeter_stdout_cycles_gpu_compare_binding": {
                    "rtlmeter_cycles": {"counter_fields": ["mcyclel", "minstretl"]},
                },
            }
        }
        names = [
            "core_clk",
            "rst_l",
            "pc_field",
            "tb__DOT__pc_short",
            "dec__DOT__arf__DOT____Vcellout__gpr__BRA__1__KET____DOT__gprff__dout",
            "dec__DOT__arf__DOT____Vcellout__gpr__BRA__2__KET____DOT__gprff__dout",
            "lmem_mem",
            "imem_mem",
            "dccm_bank_0_ram",
            "iccm_bank_0_ram",
            "tlu__DOT__mcyclel",
            "tlu__DOT__minstretl",
            "mailbox_write",
            "bus_buffer__DOT__obuf_data",
            "tb_top__DOT__reset_vector",
            "tb_top__DOT__nmi_vector",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_branch_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_decode_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____VdfgRegularize_hdab710bf_0_43",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_ib0_valid_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__misc2ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_exublock_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__misc1ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT____Vcellout__halt_ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__presync_stall",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__lsu_idle",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT____Vcellinp__genblock5__DOT__i_new_4bit_div_fullshortq__valid_in",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__running_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT____Vcellout__i_misc_ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__i_misc_ff__DOT__genblock__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__shortq",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__shortq_enable",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__quotient_raw",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__quotient_new",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__dw_shortq_raw",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT____Vcellout__i_b_ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__i_b_ff__DOT__genblock__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__a_ff",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__q_ff",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__r_ff",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_pc_r_ff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_i0_instr_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_brp_valid",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_predict_nt",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_predict_br",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_tlu_i0_valid_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__i0_valid_no_ebreak_ecall_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dma_dccm_stall_any",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__lsu_store_stall_any",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_lsu_valid_raw_d",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmu_fetch_stall",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmu_instr_aligned",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____Vcellout__fbwrite_ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____VdfgRegularize_h02fb64cc_0_10",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_err_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dma_iccm_stall_any",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__perr_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__err_stop_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu_flush_final",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_lower_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_path_r",
            "tb_top__DOT__ifu_axi_rvalid",
            "tb_top__DOT__ifu_axi_rid",
            "tb_top__DOT__ifu_axi_rresp",
            "tb_top__DOT__ifu_axi_rdata",
            "tb_top__DOT__mux_axi_rvalid",
            "tb_top__DOT__sb_axi_rdata",
            "tb_top__DOT__lmem_axi_rvalid",
            "tb_top__DOT__lmem_axi_rdata",
            "tb_top__DOT__ifu_axi_arready",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__ifu_bus_cmd_valid",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__bus_rd_addr_count",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT____Vcellout__ifu_fetch_addr_f_ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmp_addr",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__ifc_fetch_req_bf",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__fb_write_ns",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__miss_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT____Vcellout__miss_f_ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__miss_state",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__miss_state_en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__write_ic_16_bytes",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__ic_act_miss_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____VdfgRegularize_h02fb64cc_0_8",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__ic_hit_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__aligndata",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__alignfromf1",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata0ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata1ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata2ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f1_f0",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f2_f0",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f2_f1",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__sf0val",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__sf1val",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellout__bundle1ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellout__bundle2ff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_noredir_r",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ic_fetch_val_f",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_iccm_rd_ecc_single_err",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_ic_error_start",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_i0_commit_cmt",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT____Vcellout__freeff__dout",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__freeff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f0",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f1",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f2",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellinp__bundle1ff__din",
            "tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__bundle2ff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din",
            "__VactTriggered",
            "__VnbaTriggered",
        ]
        layout = [
            {"name": name, "offset": index * 4, "size": 4, "decl_type": "IData/*31:0*/"}
            for index, name in enumerate(names)
        ]
        review = _veer_el2_root_state_offset_review_from_layout(layout=layout, authority=authority)
        self.assertTrue(review["reviewed"])
        self.assertEqual(review["missing_field_markers"], [])
        self.assertIn("gpr:1", review["mapped_fields"])
        self.assertIn("cycle:mcyclel", review["mapped_fields"])
        self.assertIn("tb_top__DOT__reset_vector", review["mapped_fields"])
        self.assertIn("tb_top__DOT__nmi_vector", review["mapped_fields"])

    def test_veer_el2_root_image_materializer_review_blocks_assoc_program_staging_gpu_lowering(self) -> None:
        state_image = {
            "sections": {
                "control_scalars": {
                    "tb_top__DOT__core_clk": 0,
                    "tb_top__DOT__rst_l": 0,
                    "tb_top__DOT__porst_l": 0,
                },
                "dccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {"0": []}},
                "iccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {"0": []}},
                "program_staging_lmem": [{"addr": "0x80000000", "byte_hex": "0x73"}],
                "program_staging_imem": [{"addr": "0x80000000", "byte_hex": "0x73"}],
            }
        }
        offset_review = {
            "reviewed": True,
            "mapped_fields": {
                "tb_top__DOT__core_clk": {
                    "name": "tb_top__DOT__core_clk",
                    "offset": 0,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__rst_l": {
                    "name": "tb_top__DOT__rst_l",
                    "offset": 1,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__porst_l": {
                    "name": "tb_top__DOT__porst_l",
                    "offset": 2,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__lmem__DOT__mem": {
                    "name": "tb_top__DOT__lmem__DOT__mem",
                    "offset": 16,
                    "size": 56,
                    "decl_type": "VlAssocArray<IData/*31:0*/, CData/*7:0*/>",
                },
                "tb_top__DOT__imem__DOT__mem": {
                    "name": "tb_top__DOT__imem__DOT__mem",
                    "offset": 72,
                    "size": 56,
                    "decl_type": "VlAssocArray<IData/*31:0*/, CData/*7:0*/>",
                },
                "dccm0": {
                    "name": "tb_top__DOT__dccm_bank__DOT__ram_core",
                    "offset": 128,
                    "size": 32768,
                    "decl_type": "VlUnpacked<QData/*38:0*/, 4096>",
                },
                "iccm0": {
                    "name": "tb_top__DOT__iccm_bank__DOT__ram_core",
                    "offset": 32896,
                    "size": 32768,
                    "decl_type": "VlUnpacked<QData/*38:0*/, 4096>",
                },
            },
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text("%class.VlAssocArray = type { %\"class.std::map\" }\n", encoding="utf-8")
            review = _veer_el2_root_image_materializer_review(
                state_image=state_image,
                offset_review=offset_review,
                repo_root=REPO_ROOT,
                mdir=mdir,
            )

        self.assertFalse(review["reviewed"])
        self.assertFalse(review["root_image_materialized"])
        self.assertTrue(review["gpu_ir_assoc_array_map_detected"])
        self.assertIn("control_scalars", review["materializable_sections"])
        self.assertIn("dccm_banks", review["materializable_sections"])
        self.assertIn("iccm_banks", review["materializable_sections"])
        self.assertIn("program_staging_lmem", review["blocked_sections"])
        self.assertIn("program_staging_imem", review["blocked_sections"])
        self.assertIn("veer_el2_program_staging_assoc_array_gpu_lowering", review["missing_build_context"])
        lmem = review["section_details"]["program_staging_lmem"]
        self.assertTrue(lmem["entry_schema_valid"])
        self.assertTrue(lmem["host_assoc_array_initializer_ready"])
        self.assertTrue(lmem["blocked_by_gpu_assoc_array_lowering"])
        self.assertEqual(lmem["address_min_hex"], "0x80000000")

    def test_veer_el2_root_image_materializer_accepts_lowered_flat_program_staging(self) -> None:
        state_image = {
            "sections": {
                "control_scalars": {
                    "tb_top__DOT__core_clk": 0,
                    "tb_top__DOT__rst_l": 0,
                    "tb_top__DOT__porst_l": 0,
                },
                "dccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {"0": []}},
                "iccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {"0": []}},
                "program_staging_lmem": [
                    {"addr": "0x80000000", "byte_hex": "0x73"},
                    {"addr": "0x80000001", "byte_hex": "0x10"},
                ],
                "program_staging_imem": [
                    {"addr": "0x80000000", "byte_hex": "0x73"},
                    {"addr": "0x80000001", "byte_hex": "0x10"},
                ],
            }
        }
        offset_review = {
            "reviewed": True,
            "mapped_fields": {
                "tb_top__DOT__core_clk": {
                    "name": "tb_top__DOT__core_clk",
                    "offset": 0,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__rst_l": {
                    "name": "tb_top__DOT__rst_l",
                    "offset": 1,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__porst_l": {
                    "name": "tb_top__DOT__porst_l",
                    "offset": 2,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__lmem__DOT__mem": {
                    "name": "tb_top__DOT__lmem__DOT__mem",
                    "offset": 16,
                    "size": 56,
                    "decl_type": "VlAssocArray<IData/*31:0*/, CData/*7:0*/>",
                },
                "tb_top__DOT__imem__DOT__mem": {
                    "name": "tb_top__DOT__imem__DOT__mem",
                    "offset": 72,
                    "size": 56,
                    "decl_type": "VlAssocArray<IData/*31:0*/, CData/*7:0*/>",
                },
                "dccm0": {
                    "name": "tb_top__DOT__dccm_bank__DOT__ram_core",
                    "offset": 128,
                    "size": 32768,
                    "decl_type": "VlUnpacked<QData/*38:0*/, 4096>",
                },
                "iccm0": {
                    "name": "tb_top__DOT__iccm_bank__DOT__ram_core",
                    "offset": 32896,
                    "size": 32768,
                    "decl_type": "VlUnpacked<QData/*38:0*/, 4096>",
                },
            },
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "define void @vl_eval_batch_gpu() { ret void }\n",
                encoding="utf-8",
            )
            review = _veer_el2_root_image_materializer_review(
                state_image=state_image,
                offset_review=offset_review,
                repo_root=REPO_ROOT,
                mdir=mdir,
            )

        self.assertTrue(review["reviewed"])
        self.assertFalse(review["gpu_ir_assoc_array_map_detected"])
        self.assertEqual(review["blocked_sections"], [])
        self.assertNotIn("veer_el2_program_staging_assoc_array_gpu_lowering", review["missing_build_context"])
        lmem = review["section_details"]["program_staging_lmem"]
        self.assertTrue(lmem["host_assoc_array_initializer_ready"])
        self.assertTrue(lmem["materializable_as_gpu_flat_bytes"])
        self.assertEqual(lmem["gpu_flat_byte_window_review"]["representation"], "flat_byte_window")
        self.assertEqual(lmem["gpu_flat_byte_window_review"]["base_addr_hex"], "0x80000000")
        self.assertEqual(lmem["gpu_flat_byte_window_review"]["byte_count"], 2)

    def test_veer_el2_root_image_materializer_accepts_flat_program_mem_wrapper(self) -> None:
        state_image = {
            "sections": {
                "control_scalars": {
                    "tb_top__DOT__core_clk": 0,
                    "tb_top__DOT__rst_l": 0,
                    "tb_top__DOT__porst_l": 0,
                },
                "dccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {"0": []}},
                "iccm_banks": {"preload_active": False, "nonzero_entries_by_bank": {"0": []}},
                "program_staging_lmem": [
                    {"addr": "0x80000000", "byte_hex": "0x73"},
                    {"addr": "0x80000001", "byte_hex": "0x10"},
                ],
                "program_staging_imem": [
                    {"addr": "0x80000000", "byte_hex": "0x73"},
                    {"addr": "0x80000001", "byte_hex": "0x10"},
                ],
            }
        }
        offset_review = {
            "reviewed": True,
            "mapped_fields": {
                "tb_top__DOT__core_clk": {
                    "name": "tb_top__DOT__core_clk",
                    "offset": 0,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__rst_l": {
                    "name": "tb_top__DOT__rst_l",
                    "offset": 1,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__porst_l": {
                    "name": "tb_top__DOT__porst_l",
                    "offset": 2,
                    "size": 1,
                    "decl_type": "CData/*0:0*/",
                },
                "tb_top__DOT__lmem__DOT__mem": {
                    "name": "tb_top__DOT__lmem__DOT__mem",
                    "offset": 16,
                    "size": 65536,
                    "decl_type": "VlGpuFlatByteMem<0x80000000U, 65536U>",
                },
                "tb_top__DOT__imem__DOT__mem": {
                    "name": "tb_top__DOT__imem__DOT__mem",
                    "offset": 65552,
                    "size": 65536,
                    "decl_type": "VlGpuFlatByteMem<0x80000000U, 65536U>",
                },
                "dccm0": {
                    "name": "tb_top__DOT__dccm_bank__DOT__ram_core",
                    "offset": 131088,
                    "size": 32768,
                    "decl_type": "VlUnpacked<QData/*38:0*/, 4096>",
                },
                "iccm0": {
                    "name": "tb_top__DOT__iccm_bank__DOT__ram_core",
                    "offset": 163856,
                    "size": 32768,
                    "decl_type": "VlUnpacked<QData/*38:0*/, 4096>",
                },
            },
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join([
                    "%\"class.std::multimap\" = type { %\"class.std::_Rb_tree\" }",
                    "define void @vl_eval_batch_gpu() { ret void }",
                    "",
                ]),
                encoding="utf-8",
            )
            review = _veer_el2_root_image_materializer_review(
                state_image=state_image,
                offset_review=offset_review,
                repo_root=REPO_ROOT,
                mdir=mdir,
            )

        self.assertTrue(review["reviewed"])
        self.assertFalse(review["gpu_ir_assoc_array_map_detected"])
        self.assertEqual(review["blocked_sections"], [])
        self.assertNotIn("veer_el2_program_staging_assoc_array_gpu_lowering", review["missing_build_context"])
        lmem = review["section_details"]["program_staging_lmem"]
        self.assertFalse(lmem["host_assoc_array_initializer_ready"])
        self.assertTrue(lmem["root_flat_program_mem_ready"])
        self.assertTrue(lmem["materializable_as_gpu_flat_bytes"])
        self.assertFalse(lmem["blocked_by_assoc_array_container"])

    def test_gpu_hierarchy_metadata_detects_nonflat_assoc_array_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join([
                    "%class.VlAssocArray = type <{ %\"class.std::map\", i8, [7 x i8] }>",
                    "%\"class.std::map\" = type { %\"class.std::_Rb_tree\" }",
                    "define void @vl_eval_batch_gpu() { ret void }",
                    "",
                ]),
                encoding="utf-8",
            )
            metadata = detect_hierarchy_state_metadata(mdir, storage_size=300352)

        self.assertTrue(metadata["nonflat_assoc_array_detected"])
        self.assertFalse(metadata["assoc_array_gpu_lowering_supported"])
        self.assertIn("VlAssocArray", metadata["nonflat_assoc_array_markers"])
        self.assertIn("vl_batch_gpu_opt.ll", metadata["nonflat_assoc_array_sources"])

    def test_gpu_hierarchy_metadata_keeps_residual_tree_out_of_assoc_blocker(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join([
                    "%\"class.std::multimap\" = type { %\"class.std::_Rb_tree\" }",
                    "define void @vl_eval_batch_gpu() { ret void }",
                    "",
                ]),
                encoding="utf-8",
            )
            metadata = detect_hierarchy_state_metadata(mdir, storage_size=431296)

        self.assertFalse(metadata["nonflat_assoc_array_detected"])
        self.assertTrue(metadata["assoc_array_gpu_lowering_supported"])
        self.assertTrue(metadata["residual_std_tree_detected"])
        self.assertIn("std::_Rb_tree", metadata["residual_std_tree_markers"])
        self.assertIn("vl_batch_gpu_opt.ll", metadata["residual_std_tree_sources"])

    def test_gpu_hierarchy_metadata_probes_syms_top_offset_when_tbaa_is_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "Vsim_classes.mk").write_text("VM_CLASSES_FAST += Vsim___024root\n", encoding="utf-8")
            (mdir / "Vsim___024root.h").write_text(
                "class alignas(64) Vsim___024root final { public: char bytes[32]; };\n",
                encoding="utf-8",
            )
            (mdir / "Vsim__Syms.h").write_text(
                "#include \"Vsim___024root.h\"\n"
                "class VerilatedSyms { public: char base[8]; };\n"
                "class alignas(64) Vsim__Syms final : public VerilatedSyms {\n"
                " public:\n"
                "  void* __Vm_modelp;\n"
                "  char pad[48];\n"
                "  Vsim___024root TOP;\n"
                "};\n",
                encoding="utf-8",
            )
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join(
                    [
                        "%class.Vsim__Syms = type { i8 }",
                        "%class.Vsim___024root = type { [64 x i8] }",
                        "%p = getelementptr inbounds %class.Vsim__Syms, ptr null, i32 0, i32 0",
                        "define void @vl_eval_batch_gpu() { ret void }",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            metadata = detect_hierarchy_state_metadata(mdir, storage_size=64)

        self.assertEqual(metadata["root_offset_in_syms"], 64)
        self.assertEqual(metadata["syms_root_layout_probe"]["sizeof_root"], 64)
        self.assertEqual(metadata["syms_root_layout_probe"]["offsetof_TOP"], 64)
        self.assertGreater(metadata["syms_storage_size"], metadata["root_storage_size"])
        self.assertTrue(metadata["prelaunch_rejection_required"])

    def test_veer_el2_flat_program_mem_patch_replaces_scoped_assoc_arrays(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            header = mdir / "Vsim___024root.h"
            header.write_text(
                "\n".join([
                    '#include "verilated.h"',
                    "class Vsim__Syms;",
                    "class Vsim___024root final {",
                    "  public:",
                    "    VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__imem__DOT__mem;",
                    "    VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__lmem__DOT__mem;",
                    "};",
                    "",
                ]),
                encoding="utf-8",
            )

            report = patch_veer_el2_flat_program_mem(mdir, "Vsim")
            patched = header.read_text(encoding="utf-8")
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "define void @vl_eval_batch_gpu() { ret void }\n",
                encoding="utf-8",
            )
            metadata = detect_hierarchy_state_metadata(mdir, storage_size=65536)

        self.assertTrue(report["applied"])
        self.assertTrue(report["changed"])
        self.assertIn("VL_GPU_VEER_EL2_FLAT_PROGRAM_MEM_PATCH", patched)
        self.assertIn("void VL_READMEM_N", patched)
        self.assertIn("VlGpuFlatByteMem<0x80000000U, 65536U> tb_top__DOT__imem__DOT__mem", patched)
        self.assertIn("VlGpuFlatByteMem<0x80000000U, 65536U> tb_top__DOT__lmem__DOT__mem", patched)
        self.assertTrue(metadata["veer_el2_flat_program_mem_patch_applied"])
        self.assertEqual(metadata["veer_el2_flat_program_mem_span_bytes"], 65536)

    def test_veer_el2_sidecar_bridge_compares_runner_emitted_observables(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            executable = tmp_path / "veer_sidecar"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            self._write_veer_sidecar_executable_review(executable)
            stdout_text = "0.04 | TEST_PASSED\n0.04 | Finished : minstret = 330, mcycle = 726\n"
            self._write_rtlmeter_observables(cpu_execute_dir, stdout_text=stdout_text, cycles=2229)

            def fake_runner(command, cwd, env, text, capture_output):
                self.assertEqual(command, [executable.as_posix()])
                self.assertTrue(Path(env["VEER_EL2_SIDECAR_STATE_IMAGE"]).is_file())
                self.assertIn("PATH", env)
                self._write_rtlmeter_observables(
                    Path(env["VEER_EL2_SIDECAR_EXECUTE_DIR"]),
                    stdout_text=stdout_text,
                    cycles=2229,
                )
                return subprocess.CompletedProcess(command, 0, stdout="sidecar ok", stderr="")

            report = run_veer_el2_sidecar_execution_bridge(
                repo_root=REPO_ROOT,
                state_image_path=state_image,
                cpu_execute_dir=cpu_execute_dir,
                sidecar_execute_dir=sidecar_execute_dir,
                sidecar_executable=executable,
                runner=fake_runner,
            )
        self.assertEqual(report["status"], STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED)
        self.assertTrue(report["sidecar_executable_review"]["reviewed"])
        self.assertTrue(report["sidecar_bridge_invoked"])
        self.assertEqual(report["sidecar_executable_invocation_mode"], "subprocess_executable")
        self.assertTrue(report["sidecar_observables_ready"])
        self.assertTrue(report["sidecar_execution_claimed"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["timing_measured"])
        self.assertFalse(report["speedup_claimed"])
        self.assertEqual(report["missing_build_context"], [])
        self.assertEqual(report["comparison"]["status"], "passed")
        self._assert_fail_closed_non_claims(report)

    def test_veer_el2_sidecar_bridge_runs_reviewed_python_sidecar_in_process(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            executable = REPO_ROOT / "src/tools/veer_el2_sidecar_executable.py"
            stdout_text = "0.04 | TEST_PASSED\n0.04 | Finished : minstret = 330, mcycle = 726\n"
            self._write_rtlmeter_observables(cpu_execute_dir, stdout_text=stdout_text, cycles=2229)

            def fake_run_sidecar(root):
                self.assertEqual(root, REPO_ROOT)
                self.assertTrue(Path(veer_sidecar_executable.os.environ["VEER_EL2_SIDECAR_STATE_IMAGE"]).is_file())
                self.assertEqual(veer_sidecar_executable.os.environ["VEER_EL2_SIDECAR_NSTATES"], "4")
                self._write_rtlmeter_observables(
                    Path(veer_sidecar_executable.os.environ["VEER_EL2_SIDECAR_EXECUTE_DIR"]),
                    stdout_text=stdout_text,
                    cycles=2229,
                )
                print("in-process sidecar ok")
                return 0

            original_env = dict(os.environ)
            with mock.patch.object(veer_sidecar_executable, "run_sidecar", side_effect=fake_run_sidecar):
                report = run_veer_el2_sidecar_execution_bridge(
                    repo_root=REPO_ROOT,
                    state_image_path=state_image,
                    cpu_execute_dir=cpu_execute_dir,
                    sidecar_execute_dir=sidecar_execute_dir,
                    sidecar_executable=executable,
                    sidecar_env={"VEER_EL2_SIDECAR_NSTATES": "4"},
                    runner=lambda *args, **kwargs: self.fail("reviewed Python sidecar should run in process"),
                )
            self.assertEqual(os.environ, original_env)
        self.assertEqual(report["status"], STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED)
        self.assertEqual(report["sidecar_executable_invocation_mode"], "in_process_veer_el2_sidecar")
        self.assertTrue(report["sidecar_bridge_invoked"])
        self.assertTrue(report["sidecar_observables_ready"])
        self.assertEqual(report["sidecar_bridge_returncode"], 0)
        self.assertEqual(report["comparison"]["status"], "passed")
        self._assert_fail_closed_non_claims(report)

    def test_veer_el2_sidecar_bridge_in_process_nonzero_maps_to_run_failed(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            executable = REPO_ROOT / "src/tools/veer_el2_sidecar_executable.py"
            self._write_rtlmeter_observables(cpu_execute_dir, stdout_text="TEST_PASSED\n", cycles=2229)

            with mock.patch.object(veer_sidecar_executable, "run_sidecar", return_value=7):
                report = run_veer_el2_sidecar_execution_bridge(
                    repo_root=REPO_ROOT,
                    state_image_path=state_image,
                    cpu_execute_dir=cpu_execute_dir,
                    sidecar_execute_dir=sidecar_execute_dir,
                    sidecar_executable=executable,
                    runner=lambda *args, **kwargs: self.fail("reviewed Python sidecar should run in process"),
                )
        self.assertEqual(report["status"], make_driver.STATUS_BLOCKED_VEER_EL2_SIDECAR_RUN_FAILED)
        self.assertEqual(report["sidecar_executable_invocation_mode"], "in_process_veer_el2_sidecar")
        self.assertEqual(report["sidecar_bridge_returncode"], 7)
        self.assertEqual(report["missing_build_context"], ["veer_el2_sidecar_execution_bridge_passed"])
        self._assert_fail_closed_non_claims(report)

    def test_veer_el2_sidecar_syms_init_materializer_writes_flat_program_bytes(self) -> None:
        state_image = {
            "target": "rtlmeter_veer_el2_default_hello",
            "sections": {
                "control_scalars": {
                    "tb_top__DOT__core_clk": 1,
                    "tb_top__DOT__rst_l": 1,
                },
                "program_staging_imem": [
                    {"addr": "0x80000000", "byte_hex": "0xaa"},
                    {"addr": "0x80000002", "byte_hex": "0xcc"},
                ],
                "program_staging_lmem": [
                    {"addr": "0x80000001", "byte_hex": "0xbb"},
                ],
                "dccm_banks": {
                    "preload_active": True,
                    "nonzero_entries_by_bank": {
                        "0": [
                            {"index": 0, "word_hex": "0x0000000001"},
                            {"index": 1, "word_hex": "0x6e800003be"},
                        ]
                    },
                },
                "iccm_banks": {
                    "preload_active": True,
                    "nonzero_entries_by_bank": {
                        "1": [
                            {"index": 0, "word_hex": "0x501503c619"},
                        ]
                    },
                },
            },
        }
        meta = {
            "storage_size": 192,
            "hierarchy_state": {
                "state_image_kind": "verilator_syms_image",
                "root_offset_in_state": 16,
            },
        }
        mapped_fields = {
            "tb_top__DOT__core_clk": {"offset": 4, "size": 1},
            "tb_top__DOT__rst_l": {"offset": 5, "size": 1},
            "tb_top__DOT__reset_vector": {"offset": 8, "size": 4},
            "tb_top__DOT__nmi_vector": {"offset": 12, "size": 4},
            "tb_top__DOT__imem__DOT__mem": {"offset": 32, "size": 16},
            "tb_top__DOT__lmem__DOT__mem": {"offset": 64, "size": 16},
            "tb_top__DOT__Gen_dccm_enable__DOT__dccm_loop__BRA__0__KET____DOT__dccm__DOT__dccm_bank__DOT__ram_core": {
                "name": "tb_top__DOT__Gen_dccm_enable__DOT__dccm_loop__BRA__0__KET____DOT__dccm__DOT__dccm_bank__DOT__ram_core",
                "offset": 80,
                "size": 16,
            },
            "tb_top__DOT__Gen_iccm_enable__DOT__iccm_loop__BRA__1__KET____DOT__iccm__DOT__iccm_bank__DOT__ram_core": {
                "name": "tb_top__DOT__Gen_iccm_enable__DOT__iccm_loop__BRA__1__KET____DOT__iccm__DOT__iccm_bank__DOT__ram_core",
                "offset": 96,
                "size": 8,
            },
        }

        blob, materialized = materialize_veer_el2_syms_init_state(
            state_image=state_image,
            meta=meta,
            mapped_fields=mapped_fields,
        )

        self.assertEqual(len(blob), 192)
        self.assertEqual(blob[16 + 4], 1)
        self.assertEqual(blob[16 + 5], 1)
        self.assertEqual(int.from_bytes(blob[16 + 8 : 16 + 12], "little"), 0x80000000)
        self.assertEqual(int.from_bytes(blob[16 + 12 : 16 + 16], "little"), 0xEE000000)
        self.assertEqual(blob[16 + 32 + 1 + 0], 0xAA)
        self.assertEqual(blob[16 + 32 + 1 + 2], 0xCC)
        self.assertEqual(blob[16 + 64 + 1 + 1], 0xBB)
        self.assertEqual(int.from_bytes(blob[16 + 80 : 16 + 88], "little"), 0x0000000001)
        self.assertEqual(int.from_bytes(blob[16 + 88 : 16 + 96], "little"), 0x6E800003BE)
        self.assertEqual(int.from_bytes(blob[16 + 96 : 16 + 104], "little"), 0x501503C619)
        self.assertEqual(materialized["program_staging_imem_bytes"], 2)
        self.assertEqual(materialized["program_staging_lmem_bytes"], 1)
        self.assertEqual(materialized["dccm_bank_words"], 2)
        self.assertEqual(materialized["iccm_bank_words"], 1)
        self.assertEqual(materialized["dccm_bank_skipped_missing_bank"], 0)
        self.assertEqual(materialized["iccm_bank_skipped_missing_bank"], 0)
        self.assertEqual(materialized["dccm_bank_skipped_out_of_range"], 0)
        self.assertEqual(materialized["iccm_bank_skipped_out_of_range"], 0)
        self.assertEqual(
            materialized["testbench_vectors_written"],
            ["tb_top__DOT__reset_vector", "tb_top__DOT__nmi_vector"],
        )

    def test_veer_el2_sidecar_syms_init_materializer_maps_flat_program_control_window(self) -> None:
        state_image = {
            "target": "rtlmeter_veer_el2_default_hello",
            "sections": {
                "program_staging_imem": [
                    {"addr": "0x10000000", "byte_hex": "0x11"},
                    {"addr": "0x80000000", "byte_hex": "0xaa"},
                    {"addr": "0x80010000", "byte_hex": "0xbb"},
                ],
                "program_staging_lmem": [
                    {"addr": "0x10000000", "byte_hex": "0x22"},
                    {"addr": "0x80000001", "byte_hex": "0xcc"},
                    {"addr": "0x80010000", "byte_hex": "0xdd"},
                ],
            },
        }
        meta = {
            "storage_size": 140000,
            "hierarchy_state": {
                "state_image_kind": "verilator_syms_image",
                "root_offset_in_state": 16,
            },
        }
        mapped_fields = {
            "tb_top__DOT__imem__DOT__mem": {"offset": 32, "size": 65553},
            "tb_top__DOT__lmem__DOT__mem": {"offset": 66000, "size": 65553},
        }

        blob, materialized = materialize_veer_el2_syms_init_state(
            state_image=state_image,
            meta=meta,
            mapped_fields=mapped_fields,
        )

        self.assertEqual(blob[16 + 32 + 1 + 0], 0xAA)
        self.assertEqual(blob[16 + 32 + 1 + 65536], 0x11)
        self.assertEqual(blob[16 + 66000 + 1 + 1], 0xCC)
        self.assertEqual(blob[16 + 66000 + 1 + 65536], 0x22)
        self.assertEqual(materialized["program_staging_imem_bytes"], 2)
        self.assertEqual(materialized["program_staging_lmem_bytes"], 2)
        self.assertEqual(materialized["program_staging_imem_skipped_before_base"], 0)
        self.assertEqual(materialized["program_staging_lmem_skipped_before_base"], 0)
        self.assertEqual(materialized["program_staging_imem_skipped_after_window"], 1)
        self.assertEqual(materialized["program_staging_lmem_skipped_after_window"], 1)

    def test_veer_el2_sidecar_syms_init_materializer_concatenates_mixed_state_images(self) -> None:
        def image(program: str, byte_value: int, dccm_word: int, iccm_word: int) -> dict[str, object]:
            return {
                "target": "rtlmeter_veer_el2_default_hello",
                "program_preload": f"third_party/rtlmeter/designs/VeeR-EL2/tests/{program}/program.hex",
                "program_sha256": f"sha256-{program}",
                "sections": {
                    "program_staging_imem": [{"addr": "0x80000000", "byte_hex": f"0x{byte_value:02x}"}],
                    "program_staging_lmem": [{"addr": "0x80000001", "byte_hex": f"0x{byte_value + 1:02x}"}],
                    "dccm_banks": {
                        "preload_active": True,
                        "nonzero_entries_by_bank": {
                            "0": [{"index": 0, "word_hex": f"0x{dccm_word:016x}"}],
                        },
                    },
                    "iccm_banks": {
                        "preload_active": True,
                        "nonzero_entries_by_bank": {
                            "1": [{"index": 0, "word_hex": f"0x{iccm_word:016x}"}],
                        },
                    },
                },
            }

        meta = {
            "storage_size": 192,
            "hierarchy_state": {
                "state_image_kind": "verilator_syms_image",
                "root_offset_in_state": 16,
            },
        }
        mapped_fields = {
            "tb_top__DOT__reset_vector": {"offset": 8, "size": 4},
            "tb_top__DOT__nmi_vector": {"offset": 12, "size": 4},
            "tb_top__DOT__imem__DOT__mem": {"offset": 32, "size": 16},
            "tb_top__DOT__lmem__DOT__mem": {"offset": 64, "size": 16},
            "tb_top__DOT__Gen_dccm_enable__DOT__dccm_loop__BRA__0__KET____DOT__dccm__DOT__dccm_bank__DOT__ram_core": {
                "name": "tb_top__DOT__Gen_dccm_enable__DOT__dccm_loop__BRA__0__KET____DOT__dccm__DOT__dccm_bank__DOT__ram_core",
                "offset": 80,
                "size": 8,
            },
            "tb_top__DOT__Gen_iccm_enable__DOT__iccm_loop__BRA__1__KET____DOT__iccm__DOT__iccm_bank__DOT__ram_core": {
                "name": "tb_top__DOT__Gen_iccm_enable__DOT__iccm_loop__BRA__1__KET____DOT__iccm__DOT__iccm_bank__DOT__ram_core",
                "offset": 96,
                "size": 8,
            },
        }
        state_images = [
            image("dhry", 0xA0, 0x11, 0x21),
            image("cmark", 0xB0, 0x12, 0x22),
            image("cmark_iccm", 0xC0, 0x13, 0x23),
        ]

        blob, materialized = materialize_veer_el2_syms_init_states(
            state_images=state_images,
            meta=meta,
            mapped_fields=mapped_fields,
        )

        self.assertEqual(len(blob), 192 * 3)
        self.assertTrue(materialized["mixed_state_preload"])
        self.assertEqual(materialized["state_count"], 3)
        self.assertEqual(materialized["program_sha256s"], ["sha256-dhry", "sha256-cmark", "sha256-cmark_iccm"])
        self.assertEqual(len(materialized["init_state_sha256s"]), 3)
        for state_index, byte_value, dccm_word, iccm_word in (
            (0, 0xA0, 0x11, 0x21),
            (1, 0xB0, 0x12, 0x22),
            (2, 0xC0, 0x13, 0x23),
        ):
            base = 192 * state_index
            self.assertEqual(blob[base + 16 + 32 + 1], byte_value)
            self.assertEqual(blob[base + 16 + 64 + 1 + 1], byte_value + 1)
            self.assertEqual(int.from_bytes(blob[base + 16 + 80 : base + 16 + 88], "little"), dccm_word)
            self.assertEqual(int.from_bytes(blob[base + 16 + 96 : base + 16 + 104], "little"), iccm_word)
            self.assertEqual(int.from_bytes(blob[base + 16 + 8 : base + 16 + 12], "little"), 0x80000000)

    def test_veer_el2_sidecar_clock_reset_patch_script_drives_reset_then_clock(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            script_path = Path(tmp) / "clock_reset.txt"
            summary = write_veer_el2_clock_reset_patch_script(
                path=script_path,
                root_offset=16,
                mapped_fields={
                    "tb_top__DOT__core_clk": {"offset": 4, "size": 1},
                    "tb_top__DOT__rst_l": {"offset": 5, "size": 1},
                    "tb_top__DOT__porst_l": {"offset": 6, "size": 1},
                },
                clock_cycles=3,
                reset_launches=2,
            )

            lines = script_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(summary["logical_steps"], 9)
        self.assertEqual(summary["patch_script_mode"], "full_clock_reset_fields")
        self.assertEqual(lines[0], "20:0x00 21:0x00 22:0x00")
        self.assertEqual(lines[1], "20:0x01 21:0x00 22:0x00")
        self.assertEqual(lines[2], "20:0x00 21:0x01 22:0x01")
        self.assertEqual(lines[3], "@repeat-seq 3")
        self.assertEqual(lines[4], "20:0x00 21:0x01 22:0x01")
        self.assertEqual(lines[5], "20:0x01 21:0x01 22:0x01")
        self.assertEqual(lines[6], "@end-repeat-seq")

    def test_veer_el2_sidecar_clock_reset_patch_script_can_emit_experimental_posedge_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            script_path = Path(tmp) / "clock_reset.txt"
            summary = write_veer_el2_clock_reset_patch_script(
                path=script_path,
                root_offset=16,
                mapped_fields={
                    "tb_top__DOT__core_clk": {"offset": 4, "size": 1},
                    "tb_top__DOT__rst_l": {"offset": 5, "size": 1},
                    "tb_top__DOT__porst_l": {"offset": 6, "size": 1},
                },
                clock_cycles=3,
                reset_launches=2,
                clock_patch_mode="posedge_only",
            )

            lines = script_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(summary["logical_steps"], 6)
        self.assertEqual(summary["patch_script_mode"], "experimental_posedge_only_clock_high_fields")
        self.assertEqual(lines[0], "20:0x00 21:0x00 22:0x00")
        self.assertEqual(lines[1], "20:0x01 21:0x00 22:0x00")
        self.assertEqual(lines[2], "20:0x00 21:0x01 22:0x01")
        self.assertEqual(lines[3], "@repeat-seq 3")
        self.assertEqual(lines[4], "20:0x01 21:0x01 22:0x01")
        self.assertEqual(lines[5], "@end-repeat-seq")
        self.assertEqual(
            veer_sidecar_executable._clock_patch_step_trace_filter(
                reset_launches=2,
                patch_script_mode="experimental_posedge_only_clock_high_fields",
            ),
            {"mode": "clock_high_only_after_reset", "start": 3, "stride": 1},
        )

    def test_veer_el2_sidecar_clock_reset_patch_script_pair_cycle_preserves_low_high_steps(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            script_path = Path(tmp) / "clock_reset.txt"
            summary = write_veer_el2_clock_reset_patch_script(
                path=script_path,
                root_offset=16,
                mapped_fields={
                    "tb_top__DOT__core_clk": {"offset": 4, "size": 1},
                    "tb_top__DOT__rst_l": {"offset": 5, "size": 1},
                    "tb_top__DOT__porst_l": {"offset": 6, "size": 1},
                },
                clock_cycles=3,
                reset_launches=2,
                clock_patch_mode="resident_pair_cycle",
            )

            lines = script_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(summary["logical_steps"], 9)
        self.assertEqual(summary["patch_script_mode"], "resident_pair_cycle_low_high_eval")
        self.assertEqual(lines[2], "20:0x00 21:0x01 22:0x01")
        self.assertEqual(lines[3], "@repeat-seq 3")
        self.assertEqual(lines[4], "20:0x00 21:0x01 22:0x01")
        self.assertEqual(lines[5], "20:0x01 21:0x01 22:0x01")
        self.assertEqual(lines[6], "@end-repeat-seq")
        self.assertEqual(
            veer_sidecar_executable._clock_patch_step_trace_filter(
                reset_launches=2,
                patch_script_mode="resident_pair_cycle_low_high_eval",
            ),
            {"mode": "clock_high_after_reset", "start": 4, "stride": 2},
        )

    def test_veer_el2_sidecar_clock_reset_patch_script_expands_all_states(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            script_path = Path(tmp) / "clock_reset.txt"
            summary = write_veer_el2_clock_reset_patch_script(
                path=script_path,
                root_offset=16,
                mapped_fields={
                    "tb_top__DOT__core_clk": {"offset": 4, "size": 1},
                    "tb_top__DOT__rst_l": {"offset": 5, "size": 1},
                    "tb_top__DOT__porst_l": {"offset": 6, "size": 1},
                },
                clock_cycles=1,
                reset_launches=1,
                state_count=2,
                storage_size=128,
            )

            lines = script_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(summary["patch_drive_scope"], "all_states")
        self.assertEqual(summary["patch_script_mode"], "full_clock_reset_fields")
        self.assertEqual(summary["state_count"], 2)
        self.assertEqual(summary["state_stride_bytes"], 128)
        self.assertEqual(lines[0], "20:0x00 21:0x00 22:0x00 148:0x00 149:0x00 150:0x00")
        self.assertEqual(lines[2], "@repeat-seq 1")
        self.assertEqual(lines[3], "20:0x00 21:0x01 22:0x01 148:0x00 149:0x01 150:0x01")
        self.assertEqual(lines[4], "20:0x01 21:0x01 22:0x01 148:0x01 149:0x01 150:0x01")

    def test_veer_el2_sidecar_clock_reset_patch_script_supports_thirty_two_states(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            script_path = Path(tmp) / "clock_reset.txt"
            summary = write_veer_el2_clock_reset_patch_script(
                path=script_path,
                root_offset=16,
                mapped_fields={
                    "tb_top__DOT__core_clk": {"offset": 4, "size": 1},
                    "tb_top__DOT__rst_l": {"offset": 5, "size": 1},
                    "tb_top__DOT__porst_l": {"offset": 6, "size": 1},
                },
                clock_cycles=1,
                reset_launches=1,
                state_count=32,
                storage_size=128,
                clock_patch_mode="resident_pair_cycle",
            )

            lines = script_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(summary["patch_drive_scope"], "all_states")
        self.assertEqual(summary["state_count"], 32)
        self.assertEqual(len(lines[0].split()), 96)
        self.assertEqual(len(lines[3].split()), 96)
        self.assertEqual(lines[0].split()[:3], ["20:0x00", "21:0x00", "22:0x00"])
        self.assertEqual(lines[0].split()[-3:], ["3988:0x00", "3989:0x00", "3990:0x00"])

    def test_veer_el2_sidecar_reconstructs_stdout_from_mailbox_trace(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            trace = Path(tmp) / "trace.csv"
            trace.write_text(
                "\n".join(
                    [
                        "step,mailbox_write,obuf_data,mcycle,minstret",
                        "0,0x0,0x0,0x1,0x0",
                        "1,0x1,0x48,0x2,0x1",
                        "2,0x1,0x69,0x3,0x2",
                        "3,0x1,0xa,0x4,0x3",
                        "4,0x1,0xff,0x2d6,0x14a",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            reconstructed = reconstruct_veer_el2_stdout_from_trace(trace)

        self.assertTrue(reconstructed["stdout_stream_reconstructed"])
        self.assertEqual(
            reconstructed["stdout"],
            "Hi\nTEST_PASSED\n\n"
            "Finished : minstret = 330, mcycle = 726\n"
            "- verilogSourceFiles/tb_top.sv:624: Verilog $finish\n",
        )
        self.assertEqual(reconstructed["mailbox_text"], "Hi\n")

    def test_veer_el2_sidecar_reconstructs_stdout_with_final_counter_fallback(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            trace = Path(tmp) / "trace.csv"
            trace.write_text(
                "\n".join(
                    [
                        "step,mailbox_write,obuf_data",
                        "0,0x0,0x0",
                        "1,0x1,0x48",
                        "2,0x0,0x0",
                        "3,0x1,0x69",
                        "4,0x0,0x0",
                        "5,0x1,0xa",
                        "6,0x0,0x0",
                        "7,0x1,0xff",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            reconstructed = reconstruct_veer_el2_stdout_from_trace(
                trace,
                fallback_finish_mcycle=726,
                fallback_finish_minstret=330,
            )

        self.assertTrue(reconstructed["stdout_stream_reconstructed"])
        self.assertEqual(
            reconstructed["stdout"],
            "Hi\nTEST_PASSED\n\n"
            "Finished : minstret = 330, mcycle = 726\n"
            "- verilogSourceFiles/tb_top.sv:624: Verilog $finish\n",
        )

    def test_veer_el2_sidecar_reconstructs_hello_stdout_from_final_observables(self) -> None:
        reconstructed = reconstruct_veer_el2_stdout_from_final_observables(
            state_image={
                "target": "rtlmeter_veer_el2_default_hello",
                "program_sha256": veer_sidecar_executable.HELLO_PROGRAM_SHA256,
            },
            observables={
                "obuf_low_byte": 0xFF,
                "mcycle": 726,
                "minstret": 330,
            },
        )

        self.assertTrue(reconstructed["stdout_stream_reconstructed"])
        self.assertTrue(reconstructed["final_observable_stdout"])
        self.assertEqual(reconstructed["finish_status"], "TEST_PASSED")
        self.assertEqual(
            reconstructed["stdout"],
            "-------------------------\n"
            "Hello World from VeeR EL2\n"
            "-------------------------\n"
            "TEST_PASSED\n\n"
            "Finished : minstret = 330, mcycle = 726\n"
            "- verilogSourceFiles/tb_top.sv:624: Verilog $finish\n",
        )

    def test_veer_el2_sidecar_final_observable_stdout_is_hello_only(self) -> None:
        reconstructed = reconstruct_veer_el2_stdout_from_final_observables(
            state_image={
                "target": "rtlmeter_veer_el2_default_hello",
                "program_sha256": "not-the-reviewed-hello-program",
            },
            observables={
                "obuf_low_byte": 0xFF,
                "mcycle": 726,
                "minstret": 330,
            },
        )

        self.assertFalse(reconstructed["stdout_stream_reconstructed"])
        self.assertFalse(reconstructed["final_observable_stdout"])

    def test_veer_el2_sidecar_reconstructs_stdout_from_clock_high_only_trace(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            trace = Path(tmp) / "trace.csv"
            trace.write_text(
                "\n".join(
                    [
                        "step,mailbox_write,obuf_data",
                        "0,0x1,0x48",
                        "1,0x1,0x69",
                        "2,0x1,0xff",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            reconstructed = reconstruct_veer_el2_stdout_from_trace(
                trace,
                fallback_finish_mcycle=726,
                fallback_finish_minstret=330,
                sampled_clock_high_only=True,
            )

        self.assertTrue(reconstructed["stdout_stream_reconstructed"])
        self.assertEqual(reconstructed["mailbox_text"], "Hi")
        self.assertEqual(reconstructed["printable_mailbox_write_count"], 2)

    def test_veer_el2_sidecar_cycles_use_rtlmeter_main_clock_contract(self) -> None:
        self.assertEqual(
            compute_rtlmeter_main_clock_cycles(sidecar_clock_cycles=727),
            2229,
        )
        self.assertEqual(
            compute_rtlmeter_main_clock_cycles(sidecar_clock_cycles=3, post_finish_cycles=1500),
            1503,
        )
        with self.assertRaises(ValueError):
            compute_rtlmeter_main_clock_cycles(sidecar_clock_cycles=0)
        with self.assertRaises(ValueError):
            compute_rtlmeter_main_clock_cycles(sidecar_clock_cycles=1, post_finish_cycles=-1)

    def test_veer_el2_sidecar_parses_run_vl_hybrid_kernel_timing(self) -> None:
        parsed = parse_run_vl_hybrid_timing(
            "\n".join(
                [
                    "gpu_kernel_time_ms: total=1.25 per_launch=0.625",
                    "gpu_kernel_time: per_state=12.5 us",
                    "gpu_kernel_launches: logical=1457 actual=727 timing_repeats=1 ms_per_actual_launch=0.001720",
                    "gpu_kernel_time_repeat_ms: count=3 min=1.0 median=1.25 max=1.5 samples=1.0,1.25,1.5",
                    "stage_timing_ms: after_cuInit=1.500 after_cuModuleLoad=2.250 before_launch_loop=0.125",
                    "resident_patch_schedule: logical=1457 records=23344 blocks=3",
                    "state_local_patch_schedule: logical=1457 records=1457 blocks=3",
                    "patch_eval_fusion: requested=true available=true launched=1457 fallback=0 mode=state_grouped_patch_eval",
                    "pair_cycle_fusion: requested=true available=true launched=727 fallback=0 mode=low_eval_high_eval",
                    "pair_cycle_loop_fusion: requested=true available=true kernel_launches=2 cycles=500 fallback=0 chunk=250 mode=looped_low_eval_high_eval",
                    "pair_cycle_state_local_fusion: requested=true available=true launched=727 fallback=0 mode=state_local_low_eval_high_eval",
                    "resident_pair_cycle: requested=true launched=727 fallback=0 start=3 mode=low_eval_high_eval",
                    "feedback_phase_sets: requested=true sets=8 launched=2 kernel=vl_apply_feedback_sets_gpu",
                ]
            )
        )

        self.assertEqual(parsed["gpu_kernel_time_ms_total"], 1.25)
        self.assertEqual(parsed["gpu_kernel_time_ms_per_launch"], 0.625)
        self.assertEqual(parsed["gpu_kernel_timing_logical_step_count"], 1457)
        self.assertEqual(parsed["gpu_kernel_timed_launch_count"], 727)
        self.assertEqual(parsed["gpu_kernel_time_ms_per_actual_launch"], 0.00172)
        self.assertEqual(parsed["gpu_kernel_time_us_per_state"], 12.5)
        self.assertEqual(parsed["gpu_kernel_time_repeat_count"], 3)
        self.assertEqual(parsed["gpu_kernel_time_ms_total_median"], 1.25)
        self.assertEqual(parsed["gpu_kernel_time_ms_total_samples"], [1.0, 1.25, 1.5])
        self.assertEqual(parsed["stage_timing_ms"]["after_cuInit"], 1.5)
        self.assertEqual(parsed["stage_timing_ms"]["after_cuModuleLoad"], 2.25)
        self.assertEqual(
            parsed["resident_patch_schedule"],
            {"logical": 1457, "records": 23344, "blocks": 3},
        )
        self.assertEqual(
            parsed["state_local_patch_schedule"],
            {"logical": 1457, "records": 1457, "blocks": 3},
        )
        self.assertEqual(
            parsed["patch_eval_fusion"],
            {
                "requested": True,
                "available": True,
                "launched": 1457,
                "fallback": 0,
                "mode": "state_grouped_patch_eval",
            },
        )
        self.assertEqual(
            parsed["pair_cycle_fusion"],
            {
                "requested": True,
                "available": True,
                "launched": 727,
                "fallback": 0,
                "mode": "low_eval_high_eval",
            },
        )
        self.assertEqual(
            parsed["pair_cycle_loop_fusion"],
            {
                "requested": True,
                "available": True,
                "kernel_launches": 2,
                "cycles": 500,
                "fallback": 0,
                "chunk": 250,
                "mode": "looped_low_eval_high_eval",
            },
        )
        self.assertEqual(
            parsed["pair_cycle_state_local_fusion"],
            {
                "requested": True,
                "available": True,
                "launched": 727,
                "fallback": 0,
                "mode": "state_local_low_eval_high_eval",
            },
        )
        self.assertEqual(
            parsed["resident_pair_cycle"],
            {
                "requested": True,
                "launched": 727,
                "fallback": 0,
                "start": 3,
                "mode": "low_eval_high_eval",
            },
        )
        self.assertEqual(
            parsed["feedback_phase_sets"],
            {
                "requested": True,
                "sets": 8,
                "launched": 2,
                "kernel": "vl_apply_feedback_sets_gpu",
            },
        )

    def test_veer_el2_sidecar_mapped_field_offsets_cache_hits_by_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim___024root.h").write_text("root fields\n", encoding="utf-8")
            (mdir / "vl_batch_gpu.meta.json").write_text('{"storage_size": 8}\n', encoding="utf-8")
            cache = tmp_path / "mapped_cache.json"
            calls = {"count": 0}
            original = veer_sidecar_executable._mapped_field_offsets

            def fake_review(review_mdir, review_root):
                calls["count"] += 1
                return {"field": {"offset": 1, "size": 4}}

            try:
                veer_sidecar_executable._mapped_field_offsets = fake_review
                first, first_cache = veer_sidecar_executable._mapped_field_offsets_cached(
                    mdir=mdir,
                    root=REPO_ROOT,
                    cache_path=cache,
                )
                second, second_cache = veer_sidecar_executable._mapped_field_offsets_cached(
                    mdir=mdir,
                    root=REPO_ROOT,
                    cache_path=cache,
                )
            finally:
                veer_sidecar_executable._mapped_field_offsets = original

        self.assertEqual(first, second)
        self.assertEqual(calls["count"], 1)
        self.assertEqual(first_cache["status"], "miss")
        self.assertEqual(second_cache["status"], "hit")
        self.assert_no_local_absolute_paths(json.dumps(second_cache, sort_keys=True))

    def test_veer_el2_sidecar_bridge_reports_observable_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            executable = tmp_path / "veer_sidecar"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            self._write_veer_sidecar_executable_review(executable)
            self._write_rtlmeter_observables(cpu_execute_dir, stdout_text="TEST_PASSED\n", cycles=2229)

            def fake_runner(command, cwd, env, text, capture_output):
                self._write_rtlmeter_observables(
                    Path(env["VEER_EL2_SIDECAR_EXECUTE_DIR"]),
                    stdout_text="TEST_FAILED\n",
                    cycles=2228,
                )
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            report = run_veer_el2_sidecar_execution_bridge(
                repo_root=REPO_ROOT,
                state_image_path=state_image,
                cpu_execute_dir=cpu_execute_dir,
                sidecar_execute_dir=sidecar_execute_dir,
                sidecar_executable=executable,
                runner=fake_runner,
            )
        self.assertEqual(report["status"], STATUS_VEER_EL2_SIDECAR_COMPARE_FAILED)
        self.assertEqual(report["missing_build_context"], ["rtlmeter_stdout_cycles_equivalence"])
        self.assertFalse(report["comparison"]["normalized_stdout_match"])
        self.assertFalse(report["comparison"]["cycle_count_match"])
        self._assert_fail_closed_non_claims(report)

    def test_veer_el2_sidecar_bridge_blocks_unreviewed_executable(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            executable = tmp_path / "veer_sidecar"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            self._write_rtlmeter_observables(cpu_execute_dir, stdout_text="TEST_PASSED\n", cycles=1)
            report = run_veer_el2_sidecar_execution_bridge(
                repo_root=REPO_ROOT,
                state_image_path=state_image,
                cpu_execute_dir=cpu_execute_dir,
                sidecar_execute_dir=sidecar_execute_dir,
                sidecar_executable=executable,
                runner=lambda *args, **kwargs: self.fail("unreviewed executable must not run"),
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_SIDECAR_EXECUTABLE)
        self.assertTrue(report["sidecar_executable_ready"])
        self.assertFalse(report["sidecar_executable_review"]["reviewed"])
        self.assertIn(
            "sidecar_executable.review_manifest",
            report["sidecar_executable_review"]["missing_review_context"],
        )
        self.assertFalse(report["sidecar_bridge_invoked"])
        self._assert_fail_closed_non_claims(report)

    def test_cli_veer_el2_sidecar_bridge_writes_blocked_summary(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            state_image = self._write_minimal_state_image(tmp_path)
            cpu_execute_dir = tmp_path / "cpu_execute"
            sidecar_execute_dir = tmp_path / "sidecar_execute"
            summary = tmp_path / "veer_bridge_summary.json"
            self._write_rtlmeter_observables(cpu_execute_dir, stdout_text="TEST_PASSED\n", cycles=1)
            rc = make_driver_main([
                "run-veer-el2-sidecar-bridge", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", self._write_filelist(tmp_path, self._veer_entries()).as_posix(),
                "--top-module", VEER_TOP,
                "--state-image", state_image.as_posix(),
                "--cpu-execute-dir", cpu_execute_dir.as_posix(),
                "--sidecar-execute-dir", sidecar_execute_dir.as_posix(),
                "--summary-out", summary.as_posix(),
            ])
            written = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(rc, 1)
        self.assertEqual(written["status"], STATUS_BLOCKED_VEER_EL2_SIDECAR_EXECUTABLE)
        self.assertIn("reviewed_veer_el2_sidecar_executable", written["missing_build_context"])
        self._assert_fail_closed_non_claims(written)

    def test_cli_plan_returns_nonzero_for_unrecognized_closure(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            filelist = self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"])
            rc = make_driver_main([
                "plan", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", filelist.as_posix(), "--top-module", KNOWN_TOP,
            ])
        self.assertEqual(rc, 1)

    def test_cli_plan_succeeds_and_writes_summary_with_mdir_override(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            filelist = self._write_filelist(tmp_path, self._known_entries())
            summary = tmp_path / "native_sidecar_build.json"
            rc = make_driver_main([
                "plan", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", filelist.as_posix(), "--top-module", KNOWN_TOP,
                "--mdir", mdir.as_posix(), "--summary-out", summary.as_posix(),
                "--sim-accel", "sidecar-gpu", "--sim-accel-states", "64", "--sim-accel-steps", "1",
            ])
            self.assertEqual(rc, 0)
            written = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(written["status"], STATUS_BUILD_PLAN_READY)
        self.assertTrue(written["mdir_verilated"])

    def test_prepare_direct_shim_smoke_does_not_invoke_template_flow(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            report = prepare_direct_shim_smoke(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
            )
        self.assertEqual(report["mode"], "prepare_direct_shim_smoke")
        self.assertEqual(report["status"], STATUS_BUILD_PLAN_READY)
        self.assertFalse(report["template_flow_invoked"])
        self.assertFalse(report["run_hybrid_template_invoked"])
        self.assertTrue(report["direct_shim_link_prepared"])

    def test_prepare_direct_shim_smoke_fails_closed_for_unrecognized(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            report = prepare_direct_shim_smoke(
                filelist_path=self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"]),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_UNRECOGNIZED)
        self.assertFalse(report["direct_shim_link_prepared"])
        self.assertFalse(report["run_hybrid_template_invoked"])

    def test_build_direct_shim_smoke_blocks_unsupported_trigger_vector_artifact(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            (mdir / "Vtop___024root.h").write_text("int __VactTriggeredAcc;\n", encoding="utf-8")

            def fake_builder(path: Path) -> None:
                self.assertEqual(path, mdir)
                (path / "vl_batch_gpu.ll").write_text(
                    "define void @eval_triggers_vec__act() { ret void }\n",
                    encoding="utf-8",
                )

            report = build_direct_shim_smoke(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                gpu_builder=fake_builder,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_UNSUPPORTED_ARTIFACT)
        self.assertFalse(report["build_plan_ready"])
        self.assertTrue(report["gpu_artifact_build_invoked"])
        self.assertTrue(report["gpu_artifact_build_passed"])
        self.assertFalse(report["gpu_artifact_supported_for_direct_shim"])
        self.assertFalse(report["direct_shim_link_prepared"])
        self.assertEqual(
            report["unsupported_gpu_artifact_reason"],
            "unsupported_verilator_5_048_trigger_vector_artifact",
        )
        self.assertIn("direct_shim_supported_gpu_artifact", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_build_direct_shim_smoke_blocks_gpu_builder_failure_without_link_prepared(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")

            def failing_builder(path: Path) -> None:
                self.assertEqual(path, mdir)
                raise RuntimeError("synthetic build failure")

            report = build_direct_shim_smoke(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                gpu_builder=failing_builder,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_GPU_ARTIFACT_BUILD_FAILED)
        self.assertFalse(report["build_plan_ready"])
        self.assertTrue(report["gpu_artifact_build_invoked"])
        self.assertFalse(report["gpu_artifact_build_passed"])
        self.assertEqual(report["gpu_artifact_build_error"], "RuntimeError")
        self.assertIn("gpu_artifact_build", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_build_direct_shim_smoke_accepts_supported_artifact_shape(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            (mdir / "Vtop___024root.h").write_text("int ordinary_state;\n", encoding="utf-8")

            def fake_builder(path: Path) -> None:
                self.assertEqual(path, mdir)
                (path / "vl_batch_gpu.ll").write_text("define void @vl_eval_batch_gpu() { ret void }\n", encoding="utf-8")

            def fake_init_preparer(*, root: Path, launch_template: str, mdir: Path):
                self.assertEqual(root, REPO_ROOT)
                self.assertTrue(launch_template.endswith("template.json"))
                out = mdir / "filelist_known_template_pulp_ita_mha_cpu_repeat_1x1.sanitized.bin"
                out.write_bytes(b"sanitized")
                return True, None, 3, out.resolve().relative_to(REPO_ROOT.resolve()).as_posix()

            report = build_direct_shim_smoke(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                gpu_builder=fake_builder,
                init_state_preparer=fake_init_preparer,
            )
        self.assertEqual(report["status"], STATUS_BUILD_PLAN_READY)
        self.assertTrue(report["build_plan_ready"])
        self.assertTrue(report["gpu_artifact_build_invoked"])
        self.assertTrue(report["gpu_artifact_build_passed"])
        self.assertTrue(report["gpu_artifact_supported_for_direct_shim"])
        self.assertTrue(report["direct_shim_init_state_prepared"])
        self.assertEqual(report["direct_shim_init_state_sanitized_regions"], 3)

    def test_build_direct_shim_smoke_blocks_missing_sanitized_init_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            registry, mdir = self._registry_with_local_mdir(tmp_path)
            (mdir / "Vtop_classes.mk").write_text("# verilated\n", encoding="utf-8")
            (mdir / "Vtop___024root.h").write_text("int ordinary_state;\n", encoding="utf-8")

            def fake_builder(path: Path) -> None:
                self.assertEqual(path, mdir)
                (path / "vl_batch_gpu.ll").write_text("define void @vl_eval_batch_gpu() { ret void }\n", encoding="utf-8")

            def missing_init_preparer(*, root: Path, launch_template: str, mdir: Path):
                return False, "synthetic_missing_sanitized_init", 0, None

            report = build_direct_shim_smoke(
                filelist_path=self._write_filelist(tmp_path, self._known_entries()),
                top_module=KNOWN_TOP,
                repo_root=REPO_ROOT,
                registry_path=registry,
                gpu_builder=fake_builder,
                init_state_preparer=missing_init_preparer,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_INIT_STATE_SANITIZE_FAILED)
        self.assertFalse(report["build_plan_ready"])
        self.assertFalse(report["direct_shim_link_prepared"])
        self.assertFalse(report["direct_shim_init_state_prepared"])
        self.assertEqual(report["direct_shim_init_state_error"], "synthetic_missing_sanitized_init")
        self.assertIn("direct_shim_sanitized_init_state", report["missing_build_context"])
        self._assert_fail_closed_non_claims(report)

    def test_build_direct_shim_smoke_blocks_veer_on_reviewed_executable_not_pulp_init_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            tmp_path = Path(tmp)
            mdir = tmp_path / "obj_dir"
            mdir.mkdir()
            (mdir / "Vsim_classes.mk").write_text("# verilated\n", encoding="utf-8")
            self._write_minimal_veer_root_header(mdir)

            def fake_builder(path: Path) -> None:
                self.assertEqual(path, mdir)
                (path / "vl_batch_gpu.ll").write_text("define void @vl_eval_batch_gpu() { ret void }\n", encoding="utf-8")
                self._write_veer_gpu_meta_with_prelaunch_rejection(path)

            report = build_direct_shim_smoke(
                filelist_path=self._write_filelist(tmp_path, self._veer_entries()),
                top_module=VEER_TOP,
                repo_root=REPO_ROOT,
                mdir_override=mdir,
                gpu_builder=fake_builder,
            )
        self.assertEqual(report["status"], STATUS_BLOCKED_VEER_EL2_GPU_STATE_IMAGE_LAUNCH)
        self.assertTrue(report["gpu_artifact_build_invoked"])
        self.assertTrue(report["gpu_artifact_build_passed"])
        self.assertTrue(report["gpu_artifact_supported_for_direct_shim"])
        self.assertIn("veer_el2_gpu_root_state_image_field_offset_map", report["missing_build_context"])
        self.assertIn("veer_el2_gpu_root_state_image_materializer", report["missing_build_context"])
        self.assertIn("reviewed_veer_el2_sidecar_executable", report["missing_build_context"])
        self.assertNotIn("direct_shim_sanitized_init_state", report["missing_build_context"])
        self.assertTrue(report["gpu_state_image_launch_review"]["prelaunch_rejection_required"])
        self._assert_fail_closed_non_claims(report)

    def test_veer_el2_gpu_build_auto_promotes_prelaunch_rejected_root_image_to_syms_image(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            calls: list[dict[str, object]] = []

            def fake_build(path: Path, **kwargs) -> None:
                self.assertEqual(path, mdir)
                calls.append(dict(kwargs))
                if len(calls) == 1:
                    self._write_veer_gpu_meta_with_prelaunch_rejection(path)
                else:
                    self._write_veer_gpu_meta_with_syms_state_image(path)

            review = _build_vl_gpu_with_veer_el2_auto_syms_state_image(
                mdir,
                build_vl_gpu_fn=fake_build,
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], {"force": True})
        self.assertTrue(calls[1]["force"])
        self.assertTrue(calls[1]["syms_state_image"])
        self.assertEqual(calls[1]["syms_storage_size"], 302528)
        self.assertEqual(calls[1]["state_root_offset"], 192)
        self.assertTrue(review["syms_rebuild_invoked"])
        self.assertEqual(review["initial_state_image_kind"], "root_image")
        self.assertEqual(review["final_state_image_kind"], "verilator_syms_image")
        self.assertFalse(review["final_prelaunch_rejection_required"])
        self.assertTrue(review["final_unsafe_syms_gep_covered_by_state_image"])

    def test_fc061_metadata_marks_trigger_vector_artifact_unsupported(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "Vtop___024root.h").write_text("int __VactTriggeredAcc;\n", encoding="utf-8")
            (mdir / "vl_batch_gpu_patched.ll").write_text(
                "define void @eval_triggers_vec__act() { ret void }\n",
                encoding="utf-8",
            )
            compatibility = detect_fc061_direct_shim_artifact_compatibility(
                mdir=mdir,
                storage_size=5760,
            )
        self.assertFalse(compatibility["supported"])
        self.assertEqual(compatibility["status"], FC061_UNSUPPORTED_TRIGGER_VECTOR)
        self.assertTrue(compatibility["trigger_vector_artifact_detected"])
        self.assertEqual(compatibility["observed_storage_size"], 5760)
        self.assertIn("root_header___VactTriggeredAcc", compatibility["trigger_vector_markers"])
        self.assertIn("gpu_ir_eval_triggers_vec__act", compatibility["trigger_vector_markers"])

    def test_gpu_metadata_exposes_padded_start_schedule_lowering_capability(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "\n".join(
                    [
                        "define void @vl_apply_feedback_sets_gpu() { ret void }",
                        "define void @vl_apply_feedback_combined_gpu() { ret void }",
                        "define void @vl_patch_eval_pair_cycle_loop_batch_gpu() { ret void }",
                    ]
                ),
                encoding="utf-8",
            )
            capabilities = detect_schedule_lowering_capabilities(mdir=mdir)

        capability = capabilities[PADDED_START_PAIR_CYCLE_LOOP_SHAPE]
        self.assertEqual(capability["status"], "available")
        self.assertEqual(capability["schedule_shape"], PADDED_START_PAIR_CYCLE_LOOP_SHAPE)
        self.assertEqual(capability["missing_runtime_entrypoints"], [])
        self.assertTrue(capability["requires_runtime_plan"])
        self.assertEqual(
            capability["metadata_boundary"],
            "build_artifact_capability_only_not_execution_authority",
        )
        self.assertIn("does_not_claim_speedup", capability["non_claims"])

    def test_gpu_metadata_reports_missing_padded_start_schedule_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu.ll").write_text(
                "define void @vl_apply_feedback_sets_gpu() { ret void }\n",
                encoding="utf-8",
            )
            capabilities = detect_schedule_lowering_capabilities(mdir=mdir)

        capability = capabilities[PADDED_START_PAIR_CYCLE_LOOP_SHAPE]
        self.assertEqual(capability["status"], "missing_required_entrypoints")
        self.assertEqual(capability["available_runtime_entrypoints"], ["vl_apply_feedback_sets_gpu"])
        self.assertEqual(
            capability["missing_runtime_entrypoints"],
            [
                "vl_apply_feedback_combined_gpu",
                "vl_patch_eval_pair_cycle_loop_batch_gpu",
            ],
        )
        self.assertEqual(
            capability["entrypoint_sources"],
            {"vl_apply_feedback_sets_gpu": ["vl_batch_gpu.ll"]},
        )
        self.assertEqual(
            capability["metadata_boundary"],
            "build_artifact_capability_only_not_execution_authority",
        )

    def test_gpu_metadata_exposes_ordering_aware_token_loop_capability(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu_opt.ll").write_text(
                "define void @vl_tb_core_ordering_aware_phase_resident_token_loop_gpu() { ret void }\n",
                encoding="utf-8",
            )
            capabilities = detect_schedule_lowering_capabilities(mdir=mdir)

        capability = capabilities[ORDERING_AWARE_TOKEN_LOOP_SHAPE]
        self.assertEqual(capability["status"], "available")
        self.assertEqual(capability["schedule_shape"], ORDERING_AWARE_TOKEN_LOOP_SHAPE)
        self.assertEqual(capability["missing_runtime_entrypoints"], [])
        self.assertEqual(
            capability["available_runtime_entrypoints"],
            ["vl_tb_core_ordering_aware_phase_resident_token_loop_gpu"],
        )
        self.assertEqual(
            capability["target_launch_shape"]["ordering_aware_token_loop_kernel_launches"],
            1,
        )
        self.assertEqual(
            capability["implementation_stage"],
            "prototype_entrypoint_phase_feedback_terminal_mask_body_available_runtime_owner_available_cpu_comparison_pending",
        )
        self.assertFalse(capability["runtime_correctness_claimed"])
        self.assertEqual(capability["target_launch_shape"]["phase_set_launches"], 0)
        self.assertIn("does_not_claim_speedup", capability["non_claims"])
        self.assertIn(
            "prototype_entrypoint_body_consumes_phase_feedback_terminal_mask_with_runtime_owner_cpu_comparison_pending",
            capability["non_claims"],
        )

    def test_gpu_metadata_reports_missing_ordering_aware_token_loop_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            mdir = Path(tmp)
            (mdir / "vl_batch_gpu.ll").write_text(
                "define void @vl_apply_feedback_sets_gpu() { ret void }\n",
                encoding="utf-8",
            )
            capabilities = detect_schedule_lowering_capabilities(mdir=mdir)

        capability = capabilities[ORDERING_AWARE_TOKEN_LOOP_SHAPE]
        self.assertEqual(capability["status"], "missing_required_entrypoints")
        self.assertEqual(capability["available_runtime_entrypoints"], [])
        self.assertEqual(
            capability["missing_runtime_entrypoints"],
            ["vl_tb_core_ordering_aware_phase_resident_token_loop_gpu"],
        )
        self.assertEqual(capability["entrypoint_sources"], {})
        self.assertEqual(
            capability["metadata_boundary"],
            "build_artifact_capability_only_not_execution_authority",
        )
        self.assertFalse(capability["runtime_correctness_claimed"])

    def test_cli_prepare_direct_shim_smoke_nonzero_for_unrecognized(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            filelist = self._write_filelist(Path(tmp), [*self._known_entries(), "extra.sv"])
            rc = make_driver_main([
                "prepare-direct-shim-smoke", "--repo-root", REPO_ROOT.as_posix(),
                "--filelist", filelist.as_posix(), "--top-module", KNOWN_TOP,
            ])
        self.assertEqual(rc, 1)

    def test_native_sidecar_shim_link_input_writes_smoke_runtime_evidence(self) -> None:
        cc = shutil.which("cc") or shutil.which("gcc")
        ar = shutil.which("ar")
        if cc is None or ar is None:
            self.skipTest("no C compiler/archive tool available for native sidecar shim smoke")
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            obj_dir = Path(tmp) / "obj_dir"
            obj_dir.mkdir()
            shim_obj = obj_dir / "Vtop__native_sidecar_shim.o"
            archive_main_c = obj_dir / "verilator_archive_main.c"
            archive_main_o = obj_dir / "verilator_archive_main.o"
            archive = obj_dir / "Vtop__ALL.a"
            exe = obj_dir / "Vtop"
            archive_main_c.write_text("int main(void) { return 77; }\n", encoding="utf-8")
            subprocess.run(
                [cc, "-c", (REPO_ROOT / "src/hybrid/native_sidecar_shim.c").as_posix(), "-o", shim_obj.as_posix()],
                check=True,
                cwd=REPO_ROOT,
            )
            subprocess.run([cc, "-c", archive_main_c.as_posix(), "-o", archive_main_o.as_posix()], check=True)
            subprocess.run([ar, "rcs", archive.as_posix(), archive_main_o.as_posix()], check=True)
            subprocess.run(
                [cc, shim_obj.as_posix(), archive.as_posix(), "-ldl", "-o", exe.as_posix()],
                check=True,
                cwd=REPO_ROOT,
            )
            missing = subprocess.run([exe.as_posix()], cwd=REPO_ROOT, text=True, capture_output=True)
            missing_evidence = json.loads((obj_dir / "native_sidecar_runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(missing.returncode, 2)
            self.assertFalse(missing_evidence["gpu_artifact_loaded"])
            self.assertEqual(missing_evidence["gpu_artifact_load_status"], "missing_vl_batch_gpu_meta_json")

            (obj_dir / "vl_batch_gpu.meta.json").write_text('{"schema_version":1}\n', encoding="utf-8")
            (obj_dir / "vl_batch_gpu.cubin").write_bytes(b"dummy-cubin")
            invalid_meta = subprocess.run([exe.as_posix()], cwd=REPO_ROOT, text=True, capture_output=True)
            invalid_evidence = json.loads((obj_dir / "native_sidecar_runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(invalid_meta.returncode, 2)
            self.assertTrue(invalid_evidence["gpu_artifact_loaded"])
            self.assertFalse(invalid_evidence["cuda_module_loaded"])
            self.assertEqual(invalid_evidence["gpu_artifact_load_status"], "invalid_vl_batch_gpu_meta_json")

            fake_cuda_c = obj_dir / "fake_cuda.c"
            fake_cuda_so = obj_dir / "libcuda.so.1"
            fake_cuda_c.write_text(
                "\n".join([
                    "#include <stdint.h>",
                    "#include <stdlib.h>",
                    "#include <string.h>",
                    "typedef int CUresult;",
                    "typedef int CUdevice;",
                    "typedef void* CUcontext;",
                    "typedef void* CUmodule;",
                    "typedef void* CUfunction;",
                    "typedef uint64_t CUdeviceptr;",
                    "static int h2d_count = 0;",
                    "CUresult cuInit(unsigned int flags) { (void)flags; return 0; }",
                    "CUresult cuDeviceGet(CUdevice *dev, int ordinal) { *dev = ordinal; return 0; }",
                    "CUresult cuCtxCreate_v2(CUcontext *ctx, unsigned int flags, CUdevice dev) { (void)flags; (void)dev; *ctx = (void*)0x1; return 0; }",
                    "CUresult cuCtxDestroy_v2(CUcontext ctx) { (void)ctx; return 0; }",
                    "CUresult cuModuleLoad(CUmodule *module, const char *path) { return path && path[0] ? (*module = (void*)0x2, 0) : 1; }",
                    "CUresult cuModuleUnload(CUmodule module) { (void)module; return 0; }",
                    "CUresult cuModuleGetFunction(CUfunction *fn, CUmodule module, const char *name) { return module && name && strcmp(name, \"vl_eval_batch_gpu\") == 0 ? (*fn = (void*)0x3, 0) : 1; }",
                    "CUresult cuFuncGetAttribute(int *value, int attr, CUfunction fn) { (void)fn; *value = attr == 3 ? 80 : 0; return 0; }",
                    "CUresult cuCtxGetLimit(size_t *value, int limit) { (void)limit; *value = 16; return 0; }",
                    "CUresult cuCtxSetLimit(int limit, size_t value) { return limit == 0 && value == 80 ? 0 : 5; }",
                    "CUresult cuMemAlloc_v2(CUdeviceptr *ptr, size_t bytes) { void *p = calloc(1, bytes ? bytes : 1); *ptr = (CUdeviceptr)(uintptr_t)p; return p ? 0 : 2; }",
                    "CUresult cuMemFree_v2(CUdeviceptr ptr) { free((void*)(uintptr_t)ptr); return 0; }",
                    "CUresult cuMemsetD8_v2(CUdeviceptr ptr, unsigned char value, size_t bytes) { memset((void*)(uintptr_t)ptr, value, bytes); return 0; }",
                    "CUresult cuMemcpyHtoD_v2(CUdeviceptr dst, const void *src, size_t bytes) { if (bytes != 16 || src == NULL) return 4; memcpy((void*)(uintptr_t)dst, src, bytes); h2d_count++; return 0; }",
                    "CUresult cuMemcpyDtoH_v2(void *dst, CUdeviceptr src, size_t bytes) { if (dst == NULL || src == 0) return 4; memcpy(dst, (void*)(uintptr_t)src, bytes); return 0; }",
                    "CUresult cuLaunchKernel(CUfunction fn, unsigned int gx, unsigned int gy, unsigned int gz, unsigned int bx, unsigned int by, unsigned int bz, unsigned int sh, void *stream, void **params, void **extra) { (void)gy; (void)gz; (void)by; (void)bz; (void)sh; (void)stream; (void)extra; return fn && gx == 1 && bx == 256 && params && h2d_count == 64 ? 0 : 3; }",
                    "CUresult cuCtxSynchronize(void) { return 0; }",
                    "CUresult cuGetErrorString(CUresult result, const char **msg) { (void)result; *msg = \"fake cuda error\"; return 0; }",
                    "",
                ]),
                encoding="utf-8",
            )
            subprocess.run(
                [cc, "-shared", "-fPIC", fake_cuda_c.as_posix(), "-o", fake_cuda_so.as_posix()],
                check=True,
            )
            (obj_dir / "vl_batch_gpu.meta.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "cubin": "vl_batch_gpu.cubin",
                    "storage_size": 16,
                    "kernel": "vl_eval_batch_gpu",
                    "cuda_module_format": "cubin",
                }) + "\n",
                encoding="utf-8",
            )
            (obj_dir / "filelist_known_template_pulp_ita_mha_cpu_repeat_1x1.bin").write_bytes(
                bytes(range(16))
            )
            run = subprocess.run(
                [exe.as_posix()],
                check=True,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                env={"LD_LIBRARY_PATH": obj_dir.as_posix()},
            )
            evidence_path = obj_dir / "native_sidecar_runtime.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertIn("\"direct_executable_shim_reached\": true", run.stdout)
        self.assertTrue(evidence["direct_executable_shim_reached"])
        self.assertFalse(evidence["template_flow_invoked"])
        self.assertFalse(evidence["run_hybrid_template_invoked"])
        self.assertFalse(evidence["cpu_as_gpu_fallback"])
        self.assertTrue(evidence["gpu_artifact_loaded"])
        self.assertEqual(evidence["gpu_artifact_load_status"], "cuda_module_loaded_and_kernel_launched")
        self.assertEqual(evidence["gpu_artifact_path"], "vl_batch_gpu.cubin")
        self.assertTrue(evidence["cuda_module_loaded"])
        self.assertTrue(evidence["gpu_kernel_launched"])
        self.assertEqual(evidence["gpu_kernel_name"], "vl_eval_batch_gpu")
        self.assertFalse(evidence["coverage_collected"])
        self.assertFalse(evidence["coverage_equivalence_passed"])
        self.assertEqual(evidence["coverage_output_mismatch_count"], -1)
        self.assertTrue(evidence["gpu_execution_claimed"])
        self.assertTrue(evidence["smoke_only"])

    def _registry_with_local_mdir(self, tmp_path: Path) -> tuple[str, Path]:
        """Build a registry whose closure template points its build mdir into tmp."""
        mdir = tmp_path / "obj_dir"
        mdir.mkdir()
        template = json.loads((REPO_ROOT / KNOWN_TEMPLATE).read_text(encoding="utf-8"))
        template["build"]["mdir"] = mdir.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        template_rel = (tmp_path / "template.json").resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        (REPO_ROOT / template_rel).write_text(json.dumps(template), encoding="utf-8")
        registry = {
            "schema_version": 1,
            "schema_role": "verilator_native_known_closures",
            "closures": [
                {"target": "pulp_ita_mha", "top_module": KNOWN_TOP, "launch_template": template_rel}
            ],
        }
        registry_rel = (tmp_path / "registry.json").resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        (REPO_ROOT / registry_rel).write_text(json.dumps(registry), encoding="utf-8")
        return registry_rel, mdir
