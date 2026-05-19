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
3. Run route first and read the route JSON.
4. Run only tools that the deterministic route marks as ready, normally through
   `pcr-audit run --scenario auto` for single inputs or `pcr-audit project` for
   project folders/manifests.
5. Treat missing tools, missing dependencies, insufficient material, skipped
   checks, and not-applicable tools as `level: info`, not data-risk findings.
6. Explain findings only as risk signals requiring human review.
7. Never claim that a finding proves misconduct, fabrication, fraud, or academic
   wrongdoing.

## Input Handling

- Single files such as CSV, XLSX, DOCX, PDF, TXT, MD, images, or analysis code:
  use route plus `pcr-audit run --scenario auto`.
- Project folders or `pcr-project.json` manifests: use `pcr-audit project`.
- If the user only asks what would run, use `pcr-audit route` or
  `pcr-audit project --inspect` and do not run detectors.
- If the user explicitly asks for a scenario, respect it. Otherwise use
  `--scenario auto`.

## Command Templates

For a single file, with `OUTDIR` resolved by the output-directory rule:

```bash
pcr-audit route <input> --json OUTDIR/<stem>.route.json
pcr-audit run <input> --scenario auto --out OUTDIR/<stem>.md --json OUTDIR/<stem>.json
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
