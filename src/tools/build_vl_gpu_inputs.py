from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from build_vl_gpu_option_validation import incremental_mode_name, validate_build_options

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent

# Verilator --timing -> coroutines; Clang + libstdc++ need C++20 for <coroutine> builtins.
CXX_STANDARD = 'c++20'

CLANG = 'clang++-18'
LLVMLINK = 'llvm-link-18'
OPT = 'opt-18'
LLC = 'llc-18'
PTXAS = 'ptxas'


def verilator_include_dir() -> Path:
    """Include path for Verilator headers; must match the Verilator that generated mdir."""
    root = os.environ.get('VERILATOR_ROOT')
    if root:
        rp = Path(root)
        for cand in (rp / 'include', rp / 'share' / 'verilator' / 'include'):
            if cand.is_dir():
                return cand
    env_inc = os.environ.get('VL_INCLUDE')
    if env_inc:
        return Path(env_inc)
    bundled = REPO_ROOT / 'third_party' / 'verilator' / 'include'
    if bundled.is_dir():
        return bundled
    return Path('/usr/local/share/verilator/include')


def verilator_vltstd_include_dir() -> Path:
    base = verilator_include_dir()
    candidate = base / 'vltstd'
    if candidate.is_dir():
        return candidate
    return candidate


def read_mk_list(mk_text: str, var: str) -> list[str]:
    """Makefile の var += ... (複数行) を収集して値リストを返す"""
    values = []
    in_var = False
    for raw_line in mk_text.splitlines():
        line = raw_line.strip()
        if not in_var:
            m = re.match(r'^' + re.escape(var) + r'\s*\+?=\s*(.*)', line)
            if m:
                in_var = True
                val = m.group(1).rstrip('\\').strip()
                if val:
                    values.append(val)
        else:
            val = line.rstrip('\\').strip()
            if val:
                values.append(val)
            if not raw_line.rstrip().endswith('\\'):
                in_var = False
    return values


def find_classes_mk(mdir: Path) -> Path:
    hits = list(mdir.glob('*_classes.mk'))
    if not hits:
        mdir = mdir.resolve()
        hint = (
            f'No *_classes.mk under {mdir}.\n'
            '  build_vl_gpu.py needs a Verilator --cc output directory (run verilator with -cc).\n'
            '  On a fresh clone, work/… is often empty or gitignored — regenerate that obj_dir, '
            'or pass a different --mdir.'
        )
        raise FileNotFoundError(hint)
    return hits[0]


def find_prefix(mdir: Path) -> str:
    mk = find_classes_mk(mdir)
    return mk.stem.replace('_classes', '')


def detect_storage_size(mdir: Path, prefix: str) -> int:
    """sizeof(prefix___024root) を C++ probe でコンパイル実行して返す"""
    root_h = mdir / f'{prefix}___024root.h'
    probe_src = (
        f'#include <cstdio>\n'
        f'#include "{root_h.resolve()}"\n'
        f'int main() {{\n'
        f'    printf("%zu\\n", sizeof({prefix}___024root));\n'
        f'    return 0;\n'
        f'}}\n'
    )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'probe_size.cpp'
        exe = Path(tmp) / 'probe_size'
        src.write_text(probe_src)
        vl_inc = verilator_include_dir()
        vl_vltstd_inc = verilator_vltstd_include_dir()
        cmd = [
            CLANG, f'-std={CXX_STANDARD}',
            f'-I{mdir}', f'-I{vl_inc}', f'-I{vl_vltstd_inc}',
            str(src), '-o', str(exe),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        result = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
        return int(result.stdout.strip())


def clang_opt_changed(mdir: Path, clang_opt: str) -> tuple[Path, bool]:
    opt_marker = mdir / '.vl_gpu_clang_opt'
    stored_opt = opt_marker.read_text(encoding='utf-8').strip() if opt_marker.exists() else None
    clang_changed = stored_opt is not None and stored_opt != clang_opt
    if clang_changed:
        print(f'  [clang] opt changed {stored_opt!r} -> {clang_opt!r}; re-emitting .ll')
    return opt_marker, clang_changed
