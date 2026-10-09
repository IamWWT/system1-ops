# 基线登记表

| 基线名 | 标识 | 形成日期 | 形成依据 | 复现与状态 |
|---|---|---|---|---|
| 整理前回退 | baseline/pre-engineering-fd8ada3 | 2026-10-09 | 原代码fd8ada3，28项测试及真机证据 | Git标签可恢复 |
| B4/B5合并产品基线 | v0.2.0 / f5eb663 | 2026-10-09 | Linux/Windows CI37910322388通过、31测试、native/HTTP/浏览器 | checkout标签后uv sync --locked和quality_gate；旧归档在.local/archives/v0.2.0 |

v0.3.0本轮关口记录以04-progress最新追加为准，最终验证后追加形成依据，不伪造用户评审或设备验收。

| B4/B5合并组织基线 | v0.3.0 | 2026-10-09 | 33测试/coverage37%、Linux/Windows CI37915093701、Windows native37914345721、三模型HTTP与页面 | 源提交/制品SHA256见.local/products/v0.3.0/manifest.json；uv sync --locked，quality_gate可复跑 |

旧表标识是形成时的历史标签；按用户约定最终只保留v0.3.0。旧基线按fd8ada3/f5eb663提交与回退归档恢复，旧tag不再可用于checkout。
