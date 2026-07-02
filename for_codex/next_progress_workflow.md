# 次に進めるための作業プロトコル

このメモは、ユーザーが「引き続き進めて」「次は何をやるべき」
「GitHubを確認してタスク整理」「goal機能を使って進めて」と依頼した
ときに、Codexが止まらずにプロジェクトを前進させるための手順である。

## 基本姿勢

- まずGitHub issueと`for_codex/issues.md`を確認し、既存の受け皿があるか
  判断する。
- 既存issueで表現できる作業なら新規issueを作らず、該当FCファイルを更新する。
- 既存issueがない独立した実装・測定・検証作業だけ、新しいタスクissueにする。
- 「GPUが速い」「有用」と言う前に、正しさ、測定範囲、CPU基準を分けて証明する。
- 生成物は`artifacts/`または`reports/`に置き、判断や目標は
  `for_codex/`、`docs/`、`config/`側に残す。

## 毎回の開始手順

1. `for_codex/AGENTS.md`を読む。
2. GitHubで現在の関連issueを確認する。
   - RTLMeter direct-native correctness: FC-058 / #58
   - RTLMeter timing and usefulness: FC-037 / #2
   - RTLMeter second seed: FC-040 / #4
   - native `obj_dir/V<top>` sidecar runtime: FC-057 / #57 and child issues
3. goalが未設定なら、そのターンで達成する具体ゴールを作る。
4. 作業前に「今回進める最小単位」を1つ選ぶ。
5. 変更する前に、対象ファイルと既存テストを読む。
6. 実装、検証、GitHub/for_codexへの結果記録までを1セットにする。

## 現在の最短ルート

RTLMeterでGPU有用性を確認する道筋は次の順序で進める。

1. 完了済み前提を維持する。
   - FC-064 / #63で、`VeeR-EL2:default:hello` はdirect sidecarの
     stdout/cycles correctnessを通過済み。
   - FC-037 / #2で、4-state、8-state、16-stateのCPU-parallel比較付き
     `hello` timing gateを測定済み。
   - 最新のfiltered 16-state scaling gateは、3 batch x 7 samplesで21/21 correctness pass、
     `sidecar_wall_s_median=0.768573s`,
     `sidecar_wall_s_per_parallel_state_median=0.048036s`,
     `sidecar_vs_cpu_parallel_ratio=2.887022`,
     `gpu_kernel_ms_total_median=268.161011ms`,
     `step_trace_copy_mode_counts={"device_buffered_coalesced_d2d_trace": 21}`,
     `step_trace_filter_rows_median=727.0`,
     `resident_patch_records_median=69936.0`。
   - 8-state比ではtotal wallが`1.258905x`悪化する一方、
     per-state wall/states/sは約`1.589x`改善する。
   - previous filtered 16-state runは`0.643080s`まで出ているが、
     latest rerunは悪化しており、robustな新規speedupとは扱わない。
   - delta patch-script化はpatch recordを減らしたがfull gateで悪化したため非採用。
   - CPU-as-GPU fallbackは常に不可能にする。
2. non-`hello` `dhry` の現在地を優先する。
   - CPU full runは `reports/rtlmeter_cpu_dhry_serial_baseline.json` で
     `5984259` cycles / `37.240654s`。
   - GPU bank-init 200000-cycle probeは
     `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk200000_dccm_init_final_stdout_200000.json`
     で `mcycle=199999`, `minstret=191985`, `finish_marker_observed=false`。
   - 同じ `mcycle` のCPU snapshotではCPUがGPUより52-53命令多くretireし、
     PCも一致しない。
   - `+iterations=17500` を外しても、CPU-minus-GPU `minstret` deltaは
     3窓すべてで`65`のまま。
   - CPUを`mcycle-65`で見ると長い窓は近づくが、短い窓は揃わない。
   - `post_reset_posedges=N+2`でCPU `mcycle`をGPU窓に合わせても、
     `minstret`/PCはGPUに一致しない。
   - CPU reset-release early snapshotは追加済み:
     post-reset posedge `1/2/3` は `mcycle=0/minstret=0/pc=0`,
     posedge `4` は `mcycle=1`, posedge `500` は
     `mcycle=497/minstret=360/pc=0x400002d1`。
   - 既存GPU 500-cycle reportはpre-bank-initなので、現在のbank-init pathとの
     比較には弱い。
   - bank-init付きGPU 500/750/875/1000/2000 reportは生成済み。
   - CPUを`post_reset_posedges=N+2`で見ると、500/750/875 cycleは
     GPUと`mcycle/minstret/PC/mailbox`が一致する。
   - 1000 cycleで初めて分岐する:
     CPU `mcycle=999/minstret=746/pc=0x40000194/obuf=117`,
     GPU `mcycle=999/minstret=709/pc=0x40000270/obuf=32`。
   - GPU step traceには `mcycle/minstret/pc` を追加済みで、
     `reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_875_1000.json`
     がCPU traceと比較する。
   - 比較時の対応は `cpu_post_reset_posedges=gpu_step+3`。
   - progress-only traceでは `gpu_step=896` / CPU post-reset `899` までは
     一致し、`gpu_step=897` / CPU post-reset `900` でPCだけがずれていた。
   - `pc_d` 追加後、さらにdecode/fetch debug traceを追加した比較では
     最初の差分がさらに1行早く絞れる:
     `reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_debug_875_1000.json`
     は `gpu_step=894` / CPU post-reset `897` まで一致し、
     `gpu_step=895` / CPU post-reset `898` で `decode_d` と `fetch_stall`
     だけがずれる。
   - この時点でも `mcycle=895/minstret=669/pc=0x4000026e/pc_d=0x40000270/pc_din=0x4000026e/instr_d=0x0334c4b3/obuf=32` は一致する。
   - CPUは `decode_d=1/fetch_stall=0`、GPUは
     `decode_d=0/fetch_stall=1`。後続の `pc_d` 差分、登録PC差分、
     `minstret`遅れは、GPU側のfetch stallが1 sampled cycle長く残ることの
     結果として扱う。
   - 次の最優先は `gpu_step=895` 周辺の `ifu_pmu_fetch_stall` /
     `dec_i0_decode_d` eval順序またはsettle不足を監査・修正し、
     bounded trace compareを再実行すること。
   - phase-split ordering probeは前進した:
     `reports/rtlmeter_veer_el2_dhry_phase_nba_loop_trial_summary.json`。
     `_eval_phase__act` の過剰stub、phase kernelのsyms self-pointer補修漏れ、
     legacy `vl_nba_comb_batch_gpu` / `vl_nba_sequent_batch_gpu` 直呼びは修正し、
     現在のsequenceは `vl_ico_batch_gpu`, `vl_eval_loop_batch_gpu`。
     1000-cycle traceは全ゼロではなくなり、
     single eval kernelと同じ最終observablesに到達する。
   - ただし `gpu_step=895` ではまだ `fetch_stall=1` / `decode_d=0` で、
     CPUの `fetch_stall=0` / `decode_d=1` とずれる。
   - 入力依存traceは
     `reports/rtlmeter_veer_el2_dhry_fetch_inputs_compare_875_1000.json`。
     同じ行で `decode_valid_gate=1` と `fetch_fbwrite=0x038` は一致するが、
     GPUだけ `decode_misc2ff=4`, `decode_i0_exublock=1`,
     `fetch_consume_gate=0` になる。次はphase順序全体ではなく、
     `misc2ff`/exublock と fetch-consume gate の更新順序を切り分ける。
   - 追加のAXI入力traceは
     `reports/rtlmeter_veer_el2_dhry_axi_inputs_compare_875_1000.json`。
     divergent windowではvalidなIFU応答入力はCPU/GPUで一致し、差分は
     invalidな `lmem_axi_rdata` fillerに限られる。次は外部命令応答ではなく、
     IFU内部を追う。
   - IFU consume/request traceは
     `reports/rtlmeter_veer_el2_dhry_ifu_consume_compare_875_1000.json`。
     `gpu_step=894` までは追加fieldも一致し、`gpu_step=895` / CPU
     post-reset `898` で `ifu_ifc_fetch_req_bf` が `CPU=1` / `GPU=0`,
     `ifu_ifc_fb_write_ns` が `CPU=4` / `GPU=8` に分岐する。request/response
     相当の `tb_ifu_axi_arready`, `ifu_bus_cmd_valid`,
     `ifu_bus_rd_addr_count`, `ifu_fetch_addr_f`, `ifu_pmp_addr`,
     `tb_ifu_axi_rvalid/rid/rdata` と miss-state 系は同じなので、次は
     IFC fetch-buffer consume/request next-state logicを修正対象にする。
3. FC-037 / #2で次の測定・改善を継続する。
   - serial CPU
   - CPU parallel simulations with isolated work roots
   - GPU wall time
   - GPU kernel diagnostics
   これらを別フィールドで記録する。
4. GPUが有用かは、serial CPUだけでなくbest CPU-parallel baselineとも比較して
   判定する。遅い、同等、未測定も有効な結果として記録する。
5. longer non-`hello` GPU finish probeやspeedup/usefulness wordingは、
   same-window progress mismatchを説明または修正してからにする。
6. FC-040 / #4のsecond seedは、FC-037の現在結果と残ブロッカーをレビューしてから
   開始する。

## CPU並列SIMを進めるとき

CPU並列SIMは新規FC issueではなく、FC-037 / #2の測定方法として扱う。

実装・測定時の条件:

- 同じRTLMeter seedをCPU-onlyで複数プロセス実行する。
- 各workerは独立したwork rootを使い、`obj_dir`や実行ログを共有しない。
- worker数は1, 2, 4, 可能ならローカルcore上限までsweepする。
- reportには少なくとも次を残す。
  - worker count
  - wall time
  - completed simulations per second
  - per-run normalized stdout hash
  - RTLMeter cycle count
  - pass/fail
- すべてのpassing runでstdout/cyclesが一致しない限り、CPU並列baselineとして
  採用しない。

## issue追加の判断

新規issueを作る条件:

- 既存FCではscopeが混ざる。
- 受け入れ条件を独立して定義できる。
- GitHub上で他agentやレビュー担当に共有する必要がある。
- 完了しても既存issue全体は閉じられないが、明確な前進になる。

新規issueを作らない条件:

- correctnessならFC-058に入る。
- timing、CPU並列baseline、有用性判定ならFC-037に入る。
- second seedならFC-040に入る。
- `pulp_ita_mha`のapples-to-apples timingならFC-056に入る。
- 単なる状況整理、検証結果、ブロッカー更新なら既存issueコメントと
  FCファイル更新で足りる。

## 完了条件

作業を「進めた」と言えるのは、少なくとも次のどれかを満たしたときだけ。

- ブロッカーが1つ具体化され、GitHub issueまたはFCファイルに記録された。
- 既存ブロッカーを解く実装が入り、関連テストが通った。
- 実測reportが生成され、何が測れたか、何が未測定かが明記された。
- fail-closed結果が再現可能なコマンド付きで記録された。
- 次のagentが迷わず着手できるacceptance/validationが更新された。

単にログを読んだだけ、未検証の推測を書いただけ、生成reportを作っただけでは
前進扱いにしない。

## 最低限の検証

ドキュメントだけの変更:

```sh
git diff --check
```

RTLMeter runnerやcompare周辺を触った変更:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_rtlmeter_verilator_wrapper_runtime \
  tests.contract.test_rtlmeter_stdout_cycles_runner_contract \
  tests.contract.test_rtlmeter_cpu_gpu_compare_integration -q
PYTHONDONTWRITEBYTECODE=1 make surface
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/check_staged_large_files.py
```

Verilator patchやnative sidecar hookを触った変更:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_verilator_native_sidecar_makefile_build_hook_patch \
  tests.contract.test_verilator_native_sidecar_direct_shim_v5_044_patch -q
git diff --check
```

## 禁止する近道

- proxy/marker/review-manifest laneをGPU実行証拠として復活させない。
- CPU実行をGPU実行として扱わない。
- `pulp_ita_mha`の成功をRTLMeter first seed成功として扱わない。
- GPU kernel timeだけをCPU wall timeと比較しない。
- 1回の実行だけでspeedupを主張しない。
- generated JSONをruntime ABIやsource of truthとして扱わない。
