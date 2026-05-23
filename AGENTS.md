# PCR mvp2 — Research Data Risk Audit

Agent-oriented CLI toolkit for research data risk auditing.

## Setup

```bash
python3 -m pip install -e ".[dev]"  # use python if your environment exposes it
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional: `install.packages(c("statcheck", "scrutiny", "rsprite2"))` in R.

## Available Tools

| CLI | Runtime | Input | Purpose |
|-----|---------|-------|---------|
| `pcr-extract` | Python | DOCX/PDF/XLSX | Extract tables → CSV |
| `pcr-raw-audit` | Python | CSV | Raw-data digit distribution scan |
| `pcr-crosscheck` | Python | CSV/XLSX/DOCX/PDF | Row-level summary-stat math checks |
| `pcr-statcheck` | R | TXT | APA/NHST reporting consistency |
| `pcr-scrutiny` | R | CSV | GRIM/GRIMMER/DEBIT feasibility |
| `pcr-sprite` | R | CSV | SPRITE discrete reconstruction |
| `pcr-report merge` | Python | JSON | Merge findings → Markdown |
| `pcr-audit route` | Python | Mixed | Explain deterministic routing |
| `pcr-audit run` | Python | Mixed | One-command pipeline |
| `pcr-audit project` | Python | Folder/manifest | Multi-material project audit |
| `pcr-audit provenance` | Python | Folder/manifest | SHA-256 provenance ledger |
| `pcr-audit corpus` | Python | Folder/manifest | Local cross-manuscript screening |

Python CLIs: `src/pcr_audit/cli.py`
R CLIs: `tools/r/*/` (standalone Rscript files)
Schema: `tools/common/schemas/finding.schema.json`

## Output Rules

- Findings are risk signals, not misconduct verdicts.
- Missing tools/deps → `level: info`, not risk findings.
- Project audits run all applicable modules; missing material, disabled external lookups, unsupported script runtimes, and missing dependencies are recorded as `info`.
- Python/R scripts can be sandbox-rerun automatically. Stata/SPSS/SAS scripts are scanned read-only and flagged for controlled manual rerun.
- Image checks are weak-signal triage. PDF image extraction is best-effort; use original images or DOCX when image review matters.
- Every finding JSON must include: tool_id, tool_name, detector_runtime, dependency_status, source, input_type, findings[].

## Skills

See `.agent/skills/pcr-data-risk-audit/SKILL.md` for full workflow and tool selection rules.
