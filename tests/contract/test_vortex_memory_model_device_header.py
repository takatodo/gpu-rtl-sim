import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT


class VortexMemoryModelDeviceHeaderTest(unittest.TestCase):
    def test_header_compiles_and_matches_reference_semantics(self) -> None:
        source = textwrap.dedent(
            f"""
            #include <assert.h>
            #include <stdint.h>
            #include <string.h>
            #include "{(REPO_ROOT / 'src/hybrid/vortex_memory_model_device.h').as_posix()}"

            int main(void) {{
              uint8_t init_payload[80];
              uint8_t post_payload[16];
              for (uint32_t i = 0; i < 80; ++i) init_payload[i] = (uint8_t)i;
              for (uint32_t i = 0; i < 16; ++i) post_payload[i] = (uint8_t)(0xa0 + i);

              VortexMemSegment init_segments[1] = {{ {{0x1000ull, 0, 80}} }};
              VortexMemSegment post_segments[1] = {{ {{0x1002ull, 0, 16}} }};
              VortexMemBlock blocks[2];
              memset(blocks, 0, sizeof(blocks));
              blocks[0].block_addr = 0x1000ull / VORTEX_MEM_BLOCK_SIZE;
              blocks[1].block_addr = 0x1040ull / VORTEX_MEM_BLOCK_SIZE;
              vortex_init_blocks_from_segments(blocks, 2, init_segments, 1, init_payload);
              assert(blocks[0].data[0] == 0);
              assert(blocks[0].data[63] == 63);
              assert(blocks[1].data[0] == 64);
              assert(blocks[1].data[15] == 79);

              uint8_t rdata[VORTEX_MEM_BLOCK_SIZE];
              uint8_t wdata[VORTEX_MEM_BLOCK_SIZE];
              memset(rdata, 0, sizeof(rdata));
              memset(wdata, 0, sizeof(wdata));
              wdata[2] = 0xa0;
              wdata[3] = 0xa1;
              wdata[7] = 0xa5;
              vortex_mem_access_device_helper(1, (1ull << 2) | (1ull << 3) | (1ull << 7),
                                              blocks[0].block_addr, wdata, rdata, blocks, 2, 0);
              assert(blocks[0].data[2] == 0xa0);
              assert(blocks[0].data[3] == 0xa1);
              assert(blocks[0].data[4] == 4);
              assert(blocks[0].data[7] == 0xa5);

              for (uint32_t i = 0; i < 16; ++i) {{
                wdata[2 + i] = post_payload[i];
              }}
              vortex_mem_access_device_helper(1, 0x3fffcull, blocks[0].block_addr,
                                              wdata, rdata, blocks, 2, 0);
              VortexPostCompareResult compare = vortex_post_compare_device_helper(
                  blocks, 2, post_segments, 1, post_payload);
              assert(compare.mismatch_count == 0);

              VortexIoCoutCapture io = {{0}};
              memset(wdata, 0, sizeof(wdata));
              wdata[1] = 'X';
              vortex_mem_access_device_helper(1, 1ull << 1, VORTEX_IO_COUT_ADDR / VORTEX_MEM_BLOCK_SIZE,
                                              wdata, rdata, blocks, 2, &io);
              assert(io.count == 1);
              assert(io.lanes[0] == 1);
              assert(io.chars[0] == 'X');
              assert(vortex_find_block(blocks, 2, VORTEX_IO_COUT_ADDR / VORTEX_MEM_BLOCK_SIZE) < 0);
              return 0;
            }}
            """
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "vortex_memory_model_device_header_test.c"
            binary_path = root / "vortex_memory_model_device_header_test"
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
