# pre-check-research (pcr)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/PreCheckResearch/pre-check-research) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Pre-check research data risk audit toolkit. The project name is `pre-check-research`; `pcr` is the abbreviation used for CLI commands, output stems, schemas, and agent workflows.

pcr routes research materials to deterministic CLI tools and emits mergeable, explainable, reviewable risk signals. Reports must stay at the level of "anomalous signal, evidence, possible normal explanations, review steps" and must not make misconduct determinations.

## Architecture

```text
Input materials
  Manuscripts / raw CSV-XLSX / summary-stat tables / statistical text / images
    |
Extraction layer (pcr-extract)
  Heterogeneous files -> CSV/TXT/JSON intermediates
    |
Deterministic routing layer
  tool_system.py / router.py / pcr-audit route
    |
Thin runner
  runner.py executes route-ready tools only
    |
Detector layer (Python CLI / R CLI)
  detectors/raw.py / crosscheck.py / tools/r/*
    |
Unified result layer
  models.py / reporting.py / finding JSON
    |
Agent orchestration layer
  Reads route decisions and reports, then adds human-review narrative when needed
```

## Install

```bash
python3 -m pip install -e ".[dev]"  # use python if your environment exposes it
```

The GitHub source checkout includes both the Python CLIs and the standalone R CLIs under `tools/r/`. Python packaging currently installs the Python entry points only; add the R CLI directories to `PATH` when using the R-backed tools:

```bash
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages:

```r
install.packages(c("statcheck", "scrutiny", "rsprite2"))
```

Optional local image forensics dependencies:

```bash
python3 -m pip install -e ".[image]"
```

Local audit outputs can be written to `output/` or any explicit `--out` path. Generated reports, extracted images, external lookup caches, and private research materials should not be committed.

## Usage

Prefer the deterministic route layer before running an audit. This records tool applicability and missing dependencies in JSON instead of leaving those decisions to an agent or an ad hoc operator.

```bash
mkdir -p build
pcr-audit route examples/summary_stat_sample.csv --json build/route.json
pcr-audit run examples/summary_stat_sample.csv --scenario auto --out build/audit.md --json build/audit.json
```

`pcr-audit run` classifies the input, executes route-ready tools, and merges outputs into Markdown and unified JSON. The default `--scenario auto` behavior depends on the input shape:

| Input shape | Auto scenario behavior |
|-------------|------------------------|
| Raw observation tables and figure source data | Runs Python table rules through `raw_data_rules`, including digit distribution, repeated or highly similar rows and columns, column relationships, and discrete-variable shape checks. |
| Summary-stat tables | Runs row-level mathematical cross-checks through `crosscheck`, and runs `scrutiny` when R dependencies are available. |
| Likert or integer-score summaries | Runs `crosscheck`, `scrutiny`, and `rsprite2` when R dependencies are available. |
| p-value collections | Runs `p_value_distribution` to check p-value domain validity and weak signals around just-significant clustering. |
| APA/NHST statistical text | Runs `statcheck` when R dependencies are available. |
| Analysis code files | Runs a lightweight read-only code scan; Python and R scripts can be rerun in a temporary copy, while Stata/SPSS/SAS scripts are recorded as `info` for controlled manual rerun. |

Explicit scenarios are also available:

```bash
pcr-audit run data.csv --scenario raw --out build/raw.md --json build/raw.json
pcr-audit run summary.csv --scenario summary --out build/summary.md --json build/summary.json
pcr-audit run stats.txt --scenario text --out build/text.md --json build/text.json
pcr-audit run likert_summary.csv --scenario r-advanced --out build/sprite.md --json build/sprite.json
```

Use `--dry-run` to inspect route decisions without running detectors:

```bash
pcr-audit run examples/summary_stat_sample.csv --out build/dry.md --json build/dry-route.json --dry-run
```

For DOCX/PDF/XLSX materials, extract intermediate files first and then run the relevant CSV/TXT tools:

```bash
pcr-extract examples/suspicious_sample.xlsx --out build/extracted --json build/extracted.json
pcr-raw-audit build/extracted/01_Sheet1.csv --out build/raw.md --json build/raw.json
```

Use the paths in `build/extracted.json` under `outputs[].path` as the source of truth for extracted filenames. If an extracted CSV is a summary-stat table, pass it to `pcr-crosscheck` or let `pcr-audit run` route it automatically.

Use `pcr-report merge` to combine multiple finding JSON files manually:

```bash
pcr-report merge build/raw.json build/crosscheck.json --out build/merged.md --json build/merged.json
```

Interpretation boundaries:

- `level: info` usually means run notes, missing dependencies, insufficient material, or skip reasons; it is not a risk finding.
- `medium` and `high` indicate risk signals requiring human review; they are not findings of misconduct, fabrication, fraud, or data manipulation.
- PDF/DOCX extraction can introduce table-recognition errors; important findings should be rerun against source CSV/XLSX files, statistical scripts, or raw data when possible.
- Image checks are weak-signal triage; PDF image extraction is best-effort, and complex layouts should be reviewed with original images or DOCX sources.

## Commands

| CLI | Runtime | Input | Purpose |
|-----|---------|-------|---------|
| `pcr-extract` | Python | XLSX/DOCX/PDF | Extract tables to CSV. |
| `pcr-raw-audit` | Python | CSV | Scan raw-data digit distribution and table-shape signals. |
| `pcr-crosscheck` | Python | CSV/XLSX/DOCX/PDF | Run row-level summary-stat math cross-checks. |
| `pcr-statcheck` | R | TXT | Check APA/NHST reporting consistency. |
| `pcr-scrutiny` | R | CSV | Run GRIM/GRIMMER/DEBIT feasibility checks. |
| `pcr-sprite` | R | CSV | Run SPRITE discrete reconstruction. |
| `pcr-report merge` | Python | JSON | Merge finding JSON into Markdown. |
| `pcr-audit route` | Python | Mixed | Explain deterministic tool routing. |
| `pcr-audit run` | Python | Mixed | Run the single-input pipeline. |
| `pcr-audit project` | Python | Folder/manifest | Run a multi-material pre-submission audit. |
| `pcr-audit provenance` | Python | Folder/manifest | Maintain an append-only SHA-256 JSONL ledger. |
| `pcr-audit corpus` | Python | Folder/manifest | Build and screen a local cross-manuscript corpus. |

```bash
pcr-audit route examples/summary_stat_sample.csv --json build/route.json
pcr-audit run examples/summary_stat_sample.csv --out build/auto.md --json build/auto.json
pcr-audit project path/to/project_folder --out build/project.md --json build/project.json
pcr-audit project path/to/project_folder --out build/project-offline.md --json build/project-offline.json --no-external-lookups --no-rerun-code
pcr-audit project examples/project_minimal --out build/project-minimal.md --json build/project-minimal.json
pcr-audit provenance record examples/project_minimal --json build/provenance-record.json
pcr-audit provenance verify examples/project_minimal --json build/provenance-verify.json
pcr-audit corpus build examples --out build/corpus-index.json
pcr-audit corpus screen examples/project_minimal --index build/corpus-index.json --out build/corpus-screen.md --json build/corpus-screen.json
pcr-audit project examples/project_questionnaire --inspect --json build/project-questionnaire.inspect.json
pcr-audit run examples/summary_stat_sample.csv --out build/route.md --json build/route.json --dry-run
pcr-extract examples/suspicious_sample.xlsx --out build/extracted --json build/extracted.json
pcr-raw-audit examples/suspicious_sample.csv --out build/raw.md --json build/raw.json
pcr-crosscheck examples/summary_stat_sample.csv --out build/crosscheck.md --json build/crosscheck.json
pcr-scrutiny examples/summary_stat_sample.csv --scale-min 1 --scale-max 5 --json build/scrutiny.json
pcr-report merge build/raw.json build/scrutiny.json --out build/merged.md --json build/merged.json
```

For deterministic operation, prefer `pcr-audit route` and `pcr-audit run --scenario auto`. Agents should not guess tool applicability; they should read the route output and execute tools marked ready. Agents are only expected to help with multi-material orchestration, narrative reporting, and human-review suggestions.

## Python Modules

- `models.py`: Finding/result data models and explanation enrichment.
- `io.py`: Input parsing, table reading, text extraction, and extraction manifests.
- `tool_system.py`: Tool registry, data classification, dependency status, and routing decisions.
- `router.py`: Stable route JSON construction.
- `runner.py`: Execution of route-ready tools and result merging.
- `reporting.py`: Markdown/JSON report rendering and merge utilities.
- `detectors/` and `crosscheck.py`: Detector implementations.
- `product_detectors.py`: Project-level incremental checks, including reference audit, citation-claim extraction, lightweight paper-mill signals, internal image-duplicate triage, hash provenance, and lightweight code-rerun readiness checks.
- `data_trace.py`: Cross-material summary-stat reconciliation and temporary Python/R script reruns.

## Project Audits

`pcr-audit project <folder-or-manifest>` audits a multi-material project package:

- Data files: Continue through deterministic routing for raw-data rules, digit-distribution weak signals, p-value collection signals, cross-checks, and available R tools.
- Documents and references: Parse DOI/PMID identifiers, query Crossref/OpenAlex/NCBI metadata by default, extract cited claims, and scan lightweight paper-mill phrase signals; use `--no-external-lookups` to disable network calls.
- Cross-material reconciliation: Compare determinable N, mean, SD, SE, count, and percent values across manuscript/supplement tables, raw-data summaries, and script output tables.
- Images: Discover or extract image files from images, DOCX, PDF, or image directories; use Pillow/numpy/scipy aHash/dHash/pHash and optional OpenCV ORB for internal duplicates, rotated/flipped similarity, local copy-move triage, and blot/gel review checklists. PDF image extraction is best-effort; complex layouts should use original images or DOCX sources.
- Code: Run lightweight read-only scans of R/Python/Stata/SPSS/SAS scripts for paths, inputs, missing-data exclusion, and significance-filtering clues. Python/R scripts are rerun by default in a temporary project copy, with captured outputs included in cross-material reconciliation; use `--no-rerun-code` to disable this. Stata/SPSS/SAS scripts are not executed automatically and are recorded as `info` for controlled manual rerun.
- Provenance: Compute SHA-256 hashes, file sizes, and modification times; `pcr-audit provenance` can append records to a JSONL ledger and verify matched/changed/missing/new status.
- Local corpus signals: Use `pcr-audit corpus build/screen` to index local project corpora and screen for text-template similarity, reference overlap, author/email-domain overlap, and cross-manuscript image-fingerprint similarity.

v1.1.0 includes the current table rules, confidence scoring, project preflight checks, example projects, and internal extension structure:

```bash
pcr-audit project examples/project_questionnaire --inspect --json build/questionnaire.inspect.json
pcr-audit project path/to/new_project --init-manifest
```

Built-in examples cover three common service scenarios:

- `examples/project_minimal`: Minimal project package.
- `examples/project_questionnaire`: Questionnaire/social-science summary statistics and raw responses.
- `examples/project_biomed`: Biomedical data, image-material checklist, and reference checks.

Project audits query Crossref/OpenAlex/NCBI for DOI/PMID metadata by default and record lookup cache/compliance metadata in the workdir. Offline or private runs can disable this explicitly:

```bash
pcr-audit project examples/project_minimal --out build/project.md --json build/project.json --contact-email you@example.org
pcr-audit project examples/project_minimal --out build/project-offline.md --json build/project-offline.json --no-external-lookups
```

Project manifests use `pcr-project.json`:

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

Optional GROBID REST support can be enabled through the manifest, `PCR_GROBID_URL`, or CLI parameters:

```bash
pcr-audit project examples/project_minimal --out build/project.md --json build/project.json --grobid-url http://localhost:8070
```

Commercial or private deployments do not include PyMuPDF, grobid-client, imagehash, unstructured, or tabula-py by default. PDF image extraction uses pdfplumber/Pillow best-effort behavior, GROBID is integrated as an independent REST service, and external lookups record cache/compliance metadata without caching full manuscript text. Script reruns use temporary project copies, minimal environment variables, and timeouts; this is not a strong security sandbox, so unknown code should still run on controlled machines. Project audits run all applicable modules; missing dependencies, insufficient material, disabled external lookups, and unsupported script languages are recorded as `info`, not as risk findings.

## Extension Principles

- Prefer native CLI tools in their implementation language over forced Python wrappers.
- Every tool must declare applicable input, dependency status, method limits, and false-positive risk.
- Data-shape recognition and tool-applicability decisions must live in `tool_system.py`, not in agent prompts or skills.
- Every tool must emit unified finding JSON for downstream merging.
- Third-party commercial tools should be integrated as independent CLIs/connectors with clear data-upload compliance boundaries.
- Missing tools, missing dependencies, and skipped checks must be recorded as `info`, not as data-risk findings.
