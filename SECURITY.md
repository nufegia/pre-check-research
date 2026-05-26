# Security Policy

## Reporting Security Issues

Please report security issues privately through the repository's GitHub security advisory workflow when available, or by opening a minimal issue that asks the maintainers for a private contact path. Do not include exploit details, private research data, manuscripts, credentials, API keys, or confidential third-party material in a public issue.

## Data Handling

pre-check-research is designed for local pre-submission risk-signal auditing. Users are responsible for deciding what material can be processed in their environment. Do not submit real manuscripts, private datasets, identifiable human-subject data, or confidential third-party outputs as test fixtures or bug reports.

External metadata lookups for DOI/PMID checks can contact Crossref, OpenAlex, and NCBI when enabled. Use `--no-external-lookups` for offline or private reviews.
