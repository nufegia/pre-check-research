# Changelog

## v1.3.1

- Fixed the audit HTTP user agent to use the package version consistently.

## v1.3.0

- Added layout-aware XLSX extraction that splits visually arranged source-data sheets into separate logical tables using borders, blank row/column separators, merged-cell labels, and cell ranges.
- Preserved unsegmented sheets in mixed workbooks so normal long-form data sheets remain available alongside extracted layout tables.
- Added regression coverage for bordered Excel table extraction and mixed-workbook preservation.

## v1.2.0

- Added public report export support with schema metadata and CLI coverage.
- Expanded project audit checks for references, image signals, routing, raw data, and summary-stat crosschecks.
- Improved benchmark fixtures, benchmark reports, and documentation for the updated audit behavior.
- Added development tooling configuration for pytest, ruff, mypy, and type stubs.

## v1.1.0

- Renamed the project to `pre-check-research` and standardized the `pcr` CLI/output prefix.
- Added project-level audits for mixed research materials.
- Expanded raw-data, summary-stat, p-value, image, provenance, corpus, and code checks.
- Added benchmark coverage and open-source release files.
