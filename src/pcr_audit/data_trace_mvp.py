"""Compatibility shim for the pre-router MVP module.

The product path now lives in focused modules:
models, io, reporting, router, runner, and detectors/*.
New code should not import from this module.
"""

from __future__ import annotations

from pcr_audit.detectors.raw import analyze_raw_data_rules
from pcr_audit.io import load_tables
from pcr_audit.models import Finding, TableResult, enrich_finding_explanation
from pcr_audit.reporting import render_markdown, save_json


def analyze_table(name, df):
    """Legacy compatibility wrapper; prefer deterministic routing."""
    return analyze_raw_data_rules(name, df)


def main(argv: list[str] | None = None) -> int:
    from pcr_audit.cli import raw_audit_main

    return raw_audit_main(argv)


__all__ = [
    "Finding",
    "TableResult",
    "analyze_raw_data_rules",
    "analyze_table",
    "enrich_finding_explanation",
    "load_tables",
    "main",
    "render_markdown",
    "save_json",
]
