import concurrent.futures
from collections.abc import Callable
from pathlib import Path


RunCommand = Callable[[list], None]
CompileOne = Callable[[Path, Path], None]


def compile_ll(
    cpp_path: Path,
    mdir: Path,
    out_ll: Path,
    *,
    clang_opt: str,
    clang: str,
    cxx_standard: str,
    verilator_include: Path,
    verilator_vltstd_include: Path,
    run_command: RunCommand,
) -> None:
    """Emit LLVM IR from Verilator C++."""
    flag = f'-{clang_opt}' if not clang_opt.startswith('-') else clang_opt
    cmd = [
        clang, f'-std={cxx_standard}', '-S', '-emit-llvm', flag,
        f'-I{mdir}', f'-I{verilator_include}', f'-I{verilator_vltstd_include}',
        str(cpp_path), '-o', str(out_ll),
    ]
    run_command(cmd)


def plan_verilator_ll_files(
    *,
    mdir: Path,
    all_classes: list[str],
    force: bool,
    clang_changed: bool,
    clang_opt: str,
) -> tuple[list[Path], bool]:
    ll_files: list[Path] = []
    any_ll_rebuilt = False
    for cls in all_classes:
        if cls.endswith("__main"):
            print(f"  skip (host main): {cls}.cpp")
            continue
        cpp = mdir / f'{cls}.cpp'
        if not cpp.exists():
            print(f'  skip (missing): {cpp.name}')
            continue
        out_ll = mdir / f'{cls}.ll'
        rebuild = force or clang_changed or not out_ll.exists()
        print(f'  [clang -{clang_opt}] {cpp.name} -> {out_ll.name}' if rebuild else f'  [cached] {out_ll.name}')
        any_ll_rebuilt = any_ll_rebuilt or rebuild
        ll_files.append(out_ll)
    return ll_files, any_ll_rebuilt


def compile_planned_ll_files(
    *,
    mdir: Path,
    ll_files: list[Path],
    force: bool,
    clang_changed: bool,
    jobs: int,
    compile_one: CompileOne,
) -> None:
    compile_jobs = [
        (mdir / f'{out_ll.stem}.cpp', out_ll)
        for out_ll in ll_files
        if force or clang_changed or not out_ll.exists()
    ]
    if jobs == 1:
        for cpp, out_ll in compile_jobs:
            compile_one(cpp, out_ll)
        return
    if compile_jobs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = [
                executor.submit(compile_one, cpp, out_ll)
                for cpp, out_ll in compile_jobs
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()


def link_merged_ll(
    *,
    mdir: Path,
    ll_files: list[Path],
    force: bool,
    clang_changed: bool,
    any_ll_rebuilt: bool,
    llvm_link: str,
    run_command: RunCommand,
) -> Path:
    if not ll_files:
        raise RuntimeError('No .ll files generated')

    merged_ll = mdir / 'merged.ll'
    if force or clang_changed or any_ll_rebuilt or not merged_ll.exists():
        print(f'  [llvm-link] -> merged.ll')
        run_command([llvm_link, '-S', '-o', str(merged_ll)] + [str(f) for f in ll_files])
    else:
        print(f'  [cached] merged.ll')
    return merged_ll


def compile_verilator_ir(
    *,
    mdir: Path,
    all_classes: list[str],
    force: bool,
    clang_changed: bool,
    clang_opt: str,
    jobs: int,
    compile_one: CompileOne,
    llvm_link: str,
    run_command: RunCommand,
) -> Path:
    ll_files, any_ll_rebuilt = plan_verilator_ll_files(
        mdir=mdir,
        all_classes=all_classes,
        force=force,
        clang_changed=clang_changed,
        clang_opt=clang_opt,
    )
    compile_planned_ll_files(
        mdir=mdir,
        ll_files=ll_files,
        force=force,
        clang_changed=clang_changed,
        jobs=jobs,
        compile_one=compile_one,
    )
    return link_merged_ll(
        mdir=mdir,
        ll_files=ll_files,
        force=force,
        clang_changed=clang_changed,
        any_ll_rebuilt=any_ll_rebuilt,
        llvm_link=llvm_link,
        run_command=run_command,
    )
