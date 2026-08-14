// CPU reference driver for tlul_adapter_sram_10818_gpu_tb.
#include "Vtlul_adapter_sram_10818_gpu_tb.h"
#include "Vtlul_adapter_sram_10818_gpu_tb___024root.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>

static void eval(Vtlul_adapter_sram_10818_gpu_tb& top, unsigned char clk) {
    top.clk_i = clk;
    top.eval();
}

static bool load_state(Vtlul_adapter_sram_10818_gpu_tb& top, const char* path) {
    if (!path) {
        return false;
    }
    std::ifstream in(path, std::ios::binary);
    if (!in.is_open()) {
        return false;
    }
    in.read(reinterpret_cast<char*>(top.rootp), sizeof(*top.rootp));
    return in.good() && in.gcount() == sizeof(*top.rootp);
}

static unsigned long parse_cycles(const char* text, const char* option) {
    if (!text || text[0] == '\0' || text[0] == '-') {
        throw std::runtime_error(std::string(option) + " requires a nonnegative integer");
    }
    char* end = nullptr;
    unsigned long value = std::strtoul(text, &end, 10);
    if (*end != '\0') {
        throw std::runtime_error(std::string(option) + " requires a nonnegative integer");
    }
    return value;
}

static void run_action(
    Vtlul_adapter_sram_10818_gpu_tb& top,
    bool malformed,
    unsigned long backpressure_cycles,
    unsigned long response_delay_cycles
) {
    top.rst_ni = 0;
    top.start_i = 0;
    top.malformed_i = malformed;
    top.d_backpressure_i = 0;
    top.response_valid_i = 0;
    eval(top, 0);
    eval(top, 1);
    eval(top, 0);
    top.rst_ni = 1;
    top.start_i = 1;
    eval(top, 1);
    top.start_i = 0;
    eval(top, 0);
    eval(top, 1);

    const unsigned long active_response_delay = malformed ? 0UL : response_delay_cycles;
    const unsigned long wait_cycles_before_completion =
        backpressure_cycles > active_response_delay ? backpressure_cycles : active_response_delay;
    for (unsigned long wait_cycle = 0; wait_cycle <= wait_cycles_before_completion; ++wait_cycle) {
        top.d_backpressure_i = wait_cycle < backpressure_cycles;
        top.response_valid_i = wait_cycle >= active_response_delay;
        eval(top, 0);
        eval(top, 1);
    }
}

int main(int argc, char** argv) {
    unsigned long backpressure_cycles = 0;
    unsigned long response_delay_cycles = 0;
    bool malformed = false;
    const char* dump_path = nullptr;
    const char* checkpoint_path = nullptr;
    bool one_eval = false;
    for (int index = 1; index < argc; ++index) {
        const std::string arg(argv[index]);
        if (arg == "--backpressure") backpressure_cycles = 1;
        else if (arg == "--backpressure-cycles" && index + 1 < argc) {
            try {
                backpressure_cycles = parse_cycles(argv[++index], "--backpressure-cycles");
            } catch (const std::runtime_error& error) {
                std::fprintf(stderr, "%s\n", error.what());
                return 2;
            }
        }
        else if (arg == "--response-delay-cycles" && index + 1 < argc) {
            try {
                response_delay_cycles = parse_cycles(argv[++index], "--response-delay-cycles");
            } catch (const std::runtime_error& error) {
                std::fprintf(stderr, "%s\n", error.what());
                return 2;
            }
        }
        else if (arg == "--malformed") malformed = true;
        else if (arg == "--dump-state" && index + 1 < argc) dump_path = argv[++index];
        else if (arg == "--checkpoint" && index + 1 < argc) checkpoint_path = argv[++index];
        else if (arg == "--one-eval") one_eval = true;
        else {
            std::fprintf(
                stderr,
                "usage: %s [--malformed] [--backpressure] [--backpressure-cycles N] [--response-delay-cycles N] [--checkpoint PATH] [--one-eval] [--dump-state PATH]\n",
                argv[0]
            );
            return 2;
        }
    }
    if (one_eval && !checkpoint_path) {
        std::fprintf(stderr, "--one-eval requires --checkpoint\n");
        return 2;
    }

    Vtlul_adapter_sram_10818_gpu_tb top;
    if (checkpoint_path) {
        if (!load_state(top, checkpoint_path)) {
            std::fprintf(stderr, "failed to load checkpoint: %s\n", checkpoint_path);
            return 2;
        }
        if (one_eval) {
            top.clk_i ^= 1;
            eval(top, top.clk_i);
        }
    } else {
        run_action(top, malformed, backpressure_cycles, response_delay_cycles);
    }

    if (dump_path) {
        std::ofstream out(dump_path, std::ios::binary);
        out.write(reinterpret_cast<const char*>(top.rootp), sizeof(*top.rootp));
    }
    std::printf("RESULT done=%u oracle_violation=%u d_data=%08x d_error=%u intg_error=%u coverage=%x malformed=%u backpressure_cycles=%lu response_delay_cycles=%lu\n",
                top.done_o, top.oracle_violation_o, top.observed_d_data_o,
                top.observed_d_error_o, top.observed_intg_error_o, top.action_coverage_o,
                malformed ? 1 : 0, backpressure_cycles, response_delay_cycles);
    return top.done_o ? 0 : 1;
}
