---
title: 需求摄入
type: reference
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 需求摄入

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 用户原话

“完成这三个模型的启动与运维脚本维护，最好常用启动端口是8882-8885……可以自动切换是否用cpu gpu加载……上下文长度也要灵活可设置……最好兼容jev当前api。”

“希望可以对外暴露，所以0.0.0.0要支持……建议fastapi。”

“建议针对硬件软件做极致优化测试……还有个cpu laptop - windows想要同时运行……简单的……运维页面……可以停止8881端口……github IamWWT……public。”

“性能优化过程如果有比python更匹配的语言能获得更快的加速……直接用。”

“读取dsh-agent-presets engineering相关工程编码规范，按照规范组织当前项目。”

## 提炼范围

目标项目仅为本仓 System1 Ops。工程规范来源见标准快照 `standards/source.json`；不修改 dsh-agent-presets、上游模型源仓库或用户原始权重。目录和质量门禁重构复用已授权的维护、真机测试和公开推送范围。

## 假设与边界

| 编号 | 假设 | 依据与影响 |
|---|---|---|
| A1 | 保留根目录启动脚本和已公开Python CLI入口 | 避免已有操作命令失效 |
| A2 | 私有config.toml和.env保持原位置 | 用户已有运行配置与密钥 |
| A3 | 模型依赖环境独立，uv.lock锁服务/开发工具链 | CUDA、CPU与上游模型包存在平台差异 |
| A4 | Windows laptop性能待目标机器实测 | CI runner只能证明已测路径的可迁移性 |
| A5 | 工程整理期间可重启本项目服务 | 用户授权启动运维与测试；完成后恢复端口 |

## 验收关系

[[01-requirements/BRD-system1_U_0.2.0|需求与验收矩阵]]是功能验收入口；[[02-design/decisions/ADR-001-engineering_CD_0.2.0|规范裁剪决策]]列明保留的兼容行为。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
