# pre-check-research (pcr) - Claude Instructions

Data risk audit toolkit. Python and R CLI tools inspect research materials and emit structured risk-signal findings. `pcr` is the project abbreviation used by all commands, output filenames, and schemas.

This file is guidance for Claude-style coding agents working in this repository. It is not part of the runtime API.

## Rules

- **Role**: Data risk audit toolchain, not misconduct adjudicator. Reports stay at "anomalous signal -> evidence -> possible normal explanations -> review steps." Never output misconduct conclusions.
- **Missing tools/dependencies**: Record as `level: info`, not as risk findings.
- **Output**: Use `output/` for local ad hoc audit outputs when no other path is specified. Examples and tests may use `build/`, `benchmark/reports/`, or temporary directories.
- **Naming**: Output files use the `pcr` prefix, for example `pcr.audit.md`. Never derive filenames from input names.
- **Repository hygiene**: Do not commit private manuscripts, real research data, generated audit output, external lookup caches, credentials, or local machine paths.

## Setup

```bash
python -m pip install -e ".[dev]"
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages: `install.packages(c("statcheck", "scrutiny", "rsprite2"))`

## Commands

| CLI | Runtime | Purpose |
|-----|---------|---------|
| `pcr-audit run` | Python | Route and run detectors on a single file. |
| `pcr-audit project` | Python | Audit a project folder. |
| `pcr-audit corpus` | Python | Build or screen a cross-manuscript corpus. |
| `pcr-audit provenance` | Python | Record or verify file provenance chains. |
| `pcr-extract` | Python | Extract tables from DOCX/PDF/XLSX to CSV. |
| `pcr-raw-audit` | Python | Raw-data digit distribution scan. |
| `pcr-report merge` | Python | Merge finding JSON files to Markdown. |
| `pcr-statcheck` | R | APA/NHST text statistical consistency. |
| `pcr-scrutiny` | R | GRIM/GRIMMER/DEBIT summary feasibility. |
| `pcr-sprite` | R | SPRITE discrete distribution reconstruction. |

All tools emit finding JSON conforming to `tools/common/schemas/finding.schema.json`.

## Source Layout

```text
src/pcr_audit/             Python package (CLI, detectors, models, IO)
tools/r/                   Standalone R CLI scripts
tools/python/              Python tool README
tools/common/schemas/      JSON Schema for finding payloads
tests/                     Pytest test suite
benchmark/                 Fixtures, runner, reports
```

## R CLI Conventions

- Execute with `Rscript <script> <input> --json <output.json>`.
- Missing R packages must produce an info-level finding and exit 0.
- Use `--scale-min` and `--scale-max` for scale-bounded tools.
- `--json` sets the output file; stdout is used when it is omitted.
