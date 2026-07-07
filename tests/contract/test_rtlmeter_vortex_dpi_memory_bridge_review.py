import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_dpi_memory_bridge_review import build_review  # noqa: E402


class RtlmeterVortexDpiMemoryBridgeReviewTest(HybridCliTestCase):
    def _write_sources(self, root: Path) -> None:
        design = root / "third_party" / "rtlmeter" / "designs" / "Vortex" / "src"
        dpi = design / "dpi"
        dpi.mkdir(parents=True, exist_ok=True)
        (design / "tb.sv").write_text(
            "\n".join(
                [
                    'import "DPI-C" function void mem_load(input string fileName);',
                    'import "DPI-C" function bit mem_check(input string fileName, input bit verbose);',
                    'import "DPI-C" function void mem_access(input bit req_rw, input longint unsigned req_byteen, input longint unsigned req_addr, output bit [511:0] rsp_data);',
                    'initial begin mem_load("init.bin"); if (mem_check("post.bin", 1\'b0)) $finish;',
                    'fd = $fopen("dcrs.bin", "r");',
                    'while (!busy) #10; while (busy) #10;',
                    'if (!mem_check("post.bin", 1\'b1)) $display("TEST FAILED");',
                    'else $display("TEST PASSED");',
                    "end",
                    "always @(negedge clk) begin",
                    "  if (mem_req_valid && mem_rsp_ready) mem_access(mem_req_rw, mem_req_byteen, mem_req_addr, mem_rsp_data);",
                    "end",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (dpi / "memory.cpp").write_text(
            "\n".join(
                [
                    "#include <cstdint>",
                    "#include <memory>",
                    "#include <sstream>",
                    "#include <unordered_map>",
                    "#define IO_COUT_ADDR 0x00000040",
                    "#define IO_COUT_SIZE 64",
                    "#define MEM_BLOCK_SIZE 64",
                    "class Ram final { std::unordered_map<uint64_t, std::unique_ptr<uint8_t[]>> pages; };",
                    "static Ram s_ram;",
                    "static std::stringstream s_print_bufs[IO_COUT_SIZE];",
                    'extern "C" void mem_load(const char* fileName) {}',
                    'extern "C" svBit mem_check(const char* fileName, svBit verbose) { s_ram.dump("check.bin"); return 1; }',
                    'extern "C" void mem_access(svBit req_rw, const uint64_t byteen, const uint64_t block_addr, const uint8_t* wdatap, uint8_t* rdatap) {',
                    "  const uint64_t addr = block_addr * MEM_BLOCK_SIZE;",
                    "  if (IO_COUT_ADDR <= addr && addr < IO_COUT_ADDR + IO_COUT_SIZE) printf(\"%s\", \"\");",
                    "}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_binary_input_summary(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_binary_input_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_binary_input_summary",
                    "status": "parsed",
                    "init_memory": {"segment_count": 9, "total_payload_bytes": 36864},
                    "post_memory": {"segment_count": 1, "total_payload_bytes": 48},
                    "dcr_writes": {"write_count": 9},
                }
            ),
            encoding="utf-8",
        )

    def _write_gpu_memory_model_plan(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_gpu_memory_model_plan.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_gpu_memory_model_plan",
                    "status": "abi_plan_ready",
                    "runtime_launchable": False,
                    "memory_model_abi": {
                        "minimum_static_input_bytes": 37224,
                        "init_block_count": 576,
                    },
                    "device_buffers": [
                        {"name": "vortex_init_segment_table"},
                        {"name": "vortex_post_compare_result"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _write_memory_model_reference(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_memory_model_reference.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_memory_model_reference",
                    "status": "reference_validated",
                    "initial_post_compare": {"match": False},
                    "post_replay_self_check": {"status": "passed"},
                    "io_cout_self_check": {"status": "passed"},
                    "gpu_bridge_implication": {"reference_semantics_ready": True},
                }
            ),
            encoding="utf-8",
        )

    def _write_device_helper_header(self, root: Path) -> None:
        path = root / "src" / "hybrid" / "vortex_memory_model_device.h"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "#define VORTEX_MEM_BLOCK_SIZE 64u",
                    "#define VORTEX_IO_COUT_ADDR 0x40ull",
                    "typedef struct { /* ABI record type: u64_addr_u64_payload_offset_u64_size_bytes. */ } VortexMemSegment;",
                    "typedef struct {} VortexMemBlock;",
                    "typedef struct {} VortexIoCoutCapture;",
                    "void vortex_init_blocks_from_segments(void);",
                    "void vortex_mem_access_device_helper(void);",
                    "void vortex_post_compare_device_helper(void);",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_device_buffer_materialization(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_device_buffer_materialize.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_device_buffer_materialize",
                    "status": "device_buffers_materialized",
                    "totals": {
                        "host_to_device_bytes": 37224,
                        "device_to_host_initial_bytes": 88,
                    },
                    "device_buffers": [
                        {"name": "vortex_init_segment_table"},
                        {"name": "vortex_post_compare_result_initial"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _write_dcr_schedule(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_dcr_schedule.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_dcr_schedule",
                    "status": "dcr_schedule_materialized",
                    "write_count": 9,
                    "device_schedule": {
                        "bytes": 72,
                    },
                    "schedule_semantics": {
                        "reset_asserted_during_all_dcr_writes": True,
                    },
                }
            ),
            encoding="utf-8",
        )

    def _write_runtime_upload_header(self, root: Path) -> None:
        path = root / "src" / "hybrid" / "vortex_runtime_upload.h"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "typedef struct {} VortexCudaUploadDriver;",
                    "typedef struct {} VortexRuntimeBuffer;",
                    "typedef struct {} VortexRuntimeUploadSummary;",
                    "enum { VORTEX_BUFFER_HOST_TO_DEVICE = 1, VORTEX_BUFFER_DEVICE_TO_HOST = 2 };",
                    "void vortex_upload_runtime_buffers(void);",
                    "void vortex_release_runtime_buffers(void);",
                    "void cuMemcpyHtoD(void);",
                    "void cuMemsetD8(void);",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_observable_export_header(self, root: Path) -> None:
        path = root / "src" / "hybrid" / "vortex_observable_export.h"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "typedef struct {} VortexObservableExportDriver;",
                    "typedef struct {} VortexObservableDeviceBuffers;",
                    "typedef struct { int memory_post_condition_passed; int stdout_test_passed_observed; int authority_passed; const char *authority_source; int post_compare_exported; int stdout_exported; } VortexObservableExportSummary;",
                    "void vortex_export_observables(void);",
                    "void vortex_stdout_contains_test_passed(void);",
                    "void vortex_observable_authority_update(void);",
                    "void cuMemcpyDtoH(void);",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_runtime_sequence_header(self, root: Path) -> None:
        path = root / "src" / "hybrid" / "vortex_runtime_sequence.h"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "typedef struct {} VortexRuntimeSequenceArgs;",
                    "typedef struct { int dcr_reset_asserted; int kernel_launch_invoked; int observable_export_invoked; } VortexRuntimeSequenceSummary;",
                    "typedef struct {} VortexDcrWrite;",
                    "typedef int (*VortexDcrApplyFn)(void);",
                    "typedef int (*VortexKernelLaunchFn)(void);",
                    "void vortex_run_runtime_sequence(void);",
                    "void vortex_upload_runtime_buffers(void);",
                    "void vortex_export_observables(void);",
                    "void vortex_release_runtime_buffers(void);",
                    "void vortex_observable_buffers_from_runtime_buffers(void);",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_runtime_invocation_plan(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_runtime_invocation_plan.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_runtime_invocation_plan",
                    "status": "runtime_sequence_invocation_plan_ready_not_invoked",
                    "plan_ready": True,
                    "entrypoint": "vortex_run_runtime_sequence",
                    "required_order": [
                        "vortex_upload_runtime_buffers",
                        "apply_ordered_dcr_writes_while_reset_asserted",
                        "vortex_kernel_launch_callback",
                        "vortex_export_observables",
                        "vortex_release_runtime_buffers",
                    ],
                    "runtime_launchable": False,
                }
            ),
            encoding="utf-8",
        )

    def _write_lowered_tb_invocation_smoke(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_lowered_tb_invocation_smoke.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_lowered_tb_invocation_smoke",
                    "status": "lowered_tb_invocation_smoke_ready_not_integrated",
                    "smoke_ready": True,
                    "runtime_launchable": False,
                }
            ),
            encoding="utf-8",
        )

    def _write_materialized_runtime_invocation_smoke(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_materialized_runtime_invocation_smoke.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_materialized_runtime_invocation_smoke",
                    "status": "materialized_runtime_invocation_smoke_ready_not_integrated",
                    "smoke_ready": True,
                    "host_to_device_bytes": 37224,
                    "device_to_host_initial_bytes": 88,
                    "dcr_write_count": 9,
                    "runtime_launchable": False,
                }
            ),
            encoding="utf-8",
        )

    def _write_generated_lowered_tb_invocation_smoke(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_generated_lowered_tb_invocation_smoke",
                    "status": "generated_lowered_tb_invocation_smoke_passed",
                    "generated_lowered_tb_invocation_smoke_passed": True,
                    "host_to_device_bytes": 37224,
                    "device_to_host_initial_bytes": 88,
                    "dcr_write_count": 9,
                    "runtime_launchable": False,
                }
            ),
            encoding="utf-8",
        )

    def _write_lowered_tb_memory_helper_integration_smoke(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke",
                    "status": "lowered_tb_memory_helper_integration_smoke_passed",
                    "lowered_tb_memory_helper_integration_smoke_passed": True,
                    "host_to_device_bytes": 37224,
                    "device_to_host_initial_bytes": 88,
                    "init_segment_count": 9,
                    "post_segment_count": 1,
                    "runtime_launchable": False,
                }
            ),
            encoding="utf-8",
        )

    def test_review_classifies_vortex_dpi_memory_bridge_as_reviewed_but_not_implemented(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)

            summary = build_review(root)

        self.assertEqual(summary["status"], "reviewed_blocked_on_gpu_bridge_implementation")
        self.assertTrue(summary["reviewed_bridge_boundary"])
        self.assertFalse(summary["runtime_launchable"])
        self.assertEqual(summary["memory_model"]["block_size_bytes"], 64)
        self.assertEqual(summary["memory_model"]["io_cout_addr"], 0x40)
        self.assertIn("gpu_memory_model_for_64B_block_reads_writes_and_byteen", summary["missing_prerequisites"])
        self.assertIn("gpu_post_bin_memory_compare_or_export", summary["missing_prerequisites"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_review_includes_binary_input_summary_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_binary_input_summary(root)

            summary = build_review(root)

        self.assertEqual(summary["binary_input_summary"]["status"], "parsed")
        self.assertEqual(summary["binary_input_summary"]["init_segment_count"], 9)
        self.assertEqual(summary["binary_input_summary"]["post_total_payload_bytes"], 48)
        self.assertEqual(summary["binary_input_summary"]["dcr_write_count"], 9)

    def test_review_includes_gpu_memory_model_plan_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_gpu_memory_model_plan(root)

            summary = build_review(root)

        self.assertEqual(summary["gpu_memory_model_plan"]["status"], "abi_plan_ready")
        self.assertEqual(summary["gpu_memory_model_plan"]["minimum_static_input_bytes"], 37224)
        self.assertEqual(summary["gpu_memory_model_plan"]["init_block_count"], 576)
        self.assertEqual(summary["gpu_memory_model_plan"]["device_buffer_count"], 2)

    def test_review_includes_memory_model_reference_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)

            summary = build_review(root)

        self.assertEqual(summary["memory_model_reference"]["status"], "reference_validated")
        self.assertFalse(summary["memory_model_reference"]["initial_post_match"])
        self.assertEqual(summary["memory_model_reference"]["post_replay_status"], "passed")
        self.assertEqual(summary["memory_model_reference"]["io_cout_status"], "passed")
        self.assertTrue(summary["memory_model_reference"]["reference_semantics_ready"])
        self.assertEqual(
            summary["recommended_next"],
            "implement_vortex_device_memory_helper_from_reference_model_before_launch_template_timing",
        )

    def test_review_recognizes_device_helper_header_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)

            summary = build_review(root)

        self.assertTrue(summary["device_helper_ready_for_integration"])
        self.assertNotIn("gpu_memory_model_for_64B_block_reads_writes_and_byteen", summary["missing_prerequisites"])
        self.assertIn("lowered_tb_mem_access_device_helper_integration", summary["missing_prerequisites"])
        self.assertIn("gpu_post_compare_result_export", summary["missing_prerequisites"])
        self.assertEqual(
            summary["recommended_next"],
            "integrate_vortex_device_memory_helper_with_lowered_tb_and_observable_export",
        )

    def test_review_consumes_device_buffer_materialization_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)

            summary = build_review(root)

        self.assertTrue(summary["device_buffers_materialized_for_upload"])
        self.assertEqual(summary["device_buffer_materialization"]["status"], "device_buffers_materialized")
        self.assertEqual(summary["device_buffer_materialization"]["host_to_device_bytes"], 37224)
        self.assertNotIn("device_memory_buffers_materialized_for_runtime_upload", summary["missing_prerequisites"])
        self.assertIn("device_memory_buffers_uploaded_to_runtime", summary["missing_prerequisites"])

    def test_review_consumes_dcr_schedule_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_dcr_schedule(root)

            summary = build_review(root)

        self.assertTrue(summary["dcr_schedule_materialized"])
        self.assertEqual(summary["dcr_schedule"]["status"], "dcr_schedule_materialized")
        self.assertEqual(summary["dcr_schedule"]["write_count"], 9)
        self.assertEqual(summary["dcr_schedule"]["device_schedule_bytes"], 72)
        self.assertTrue(summary["dcr_schedule"]["reset_asserted_during_all_dcr_writes"])
        self.assertNotIn("dcrs_bin_gpu_schedule_or_host_phase_bridge", summary["missing_prerequisites"])
        self.assertIn(
            "runtime_execution_applies_vortex_dcr_schedule_while_reset_asserted",
            summary["missing_prerequisites"],
        )

    def test_review_recognizes_runtime_upload_helper_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_runtime_upload_header(root)

            summary = build_review(root)

        self.assertTrue(summary["runtime_upload_helper_ready"])
        self.assertEqual(summary["runtime_upload_header"], "src/hybrid/vortex_runtime_upload.h")
        self.assertNotIn("device_memory_buffers_uploaded_to_runtime", summary["missing_prerequisites"])
        self.assertIn("runtime_execution_invokes_vortex_upload_runtime_buffers", summary["missing_prerequisites"])

    def test_review_recognizes_observable_export_helper_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_runtime_upload_header(root)
            self._write_observable_export_header(root)

            summary = build_review(root)

        self.assertTrue(summary["observable_export_helper_ready"])
        self.assertEqual(summary["observable_export_header"], "src/hybrid/vortex_observable_export.h")
        self.assertNotIn("gpu_post_compare_result_export", summary["missing_prerequisites"])
        self.assertIn("runtime_execution_invokes_vortex_export_observables", summary["missing_prerequisites"])
        self.assertNotIn("gpu_stdout_or_post_compare_observable_export", summary["missing_prerequisites"])
        self.assertIn("runtime_execution_reports_vortex_observable_authority", summary["missing_prerequisites"])
        self.assertTrue(summary["observable_export_features"]["vortex_stdout_contains_test_passed"])
        self.assertTrue(summary["observable_export_features"]["vortex_observable_authority_update"])
        self.assertTrue(summary["observable_export_features"]["authority_passed"])

    def test_review_recognizes_runtime_sequence_helper_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_dcr_schedule(root)
            self._write_runtime_upload_header(root)
            self._write_observable_export_header(root)
            self._write_runtime_sequence_header(root)

            summary = build_review(root)

        self.assertTrue(summary["runtime_sequence_helper_ready"])
        self.assertEqual(summary["runtime_sequence_header"], "src/hybrid/vortex_runtime_sequence.h")
        self.assertTrue(summary["runtime_sequence"]["helper_ready"])
        self.assertTrue(summary["runtime_sequence"]["invokes_upload_helper"])
        self.assertTrue(summary["runtime_sequence"]["invokes_observable_export_helper"])
        self.assertTrue(summary["runtime_sequence"]["applies_dcr_with_reset_asserted_summary"])
        self.assertNotIn("runtime_execution_invokes_vortex_upload_runtime_buffers", summary["missing_prerequisites"])
        self.assertNotIn("runtime_execution_invokes_vortex_export_observables", summary["missing_prerequisites"])
        self.assertNotIn(
            "runtime_execution_applies_vortex_dcr_schedule_while_reset_asserted",
            summary["missing_prerequisites"],
        )
        self.assertIn("runtime_execution_invokes_vortex_runtime_sequence_helper", summary["missing_prerequisites"])

    def test_review_consumes_runtime_invocation_plan_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_dcr_schedule(root)
            self._write_runtime_upload_header(root)
            self._write_observable_export_header(root)
            self._write_runtime_sequence_header(root)
            self._write_runtime_invocation_plan(root)

            summary = build_review(root)

        self.assertTrue(summary["runtime_invocation_plan_ready"])
        self.assertEqual(
            summary["runtime_invocation_plan"]["status"],
            "runtime_sequence_invocation_plan_ready_not_invoked",
        )
        self.assertNotIn("runtime_execution_invokes_vortex_runtime_sequence_helper", summary["missing_prerequisites"])
        self.assertIn("lowered_tb_invokes_vortex_run_runtime_sequence", summary["missing_prerequisites"])

    def test_review_consumes_lowered_tb_invocation_smoke_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_dcr_schedule(root)
            self._write_runtime_upload_header(root)
            self._write_observable_export_header(root)
            self._write_runtime_sequence_header(root)
            self._write_runtime_invocation_plan(root)
            self._write_lowered_tb_invocation_smoke(root)

            summary = build_review(root)

        self.assertTrue(summary["lowered_tb_invocation_smoke_ready"])
        self.assertEqual(
            summary["lowered_tb_invocation_smoke"]["status"],
            "lowered_tb_invocation_smoke_ready_not_integrated",
        )
        self.assertNotIn("lowered_tb_invokes_vortex_run_runtime_sequence", summary["missing_prerequisites"])
        self.assertIn(
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            summary["missing_prerequisites"],
        )

    def test_review_consumes_materialized_runtime_invocation_smoke_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_dcr_schedule(root)
            self._write_runtime_upload_header(root)
            self._write_observable_export_header(root)
            self._write_runtime_sequence_header(root)
            self._write_runtime_invocation_plan(root)
            self._write_lowered_tb_invocation_smoke(root)
            self._write_materialized_runtime_invocation_smoke(root)

            summary = build_review(root)

        self.assertTrue(summary["materialized_runtime_invocation_smoke_ready"])
        self.assertEqual(
            summary["materialized_runtime_invocation_smoke"]["status"],
            "materialized_runtime_invocation_smoke_ready_not_integrated",
        )
        self.assertEqual(summary["materialized_runtime_invocation_smoke"]["host_to_device_bytes"], 37224)
        self.assertEqual(
            summary["recommended_next"],
            "generate_lowered_tb_call_to_vortex_lowered_tb_invoke_runtime_sequence",
        )
        self.assertIn(
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            summary["missing_prerequisites"],
        )

    def test_review_consumes_generated_lowered_tb_invocation_smoke_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_dcr_schedule(root)
            self._write_runtime_upload_header(root)
            self._write_observable_export_header(root)
            self._write_runtime_sequence_header(root)
            self._write_runtime_invocation_plan(root)
            self._write_lowered_tb_invocation_smoke(root)
            self._write_materialized_runtime_invocation_smoke(root)
            self._write_generated_lowered_tb_invocation_smoke(root)

            summary = build_review(root)

        self.assertTrue(summary["generated_lowered_tb_invocation_smoke_passed"])
        self.assertEqual(
            summary["generated_lowered_tb_invocation_smoke"]["status"],
            "generated_lowered_tb_invocation_smoke_passed",
        )
        self.assertNotIn(
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            summary["missing_prerequisites"],
        )
        self.assertIn(
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            summary["missing_prerequisites"],
        )
        self.assertEqual(
            summary["recommended_next"],
            "run_lowered_tb_memory_helper_integration_smoke",
        )

    def test_review_consumes_lowered_tb_memory_helper_integration_smoke_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            self._write_memory_model_reference(root)
            self._write_device_helper_header(root)
            self._write_device_buffer_materialization(root)
            self._write_dcr_schedule(root)
            self._write_runtime_upload_header(root)
            self._write_observable_export_header(root)
            self._write_runtime_sequence_header(root)
            self._write_runtime_invocation_plan(root)
            self._write_lowered_tb_invocation_smoke(root)
            self._write_materialized_runtime_invocation_smoke(root)
            self._write_generated_lowered_tb_invocation_smoke(root)
            self._write_lowered_tb_memory_helper_integration_smoke(root)

            summary = build_review(root)

        self.assertTrue(summary["lowered_tb_memory_helper_integration_smoke_passed"])
        self.assertEqual(
            summary["lowered_tb_memory_helper_integration_smoke"]["status"],
            "lowered_tb_memory_helper_integration_smoke_passed",
        )
        self.assertNotIn("lowered_tb_mem_access_device_helper_integration", summary["missing_prerequisites"])
        self.assertIn(
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
            summary["missing_prerequisites"],
        )
        self.assertEqual(
            summary["recommended_next"],
            "connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence",
        )

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_sources(root)
            out = root / "reports" / "vortex_bridge.json"
            out.parent.mkdir()

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_dpi_memory_bridge_review.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_dpi_memory_bridge_review")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
