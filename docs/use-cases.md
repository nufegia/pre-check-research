# Use Cases

## Pre-Submission Manuscript Review

Use `pcr` before journal submission to check whether tables, manuscript text, raw data, scripts, references, figures, and supplements contain review leads that should be resolved before submission.

Useful commands:

```bash
pcr-audit project path/to/project_folder --out build/project.md --json build/project.json
pcr-audit provenance record path/to/project_folder --json build/provenance-record.json
```

## Lab or Institutional Reproducibility Screening

Use project audits and provenance records to review a research package before internal sign-off. Keep all private data local and disable external lookups when required.

```bash
pcr-audit project path/to/project_folder --out build/project-offline.md --json build/project-offline.json --no-external-lookups
```

## Editorial or Peer Review Support

Use `pcr` to produce cautious, evidence-linked review leads. Reports should describe anomalous signals, possible normal explanations, and suggested checks. They should not accuse authors or assert misconduct.

Useful inputs:

- Manuscript DOCX/PDF files.
- Supplementary CSV/XLSX tables.
- Statistical text exports.
- Figure source images.
- Analysis scripts.

## AI-Assisted Audit Orchestration

Agents should read route JSON and run only tools marked ready. Agents can help merge outputs, write cautious summaries, and suggest next review steps, but tool applicability should come from `pcr-audit route`, not from an agent guess.

```bash
pcr-audit route path/to/material --json build/route.json
pcr-audit run path/to/material --scenario auto --out build/audit.md --json build/audit.json
```

See [`llms.txt`](https://github.com/nufegia/pre-check-research/blob/main/llms.txt) for the concise AI-agent entry point.

## Teaching and Benchmarking

The benchmark fixtures provide examples for teaching statistical consistency checks, weak-signal triage, provenance tracking, and responsible interpretation.

```bash
python3 benchmark/run_benchmark.py --no-network
```
