#ifndef GPU_TOGGLE_VORTEX_LOWERED_TB_RUNTIME_SEQUENCE_H
#define GPU_TOGGLE_VORTEX_LOWERED_TB_RUNTIME_SEQUENCE_H

#include "vortex_runtime_sequence.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  int runtime_sequence_called;
  int runtime_sequence_passed;
  int authority_report_ready;
  int authority_passed;
  const char *authority_source;
  const char *failed_stage;
  VortexCuResult failed_result;
} VortexLoweredTbRuntimeSummary;

static inline void vortex_lowered_tb_runtime_summary_clear(VortexLoweredTbRuntimeSummary *summary) {
  if (summary == 0) return;
  summary->runtime_sequence_called = 0;
  summary->runtime_sequence_passed = 0;
  summary->authority_report_ready = 0;
  summary->authority_passed = 0;
  summary->authority_source = 0;
  summary->failed_stage = 0;
  summary->failed_result = VORTEX_CUDA_SUCCESS;
}

static inline VortexCuResult vortex_lowered_tb_invoke_runtime_sequence(
    const VortexRuntimeSequenceArgs *args,
    VortexRuntimeSequenceSummary *sequence_summary,
    VortexLoweredTbRuntimeSummary *tb_summary) {
  vortex_lowered_tb_runtime_summary_clear(tb_summary);
  if (tb_summary == 0 || sequence_summary == 0) {
    return 1;
  }
  tb_summary->runtime_sequence_called = 1;
  VortexCuResult result = vortex_run_runtime_sequence(args, sequence_summary);
  tb_summary->failed_result = result;
  tb_summary->failed_stage = sequence_summary->failed_stage;
  tb_summary->runtime_sequence_passed = result == VORTEX_CUDA_SUCCESS;
  tb_summary->authority_report_ready = sequence_summary->observable_export_invoked;
  tb_summary->authority_passed = sequence_summary->observables.authority_passed;
  tb_summary->authority_source = sequence_summary->observables.authority_source;
  return result;
}

#ifdef __cplusplus
}
#endif

#endif
