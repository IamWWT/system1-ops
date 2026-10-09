---
title: 需求摄入
type: reference
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 需求摄入

> 版本: 0.3.0 | 状态: Active
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

[[01-requirements/BRD-system1_U_0.3.0|需求与验收矩阵]]是功能验收入口；[[02-design/decisions/ADR-001-engineering_CD_0.2.0|规范裁剪决策]]列明保留的兼容行为。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |

## 本轮用户原话与目标锚定

“你看看完整的engineering模式的工作方式 要求 规范, 你现在工作目录下面内容组织仍旧乱七八糟的”

目标项目绝对路径：/home/wwt/Downloads/aigc/proj/frameworks/system1-ops。父目录frameworks是多个独立仓库集合，只读盘点；续接入口改为打开本项目。目标外仓库和用户模型原目录不移动。用户反馈构成本轮组织返工依据，验收看真实工作目录和运行结果，不以CI替代用户对目录组织的判断。

## 原始需求完整补录

> 完成这三个模型的启动与运维脚本维护,最好常用启动端口是8882-8885, 且可以自动切换是否用cpu gpu加载,且要求资源消耗最低情况下,可输入上下文足够长,上下文长度也要灵活可设置, 最好是配置文件灵活配置我说的方式, 并且日志打印要完整. 最好兼容jev当前api

> nvidia可用,只不过我现在占用了他在其他llm端口服务上 8881

> 希望可以对外暴露,所以0.0.0.0 要支持,如果api python实现,建议fastapi, 不过你可以灵活选择并告诉我原因

> 建议针对硬件软件做极致优化测试(同时可用性兼容设备迁移保底,因为我还有个cpu laptop - windows 想要同时运行 ), 需要考虑的因素你可以自己看 自己搜网上. (2) 建议有个简单的我可以看到调试的运维页面 (3) 你可以停止8881端口 释放gpu来测试, 我暂时不用了 (4) 该项目 建议仓库推送到: github IamWWT 仓库,仓库你初始创建 public就行.

> 性能优化过程如果有比python更匹配的语言能获得更快的加速,不要怀疑,直接用,比如rust c cpp go等

> 读取dsh-agent-presets engineering相关工程编码规范,按照规范组织当前项目.

> 你看看完整的engineering模式的工作方式 要求 规范, 你现在工作目录下面内容组织仍旧乱七八糟的

## 变更记录

| 版本 | 日期 | 记录入口 |
|---|---|---|
| 0.3.0 | 2026-10-09 | [[04-progress/2026-10-09-complete-engineering|过程记录]]；历史基线见[[04-progress/baselines]] |

## 续接入口的联合写入白名单

/home/wwt/Downloads/aigc/proj/frameworks/resume-system1-host.sh为此前本任务生成且用户已执行的续接入口。只调整其-C工作目录到system1-ops，避免后续会话误把frameworks集合当成本项目；父目录其他内容仍只读。

## 分支与标签约定（用户新增）

> 另外分支只保留一个主就行, tag也只要1个

本仓最终只保留main和最新一个标签；旧基线由提交哈希与产品归档保留。不得为框架模板要求额外保留分支/标签，用户约定优先。
