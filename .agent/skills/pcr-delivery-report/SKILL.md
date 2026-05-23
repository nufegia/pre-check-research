---
name: pcr-delivery-report
description: Convert PCR mvp2 standardized audit outputs such as pcr.audit.md, pcr.audit.json, merged finding JSON, or project audit parts into a pre-submission decision report for a PI, supervisor, manuscript author, or research team. Use when the user asks to write, polish, translate, summarize, or package precheck/pre-audit results into a non-technical delivery report that supports decisions about whether to proceed with submission, supplement review materials, pause submission, or request author explanations.
---

# PCR Delivery Report

## Purpose

Turn deterministic PCR audit outputs into a calm, actionable pre-submission decision report for research stakeholders. The output should help a PI, supervisor, or author decide whether the manuscript can keep moving, needs author explanation before submission, should pause for further material review, or cannot yet be judged from the provided materials.

This skill does not rerun detectors unless the user explicitly asks. It rewrites and prioritizes already-produced results.

## Audience Model

Assume the recipient needs five things:

1. A delivery conclusion: whether high-priority signals were found, whether immediate submission pause is recommended, whether additional pre-submission review is recommended, and the most important author explanation needed.
2. Scope clarity: what materials and checks were actually covered.
3. Main concerns: 2-5 aggregated signal clusters with concrete evidence, not a long detector dump.
4. Fair interpretation: plausible benign explanations and method limitations.
5. Next actions: a finite pre-submission checklist assignable to author, student, statistician, data manager, or PI.

Avoid making the report feel like an allegation. Use "复核优先级" instead of "风险等级". Prefer terms such as "复核信号", "需复核", "提示", "优先回看", "服务边界", "投稿前建议", and "作者需确认". Do not use "造假", "舞弊", "篡改", "实锤", "定罪", or equivalent misconduct conclusions unless quoting a user-provided policy, and even then distinguish the automated result from any institutional judgment.

## Input Priority

Prefer structured JSON when available, then use Markdown for narrative/context:

- `pcr.audit.json`: best source for fields such as `level`, `check`, `target`, `evidence`, `detail`, `review_steps`, `normal_explanations`, `confidence_score`, `confidence`, `confidence_basis`, `false_positive_risk`, `tool_id`, `dependency_status`, `location`, and `evidence_id`.
- `pcr.audit.md`: useful for material lists, coverage matrix, tool run details, service-boundary notes, and already-merged human-readable sections.
- `pcr.audit.parts/*.json`: use when the merged JSON is missing or when checking per-material provenance.
- `tools/common/schemas/finding.schema.json`: use only if field meaning is unclear.

When both JSON and Markdown disagree, treat JSON as the evidence source and Markdown as presentation context. Mention unresolved inconsistencies as a report limitation instead of silently reconciling them.

## Workflow

1. Identify recipient and format.
   - If unspecified, write in Chinese Markdown for a PI/导师.
   - Use a professional but non-adversarial tone.
   - If the user asks for email/letter/docx, adapt the same content to that format.

2. Extract reusable facts.
   - Count non-`info` findings by `high`, `medium`, and `low`.
   - Read `confidence_score` as methodological confidence, not signal severity. Use it to explain evidence reliability and to avoid over-prioritizing high-severity but low-confidence findings.
   - Count `info` separately as run notes, skipped checks, dependency status, or material gaps.
   - List materials, rows/columns, input types, and tool coverage if present.
   - Group findings by `check`, `tool_id`, material/location, and review action.

3. Decide pre-submission status.
   - Use the status rules below to select exactly one status: "可继续推进投稿", "建议补充说明后再投稿", "建议暂缓投稿并补充材料复核", or "暂无法判断".
   - Include a delivery conclusion answering: whether high-priority signals were found, whether immediate submission pause is recommended, whether pre-submission supplemental review is recommended, and the most important author explanation needed.
   - Do not guarantee journal acceptance, peer-review outcome, or institutional conclusions.

4. Aggregate signal clusters.
   - Produce 2-5 signal clusters when findings exist.
   - Cluster by shared review meaning, not just by tool: for example digit concentration in multiple scales, 行列高度相似, 列间线性变换/列间过高相关性, 低频类别, 有序变量极端集中, provenance/version status, manuscript-data mismatch, or code reproducibility gap.
   - For each cluster, state involved materials, representative evidence, what it means, what it does not mean, and recommended action.
   - Preserve representative evidence IDs and examples; move all finding-level detail to the appendix.

5. Interpret cautiously.
   - Say what the signal means and what it does not prove.
   - Include normal explanations from the finding payload when available.
   - For `dependency_status` values such as `missing`, `missing_material`, `insufficient_material`, skipped, or not applicable, describe them as service boundaries, not system failures and not risk findings.

6. Write the deliverable.
   - Use the template in `references/report-template.md` when a full report is needed.
   - Keep the main body concise and non-technical; put all finding-level detail in the appendix.
   - For short outputs, include only delivery conclusion, pre-submission status, key signal clusters, service boundaries, author questions, and next actions.

7. Quality check before finalizing.
   - Numeric counts match the source.
   - Every claim can be traced to a source field or table.
   - The report contains a clear non-verdict statement.
   - `info` items are not counted as risk findings.
   - Raw-table coverage uses current `raw_data_rules` wording: digit distribution, 行列高度相似, 列间线性变换, 列间过高相关性, 低频类别, 有序变量极端集中, outliers, missingness, fixed-step, dominant values, and decimal precision.
   - `confidence_score` is explained as methodological confidence when it materially changes priority; low-confidence signals are framed as needing more material or rerun rather than as top-priority conclusions by default.
   - "风险等级" has been rewritten as "复核优先级" in client-facing Chinese output.
   - Client-facing report text does not use Markdown code styling. Replace code spans or code blocks with quotation marks.
   - The strict boundary statement remains present.

## Pre-Submission Status Rules

Select one status and explain the reasoning in 2-4 sentences:

- **可继续推进投稿**: no high-priority signals, no unresolved medium-priority clusters requiring author explanation before submission, and service boundaries do not block the specific submission decision. Still list ordinary documentation improvements if useful.
- **建议补充说明后再投稿**: no high-priority signals, but medium-priority clusters need author/statistician explanation, recalculation, or documentation before submission. Use this as the default when repeated medium signals are present but are plausibly explainable with scale rules, rounding, data dictionary, or grouping logic.
- **建议暂缓投稿并补充材料复核**: high-priority signals exist, multiple independent medium-priority clusters affect core results, manuscript-data consistency cannot be checked for central claims, or source materials needed for basic verification are missing.
- **暂无法判断**: the provided audit result lacks enough material coverage or structured findings to support a submission recommendation. Use this when the report is mostly `info` records, missing core manuscript/raw data, or the source output is incomplete/inconsistent.

Never write "建议投稿" as a guarantee. Write "可继续推进投稿流程" or "投稿前建议完成以下补充确认".

## Delivery Conclusion Requirements

Include a "交付结论" module near the top with these fields:

- 当前是否发现高优先级复核信号：yes/no/无法判断, with count if available.
- 是否建议立即中止投稿：yes/no/暂不建议, with a short reason.
- 是否建议投稿前补充复核：yes/no, with the exact materials or questions.
- 最需要作者解释的问题：one clear question or a short numbered list.
- 投稿前状态判断：one of the four statuses in the status rules.

Use "立即中止投稿" only when the user requests that exact decision language; otherwise prefer "暂缓投稿" in the recommendation.

## Signal Cluster Rules

Convert finding rows into 2-5 client-readable clusters:

- Name clusters by issue meaning, such as "多项量表末位数字集中", "行列高度相似需回看原始记录", "列间线性关系或高相关需解释", "低频类别或有序评分分布异常", "原始文件版本链需补充说明", "稿件表格与原始数据尚未对账", or "分析脚本复跑材料不足".
- Do not list every variable in the main body when many variables repeat the same signal. State the range and give representative examples.
- Each cluster must include:
  - 涉及材料
  - 代表性证据
  - 这意味着什么
  - 这不意味着什么
  - 投稿前建议动作
- Keep all finding-level rows in an appendix table.

## Recommended Report Shape

For a PI/导师/作者 delivery report, use this order:

1. Title and delivery metadata.
2. 交付结论.
3. Executive summary with pre-submission status and overall review priority.
4. Scope and material coverage.
5. Key signal clusters.
6. Service boundaries.
7. Recommended pre-submission review plan.
8. Recommended supplemental materials.
9. Suggested author confirmation questions.
10. Optional follow-up review.
11. Appendix with finding-level evidence table.
12. Boundary statement.

Keep the main body short enough for a non-technical PI to read quickly. Put long detector details, hashes, route notes, and per-evidence rows in appendices.

## Writing Rules

- Translate detector names into plain language while keeping `tool_id` or evidence IDs in appendices.
- Preserve exact evidence values such as p-values, CVs, counts, SHA-256 status, sample size, and percentages.
- Use "总体复核优先级" and "复核优先级" rather than "总体风险", "风险等级", or "风险发现".
- Say "本次服务边界为..." or "当前材料尚不足以覆盖..." instead of "系统失败", "工具失败", or "不存在...".
- For repeated 数字分布类信号, explain possible measurement/rounding/scale effects before recommending source-data review.
- For provenance hash or chain status, explain that hashing supports file integrity/version tracking but does not prove experimental authenticity.
- For manuscript-facing reports, avoid exposing unnecessary absolute local paths in the executive body; put full paths in the appendix only if useful.
- Do not use Markdown code styling in report deliverables, including inline code spans or fenced code blocks. When a field name, variable name, file name, tool ID, evidence ID, or exact phrase needs emphasis, use quotation marks instead, such as "info", "tool_id", or "pcr.audit.json".
- Include a "下一步建议补充材料" table when materials are missing or when submission decisions depend on additional verification. Common rows: CRF/问卷记录, 数据字典, 投稿主稿, 统计脚本, 图像原始文件.
- Include "建议作者确认的问题" as neutral questions that a PI can forward directly to students or authors.
- Include "可选后续复核" to bridge to next-stage services such as manuscript-data crosscheck, statistic rerun, image-source review, code rerun, or author response review.
- Keep the strict boundary statement: the report does not constitute an academic misconduct finding, ethics investigation conclusion, statistical peer-review opinion, or guarantee of submission outcome.

## Output Variants

- **Full report**: use the full template; best for handoff deliverables.
- **PI email**: 5-8 paragraphs, with a short bullet list of actions.
- **Author response request**: convert findings into neutral questions and requested materials.
- **Internal triage memo**: emphasize service boundaries, prioritization, and who should review each item.
- **Pre-submission decision memo**: emphasize the selected submission status, delivery conclusion, service boundaries, author questions, and optional follow-up review.

## Reference

Read `references/report-template.md` when drafting a complete deliverable or when the user asks for a reusable format.
