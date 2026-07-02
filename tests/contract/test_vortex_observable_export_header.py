import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT


class VortexObservableExportHeaderTest(unittest.TestCase):
    def test_header_exports_post_compare_and_stdout_bytes(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_observable_export.h').as_posix()}"

            static VortexPostCompareResult g_post;
            static unsigned char g_stdout[64];
            static unsigned dtoh_count = 0;

            static VortexCuResult fake_dtoh(void *dst, VortexCuDeviceptr src, size_t bytes) {{
              ++dtoh_count;
              if (src == 100) {{
                assert(bytes == sizeof(VortexPostCompareResult));
                memcpy(dst, &g_post, bytes);
                return VORTEX_CUDA_SUCCESS;
              }}
              if (src == 200) {{
                assert(bytes == 64);
                memcpy(dst, g_stdout, bytes);
                return VORTEX_CUDA_SUCCESS;
              }}
              return 99;
            }}

            int main(void) {{
              memset(&g_post, 0, sizeof(g_post));
              memcpy(g_stdout, "TEST PASSED\\n", 12);
              VortexObservableExportDriver driver = {{fake_dtoh}};
              VortexObservableDeviceBuffers buffers = {{100, 200, 64}};
              VortexObservableExportSummary summary;
              VortexCuResult result = vortex_export_observables(&driver, &buffers, &summary);
              assert(result == VORTEX_CUDA_SUCCESS);
              assert(dtoh_count == 2);
              assert(summary.post_compare_exported == 1);
              assert(summary.memory_post_condition_passed == 1);
              assert(summary.stdout_exported == 1);
              assert(summary.stdout_bytes_copied == 64);
              assert(summary.stdout_test_passed_observed == 1);
              assert(summary.authority_passed == 1);
              assert(strcmp(summary.authority_source, "memory_post_condition_and_stdout_TEST_PASSED") == 0);
              assert(memcmp(summary.stdout_bytes, "TEST PASSED\\n", 12) == 0);
              return 0;
            }}
            """
        )
        self._compile_and_run(source, "vortex_observable_export_test")

    def test_header_reports_post_compare_mismatch_and_copy_failure(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_observable_export.h').as_posix()}"

            static VortexPostCompareResult g_post;
            static VortexCuResult fake_dtoh(void *dst, VortexCuDeviceptr src, size_t bytes) {{
              if (src == 100) {{
                assert(bytes == sizeof(VortexPostCompareResult));
                memcpy(dst, &g_post, bytes);
                return VORTEX_CUDA_SUCCESS;
              }}
              return 55;
            }}

            int main(void) {{
              memset(&g_post, 0, sizeof(g_post));
              g_post.mismatch_count = 3;
              g_post.first_mismatch_addr = 0x1000;
              g_post.first_expected = 0xaa;
              g_post.first_actual = 0xbb;
              VortexObservableExportDriver driver = {{fake_dtoh}};
              VortexObservableDeviceBuffers buffers = {{100, 0, 0}};
              VortexObservableExportSummary summary;
              VortexCuResult result = vortex_export_observables(&driver, &buffers, &summary);
              assert(result == VORTEX_CUDA_SUCCESS);
              assert(summary.post_compare_exported == 1);
              assert(summary.memory_post_condition_passed == 0);
              assert(summary.stdout_test_passed_observed == 0);
              assert(summary.authority_passed == 0);
              assert(summary.authority_source == 0);
              assert(summary.post_compare.mismatch_count == 3);
              assert(summary.stdout_exported == 0);

              buffers.stdout_ring = 999;
              buffers.stdout_ring_bytes = 64;
              result = vortex_export_observables(&driver, &buffers, &summary);
              assert(result == 55);
              assert(summary.failed_copy_index == 1);
              assert(strcmp(summary.failed_op, "cuMemcpyDtoH_stdout_ring") == 0);
              assert(summary.failed_result == 55);
              return 0;
            }}
            """
        )
        self._compile_and_run(source, "vortex_observable_export_failure_test")

    def test_header_accepts_stdout_test_passed_as_observable_authority(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_observable_export.h').as_posix()}"

            int main(void) {{
              VortexObservableExportSummary summary;
              vortex_observable_export_summary_clear(&summary);
              summary.post_compare_exported = 1;
              summary.memory_post_condition_passed = 0;
              summary.stdout_exported = 1;
              memcpy(summary.stdout_bytes, "prefix TEST PASSED suffix", 25);
              summary.stdout_bytes_copied = 25;
              vortex_observable_authority_update(&summary);
              assert(vortex_stdout_contains_test_passed(summary.stdout_bytes, summary.stdout_bytes_copied) == 1);
              assert(summary.stdout_test_passed_observed == 1);
              assert(summary.authority_passed == 1);
              assert(strcmp(summary.authority_source, "stdout_TEST_PASSED") == 0);

              summary.stdout_bytes[12] = 'F';
              vortex_observable_authority_update(&summary);
              assert(summary.stdout_test_passed_observed == 0);
              assert(summary.authority_passed == 0);
              assert(summary.authority_source == 0);
              return 0;
            }}
            """
        )
        self._compile_and_run(source, "vortex_observable_export_authority_test")

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
