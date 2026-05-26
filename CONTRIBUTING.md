# Contributing

Thanks for helping improve pre-check-research (pcr).

## Development Setup

```bash
python3 -m pip install -e ".[dev]"
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages:

```r
install.packages(c("statcheck", "scrutiny", "rsprite2"))
```

Optional local image checks:

```bash
python3 -m pip install -e ".[image]"
```

## Checks Before a Pull Request

```bash
python3 -m pytest -q
python3 benchmark/run_benchmark.py --no-network
python3 -m build --outdir /tmp/pcr-build-check
```

Network benchmark coverage can be run with `python3 benchmark/run_benchmark.py`, but external Crossref, OpenAlex, and NCBI availability can vary.

## Contribution Guidelines

- Findings must remain risk signals, not misconduct verdicts.
- Missing dependencies, skipped checks, and unsupported material should be recorded as `level: info`.
- Do not commit real manuscripts, private research data, confidential third-party materials, local audit outputs, API keys, credentials, or external lookup caches.
- Keep CLI output compatible with `tools/common/schemas/finding.schema.json`.
