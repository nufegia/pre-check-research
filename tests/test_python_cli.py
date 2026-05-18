from __future__ import annotations

import json
from pathlib import Path

from pcr_audit.cli import extract_main, raw_audit_main, report_main


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
    assert "数据造假痕迹检查 MVP 报告" in text
    assert "问题清单" in text
