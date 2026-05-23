# PCR Benchmark Report

## Overall Conclusion

This benchmark ran 13 test cases, 13 PASS, 0 FAIL. All passed.

- Benchmark root: `benchmark`
- Network tests: Not executed (--no-network used).
- Total risk signals: 66
- Total run/info records: 47

Conclusion: The core detection pipeline is stably covered by automated benchmarks. Deterministic mathematical checks, hash provenance, and project-level reconciliation checks serve as reliable engineering regression indicators; image checks, raw table digit distribution/inter-column relationship weak signals, and paper mill/cross-manuscript similarity are suitable for measuring 'whether review leads are surfaced', not as strong conclusion indicators.

## Coverage Summary

- Raw data: Covers duplicate/highly similar rows and columns, fixed steps, high-frequency values, missing-concentrated-by-group, terminal digit distribution, inter-column relationships, and non-continuous variable anomalies; clean controls maintain 0 risk signals.
- Summary statistics: Covers SE/SD/N, CI, percent/count, p/t/df, p-value domain, and R scrutiny/SPRITE feasibility checks.
- In-text statistics: Covers R statcheck p-value consistency checks on APA/NHST expressions.
- Literature & network: Covers DOI/PMID parsing, Crossref/OpenAlex/NCBI metadata queries, and citation claim extraction.
- Images: Covers image discovery, internal duplicates, local copy-move, metadata quality, and Western blot/gel review checklist.
- Code & project: Covers Python/R script reruns, Stata/SPSS/SAS read-only prompts, cross-material data reconciliation, project manifest, provenance version chain, and local corpus screening.

## Reliability Tiers

| Tier | Tools / Capabilities | Benchmark Interpretation |
|---|---|---|
| More Reliable | `crosscheck`, `p_value_distribution`, `data_trace_crosscheck`, `provenance_hash`, `provenance_chain_verify` | Mathematics, domain, or hash rules are explicit; suitable as regression thresholds. |
| Moderately Reliable | `raw_data_rules`, `r_statcheck`, `r_scrutiny`, `r_rsprite2`, `code_rerun_execute` | Sensitive to input format, column names, R package versions, and script dependencies; suitable as coverage and primary anomaly capture indicators. |
| Weak Signal | `raw_data_rules` digit distribution/inter-column relationship/non-continuous variable shape signals, image duplicate/copy-move, `papermill_light_signals`, `papermill_network_signals` | Only indicate that human review leads were generated; higher false positive/negative risk. |

## Network Module Test Conclusion

Not executed (--no-network used).

## Case Matrix

| Case | Type | Pass | Seconds | Risk Signals | Info | Missing Tools | Missing Checks |
|---|---:|---:|---:|---:|---|---|
| raw_suspicious | single_run | Yes | 1.16 | 16 | 0 |  |  |
| raw_clean_control | single_run | Yes | 1.046 | 0 | 0 |  |  |
| summary_suspicious | single_run | Yes | 2.083 | 17 | 2 |  |  |
| p_values_suspicious | single_run | Yes | 1.012 | 2 | 0 |  |  |
| apa_stats_suspicious | single_run | Yes | 2.193 | 2 | 0 |  |  |
| paper_refs_and_claims_offline | single_run | Yes | 1.011 | 0 | 4 |  |  |
| analysis_suspicious | single_run | Yes | 1.378 | 1 | 1 |  |  |
| analysis_manual_unsupported | single_run | Yes | 1.012 | 0 | 3 |  |  |
| figures_project | project | Yes | 1.205 | 11 | 13 |  |  |
| project_full | project | Yes | 2.555 | 12 | 19 |  |  |
| corpus_screen | corpus | Yes | 2.355 | 4 | 0 |  |  |
| provenance_change | provenance_change | Yes | 2.067 | 1 | 5 |  |  |
| external_refs_online | project_network | Yes | 0.0 | 0 | 0 |  |  |

## Tool Coverage

- `citation_claim_check`: 2 cases
- `code_rerun_audit`: 4 cases
- `code_rerun_execute`: 4 cases
- `crosscheck`: 2 cases
- `data_trace_crosscheck`: 2 cases
- `image_copy_move_internal`: 2 cases
- `image_duplicate_internal`: 2 cases
- `image_extract`: 2 cases
- `image_metadata_audit`: 2 cases
- `p_value_distribution`: 1 cases
- `papermill_light_signals`: 2 cases
- `papermill_network_signals`: 3 cases
- `project_audit`: 1 cases
- `provenance_chain_verify`: 3 cases
- `provenance_hash`: 2 cases
- `r_rsprite2`: 1 cases
- `r_scrutiny`: 2 cases
- `r_statcheck`: 1 cases
- `raw_data_rules`: 1 cases
- `reference_audit`: 2 cases
- `western_blot_review_list`: 2 cases

## Run Log

- `raw_suspicious`: Merged report generated: benchmark/reports/pcr.raw_suspicious.md
- `raw_clean_control`: Merged report generated: benchmark/reports/pcr.raw_clean_control.md
- `summary_suspicious`: Merged report generated: benchmark/reports/pcr.summary_suspicious.md
- `p_values_suspicious`: Merged report generated: benchmark/reports/pcr.p_values_suspicious.md
- `apa_stats_suspicious`: Merged report generated: benchmark/reports/pcr.apa_stats_suspicious.md
- `paper_refs_and_claims_offline`: Merged report generated: benchmark/reports/pcr.paper_refs_and_claims_offline.md
- `analysis_suspicious`: Merged report generated: benchmark/reports/pcr.analysis_suspicious.md
- `analysis_manual_unsupported`: Merged report generated: benchmark/reports/pcr.analysis_manual_unsupported.md
- `figures_project`: Project audit report generated: benchmark/reports/pcr.figures_project.md
- `project_full`: Project audit report generated: benchmark/reports/pcr.project_full.md
- `corpus_screen`: Local corpus index generated: benchmark/reports/pcr.corpus_index.json | Local corpus screening report generated: benchmark/reports/pcr.corpus_screen.md
- `provenance_change`: } | }
- `external_refs_online`: network case skipped by --no-network

## Interpretation Boundaries

The high/medium/low levels in this report are benchmark risk signals, not conclusions of academic misconduct, fabrication, or fraud. `info` records are run statuses, dependency states, skip reasons, or coverage notes; they do not count toward risk conclusions.
Network test cases depend on real-time availability, certificate chains, and rate limiting of Crossref, OpenAlex, and NCBI. If network cases fail, first check HTTP/SSL/rate-limit information in evidence before concluding it is a detector regression.
All weak-signal tools are only for surfacing human review directions. Final review should return to original data, scripts, image source files, literature metadata, and audit logs.
