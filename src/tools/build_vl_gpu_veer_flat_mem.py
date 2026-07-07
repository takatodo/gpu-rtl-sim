"""Scoped VeeR-EL2 generated-source patch for GPU-friendly program memories."""

from __future__ import annotations

import json
from pathlib import Path


PATCH_MARKER = "VL_GPU_VEER_EL2_FLAT_PROGRAM_MEM_PATCH"
FLAT_MEM_SPAN_BYTES = 64 * 1024
PROGRAM_MEM_BASE_HEX = "0x80000000U"
CONTROL_MEM_BASE_HEX = "0x10000000U"
CONTROL_MEM_SPAN_BYTES = 16
PATCH_REPORT = "vl_gpu_veer_el2_flat_program_mem_patch.json"


def _flat_mem_definition() -> str:
    return f"""
#ifndef {PATCH_MARKER}
#define {PATCH_MARKER} 1
template <IData Base, IData Span>
class VlGpuFlatByteMem final {{
    CData m_defaultValue = 0;
    CData m_storage[Span] = {{}};
    CData m_controlStorage[{CONTROL_MEM_SPAN_BYTES}U] = {{}};
    CData m_unmappedWriteSink = 0;

  public:
    CData& atDefault() {{ return m_defaultValue; }}
    const CData& atDefault() const {{ return m_defaultValue; }}
    CData& at(const IData& index) {{
        if (index >= {CONTROL_MEM_BASE_HEX} && index < ({CONTROL_MEM_BASE_HEX} + {CONTROL_MEM_SPAN_BYTES}U)) {{
            return m_controlStorage[index - {CONTROL_MEM_BASE_HEX}];
        }}
        if (index < Base) return m_defaultValue;
        const IData offset = index - Base;
        if (offset >= Span) return m_unmappedWriteSink;
        return m_storage[offset];
    }}
    const CData& at(const IData& index) const {{
        if (index >= {CONTROL_MEM_BASE_HEX} && index < ({CONTROL_MEM_BASE_HEX} + {CONTROL_MEM_SPAN_BYTES}U)) {{
            return m_controlStorage[index - {CONTROL_MEM_BASE_HEX}];
        }}
        if (index < Base) return m_defaultValue;
        const IData offset = index - Base;
        if (offset >= Span) return m_defaultValue;
        return m_storage[offset];
    }}
}};
template <IData Base, IData Span>
void VL_READMEM_N(bool hex, int bits, const std::string& filename,
                  VlGpuFlatByteMem<Base, Span>& obj, QData start, QData end) VL_MT_SAFE {{
    VlReadMem rmem{{hex, bits, filename, start, end}};
    if (VL_UNLIKELY(!rmem.isOpen())) return;
    while (true) {{
        QData addr;
        std::string data;
        if (rmem.get(addr, data)) {{
            rmem.setData(&(obj.at(static_cast<IData>(addr))), data);
        }} else {{
            break;
        }}
    }}
}}
#endif
""".strip()


def _replacement_line(field_name: str) -> str:
    return (
        f"    VlGpuFlatByteMem<{PROGRAM_MEM_BASE_HEX}, {FLAT_MEM_SPAN_BYTES}U> "
        f"{field_name};"
    )


def _upsert_flat_mem_definition(text: str) -> tuple[str, bool]:
    definition = _flat_mem_definition()
    start = text.find(f"#ifndef {PATCH_MARKER}")
    if start != -1:
        end = text.find("\n#endif", start)
        if end == -1:
            return text, False
        end += len("\n#endif")
        updated = f"{text[:start]}{definition}{text[end:]}"
        return updated, updated != text

    include_anchor = 'class Vsim__Syms;\n'
    if include_anchor not in text:
        return text, False
    return text.replace(include_anchor, f"{definition}\n\n{include_anchor}", 1), True


def patch_veer_el2_flat_program_mem(mdir: Path, prefix: str) -> dict[str, object]:
    """Patch VeeR-EL2 generated program memories from VlAssocArray to flat bytes.

    This is intentionally narrow: it recognizes only the RTLMeter VeeR-EL2
    `tb_top` root header field names used by the current FC-064 target.
    """
    header = mdir / f"{prefix}___024root.h"
    report: dict[str, object] = {
        "schema_version": 1,
        "patch": "veer_el2_flat_program_mem",
        "header": header.name,
        "applied": False,
        "changed": False,
        "base_addr_hex": PROGRAM_MEM_BASE_HEX.rstrip("U"),
        "span_bytes": FLAT_MEM_SPAN_BYTES,
        "fields": [
            "tb_top__DOT__imem__DOT__mem",
            "tb_top__DOT__lmem__DOT__mem",
        ],
        "missing_context": [],
    }
    if not header.is_file():
        report["missing_context"] = ["root_header"]
        return report

    text = header.read_text(encoding="utf-8")
    fields = {
        "tb_top__DOT__imem__DOT__mem": (
            "    VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__imem__DOT__mem;"
        ),
        "tb_top__DOT__lmem__DOT__mem": (
            "    VlAssocArray<IData/*31:0*/, CData/*7:0*/> tb_top__DOT__lmem__DOT__mem;"
        ),
    }
    missing = [field for field, needle in fields.items() if needle not in text and field not in text]
    if missing:
        report["missing_context"] = [f"{field}_field" for field in missing]
        return report

    patched, definition_ready = _upsert_flat_mem_definition(text)
    if not definition_ready and PATCH_MARKER not in patched:
        report["missing_context"] = ["root_header_insertion_anchor"]
        return report

    replaced_fields: list[str] = []
    for field, needle in fields.items():
        replacement = _replacement_line(field)
        if needle in patched:
            patched = patched.replace(needle, replacement, 1)
            replaced_fields.append(field)
        elif replacement in patched:
            replaced_fields.append(field)
        else:
            report["missing_context"] = [*report["missing_context"], f"{field}_replacement"]

    report["applied"] = len(replaced_fields) == len(fields) and not report["missing_context"]
    report["replaced_fields"] = replaced_fields
    if patched != text:
        header.write_text(patched, encoding="utf-8")
        report["changed"] = True

    (mdir / PATCH_REPORT).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
