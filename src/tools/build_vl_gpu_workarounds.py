import re
from pathlib import Path


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
