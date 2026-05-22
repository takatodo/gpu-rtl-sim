from __future__ import annotations

from pathlib import Path


def _strict_output_words(tb_contract: dict, prefixes: list[str]) -> list[dict[str, int | str]]:
    counts = tb_contract.get("baseline_reference_counts") or {}
    return [
        {"prefix": str(prefix), "count": int(counts[prefix])}
        for prefix in prefixes
        if prefix in counts
    ]


def _legacy_clock_reset_fields(target_name: str, top_module: str) -> dict[str, str]:
    clock_field = f"{top_module}__DOT__clk_i"
    reset_field = f"{top_module}__DOT__reset_like_w"
    reset_report_name = "reset_like_w"
    if target_name in {
        "tlul_sink",
        "tlul_request_loopback",
        "tlul_adapter_reg",
        "tlul_adapter_sram",
        "tlul_err_resp",
        "tlul_err",
        "tlul_cmd_intg_chk",
        "tlul_lc_gate",
    }:
        reset_field = f"{top_module}__DOT__rst_ni"
        reset_report_name = "rst_ni"
    elif target_name in {"tlul_adapter_host", "tlul_socket_m1", "tlul_socket_1n"}:
        clock_field = "clk_i"
        reset_field = "rst_ni"
        reset_report_name = "rst_ni"
    return {
        "clock_field": clock_field,
        "reset_field": reset_field,
        "reset_report_name": reset_report_name,
    }


def _legacy_source_files(*, target_name: str, rtl_path: str) -> list[str]:
    source_files = [
        "third_party/rtlmeter/designs/OpenTitan/src/top_pkg.sv",
        "third_party/rtlmeter/designs/OpenTitan/src/prim_mubi_pkg.sv",
        "third_party/rtlmeter/designs/OpenTitan/src/prim_secded_pkg.sv",
        "third_party/rtlmeter/designs/OpenTitan/src/prim_util_pkg.sv",
        "third_party/rtlmeter/designs/OpenTitan/src/prim_count_pkg.sv",
        "third_party/rtlmeter/designs/OpenTitan/src/prim_pkg.sv",
        "third_party/rtlmeter/designs/OpenTitan/src/tlul_pkg.sv",
        rtl_path,
    ]
    if target_name == "tlul_lc_gate":
        source_files.insert(-1, "third_party/rtlmeter/designs/OpenTitan/src/lc_ctrl_reg_pkg.sv")
        source_files.insert(-1, "third_party/rtlmeter/designs/OpenTitan/src/lc_ctrl_pkg.sv")
    return source_files


def _legacy_build_config(
    *,
    target_name: str,
    runner_args: dict,
    clock_reset: dict[str, str],
) -> dict:
    return {
        "mdir": f"artifacts/{target_name}_obj_dir",
        "work_dir": str(runner_args.get("work_dir", f"work/slice_pilots/{target_name}")),
        "host_probe_target": f"{target_name}_host_probe",
        "host_probe_builder": "src/tools/build_host_probe.py",
        "host_probe": {
            "output": "tlul_slice_host_probe",
            "clock_field": clock_reset["clock_field"],
            "clock_report_name": "clk_i",
            "reset_field": clock_reset["reset_field"],
            "reset_report_name": clock_reset["reset_report_name"],
            "reset_asserted_value": "1U",
            "reset_deasserted_value": "0U",
            "host_clock_control": True,
            "host_reset_control": False,
            "probe_syms_state": False,
        },
    }


def _legacy_planned_overlay(
    *,
    target_name: str,
    coverage_tb_path: str,
    coverage_manifest_path: str,
) -> dict:
    return {
        "coverage_tb_path": coverage_tb_path,
        "coverage_manifest_path": coverage_manifest_path,
        "launch_template_path": f"config/slice_launch_templates/{target_name}.json",
        "host_probe_target": f"{target_name}_host_probe",
        "host_probe_builder": "src/tools/build_host_probe.py",
        "status": "legacy_schema_normalized_in_memory",
    }


def _coverage_output_contract(strict_output_words: list[dict[str, int | str]]) -> dict:
    total_words = sum(int(entry["count"]) for entry in strict_output_words)
    return {
        "strict_output_words": strict_output_words,
        "total_words_per_state": total_words,
        "total_bytes_per_state": total_words * 4,
        "acceptance_policy": "coverage_output_equivalence",
    }


def normalize_template_payload(payload: dict) -> dict:
    if payload.get("top_module") or payload.get("build"):
        return payload
    if payload.get("schema_version") != "opentitan-tlul-slice-launch-template-v1":
        return payload

    runner_args = payload.get("runner_args_template") or {}
    static_features = payload.get("static_features") or {}
    tb_contract = payload.get("tb_core_contract") or {}
    target = str(payload.get("target") or runner_args["target"])
    target_name = target.split(".")[-1]
    top_module = str(runner_args["top_module"])
    rtl_path = str(runner_args.get("rtl_path") or static_features["rtl_path"])
    coverage_tb_path = str(
        runner_args.get("coverage_tb_path") or static_features["coverage_tb_path"]
    )
    coverage_manifest_path = str(
        runner_args.get("coverage_manifest_path") or static_features["coverage_manifest_path"]
    )
    prefixes = tb_contract.get("required_output_prefixes") or [
        "real_toggle_subset_word",
        "toggle_bitmap_word",
        "focused_wave_word",
    ]
    output_words = _strict_output_words(tb_contract, prefixes)
    clock_reset = _legacy_clock_reset_fields(target_name, top_module)

    normalized = dict(payload)
    normalized["schema_version"] = 1
    normalized["target"] = target
    normalized["top_module"] = top_module
    normalized["source_gate"] = "config/scaling_gates/tlul_coverage_output_equivalence.json"
    normalized["source_files"] = _legacy_source_files(target_name=target_name, rtl_path=rtl_path)
    normalized["verilator_args"] = [
        "-Wno-fatal",
        "-Ithird_party/rtlmeter/designs/OpenTitan/src",
        f"-I{Path(coverage_tb_path).parent}",
    ]
    normalized["build"] = _legacy_build_config(
        target_name=target_name,
        runner_args=runner_args,
        clock_reset=clock_reset,
    )
    normalized["planned_overlay"] = _legacy_planned_overlay(
        target_name=target_name,
        coverage_tb_path=coverage_tb_path,
        coverage_manifest_path=coverage_manifest_path,
    )
    normalized["coverage_output_contract"] = _coverage_output_contract(output_words)
    return normalized
