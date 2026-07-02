import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from llvm_rtl_gpu_suitability import analyze_llvm_rtl_gpu_suitability  # noqa: E402
from llvm_ir_parse import external_calls, extract_functions, reachable_from  # noqa: E402
from build_vl_gpu_compile import compile_ll  # noqa: E402


ITA_MHA_STATE_PARALLEL_IR = """
define void @pulp_ita_mha_state_parallel(ptr %state_storage, i32 %state_id) {
entry:
  %state_stride = mul i32 %state_id, 256
  %idxprom = zext i32 %state_stride to i64
  %q = getelementptr inbounds i8, ptr %state_storage, i64 %idxprom
  %qv = load i32, ptr %q, align 4
  %kptr = getelementptr inbounds i8, ptr %state_storage, i64 64
  %kv = load i32, ptr %kptr, align 4
  %score = mul i32 %qv, %kv
  %out = getelementptr inbounds i8, ptr %state_storage, i64 128
  store i32 %score, ptr %out, align 4
  ret void
}
"""


VEER_MIXED_CPU_CORE_IR = """
define void @veer_mixed_step(ptr %state_storage, i32 %state_id) {
entry:
  %state_stride = mul i32 %state_id, 433536
  %pcptr = getelementptr i8, ptr %state_storage, i32 %state_stride
  %pc = load i32, ptr %pcptr, align 4
  %is_branch = icmp ne i32 %pc, 0
  br i1 %is_branch, label %decode, label %stall
decode:
  %lsu = and i32 %pc, 3
  switch i32 %lsu, label %exu [
    i32 0, label %dccm
    i32 1, label %iccm
  ]
dccm:
  %dccm_ptr = inttoptr i64 4096 to ptr
  %dccm_value = load i32, ptr %dccm_ptr, align 4
  br label %observable
iccm:
  %iccm_ptr = getelementptr i8, ptr %state_storage, i32 %pc
  %iccm_value = load i32, ptr %iccm_ptr, align 4
  br label %observable
exu:
  %mcycle = add i32 %pc, 1
  br label %observable
stall:
  br label %observable
observable:
  %mailbox = phi i32 [ %dccm_value, %dccm ], [ %iccm_value, %iccm ], [ %mcycle, %exu ], [ 0, %stall ]
  call void @printf(ptr %pcptr)
  %finish_marker = icmp eq i32 %mailbox, 255
  br i1 %finish_marker, label %finish, label %next
next:
  store volatile i32 %mailbox, ptr %pcptr, align 4
  ret void
finish:
  store volatile i32 1, ptr %pcptr, align 4
  ret void
}
"""


UNSUPPORTED_ATOMIC_IR = """
define void @unsupported(ptr %state_storage) {
entry:
  %old = atomicrmw add ptr %state_storage, i32 1 seq_cst
  ret void
}
"""


DOTTED_AND_QUOTED_FUNCTION_IR = """
define void @"Vsim___024root.eval"(ptr %state_storage, i32 %state_id) {
entry:
  call void @"Vsim___024root.helper.1"(ptr %state_storage)
  call void @"llvm.sideeffect"()
  call void asm sideeffect "mov @not_a_function", ""()
  %state_stride = mul i32 %state_id, 256
  %idxprom = zext i32 %state_stride to i64
  %q = getelementptr inbounds i8, ptr %state_storage, i64 %idxprom
  %qv = load i32, ptr %q, align 4
  %out = getelementptr inbounds i8, ptr %state_storage, i64 128
  store i32 %qv, ptr %out, align 4
  ret void
}

define void @"Vsim___024root.helper.1"(ptr %state_storage) {
entry:
  ret void
}
"""


QUOTED_STATE_PARALLEL_IR = """
define void @"pulp.ita_mha.state_parallel"(ptr %state_storage, i32 %state_id) {
entry:
  %state_stride = mul i32 %state_id, 256
  %idxprom = zext i32 %state_stride to i64
  %q = getelementptr inbounds i8, ptr %state_storage, i64 %idxprom
  %qv = load i32, ptr %q, align 4
  %kptr = getelementptr inbounds i8, ptr %state_storage, i64 64
  %kv = load i32, ptr %kptr, align 4
  %score = mul i32 %qv, %kv
  %out = getelementptr inbounds i8, ptr %state_storage, i64 128
  store i32 %score, ptr %out, align 4
  ret void
}
"""


REALISTIC_LOWERED_STATE_PARALLEL_IR = """
; ModuleID = 'pulp_ita_mha_lowered.ll'
source_filename = "pulp_ita_mha_gpu_cov_tb.cpp"
target triple = "nvptx64-nvidia-cuda"

define dso_local void @"Vpulp_ita_mha_gpu_cov_tb___024root___eval_state_parallel"(ptr nocapture %state_storage, i32 %state_id) local_unnamed_addr {
entry:
  %state_stride = shl i32 %state_id, 8
  %idxprom = zext i32 %state_stride to i64
  %state_base = getelementptr inbounds i8, ptr %state_storage, i64 %idxprom
  %q_ptr = getelementptr inbounds i8, ptr %state_base, i64 0
  %k_ptr = getelementptr inbounds i8, ptr %state_base, i64 64
  %q = load i32, ptr %q_ptr, align 4
  %k = load i32, ptr %k_ptr, align 4
  %score = mul i32 %q, %k
  %out_ptr = getelementptr inbounds i8, ptr %state_base, i64 128
  store i32 %score, ptr %out_ptr, align 4
  ret void
}
"""


REALISTIC_LOWERED_VEER_CPU_IR = """
; ModuleID = 'veer_el2_lowered.ll'
source_filename = "Vsim__ALL.cpp"
target triple = "nvptx64-nvidia-cuda"

define dso_local void @"Vsim___024root___eval_veer_mixed_step"(ptr %state_storage, i32 %state_id) local_unnamed_addr {
entry:
  %state_stride = mul i32 %state_id, 433536
  %base = getelementptr i8, ptr %state_storage, i32 %state_stride
  %pcptr = getelementptr i8, ptr %base, i32 4096
  %pc = load i32, ptr %pcptr, align 4
  %is_branch = icmp ne i32 %pc, 0
  br i1 %is_branch, label %decode, label %finish_check
decode:
  switch i32 %pc, label %lsu [
    i32 1, label %ifu
    i32 2, label %exu
  ]
ifu:
  %iccm_ptr = inttoptr i64 2147483648 to ptr
  %iccm_word = load i32, ptr %iccm_ptr, align 4
  br label %observable
lsu:
  %dccm_ptr = getelementptr i8, ptr %base, i32 %pc
  %dccm_word = load i32, ptr %dccm_ptr, align 4
  br label %observable
exu:
  %mcycle = add i32 %pc, 1
  br label %observable
finish_check:
  br label %observable
observable:
  %mailbox = phi i32 [ %iccm_word, %ifu ], [ %dccm_word, %lsu ], [ %mcycle, %exu ], [ 255, %finish_check ]
  call void @printf(ptr %pcptr)
  %done = icmp eq i32 %mailbox, 255
  br i1 %done, label %finish, label %next
next:
  store volatile i32 %mailbox, ptr %pcptr, align 4
  ret void
finish:
  store volatile i32 1, ptr %pcptr, align 4
  ret void
}
"""


REACHABLE_HELPER_PRESSURE_IR = """
define void @entry_state_parallel(ptr %state_storage, i32 %state_id) {
entry:
  call void @helper_observable_cpu(ptr %state_storage)
  %state_stride = shl i32 %state_id, 8
  %idxprom = zext i32 %state_stride to i64
  %q = getelementptr inbounds i8, ptr %state_storage, i64 %idxprom
  %qv = load i32, ptr %q, align 4
  %out = getelementptr inbounds i8, ptr %state_storage, i64 128
  store i32 %qv, ptr %out, align 4
  ret void
}

define void @helper_observable_cpu(ptr %state_storage) {
entry:
  %pc = load i32, ptr %state_storage, align 4
  %branch = icmp ne i32 %pc, 0
  br i1 %branch, label %veer_exu, label %finish
veer_exu:
  call void @printf(ptr %state_storage)
  br label %finish
finish:
  store volatile i32 1, ptr %state_storage, align 4
  ret void
}
"""


GENERATED_STATE_PARALLEL_CPP = """
extern "C" void pulp_ita_mha_state_parallel_generated(unsigned char* state_storage, int state_id) {
  int state_stride = state_id * 256;
  int* q = reinterpret_cast<int*>(state_storage + state_stride);
  int* k = reinterpret_cast<int*>(state_storage + state_stride + 64);
  int* out = reinterpret_cast<int*>(state_storage + state_stride + 128);
  *out = (*q) * (*k);
}
"""


class LlvmRtlGpuSuitabilityCliTest(HybridCliTestCase):
    def test_importable_analyzer_marks_ita_mha_64x1_good_state_parallel(self) -> None:
        report = analyze_llvm_rtl_gpu_suitability(
            ITA_MHA_STATE_PARALLEL_IR,
            target="filelist_known_template_pulp_ita_mha",
            workload="pulp_ita_mha",
            shape="64x1",
            entry="pulp_ita_mha_state_parallel",
        )

        self.assertEqual(report["surface"], "llvm_rtl_gpu_suitability")
        self.assertEqual(report["status"], "analyzed")
        self.assertEqual(report["verdict"], "good_state_parallel")
        self.assertEqual(report["recommended_path"], "gpu_state_parallel")
        self.assertIn("state_parallel_shape", report["reasons"]["positive"])
        self.assertLess(report["metrics"]["branch_density"], 0.06)
        self.assertGreaterEqual(report["metrics"]["memory_regularity_score"], 0.7)
        self.assertGreaterEqual(report["metrics"]["state_independence_score"], 0.55)
        self.assertLess(report["metrics"]["observable_pressure"], 0.08)
        self.assertIn("no_speedup_claim", report["non_claims"])
        self.assertIn("no_runtime_abi_change", report["non_claims"])
        self.assertIn("no_gpu_execution", report["non_claims"])

    def test_importable_analyzer_marks_veer_mixed_poor_requires_new_implementation(self) -> None:
        report = analyze_llvm_rtl_gpu_suitability(
            VEER_MIXED_CPU_CORE_IR,
            target="VeeR-EL2",
            workload="dhry+cmark+cmark_iccm",
            shape="3x100000",
            entry="veer_mixed_step",
        )

        self.assertEqual(report["verdict"], "poor_requires_new_implementation")
        self.assertEqual(report["recommended_path"], "cpu_parallel_or_gem_like_mapping")
        self.assertIn("high_observable_pressure", report["reasons"]["negative"])
        self.assertIn("rtl_cpu_core_with_observable_pressure", report["reasons"]["negative"])
        self.assertIn("unsupported_volatile_or_inline_asm", report["reasons"]["negative"])
        self.assertGreater(report["metrics"]["branch_density"], 0.07)
        self.assertGreater(report["metrics"]["observable_pressure"], 0.08)
        self.assertGreater(report["metrics"]["volatile_count"], 0)

    def test_importable_analyzer_marks_atomic_ir_as_requires_new_implementation(self) -> None:
        report = analyze_llvm_rtl_gpu_suitability(
            UNSUPPORTED_ATOMIC_IR,
            target="unsupported",
            workload="atomic",
            shape="64x1",
            entry="unsupported",
        )

        self.assertEqual(report["verdict"], "poor_requires_new_implementation")
        self.assertGreater(report["metrics"]["atomic_count"], 0)
        self.assertIn("unsupported_atomic_or_fence", report["reasons"]["negative"])

    def test_parser_and_analyzer_accept_dotted_quoted_function_names(self) -> None:
        funcs = extract_functions(DOTTED_AND_QUOTED_FUNCTION_IR)

        self.assertIn("Vsim___024root.eval", funcs)
        self.assertIn("Vsim___024root.helper.1", funcs)
        self.assertEqual(
            reachable_from("Vsim___024root.eval", funcs),
            {"Vsim___024root.eval", "Vsim___024root.helper.1"},
        )
        self.assertEqual(external_calls({"Vsim___024root.eval"}, funcs), set())

        report = analyze_llvm_rtl_gpu_suitability(
            QUOTED_STATE_PARALLEL_IR,
            target="filelist_known_template_pulp_ita_mha",
            workload="pulp_ita_mha",
            shape="64x1",
            entry="pulp.ita_mha.state_parallel",
        )

        self.assertEqual(report["status"], "analyzed")
        self.assertEqual(report["entry"], "pulp.ita_mha.state_parallel")
        self.assertEqual(report["verdict"], "good_state_parallel")

    def test_importable_analyzer_includes_reachable_callees_in_metrics(self) -> None:
        report = analyze_llvm_rtl_gpu_suitability(
            REACHABLE_HELPER_PRESSURE_IR,
            target="VeeR-EL2",
            workload="pulp_ita_mha",
            shape="64x1",
            entry="entry_state_parallel",
        )

        self.assertEqual(report["reachable_function_count"], 2)
        self.assertEqual(
            report["reachable_functions"],
            ["entry_state_parallel", "helper_observable_cpu"],
        )
        self.assertEqual(report["verdict"], "poor_requires_new_implementation")
        self.assertEqual(report["recommended_path"], "cpu_parallel_or_gem_like_mapping")
        self.assertGreater(report["metrics"]["branch_count"], 0)
        self.assertGreater(report["metrics"]["observable_pressure"], 0.08)
        self.assertEqual(report["metrics"]["external_call_count"], 1)
        self.assertEqual(report["metrics"]["external_calls"], ["printf"])
        self.assertEqual(report["metrics"]["llvm_intrinsic_call_count"], 0)
        self.assertIn("unsupported_volatile_or_inline_asm", report["reasons"]["negative"])
        self.assertIn("external_side_effect_call", report["reasons"]["negative"])

    def test_cli_prints_json_without_local_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ir_path = Path(temp_dir) / "ita.ll"
            ir_path.write_text(ITA_MHA_STATE_PARALLEL_IR, encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/llvm_rtl_gpu_suitability_cli.py",
                "--ir",
                ir_path.as_posix(),
                "--entry",
                "pulp_ita_mha_state_parallel",
                "--target",
                "filelist_known_template_pulp_ita_mha",
                "--workload",
                "pulp_ita_mha",
                "--shape",
                "64x1",
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "good_state_parallel")
        self.assert_no_local_absolute_paths(result.stdout)

    def test_cli_corpus_gate_writes_reports_for_realistic_lowered_ir_samples(self) -> None:
        corpus = [
            {
                "file_name": "pulp_ita_mha_lowered.ll",
                "ir": REALISTIC_LOWERED_STATE_PARALLEL_IR,
                "entry": "Vpulp_ita_mha_gpu_cov_tb___024root___eval_state_parallel",
                "target": "filelist_known_template_pulp_ita_mha",
                "workload": "pulp_ita_mha",
                "shape": "64x1",
                "verdict": "good_state_parallel",
                "recommended_path": "gpu_state_parallel",
            },
            {
                "file_name": "veer_el2_lowered.ll",
                "ir": REALISTIC_LOWERED_VEER_CPU_IR,
                "entry": "Vsim___024root___eval_veer_mixed_step",
                "target": "VeeR-EL2",
                "workload": "dhry+cmark+cmark_iccm",
                "shape": "3x100000",
                "verdict": "poor_requires_new_implementation",
                "recommended_path": "cpu_parallel_or_gem_like_mapping",
            },
        ]
        required_metrics = (
            "branch_density",
            "memory_regularity_score",
            "state_independence_score",
            "observable_pressure",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            for sample in corpus:
                ir_path = temp_path / sample["file_name"]
                report_path = temp_path / f"{ir_path.stem}.json"
                ir_path.write_text(str(sample["ir"]), encoding="utf-8")
                result = self.run_python_tool(
                    "src/tools/llvm_rtl_gpu_suitability_cli.py",
                    "--ir",
                    ir_path.as_posix(),
                    "--entry",
                    str(sample["entry"]),
                    "--target",
                    str(sample["target"]),
                    "--workload",
                    str(sample["workload"]),
                    "--shape",
                    str(sample["shape"]),
                    "--write-report",
                    "--report-out",
                    report_path.as_posix(),
                )

                stdout_payload = json.loads(result.stdout)
                report_payload = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(stdout_payload, report_payload)
                self.assertEqual(report_payload["verdict"], sample["verdict"])
                self.assertEqual(report_payload["recommended_path"], sample["recommended_path"])
                for metric in required_metrics:
                    self.assertIn(metric, report_payload["metrics"])
                self.assertIn("external_call_count", report_payload["metrics"])
                self.assertIn("external_calls", report_payload["metrics"])
                self.assertIn("llvm_intrinsic_call_count", report_payload["metrics"])
                self.assertIn("no_gpu_execution", report_payload["non_claims"])
                self.assertIn("no_speedup_claim", report_payload["non_claims"])
                self.assert_no_local_absolute_paths(result.stdout)
                self.assert_no_local_absolute_paths(report_path.read_text(encoding="utf-8"))

    def test_cli_corpus_gate_accepts_ir_regenerated_by_clang_emit_llvm_flow(self) -> None:
        clang = shutil.which("clang++-18") or shutil.which("clang++")
        if not clang:
            self.skipTest("clang++ is required to regenerate the lowered IR corpus sample")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cpp_path = temp_path / "generated_state_parallel.cpp"
            ir_path = temp_path / "generated_state_parallel.ll"
            report_path = temp_path / "generated_state_parallel.json"
            cpp_path.write_text(GENERATED_STATE_PARALLEL_CPP, encoding="utf-8")
            compile_ll(
                cpp_path,
                temp_path,
                ir_path,
                clang_opt="O1",
                clang=clang,
                cxx_standard="c++20",
                verilator_include=temp_path,
                verilator_vltstd_include=temp_path,
                run_command=lambda command: self.run_command([str(part) for part in command]),
            )
            result = self.run_python_tool(
                "src/tools/llvm_rtl_gpu_suitability_cli.py",
                "--ir",
                ir_path.as_posix(),
                "--entry",
                "pulp_ita_mha_state_parallel_generated",
                "--target",
                "filelist_known_template_pulp_ita_mha",
                "--workload",
                "pulp_ita_mha",
                "--shape",
                "64x1",
                "--write-report",
                "--report-out",
                report_path.as_posix(),
            )
            payload = json.loads(result.stdout)
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["verdict"], "good_state_parallel")
        self.assertEqual(payload, report_payload)
        self.assertEqual(payload["recommended_path"], "gpu_state_parallel")
        self.assertGreaterEqual(payload["metrics"]["memory_regularity_score"], 0.7)
        self.assertIn("branch_density", payload["metrics"])
        self.assertIn("state_independence_score", payload["metrics"])
        self.assert_no_local_absolute_paths(result.stdout)
        self.assert_no_local_absolute_paths(json.dumps(report_payload, sort_keys=True))

    def test_cli_missing_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ir_path = Path(temp_dir) / "ita.ll"
            ir_path.write_text(ITA_MHA_STATE_PARALLEL_IR, encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/llvm_rtl_gpu_suitability_cli.py",
                "--ir",
                ir_path.as_posix(),
                "--entry",
                "missing",
                "--target",
                "filelist_known_template_pulp_ita_mha",
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("entry function 'missing' was not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
