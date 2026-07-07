#ifndef GPU_TOGGLE_VORTEX_MEMORY_MODEL_DEVICE_H
#define GPU_TOGGLE_VORTEX_MEMORY_MODEL_DEVICE_H

#include <stddef.h>
#include <stdint.h>

#ifndef VORTEX_MEM_DEVICE_INLINE
#if defined(__CUDACC__)
#define VORTEX_MEM_DEVICE_INLINE __host__ __device__ static inline
#else
#define VORTEX_MEM_DEVICE_INLINE static inline
#endif
#endif

#define VORTEX_MEM_BLOCK_SIZE 64u
#define VORTEX_IO_COUT_ADDR 0x40ull
#define VORTEX_IO_COUT_SIZE 64u

typedef struct {
  /* ABI record type: u64_addr_u64_payload_offset_u64_size_bytes. */
  uint64_t addr;
  uint64_t payload_offset;
  uint64_t size_bytes;
} VortexMemSegment;

typedef struct {
  uint64_t block_addr;
  uint8_t data[VORTEX_MEM_BLOCK_SIZE];
} VortexMemBlock;

typedef struct {
  uint32_t mismatch_count;
  uint64_t first_mismatch_addr;
  uint8_t first_expected;
  uint8_t first_actual;
} VortexPostCompareResult;

typedef struct {
  uint32_t count;
  uint8_t lanes[VORTEX_IO_COUT_SIZE];
  uint8_t chars[VORTEX_IO_COUT_SIZE];
} VortexIoCoutCapture;

VORTEX_MEM_DEVICE_INLINE uint8_t vortex_uninitialized_byte(uint64_t addr) {
  return (uint8_t)((0xbaadf00dull >> ((addr & 0x3ull) * 8ull)) & 0xffull);
}

VORTEX_MEM_DEVICE_INLINE int vortex_addr_in_segment(uint64_t addr, const VortexMemSegment *segment) {
  return addr >= segment->addr && addr < (segment->addr + segment->size_bytes);
}

VORTEX_MEM_DEVICE_INLINE uint8_t vortex_payload_read_byte(const VortexMemSegment *segments,
                                                          uint32_t segment_count,
                                                          const uint8_t *payload,
                                                          uint64_t addr) {
  for (uint32_t i = 0; i < segment_count; ++i) {
    if (vortex_addr_in_segment(addr, &segments[i])) {
      return payload[segments[i].payload_offset + (addr - segments[i].addr)];
    }
  }
  return vortex_uninitialized_byte(addr);
}

VORTEX_MEM_DEVICE_INLINE int vortex_find_block(VortexMemBlock *blocks, uint32_t block_count, uint64_t block_addr) {
  for (uint32_t i = 0; i < block_count; ++i) {
    if (blocks[i].block_addr == block_addr) {
      return (int)i;
    }
  }
  return -1;
}

VORTEX_MEM_DEVICE_INLINE void vortex_init_blocks_from_segments(VortexMemBlock *blocks,
                                                               uint32_t block_count,
                                                               const VortexMemSegment *segments,
                                                               uint32_t segment_count,
                                                               const uint8_t *payload) {
  for (uint32_t block = 0; block < block_count; ++block) {
    const uint64_t base_addr = blocks[block].block_addr * VORTEX_MEM_BLOCK_SIZE;
    for (uint32_t lane = 0; lane < VORTEX_MEM_BLOCK_SIZE; ++lane) {
      blocks[block].data[lane] = vortex_payload_read_byte(segments, segment_count, payload, base_addr + lane);
    }
  }
}

VORTEX_MEM_DEVICE_INLINE void vortex_mem_access_device_helper(uint8_t req_rw,
                                                              uint64_t byteen,
                                                              uint64_t block_addr,
                                                              const uint8_t *wdata,
                                                              uint8_t *rdata,
                                                              VortexMemBlock *blocks,
                                                              uint32_t block_count,
                                                              VortexIoCoutCapture *io_cout) {
  const uint64_t addr = block_addr * VORTEX_MEM_BLOCK_SIZE;
  const int block_index = vortex_find_block(blocks, block_count, block_addr);

  if (!req_rw) {
    for (uint32_t lane = 0; lane < VORTEX_MEM_BLOCK_SIZE; ++lane) {
      rdata[lane] = block_index >= 0 ? blocks[block_index].data[lane] : vortex_uninitialized_byte(addr + lane);
    }
    return;
  }

  if (VORTEX_IO_COUT_ADDR <= addr && addr < (VORTEX_IO_COUT_ADDR + VORTEX_IO_COUT_SIZE)) {
    if (io_cout != 0) {
      for (uint32_t lane = 0; lane < VORTEX_IO_COUT_SIZE; ++lane) {
        if (((byteen >> lane) & 1ull) && io_cout->count < VORTEX_IO_COUT_SIZE) {
          const uint32_t out = io_cout->count++;
          io_cout->lanes[out] = (uint8_t)lane;
          io_cout->chars[out] = wdata[lane];
        }
      }
    }
    return;
  }

  if (block_index < 0) {
    return;
  }
  for (uint32_t lane = 0; lane < VORTEX_MEM_BLOCK_SIZE; ++lane) {
    if ((byteen >> lane) & 1ull) {
      blocks[block_index].data[lane] = wdata[lane];
    }
  }
}

VORTEX_MEM_DEVICE_INLINE VortexPostCompareResult vortex_post_compare_device_helper(
    VortexMemBlock *blocks,
    uint32_t block_count,
    const VortexMemSegment *post_segments,
    uint32_t post_segment_count,
    const uint8_t *post_payload) {
  VortexPostCompareResult result;
  result.mismatch_count = 0;
  result.first_mismatch_addr = 0;
  result.first_expected = 0;
  result.first_actual = 0;

  for (uint32_t segment_index = 0; segment_index < post_segment_count; ++segment_index) {
    const VortexMemSegment *segment = &post_segments[segment_index];
    for (uint64_t offset = 0; offset < segment->size_bytes; ++offset) {
      const uint64_t addr = segment->addr + offset;
      const uint64_t block_addr = addr / VORTEX_MEM_BLOCK_SIZE;
      const uint32_t lane = (uint32_t)(addr % VORTEX_MEM_BLOCK_SIZE);
      const int block_index = vortex_find_block(blocks, block_count, block_addr);
      const uint8_t actual = block_index >= 0 ? blocks[block_index].data[lane] : vortex_uninitialized_byte(addr);
      const uint8_t expected = post_payload[segment->payload_offset + offset];
      if (actual != expected) {
        if (result.mismatch_count == 0) {
          result.first_mismatch_addr = addr;
          result.first_expected = expected;
          result.first_actual = actual;
        }
        ++result.mismatch_count;
      }
    }
  }
  return result;
}

#endif
