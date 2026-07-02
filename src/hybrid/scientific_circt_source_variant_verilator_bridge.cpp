#include "Vsim.h"
#include "verilated.h"

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <vector>

#ifndef SCI_CIRCT_BRIDGE_EXPECTED_CANDIDATE
#define SCI_CIRCT_BRIDGE_EXPECTED_CANDIDATE "metadata_gate_header_missing"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_SOURCE_VARIANT
#define SCI_CIRCT_BRIDGE_EXPECTED_SOURCE_VARIANT "metadata_gate_header_missing"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_SHAPE
#define SCI_CIRCT_BRIDGE_EXPECTED_SHAPE "metadata_gate_header_missing"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_RUN_GPU_OUTPUTS
#define SCI_CIRCT_BRIDGE_EXPECTED_RUN_GPU_OUTPUTS "metadata_gate_header_missing"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_RUN_HYBRID_JSON
#define SCI_CIRCT_BRIDGE_EXPECTED_RUN_HYBRID_JSON "metadata_gate_header_missing"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_TYPE
#define SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_TYPE "metadata_gate_header_missing"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_COUNT
#define SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_COUNT "0"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_TYPE
#define SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_TYPE "metadata_gate_header_missing"
#endif
#ifndef SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_COUNT
#define SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_COUNT "0"
#endif
#ifndef SCI_CIRCT_BRIDGE_INPUT_ELEMENT_TYPE
#define SCI_CIRCT_BRIDGE_INPUT_ELEMENT_TYPE uint8_t
#endif
#ifndef SCI_CIRCT_BRIDGE_INPUT_ELEMENT_COUNT
#define SCI_CIRCT_BRIDGE_INPUT_ELEMENT_COUNT 1
#endif
#ifndef SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_TYPE
#define SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_TYPE uint64_t
#endif
#ifndef SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_COUNT
#define SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_COUNT 1
#endif
#ifndef SCI_CIRCT_BRIDGE_APPLY_INPUTS
#define SCI_CIRCT_BRIDGE_APPLY_INPUTS(top, in) ((void)(top), (void)(in))
#endif
#ifndef SCI_CIRCT_BRIDGE_READ_OUTPUTS
#define SCI_CIRCT_BRIDGE_READ_OUTPUTS(top, base) ((void)(top), (void)(base))
#endif

struct BridgeIn {
  SCI_CIRCT_BRIDGE_INPUT_ELEMENT_TYPE x[SCI_CIRCT_BRIDGE_INPUT_ELEMENT_COUNT];
};

struct BridgeOut {
  SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_TYPE y[SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_COUNT];
};

typedef int (*run_outputs_fn)(int, int, BridgeOut *, size_t);
typedef int (*run_json_fn)(int, int, int, int, char *, size_t);

static double ms_since(struct timespec start) {
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

static void fill(std::vector<BridgeIn> &input) {
  // The GPU .so fills its own input batch with the same generated formula;
  // the two sides must agree element-for-element for the compare to hold.
  for (size_t i = 0; i < input.size(); ++i) {
    for (int j = 0; j < SCI_CIRCT_BRIDGE_INPUT_ELEMENT_COUNT; ++j) {
      input[i].x[j] = SCI_CIRCT_BRIDGE_FILL_VALUE(i, j);
    }
  }
}

static BridgeOut verilator_eval_fused(Vsim &top, const BridgeIn &in, int inner_repeat) {
  SCI_CIRCT_BRIDGE_APPLY_INPUTS(top, in);
  top.eval();

  BridgeOut base{{0}}, out{{0}};
  SCI_CIRCT_BRIDGE_READ_OUTPUTS(top, base);
  for (int r = 0; r < inner_repeat; ++r) {
    for (int j = 0; j < SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_COUNT; ++j) {
      out.y[j] = (out.y[j] + base.y[j]) ^ SCI_CIRCT_BRIDGE_MIX_VALUE(r, j);
    }
  }
  return out;
}

static void print_status(const char *status) {
  printf("{\"status\":\"%s\"}\n", status);
}

static int str_eq(const char *lhs, const char *rhs) {
  return lhs && rhs && strcmp(lhs, rhs) == 0;
}

int main(int argc, char **argv) {
  if (argc != 15) {
    print_status("failed_usage");
    return 2;
  }

  if (!str_eq(argv[2], SCI_CIRCT_BRIDGE_EXPECTED_CANDIDATE) ||
      !str_eq(argv[3], SCI_CIRCT_BRIDGE_EXPECTED_SOURCE_VARIANT) ||
      !str_eq(argv[4], SCI_CIRCT_BRIDGE_EXPECTED_SHAPE) ||
      !str_eq(argv[5], SCI_CIRCT_BRIDGE_EXPECTED_RUN_GPU_OUTPUTS) ||
      !str_eq(argv[6], SCI_CIRCT_BRIDGE_EXPECTED_RUN_HYBRID_JSON) ||
      !str_eq(argv[7], SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_TYPE) ||
      !str_eq(argv[8], SCI_CIRCT_BRIDGE_EXPECTED_INPUT_ELEMENT_COUNT) ||
      !str_eq(argv[9], SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_TYPE) ||
      !str_eq(argv[10], SCI_CIRCT_BRIDGE_EXPECTED_OUTPUT_ELEMENT_COUNT)) {
    print_status("failed_metadata_gate");
    return 2;
  }

  int nstates = atoi(argv[11]);
  int repeat = atoi(argv[12]);
  int inner_repeat = atoi(argv[13]);
  int integration_batches = atoi(argv[14]);
  if (nstates <= 0 || repeat <= 0 || inner_repeat <= 0 || integration_batches <= 0) {
    print_status("failed_invalid_dimensions");
    return 2;
  }

  void *handle = dlopen(argv[1], RTLD_NOW);
  if (!handle) {
    print_status("failed_dlopen");
    return 1;
  }
  run_outputs_fn run_outputs =
      (run_outputs_fn)dlsym(handle, argv[5]);
  run_json_fn run_json =
      (run_json_fn)dlsym(handle, argv[6]);
  if (!run_outputs || !run_json) {
    dlclose(handle);
    print_status("failed_dlsym");
    return 1;
  }

  std::vector<BridgeIn> input(nstates);
  std::vector<BridgeOut> cpu(nstates), gpu(nstates);
  fill(input);

  VerilatedContext context;
  Vsim top(&context);
  double cpu_ms = 0.0;
  uint64_t cpu_checksum = 0;
  for (int r = 0; r < repeat; ++r) {
    struct timespec cpu_start;
    clock_gettime(CLOCK_MONOTONIC, &cpu_start);
    for (int b = 0; b < integration_batches; ++b) {
      for (int i = 0; i < nstates; ++i) {
        cpu[i] = verilator_eval_fused(top, input[i], inner_repeat);
      }
      cpu_checksum ^= cpu[(b + r) % nstates].y[(b + r) % SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_COUNT] + uint64_t(b + r);
    }
    cpu_ms += ms_since(cpu_start);
  }
  const double batches = (double)repeat * (double)integration_batches;
  cpu_ms /= batches;

  int out_rc = run_outputs(nstates, inner_repeat, gpu.data(), gpu.size());
  if (out_rc != 0) {
    dlclose(handle);
    print_status("failed_gpu_outputs");
    return 1;
  }
  size_t mismatch_count = 0;
  for (int i = 0; i < nstates; ++i) {
    for (int j = 0; j < SCI_CIRCT_BRIDGE_OUTPUT_ELEMENT_COUNT; ++j) {
      if (cpu[i].y[j] != gpu[i].y[j]) ++mismatch_count;
    }
  }

  char hybrid_json[4096];
  struct timespec hybrid_start;
  clock_gettime(CLOCK_MONOTONIC, &hybrid_start);
  int json_rc = run_json(nstates, repeat, inner_repeat, integration_batches, hybrid_json, sizeof(hybrid_json));
  double bridge_wall_ms = ms_since(hybrid_start);
  dlclose(handle);
  top.final();
  if (json_rc != 0) {
    print_status("failed_hybrid_json");
    return 1;
  }

  unsigned long long gpu_checksum = 0;
  double gpu_ms = 0.0, kernel_ms = 0.0;
  int parsed = json_ull(hybrid_json, "gpu_control_checksum", &gpu_checksum) &&
               json_double(hybrid_json, "gpu_end_to_end_ms", &gpu_ms) &&
               json_double(hybrid_json, "gpu_kernel_ms", &kernel_ms);
  if (!parsed) {
    print_status("failed_parse_hybrid_json");
    return 1;
  }

  bool pass = mismatch_count == 0 && cpu_checksum == uint64_t(gpu_checksum);
  printf(
      "{\"status\":\"%s\",\"variant\":\"%s\","
      "\"entrypoint\":\"src_hybrid_verilator_callsite\","
      "\"verilator_callsite_used\":true,"
      "\"nstates\":%d,\"repeat\":%d,\"inner_repeat\":%d,"
      "\"integration_batches\":%d,"
      "\"input_bytes\":%zu,\"output_bytes\":%zu,"
      "\"mismatch_count\":%zu,\"cpu_control_checksum\":%llu,"
      "\"gpu_control_checksum\":%llu,\"cpu_vs_gpu_output_equal\":%s,"
      "\"cpu_vs_gpu_control_checksum_equal\":%s,\"cpu_ms\":%.17g,"
      "\"gpu_end_to_end_ms\":%.17g,\"gpu_kernel_ms\":%.17g,"
      "\"bridge_hybrid_wall_ms\":%.17g,"
      "\"bridge_hybrid_wall_ms_per_integration_batch\":%.17g,"
      "\"cpu_to_gpu_end_to_end_speedup\":%.17g,"
      "\"cpu_to_gpu_kernel_speedup\":%.17g,"
      "\"cpu_to_bridge_hybrid_wall_speedup\":%.17g}\n",
      pass ? "src_hybrid_verilator_callsite_passed" : "src_hybrid_verilator_callsite_mismatch",
      SCI_CIRCT_BRIDGE_EXPECTED_SOURCE_VARIANT,
      nstates,
      repeat,
      inner_repeat,
      integration_batches,
      input.size() * sizeof(BridgeIn),
      gpu.size() * sizeof(BridgeOut),
      mismatch_count,
      static_cast<unsigned long long>(cpu_checksum),
      gpu_checksum,
      mismatch_count == 0 ? "true" : "false",
      cpu_checksum == uint64_t(gpu_checksum) ? "true" : "false",
      cpu_ms,
      gpu_ms,
      kernel_ms,
      bridge_wall_ms,
      bridge_wall_ms / batches,
      gpu_ms > 0.0 ? cpu_ms / gpu_ms : 0.0,
      kernel_ms > 0.0 ? cpu_ms / kernel_ms : 0.0,
      (bridge_wall_ms / batches) > 0.0 ? cpu_ms / (bridge_wall_ms / batches) : 0.0);
  return pass ? 0 : 1;
}
