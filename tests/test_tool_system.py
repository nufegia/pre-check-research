from __future__ import annotations

import pandas as pd

from pcr_audit.tool_system import (
    TOOL_REGISTRY,
    classify_table,
    classify_text,
    route_tool,
)


def test_classify_raw_observation_table() -> None:
    df = pd.DataFrame({"subject": ["S1", "S2", "S3"], "value": [1.2, 1.5, 1.7]})

    result = classify_table(df)

    assert result["primary_type"] == "raw_observation_table"
    assert result["input_types"] == ["raw_observation_table"]


def test_classify_summary_statistics_table() -> None:
    df = pd.DataFrame({"group": ["A", "B"], "n": [25, 20], "mean": [10.0, 12.0], "sd": [2.0, 3.0]})

    result = classify_table(df)

    assert result["primary_type"] == "summary_statistics_table"
    assert "summary_statistics_table" in result["input_types"]
    assert result["signals"]["n_columns"] == ["n"]


def test_classify_likert_summary_table() -> None:
    df = pd.DataFrame({"scale": ["anxiety", "stress"], "n": [30, 30], "mean": [3.1, 2.8], "sd": [0.7, 0.8]})

    result = classify_table(df)

    assert result["primary_type"] == "likert_or_integer_scale_summary"
    assert "summary_statistics_table" in result["input_types"]


def test_classify_apa_statistical_text() -> None:
    result = classify_text("The result was significant, t(28)=2.20, p<.05.")

    assert result["primary_type"] == "apa_statistical_text"
    assert result["signals"]["apa_statistical_expressions"] is True


def test_classify_reference_text() -> None:
    result = classify_text("References\nSmith J. Important study. doi:10.1234/example.2025. PMID: 12345678")

    assert result["primary_type"] == "reference_list"
    assert "reference_list" in result["input_types"]
    assert result["signals"]["reference_identifiers"] is True


def test_route_reports_insufficient_material() -> None:
    decision = route_tool(
        TOOL_REGISTRY["raw_data_rules"],
        {"raw_data_rules"},
        ["raw_observation_table"],
        row_count=1,
        available_fields=["value"],
    )

    assert decision.status == "insufficient_material"
    assert decision.applicable is False
    assert "至少 2 行" in decision.skip_reason


def test_route_reports_not_applicable() -> None:
    decision = route_tool(
        TOOL_REGISTRY["r_statcheck"],
        {"r_statcheck"},
        ["plain_text"],
        row_count=0,
        available_fields=[],
    )

    assert decision.status == "not_applicable"
    assert decision.applicable is False


def test_route_reports_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)

    decision = route_tool(
        TOOL_REGISTRY["r_scrutiny"],
        {"r_scrutiny"},
        ["summary_statistics_table"],
        row_count=2,
        available_fields=["n", "mean", "sd"],
    )

    assert decision.status == "missing_r_package"
    assert decision.dependency_status == "missing_r_package"
