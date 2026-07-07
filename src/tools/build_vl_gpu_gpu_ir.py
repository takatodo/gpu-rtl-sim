from collections.abc import Callable
from pathlib import Path

from build_vl_gpu_ptx import optimize_gpu_ir_to_ptx


RunCommand = Callable[[list], None]
LaunchSequenceResolver = Callable[[Path, dict | None], list[str] | None]
ManifestLaunchSequenceLoader = Callable[[Path], list[str]]


def build_vlgpugen_command(
    *,
    vlgpugen: Path,
    merged_ll: Path,
    storage_size: int,
    gpu_ll: Path,
    classifier_report: Path,
    syms_state_image: bool,
    state_root_offset: int | None,
    kernel_split_phases: bool,
    kernel_manifest: Path,
    kernel_probe_act_sequent_chunk_size: int,
    disable_cfg_clone_diagnostics: bool,
) -> list[str]:
    command = [
        str(vlgpugen), str(merged_ll),
        f'--storage-size={storage_size}', f'--out={gpu_ll}',
        f'--classifier-report-out={classifier_report}',
    ]
    if syms_state_image:
        command.append('--syms-state-image')
        command.append(f'--state-root-offset={state_root_offset}')
    if kernel_split_phases:
        command.append('--kernel-split=phases')
        command.append(f'--kernel-manifest-out={kernel_manifest}')
    if kernel_probe_act_sequent_chunk_size:
        command.append(f'--kernel-probe-act-sequent-chunk-size={kernel_probe_act_sequent_chunk_size}')
    if disable_cfg_clone_diagnostics:
        command.append('--disable-cfg-clone-diagnostics')
    return command


def run_gpu_patch_opt(
    *,
    gpu_ll: Path,
    gpu_patched: Path,
    syms_state_image: bool,
    passes_dir: Path,
    passes_so: Path,
    opt: str,
    run_command: RunCommand,
) -> None:
    run_command(['make', '-C', str(passes_dir), '--no-print-directory'])
    print('  [opt] lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-stub-host-io-calls,vl-stub-timing-scheduler-context,vl-patch-convergence,dce,adce,simplifycfg,dce')
    vl_passes = 'lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-stub-host-io-calls,vl-stub-timing-scheduler-context,vl-patch-convergence,dce,adce,simplifycfg,dce'
    opt_cmd = [
        opt,
        f'--load-pass-plugin={passes_so}',
        f'-passes={vl_passes}',
        '-S',
        str(gpu_ll),
        '-o',
        str(gpu_patched),
    ]
    if syms_state_image:
        opt_cmd.insert(2, '--vl-preserve-convergence-threshold')
    run_command(opt_cmd)


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
    vlgpugen: Path,
    passes_dir: Path,
    passes_so: Path,
    opt: str,
    run_command: RunCommand,
    reuse_launch_sequence: LaunchSequenceResolver,
    load_launch_sequence_from_manifest: ManifestLaunchSequenceLoader,
) -> tuple[Path, list[str] | None]:
    gpu_patched = mdir / 'vl_batch_gpu_patched.ll'
    if reuse_gpu_patched_ll:
        if not gpu_patched.exists():
            raise FileNotFoundError(f'missing patched GPU IR for reuse: {gpu_patched}')
        print(f'  [reuse] using existing {gpu_patched.name}')
        return gpu_patched, reuse_launch_sequence(mdir, existing_meta)

    gpu_ll = mdir / 'vl_batch_gpu.ll'
    kernel_manifest = mdir / 'vl_kernel_manifest.json'
    print('  [vlgpugen] -> vl_batch_gpu.ll')
    run_command(
        build_vlgpugen_command(
            vlgpugen=vlgpugen,
            merged_ll=merged_ll,
            storage_size=storage_size,
            gpu_ll=gpu_ll,
            classifier_report=classifier_report,
            syms_state_image=syms_state_image,
            state_root_offset=state_root_offset,
            kernel_split_phases=kernel_split_phases,
            kernel_manifest=kernel_manifest,
            kernel_probe_act_sequent_chunk_size=kernel_probe_act_sequent_chunk_size,
            disable_cfg_clone_diagnostics=disable_cfg_clone_diagnostics,
        )
    )
    launch_sequence = load_launch_sequence_from_manifest(kernel_manifest) if kernel_split_phases else None
    run_gpu_patch_opt(
        gpu_ll=gpu_ll,
        gpu_patched=gpu_patched,
        syms_state_image=syms_state_image,
        passes_dir=passes_dir,
        passes_so=passes_so,
        opt=opt,
        run_command=run_command,
    )
    return gpu_patched, launch_sequence
