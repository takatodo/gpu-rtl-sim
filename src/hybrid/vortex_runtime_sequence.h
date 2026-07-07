#ifndef GPU_TOGGLE_VORTEX_RUNTIME_SEQUENCE_H
#define GPU_TOGGLE_VORTEX_RUNTIME_SEQUENCE_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "vortex_observable_export.h"
#include "vortex_runtime_upload.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  uint32_t addr;
  uint32_t value;
} VortexDcrWrite;

typedef VortexCuResult (*VortexDcrApplyFn)(void *user, uint32_t addr, uint32_t value, int reset_asserted);
typedef VortexCuResult (*VortexKernelLaunchFn)(void *user, VortexRuntimeBuffer *buffers, unsigned buffer_count);

typedef struct {
  const VortexCudaUploadDriver *upload_driver;
  VortexRuntimeBuffer *buffers;
  unsigned buffer_count;
  const VortexDcrWrite *dcr_writes;
  unsigned dcr_write_count;
  VortexDcrApplyFn apply_dcr;
  void *dcr_user;
  VortexKernelLaunchFn launch_kernel;
  void *kernel_user;
  const VortexObservableExportDriver *export_driver;
} VortexRuntimeSequenceArgs;

typedef struct {
  VortexRuntimeUploadSummary upload;
  VortexObservableExportSummary observables;
  unsigned dcr_write_count;
  unsigned dcr_applied_count;
  int dcr_reset_asserted;
  int kernel_launch_invoked;
  int observable_export_invoked;
  int buffers_released;
  const char *failed_stage;
  int failed_index;
  VortexCuResult failed_result;
} VortexRuntimeSequenceSummary;

static inline void vortex_runtime_sequence_summary_clear(VortexRuntimeSequenceSummary *summary) {
  if (summary == 0) return;
  vortex_runtime_upload_summary_clear(&summary->upload);
  vortex_observable_export_summary_clear(&summary->observables);
  summary->dcr_write_count = 0;
  summary->dcr_applied_count = 0;
  summary->dcr_reset_asserted = 0;
  summary->kernel_launch_invoked = 0;
  summary->observable_export_invoked = 0;
  summary->buffers_released = 0;
  summary->failed_stage = 0;
  summary->failed_index = -1;
  summary->failed_result = VORTEX_CUDA_SUCCESS;
}

static inline VortexCuDeviceptr vortex_find_runtime_buffer_device_ptr(VortexRuntimeBuffer *buffers,
                                                                      unsigned buffer_count,
                                                                      const char *name) {
  if (buffers == 0 || name == 0) return 0;
  for (unsigned i = 0; i < buffer_count; ++i) {
    if (buffers[i].name != 0 && strcmp(buffers[i].name, name) == 0) {
      return buffers[i].device_ptr;
    }
  }
  return 0;
}

static inline VortexObservableDeviceBuffers vortex_observable_buffers_from_runtime_buffers(
    VortexRuntimeBuffer *buffers,
    unsigned buffer_count) {
  VortexObservableDeviceBuffers out;
  out.post_compare_result =
      vortex_find_runtime_buffer_device_ptr(buffers, buffer_count, "vortex_post_compare_result");
  if (out.post_compare_result == 0) {
    out.post_compare_result =
        vortex_find_runtime_buffer_device_ptr(buffers, buffer_count, "vortex_post_compare_result_initial");
  }
  out.stdout_ring = vortex_find_runtime_buffer_device_ptr(buffers, buffer_count, "vortex_stdout_ring");
  if (out.stdout_ring == 0) {
    out.stdout_ring = vortex_find_runtime_buffer_device_ptr(buffers, buffer_count, "vortex_stdout_ring_initial");
  }
  out.stdout_ring_bytes = out.stdout_ring != 0 ? VORTEX_IO_COUT_SIZE : 0;
  return out;
}

static inline VortexCuResult vortex_run_runtime_sequence(const VortexRuntimeSequenceArgs *args,
                                                         VortexRuntimeSequenceSummary *summary) {
  vortex_runtime_sequence_summary_clear(summary);
  if (args == 0 || summary == 0 || args->upload_driver == 0 || args->buffers == 0 ||
      args->apply_dcr == 0 || args->launch_kernel == 0 || args->export_driver == 0) {
    if (summary != 0) {
      summary->failed_stage = "invalid_runtime_sequence_args";
      summary->failed_result = 1;
    }
    return 1;
  }

  VortexCuResult result = vortex_upload_runtime_buffers(
      args->upload_driver, args->buffers, args->buffer_count, &summary->upload);
  if (result != VORTEX_CUDA_SUCCESS) {
    summary->failed_stage = "upload";
    summary->failed_index = summary->upload.failed_index;
    summary->failed_result = result;
    return result;
  }

  summary->dcr_write_count = args->dcr_write_count;
  summary->dcr_reset_asserted = 1;
  for (unsigned i = 0; i < args->dcr_write_count; ++i) {
    result = args->apply_dcr(args->dcr_user, args->dcr_writes[i].addr, args->dcr_writes[i].value, 1);
    if (result != VORTEX_CUDA_SUCCESS) {
      summary->failed_stage = "dcr_apply";
      summary->failed_index = (int)i;
      summary->failed_result = result;
      vortex_release_runtime_buffers(args->upload_driver, args->buffers, args->buffer_count);
      summary->buffers_released = 1;
      return result;
    }
    ++summary->dcr_applied_count;
  }

  result = args->launch_kernel(args->kernel_user, args->buffers, args->buffer_count);
  summary->kernel_launch_invoked = 1;
  if (result != VORTEX_CUDA_SUCCESS) {
    summary->failed_stage = "kernel_launch";
    summary->failed_result = result;
    vortex_release_runtime_buffers(args->upload_driver, args->buffers, args->buffer_count);
    summary->buffers_released = 1;
    return result;
  }

  VortexObservableDeviceBuffers observable_buffers =
      vortex_observable_buffers_from_runtime_buffers(args->buffers, args->buffer_count);
  result = vortex_export_observables(args->export_driver, &observable_buffers, &summary->observables);
  summary->observable_export_invoked = 1;
  if (result != VORTEX_CUDA_SUCCESS) {
    summary->failed_stage = "observable_export";
    summary->failed_index = summary->observables.failed_copy_index;
    summary->failed_result = result;
    vortex_release_runtime_buffers(args->upload_driver, args->buffers, args->buffer_count);
    summary->buffers_released = 1;
    return result;
  }

  vortex_release_runtime_buffers(args->upload_driver, args->buffers, args->buffer_count);
  summary->buffers_released = 1;
  return VORTEX_CUDA_SUCCESS;
}

#ifdef __cplusplus
}
#endif

#endif
