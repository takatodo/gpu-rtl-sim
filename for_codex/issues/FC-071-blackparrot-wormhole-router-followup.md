# FC-071: BlackParrot bsg_wormhole_router resident packet-pattern follow-up

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/70
Parent: FC-070
Related: FC-063 / https://github.com/takatodo/gpu-rtl-sim/issues/64, FC-065 / https://github.com/takatodo/gpu-rtl-sim/issues/65

## Objective

Advance the BlackParrot BaseJump `bsg_wormhole_router` heavy-RTL candidate
after the completed `32x1` / `64x1` / `128x1` / `256x1` repeat-median
packet-batch shape sweep. The larger packet-batch shape path remains favorable,
and the resident/multi-step definition gate plus dry-run resident command-plan
surface now exist. The next stabilizing task is to materialize the BlackParrot
packet-pattern patch script, or record that patch-script source as the named
blocker outcome.

This issue should determine whether BlackParrot can gain a resident/multi-step
policy, or whether that path hits the remaining named blocker boundary.

## Current Evidence

- `32x1`: 3/3 coverage-output equivalence pass, median CPU-to-hybrid wall
  speedup `32.76216804527645x`.
- `64x1`: 3/3 coverage-output equivalence pass, median CPU-to-hybrid wall
  speedup `158.28447339847992x`.
- `128x1`: 3/3 coverage-output equivalence pass, median CPU-to-hybrid wall
  speedup `259.4919886899152x`.
- `256x1`: 3/3 coverage-output equivalence pass, median CPU-to-hybrid wall
  speedup `651.817697228145x`.
- `config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json`
  defines the scoped `256x4` resident packet-pattern timing target and expected
  report surface.
- `reports/heavy_rtl_candidate_matrix.json` classifies
  `blackparrot_bsg_wormhole_router` as `promote_state_parallel_measurement`
  with
  `source_backed_shape_sweep_promote_256x1_resident_template_surface_defined_patch_script_next`.
- `run_hybrid_template.py` now exposes a dry-run resident command-plan surface:
  `--resident-steps` requires an explicit `--patch-script`, resident non-dry
  runs require that patch script to exist, and command planning derives
  resident-specific candidate dump and compare-report paths.
- The reviewed dry-run command surface is:
  `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/blackparrot_bsg_wormhole_router.json --shape 256x4 --resident-steps --patch-script artifacts/blackparrot_bsg_wormhole_router_packet_pattern_256x4.patch --dry-run`.
- The only current named blocker before execution is
  `blackparrot_packet_pattern_patch_script_not_materialized`.
- Dry-run command planning is not resident execution evidence and does not claim
  speedup or broader BlackParrot support.

## Tasks

- Keep the reviewed resident template command plan surface stable:
  `--resident-steps`, explicit `--patch-script`, and resident-specific
  dump/report paths.
- Materialize the reproducible BlackParrot packet-pattern patch script or prove
  the existing host-probe cfg inputs are sufficient for resident steps.
- Run the `256x4` resident/multi-step measurement only after the resident
  patch-script source is explicit.
- Update `src/tools/heavy_rtl_candidate_matrix.py`,
  `reports/heavy_rtl_candidate_matrix.json`, and `config/selection.json` with
  the selected result.
- Update README, `docs/status.md`, `docs/roadmap.md`, and FC-070 so the next
  policy is not stale.
- Keep generated reports as evidence only; canonical decisions stay in
  `config/selection.json`, README, and docs.

## Acceptance

- One scoped follow-up is completed beyond the command-plan gate:
  resident/multi-step timing or a named blocker explaining why it cannot be run
  safely yet.
- Coverage-output equivalence status and mismatch count are recorded if the
  resident measurement runs.
- Median CPU/hybrid timing and sample spread are recorded if the resident
  measurement runs.
- The matrix clearly classifies BlackParrot as one of:
  - shape-extension repeat-median-backed promote with resident follow-up
    pending,
  - resident/multi-step required,
  - blocked with a named blocker.
- No broad arbitrary RTL, native Verilator option, raw full-state equality, or
  project-level GPU speedup claim is made.
- Local docs/config no longer point to an already completed BlackParrot
  measurement as the next task.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_clean_sim_prerequisites tests.contract.test_hybrid_config_template_cli tests.contract.test_heavy_rtl_candidate_matrix -q
python3 -m py_compile src/tools/hybrid_template_commands.py src/tools/run_hybrid_template.py src/tools/heavy_rtl_candidate_matrix.py tests/contract/test_clean_sim_prerequisites.py tests/contract/test_hybrid_config_template_cli.py tests/contract/test_heavy_rtl_candidate_matrix.py
python3 -m json.tool config/selection.json >/dev/null
python3 -m json.tool config/slice_launch_templates/blackparrot_bsg_wormhole_router.json >/dev/null
python3 -m json.tool config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json >/dev/null
python3 -m json.tool reports/heavy_rtl_candidate_matrix.json >/dev/null
python3 -m json.tool reports/blackparrot_bsg_wormhole_router_256x1_median.json >/dev/null
rg -n '/home|/tmp|/Users|/mnt|/workspace|/root' reports/heavy_rtl_candidate_matrix.json reports/blackparrot_bsg_wormhole_router_256x1_median.json records/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json || true
git diff --check -- README.md config/selection.json docs/status.md docs/roadmap.md for_codex/issues/FC-070-scientific-circt-gpu-candidate-search.md for_codex/issues/FC-071-blackparrot-wormhole-router-followup.md src/tools/hybrid_template_commands.py src/tools/run_hybrid_template.py src/tools/heavy_rtl_candidate_matrix.py tests/contract/test_clean_sim_prerequisites.py tests/contract/test_hybrid_config_template_cli.py tests/contract/test_heavy_rtl_candidate_matrix.py config/slice_launch_templates/blackparrot_bsg_wormhole_router.json records/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json reports/heavy_rtl_candidate_matrix.json
```
