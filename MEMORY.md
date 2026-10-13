# System1 Ops 当前状态入口

目标system1-ops；状态真源docs/04-progress/SESSION.md，过程/基线在该目录。

线上 8885 仍是旧代码：在宿主执行 ./system1.sh dashboard stop（现可接管未纳管的旧运维台）+ ./system1.sh dashboard start；随后三卡应显示“运行中（未纳管 · …）”，停止/重启按钮可直接接管这三个模型实例。若要三个模型实例重新纳入管理记录，可用 ./system1.sh restart <模型>（接管后由新进程写入记录）。长期欠账不变：覆盖提升、大函数拆分、Windows laptop Laya/4B真机测试。用户约定仅main+最新tag。
