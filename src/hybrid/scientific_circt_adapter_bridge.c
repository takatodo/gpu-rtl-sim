#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef int (*run_json_fn)(
    int nstates,
    int repeat,
    int inner_repeat,
    int integration_batches,
    char *out_json,
    size_t out_json_size);

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

static int json_size(const char *json, const char *key, size_t *out) {
  unsigned long long parsed = 0;
  if (!json_ull(json, key, &parsed)) return 0;
  *out = (size_t)parsed;
  return 1;
}

static int json_double(const char *json, const char *key, double *out) {
  const char *value = json_value_start(json, key);
  char *end = NULL;
  if (!value) return 0;
  *out = strtod(value, &end);
  return end != value;
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

  run_json_fn run_correctness = (run_json_fn)dlsym(
      handle, "microgpt_attention_head_handoff_adapter_run_json");
  run_json_fn run_hybrid = (run_json_fn)dlsym(
      handle, "microgpt_attention_head_handoff_adapter_run_hybrid_json");
  if (!run_correctness || !run_hybrid) {
    dlclose(handle);
    print_status("failed_missing_adapter_symbol");
    return 1;
  }

  char correctness_json[8192];
  char hybrid_json[8192];
  int correctness_rc = run_correctness(
      nstates, repeat, inner_repeat, integration_batches,
      correctness_json, sizeof(correctness_json));
  if (correctness_rc != 0) {
    dlclose(handle);
    print_status("failed_correctness_adapter_call");
    return 1;
  }

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

  char correctness_status[96] = {0};
  char hybrid_status[96] = {0};
  unsigned long long cpu_checksum = 0;
  unsigned long long correctness_gpu_checksum = 0;
  unsigned long long timed_gpu_checksum = 0;
  size_t mismatch_count = 0;
  double cpu_ms = 0.0;
  double gpu_end_to_end_ms = 0.0;
  double gpu_kernel_ms = 0.0;

  int parsed =
      json_string(correctness_json, "status", correctness_status, sizeof(correctness_status)) &&
      json_string(hybrid_json, "status", hybrid_status, sizeof(hybrid_status)) &&
      json_ull(correctness_json, "cpu_control_checksum", &cpu_checksum) &&
      json_ull(correctness_json, "gpu_control_checksum", &correctness_gpu_checksum) &&
      json_ull(hybrid_json, "gpu_control_checksum", &timed_gpu_checksum) &&
      json_size(correctness_json, "mismatch_count", &mismatch_count) &&
      json_double(correctness_json, "cpu_ms", &cpu_ms) &&
      json_double(hybrid_json, "gpu_end_to_end_ms", &gpu_end_to_end_ms) &&
      json_double(hybrid_json, "gpu_kernel_ms", &gpu_kernel_ms);
  if (!parsed) {
    print_status("failed_parse_adapter_json");
    return 1;
  }

  int checksum_equal = cpu_checksum == correctness_gpu_checksum;
  int timed_checksum_matches = timed_gpu_checksum == correctness_gpu_checksum;
  int passed =
      strcmp(correctness_status, "adapter_correctness_passed") == 0 &&
      strcmp(hybrid_status, "hybrid_entrypoint_passed") == 0 &&
      mismatch_count == 0 &&
      checksum_equal &&
      timed_checksum_matches;
  const double measured_batches = (double)repeat * (double)integration_batches;
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
      "\"integration_batches\":%d,\"correctness_status\":\"%s\","
      "\"hybrid_status\":\"%s\",\"mismatch_count\":%zu,"
      "\"cpu_control_checksum\":%llu,\"correctness_gpu_control_checksum\":%llu,"
      "\"timed_gpu_control_checksum\":%llu,"
      "\"cpu_vs_gpu_output_equal\":%s,"
      "\"cpu_vs_gpu_control_checksum_equal\":%s,"
      "\"timed_gpu_checksum_matches_correctness\":%s,"
      "\"cpu_ms\":%.17g,\"gpu_end_to_end_ms\":%.17g,"
      "\"gpu_kernel_ms\":%.17g,\"bridge_hybrid_wall_ms\":%.17g,"
      "\"bridge_hybrid_wall_ms_per_integration_batch\":%.17g,"
      "\"cpu_to_bridge_hybrid_wall_speedup\":%.17g,"
      "\"cpu_to_gpu_end_to_end_speedup\":%.17g,"
      "\"cpu_to_gpu_kernel_speedup\":%.17g}\n",
      passed ? "broader_runtime_entrypoint_passed" : "broader_runtime_entrypoint_failed",
      nstates,
      repeat,
      inner_repeat,
      integration_batches,
      correctness_status,
      hybrid_status,
      mismatch_count,
      cpu_checksum,
      correctness_gpu_checksum,
      timed_gpu_checksum,
      mismatch_count == 0 ? "true" : "false",
      checksum_equal ? "true" : "false",
      timed_checksum_matches ? "true" : "false",
      cpu_ms,
      gpu_end_to_end_ms,
      gpu_kernel_ms,
      bridge_hybrid_wall_ms,
      bridge_wall_per_batch,
      cpu_to_bridge_wall_speedup,
      cpu_to_gpu_end_to_end_speedup,
      cpu_to_gpu_kernel_speedup);

  return passed ? 0 : 1;
}
