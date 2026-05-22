import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
LOCAL_ABSOLUTE_PATH_MARKERS = ("/home/", "/tmp/", "/Users/", "/var/", "/mnt/", "/workspace/", "/root/")

PUBLIC_PACK_REPRESENTATIVE_PATHS = (
    "README.md",
    "config/selection.json",
    "docs/results.md",
    "src/tools/results_reproduction_io.py",
    "src/tools/results_reproduction.py",
    "src/tools/results_reproduction_persistent_probe.py",
    "src/tools/results_reproduction_persistent_resident.py",
    "src/tools/results_reproduction_persistent_shape_phase.py",
    "src/tools/results_reproduction_resident_batch.py",
    "src/tools/results_reproduction_resident_reuse.py",
    "src/tools/results_reproduction_summaries.py",
    "src/tools/results_reproduction_workloads.py",
    "src/tools/compare_vl_hybrid_coverage.py",
    "src/tools/compare_vl_hybrid_modes.py",
    "src/tools/compare_vl_hybrid_normalized.py",
    "src/tools/compare_vl_hybrid_phase_debug.py",
    "src/tools/compare_vl_hybrid_phase_localization.py",
    "src/tools/compare_vl_hybrid_state_compare.py",
    "src/tools/mobile_vit_imagenet_manifest.py",
    "src/tools/mobile_vit_imagenet_hf_parquet.py",
    "records/scaling_gates/public_results_packaging_gate.json",
    "records/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_gate.json",
    "records/scaling_gates/tlul_template_schema_normalization_more_breadth_gate.json",
    "reports/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json",
    "reports/persistent_resident_state_abi_shape_phase_sweep_summary.json",
    "reports/hybrid_benchmark_mobile_vit_template_limit128.json",
)


def results_reproduction_command(*args: str) -> list[str]:
    return [sys.executable, "src/tools/run_results_reproduction.py", *args]


def hybrid_benchmark_command(target: str, *args: str) -> list[str]:
    return [sys.executable, "src/tools/run_hybrid_benchmark.py", target, *args]


class HybridCliTestCase(unittest.TestCase):
    def run_python_tool(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=REPO_ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def run_command(self, command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def assert_no_local_absolute_paths(self, text: str) -> None:
        for marker in LOCAL_ABSOLUTE_PATH_MARKERS:
            self.assertNotIn(marker, text)

    def add_tools_to_path(self) -> None:
        tools_dir = str(TOOLS_DIR)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)

    def assert_dry_run_command_passes(self, command: list[str]) -> None:
        result = self.run_command(command)
        self.assertNotEqual(result.stdout.strip(), "")
        self.assertNotIn("error:", result.stderr.lower())
        self.assert_no_local_absolute_paths(result.stdout)

    def write_persistent_resident_sample_summary(self, tmp: Path) -> Path:
        hybrid_report = tmp / "hybrid.txt"
        hybrid_report.write_text(
            "\n".join(
                [
                    "gpu_kernel_time_ms: total=12.0 per_launch=3.0",
                    "gpu_kernel_time: per_state=4.0 us",
                    "wall_time_ms: 20.0",
                ]
            ),
            encoding="utf-8",
        )
        summary_path = tmp / "sample.json"
        summary_path.write_text(
            json.dumps(
                {
                    "state_authority": "in_process_gpu_d_storage_after_phase_1",
                    "phase_reports": [{"shape": "2x3"}],
                    "all_coverage_output_passed": True,
                    "max_coverage_output_mismatch_count": 0,
                    "hybrid_report": str(hybrid_report.relative_to(REPO_ROOT)),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return summary_path

    @staticmethod
    def persistent_resident_repeat_metric_samples() -> list[dict[str, float]]:
        return [
            {
                "gpu_kernel_total_ms": 3.0,
                "hybrid_wall_ms": 9.0,
                "wall_minus_kernel_residual_ms": 6.0,
                "gpu_kernel_total_ms_per_final_state_step": 0.3,
                "hybrid_wall_ms_per_final_state_step": 0.9,
                "wall_minus_kernel_residual_ms_per_final_state_step": 0.6,
            },
            {
                "gpu_kernel_total_ms": 1.0,
                "hybrid_wall_ms": 5.0,
                "wall_minus_kernel_residual_ms": 4.0,
                "gpu_kernel_total_ms_per_final_state_step": 0.1,
                "hybrid_wall_ms_per_final_state_step": 0.5,
                "wall_minus_kernel_residual_ms_per_final_state_step": 0.4,
            },
            {
                "gpu_kernel_total_ms": 5.0,
                "hybrid_wall_ms": 13.0,
                "wall_minus_kernel_residual_ms": 8.0,
                "gpu_kernel_total_ms_per_final_state_step": 0.5,
                "hybrid_wall_ms_per_final_state_step": 1.3,
                "wall_minus_kernel_residual_ms_per_final_state_step": 0.8,
            },
        ]

    def tearDown(self) -> None:
        tools_dir = str(TOOLS_DIR)
        while tools_dir in sys.path:
            sys.path.remove(tools_dir)
