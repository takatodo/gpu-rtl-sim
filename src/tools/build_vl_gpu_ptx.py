from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


RunCommand = Callable[[list], None]
OptInputPreparer = Callable[..., tuple[Path, list[str]]]
LifetimeRetimingPreparer = Callable[..., tuple[Path, list[str]]]


def run_host_cleanup_opt(
    *,
    mdir: Path,
    gpu_opt_input: Path,
    passes_so: Path,
    opt: str,
    run_command: RunCommand,
) -> Path:
    gpu_host_cleanup = mdir / "vl_batch_gpu_host_cleanup.ll"
    print(
        "  [opt] vl-stub-host-io-calls,vl-stub-timing-scheduler-context,"
        "dce,adce,simplifycfg,dce -> vl_batch_gpu_host_cleanup.ll"
    )
    run_command(
        [
            opt,
            f"--load-pass-plugin={passes_so}",
            "-passes=vl-stub-host-io-calls,vl-stub-timing-scheduler-context,dce,adce,simplifycfg,dce",
            "-S",
            str(gpu_opt_input),
            "-o",
            str(gpu_host_cleanup),
        ]
    )
    return gpu_host_cleanup


def run_gpu_opt(
    *,
    mdir: Path,
    gpu_host_cleanup: Path,
    gpu_opt_level: str,
    passes_so: Path,
    opt: str,
    run_command: RunCommand,
) -> Path:
    gpu_opt = mdir / "vl_batch_gpu_opt.ll"
    if gpu_opt_level == "O0":
        gpu_opt_raw = gpu_host_cleanup
        print("  [opt] vl-sanitize-host-io-null-writes -> vl_batch_gpu_opt.ll (gpu_opt=O0)")
    else:
        gpu_opt_raw = mdir / "vl_batch_gpu_opt_raw.ll"
        print(f"  [opt -{gpu_opt_level}] -> {gpu_opt_raw.name}")
        run_command([opt, f"-{gpu_opt_level}", "-S", str(gpu_host_cleanup), "-o", str(gpu_opt_raw)])
        print("  [opt] vl-sanitize-host-io-null-writes -> vl_batch_gpu_opt.ll")
    run_command(
        [
            opt,
            f"--load-pass-plugin={passes_so}",
            "-passes=vl-sanitize-host-io-null-writes",
            "-S",
            str(gpu_opt_raw),
            "-o",
            str(gpu_opt),
        ]
    )
    return gpu_opt


def optimize_gpu_ir_to_ptx(
    *,
    mdir: Path,
    prefix: str,
    gpu_patched: Path,
    gpu_opt_level: str,
    sm: str,
    passes_so: Path,
    opt: str,
    llc: str,
    run_command: RunCommand,
    prepare_gpu_opt_input: OptInputPreparer,
    prepare_lifetime_retiming_input: LifetimeRetimingPreparer,
) -> tuple[Path, list[str]]:
    gpu_ir_workarounds: list[str] = []
    gpu_opt_input, gpu_opt_workarounds = prepare_gpu_opt_input(
        prefix=prefix,
        mdir=mdir,
        gpu_patched=gpu_patched,
    )
    gpu_ir_workarounds.extend(gpu_opt_workarounds)
    gpu_host_cleanup = run_host_cleanup_opt(
        mdir=mdir,
        gpu_opt_input=gpu_opt_input,
        passes_so=passes_so,
        opt=opt,
        run_command=run_command,
    )
    gpu_opt = run_gpu_opt(
        mdir=mdir,
        gpu_host_cleanup=gpu_host_cleanup,
        gpu_opt_level=gpu_opt_level,
        passes_so=passes_so,
        opt=opt,
        run_command=run_command,
    )
    gpu_llc_input, lifetime_workarounds = prepare_lifetime_retiming_input(
        mdir=mdir,
        gpu_opt=gpu_opt,
    )
    gpu_ir_workarounds.extend(lifetime_workarounds)

    gpu_ptx = mdir / "vl_batch_gpu.ptx"
    print(f"  [llc] -march=nvptx64 -mcpu={sm} -> vl_batch_gpu.ptx")
    run_command([llc, "-march=nvptx64", f"-mcpu={sm}", str(gpu_llc_input), "-o", str(gpu_ptx)])
    return gpu_ptx, gpu_ir_workarounds
