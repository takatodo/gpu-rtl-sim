# FC-064: RTLMeter VeeR-EL2 design-CPU known closure and state layout

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/63
Parent: FC-037 / https://github.com/takatodo/gpu-rtl-sim/issues/2
Related:
- FC-058 / https://github.com/takatodo/gpu-rtl-sim/issues/58
- FC-057 / https://github.com/takatodo/gpu-rtl-sim/issues/57
- FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1

## Objective

Create one scoped, reviewed path for `VeeR-EL2:default` design-CPU RTLMeter
cases to be recognized as a native sidecar known closure, with explicit source
closure, preload memory/state layout boundaries, and fail-closed GPU-side
eligibility.

This is the missing prerequisite between the useful CPU-parallel design-CPU
probe and any later GPU usefulness measurement. It does not claim GPU
execution, GPU speedup, or broad RTLMeter CPU-core support.

## Current Evidence

- The CPU-parallel RTLMeter baseline runner exists at
  `src/tools/rtlmeter_cpu_parallel_baseline.py`.
- The latest runner report is
  `reports/rtlmeter_cpu_parallel_baseline_try.json`.
- That report passed with all serial/parallel observables matching, serial sum
  `70.459551s`, parallel wall `37.578359s`, speedup versus serial sum
  `1.875003x`, and two-worker efficiency `0.937502`.
- The VeeR-EL2 GPU-side RTLMeter bridge is recorded in
  `reports/rtlmeter_veer_el2_sidecar_bridge.json`; the GPU executable run report
  is under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/hello/_sidecar/`.
- The direct VeeR build now produces `vl_batch_gpu.cubin` with
  `storage_size=433472`, `state_image_kind=verilator_syms_image`,
  `prelaunch_rejection_required=false`, and
  `unsafe_syms_gep_covered_by_state_image=true`.
- The sidecar materializer writes reset/nmi vectors, stages the flat program
  memories, drives a VeeR clock/reset patch, and reaches GPU final-state
  observables `mcycle=726`, `minstret=330`, and `finish_marker_observed=true`.
- The direct bridge now reaches
  `status=verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed`:
  GPU stdout stream reconstruction matches the normalized CPU stdout, and
  `_rtlmeter_cycles.txt` is aligned to RTLMeter's injected `tb_top.core_clk`
  posedge count with `cpu_cycles=2229` and `gpu_cycles=2229`.
- `cpu_as_gpu_fallback=false`, `gpu_execution_claimed=false`,
  `timing_measured=false`, and `speedup_claimed=false` throughout.

## 2026-06-14 Progress

The first FC-064 closure-authority slice is implemented.

Changes:

- Added a target-specific RTLMeter authority registry:
  `config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json`.
- Added a native known-closure registry entry for exactly
  `rtlmeter_veer_el2_default_hello`, top `tb_top`, and the captured
  RTLMeter-generated VeeR-EL2 default/hello filelist entries.
- Extended `src/tools/verilator_native_known_closure.py` so tracked closures
  may use inline `filelist_entries` when there is no runnable launch template.
- Added focused tests proving:
  - VeeR-EL2 default/hello is recognized only with exact filelist order and
    top `tb_top`;
  - reordered or non-default/variant filelists remain unrecognized;
  - the VeeR-EL2 RTLMeter context can adopt the reviewed authority registry;
  - `VeeR-EL2:hiperf:cmark` does not adopt the default/hello authority.
- Added a guard so the `run` command blocks recognized RTLMeter closures that
  have no reviewed runtime launch template instead of trying to run `None`.

Validation:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_verilator_native_known_closure \
  tests.contract.test_rtlmeter_sidecar_authority_registry -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_verilator_native_sidecar_make_driver -q
python3 -m json.tool config/native_known_closures.json >/dev/null
python3 -m json.tool \
  config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json >/dev/null
git diff --check -- src/tools/verilator_native_known_closure.py \
  config/native_known_closures.json \
  config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json \
  tests/contract/test_verilator_native_known_closure.py \
  tests/contract/test_rtlmeter_sidecar_authority_registry.py
```

Real previous-filelist probe:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  plan --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1
```

Result:

- `status=verilator_native_sidecar_build_plan_ready`
- `recognition.status=verilator_native_known_closure_recognized`
- `target=rtlmeter_veer_el2_default_hello`
- `missing_recognition_context=[]`
- `cpu_as_gpu_fallback=false`
- `gpu_execution_claimed=false`

The `run` command now fails closed for the same recognized target with
`status=verilator_native_sidecar_blocked_launch_template` and
`missing_build_context=["launch_template"]`, because no reviewed runtime launch
template exists for VeeR-EL2 yet. This check is expected to exit nonzero:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  run --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1
```

This moves the blocker from known-closure recognition to VeeR-EL2 state-layout,
GPU artifact build/run, and stdout/cycles compare. It is still not GPU
execution or speedup evidence.

The second FC-064 slice adds a fail-closed VeeR-EL2 state/preload/observable
inspection mode to the native sidecar make driver:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  inspect-veer-el2-state-layout --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --rtlmeter-program-hex artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/VeeR-EL2/default/execute-0/hello/program.hex \
  --summary-out reports/rtlmeter_veer_el2_state_layout_inspection.json
```

Result:

- `status=verilator_native_sidecar_blocked_veer_el2_state_layout_unreviewed`
- `recognition.status=verilator_native_known_closure_recognized`
- `state_layout_inspection_performed=true`
- `state_layout_ready=false`
- `cpu_as_gpu_fallback=false`
- `gpu_execution_claimed=false`
- `speedup_claimed=false`
- `detected_layout.rtlmeter_program_identity_verified=true`
- `detected_layout.observable_root_fields_found=false`
- `detected_layout.observable_expression_binding_found=true`
- `detected_layout.mailbox_address_expression_found=true`
- `detected_layout.pc_schema_verified=true`
- `detected_layout.gpr_schema_verified=true`
- `detected_layout.staging_memory_schema_verified=true`
- `detected_layout.dccm_schema_verified=true`
- `detected_layout.dccm_bank_fields_detected=[0,1,2,3]`
- `detected_layout.iccm_schema_verified=true`
- `detected_layout.iccm_bank_fields_detected=[0,1,2,3]`
- `detected_layout.ecc_schema_verified=true`
- `detected_layout.memory_preload_schema_verified=true`
- `detected_layout.gpu_state_image_initialization_schema_verified=true`
- `detected_layout.gpu_state_image_sections=["control_scalars","dccm_banks","iccm_banks","program_staging_imem","program_staging_lmem"]`
- `detected_layout.gpu_state_image_requires_materializer=true`
- `rtlmeter_program_sha256=d0219135d529505962c1c5ed44360e91466ae046cb8ec40b5980761861c63d76`

Detected in the real generated VeeR-EL2 root/testbench:

- reset/clock root fields;
- `imem.mem` and `lmem.mem` preload backing memories;
- PC candidates and GPR indices 1 through 31;
- `mcyclel` and `minstretl` cycle counter fields;
- testbench `program.hex` readmemh preload;
- `+iterations` lmem preload patch;
- `preload_dccm()` / `preload_iccm()` with ECC/bank slam tasks;
- testbench pass/fail mailbox policy;
- generated C++ observable expression binding for mailbox stdout,
  `TEST_PASSED`/`TEST_FAILED`, and `minstret`/`mcycle`;
- reviewed PC candidate schema;
- reviewed integer register file schema for x1 through x31 with x0 implicit
  zero;
- reviewed `lmem`/`imem` staging schema;
- reviewed ICCM/DCCM 4-bank `ram_core` fields with 4096 rows and 39-bit
  ECC-packed words;
- reviewed ECC packing markers through `riscv_ecc32`, `slam_dccm_ram`, and
  `slam_iccm_ram`;
- reviewed GPU state-image initialization order and sections for control
  scalars, host-only staging memories, and derived ICCM/DCCM banks.
- reviewed RTLMeter stdout/cycles compare binding from mailbox stdout and
  `mcycle`/`minstret` markers to the normalized RTLMeter observable files.

Remaining blockers:

- `gpu_state_image_materializer` before materialization is run;
- `reviewed_veer_el2_sidecar_executable` before the bridge can execute.

This is now an automatic "not ready yet"判定 for VeeR-EL2 GPU usefulness. The
program/preload identity blocker has been reduced to a sha256 check against the
reviewed VeeR-EL2 `hello` program, and the stdout/pass-fail observable source
is detected from generated C++ expressions even though `mailbox_data` is not a
stable root field. The PC/GPR schema blocker, explicit ICCM/DCCM bank/ECC
layout blocker, GPU state-image initialization schema blocker, and RTLMeter
stdout/cycles compare-binding blocker have been reduced to authority schema
checks against the generated root header and generated C++/testbench markers.
The next useful implementation step is to produce or link a reviewed VeeR-EL2
sidecar executable that consumes the extracted state image and emits the bound
RTLMeter observable files through the direct bridge.

The third FC-064 slice adds a materializer for the reviewed extracted
state-image schema:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  materialize-veer-el2-state-image --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --rtlmeter-program-hex artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/VeeR-EL2/default/execute-0/hello/program.hex \
  --state-image-out artifacts/veer_el2_direct_verilator_sidecar_probe/veer_el2_extracted_state_image.json \
  --summary-out reports/rtlmeter_veer_el2_state_image_materializer.json
```

Result:

- `state_image_materialized=true`
- `state_image_path=artifacts/veer_el2_direct_verilator_sidecar_probe/veer_el2_extracted_state_image.json`
- `state_image_program_byte_count=383`
- `state_image_dccm_preload_active=false`
- `state_image_iccm_preload_active=false`
- `state_image_dccm_nonzero_entry_count=0`
- `state_image_iccm_nonzero_entry_count=0`
- `missing_build_context=["veer_el2_sidecar_execution_bridge"]`
- `gpu_execution_claimed=false`
- `speedup_claimed=false`

For the current `hello` program, the ICCM/DCCM preload sentinels are absent, so
the materialized image contains program staging sections and empty derived bank
sections. The RTLMeter stdout/cycles compare binding is reviewed as a
non-executing schema, but this is still not GPU execution or usefulness
evidence.

The fourth FC-064 slice adds the direct observable bridge command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  run-veer-el2-sidecar-bridge --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --state-image artifacts/veer_el2_direct_verilator_sidecar_probe/veer_el2_extracted_state_image.json \
  --cpu-execute-dir artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/VeeR-EL2/default/execute-0/hello \
  --sidecar-execute-dir artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/hello \
  --summary-out reports/rtlmeter_veer_el2_sidecar_bridge.json
```

Historical fourth-slice result before flat program-staging lowering:

- `status=verilator_native_sidecar_blocked_veer_el2_gpu_state_image_launch`
- `state_image_loaded=true`
- `gpu_state_image_launch_review.prelaunch_rejection_required=true`
- `gpu_state_image_launch_review.unsafe_syms_gep_covered_by_state_image=false`
- `gpu_state_image_launch_review.unsafe_syms_gep_count=1085`
- `gpu_state_image_launch_review.nonflat_assoc_array_detected=true`
- `gpu_state_image_launch_review.assoc_array_gpu_lowering_supported=false`
- `gpu_state_image_launch_review.nonflat_assoc_array_markers=["VlAssocArray", "std::_Rb_tree", "_Rb_tree", "class.std::map"]`
- `gpu_state_image_launch_review.root_state_image_field_offset_review.reviewed=true`
- `gpu_state_image_launch_review.root_state_image_field_offset_review.mapped_field_count=50`
- `gpu_state_image_launch_review.root_state_image_materializer_review.reviewed=false`
- `gpu_state_image_launch_review.root_state_image_materializer_review.gpu_ir_assoc_array_map_detected=true`
- `gpu_state_image_launch_review.root_state_image_materializer_review.materializable_sections=["control_scalars", "dccm_banks", "iccm_banks"]`
- `gpu_state_image_launch_review.root_state_image_materializer_review.blocked_sections=["program_staging_lmem", "program_staging_imem"]`
- `gpu_state_image_launch_review.root_state_image_materializer_review.missing_build_context=["veer_el2_program_staging_assoc_array_gpu_lowering"]`
- `program_staging_lmem.entry_count=383`
- `program_staging_lmem.host_assoc_array_initializer_ready=true`
- `program_staging_lmem.blocked_by_gpu_assoc_array_lowering=true`
- `program_staging_imem.entry_count=383`
- `program_staging_imem.host_assoc_array_initializer_ready=true`
- `program_staging_imem.blocked_by_gpu_assoc_array_lowering=true`
- `sidecar_bridge_invoked=false`
- `sidecar_observables_ready=false`
- `missing_build_context=["veer_el2_gpu_root_state_image_prelaunch_rejection", "veer_el2_gpu_unsafe_syms_gep_coverage", "veer_el2_program_staging_assoc_array_gpu_lowering", "veer_el2_gpu_root_state_image_materializer", "reviewed_veer_el2_sidecar_executable"]`
- `gpu_execution_claimed=false`
- `speedup_claimed=false`

The bridge intentionally refuses to copy CPU observables into the sidecar output.
It only compares after a reviewed sidecar executable emits `_execute/stdout.log`
and `_rtlmeter_cycles.txt` into the sidecar execute dir.

The fifth FC-064 slice tightened the executable review gate and exercised the
native make path with the correct repo root:

```sh
RTLMETER_REPO_ROOT=$PWD make -C artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir -f Vsim.mk Vsim
```

Observed result:

- `build_vl_gpu` completes for the VeeR obj_dir;
- `vl_batch_gpu.cubin` is produced;
- `storage_size=300352`;
- `gpu_artifact_build_passed=true`;
- `gpu_artifact_supported_for_direct_shim=true`;
- `status=verilator_native_sidecar_blocked_veer_el2_gpu_state_image_launch`;
- `gpu_state_image_launch_review.prelaunch_rejection_required=true`;
- `gpu_state_image_launch_review.unsafe_syms_gep_covered_by_state_image=false`;
- `gpu_state_image_launch_review.unsafe_syms_gep_count=1085`;
- `gpu_state_image_launch_review.root_state_image_field_offset_review.reviewed=true`;
- `gpu_state_image_launch_review.root_state_image_field_offset_review.mapped_field_count=50`;
- `missing_build_context=["veer_el2_gpu_root_state_image_prelaunch_rejection", "veer_el2_gpu_unsafe_syms_gep_coverage", "veer_el2_gpu_root_state_image_materializer", "reviewed_veer_el2_sidecar_executable"]`.

At this fifth-slice checkpoint, the blocker was no longer source closure, extracted
state-image emission, stdout/cycles binding, GPU artifact generation, or root
offset discovery. The next gap is earlier than the executable: the generated
GPU artifact is a `root_image` artifact whose metadata still requires prelaunch
rejection because unsafe `%vlSymsp`-relative accesses were not covered by that
slice's extracted state image. The bridge/build report mapped 50 required
VeeR root fields from the generated layout at that checkpoint, including PC candidates, GPR 1..31,
ICCM/DCCM banks, control inputs, and stdout/cycle observables. The bridge
materializer review says control scalars and inactive ICCM/DCCM bank sections
can be byte-materialized from the mapped offsets. The 383-byte
`program_staging_lmem` and `program_staging_imem` sections also have valid host
assoc-array initializers for Verilated `VlAssocArray<IData,CData>` fields, but
the generated GPU IR still contains `VlAssocArray` / `std::map` / `_Rb_tree`
for those memories. The VeeR GPU artifact metadata now records this directly as
`nonflat_assoc_array_detected=true` and
`assoc_array_gpu_lowering_supported=false`. The next implementation task is
therefore not a plain host initializer: lower program-staging assoc arrays to a
device-suitable
flat/byte-addressable memory representation, then clear unsafe `%vlSymsp`
coverage so the extracted semantic preload image can initialize the 300352-byte
root image. Only after that should a reviewed VeeR
executable/runtime binding consume `VEER_EL2_SIDECAR_STATE_IMAGE`, emit sidecar
RTLMeter observables under `VEER_EL2_SIDECAR_EXECUTE_DIR`, and carry a
`veer_el2_sidecar_executable_review` manifest. The existing direct shim remains
PULP-init-state specific and must not be treated as the VeeR observable
executable.

The sixth FC-064 slice lowered the two VeeR program-staging memories into a
generated flat byte-window representation before GPU IR emission. This slice is
now superseded by the seventh syms-state-image slice below, but remains as the
audit record for the program-memory blocker:

- `tb_top__DOT__imem__DOT__mem` and `tb_top__DOT__lmem__DOT__mem` are rewritten
  from scoped `VlAssocArray<IData,CData>` fields to
  `VlGpuFlatByteMem<0x80000000U, 65536U>`.
- The patch report is
  `artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir/vl_gpu_veer_el2_flat_program_mem_patch.json`.
- The VeeR GPU build now emits `vl_batch_gpu.ptx`, `storage_size=431296`.
- Optimized metadata records `nonflat_assoc_array_detected=false` and
  `assoc_array_gpu_lowering_supported=true`.
- Residual `_Rb_tree` markers are still present in optimized LLVM IR, but they
  are `std::multimap<unsigned long,VlCoroutineHandle>` scheduler state rather
  than program-memory `VlAssocArray` / `std::map<unsigned int,unsigned char>`.
- `unsafe_syms_gep_count` dropped from `1085` to `341`, but
  `unsafe_syms_gep_covered_by_state_image=false` and
  `prelaunch_rejection_required=true` remain.
- The bridge materializer review now has `reviewed=true`; it accepts
  `control_scalars`, `dccm_banks`, `iccm_banks`, `program_staging_lmem`, and
  `program_staging_imem` as materializable sections.
- The bridge still fails closed with
  `missing_build_context=["veer_el2_gpu_root_state_image_prelaunch_rejection",
  "veer_el2_gpu_unsafe_syms_gep_coverage",
  "reviewed_veer_el2_sidecar_executable"]`.

At the end of the sixth slice, the next implementation task was unsafe
`%vlSymsp` coverage and prelaunch rejection, not program-staging assoc-array
lowering. The seventh slice below clears that blocker in metadata. GPU
execution, RTLMeter correctness, timing, speedup, and usefulness are still
unmeasured.

The seventh FC-064 slice adds automatic syms-state-image rebuild for VeeR-EL2
GPU artifact prep when the first root-image build reports uncovered `%vlSymsp`
accesses:

- `build-direct-shim-smoke` now records `gpu_artifact_build_review.mode=
  veer_el2_auto_syms_state_image_build`.
- The real VeeR build first observes `state_image_kind=root_image`,
  `unsafe_syms_gep_covered_by_state_image=false`, and
  `prelaunch_rejection_required=true`, then rebuilds with
  `--syms-state-image --syms-storage-size 433472 --state-root-offset 192`.
- The final artifact is `vl_batch_gpu.cubin`, `storage_size=433472`, with
  `state_image_kind=verilator_syms_image`,
  `unsafe_syms_gep_covered_by_state_image=true`, and
  `prelaunch_rejection_required=false`.
- Program staging remains flat:
  `nonflat_assoc_array_detected=false` and
  `assoc_array_gpu_lowering_supported=true`.
- The bridge and build reports now fail closed only on
  `missing_build_context=["reviewed_veer_el2_sidecar_executable"]`.

The next implementation task is the reviewed state-image-consuming VeeR sidecar
executable that emits RTLMeter stdout/cycles observables. Correctness compare,
timing, speedup, and GPU usefulness remain unmeasured until that executable
actually runs and produces sidecar observables.

The eighth FC-064 slice adds the reviewed executable and moves the blocker to
stdout/cycles equivalence:

- `src/tools/veer_el2_sidecar_executable.py` has a
  `veer_el2_sidecar_executable_review` manifest.
- The executable consumes `VEER_EL2_SIDECAR_STATE_IMAGE`, materializes a
  syms-state init image from the extracted preload JSON, invokes
  `src/tools/run_vl_hybrid.py` against the generated VeeR `obj_dir`, dumps GPU
  state, and writes sidecar `_execute/stdout.log` plus
  `_rtlmeter_cycles.txt`.
- It records `cpu_observables_copied=false` and does not read the CPU execute
  directory.
- The bridge now reports `sidecar_executable_review.reviewed=true`,
  `sidecar_bridge_invoked=true`, and `sidecar_observables_ready=true`.
- The initial real comparison failed with
  `missing_build_context=["rtlmeter_stdout_cycles_equivalence"]`,
  `cpu_cycles=2229`, and `gpu_cycles=0`.

The ninth FC-064 slice adds enough VeeR-specific state initialization and
clock/reset driving to reach architectural progress on GPU:

- The root state offset review now maps 52 required fields, including
  `tb_top__DOT__reset_vector` at root offset `5456` and
  `tb_top__DOT__nmi_vector` at root offset `5460`.
- The sidecar syms-state materializer writes `reset_vector=0x80000000` and
  `nmi_vector=0xee000000`, stages both 383-byte flat program memories, and
  emits a clock/reset patch script.
- The default GPU sidecar run uses 727 VeeR clock cycles. The final GPU state
  reaches `mcycle=726`, `minstret=330`, `mailbox_write=1`, `obuf_data=0xff`,
  and `finish_marker_observed=true`, matching the architectural counters
  printed in the CPU stdout.
- The bridge passes stdout/cycles equivalence. The GPU mailbox trace
  reconstructs normalized stdout to match the CPU reference, and the sidecar
  `_rtlmeter_cycles.txt` uses RTLMeter's `tb_top.core_clk` count rather than the
  VeeR architectural `mcycle`.

The next implementation task is CPU vs sidecar timing/usefulness measurement.
Timing, speedup, and usefulness remain unmeasured until that measurement gate
runs.

## Scope

- Define a reviewed source closure for exactly `VeeR-EL2:default` first.
- Define top/filelist recognition for the RTLMeter-generated VeeR-EL2 case
  (`tb_top` plus the generated filelist), and fail closed if it does not match.
- Pin RTLMeter-generated provenance for the accepted case: top module, source
  file order, include/define set, `default` config, and the program/test
  identity used for preload.
- Identify the design-CPU state layout boundaries needed for a sidecar plan:
  PC/register state, relevant core state, ICCM/DCCM/preloaded program memory,
  reset/clock inputs, and the stdout/cycle observables used by RTLMeter.
- Decide whether the sidecar can operate on a full Verilator state image or
  needs an explicit extracted memory/state layout. Record a named blocker class
  if the layout cannot be supported safely.
- Define observable equivalence for VeeR-EL2: stdout normalization, RTLMeter
  cycle source, pass/fail marker handling, and whether memory/register end
  state is excluded or required.
- Extend the authority registry or known-closure mapping only after tests pin
  the exact accepted and rejected target shapes.
- Add focused tests for VeeR-EL2 recognition pass/fail behavior and for
  rejecting arbitrary filelists or unrelated CPU-core designs.
- Re-run the GPU-side VeeR-EL2 probe only after source closure and known
  closure pass.

## Acceptance

- A target-specific VeeR-EL2 closure registry or authority entry exists, or the
  issue records a reviewed reason why it cannot exist yet.
- The known-closure recognizer accepts only the reviewed VeeR-EL2
  filelist/top/source shape and rejects modified, missing, or unrelated
  filelists.
- The recognizer rejects modified program hex/preload arguments and
  non-`default` VeeR-EL2 config variants such as `hiperf` or `asic` unless a
  later issue explicitly admits them.
- The state layout and program preload memory mapping are either captured as a
  concrete extracted layout schema for sidecar build planning, or explicitly
  blocked with a named reason.
- Observable equivalence for VeeR-EL2 is defined before any compare result is
  accepted.
- The reviewed VeeR sidecar bridge reconstructs the GPU stdout character stream
  and aligns the RTLMeter cycles-source contract so stdout/cycles equivalence
  passes without copying CPU observables.
- The RTLMeter wrapper path can reach the native sidecar make hook for VeeR-EL2
  without the current source-closure authority failure.
- If GPU build/run is not implemented yet, the result still fails closed with
  `cpu_as_gpu_fallback=false` and `gpu_execution_claimed=false`.
- No GPU speedup, usefulness, arbitrary RTLMeter, or arbitrary CPU-core support
  claim is made from this issue alone.

## Validation

Required:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_verilator_native_known_closure -q
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/check_staged_large_files.py
```

Add focused VeeR-EL2 closure tests when the recognizer or registry changes.
After implementation, run one real VeeR-EL2 direct-native RTLMeter probe and
record whether the blocker moves explicitly from source closure to state
layout, build, runtime, or stdout/cycles compare.

## Non-Goals

- No arbitrary RTLMeter CPU-core support.
- No GPU execution claim until artifact load, kernel launch, and required
  observables are actually recorded.
- No speedup or usefulness claim.
- No second seed broadening.
- No proxy/marker-lane evidence revival.
