# pre-check-research Documentation

pre-check-research (`pcr`) is a local-first toolkit for pre-submission research package audit workflows. It helps researchers, labs, reviewers, editors, and research integrity teams route research materials to deterministic checks and produce explainable risk signals for human review.

`pcr` is designed for cautious review workflows. It can surface statistical inconsistencies, data-shape anomalies, provenance changes, code rerun notes, image triage leads, and cross-material reconciliation issues. It must not be used to make misconduct determinations by itself.

## Reader Paths

- **I need to try it quickly**: start with [Getting started](getting-started.md), run `pcr-audit route`, then run `pcr-audit run` on an example CSV.
- **I have a manuscript package**: read [Use cases](use-cases.md), prepare a `pcr-project.json`, and run `pcr-audit project`.
- **I need to interpret a report**: read [Interpretation boundaries](interpretation-boundaries.md) before turning findings into reviewer, editor, lab, or external-facing language.
- **I am an AI agent**: read [`llms.txt`](https://github.com/nufegia/pre-check-research/blob/main/llms.txt), preserve JSON outputs, and do not infer misconduct from risk signals.

## Start Here

- [Getting started](getting-started.md): install the package and run the first route/audit commands.
- [Use cases](use-cases.md): common workflows for manuscripts, labs, reviewers, and AI agents.
- [Methods](methods.md): detector families, inputs, outputs, and known limits.
- [Interpretation boundaries](interpretation-boundaries.md): responsible language for reports and review notes.
- [Benchmark](benchmark.md): synthetic benchmark design and coverage.

## Search Terms

Relevant terms include research integrity, reproducibility, open science, data audit, data quality, statistical consistency, manuscript screening, pre-submission review, forensic statistics, `statcheck`, GRIM/GRIMMER, DEBIT, and SPRITE.

## Project Links

- Repository: https://github.com/nufegia/pre-check-research
- Citation metadata: [`CITATION.cff`](https://github.com/nufegia/pre-check-research/blob/main/CITATION.cff)
- AI-agent entry point: [`llms.txt`](https://github.com/nufegia/pre-check-research/blob/main/llms.txt)
