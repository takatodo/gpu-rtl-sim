from __future__ import annotations


def validate_repeat_median_request(*, repeat_count: int, phases: int) -> None:
    if repeat_count <= 0:
        raise ValueError("--persistent-resident-state-abi-repeat-median must be positive")
    if phases <= 0:
        raise ValueError("--persistent-resident-state-abi-phases must be positive")
