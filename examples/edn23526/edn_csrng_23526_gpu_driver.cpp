// CPU reference driver for edn_csrng_23526_gpu_tb.
#include "Vedn_csrng_23526_gpu_tb.h"
#include "Vedn_csrng_23526_gpu_tb___024root.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

static void eval(Vedn_csrng_23526_gpu_tb& top, unsigned char clk) {
    top.clk_i = clk;
    top.eval();
}

static void cycle(Vedn_csrng_23526_gpu_tb& top) {
    eval(top, 1);
    eval(top, 0);
}

static bool load_state(Vedn_csrng_23526_gpu_tb& top, const char* path) {
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

int main(int argc, char** argv) {
    const char* dump_path = nullptr;
    bool inject_error = false;
    bool ready = true;
    const char* checkpoint_path = nullptr;
    bool one_eval = false;
    for (int index = 1; index < argc; ++index) {
        const std::string arg(argv[index]);
        if (arg == "--dump-state" && index + 1 < argc) {
            dump_path = argv[++index];
        } else if (arg == "--error-ack") {
            inject_error = true;
        } else if (arg == "--backpressure") {
            ready = false;
        } else if (arg == "--checkpoint" && index + 1 < argc) {
            checkpoint_path = argv[++index];
        } else if (arg == "--one-eval") {
            one_eval = true;
        } else {
            std::fprintf(
                stderr,
                "usage: %s [--error-ack] [--backpressure] [--checkpoint PATH] [--one-eval] [--dump-state PATH]\n",
                argv[0]
            );
            return 2;
        }
    }
    if (one_eval && !checkpoint_path) {
        std::fprintf(stderr, "--one-eval requires --checkpoint\n");
        return 2;
    }

    Vedn_csrng_23526_gpu_tb top;
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
        top.rst_ni = 0;
        top.start_i = 0;
        top.inject_error_i = inject_error;
        top.csrng_ready_i = ready;
        eval(top, 0);
        cycle(top);
        cycle(top);

        top.rst_ni = 1;
        top.start_i = 1;
        int drive_cycles = 0;
        cycle(top);
        ++drive_cycles;
        top.start_i = 0;
        while (!top.done_o) {
            cycle(top);
            ++drive_cycles;
        }
        if (dump_path) {
            std::ofstream out(dump_path, std::ios::binary);
            out.write(reinterpret_cast<const char*>(top.rootp), sizeof(*top.rootp));
        }
        std::printf("RESULT done=%u protocol_violation=%u valid_after_error=%u valid_seen=%u coverage=%x drive_cycles=%d error=%u backpressure=%u\n",
                    top.done_o, top.protocol_violation_o, top.valid_after_error_o,
                    top.csrng_req_valid_seen_o, top.action_coverage_o, drive_cycles,
                    inject_error ? 1 : 0, ready ? 0 : 1);
        return top.done_o ? 0 : 1;
    }

    if (dump_path) {
        std::ofstream out(dump_path, std::ios::binary);
        out.write(reinterpret_cast<const char*>(top.rootp), sizeof(*top.rootp));
    }

    std::printf(
        "RESULT done=%u protocol_violation=%u valid_after_error=%u valid_seen=%u coverage=%x drive_cycles=%d error=%u backpressure=%u\n",
        top.done_o,
        top.protocol_violation_o,
        top.valid_after_error_o,
        top.csrng_req_valid_seen_o,
        top.action_coverage_o,
        1,
        inject_error ? 1 : 0,
        ready ? 0 : 1
    );
    return top.done_o ? 0 : 1;
}
