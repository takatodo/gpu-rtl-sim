#!/usr/bin/env python3
"""Patch Vortex Vsim main materialized runtime args to use real CUDA Driver API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MAIN_CPP = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/Vsim__main.cpp"
)
INCLUDE_ANCHOR = "#include <unistd.h>\n"
PATCH_BEGIN = "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN */"
PATCH_END = "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_END */"
MATERIALIZED_ARGS_PROBE_BEGIN = "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */"
MATERIALIZED_ARGS_PROBE_CALL_OLD = (
    "    if (rtlmeter_vortex_materialized_runtime_args_probe() != 0) return 123;\n"
)
MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC = (
    "    int rtlmeter_vortex_materialized_runtime_args_status = rtlmeter_vortex_materialized_runtime_args_probe(topp.get());\n"
    "    if (rtlmeter_vortex_materialized_runtime_args_status != 0) {\n"
    "        std::fprintf(stderr, \"rtlmeter_vortex_materialized_runtime_args_probe_status=%d\\n\", rtlmeter_vortex_materialized_runtime_args_status);\n"
    "        return 123;\n"
    "    }\n"
)
MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC_NO_MODEL = (
    "    int rtlmeter_vortex_materialized_runtime_args_status = rtlmeter_vortex_materialized_runtime_args_probe();\n"
    "    if (rtlmeter_vortex_materialized_runtime_args_status != 0) {\n"
    "        std::fprintf(stderr, \"rtlmeter_vortex_materialized_runtime_args_probe_status=%d\\n\", rtlmeter_vortex_materialized_runtime_args_status);\n"
    "        return 123;\n"
    "    }\n"
)
STATUS_PATCHED = "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_applied"
STATUS_ALREADY_PATCHED = "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_already_present"
STATUS_MISSING = "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_missing_source"
STATUS_UNSUPPORTED = "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_unsupported_source"
ROOT_STORAGE_CALLBACK = "rtlmeter_vortex_real_cuda_launch_root_storage_kernel"
NOOP_CALLBACK = "rtlmeter_vortex_real_cuda_noop_kernel"
SEQUENCE_FAILURE_DIAGNOSTIC = (
    "    if (result != VORTEX_CUDA_SUCCESS) {\n"
    "        std::fprintf(stderr, \"rtlmeter_vortex_runtime_sequence_failed stage=%s result=%d index=%d\\n\",\n"
    "            sequence_summary.failed_stage ? sequence_summary.failed_stage : \"unknown\",\n"
    "            (int)sequence_summary.failed_result,\n"
    "            sequence_summary.failed_index);\n"
    "        return 30;\n"
    "    }\n"
)
AUTHORITY_DIAGNOSTIC_PREFIX = "rtlmeter_vortex_runtime_authority"
AUTHORITY_DIAGNOSTIC = (
    "    std::fprintf(stderr, \"rtlmeter_vortex_runtime_authority authority_report_ready=%d authority_passed=%d authority_source=%s memory_post_condition_passed=%d stdout_test_passed_observed=%d observable_export_invoked=%d kernel_launch_invoked=%d dcr_applied_count=%u\\n\",\n"
    "        tb_summary.authority_report_ready,\n"
    "        tb_summary.authority_passed,\n"
    "        tb_summary.authority_source ? tb_summary.authority_source : \"none\",\n"
    "        sequence_summary.observables.memory_post_condition_passed,\n"
    "        sequence_summary.observables.stdout_test_passed_observed,\n"
    "        sequence_summary.observable_export_invoked,\n"
    "        sequence_summary.kernel_launch_invoked,\n"
    "        sequence_summary.dcr_applied_count);\n"
)
ROOT_STORAGE_KERNEL_FAILURE_PREFIX = "rtlmeter_vortex_root_storage_kernel_failed"
ROOT_STORAGE_KERNEL_STAGE_PREFIX = "rtlmeter_vortex_root_storage_kernel_stage"


REQUIRED_FAKE_SYMBOLS = (
    "rtlmeter_vortex_runtime_args_probe_alloc",
    "rtlmeter_vortex_runtime_args_probe_h2d",
    "rtlmeter_vortex_runtime_args_probe_memset",
    "rtlmeter_vortex_runtime_args_probe_free",
    "rtlmeter_vortex_runtime_args_probe_dcr",
    "rtlmeter_vortex_runtime_args_probe_kernel",
    "rtlmeter_vortex_runtime_args_probe_dtoh",
)


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    return "<local-absolute-path>" if path.is_absolute() else path.as_posix()


def _real_cuda_block() -> str:
    return (
        f"{PATCH_BEGIN}\n"
        "#include <cstdio>\n"
        "#include <dlfcn.h>\n"
        "#include <stdint.h>\n"
        "#include <string.h>\n"
        "#include \"../../../../../../../src/hybrid/vortex_lowered_tb_runtime_sequence.h\"\n"
        "typedef int RtlmeterVortexCuResult;\n"
        "typedef int RtlmeterVortexCuDevice;\n"
        "typedef void* RtlmeterVortexCuContext;\n"
        "typedef void* RtlmeterVortexCuModule;\n"
        "typedef void* RtlmeterVortexCuFunction;\n"
        "typedef void* RtlmeterVortexCuStream;\n"
        "typedef unsigned long long RtlmeterVortexCuDeviceptr;\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuInitFn)(unsigned int);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuDeviceGetFn)(RtlmeterVortexCuDevice*, int);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuCtxCreateFn)(RtlmeterVortexCuContext*, unsigned int, RtlmeterVortexCuDevice);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuCtxDestroyFn)(RtlmeterVortexCuContext);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuCtxSynchronizeFn)(void);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuModuleLoadFn)(RtlmeterVortexCuModule*, const char*);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuModuleUnloadFn)(RtlmeterVortexCuModule);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuModuleGetFunctionFn)(RtlmeterVortexCuFunction*, RtlmeterVortexCuModule, const char*);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuLaunchKernelFn)(RtlmeterVortexCuFunction, unsigned int, unsigned int, unsigned int, unsigned int, unsigned int, unsigned int, unsigned int, RtlmeterVortexCuStream, void**, void**);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuMemAllocFn)(RtlmeterVortexCuDeviceptr*, size_t);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuMemcpyHtoDFn)(RtlmeterVortexCuDeviceptr, const void*, size_t);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuMemcpyDtoHFn)(void*, RtlmeterVortexCuDeviceptr, size_t);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuMemsetD8Fn)(RtlmeterVortexCuDeviceptr, unsigned char, size_t);\n"
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuMemFreeFn)(RtlmeterVortexCuDeviceptr);\n\n"
        "typedef struct {\n"
        "    void* libcuda;\n"
        "    RtlmeterVortexCuContext context;\n"
        "    unsigned dcr_count;\n"
        "    unsigned kernel_count;\n"
        "    RtlmeterVortexCuInitFn cuInit;\n"
        "    RtlmeterVortexCuDeviceGetFn cuDeviceGet;\n"
        "    RtlmeterVortexCuCtxCreateFn cuCtxCreate;\n"
        "    RtlmeterVortexCuCtxDestroyFn cuCtxDestroy;\n"
        "    RtlmeterVortexCuCtxSynchronizeFn cuCtxSynchronize;\n"
        "    RtlmeterVortexCuModuleLoadFn cuModuleLoad;\n"
        "    RtlmeterVortexCuModuleUnloadFn cuModuleUnload;\n"
        "    RtlmeterVortexCuModuleGetFunctionFn cuModuleGetFunction;\n"
        "    RtlmeterVortexCuLaunchKernelFn cuLaunchKernel;\n"
        "    RtlmeterVortexCuMemAllocFn cuMemAlloc;\n"
        "    RtlmeterVortexCuMemcpyHtoDFn cuMemcpyHtoD;\n"
        "    RtlmeterVortexCuMemcpyDtoHFn cuMemcpyDtoH;\n"
        "    RtlmeterVortexCuMemsetD8Fn cuMemsetD8;\n"
        "    RtlmeterVortexCuMemFreeFn cuMemFree;\n"
        "} RtlmeterVortexRealCudaMaterializedRuntime;\n\n"
        "typedef struct {\n"
        "    const void* data;\n"
        "    size_t bytes;\n"
        "} RtlmeterVortexRootStorageImage;\n\n"
        "static RtlmeterVortexRealCudaMaterializedRuntime rtlmeter_vortex_real_cuda_runtime;\n\n"
        "static void rtlmeter_vortex_root_storage_kernel_stage(const char* stage) {\n"
        "    std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_stage stage=%s\\n\", stage);\n"
        "    std::fflush(stderr);\n"
        "}\n"
        "static void* rtlmeter_vortex_real_cuda_sym(const char* name) {\n"
        "    return rtlmeter_vortex_real_cuda_runtime.libcuda ? dlsym(rtlmeter_vortex_real_cuda_runtime.libcuda, name) : 0;\n"
        "}\n"
        "static int rtlmeter_vortex_real_cuda_open(void) {\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.libcuda != 0) return 0;\n"
        "    const char* names[] = {\"libcuda.so.1\", \"/usr/lib/wsl/lib/libcuda.so.1\", \"libcuda.so\"};\n"
        "    for (unsigned i = 0; i < sizeof(names) / sizeof(names[0]); ++i) {\n"
        "        rtlmeter_vortex_real_cuda_runtime.libcuda = dlopen(names[i], RTLD_NOW | RTLD_LOCAL);\n"
        "        if (rtlmeter_vortex_real_cuda_runtime.libcuda != 0) break;\n"
        "    }\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.libcuda == 0) return 7001;\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuInit = (RtlmeterVortexCuInitFn)rtlmeter_vortex_real_cuda_sym(\"cuInit\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuDeviceGet = (RtlmeterVortexCuDeviceGetFn)rtlmeter_vortex_real_cuda_sym(\"cuDeviceGet\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuCtxCreate = (RtlmeterVortexCuCtxCreateFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxCreate_v2\");\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.cuCtxCreate == 0) rtlmeter_vortex_real_cuda_runtime.cuCtxCreate = (RtlmeterVortexCuCtxCreateFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxCreate\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy = (RtlmeterVortexCuCtxDestroyFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxDestroy_v2\");\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy == 0) rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy = (RtlmeterVortexCuCtxDestroyFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxDestroy\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize = (RtlmeterVortexCuCtxSynchronizeFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxSynchronize\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuModuleLoad = (RtlmeterVortexCuModuleLoadFn)rtlmeter_vortex_real_cuda_sym(\"cuModuleLoad\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuModuleUnload = (RtlmeterVortexCuModuleUnloadFn)rtlmeter_vortex_real_cuda_sym(\"cuModuleUnload\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction = (RtlmeterVortexCuModuleGetFunctionFn)rtlmeter_vortex_real_cuda_sym(\"cuModuleGetFunction\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuLaunchKernel = (RtlmeterVortexCuLaunchKernelFn)rtlmeter_vortex_real_cuda_sym(\"cuLaunchKernel\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuMemAlloc = (RtlmeterVortexCuMemAllocFn)rtlmeter_vortex_real_cuda_sym(\"cuMemAlloc_v2\");\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.cuMemAlloc == 0) rtlmeter_vortex_real_cuda_runtime.cuMemAlloc = (RtlmeterVortexCuMemAllocFn)rtlmeter_vortex_real_cuda_sym(\"cuMemAlloc\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD = (RtlmeterVortexCuMemcpyHtoDFn)rtlmeter_vortex_real_cuda_sym(\"cuMemcpyHtoD_v2\");\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD == 0) rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD = (RtlmeterVortexCuMemcpyHtoDFn)rtlmeter_vortex_real_cuda_sym(\"cuMemcpyHtoD\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuMemcpyDtoH = (RtlmeterVortexCuMemcpyDtoHFn)rtlmeter_vortex_real_cuda_sym(\"cuMemcpyDtoH_v2\");\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.cuMemcpyDtoH == 0) rtlmeter_vortex_real_cuda_runtime.cuMemcpyDtoH = (RtlmeterVortexCuMemcpyDtoHFn)rtlmeter_vortex_real_cuda_sym(\"cuMemcpyDtoH\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuMemsetD8 = (RtlmeterVortexCuMemsetD8Fn)rtlmeter_vortex_real_cuda_sym(\"cuMemsetD8_v2\");\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.cuMemsetD8 == 0) rtlmeter_vortex_real_cuda_runtime.cuMemsetD8 = (RtlmeterVortexCuMemsetD8Fn)rtlmeter_vortex_real_cuda_sym(\"cuMemsetD8\");\n"
        "    rtlmeter_vortex_real_cuda_runtime.cuMemFree = (RtlmeterVortexCuMemFreeFn)rtlmeter_vortex_real_cuda_sym(\"cuMemFree_v2\");\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.cuMemFree == 0) rtlmeter_vortex_real_cuda_runtime.cuMemFree = (RtlmeterVortexCuMemFreeFn)rtlmeter_vortex_real_cuda_sym(\"cuMemFree\");\n"
        "    if (!rtlmeter_vortex_real_cuda_runtime.cuInit || !rtlmeter_vortex_real_cuda_runtime.cuDeviceGet || !rtlmeter_vortex_real_cuda_runtime.cuCtxCreate || !rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy || !rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize || !rtlmeter_vortex_real_cuda_runtime.cuModuleLoad || !rtlmeter_vortex_real_cuda_runtime.cuModuleUnload || !rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction || !rtlmeter_vortex_real_cuda_runtime.cuLaunchKernel || !rtlmeter_vortex_real_cuda_runtime.cuMemAlloc || !rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD || !rtlmeter_vortex_real_cuda_runtime.cuMemcpyDtoH || !rtlmeter_vortex_real_cuda_runtime.cuMemsetD8 || !rtlmeter_vortex_real_cuda_runtime.cuMemFree) return 7002;\n"
        "    return 0;\n"
        "}\n"
        "static int rtlmeter_vortex_real_cuda_context_open(void) {\n"
        "    int ok = rtlmeter_vortex_real_cuda_open();\n"
        "    if (ok != 0) return ok;\n"
        "    RtlmeterVortexCuResult r = rtlmeter_vortex_real_cuda_runtime.cuInit(0);\n"
        "    if (r != 0) return r;\n"
        "    RtlmeterVortexCuDevice dev = 0;\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuDeviceGet(&dev, 0);\n"
        "    if (r != 0) return r;\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuCtxCreate(&rtlmeter_vortex_real_cuda_runtime.context, 0, dev);\n"
        "    return r;\n"
        "}\n"
        "static void rtlmeter_vortex_real_cuda_context_close(void) {\n"
        "    if (rtlmeter_vortex_real_cuda_runtime.context != 0 && rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy != 0) {\n"
        "        (void)rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy(rtlmeter_vortex_real_cuda_runtime.context);\n"
        "        rtlmeter_vortex_real_cuda_runtime.context = 0;\n"
        "    }\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_real_cuda_alloc(VortexCuDeviceptr* out, size_t bytes) {\n"
        "    RtlmeterVortexCuDeviceptr ptr = 0;\n"
        "    RtlmeterVortexCuResult r = rtlmeter_vortex_real_cuda_runtime.cuMemAlloc(&ptr, bytes);\n"
        "    if (r == 0 && out != 0) *out = (VortexCuDeviceptr)ptr;\n"
        "    return (VortexCuResult)r;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_real_cuda_h2d(VortexCuDeviceptr dst, const void* src, size_t bytes) {\n"
        "    return (VortexCuResult)rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD((RtlmeterVortexCuDeviceptr)dst, src, bytes);\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_real_cuda_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {\n"
        "    return (VortexCuResult)rtlmeter_vortex_real_cuda_runtime.cuMemsetD8((RtlmeterVortexCuDeviceptr)dst, value, bytes);\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_real_cuda_free(VortexCuDeviceptr ptr) {\n"
        "    return (VortexCuResult)rtlmeter_vortex_real_cuda_runtime.cuMemFree((RtlmeterVortexCuDeviceptr)ptr);\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_real_cuda_d2h(void* dst, VortexCuDeviceptr src, size_t bytes) {\n"
        "    return (VortexCuResult)rtlmeter_vortex_real_cuda_runtime.cuMemcpyDtoH(dst, (RtlmeterVortexCuDeviceptr)src, bytes);\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_real_cuda_dcr(void* user, uint32_t addr, uint32_t value, int reset_asserted) {\n"
        "    (void)user; (void)addr; (void)value;\n"
        "    if (reset_asserted != 1) return 7003;\n"
        "    ++rtlmeter_vortex_real_cuda_runtime.dcr_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult rtlmeter_vortex_real_cuda_launch_root_storage_kernel(void* user, VortexRuntimeBuffer* buffers, unsigned buffer_count) {\n"
        "    if (buffers == 0 || buffer_count != 7) return 7004;\n"
        "    const RtlmeterVortexRootStorageImage* root_image = (const RtlmeterVortexRootStorageImage*)user;\n"
        "    const char* module_path = getenv(\"RTLMETER_VORTEX_VL_BATCH_GPU_MODULE\");\n"
        "    if (module_path == 0 || module_path[0] == '\\0') module_path = \"vl_batch_gpu.ptx\";\n"
        "    RtlmeterVortexCuModule module = 0;\n"
        "    RtlmeterVortexCuFunction fn = 0;\n"
        "    RtlmeterVortexCuDeviceptr rtlmeter_vortex_root_storage = 0;\n"
        "    const size_t storage_size = 80768u;\n"
        "    int nstates = 1;\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"before_cuModuleLoad\");\n"
        "    RtlmeterVortexCuResult r = rtlmeter_vortex_real_cuda_runtime.cuModuleLoad(&module, module_path);\n"
        "    if (r != 0) return (VortexCuResult)r;\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuModuleLoad\");\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction(&fn, module, \"vl_eval_batch_gpu\");\n"
        "    if (r != 0) { (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuModuleGetFunction\");\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuMemAlloc(&rtlmeter_vortex_root_storage, storage_size);\n"
        "    if (r != 0) { (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemAllocRootStorage\");\n"
        "    if (root_image != 0 && root_image->data != 0 && root_image->bytes == storage_size) {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuMemcpyHtoDRootStorage\");\n"
        "        unsigned char* relocated_root_image = (unsigned char*)malloc(storage_size);\n"
        "        if (relocated_root_image == 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=relocateRootStorage result=7006\\n\"); (void)rtlmeter_vortex_real_cuda_runtime.cuMemFree(rtlmeter_vortex_root_storage); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)7006; }\n"
        "        memcpy(relocated_root_image, root_image->data, storage_size);\n"
        "        const uintptr_t host_base = (uintptr_t)root_image->data;\n"
        "        const uintptr_t host_limit = host_base + storage_size;\n"
        "        const unsigned long long device_base = (unsigned long long)rtlmeter_vortex_root_storage;\n"
        "        size_t relocated_pointer_count = 0;\n"
        "        for (size_t off = 0; off + sizeof(unsigned long long) <= storage_size; off += sizeof(unsigned long long)) {\n"
        "            unsigned long long word = 0;\n"
        "            memcpy(&word, relocated_root_image + off, sizeof(word));\n"
        "            if (word >= (unsigned long long)host_base && word < (unsigned long long)host_limit) {\n"
        "                const unsigned long long relocated = device_base + (word - (unsigned long long)host_base);\n"
        "                memcpy(relocated_root_image + off, &relocated, sizeof(relocated));\n"
        "                ++relocated_pointer_count;\n"
        "            }\n"
        "        }\n"
        "        std::fprintf(stderr, \"rtlmeter_vortex_root_storage_relocation_count count=%zu\\n\", relocated_pointer_count);\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD(rtlmeter_vortex_root_storage, relocated_root_image, storage_size);\n"
        "        free(relocated_root_image);\n"
        "        if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemcpyHtoDRootStorage\");\n"
        "        if (r != 0) std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemcpyHtoDRootStorage result=%d\\n\", (int)r);\n"
        "    } else {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuMemsetRootStorage\");\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n"
        "        if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemsetRootStorage\");\n"
        "        if (r != 0) std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemsetRootStorage result=%d\\n\", (int)r);\n"
        "    }\n"
        "    if (r == 0) {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuLaunchKernel\");\n"
        "        void* params[] = {&rtlmeter_vortex_root_storage, &nstates};\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuLaunchKernel(fn, 1, 1, 1, 256, 1, 1, 0, 0, params, 0);\n"
        "    }\n"
        "    if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuLaunchKernel\");\n"
        "    if (r == 0) r = rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize();\n"
        "    if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuCtxSynchronize\");\n"
        "    (void)rtlmeter_vortex_real_cuda_runtime.cuMemFree(rtlmeter_vortex_root_storage);\n"
        "    (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module);\n"
        "    if (r != 0) return (VortexCuResult)r;\n"
        "    ++rtlmeter_vortex_real_cuda_runtime.kernel_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        f"{PATCH_END}\n\n"
    )


def _upgrade_existing_root_storage_callback(text: str) -> tuple[str, bool]:
    changed = False
    replacements = {
        "#include <dlfcn.h>\n": "#include <cstdio>\n#include <dlfcn.h>\n",
        "#include <stdint.h>\n": "#include <stdint.h>\n#include <string.h>\n",
        "static RtlmeterVortexRealCudaMaterializedRuntime rtlmeter_vortex_real_cuda_runtime;\n\n": (
            "static RtlmeterVortexRealCudaMaterializedRuntime rtlmeter_vortex_real_cuda_runtime;\n\n"
            "static void rtlmeter_vortex_root_storage_kernel_stage(const char* stage) {\n"
            "    std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_stage stage=%s\\n\", stage);\n"
            "    std::fflush(stderr);\n"
            "}\n"
        ),
        "typedef void* RtlmeterVortexCuContext;\n": (
            "typedef void* RtlmeterVortexCuContext;\n"
            "typedef void* RtlmeterVortexCuModule;\n"
            "typedef void* RtlmeterVortexCuFunction;\n"
            "typedef void* RtlmeterVortexCuStream;\n"
        ),
        "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuCtxDestroyFn)(RtlmeterVortexCuContext);\n": (
            "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuCtxDestroyFn)(RtlmeterVortexCuContext);\n"
            "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuCtxSynchronizeFn)(void);\n"
            "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuModuleLoadFn)(RtlmeterVortexCuModule*, const char*);\n"
            "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuModuleUnloadFn)(RtlmeterVortexCuModule);\n"
            "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuModuleGetFunctionFn)(RtlmeterVortexCuFunction*, RtlmeterVortexCuModule, const char*);\n"
            "typedef RtlmeterVortexCuResult (*RtlmeterVortexCuLaunchKernelFn)(RtlmeterVortexCuFunction, unsigned int, unsigned int, unsigned int, unsigned int, unsigned int, unsigned int, unsigned int, RtlmeterVortexCuStream, void**, void**);\n"
        ),
        "    RtlmeterVortexCuCtxDestroyFn cuCtxDestroy;\n": (
            "    RtlmeterVortexCuCtxDestroyFn cuCtxDestroy;\n"
            "    RtlmeterVortexCuCtxSynchronizeFn cuCtxSynchronize;\n"
            "    RtlmeterVortexCuModuleLoadFn cuModuleLoad;\n"
            "    RtlmeterVortexCuModuleUnloadFn cuModuleUnload;\n"
            "    RtlmeterVortexCuModuleGetFunctionFn cuModuleGetFunction;\n"
            "    RtlmeterVortexCuLaunchKernelFn cuLaunchKernel;\n"
        ),
        "    if (rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy == 0) rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy = (RtlmeterVortexCuCtxDestroyFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxDestroy\");\n": (
            "    if (rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy == 0) rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy = (RtlmeterVortexCuCtxDestroyFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxDestroy\");\n"
            "    rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize = (RtlmeterVortexCuCtxSynchronizeFn)rtlmeter_vortex_real_cuda_sym(\"cuCtxSynchronize\");\n"
            "    rtlmeter_vortex_real_cuda_runtime.cuModuleLoad = (RtlmeterVortexCuModuleLoadFn)rtlmeter_vortex_real_cuda_sym(\"cuModuleLoad\");\n"
            "    rtlmeter_vortex_real_cuda_runtime.cuModuleUnload = (RtlmeterVortexCuModuleUnloadFn)rtlmeter_vortex_real_cuda_sym(\"cuModuleUnload\");\n"
            "    rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction = (RtlmeterVortexCuModuleGetFunctionFn)rtlmeter_vortex_real_cuda_sym(\"cuModuleGetFunction\");\n"
            "    rtlmeter_vortex_real_cuda_runtime.cuLaunchKernel = (RtlmeterVortexCuLaunchKernelFn)rtlmeter_vortex_real_cuda_sym(\"cuLaunchKernel\");\n"
        ),
        "    if (!rtlmeter_vortex_real_cuda_runtime.cuInit || !rtlmeter_vortex_real_cuda_runtime.cuDeviceGet || !rtlmeter_vortex_real_cuda_runtime.cuCtxCreate || !rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy || !rtlmeter_vortex_real_cuda_runtime.cuMemAlloc || !rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD || !rtlmeter_vortex_real_cuda_runtime.cuMemcpyDtoH || !rtlmeter_vortex_real_cuda_runtime.cuMemsetD8 || !rtlmeter_vortex_real_cuda_runtime.cuMemFree) return 7002;\n": (
            "    if (!rtlmeter_vortex_real_cuda_runtime.cuInit || !rtlmeter_vortex_real_cuda_runtime.cuDeviceGet || !rtlmeter_vortex_real_cuda_runtime.cuCtxCreate || !rtlmeter_vortex_real_cuda_runtime.cuCtxDestroy || !rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize || !rtlmeter_vortex_real_cuda_runtime.cuModuleLoad || !rtlmeter_vortex_real_cuda_runtime.cuModuleUnload || !rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction || !rtlmeter_vortex_real_cuda_runtime.cuLaunchKernel || !rtlmeter_vortex_real_cuda_runtime.cuMemAlloc || !rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD || !rtlmeter_vortex_real_cuda_runtime.cuMemcpyDtoH || !rtlmeter_vortex_real_cuda_runtime.cuMemsetD8 || !rtlmeter_vortex_real_cuda_runtime.cuMemFree) return 7002;\n"
        ),
        "    int nstates = 1;\n"
        "    RtlmeterVortexCuResult r = rtlmeter_vortex_real_cuda_runtime.cuModuleLoad(&module, module_path);\n": (
            "    int nstates = 1;\n"
            "    rtlmeter_vortex_root_storage_kernel_stage(\"before_cuModuleLoad\");\n"
            "    RtlmeterVortexCuResult r = rtlmeter_vortex_real_cuda_runtime.cuModuleLoad(&module, module_path);\n"
        ),
        "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuModuleLoad result=%d\\n\", (int)r); return (VortexCuResult)r; }\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction(&fn, module, \"vl_eval_batch_gpu\");\n": (
            "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuModuleLoad result=%d\\n\", (int)r); return (VortexCuResult)r; }\n"
            "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuModuleLoad\");\n"
            "    r = rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction(&fn, module, \"vl_eval_batch_gpu\");\n"
        ),
        "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuModuleGetFunction result=%d\\n\", (int)r); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuMemAlloc(&rtlmeter_vortex_root_storage, storage_size);\n": (
            "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuModuleGetFunction result=%d\\n\", (int)r); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
            "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuModuleGetFunction\");\n"
            "    r = rtlmeter_vortex_real_cuda_runtime.cuMemAlloc(&rtlmeter_vortex_root_storage, storage_size);\n"
        ),
        "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemAllocRootStorage result=%d\\n\", (int)r); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n": (
            "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemAllocRootStorage result=%d\\n\", (int)r); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
            "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemAllocRootStorage\");\n"
            "    r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n"
        ),
        "    if (r == 0) {\n"
        "        void* params[] = {&rtlmeter_vortex_root_storage, &nstates};\n": (
            "    if (r == 0) {\n"
            "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuLaunchKernel\");\n"
            "        void* params[] = {&rtlmeter_vortex_root_storage, &nstates};\n"
        ),
        "    }\n"
        "    if (r == 0) r = rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize();\n": (
            "    }\n"
            "    if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuLaunchKernel\");\n"
            "    if (r == 0) r = rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize();\n"
            "    if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuCtxSynchronize\");\n"
        ),
    }
    for old, new in replacements.items():
        if old in text and new not in text:
            text = text.replace(old, new, 1)
            changed = True
    old_noop = (
        "static VortexCuResult rtlmeter_vortex_real_cuda_noop_kernel(void* user, VortexRuntimeBuffer* buffers, unsigned buffer_count) {\n"
        "    (void)user;\n"
        "    if (buffers == 0 || buffer_count != 7) return 7004;\n"
        "    ++rtlmeter_vortex_real_cuda_runtime.kernel_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
    )
    new_callback = (
        "static VortexCuResult rtlmeter_vortex_real_cuda_launch_root_storage_kernel(void* user, VortexRuntimeBuffer* buffers, unsigned buffer_count) {\n"
        "    if (buffers == 0 || buffer_count != 7) return 7004;\n"
        "    const RtlmeterVortexRootStorageImage* root_image = (const RtlmeterVortexRootStorageImage*)user;\n"
        "    const char* module_path = getenv(\"RTLMETER_VORTEX_VL_BATCH_GPU_MODULE\");\n"
        "    if (module_path == 0 || module_path[0] == '\\0') module_path = \"vl_batch_gpu.ptx\";\n"
        "    RtlmeterVortexCuModule module = 0;\n"
        "    RtlmeterVortexCuFunction fn = 0;\n"
        "    RtlmeterVortexCuDeviceptr rtlmeter_vortex_root_storage = 0;\n"
        "    const size_t storage_size = 80768u;\n"
        "    int nstates = 1;\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"before_cuModuleLoad\");\n"
        "    RtlmeterVortexCuResult r = rtlmeter_vortex_real_cuda_runtime.cuModuleLoad(&module, module_path);\n"
        "    if (r != 0) return (VortexCuResult)r;\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuModuleLoad\");\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction(&fn, module, \"vl_eval_batch_gpu\");\n"
        "    if (r != 0) { (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuModuleGetFunction\");\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuMemAlloc(&rtlmeter_vortex_root_storage, storage_size);\n"
        "    if (r != 0) { (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemAllocRootStorage\");\n"
        "    if (root_image != 0 && root_image->data != 0 && root_image->bytes == storage_size) {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuMemcpyHtoDRootStorage\");\n"
        "        unsigned char* relocated_root_image = (unsigned char*)malloc(storage_size);\n"
        "        if (relocated_root_image == 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=relocateRootStorage result=7006\\n\"); (void)rtlmeter_vortex_real_cuda_runtime.cuMemFree(rtlmeter_vortex_root_storage); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)7006; }\n"
        "        memcpy(relocated_root_image, root_image->data, storage_size);\n"
        "        const uintptr_t host_base = (uintptr_t)root_image->data;\n"
        "        const uintptr_t host_limit = host_base + storage_size;\n"
        "        const unsigned long long device_base = (unsigned long long)rtlmeter_vortex_root_storage;\n"
        "        size_t relocated_pointer_count = 0;\n"
        "        for (size_t off = 0; off + sizeof(unsigned long long) <= storage_size; off += sizeof(unsigned long long)) {\n"
        "            unsigned long long word = 0;\n"
        "            memcpy(&word, relocated_root_image + off, sizeof(word));\n"
        "            if (word >= (unsigned long long)host_base && word < (unsigned long long)host_limit) {\n"
        "                const unsigned long long relocated = device_base + (word - (unsigned long long)host_base);\n"
        "                memcpy(relocated_root_image + off, &relocated, sizeof(relocated));\n"
        "                ++relocated_pointer_count;\n"
        "            }\n"
        "        }\n"
        "        std::fprintf(stderr, \"rtlmeter_vortex_root_storage_relocation_count count=%zu\\n\", relocated_pointer_count);\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD(rtlmeter_vortex_root_storage, relocated_root_image, storage_size);\n"
        "        free(relocated_root_image);\n"
        "        if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemcpyHtoDRootStorage\");\n"
        "        if (r != 0) std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemcpyHtoDRootStorage result=%d\\n\", (int)r);\n"
        "    } else {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuMemsetRootStorage\");\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n"
        "        if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemsetRootStorage\");\n"
        "        if (r != 0) std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemsetRootStorage result=%d\\n\", (int)r);\n"
        "    }\n"
        "    if (r == 0) {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuLaunchKernel\");\n"
        "        void* params[] = {&rtlmeter_vortex_root_storage, &nstates};\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuLaunchKernel(fn, 1, 1, 1, 256, 1, 1, 0, 0, params, 0);\n"
        "    }\n"
        "    if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuLaunchKernel\");\n"
        "    if (r == 0) r = rtlmeter_vortex_real_cuda_runtime.cuCtxSynchronize();\n"
        "    if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuCtxSynchronize\");\n"
        "    (void)rtlmeter_vortex_real_cuda_runtime.cuMemFree(rtlmeter_vortex_root_storage);\n"
        "    (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module);\n"
        "    if (r != 0) return (VortexCuResult)r;\n"
        "    ++rtlmeter_vortex_real_cuda_runtime.kernel_count;\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
    )
    if old_noop in text:
        text = text.replace(old_noop, new_callback, 1)
        changed = True
    if "rtlmeter_vortex_real_cuda_noop_kernel, 0," in text:
        text = text.replace(
            "rtlmeter_vortex_real_cuda_noop_kernel, 0,",
            "rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0,",
            1,
        )
        changed = True
    if "RtlmeterVortexRootStorageImage" not in text and "static RtlmeterVortexRealCudaMaterializedRuntime rtlmeter_vortex_real_cuda_runtime;\n" in text:
        text = text.replace(
            "static RtlmeterVortexRealCudaMaterializedRuntime rtlmeter_vortex_real_cuda_runtime;\n",
            "typedef struct {\n"
            "    const void* data;\n"
            "    size_t bytes;\n"
            "} RtlmeterVortexRootStorageImage;\n\n"
            "static RtlmeterVortexRealCudaMaterializedRuntime rtlmeter_vortex_real_cuda_runtime;\n",
            1,
        )
        changed = True
    if "    (void)user;\n    if (buffers == 0 || buffer_count != 7) return 7004;\n" in text:
        text = text.replace(
            "    (void)user;\n    if (buffers == 0 || buffer_count != 7) return 7004;\n",
            "    if (buffers == 0 || buffer_count != 7) return 7004;\n"
            "    const RtlmeterVortexRootStorageImage* root_image = (const RtlmeterVortexRootStorageImage*)user;\n",
            1,
        )
        changed = True
    zero_init = "    r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n"
    image_upload = (
        "    if (root_image != 0 && root_image->data != 0 && root_image->bytes == storage_size) {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuMemcpyHtoDRootStorage\");\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD(rtlmeter_vortex_root_storage, root_image->data, storage_size);\n"
        "        if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemcpyHtoDRootStorage\");\n"
        "        if (r != 0) std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemcpyHtoDRootStorage result=%d\\n\", (int)r);\n"
        "    } else {\n"
        "        rtlmeter_vortex_root_storage_kernel_stage(\"before_cuMemsetRootStorage\");\n"
        "        r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n"
        "        if (r == 0) rtlmeter_vortex_root_storage_kernel_stage(\"after_cuMemsetRootStorage\");\n"
        "        if (r != 0) std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemsetRootStorage result=%d\\n\", (int)r);\n"
        "    }\n"
    )
    if zero_init in text and "before_cuMemcpyHtoDRootStorage" not in text:
        text = text.replace(zero_init, image_upload, 1)
        changed = True
    if (
        "r = rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD(rtlmeter_vortex_root_storage, root_image->data, storage_size);\n"
        in text
        and "relocated_root_image" not in text
    ):
        text = text.replace(
            "        r = rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD(rtlmeter_vortex_root_storage, root_image->data, storage_size);\n",
            "        unsigned char* relocated_root_image = (unsigned char*)malloc(storage_size);\n"
            "        if (relocated_root_image == 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=relocateRootStorage result=7006\\n\"); (void)rtlmeter_vortex_real_cuda_runtime.cuMemFree(rtlmeter_vortex_root_storage); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)7006; }\n"
            "        memcpy(relocated_root_image, root_image->data, storage_size);\n"
            "        const uintptr_t host_base = (uintptr_t)root_image->data;\n"
            "        const uintptr_t host_limit = host_base + storage_size;\n"
            "        const unsigned long long device_base = (unsigned long long)rtlmeter_vortex_root_storage;\n"
            "        size_t relocated_pointer_count = 0;\n"
            "        for (size_t off = 0; off + sizeof(unsigned long long) <= storage_size; off += sizeof(unsigned long long)) {\n"
            "            unsigned long long word = 0;\n"
            "            memcpy(&word, relocated_root_image + off, sizeof(word));\n"
            "            if (word >= (unsigned long long)host_base && word < (unsigned long long)host_limit) {\n"
            "                const unsigned long long relocated = device_base + (word - (unsigned long long)host_base);\n"
            "                memcpy(relocated_root_image + off, &relocated, sizeof(relocated));\n"
            "                ++relocated_pointer_count;\n"
            "            }\n"
            "        }\n"
            "        std::fprintf(stderr, \"rtlmeter_vortex_root_storage_relocation_count count=%zu\\n\", relocated_pointer_count);\n"
            "        r = rtlmeter_vortex_real_cuda_runtime.cuMemcpyHtoD(rtlmeter_vortex_root_storage, relocated_root_image, storage_size);\n"
            "        free(relocated_root_image);\n",
            1,
        )
        changed = True
    if "static int rtlmeter_vortex_materialized_runtime_args_probe() {" in text:
        text = text.replace(
            "static int rtlmeter_vortex_materialized_runtime_args_probe() {",
            "static int rtlmeter_vortex_materialized_runtime_args_probe(Vsim* topp) {",
            1,
        )
        changed = True
    if "RtlmeterVortexRootStorageImage root_image = {" not in text and "    int rtlmeter_vortex_real_cuda_status = rtlmeter_vortex_real_cuda_context_open();\n" in text:
        text = text.replace(
            "    int rtlmeter_vortex_real_cuda_status = rtlmeter_vortex_real_cuda_context_open();\n"
            "    if (rtlmeter_vortex_real_cuda_status != 0) return rtlmeter_vortex_real_cuda_status;\n",
            "    if (topp == 0 || topp->rootp == 0) return 7005;\n"
            "    RtlmeterVortexRootStorageImage root_image = {\n"
            "        reinterpret_cast<const unsigned char*>(topp->rootp) - 192u,\n"
            "        80768u\n"
            "    };\n"
            "    int rtlmeter_vortex_real_cuda_status = rtlmeter_vortex_real_cuda_context_open();\n"
            "    if (rtlmeter_vortex_real_cuda_status != 0) return rtlmeter_vortex_real_cuda_status;\n",
            1,
        )
        changed = True
    if "rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0," in text:
        text = text.replace(
            "rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0,",
            "rtlmeter_vortex_real_cuda_launch_root_storage_kernel, &root_image,",
            1,
        )
        changed = True
    if MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC_NO_MODEL in text:
        text = text.replace(MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC_NO_MODEL, MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC, 1)
        changed = True
    if MATERIALIZED_ARGS_PROBE_CALL_OLD in text:
        text = text.replace(MATERIALIZED_ARGS_PROBE_CALL_OLD, MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC, 1)
        changed = True
    diagnostic_replacements = {
        "    if (r != 0) return (VortexCuResult)r;\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction(&fn, module, \"vl_eval_batch_gpu\");\n": (
            "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuModuleLoad result=%d\\n\", (int)r); return (VortexCuResult)r; }\n"
            "    r = rtlmeter_vortex_real_cuda_runtime.cuModuleGetFunction(&fn, module, \"vl_eval_batch_gpu\");\n"
        ),
        "    if (r != 0) { (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuMemAlloc(&rtlmeter_vortex_root_storage, storage_size);\n": (
            "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuModuleGetFunction result=%d\\n\", (int)r); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
            "    r = rtlmeter_vortex_real_cuda_runtime.cuMemAlloc(&rtlmeter_vortex_root_storage, storage_size);\n"
        ),
        "    if (r != 0) { (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
        "    r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n": (
            "    if (r != 0) { std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuMemAllocRootStorage result=%d\\n\", (int)r); (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module); return (VortexCuResult)r; }\n"
            "    r = rtlmeter_vortex_real_cuda_runtime.cuMemsetD8(rtlmeter_vortex_root_storage, 0, storage_size);\n"
        ),
        "    (void)rtlmeter_vortex_real_cuda_runtime.cuMemFree(rtlmeter_vortex_root_storage);\n"
        "    (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module);\n"
        "    if (r != 0) return (VortexCuResult)r;\n": (
            "    if (r != 0) std::fprintf(stderr, \"rtlmeter_vortex_root_storage_kernel_failed stage=cuLaunchOrSync result=%d\\n\", (int)r);\n"
            "    (void)rtlmeter_vortex_real_cuda_runtime.cuMemFree(rtlmeter_vortex_root_storage);\n"
            "    (void)rtlmeter_vortex_real_cuda_runtime.cuModuleUnload(module);\n"
            "    if (r != 0) return (VortexCuResult)r;\n"
        ),
    }
    for old, new in diagnostic_replacements.items():
        if old in text and new not in text:
            text = text.replace(old, new, 1)
            changed = True
    old_failure = "    if (result != VORTEX_CUDA_SUCCESS) return 30;\n"
    if old_failure in text and SEQUENCE_FAILURE_DIAGNOSTIC not in text:
        text = text.replace(old_failure, SEQUENCE_FAILURE_DIAGNOSTIC, 1)
        changed = True
    authority_anchor = (
        "    if (sequence_summary.buffers_released != 1) return 37;\n"
        "    return 0;\n"
    )
    if AUTHORITY_DIAGNOSTIC_PREFIX not in text and authority_anchor in text:
        text = text.replace(
            authority_anchor,
            "    if (sequence_summary.buffers_released != 1) return 37;\n"
            + AUTHORITY_DIAGNOSTIC
            + "    return 0;\n",
            1,
        )
        changed = True
    compact_authority_anchor = (
        "    if (sequence_summary.observable_export_invoked != 1 || sequence_summary.buffers_released != 1) return 34;\n"
        "    return 0;\n"
    )
    if AUTHORITY_DIAGNOSTIC_PREFIX not in text and compact_authority_anchor in text:
        text = text.replace(
            compact_authority_anchor,
            "    if (sequence_summary.observable_export_invoked != 1 || sequence_summary.buffers_released != 1) return 34;\n"
            + AUTHORITY_DIAGNOSTIC
            + "    return 0;\n",
            1,
        )
        changed = True
    result_return_anchor = "    return result;\n"
    if AUTHORITY_DIAGNOSTIC_PREFIX not in text and result_return_anchor in text:
        text = text.replace(
            result_return_anchor,
            "    if (result == VORTEX_CUDA_SUCCESS) {\n"
            + AUTHORITY_DIAGNOSTIC
            + "    }\n"
            + result_return_anchor,
            1,
        )
        changed = True
    return text, changed


def _report(
    status: str,
    main_cpp: Path,
    repo_root: Path | None,
    applied: bool,
    *,
    diagnostic_applied: bool = False,
    missing: list[str] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch",
        "status": status,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "real_cuda_materialized_runtime_patch_applied": applied,
        "materialized_runtime_args_status_diagnostic_applied": diagnostic_applied,
        "root_storage_kernel_callback_wired": applied and not (missing and "root_storage_kernel_callback" in missing),
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_patch_context": missing or [],
        "non_claims": [
            "real_cuda_driver_api_boundary_is_not_vortex_kernel_execution",
            "root_storage_kernel_callback_is_not_observable_authority",
            "not_runtime_observable_authority",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def patch_real_cuda_materialized_runtime(*, main_cpp: Path, repo_root: Path | None = None) -> dict[str, object]:
    if main_cpp.name != "Vsim__main.cpp" or main_cpp.parent.name != "obj_dir":
        return _report(STATUS_UNSUPPORTED, main_cpp, repo_root, False, missing=["rtlmeter_vsim_main_path"])
    if not main_cpp.is_file():
        return _report(STATUS_MISSING, main_cpp, repo_root, False, missing=["main_cpp"])
    text = main_cpp.read_text(encoding="utf-8")
    if PATCH_BEGIN in text and PATCH_END in text:
        upgraded_text, upgraded_callback = _upgrade_existing_root_storage_callback(text)
        if upgraded_callback:
            main_cpp.write_text(upgraded_text, encoding="utf-8")
            return _report(
                STATUS_PATCHED,
                main_cpp,
                repo_root,
                True,
                diagnostic_applied=MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC in upgraded_text,
            )
        if MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC in text:
            return _report(
                STATUS_ALREADY_PATCHED,
                main_cpp,
                repo_root,
                True,
                diagnostic_applied=True,
            )
        if MATERIALIZED_ARGS_PROBE_CALL_OLD in text:
            patched = text.replace(
                MATERIALIZED_ARGS_PROBE_CALL_OLD,
                MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC,
                1,
            )
            main_cpp.write_text(patched, encoding="utf-8")
            return _report(
                STATUS_PATCHED,
                main_cpp,
                repo_root,
                True,
                diagnostic_applied=True,
            )
        return _report(
            STATUS_UNSUPPORTED,
            main_cpp,
            repo_root,
            True,
            missing=["materialized_runtime_args_probe_call"],
        )
    missing = []
    if INCLUDE_ANCHOR not in text:
        missing.append("include_anchor")
    if MATERIALIZED_ARGS_PROBE_BEGIN not in text:
        missing.append("materialized_runtime_args_probe")
    for source in REQUIRED_FAKE_SYMBOLS:
        if source not in text:
            missing.append(source)
    if missing:
        return _report(STATUS_UNSUPPORTED, main_cpp, repo_root, False, missing=missing)

    patched = text.replace(INCLUDE_ANCHOR, INCLUDE_ANCHOR + _real_cuda_block(), 1)
    patched = patched.replace(
        "        rtlmeter_vortex_runtime_args_probe_alloc,\n"
        "        rtlmeter_vortex_runtime_args_probe_h2d,\n"
        "        rtlmeter_vortex_runtime_args_probe_memset,\n"
        "        rtlmeter_vortex_runtime_args_probe_free\n",
        "        rtlmeter_vortex_real_cuda_alloc,\n"
        "        rtlmeter_vortex_real_cuda_h2d,\n"
        "        rtlmeter_vortex_real_cuda_memset,\n"
        "        rtlmeter_vortex_real_cuda_free\n",
        1,
    )
    patched = patched.replace(
        "    VortexObservableExportDriver export_driver = {rtlmeter_vortex_runtime_args_probe_dtoh};\n",
        "    VortexObservableExportDriver export_driver = {rtlmeter_vortex_real_cuda_d2h};\n",
        1,
    )
    patched = patched.replace(
        "        rtlmeter_vortex_runtime_args_probe_dcr, 0,\n"
        "        rtlmeter_vortex_runtime_args_probe_kernel, 0,\n",
        "        rtlmeter_vortex_real_cuda_dcr, 0,\n"
        "        rtlmeter_vortex_real_cuda_launch_root_storage_kernel, &root_image,\n",
        1,
    )
    open_call = "    memset(&rtlmeter_vortex_real_cuda_runtime, 0, sizeof(rtlmeter_vortex_real_cuda_runtime));\n    int rtlmeter_vortex_real_cuda_status = rtlmeter_vortex_real_cuda_context_open();\n    if (rtlmeter_vortex_real_cuda_status != 0) return rtlmeter_vortex_real_cuda_status;\n"
    patched = patched.replace(
        "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n",
        "static int rtlmeter_vortex_materialized_runtime_args_probe(Vsim* topp) {\n"
        "    if (topp == 0 || topp->rootp == 0) return 7005;\n"
        "    RtlmeterVortexRootStorageImage root_image = {\n"
        "        reinterpret_cast<const unsigned char*>(topp->rootp) - 192u,\n"
        "        80768u\n"
        "    };\n"
        + open_call,
        1,
    )
    patched = patched.replace(
        "    for (unsigned i = 0; i < 5; ++i) { free((void*)buffers[i].host_data); buffers[i].host_data = 0; }\n",
        "    for (unsigned i = 0; i < 5; ++i) { free((void*)buffers[i].host_data); buffers[i].host_data = 0; }\n"
        "    rtlmeter_vortex_real_cuda_context_close();\n",
        1,
    )
    patched, _ = _upgrade_existing_root_storage_callback(patched)
    patched = patched.replace(
        MATERIALIZED_ARGS_PROBE_CALL_OLD,
        MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC,
        1,
    )
    main_cpp.write_text(patched, encoding="utf-8")
    return _report(
        STATUS_PATCHED,
        main_cpp,
        repo_root,
        True,
        diagnostic_applied=MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC in patched,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--main-cpp", default=DEFAULT_MAIN_CPP.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch.json")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    main_cpp = Path(args.main_cpp)
    if not main_cpp.is_absolute():
        main_cpp = repo_root / main_cpp
    report = patch_real_cuda_materialized_runtime(main_cpp=main_cpp, repo_root=repo_root)
    if args.write_report:
        report_out = Path(args.report_out)
        if not report_out.is_absolute():
            report_out = repo_root / report_out
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {STATUS_PATCHED, STATUS_ALREADY_PATCHED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
