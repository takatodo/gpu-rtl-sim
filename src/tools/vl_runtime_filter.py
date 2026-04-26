"""
vl_runtime_filter.py
Verilator 生成コードの GPU 実行可否を判定する。

- is_runtime(): GPU で実行できない関数かどうかを判定
- detect_vlsyms_offset(): vlSymsp フィールドのバイトオフセットを TBAA から検出
- detect_syms_buffer_size(): fake vlSymsp buffer に必要な最小サイズを検出
"""

import re

# GPU で stub 化すべき Verilated ランタイム / C++ 標準ライブラリのプレフィックス
_RUNTIME_PREFIXES = (
    '_ZN9Verilated',        # Verilated::* クラスメソッド
    '_ZNK9Verilated',
    '_ZN16VerilatedContext',
    '_ZNK16VerilatedContext',
    '_ZN14VerilatedModel',
    '_ZNK14VerilatedModel',
    '_ZN9VlDeleter',
    '_ZNSt',                # std::* (string, exception etc.)
    '_ZSt',
    '_Z13sc_time_stamp',
    '_Z15vl_time_stamp',
    '__cxa_',
    '_ZTHN',                # TLS variable helper
)

# vlSyms を参照するがシミュレーション本体の関数 → stub 化しない
# fake_syms_buf による null-safe 化で対応する
_FORCE_INCLUDE_PATTERNS = (
    '___ico_sequent',
    '___nba_comb',
)


def is_runtime(name: str, func_body: str) -> bool:
    """
    GPU で実行できない関数なら True を返す。

    stub 化の判定基準:
    1. _FORCE_INCLUDE_PATTERNS に一致 → 必ず False (GPU に含める)
    2. _RUNTIME_PREFIXES に一致 → True
    3. static guard (@_ZGVZ) を参照 → True
    4. VerilatedSyms / _Syms を参照 → True
    """
    if any(pat in name for pat in _FORCE_INCLUDE_PATTERNS):
        return False
    if "___024root___" in name:
        return False
    if any(name.startswith(p) for p in _RUNTIME_PREFIXES):
        return True
    if re.search(r'@_ZGVZ', func_body):
        return True
    if re.search(r'VerilatedSyms|_gpu_cov_tb__Syms', func_body):
        return True
    return False


def _metadata_i64_offset(text: str, metadata_id: str) -> int | None:
    m = re.search(
        rf'^!{re.escape(metadata_id)}\s*=\s*!\{{.*,\s*i64\s+(\d+)\s*\}}',
        text,
        re.MULTILINE,
    )
    if m:
        return int(m.group(1))
    return None


def detect_vlsyms_offset(text: str) -> int | None:
    """
    TBAA メタデータから vlSymsp フィールドのバイトオフセットを検出する。
    root class から load され、その後 `__Syms` GEP の base として使われる
    pointer load を優先する。大きい Verilator root では先頭にも pointer
    field が並ぶため、root TBAA ノードの最初の "any pointer" を vlSymsp と
    みなすと offset 0 を誤検出する。
    例: !10 = !{!"..._024root", ..., !31, i64 2000, !31, i64 2008}  → 2000
    """
    load_pat = re.compile(
        r'^\s*(%[-A-Za-z$._0-9]+)\s*=\s*getelementptr inbounds '
        r'%class\.[^,\n]*___024root[^,\n]*,\s*ptr\s+%[-A-Za-z$._0-9]+,'
        r'\s*i64\s+0,\s*i32\s+\d+\s*\n'
        r'\s*(%[-A-Za-z$._0-9]+)\s*=\s*load\s+ptr,\s+ptr\s+\1([^\n]*)',
        re.MULTILINE,
    )
    for m in load_pat.finditer(text):
        loaded_value = m.group(2)
        load_suffix = m.group(3)
        tbaa_m = re.search(r'!tbaa\s+!(\d+)', load_suffix)
        tbaa_id = tbaa_m.group(1) if tbaa_m else None
        syms_use_pat = re.compile(
            r'getelementptr inbounds %class\.[^,\n]*__Syms[^,\n]*,\s*ptr\s+'
            + re.escape(loaded_value)
            + r'(?=[,\s])'
        )
        if not syms_use_pat.search(text):
            continue
        if tbaa_id is None:
            continue
        offset = _metadata_i64_offset(text, tbaa_id)
        if offset is not None:
            return offset

    m = re.search(r'^(!(\d+))\s*=\s*!\{!"any pointer"', text, re.MULTILINE)
    if not m:
        return None
    any_ptr_id = m.group(2)
    pat = re.compile(
        r'^!\d+\s*=\s*!\{!"[^"]*_024root".*?!'
        + re.escape(any_ptr_id) + r',\s*i64\s+(\d+)',
        re.MULTILINE,
    )
    m2 = pat.search(text)
    if m2:
        return int(m2.group(1))
    return None


def detect_syms_buffer_size(text: str, minimum: int = 4096) -> int:
    """
    fake_syms_buf に必要なバイト数を検出する。

    Verilator の Syms ctor/dtor 宣言には `ptr ... dereferenceable(N)` が付く
    ことが多い。これを使い、固定 4096 を超える Syms GEP でも null-safe
    buffer の範囲内に収める。
    """
    size = minimum
    for line in text.splitlines():
        if "__Syms" not in line:
            continue
        for m in re.finditer(r'dereferenceable\((\d+)\)', line):
            size = max(size, int(m.group(1)))
    return size
