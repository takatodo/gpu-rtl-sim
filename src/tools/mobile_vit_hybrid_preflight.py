"""Preflight checks for MobileViT hybrid ImageNet evaluation."""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path


DEFAULT_TEMPLATE = Path("config/slice_launch_templates/mobile_vit_cpu_kick_rtl_proxy.json")
DEFAULT_HF_CACHE_DATASET_DIR = Path.home() / ".cache" / "huggingface" / "hub" / "datasets--ILSVRC--imagenet-1k"


def _cached_hf_validation_shards(cache_dir: Path = DEFAULT_HF_CACHE_DATASET_DIR) -> list[Path]:
    snapshots = cache_dir / "snapshots"
    if not snapshots.exists():
        return []
    return sorted(snapshots.glob("*/data/validation-*.parquet"))


def _python_dependency_status() -> dict[str, bool]:
    return {
        name: importlib.util.find_spec(name) is not None
        for name in ("torch", "torchvision", "transformers", "PIL", "datasets", "huggingface_hub", "pyarrow")
    }


def _executable_status() -> dict[str, bool]:
    return {
        name: shutil.which(name) is not None
        for name in ("verilator", "make", "clang++-18", "llc-18", "opt-18", "ptxas")
    }


def _cpu_kick_ready(
    *,
    predictions_exist: bool,
    run_cpu_kick_infer: bool,
    python_deps: dict[str, bool],
) -> bool:
    return predictions_exist or (
        run_cpu_kick_infer
        and python_deps["torch"]
        and python_deps["torchvision"]
        and python_deps["transformers"]
        and python_deps["PIL"]
    )


def _preflight_missing_checks(
    *,
    manifest_exists: bool,
    predictions_exist: bool,
    run_cpu_kick_infer: bool,
    template_exists: bool,
    python_deps: dict[str, bool],
    executables: dict[str, bool],
) -> list[str]:
    missing: list[str] = []
    if not manifest_exists:
        missing.append("manifest")
    if not predictions_exist and not run_cpu_kick_infer:
        missing.append("cpu_kick_predictions_or_run_cpu_kick_infer")
    if run_cpu_kick_infer:
        for name in ("torch", "torchvision", "transformers", "PIL"):
            if not python_deps[name]:
                missing.append(f"python_dependency:{name}")
    if not template_exists:
        missing.append("hybrid_template")
    for name, present in executables.items():
        if not present:
            missing.append(f"executable:{name}")
    return missing


def _local_hf_cache_report(python_deps: dict[str, bool]) -> dict[str, object]:
    cached_shards = _cached_hf_validation_shards()
    return {
        "dataset_dir": str(DEFAULT_HF_CACHE_DATASET_DIR),
        "validation_parquet_shard_count": len(cached_shards),
        "usable_for_manifest_generation": bool(cached_shards) and python_deps["pyarrow"] and python_deps["PIL"],
    }


def build_preflight_report(
    *,
    manifest_path: Path,
    cpu_kick_predictions_path: Path,
    hybrid_template_path: Path = DEFAULT_TEMPLATE,
    run_cpu_kick_infer: bool = False,
    token_env: str = "HF_TOKEN",
) -> dict[str, object]:
    python_deps = _python_dependency_status()
    executables = _executable_status()
    manifest_exists = manifest_path.exists()
    predictions_exist = cpu_kick_predictions_path.exists()
    template_exists = hybrid_template_path.exists()
    cpu_kick_ready = _cpu_kick_ready(
        predictions_exist=predictions_exist,
        run_cpu_kick_infer=run_cpu_kick_infer,
        python_deps=python_deps,
    )
    hybrid_ready = template_exists and all(executables.values())
    ready = manifest_exists and cpu_kick_ready and hybrid_ready
    missing = _preflight_missing_checks(
        manifest_exists=manifest_exists,
        predictions_exist=predictions_exist,
        run_cpu_kick_infer=run_cpu_kick_infer,
        template_exists=template_exists,
        python_deps=python_deps,
        executables=executables,
    )

    return {
        "schema_version": 1,
        "tool": "src/tools/mobile_vit_hybrid_imagenet_eval.py",
        "mode": "preflight",
        "ready_for_full_hybrid_imagenet_eval": ready,
        "manifest": str(manifest_path),
        "manifest_exists": manifest_exists,
        "cpu_kick_predictions": str(cpu_kick_predictions_path),
        "cpu_kick_predictions_exists": predictions_exist,
        "run_cpu_kick_infer": run_cpu_kick_infer,
        "hybrid_template": str(hybrid_template_path),
        "hybrid_template_exists": template_exists,
        "local_hf_cache": _local_hf_cache_report(python_deps),
        "python_dependencies": python_deps,
        "executables": executables,
        "token_env": token_env,
        "token_present": bool(os.environ.get(token_env)),
        "dependency_install_command": "python3 -m pip install -r requirements/mobile_vit.txt",
        "missing_or_failed_checks": missing,
        "non_claims": [
            "preflight does not execute MobileViT inference",
            "preflight does not execute hybrid RTL",
            "preflight is not ImageNet accuracy evidence",
        ],
    }
