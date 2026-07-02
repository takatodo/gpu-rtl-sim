import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


IR_FIXTURE = """
define void @_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root() {
  %compact.cfg_clone.expected_liveout.valid.clear.slot20726 = getelementptr inbounds [48 x i8], ptr %frame, i64 0, i64 36
  store i8 0, ptr %compact.cfg_clone.expected_liveout.valid.clear.slot20726, align 1
  ret void
}
!1558 = !{!"stage112_nested_body_store_source", i64 1415, i64 1, ptr @_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root, !"", !"compact.cfg_clone.expected_liveout.valid.clear.slot20726", !"0"}
"""


class GateGptStage112StoreSourceSummaryTest(HybridCliTestCase):
    def setUp(self) -> None:
        self.add_tools_to_path()

    def test_static_candidate_is_not_runtime_authority(self) -> None:
        from gategpt_stage112_store_source_summary import (
            summarize_stage112_store_sources,
        )

        report = {
            "probe": {
                "runtime_summary": {
                    "phase1_post_sync_high_eval_callee0_nested_call_body_store_watchpoint_event": {
                        "progress_stage": 112,
                        "control_word": (2 << 56) | (2 << 40) | (5 << 32),
                        "source_id": 0,
                        "clean_no_nested_body_store": True,
                        "write_source_found": False,
                    }
                }
            }
        }

        summary = summarize_stage112_store_sources(
            ir_text=IR_FIXTURE, report=report, source_ids=[1415]
        )

        self.assertEqual(
            summary["status"], "stage112_runtime_clean_or_unmapped_static_candidates_only"
        )
        self.assertFalse(summary["runtime_authority"])
        self.assertEqual(summary["static_candidate_count"], 1)
        self.assertEqual(summary["static_candidates"][0]["source_id"], 1415)
        self.assertTrue(summary["static_candidates"][0]["expected_liveout_candidate"])
        self.assertEqual(summary["runtime_clean_event_count"], 1)
        self.assertEqual(summary["runtime_source_ids"], [])

    def test_runtime_source_id_maps_to_metadata_row(self) -> None:
        from gategpt_stage112_store_source_summary import (
            summarize_stage112_store_sources,
        )

        report = {
            "ordering_aware_token_loop_high_eval_callee0_nested_call_body_pair_offset_store_watchpoint_events": [
                {
                    "progress_stage": 112,
                    "control_word": (1 << 56) | (1 << 40) | (5 << 32) | 1415,
                    "source_id": 1415,
                    "watchpoint_complete": True,
                    "write_source_found": True,
                }
            ]
        }

        summary = summarize_stage112_store_sources(
            ir_text=IR_FIXTURE, report=report, source_ids=[]
        )

        self.assertEqual(summary["status"], "stage112_runtime_source_mapped")
        self.assertTrue(summary["runtime_authority"])
        self.assertEqual(summary["runtime_source_ids"], [1415])
        self.assertEqual(summary["runtime_mapped_sources"][0]["pointer_operand"], "compact.cfg_clone.expected_liveout.valid.clear.slot20726")

    def test_cli_writes_summary_without_local_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ir = root / "vl_batch_gpu.ll"
            report = root / "runtime.json"
            out = root / "summary.json"
            ir.write_text(IR_FIXTURE, encoding="utf-8")
            report.write_text(
                json.dumps(
                    {
                        "event": {
                            "progress_stage": 112,
                            "control_word": (2 << 56) | (2 << 40) | (5 << 32),
                            "source_id": 0,
                            "clean_no_nested_body_store": True,
                            "write_source_found": False,
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.run_python_tool(
                "src/tools/gategpt_stage112_store_source_summary.py",
                "--ir",
                str(ir),
                "--report",
                str(report),
                "--source-id",
                "1415",
                "--out",
                str(out),
            )
            summary = json.loads(out.read_text(encoding="utf-8"))

        self.assertFalse(summary["runtime_authority"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))
