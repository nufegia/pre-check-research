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
    assert "Data Audit Report" in text
    assert "Audit Scope and Interpretation Guide" in text
    assert "Material Inventory" in text
    assert "Tool Run Details" in text
    assert "Coverage Gaps and Skip Reasons" in text
    assert "Risk Finding List" in text


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
    report = out.read_text(encoding="utf-8")
    assert "Tool Run Details" in report
    assert "Coverage Gaps and Skip Reasons" in report
    assert "r_scrutiny" in report
    assert "missing_r_package" in report


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


def test_audit_auto_reference_text_runs_local_reference_tools(tmp_path: Path) -> None:
    source = tmp_path / "refs.md"
    source.write_text(
        "References\n[1] Smith J. A useful paper. doi:10.1234/example.2026.\n"
        "The method is widely used [1].\n",
        encoding="utf-8",
    )
    out = tmp_path / "refs.md.out"
    merged_json = tmp_path / "refs.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    tool_ids = {finding["tool_id"] for result in payload["results"] for finding in result["findings"]}

    assert "reference_audit" in tool_ids
    assert "citation_claim_check" in tool_ids
    assert "papermill_light_signals" in tool_ids


def test_audit_auto_p_value_collection_runs_detector(tmp_path: Path) -> None:
    source = tmp_path / "p_values.csv"
    values = [0.046, 0.047, 0.048, 0.049, 0.12, 0.2, 0.3, 0.4, 0.5, 0.6, 1.2, 0.8]
    source.write_text("label,p\n" + "\n".join(f"H{idx},{value}" for idx, value in enumerate(values, start=1)), encoding="utf-8")
    out = tmp_path / "p-values.md"
    merged_json = tmp_path / "p-values.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result["findings"]]

    assert any(finding["tool_id"] == "p_value_distribution" and finding["check"] == "P-value domain" for finding in findings)
    assert any(finding["tool_id"] == "p_value_distribution" and finding["check"] == "Marginally significant p-value clustering" for finding in findings)


def test_audit_auto_single_python_code_runs_sandbox(tmp_path: Path) -> None:
    source = tmp_path / "analysis.py"
    source.write_text("print('single file rerun ok')\n", encoding="utf-8")
    out = tmp_path / "code.md"
    merged_json = tmp_path / "code.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result["findings"]]

    assert any(finding["tool_id"] == "code_rerun_audit" for finding in findings)
    assert any(finding["tool_id"] == "code_rerun_execute" and "completed" in finding["summary"] for finding in findings)


def test_audit_auto_unsupported_code_records_info(tmp_path: Path) -> None:
    source = tmp_path / "analysis.do"
    source.write_text("display \"hello\"\n", encoding="utf-8")
    out = tmp_path / "stata.md"
    merged_json = tmp_path / "stata.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(merged_json)]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result["findings"]]

    assert any(
        finding["tool_id"] == "code_rerun_execute"
        and finding["level"] == "info"
        and "unsupported" in finding["check"]
        for finding in findings
    )


def test_audit_project_runs_multimaterial_audit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    project = tmp_path / "project"
    project.mkdir()
    (project / "paper.md").write_text(
        "References\n[1] Smith J. A useful paper. doi:10.1234/example.2026.\n"
        "This claim is supported by prior work [1].\n",
        encoding="utf-8",
    )
    pd.DataFrame({"subject": ["S1", "S2", "S3"], "value": [1.0, 1.2, 1.4]}).to_csv(project / "data.csv", index=False)
    (project / "analysis.py").write_text("import pandas as pd\ndf = pd.read_csv('data.csv').dropna()\n", encoding="utf-8")
    out = tmp_path / "project-report.md"
    merged_json = tmp_path / "project-report.json"

    assert audit_main(["project", str(project), "--out", str(out), "--json", str(merged_json), "--no-external-lookups"]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    tool_ids = {finding["tool_id"] for result in payload["results"] for finding in result["findings"]}

    assert "provenance_hash" in tool_ids
    assert "code_rerun_audit" in tool_ids
    assert "reference_audit" in tool_ids


def test_audit_project_example_and_flags(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    source = ROOT / "examples" / "project_minimal"
    out = tmp_path / "example-project.md"
    merged_json = tmp_path / "example-project.json"
    workdir = tmp_path / "work"

    assert audit_main(
        [
            "project",
            str(source),
            "--out",
            str(out),
            "--json",
            str(merged_json),
            "--workdir",
            str(workdir),
            "--grobid-url",
            "http://localhost:8070",
            "--contact-email",
            "audit@example.org",
            "--no-external-lookups",
        ]
    ) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    route = json.loads((workdir / "project-route.json").read_text(encoding="utf-8"))
    report = out.read_text(encoding="utf-8")
    tool_ids = {finding["tool_id"] for result in payload["results"] for finding in result["findings"]}

    assert route["project_id"] == "project-minimal"
    assert route["policy"]["grobid_url"] == "http://localhost:8070"
    assert route["policy"]["contact_email"] == "audit@example.org"
    assert "Audit Scope and Interpretation Guide" in report
    assert "Material Inventory" in report
    assert "Tool Run Details" in report
    assert "Coverage Gaps and Skip Reasons" in report
    assert "Manual Review Task List" in report
    assert "paper.md" in report
    assert "data.csv" in report
    assert "reference_audit" in tool_ids
    assert "provenance_hash" in tool_ids


def test_project_inspect_without_running_detectors(tmp_path: Path) -> None:
    source = ROOT / "examples" / "project_minimal"
    inspect_json = tmp_path / "inspect.json"

    assert audit_main(["project", str(source), "--inspect", "--json", str(inspect_json)]) == 0
    payload = json.loads(inspect_json.read_text(encoding="utf-8"))

    assert payload["project_id"] == "project-minimal"
    assert payload["role_counts"]["manuscript"] == 1
    assert payload["role_counts"]["raw_data"] == 1
    assert payload["missing_core_roles"] == []


def test_project_init_manifest(tmp_path: Path) -> None:
    project = tmp_path / "new_project"
    project.mkdir()
    (project / "paper.md").write_text("References\n", encoding="utf-8")
    (project / "data.csv").write_text("id,value\n1,2\n", encoding="utf-8")
    out_json = tmp_path / "init.json"

    assert audit_main(["project", str(project), "--init-manifest", "--json", str(out_json)]) == 0
    manifest = project / "pcr-project.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert manifest.exists()
    assert any(item["role"] == "manuscript" for item in payload["materials"])
    assert any(item["role"] == "raw_data" for item in payload["materials"])


def test_project_sample_reports_are_stable_enough_for_golden_checks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    samples = ["project_minimal", "project_questionnaire", "project_biomed"]
    for sample in samples:
        source = ROOT / "examples" / sample
        out = tmp_path / f"{sample}.md"
        merged_json = tmp_path / f"{sample}.json"
        assert audit_main(["project", str(source), "--out", str(out), "--json", str(merged_json), "--no-external-lookups"]) == 0
        report = out.read_text(encoding="utf-8")
        payload = json.loads(merged_json.read_text(encoding="utf-8"))
        tool_ids = {finding["tool_id"] for result in payload["results"] for finding in result["findings"]}

        assert "Executive Summary" in report
        assert "Audit Scope and Interpretation Guide" in report
        assert "Material Inventory" in report
        assert "Material Coverage Matrix" in report
        assert "Tool Run Details" in report
        assert "Coverage Gaps and Skip Reasons" in report
        assert "Manual Review Task List" in report
        assert "reference_audit" in tool_ids
        assert "provenance_hash" in tool_ids
        if sample == "project_biomed":
            assert "image_extract" in tool_ids
            assert "image_metadata_audit" in tool_ids


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
