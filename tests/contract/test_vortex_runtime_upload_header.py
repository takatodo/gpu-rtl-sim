import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT


class VortexRuntimeUploadHeaderTest(unittest.TestCase):
    def test_header_uploads_buffers_with_fake_cuda_driver(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_runtime_upload.h').as_posix()}"

            typedef struct {{
              unsigned alloc_count;
              unsigned h2d_count;
              unsigned memset_count;
              unsigned free_count;
              size_t h2d_bytes;
              size_t memset_bytes;
              VortexCuDeviceptr next_ptr;
            }} FakeCuda;

            static FakeCuda g_fake;

            static VortexCuResult fake_alloc(VortexCuDeviceptr *out, size_t bytes) {{
              assert(bytes > 0);
              *out = g_fake.next_ptr++;
              ++g_fake.alloc_count;
              return VORTEX_CUDA_SUCCESS;
            }}

            static VortexCuResult fake_h2d(VortexCuDeviceptr dst, const void *src, size_t bytes) {{
              assert(dst != 0);
              assert(src != 0);
              g_fake.h2d_bytes += bytes;
              ++g_fake.h2d_count;
              return VORTEX_CUDA_SUCCESS;
            }}

            static VortexCuResult fake_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {{
              assert(dst != 0);
              assert(value == 0);
              g_fake.memset_bytes += bytes;
              ++g_fake.memset_count;
              return VORTEX_CUDA_SUCCESS;
            }}

            static VortexCuResult fake_free(VortexCuDeviceptr ptr) {{
              assert(ptr != 0);
              ++g_fake.free_count;
              return VORTEX_CUDA_SUCCESS;
            }}

            int main(void) {{
              uint8_t init_table[216] = {{0}};
              uint8_t init_payload[36864] = {{0}};
              uint8_t post_table[24] = {{0}};
              uint8_t post_payload[48] = {{0}};
              uint8_t dcr_table[72] = {{0}};
              memset(&g_fake, 0, sizeof(g_fake));
              g_fake.next_ptr = 1000;
              VortexCudaUploadDriver driver = {{fake_alloc, fake_h2d, fake_memset, fake_free}};
              VortexRuntimeBuffer buffers[7] = {{
                {{"vortex_init_segment_table", init_table, sizeof(init_table), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_init_payload", init_payload, sizeof(init_payload), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_post_segment_table", post_table, sizeof(post_table), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_post_expected_payload", post_payload, sizeof(post_payload), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_dcr_write_table", dcr_table, sizeof(dcr_table), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}},
                {{"vortex_stdout_ring", 0, 64, VORTEX_BUFFER_DEVICE_TO_HOST, 0, 0}},
                {{"vortex_post_compare_result", 0, 4, VORTEX_BUFFER_DEVICE_TO_HOST, 0, 0}},
              }};
              VortexRuntimeUploadSummary summary;
              VortexCuResult result = vortex_upload_runtime_buffers(&driver, buffers, 7, &summary);
              assert(result == VORTEX_CUDA_SUCCESS);
              assert(summary.allocated_count == 7);
              assert(summary.h2d_copy_count == 5);
              assert(summary.d2h_init_count == 2);
              assert(summary.h2d_bytes == 37224);
              assert(summary.d2h_initial_bytes == 68);
              assert(g_fake.alloc_count == 7);
              assert(g_fake.h2d_count == 5);
              assert(g_fake.memset_count == 2);
              assert(g_fake.h2d_bytes == 37224);
              assert(g_fake.memset_bytes == 68);
              assert(buffers[0].device_ptr == 1000);
              assert(buffers[6].device_ptr == 1006);
              vortex_release_runtime_buffers(&driver, buffers, 7);
              assert(g_fake.free_count == 7);
              for (unsigned i = 0; i < 7; ++i) assert(buffers[i].device_ptr == 0);
              return 0;
            }}
            """
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "vortex_runtime_upload_header_test.c"
            binary_path = root / "vortex_runtime_upload_header_test"
            source_path.write_text(source, encoding="utf-8")
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", source_path.as_posix(), "-o", binary_path.as_posix()],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )
            subprocess.run([binary_path.as_posix()], check=True, text=True, capture_output=True)

    def test_header_cleans_up_allocations_on_copy_failure(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_runtime_upload.h').as_posix()}"

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
              return 77;
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

            int main(void) {{
              uint8_t payload[4] = {{1, 2, 3, 4}};
              VortexCudaUploadDriver driver = {{fake_alloc, fake_h2d, fake_memset, fake_free}};
              VortexRuntimeBuffer buffer = {{"payload", payload, sizeof(payload), VORTEX_BUFFER_HOST_TO_DEVICE, 0, 0}};
              VortexRuntimeUploadSummary summary;
              VortexCuResult result = vortex_upload_runtime_buffers(&driver, &buffer, 1, &summary);
              assert(result == 77);
              assert(summary.failed_index == 0);
              assert(strcmp(summary.failed_op, "cuMemcpyHtoD") == 0);
              assert(summary.failed_result == 77);
              assert(free_count == 1);
              assert(buffer.device_ptr == 0);
              return 0;
            }}
            """
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "vortex_runtime_upload_failure_test.c"
            binary_path = root / "vortex_runtime_upload_failure_test"
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
