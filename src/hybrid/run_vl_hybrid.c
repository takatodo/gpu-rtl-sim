/**
 * run_vl_hybrid.c — Phase-D host: load cubin(s), optional per-step HtoD patches, repeat launch.
 *
 * If RUN_VL_HYBRID_KERNELS is set (comma-separated names), each step launches that sequence
 * instead of a single vl_eval_batch_gpu (see vl_batch_gpu.meta.json launch_sequence).
 * If RUN_VL_HYBRID_CUBINS is set (comma-separated paths), functions are resolved across all
 * loaded cubins in order. argv[1] remains the single-cubin fallback for older callers.
 *
 * Usage:
 *   ./run_vl_hybrid <cubin> <storage_bytes> <nstates> [block] [steps] [patch ...]
 *
 *   patch:  global_byte_offset:value  (value 0–255 decimal, or 0xNN hex)
 *           @state_index:state_local_byte_offset:value
 *   block:  0 = default 256
 *   steps:  0 = default 1; each step applies all patches then launches kernel
 *
 * Example (toggle a byte at global offset 42 before each of 8 evals):
 *   ./run_vl_hybrid m.cubin 2048 1024 256 8 42:0 42:1 42:0
 *   (three patches per step — use one patch per step instead: run with steps=8 and one patch
 *    per step requires multiple invocations; here all patches run each step in order.)
 */

#include <ctype.h>
#include <cuda.h>
#include <limits.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

/* Comma-separated kernel names; Verilator phase order (see vl_batch_gpu.meta.json launch_sequence). */
#define ENV_KERNEL_CHAIN "RUN_VL_HYBRID_KERNELS"
/* Caliptra act-sequent probes can need ico + chunk4 act kernels + nba kernels. */
#define MAX_KERNEL_CHAIN 64
/* Comma-separated cubin paths; used for split entries packaged as independent cubins. */
#define ENV_CUBIN_CHAIN "RUN_VL_HYBRID_CUBINS"
#define MAX_CUBIN_CHAIN 64
/* Optional preflight: load module(s), require one function symbol, then exit. */
#define ENV_MODULE_LOAD_SYMBOL_CHECK "RUN_VL_HYBRID_MODULE_LOAD_SYMBOL_CHECK"

/* Optional binary dump of device storage after the last launch sequence. */
#define ENV_DUMP_STATE "RUN_VL_HYBRID_DUMP_STATE"
/* Optional CSV trace of selected state fields after each synchronized step. */
#define ENV_STEP_TRACE "RUN_VL_HYBRID_STEP_TRACE"
#define ENV_STEP_TRACE_FIELDS "RUN_VL_HYBRID_STEP_TRACE_FIELDS"
#define ENV_STEP_TRACE_DEVICE_BUFFER "RUN_VL_HYBRID_STEP_TRACE_DEVICE_BUFFER"
#define ENV_STEP_TRACE_START "RUN_VL_HYBRID_STEP_TRACE_START"
#define ENV_STEP_TRACE_STRIDE "RUN_VL_HYBRID_STEP_TRACE_STRIDE"
#define MAX_STEP_TRACE_FIELDS 96
#define MAX_STEP_TRACE_NAME 64
#define MAX_STEP_TRACE_COALESCE_SPAN_BYTES (64U * 1024U)
/* Optional comma-separated symbol:path dump list for device-global probe buffers. */
#define ENV_DUMP_GLOBALS "RUN_VL_HYBRID_DUMP_GLOBALS"
/* Optional raw state image copied into device storage before patches/launches. */
#define ENV_INIT_STATE "RUN_VL_HYBRID_INIT_STATE"
/* Optional device-side replication for a single-state init image. */
#define ENV_GPU_REPLICATE_INIT_STATE "RUN_VL_HYBRID_GPU_REPLICATE_INIT_STATE"
/* Optional per-step patch script file; each non-comment line is one step of patch tokens. */
#define ENV_PATCH_SCRIPT "RUN_VL_HYBRID_PATCH_SCRIPT"
/* Explicit resident repeated-step mode; keeps state on device across eval steps. */
#define ENV_RESIDENT_STEPS "RUN_VL_HYBRID_RESIDENT_STEPS"
/* Optional VeeR-style state-grouped resident patch + eval fusion. */
#define ENV_FUSED_PATCH_EVAL "RUN_VL_HYBRID_FUSED_PATCH_EVAL"
/* Optional VeeR-style two-step low/high pair-cycle fusion. */
#define ENV_FUSED_PAIR_CYCLE "RUN_VL_HYBRID_FUSED_PAIR_CYCLE"
/* Optional diagnostic: collapse repeated low/high pair cycles into loop kernels. */
#define ENV_FUSED_PAIR_CYCLE_LOOP "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP"
#define ENV_FUSED_PAIR_CYCLE_LOOP_CHUNK "RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK"
/* Optional state-local resident patches; offsets are relative to each state. */
#define ENV_STATE_LOCAL_PATCHES "RUN_VL_HYBRID_STATE_LOCAL_PATCHES"
/* Optional resident patch replication: treat a single-state schedule as state-local
 * and expand it across all state strides before upload. */
#define ENV_REPLICATE_STATE0_PATCHES "RUN_VL_HYBRID_REPLICATE_STATE0_PATCHES"
/* Optional VeeR-style low-eval/high-eval resident pair-cycle grouping. */
#define ENV_RESIDENT_PAIR_CYCLE "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE"
#define ENV_RESIDENT_PAIR_CYCLE_START "RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START"
/* Probe-only persistent resident state ABI surface. */
#define ENV_PERSISTENT_RESIDENT_HANDLE "RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_HANDLE"
#define ENV_PERSISTENT_RESIDENT_PHASE "RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_PHASE"
#define ENV_PERSISTENT_RESIDENT_PHASE_COUNT "RUN_VL_HYBRID_PERSISTENT_RESIDENT_PHASE_COUNT"
#define ENV_PERSISTENT_RESIDENT_PHASE_DUMPS "RUN_VL_HYBRID_PERSISTENT_RESIDENT_PHASE_DUMPS"
#define MAX_PERSISTENT_RESIDENT_PHASES 64
/* Optional resident feedback edges, encoded as state-local src:dst byte offsets. */
#define ENV_FEEDBACK_EDGES "RUN_VL_HYBRID_FEEDBACK_EDGES"
#define ENV_FEEDBACK_EDGE_MODE "RUN_VL_HYBRID_FEEDBACK_EDGE_MODE"
/* Optional resident feedback increments, encoded as state-local offset:delta bytes. */
#define ENV_FEEDBACK_INCREMENTS "RUN_VL_HYBRID_FEEDBACK_INCREMENTS"
/* Optional resident feedback phase sets, encoded as phase:state-local-offset:byte
 * or @state:phase:state-local-offset:byte. */
#define ENV_FEEDBACK_PHASE_SETS "RUN_VL_HYBRID_FEEDBACK_PHASE_SETS"
/* Probe-only #69 ordering-aware token-loop ABI readiness surface. */
#define ENV_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_CYCLE_LIMIT "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_CYCLE_LIMIT"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_PROGRESS "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_PROGRESS"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_PROGRESS_GLOBAL_DIAGNOSTIC "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_PROGRESS_GLOBAL_DIAGNOSTIC"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_FIRST_LAUNCH_DIAGNOSTIC "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_FIRST_LAUNCH_DIAGNOSTIC"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_SYNC_AFTER_LAUNCH "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_SYNC_AFTER_LAUNCH"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC"
#define ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC_RECORD "RUN_VL_HYBRID_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC_RECORD"
#define ENV_EVAL_PARTITION_PREDICATES "RUN_VL_HYBRID_EVAL_PARTITION_PREDICATES"
#define ENV_EVAL_PARTITION_PREDICATES_ACTIVE_MASK_AUTHORITY "RUN_VL_HYBRID_EVAL_PARTITION_PREDICATES_ACTIVE_MASK_AUTHORITY"
#define ENV_EVAL_PARTITION_GUARDED_SKIP "RUN_VL_HYBRID_EVAL_PARTITION_GUARDED_SKIP"
/* Probe-only CFG-clone liveout execution summary. This is not semantic
 * authority unless a later runtime path can mark executed=true. */
#define ENV_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_ORACLE_PROBE "RUN_VL_HYBRID_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_ORACLE_PROBE"
#define ENV_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_EXPECTED_COUNT "RUN_VL_HYBRID_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_EXPECTED_COUNT"
/* Optional ordering-aware baseline mode: keep the token-loop ABI but do not
 * allocate/pass CFG-clone counter and shadow diagnostic buffers. */
#define ENV_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI "RUN_VL_HYBRID_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI"
/* Optional diagnostic region timing for the ordering-aware token-loop kernel. */
#define ENV_ORDERING_AWARE_REGION_TIMING "RUN_VL_HYBRID_ORDERING_AWARE_REGION_TIMING"
/* Optional diagnostic pointer init for eval closures that contain region counters
 * without the token-loop region timing entrypoint. */
#define ENV_ORDERING_AWARE_REGION_COUNTER_GLOBAL_INIT "RUN_VL_HYBRID_ORDERING_AWARE_REGION_COUNTER_GLOBAL_INIT"
#define ORDERING_AWARE_REGION_TIMING_COUNTERS 16U
#define ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS 192U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE101_PROGRESS_BASE 10U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE102_PROGRESS_BASE 20U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE103_PROGRESS_BASE 30U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE104_PROGRESS_BASE 40U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE105_PROGRESS_BASE 52U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE106_PROGRESS_BASE 60U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE107_PROGRESS_BASE 64U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE108_PROGRESS_BASE 72U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE109_PROGRESS_BASE 80U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE110_PROGRESS_BASE 88U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE111_PROGRESS_BASE 96U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE112_PROGRESS_BASE 104U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE113_PROGRESS_BASE 112U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE114_PROGRESS_BASE 120U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE116_PROGRESS_BASE 128U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE117_PROGRESS_BASE 136U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE118_PROGRESS_BASE 144U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE119_PROGRESS_BASE 152U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE120_PROGRESS_BASE 160U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE122_PROGRESS_BASE 168U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE123_PROGRESS_BASE 176U
#define ORDERING_AWARE_TOKEN_LOOP_STAGE124_PROGRESS_BASE 184U
#define CFG_CLONE_SHADOW_DESCRIPTOR_COUNT 168U
#define CFG_CLONE_SHADOW_DESCRIPTOR_RECORD_BYTES 32U
#define CFG_CLONE_SHADOW_PAYLOAD_BYTES_PER_STATE 672U
#define CFG_CLONE_LIVEOUT_COUNTER_BANDS 106U

/* Set to force one cuCtxSynchronize per step (slower wall clock; old behavior). */
#define ENV_SYNC_EACH_STEP "RUN_VL_HYBRID_SYNC_EACH_STEP"
/* Optional untimed launch after init to absorb first-launch / driver latency. */
#define ENV_WARMUP "RUN_VL_HYBRID_WARMUP"
/* Optional in-process repeated GPU-event timing samples. */
#define ENV_TIMING_REPEATS "RUN_VL_HYBRID_TIMING_REPEATS"
/* Optional stage trace to help localize runtime kills / hangs. */
#define ENV_TRACE_STAGES "RUN_VL_HYBRID_TRACE_STAGES"
/* Optional machine-readable stage timing summary on stdout. */
#define ENV_STAGE_TIMING "RUN_VL_HYBRID_STAGE_TIMING"
/* Optional override of the requested CUDA stack limit in bytes. */
#define ENV_STACK_LIMIT_OVERRIDE "RUN_VL_HYBRID_STACK_LIMIT_OVERRIDE"
/* Optional exit after stack-limit handling, before alloc / launch. */
#define ENV_STACK_LIMIT_PROBE_ONLY "RUN_VL_HYBRID_STACK_LIMIT_PROBE_ONLY"

static void cuda_fail(const char *file, int line, CUresult err, const char *what) {
  const char *msg = NULL;
  cuGetErrorString(err, &msg);
  fprintf(stderr, "%s:%d CUDA error %d: %s (%s)\n", file, line, (int)err,
          msg ? msg : "?", what);
  /* CUDA_ERROR_NO_DEVICE == 100 */
  if ((int)err == 100) {
    fprintf(stderr,
            "Hint: if nvidia-smi works but this fails, on WSL2 try:\n"
            "  export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$LD_LIBRARY_PATH\n"
            "Also check CUDA_VISIBLE_DEVICES and that libcuda is not a stub-only link.\n");
  }
  exit(1);
}

#define CUDA_CHECK(stmt)                                                       \
  do {                                                                         \
    CUresult _err = (stmt);                                                    \
    if (_err != CUDA_SUCCESS) {                                                \
      const char *_msg = NULL;                                                 \
      cuGetErrorString(_err, &_msg);                                           \
      fprintf(stderr, "%s:%d CUDA error %d: %s\n", __FILE__, __LINE__,        \
              (int)_err, _msg ? _msg : "?");                                    \
      exit(1);                                                                 \
    }                                                                          \
  } while (0)

struct ordering_aware_token_loop_progress_watchdog {
  volatile unsigned long long *counters;
  volatile int stop;
  pthread_t thread;
  int started;
};

struct ordering_aware_token_loop_progress_snapshot {
  unsigned long long counters[ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS];
  unsigned long long changed_mask;
  int consistent;
};

static void read_ordering_aware_token_loop_progress_snapshot(
    volatile unsigned long long *counters,
    struct ordering_aware_token_loop_progress_snapshot *snapshot) {
  unsigned long long first[ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS];
  snapshot->changed_mask = 0ULL;
  snapshot->consistent = 1;
  for (unsigned i = 0U; i < ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS; i++)
    first[i] = counters[i];
  for (unsigned i = 0U; i < ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS; i++) {
    snapshot->counters[i] = counters[i];
    if (snapshot->counters[i] != first[i]) {
      if (i < 64U)
        snapshot->changed_mask |= (1ULL << i);
      snapshot->consistent = 0;
    }
  }
}

static const char *ordering_aware_progress_changed_slots(
    unsigned long long changed_mask, char *slots, size_t slot_count) {
  char *out = slots;
  size_t remaining = slot_count;
  int first = 1;
  if (changed_mask == 0ULL)
    return "none";
  if (slot_count == 0U)
    return "";
  slots[0] = '\0';
  for (unsigned i = 0U; i < ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS; i++) {
    if (i >= 64U)
      break;
    if ((changed_mask & (1ULL << i)) == 0ULL)
      continue;
    int written = snprintf(out, remaining, "%s%u", first ? "" : ",", i);
    if (written < 0 || (size_t)written >= remaining)
      break;
    out += written;
    remaining -= (size_t)written;
    first = 0;
  }
  return slots;
}

static const char *ordering_aware_stage67_group_complete_evidence(
    unsigned long long stage, int snapshot_consistent) {
  if (stage != 67ULL)
    return "not_stage67";
  return snapshot_consistent ? "stable" : "unstable_host_read";
}

static unsigned ordering_aware_progress_marker_record(
    unsigned long long marker) {
  return (unsigned)(marker & 0xffffffffULL);
}

static unsigned ordering_aware_progress_marker_high_patch_idx(
    unsigned long long marker) {
  return (unsigned)((marker >> 32) & 0xffffffffULL);
}

static const char *ordering_aware_stage67_group_state(
    unsigned long long stage,
    int snapshot_consistent,
    unsigned long long epoch_begin,
    unsigned long long epoch_end) {
  if (stage != 67ULL)
    return "not_stage67";
  if (!snapshot_consistent)
    return "unstable_host_read";
  if (epoch_begin == epoch_end)
    return "complete";
  return "epoch_begin_visible_epoch_end_pending";
}

static void *ordering_aware_token_loop_progress_watchdog_main(void *arg) {
  struct ordering_aware_token_loop_progress_watchdog *watchdog =
      (struct ordering_aware_token_loop_progress_watchdog *)arg;
  unsigned long long last_stage = ~0ULL;
  unsigned long long last_cycle = ~0ULL;
  while (!watchdog->stop) {
    sleep(1);
    if (watchdog->stop)
      break;
    unsigned long long stage = watchdog->counters[0];
    unsigned long long cycle = watchdog->counters[1];
    if (stage != last_stage || cycle != last_cycle) {
      struct ordering_aware_token_loop_progress_snapshot snapshot;
      read_ordering_aware_token_loop_progress_snapshot(watchdog->counters,
                                                       &snapshot);
      stage = snapshot.counters[0];
      cycle = snapshot.counters[1];
      unsigned long long epoch_begin = snapshot.counters[8];
      unsigned long long epoch_end = snapshot.counters[9];
      int epoch_coherent = epoch_begin == epoch_end;
      int stage67_group_complete =
          stage != 67ULL || (snapshot.consistent && epoch_coherent);
      char changed_slots[32];
      fprintf(stderr,
              "run_vl_hybrid: ordering_aware_token_loop_progress "
              "stage=%llu cycle=%llu slots=%llu,%llu,%llu,%llu,%llu,%llu epoch_begin=%llu epoch_end=%llu epoch_coherent=%s stage67_group_complete=%s snapshot_read_passes=2 host_snapshot_consistent=%s snapshot_consistent=%s snapshot_changed_mask=%llu snapshot_changed_slots=%s stage67_group_complete_evidence=%s stage67_group_state=%s stage67_epoch_begin_record=%u stage67_epoch_end_record=%u stage67_epoch_begin_high_patch_idx=%u stage67_epoch_end_high_patch_idx=%u\n",
              stage, cycle, snapshot.counters[2], snapshot.counters[3],
              snapshot.counters[4], snapshot.counters[5],
              snapshot.counters[6], snapshot.counters[7], epoch_begin,
              epoch_end, epoch_coherent ? "true" : "false",
              stage67_group_complete ? "true" : "false",
              snapshot.consistent ? "true" : "false",
              snapshot.consistent ? "true" : "false", snapshot.changed_mask,
              ordering_aware_progress_changed_slots(snapshot.changed_mask,
                                                    changed_slots,
                                                    sizeof(changed_slots)),
              ordering_aware_stage67_group_complete_evidence(
                  stage, snapshot.consistent),
              ordering_aware_stage67_group_state(stage, snapshot.consistent,
                                                 epoch_begin, epoch_end),
              ordering_aware_progress_marker_record(epoch_begin),
              ordering_aware_progress_marker_record(epoch_end),
              ordering_aware_progress_marker_high_patch_idx(epoch_begin),
              ordering_aware_progress_marker_high_patch_idx(epoch_end));
      fflush(stderr);
      last_stage = stage;
      last_cycle = cycle;
    }
  }
  return NULL;
}

static int start_ordering_aware_token_loop_progress_watchdog(
    struct ordering_aware_token_loop_progress_watchdog *watchdog,
    volatile unsigned long long *counters) {
  memset(watchdog, 0, sizeof(*watchdog));
  watchdog->counters = counters;
  if (pthread_create(&watchdog->thread, NULL,
                     ordering_aware_token_loop_progress_watchdog_main,
                     watchdog) != 0) {
    fprintf(stderr,
            "failed to start ordering-aware token-loop progress watchdog\n");
    return 1;
  }
  watchdog->started = 1;
  return 0;
}

static void stop_ordering_aware_token_loop_progress_watchdog(
    struct ordering_aware_token_loop_progress_watchdog *watchdog) {
  if (!watchdog->started)
    return;
  watchdog->stop = 1;
  pthread_join(watchdog->thread, NULL);
  watchdog->started = 0;
}

static void print_ordering_aware_token_loop_progress_snapshot(
    const char *status, volatile unsigned long long *counters) {
  if (!counters)
    return;
  struct ordering_aware_token_loop_progress_snapshot snapshot;
  read_ordering_aware_token_loop_progress_snapshot(counters, &snapshot);
  unsigned long long epoch_begin = snapshot.counters[8];
  unsigned long long epoch_end = snapshot.counters[9];
  int epoch_coherent = epoch_begin == epoch_end;
  int stage67_group_complete =
      snapshot.counters[0] != 67ULL || (snapshot.consistent && epoch_coherent);
  char changed_slots[32];
  if (status && status[0] != '\0') {
    printf("ordering_aware_token_loop_progress: requested=true status=%s stage=%llu cycle=%llu slots=%llu,%llu,%llu,%llu,%llu,%llu epoch_begin=%llu epoch_end=%llu epoch_coherent=%s stage67_group_complete=%s snapshot_read_passes=2 host_snapshot_consistent=%s snapshot_consistent=%s snapshot_changed_mask=%llu snapshot_changed_slots=%s stage67_group_complete_evidence=%s stage67_group_state=%s stage67_epoch_begin_record=%u stage67_epoch_end_record=%u stage67_epoch_begin_high_patch_idx=%u stage67_epoch_end_high_patch_idx=%u\n",
           status, snapshot.counters[0], snapshot.counters[1],
           snapshot.counters[2], snapshot.counters[3], snapshot.counters[4],
           snapshot.counters[5], snapshot.counters[6], snapshot.counters[7],
           epoch_begin, epoch_end, epoch_coherent ? "true" : "false",
           stage67_group_complete ? "true" : "false",
           snapshot.consistent ? "true" : "false",
           snapshot.consistent ? "true" : "false", snapshot.changed_mask,
           ordering_aware_progress_changed_slots(snapshot.changed_mask,
                                                changed_slots,
                                                sizeof(changed_slots)),
           ordering_aware_stage67_group_complete_evidence(
               snapshot.counters[0], snapshot.consistent),
           ordering_aware_stage67_group_state(snapshot.counters[0],
                                              snapshot.consistent, epoch_begin,
                                              epoch_end),
           ordering_aware_progress_marker_record(epoch_begin),
           ordering_aware_progress_marker_record(epoch_end),
           ordering_aware_progress_marker_high_patch_idx(epoch_begin),
           ordering_aware_progress_marker_high_patch_idx(epoch_end));
  } else {
    printf("ordering_aware_token_loop_progress: requested=true stage=%llu cycle=%llu slots=%llu,%llu,%llu,%llu,%llu,%llu epoch_begin=%llu epoch_end=%llu epoch_coherent=%s stage67_group_complete=%s snapshot_read_passes=2 host_snapshot_consistent=%s snapshot_consistent=%s snapshot_changed_mask=%llu snapshot_changed_slots=%s stage67_group_complete_evidence=%s stage67_group_state=%s stage67_epoch_begin_record=%u stage67_epoch_end_record=%u stage67_epoch_begin_high_patch_idx=%u stage67_epoch_end_high_patch_idx=%u\n",
           snapshot.counters[0], snapshot.counters[1], snapshot.counters[2],
           snapshot.counters[3], snapshot.counters[4], snapshot.counters[5],
           snapshot.counters[6], snapshot.counters[7], epoch_begin, epoch_end,
           epoch_coherent ? "true" : "false",
           stage67_group_complete ? "true" : "false",
           snapshot.consistent ? "true" : "false",
           snapshot.consistent ? "true" : "false", snapshot.changed_mask,
           ordering_aware_progress_changed_slots(snapshot.changed_mask,
                                                changed_slots,
                                                sizeof(changed_slots)),
           ordering_aware_stage67_group_complete_evidence(
               snapshot.counters[0], snapshot.consistent),
           ordering_aware_stage67_group_state(snapshot.counters[0],
                                              snapshot.consistent, epoch_begin,
                                              epoch_end),
           ordering_aware_progress_marker_record(epoch_begin),
           ordering_aware_progress_marker_record(epoch_end),
           ordering_aware_progress_marker_high_patch_idx(epoch_begin),
           ordering_aware_progress_marker_high_patch_idx(epoch_end));
  }
  fflush(stdout);
}

static void print_ordering_aware_token_loop_progress_global_diagnostic(
    const char *status,
    CUdeviceptr d_progress_global,
    size_t global_bytes,
    int progress_global_module_idx,
    int token_loop_module_idx,
    const void *h_progress,
    CUdeviceptr d_progress,
    CUdeviceptr roundtrip_progress,
    CUresult copy_result) {
  const char *copy_name = NULL;
  cuGetErrorName(copy_result, &copy_name);
  printf("ordering_aware_token_loop_progress_global: requested=true status=%s global_ptr=%llu global_bytes=%zu progress_global_module_idx=%d token_loop_module_idx=%d host_ptr=%p device_ptr=%llu roundtrip_device_ptr=%llu roundtrip_matches=%s copy_result=%d copy_error=%s\n",
         status && status[0] ? status : "unknown",
         (unsigned long long)d_progress_global,
         global_bytes,
         progress_global_module_idx,
         token_loop_module_idx,
         h_progress,
         (unsigned long long)d_progress,
         (unsigned long long)roundtrip_progress,
         roundtrip_progress == d_progress ? "true" : "false",
         (int)copy_result,
         copy_name ? copy_name : "?");
  fflush(stdout);
}

#define MAX_PATCHES 4096
typedef struct {
  size_t global_off;
  unsigned char val;
} Patch;

typedef struct {
  Patch *items;
  int count;
} StepPatchList;

typedef struct {
  StepPatchList *steps;
  unsigned step_count;
  unsigned repeat_count;
} StepPatchBlock;

typedef struct {
  size_t *offsets;
  unsigned char *values;
  unsigned *step_offsets;
  unsigned logical_steps;
  unsigned record_count;
  CUdeviceptr d_offsets;
  CUdeviceptr d_values;
} ResidentPatchSchedule;

typedef struct {
  size_t *src_offsets;
  size_t *dst_offsets;
  unsigned edge_count;
  CUdeviceptr d_src_offsets;
  CUdeviceptr d_dst_offsets;
} FeedbackEdgeTable;

typedef struct {
  size_t *offsets;
  unsigned char *deltas;
  unsigned increment_count;
  CUdeviceptr d_offsets;
  CUdeviceptr d_deltas;
} FeedbackIncrementTable;

typedef struct {
  unsigned *phases;
  unsigned *states;
  size_t *offsets;
  unsigned char *values;
  unsigned set_count;
  CUdeviceptr d_phases;
  CUdeviceptr d_states;
  CUdeviceptr d_offsets;
  CUdeviceptr d_values;
} FeedbackSetTable;

typedef struct {
  unsigned *states;
  unsigned *terminal_steps;
  unsigned mask_count;
  CUdeviceptr d_states;
  CUdeviceptr d_terminal_steps;
} OrderingAwareTerminalMaskTable;

typedef struct {
  unsigned *partition_ids;
  unsigned *phases;
  unsigned *states;
  unsigned char *active;
  unsigned char *active_bitmap;
  unsigned record_count;
  unsigned active_bitmap_partition_count;
  unsigned active_bitmap_phase_count;
  unsigned active_bitmap_size;
  CUdeviceptr d_partition_ids;
  CUdeviceptr d_phases;
  CUdeviceptr d_states;
  CUdeviceptr d_active;
  CUdeviceptr d_active_bitmap;
} EvalPartitionPredicateTable;

typedef struct {
  int requested;
  int entrypoint_available;
  int runtime_supported;
  unsigned phase_control_record_count;
  unsigned feedback_copy_record_count;
  unsigned feedback_increment_record_count;
  unsigned pair_cycle_loop_record_count;
  unsigned terminal_mask_record_count;
  unsigned terminal_mask_device_record_count;
  unsigned terminal_mask_parse_error_count;
  int eval_partition_predicates_requested;
  int eval_partition_predicate_active_mask_authority;
  unsigned eval_partition_predicate_record_count;
  unsigned eval_partition_predicate_device_record_count;
  unsigned eval_partition_predicate_parse_error_count;
  unsigned eval_partition_predicate_active_bitmap_partition_count;
  unsigned eval_partition_predicate_active_bitmap_phase_count;
  unsigned eval_partition_predicate_active_bitmap_device_bytes;
  int eval_partition_predicate_read_no_skip_requested;
  int eval_partition_predicate_read_no_skip_device_read;
  int eval_partition_guarded_skip_requested;
  int eval_partition_guarded_skip_enabled;
  unsigned device_table_launch_count;
  unsigned launch_probe_count;
  unsigned cfg_clone_shadow_descriptor_count;
  unsigned cfg_clone_shadow_descriptor_table_bytes;
  unsigned cfg_clone_shadow_payload_bytes_per_state;
  size_t cfg_clone_shadow_payload_total_bytes;
  unsigned cfg_clone_shadow_runtime_argument_count;
  const char *blocking_reason;
} OrderingAwareTokenLoopAbiProbe;

typedef struct {
  char name[MAX_STEP_TRACE_NAME];
  size_t offset;
  size_t size;
} StepTraceField;

typedef struct {
  StepTraceField fields[MAX_STEP_TRACE_FIELDS];
  unsigned field_count;
  size_t coalesced_base;
  size_t coalesced_span;
  unsigned char *coalesced_buf;
  CUdeviceptr d_coalesced_rows;
  unsigned char *host_coalesced_rows;
  CUdeviceptr d_rows;
  unsigned long long *host_rows;
  unsigned row_count;
  unsigned row_capacity;
  unsigned trace_start;
  unsigned trace_stride;
  int device_buffered;
  int flushed;
  FILE *fp;
} StepTrace;

#define MAX_STAGE_TIMINGS 160
typedef struct {
  const char *stage;
  double since_previous_ms;
} StageTiming;

static StageTiming g_stage_timings[MAX_STAGE_TIMINGS];
static unsigned g_stage_timing_count = 0U;
static int g_stage_timing_started = 0;
static struct timespec g_stage_timing_previous;

static int parse_byte(const char *s, unsigned char *out) {
  if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X'))
    return sscanf(s + 2, "%hhx", out) == 1 ? 0 : -1;
  unsigned v;
  if (sscanf(s, "%u", &v) != 1 || v > 255)
    return -1;
  *out = (unsigned char)v;
  return 0;
}

static int parse_patch(const char *arg, Patch *p) {
  const char *colon = strchr(arg, ':');
  if (!colon)
    return -1;
  char *end = NULL;
  unsigned long long off = strtoull(arg, &end, 0);
  if (end != colon || colon[1] == '\0')
    return -1;
  unsigned char b;
  if (parse_byte(colon + 1, &b) != 0)
    return -1;
  p->global_off = (size_t)off;
  p->val = b;
  return 0;
}

static int parse_state_indexed_patch(const char *arg, size_t storage,
                                     unsigned nstates, Patch *p) {
  if (arg[0] != '@')
    return -1;
  const char *first_colon = strchr(arg + 1, ':');
  if (!first_colon)
    return -1;
  const char *second_colon = strchr(first_colon + 1, ':');
  if (!second_colon || second_colon[1] == '\0')
    return -1;
  char *end = NULL;
  unsigned long state = strtoul(arg + 1, &end, 0);
  if (end != first_colon || state >= nstates)
    return -1;
  unsigned long long local_off = strtoull(first_colon + 1, &end, 0);
  if (end != second_colon || local_off >= storage)
    return -1;
  unsigned char b;
  if (parse_byte(second_colon + 1, &b) != 0)
    return -1;
  size_t state_index = (size_t)state;
  size_t local = (size_t)local_off;
  if (storage != 0U && state_index > (SIZE_MAX - local) / storage)
    return -1;
  p->global_off = (state_index * storage) + local;
  p->val = b;
  return 0;
}

static void print_cfg_clone_raw_band_slots(
    const char *field, const unsigned long long *counters,
    unsigned expected_count, unsigned band) {
  printf(" %s=", field);
  if (!counters || expected_count == 0U) {
    printf("none");
    return;
  }
  const size_t base = 6U + ((size_t)band * (size_t)expected_count);
  for (unsigned slot = 0; slot < expected_count; ++slot) {
    printf("%s%u:%llu", slot == 0U ? "" : ",", slot, counters[base + slot]);
  }
}

static int parse_patch_for_storage(const char *arg, size_t storage,
                                   unsigned nstates, Patch *p) {
  if (arg[0] == '@')
    return parse_state_indexed_patch(arg, storage, nstates, p);
  return parse_patch(arg, p);
}

static int apply_patch_array(CUdeviceptr d_storage, size_t total,
                             const Patch *patches, int npatch) {
  for (int i = 0; i < npatch; i++) {
    if (patches[i].global_off >= total) {
      fprintf(stderr, "patch offset %zu >= total %zu\n", patches[i].global_off,
              total);
      return -1;
    }
    CUDA_CHECK(cuMemcpyHtoD(d_storage + patches[i].global_off, &patches[i].val,
                            1));
  }
  return 0;
}

static void free_step_patch_blocks(StepPatchBlock *blocks, unsigned block_count) {
  if (!blocks)
    return;
  for (unsigned block_idx = 0; block_idx < block_count; block_idx++) {
    StepPatchBlock *block = &blocks[block_idx];
    for (unsigned step_idx = 0; step_idx < block->step_count; step_idx++) {
      free(block->steps[step_idx].items);
    }
    free(block->steps);
  }
  free(blocks);
}

static void free_resident_patch_schedule(ResidentPatchSchedule *schedule) {
  if (!schedule)
    return;
  if (schedule->d_offsets)
    CUDA_CHECK(cuMemFree(schedule->d_offsets));
  if (schedule->d_values)
    CUDA_CHECK(cuMemFree(schedule->d_values));
  free(schedule->offsets);
  free(schedule->values);
  free(schedule->step_offsets);
  memset(schedule, 0, sizeof(*schedule));
}

static void free_feedback_edge_table(FeedbackEdgeTable *edges) {
  if (!edges)
    return;
  if (edges->d_src_offsets)
    CUDA_CHECK(cuMemFree(edges->d_src_offsets));
  if (edges->d_dst_offsets)
    CUDA_CHECK(cuMemFree(edges->d_dst_offsets));
  free(edges->src_offsets);
  free(edges->dst_offsets);
  memset(edges, 0, sizeof(*edges));
}

static void free_feedback_increment_table(FeedbackIncrementTable *increments) {
  if (!increments)
    return;
  if (increments->d_offsets)
    CUDA_CHECK(cuMemFree(increments->d_offsets));
  if (increments->d_deltas)
    CUDA_CHECK(cuMemFree(increments->d_deltas));
  free(increments->offsets);
  free(increments->deltas);
  memset(increments, 0, sizeof(*increments));
}

static void free_feedback_set_table(FeedbackSetTable *sets) {
  if (!sets)
    return;
  if (sets->d_phases)
    CUDA_CHECK(cuMemFree(sets->d_phases));
  if (sets->d_states)
    CUDA_CHECK(cuMemFree(sets->d_states));
  if (sets->d_offsets)
    CUDA_CHECK(cuMemFree(sets->d_offsets));
  if (sets->d_values)
    CUDA_CHECK(cuMemFree(sets->d_values));
  free(sets->phases);
  free(sets->states);
  free(sets->offsets);
  free(sets->values);
  memset(sets, 0, sizeof(*sets));
}

static void free_ordering_aware_terminal_mask_table(
    OrderingAwareTerminalMaskTable *masks) {
  if (!masks)
    return;
  if (masks->d_states)
    CUDA_CHECK(cuMemFree(masks->d_states));
  if (masks->d_terminal_steps)
    CUDA_CHECK(cuMemFree(masks->d_terminal_steps));
  free(masks->states);
  free(masks->terminal_steps);
  memset(masks, 0, sizeof(*masks));
}

static void free_eval_partition_predicate_table(
    EvalPartitionPredicateTable *predicates) {
  if (!predicates)
    return;
  if (predicates->d_partition_ids)
    CUDA_CHECK(cuMemFree(predicates->d_partition_ids));
  if (predicates->d_phases)
    CUDA_CHECK(cuMemFree(predicates->d_phases));
  if (predicates->d_states)
    CUDA_CHECK(cuMemFree(predicates->d_states));
  if (predicates->d_active)
    CUDA_CHECK(cuMemFree(predicates->d_active));
  if (predicates->d_active_bitmap)
    CUDA_CHECK(cuMemFree(predicates->d_active_bitmap));
  free(predicates->partition_ids);
  free(predicates->phases);
  free(predicates->states);
  free(predicates->active);
  free(predicates->active_bitmap);
  memset(predicates, 0, sizeof(*predicates));
}

static int append_resident_patch_record(ResidentPatchSchedule *schedule,
                                        unsigned *capacity,
                                        size_t total,
                                        const Patch *patch) {
  if (patch->global_off >= total) {
    fprintf(stderr, "resident patch offset %zu >= total %zu\n",
            patch->global_off, total);
    return -1;
  }
  if (schedule->record_count == *capacity) {
    unsigned new_capacity = *capacity ? (*capacity * 2U) : 64U;
    size_t *grown_offsets =
        (size_t *)realloc(schedule->offsets, new_capacity * sizeof(*schedule->offsets));
    if (!grown_offsets)
      return -1;
    schedule->offsets = grown_offsets;
    unsigned char *grown_values = (unsigned char *)realloc(
        schedule->values, new_capacity * sizeof(*schedule->values));
    if (!grown_values)
      return -1;
    schedule->values = grown_values;
    *capacity = new_capacity;
  }
  schedule->offsets[schedule->record_count] = patch->global_off;
  schedule->values[schedule->record_count] = patch->val;
  schedule->record_count++;
  return 0;
}

static int build_resident_patch_schedule(StepPatchBlock *blocks,
                                         unsigned block_count,
                                         unsigned logical_steps,
                                         size_t total,
                                         ResidentPatchSchedule *out) {
  unsigned record_capacity = 0U;
  unsigned logical_step = 0U;
  memset(out, 0, sizeof(*out));
  out->logical_steps = logical_steps;
  out->step_offsets =
      (unsigned *)calloc((size_t)logical_steps + 1U, sizeof(*out->step_offsets));
  if (!out->step_offsets) {
    fprintf(stderr, "calloc failed for resident patch step offsets\n");
    return -1;
  }
  for (unsigned block_idx = 0; block_idx < block_count; block_idx++) {
    StepPatchBlock *block_desc = &blocks[block_idx];
    for (unsigned repeat_idx = 0; repeat_idx < block_desc->repeat_count; repeat_idx++) {
      for (unsigned step_idx = 0; step_idx < block_desc->step_count; step_idx++, logical_step++) {
        if (logical_step >= logical_steps) {
          fprintf(stderr, "resident patch schedule step overflow\n");
          free_resident_patch_schedule(out);
          return -1;
        }
        out->step_offsets[logical_step] = out->record_count;
        StepPatchList *step = &block_desc->steps[step_idx];
        for (int patch_idx = 0; patch_idx < step->count; patch_idx++) {
          if (append_resident_patch_record(out, &record_capacity, total,
                                           &step->items[patch_idx]) != 0) {
            free_resident_patch_schedule(out);
            return -1;
          }
        }
      }
    }
  }
  if (logical_step != logical_steps) {
    fprintf(stderr, "resident patch schedule expected %u steps, built %u\n",
            logical_steps, logical_step);
    free_resident_patch_schedule(out);
    return -1;
  }
  out->step_offsets[logical_steps] = out->record_count;
  return 0;
}

static int build_state_local_resident_patch_schedule(
    const ResidentPatchSchedule *global, unsigned nstates, size_t storage,
    ResidentPatchSchedule *out) {
  unsigned record_capacity = 0U;
  memset(out, 0, sizeof(*out));
  if (!global || !global->step_offsets || nstates == 0U || storage == 0U) {
    fprintf(stderr,
            "state-local resident patch schedule requires global schedule, nstates, and storage\n");
    return -1;
  }
  out->logical_steps = global->logical_steps;
  out->step_offsets =
      (unsigned *)calloc((size_t)global->logical_steps + 1U,
                         sizeof(*out->step_offsets));
  if (!out->step_offsets) {
    fprintf(stderr, "calloc failed for state-local resident patch step offsets\n");
    return -1;
  }
  for (unsigned step = 0U; step < global->logical_steps; step++) {
    unsigned start = global->step_offsets[step];
    unsigned end = global->step_offsets[step + 1U];
    unsigned count = end - start;
    out->step_offsets[step] = out->record_count;
    if (count == 0U)
      continue;
    if ((count % nstates) != 0U) {
      fprintf(stderr,
              "state-local resident patch step %u count %u is not divisible by nstates %u\n",
              step, count, nstates);
      free_resident_patch_schedule(out);
      return -1;
    }
    unsigned local_count = count / nstates;
    for (unsigned state = 0U; state < nstates; state++) {
      size_t state_base = (size_t)state * storage;
      for (unsigned idx = 0U; idx < local_count; idx++) {
        unsigned record = start + (state * local_count) + idx;
        unsigned local_record = start + idx;
        size_t expected_off = global->offsets[local_record] + state_base;
        if (global->offsets[record] != expected_off ||
            global->values[record] != global->values[local_record]) {
          fprintf(stderr,
                  "state-local resident patch mismatch at step %u state %u local %u\n",
                  step, state, idx);
          free_resident_patch_schedule(out);
          return -1;
        }
      }
    }
    for (unsigned idx = 0U; idx < local_count; idx++) {
      Patch patch = {
          .global_off = global->offsets[start + idx],
          .val = global->values[start + idx],
      };
      if (append_resident_patch_record(out, &record_capacity, storage, &patch) != 0) {
        free_resident_patch_schedule(out);
        return -1;
      }
    }
  }
  out->step_offsets[global->logical_steps] = out->record_count;
  return 0;
}

static int build_replicated_state0_resident_patch_schedule(
    const ResidentPatchSchedule *single_state, unsigned nstates, size_t storage,
    size_t total, ResidentPatchSchedule *out) {
  unsigned record_capacity = 0U;
  memset(out, 0, sizeof(*out));
  if (!single_state || !single_state->step_offsets || nstates == 0U ||
      storage == 0U) {
    fprintf(stderr,
            "replicated resident patch schedule requires source schedule, nstates, and storage\n");
    return -1;
  }
  out->logical_steps = single_state->logical_steps;
  out->step_offsets =
      (unsigned *)calloc((size_t)single_state->logical_steps + 1U,
                         sizeof(*out->step_offsets));
  if (!out->step_offsets) {
    fprintf(stderr, "calloc failed for replicated resident patch step offsets\n");
    return -1;
  }
  for (unsigned step = 0U; step < single_state->logical_steps; step++) {
    unsigned start = single_state->step_offsets[step];
    unsigned end = single_state->step_offsets[step + 1U];
    out->step_offsets[step] = out->record_count;
    for (unsigned state = 0U; state < nstates; state++) {
      size_t state_base = (size_t)state * storage;
      for (unsigned record = start; record < end; record++) {
        if (single_state->offsets[record] >= storage) {
          fprintf(stderr,
                  "replicated resident patch step %u offset %zu is not state-local for storage %zu\n",
                  step, single_state->offsets[record], storage);
          free_resident_patch_schedule(out);
          return -1;
        }
        Patch patch = {
            .global_off = state_base + single_state->offsets[record],
            .val = single_state->values[record],
        };
        if (append_resident_patch_record(out, &record_capacity, total, &patch) != 0) {
          free_resident_patch_schedule(out);
          return -1;
        }
      }
    }
  }
  out->step_offsets[single_state->logical_steps] = out->record_count;
  return 0;
}

static int append_feedback_edge(FeedbackEdgeTable *edges, unsigned *capacity,
                                size_t storage, size_t src, size_t dst) {
  if (src >= storage || dst >= storage) {
    fprintf(stderr,
            "feedback edge local offsets out of range: src=%zu dst=%zu storage=%zu\n",
            src, dst, storage);
    return -1;
  }
  if (edges->edge_count == *capacity) {
    unsigned new_capacity = *capacity ? (*capacity * 2U) : 8U;
    size_t *grown_src =
        (size_t *)realloc(edges->src_offsets,
                          (size_t)new_capacity * sizeof(*edges->src_offsets));
    if (!grown_src)
      return -1;
    edges->src_offsets = grown_src;
    size_t *grown_dst =
        (size_t *)realloc(edges->dst_offsets,
                          (size_t)new_capacity * sizeof(*edges->dst_offsets));
    if (!grown_dst)
      return -1;
    edges->dst_offsets = grown_dst;
    *capacity = new_capacity;
  }
  edges->src_offsets[edges->edge_count] = src;
  edges->dst_offsets[edges->edge_count] = dst;
  edges->edge_count++;
  return 0;
}

static int parse_feedback_edges(const char *raw, size_t storage,
                                FeedbackEdgeTable *out) {
  char *buf = NULL;
  unsigned capacity = 0U;
  memset(out, 0, sizeof(*out));
  if (!raw || raw[0] == '\0')
    return 0;
  buf = strdup(raw);
  if (!buf) {
    fprintf(stderr, "strdup failed for %s\n", ENV_FEEDBACK_EDGES);
    return -1;
  }
  for (char *tok = strtok(buf, ","); tok != NULL; tok = strtok(NULL, ",")) {
    char *spec = NULL;
    char *colon = NULL;
    char *end = NULL;
    unsigned long long src_ull = 0ULL;
    unsigned long long dst_ull = 0ULL;
    while (*tok && isspace((unsigned char)*tok))
      tok++;
    char *trim_end = tok + strlen(tok);
    while (trim_end > tok && isspace((unsigned char)trim_end[-1]))
      *--trim_end = '\0';
    if (*tok == '\0')
      continue;
    spec = tok;
    colon = strchr(spec, ':');
    if (!colon || colon == spec || colon[1] == '\0') {
      fprintf(stderr, "bad %s entry '%s' (want src_local:dst_local)\n",
              ENV_FEEDBACK_EDGES, spec);
      free(buf);
      free_feedback_edge_table(out);
      return -1;
    }
    *colon = '\0';
    src_ull = strtoull(spec, &end, 0);
    if (end == spec || *end != '\0') {
      fprintf(stderr, "bad %s src offset '%s'\n", ENV_FEEDBACK_EDGES, spec);
      free(buf);
      free_feedback_edge_table(out);
      return -1;
    }
    dst_ull = strtoull(colon + 1, &end, 0);
    if (end == colon + 1 || *end != '\0') {
      fprintf(stderr, "bad %s dst offset '%s'\n", ENV_FEEDBACK_EDGES,
              colon + 1);
      free(buf);
      free_feedback_edge_table(out);
      return -1;
    }
    if (append_feedback_edge(out, &capacity, storage, (size_t)src_ull,
                             (size_t)dst_ull) != 0) {
      free(buf);
      free_feedback_edge_table(out);
      return -1;
    }
  }
  free(buf);
  if (out->edge_count == 0U) {
    fprintf(stderr, "%s did not contain any feedback edges\n",
            ENV_FEEDBACK_EDGES);
    return -1;
  }
  return 0;
}

static int append_ordering_aware_terminal_mask(
    OrderingAwareTerminalMaskTable *masks,
    unsigned *capacity,
    unsigned state,
    unsigned terminal_step) {
  if (masks->mask_count == *capacity) {
    unsigned new_capacity = *capacity ? (*capacity * 2U) : 16U;
    unsigned *grown_states =
        (unsigned *)realloc(masks->states,
                            (size_t)new_capacity * sizeof(*masks->states));
    if (!grown_states)
      return -1;
    masks->states = grown_states;
    unsigned *grown_terminal_steps =
        (unsigned *)realloc(masks->terminal_steps,
                            (size_t)new_capacity *
                                sizeof(*masks->terminal_steps));
    if (!grown_terminal_steps)
      return -1;
    masks->terminal_steps = grown_terminal_steps;
    *capacity = new_capacity;
  }
  masks->states[masks->mask_count] = state;
  masks->terminal_steps[masks->mask_count] = terminal_step;
  masks->mask_count++;
  return 0;
}

static int parse_ordering_aware_terminal_mask_records(
    const char *raw,
    unsigned nstates,
    OrderingAwareTerminalMaskTable *out) {
  unsigned capacity = 0U;
  char *buf = NULL;
  unsigned char *seen_states = NULL;
  if (!out)
    return -1;
  memset(out, 0, sizeof(*out));
  if (!raw || raw[0] == '\0')
    return 0;
  seen_states = (unsigned char *)calloc(nstates ? nstates : 1U,
                                        sizeof(*seen_states));
  if (!seen_states) {
    fprintf(stderr, "calloc failed for %s state coverage\n",
            ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK);
    return -1;
  }
  buf = strdup(raw);
  if (!buf) {
    fprintf(stderr, "strdup failed for %s\n",
            ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK);
    free(seen_states);
    return -1;
  }
  for (char *tok = strtok(buf, ","); tok != NULL; tok = strtok(NULL, ",")) {
    char *spec = NULL;
    char *colon = NULL;
    char *end = NULL;
    unsigned long state = 0UL;
    unsigned long terminal_step = 0UL;
    while (*tok && isspace((unsigned char)*tok))
      tok++;
    char *trim_end = tok + strlen(tok);
    while (trim_end > tok && isspace((unsigned char)trim_end[-1]))
      *--trim_end = '\0';
    if (*tok == '\0')
      continue;
    spec = tok;
    colon = strchr(spec, ':');
    if (!colon || colon == spec || colon[1] == '\0') {
      fprintf(stderr, "bad %s entry '%s' (want state:terminal_step)\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK, spec);
      free(buf);
      free(seen_states);
      free_ordering_aware_terminal_mask_table(out);
      return -1;
    }
    *colon = '\0';
    state = strtoul(spec, &end, 0);
    if (end == spec || *end != '\0' || state >= nstates) {
      fprintf(stderr, "bad %s state '%s' for nstates=%u\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK, spec, nstates);
      free(buf);
      free(seen_states);
      free_ordering_aware_terminal_mask_table(out);
      return -1;
    }
    if (seen_states[state]) {
      fprintf(stderr, "duplicate %s state '%lu'\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK, state);
      free(buf);
      free(seen_states);
      free_ordering_aware_terminal_mask_table(out);
      return -1;
    }
    terminal_step = strtoul(colon + 1, &end, 0);
    if (end == colon + 1 || *end != '\0' || terminal_step == 0UL ||
        terminal_step > (unsigned long)UINT_MAX) {
      fprintf(stderr, "bad %s terminal step '%s'\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK, colon + 1);
      free(buf);
      free(seen_states);
      free_ordering_aware_terminal_mask_table(out);
      return -1;
    }
    if (append_ordering_aware_terminal_mask(
            out, &capacity, (unsigned)state, (unsigned)terminal_step) != 0) {
      fprintf(stderr, "failed to append %s entry\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK);
      free(buf);
      free(seen_states);
      free_ordering_aware_terminal_mask_table(out);
      return -1;
    }
    seen_states[state] = 1U;
  }
  free(buf);
  if (out->mask_count != nstates) {
    fprintf(stderr, "%s expected %u per-state records, got %u\n",
            ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK, nstates,
            out->mask_count);
    free(seen_states);
    free_ordering_aware_terminal_mask_table(out);
    return -1;
  }
  for (unsigned state = 0U; state < nstates; state++) {
    if (!seen_states[state]) {
      fprintf(stderr, "%s missing state %u\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK, state);
      free(seen_states);
      free_ordering_aware_terminal_mask_table(out);
      return -1;
    }
  }
  if (out->mask_count > 0U) {
    unsigned *canonical_states =
        (unsigned *)calloc(out->mask_count, sizeof(*canonical_states));
    unsigned *canonical_terminal_steps =
        (unsigned *)calloc(out->mask_count, sizeof(*canonical_terminal_steps));
    if (!canonical_states || !canonical_terminal_steps) {
      fprintf(stderr, "calloc failed while canonicalizing %s by state\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK);
      free(canonical_states);
      free(canonical_terminal_steps);
      free(seen_states);
      free_ordering_aware_terminal_mask_table(out);
      return -1;
    }
    for (unsigned idx = 0U; idx < out->mask_count; idx++) {
      unsigned state = out->states[idx];
      canonical_states[state] = state;
      canonical_terminal_steps[state] = out->terminal_steps[idx];
    }
    free(out->states);
    free(out->terminal_steps);
    out->states = canonical_states;
    out->terminal_steps = canonical_terminal_steps;
  }
  free(seen_states);
  return 0;
}

static int append_eval_partition_predicate(
    EvalPartitionPredicateTable *predicates,
    unsigned *capacity,
    unsigned partition_id,
    unsigned phase,
    unsigned state,
    unsigned active) {
  if (predicates->record_count == *capacity) {
    unsigned new_capacity = *capacity ? (*capacity * 2U) : 64U;
    unsigned *grown_partitions = (unsigned *)realloc(
        predicates->partition_ids,
        (size_t)new_capacity * sizeof(*predicates->partition_ids));
    if (!grown_partitions)
      return -1;
    predicates->partition_ids = grown_partitions;
    unsigned *grown_phases = (unsigned *)realloc(
        predicates->phases, (size_t)new_capacity * sizeof(*predicates->phases));
    if (!grown_phases)
      return -1;
    predicates->phases = grown_phases;
    unsigned *grown_states = (unsigned *)realloc(
        predicates->states, (size_t)new_capacity * sizeof(*predicates->states));
    if (!grown_states)
      return -1;
    predicates->states = grown_states;
    unsigned char *grown_active = (unsigned char *)realloc(
        predicates->active, (size_t)new_capacity * sizeof(*predicates->active));
    if (!grown_active)
      return -1;
    predicates->active = grown_active;
    *capacity = new_capacity;
  }
  predicates->partition_ids[predicates->record_count] = partition_id;
  predicates->phases[predicates->record_count] = phase;
  predicates->states[predicates->record_count] = state;
  predicates->active[predicates->record_count] = (unsigned char)active;
  predicates->record_count++;
  return 0;
}

static int parse_eval_partition_predicate_records(
    const char *raw,
    unsigned nstates,
    EvalPartitionPredicateTable *out) {
  unsigned capacity = 0U;
  unsigned max_partition = 0U;
  unsigned max_phase = 0U;
  char *buf = NULL;
  if (!out)
    return -1;
  memset(out, 0, sizeof(*out));
  if (!raw || raw[0] == '\0')
    return 0;
  if (nstates == 0U) {
    fprintf(stderr, "%s requires nstates > 0\n", ENV_EVAL_PARTITION_PREDICATES);
    return -1;
  }
  buf = strdup(raw);
  if (!buf) {
    fprintf(stderr, "strdup failed for %s\n", ENV_EVAL_PARTITION_PREDICATES);
    return -1;
  }
  for (char *tok = strtok(buf, ","); tok != NULL; tok = strtok(NULL, ",")) {
    char *parts[4] = {0};
    char *cursor = tok;
    char *end = NULL;
    unsigned long values[4] = {0UL, 0UL, 0UL, 0UL};
    while (*cursor && isspace((unsigned char)*cursor))
      cursor++;
    char *trim_end = cursor + strlen(cursor);
    while (trim_end > cursor && isspace((unsigned char)trim_end[-1]))
      *--trim_end = '\0';
    if (*cursor == '\0')
      continue;
    for (unsigned idx = 0U; idx < 4U; idx++) {
      parts[idx] = cursor;
      char *colon = strchr(cursor, ':');
      if (idx < 3U) {
        if (!colon || colon == cursor) {
          fprintf(stderr,
                  "bad %s entry '%s' (want partition:phase:state:active)\n",
                  ENV_EVAL_PARTITION_PREDICATES, tok);
          free(buf);
          free_eval_partition_predicate_table(out);
          return -1;
        }
        *colon = '\0';
        cursor = colon + 1;
      } else if (colon) {
        fprintf(stderr,
                "bad %s entry '%s' (want partition:phase:state:active)\n",
                ENV_EVAL_PARTITION_PREDICATES, tok);
        free(buf);
        free_eval_partition_predicate_table(out);
        return -1;
      }
    }
    for (unsigned idx = 0U; idx < 4U; idx++) {
      values[idx] = strtoul(parts[idx], &end, 0);
      if (end == parts[idx] || *end != '\0' ||
          values[idx] > (unsigned long)UINT_MAX) {
        fprintf(stderr, "bad %s numeric field '%s'\n",
                ENV_EVAL_PARTITION_PREDICATES, parts[idx]);
        free(buf);
        free_eval_partition_predicate_table(out);
        return -1;
      }
    }
    if (values[2] >= (unsigned long)nstates) {
      fprintf(stderr, "bad %s state '%lu' for nstates=%u\n",
              ENV_EVAL_PARTITION_PREDICATES, values[2], nstates);
      free(buf);
      free_eval_partition_predicate_table(out);
      return -1;
    }
    if (values[1] > (unsigned long)INT_MAX) {
      fprintf(stderr, "bad %s phase '%lu' for int ABI\n",
              ENV_EVAL_PARTITION_PREDICATES, values[1]);
      free(buf);
      free_eval_partition_predicate_table(out);
      return -1;
    }
    if (values[3] > 1UL) {
      fprintf(stderr, "bad %s active value '%lu' (want 0 or 1)\n",
              ENV_EVAL_PARTITION_PREDICATES, values[3]);
      free(buf);
      free_eval_partition_predicate_table(out);
      return -1;
    }
    if (append_eval_partition_predicate(
            out, &capacity, (unsigned)values[0], (unsigned)values[1],
            (unsigned)values[2], (unsigned)values[3]) != 0) {
      fprintf(stderr, "failed to append %s entry\n",
              ENV_EVAL_PARTITION_PREDICATES);
      free(buf);
      free_eval_partition_predicate_table(out);
      return -1;
    }
    if ((unsigned)values[1] > max_phase)
      max_phase = (unsigned)values[1];
    if ((unsigned)values[0] > max_partition)
      max_partition = (unsigned)values[0];
  }
  free(buf);
  if (out->record_count == 0U) {
    fprintf(stderr, "%s did not contain any predicate records\n",
            ENV_EVAL_PARTITION_PREDICATES);
    return -1;
  }
  if (max_phase == UINT_MAX) {
    fprintf(stderr, "%s active bitmap phase count overflow\n",
            ENV_EVAL_PARTITION_PREDICATES);
    free_eval_partition_predicate_table(out);
    return -1;
  }
  out->active_bitmap_partition_count = max_partition + 1U;
  out->active_bitmap_phase_count = max_phase + 1U;
  if (out->active_bitmap_partition_count != 0U &&
      out->active_bitmap_phase_count >
          UINT_MAX / out->active_bitmap_partition_count) {
    fprintf(stderr, "%s active bitmap dimensions overflow\n",
            ENV_EVAL_PARTITION_PREDICATES);
    free_eval_partition_predicate_table(out);
    return -1;
  }
  unsigned partition_phase_count =
      out->active_bitmap_partition_count * out->active_bitmap_phase_count;
  if (partition_phase_count > UINT_MAX / nstates) {
    fprintf(stderr, "%s active bitmap dimensions overflow\n",
            ENV_EVAL_PARTITION_PREDICATES);
    free_eval_partition_predicate_table(out);
    return -1;
  }
  out->active_bitmap_size = partition_phase_count * nstates;
  out->active_bitmap =
      (unsigned char *)calloc(out->active_bitmap_size, sizeof(*out->active_bitmap));
  if (!out->active_bitmap) {
    fprintf(stderr, "calloc failed for %s active bitmap\n",
            ENV_EVAL_PARTITION_PREDICATES);
    free_eval_partition_predicate_table(out);
    return -1;
  }
  for (unsigned idx = 0U; idx < out->record_count; idx++) {
    if (out->active[idx]) {
      unsigned bitmap_idx =
          ((out->partition_ids[idx] * out->active_bitmap_phase_count +
            out->phases[idx]) *
           nstates) +
          out->states[idx];
      out->active_bitmap[bitmap_idx] = 1U;
    }
  }
  return 0;
}

static void update_ordering_aware_token_loop_abi_probe(
    OrderingAwareTokenLoopAbiProbe *probe,
    int entrypoint_available,
    ResidentPatchSchedule *schedule,
    FeedbackEdgeTable *edges,
    FeedbackIncrementTable *increments,
    FeedbackSetTable *sets,
    unsigned terminal_mask_record_count,
    unsigned terminal_mask_device_record_count,
    unsigned terminal_mask_parse_error_count,
    int eval_partition_predicates_requested,
    int eval_partition_predicate_active_mask_authority,
    unsigned eval_partition_predicate_record_count,
    unsigned eval_partition_predicate_device_record_count,
    unsigned eval_partition_predicate_parse_error_count,
    unsigned eval_partition_predicate_active_bitmap_partition_count,
    unsigned eval_partition_predicate_active_bitmap_phase_count,
    unsigned eval_partition_predicate_active_bitmap_device_bytes,
    int eval_partition_predicate_read_no_skip_requested,
    int eval_partition_predicate_read_no_skip_device_read,
    int eval_partition_guarded_skip_requested,
    int eval_partition_guarded_skip_enabled,
    int cfg_clone_diagnostic_abi_enabled) {
  if (!probe || !probe->requested)
    return;
  probe->entrypoint_available = entrypoint_available;
  probe->phase_control_record_count = sets ? sets->set_count : 0U;
  probe->feedback_copy_record_count = edges ? edges->edge_count : 0U;
  probe->feedback_increment_record_count =
      increments ? increments->increment_count : 0U;
  probe->pair_cycle_loop_record_count =
      schedule ? (schedule->logical_steps / 2U) : 0U;
  probe->terminal_mask_record_count = terminal_mask_record_count;
  probe->terminal_mask_device_record_count = terminal_mask_device_record_count;
  probe->terminal_mask_parse_error_count = terminal_mask_parse_error_count;
  probe->eval_partition_predicates_requested =
      eval_partition_predicates_requested;
  probe->eval_partition_predicate_active_mask_authority =
      eval_partition_predicate_active_mask_authority;
  probe->eval_partition_predicate_record_count =
      eval_partition_predicate_record_count;
  probe->eval_partition_predicate_device_record_count =
      eval_partition_predicate_device_record_count;
  probe->eval_partition_predicate_parse_error_count =
      eval_partition_predicate_parse_error_count;
  probe->eval_partition_predicate_active_bitmap_partition_count =
      eval_partition_predicate_active_bitmap_partition_count;
  probe->eval_partition_predicate_active_bitmap_phase_count =
      eval_partition_predicate_active_bitmap_phase_count;
  probe->eval_partition_predicate_active_bitmap_device_bytes =
      eval_partition_predicate_active_bitmap_device_bytes;
  probe->eval_partition_predicate_read_no_skip_requested =
      eval_partition_predicate_read_no_skip_requested;
  probe->eval_partition_predicate_read_no_skip_device_read =
      eval_partition_predicate_read_no_skip_device_read;
  probe->eval_partition_guarded_skip_requested =
      eval_partition_guarded_skip_requested;
  probe->eval_partition_guarded_skip_enabled =
      eval_partition_guarded_skip_enabled;
  probe->cfg_clone_shadow_descriptor_count =
      cfg_clone_diagnostic_abi_enabled ? CFG_CLONE_SHADOW_DESCRIPTOR_COUNT : 0U;
  probe->cfg_clone_shadow_descriptor_table_bytes =
      cfg_clone_diagnostic_abi_enabled
          ? CFG_CLONE_SHADOW_DESCRIPTOR_COUNT *
                CFG_CLONE_SHADOW_DESCRIPTOR_RECORD_BYTES
          : 0U;
  probe->cfg_clone_shadow_payload_bytes_per_state =
      cfg_clone_diagnostic_abi_enabled ? CFG_CLONE_SHADOW_PAYLOAD_BYTES_PER_STATE
                                       : 0U;
  probe->cfg_clone_shadow_runtime_argument_count =
      cfg_clone_diagnostic_abi_enabled ? 3U : 0U;
  probe->runtime_supported = 0;
  if (!entrypoint_available)
    probe->blocking_reason = "missing_ordering_aware_token_loop_entrypoint";
  else if (probe->phase_control_record_count == 0U)
    probe->blocking_reason = "missing_phase_control_records";
  else if (probe->feedback_copy_record_count == 0U)
    probe->blocking_reason = "missing_feedback_copy_records";
  else if (probe->feedback_increment_record_count == 0U)
    probe->blocking_reason = "missing_feedback_increment_records";
  else if (probe->pair_cycle_loop_record_count == 0U)
    probe->blocking_reason = "missing_pair_cycle_loop_records";
  else if (probe->terminal_mask_record_count == 0U)
    probe->blocking_reason = "missing_per_state_terminal_mask_records";
  else if (probe->terminal_mask_parse_error_count > 0U)
    probe->blocking_reason = "invalid_per_state_terminal_mask_records";
  else
    probe->blocking_reason = "runtime_launch_path_not_integrated";
}

static int append_script_block(StepPatchBlock **blocks, unsigned *block_count,
                               unsigned *block_capacity, StepPatchBlock *block) {
  if (*block_count == *block_capacity) {
    unsigned new_capacity = *block_capacity ? (*block_capacity * 2U) : 16U;
    StepPatchBlock *grown = (StepPatchBlock *)realloc(
        *blocks, new_capacity * sizeof(**blocks));
    if (!grown) {
      return -1;
    }
    *blocks = grown;
    *block_capacity = new_capacity;
  }
  (*blocks)[*block_count] = *block;
  (*block_count)++;
  return 0;
}

static int append_step_to_block(StepPatchBlock *block, unsigned *step_capacity,
                                StepPatchList *step) {
  if (block->step_count == *step_capacity) {
    unsigned new_capacity = *step_capacity ? (*step_capacity * 2U) : 16U;
    StepPatchList *grown =
        (StepPatchList *)realloc(block->steps, new_capacity * sizeof(*block->steps));
    if (!grown) {
      return -1;
    }
    block->steps = grown;
    *step_capacity = new_capacity;
  }
  block->steps[block->step_count] = *step;
  block->step_count++;
  return 0;
}

static int load_patch_script(const char *path, size_t storage, unsigned nstates,
                             StepPatchBlock **out_blocks,
                             unsigned *out_block_count,
                             unsigned *out_logical_step_count,
                             unsigned *out_record_count) {
  FILE *fp = fopen(path, "r");
  char line[65536];
  StepPatchBlock *blocks = NULL;
  unsigned block_count = 0;
  unsigned block_capacity = 0;
  unsigned logical_step_count = 0;
  unsigned record_count = 0;
  int in_repeat_seq = 0;
  unsigned repeat_seq_count = 0;
  unsigned repeat_seq_step_capacity = 0;
  StepPatchBlock repeat_seq_block = {.steps = NULL, .step_count = 0U, .repeat_count = 0U};
  unsigned line_no = 0;
  if (!fp) {
    fprintf(stderr, "failed to open %s=%s\n", ENV_PATCH_SCRIPT, path);
    return -1;
  }

  while (fgets(line, sizeof(line), fp) != NULL) {
    char *cursor = line;
    char *token = NULL;
    char *comment = NULL;
    Patch parsed[MAX_PATCHES];
    int parsed_count = 0;
    int no_patch_step = 0;
    line_no++;

    if (strchr(line, '\n') == NULL && !feof(fp)) {
      fprintf(stderr, "%s line %u exceeds internal parser buffer\n", path,
              line_no);
      fclose(fp);
      free_step_patch_blocks(blocks, block_count);
      return -1;
    }

    while (*cursor != '\0' && isspace((unsigned char)*cursor))
      cursor++;
    if (*cursor == '\0' || *cursor == '\n' || *cursor == '#')
      continue;

    comment = strchr(cursor, '#');
    if (comment)
      *comment = '\0';

    token = strtok(cursor, " \t\r\n");
    if (token && strcmp(token, "@repeat-seq") == 0) {
      char *count_token = strtok(NULL, " \t\r\n");
      char *extra = strtok(NULL, " \t\r\n");
      unsigned long parsed_repeat = 0;
      char *end = NULL;
      if (in_repeat_seq) {
        fprintf(stderr, "%s line %u nests @repeat-seq blocks\n", path, line_no);
        fclose(fp);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      if (!count_token || extra) {
        fprintf(stderr, "%s line %u requires '@repeat-seq <count>' only\n", path, line_no);
        fclose(fp);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      parsed_repeat = strtoul(count_token, &end, 0);
      if (end == count_token || *end != '\0' || parsed_repeat == 0UL) {
        fprintf(stderr, "%s line %u has invalid repeat count '%s'\n", path, line_no, count_token);
        fclose(fp);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      in_repeat_seq = 1;
      repeat_seq_count = (unsigned)parsed_repeat;
      repeat_seq_step_capacity = 0;
      repeat_seq_block.steps = NULL;
      repeat_seq_block.step_count = 0;
      repeat_seq_block.repeat_count = repeat_seq_count;
      continue;
    }
    if (token && strcmp(token, "@end-repeat-seq") == 0) {
      if (!in_repeat_seq) {
        fprintf(stderr, "%s line %u has @end-repeat-seq without matching block\n", path, line_no);
        fclose(fp);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      if (repeat_seq_block.step_count == 0) {
        fprintf(stderr, "%s line %u closes an empty @repeat-seq block\n", path, line_no);
        fclose(fp);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      if (append_script_block(&blocks, &block_count, &block_capacity, &repeat_seq_block) != 0) {
        fprintf(stderr, "realloc failed while loading %s\n", path);
        fclose(fp);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      logical_step_count += repeat_seq_block.step_count * repeat_seq_block.repeat_count;
      record_count += repeat_seq_block.step_count;
      in_repeat_seq = 0;
      repeat_seq_count = 0;
      repeat_seq_step_capacity = 0;
      repeat_seq_block.steps = NULL;
      repeat_seq_block.step_count = 0;
      repeat_seq_block.repeat_count = 0;
      continue;
    }
    while (token != NULL) {
      if (strcmp(token, "-") == 0) {
        if (parsed_count != 0 || no_patch_step) {
          fprintf(stderr, "%s line %u mixes '-' with concrete patches\n", path,
                  line_no);
          fclose(fp);
          free_step_patch_blocks(blocks, block_count);
          return -1;
        }
        no_patch_step = 1;
      } else {
        if (no_patch_step) {
          fprintf(stderr, "%s line %u mixes '-' with concrete patches\n", path,
                  line_no);
          fclose(fp);
          free_step_patch_blocks(blocks, block_count);
          return -1;
        }
        if (parsed_count >= MAX_PATCHES) {
          fprintf(stderr, "%s line %u exceeds max patches per step (%d)\n",
                  path, line_no, MAX_PATCHES);
          fclose(fp);
          free_step_patch_blocks(blocks, block_count);
          return -1;
        }
        if (parse_patch_for_storage(token, storage, nstates, &parsed[parsed_count]) != 0) {
          fprintf(stderr,
                  "%s line %u has bad patch token '%s' (want global_offset:byte or @state:local_offset:byte)\n",
                  path, line_no, token);
          fclose(fp);
          free_step_patch_blocks(blocks, block_count);
          return -1;
        }
        parsed_count++;
      }
      token = strtok(NULL, " \t\r\n");
    }
    StepPatchList parsed_step = {.items = NULL, .count = parsed_count};
    if (parsed_count > 0) {
      parsed_step.items =
          (Patch *)malloc((size_t)parsed_count * sizeof(Patch));
      if (!parsed_step.items) {
        fprintf(stderr, "malloc failed while loading %s\n", path);
        fclose(fp);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      memcpy(parsed_step.items, parsed,
             (size_t)parsed_count * sizeof(Patch));
    }
    if (in_repeat_seq) {
      if (append_step_to_block(&repeat_seq_block, &repeat_seq_step_capacity, &parsed_step) != 0) {
        fprintf(stderr, "realloc failed while loading %s\n", path);
        fclose(fp);
        free(parsed_step.items);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
    } else {
      StepPatchBlock single_block = {.steps = NULL, .step_count = 0U, .repeat_count = 0U};
      single_block.steps = (StepPatchList *)malloc(sizeof(StepPatchList));
      if (!single_block.steps) {
        fprintf(stderr, "malloc failed while loading %s\n", path);
        fclose(fp);
        free(parsed_step.items);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      single_block.steps[0] = parsed_step;
      single_block.step_count = 1U;
      single_block.repeat_count = 1U;
      if (append_script_block(&blocks, &block_count, &block_capacity, &single_block) != 0) {
        fprintf(stderr, "realloc failed while loading %s\n", path);
        fclose(fp);
        free(single_block.steps[0].items);
        free(single_block.steps);
        free_step_patch_blocks(blocks, block_count);
        return -1;
      }
      logical_step_count += 1U;
      record_count += 1U;
    }
  }

  if (ferror(fp)) {
    fprintf(stderr, "failed while reading %s\n", path);
    fclose(fp);
    free_step_patch_blocks(blocks, block_count);
    return -1;
  }
  fclose(fp);

  if (in_repeat_seq) {
    fprintf(stderr, "%s terminated before @end-repeat-seq\n", path);
    free(repeat_seq_block.steps);
    free_step_patch_blocks(blocks, block_count);
    return -1;
  }

  if (block_count == 0 || logical_step_count == 0) {
    fprintf(stderr, "%s contained no executable patch steps\n", path);
    free_step_patch_blocks(blocks, block_count);
    return -1;
  }

  *out_blocks = blocks;
  *out_block_count = block_count;
  *out_logical_step_count = logical_step_count;
  *out_record_count = record_count;
  return 0;
}

static int trace_stages_enabled(void) {
  const char *raw = getenv(ENV_TRACE_STAGES);
  return raw != NULL && raw[0] != '\0';
}

static int stage_timing_enabled(void) {
  const char *raw = getenv(ENV_STAGE_TIMING);
  return raw != NULL && raw[0] != '\0';
}

static int env_flag_enabled(const char *name) {
  const char *raw = getenv(name);
  return raw != NULL && raw[0] != '\0';
}

static int parse_size_t_env(const char *name, size_t *out) {
  const char *raw = getenv(name);
  char *end = NULL;
  unsigned long long value = 0;
  if (raw == NULL || raw[0] == '\0')
    return 0;
  value = strtoull(raw, &end, 0);
  if (end == raw || *end != '\0')
    return -1;
  *out = (size_t)value;
  return 1;
}

static int parse_unsigned_env(const char *name, unsigned *out) {
  const char *raw = getenv(name);
  char *end = NULL;
  unsigned long value = 0UL;
  if (raw == NULL || raw[0] == '\0')
    return 0;
  value = strtoul(raw, &end, 0);
  if (end == raw || *end != '\0' || value > 1000UL)
    return -1;
  *out = (unsigned)value;
  return 1;
}

static int parse_unsigned_env_with_max(const char *name, unsigned *out,
                                       unsigned long max_value) {
  const char *raw = getenv(name);
  char *end = NULL;
  unsigned long value = 0UL;
  if (raw == NULL || raw[0] == '\0')
    return 0;
  value = strtoul(raw, &end, 0);
  if (end == raw || *end != '\0' || value > max_value)
    return -1;
  *out = (unsigned)value;
  return 1;
}

typedef struct {
  const char *name;
  CUdeviceptr ptr;
  size_t bytes;
} TokenLoopAliasScanEntry;

static size_t checked_mul_size(size_t lhs, size_t rhs) {
  if (lhs == 0U || rhs == 0U)
    return 0U;
  if (lhs > SIZE_MAX / rhs)
    return 0U;
  return lhs * rhs;
}

static int device_range_contains(CUdeviceptr base, size_t bytes,
                                 CUdeviceptr ptr) {
  if (base == 0 || ptr == 0 || bytes == 0U)
    return 0;
  CUdeviceptr end = base + (CUdeviceptr)bytes;
  if (end < base)
    return ptr >= base;
  return ptr >= base && ptr < end;
}

static int device_ranges_overlap(CUdeviceptr base_a, size_t bytes_a,
                                 CUdeviceptr base_b, size_t bytes_b) {
  CUdeviceptr end_a = 0;
  CUdeviceptr end_b = 0;
  if (base_a == 0 || base_b == 0 || bytes_a == 0U || bytes_b == 0U)
    return 0;
  end_a = base_a + (CUdeviceptr)bytes_a;
  end_b = base_b + (CUdeviceptr)bytes_b;
  if (end_a < base_a || end_b < base_b)
    return 0;
  return base_a < end_b && base_b < end_a;
}

static void append_scan_name(char *buf, size_t buf_size, const char *name) {
  size_t len = strlen(buf);
  int written = 0;
  if (buf_size == 0U || len >= buf_size - 1U)
    return;
  written = snprintf(buf + len, buf_size - len, "%s%s",
                     len == 0U ? "" : ",", name ? name : "unknown");
  if (written < 0)
    return;
  if ((size_t)written >= buf_size - len)
    buf[buf_size - 1U] = '\0';
}

static void print_ordering_aware_token_loop_arg_table_alias_scan(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    const TokenLoopAliasScanEntry *entries,
    unsigned entry_count,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;
  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  size_t pair_values_bytes = pair_record_count;
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr pair_values_base = 0;
  CUdeviceptr record_addr = 0;
  CUdeviceptr adjacent_window_start = 0;
  size_t adjacent_window_bytes = 0U;
  unsigned adjacent_first = record > 1U ? record - 1U : 0U;
  unsigned adjacent_last = record + 4U;
  unsigned pointer_in_adjacent_window_count = 0U;
  unsigned range_overlap_adjacent_window_count = 0U;
  unsigned pointer_in_adjacent_window_non_pair_offsets_count = 0U;
  unsigned range_overlap_adjacent_window_non_pair_offsets_count = 0U;
  unsigned pair_offsets_alias_count = 0U;
  unsigned pair_offsets_overlap_count = 0U;
  unsigned pair_offsets_overlap_non_pair_offsets_count = 0U;
  unsigned diagnostic_allocation_count = 0U;
  unsigned diagnostic_allocation_pointer_in_adjacent_window_count = 0U;
  unsigned diagnostic_allocation_range_overlap_adjacent_window_count = 0U;
  unsigned diagnostic_allocation_pair_offsets_overlap_count = 0U;
  char alias_names[512];
  char overlap_names[512];
  char diagnostic_allocation_overlap_names[512];
  int scan_complete = 0;
  alias_names[0] = '\0';
  overlap_names[0] = '\0';
  diagnostic_allocation_overlap_names[0] = '\0';

  if (schedule && schedule->d_offsets) {
    if (adjacent_last >= schedule->record_count)
      adjacent_last = schedule->record_count > 0U
                          ? schedule->record_count - 1U
                          : 0U;
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        schedule->d_offsets +
        ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
    adjacent_window_start =
        schedule->d_offsets +
        ((CUdeviceptr)adjacent_first * (CUdeviceptr)sizeof(size_t));
    adjacent_window_bytes =
        (size_t)(adjacent_last - adjacent_first + 1U) * sizeof(size_t);
    scan_complete = entries != NULL && entry_count > 0U;
  }
  if (schedule && schedule->d_values) {
    pair_values_base = schedule->d_values + (CUdeviceptr)low_start;
  }

  if (entries) {
    for (unsigned i = 0U; i < entry_count; i++) {
      const TokenLoopAliasScanEntry *entry = &entries[i];
      int is_diagnostic_allocation =
          entry->name && strncmp(entry->name, "diagnostic_", 11) == 0;
      if (!entry->ptr)
        continue;
      if (is_diagnostic_allocation)
        diagnostic_allocation_count++;
      if (device_range_contains(adjacent_window_start, adjacent_window_bytes,
                                entry->ptr)) {
        pointer_in_adjacent_window_count++;
        if (entry->name && strcmp(entry->name, "pair_offsets") != 0)
          pointer_in_adjacent_window_non_pair_offsets_count++;
        if (is_diagnostic_allocation) {
          diagnostic_allocation_pointer_in_adjacent_window_count++;
          append_scan_name(diagnostic_allocation_overlap_names,
                           sizeof(diagnostic_allocation_overlap_names),
                           entry->name);
        }
        append_scan_name(alias_names, sizeof(alias_names), entry->name);
      }
      if (device_ranges_overlap(entry->ptr, entry->bytes,
                                adjacent_window_start,
                                adjacent_window_bytes)) {
        range_overlap_adjacent_window_count++;
        if (entry->name && strcmp(entry->name, "pair_offsets") != 0)
          range_overlap_adjacent_window_non_pair_offsets_count++;
        if (is_diagnostic_allocation) {
          diagnostic_allocation_range_overlap_adjacent_window_count++;
          append_scan_name(diagnostic_allocation_overlap_names,
                           sizeof(diagnostic_allocation_overlap_names),
                           entry->name);
        }
        append_scan_name(overlap_names, sizeof(overlap_names), entry->name);
      }
      if (entry->ptr == pair_offsets_base)
        pair_offsets_alias_count++;
      if (device_ranges_overlap(entry->ptr, entry->bytes, pair_offsets_base,
                                pair_offsets_bytes)) {
        pair_offsets_overlap_count++;
        if (entry->name && strcmp(entry->name, "pair_offsets") != 0)
          pair_offsets_overlap_non_pair_offsets_count++;
        if (is_diagnostic_allocation) {
          diagnostic_allocation_pair_offsets_overlap_count++;
          append_scan_name(diagnostic_allocation_overlap_names,
                           sizeof(diagnostic_allocation_overlap_names),
                           entry->name);
        }
      }
    }
  }

  printf("ordering_aware_token_loop_arg_table_alias_scan: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu adjacent_first=%u adjacent_last=%u adjacent_window_start=%llu adjacent_window_bytes=%zu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu pair_values_base=%llu pair_values_bytes=%zu launch_arg_count=%u pointer_in_adjacent_window_count=%u range_overlap_adjacent_window_count=%u pointer_in_adjacent_window_non_pair_offsets_count=%u range_overlap_adjacent_window_non_pair_offsets_count=%u pair_offsets_alias_count=%u pair_offsets_overlap_count=%u pair_offsets_overlap_non_pair_offsets_count=%u diagnostic_allocation_count=%u diagnostic_allocation_pointer_in_adjacent_window_count=%u diagnostic_allocation_range_overlap_adjacent_window_count=%u diagnostic_allocation_pair_offsets_overlap_count=%u diagnostic_allocation_overlap_names=%s alias_names=%s overlap_names=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         adjacent_first,
         adjacent_last,
         (unsigned long long)adjacent_window_start,
         adjacent_window_bytes,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         (unsigned long long)pair_values_base,
         pair_values_bytes,
         entry_count,
         pointer_in_adjacent_window_count,
         range_overlap_adjacent_window_count,
         pointer_in_adjacent_window_non_pair_offsets_count,
         range_overlap_adjacent_window_non_pair_offsets_count,
         pair_offsets_alias_count,
         pair_offsets_overlap_count,
         pair_offsets_overlap_non_pair_offsets_count,
         diagnostic_allocation_count,
         diagnostic_allocation_pointer_in_adjacent_window_count,
         diagnostic_allocation_range_overlap_adjacent_window_count,
         diagnostic_allocation_pair_offsets_overlap_count,
         diagnostic_allocation_overlap_names[0] != '\0'
             ? diagnostic_allocation_overlap_names
             : "none",
         alias_names[0] != '\0' ? alias_names : "none",
         overlap_names[0] != '\0' ? overlap_names : "none",
         scan_complete ? "true" : "false");
  fflush(stdout);
}

static int append_internal_writer_hit(char *names,
                                      size_t names_size,
                                      unsigned *hit_count,
                                      const char *name,
                                      CUdeviceptr target,
                                      CUdeviceptr window_start,
                                      size_t window_bytes,
                                      CUdeviceptr *first_target) {
  if (!device_range_contains(window_start, window_bytes, target))
    return 0;
  if (*hit_count == 0U && first_target)
    *first_target = target;
  (*hit_count)++;
  append_scan_name(names, names_size, name);
  return 1;
}

static void scan_storage_local_internal_writer_hit(
    char *names,
    size_t names_size,
    unsigned *hit_count,
    unsigned *checked_count,
    const char *name,
    CUdeviceptr d_storage,
    size_t storage_size,
    unsigned nstates,
    size_t local_offset,
    CUdeviceptr window_start,
    size_t window_bytes,
    CUdeviceptr *first_target) {
  if (!d_storage || storage_size == 0U || nstates == 0U)
    return;
  if (local_offset >= storage_size)
    return;
  for (unsigned state = 0U; state < nstates; state++) {
    CUdeviceptr target =
        d_storage + (CUdeviceptr)state * (CUdeviceptr)storage_size +
        (CUdeviceptr)local_offset;
    (*checked_count)++;
    append_internal_writer_hit(names, names_size, hit_count, name, target,
                               window_start, window_bytes, first_target);
  }
}

static void print_ordering_aware_token_loop_internal_writer_scan(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    FeedbackSetTable *sets,
    FeedbackEdgeTable *edges,
    FeedbackIncrementTable *increments,
    CUdeviceptr d_storage,
    size_t storage_size,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    int apply_phase_controls,
    int apply_feedback,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;
  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  CUdeviceptr adjacent_window_start = 0;
  size_t adjacent_window_bytes = 0U;
  unsigned adjacent_first = record > 1U ? record - 1U : 0U;
  unsigned adjacent_last = record + 4U;
  unsigned internal_writer_count = 0U;
  unsigned internal_writer_checked_count = 0U;
  CUdeviceptr first_internal_writer_target = 0;
  char internal_writer_names[512];
  int scan_complete = 0;
  internal_writer_names[0] = '\0';

  if (schedule && schedule->d_offsets) {
    if (adjacent_last >= schedule->record_count)
      adjacent_last = schedule->record_count > 0U
                          ? schedule->record_count - 1U
                          : 0U;
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        schedule->d_offsets +
        ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
    adjacent_window_start =
        schedule->d_offsets +
        ((CUdeviceptr)adjacent_first * (CUdeviceptr)sizeof(size_t));
    adjacent_window_bytes =
        (size_t)(adjacent_last - adjacent_first + 1U) * sizeof(size_t);
    scan_complete = d_storage != 0 && storage_size > 0U &&
                    pair_record_span > 0U && pair_record_count > 0U;
  }

  if (scan_complete) {
    if (apply_phase_controls && sets) {
      for (unsigned i = 0U; i < sets->set_count; i++) {
        unsigned phase = sets->phases ? sets->phases[i] : 0U;
        unsigned state = sets->states ? sets->states[i] : UINT_MAX;
        if (phase != current_phase || !sets->offsets)
          continue;
        if (state == UINT_MAX) {
          scan_storage_local_internal_writer_hit(
              internal_writer_names, sizeof(internal_writer_names),
              &internal_writer_count, &internal_writer_checked_count,
              "phase_set", d_storage, storage_size, nstates, sets->offsets[i],
              adjacent_window_start, adjacent_window_bytes,
              &first_internal_writer_target);
        } else if (state < nstates && sets->offsets[i] < storage_size) {
          CUdeviceptr target =
              d_storage + (CUdeviceptr)state * (CUdeviceptr)storage_size +
              (CUdeviceptr)sets->offsets[i];
          internal_writer_checked_count++;
          append_internal_writer_hit(
              internal_writer_names, sizeof(internal_writer_names),
              &internal_writer_count, "phase_set", target,
              adjacent_window_start, adjacent_window_bytes,
              &first_internal_writer_target);
        }
      }
    }

    if (schedule->offsets) {
      for (unsigned cycle = 0U; cycle < cycle_count; cycle++) {
        size_t cycle_base =
            (size_t)low_start + (size_t)cycle * (size_t)pair_record_span;
        for (unsigned i = 0U; i < low_count; i++) {
          size_t idx = cycle_base + (size_t)i;
          if (idx >= schedule->record_count)
            continue;
          scan_storage_local_internal_writer_hit(
              internal_writer_names, sizeof(internal_writer_names),
              &internal_writer_count, &internal_writer_checked_count,
              "low_patch", d_storage, storage_size, nstates,
              schedule->offsets[idx], adjacent_window_start,
              adjacent_window_bytes, &first_internal_writer_target);
        }
        for (unsigned i = 0U; i < high_count; i++) {
          size_t idx = cycle_base + (size_t)low_count + (size_t)i;
          if (idx >= schedule->record_count)
            continue;
          scan_storage_local_internal_writer_hit(
              internal_writer_names, sizeof(internal_writer_names),
              &internal_writer_count, &internal_writer_checked_count,
              "high_patch", d_storage, storage_size, nstates,
              schedule->offsets[idx], adjacent_window_start,
              adjacent_window_bytes, &first_internal_writer_target);
        }
      }
    }

    if (apply_feedback && edges && edges->dst_offsets) {
      for (unsigned i = 0U; i < edges->edge_count; i++) {
        scan_storage_local_internal_writer_hit(
            internal_writer_names, sizeof(internal_writer_names),
            &internal_writer_count, &internal_writer_checked_count,
            "feedback_copy", d_storage, storage_size, nstates,
            edges->dst_offsets[i], adjacent_window_start,
            adjacent_window_bytes, &first_internal_writer_target);
      }
    }

    if (apply_feedback && increments && increments->offsets) {
      for (unsigned i = 0U; i < increments->increment_count; i++) {
        scan_storage_local_internal_writer_hit(
            internal_writer_names, sizeof(internal_writer_names),
            &internal_writer_count, &internal_writer_checked_count,
            "feedback_increment", d_storage, storage_size, nstates,
            increments->offsets[i], adjacent_window_start,
            adjacent_window_bytes, &first_internal_writer_target);
      }
    }
  }

  printf("ordering_aware_token_loop_internal_pair_offset_table_writer_scan: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu adjacent_first=%u adjacent_last=%u adjacent_window_start=%llu adjacent_window_bytes=%zu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu internal_writer_found=%s internal_writer_count=%u internal_writer_checked_count=%u first_internal_writer_target=%llu internal_writer_names=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         adjacent_first,
         adjacent_last,
         (unsigned long long)adjacent_window_start,
         adjacent_window_bytes,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         internal_writer_count > 0U ? "true" : "false",
         internal_writer_count,
         internal_writer_checked_count,
         (unsigned long long)first_internal_writer_target,
         internal_writer_names[0] != '\0' ? internal_writer_names : "none",
         scan_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_pair_offset_device_write_watchpoint(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  unsigned adjacent_first = record > 1U ? record - 1U : 0U;
  unsigned adjacent_last = record + 4U;
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  CUdeviceptr adjacent_window_start = 0;
  size_t adjacent_window_bytes = 0U;
  if (schedule && schedule->d_offsets) {
    if (adjacent_last >= schedule->record_count)
      adjacent_last = schedule->record_count > 0U
                          ? schedule->record_count - 1U
                          : 0U;
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
    adjacent_window_start =
        pair_offsets_base +
        ((CUdeviceptr)adjacent_first * (CUdeviceptr)sizeof(size_t));
    adjacent_window_bytes =
        (size_t)(adjacent_last - adjacent_first + 1U) * sizeof(size_t);
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned long long stage = snapshot.counters[0];
  int watchpoint_complete = progress && stage == 100ULL;
  unsigned long long source_id = watchpoint_complete ? snapshot.counters[2] : 0ULL;
  unsigned long long observed_pair_offsets_base =
      watchpoint_complete ? snapshot.counters[3] : (unsigned long long)pair_offsets_base;
  unsigned long long first_target =
      watchpoint_complete ? snapshot.counters[4] : 0ULL;
  unsigned long long target_delta =
      watchpoint_complete ? snapshot.counters[5] : 0ULL;
  unsigned long long hit_mask =
      watchpoint_complete ? snapshot.counters[6] : 0ULL;
  unsigned long long stored_value = (hit_mask >> 8) & 0xffULL;
  unsigned long long store_width = (hit_mask >> 16) & 0xffULL;
  int write_source_found = watchpoint_complete && ((hit_mask & 1ULL) != 0ULL);
  const char *source_name =
      source_id == 10001ULL ? "high_patch_store_or_guard" : "unknown";

  printf("ordering_aware_token_loop_pair_offset_device_write_watchpoint: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu adjacent_first=%u adjacent_last=%u adjacent_window_start=%llu adjacent_window_bytes=%zu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu watchpoint_complete=%s source_checked_count=%u source_id=%llu checked_source_names=%s write_source_found=%s write_source_count=%u first_write_source_target=%llu first_write_source_delta=%llu hit_mask=%llu stored_value=%llu store_width=%llu write_source_names=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         adjacent_first,
         adjacent_last,
         (unsigned long long)adjacent_window_start,
         adjacent_window_bytes,
         pair_record_span,
         pair_record_count,
         observed_pair_offsets_base,
         pair_offsets_bytes,
         stage,
         watchpoint_complete ? "true" : "false",
         watchpoint_complete ? 1U : 0U,
         source_id,
         watchpoint_complete ? source_name : "none",
         write_source_found ? "true" : "false",
         write_source_found ? 1U : 0U,
         write_source_found ? first_target : 0ULL,
         write_source_found ? target_delta : 0ULL,
         hit_mask,
         stored_value,
         store_width,
         write_source_found ? source_name : "none",
         watchpoint_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_eval_callsite_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage101_base = ORDERING_AWARE_TOKEN_LOOP_STAGE101_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage101_base + 0U];
  int view_complete = progress && stage == 101ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage101_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long callee_index = (control_word >> 32) & 0xffffULL;
  unsigned long long eval_region_id = (control_word >> 48) & 0xffULL;
  unsigned long long event_kind_id = (control_word >> 56) & 0xffULL;
  unsigned long long entry_direct =
      view_complete ? snapshot.counters[stage101_base + 2U] : 0ULL;
  unsigned long long before_direct =
      view_complete ? snapshot.counters[stage101_base + 3U] : 0ULL;
  unsigned long long after_direct =
      view_complete ? snapshot.counters[stage101_base + 4U] : 0ULL;
  unsigned long long done_direct =
      view_complete ? snapshot.counters[stage101_base + 5U] : 0ULL;
  unsigned long long view_mask =
      view_complete ? snapshot.counters[stage101_base + 6U] : 0ULL;
  int before_after_changed = view_complete && ((view_mask & 1ULL) != 0ULL);
  int entry_before_changed = view_complete && ((view_mask & 2ULL) != 0ULL);
  int after_done_changed = view_complete && ((view_mask & 4ULL) != 0ULL);
  int clean_summary = view_complete && ((view_mask & 8ULL) != 0ULL);
  int eval_skipped = view_complete && event_kind_id == 3ULL;
  int eval_call_path_reached =
      view_complete && (event_kind_id == 1ULL || event_kind_id == 2ULL);
  int eval_predicate_active = view_complete && !eval_skipped;
  const char *eval_region =
      eval_region_id == 1ULL ? "low_eval" :
      eval_region_id == 2ULL ? "high_eval" : "unknown";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee_transition" :
      event_kind_id == 2ULL ? "eval_done_clean" :
      event_kind_id == 3ULL ? "eval_predicate_false" : "unknown";

  printf("ordering_aware_token_loop_eval_callsite_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu eval_region=%s eval_region_id=%llu event_kind=%s event_kind_id=%llu cycle_idx=%llu callee_index=%llu entry_direct_param_record318=%llu before_call_direct_param_record318=%llu after_call_direct_param_record318=%llu done_direct_param_record318=%llu view_mask=%llu before_after_changed=%s entry_before_changed=%s after_done_changed=%s clean_summary=%s eval_predicate_active=%s eval_call_path_reached=%s eval_skipped=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         eval_region,
         eval_region_id,
         event_kind,
         event_kind_id,
         cycle_idx,
         callee_index,
         entry_direct,
         before_direct,
         after_direct,
         done_direct,
         view_mask,
         before_after_changed ? "true" : "false",
         entry_before_changed ? "true" : "false",
         after_done_changed ? "true" : "false",
         clean_summary ? "true" : "false",
         eval_predicate_active ? "true" : "false",
         eval_call_path_reached ? "true" : "false",
         eval_skipped ? "true" : "false",
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_low_patch_to_low_eval_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage102_base = ORDERING_AWARE_TOKEN_LOOP_STAGE102_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage102_base + 0U];
  int view_complete = progress && stage == 102ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage102_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long low_patch_idx = (control_word >> 32) & 0xffffULL;
  unsigned long long boundary_kind_id = (control_word >> 56) & 0xffULL;
  unsigned long long cycle_entry_direct =
      view_complete ? snapshot.counters[stage102_base + 2U] : 0ULL;
  unsigned long long before_store_direct =
      view_complete ? snapshot.counters[stage102_base + 3U] : 0ULL;
  unsigned long long after_store_direct =
      view_complete ? snapshot.counters[stage102_base + 4U] : 0ULL;
  unsigned long long low_eval_entry_direct =
      view_complete ? snapshot.counters[stage102_base + 5U] : 0ULL;
  unsigned long long store_offset =
      view_complete ? snapshot.counters[stage102_base + 6U] : 0ULL;
  unsigned long long view_mask =
      view_complete ? snapshot.counters[stage102_base + 7U] : 0ULL;
  int cycle_entry_polluted = view_complete && ((view_mask & 1ULL) != 0ULL);
  int before_after_changed = view_complete && ((view_mask & 2ULL) != 0ULL);
  int low_eval_changed_from_cycle_entry =
      view_complete && ((view_mask & 4ULL) != 0ULL);
  int low_eval_entry_polluted = view_complete && ((view_mask & 8ULL) != 0ULL);
  const char *boundary_kind =
      boundary_kind_id == 1ULL ? "cycle_entry_already_polluted" :
      boundary_kind_id == 2ULL ? "low_patch_after_store_changed" :
      boundary_kind_id == 3ULL ? "low_eval_entry_changed_from_cycle_entry" :
                                 "unknown";

  printf("ordering_aware_token_loop_low_patch_to_low_eval_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu cycle_idx=%llu low_patch_idx=%llu cycle_entry_direct_param_record318=%llu before_store_direct_param_record318=%llu after_store_direct_param_record318=%llu low_eval_entry_direct_param_record318=%llu store_offset=%llu view_mask=%llu cycle_entry_polluted=%s before_after_changed=%s low_eval_changed_from_cycle_entry=%s low_eval_entry_polluted=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         cycle_idx,
         low_patch_idx,
         cycle_entry_direct,
         before_store_direct,
         after_store_direct,
         low_eval_entry_direct,
         store_offset,
         view_mask,
         cycle_entry_polluted ? "true" : "false",
         before_after_changed ? "true" : "false",
         low_eval_changed_from_cycle_entry ? "true" : "false",
         low_eval_entry_polluted ? "true" : "false",
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_pre_low_patch_cycle_entry_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage103_base = ORDERING_AWARE_TOKEN_LOOP_STAGE103_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage103_base + 0U];
  int view_complete = progress && stage == 103ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage103_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long first_polluted_checkpoint_id =
      (control_word >> 32) & 0xffULL;
  unsigned long long entry_direct =
      view_complete ? snapshot.counters[stage103_base + 2U] : 0ULL;
  unsigned long long state_setup_direct =
      view_complete ? snapshot.counters[stage103_base + 3U] : 0ULL;
  unsigned long long predicate_done_direct =
      view_complete ? snapshot.counters[stage103_base + 4U] : 0ULL;
  unsigned long long terminal_mask_done_direct =
      view_complete ? snapshot.counters[stage103_base + 5U] : 0ULL;
  unsigned long long phase_set_done_direct =
      view_complete ? snapshot.counters[stage103_base + 6U] : 0ULL;
  unsigned long long pre_cycle_cond_direct =
      view_complete ? snapshot.counters[stage103_base + 7U] : 0ULL;
  unsigned long long cycle_cond_direct =
      view_complete ? snapshot.counters[stage103_base + 8U] : 0ULL;
  unsigned long long cycle_entry_direct =
      view_complete ? snapshot.counters[stage103_base + 9U] : 0ULL;
  const char *first_polluted_checkpoint =
      first_polluted_checkpoint_id == 1ULL ? "entry" :
      first_polluted_checkpoint_id == 2ULL ? "state_setup" :
      first_polluted_checkpoint_id == 3ULL ? "predicate_done" :
      first_polluted_checkpoint_id == 4ULL ? "terminal_mask_done" :
      first_polluted_checkpoint_id == 5ULL ? "phase_set_done" :
      first_polluted_checkpoint_id == 6ULL ? "pre_cycle_cond" :
      first_polluted_checkpoint_id == 7ULL ? "cycle_cond" :
      first_polluted_checkpoint_id == 8ULL ? "cycle_entry" : "none";

  printf("ordering_aware_token_loop_pre_low_patch_cycle_entry_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu cycle_idx=%llu first_polluted_checkpoint=%s first_polluted_checkpoint_id=%llu entry_direct_param_record318=%llu state_setup_direct_param_record318=%llu predicate_done_direct_param_record318=%llu terminal_mask_done_direct_param_record318=%llu phase_set_done_direct_param_record318=%llu pre_cycle_cond_direct_param_record318=%llu cycle_cond_direct_param_record318=%llu cycle_entry_direct_param_record318=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         cycle_idx,
         first_polluted_checkpoint,
         first_polluted_checkpoint_id,
         entry_direct,
         state_setup_direct,
         predicate_done_direct,
         terminal_mask_done_direct,
         phase_set_done_direct,
         pre_cycle_cond_direct,
         cycle_cond_direct,
         cycle_entry_direct,
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_pre_cycle_cond_to_cycle_cond_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage104_base = ORDERING_AWARE_TOKEN_LOOP_STAGE104_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage104_base + 0U];
  int view_complete = progress && stage == 104ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage104_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long first_polluted_checkpoint_id =
      (control_word >> 32) & 0xffULL;
  unsigned long long pre_cycle_cond_direct =
      view_complete ? snapshot.counters[stage104_base + 2U] : 0ULL;
  unsigned long long cycle_cond_entry_direct =
      view_complete ? snapshot.counters[stage104_base + 3U] : 0ULL;
  unsigned long long typed_load_direct =
      view_complete ? snapshot.counters[stage104_base + 4U] : 0ULL;
  unsigned long long second_typed_load_direct =
      view_complete ? snapshot.counters[stage104_base + 5U] : 0ULL;
  unsigned long long raw_addr_reload_direct =
      view_complete ? snapshot.counters[stage104_base + 6U] : 0ULL;
  unsigned long long direct_param_reload =
      view_complete ? snapshot.counters[stage104_base + 7U] : 0ULL;
  unsigned long long byte_reassembled_direct =
      view_complete ? snapshot.counters[stage104_base + 8U] : 0ULL;
  unsigned long long after_progress_direct =
      view_complete ? snapshot.counters[stage104_base + 9U] : 0ULL;
  unsigned long long cycle_entry_direct =
      view_complete ? snapshot.counters[stage104_base + 10U] : 0ULL;
  unsigned long long view_mask =
      view_complete ? snapshot.counters[stage104_base + 11U] : 0ULL;
  const char *first_polluted_checkpoint =
      first_polluted_checkpoint_id == 1ULL ? "pre_cycle_cond" :
      first_polluted_checkpoint_id == 2ULL ? "cycle_cond_entry" :
      first_polluted_checkpoint_id == 3ULL ? "typed_load" :
      first_polluted_checkpoint_id == 4ULL ? "second_typed_load" :
      first_polluted_checkpoint_id == 5ULL ? "raw_addr_reload" :
      first_polluted_checkpoint_id == 6ULL ? "direct_param_reload" :
      first_polluted_checkpoint_id == 7ULL ? "byte_reassembled" :
      first_polluted_checkpoint_id == 8ULL ? "after_progress" :
      first_polluted_checkpoint_id == 9ULL ? "cycle_entry" : "none";

  printf("ordering_aware_token_loop_pre_cycle_cond_to_cycle_cond_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu cycle_idx=%llu first_polluted_checkpoint=%s first_polluted_checkpoint_id=%llu pre_cycle_cond_direct_param_record318=%llu cycle_cond_entry_direct_param_record318=%llu typed_load_direct_param_record318=%llu second_typed_load_direct_param_record318=%llu raw_addr_reload_direct_param_record318=%llu direct_param_reload_record318=%llu byte_reassembled_direct_param_record318=%llu after_progress_direct_param_record318=%llu cycle_entry_direct_param_record318=%llu view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         cycle_idx,
         first_polluted_checkpoint,
         first_polluted_checkpoint_id,
         pre_cycle_cond_direct,
         cycle_cond_entry_direct,
         typed_load_direct,
         second_typed_load_direct,
         raw_addr_reload_direct,
         direct_param_reload,
         byte_reassembled_direct,
         after_progress_direct,
         cycle_entry_direct,
         view_mask,
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_cycle_cond_entry_boundary_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage105_base = ORDERING_AWARE_TOKEN_LOOP_STAGE105_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage105_base + 0U];
  int view_complete = progress && stage == 105ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage105_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long first_polluted_checkpoint_id =
      (control_word >> 32) & 0xffULL;
  unsigned long long pre_cycle_cond_direct =
      view_complete ? snapshot.counters[stage105_base + 2U] : 0ULL;
  unsigned long long post_phi_direct =
      view_complete ? snapshot.counters[stage105_base + 3U] : 0ULL;
  unsigned long long after_control_direct =
      view_complete ? snapshot.counters[stage105_base + 4U] : 0ULL;
  unsigned long long cycle_cond_entry_direct =
      view_complete ? snapshot.counters[stage105_base + 5U] : 0ULL;
  unsigned long long cycle_entry_direct =
      view_complete ? snapshot.counters[stage105_base + 6U] : 0ULL;
  unsigned long long view_mask =
      view_complete ? snapshot.counters[stage105_base + 7U] : 0ULL;
  const char *first_polluted_checkpoint =
      first_polluted_checkpoint_id == 1ULL ? "pre_cycle_cond" :
      first_polluted_checkpoint_id == 2ULL ? "post_phi" :
      first_polluted_checkpoint_id == 3ULL ? "after_control_word" :
      first_polluted_checkpoint_id == 4ULL ? "cycle_cond_entry" :
      first_polluted_checkpoint_id == 5ULL ? "cycle_entry" : "none";

  printf("ordering_aware_token_loop_cycle_cond_entry_boundary_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu cycle_idx=%llu first_polluted_checkpoint=%s first_polluted_checkpoint_id=%llu pre_cycle_cond_direct_param_record318=%llu post_phi_direct_param_record318=%llu after_control_word_direct_param_record318=%llu cycle_cond_entry_direct_param_record318=%llu cycle_entry_direct_param_record318=%llu view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         cycle_idx,
         first_polluted_checkpoint,
         first_polluted_checkpoint_id,
         pre_cycle_cond_direct,
         post_phi_direct,
         after_control_direct,
         cycle_cond_entry_direct,
         cycle_entry_direct,
         view_mask,
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_cycle_cond_post_phi_edge_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage106_base = ORDERING_AWARE_TOKEN_LOOP_STAGE106_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage106_base + 0U];
  int view_complete = progress && stage == 106ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage106_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long first_polluted_checkpoint_id =
      (control_word >> 32) & 0xffULL;
  unsigned long long predecessor_id = (control_word >> 40) & 0xffULL;
  unsigned long long selected_edge_direct =
      view_complete ? snapshot.counters[stage106_base + 2U] : 0ULL;
  unsigned long long post_phi_direct =
      view_complete ? snapshot.counters[stage106_base + 3U] : 0ULL;
  int selected_edge_polluted =
      view_complete && selected_edge_direct != 0ULL;
  int post_phi_polluted =
      view_complete && post_phi_direct != 0ULL;
  int selected_post_phi_changed =
      view_complete && selected_edge_direct != post_phi_direct;
  const char *first_polluted_checkpoint =
      first_polluted_checkpoint_id == 1ULL ? "selected_edge" :
      first_polluted_checkpoint_id == 2ULL ? "post_phi" : "none";
  const char *predecessor_kind =
      predecessor_id == 1ULL ? "entry" :
      predecessor_id == 2ULL ? "backedge" : "unknown";

  printf("ordering_aware_token_loop_cycle_cond_post_phi_edge_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu cycle_idx=%llu predecessor_id=%llu predecessor_kind=%s first_polluted_checkpoint=%s first_polluted_checkpoint_id=%llu selected_edge_direct_param_record318=%llu post_phi_direct_param_record318=%llu selected_edge_polluted=%s post_phi_polluted=%s selected_post_phi_changed=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         cycle_idx,
         predecessor_id,
         predecessor_kind,
         first_polluted_checkpoint,
         first_polluted_checkpoint_id,
         selected_edge_direct,
         post_phi_direct,
         selected_edge_polluted ? "true" : "false",
         post_phi_polluted ? "true" : "false",
         selected_post_phi_changed ? "true" : "false",
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_cycle_cond_backedge_pre_branch_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage107_base = ORDERING_AWARE_TOKEN_LOOP_STAGE107_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage107_base + 0U];
  int view_complete = progress && stage == 107ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage107_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long first_polluted_checkpoint_id =
      (control_word >> 32) & 0xffULL;
  unsigned long long predecessor_id = (control_word >> 40) & 0xffULL;
  unsigned long long high_eval_entry =
      view_complete ? snapshot.counters[stage107_base + 2U] : 0ULL;
  unsigned long long selected_edge =
      view_complete ? snapshot.counters[stage107_base + 3U] : 0ULL;
  unsigned long long high_eval_done_entry =
      view_complete ? snapshot.counters[stage107_base + 4U] : 0ULL;
  unsigned long long high_eval_done_after_stage90 =
      view_complete ? snapshot.counters[stage107_base + 5U] : 0ULL;
  unsigned long long backedge_pre_branch =
      view_complete ? snapshot.counters[stage107_base + 6U] : 0ULL;
  unsigned long long view_mask =
      view_complete ? snapshot.counters[stage107_base + 7U] : 0ULL;
  int high_eval_entry_polluted = view_complete && high_eval_entry != 0ULL;
  int selected_edge_polluted = view_complete && selected_edge != 0ULL;
  int done_entry_polluted = view_complete && high_eval_done_entry != 0ULL;
  int after_stage90_polluted =
      view_complete && high_eval_done_after_stage90 != 0ULL;
  int pre_branch_polluted = view_complete && backedge_pre_branch != 0ULL;
  int selected_done_changed =
      view_complete && selected_edge != high_eval_done_entry;
  int done_stage90_changed =
      view_complete && high_eval_done_entry != high_eval_done_after_stage90;
  int after_stage90_pre_branch_changed =
      view_complete && high_eval_done_after_stage90 != backedge_pre_branch;
  const char *first_polluted_checkpoint =
      first_polluted_checkpoint_id == 1ULL ? "selected_edge" :
      first_polluted_checkpoint_id == 2ULL ? "high_eval_done_entry" :
      first_polluted_checkpoint_id == 3ULL ? "after_stage90_reload" :
      first_polluted_checkpoint_id == 4ULL ? "backedge_pre_branch" : "none";
  const char *predecessor_kind =
      predecessor_id == 1ULL ? "predicate_false" :
      predecessor_id == 2ULL ? "call_path" : "unknown";

  printf("ordering_aware_token_loop_cycle_cond_backedge_pre_branch_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu cycle_idx=%llu predecessor_id=%llu predecessor_kind=%s first_polluted_checkpoint=%s first_polluted_checkpoint_id=%llu high_eval_entry_direct_param_record318=%llu selected_high_eval_done_edge_direct_param_record318=%llu high_eval_done_entry_direct_param_record318=%llu high_eval_done_after_stage90_direct_param_record318=%llu backedge_pre_branch_direct_param_record318=%llu high_eval_entry_polluted=%s selected_edge_polluted=%s done_entry_polluted=%s after_stage90_polluted=%s pre_branch_polluted=%s selected_done_changed=%s done_stage90_changed=%s after_stage90_pre_branch_changed=%s view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         cycle_idx,
         predecessor_id,
         predecessor_kind,
         first_polluted_checkpoint,
         first_polluted_checkpoint_id,
         high_eval_entry,
         selected_edge,
         high_eval_done_entry,
         high_eval_done_after_stage90,
         backedge_pre_branch,
         high_eval_entry_polluted ? "true" : "false",
         selected_edge_polluted ? "true" : "false",
         done_entry_polluted ? "true" : "false",
         after_stage90_polluted ? "true" : "false",
         pre_branch_polluted ? "true" : "false",
         selected_done_changed ? "true" : "false",
         done_stage90_changed ? "true" : "false",
         after_stage90_pre_branch_changed ? "true" : "false",
         view_mask,
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_call_path_memory_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage108_base = ORDERING_AWARE_TOKEN_LOOP_STAGE108_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage108_base + 0U];
  int view_complete = progress && stage == 108ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage108_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long first_polluted_checkpoint_id =
      (control_word >> 32) & 0xffULL;
  unsigned long long control_callee_index = (control_word >> 40) & 0xffULL;
  unsigned long long high_eval_entry =
      view_complete ? snapshot.counters[stage108_base + 2U] : 0ULL;
  unsigned long long call_path_entry =
      view_complete ? snapshot.counters[stage108_base + 3U] : 0ULL;
  unsigned long long before_callee =
      view_complete ? snapshot.counters[stage108_base + 4U] : 0ULL;
  unsigned long long after_callee =
      view_complete ? snapshot.counters[stage108_base + 5U] : 0ULL;
  unsigned long long call_path_edge =
      view_complete ? snapshot.counters[stage108_base + 6U] : 0ULL;
  unsigned long long callee_index =
      view_complete ? snapshot.counters[stage108_base + 7U] : 0ULL;
  int high_eval_entry_polluted = view_complete && high_eval_entry != 0ULL;
  int call_path_entry_polluted = view_complete && call_path_entry != 0ULL;
  int before_callee_polluted = view_complete && before_callee != 0ULL;
  int after_callee_polluted = view_complete && after_callee != 0ULL;
  int call_path_edge_polluted = view_complete && call_path_edge != 0ULL;
  int entry_to_call_path_changed =
      view_complete && high_eval_entry != call_path_entry;
  int call_path_to_before_callee_changed =
      view_complete && call_path_entry != before_callee;
  int before_after_callee_changed =
      view_complete && before_callee != after_callee;
  int after_callee_to_edge_changed =
      view_complete && after_callee != call_path_edge;
  const char *first_polluted_checkpoint =
      first_polluted_checkpoint_id == 1ULL ? "call_path_entry" :
      first_polluted_checkpoint_id == 2ULL ? "before_callee" :
      first_polluted_checkpoint_id == 3ULL ? "after_callee" :
      first_polluted_checkpoint_id == 4ULL ? "call_path_edge" :
      first_polluted_checkpoint_id == 5ULL ? "high_eval_entry" : "none";

  printf("ordering_aware_token_loop_high_eval_call_path_memory_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu cycle_idx=%llu callee_index=%llu control_callee_index=%llu first_polluted_checkpoint=%s first_polluted_checkpoint_id=%llu high_eval_entry_direct_param_record318=%llu call_path_entry_direct_param_record318=%llu selected_before_callee_direct_param_record318=%llu selected_after_callee_direct_param_record318=%llu call_path_edge_direct_param_record318=%llu high_eval_entry_polluted=%s call_path_entry_polluted=%s before_callee_polluted=%s after_callee_polluted=%s call_path_edge_polluted=%s entry_to_call_path_changed=%s call_path_to_before_callee_changed=%s before_after_callee_changed=%s after_callee_to_edge_changed=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         cycle_idx,
         callee_index,
         control_callee_index,
         first_polluted_checkpoint,
         first_polluted_checkpoint_id,
         high_eval_entry,
         call_path_entry,
         before_callee,
         after_callee,
         call_path_edge,
         high_eval_entry_polluted ? "true" : "false",
         call_path_entry_polluted ? "true" : "false",
         before_callee_polluted ? "true" : "false",
         after_callee_polluted ? "true" : "false",
         call_path_edge_polluted ? "true" : "false",
         entry_to_call_path_changed ? "true" : "false",
         call_path_to_before_callee_changed ? "true" : "false",
         before_after_callee_changed ? "true" : "false",
         after_callee_to_edge_changed ? "true" : "false",
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee_callsite_pointer_view(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage109_base = ORDERING_AWARE_TOKEN_LOOP_STAGE109_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage109_base + 0U];
  int view_complete = progress && stage == 109ULL;
  unsigned long long control_word =
      view_complete ? snapshot.counters[stage109_base + 1U] : 0ULL;
  unsigned long long cycle_idx = control_word & 0xffffffffULL;
  unsigned long long callee_index = (control_word >> 32) & 0xffULL;
  unsigned long long split_result_id = (control_word >> 40) & 0xffULL;
  unsigned long long eval_region_id = (control_word >> 48) & 0xffULL;
  unsigned long long event_kind_id = (control_word >> 56) & 0xffULL;
  unsigned long long before_direct =
      view_complete ? snapshot.counters[stage109_base + 2U] : 0ULL;
  unsigned long long after_direct =
      view_complete ? snapshot.counters[stage109_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      view_complete ? snapshot.counters[stage109_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      view_complete ? snapshot.counters[stage109_base + 5U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      view_complete ? snapshot.counters[stage109_base + 6U] : 0ULL;
  unsigned long long callee_target_id =
      view_complete ? snapshot.counters[stage109_base + 7U] : 0ULL;
  int direct_before_after_changed =
      view_complete && before_direct != after_direct;
  int saved_after_polluted = view_complete && after_saved_addr != 0ULL;
  int direct_after_polluted = view_complete && after_direct != 0ULL;
  int param_int_changed =
      view_complete &&
      pair_offsets_param_int_before != pair_offsets_param_int_after;
  int direct_after_differs_from_saved_after =
      view_complete && after_direct != after_saved_addr;
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" : "incomplete";
  const char *eval_region = eval_region_id == 2ULL ? "high_eval" : "unknown";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee_callsite_pointer_view" : "unknown";

  printf("ordering_aware_token_loop_high_eval_callee_callsite_pointer_view: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu view_complete=%s control_word=%llu cycle_idx=%llu callee_index=%llu callee_target_id=%llu eval_region=%s eval_region_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu pair_offsets_param_int_after_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s split_result=%s split_result_id=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         view_complete ? "true" : "false",
         control_word,
         cycle_idx,
         callee_index,
         callee_target_id,
         eval_region,
         eval_region_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         split_result,
         split_result_id,
         view_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_body_pair_offset_store_watchpoint(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }
  unsigned adjacent_first = record > 0U ? record - 1U : record;
  unsigned adjacent_last = record + 4U;
  CUdeviceptr adjacent_window_start =
      pair_offsets_base + ((CUdeviceptr)adjacent_first * (CUdeviceptr)sizeof(size_t));
  size_t adjacent_window_bytes =
      (size_t)(adjacent_last - adjacent_first + 1U) * sizeof(size_t);

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage110_base = ORDERING_AWARE_TOKEN_LOOP_STAGE110_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage110_base + 0U];
  int watchpoint_complete = progress && stage == 110ULL;
  unsigned long long control_word =
      watchpoint_complete ? snapshot.counters[stage110_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long callee_index = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long recorded_pair_offsets_base =
      watchpoint_complete ? snapshot.counters[stage110_base + 2U] : 0ULL;
  unsigned long long target =
      watchpoint_complete ? snapshot.counters[stage110_base + 3U] : 0ULL;
  unsigned long long target_delta =
      watchpoint_complete ? snapshot.counters[stage110_base + 4U] : 0ULL;
  unsigned long long hit_mask =
      watchpoint_complete ? snapshot.counters[stage110_base + 5U] : 0ULL;
  unsigned long long source_checked_count =
      watchpoint_complete ? snapshot.counters[stage110_base + 6U] : 0ULL;
  unsigned long long stored_value =
      watchpoint_complete ? snapshot.counters[stage110_base + 7U] : 0ULL;
  unsigned long long store_width = (hit_mask >> 16) & 0xffffULL;
  int write_source_found = watchpoint_complete && (hit_mask & 1ULL) != 0ULL;
  int clean_no_body_store =
      watchpoint_complete && split_result_id == 2ULL && !write_source_found;
  const char *split_result =
      split_result_id == 1ULL ? "body_store_hit" :
      split_result_id == 2ULL ? "clean_no_body_store" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_body_store_hit" :
      event_kind_id == 2ULL ? "callee0_body_store_clean_summary" : "unknown";
  const char *write_source_names =
      write_source_found ? "high_eval_callee0_reachable_store" : "none";

  printf("ordering_aware_token_loop_high_eval_callee0_body_pair_offset_store_watchpoint: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu adjacent_first=%u adjacent_last=%u adjacent_window_start=%llu adjacent_window_bytes=%zu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu watchpoint_complete=%s control_word=%llu callee_index=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu recorded_pair_offsets_base=%llu target=%llu target_delta=%llu hit_mask=%llu stored_value=%llu store_width=%llu source_checked_count=%llu write_source_found=%s write_source_count=%u first_write_source_target=%llu first_write_source_delta=%llu write_source_names=%s clean_no_body_store=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         adjacent_first,
         adjacent_last,
         (unsigned long long)adjacent_window_start,
         adjacent_window_bytes,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         watchpoint_complete ? "true" : "false",
         control_word,
         callee_index,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         recorded_pair_offsets_base,
         target,
         target_delta,
         hit_mask,
         stored_value,
         store_width,
         source_checked_count,
         write_source_found ? "true" : "false",
         write_source_found ? 1U : 0U,
         write_source_found ? target : 0ULL,
         write_source_found ? target_delta : 0ULL,
         write_source_names,
         clean_no_body_store ? "true" : "false",
         watchpoint_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_pair_offset_boundary(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage111_base = ORDERING_AWARE_TOKEN_LOOP_STAGE111_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage111_base + 0U];
  int boundary_complete = progress && stage == 111ULL;
  unsigned long long control_word =
      boundary_complete ? snapshot.counters[stage111_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      boundary_complete ? snapshot.counters[stage111_base + 2U] : 0ULL;
  unsigned long long after_direct =
      boundary_complete ? snapshot.counters[stage111_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      boundary_complete ? snapshot.counters[stage111_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      boundary_complete ? snapshot.counters[stage111_base + 5U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      boundary_complete ? snapshot.counters[stage111_base + 6U] : 0ULL;
  unsigned long long view_mask =
      boundary_complete ? snapshot.counters[stage111_base + 7U] : 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int param_int_changed = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = boundary_complete && after_direct != 0ULL;
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_boundary_changed" : "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_pair_offset_boundary: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu boundary_complete=%s control_word=%llu nested_call_index=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu pair_offsets_param_int_after_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         boundary_complete ? "true" : "false",
         control_word,
         source_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         view_mask,
         boundary_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_pair_offset_store_watchpoint(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }
  unsigned adjacent_first = record > 0U ? record - 1U : record;
  unsigned adjacent_last = record + 4U;
  CUdeviceptr adjacent_window_start =
      pair_offsets_base + ((CUdeviceptr)adjacent_first * (CUdeviceptr)sizeof(size_t));
  size_t adjacent_window_bytes =
      (size_t)(adjacent_last - adjacent_first + 1U) * sizeof(size_t);

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);
  unsigned stage112_base = ORDERING_AWARE_TOKEN_LOOP_STAGE112_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage112_base + 0U];
  int watchpoint_complete = progress && stage == 112ULL;
  unsigned long long control_word =
      watchpoint_complete ? snapshot.counters[stage112_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long callee_nested_source_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long recorded_pair_offsets_base =
      watchpoint_complete ? snapshot.counters[stage112_base + 2U] : 0ULL;
  unsigned long long target =
      watchpoint_complete ? snapshot.counters[stage112_base + 3U] : 0ULL;
  unsigned long long target_delta =
      watchpoint_complete ? snapshot.counters[stage112_base + 4U] : 0ULL;
  unsigned long long hit_mask =
      watchpoint_complete ? snapshot.counters[stage112_base + 5U] : 0ULL;
  unsigned long long source_checked_count =
      watchpoint_complete ? snapshot.counters[stage112_base + 6U] : 0ULL;
  unsigned long long stored_value =
      watchpoint_complete ? snapshot.counters[stage112_base + 7U] : 0ULL;
  unsigned long long store_width = (hit_mask >> 16) & 0xffffULL;
  int write_source_found = watchpoint_complete && (hit_mask & 1ULL) != 0ULL;
  const char *split_result =
      split_result_id == 1ULL ? "nested_body_store_hit" :
      split_result_id == 2ULL ? "clean_no_nested_body_store" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_store_hit" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_store_clean_summary" : "unknown";
  const char *write_source_names =
      write_source_found ? "high_eval_callee0_nested_call_body_store" : "none";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_pair_offset_store_watchpoint: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu adjacent_first=%u adjacent_last=%u adjacent_window_start=%llu adjacent_window_bytes=%zu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu watchpoint_complete=%s control_word=%llu callee_nested_source_id=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu recorded_pair_offsets_base=%llu target=%llu target_delta=%llu hit_mask=%llu stored_value=%llu store_width=%llu source_checked_count=%llu write_source_found=%s write_source_count=%u first_write_source_target=%llu first_write_source_delta=%llu write_source_names=%s clean_no_nested_body_store=%s scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         adjacent_first,
         adjacent_last,
         (unsigned long long)adjacent_window_start,
         adjacent_window_bytes,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         watchpoint_complete ? "true" : "false",
         control_word,
         callee_nested_source_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         recorded_pair_offsets_base,
         target,
         target_delta,
         hit_mask,
         stored_value,
         store_width,
         source_checked_count,
         write_source_found ? "true" : "false",
         write_source_found ? 1U : 0U,
         write_source_found ? target : 0ULL,
         write_source_found ? target_delta : 0ULL,
         write_source_names,
         (watchpoint_complete && split_result_id == 2ULL && !write_source_found) ? "true" : "false",
         watchpoint_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_deeper_call_pair_offset_boundary(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage113_base = ORDERING_AWARE_TOKEN_LOOP_STAGE113_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage113_base + 0U];
  int boundary_complete = progress && stage == 113ULL;
  unsigned long long control_word =
      boundary_complete ? snapshot.counters[stage113_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long callee_nested_source_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      boundary_complete ? snapshot.counters[stage113_base + 2U] : 0ULL;
  unsigned long long after_direct =
      boundary_complete ? snapshot.counters[stage113_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      boundary_complete ? snapshot.counters[stage113_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      boundary_complete ? snapshot.counters[stage113_base + 5U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      boundary_complete ? snapshot.counters[stage113_base + 6U] : 0ULL;
  unsigned long long view_mask =
      boundary_complete ? snapshot.counters[stage113_base + 7U] : 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int param_int_changed = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = boundary_complete && after_direct != 0ULL;
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" :
      split_result_id == 5ULL ? "clean_no_deeper_call_boundary" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_deeper_call_boundary_changed" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_deeper_call_boundary_clean_summary" :
      "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_deeper_call_boundary: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu boundary_complete=%s control_word=%llu callee_nested_source_id=%llu deeper_call_index=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu pair_offsets_param_int_after_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s clean_no_deeper_call_boundary=%s view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         boundary_complete ? "true" : "false",
         control_word,
         callee_nested_source_id,
         source_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         (boundary_complete && split_result_id == 5ULL) ? "true" : "false",
         view_mask,
         boundary_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_non_store_effect_pair_offset_watchpoint(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage114_base = ORDERING_AWARE_TOKEN_LOOP_STAGE114_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage114_base + 0U];
  int watchpoint_complete = progress && stage == 114ULL;
  unsigned long long control_word =
      watchpoint_complete ? snapshot.counters[stage114_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long effect_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      watchpoint_complete ? snapshot.counters[stage114_base + 2U] : 0ULL;
  unsigned long long after_direct =
      watchpoint_complete ? snapshot.counters[stage114_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      watchpoint_complete ? snapshot.counters[stage114_base + 4U] : 0ULL;
  long long target_delta =
      watchpoint_complete ? (long long)snapshot.counters[stage114_base + 5U] : 0LL;
  unsigned long long source_checked_count =
      watchpoint_complete ? snapshot.counters[stage114_base + 6U] : 0ULL;
  unsigned long long view_mask =
      watchpoint_complete ? snapshot.counters[stage114_base + 7U] : 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int target_overlaps_window = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = watchpoint_complete && after_direct != 0ULL;
  const char *effect_kind =
      effect_kind_id == 1ULL ? "atomicrmw" :
      effect_kind_id == 2ULL ? "cmpxchg" :
      effect_kind_id == 3ULL ? "llvm_memory_intrinsic" :
      effect_kind_id == 0ULL ? "clean_summary" : "unknown";
  const char *split_result =
      split_result_id == 1ULL ? "target_window_overlap" :
      split_result_id == 2ULL ? "same_saved_addr_changed" :
      split_result_id == 3ULL ? "direct_view_only_changed" :
      split_result_id == 4ULL ? "clean_no_non_store_effect" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_non_store_effect_watchpoint_changed" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_non_store_effect_watchpoint_clean_summary" :
      "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_non_store_effect_watchpoint: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu watchpoint_complete=%s control_word=%llu effect_kind=%s effect_kind_id=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu target_delta=%lld source_checked_count=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s target_overlaps_window=%s direct_after_differs_from_saved_after=%s clean_no_non_store_effect=%s view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         watchpoint_complete ? "true" : "false",
         control_word,
         effect_kind,
         effect_kind_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         target_delta,
         source_checked_count,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         target_overlaps_window ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         (watchpoint_complete && split_result_id == 4ULL) ? "true" : "false",
         view_mask,
         watchpoint_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_residual_boundary(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage116_base = ORDERING_AWARE_TOKEN_LOOP_STAGE116_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage116_base + 0U];
  int boundary_complete = progress && stage == 116ULL;
  unsigned long long control_word =
      boundary_complete ? snapshot.counters[stage116_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      boundary_complete ? snapshot.counters[stage116_base + 2U] : 0ULL;
  unsigned long long after_direct =
      boundary_complete ? snapshot.counters[stage116_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      boundary_complete ? snapshot.counters[stage116_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      boundary_complete ? snapshot.counters[stage116_base + 5U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      boundary_complete ? snapshot.counters[stage116_base + 6U] : 0ULL;
  unsigned long long view_mask =
      boundary_complete ? snapshot.counters[stage116_base + 7U] : 0ULL;
  int clean_summary = boundary_complete && event_kind_id == 2ULL;
  unsigned long long source_checked_count = clean_summary ? view_mask : 0ULL;
  if (clean_summary)
    view_mask = 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int param_int_changed = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = boundary_complete && after_direct != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 1ULL ? "cfg_edge_entry_after_phi" : "unknown";
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" :
      split_result_id == 5ULL ? "clean_no_residual_boundary" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_residual_boundary_changed" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_residual_boundary_clean_summary" :
      "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_residual_boundary: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu boundary_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu pair_offsets_param_int_after_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s clean_no_residual_boundary=%s source_checked_count=%llu view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         boundary_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         (boundary_complete && split_result_id == 5ULL) ? "true" : "false",
         source_checked_count,
         view_mask,
         boundary_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_body_boundary(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage117_base = ORDERING_AWARE_TOKEN_LOOP_STAGE117_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage117_base + 0U];
  int boundary_complete = progress && stage == 117ULL;
  unsigned long long control_word =
      boundary_complete ? snapshot.counters[stage117_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      boundary_complete ? snapshot.counters[stage117_base + 2U] : 0ULL;
  unsigned long long after_direct =
      boundary_complete ? snapshot.counters[stage117_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      boundary_complete ? snapshot.counters[stage117_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      boundary_complete ? snapshot.counters[stage117_base + 5U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      boundary_complete ? snapshot.counters[stage117_base + 6U] : 0ULL;
  unsigned long long view_mask =
      boundary_complete ? snapshot.counters[stage117_base + 7U] : 0ULL;
  int clean_summary = boundary_complete && event_kind_id == 2ULL;
  unsigned long long source_checked_count = clean_summary ? view_mask : 0ULL;
  if (clean_summary)
    view_mask = 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int param_int_changed = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = boundary_complete && after_direct != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 2ULL ? "basic_block_entry_after_phi_to_pre_terminator" : "unknown";
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" :
      split_result_id == 5ULL ? "clean_no_block_body_boundary" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_block_body_boundary_changed" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_block_body_boundary_clean_summary" :
      "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_body_boundary: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu boundary_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu pair_offsets_param_int_after_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s clean_no_block_body_boundary=%s source_checked_count=%llu view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         boundary_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         (boundary_complete && split_result_id == 5ULL) ? "true" : "false",
         source_checked_count,
         view_mask,
         boundary_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_instruction_boundary(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage118_base = ORDERING_AWARE_TOKEN_LOOP_STAGE118_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage118_base + 0U];
  int boundary_complete = progress && stage == 118ULL;
  unsigned long long control_word =
      boundary_complete ? snapshot.counters[stage118_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      boundary_complete ? snapshot.counters[stage118_base + 2U] : 0ULL;
  unsigned long long after_direct =
      boundary_complete ? snapshot.counters[stage118_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      boundary_complete ? snapshot.counters[stage118_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      boundary_complete ? snapshot.counters[stage118_base + 5U] : 0ULL;
  unsigned long long block_source_id =
      boundary_complete ? snapshot.counters[stage118_base + 6U] : 0ULL;
  unsigned long long view_mask =
      boundary_complete ? snapshot.counters[stage118_base + 7U] : 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int param_int_changed = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = boundary_complete && after_direct != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 3ULL ? "intrablock_instruction_before_after" : "unknown";
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" :
      split_result_id == 5ULL ? "clean_no_instruction_boundary" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_block_instruction_boundary_changed" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_block_instruction_boundary_clean_summary" :
      "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_instruction_boundary: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu boundary_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu block_source_id=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         boundary_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         block_source_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         view_mask,
         boundary_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_boundary(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage119_base = ORDERING_AWARE_TOKEN_LOOP_STAGE119_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage119_base + 0U];
  int boundary_complete = progress && stage == 119ULL;
  unsigned long long control_word =
      boundary_complete ? snapshot.counters[stage119_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      boundary_complete ? snapshot.counters[stage119_base + 2U] : 0ULL;
  unsigned long long after_direct =
      boundary_complete ? snapshot.counters[stage119_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      boundary_complete ? snapshot.counters[stage119_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      boundary_complete ? snapshot.counters[stage119_base + 5U] : 0ULL;
  unsigned long long block_source_id =
      boundary_complete ? snapshot.counters[stage119_base + 6U] : 0ULL;
  unsigned long long view_mask =
      boundary_complete ? snapshot.counters[stage119_base + 7U] : 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int param_int_changed = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = boundary_complete && after_direct != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 4ULL ? "skipped_instruction_span_before_after" : "unknown";
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" :
      split_result_id == 5ULL ? "clean_no_skipped_span_boundary" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_block_skipped_span_boundary_changed" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_block_skipped_span_boundary_clean_summary" :
      "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_boundary: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu boundary_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu block_source_id=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         boundary_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         block_source_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         view_mask,
         boundary_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_instruction_boundary(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage120_base = ORDERING_AWARE_TOKEN_LOOP_STAGE120_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage120_base + 0U];
  int boundary_complete = progress && stage == 120ULL;
  unsigned long long control_word =
      boundary_complete ? snapshot.counters[stage120_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long split_result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      boundary_complete ? snapshot.counters[stage120_base + 2U] : 0ULL;
  unsigned long long after_direct =
      boundary_complete ? snapshot.counters[stage120_base + 3U] : 0ULL;
  unsigned long long after_saved_addr =
      boundary_complete ? snapshot.counters[stage120_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      boundary_complete ? snapshot.counters[stage120_base + 5U] : 0ULL;
  unsigned long long block_source_id =
      boundary_complete ? snapshot.counters[stage120_base + 6U] : 0ULL;
  unsigned long long view_mask =
      boundary_complete ? snapshot.counters[stage120_base + 7U] : 0ULL;
  int direct_before_after_changed = (view_mask & 1ULL) != 0ULL;
  int saved_after_polluted = (view_mask & 2ULL) != 0ULL;
  int param_int_changed = (view_mask & 4ULL) != 0ULL;
  int direct_after_differs_from_saved_after = (view_mask & 8ULL) != 0ULL;
  int direct_after_polluted = boundary_complete && after_direct != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 5ULL ? "skipped_span_instruction_before_after" :
      boundary_kind_id == 6ULL ? "skipped_span_edge_before_after" :
      boundary_kind_id == 7ULL ? "skipped_span_aggregate_edge_before_after" :
      boundary_kind_id == 8ULL ? "non_diagnostic_lifecycle_after_suppressed_span" : "unknown";
  const char *split_result =
      split_result_id == 1ULL ? "same_saved_addr_changed" :
      split_result_id == 2ULL ? "direct_view_only_changed" :
      split_result_id == 3ULL ? "param_int_changed" :
      split_result_id == 4ULL ? "target_identity_only" :
      split_result_id == 5ULL ? "clean_no_skipped_span_instruction_boundary" :
      split_result_id == 6ULL ? "after_only_polluted" : "incomplete";
  const char *event_kind =
      event_kind_id == 1ULL ? "callee0_nested_call_body_block_skipped_span_instruction_boundary_changed" :
      event_kind_id == 2ULL ? "callee0_nested_call_body_block_skipped_span_instruction_boundary_clean_summary" :
      "unknown";

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_instruction_boundary: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu boundary_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu block_source_id=%llu source_id=%llu split_result=%s split_result_id=%llu event_kind=%s event_kind_id=%llu before_direct_param_record318=%llu after_direct_param_record318=%llu after_saved_addr_record318=%llu pair_offsets_param_int_before_call=%llu direct_before_after_changed=%s saved_after_polluted=%s direct_after_polluted=%s param_int_changed=%s direct_after_differs_from_saved_after=%s view_mask=%llu scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         boundary_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         block_source_id,
         source_id,
         split_result,
         split_result_id,
         event_kind,
         event_kind_id,
         before_direct,
         after_direct,
         after_saved_addr,
         pair_offsets_param_int_before,
         direct_before_after_changed ? "true" : "false",
         saved_after_polluted ? "true" : "false",
         direct_after_polluted ? "true" : "false",
         param_int_changed ? "true" : "false",
         direct_after_differs_from_saved_after ? "true" : "false",
         view_mask,
         boundary_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_lifecycle_probe(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage122_base = ORDERING_AWARE_TOKEN_LOOP_STAGE122_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage122_base + 0U];
  int lifecycle_complete = progress && stage == 122ULL;
  unsigned long long control_word =
      lifecycle_complete ? snapshot.counters[stage122_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long store_width = ((control_word >> 48) & 0xffULL);
  unsigned long long write_source_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      lifecycle_complete ? snapshot.counters[stage122_base + 2U] : 0ULL;
  unsigned long long after_direct =
      lifecycle_complete ? snapshot.counters[stage122_base + 3U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      lifecycle_complete ? snapshot.counters[stage122_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      lifecycle_complete ? snapshot.counters[stage122_base + 5U] : 0ULL;
  unsigned long long target_delta =
      lifecycle_complete ? snapshot.counters[stage122_base + 6U] : 0ULL;
  unsigned long long view_mask =
      lifecycle_complete ? snapshot.counters[stage122_base + 7U] : 0ULL;
  int before_after_changed = (view_mask & 1ULL) != 0ULL;
  int after_polluted = (view_mask & 2ULL) != 0ULL;
  int pair_offsets_base_changed = (view_mask & 4ULL) != 0ULL;
  int target_in_record318_window = (view_mask & 8ULL) != 0ULL;
  int target_in_adjacent_window = (view_mask & 16ULL) != 0ULL;
  int target_is_store = (view_mask & 32ULL) != 0ULL;
  int target_is_atomic_or_mem_intrinsic = (view_mask & 64ULL) != 0ULL;
  int structurally_non_diagnostic = (view_mask & 128ULL) != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 8ULL ? "non_diagnostic_lifecycle_after_suppressed_span" : "unknown";
  const char *result =
      result_id == 1ULL ? "same_saved_addr_changed" :
      result_id == 2ULL ? "direct_view_only_changed" :
      result_id == 3ULL ? "param_int_changed" :
      result_id == 4ULL ? "target_identity_only" :
      result_id == 5ULL ? "clean_no_skipped_span_instruction_boundary" :
      result_id == 6ULL ? "after_only_polluted" : "incomplete";
  const char *write_source_kind =
      write_source_kind_id == 1ULL ? "store" :
      write_source_kind_id == 2ULL ? "atomic" :
      write_source_kind_id == 3ULL ? "mem_intrinsic" : "none";
  int write_source_found =
      lifecycle_complete &&
      (target_in_record318_window || target_in_adjacent_window) &&
      (target_is_store || target_is_atomic_or_mem_intrinsic);

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_lifecycle_probe: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu lifecycle_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu source_id=%llu result=%s result_id=%llu store_width=%llu write_source_kind=%s write_source_kind_id=%llu before_target_direct_param_record318=%llu after_target_direct_param_record318=%llu pair_offsets_param_int_before=%llu pair_offsets_param_int_after=%llu target_delta=%llu view_mask=%llu before_after_changed=%s after_polluted=%s pair_offsets_base_changed=%s target_in_record318_window=%s target_in_adjacent_window=%s target_is_store=%s target_is_atomic_or_mem_intrinsic=%s structurally_non_diagnostic=%s write_source_found=%s write_source_authority=runtime_pair_offset_window scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         lifecycle_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         source_id,
         result,
         result_id,
         store_width,
         write_source_kind,
         write_source_kind_id,
         before_direct,
         after_direct,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         target_delta,
         view_mask,
         before_after_changed ? "true" : "false",
         after_polluted ? "true" : "false",
         pair_offsets_base_changed ? "true" : "false",
         target_in_record318_window ? "true" : "false",
         target_in_adjacent_window ? "true" : "false",
         target_is_store ? "true" : "false",
         target_is_atomic_or_mem_intrinsic ? "true" : "false",
         structurally_non_diagnostic ? "true" : "false",
         write_source_found ? "true" : "false",
         lifecycle_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_concrete_write_window_probe(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage123_base = ORDERING_AWARE_TOKEN_LOOP_STAGE123_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage123_base + 0U];
  int probe_complete = progress && stage == 123ULL;
  unsigned long long control_word =
      probe_complete ? snapshot.counters[stage123_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long store_width = ((control_word >> 48) & 0xffULL);
  unsigned long long write_source_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      probe_complete ? snapshot.counters[stage123_base + 2U] : 0ULL;
  unsigned long long after_direct =
      probe_complete ? snapshot.counters[stage123_base + 3U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      probe_complete ? snapshot.counters[stage123_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      probe_complete ? snapshot.counters[stage123_base + 5U] : 0ULL;
  unsigned long long target_delta =
      probe_complete ? snapshot.counters[stage123_base + 6U] : 0ULL;
  unsigned long long view_mask =
      probe_complete ? snapshot.counters[stage123_base + 7U] : 0ULL;
  int before_after_changed = (view_mask & 1ULL) != 0ULL;
  int after_polluted = (view_mask & 2ULL) != 0ULL;
  int pair_offsets_base_changed = (view_mask & 4ULL) != 0ULL;
  int target_in_record318_window = (view_mask & 8ULL) != 0ULL;
  int target_in_adjacent_window = (view_mask & 16ULL) != 0ULL;
  int target_is_store = (view_mask & 32ULL) != 0ULL;
  int target_is_atomic_or_mem_intrinsic = (view_mask & 64ULL) != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 9ULL ? "post_suppression_concrete_write_window" : "unknown";
  const char *result =
      result_id == 1ULL ? "same_saved_addr_changed" :
      result_id == 2ULL ? "direct_view_only_changed" :
      result_id == 3ULL ? "param_int_changed" :
      result_id == 4ULL ? "target_identity_only" :
      result_id == 5ULL ? "clean_no_skipped_span_instruction_boundary" :
      result_id == 6ULL ? "after_only_polluted" : "incomplete";
  const char *write_source_kind =
      write_source_kind_id == 1ULL ? "store" :
      write_source_kind_id == 2ULL ? "atomic" :
      write_source_kind_id == 3ULL ? "mem_intrinsic" : "none";
  int write_source_found =
      probe_complete &&
      (target_in_record318_window || target_in_adjacent_window) &&
      (target_is_store || target_is_atomic_or_mem_intrinsic);

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_concrete_write_window_probe: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu probe_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu source_id=%llu result=%s result_id=%llu store_width=%llu write_source_kind=%s write_source_kind_id=%llu before_target_direct_param_record318=%llu after_target_direct_param_record318=%llu pair_offsets_param_int_before=%llu pair_offsets_param_int_after=%llu target_delta=%llu view_mask=%llu before_after_changed=%s after_polluted=%s pair_offsets_base_changed=%s target_in_record318_window=%s target_in_adjacent_window=%s target_is_store=%s target_is_atomic_or_mem_intrinsic=%s write_source_found=%s write_source_authority=runtime_pair_offset_window scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         probe_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         source_id,
         result,
         result_id,
         store_width,
         write_source_kind,
         write_source_kind_id,
         before_direct,
         after_direct,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         target_delta,
         view_mask,
         before_after_changed ? "true" : "false",
         after_polluted ? "true" : "false",
         pair_offsets_base_changed ? "true" : "false",
         target_in_record318_window ? "true" : "false",
         target_in_adjacent_window ? "true" : "false",
         target_is_store ? "true" : "false",
         target_is_atomic_or_mem_intrinsic ? "true" : "false",
         write_source_found ? "true" : "false",
         probe_complete ? "true" : "false");
  fflush(stdout);
}

static void print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_transition_probe(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    volatile unsigned long long *progress,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned cycle_count,
    unsigned current_phase,
    unsigned nstates,
    unsigned record) {
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;

  unsigned pair_record_span = low_count + high_count;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)pair_record_span);
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  CUdeviceptr pair_offsets_base = 0;
  CUdeviceptr record_addr = 0;
  if (schedule && schedule->d_offsets) {
    pair_offsets_base =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    record_addr =
        pair_offsets_base + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
  }

  struct ordering_aware_token_loop_progress_snapshot snapshot;
  memset(&snapshot, 0, sizeof(snapshot));
  if (progress)
    read_ordering_aware_token_loop_progress_snapshot(progress, &snapshot);

  unsigned stage124_base = ORDERING_AWARE_TOKEN_LOOP_STAGE124_PROGRESS_BASE;
  unsigned long long stage = snapshot.counters[stage124_base + 0U];
  int transition_complete = progress && stage == 124ULL;
  unsigned long long control_word =
      transition_complete ? snapshot.counters[stage124_base + 1U] : 0ULL;
  unsigned long long source_id = control_word & 0xffffffffULL;
  unsigned long long boundary_kind_id = ((control_word >> 32) & 0xffULL);
  unsigned long long result_id = ((control_word >> 40) & 0xffULL);
  unsigned long long event_kind_id = ((control_word >> 56) & 0xffULL);
  unsigned long long before_direct =
      transition_complete ? snapshot.counters[stage124_base + 2U] : 0ULL;
  unsigned long long after_direct =
      transition_complete ? snapshot.counters[stage124_base + 3U] : 0ULL;
  unsigned long long pair_offsets_param_int_before =
      transition_complete ? snapshot.counters[stage124_base + 4U] : 0ULL;
  unsigned long long pair_offsets_param_int_after =
      transition_complete ? snapshot.counters[stage124_base + 5U] : 0ULL;
  unsigned long long skipped_count =
      transition_complete ? snapshot.counters[stage124_base + 6U] : 0ULL;
  unsigned long long view_mask =
      transition_complete ? snapshot.counters[stage124_base + 7U] : 0ULL;
  int before_after_changed = (view_mask & 1ULL) != 0ULL;
  int after_polluted = (view_mask & 2ULL) != 0ULL;
  int pair_offsets_base_changed = (view_mask & 16ULL) != 0ULL;
  const char *boundary_kind =
      boundary_kind_id == 10ULL ? "post_suppression_record318_transition" : "unknown";
  const char *result =
      result_id == 1ULL ? "same_saved_addr_changed" :
      result_id == 2ULL ? "direct_view_only_changed" :
      result_id == 3ULL ? "param_int_changed" :
      result_id == 4ULL ? "target_identity_only" :
      result_id == 5ULL ? "clean_no_skipped_span_instruction_boundary" :
      result_id == 6ULL ? "after_only_polluted" : "incomplete";
  int transition_found =
      transition_complete && before_after_changed && after_polluted;

  printf("ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_transition_probe: requested=true diagnostic_point=%s current_phase=%u low_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u nstates=%u record=%u record_addr=%llu pair_record_span=%u pair_record_count=%zu pair_offsets_base=%llu pair_offsets_bytes=%zu progress_stage=%llu transition_complete=%s control_word=%llu boundary_kind=%s boundary_kind_id=%llu source_id=%llu result=%s result_id=%llu event_kind_id=%llu before_target_direct_param_record318=%llu after_target_direct_param_record318=%llu pair_offsets_param_int_before=%llu pair_offsets_param_int_after=%llu skipped_count=%llu view_mask=%llu before_after_changed=%s after_polluted=%s pair_offsets_base_changed=%s transition_found=%s write_source_authority=none scan_complete=%s semantic_authority=false\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         low_step,
         low_start,
         low_count,
         high_count,
         cycle_count,
         nstates,
         record,
         (unsigned long long)record_addr,
         pair_record_span,
         pair_record_count,
         (unsigned long long)pair_offsets_base,
         pair_offsets_bytes,
         stage,
         transition_complete ? "true" : "false",
         control_word,
         boundary_kind,
         boundary_kind_id,
         source_id,
         result,
         result_id,
         event_kind_id,
         before_direct,
         after_direct,
         pair_offsets_param_int_before,
         pair_offsets_param_int_after,
         skipped_count,
         view_mask,
         before_after_changed ? "true" : "false",
         after_polluted ? "true" : "false",
         pair_offsets_base_changed ? "true" : "false",
         transition_found ? "true" : "false",
         transition_complete ? "true" : "false");
  fflush(stdout);
}

static void maybe_print_ordering_aware_high_patch_offset_diagnostic(
    const char *diagnostic_point,
    ResidentPatchSchedule *schedule,
    CUfunction u64_load_probe_kfn,
    int u64_load_probe_module_idx,
    int token_loop_module_idx,
    CUdeviceptr d_pair_offsets,
    CUdeviceptr d_pair_values,
    CUdeviceptr d_storage,
    CUdeviceptr d_progress_global,
    size_t storage_size,
    unsigned low_step,
    unsigned low_start,
    unsigned low_count,
    unsigned high_count,
    unsigned current_phase,
    unsigned nstates) {
  unsigned record = 318U;
  size_t host_offset = 0U;
  size_t uploaded_offset = 0U;
  unsigned high_start = low_start + low_count;
  unsigned pair_record_span = low_count + high_count;
  unsigned high_patches_per_state =
      nstates != 0U ? high_count / nstates : 0U;
  unsigned record_pair_index = 0U;
  unsigned inferred_cycle_index = 0U;
  unsigned inferred_cycle_progress = 0U;
  unsigned inferred_high_record_index = 0U;
  unsigned inferred_high_state = 0U;
  unsigned inferred_high_patch_idx = 0U;
  unsigned expected_next_high_patch_idx = 0U;
  unsigned expected_next_high_patch_cond_record = 0U;
  int expected_next_high_patch_cond_record_valid = 0;
  int record_maps_to_high_patch = 0;
  int record_in_range = 0;
  int device_read_ok = 0;
  CUdeviceptr expected_pair_offsets = 0;
  CUdeviceptr load_addr = 0;
  CUdeviceptr expected_addr = 0;
  size_t pair_loaded_offset = 0U;
  unsigned char host_value = 0U;
  unsigned char pair_loaded_value = 0U;
  int pair_load_read_ok = 0;
  int pair_value_read_ok = 0;
  int pre_token_probe_available = u64_load_probe_kfn != NULL;
  int probe_token_loop_same_module =
      u64_load_probe_module_idx >= 0 && token_loop_module_idx >= 0 &&
      u64_load_probe_module_idx == token_loop_module_idx;
  int token_loop_arg_pack_pair_offsets_matches_probe =
      d_pair_offsets != 0 && d_pair_offsets == expected_pair_offsets;
  int token_loop_arg_pack_storage_matches_probe = d_storage != 0;
  int pre_token_probe_alloc_ok = 0;
  int pre_token_probe_launch_ok = 0;
  int pre_token_probe_sync_ok = 0;
  int pre_token_probe_read_ok = 0;
  int pre_token_probe_matches_pair = 0;
  int pre_token_probe_addr_matches_load_addr = 0;
  CUresult pre_token_probe_alloc_result = CUDA_ERROR_INVALID_VALUE;
  CUresult pre_token_probe_launch_result = CUDA_ERROR_INVALID_VALUE;
  CUresult pre_token_probe_sync_result = CUDA_ERROR_INVALID_VALUE;
  CUresult pre_token_probe_read_result = CUDA_ERROR_INVALID_VALUE;
  const char *pre_token_probe_launch_error = NULL;
  const char *pre_token_probe_sync_error = NULL;
  uint64_t pre_token_probe_values[3] = {0ULL, 0ULL, 0ULL};
  int d_pair_offsets_matches_expected = 0;
  int load_addr_matches_expected = 0;
  int loaded_offset_oob = 0;
  char adjacent_records[512];
  size_t adjacent_len = 0U;
  if (!env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC))
    return;
  if (parse_unsigned_env_with_max(
          ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC_RECORD,
          &record, (unsigned long)UINT_MAX) < 0) {
    fprintf(stderr, "bad %s (want unsigned integer)\n",
            ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC_RECORD);
    return;
  }
  record_in_range =
      schedule && schedule->offsets && schedule->d_offsets &&
      record < schedule->record_count;
  adjacent_records[0] = '\0';
    if (schedule && schedule->d_offsets && schedule->d_values) {
    expected_pair_offsets =
        schedule->d_offsets +
        ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
    d_pair_offsets_matches_expected = d_pair_offsets == expected_pair_offsets;
    token_loop_arg_pack_pair_offsets_matches_probe =
        d_pair_offsets == expected_pair_offsets;
  }
  if (record_in_range) {
    host_offset = schedule->offsets[record];
    if (schedule->values)
      host_value = (unsigned char)schedule->values[record];
    if (record >= low_start && pair_record_span != 0U) {
      unsigned cycle_record_offset = 0U;
      record_pair_index = record - low_start;
      inferred_cycle_index = record_pair_index / pair_record_span;
      inferred_cycle_progress = inferred_cycle_index + 1U;
      cycle_record_offset = record_pair_index % pair_record_span;
      if (cycle_record_offset >= low_count &&
          high_patches_per_state != 0U) {
        inferred_high_record_index = cycle_record_offset - low_count;
        inferred_high_state =
            inferred_high_record_index / high_patches_per_state;
        inferred_high_patch_idx =
            inferred_high_record_index % high_patches_per_state;
        record_maps_to_high_patch =
            inferred_high_record_index < high_count;
        expected_next_high_patch_idx = inferred_high_patch_idx + 1U;
        if (expected_next_high_patch_idx < high_patches_per_state) {
          expected_next_high_patch_cond_record =
              record + (expected_next_high_patch_idx - inferred_high_patch_idx);
          expected_next_high_patch_cond_record_valid = 1;
        }
      }
    }
    load_addr =
        d_pair_offsets +
        ((CUdeviceptr)record_pair_index * (CUdeviceptr)sizeof(size_t));
    expected_addr =
        schedule->d_offsets +
        ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t));
    load_addr_matches_expected = load_addr == expected_addr;
    CUresult copy_result = cuMemcpyDtoH(
        &uploaded_offset,
        schedule->d_offsets + ((CUdeviceptr)record * (CUdeviceptr)sizeof(size_t)),
        sizeof(uploaded_offset));
    device_read_ok = copy_result == CUDA_SUCCESS;
    if (!device_read_ok)
      uploaded_offset = 0U;
    if (d_pair_offsets) {
      copy_result = cuMemcpyDtoH(&pair_loaded_offset, load_addr,
                                 sizeof(pair_loaded_offset));
      pair_load_read_ok = copy_result == CUDA_SUCCESS;
      if (!pair_load_read_ok)
        pair_loaded_offset = 0U;
    }
    if (d_pair_values) {
      copy_result = cuMemcpyDtoH(&pair_loaded_value,
                                 d_pair_values + (CUdeviceptr)record_pair_index,
                                 sizeof(pair_loaded_value));
      pair_value_read_ok = copy_result == CUDA_SUCCESS;
      if (!pair_value_read_ok)
        pair_loaded_value = 0U;
    }
    if (pre_token_probe_available && d_pair_offsets) {
      CUdeviceptr d_probe_out = 0;
      unsigned record_pair_index_arg = record_pair_index;
      void *probe_params[] = {&d_pair_offsets, &record_pair_index_arg,
                              &d_probe_out};
      pre_token_probe_alloc_result =
          cuMemAlloc(&d_probe_out, sizeof(pre_token_probe_values));
      pre_token_probe_alloc_ok =
          pre_token_probe_alloc_result == CUDA_SUCCESS && d_probe_out != 0;
      if (pre_token_probe_alloc_ok) {
        (void)cuMemsetD8(d_probe_out, 0, sizeof(pre_token_probe_values));
        pre_token_probe_launch_result =
            cuLaunchKernel(u64_load_probe_kfn, 1, 1, 1, 1, 1, 1, 0, 0,
                           probe_params, NULL);
        pre_token_probe_launch_ok =
            pre_token_probe_launch_result == CUDA_SUCCESS;
        cuGetErrorName(pre_token_probe_launch_result,
                       &pre_token_probe_launch_error);
        if (pre_token_probe_launch_ok) {
          pre_token_probe_sync_result = cuCtxSynchronize();
          pre_token_probe_sync_ok =
              pre_token_probe_sync_result == CUDA_SUCCESS;
          cuGetErrorName(pre_token_probe_sync_result,
                         &pre_token_probe_sync_error);
          if (pre_token_probe_sync_ok) {
            pre_token_probe_read_result =
                cuMemcpyDtoH(pre_token_probe_values, d_probe_out,
                             sizeof(pre_token_probe_values));
            pre_token_probe_read_ok =
                pre_token_probe_read_result == CUDA_SUCCESS;
          }
        }
        (void)cuMemFree(d_probe_out);
      }
      if (pre_token_probe_read_ok) {
        pre_token_probe_matches_pair =
            pair_load_read_ok &&
            pre_token_probe_values[0] == (uint64_t)pair_loaded_offset;
        pre_token_probe_addr_matches_load_addr =
            pre_token_probe_values[1] == (uint64_t)load_addr;
      }
    }
    loaded_offset_oob = pair_load_read_ok && storage_size != 0U &&
                        pair_loaded_offset >= storage_size;
  }
  if (schedule && schedule->offsets && schedule->values &&
      schedule->d_offsets && schedule->d_values &&
      schedule->record_count > 0U) {
    unsigned adjacent_first = record > 1U ? record - 1U : 0U;
    unsigned adjacent_last = record + 4U;
    if (adjacent_last >= schedule->record_count)
      adjacent_last = schedule->record_count - 1U;
    for (unsigned adjacent = adjacent_first; adjacent <= adjacent_last;
         adjacent++) {
      size_t adjacent_uploaded_offset = 0U;
      unsigned char adjacent_uploaded_value = 0U;
      int adjacent_offset_ok =
          cuMemcpyDtoH(&adjacent_uploaded_offset,
                       schedule->d_offsets +
                           ((CUdeviceptr)adjacent * (CUdeviceptr)sizeof(size_t)),
                       sizeof(adjacent_uploaded_offset)) == CUDA_SUCCESS;
      int adjacent_value_ok =
          cuMemcpyDtoH(&adjacent_uploaded_value,
                       schedule->d_values + (CUdeviceptr)adjacent,
                       sizeof(adjacent_uploaded_value)) == CUDA_SUCCESS;
      int written = snprintf(
          adjacent_records + adjacent_len,
          sizeof(adjacent_records) - adjacent_len,
          "%s%u:%zu:%u:%zu:%u:%s",
          adjacent_len == 0U ? "" : ",",
          adjacent,
          schedule->offsets[adjacent],
          (unsigned)(unsigned char)schedule->values[adjacent],
          adjacent_offset_ok ? adjacent_uploaded_offset : 0U,
          adjacent_value_ok ? (unsigned)adjacent_uploaded_value : 0U,
          (adjacent_offset_ok && adjacent_value_ok) ? "true" : "false");
      if (written < 0)
        break;
      if ((size_t)written >= sizeof(adjacent_records) - adjacent_len) {
        adjacent_len = sizeof(adjacent_records) - 1U;
        break;
      }
      adjacent_len += (size_t)written;
    }
  }
  printf("ordering_aware_token_loop_high_patch_diagnostic: requested=true diagnostic_point=%s current_phase=%u record=%u record_in_range=%s low_step=%u low_start=%u low_count=%u high_start=%u high_count=%u nstates=%u pair_record_span=%u high_patches_per_state=%u record_pair_index=%u inferred_cycle_index=%u inferred_cycle_progress=%u inferred_high_record_index=%u inferred_high_state=%u inferred_high_patch_idx=%u expected_next_high_patch_idx=%u expected_next_high_patch_cond_record=%u expected_next_high_patch_cond_record_valid=%s progress_stage67_slot7_expected_semantics=high_patch_cond_record progress_stage67_write_sequence=epoch_begin_stage_slot5_slot6_slot7_epoch_end progress_stage67_stores_are_separate=true progress_stage67_progress_update_atomic=false progress_stage67_slot7_store_after_stage=true progress_stage67_epoch_begin_slot=8 progress_stage67_epoch_end_slot=9 progress_stage67_epoch_marker_encoding=high_patch_idx_u32_record_u32 progress_stage67_post_group_marker_slot=9 progress_stage67_post_group_marker_semantics=high_patch_cond_record_after_payload progress_stage67_sealed_read_requires_slot7_equals_epoch_end=true progress_stage67_sealed_read_requires_slot7_equals_epoch_end_record=true record_maps_to_high_patch=%s host_offset=%zu uploaded_offset=%zu upload_read_ok=%s expected_offset=0 expected_record_token=@0:0:1 d_offsets_base=%llu d_pair_offsets=%llu expected_pair_offsets=%llu d_pair_offsets_matches_expected=%s load_addr=%llu expected_addr=%llu load_addr_matches_expected=%s pair_loaded_offset=%zu pair_load_read_ok=%s pair_loaded_value=%u pair_value_read_ok=%s host_value=%u pair_loaded_offset_matches_upload=%s pre_token_probe_available=%s pre_token_probe_alloc_ok=%s pre_token_probe_launch_ok=%s pre_token_probe_launch_error=%s pre_token_probe_sync_ok=%s pre_token_probe_sync_error=%s pre_token_probe_read_ok=%s pre_token_probe_value=%llu pre_token_probe_addr=%llu pre_token_probe_index=%llu pre_token_probe_matches_pair=%s pre_token_probe_addr_matches_load_addr=%s probe_module_idx=%d token_loop_module_idx=%d probe_token_loop_same_module=%s token_loop_arg_pack_storage=%llu token_loop_arg_pack_pair_offsets=%llu token_loop_arg_pack_pair_values=%llu token_loop_arg_pack_progress_global=%llu token_loop_arg_pack_provenance=token_loop_launch_args token_loop_arg_pack_pair_offsets_matches_probe=%s token_loop_arg_pack_storage_matches_probe=%s storage_size=%zu loaded_offset_oob=%s adjacent_records=%s\n",
         diagnostic_point ? diagnostic_point : "unspecified",
         current_phase,
         record,
         record_in_range ? "true" : "false",
         low_step,
         low_start,
         low_count,
         high_start,
         high_count,
         nstates,
         pair_record_span,
         high_patches_per_state,
         record_pair_index,
         inferred_cycle_index,
         inferred_cycle_progress,
         inferred_high_record_index,
         inferred_high_state,
         inferred_high_patch_idx,
         expected_next_high_patch_idx,
         expected_next_high_patch_cond_record,
         expected_next_high_patch_cond_record_valid ? "true" : "false",
         record_maps_to_high_patch ? "true" : "false",
         host_offset,
         uploaded_offset,
         device_read_ok ? "true" : "false",
         (unsigned long long)(schedule ? schedule->d_offsets : 0),
         (unsigned long long)d_pair_offsets,
         (unsigned long long)expected_pair_offsets,
         d_pair_offsets_matches_expected ? "true" : "false",
         (unsigned long long)load_addr,
         (unsigned long long)expected_addr,
         load_addr_matches_expected ? "true" : "false",
         pair_loaded_offset,
         pair_load_read_ok ? "true" : "false",
         (unsigned)pair_loaded_value,
         pair_value_read_ok ? "true" : "false",
         (unsigned)host_value,
         (pair_load_read_ok && pair_loaded_offset == uploaded_offset)
             ? "true"
             : "false",
         pre_token_probe_available ? "true" : "false",
         pre_token_probe_alloc_ok ? "true" : "false",
         pre_token_probe_launch_ok ? "true" : "false",
         pre_token_probe_launch_error ? pre_token_probe_launch_error : "not_run",
         pre_token_probe_sync_ok ? "true" : "false",
         pre_token_probe_sync_error ? pre_token_probe_sync_error : "not_run",
         pre_token_probe_read_ok ? "true" : "false",
         (unsigned long long)pre_token_probe_values[0],
         (unsigned long long)pre_token_probe_values[1],
         (unsigned long long)pre_token_probe_values[2],
         pre_token_probe_matches_pair ? "true" : "false",
         pre_token_probe_addr_matches_load_addr ? "true" : "false",
         u64_load_probe_module_idx,
         token_loop_module_idx,
         probe_token_loop_same_module ? "true" : "false",
         (unsigned long long)d_storage,
         (unsigned long long)d_pair_offsets,
         (unsigned long long)d_pair_values,
         (unsigned long long)d_progress_global,
         token_loop_arg_pack_pair_offsets_matches_probe ? "true" : "false",
         token_loop_arg_pack_storage_matches_probe ? "true" : "false",
         storage_size,
         loaded_offset_oob ? "true" : "false",
         adjacent_records[0] != '\0' ? adjacent_records : "none");
  fflush(stdout);
}

static int split_csv_dup(const char *raw, char **out, unsigned *out_count,
                         unsigned max_count) {
  char *buf = NULL;
  unsigned count = 0U;
  if (raw == NULL || raw[0] == '\0') {
    *out_count = 0U;
    return 0;
  }
  buf = strdup(raw);
  if (!buf) {
    fprintf(stderr, "strdup failed for csv env\n");
    return -1;
  }
  for (char *tok = strtok(buf, ","); tok != NULL; tok = strtok(NULL, ",")) {
    while (*tok && isspace((unsigned char)*tok))
      tok++;
    char *end = tok + strlen(tok);
    while (end > tok && isspace((unsigned char)end[-1]))
      *--end = '\0';
    if (*tok == '\0')
      continue;
    if (count >= max_count) {
      fprintf(stderr, "too many csv entries (max %u)\n", max_count);
      free(buf);
      return -1;
    }
    out[count] = strdup(tok);
    if (!out[count]) {
      fprintf(stderr, "strdup failed for csv token\n");
      free(buf);
      return -1;
    }
    count++;
  }
  free(buf);
  *out_count = count;
  return 0;
}

static void free_string_list(char **items, unsigned count) {
  for (unsigned i = 0U; i < count; i++) {
    free(items[i]);
    items[i] = NULL;
  }
}

static int dump_device_storage(CUdeviceptr d_storage, size_t total,
                               const char *dump_path) {
  unsigned char *host = NULL;
  FILE *fp = NULL;
  size_t nw = 0U;
  if (dump_path == NULL || dump_path[0] == '\0')
    return 0;
  host = (unsigned char *)malloc(total);
  if (!host) {
    fprintf(stderr, "malloc failed for %zu-byte state dump\n", total);
    return 1;
  }
  CUDA_CHECK(cuMemcpyDtoH(host, d_storage, total));
  fp = fopen(dump_path, "wb");
  if (!fp) {
    fprintf(stderr, "fopen(%s) failed\n", dump_path);
    free(host);
    return 1;
  }
  nw = fwrite(host, 1, total, fp);
  fclose(fp);
  free(host);
  if (nw != total) {
    fprintf(stderr, "short write to %s: wrote %zu / %zu bytes\n", dump_path,
            nw, total);
    return 1;
  }
  return 0;
}

static void close_step_trace(StepTrace *trace) {
  free(trace->coalesced_buf);
  trace->coalesced_buf = NULL;
  free(trace->host_coalesced_rows);
  trace->host_coalesced_rows = NULL;
  if (trace->d_coalesced_rows) {
    (void)cuMemFree(trace->d_coalesced_rows);
    trace->d_coalesced_rows = 0;
  }
  free(trace->host_rows);
  trace->host_rows = NULL;
  if (trace->d_rows) {
    (void)cuMemFree(trace->d_rows);
    trace->d_rows = 0;
  }
  trace->coalesced_base = 0U;
  trace->coalesced_span = 0U;
  trace->trace_start = 0U;
  trace->trace_stride = 1U;
  trace->row_count = 0U;
  trace->row_capacity = 0U;
  if (trace->fp) {
    fclose(trace->fp);
    trace->fp = NULL;
  }
}

static int flush_step_trace(StepTrace *trace) {
  if (!trace->fp || trace->flushed)
    return 0;
  if (trace->device_buffered) {
    size_t value_count = (size_t)trace->row_capacity * trace->field_count;
    if (trace->row_count > trace->row_capacity)
      return -1;
    if (trace->d_coalesced_rows) {
      size_t coalesced_bytes =
          (size_t)trace->row_capacity * trace->coalesced_span;
      if (coalesced_bytes > 0U) {
        CUDA_CHECK(cuMemcpyDtoH(trace->host_coalesced_rows,
                                trace->d_coalesced_rows, coalesced_bytes));
      }
    } else if (value_count > 0U) {
      CUDA_CHECK(cuMemcpyDtoH(trace->host_rows, trace->d_rows,
                              value_count * sizeof(*trace->host_rows)));
    }
  }
  if (trace->device_buffered) {
    fprintf(trace->fp, "step");
    for (unsigned i = 0U; i < trace->field_count; i++)
      fprintf(trace->fp, ",%s", trace->fields[i].name);
    fprintf(trace->fp, "\n");
    for (unsigned row_idx = 0U; row_idx < trace->row_count; row_idx++) {
      fprintf(trace->fp, "%u", row_idx);
      for (unsigned field_idx = 0U; field_idx < trace->field_count; field_idx++) {
        unsigned long long value = 0ULL;
        if (trace->host_coalesced_rows) {
          StepTraceField *field = &trace->fields[field_idx];
          size_t row_base = (size_t)row_idx * trace->coalesced_span;
          size_t field_base = field->offset - trace->coalesced_base;
          unsigned char *src =
              trace->host_coalesced_rows + row_base + field_base;
          for (size_t byte_idx = 0U; byte_idx < field->size; byte_idx++)
            value |= ((unsigned long long)src[byte_idx]) << (8U * byte_idx);
        } else {
          size_t value_idx = ((size_t)row_idx * trace->field_count) + field_idx;
          value = trace->host_rows[value_idx];
        }
        fprintf(trace->fp, ",0x%llx", value);
      }
      fprintf(trace->fp, "\n");
    }
  }
  trace->flushed = 1;
  return ferror(trace->fp) ? -1 : 0;
}

static int parse_step_trace_field(const char *raw, StepTraceField *field) {
  char buf[256];
  char *name = NULL;
  char *offset_s = NULL;
  char *size_s = NULL;
  char *end = NULL;
  unsigned long long offset = 0ULL;
  unsigned long long size = 0ULL;
  if (!raw || raw[0] == '\0' || strlen(raw) >= sizeof(buf))
    return -1;
  strcpy(buf, raw);
  name = buf;
  offset_s = strchr(name, ':');
  if (!offset_s)
    return -1;
  *offset_s++ = '\0';
  size_s = strchr(offset_s, ':');
  if (!size_s)
    return -1;
  *size_s++ = '\0';
  if (name[0] == '\0' || strlen(name) >= MAX_STEP_TRACE_NAME)
    return -1;
  offset = strtoull(offset_s, &end, 0);
  if (end == offset_s || *end != '\0')
    return -1;
  size = strtoull(size_s, &end, 0);
  if (end == size_s || *end != '\0' || size == 0ULL || size > 8ULL)
    return -1;
  snprintf(field->name, sizeof(field->name), "%s", name);
  field->offset = (size_t)offset;
  field->size = (size_t)size;
  return 0;
}

static int open_step_trace(StepTrace *trace, size_t total,
                           unsigned expected_rows) {
  const char *path = getenv(ENV_STEP_TRACE);
  char *field_specs[MAX_STEP_TRACE_FIELDS];
  unsigned field_count = 0U;
  unsigned trace_start = 0U;
  unsigned trace_stride = 1U;
  size_t min_offset = 0U;
  size_t max_end = 0U;
  memset(trace, 0, sizeof(*trace));
  trace->trace_stride = 1U;
  memset(field_specs, 0, sizeof(field_specs));
  if (!path || path[0] == '\0')
    return 0;
  if (parse_unsigned_env(ENV_STEP_TRACE_START, &trace_start) < 0) {
    fprintf(stderr, "bad %s (want unsigned integer)\n", ENV_STEP_TRACE_START);
    return -1;
  }
  if (parse_unsigned_env(ENV_STEP_TRACE_STRIDE, &trace_stride) < 0 ||
      trace_stride == 0U) {
    fprintf(stderr, "bad %s (want positive unsigned integer)\n",
            ENV_STEP_TRACE_STRIDE);
    return -1;
  }
  trace->trace_start = trace_start;
  trace->trace_stride = trace_stride;
  if (split_csv_dup(getenv(ENV_STEP_TRACE_FIELDS), field_specs, &field_count,
                    MAX_STEP_TRACE_FIELDS) != 0) {
    return -1;
  }
  if (field_count == 0U) {
    fprintf(stderr, "%s requires %s\n", ENV_STEP_TRACE, ENV_STEP_TRACE_FIELDS);
    return -1;
  }
  for (unsigned i = 0U; i < field_count; i++) {
    if (parse_step_trace_field(field_specs[i], &trace->fields[i]) != 0) {
      fprintf(stderr, "bad %s field '%s' (want name:offset:size)\n",
              ENV_STEP_TRACE_FIELDS, field_specs[i]);
      free_string_list(field_specs, field_count);
      return -1;
    }
    if (trace->fields[i].offset + trace->fields[i].size > total) {
      fprintf(stderr, "%s field '%s' out of range\n", ENV_STEP_TRACE_FIELDS,
              trace->fields[i].name);
      free_string_list(field_specs, field_count);
      return -1;
    }
  }
  free_string_list(field_specs, field_count);
  for (unsigned i = 0U; i < field_count; i++) {
    size_t offset = trace->fields[i].offset;
    size_t end = offset + trace->fields[i].size;
    if (i == 0U || offset < min_offset)
      min_offset = offset;
    if (end > max_end)
      max_end = end;
  }
  if (field_count > 0U && max_end >= min_offset &&
      max_end - min_offset <= MAX_STEP_TRACE_COALESCE_SPAN_BYTES) {
    trace->coalesced_base = min_offset;
    trace->coalesced_span = max_end - min_offset;
    trace->coalesced_buf = (unsigned char *)malloc(trace->coalesced_span);
    if (!trace->coalesced_buf) {
      fprintf(stderr, "malloc failed for step trace coalesced buffer\n");
      return -1;
    }
  }
  trace->fp = fopen(path, "w");
  if (!trace->fp) {
    close_step_trace(trace);
    fprintf(stderr, "fopen(%s) failed\n", path);
    return -1;
  }
  trace->field_count = field_count;
  trace->device_buffered = getenv(ENV_STEP_TRACE_DEVICE_BUFFER) != NULL;
  if (trace->device_buffered) {
    size_t value_count = (size_t)expected_rows * trace->field_count;
    if (expected_rows == 0U || value_count / trace->field_count != expected_rows) {
      fprintf(stderr, "%s requires a positive bounded step count\n",
              ENV_STEP_TRACE_DEVICE_BUFFER);
      close_step_trace(trace);
      return -1;
    }
    trace->row_capacity = expected_rows;
    if (trace->coalesced_span > 0U) {
      size_t coalesced_bytes = (size_t)expected_rows * trace->coalesced_span;
      if (coalesced_bytes / trace->coalesced_span != expected_rows) {
        fprintf(stderr, "device-buffered coalesced step trace size overflow\n");
        close_step_trace(trace);
        return -1;
      }
      trace->host_coalesced_rows =
          (unsigned char *)calloc(coalesced_bytes, sizeof(*trace->host_coalesced_rows));
      if (!trace->host_coalesced_rows) {
        fprintf(stderr, "calloc failed for coalesced step trace rows\n");
        close_step_trace(trace);
        return -1;
      }
      CUDA_CHECK(cuMemAlloc(&trace->d_coalesced_rows, coalesced_bytes));
      CUDA_CHECK(cuMemsetD8(trace->d_coalesced_rows, 0, coalesced_bytes));
    } else {
      trace->host_rows = (unsigned long long *)calloc(value_count,
                                                     sizeof(*trace->host_rows));
      if (!trace->host_rows) {
        fprintf(stderr, "calloc failed for device-buffered step trace rows\n");
        close_step_trace(trace);
        return -1;
      }
      CUDA_CHECK(cuMemAlloc(&trace->d_rows, value_count * sizeof(*trace->host_rows)));
      CUDA_CHECK(cuMemsetD8(trace->d_rows, 0, value_count * sizeof(*trace->host_rows)));
    }
  } else {
    fprintf(trace->fp, "step");
    for (unsigned i = 0U; i < trace->field_count; i++)
      fprintf(trace->fp, ",%s", trace->fields[i].name);
    fprintf(trace->fp, "\n");
  }
  return 0;
}

static int should_write_step_trace(StepTrace *trace, unsigned step) {
  if (!trace->fp)
    return 0;
  if (step < trace->trace_start)
    return 0;
  return ((step - trace->trace_start) % trace->trace_stride) == 0U;
}

static int write_step_trace(StepTrace *trace, CUdeviceptr d_storage,
                            unsigned step) {
  if (!should_write_step_trace(trace, step))
    return 0;
  if (trace->device_buffered) {
    if (trace->row_count >= trace->row_capacity) {
      fprintf(stderr, "device-buffered step trace exceeded expected rows\n");
      return -1;
    }
    if (trace->d_coalesced_rows) {
      CUdeviceptr dst =
          trace->d_coalesced_rows +
          (CUdeviceptr)((size_t)trace->row_count * trace->coalesced_span);
      CUDA_CHECK(cuMemcpyDtoDAsync(dst,
                                   d_storage + (CUdeviceptr)trace->coalesced_base,
                                   trace->coalesced_span, 0));
      trace->row_count++;
      return 0;
    }
    for (unsigned i = 0U; i < trace->field_count; i++) {
      StepTraceField *field = &trace->fields[i];
      CUdeviceptr dst =
          trace->d_rows +
          (CUdeviceptr)((((size_t)trace->row_count * trace->field_count) + i) *
                        sizeof(unsigned long long));
      CUDA_CHECK(cuMemcpyDtoDAsync(dst, d_storage + (CUdeviceptr)field->offset,
                                   field->size, 0));
    }
    trace->row_count++;
    return 0;
  }
  if (trace->coalesced_buf) {
    CUDA_CHECK(cuMemcpyDtoH(trace->coalesced_buf,
                            d_storage + (CUdeviceptr)trace->coalesced_base,
                            trace->coalesced_span));
  }
  fprintf(trace->fp, "%u", step);
  for (unsigned i = 0U; i < trace->field_count; i++) {
    unsigned char buf[8] = {0};
    unsigned long long value = 0ULL;
    StepTraceField *field = &trace->fields[i];
    if (trace->coalesced_buf) {
      memcpy(buf, trace->coalesced_buf + (field->offset - trace->coalesced_base),
             field->size);
    } else {
      CUDA_CHECK(cuMemcpyDtoH(buf, d_storage + (CUdeviceptr)field->offset,
                              field->size));
    }
    for (size_t byte_idx = 0U; byte_idx < field->size; byte_idx++)
      value |= ((unsigned long long)buf[byte_idx]) << (8U * byte_idx);
    fprintf(trace->fp, ",0x%llx", value);
  }
  fprintf(trace->fp, "\n");
  return ferror(trace->fp) ? -1 : 0;
}

static int compare_float_ascending(const void *lhs, const void *rhs) {
  const float a = *(const float *)lhs;
  const float b = *(const float *)rhs;
  return (a > b) - (a < b);
}

static float median_float_copy(const float *values, unsigned count) {
  if (count == 0U)
    return 0.f;
  float *copy = (float *)malloc((size_t)count * sizeof(*copy));
  if (!copy)
    return values[count - 1U];
  memcpy(copy, values, (size_t)count * sizeof(*copy));
  qsort(copy, count, sizeof(*copy), compare_float_ascending);
  float median = 0.f;
  if ((count % 2U) == 1U) {
    median = copy[count / 2U];
  } else {
    median = (copy[(count / 2U) - 1U] + copy[count / 2U]) / 2.f;
  }
  free(copy);
  return median;
}

static void trace_stage(const char *stage) {
  if (stage_timing_enabled()) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    if (!g_stage_timing_started) {
      g_stage_timing_started = 1;
      g_stage_timing_previous = now;
    } else if (g_stage_timing_count < MAX_STAGE_TIMINGS) {
      double elapsed_ms =
          (now.tv_sec - g_stage_timing_previous.tv_sec) * 1000.0 +
          (now.tv_nsec - g_stage_timing_previous.tv_nsec) / 1e6;
      g_stage_timings[g_stage_timing_count].stage = stage;
      g_stage_timings[g_stage_timing_count].since_previous_ms = elapsed_ms;
      g_stage_timing_count++;
      g_stage_timing_previous = now;
    }
  }
  if (trace_stages_enabled()) {
    fprintf(stderr, "run_vl_hybrid: stage=%s\n", stage);
    fflush(stderr);
  }
}

static void print_stage_timings(void) {
  if (!stage_timing_enabled())
    return;
  printf("stage_timing_ms:");
  for (unsigned i = 0U; i < g_stage_timing_count; i++) {
    printf(" %s=%.3f", g_stage_timings[i].stage,
           g_stage_timings[i].since_previous_ms);
  }
  printf("\n");
}

static void trace_function_attr(CUfunction fn, const char *kernel_name,
                                const char *attr_name,
                                CUfunction_attribute attr) {
  if (!trace_stages_enabled())
    return;
  int value = 0;
  CUresult err = cuFuncGetAttribute(&value, attr, fn);
  if (err != CUDA_SUCCESS) {
    const char *msg = NULL;
    cuGetErrorString(err, &msg);
    fprintf(stderr, "run_vl_hybrid: attr %s %s=error:%d:%s\n", kernel_name,
            attr_name, (int)err, msg ? msg : "?");
    return;
  }
  fprintf(stderr, "run_vl_hybrid: attr %s %s=%d\n", kernel_name, attr_name,
          value);
}

static void trace_function_attrs(CUfunction fn, const char *kernel_name) {
  if (!trace_stages_enabled())
    return;
  trace_function_attr(fn, kernel_name, "MAX_THREADS_PER_BLOCK",
                      CU_FUNC_ATTRIBUTE_MAX_THREADS_PER_BLOCK);
  trace_function_attr(fn, kernel_name, "NUM_REGS",
                      CU_FUNC_ATTRIBUTE_NUM_REGS);
  trace_function_attr(fn, kernel_name, "LOCAL_SIZE_BYTES",
                      CU_FUNC_ATTRIBUTE_LOCAL_SIZE_BYTES);
  trace_function_attr(fn, kernel_name, "SHARED_SIZE_BYTES",
                      CU_FUNC_ATTRIBUTE_SHARED_SIZE_BYTES);
  trace_function_attr(fn, kernel_name, "CONST_SIZE_BYTES",
                      CU_FUNC_ATTRIBUTE_CONST_SIZE_BYTES);
  trace_function_attr(fn, kernel_name, "PTX_VERSION",
                      CU_FUNC_ATTRIBUTE_PTX_VERSION);
  trace_function_attr(fn, kernel_name, "BINARY_VERSION",
                      CU_FUNC_ATTRIBUTE_BINARY_VERSION);
  trace_function_attr(fn, kernel_name, "CACHE_MODE_CA",
                      CU_FUNC_ATTRIBUTE_CACHE_MODE_CA);
#ifdef CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES
  trace_function_attr(fn, kernel_name, "MAX_DYNAMIC_SHARED_SIZE_BYTES",
                      CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES);
#endif
#ifdef CU_FUNC_ATTRIBUTE_PREFERRED_SHARED_MEMORY_CARVEOUT
  trace_function_attr(fn, kernel_name, "PREFERRED_SHARED_MEMORY_CARVEOUT",
                      CU_FUNC_ATTRIBUTE_PREFERRED_SHARED_MEMORY_CARVEOUT);
#endif
#ifdef CU_FUNC_ATTRIBUTE_CLUSTER_SIZE_MUST_BE_SET
  trace_function_attr(fn, kernel_name, "CLUSTER_SIZE_MUST_BE_SET",
                      CU_FUNC_ATTRIBUTE_CLUSTER_SIZE_MUST_BE_SET);
#endif
#ifdef CU_FUNC_ATTRIBUTE_REQUIRED_CLUSTER_WIDTH
  trace_function_attr(fn, kernel_name, "REQUIRED_CLUSTER_WIDTH",
                      CU_FUNC_ATTRIBUTE_REQUIRED_CLUSTER_WIDTH);
#endif
#ifdef CU_FUNC_ATTRIBUTE_REQUIRED_CLUSTER_HEIGHT
  trace_function_attr(fn, kernel_name, "REQUIRED_CLUSTER_HEIGHT",
                      CU_FUNC_ATTRIBUTE_REQUIRED_CLUSTER_HEIGHT);
#endif
#ifdef CU_FUNC_ATTRIBUTE_REQUIRED_CLUSTER_DEPTH
  trace_function_attr(fn, kernel_name, "REQUIRED_CLUSTER_DEPTH",
                      CU_FUNC_ATTRIBUTE_REQUIRED_CLUSTER_DEPTH);
#endif
#ifdef CU_FUNC_ATTRIBUTE_NON_PORTABLE_CLUSTER_SIZE_ALLOWED
  trace_function_attr(fn, kernel_name, "NON_PORTABLE_CLUSTER_SIZE_ALLOWED",
                      CU_FUNC_ATTRIBUTE_NON_PORTABLE_CLUSTER_SIZE_ALLOWED);
#endif
#ifdef CU_FUNC_ATTRIBUTE_CLUSTER_SCHEDULING_POLICY_PREFERENCE
  trace_function_attr(fn, kernel_name, "CLUSTER_SCHEDULING_POLICY_PREFERENCE",
                      CU_FUNC_ATTRIBUTE_CLUSTER_SCHEDULING_POLICY_PREFERENCE);
#endif
}

static void trace_kernel_launch(const char *kernel_name, unsigned step,
                                int kernel_index) {
  if (!trace_stages_enabled())
    return;
  fprintf(stderr, "run_vl_hybrid: launch step=%u kernel_index=%d kernel=%s\n",
          step, kernel_index, kernel_name);
}

static int launch_resident_patch_step(CUfunction patch_kfn,
                                      ResidentPatchSchedule *schedule,
                                      CUdeviceptr d_storage,
                                      unsigned step) {
  if (!schedule || !schedule->step_offsets || step >= schedule->logical_steps)
    return 0;
  unsigned start = schedule->step_offsets[step];
  unsigned end = schedule->step_offsets[step + 1U];
  unsigned count = end - start;
  if (count == 0U)
    return 0;
  CUdeviceptr d_step_offsets =
      schedule->d_offsets + ((CUdeviceptr)start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_step_values = schedule->d_values + (CUdeviceptr)start;
  int count_i = (int)count;
  unsigned patch_block = 256U;
  unsigned patch_grid = (count + patch_block - 1U) / patch_block;
  void *patch_params[] = {&d_storage, &d_step_offsets, &d_step_values, &count_i};
  trace_kernel_launch("vl_apply_patch_schedule_gpu", step, -1);
  CUDA_CHECK(cuLaunchKernel(patch_kfn, patch_grid, 1, 1, patch_block, 1, 1, 0,
                            0, patch_params, NULL));
  return 0;
}

static unsigned resident_patch_count_for_step(ResidentPatchSchedule *schedule,
                                              unsigned step) {
  if (!schedule || !schedule->step_offsets || step >= schedule->logical_steps)
    return 0U;
  return schedule->step_offsets[step + 1U] - schedule->step_offsets[step];
}

static int launch_fused_patch_eval_step(CUfunction fused_kfn,
                                        ResidentPatchSchedule *schedule,
                                        CUdeviceptr d_storage,
                                        unsigned step,
                                        unsigned nstates,
                                        unsigned grid,
                                        unsigned block) {
  if (!fused_kfn || !schedule || !schedule->step_offsets ||
      step >= schedule->logical_steps || nstates == 0U)
    return 0;
  unsigned start = schedule->step_offsets[step];
  unsigned count = schedule->step_offsets[step + 1U] - start;
  if (count == 0U || (count % nstates) != 0U)
    return 0;
  CUdeviceptr d_step_offsets =
      schedule->d_offsets + ((CUdeviceptr)start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_step_values = schedule->d_values + (CUdeviceptr)start;
  int count_i = (int)count;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage, &d_step_offsets, &d_step_values, &count_i,
                    &nstates_i};
  trace_kernel_launch("vl_patch_eval_batch_gpu", step, -2);
  CUDA_CHECK(cuLaunchKernel(fused_kfn, grid, 1, 1, block, 1, 1, 0, 0, params,
                            NULL));
  return 1;
}

static int launch_fused_pair_cycle_step(CUfunction pair_kfn,
                                        ResidentPatchSchedule *schedule,
                                        CUdeviceptr d_storage,
                                        unsigned low_step,
                                        unsigned nstates,
                                        unsigned grid,
                                        unsigned block) {
  if (!pair_kfn || !schedule || !schedule->step_offsets ||
      low_step + 1U >= schedule->logical_steps || nstates == 0U)
    return 0;
  unsigned low_start = schedule->step_offsets[low_step];
  unsigned low_count = schedule->step_offsets[low_step + 1U] - low_start;
  unsigned high_start = schedule->step_offsets[low_step + 1U];
  unsigned high_count = schedule->step_offsets[low_step + 2U] - high_start;
  if (low_count == 0U || high_count == 0U ||
      (low_count % nstates) != 0U || (high_count % nstates) != 0U)
    return 0;
  CUdeviceptr d_low_offsets =
      schedule->d_offsets + ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_low_values = schedule->d_values + (CUdeviceptr)low_start;
  CUdeviceptr d_high_offsets =
      schedule->d_offsets + ((CUdeviceptr)high_start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_high_values = schedule->d_values + (CUdeviceptr)high_start;
  int low_count_i = (int)low_count;
  int high_count_i = (int)high_count;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage, &d_low_offsets, &d_low_values, &low_count_i,
                    &d_high_offsets, &d_high_values, &high_count_i,
                    &nstates_i};
  trace_kernel_launch("vl_patch_eval_pair_cycle_batch_gpu", low_step, -3);
  CUDA_CHECK(cuLaunchKernel(pair_kfn, grid, 1, 1, block, 1, 1, 0, 0, params,
                            NULL));
  return 1;
}

static unsigned fused_pair_cycle_loop_count(ResidentPatchSchedule *schedule,
                                            unsigned low_step,
                                            unsigned nstates,
                                            unsigned max_cycles) {
  if (!schedule || !schedule->step_offsets ||
      low_step + 1U >= schedule->logical_steps || nstates == 0U)
    return 0U;
  unsigned low_start = schedule->step_offsets[low_step];
  unsigned low_count = schedule->step_offsets[low_step + 1U] - low_start;
  unsigned high_start = schedule->step_offsets[low_step + 1U];
  unsigned high_count = schedule->step_offsets[low_step + 2U] - high_start;
  if (low_count == 0U || high_count == 0U ||
      (low_count % nstates) != 0U || (high_count % nstates) != 0U)
    return 0U;
  unsigned available = (schedule->logical_steps - low_step) / 2U;
  if (max_cycles > 0U && available > max_cycles)
    available = max_cycles;
  unsigned cycles = 0U;
  for (; cycles < available; cycles++) {
    unsigned step = low_step + (cycles * 2U);
    unsigned this_low = schedule->step_offsets[step + 1U] -
                        schedule->step_offsets[step];
    unsigned this_high = schedule->step_offsets[step + 2U] -
                         schedule->step_offsets[step + 1U];
    if (this_low != low_count || this_high != high_count)
      break;
  }
  return cycles;
}

static int launch_fused_pair_cycle_loop_step(CUfunction pair_loop_kfn,
                                             ResidentPatchSchedule *schedule,
                                             CUdeviceptr d_storage,
                                             unsigned low_step,
                                             unsigned cycle_count,
                                             unsigned nstates,
                                             unsigned grid,
                                             unsigned block,
                                             const char *kernel_name) {
  if (!pair_loop_kfn || !schedule || !schedule->step_offsets ||
      cycle_count == 0U || low_step + 1U >= schedule->logical_steps ||
      nstates == 0U)
    return 0;
  unsigned low_start = schedule->step_offsets[low_step];
  unsigned low_count = schedule->step_offsets[low_step + 1U] - low_start;
  unsigned high_count = schedule->step_offsets[low_step + 2U] -
                        schedule->step_offsets[low_step + 1U];
  if (low_count == 0U || high_count == 0U ||
      (low_count % nstates) != 0U || (high_count % nstates) != 0U)
    return 0;
  if (low_count > (unsigned)INT_MAX || high_count > (unsigned)INT_MAX ||
      nstates > (unsigned)INT_MAX || cycle_count > (unsigned)INT_MAX)
    return 0;
  CUdeviceptr d_pair_offsets =
      schedule->d_offsets + ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_pair_values = schedule->d_values + (CUdeviceptr)low_start;
  int low_count_i = (int)low_count;
  int high_count_i = (int)high_count;
  int nstates_i = (int)nstates;
  int cycle_count_i = (int)cycle_count;
  void *params[] = {&d_storage, &d_pair_offsets, &d_pair_values, &low_count_i,
                    &high_count_i, &nstates_i, &cycle_count_i};
  trace_kernel_launch(kernel_name ? kernel_name : "vl_patch_eval_pair_cycle_loop_batch_gpu",
                      low_step, -5);
  CUDA_CHECK(cuLaunchKernel(pair_loop_kfn, grid, 1, 1, block, 1, 1, 0, 0,
                            params, NULL));
  return 1;
}

static int launch_ordering_aware_token_loop_step(
    CUfunction token_loop_kfn,
    CUfunction u64_load_probe_kfn,
    int u64_load_probe_module_idx,
    int token_loop_module_idx,
    ResidentPatchSchedule *schedule,
    FeedbackSetTable *sets,
    FeedbackEdgeTable *edges,
    FeedbackIncrementTable *increments,
    OrderingAwareTerminalMaskTable *terminal_masks,
    EvalPartitionPredicateTable *predicates,
    CUdeviceptr d_storage,
    size_t storage_size,
    unsigned low_step,
    unsigned cycle_count,
    unsigned current_phase,
    int apply_phase_controls,
    int apply_feedback,
    unsigned nstates,
    unsigned grid,
    unsigned block,
    int eval_partition_guarded_skip_enabled,
    CUdeviceptr d_single_entry_cfg_clone_liveout_counters,
    size_t single_entry_cfg_clone_liveout_counter_count,
    CUdeviceptr d_cfg_clone_shadow_descriptor_records,
    CUdeviceptr d_cfg_clone_shadow_payload,
    size_t cfg_clone_shadow_payload_total_bytes,
    unsigned cfg_clone_shadow_descriptor_count,
    CUdeviceptr d_region_cycles,
    CUdeviceptr d_ordering_aware_token_loop_progress_global,
    size_t ordering_aware_token_loop_progress_global_bytes,
    volatile unsigned long long *ordering_aware_token_loop_progress) {
  if (!token_loop_kfn || !schedule || !schedule->step_offsets ||
      cycle_count == 0U || low_step + 1U >= schedule->logical_steps ||
      nstates == 0U)
    return 0;
  if (!apply_phase_controls && sets && sets->set_count > 0U) {
    fprintf(stderr,
            "run_vl_hybrid: ordering-aware token-loop phase controls cannot be continued across chunk boundaries without a generated continuation ABI; rerun with a full logical phase chunk\n");
    return -1;
  }
  unsigned low_start = schedule->step_offsets[low_step];
  unsigned low_count = schedule->step_offsets[low_step + 1U] - low_start;
  unsigned high_count = schedule->step_offsets[low_step + 2U] -
                        schedule->step_offsets[low_step + 1U];
  if (low_count == 0U || high_count == 0U ||
      (low_count % nstates) != 0U || (high_count % nstates) != 0U)
    return 0;
  if (low_count > (unsigned)INT_MAX || high_count > (unsigned)INT_MAX ||
      nstates > (unsigned)INT_MAX || cycle_count > (unsigned)INT_MAX ||
      current_phase > (unsigned)INT_MAX)
    return 0;

  CUdeviceptr d_pair_offsets =
      schedule->d_offsets + ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_pair_values = schedule->d_values + (CUdeviceptr)low_start;
  CUdeviceptr d_phase_control_phases =
      sets && sets->d_phases ? sets->d_phases : (CUdeviceptr)0;
  CUdeviceptr d_phase_control_states =
      sets && sets->d_states ? sets->d_states : (CUdeviceptr)0;
  CUdeviceptr d_phase_control_offsets =
      sets && sets->d_offsets ? sets->d_offsets : (CUdeviceptr)0;
  CUdeviceptr d_phase_control_values =
      sets && sets->d_values ? sets->d_values : (CUdeviceptr)0;
  CUdeviceptr d_feedback_copy_src_offsets =
      edges && edges->d_src_offsets ? edges->d_src_offsets : (CUdeviceptr)0;
  CUdeviceptr d_feedback_copy_dst_offsets =
      edges && edges->d_dst_offsets ? edges->d_dst_offsets : (CUdeviceptr)0;
  CUdeviceptr d_feedback_increment_offsets =
      increments && increments->d_offsets ? increments->d_offsets : (CUdeviceptr)0;
  CUdeviceptr d_feedback_increment_deltas =
      increments && increments->d_deltas ? increments->d_deltas : (CUdeviceptr)0;
  CUdeviceptr d_terminal_mask_states =
      terminal_masks && terminal_masks->d_states ? terminal_masks->d_states
                                                 : (CUdeviceptr)0;
  CUdeviceptr d_terminal_mask_steps =
      terminal_masks && terminal_masks->d_terminal_steps
          ? terminal_masks->d_terminal_steps
          : (CUdeviceptr)0;
  CUdeviceptr d_eval_predicate_partition_ids =
      predicates && predicates->d_partition_ids ? predicates->d_partition_ids
                                                : (CUdeviceptr)0;
  CUdeviceptr d_eval_predicate_phases =
      predicates && predicates->d_phases ? predicates->d_phases : (CUdeviceptr)0;
  CUdeviceptr d_eval_predicate_states =
      predicates && predicates->d_states ? predicates->d_states : (CUdeviceptr)0;
  CUdeviceptr d_eval_predicate_active =
      predicates && predicates->d_active ? predicates->d_active : (CUdeviceptr)0;
  CUdeviceptr d_eval_predicate_active_bitmap =
      predicates && predicates->d_active_bitmap ? predicates->d_active_bitmap
                                                : (CUdeviceptr)0;
  int low_count_i = (int)low_count;
  int high_count_i = (int)high_count;
  int nstates_i = (int)nstates;
  int cycle_count_i = (int)cycle_count;
  int current_phase_i = (int)current_phase;
  int phase_control_count_i =
      apply_phase_controls && sets && sets->set_count <= (unsigned)INT_MAX
          ? (int)sets->set_count
          : 0;
  int feedback_copy_count_i =
      apply_feedback && edges && edges->edge_count <= (unsigned)INT_MAX
          ? (int)edges->edge_count
          : 0;
  int feedback_increment_count_i =
      apply_feedback && increments && increments->increment_count <= (unsigned)INT_MAX
          ? (int)increments->increment_count
          : 0;
  int terminal_mask_count_i =
      terminal_masks && terminal_masks->mask_count <= (unsigned)INT_MAX
          ? (int)terminal_masks->mask_count
          : 0;
  int eval_predicate_count_i =
      predicates && predicates->record_count <= (unsigned)INT_MAX
          ? (int)predicates->record_count
          : 0;
  int eval_predicate_active_bitmap_phase_count_i =
      predicates && predicates->active_bitmap_phase_count <= (unsigned)INT_MAX
          ? (int)predicates->active_bitmap_phase_count
          : 0;
  int eval_predicate_active_bitmap_partition_count_i =
      predicates &&
              predicates->active_bitmap_partition_count <= (unsigned)INT_MAX
          ? (int)predicates->active_bitmap_partition_count
          : 0;
  int eval_predicate_guarded_skip_enabled_i =
      eval_partition_guarded_skip_enabled ? 1 : 0;
  int cfg_clone_shadow_descriptor_count_i =
      cfg_clone_shadow_descriptor_count <= (unsigned)INT_MAX
          ? (int)cfg_clone_shadow_descriptor_count
          : 0;
  size_t pair_record_count =
      checked_mul_size((size_t)cycle_count, (size_t)(low_count + high_count));
  size_t pair_offsets_bytes =
      checked_mul_size(pair_record_count, sizeof(size_t));
  size_t pair_values_bytes = pair_record_count;
  TokenLoopAliasScanEntry alias_scan_entries[] = {
      {"storage", d_storage, storage_size},
      {"pair_offsets", d_pair_offsets, pair_offsets_bytes},
      {"pair_values", d_pair_values, pair_values_bytes},
      {"phase_control_phases", d_phase_control_phases,
       (size_t)phase_control_count_i * sizeof(unsigned)},
      {"phase_control_states", d_phase_control_states,
       (size_t)phase_control_count_i * sizeof(unsigned)},
      {"phase_control_offsets", d_phase_control_offsets,
       (size_t)phase_control_count_i * sizeof(size_t)},
      {"phase_control_values", d_phase_control_values,
       (size_t)phase_control_count_i},
      {"feedback_copy_src_offsets", d_feedback_copy_src_offsets,
       (size_t)feedback_copy_count_i * sizeof(size_t)},
      {"feedback_copy_dst_offsets", d_feedback_copy_dst_offsets,
       (size_t)feedback_copy_count_i * sizeof(size_t)},
      {"feedback_increment_offsets", d_feedback_increment_offsets,
       (size_t)feedback_increment_count_i * sizeof(size_t)},
      {"feedback_increment_deltas", d_feedback_increment_deltas,
       (size_t)feedback_increment_count_i},
      {"terminal_mask_states", d_terminal_mask_states,
       (size_t)terminal_mask_count_i * sizeof(unsigned)},
      {"terminal_mask_steps", d_terminal_mask_steps,
       (size_t)terminal_mask_count_i * sizeof(unsigned)},
      {"eval_predicate_partition_ids", d_eval_predicate_partition_ids,
       (size_t)eval_predicate_count_i * sizeof(unsigned)},
      {"eval_predicate_phases", d_eval_predicate_phases,
       (size_t)eval_predicate_count_i * sizeof(unsigned)},
      {"eval_predicate_states", d_eval_predicate_states,
       (size_t)eval_predicate_count_i * sizeof(unsigned)},
      {"eval_predicate_active", d_eval_predicate_active,
       (size_t)eval_predicate_count_i},
      {"eval_predicate_active_bitmap", d_eval_predicate_active_bitmap,
       predicates ? (size_t)predicates->active_bitmap_size : 0U},
      {"diagnostic_cfg_clone_liveout_counters",
       d_single_entry_cfg_clone_liveout_counters,
       single_entry_cfg_clone_liveout_counter_count *
           sizeof(unsigned long long)},
      {"diagnostic_cfg_clone_shadow_descriptor_records",
       d_cfg_clone_shadow_descriptor_records,
       (size_t)cfg_clone_shadow_descriptor_count_i *
           CFG_CLONE_SHADOW_DESCRIPTOR_RECORD_BYTES},
      {"diagnostic_cfg_clone_shadow_payload", d_cfg_clone_shadow_payload,
       cfg_clone_shadow_payload_total_bytes},
      {"diagnostic_ordering_aware_token_loop_progress",
       (CUdeviceptr)ordering_aware_token_loop_progress,
       ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS *
           sizeof(unsigned long long)},
      {"diagnostic_ordering_aware_token_loop_progress_global",
       d_ordering_aware_token_loop_progress_global,
       ordering_aware_token_loop_progress_global_bytes},
      {"diagnostic_region_cycles", d_region_cycles,
       ORDERING_AWARE_REGION_TIMING_COUNTERS * sizeof(unsigned long long)},
  };
  unsigned alias_scan_entry_count =
      (unsigned)(sizeof(alias_scan_entries) / sizeof(alias_scan_entries[0]));
  static int first_launch_diagnostic_emitted = 0;
  if (env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_FIRST_LAUNCH_DIAGNOSTIC) &&
      !first_launch_diagnostic_emitted) {
    first_launch_diagnostic_emitted = 1;
    printf("ordering_aware_token_loop_first_launch: schedule_step=%u low_start=%u low_count=%u high_count=%u cycle_count=%u current_phase=%u apply_phase_controls=%s apply_feedback=%s nstates=%u grid=%u block=%u phase_control_count=%d feedback_copy_count=%d feedback_increment_count=%d terminal_mask_count=%d eval_predicate_count=%d eval_predicate_active_bitmap_phase_count=%d eval_predicate_active_bitmap_partition_count=%d eval_predicate_guarded_skip_enabled=%s cfg_clone_shadow_descriptor_count=%d has_storage=%s has_pair_offsets=%s has_pair_values=%s has_phase_control_device=%s has_feedback_copy_device=%s has_feedback_increment_device=%s has_terminal_mask_device=%s has_eval_predicate_device=%s has_eval_predicate_active_bitmap=%s has_cfg_clone_liveout_counters=%s has_cfg_clone_shadow_descriptor_records=%s has_cfg_clone_shadow_payload=%s region_timing=%s\n",
           low_step,
           low_start,
           low_count,
           high_count,
           cycle_count,
           current_phase,
           apply_phase_controls ? "true" : "false",
           apply_feedback ? "true" : "false",
           nstates,
           grid,
           block,
           phase_control_count_i,
           feedback_copy_count_i,
           feedback_increment_count_i,
           terminal_mask_count_i,
           eval_predicate_count_i,
           eval_predicate_active_bitmap_phase_count_i,
           eval_predicate_active_bitmap_partition_count_i,
           eval_predicate_guarded_skip_enabled_i ? "true" : "false",
           cfg_clone_shadow_descriptor_count_i,
           d_storage ? "true" : "false",
           d_pair_offsets ? "true" : "false",
           d_pair_values ? "true" : "false",
           (d_phase_control_phases && d_phase_control_states &&
            d_phase_control_offsets && d_phase_control_values)
               ? "true"
               : "false",
           (d_feedback_copy_src_offsets && d_feedback_copy_dst_offsets)
               ? "true"
               : "false",
           (d_feedback_increment_offsets && d_feedback_increment_deltas)
               ? "true"
               : "false",
           (d_terminal_mask_states && d_terminal_mask_steps) ? "true" : "false",
           (d_eval_predicate_partition_ids && d_eval_predicate_phases &&
            d_eval_predicate_states && d_eval_predicate_active)
               ? "true"
               : "false",
           d_eval_predicate_active_bitmap ? "true" : "false",
           d_single_entry_cfg_clone_liveout_counters ? "true" : "false",
           d_cfg_clone_shadow_descriptor_records ? "true" : "false",
           d_cfg_clone_shadow_payload ? "true" : "false",
           d_region_cycles ? "true" : "false");
    fflush(stdout);
  }
  maybe_print_ordering_aware_high_patch_offset_diagnostic(
      "pre_token_loop_launch",
      schedule, u64_load_probe_kfn, u64_load_probe_module_idx,
      token_loop_module_idx, d_pair_offsets, d_pair_values, d_storage,
      (CUdeviceptr)ordering_aware_token_loop_progress, storage_size, low_step,
      low_start, low_count, high_count, current_phase, nstates);
  print_ordering_aware_token_loop_arg_table_alias_scan(
      "pre_token_loop_launch",
      schedule, alias_scan_entries, alias_scan_entry_count, low_step,
      low_start, low_count, high_count, cycle_count, current_phase, nstates,
      318U);
  print_ordering_aware_token_loop_internal_writer_scan(
      "pre_token_loop_launch",
      schedule, sets, edges, increments, d_storage, storage_size, low_step,
      low_start, low_count, high_count, cycle_count, current_phase,
      apply_phase_controls, apply_feedback, nstates, 318U);
  void *params[] = {
      &d_storage,
      &d_pair_offsets,
      &d_pair_values,
      &low_count_i,
      &high_count_i,
      &nstates_i,
      &cycle_count_i,
      &current_phase_i,
      &d_phase_control_phases,
      &d_phase_control_states,
      &d_phase_control_offsets,
      &d_phase_control_values,
      &phase_control_count_i,
      &d_feedback_copy_src_offsets,
      &d_feedback_copy_dst_offsets,
      &feedback_copy_count_i,
      &d_feedback_increment_offsets,
      &d_feedback_increment_deltas,
      &feedback_increment_count_i,
      &d_terminal_mask_states,
      &d_terminal_mask_steps,
      &terminal_mask_count_i,
      &d_eval_predicate_partition_ids,
      &d_eval_predicate_phases,
      &d_eval_predicate_states,
      &d_eval_predicate_active,
      &eval_predicate_count_i,
      &d_eval_predicate_active_bitmap,
      &eval_predicate_active_bitmap_phase_count_i,
      &eval_predicate_guarded_skip_enabled_i,
      &eval_predicate_active_bitmap_partition_count_i,
      &d_single_entry_cfg_clone_liveout_counters,
      &d_cfg_clone_shadow_descriptor_records,
      &d_cfg_clone_shadow_payload,
      &cfg_clone_shadow_descriptor_count_i,
  };
  void *timing_params[] = {
      &d_storage,
      &d_pair_offsets,
      &d_pair_values,
      &low_count_i,
      &high_count_i,
      &nstates_i,
      &cycle_count_i,
      &current_phase_i,
      &d_phase_control_phases,
      &d_phase_control_states,
      &d_phase_control_offsets,
      &d_phase_control_values,
      &phase_control_count_i,
      &d_feedback_copy_src_offsets,
      &d_feedback_copy_dst_offsets,
      &feedback_copy_count_i,
      &d_feedback_increment_offsets,
      &d_feedback_increment_deltas,
      &feedback_increment_count_i,
      &d_terminal_mask_states,
      &d_terminal_mask_steps,
      &terminal_mask_count_i,
      &d_eval_predicate_partition_ids,
      &d_eval_predicate_phases,
      &d_eval_predicate_states,
      &d_eval_predicate_active,
      &eval_predicate_count_i,
      &d_eval_predicate_active_bitmap,
      &eval_predicate_active_bitmap_phase_count_i,
      &eval_predicate_guarded_skip_enabled_i,
      &eval_predicate_active_bitmap_partition_count_i,
      &d_single_entry_cfg_clone_liveout_counters,
      &d_cfg_clone_shadow_descriptor_records,
      &d_cfg_clone_shadow_payload,
      &cfg_clone_shadow_descriptor_count_i,
      &d_region_cycles,
  };
  trace_kernel_launch(
      d_region_cycles
          ? "vl_tb_core_ordering_aware_phase_resident_token_loop_region_timing_gpu"
          : "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu",
      low_step, -6);
  CUDA_CHECK(cuLaunchKernel(token_loop_kfn, grid, 1, 1, block, 1, 1, 0, 0,
                            d_region_cycles ? timing_params : params, NULL));
  if (env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_SYNC_AFTER_LAUNCH)) {
    printf("ordering_aware_token_loop_post_launch_sync: requested=true status=before_sync schedule_step=%u cycle_count=%u current_phase=%u nstates=%u low_count=%u high_count=%u\n",
           low_step,
           cycle_count,
           current_phase,
           nstates,
           low_count,
           high_count);
    fflush(stdout);
    CUresult sync_err = cuCtxSynchronize();
    const char *sync_name = NULL;
    cuGetErrorName(sync_err, &sync_name);
    if (sync_err != CUDA_SUCCESS) {
      printf("ordering_aware_token_loop_post_launch_sync: requested=true status=failed cuda_result=%d cuda_error=%s schedule_step=%u cycle_count=%u current_phase=%u nstates=%u low_count=%u high_count=%u\n",
             (int)sync_err,
             sync_name ? sync_name : "?",
             low_step,
             cycle_count,
             current_phase,
             nstates,
             low_count,
             high_count);
      fflush(stdout);
      print_ordering_aware_token_loop_progress_snapshot(
          "post_launch_sync_failed",
          ordering_aware_token_loop_progress);
      print_ordering_aware_token_loop_pair_offset_device_write_watchpoint(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_eval_callsite_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_low_patch_to_low_eval_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_pre_low_patch_cycle_entry_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_pre_cycle_cond_to_cycle_cond_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_cycle_cond_entry_boundary_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_cycle_cond_post_phi_edge_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_cycle_cond_backedge_pre_branch_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_call_path_memory_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee_callsite_pointer_view(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_body_pair_offset_store_watchpoint(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_pair_offset_boundary(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_pair_offset_store_watchpoint(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_deeper_call_pair_offset_boundary(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_non_store_effect_pair_offset_watchpoint(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_residual_boundary(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_body_boundary(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_instruction_boundary(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_boundary(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_instruction_boundary(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_lifecycle_probe(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_concrete_write_window_probe(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_transition_probe(
          "post_token_loop_sync_failed",
          schedule, ordering_aware_token_loop_progress, low_step, low_start,
          low_count, high_count, cycle_count, current_phase, nstates, 318U);
      print_ordering_aware_token_loop_arg_table_alias_scan(
          "post_token_loop_sync_failed",
          schedule, alias_scan_entries, alias_scan_entry_count, low_step,
          low_start, low_count, high_count, cycle_count, current_phase, nstates,
          318U);
      print_ordering_aware_token_loop_internal_writer_scan(
          "post_token_loop_sync_failed",
          schedule, sets, edges, increments, d_storage, storage_size, low_step,
          low_start, low_count, high_count, cycle_count, current_phase,
          apply_phase_controls, apply_feedback, nstates, 318U);
      cuda_fail(__FILE__, __LINE__, sync_err,
                "ordering-aware token-loop post-launch sync");
    }
    printf("ordering_aware_token_loop_post_launch_sync: requested=true status=passed cuda_result=%d cuda_error=%s schedule_step=%u cycle_count=%u current_phase=%u nstates=%u low_count=%u high_count=%u\n",
           (int)sync_err,
           sync_name ? sync_name : "CUDA_SUCCESS",
           low_step,
           cycle_count,
           current_phase,
           nstates,
           low_count,
           high_count);
    fflush(stdout);
    maybe_print_ordering_aware_high_patch_offset_diagnostic(
        "post_token_loop_sync",
        schedule, u64_load_probe_kfn, u64_load_probe_module_idx,
        token_loop_module_idx, d_pair_offsets, d_pair_values, d_storage,
        (CUdeviceptr)ordering_aware_token_loop_progress, storage_size, low_step,
        low_start, low_count, high_count, current_phase, nstates);
    print_ordering_aware_token_loop_arg_table_alias_scan(
        "post_token_loop_sync",
        schedule, alias_scan_entries, alias_scan_entry_count, low_step,
        low_start, low_count, high_count, cycle_count, current_phase, nstates,
        318U);
    print_ordering_aware_token_loop_internal_writer_scan(
        "post_token_loop_sync",
        schedule, sets, edges, increments, d_storage, storage_size, low_step,
        low_start, low_count, high_count, cycle_count, current_phase,
        apply_phase_controls, apply_feedback, nstates, 318U);
    print_ordering_aware_token_loop_pair_offset_device_write_watchpoint(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_eval_callsite_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_low_patch_to_low_eval_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_pre_low_patch_cycle_entry_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_pre_cycle_cond_to_cycle_cond_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_cycle_cond_entry_boundary_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_cycle_cond_post_phi_edge_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_cycle_cond_backedge_pre_branch_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_call_path_memory_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee_callsite_pointer_view(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_body_pair_offset_store_watchpoint(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_pair_offset_boundary(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_pair_offset_store_watchpoint(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_deeper_call_pair_offset_boundary(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_non_store_effect_pair_offset_watchpoint(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_residual_boundary(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_body_boundary(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_instruction_boundary(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_boundary(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_instruction_boundary(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_lifecycle_probe(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_concrete_write_window_probe(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
    print_ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_transition_probe(
        "post_token_loop_sync",
        schedule, ordering_aware_token_loop_progress, low_step, low_start,
        low_count, high_count, cycle_count, current_phase, nstates, 318U);
  }
  return 1;
}

static int launch_fused_pair_cycle_state_local_step(
    CUfunction pair_kfn, ResidentPatchSchedule *schedule, CUdeviceptr d_storage,
    unsigned low_step, unsigned nstates, unsigned grid, unsigned block) {
  if (!pair_kfn || !schedule || !schedule->step_offsets ||
      low_step + 1U >= schedule->logical_steps || nstates == 0U)
    return 0;
  unsigned low_start = schedule->step_offsets[low_step];
  unsigned low_count = schedule->step_offsets[low_step + 1U] - low_start;
  unsigned high_start = schedule->step_offsets[low_step + 1U];
  unsigned high_count = schedule->step_offsets[low_step + 2U] - high_start;
  if (low_count == 0U || high_count == 0U)
    return 0;
  CUdeviceptr d_low_offsets =
      schedule->d_offsets + ((CUdeviceptr)low_start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_low_values = schedule->d_values + (CUdeviceptr)low_start;
  CUdeviceptr d_high_offsets =
      schedule->d_offsets + ((CUdeviceptr)high_start * (CUdeviceptr)sizeof(size_t));
  CUdeviceptr d_high_values = schedule->d_values + (CUdeviceptr)high_start;
  int low_count_i = (int)low_count;
  int high_count_i = (int)high_count;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage, &d_low_offsets, &d_low_values, &low_count_i,
                    &d_high_offsets, &d_high_values, &high_count_i,
                    &nstates_i};
  trace_kernel_launch("vl_patch_eval_pair_cycle_batch_gpu_state_local",
                      low_step, -4);
  CUDA_CHECK(cuLaunchKernel(pair_kfn, grid, 1, 1, block, 1, 1, 0, 0, params,
                            NULL));
  return 1;
}

static int upload_resident_patch_schedule(ResidentPatchSchedule *schedule) {
  if (!schedule || schedule->record_count == 0U)
    return 0;
  CUDA_CHECK(cuMemAlloc(&schedule->d_offsets,
                        (size_t)schedule->record_count *
                            sizeof(*schedule->offsets)));
  CUDA_CHECK(cuMemAlloc(&schedule->d_values,
                        (size_t)schedule->record_count *
                            sizeof(*schedule->values)));
  CUDA_CHECK(cuMemcpyHtoD(schedule->d_offsets, schedule->offsets,
                          (size_t)schedule->record_count *
                              sizeof(*schedule->offsets)));
  CUDA_CHECK(cuMemcpyHtoD(schedule->d_values, schedule->values,
                          (size_t)schedule->record_count *
                              sizeof(*schedule->values)));
  return 0;
}

static int upload_feedback_edge_table(FeedbackEdgeTable *edges) {
  if (!edges || edges->edge_count == 0U)
    return 0;
  CUDA_CHECK(cuMemAlloc(&edges->d_src_offsets,
                        (size_t)edges->edge_count *
                            sizeof(*edges->src_offsets)));
  CUDA_CHECK(cuMemAlloc(&edges->d_dst_offsets,
                        (size_t)edges->edge_count *
                            sizeof(*edges->dst_offsets)));
  CUDA_CHECK(cuMemcpyHtoD(edges->d_src_offsets, edges->src_offsets,
                          (size_t)edges->edge_count *
                              sizeof(*edges->src_offsets)));
  CUDA_CHECK(cuMemcpyHtoD(edges->d_dst_offsets, edges->dst_offsets,
                          (size_t)edges->edge_count *
                              sizeof(*edges->dst_offsets)));
  return 0;
}

static int upload_feedback_increment_table(FeedbackIncrementTable *increments) {
  if (!increments || increments->increment_count == 0U)
    return 0;
  CUDA_CHECK(cuMemAlloc(&increments->d_offsets,
                        (size_t)increments->increment_count *
                            sizeof(*increments->offsets)));
  CUDA_CHECK(cuMemAlloc(&increments->d_deltas,
                        (size_t)increments->increment_count *
                            sizeof(*increments->deltas)));
  CUDA_CHECK(cuMemcpyHtoD(increments->d_offsets, increments->offsets,
                          (size_t)increments->increment_count *
                              sizeof(*increments->offsets)));
  CUDA_CHECK(cuMemcpyHtoD(increments->d_deltas, increments->deltas,
                          (size_t)increments->increment_count *
                              sizeof(*increments->deltas)));
  return 0;
}

static int upload_feedback_set_table(FeedbackSetTable *sets) {
  if (!sets || sets->set_count == 0U)
    return 0;
  CUDA_CHECK(cuMemAlloc(&sets->d_phases,
                        (size_t)sets->set_count * sizeof(*sets->phases)));
  CUDA_CHECK(cuMemAlloc(&sets->d_states,
                        (size_t)sets->set_count * sizeof(*sets->states)));
  CUDA_CHECK(cuMemAlloc(&sets->d_offsets,
                        (size_t)sets->set_count * sizeof(*sets->offsets)));
  CUDA_CHECK(cuMemAlloc(&sets->d_values,
                        (size_t)sets->set_count * sizeof(*sets->values)));
  CUDA_CHECK(cuMemcpyHtoD(sets->d_phases, sets->phases,
                          (size_t)sets->set_count * sizeof(*sets->phases)));
  CUDA_CHECK(cuMemcpyHtoD(sets->d_states, sets->states,
                          (size_t)sets->set_count * sizeof(*sets->states)));
  CUDA_CHECK(cuMemcpyHtoD(sets->d_offsets, sets->offsets,
                          (size_t)sets->set_count * sizeof(*sets->offsets)));
  CUDA_CHECK(cuMemcpyHtoD(sets->d_values, sets->values,
                          (size_t)sets->set_count * sizeof(*sets->values)));
  return 0;
}

static int upload_ordering_aware_terminal_mask_table(
    OrderingAwareTerminalMaskTable *masks) {
  if (!masks || masks->mask_count == 0U)
    return 0;
  CUDA_CHECK(cuMemAlloc(&masks->d_states,
                        (size_t)masks->mask_count * sizeof(*masks->states)));
  CUDA_CHECK(cuMemAlloc(&masks->d_terminal_steps,
                        (size_t)masks->mask_count *
                            sizeof(*masks->terminal_steps)));
  CUDA_CHECK(cuMemcpyHtoD(masks->d_states, masks->states,
                          (size_t)masks->mask_count * sizeof(*masks->states)));
  CUDA_CHECK(cuMemcpyHtoD(masks->d_terminal_steps, masks->terminal_steps,
                          (size_t)masks->mask_count *
                              sizeof(*masks->terminal_steps)));
  return 0;
}

static int upload_eval_partition_predicate_table(
    EvalPartitionPredicateTable *predicates) {
  if (!predicates || predicates->record_count == 0U)
    return 0;
  CUDA_CHECK(cuMemAlloc(&predicates->d_partition_ids,
                        (size_t)predicates->record_count *
                            sizeof(*predicates->partition_ids)));
  CUDA_CHECK(cuMemAlloc(&predicates->d_phases,
                        (size_t)predicates->record_count *
                            sizeof(*predicates->phases)));
  CUDA_CHECK(cuMemAlloc(&predicates->d_states,
                        (size_t)predicates->record_count *
                            sizeof(*predicates->states)));
  CUDA_CHECK(cuMemAlloc(&predicates->d_active,
                        (size_t)predicates->record_count *
                            sizeof(*predicates->active)));
  if (predicates->active_bitmap && predicates->active_bitmap_size > 0U) {
    CUDA_CHECK(cuMemAlloc(&predicates->d_active_bitmap,
                          (size_t)predicates->active_bitmap_size *
                              sizeof(*predicates->active_bitmap)));
  }
  CUDA_CHECK(cuMemcpyHtoD(predicates->d_partition_ids,
                          predicates->partition_ids,
                          (size_t)predicates->record_count *
                              sizeof(*predicates->partition_ids)));
  CUDA_CHECK(cuMemcpyHtoD(predicates->d_phases, predicates->phases,
                          (size_t)predicates->record_count *
                              sizeof(*predicates->phases)));
  CUDA_CHECK(cuMemcpyHtoD(predicates->d_states, predicates->states,
                          (size_t)predicates->record_count *
                              sizeof(*predicates->states)));
  CUDA_CHECK(cuMemcpyHtoD(predicates->d_active, predicates->active,
                          (size_t)predicates->record_count *
                              sizeof(*predicates->active)));
  if (predicates->d_active_bitmap) {
    CUDA_CHECK(cuMemcpyHtoD(predicates->d_active_bitmap,
                            predicates->active_bitmap,
                            (size_t)predicates->active_bitmap_size *
                                sizeof(*predicates->active_bitmap)));
  }
  return 0;
}

static int launch_feedback_edges(CUfunction feedback_kfn,
                                 FeedbackEdgeTable *edges,
                                 CUdeviceptr d_storage,
                                 size_t storage,
                                 unsigned nstates,
                                 unsigned step) {
  if (!feedback_kfn || !edges || edges->edge_count == 0U)
    return 0;
  if (edges->edge_count > (unsigned)INT_MAX || nstates > (unsigned)INT_MAX) {
    fprintf(stderr, "feedback edge launch dimensions exceed int ABI\n");
    return -1;
  }
  unsigned long long total_work =
      (unsigned long long)edges->edge_count * (unsigned long long)nstates;
  unsigned feedback_block = 256U;
  unsigned long long grid_ull =
      (total_work + (unsigned long long)feedback_block - 1ULL) /
      (unsigned long long)feedback_block;
  if (grid_ull == 0ULL || grid_ull > 2147483647ULL) {
    fprintf(stderr, "feedback edge grid out of range: %llu\n", grid_ull);
    return -1;
  }
  unsigned feedback_grid = (unsigned)grid_ull;
  int edge_count_i = (int)edges->edge_count;
  unsigned long long storage_stride = (unsigned long long)storage;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage,
                    &edges->d_src_offsets,
                    &edges->d_dst_offsets,
                    &edge_count_i,
                    &storage_stride,
                    &nstates_i};
  trace_kernel_launch("vl_apply_feedback_edges_gpu", step, -6);
  CUDA_CHECK(cuLaunchKernel(feedback_kfn, feedback_grid, 1, 1, feedback_block,
                            1, 1, 0, 0, params, NULL));
  return 1;
}

static int launch_feedback_increments(CUfunction increment_kfn,
                                      FeedbackIncrementTable *increments,
                                      CUdeviceptr d_storage,
                                      size_t storage,
                                      unsigned nstates,
                                      unsigned step) {
  if (!increment_kfn || !increments || increments->increment_count == 0U)
    return 0;
  if (increments->increment_count > (unsigned)INT_MAX ||
      nstates > (unsigned)INT_MAX) {
    fprintf(stderr, "feedback increment launch dimensions exceed int ABI\n");
    return -1;
  }
  unsigned long long total_work =
      (unsigned long long)increments->increment_count * (unsigned long long)nstates;
  unsigned increment_block = 256U;
  unsigned long long grid_ull =
      (total_work + (unsigned long long)increment_block - 1ULL) /
      (unsigned long long)increment_block;
  if (grid_ull == 0ULL || grid_ull > 2147483647ULL) {
    fprintf(stderr, "feedback increment grid out of range: %llu\n", grid_ull);
    return -1;
  }
  unsigned increment_grid = (unsigned)grid_ull;
  int increment_count_i = (int)increments->increment_count;
  unsigned long long storage_stride = (unsigned long long)storage;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage,
                    &increments->d_offsets,
                    &increments->d_deltas,
                    &increment_count_i,
                    &storage_stride,
                    &nstates_i};
  trace_kernel_launch("vl_apply_feedback_increments_gpu", step, -7);
  CUDA_CHECK(cuLaunchKernel(increment_kfn, increment_grid, 1, 1,
                            increment_block, 1, 1, 0, 0, params, NULL));
  return 1;
}

static int launch_feedback_sets(CUfunction set_kfn,
                                FeedbackSetTable *sets,
                                CUdeviceptr d_storage,
                                size_t storage,
                                unsigned nstates,
                                unsigned current_phase,
                                unsigned step) {
  if (!set_kfn || !sets || sets->set_count == 0U)
    return 0;
  if (sets->set_count > (unsigned)INT_MAX || nstates > (unsigned)INT_MAX ||
      current_phase > (unsigned)INT_MAX) {
    fprintf(stderr, "feedback phase set launch dimensions exceed int ABI\n");
    return -1;
  }
  unsigned long long total_work =
      (unsigned long long)sets->set_count * (unsigned long long)nstates;
  unsigned set_block = 256U;
  unsigned long long grid_ull =
      (total_work + (unsigned long long)set_block - 1ULL) /
      (unsigned long long)set_block;
  if (grid_ull == 0ULL || grid_ull > 2147483647ULL) {
    fprintf(stderr, "feedback phase set grid out of range: %llu\n", grid_ull);
    return -1;
  }
  unsigned set_grid = (unsigned)grid_ull;
  int set_count_i = (int)sets->set_count;
  int current_phase_i = (int)current_phase;
  unsigned long long storage_stride = (unsigned long long)storage;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage,
                    &sets->d_phases,
                    &sets->d_states,
                    &sets->d_offsets,
                    &sets->d_values,
                    &set_count_i,
                    &current_phase_i,
                    &storage_stride,
                    &nstates_i};
  trace_kernel_launch("vl_apply_feedback_sets_gpu", step, -8);
  CUDA_CHECK(cuLaunchKernel(set_kfn, set_grid, 1, 1, set_block, 1, 1, 0, 0,
                            params, NULL));
  return 1;
}

static int launch_feedback_combined(CUfunction combined_kfn,
                                    FeedbackEdgeTable *edges,
                                    FeedbackIncrementTable *increments,
                                    FeedbackSetTable *sets,
                                    CUdeviceptr d_storage,
                                    size_t storage,
                                    unsigned nstates,
                                    unsigned current_phase,
                                    unsigned step) {
  if (!combined_kfn || !edges || !increments || !sets ||
      (edges->edge_count == 0U && increments->increment_count == 0U &&
       sets->set_count == 0U))
    return 0;
  if (edges->edge_count > (unsigned)INT_MAX ||
      increments->increment_count > (unsigned)INT_MAX ||
      sets->set_count > (unsigned)INT_MAX || nstates > (unsigned)INT_MAX ||
      current_phase > (unsigned)INT_MAX) {
    fprintf(stderr, "combined feedback launch dimensions exceed int ABI\n");
    return -1;
  }
  unsigned long long per_state_work =
      (unsigned long long)edges->edge_count +
      (unsigned long long)increments->increment_count;
  unsigned long long total_work = per_state_work * (unsigned long long)nstates;
  unsigned combined_block = 256U;
  unsigned long long grid_ull =
      (total_work + (unsigned long long)combined_block - 1ULL) /
      (unsigned long long)combined_block;
  if (grid_ull == 0ULL || grid_ull > 2147483647ULL) {
    fprintf(stderr, "combined feedback grid out of range: %llu\n", grid_ull);
    return -1;
  }
  unsigned combined_grid = (unsigned)grid_ull;
  int edge_count_i = (int)edges->edge_count;
  int increment_count_i = (int)increments->increment_count;
  int set_count_i = 0;
  int current_phase_i = (int)current_phase;
  unsigned long long storage_stride = (unsigned long long)storage;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage,
                    &edges->d_src_offsets,
                    &edges->d_dst_offsets,
                    &edge_count_i,
                    &increments->d_offsets,
                    &increments->d_deltas,
                    &increment_count_i,
                    &sets->d_phases,
                    &sets->d_states,
                    &sets->d_offsets,
                    &sets->d_values,
                    &set_count_i,
                    &current_phase_i,
                    &storage_stride,
                    &nstates_i};
  trace_kernel_launch("vl_apply_feedback_combined_gpu", step, -9);
  CUDA_CHECK(cuLaunchKernel(combined_kfn, combined_grid, 1, 1, combined_block,
                            1, 1, 0, 0, params, NULL));
  return 1;
}

static int launch_init_state_replication(CUfunction init_kfn,
                                         CUdeviceptr d_storage,
                                         CUdeviceptr d_init_state,
                                         size_t storage,
                                         size_t total) {
  int block = 256;
  unsigned long long grid_ull =
      ((unsigned long long)total + (unsigned long long)block - 1ULL) /
      (unsigned long long)block;
  if (grid_ull == 0ULL || grid_ull > 2147483647ULL) {
    fprintf(stderr, "init-state replication grid out of range: %llu\n", grid_ull);
    return -1;
  }
  unsigned grid = (unsigned)grid_ull;
  unsigned long long storage_arg = (unsigned long long)storage;
  unsigned long long total_arg = (unsigned long long)total;
  void *params[] = {&d_storage, &d_init_state, &storage_arg, &total_arg};
  trace_kernel_launch("vl_replicate_init_state_gpu", 0, -1);
  CUDA_CHECK(cuLaunchKernel(init_kfn, grid, 1, 1, (unsigned)block, 1, 1, 0, 0,
                            params, NULL));
  return 0;
}

static size_t kernel_local_size_bytes(CUfunction fn) {
  int value = 0;
  CUresult err =
      cuFuncGetAttribute(&value, CU_FUNC_ATTRIBUTE_LOCAL_SIZE_BYTES, fn);
  if (err != CUDA_SUCCESS || value < 0)
    return 0;
  return (size_t)value;
}

static int trim_csv_token(char *tok, char **out) {
  while (*tok == ' ' || *tok == '\t')
    tok++;
  size_t L = strlen(tok);
  while (L > 0 && (tok[L - 1] == ' ' || tok[L - 1] == '\t'))
    tok[--L] = '\0';
  *out = tok;
  return tok[0] != '\0';
}

static int load_module_chain(const char *fallback_cubin_path, CUmodule *mods,
                             int *nmods) {
  const char *cchain = getenv(ENV_CUBIN_CHAIN);
  *nmods = 0;
  if (cchain && cchain[0] != '\0') {
    char *buf = strdup(cchain);
    if (!buf) {
      fprintf(stderr, "strdup failed\n");
      return 1;
    }
    for (char *raw = strtok(buf, ","); raw != NULL; raw = strtok(NULL, ",")) {
      char *path = NULL;
      if (!trim_csv_token(raw, &path))
        continue;
      if (*nmods >= MAX_CUBIN_CHAIN) {
        fprintf(stderr, "too many cubins in %s (max %d)\n", ENV_CUBIN_CHAIN,
                MAX_CUBIN_CHAIN);
        free(buf);
        return 1;
      }
      trace_stage("before_cuModuleLoad");
      CUDA_CHECK(cuModuleLoad(&mods[*nmods], path));
      (*nmods)++;
      trace_stage("after_cuModuleLoad");
    }
    free(buf);
  } else {
    trace_stage("before_cuModuleLoad");
    CUDA_CHECK(cuModuleLoad(&mods[0], fallback_cubin_path));
    *nmods = 1;
    trace_stage("after_cuModuleLoad");
  }
  if (*nmods < 1) {
    fprintf(stderr, "no cubins to load\n");
    return 1;
  }
  return 0;
}

static int resolve_function_across_modules(CUfunction *out, CUmodule *mods,
                                           int nmods, const char *kernel_name) {
  CUresult last_err = CUDA_ERROR_NOT_FOUND;
  for (int module_idx = 0; module_idx < nmods; module_idx++) {
    CUresult gr = cuModuleGetFunction(out, mods[module_idx], kernel_name);
    if (gr == CUDA_SUCCESS)
      return 0;
    last_err = gr;
  }
  {
    const char *em = NULL;
    cuGetErrorString(last_err, &em);
    fprintf(stderr, "cuModuleGetFunction(%s) across %d module(s): %d %s\n",
            kernel_name, nmods, (int)last_err, em ? em : "?");
  }
  return 1;
}

static int resolve_optional_function_across_modules(CUfunction *out, CUmodule *mods,
                                                   int nmods,
                                                   const char *kernel_name) {
  for (int module_idx = 0; module_idx < nmods; module_idx++) {
    CUresult gr = cuModuleGetFunction(out, mods[module_idx], kernel_name);
    if (gr == CUDA_SUCCESS)
      return 1;
  }
  *out = NULL;
  return 0;
}

static int resolve_optional_function_across_modules_with_index(
    CUfunction *out, int *out_module_idx, CUmodule *mods, int nmods,
    const char *kernel_name) {
  for (int module_idx = 0; module_idx < nmods; module_idx++) {
    CUresult gr = cuModuleGetFunction(out, mods[module_idx], kernel_name);
    if (gr == CUDA_SUCCESS) {
      if (out_module_idx)
        *out_module_idx = module_idx;
      return 1;
    }
  }
  *out = NULL;
  if (out_module_idx)
    *out_module_idx = -1;
  return 0;
}

static int resolve_global_across_modules(CUdeviceptr *out, size_t *out_bytes,
                                         CUmodule *mods, int nmods,
                                         const char *global_name) {
  CUresult last_err = CUDA_ERROR_NOT_FOUND;
  for (int module_idx = 0; module_idx < nmods; module_idx++) {
    CUresult gr = cuModuleGetGlobal(out, out_bytes, mods[module_idx], global_name);
    if (gr == CUDA_SUCCESS)
      return 0;
    last_err = gr;
  }
  {
    const char *em = NULL;
    cuGetErrorString(last_err, &em);
    fprintf(stderr, "cuModuleGetGlobal(%s) across %d module(s): %d %s\n",
            global_name, nmods, (int)last_err, em ? em : "?");
  }
  return 1;
}

static int resolve_optional_global_across_modules(CUdeviceptr *out,
                                                  size_t *out_bytes,
                                                  CUmodule *mods, int nmods,
                                                  const char *global_name) {
  for (int module_idx = 0; module_idx < nmods; module_idx++) {
    CUresult gr = cuModuleGetGlobal(out, out_bytes, mods[module_idx], global_name);
    if (gr == CUDA_SUCCESS)
      return 1;
  }
  *out = 0;
  *out_bytes = 0;
  return 0;
}

static int resolve_optional_global_in_module(CUdeviceptr *out,
                                             size_t *out_bytes,
                                             CUmodule mod,
                                             const char *global_name) {
  CUresult gr = cuModuleGetGlobal(out, out_bytes, mod, global_name);
  if (gr == CUDA_SUCCESS)
    return 1;
  *out = 0;
  *out_bytes = 0;
  return 0;
}

static int dump_one_device_global(CUmodule *mods, int nmods,
                                  const char *global_name, const char *path) {
  CUdeviceptr d_global = 0;
  size_t bytes = 0;
  unsigned char *host = NULL;
  FILE *fp = NULL;
  size_t nw = 0;
  if (resolve_global_across_modules(&d_global, &bytes, mods, nmods, global_name) != 0)
    return 1;
  host = (unsigned char *)malloc(bytes ? bytes : 1);
  if (!host) {
    fprintf(stderr, "malloc failed for %zu-byte global dump %s\n", bytes,
            global_name);
    return 1;
  }
  if (bytes)
    CUDA_CHECK(cuMemcpyDtoH(host, d_global, bytes));
  fp = fopen(path, "wb");
  if (!fp) {
    fprintf(stderr, "fopen(%s) failed\n", path);
    free(host);
    return 1;
  }
  nw = bytes ? fwrite(host, 1, bytes, fp) : 0;
  fclose(fp);
  free(host);
  if (nw != bytes) {
    fprintf(stderr, "short write to %s: wrote %zu / %zu bytes\n", path, nw,
            bytes);
    return 1;
  }
  printf("global_dump: %s %s (%zu bytes)\n", global_name, path, bytes);
  return 0;
}

static int dump_device_global_specs(CUmodule *mods, int nmods,
                                    const char *specs) {
  char *buf = strdup(specs);
  if (!buf) {
    fprintf(stderr, "strdup failed\n");
    return 1;
  }
  for (char *raw = strtok(buf, ","); raw != NULL; raw = strtok(NULL, ",")) {
    char *spec = NULL;
    char *colon = NULL;
    char *global_name = NULL;
    char *path = NULL;
    if (!trim_csv_token(raw, &spec))
      continue;
    colon = strchr(spec, ':');
    if (!colon || colon == spec || colon[1] == '\0') {
      fprintf(stderr, "bad %s entry '%s' (want global_name:path)\n",
              ENV_DUMP_GLOBALS, spec);
      free(buf);
      return 1;
    }
    *colon = '\0';
    trim_csv_token(spec, &global_name);
    trim_csv_token(colon + 1, &path);
    if (global_name[0] == '\0' || path[0] == '\0') {
      fprintf(stderr, "bad %s entry '%s:%s' (want global_name:path)\n",
              ENV_DUMP_GLOBALS, global_name, path);
      free(buf);
      return 1;
    }
    if (dump_one_device_global(mods, nmods, global_name, path) != 0) {
      free(buf);
      return 1;
    }
  }
  free(buf);
  return 0;
}

static int append_feedback_increment(FeedbackIncrementTable *increments,
                                     unsigned *capacity,
                                     size_t storage,
                                     size_t offset,
                                     unsigned char delta) {
  if (offset >= storage) {
    fprintf(stderr,
            "feedback increment local offset out of range: offset=%zu storage=%zu\n",
            offset, storage);
    return -1;
  }
  if (increments->increment_count == *capacity) {
    unsigned new_capacity = *capacity ? (*capacity * 2U) : 8U;
    size_t *grown_offsets =
        (size_t *)realloc(increments->offsets,
                          (size_t)new_capacity * sizeof(*increments->offsets));
    if (!grown_offsets)
      return -1;
    increments->offsets = grown_offsets;
    unsigned char *grown_deltas =
        (unsigned char *)realloc(increments->deltas,
                                 (size_t)new_capacity * sizeof(*increments->deltas));
    if (!grown_deltas)
      return -1;
    increments->deltas = grown_deltas;
    *capacity = new_capacity;
  }
  increments->offsets[increments->increment_count] = offset;
  increments->deltas[increments->increment_count] = delta;
  increments->increment_count++;
  return 0;
}

static int parse_feedback_increments(const char *raw, size_t storage,
                                     FeedbackIncrementTable *out) {
  char *buf = NULL;
  unsigned capacity = 0U;
  memset(out, 0, sizeof(*out));
  if (!raw || raw[0] == '\0')
    return 0;
  buf = strdup(raw);
  if (!buf) {
    fprintf(stderr, "strdup failed for %s\n", ENV_FEEDBACK_INCREMENTS);
    return -1;
  }
  for (char *tok = strtok(buf, ","); tok != NULL; tok = strtok(NULL, ",")) {
    char *spec = NULL;
    char *colon = NULL;
    char *end = NULL;
    unsigned long long offset_ull = 0ULL;
    unsigned long long delta_ull = 0ULL;
    while (*tok && isspace((unsigned char)*tok))
      tok++;
    char *trim_end = tok + strlen(tok);
    while (trim_end > tok && isspace((unsigned char)trim_end[-1]))
      *--trim_end = '\0';
    if (*tok == '\0')
      continue;
    spec = tok;
    colon = strchr(spec, ':');
    if (!colon || colon == spec || colon[1] == '\0') {
      fprintf(stderr, "bad %s entry '%s' (want offset_local:delta_byte)\n",
              ENV_FEEDBACK_INCREMENTS, spec);
      free(buf);
      free_feedback_increment_table(out);
      return -1;
    }
    *colon = '\0';
    offset_ull = strtoull(spec, &end, 0);
    if (end == spec || *end != '\0') {
      fprintf(stderr, "bad %s offset '%s'\n", ENV_FEEDBACK_INCREMENTS, spec);
      free(buf);
      free_feedback_increment_table(out);
      return -1;
    }
    delta_ull = strtoull(colon + 1, &end, 0);
    if (end == colon + 1 || *end != '\0' || delta_ull > 255ULL) {
      fprintf(stderr, "bad %s delta '%s'\n", ENV_FEEDBACK_INCREMENTS,
              colon + 1);
      free(buf);
      free_feedback_increment_table(out);
      return -1;
    }
    if (append_feedback_increment(out, &capacity, storage,
                                  (size_t)offset_ull,
                                  (unsigned char)delta_ull) != 0) {
      free(buf);
      free_feedback_increment_table(out);
      return -1;
    }
  }
  free(buf);
  if (out->increment_count == 0U) {
    fprintf(stderr, "%s did not contain any feedback increments\n",
            ENV_FEEDBACK_INCREMENTS);
    return -1;
  }
  return 0;
}

static int append_feedback_set(FeedbackSetTable *sets, unsigned *capacity,
                               size_t storage, unsigned nstates,
                               unsigned state, unsigned phase,
                               size_t offset, unsigned char value) {
  const unsigned all_states = UINT_MAX;
  if (state != all_states && state >= nstates) {
    fprintf(stderr, "feedback phase set state out of range: state=%u nstates=%u\n",
            state, nstates);
    return -1;
  }
  if (phase == 0U || phase > MAX_PERSISTENT_RESIDENT_PHASES) {
    fprintf(stderr, "feedback phase set phase out of range: phase=%u\n", phase);
    return -1;
  }
  if (offset >= storage) {
    fprintf(stderr,
            "feedback phase set local offset out of range: offset=%zu storage=%zu\n",
            offset, storage);
    return -1;
  }
  if (sets->set_count == *capacity) {
    unsigned new_capacity = *capacity ? (*capacity * 2U) : 16U;
    unsigned *grown_phases =
        (unsigned *)realloc(sets->phases,
                            (size_t)new_capacity * sizeof(*sets->phases));
    if (!grown_phases)
      return -1;
    sets->phases = grown_phases;
    unsigned *grown_states =
        (unsigned *)realloc(sets->states,
                            (size_t)new_capacity * sizeof(*sets->states));
    if (!grown_states)
      return -1;
    sets->states = grown_states;
    size_t *grown_offsets =
        (size_t *)realloc(sets->offsets,
                          (size_t)new_capacity * sizeof(*sets->offsets));
    if (!grown_offsets)
      return -1;
    sets->offsets = grown_offsets;
    unsigned char *grown_values =
        (unsigned char *)realloc(sets->values,
                                 (size_t)new_capacity * sizeof(*sets->values));
    if (!grown_values)
      return -1;
    sets->values = grown_values;
    *capacity = new_capacity;
  }
  sets->phases[sets->set_count] = phase;
  sets->states[sets->set_count] = state;
  sets->offsets[sets->set_count] = offset;
  sets->values[sets->set_count] = value;
  sets->set_count++;
  return 0;
}

static int parse_feedback_phase_sets(const char *raw, size_t storage,
                                     unsigned nstates,
                                     FeedbackSetTable *out) {
  char *buf = NULL;
  unsigned capacity = 0U;
  memset(out, 0, sizeof(*out));
  if (!raw || raw[0] == '\0')
    return 0;
  buf = strdup(raw);
  if (!buf) {
    fprintf(stderr, "strdup failed for %s\n", ENV_FEEDBACK_PHASE_SETS);
    return -1;
  }
  for (char *tok = strtok(buf, ","); tok != NULL; tok = strtok(NULL, ",")) {
    char *spec = NULL;
    char *first_colon = NULL;
    char *second_colon = NULL;
    char *third_colon = NULL;
    char *end = NULL;
    unsigned state = UINT_MAX;
    unsigned long phase_ul = 0UL;
    unsigned long long offset_ull = 0ULL;
    unsigned long long value_ull = 0ULL;
    while (*tok && isspace((unsigned char)*tok))
      tok++;
    char *trim_end = tok + strlen(tok);
    while (trim_end > tok && isspace((unsigned char)trim_end[-1]))
      *--trim_end = '\0';
    if (*tok == '\0')
      continue;
    spec = tok;
    if (spec[0] == '@') {
      unsigned long state_ul = 0UL;
      char *state_end = NULL;
      first_colon = strchr(spec, ':');
      if (!first_colon || first_colon == spec + 1 || first_colon[1] == '\0') {
        fprintf(stderr,
                "bad %s entry '%s' (want phase:offset_local:value_byte or @state:phase:offset_local:value_byte)\n",
                ENV_FEEDBACK_PHASE_SETS, spec);
        free(buf);
        free_feedback_set_table(out);
        return -1;
      }
      *first_colon = '\0';
      state_ul = strtoul(spec + 1, &state_end, 0);
      if (state_end == spec + 1 || *state_end != '\0' ||
          state_ul > (unsigned long)UINT_MAX) {
        fprintf(stderr, "bad %s state '%s'\n", ENV_FEEDBACK_PHASE_SETS,
                spec + 1);
        free(buf);
        free_feedback_set_table(out);
        return -1;
      }
      state = (unsigned)state_ul;
      spec = first_colon + 1;
    }
    first_colon = strchr(spec, ':');
    if (!first_colon || first_colon == spec || first_colon[1] == '\0') {
      fprintf(stderr,
              "bad %s entry '%s' (want phase:offset_local:value_byte or @state:phase:offset_local:value_byte)\n",
              ENV_FEEDBACK_PHASE_SETS, spec);
      free(buf);
      free_feedback_set_table(out);
      return -1;
    }
    *first_colon = '\0';
    second_colon = strchr(first_colon + 1, ':');
    if (!second_colon || second_colon == first_colon + 1 ||
        second_colon[1] == '\0') {
      fprintf(stderr,
              "bad %s entry '%s:%s' (want phase:offset_local:value_byte or @state:phase:offset_local:value_byte)\n",
              ENV_FEEDBACK_PHASE_SETS, spec, first_colon + 1);
      free(buf);
      free_feedback_set_table(out);
      return -1;
    }
    *second_colon = '\0';
    third_colon = strchr(second_colon + 1, ':');
    if (third_colon) {
      fprintf(stderr,
              "bad %s entry with too many fields (want phase:offset_local:value_byte or @state:phase:offset_local:value_byte)\n",
              ENV_FEEDBACK_PHASE_SETS);
      free(buf);
      free_feedback_set_table(out);
      return -1;
    }
    phase_ul = strtoul(spec, &end, 0);
    if (end == spec || *end != '\0' || phase_ul == 0UL ||
        phase_ul > MAX_PERSISTENT_RESIDENT_PHASES) {
      fprintf(stderr, "bad %s phase '%s'\n", ENV_FEEDBACK_PHASE_SETS, spec);
      free(buf);
      free_feedback_set_table(out);
      return -1;
    }
    offset_ull = strtoull(first_colon + 1, &end, 0);
    if (end == first_colon + 1 || *end != '\0') {
      fprintf(stderr, "bad %s offset '%s'\n", ENV_FEEDBACK_PHASE_SETS,
              first_colon + 1);
      free(buf);
      free_feedback_set_table(out);
      return -1;
    }
    value_ull = strtoull(second_colon + 1, &end, 0);
    if (end == second_colon + 1 || *end != '\0' || value_ull > 255ULL) {
      fprintf(stderr, "bad %s value '%s'\n", ENV_FEEDBACK_PHASE_SETS,
              second_colon + 1);
      free(buf);
      free_feedback_set_table(out);
      return -1;
    }
    if (append_feedback_set(out, &capacity, storage, nstates, state,
                            (unsigned)phase_ul, (size_t)offset_ull,
                            (unsigned char)value_ull) != 0) {
      free(buf);
      free_feedback_set_table(out);
      return -1;
    }
  }
  free(buf);
  if (out->set_count == 0U) {
    fprintf(stderr, "%s did not contain any feedback phase sets\n",
            ENV_FEEDBACK_PHASE_SETS);
    return -1;
  }
  return 0;
}

static int maybe_raise_stack_limit_for_kernels(CUfunction *kfns, int nk) {
  size_t required_stack = 0;
  size_t target_stack = 0;
  for (int i = 0; i < nk; i++) {
    size_t local_size = kernel_local_size_bytes(kfns[i]);
    if (local_size > required_stack)
      required_stack = local_size;
  }
  if (required_stack == 0)
    return 0;

  target_stack = required_stack;
  {
    size_t override_stack = 0;
    int override_status = parse_size_t_env(ENV_STACK_LIMIT_OVERRIDE, &override_stack);
    if (override_status < 0) {
      fprintf(stderr, "invalid %s='%s'\n", ENV_STACK_LIMIT_OVERRIDE,
              getenv(ENV_STACK_LIMIT_OVERRIDE));
      return 2;
    }
    if (override_status > 0)
      target_stack = override_stack;
  }

  size_t current_limit = 0;
  CUDA_CHECK(cuCtxGetLimit(&current_limit, CU_LIMIT_STACK_SIZE));
  if (trace_stages_enabled()) {
    fprintf(stderr,
            "run_vl_hybrid: ctx_limit STACK_SIZE current=%zu required=%zu target=%zu\n",
            current_limit, required_stack, target_stack);
  }
  if (target_stack <= current_limit)
    return 0;
  {
    CUresult err = cuCtxSetLimit(CU_LIMIT_STACK_SIZE, target_stack);
    if (err != CUDA_SUCCESS) {
      const char *msg = NULL;
      cuGetErrorString(err, &msg);
      if (trace_stages_enabled()) {
        fprintf(stderr,
                "run_vl_hybrid: ctx_limit STACK_SIZE set_failed target=%zu err=%d:%s\n",
                target_stack, (int)err, msg ? msg : "?");
      }
      return 1;
    }
  }
  if (trace_stages_enabled()) {
    size_t updated_limit = 0;
    CUDA_CHECK(cuCtxGetLimit(&updated_limit, CU_LIMIT_STACK_SIZE));
    fprintf(stderr, "run_vl_hybrid: ctx_limit STACK_SIZE updated=%zu\n",
            updated_limit);
  }
  return 0;
}

int main(int argc, char **argv) {
  if (trace_stages_enabled())
    setvbuf(stderr, NULL, _IONBF, 0);

  if (argc < 4) {
    fprintf(stderr,
            "Usage: %s <cubin> <storage_bytes> <nstates> [block] [steps] "
            "[global_off:byte ...]\n",
            argv[0]);
    return 1;
  }

  const char *cubin_path = argv[1];
  unsigned long long storage_ull = strtoull(argv[2], NULL, 0);
  unsigned nstates = (unsigned)strtoul(argv[3], NULL, 0);
  if (storage_ull == 0ULL || storage_ull > (1ULL << 40)) {
    fprintf(stderr, "invalid storage_bytes\n");
    return 1;
  }
  if (nstates == 0U) {
    fprintf(stderr, "nstates must be >= 1\n");
    return 1;
  }
  size_t storage = (size_t)storage_ull;

  unsigned block = 256U;
  unsigned steps = 1U;
  Patch patches[MAX_PATCHES];
  int npatch = 0;
  StepPatchBlock *script_blocks = NULL;
  unsigned script_block_count = 0U;
  unsigned script_logical_step_count = 0U;
  unsigned script_record_count = 0U;
  unsigned resident_patch_script_block_count = 0U;
  ResidentPatchSchedule resident_patch_schedule;
  ResidentPatchSchedule state_local_patch_schedule;
  FeedbackEdgeTable feedback_edges;
  FeedbackIncrementTable feedback_increments;
  FeedbackSetTable feedback_phase_sets;
  OrderingAwareTerminalMaskTable ordering_aware_terminal_masks;
  EvalPartitionPredicateTable eval_partition_predicates;
  OrderingAwareTokenLoopAbiProbe ordering_aware_token_loop_abi;
  StepTrace step_trace;
  memset(&resident_patch_schedule, 0, sizeof(resident_patch_schedule));
  memset(&state_local_patch_schedule, 0, sizeof(state_local_patch_schedule));
  memset(&feedback_edges, 0, sizeof(feedback_edges));
  memset(&feedback_increments, 0, sizeof(feedback_increments));
  memset(&feedback_phase_sets, 0, sizeof(feedback_phase_sets));
  memset(&ordering_aware_terminal_masks, 0, sizeof(ordering_aware_terminal_masks));
  memset(&eval_partition_predicates, 0, sizeof(eval_partition_predicates));
  memset(&ordering_aware_token_loop_abi, 0, sizeof(ordering_aware_token_loop_abi));
  memset(&step_trace, 0, sizeof(step_trace));
  CUfunction resident_patch_kfn = NULL;
  CUfunction fused_patch_eval_kfn = NULL;
  CUfunction fused_pair_cycle_kfn = NULL;
  CUfunction fused_pair_cycle_loop_kfn = NULL;
  CUfunction fused_pair_cycle_state_local_kfn = NULL;
  CUfunction init_replication_kfn = NULL;
  CUfunction feedback_edge_kfn = NULL;
  CUfunction feedback_increment_kfn = NULL;
  CUfunction feedback_set_kfn = NULL;
  CUfunction feedback_combined_kfn = NULL;
  CUfunction ordering_aware_token_loop_kfn = NULL;
  CUfunction ordering_aware_region_timing_kfn = NULL;
  CUfunction u64_load_probe_kfn = NULL;
  int ordering_aware_token_loop_module_idx = -1;
  int u64_load_probe_module_idx = -1;
  int ordering_aware_progress_global_module_idx = -1;

  int pi = 4;
  if (argc > 4 && strchr(argv[4], ':') == NULL && strlen(argv[4]) > 0) {
    unsigned b = (unsigned)strtoul(argv[4], NULL, 0);
    if (b > 0U && b <= 1024U)
      block = b;
    pi++;
  }
  if (argc > pi && strchr(argv[pi], ':') == NULL && strlen(argv[pi]) > 0) {
    unsigned s = (unsigned)strtoul(argv[pi], NULL, 0);
    if (s > 0U)
      steps = s;
    pi++;
  }
  for (; pi < argc; pi++) {
    if (npatch >= MAX_PATCHES) {
      fprintf(stderr, "too many patches (max %d)\n", MAX_PATCHES);
      return 1;
    }
    if (parse_patch_for_storage(argv[pi], storage, nstates, &patches[npatch]) != 0) {
      fprintf(stderr,
              "bad patch '%s' (want global_offset:byte or @state:local_offset:byte)\n",
              argv[pi]);
      return 1;
    }
    npatch++;
  }

  const int resident_steps = getenv(ENV_RESIDENT_STEPS) != NULL;
  const int fused_patch_eval_requested = env_flag_enabled(ENV_FUSED_PATCH_EVAL);
  int fused_patch_eval_available = 0;
  unsigned fused_patch_eval_launches = 0U;
  unsigned fused_patch_eval_fallbacks = 0U;
  const int fused_pair_cycle_requested = env_flag_enabled(ENV_FUSED_PAIR_CYCLE);
  int fused_pair_cycle_available = 0;
  const int fused_pair_cycle_loop_requested =
      env_flag_enabled(ENV_FUSED_PAIR_CYCLE_LOOP);
  int fused_pair_cycle_loop_available = 0;
  unsigned fused_pair_cycle_loop_kernel_launches = 0U;
  unsigned fused_pair_cycle_loop_cycles = 0U;
  unsigned fused_pair_cycle_loop_fallbacks = 0U;
  unsigned fused_pair_cycle_loop_chunk = 1000U;
  const int state_local_patches_requested =
      env_flag_enabled(ENV_STATE_LOCAL_PATCHES);
  const int replicate_state0_patches_requested =
      env_flag_enabled(ENV_REPLICATE_STATE0_PATCHES);
  int fused_pair_cycle_state_local_available = 0;
  unsigned fused_pair_cycle_state_local_launches = 0U;
  unsigned fused_pair_cycle_state_local_fallbacks = 0U;
  unsigned fused_pair_cycle_launches = 0U;
  unsigned fused_pair_cycle_fallbacks = 0U;
  const int resident_pair_cycle_requested = env_flag_enabled(ENV_RESIDENT_PAIR_CYCLE);
  unsigned resident_pair_cycle_start = 0U;
  unsigned resident_pair_cycle_launches = 0U;
  unsigned resident_pair_cycle_fallbacks = 0U;
  const char *persistent_resident_handle = getenv(ENV_PERSISTENT_RESIDENT_HANDLE);
  const int persistent_resident_requested =
      persistent_resident_handle != NULL && persistent_resident_handle[0] != '\0';
  unsigned persistent_resident_phase = 0U;
  unsigned persistent_resident_phase_count = 1U;
  char *persistent_phase_dumps[MAX_PERSISTENT_RESIDENT_PHASES];
  unsigned persistent_phase_dump_count = 0U;
  memset(persistent_phase_dumps, 0, sizeof(persistent_phase_dumps));
  const char *feedback_edge_specs = getenv(ENV_FEEDBACK_EDGES);
  const int feedback_edges_requested =
      feedback_edge_specs != NULL && feedback_edge_specs[0] != '\0';
  const char *feedback_increment_specs = getenv(ENV_FEEDBACK_INCREMENTS);
  const int feedback_increments_requested =
      feedback_increment_specs != NULL && feedback_increment_specs[0] != '\0';
  const char *feedback_phase_set_specs = getenv(ENV_FEEDBACK_PHASE_SETS);
  const int feedback_phase_sets_requested =
      feedback_phase_set_specs != NULL && feedback_phase_set_specs[0] != '\0';
  const char *ordering_aware_terminal_mask_specs =
      getenv(ENV_ORDERING_AWARE_TOKEN_LOOP_TERMINAL_MASK);
  const char *eval_partition_predicate_specs =
      getenv(ENV_EVAL_PARTITION_PREDICATES);
  const int eval_partition_predicates_requested =
      eval_partition_predicate_specs != NULL &&
      eval_partition_predicate_specs[0] != '\0';
  const int eval_partition_predicate_active_mask_authority =
      eval_partition_predicates_requested &&
      env_flag_enabled(ENV_EVAL_PARTITION_PREDICATES_ACTIVE_MASK_AUTHORITY);
  const int eval_partition_guarded_skip_requested =
      eval_partition_predicate_active_mask_authority &&
      env_flag_enabled(ENV_EVAL_PARTITION_GUARDED_SKIP);
  ordering_aware_token_loop_abi.requested =
      env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_ABI_PROBE);
  const int single_entry_cfg_clone_liveout_oracle_requested =
      env_flag_enabled(ENV_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_ORACLE_PROBE);
  const int cfg_clone_diagnostic_abi_disabled =
      env_flag_enabled(ENV_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI);
  if (cfg_clone_diagnostic_abi_disabled &&
      single_entry_cfg_clone_liveout_oracle_requested) {
    fprintf(stderr, "%s=1 conflicts with %s=1\n",
            ENV_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI,
            ENV_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_ORACLE_PROBE);
    return 1;
  }
  const int cfg_clone_diagnostic_abi_enabled =
      ordering_aware_token_loop_abi.requested &&
      !cfg_clone_diagnostic_abi_disabled;
  unsigned single_entry_cfg_clone_liveout_expected_count = 0U;
  size_t single_entry_cfg_clone_liveout_counter_count = 6U;
  const int ordering_aware_region_timing_requested =
      env_flag_enabled(ENV_ORDERING_AWARE_REGION_TIMING);
  unsigned ordering_aware_token_loop_cycle_limit = 0U;
  unsigned ordering_aware_token_loop_cycle_limit_applied = 0U;
  unsigned ordering_aware_terminal_mask_parse_error_count = 0U;
  unsigned eval_partition_predicate_parse_error_count = 0U;
  int feedback_edge_mode_phase = persistent_resident_requested;
  unsigned feedback_edge_launches = 0U;
  unsigned feedback_increment_launches = 0U;
  unsigned feedback_phase_set_launches = 0U;
  unsigned feedback_combined_launches = 0U;

  if (parse_unsigned_env_with_max(
          ENV_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_EXPECTED_COUNT,
          &single_entry_cfg_clone_liveout_expected_count,
          (unsigned long)INT_MAX) < 0) {
    fprintf(stderr, "bad %s (want unsigned integer)\n",
            ENV_SINGLE_ENTRY_CFG_CLONE_LIVEOUT_EXPECTED_COUNT);
    return 1;
  }
  if (single_entry_cfg_clone_liveout_expected_count >
      (unsigned)((SIZE_MAX / sizeof(unsigned long long) - 6U) /
                 CFG_CLONE_LIVEOUT_COUNTER_BANDS)) {
    fprintf(stderr, "single-entry CFG-clone liveout counter size overflow\n");
    return 1;
  }
  single_entry_cfg_clone_liveout_counter_count =
      6U + ((size_t)single_entry_cfg_clone_liveout_expected_count *
            CFG_CLONE_LIVEOUT_COUNTER_BANDS);
  const int gpu_replicate_init_state = getenv(ENV_GPU_REPLICATE_INIT_STATE) != NULL;
  unsigned timing_repeats = 1U;
  {
    int repeat_status = parse_unsigned_env(ENV_TIMING_REPEATS, &timing_repeats);
    if (repeat_status < 0 || timing_repeats == 0U || timing_repeats > 64U) {
      fprintf(stderr, "invalid %s (expected 1..64)\n", ENV_TIMING_REPEATS);
      return 1;
    }
  }
  if (persistent_resident_requested) {
    int phase_status = parse_unsigned_env(ENV_PERSISTENT_RESIDENT_PHASE,
                                          &persistent_resident_phase);
    int phase_count_status = parse_unsigned_env(ENV_PERSISTENT_RESIDENT_PHASE_COUNT,
                                                &persistent_resident_phase_count);
    if (!resident_steps) {
      fprintf(stderr, "%s requires %s=1\n", ENV_PERSISTENT_RESIDENT_HANDLE,
              ENV_RESIDENT_STEPS);
      return 1;
    }
    if (phase_status <= 0 || persistent_resident_phase == 0U) {
      fprintf(stderr, "%s requires a positive %s\n",
              ENV_PERSISTENT_RESIDENT_HANDLE, ENV_PERSISTENT_RESIDENT_PHASE);
      return 1;
    }
    if (phase_count_status < 0 || persistent_resident_phase_count == 0U ||
        persistent_resident_phase_count > MAX_PERSISTENT_RESIDENT_PHASES) {
      fprintf(stderr, "%s must be 1..%u\n", ENV_PERSISTENT_RESIDENT_PHASE_COUNT,
              MAX_PERSISTENT_RESIDENT_PHASES);
      return 1;
    }
    if (persistent_resident_phase > 1U && persistent_resident_phase_count <= 1U) {
      fprintf(stderr,
              "persistent resident state ABI phase %u for handle '%s' is not "
              "implemented yet; refusing to fall back to a previous phase "
              "--init-state reload\n",
              persistent_resident_phase, persistent_resident_handle);
      return 1;
    }
    if (split_csv_dup(getenv(ENV_PERSISTENT_RESIDENT_PHASE_DUMPS),
                      persistent_phase_dumps, &persistent_phase_dump_count,
                      MAX_PERSISTENT_RESIDENT_PHASES) != 0) {
      return 1;
    }
    if (persistent_phase_dump_count != 0U &&
        persistent_phase_dump_count != persistent_resident_phase_count) {
      fprintf(stderr, "%s count %u does not match %s %u\n",
              ENV_PERSISTENT_RESIDENT_PHASE_DUMPS, persistent_phase_dump_count,
              ENV_PERSISTENT_RESIDENT_PHASE_COUNT, persistent_resident_phase_count);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }
  if (feedback_edges_requested) {
    const char *mode = getenv(ENV_FEEDBACK_EDGE_MODE);
    if (!resident_steps) {
      fprintf(stderr, "%s requires %s=1\n", ENV_FEEDBACK_EDGES,
              ENV_RESIDENT_STEPS);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    feedback_edge_mode_phase =
        persistent_resident_requested && persistent_resident_phase_count > 1U;
    if (mode && mode[0] != '\0') {
      if (strcmp(mode, "phase") == 0) {
        feedback_edge_mode_phase = 1;
      } else if (strcmp(mode, "step") == 0) {
        feedback_edge_mode_phase = 0;
      } else {
        fprintf(stderr, "bad %s='%s' (want phase or step)\n",
                ENV_FEEDBACK_EDGE_MODE, mode);
        free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
        return 1;
      }
    }
    if (parse_feedback_edges(feedback_edge_specs, storage, &feedback_edges) != 0) {
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }
  if (feedback_increments_requested) {
    const char *mode = getenv(ENV_FEEDBACK_EDGE_MODE);
    if (!resident_steps) {
      fprintf(stderr, "%s requires %s=1\n", ENV_FEEDBACK_INCREMENTS,
              ENV_RESIDENT_STEPS);
      free_feedback_edge_table(&feedback_edges);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    feedback_edge_mode_phase =
        persistent_resident_requested && persistent_resident_phase_count > 1U;
    if (mode && mode[0] != '\0') {
      if (strcmp(mode, "phase") == 0) {
        feedback_edge_mode_phase = 1;
      } else if (strcmp(mode, "step") == 0) {
        feedback_edge_mode_phase = 0;
      } else {
        fprintf(stderr, "bad %s='%s' (want phase or step)\n",
                ENV_FEEDBACK_EDGE_MODE, mode);
        free_feedback_edge_table(&feedback_edges);
        free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
        return 1;
      }
    }
    if (parse_feedback_increments(feedback_increment_specs, storage,
                                  &feedback_increments) != 0) {
      free_feedback_edge_table(&feedback_edges);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }
  if (feedback_phase_sets_requested) {
    if (!resident_steps) {
      fprintf(stderr, "%s requires %s=1\n", ENV_FEEDBACK_PHASE_SETS,
              ENV_RESIDENT_STEPS);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    if (!persistent_resident_requested || persistent_resident_phase_count <= 1U) {
      fprintf(stderr, "%s requires multi-phase persistent resident ABI mode\n",
              ENV_FEEDBACK_PHASE_SETS);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    if (parse_feedback_phase_sets(feedback_phase_set_specs, storage, nstates,
                                  &feedback_phase_sets) != 0) {
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }
  if (resident_pair_cycle_requested) {
    if (!resident_steps) {
      fprintf(stderr, "%s=1 requires %s=1\n",
              ENV_RESIDENT_PAIR_CYCLE, ENV_RESIDENT_STEPS);
      return 1;
    }
    if (parse_unsigned_env(ENV_RESIDENT_PAIR_CYCLE_START,
                           &resident_pair_cycle_start) < 0) {
      fprintf(stderr, "bad %s (want unsigned integer)\n",
              ENV_RESIDENT_PAIR_CYCLE_START);
      return 1;
    }
  }

  {
    const char *patch_script_path = getenv(ENV_PATCH_SCRIPT);
    if (patch_script_path && patch_script_path[0] != '\0') {
      if (load_patch_script(patch_script_path, storage, nstates,
                            &script_blocks, &script_block_count,
                            &script_logical_step_count, &script_record_count) != 0) {
        return 1;
      }
      steps = script_logical_step_count;
    }
  }
  if (resident_steps && npatch > 0) {
    fprintf(stderr,
            "%s=1 rejects argv per-step host patches; use %s for a device-resident schedule\n",
            ENV_RESIDENT_STEPS, ENV_PATCH_SCRIPT);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (fused_pair_cycle_requested && !resident_pair_cycle_requested) {
    fprintf(stderr, "%s=1 requires %s=1\n",
            ENV_FUSED_PAIR_CYCLE, ENV_RESIDENT_PAIR_CYCLE);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (fused_pair_cycle_loop_requested) {
    if (!fused_pair_cycle_requested || !resident_pair_cycle_requested) {
      fprintf(stderr, "%s=1 requires %s=1 and %s=1\n",
              ENV_FUSED_PAIR_CYCLE_LOOP, ENV_FUSED_PAIR_CYCLE,
              ENV_RESIDENT_PAIR_CYCLE);
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
    if (parse_unsigned_env_with_max(ENV_FUSED_PAIR_CYCLE_LOOP_CHUNK,
                                    &fused_pair_cycle_loop_chunk,
                                    (unsigned long)INT_MAX) < 0) {
      fprintf(stderr, "bad %s (want unsigned integer)\n",
              ENV_FUSED_PAIR_CYCLE_LOOP_CHUNK);
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
    if (fused_pair_cycle_loop_chunk == 0U)
      fused_pair_cycle_loop_chunk = 1000U;
  }
  if (parse_unsigned_env_with_max(ENV_ORDERING_AWARE_TOKEN_LOOP_CYCLE_LIMIT,
                                  &ordering_aware_token_loop_cycle_limit,
                                  (unsigned long)INT_MAX) < 0) {
    fprintf(stderr, "bad %s (want unsigned integer)\n",
            ENV_ORDERING_AWARE_TOKEN_LOOP_CYCLE_LIMIT);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (ordering_aware_token_loop_cycle_limit != 0U &&
      ordering_aware_token_loop_cycle_limit < 2U) {
    fprintf(stderr, "%s must be 0 or >=2\n",
            ENV_ORDERING_AWARE_TOKEN_LOOP_CYCLE_LIMIT);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (state_local_patches_requested &&
      (!fused_pair_cycle_requested || !resident_pair_cycle_requested)) {
    fprintf(stderr, "%s=1 requires %s=1 and %s=1\n",
            ENV_STATE_LOCAL_PATCHES, ENV_FUSED_PAIR_CYCLE,
            ENV_RESIDENT_PAIR_CYCLE);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (resident_pair_cycle_requested && fused_patch_eval_requested) {
    fprintf(stderr,
            "%s=1 cannot be combined with %s=1; pair-cycle preserves two evals per clock cycle\n",
            ENV_RESIDENT_PAIR_CYCLE, ENV_FUSED_PATCH_EVAL);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (resident_pair_cycle_requested && resident_pair_cycle_start >= steps) {
    fprintf(stderr, "%s=%u is outside logical step count %u\n",
            ENV_RESIDENT_PAIR_CYCLE_START, resident_pair_cycle_start, steps);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (timing_repeats > 1U && npatch > 0) {
    fprintf(stderr,
            "%s > 1 rejects argv per-step host patches; use %s for a "
            "device-resident schedule\n",
            ENV_TIMING_REPEATS, ENV_PATCH_SCRIPT);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (timing_repeats > 1U &&
      (resident_steps || script_blocks || env_flag_enabled(ENV_INIT_STATE)) &&
      env_flag_enabled(ENV_STEP_TRACE)) {
    fprintf(stderr,
            "%s > 1 with resident/init-state replay requires %s unset; "
            "use final-observable dumping for repeat timing\n",
            ENV_TIMING_REPEATS, ENV_STEP_TRACE);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  if (persistent_resident_requested && persistent_resident_phase_count > 1U) {
    if (npatch > 0 || (script_blocks && !resident_steps)) {
      fprintf(stderr,
              "%s multi-phase mode rejects argv patches and host-applied patch scripts; "
              "use %s=1 with %s for a device-resident schedule\n",
              ENV_PERSISTENT_RESIDENT_HANDLE, ENV_RESIDENT_STEPS,
              ENV_PATCH_SCRIPT);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    if (script_blocks && script_logical_step_count == 0U) {
      fprintf(stderr,
              "%s multi-phase mode received an empty resident patch schedule\n",
              ENV_PERSISTENT_RESIDENT_HANDLE);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    if (timing_repeats > 1U) {
      fprintf(stderr, "%s multi-phase mode requires %s unset or 1\n",
              ENV_PERSISTENT_RESIDENT_HANDLE, ENV_TIMING_REPEATS);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }

  size_t total = storage * (size_t)nstates;
  trace_stage("before_cuInit");
  {
    CUresult err = cuInit(0);
    if (err != CUDA_SUCCESS)
      cuda_fail(__FILE__, __LINE__, err, "cuInit");
  }
  trace_stage("after_cuInit");

  CUdevice dev;
  {
    trace_stage("before_cuDeviceGet");
    CUresult err = cuDeviceGet(&dev, 0);
    if (err != CUDA_SUCCESS)
      cuda_fail(__FILE__, __LINE__, err, "cuDeviceGet");
  }
  trace_stage("after_cuDeviceGet");

  char name[256];
  CUDA_CHECK(cuDeviceGetName(name, sizeof(name), dev));
  printf("device 0: %s\n", name);
  fflush(stdout);

  trace_stage("before_cuCtxCreate");
  CUcontext ctx;
  CUDA_CHECK(cuCtxCreate(&ctx, 0, dev));
  trace_stage("after_cuCtxCreate");

  CUmodule mods[MAX_CUBIN_CHAIN];
  int nmods = 0;
  if (load_module_chain(cubin_path, mods, &nmods) != 0) {
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }

  const char *module_load_symbol_check = getenv(ENV_MODULE_LOAD_SYMBOL_CHECK);
  if (module_load_symbol_check && module_load_symbol_check[0] != '\0') {
    CUfunction checked_fn = NULL;
    trace_stage("before_module_load_symbol_check");
    if (resolve_function_across_modules(&checked_fn, mods, nmods,
                                        module_load_symbol_check) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      CUDA_CHECK(cuCtxDestroy(ctx));
      return 1;
    }
    trace_stage("after_module_load_symbol_check");
    printf("module_load_symbol_check: passed symbol=%s modules=%d\n",
           module_load_symbol_check, nmods);
    free_step_patch_blocks(script_blocks, script_block_count);
    CUDA_CHECK(cuCtxDestroy(ctx));
    return 0;
  }

  CUfunction kfns[MAX_KERNEL_CHAIN];
  char kernel_names[MAX_KERNEL_CHAIN][256];
  int nk = 0;
  const char *kchain = getenv(ENV_KERNEL_CHAIN);
  if (kchain && kchain[0] != '\0') {
    char *buf = strdup(kchain);
    if (!buf) {
      fprintf(stderr, "strdup failed\n");
      return 1;
    }
    for (char *tok = strtok(buf, ","); tok != NULL; tok = strtok(NULL, ",")) {
      char *kernel_name = NULL;
      if (!trim_csv_token(tok, &kernel_name))
        continue;
      if (nk >= MAX_KERNEL_CHAIN) {
        fprintf(stderr, "too many kernels in %s (max %d)\n", ENV_KERNEL_CHAIN,
                MAX_KERNEL_CHAIN);
        free(buf);
        return 1;
      }
      if (resolve_function_across_modules(&kfns[nk], mods, nmods,
                                          kernel_name) != 0) {
        free(buf);
        return 1;
      }
      snprintf(kernel_names[nk], sizeof(kernel_names[nk]), "%s", kernel_name);
      trace_function_attrs(kfns[nk], kernel_names[nk]);
      nk++;
    }
    free(buf);
  } else {
    if (resolve_function_across_modules(&kfns[0], mods, nmods,
                                        "vl_eval_batch_gpu") != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
    snprintf(kernel_names[0], sizeof(kernel_names[0]), "%s",
             "vl_eval_batch_gpu");
    trace_function_attrs(kfns[0], kernel_names[0]);
    nk = 1;
  }
  if (nk < 1) {
    fprintf(stderr, "no kernels to launch\n");
    return 1;
  }
  if (resident_steps && script_blocks) {
    if (resolve_function_across_modules(&resident_patch_kfn, mods, nmods,
                                        "vl_apply_patch_schedule_gpu") != 0) {
      fprintf(stderr,
              "resident %s requires a cubin regenerated with vl_apply_patch_schedule_gpu\n",
              ENV_PATCH_SCRIPT);
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
    trace_function_attrs(resident_patch_kfn, "vl_apply_patch_schedule_gpu");
    if (fused_patch_eval_requested) {
      fused_patch_eval_available = resolve_optional_function_across_modules(
          &fused_patch_eval_kfn, mods, nmods, "vl_patch_eval_batch_gpu");
      if (fused_patch_eval_available)
        trace_function_attrs(fused_patch_eval_kfn, "vl_patch_eval_batch_gpu");
    }
    if (fused_pair_cycle_requested) {
      fused_pair_cycle_available = resolve_optional_function_across_modules(
          &fused_pair_cycle_kfn, mods, nmods, "vl_patch_eval_pair_cycle_batch_gpu");
      if (fused_pair_cycle_available)
        trace_function_attrs(fused_pair_cycle_kfn,
                             "vl_patch_eval_pair_cycle_batch_gpu");
      if (fused_pair_cycle_loop_requested) {
        fused_pair_cycle_loop_available =
            resolve_optional_function_across_modules(
                &fused_pair_cycle_loop_kfn, mods, nmods,
                "vl_patch_eval_pair_cycle_loop_batch_gpu");
        if (fused_pair_cycle_loop_available)
          trace_function_attrs(fused_pair_cycle_loop_kfn,
                               "vl_patch_eval_pair_cycle_loop_batch_gpu");
      }
      if (state_local_patches_requested) {
        fused_pair_cycle_state_local_available =
            resolve_optional_function_across_modules(
                &fused_pair_cycle_state_local_kfn, mods, nmods,
                "vl_patch_eval_pair_cycle_batch_gpu_state_local");
        if (fused_pair_cycle_state_local_available)
          trace_function_attrs(
              fused_pair_cycle_state_local_kfn,
              "vl_patch_eval_pair_cycle_batch_gpu_state_local");
      }
    }
  }
  if (feedback_edges_requested) {
    if (resolve_function_across_modules(&feedback_edge_kfn, mods, nmods,
                                        "vl_apply_feedback_edges_gpu") != 0) {
      fprintf(stderr,
              "%s requires a cubin regenerated with vl_apply_feedback_edges_gpu\n",
              ENV_FEEDBACK_EDGES);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    trace_function_attrs(feedback_edge_kfn, "vl_apply_feedback_edges_gpu");
  }
  if (feedback_increments_requested) {
    if (resolve_function_across_modules(&feedback_increment_kfn, mods, nmods,
                                        "vl_apply_feedback_increments_gpu") != 0) {
      fprintf(stderr,
              "%s requires a cubin regenerated with vl_apply_feedback_increments_gpu\n",
              ENV_FEEDBACK_INCREMENTS);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    trace_function_attrs(feedback_increment_kfn,
                         "vl_apply_feedback_increments_gpu");
  }
  if (feedback_phase_sets_requested) {
    if (resolve_function_across_modules(&feedback_set_kfn, mods, nmods,
                                        "vl_apply_feedback_sets_gpu") != 0) {
      fprintf(stderr,
              "%s requires a cubin regenerated with vl_apply_feedback_sets_gpu\n",
              ENV_FEEDBACK_PHASE_SETS);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_feedback_set_table(&feedback_phase_sets);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    trace_function_attrs(feedback_set_kfn, "vl_apply_feedback_sets_gpu");
  }
  int feedback_combined_available = 0;
  if (feedback_edge_mode_phase && feedback_edges_requested &&
      feedback_increments_requested && feedback_phase_sets_requested) {
    feedback_combined_available =
        resolve_optional_function_across_modules(&feedback_combined_kfn, mods,
                                                 nmods,
                                                 "vl_apply_feedback_combined_gpu");
    if (feedback_combined_available)
      trace_function_attrs(feedback_combined_kfn,
                           "vl_apply_feedback_combined_gpu");
  }
  int ordering_aware_token_loop_available = 0;
  int ordering_aware_region_timing_available = 0;
  if (ordering_aware_token_loop_abi.requested || ordering_aware_region_timing_requested) {
    ordering_aware_token_loop_available = resolve_optional_function_across_modules_with_index(
        &ordering_aware_token_loop_kfn, &ordering_aware_token_loop_module_idx,
        mods, nmods,
        "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu");
    if (ordering_aware_token_loop_available)
      trace_function_attrs(ordering_aware_token_loop_kfn,
                           "vl_tb_core_ordering_aware_phase_resident_token_loop_gpu");
    if (env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_HIGH_PATCH_DIAGNOSTIC)) {
      if (resolve_optional_function_across_modules_with_index(
              &u64_load_probe_kfn, &u64_load_probe_module_idx, mods, nmods,
              "vl_probe_u64_load_gpu"))
        trace_function_attrs(u64_load_probe_kfn, "vl_probe_u64_load_gpu");
    }
  }
  if (ordering_aware_region_timing_requested) {
    ordering_aware_region_timing_available = resolve_optional_function_across_modules(
        &ordering_aware_region_timing_kfn, mods, nmods,
        "vl_tb_core_ordering_aware_phase_resident_token_loop_region_timing_gpu");
    if (!ordering_aware_region_timing_available) {
      fprintf(stderr,
              "%s=1 requires vl_tb_core_ordering_aware_phase_resident_token_loop_region_timing_gpu\n",
              ENV_ORDERING_AWARE_REGION_TIMING);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_feedback_set_table(&feedback_phase_sets);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    trace_function_attrs(
        ordering_aware_region_timing_kfn,
        "vl_tb_core_ordering_aware_phase_resident_token_loop_region_timing_gpu");
    ordering_aware_token_loop_kfn = ordering_aware_region_timing_kfn;
    ordering_aware_token_loop_available = 1;
  }
  if (gpu_replicate_init_state) {
    if (resolve_function_across_modules(&init_replication_kfn, mods, nmods,
                                        "vl_replicate_init_state_gpu") != 0) {
      fprintf(stderr,
              "%s=1 requires a cubin regenerated with vl_replicate_init_state_gpu\n",
              ENV_GPU_REPLICATE_INIT_STATE);
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
    trace_function_attrs(init_replication_kfn, "vl_replicate_init_state_gpu");
  }
  {
    int stack_limit_status = maybe_raise_stack_limit_for_kernels(kfns, nk);
    if (env_flag_enabled(ENV_STACK_LIMIT_PROBE_ONLY))
      return stack_limit_status;
    if (stack_limit_status != 0) {
      fprintf(stderr, "stack-limit setup failed with status=%d\n", stack_limit_status);
      return stack_limit_status;
    }
  }
  trace_stage("after_kernel_resolution");

  CUdeviceptr d_storage = 0;
  CUdeviceptr d_initial_snapshot = 0;
  CUdeviceptr d_single_entry_cfg_clone_liveout_counters = 0;
  CUdeviceptr d_cfg_clone_shadow_descriptor_records = 0;
  CUdeviceptr d_cfg_clone_shadow_payload = 0;
  CUdeviceptr d_ordering_aware_region_cycles = 0;
  CUdeviceptr d_ordering_aware_region_cycles_global = 0;
  CUdeviceptr d_ordering_aware_token_loop_progress = 0;
  CUdeviceptr d_ordering_aware_token_loop_progress_global = 0;
  unsigned long long *h_ordering_aware_token_loop_progress = NULL;
  size_t ordering_aware_region_cycles_global_bytes = 0U;
  size_t ordering_aware_token_loop_progress_global_bytes = 0U;
  int ordering_aware_region_cycles_global_available = 0;
  int ordering_aware_token_loop_progress_global_available = 0;
  const int ordering_aware_region_counter_global_init_requested =
      env_flag_enabled(ENV_ORDERING_AWARE_REGION_COUNTER_GLOBAL_INIT);
  const int ordering_aware_token_loop_progress_requested =
      env_flag_enabled(ENV_ORDERING_AWARE_TOKEN_LOOP_PROGRESS);
  struct ordering_aware_token_loop_progress_watchdog
      ordering_aware_token_loop_progress_watchdog;
  memset(&ordering_aware_token_loop_progress_watchdog, 0,
         sizeof(ordering_aware_token_loop_progress_watchdog));
  size_t cfg_clone_shadow_payload_total_bytes = 0U;
  if (ordering_aware_region_timing_requested ||
      ordering_aware_region_counter_global_init_requested) {
    ordering_aware_region_cycles_global_available =
        resolve_optional_global_across_modules(
            &d_ordering_aware_region_cycles_global,
            &ordering_aware_region_cycles_global_bytes, mods, nmods,
            "__vlgpu_ordering_aware_region_cycle_counters");
  }
  if (ordering_aware_region_cycles_global_available &&
      ordering_aware_region_cycles_global_bytes < sizeof(CUdeviceptr)) {
    fprintf(stderr,
            "__vlgpu_ordering_aware_region_cycle_counters is %zu bytes, "
            "expected at least %zu\n",
            ordering_aware_region_cycles_global_bytes, sizeof(CUdeviceptr));
    return 1;
  }
  if (ordering_aware_token_loop_progress_requested) {
    if (ordering_aware_token_loop_module_idx >= 0 &&
        ordering_aware_token_loop_module_idx < nmods) {
      ordering_aware_token_loop_progress_global_available =
          resolve_optional_global_in_module(
            &d_ordering_aware_token_loop_progress_global,
            &ordering_aware_token_loop_progress_global_bytes,
            mods[ordering_aware_token_loop_module_idx],
            "__vlgpu_ordering_aware_token_loop_progress_counters");
      if (ordering_aware_token_loop_progress_global_available)
        ordering_aware_progress_global_module_idx =
            ordering_aware_token_loop_module_idx;
    }
    if (!ordering_aware_token_loop_progress_global_available) {
      ordering_aware_token_loop_progress_global_available =
          resolve_optional_global_across_modules(
              &d_ordering_aware_token_loop_progress_global,
              &ordering_aware_token_loop_progress_global_bytes, mods, nmods,
              "__vlgpu_ordering_aware_token_loop_progress_counters");
      if (ordering_aware_token_loop_progress_global_available)
        ordering_aware_progress_global_module_idx = -2;
    }
    if (!ordering_aware_token_loop_progress_global_available) {
      fprintf(stderr,
              "%s=1 requires a cubin regenerated with "
              "__vlgpu_ordering_aware_token_loop_progress_counters\n",
              ENV_ORDERING_AWARE_TOKEN_LOOP_PROGRESS);
      return 1;
    }
    if (ordering_aware_token_loop_progress_global_bytes < sizeof(CUdeviceptr)) {
      fprintf(stderr,
              "__vlgpu_ordering_aware_token_loop_progress_counters is %zu "
              "bytes, expected at least %zu\n",
              ordering_aware_token_loop_progress_global_bytes,
              sizeof(CUdeviceptr));
      return 1;
    }
  }
  if (cfg_clone_diagnostic_abi_enabled) {
    if ((size_t)nstates >
        SIZE_MAX / (size_t)CFG_CLONE_SHADOW_PAYLOAD_BYTES_PER_STATE) {
      fprintf(stderr, "cfg-clone shadow payload size overflow\n");
      return 1;
    }
    cfg_clone_shadow_payload_total_bytes =
        (size_t)nstates *
        (size_t)CFG_CLONE_SHADOW_PAYLOAD_BYTES_PER_STATE;
    ordering_aware_token_loop_abi.cfg_clone_shadow_payload_total_bytes =
        cfg_clone_shadow_payload_total_bytes;
  }
  trace_stage("before_cuMemAlloc");
  CUDA_CHECK(cuMemAlloc(&d_storage, total));
  CUDA_CHECK(cuMemsetD8(d_storage, 0, total));
  if (cfg_clone_diagnostic_abi_enabled) {
    CUDA_CHECK(cuMemAlloc(&d_single_entry_cfg_clone_liveout_counters,
                          single_entry_cfg_clone_liveout_counter_count *
                              sizeof(unsigned long long)));
    CUDA_CHECK(cuMemsetD8(d_single_entry_cfg_clone_liveout_counters, 0,
                          single_entry_cfg_clone_liveout_counter_count *
                              sizeof(unsigned long long)));
    CUDA_CHECK(cuMemAlloc(&d_cfg_clone_shadow_descriptor_records,
                          CFG_CLONE_SHADOW_DESCRIPTOR_COUNT *
                              CFG_CLONE_SHADOW_DESCRIPTOR_RECORD_BYTES));
    CUDA_CHECK(cuMemsetD8(d_cfg_clone_shadow_descriptor_records, 0,
                          CFG_CLONE_SHADOW_DESCRIPTOR_COUNT *
                              CFG_CLONE_SHADOW_DESCRIPTOR_RECORD_BYTES));
    CUDA_CHECK(cuMemAlloc(&d_cfg_clone_shadow_payload,
                          cfg_clone_shadow_payload_total_bytes));
    CUDA_CHECK(cuMemsetD8(d_cfg_clone_shadow_payload, 0,
                          cfg_clone_shadow_payload_total_bytes));
  }
  if (ordering_aware_region_timing_requested ||
      ordering_aware_region_cycles_global_available) {
    CUDA_CHECK(cuMemAlloc(&d_ordering_aware_region_cycles,
                          ORDERING_AWARE_REGION_TIMING_COUNTERS *
                              sizeof(unsigned long long)));
    CUDA_CHECK(cuMemsetD8(d_ordering_aware_region_cycles, 0,
                          ORDERING_AWARE_REGION_TIMING_COUNTERS *
                              sizeof(unsigned long long)));
  }
  if (ordering_aware_token_loop_progress_requested) {
    CUDA_CHECK(cuMemHostAlloc(
        (void **)&h_ordering_aware_token_loop_progress,
        ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS *
            sizeof(unsigned long long),
        CU_MEMHOSTALLOC_DEVICEMAP));
    memset(h_ordering_aware_token_loop_progress, 0,
           ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS *
               sizeof(unsigned long long));
    CUDA_CHECK(cuMemHostGetDevicePointer(
        &d_ordering_aware_token_loop_progress,
        h_ordering_aware_token_loop_progress, 0));
  }
  trace_stage("after_cuMemAlloc");
  if (ordering_aware_region_cycles_global_available) {
    trace_stage("before_ordering_aware_region_counter_global_init");
    CUDA_CHECK(cuMemcpyHtoD(d_ordering_aware_region_cycles_global,
                            &d_ordering_aware_region_cycles,
                            sizeof(d_ordering_aware_region_cycles)));
    trace_stage("after_ordering_aware_region_counter_global_init");
  }
  if (ordering_aware_token_loop_progress_requested) {
    trace_stage("before_ordering_aware_token_loop_progress_global_init");
    CUDA_CHECK(cuMemcpyHtoD(d_ordering_aware_token_loop_progress_global,
                            &d_ordering_aware_token_loop_progress,
                            sizeof(d_ordering_aware_token_loop_progress)));
    if (env_flag_enabled(
            ENV_ORDERING_AWARE_TOKEN_LOOP_PROGRESS_GLOBAL_DIAGNOSTIC)) {
      CUdeviceptr roundtrip_ordering_aware_token_loop_progress = 0;
      CUresult progress_global_copy_result = cuMemcpyDtoH(
          &roundtrip_ordering_aware_token_loop_progress,
          d_ordering_aware_token_loop_progress_global,
          sizeof(roundtrip_ordering_aware_token_loop_progress));
      print_ordering_aware_token_loop_progress_global_diagnostic(
          progress_global_copy_result == CUDA_SUCCESS ? "initialized"
                                                      : "dtoh_failed",
          d_ordering_aware_token_loop_progress_global,
          ordering_aware_token_loop_progress_global_bytes,
          ordering_aware_progress_global_module_idx,
          ordering_aware_token_loop_module_idx,
          h_ordering_aware_token_loop_progress,
          d_ordering_aware_token_loop_progress,
          roundtrip_ordering_aware_token_loop_progress,
          progress_global_copy_result);
      if (progress_global_copy_result != CUDA_SUCCESS) {
        cuda_fail(__FILE__, __LINE__, progress_global_copy_result,
                  "ordering-aware token-loop progress global diagnostic");
      }
    }
    trace_stage("after_ordering_aware_token_loop_progress_global_init");
  }

  {
    const char *init_state_path = getenv(ENV_INIT_STATE);
    if (init_state_path && init_state_path[0] != '\0') {
      trace_stage("before_init_state_upload");
      FILE *fp = fopen(init_state_path, "rb");
      if (!fp) {
        fprintf(stderr, "failed to open %s=%s\n", ENV_INIT_STATE, init_state_path);
        return 1;
      }
      if (fseek(fp, 0, SEEK_END) != 0) {
        fclose(fp);
        free_step_patch_blocks(script_blocks, script_block_count);
        fprintf(stderr, "failed to seek %s\n", init_state_path);
        return 1;
      }
      long file_size_long = ftell(fp);
      if (file_size_long < 0) {
        fclose(fp);
        free_step_patch_blocks(script_blocks, script_block_count);
        fprintf(stderr, "failed to stat %s\n", init_state_path);
        return 1;
      }
      if (fseek(fp, 0, SEEK_SET) != 0) {
        fclose(fp);
        free_step_patch_blocks(script_blocks, script_block_count);
        fprintf(stderr, "failed to rewind %s\n", init_state_path);
        return 1;
      }
      size_t file_size = (size_t)file_size_long;
      if (!(file_size == storage || file_size == total)) {
        fclose(fp);
        free_step_patch_blocks(script_blocks, script_block_count);
        fprintf(stderr,
                "%s size %zu does not match storage_size %zu or total bytes %zu\n",
                init_state_path, file_size, storage, total);
        return 1;
      }
      unsigned char *buf = (unsigned char *)malloc(file_size ? file_size : 1);
      if (!buf) {
        fclose(fp);
        free_step_patch_blocks(script_blocks, script_block_count);
        fprintf(stderr, "malloc failed for init state\n");
        return 1;
      }
      if (file_size && fread(buf, 1, file_size, fp) != file_size) {
        free(buf);
        fclose(fp);
        free_step_patch_blocks(script_blocks, script_block_count);
        fprintf(stderr, "failed to read %s\n", init_state_path);
        return 1;
      }
      fclose(fp);
      if (file_size == total) {
        CUDA_CHECK(cuMemcpyHtoD(d_storage, buf, total));
      } else if (gpu_replicate_init_state && nstates > 1U) {
        CUdeviceptr d_init_state = 0;
        CUDA_CHECK(cuMemAlloc(&d_init_state, storage));
        CUDA_CHECK(cuMemcpyHtoD(d_init_state, buf, storage));
        if (launch_init_state_replication(init_replication_kfn, d_storage,
                                          d_init_state, storage, total) != 0) {
          CUDA_CHECK(cuMemFree(d_init_state));
          free(buf);
          free_step_patch_blocks(script_blocks, script_block_count);
          return 1;
        }
        CUDA_CHECK(cuCtxSynchronize());
        CUDA_CHECK(cuMemFree(d_init_state));
      } else {
        for (unsigned state = 0; state < nstates; state++) {
          CUDA_CHECK(cuMemcpyHtoD(d_storage + ((size_t)state * storage), buf, storage));
        }
      }
      free(buf);
      trace_stage("after_init_state_upload");
    }
  }

  if (timing_repeats > 1U &&
      (resident_steps || script_blocks || env_flag_enabled(ENV_INIT_STATE))) {
    trace_stage("before_timing_repeat_snapshot");
    CUDA_CHECK(cuMemAlloc(&d_initial_snapshot, total));
    CUDA_CHECK(cuMemcpyDtoD(d_initial_snapshot, d_storage, total));
    trace_stage("after_timing_repeat_snapshot");
  }

  if (resident_steps && script_blocks) {
    if (build_resident_patch_schedule(script_blocks, script_block_count,
                                      script_logical_step_count, total,
                                      &resident_patch_schedule) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
    resident_patch_script_block_count = script_block_count;
    if (state_local_patches_requested && replicate_state0_patches_requested) {
      fprintf(stderr, "%s and %s are mutually exclusive\n",
              ENV_STATE_LOCAL_PATCHES, ENV_REPLICATE_STATE0_PATCHES);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&resident_patch_schedule);
      return 1;
    }
    if (replicate_state0_patches_requested) {
      ResidentPatchSchedule single_state_patch_schedule = resident_patch_schedule;
      memset(&resident_patch_schedule, 0, sizeof(resident_patch_schedule));
      if (build_replicated_state0_resident_patch_schedule(
              &single_state_patch_schedule, nstates, storage, total,
              &resident_patch_schedule) != 0) {
        free_step_patch_blocks(script_blocks, script_block_count);
        free_resident_patch_schedule(&single_state_patch_schedule);
        return 1;
      }
      free_resident_patch_schedule(&single_state_patch_schedule);
    }
    if (state_local_patches_requested) {
      if (build_state_local_resident_patch_schedule(&resident_patch_schedule,
                                                    nstates, storage,
                                                    &state_local_patch_schedule) != 0) {
        free_step_patch_blocks(script_blocks, script_block_count);
        free_resident_patch_schedule(&resident_patch_schedule);
        return 1;
      }
    }
    if (upload_resident_patch_schedule(&resident_patch_schedule) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      return 1;
    }
    if (upload_resident_patch_schedule(&state_local_patch_schedule) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      return 1;
    }
    if (resident_patch_schedule.step_offsets &&
        resident_patch_schedule.logical_steps >= 2U) {
      unsigned diagnostic_low_start = resident_patch_schedule.step_offsets[0];
      unsigned diagnostic_low_count =
          resident_patch_schedule.step_offsets[1] - diagnostic_low_start;
      unsigned diagnostic_high_count =
          resident_patch_schedule.step_offsets[2] -
          resident_patch_schedule.step_offsets[1];
      CUdeviceptr diagnostic_pair_offsets =
          resident_patch_schedule.d_offsets +
          ((CUdeviceptr)diagnostic_low_start * (CUdeviceptr)sizeof(size_t));
      CUdeviceptr diagnostic_pair_values =
          resident_patch_schedule.d_values + (CUdeviceptr)diagnostic_low_start;
      maybe_print_ordering_aware_high_patch_offset_diagnostic(
          "post_schedule_upload",
          &resident_patch_schedule, u64_load_probe_kfn,
          u64_load_probe_module_idx, ordering_aware_token_loop_module_idx,
          diagnostic_pair_offsets, diagnostic_pair_values, d_storage,
          d_ordering_aware_token_loop_progress, storage, 0U,
          diagnostic_low_start, diagnostic_low_count, diagnostic_high_count,
          0U, nstates);
    }
    free_step_patch_blocks(script_blocks, script_block_count);
    script_blocks = NULL;
    script_block_count = 0U;
  }
  if (feedback_edges_requested) {
    if (upload_feedback_edge_table(&feedback_edges) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }
  if (feedback_increments_requested) {
    if (upload_feedback_increment_table(&feedback_increments) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }
  if (feedback_phase_sets_requested) {
    if (upload_feedback_set_table(&feedback_phase_sets) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_feedback_set_table(&feedback_phase_sets);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
	  }
	  if (ordering_aware_token_loop_abi.requested) {
    if (parse_ordering_aware_terminal_mask_records(
            ordering_aware_terminal_mask_specs, nstates,
            &ordering_aware_terminal_masks) != 0) {
      ordering_aware_terminal_mask_parse_error_count = 1U;
      free_step_patch_blocks(script_blocks, script_block_count);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_feedback_set_table(&feedback_phase_sets);
      free_ordering_aware_terminal_mask_table(&ordering_aware_terminal_masks);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    if (upload_ordering_aware_terminal_mask_table(
            &ordering_aware_terminal_masks) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_feedback_edge_table(&feedback_edges);
      free_feedback_increment_table(&feedback_increments);
      free_feedback_set_table(&feedback_phase_sets);
      free_ordering_aware_terminal_mask_table(&ordering_aware_terminal_masks);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    if (eval_partition_predicates_requested) {
      if (parse_eval_partition_predicate_records(
              eval_partition_predicate_specs, nstates,
              &eval_partition_predicates) != 0) {
        eval_partition_predicate_parse_error_count = 1U;
        free_step_patch_blocks(script_blocks, script_block_count);
        free_feedback_edge_table(&feedback_edges);
        free_feedback_increment_table(&feedback_increments);
        free_feedback_set_table(&feedback_phase_sets);
        free_ordering_aware_terminal_mask_table(&ordering_aware_terminal_masks);
        free_eval_partition_predicate_table(&eval_partition_predicates);
        free_resident_patch_schedule(&state_local_patch_schedule);
        free_resident_patch_schedule(&resident_patch_schedule);
        free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
        return 1;
      }
      if (upload_eval_partition_predicate_table(
              &eval_partition_predicates) != 0) {
        free_step_patch_blocks(script_blocks, script_block_count);
        free_feedback_edge_table(&feedback_edges);
        free_feedback_increment_table(&feedback_increments);
        free_feedback_set_table(&feedback_phase_sets);
        free_ordering_aware_terminal_mask_table(&ordering_aware_terminal_masks);
        free_eval_partition_predicate_table(&eval_partition_predicates);
        free_resident_patch_schedule(&state_local_patch_schedule);
        free_resident_patch_schedule(&resident_patch_schedule);
        free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
        return 1;
      }
    }
  }
  update_ordering_aware_token_loop_abi_probe(
      &ordering_aware_token_loop_abi,
      ordering_aware_token_loop_available,
      &resident_patch_schedule,
      &feedback_edges,
      &feedback_increments,
      &feedback_phase_sets,
      ordering_aware_terminal_masks.mask_count,
      (ordering_aware_terminal_masks.d_states &&
       ordering_aware_terminal_masks.d_terminal_steps)
          ? ordering_aware_terminal_masks.mask_count
          : 0U,
      ordering_aware_terminal_mask_parse_error_count,
      eval_partition_predicates_requested,
      eval_partition_predicate_active_mask_authority,
      eval_partition_predicates.record_count,
      (eval_partition_predicates.d_partition_ids &&
       eval_partition_predicates.d_phases &&
       eval_partition_predicates.d_states &&
       eval_partition_predicates.d_active)
          ? eval_partition_predicates.record_count
          : 0U,
      eval_partition_predicate_parse_error_count,
      eval_partition_predicates.active_bitmap_partition_count,
      eval_partition_predicates.active_bitmap_phase_count,
      eval_partition_predicates.d_active_bitmap
          ? eval_partition_predicates.active_bitmap_size
          : 0U,
      eval_partition_predicates_requested &&
          !eval_partition_guarded_skip_requested,
      eval_partition_predicates_requested &&
          !eval_partition_guarded_skip_requested &&
          eval_partition_predicates.d_partition_ids &&
          eval_partition_predicates.d_phases &&
          eval_partition_predicates.d_states &&
          eval_partition_predicates.d_active,
      eval_partition_guarded_skip_requested,
      eval_partition_guarded_skip_requested &&
          eval_partition_predicates.record_count > 0U &&
          eval_partition_predicates.d_partition_ids &&
          eval_partition_predicates.d_phases &&
          eval_partition_predicates.d_states &&
          eval_partition_predicates.d_active &&
          eval_partition_predicates.d_active_bitmap,
      cfg_clone_diagnostic_abi_enabled);
  const int ordering_aware_token_loop_launch_probe_available =
      ordering_aware_token_loop_abi.requested &&
      ordering_aware_token_loop_available &&
      ordering_aware_token_loop_abi.phase_control_record_count > 0U &&
      ordering_aware_token_loop_abi.feedback_copy_record_count > 0U &&
      ordering_aware_token_loop_abi.feedback_increment_record_count > 0U &&
      ordering_aware_token_loop_abi.pair_cycle_loop_record_count > 0U &&
      ordering_aware_token_loop_abi.terminal_mask_record_count == nstates &&
      ordering_aware_token_loop_abi.terminal_mask_device_record_count == nstates &&
      ordering_aware_token_loop_abi.terminal_mask_parse_error_count == 0U;

  int nstates_i = (int)nstates;
  void *params[] = {&d_storage, &nstates_i};
  unsigned grid = (nstates + block - 1) / block;

  CUevent ev_start, ev_stop;
  CUDA_CHECK(cuEventCreate(&ev_start, CU_EVENT_DEFAULT));
  CUDA_CHECK(cuEventCreate(&ev_stop, CU_EVENT_DEFAULT));
  float *timing_repeat_ms = (float *)calloc(timing_repeats, sizeof(*timing_repeat_ms));
  if (!timing_repeat_ms) {
    fprintf(stderr, "calloc failed for %u timing repeats\n", timing_repeats);
    free_step_patch_blocks(script_blocks, script_block_count);
    free_resident_patch_schedule(&resident_patch_schedule);
    return 1;
  }
  unsigned *timing_repeat_launches =
      (unsigned *)calloc(timing_repeats, sizeof(*timing_repeat_launches));
  if (!timing_repeat_launches) {
    fprintf(stderr, "calloc failed for %u timing repeat launch counters\n",
            timing_repeats);
    free(timing_repeat_ms);
    free_step_patch_blocks(script_blocks, script_block_count);
    free_resident_patch_schedule(&resident_patch_schedule);
    return 1;
  }

  struct timespec wall0, wall1;
  clock_gettime(CLOCK_MONOTONIC, &wall0);
  trace_stage("before_launch_loop");
  if (ordering_aware_token_loop_progress_requested) {
    if (start_ordering_aware_token_loop_progress_watchdog(
            &ordering_aware_token_loop_progress_watchdog,
            h_ordering_aware_token_loop_progress) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
  }

  float gpu_kernel_ms_sum = 0.f;
  unsigned trace_expected_steps =
      (!script_blocks && persistent_resident_requested &&
       persistent_resident_phase_count > 1U)
          ? steps * persistent_resident_phase_count
          : steps;
  if (timing_repeats > 1U && trace_expected_steps > UINT_MAX / timing_repeats) {
    fprintf(stderr, "step trace expected row count overflow\n");
    free_step_patch_blocks(script_blocks, script_block_count);
    free_resident_patch_schedule(&resident_patch_schedule);
    free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
    return 1;
  }
  if (open_step_trace(&step_trace, total,
                      trace_expected_steps * timing_repeats) != 0) {
    free_step_patch_blocks(script_blocks, script_block_count);
    free_resident_patch_schedule(&resident_patch_schedule);
    free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
    return 1;
  }
  const int sync_each_step = getenv(ENV_SYNC_EACH_STEP) != NULL ||
                             (step_trace.fp != NULL &&
                              !step_trace.device_buffered);

  for (unsigned timing_repeat = 0U; timing_repeat < timing_repeats;
       timing_repeat++) {
    gpu_kernel_ms_sum = 0.f;
    unsigned gpu_launches_this_repeat = 0U;
    if (timing_repeats > 1U && d_initial_snapshot) {
      CUDA_CHECK(cuMemcpyDtoD(d_storage, d_initial_snapshot, total));
    } else if (timing_repeats > 1U) {
      CUDA_CHECK(cuMemsetD8(d_storage, 0, total));
    }

    if (getenv(ENV_WARMUP) != NULL) {
      trace_stage("before_warmup");
      for (int k = 0; k < nk; k++) {
        trace_kernel_launch(kernel_names[k], 0U, k);
        CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0, params,
                                  NULL));
      }
      CUDA_CHECK(cuCtxSynchronize());
      trace_stage("after_warmup");
    }

    if (sync_each_step) {
      unsigned logical_step = 0U;
	      if (script_blocks) {
	        for (unsigned block_idx = 0; block_idx < script_block_count; block_idx++) {
	          StepPatchBlock *block_desc = &script_blocks[block_idx];
		          for (unsigned repeat_idx = 0; repeat_idx < block_desc->repeat_count; repeat_idx++) {
	            for (unsigned step_idx = 0; step_idx < block_desc->step_count; step_idx++, logical_step++) {
	              if (apply_patch_array(d_storage, total, patches, npatch) != 0) {
	                free_step_patch_blocks(script_blocks, script_block_count);
	                return 1;
              }
              if (apply_patch_array(d_storage, total, block_desc->steps[step_idx].items,
                                    block_desc->steps[step_idx].count) != 0) {
                free_step_patch_blocks(script_blocks, script_block_count);
                return 1;
              }
              CUDA_CHECK(cuEventRecord(ev_start, 0));
              if (logical_step == 0U)
                trace_stage("before_first_kernel_launch");
              for (int k = 0; k < nk; k++) {
                trace_kernel_launch(kernel_names[k], logical_step, k);
                CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                          params, NULL));
                gpu_launches_this_repeat++;
              }
              if (logical_step == 0U)
                trace_stage("after_first_kernel_launch");
              CUDA_CHECK(cuEventRecord(ev_stop, 0));
              if (logical_step == 0U)
                trace_stage("before_first_step_sync");
              CUDA_CHECK(cuCtxSynchronize());
              if (logical_step == 0U)
                trace_stage("after_first_step_sync");
              if (write_step_trace(&step_trace, d_storage, logical_step) != 0) {
                close_step_trace(&step_trace);
                free_step_patch_blocks(script_blocks, script_block_count);
                free_resident_patch_schedule(&resident_patch_schedule);
                return 1;
              }
              float step_ms = 0.f;
              CUDA_CHECK(cuEventElapsedTime(&step_ms, ev_start, ev_stop));
              gpu_kernel_ms_sum += step_ms;
            }
          }
        }
      } else {
        for (unsigned step = 0; step < steps; step++) {
          if (apply_patch_array(d_storage, total, patches, npatch) != 0) {
            free_step_patch_blocks(script_blocks, script_block_count);
            free_resident_patch_schedule(&resident_patch_schedule);
            return 1;
          }
          CUDA_CHECK(cuEventRecord(ev_start, 0));
          if (step == 0U)
            trace_stage("before_first_kernel_launch");
          if (resident_pair_cycle_requested &&
              step >= resident_pair_cycle_start &&
              ((step - resident_pair_cycle_start) % 2U) == 0U &&
              step + 1U < steps) {
            int pair_fused_launched = 0;
            int can_try_pair_cycle_loop =
                fused_pair_cycle_requested &&
                fused_pair_cycle_loop_requested &&
                (fused_pair_cycle_loop_available ||
                 ordering_aware_token_loop_launch_probe_available) &&
                !state_local_patches_requested && !step_trace.fp &&
                npatch == 0;
            int can_try_single_kernel_pair =
                fused_pair_cycle_requested &&
                (fused_pair_cycle_available ||
                 fused_pair_cycle_state_local_available) &&
                nk == 1 && npatch == 0;
            if (trace_stages_enabled()) {
              fprintf(stderr,
                      "run_vl_hybrid: pair_cycle_loop_elig step=%u requested=%d "
                      "pair_requested=%d available=%d state_local=%d trace=%d "
                      "npatch=%d nk=%d can_loop=%d can_single=%d\n",
                      step, fused_pair_cycle_loop_requested,
                      fused_pair_cycle_requested, fused_pair_cycle_loop_available,
                      state_local_patches_requested, step_trace.fp ? 1 : 0,
                      npatch, nk, can_try_pair_cycle_loop,
                      can_try_single_kernel_pair);
            }
            if (can_try_pair_cycle_loop) {
              unsigned loop_cycles = fused_pair_cycle_loop_count(
                  &resident_patch_schedule, step, nstates,
                  fused_pair_cycle_loop_chunk);
              if (ordering_aware_token_loop_launch_probe_available &&
                  ordering_aware_token_loop_cycle_limit > 0U &&
                  loop_cycles > ordering_aware_token_loop_cycle_limit) {
                loop_cycles = ordering_aware_token_loop_cycle_limit;
                ordering_aware_token_loop_cycle_limit_applied++;
              }
              if (trace_stages_enabled()) {
                fprintf(stderr,
                        "run_vl_hybrid: pair_cycle_loop_count step=%u cycles=%u\n",
                        step, loop_cycles);
              }
              if (loop_cycles > 1U) {
                if (ordering_aware_token_loop_launch_probe_available) {
                  int ordering_chunk_starts_phase = (step == 0U);
                  int ordering_chunk_applies_feedback = 1;
                  pair_fused_launched = launch_ordering_aware_token_loop_step(
                      ordering_aware_token_loop_kfn, u64_load_probe_kfn,
                      u64_load_probe_module_idx,
                      ordering_aware_token_loop_module_idx,
                      &resident_patch_schedule,
                      &feedback_phase_sets, &feedback_edges,
                      &feedback_increments, &ordering_aware_terminal_masks,
                      &eval_partition_predicates, d_storage, storage,
                      step, loop_cycles,
                      1U, ordering_chunk_starts_phase,
                      ordering_chunk_applies_feedback, nstates, grid, block,
	                      ordering_aware_token_loop_abi.eval_partition_guarded_skip_enabled,
	                      d_single_entry_cfg_clone_liveout_counters,
                          single_entry_cfg_clone_liveout_counter_count,
	                      d_cfg_clone_shadow_descriptor_records,
	                      d_cfg_clone_shadow_payload,
                          cfg_clone_shadow_payload_total_bytes,
	                      cfg_clone_diagnostic_abi_enabled
	                          ? CFG_CLONE_SHADOW_DESCRIPTOR_COUNT
	                          : 0U,
	                      d_ordering_aware_region_cycles,
                          d_ordering_aware_token_loop_progress_global,
                          ordering_aware_token_loop_progress_global_bytes,
                          h_ordering_aware_token_loop_progress);
                } else {
                  pair_fused_launched = launch_fused_pair_cycle_loop_step(
                      fused_pair_cycle_loop_kfn, &resident_patch_schedule,
                      d_storage, step, loop_cycles, nstates, grid, block,
                      "vl_patch_eval_pair_cycle_loop_batch_gpu");
                }
                if (pair_fused_launched < 0)
                  return 1;
                if (pair_fused_launched) {
                  if (ordering_aware_token_loop_launch_probe_available) {
                    ordering_aware_token_loop_abi.launch_probe_count++;
                    ordering_aware_token_loop_abi.device_table_launch_count++;
                  } else {
                    fused_pair_cycle_loop_kernel_launches++;
                    fused_pair_cycle_loop_cycles += loop_cycles;
                  }
                  gpu_launches_this_repeat++;
                  resident_pair_cycle_launches++;
                  if (step == 0U)
                    trace_stage("after_first_kernel_launch");
                  CUDA_CHECK(cuEventRecord(ev_stop, 0));
                  if (step == 0U)
                    trace_stage("before_first_step_sync");
                  CUDA_CHECK(cuCtxSynchronize());
                  if (step == 0U)
                    trace_stage("after_first_step_sync");
                  {
                    float step_ms = 0.0f;
                    CUDA_CHECK(cuEventElapsedTime(&step_ms, ev_start, ev_stop));
                    gpu_kernel_ms_sum += step_ms;
                  }
                  step += (loop_cycles * 2U) - 1U;
                  continue;
                }
              }
              fused_pair_cycle_loop_fallbacks++;
            } else if (fused_pair_cycle_loop_requested) {
              fused_pair_cycle_loop_fallbacks++;
            }
            if (can_try_single_kernel_pair) {
              if (state_local_patches_requested &&
                  fused_pair_cycle_state_local_available) {
                pair_fused_launched =
                    launch_fused_pair_cycle_state_local_step(
                        fused_pair_cycle_state_local_kfn,
                        &state_local_patch_schedule, d_storage, step, nstates,
                        grid, block);
                if (pair_fused_launched) {
                  fused_pair_cycle_state_local_launches++;
                } else {
                  fused_pair_cycle_state_local_fallbacks++;
                }
              }
              if (!pair_fused_launched) {
                pair_fused_launched = launch_fused_pair_cycle_step(
                    fused_pair_cycle_kfn, &resident_patch_schedule, d_storage,
                    step, nstates, grid, block);
              }
              if (pair_fused_launched) {
                fused_pair_cycle_launches++;
                gpu_launches_this_repeat++;
              }
            }
            if (!pair_fused_launched) {
              if (fused_pair_cycle_requested)
                fused_pair_cycle_fallbacks++;
              if (resident_patch_count_for_step(&resident_patch_schedule, step) > 0U)
                gpu_launches_this_repeat++;
              if (launch_resident_patch_step(resident_patch_kfn,
                                             &resident_patch_schedule,
                                             d_storage, step) != 0) {
                free_resident_patch_schedule(&resident_patch_schedule);
                return 1;
              }
              for (int k = 0; k < nk; k++) {
                trace_kernel_launch(kernel_names[k], step, k);
                CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                          params, NULL));
                gpu_launches_this_repeat++;
              }
              if (resident_patch_count_for_step(&resident_patch_schedule, step + 1U) > 0U)
                gpu_launches_this_repeat++;
              if (launch_resident_patch_step(resident_patch_kfn,
                                             &resident_patch_schedule,
                                             d_storage, step + 1U) != 0) {
                free_resident_patch_schedule(&resident_patch_schedule);
                return 1;
              }
              for (int k = 0; k < nk; k++) {
                trace_kernel_launch(kernel_names[k], step + 1U, k);
                CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                          params, NULL));
                gpu_launches_this_repeat++;
              }
            }
            resident_pair_cycle_launches++;
            if (step == 0U)
              trace_stage("after_first_kernel_launch");
            CUDA_CHECK(cuEventRecord(ev_stop, 0));
            if (step == 0U)
              trace_stage("before_first_step_sync");
            CUDA_CHECK(cuCtxSynchronize());
            if (step == 0U)
              trace_stage("after_first_step_sync");
            if (write_step_trace(&step_trace, d_storage, step + 1U) != 0) {
              close_step_trace(&step_trace);
              free_step_patch_blocks(script_blocks, script_block_count);
              free_resident_patch_schedule(&resident_patch_schedule);
              return 1;
            }
            {
              float step_ms = 0.f;
              CUDA_CHECK(cuEventElapsedTime(&step_ms, ev_start, ev_stop));
              gpu_kernel_ms_sum += step_ms;
            }
            step++;
            continue;
          } else if (resident_pair_cycle_requested &&
                     step >= resident_pair_cycle_start) {
            resident_pair_cycle_fallbacks++;
          }
          int fused_launched = 0;
          if (fused_patch_eval_requested && fused_patch_eval_available &&
              nk == 1 && npatch == 0 &&
              resident_patch_count_for_step(&resident_patch_schedule, step) > 0U) {
            fused_launched = launch_fused_patch_eval_step(
                fused_patch_eval_kfn, &resident_patch_schedule, d_storage, step,
                nstates, grid, block);
            if (fused_launched) {
              fused_patch_eval_launches++;
              gpu_launches_this_repeat++;
            } else {
              fused_patch_eval_fallbacks++;
            }
          }
          if (!fused_launched) {
            if (resident_patch_count_for_step(&resident_patch_schedule, step) > 0U)
              gpu_launches_this_repeat++;
            if (launch_resident_patch_step(resident_patch_kfn,
                                           &resident_patch_schedule,
                                           d_storage, step) != 0) {
              free_resident_patch_schedule(&resident_patch_schedule);
              return 1;
            }
            for (int k = 0; k < nk; k++) {
              trace_kernel_launch(kernel_names[k], step, k);
              CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                        params, NULL));
              gpu_launches_this_repeat++;
            }
            if (feedback_edges_requested && !feedback_edge_mode_phase) {
              int feedback_launched =
                  launch_feedback_edges(feedback_edge_kfn, &feedback_edges,
                                        d_storage, storage, nstates, step);
              if (feedback_launched < 0) {
                free_feedback_edge_table(&feedback_edges);
                free_feedback_increment_table(&feedback_increments);
                free_resident_patch_schedule(&resident_patch_schedule);
                return 1;
              }
              if (feedback_launched) {
                feedback_edge_launches++;
                gpu_launches_this_repeat++;
              }
            }
            if (feedback_increments_requested && !feedback_edge_mode_phase) {
              int increment_launched =
                  launch_feedback_increments(feedback_increment_kfn,
                                             &feedback_increments, d_storage,
                                             storage, nstates, step);
              if (increment_launched < 0) {
                free_feedback_edge_table(&feedback_edges);
                free_feedback_increment_table(&feedback_increments);
                free_resident_patch_schedule(&resident_patch_schedule);
                return 1;
              }
              if (increment_launched) {
                feedback_increment_launches++;
                gpu_launches_this_repeat++;
              }
            }
          }
          if (step == 0U)
            trace_stage("after_first_kernel_launch");
          CUDA_CHECK(cuEventRecord(ev_stop, 0));
          if (step == 0U)
            trace_stage("before_first_step_sync");
          CUDA_CHECK(cuCtxSynchronize());
          if (step == 0U)
            trace_stage("after_first_step_sync");
          if (write_step_trace(&step_trace, d_storage, step) != 0) {
            close_step_trace(&step_trace);
            free_step_patch_blocks(script_blocks, script_block_count);
            free_resident_patch_schedule(&resident_patch_schedule);
            return 1;
          }
          {
            float step_ms = 0.f;
            CUDA_CHECK(cuEventElapsedTime(&step_ms, ev_start, ev_stop));
            gpu_kernel_ms_sum += step_ms;
          }
        }
      }
    } else {
	      /* One sync after all work: much lower wall latency when steps > 1. */
	      int recorded_start = 0;
	      unsigned logical_step = 0U;
	      if (script_blocks) {
	        for (unsigned block_idx = 0; block_idx < script_block_count; block_idx++) {
	          StepPatchBlock *block_desc = &script_blocks[block_idx];
	          for (unsigned repeat_idx = 0; repeat_idx < block_desc->repeat_count; repeat_idx++) {
	            if (resident_pair_cycle_requested && block_desc->step_count == 2U &&
	                logical_step >= resident_pair_cycle_start &&
	                ((logical_step - resident_pair_cycle_start) % 2U) == 0U &&
	                repeat_idx + 1U < block_desc->repeat_count) {
	              int pair_fused_launched = 0;
	              if (fused_pair_cycle_requested &&
	                  (fused_pair_cycle_available ||
	                   fused_pair_cycle_loop_available ||
	                   ordering_aware_token_loop_launch_probe_available ||
	                   fused_pair_cycle_state_local_available) &&
	                  nk == 1 && npatch == 0) {
	                if (fused_pair_cycle_loop_requested &&
	                    (fused_pair_cycle_loop_available ||
	                     ordering_aware_token_loop_launch_probe_available) &&
	                    !state_local_patches_requested && !step_trace.fp) {
	                  unsigned loop_cycles = fused_pair_cycle_loop_count(
	                      &resident_patch_schedule, logical_step, nstates,
	                      fused_pair_cycle_loop_chunk);
	                  unsigned remaining_cycles = block_desc->repeat_count - repeat_idx;
	                  if (loop_cycles > remaining_cycles)
	                    loop_cycles = remaining_cycles;
                  if (ordering_aware_token_loop_launch_probe_available &&
                      ordering_aware_token_loop_cycle_limit > 0U &&
                      loop_cycles > ordering_aware_token_loop_cycle_limit) {
                    loop_cycles = ordering_aware_token_loop_cycle_limit;
                    ordering_aware_token_loop_cycle_limit_applied++;
                  }
	                  if (loop_cycles > 1U) {
	                    if (!recorded_start) {
	                      CUDA_CHECK(cuEventRecord(ev_start, 0));
	                      recorded_start = 1;
	                    }
	                    if (logical_step == 0U)
	                      trace_stage("before_first_kernel_launch");
	                    if (ordering_aware_token_loop_launch_probe_available) {
                      int ordering_chunk_starts_phase = (logical_step == 0U);
                      int ordering_chunk_applies_feedback = 1;
	                      pair_fused_launched =
	                          launch_ordering_aware_token_loop_step(
                              ordering_aware_token_loop_kfn,
                              u64_load_probe_kfn,
                              u64_load_probe_module_idx,
                              ordering_aware_token_loop_module_idx,
                              &resident_patch_schedule, &feedback_phase_sets,
                              &feedback_edges, &feedback_increments,
                              &ordering_aware_terminal_masks,
                              &eval_partition_predicates, d_storage, storage,
                              logical_step, loop_cycles, 1U,
                              ordering_chunk_starts_phase,
                              ordering_chunk_applies_feedback, nstates, grid,
                              block,
	                              ordering_aware_token_loop_abi.eval_partition_guarded_skip_enabled,
	                              d_single_entry_cfg_clone_liveout_counters,
                                  single_entry_cfg_clone_liveout_counter_count,
	                              d_cfg_clone_shadow_descriptor_records,
	                              d_cfg_clone_shadow_payload,
                                  cfg_clone_shadow_payload_total_bytes,
	                              cfg_clone_diagnostic_abi_enabled
	                                  ? CFG_CLONE_SHADOW_DESCRIPTOR_COUNT
	                                  : 0U,
	                              d_ordering_aware_region_cycles,
                                  d_ordering_aware_token_loop_progress_global,
                                  ordering_aware_token_loop_progress_global_bytes,
                              h_ordering_aware_token_loop_progress);
	                    } else {
	                      pair_fused_launched =
	                          launch_fused_pair_cycle_loop_step(
	                              fused_pair_cycle_loop_kfn,
	                              &resident_patch_schedule, d_storage,
	                              logical_step, loop_cycles, nstates, grid,
		                              block,
		                              "vl_patch_eval_pair_cycle_loop_batch_gpu");
		                    }
                    if (pair_fused_launched < 0)
                      return 1;
			                    if (pair_fused_launched) {
	                      if (ordering_aware_token_loop_launch_probe_available) {
	                        ordering_aware_token_loop_abi.launch_probe_count++;
	                        ordering_aware_token_loop_abi.device_table_launch_count++;
	                      } else {
	                        fused_pair_cycle_loop_kernel_launches++;
	                        fused_pair_cycle_loop_cycles += loop_cycles;
	                        resident_pair_cycle_launches++;
	                      }
	                      gpu_launches_this_repeat++;
	                      if (logical_step == 0U)
	                        trace_stage("after_first_kernel_launch");
	                      repeat_idx += loop_cycles - 1U;
	                      logical_step += loop_cycles * 2U;
	                      continue;
	                    }
	                  }
	                  fused_pair_cycle_loop_fallbacks++;
	                } else if (fused_pair_cycle_loop_requested) {
	                  fused_pair_cycle_loop_fallbacks++;
	                }
	              } else if (fused_pair_cycle_loop_requested) {
	                fused_pair_cycle_loop_fallbacks++;
	              }
	            }
	            for (unsigned step_idx = 0; step_idx < block_desc->step_count; step_idx++, logical_step++) {
              if (apply_patch_array(d_storage, total, patches, npatch) != 0) {
                free_step_patch_blocks(script_blocks, script_block_count);
                return 1;
              }
              if (apply_patch_array(d_storage, total, block_desc->steps[step_idx].items,
                                    block_desc->steps[step_idx].count) != 0) {
                free_step_patch_blocks(script_blocks, script_block_count);
                return 1;
              }
              if (!recorded_start) {
                CUDA_CHECK(cuEventRecord(ev_start, 0));
                recorded_start = 1;
              }
              if (logical_step == 0U)
                trace_stage("before_first_kernel_launch");
              for (int k = 0; k < nk; k++) {
                trace_kernel_launch(kernel_names[k], logical_step, k);
                CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                          params, NULL));
                gpu_launches_this_repeat++;
              }
              if (logical_step == 0U)
                trace_stage("after_first_kernel_launch");
              if (step_trace.fp &&
                  write_step_trace(&step_trace, d_storage, logical_step) != 0) {
                close_step_trace(&step_trace);
                free_step_patch_blocks(script_blocks, script_block_count);
                free_resident_patch_schedule(&resident_patch_schedule);
                return 1;
              }
            }
          }
        }
      } else {
        unsigned total_phases =
            (persistent_resident_requested && persistent_resident_phase_count > 1U)
                ? persistent_resident_phase_count
                : 1U;
        unsigned logical_step_index = 0U;
        for (unsigned phase_idx = 0U; phase_idx < total_phases; phase_idx++) {
          for (unsigned step = 0; step < steps; step++, logical_step_index++) {
            unsigned schedule_step_index = (total_phases > 1U) ? step : logical_step_index;
            if (apply_patch_array(d_storage, total, patches, npatch) != 0) {
              free_step_patch_blocks(script_blocks, script_block_count);
              free_resident_patch_schedule(&resident_patch_schedule);
              return 1;
            }
            if (!recorded_start) {
              CUDA_CHECK(cuEventRecord(ev_start, 0));
              recorded_start = 1;
            }
            if (logical_step_index == 0U)
              trace_stage("before_first_kernel_launch");
            if (feedback_phase_sets_requested && step == 0U &&
                !ordering_aware_token_loop_launch_probe_available) {
              int set_launched =
                  launch_feedback_sets(feedback_set_kfn, &feedback_phase_sets,
                                       d_storage, storage, nstates,
                                       phase_idx + 1U, logical_step_index);
              if (set_launched < 0) {
                free_feedback_edge_table(&feedback_edges);
                free_feedback_increment_table(&feedback_increments);
                free_feedback_set_table(&feedback_phase_sets);
                free_resident_patch_schedule(&resident_patch_schedule);
                free_string_list(persistent_phase_dumps,
                                 persistent_phase_dump_count);
                return 1;
              }
              if (set_launched) {
                feedback_phase_set_launches++;
                gpu_launches_this_repeat++;
              }
            }
	            if (resident_pair_cycle_requested &&
	                logical_step_index >= resident_pair_cycle_start &&
	                ((logical_step_index - resident_pair_cycle_start) % 2U) == 0U &&
	                step + 1U < steps) {
	              int pair_fused_launched = 0;
	              int can_try_pair_cycle_loop =
	                  fused_pair_cycle_requested &&
	                  fused_pair_cycle_loop_requested &&
	                  (fused_pair_cycle_loop_available ||
	                   ordering_aware_token_loop_launch_probe_available) &&
	                  !state_local_patches_requested && !step_trace.fp &&
	                  npatch == 0;
	              int can_try_single_kernel_pair =
	                  fused_pair_cycle_requested &&
	                  (fused_pair_cycle_available ||
	                   fused_pair_cycle_state_local_available) &&
	                  nk == 1 && npatch == 0;
	              if (trace_stages_enabled()) {
	                fprintf(stderr,
	                        "run_vl_hybrid: pair_cycle_loop_elig step=%u requested=%d "
	                        "pair_requested=%d available=%d state_local=%d trace=%d "
	                        "npatch=%d nk=%d can_loop=%d can_single=%d\n",
	                        logical_step_index, fused_pair_cycle_loop_requested,
	                        fused_pair_cycle_requested, fused_pair_cycle_loop_available,
	                        state_local_patches_requested, step_trace.fp ? 1 : 0,
	                        npatch, nk, can_try_pair_cycle_loop,
	                        can_try_single_kernel_pair);
	              }
		              if (can_try_pair_cycle_loop) {
		                  unsigned loop_cycles = fused_pair_cycle_loop_count(
		                      &resident_patch_schedule, schedule_step_index, nstates,
		                      fused_pair_cycle_loop_chunk);
                  if (ordering_aware_token_loop_launch_probe_available &&
                      ordering_aware_token_loop_cycle_limit > 0U &&
                      loop_cycles > ordering_aware_token_loop_cycle_limit) {
                    loop_cycles = ordering_aware_token_loop_cycle_limit;
                    ordering_aware_token_loop_cycle_limit_applied++;
                  }
		                if (trace_stages_enabled()) {
		                  fprintf(stderr,
		                          "run_vl_hybrid: pair_cycle_loop_count step=%u cycles=%u\n",
	                          logical_step_index, loop_cycles);
	                }
	                if (loop_cycles > 1U) {
	                  if (ordering_aware_token_loop_launch_probe_available) {
                    int ordering_chunk_starts_phase = (step == 0U);
                    int ordering_chunk_applies_feedback = 1;
		                    pair_fused_launched =
		                        launch_ordering_aware_token_loop_step(
                            ordering_aware_token_loop_kfn,
                            u64_load_probe_kfn,
                            u64_load_probe_module_idx,
                            ordering_aware_token_loop_module_idx,
                            &resident_patch_schedule, &feedback_phase_sets,
                            &feedback_edges, &feedback_increments,
                            &ordering_aware_terminal_masks,
                            &eval_partition_predicates, d_storage, storage,
                            schedule_step_index, loop_cycles, phase_idx + 1U,
                            ordering_chunk_starts_phase,
                            ordering_chunk_applies_feedback, nstates, grid, block,
	                            ordering_aware_token_loop_abi.eval_partition_guarded_skip_enabled,
	                            d_single_entry_cfg_clone_liveout_counters,
                                single_entry_cfg_clone_liveout_counter_count,
	                            d_cfg_clone_shadow_descriptor_records,
	                            d_cfg_clone_shadow_payload,
                                cfg_clone_shadow_payload_total_bytes,
	                            cfg_clone_diagnostic_abi_enabled
	                                ? CFG_CLONE_SHADOW_DESCRIPTOR_COUNT
	                                : 0U,
	                            d_ordering_aware_region_cycles,
                                d_ordering_aware_token_loop_progress_global,
                                ordering_aware_token_loop_progress_global_bytes,
                            h_ordering_aware_token_loop_progress);
	                  } else {
	                    pair_fused_launched = launch_fused_pair_cycle_loop_step(
	                        fused_pair_cycle_loop_kfn,
	                        &resident_patch_schedule, d_storage,
	                        schedule_step_index, loop_cycles, nstates, grid,
		                        block, "vl_patch_eval_pair_cycle_loop_batch_gpu");
		                  }
                  if (pair_fused_launched < 0)
                    return 1;
			                  if (pair_fused_launched) {
		                    if (ordering_aware_token_loop_launch_probe_available) {
		                      ordering_aware_token_loop_abi.launch_probe_count++;
		                      ordering_aware_token_loop_abi.device_table_launch_count++;
		                    } else {
		                      fused_pair_cycle_loop_kernel_launches++;
		                      fused_pair_cycle_loop_cycles += loop_cycles;
		                      resident_pair_cycle_launches++;
		                    }
		                    gpu_launches_this_repeat++;
	                    if (logical_step_index == 0U)
	                      trace_stage("after_first_kernel_launch");
	                    step += (loop_cycles * 2U) - 1U;
	                    logical_step_index += (loop_cycles * 2U) - 1U;
	                    continue;
	                  }
	                }
	                fused_pair_cycle_loop_fallbacks++;
	              } else if (fused_pair_cycle_loop_requested) {
	                fused_pair_cycle_loop_fallbacks++;
	              }
	              if (can_try_single_kernel_pair) {
	                if (state_local_patches_requested &&
	                    fused_pair_cycle_state_local_available) {
	                  pair_fused_launched =
	                      launch_fused_pair_cycle_state_local_step(
	                          fused_pair_cycle_state_local_kfn,
	                          &state_local_patch_schedule, d_storage,
	                          schedule_step_index, nstates, grid, block);
	                  if (pair_fused_launched) {
	                    fused_pair_cycle_state_local_launches++;
	                  } else {
	                    fused_pair_cycle_state_local_fallbacks++;
	                  }
	                }
	                if (!pair_fused_launched) {
	                  pair_fused_launched = launch_fused_pair_cycle_step(
	                      fused_pair_cycle_kfn, &resident_patch_schedule,
	                      d_storage, schedule_step_index, nstates, grid, block);
	                }
	                if (pair_fused_launched) {
	                  fused_pair_cycle_launches++;
	                  gpu_launches_this_repeat++;
	                }
	              }
	              if (!pair_fused_launched) {
	                if (fused_pair_cycle_requested)
	                  fused_pair_cycle_fallbacks++;
	                if (resident_patch_count_for_step(&resident_patch_schedule,
	                                                  schedule_step_index) > 0U)
	                  gpu_launches_this_repeat++;
	                if (launch_resident_patch_step(resident_patch_kfn,
	                                               &resident_patch_schedule,
	                                               d_storage,
	                                               schedule_step_index) != 0) {
	                  free_resident_patch_schedule(&resident_patch_schedule);
	                  return 1;
	                }
	                for (int k = 0; k < nk; k++) {
	                  trace_kernel_launch(kernel_names[k], logical_step_index, k);
	                  CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
	                                            params, NULL));
	                  gpu_launches_this_repeat++;
	                }
	                if (resident_patch_count_for_step(&resident_patch_schedule,
	                                                  schedule_step_index + 1U) > 0U)
	                  gpu_launches_this_repeat++;
	                if (launch_resident_patch_step(resident_patch_kfn,
	                                               &resident_patch_schedule,
	                                               d_storage,
	                                               schedule_step_index + 1U) != 0) {
	                  free_resident_patch_schedule(&resident_patch_schedule);
	                  return 1;
	                }
	                for (int k = 0; k < nk; k++) {
	                  trace_kernel_launch(kernel_names[k], logical_step_index + 1U, k);
	                  CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
	                                            params, NULL));
	                  gpu_launches_this_repeat++;
	                }
	              }
	              resident_pair_cycle_launches++;
	              if (logical_step_index == 0U)
	                trace_stage("after_first_kernel_launch");
	              if (step_trace.fp &&
	                  write_step_trace(&step_trace, d_storage,
	                                   logical_step_index + 1U) != 0) {
	                close_step_trace(&step_trace);
	                free_step_patch_blocks(script_blocks, script_block_count);
	                free_resident_patch_schedule(&resident_patch_schedule);
	                return 1;
	              }
	              step++;
	              logical_step_index++;
	              continue;
	            } else if (resident_pair_cycle_requested &&
	                       logical_step_index >= resident_pair_cycle_start) {
	              resident_pair_cycle_fallbacks++;
	            }
            int fused_launched = 0;
            if (fused_patch_eval_requested && fused_patch_eval_available &&
                nk == 1 && npatch == 0 &&
                resident_patch_count_for_step(&resident_patch_schedule,
                                              schedule_step_index) > 0U) {
              fused_launched = launch_fused_patch_eval_step(
                  fused_patch_eval_kfn, &resident_patch_schedule,
                  d_storage, schedule_step_index, nstates, grid, block);
              if (fused_launched) {
                fused_patch_eval_launches++;
                gpu_launches_this_repeat++;
              } else {
                fused_patch_eval_fallbacks++;
              }
            }
            if (!fused_launched) {
              if (resident_patch_count_for_step(&resident_patch_schedule,
                                                schedule_step_index) > 0U)
                gpu_launches_this_repeat++;
              if (launch_resident_patch_step(resident_patch_kfn,
                                             &resident_patch_schedule, d_storage,
                                             schedule_step_index) != 0) {
                free_resident_patch_schedule(&resident_patch_schedule);
                return 1;
              }
              for (int k = 0; k < nk; k++) {
                trace_kernel_launch(kernel_names[k], logical_step_index, k);
                CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                          params, NULL));
                gpu_launches_this_repeat++;
              }
              if (feedback_edges_requested && !feedback_edge_mode_phase) {
                int feedback_launched =
                    launch_feedback_edges(feedback_edge_kfn, &feedback_edges,
                                          d_storage, storage, nstates,
                                          logical_step_index);
                if (feedback_launched < 0) {
                  free_feedback_edge_table(&feedback_edges);
                  free_feedback_increment_table(&feedback_increments);
                  free_resident_patch_schedule(&resident_patch_schedule);
                  return 1;
                }
                if (feedback_launched) {
                  feedback_edge_launches++;
                  gpu_launches_this_repeat++;
                }
              }
              if (feedback_increments_requested && !feedback_edge_mode_phase) {
                int increment_launched =
                    launch_feedback_increments(feedback_increment_kfn,
                                               &feedback_increments, d_storage,
                                               storage, nstates,
                                               logical_step_index);
                if (increment_launched < 0) {
                  free_feedback_edge_table(&feedback_edges);
                  free_feedback_increment_table(&feedback_increments);
                  free_resident_patch_schedule(&resident_patch_schedule);
                  return 1;
                }
                if (increment_launched) {
                  feedback_increment_launches++;
                  gpu_launches_this_repeat++;
                }
              }
            }
            if (logical_step_index == 0U)
              trace_stage("after_first_kernel_launch");
            if (step_trace.fp &&
                write_step_trace(&step_trace, d_storage, logical_step_index) !=
                    0) {
              close_step_trace(&step_trace);
              free_step_patch_blocks(script_blocks, script_block_count);
              free_resident_patch_schedule(&resident_patch_schedule);
              return 1;
            }
          }
          if (total_phases > 1U) {
            if (!ordering_aware_token_loop_launch_probe_available &&
                feedback_combined_available && phase_idx + 1U < total_phases) {
              int combined_launched = launch_feedback_combined(
                  feedback_combined_kfn, &feedback_edges, &feedback_increments,
                  &feedback_phase_sets, d_storage, storage, nstates,
                  phase_idx + 2U, logical_step_index);
              if (combined_launched < 0) {
                free_feedback_edge_table(&feedback_edges);
                free_feedback_increment_table(&feedback_increments);
                free_feedback_set_table(&feedback_phase_sets);
                free_resident_patch_schedule(&resident_patch_schedule);
                free_string_list(persistent_phase_dumps,
                                 persistent_phase_dump_count);
                return 1;
              }
              if (combined_launched) {
                feedback_combined_launches++;
                gpu_launches_this_repeat++;
              }
            } else if (!ordering_aware_token_loop_launch_probe_available &&
                feedback_edges_requested && feedback_edge_mode_phase &&
                phase_idx + 1U < total_phases) {
              int feedback_launched =
                  launch_feedback_edges(feedback_edge_kfn, &feedback_edges,
                                        d_storage, storage, nstates,
                                        logical_step_index);
              if (feedback_launched < 0) {
                free_feedback_edge_table(&feedback_edges);
                free_feedback_increment_table(&feedback_increments);
                free_resident_patch_schedule(&resident_patch_schedule);
                free_string_list(persistent_phase_dumps,
                                 persistent_phase_dump_count);
                return 1;
              }
              if (feedback_launched) {
                feedback_edge_launches++;
                gpu_launches_this_repeat++;
              }
            }
            if (!ordering_aware_token_loop_launch_probe_available &&
                !feedback_combined_available &&
                feedback_increments_requested && feedback_edge_mode_phase &&
                phase_idx + 1U < total_phases) {
              int increment_launched =
                  launch_feedback_increments(feedback_increment_kfn,
                                             &feedback_increments, d_storage,
                                             storage, nstates,
                                             logical_step_index);
              if (increment_launched < 0) {
                free_feedback_edge_table(&feedback_edges);
                free_feedback_increment_table(&feedback_increments);
                free_resident_patch_schedule(&resident_patch_schedule);
                free_string_list(persistent_phase_dumps,
                                 persistent_phase_dump_count);
                return 1;
              }
              if (increment_launched) {
                feedback_increment_launches++;
                gpu_launches_this_repeat++;
              }
            }
            CUDA_CHECK(cuCtxSynchronize());
            if (persistent_phase_dump_count > phase_idx &&
                persistent_phase_dumps[phase_idx] != NULL) {
              if (dump_device_storage(d_storage, total,
                                      persistent_phase_dumps[phase_idx]) != 0) {
                free_resident_patch_schedule(&resident_patch_schedule);
                free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
                return 1;
              }
              printf("persistent_phase_state_dump: phase=%u path=%s (%zu bytes)\n",
                     phase_idx + 1U, persistent_phase_dumps[phase_idx], total);
            }
          }
        }
      }
      CUDA_CHECK(cuEventRecord(ev_stop, 0));
      trace_stage("before_final_sync");
      CUDA_CHECK(cuCtxSynchronize());
      trace_stage("after_final_sync");
      CUDA_CHECK(cuEventElapsedTime(&gpu_kernel_ms_sum, ev_start, ev_stop));
    }

    timing_repeat_ms[timing_repeat] = gpu_kernel_ms_sum;
    timing_repeat_launches[timing_repeat] = gpu_launches_this_repeat;
  }
  if (flush_step_trace(&step_trace) != 0) {
    close_step_trace(&step_trace);
    free(timing_repeat_ms);
    free(timing_repeat_launches);
    free_resident_patch_schedule(&state_local_patch_schedule);
    free_resident_patch_schedule(&resident_patch_schedule);
    free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
    free_step_patch_blocks(script_blocks, script_block_count);
    return 1;
  }
  gpu_kernel_ms_sum = median_float_copy(timing_repeat_ms, timing_repeats);

  clock_gettime(CLOCK_MONOTONIC, &wall1);
  double wall_ms =
      (wall1.tv_sec - wall0.tv_sec) * 1000.0 +
      (wall1.tv_nsec - wall0.tv_nsec) / 1e6;

  CUDA_CHECK(cuEventDestroy(ev_start));
  CUDA_CHECK(cuEventDestroy(ev_stop));

  unsigned timing_launch_count =
      (persistent_resident_requested && persistent_resident_phase_count > 1U)
          ? steps * persistent_resident_phase_count
          : steps;
  double ms_per_launch =
      timing_launch_count > 0 ? (double)gpu_kernel_ms_sum / (double)timing_launch_count : 0.0;
  unsigned actual_timed_launch_count = timing_repeat_launches[0];
  for (unsigned i = 1U; i < timing_repeats; i++) {
    if (timing_repeat_launches[i] > actual_timed_launch_count)
      actual_timed_launch_count = timing_repeat_launches[i];
  }
  double ms_per_actual_launch =
      actual_timed_launch_count > 0
          ? (double)gpu_kernel_ms_sum / (double)actual_timed_launch_count
          : 0.0;
  double us_per_state =
      (nstates > 0) ? (ms_per_launch / (double)nstates) * 1000.0 : 0.0;
  float timing_repeat_min_ms = timing_repeat_ms[0];
  float timing_repeat_max_ms = timing_repeat_ms[0];
  for (unsigned i = 1U; i < timing_repeats; i++) {
    if (timing_repeat_ms[i] < timing_repeat_min_ms)
      timing_repeat_min_ms = timing_repeat_ms[i];
    if (timing_repeat_ms[i] > timing_repeat_max_ms)
      timing_repeat_max_ms = timing_repeat_ms[i];
  }

  printf("ok: steps=%u kernels_per_step=%d patches_per_step=%d grid=%u block=%u "
         "nstates=%u storage=%zu B\n",
         steps, nk, npatch, grid, block, nstates, storage);
  printf("resident_mode: %s\n", resident_steps ? "true" : "false");
  if (persistent_resident_requested) {
    printf("persistent_resident_state_abi: handle=%s phase=%u status=probe_surface_phase1_only\n",
           persistent_resident_handle, persistent_resident_phase);
    if (persistent_resident_phase_count > 1U) {
      printf("persistent_resident_state_abi_phases: count=%u steps_per_phase=%u authority=device_d_storage\n",
             persistent_resident_phase_count, steps);
    }
  }
  printf("gpu_init_state_replication: %s\n",
         gpu_replicate_init_state ? "true" : "false");
  if (script_blocks) {
    printf("patch_script_steps: logical=%u records=%u blocks=%u\n",
           script_logical_step_count, script_record_count, script_block_count);
  } else if (resident_patch_schedule.step_offsets) {
    printf("resident_patch_schedule: logical=%u records=%u blocks=%u\n",
           resident_patch_schedule.logical_steps,
           resident_patch_schedule.record_count, resident_patch_script_block_count);
  }
  if (replicate_state0_patches_requested && resident_patch_schedule.step_offsets) {
    printf("replicated_state0_patch_schedule: requested=true logical=%u records=%u nstates=%u mode=state0_to_all_states\n",
           resident_patch_schedule.logical_steps,
           resident_patch_schedule.record_count, nstates);
  }
  if (state_local_patch_schedule.step_offsets) {
    printf("state_local_patch_schedule: logical=%u records=%u blocks=%u\n",
           state_local_patch_schedule.logical_steps,
           state_local_patch_schedule.record_count,
           resident_patch_script_block_count);
  }
  if (fused_patch_eval_requested || fused_patch_eval_launches > 0U) {
    printf("patch_eval_fusion: requested=%s available=%s launched=%u fallback=%u mode=state_grouped_patch_eval\n",
           fused_patch_eval_requested ? "true" : "false",
           fused_patch_eval_available ? "true" : "false",
           fused_patch_eval_launches, fused_patch_eval_fallbacks);
  }
  if (fused_pair_cycle_requested || fused_pair_cycle_launches > 0U) {
    printf("pair_cycle_fusion: requested=%s available=%s launched=%u fallback=%u mode=low_eval_high_eval\n",
           fused_pair_cycle_requested ? "true" : "false",
           fused_pair_cycle_available ? "true" : "false",
           fused_pair_cycle_launches, fused_pair_cycle_fallbacks);
  }
  if (fused_pair_cycle_loop_requested ||
      fused_pair_cycle_loop_kernel_launches > 0U) {
    printf("pair_cycle_loop_fusion: requested=%s available=%s kernel_launches=%u cycles=%u fallback=%u chunk=%u mode=looped_low_eval_high_eval\n",
           fused_pair_cycle_loop_requested ? "true" : "false",
           fused_pair_cycle_loop_available ? "true" : "false",
           fused_pair_cycle_loop_kernel_launches, fused_pair_cycle_loop_cycles,
           fused_pair_cycle_loop_fallbacks, fused_pair_cycle_loop_chunk);
  }
  if (state_local_patches_requested ||
      fused_pair_cycle_state_local_launches > 0U) {
    printf("pair_cycle_state_local_fusion: requested=%s available=%s launched=%u fallback=%u mode=state_local_low_eval_high_eval\n",
           state_local_patches_requested ? "true" : "false",
           fused_pair_cycle_state_local_available ? "true" : "false",
           fused_pair_cycle_state_local_launches,
           fused_pair_cycle_state_local_fallbacks);
  }
  if (resident_pair_cycle_requested || resident_pair_cycle_launches > 0U) {
    printf("resident_pair_cycle: requested=%s launched=%u fallback=%u start=%u mode=low_eval_high_eval\n",
           resident_pair_cycle_requested ? "true" : "false",
           resident_pair_cycle_launches, resident_pair_cycle_fallbacks,
           resident_pair_cycle_start);
  }
  if (feedback_edges_requested || feedback_edge_launches > 0U) {
    printf("feedback_edges: requested=%s mode=%s edges=%u launched=%u kernel=vl_apply_feedback_edges_gpu\n",
           feedback_edges_requested ? "true" : "false",
           feedback_edge_mode_phase ? "phase" : "step",
           feedback_edges.edge_count, feedback_edge_launches);
  }
  if (feedback_increments_requested || feedback_increment_launches > 0U) {
    printf("feedback_increments: requested=%s mode=%s increments=%u launched=%u kernel=vl_apply_feedback_increments_gpu\n",
           feedback_increments_requested ? "true" : "false",
           feedback_edge_mode_phase ? "phase" : "step",
           feedback_increments.increment_count, feedback_increment_launches);
  }
  if (feedback_phase_sets_requested || feedback_phase_set_launches > 0U) {
    printf("feedback_phase_sets: requested=%s sets=%u launched=%u kernel=vl_apply_feedback_sets_gpu\n",
           feedback_phase_sets_requested ? "true" : "false",
           feedback_phase_sets.set_count, feedback_phase_set_launches);
  }
  if (feedback_combined_available || feedback_combined_launches > 0U) {
    printf("feedback_combined: requested=%s launched=%u kernel=vl_apply_feedback_combined_gpu\n",
           feedback_combined_available ? "true" : "false",
           feedback_combined_launches);
  }
  if (ordering_aware_token_loop_abi.requested) {
    if (ordering_aware_token_loop_abi.device_table_launch_count > 0U &&
        feedback_phase_set_launches == 0U &&
        feedback_combined_launches == 0U &&
        fused_pair_cycle_loop_kernel_launches == 0U) {
      ordering_aware_token_loop_abi.runtime_supported = 1;
      ordering_aware_token_loop_abi.blocking_reason =
          "ordering_aware_token_loop_schedule_integrated_cpu_comparison_pending";
    }
    if (ordering_aware_token_loop_abi.launch_probe_count > 0U &&
        ordering_aware_token_loop_abi.blocking_reason &&
        strcmp(ordering_aware_token_loop_abi.blocking_reason,
               "runtime_launch_path_not_integrated") == 0) {
      ordering_aware_token_loop_abi.blocking_reason =
          ordering_aware_token_loop_abi.device_table_launch_count > 0U
              ? "ordering_aware_token_loop_device_table_launch_probe_only_not_schedule_integrated"
              : "ordering_aware_token_loop_launch_probe_only_not_schedule_integrated";
    }
    printf("ordering_aware_token_loop_abi: requested=true entrypoint_available=%s runtime_supported=%s phase_control_records=%u feedback_copy_records=%u feedback_increment_records=%u pair_cycle_loop_records=%u terminal_mask_records=%u terminal_mask_device_records=%u terminal_mask_parse_errors=%u launch_probe=%u device_table_launches=%u shadow_descriptor_records=%u shadow_descriptor_table_bytes=%u shadow_payload_bytes_per_state=%u shadow_payload_total_bytes=%zu shadow_runtime_args=%u blocking=%s kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_gpu\n",
           ordering_aware_token_loop_abi.entrypoint_available ? "true" : "false",
           ordering_aware_token_loop_abi.runtime_supported ? "true" : "false",
           ordering_aware_token_loop_abi.phase_control_record_count,
           ordering_aware_token_loop_abi.feedback_copy_record_count,
           ordering_aware_token_loop_abi.feedback_increment_record_count,
           ordering_aware_token_loop_abi.pair_cycle_loop_record_count,
           ordering_aware_token_loop_abi.terminal_mask_record_count,
           ordering_aware_token_loop_abi.terminal_mask_device_record_count,
           ordering_aware_token_loop_abi.terminal_mask_parse_error_count,
           ordering_aware_token_loop_abi.launch_probe_count,
           ordering_aware_token_loop_abi.device_table_launch_count,
           ordering_aware_token_loop_abi.cfg_clone_shadow_descriptor_count,
           ordering_aware_token_loop_abi.cfg_clone_shadow_descriptor_table_bytes,
           ordering_aware_token_loop_abi.cfg_clone_shadow_payload_bytes_per_state,
           ordering_aware_token_loop_abi.cfg_clone_shadow_payload_total_bytes,
           ordering_aware_token_loop_abi.cfg_clone_shadow_runtime_argument_count,
	           ordering_aware_token_loop_abi.blocking_reason
	               ? ordering_aware_token_loop_abi.blocking_reason
	               : "runtime_launch_path_not_integrated");
    if (ordering_aware_token_loop_cycle_limit > 0U) {
      printf("ordering_aware_token_loop_cycle_limit: requested=true limit=%u applied_launches=%u\n",
             ordering_aware_token_loop_cycle_limit,
             ordering_aware_token_loop_cycle_limit_applied);
    }
    if (ordering_aware_token_loop_abi.eval_partition_predicates_requested) {
      printf("eval_partition_predicates: requested=true observation_only=%s records=%u device_records=%u parse_errors=%u active_mask_authority=%s launch_probe=%u mode=phase_state_partition kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_gpu\n",
             ordering_aware_token_loop_abi.eval_partition_predicate_active_mask_authority
                 ? "false"
                 : "true",
             ordering_aware_token_loop_abi.eval_partition_predicate_record_count,
             ordering_aware_token_loop_abi.eval_partition_predicate_device_record_count,
             ordering_aware_token_loop_abi.eval_partition_predicate_parse_error_count,
             ordering_aware_token_loop_abi.eval_partition_predicate_active_mask_authority
                 ? "true"
                 : "false",
             ordering_aware_token_loop_abi.launch_probe_count);
      printf("eval_partition_predicate_read_no_skip: requested=%s device_read=%s launch_probe=%u skip_authority=false mode=volatile_read_no_control_flow kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_gpu\n",
             ordering_aware_token_loop_abi.eval_partition_predicate_read_no_skip_requested
                 ? "true"
                 : "false",
             (ordering_aware_token_loop_abi.eval_partition_predicate_read_no_skip_device_read &&
              ordering_aware_token_loop_abi.launch_probe_count > 0U)
                 ? "true"
                 : "false",
             ordering_aware_token_loop_abi.launch_probe_count);
      printf("eval_partition_guarded_skip: requested=%s enabled=%s launch_probe=%u skip_authority=%s mode=phase_state_partition_bitmap active_bitmap_partition_count=%u active_bitmap_phase_count=%u active_bitmap_device_bytes=%u kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_gpu\n",
             ordering_aware_token_loop_abi.eval_partition_guarded_skip_requested
                 ? "true"
                 : "false",
             (ordering_aware_token_loop_abi.eval_partition_guarded_skip_enabled &&
              ordering_aware_token_loop_abi.launch_probe_count > 0U)
                 ? "true"
                 : "false",
             ordering_aware_token_loop_abi.launch_probe_count,
             (ordering_aware_token_loop_abi.eval_partition_guarded_skip_enabled &&
              ordering_aware_token_loop_abi.launch_probe_count > 0U)
                 ? "true"
                 : "false",
             ordering_aware_token_loop_abi.eval_partition_predicate_active_bitmap_partition_count,
             ordering_aware_token_loop_abi.eval_partition_predicate_active_bitmap_phase_count,
             ordering_aware_token_loop_abi.eval_partition_predicate_active_bitmap_device_bytes);
    }
	  }
  if (single_entry_cfg_clone_liveout_oracle_requested) {
    unsigned long long cfg_clone_runtime_counters[6] = {0ULL, 0ULL, 0ULL, 0ULL, 0ULL, 0ULL};
    unsigned long long *cfg_clone_slot_mismatch_counters = NULL;
    unsigned long long *cfg_clone_slot_checked_counters = NULL;
    unsigned long long *cfg_clone_slot_actual_valid_counters = NULL;
    unsigned long long *cfg_clone_slot_expected_valid_counters = NULL;
    unsigned long long *cfg_clone_slot_entry_phi_selector_counters = NULL;
    unsigned long long *cfg_clone_slot_entry_phi_selector_indices = NULL;
    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_counters = NULL;
    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_compare_counters = NULL;
    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_mismatch_counters = NULL;
    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_store_site_compare_counters = NULL;
    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters = NULL;
    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_counters = NULL;
    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_missing_counters = NULL;
	    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples = NULL;
	    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples = NULL;
		    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_store_site_reached_counters = NULL;
		    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples = NULL;
			    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_materialized_store_reload_samples = NULL;
			    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_candidate_source_status_samples = NULL;
			    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_candidate_source_value_samples = NULL;
					    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_lowered_liveout_source_clone_cause_samples = NULL;
					    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_indices = NULL;
					    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_indices = NULL;
					    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_encoded_indices = NULL;
				    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_entry_id_samples = NULL;
						    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_raw_indices = NULL;
						    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_return_compare_proxy_read_indices = NULL;
						    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selected_encoded_value_samples = NULL;
						    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_mapped_samples = NULL;
						    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_encoded_samples = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_match_seen_samples = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_map_status_samples = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_reject_cause_samples = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_materialization_phi_incoming_count_samples = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_in_range_samples = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_encoded_indices = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_in_range_samples = NULL;
							    unsigned long long *cfg_clone_slot_selected_phi_incoming_value_producer_current_selector_phi_block_read_encoded_indices = NULL;
							    unsigned long long *all_cfg_clone_runtime_counters = NULL;
    unsigned long long liveout_frame_store_count = 0ULL;
    unsigned long long outline_call_count = 0ULL;
    unsigned long long liveout_compare_count = 0ULL;
    unsigned long long liveout_mismatch_count = 0ULL;
    unsigned long long partition_guard_execution_count = 0ULL;
    unsigned long long inactive_successor_phi_liveout_select_level_dispatch_count = 0ULL;
    int liveout_counter_available =
        d_single_entry_cfg_clone_liveout_counters != (CUdeviceptr)0;
    int liveout_counter_executed = 0;
    int liveout_counter_authority = 0;
    const char *liveout_counter_blocking =
        "runtime_outline_execution_not_integrated";
    if (liveout_counter_available) {
      size_t counter_bytes =
          single_entry_cfg_clone_liveout_counter_count *
          sizeof(unsigned long long);
      all_cfg_clone_runtime_counters =
          (unsigned long long *)calloc(single_entry_cfg_clone_liveout_counter_count,
                                      sizeof(unsigned long long));
      if (!all_cfg_clone_runtime_counters) {
        fprintf(stderr, "failed to allocate CFG-clone liveout counter buffer\n");
        return 1;
      }
      CUDA_CHECK(cuMemcpyDtoH(all_cfg_clone_runtime_counters,
                              d_single_entry_cfg_clone_liveout_counters,
                              counter_bytes));
      cfg_clone_runtime_counters[0] = all_cfg_clone_runtime_counters[0];
      cfg_clone_runtime_counters[1] = all_cfg_clone_runtime_counters[1];
      cfg_clone_runtime_counters[2] = all_cfg_clone_runtime_counters[2];
      cfg_clone_runtime_counters[3] = all_cfg_clone_runtime_counters[3];
      cfg_clone_runtime_counters[4] = all_cfg_clone_runtime_counters[4];
      cfg_clone_runtime_counters[5] = all_cfg_clone_runtime_counters[5];
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_mismatch_counters =
            all_cfg_clone_runtime_counters + 6U;
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_checked_counters =
            all_cfg_clone_runtime_counters + 6U +
            single_entry_cfg_clone_liveout_expected_count;
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_actual_valid_counters =
            all_cfg_clone_runtime_counters + 6U +
            (2U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_expected_valid_counters =
            all_cfg_clone_runtime_counters + 6U +
            (3U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_entry_phi_selector_counters =
            all_cfg_clone_runtime_counters + 6U +
            (4U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_entry_phi_selector_indices =
            all_cfg_clone_runtime_counters + 6U +
            (5U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_counters =
            all_cfg_clone_runtime_counters + 6U +
            (6U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_compare_counters =
            all_cfg_clone_runtime_counters + 6U +
            (7U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_mismatch_counters =
            all_cfg_clone_runtime_counters + 6U +
            (8U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_store_site_compare_counters =
            all_cfg_clone_runtime_counters + 6U +
            (9U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters =
            all_cfg_clone_runtime_counters + 6U +
            (10U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_counters =
            all_cfg_clone_runtime_counters + 6U +
            (11U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_missing_counters =
            all_cfg_clone_runtime_counters + 6U +
            (12U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples =
            all_cfg_clone_runtime_counters + 6U +
            (13U * single_entry_cfg_clone_liveout_expected_count);
      if (single_entry_cfg_clone_liveout_expected_count > 0U)
        cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples =
            all_cfg_clone_runtime_counters + 6U +
            (14U * single_entry_cfg_clone_liveout_expected_count);
	      if (single_entry_cfg_clone_liveout_expected_count > 0U)
	        cfg_clone_slot_selected_phi_incoming_value_store_site_reached_counters =
	            all_cfg_clone_runtime_counters + 6U +
	            (15U * single_entry_cfg_clone_liveout_expected_count);
	      if (single_entry_cfg_clone_liveout_expected_count > 0U)
		        cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples =
		            all_cfg_clone_runtime_counters + 6U +
		            (16U * single_entry_cfg_clone_liveout_expected_count);
	      if (single_entry_cfg_clone_liveout_expected_count > 0U)
	        cfg_clone_slot_selected_phi_incoming_value_materialized_store_reload_samples =
	            all_cfg_clone_runtime_counters + 6U +
	            (17U * single_entry_cfg_clone_liveout_expected_count);
	      if (single_entry_cfg_clone_liveout_expected_count > 0U)
	        cfg_clone_slot_selected_phi_incoming_value_candidate_source_status_samples =
	            all_cfg_clone_runtime_counters + 6U +
	            (18U * single_entry_cfg_clone_liveout_expected_count);
	      if (single_entry_cfg_clone_liveout_expected_count > 0U)
		        cfg_clone_slot_selected_phi_incoming_value_candidate_source_value_samples =
		            all_cfg_clone_runtime_counters + 6U +
		            (19U * single_entry_cfg_clone_liveout_expected_count);
		      if (single_entry_cfg_clone_liveout_expected_count > 0U)
		        cfg_clone_slot_selected_phi_incoming_value_lowered_liveout_source_clone_cause_samples =
		            all_cfg_clone_runtime_counters + 6U +
		            (20U * single_entry_cfg_clone_liveout_expected_count);
		      if (single_entry_cfg_clone_liveout_expected_count > 0U)
		        cfg_clone_slot_selected_phi_incoming_value_producer_selector_indices =
		            all_cfg_clone_runtime_counters + 6U +
		            (21U * single_entry_cfg_clone_liveout_expected_count);
		      if (single_entry_cfg_clone_liveout_expected_count > 0U)
		        cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_encoded_indices =
		            all_cfg_clone_runtime_counters + 6U +
		            (22U * single_entry_cfg_clone_liveout_expected_count);
			      if (single_entry_cfg_clone_liveout_expected_count > 0U)
			        cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_entry_id_samples =
			            all_cfg_clone_runtime_counters + 6U +
			            (23U * single_entry_cfg_clone_liveout_expected_count);
			      if (single_entry_cfg_clone_liveout_expected_count > 0U)
			        cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_raw_indices =
			            all_cfg_clone_runtime_counters + 6U +
			            (24U * single_entry_cfg_clone_liveout_expected_count);
				      if (single_entry_cfg_clone_liveout_expected_count > 0U)
				        cfg_clone_slot_selected_phi_incoming_value_producer_selector_return_compare_proxy_read_indices =
				            all_cfg_clone_runtime_counters + 6U +
				            (25U * single_entry_cfg_clone_liveout_expected_count);
					      if (single_entry_cfg_clone_liveout_expected_count > 0U)
					        cfg_clone_slot_selected_phi_incoming_value_producer_selected_encoded_value_samples =
					            all_cfg_clone_runtime_counters + 6U +
					            (26U * single_entry_cfg_clone_liveout_expected_count);
					      if (single_entry_cfg_clone_liveout_expected_count > 0U)
					        cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_mapped_samples =
					            all_cfg_clone_runtime_counters + 6U +
					            (27U * single_entry_cfg_clone_liveout_expected_count);
					      if (single_entry_cfg_clone_liveout_expected_count > 0U)
					        cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_encoded_samples =
					            all_cfg_clone_runtime_counters + 6U +
					            (28U * single_entry_cfg_clone_liveout_expected_count);
					      if (single_entry_cfg_clone_liveout_expected_count > 0U)
					        cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_indices =
					            all_cfg_clone_runtime_counters + 6U +
					            (29U * single_entry_cfg_clone_liveout_expected_count);
					      if (single_entry_cfg_clone_liveout_expected_count > 0U)
					        cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_match_seen_samples =
					            all_cfg_clone_runtime_counters + 6U +
					            (30U * single_entry_cfg_clone_liveout_expected_count);
					      if (single_entry_cfg_clone_liveout_expected_count > 0U)
					        cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_map_status_samples =
					            all_cfg_clone_runtime_counters + 6U +
					            (31U * single_entry_cfg_clone_liveout_expected_count);
						      if (single_entry_cfg_clone_liveout_expected_count > 0U)
						        cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_reject_cause_samples =
						            all_cfg_clone_runtime_counters + 6U +
						            (32U * single_entry_cfg_clone_liveout_expected_count);
						      if (single_entry_cfg_clone_liveout_expected_count > 0U)
						        cfg_clone_slot_selected_phi_incoming_value_producer_materialization_phi_incoming_count_samples =
						            all_cfg_clone_runtime_counters + 6U +
						            (33U * single_entry_cfg_clone_liveout_expected_count);
						      if (single_entry_cfg_clone_liveout_expected_count > 0U)
						        cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_in_range_samples =
						            all_cfg_clone_runtime_counters + 6U +
						            (34U * single_entry_cfg_clone_liveout_expected_count);
						      if (single_entry_cfg_clone_liveout_expected_count > 0U)
						        cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_encoded_indices =
						            all_cfg_clone_runtime_counters + 6U +
						            (35U * single_entry_cfg_clone_liveout_expected_count);
						      if (single_entry_cfg_clone_liveout_expected_count > 0U)
						        cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_in_range_samples =
						            all_cfg_clone_runtime_counters + 6U +
						            (36U * single_entry_cfg_clone_liveout_expected_count);
						      if (single_entry_cfg_clone_liveout_expected_count > 0U)
						        cfg_clone_slot_selected_phi_incoming_value_producer_current_selector_phi_block_read_encoded_indices =
						            all_cfg_clone_runtime_counters + 6U +
						            (37U * single_entry_cfg_clone_liveout_expected_count);
      liveout_frame_store_count = cfg_clone_runtime_counters[0];
      outline_call_count = cfg_clone_runtime_counters[1];
      liveout_compare_count = cfg_clone_runtime_counters[2];
      liveout_mismatch_count = cfg_clone_runtime_counters[3];
      partition_guard_execution_count = cfg_clone_runtime_counters[4];
      inactive_successor_phi_liveout_select_level_dispatch_count =
          cfg_clone_runtime_counters[5];
    }
    liveout_counter_executed =
        single_entry_cfg_clone_liveout_expected_count > 0U &&
        liveout_frame_store_count > 0ULL;
    unsigned checked_slot_coverage_count = 0U;
    if (cfg_clone_slot_checked_counters) {
      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
           ++slot) {
        if (cfg_clone_slot_checked_counters[slot] > 0ULL)
          ++checked_slot_coverage_count;
      }
    }
    liveout_counter_authority =
        liveout_counter_executed &&
        single_entry_cfg_clone_liveout_expected_count > 0U &&
        liveout_frame_store_count > 0ULL &&
        liveout_compare_count > 0ULL &&
        liveout_mismatch_count == 0ULL &&
        checked_slot_coverage_count ==
            single_entry_cfg_clone_liveout_expected_count;
    if (!liveout_counter_available)
      liveout_counter_blocking = "runtime_liveout_counter_not_allocated";
    else if (!liveout_counter_executed && outline_call_count == 0ULL)
      liveout_counter_blocking = "runtime_outline_call_counter_zero";
    else if (!liveout_counter_executed)
      liveout_counter_blocking = "runtime_outline_call_reached_but_cfg_clone_liveout_counter_zero";
    else if (!liveout_counter_authority)
      liveout_counter_blocking =
          checked_slot_coverage_count <
                  single_entry_cfg_clone_liveout_expected_count
              ? "runtime_checked_slot_coverage_partial"
              : "runtime_outline_execution_counter_non_authoritative";
    else
      liveout_counter_blocking = "none";
    printf("single_entry_cfg_clone_liveout_cpu_oracle_validation: requested=true executed=%s liveout_frame_store_count=%llu outline_call_count=%llu expected_liveout_value_count=%u compare_count=%llu mismatch_count=%llu",
           liveout_counter_executed ? "true" : "false",
           liveout_frame_store_count,
           outline_call_count,
           single_entry_cfg_clone_liveout_expected_count,
           liveout_compare_count,
           liveout_mismatch_count);
    if (cfg_clone_slot_mismatch_counters) {
      printf(" mismatch_slots=");
      int printed_slot = 0;
      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
           ++slot) {
        unsigned long long slot_count = cfg_clone_slot_mismatch_counters[slot];
        if (slot_count == 0ULL)
          continue;
        printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
        printed_slot = 1;
      }
      if (!printed_slot)
        printf("none");
    }
    if (cfg_clone_slot_checked_counters) {
      printf(" checked_slots=");
      int printed_slot = 0;
      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
           ++slot) {
        unsigned long long slot_count = cfg_clone_slot_checked_counters[slot];
        if (slot_count == 0ULL)
          continue;
        printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
        printed_slot = 1;
      }
      if (!printed_slot)
        printf("none");
    }
    if (cfg_clone_slot_actual_valid_counters) {
      printf(" actual_valid_slots=");
      int printed_slot = 0;
      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
           ++slot) {
        unsigned long long slot_count = cfg_clone_slot_actual_valid_counters[slot];
        if (slot_count == 0ULL)
          continue;
        printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
        printed_slot = 1;
      }
      if (!printed_slot)
        printf("none");
    }
    if (cfg_clone_slot_expected_valid_counters) {
      printf(" expected_valid_slots=");
      int printed_slot = 0;
      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
           ++slot) {
        unsigned long long slot_count = cfg_clone_slot_expected_valid_counters[slot];
        if (slot_count == 0ULL)
          continue;
        printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
        printed_slot = 1;
      }
      if (!printed_slot)
        printf("none");
    }
    printf(" authority=%s blocking=%s kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_gpu\n",
           liveout_counter_authority ? "true" : "false",
           liveout_counter_blocking);
	    if (cfg_clone_slot_entry_phi_selector_counters) {
	      unsigned selector_observed_slot_count = 0U;
	      unsigned selector_actual_valid_materialized_slot_count = 0U;
	      unsigned selector_guarded_actual_valid_candidate_count = 0U;
		      unsigned runtime_selected_phi_incoming_edge_index_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_materialized_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_compare_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_mismatch_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_store_site_compare_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_store_site_mismatch_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_store_site_expected_valid_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_store_site_expected_valid_missing_count = 0U;
		      unsigned runtime_selected_phi_incoming_value_store_site_reached_count = 0U;
		      unsigned selected_phi_incoming_value_materialization_failure_slot_count = 0U;
	      unsigned missing_runtime_selected_predecessor_edge_count = 0U;
	      unsigned selected_phi_incoming_value_materialization_counter_absent_count = 0U;
	      unsigned missing_selected_phi_incoming_value_materialization_after_edge_index_observed_count = 0U;
	      unsigned long long max_selector_observed_slot_count = 0ULL;
	      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	           ++slot) {
	        unsigned long long slot_count =
	            cfg_clone_slot_entry_phi_selector_counters[slot];
	        if (slot_count == 0ULL)
	          continue;
	        ++selector_observed_slot_count;
	        ++selector_guarded_actual_valid_candidate_count;
	        if (cfg_clone_slot_actual_valid_counters &&
	            cfg_clone_slot_actual_valid_counters[slot] > 0ULL)
	          ++selector_actual_valid_materialized_slot_count;
	        if (slot_count > max_selector_observed_slot_count)
	          max_selector_observed_slot_count = slot_count;
	        if (cfg_clone_slot_entry_phi_selector_indices &&
	            cfg_clone_slot_entry_phi_selector_indices[slot] > 0ULL)
	          ++runtime_selected_phi_incoming_edge_index_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_materialized_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_compare_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_compare_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_compare_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_mismatch_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_mismatch_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_mismatch_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_store_site_compare_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_store_site_compare_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_store_site_compare_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_store_site_mismatch_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_store_site_expected_valid_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_missing_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_missing_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_store_site_expected_valid_missing_count;
		        if (cfg_clone_slot_selected_phi_incoming_value_store_site_reached_counters &&
		            cfg_clone_slot_selected_phi_incoming_value_store_site_reached_counters[slot] > 0ULL)
		          ++runtime_selected_phi_incoming_value_store_site_reached_count;
	        if (!cfg_clone_slot_entry_phi_selector_indices) {
	          ++selected_phi_incoming_value_materialization_failure_slot_count;
	          ++missing_runtime_selected_predecessor_edge_count;
	        } else if (cfg_clone_slot_entry_phi_selector_indices[slot] == 0ULL) {
	          ++selected_phi_incoming_value_materialization_failure_slot_count;
	          ++missing_runtime_selected_predecessor_edge_count;
	        } else if (!cfg_clone_slot_selected_phi_incoming_value_counters) {
	          ++selected_phi_incoming_value_materialization_failure_slot_count;
	          ++selected_phi_incoming_value_materialization_counter_absent_count;
	        } else if (cfg_clone_slot_selected_phi_incoming_value_counters[slot] == 0ULL) {
	          ++selected_phi_incoming_value_materialization_failure_slot_count;
	          ++missing_selected_phi_incoming_value_materialization_after_edge_index_observed_count;
	        }
	      }
	      const char *selector_actual_valid_gate_blocking =
	          "diagnostic_entry_phi_selector_counter_not_observed";
	      if (selector_observed_slot_count > 0U &&
	          selector_actual_valid_materialized_slot_count == 0U)
	        selector_actual_valid_gate_blocking =
	            "selector_counter_observed_but_actual_valid_materialization_missing";
	      else if (selector_observed_slot_count > 0U &&
	               selector_actual_valid_materialized_slot_count <
	                   selector_observed_slot_count)
	        selector_actual_valid_gate_blocking =
	            "selector_counter_actual_valid_materialization_partial";
	      else if (selector_observed_slot_count > 0U)
	        selector_actual_valid_gate_blocking =
	            "selector_counter_actual_valid_materialization_observed_no_authority";
	      printf("diagnostic_entry_phi_predecessor_selector_abi: requested=true runtime_supported=true selector_abi_available=true expected_liveout_value_count=%u selector_counter_count=%u selector_observed_slots=",
	             single_entry_cfg_clone_liveout_expected_count,
	             single_entry_cfg_clone_liveout_expected_count);
      int printed_slot = 0;
      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
           ++slot) {
        unsigned long long slot_count =
            cfg_clone_slot_entry_phi_selector_counters[slot];
        if (slot_count == 0ULL)
          continue;
        printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
        printed_slot = 1;
	      }
	      if (!printed_slot)
	        printf("none");
		      printf(" selector_observed_slot_count=%u max_selector_observed_slot_count=%llu runtime_selector_argument_count=1 replay_authorized_count=0 selected_phi_incoming_slots=",
		             selector_observed_slot_count,
		             max_selector_observed_slot_count);
      printed_slot = 0;
      if (cfg_clone_slot_entry_phi_selector_indices) {
        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
             ++slot) {
          unsigned long long encoded_index =
              cfg_clone_slot_entry_phi_selector_indices[slot];
          if (encoded_index == 0ULL)
            continue;
          printf("%s%u:%llu", printed_slot ? "," : "", slot,
                 encoded_index - 1ULL);
          printed_slot = 1;
        }
      }
      if (!printed_slot)
        printf("none");
      printf(" selected_phi_incoming_producer_slots=");
      printed_slot = 0;
      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_indices) {
        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
             ++slot) {
          unsigned long long encoded_index =
              cfg_clone_slot_selected_phi_incoming_value_producer_selector_indices[slot];
          if (encoded_index == 0ULL)
            continue;
          printf("%s%u:%llu", printed_slot ? "," : "", slot,
                 encoded_index - 1ULL);
          printed_slot = 1;
        }
      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_producer_last_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_indices) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long encoded_index =
	              cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_indices[slot];
	          if (encoded_index == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot,
	                 encoded_index - 1ULL);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_producer_read_encoded_slots=");
      printed_slot = 0;
      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_encoded_indices) {
        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
             ++slot) {
          unsigned long long encoded_index =
              cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_encoded_indices[slot];
          printf("%s%u:%llu", printed_slot ? "," : "", slot, encoded_index);
          printed_slot = 1;
        }
      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_producer_read_raw_encoded_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_raw_indices) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long encoded_index =
	              cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_raw_indices[slot];
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, encoded_index);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_producer_return_compare_proxy_read_encoded_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_return_compare_proxy_read_indices) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long encoded_index =
	              cfg_clone_slot_selected_phi_incoming_value_producer_selector_return_compare_proxy_read_indices[slot];
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, encoded_index);
	          printed_slot = 1;
	        }
	      }
		      if (!printed_slot)
		        printf("none");
		      printf(" selected_phi_incoming_producer_selected_encoded_value_slots=");
		      printed_slot = 0;
		      if (cfg_clone_slot_selected_phi_incoming_value_producer_selected_encoded_value_samples) {
		        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
		             ++slot) {
		          unsigned long long selected_value =
		              cfg_clone_slot_selected_phi_incoming_value_producer_selected_encoded_value_samples[slot];
		          printf("%s%u:%llu", printed_slot ? "," : "", slot, selected_value);
		          printed_slot = 1;
		        }
		      }
			      if (!printed_slot)
			        printf("none");
			      printf(" selected_phi_incoming_producer_selected_edge_mapped_slots=");
			      printed_slot = 0;
			      if (cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_mapped_samples) {
			        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
			             ++slot) {
			          unsigned long long mapped =
			              cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_mapped_samples[slot];
			          printf("%s%u:%llu", printed_slot ? "," : "", slot, mapped);
			          printed_slot = 1;
			        }
			      }
			      if (!printed_slot)
			        printf("none");
			      printf(" selected_phi_incoming_producer_selected_edge_encoded_slots=");
			      printed_slot = 0;
			      if (cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_encoded_samples) {
			        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
			             ++slot) {
			          unsigned long long encoded =
			              cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_encoded_samples[slot];
			          printf("%s%u:%llu", printed_slot ? "," : "", slot, encoded);
			          printed_slot = 1;
			        }
			      }
			      if (!printed_slot)
			        printf("none");
			      printf(" selected_phi_incoming_producer_selected_edge_match_seen_slots=");
			      printed_slot = 0;
			      if (cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_match_seen_samples) {
			        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
			             ++slot) {
			          unsigned long long seen =
			              cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_match_seen_samples[slot];
			          printf("%s%u:%llu", printed_slot ? "," : "", slot, seen);
			          printed_slot = 1;
			        }
			      }
			      if (!printed_slot)
			        printf("none");
			      printf(" selected_phi_incoming_producer_selected_edge_map_status_slots=");
			      printed_slot = 0;
			      if (cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_map_status_samples) {
			        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
			             ++slot) {
			          unsigned long long status =
			              cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_map_status_samples[slot];
			          printf("%s%u:%llu", printed_slot ? "," : "", slot, status);
			          printed_slot = 1;
			        }
			      }
			      if (!printed_slot)
			        printf("none");
			      printf(" selected_phi_incoming_producer_selected_edge_reject_cause_slots=");
			      printed_slot = 0;
			      if (cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_reject_cause_samples) {
			        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
			             ++slot) {
			          unsigned long long cause =
			              cfg_clone_slot_selected_phi_incoming_value_producer_selected_edge_reject_cause_samples[slot];
			          printf("%s%u:%llu", printed_slot ? "," : "", slot, cause);
			          printed_slot = 1;
			        }
			      }
				      if (!printed_slot)
				        printf("none");
				      printf(" selected_phi_incoming_producer_materialization_phi_incoming_count_slots=");
				      printed_slot = 0;
				      if (cfg_clone_slot_selected_phi_incoming_value_producer_materialization_phi_incoming_count_samples) {
				        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
				             ++slot) {
				          unsigned long long count =
				              cfg_clone_slot_selected_phi_incoming_value_producer_materialization_phi_incoming_count_samples[slot];
				          if (count == 0ULL)
				            continue;
				          printf("%s%u:%llu", printed_slot ? "," : "", slot, count);
				          printed_slot = 1;
				        }
				      }
				      if (!printed_slot)
				        printf("none");
				      printf(" selected_phi_incoming_producer_read_in_range_slots=");
				      printed_slot = 0;
				      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_in_range_samples) {
				        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
				             ++slot) {
				          unsigned long long in_range =
				              cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_in_range_samples[slot];
				          printf("%s%u:%llu", printed_slot ? "," : "", slot, in_range);
				          printed_slot = 1;
				        }
				      }
				      if (!printed_slot)
				        printf("none");
				      printf(" selected_phi_incoming_producer_last_read_encoded_slots=");
				      printed_slot = 0;
				      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_encoded_indices) {
				        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
				             ++slot) {
				          unsigned long long encoded =
				              cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_encoded_indices[slot];
				          printf("%s%u:%llu", printed_slot ? "," : "", slot, encoded);
				          printed_slot = 1;
				        }
				      }
				      if (!printed_slot)
				        printf("none");
				      printf(" selected_phi_incoming_producer_last_read_in_range_slots=");
				      printed_slot = 0;
				      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_in_range_samples) {
				        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
				             ++slot) {
				          unsigned long long in_range =
				              cfg_clone_slot_selected_phi_incoming_value_producer_selector_last_read_in_range_samples[slot];
				          printf("%s%u:%llu", printed_slot ? "," : "", slot, in_range);
				          printed_slot = 1;
				        }
				      }
				      if (!printed_slot)
				        printf("none");
				      printf(" selected_phi_incoming_producer_current_selector_phi_block_read_encoded_slots=");
				      printed_slot = 0;
				      if (cfg_clone_slot_selected_phi_incoming_value_producer_current_selector_phi_block_read_encoded_indices) {
				        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
				             ++slot) {
				          unsigned long long encoded =
				              cfg_clone_slot_selected_phi_incoming_value_producer_current_selector_phi_block_read_encoded_indices[slot];
				          printf("%s%u:%llu", printed_slot ? "," : "", slot, encoded);
				          printed_slot = 1;
				        }
				      }
				      if (!printed_slot)
				        printf("none");
				      print_cfg_clone_raw_band_slots(
				          "cfg_clone_liveout_raw_band22_slots",
				          all_cfg_clone_runtime_counters,
				          single_entry_cfg_clone_liveout_expected_count, 22U);
				      print_cfg_clone_raw_band_slots(
				          "cfg_clone_liveout_raw_band33_slots",
				          all_cfg_clone_runtime_counters,
				          single_entry_cfg_clone_liveout_expected_count, 33U);
				      print_cfg_clone_raw_band_slots(
				          "cfg_clone_liveout_raw_band37_slots",
				          all_cfg_clone_runtime_counters,
				          single_entry_cfg_clone_liveout_expected_count, 37U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band38_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 38U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band39_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 39U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band40_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 40U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band41_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 41U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band42_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 42U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band43_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 43U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band44_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 44U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band45_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 45U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band46_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 46U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band47_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 47U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band48_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 48U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band49_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 49U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band50_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 50U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band51_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 51U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band52_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 52U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band53_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 53U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band54_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 54U);
					      print_cfg_clone_raw_band_slots(
					          "cfg_clone_liveout_raw_band55_slots",
					          all_cfg_clone_runtime_counters,
					          single_entry_cfg_clone_liveout_expected_count, 55U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band56_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 56U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band57_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 57U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band58_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 58U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band59_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 59U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band60_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 60U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band61_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 61U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band62_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 62U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band63_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 63U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band64_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 64U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band65_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 65U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band66_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 66U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band67_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 67U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band68_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 68U);
						      print_cfg_clone_raw_band_slots(
						          "cfg_clone_liveout_raw_band69_slots",
						          all_cfg_clone_runtime_counters,
						          single_entry_cfg_clone_liveout_expected_count, 69U);
							      print_cfg_clone_raw_band_slots(
							          "cfg_clone_liveout_raw_band70_slots",
							          all_cfg_clone_runtime_counters,
							          single_entry_cfg_clone_liveout_expected_count, 70U);
							      print_cfg_clone_raw_band_slots(
							          "cfg_clone_liveout_raw_band71_slots",
							          all_cfg_clone_runtime_counters,
							          single_entry_cfg_clone_liveout_expected_count, 71U);
							      print_cfg_clone_raw_band_slots(
							          "cfg_clone_liveout_raw_band72_slots",
							          all_cfg_clone_runtime_counters,
							          single_entry_cfg_clone_liveout_expected_count, 72U);
							      print_cfg_clone_raw_band_slots(
							          "cfg_clone_liveout_raw_band73_slots",
							          all_cfg_clone_runtime_counters,
							          single_entry_cfg_clone_liveout_expected_count, 73U);
								      print_cfg_clone_raw_band_slots(
								          "cfg_clone_liveout_raw_band74_slots",
								          all_cfg_clone_runtime_counters,
								          single_entry_cfg_clone_liveout_expected_count, 74U);
								      print_cfg_clone_raw_band_slots(
								          "cfg_clone_liveout_raw_band75_slots",
								          all_cfg_clone_runtime_counters,
								          single_entry_cfg_clone_liveout_expected_count, 75U);
								      print_cfg_clone_raw_band_slots(
								          "cfg_clone_liveout_raw_band76_slots",
								          all_cfg_clone_runtime_counters,
								          single_entry_cfg_clone_liveout_expected_count, 76U);
									      print_cfg_clone_raw_band_slots(
									          "cfg_clone_liveout_raw_band77_slots",
									          all_cfg_clone_runtime_counters,
									          single_entry_cfg_clone_liveout_expected_count, 77U);
									      print_cfg_clone_raw_band_slots(
									          "cfg_clone_liveout_raw_band78_slots",
									          all_cfg_clone_runtime_counters,
									          single_entry_cfg_clone_liveout_expected_count, 78U);
									      print_cfg_clone_raw_band_slots(
									          "cfg_clone_liveout_raw_band79_slots",
									          all_cfg_clone_runtime_counters,
									          single_entry_cfg_clone_liveout_expected_count, 79U);
									      print_cfg_clone_raw_band_slots(
									          "cfg_clone_liveout_raw_band80_slots",
									          all_cfg_clone_runtime_counters,
									          single_entry_cfg_clone_liveout_expected_count, 80U);
									      print_cfg_clone_raw_band_slots(
									          "cfg_clone_liveout_raw_band81_slots",
									          all_cfg_clone_runtime_counters,
									          single_entry_cfg_clone_liveout_expected_count, 81U);
									      print_cfg_clone_raw_band_slots(
									          "cfg_clone_liveout_raw_band82_slots",
									          all_cfg_clone_runtime_counters,
									          single_entry_cfg_clone_liveout_expected_count, 82U);
									      print_cfg_clone_raw_band_slots(
									          "cfg_clone_liveout_raw_band83_slots",
									          all_cfg_clone_runtime_counters,
									          single_entry_cfg_clone_liveout_expected_count, 83U);
										      print_cfg_clone_raw_band_slots(
										          "cfg_clone_liveout_raw_band84_slots",
										          all_cfg_clone_runtime_counters,
										          single_entry_cfg_clone_liveout_expected_count, 84U);
										      print_cfg_clone_raw_band_slots(
										          "cfg_clone_liveout_raw_band85_slots",
										          all_cfg_clone_runtime_counters,
										          single_entry_cfg_clone_liveout_expected_count, 85U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band86_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 86U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band87_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 87U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band88_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 88U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band89_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 89U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band90_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 90U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band91_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 91U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band92_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 92U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band93_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 93U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band94_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 94U);
											      print_cfg_clone_raw_band_slots(
											          "cfg_clone_liveout_raw_band95_slots",
											          all_cfg_clone_runtime_counters,
											          single_entry_cfg_clone_liveout_expected_count, 95U);
												      print_cfg_clone_raw_band_slots(
												          "cfg_clone_liveout_raw_band96_slots",
												          all_cfg_clone_runtime_counters,
												          single_entry_cfg_clone_liveout_expected_count, 96U);
												      print_cfg_clone_raw_band_slots(
												          "cfg_clone_liveout_raw_band97_slots",
												          all_cfg_clone_runtime_counters,
												          single_entry_cfg_clone_liveout_expected_count, 97U);
												      print_cfg_clone_raw_band_slots(
												          "cfg_clone_liveout_raw_band98_slots",
												          all_cfg_clone_runtime_counters,
												          single_entry_cfg_clone_liveout_expected_count, 98U);
												      print_cfg_clone_raw_band_slots(
												          "cfg_clone_liveout_raw_band99_slots",
												          all_cfg_clone_runtime_counters,
												          single_entry_cfg_clone_liveout_expected_count, 99U);
													      print_cfg_clone_raw_band_slots(
													          "cfg_clone_liveout_raw_band100_slots",
													          all_cfg_clone_runtime_counters,
													          single_entry_cfg_clone_liveout_expected_count, 100U);
													      print_cfg_clone_raw_band_slots(
													          "cfg_clone_liveout_raw_band101_slots",
													          all_cfg_clone_runtime_counters,
													          single_entry_cfg_clone_liveout_expected_count, 101U);
													      print_cfg_clone_raw_band_slots(
													          "cfg_clone_liveout_raw_band102_slots",
													          all_cfg_clone_runtime_counters,
													          single_entry_cfg_clone_liveout_expected_count, 102U);
													      print_cfg_clone_raw_band_slots(
													          "cfg_clone_liveout_raw_band103_slots",
													          all_cfg_clone_runtime_counters,
													          single_entry_cfg_clone_liveout_expected_count, 103U);
													      print_cfg_clone_raw_band_slots(
													          "cfg_clone_liveout_raw_band104_slots",
													          all_cfg_clone_runtime_counters,
													          single_entry_cfg_clone_liveout_expected_count, 104U);
													      print_cfg_clone_raw_band_slots(
													          "cfg_clone_liveout_raw_band105_slots",
													          all_cfg_clone_runtime_counters,
													          single_entry_cfg_clone_liveout_expected_count, 105U);
												      printf(" selected_phi_incoming_producer_read_entry_id_slots=");
      printed_slot = 0;
      if (cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_entry_id_samples) {
        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
             ++slot) {
          unsigned long long entry_id =
              cfg_clone_slot_selected_phi_incoming_value_producer_selector_read_entry_id_samples[slot];
          printf("%s%u:%llu", printed_slot ? "," : "", slot, entry_id);
          printed_slot = 1;
        }
      }
      if (!printed_slot)
        printf("none");
      printf(" selected_phi_incoming_value_materialized_slots=");
      printed_slot = 0;
      if (cfg_clone_slot_selected_phi_incoming_value_counters) {
        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
             ++slot) {
          unsigned long long slot_count =
              cfg_clone_slot_selected_phi_incoming_value_counters[slot];
          if (slot_count == 0ULL)
            continue;
          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
          printed_slot = 1;
        }
      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_store_site_reached_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_store_site_reached_counters) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long slot_count =
	              cfg_clone_slot_selected_phi_incoming_value_store_site_reached_counters[slot];
	          if (slot_count == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_compare_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_compare_counters) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long slot_count =
	              cfg_clone_slot_selected_phi_incoming_value_compare_counters[slot];
	          if (slot_count == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_mismatch_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_mismatch_counters) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long slot_count =
	              cfg_clone_slot_selected_phi_incoming_value_mismatch_counters[slot];
	          if (slot_count == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_store_site_immediate_compare_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_store_site_compare_counters) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long slot_count =
	              cfg_clone_slot_selected_phi_incoming_value_store_site_compare_counters[slot];
	          if (slot_count == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_store_site_immediate_mismatch_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long slot_count =
	              cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters[slot];
	          if (slot_count == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_store_site_immediate_expected_valid_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_counters) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long slot_count =
	              cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_counters[slot];
	          if (slot_count == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_store_site_immediate_expected_valid_missing_slots=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_missing_counters) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long slot_count =
	              cfg_clone_slot_selected_phi_incoming_value_store_site_expected_valid_missing_counters[slot];
	          if (slot_count == 0ULL)
	            continue;
	          printf("%s%u:%llu", printed_slot ? "," : "", slot, slot_count);
	          printed_slot = 1;
	        }
	      }
	      if (!printed_slot)
	        printf("none");
	      printf(" selected_phi_incoming_value_return_compare_samples=");
	      printed_slot = 0;
	      if (cfg_clone_slot_selected_phi_incoming_value_mismatch_counters &&
	          cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples &&
	          cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples) {
	        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
	             ++slot) {
	          unsigned long long mismatch_count =
	              cfg_clone_slot_selected_phi_incoming_value_mismatch_counters[slot];
	          if (mismatch_count == 0ULL)
	            continue;
	          unsigned long long edge_index =
	              cfg_clone_slot_entry_phi_selector_indices
	                  ? cfg_clone_slot_entry_phi_selector_indices[slot]
	                  : 0ULL;
	          unsigned long long actual_value =
	              cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples[slot];
	          unsigned long long expected_value =
	              cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples[slot];
	          printf("%s%u:%llu:%llu:%llu",
	                 printed_slot ? "," : "",
	                 slot,
	                 edge_index,
	                 actual_value,
	                 expected_value);
	          printed_slot = 1;
	        }
	      }
		      if (!printed_slot)
		        printf("none");
		      printf(" selected_phi_incoming_value_candidate_source_status_samples=");
		      printed_slot = 0;
		      if (cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters &&
		          cfg_clone_slot_selected_phi_incoming_value_candidate_source_status_samples) {
		        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
		             ++slot) {
		          unsigned long long mismatch_count =
		              cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters[slot];
		          if (mismatch_count == 0ULL)
		            continue;
		          unsigned long long edge_index =
		              cfg_clone_slot_entry_phi_selector_indices
		                  ? cfg_clone_slot_entry_phi_selector_indices[slot]
		                  : 0ULL;
		          unsigned long long candidate_status =
		              cfg_clone_slot_selected_phi_incoming_value_candidate_source_status_samples[slot];
		          printf("%s%u:%llu:%llu",
		                 printed_slot ? "," : "",
		                 slot,
		                 edge_index,
		                 candidate_status);
		          printed_slot = 1;
		        }
		      }
			      if (!printed_slot)
			        printf("none");
			      printf(" selected_phi_incoming_value_lowered_liveout_source_clone_cause_samples=");
			      printed_slot = 0;
			      if (cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters &&
			          cfg_clone_slot_selected_phi_incoming_value_lowered_liveout_source_clone_cause_samples) {
			        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
			             ++slot) {
			          unsigned long long mismatch_count =
			              cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters[slot];
			          if (mismatch_count == 0ULL)
			            continue;
			          unsigned long long edge_index =
			              cfg_clone_slot_entry_phi_selector_indices
			                  ? cfg_clone_slot_entry_phi_selector_indices[slot]
			                  : 0ULL;
			          unsigned long long cause =
			              cfg_clone_slot_selected_phi_incoming_value_lowered_liveout_source_clone_cause_samples[slot];
			          printf("%s%u:%llu:%llu",
			                 printed_slot ? "," : "",
			                 slot,
			                 edge_index,
			                 cause);
			          printed_slot = 1;
			        }
			      }
			      if (!printed_slot)
			        printf("none");
			      printf(" selected_phi_incoming_value_encoded_before_store_reload_samples=");
		      printed_slot = 0;
		      if (cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters &&
		          cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_materialized_store_reload_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_candidate_source_value_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples) {
		        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
		             ++slot) {
		          unsigned long long mismatch_count =
		              cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters[slot];
		          if (mismatch_count == 0ULL)
		            continue;
		          unsigned long long edge_index =
		              cfg_clone_slot_entry_phi_selector_indices
		                  ? cfg_clone_slot_entry_phi_selector_indices[slot]
		                  : 0ULL;
		          unsigned long long candidate_value =
		              cfg_clone_slot_selected_phi_incoming_value_candidate_source_value_samples[slot];
		          unsigned long long materialized_value =
		              cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples[slot];
		          unsigned long long reloaded_value =
		              cfg_clone_slot_selected_phi_incoming_value_materialized_store_reload_samples[slot];
		          unsigned long long actual_value =
		              cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples[slot];
		          unsigned long long expected_value =
		              cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples[slot];
		          printf("%s%u:%llu:%llu:%llu:%llu:%llu:%llu",
		                 printed_slot ? "," : "",
		                 slot,
		                 edge_index,
		                 candidate_value,
		                 materialized_value,
		                 reloaded_value,
		                 actual_value,
		                 expected_value);
		          printed_slot = 1;
		        }
		      }
		      if (!printed_slot)
		        printf("none");
		      printf(" selected_phi_incoming_value_materialized_store_samples=");
		      printed_slot = 0;
		      if (cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters &&
		          cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples) {
		        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
		             ++slot) {
		          unsigned long long mismatch_count =
		              cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters[slot];
		          if (mismatch_count == 0ULL)
		            continue;
		          unsigned long long edge_index =
		              cfg_clone_slot_entry_phi_selector_indices
		                  ? cfg_clone_slot_entry_phi_selector_indices[slot]
		                  : 0ULL;
		          unsigned long long materialized_value =
		              cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples[slot];
		          unsigned long long actual_value =
		              cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples[slot];
		          unsigned long long expected_value =
		              cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples[slot];
		          printf("%s%u:%llu:%llu:%llu:%llu",
		                 printed_slot ? "," : "",
		                 slot,
		                 edge_index,
		                 materialized_value,
		                 actual_value,
		                 expected_value);
		          printed_slot = 1;
		        }
		      }
			      if (!printed_slot)
			        printf("none");
		      printf(" selected_phi_incoming_value_materialized_store_reload_samples=");
		      printed_slot = 0;
		      if (cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters &&
		          cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_materialized_store_reload_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples &&
		          cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples) {
		        for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
		             ++slot) {
		          unsigned long long mismatch_count =
		              cfg_clone_slot_selected_phi_incoming_value_store_site_mismatch_counters[slot];
		          if (mismatch_count == 0ULL)
		            continue;
		          unsigned long long edge_index =
		              cfg_clone_slot_entry_phi_selector_indices
		                  ? cfg_clone_slot_entry_phi_selector_indices[slot]
		                  : 0ULL;
		          unsigned long long materialized_value =
		              cfg_clone_slot_selected_phi_incoming_value_materialized_store_samples[slot];
		          unsigned long long reloaded_value =
		              cfg_clone_slot_selected_phi_incoming_value_materialized_store_reload_samples[slot];
		          unsigned long long actual_value =
		              cfg_clone_slot_selected_phi_incoming_value_return_compare_actual_samples[slot];
		          unsigned long long expected_value =
		              cfg_clone_slot_selected_phi_incoming_value_return_compare_expected_samples[slot];
		          printf("%s%u:%llu:%llu:%llu:%llu:%llu",
		                 printed_slot ? "," : "",
		                 slot,
		                 edge_index,
		                 materialized_value,
		                 reloaded_value,
		                 actual_value,
		                 expected_value);
		          printed_slot = 1;
		        }
		      }
		      if (!printed_slot)
		        printf("none");
			      printf(" selected_phi_incoming_value_materialization_failure_slots=");
      printed_slot = 0;
      for (unsigned slot = 0; slot < single_entry_cfg_clone_liveout_expected_count;
           ++slot) {
        unsigned long long selector_count =
            cfg_clone_slot_entry_phi_selector_counters[slot];
        if (selector_count == 0ULL)
          continue;
        const char *reason = NULL;
        if (!cfg_clone_slot_entry_phi_selector_indices ||
            cfg_clone_slot_entry_phi_selector_indices[slot] == 0ULL)
          reason = "missing_runtime_selected_predecessor_edge";
        else if (!cfg_clone_slot_selected_phi_incoming_value_counters)
          reason = "selected_phi_incoming_value_materialization_counter_absent";
        else if (cfg_clone_slot_selected_phi_incoming_value_counters[slot] == 0ULL)
          reason =
              "missing_selected_phi_incoming_value_materialization_after_edge_index_observed";
        if (!reason)
          continue;
        printf("%s%u:%s", printed_slot ? "," : "", slot, reason);
        printed_slot = 1;
      }
      if (!printed_slot)
        printf("none");
      printf(" selected_phi_incoming_value_materialization_failure_slot_count=%u selected_phi_incoming_value_materialization_failure_reason_counts=",
             selected_phi_incoming_value_materialization_failure_slot_count);
      printed_slot = 0;
      if (missing_runtime_selected_predecessor_edge_count > 0U) {
        printf("%smissing_runtime_selected_predecessor_edge:%u",
               printed_slot ? "," : "",
               missing_runtime_selected_predecessor_edge_count);
        printed_slot = 1;
      }
      if (selected_phi_incoming_value_materialization_counter_absent_count > 0U) {
        printf("%sselected_phi_incoming_value_materialization_counter_absent:%u",
               printed_slot ? "," : "",
               selected_phi_incoming_value_materialization_counter_absent_count);
        printed_slot = 1;
      }
      if (missing_selected_phi_incoming_value_materialization_after_edge_index_observed_count > 0U) {
        printf("%smissing_selected_phi_incoming_value_materialization_after_edge_index_observed:%u",
               printed_slot ? "," : "",
               missing_selected_phi_incoming_value_materialization_after_edge_index_observed_count);
        printed_slot = 1;
      }
      if (!printed_slot)
        printf("none");
      const char *dominant_selected_phi_incoming_value_materialization_failure_reason =
          "none";
      if (missing_selected_phi_incoming_value_materialization_after_edge_index_observed_count >=
              missing_runtime_selected_predecessor_edge_count &&
          missing_selected_phi_incoming_value_materialization_after_edge_index_observed_count >=
              selected_phi_incoming_value_materialization_counter_absent_count &&
          missing_selected_phi_incoming_value_materialization_after_edge_index_observed_count >
              0U)
        dominant_selected_phi_incoming_value_materialization_failure_reason =
            "missing_selected_phi_incoming_value_materialization_after_edge_index_observed";
      else if (missing_runtime_selected_predecessor_edge_count >=
                   selected_phi_incoming_value_materialization_counter_absent_count &&
               missing_runtime_selected_predecessor_edge_count > 0U)
        dominant_selected_phi_incoming_value_materialization_failure_reason =
            "missing_runtime_selected_predecessor_edge";
      else if (selected_phi_incoming_value_materialization_counter_absent_count > 0U)
        dominant_selected_phi_incoming_value_materialization_failure_reason =
            "selected_phi_incoming_value_materialization_counter_absent";
			      printf(" dominant_selected_phi_incoming_value_materialization_failure_reason=%s selected_phi_incoming_slot_count=%u runtime_selected_phi_incoming_edge_index_count=%u missing_runtime_selected_phi_incoming_edge_index_count=%u runtime_selected_phi_incoming_edge_index_authority=%s selected_phi_incoming_value_materialized_slot_count=%u runtime_selected_phi_incoming_value_materialized_count=%u missing_runtime_selected_phi_incoming_value_materialized_count=%u runtime_selected_phi_incoming_value_materialization_authority=%s selected_phi_incoming_value_store_site_reached_slot_count=%u runtime_selected_phi_incoming_value_store_site_reached_count=%u selected_phi_incoming_value_store_site_reached_authority=%s selected_phi_incoming_value_compare_slot_count=%u runtime_selected_phi_incoming_value_compare_count=%u selected_phi_incoming_value_mismatch_slot_count=%u runtime_selected_phi_incoming_value_mismatch_count=%u selected_phi_incoming_value_compare_authority=%s selected_phi_incoming_value_store_site_immediate_compare_slot_count=%u runtime_selected_phi_incoming_value_store_site_immediate_compare_count=%u selected_phi_incoming_value_store_site_immediate_mismatch_slot_count=%u runtime_selected_phi_incoming_value_store_site_immediate_mismatch_count=%u selected_phi_incoming_value_store_site_immediate_compare_authority=%s selected_phi_incoming_value_store_site_immediate_expected_valid_slot_count=%u runtime_selected_phi_incoming_value_store_site_immediate_expected_valid_count=%u selected_phi_incoming_value_store_site_immediate_expected_valid_missing_slot_count=%u runtime_selected_phi_incoming_value_store_site_immediate_expected_valid_missing_count=%u selected_phi_incoming_value_store_site_immediate_expected_valid_authority=%s selector_actual_valid_materialized_slot_count=%u selector_guarded_actual_valid_candidate_count=%u selector_actual_valid_authority_review=blocked_missing_value_semantic_authority actual_valid_authorized_count=0 authority=false blocking=%s kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_gpu\n",
			             dominant_selected_phi_incoming_value_materialization_failure_reason,
		             runtime_selected_phi_incoming_edge_index_count,
		             runtime_selected_phi_incoming_edge_index_count,
		             selector_guarded_actual_valid_candidate_count >
		                     runtime_selected_phi_incoming_edge_index_count
		                 ? selector_guarded_actual_valid_candidate_count -
		                       runtime_selected_phi_incoming_edge_index_count
		                 : 0U,
		             runtime_selected_phi_incoming_edge_index_count > 0U
		                 ? "observed_expected_capture_edge_index_no_value_or_actual_valid_authority"
		                 : "missing_runtime_selected_predecessor_edge",
		             runtime_selected_phi_incoming_value_materialized_count,
		             runtime_selected_phi_incoming_value_materialized_count,
		             selector_guarded_actual_valid_candidate_count >
		                     runtime_selected_phi_incoming_value_materialized_count
		                 ? selector_guarded_actual_valid_candidate_count -
		                       runtime_selected_phi_incoming_value_materialized_count
		                 : 0U,
			             runtime_selected_phi_incoming_value_materialized_count > 0U
			                 ? "selected_phi_incoming_value_materialized_no_actual_valid_authority"
			                 : "missing_selected_phi_incoming_value_materialization",
			             runtime_selected_phi_incoming_value_store_site_reached_count,
			             runtime_selected_phi_incoming_value_store_site_reached_count,
			             runtime_selected_phi_incoming_value_store_site_reached_count > 0U
			                 ? "selected_phi_incoming_value_store_site_reached_unproven_return_compare_proxy_no_actual_valid_authority"
			                 : "selected_phi_incoming_value_store_site_not_reached",
			             runtime_selected_phi_incoming_value_compare_count,
			             runtime_selected_phi_incoming_value_compare_count,
			             runtime_selected_phi_incoming_value_mismatch_count,
			             runtime_selected_phi_incoming_value_mismatch_count,
			             runtime_selected_phi_incoming_value_compare_count > 0U &&
			                     runtime_selected_phi_incoming_value_mismatch_count == 0U
			                 ? "selected_phi_incoming_value_compared_no_actual_valid_authority"
			                 : runtime_selected_phi_incoming_value_mismatch_count > 0U
			                       ? "selected_phi_incoming_value_compare_mismatch_no_actual_valid_authority"
			                       : "selected_phi_incoming_value_compare_missing",
			             runtime_selected_phi_incoming_value_store_site_compare_count,
			             runtime_selected_phi_incoming_value_store_site_compare_count,
			             runtime_selected_phi_incoming_value_store_site_mismatch_count,
			             runtime_selected_phi_incoming_value_store_site_mismatch_count,
			             runtime_selected_phi_incoming_value_store_site_compare_count > 0U &&
			                     runtime_selected_phi_incoming_value_store_site_mismatch_count == 0U
			                 ? "selected_phi_incoming_value_store_site_immediate_compared_no_actual_valid_authority"
			                 : runtime_selected_phi_incoming_value_store_site_mismatch_count > 0U
			                       ? "selected_phi_incoming_value_store_site_immediate_compare_mismatch_no_actual_valid_authority"
			                       : "selected_phi_incoming_value_store_site_immediate_compare_missing",
			             runtime_selected_phi_incoming_value_store_site_expected_valid_count,
			             runtime_selected_phi_incoming_value_store_site_expected_valid_count,
			             runtime_selected_phi_incoming_value_store_site_expected_valid_missing_count,
			             runtime_selected_phi_incoming_value_store_site_expected_valid_missing_count,
			             runtime_selected_phi_incoming_value_store_site_expected_valid_count > 0U
			                 ? "selected_phi_incoming_value_store_site_immediate_expected_valid_observed_no_actual_valid_authority"
			                 : runtime_selected_phi_incoming_value_store_site_expected_valid_missing_count > 0U
			                       ? "selected_phi_incoming_value_store_site_immediate_expected_valid_missing_no_actual_valid_authority"
			                       : "selected_phi_incoming_value_store_site_immediate_expected_valid_not_measured",
			             selector_actual_valid_materialized_slot_count,
		             selector_guarded_actual_valid_candidate_count,
		             selector_actual_valid_gate_blocking);
	    }
    printf("partition_local_eval_continuation_guard_cpu_oracle_validation: requested=true executed=%s guarded_region_execution_count=%llu cfg_clone_liveout_compare_count=%llu cfg_clone_liveout_mismatch_count=%llu inactive_successor_phi_liveout_select_level_dispatch_count=%llu authority=false blocking=%s kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_gpu\n",
           partition_guard_execution_count > 0ULL ? "true" : "false",
           partition_guard_execution_count,
           liveout_compare_count,
           liveout_mismatch_count,
           inactive_successor_phi_liveout_select_level_dispatch_count,
           partition_guard_execution_count > 0ULL
               ? "runtime_noop_or_skip_authority_missing"
               : liveout_counter_authority
                     ? "guard_runtime_counter_zero_after_cfg_clone_liveout_compare_observed"
                     : "cfg_clone_liveout_compare_not_authoritative_for_guard_runtime");
    free(all_cfg_clone_runtime_counters);
  }
  if (ordering_aware_region_timing_requested) {
    unsigned long long region_cycles[ORDERING_AWARE_REGION_TIMING_COUNTERS] = {0};
    if (d_ordering_aware_region_cycles) {
      CUDA_CHECK(cuMemcpyDtoH(region_cycles, d_ordering_aware_region_cycles,
                              sizeof(region_cycles)));
    }
    printf("ordering_aware_region_cycles: requested=true available=%s terminal_mask=%llu phase_set=%llu cycle_body=%llu feedback=%llu low_patch=%llu low_eval=%llu high_patch=%llu high_eval=%llu memory_cluster=%llu select_mux_cluster=%llu branch_control_cluster=%llu active_eval_basic_blocks=%llu active_memory_candidate_blocks=%llu active_select_candidate_blocks=%llu select_mux_scoped_cycles=%llu select_mux_scoped_blocks=%llu source=diagnostic_gid0_clock64 kernel=vl_tb_core_ordering_aware_phase_resident_token_loop_region_timing_gpu\n",
           ordering_aware_region_timing_available ? "true" : "false",
           region_cycles[0], region_cycles[1], region_cycles[2],
           region_cycles[3], region_cycles[4], region_cycles[5],
           region_cycles[6], region_cycles[7], region_cycles[8],
           region_cycles[9], region_cycles[10], region_cycles[11],
           region_cycles[12], region_cycles[13], region_cycles[14],
           region_cycles[15]);
  }
  if (step_trace.fp) {
    printf("step_trace_copy_mode: %s\n",
           step_trace.device_buffered
               ? (step_trace.d_coalesced_rows
                      ? "device_buffered_coalesced_d2d_trace"
                      : "device_buffered_d2d_trace")
               : (step_trace.coalesced_buf ? "host_coalesced_dtoh_trace"
                                            : "host_field_dtoh_trace"));
    if (step_trace.trace_start != 0U || step_trace.trace_stride != 1U) {
      printf("step_trace_filter: start=%u stride=%u rows=%u capacity=%u\n",
             step_trace.trace_start, step_trace.trace_stride,
             step_trace.row_count, step_trace.row_capacity);
    }
  }
  if (sync_each_step) {
    printf("gpu_kernel_time_ms: total=%.6f  per_launch=%.6f  (per-step CUDA "
           "events; kernels only)\n",
           gpu_kernel_ms_sum, ms_per_launch);
  } else if (steps <= 1U) {
    printf("gpu_kernel_time_ms: total=%.6f  per_launch=%.6f  (CUDA events, "
           "kernels only; HtoD patches before launch excluded)\n",
           gpu_kernel_ms_sum, ms_per_launch);
  } else if (resident_steps) {
    printf("gpu_kernel_time_ms: total=%.6f  per_launch=%.6f  (CUDA events, "
           "resident repeated-step mode: one HtoD init before launches, no "
           "per-step host patches, final DtoH only if requested)\n",
           gpu_kernel_ms_sum, ms_per_launch);
  } else {
    printf("gpu_kernel_time_ms: total=%.6f  per_launch=%.6f  (CUDA events, "
           "default stream: first kernel → last kernel; includes HtoD "
           "between steps)\n",
           gpu_kernel_ms_sum, ms_per_launch);
  }
  printf("gpu_kernel_time: per_state=%.3f us  (per_launch / nstates)\n",
         us_per_state);
  printf("gpu_kernel_launches: logical=%u actual=%u timing_repeats=%u "
         "ms_per_actual_launch=%.6f\n",
         timing_launch_count, actual_timed_launch_count, timing_repeats,
         ms_per_actual_launch);
  if (timing_repeats > 1U) {
    printf("gpu_kernel_time_repeat_ms: count=%u min=%.6f median=%.6f max=%.6f samples=",
           timing_repeats, timing_repeat_min_ms, gpu_kernel_ms_sum,
           timing_repeat_max_ms);
    for (unsigned i = 0U; i < timing_repeats; i++) {
      if (i > 0U)
        printf(",");
      printf("%.6f", timing_repeat_ms[i]);
    }
    printf("\n");
	  }
	  printf("wall_time_ms: %.3f  (host; one GPU sync unless %s=1)\n", wall_ms,
	         ENV_SYNC_EACH_STEP);
  if (ordering_aware_token_loop_progress_requested) {
    stop_ordering_aware_token_loop_progress_watchdog(
        &ordering_aware_token_loop_progress_watchdog);
    struct ordering_aware_token_loop_progress_snapshot snapshot;
    read_ordering_aware_token_loop_progress_snapshot(
        h_ordering_aware_token_loop_progress, &snapshot);
    unsigned long long epoch_begin = snapshot.counters[8];
    unsigned long long epoch_end = snapshot.counters[9];
    int epoch_coherent = epoch_begin == epoch_end;
    int stage67_group_complete =
        snapshot.counters[0] != 67ULL || (snapshot.consistent && epoch_coherent);
    char changed_slots[32];
    printf("ordering_aware_token_loop_progress: requested=true stage=%llu cycle=%llu slots=%llu,%llu,%llu,%llu,%llu,%llu epoch_begin=%llu epoch_end=%llu epoch_coherent=%s stage67_group_complete=%s snapshot_read_passes=2 host_snapshot_consistent=%s snapshot_consistent=%s snapshot_changed_mask=%llu snapshot_changed_slots=%s stage67_group_complete_evidence=%s stage67_group_state=%s stage67_epoch_begin_record=%u stage67_epoch_end_record=%u stage67_epoch_begin_high_patch_idx=%u stage67_epoch_end_high_patch_idx=%u\n",
           snapshot.counters[0], snapshot.counters[1], snapshot.counters[2],
           snapshot.counters[3], snapshot.counters[4], snapshot.counters[5],
           snapshot.counters[6], snapshot.counters[7], epoch_begin, epoch_end,
           epoch_coherent ? "true" : "false",
           stage67_group_complete ? "true" : "false",
           snapshot.consistent ? "true" : "false",
           snapshot.consistent ? "true" : "false", snapshot.changed_mask,
           ordering_aware_progress_changed_slots(snapshot.changed_mask,
                                                changed_slots,
                                                sizeof(changed_slots)),
           ordering_aware_stage67_group_complete_evidence(
               snapshot.counters[0], snapshot.consistent),
           ordering_aware_stage67_group_state(snapshot.counters[0],
                                              snapshot.consistent, epoch_begin,
                                              epoch_end),
           ordering_aware_progress_marker_record(epoch_begin),
           ordering_aware_progress_marker_record(epoch_end),
           ordering_aware_progress_marker_high_patch_idx(epoch_begin),
           ordering_aware_progress_marker_high_patch_idx(epoch_end));
  }
	  trace_stage("after_launch_loop");

  free(timing_repeat_launches);

  const char *dump_path = getenv(ENV_DUMP_STATE);
  if (dump_path && dump_path[0] != '\0') {
    trace_stage("before_dump_state");
    if (dump_device_storage(d_storage, total, dump_path) != 0) {
      close_step_trace(&step_trace);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&state_local_patch_schedule);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
      return 1;
    }
    printf("state_dump: %s (%zu bytes)\n", dump_path, total);
    trace_stage("after_dump_state");
  }

  {
    const char *dump_globals = getenv(ENV_DUMP_GLOBALS);
    if (dump_globals && dump_globals[0] != '\0') {
      trace_stage("before_dump_globals");
      if (dump_device_global_specs(mods, nmods, dump_globals) != 0) {
        close_step_trace(&step_trace);
        free_step_patch_blocks(script_blocks, script_block_count);
        free_resident_patch_schedule(&state_local_patch_schedule);
        free_resident_patch_schedule(&resident_patch_schedule);
        free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
        return 1;
      }
      trace_stage("after_dump_globals");
    }
  }

  trace_stage("before_cleanup");
  print_stage_timings();
  close_step_trace(&step_trace);
  free(timing_repeat_ms);
  free_feedback_edge_table(&feedback_edges);
  free_feedback_increment_table(&feedback_increments);
  free_feedback_set_table(&feedback_phase_sets);
  free_ordering_aware_terminal_mask_table(&ordering_aware_terminal_masks);
  free_eval_partition_predicate_table(&eval_partition_predicates);
  free_resident_patch_schedule(&state_local_patch_schedule);
	  free_resident_patch_schedule(&resident_patch_schedule);
	  free_string_list(persistent_phase_dumps, persistent_phase_dump_count);
  if (h_ordering_aware_token_loop_progress)
    CUDA_CHECK(cuMemFreeHost(h_ordering_aware_token_loop_progress));
	  if (d_ordering_aware_region_cycles)
	    CUDA_CHECK(cuMemFree(d_ordering_aware_region_cycles));
  if (d_cfg_clone_shadow_payload)
    CUDA_CHECK(cuMemFree(d_cfg_clone_shadow_payload));
  if (d_cfg_clone_shadow_descriptor_records)
    CUDA_CHECK(cuMemFree(d_cfg_clone_shadow_descriptor_records));
  if (d_single_entry_cfg_clone_liveout_counters)
    CUDA_CHECK(cuMemFree(d_single_entry_cfg_clone_liveout_counters));
  if (d_initial_snapshot)
    CUDA_CHECK(cuMemFree(d_initial_snapshot));
  CUDA_CHECK(cuMemFree(d_storage));
  CUDA_CHECK(cuCtxDestroy(ctx));
  free_step_patch_blocks(script_blocks, script_block_count);
  trace_stage("after_cleanup");
  return 0;
}
