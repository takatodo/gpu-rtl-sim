from __future__ import annotations

import re
from pathlib import Path

from results_reproduction import REPO_ROOT, ReproductionCommand, format_command


LOCAL_ABSOLUTE_PATH_PATTERN = re.compile(
    r"/(?:home|tmp|Users|var|mnt|workspace|root)/[^\s'\",;)]+"
)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def shape_tag(*, shape: str | None, limit: int | None) -> str:
    if shape is not None:
        return shape.replace("/", "_")
    if limit is not None:
        return f"limit{limit}"
    return "unshaped"


def sanitize_local_absolute_paths(text: str) -> str:
    return LOCAL_ABSOLUTE_PATH_PATTERN.sub("<local-absolute-path>", text)


def format_report_command(command: ReproductionCommand) -> str:
    rendered = format_command(command).replace(str(REPO_ROOT), ".")
    return sanitize_local_absolute_paths(rendered)


def default_summary_path(*, target: str, shape: str | None, limit: int | None, mode: str) -> Path:
    mode_tag = mode.replace("-", "_")
    return REPO_ROOT / "reports" / f"hybrid_benchmark_{target}_{mode_tag}_{shape_tag(shape=shape, limit=limit)}.json"
