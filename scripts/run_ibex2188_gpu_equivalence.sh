#!/usr/bin/env bash
# Build and run the directed local GPU equivalence for Ibex issue #2188.
#
# Mirrors scripts/run_ibex2188_cpu_regression.sh but uses the device-clean
# GPU testbench and the GPU sidecar pipeline (build_vl_gpu.py + run_vl_hybrid.py).
# Produces, per revision and delay, a CPU state image and a GPU state image and
# compares the declared semantic observables.
set -euo pipefail

bad_checkout=''
fixed_checkout=''
out_dir=''
verilator_bin='verilator'
load_response_delay=1
expect_bad_oracle=1
expect_fixed_oracle=0
sm='sm_89'
fault_bit=0

while (($#)); do
  case "$1" in
    --bad-checkout) bad_checkout=$2; shift 2 ;;
    --fixed-checkout) fixed_checkout=$2; shift 2 ;;
    --out) out_dir=$2; shift 2 ;;
    --verilator) verilator_bin=$2; shift 2 ;;
    --load-response-delay) load_response_delay=$2; shift 2 ;;
    --expect-bad-oracle) expect_bad_oracle=$2; shift 2 ;;
    --expect-fixed-oracle) expect_fixed_oracle=$2; shift 2 ;;
    --sm) sm=$2; shift 2 ;;
    --fault-bit) fault_bit=$2; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z $bad_checkout || -z $fixed_checkout || -z $out_dir ]]; then
  echo 'required: --bad-checkout --fixed-checkout --out' >&2
  exit 2
fi
if [[ $load_response_delay != 0 && $load_response_delay != 1 ]]; then
  echo 'load response delay must be 0 or 1' >&2
  exit 2
fi
if [[ -e $out_dir ]]; then
  echo "output path already exists: $out_dir" >&2
  exit 2
fi

readonly bad_revision=668233699df9ec2a40413e69e0de0a5b10185980
readonly fixed_revision=9e4a950aa6aa0e20eb638aeeb78743d4a9ddaaeb
readonly repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly gpu_tb="$repo_root/examples/ibex2188/ibex2188_ecc_temporal_gpu_tb.sv"
readonly cpu_driver="$repo_root/examples/ibex2188/ibex2188_ecc_temporal_gpu_driver.cpp"
readonly verilator_root="${VERILATOR_ROOT:-$(verilator --getenv VERILATOR_ROOT)}"
readonly hybrid="${HYBRID_RUNNER:-$repo_root/src/tools/run_vl_hybrid.py}"
readonly build_gpu="${BUILD_VL_GPU:-$repo_root/src/tools/build_vl_gpu.py}"

require_revision() {
  local checkout=$1 expected=$2 label=$3
  [[ -d $checkout/.git || -f $checkout/.git ]] || {
    echo "$label checkout is not a Git worktree: $checkout" >&2; exit 2;
  }
  [[ $(git -C "$checkout" rev-parse HEAD) == "$expected" ]] || {
    echo "$label checkout is not the pinned revision" >&2; exit 2;
  }
}

core_sources() {
  local checkout=$1
  printf '%s\0' \
    "$checkout/rtl/ibex_alu.sv" \
    "$checkout/rtl/ibex_branch_predict.sv" \
    "$checkout/rtl/ibex_compressed_decoder.sv" \
    "$checkout/rtl/ibex_controller.sv" \
    "$checkout/rtl/ibex_cs_registers.sv" \
    "$checkout/rtl/ibex_csr.sv" \
    "$checkout/rtl/ibex_counter.sv" \
    "$checkout/rtl/ibex_decoder.sv" \
    "$checkout/rtl/ibex_ex_block.sv" \
    "$checkout/rtl/ibex_fetch_fifo.sv" \
    "$checkout/rtl/ibex_id_stage.sv" \
    "$checkout/rtl/ibex_if_stage.sv" \
    "$checkout/rtl/ibex_load_store_unit.sv" \
    "$checkout/rtl/ibex_multdiv_fast.sv" \
    "$checkout/rtl/ibex_multdiv_slow.sv" \
    "$checkout/rtl/ibex_prefetch_buffer.sv" \
    "$checkout/rtl/ibex_pmp.sv" \
    "$checkout/rtl/ibex_wb_stage.sv" \
    "$checkout/rtl/ibex_dummy_instr.sv" \
    "$checkout/rtl/ibex_icache.sv" \
    "$checkout/rtl/ibex_core.sv"
}

run_revision() {
  local label=$1 checkout=$2 expected=$3
  local rev_out="$out_dir/$label"
  local gpu_mdir="$rev_out/gpu_obj"
  local cpu_mdir="$rev_out/cpu_obj"
  local primitive_dir="$checkout/vendor/lowrisc_ip/ip/prim/rtl"
  local generic_dir="$checkout/vendor/lowrisc_ip/ip/prim_generic/rtl"
  local dv_utils_dir="$checkout/vendor/lowrisc_ip/dv/sv/dv_utils"
  local -a primitive_sources core_rtl command
  local source

  require_revision "$checkout" "$expected" "$label"
  mkdir -p "$rev_out"
  mapfile -d '' -t primitive_sources < <(
    find "$primitive_dir" -maxdepth 1 -type f -name '*.sv' \
      ! -name 'prim_lc_*' ! -name 'prim_mubi_pkg.sv' ! -name 'prim_secded_pkg.sv' \
      -print0 | sort -z
  )
  mapfile -d '' -t core_rtl < <(core_sources "$checkout")
  for source in "${primitive_sources[@]}" "${core_rtl[@]}"; do
    [[ -f $source ]] || { echo "missing source: $source" >&2; exit 2; }
  done

  export VERILATOR_ROOT="$verilator_root"
  export PYTHONPATH="$repo_root/src/tools"

  local base=( "$verilator_bin" --cc -Wno-fatal --public-flat-rw -DSYNTHESIS
               --top-module ibex2188_ecc_temporal_gpu_tb
               "-I$checkout/rtl" "-I$primitive_dir" "-I$dv_utils_dir"
               "$primitive_dir/prim_mubi_pkg.sv" "$primitive_dir/prim_secded_pkg.sv"
               "$checkout/rtl/ibex_pkg.sv" "$generic_dir/prim_generic_buf.sv"
               "$generic_dir/prim_generic_clock_gating.sv"
               "${primitive_sources[@]}" "${core_rtl[@]}" "$gpu_tb" )

  "${base[@]}" "--Mdir" "$gpu_mdir" >"$rev_out/gpu-build.log" 2>&1
  "${base[@]}" "--exe" "$cpu_driver" "--build" "--Mdir" "$cpu_mdir" >"$rev_out/cpu-build.log" 2>&1

  python3 "$build_gpu" "$gpu_mdir" --sm "$sm" --force >"$rev_out/gpu-cubin.log" 2>&1

  local cpu_state="$rev_out/delay${load_response_delay}.cpu.bin"
  local gpu_state="$rev_out/delay${load_response_delay}.gpu.bin"
  local patch="$rev_out/delay${load_response_delay}.patch"

  "$cpu_mdir/Vibex2188_ecc_temporal_gpu_tb" \
    --load-response-delay "$load_response_delay" --fault-bit "$fault_bit" \
    --dump-state "$cpu_state" >"$rev_out/cpu-run.log" 2>&1

  python3 - "$patch" "$load_response_delay" <<'PY'
import sys
from pathlib import Path
offsets = {
    "clk_i": 104, "rst_ni": 105, "fault_enable_i": 106,
    "inject_port_b_i": 107, "fault_bit_i": 108, "load_response_delay_i": 109,
}
def line(**values):
    return " ".join(f"{offsets[k]}:{v}" for k, v in values.items())
patch_path, delay = sys.argv[1], int(sys.argv[2])
lines = [line(clk_i=0, rst_ni=0, fault_enable_i=1, inject_port_b_i=0,
              fault_bit_i=0, load_response_delay_i=delay)]
for cyc in range(11):
    lines.append(line(clk_i=1, rst_ni=1 if cyc >= 2 else 0))
    lines.append(line(clk_i=0, rst_ni=1 if cyc >= 2 else 0))
Path(patch_path).write_text("\n".join(lines) + "\n")
PY

  python3 "$hybrid" --mdir "$gpu_mdir" --nstates 1 --resident-steps \
    --patch-script "$patch" --dump-state "$gpu_state" >"$rev_out/gpu-run.log" 2>&1

  python3 - "$rev_out" "$load_response_delay" <<'PY'
import json, sys
from pathlib import Path
rev_out = Path(sys.argv[1])
delay = int(sys.argv[2])
ports = {
    "done": 110, "oracle_violation": 111, "fault_seen": 112, "alert_seen": 113,
    "rf_read_enable": 114, "rf_wb_match": 115, "rf_write_wb": 116,
    "rf_ecc_error_id": 117, "instruction_valid_id": 118, "alert_major_internal": 119,
}
def read(path):
    image = path.read_bytes()
    return {name: image[off] for name, off in ports.items()}
cpu = read(rev_out / f"delay{delay}.cpu.bin")
gpu = read(rev_out / f"delay{delay}.gpu.bin")
match = cpu == gpu
print(json.dumps({"cpu": cpu, "gpu": gpu, "match": match}, indent=2))
if not match:
    raise SystemExit(1)
PY
}

mkdir "$out_dir"
bad_report=$(run_revision bad "$bad_checkout" "$bad_revision")
fixed_report=$(run_revision fixed "$fixed_checkout" "$fixed_revision")
echo "bad: $bad_report"
echo "fixed: $fixed_report"
echo "OK: CPU/GPU semantic observables match on both pinned revisions"
