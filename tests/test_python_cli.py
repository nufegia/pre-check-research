from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pcr_audit.cli import audit_main, extract_main, raw_audit_main, report_main


ROOT = Path(__file__).resolve().parents[1]


def test_raw_audit_generates_markdown_and_json(tmp_path: Path) -> None:
    source = ROOT / "examples" / "suspicious_sample.csv"
    report = tmp_path / "raw.md"
    findings = tmp_path / "raw.json"

    assert raw_audit_main([str(source), "--out", str(report), "--json", str(findings)]) == 0
    payload = json.loads(findings.read_text(encoding="utf-8"))

    assert report.exists()
    assert payload["source"] == str(source.resolve())
    assert payload["results"]
    assert "findings" in payload["results"][0]


def test_extract_xlsx_writes_manifest_and_csv(tmp_path: Path) -> None:
    source = ROOT / "examples" / "suspicious_sample.xlsx"
    out_dir = tmp_path / "extracted"
    manifest = tmp_path / "extracted.json"

    assert extract_main([str(source), "--out", str(out_dir), "--json", str(manifest)]) == 0
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert payload["tool_id"] == "pcr_extract"
    assert payload["outputs"]
    assert Path(payload["outputs"][0]["path"]).exists()


def test_report_merge_combines_payloads(tmp_path: Path) -> None:
    source = ROOT / "examples" / "suspicious_sample.csv"
    raw_report = tmp_path / "raw.md"
    raw_json = tmp_path / "raw.json"
    merged = tmp_path / "merged.md"

    assert raw_audit_main([str(source), "--out", str(raw_report), "--json", str(raw_json)]) == 0
    assert report_main(["merge", str(raw_json), "--out", str(merged)]) == 0

    text = merged.read_text(encoding="utf-8")
    assert "数据审计报告" in text
    assert "问题清单" in text


def test_audit_route_outputs_deterministic_json(tmp_path: Path) -> None:
    source = ROOT / "examples" / "summary_stat_sample.csv"
    route_json = tmp_path / "route.json"

    assert audit_main(["route", str(source), "--json", str(route_json)]) == 0
    payload = json.loads(route_json.read_text(encoding="utf-8"))

    assert payload["source"] == str(source.resolve())
    assert payload["tables"]
    table = payload["tables"][0]
    assert table["classification"]["primary_type"] == "summary_statistics_table"
    assert "routing_decisions" in table
    assert table["routing_decisions"]["crosscheck"]["selected_by_user"] is True


def test_audit_auto_raw_runs_raw_rules_only(tmp_path: Path) -> None:
    source = ROOT / "examples" / "suspicious_sample.csv"
    out = tmp_path / "auto-raw.md"
    merged_json = tmp_path / "auto-raw.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    tool_ids = {finding["tool_id"] for result in payload["results"] for finding in result["findings"]}

    assert "raw_data_rules" in tool_ids
    assert "crosscheck" not in tool_ids
    assert "r_scrutiny" not in tool_ids


def test_audit_auto_summary_runs_crosscheck_and_records_missing_r_package(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    source = ROOT / "examples" / "summary_stat_sample.csv"
    out = tmp_path / "auto-summary.md"
    merged_json = tmp_path / "auto-summary.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result["findings"]]
    tool_ids = {finding["tool_id"] for finding in findings}
    r_infos = [finding for finding in findings if finding["tool_id"] == "r_scrutiny"]

    assert "crosscheck" in tool_ids
    assert r_infos
    assert all(finding["level"] == "info" for finding in r_infos)
    assert all(finding["dependency_status"] == "missing_r_package" for finding in r_infos)


def test_audit_auto_text_routes_statcheck_or_info(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    source = tmp_path / "stats.txt"
    source.write_text("A result was reported as t(28)=2.20, p<.05.", encoding="utf-8")
    out = tmp_path / "auto-text.md"
    merged_json = tmp_path / "auto-text.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result["findings"]]

    assert any(finding["tool_id"] == "r_statcheck" for finding in findings)
    assert all(finding["level"] == "info" for finding in findings if finding["tool_id"] == "r_statcheck")


def test_audit_run_dry_run_writes_route_json(tmp_path: Path) -> None:
    source = ROOT / "examples" / "summary_stat_sample.csv"
    out = tmp_path / "dry.md"
    route_json = tmp_path / "dry-route.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(route_json), "--dry-run"]) == 0
    payload = json.loads(route_json.read_text(encoding="utf-8"))

    assert not out.exists()
    assert payload["tables"][0]["classification"]["input_types"]
    assert "routing_decisions" in payload["tables"][0]


def test_audit_auto_multisheet_runs_only_route_ready_tables(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    source = tmp_path / "mixed.xlsx"
    with pd.ExcelWriter(source) as writer:
        pd.DataFrame({"subject": ["S1", "S1", "S3"], "value": [1.1, 1.1, 1.3]}).to_excel(
            writer, sheet_name="raw_sheet", index=False
        )
        pd.DataFrame({"group": ["A", "B"], "n": [25, 20], "mean": [10.0, 12.0], "sd": [2.0, 3.0]}).to_excel(
            writer, sheet_name="summary_sheet", index=False
        )
    out = tmp_path / "mixed.md"
    merged_json = tmp_path / "mixed.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    result_names = [result["name"] for result in payload["results"]]
    tool_tables = [
        (finding["tool_id"], result["name"])
        for result in payload["results"]
        for finding in result["findings"]
    ]

    assert "raw_sheet" in result_names
    assert not any(tool_id == "raw_data_rules" and table == "summary_sheet" for tool_id, table in tool_tables)
    assert any(tool_id == "crosscheck" and table == "summary_sheet" for tool_id, table in tool_tables)
    assert not any(tool_id == "crosscheck" and table == "raw_sheet" for tool_id, table in tool_tables)
