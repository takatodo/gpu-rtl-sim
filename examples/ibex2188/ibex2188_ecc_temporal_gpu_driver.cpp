// CPU reference driver for ibex2188_ecc_temporal_gpu_tb.
// Runs the device-clean GPU TB on the host, dumps the full root state, and
// prints the semantic observables so CPU/GPU state images can be compared.
#include "Vibex2188_ecc_temporal_gpu_tb.h"
#include "Vibex2188_ecc_temporal_gpu_tb___024root.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>

static void eval(Vibex2188_ecc_temporal_gpu_tb& top, unsigned char clk) {
    top.clk_i = clk;
    top.eval();
}

static void run_reproducer(
    Vibex2188_ecc_temporal_gpu_tb& top,
    bool fault_enable,
    unsigned fault_bit,
    unsigned load_response_delay,
    bool inject_port_b
) {
    top.rst_ni = 0;
    top.fault_enable_i = fault_enable;
    top.fault_bit_i = fault_bit & 0x1f;
    top.load_response_delay_i = load_response_delay & 0x3;
    top.inject_port_b_i = inject_port_b;
    eval(top, 0);
    eval(top, 1);
    eval(top, 0);
    eval(top, 1);
    eval(top, 0);
    top.rst_ni = 1;
    eval(top, 1);
    eval(top, 0);
    // Keep clocking until done_o is asserted or a bound is reached.
    for (unsigned cycle = 0; cycle < 200; ++cycle) {
        eval(top, 1);
        eval(top, 0);
        if (top.done_o) break;
    }
}

int main(int argc, char** argv) {
    bool fault_enable = true;
    unsigned fault_bit = 0;
    unsigned load_response_delay = 1;
    bool inject_port_b = false;
    const char* dump_path = nullptr;
    for (int index = 1; index < argc; ++index) {
        const std::string arg(argv[index]);
        if (arg == "--no-fault") fault_enable = false;
        else if (arg == "--fault-bit" && index + 1 < argc) fault_bit = std::strtoul(argv[++index], nullptr, 10);
        else if (arg == "--load-response-delay" && index + 1 < argc) load_response_delay = std::strtoul(argv[++index], nullptr, 10);
        else if (arg == "--fault-port-b") inject_port_b = true;
        else if (arg == "--dump-state" && index + 1 < argc) dump_path = argv[++index];
        else {
            std::fprintf(stderr, "usage: %s [--no-fault] [--fault-bit N] [--load-response-delay N] [--fault-port-b] [--dump-state PATH]\n", argv[0]);
            return 2;
        }
    }
    Vibex2188_ecc_temporal_gpu_tb top;
    run_reproducer(top, fault_enable, fault_bit, load_response_delay, inject_port_b);
    if (dump_path) {
        std::ofstream out(dump_path, std::ios::binary);
        out.write(reinterpret_cast<const char*>(top.rootp), sizeof(*top.rootp));
    }
    std::printf(
        "RESULT done=%u oracle_violation=%u fault_seen=%u alert_seen=%u "
        "rf_read_enable=%u rf_wb_match=%u rf_write_wb=%u rf_ecc_error_id=%u "
        "instruction_valid_id=%u alert_major_internal=%u fault_enable=%u "
        "fault_bit=%u load_response_delay=%u inject_port_b=%u\n",
        top.done_o, top.oracle_violation_o, top.fault_seen_o, top.alert_seen_o,
        top.rf_read_enable_o, top.rf_wb_match_o, top.rf_write_wb_o,
        top.rf_ecc_error_id_o, top.instruction_valid_id_o, top.alert_major_internal_o,
        fault_enable ? 1 : 0, fault_bit, load_response_delay, inject_port_b ? 1 : 0
    );
    return top.done_o ? 0 : 1;
}
