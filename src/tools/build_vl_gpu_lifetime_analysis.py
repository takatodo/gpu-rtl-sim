"""Analysis helpers for VlWide lifetime retiming."""

from __future__ import annotations

import re


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


def find_wide_type_sizes(lines: list[str]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for line in lines:
        match = VL_WIDE_TYPE_RE.match(line)
        if match:
            sizes[match.group(1)] = int(match.group(2)) * 4
    return sizes


def is_function_start(line: str) -> bool:
    return line.startswith('define ') and '{' in line


def collect_wide_lifetime_markers(
    lines: list[str],
    *,
    wide_type_sizes: dict[str, int],
) -> tuple[dict[str, dict[str, int | str]], dict[str, list[tuple[int, str]]], dict[str, list[tuple[int, str]]]]:
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
    return allocas, starts, ends


def find_retime_eligible_allocas(
    *,
    allocas: dict[str, dict[str, int | str]],
    starts: dict[str, list[tuple[int, str]]],
    ends: dict[str, list[tuple[int, str]]],
) -> set[str]:
    return {
        var
        for var in allocas
        if len(starts.get(var, [])) == 1 and len(ends.get(var, [])) == 1
    }


def derived_pointer_owners(lines: list[str], eligible: set[str]) -> dict[str, str]:
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
    return owner


def wide_lifetime_uses_and_unsafe_roots(
    lines: list[str],
    *,
    eligible: set[str],
    owner: dict[str, str],
) -> tuple[dict[str, list[int]], set[str]]:
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

        if 'call ' in line and '@llvm.' not in line:
            unsafe.update(roots)
        for token in tokens:
            if re.search(r'\bstore\s+ptr\s+' + re.escape(token) + r'\b', line):
                unsafe.add(owner[token])
            if re.search(r'\bret\s+ptr\s+' + re.escape(token) + r'\b', line):
                unsafe.add(owner[token])
    return uses, unsafe
