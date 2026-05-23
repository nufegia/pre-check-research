from __future__ import annotations

import json
from pathlib import Path

from pcr_audit.models import Finding, TableResult, enrich_finding_explanation
from pcr_audit.reporting import (
    markdown_cell,
    merge_reports,
    overall_level,
    render_markdown,
    results_from_payload,
    save_json,
)


def make_finding(level="medium", check="test_check", target="test_target", summary="A test finding.", evidence="n=100", suggestion="Review the data."):
    f = Finding(
        table="test_table",
        level=level,
        check=check,
        target=target,
        summary=summary,
        evidence=evidence,
        detail="Some detail.",
        suggestion=suggestion,
        tool_id="test_tool",
        tool_name="Test Tool",
        module="test_module",
        input_type="test_input",
    )
    enrich_finding_explanation(f)
    return f


class TestOverallLevel:
    def test_no_risk_findings_returns_low(self):
        findings = [make_finding("info")]
        assert overall_level(findings) == "low"

    def test_high_dominates_medium(self):
        findings = [make_finding("medium"), make_finding("high")]
        assert overall_level(findings) == "high"

    def test_medium_over_low(self):
        findings = [make_finding("low"), make_finding("medium")]
        assert overall_level(findings) == "medium"

    def test_empty_list_returns_low(self):
        assert overall_level([]) == "low"


class TestMarkdownCell:
    def test_escapes_pipe(self):
        assert markdown_cell("a|b") == "a\\|b"

    def test_replaces_newline_with_br(self):
        assert markdown_cell("line1\nline2") == "line1<br>line2"

    def test_preserves_plain_text(self):
        assert markdown_cell("hello world") == "hello world"


class TestRenderMarkdown:
    def test_renders_basic_report_with_findings(self, tmp_path: Path):
        source = Path("test.csv")
        results = [TableResult("sheet1", 100, 5, [make_finding("high")])]
        output = render_markdown(source, results, [])
        assert "# Data Audit Report" in output
        assert "Overall risk: High" in output
        assert "sheet1" in output
        assert "test_check" in output

    def test_renders_report_with_no_findings(self):
        source = Path("test.csv")
        results = [TableResult("sheet1", 10, 3, [])]
        output = render_markdown(source, results, [])
        assert "No obvious anomalous patterns" in output.lower() or "no risk findings" in output.lower()

    def test_includes_extraction_notes(self):
        source = Path("test.pdf")
        results = [TableResult("sheet1", 10, 3, [make_finding("low")])]
        output = render_markdown(source, results, ["Note: extracted from PDF."])
        assert "Note: extracted from PDF." in output

    def test_renders_multiple_results(self):
        source = Path("test.csv")
        results = [
            TableResult("sheet1", 50, 4, [make_finding("high", "check_a")]),
            TableResult("sheet2", 30, 3, [make_finding("medium", "check_b")]),
        ]
        output = render_markdown(source, results, [])
        assert "sheet1" in output
        assert "sheet2" in output
        assert "check_a" in output
        assert "check_b" in output

    def test_includes_material_coverage_matrix(self):
        source = Path("test.csv")
        results = [TableResult("sheet1", 100, 5, [make_finding("high")])]
        output = render_markdown(source, results, [])
        assert "Material Coverage Matrix" in output

    def test_includes_expert_review_appendix(self):
        source = Path("test.csv")
        results = [TableResult("sheet1", 100, 5, [make_finding("high")])]
        output = render_markdown(source, results, [])
        assert "Expert Review Appendix" in output

    def test_includes_audit_confidence_summary(self):
        source = Path("test.csv")
        results = [TableResult("sheet1", 100, 5, [make_finding("high")])]
        output = render_markdown(source, results, [])
        assert "Audit Confidence Summary" in output

    def test_info_only_results_no_risk(self):
        source = Path("test.csv")
        results = [TableResult("sheet1", 10, 3, [make_finding("info")])]
        output = render_markdown(source, results, [])
        assert "No obvious anomalous patterns" in output.lower() or "no risk findings" in output.lower()


class TestSaveAndLoadJSON:
    def test_save_and_read_roundtrip(self, tmp_path: Path):
        source = Path("test.csv")
        results = [TableResult("sheet1", 50, 5, [make_finding("medium")])]
        json_path = tmp_path / "test.json"
        save_json(json_path, source, results)
        assert json_path.exists()

        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        assert loaded["source"] == str(source)
        assert len(loaded["results"]) == 1
        assert loaded["results"][0]["name"] == "sheet1"

    def test_results_from_payload(self):
        payload = {
            "source": "test.csv",
            "results": [
                {
                    "name": "sheet1",
                    "rows": 100,
                    "columns": 5,
                    "findings": [
                        {
                            "level": "high",
                            "check": "test",
                            "target": "col1",
                            "summary": "Found issue.",
                            "evidence": "n=100",
                            "detail": "",
                            "suggestion": "Review.",
                        }
                    ],
                }
            ],
        }
        results = results_from_payload(payload)
        assert len(results) == 1
        assert results[0].name == "sheet1"
        assert results[0].rows == 100
        assert results[0].columns == 5
        assert len(results[0].findings) == 1
        assert results[0].findings[0].level == "high"

    def test_results_from_legacy_payload(self):
        payload = {
            "source": "legacy.json",
            "findings": [
                {
                    "level": "medium",
                    "check": "old_check",
                    "target": "",
                    "summary": "Old finding.",
                    "evidence": "",
                    "detail": "",
                    "suggestion": "",
                }
            ],
        }
        results = results_from_payload(payload)
        assert len(results) == 1
        assert results[0].name == "legacy.json"


class TestMergeReports:
    def test_merge_creates_output(self, tmp_path: Path):
        json1 = tmp_path / "part1.json"
        json2 = tmp_path / "part2.json"
        source = Path("test.csv")
        results1 = [TableResult("sheet1", 10, 3, [make_finding("high", "check_1")])]
        results2 = [TableResult("sheet2", 20, 4, [make_finding("medium", "check_2")])]
        save_json(json1, source, results1)
        save_json(json2, source, results2)

        out_path = tmp_path / "merged.md"
        json_out = tmp_path / "merged.json"
        merge_reports([str(json1), str(json2)], out_path, json_out)

        assert out_path.exists()
        assert json_out.exists()
        content = out_path.read_text(encoding="utf-8")
        assert "check_1" in content
        assert "check_2" in content
