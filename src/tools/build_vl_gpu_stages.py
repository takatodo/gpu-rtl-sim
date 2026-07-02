"""Stage wrappers that bind build_vl_gpu defaults to shared helpers."""

from pathlib import Path

from build_vl_gpu_compile import compile_ll, compile_verilator_ir as compile_verilator_ir_impl
from build_vl_gpu_gpu_ir import (
    optimize_gpu_ir_to_ptx as optimize_gpu_ir_to_ptx_impl,
    prepare_gpu_patched_ir as prepare_gpu_patched_ir_impl,
)
from build_vl_gpu_inputs import (
    CLANG,
    CXX_STANDARD,
    LLC,
    LLVMLINK,
    OPT,
    PTXAS,
    verilator_include_dir,
    verilator_vltstd_include_dir,
)
from build_vl_gpu_lifetime import maybe_prepare_gpu_lifetime_retiming_input
from build_vl_gpu_output import assemble_output_module as assemble_output_module_impl
from build_vl_gpu_state import (
    load_launch_sequence_from_manifest,
    reuse_launch_sequence,
)
from build_vl_gpu_workarounds import maybe_prepare_gpu_opt_input
from build_vl_gpu_stage_env import PASSES_DIR, PASSES_SO, VLGPUGEN, ensure_pass_tools_built, run
from build_vl_gpu_stage_metadata import analyze_phase_ir, resolve_build_storage_size


def compile_verilator_ir(
    *,
    mdir: Path,
    all_classes: list[str],
    force: bool,
    clang_changed: bool,
    clang_opt: str,
    jobs: int,
) -> Path:
    vl_inc = verilator_include_dir()
    vl_vltstd_inc = verilator_vltstd_include_dir()

    def compile_one(cpp_path: Path, out_ll: Path) -> None:
        compile_ll(
            cpp_path,
            mdir,
            out_ll,
            clang_opt=clang_opt,
            clang=CLANG,
            cxx_standard=CXX_STANDARD,
            verilator_include=vl_inc,
            verilator_vltstd_include=vl_vltstd_inc,
            run_command=run,
        )

    return compile_verilator_ir_impl(
        mdir=mdir,
        all_classes=all_classes,
        force=force,
        clang_changed=clang_changed,
        clang_opt=clang_opt,
        jobs=jobs,
        compile_one=compile_one,
        llvm_link=LLVMLINK,
        run_command=run,
    )


def prepare_gpu_patched_ir(
    *,
    mdir: Path,
    merged_ll: Path,
    storage_size: int,
    classifier_report: Path,
    existing_meta: dict | None,
    reuse_gpu_patched_ll: bool,
    syms_state_image: bool,
    state_root_offset: int | None,
    kernel_split_phases: bool,
    kernel_probe_act_sequent_chunk_size: int,
    disable_cfg_clone_diagnostics: bool,
) -> tuple[Path, list[str] | None]:
    ensure_pass_tools_built()
    return prepare_gpu_patched_ir_impl(
        mdir=mdir,
        merged_ll=merged_ll,
        storage_size=storage_size,
        classifier_report=classifier_report,
        existing_meta=existing_meta,
        reuse_gpu_patched_ll=reuse_gpu_patched_ll,
        syms_state_image=syms_state_image,
        state_root_offset=state_root_offset,
        kernel_split_phases=kernel_split_phases,
        kernel_probe_act_sequent_chunk_size=kernel_probe_act_sequent_chunk_size,
        disable_cfg_clone_diagnostics=disable_cfg_clone_diagnostics,
        vlgpugen=VLGPUGEN,
        passes_dir=PASSES_DIR,
        passes_so=PASSES_SO,
        opt=OPT,
        run_command=run,
        reuse_launch_sequence=reuse_launch_sequence,
        load_launch_sequence_from_manifest=load_launch_sequence_from_manifest,
    )


def optimize_gpu_ir_to_ptx(
    *,
    mdir: Path,
    prefix: str,
    gpu_patched: Path,
    gpu_opt_level: str,
    sm: str,
) -> tuple[Path, list[str]]:
    ensure_pass_tools_built()
    return optimize_gpu_ir_to_ptx_impl(
        mdir=mdir,
        prefix=prefix,
        gpu_patched=gpu_patched,
        gpu_opt_level=gpu_opt_level,
        sm=sm,
        passes_so=PASSES_SO,
        opt=OPT,
        llc=LLC,
        run_command=run,
        prepare_gpu_opt_input=maybe_prepare_gpu_opt_input,
        prepare_lifetime_retiming_input=maybe_prepare_gpu_lifetime_retiming_input,
    )


def assemble_output_module(
    *,
    mdir: Path,
    gpu_ptx: Path,
    sm: str,
    out_cubin: Path | None,
    emit_ptx_module: bool,
    ptxas_opt_level: int | None,
) -> Path:
    return assemble_output_module_impl(
        mdir=mdir,
        gpu_ptx=gpu_ptx,
        sm=sm,
        out_cubin=out_cubin,
        emit_ptx_module=emit_ptx_module,
        ptxas_opt_level=ptxas_opt_level,
        ptxas=PTXAS,
        run_command=run,
    )
