from collections.abc import Callable
from pathlib import Path


RunCommand = Callable[[list], None]


def assemble_output_module(
    *,
    mdir: Path,
    gpu_ptx: Path,
    sm: str,
    out_cubin: Path | None,
    emit_ptx_module: bool,
    ptxas_opt_level: int | None,
    ptxas: str,
    run_command: RunCommand,
) -> Path:
    if emit_ptx_module:
        print(f'  [module] using PTX directly -> {gpu_ptx.name}')
        return gpu_ptx

    if out_cubin is None:
        out_cubin = mdir / 'vl_batch_gpu.cubin'
    ptxas_cmd = [ptxas, f'--gpu-name={sm}']
    if ptxas_opt_level is not None:
        ptxas_cmd.extend(['--opt-level', str(ptxas_opt_level)])
    ptxas_cmd.extend([str(gpu_ptx), '-o', str(out_cubin)])
    if ptxas_opt_level is None:
        print(f'  [ptxas] -> {out_cubin.name}')
    else:
        print(f'  [ptxas -O{ptxas_opt_level}] -> {out_cubin.name}')
    run_command(ptxas_cmd)
    return out_cubin
