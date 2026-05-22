"""CLI dispatch for MobileViT ImageNet manifest generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from mobile_vit_imagenet_manifest import (
    DEFAULT_HF_SPLIT,
    build_manifest,
    build_manifest_from_hf_dataset,
    build_manifest_from_local_hf_cache,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an ImageNet-style manifest for MobileViT evaluation.")
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--labels", type=Path)
    parser.add_argument(
        "--labels-format",
        choices=("filename_label", "imagenet_val_ground_truth"),
        default="filename_label",
    )
    parser.add_argument(
        "--label-index-base",
        type=int,
        default=0,
        choices=(0, 1),
        help="Index base for imagenet_val_ground_truth labels; use 1 for ILSVRC2012_validation_ground_truth.txt.",
    )
    parser.add_argument("--dataset-scope", default="imagenet_validation_or_scoped_subset")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--hf-dataset")
    parser.add_argument("--hf-split", default=DEFAULT_HF_SPLIT)
    parser.add_argument("--hf-output-dir", type=Path)
    parser.add_argument("--hf-token-env", default="HF_TOKEN")
    parser.add_argument("--hf-cache-dir", type=Path)
    return parser.parse_args()


def run_manifest_cli() -> None:
    args = parse_args()
    if args.hf_dataset or args.hf_cache_dir is not None:
        if args.image_root is not None or args.labels is not None:
            raise SystemExit("--hf-dataset/--hf-cache-dir cannot be combined with --image-root/--labels")
        if args.hf_cache_dir is not None:
            manifest = build_manifest_from_local_hf_cache(
                cache_dir=args.hf_cache_dir,
                output_dir=args.hf_output_dir or args.output.parent,
                output_path=args.output,
                dataset_scope=args.dataset_scope,
                split=args.hf_split,
                limit=args.limit,
            )
        else:
            manifest = build_manifest_from_hf_dataset(
                output_dir=args.hf_output_dir or args.output.parent,
                output_path=args.output,
                dataset_scope=args.dataset_scope,
                dataset_name=args.hf_dataset,
                split=args.hf_split,
                limit=args.limit,
                token=os.environ.get(args.hf_token_env),
            )
    else:
        if args.image_root is None or args.labels is None:
            raise SystemExit("--image-root and --labels are required unless --hf-dataset is used")
        manifest = build_manifest(
            image_root=args.image_root,
            labels_path=args.labels,
            dataset_scope=args.dataset_scope,
            output_path=args.output,
            limit=args.limit,
            labels_format=args.labels_format,
            label_index_base=args.label_index_base,
        )
    print(json.dumps(manifest, indent=2))
