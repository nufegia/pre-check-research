# Benchmark

The repository includes a synthetic benchmark suite for regression checks and communication about current coverage. It is designed to test whether `pcr` can surface expected review leads without treating weak signals as conclusions.

## Current Checked-In Summary

The latest checked-in offline report covers 13 synthetic cases, with 13 passing and 0 failing. It includes raw data rules, summary-stat cross-checks, p-value collections, APA/NHST text, reference and claim parsing, image triage, code scans/reruns, provenance checks, and local corpus screening.

See the repository files for full details:

- [`benchmark/BENCHMARK.md`](https://github.com/nufegia/pre-check-research/blob/main/benchmark/BENCHMARK.md)
- [`benchmark/BENCHMARK_REPORT.md`](https://github.com/nufegia/pre-check-research/blob/main/benchmark/BENCHMARK_REPORT.md)

## Run Locally

```bash
python3 benchmark/run_benchmark.py --no-network
```

Network benchmark coverage can be run without `--no-network`, but Crossref, OpenAlex, PubPeer, and NCBI availability can vary.
