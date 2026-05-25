# pre-check-research (pcr)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/nufegia/pre-check-research)
[![CI](https://github.com/nufegia/pre-check-research/actions/workflows/ci.yml/badge.svg)](https://github.com/nufegia/pre-check-research/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production%20stable-brightgreen.svg)](https://github.com/nufegia/pre-check-research)

**Catch data problems before reviewers do.** `pcr` is a local-first, deterministic CLI toolkit for pre-submission research package screening. It routes manuscripts, data files, statistics, images, code, references, and provenance records through reproducible checks, then produces structured findings that a human reviewer can verify and explain.

`pcr` is built for serious review workflows: it helps you find issues early, document what was checked, preserve cautious language, and decide what needs expert follow-up before a manuscript, report, or case file moves forward. It produces review leads — not misconduct verdicts.

---

## Where pcr Fits

Use `pcr` when a research package needs a documented pre-submission or pre-decision screen before it moves to a journal, supervisor, editor, institution, client, or public record.

It is designed for review workflows where the reviewer has source materials available: manuscript text, source tables, raw or summary data, analysis scripts, figures, references, and provenance context. The goal is to surface reproducible review leads early enough that a human expert can verify, resolve, or explain them.

Common fits:

- **Before submission**: researchers and PIs check tables, data, figures, references, and scripts before sending a manuscript out.
- **Before acceptance or sign-off**: labs, editorial offices, and institutions run a consistent screening checklist across packages.
- **During triage**: reviewers separate concrete, reproducible signals from speculation, missing material, dependency gaps, and extraction artifacts.
- **With AI agents**: agent workflows consume route decisions and schema-bound findings instead of guessing which checks apply.

## The Problem

Research integrity screening is time-consuming, error-prone, and often happens too late — after submission, during peer review, or post-publication. Journals, labs, and institutions need reliable, reproducible pre-submission checks, but existing tools are scattered across languages (R, Python), lack a unified output format, and require expert judgment to route the right tool to the right material.

## What pcr Solves

`pcr` solves the routing, execution, and reporting problem:

| Capability | How it works |
|---|---|
| **Deterministic routing** | Classifies input by shape (table columns, text patterns, file type), then selects applicable tools via explicit rules — no AI guessing |
| **Unified output** | Every tool emits the same JSON schema; findings merge into a single Markdown report |
| **Local-first privacy** | All computation runs on your machine; no data ever leaves your filesystem |
| **Clear boundaries** | Findings are risk signals for human review, never misconduct conclusions |
| **Multi-material projects** | Audit entire research packages: data + manuscript + code + figures + references |
| **Graceful degradation** | Missing R packages or optional dependencies become `info` records, not failures |

## What You Get

A run produces two complementary outputs:

- **Markdown report** for humans: findings grouped by tool, evidence, possible normal explanations, review steps, confidence, and limitations.
- **JSON report** for systems: schema-bound findings that can be merged, archived, diffed, or handed to an AI-assisted review workflow.

The report is designed to support a defensible review process. It does not replace source-material verification, subject-matter judgment, or statistical consultation.

## Review Boundaries

- Findings are **risk signals**, not misconduct conclusions.
- Missing tools, missing dependencies, skipped checks, and unsupported material are recorded as `level: info`.
- PDF/DOCX extraction can introduce recognition errors; important findings should be verified against source CSV/XLSX, original figures, and manuscript tables.
- Python/R scripts can be rerun in a temporary copy; Stata/SPSS/SAS scripts are scanned read-only and flagged for controlled manual rerun.

## Who Is This For

- **Researchers & PIs**: screen your own manuscript package before submission and fix issues while there is still time.
- **Journal editorial offices**: standardize pre-acceptance screening across submissions with reproducible, documented checks.
- **Research integrity officers**: triage cases with explainable leads rather than starting from scratch.
- **Peer reviewers**: supplement review with automated consistency checks.
- **Methods educators**: teach statistical error detection with concrete, runnable examples.
- **AI agent pipelines**: use structured JSON route decisions and findings instead of prompt-only tool selection.

## Supported Checks

| Category | Tools | What it catches |
|---|---|---|
| **Raw data** | `raw_data_rules` | Duplicate rows/columns, terminal digit anomalies, Benford violations, arithmetic sequences, inter-column linear transforms, high-frequency fill values, missing-by-group patterns |
| **Summary statistics** | `crosscheck`, `scrutiny` | SE/SD/N math consistency, CI centering and span, percent/count back-calculation, t/F/chi-square p-value verification, GRIM/GRIMMER/DEBIT feasibility |
| **P-values** | `p_value_collection` | Domain validity (p outside [0,1]), just-significant clustering |
| **Statistical text** | `statcheck` | APA/NHST in-text statistic vs reported p-value consistency |
| **Images** | `image_audit` | Internal duplicates (aHash/dHash/pHash), rotated/flipped copies, copy-move triage, western blot/gel review |
| **References** | `reference_audit` | DOI/PMID parsing, Crossref/OpenAlex/PubPeer/NCBI metadata queries, citation claim extraction |
| **Code** | `code_audit`, sandbox | Pattern scanning (hardcoded paths, exclusion clues), Python/R script rerun with output capture |
| **Corpus** | `corpus_signals` | Cross-manuscript text similarity (simhash, Jaccard), reference overlap, papermill phrase signals |
| **Provenance** | `provenance` | SHA-256 file hashing, append-only JSONL ledger, verify/diff change detection |

## Benchmark

13 synthetic cases, **13 pass, 0 fail**, covering every detector family. 66 risk signals and 47 info records in an offline run.

[`benchmark/BENCHMARK.md`](benchmark/BENCHMARK.md) · [`benchmark/BENCHMARK_REPORT.md`](benchmark/BENCHMARK_REPORT.md)

## Architecture

```
Input materials
  Manuscripts / CSV-XLSX / summary tables / statistical text / images / code
    │
Extraction (pcr-extract)
  Heterogeneous files → CSV/TXT/JSON intermediates
    │
Deterministic routing (tool_system.py / router.py)
  Classify by shape → select applicable tools via explicit rules
    │
Thin runner (runner.py)
  Execute route-ready tools only; record skips as info
    │
Detectors (Python + R CLI)
  detectors/raw.py / crosscheck.py / tools/r/*
    │
Unified output (models.py / reporting.py)
  Finding JSON → merged Markdown report
```

## Install

```bash
git clone https://github.com/nufegia/pre-check-research.git
cd pre-check-research
python3 -m pip install -e ".[dev]"
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages for statistical checks:

```r
install.packages(c("statcheck", "scrutiny", "rsprite2"))
```

Optional image forensics:

```bash
python3 -m pip install -e ".[image]"
```

## Try It

```bash
mkdir -p build

# Inspect which checks apply to an example summary-stat table
pcr-audit route examples/summary_stat_sample.csv --json build/route.json

# Run the applicable checks and write human + machine-readable reports
pcr-audit run examples/summary_stat_sample.csv --out build/audit.md --json build/audit.json

# Read the human report
cat build/audit.md
```

This example is a smoke test, not a complete review. It shows how `pcr` records route decisions, runs applicable checks, and emits reports. A serious pre-submission or editorial audit usually requires assembling source tables, manuscript text, figure originals, analysis scripts, references, and provenance context, then interpreting each finding against the study design and source files.

For a full package, use a project folder:

```bash
pcr-audit project path/to/project_folder --out build/project.md --json build/project.json
```

## Usage

### Single-file audit

```bash
# Route first — see which tools apply before running
pcr-audit route examples/summary_stat_sample.csv --json build/route.json

# Run with auto-detection
pcr-audit run examples/summary_stat_sample.csv --scenario auto --out build/audit.md --json build/audit.json
```

Auto-detection behavior by input shape:

| Input shape | What runs |
|---|---|
| Raw observation tables | `raw_data_rules`: duplicates, digit distribution, column relationships, outliers |
| Summary-stat tables (N/mean/SD/SE/CI/p) | `crosscheck` + `scrutiny` (when R is available) |
| Likert or integer-score summaries | `crosscheck` + `scrutiny` + `rsprite2` (when R is available) |
| p-value collections | `p_value_collection`: domain checks, clustering signals |
| APA/NHST statistical text | `statcheck` (when R is available) |
| Analysis code (.py, .R, .do, .sps, .sas) | Read-only pattern scan; Python/R scripts rerun in sandbox |

Explicit scenarios:

```bash
pcr-audit run data.csv --scenario raw --out build/raw.md --json build/raw.json
pcr-audit run summary.csv --scenario summary --out build/summary.md --json build/summary.json
pcr-audit run stats.txt --scenario text --out build/text.md --json build/text.json
```

### Multi-material project audit

```bash
pcr-audit project path/to/project_folder --out build/project.md --json build/project.json
pcr-audit project path/to/project_folder --out build/offline.md --json build/offline.json --no-external-lookups --no-rerun-code
```

Project manifest (`pcr-project.json`):

```json
{
  "project_id": "optional-id",
  "title": "optional title",
  "materials": [
    {"path": "paper.docx", "role": "manuscript"},
    {"path": "data.csv", "role": "raw_data"},
    {"path": "analysis.py", "role": "analysis_code"},
    {"path": "figures/", "role": "figures"}
  ],
  "settings": {
    "external_lookups": true,
    "grobid_url": "http://localhost:8070",
    "contact_email": ""
  }
}
```

### Extraction and merging

```bash
# Extract tables from DOCX/PDF/XLSX
pcr-extract examples/suspicious_sample.xlsx --out build/extracted --json build/extracted.json

# Merge multiple finding JSONs
pcr-report merge build/raw.json build/crosscheck.json --out build/merged.md --json build/merged.json
```

### Provenance and corpus

```bash
pcr-audit provenance record examples/project_minimal --json build/provenance.json
pcr-audit provenance verify examples/project_minimal --json build/verify.json
pcr-audit corpus build examples --out build/corpus-index.json
pcr-audit corpus screen examples/project_minimal --index build/corpus-index.json --out build/screen.md --json build/screen.json
```

## Interpreting Results

- `level: info` — run notes, missing dependencies, insufficient material, skip reasons. **Not a risk finding.**
- `low` / `medium` / `high` — risk signals requiring human review. **Not misconduct conclusions.**
- Each finding includes: evidence, calculation trace, normal explanations, review steps, confidence score, false-positive risk, and method limitations.
- PDF/DOCX extraction can introduce table-recognition errors; verify important findings against source CSV/XLSX.

## Commands

| CLI | Runtime | Purpose |
|---|---|---|
| `pcr-audit route` | Python | Explain deterministic tool routing |
| `pcr-audit run` | Python | Single-input audit pipeline |
| `pcr-audit project` | Python | Multi-material project audit |
| `pcr-audit provenance` | Python | SHA-256 provenance ledger |
| `pcr-audit corpus` | Python | Cross-manuscript corpus screening |
| `pcr-extract` | Python | Extract tables to CSV |
| `pcr-raw-audit` | Python | Raw-data digit distribution scan |
| `pcr-crosscheck` | Python | Summary-stat math cross-checks |
| `pcr-report merge` | Python | Merge finding JSON to Markdown |
| `pcr-statcheck` | R | APA/NHST reporting consistency |
| `pcr-scrutiny` | R | GRIM/GRIMMER/DEBIT feasibility |
| `pcr-sprite` | R | SPRITE discrete distribution reconstruction |

## Design Principles

- **Prefer native CLI tools** in their implementation language over forced Python wrappers.
- **Every tool declares** applicable input, dependency status, method limits, and false-positive risk.
- **Data-shape recognition** and tool-applicability decisions live in `tool_system.py`, not in agent prompts.
- **Every tool emits** unified finding JSON for downstream merging.
- **Missing tools, missing dependencies, and skipped checks** are recorded as `info`, not as risk findings.

## Documentation

- [`docs/index.md`](docs/index.md) — Overview and concepts
- [`docs/getting-started.md`](docs/getting-started.md) — First commands and workflow
- [`docs/use-cases.md`](docs/use-cases.md) — Practical workflow examples
- [`docs/methods.md`](docs/methods.md) — Detector families, limits, and interpretation
- [`docs/interpretation-boundaries.md`](docs/interpretation-boundaries.md) — Responsible reporting language
- [`llms.txt`](llms.txt) — Concise AI-agent entry point

## Examples

Built-in example projects for testing and demonstration:

- `examples/project_minimal` — Minimal project package
- `examples/project_questionnaire` — Questionnaire/social-science summary statistics
- `examples/project_biomed` — Biomedical data, image checklist, reference checks
- `examples/summary_stat_sample.csv` — Summary statistics sample
- `examples/suspicious_sample.csv`, `examples/suspicious_sample.xlsx` — Raw data samples

## Privacy and Security

- **All computation is local.** No data is uploaded to external services.
- External lookups (Crossref, OpenAlex, PubPeer, NCBI) only query public identifiers (DOI, PMID) and can be disabled with `--no-external-lookups`.
- Code reruns execute in temporary project copies with timeouts and minimal environment variables. This is not a strong security sandbox — treat unknown code accordingly.
- SHA-256 provenance ledgers are append-only and never transmit file contents.

## Citing

If you use `pcr` in your research integrity workflow, please cite:

[`CITATION.cff`](CITATION.cff)

## Contributing

Bug reports, feature requests, and pull requests are welcome on [GitHub Issues](https://github.com/nufegia/pre-check-research/issues).

Development install:

```bash
python3 -m pip install -e ".[dev,image]"
python3 -m pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
