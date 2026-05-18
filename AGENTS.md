# PCR mvp2 — Research Data Risk Audit

Agent-oriented CLI toolkit for research data risk auditing.

## Setup

```bash
python -m pip install -e ".[dev]"
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional: `install.packages(c("statcheck", "scrutiny", "rsprite2"))` in R.

## Available Tools

| CLI | Runtime | Input | Purpose |
|-----|---------|-------|---------|
| `pcr-extract` | Python | DOCX/PDF/XLSX | Extract tables → CSV |
| `pcr-raw-audit` | Python | CSV | Raw-data digit distribution scan |
| `pcr-statcheck` | R | TXT | APA/NHST reporting consistency |
| `pcr-scrutiny` | R | CSV | GRIM/GRIMMER/DEBIT feasibility |
| `pcr-sprite` | R | CSV | SPRITE discrete reconstruction |
| `pcr-report merge` | Python | JSON | Merge findings → Markdown |
| `pcr-audit run` | Python | Mixed | One-command pipeline |

Python CLIs: `src/pcr_audit/cli.py`
R CLIs: `tools/r/*/` (standalone Rscript files)
Schema: `tools/common/schemas/finding.schema.json`

## Output Rules

- Findings are risk signals, not misconduct verdicts.
- Missing tools/deps → `level: info`, not risk findings.
- Every finding JSON must include: tool_id, tool_name, detector_runtime, dependency_status, source, input_type, findings[].

## Skills

See `.agent/skills/data-risk-audit/SKILL.md` for full workflow and tool selection rules.
