from __future__ import annotations

import json
from pathlib import Path

from pcr_audit.cli import report_main
from pcr_audit.public_report import lint_text, public_payload_from_audit


def test_public_payload_filters_status_records_and_sanitizes_paths(tmp_path: Path) -> None:
    source = tmp_path / "private" / "paper.pdf"
    payload = {
        "source": str(source),
        "results": [
            {
                "name": "reference_audit",
                "rows": 0,
                "columns": 0,
                "findings": [
                    {
                        "level": "info",
                        "check": "DOI metadata verification",
                        "summary": "Attempted lookup.",
                        "evidence": f"cache={tmp_path}/cache",
                        "tool_id": "reference_audit",
                        "location": str(source),
                    },
                    {
                        "level": "medium",
                        "check": "DOI title mismatch",
                        "target": "10.1234/example.2026",
                        "summary": "Title mismatch.",
                        "evidence": f"reported_line={source}; manual review needed",
                        "method_limitations": "This result only flags risk signals that need human review.",
                        "tool_id": "reference_audit",
                        "location": str(source),
                    },
                ],
            }
        ],
    }

    public = public_payload_from_audit(payload)

    assert public["profile"] == "public"
    assert public["source"] == f"/{source.name}"
    assert public["finding_counts"] == {"high": 0, "medium": 1, "low": 0}
    assert len(public["findings"]) == 1
    assert public["findings"][0]["location"] == f"/{source.name}"
    public_text = json.dumps(public, ensure_ascii=False)
    assert "/Users/" not in public_text
    assert "manual review" not in public_text.lower()
    assert "human review" not in public_text.lower()
    assert "method_limitations" not in public_text


def test_public_validate_flags_shareable_output_blockers() -> None:
    text = "| a | " + ("x" * 170) + " |\nLocation: /Users/me/private/paper.pdf\nInfo records: 3\n"
    issue_ids = {issue["id"] for issue in lint_text(text)}

    assert "local_absolute_path" in issue_ids
    assert "info_record_count" in issue_ids
    assert "long_markdown_table_cell" in issue_ids


def test_report_export_and_validate_commands(tmp_path: Path) -> None:
    audit_json = tmp_path / "audit.json"
    public_json = tmp_path / "public.json"
    report_md = tmp_path / "report.md"
    audit_json.write_text(
        json.dumps(
            {
                "source": str(tmp_path / "paper.pdf"),
                "results": [
                    {
                        "name": "paper",
                        "rows": 0,
                        "columns": 0,
                        "findings": [
                            {
                                "level": "low",
                                "check": "Image metadata and quality",
                                "target": "p1_img1",
                                "summary": "Low resolution.",
                                "evidence": "size=18x24",
                                "tool_id": "image_metadata_audit",
                                "location": str(tmp_path / "paper.pdf"),
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert report_main(["export", str(audit_json), "--profile", "public", "--out", str(public_json)]) == 0
    public = json.loads(public_json.read_text(encoding="utf-8"))
    assert public["finding_counts"]["low"] == 1
    assert str(tmp_path) not in json.dumps(public, ensure_ascii=False)

    report_md.write_text("# Shareable Report\n\nNo local paths.\n", encoding="utf-8")
    assert report_main(["validate", str(report_md), "--profile", "public"]) == 0
