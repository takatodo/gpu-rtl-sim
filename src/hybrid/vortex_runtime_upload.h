#ifndef GPU_TOGGLE_VORTEX_RUNTIME_UPLOAD_H
#define GPU_TOGGLE_VORTEX_RUNTIME_UPLOAD_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef uint64_t VortexCuDeviceptr;
typedef int VortexCuResult;

#define VORTEX_CUDA_SUCCESS 0

typedef VortexCuResult (*VortexCuMemAllocFn)(VortexCuDeviceptr *, size_t);
typedef VortexCuResult (*VortexCuMemcpyHtoDFn)(VortexCuDeviceptr, const void *, size_t);
typedef VortexCuResult (*VortexCuMemsetD8Fn)(VortexCuDeviceptr, unsigned char, size_t);
typedef VortexCuResult (*VortexCuMemFreeFn)(VortexCuDeviceptr);

typedef struct {
  VortexCuMemAllocFn cuMemAlloc;
  VortexCuMemcpyHtoDFn cuMemcpyHtoD;
  VortexCuMemsetD8Fn cuMemsetD8;
  VortexCuMemFreeFn cuMemFree;
} VortexCudaUploadDriver;

typedef enum {
  VORTEX_BUFFER_HOST_TO_DEVICE = 1,
  VORTEX_BUFFER_DEVICE_TO_HOST = 2
} VortexRuntimeBufferDirection;

typedef struct {
  const char *name;
  const void *host_data;
  size_t bytes;
  VortexRuntimeBufferDirection direction;
  unsigned char initial_value;
  VortexCuDeviceptr device_ptr;
} VortexRuntimeBuffer;

typedef struct {
  unsigned allocated_count;
  unsigned h2d_copy_count;
  unsigned d2h_init_count;
  size_t h2d_bytes;
  size_t d2h_initial_bytes;
  int failed_index;
  const char *failed_op;
  VortexCuResult failed_result;
} VortexRuntimeUploadSummary;

static inline void vortex_runtime_upload_summary_clear(VortexRuntimeUploadSummary *summary) {
  if (summary == 0) return;
  summary->allocated_count = 0;
  summary->h2d_copy_count = 0;
  summary->d2h_init_count = 0;
  summary->h2d_bytes = 0;
  summary->d2h_initial_bytes = 0;
  summary->failed_index = -1;
  summary->failed_op = 0;
  summary->failed_result = VORTEX_CUDA_SUCCESS;
}

static inline int vortex_runtime_buffer_valid(const VortexRuntimeBuffer *buffer) {
  if (buffer == 0 || buffer->bytes == 0) return 0;
  if (buffer->direction == VORTEX_BUFFER_HOST_TO_DEVICE) return buffer->host_data != 0;
  return buffer->direction == VORTEX_BUFFER_DEVICE_TO_HOST;
}

static inline void vortex_release_runtime_buffers(const VortexCudaUploadDriver *driver,
                                                  VortexRuntimeBuffer *buffers,
                                                  unsigned buffer_count) {
  if (driver == 0 || driver->cuMemFree == 0 || buffers == 0) return;
  for (unsigned i = 0; i < buffer_count; ++i) {
    if (buffers[i].device_ptr != 0) {
      (void)driver->cuMemFree(buffers[i].device_ptr);
      buffers[i].device_ptr = 0;
    }
  }
}

static inline VortexCuResult vortex_upload_runtime_buffers(const VortexCudaUploadDriver *driver,
                                                           VortexRuntimeBuffer *buffers,
                                                           unsigned buffer_count,
                                                           VortexRuntimeUploadSummary *summary) {
  vortex_runtime_upload_summary_clear(summary);
  if (driver == 0 || driver->cuMemAlloc == 0 || driver->cuMemcpyHtoD == 0 || driver->cuMemsetD8 == 0) {
    if (summary != 0) {
      summary->failed_index = -1;
      summary->failed_op = "missing_driver_function";
      summary->failed_result = 1;
    }
    return 1;
  }
  if (buffers == 0 && buffer_count != 0) {
    if (summary != 0) {
      summary->failed_index = -1;
      summary->failed_op = "missing_buffers";
      summary->failed_result = 1;
    }
    return 1;
  }

  for (unsigned i = 0; i < buffer_count; ++i) {
    if (!vortex_runtime_buffer_valid(&buffers[i])) {
      if (summary != 0) {
        summary->failed_index = (int)i;
        summary->failed_op = "invalid_buffer";
        summary->failed_result = 1;
      }
      vortex_release_runtime_buffers(driver, buffers, i);
      return 1;
    }

    VortexCuDeviceptr device_ptr = 0;
    VortexCuResult result = driver->cuMemAlloc(&device_ptr, buffers[i].bytes);
    if (result != VORTEX_CUDA_SUCCESS) {
      if (summary != 0) {
        summary->failed_index = (int)i;
        summary->failed_op = "cuMemAlloc";
        summary->failed_result = result;
      }
      vortex_release_runtime_buffers(driver, buffers, i);
      return result;
    }
    buffers[i].device_ptr = device_ptr;
    if (summary != 0) ++summary->allocated_count;

    if (buffers[i].direction == VORTEX_BUFFER_HOST_TO_DEVICE) {
      result = driver->cuMemcpyHtoD(device_ptr, buffers[i].host_data, buffers[i].bytes);
      if (result != VORTEX_CUDA_SUCCESS) {
        if (summary != 0) {
          summary->failed_index = (int)i;
          summary->failed_op = "cuMemcpyHtoD";
          summary->failed_result = result;
        }
        vortex_release_runtime_buffers(driver, buffers, i + 1);
        return result;
      }
      if (summary != 0) {
        ++summary->h2d_copy_count;
        summary->h2d_bytes += buffers[i].bytes;
      }
    } else {
      result = driver->cuMemsetD8(device_ptr, buffers[i].initial_value, buffers[i].bytes);
      if (result != VORTEX_CUDA_SUCCESS) {
        if (summary != 0) {
          summary->failed_index = (int)i;
          summary->failed_op = "cuMemsetD8";
          summary->failed_result = result;
        }
        vortex_release_runtime_buffers(driver, buffers, i + 1);
        return result;
      }
      if (summary != 0) {
        ++summary->d2h_init_count;
        summary->d2h_initial_bytes += buffers[i].bytes;
      }
    }
  }

  return VORTEX_CUDA_SUCCESS;
}

#ifdef __cplusplus
}
#endif

#endif
