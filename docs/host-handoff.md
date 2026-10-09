# 宿主会话继续记录

用户已授权完成三模型维护、性能优化、停止8881释放GPU进行测试，以及在
IamWWT下创建public仓库并推送。无需再次询问这些授权。

项目目录：`system1-ops`，目前最后提交 `8df94e8`。原始权重只读复用，
本地配置 `config.toml` 已被Git忽略，公共模板和文档已提交。

## 已完成

* FastAPI Jev接口：8882 Laya、8883 StartLux 0.8B、8884 StartLux 4B；8885运维台。
* Windows/Linux进程身份验证、启停重启、日志、设备选择和灵活上下文配置。
* C++ llama.cpp JSONL管道后端，复用StartLux原生模板和温度校准。
* 原生源码无修改，依赖提交固定；本机已构建原生库与驱动。
* 24项API/运维测试通过；原生真实输入、状态隔离、非法token恢复、卸载重载、上下文限制通过。
* i9-13900K CPU测试：Laya 4→8线程P50 1.245→0.822秒；0.8B BF16参考17.185秒、
  FP32最快1.910秒/5.40GiB、C++Q8最快1.483秒/1.61GiB。
  Q8选项全部一致，最大概率差0.00985。LayaINT8差0.4886，拒绝默认使用。
* 单题原生4668token输入18.17秒；4096请求上限明确拒绝，8192接受。
* 完整本机证据在被忽略的evidence/、reports/中；公开样本在reports/samples/。

## 下一步（需要真正的宿主访问）

1. 先核实GPU、端口、网络可见性。受限窗口会显示netlink EPERM、GitHub连接失败、
   工具进程仍由codex-linux-sandbox以managed/restricted配置执行。
   该状态不能证明宿主NVIDIA驱动损坏。
2. 查8881实际服务及其管理器。用户授权停止该服务；若是Docker/守护进程，
   使用其管理器停止，避免只杀代理。确认GPU资源释放。
3. 当前现有Python环境torch均为CPU构建。选择独立CUDA环境或构建CUDA版原生后端，
   避免覆盖原有环境。查驱动/工具链再决定CUDA安装索引。
4. 原生CPU驱动位置`.native-build/bin/system1-native`，本地转换的Q8位置
   `models/startlux-0.8b-q8.gguf`。在CPU构建上auto尝试GPU时应回退CPU，
   强制CUDA应明确失败；需要目标设备验证。
5. 现有4B目录`~/repo/aigc/models/system1/startlux-models--StartLux-Decision-4B`
   缺两个safetensors分片。下载完整权重到可写项目models/，或使用官方Q8仓库，
   然后更新本地配置；不要把缓存.incomplete当成完整权重。
6. 执行GPU和CPU对照、真实端口启动/smoke、浏览器运维台验收。
   benchmark.py提供独立进程、数值兼容门槛、内存采样、超时子进程清理。
   原生GPU显存须用nvidia-smi/原生日志补充，torch统计不包含C++显存。
7. 本机gh登录IamWWT后执行publish.py创建public仓库并push。
   本沙箱创建尝试因GitHub网络失败，远程仓库尚未创建。
   GitHub connector已验证账号，但无创建仓库工具。不要误报发布成功。
8. 提交任何新增修复/脱敏报告，保护权重、密钥、个人路径和本地日志。

## 启动与验收

```bash
cd system1-ops  # 从frameworks工作目录执行
./system1.sh doctor all
./system1.sh start laya
./system1.sh start startlux-0.8b
./system1.sh start startlux-4b
# 设置真实管理密钥后启动8885，页面提供启停/日志/请求调试/性能报告。
./system1.sh dashboard start
./system1.sh smoke startlux-0.8b
python publish.py
```

如无法恢复原会话，在宿主CLI的新会话发送：
“读取system1-ops/docs/host-handoff.md，继续执行其中已授权的工作。”
