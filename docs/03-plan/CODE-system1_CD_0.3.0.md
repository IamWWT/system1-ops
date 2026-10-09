---
title: 编码与质量门禁
type: standard
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 编码与质量门禁

> 版本: 0.3.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 执行规则

Python3.12，项目依赖与开发工具从uv.lock安装；HTTP与模型运行环境分离。Python使用Ruff格式和import/lint，mypy检查所有包模块函数体。动态上游对象可用Any，配置与进程边界优先具体类型。C++17用.clang-format格式化且必须真实构建。浏览器JS通过Node语法检查，运行不依赖Node或CDN。

规范来源：standards/README.md及standards/source.json。新需求先更新[[01-requirements/BRD-system1_U_0.3.0]]，契约先改验收用例；结构/行为取舍进入ADR，事实与失败进入进度记录。

## 本地命令

```bash
uv sync --locked
uv run python scripts/quality_gate.py
uv run python scripts/doc_check.py
uv run pytest -q
uv run mypy src/system1_ops
uv run ruff check .
uv run ruff format --check .
```

Windows使用同一Python门禁，不依赖bash/WSL。Linux提供scripts/quality-gate.sh与doc-check.sh包装入口。

## 指标与动作

| 指标 | 定义/采集 | 阈值 | 超标动作 |
|---|---|---|---|
| 单测 | pytest退出码 | 0失败 | 阻止合入 |
| lint/format/type/doc | quality_gate各命令 | 0错误 | 修复并重跑受影响检查 |
| 覆盖 | coverage分支+行汇总 | ≥35%基线；建议提升70–80% | 拒绝回退到基线下；新增关键逻辑补有效用例 |
| API兼容 | Jev正反路径 + 真实smoke | 接口字段/类型通过 | 回退行为变更 |
| 数值兼容 | benchmark固定输入 | 全部choice一致，最大差≤0.02 | 不采用该候选默认值 |

## 提交与分支

仅保留main，type(scope):摘要；按小批验证提交。只有最新版本保留annotated tag，旧基线用提交哈希和不可变产品归档追溯。源码归档记录SHA256。当前项目门禁2–4合并到Linux/Windows CI；模型集成由Windows native workflow与宿主证据补足。

## 文档组织

现状文档只描述当前实现；过程进04-progress/CHANGELOG；取舍进02-design/decisions。移动文件必须同批修链接并更新FILE_INDEX。具体裁剪见[[02-design/decisions/ADR-001-engineering_CD_0.2.0]]。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |

## 变更记录

| 版本 | 日期 | 记录入口 |
|---|---|---|
| 0.3.0 | 2026-10-09 | [[04-progress/2026-10-09-complete-engineering|过程记录]]；历史基线见[[04-progress/baselines]] |
