# Getting Started

## Install

From the repository root:

```bash
python3 -m pip install -e ".[dev]"
```

Optional R-backed tools are stored under `tools/r/`:

```bash
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages:

```r
install.packages(c("statcheck", "scrutiny", "rsprite2"))
```

Optional image triage dependencies:

```bash
python3 -m pip install -e ".[image]"
```

## First Audit

Use the deterministic route layer before running an audit:

```bash
mkdir -p build
pcr-audit route examples/summary_stat_sample.csv --json build/route.json
pcr-audit run examples/summary_stat_sample.csv --scenario auto --out build/audit.md --json build/audit.json
```

Use `--dry-run` to inspect routing without running detectors:

```bash
pcr-audit run examples/summary_stat_sample.csv --out build/dry.md --json build/dry-route.json --dry-run
```

## Project Folder Audit

```bash
pcr-audit project examples/project_minimal --out build/project.md --json build/project.json
```

For offline or private runs, disable external DOI/PMID metadata lookups:

```bash
pcr-audit project examples/project_minimal --out build/project-offline.md --json build/project-offline.json --no-external-lookups
```

## Read the Outputs

- Markdown reports are for human review.
- JSON outputs are the source of truth for merging, agent workflows, and downstream tools.
- `level: info` records run notes, missing dependencies, disabled lookups, unsupported material, or skipped checks. It is not a risk finding.
