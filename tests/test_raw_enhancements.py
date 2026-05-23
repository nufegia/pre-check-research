from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pcr_audit.detectors.raw import analyze_raw_data_rules
from pcr_audit.reporting import save_json


def _checks(df: pd.DataFrame) -> set[str]:
    return {finding.check for finding in analyze_raw_data_rules("demo", df).findings}


def test_raw_rules_detect_column_relationships_and_confidence_scores(tmp_path: Path) -> None:
    rng = np.random.default_rng(7)
    x = np.arange(1, 81, dtype=float)
    noisy_template = x + rng.normal(0, 7.0, size=len(x))
    df = pd.DataFrame(
        {
            "x": x,
            "double_x": x * 2,
            "shift_x": x + 5,
            "noisy_template": noisy_template,
        }
    )

    result = analyze_raw_data_rules("relationships", df)
    findings = result.findings
    checks = {finding.check for finding in findings}

    assert "Inter-column linear transform" in checks
    assert "Inter-column high correlation" in checks
    assert all(0.0 <= finding.confidence_score <= 1.0 for finding in findings)

    save_path = tmp_path / "raw.json"
    save_json(save_path, tmp_path / "source.csv", [result])
    assert '"confidence_score"' in save_path.read_text(encoding="utf-8")


def test_raw_rules_detect_similarity_rows_and_columns() -> None:
    rows = []
    for idx in range(24):
        rows.append({f"v{col}": f"{idx}-{col}" for col in range(13)})
    rows[17] = rows[2].copy()
    rows[17]["v12"] = "changed"
    df = pd.DataFrame(rows)
    df["mostly_same_a"] = list(range(22)) + [100, 101]
    df["mostly_same_b"] = list(range(22)) + [200, 201]
    df.loc[17, ["mostly_same_a", "mostly_same_b"]] = df.loc[2, ["mostly_same_a", "mostly_same_b"]]

    checks = _checks(df)

    assert "Highly similar rows" in checks
    assert "Highly similar columns" in checks


def test_raw_rules_detect_numeric_column_similarity_with_tolerance() -> None:
    base = np.arange(1, 61, dtype=float)
    df = pd.DataFrame(
        {
            "measure_a": base,
            "measure_b": base * 1.005,
            "noise": np.linspace(100, 200, len(base)),
        }
    )

    result = analyze_raw_data_rules("numeric_similarity", df)
    findings = [finding for finding in result.findings if finding.check == "Highly similar columns"]

    assert findings
    assert findings[0].confidence_basis


def test_raw_rules_assign_confidence_basis_to_basic_checks() -> None:
    values = [float(f"{idx}.17") for idx in range(1, 121)]
    df = pd.DataFrame({"terminal_pattern": values})

    findings = analyze_raw_data_rules("basic_confidence", df).findings
    terminal_digit = [finding for finding in findings if finding.check == "Terminal digit distribution"]

    assert terminal_digit
    assert terminal_digit[0].confidence_basis
    assert terminal_digit[0].confidence_score != 0.6


def test_raw_rules_detect_non_continuous_variable_anomalies() -> None:
    df = pd.DataFrame(
        {
            "treatment_group": ["A"] * 98 + ["B"] * 101 + ["Other"],
            "anxiety_score": [1] * 42 + [4] * 5 + [5] * 153,
        }
    )

    checks = _checks(df)

    assert "Low-frequency category" in checks
    assert "Ordinal variable extreme concentration" in checks
