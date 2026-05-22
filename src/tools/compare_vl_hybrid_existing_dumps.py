from __future__ import annotations

import json
from pathlib import Path

from compare_vl_hybrid_acceptance import (
    build_acceptance_policies,
    select_acceptance_policy,
)
from compare_vl_hybrid_coverage import (
    build_coverage_output_policy_summary,
    select_coverage_output_target,
    validate_coverage_output_gate,
)
from compare_vl_hybrid_layout import probe_root_layout
from compare_vl_hybrid_state_compare import compare_state_dumps

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def read_storage_size_from_meta(mdir: Path) -> int:
    meta_path = mdir / "vl_batch_gpu.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    storage_size = int(meta["storage_size"])
    if storage_size <= 0:
        raise ValueError(f"invalid storage_size in {meta_path}: {storage_size}")
    return storage_size


def select_coverage_target_entry(gate: dict, coverage_output_target: str | None) -> dict:
    target_scope = gate.get("target_scope") or []
    if coverage_output_target is not None:
        return select_coverage_output_target(gate, coverage_output_target)
    if len(target_scope) == 1:
        return dict(target_scope[0])
    names = [str(entry.get("target")) for entry in target_scope]
    raise SystemExit(
        "--coverage-output-target is required when the gate has multiple "
        f"target_scope entries; available: {names}"
    )


def load_coverage_manifest(
    *,
    gate_path: Path,
    target_entry: dict,
) -> tuple[dict | None, str | None]:
    manifest_relative = target_entry.get("coverage_manifest")
    if not manifest_relative:
        return None, None

    manifest_candidate = Path(str(manifest_relative))
    candidate_paths = [
        manifest_candidate,
        REPO_ROOT / manifest_candidate,
        gate_path.parent / manifest_candidate,
    ]
    manifest_path = next((candidate for candidate in candidate_paths if candidate.exists()), None)
    if manifest_path is None:
        return None, str(manifest_relative)
    return json.loads(manifest_path.read_text(encoding="utf-8")), str(manifest_path)


def build_existing_dump_coverage_policy(
    *,
    reference_dump: Path,
    candidate_dump: Path,
    storage_size: int,
    layout: list[dict[str, int | str]],
    coverage_output_gate_path: Path,
    coverage_output_target: str | None,
) -> dict[str, object]:
    gate_path = coverage_output_gate_path.resolve()
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    validate_coverage_output_gate(gate)
    target_entry = select_coverage_target_entry(gate, coverage_output_target)
    manifest, manifest_path = load_coverage_manifest(
        gate_path=gate_path,
        target_entry=target_entry,
    )
    return build_coverage_output_policy_summary(
        reference_dump.read_bytes(),
        candidate_dump.read_bytes(),
        storage_size=storage_size,
        layout=layout,
        gate=gate,
        target_entry=target_entry,
        manifest=manifest,
        manifest_path=manifest_path,
    )


def compare_dump_files(
    *,
    mdir: Path,
    display_mdir: Path,
    reference_dump: Path,
    candidate_dump: Path,
    storage_size: int | None,
    acceptance_policy: str,
    reference_label: str,
    candidate_label: str,
    coverage_output_gate_path: Path | None = None,
    coverage_output_target: str | None = None,
) -> dict[str, object]:
    effective_storage_size = (
        storage_size if storage_size is not None else read_storage_size_from_meta(mdir)
    )
    layout = probe_root_layout(mdir)
    summary = compare_state_dumps(
        reference_dump,
        candidate_dump,
        effective_storage_size,
        layout=layout,
    )
    if coverage_output_gate_path is not None:
        summary["coverage_output_policy"] = build_existing_dump_coverage_policy(
            reference_dump=reference_dump,
            candidate_dump=candidate_dump,
            storage_size=effective_storage_size,
            layout=layout,
            coverage_output_gate_path=coverage_output_gate_path,
            coverage_output_target=coverage_output_target,
        )
    summary["acceptance_policies"] = build_acceptance_policies(summary)
    summary["selected_acceptance_policy"] = select_acceptance_policy(summary, acceptance_policy)
    summary.update(
        {
            "schema_version": 2,
            "mode": "compare_existing_state_dumps",
            "mdir": str(display_mdir),
            "reference_label": reference_label,
            "candidate_label": candidate_label,
            "reference_dump": str(reference_dump),
            "candidate_dump": str(candidate_dump),
            "root_layout_member_count": len(layout),
        }
    )
    return summary
