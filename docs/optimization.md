# Measured optimization

Linux CPU results on Intel Core i9-13900K (24 physical / 32 logical cores,
approximately 94 GiB RAM), Python 3.12, torch 2.14.1+cpu. CPU ISA dispatch in
PyTorch reported AVX2. No Windows or GPU inference result is claimed.

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
Windows MSVC builds and CUDA offload still require testing on their target host.
GPU selection checks free VRAM; native offload additionally needs a CUDA-enabled
build. Allocation failure in auto mode falls back to CPU. Forced CUDA fails clearly.

StartLux 4B currently has metadata but neither complete safetensors shard. It is
reported as unavailable; its speed, memory and prediction behavior are unmeasured.
The execution sandbox cannot see host NVIDIA devices or the 8881 listener and
forbids socket binding. Thus host HTTP exposure, GPU testing, Windows runtime and
browser rendering remain unverified. Dashboard routes/authentication are tested
through ASGI and JavaScript syntax is checked. CI includes Ubuntu/Windows API and
operations tests without model weights; it has not run remotely yet.

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
