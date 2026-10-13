# System1 Ops 当前状态入口

目标system1-ops；状态真源docs/04-progress/SESSION.md，过程/基线在该目录。

优先恢复三个模型服务：在宿主执行 ./system1.sh start all（此前它们因接管连带被停，已修复；启动后写入管理记录，页面显示为受管运行中）。随后可在 http://localhost:8885/ 复核：三卡“运行中”、检查行带真实设备/内存/请求数。其余：三个模型的原生助手子进程由worker优雅收尾，无需手动清理；长期欠账不变：覆盖提升、大函数拆分、Windows laptop Laya/4B真机测试。用户约定仅main+最新tag。
