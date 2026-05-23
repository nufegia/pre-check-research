from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcr_audit.cli import audit_main
from pcr_audit.product_detectors import (
    analyze_images,
    analyze_papermill_network_signals,
    build_corpus_index,
    provenance_diff,
    provenance_record,
    provenance_verify,
)
from pcr_audit.product.image_audit import _is_page_sized_pdf_image
from pcr_audit.router import build_route_payload


def _write_demo_image(path: Path, duplicate_patch: bool = False) -> None:
    Image = pytest.importorskip("PIL.Image")
    ImageDraw = pytest.importorskip("PIL.ImageDraw")
    image = Image.new("RGB", (180, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 80, 70), fill="black")
    draw.ellipse((100, 30, 150, 80), fill="gray")
    if duplicate_patch:
        patch = image.crop((15, 15, 90, 80))
        image.paste(patch, (95, 35))
    image.save(path)


def test_image_enhancement_detects_duplicate_and_metadata(tmp_path: Path) -> None:
    left = tmp_path / "figure_a.png"
    right = tmp_path / "figure_b.png"
    _write_demo_image(left)
    _write_demo_image(right)

    results = analyze_images(tmp_path, tmp_path / "work")
    findings = [finding for result in results for finding in result.findings]

    assert any(finding.tool_id == "image_duplicate_internal" and finding.level == "medium" for finding in findings)
    assert any(finding.tool_id == "image_metadata_audit" for finding in findings)


def test_image_copy_move_detects_local_patch_when_cv2_available(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    image = tmp_path / "copy_move.png"
    _write_demo_image(image, duplicate_patch=True)

    results = analyze_images(image, tmp_path / "work")
    findings = [finding for result in results for finding in result.findings]

    assert any(finding.tool_id == "image_copy_move_internal" for finding in findings)


def test_pdf_image_extraction_flows_into_image_audit(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    image = tmp_path / "extracted.png"
    _write_demo_image(image)

    monkeypatch.setattr("pcr_audit.product_detectors.extract_pdf_images", lambda _source, _workdir: ([image], ""))
    results = analyze_images(pdf, tmp_path / "work")
    findings = [finding for result in results for finding in result.findings]

    assert any(finding.tool_id == "image_extract" and "found" in finding.summary.lower() for finding in findings)
    assert any(finding.tool_id == "image_metadata_audit" for finding in findings)


def test_pdf_page_sized_images_are_not_valid_audit_units() -> None:
    class Page:
        width = 600
        height = 800

    assert _is_page_sized_pdf_image(Page(), (0, 0, 600, 800))
    assert _is_page_sized_pdf_image(Page(), (10, 12, 592, 784))
    assert not _is_page_sized_pdf_image(Page(), (100, 120, 420, 460))


def test_provenance_jsonl_record_verify_and_diff(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    data = project / "data.csv"
    data.write_text("id,value\n1,2\n", encoding="utf-8")
    ledger = project / ".pcr" / "provenance-ledger.jsonl"

    first = provenance_record(project, ledger, operator="tester")
    verify_first = provenance_verify(project, ledger)
    data.write_text("id,value\n1,3\n", encoding="utf-8")
    verify_changed = provenance_verify(project, ledger)
    second = provenance_record(project, ledger, operator="tester")
    diff = provenance_diff(project, ledger, first["batch_id"], second["batch_id"])

    assert ledger.exists()
    assert any(item["status"] == "matched" for item in verify_first["statuses"])
    assert any(item["status"] == "changed" for item in verify_changed["statuses"])
    assert any(item["status"] == "modified" for item in diff["changes"])


def test_local_corpus_screen_flags_similar_projects(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    project_a = corpus / "project_a"
    project_b = corpus / "project_b"
    project_a.mkdir(parents=True)
    project_b.mkdir(parents=True)
    text = (
        "Authors: Alice Zhang, Bob Li\n"
        "Affiliations: Example Hospital\n"
        "This retrospective study used a standardized method and identical inclusion criteria. "
        "The outcome was assessed with the same imaging workflow and statistical model.\n"
        "References\n"
        "[1] doi:10.1111/example.1\n[2] doi:10.1111/example.2\n[3] doi:10.1111/example.3\n"
    )
    (project_a / "paper.md").write_text(text, encoding="utf-8")
    (project_b / "paper.md").write_text(text.replace("Alice Zhang", "Alice Zhang"), encoding="utf-8")

    index = build_corpus_index(corpus)
    result = analyze_papermill_network_signals(project_a, index)

    assert any(finding.tool_id == "papermill_network_signals" and finding.level in {"low", "medium"} for finding in result.findings)


def test_route_selects_stage2_stage3_tools_for_project_and_image(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "paper.md").write_text("References\n", encoding="utf-8")
    image = tmp_path / "figure.png"
    _write_demo_image(image)

    project_route = build_route_payload(project)
    image_route = build_route_payload(image)

    project_tools = project_route["project"]["routing_decisions"]
    image_tools = image_route["image"]["routing_decisions"]
    assert project_tools["papermill_network_signals"]["selected_by_user"] is True
    assert project_tools["provenance_chain_verify"]["selected_by_user"] is True
    assert project_tools["data_trace_crosscheck"]["selected_by_user"] is True
    assert project_tools["code_rerun_execute"]["selected_by_user"] is True
    assert project_tools["reference_audit"]["selected_by_user"] is False
    assert "delegated_material_tools" in project_route["project"]
    assert "reference_audit" in project_route["project"]["delegated_material_tools"]["documents"]
    assert "image_duplicate_internal" in project_route["project"]["delegated_material_tools"]["images"]
    assert image_tools["image_copy_move_internal"]["selected_by_user"] is True
    assert image_tools["image_metadata_audit"]["selected_by_user"] is True


def test_auto_route_selects_raw_rules_for_raw_data(tmp_path: Path) -> None:
    source = tmp_path / "raw.csv"
    source.write_text("id,value\n" + "\n".join(f"{idx},{idx * 1.1}" for idx in range(40)), encoding="utf-8")

    route = build_route_payload(source)
    decisions = route["tables"][0]["routing_decisions"]

    assert decisions["raw_data_rules"]["selected_by_user"] is True


def test_auto_route_selects_p_value_collection_detector(tmp_path: Path) -> None:
    source = tmp_path / "p_values.csv"
    source.write_text("test,p\n" + "\n".join(f"T{idx},0.0{idx % 9 + 1}" for idx in range(12)), encoding="utf-8")

    route = build_route_payload(source)
    table = route["tables"][0]
    decisions = table["routing_decisions"]

    assert table["classification"]["primary_type"] == "p_value_collection"
    assert decisions["p_value_distribution"]["selected_by_user"] is True
    assert decisions["p_value_distribution"]["status"] == "ready"


def test_new_cli_commands_generate_json_and_reports(tmp_path: Path) -> None:
    project = tmp_path / "project"
    corpus = tmp_path / "corpus"
    project.mkdir()
    corpus.mkdir()
    (project / "paper.md").write_text("Authors: A, B\nReferences\ndoi:10.1111/example.1\n", encoding="utf-8")
    (corpus / "p1").mkdir()
    (corpus / "p1" / "paper.md").write_text("Authors: A, B\nReferences\ndoi:10.1111/example.1\n", encoding="utf-8")
    ledger_json = tmp_path / "record.json"
    index_json = tmp_path / "corpus-index.json"
    screen_md = tmp_path / "screen.md"
    screen_json = tmp_path / "screen.json"

    assert audit_main(["provenance", "record", str(project), "--json", str(ledger_json)]) == 0
    assert audit_main(["corpus", "build", str(corpus), "--out", str(index_json)]) == 0
    assert audit_main(["corpus", "screen", str(project), "--index", str(index_json), "--out", str(screen_md), "--json", str(screen_json)]) == 0

    assert json.loads(ledger_json.read_text(encoding="utf-8"))["records"]
    assert json.loads(index_json.read_text(encoding="utf-8"))["projects"]
    assert screen_md.exists()
    assert json.loads(screen_json.read_text(encoding="utf-8"))["results"]


def test_project_data_trace_and_code_sandbox_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    project = tmp_path / "project"
    project.mkdir()
    pd = pytest.importorskip("pandas")
    pd.DataFrame({"variable": ["value"], "n": [4], "mean": [99.0], "sd": [1.0]}).to_excel(project / "paper_tables.xlsx", index=False)
    pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0]}).to_csv(project / "data.csv", index=False)
    (project / "analysis.py").write_text(
        "import pandas as pd\n"
        "df = pd.read_csv('data.csv')\n"
        "pd.DataFrame({'variable':['value'], 'n':[len(df)], 'mean':[df.value.mean()], 'sd':[df.value.std()]}).to_csv('script_summary.csv', index=False)\n",
        encoding="utf-8",
    )
    manifest = project / "pcr-project.json"
    manifest.write_text(
        json.dumps(
            {
                "project_id": "trace-demo",
                "materials": [
                    {"path": "paper_tables.xlsx", "role": "supplement"},
                    {"path": "data.csv", "role": "raw_data"},
                    {"path": "analysis.py", "role": "analysis_code"},
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "trace.md"
    merged_json = tmp_path / "trace.json"

    assert audit_main(["project", str(project), "--out", str(out), "--json", str(merged_json), "--no-external-lookups"]) == 0
    payload = json.loads(merged_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result["findings"]]

    assert any(finding["tool_id"] == "code_rerun_execute" and "completed" in finding["summary"] for finding in findings)
    assert any(finding["tool_id"] == "data_trace_crosscheck" and finding["level"] == "high" for finding in findings)


def test_project_default_external_lookup_can_be_disabled(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        calls.append(url)
        return {"status": "ok", "message": {"title": ["Demo"]}} if "crossref" in url else {"id": "W1", "is_retracted": False}

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    project = tmp_path / "project"
    project.mkdir()
    (project / "paper.md").write_text("References\ndoi:10.1234/example.2026\n", encoding="utf-8")
    out = tmp_path / "external.md"
    merged_json = tmp_path / "external.json"

    assert audit_main(["project", str(project), "--out", str(out), "--json", str(merged_json), "--no-rerun-code"]) == 0
    assert calls
    calls.clear()
    assert audit_main(["project", str(project), "--out", str(out), "--json", str(merged_json), "--no-rerun-code", "--no-external-lookups"]) == 0
    assert calls == []
