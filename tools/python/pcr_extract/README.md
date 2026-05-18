# Python CLI implementation

The Python CLIs are packaged from `src/pcr_audit` and installed through `pyproject.toml`:

- `pcr-extract`
- `pcr-raw-audit`
- `pcr-report`
- `pcr-audit`

This directory exists to keep the project-level tool map aligned with the mvp2 architecture: Python owns extraction, normalization, raw-data checks, and report merging. The executable entry points remain in the standard Python package layout so `pip install -e .` works normally.
