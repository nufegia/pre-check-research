---
name: data-risk-audit
description: Use PCR mvp2 CLI tools to extract, normalize, audit, and merge research data risk findings.
---

# Data Risk Audit

Use this skill when an agent needs to inspect research data, summary statistics, or statistical-result text with the local PCR CLI toolkit.

## Workflow

1. Inventory the submitted materials and classify them as raw data, extracted table, summary statistics, APA/NHST result text, or advanced discrete-score summary.
2. If the file is DOCX/PDF/XLSX and a detector needs CSV, run `pcr-extract` first.
3. Prefer direct specialized CLIs:
   - Raw tables: `pcr-raw-audit`
   - APA/NHST text: `pcr-statcheck`
   - Summary N/mean/SD/proportion tables: `pcr-scrutiny`
   - Expert discrete summary reconstruction: `pcr-sprite`
4. Merge JSON outputs with `pcr-report merge`.
5. Explain findings as risk signals requiring human review. Never state that the tool proves misconduct or fabrication.

## Required Output Handling

Every tool should emit finding JSON with:

- `tool_id`
- `tool_name`
- `detector_runtime`
- `dependency_status`
- `source`
- `input_type`
- `findings[]`

Every finding should include `level`, `check`, `target`, `summary`, `evidence`, `detail`, `suggestion`, `meaning`, `normal_explanations`, `review_steps`, `confidence`, and `false_positive_risk`.

## Tool Selection Rules

- Use `pcr-extract` before auditing DOCX/PDF tables unless the detector can consume the original format.
- Use `pcr-raw-audit` for observation-level CSV/XLSX data.
- Use `pcr-scrutiny` only when N plus mean/SD/proportion columns are present and the variable type is compatible.
- Use `pcr-statcheck` only for plain text containing APA/NHST expressions.
- Use `pcr-sprite` only for advanced review of discrete-score summaries with clear scale bounds.
- Use `pcr-audit run` only when a one-command pipeline is more useful than direct CLI calls.
