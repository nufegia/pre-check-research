---
name: data-risk-audit
description: Route-first PCR mvp2 workflow for research data, manuscript, image, code, and project risk auditing.
---

# Data Risk Audit SOP

Use this skill when the user asks to audit, inspect, check, review, or explain
research data, summary statistics, APA/NHST text, manuscript materials, images,
analysis code, or a mixed PCR mvp2 project folder.

## Default Agent Protocol

Do not infer tool suitability in agent reasoning. The project route layer must
decide which tools apply.

1. Determine the input path from the user's request.
2. Determine the output directory:
   - If the user names an output directory or output path, use that location.
   - If the user does not specify output location, use `output/` under the
     project root.
   - All output filenames must use `pcr` as the prefix stem, for example
     `pcr.audit.route.json`, `pcr.audit.md`, and `pcr.audit.raw.json`.
     Do not derive filenames from the input name or from AI-generated
     descriptions.
3. **Check for pre-existing results** in the output directory before running.
   If `pcr.standard.*` files exist for the same input, prefer them — they
   represent a full project-mode audit. Confirm with the user whether to reuse
   or re-run.
4. **Choose the correct command** based on input type:
   - Manuscript documents (PDF, DOCX papers): use `pcr-audit project` — this
     enables image extraction and forensic tools.
   - Data files (CSV, XLSX): use `pcr-audit route` + `pcr-audit run --scenario auto`.
   - Standalone images: use `pcr-audit route` + `pcr-audit run --scenario auto`.
   - **Never use `pcr-audit run --scenario auto` for manuscript PDFs/DOCXs.**
     It silently skips image extraction and forensics, producing false negatives.
5. Run only tools that the route or project manifest marks as ready.
6. Treat missing tools, missing dependencies, insufficient material, skipped
   checks, and not-applicable tools as `level: info`, not data-risk findings.
7. Explain findings only as risk signals requiring human review.
8. Never claim that a finding proves misconduct, fabrication, fraud, or academic
   wrongdoing.

## Pre-existing Results Check

Before running any audit, check the output directory for existing results from
prior runs. If comprehensive results already exist (especially `pcr.standard.*`
files), use those instead of re-running — and confirm with the user.

```bash
ls output/pcr*.json output/pcr*.md 2>/dev/null
```

Common naming conventions found in output:
- `pcr.standard.*` — full project-mode audit (comprehensive, includes image forensics)
- `pcr.*` — single-file route+auto audit (text-level tools only)
- `pcr.image.audit.*` — image-only audit runs

If `pcr.standard.*` files exist, prefer them as the authoritative source. They
were produced by `pcr-audit project` and include the full tool suite.

## Input Handling

- **Data files** (CSV, XLSX, TXT with tables): use route plus
  `pcr-audit run --scenario auto`. These contain structured data and the
  auto scenario correctly selects statistical and raw-table rules.
- **Manuscript documents** (PDF, DOCX that are journal papers or preprints):
  use `pcr-audit project <input>`. This assigns the file role `manuscript`,
  enables image extraction from the PDF, and runs the full pipeline including
  image forensics (duplicate detection, copy-move, metadata audit).
  **Do NOT use `pcr-audit run --scenario auto` for manuscript PDFs/DOCXs** —
  the auto scenario only selects text-level tools (reference_audit,
  citation_claim_check, papermill_light_signals) and silently skips image
  extraction and all image forensic tools, producing a false "no findings"
  result.
- **Standalone images** (PNG, JPG, TIFF): use route plus
  `pcr-audit run --scenario auto`.
- **Project folders** or `pcr-project.json` manifests: use `pcr-audit project`.
- If the user only asks what would run, use `pcr-audit route` or
  `pcr-audit project --inspect` and do not run detectors.
- If the user explicitly asks for a scenario, respect it. Otherwise follow the
  rules above — do not default to `--scenario auto` for manuscript documents.

## Command Templates

For a **data file** (CSV, XLSX) with `OUTDIR` resolved by the output-directory rule:

```bash
pcr-audit route <input> --json OUTDIR/<stem>.route.json
pcr-audit run <input> --scenario auto --out OUTDIR/<stem>.md --json OUTDIR/<stem>.json
```

For a **manuscript document** (PDF, DOCX) — use project mode to enable image forensics:

```bash
pcr-audit project <input> --out OUTDIR/<stem>.md --json OUTDIR/<stem>.json
```

For a project folder or manifest:

```bash
pcr-audit project <input> --out OUTDIR/<stem>.md --json OUTDIR/<stem>.json
```

For route-only inspection:

```bash
pcr-audit route <input> --json OUTDIR/<stem>.route.json
```

For project material inspection without running detectors:

```bash
pcr-audit project <input> --inspect --json OUTDIR/<stem>.inspect.json
```

## Result Boundaries

Separate the final explanation into these layers whenever useful:

- Standard tool results: route decisions, detector findings, R CLI output,
  dependency status, and finding JSON content.
- Agent interpretation: prioritization, plain-language explanation, grouping of
  related findings, and possible normal explanations.
- Human review actions: concrete next steps using original data, scripts,
  logs, images, manuscript tables, or statistical output.

The agent may summarize and prioritize findings, but must not upgrade risk
signals into misconduct conclusions.

## Reporting Requirements

Reports and conversational summaries should include:

- What was detected by standard tools.
- Which checks were skipped or unavailable, and why.
- Quantitative evidence or evidence IDs when present.
- Possible normal explanations.
- Concrete review steps.
- A clear note that `info` records are operational status, not risk findings.

For DOCX/PDF inputs, recommend rerunning important findings on original CSV/XLSX
or source materials whenever possible.

## Current Raw Table Coverage

`raw_data_rules` is the single Python tool for raw observation tables. It includes
basic table rules, digit distribution checks, repeated/highly similar rows and
columns, 列间线性变换、列间过高相关性、低频类别、有序变量极端集中,
continuous outlier checks, and missingness by group.
