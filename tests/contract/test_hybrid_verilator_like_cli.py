import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class HybridVerilatorLikeCliTest(unittest.TestCase):
    def test_paged_attention_kv_cache_scale_up_measurement_dry_run_commands_pass(self) -> None:
        dry_run_commands = [
            [
                sys.executable,
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_paged_kv_cache_large.json",
                "--shape",
                "256x1",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_paged_kv_cache_large.json",
                "--shape",
                "1x64",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "paged_attention_kv_score",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "paged_attention_kv_score",
                "--shape",
                "1x64",
                "--dry-run",
            ],
        ]

        for command in dry_run_commands:
            with self.subTest(command=" ".join(command)):
                result = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    check=True,
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.stdout.strip(), "")
                self.assertNotIn("error:", result.stderr.lower())
                for marker in ("/home/", "/tmp/", "/Users/", "/var/", "/mnt/", "/workspace/", "/root/"):
                    self.assertNotIn(marker, result.stdout)

    def test_public_pack_reproduction_smoke_dry_run_commands_pass(self) -> None:
        smoke_commands = [
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--public-pack-archive",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "paged_attention_kv_score",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--shape",
                "16x64",
                "--mode",
                "persistent-resident-state-abi",
                "--dry-run",
            ],
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "mobile_vit",
                "--limit",
                "128",
                "--dry-run",
            ],
        ]

        for command in smoke_commands:
            with self.subTest(command=" ".join(command)):
                result = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    check=True,
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.stdout.strip(), "")
                self.assertNotIn("error:", result.stderr.lower())
                for marker in ("/home/", "/tmp/", "/Users/", "/var/", "/mnt/", "/workspace/", "/root/"):
                    self.assertNotIn(marker, result.stdout)

    def test_public_pack_archive_dry_run_prints_include_exclude_plan(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--public-pack-archive",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("# public_pack_archive_ready", stdout)
        self.assertIn("# dry-run only: no archive is created", stdout)
        for path in (
            "README.md",
            "config/selection.json",
            "docs/results.md",
            "records/scaling_gates/public_results_packaging_gate.json",
            "records/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json",
            "records/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json",
            "records/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json",
            "records/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
            "records/scaling_gates/public_benchmark_pack_externalization_completion_gate.json",
            "records/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
            "records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
            "records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json",
            "records/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
            "records/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
            "records/scaling_gates/pulp_ita_mha_shape_expansion_gate.json",
            "records/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json",
            "src/tools/run_results_reproduction.py",
            "src/tools/results_reproduction.py",
            "config/slice_launch_templates/pulp_paged_kv_cache_large.json",
            "tests/contract/test_full_ita_mha_larger_paged_kv_next.py",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json",
            "reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json",
            "reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json",
            "reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json",
            "reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json",
            "reports/persistent_resident_state_abi_repeat_median_summary.json",
            "reports/hybrid_benchmark_mobile_vit_template_limit128.json",
        ):
            self.assertIn(f"include: {path}", stdout)
        self.assertIn("exclude: artifacts/", stdout)
        self.assertIn("exclude: reports/* except listed evidence snapshots", stdout)
        self.assertIn("tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>", stdout)
        include_lines = [line for line in stdout.splitlines() if line.startswith("include: ")]
        for excluded in ("include: .gitmodules", "include: third_party/", "include: overlays/"):
            self.assertNotIn(excluded, include_lines)
        for marker in ("/home/", "/tmp/", "/Users/", "/var/", "/mnt/", "/workspace/", "/root/"):
            self.assertNotIn(marker, stdout)
            self.assertNotIn(marker, (REPO_ROOT / "src" / "tools" / "results_reproduction.py").read_text(encoding="utf-8"))

        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--public-pack-archive",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dry-run only", result.stderr)

    def test_run_hybrid_benchmark_dry_run_dispatches_template_targets(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1",
            result.stdout,
        )

        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "paged_attention_kv_score",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1",
            result.stdout,
        )

    def test_run_hybrid_benchmark_mobile_vit_dry_run_dispatches_limit_128_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "mobile_vit",
                "--limit",
                "128",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("src/tools/mobile_vit_imagenet_manifest.py", stdout)
        self.assertIn("--limit 128", stdout)
        self.assertIn("src/tools/mobile_vit_hybrid_imagenet_eval.py", stdout)
        self.assertIn("--hybrid-batch-size 128", stdout)

    def test_run_hybrid_benchmark_preflight_reports_commands_without_execution(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--shape",
                "64x1",
                "--preflight",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["tool"], "src/tools/run_hybrid_benchmark.py")
        self.assertEqual(report["target"], "pulp_ita_mha")
        self.assertEqual(report["shape"], "64x1")
        self.assertEqual(report["execution_mode"], "preflight")
        self.assertIn("preflight does not execute benchmark commands", report["non_claims"])
        self.assertIn("run_hybrid_template.py", report["commands"][0])

    def test_run_hybrid_benchmark_summary_out_uses_unified_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "src/tools/run_hybrid_benchmark.py",
                    "pulp_ita_mha",
                    "--shape",
                    "64x1",
                    "--dry-run",
                    "--summary-out",
                    str(summary_path),
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("+ write", result.stdout)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["schema_version"], 1)
            self.assertEqual(summary["tool"], "src/tools/run_hybrid_benchmark.py")
            self.assertEqual(summary["target"], "pulp_ita_mha")
            self.assertEqual(summary["shape"], "64x1")
            self.assertEqual(summary["mode"], "template")
            self.assertEqual(summary["execution_mode"], "dry_run")
            self.assertIn("compare_report", summary["expected_reports"])
            self.assertEqual(summary["evidence"]["status"], "not_collected")
            self.assertIn("dry-run summaries are not correctness or timing evidence", summary["non_claims"])

    def test_run_hybrid_benchmark_summary_reads_existing_mobile_vit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "mobile_vit_summary.json"
            subprocess.run(
                [
                    sys.executable,
                    "src/tools/run_hybrid_benchmark.py",
                    "mobile_vit",
                    "--limit",
                    "128",
                    "--dry-run",
                    "--summary-out",
                    str(summary_path),
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            dry_run_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(dry_run_summary["evidence"]["status"], "not_collected")

            sys.path.insert(0, str(REPO_ROOT / "src/tools"))
            from hybrid_benchmark import benchmark_summary

            executed_summary = benchmark_summary(
                target="mobile_vit",
                limit=128,
                execution_mode="executed",
            )
            self.assertEqual(executed_summary["expected_reports"]["aggregate_summary"], "reports/mobile_vit_hybrid_128_summary.json")
            if executed_summary["evidence"]["status"] == "missing":
                self.assertEqual(
                    executed_summary["evidence"]["missing_report"],
                    "reports/mobile_vit_hybrid_128_summary.json",
                )
            else:
                self.assertEqual(executed_summary["evidence"]["status"], "collected")
                self.assertEqual(executed_summary["evidence"]["evaluated_count"], 128)
                self.assertTrue(executed_summary["evidence"]["coverage_output_passed"])

    def test_run_hybrid_benchmark_summary_from_existing_mobile_vit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "mobile_vit_existing_summary.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "src/tools/run_hybrid_benchmark.py",
                    "mobile_vit",
                    "--limit",
                    "128",
                    "--summary-from-existing",
                    "--summary-out",
                    str(summary_path),
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("+ write", result.stdout)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["execution_mode"], "existing_evidence")
            self.assertEqual(summary["expected_reports"]["aggregate_summary"], "reports/mobile_vit_hybrid_128_summary.json")
            if summary["evidence"]["status"] == "missing":
                self.assertEqual(
                    summary["evidence"]["missing_report"],
                    "reports/mobile_vit_hybrid_128_summary.json",
                )
            else:
                self.assertEqual(summary["evidence"]["status"], "collected")
                self.assertEqual(summary["evidence"]["evaluated_count"], 128)
                self.assertEqual(summary["evidence"]["top1_accuracy"], 0.7734375)
                self.assertTrue(summary["evidence"]["coverage_output_passed"])
            self.assertIn("existing_evidence summaries do not rerun benchmark commands", summary["non_claims"])
            self.assertNotIn("/home/", json.dumps(summary["commands"]))

    def test_run_hybrid_benchmark_resident_summary_records_expected_aggregate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "resident_summary.json"
            subprocess.run(
                [
                    sys.executable,
                    "src/tools/run_hybrid_benchmark.py",
                    "pulp_ita_mha",
                    "--shape",
                    "1x1",
                    "--mode",
                    "resident-state-reuse",
                    "--phases",
                    "2",
                    "--dry-run",
                    "--summary-out",
                    str(summary_path),
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["target"], "pulp_ita_mha")
            self.assertEqual(summary["shape"], "1x1")
            self.assertEqual(summary["mode"], "resident-state-reuse")
            self.assertEqual(summary["phases"], 2)
            self.assertEqual(summary["expected_reports"]["aggregate_summary"], "reports/resident_state_reuse_experiment_summary.json")
            self.assertEqual(summary["expected_reports"]["phase_count"], 2)
            self.assertEqual(summary["evidence"]["status"], "not_collected")

    def test_run_hybrid_benchmark_dispatches_resident_modes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--shape",
                "16x64",
                "--mode",
                "resident-state-reuse",
                "--phases",
                "4",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("src/tools/run_results_reproduction.py --resident-state-reuse 16x64", result.stdout)
        self.assertIn("--resident-state-reuse-phases 4", result.stdout)

        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--shape",
                "16x64",
                "--mode",
                "persistent-resident-state-abi",
                "--phases",
                "4",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64", result.stdout)
        self.assertIn("--persistent-resident-state-abi-phases 4", result.stdout)

    def test_run_hybrid_benchmark_rejects_missing_required_shape_or_limit(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "pulp_ita_mha",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --shape", result.stderr)

        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_benchmark.py",
                "mobile_vit",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("supports --limit 128 only", result.stderr)

    def test_gen_hybrid_config_dry_run_emits_gate_manifest_and_template(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/gen_hybrid_config.py",
                "--target",
                "PULP_ITA.demo_cov",
                "--top-module",
                "demo_cov_tb",
                "--overlay",
                "overlays/demo/src/demo_cov_tb.sv",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn("write: overlays/generated/tests/demo_cov_coverage_regions.json", result.stdout)
        self.assertIn("write: config/slice_launch_templates/demo_cov.json", result.stdout)
        self.assertIn("write: config/scaling_gates/demo_cov_first_hybrid_benchmark_gate.json", result.stdout)
        self.assertIn('"target": "PULP_ITA.demo_cov"', result.stdout)
        self.assertIn('"top_module": "demo_cov_tb"', result.stdout)
        self.assertIn('"host_probe_builder": "src/tools/build_host_probe.py"', result.stdout)
        self.assertIn('"makefile": "not_required_for_generated_template"', result.stdout)
        self.assertIn('"acceptance_policy": "coverage_output_equivalence"', result.stdout)

    def test_run_hybrid_template_dry_run_uses_existing_template(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("verilator --cc --timing", stdout)
        self.assertIn(
            "python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_paged_attention_kv_score.json",
            stdout,
        )
        self.assertNotIn("make -C src/hybrid pulp_paged_attention_kv_score_host_probe", stdout)
        self.assertIn("python3 src/tools/build_vl_gpu.py artifacts/pulp_paged_attention_kv_score_obj_dir --force", stdout)
        self.assertIn("python3 src/tools/run_vl_hybrid.py --mdir artifacts/pulp_paged_attention_kv_score_obj_dir", stdout)
        self.assertIn("python3 src/tools/compare_vl_hybrid_modes.py artifacts/pulp_paged_attention_kv_score_obj_dir", stdout)
        self.assertIn("--coverage-output-target pulp_paged_attention_kv_score", stdout)
        self.assertIn("pulp_paged_attention_kv_score_cpu_repeat_64x1.bin", stdout)

    def test_run_results_reproduction_dry_run_prints_representative_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1",
            stdout,
        )
        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x64",
            stdout,
        )
        self.assertIn("python3 src/tools/run_vl_hybrid.py --mdir artifacts/pulp_ita_mha_obj_dir", stdout)
        self.assertIn("--nstates 32 --steps 64 --resident-steps", stdout)
        self.assertIn("pulp_ita_mha_cpu_repeat_32x64.json", stdout)
        self.assertIn("pulp_ita_mha_cpu_vs_hybrid_32x64_resident_coverage_output_compare.json", stdout)
        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1",
            stdout,
        )

    def test_run_results_reproduction_repeat_median_dry_run_prints_sampled_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--repeat-median",
                "3",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("pulp_ita_mha_median_init_1x1_cpu.json", stdout)
        self.assertIn("pulp_ita_mha_64x1_median_sample_1_cpu.json", stdout)
        self.assertIn("pulp_ita_mha_1x64_median_sample_1_hybrid.txt", stdout)
        self.assertIn("--resident-steps", stdout)
        self.assertIn("pulp_ita_mha_32x64_resident_median_sample_3_compare.json", stdout)
        self.assertIn("pulp_ita_mha_32x64_resident_median_sample_3_compare_stdout.txt", stdout)
        self.assertIn("pulp_paged_attention_kv_score_64x1_median_sample_3_compare.json", stdout)
        self.assertIn("pulp_paged_attention_kv_score_median_init_1x1_cpu.json", stdout)
        self.assertIn("--coverage-output-gate config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json", stdout)
        self.assertIn("--coverage-output-gate config/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json", stdout)

    def test_run_results_reproduction_resident_batch_sweep_dry_run_prints_sweep_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--resident-batch-sweep",
                "1,8,32",
                "--resident-batch-sweep-repeat",
                "2",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("pulp_ita_mha_resident_batch_sweep_init_1x1_cpu.json", stdout)
        self.assertIn("pulp_ita_mha_1x64_resident_median_sample_1_cpu.json", stdout)
        self.assertIn("pulp_ita_mha_8x64_resident_median_sample_2_hybrid.txt", stdout)
        self.assertIn("pulp_ita_mha_32x64_resident_median_sample_2_compare.json", stdout)
        self.assertIn("pulp_ita_mha_32x64_resident_median_sample_2_compare_stdout.txt", stdout)
        self.assertIn("--resident-steps", stdout)

    def test_run_results_reproduction_resident_state_reuse_dry_run_prints_phase_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--resident-state-reuse",
                "16x64",
                "--resident-state-reuse-phases",
                "4",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("pulp_ita_mha_resident_state_reuse_init_1x1_cpu.json", stdout)
        self.assertIn("pulp_ita_mha_16x64_resident_state_reuse_phase_1_cpu_16x64.json", stdout)
        self.assertIn("pulp_ita_mha_16x64_resident_state_reuse_phase_2_gpu_16x128.bin", stdout)
        self.assertIn("--init-state artifacts/pulp_ita_mha_obj_dir/pulp_ita_mha_16x64_resident_state_reuse_phase_1_gpu_16x64.bin", stdout)
        self.assertIn("pulp_ita_mha_16x64_resident_state_reuse_phase_4_compare_16x256.json", stdout)
        self.assertIn("pulp_ita_mha_16x64_resident_state_reuse_phase_4_compare_16x256_stdout.txt", stdout)
        self.assertIn("--acceptance-policy coverage_output_equivalence", stdout)

    def test_run_results_reproduction_persistent_resident_state_abi_dry_run_prints_handle_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--persistent-resident-state-abi",
                "16x64",
                "--persistent-resident-state-abi-phases",
                "4",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("pulp_ita_mha_persistent_resident_state_abi_init_1x1_cpu.json", stdout)
        self.assertIn("--persistent-resident-state-abi-handle pulp_ita_mha_16x64", stdout)
        self.assertIn("--persistent-resident-state-abi-phase 1", stdout)
        self.assertIn("--persistent-resident-state-abi-phases 4", stdout)
        self.assertIn("--persistent-resident-state-abi-phase-dumps", stdout)
        self.assertNotIn("phase_1_gpu_dump_16x64.bin --sanitize-host-only-internals", stdout)
        self.assertNotIn("--persistent-resident-state-abi-phase 2 --init-state", stdout)
        self.assertIn("pulp_ita_mha_16x64_persistent_resident_state_abi_phase_4_compare_16x256.json", stdout)
        self.assertIn("reports/persistent_resident_state_abi_probe_summary.json", stdout)
        self.assertIn("--acceptance-policy coverage_output_equivalence", stdout)

    def test_run_results_reproduction_persistent_resident_state_abi_repeat_median_dry_run_prints_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--persistent-resident-state-abi",
                "16x64",
                "--persistent-resident-state-abi-phases",
                "4",
                "--persistent-resident-state-abi-repeat-median",
                "3",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("# persistent_resident_state_abi_repeat_median sample 1/3", stdout)
        self.assertIn("# persistent_resident_state_abi_repeat_median sample 3/3", stdout)
        self.assertIn("reports/persistent_resident_state_abi_repeat_median_sample_1.json", stdout)
        self.assertIn("reports/persistent_resident_state_abi_repeat_median_sample_2.json", stdout)
        self.assertIn("reports/persistent_resident_state_abi_repeat_median_sample_3.json", stdout)
        self.assertIn("persistent_resident_state_abi_repeat_median_sample_1_phase_1_cpu_16x64.json", stdout)
        self.assertIn("persistent_resident_state_abi_repeat_median_sample_3_multiphase_hybrid.txt", stdout)
        self.assertIn("reports/persistent_resident_state_abi_repeat_median_summary.json", stdout)
        self.assertIn("--persistent-resident-state-abi-handle pulp_ita_mha_16x64", stdout)
        self.assertIn("--persistent-resident-state-abi-phases 4", stdout)
        self.assertNotIn("--persistent-resident-state-abi-phase 2 --init-state", stdout)

    def test_run_results_reproduction_mobile_vit_imagenet_128_dry_run_prints_flow(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_results_reproduction.py",
                "--mobile-vit-imagenet-128",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        stdout = result.stdout
        self.assertIn("src/tools/mobile_vit_imagenet_manifest.py", stdout)
        self.assertIn("--limit 128", stdout)
        self.assertIn("scoped_subset:imagenet_local_cache_128", stdout)
        self.assertIn("env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1", stdout)
        self.assertIn("src/tools/mobile_vit_hybrid_imagenet_eval.py", stdout)
        self.assertIn("--cpu-kick-batch-size 16", stdout)
        self.assertIn("--hybrid-batch-size 128", stdout)
        self.assertIn("reports/mobile_vit_hybrid_128_summary.json", stdout)

    def test_run_vl_hybrid_persistent_multiphase_rejects_mismatched_dump_count(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_vl_hybrid.py",
                "--storage-size",
                "1",
                "--cubin",
                "missing.cubin",
                "--nstates",
                "16",
                "--steps",
                "64",
                "--resident-steps",
                "--persistent-resident-state-abi-handle",
                "pulp_ita_mha_16x64",
                "--persistent-resident-state-abi-phase",
                "1",
                "--persistent-resident-state-abi-phases",
                "4",
                "--persistent-resident-state-abi-phase-dumps",
                "one.bin,two.bin",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("phase-dumps count must match", result.stderr)

    def test_run_vl_hybrid_persistent_phase_after_one_rejects_init_state_reload(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_vl_hybrid.py",
                "--storage-size",
                "1",
                "--cubin",
                "missing.cubin",
                "--nstates",
                "16",
                "--steps",
                "64",
                "--resident-steps",
                "--persistent-resident-state-abi-handle",
                "pulp_ita_mha_16x64",
                "--persistent-resident-state-abi-phase",
                "2",
                "--init-state",
                "previous_phase_gpu_dump.bin",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("phases after 1 must not use --init-state", result.stderr)

    def test_generated_payloads_are_importable_and_structured(self) -> None:
        sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
        from hybrid_config_generator import HybridConfigSpec, generated_payloads

        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=[],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir=None,
            work_dir=None,
            verilator_args=["--flatten"],
        )
        payloads = generated_payloads(spec)
        self.assertEqual(
            set(payloads),
            {
                "overlays/generated/tests/demo_cov_coverage_regions.json",
                "config/slice_launch_templates/demo_cov.json",
                "config/scaling_gates/demo_cov_gate.json",
            },
        )
        for payload in payloads.values():
            json.dumps(payload)
        template = payloads["config/slice_launch_templates/demo_cov.json"]
        gate = payloads["config/scaling_gates/demo_cov_gate.json"]
        self.assertEqual(template["build"]["host_probe_target"], "demo_cov_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(template["build"]["host_probe"]["clock_field"], "demo_cov_tb__DOT__clk_i")
        self.assertEqual(template["build"]["host_probe"]["reset_field"], "demo_cov_tb__DOT__reset_like_w")
        self.assertEqual(template["build"]["mdir"], "artifacts/demo_cov_obj_dir")
        self.assertEqual(gate["coverage_output_contract"]["total_words_per_state"], 29)
        self.assertTrue(gate["acceptance_policy"]["host_probe_glue_generated_from_template"])
        self.assertFalse(gate["acceptance_policy"]["makefile_target_required"])

    def test_generated_template_uses_host_probe_builder_without_makefile_glue(self) -> None:
        sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
        from hybrid_config_generator import HybridConfigSpec, generated_payloads
        from hybrid_template_runner import command_plan, load_template_plan
        from hybrid_host_probe_builder import host_probe_compile_command, load_host_probe_build_plan

        spec = HybridConfigSpec(
            target="PULP_ITA.demo_cov",
            top_module="demo_cov_tb",
            source_files=[],
            overlay="overlays/demo/src/demo_cov_tb.sv",
            gate_name="demo_cov_gate",
            host_probe_target=None,
            mdir="artifacts/demo_cov_obj_dir",
            work_dir=None,
            verilator_args=["--flatten"],
        )
        payloads = generated_payloads(spec)
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "demo_cov.json"
            template_path.write_text(
                json.dumps(payloads["config/slice_launch_templates/demo_cov.json"], indent=2) + "\n",
                encoding="utf-8",
            )

            commands = command_plan(load_template_plan(template_path, shape="1x1"))
            self.assertEqual(commands[1][0:2], ["python3", "src/tools/build_host_probe.py"])
            self.assertNotIn("make", commands[1])

            build_plan = load_host_probe_build_plan(template_path)
            compile_command = host_probe_compile_command(build_plan)
            joined = " ".join(compile_command)
            self.assertIn("-DMODEL_HEADER=\"Vdemo_cov_tb.h\"", joined)
            self.assertIn("-DROOT_CLK_FIELD=demo_cov_tb__DOT__clk_i", joined)
            self.assertIn("-DROOT_RST_FIELD=demo_cov_tb__DOT__reset_like_w", joined)
            self.assertIn("artifacts/demo_cov_obj_dir/*.cpp", joined)

    def test_run_hybrid_template_passes_template_verilator_defines(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/nvdla_cmac_core_mac.json",
                "--shape",
                "1x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        first_line = result.stdout.splitlines()[0]
        self.assertIn("-DSYNTHESIS", first_line)
        self.assertIn("-DDESIGNWARE_NOEXIST", first_line)
        self.assertIn("--flatten", first_line)
        self.assertIn("third_party/rtlmeter/designs/NVDLA/src/NV_DW02_tree.v", first_line)
        self.assertIn("third_party/rtlmeter/designs/NVDLA/src/NV_DW_minmax.v", first_line)


if __name__ == "__main__":
    unittest.main()
