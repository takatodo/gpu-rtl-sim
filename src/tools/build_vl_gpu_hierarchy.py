import re
import json
import subprocess
import tempfile
from pathlib import Path

from build_vl_gpu_inputs import CLANG, CXX_STANDARD, find_prefix, verilator_include_dir, verilator_vltstd_include_dir


UNSAFE_SYMS_GEP_RE = re.compile(
    r'getelementptr\s+inbounds\s+%class\.[^,\n]*__Syms[^,\n]*,'
)
SYMS_TBAA_RE = re.compile(r'^!\d+\s*=\s*!\{!"[^"]*__Syms",(?P<body>.*)\}$')
NONFLAT_ASSOC_ARRAY_MARKERS = (
    "VlAssocArray",
    "class.std::map",
)
RESIDUAL_TREE_MARKERS = (
    "std::_Rb_tree",
    "_Rb_tree",
    "class.std::multimap",
)
VEER_FLAT_PROGRAM_MEM_PATCH = "vl_gpu_veer_el2_flat_program_mem_patch.json"


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


def detect_syms_root_layout_probe(mdir: Path) -> dict[str, int] | None:
    """Compile a generated-header probe for sizeof(__Syms), sizeof(root), and TOP offset."""
    try:
        prefix = find_prefix(mdir)
    except FileNotFoundError:
        return None
    syms_h = mdir / f"{prefix}__Syms.h"
    root_h = mdir / f"{prefix}___024root.h"
    if not syms_h.is_file() or not root_h.is_file():
        return None
    probe_src = (
        "#include <cstddef>\n"
        "#include <cstdio>\n"
        f"#include \"{syms_h.resolve()}\"\n"
        "int main() {\n"
        f"  std::printf(\"sizeof_syms=%zu\\n\", sizeof({prefix}__Syms));\n"
        f"  std::printf(\"sizeof_root=%zu\\n\", sizeof({prefix}___024root));\n"
        f"  std::printf(\"offsetof_TOP=%zu\\n\", offsetof({prefix}__Syms, TOP));\n"
        "  return 0;\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "probe_syms_layout.cpp"
        exe = Path(tmp) / "probe_syms_layout"
        src.write_text(probe_src, encoding="utf-8")
        cmd = [
            CLANG,
            f"-std={CXX_STANDARD}",
            f"-I{mdir}",
            f"-I{verilator_include_dir()}",
            f"-I{verilator_vltstd_include_dir()}",
            str(src),
            "-o",
            str(exe),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError):
            return None
    values: dict[str, int] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            values[key] = int(value)
        except ValueError:
            continue
    required = {"sizeof_syms", "sizeof_root", "offsetof_TOP"}
    return values if required.issubset(values) else None


def syms_gep_covered_by_root_image(
    *, unsafe_count: int, syms_size: int | None, storage_size: int
) -> bool:
    if unsafe_count == 0:
        return True
    return syms_size is not None and syms_size <= storage_size


def detect_nonflat_assoc_array_state(ir_texts: list[tuple[Path, str]]) -> dict[str, object]:
    """Detect C++ associative containers that cannot be treated as flat GPU state."""
    markers: list[str] = []
    sources: list[str] = []
    residual_markers: list[str] = []
    residual_sources: list[str] = []
    for path, text in ir_texts:
        matched = [marker for marker in NONFLAT_ASSOC_ARRAY_MARKERS if marker in text]
        if matched:
            markers.extend(matched)
            sources.append(path.name)
        residual = [marker for marker in RESIDUAL_TREE_MARKERS if marker in text]
        if residual:
            residual_markers.extend(residual)
            residual_sources.append(path.name)
    detected = bool(markers)
    return {
        "nonflat_assoc_array_detected": detected,
        "nonflat_assoc_array_markers": list(dict.fromkeys(markers)),
        "nonflat_assoc_array_sources": list(dict.fromkeys(sources)),
        "assoc_array_gpu_lowering_supported": not detected,
        "residual_std_tree_detected": bool(residual_markers),
        "residual_std_tree_markers": list(dict.fromkeys(residual_markers)),
        "residual_std_tree_sources": list(dict.fromkeys(residual_sources)),
    }


def detect_veer_flat_program_memory_patch(mdir: Path) -> dict[str, object]:
    report_path = mdir / VEER_FLAT_PROGRAM_MEM_PATCH
    if not report_path.is_file():
        return {
            "veer_el2_flat_program_mem_patch_applied": False,
            "veer_el2_flat_program_mem_patch_report": None,
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "veer_el2_flat_program_mem_patch_applied": False,
            "veer_el2_flat_program_mem_patch_report": report_path.name,
            "veer_el2_flat_program_mem_patch_valid": False,
        }
    if not isinstance(report, dict):
        report = {}
    return {
        "veer_el2_flat_program_mem_patch_applied": report.get("applied") is True,
        "veer_el2_flat_program_mem_patch_report": report_path.name,
        "veer_el2_flat_program_mem_base_addr_hex": report.get("base_addr_hex"),
        "veer_el2_flat_program_mem_span_bytes": report.get("span_bytes"),
        "veer_el2_flat_program_mem_fields": report.get("fields"),
    }


def detect_hierarchy_state_metadata(mdir: Path, storage_size: int) -> dict[str, object]:
    """Summarize whether generated GPU IR needs Verilator __Syms state."""
    ir_texts = hierarchy_ir_texts(mdir)
    if not ir_texts:
        return {
            "state_image_kind": "root_image",
            "root_storage_size": storage_size,
            "unsafe_syms_gep_count": 0,
            "unsafe_syms_gep_covered_by_state_image": True,
            **detect_nonflat_assoc_array_state(ir_texts),
            **detect_veer_flat_program_memory_patch(mdir),
            "metadata_source": None,
        }
    primary_path, primary_text = ir_texts[0]
    syms_size = detect_syms_storage_size(ir_texts)
    unsafe_count = len(UNSAFE_SYMS_GEP_RE.findall(primary_text))
    root_offset = detect_root_offset_in_syms(ir_texts, storage_size=storage_size)
    syms_layout_probe = detect_syms_root_layout_probe(mdir)
    if root_offset is None and syms_layout_probe is not None:
        probed_root = syms_layout_probe.get("sizeof_root")
        probed_offset = syms_layout_probe.get("offsetof_TOP")
        if probed_root == storage_size and isinstance(probed_offset, int):
            root_offset = probed_offset
    if syms_size is None and syms_layout_probe is not None:
        syms_size = syms_layout_probe.get("sizeof_syms")
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
        "syms_root_layout_probe": syms_layout_probe,
        **detect_nonflat_assoc_array_state(ir_texts),
        **detect_veer_flat_program_memory_patch(mdir),
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
