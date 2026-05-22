from pathlib import Path

from build_vl_gpu_lifetime_analysis import (
    LIFETIME_RE,
    collect_wide_lifetime_markers,
    derived_pointer_owners,
    find_retime_eligible_allocas,
    find_wide_type_sizes,
    is_function_start,
    wide_lifetime_uses_and_unsafe_roots,
)


def _rewrite_wide_lifetime_markers(
    *,
    lines: list[str],
    retimed: list[str],
    uses: dict[str, list[int]],
    starts: dict[str, list[tuple[int, str]]],
    ends: dict[str, list[tuple[int, str]]],
) -> list[str]:
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
    return rewritten


def _retime_wide_lifetimes_in_function(
    lines: list[str],
    *,
    wide_type_sizes: dict[str, int],
) -> tuple[list[str], dict[str, int]]:
    allocas, starts, ends = collect_wide_lifetime_markers(
        lines,
        wide_type_sizes=wide_type_sizes,
    )

    eligible = find_retime_eligible_allocas(allocas=allocas, starts=starts, ends=ends)
    if not eligible:
        return lines, {'retimed_allocas': 0, 'retimed_functions': 0}

    # Track pointer SSA values derived from each stack slot. The rewrite only
    # handles pointer arithmetic that remains local to the function body.
    owner = derived_pointer_owners(lines, eligible)
    uses, unsafe = wide_lifetime_uses_and_unsafe_roots(lines, eligible=eligible, owner=owner)

    retimed = sorted(
        var for var in eligible
        if var not in unsafe and uses.get(var)
    )
    if not retimed:
        return lines, {'retimed_allocas': 0, 'retimed_functions': 0}

    rewritten = _rewrite_wide_lifetime_markers(
        lines=lines,
        retimed=retimed,
        uses=uses,
        starts=starts,
        ends=ends,
    )
    return rewritten, {
        'retimed_allocas': len(retimed),
        'retimed_functions': 1,
    }


def apply_gpu_wide_alloca_lifetime_retiming_text(ir_text: str) -> tuple[str, dict[str, int]]:
    lines = ir_text.splitlines()
    wide_type_sizes = find_wide_type_sizes(lines)
    if not wide_type_sizes:
        return ir_text, {'retimed_allocas': 0, 'retimed_functions': 0}

    rewritten: list[str] = []
    summary = {'retimed_allocas': 0, 'retimed_functions': 0}
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not is_function_start(line):
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
