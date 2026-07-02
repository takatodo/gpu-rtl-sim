#ifndef GPU_TOGGLE_VORTEX_OBSERVABLE_EXPORT_H
#define GPU_TOGGLE_VORTEX_OBSERVABLE_EXPORT_H

#include <stddef.h>
#include <stdint.h>

#include "vortex_memory_model_device.h"
#include "vortex_runtime_upload.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef VortexCuResult (*VortexCuMemcpyDtoHFn)(void *, VortexCuDeviceptr, size_t);

typedef struct {
  VortexCuMemcpyDtoHFn cuMemcpyDtoH;
} VortexObservableExportDriver;

typedef struct {
  VortexCuDeviceptr post_compare_result;
  VortexCuDeviceptr stdout_ring;
  size_t stdout_ring_bytes;
} VortexObservableDeviceBuffers;

typedef struct {
  VortexPostCompareResult post_compare;
  unsigned char stdout_bytes[64];
  size_t stdout_bytes_copied;
  int post_compare_exported;
  int stdout_exported;
  int memory_post_condition_passed;
  int stdout_test_passed_observed;
  int authority_passed;
  const char *authority_source;
  int failed_copy_index;
  const char *failed_op;
  VortexCuResult failed_result;
} VortexObservableExportSummary;

static inline int vortex_stdout_contains_test_passed(const unsigned char *bytes, size_t byte_count) {
  static const unsigned char needle[] = "TEST PASSED";
  const size_t needle_bytes = sizeof(needle) - 1u;
  if (bytes == 0 || byte_count < needle_bytes) return 0;
  for (size_t i = 0; i + needle_bytes <= byte_count; ++i) {
    size_t matched = 0;
    while (matched < needle_bytes && bytes[i + matched] == needle[matched]) {
      ++matched;
    }
    if (matched == needle_bytes) return 1;
  }
  return 0;
}

static inline void vortex_observable_export_summary_clear(VortexObservableExportSummary *summary) {
  if (summary == 0) return;
  summary->post_compare.mismatch_count = 0;
  summary->post_compare.first_mismatch_addr = 0;
  summary->post_compare.first_expected = 0;
  summary->post_compare.first_actual = 0;
  for (size_t i = 0; i < sizeof(summary->stdout_bytes); ++i) {
    summary->stdout_bytes[i] = 0;
  }
  summary->stdout_bytes_copied = 0;
  summary->post_compare_exported = 0;
  summary->stdout_exported = 0;
  summary->memory_post_condition_passed = 0;
  summary->stdout_test_passed_observed = 0;
  summary->authority_passed = 0;
  summary->authority_source = 0;
  summary->failed_copy_index = -1;
  summary->failed_op = 0;
  summary->failed_result = VORTEX_CUDA_SUCCESS;
}

static inline void vortex_observable_authority_update(VortexObservableExportSummary *summary) {
  if (summary == 0) return;
  summary->stdout_test_passed_observed =
      summary->stdout_exported &&
      vortex_stdout_contains_test_passed(summary->stdout_bytes, summary->stdout_bytes_copied);
  summary->authority_passed =
      (summary->post_compare_exported && summary->memory_post_condition_passed) ||
      summary->stdout_test_passed_observed;
  if (summary->post_compare_exported && summary->memory_post_condition_passed &&
      summary->stdout_test_passed_observed) {
    summary->authority_source = "memory_post_condition_and_stdout_TEST_PASSED";
  } else if (summary->post_compare_exported && summary->memory_post_condition_passed) {
    summary->authority_source = "memory_post_condition";
  } else if (summary->stdout_test_passed_observed) {
    summary->authority_source = "stdout_TEST_PASSED";
  } else {
    summary->authority_source = 0;
  }
}

static inline VortexCuResult vortex_export_observables(const VortexObservableExportDriver *driver,
                                                       const VortexObservableDeviceBuffers *buffers,
                                                       VortexObservableExportSummary *summary) {
  vortex_observable_export_summary_clear(summary);
  if (driver == 0 || driver->cuMemcpyDtoH == 0 || buffers == 0 || summary == 0) {
    if (summary != 0) {
      summary->failed_copy_index = -1;
      summary->failed_op = "invalid_observable_export_args";
      summary->failed_result = 1;
    }
    return 1;
  }
  if (buffers->post_compare_result == 0) {
    summary->failed_copy_index = 0;
    summary->failed_op = "missing_post_compare_result";
    summary->failed_result = 1;
    return 1;
  }

  VortexCuResult result = driver->cuMemcpyDtoH(&summary->post_compare,
                                               buffers->post_compare_result,
                                               sizeof(summary->post_compare));
  if (result != VORTEX_CUDA_SUCCESS) {
    summary->failed_copy_index = 0;
    summary->failed_op = "cuMemcpyDtoH_post_compare_result";
    summary->failed_result = result;
    return result;
  }
  summary->post_compare_exported = 1;
  summary->memory_post_condition_passed = summary->post_compare.mismatch_count == 0;

  if (buffers->stdout_ring != 0 && buffers->stdout_ring_bytes != 0) {
    size_t copy_bytes = buffers->stdout_ring_bytes;
    if (copy_bytes > sizeof(summary->stdout_bytes)) {
      copy_bytes = sizeof(summary->stdout_bytes);
    }
    result = driver->cuMemcpyDtoH(summary->stdout_bytes, buffers->stdout_ring, copy_bytes);
    if (result != VORTEX_CUDA_SUCCESS) {
      summary->failed_copy_index = 1;
      summary->failed_op = "cuMemcpyDtoH_stdout_ring";
      summary->failed_result = result;
      return result;
    }
    summary->stdout_bytes_copied = copy_bytes;
    summary->stdout_exported = 1;
  }

  vortex_observable_authority_update(summary);
  return VORTEX_CUDA_SUCCESS;
}

#ifdef __cplusplus
}
#endif

#endif
