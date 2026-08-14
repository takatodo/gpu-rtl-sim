from __future__ import annotations

import itertools
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.tlul10818_boundary_fixtures import (
    ADMISSION_MANIFEST_SCHEMA,
    CONTRACT,
    DOC,
    GOLDEN_SWEEP_SHA256,
    GPU_TB,
    HEX40,
    POINT_RESULT_TEMPLATE_SCHEMA,
    REPO_ROOT,
    RUNNER_OBSERVATIONS_SCHEMA,
    RUN_SPEC_SCHEMA,
    SCRIPT,
    TIMING_TEMPLATE_SCHEMA,
    experiment_run_spec,
    golden_sweep_enumerator,
    load_contract,
    raw_run_result,
)

from tlul10818_gpu_schedule import (  # noqa: E402
    ACTION_DOMAIN,
    RUNNER_CONTROL_AXES,
    boundary_action_mapping,
    boundary_action_name,
    boundary_contract_projection,
    boundary_patch_script,
    boundary_patch_script_for_parameters,
    boundary_sweep_space,
    uniform_scale_patch_script,
)
from tlul10818_boundary_contract import (  # noqa: E402
    build_boundary_experiment_contract,
    build_boundary_semantic_identity,
)
from tlul10818_boundary_evidence import (  # noqa: E402
    build_boundary_evidence_bundle,
    build_boundary_trial_evidence,
)
from build_tlul10818_boundary_artifacts import main as build_boundary_artifacts_main  # noqa: E402
from build_tlul10818_boundary_artifacts import _read_object as read_artifact_object  # noqa: E402
from build_tlul10818_boundary_execution_packet import (  # noqa: E402
    main as build_execution_packet_main,
)
from build_tlul10818_boundary_run_spec import main as build_run_spec_main  # noqa: E402
from build_tlul10818_boundary_run_result import (  # noqa: E402
    build_run_result,
    main as build_run_result_main,
)
from build_tlul10818_boundary_timing_template import (  # noqa: E402
    main as build_timing_template_main,
)
from admit_tlul10818_boundary_observations import (  # noqa: E402
    main as admit_boundary_observations_main,
)


class Tlul10818BoundaryBenchmarkContractTest(unittest.TestCase):
    def test_target_identity_and_external_authority_are_fixed(self) -> None:
        contract = load_contract()
        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(contract["surface"], "tlul10818_boundary_benchmark_target")
        self.assertEqual(contract["status"], "pending_external_full_grid_evidence")
        target = contract["target"]
        self.assertEqual(target["target_id"], "tlul10818")
        self.assertEqual(target["issue"], "https://github.com/lowRISC/opentitan/issues/10818")
        self.assertRegex(target["bad_revision"], HEX40)
        self.assertRegex(target["fixed_revision"], HEX40)
        self.assertNotEqual(target["bad_revision"], target["fixed_revision"])
        authority = contract["authority"]
        self.assertIs(authority["codex_runtime_execution"], False)
        self.assertEqual(authority["runtime_owner"], "external_operator_or_ci")
        self.assertRegex(authority["adjudicator_commit"], HEX40)
        self.assertEqual(
            authority["adjudicator_commit_status"],
            "pinned",
        )
        self.assertEqual(
            authority["required_adjudicator_surfaces"],
            [
                "rtl_boundary_sweep_enumeration",
                "rtl_boundary_selector_response",
                "rtl_boundary_experiment_contract",
                "rtl_boundary_evidence_bundle",
                "rtl_boundary_ground_truth",
                "rtl_boundary_analysis",
                "rtl_boundary_policy_trial",
                "rtl_boundary_policy_analysis",
                "rtl_boundary_adjudication",
                "rtl_boundary_plot_payload",
                "rtl_boundary_report_bundle",
                "rtl_boundary_report_validation",
                "rtl_boundary_pipeline_result",
            ],
        )
        doc_text = DOC.read_text(encoding="utf-8")
        self.assertIn(authority["adjudicator_commit"], doc_text)
        self.assertIn("ground-truth/policy-analysis surfaces", doc_text)
        self.assertIn("plot/report validation", doc_text)
        self.assertIn("typed selector/backend comparison adjudication schema", doc_text)
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if sidecar_src.is_dir():
            sys.path.insert(0, sidecar_src.as_posix())
            import verilator_model_sidecar

            exported = {
                value
                for name, value in vars(verilator_model_sidecar).items()
                if name.startswith("RTL_BOUNDARY_") and name.endswith("_SURFACE")
            }
            self.assertTrue(set(authority["required_adjudicator_surfaces"]) <= exported)

    def test_current_wrapper_grid_matches_existing_action_domain(self) -> None:
        contract = load_contract()
        sweep_space = contract["current_wrapper_sweep_space"]
        axes = sweep_space["axes"]
        self.assertEqual(sweep_space["surface"], "rtl_boundary_sweep_space")
        self.assertEqual([axis["kind"] for axis in axes], ["categorical", "categorical"])
        axis_names = [axis["name"] for axis in axes]
        values = [axis["values"] for axis in axes]
        expected_parameters = [
            dict(zip(axis_names, combination))
            for combination in itertools.product(*values)
        ]
        mapping = contract["current_wrapper_action_mapping"]
        self.assertEqual(
            sorted(json.dumps(item["parameters"], sort_keys=True) for item in mapping),
            sorted(json.dumps(parameters, sort_keys=True) for parameters in expected_parameters),
        )
        self.assertEqual(
            sorted(item["action"] for item in mapping),
            sorted(ACTION_DOMAIN),
        )

    def test_runner_control_surface_exposes_ordered_timing_axes_without_grid_values(self) -> None:
        surface = load_contract()["runner_control_surface"]
        self.assertEqual(surface["finite_values_owner"], "external_experiment_contract")
        self.assertEqual(surface["source_module"], "src/tools/tlul10818_gpu_schedule.py")
        self.assertEqual(
            surface["source_module_sha256"],
            hashlib.sha256((REPO_ROOT / surface["source_module"]).read_bytes()).hexdigest(),
        )
        self.assertEqual(
            surface["interfaces"],
            {
                "sweep_space": "boundary_sweep_space",
                "action_mapping": "boundary_action_mapping",
                "contract_projection": "boundary_contract_projection",
                "patch_script": "boundary_patch_script_for_parameters",
            },
        )
        axes = {axis["name"]: axis for axis in surface["axes"]}
        self.assertEqual(set(axes), {"request_integrity", "backpressure_cycles", "response_delay_cycles"})
        self.assertEqual(axes["backpressure_cycles"]["kind"], "ordered")
        self.assertEqual(axes["response_delay_cycles"]["kind"], "ordered")
        self.assertEqual(axes["backpressure_cycles"]["value_type"], "nonnegative_integer")
        self.assertEqual(axes["response_delay_cycles"]["values_owner"], "external_experiment_contract")
        self.assertNotIn("values", axes["backpressure_cycles"])
        self.assertNotIn("values", axes["response_delay_cycles"])
        self.assertEqual(
            tuple(axis["name"] for axis in RUNNER_CONTROL_AXES),
            ("request_integrity", "backpressure_cycles", "response_delay_cycles"),
        )

    def test_semantic_identity_is_pinned_to_wrapper_outputs(self) -> None:
        config = load_contract()
        surface = config["semantic_identity_surface"]
        source = REPO_ROOT / surface["source_module"]
        self.assertEqual(
            surface["interfaces"],
            {
                "semantic_identity": "build_boundary_semantic_identity",
                "experiment_contract": "build_boundary_experiment_contract",
            },
        )
        self.assertEqual(
            surface["source_module_sha256"], hashlib.sha256(source.read_bytes()).hexdigest()
        )
        identity = build_boundary_semantic_identity(config)
        target = identity["target"]
        self.assertEqual(
            target["semantic_observables"], ["done", "d_data", "d_error", "intg_error"]
        )
        self.assertEqual(target["oracle_field"], "oracle_violation")
        manifests = identity["semantic_manifests"]
        self.assertEqual(
            manifests["bad"]["observables"], manifests["fixed"]["observables"]
        )
        self.assertEqual(
            [row["width_bits"] for row in manifests["bad"]["observables"]],
            [1, 32, 1, 1, 1],
        )
        for label in ("bad", "fixed"):
            canonical = json.dumps(
                manifests[label], allow_nan=False, ensure_ascii=True,
                separators=(",", ":"), sort_keys=True,
            ).encode("utf-8")
            self.assertEqual(
                target["semantic_manifest_sha256"][label],
                hashlib.sha256(canonical).hexdigest(),
            )
        rtl = GPU_TB.read_text(encoding="utf-8")
        descriptors = config["target"]["semantic_projection"]["observables"] + [
            config["target"]["semantic_projection"]["oracle"]
        ]
        for descriptor in descriptors:
            packed = "[31:0] " if descriptor["width_bits"] == 32 else ""
            self.assertIn(f"output logic {packed}{descriptor['rtl_signal']}", rtl)
        self.assertNotIn(
            "action_coverage",
            [row["name"] for row in manifests["bad"]["observables"]],
        )

        evidence_surface = config["evidence_builder_surface"]
        evidence_source = REPO_ROOT / evidence_surface["source_module"]
        self.assertEqual(evidence_surface["interface"], "build_boundary_evidence_bundle")
        self.assertEqual(
            evidence_surface["source_module_sha256"],
            hashlib.sha256(evidence_source.read_bytes()).hexdigest(),
        )
        run_spec_surface = config["run_spec_builder_surface"]
        run_spec_source = REPO_ROOT / run_spec_surface["source_module"]
        self.assertEqual(run_spec_surface["interface"], "build_run_spec")
        self.assertEqual(
            run_spec_surface["source_module_sha256"],
            hashlib.sha256(run_spec_source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            REPO_ROOT / run_spec_surface["run_spec_schema"],
            RUN_SPEC_SCHEMA,
        )
        self.assertEqual(
            run_spec_surface["run_spec_schema_sha256"],
            hashlib.sha256(RUN_SPEC_SCHEMA.read_bytes()).hexdigest(),
        )
        execution_packet_surface = config["execution_packet_surface"]
        execution_packet_source = REPO_ROOT / execution_packet_surface["source_module"]
        self.assertEqual(execution_packet_surface["interface"], "build_execution_packet")
        self.assertEqual(
            execution_packet_surface["source_module_sha256"],
            hashlib.sha256(execution_packet_source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            REPO_ROOT / execution_packet_surface["point_result_template_schema"],
            POINT_RESULT_TEMPLATE_SCHEMA,
        )
        self.assertEqual(
            execution_packet_surface["point_result_template_schema_sha256"],
            hashlib.sha256(POINT_RESULT_TEMPLATE_SCHEMA.read_bytes()).hexdigest(),
        )
        run_result_surface = config["run_result_builder_surface"]
        run_result_source = REPO_ROOT / run_result_surface["source_module"]
        self.assertEqual(run_result_surface["interface"], "build_run_result")
        self.assertEqual(
            run_result_surface["source_module_sha256"],
            hashlib.sha256(run_result_source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            REPO_ROOT / run_result_surface["runner_observations_schema"],
            RUNNER_OBSERVATIONS_SCHEMA,
        )
        self.assertEqual(
            run_result_surface["runner_observations_schema_sha256"],
            hashlib.sha256(RUNNER_OBSERVATIONS_SCHEMA.read_bytes()).hexdigest(),
        )
        admission_surface = config["admission_pipeline_surface"]
        admission_source = REPO_ROOT / admission_surface["source_module"]
        self.assertEqual(admission_surface["interface"], "admit_observations")
        self.assertEqual(
            admission_surface["source_module_sha256"],
            hashlib.sha256(admission_source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            REPO_ROOT / admission_surface["admission_manifest_schema"],
            ADMISSION_MANIFEST_SCHEMA,
        )
        self.assertEqual(
            admission_surface["admission_manifest_schema_sha256"],
            hashlib.sha256(ADMISSION_MANIFEST_SCHEMA.read_bytes()).hexdigest(),
        )
        timing_surface = config["timing_template_surface"]
        timing_source = REPO_ROOT / timing_surface["source_module"]
        self.assertEqual(timing_surface["interface"], "build_timing_template")
        self.assertEqual(
            timing_surface["source_module_sha256"],
            hashlib.sha256(timing_source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            REPO_ROOT / timing_surface["timing_template_schema"],
            TIMING_TEMPLATE_SCHEMA,
        )
        self.assertEqual(
            timing_surface["timing_template_schema_sha256"],
            hashlib.sha256(TIMING_TEMPLATE_SCHEMA.read_bytes()).hexdigest(),
        )

    def test_semantic_identity_rejects_aliasing(self) -> None:
        config = json.loads(json.dumps(load_contract()))
        first = config["target"]["semantic_projection"]["observables"][0]
        config["target"]["semantic_projection"]["oracle"]["semantic_id"] = first[
            "semantic_id"
        ]
        with self.assertRaises(ValueError):
            build_boundary_semantic_identity(config)

    def test_boundary_patch_script_lowers_ordered_timing_controls(self) -> None:
        offsets = {
            "clk_i": 0,
            "rst_ni": 1,
            "start_i": 2,
            "malformed_i": 3,
            "d_backpressure_i": 4,
            "response_valid_i": 5,
        }
        script = boundary_patch_script(
            offsets,
            request_integrity="valid",
            backpressure_cycles=1,
            response_delay_cycles=2,
        ).splitlines()
        self.assertIn("3:0", script[0])
        self.assertIn("4:1", script[7])
        self.assertIn("5:0", script[7])
        self.assertIn("4:0", script[9])
        self.assertIn("5:0", script[9])
        self.assertIn("4:0", script[11])
        self.assertIn("5:1", script[11])

    def test_boundary_patch_script_rejects_noncanonical_cycle_counts(self) -> None:
        offsets = {
            "clk_i": 0,
            "rst_ni": 1,
            "start_i": 2,
            "malformed_i": 3,
            "d_backpressure_i": 4,
            "response_valid_i": 5,
        }
        with self.assertRaises(ValueError):
            boundary_patch_script(
                offsets,
                request_integrity="valid",
                backpressure_cycles=True,
                response_delay_cycles=0,
            )
        with self.assertRaises(ValueError):
            boundary_patch_script(
                offsets,
                request_integrity="valid",
                backpressure_cycles=0,
                response_delay_cycles=-1,
            )

    def test_uniform_scale_patch_uses_runtime_replication_surface(self) -> None:
        offsets = {
            "clk_i": 0,
            "rst_ni": 1,
            "start_i": 2,
            "malformed_i": 3,
            "d_backpressure_i": 4,
            "response_valid_i": 5,
        }
        script = uniform_scale_patch_script(offsets, 4096)
        self.assertEqual(
            script,
            boundary_patch_script(
                offsets,
                request_integrity="malformed",
                backpressure_cycles=1,
                response_delay_cycles=0,
            ),
        )
        self.assertNotIn("@4095:", script)

    def test_external_finite_values_build_runner_sweep_space_and_action_mapping(self) -> None:
        sweep_space = boundary_sweep_space(
            backpressure_cycles=(0, 3),
            response_delay_cycles=(0, 2),
        )
        self.assertEqual(
            [axis["name"] for axis in sweep_space["axes"]],
            ["request_integrity", "backpressure_cycles", "response_delay_cycles"],
        )
        self.assertEqual(sweep_space["axes"][1]["kind"], "ordered")
        self.assertEqual(sweep_space["axes"][1]["values"], [0, 3])
        self.assertEqual(sweep_space["axes"][2]["values"], [0, 2])
        mapping = boundary_action_mapping(
            backpressure_cycles=(0, 3),
            response_delay_cycles=(0, 2),
        )
        self.assertEqual(len(mapping), 8)
        self.assertEqual(mapping[0]["action"], "valid_bp0_rd0")
        self.assertEqual(mapping[-1]["action"], "malformed_bp3_rd2")
        self.assertEqual(
            mapping[-1]["parameters"],
            {
                "request_integrity": "malformed",
                "backpressure_cycles": 3,
                "response_delay_cycles": 2,
            },
        )

    def test_contract_projection_binds_sidecar_canonical_point_order(self) -> None:
        projection = boundary_contract_projection(
            backpressure_cycles=(0, 3),
            response_delay_cycles=(0, 2),
            sweep_enumerator=golden_sweep_enumerator,
        )
        self.assertEqual(
            set(projection),
            {"sweep_space", "sweep_space_sha256", "action_domain", "action_domain_sha256"},
        )
        self.assertEqual(projection["sweep_space_sha256"], GOLDEN_SWEEP_SHA256)
        self.assertEqual(projection["action_domain"][0]["action"], "malformed_bp0_rd0")
        self.assertEqual(projection["action_domain"][-1]["action"], "valid_bp3_rd2")
        canonical = json.dumps(
            projection["action_domain"], allow_nan=False, ensure_ascii=True,
            separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
        self.assertEqual(
            projection["action_domain_sha256"], hashlib.sha256(canonical).hexdigest()
        )

    def test_complete_experiment_contract_is_assembled_from_pure_projections(self) -> None:
        bundle = build_boundary_experiment_contract(
            load_contract(), experiment_run_spec(), golden_sweep_enumerator
        )
        contract = bundle["experiment_contract"]
        self.assertEqual(contract["surface"], "rtl_boundary_experiment_contract")
        self.assertEqual(contract["sweep_space_sha256"], GOLDEN_SWEEP_SHA256)
        self.assertEqual(len(contract["action_domain"]), 8)
        self.assertEqual(
            {trial["policy"]["kind"] for trial in contract["trials"]},
            {"random", "stratified", "ordered_refinement", "novelty_boundary_guided"},
        )
        self.assertEqual(
            contract["reconstructor"],
            {"kind": "nearest_observed_graph", "algorithm_version": 1},
        )
        for label, manifest in bundle["semantic_manifests"].items():
            canonical = json.dumps(
                manifest, allow_nan=False, ensure_ascii=True,
                separators=(",", ":"), sort_keys=True,
            ).encode("utf-8")
            self.assertEqual(
                contract["target"]["semantic_manifest_sha256"][label],
                hashlib.sha256(canonical).hexdigest(),
            )

    def test_experiment_contract_rejects_unfair_comparisons(self) -> None:
        run_spec = experiment_run_spec()
        cpu = next(row for row in run_spec["trials"] if row["trial_id"] == "random_cpu")
        cpu["policy"] = json.loads(json.dumps(cpu["policy"]))
        cpu["policy"]["seed_sha256"] = "2" * 64
        with self.assertRaises(ValueError):
            build_boundary_experiment_contract(
                load_contract(), run_spec, golden_sweep_enumerator
            )

        missing_policy = experiment_run_spec()
        missing_policy["trials"] = [
            row for row in missing_policy["trials"]
            if row["trial_id"] != "novelty_gpu"
        ]
        missing_policy["comparisons"][0]["trial_ids"].remove("novelty_gpu")
        with self.assertRaises(ValueError):
            build_boundary_experiment_contract(
                load_contract(), missing_policy, golden_sweep_enumerator
            )

    def test_evidence_bundle_derives_ground_truth_from_raw_semantics(self) -> None:
        contract_bundle = build_boundary_experiment_contract(
            load_contract(), experiment_run_spec(), golden_sweep_enumerator
        )
        contract = contract_bundle["experiment_contract"]
        evidence = build_boundary_evidence_bundle(
            contract_bundle, raw_run_result(contract)
        )
        self.assertEqual(evidence["surface"], "rtl_boundary_evidence_bundle")
        self.assertEqual(
            [row["point_id"] for row in evidence["ground_truth"]["observations"]],
            [row["point_id"] for row in contract["action_domain"]],
        )
        self.assertEqual(
            sum(row["bad_oracle"] for row in evidence["ground_truth"]["observations"]),
            4,
        )
        self.assertEqual(
            sum(row["fixed_oracle"] for row in evidence["ground_truth"]["observations"]),
            0,
        )
        self.assertEqual(
            evidence["semantic_manifests"], contract_bundle["semantic_manifests"]
        )

    def test_evidence_bundle_rejects_incomplete_or_mismatched_raw_points(self) -> None:
        contract_bundle = build_boundary_experiment_contract(
            load_contract(), experiment_run_spec(), golden_sweep_enumerator
        )
        raw = raw_run_result(contract_bundle["experiment_contract"])
        raw["point_results"][0]["revisions"]["bad"]["gpu"]["done"] = True
        with self.assertRaises(ValueError):
            build_boundary_evidence_bundle(contract_bundle, raw)

        incomplete = raw_run_result(contract_bundle["experiment_contract"])
        incomplete["point_results"].pop()
        with self.assertRaises(ValueError):
            build_boundary_evidence_bundle(contract_bundle, incomplete)

        missing_trial = raw_run_result(contract_bundle["experiment_contract"])
        missing_trial["trials"].pop()
        with self.assertRaises(ValueError):
            build_boundary_evidence_bundle(contract_bundle, missing_trial)

        wrong_trial_shape = raw_run_result(contract_bundle["experiment_contract"])
        wrong_trial_shape["trials"][0] = {
            "trial_id": wrong_trial_shape["trials"][0]["trial_id"],
            "external_result": "not-sidecar-ready",
        }
        with self.assertRaises(ValueError):
            build_boundary_evidence_bundle(contract_bundle, wrong_trial_shape)

        def selector(_sweep_space, _policy, _completed_batches, requested_count):
            completed = {
                point_id
                for batch in _completed_batches
                for point_id in batch["selected_point_ids"]
            }
            return [
                row["point_id"]
                for row in contract_bundle["experiment_contract"]["action_domain"]
                if row["point_id"] not in completed
            ][:requested_count]

        def bad_timing(_trial_id, _launch_index, _group):
            return {"cycle_evals": 1, "start_offset_ns": 2, "end_offset_ns": 1}

        with self.assertRaises(ValueError):
            build_boundary_trial_evidence(
                contract_bundle["experiment_contract"],
                raw_run_result(contract_bundle["experiment_contract"])["point_results"],
                selector,
                bad_timing,
            )

    def test_runner_point_parameters_are_the_patch_script_interface(self) -> None:
        offsets = {
            "clk_i": 0,
            "rst_ni": 1,
            "start_i": 2,
            "malformed_i": 3,
            "d_backpressure_i": 4,
            "response_valid_i": 5,
        }
        parameters = {
            "request_integrity": "valid",
            "backpressure_cycles": 3,
            "response_delay_cycles": 1,
        }
        self.assertEqual(boundary_action_name(parameters), "valid_bp3_rd1")
        direct = boundary_patch_script(
            offsets,
            request_integrity="valid",
            backpressure_cycles=3,
            response_delay_cycles=1,
        )
        self.assertEqual(boundary_patch_script_for_parameters(offsets, parameters), direct)

    def test_runner_point_parameters_reject_unknown_axes(self) -> None:
        offsets = {
            "clk_i": 0,
            "rst_ni": 1,
            "start_i": 2,
            "malformed_i": 3,
            "d_backpressure_i": 4,
            "response_valid_i": 5,
        }
        with self.assertRaises(ValueError):
            boundary_patch_script_for_parameters(
                offsets,
                {
                    "request_integrity": "valid",
                    "backpressure_cycles": 0,
                    "response_delay_cycles": 0,
                    "unused_axis": 0,
                },
            )

    def test_runner_sweep_space_rejects_invalid_external_finite_values(self) -> None:
        with self.assertRaises(ValueError):
            boundary_sweep_space(backpressure_cycles=(), response_delay_cycles=(0,))
        with self.assertRaises(ValueError):
            boundary_sweep_space(backpressure_cycles=(0, 0), response_delay_cycles=(0,))
        with self.assertRaises(ValueError):
            boundary_sweep_space(backpressure_cycles=(False,), response_delay_cycles=(0,))
        with self.assertRaises(ValueError):
            boundary_sweep_space(backpressure_cycles=(3, 0), response_delay_cycles=(0,))

    def test_completion_requirements_reject_runtime_and_algorithm_overclaims(self) -> None:
        requirements = load_contract()["completion_requirements"]
        self.assertIs(requirements["current_wrapper_is_not_full_boundary_benchmark"], True)
        self.assertIs(requirements["external_runner_must_generate_complete_ground_truth"], True)
        self.assertIs(
            requirements["external_runner_must_generate_action_domain_from_runner_control_surface"],
            True,
        )
        self.assertIs(requirements["external_runner_must_record_raw_trial_executions_and_launches"], True)
        self.assertIs(requirements["no_unknown_bug_discovery_claim"], True)
        self.assertIs(requirements["no_ppo_or_rl_superiority_claim"], True)
        self.assertIs(requirements["no_gpu_selector_algorithm_superiority_claim"], True)

    def test_expected_artifacts_are_generated_outputs_not_source_of_truth(self) -> None:
        artifacts = load_contract()["expected_artifacts"]
        self.assertEqual(
            set(artifacts),
            {
                "run_spec",
                "runner_observations",
                "sweep_enumeration",
                "semantic_manifests",
                "experiment_contract",
                "run_result",
                "evidence_bundle",
                "pipeline_result",
                "graph_svg",
                "markdown_report",
                "admission_manifest",
            },
        )
        self.assertEqual(len(artifacts), len(set(artifacts.values())))
        for relative in artifacts.values():
            self.assertFalse(Path(relative).is_absolute())
            self.assertTrue(relative.startswith("artifacts/tlul10818_boundary_benchmark/"))
        self.assertTrue(DOC.is_file())
        doc_text = DOC.read_text(encoding="utf-8")
        self.assertIn("not contain runtime evidence", doc_text)
        self.assertIn("Codex must not", doc_text)
        self.assertIn(SCRIPT.relative_to(REPO_ROOT).as_posix(), doc_text)

    def test_adjudication_script_is_static_json_only(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("adjudicate-boundary-benchmark", text)
        self.assertNotIn("run_tlul10818", text)
        self.assertNotIn("--bad", text)
        self.assertNotIn("--fixed", text)
        self.assertNotIn("opentitan-", text)

    def test_adjudication_script_delegates_to_configurable_adjudicator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            capture = directory / "argv.txt"
            fake = directory / "fake-sidecar"
            fake.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"${CAPTURE}\"\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "BOUNDARY_ADJUDICATOR_BIN": fake.as_posix(),
                    "CAPTURE": capture.as_posix(),
                }
            )
            completed = subprocess.run(
                [SCRIPT.as_posix()],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            argv = capture.read_text(encoding="utf-8").splitlines()
        self.assertEqual(argv[0], "adjudicate-boundary-benchmark")
        self.assertIn("--experiment-contract", argv)
        self.assertIn("--evidence", argv)
        self.assertIn("--output", argv)

    def test_boundary_artifact_builder_is_json_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            run_spec_path = directory / "run_spec.json"
            enumeration_path = directory / "sweep_enumeration.json"
            run_result_path = directory / "run_result.json"
            output_dir = directory / "out"

            run_spec = experiment_run_spec()
            contract_bundle = build_boundary_experiment_contract(
                load_contract(), run_spec, golden_sweep_enumerator
            )
            run_spec_path.write_text(json.dumps(run_spec), encoding="utf-8")
            enumeration_path.write_text(
                json.dumps(
                    golden_sweep_enumerator(
                        contract_bundle["experiment_contract"]["sweep_space"]
                    )
                ),
                encoding="utf-8",
            )
            run_result_path.write_text(
                json.dumps(raw_run_result(contract_bundle["experiment_contract"])),
                encoding="utf-8",
            )

            exit_code = build_boundary_artifacts_main(
                [
                    "--target-config",
                    CONTRACT.as_posix(),
                    "--run-spec",
                    run_spec_path.as_posix(),
                    "--sweep-enumeration",
                    enumeration_path.as_posix(),
                    "--run-result",
                    run_result_path.as_posix(),
                    "--out-dir",
                    output_dir.as_posix(),
                ]
            )
            self.assertEqual(exit_code, 0)
            experiment_contract = json.loads(
                (output_dir / "experiment_contract.json").read_text(encoding="utf-8")
            )
            evidence_bundle = json.loads(
                (output_dir / "evidence_bundle.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                experiment_contract["surface"], "rtl_boundary_experiment_contract"
            )
            self.assertEqual(evidence_bundle["surface"], "rtl_boundary_evidence_bundle")
            self.assertEqual(
                evidence_bundle["experiment_contract_sha256"],
                hashlib.sha256(
                    json.dumps(
                        experiment_contract,
                        allow_nan=False,
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest(),
            )

    def test_boundary_run_spec_builder_materializes_fair_comparisons(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run_spec.json"
            self.assertEqual(
                build_run_spec_main(
                    [
                        "--experiment-id",
                        "opentitan-tlul10818-boundary-cli-fixture-v1",
                        "--backpressure-cycles",
                        "0,3",
                        "--response-delay-cycles",
                        "0,2",
                        "--cpu-executor-identity",
                        "cpu-reference:fixture",
                        "--gpu-executor-identity",
                        "gpu-resident:fixture",
                        "--gpu-resident-width",
                        "8",
                        "--requested-count",
                        "2",
                        "--budget-logical-bad-queries",
                        "8",
                        "--seed-sha256",
                        "1" * 64,
                        "--out",
                        output.as_posix(),
                    ]
                ),
                0,
            )
            run_spec = json.loads(output.read_text(encoding="utf-8"))
            schema = json.loads(RUN_SPEC_SCHEMA.read_text(encoding="utf-8"))
            self.assertEqual(schema["additionalProperties"], False)
            self.assertEqual(
                schema["required"],
                [
                    "experiment_id",
                    "finite_axis_values",
                    "backends",
                    "trials",
                    "comparisons",
                ],
            )
            self.assertEqual(
                schema["properties"]["trials"]["items"]["$ref"], "#/$defs/trial"
            )
            self.assertEqual(
                schema["$defs"]["trial"]["properties"]["policy"]["$ref"],
                "#/$defs/policy",
            )
            self.assertEqual(
                set(
                    schema["$defs"]["policy"]["properties"]["kind"]["enum"]
                ),
                {"random", "stratified", "ordered_refinement", "novelty_boundary_guided"},
            )
            contract_bundle = build_boundary_experiment_contract(
                load_contract(), run_spec, golden_sweep_enumerator
            )
            self.assertEqual(
                contract_bundle["experiment_contract"]["experiment_id"],
                "opentitan-tlul10818-boundary-cli-fixture-v1",
            )
            self.assertEqual(
                {trial["policy"]["kind"] for trial in run_spec["trials"]},
                {"random", "stratified", "ordered_refinement", "novelty_boundary_guided"},
            )

    def test_boundary_execution_packet_lists_all_points_without_observations(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            run_spec_path = directory / "run_spec.json"
            out_dir = directory / "packet"
            run_spec_path.write_text(json.dumps(experiment_run_spec()), encoding="utf-8")
            self.assertEqual(
                build_execution_packet_main(
                    [
                        "--target-config",
                        CONTRACT.as_posix(),
                        "--run-spec",
                        run_spec_path.as_posix(),
                        "--sidecar-src",
                        sidecar_src.as_posix(),
                        "--out-dir",
                        out_dir.as_posix(),
                    ]
                ),
                0,
            )
            contract = json.loads(
                (out_dir / "experiment_contract.json").read_text(encoding="utf-8")
            )
            template = json.loads(
                (out_dir / "point_result_template.json").read_text(encoding="utf-8")
            )
            schema = json.loads(POINT_RESULT_TEMPLATE_SCHEMA.read_text(encoding="utf-8"))
            self.assertEqual(schema["additionalProperties"], False)
            self.assertEqual(
                schema["required"],
                [
                    "schema_version",
                    "surface",
                    "experiment_id",
                    "sweep_space_sha256",
                    "action_domain_sha256",
                    "semantic_projection_keys",
                    "oracle_field",
                    "rows",
                ],
            )
            self.assertEqual(schema["properties"]["rows"]["items"]["$ref"], "#/$defs/row")
            self.assertEqual(schema["$defs"]["row"]["additionalProperties"], False)
            self.assertEqual(
                template["surface"], "tlul10818_boundary_point_result_template"
            )
            self.assertEqual(template["experiment_id"], contract["experiment_id"])
            self.assertEqual(
                template["semantic_projection_keys"],
                ["done", "d_data", "d_error", "intg_error", "oracle_violation"],
            )
            self.assertEqual(len(template["rows"]), len(contract["action_domain"]))
            self.assertEqual(
                [row["point_id"] for row in template["rows"]],
                [row["point_id"] for row in contract["action_domain"]],
            )
            self.assertTrue(
                all("observed" not in json.dumps(row) for row in template["rows"])
            )
            self.assertTrue((out_dir / "sweep_enumeration.json").is_file())
            self.assertTrue((out_dir / "semantic_manifests.json").is_file())

    def test_boundary_run_result_builder_materializes_sidecar_trial_surface(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        sys.path.insert(0, sidecar_src.as_posix())
        from verilator_model_sidecar.sweep_boundary import select_boundary_points

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            contract_path = directory / "experiment_contract.json"
            observations_path = directory / "runner_observations.json"
            output_path = directory / "run_result.json"
            contract_bundle = build_boundary_experiment_contract(
                load_contract(), experiment_run_spec(), golden_sweep_enumerator
            )
            contract = contract_bundle["experiment_contract"]
            fixture_result = raw_run_result(contract, selector=select_boundary_points)
            timing_rows = [
                {
                    "trial_id": trial["trial_id"],
                    "launch_index": index,
                    "cycle_evals": launch["resident_width"],
                    "start_offset_ns": launch["start_offset_ns"],
                    "end_offset_ns": launch["end_offset_ns"],
                }
                for trial in fixture_result["trials"]
                for index, launch in enumerate(trial["launches"])
            ]
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            observations_path.write_text(
                json.dumps(
                    {
                        "runner": fixture_result["runner"],
                        "point_results": fixture_result["point_results"],
                        "timing": timing_rows,
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                build_run_result_main(
                    [
                        "--experiment-contract",
                        contract_path.as_posix(),
                        "--runner-observations",
                        observations_path.as_posix(),
                        "--sidecar-src",
                        sidecar_src.as_posix(),
                        "--out",
                        output_path.as_posix(),
                    ]
                ),
                0,
            )
            run_result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(set(run_result), {"runner", "point_results", "trials"})
            self.assertEqual(run_result["runner"], fixture_result["runner"])
            self.assertEqual(run_result["point_results"], fixture_result["point_results"])
            self.assertEqual(
                [trial["trial_id"] for trial in run_result["trials"]],
                [trial["trial_id"] for trial in contract["trials"]],
            )
            self.assertTrue(
                all(
                    trial["policy_trial"]["surface"] == "rtl_boundary_policy_trial"
                    for trial in run_result["trials"]
                )
            )

    def test_boundary_runner_observations_schema_matches_builder_input_surface(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        sys.path.insert(0, sidecar_src.as_posix())
        from verilator_model_sidecar.sweep_boundary import select_boundary_points

        contract_bundle = build_boundary_experiment_contract(
            load_contract(), experiment_run_spec(), golden_sweep_enumerator
        )
        contract = contract_bundle["experiment_contract"]
        fixture_result = raw_run_result(contract, selector=select_boundary_points)
        observations = {
            "runner": fixture_result["runner"],
            "point_results": fixture_result["point_results"],
            "timing": [
                {
                    "trial_id": trial["trial_id"],
                    "launch_index": index,
                    "cycle_evals": launch["resident_width"],
                    "start_offset_ns": launch["start_offset_ns"],
                    "end_offset_ns": launch["end_offset_ns"],
                }
                for trial in fixture_result["trials"]
                for index, launch in enumerate(trial["launches"])
            ],
        }
        schema = json.loads(RUNNER_OBSERVATIONS_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["additionalProperties"], False)
        self.assertEqual(schema["required"], ["runner", "point_results", "timing"])
        self.assertEqual(
            schema["properties"]["runner"]["properties"]["status"]["const"], "pass"
        )
        self.assertEqual(
            schema["properties"]["point_results"]["items"]["$ref"],
            "#/$defs/point_result",
        )
        self.assertEqual(
            schema["properties"]["timing"]["items"]["$ref"], "#/$defs/timing_row"
        )
        timing_row = schema["$defs"]["timing_row"]
        self.assertEqual(
            schema["$defs"]["semantic_projection"]["additionalProperties"],
            {"type": "integer"},
        )
        self.assertEqual(
            timing_row["required"],
            [
                "trial_id",
                "launch_index",
                "cycle_evals",
                "start_offset_ns",
                "end_offset_ns",
            ],
        )
        self.assertEqual(timing_row["additionalProperties"], False)

        build_run_result(
            experiment_contract=contract,
            runner_observations=observations,
            selector=select_boundary_points,
        )

        invalid = json.loads(json.dumps(observations))
        invalid["timing"][0]["launch_index"] = True
        with self.assertRaises(ValueError):
            build_run_result(
                experiment_contract=contract,
                runner_observations=invalid,
                selector=select_boundary_points,
            )

    def test_boundary_timing_template_lists_launches_without_fabricating_timing(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        sys.path.insert(0, sidecar_src.as_posix())
        from verilator_model_sidecar.sweep_boundary import select_boundary_points

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            contract_path = directory / "experiment_contract.json"
            point_results_path = directory / "point_results.json"
            output_path = directory / "timing_template.json"
            contract_bundle = build_boundary_experiment_contract(
                load_contract(), experiment_run_spec(), golden_sweep_enumerator
            )
            contract = contract_bundle["experiment_contract"]
            fixture_result = raw_run_result(contract, selector=select_boundary_points)
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            point_results_path.write_text(
                json.dumps({"point_results": fixture_result["point_results"]}),
                encoding="utf-8",
            )
            self.assertEqual(
                build_timing_template_main(
                    [
                        "--experiment-contract",
                        contract_path.as_posix(),
                        "--point-results",
                        point_results_path.as_posix(),
                        "--sidecar-src",
                        sidecar_src.as_posix(),
                        "--out",
                        output_path.as_posix(),
                    ]
                ),
                0,
            )
            template = json.loads(output_path.read_text(encoding="utf-8"))
            schema = json.loads(TIMING_TEMPLATE_SCHEMA.read_text(encoding="utf-8"))
            self.assertEqual(schema["additionalProperties"], False)
            self.assertEqual(
                schema["required"],
                [
                    "schema_version",
                    "surface",
                    "experiment_id",
                    "sweep_space_sha256",
                    "action_domain_sha256",
                    "timing_rows",
                ],
            )
            self.assertEqual(
                schema["properties"]["timing_rows"]["items"]["$ref"],
                "#/$defs/timing_row",
            )
            self.assertEqual(
                schema["$defs"]["timing_row"]["additionalProperties"], False
            )
            self.assertEqual(template["surface"], "tlul10818_boundary_timing_template")
            self.assertEqual(template["experiment_id"], contract["experiment_id"])
            self.assertEqual(template["sweep_space_sha256"], contract["sweep_space_sha256"])
            rows = template["timing_rows"]
            self.assertGreater(len(rows), 0)
            self.assertTrue(
                all(
                    row["runner_must_fill"]
                    == ["cycle_evals", "start_offset_ns", "end_offset_ns"]
                    for row in rows
                )
            )
            self.assertTrue(all("cycle_evals" not in row for row in rows))
            self.assertTrue(all(row["execution_requests"] for row in rows))

    def test_boundary_timing_template_rejects_point_results_from_other_contract(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        sys.path.insert(0, sidecar_src.as_posix())
        from verilator_model_sidecar.sweep_boundary import select_boundary_points

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            contract_path = directory / "experiment_contract.json"
            point_results_path = directory / "point_results.json"
            output_path = directory / "timing_template.json"
            contract_bundle = build_boundary_experiment_contract(
                load_contract(), experiment_run_spec(), golden_sweep_enumerator
            )
            contract = contract_bundle["experiment_contract"]
            fixture_result = raw_run_result(contract, selector=select_boundary_points)
            bad_point_results = json.loads(json.dumps(fixture_result["point_results"]))
            bad_point_results[0]["point_id"] = (
                "point:v1:" + "0" * 64
            )
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            point_results_path.write_text(
                json.dumps({"point_results": bad_point_results}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                build_timing_template_main(
                    [
                        "--experiment-contract",
                        contract_path.as_posix(),
                        "--point-results",
                        point_results_path.as_posix(),
                        "--sidecar-src",
                        sidecar_src.as_posix(),
                        "--out",
                        output_path.as_posix(),
                    ]
                )

    def test_boundary_run_result_builder_rejects_timing_mismatch(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        sys.path.insert(0, sidecar_src.as_posix())
        from verilator_model_sidecar.sweep_boundary import select_boundary_points

        contract_bundle = build_boundary_experiment_contract(
            load_contract(), experiment_run_spec(), golden_sweep_enumerator
        )
        contract = contract_bundle["experiment_contract"]
        fixture_result = raw_run_result(contract, selector=select_boundary_points)
        timing_rows = [
            {
                "trial_id": trial["trial_id"],
                "launch_index": index,
                "cycle_evals": launch["resident_width"],
                "start_offset_ns": launch["start_offset_ns"],
                "end_offset_ns": launch["end_offset_ns"],
            }
            for trial in fixture_result["trials"]
            for index, launch in enumerate(trial["launches"])
        ]
        observations = {
            "runner": fixture_result["runner"],
            "point_results": fixture_result["point_results"],
            "timing": timing_rows[:-1],
        }
        with self.assertRaises(ValueError):
            build_run_result(
                experiment_contract=contract,
                runner_observations=observations,
                selector=select_boundary_points,
            )

        observations["timing"] = timing_rows + [dict(timing_rows[-1])]
        with self.assertRaises(ValueError):
            build_run_result(
                experiment_contract=contract,
                runner_observations=observations,
                selector=select_boundary_points,
            )

    def test_boundary_admission_pipeline_consumes_runner_observations(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        sys.path.insert(0, sidecar_src.as_posix())
        from verilator_model_sidecar.sweep_boundary import select_boundary_points

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            run_spec_path = directory / "run_spec.json"
            observations_path = directory / "runner_observations.json"
            output_dir = directory / "admitted"
            wrapper = directory / "verilator-model-sidecar"
            wrapper.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "PYTHONPATH=\"${SIDECAR_SRC}\" "
                "python3 -m verilator_model_sidecar.cli \"$@\"\n",
                encoding="utf-8",
            )
            wrapper.chmod(0o755)

            contract_bundle = build_boundary_experiment_contract(
                load_contract(), experiment_run_spec(), golden_sweep_enumerator
            )
            contract = contract_bundle["experiment_contract"]
            fixture_result = raw_run_result(contract, selector=select_boundary_points)
            runner_observations = {
                "runner": fixture_result["runner"],
                "point_results": fixture_result["point_results"],
                "timing": [
                    {
                        "trial_id": trial["trial_id"],
                        "launch_index": index,
                        "cycle_evals": launch["resident_width"],
                        "start_offset_ns": launch["start_offset_ns"],
                        "end_offset_ns": launch["end_offset_ns"],
                    }
                    for trial in fixture_result["trials"]
                    for index, launch in enumerate(trial["launches"])
                ],
            }
            run_spec_path.write_text(json.dumps(experiment_run_spec()), encoding="utf-8")
            observations_path.write_text(
                json.dumps(runner_observations), encoding="utf-8"
            )
            previous = os.environ.get("SIDECAR_SRC")
            os.environ["SIDECAR_SRC"] = sidecar_src.as_posix()
            try:
                exit_code = admit_boundary_observations_main(
                    [
                        "--target-config",
                        CONTRACT.as_posix(),
                        "--run-spec",
                        run_spec_path.as_posix(),
                        "--runner-observations",
                        observations_path.as_posix(),
                        "--sidecar-src",
                        sidecar_src.as_posix(),
                        "--adjudicator-bin",
                        wrapper.as_posix(),
                        "--out-dir",
                        output_dir.as_posix(),
                    ]
                )
            finally:
                if previous is None:
                    os.environ.pop("SIDECAR_SRC", None)
                else:
                    os.environ["SIDECAR_SRC"] = previous
            self.assertEqual(exit_code, 0)
            pipeline = json.loads(
                (output_dir / "pipeline_result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(pipeline["status"], "pass")
            self.assertEqual(pipeline["adjudication"]["status"], "pass")
            self.assertTrue((output_dir / "sweep_enumeration.json").is_file())
            self.assertTrue((output_dir / "semantic_manifests.json").is_file())
            self.assertTrue((output_dir / "experiment_contract.json").is_file())
            self.assertTrue((output_dir / "run_spec.json").is_file())
            self.assertTrue((output_dir / "runner_observations.json").is_file())
            self.assertTrue((output_dir / "run_result.json").is_file())
            self.assertTrue((output_dir / "evidence_bundle.json").is_file())
            self.assertEqual(
                json.loads((output_dir / "run_spec.json").read_text(encoding="utf-8")),
                experiment_run_spec(),
            )
            self.assertEqual(
                json.loads(
                    (output_dir / "runner_observations.json").read_text(
                        encoding="utf-8"
                    )
                ),
                runner_observations,
            )
            self.assertIsNotNone(pipeline["graph_artifact"])
            self.assertIsNotNone(pipeline["markdown_artifact"])
            manifest_path = output_dir / "admission_manifest.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            schema = json.loads(ADMISSION_MANIFEST_SCHEMA.read_text(encoding="utf-8"))
            self.assertEqual(schema["additionalProperties"], False)
            self.assertEqual(
                set(schema["$defs"]["role"]["enum"]),
                set(load_contract()["expected_artifacts"]) - {"admission_manifest"},
            )
            self.assertEqual(manifest["surface"], "tlul10818_boundary_admission_manifest")
            self.assertEqual(manifest["status"], "pass")
            rows = {row["role"]: row for row in manifest["artifacts"]}
            self.assertEqual(set(rows), set(schema["$defs"]["role"]["enum"]))
            for role, row in rows.items():
                artifact = output_dir / row["path"]
                self.assertTrue(artifact.is_file(), role)
                self.assertEqual(
                    row["sha256"],
                    hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    role,
                )

    def test_boundary_admission_pipeline_replaces_stale_pass_on_input_error(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            run_spec_path = directory / "run_spec.json"
            observations_path = directory / "runner_observations.json"
            output_dir = directory / "admitted"
            pipeline_path = output_dir / "pipeline_result.json"
            output_dir.mkdir()
            pipeline_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "surface": "rtl_boundary_pipeline_result",
                        "status": "pass",
                        "adjudication": {"status": "pass"},
                        "report_bundle": {},
                        "graph_artifact": {},
                        "markdown_artifact": {},
                    }
                ),
                encoding="utf-8",
            )
            run_spec_path.write_text(json.dumps(experiment_run_spec()), encoding="utf-8")
            observations_path.write_text('{"runner": {"status": "pass"}}', encoding="utf-8")

            exit_code = admit_boundary_observations_main(
                [
                    "--target-config",
                    CONTRACT.as_posix(),
                    "--run-spec",
                    run_spec_path.as_posix(),
                    "--runner-observations",
                    observations_path.as_posix(),
                    "--sidecar-src",
                    sidecar_src.as_posix(),
                    "--adjudicator-bin",
                    "unused-for-invalid-input",
                    "--out-dir",
                    output_dir.as_posix(),
                ]
            )
            self.assertEqual(exit_code, 1)
            pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
            self.assertEqual(pipeline["status"], "fail")
            self.assertEqual(pipeline["adjudication"]["status"], "fail")
            self.assertEqual(pipeline["report_bundle"], None)
            self.assertEqual(pipeline["graph_artifact"], None)
            self.assertEqual(pipeline["markdown_artifact"], None)
            self.assertEqual(
                pipeline["adjudication"]["issues"][0]["code"],
                "admission_input_error",
            )
            self.assertEqual(
                pipeline["adjudication"]["input_file_sha256"],
                {"experiment_contract": None, "evidence_bundle": None},
            )

    def test_boundary_artifacts_pass_real_sidecar_adjudication(self) -> None:
        sidecar_src = Path("/home/takatodo/circt_manage/coverage/src")
        if not sidecar_src.is_dir():
            self.skipTest("verilator-model-sidecar source checkout is unavailable")
        sys.path.insert(0, sidecar_src.as_posix())
        from verilator_model_sidecar.sweep_boundary import select_boundary_points

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            run_spec_path = directory / "run_spec.json"
            enumeration_path = directory / "sweep_enumeration.json"
            run_result_path = directory / "run_result.json"
            output_dir = directory / "out"
            pipeline_path = output_dir / "pipeline_result.json"
            wrapper = directory / "verilator-model-sidecar"
            wrapper.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "PYTHONPATH=\"${SIDECAR_SRC}\" "
                "python3 -m verilator_model_sidecar.cli \"$@\"\n",
                encoding="utf-8",
            )
            wrapper.chmod(0o755)

            run_spec = experiment_run_spec()
            contract_bundle = build_boundary_experiment_contract(
                load_contract(), run_spec, golden_sweep_enumerator
            )
            run_spec_path.write_text(json.dumps(run_spec), encoding="utf-8")
            enumeration_path.write_text(
                json.dumps(
                    golden_sweep_enumerator(
                        contract_bundle["experiment_contract"]["sweep_space"]
                    )
                ),
                encoding="utf-8",
            )
            run_result_path.write_text(
                json.dumps(
                    raw_run_result(
                        contract_bundle["experiment_contract"],
                        selector=select_boundary_points,
                    )
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                build_boundary_artifacts_main(
                    [
                        "--target-config",
                        CONTRACT.as_posix(),
                        "--run-spec",
                        run_spec_path.as_posix(),
                        "--sweep-enumeration",
                        enumeration_path.as_posix(),
                        "--run-result",
                        run_result_path.as_posix(),
                        "--out-dir",
                        output_dir.as_posix(),
                    ]
                ),
                0,
            )
            env = os.environ.copy()
            env.update(
                {
                    "BOUNDARY_ADJUDICATOR_BIN": wrapper.as_posix(),
                    "SIDECAR_SRC": sidecar_src.as_posix(),
                    "CONTRACT": (output_dir / "experiment_contract.json").as_posix(),
                    "EVIDENCE": (output_dir / "evidence_bundle.json").as_posix(),
                    "OUTPUT": pipeline_path.as_posix(),
                }
            )
            completed = subprocess.run(
                [SCRIPT.as_posix()],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
            self.assertEqual(pipeline["status"], "pass")
            self.assertEqual(pipeline["adjudication"]["status"], "pass")
            self.assertIsNotNone(pipeline["report_bundle"])
            self.assertIsNotNone(pipeline["graph_artifact"])
            self.assertIsNotNone(pipeline["markdown_artifact"])

    def test_boundary_artifact_builder_rejects_non_strict_json_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            nan_path = directory / "nan.json"
            duplicate_path = directory / "duplicate.json"
            nan_path.write_text('{"value": NaN}', encoding="utf-8")
            duplicate_path.write_text('{"value": 1, "value": 2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_artifact_object(nan_path, "fixture")
            with self.assertRaises(ValueError):
                read_artifact_object(duplicate_path, "fixture")


def run_contract_checks(case: unittest.TestCase) -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        Tlul10818BoundaryBenchmarkContractTest
    )
    result = unittest.TestResult()
    suite.run(result)
    if result.wasSuccessful():
        return
    details = []
    for test, error in result.errors + result.failures:
        details.append(f"{test.id()}\n{error}")
    case.fail("\n\n".join(details))
