# Use Cases

## Pre-Submission Manuscript Review

Use `pcr` before journal submission to check whether tables, manuscript text, raw data, scripts, references, figures, and supplements contain review leads that should be resolved before submission.

Good fit:

- A manuscript package with source tables, analysis scripts, figures, and references.
- A lab wants a documented pre-submission checklist before the corresponding author signs off.
- A researcher wants to know which issues are mechanical consistency problems and which require statistical or domain review.

Not enough by itself:

- A final accusation, misconduct finding, or publication decision.
- A review where the source data, manuscript tables, or figure originals cannot be inspected.

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

Recommended workflow:

1. Route the submitted material and record skipped or unsupported checks as `info`.
2. Run applicable checks and preserve the JSON output.
3. Verify high-impact findings against the original source files.
4. Convert findings into cautious review language using [Interpretation boundaries](interpretation-boundaries.md).

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
