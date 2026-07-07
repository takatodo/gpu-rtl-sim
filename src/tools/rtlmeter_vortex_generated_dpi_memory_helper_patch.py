#!/usr/bin/env python3
"""Patch generated Vortex DPI mem_access wrapper with a helper shadow call."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ROOT_CPP = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/Vsim___024root__0.cpp"
)
DEFAULT_REPO_ROOT_RELATIVE_FROM_OBJ_DIR = "../../../../../../.."
INCLUDE_SENTINEL = "RTLMETER_VORTEX_DPI_MEMORY_HELPER_INCLUDE"
CALL_BEGIN = "/* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */"
CALL_END = "/* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */"
STATUS_PATCHED = "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied"
STATUS_ALREADY_PATCHED = "rtlmeter_vortex_generated_dpi_memory_helper_patch_already_present"
STATUS_MISSING = "rtlmeter_vortex_generated_dpi_memory_helper_patch_missing_source"
STATUS_UNSUPPORTED = "rtlmeter_vortex_generated_dpi_memory_helper_patch_unsupported_source"


@dataclass(frozen=True)
class PatchContext:
    root_cpp: Path
    repo_root: Path | None = None
    repo_root_relative_from_obj_dir: str = DEFAULT_REPO_ROOT_RELATIVE_FROM_OBJ_DIR


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def _unsupported(ctx: PatchContext, missing: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_generated_dpi_memory_helper_patch",
        "status": STATUS_UNSUPPORTED,
        "root_cpp": _relative_path(ctx.root_cpp, ctx.repo_root),
        "generated_dpi_memory_helper_patch_applied": False,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_patch_context": missing,
    }


def _include_block(root_rel: str) -> str:
    return (
        f"/* {INCLUDE_SENTINEL} */\n"
        f'#include "{root_rel}/src/hybrid/vortex_memory_model_device.h"\n'
    )


def _shadow_call_block() -> str:
    return (
        f"    {CALL_BEGIN}\n"
        "    VortexMemBlock rtlmeter_vortex_shadow_blocks[1];\n"
        "    rtlmeter_vortex_shadow_blocks[0].block_addr = req_addr__Vcvt;\n"
        "    for (unsigned rtlmeter_lane = 0; rtlmeter_lane < VORTEX_MEM_BLOCK_SIZE; ++rtlmeter_lane) {\n"
        "        rtlmeter_vortex_shadow_blocks[0].data[rtlmeter_lane] = 0;\n"
        "    }\n"
        "    uint8_t rtlmeter_vortex_shadow_rsp[VORTEX_MEM_BLOCK_SIZE];\n"
        "    vortex_mem_access_device_helper(\n"
        "        (uint8_t)req_rw__Vcvt,\n"
        "        (uint64_t)req_byteen__Vcvt,\n"
        "        (uint64_t)req_addr__Vcvt,\n"
        "        (const uint8_t*)req_data__Vcvt,\n"
        "        rtlmeter_vortex_shadow_rsp,\n"
        "        rtlmeter_vortex_shadow_blocks,\n"
        "        1u,\n"
        "        0);\n"
        f"    {CALL_END}\n"
    )


def patch_generated_dpi_memory_helper(ctx: PatchContext) -> dict[str, object]:
    if not ctx.root_cpp.is_file():
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vortex_generated_dpi_memory_helper_patch",
            "status": STATUS_MISSING,
            "root_cpp": _relative_path(ctx.root_cpp, ctx.repo_root),
            "generated_dpi_memory_helper_patch_applied": False,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
        }
    text = ctx.root_cpp.read_text(encoding="utf-8")
    if CALL_BEGIN in text:
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vortex_generated_dpi_memory_helper_patch",
            "status": STATUS_ALREADY_PATCHED,
            "root_cpp": _relative_path(ctx.root_cpp, ctx.repo_root),
            "generated_dpi_memory_helper_patch_applied": True,
            "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
        }
    missing = []
    include_anchor = '#include "Vsim__pch.h"\n'
    call_anchor = "    mem_access(req_rw__Vcvt, req_byteen__Vcvt, req_addr__Vcvt, req_data__Vcvt, rsp_data__Vcvt);\n"
    required = [
        "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP",
        "svBit req_rw__Vcvt;",
        "unsigned long long req_byteen__Vcvt;",
        "unsigned long long req_addr__Vcvt;",
        "svBitVecVal req_data__Vcvt[16];",
        call_anchor.strip(),
    ]
    for item in required:
        if item not in text:
            missing.append(item)
    if include_anchor not in text:
        missing.append(include_anchor.strip())
    if missing:
        return _unsupported(ctx, missing)

    patched = text.replace(
        include_anchor,
        include_anchor + "\n" + _include_block(ctx.repo_root_relative_from_obj_dir),
        1,
    ).replace(call_anchor, _shadow_call_block() + call_anchor, 1)
    ctx.root_cpp.write_text(patched, encoding="utf-8")
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_generated_dpi_memory_helper_patch",
        "status": STATUS_PATCHED,
        "root_cpp": _relative_path(ctx.root_cpp, ctx.repo_root),
        "generated_dpi_memory_helper_patch_applied": True,
        "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "shadow_call_only",
            "cpu_dpi_mem_access_still_authoritative",
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--root-cpp", default=DEFAULT_ROOT_CPP.as_posix())
    parser.add_argument("--repo-root-relative-from-obj-dir", default=DEFAULT_REPO_ROOT_RELATIVE_FROM_OBJ_DIR)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_generated_dpi_memory_helper_patch.json")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    root_cpp = Path(args.root_cpp)
    if not root_cpp.is_absolute():
        root_cpp = repo_root / root_cpp
    report = patch_generated_dpi_memory_helper(
        PatchContext(
            root_cpp=root_cpp,
            repo_root=repo_root,
            repo_root_relative_from_obj_dir=args.repo_root_relative_from_obj_dir,
        )
    )
    if args.write_report:
        out = Path(args.report_out)
        if not out.is_absolute():
            out = repo_root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {STATUS_PATCHED, STATUS_ALREADY_PATCHED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
