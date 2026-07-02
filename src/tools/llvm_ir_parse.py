"""
llvm_ir_parse.py
LLVM IR テキストからデータ構造を抽出するパーサ群。
副作用なし、テキスト → dict/set/tuple のみ。
"""

import re

_LLVM_GLOBAL_NAME = r'(?:"(?:\\.|[^"\\])*"|[-A-Za-z$._0-9]+)'
_DEFINE_PAT = re.compile(r'^define\b[^@\n]*@(' + _LLVM_GLOBAL_NAME + r')\s*\(')
_CALL_PAT = re.compile(r'(?:call|tail call|invoke)[^@\n]*@(' + _LLVM_GLOBAL_NAME + r')')


def _normalize_global_name(name: str) -> str:
    if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
        return name[1:-1]
    return name


def _called_global_names(body: str) -> list[str]:
    names: list[str] = []
    for line in body.splitlines():
        if re.search(r'\bcall\b[^@\n]*\basm\b', line):
            continue
        names.extend(_normalize_global_name(name) for name in _CALL_PAT.findall(line))
    return names


def called_global_names(body: str) -> list[str]:
    """body 内の直接 call/invoke 先グローバル名を返す。inline asm は除外する。"""
    return _called_global_names(body)


def extract_functions(text: str) -> dict[str, str]:
    """全 define 関数を {name: full_text} で返す"""
    funcs = {}
    i = 0
    lines = text.splitlines(keepends=True)
    n = len(lines)
    while i < n:
        line = lines[i]
        m = _DEFINE_PAT.match(line)
        if m:
            name = _normalize_global_name(m.group(1))
            body_lines = [line]
            depth = line.count('{') - line.count('}')
            i += 1
            while i < n and depth > 0:
                body_lines.append(lines[i])
                depth += lines[i].count('{') - lines[i].count('}')
                i += 1
            funcs[name] = ''.join(body_lines)
        else:
            i += 1
    return funcs


def reachable_from(start: str, funcs: dict[str, str]) -> set[str]:
    """start から call/invoke で到達できる全関数名 (define 済みのみ)"""
    visited: set[str] = set()
    queue = [start]
    while queue:
        fn = queue.pop()
        if fn in visited:
            continue
        visited.add(fn)
        body = funcs.get(fn, '')
        for callee in _called_global_names(body):
            if callee in funcs and callee not in visited:
                queue.append(callee)
    return visited


def external_calls(names: set[str], funcs: dict[str, str]) -> set[str]:
    """names の関数群から呼ばれる、funcs に定義のない外部関数"""
    ext: set[str] = set()
    for fn in names:
        body = funcs.get(fn, '')
        for callee in _called_global_names(body):
            if callee not in funcs and not callee.startswith('llvm.'):
                ext.add(callee)
    return ext
