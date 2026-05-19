# PCR Delivery Report Template

Use this template for a full Markdown pre-submission decision report. Adapt section names to the recipient and omit sections only when the user asks for a shorter note. Keep the main body concise and move all finding-level detail to the appendix.

## 标题

`# 投稿前研究数据复核交付报告：<项目/稿件名称>`

Metadata block:

- 交付对象：
- 预审材料：
- 预审结果来源：
- 报告日期：
- 总体复核优先级：
- 投稿前状态判断：

## 交付结论

Use a compact decision table:

| 判断项 | 结论 | 说明 |
|---|---|---|
| 当前是否发现高优先级复核信号 | 未发现/发现/暂无法判断 | 写明数量和来源 |
| 是否建议立即中止投稿 | 不建议/建议暂缓/暂无法判断 | 避免夸大，说明原因 |
| 是否建议投稿前补充复核 | 建议/不建议/暂无法判断 | 写明需补充的材料或说明 |
| 最需要作者解释的问题 | <一句话> | 便于 PI 直接转发 |
| 投稿前状态判断 | 可继续推进投稿/建议补充说明后再投稿/建议暂缓投稿并补充材料复核/暂无法判断 | 用 1-2 句解释 |

## 一页摘要

Include:

- Materials reviewed and detector coverage.
- Counts by review priority: high / medium / low; `info` run notes separately.
- One sentence on the main signal clusters.
- One sentence on what the audit cannot conclude.
- Immediate pre-submission action.

Example wording:

`本次预审在已提供材料中未出现高优先级复核信号；投稿前主要建议补充确认 <cluster>. 这些结果提示需要回看原始记录和处理流程，但不构成对数据真实性、研究诚信或投稿结果的结论。`

## 预审范围

Recommended table columns:

| 材料 | 类型 | 行/列或页数 | 已运行检查 | 备注 |
|---|---|---:|---|---|

Summarize unrun checks under the table.

## 主要复核信号簇

Aggregate all findings into 2-5 clusters. Recommended columns:

| 复核优先级 | 信号簇 | 涉及材料 | 代表性证据 | 这意味着什么 | 这不意味着什么 | 投稿前建议动作 |
|---|---|---|---|---|---|---|

For each cluster, include 1-3 representative evidence IDs and examples. Put every finding-level row in the appendix.

## 服务边界

Present unavailable checks as service boundaries, not system failure. Separate these from review-priority signals:

- Missing manuscript or summary table.
- Missing analysis code.
- Missing corpus/index.
- Missing R/Python dependency.
- Insufficient sample size or unsuitable material.

Use wording:

`该项表示当前服务未覆盖或材料尚不足，不能解释为相应问题不存在，也不代表系统失败。`

Recommended table:

| 服务边界 | 当前状态 | 对投稿前判断的影响 | 建议补充 |
|---|---|---|---|

## 建议复核计划

Make actions concrete and assignable:

| 复核优先级 | 复核任务 | 所需材料 | 建议负责人 | 预期产出 |
|---|---|---|---|---|

Common tasks:

- Ask authors to confirm measurement scale, rounding, range limits, and data export rules.
- Recompute key descriptive statistics from original CSV/XLSX.
- Compare manuscript tables with raw-data summaries and analysis script output.
- Check grouping variables and coding rules.
- Preserve or update hash/version records after receiving corrected materials.

## 下一步建议补充材料

Include this table even if some materials are already present. Mark unavailable or not needed clearly.

| 材料 | 用途 | 当前是否已提供 | 投稿前建议 |
|---|---|---|---|
| CRF/问卷记录 | 核对原始量表、填写规则、异常值和缺失值 | 已提供/未提供/不适用 | <建议> |
| 数据字典 | 确认变量含义、编码、量表范围、四舍五入和阈值规则 | 已提供/未提供/不适用 | <建议> |
| 投稿主稿 | 对账论文表格、摘要结果和方法描述 | 已提供/未提供/不适用 | <建议> |
| 统计脚本 | 复跑核心统计量、确认清洗和建模流程 | 已提供/未提供/不适用 | <建议> |
| 图像原始文件 | 核对图像来源、处理链和投稿图一致性 | 已提供/未提供/不适用 | <建议> |

## 建议作者确认的问题

Phrase as neutral questions:

- 请说明 `<variable>` 的量表范围、计分方式、四舍五入规则和是否存在阈值截断。
- 请提供用于生成论文表格的原始数据版本、清洗脚本和统计输出。
- 请确认分组变量 `<group>` 是否为分析分层变量、随机分组变量或人口学变量。
- 请说明当前投稿主稿中哪些表格直接来自本次提供的数据文件。
- 如存在图像或实验照片，请确认原始文件、处理步骤和投稿图版本是否可追溯。

## 可选后续复核

Use this section to bridge to the next service phase without overselling:

| 后续复核项 | 适用情形 | 需要材料 | 预期产出 |
|---|---|---|---|
| 稿件-数据对账 | 已有投稿主稿和原始数据 | 投稿主稿、数据表、数据字典 | 表格/摘要结果与原始数据的一致性说明 |
| 核心统计复跑 | 有统计脚本或可重建分析流程 | 统计脚本、原始数据、依赖说明 | 关键统计量复算记录 |
| 图像源文件复核 | 稿件含图像、照片、凝胶图或显微图 | 原始图、处理后图、图注 | 图像来源和处理链核对记录 |
| 作者说明复核 | 作者已回复确认问题 | 作者回复、补充材料 | 是否可支撑投稿前判断的复核意见 |

## 附录：证据明细

Recommended columns:

| 证据ID | 复核优先级 | 检查项 | 位置 | 对象 | 证据 | 复核动作 |
|---|---|---|---|---|---|---|

Keep exact evidence values. Full local paths may appear here when needed.

## 边界声明

Include a short statement:

`本报告基于自动化预审工具和当前提供材料形成，仅用于支持投稿前复核和材料补充决策。复核信号不等同于学术不端认定、伦理调查结论、统计审稿意见或投稿结果保证；最终判断需结合原始记录、伦理/试验流程、统计脚本、数据字典、图像源文件和作者说明。`
