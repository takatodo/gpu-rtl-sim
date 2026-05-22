"""Root-layout probing helpers for hybrid comparison."""

from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

from build_vl_gpu import CLANG, CXX_STANDARD, find_prefix, verilator_include_dir


FIELD_MACRO_RE = re.compile(r"^\s*VL_(?:IN|OUT)\d*\(\s*([A-Za-z_]\w*)\s*,")
FIELD_DECL_RE = re.compile(r"([A-Za-z_]\w*)\s*;\s*$")
FIELD_DECL_WITH_TYPE_RE = re.compile(
    r"^\s*(?P<decl_type>.+?)\s+(?P<name>[A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*;\s*$"
)
SECTION_COMMENT_RE = re.compile(r"^\s*//\s+([A-Z][A-Z0-9_ ]+)\s*$")
VERILATOR_INTERNAL_FIELDS = {"vlSymsp", "vlNamep", "__VdlySched"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_root_member_declarations(root_h: Path) -> list[dict[str, str]]:
    declarations: list[dict[str, str]] = []
    section = ""
    for raw_line in root_h.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        section_match = SECTION_COMMENT_RE.match(line)
        if section_match:
            section = section_match.group(1)
            continue
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if line in {"public:", "private:", "protected:", "};"}:
            continue
        if line.startswith("class ") or line.startswith("struct {"):
            continue
        macro_match = FIELD_MACRO_RE.match(line)
        if macro_match:
            declarations.append(
                {
                    "name": macro_match.group(1),
                    "decl_type": line.split("(", 1)[0].strip(),
                    "section": section,
                    "declaration": line,
                }
            )
            continue
        if "(" in line or ")" in line:
            continue
        decl_with_type_match = FIELD_DECL_WITH_TYPE_RE.match(line)
        if decl_with_type_match:
            declarations.append(
                {
                    "name": decl_with_type_match.group("name"),
                    "decl_type": decl_with_type_match.group("decl_type").strip(),
                    "section": section,
                    "declaration": line,
                }
            )
            continue
        decl_match = FIELD_DECL_RE.search(line)
        if decl_match:
            declarations.append(
                {
                    "name": decl_match.group(1),
                    "decl_type": "",
                    "section": section,
                    "declaration": line,
                }
            )
    return declarations


def extract_root_member_names(root_h: Path) -> list[str]:
    return [declaration["name"] for declaration in extract_root_member_declarations(root_h)]


def classify_field_role(field_name: str) -> str:
    if field_name.startswith("__V") or field_name in VERILATOR_INTERNAL_FIELDS:
        return "verilator_internal"
    if "__DOT__" in field_name:
        return "design_state"
    if field_name.endswith("_i") or field_name.endswith("_o"):
        return "top_level_io"
    return "other"


def probe_root_layout(mdir: Path) -> list[dict[str, int | str]]:
    prefix = find_prefix(mdir)
    root_type = f"{prefix}___024root"
    root_h = mdir / f"{root_type}.h"
    declarations = extract_root_member_declarations(root_h)
    member_names = [entry["name"] for entry in declarations]
    if not member_names:
        return []
    metadata_by_name = {entry["name"]: entry for entry in declarations}

    probe_lines = ["#include <cstddef>", "#include <cstdio>", f'#include "{root_h.resolve()}"', "int main() {"]
    for name in member_names:
        probe_lines.append(
            f'  std::printf("{name}\\t%zu\\t%zu\\n", '
            f"offsetof({root_type}, {name}), sizeof((({root_type}*)nullptr)->{name}));"
        )
    probe_lines.extend(["  return 0;", "}"])
    probe_src = "\n".join(probe_lines) + "\n"

    with tempfile.TemporaryDirectory(prefix="vl_root_layout_") as tmpdir:
        tmp = Path(tmpdir)
        src = tmp / "probe_layout.cpp"
        exe = tmp / "probe_layout"
        src.write_text(probe_src, encoding="utf-8")
        cmd = [
            CLANG,
            f"-std={CXX_STANDARD}",
            "-Wno-invalid-offsetof",
            f"-I{mdir}",
            f"-I{verilator_include_dir()}",
            str(src),
            "-o",
            str(exe),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        result = subprocess.run([str(exe)], check=True, capture_output=True, text=True)

    layout: list[dict[str, int | str]] = []
    for line in result.stdout.splitlines():
        name, offset, size = line.split("\t")
        entry: dict[str, int | str] = {"name": name, "offset": int(offset), "size": int(size)}
        metadata = metadata_by_name.get(name)
        if metadata:
            entry["decl_type"] = metadata.get("decl_type", "")
            entry["section"] = metadata.get("section", "")
            entry["declaration"] = metadata.get("declaration", "")
        layout.append(entry)
    layout.sort(key=lambda entry: (int(entry["offset"]), int(entry["size"]), str(entry["name"])))
    return layout
