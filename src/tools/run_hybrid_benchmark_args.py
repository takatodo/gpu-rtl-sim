from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one supported hybrid RTL benchmark with a Verilator-like target/shape interface.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python3 src/tools/run_hybrid_benchmark.py --list-targets
  python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --sidecar-gpu --dry-run
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --sidecar-gpu --preflight
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --sim-accel-estimate-efficiency --dry-run
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-command
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-estimate-command
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-efficiency-estimate
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json

notes:
  --print-verilator-command, --print-verilator-estimate-command, --print-efficiency-estimate, --print-operator-plan, and --operator-plan-json do not execute commands.
  --sim-accel-estimate-efficiency follows the normal execution or --dry-run path; use --print-efficiency-estimate for estimate-only preview.
  coverage_output_equivalence remains the correctness policy; efficiency output is separate.
""",
    )
    parser.add_argument("target", nargs="?", help="Benchmark target, e.g. pulp_ita_mha, paged_attention_kv_score, mobile_vit.")
    parser.add_argument("--shape", help="Shape for RTL slice-template targets, e.g. 64x1 or 1x64.")
    parser.add_argument(
        "--sim-accel",
        choices=("sidecar-gpu",),
        help="Verilator-compatible accelerator spelling. Currently supports sidecar-gpu.",
    )
    parser.add_argument(
        "--sim-accel-states",
        help="Verilator-compatible independent state count. Use with --sim-accel-steps.",
    )
    parser.add_argument(
        "--sim-accel-steps",
        help="Verilator-compatible eval steps per state. Use with --sim-accel-states.",
    )
    parser.add_argument(
        "--sim-accel-shape",
        help="Compact compatibility spelling for --sim-accel-states N --sim-accel-steps S, e.g. 64x1.",
    )
    parser.add_argument(
        "--sim-accel-estimate-efficiency",
        action="store_true",
        help="Verilator-compatible alias for --estimate-efficiency after normal execution or --dry-run.",
    )
    parser.add_argument("--limit", type=int, help="Input limit for dataset-backed targets, e.g. mobile_vit --limit 128.")
    parser.add_argument(
        "--mode",
        default="template",
        choices=("template", "resident-state-reuse", "persistent-resident-state-abi"),
        help="Benchmark execution mode for targets that support more than the template flow.",
    )
    parser.add_argument("--phases", type=int, default=4, help="Phase count for resident-state-reuse or persistent modes.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    parser.add_argument("--preflight", action="store_true", help="Print a JSON plan without executing commands.")
    parser.add_argument(
        "--summary-out",
        nargs="?",
        const="auto",
        help="Write a unified benchmark summary JSON. With no path, writes under reports/.",
    )
    parser.add_argument(
        "--summary-from-existing",
        action="store_true",
        help="Write a summary from existing generated reports without running benchmark commands.",
    )
    parser.add_argument(
        "--estimate-efficiency",
        action="store_true",
        help="Print a short human-readable efficiency estimate after planning or execution.",
    )
    parser.add_argument(
        "--estimate-efficiency-json",
        action="store_true",
        help="Print the efficiency estimate as JSON after planning or execution.",
    )
    parser.add_argument(
        "--sidecar-gpu",
        action="store_true",
        help=(
            "Use the existing hybrid sidecar GPU benchmark flow and print the "
            "human-readable efficiency estimate."
        ),
    )
    parser.add_argument(
        "--print-verilator-command",
        action="store_true",
        help="Print only the synthesized future Verilator sidecar command without executing commands.",
    )
    parser.add_argument(
        "--print-verilator-estimate-command",
        action="store_true",
        help=(
            "Print only the synthesized future Verilator sidecar command with "
            "--sim-accel-estimate-efficiency without executing commands."
        ),
    )
    parser.add_argument(
        "--print-efficiency-estimate",
        action="store_true",
        help="Print only the human-readable efficiency estimate without executing commands.",
    )
    parser.add_argument(
        "--print-operator-plan",
        action="store_true",
        help="Print the synthesized Verilator sidecar command and efficiency estimate without executing commands.",
    )
    parser.add_argument(
        "--operator-plan-json",
        action="store_true",
        help="Print the synthesized Verilator sidecar operator plan as JSON without executing commands.",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="Print supported benchmark targets and exit. Optional view: sidecar_gpu.",
    )
    return parser
