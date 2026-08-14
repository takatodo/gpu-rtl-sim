# TL-UL #10818 Boundary Benchmark Target

`config/tlul10818_boundary_benchmark.json` records the static target authority
for turning OpenTitan TL-UL #10818 into a boundary-discovery benchmark. It does
not contain runtime evidence and must not be treated as a passing result.
The required sidecar surfaces are pinned to adjudicator commit
`5d42365c5aa6de0af0b2395bbbd2e215943d1cb1`, which includes the selector-response
surface, ground-truth/policy-analysis surfaces, plot/report validation
surfaces, and the typed selector/backend comparison adjudication schema.

The currently implemented wrapper exposes the four-action grid already used by
the TL-UL equivalence tracer:

- request integrity: `valid` or `malformed`
- D-response observation mode: `immediate` or `backpressured`

That grid is useful as the compatibility seed for action naming, checkpoint
identity, oracle identity, and semantic observables. It is not the final
boundary benchmark by itself. Completion still requires an external operator or
CI runner to generate a complete `rtl_boundary_experiment_contract` and
`rtl_boundary_evidence_bundle`, then admit them through the
`rtl_boundary_pipeline_result` surface from `verilator-model-sidecar`. The same
authority also requires the `rtl_boundary_selector_response` surface so runner
selection and sidecar replay use one Selector ABI.

The runner-facing control surface now also exposes ordered timing controls:

- `backpressure_cycles`: the number of `WaitD` cycles with `d_ready` low before
  observing the response
- `response_delay_cycles`: the number of `WaitD` cycles before the SRAM
  `rvalid` response is made visible for valid requests

The exact finite values for those ordered axes are not declared here. They
belong in the external `rtl_boundary_experiment_contract`, where the full grid
identity can be hashed and adjudicated.

`src/tools/tlul10818_gpu_schedule.py` is the runner-facing Module for that
surface. Its Interface is:

- `boundary_sweep_space(backpressure_cycles=..., response_delay_cycles=...)`
- `boundary_action_mapping(backpressure_cycles=..., response_delay_cycles=...)`
- `boundary_contract_projection(..., sweep_enumerator=...)`
- `boundary_patch_script_for_parameters(offsets, parameters)`

The runner supplies the finite ordered values and generated layout offsets. The
Module supplies canonical JSON shape, deterministic action names, and patch
schedule lowering. `config/tlul10818_boundary_benchmark.json` records the
Module path and SHA-256 so evidence can name the exact schedule semantics it
used.

`boundary_contract_projection` is the producer Seam. The external harness
passes the sidecar's canonical sweep enumerator as its Adapter; the Module then
joins the returned point IDs to runner actions in that exact order and returns
the four fields admitted by the Experiment Contract: `sweep_space`,
`sweep_space_sha256`, `action_domain`, and `action_domain_sha256`. Point-ID and
categorical ordering rules therefore remain owned by the sidecar rather than
being duplicated in the runner.

`src/tools/tlul10818_boundary_contract.py` provides the independent semantic
identity Module. `build_boundary_semantic_identity(target_config)` derives the
Experiment Contract target projection and paired bad/fixed
`rtl_boundary_semantic_manifest` documents from the tracked wrapper signal
descriptors. Both manifests have identical semantic IDs and widths; only their
revision label and revision SHA differ. Functional coverage remains trial
feedback and is deliberately excluded from semantic observable identity.

`build_boundary_experiment_contract(target_config, run_spec,
sweep_enumerator)` is the complete producer Interface. The run spec supplies
only externally chosen finite axis values, backend identities and widths,
policy trials, logical batch sizes, budgets, and comparison membership. The
Module supplies the tracked target, manifest hashes, canonical sweep/action
projection, and shared reconstructor. It rejects a run spec unless all four
declared policies are compared on one GPU backend and at least one identical
policy is compared across CPU and GPU backends.

`src/tools/build_tlul10818_boundary_run_spec.py` is the JSON producer for that
run spec. It does not choose the finite grid or benchmark budget. The external
runner or CI must pass the ordered axis values, logical batch size, bad-query
budget, selector seed, CPU executor identity, GPU executor identity, and GPU
resident width explicitly. The tool materializes the four declared selector
trials on the GPU backend plus the matching random CPU/GPU backend comparison.
Its public JSON shape is `contracts/tlul10818_boundary_run_spec.schema.json`;
the builder remains the authority for ordered-cycle monotonicity and fair
comparison semantics.

`src/tools/build_tlul10818_boundary_execution_packet.py` is the pre-runtime
handoff producer. Given the target config, run spec, and sidecar source, it
writes `sweep_enumeration.json`, `experiment_contract.json`,
`semantic_manifests.json`, and `point_result_template.json`. The template lists
every canonical point ID, action name, parameters, required bad/fixed CPU/GPU
projection keys, and coverage-field obligation. It contains no observed values
and is not runtime evidence. Its machine-readable output shape is
`contracts/tlul10818_boundary_point_result_template.schema.json`.

`src/tools/build_tlul10818_boundary_run_result.py` is the JSON producer for the
external runner's completed result. It consumes an already generated
`rtl_boundary_experiment_contract`, a runner observation JSON containing
`runner`, complete `point_results`, and runner-owned `timing` rows, then uses
the public sidecar selector ABI to materialize sidecar-ready policy trials,
executions, launches, and fixed-confirmation rows. It does not compile RTL, run
the DUT, search for the known failure, replay bad/fixed sequences, or fabricate
timing. The timing rows are consumed in deterministic launch order and rejected
if any row is missing, extra, or attached to the wrong trial/launch index.
The machine-readable input shape for that external runner JSON is
`contracts/tlul10818_boundary_runner_observations.schema.json`; semantic
projection values must be integers at the public input boundary, while exact
projection key equality and target-specific oracle binding are checked later by
the builder against the Experiment Contract.

`src/tools/admit_tlul10818_boundary_observations.py` is the JSON-only admission
pipeline for that handoff. It consumes the target config, run spec, and external
runner observations, imports the sidecar sweep enumerator and selector Adapter,
writes canonical copies of `run_spec.json` and `runner_observations.json`,
then writes `sweep_enumeration.json`, `semantic_manifests.json`,
`experiment_contract.json`, `run_result.json`, and `evidence_bundle.json` before
delegating final static adjudication and report/graph generation to
`verilator-model-sidecar adjudicate-boundary-benchmark`. It is the repository entry point after external
runtime evidence exists; it is not a DUT runner.
On a passing admission, it also writes `admission_manifest.json`, whose
public shape is `contracts/tlul10818_boundary_admission_manifest.schema.json`,
with SHA-256 rows for the preserved inputs, generated JSON, pipeline result,
graph, and Markdown report. If admission fails before final adjudication, the
script still replaces `pipeline_result.json` with a `status=fail` result so
stale passing output is not left as evidence.

`src/tools/build_tlul10818_boundary_timing_template.py` is the optional
post-observation checklist for runner timing. Trial scheduling depends on the
observed bad-revision oracle bits because only bad failures require fixed
confirmation launches. Given an Experiment Contract and complete point results,
the tool emits the exact trial/launch order and execution requests that the
external runner must time. It deliberately outputs placeholders only; the
runner must fill `cycle_evals`, `start_offset_ns`, and `end_offset_ns` in
`runner_observations.json`. Its machine-readable output shape is
`contracts/tlul10818_boundary_timing_template.schema.json`.

`src/tools/tlul10818_boundary_evidence.py` is the evidence-admission producer
Module. `build_boundary_evidence_bundle(contract_bundle, run_result)` accepts
only external runner completion identity, one raw bad/fixed CPU/GPU projection
per canonical point, and raw trial/execution/launch records. It joins point
parameters from the Contract, verifies exact CPU/GPU JSON equality, derives
bad/fixed oracle labels from the CPU projection, and emits ground truth and
semantic observations. It does not accept producer-computed boundary edges,
components, metric summaries, or pass/fail labels.

`build_boundary_trial_evidence(contract, point_results, selector, timing)` is
the runner-side helper for the trial surface. The `selector` argument is the
public Selector ABI Adapter:
`select_points(sweep_space, policy_spec, completed_public_batches,
requested_count)`. The helper feeds back only public bad observations and
coverage feature IDs, continues until the trial budget is reached or the
selector exhausts the grid, and materializes bad-search and fixed-confirmation
execution/launch rows. The `timing` Adapter supplies runner-owned
`cycle_evals`, `start_offset_ns`, and `end_offset_ns` for each launch group; the
helper does not fabricate timing for benchmark claims. It does not decide
boundary topology or metrics.
External runners may implement that Adapter by importing
`verilator_model_sidecar.select_boundary_points` or by invoking the sidecar CLI
`verilator-model-sidecar select-boundary-points` with the same four inputs. The
CLI output surface is `rtl_boundary_selector_response` and is governed by the
sidecar schema `contracts/rtl_boundary_selector_response.schema.json`. The
selector CLI rejects duplicate JSON object keys and non-finite tokens before it
selects points.

`src/tools/build_tlul10818_boundary_artifacts.py` is the JSON-only artifact
builder for an external runner. It consumes a target config, an externally
chosen run spec, a sidecar-generated sweep enumeration, and an already
generated runner result. It writes `experiment_contract.json` and
`evidence_bundle.json` under `artifacts/tlul10818_boundary_benchmark/`. It does
not compile RTL, run the DUT, replay a bad/fixed sequence, or construct runner
commands. Its JSON inputs are parsed fail-closed: duplicate object keys and
non-finite tokens such as `NaN` or `Infinity` are rejected before hashing or
artifact generation.

The runner result must already contain sidecar-ready trial evidence for every
trial declared by the Experiment Contract. Each trial row is passed through only
after its public surface is present: `trial_id`, `policy_trial`,
`fixed_confirmations`, `executions`, `launches`, and `trial_wall_time_ns`. The
builder derives ground truth and semantic observations from raw point results,
but the sidecar remains the authority for replaying selector order, budget
completion, launch accounting, fixed confirmation, and metric recomputation.

The external `rtl_boundary_experiment_contract` must include the full
projection produced from this Module, including the `action_domain` rows and
`action_domain_sha256`. The sidecar adjudicator recomputes each row against the
canonical sweep-space enumeration.

The repository-owned admission workflow is
`scripts/adjudicate_tlul10818_boundary_benchmark.sh`. It consumes only existing
JSON artifacts under `artifacts/tlul10818_boundary_benchmark/` and delegates the
static checks to `verilator-model-sidecar adjudicate-boundary-benchmark`.

Codex may review and adjudicate already-generated JSON evidence. Codex must not
compile or run the DUT, search or replay failure-triggering sequences, or emit
runner commands for reproducing the known failing condition.
