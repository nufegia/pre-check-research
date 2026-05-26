# pre-check-research (pcr) - Agent Instructions

Pre-check research data risk audit toolkit. `pcr` is the project abbreviation used by commands, output filenames, schemas, and agent workflows.

This file is guidance for coding agents working in this repository. It is not part of the runtime API.

## Setup

```bash
python3 -m pip install -e ".[dev]"  # use python if your environment exposes it
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional: `install.packages(c("statcheck", "scrutiny", "rsprite2"))` in R.

## Available Tools

| CLI | Runtime | Input | Purpose |
|-----|---------|-------|---------|
| `pcr-extract` | Python | DOCX/PDF/XLSX | Extract tables to CSV. |
| `pcr-raw-audit` | Python | CSV | Raw-data digit distribution scan. |
| `pcr-crosscheck` | Python | CSV/XLSX/DOCX/PDF | Row-level summary-stat math checks. |
| `pcr-statcheck` | R | TXT | APA/NHST reporting consistency. |
| `pcr-scrutiny` | R | CSV | GRIM/GRIMMER/DEBIT feasibility. |
| `pcr-sprite` | R | CSV | SPRITE discrete reconstruction. |
| `pcr-report merge` | Python | JSON | Merge findings to Markdown. |
| `pcr-audit route` | Python | Mixed | Explain deterministic routing. |
| `pcr-audit run` | Python | Mixed | Run a one-command pipeline. |
| `pcr-audit project` | Python | Folder/manifest | Multi-material project audit. |
| `pcr-audit provenance` | Python | Folder/manifest | SHA-256 provenance ledger. |
| `pcr-audit corpus` | Python | Folder/manifest | Local cross-manuscript screening. |

Python CLIs: `src/pcr_audit/cli.py`
R CLIs: `tools/r/*/` standalone Rscript files
Schema: `tools/common/schemas/finding.schema.json`

## Output Rules

- Findings are risk signals, not misconduct verdicts.
- Missing tools/dependencies must be recorded as `level: info`, not as risk findings.
- Project audits run all applicable modules; missing material, disabled external lookups, unsupported script runtimes, and missing dependencies are recorded as `info`.
- Python/R scripts can be rerun automatically in a temporary copy. Stata/SPSS/SAS scripts are scanned read-only and flagged for controlled manual rerun.
- Image checks are weak-signal triage. PDF image extraction is best-effort; use original images or DOCX when image review matters.
- Every finding JSON must include `tool_id`, `tool_name`, `detector_runtime`, `dependency_status`, `source`, `input_type`, and `findings[]`.
- Do not commit private manuscripts, real research data, generated audit output, external lookup caches, credentials, or local machine paths.
- Do not add downstream delivery templates, external report workflows, or service-specific logic to this repository.
