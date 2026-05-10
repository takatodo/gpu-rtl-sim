#!/usr/bin/env python3
"""
build_vl_gpu.py
Verilator --cc 出力ディレクトリから GPU cubin を自動生成する。

Usage:
  python3 build_vl_gpu.py <mdir> [--sm sm_89] [--out out.cubin] [--force]
  python3 build_vl_gpu.py <mdir> [--ptxas-opt-level 0]
  python3 build_vl_gpu.py <mdir> [--emit-ptx-module]
  python3 build_vl_gpu.py <mdir> [--reuse-gpu-patched-ll] [--gpu-opt-level O0]
  python3 build_vl_gpu.py <mdir> [--reuse-ptx] [--ptxas-opt-level 0]
  python3 build_vl_gpu.py <mdir> --kernel-split-phases --kernel-probe-act-sequent-chunk-size N
  python3 build_vl_gpu.py <mdir> --syms-state-image --syms-storage-size N --state-root-offset N

Steps:
  1. {mdir}/*_classes.mk から VM_CLASSES_FAST + VM_CLASSES_SLOW を読み込む
  2. 各 .cpp を clang++-18 -std=c++20 -S -emit-llvm (-O1 既定、--clang-O で変更) → .ll
  3. llvm-link-18 → merged.ll
  4. C++ probe で storage_size (sizeof root struct) を自動検出
  5. vlgpugen merged.ll --storage-size=N → vl_batch_gpu.ll
     (or Syms image mode: --storage-size=<sizeof __Syms> --state-root-offset=<root offset>)
  6. opt (lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-stub-host-io-calls,vl-stub-timing-scheduler-context,vl-patch-convergence,cleanup) → patched
  7. host cleanup → optional opt → vl-sanitize-host-io-null-writes → vl_batch_gpu_opt.ll → optional VlWide lifetime retiming → llc-18 → vl_batch_gpu.ptx → ptxas → vl_batch_gpu.cubin
     (or skip ptxas and use vl_batch_gpu.ptx directly when --emit-ptx-module is set)
  8. vl_classifier_report.json (reachable GPU/runtime placement report)
  9. vl_batch_gpu.meta.json (schema_version, cubin/module path, storage_size, sm, kernel, classifier_report)
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PASSES_DIR  = SCRIPT_DIR.parent / 'passes'
PASSES_SO   = PASSES_DIR / 'VlGpuPasses.so'
VLGPUGEN    = PASSES_DIR / 'vlgpugen'

# Verilator --timing → coroutines; Clang + libstdc++ need C++20 for <coroutine> builtins.
CXX_STANDARD = 'c++20'


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

CLANG    = 'clang++-18'
LLVMLINK = 'llvm-link-18'
OPT      = 'opt-18'
LLC      = 'llc-18'
PTXAS    = 'ptxas'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list, **kwargs):
    print(' '.join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def load_launch_sequence_from_manifest(manifest_path: Path) -> list[str]:
    if not manifest_path.is_file():
        raise RuntimeError(f'kernel manifest not found: {manifest_path}')
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    launch_sequence = payload.get('launch_sequence')
    if not isinstance(launch_sequence, list) or not launch_sequence:
        raise RuntimeError(f'invalid kernel manifest launch_sequence: {manifest_path}')
    if any(not isinstance(item, str) or not item for item in launch_sequence):
        raise RuntimeError(f'invalid kernel manifest kernel name: {manifest_path}')
    return [str(item) for item in launch_sequence]


def resolve_manifest_launch_sequence(mdir: Path) -> list[str] | None:
    manifest_path = mdir / 'vl_kernel_manifest.json'
    if not manifest_path.is_file():
        return None
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    if payload.get('kernel_split') != 'phases':
        return None
    return load_launch_sequence_from_manifest(manifest_path)


def load_existing_meta(mdir: Path) -> dict | None:
    meta_path = mdir / 'vl_batch_gpu.meta.json'
    if not meta_path.is_file():
        return None
    try:
        payload = json.loads(meta_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'invalid existing meta.json: {meta_path}') from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f'invalid existing meta.json payload: {meta_path}')
    return payload


def resolve_existing_storage_size(existing_meta: dict | None) -> int | None:
    if not existing_meta:
        return None
    storage_size = existing_meta.get('storage_size')
    if isinstance(storage_size, int) and storage_size > 0:
        return storage_size
    return None


def resolve_existing_classifier_report(mdir: Path, existing_meta: dict | None) -> Path:
    report_name = None
    if existing_meta:
        raw_name = existing_meta.get('classifier_report')
        if isinstance(raw_name, str) and raw_name:
            report_name = raw_name
    return mdir / (report_name or 'vl_classifier_report.json')


def resolve_existing_launch_sequence(existing_meta: dict | None) -> list[str] | None:
    if not existing_meta:
        return None
    raw = existing_meta.get('launch_sequence')
    if not isinstance(raw, list):
        return None
    launch_sequence = [str(item) for item in raw if isinstance(item, str) and item]
    return launch_sequence or None


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


# ---------------------------------------------------------------------------
# Storage size detection via C++ probe
# ---------------------------------------------------------------------------

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


def detect_hierarchy_state_metadata(mdir: Path, storage_size: int) -> dict[str, object]:
    """Summarize whether generated GPU IR needs Verilator __Syms state."""
    ir_paths = [path for path in (mdir / 'vl_batch_gpu_opt.ll', mdir / 'vl_batch_gpu.ll') if path.is_file()]
    if not ir_paths:
        return {
            "state_image_kind": "root_image",
            "root_storage_size": storage_size,
            "unsafe_syms_gep_count": 0,
            "unsafe_syms_gep_covered_by_state_image": True,
            "metadata_source": None,
        }
    primary_path = ir_paths[0]
    primary_text = primary_path.read_text(encoding='utf-8')
    all_texts = [(path, path.read_text(encoding='utf-8')) for path in ir_paths]
    syms_size = None
    for _, text in all_texts:
        for line in text.splitlines():
            if "__Syms" not in line:
                continue
            for match in re.finditer(r'dereferenceable\((\d+)\)', line):
                syms_size = max(syms_size or 0, int(match.group(1)))
    unsafe_count = len(UNSAFE_SYMS_GEP_RE.findall(primary_text))
    root_offset = None
    for _, text in all_texts:
        for line in text.splitlines():
            match = SYMS_TBAA_RE.match(line)
            if not match:
                continue
            offsets = [int(raw) for raw in re.findall(r'i64\s+(\d+)', match.group('body'))]
            for left, right in zip(offsets, offsets[1:]):
                if right - left == storage_size:
                    root_offset = left
                    break
            if root_offset is not None:
                break
        if root_offset is not None:
            break
    covered = unsafe_count == 0
    if syms_size is not None and syms_size <= storage_size:
        covered = True
    return {
        "state_image_kind": "root_image",
        "root_storage_size": storage_size,
        "syms_storage_size": syms_size,
        "root_offset_in_syms": root_offset,
        "unsafe_syms_gep_count": unsafe_count,
        "unsafe_syms_gep_covered_by_state_image": covered,
        "prelaunch_rejection_required": not covered,
        "metadata_source": primary_path.name,
    }


def syms_image_hierarchy_metadata(
    mdir: Path,
    *,
    root_storage_size: int,
    syms_storage_size: int,
    state_root_offset: int,
) -> dict[str, object]:
    """Metadata for a per-state Verilator __Syms image with root embedded inside it."""
    metadata = detect_hierarchy_state_metadata(mdir, root_storage_size)
    metadata.update(
        {
            "state_image_kind": "verilator_syms_image",
            "root_storage_size": root_storage_size,
            "syms_storage_size": syms_storage_size,
            "root_offset_in_syms": state_root_offset,
            "root_offset_in_state": state_root_offset,
            "unsafe_syms_gep_covered_by_state_image": True,
            "prelaunch_rejection_required": False,
        }
    )
    return metadata


# ---------------------------------------------------------------------------
# Compile .cpp → .ll
# ---------------------------------------------------------------------------

def compile_ll(cpp_path: Path, mdir: Path, out_ll: Path, *, clang_opt: str = 'O1'):
    """Emit LLVM IR from Verilator C++. Higher -O (O2/O3) often shortens GPU _eval time."""
    flag = f'-{clang_opt}' if not clang_opt.startswith('-') else clang_opt
    vl_inc = verilator_include_dir()
    vl_vltstd_inc = verilator_vltstd_include_dir()
    cmd = [
        CLANG, f'-std={CXX_STANDARD}', '-S', '-emit-llvm', flag,
        f'-I{mdir}', f'-I{vl_inc}', f'-I{vl_vltstd_inc}',
        str(cpp_path), '-o', str(out_ll),
    ]
    run(cmd)


VERILATED_TLS_SLOT_SYMBOL = '@_ZN9Verilated3t_sE = external thread_local global'
VERILATED_FAKE_TLS_SLOT_SYMBOL = '@vl_gpu_fake_verilated_t_contextp = internal global ptr null, align 8'
VERILATED_TLS_SLOT_DECL_RE = re.compile(
    r'^@_ZN9Verilated3t_sE = external thread_local global .*$',
    re.MULTILINE,
)
VERILATED_TLS_SLOT_CALL_RE = re.compile(
    r'^(?P<indent>\s*)(?P<ssa>%[0-9]+)\s*=\s*(?:tail\s+)?call '
    r'noundef align 8 ptr @llvm\.threadlocal\.address\.p0'
    r'\(ptr align 8 @_ZN9Verilated3t_sE\)\s*$',
    re.MULTILINE,
)
VERILATED_TLS_BYPASS_PREFIXES = {
    'Vvortex_gpu_cov_tb': 'vortex',
    'Vcaliptra_gpu_cov_tb': 'caliptra',
}

VL_WIDE_TYPE_RE = re.compile(r'^(%struct\.VlWide(?:\.\d+)?) = type \{ \[(\d+) x i32\] \}$')
VL_WIDE_ALLOCA_RE = re.compile(
    r'^\s*(%\d+) = alloca (?P<ty>%struct\.VlWide(?:\.\d+)?), align (?P<align>\d+)\s*$'
)
LIFETIME_RE = re.compile(
    r'^(?P<indent>\s*)call void @llvm\.lifetime\.(?P<kind>start|end)\.p0'
    r'\(i64 (?P<size>\d+), ptr nonnull (?P<var>%\d+)\)(?P<suffix>.*)$'
)
PTR_DERIVED_ASSIGN_RE = re.compile(
    r'^\s*(?P<lhs>%\d+) = (?:getelementptr(?: inbounds)? [^,]+, ptr|addrspacecast ptr|bitcast ptr) '
    r'(?P<base>%\d+)\b'
)
SSA_VALUE_RE = re.compile(r'%\d+')
UNSAFE_SYMS_GEP_RE = re.compile(
    r'getelementptr\s+inbounds\s+%class\.[^,\n]*__Syms[^,\n]*,'
)
SYMS_TBAA_RE = re.compile(r'^!\d+\s*=\s*!\{!"[^"]*__Syms",(?P<body>.*)\}$')


def should_apply_vortex_tls_slot_bypass(*, prefix: str, ir_text: str) -> bool:
    return (
        prefix in VERILATED_TLS_BYPASS_PREFIXES
        and VERILATED_TLS_SLOT_SYMBOL in ir_text
        and '@llvm.threadlocal.address.p0(ptr align 8 @_ZN9Verilated3t_sE)' in ir_text
    )


def apply_vortex_tls_slot_bypass_text(ir_text: str) -> tuple[str, int]:
    updated = ir_text
    if VERILATED_FAKE_TLS_SLOT_SYMBOL not in updated:
        if VERILATED_TLS_SLOT_SYMBOL not in updated:
            raise RuntimeError('missing Verilated TLS slot symbol in Vortex GPU IR')
        updated, decl_replacements = VERILATED_TLS_SLOT_DECL_RE.subn(
            lambda match: match.group(0) + '\n' + VERILATED_FAKE_TLS_SLOT_SYMBOL,
            updated,
            count=1,
        )
        if decl_replacements != 1:
            raise RuntimeError('failed to inject Vortex fake TLS slot declaration')

    def _replace(match: re.Match[str]) -> str:
        return (
            f"{match.group('indent')}{match.group('ssa')} = getelementptr inbounds ptr, "
            f"ptr @vl_gpu_fake_verilated_t_contextp, i64 0"
        )

    updated, replacements = VERILATED_TLS_SLOT_CALL_RE.subn(_replace, updated)
    if replacements == 0:
        raise RuntimeError('no Vortex TLS slot callsites were rewritten')
    return updated, replacements


def maybe_prepare_gpu_opt_input(*, prefix: str, mdir: Path, gpu_patched: Path) -> tuple[Path, list[str]]:
    ir_text = gpu_patched.read_text(encoding='utf-8')
    if not should_apply_vortex_tls_slot_bypass(prefix=prefix, ir_text=ir_text):
        return gpu_patched, []

    rewritten_text, replacements = apply_vortex_tls_slot_bypass_text(ir_text)
    bypass_slug = VERILATED_TLS_BYPASS_PREFIXES[prefix]
    bypass_path = mdir / f'vl_batch_gpu_{bypass_slug}_tls_bypass.ll'
    bypass_path.write_text(rewritten_text, encoding='utf-8')
    return bypass_path, [f'{bypass_slug}_verilated_tls_slot_bypass:{replacements}']


def _find_wide_type_sizes(lines: list[str]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for line in lines:
        match = VL_WIDE_TYPE_RE.match(line)
        if match:
            sizes[match.group(1)] = int(match.group(2)) * 4
    return sizes


def _is_function_start(line: str) -> bool:
    return line.startswith('define ') and '{' in line


def _retime_wide_lifetimes_in_function(
    lines: list[str],
    *,
    wide_type_sizes: dict[str, int],
) -> tuple[list[str], dict[str, int]]:
    allocas: dict[str, dict[str, int | str]] = {}
    starts: dict[str, list[tuple[int, str]]] = {}
    ends: dict[str, list[tuple[int, str]]] = {}

    for idx, line in enumerate(lines):
        alloca_match = VL_WIDE_ALLOCA_RE.match(line)
        if alloca_match:
            ty = alloca_match.group('ty')
            size = wide_type_sizes.get(ty)
            if size is not None:
                allocas[alloca_match.group(1)] = {
                    'size': size,
                    'align': int(alloca_match.group('align')),
                    'type': ty,
                }
            continue

        lifetime_match = LIFETIME_RE.match(line)
        if not lifetime_match:
            continue
        var = lifetime_match.group('var')
        if var not in allocas:
            continue
        if int(lifetime_match.group('size')) != int(allocas[var]['size']):
            continue
        target = starts if lifetime_match.group('kind') == 'start' else ends
        target.setdefault(var, []).append((idx, line))

    eligible = {
        var
        for var in allocas
        if len(starts.get(var, [])) == 1 and len(ends.get(var, [])) == 1
    }
    if not eligible:
        return lines, {'retimed_allocas': 0, 'retimed_functions': 0}

    # Track pointer SSA values derived from each stack slot. The rewrite only
    # handles pointer arithmetic that remains local to the function body.
    owner: dict[str, str] = {var: var for var in eligible}
    changed = True
    while changed:
        changed = False
        for line in lines:
            match = PTR_DERIVED_ASSIGN_RE.match(line)
            if not match:
                continue
            base = match.group('base')
            lhs = match.group('lhs')
            if base in owner and lhs not in owner:
                owner[lhs] = owner[base]
                changed = True

    owned_values = set(owner)
    uses: dict[str, list[int]] = {var: [] for var in eligible}
    unsafe: set[str] = set()
    for idx, line in enumerate(lines):
        if 'alloca ' in line or 'llvm.lifetime.start' in line or 'llvm.lifetime.end' in line:
            continue
        tokens = set(SSA_VALUE_RE.findall(line)) & owned_values
        if not tokens:
            continue
        roots = {owner[token] for token in tokens}
        for root in roots:
            uses[root].append(idx)

        # If the pointer value itself escapes, moving lifetime markers from the
        # original conservative range is not defensible from local text alone.
        if 'call ' in line and '@llvm.' not in line:
            unsafe.update(roots)
        for token in tokens:
            if re.search(r'\bstore\s+ptr\s+' + re.escape(token) + r'\b', line):
                unsafe.add(owner[token])
            if re.search(r'\bret\s+ptr\s+' + re.escape(token) + r'\b', line):
                unsafe.add(owner[token])

    retimed = sorted(
        var for var in eligible
        if var not in unsafe and uses.get(var)
    )
    if not retimed:
        return lines, {'retimed_allocas': 0, 'retimed_functions': 0}

    retimed_set = set(retimed)
    insert_before: dict[int, list[str]] = {}
    insert_after: dict[int, list[str]] = {}
    for var in retimed:
        first_use = min(uses[var])
        last_use = max(uses[var])
        insert_before.setdefault(first_use, []).append(starts[var][0][1])
        insert_after.setdefault(last_use, []).append(ends[var][0][1])

    rewritten: list[str] = []
    for idx, line in enumerate(lines):
        lifetime_match = LIFETIME_RE.match(line)
        if lifetime_match and lifetime_match.group('var') in retimed_set:
            continue
        rewritten.extend(insert_before.get(idx, []))
        rewritten.append(line)
        rewritten.extend(insert_after.get(idx, []))

    return rewritten, {
        'retimed_allocas': len(retimed),
        'retimed_functions': 1,
    }


def apply_gpu_wide_alloca_lifetime_retiming_text(ir_text: str) -> tuple[str, dict[str, int]]:
    lines = ir_text.splitlines()
    wide_type_sizes = _find_wide_type_sizes(lines)
    if not wide_type_sizes:
        return ir_text, {'retimed_allocas': 0, 'retimed_functions': 0}

    rewritten: list[str] = []
    summary = {'retimed_allocas': 0, 'retimed_functions': 0}
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not _is_function_start(line):
            rewritten.append(line)
            idx += 1
            continue

        function_lines = [line]
        brace_depth = line.count('{') - line.count('}')
        idx += 1
        while idx < len(lines) and brace_depth > 0:
            function_lines.append(lines[idx])
            brace_depth += lines[idx].count('{') - lines[idx].count('}')
            idx += 1

        transformed, function_summary = _retime_wide_lifetimes_in_function(
            function_lines,
            wide_type_sizes=wide_type_sizes,
        )
        rewritten.extend(transformed)
        summary['retimed_allocas'] += function_summary['retimed_allocas']
        summary['retimed_functions'] += function_summary['retimed_functions']

    trailing_newline = '\n' if ir_text.endswith('\n') else ''
    return '\n'.join(rewritten) + trailing_newline, summary


def maybe_prepare_gpu_lifetime_retiming_input(*, mdir: Path, gpu_opt: Path) -> tuple[Path, list[str]]:
    ir_text = gpu_opt.read_text(encoding='utf-8')
    rewritten_text, summary = apply_gpu_wide_alloca_lifetime_retiming_text(ir_text)
    retimed_allocas = summary['retimed_allocas']
    if retimed_allocas == 0:
        return gpu_opt, []

    retimed_path = mdir / 'vl_batch_gpu_lifetime_retimed.ll'
    retimed_path.write_text(rewritten_text, encoding='utf-8')
    retimed_functions = summary['retimed_functions']
    return retimed_path, [f'vlwide_lifetime_retiming:{retimed_allocas}:{retimed_functions}']


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_vl_gpu(
    mdir: Path,
    sm: str = 'sm_89',
    out_cubin: Path = None,
    force: bool = False,
    clang_opt: str = 'O1',
    gpu_opt_level: str = 'O3',
    ptxas_opt_level: int | None = None,
    emit_ptx_module: bool = False,
    analyze_phases: bool = False,
    kernel_split_phases: bool = False,
    kernel_probe_act_sequent_chunk_size: int = 0,
    reuse_gpu_patched_ll: bool = False,
    reuse_ptx: bool = False,
    syms_state_image: bool = False,
    syms_storage_size: int | None = None,
    state_root_offset: int | None = None,
    jobs: int = 1,
) -> tuple[Path, int]:

    if reuse_gpu_patched_ll and reuse_ptx:
        raise ValueError('choose at most one reuse mode')
    if jobs <= 0:
        raise ValueError('jobs must be >= 1')
    if (reuse_gpu_patched_ll or reuse_ptx) and analyze_phases:
        raise ValueError('--analyze-phases requires a full rebuild from merged.ll')
    if (reuse_gpu_patched_ll or reuse_ptx) and kernel_split_phases:
        raise ValueError('--kernel-split-phases requires a full rebuild from merged.ll')
    if kernel_probe_act_sequent_chunk_size < 0:
        raise ValueError('--kernel-probe-act-sequent-chunk-size must be >= 0')
    if kernel_probe_act_sequent_chunk_size and not kernel_split_phases:
        raise ValueError('--kernel-probe-act-sequent-chunk-size requires --kernel-split-phases')
    if (reuse_gpu_patched_ll or reuse_ptx) and kernel_probe_act_sequent_chunk_size:
        raise ValueError('--kernel-probe-act-sequent-chunk-size requires a full rebuild from merged.ll')
    if syms_state_image and (reuse_gpu_patched_ll or reuse_ptx):
        raise ValueError('--syms-state-image requires a full rebuild from merged.ll')
    if syms_state_image:
        if syms_storage_size is None or syms_storage_size <= 0:
            raise ValueError('--syms-state-image requires --syms-storage-size > 0')
        if state_root_offset is None or state_root_offset < 0:
            raise ValueError('--syms-state-image requires --state-root-offset >= 0')
    elif syms_storage_size is not None or state_root_offset is not None:
        raise ValueError('--syms-storage-size/--state-root-offset require --syms-state-image')

    mdir = mdir.resolve()
    classes_mk = find_classes_mk(mdir)
    mk_text = classes_mk.read_text()
    prefix = find_prefix(mdir)
    incremental_mode = 'full'
    if reuse_gpu_patched_ll:
        incremental_mode = 'reuse_gpu_patched_ll'
    elif reuse_ptx:
        incremental_mode = 'reuse_ptx'
    print(
        f'[build_vl_gpu] mdir={mdir}  prefix={prefix}  sm={sm}  '
        f'clang={clang_opt}  gpu_opt={gpu_opt_level}  mode={incremental_mode}'
    )

    fast_classes = read_mk_list(mk_text, 'VM_CLASSES_FAST')
    slow_classes = read_mk_list(mk_text, 'VM_CLASSES_SLOW')
    all_classes  = fast_classes + slow_classes
    print(f'  Classes: {all_classes}')
    existing_meta = load_existing_meta(mdir)
    launch_sequence = None
    classifier_report = mdir / 'vl_classifier_report.json'
    gpu_ir_workarounds: list[str] = []

    opt_marker = mdir / '.vl_gpu_clang_opt'
    stored_opt = opt_marker.read_text(encoding='utf-8').strip() if opt_marker.exists() else None
    clang_changed = stored_opt is not None and stored_opt != clang_opt
    if clang_changed:
        print(f'  [clang] opt changed {stored_opt!r} → {clang_opt!r}; re-emitting .ll')

    if reuse_ptx:
        gpu_ptx = mdir / 'vl_batch_gpu.ptx'
        if not gpu_ptx.exists():
            raise FileNotFoundError(f'missing PTX for --reuse-ptx: {gpu_ptx}')
        storage_size = resolve_existing_storage_size(existing_meta)
        if storage_size is None:
            print('  [probe] existing meta missing storage_size; detecting...')
            storage_size = detect_storage_size(mdir, prefix)
        else:
            print(f'  [meta] reuse storage_size = {storage_size} bytes')
        classifier_report = resolve_existing_classifier_report(mdir, existing_meta)
        launch_sequence = resolve_existing_launch_sequence(existing_meta)
        if launch_sequence is None:
            launch_sequence = resolve_manifest_launch_sequence(mdir)
            if launch_sequence is not None:
                print('  [meta] reuse launch_sequence from vl_kernel_manifest.json')
    else:
        # Step 1: compile each .cpp → .ll
        ll_files = []
        any_ll_rebuilt = False
        for cls in all_classes:
            cpp = mdir / f'{cls}.cpp'
            if not cpp.exists():
                print(f'  skip (missing): {cpp.name}')
                continue
            out_ll = mdir / f'{cls}.ll'
            if force or clang_changed or not out_ll.exists():
                print(f'  [clang -{clang_opt}] {cpp.name} → {out_ll.name}')
                ll_files.append(out_ll)
                any_ll_rebuilt = True
                continue
            print(f'  [cached] {out_ll.name}')
            ll_files.append(out_ll)

        if jobs == 1:
            for out_ll in ll_files:
                cpp = mdir / f'{out_ll.stem}.cpp'
                if force or clang_changed or not out_ll.exists():
                    compile_ll(cpp, mdir, out_ll, clang_opt=clang_opt)
        else:
            compile_jobs: list[tuple[Path, Path]] = []
            for out_ll in ll_files:
                cpp = mdir / f'{out_ll.stem}.cpp'
                if force or clang_changed or not out_ll.exists():
                    compile_jobs.append((cpp, out_ll))
            if compile_jobs:
                with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
                    futures = [
                        executor.submit(compile_ll, cpp, mdir, out_ll, clang_opt=clang_opt)
                        for cpp, out_ll in compile_jobs
                    ]
                    for future in concurrent.futures.as_completed(futures):
                        future.result()

        if not ll_files:
            raise RuntimeError('No .ll files generated')

        # Step 2: llvm-link → merged.ll
        merged_ll = mdir / 'merged.ll'
        if force or clang_changed or any_ll_rebuilt or not merged_ll.exists():
            print(f'  [llvm-link] → merged.ll')
            run([LLVMLINK, '-S', '-o', str(merged_ll)] + [str(f) for f in ll_files])
        else:
            print(f'  [cached] merged.ll')

        if analyze_phases:
            phase_json = (mdir / 'vl_phase_analysis.json').resolve()
            print('  [analyze-phases] vlgpugen --analyze-phases merged.ll', flush=True)
            run([
                str(VLGPUGEN), str(merged_ll), '--analyze-phases',
                f'--analyze-phases-json={phase_json}',
            ])

        existing_storage_size = resolve_existing_storage_size(existing_meta)
        if reuse_gpu_patched_ll and existing_storage_size is not None:
            storage_size = existing_storage_size
            print(f'  [meta] reuse storage_size = {storage_size} bytes')
        else:
            print('  [probe] detecting storage_size...')
            root_storage_size = detect_storage_size(mdir, prefix)
            storage_size = syms_storage_size if syms_state_image else root_storage_size
            print(f'  root_storage_size = {root_storage_size} bytes')
            if syms_state_image:
                print(
                    f'  syms_storage_size = {storage_size} bytes; '
                    f'root_offset_in_state = {state_root_offset} bytes'
                )
            else:
                print(f'  storage_size = {storage_size} bytes')

        gpu_patched = mdir / 'vl_batch_gpu_patched.ll'
        if reuse_gpu_patched_ll:
            if not gpu_patched.exists():
                raise FileNotFoundError(f'missing patched GPU IR for reuse: {gpu_patched}')
            classifier_report = resolve_existing_classifier_report(mdir, existing_meta)
            launch_sequence = resolve_existing_launch_sequence(existing_meta)
            if launch_sequence is None:
                launch_sequence = resolve_manifest_launch_sequence(mdir)
                if launch_sequence is not None:
                    print('  [meta] reuse launch_sequence from vl_kernel_manifest.json')
            print(f'  [reuse] using existing {gpu_patched.name}')
        else:
            # Step 4: vlgpugen merged.ll → vl_batch_gpu.ll
            gpu_ll = mdir / 'vl_batch_gpu.ll'
            kernel_manifest = mdir / 'vl_kernel_manifest.json'
            print('  [vlgpugen] → vl_batch_gpu.ll')
            vg_cmd = [
                str(VLGPUGEN), str(merged_ll),
                f'--storage-size={storage_size}', f'--out={gpu_ll}',
                f'--classifier-report-out={classifier_report}',
            ]
            if syms_state_image:
                vg_cmd.append('--syms-state-image')
                vg_cmd.append(f'--state-root-offset={state_root_offset}')
            if kernel_split_phases:
                vg_cmd.append('--kernel-split=phases')
                vg_cmd.append(f'--kernel-manifest-out={kernel_manifest}')
            if kernel_probe_act_sequent_chunk_size:
                vg_cmd.append(
                    f'--kernel-probe-act-sequent-chunk-size={kernel_probe_act_sequent_chunk_size}'
                )
            run(vg_cmd)
            if kernel_split_phases:
                launch_sequence = load_launch_sequence_from_manifest(kernel_manifest)

            # Step 5a: VlGpuPasses.so のビルド (変更がなければ no-op)
            run(['make', '-C', str(PASSES_DIR), '--no-print-directory'])
            # Step 5b: EH lowering + x86 属性除去 + host I/O callsite stub + 収束パッチ
            print('  [opt] lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-stub-host-io-calls,vl-stub-timing-scheduler-context,vl-patch-convergence,dce,adce,simplifycfg,dce')
            vl_passes = 'lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-stub-host-io-calls,vl-stub-timing-scheduler-context,vl-patch-convergence,dce,adce,simplifycfg,dce'
            opt_cmd = [
                OPT,
                f'--load-pass-plugin={PASSES_SO}',
                f'-passes={vl_passes}',
                '-S',
                str(gpu_ll),
                '-o',
                str(gpu_patched),
            ]
            if syms_state_image:
                opt_cmd.insert(2, '--vl-preserve-convergence-threshold')
            run(opt_cmd)

        gpu_opt = mdir / 'vl_batch_gpu_opt.ll'
        gpu_opt_input, gpu_opt_workarounds = maybe_prepare_gpu_opt_input(
            prefix=prefix,
            mdir=mdir,
            gpu_patched=gpu_patched,
        )
        gpu_ir_workarounds.extend(gpu_opt_workarounds)
        gpu_host_cleanup = mdir / 'vl_batch_gpu_host_cleanup.ll'
        print('  [opt] vl-stub-host-io-calls,vl-stub-timing-scheduler-context,dce,adce,simplifycfg,dce → vl_batch_gpu_host_cleanup.ll')
        run([OPT, f'--load-pass-plugin={PASSES_SO}',
             '-passes=vl-stub-host-io-calls,vl-stub-timing-scheduler-context,dce,adce,simplifycfg,dce',
             '-S', str(gpu_opt_input), '-o', str(gpu_host_cleanup)])

        if gpu_opt_level == 'O0':
            gpu_opt_raw = gpu_host_cleanup
            print('  [opt] vl-sanitize-host-io-null-writes → vl_batch_gpu_opt.ll (gpu_opt=O0)')
        else:
            gpu_opt_raw = mdir / 'vl_batch_gpu_opt_raw.ll'
            print(f'  [opt -{gpu_opt_level}] → {gpu_opt_raw.name}')
            run([OPT, f'-{gpu_opt_level}', '-S', str(gpu_host_cleanup), '-o', str(gpu_opt_raw)])
            print('  [opt] vl-sanitize-host-io-null-writes → vl_batch_gpu_opt.ll')
        run([OPT, f'--load-pass-plugin={PASSES_SO}',
             '-passes=vl-sanitize-host-io-null-writes',
             '-S', str(gpu_opt_raw), '-o', str(gpu_opt)])

        gpu_llc_input, lifetime_workarounds = maybe_prepare_gpu_lifetime_retiming_input(
            mdir=mdir,
            gpu_opt=gpu_opt,
        )
        gpu_ir_workarounds.extend(lifetime_workarounds)

        # Step 6: llc → ptx
        gpu_ptx = mdir / 'vl_batch_gpu.ptx'
        print(f'  [llc] -march=nvptx64 -mcpu={sm} → vl_batch_gpu.ptx')
        run([LLC, '-march=nvptx64', f'-mcpu={sm}', str(gpu_llc_input), '-o', str(gpu_ptx)])

    if emit_ptx_module:
        out_module = gpu_ptx
        print(f'  [module] using PTX directly → {out_module.name}')
    else:
        # Step 7: ptxas → cubin
        if out_cubin is None:
            out_cubin = mdir / 'vl_batch_gpu.cubin'
        ptxas_cmd = [PTXAS, f'--gpu-name={sm}']
        if ptxas_opt_level is not None:
            ptxas_cmd.extend(['--opt-level', str(ptxas_opt_level)])
        ptxas_cmd.extend([str(gpu_ptx), '-o', str(out_cubin)])
        if ptxas_opt_level is None:
            print(f'  [ptxas] → {out_cubin.name}')
        else:
            print(f'  [ptxas -O{ptxas_opt_level}] → {out_cubin.name}')
        run(ptxas_cmd)
        out_module = out_cubin

    sz = out_module.stat().st_size
    meta_path = mdir / "vl_batch_gpu.meta.json"
    meta = {
        "schema_version": 1,
        "cubin": out_module.name,
        "storage_size": storage_size,
        "sm": sm,
        "kernel": "vl_eval_batch_gpu",
        "classifier_report": classifier_report.name,
        "clang_opt": (
            existing_meta.get("clang_opt", clang_opt)
            if incremental_mode == 'reuse_ptx' and existing_meta
            else clang_opt
        ),
        "gpu_opt_level": (
            existing_meta.get("gpu_opt_level", gpu_opt_level)
            if incremental_mode == 'reuse_ptx' and existing_meta
            else gpu_opt_level
        ),
        "cuda_module_format": "ptx" if emit_ptx_module else "cubin",
        "incremental_mode": incremental_mode,
    }
    if ptxas_opt_level is not None:
        meta["ptxas_opt_level"] = ptxas_opt_level
    if launch_sequence is not None:
        meta["launch_sequence"] = launch_sequence
    if gpu_ir_workarounds:
        meta["gpu_ir_workarounds"] = gpu_ir_workarounds
    if syms_state_image:
        hierarchy_state = syms_image_hierarchy_metadata(
            mdir,
            root_storage_size=root_storage_size,
            syms_storage_size=storage_size,
            state_root_offset=state_root_offset,
        )
    else:
        hierarchy_state = detect_hierarchy_state_metadata(mdir, storage_size)
    meta["hierarchy_state"] = hierarchy_state
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    if incremental_mode != 'reuse_ptx':
        opt_marker.write_text(clang_opt + "\n", encoding='utf-8')
    if incremental_mode == 'full':
        (mdir / '.vl_gpu_kernel_split').write_text(
            'phases' if kernel_split_phases else '', encoding='utf-8'
        )
    print(f"  [meta] → {meta_path.name}")
    print(f'\nDone: {out_module}  ({sz} bytes)  storage_size={storage_size}')
    return out_module, storage_size


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description='Verilator --cc output dir → GPU cubin'
    )
    p.add_argument('mdir', help='Verilator --cc output directory (contains *_classes.mk)')
    p.add_argument('--sm', default='sm_89', help='GPU arch (default: sm_89)')
    p.add_argument('--out', default=None, help='Output cubin path (default: mdir/vl_batch_gpu.cubin)')
    p.add_argument('--force', action='store_true', help='Re-run all steps even if outputs exist')
    p.add_argument(
        '--clang-O',
        dest='clang_opt',
        default='O1',
        choices=('O0', 'O1', 'O2', 'O3', 'Os', 'Oz'),
        help='clang optimization when emitting .ll (default O1). O2/O3 often shortens GPU _eval.',
    )
    p.add_argument(
        '--gpu-opt-level',
        default='O3',
        choices=('O0', 'O1', 'O2', 'O3'),
        help=(
            'Optimization after vl_batch_gpu_patched.ll. O0 copies patched.ll directly to '
            'vl_batch_gpu_opt.ll; useful for low-cost validation rebuilds.'
        ),
    )
    p.add_argument(
        '--ptxas-opt-level',
        type=int,
        choices=(0, 1, 2, 3),
        default=None,
        help='Optional ptxas optimization level override. Use 0 for faster validation builds.',
    )
    p.add_argument(
        '--emit-ptx-module',
        action='store_true',
        help='Skip ptxas and write meta that points directly at vl_batch_gpu.ptx.',
    )
    p.add_argument(
        '--analyze-phases',
        action='store_true',
        help='After merged.ll, run vlgpugen --analyze-phases and write mdir/vl_phase_analysis.json; then continue cubin build.',
    )
    p.add_argument(
        '--kernel-split-phases',
        action='store_true',
        help='Pass --kernel-split=phases to vlgpugen (ico/nba batch kernels + vl_eval_batch_gpu); meta gets launch_sequence.',
    )
    p.add_argument(
        '--kernel-probe-act-sequent-chunk-size',
        type=int,
        default=0,
        help=(
            'With --kernel-split-phases, emit non-launch act_sequent chunk probe kernels '
            'of this size into vl_kernel_manifest.json.'
        ),
    )
    p.add_argument(
        '--reuse-gpu-patched-ll',
        action='store_true',
        help='Skip vlgpugen and pass lowering; rebuild from an existing vl_batch_gpu_patched.ll.',
    )
    p.add_argument(
        '--reuse-ptx',
        action='store_true',
        help='Skip llc/vlgpugen and rebuild only from an existing vl_batch_gpu.ptx.',
    )
    p.add_argument(
        '--syms-state-image',
        action='store_true',
        help=(
            'Generate a non-flattened Verilator __Syms state-image kernel. '
            'Requires --syms-storage-size and --state-root-offset.'
        ),
    )
    p.add_argument(
        '--syms-storage-size',
        type=int,
        default=None,
        help='Bytes per __Syms state image when --syms-state-image is used.',
    )
    p.add_argument(
        '--state-root-offset',
        type=int,
        default=None,
        help='Byte offset of the root object inside each __Syms state image.',
    )
    p.add_argument(
        '--jobs',
        type=int,
        default=int(os.environ.get('BUILD_VL_GPU_JOBS', '1')),
        help='Parallel clang emission jobs for .cpp -> .ll (default: $BUILD_VL_GPU_JOBS or 1).',
    )
    args = p.parse_args()

    cubin, sz = build_vl_gpu(
        Path(args.mdir),
        sm=args.sm,
        out_cubin=Path(args.out) if args.out else None,
        force=args.force,
        clang_opt=args.clang_opt,
        gpu_opt_level=args.gpu_opt_level,
        ptxas_opt_level=args.ptxas_opt_level,
        emit_ptx_module=args.emit_ptx_module,
        analyze_phases=args.analyze_phases,
        kernel_split_phases=args.kernel_split_phases,
        kernel_probe_act_sequent_chunk_size=args.kernel_probe_act_sequent_chunk_size,
        reuse_gpu_patched_ll=args.reuse_gpu_patched_ll,
        reuse_ptx=args.reuse_ptx,
        syms_state_image=args.syms_state_image,
        syms_storage_size=args.syms_storage_size,
        state_root_offset=args.state_root_offset,
        jobs=args.jobs,
    )
    print(f'\nstorage_size={sz}')
    print(f'cubin={cubin}')


if __name__ == '__main__':
    main()
