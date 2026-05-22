import re
from pathlib import Path


UNSAFE_SYMS_GEP_RE = re.compile(
    r'getelementptr\s+inbounds\s+%class\.[^,\n]*__Syms[^,\n]*,'
)
SYMS_TBAA_RE = re.compile(r'^!\d+\s*=\s*!\{!"[^"]*__Syms",(?P<body>.*)\}$')


def hierarchy_ir_texts(mdir: Path) -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding='utf-8'))
        for path in (mdir / 'vl_batch_gpu_opt.ll', mdir / 'vl_batch_gpu.ll')
        if path.is_file()
    ]


def detect_syms_storage_size(ir_texts: list[tuple[Path, str]]) -> int | None:
    syms_size = None
    for _, text in ir_texts:
        for line in text.splitlines():
            if "__Syms" not in line:
                continue
            for match in re.finditer(r'dereferenceable\((\d+)\)', line):
                syms_size = max(syms_size or 0, int(match.group(1)))
    return syms_size


def detect_root_offset_in_syms(
    ir_texts: list[tuple[Path, str]], *, storage_size: int
) -> int | None:
    for _, text in ir_texts:
        for line in text.splitlines():
            match = SYMS_TBAA_RE.match(line)
            if not match:
                continue
            offsets = [int(raw) for raw in re.findall(r'i64\s+(\d+)', match.group('body'))]
            for left, right in zip(offsets, offsets[1:]):
                if right - left == storage_size:
                    return left
    return None


def syms_gep_covered_by_root_image(
    *, unsafe_count: int, syms_size: int | None, storage_size: int
) -> bool:
    if unsafe_count == 0:
        return True
    return syms_size is not None and syms_size <= storage_size


def detect_hierarchy_state_metadata(mdir: Path, storage_size: int) -> dict[str, object]:
    """Summarize whether generated GPU IR needs Verilator __Syms state."""
    ir_texts = hierarchy_ir_texts(mdir)
    if not ir_texts:
        return {
            "state_image_kind": "root_image",
            "root_storage_size": storage_size,
            "unsafe_syms_gep_count": 0,
            "unsafe_syms_gep_covered_by_state_image": True,
            "metadata_source": None,
        }
    primary_path, primary_text = ir_texts[0]
    syms_size = detect_syms_storage_size(ir_texts)
    unsafe_count = len(UNSAFE_SYMS_GEP_RE.findall(primary_text))
    root_offset = detect_root_offset_in_syms(ir_texts, storage_size=storage_size)
    covered = syms_gep_covered_by_root_image(
        unsafe_count=unsafe_count,
        syms_size=syms_size,
        storage_size=storage_size,
    )
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
