import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT


class VortexRuntimeSequenceHeaderTest(unittest.TestCase):
    def test_header_invokes_upload_dcr_kernel_export_and_release(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_runtime_sequence.h').as_posix()}"

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
              if (g_fake.dcr_count == 0) {{
                assert(addr == 1);
                assert(value == 0x80000000u);
              }}
              ++g_fake.dcr_count;
              return VORTEX_CUDA_SUCCESS;
            }}

            static VortexCuResult fake_kernel(void *user, VortexRuntimeBuffer *buffers, unsigned buffer_count) {{
              (void)user;
              assert(buffer_count == 7);
              assert(buffers[0].device_ptr == 1000);
              assert(buffers[6].device_ptr == 1006);
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
              VortexDcrWrite dcr_writes[2] = {{ {{1, 0x80000000u}}, {{2, 3}} }};
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
                &upload,
                buffers,
                7,
                dcr_writes,
                2,
                fake_dcr,
                0,
                fake_kernel,
                0,
                &export_driver,
              }};
              VortexRuntimeSequenceSummary summary;
              VortexCuResult result = vortex_run_runtime_sequence(&args, &summary);
              assert(result == VORTEX_CUDA_SUCCESS);
              assert(summary.upload.allocated_count == 7);
              assert(summary.upload.h2d_copy_count == 5);
              assert(summary.upload.d2h_init_count == 2);
              assert(summary.dcr_write_count == 2);
              assert(summary.dcr_applied_count == 2);
              assert(summary.dcr_reset_asserted == 1);
              assert(summary.kernel_launch_invoked == 1);
              assert(summary.observable_export_invoked == 1);
              assert(summary.observables.authority_passed == 1);
              assert(summary.buffers_released == 1);
              assert(g_fake.alloc_count == 7);
              assert(g_fake.h2d_count == 5);
              assert(g_fake.memset_count == 2);
              assert(g_fake.dcr_count == 2);
              assert(g_fake.kernel_count == 1);
              assert(g_fake.dtoh_count == 2);
              assert(g_fake.free_count == 7);
              return 0;
            }}
            """
        )
        self._compile_and_run(source, "vortex_runtime_sequence_test")

    def test_header_releases_buffers_on_dcr_failure(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_runtime_sequence.h').as_posix()}"

            static unsigned free_count = 0;

            static VortexCuResult fake_alloc(VortexCuDeviceptr *out, size_t bytes) {{
              (void)bytes;
              *out = 2000;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_h2d(VortexCuDeviceptr dst, const void *src, size_t bytes) {{
              (void)dst;
              (void)src;
              (void)bytes;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {{
              (void)dst;
              (void)value;
              (void)bytes;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fake_free(VortexCuDeviceptr ptr) {{
              assert(ptr == 2000);
              ++free_count;
              return VORTEX_CUDA_SUCCESS;
            }}
            static VortexCuResult fail_dcr(void *user, uint32_t addr, uint32_t value, int reset_asserted) {{
              (void)user;
              (void)addr;
              (void)value;
              assert(reset_asserted == 1);
              return 44;
            }}
            static VortexCuResult never_kernel(void *user, VortexRuntimeBuffer *buffers, unsigned buffer_count) {{
              (void)user;
              (void)buffers;
              (void)buffer_count;
              assert(0);
              return 0;
            }}
            static VortexCuResult never_dtoh(void *dst, VortexCuDeviceptr src, size_t bytes) {{
              (void)dst;
              (void)src;
              (void)bytes;
              assert(0);
              return 0;
            }}

            int main(void) {{
              uint8_t payload[8] = {{0}};
              VortexDcrWrite dcr_writes[1] = {{ {{1, 2}} }};
              VortexCudaUploadDriver upload = {{fake_alloc, fake_h2d, fake_memset, fake_free}};
              VortexObservableExportDriver export_driver = {{never_dtoh}};
              VortexRuntimeBuffer buffer = {{"vortex_dcr_write_table", payload, sizeof(payload), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}};
              VortexRuntimeSequenceArgs args = {{
                &upload,
                &buffer,
                1,
                dcr_writes,
                1,
                fail_dcr,
                0,
                never_kernel,
                0,
                &export_driver,
              }};
              VortexRuntimeSequenceSummary summary;
              VortexCuResult result = vortex_run_runtime_sequence(&args, &summary);
              assert(result == 44);
              assert(summary.failed_stage != 0);
              assert(strcmp(summary.failed_stage, "dcr_apply") == 0);
              assert(summary.failed_index == 0);
              assert(summary.failed_result == 44);
              assert(summary.dcr_applied_count == 0);
              assert(summary.kernel_launch_invoked == 0);
              assert(summary.observable_export_invoked == 0);
              assert(summary.buffers_released == 1);
              assert(free_count == 1);
              assert(buffer.device_ptr == 0);
              return 0;
            }}
            """
        )
        self._compile_and_run(source, "vortex_runtime_sequence_dcr_failure_test")

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
