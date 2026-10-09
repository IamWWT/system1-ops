---
title: 项目术语表
type: reference
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 项目术语表

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

| 术语 | 含义与权威入口 |
|---|---|
| Jev | 结构化决策请求/响应，见[[02-design/SAD-system1_HD_0.2.0]] |
| noul | Jev二元概率题型，使用上游校准 |
| GGUF / Q8_0 | 原生模型格式/量化形式，不代表已验证通用准确率 |
| gateway | FastAPI模型公共入口，不执行生成式聊天 |
| native child | 原生推理子进程，RSS统计包含其内存 |
| 上下文预算 | 请求允许token上限，不等于批量/分块预算 |
| 覆盖基线 | 当前单测可重复覆盖的下限，实际硬件集成另列证据 |
| B4/B5 | 本项目合并的开发/验证基线，以Git标签和证据标识 |

正式交付文档文件名使用工艺前缀+项目+类型码+软件版本；稳定导航和request/tasks使用固定名称，版本由frontmatter和Git标签识别。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
