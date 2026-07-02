"""Plan the next NVDLA hot-SS hybrid measurements.

This consumes the non-VeeR next queue and produces concrete commands for the
measured NVDLA hot-SS lane. It is a plan only: no Verilator build, host probe,
GPU launch, timing run, or speedup claim is performed here.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_QUEUE = Path("reports/rtlmeter_non_veer_hybrid_next_queue.json")
DEFAULT_TEMPLATE = Path("config/slice_launch_templates/nvdla_cmac_a2cacc.json")


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_shape(shape: object) -> tuple[int, int] | None:
    if not isinstance(shape, str):
        return None
    pieces = shape.lower().split("x", 1)
    if len(pieces) != 2:
        return None
    try:
        nstates = int(pieces[0])
        steps = int(pieces[1])
    except ValueError:
        return None
    if nstates <= 0 or steps <= 0:
        return None
    return nstates, steps


def _shape(nstates: int, steps: int) -> str:
    return f"{nstates}x{steps}"


def _queue_item(queue: Mapping[str, Any], item_id: str) -> Mapping[str, Any]:
    items = queue.get("queue")
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, Mapping) and item.get("id") == item_id:
            return item
    return {}


def _repeat_command(template: str, shape: str, repeat: int, report_out: str) -> list[str]:
    return [
        "PYTHONDONTWRITEBYTECODE=1",
        "python3",
        "src/tools/hybrid_template_repeat_median.py",
        template,
        "--shape",
        shape,
        "--repeat",
        str(repeat),
        "--write-report",
        "--report-out",
        report_out,
    ]


def _dry_run_command(template: str, shape: str) -> list[str]:
    return [
        "PYTHONDONTWRITEBYTECODE=1",
        "python3",
        "src/tools/run_hybrid_template.py",
        template,
        "--shape",
        shape,
        "--dry-run",
    ]


def _plan_item(
    *,
    order: int,
    item_id: str,
    shape: str,
    purpose: str,
    template: str,
    repeat: int,
    report_stem: str,
    dry_run_required: bool = True,
) -> dict[str, Any]:
    report_out = f"reports/{report_stem}_{shape}.json"
    commands = {
        "repeat_median": _repeat_command(template, shape, repeat, report_out),
    }
    if dry_run_required:
        commands["dry_run"] = _dry_run_command(template, shape)
    return {
        "order": order,
        "id": item_id,
        "shape": shape,
        "purpose": purpose,
        "repeat": repeat,
        "report_out": report_out,
        "commands": commands,
        "acceptance": [
            "coverage_output_equivalence_all_passed",
            "median.cpu_elapsed_ms",
            "median.hybrid_wall_ms",
            "median.cpu_to_hybrid_wall_speedup",
            "non_claims_present",
        ],
    }


def build_plan(repo_root: Path, *, queue_path: Path = DEFAULT_QUEUE, repeat: int = 3) -> dict[str, Any]:
    queue = _load_json(repo_root / queue_path)
    nvdla_item = _queue_item(queue, "nvdla_hot_ss_measurement_extension")
    if not nvdla_item:
        raise ValueError("queue does not contain nvdla_hot_ss_measurement_extension")
    next_measurement = _mapping(nvdla_item.get("next_measurement"))
    preferred_shape = next_measurement.get("preferred_shape")
    parsed = _parse_shape(preferred_shape)
    if parsed is None:
        raise ValueError("NVDLA queue item is missing a valid preferred_shape")
    nstates, steps = parsed
    template = _display_path(repo_root / DEFAULT_TEMPLATE, repo_root=repo_root)
    if not (repo_root / DEFAULT_TEMPLATE).exists():
        raise ValueError(f"missing NVDLA hot-SS template: {DEFAULT_TEMPLATE}")

    half_state = max(1, nstates // 2)
    double_state = nstates * 2
    plan_items = [
        _plan_item(
            order=1,
            item_id="confirm_best_observed_a2cacc_shape_repeat_median",
            shape=_shape(nstates, steps),
            purpose="Repeat the best observed NVDLA hot-SS shape before extending the claim boundary.",
            template=template,
            repeat=repeat,
            report_stem="nvdla_cmac_a2cacc_repeat_median",
        ),
        _plan_item(
            order=2,
            item_id="check_lower_neighbor_same_steps",
            shape=_shape(half_state, steps),
            purpose="Check whether the same repeated-step bucket remains favorable below the current best state count.",
            template=template,
            repeat=repeat,
            report_stem="nvdla_cmac_a2cacc_repeat_median",
        ),
        _plan_item(
            order=3,
            item_id="probe_larger_state_batch_same_steps",
            shape=_shape(double_state, steps),
            purpose="Probe whether the small a2cacc hot-SS boundary continues scaling above the current best measured shape.",
            template=template,
            repeat=repeat,
            report_stem="nvdla_cmac_a2cacc_repeat_median",
        ),
        _plan_item(
            order=4,
            item_id="separate_state_batch_from_repeated_step_effect",
            shape=_shape(nstates, 1),
            purpose="Separate state-batch benefit from repeated-step benefit inside the same a2cacc hot-SS boundary.",
            template=template,
            repeat=repeat,
            report_stem="nvdla_cmac_a2cacc_repeat_median",
        ),
    ]

    return {
        "schema_version": 1,
        "surface": "rtlmeter_nvdla_hot_ss_measurement_plan",
        "status": "planned_not_run",
        "source_queue": _display_path(repo_root / queue_path, repo_root=repo_root),
        "target": "NVDLA.nvdla_cmac_a2cacc",
        "template": template,
        "source_queue_item": {
            "id": nvdla_item.get("id"),
            "status": nvdla_item.get("status"),
            "preferred_shape": preferred_shape,
            "preferred_bucket": next_measurement.get("preferred_bucket"),
        },
        "planned_measurement_count": len(plan_items),
        "planned_measurements": plan_items,
        "deferred": [
            {
                "target": "NVDLA.nvdla_cmac_core_mac",
                "reason": "recent local 32x1 refresh hit high ptxas compile cost; keep this plan on smaller hot-SS a2cacc first",
            },
            {
                "target": "Vortex:mini:hello",
                "reason": "second queue item; first finish lowered-TB memory helper integration and observable authority",
            },
        ],
        "non_claims": [
            "plan_only_not_measurement",
            "no_new_speedup_claim",
            "not_full_nvdla_execution",
            "not_automatic_hybrid_partition",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--queue", default=DEFAULT_QUEUE.as_posix(), help="Input non-VeeR hybrid next queue JSON")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        if args.repeat <= 0:
            raise ValueError("--repeat must be positive")
        plan = build_plan(Path(args.repo_root), queue_path=Path(args.queue), repeat=args.repeat)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
