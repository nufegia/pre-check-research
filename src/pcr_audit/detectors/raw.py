from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from pcr_audit.models import TableResult, finding_from_mapping


def analyze_raw_data_rules(name: str, df: pd.DataFrame, input_type: str = "raw_observation_table") -> TableResult:
    """Run the raw-data detector while keeping legacy implementation out of CLI code."""
    from pcr_audit.detectors.raw_legacy import analyze_raw_data_rules as legacy_analyze_raw_data_rules

    result = legacy_analyze_raw_data_rules(name, df, input_type)
    return TableResult(
        name=result.name,
        rows=result.rows,
        columns=result.columns,
        findings=[finding_from_mapping(name, asdict(finding)) for finding in result.findings],
    )
