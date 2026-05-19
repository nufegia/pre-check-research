from __future__ import annotations

import json
from pathlib import Path

from pcr_audit.models import Finding, TableResult, enrich_finding_explanation
from pcr_audit.product_detectors import AuditConfig, analyze_references, init_manifest_payload, parse_project_spec
from pcr_audit.reporting import render_markdown


def test_manifest_v1_parses_roles_and_records_warnings(tmp_path: Path) -> None:
    (tmp_path / "paper.md").write_text("References\n[1] doi:10.1234/example.2026", encoding="utf-8")
    (tmp_path / "data.csv").write_text("id,value\n1,2\n", encoding="utf-8")
    manifest = tmp_path / "pcr-project.json"
    manifest.write_text(
        json.dumps(
            {
                "project_id": "demo",
                "title": "Demo",
                "materials": [
                    {"path": "paper.md", "role": "manuscript"},
                    {"path": "data.csv", "role": "raw_data"},
                    {"path": "data.csv", "role": "raw_data"},
                    {"path": "missing.csv", "role": "raw_data"},
                    {"path": "paper.md", "role": "strange_role"},
                ],
                "settings": {"external_lookups": False},
            }
        ),
        encoding="utf-8",
    )

    spec, config = parse_project_spec(manifest, workdir=tmp_path / "work")

    assert spec.project_id == "demo"
    assert any(material.role == "manuscript" for material in spec.materials)
    assert any(f.check == "Manifest重复材料" for f in spec.findings)
    assert any(f.check == "Manifest材料缺失" for f in spec.findings)
    assert any(f.check == "Manifest材料角色" for f in spec.findings)
    assert config.external_lookups is False


def test_project_directory_ignores_hidden_and_system_files(tmp_path: Path) -> None:
    (tmp_path / "paper.md").write_text("References\n[1] doi:10.1234/example.2026", encoding="utf-8")
    (tmp_path / "data.csv").write_text("id,value\n1,2\n", encoding="utf-8")
    (tmp_path / ".DS_Store").write_text("system metadata", encoding="utf-8")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.csv").write_text("id,value\n1,9\n", encoding="utf-8")

    spec, _config = parse_project_spec(tmp_path, workdir=tmp_path / "work")
    paths = {material.path.name for material in spec.materials}

    assert "paper.md" in paths
    assert "data.csv" in paths
    assert ".DS_Store" not in paths
    assert "secret.csv" not in paths


def test_init_manifest_ignores_hidden_and_system_files(tmp_path: Path) -> None:
    (tmp_path / "paper.md").write_text("References\n", encoding="utf-8")
    (tmp_path / "data.csv").write_text("id,value\n1,2\n", encoding="utf-8")
    (tmp_path / ".DS_Store").write_text("system metadata", encoding="utf-8")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "extra.csv").write_text("id,value\n1,9\n", encoding="utf-8")

    init_manifest_payload(tmp_path)
    payload = json.loads((tmp_path / "pcr-project.json").read_text(encoding="utf-8"))
    material_paths = {item["path"] for item in payload["materials"]}

    assert "paper.md" in material_paths
    assert "data.csv" in material_paths
    assert ".DS_Store" not in material_paths
    assert ".hidden/extra.csv" not in material_paths


def test_report_separates_info_from_risk_findings(tmp_path: Path) -> None:
    risk = Finding(
        table="table1",
        level="high",
        check="高风险检查",
        target="A1",
        summary="发现明确数学矛盾。",
        evidence="expected=1, actual=2",
        detail="detail",
        suggestion="核对原始统计脚本。",
        tool_id="crosscheck",
        location="table1 row 1",
    )
    info = Finding(
        table="route",
        level="info",
        check="工具运行记录",
        target="r_scrutiny",
        summary="R 包缺失，已跳过。",
        evidence="missing_r_package",
        detail="",
        suggestion="安装 R 包后重试。",
        tool_id="r_scrutiny",
    )
    enrich_finding_explanation(risk)
    enrich_finding_explanation(info)

    report = render_markdown(tmp_path / "source.csv", [TableResult("demo", 1, 1, [risk, info])], [])

    assert "导师摘要" in report
    assert "作者整改清单" in report
    assert "运行提示（不计入风险）" in report
    assert "| 高 |" in report
    assert "R 包缺失，已跳过" in report


def test_external_lookup_cache_records_metadata(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text("References\n[1] Example. doi:10.1234/example.2026.", encoding="utf-8")

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        if "crossref" in url:
            return {"status": "ok", "message": {"title": ["Cached title"]}}
        return {"id": "https://openalex.org/W1", "is_retracted": False}

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    config = AuditConfig(external_lookups=True, contact_email="audit@example.org", lookup_cache_dir=tmp_path / "cache")

    first = analyze_references(source, config)
    second = analyze_references(source, config)

    assert any("cache_miss" in finding.evidence for finding in first.findings)
    assert any("cache_hit" in finding.evidence for finding in second.findings)
    assert list((tmp_path / "cache").glob("crossref-*.json"))
    assert list((tmp_path / "cache").glob("openalex-*.json"))


def test_grobid_success_and_fallback(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-1.4 fake")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"<TEI><text><body><p>GROBID extracted doi:10.1234/example.2026.</p></body></text></TEI>"

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse())
    result = analyze_references(source, AuditConfig(grobid_url="http://localhost:8070"))

    assert any(f.tool_id == "grobid_extract" and f.dependency_status == "ready" for f in result.findings)
    assert any(f.tool_id == "reference_audit" for f in result.findings)

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("down")))
    result = analyze_references(source, AuditConfig(grobid_url="http://localhost:8070"))

    assert any(f.tool_id == "grobid_extract" and f.dependency_status == "grobid_unavailable" for f in result.findings)
