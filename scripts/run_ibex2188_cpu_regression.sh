#!/usr/bin/env bash
# Build and run the directed local RTL regression for Ibex issue #2188.
set -euo pipefail

bad_checkout=''
fixed_checkout=''
out_dir=''
verilator_bin='verilator'

while (($#)); do
  case "$1" in
    --bad-checkout) bad_checkout=$2; shift 2 ;;
    --fixed-checkout) fixed_checkout=$2; shift 2 ;;
    --out) out_dir=$2; shift 2 ;;
    --verilator) verilator_bin=$2; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z $bad_checkout || -z $fixed_checkout || -z $out_dir ]]; then
  echo 'required: --bad-checkout --fixed-checkout --out' >&2
  exit 2
fi
if [[ -e $out_dir ]]; then
  echo "output path already exists: $out_dir" >&2
  exit 2
fi

readonly bad_revision=668233699df9ec2a40413e69e0de0a5b10185980
readonly fixed_revision=9e4a950aa6aa0e20eb638aeeb78743d4a9ddaaeb
readonly repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly testbench="$repo_root/examples/ibex2188/ibex2188_ecc_temporal_tb.sv"

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
  local build_dir="$out_dir/build-$label"
  local primitive_dir="$checkout/vendor/lowrisc_ip/ip/prim/rtl"
  local generic_dir="$checkout/vendor/lowrisc_ip/ip/prim_generic/rtl"
  local dv_utils_dir="$checkout/vendor/lowrisc_ip/dv/sv/dv_utils"
  local -a primitive_sources core_rtl command
  local source

  require_revision "$checkout" "$expected" "$label"
  mapfile -d '' -t primitive_sources < <(
    find "$primitive_dir" -maxdepth 1 -type f -name '*.sv' \
      ! -name 'prim_lc_*' ! -name 'prim_mubi_pkg.sv' ! -name 'prim_secded_pkg.sv' \
      -print0 | sort -z
  )
  mapfile -d '' -t core_rtl < <(core_sources "$checkout")
  for source in "${primitive_sources[@]}" "${core_rtl[@]}"; do
    [[ -f $source ]] || { echo "missing source: $source" >&2; exit 2; }
  done

  command=(
    "$verilator_bin" --binary --timing --top-module ibex2188_ecc_temporal_tb
    -DSYNTHESIS -Wno-fatal -Mdir "$build_dir"
    "-I$checkout/rtl" "-I$primitive_dir" "-I$dv_utils_dir"
    "$primitive_dir/prim_mubi_pkg.sv" "$primitive_dir/prim_secded_pkg.sv"
    "$checkout/rtl/ibex_pkg.sv" "$generic_dir/prim_generic_buf.sv"
    "$generic_dir/prim_generic_clock_gating.sv"
    "${primitive_sources[@]}" "${core_rtl[@]}" "$testbench"
  )
  "${command[@]}" >"$out_dir/$label-build.log" 2>&1
  "$build_dir/Vibex2188_ecc_temporal_tb" +fault-bit=0 \
    >"$out_dir/$label-run.log" 2>&1
  grep '^IBEX2188_RESULT ' "$out_dir/$label-run.log" | tail -n 1
}

mkdir "$out_dir"
bad_result=$(run_revision bad "$bad_checkout" "$bad_revision")
fixed_result=$(run_revision fixed "$fixed_checkout" "$fixed_revision")

[[ $bad_result == *'fault_seen=1 alert_seen=0 oracle_violation=1'* ]] || {
  echo "bad revision did not reproduce the expected #2188 oracle violation" >&2; exit 1;
}
[[ $fixed_result == *'fault_seen=1 alert_seen=1 oracle_violation=0'* ]] || {
  echo "fixed revision did not clear the expected #2188 oracle violation" >&2; exit 1;
}

field() {
  local line=$1 key=$2
  local pair
  for pair in $line; do
    [[ $pair == "$key="* ]] && { printf '%s' "${pair#*=}"; return 0; }
  done
  echo "missing $key in runner result" >&2
  return 1
}

bad_rf_read_enable=$(field "$bad_result" rf_read_enable)
bad_rf_wb_match=$(field "$bad_result" rf_wb_match)
bad_rf_write_wb=$(field "$bad_result" rf_write_wb)
bad_rf_ecc_error_id=$(field "$bad_result" rf_ecc_error_id)
bad_instruction_valid_id=$(field "$bad_result" instruction_valid_id)
bad_alert_major_internal=$(field "$bad_result" alert_major_internal)
fixed_rf_read_enable=$(field "$fixed_result" rf_read_enable)
fixed_rf_wb_match=$(field "$fixed_result" rf_wb_match)
fixed_rf_write_wb=$(field "$fixed_result" rf_write_wb)
fixed_rf_ecc_error_id=$(field "$fixed_result" rf_ecc_error_id)
fixed_instruction_valid_id=$(field "$fixed_result" instruction_valid_id)
fixed_alert_major_internal=$(field "$fixed_result" alert_major_internal)

printf '%s\n' '{' \
  '  "schema_version": 1,' \
  '  "surface": "ibex2188_cpu_regression_observations",' \
  '  "status": "pass",' \
  '  "target_id": "ibex2188",' \
  "  \"bad_revision\": \"$bad_revision\", " \
  "  \"fixed_revision\": \"$fixed_revision\", " \
  '  "checkpoint_identity": "directed_load_dependent_branch_one_cycle_response_v1",' \
  '  "oracle_identity": "ibex2188.ecc_read_error_requires_major_alert_when_no_wb_forwarding.v1",' \
  '  "fault_port": "a",' \
  '  "fault_bit": 0,' \
  '  "revisions": {' \
  '    "bad": {' \
  '      "oracle_violation": 1,' \
  "      \"semantic\": {\"rf_read_enable\": $bad_rf_read_enable, \"rf_wb_match\": $bad_rf_wb_match, \"rf_write_wb\": $bad_rf_write_wb, \"rf_ecc_error_id\": $bad_rf_ecc_error_id, \"instruction_valid_id\": $bad_instruction_valid_id, \"alert_major_internal\": $bad_alert_major_internal}" \
  '    },' \
  '    "fixed": {' \
  '      "oracle_violation": 0,' \
  "      \"semantic\": {\"rf_read_enable\": $fixed_rf_read_enable, \"rf_wb_match\": $fixed_rf_wb_match, \"rf_write_wb\": $fixed_rf_write_wb, \"rf_ecc_error_id\": $fixed_rf_ecc_error_id, \"instruction_valid_id\": $fixed_instruction_valid_id, \"alert_major_internal\": $fixed_alert_major_internal}" \
  '    }' \
  '  }' \
  '}' >"$out_dir/runner_observations.json"

printf '%s\n' "$bad_result" "$fixed_result"
