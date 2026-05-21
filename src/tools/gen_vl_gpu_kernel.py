#!/usr/bin/env python3
"""
gen_vl_gpu_kernel.py
Verilator --cc + clang++ -emit-llvm の merged.ll から
NVPTX GPU カーネルを生成する。

戦略:
  1. _eval から到達する define 済み関数だけ抽出
  2. 外部関数 (VL_FATAL_MT 等) を no-op stub に置き換え
  3. NVPTX ターゲット設定
  4. AoS-strided カーネルを追加
       thread i → _eval(base + i * storage_size)

Usage:
  python3 gen_vl_gpu_kernel.py <merged.ll> <storage_size> [out_gpu.ll]
"""

import re
import sys
from pathlib import Path

from llvm_ir_parse import extract_functions, reachable_from, external_calls
from llvm_stub_gen import make_no_op_stub
from vl_runtime_filter import is_runtime, detect_syms_buffer_size, detect_vlsyms_offset
from gen_vl_gpu_kernel_templates import (
    batch_kernel_lines as _batch_kernel_lines,
    header_lines as _template_header_lines,
    init_replication_kernel_lines as _init_replication_kernel_lines,
    metadata_lines as _metadata_lines,
    nvvm_decl_lines as _nvvm_decl_lines,
    patch_schedule_kernel_lines as _patch_schedule_kernel_lines,
)


def _find_eval_fn(all_funcs: dict[str, str], text: str) -> str:
    for name in all_funcs:
        if re.search(r'___024root___evalP', name) and '___eval_' not in name:
            return name
    for name in all_funcs:
        if '_eval' in name and re.search(r'define\s+void\s+@' + re.escape(name) + r'\s*\(ptr', text):
            return name
    raise RuntimeError('_eval 関数が見つかりません')


def _gpu_function_sets(eval_fn: str, all_funcs: dict[str, str]) -> tuple[set[str], set[str], set[str]]:
    needed_raw = reachable_from(eval_fn, all_funcs)
    print(f'到達可能な define 関数 (raw): {len(needed_raw)} 個')
    needed = {n for n in needed_raw if not is_runtime(n, all_funcs.get(n, ''))}
    forced_stubs = needed_raw - needed
    print(f'到達可能な define 関数 (GPU対象): {len(needed)} 個')
    if forced_stubs:
        print(f'ランタイム関数を stub 化: {len(forced_stubs)} 個')
    ext = external_calls(needed, all_funcs) | forced_stubs
    print(f'stub 必要な外部関数: {len(ext)} 個')
    return needed, forced_stubs, ext


def _header_lines(*, storage_size: int, eval_fn: str, vlsyms_offset: int | None) -> list[str]:
    return _template_header_lines(storage_size=storage_size, eval_fn=eval_fn, vlsyms_offset=vlsyms_offset)


def _type_definition_lines(text: str) -> list[str]:
    lines = [line for line in text.splitlines() if re.match(r'^%.*=\s*type\s', line)]
    lines.append('')
    return lines


def _global_lines(*, text: str, needed: set[str], all_funcs: dict[str, str]) -> list[str]:
    lines = [line for line in text.splitlines() if re.match(r'^@\.str', line)]
    global_defs: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r'^(@[\w.]+)\s*=', line)
        if m and not re.match(r'^@\.str', line):
            global_defs[m.group(1)] = line
    needed_globals: set[str] = set()
    for fn_name in needed:
        for ref in re.findall(r'@([\w.]+)', all_funcs[fn_name]):
            gname = f'@{ref}'
            if gname in global_defs:
                needed_globals.add(gname)
    if needed_globals:
        lines.append('; referenced globals (switch tables, const data, ...)')
        for gname in sorted(needed_globals):
            lines.append(global_defs[gname])
    lines.append('')
    return lines


def _stub_and_function_lines(*, ext: set[str], needed: set[str], all_funcs: dict[str, str], text: str) -> list[str]:
    lines: list[str] = []
    for ext_fn in sorted(ext):
        lines.append(f'; stub: {ext_fn}')
        lines.append(make_no_op_stub(ext_fn, text))
    for fn_name in sorted(needed):
        lines.append(all_funcs[fn_name])
        lines.append('')
    return lines


def generate_gpu_ll(merged_ll_path: Path, storage_size: int) -> str:
    text = merged_ll_path.read_text(encoding='utf-8')
    all_funcs = extract_functions(text)
    eval_fn = _find_eval_fn(all_funcs, text)
    print(f'eval 関数: @{eval_fn}')
    needed, _forced_stubs, ext = _gpu_function_sets(eval_fn, all_funcs)
    vlsyms_offset = detect_vlsyms_offset(text)
    syms_buffer_size = detect_syms_buffer_size(text) if vlsyms_offset is not None else None
    if vlsyms_offset is not None:
        print(f'vlSymsp オフセット: {vlsyms_offset} bytes (fake_syms_buf で null-safe 化)')
    else:
        print('vlSymsp オフセット: 未検出 (vlSyms 初期化スキップ)')

    lines = _header_lines(storage_size=storage_size, eval_fn=eval_fn, vlsyms_offset=vlsyms_offset)
    lines.extend(_type_definition_lines(text))
    if vlsyms_offset is not None:
        lines.append(f'@fake_syms_buf = internal global [{syms_buffer_size} x i8] zeroinitializer, align 64')
        lines.append('')
    lines.extend(_global_lines(text=text, needed=needed, all_funcs=all_funcs))
    lines.extend(_nvvm_decl_lines())
    lines.extend(_init_replication_kernel_lines())
    lines.extend(_stub_and_function_lines(ext=ext, needed=needed, all_funcs=all_funcs, text=text))
    lines.extend(_batch_kernel_lines(storage_size=storage_size, eval_fn=eval_fn, vlsyms_offset=vlsyms_offset))
    lines.extend(_patch_schedule_kernel_lines())
    lines.extend(_metadata_lines(text))

    return '\n'.join(lines)


def main() -> None:
    if len(sys.argv) < 3:
        print(f'Usage: {sys.argv[0]} <merged.ll> <storage_size> [out_gpu.ll]')
        sys.exit(1)

    merged_ll  = Path(sys.argv[1])
    storage_sz = int(sys.argv[2])
    out_path   = Path(sys.argv[3]) if len(sys.argv) > 3 \
                 else merged_ll.parent / 'vl_batch_gpu.ll'

    gpu_ll = generate_gpu_ll(merged_ll, storage_sz)
    out_path.write_text(gpu_ll, encoding='utf-8')
    print(f'Written: {out_path}')


if __name__ == '__main__':
    main()
