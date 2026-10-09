# 重构前宿主验收记录

记录来源：fd8ada3基线的host-handoff.md，保留其当时验收事实。当前运维入口见[[07-ops/RUNBOOK-system1_MG_0.3.0|运行手册]]。

## 原验收内容

统一项目：`system1-ops`，公开仓库 https://github.com/IamWWT/system1-ops 。

2026-10-09已恢复宿主访问。已按授权停止8881的GPU服务，使用独立CUDA环境与C++原生后端完成实测。Laya、StartLux 0.8B、StartLux 4B服务分别监听0.0.0.0:8882–8884，运维台8885。本机配置与密钥在Git忽略的config.toml、.env中；原始环境、权重和下载缓存保留。

4B使用官方Q8 GGUF，下载完成且SHA256匹配Hub元数据；原始safetensors仍不完整，未使用。C++构建输出在.native-build/bin。CPU/GPU数据、失败候选和测试边界见optimization.md与reports/samples/；原始日志和浏览器截图保存在本机evidence/。

Ubuntu/Windows单元CI、Windows原生CPU编译/真实0.8B推理/PowerShell启动/HTTP运维API已执行通过。目标Windows laptop尚未实测性能，使用config.windows-gguf.toml保守模板后在目标机器复测。

```bash
./system1.sh status all
./system1.sh smoke laya
./system1.sh smoke startlux-0.8b
./system1.sh smoke startlux-4b
./system1.sh dashboard start
./system1.sh logs startlux-4b --follow
```

修改config.toml后restart相应模型生效。管理密钥从.env读取，勿提交或分享。停止操作只处理已确认身份的项目进程；不自动恢复8881。
