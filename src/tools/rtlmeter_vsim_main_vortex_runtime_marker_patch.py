"""Patch generated Vortex Vsim main with a fail-closed runtime-sequence marker."""

from __future__ import annotations

from pathlib import Path


PATCH_BEGIN = "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_BEGIN */"
PATCH_END = "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_END */"
INSERT_ANCHOR = "    // Construct the Verilated model, from Vtop.h generated from Verilating"
REQUIRED_SENTINELS = (
    "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
    '#include "verilated.h"',
    '#include "Vsim.h"',
    "int main(int argc, char** argv, char**) {",
    "contextp->commandArgs(argc, argv);",
    "while (VL_LIKELY(!contextp->gotFinish())) {",
    "topp->eval();",
    "topp->final();",
)
STATUS_PATCHED = "rtlmeter_vsim_main_vortex_runtime_marker_patch_applied"
STATUS_ALREADY_PATCHED = "rtlmeter_vsim_main_vortex_runtime_marker_patch_already_present"
STATUS_MISSING = "rtlmeter_vsim_main_vortex_runtime_marker_patch_missing_source"
STATUS_UNSUPPORTED = "rtlmeter_vsim_main_vortex_runtime_marker_patch_unsupported_source"


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def _marker_block() -> str:
    return (
        f"    {PATCH_BEGIN}\n"
        "    /* schema_version=1 */\n"
        "    /* producer=rtlmeter_vsim_main_vortex_runtime_marker_patch */\n"
        "    /* runtime_authority=false timing_measured=false speedup_claimed=false */\n"
        "    /* generated_main_runtime_sequence_marker=true */\n"
        "    /* next_call_boundary=vortex_lowered_tb_invoke_runtime_sequence */\n"
        "    /* next_memory_boundary=vortex_mem_access_device_helper */\n"
        "    /* next_authority_boundary=vortex_export_observables */\n"
        f"    {PATCH_END}\n"
    )


def _unsupported(main_cpp: Path, repo_root: Path | None, missing: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_runtime_marker_patch",
        "status": STATUS_UNSUPPORTED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "marker_applied": False,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_patch_context": missing,
    }


def patch_vortex_runtime_sequence_marker(*, main_cpp: Path, repo_root: Path | None = None) -> dict[str, object]:
    if main_cpp.name != "Vsim__main.cpp" or main_cpp.parent.name != "obj_dir":
        return _unsupported(main_cpp, repo_root, ["rtlmeter_vsim_main_path"])
    if not main_cpp.is_file():
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_vortex_runtime_marker_patch",
            "status": STATUS_MISSING,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "marker_applied": False,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
            "missing_patch_context": ["main_cpp"],
        }

    text = main_cpp.read_text(encoding="utf-8")
    begin_count = text.count(PATCH_BEGIN)
    end_count = text.count(PATCH_END)
    if begin_count == 1 and end_count == 1:
        return {
            "schema_version": 1,
            "surface": "rtlmeter_vsim_main_vortex_runtime_marker_patch",
            "status": STATUS_ALREADY_PATCHED,
            "main_cpp": _relative_path(main_cpp, repo_root),
            "marker_applied": True,
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
            "missing_patch_context": [],
        }
    if begin_count or end_count:
        return _unsupported(main_cpp, repo_root, ["vortex_runtime_marker_patch_markers"])
    missing = [sentinel for sentinel in REQUIRED_SENTINELS if text.count(sentinel) != 1]
    if INSERT_ANCHOR not in text:
        missing.append("construct_model_anchor")
    if missing:
        return _unsupported(main_cpp, repo_root, missing)

    patched = text.replace(INSERT_ANCHOR, _marker_block() + INSERT_ANCHOR, 1)
    main_cpp.write_text(patched, encoding="utf-8")
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vsim_main_vortex_runtime_marker_patch",
        "status": STATUS_PATCHED,
        "main_cpp": _relative_path(main_cpp, repo_root),
        "marker_applied": True,
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_patch_context": [],
    }
