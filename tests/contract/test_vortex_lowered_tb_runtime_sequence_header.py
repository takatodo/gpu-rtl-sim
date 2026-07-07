import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT


class VortexLoweredTbRuntimeSequenceHeaderTest(unittest.TestCase):
    def test_header_invokes_runtime_sequence_and_reports_authority(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_lowered_tb_runtime_sequence.h').as_posix()}"

            typedef struct {{
              unsigned alloc_count;
              unsigned h2d_count;
              unsigned memset_count;
              unsigned free_count;
              unsigned dcr_count;
              unsigned kernel_count;
              unsigned dtoh_count;
              VortexCuDeviceptr next_ptr;
            }} FakeRuntime;

            static FakeRuntime g_fake;
            static VortexPostCompareResult g_post;
            static unsigned char g_stdout[64];

            static VortexCuResult fake_alloc(VortexCuDeviceptr *out, size_t bytes) {{
              assert(bytes > 0);
              *out = g_fake.next_ptr++;
              ++g_fake.alloc_count;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_h2d(VortexCuDeviceptr dst, const void *src, size_t bytes) {{
              assert(dst != 0);
              assert(src != 0);
              assert(bytes > 0);
              ++g_fake.h2d_count;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {{
              assert(dst != 0);
              assert(value == 0);
              assert(bytes > 0);
              ++g_fake.memset_count;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_free(VortexCuDeviceptr ptr) {{
              assert(ptr != 0);
              ++g_fake.free_count;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_dcr(void *user, uint32_t addr, uint32_t value, int reset_asserted) {{
              (void)user;
              assert(reset_asserted == 1);
              assert(addr == 1 || addr == 2);
              if (addr == 1) assert(value == 0x80000000u);
              ++g_fake.dcr_count;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_kernel(void *user, VortexRuntimeBuffer *buffers, unsigned buffer_count) {{
              (void)user;
              assert(buffer_count == 7);
              assert(buffers[0].device_ptr == 1000);
              ++g_fake.kernel_count;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_dtoh(void *dst, VortexCuDeviceptr src, size_t bytes) {{
              ++g_fake.dtoh_count;
              if (src == 1006) {{
                assert(bytes == sizeof(VortexPostCompareResult));
                memcpy(dst, &g_post, bytes);
                return VORTEX_CUDA_SUCCESS;
              }}
              if (src == 1005) {{
                assert(bytes == 64);
                memcpy(dst, g_stdout, bytes);
                return VORTEX_CUDA_SUCCESS;
              }}
              return 99;
            }}

            int main(void) {{
              uint8_t init_table[216] = {{0}};
              uint8_t init_payload[36864] = {{0}};
              uint8_t post_table[24] = {{0}};
              uint8_t post_payload[48] = {{0}};
              VortexDcrWrite dcr_writes[2] = {{ {{1, 0x80000000u}}, {{2, 0}} }};
              memset(&g_fake, 0, sizeof(g_fake));
              memset(&g_post, 0, sizeof(g_post));
              memset(g_stdout, 0, sizeof(g_stdout));
              memcpy(g_stdout, "TEST PASSED\\n", 12);
              g_fake.next_ptr = 1000;

              VortexCudaUploadDriver upload = {{fake_alloc, fake_h2d, fake_memset, fake_free}};
              VortexObservableExportDriver export_driver = {{fake_dtoh}};
              VortexRuntimeBuffer buffers[7] = {{
                {{"vortex_init_segment_table", init_table, sizeof(init_table), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_init_payload", init_payload, sizeof(init_payload), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_post_segment_table", post_table, sizeof(post_table), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_post_expected_payload", post_payload, sizeof(post_payload), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_dcr_write_table", dcr_writes, sizeof(dcr_writes), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_stdout_ring_initial", 0, 64, VORTEX_BUFFER_DEVICE_TO_HOST, 0, 0}},
                {{"vortex_post_compare_result_initial", 0, sizeof(VortexPostCompareResult), VORTEX_BUFFER_DEVICE_TO_HOST, 0, 0}},
              }};
              VortexRuntimeSequenceArgs args = {{
                &upload, buffers, 7, dcr_writes, 2, fake_dcr, 0, fake_kernel, 0, &export_driver
              }};
              VortexRuntimeSequenceSummary sequence_summary;
              VortexLoweredTbRuntimeSummary tb_summary;
              VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(
                  &args, &sequence_summary, &tb_summary);
              assert(result == VORTEX_CUDA_SUCCESS);
              assert(tb_summary.runtime_sequence_called == 1);
              assert(tb_summary.runtime_sequence_passed == 1);
              assert(tb_summary.authority_report_ready == 1);
              assert(tb_summary.authority_passed == 1);
              assert(strcmp(tb_summary.authority_source, "memory_post_condition_and_stdout_TEST_PASSED") == 0);
              assert(sequence_summary.dcr_applied_count == 2);
              assert(sequence_summary.kernel_launch_invoked == 1);
              assert(sequence_summary.observable_export_invoked == 1);
              assert(g_fake.free_count == 7);
              return 0;
            }}
            """
        )
        self._compile_and_run(source, "vortex_lowered_tb_runtime_sequence_test")

    def test_header_reports_runtime_sequence_failure(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_lowered_tb_runtime_sequence.h').as_posix()}"

            int main(void) {{
              VortexRuntimeSequenceSummary sequence_summary;
              VortexLoweredTbRuntimeSummary tb_summary;
              VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(0, &sequence_summary, &tb_summary);
              assert(result == 1);
              assert(tb_summary.runtime_sequence_called == 1);
              assert(tb_summary.runtime_sequence_passed == 0);
              assert(tb_summary.authority_report_ready == 0);
              assert(strcmp(tb_summary.failed_stage, "invalid_runtime_sequence_args") == 0);
              assert(tb_summary.failed_result == 1);
              return 0;
            }}
            """
        )
        self._compile_and_run(source, "vortex_lowered_tb_runtime_sequence_failure_test")

    def _compile_and_run(self, source: str, name: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / f"{name}.c"
            binary_path = root / name
            source_path.write_text(source, encoding="utf-8")
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", source_path.as_posix(), "-o", binary_path.as_posix()],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            subprocess.run([binary_path.as_posix()], check=True, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
