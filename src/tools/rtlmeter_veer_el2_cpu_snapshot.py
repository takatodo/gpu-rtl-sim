#!/usr/bin/env python3
"""Bounded VeeR-EL2 RTLMeter CPU snapshot runner for same-cycle comparison."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path


SURFACE = "rtlmeter_veer_el2_cpu_snapshot"
OPT_IN_ENV = "RTLMETER_VEER_EL2_CPU_SNAPSHOT_EXECUTE"
DEFAULT_COMPILE_ROOT = "artifacts/design_cpu_state_parallel_probe/veer_el2_serial"
DEFAULT_EXECUTE_DIR = (
    "artifacts/rtlmeter_cpu_dhry_serial_baseline/serial/veer_el2_default_dhry/"
    "VeeR-EL2/default/execute-0/dhry"
)
DEFAULT_ARTIFACT_ROOT = "artifacts/rtlmeter_veer_el2_cpu_snapshot"
DEFAULT_REPORT = "reports/rtlmeter_veer_el2_cpu_snapshot.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _display_path(path: str | Path, repo_root: Path) -> str:
    p = Path(path)
    try:
        return p.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>"


def _report_arg_path(path: str | Path, repo_root: Path) -> str:
    p = Path(path)
    if p.is_absolute():
        return _display_path(p, repo_root)
    if ".." in p.parts:
        return "<local-relative-parent-path>"
    return p.as_posix()


def _sanitize_report_value(value: object, repo_root: Path) -> object:
    if isinstance(value, str):
        if value.startswith("-I"):
            return "-I" + str(_sanitize_report_value(value[2:], repo_root))
        root_text = repo_root.resolve().as_posix()
        if value.startswith(root_text + "/"):
            return value.replace(root_text + "/", "")
        if value == root_text:
            return "."
        if value.startswith("/"):
            return "<local-absolute-path>"
        return value
    if isinstance(value, list):
        return [_sanitize_report_value(item, repo_root) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_report_value(item, repo_root) for key, item in value.items()}
    return value


def _extract_snapshot_json(stdout: str) -> dict[str, object] | None:
    decoder = json.JSONDecoder()
    marker = '"surface":"rtlmeter_veer_el2_cpu_snapshot.executable"'
    for marker_index in reversed([i for i in range(len(stdout)) if stdout.startswith(marker, i)]):
        start = stdout.rfind("{", 0, marker_index)
        if start < 0:
            continue
        try:
            loaded, _ = decoder.raw_decode(stdout[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, Mapping):
            return dict(loaded)
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(loaded, Mapping):
                return dict(loaded)
    return None


def _validated_output_path(path: str | Path, *, required_root: str, default: str) -> tuple[str, list[str]]:
    candidate = Path(str(path))
    errors: list[str] = []
    if candidate.is_absolute():
        errors.append(f"{required_root}_path.absolute")
    if ".." in candidate.parts:
        errors.append(f"{required_root}_path.parent_reference")
    if not candidate.parts or candidate.parts[0] != required_root:
        errors.append(f"{required_root}_path.outside_{required_root}")
    return (default if errors else str(path), errors)


def obj_dir_from_compile_root(compile_root: str | Path, *, repo_root: Path) -> Path:
    path = Path(compile_root)
    if not path.is_absolute():
        path = repo_root / path
    return path / "VeeR-EL2" / "default" / "compile-0" / "obj_dir"


def cpu_snapshot_source() -> str:
    return r'''#include "Vsim.h"
#include "Vsim___024root.h"
#include "verilated.h"

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

static uint32_t read_mcycle(Vsim___024root* root) {
    return root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__mcyclel;
}

static uint32_t read_minstret(Vsim___024root* root) {
    return root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__minstretl;
}

static uint32_t read_pc_raw(Vsim___024root* root) {
    return root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__i0_pc_r_ff__dout;
}

static uint32_t read_pc_d(Vsim___024root* root) {
    return root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d;
}

static uint32_t read_i0_pc_r_ff_din(Vsim___024root* root) {
    return root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_pc_r_ff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din;
}

static uint32_t read_dec_i0_instr_d(Vsim___024root* root) {
    return root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_i0_instr_d;
}

static uint8_t read_mailbox_write(Vsim___024root* root) {
    return root->tb_top__DOT__mailbox_write;
}

static uint64_t read_obuf_data(Vsim___024root* root) {
    return root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__lsu__DOT__bus_intf__DOT__bus_buffer__DOT__obuf_data;
}

static uint64_t parse_u64(const char* value, uint64_t fallback) {
    if (value == nullptr || *value == '\0') return fallback;
    char* end = nullptr;
    const uint64_t parsed = std::strtoull(value, &end, 0);
    return (end != value && *end == '\0') ? parsed : fallback;
}

struct TraceRow {
    uint64_t post_reset_posedges;
    uint64_t time;
    uint32_t mcycle;
    uint32_t minstret;
    uint32_t pc;
    uint32_t pc_d;
    uint32_t i0_pc_r_ff_din;
    uint32_t dec_i0_instr_d;
    uint8_t dec_i0_branch_d;
    uint8_t dec_i0_decode_d;
    uint8_t dec_decode_valid_gate;
    uint8_t dec_ib0_valid_d;
    uint8_t dec_misc2ff_dout;
    uint8_t dec_i0_exublock_d;
    uint8_t dec_misc1ff_dout;
    uint32_t dec_halt_ff_dout;
    uint8_t dec_presync_stall;
    uint8_t dec_lsu_idle;
    uint8_t exu_div_valid_in;
    uint8_t exu_div_running_state;
    uint32_t exu_div_i_misc_ff;
    uint32_t exu_div_i_misc_ff_din;
    uint8_t exu_div_shortq;
    uint8_t exu_div_shortq_enable;
    uint32_t exu_div_quotient_raw;
    uint8_t exu_div_quotient_new;
    uint8_t exu_div_dw_shortq_raw;
    uint64_t exu_div_i_b_ff;
    uint64_t exu_div_i_b_ff_din;
    uint32_t exu_div_a_ff;
    uint32_t exu_div_q_ff;
    uint64_t exu_div_r_ff;
    uint8_t i0_brp_valid;
    uint8_t i0_predict_nt;
    uint8_t i0_predict_br;
    uint8_t dec_tlu_i0_valid_r;
    uint8_t i0_valid_no_ebreak_ecall_r;
    uint8_t dma_dccm_stall_any;
    uint8_t lsu_store_stall_any;
    uint8_t dec_lsu_valid_raw_d;
    uint8_t ifu_pmu_fetch_stall;
    uint8_t ifu_pmu_instr_aligned;
    uint16_t ifu_ifc_fbwrite_dout;
    uint8_t ifu_ifc_fetch_consume_gate;
    uint8_t dec_tlu_flush_err_r;
    uint8_t dma_iccm_stall_any;
    uint8_t ifu_mem_perr_state;
    uint8_t ifu_mem_err_stop_state;
    uint8_t exu_flush_final;
    uint8_t dec_tlu_flush_lower_r;
    uint32_t dec_tlu_flush_path_r;
    uint8_t tb_ifu_axi_rvalid;
    uint8_t tb_ifu_axi_rid;
    uint8_t tb_ifu_axi_rresp;
    uint64_t tb_ifu_axi_rdata;
    uint8_t tb_mux_axi_rvalid;
    uint64_t tb_sb_axi_rdata;
    uint8_t tb_lmem_axi_rvalid;
    uint64_t tb_lmem_axi_rdata;
    uint8_t tb_ifu_axi_arready;
    uint8_t ifu_bus_cmd_valid;
    uint8_t ifu_bus_rd_addr_count;
    uint32_t ifu_fetch_addr_f;
    uint32_t ifu_pmp_addr;
    uint8_t ifu_ifc_fetch_req_bf;
    uint8_t ifu_ifc_fb_write_ns;
    uint8_t ifu_ifc_miss_f;
    uint32_t ifu_mem_miss_f;
    uint8_t ifu_mem_miss_state;
    uint8_t ifu_mem_miss_state_en;
    uint8_t ifu_mem_write_ic_16_bytes;
    uint8_t ifu_mem_ic_act_miss_f;
    uint8_t ifu_ifc_fetch_ready;
    uint8_t ifu_ifc_ic_hit_f;
    uint32_t ifu_aln_aligndata;
    uint8_t ifu_aln_alignfromf1;
    uint8_t ifu_aln_brdata0_en;
    uint8_t ifu_aln_brdata1_en;
    uint8_t ifu_aln_brdata2_en;
    uint8_t ifu_aln_shift_f1_f0;
    uint8_t ifu_aln_shift_f2_f0;
    uint8_t ifu_aln_shift_f2_f1;
    uint8_t ifu_aln_sf0val;
    uint8_t ifu_aln_sf1val;
    uint8_t ifu_aln_bundle1;
    uint8_t ifu_aln_bundle2;
    uint8_t dec_tlu_flush_noredir_r;
    uint8_t ifu_ic_fetch_val_f;
    uint8_t ifu_iccm_rd_ecc_single_err;
    uint8_t ifu_ic_error_start;
    uint8_t dec_tlu_i0_commit_cmt;
    uint16_t dec_tlu_freeff_dout;
    uint16_t dec_tlu_freeff_din;
    uint8_t ifu_aln_fetch_to_f0;
    uint8_t ifu_aln_fetch_to_f1;
    uint8_t ifu_aln_fetch_to_f2;
    uint8_t ifu_aln_bundle1_din;
    uint8_t ifu_aln_bundle2_din;
    uint64_t root_act_triggered;
    uint64_t root_nba_triggered;
    uint8_t mailbox_write;
    uint64_t obuf_data;
};

int main(int argc, char** argv) {
    uint64_t target_mcycle = 0;
    uint64_t target_post_reset_cycles = 0;
    uint64_t trace_start_post_reset_cycles = 0;
    uint64_t trace_end_post_reset_cycles = 0;
    uint64_t max_time = 0;
    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        if (arg.rfind("+snapshot_mcycle=", 0) == 0) {
            target_mcycle = parse_u64(arg.c_str() + 17, 0);
        } else if (arg.rfind("+snapshot_post_reset_cycles=", 0) == 0) {
            target_post_reset_cycles = parse_u64(arg.c_str() + 28, 0);
        } else if (arg.rfind("+snapshot_trace_start_post_reset_cycles=", 0) == 0) {
            trace_start_post_reset_cycles = parse_u64(arg.c_str() + 40, 0);
        } else if (arg.rfind("+snapshot_trace_end_post_reset_cycles=", 0) == 0) {
            trace_end_post_reset_cycles = parse_u64(arg.c_str() + 38, 0);
        } else if (arg.rfind("+snapshot_max_time=", 0) == 0) {
            max_time = parse_u64(arg.c_str() + 19, 0);
        }
    }
    if (target_mcycle == 0 && target_post_reset_cycles == 0) {
        std::cerr << "missing +snapshot_mcycle=<positive integer> or +snapshot_post_reset_cycles=<positive integer>\n";
        return 2;
    }
    if (max_time == 0) {
        const uint64_t target = target_mcycle ? target_mcycle : target_post_reset_cycles;
        max_time = target * 20 + 10000;
    }

    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
    contextp->threads(1);
    contextp->commandArgs(argc, argv);
    const std::unique_ptr<Vsim> top{new Vsim{contextp.get(), ""}};
    Vsim___024root* root = top->rootp;

    bool reached_target = false;
    bool events_exhausted = false;
    bool reset_released_seen = false;
    uint8_t previous_core_clk = root->tb_top__DOT__core_clk;
    uint64_t post_reset_posedges = 0;
    std::vector<TraceRow> trace_rows;
    while (VL_LIKELY(!contextp->gotFinish())) {
        top->eval();
        const uint8_t core_clk = root->tb_top__DOT__core_clk;
        const bool reset_released = root->tb_top__DOT__rst_l && root->tb_top__DOT__porst_l;
        if (reset_released && !reset_released_seen) {
            reset_released_seen = true;
        }
        if (reset_released_seen && previous_core_clk == 0 && core_clk != 0) {
            ++post_reset_posedges;
            if (trace_start_post_reset_cycles
                && trace_end_post_reset_cycles >= trace_start_post_reset_cycles
                && post_reset_posedges >= trace_start_post_reset_cycles
                && post_reset_posedges <= trace_end_post_reset_cycles) {
                trace_rows.push_back(TraceRow{
                    post_reset_posedges,
                    contextp->time(),
                    read_mcycle(root),
                    read_minstret(root),
                    read_pc_raw(root),
                    read_pc_d(root),
                    read_i0_pc_r_ff_din(root),
                    read_dec_i0_instr_d(root),
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_branch_d,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_i0_decode_d,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____VdfgRegularize_hdab710bf_0_43,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_ib0_valid_d,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__misc2ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_exublock_d,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT____Vcellout__misc1ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT____Vcellout__halt_ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__presync_stall,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__lsu_idle,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT____Vcellinp__genblock5__DOT__i_new_4bit_div_fullshortq__valid_in,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__running_state,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT____Vcellout__i_misc_ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__i_misc_ff__DOT__genblock__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__shortq,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__shortq_enable,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__quotient_raw,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__quotient_new,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__dw_shortq_raw,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT____Vcellout__i_b_ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__i_b_ff__DOT__genblock__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__a_ff,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__q_ff,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu__DOT__i_div__DOT__genblock5__DOT__i_new_4bit_div_fullshortq__DOT__r_ff,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_brp_valid,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_predict_nt,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__i0_predict_br,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__decode__DOT__dec_tlu_i0_valid_r,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__i0_valid_no_ebreak_ecall_r,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dma_dccm_stall_any,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__lsu_store_stall_any,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_lsu_valid_raw_d,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmu_fetch_stall,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmu_instr_aligned,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____Vcellout__fbwrite_ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____VdfgRegularize_h02fb64cc_0_10,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_err_r,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dma_iccm_stall_any,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__perr_state,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__err_stop_state,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__exu_flush_final,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_lower_r,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_path_r,
                    root->tb_top__DOT__ifu_axi_rvalid,
                    root->tb_top__DOT__ifu_axi_rid,
                    root->tb_top__DOT__ifu_axi_rresp,
                    root->tb_top__DOT__ifu_axi_rdata,
                    root->tb_top__DOT__mux_axi_rvalid,
                    root->tb_top__DOT__sb_axi_rdata,
                    root->tb_top__DOT__lmem_axi_rvalid,
                    root->tb_top__DOT__lmem_axi_rdata,
                    root->tb_top__DOT__ifu_axi_arready,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__ifu_bus_cmd_valid,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__bus_rd_addr_count,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT____Vcellout__ifu_fetch_addr_f_ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_pmp_addr,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__ifc_fetch_req_bf,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__fb_write_ns,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__miss_f,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT____Vcellout__miss_f_ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__miss_state,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__miss_state_en,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__write_ic_16_bytes,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__mem_ctl__DOT__ic_act_miss_f,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT____VdfgRegularize_h02fb64cc_0_8,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ifc__DOT__ic_hit_f,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__aligndata,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__alignfromf1,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata0ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata1ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__genblock1__DOT__brdata2ff__DOT__genblock__DOT__genblock__DOT__dff__DOT__en,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f1_f0,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f2_f0,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__shift_f2_f1,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__sf0val,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__sf1val,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellout__bundle1ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellout__bundle2ff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_flush_noredir_r,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__ic_fetch_val_f,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_iccm_rd_ecc_single_err,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu_ic_error_start,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec_tlu_i0_commit_cmt,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT____Vcellout__freeff__dout,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__dec__DOT__tlu__DOT__freeff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f0,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f1,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__fetch_to_f2,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT____Vcellinp__bundle1ff__din,
                    root->tb_top__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer__DOT__ifu__DOT__aln__DOT__bundle2ff__DOT__genblock__DOT__dff__DOT____Vcellinp__genblock__DOT__dffs__din,
                    root->__VactTriggered[0],
                    root->__VnbaTriggered[0],
                    read_mailbox_write(root),
                    read_obuf_data(root),
                });
            }
        }
        previous_core_clk = core_clk;
        if ((target_mcycle && read_mcycle(root) >= target_mcycle)
            || (target_post_reset_cycles && post_reset_posedges >= target_post_reset_cycles)) {
            reached_target = true;
            break;
        }
        if (!top->eventsPending()) {
            events_exhausted = true;
            break;
        }
        const uint64_t next_time = top->nextTimeSlot();
        if (next_time > max_time) {
            break;
        }
        contextp->time(next_time);
    }

    top->final();

    const uint64_t obuf_data = read_obuf_data(root);
    const uint32_t pc_raw = read_pc_raw(root);
    const uint32_t pc_d = read_pc_d(root);
    std::cout
        << "{\"schema_version\":1"
        << ",\"surface\":\"rtlmeter_veer_el2_cpu_snapshot.executable\""
        << ",\"target_mcycle\":" << target_mcycle
        << ",\"target_post_reset_cycles\":" << target_post_reset_cycles
        << ",\"trace_start_post_reset_cycles\":" << trace_start_post_reset_cycles
        << ",\"trace_end_post_reset_cycles\":" << trace_end_post_reset_cycles
        << ",\"post_reset_posedges\":" << post_reset_posedges
        << ",\"reset_released_seen\":" << (reset_released_seen ? "true" : "false")
        << ",\"mcycle\":" << read_mcycle(root)
        << ",\"minstret\":" << read_minstret(root)
        << ",\"pc\":" << pc_raw
        << ",\"pc_d\":" << pc_d
        << ",\"mailbox_write\":" << static_cast<unsigned>(read_mailbox_write(root))
        << ",\"obuf_data\":" << obuf_data
        << ",\"obuf_low_byte\":" << (obuf_data & 0xffu)
        << ",\"finish_marker_observed\":" << (((obuf_data & 0xffu) == 0xffu) ? "true" : "false")
        << ",\"reached_target\":" << (reached_target ? "true" : "false")
        << ",\"got_finish\":" << (contextp->gotFinish() ? "true" : "false")
        << ",\"events_exhausted\":" << (events_exhausted ? "true" : "false")
        << ",\"time\":" << contextp->time();
    if (!trace_rows.empty()) {
        std::cout << ",\"trace\":[";
        for (size_t i = 0; i < trace_rows.size(); ++i) {
            const TraceRow& row = trace_rows[i];
            if (i) std::cout << ",";
            std::cout
                << "{\"post_reset_posedges\":" << row.post_reset_posedges
                << ",\"time\":" << row.time
                << ",\"mcycle\":" << row.mcycle
                << ",\"minstret\":" << row.minstret
                << ",\"pc\":" << row.pc
                << ",\"pc_d\":" << row.pc_d
                << ",\"i0_pc_r_ff_din\":" << row.i0_pc_r_ff_din
                << ",\"dec_i0_instr_d\":" << row.dec_i0_instr_d
                << ",\"dec_i0_branch_d\":" << static_cast<unsigned>(row.dec_i0_branch_d)
                << ",\"dec_i0_decode_d\":" << static_cast<unsigned>(row.dec_i0_decode_d)
                << ",\"dec_decode_valid_gate\":" << static_cast<unsigned>(row.dec_decode_valid_gate)
                << ",\"dec_ib0_valid_d\":" << static_cast<unsigned>(row.dec_ib0_valid_d)
                << ",\"dec_misc2ff_dout\":" << static_cast<unsigned>(row.dec_misc2ff_dout)
                << ",\"dec_i0_exublock_d\":" << static_cast<unsigned>(row.dec_i0_exublock_d)
                << ",\"dec_misc1ff_dout\":" << static_cast<unsigned>(row.dec_misc1ff_dout)
                << ",\"dec_halt_ff_dout\":" << row.dec_halt_ff_dout
                << ",\"dec_presync_stall\":" << static_cast<unsigned>(row.dec_presync_stall)
                << ",\"dec_lsu_idle\":" << static_cast<unsigned>(row.dec_lsu_idle)
                << ",\"exu_div_valid_in\":" << static_cast<unsigned>(row.exu_div_valid_in)
                << ",\"exu_div_running_state\":" << static_cast<unsigned>(row.exu_div_running_state)
                << ",\"exu_div_i_misc_ff\":" << row.exu_div_i_misc_ff
                << ",\"exu_div_i_misc_ff_din\":" << row.exu_div_i_misc_ff_din
                << ",\"exu_div_shortq\":" << static_cast<unsigned>(row.exu_div_shortq)
                << ",\"exu_div_shortq_enable\":" << static_cast<unsigned>(row.exu_div_shortq_enable)
                << ",\"exu_div_quotient_raw\":" << row.exu_div_quotient_raw
                << ",\"exu_div_quotient_new\":" << static_cast<unsigned>(row.exu_div_quotient_new)
                << ",\"exu_div_dw_shortq_raw\":" << static_cast<unsigned>(row.exu_div_dw_shortq_raw)
                << ",\"exu_div_i_b_ff\":" << row.exu_div_i_b_ff
                << ",\"exu_div_i_b_ff_din\":" << row.exu_div_i_b_ff_din
                << ",\"exu_div_a_ff\":" << row.exu_div_a_ff
                << ",\"exu_div_q_ff\":" << row.exu_div_q_ff
                << ",\"exu_div_r_ff\":" << row.exu_div_r_ff
                << ",\"i0_brp_valid\":" << static_cast<unsigned>(row.i0_brp_valid)
                << ",\"i0_predict_nt\":" << static_cast<unsigned>(row.i0_predict_nt)
                << ",\"i0_predict_br\":" << static_cast<unsigned>(row.i0_predict_br)
                << ",\"dec_tlu_i0_valid_r\":" << static_cast<unsigned>(row.dec_tlu_i0_valid_r)
                << ",\"i0_valid_no_ebreak_ecall_r\":" << static_cast<unsigned>(row.i0_valid_no_ebreak_ecall_r)
                << ",\"dma_dccm_stall_any\":" << static_cast<unsigned>(row.dma_dccm_stall_any)
                << ",\"lsu_store_stall_any\":" << static_cast<unsigned>(row.lsu_store_stall_any)
                << ",\"dec_lsu_valid_raw_d\":" << static_cast<unsigned>(row.dec_lsu_valid_raw_d)
                << ",\"ifu_pmu_fetch_stall\":" << static_cast<unsigned>(row.ifu_pmu_fetch_stall)
                << ",\"ifu_pmu_instr_aligned\":" << static_cast<unsigned>(row.ifu_pmu_instr_aligned)
                << ",\"ifu_ifc_fbwrite_dout\":" << static_cast<unsigned>(row.ifu_ifc_fbwrite_dout)
                << ",\"ifu_ifc_fetch_consume_gate\":" << static_cast<unsigned>(row.ifu_ifc_fetch_consume_gate)
                << ",\"dec_tlu_flush_err_r\":" << static_cast<unsigned>(row.dec_tlu_flush_err_r)
                << ",\"dma_iccm_stall_any\":" << static_cast<unsigned>(row.dma_iccm_stall_any)
                << ",\"ifu_mem_perr_state\":" << static_cast<unsigned>(row.ifu_mem_perr_state)
                << ",\"ifu_mem_err_stop_state\":" << static_cast<unsigned>(row.ifu_mem_err_stop_state)
                << ",\"exu_flush_final\":" << static_cast<unsigned>(row.exu_flush_final)
                << ",\"dec_tlu_flush_lower_r\":" << static_cast<unsigned>(row.dec_tlu_flush_lower_r)
                << ",\"dec_tlu_flush_path_r\":" << row.dec_tlu_flush_path_r
                << ",\"tb_ifu_axi_rvalid\":" << static_cast<unsigned>(row.tb_ifu_axi_rvalid)
                << ",\"tb_ifu_axi_rid\":" << static_cast<unsigned>(row.tb_ifu_axi_rid)
                << ",\"tb_ifu_axi_rresp\":" << static_cast<unsigned>(row.tb_ifu_axi_rresp)
                << ",\"tb_ifu_axi_rdata\":" << row.tb_ifu_axi_rdata
                << ",\"tb_mux_axi_rvalid\":" << static_cast<unsigned>(row.tb_mux_axi_rvalid)
                << ",\"tb_sb_axi_rdata\":" << row.tb_sb_axi_rdata
                << ",\"tb_lmem_axi_rvalid\":" << static_cast<unsigned>(row.tb_lmem_axi_rvalid)
                << ",\"tb_lmem_axi_rdata\":" << row.tb_lmem_axi_rdata
                << ",\"tb_ifu_axi_arready\":" << static_cast<unsigned>(row.tb_ifu_axi_arready)
                << ",\"ifu_bus_cmd_valid\":" << static_cast<unsigned>(row.ifu_bus_cmd_valid)
                << ",\"ifu_bus_rd_addr_count\":" << static_cast<unsigned>(row.ifu_bus_rd_addr_count)
                << ",\"ifu_fetch_addr_f\":" << row.ifu_fetch_addr_f
                << ",\"ifu_pmp_addr\":" << row.ifu_pmp_addr
                << ",\"ifu_ifc_fetch_req_bf\":" << static_cast<unsigned>(row.ifu_ifc_fetch_req_bf)
                << ",\"ifu_ifc_fb_write_ns\":" << static_cast<unsigned>(row.ifu_ifc_fb_write_ns)
                << ",\"ifu_ifc_miss_f\":" << static_cast<unsigned>(row.ifu_ifc_miss_f)
                << ",\"ifu_mem_miss_f\":" << row.ifu_mem_miss_f
                << ",\"ifu_mem_miss_state\":" << static_cast<unsigned>(row.ifu_mem_miss_state)
                << ",\"ifu_mem_miss_state_en\":" << static_cast<unsigned>(row.ifu_mem_miss_state_en)
                << ",\"ifu_mem_write_ic_16_bytes\":" << static_cast<unsigned>(row.ifu_mem_write_ic_16_bytes)
                << ",\"ifu_mem_ic_act_miss_f\":" << static_cast<unsigned>(row.ifu_mem_ic_act_miss_f)
                << ",\"ifu_ifc_fetch_ready\":" << static_cast<unsigned>(row.ifu_ifc_fetch_ready)
                << ",\"ifu_ifc_ic_hit_f\":" << static_cast<unsigned>(row.ifu_ifc_ic_hit_f)
                << ",\"ifu_aln_aligndata\":" << row.ifu_aln_aligndata
                << ",\"ifu_aln_alignfromf1\":" << static_cast<unsigned>(row.ifu_aln_alignfromf1)
                << ",\"ifu_aln_brdata0_en\":" << static_cast<unsigned>(row.ifu_aln_brdata0_en)
                << ",\"ifu_aln_brdata1_en\":" << static_cast<unsigned>(row.ifu_aln_brdata1_en)
                << ",\"ifu_aln_brdata2_en\":" << static_cast<unsigned>(row.ifu_aln_brdata2_en)
                << ",\"ifu_aln_shift_f1_f0\":" << static_cast<unsigned>(row.ifu_aln_shift_f1_f0)
                << ",\"ifu_aln_shift_f2_f0\":" << static_cast<unsigned>(row.ifu_aln_shift_f2_f0)
                << ",\"ifu_aln_shift_f2_f1\":" << static_cast<unsigned>(row.ifu_aln_shift_f2_f1)
                << ",\"ifu_aln_sf0val\":" << static_cast<unsigned>(row.ifu_aln_sf0val)
                << ",\"ifu_aln_sf1val\":" << static_cast<unsigned>(row.ifu_aln_sf1val)
                << ",\"ifu_aln_bundle1\":" << static_cast<unsigned>(row.ifu_aln_bundle1)
                << ",\"ifu_aln_bundle2\":" << static_cast<unsigned>(row.ifu_aln_bundle2)
                << ",\"dec_tlu_flush_noredir_r\":" << static_cast<unsigned>(row.dec_tlu_flush_noredir_r)
                << ",\"ifu_ic_fetch_val_f\":" << static_cast<unsigned>(row.ifu_ic_fetch_val_f)
                << ",\"ifu_iccm_rd_ecc_single_err\":" << static_cast<unsigned>(row.ifu_iccm_rd_ecc_single_err)
                << ",\"ifu_ic_error_start\":" << static_cast<unsigned>(row.ifu_ic_error_start)
                << ",\"dec_tlu_i0_commit_cmt\":" << static_cast<unsigned>(row.dec_tlu_i0_commit_cmt)
                << ",\"dec_tlu_freeff_dout\":" << static_cast<unsigned>(row.dec_tlu_freeff_dout)
                << ",\"dec_tlu_freeff_din\":" << static_cast<unsigned>(row.dec_tlu_freeff_din)
                << ",\"ifu_aln_fetch_to_f0\":" << static_cast<unsigned>(row.ifu_aln_fetch_to_f0)
                << ",\"ifu_aln_fetch_to_f1\":" << static_cast<unsigned>(row.ifu_aln_fetch_to_f1)
                << ",\"ifu_aln_fetch_to_f2\":" << static_cast<unsigned>(row.ifu_aln_fetch_to_f2)
                << ",\"ifu_aln_bundle1_din\":" << static_cast<unsigned>(row.ifu_aln_bundle1_din)
                << ",\"ifu_aln_bundle2_din\":" << static_cast<unsigned>(row.ifu_aln_bundle2_din)
                << ",\"root_act_triggered\":" << row.root_act_triggered
                << ",\"root_nba_triggered\":" << row.root_nba_triggered
                << ",\"mailbox_write\":" << static_cast<unsigned>(row.mailbox_write)
                << ",\"obuf_data\":" << row.obuf_data
                << ",\"obuf_low_byte\":" << (row.obuf_data & 0xffu)
                << "}";
        }
        std::cout << "]";
    }
    std::cout << "}\n";
    return reached_target ? 0 : 3;
}
'''


def build_compile_command(*, source: Path, binary: Path, obj_dir: Path) -> list[str]:
    verilator_root = Path(os.environ.get("VERILATOR_ROOT", "/usr/local/share/verilator"))
    return [
        "g++",
        "-std=c++17",
        "-DVL_TIME_CONTEXT",
        "-DVERILATOR=1",
        "-DVM_COVERAGE=0",
        "-DVM_SC=0",
        "-DVM_TIMING=1",
        "-DVM_TRACE=0",
        "-DVM_TRACE_FST=0",
        "-DVM_TRACE_VCD=0",
        "-DVM_TRACE_SAIF=0",
        "-fcoroutines",
        f"-I{obj_dir}",
        f"-I{verilator_root / 'include'}",
        f"-I{verilator_root / 'include' / 'vltstd'}",
        str(source),
        str(obj_dir / "Vsim__ALL.a"),
        str(obj_dir / "verilated.o"),
        str(obj_dir / "verilated_threads.o"),
        str(obj_dir / "verilated_timing.o"),
        "-pthread",
        "-latomic",
        "-o",
        str(binary),
    ]


def run_cpu_snapshot(
    *,
    compile_root: str = DEFAULT_COMPILE_ROOT,
    execute_dir: str = DEFAULT_EXECUTE_DIR,
    artifact_root: str = DEFAULT_ARTIFACT_ROOT,
    target_mcycle: int,
    target_post_reset_cycles: int | None = None,
    trace_start_post_reset_cycles: int | None = None,
    trace_end_post_reset_cycles: int | None = None,
    iterations: int | None = None,
    max_time: int | None = None,
    execute: bool = False,
    repo_root: Path | None = None,
    runner=subprocess.run,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    artifact_rel, artifact_errors = _validated_output_path(
        artifact_root,
        required_root="artifacts",
        default=DEFAULT_ARTIFACT_ROOT,
    )
    report: dict[str, object] = {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "opt_in_required" if not execute else "preflight_pending",
        "compile_root": _report_arg_path(compile_root, root),
        "execute_dir": _report_arg_path(execute_dir, root),
        "artifact_root": artifact_rel,
        "target_mcycle": target_mcycle,
        "target_post_reset_cycles": target_post_reset_cycles,
        "trace_start_post_reset_cycles": trace_start_post_reset_cycles,
        "trace_end_post_reset_cycles": trace_end_post_reset_cycles,
        "iterations": iterations,
        "max_time": max_time,
        "gpu_execution_claimed": False,
        "speedup_claimed": False,
        "same_cycle_cpu_snapshot": False,
        "canonical_project_state_changed": False,
        "generated_report_is_source_of_truth": False,
        "commands": {},
        "snapshot": None,
        "missing_prerequisites": [],
        "non_claims": [
            "CPU snapshot is not GPU execution evidence",
            "bounded CPU snapshot is progress evidence only until compared with a matching GPU report",
            "reports are generated evidence only and not source of truth",
        ],
    }
    if artifact_errors:
        report["status"] = "invalid_artifact_root"
        report["missing_prerequisites"] = artifact_errors
        return report
    if target_mcycle < 1 and not (isinstance(target_post_reset_cycles, int) and target_post_reset_cycles > 0):
        report["status"] = "invalid_target_mcycle"
        report["missing_prerequisites"] = ["target_mcycle_or_target_post_reset_cycles"]
        return report

    obj_dir = obj_dir_from_compile_root(compile_root, repo_root=root)
    exec_dir_path = Path(execute_dir)
    if not exec_dir_path.is_absolute():
        exec_dir_path = root / exec_dir_path
    artifact_path = root / artifact_rel
    source = artifact_path / "veer_el2_cpu_snapshot_main.cpp"
    binary = artifact_path / "veer_el2_cpu_snapshot"
    compile_command = build_compile_command(source=source, binary=binary, obj_dir=obj_dir)
    run_command = [
        str(binary),
        "+verilator+quiet",
    ]
    if target_mcycle > 0:
        run_command.append(f"+snapshot_mcycle={target_mcycle}")
    if target_post_reset_cycles is not None:
        run_command.append(f"+snapshot_post_reset_cycles={target_post_reset_cycles}")
    if trace_start_post_reset_cycles is not None:
        run_command.append(f"+snapshot_trace_start_post_reset_cycles={trace_start_post_reset_cycles}")
    if trace_end_post_reset_cycles is not None:
        run_command.append(f"+snapshot_trace_end_post_reset_cycles={trace_end_post_reset_cycles}")
    if iterations is not None:
        run_command.append(f"+iterations={iterations}")
    if max_time is not None:
        run_command.append(f"+snapshot_max_time={max_time}")
    report["commands"] = {
        "compile": [_sanitize_report_value(arg, root) for arg in compile_command],
        "run": [_sanitize_report_value(arg, root) for arg in run_command],
    }

    if not execute:
        return report
    missing = []
    for path, label in (
        (obj_dir / "Vsim__ALL.a", "compiled_verilator_archive"),
        (obj_dir / "verilated.o", "verilated_runtime_object"),
        (exec_dir_path / "program.hex", "execute_program_hex"),
    ):
        if not path.exists():
            missing.append(label)
    if missing:
        report["status"] = "missing_prerequisites"
        report["missing_prerequisites"] = missing
        return report

    artifact_path.mkdir(parents=True, exist_ok=True)
    source.write_text(cpu_snapshot_source(), encoding="utf-8")
    start = time.monotonic()
    compile_result = runner(compile_command, cwd=root, text=True, capture_output=True)
    compile_wall = time.monotonic() - start
    report["compile"] = {
        "returncode": int(compile_result.returncode),
        "wall_s": round(compile_wall, 6),
        "stdout_tail": _sanitize_report_value(str(compile_result.stdout)[-4000:], root),
        "stderr_tail": _sanitize_report_value(str(compile_result.stderr)[-4000:], root),
    }
    if int(compile_result.returncode) != 0:
        report["status"] = "compile_failed"
        return report

    start = time.monotonic()
    run_result = runner(run_command, cwd=exec_dir_path, text=True, capture_output=True)
    run_wall = time.monotonic() - start
    report["run"] = {
        "returncode": int(run_result.returncode),
        "wall_s": round(run_wall, 6),
        "stdout_tail": _sanitize_report_value(str(run_result.stdout)[-4000:], root),
        "stderr_tail": _sanitize_report_value(str(run_result.stderr)[-4000:], root),
    }
    snapshot = _extract_snapshot_json(str(run_result.stdout))
    if snapshot is None:
        report["status"] = "missing_snapshot_json"
        return report
    pc = snapshot.get("pc")
    pc_d = snapshot.get("pc_d")
    obuf_data = snapshot.get("obuf_data")
    snapshot["pc_hex"] = f"0x{int(pc):08x}" if isinstance(pc, int) else None
    snapshot["pc_d_hex"] = f"0x{int(pc_d):08x}" if isinstance(pc_d, int) else None
    snapshot["obuf_data_hex"] = f"0x{int(obuf_data):016x}" if isinstance(obuf_data, int) else None
    trace = snapshot.get("trace")
    if isinstance(trace, list):
        for raw_row in trace:
            if isinstance(raw_row, dict):
                row_pc = raw_row.get("pc")
                row_pc_d = raw_row.get("pc_d")
                row_pc_din = raw_row.get("i0_pc_r_ff_din")
                row_instr = raw_row.get("dec_i0_instr_d")
                row_flush_path = raw_row.get("dec_tlu_flush_path_r")
                row_misc1 = raw_row.get("dec_misc1ff_dout")
                row_halt = raw_row.get("dec_halt_ff_dout")
                row_div_misc = raw_row.get("exu_div_i_misc_ff")
                row_div_misc_din = raw_row.get("exu_div_i_misc_ff_din")
                row_div_quotient_raw = raw_row.get("exu_div_quotient_raw")
                row_div_i_b_ff = raw_row.get("exu_div_i_b_ff")
                row_fbwrite = raw_row.get("ifu_ifc_fbwrite_dout")
                row_ifu_rdata = raw_row.get("tb_ifu_axi_rdata")
                row_sb_rdata = raw_row.get("tb_sb_axi_rdata")
                row_lmem_rdata = raw_row.get("tb_lmem_axi_rdata")
                row_ifu_fetch_addr = raw_row.get("ifu_fetch_addr_f")
                row_ifu_pmp_addr = raw_row.get("ifu_pmp_addr")
                row_ifu_miss_f = raw_row.get("ifu_mem_miss_f")
                row_aligndata = raw_row.get("ifu_aln_aligndata")
                row_freeff_dout = raw_row.get("dec_tlu_freeff_dout")
                row_freeff_din = raw_row.get("dec_tlu_freeff_din")
                row_obuf = raw_row.get("obuf_data")
                raw_row["pc_hex"] = f"0x{int(row_pc):08x}" if isinstance(row_pc, int) else None
                raw_row["pc_d_hex"] = f"0x{int(row_pc_d):08x}" if isinstance(row_pc_d, int) else None
                raw_row["i0_pc_r_ff_din_hex"] = f"0x{int(row_pc_din):08x}" if isinstance(row_pc_din, int) else None
                raw_row["dec_i0_instr_d_hex"] = f"0x{int(row_instr):08x}" if isinstance(row_instr, int) else None
                raw_row["ifu_ifc_fbwrite_dout_hex"] = (
                    f"0x{int(row_fbwrite):03x}" if isinstance(row_fbwrite, int) else None
                )
                raw_row["dec_tlu_flush_path_r_hex"] = (
                    f"0x{int(row_flush_path):08x}" if isinstance(row_flush_path, int) else None
                )
                raw_row["dec_misc1ff_dout_hex"] = (
                    f"0x{int(row_misc1):02x}" if isinstance(row_misc1, int) else None
                )
                raw_row["dec_halt_ff_dout_hex"] = (
                    f"0x{int(row_halt):05x}" if isinstance(row_halt, int) else None
                )
                raw_row["exu_div_i_misc_ff_hex"] = (
                    f"0x{int(row_div_misc):05x}" if isinstance(row_div_misc, int) else None
                )
                raw_row["exu_div_i_misc_ff_din_hex"] = (
                    f"0x{int(row_div_misc_din):05x}" if isinstance(row_div_misc_din, int) else None
                )
                raw_row["exu_div_quotient_raw_hex"] = (
                    f"0x{int(row_div_quotient_raw):04x}" if isinstance(row_div_quotient_raw, int) else None
                )
                raw_row["exu_div_i_b_ff_hex"] = (
                    f"0x{int(row_div_i_b_ff):010x}" if isinstance(row_div_i_b_ff, int) else None
                )
                raw_row["tb_ifu_axi_rdata_hex"] = (
                    f"0x{int(row_ifu_rdata):016x}" if isinstance(row_ifu_rdata, int) else None
                )
                raw_row["tb_sb_axi_rdata_hex"] = (
                    f"0x{int(row_sb_rdata):016x}" if isinstance(row_sb_rdata, int) else None
                )
                raw_row["tb_lmem_axi_rdata_hex"] = (
                    f"0x{int(row_lmem_rdata):016x}" if isinstance(row_lmem_rdata, int) else None
                )
                raw_row["ifu_fetch_addr_f_hex"] = (
                    f"0x{int(row_ifu_fetch_addr):08x}" if isinstance(row_ifu_fetch_addr, int) else None
                )
                raw_row["ifu_pmp_addr_hex"] = (
                    f"0x{int(row_ifu_pmp_addr):08x}" if isinstance(row_ifu_pmp_addr, int) else None
                )
                raw_row["ifu_mem_miss_f_hex"] = (
                    f"0x{int(row_ifu_miss_f):08x}" if isinstance(row_ifu_miss_f, int) else None
                )
                raw_row["ifu_aln_aligndata_hex"] = (
                    f"0x{int(row_aligndata):08x}" if isinstance(row_aligndata, int) else None
                )
                raw_row["dec_tlu_freeff_dout_hex"] = (
                    f"0x{int(row_freeff_dout):03x}" if isinstance(row_freeff_dout, int) else None
                )
                raw_row["dec_tlu_freeff_din_hex"] = (
                    f"0x{int(row_freeff_din):03x}" if isinstance(row_freeff_din, int) else None
                )
                raw_row["obuf_data_hex"] = f"0x{int(row_obuf):016x}" if isinstance(row_obuf, int) else None
    report["snapshot"] = snapshot
    report["same_cycle_cpu_snapshot"] = snapshot.get("reached_target") is True
    report["status"] = "passed" if report["same_cycle_cpu_snapshot"] else "target_not_reached"
    return report


def write_report(report: Mapping[str, object], report_path: str | Path, *, repo_root: Path) -> Path:
    path_text, errors = _validated_output_path(report_path, required_root="reports", default=DEFAULT_REPORT)
    if errors:
        raise ValueError(",".join(errors))
    path = repo_root / path_text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile-root", default=DEFAULT_COMPILE_ROOT)
    parser.add_argument("--execute-dir", default=DEFAULT_EXECUTE_DIR)
    parser.add_argument("--artifact-root", default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--target-mcycle", type=int, required=True)
    parser.add_argument("--target-post-reset-cycles", type=int, default=None)
    parser.add_argument("--trace-start-post-reset-cycles", type=int, default=None)
    parser.add_argument("--trace-end-post-reset-cycles", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--max-time", type=int, default=None)
    parser.add_argument("--execute", action="store_true", help="Run the snapshot build/executable; also enabled by opt-in env")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = _repo_root()
    execute = args.execute or os.environ.get(OPT_IN_ENV) == "1"
    report = run_cpu_snapshot(
        compile_root=args.compile_root,
        execute_dir=args.execute_dir,
        artifact_root=args.artifact_root,
        target_mcycle=args.target_mcycle,
        target_post_reset_cycles=args.target_post_reset_cycles,
        trace_start_post_reset_cycles=args.trace_start_post_reset_cycles,
        trace_end_post_reset_cycles=args.trace_end_post_reset_cycles,
        iterations=args.iterations,
        max_time=args.max_time,
        execute=execute,
        repo_root=root,
    )
    if args.write_report:
        write_report(report, args.report_out, repo_root=root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"opt_in_required", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
