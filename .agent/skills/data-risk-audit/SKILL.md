---
name: data-risk-audit
description: Use PCR mvp2 deterministic routing and CLI tools for research data risk auditing.
---

# Data Risk Audit SOP

Use this skill when auditing research tables, summary statistics, APA/NHST text,
or mixed paper materials with PCR mvp2.

## Core Rule

Do not infer tool suitability in agent reasoning. Always let the project route
layer decide:

```bash
pcr-audit route <input> --json output/<name>.route.json
```

For the fastest standard audit, run:

```bash
pcr-audit run <input> --scenario auto --out output/<name>.md --json output/<name>.json
```

## Agent Role

- Read route JSON and execute only tools marked `ready`.
- Treat missing tools, missing dependencies, insufficient material, and skipped
  checks as `level: info`, not data-risk findings.
- Merge outputs and write a human-readable audit narrative.
- State findings only as risk signals requiring human review.
- Never claim that a finding proves misconduct, fabrication, or fraud.

## Human Review Boundary

Reports should include what was detected, quantitative evidence, possible normal
explanations, and concrete review steps. For DOCX/PDF inputs, recommend rerunning
on original CSV/XLSX whenever findings matter.
