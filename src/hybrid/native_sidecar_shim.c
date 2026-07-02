/*
 * native_sidecar_shim.c - FC-059 direct executable sidecar shim (smoke).
 *
 * This shim is linked as main() into the recognized native closure's
 * obj_dir/V<top> executable (its own main wins over the Verilator-generated
 * main, which lives inside the *__ALL.a archive and is therefore not pulled
 * when main is already defined here). Running the make-built executable thus
 * enters repo-owned sidecar runtime code directly, without delegating to
 * run_hybrid_template.py.
 *
 * Smoke slice only: it records that the direct executable path was reached and
 * fails closed before GPU artifact load / kernel launch / coverage compare. It
 * never falls back to CPU and never claims GPU execution.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Smoke evidence written next to the executable, under the generated obj_dir.
 * It is an evidence snapshot, not source of truth. */
static const char *EVIDENCE_NAME = "native_sidecar_runtime.json";

static const char *EVIDENCE_JSON =
    "{\n"
    "  \"schema_version\": 1,\n"
    "  \"surface\": \"native_sidecar_runtime\",\n"
    "  \"direct_executable_shim_reached\": true,\n"
    "  \"template_flow_invoked\": false,\n"
    "  \"run_hybrid_template_invoked\": false,\n"
    "  \"cpu_as_gpu_fallback\": false,\n"
    "  \"gpu_artifact_loaded\": false,\n"
    "  \"gpu_kernel_launched\": false,\n"
    "  \"coverage_collected\": false,\n"
    "  \"coverage_equivalence_passed\": false,\n"
    "  \"gpu_execution_claimed\": false,\n"
    "  \"smoke_only\": true,\n"
    "  \"fail_closed\": true,\n"
    "  \"in_process_runtime_abi\": false,\n"
    "  \"classification\": \"direct_shim_smoke_no_gpu_artifact\",\n"
    "  \"exit_zero_means\": \"direct executable sidecar shim was reached and smoke evidence was written; not GPU execution\"\n"
    "}\n";

/* Resolve the directory of argv[0] so the evidence lands in the obj_dir the
 * executable was built into, regardless of the caller's working directory. */
static int write_evidence(const char *argv0) {
  char dir[4096];
  dir[0] = '\0';
  if (argv0 != NULL) {
    const char *slash = strrchr(argv0, '/');
    if (slash != NULL) {
      size_t n = (size_t)(slash - argv0);
      if (n >= sizeof(dir)) n = sizeof(dir) - 1;
      memcpy(dir, argv0, n);
      dir[n] = '\0';
    }
  }

  char path[4096];
  if (dir[0] != '\0') {
    const size_t dir_len = strlen(dir);
    const size_t name_len = strlen(EVIDENCE_NAME);
    if (dir_len + 1 + name_len >= sizeof(path)) {
      fprintf(stderr, "native_sidecar_shim: evidence path is too long\n");
      return 1;
    }
    memcpy(path, dir, dir_len);
    path[dir_len] = '/';
    memcpy(path + dir_len + 1, EVIDENCE_NAME, name_len + 1);
  } else {
    memcpy(path, EVIDENCE_NAME, strlen(EVIDENCE_NAME) + 1);
  }

  FILE *fp = fopen(path, "wb");
  if (fp == NULL) {
    fprintf(stderr, "native_sidecar_shim: failed to open %s for writing\n", path);
    return 1;
  }
  if (fputs(EVIDENCE_JSON, fp) < 0) {
    fprintf(stderr, "native_sidecar_shim: failed to write %s\n", path);
    fclose(fp);
    return 1;
  }
  if (fclose(fp) != 0) {
    fprintf(stderr, "native_sidecar_shim: failed to close %s\n", path);
    return 1;
  }
  fputs(EVIDENCE_JSON, stdout);
  return 0;
}

int main(int argc, char **argv) {
  (void)argc;
  /* Writing the runtime evidence is the FC-059 smoke prerequisite; if it cannot
   * be written, fail nonzero (do not silently continue). */
  if (write_evidence(argc > 0 ? argv[0] : NULL) != 0) {
    return 1;
  }
  /* Smoke stop: the direct shim was reached. GPU artifact load / kernel launch /
   * coverage compare are not implemented in this slice, and CPU fallback is not
   * used. Exit 0 means "direct shim smoke reached", classified in the evidence. */
  return 0;
}
