# TL-UL #10818 Boundary Benchmark Target

`config/tlul10818_boundary_benchmark.json` records the static target authority
for turning OpenTitan TL-UL #10818 into a boundary-discovery benchmark. It does
not contain runtime evidence and must not be treated as a passing result.

The currently implemented wrapper exposes the four-action grid already used by
the TL-UL equivalence tracer:

- request integrity: `valid` or `malformed`
- D-response observation mode: `immediate` or `backpressured`

That grid is useful as the compatibility seed for action naming, checkpoint
identity, oracle identity, and semantic observables. It is not the final
boundary benchmark by itself. Completion still requires an external operator or
CI runner to generate a complete `rtl_boundary_experiment_contract` and
`rtl_boundary_evidence_bundle`, then admit them through the
`rtl_boundary_pipeline_result` surface from `verilator-model-sidecar`.

The repository-owned admission workflow is
`scripts/adjudicate_tlul10818_boundary_benchmark.sh`. It consumes only existing
JSON artifacts under `artifacts/tlul10818_boundary_benchmark/` and delegates the
static checks to `verilator-model-sidecar adjudicate-boundary-benchmark`.

Codex may review and adjudicate already-generated JSON evidence. Codex must not
compile or run the DUT, search or replay failure-triggering sequences, or emit
runner commands for reproducing the known failing condition.
