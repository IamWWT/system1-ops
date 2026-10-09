---
title: 企业规范收件箱（_inbox）
type: standard
status: active
version: 1.0.0
date: 2026-10-04
owner: 企业维护人
applies_to: 企业规范导入
references:
  - ../README.md
---

# 企业规范收件箱（_inbox）

> 把**原始格式**的企业规范文档（docx / pdf / html / txt / 旧 md）放在**本目录下**，
> 然后对 Agent 说一句：

```
把 standards/enterprise/_inbox/ 里的企业规范按 prompts/import-standards.md 全部导入
```

## 目录约定

| 位置 | 放什么 | 说明 |
|---|---|---|
| `_inbox/`（本目录） | **未转化的原始文档** | 唯一允许放原始格式的地方 |
| `_inbox/_source/` | 转化完成后的**原件留档** | 可追溯；不入库时可自行 gitignore |
| `../{java,database,frontend,api,security,process,quality}/` | 转化后的 markdown 规范 | 每份规范独立成文（带 frontmatter） |

## 规则

1. **只有本目录允许放原始格式文件**；转化完成后移入 `_source/`，禁止原始格式进规范子目录。
2. 导入前检查**敏感信息**：含凭证/内部地址的文档，只改写"规则条款"，凭证与地址用 `<占位>` 替代
   （见 `../README.md` §3）。
3. 转化流程与分类蓝图见 `../README.md` §1–§2。

> 本目录的 `.gitkeep` 仅用于让空目录能被 git 与 `init-project.sh` 的 `cp -r` 保留；
> 导入真实文档后可以保留。
