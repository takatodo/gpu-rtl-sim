/**
 * vlgpugen — Verilator merged.ll → NVPTX GPU kernel generator.
 *
 * Replaces gen_vl_gpu_kernel.py (Phase 3 of C++ pass migration).
 *
 * Analysis layer  (always runs):
 *   - findEvalFunction, collectReachable, isRuntimeFunction  (mirrors Python)
 *   - detectVlSymsOffset via C++ regex on raw .ll text       (same as Python)
 *
 * Generation layer (activated by --out <path> --storage-size=N):
 *   - stub runtime functions and extern calls
 *   - remove host-only globals (vtable, typeinfo, annotations)
 *   - inject @fake_syms_buf, @vl_eval_batch_gpu, and resident patch schedule kernels
 *   - retarget module to NVPTX and write output .ll
 *
 * Usage:
 *   vlgpugen <merged.ll>                               # analysis only
 *   vlgpugen <merged.ll> --analyze-phases [--analyze-phases-json=path]
 *                                                        # Phase B: ico/nba (+ optional JSON)
 *   vlgpugen <merged.ll> --storage-size=N --out=... [--kernel-split=phases]
 *            [--kernel-manifest-out=path] [--kernel-probe-act-sequent-chunk-size=N]
 *                                                        # optional phase batch kernels
 *
 * Build:
 *   make -C src/passes
 */

#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/DenseSet.h"
#include "llvm/ADT/SmallPtrSet.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalAlias.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Type.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Transforms/Utils/Cloning.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/InitLLVM.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/raw_ostream.h"

#include <algorithm>
#include <optional>
#include <regex>
#include <string>
#include <utility>

#include "llvm/ADT/ArrayRef.h"

#include <cctype>

using namespace llvm;

static cl::opt<std::string> InputFilename(cl::Positional, cl::desc("<merged.ll>"), cl::init(""));
static cl::opt<uint64_t> StorageSize("storage-size", cl::desc("sizeof(root struct) in bytes"), cl::init(0));
static cl::opt<std::string> OutFile("out", cl::desc("Output .ll (enables generation mode)"), cl::init(""));
static cl::opt<std::string> Sm("sm", cl::desc("PTX GPU arch label"), cl::init("sm_89"));
static cl::opt<bool> Quiet("q", cl::desc("Minimal output"), cl::init(false));
static cl::opt<bool> AnalyzePhases(
    "analyze-phases",
    cl::desc("Phase B: report ___ico_sequent / ___nba_* reachability from eval, then exit"),
    cl::init(false));
static cl::opt<std::string> AnalyzePhasesJson(
    "analyze-phases-json",
    cl::desc("With --analyze-phases, write machine-readable report to this path (UTF-8 JSON)"),
    cl::value_desc("path"),
    cl::init(""));
static cl::opt<bool> NoDeclRuntimeMerge(
    "no-decl-runtime-merge",
    cl::desc("Phase E: disable decl-callee expansion of runtime function set (default: merge on)"),
    cl::init(false));
static cl::opt<std::string> KernelSplit(
    "kernel-split",
    cl::desc("Generation: if 'phases', emit vl_ico_batch_gpu, vl_nba_comb_batch_gpu, "
             "vl_nba_sequent_batch_gpu (lexicographic callee order) in addition to vl_eval_batch_gpu"),
    cl::value_desc("mode"),
    cl::init(""));
static cl::opt<std::string> KernelManifestOut(
    "kernel-manifest-out",
    cl::desc("With --kernel-split=phases, write emitted split-kernel order to this path (UTF-8 JSON)"),
    cl::value_desc("path"),
    cl::init(""));
static cl::opt<unsigned> KernelProbeActSequentChunkSize(
    "kernel-probe-act-sequent-chunk-size",
    cl::desc("With --kernel-split=phases, also emit non-launch probe kernels that chunk reachable ___act_sequent callees by N, preserving eval_act trigger guards when available"),
    cl::value_desc("N"),
    cl::init(0));
static cl::opt<std::string> ClassifierReportOut(
    "classifier-report-out",
    cl::desc("Write a machine-readable GPU/runtime placement report to this path (UTF-8 JSON)"),
    cl::value_desc("path"),
    cl::init(""));

static constexpr StringLiteral NVPTX_TRIPLE    = "nvptx64-nvidia-cuda";
static constexpr StringLiteral NVPTX_DATALAYOUT = "e-i64:64-i128:128-v16:16-v32:32-n16:32:64";

// ---------------------------------------------------------------------------
// Analysis: isRuntimeFunction — mirrors vl_runtime_filter.py
// ---------------------------------------------------------------------------

static void functionToString(const Function &F, std::string &Out) {
    raw_string_ostream OS(Out);
    F.print(OS);
}

static const char *matchForceIncludePattern(StringRef Name) {
    static const char *Patterns[] = {"___ico_sequent", "___nba_comb"};
    for (const char *Pattern : Patterns)
        if (Name.contains(Pattern))
            return Pattern;
    return nullptr;
}

static bool isForceInclude(StringRef Name) {
    return matchForceIncludePattern(Name) != nullptr;
}

static bool isRootLocalDesignFunction(StringRef Name) {
    return Name.contains("___024root___");
}

static const char *matchRuntimePrefix(StringRef Name) {
    static const char *Prefixes[] = {
        "_ZN9Verilated",  "_ZNK9Verilated",
        "_ZN16VerilatedContext", "_ZNK16VerilatedContext",
        "_ZN14VerilatedModel",   "_ZNK14VerilatedModel",
        "_ZN9VlDeleter",  "_ZNSt", "_ZSt",
        "_Z13sc_time_stamp", "_Z15vl_time_stamp", "__cxa_", "_ZTHN",
    };
    for (const char *P : Prefixes)
        if (Name.starts_with(P))
            return P;
    return nullptr;
}

struct ClassificationReason {
    std::string Category;
    std::string Detail;
};

static std::optional<ClassificationReason> classifyRuntimeReason(const Function &F,
                                                                const std::string &BodyStr) {
    StringRef Name = F.getName();
    if (isForceInclude(Name))
        return std::nullopt;
    if (isRootLocalDesignFunction(Name))
        return std::nullopt;
    if (const char *Prefix = matchRuntimePrefix(Name))
        return ClassificationReason{"runtime_prefix", Prefix};
    if (BodyStr.find("@_ZGVZ") != std::string::npos)
        return ClassificationReason{"runtime_static_guard", "@_ZGVZ"};
    if (BodyStr.find("VerilatedSyms") != std::string::npos)
        return ClassificationReason{"runtime_syms_reference", "VerilatedSyms"};
    if (BodyStr.find("_gpu_cov_tb__Syms") != std::string::npos)
        return ClassificationReason{"runtime_syms_reference", "_gpu_cov_tb__Syms"};
    return std::nullopt;
}

// ---------------------------------------------------------------------------
// Analysis: detectVlSymsOffset mirrors detect_vlsyms_offset().
// Prefer source-like line scanning because whole-file regex backtracking can
// be unstable on large Verilator IR dumps.
// ---------------------------------------------------------------------------

static std::optional<int64_t> metadataI64Offset(const std::string &Text,
                                                const std::string &MetadataId) {
    std::string Needle = "!" + MetadataId + " =";
    size_t Pos = Text.find(Needle);
    if (Pos != 0) {
        Pos = Text.find("\n" + Needle);
        if (Pos == std::string::npos)
            return std::nullopt;
        ++Pos;
    }
    size_t End = Text.find('\n', Pos);
    std::string Line = Text.substr(Pos, End == std::string::npos ? std::string::npos : End - Pos);
    size_t I64 = Line.rfind("i64");
    if (I64 == std::string::npos)
        return std::nullopt;
    I64 += 3;
    while (I64 < Line.size() && std::isspace(static_cast<unsigned char>(Line[I64])))
        ++I64;
    size_t Start = I64;
    while (I64 < Line.size() && std::isdigit(static_cast<unsigned char>(Line[I64])))
        ++I64;
    if (Start == I64)
        return std::nullopt;
    return std::stoll(Line.substr(Start, I64 - Start));
}

static std::optional<std::string> assignedValueName(StringRef LineRef) {
    std::string Line = LineRef.str();
    size_t Start = Line.find_first_not_of(" \t");
    if (Start == std::string::npos || Line[Start] != '%')
        return std::nullopt;
    size_t Eq = Line.find('=', Start);
    if (Eq == std::string::npos)
        return std::nullopt;
    size_t End = Line.find_last_not_of(" \t", Eq - 1);
    if (End == std::string::npos || End < Start)
        return std::nullopt;
    return Line.substr(Start, End - Start + 1);
}

static std::optional<std::string> tbaaMetadataId(StringRef LineRef) {
    std::string Line = LineRef.str();
    size_t Pos = Line.find("!tbaa !");
    if (Pos == std::string::npos)
        return std::nullopt;
    Pos += 7;
    size_t Start = Pos;
    while (Pos < Line.size() && std::isdigit(static_cast<unsigned char>(Line[Pos])))
        ++Pos;
    if (Start == Pos)
        return std::nullopt;
    return Line.substr(Start, Pos - Start);
}

static bool symsGepUsesValue(const std::string &Text, const std::string &ValueName) {
    std::string Needle = "ptr " + ValueName;
    size_t Pos = 0;
    while ((Pos = Text.find(Needle, Pos)) != std::string::npos) {
        size_t LineStart = Text.rfind('\n', Pos);
        LineStart = (LineStart == std::string::npos) ? 0 : LineStart + 1;
        size_t LineEnd = Text.find('\n', Pos);
        std::string Line = Text.substr(
            LineStart, LineEnd == std::string::npos ? std::string::npos : LineEnd - LineStart);
        if (Line.find("getelementptr inbounds %class.") != std::string::npos &&
            Line.find("__Syms") != std::string::npos)
            return true;
        Pos += Needle.size();
    }
    return false;
}

static std::optional<int64_t> detectVlSymsOffset(StringRef FileText) {
    std::string Text = FileText.str();
    std::smatch M;

    size_t LineStart = 0;
    while (LineStart < Text.size()) {
        size_t LineEnd = Text.find('\n', LineStart);
        StringRef Line(Text.data() + LineStart,
                       (LineEnd == std::string::npos ? Text.size() : LineEnd) - LineStart);
        size_t NextStart = (LineEnd == std::string::npos) ? Text.size() : LineEnd + 1;
        if (!Line.contains("getelementptr inbounds %class.") || !Line.contains("___024root")) {
            LineStart = NextStart;
            continue;
        }
        auto GepName = assignedValueName(Line);
        if (!GepName) {
            LineStart = NextStart;
            continue;
        }
        size_t LoadEnd = Text.find('\n', NextStart);
        StringRef LoadLine(Text.data() + NextStart,
                           (LoadEnd == std::string::npos ? Text.size() : LoadEnd) - NextStart);
        std::string PtrNeedle = "ptr " + *GepName;
        if (!LoadLine.contains("load ptr") || !LoadLine.contains(StringRef(PtrNeedle))) {
            LineStart = NextStart;
            continue;
        }
        auto LoadedValue = assignedValueName(LoadLine);
        if (!LoadedValue || !symsGepUsesValue(Text, *LoadedValue)) {
            LineStart = NextStart;
            continue;
        }
        if (auto TbaaId = tbaaMetadataId(LoadLine)) {
            if (auto Offset = metadataI64Offset(Text, *TbaaId))
                return Offset;
        }
        LineStart = NextStart;
    }

    std::regex AnyPtrRe(R"(^(!(\d+))\s*=\s*!\{!"any pointer")",
                        std::regex_constants::multiline);
    if (!std::regex_search(Text, M, AnyPtrRe)) return std::nullopt;
    const std::string AnyId = M.str(2);
    std::string RootPat = R"(^!\d+\s*=\s*!\{!"[^"]*_024root".*?!)"
                          + AnyId + R"(,\s*i64\s+(\d+))";
    std::regex RootRe(RootPat, std::regex_constants::multiline);
    if (std::regex_search(Text, M, RootRe))
        return std::stoll(M.str(1));
    return std::nullopt;
}

static uint64_t detectSymsBufferSize(StringRef FileText, uint64_t Minimum = 4096) {
    std::string Text = FileText.str();
    uint64_t Size = Minimum;
    std::regex DerefRe(R"(dereferenceable\((\d+)\))");
    size_t LineStart = 0;
    while (LineStart < Text.size()) {
        size_t LineEnd = Text.find('\n', LineStart);
        std::string Line = Text.substr(
            LineStart, (LineEnd == std::string::npos ? Text.size() : LineEnd) - LineStart);
        LineStart = (LineEnd == std::string::npos) ? Text.size() : LineEnd + 1;
        if (Line.find("__Syms") == std::string::npos)
            continue;
        for (std::sregex_iterator Dit(Line.begin(), Line.end(), DerefRe), DEnd; Dit != DEnd;
             ++Dit)
            Size = std::max<uint64_t>(Size, std::stoull((*Dit).str(1)));
    }
    return Size;
}

// ---------------------------------------------------------------------------
// Analysis: eval function + reachable BFS
// ---------------------------------------------------------------------------

static Function *findEvalFunction(Module &M) {
    for (auto &F : M) {
        if (F.isDeclaration()) continue;
        StringRef N = F.getName();
        if (N.contains("___024root___eval") && !N.contains("___eval_"))
            return &F;
    }
    for (auto &F : M) {
        if (F.isDeclaration()) continue;
        if (F.getName().contains("_eval") && F.getFunctionType()->getNumParams() >= 1)
            return &F;
    }
    return nullptr;
}

static bool hostLikeDecl(const Function *F) {
    if (!F || !F->isDeclaration())
        return false;
    StringRef N = F->getName();
    if (N.starts_with("llvm."))
        return false;
    static const char *Pfx[] = {
        "_ZN9Verilated",  "_ZNK9Verilated", "_ZN16VerilatedContext",
        "_ZNK16VerilatedContext", "_ZN14VerilatedModel", "_ZNK14VerilatedModel",
        "_ZN9VlDeleter",  "_ZNSt", "_ZSt", "__cxa_", "_Z13sc_time_stamp",
        "_Z15vl_time_stamp", "_ZTHN"};
    for (const char *P : Pfx)
        if (N.starts_with(P))
            return true;
    return false;
}

/// Phase E: any function in Reach that directly calls a host-like declare is treated as runtime
/// (conservative; complements body-string isRuntimeFunction).
static void mergeRuntimeViaDeclCalls(const DenseSet<Function *> &Reach,
                                     DenseSet<Function *> &RuntimeFuncs,
                                     DenseMap<Function *, ClassificationReason> &Reasons) {
    bool Changed = true;
    while (Changed) {
        Changed = false;
        for (Function *F : Reach) {
            if (RuntimeFuncs.count(F))
                continue;
            if (isRootLocalDesignFunction(F->getName()))
                continue;
            for (BasicBlock &BB : *F)
                for (Instruction &I : BB)
                    if (auto *CB = dyn_cast<CallBase>(&I))
                        if (auto *Callee = dyn_cast<Function>(
                                CB->getCalledOperand()->stripPointerCasts()))
                            if (Callee->isDeclaration() && hostLikeDecl(Callee)) {
                                RuntimeFuncs.insert(F);
                                Reasons[F] = {"decl_host_callee", Callee->getName().str()};
                                Changed = true;
                                goto NextF;
                            }
        NextF:;
        }
    }
}

static ClassificationReason classifyGpuReason(const Function &F) {
    if (const char *Pattern = matchForceIncludePattern(F.getName()))
        return {"force_include", Pattern};
    return {"gpu_reachable", "reachable_from_eval"};
}

static void reportAnalyzePhases(Module &M, const DenseSet<Function *> &Reach) {
    outs() << "analyze-phases (reachable from _eval):\n";
    const char *Subs[] = {"___ico_sequent", "___nba_comb", "___nba_sequent"};
    for (const char *Sub : Subs) {
        bool Any = false;
        for (Function &F : M) {
            if (F.isDeclaration())
                continue;
            if (!F.getName().contains(Sub))
                continue;
            Any = true;
            outs() << "  @" << F.getName() << "  reachable=" << Reach.count(&F) << "\n";
        }
        if (!Any)
            outs() << "  (" << Sub << " — no definition in module)\n";
    }
}

static void writeJsonString(raw_ostream &OS, StringRef S) {
    OS << '"';
    for (unsigned char C : S) {
        switch (C) {
        case '"':
            OS << "\\\"";
            break;
        case '\\':
            OS << "\\\\";
            break;
        case '\b':
            OS << "\\b";
            break;
        case '\f':
            OS << "\\f";
            break;
        case '\n':
            OS << "\\n";
            break;
        case '\r':
            OS << "\\r";
            break;
        case '\t':
            OS << "\\t";
            break;
        default:
            if (C < 0x20) {
                static const char *Hex = "0123456789abcdef";
                OS << "\\u00" << Hex[(C >> 4) & 0xf] << Hex[C & 0xf];
            } else {
                OS << char(C);
            }
        }
    }
    OS << '"';
}

/// Phase B: JSON for tooling (kernel-split, CI). Requires --analyze-phases.
static int writeAnalyzePhasesJson(Module &M, const DenseSet<Function *> &Reach, Function *EvalFn,
                                  const std::string &Path) {
    struct PhaseKey {
        const char *Substr;
        const char *JsonId;
    };
    static const PhaseKey Phases[] = {
        {"___ico_sequent", "ico_sequent"},
        {"___nba_comb", "nba_comb"},
        {"___nba_sequent", "nba_sequent"},
    };
    const size_t NumPhases = sizeof(Phases) / sizeof(Phases[0]);

    std::error_code EC;
    raw_fd_ostream OS(Path, EC, sys::fs::OF_Text);
    if (EC) {
        errs() << "error: cannot open --analyze-phases-json " << Path << ": " << EC.message()
               << "\n";
        return 1;
    }

    OS << "{\n";
    OS << "  \"schema_version\": 1,\n  \"eval_function\": ";
    writeJsonString(OS, EvalFn->getName());
    OS << ",\n  \"phases\": {\n";

    for (size_t Pi = 0; Pi < NumPhases; ++Pi) {
        const char *Sub = Phases[Pi].Substr;
        if (Pi > 0)
            OS << ",\n";
        OS << "    ";
        writeJsonString(OS, Phases[Pi].JsonId);
        OS << ": {\n      \"any_defined_in_module\": ";
        bool AnyDef = false;
        bool AnyReach = false;
        SmallVector<std::pair<std::string, bool>, 8> Rows;
        for (Function &F : M) {
            if (F.isDeclaration())
                continue;
            if (!F.getName().contains(Sub))
                continue;
            AnyDef = true;
            bool R = Reach.count(&F);
            if (R)
                AnyReach = true;
            Rows.push_back({F.getName().str(), R});
        }
        OS << (AnyDef ? "true" : "false");
        OS << ",\n      \"any_reachable_from_eval\": ";
        OS << (AnyReach ? "true" : "false");
        OS << ",\n      \"functions\": [";
        for (unsigned i = 0; i < Rows.size(); ++i) {
            if (i > 0)
                OS << ',';
            OS << "\n        {\"name\": ";
            writeJsonString(OS, Rows[i].first);
            OS << ", \"reachable\": " << (Rows[i].second ? "true" : "false") << "}";
        }
        OS << "\n      ]\n    }";
    }
    OS << "\n  }\n}\n";
    OS.flush();
    outs() << "analyze-phases-json: " << Path << "\n";
    return 0;
}

static int writeClassifierReportJson(
    const DenseSet<Function *> &Reach,
    const DenseSet<Function *> &RuntimeFuncs,
    const DenseMap<Function *, ClassificationReason> &RuntimeReasons,
    Function *EvalFn,
    std::optional<int64_t> VlOff,
    bool DeclRuntimeMergeEnabled,
    const std::string &Path) {
    std::error_code EC;
    raw_fd_ostream OS(Path, EC, sys::fs::OF_Text);
    if (EC) {
        errs() << "error: cannot open --classifier-report-out " << Path << ": "
               << EC.message() << "\n";
        return 1;
    }

    struct Row {
        std::string Name;
        std::string Placement;
        ClassificationReason Reason;
    };

    SmallVector<Row, 64> Rows;
    Rows.reserve(Reach.size());
    for (Function *F : Reach) {
        Row R;
        R.Name = F->getName().str();
        if (RuntimeFuncs.count(F)) {
            R.Placement = "runtime";
            auto It = RuntimeReasons.find(F);
            if (It != RuntimeReasons.end())
                R.Reason = It->second;
            else
                R.Reason = {"runtime_unknown", ""};
        } else {
            R.Placement = "gpu";
            R.Reason = classifyGpuReason(*F);
        }
        Rows.push_back(std::move(R));
    }
    llvm::sort(Rows, [](const Row &A, const Row &B) { return A.Name < B.Name; });

    OS << "{\n";
    OS << "  \"schema_version\": 1,\n";
    OS << "  \"eval_function\": ";
    writeJsonString(OS, EvalFn->getName());
    OS << ",\n";
    OS << "  \"decl_runtime_merge_enabled\": "
       << (DeclRuntimeMergeEnabled ? "true" : "false") << ",\n";
    OS << "  \"vl_symsp_offset\": ";
    if (VlOff)
        OS << *VlOff;
    else
        OS << "null";
    OS << ",\n";
    OS << "  \"counts\": {\n";
    OS << "    \"reachable\": " << Reach.size() << ",\n";
    OS << "    \"gpu\": " << (Reach.size() - RuntimeFuncs.size()) << ",\n";
    OS << "    \"runtime\": " << RuntimeFuncs.size() << "\n";
    OS << "  },\n";
    OS << "  \"functions\": [";
    for (size_t I = 0; I < Rows.size(); ++I) {
        if (I > 0)
            OS << ',';
        OS << "\n    {\n";
        OS << "      \"name\": ";
        writeJsonString(OS, Rows[I].Name);
        OS << ",\n      \"placement\": ";
        writeJsonString(OS, Rows[I].Placement);
        OS << ",\n      \"reason\": ";
        writeJsonString(OS, Rows[I].Reason.Category);
        if (!Rows[I].Reason.Detail.empty()) {
            OS << ",\n      \"detail\": ";
            writeJsonString(OS, Rows[I].Reason.Detail);
        }
        OS << "\n    }";
    }
    OS << "\n  ]\n}\n";
    OS.flush();
    outs() << "classifier-report-json: " << Path << "\n";
    return 0;
}

struct KernelManifestEntry {
    std::string Selector;
    std::string KernelName;
};

static int writeKernelManifestJson(ArrayRef<KernelManifestEntry> LaunchKernels,
                                   StringRef SplitMode, const std::string &Path,
                                   ArrayRef<KernelManifestEntry> ProbeKernels = {}) {
    std::error_code EC;
    raw_fd_ostream OS(Path, EC, sys::fs::OF_Text);
    if (EC) {
        errs() << "error: cannot open --kernel-manifest-out " << Path << ": "
               << EC.message() << "\n";
        return 1;
    }

    OS << "{\n";
    OS << "  \"schema_version\": 1,\n";
    OS << "  \"kernel_split\": ";
    writeJsonString(OS, SplitMode);
    OS << ",\n  \"kernels\": [";
    size_t Written = 0;
    auto WriteKernelRow = [&](const KernelManifestEntry &Entry) {
        if (Written++ > 0)
            OS << ',';
        OS << "\n    {\"name\": ";
        writeJsonString(OS, Entry.KernelName);
        OS << ", \"selector\": ";
        writeJsonString(OS, Entry.Selector);
        OS << "}";
    };
    for (const auto &Entry : LaunchKernels)
        WriteKernelRow(Entry);
    for (const auto &Entry : ProbeKernels)
        WriteKernelRow(Entry);
    OS << "\n  ],\n  \"launch_sequence\": [";
    for (size_t I = 0; I < LaunchKernels.size(); ++I) {
        if (I > 0)
            OS << ',';
        OS << "\n    ";
        writeJsonString(OS, LaunchKernels[I].KernelName);
    }
    if (!ProbeKernels.empty()) {
        OS << "\n  ],\n  \"probe_kernels\": [";
        for (size_t I = 0; I < ProbeKernels.size(); ++I) {
            if (I > 0)
                OS << ',';
            OS << "\n    ";
            writeJsonString(OS, ProbeKernels[I].KernelName);
        }
    }
    OS << "\n  ]\n}\n";
    OS.flush();
    outs() << "kernel-manifest-json: " << Path << "\n";
    return 0;
}

struct TriggerMaskTest {
    GetElementPtrInst *TriggerPtr = nullptr;
    IntegerType *LoadTy = nullptr;
    APInt Mask = APInt(64, 0);
    CmpInst::Predicate Predicate = CmpInst::ICMP_EQ;
    Align LoadAlign = Align(1);
};

struct GuardedSegment {
    TriggerMaskTest Guard;
    SmallVector<BasicBlock *, 8> RegionBlocks;
    Function *Callee = nullptr;
    BasicBlock *JoinBlock = nullptr;
    bool ExecuteOnTrue = false;
};

static Function *findReachableNamedFunction(Module &M, const DenseSet<Function *> &Reach,
                                            StringRef NameSubstr) {
    for (Function &F : M) {
        if (F.isDeclaration())
            continue;
        if (!Reach.count(&F))
            continue;
        if (F.getName().contains(NameSubstr))
            return &F;
    }
    return nullptr;
}

static bool isZeroIntConstant(const Value *V) {
    if (auto *CI = dyn_cast<ConstantInt>(V))
        return CI->isZero();
    return false;
}

static bool parseTriggerMaskTest(Value *Cond, TriggerMaskTest &Out) {
    auto *Cmp = dyn_cast<ICmpInst>(Cond);
    if (!Cmp)
        return false;
    if (Cmp->getPredicate() != CmpInst::ICMP_EQ &&
        Cmp->getPredicate() != CmpInst::ICMP_NE)
        return false;

    Value *Masked = nullptr;
    if (isZeroIntConstant(Cmp->getOperand(0)))
        Masked = Cmp->getOperand(1);
    else if (isZeroIntConstant(Cmp->getOperand(1)))
        Masked = Cmp->getOperand(0);
    else
        return false;

    auto *And = dyn_cast<BinaryOperator>(Masked);
    if (!And || And->getOpcode() != Instruction::And)
        return false;

    Value *MaskV = And->getOperand(0);
    Value *LoadV = And->getOperand(1);
    if (!isa<ConstantInt>(MaskV))
        std::swap(MaskV, LoadV);
    auto *MaskC = dyn_cast<ConstantInt>(MaskV);
    auto *Load = dyn_cast<LoadInst>(LoadV);
    if (!MaskC || !Load)
        return false;
    auto *LoadTy = dyn_cast<IntegerType>(Load->getType());
    if (!LoadTy)
        return false;

    auto *TriggerPtr = dyn_cast<GetElementPtrInst>(Load->getPointerOperand());
    if (!TriggerPtr || !TriggerPtr->hasAllConstantIndices())
        return false;
    if (!isa<Argument>(TriggerPtr->getPointerOperand()))
        return false;

    Out.TriggerPtr = TriggerPtr;
    Out.LoadTy = LoadTy;
    Out.Mask = MaskC->getValue();
    Out.Predicate = Cmp->getPredicate();
    Out.LoadAlign = Load->getAlign();
    return true;
}

static bool isTrivialReturnBlock(BasicBlock *BB) {
    auto *Ret = dyn_cast<ReturnInst>(BB->getTerminator());
    if (!Ret)
        return false;
    for (Instruction &I : *BB) {
        if (&I == Ret)
            continue;
        if (auto *CB = dyn_cast<CallBase>(&I)) {
            if (Function *Callee = CB->getCalledFunction()) {
                if (Callee->getName().starts_with("llvm.lifetime."))
                    continue;
            }
        }
        return false;
    }
    return true;
}

static bool matchSingleCallBlock(BasicBlock *BB, BasicBlock *ExpectedNext, Function *&CalleeOut) {
    auto *Br = dyn_cast<BranchInst>(BB->getTerminator());
    if (!Br || Br->isConditional() || Br->getSuccessor(0) != ExpectedNext)
        return false;

    Function *Callee = nullptr;
    for (Instruction &I : *BB) {
        if (&I == Br)
            continue;
        auto *CB = dyn_cast<CallBase>(&I);
        if (!CB || Callee)
            return false;
        auto *Fn = dyn_cast<Function>(CB->getCalledOperand()->stripPointerCasts());
        if (!Fn || Fn->isDeclaration())
            return false;
        Callee = Fn;
    }
    if (!Callee)
        return false;
    CalleeOut = Callee;
    return true;
}

static bool collectRegionBlocks(BasicBlock *Start, BasicBlock *Join, BasicBlock *EntryPred,
                                SmallVectorImpl<BasicBlock *> &Order) {
    SmallVector<BasicBlock *, 8> Stack;
    SmallPtrSet<BasicBlock *, 16> RegionSet;
    Stack.push_back(Start);

    while (!Stack.empty()) {
        BasicBlock *BB = Stack.pop_back_val();
        if (BB == Join)
            continue;
        if (!RegionSet.insert(BB).second)
            continue;
        auto *TI = BB->getTerminator();
        for (unsigned I = 0; I < TI->getNumSuccessors(); ++I)
            Stack.push_back(TI->getSuccessor(I));
    }

    if (RegionSet.empty())
        return false;

    bool HasExitToJoin = false;
    Function *Parent = Start->getParent();
    for (BasicBlock &BB : *Parent) {
        if (!RegionSet.count(&BB))
            continue;

        if (&BB == Start) {
            for (BasicBlock *Pred : predecessors(&BB))
                if (Pred != EntryPred && !RegionSet.count(Pred))
                    return false;
        } else {
            for (BasicBlock *Pred : predecessors(&BB))
                if (!RegionSet.count(Pred))
                    return false;
        }

        auto *TI = BB.getTerminator();
        for (unsigned I = 0; I < TI->getNumSuccessors(); ++I) {
            BasicBlock *Succ = TI->getSuccessor(I);
            if (Succ == Join) {
                HasExitToJoin = true;
                continue;
            }
            if (!RegionSet.count(Succ))
                return false;
        }

        Order.push_back(&BB);
    }

    return HasExitToJoin;
}

static bool regionUsesOnlyRootArg(const SmallVectorImpl<BasicBlock *> &RegionBlocks,
                                  Argument *RootArg) {
    SmallPtrSet<const Instruction *, 32> RegionInsts;
    for (BasicBlock *BB : RegionBlocks)
        for (Instruction &I : *BB)
            RegionInsts.insert(&I);

    for (BasicBlock *BB : RegionBlocks) {
        for (Instruction &I : *BB) {
            for (Value *Op : I.operands()) {
                if (isa<Constant>(Op) || isa<BasicBlock>(Op))
                    continue;
                if (Op == RootArg)
                    continue;
                auto *Inst = dyn_cast<Instruction>(Op);
                if (Inst && RegionInsts.count(Inst))
                    continue;
                return false;
            }
        }
    }

    return true;
}

static bool matchGuardedRegion(BasicBlock *ActiveBB, BasicBlock *JoinBB, BasicBlock *EntryPred,
                               GuardedSegment &OutSeg) {
    SmallVector<BasicBlock *, 8> RegionBlocks;
    if (!collectRegionBlocks(ActiveBB, JoinBB, EntryPred, RegionBlocks))
        return false;
    if (!regionUsesOnlyRootArg(RegionBlocks, &*ActiveBB->getParent()->arg_begin()))
        return false;

    Function *Callee = nullptr;
    if (RegionBlocks.size() == 1 && matchSingleCallBlock(ActiveBB, JoinBB, Callee))
        OutSeg.Callee = Callee;
    OutSeg.RegionBlocks = std::move(RegionBlocks);
    OutSeg.JoinBlock = JoinBB;
    return true;
}

static bool extractGuardedSegments(Function &EvalNba,
                                   SmallVectorImpl<GuardedSegment> &Out) {
    BasicBlock *Cur = &EvalNba.getEntryBlock();
    SmallPtrSet<BasicBlock *, 16> Seen;

    while (true) {
        if (!Seen.insert(Cur).second)
            return false;
        if (isTrivialReturnBlock(Cur))
            return !Out.empty();

        auto *Br = dyn_cast<BranchInst>(Cur->getTerminator());
        if (!Br || !Br->isConditional())
            return false;

        TriggerMaskTest Guard;
        if (!parseTriggerMaskTest(Br->getCondition(), Guard))
            return false;

        BasicBlock *TrueBB = Br->getSuccessor(0);
        BasicBlock *FalseBB = Br->getSuccessor(1);
        BasicBlock *Next = nullptr;
        GuardedSegment Seg;
        Seg.Guard = Guard;

        if (matchGuardedRegion(TrueBB, FalseBB, Cur, Seg)) {
            Next = FalseBB;
            Seg.ExecuteOnTrue = true;
        } else if (matchGuardedRegion(FalseBB, TrueBB, Cur, Seg)) {
            Next = TrueBB;
            Seg.ExecuteOnTrue = false;
        } else {
            return false;
        }

        Out.push_back(std::move(Seg));
        Cur = Next;
    }
}

static Value *cloneConstantIndexGEP(IRBuilder<> &B, GetElementPtrInst *GEP, Value *BasePtr) {
    SmallVector<Value *, 8> Indices;
    for (unsigned I = 1; I < GEP->getNumOperands(); ++I) {
        auto *Idx = dyn_cast<ConstantInt>(GEP->getOperand(I));
        if (!Idx)
            return nullptr;
        Indices.push_back(Idx);
    }
    return GEP->isInBounds()
               ? B.CreateInBoundsGEP(GEP->getSourceElementType(), BasePtr, Indices, "trigger_gep")
               : B.CreateGEP(GEP->getSourceElementType(), BasePtr, Indices, "trigger_gep");
}

static Function *createGuardedSegmentWrapper(Module &M, StringRef WrapperName,
                                             const GuardedSegment &Seg) {
    LLVMContext &Ctx = M.getContext();
    auto *PtrTy = cast<PointerType>(Seg.Guard.TriggerPtr->getPointerOperand()->getType());
    auto *FTy = FunctionType::get(Type::getVoidTy(Ctx), {PtrTy}, false);
    auto *Wrapper =
        Function::Create(FTy, GlobalValue::InternalLinkage, WrapperName, &M);
    Wrapper->getArg(0)->setName("state_ptr");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Wrapper);
    auto *ExitBB = BasicBlock::Create(Ctx, "exit", Wrapper);

    IRBuilder<> B(EntryBB);
    Value *TriggerPtr = cloneConstantIndexGEP(B, Seg.Guard.TriggerPtr, Wrapper->getArg(0));
    if (!TriggerPtr) {
        Wrapper->eraseFromParent();
        return nullptr;
    }
    auto *Load = B.CreateAlignedLoad(Seg.Guard.LoadTy, TriggerPtr, Seg.Guard.LoadAlign, "trigger");
    auto *Masked =
        B.CreateAnd(Load, ConstantInt::get(Seg.Guard.LoadTy, Seg.Guard.Mask), "trigger_masked");
    auto *Zero = ConstantInt::get(Seg.Guard.LoadTy, 0);
    auto *Cond = B.CreateICmp(Seg.Guard.Predicate, Masked, Zero, "trigger_cond");
    if (Seg.Callee && Seg.RegionBlocks.size() == 1) {
        auto *CallBB = BasicBlock::Create(Ctx, "call", Wrapper);
        if (Seg.ExecuteOnTrue)
            B.CreateCondBr(Cond, CallBB, ExitBB);
        else
            B.CreateCondBr(Cond, ExitBB, CallBB);

        B.SetInsertPoint(CallBB);
        B.CreateCall(Seg.Callee, {Wrapper->getArg(0)});
        B.CreateBr(ExitBB);
    } else {
        ValueToValueMapTy VMap;
        DenseMap<BasicBlock *, BasicBlock *> BBMap;
        VMap[&*Seg.RegionBlocks.front()->getParent()->arg_begin()] = Wrapper->getArg(0);
        for (BasicBlock *OrigBB : Seg.RegionBlocks) {
            auto *CloneBB = CloneBasicBlock(OrigBB, VMap, ".seg", Wrapper);
            VMap[OrigBB] = CloneBB;
            BBMap[OrigBB] = CloneBB;
        }

        BasicBlock *StartBB = BBMap[Seg.RegionBlocks.front()];
        if (Seg.ExecuteOnTrue)
            B.CreateCondBr(Cond, StartBB, ExitBB);
        else
            B.CreateCondBr(Cond, ExitBB, StartBB);

        for (BasicBlock *OrigBB : Seg.RegionBlocks) {
            BasicBlock *CloneBB = BBMap[OrigBB];
            for (Instruction &I : *CloneBB)
                RemapInstruction(&I, VMap,
                                 RF_NoModuleLevelChanges | RF_IgnoreMissingLocals);

            auto *OrigBr = dyn_cast<BranchInst>(OrigBB->getTerminator());
            auto *CloneBr = dyn_cast<BranchInst>(CloneBB->getTerminator());
            if (!OrigBr || !CloneBr) {
                Wrapper->eraseFromParent();
                return nullptr;
            }

            IRBuilder<> BodyB(CloneBB);
            if (OrigBr->isConditional()) {
                Value *CloneCond = CloneBr->getCondition();
                CloneBr->eraseFromParent();
                auto mapSucc = [&](BasicBlock *Succ) -> BasicBlock * {
                    return Succ == Seg.JoinBlock ? ExitBB : BBMap[Succ];
                };
                BodyB.CreateCondBr(CloneCond, mapSucc(OrigBr->getSuccessor(0)),
                                   mapSucc(OrigBr->getSuccessor(1)));
            } else {
                CloneBr->eraseFromParent();
                BasicBlock *Succ = OrigBr->getSuccessor(0);
                BodyB.CreateBr(Succ == Seg.JoinBlock ? ExitBB : BBMap[Succ]);
            }
        }
    }

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();
    return Wrapper;
}

static Function *createTriggerClearWrapper(Module &M, StringRef WrapperName,
                                           const TriggerMaskTest &Guard) {
    LLVMContext &Ctx = M.getContext();
    auto *PtrTy = cast<PointerType>(Guard.TriggerPtr->getPointerOperand()->getType());
    auto *FTy = FunctionType::get(Type::getVoidTy(Ctx), {PtrTy}, false);
    auto *Wrapper =
        Function::Create(FTy, GlobalValue::InternalLinkage, WrapperName, &M);
    Wrapper->getArg(0)->setName("state_ptr");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Wrapper);
    IRBuilder<> B(EntryBB);
    Value *TriggerPtr = cloneConstantIndexGEP(B, Guard.TriggerPtr, Wrapper->getArg(0));
    if (!TriggerPtr) {
        Wrapper->eraseFromParent();
        return nullptr;
    }
    B.CreateAlignedStore(ConstantInt::get(Guard.LoadTy, 0), TriggerPtr, Guard.LoadAlign);
    B.CreateRetVoid();
    return Wrapper;
}

static void collectPhaseReachable(Module &M, const DenseSet<Function *> &Reach,
                                  StringRef NameSubstr, SmallVectorImpl<Function *> &Out);

struct GuardedActCall {
    TriggerMaskTest Guard;
    Function *Callee = nullptr;
    bool ExecuteOnTrue = false;
};

static bool sameGuardedActCallGuard(const GuardedActCall &A, const GuardedActCall &B) {
    return A.Guard.TriggerPtr == B.Guard.TriggerPtr && A.Guard.LoadTy == B.Guard.LoadTy &&
           A.Guard.Mask == B.Guard.Mask && A.Guard.Predicate == B.Guard.Predicate &&
           A.Guard.LoadAlign == B.Guard.LoadAlign && A.ExecuteOnTrue == B.ExecuteOnTrue;
}

static bool collectGuardedActCallsFromEvalAct(Function &EvalAct,
                                              const DenseSet<Function *> &AllowedActFns,
                                              SmallVectorImpl<GuardedActCall> &Out) {
    bool SawAny = false;

    for (BasicBlock &BB : EvalAct) {
        BasicBlock *OnlyPred = nullptr;
        for (BasicBlock *Pred : predecessors(&BB)) {
            if (OnlyPred)
                OnlyPred = nullptr;
            else
                OnlyPred = Pred;
            if (!OnlyPred)
                break;
        }
        auto *PredBr = OnlyPred ? dyn_cast<BranchInst>(OnlyPred->getTerminator()) : nullptr;
        if (!PredBr || !PredBr->isConditional())
            continue;

        TriggerMaskTest Guard;
        if (!parseTriggerMaskTest(PredBr->getCondition(), Guard))
            continue;

        bool ExecuteOnTrue = false;
        if (PredBr->getSuccessor(0) == &BB)
            ExecuteOnTrue = true;
        else if (PredBr->getSuccessor(1) == &BB)
            ExecuteOnTrue = false;
        else
            continue;

        for (Instruction &I : BB) {
            auto *CB = dyn_cast<CallBase>(&I);
            if (!CB)
                continue;
            auto *Callee = dyn_cast<Function>(CB->getCalledOperand()->stripPointerCasts());
            if (!Callee || !AllowedActFns.count(Callee))
                continue;
            Out.push_back({Guard, Callee, ExecuteOnTrue});
            SawAny = true;
        }
    }

    return SawAny;
}

static void collectGuardedActCalls(Module &M, const DenseSet<Function *> &Reach,
                                   const DenseSet<Function *> &AllowedActFns,
                                   SmallVectorImpl<GuardedActCall> &Out) {
    SmallVector<Function *, 16> EvalActFns;
    collectPhaseReachable(M, Reach, "___eval_act", EvalActFns);
    for (Function *F : EvalActFns)
        collectGuardedActCallsFromEvalAct(*F, AllowedActFns, Out);
}

static Function *createGuardedActChunkWrapper(Module &M, StringRef WrapperName,
                                             ArrayRef<GuardedActCall> Calls) {
    if (Calls.empty())
        return nullptr;

    LLVMContext &Ctx = M.getContext();
    auto *PtrTy = cast<PointerType>(Calls.front().Guard.TriggerPtr->getPointerOperand()->getType());
    auto *FTy = FunctionType::get(Type::getVoidTy(Ctx), {PtrTy}, false);
    auto *Wrapper =
        Function::Create(FTy, GlobalValue::InternalLinkage, WrapperName, &M);
    Wrapper->getArg(0)->setName("state_ptr");

    auto *CurBB = BasicBlock::Create(Ctx, "entry", Wrapper);
    IRBuilder<> B(CurBB);

    unsigned GroupIdx = 0;
    for (unsigned Start = 0; Start < Calls.size();) {
        unsigned End = Start + 1;
        while (End < Calls.size() && sameGuardedActCallGuard(Calls[Start], Calls[End]))
            ++End;

        Value *TriggerPtr =
            cloneConstantIndexGEP(B, Calls[Start].Guard.TriggerPtr, Wrapper->getArg(0));
        if (!TriggerPtr) {
            Wrapper->eraseFromParent();
            return nullptr;
        }
        auto *Load = B.CreateAlignedLoad(Calls[Start].Guard.LoadTy, TriggerPtr,
                                         Calls[Start].Guard.LoadAlign, "trigger");
        auto *Masked = B.CreateAnd(Load, ConstantInt::get(Calls[Start].Guard.LoadTy,
                                                          Calls[Start].Guard.Mask),
                                   "trigger_masked");
        auto *Zero = ConstantInt::get(Calls[Start].Guard.LoadTy, 0);
        auto *Cond =
            B.CreateICmp(Calls[Start].Guard.Predicate, Masked, Zero, "trigger_cond");

        auto *CallBB = BasicBlock::Create(Ctx, "guarded_calls" + std::to_string(GroupIdx), Wrapper);
        auto *NextBB = BasicBlock::Create(Ctx, "after_guard" + std::to_string(GroupIdx), Wrapper);
        if (Calls[Start].ExecuteOnTrue)
            B.CreateCondBr(Cond, CallBB, NextBB);
        else
            B.CreateCondBr(Cond, NextBB, CallBB);

        B.SetInsertPoint(CallBB);
        for (unsigned I = Start; I < End; ++I)
            B.CreateCall(Calls[I].Callee, {Wrapper->getArg(0)});
        B.CreateBr(NextBB);

        B.SetInsertPoint(NextBB);
        Start = End;
        ++GroupIdx;
    }

    B.CreateRetVoid();
    return Wrapper;
}

static void collectReachable(Function *Root, DenseSet<Function *> &Out) {
    SmallVector<Function *, 64> Stack;
    Stack.push_back(Root);
    while (!Stack.empty()) {
        auto *F = Stack.pop_back_val();
        if (!Out.insert(F).second) continue;
        for (auto &BB : *F)
            for (auto &I : BB)
                if (auto *CB = dyn_cast<CallBase>(&I))
                    if (auto *Callee = dyn_cast<Function>(
                            CB->getCalledOperand()->stripPointerCasts()))
                        if (!Callee->isDeclaration())
                            Stack.push_back(Callee);
    }
}

// ---------------------------------------------------------------------------
// Generation: stub creation
// ---------------------------------------------------------------------------

static void stubFunction(Function &F) {
    F.deleteBody();
    F.setPersonalityFn(nullptr);
    auto *BB = BasicBlock::Create(F.getContext(), "entry", &F);
    IRBuilder<> B(BB);
    Type *Ret = F.getReturnType();
    if (Ret->isVoidTy())               B.CreateRetVoid();
    else if (Ret->isIntegerTy(1))      B.CreateRet(ConstantInt::getFalse(F.getContext()));
    else if (Ret->isIntegerTy())       B.CreateRet(ConstantInt::get(Ret, 0));
    else if (Ret->isPointerTy())       B.CreateRet(ConstantPointerNull::get(cast<PointerType>(Ret)));
    else if (Ret->isFloatingPointTy()) B.CreateRet(ConstantFP::get(Ret, 0.0));
    else                               B.CreateRet(UndefValue::get(Ret));
}

// ---------------------------------------------------------------------------
// Generation: @fake_syms_buf + batch GPU kernels (eval + optional phase split)
// ---------------------------------------------------------------------------

static void collectPhaseReachable(Module &M, const DenseSet<Function *> &Reach,
                                  StringRef NameSubstr, SmallVectorImpl<Function *> &Out) {
    for (Function &F : M) {
        if (F.isDeclaration())
            continue;
        if (!F.getName().contains(NameSubstr))
            continue;
        if (!Reach.count(&F))
            continue;
        Out.push_back(&F);
    }
    llvm::sort(Out, [](const Function *A, const Function *B) {
        return A->getName() < B->getName();
    });
}

static bool isClosureHelperFunctionName(StringRef Name) {
    // Local lambda/operator helpers are closure methods. Their first argument is
    // the closure object, not the Verilator root pointer, so batch/probe kernels
    // must only execute them through their enclosing root function.
    return Name.starts_with("_ZZ") || (Name.contains("ENK") && Name.contains("clEv"));
}

static void filterTopLevelPhaseTargets(ArrayRef<Function *> In,
                                       SmallVectorImpl<Function *> &Out) {
    bool HasRootPhaseTargets = false;
    for (Function *F : In) {
        if (F && F->getName().contains("___024root___")) {
            HasRootPhaseTargets = true;
            break;
        }
    }

    for (Function *F : In) {
        if (!F)
            continue;
        StringRef Name = F->getName();
        if (isClosureHelperFunctionName(Name))
            continue;
        if (HasRootPhaseTargets && !Name.contains("___024root___"))
            continue;
        Out.push_back(F);
    }
}

static GlobalVariable *injectFakeSymsBuf(Module &M, uint64_t SizeBytes) {
    auto *ArrTy = ArrayType::get(Type::getInt8Ty(M.getContext()),
                                 std::max<uint64_t>(SizeBytes, 4096));
    auto *GV = new GlobalVariable(M, ArrTy, false,
                                   GlobalValue::InternalLinkage,
                                   ConstantAggregateZero::get(ArrTy), "fake_syms_buf");
    GV->setAlignment(Align(64));
    return GV;
}

/// One NVPTX kernel: for each active thread, optionally store fake vlSyms, then call each Callee(state_ptr).
static void injectBatchKernel(Module &M, StringRef KernelName, ArrayRef<Function *> Callees,
                              uint64_t Storage, std::optional<int64_t> VlSymsOff,
                              GlobalVariable *FakeSymsBuf) {
    LLVMContext &Ctx = M.getContext();
    Type *I8Ty  = Type::getInt8Ty(Ctx);
    Type *I32Ty = Type::getInt32Ty(Ctx);
    Type *I64Ty = Type::getInt64Ty(Ctx);
    auto *PtrTy = PointerType::get(Ctx, 0);
    auto *IntrTy = FunctionType::get(I32Ty, {}, false);

    auto *TidX   = cast<Function>(M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.tid.x",   IntrTy).getCallee());
    auto *CtaidX = cast<Function>(M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ctaid.x", IntrTy).getCallee());
    auto *NtidX  = cast<Function>(M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ntid.x",  IntrTy).getCallee());

    auto *Kernel = Function::Create(
        FunctionType::get(Type::getVoidTy(Ctx), {PtrTy, I32Ty}, false),
        GlobalValue::ExternalLinkage, KernelName, &M);
    Kernel->getArg(0)->setName("storage_base");
    Kernel->getArg(1)->setName("nstates");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Kernel);
    auto *BodyBB  = BasicBlock::Create(Ctx, "body",  Kernel);
    auto *ExitBB  = BasicBlock::Create(Ctx, "exit",  Kernel);

    IRBuilder<> B(EntryBB);
    auto *Gid32 = B.CreateAdd(
        B.CreateMul(B.CreateCall(CtaidX, {}, "bid"),
                    B.CreateCall(NtidX,  {}, "bdim"), "gid_mul"),
        B.CreateCall(TidX, {}, "tid"), "gid32");
    B.CreateCondBr(B.CreateICmpULT(Gid32, Kernel->getArg(1), "in_range"), BodyBB, ExitBB);

    B.SetInsertPoint(BodyBB);
    auto *StatePtr = B.CreateGEP(I8Ty, Kernel->getArg(0),
        {B.CreateMul(B.CreateZExt(Gid32, I64Ty, "gid"),
                     ConstantInt::get(I64Ty, Storage), "offset")},
        "state_ptr", true);
    if (VlSymsOff && FakeSymsBuf)
        B.CreateAlignedStore(FakeSymsBuf,
            B.CreateGEP(I8Ty, StatePtr, {ConstantInt::get(I64Ty, *VlSymsOff)},
                        "vlsyms_gep", true),
            Align(8));
    for (Function *Callee : Callees)
        B.CreateCall(Callee, {StatePtr});
    B.CreateBr(ExitBB);

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();

    M.getOrInsertNamedMetadata("nvvm.annotations")->addOperand(
        MDNode::get(Ctx, {ValueAsMetadata::get(Kernel),
                          MDString::get(Ctx, "kernel"),
                          ConstantAsMetadata::get(ConstantInt::get(I32Ty, 1))}));
}

static void injectResidentPatchScheduleKernel(Module &M) {
    LLVMContext &Ctx = M.getContext();
    Type *I8Ty = Type::getInt8Ty(Ctx);
    Type *I32Ty = Type::getInt32Ty(Ctx);
    Type *I64Ty = Type::getInt64Ty(Ctx);
    auto *PtrTy = PointerType::get(Ctx, 0);
    auto *IntrTy = FunctionType::get(I32Ty, {}, false);

    auto *TidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.tid.x", IntrTy).getCallee());
    auto *CtaidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ctaid.x", IntrTy).getCallee());
    auto *NtidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ntid.x", IntrTy).getCallee());

    auto *Kernel = Function::Create(
        FunctionType::get(Type::getVoidTy(Ctx), {PtrTy, PtrTy, PtrTy, I32Ty}, false),
        GlobalValue::ExternalLinkage, "vl_apply_patch_schedule_gpu", &M);
    Kernel->getArg(0)->setName("storage_base");
    Kernel->getArg(1)->setName("patch_offsets");
    Kernel->getArg(2)->setName("patch_values");
    Kernel->getArg(3)->setName("patch_count");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Kernel);
    auto *BodyBB = BasicBlock::Create(Ctx, "body", Kernel);
    auto *ExitBB = BasicBlock::Create(Ctx, "exit", Kernel);

    IRBuilder<> B(EntryBB);
    auto *Gid32 = B.CreateAdd(
        B.CreateMul(B.CreateCall(CtaidX, {}, "bid"),
                    B.CreateCall(NtidX, {}, "bdim"), "gid_mul"),
        B.CreateCall(TidX, {}, "tid"), "gid32");
    B.CreateCondBr(B.CreateICmpULT(Gid32, Kernel->getArg(3), "in_range"), BodyBB,
                   ExitBB);

    B.SetInsertPoint(BodyBB);
    auto *Gid64 = B.CreateZExt(Gid32, I64Ty, "gid");
    auto *OffsetPtr =
        B.CreateGEP(I64Ty, Kernel->getArg(1), {Gid64}, "offset_ptr", true);
    auto *Offset = B.CreateAlignedLoad(I64Ty, OffsetPtr, Align(8), "off");
    auto *ValuePtr =
        B.CreateGEP(I8Ty, Kernel->getArg(2), {Gid64}, "value_ptr", true);
    auto *Value = B.CreateAlignedLoad(I8Ty, ValuePtr, Align(1), "value");
    auto *Dst = B.CreateGEP(I8Ty, Kernel->getArg(0), {Offset}, "dst", true);
    B.CreateAlignedStore(Value, Dst, Align(1));
    B.CreateBr(ExitBB);

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();

    M.getOrInsertNamedMetadata("nvvm.annotations")->addOperand(
        MDNode::get(Ctx, {ValueAsMetadata::get(Kernel),
                          MDString::get(Ctx, "kernel"),
                          ConstantAsMetadata::get(ConstantInt::get(I32Ty, 1))}));
}

static void injectProgramImageInitKernel(Module &M) {
    LLVMContext &Ctx = M.getContext();
    Type *I8Ty = Type::getInt8Ty(Ctx);
    Type *I32Ty = Type::getInt32Ty(Ctx);
    Type *I64Ty = Type::getInt64Ty(Ctx);
    auto *PtrTy = PointerType::get(Ctx, 0);
    auto *IntrTy = FunctionType::get(I32Ty, {}, false);

    auto *TidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.tid.x", IntrTy).getCallee());
    auto *CtaidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ctaid.x", IntrTy).getCallee());
    auto *NtidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ntid.x", IntrTy).getCallee());

    auto *Kernel = Function::Create(
        FunctionType::get(Type::getVoidTy(Ctx),
                          {PtrTy, PtrTy, PtrTy, I32Ty, I64Ty, I32Ty}, false),
        GlobalValue::ExternalLinkage, "vl_apply_program_image_init_gpu", &M);
    Kernel->getArg(0)->setName("storage_base");
    Kernel->getArg(1)->setName("record_offsets");
    Kernel->getArg(2)->setName("record_values");
    Kernel->getArg(3)->setName("record_count");
    Kernel->getArg(4)->setName("storage_bytes");
    Kernel->getArg(5)->setName("nstates");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Kernel);
    auto *BodyBB = BasicBlock::Create(Ctx, "body", Kernel);
    auto *ExitBB = BasicBlock::Create(Ctx, "exit", Kernel);

    IRBuilder<> B(EntryBB);
    auto *Gid32 = B.CreateAdd(
        B.CreateMul(B.CreateCall(CtaidX, {}, "bid"),
                    B.CreateCall(NtidX, {}, "bdim"), "gid_mul"),
        B.CreateCall(TidX, {}, "tid"), "gid32");
    auto *Gid64 = B.CreateZExt(Gid32, I64Ty, "gid");
    auto *RecordCount64 = B.CreateZExt(Kernel->getArg(3), I64Ty, "record_count64");
    auto *Nstates64 = B.CreateZExt(Kernel->getArg(5), I64Ty, "nstates64");
    auto *TotalRecords = B.CreateMul(RecordCount64, Nstates64, "total_records");
    B.CreateCondBr(B.CreateICmpULT(Gid64, TotalRecords, "in_range"), BodyBB,
                   ExitBB);

    B.SetInsertPoint(BodyBB);
    auto *StateIdx = B.CreateUDiv(Gid64, RecordCount64, "state_idx");
    auto *RecordIdx = B.CreateURem(Gid64, RecordCount64, "record_idx");
    auto *StateBaseOff =
        B.CreateMul(StateIdx, Kernel->getArg(4), "state_base_off");
    auto *OffsetPtr =
        B.CreateGEP(I64Ty, Kernel->getArg(1), {RecordIdx}, "offset_ptr", true);
    auto *RecordOff = B.CreateAlignedLoad(I64Ty, OffsetPtr, Align(8), "record_off");
    auto *ValuePtr =
        B.CreateGEP(I8Ty, Kernel->getArg(2), {RecordIdx}, "value_ptr", true);
    auto *Value = B.CreateAlignedLoad(I8Ty, ValuePtr, Align(1), "value");
    auto *DstOff = B.CreateAdd(StateBaseOff, RecordOff, "dst_off");
    auto *Dst = B.CreateGEP(I8Ty, Kernel->getArg(0), {DstOff}, "dst", true);
    B.CreateAlignedStore(Value, Dst, Align(1));
    B.CreateBr(ExitBB);

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();

    M.getOrInsertNamedMetadata("nvvm.annotations")->addOperand(
        MDNode::get(Ctx, {ValueAsMetadata::get(Kernel),
                          MDString::get(Ctx, "kernel"),
                          ConstantAsMetadata::get(ConstantInt::get(I32Ty, 1))}));
}

static void injectProgramImageWordsKernel(Module &M) {
    LLVMContext &Ctx = M.getContext();
    Type *I8Ty = Type::getInt8Ty(Ctx);
    Type *I32Ty = Type::getInt32Ty(Ctx);
    Type *I64Ty = Type::getInt64Ty(Ctx);
    auto *PtrTy = PointerType::get(Ctx, 0);
    auto *IntrTy = FunctionType::get(I32Ty, {}, false);

    auto *TidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.tid.x", IntrTy).getCallee());
    auto *CtaidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ctaid.x", IntrTy).getCallee());
    auto *NtidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ntid.x", IntrTy).getCallee());

    auto *Kernel = Function::Create(
        FunctionType::get(Type::getVoidTy(Ctx),
                          {PtrTy, PtrTy, PtrTy, I32Ty, I64Ty, I32Ty}, false),
        GlobalValue::ExternalLinkage, "vl_apply_program_image_words_gpu", &M);
    Kernel->getArg(0)->setName("storage_base");
    Kernel->getArg(1)->setName("program_words");
    Kernel->getArg(2)->setName("lane_base_offsets");
    Kernel->getArg(3)->setName("word_count");
    Kernel->getArg(4)->setName("storage_bytes");
    Kernel->getArg(5)->setName("nstates");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Kernel);
    auto *BodyBB = BasicBlock::Create(Ctx, "body", Kernel);
    auto *ExitBB = BasicBlock::Create(Ctx, "exit", Kernel);

    IRBuilder<> B(EntryBB);
    auto *Gid32 = B.CreateAdd(
        B.CreateMul(B.CreateCall(CtaidX, {}, "bid"),
                    B.CreateCall(NtidX, {}, "bdim"), "gid_mul"),
        B.CreateCall(TidX, {}, "tid"), "gid32");
    auto *Gid64 = B.CreateZExt(Gid32, I64Ty, "gid");
    auto *WordCount64 = B.CreateZExt(Kernel->getArg(3), I64Ty, "word_count64");
    auto *Nstates64 = B.CreateZExt(Kernel->getArg(5), I64Ty, "nstates64");
    auto *TotalWords = B.CreateMul(WordCount64, Nstates64, "total_words");
    B.CreateCondBr(B.CreateICmpULT(Gid64, TotalWords, "in_range"), BodyBB,
                   ExitBB);

    B.SetInsertPoint(BodyBB);
    auto *StateIdx = B.CreateUDiv(Gid64, WordCount64, "state_idx");
    auto *WordIdx = B.CreateURem(Gid64, WordCount64, "word_idx");
    auto *StateBaseOff =
        B.CreateMul(StateIdx, Kernel->getArg(4), "state_base_off");
    auto *WordPtr =
        B.CreateGEP(I32Ty, Kernel->getArg(1), {WordIdx}, "word_ptr", true);
    auto *Word = B.CreateAlignedLoad(I32Ty, WordPtr, Align(4), "word");

    Value *LaneValues[4] = {
        B.CreateTrunc(B.CreateLShr(Word, ConstantInt::get(I32Ty, 24), "ram0_shift"),
                      I8Ty, "ram0_byte"),
        B.CreateTrunc(B.CreateLShr(Word, ConstantInt::get(I32Ty, 16), "ram1_shift"),
                      I8Ty, "ram1_byte"),
        B.CreateTrunc(B.CreateLShr(Word, ConstantInt::get(I32Ty, 8), "ram2_shift"),
                      I8Ty, "ram2_byte"),
        B.CreateTrunc(Word, I8Ty, "ram3_byte"),
    };

    for (uint64_t Lane = 0; Lane < 4; ++Lane) {
        auto *LaneBasePtr = B.CreateGEP(
            I64Ty, Kernel->getArg(2), {ConstantInt::get(I64Ty, Lane)},
            "lane_base_ptr", true);
        auto *LaneBase =
            B.CreateAlignedLoad(I64Ty, LaneBasePtr, Align(8), "lane_base");
        auto *LaneRel = B.CreateAdd(LaneBase, WordIdx, "lane_rel");
        auto *DstOff = B.CreateAdd(StateBaseOff, LaneRel, "dst_off");
        auto *Dst = B.CreateGEP(I8Ty, Kernel->getArg(0), {DstOff}, "dst", true);
        B.CreateAlignedStore(LaneValues[Lane], Dst, Align(1));
    }
    B.CreateBr(ExitBB);

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();

    M.getOrInsertNamedMetadata("nvvm.annotations")->addOperand(
        MDNode::get(Ctx, {ValueAsMetadata::get(Kernel),
                          MDString::get(Ctx, "kernel"),
                          ConstantAsMetadata::get(ConstantInt::get(I32Ty, 1))}));
}

static void injectDmemZeroFillKernel(Module &M) {
    LLVMContext &Ctx = M.getContext();
    Type *I8Ty = Type::getInt8Ty(Ctx);
    Type *I32Ty = Type::getInt32Ty(Ctx);
    Type *I64Ty = Type::getInt64Ty(Ctx);
    auto *PtrTy = PointerType::get(Ctx, 0);
    auto *IntrTy = FunctionType::get(I32Ty, {}, false);

    auto *TidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.tid.x", IntrTy).getCallee());
    auto *CtaidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ctaid.x", IntrTy).getCallee());
    auto *NtidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ntid.x", IntrTy).getCallee());

    auto *Kernel = Function::Create(
        FunctionType::get(Type::getVoidTy(Ctx), {PtrTy, PtrTy, I32Ty, I64Ty, I32Ty}, false),
        GlobalValue::ExternalLinkage, "vl_zero_dmem_words_gpu", &M);
    Kernel->getArg(0)->setName("storage_base");
    Kernel->getArg(1)->setName("lane_base_offsets");
    Kernel->getArg(2)->setName("word_count");
    Kernel->getArg(3)->setName("storage_bytes");
    Kernel->getArg(4)->setName("nstates");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Kernel);
    auto *BodyBB = BasicBlock::Create(Ctx, "body", Kernel);
    auto *ExitBB = BasicBlock::Create(Ctx, "exit", Kernel);

    IRBuilder<> B(EntryBB);
    auto *Gid32 = B.CreateAdd(
        B.CreateMul(B.CreateCall(CtaidX, {}, "bid"),
                    B.CreateCall(NtidX, {}, "bdim"), "gid_mul"),
        B.CreateCall(TidX, {}, "tid"), "gid32");
    auto *Gid64 = B.CreateZExt(Gid32, I64Ty, "gid");
    auto *WordCount64 = B.CreateZExt(Kernel->getArg(2), I64Ty, "word_count64");
    auto *Nstates64 = B.CreateZExt(Kernel->getArg(4), I64Ty, "nstates64");
    auto *TotalWords = B.CreateMul(WordCount64, Nstates64, "total_words");
    B.CreateCondBr(B.CreateICmpULT(Gid64, TotalWords, "in_range"), BodyBB,
                   ExitBB);

    B.SetInsertPoint(BodyBB);
    auto *StateIdx = B.CreateUDiv(Gid64, WordCount64, "state_idx");
    auto *WordIdx = B.CreateURem(Gid64, WordCount64, "word_idx");
    auto *StateBaseOff =
        B.CreateMul(StateIdx, Kernel->getArg(3), "state_base_off");
    for (uint64_t Lane = 0; Lane < 4; ++Lane) {
        auto *LaneBasePtr = B.CreateGEP(
            I64Ty, Kernel->getArg(1), {ConstantInt::get(I64Ty, Lane)},
            "dmem_lane_base_ptr", true);
        auto *LaneBase =
            B.CreateAlignedLoad(I64Ty, LaneBasePtr, Align(8), "dmem_lane_base");
        auto *LaneRel = B.CreateAdd(LaneBase, WordIdx, "dmem_lane_rel");
        auto *DstOff = B.CreateAdd(StateBaseOff, LaneRel, "dmem_lane_dst_off");
        auto *Dst =
            B.CreateGEP(I8Ty, Kernel->getArg(0), {DstOff}, "dmem_lane_dst", true);
        B.CreateAlignedStore(ConstantInt::get(I8Ty, 0), Dst, Align(1));
    }
    B.CreateBr(ExitBB);

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();

    M.getOrInsertNamedMetadata("nvvm.annotations")->addOperand(
        MDNode::get(Ctx, {ValueAsMetadata::get(Kernel),
                          MDString::get(Ctx, "kernel"),
                          ConstantAsMetadata::get(ConstantInt::get(I32Ty, 1))}));
}

static void injectInitStateReplicationKernel(Module &M) {
    LLVMContext &Ctx = M.getContext();
    Type *I8Ty = Type::getInt8Ty(Ctx);
    Type *I32Ty = Type::getInt32Ty(Ctx);
    Type *I64Ty = Type::getInt64Ty(Ctx);
    auto *PtrTy = PointerType::get(Ctx, 0);
    auto *IntrTy = FunctionType::get(I32Ty, {}, false);

    auto *TidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.tid.x", IntrTy).getCallee());
    auto *CtaidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ctaid.x", IntrTy).getCallee());
    auto *NtidX = cast<Function>(
        M.getOrInsertFunction("llvm.nvvm.read.ptx.sreg.ntid.x", IntrTy).getCallee());

    auto *Kernel = Function::Create(
        FunctionType::get(Type::getVoidTy(Ctx), {PtrTy, PtrTy, I64Ty, I64Ty}, false),
        GlobalValue::ExternalLinkage, "vl_replicate_init_state_gpu", &M);
    Kernel->getArg(0)->setName("storage_base");
    Kernel->getArg(1)->setName("init_state");
    Kernel->getArg(2)->setName("storage_bytes");
    Kernel->getArg(3)->setName("total_bytes");

    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Kernel);
    auto *BodyBB = BasicBlock::Create(Ctx, "body", Kernel);
    auto *ExitBB = BasicBlock::Create(Ctx, "exit", Kernel);

    IRBuilder<> B(EntryBB);
    auto *Gid32 = B.CreateAdd(
        B.CreateMul(B.CreateCall(CtaidX, {}, "bid"),
                    B.CreateCall(NtidX, {}, "bdim"), "gid_mul"),
        B.CreateCall(TidX, {}, "tid"), "gid32");
    auto *Gid64 = B.CreateZExt(Gid32, I64Ty, "gid");
    B.CreateCondBr(B.CreateICmpULT(Gid64, Kernel->getArg(3), "in_range"), BodyBB,
                   ExitBB);

    B.SetInsertPoint(BodyBB);
    auto *SrcOff = B.CreateURem(Gid64, Kernel->getArg(2), "src_off");
    auto *Src = B.CreateGEP(I8Ty, Kernel->getArg(1), {SrcOff}, "src", true);
    auto *Value = B.CreateAlignedLoad(I8Ty, Src, Align(1), "value");
    auto *Dst = B.CreateGEP(I8Ty, Kernel->getArg(0), {Gid64}, "dst", true);
    B.CreateAlignedStore(Value, Dst, Align(1));
    B.CreateBr(ExitBB);

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();

    M.getOrInsertNamedMetadata("nvvm.annotations")->addOperand(
        MDNode::get(Ctx, {ValueAsMetadata::get(Kernel),
                          MDString::get(Ctx, "kernel"),
                          ConstantAsMetadata::get(ConstantInt::get(I32Ty, 1))}));
}

static Function *createPhaseLoopWrapper(Module &M, StringRef WrapperName, Function *PhaseFn,
                                        unsigned MaxIters = 100) {
    if (!PhaseFn || PhaseFn->arg_size() != 1)
        return nullptr;

    LLVMContext &Ctx = M.getContext();
    auto *FTy = FunctionType::get(Type::getVoidTy(Ctx),
                                  {PhaseFn->getArg(0)->getType()}, false);
    auto *Wrapper =
        Function::Create(FTy, GlobalValue::InternalLinkage, WrapperName, &M);
    Wrapper->getArg(0)->setName("state_ptr");

    Type *RetTy = PhaseFn->getReturnType();
    if (RetTy->isVoidTy()) {
        auto *EntryBB = BasicBlock::Create(Ctx, "entry", Wrapper);
        IRBuilder<> B(EntryBB);
        B.CreateCall(PhaseFn, {Wrapper->getArg(0)});
        B.CreateRetVoid();
        return Wrapper;
    }

    if (!RetTy->isIntegerTy(1)) {
        Wrapper->eraseFromParent();
        return nullptr;
    }

    Type *I32Ty = Type::getInt32Ty(Ctx);
    auto *EntryBB = BasicBlock::Create(Ctx, "entry", Wrapper);
    auto *LoopBB = BasicBlock::Create(Ctx, "phase_loop", Wrapper);
    auto *ExitBB = BasicBlock::Create(Ctx, "exit", Wrapper);

    IRBuilder<> B(EntryBB);
    B.CreateBr(LoopBB);

    B.SetInsertPoint(LoopBB);
    auto *Iter = B.CreatePHI(I32Ty, 2, "iter");
    Iter->addIncoming(ConstantInt::get(I32Ty, 0), EntryBB);
    Value *Changed = B.CreateCall(PhaseFn, {Wrapper->getArg(0)}, "changed");
    Value *NextIter = B.CreateAdd(Iter, ConstantInt::get(I32Ty, 1), "next_iter");
    Value *UnderCap =
        B.CreateICmpULT(NextIter, ConstantInt::get(I32Ty, MaxIters), "under_cap");
    Value *Continue = B.CreateAnd(Changed, UnderCap, "continue_phase_loop");
    B.CreateCondBr(Continue, LoopBB, ExitBB);
    Iter->addIncoming(NextIter, LoopBB);

    B.SetInsertPoint(ExitBB);
    B.CreateRetVoid();
    return Wrapper;
}

static bool injectPhaseLoopKernelIfReachable(Module &M, const DenseSet<Function *> &Reach,
                                             StringRef PhaseSelector,
                                             StringRef ManifestSelector,
                                             StringRef KernelName,
                                             StringRef WrapperName,
                                             uint64_t Storage,
                                             std::optional<int64_t> VlSymsOff,
                                             GlobalVariable *FakeSymsBuf,
                                             SmallVectorImpl<KernelManifestEntry> &Manifest) {
    Function *PhaseFn = findReachableNamedFunction(M, Reach, PhaseSelector);
    if (!PhaseFn)
        return false;
    Function *Wrapper = createPhaseLoopWrapper(M, WrapperName, PhaseFn);
    if (!Wrapper)
        return false;
    Function *WrapperArr[] = {Wrapper};
    injectBatchKernel(M, KernelName, WrapperArr, Storage, VlSymsOff, FakeSymsBuf);
    Manifest.push_back({ManifestSelector.str(), KernelName.str()});
    return true;
}

static void injectActSequentChunkProbeKernels(Module &M, const DenseSet<Function *> &Reach,
                                              unsigned ChunkSize, uint64_t Storage,
                                              std::optional<int64_t> VlSymsOff,
                                              GlobalVariable *FakeSymsBuf,
                                              SmallVectorImpl<KernelManifestEntry> &ProbeManifest) {
    if (ChunkSize == 0)
        return;
    SmallVector<Function *, 128> ReachableActFns;
    SmallVector<Function *, 128> ActFns;
    collectPhaseReachable(M, Reach, "___act_sequent", ReachableActFns);
    filterTopLevelPhaseTargets(ReachableActFns, ActFns);

    DenseSet<Function *> AllowedActFns;
    for (Function *F : ActFns)
        AllowedActFns.insert(F);

    SmallVector<GuardedActCall, 256> GuardedCalls;
    collectGuardedActCalls(M, Reach, AllowedActFns, GuardedCalls);
    if (!GuardedCalls.empty()) {
        for (unsigned Start = 0, ChunkIdx = 0; Start < GuardedCalls.size();
             Start += ChunkSize, ++ChunkIdx) {
            unsigned Count = std::min<unsigned>(ChunkSize, GuardedCalls.size() - Start);
            std::string WrapperName =
                "__vlgpu_act_seq_chunk" + std::to_string(ChunkIdx) + "_wrapper";
            Function *Wrapper = createGuardedActChunkWrapper(
                M, WrapperName, ArrayRef<GuardedActCall>(GuardedCalls).slice(Start, Count));
            if (!Wrapper)
                break;
            std::string KernelName = "vl_act_seq_chunk" + std::to_string(ChunkIdx) + "_batch_gpu";
            Function *WrapperArr[] = {Wrapper};
            injectBatchKernel(M, KernelName, WrapperArr, Storage, VlSymsOff, FakeSymsBuf);
            std::string Selector = "___act_sequent_chunk:";
            Selector += std::to_string(Start);
            Selector += "-";
            Selector += std::to_string(Start + Count - 1);
            ProbeManifest.push_back({Selector, KernelName});
        }
        return;
    }

    for (unsigned Start = 0, ChunkIdx = 0; Start < ActFns.size(); Start += ChunkSize, ++ChunkIdx) {
        unsigned Count = std::min<unsigned>(ChunkSize, ActFns.size() - Start);
        std::string KernelName = "vl_act_seq_chunk" + std::to_string(ChunkIdx) + "_batch_gpu";
        injectBatchKernel(M, KernelName, ArrayRef<Function *>(ActFns).slice(Start, Count),
                          Storage, VlSymsOff, FakeSymsBuf);
        std::string Selector = "___act_sequent_chunk:";
        Selector += std::to_string(Start);
        Selector += "-";
        Selector += std::to_string(Start + Count - 1);
        ProbeManifest.push_back({Selector, KernelName});
    }
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main(int argc, char **argv) {
    InitLLVM X(argc, argv);
    cl::ParseCommandLineOptions(argc, argv,
        "vlgpugen — Verilator merged.ll → NVPTX GPU kernel generator\n");

    if (InputFilename.empty()) { errs() << "error: no input .ll file\n"; return 1; }
    if (!AnalyzePhasesJson.empty() && !AnalyzePhases) {
        errs() << "error: --analyze-phases-json requires --analyze-phases\n";
        return 1;
    }
    if (!KernelManifestOut.empty() && KernelSplit != "phases") {
        errs() << "error: --kernel-manifest-out requires --kernel-split=phases\n";
        return 1;
    }
    if (KernelProbeActSequentChunkSize != 0 && KernelSplit != "phases") {
        errs() << "error: --kernel-probe-act-sequent-chunk-size requires --kernel-split=phases\n";
        return 1;
    }

    auto BufOr = MemoryBuffer::getFile(InputFilename);
    if (!BufOr) { errs() << "error: " << BufOr.getError().message() << "\n"; return 1; }

    LLVMContext Ctx;
    SMDiagnostic Err;
    auto M = parseIRFile(InputFilename, Err, Ctx);
    if (!M) { Err.print(argv[0], errs()); return 1; }

    auto VlOff   = detectVlSymsOffset(BufOr.get()->getBuffer());
    uint64_t SymsBufferSize = VlOff ? detectSymsBufferSize(BufOr.get()->getBuffer()) : 0;
    auto *EvalFn = findEvalFunction(*M);
    if (!EvalFn) { errs() << "error: eval function not found\n"; return 1; }

    DenseSet<Function *> Reach;
    collectReachable(EvalFn, Reach);

    DenseSet<Function *> RuntimeFuncs;
    DenseMap<Function *, ClassificationReason> RuntimeReasons;
    for (auto *F : Reach) {
        std::string Body;
        functionToString(*F, Body);
        if (auto Reason = classifyRuntimeReason(*F, Body)) {
            RuntimeFuncs.insert(F);
            RuntimeReasons[F] = std::move(*Reason);
        }
    }
    if (!NoDeclRuntimeMerge)
        mergeRuntimeViaDeclCalls(Reach, RuntimeFuncs, RuntimeReasons);

    if (AnalyzePhases) {
        reportAnalyzePhases(*M, Reach);
        if (!AnalyzePhasesJson.empty()) {
            if (writeAnalyzePhasesJson(*M, Reach, EvalFn, AnalyzePhasesJson))
                return 1;
        }
    }

    DenseSet<Function *> GPUFuncs;
    for (auto *F : Reach) {
        if (!RuntimeFuncs.count(F))
            GPUFuncs.insert(F);
    }

    if (!Quiet) {
        outs() << "eval:            @" << EvalFn->getName() << "\n";
        outs() << "reachable (raw): " << Reach.size() << "\n";
        outs() << "GPU functions:   " << GPUFuncs.size() << "\n";
        outs() << "runtime (stub):  " << RuntimeFuncs.size() << "\n";
        if (VlOff) outs() << "vlSymsp offset:  " << *VlOff << " bytes\n";
        else       outs() << "vlSymsp offset:  (not detected)\n";
    }

    if (!ClassifierReportOut.empty()) {
        if (writeClassifierReportJson(Reach, RuntimeFuncs, RuntimeReasons, EvalFn, VlOff,
                                      !NoDeclRuntimeMerge, ClassifierReportOut))
            return 1;
    }

    if (AnalyzePhases)
        return 0;

    if (OutFile.empty()) return 0;  // analysis-only mode

    // ── generation mode ───────────────────────────────────────────────────
    if (StorageSize == 0) { errs() << "error: --storage-size required with --out\n"; return 1; }
    if (!KernelSplit.empty() && KernelSplit != "phases") {
        errs() << "error: --kernel-split must be empty or 'phases' (got '" << KernelSplit << "')\n";
        return 1;
    }

    // Remove GlobalAliases (ctor/dtor aliases become invalid after deleteBody)
    SmallVector<GlobalAlias *, 16> Aliases;
    for (auto &GA : M->aliases()) Aliases.push_back(&GA);
    for (auto *GA : Aliases) { GA->replaceAllUsesWith(GA->getAliasee()); GA->eraseFromParent(); }

    for (auto *F : RuntimeFuncs) stubFunction(*F);

    for (auto &F : *M)
        if (!F.isDeclaration() && !Reach.count(&F))
            F.deleteBody();

    // NVPTX rejects comdat on declarations
    for (auto &F  : *M)          if (F.isDeclaration())  F.setComdat(nullptr);
    for (auto &GV : M->globals()) if (GV.isDeclaration()) GV.setComdat(nullptr);

    // Stub extern non-llvm calls from GPU functions
    DenseSet<Function *> ExternCalls;
    for (auto *F : GPUFuncs)
        for (auto &BB : *F)
            for (auto &I : BB)
                if (auto *CB = dyn_cast<CallBase>(&I))
                    if (auto *Callee = CB->getCalledFunction())
                        if (Callee->isDeclaration() &&
                            !Callee->getName().starts_with("llvm.") &&
                            !RuntimeFuncs.count(Callee))
                            ExternCalls.insert(Callee);
    for (auto *F : ExternCalls) stubFunction(*F);
    if (!ExternCalls.empty() && !Quiet)
        outs() << "stubbed extern calls: " << ExternCalls.size() << "\n";

    // Remove host-only globals (@llvm.global.annotations keeps .24-suffix decls alive)
    SmallVector<GlobalVariable *, 32> HostGVs;
    for (auto &GV : M->globals()) {
        StringRef N = GV.getName();
        if (N == "llvm.global.annotations" ||
            N.starts_with("_ZTV") || N.starts_with("_ZTI") || N.starts_with("_ZTS"))
            HostGVs.push_back(&GV);
    }
    for (auto *GV : HostGVs) { GV->replaceAllUsesWith(PoisonValue::get(GV->getType())); GV->eraseFromParent(); }
    if (!HostGVs.empty() && !Quiet)
        outs() << "removed host globals: " << HostGVs.size() << "\n";

    auto *FakeSymsBuf = VlOff ? injectFakeSymsBuf(*M, SymsBufferSize) : nullptr;

    M->setTargetTriple(NVPTX_TRIPLE);
    M->setDataLayout(NVPTX_DATALAYOUT);

    // Keep the Verilator root eval loop as a callable unit.  Some stateful
    // designs rely on the exact act/inact/nba phase do-while structure; fully
    // inlining it into the batch wrapper can obscure that loop boundary under
    // later GPU IR optimization.
    EvalFn->removeFnAttr(Attribute::AlwaysInline);
    EvalFn->addFnAttr(Attribute::NoInline);

    injectBatchKernel(*M, "vl_eval_batch_gpu", ArrayRef(&EvalFn, 1), StorageSize, VlOff,
                      FakeSymsBuf);
    injectResidentPatchScheduleKernel(*M);
    injectProgramImageInitKernel(*M);
    injectProgramImageWordsKernel(*M);
    injectDmemZeroFillKernel(*M);
    injectInitStateReplicationKernel(*M);

    if (KernelSplit == "phases") {
        SmallVector<KernelManifestEntry, 8> Manifest;
        SmallVector<KernelManifestEntry, 8> ProbeManifest;

        SmallVector<Function *, 8> IcoFns;
        collectPhaseReachable(*M, Reach, "___ico_sequent", IcoFns);
        injectBatchKernel(*M, "vl_ico_batch_gpu", IcoFns, StorageSize, VlOff, FakeSymsBuf);
        Manifest.push_back({"___ico_sequent", "vl_ico_batch_gpu"});

        bool UsedActLoop = injectPhaseLoopKernelIfReachable(
            *M, Reach, "___eval_phase__act", "___eval_phase__act_loop",
            "vl_act_loop_batch_gpu", "__vlgpu_eval_phase_act_loop_wrapper", StorageSize,
            VlOff, FakeSymsBuf, Manifest);
        bool UsedInactLoop = injectPhaseLoopKernelIfReachable(
            *M, Reach, "___eval_phase__inact", "___eval_phase__inact_loop",
            "vl_inact_loop_batch_gpu", "__vlgpu_eval_phase_inact_loop_wrapper", StorageSize,
            VlOff, FakeSymsBuf, Manifest);
        injectActSequentChunkProbeKernels(
            *M, Reach, KernelProbeActSequentChunkSize, StorageSize, VlOff, FakeSymsBuf,
            ProbeManifest);

        bool UsedGuardedSegments = false;
        if (Function *EvalNba = findReachableNamedFunction(*M, Reach, "___eval_nba")) {
            SmallVector<GuardedSegment, 8> Segments;
            if (extractGuardedSegments(*EvalNba, Segments)) {
                UsedGuardedSegments = true;
                for (unsigned I = 0; I < Segments.size(); ++I) {
                    std::string WrapperName = "__vlgpu_nba_seg" + std::to_string(I) + "_wrapper";
                    Function *Wrapper = createGuardedSegmentWrapper(*M, WrapperName, Segments[I]);
                    if (!Wrapper) {
                        UsedGuardedSegments = false;
                        break;
                    }
                    std::string KernelName = "vl_nba_seg" + std::to_string(I) + "_batch_gpu";
                    Function *WrapperArr[] = {Wrapper};
                    injectBatchKernel(*M, KernelName, WrapperArr, StorageSize, VlOff, FakeSymsBuf);
                    std::string Selector;
                    if (Segments[I].Callee)
                        Selector =
                            "___eval_nba_guarded_helper:" + Segments[I].Callee->getName().str();
                    else
                        Selector = "___eval_nba_inline_region:seg" + std::to_string(I);
                    Manifest.push_back({Selector, KernelName});
                }
                if (UsedGuardedSegments) {
                    Function *ClearWrapper = createTriggerClearWrapper(
                        *M, "__vlgpu_nba_trigger_clear_wrapper", Segments.front().Guard);
                    if (!ClearWrapper) {
                        UsedGuardedSegments = false;
                    } else {
                        Function *ClearWrapperArr[] = {ClearWrapper};
                        injectBatchKernel(*M, "vl_nba_trigger_clear_batch_gpu",
                                          ClearWrapperArr, StorageSize, VlOff, FakeSymsBuf);
                        Manifest.push_back({"___eval_nba_trigger_clear",
                                            "vl_nba_trigger_clear_batch_gpu"});
                    }
                }
                if (!UsedGuardedSegments)
                    while (Manifest.size() > 1)
                        Manifest.pop_back();
            }
        }

        if (!UsedGuardedSegments) {
            static const KernelManifestEntry LegacyNbaKernels[] = {
                {"___nba_comb", "vl_nba_comb_batch_gpu"},
                {"___nba_sequent", "vl_nba_sequent_batch_gpu"},
            };
            for (auto &PK : LegacyNbaKernels) {
                SmallVector<Function *, 8> Fs;
                collectPhaseReachable(*M, Reach, PK.Selector, Fs);
                SmallVector<Function *, 8> TopLevelFs;
                filterTopLevelPhaseTargets(Fs, TopLevelFs);
                injectBatchKernel(*M, PK.KernelName, TopLevelFs,
                                  StorageSize, VlOff, FakeSymsBuf);
                Manifest.push_back(PK);
            }
        }

        if (!KernelManifestOut.empty())
            if (int RC = writeKernelManifestJson(Manifest, "phases",
                                                 KernelManifestOut, ProbeManifest))
                return RC;
        if (!Quiet) {
            if (UsedGuardedSegments)
                outs() << "kernel-split=phases: vl_ico_batch_gpu + guarded eval_nba segments "
                          "(plus vl_eval_batch_gpu)\n";
            else
                outs() << "kernel-split=phases: vl_ico_batch_gpu, vl_nba_comb_batch_gpu, "
                          "vl_nba_sequent_batch_gpu (plus vl_eval_batch_gpu)\n";
            if (UsedActLoop || UsedInactLoop)
                outs() << "kernel-split=phases: eval act/inact phase loops included\n";
            if (!ProbeManifest.empty())
                outs() << "kernel-split=phases: act_sequent probe chunks included: "
                       << ProbeManifest.size() << "\n";
        }
    }

    std::error_code EC;
    raw_fd_ostream OS(OutFile, EC);
    if (EC) { errs() << "error: " << EC.message() << "\n"; return 1; }
    M->print(OS, nullptr);
    outs() << "written: " << OutFile << "\n";
    return 0;
}
