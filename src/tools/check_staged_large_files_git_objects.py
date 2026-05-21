from __future__ import annotations

import subprocess
from typing import Sequence

try:
    from .check_staged_large_files_paths import unique_in_order
    from .check_staged_large_files_types import GitSizeCheckError
except ImportError:  # pragma: no cover - exercised when run as a script.
    from check_staged_large_files_paths import unique_in_order
    from check_staged_large_files_types import GitSizeCheckError


def batch_object_sizes(object_ids: Sequence[str]) -> list[int]:
    if not object_ids:
        return []

    result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectsize)"],
        check=False,
        input="".join(f"{object_id}\n" for object_id in object_ids),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git cat-file failed"
        raise GitSizeCheckError(detail)

    sizes: list[int] = []
    for object_id, line in zip(object_ids, result.stdout.splitlines()):
        try:
            sizes.append(int(line))
        except ValueError:
            raise GitSizeCheckError(f"could not parse staged blob size for {object_id}: {line!r}")
    if len(sizes) != len(object_ids):
        raise GitSizeCheckError("git cat-file returned fewer size records than requested")
    return sizes


def batch_object_size_map(object_ids: Sequence[str]) -> dict[str, int]:
    unique_ids = unique_in_order(object_ids)
    sizes = batch_object_sizes(unique_ids)
    return dict(zip(unique_ids, sizes))
