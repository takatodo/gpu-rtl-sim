"""Reusable state and manifest helpers for build_vl_gpu."""

import json
from pathlib import Path


def load_launch_sequence_from_manifest(manifest_path: Path) -> list[str]:
    if not manifest_path.is_file():
        raise RuntimeError(f'kernel manifest not found: {manifest_path}')
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    launch_sequence = payload.get('launch_sequence')
    if not isinstance(launch_sequence, list) or not launch_sequence:
        raise RuntimeError(f'invalid kernel manifest launch_sequence: {manifest_path}')
    if any(not isinstance(item, str) or not item for item in launch_sequence):
        raise RuntimeError(f'invalid kernel manifest kernel name: {manifest_path}')
    return [str(item) for item in launch_sequence]


def resolve_manifest_launch_sequence(mdir: Path) -> list[str] | None:
    manifest_path = mdir / 'vl_kernel_manifest.json'
    if not manifest_path.is_file():
        return None
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    if payload.get('kernel_split') != 'phases':
        return None
    return load_launch_sequence_from_manifest(manifest_path)


def load_existing_meta(mdir: Path) -> dict | None:
    meta_path = mdir / 'vl_batch_gpu.meta.json'
    if not meta_path.is_file():
        return None
    try:
        payload = json.loads(meta_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'invalid existing meta.json: {meta_path}') from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f'invalid existing meta.json payload: {meta_path}')
    return payload


def resolve_existing_storage_size(existing_meta: dict | None) -> int | None:
    if not existing_meta:
        return None
    storage_size = existing_meta.get('storage_size')
    if isinstance(storage_size, int) and storage_size > 0:
        return storage_size
    return None


def resolve_existing_classifier_report(mdir: Path, existing_meta: dict | None) -> Path:
    report_name = None
    if existing_meta:
        raw_name = existing_meta.get('classifier_report')
        if isinstance(raw_name, str) and raw_name:
            report_name = raw_name
    return mdir / (report_name or 'vl_classifier_report.json')


def resolve_existing_launch_sequence(existing_meta: dict | None) -> list[str] | None:
    if not existing_meta:
        return None
    raw = existing_meta.get('launch_sequence')
    if not isinstance(raw, list):
        return None
    launch_sequence = [str(item) for item in raw if isinstance(item, str) and item]
    return launch_sequence or None


def reuse_launch_sequence(mdir: Path, existing_meta: dict | None) -> list[str] | None:
    launch_sequence = resolve_existing_launch_sequence(existing_meta)
    if launch_sequence is not None:
        return launch_sequence
    launch_sequence = resolve_manifest_launch_sequence(mdir)
    if launch_sequence is not None:
        print('  [meta] reuse launch_sequence from vl_kernel_manifest.json')
    return launch_sequence
