---
title: 第三方组件与许可
type: reference
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 第三方组件与许可

> 版本: 0.3.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

System1 Ops does not redistribute weights or vendor source. Downloaded sources
and weights stay outside Git. Their upstream licenses and notices still apply.

* [Laya](https://github.com/NandhaKishorM/laya), Apache-2.0,
  pinned commit `1adc59f7e371deb601fcfa18a14e25db238addcc`.
* [StartLux Decision](https://github.com/StartLuxLabs/StartLux-Decision), Apache-2.0,
  pinned commit `0e7a2e81b9c92756e26d8edd843a44d50e362669`.
  `startlux_policy.py` adapts its model-loading boundary. Jev rendering, decision
  types and probability calibration remain in the upstream implementation.
* [llama.cpp](https://github.com/ggml-org/llama.cpp), MIT,
  pinned commit `89fe24240548456477870b2a627cd8021fea1e39`.
  The original native pipe driver links to its C API and includes its vendored
  nlohmann/json headers (MIT). Retain upstream LICENSE files when distributing binaries.
* StartLux weights include their own LICENSE and NOTICE; conversion/quantization
  does not replace those terms. No weights are published in this repository.

Other runtime dependencies retain their respective licenses.

Engineering standards are vendored from [dsh-agent-presets](https://github.com/IamWWT/dsh-agent-presets), Apache-2.0, revision `74dfcd1270675713853c5f87e798ed9b5f7acb25`. The unchanged file manifest is standards/source.json; its license is retained in standards/LICENSE. No third-party skill is installed.

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |

## 变更记录

| 版本 | 日期 | 记录入口 |
|---|---|---|
| 0.3.0 | 2026-10-09 | [[04-progress/2026-10-09-complete-engineering|过程记录]]；历史基线见[[04-progress/baselines]] |
