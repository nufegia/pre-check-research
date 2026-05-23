# Open Source Release Checklist

Use this checklist when publishing `pre-check-research` on GitHub, PyPI, documentation sites, and citation indexes.

## GitHub Repository Metadata

Recommended short description:

> Pre-submission research data audit toolkit for reproducibility checks, statistical consistency screening, manuscript/material review, and research integrity workflows.

Recommended topics:

```text
research-integrity
reproducibility
data-audit
data-quality
statistics
statistical-consistency
forensic-statistics
manuscript-screening
pre-submission
open-science
scientific-computing
research-software
statcheck
grim
sprite
python
rstats
```

Recommended website URL:

```text
https://precheckresearch.github.io/pre-check-research/
```

## Search and AI Discovery

- Keep `README.md` first-screen language focused on use cases and search terms.
- Keep `llms.txt` concise and current when commands or interpretation boundaries change.
- Keep `CITATION.cff` aligned with the current release version.
- Link benchmark results from the README and documentation home.
- Prefer stable phrases: research integrity, reproducibility, data audit, statistical consistency, manuscript screening, pre-submission review, and open science.

## Release Hygiene

- Run tests: `python3 -m pytest -q`.
- Run offline benchmark: `python3 benchmark/run_benchmark.py --no-network`.
- Check package build: `python3 -m build --outdir /tmp/pcr-build-check`.
- Do not publish private manuscripts, real research data, generated client audit output, external lookup caches, credentials, or local machine paths.
