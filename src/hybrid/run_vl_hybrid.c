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
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Comma-separated kernel names; Verilator phase order (see vl_batch_gpu.meta.json launch_sequence). */
#define ENV_KERNEL_CHAIN "RUN_VL_HYBRID_KERNELS"
/* Caliptra act-sequent probes can need ico + chunk4 act kernels + nba kernels. */
#define MAX_KERNEL_CHAIN 64
/* Comma-separated cubin paths; used for split entries packaged as independent cubins. */
#define ENV_CUBIN_CHAIN "RUN_VL_HYBRID_CUBINS"
#define MAX_CUBIN_CHAIN 64

/* Optional binary dump of device storage after the last launch sequence. */
#define ENV_DUMP_STATE "RUN_VL_HYBRID_DUMP_STATE"
/* Optional comma-separated symbol:path dump list for device-global probe buffers. */
#define ENV_DUMP_GLOBALS "RUN_VL_HYBRID_DUMP_GLOBALS"
/* Optional raw state image copied into device storage before patches/launches. */
#define ENV_INIT_STATE "RUN_VL_HYBRID_INIT_STATE"
/* Optional device-side replication for a single-state init image. */
#define ENV_GPU_REPLICATE_INIT_STATE "RUN_VL_HYBRID_GPU_REPLICATE_INIT_STATE"
/* Optional per-step patch script file; each non-comment line is one step of patch tokens. */
#define ENV_PATCH_SCRIPT "RUN_VL_HYBRID_PATCH_SCRIPT"
/* Optional source-backed program-image initialization records. */
#define ENV_PROGRAM_IMAGE_INIT_RECORDS "RUN_VL_HYBRID_PROGRAM_IMAGE_INIT_RECORDS"
/* Explicit resident repeated-step mode; keeps state on device across eval steps. */
#define ENV_RESIDENT_STEPS "RUN_VL_HYBRID_RESIDENT_STEPS"

/* Set to force one cuCtxSynchronize per step (slower wall clock; old behavior). */
#define ENV_SYNC_EACH_STEP "RUN_VL_HYBRID_SYNC_EACH_STEP"
/* Optional untimed launch after init to absorb first-launch / driver latency. */
#define ENV_WARMUP "RUN_VL_HYBRID_WARMUP"
/* Optional stage trace to help localize runtime kills / hangs. */
#define ENV_TRACE_STAGES "RUN_VL_HYBRID_TRACE_STAGES"
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

#define MAX_PATCHES 64
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
  size_t *offsets;
  unsigned char *values;
  unsigned record_count;
  CUdeviceptr d_offsets;
  CUdeviceptr d_values;
} ProgramImageInitRecords;

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

static void free_program_image_init_records(ProgramImageInitRecords *records) {
  if (!records)
    return;
  if (records->d_offsets)
    CUDA_CHECK(cuMemFree(records->d_offsets));
  if (records->d_values)
    CUDA_CHECK(cuMemFree(records->d_values));
  free(records->offsets);
  free(records->values);
  memset(records, 0, sizeof(*records));
}

static int append_program_image_init_record(ProgramImageInitRecords *records,
                                            unsigned *capacity, size_t storage,
                                            const Patch *patch) {
  if (patch->global_off >= storage) {
    fprintf(stderr, "program image init offset %zu >= storage_size %zu\n",
            patch->global_off, storage);
    return -1;
  }
  for (unsigned i = 0; i < records->record_count; i++) {
    if (records->offsets[i] == patch->global_off) {
      fprintf(stderr, "duplicate program image init offset %zu\n",
              patch->global_off);
      return -1;
    }
  }
  if (records->record_count == *capacity) {
    unsigned new_capacity = *capacity ? (*capacity * 2U) : 256U;
    size_t *grown_offsets =
        (size_t *)realloc(records->offsets, new_capacity * sizeof(*records->offsets));
    if (!grown_offsets)
      return -1;
    records->offsets = grown_offsets;
    unsigned char *grown_values = (unsigned char *)realloc(
        records->values, new_capacity * sizeof(*records->values));
    if (!grown_values)
      return -1;
    records->values = grown_values;
    *capacity = new_capacity;
  }
  records->offsets[records->record_count] = patch->global_off;
  records->values[records->record_count] = patch->val;
  records->record_count++;
  return 0;
}

static int load_program_image_init_records(const char *path, size_t storage,
                                           ProgramImageInitRecords *out) {
  FILE *fp = fopen(path, "r");
  char line[4096];
  unsigned capacity = 0U;
  unsigned line_no = 0U;
  memset(out, 0, sizeof(*out));
  if (!fp) {
    fprintf(stderr, "failed to open %s=%s\n", ENV_PROGRAM_IMAGE_INIT_RECORDS, path);
    return -1;
  }
  while (fgets(line, sizeof(line), fp) != NULL) {
    char *cursor = line;
    char *comment = NULL;
    char *token = NULL;
    line_no++;
    if (strchr(line, '\n') == NULL && !feof(fp)) {
      fprintf(stderr, "%s line %u exceeds internal parser buffer\n", path, line_no);
      fclose(fp);
      free_program_image_init_records(out);
      return -1;
    }
    while (*cursor != '\0' && isspace((unsigned char)*cursor))
      cursor++;
    if (*cursor == '\0' || *cursor == '\n' || *cursor == '#')
      continue;
    comment = strchr(cursor, '#');
    if (comment)
      *comment = '\0';
    for (token = strtok(cursor, " \t\r\n"); token != NULL;
         token = strtok(NULL, " \t\r\n")) {
      Patch patch;
      if (parse_patch(token, &patch) != 0) {
        fprintf(stderr,
                "%s line %u has bad program-image init token '%s' (want target_root_offset:byte)\n",
                path, line_no, token);
        fclose(fp);
        free_program_image_init_records(out);
        return -1;
      }
      if (append_program_image_init_record(out, &capacity, storage, &patch) != 0) {
        fclose(fp);
        free_program_image_init_records(out);
        return -1;
      }
    }
  }
  if (ferror(fp)) {
    fprintf(stderr, "failed while reading %s\n", path);
    fclose(fp);
    free_program_image_init_records(out);
    return -1;
  }
  fclose(fp);
  if (out->record_count == 0U) {
    fprintf(stderr, "%s contained no program-image initialization records\n", path);
    free_program_image_init_records(out);
    return -1;
  }
  return 0;
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

static int load_patch_script(const char *path, StepPatchBlock **out_blocks,
                             unsigned *out_block_count,
                             unsigned *out_logical_step_count,
                             unsigned *out_record_count) {
  FILE *fp = fopen(path, "r");
  char line[4096];
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
        if (parse_patch(token, &parsed[parsed_count]) != 0) {
          fprintf(stderr,
                  "%s line %u has bad patch token '%s' (want global_offset:byte)\n",
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

static void trace_stage(const char *stage) {
  if (!trace_stages_enabled())
    return;
  fprintf(stderr, "run_vl_hybrid: stage=%s\n", stage);
  fflush(stderr);
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

static int launch_program_image_init(CUfunction init_kfn,
                                     CUdeviceptr d_storage,
                                     const ProgramImageInitRecords *records,
                                     size_t storage,
                                     unsigned nstates) {
  if (!records || records->record_count == 0U)
    return 0;
  if (records->record_count > 2147483647U || nstates > 2147483647U) {
    fprintf(stderr, "program-image init launch shape out of range: records=%u nstates=%u\n",
            records->record_count, nstates);
    return -1;
  }
  unsigned long long total_work =
      (unsigned long long)records->record_count * (unsigned long long)nstates;
  unsigned block = 256U;
  unsigned long long grid_ull =
      (total_work + (unsigned long long)block - 1ULL) / (unsigned long long)block;
  if (grid_ull == 0ULL || grid_ull > 2147483647ULL) {
    fprintf(stderr, "program-image init grid out of range: %llu\n", grid_ull);
    return -1;
  }
  unsigned grid = (unsigned)grid_ull;
  CUdeviceptr d_offsets = records->d_offsets;
  CUdeviceptr d_values = records->d_values;
  int record_count_i = (int)records->record_count;
  unsigned long long storage_arg = (unsigned long long)storage;
  int nstates_i = (int)nstates;
  void *params[] = {&d_storage,
                    &d_offsets,
                    &d_values,
                    &record_count_i,
                    &storage_arg,
                    &nstates_i};
  trace_kernel_launch("vl_apply_program_image_init_gpu", 0, -1);
  CUDA_CHECK(cuLaunchKernel(init_kfn, grid, 1, 1, block, 1, 1, 0, 0, params, NULL));
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
  memset(&resident_patch_schedule, 0, sizeof(resident_patch_schedule));
  ProgramImageInitRecords program_image_init_records;
  memset(&program_image_init_records, 0, sizeof(program_image_init_records));
  CUfunction resident_patch_kfn = NULL;
  CUfunction init_replication_kfn = NULL;
  CUfunction program_image_init_kfn = NULL;

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
    if (parse_patch(argv[pi], &patches[npatch]) != 0) {
      fprintf(stderr, "bad patch '%s' (want global_offset:byte)\n", argv[pi]);
      return 1;
    }
    npatch++;
  }

  const int resident_steps = getenv(ENV_RESIDENT_STEPS) != NULL;
  const int gpu_replicate_init_state = getenv(ENV_GPU_REPLICATE_INIT_STATE) != NULL;
  const char *program_image_init_records_path = getenv(ENV_PROGRAM_IMAGE_INIT_RECORDS);
  const int program_image_init_records_enabled =
      program_image_init_records_path != NULL && program_image_init_records_path[0] != '\0';

  {
    const char *patch_script_path = getenv(ENV_PATCH_SCRIPT);
    if (patch_script_path && patch_script_path[0] != '\0') {
      if (load_patch_script(patch_script_path, &script_blocks, &script_block_count,
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

  if (storage_ull == 0ULL || storage_ull > (1ULL << 40)) {
    fprintf(stderr, "invalid storage_bytes\n");
    return 1;
  }
  if (nstates == 0U) {
    fprintf(stderr, "nstates must be >= 1\n");
    return 1;
  }

  size_t storage = (size_t)storage_ull;
  size_t total = storage * (size_t)nstates;
  if (program_image_init_records_enabled) {
    if (load_program_image_init_records(program_image_init_records_path, storage,
                                        &program_image_init_records) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
  }

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
  if (program_image_init_records_enabled) {
    if (resolve_function_across_modules(&program_image_init_kfn, mods, nmods,
                                        "vl_apply_program_image_init_gpu") != 0) {
      fprintf(stderr,
              "%s requires a cubin regenerated with vl_apply_program_image_init_gpu\n",
              ENV_PROGRAM_IMAGE_INIT_RECORDS);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_program_image_init_records(&program_image_init_records);
      return 1;
    }
    trace_function_attrs(program_image_init_kfn, "vl_apply_program_image_init_gpu");
  }
  {
    int stack_limit_status = maybe_raise_stack_limit_for_kernels(kfns, nk);
    if (env_flag_enabled(ENV_STACK_LIMIT_PROBE_ONLY))
      return stack_limit_status;
    if (stack_limit_status != 0) {
      fprintf(stderr, "stack-limit setup failed with status=%d\n", stack_limit_status);
      free_program_image_init_records(&program_image_init_records);
      return stack_limit_status;
    }
  }
  trace_stage("after_kernel_resolution");

  CUdeviceptr d_storage = 0;
  trace_stage("before_cuMemAlloc");
  CUDA_CHECK(cuMemAlloc(&d_storage, total));
  CUDA_CHECK(cuMemsetD8(d_storage, 0, total));
  trace_stage("after_cuMemAlloc");

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

  if (resident_steps && script_blocks) {
    if (build_resident_patch_schedule(script_blocks, script_block_count,
                                      script_logical_step_count, total,
                                      &resident_patch_schedule) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      return 1;
    }
    resident_patch_script_block_count = script_block_count;
    if (resident_patch_schedule.record_count > 0U) {
      CUDA_CHECK(cuMemAlloc(&resident_patch_schedule.d_offsets,
                            (size_t)resident_patch_schedule.record_count *
                                sizeof(*resident_patch_schedule.offsets)));
      CUDA_CHECK(cuMemAlloc(&resident_patch_schedule.d_values,
                            (size_t)resident_patch_schedule.record_count *
                                sizeof(*resident_patch_schedule.values)));
      CUDA_CHECK(cuMemcpyHtoD(resident_patch_schedule.d_offsets,
                              resident_patch_schedule.offsets,
                              (size_t)resident_patch_schedule.record_count *
                                  sizeof(*resident_patch_schedule.offsets)));
      CUDA_CHECK(cuMemcpyHtoD(resident_patch_schedule.d_values,
                              resident_patch_schedule.values,
                              (size_t)resident_patch_schedule.record_count *
                                  sizeof(*resident_patch_schedule.values)));
    }
    free_step_patch_blocks(script_blocks, script_block_count);
    script_blocks = NULL;
    script_block_count = 0U;
  }

  if (program_image_init_records.record_count > 0U) {
    CUDA_CHECK(cuMemAlloc(&program_image_init_records.d_offsets,
                          (size_t)program_image_init_records.record_count *
                              sizeof(*program_image_init_records.offsets)));
    CUDA_CHECK(cuMemAlloc(&program_image_init_records.d_values,
                          (size_t)program_image_init_records.record_count *
                              sizeof(*program_image_init_records.values)));
    CUDA_CHECK(cuMemcpyHtoD(program_image_init_records.d_offsets,
                            program_image_init_records.offsets,
                            (size_t)program_image_init_records.record_count *
                                sizeof(*program_image_init_records.offsets)));
    CUDA_CHECK(cuMemcpyHtoD(program_image_init_records.d_values,
                            program_image_init_records.values,
                            (size_t)program_image_init_records.record_count *
                                sizeof(*program_image_init_records.values)));
    if (launch_program_image_init(program_image_init_kfn, d_storage,
                                  &program_image_init_records, storage, nstates) != 0) {
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_program_image_init_records(&program_image_init_records);
      return 1;
    }
    CUDA_CHECK(cuCtxSynchronize());
  }

  int nstates_i = (int)nstates;
  void *params[] = {&d_storage, &nstates_i};
  unsigned grid = (nstates + block - 1) / block;

  CUevent ev_start, ev_stop;
  CUDA_CHECK(cuEventCreate(&ev_start, CU_EVENT_DEFAULT));
  CUDA_CHECK(cuEventCreate(&ev_stop, CU_EVENT_DEFAULT));

  struct timespec wall0, wall1;
  clock_gettime(CLOCK_MONOTONIC, &wall0);
  trace_stage("before_launch_loop");

  float gpu_kernel_ms_sum = 0.f;
  const int sync_each_step = getenv(ENV_SYNC_EACH_STEP) != NULL;

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
            }
            if (logical_step == 0U)
              trace_stage("after_first_kernel_launch");
            CUDA_CHECK(cuEventRecord(ev_stop, 0));
            if (logical_step == 0U)
              trace_stage("before_first_step_sync");
            CUDA_CHECK(cuCtxSynchronize());
            if (logical_step == 0U)
              trace_stage("after_first_step_sync");
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
        if (launch_resident_patch_step(resident_patch_kfn, &resident_patch_schedule,
                                       d_storage, step) != 0) {
          free_resident_patch_schedule(&resident_patch_schedule);
          return 1;
        }
        if (step == 0U)
          trace_stage("before_first_kernel_launch");
        for (int k = 0; k < nk; k++) {
          trace_kernel_launch(kernel_names[k], step, k);
          CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                    params, NULL));
        }
        if (step == 0U)
          trace_stage("after_first_kernel_launch");
        CUDA_CHECK(cuEventRecord(ev_stop, 0));
        if (step == 0U)
          trace_stage("before_first_step_sync");
        CUDA_CHECK(cuCtxSynchronize());
        if (step == 0U)
          trace_stage("after_first_step_sync");
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
            }
            if (logical_step == 0U)
              trace_stage("after_first_kernel_launch");
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
        if (!recorded_start) {
          CUDA_CHECK(cuEventRecord(ev_start, 0));
          recorded_start = 1;
        }
        if (launch_resident_patch_step(resident_patch_kfn, &resident_patch_schedule,
                                       d_storage, step) != 0) {
          free_resident_patch_schedule(&resident_patch_schedule);
          return 1;
        }
        if (step == 0U)
          trace_stage("before_first_kernel_launch");
        for (int k = 0; k < nk; k++) {
          trace_kernel_launch(kernel_names[k], step, k);
          CUDA_CHECK(cuLaunchKernel(kfns[k], grid, 1, 1, block, 1, 1, 0, 0,
                                    params, NULL));
        }
        if (step == 0U)
          trace_stage("after_first_kernel_launch");
      }
    }
    CUDA_CHECK(cuEventRecord(ev_stop, 0));
    trace_stage("before_final_sync");
    CUDA_CHECK(cuCtxSynchronize());
    trace_stage("after_final_sync");
    CUDA_CHECK(cuEventElapsedTime(&gpu_kernel_ms_sum, ev_start, ev_stop));
  }

  clock_gettime(CLOCK_MONOTONIC, &wall1);
  double wall_ms =
      (wall1.tv_sec - wall0.tv_sec) * 1000.0 +
      (wall1.tv_nsec - wall0.tv_nsec) / 1e6;

  CUDA_CHECK(cuEventDestroy(ev_start));
  CUDA_CHECK(cuEventDestroy(ev_stop));

  double ms_per_launch =
      steps > 0 ? (double)gpu_kernel_ms_sum / (double)steps : 0.0;
  double us_per_state =
      (nstates > 0) ? (ms_per_launch / (double)nstates) * 1000.0 : 0.0;

  printf("ok: steps=%u kernels_per_step=%d patches_per_step=%d grid=%u block=%u "
         "nstates=%u storage=%zu B\n",
         steps, nk, npatch, grid, block, nstates, storage);
  printf("resident_mode: %s\n", resident_steps ? "true" : "false");
  printf("gpu_init_state_replication: %s\n",
         gpu_replicate_init_state ? "true" : "false");
  printf("program_image_init_records: %s\n",
         program_image_init_records_enabled ? program_image_init_records_path : "none");
  if (program_image_init_records.record_count > 0U) {
    printf("program_image_init_record_upload: records=%u layout=offsets_values_soa\n",
           program_image_init_records.record_count);
    printf("program_image_init_launch: kernel=vl_apply_program_image_init_gpu records=%u nstates=%u\n",
           program_image_init_records.record_count, nstates);
  }
  if (script_blocks) {
    printf("patch_script_steps: logical=%u records=%u blocks=%u\n",
           script_logical_step_count, script_record_count, script_block_count);
  } else if (resident_patch_schedule.step_offsets) {
    printf("resident_patch_schedule: logical=%u records=%u blocks=%u\n",
           resident_patch_schedule.logical_steps,
           resident_patch_schedule.record_count, resident_patch_script_block_count);
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
  printf("wall_time_ms: %.3f  (host; one GPU sync unless %s=1)\n", wall_ms,
         ENV_SYNC_EACH_STEP);
  trace_stage("after_launch_loop");

  const char *dump_path = getenv(ENV_DUMP_STATE);
  if (dump_path && dump_path[0] != '\0') {
    trace_stage("before_dump_state");
    unsigned char *host = (unsigned char *)malloc(total);
    if (!host) {
      fprintf(stderr, "malloc failed for %zu-byte state dump\n", total);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_program_image_init_records(&program_image_init_records);
      return 1;
    }
    CUDA_CHECK(cuMemcpyDtoH(host, d_storage, total));
    FILE *fp = fopen(dump_path, "wb");
    if (!fp) {
      fprintf(stderr, "fopen(%s) failed\n", dump_path);
      free(host);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_program_image_init_records(&program_image_init_records);
      return 1;
    }
    size_t nw = fwrite(host, 1, total, fp);
    fclose(fp);
    free(host);
    if (nw != total) {
      fprintf(stderr, "short write to %s: wrote %zu / %zu bytes\n", dump_path,
              nw, total);
      free_step_patch_blocks(script_blocks, script_block_count);
      free_resident_patch_schedule(&resident_patch_schedule);
      free_program_image_init_records(&program_image_init_records);
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
        free_step_patch_blocks(script_blocks, script_block_count);
        free_resident_patch_schedule(&resident_patch_schedule);
        return 1;
      }
      trace_stage("after_dump_globals");
    }
  }

  trace_stage("before_cleanup");
  free_resident_patch_schedule(&resident_patch_schedule);
  free_program_image_init_records(&program_image_init_records);
  CUDA_CHECK(cuMemFree(d_storage));
  CUDA_CHECK(cuCtxDestroy(ctx));
  free_step_patch_blocks(script_blocks, script_block_count);
  trace_stage("after_cleanup");
  return 0;
}
