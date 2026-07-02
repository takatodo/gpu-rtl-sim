#include "Vsim.h"
#include "verilated.h"

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <vector>

struct MicrogptAttentionHeadIn {
  uint8_t x[20];
};

struct MicrogptAttentionHeadOut {
  uint64_t y[4];
};

typedef int (*run_hybrid_json_fn)(
    int nstates,
    int repeat,
    int inner_repeat,
    int integration_batches,
    char *out_json,
    size_t out_json_size);

typedef int (*run_gpu_outputs_fn)(
    int nstates,
    int inner_repeat,
    MicrogptAttentionHeadOut *out,
    size_t out_count);

static double bridge_ms_since(struct timespec start) {
  struct timespec now;
  clock_gettime(CLOCK_MONOTONIC, &now);
  return (double)(now.tv_sec - start.tv_sec) * 1000.0 +
         (double)(now.tv_nsec - start.tv_nsec) / 1000000.0;
}

static const char *json_value_start(const char *json, const char *key) {
  char pattern[96];
  int written = snprintf(pattern, sizeof(pattern), "\"%s\":", key);
  if (written <= 0 || (size_t)written >= sizeof(pattern)) return NULL;
  const char *found = strstr(json, pattern);
  return found ? found + written : NULL;
}

static int json_string(const char *json, const char *key, char *out, size_t out_size) {
  const char *value = json_value_start(json, key);
  if (!value || *value != '"' || out_size == 0) return 0;
  ++value;
  const char *end = strchr(value, '"');
  if (!end) return 0;
  size_t len = (size_t)(end - value);
  if (len >= out_size) len = out_size - 1;
  memcpy(out, value, len);
  out[len] = '\0';
  return 1;
}

static int json_ull(const char *json, const char *key, unsigned long long *out) {
  const char *value = json_value_start(json, key);
  char *end = NULL;
  if (!value) return 0;
  *out = strtoull(value, &end, 10);
  return end != value;
}

static int json_double(const char *json, const char *key, double *out) {
  const char *value = json_value_start(json, key);
  char *end = NULL;
  if (!value) return 0;
  *out = strtod(value, &end);
  return end != value;
}

static void fill(std::vector<MicrogptAttentionHeadIn> &input) {
  for (size_t i = 0; i < input.size(); ++i) {
    for (int j = 0; j < 20; ++j) {
      input[i].x[j] = uint8_t((i * 17u + j * 11u + 1u) & 0x7fu);
    }
  }
}

static MicrogptAttentionHeadOut verilator_eval_fused(
    Vsim &top,
    const MicrogptAttentionHeadIn &in,
    int inner_repeat) {
  top.q0 = in.x[0];
  top.q1 = in.x[1];
  top.q2 = in.x[2];
  top.q3 = in.x[3];
  top.k00 = in.x[4];
  top.k01 = in.x[5];
  top.k02 = in.x[6];
  top.k03 = in.x[7];
  top.k10 = in.x[8];
  top.k11 = in.x[9];
  top.k12 = in.x[10];
  top.k13 = in.x[11];
  top.v00 = in.x[12];
  top.v01 = in.x[13];
  top.v02 = in.x[14];
  top.v03 = in.x[15];
  top.v10 = in.x[16];
  top.v11 = in.x[17];
  top.v12 = in.x[18];
  top.v13 = in.x[19];
  top.eval();

  MicrogptAttentionHeadOut out{{0, 0, 0, 0}};
  uint64_t base[4] = {top.y0, top.y1, top.y2, top.y3};
  for (int r = 0; r < inner_repeat; ++r) {
    for (int j = 0; j < 4; ++j) {
      out.y[j] = (out.y[j] + base[j]) ^ uint64_t((r + j) & 31);
    }
  }
  return out;
}

static void print_status(const char *status) {
  printf("{\"status\":\"%s\"}\n", status);
}

int main(int argc, char **argv) {
  if (argc != 6) {
    print_status("failed_usage");
    return 2;
  }

  int nstates = atoi(argv[2]);
  int repeat = atoi(argv[3]);
  int inner_repeat = atoi(argv[4]);
  int integration_batches = atoi(argv[5]);
  if (nstates <= 0 || repeat <= 0 || inner_repeat <= 0 || integration_batches <= 0) {
    print_status("failed_invalid_dimensions");
    return 2;
  }

  void *handle = dlopen(argv[1], RTLD_NOW);
  if (!handle) {
    print_status("failed_dlopen_adapter_library");
    return 1;
  }
  run_hybrid_json_fn run_hybrid = (run_hybrid_json_fn)dlsym(
      handle, "microgpt_attention_head_handoff_adapter_run_hybrid_json");
  run_gpu_outputs_fn run_gpu_outputs = (run_gpu_outputs_fn)dlsym(
      handle, "microgpt_attention_head_handoff_adapter_run_gpu_outputs");
  if (!run_hybrid || !run_gpu_outputs) {
    dlclose(handle);
    print_status("failed_missing_adapter_symbol");
    return 1;
  }

  std::vector<MicrogptAttentionHeadIn> input(nstates);
  std::vector<MicrogptAttentionHeadOut> cpu(nstates);
  std::vector<MicrogptAttentionHeadOut> gpu(nstates);
  fill(input);

  VerilatedContext context;
  Vsim top(&context);
  uint64_t cpu_control_checksum = 0;
  double cpu_ms = 0.0;
  for (int r = 0; r < repeat; ++r) {
    struct timespec cpu_start;
    clock_gettime(CLOCK_MONOTONIC, &cpu_start);
    for (int b = 0; b < integration_batches; ++b) {
      for (int i = 0; i < nstates; ++i) {
        cpu[i] = verilator_eval_fused(top, input[i], inner_repeat);
      }
      cpu_control_checksum ^= cpu[(b + r) % nstates].y[(b + r) & 3] + uint64_t(b + r);
    }
    cpu_ms += bridge_ms_since(cpu_start);
  }
  const double measured_batches = (double)repeat * (double)integration_batches;
  cpu_ms /= measured_batches;

  int gpu_outputs_rc = run_gpu_outputs(nstates, inner_repeat, gpu.data(), gpu.size());
  if (gpu_outputs_rc != 0) {
    dlclose(handle);
    print_status("failed_gpu_output_call");
    return 1;
  }

  size_t mismatch_count = 0;
  for (int i = 0; i < nstates; ++i) {
    for (int j = 0; j < 4; ++j) {
      if (cpu[i].y[j] != gpu[i].y[j]) ++mismatch_count;
    }
  }

  char hybrid_json[8192];
  struct timespec hybrid_start;
  clock_gettime(CLOCK_MONOTONIC, &hybrid_start);
  int hybrid_rc = run_hybrid(
      nstates, repeat, inner_repeat, integration_batches,
      hybrid_json, sizeof(hybrid_json));
  double bridge_hybrid_wall_ms = bridge_ms_since(hybrid_start);
  dlclose(handle);
  if (hybrid_rc != 0) {
    print_status("failed_hybrid_adapter_call");
    return 1;
  }

  char hybrid_status[96] = {0};
  unsigned long long timed_gpu_checksum = 0;
  double gpu_end_to_end_ms = 0.0;
  double gpu_kernel_ms = 0.0;
  int parsed =
      json_string(hybrid_json, "status", hybrid_status, sizeof(hybrid_status)) &&
      json_ull(hybrid_json, "gpu_control_checksum", &timed_gpu_checksum) &&
      json_double(hybrid_json, "gpu_end_to_end_ms", &gpu_end_to_end_ms) &&
      json_double(hybrid_json, "gpu_kernel_ms", &gpu_kernel_ms);
  if (!parsed) {
    print_status("failed_parse_hybrid_json");
    return 1;
  }

  int checksum_equal = cpu_control_checksum == (uint64_t)timed_gpu_checksum;
  int passed =
      strcmp(hybrid_status, "hybrid_entrypoint_passed") == 0 &&
      mismatch_count == 0 &&
      checksum_equal;
  const double bridge_wall_per_batch =
      measured_batches > 0.0 ? bridge_hybrid_wall_ms / measured_batches : 0.0;
  const double cpu_to_bridge_wall_speedup =
      bridge_wall_per_batch > 0.0 ? cpu_ms / bridge_wall_per_batch : 0.0;
  const double cpu_to_gpu_end_to_end_speedup =
      gpu_end_to_end_ms > 0.0 ? cpu_ms / gpu_end_to_end_ms : 0.0;
  const double cpu_to_gpu_kernel_speedup =
      gpu_kernel_ms > 0.0 ? cpu_ms / gpu_kernel_ms : 0.0;

  printf(
      "{\"status\":\"%s\",\"nstates\":%d,\"repeat\":%d,\"inner_repeat\":%d,"
      "\"integration_batches\":%d,\"verilator_callsite_used\":true,"
      "\"hybrid_status\":\"%s\",\"mismatch_count\":%zu,"
      "\"verilator_control_checksum\":%llu,\"timed_gpu_control_checksum\":%llu,"
      "\"cpu_vs_gpu_output_equal\":%s,"
      "\"cpu_vs_gpu_control_checksum_equal\":%s,"
      "\"cpu_ms\":%.17g,\"gpu_end_to_end_ms\":%.17g,"
      "\"gpu_kernel_ms\":%.17g,\"bridge_hybrid_wall_ms\":%.17g,"
      "\"bridge_hybrid_wall_ms_per_integration_batch\":%.17g,"
      "\"cpu_to_bridge_hybrid_wall_speedup\":%.17g,"
      "\"cpu_to_gpu_end_to_end_speedup\":%.17g,"
      "\"cpu_to_gpu_kernel_speedup\":%.17g}\n",
      passed ? "direct_verilator_callsite_entrypoint_passed" :
               "direct_verilator_callsite_entrypoint_failed",
      nstates,
      repeat,
      inner_repeat,
      integration_batches,
      hybrid_status,
      mismatch_count,
      static_cast<unsigned long long>(cpu_control_checksum),
      timed_gpu_checksum,
      mismatch_count == 0 ? "true" : "false",
      checksum_equal ? "true" : "false",
      cpu_ms,
      gpu_end_to_end_ms,
      gpu_kernel_ms,
      bridge_hybrid_wall_ms,
      bridge_wall_per_batch,
      cpu_to_bridge_wall_speedup,
      cpu_to_gpu_end_to_end_speedup,
      cpu_to_gpu_kernel_speedup);
  top.final();
  return passed ? 0 : 1;
}
