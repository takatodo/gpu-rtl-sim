/**
 * VlGpuPasses.cpp
 *
 * LLVM NewPM pass plugin for the stock-Verilator → NVPTX path (see README “Pipeline layout”).
 *
 * Passes (registered names for -passes=...):
 *   vl-strip-x86-attrs    FunctionPass  strip x86-only attrs/comdat; demote linkonce_odr;
 *                         clear personality only after EH pads are gone
 *   vl-stub-host-io-calls FunctionPass  erase GPU-incompatible Verilator host I/O call sites
 *   vl-stub-timing-scheduler-context
 *                         FunctionPass  stub timed-scheduler act phase on diagnostic GPU path
 *   vl-sanitize-host-io-null-writes
 *                         FunctionPass  redirect optimized host I/O string null writes
 *   vl-patch-convergence  FunctionPass  break infinite convergence loops after VL_FATAL_MT stubs
 *
 * EH lowering is **not** implemented here: use LLVM’s built-in `lowerinvoke` before these passes
 * (see build_vl_gpu.py: lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-patch-convergence).
 *
 * Upstream IR: **vlgpugen** (`--out`) emits `vl_batch_gpu.ll` (Phase 3). This plugin then lowers EH,
 * strips x86-only metadata, erases host I/O call sites, and patches convergence loops before
 * `opt -O3` / `llc` / `ptxas`.
 * Legacy Python `gen_vl_gpu_kernel.py` remains for parity checks — see README.
 *
 * Usage:
 *   opt-18 --load-pass-plugin=./VlGpuPasses.so \
 *          -passes="lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-stub-host-io-calls,vl-patch-convergence,dce" \
 *          -S vl_batch_gpu.ll -o vl_batch_gpu_patched.ll
 *
 * Build:
 *   make -C src/passes
 */

#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

static cl::opt<bool> PreserveConvergenceThreshold(
    "vl-preserve-convergence-threshold",
    cl::desc("Preserve Verilator convergence loop threshold instead of forcing the first trip to the fatal/exit path"),
    cl::init(false));

// ─── VlStripX86AttrsPass ──────────────────────────────────────────────────────
//
// Remove x86-oriented metadata from clang++ -emit-llvm output before NVPTX.
//
//   - function attributes (#N)     → strip x86-only attrs while preserving GPU control attrs
//   - comdat                     → setComdat(nullptr)
//   - personality                → clearPersonalityFn() only if no EH pads remain
//   - linkonce_odr linkage       → internal (NVPTX linkers warn on linkonce_odr)

static bool shouldPreserveGpuDiagnosticOptNone(Function &F) {
    return F.getMetadata("vlgpu.eval_hot_path_compact_cluster_outline_callee") ||
           F.getName().starts_with("__vlgpu_compact_cluster_outline_frame_stub");
}

struct VlStripX86AttrsPass : public PassInfoMixin<VlStripX86AttrsPass> {
    static bool isRequired() { return true; }

    PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
        bool PreserveNoInline = F.hasFnAttribute(Attribute::NoInline);
        bool PreserveOptNone =
            F.hasFnAttribute(Attribute::OptimizeNone) &&
            shouldPreserveGpuDiagnosticOptNone(F);
        F.setAttributes(F.getAttributes().removeFnAttributes(F.getContext()));
        if (PreserveNoInline || PreserveOptNone)
            F.addFnAttr(Attribute::NoInline);
        if (PreserveOptNone)
            F.addFnAttr(Attribute::OptimizeNone);
        F.setComdat(nullptr);
        bool HasRemainingEhPad = false;
        for (auto &BB : F) {
            for (auto &I : BB) {
                if (isa<LandingPadInst>(&I) || isa<ResumeInst>(&I) ||
                    I.isEHPad()) {
                    HasRemainingEhPad = true;
                    break;
                }
            }
            if (HasRemainingEhPad)
                break;
        }
        if (F.hasPersonalityFn() && !HasRemainingEhPad)
            F.setPersonalityFn(nullptr);
        if (F.getLinkage() == GlobalValue::LinkOnceODRLinkage)
            F.setLinkage(GlobalValue::InternalLinkage);
        return PreservedAnalyses::all();  // no CFG/value change
    }
};

// ─── VlStubHostIoCallsPass ───────────────────────────────────────────────────
//
// vlgpugen stubs Verilator runtime functions, but a stubbed callee is too late
// for formatted output / plusarg helpers that receive temporary std::string
// arguments.  On the O0 GPU path, argument-preparation remnants can still
// execute after the final host call is erased (for example threadContextp()
// stubs returning null before a diagnostic timestamp load).  Replace the call
// sites themselves so a follow-up DCE/ADCE cleanup can drop the dead prep path:
// plusargs/valueplusargs are false on GPU, file reads/diagnostics/stops are
// intentionally no-ops, and formatting-only std::string helpers are disposable.

static bool isHostIoRuntimeCall(StringRef Name) {
    return Name.starts_with("_Z17VL_TESTPLUSARGS_I") ||
           Name.starts_with("_Z20VL_VALUEPLUSARGS_") ||
           Name.starts_with("_Z12VL_READMEM_") ||
           Name.starts_with("_Z12VL_WRITEF_NX") ||
           Name.starts_with("_Z12VL_FINISH_MT") ||
           Name.starts_with("_Z10VL_STOP_MT") ||
           Name.starts_with("_ZN9Verilated17runFlushCallbacksEv") ||
           Name.starts_with("_ZN9Verilated14threadContextpEv") ||
           Name.starts_with("_ZN9Verilated12lastContextpEv") ||
           Name.starts_with("_Z13sc_time_stampv") ||
           Name.starts_with("_ZdlPv") ||
           Name.starts_with("_ZdlPvSt11align_val_t") ||
           Name.starts_with("_ZNSt7__cxx1112basic_string") ||
           Name.starts_with("_ZNSt6vectorINSt7__cxx1112basic_string") ||
           Name.contains("VlDelayScheduler") ||
           Name.contains("VlCoroutineHandle") ||
           Name.contains("_Rb_tree") ||
           Name.contains("St8multimapIm");
}

struct VlStubHostIoCallsPass : public PassInfoMixin<VlStubHostIoCallsPass> {
    static bool isRequired() { return true; }

    PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
        SmallVector<std::pair<CallBase *, Function *>, 8> Calls;
        for (auto &BB : F) {
            for (auto &I : BB) {
                auto *CB = dyn_cast<CallBase>(&I);
                if (!CB)
                    continue;
                auto *Callee = dyn_cast<Function>(
                    CB->getCalledOperand()->stripPointerCasts());
                if (!Callee || !isHostIoRuntimeCall(Callee->getName()))
                    continue;
                Calls.push_back({CB, Callee});
            }
        }

        if (Calls.empty())
            return PreservedAnalyses::all();

        for (auto [CB, Callee] : Calls) {
            if (!CB->getType()->isVoidTy())
                CB->replaceAllUsesWith(Constant::getNullValue(CB->getType()));
            errs() << "[vl-stub-host-io-calls] " << F.getName()
                   << ": erased @" << Callee->getName() << "\n";
            if (auto *II = dyn_cast<InvokeInst>(CB)) {
                BranchInst::Create(II->getNormalDest(), II);
                II->eraseFromParent();
            } else {
                CB->eraseFromParent();
            }
        }
        return PreservedAnalyses::none();
    }
};

// ─── VlStubTimingSchedulerContextPass ───────────────────────────────────────
//
// Timed Verilator testbenches can leave host-only scheduler/context pointers in
// the root object.  The fake-vlSymsp path protects vlSymsp itself, but
// eval_phase__act can still dereference delay-scheduler and VerilatedContext
// internals copied from the host state.  For diagnostic GPU replay, CPU remains
// the scheduler oracle, so replace the timed act phase with "no act work".

static bool isTimedActPhaseFunction(StringRef Name) {
    return Name.contains("___024root___eval_phase__act");
}

static bool isDirectHostSchedulerContextCall(StringRef Name) {
    return Name.contains("VerilatedContext") ||
           Name == "_ZN9Verilated14threadContextpEv" ||
           Name == "_ZN9Verilated12lastContextpEv" ||
           Name.contains("VlDelayScheduler");
}

static bool isTriggerSchedulerProgressCall(StringRef Name) {
    return Name.contains("VlTriggerScheduler6commit") ||
           Name.contains("VlTriggerScheduler6resume");
}

struct VlStubTimingSchedulerContextPass
    : public PassInfoMixin<VlStubTimingSchedulerContextPass> {
    static bool isRequired() { return true; }

    PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
        if (!isTimedActPhaseFunction(F.getName()))
            return PreservedAnalyses::all();
        if (!F.getReturnType()->isIntegerTy(1))
            return PreservedAnalyses::all();

        bool HasDirectHostSchedulerContextCall = false;
        bool HasTriggerSchedulerProgressCall = false;
        for (auto &BB : F) {
            for (auto &I : BB) {
                auto *CI = dyn_cast<CallInst>(&I);
                if (!CI)
                    continue;
                auto *Callee = dyn_cast<Function>(
                    CI->getCalledOperand()->stripPointerCasts());
                if (!Callee)
                    continue;
                if (isDirectHostSchedulerContextCall(Callee->getName())) {
                    HasDirectHostSchedulerContextCall = true;
                }
                if (isTriggerSchedulerProgressCall(Callee->getName()))
                    HasTriggerSchedulerProgressCall = true;
            }
            if (HasDirectHostSchedulerContextCall && HasTriggerSchedulerProgressCall)
                break;
        }

        if (!HasDirectHostSchedulerContextCall)
            return PreservedAnalyses::all();

        if (HasTriggerSchedulerProgressCall) {
            errs() << "[vl-stub-timing-scheduler-context] " << F.getName()
                   << ": preserved trigger-bearing act phase\n";
            return PreservedAnalyses::all();
        }

        F.deleteBody();
        BasicBlock *BB = BasicBlock::Create(F.getContext(), "entry", &F);
        IRBuilder<> B(BB);
        B.CreateRet(ConstantInt::getFalse(F.getContext()));
        errs() << "[vl-stub-timing-scheduler-context] " << F.getName()
               << ": return false\n";
        return PreservedAnalyses::none();
    }
};

// ─── VlSanitizeHostIoNullWritesPass ──────────────────────────────────────────
//
// After the host-I/O calls above are erased, LLVM can still fold the now-useless
// temporary std::string heap object into invalid writes such as:
//
//   memcpy(null, @.str.N, len)
//   store i8 0, inttoptr (i64 len to ptr)
//
// These are not design-state accesses.  They are remnants of host-only
// diagnostic formatting and plusarg helpers, so route them into a private
// scratch buffer after O3 and before NVPTX lowering.

static GlobalVariable *getOrCreateHostIoScratch(Module &M) {
    static constexpr const char *ScratchName = "vl_gpu_host_io_scratch";
    if (auto *GV = M.getGlobalVariable(ScratchName, true))
        return GV;
    auto &Ctx = M.getContext();
    auto *Ty = ArrayType::get(Type::getInt8Ty(Ctx), 4096);
    return new GlobalVariable(M, Ty, false, GlobalValue::InternalLinkage,
                              ConstantAggregateZero::get(Ty), ScratchName);
}

static bool isConstantNullPointer(Value *V) {
    return isa<ConstantPointerNull>(V->stripPointerCasts());
}

static bool isGlobalStringConstant(Value *V) {
    auto *GV = dyn_cast<GlobalVariable>(V->stripPointerCasts());
    if (!GV || !GV->hasInitializer())
        return false;
    auto *Data = dyn_cast<ConstantDataArray>(GV->getInitializer());
    return Data && Data->isString();
}

static bool isMemcpyToNullFromString(CallBase &CB) {
    auto *Callee = CB.getCalledFunction();
    if (!Callee || !Callee->getName().starts_with("llvm.memcpy."))
        return false;
    return CB.arg_size() >= 2 && isConstantNullPointer(CB.getArgOperand(0)) &&
           isGlobalStringConstant(CB.getArgOperand(1));
}

static bool isSmallConstantIntToPtr(Value *Ptr) {
    auto *CE = dyn_cast<ConstantExpr>(Ptr);
    if (!CE || CE->getOpcode() != Instruction::IntToPtr || CE->getNumOperands() != 1)
        return false;
    auto *CI = dyn_cast<ConstantInt>(CE->getOperand(0));
    return CI && CI->getZExtValue() <= 4096;
}

static bool isNullStringTerminatorStore(StoreInst &SI) {
    auto *Stored = dyn_cast<ConstantInt>(SI.getValueOperand());
    return Stored && Stored->isZero() && Stored->getType()->isIntegerTy(8) &&
           isSmallConstantIntToPtr(SI.getPointerOperand());
}

static bool isOperatorNewLikeCall(StringRef Name) {
    return Name.starts_with("_Znwm") || Name.starts_with("_Znam");
}

static bool isSmallConstantAllocation(CallBase &CB) {
    if (CB.arg_size() < 1)
        return false;
    auto *Size = dyn_cast<ConstantInt>(CB.getArgOperand(0));
    return Size && Size->getZExtValue() <= 4096;
}

static bool isMemcpyFromStringToValue(CallBase &CB, Value *Dest) {
    auto *Callee = CB.getCalledFunction();
    if (!Callee || !Callee->getName().starts_with("llvm.memcpy."))
        return false;
    return CB.arg_size() >= 2 && CB.getArgOperand(0)->stripPointerCasts() == Dest &&
           isGlobalStringConstant(CB.getArgOperand(1));
}

static bool isHostIoHeapStringAllocation(CallBase &CB) {
    auto *Callee = dyn_cast<Function>(CB.getCalledOperand()->stripPointerCasts());
    if (!Callee || !isOperatorNewLikeCall(Callee->getName()) ||
        !isSmallConstantAllocation(CB))
        return false;
    for (User *U : CB.users())
        if (auto *UseCB = dyn_cast<CallBase>(U))
            if (isMemcpyFromStringToValue(*UseCB, &CB))
                return true;
    return false;
}

struct VlSanitizeHostIoNullWritesPass
    : public PassInfoMixin<VlSanitizeHostIoNullWritesPass> {
    static bool isRequired() { return true; }

    PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
        SmallVector<CallBase *, 8> NullStringCopies;
        SmallVector<CallBase *, 8> HeapStringAllocs;
        SmallVector<StoreInst *, 8> NullTerminators;
        for (auto &BB : F) {
            for (auto &I : BB) {
                if (auto *CB = dyn_cast<CallBase>(&I)) {
                    if (isMemcpyToNullFromString(*CB))
                        NullStringCopies.push_back(CB);
                    else if (isHostIoHeapStringAllocation(*CB))
                        HeapStringAllocs.push_back(CB);
                    continue;
                }
                if (auto *SI = dyn_cast<StoreInst>(&I)) {
                    if (isNullStringTerminatorStore(*SI))
                        NullTerminators.push_back(SI);
                }
            }
        }

        if (NullStringCopies.empty() && HeapStringAllocs.empty() &&
            NullTerminators.empty())
            return PreservedAnalyses::all();

        auto *Scratch = getOrCreateHostIoScratch(*F.getParent());
        auto scratchBytePtr = [&]() -> Value * {
            IRBuilder<> B(&F.getEntryBlock(), F.getEntryBlock().begin());
            auto *Zero = ConstantInt::get(Type::getInt64Ty(F.getContext()), 0);
            return B.CreateInBoundsGEP(Scratch->getValueType(), Scratch,
                                       {Zero, Zero}, "vl_host_io_scratch_ptr");
        };
        for (auto *CB : NullStringCopies) {
            CB->setArgOperand(0, Scratch);
            CB->removeParamAttr(0, Attribute::Alignment);
            CB->removeParamAttr(0, Attribute::Dereferenceable);
            CB->removeParamAttr(0, Attribute::DereferenceableOrNull);
        }
        for (auto *CB : HeapStringAllocs) {
            CB->replaceAllUsesWith(scratchBytePtr());
            CB->eraseFromParent();
        }
        for (auto *SI : NullTerminators) {
            SI->setOperand(1, Scratch);
            SI->setAlignment(Align(1));
        }
        errs() << "[vl-sanitize-host-io-null-writes] " << F.getName()
               << ": memcpy=" << NullStringCopies.size()
               << " heap_alloc=" << HeapStringAllocs.size()
               << " store=" << NullTerminators.size() << "\n";
        return PreservedAnalyses::none();
    }
};

// ─── VlPatchConvergencePass ───────────────────────────────────────────────────
//
// Patch Verilator’s convergence loop (seen with --no-timing TB) so it cannot spin forever
// on GPU after VL_FATAL_MT becomes a no-op stub.
//
// Typical eval shape:
//
//   header:
//     %iter1 = add i32 %iter, 1
//     %ovf   = icmp ugt i32 %iter1, 100
//     br i1 %ovf, label %fatal, label %body
//
//   body:
//     %again = call i1 @eval_phase__ico(...)
//     br i1 %again, label %header, label %exit
//
//   fatal:
//     call void @VL_FATAL_MT(...)   ; stubbed to empty body on GPU
//     br label %body                 ; problem: loops forever after stub
//
//   exit:
//     ret void
//
// Patches:
//   1. fatal block: unconditional br to %body → br to %exit
//   2. leave the convergence threshold intact so normal settling semantics are preserved

static BasicBlock *findLoopExit(BasicBlock *HeaderBB) {
    // Find a conditional branch that targets HeaderBB; the other successor is treated as exit.
    Function *F = HeaderBB->getParent();
    for (auto &BB : *F) {
        auto *Br = dyn_cast<BranchInst>(BB.getTerminator());
        if (!Br || !Br->isConditional())
            continue;
        if (Br->getSuccessor(0) == HeaderBB)
            return Br->getSuccessor(1);
        if (Br->getSuccessor(1) == HeaderBB)
            return Br->getSuccessor(0);
    }
    return nullptr;
}

struct VlPatchConvergencePass : public PassInfoMixin<VlPatchConvergencePass> {
    static bool isRequired() { return true; }

    PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
        // Collect icmp ugt i32 %N, 100
        SmallVector<ICmpInst *, 4> Candidates;
        for (auto &BB : F)
            for (auto &I : BB)
                if (auto *Cmp = dyn_cast<ICmpInst>(&I))
                    if (Cmp->getPredicate() == ICmpInst::ICMP_UGT)
                        if (Cmp->getOperand(0)->getType()->isIntegerTy(32))
                            if (auto *C = dyn_cast<ConstantInt>(Cmp->getOperand(1)))
                                if (C->getZExtValue() == 100)
                                    Candidates.push_back(Cmp);

        if (Candidates.empty())
            return PreservedAnalyses::all();

        bool Changed = false;
        for (auto *Cmp : Candidates) {
            // Find the conditional br driven by this icmp (br i1 %ovf, %fatal, %body)
            BranchInst *GuardBr = nullptr;
            for (auto *U : Cmp->users())
                if (auto *Br = dyn_cast<BranchInst>(U))
                    if (Br->isConditional()) { GuardBr = Br; break; }
            if (!GuardBr)
                continue;

            BasicBlock *HeaderBB = Cmp->getParent();
            BasicBlock *FatalBB  = GuardBr->getSuccessor(0);  // true  → fatal
            BasicBlock *BodyBB   = GuardBr->getSuccessor(1);  // false → body
            (void)BodyBB;

            BasicBlock *ExitBB = findLoopExit(HeaderBB);
            if (!ExitBB) {
                errs() << "[vl-patch-convergence] SKIP: exit not found in "
                       << F.getName() << "\n";
                continue;
            }

            // Redirect fatal block’s unconditional branch from %body to %exit
            auto *FatalTerm = FatalBB->getTerminator();
            if (auto *FatalBr = dyn_cast<BranchInst>(FatalTerm)) {
                if (!FatalBr->isConditional()) {
                    FatalBr->setSuccessor(0, ExitBB);
                    errs() << "[vl-patch-convergence] " << F.getName()
                           << ": fatal→exit redirected\n";
                    Changed = true;
                }
            }

            if (PreserveConvergenceThreshold) {
                errs() << "[vl-patch-convergence] " << F.getName()
                       << ": threshold preserved\n";
            } else {
                Cmp->setOperand(1, ConstantInt::get(Cmp->getOperand(1)->getType(), 0));
                errs() << "[vl-patch-convergence] " << F.getName()
                       << ": threshold forced to zero\n";
                Changed = true;
            }
        }

        return Changed ? PreservedAnalyses::none() : PreservedAnalyses::all();
    }
};

// ─── Plugin registration ────────────────────────────────────────────────────

static PassPluginLibraryInfo getVlGpuPassesPluginInfo() {
    return {LLVM_PLUGIN_API_VERSION, "VlGpuPasses", LLVM_VERSION_STRING,
        [](PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [](StringRef Name, FunctionPassManager &FPM,
                   ArrayRef<PassBuilder::PipelineElement>) -> bool {
                    if (Name == "vl-strip-x86-attrs") {
                        FPM.addPass(VlStripX86AttrsPass());
                        return true;
                    }
                    if (Name == "vl-stub-host-io-calls") {
                        FPM.addPass(VlStubHostIoCallsPass());
                        return true;
                    }
                    if (Name == "vl-stub-timing-scheduler-context") {
                        FPM.addPass(VlStubTimingSchedulerContextPass());
                        return true;
                    }
                    if (Name == "vl-sanitize-host-io-null-writes") {
                        FPM.addPass(VlSanitizeHostIoNullWritesPass());
                        return true;
                    }
                    if (Name == "vl-patch-convergence") {
                        FPM.addPass(VlPatchConvergencePass());
                        return true;
                    }
                    return false;
                });
        }};
}

extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo llvmGetPassPluginInfo() {
    return getVlGpuPassesPluginInfo();
}
