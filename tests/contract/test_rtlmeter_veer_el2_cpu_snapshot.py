import json
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVeerEl2CpuSnapshotTest(HybridCliTestCase):
    def test_plan_is_non_executing_and_sanitized(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_cpu_snapshot import run_cpu_snapshot

        report = run_cpu_snapshot(target_mcycle=199999, execute=False)

        self.assertEqual(report["surface"], "rtlmeter_veer_el2_cpu_snapshot")
        self.assertEqual(report["status"], "opt_in_required")
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["speedup_claimed"])
        self.assertFalse(report["same_cycle_cpu_snapshot"])
        self.assertIn("compile", report["commands"])
        self.assertIn("run", report["commands"])
        self.assertIn("+snapshot_mcycle=199999", report["commands"]["run"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_parses_snapshot_json(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_cpu_snapshot import run_cpu_snapshot

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj_dir = root / "artifacts/compile/VeeR-EL2/default/compile-0/obj_dir"
            obj_dir.mkdir(parents=True)
            for name in ("Vsim__ALL.a", "verilated.o", "verilated_threads.o", "verilated_timing.o"):
                (obj_dir / name).write_text("", encoding="utf-8")
            execute_dir = root / "artifacts/execute/dhry"
            execute_dir.mkdir(parents=True)
            (execute_dir / "program.hex").write_text("@0\n00\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                if command[0] == "g++":
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                stdout = (
                    "noise\n"
                    '{"mcycle":199999,"minstret":191985,"pc":1073743379,'
                    '"mailbox_write":0,"obuf_data":10,"obuf_low_byte":10,'
                    '"finish_marker_observed":false,"reached_target":true,'
                    '"got_finish":false,"events_exhausted":false,"time":400000,'
                    '"target_mcycle":199999}\n'
                )
                return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

            report = run_cpu_snapshot(
                compile_root="artifacts/compile",
                execute_dir="artifacts/execute/dhry",
                artifact_root="artifacts/snapshot",
                target_mcycle=199999,
                execute=True,
                repo_root=root,
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["same_cycle_cpu_snapshot"])
        self.assertEqual(report["snapshot"]["mcycle"], 199999)
        self.assertEqual(report["snapshot"]["pc_hex"], "0x40000613")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_parses_snapshot_json_after_program_stdout_without_newline(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_cpu_snapshot import run_cpu_snapshot

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj_dir = root / "artifacts/compile/VeeR-EL2/default/compile-0/obj_dir"
            obj_dir.mkdir(parents=True)
            for name in ("Vsim__ALL.a", "verilated.o", "verilated_threads.o", "verilated_timing.o"):
                (obj_dir / name).write_text("", encoding="utf-8")
            execute_dir = root / "artifacts/execute/dhry"
            execute_dir.mkdir(parents=True)
            (execute_dir / "program.hex").write_text("@0\n00\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                if command[0] == "g++":
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                stdout = (
                    "Dhrystone Benchmark, Version 2.1 (Language: C)\n"
                    "Program compiled wi"
                    '{"schema_version":1,'
                    '"surface":"rtlmeter_veer_el2_cpu_snapshot.executable",'
                    '"target_mcycle":0,"target_post_reset_cycles":500,'
                    '"post_reset_posedges":500,"reset_released_seen":true,'
                    '"mcycle":497,"minstret":360,"pc":1073742545,'
                    '"mailbox_write":0,"obuf_data":105,"obuf_low_byte":105,'
                    '"finish_marker_observed":false,"reached_target":true,'
                    '"got_finish":false,"events_exhausted":false,"time":4995}\n'
                )
                return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

            report = run_cpu_snapshot(
                compile_root="artifacts/compile",
                execute_dir="artifacts/execute/dhry",
                artifact_root="artifacts/snapshot",
                target_mcycle=0,
                target_post_reset_cycles=500,
                execute=True,
                repo_root=root,
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["snapshot"]["mcycle"], 497)
        self.assertEqual(report["snapshot"]["pc_hex"], "0x400002d1")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_parses_trace_rows(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_cpu_snapshot import run_cpu_snapshot

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj_dir = root / "artifacts/compile/VeeR-EL2/default/compile-0/obj_dir"
            obj_dir.mkdir(parents=True)
            for name in ("Vsim__ALL.a", "verilated.o", "verilated_threads.o", "verilated_timing.o"):
                (obj_dir / name).write_text("", encoding="utf-8")
            execute_dir = root / "artifacts/execute/dhry"
            execute_dir.mkdir(parents=True)
            (execute_dir / "program.hex").write_text("@0\n00\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                if command[0] == "g++":
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                stdout = (
                    '{"schema_version":1,'
                    '"surface":"rtlmeter_veer_el2_cpu_snapshot.executable",'
                    '"target_mcycle":0,"target_post_reset_cycles":1002,'
                    '"trace_start_post_reset_cycles":875,'
                    '"trace_end_post_reset_cycles":1002,'
                    '"post_reset_posedges":1002,"reset_released_seen":true,'
                    '"mcycle":999,"minstret":746,"pc":1073742228,'
                    '"pc_d":1073742230,'
                    '"mailbox_write":0,"obuf_data":117,"obuf_low_byte":117,'
                    '"finish_marker_observed":false,"reached_target":true,'
                    '"got_finish":false,"events_exhausted":false,"time":10015,'
                    '"trace":[{"post_reset_posedges":875,"time":8745,'
                    '"mcycle":872,"minstret":655,"pc":1073742267,'
                    '"pc_d":1073742269,'
                    '"dec_decode_valid_gate":1,"dec_i0_exublock_d":0,'
                    '"dma_dccm_stall_any":0,"ifu_ifc_fbwrite_dout":96,'
                    '"ifu_ifc_fetch_consume_gate":0,'
                    '"tb_ifu_axi_rvalid":1,"tb_ifu_axi_rid":3,'
                    '"tb_ifu_axi_rresp":0,"tb_ifu_axi_rdata":1234605616436508552,'
                    '"tb_mux_axi_rvalid":1,"tb_sb_axi_rdata":9833440827789222417,'
                    '"tb_lmem_axi_rvalid":1,"tb_lmem_axi_rdata":72623859790382856,'
                    '"tb_ifu_axi_arready":1,"ifu_bus_cmd_valid":1,'
                    '"ifu_bus_rd_addr_count":3,"ifu_fetch_addr_f":1073742464,'
                    '"ifu_pmp_addr":1073742472,"ifu_ifc_fetch_req_bf":1,'
                    '"ifu_ifc_fb_write_ns":8,"ifu_ifc_miss_f":1,'
                    '"ifu_mem_miss_f":33554467,"ifu_mem_miss_state":2,'
                    '"ifu_mem_miss_state_en":1,"ifu_mem_write_ic_16_bytes":1,'
                    '"ifu_mem_ic_act_miss_f":0,'
                    '"mailbox_write":0,"obuf_data":32,"obuf_low_byte":32}]}\n'
                )
                return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

            report = run_cpu_snapshot(
                compile_root="artifacts/compile",
                execute_dir="artifacts/execute/dhry",
                artifact_root="artifacts/snapshot",
                target_mcycle=0,
                target_post_reset_cycles=1002,
                trace_start_post_reset_cycles=875,
                trace_end_post_reset_cycles=1002,
                execute=True,
                repo_root=root,
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["snapshot"]["trace"][0]["pc_hex"], "0x400001bb")
        self.assertEqual(report["snapshot"]["trace"][0]["pc_d_hex"], "0x400001bd")
        self.assertEqual(report["snapshot"]["trace"][0]["ifu_ifc_fbwrite_dout_hex"], "0x060")
        self.assertEqual(report["snapshot"]["trace"][0]["tb_ifu_axi_rdata_hex"], "0x1122334455667788")
        self.assertEqual(report["snapshot"]["trace"][0]["tb_lmem_axi_rdata_hex"], "0x0102030405060708")
        self.assertEqual(report["snapshot"]["trace"][0]["ifu_fetch_addr_f_hex"], "0x40000280")
        self.assertEqual(report["snapshot"]["trace"][0]["ifu_pmp_addr_hex"], "0x40000288")
        self.assertEqual(report["snapshot"]["trace"][0]["ifu_mem_miss_f_hex"], "0x02000023")
        self.assertEqual(report["snapshot"]["trace"][0]["obuf_data_hex"], "0x0000000000000020")
        self.assertIn("+snapshot_trace_start_post_reset_cycles=875", report["commands"]["run"])
        self.assertIn("+snapshot_trace_end_post_reset_cycles=1002", report["commands"]["run"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_plan_supports_post_reset_cycle_target(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_cpu_snapshot import run_cpu_snapshot

        report = run_cpu_snapshot(
            target_mcycle=0,
            target_post_reset_cycles=5000,
            execute=False,
        )

        self.assertEqual(report["status"], "opt_in_required")
        self.assertEqual(report["target_mcycle"], 0)
        self.assertEqual(report["target_post_reset_cycles"], 5000)
        self.assertNotIn("+snapshot_mcycle=0", report["commands"]["run"])
        self.assertIn("+snapshot_post_reset_cycles=5000", report["commands"]["run"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_dry_run_outputs_json(self) -> None:
        result = self.run_python_tool(
            "src/tools/rtlmeter_veer_el2_cpu_snapshot.py",
            "--target-mcycle",
            "199999",
            check=True,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "opt_in_required")
        self.assertEqual(report["target_mcycle"], 199999)
        self.assert_no_local_absolute_paths(result.stdout)
