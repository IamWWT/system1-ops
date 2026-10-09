# System1 Ops

一个项目维护 Laya、StartLux Decision 0.8B / 4B：统一 TOML 配置、Jev API、设备选择、运维页面、进程生命周期、日志和性能测试。StartLux 可选 **C++ llama.cpp 原生推理**，FastAPI 负责公共接口与运维；Laya 使用自己的 PyTorch encoder/head。每模型单实例进程，避免 HTTP 多 worker 复制权重。这是统一服务与运维框架，各模型复用适合自己的内核。

| 服务 | 默认监听 |
|---|---|
| Laya | `0.0.0.0:8882` |
| StartLux 0.8B | `0.0.0.0:8883` |
| StartLux 4B | `0.0.0.0:8884` |
| 运维台 | `0.0.0.0:8885` |

外部访问使用宿主机 IP。模型认证使用 `SYSTEM1_API_KEY` 和 Bearer header；运维操作使用 `SYSTEM1_ADMIN_KEY`。未设置管理密钥时页面只读；已设置时所有 `/ops` 接口须认证。页面支持启停重启、状态/资源、日志、Jev JSON 调试、性能报告，不依赖 npm/CDN；密钥只保存在当前页面内存。

## 已测结果

i9-13900K Linux CPU，四组输入、每组三个 Jev 题型、两次计时：

| 实现 | P50 | 峰值 RSS |
|---|---:|---:|
| Laya FP32 / 4线程 | 1.245 s | 2.73 GiB |
| Laya FP32 / 8线程 | **0.822 s** | **2.61 GiB** |
| StartLux 0.8B 原始 BF16 / 4线程 | 17.185 s | 1.74 GiB |
| StartLux 0.8B FP32 / 8线程 | 1.910 s | 5.40 GiB |
| StartLux 0.8B C++ Q8 / 8线程 | **1.483 s** | **1.61 GiB** |

C++ 内存包含 Python 网关和原生子进程。选项全部一致，最大概率差0.00985，通过本次 ≤0.02门槛。Laya INT8 概率差0.4886，**拒绝作为默认配置**。这些测试不等于业务准确率或全局最优，见 [实验方法和限制](docs/optimization.md) 与 [公开汇总](reports/samples/linux-i9-13900k.json)。

24项本地 API/运维测试及 C++ 真实推理、非法 token 恢复、请求隔离、卸载重载、上下文限制验证通过。GPU、Windows实机、对外HTTP和4B尚未实测：执行沙箱隔离宿主GPU/进程、禁止socket，4B两个分片不完整。Windows CI已配置，未远程运行。额外原生长输入4668tokens单题18.17秒，4096上限时明确拒绝。

## Linux / 已有环境

`config.toml` 是私有配置，未提交。模板使用项目内 `vendor/`、`models/`。已有权重直接填写 `python`、`source`、`path`，不会重复下载。相对路径以配置文件目录为基准。

```bash
cp config.example.toml config.toml
./setup-runtime.sh cpu
export SYSTEM1_PYTHON="$PWD/.venv-cpu/bin/python"
"$SYSTEM1_PYTHON" bootstrap.py --sources
# 仅需要下载时执行；使用 hf CLI，保留模型 LICENSE / NOTICE。
"$SYSTEM1_PYTHON" bootstrap.py --models laya startlux-0.8b startlux-4b
# config.toml 模型的 python 改为 .venv-cpu/bin/python，填好权重目录。
./system1.sh doctor all
./system1.sh start laya
./system1.sh start startlux-0.8b
./system1.sh start startlux-4b
export SYSTEM1_ADMIN_KEY='replace-with-your-admin-key'
./system1.sh dashboard start
```

```bash
./system1.sh status all
./system1.sh health startlux-0.8b
./system1.sh smoke startlux-0.8b
./system1.sh logs startlux-0.8b --follow
./system1.sh restart laya --device cpu --context-length 8192
./system1.sh config all
./system1.sh stop all
./system1.sh dashboard stop
```

`start` 默认等待加载、三题型 warm-up 和健康检查；`--no-wait` 仅创建进程。`start all` 尝试全部模型，任何失败最终非零退出。权重不完整时拒绝启动。`preload=false` 先监听，首请求再加载。配置修改需重启；可用 `--config`、`--port`、`--device`、`--context-length` 临时覆盖，覆盖不写回文件。停止前验证 PID 与创建时间。没有自动重启守护，按需交给 systemd、Task Scheduler 或容器。

CUDA 环境可用 `./setup-runtime.sh cu130 --fast-kernels`，也提供cu126；按 [PyTorch官方安装索引](https://pytorch.org/get-started/previous-versions/)匹配驱动。修改模型 `python` 并删除旧 `dependency_paths`。StartLux默认要求CUDA快核；`allow_slow_cuda=true` 可显式允许慢路径。

## C++ / 低内存 StartLux

需要 CMake、C++17 编译器；CUDA构建还需要CUDA Toolkit。Bootstrap固定上游提交，不修改其源代码。构建开启可迁移CPU指令集分派，不强行绑定本机ISA。

```bash
"$SYSTEM1_PYTHON" bootstrap.py --build-native cpu  # 或 cuda
"$SYSTEM1_PYTHON" bootstrap.py --models startlux-0.8b-q8 startlux-4b-q8
```

修改模型表，GGUF文件名以实际下载为准：

```toml
startlux_backend = "gguf-stdio"
gguf_file = "models/startlux-0.8b-q8/StartLux-Decision-0.8B-Q8_0.gguf"
native_binary = "vendor/llama.cpp/build-cpu/bin/system1-native"
path = "models/startlux-0.8b-q8" # tokenizer/config/decision_config所在目录
device = "cpu"
threads = 2
```

已有完整safetensors可本地转换；`path` 仍指向原模型元数据：

```bash
"$SYSTEM1_PYTHON" vendor/llama.cpp/convert_hf_to_gguf.py /path/to/complete/model \
  --outtype q8_0 --outfile models/startlux-0.8b-q8.gguf
```

`gguf-stdio` 使用本地JSONL管道，C++读取选项字母logits，复用StartLux模板、题型和温度校准，不增加推理端口。`startlux_backend="gguf"` 支持llama-server HTTP适配，另设 `llama_server`、独立 `llama_port`，只监听loopback。`"torch"` 保留PyTorch兜底，不需要编译器。Q4下载可选，但未经兼容测试，不默认推荐。

## Windows CPU laptop

安装Python3.12、Git、uv；原生方案另需Visual Studio C++ Build Tools、CMake。无需WSL。保守模板：2线程、延迟加载、60秒空闲卸载、8192上下文，按RAM再调整。

```powershell
.\setup-runtime.ps1 cpu
.\.venv\Scripts\python.exe bootstrap.py --sources
.\.venv\Scripts\python.exe bootstrap.py --build-native cpu
.\.venv\Scripts\python.exe bootstrap.py --models laya startlux-0.8b-q8 startlux-4b-q8
Copy-Item config.windows-gguf.toml config.toml
$env:SYSTEM1_NATIVE_BINARY = "$PWD\vendor\llama.cpp\build-cpu\bin\Release\system1-native.exe"
$env:SYSTEM1_ADMIN_KEY = 'replace-with-your-admin-key'
.\system1.ps1 doctor all
.\system1.ps1 start startlux-0.8b
.\system1.ps1 dashboard start
```

保留exe同目录DLL/CPU backend文件。无编译器时用 `config.windows-cpu.toml` 配合原始权重运行PyTorch FP32。低内存机器先运行一个模型，避免三模型同时推理。Windows推理和PowerShell脚本仍需目标设备验收。

## 资源、上下文、日志

| 设置 | 行为 |
|---|---|
| `device="auto"` | GPU可用且空闲显存≥`gpu_required_mb + gpu_reserve_mb`才使用，否则CPU |
| `device="cpu"` / `"cuda:0"` | 强制设备，显式CUDA失败不静默回退 |
| `threads` / `cpu_affinity` | 线程数与可选CPU核列表，需实测 |
| `cpu_dtype="auto"` | PyTorch CPU有原生BF16标志才选择BF16，否则FP32 |
| `preload=false` | 首请求加载 |
| `idle_unload_seconds` | 空闲释放权重/原生子进程，0常驻 |
| `context_length` | 请求上限，不得超过checkpoint原生限制 |
| `max_batch_tokens` / `prefill_chunk` | PyTorch批量/前缀分块预算，不等于请求硬上限 |
| `cuda_graphs=false` / `images=false` | 默认减少图缓存和视觉塔占用 |

原生GPU自动选择独立于Python的torch CUDA构建，但需要CUDA原生库；加载内存失败/原生GPU后端缺失时auto回CPU。原生实际层放置以日志为准。

StartLux原生上限262144，公共模板16384、Windows8192；长上下文增加计算和内存，C++按配置分配KV/工作区，并非零成本上限。请求 `max_len` 可降低上限，超限报错。Laya原生8192，窗口模式按 `window_length`、批量1覆盖全文，属于窗口聚合：choice/score取最有把握窗口，noul取最大值。训练默认长度512，扩大窗口不代表准确率已验证；`long_input="reject"` 强制单序列。

每模型串行，忙时503，超时504；已运行计算结束前继续占锁。日志保存配置、设备原因、请求ID、HTTP状态、延迟、usage、依赖输出、完整异常。`logs/<model>.log` 默认20MiB轮转5份，早期启动输出在 `.console.log`，C++输出在 `.native.log`。原生日志在重新加载时按大小轮转，单次原生进程生命周期内不截断。`log_payloads=true` 可保存请求/结果正文。

## Jev API、验证和发布

`POST /v1/systemone`、`GET /v1/models`、`GET /health`、`GET /v1/health`，文档 `/docs`。严格模式返回 `model`、`answers`、`usage`，保留Jev请求ID响应头。没有OpenAI chat completions或按请求切换模型，使用对应端口。

```bash
curl --fail-with-body http://127.0.0.1:8883/v1/systemone \
  -H 'Content-Type: application/json' \
  -d '{"state":"Please refund the duplicate charge.","questions":{"refund":{"type":"noul","instructions":"Is a refund requested?"}}}'
python -m unittest test_ops test_extended
python verify_native.py # 需要本地配置完整C++ 0.8B
python benchmark.py --model all --preset quick
python benchmark.py --model all --release-port 8881 --devices cpu cuda
```

释放8881仅用于已授权的测试，无法定位监听PID或服务重启时失败。Docker/守护服务先用管理器停止，避免只停代理没有释放GPU。报告在 `reports/`，页面读取 `latest.json`；原始输出/失败日志保留。torch显存指标不代表C++显存，原生GPU另核对nvidia-smi/原生日志。

`python publish.py` 创建授权的 `IamWWT/system1-ops` public并推送main，要求已提交、gh登录为IamWWT，不覆盖不同origin。当前沙箱GitHub网络受限，尚未创建或推送远程仓库。

Git访问失效代理127.0.0.1:7897时定位来源，单次直连无需改全局配置：

```bash
git config --show-origin --get-regexp 'http.*proxy|https.*proxy'
git -c http.proxy= -c https.proxy= clone https://github.com/StartLuxLabs/StartLux-Decision.git
```

网络必须经代理时先修复代理服务。公开仓库不含权重、私有配置、密钥、日志或二进制。代码Apache-2.0；见 [第三方说明](THIRD_PARTY_NOTICE.md)。
