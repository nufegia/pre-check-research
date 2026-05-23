# PCR mvp2 Benchmark System

This directory is the benchmark home for PCR mvp2. It contains synthetic fixtures, expected coverage, a runner, and generated reports.

## Layout

- `generate_synthetic_benchmark.py`: regenerates benchmark fixtures under this directory.
- `benchmark_manifest.json`: declares benchmark cases, expected tools, expected checks, and minimum/maximum finding counts.
- `run_benchmark.py`: runs the suite and writes `BENCHMARK_REPORT.md`, `reports/pcr.benchmark_summary.json`, and `reports/pcr.benchmark_summary.md`.
- `inputs/`: single-file, project, image, code, provenance, and network fixtures.
- `corpus/`: local cross-manuscript corpus fixture.
- `reports/`: benchmark outputs from PCR CLIs.
- `BENCHMARK_REPORT.md`: latest human-readable benchmark summary at the benchmark root.

## Run

From the repo root:

```bash
python3 /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/run_benchmark.py
```

To skip external Crossref/OpenAlex/NCBI calls:

```bash
python3 /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/run_benchmark.py --no-network
```

To regenerate fixtures before running:

```bash
python3 /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/run_benchmark.py --regenerate
```

## Coverage

The suite covers raw data rules, digit distribution, summary-stat crosscheck, R scrutiny, R statcheck, R rsprite2, p-value collection checks, reference parsing, external metadata lookup, citation claim extraction, papermill light/network signals, image duplicate/copy-move/metadata review, code scan/rerun, unsupported code recording, data trace crosscheck, provenance record/verify, and local corpus screening.

Network coverage uses `inputs/project_external` and expects evidence from Crossref, OpenAlex, and NCBI. Network failures should be interpreted separately from detector regressions because external APIs can be unavailable, rate-limited, or return changed metadata.

## Interpretation

Findings are risk signals, not misconduct verdicts. `info` records are operational status, dependency status, skip reasons, or coverage notes. Weak-signal tools such as image forensics, digit distribution, and papermill similarity should be evaluated for surfacing review leads, not for proving a conclusion.
