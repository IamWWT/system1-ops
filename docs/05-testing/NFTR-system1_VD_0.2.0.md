---
title: 性能验证报告
type: report
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 性能验证报告

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

Linux CPU results on Intel Core i9-13900K (24 physical / 32 logical cores,
approximately 94 GiB RAM), Python 3.12, torch 2.14.1+cpu. CPU ISA dispatch in
PyTorch reported AVX2. Initial CPU measurements used the existing CPU runtime; subsequent GPU tests used an independent torch 2.12.0+cu130 environment and a CUDA 12.8 native build on driver 580.178.04. Original CPU environments and checkpoints remain unchanged.

| Model / implementation | Threads | P50 ms | Peak RSS MiB | Largest probability drift | Gate |
|---|---:|---:|---:|---:|---|
| Laya FP32 reference | 4 | 1244.55 | 2792.93 | 0 | pass |
| Laya FP32 | 8 | 822.17 | 2677.61 | 0 | pass |
| Laya encoder dynamic INT8 | 4 | 796.00 | 2364.86 | 0.4886 | **reject** |
| StartLux 0.8B BF16 reference | 4 | 17184.95 | 1786.49 | 0 | pass |
| StartLux 0.8B FP32 | 8 | 1910.13 | 5531.39 | 0.00444 | pass |
| StartLux 0.8B C++ Q8_0 | 4 | 2316.65 | 1645.15 | 0.00985 | pass |
| StartLux 0.8B C++ Q8_0 | 8 | 1482.83 | 1645.00 | 0.00985 | pass |

The C++ candidate reduces median latency about 22% and observed peak RSS about
70% relative to the fastest measured FP32 PyTorch candidate. Relative to the
original BF16 baseline it is about 11.6x faster. These are measurements on a
small fixed workload, not broad model accuracy claims or a universal optimum.
The C++ 8-thread P95 was 5251.40 ms; long and short requests differ substantially.

One additional native long-input check completed a 4,668-token rendered prompt
with one noul question in 18.17 seconds. With request max_len=4096 it was rejected;
with max_len=8192 the full prompt was accepted. This single observation is not a
long-context latency distribution or a maximum-context qualification.

Each candidate uses a fresh process, one warm-up, four synthetic fixtures
(billing/technical × short/roughly 500-token context), three Jev question types,
and two timed repetitions per fixture. Fixtures and their SHA256 are generated
by `benchmark.py`. PyTorch rows were measured together; C++ rows were measured
afterward using identical fixtures. Background host workloads were uncontrolled.
Peak RSS is sampled every 20 ms, includes the C++ child, and can miss short spikes;
shared/mmap pages counted by RSS do not equal exclusive physical memory use.
CPU seconds from the initial C++ runs counted only the parent, so are omitted
from the public sample. The current harness includes child CPU time.

Numerical gate: every choice must agree and the largest probability, confidence,
normalized score or noul drift must be ≤0.02. This rejected Laya INT8. It does not
prove quantized accuracy on other questions, multilingual inputs or long contexts.
The converted local Q8 file is 822.6 MB and uses the original tokenizer and
decision_config calibration. Original weights remain untouched.

The native driver decodes all prompt tokens and reads only option-letter logits
at the final position. It resets recurrent/KV state between questions. The
upstream Jev renderer and temperature calibration remain authoritative. No
generative answer sampling or full-vocabulary probability transport is needed.
The Python gateway still imports torch for upstream decision arithmetic; C++
replaces the expensive transformer forward pass. Laya continues to use its
specialized PyTorch encoder/head; it is not a generative GGUF model.

CPU BF16 is selected automatically only when Linux exposes native BF16 flags.
Windows detection conservatively selects FP32 in the PyTorch fallback. Native
llama.cpp builds use `GGML_NATIVE=OFF`, backend loading and CPU ISA variants,
so migration does not require the same instruction set as the build machine.
Windows MSVC CPU builds, official Q8 inference, PowerShell startup, real HTTP and dashboard APIs passed on GitHub windows-latest. This is portability evidence, not a performance measurement on the user's laptop. CUDA offload was tested on the RTX 4090 host.
GPU selection checks free VRAM; native offload additionally needs a CUDA-enabled
build. Allocation failure in auto mode falls back to CPU. Forced CUDA fails clearly.

## RTX 4090 measurements

Four identical fixtures and three Jev question types, three timed repeats per fixture, one warm-up. CUDA calls synchronize around measured inference. Background host workloads were uncontrolled.

| Implementation | P50 ms | P95 ms | Observed native/driver VRAM MiB | Drift / gate |
|---|---:|---:|---:|---|
| Laya FP32 eager | 26.28 | 46.07 | not sampled | 0 / pass |
| Laya FP32 + TF32 eager | **20.29** | **31.83** | 2362 | 0.0014 / pass |
| Laya BF16 eager | 17.50 | 22.11 | not sampled | 0.1018 / reject |
| Laya BF16 compile | 18.92 | 28.40 | not sampled | 0.0301 / reject |
| Laya FP32 compile | 34.44 | 64.52 | 2638 | 0 / pass |
| Laya BF16 Tilelang | 12.19 | 7397.38 | 3206 | 0.0074 / pass |
| StartLux 0.8B C++ Q8 CUDA | **32.96** | **46.86** | 1912 | 0.01065 / pass |
| StartLux 4B official Q8 CPU / 8 threads | 966.12 | 1068.18 | — | Q8 CPU reference |
| StartLux 4B official Q8 CUDA / 4 threads | **82.48** | **121.14** | 5772 | 0.0000014 vs Q8 CPU / pass |

4B CPU uses two repeats per fixture; CUDA uses three. Its sampled peak process-tree RSS was 5763 MiB on CPU and 4848 MiB on CUDA, including load-time transient mappings. A separate real HTTP request processed 10,050 rendered tokens in 0.750 seconds at a 16K context limit; max_len=8192 returned 422. This is a single observation.

The TF32 eager default balances measured latency, memory and numerical compatibility. Tilelang has a faster median but higher VRAM and substantial compilation delay for a new input shape after the first fixture warm-up. `torch.compile` also increased total sampled RSS substantially through compiler subprocesses. These candidates remain configurable, not unconditional recommendations.

Driver VRAM is a process-tree observation near the end of a run, **not a sampled peak**; torch peak allocated/reserved values describe torch allocations only. The 0.8B native CUDA result includes Python gateway plus native child RSS (1368 MiB); its transformer computation runs in C++. Public GPU summary retains rejected candidates and individual settings.

Additional 0.8B GPU observations: 4,668 rendered tokens completed in 0.144 seconds. A 36,924-token prompt completed under context_length=65536 in 1.136 seconds, with native process VRAM 2488 MiB; max_len=32768 rejected it. These are single-question observations, not accuracy or tail-latency qualification at 64K.

4B was restored using the official Q8_0 GGUF repository at revision `3e98f4efc5b9f1c9c9232cc40f862a3b872cc33f`. The 4,482,402,816-byte file SHA256 is `3de47f14ca2807813a670d697e70815fbecf020732ca4d7fc5f2e6c3898e34df`; it matches the Hub download metadata. Original incomplete safetensors files were retained and are not used. GPU loading and all three Jev question types passed at port 8884. Its CPU/GPU comparison uses the **same official Q8 file**; without complete original weights this does not establish 4B quantization fidelity relative to BF16.

The authorized port 8881 listener was stopped and GPU memory released. All model ports bind 0.0.0.0; local and LAN-address HTTP checks and browser rendering are tested. Reachability from a separate external client depends on routing/firewall and has not been measured here. Browser verification covers authenticated model state, Jev debug responses, desktop/mobile layout and absence of JavaScript errors. The Windows native validation also covers dashboard and model stop/start after real HTTP traffic ([successful run](https://github.com/IamWWT/system1-ops/actions/runs/37898577693)). POSIX port probing permits TIME_WAIT while still rejecting live listeners; Windows uses exclusive binding ([Microsoft socket semantics](https://learn.microsoft.com/en-us/windows/win32/winsock/so-exclusiveaddruse)).

Low-RAM profiles serialize model requests across processes and unload after every request. A real 0.8B CPU test verified repeated requests and native process/weight teardown; unit tests verify overlapping requests cannot load two model sets simultaneously. Python process/dependency overhead persists and reload latency is intentional. Windows laptop hardware remains to be benchmarked.

Primary references used in selecting experiments:

* [PyTorch tuning guide](https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html):
  tune CPU threading/placement and measure implementation costs.
* [StartLux upstream](https://github.com/StartLuxLabs/StartLux-Decision):
  the native GGUF readout preserves decision formatting and calibration; upstream
  recommends Q8 over more lossy Q4 for probability-sensitive applications.
* [ONNX Runtime quantization guide](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html):
  quantization requires accuracy/debugging checks rather than latency alone.

Re-run on each device:

```bash
python benchmark.py --model all --preset quick
# Larger context sweep; increase candidate timeout for CPU/4B.
python benchmark.py --model startlux-0.8b --preset full --candidate-timeout 1800
# User explicitly authorized releasing 8881. This stops only an identified listener.
python benchmark.py --model all --release-port 8881 --devices cpu cuda
```

If 8881 belongs to a supervised or Docker service, stop it through that supervisor
before testing; killing a proxy does not guarantee releasing its GPU-owning worker.
The script refuses to claim release when no listener can be identified or it restarts.

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
