"""Tests for pcr-crosscheck row-level mathematical cross-checks."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

from pcr_audit.crosscheck import (
    CrosscheckTolerances,
    _check_ci_centering,
    _check_ci_span_vs_se,
    _check_ci_validity,
    _check_df_vs_n,
    _check_p_vs_t,
    _check_p_validity,
    _check_percent_count,
    _check_se_sd_n,
    _detect_columns,
    crosscheck_table,
)
from pcr_audit.cli import crosscheck_main


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def test_detect_columns_english():
    df = pd.DataFrame(columns=["n", "Mean", "SD", "SE", "ci_low", "ci_high", "count", "percent", "t", "df", "p"])
    detected = _detect_columns(df)
    assert detected["N"] == "n"
    assert detected["Mean"] == "Mean"
    assert detected["SD"] == "SD"
    assert detected["SE"] == "SE"
    assert detected["CI_low"] == "ci_low"
    assert detected["CI_high"] == "ci_high"
    assert detected["count"] == "count"
    assert detected["percent"] == "percent"
    assert detected["t"] == "t"
    assert detected["df"] == "df"
    assert "p" in detected["p"]  # type: ignore[operator]



def test_detect_columns_none():
    df = pd.DataFrame(columns=["foo", "bar", "baz"])
    detected = _detect_columns(df)
    for role in ["N", "Mean", "SD", "SE", "CI_low", "CI_high", "count", "t", "df"]:
        assert detected[role] is None
    assert detected["p"] == []


# ---------------------------------------------------------------------------
# Row-level check functions
# ---------------------------------------------------------------------------

TOL = CrosscheckTolerances()


def test_se_check_passes_correct():
    row = {"SE": 0.40, "SD": 2.0, "N": 25}
    findings: list = []
    _check_se_sd_n(row, 1, "test", findings, TOL)
    assert len(findings) == 0


def test_se_check_flags_wrong():
    row = {"SE": 0.10, "SD": 1.8, "N": 18}  # expected 0.424, reported 0.10
    findings: list = []
    _check_se_sd_n(row, 3, "test", findings, TOL)
    assert len(findings) == 1
    assert findings[0].level == "high"
    assert "76.4%" in findings[0].summary


def test_se_check_medium_deviation():
    row = {"SE": 0.90, "SD": 3.0, "N": 20}  # expected 0.671, reported 0.90, 34.2% off
    findings: list = []
    _check_se_sd_n(row, 2, "test", findings, TOL)
    assert len(findings) == 1
    assert findings[0].level == "high"  # >15%


def test_se_check_skips_missing():
    row = {"SE": 0.40, "SD": None, "N": 25}
    findings: list = []
    _check_se_sd_n(row, 1, "test", findings, TOL)
    assert len(findings) == 0


def test_ci_validity_flagged_inverted():
    row = {"CI_low": 8.2, "CI_high": 6.8}
    findings: list = []
    _check_ci_validity(row, 4, "test", findings, TOL)
    assert len(findings) == 1
    assert findings[0].level == "high"
    assert "lower bound greater than upper" in findings[0].summary


def test_ci_validity_flagged_mean_outside():
    row = {"CI_low": 6.0, "CI_high": 8.0, "Mean": 10.0}
    findings: list = []
    _check_ci_validity(row, 1, "test", findings, TOL)
    assert len(findings) == 1
    assert "Mean" in findings[0].summary


def test_ci_validity_passes():
    row = {"CI_low": 6.0, "CI_high": 8.0, "Mean": 7.0}
    findings: list = []
    _check_ci_validity(row, 1, "test", findings, TOL)
    assert len(findings) == 0


def test_ci_centering_flags_off_center():
    row = {"CI_low": 7.8, "CI_high": 8.1, "Mean": 8.0}
    findings: list = []
    _check_ci_centering(row, 3, "test", findings, TOL)
    # At 5% tolerance: CI center=7.95, mean=8.0, span=0.3, error=0.05/0.3=0.167 > 0.05
    assert len(findings) == 1


def test_ci_span_flags_wrong_se():
    # Row C: CI=(7.8,8.1), SE=0.1, df=N-1=17
    row = {"CI_low": 7.8, "CI_high": 8.1, "SE": 0.1, "df": 17}
    findings: list = []
    _check_ci_span_vs_se(row, 3, "test", findings, TOL)
    assert len(findings) == 1
    assert findings[0].level == "medium"


def test_p_validity_flags_out_of_range():
    row = {"_p_raw": {"p": "1.2"}}
    findings: list = []
    _check_p_validity(row, 4, "test", findings, TOL)
    assert len(findings) == 1
    assert findings[0].level == "high"


def test_p_validity_passes_no_pval_col():
    row = {"_p_raw": {}}
    findings: list = []
    _check_p_validity(row, 1, "test", findings, TOL)
    assert len(findings) == 0


def test_p_vs_t_flags_mismatch():
    # Row B: t=3.0, df=19, p=0.2 -> computed_p=0.00736
    row = {"t": 3.0, "df": 19, "_p_raw": {"p": "0.2"}}
    findings: list = []
    _check_p_vs_t(row, 2, "test", findings, TOL)
    assert len(findings) == 1
    assert findings[0].level == "high"


def test_p_vs_t_passes_match():
    # Row A: t=2.50, df=24, p=0.0198 -> computed_p≈0.0198
    row = {"t": 2.50, "df": 24, "_p_raw": {"p": "0.0198"}}
    findings: list = []
    _check_p_vs_t(row, 1, "test", findings, TOL)
    assert len(findings) == 0


def test_percent_count_flags_mismatch():
    row = {"percent": 25.0, "count": 8, "N": 20}
    findings: list = []
    _check_percent_count(row, 2, "test", findings, TOL)
    assert len(findings) == 1
    assert "count/N×100=40" in findings[0].evidence


def test_percent_count_passes():
    row = {"percent": 20.0, "count": 5, "N": 25}
    findings: list = []
    _check_percent_count(row, 1, "test", findings, TOL)
    assert len(findings) == 0


def test_df_vs_n_passes_onesample():
    row = {"df": 24, "N": 25}
    findings: list = []
    _check_df_vs_n(row, 1, "test", findings, TOL)
    assert len(findings) == 0


def test_df_vs_n_flags_unusual():
    row = {"df": 5, "N": 25}
    findings: list = []
    _check_df_vs_n(row, 1, "test", findings, TOL)
    assert len(findings) == 1
    assert findings[0].level == "low"


# ---------------------------------------------------------------------------
# Integration: crosscheck_table on sample data
# ---------------------------------------------------------------------------

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "summary_stat_sample.csv"


def test_crosscheck_table_finds_expected_anomalies():
    df = pd.read_csv(SAMPLE_PATH)
    result = crosscheck_table("test", df)
    levels = {f.level for f in result.findings}
    assert "high" in levels  # must have at least high-level findings
    high_count = sum(1 for f in result.findings if f.level == "high")
    assert high_count >= 6  # at least 6 high findings expected


def test_crosscheck_table_empty_df():
    df = pd.DataFrame()
    result = crosscheck_table("empty", df)
    assert result.rows == 0
    assert len(result.findings) == 0


def test_crosscheck_table_no_matching_columns():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    result = crosscheck_table("no_match", df)
    # Should have an info finding saying all clear
    assert any(f.level == "info" for f in result.findings)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_crosscheck_cli_generates_json():
    with tempfile.TemporaryDirectory() as tmp:
        out_md = Path(tmp) / "crosscheck.md"
        out_json = Path(tmp) / "crosscheck.json"
        rc = crosscheck_main([str(SAMPLE_PATH), "--out", str(out_md), "--json", str(out_json)])
        assert rc == 0
        assert out_md.exists()
        assert out_json.exists()
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        assert "results" in payload
        assert len(payload["results"]) == 1
        findings = payload["results"][0]["findings"]
        assert len(findings) >= 8
        levels = {f["level"] for f in findings}
        assert "high" in levels


def test_crosscheck_cli_file_not_found():
    rc = crosscheck_main(["nonexistent.csv", "--out", "/tmp/out.md"])
    assert rc == 2
