from __future__ import annotations

import argparse
import json
from pathlib import Path

from mobile_vit_hybrid_eval_core import MAX_RTL_PROXY_BATCH
from mobile_vit_hybrid_imagenet_defaults import DEFAULT_MODEL_ID, DEFAULT_TEMPLATE
from mobile_vit_hybrid_preflight import build_preflight_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run MobileViT ImageNet evaluation with a hybrid RTL control-boundary check."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cpu-kick-predictions", type=Path, required=True)
    parser.add_argument("--accuracy-report", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--hybrid-template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--hybrid-batch-size", type=int, default=MAX_RTL_PROXY_BATCH)
    parser.add_argument("--cfg-seed", type=int, default=1)
    parser.add_argument("--run-cpu-kick-infer", action="store_true")
    parser.add_argument("--cpu-kick-batch-size", type=int, default=1)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def run_preflight_from_args(args: argparse.Namespace) -> None:
    report = build_preflight_report(
        manifest_path=args.manifest,
        cpu_kick_predictions_path=args.cpu_kick_predictions,
        hybrid_template_path=args.hybrid_template,
        run_cpu_kick_infer=args.run_cpu_kick_infer,
        token_env=args.token_env,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
