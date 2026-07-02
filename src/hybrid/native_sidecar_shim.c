/*
 * native_sidecar_shim.c - direct executable sidecar shim smoke.
 *
 * This shim is linked as main() into the recognized native closure's
 * obj_dir/V<top> executable (its own main wins over the Verilator-generated
 * main, which lives inside the *__ALL.a archive and is therefore not pulled
 * when main is already defined here). Running the make-built executable thus
 * enters repo-owned sidecar runtime code directly, without delegating to
 * run_hybrid_template.py.
 *
 * Smoke slice only: it records that the direct executable path was reached,
 * validates the expected GPU artifact files, then attempts the minimum CUDA
 * Driver API module-load/kernel-launch sequence. Coverage compare is still a
 * later slice. It never falls back to CPU.
 */

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

/* Smoke evidence written next to the executable, under the generated obj_dir.
 * It is an evidence snapshot, not source of truth. */
static const char *EVIDENCE_NAME = "native_sidecar_runtime.json";
static const char *META_NAME = "vl_batch_gpu.meta.json";
static const char *CUBIN_NAME = "vl_batch_gpu.cubin";
static const char *INIT_STATE_NAME = "filelist_known_template_pulp_ita_mha_cpu_repeat_1x1.bin";
static const char *SANITIZED_INIT_STATE_NAME =
    "filelist_known_template_pulp_ita_mha_cpu_repeat_1x1.sanitized.bin";
static const char *DIRECT_GPU_DUMP_NAME =
    "filelist_known_template_pulp_ita_mha_direct_gpu_from_cpu_init_64x1.bin";
static const char *CPU_REFERENCE_REL =
    "artifacts/filelist_known_template_pulp_ita_mha_obj_dir/"
    "filelist_known_template_pulp_ita_mha_cpu_repeat_64x1.bin";
static const char *COVERAGE_GATE_REL =
    "config/scaling_gates/filelist_known_template_pulp_ita_mha_first_hybrid_benchmark_gate.json";
static const char *COMPARE_REPORT_REL =
    "reports/fc062_direct_shim_cpu_vs_native_64x1_coverage_output_compare.json";
static const char *COVERAGE_TARGET = "filelist_known_template_pulp_ita_mha";

#ifndef GPU_RTL_SIM_REPO_ROOT_DEFAULT
#define GPU_RTL_SIM_REPO_ROOT_DEFAULT ""
#endif

typedef int CUresult;
typedef int CUdevice;
typedef struct CUctx_st *CUcontext;
typedef struct CUmod_st *CUmodule;
typedef struct CUfunc_st *CUfunction;
typedef uint64_t CUdeviceptr;

#define CUDA_SUCCESS 0
#define CU_FUNC_ATTRIBUTE_LOCAL_SIZE_BYTES 3
#define CU_LIMIT_STACK_SIZE 0

typedef CUresult (*cuInit_fn)(unsigned int);
typedef CUresult (*cuDeviceGet_fn)(CUdevice *, int);
typedef CUresult (*cuCtxCreate_fn)(CUcontext *, unsigned int, CUdevice);
typedef CUresult (*cuCtxDestroy_fn)(CUcontext);
typedef CUresult (*cuModuleLoad_fn)(CUmodule *, const char *);
typedef CUresult (*cuModuleUnload_fn)(CUmodule);
typedef CUresult (*cuModuleGetFunction_fn)(CUfunction *, CUmodule, const char *);
typedef CUresult (*cuFuncGetAttribute_fn)(int *, int, CUfunction);
typedef CUresult (*cuCtxGetLimit_fn)(size_t *, int);
typedef CUresult (*cuCtxSetLimit_fn)(int, size_t);
typedef CUresult (*cuMemAlloc_fn)(CUdeviceptr *, size_t);
typedef CUresult (*cuMemFree_fn)(CUdeviceptr);
typedef CUresult (*cuMemsetD8_fn)(CUdeviceptr, unsigned char, size_t);
typedef CUresult (*cuMemcpyHtoD_fn)(CUdeviceptr, const void *, size_t);
typedef CUresult (*cuMemcpyDtoH_fn)(void *, CUdeviceptr, size_t);
typedef CUresult (*cuLaunchKernel_fn)(CUfunction, unsigned int, unsigned int, unsigned int,
                                      unsigned int, unsigned int, unsigned int,
                                      unsigned int, void *, void **, void **);
typedef CUresult (*cuCtxSynchronize_fn)(void);
typedef CUresult (*cuGetErrorString_fn)(CUresult, const char **);

typedef struct {
  void *lib;
  cuInit_fn cuInit;
  cuDeviceGet_fn cuDeviceGet;
  cuCtxCreate_fn cuCtxCreate;
  cuCtxDestroy_fn cuCtxDestroy;
  cuModuleLoad_fn cuModuleLoad;
  cuModuleUnload_fn cuModuleUnload;
  cuModuleGetFunction_fn cuModuleGetFunction;
  cuFuncGetAttribute_fn cuFuncGetAttribute;
  cuCtxGetLimit_fn cuCtxGetLimit;
  cuCtxSetLimit_fn cuCtxSetLimit;
  cuMemAlloc_fn cuMemAlloc;
  cuMemFree_fn cuMemFree;
  cuMemsetD8_fn cuMemsetD8;
  cuMemcpyHtoD_fn cuMemcpyHtoD;
  cuMemcpyDtoH_fn cuMemcpyDtoH;
  cuLaunchKernel_fn cuLaunchKernel;
  cuCtxSynchronize_fn cuCtxSynchronize;
  cuGetErrorString_fn cuGetErrorString;
} CudaDriver;

typedef struct {
  char cubin[512];
  char kernel[256];
  size_t storage_size;
} GpuMeta;

static const char *cuda_error_string(CudaDriver *driver, CUresult result, char *buf,
                                     size_t buf_size);

static int resolve_exe_dir(const char *argv0, char *dir, size_t dir_size) {
  if (dir_size == 0) return 1;
  dir[0] = '\0';
  if (argv0 == NULL) return 0;
  const char *slash = strrchr(argv0, '/');
  if (slash == NULL) return 0;
  size_t n = (size_t)(slash - argv0);
  if (n >= dir_size) n = dir_size - 1;
  memcpy(dir, argv0, n);
  dir[n] = '\0';
  return 0;
}

static int path_in_dir(const char *dir, const char *name, char *path, size_t path_size) {
  const size_t name_len = strlen(name);
  if (dir[0] == '\0') {
    if (name_len >= path_size) return 1;
    memcpy(path, name, name_len + 1);
    return 0;
  }
  const size_t dir_len = strlen(dir);
  if (dir_len + 1 + name_len >= path_size) return 1;
  memcpy(path, dir, dir_len);
  path[dir_len] = '/';
  memcpy(path + dir_len + 1, name, name_len + 1);
  return 0;
}

static int readable_file(const char *path, int require_nonempty) {
  FILE *fp = fopen(path, "rb");
  if (fp == NULL) return 0;
  int ok = 1;
  if (require_nonempty) {
    ok = fseek(fp, 0, SEEK_END) == 0 && ftell(fp) > 0;
  }
  fclose(fp);
  return ok;
}

static int read_text_file(const char *path, char *buf, size_t buf_size) {
  if (buf_size == 0) return 1;
  FILE *fp = fopen(path, "rb");
  if (fp == NULL) return 1;
  size_t n = fread(buf, 1, buf_size - 1, fp);
  int bad = ferror(fp);
  fclose(fp);
  if (bad) return 1;
  buf[n] = '\0';
  return 0;
}

static int extract_json_string(const char *json, const char *key, char *out, size_t out_size) {
  char needle[64];
  if (snprintf(needle, sizeof(needle), "\"%s\"", key) >= (int)sizeof(needle)) return 1;
  const char *p = strstr(json, needle);
  if (p == NULL) return 1;
  p = strchr(p + strlen(needle), ':');
  if (p == NULL) return 1;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  if (*p != '"') return 1;
  p++;
  const char *q = strchr(p, '"');
  if (q == NULL) return 1;
  size_t n = (size_t)(q - p);
  if (n == 0 || n >= out_size) return 1;
  memcpy(out, p, n);
  out[n] = '\0';
  return 0;
}

static int extract_json_size(const char *json, const char *key, size_t *out) {
  char needle[64];
  if (snprintf(needle, sizeof(needle), "\"%s\"", key) >= (int)sizeof(needle)) return 1;
  const char *p = strstr(json, needle);
  if (p == NULL) return 1;
  p = strchr(p + strlen(needle), ':');
  if (p == NULL) return 1;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  char *end = NULL;
  unsigned long long value = strtoull(p, &end, 10);
  if (end == p || value == 0) return 1;
  *out = (size_t)value;
  return 0;
}

static int load_gpu_meta(const char *meta_path, GpuMeta *meta) {
  char json[16384];
  memset(meta, 0, sizeof(*meta));
  if (read_text_file(meta_path, json, sizeof(json)) != 0) return 1;
  if (extract_json_string(json, "cubin", meta->cubin, sizeof(meta->cubin)) != 0) return 1;
  if (extract_json_string(json, "kernel", meta->kernel, sizeof(meta->kernel)) != 0) return 1;
  if (extract_json_size(json, "storage_size", &meta->storage_size) != 0) return 1;
  return 0;
}

static int repo_path(const char *root, const char *rel, char *path, size_t path_size) {
  const size_t root_len = strlen(root);
  const size_t rel_len = strlen(rel);
  if (root_len + 1 + rel_len >= path_size) return 1;
  memcpy(path, root, root_len);
  path[root_len] = '/';
  memcpy(path + root_len + 1, rel, rel_len + 1);
  return 0;
}

static int write_device_dump(CudaDriver *driver, CUdeviceptr d_storage, size_t total_storage,
                             const char *dump_path, char *status, size_t status_size) {
  unsigned char *buf = (unsigned char *)malloc(total_storage);
  if (buf == NULL) {
    snprintf(status, status_size, "candidate_dump_malloc_failed");
    return 1;
  }
  CUresult r = driver->cuMemcpyDtoH(buf, d_storage, total_storage);
  if (r != CUDA_SUCCESS) {
    char errbuf[64];
    snprintf(status, status_size, "cuMemcpyDtoH_failed_%d_%s", r,
             cuda_error_string(driver, r, errbuf, sizeof(errbuf)));
    free(buf);
    return 1;
  }
  FILE *fp = fopen(dump_path, "wb");
  if (fp == NULL) {
    snprintf(status, status_size, "candidate_dump_open_failed");
    free(buf);
    return 1;
  }
  const size_t nwritten = fwrite(buf, 1, total_storage, fp);
  const int bad = ferror(fp);
  if (fclose(fp) != 0 || bad || nwritten != total_storage) {
    snprintf(status, status_size, "candidate_dump_write_failed");
    free(buf);
    return 1;
  }
  free(buf);
  return 0;
}

static int extract_coverage_compare_result(const char *report_path, int *passed,
                                           int *mismatch_count) {
  char json[32768];
  *passed = 0;
  *mismatch_count = -1;
  if (read_text_file(report_path, json, sizeof(json)) != 0) return 1;
  const char *policy = strstr(json, "\"coverage_output_policy\"");
  if (policy == NULL) return 1;
  const char *mismatch = strstr(policy, "\"mismatch_count\"");
  if (mismatch == NULL) return 1;
  mismatch = strchr(mismatch, ':');
  if (mismatch == NULL) return 1;
  char *end = NULL;
  long value = strtol(mismatch + 1, &end, 10);
  if (end == mismatch + 1 || value < 0 || value > 2147483647L) return 1;
  *mismatch_count = (int)value;
  const char *passed_key = strstr(policy, "\"passed\"");
  if (passed_key == NULL) return 1;
  passed_key = strchr(passed_key, ':');
  if (passed_key == NULL) return 1;
  passed_key++;
  while (*passed_key == ' ' || *passed_key == '\t' || *passed_key == '\n' || *passed_key == '\r')
    passed_key++;
  *passed = strncmp(passed_key, "true", 4) == 0;
  return 0;
}

static int run_coverage_compare(const char *repo_root, const char *exe_dir,
                                const char *candidate_dump, char *status,
                                size_t status_size, int *passed, int *mismatch_count) {
  char pythonpath[4096];
  char reports_dir[4096];
  char reference_dump[4096];
  char coverage_gate[4096];
  char compare_report[4096];
  *passed = 0;
  *mismatch_count = -1;
  if (repo_path(repo_root, "src/tools", pythonpath, sizeof(pythonpath)) != 0
      || repo_path(repo_root, "reports", reports_dir, sizeof(reports_dir)) != 0
      || repo_path(repo_root, CPU_REFERENCE_REL, reference_dump, sizeof(reference_dump)) != 0
      || repo_path(repo_root, COVERAGE_GATE_REL, coverage_gate, sizeof(coverage_gate)) != 0
      || repo_path(repo_root, COMPARE_REPORT_REL, compare_report, sizeof(compare_report)) != 0) {
    snprintf(status, status_size, "coverage_compare_path_too_long");
    return 1;
  }
  if (!readable_file(reference_dump, 1)) {
    snprintf(status, status_size, "missing_cpu_reference_dump");
    return 1;
  }
  if (!readable_file(coverage_gate, 1)) {
    snprintf(status, status_size, "missing_coverage_output_gate");
    return 1;
  }
  if (mkdir(reports_dir, 0775) != 0) {
    struct stat st;
    if (stat(reports_dir, &st) != 0 || !S_ISDIR(st.st_mode)) {
      snprintf(status, status_size, "reports_dir_create_failed");
      return 1;
    }
  }
  setenv("PYTHONPATH", pythonpath, 1);
  pid_t pid = fork();
  if (pid < 0) {
    snprintf(status, status_size, "coverage_compare_fork_failed");
    return 1;
  }
  if (pid == 0) {
    if (chdir(repo_root) != 0) _exit(127);
    execlp("python3", "python3", "src/tools/compare_vl_hybrid_modes.py", exe_dir,
           "--compare-dumps", CPU_REFERENCE_REL, candidate_dump, "--reference-label",
           "cpu_repeat_64x1", "--candidate-label",
           "direct_shim_from_cpu_init_64x1", "--acceptance-policy",
           "coverage_output_equivalence", "--json-out", COMPARE_REPORT_REL,
           "--coverage-output-gate", COVERAGE_GATE_REL, "--coverage-output-target",
           COVERAGE_TARGET, (char *)NULL);
    _exit(127);
  }
  int wait_status = 0;
  if (waitpid(pid, &wait_status, 0) < 0) {
    snprintf(status, status_size, "coverage_compare_wait_failed");
    return 1;
  }
  if (!WIFEXITED(wait_status) || WEXITSTATUS(wait_status) != 0) {
    snprintf(status, status_size, "coverage_compare_failed");
    return 1;
  }
  if (extract_coverage_compare_result(compare_report, passed, mismatch_count) != 0) {
    snprintf(status, status_size, "coverage_compare_report_parse_failed");
    return 1;
  }
  if (!*passed || *mismatch_count != 0) {
    snprintf(status, status_size, "coverage_output_equivalence_failed");
    return 1;
  }
  return 0;
}

static const char *resolve_repo_root_for_runtime(void) {
  const char *repo_root = getenv("GPU_RTL_SIM_REPO_ROOT");
  if (repo_root != NULL && repo_root[0] != '\0') return repo_root;
  if (GPU_RTL_SIM_REPO_ROOT_DEFAULT[0] != '\0') return GPU_RTL_SIM_REPO_ROOT_DEFAULT;
  return NULL;
}

static int resolve_init_state_path(const char *cubin_path, char *path, size_t path_size,
                                   int *found) {
  char dir[4096];
  *found = 0;
  if (resolve_exe_dir(cubin_path, dir, sizeof(dir)) != 0) return 1;
  if (path_in_dir(dir, SANITIZED_INIT_STATE_NAME, path, path_size) != 0) return 1;
  if (readable_file(path, 1)) {
    *found = 1;
    return 0;
  }
  if (path_in_dir(dir, INIT_STATE_NAME, path, path_size) != 0) return 1;
  if (readable_file(path, 1)) *found = 1;
  return 0;
}

static void *load_symbol(void *lib, const char *name) {
  return dlsym(lib, name);
}

static int load_cuda_driver(CudaDriver *driver) {
  memset(driver, 0, sizeof(*driver));
  const char *candidates[] = {"libcuda.so.1", "libcuda.so", NULL};
  for (int i = 0; candidates[i] != NULL; i++) {
    driver->lib = dlopen(candidates[i], RTLD_NOW | RTLD_LOCAL);
    if (driver->lib != NULL) break;
  }
  if (driver->lib == NULL) return 1;

  driver->cuInit = (cuInit_fn)load_symbol(driver->lib, "cuInit");
  driver->cuDeviceGet = (cuDeviceGet_fn)load_symbol(driver->lib, "cuDeviceGet");
  driver->cuCtxCreate = (cuCtxCreate_fn)load_symbol(driver->lib, "cuCtxCreate_v2");
  if (driver->cuCtxCreate == NULL)
    driver->cuCtxCreate = (cuCtxCreate_fn)load_symbol(driver->lib, "cuCtxCreate");
  driver->cuCtxDestroy = (cuCtxDestroy_fn)load_symbol(driver->lib, "cuCtxDestroy_v2");
  if (driver->cuCtxDestroy == NULL)
    driver->cuCtxDestroy = (cuCtxDestroy_fn)load_symbol(driver->lib, "cuCtxDestroy");
  driver->cuModuleLoad = (cuModuleLoad_fn)load_symbol(driver->lib, "cuModuleLoad");
  driver->cuModuleUnload = (cuModuleUnload_fn)load_symbol(driver->lib, "cuModuleUnload");
  driver->cuModuleGetFunction =
      (cuModuleGetFunction_fn)load_symbol(driver->lib, "cuModuleGetFunction");
  driver->cuFuncGetAttribute =
      (cuFuncGetAttribute_fn)load_symbol(driver->lib, "cuFuncGetAttribute");
  driver->cuCtxGetLimit = (cuCtxGetLimit_fn)load_symbol(driver->lib, "cuCtxGetLimit");
  driver->cuCtxSetLimit = (cuCtxSetLimit_fn)load_symbol(driver->lib, "cuCtxSetLimit");
  driver->cuMemAlloc = (cuMemAlloc_fn)load_symbol(driver->lib, "cuMemAlloc_v2");
  if (driver->cuMemAlloc == NULL)
    driver->cuMemAlloc = (cuMemAlloc_fn)load_symbol(driver->lib, "cuMemAlloc");
  driver->cuMemFree = (cuMemFree_fn)load_symbol(driver->lib, "cuMemFree_v2");
  if (driver->cuMemFree == NULL)
    driver->cuMemFree = (cuMemFree_fn)load_symbol(driver->lib, "cuMemFree");
  driver->cuMemsetD8 = (cuMemsetD8_fn)load_symbol(driver->lib, "cuMemsetD8_v2");
  if (driver->cuMemsetD8 == NULL)
    driver->cuMemsetD8 = (cuMemsetD8_fn)load_symbol(driver->lib, "cuMemsetD8");
  driver->cuMemcpyHtoD = (cuMemcpyHtoD_fn)load_symbol(driver->lib, "cuMemcpyHtoD_v2");
  if (driver->cuMemcpyHtoD == NULL)
    driver->cuMemcpyHtoD = (cuMemcpyHtoD_fn)load_symbol(driver->lib, "cuMemcpyHtoD");
  driver->cuMemcpyDtoH = (cuMemcpyDtoH_fn)load_symbol(driver->lib, "cuMemcpyDtoH_v2");
  if (driver->cuMemcpyDtoH == NULL)
    driver->cuMemcpyDtoH = (cuMemcpyDtoH_fn)load_symbol(driver->lib, "cuMemcpyDtoH");
  driver->cuLaunchKernel = (cuLaunchKernel_fn)load_symbol(driver->lib, "cuLaunchKernel");
  driver->cuCtxSynchronize = (cuCtxSynchronize_fn)load_symbol(driver->lib, "cuCtxSynchronize");
  driver->cuGetErrorString = (cuGetErrorString_fn)load_symbol(driver->lib, "cuGetErrorString");

  if (driver->cuInit == NULL || driver->cuDeviceGet == NULL || driver->cuCtxCreate == NULL
      || driver->cuCtxDestroy == NULL || driver->cuModuleLoad == NULL
      || driver->cuModuleUnload == NULL || driver->cuModuleGetFunction == NULL
      || driver->cuFuncGetAttribute == NULL || driver->cuCtxGetLimit == NULL
      || driver->cuCtxSetLimit == NULL
      || driver->cuMemAlloc == NULL || driver->cuMemFree == NULL
      || driver->cuMemsetD8 == NULL || driver->cuMemcpyHtoD == NULL
      || driver->cuMemcpyDtoH == NULL || driver->cuLaunchKernel == NULL
      || driver->cuCtxSynchronize == NULL) {
    dlclose(driver->lib);
    memset(driver, 0, sizeof(*driver));
    return 1;
  }
  return 0;
}

static const char *cuda_error_string(CudaDriver *driver, CUresult result, char *buf, size_t buf_size) {
  const char *msg = NULL;
  if (driver->cuGetErrorString != NULL && driver->cuGetErrorString(result, &msg) == CUDA_SUCCESS
      && msg != NULL) {
    return msg;
  }
  snprintf(buf, buf_size, "cuda_error_%d", result);
  return buf;
}

static int raise_stack_limit_for_kernel(CudaDriver *driver, CUfunction fn, char *status,
                                        size_t status_size) {
  int local_size = 0;
  CUresult r = driver->cuFuncGetAttribute(&local_size, CU_FUNC_ATTRIBUTE_LOCAL_SIZE_BYTES, fn);
  if (r != CUDA_SUCCESS) {
    char errbuf[64];
    snprintf(status, status_size, "cuFuncGetAttribute_failed_%d_%s", r,
             cuda_error_string(driver, r, errbuf, sizeof(errbuf)));
    return 1;
  }
  if (local_size <= 0) return 0;

  size_t current = 0;
  r = driver->cuCtxGetLimit(&current, CU_LIMIT_STACK_SIZE);
  if (r != CUDA_SUCCESS) {
    char errbuf[64];
    snprintf(status, status_size, "cuCtxGetLimit_failed_%d_%s", r,
             cuda_error_string(driver, r, errbuf, sizeof(errbuf)));
    return 1;
  }
  if ((size_t)local_size <= current) return 0;

  r = driver->cuCtxSetLimit(CU_LIMIT_STACK_SIZE, (size_t)local_size);
  if (r != CUDA_SUCCESS) {
    char errbuf[64];
    snprintf(status, status_size, "cuCtxSetLimit_failed_%d_%s", r,
             cuda_error_string(driver, r, errbuf, sizeof(errbuf)));
    return 1;
  }
  return 0;
}

static int launch_kernel_smoke(const char *cubin_path, const GpuMeta *meta, char *status,
                               size_t status_size, char *kernel_name, size_t kernel_name_size,
                               int *module_loaded, int *kernel_launched,
                               int *coverage_collected, int *coverage_passed,
                               int *coverage_mismatch_count) {
  CudaDriver driver;
  CUcontext ctx = NULL;
  CUmodule module = NULL;
  CUfunction fn = NULL;
  CUdeviceptr d_storage = 0;
  unsigned char *init_buf = NULL;
  void *params[2] = {NULL, NULL};
  int rc = 1;
  char errbuf[64];
  *module_loaded = 0;
  *kernel_launched = 0;
  *coverage_collected = 0;
  *coverage_passed = 0;
  *coverage_mismatch_count = -1;
  snprintf(kernel_name, kernel_name_size, "%s", meta->kernel);

  if (load_cuda_driver(&driver) != 0) {
    snprintf(status, status_size, "cuda_driver_unavailable");
    return 1;
  }

#define CUDA_STEP(call, label)                                                                \
  do {                                                                                        \
    CUresult _r = (call);                                                                     \
    if (_r != CUDA_SUCCESS) {                                                                 \
      snprintf(status, status_size, "%s_failed_%d_%s", (label), _r,                          \
               cuda_error_string(&driver, _r, errbuf, sizeof(errbuf)));                       \
      goto done;                                                                              \
    }                                                                                         \
  } while (0)

  CUdevice dev = 0;
  int nstates = 64;
  unsigned int block = 256;
  unsigned int grid = ((unsigned int)nstates + block - 1U) / block;
  size_t total_storage = meta->storage_size * (size_t)nstates;
  if (meta->storage_size != 0 && total_storage / meta->storage_size != (size_t)nstates) {
    snprintf(status, status_size, "storage_size_overflow");
    goto done;
  }
  params[0] = &d_storage;
  params[1] = &nstates;
  CUDA_STEP(driver.cuInit(0), "cuInit");
  CUDA_STEP(driver.cuDeviceGet(&dev, 0), "cuDeviceGet");
  CUDA_STEP(driver.cuCtxCreate(&ctx, 0, dev), "cuCtxCreate");
  CUDA_STEP(driver.cuModuleLoad(&module, cubin_path), "cuModuleLoad");
  *module_loaded = 1;
  CUDA_STEP(driver.cuModuleGetFunction(&fn, module, meta->kernel), "cuModuleGetFunction");
  if (raise_stack_limit_for_kernel(&driver, fn, status, status_size) != 0) goto done;
  CUDA_STEP(driver.cuMemAlloc(&d_storage, total_storage), "cuMemAlloc");
  CUDA_STEP(driver.cuMemsetD8(d_storage, 0, total_storage), "cuMemsetD8");
  {
    char init_path[4096];
    int init_found = 0;
    if (resolve_init_state_path(cubin_path, init_path, sizeof(init_path), &init_found) != 0) {
      snprintf(status, status_size, "init_state_path_too_long");
      goto done;
    }
    if (init_found) {
      FILE *fp = fopen(init_path, "rb");
      if (fp == NULL) {
        snprintf(status, status_size, "init_state_open_failed");
        goto done;
      }
      init_buf = (unsigned char *)malloc(meta->storage_size);
      if (init_buf == NULL) {
        fclose(fp);
        snprintf(status, status_size, "init_state_malloc_failed");
        goto done;
      }
      size_t nread = fread(init_buf, 1, meta->storage_size, fp);
      int bad = ferror(fp);
      fclose(fp);
      if (bad || nread != meta->storage_size) {
        snprintf(status, status_size, "init_state_size_mismatch");
        goto done;
      }
      for (int state = 0; state < nstates; state++) {
        CUDA_STEP(driver.cuMemcpyHtoD(d_storage + ((size_t)state * meta->storage_size),
                                      init_buf, meta->storage_size),
                  "cuMemcpyHtoD");
      }
      free(init_buf);
      init_buf = NULL;
    }
  }
  CUDA_STEP(driver.cuLaunchKernel(fn, grid, 1, 1, block, 1, 1, 0, NULL, params, NULL),
            "cuLaunchKernel");
  CUDA_STEP(driver.cuCtxSynchronize(), "cuCtxSynchronize");
  *kernel_launched = 1;
  if (meta->storage_size == 6144U) {
    char exe_dir[4096];
    char dump_path[4096];
    const char *repo_root = resolve_repo_root_for_runtime();
    if (repo_root == NULL || repo_root[0] == '\0') {
      snprintf(status, status_size, "missing_repo_root_for_coverage_compare");
      goto done;
    }
    if (resolve_exe_dir(cubin_path, exe_dir, sizeof(exe_dir)) != 0
        || path_in_dir(exe_dir, DIRECT_GPU_DUMP_NAME, dump_path, sizeof(dump_path)) != 0) {
      snprintf(status, status_size, "candidate_dump_path_too_long");
      goto done;
    }
    if (write_device_dump(&driver, d_storage, total_storage, dump_path, status, status_size) != 0)
      goto done;
    *coverage_collected = 1;
    if (run_coverage_compare(repo_root, exe_dir, dump_path, status, status_size,
                             coverage_passed, coverage_mismatch_count)
        != 0)
      goto done;
  }
  snprintf(status, status_size, "cuda_module_loaded_and_kernel_launched");
  rc = 0;

done:
  free(init_buf);
  if (d_storage != 0) driver.cuMemFree(d_storage);
  if (module != NULL) driver.cuModuleUnload(module);
  if (ctx != NULL) driver.cuCtxDestroy(ctx);
  if (driver.lib != NULL) dlclose(driver.lib);
#undef CUDA_STEP
  return rc;
}

/* Evidence lands in the executable's obj_dir, regardless of caller cwd. */
static int write_evidence(const char *argv0, int artifact_loaded, int module_loaded,
                          int kernel_launched, int coverage_collected,
                          int coverage_passed, int coverage_mismatch_count,
                          int gpu_execution_claimed, const char *status,
                          const char *kernel_name) {
  char dir[4096];
  if (resolve_exe_dir(argv0, dir, sizeof(dir)) != 0) return 1;
  char path[4096];
  if (path_in_dir(dir, EVIDENCE_NAME, path, sizeof(path)) != 0) {
    fprintf(stderr, "native_sidecar_shim: evidence path is too long\n");
    return 1;
  }

  FILE *fp = fopen(path, "wb");
  if (fp == NULL) {
    fprintf(stderr, "native_sidecar_shim: failed to open %s for writing\n", path);
    return 1;
  }
  const char *loaded = artifact_loaded ? "true" : "false";
  const char *cuda_loaded = module_loaded ? "true" : "false";
  const char *launched = kernel_launched ? "true" : "false";
  const char *collected = coverage_collected ? "true" : "false";
  const char *coverage_ok = coverage_passed ? "true" : "false";
  const char *claimed = gpu_execution_claimed ? "true" : "false";
  if (fprintf(fp,
              "{\n"
              "  \"schema_version\": 1,\n"
              "  \"surface\": \"native_sidecar_runtime\",\n"
              "  \"direct_executable_shim_reached\": true,\n"
              "  \"template_flow_invoked\": false,\n"
              "  \"run_hybrid_template_invoked\": false,\n"
              "  \"cpu_as_gpu_fallback\": false,\n"
              "  \"gpu_artifact_loaded\": %s,\n"
              "  \"gpu_artifact_path\": \"%s\",\n"
              "  \"gpu_artifact_meta_path\": \"%s\",\n"
              "  \"gpu_artifact_load_status\": \"%s\",\n"
              "  \"cuda_module_loaded\": %s,\n"
              "  \"gpu_kernel_launched\": %s,\n"
              "  \"gpu_kernel_name\": \"%s\",\n"
              "  \"coverage_collected\": %s,\n"
              "  \"coverage_equivalence_passed\": %s,\n"
              "  \"coverage_output_mismatch_count\": %d,\n"
              "  \"gpu_execution_claimed\": %s,\n"
              "  \"smoke_only\": true,\n"
              "  \"fail_closed\": true,\n"
              "  \"in_process_runtime_abi\": true,\n"
              "  \"classification\": \"%s\",\n"
              "  \"exit_zero_means\": \"direct executable sidecar shim loaded the CUDA module, launched the kernel, and passed coverage-output equivalence when coverage_equivalence_passed is true; not timing\"\n"
              "}\n",
              loaded, CUBIN_NAME, META_NAME, status, cuda_loaded, launched,
              kernel_name != NULL ? kernel_name : "", collected, coverage_ok,
              coverage_mismatch_count, claimed,
              coverage_passed ? "direct_shim_coverage_output_equivalence_smoke"
                              : kernel_launched ? "direct_shim_cuda_kernel_launch_smoke_no_coverage"
                              : "direct_shim_cuda_kernel_launch_fail_closed")
      < 0) {
    fprintf(stderr, "native_sidecar_shim: failed to write %s\n", path);
    fclose(fp);
    return 1;
  }
  if (fclose(fp) != 0) {
    fprintf(stderr, "native_sidecar_shim: failed to close %s\n", path);
    return 1;
  }
  FILE *readback = fopen(path, "rb");
  if (readback != NULL) {
    int ch;
    while ((ch = fgetc(readback)) != EOF) fputc(ch, stdout);
    fclose(readback);
  }
  return 0;
}

int main(int argc, char **argv) {
  const char *argv0 = argc > 0 ? argv[0] : NULL;
  char dir[4096];
  char meta_path[4096];
  char cubin_path[4096];
  if (resolve_exe_dir(argv0, dir, sizeof(dir)) != 0
      || path_in_dir(dir, META_NAME, meta_path, sizeof(meta_path)) != 0
      || path_in_dir(dir, CUBIN_NAME, cubin_path, sizeof(cubin_path)) != 0) {
    fprintf(stderr, "native_sidecar_shim: runtime artifact path is too long\n");
    return 1;
  }

  const int meta_ok = readable_file(meta_path, 1);
  const int cubin_ok = readable_file(cubin_path, 1);
  if (!meta_ok || !cubin_ok) {
    const char *status = !meta_ok ? "missing_vl_batch_gpu_meta_json" : "missing_or_empty_vl_batch_gpu_cubin";
    if (write_evidence(argv0, 0, 0, 0, 0, 0, -1, 0, status, "") != 0) return 1;
    fprintf(stderr, "native_sidecar_shim: %s\n", status);
    return 2;
  }

  GpuMeta meta;
  if (load_gpu_meta(meta_path, &meta) != 0) {
    if (write_evidence(argv0, 1, 0, 0, 0, 0, -1, 0, "invalid_vl_batch_gpu_meta_json", "") != 0)
      return 1;
    fprintf(stderr, "native_sidecar_shim: invalid_vl_batch_gpu_meta_json\n");
    return 2;
  }
  if (strcmp(meta.cubin, CUBIN_NAME) != 0) {
    if (write_evidence(argv0, 1, 0, 0, 0, 0, -1, 0, "unexpected_vl_batch_gpu_cubin_name", meta.kernel) != 0)
      return 1;
    fprintf(stderr, "native_sidecar_shim: unexpected_vl_batch_gpu_cubin_name\n");
    return 2;
  }

  char status[256];
  char kernel_name[256];
  int module_loaded = 0;
  int kernel_launched = 0;
  int coverage_collected = 0;
  int coverage_passed = 0;
  int coverage_mismatch_count = -1;
  int launch_ok = launch_kernel_smoke(cubin_path, &meta, status, sizeof(status),
                                      kernel_name, sizeof(kernel_name), &module_loaded,
                                      &kernel_launched, &coverage_collected,
                                      &coverage_passed, &coverage_mismatch_count) == 0;
  if (write_evidence(argv0, 1, module_loaded, kernel_launched, coverage_collected,
                     coverage_passed, coverage_mismatch_count, launch_ok, status,
                     kernel_name) != 0)
    return 1;
  if (!launch_ok) {
    fprintf(stderr, "native_sidecar_shim: %s\n", status);
    return 3;
  }
  return 0;
}
