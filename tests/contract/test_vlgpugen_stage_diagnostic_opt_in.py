import re

from tests.contract.hybrid_cli_helpers import HybridCliTestCase, REPO_ROOT


class VlGpuGenStageDiagnosticOptInTest(HybridCliTestCase):
    def _function_body(self, source: str, name: str) -> str:
        match = re.search(
            rf"static (?:unsigned|bool) {re.escape(name)}\([^)]*\) \{{",
            source,
            re.MULTILINE,
        )
        self.assertIsNotNone(match, f"missing function {name}")
        start = match.end()
        depth = 1
        index = start
        while index < len(source) and depth:
            char = source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        self.assertEqual(depth, 0, f"unterminated function {name}")
        return source[start:index - 1]

    def test_stage112_114_116_117_118_119_120_diagnostics_are_env_opt_in(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("static bool hasNonEmptyEnv(const char *Name)", source)

        cases = [
            (
                "instrumentHighEvalCallee0NestedCallBodyPairOffsetStoreWatchpoint",
                [
                    "VLGPUGEN_STAGE112_STORE_START",
                    "VLGPUGEN_STAGE112_STORE_COUNT",
                ],
                "resolveHighEvalCallee0Stage111ChangedNestedCallee",
            ),
            (
                "instrumentHighEvalCallee0NestedCallBodyNonStoreMemoryEffectPairOffsetWatchpoint",
                [
                    "VLGPUGEN_STAGE114_EFFECT_START",
                    "VLGPUGEN_STAGE114_EFFECT_COUNT",
                ],
                "resolveHighEvalCallee0Stage111ChangedNestedCallee",
            ),
            (
                "instrumentHighEvalCallee0NestedCallBodyResidualControlBoundary",
                [
                    "VLGPUGEN_STAGE116_BOUNDARY_START",
                    "VLGPUGEN_STAGE116_BOUNDARY_COUNT",
                ],
                "resolveHighEvalCallee0Stage111ChangedNestedCallee",
            ),
            (
                "instrumentHighEvalCallee0NestedCallBodyBlockBodyBoundary",
                [
                    "VLGPUGEN_STAGE117_BOUNDARY_START",
                    "VLGPUGEN_STAGE117_BOUNDARY_COUNT",
                ],
                "resolveHighEvalCallee0Stage111ChangedNestedCallee",
            ),
            (
                "instrumentHighEvalCallee0NestedCallBodyBlockInstructionBoundary",
                [
                    "VLGPUGEN_STAGE118_BLOCK_SOURCE_ID",
                    "VLGPUGEN_STAGE118_INSTRUCTION_START",
                    "VLGPUGEN_STAGE118_INSTRUCTION_COUNT",
                ],
                "resolveHighEvalCallee0Stage111ChangedNestedCallee",
            ),
            (
                "instrumentHighEvalCallee0NestedCallBodyBlockSkippedSpanBoundary",
                [
                    "VLGPUGEN_STAGE119_BLOCK_SOURCE_ID",
                    "VLGPUGEN_STAGE119_SKIP_SPAN_START",
                    "VLGPUGEN_STAGE119_SKIP_SPAN_COUNT",
                ],
                "resolveHighEvalCallee0Stage111ChangedNestedCallee",
            ),
            (
                "instrumentHighEvalCallee0NestedCallBodyBlockSkippedSpanInstructionBoundary",
                [
                    "VLGPUGEN_STAGE120_BLOCK_SOURCE_ID",
                    "VLGPUGEN_STAGE120_SKIP_SPAN_SOURCE_ID",
                    "VLGPUGEN_STAGE120_INSTRUCTION_START",
                    "VLGPUGEN_STAGE120_INSTRUCTION_COUNT",
                    "VLGPUGEN_STAGE120_SPAN_EDGE_PROBE",
                    "VLGPUGEN_STAGE120_AGGREGATE_EDGE_PROBE",
                    "VLGPUGEN_STAGE120_LOW_PERTURBATION_PROBE",
                    "VLGPUGEN_STAGE121_SOURCE611_DIAGNOSTIC_ATOMIC_SUPPRESSION_PROBE",
                    "VLGPUGEN_STAGE121_DIAGNOSTIC_ATOMIC_SOURCE_ID",
                    "VLGPUGEN_STAGE121_DIAGNOSTIC_ATOMIC_SOURCE_IDS",
                    "VLGPUGEN_STAGE121_DIAGNOSTIC_MARKER_READ_SOURCE_IDS",
                    "VLGPUGEN_STAGE122_NON_DIAGNOSTIC_LIFECYCLE_PROBE",
                    "VLGPUGEN_STAGE123_CONCRETE_WRITE_WINDOW_BISECTION_PROBE",
                    "VLGPUGEN_STAGE124_RECORD318_TRANSITION_PROBE",
                ],
                "resolveHighEvalCallee0Stage111ChangedNestedCallee",
            ),
        ]

        for function_name, env_names, first_body_work in cases:
            with self.subTest(function=function_name):
                body = self._function_body(source, function_name)
                first_work_index = body.index(first_body_work)
                guard_prefix = body[:first_work_index]
                for env_name in env_names:
                    self.assertIn(f'hasNonEmptyEnv("{env_name}")', guard_prefix)
                self.assertIn("return 0;", guard_prefix)

    def test_stage119_skipped_span_probe_includes_cfg_clone_probe_spans(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(
            encoding="utf-8"
        )
        predicate_body = self._function_body(
            source, "isStage119ExtendedSkippedSpanInstruction"
        )
        stage119_body = self._function_body(
            source, "instrumentHighEvalCallee0NestedCallBodyBlockSkippedSpanBoundary"
        )

        self.assertIn("isStage118SkippableDiagnosticInstruction", predicate_body)
        self.assertIn('Name.contains("compact.cfg_clone")', predicate_body)
        self.assertIn('Name.contains("producer_selector")', predicate_body)
        self.assertIn('Name.contains("materialized_store")', predicate_body)
        self.assertIn(
            "isStage119ExtendedSkippedSpanInstruction(I)", stage119_body
        )

    def test_stage121_suppression_runs_before_stage120_after_observation(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(
            encoding="utf-8"
        )
        body = self._function_body(
            source,
            "instrumentHighEvalCallee0NestedCallBodyBlockSkippedSpanInstructionBoundary",
        )

        suppression_index = body.index("Stage121AtomicSuppressionSelected")
        all_candidates_suppression_index = body.index(
            "for (const InstructionCandidate &C : Stage121AggregateSuppressionCandidates)\n"
            "        suppressStage121DiagnosticCandidate(C);"
        )
        selected_loop_index = body.index(
            "for (const InstructionCandidate &C : Selected)"
        )
        after_observation_index = body.index(
            "stage120.callee0_nested_body_block_skipped_span_instruction_boundary.after"
        )
        self.assertLess(suppression_index, after_observation_index)
        self.assertLess(all_candidates_suppression_index, selected_loop_index)
        self.assertNotIn("Stage121SuppressedDiagnosticAtomics", body)
        self.assertNotIn("Stage121SuppressedDiagnosticMarkerReads", body)

    def test_stage122_non_diagnostic_lifecycle_probe_uses_expanded_progress_abi(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(
            encoding="utf-8"
        )
        body = self._function_body(
            source,
            "instrumentHighEvalCallee0NestedCallBodyBlockSkippedSpanInstructionBoundary",
        )
        runtime = (REPO_ROOT / "src/hybrid/run_vl_hybrid.c").read_text(
            encoding="utf-8"
        )

        self.assertIn("VLGPUGEN_STAGE122_NON_DIAGNOSTIC_LIFECYCLE_PROBE", body)
        self.assertIn("Stage122NonDiagnosticLifecycleProbe", body)
        self.assertIn(
            "non_diagnostic_lifecycle_after_suppressed_span", body
        )
        self.assertIn(
            "suppressed_span_entry_to_next_non_diagnostic", body
        )
        self.assertLess(
            body.index(
                "for (const InstructionCandidate &C : Stage121AggregateSuppressionCandidates)\n"
                "        suppressStage121DiagnosticCandidate(C);"
            ),
            body.index("for (const InstructionCandidate &C : Selected)"),
        )
        self.assertNotIn("Stage122Suppressed", body)
        self.assertIn("progress_stage122_control_word", body)
        self.assertIn("progress_stage122_target_delta", body)
        self.assertIn("progress_stage122_view_mask", body)
        self.assertIn(
            "#define ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS 192U",
            runtime,
        )
        self.assertIn(
            "#define ORDERING_AWARE_TOKEN_LOOP_STAGE122_PROGRESS_BASE 168U",
            runtime,
        )
        self.assertIn(
            'boundary_kind_id == 8ULL ? "non_diagnostic_lifecycle_after_suppressed_span"',
            runtime,
        )
        self.assertIn(
            "ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_lifecycle_probe",
            runtime,
        )

    def test_stage123_concrete_write_window_probe_uses_dedicated_progress_abi(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(
            encoding="utf-8"
        )
        body = self._function_body(
            source,
            "instrumentHighEvalCallee0NestedCallBodyBlockSkippedSpanInstructionBoundary",
        )
        runtime = (REPO_ROOT / "src/hybrid/run_vl_hybrid.c").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "VLGPUGEN_STAGE123_CONCRETE_WRITE_WINDOW_BISECTION_PROBE", body
        )
        self.assertIn("Stage123ConcreteWriteWindowBisectionProbe", body)
        self.assertIn("post_suppression_concrete_write_window", body)
        self.assertIn("progress_stage123_control_word", body)
        self.assertIn("progress_stage123_target_delta", body)
        self.assertIn("progress_stage123_view_mask", body)
        self.assertIn(
            "#define ORDERING_AWARE_TOKEN_LOOP_STAGE123_PROGRESS_BASE 176U",
            runtime,
        )
        self.assertIn(
            "ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_concrete_write_window_probe",
            runtime,
        )

    def test_stage124_record318_transition_probe_uses_dedicated_progress_abi(self) -> None:
        source = (REPO_ROOT / "src/passes/vlgpugen.cpp").read_text(
            encoding="utf-8"
        )
        body = self._function_body(
            source,
            "instrumentHighEvalCallee0NestedCallBodyBlockSkippedSpanInstructionBoundary",
        )
        runtime = (REPO_ROOT / "src/hybrid/run_vl_hybrid.c").read_text(
            encoding="utf-8"
        )

        self.assertIn("VLGPUGEN_STAGE124_RECORD318_TRANSITION_PROBE", body)
        self.assertIn("Stage124Record318TransitionProbe", body)
        self.assertIn("post_suppression_record318_transition", body)
        self.assertIn("progress_stage124_control_word", body)
        self.assertIn("progress_stage124_view_mask", body)
        self.assertIn(
            "#define ORDERING_AWARE_TOKEN_LOOP_PROGRESS_COUNTERS 192U",
            runtime,
        )
        self.assertIn(
            "#define ORDERING_AWARE_TOKEN_LOOP_STAGE124_PROGRESS_BASE 184U",
            runtime,
        )
        self.assertIn(
            "ordering_aware_token_loop_high_eval_callee0_nested_call_body_record318_transition_probe",
            runtime,
        )
