# Methods

`pcr` combines deterministic routing with multiple detector families. Each detector should declare applicable input types, dependency status, method limits, and false-positive risk.

## Detector Families

| Area | Examples | Notes |
|---|---|---|
| Raw data rules | Digit distributions, repeated rows/columns, column relationships, category shape, missingness concentration | Useful for surfacing review leads; many signals are weak and context-sensitive. |
| Summary-stat cross-checks | N/mean/SD/SE/CI/count/percentage/t/df/p consistency | More deterministic when input tables are parsed correctly and columns are identifiable. |
| Statistical text | APA/NHST consistency through `statcheck` | Depends on text extraction quality and R package availability. |
| Likert/integer feasibility | GRIM/GRIMMER/DEBIT and SPRITE-style reconstruction | Depends on scale assumptions and R package availability. |
| P-value collections | Domain validity and just-significant clustering signals | Domain errors are strong; distributional signals need careful context. |
| Project audit | References, cited claims, paper-mill light signals, cross-material reconciliation, code reruns | Designed for mixed manuscript/data/code packages. |
| Image triage | Internal duplicates, copy-move candidates, metadata checks, blot/gel checklist | Weak-signal triage only; use original images for serious review. |
| Provenance and corpus | SHA-256 ledger, change verification, local cross-manuscript similarity | Useful for package history and local corpus screening. |

## Routing

Use routing to decide tool applicability:

```bash
pcr-audit route path/to/input --json build/route.json
```

The route output records ready tools, missing dependencies, skipped checks, and unsupported inputs as structured data. Missing tools and dependencies should be recorded as `level: info`, not converted into risk findings.

## Outputs

Every finding JSON should include `tool_id`, `tool_name`, `detector_runtime`, `dependency_status`, `source`, `input_type`, and `findings[]`.

Markdown reports are readable summaries. JSON reports are the preferred machine-readable artifact for merging, automation, and audit trails.
