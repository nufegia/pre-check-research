# PCR mvp2

Agent-oriented CLI toolkit for research data risk auditing.

## Install

```bash
python -m pip install -e ".[dev]"
```

R CLIs are executable `Rscript` files under `tools/r/`. Add them to `PATH` when you want short command names:

```bash
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages:

```r
install.packages(c("statcheck", "scrutiny", "rsprite2"))
```

## Commands

```bash
pcr-extract examples/suspicious_sample.xlsx --out build/extracted --json build/extracted.json
pcr-raw-audit examples/suspicious_sample.csv --out build/raw.md --json build/raw.json
pcr-scrutiny examples/summary_stat_sample.csv --scale-min 1 --scale-max 5 --json build/scrutiny.json
pcr-report merge build/raw.json build/scrutiny.json --out build/merged.md --json build/merged.json
```

`pcr-audit run` is an optional orchestration layer. Prefer direct tool CLIs when an agent already knows which input and detector are appropriate.
