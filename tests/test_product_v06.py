from __future__ import annotations

import json
from pathlib import Path

from pcr_audit.models import Finding, TableResult, enrich_finding_explanation
from pcr_audit.product.common import normalize_doi
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
    assert any(f.check == "Manifest duplicate material" for f in spec.findings)
    assert any(f.check == "Manifest missing material" for f in spec.findings)
    assert any(f.check == "Manifest material role" for f in spec.findings)
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
        check="High-risk check",
        target="A1",
        summary="Found clear mathematical contradiction.",
        evidence="expected=1, actual=2",
        detail="detail",
        suggestion="Verify original statistical scripts.",
        tool_id="crosscheck",
        location="table1 row 1",
    )
    info = Finding(
        table="route",
        level="info",
        check="Tool Run Record",
        target="r_scrutiny",
        summary="R package missing; skipped.",
        evidence="missing_r_package",
        detail="",
        suggestion="Install R package and retry.",
        tool_id="r_scrutiny",
    )
    enrich_finding_explanation(risk)
    enrich_finding_explanation(info)

    report = render_markdown(tmp_path / "source.csv", [TableResult("demo", 1, 1, [risk, info])], [])

    assert "Executive Summary" in report
    assert "Audit Scope and Interpretation Guide" in report
    assert "Material Inventory" in report
    assert "Tool Run Details" in report
    assert "Coverage Gaps and Skip Reasons" in report
    assert "Manual Review Task List" in report
    assert "Info Records (Not Risk)" in report
    assert "| High |" in report
    assert "R package missing; skipped" in report


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


def test_reference_audit_flags_crossref_author_and_year_mismatch(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "References\n[1] Wrongson A, Helper B. (2024). Cached title. Journal of Correct Science. doi:10.1234/example.2026.",
        encoding="utf-8",
    )

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        if "crossref" in url:
            return {
                "status": "ok",
                "message": {
                    "title": ["Cached title"],
                    "author": [{"family": "Rightsmith"}, {"family": "Verifier"}],
                    "container-title": ["Journal of Correct Science"],
                    "issued": {"date-parts": [[2026, 1, 1]]},
                },
            }
        return {"id": "https://openalex.org/W1", "is_retracted": False}

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    checks = {finding.check: finding for finding in result.findings}
    assert checks["DOI author mismatch"].level == "medium"
    assert checks["DOI publication date mismatch"].level == "medium"
    assert "Rightsmith" in checks["DOI author mismatch"].evidence
    assert "2026" in checks["DOI publication date mismatch"].evidence


def test_reference_audit_flags_crossref_journal_mismatch(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "References\n[1] Rightsmith A. (2026). Cached title. Journal of Wrong Medicine. doi:10.1234/example.2026.",
        encoding="utf-8",
    )

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        if "crossref" in url:
            return {
                "status": "ok",
                "message": {
                    "title": ["Cached title"],
                    "author": [{"family": "Rightsmith"}],
                    "container-title": ["Correct Science"],
                    "issued": {"date-parts": [[2026, 1, 1]]},
                },
            }
        return {"id": "https://openalex.org/W1", "is_retracted": False}

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    journal = next(finding for finding in result.findings if finding.check == "DOI journal mismatch")
    assert journal.level == "medium"
    assert "Correct Science" in journal.evidence


def test_reference_audit_doi_not_found_is_medium(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text("References\n[1] Missing reference title. doi:10.9999/missing.2026.", encoding="utf-8")

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        raise RuntimeError("HTTP Error 404: Not Found")

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    absent = next(finding for finding in result.findings if finding.check == "DOI external metadata absent")
    assert absent.level == "medium"
    assert "fabricated/unverifiable citation" in absent.suggestion


def test_reference_audit_flags_pubpeer_discussion_signal(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text("References\n[1] Example title. doi:10.1234/example.2026.", encoding="utf-8")

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        if "crossref" in url:
            return {"status": "ok", "message": {"title": ["Example title"]}}
        if "openalex" in url:
            return {"id": "https://openalex.org/W1", "is_retracted": False}
        if "pubpeer" in url:
            return {"results": [{"doi": "10.1234/example.2026", "comments_count": 2}]}
        raise AssertionError(url)

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    signal = next(finding for finding in result.findings if finding.check == "Post-publication discussion signal")
    assert signal.level == "medium"
    assert "pubpeer_discussion_count=2" in signal.evidence
    assert list((tmp_path / "cache").glob("pubpeer-*.json"))


def test_reference_audit_pubpeer_search_hit_without_comment_count_is_not_risk(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text("References\n[1] Example title. doi:10.1234/example.2026.", encoding="utf-8")

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        if "crossref" in url:
            return {"status": "ok", "message": {"title": ["Example title"]}}
        if "openalex" in url:
            return {"id": "https://openalex.org/W1", "is_retracted": False}
        if "pubpeer" in url:
            return {"results": [{"doi": "10.1234/example.2026", "title": "Example title"}]}
        raise AssertionError(url)

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    assert not any(finding.check == "Post-publication discussion signal" for finding in result.findings)


def test_reference_audit_external_lookup_limit_controls_doi_and_pmid_queries(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "\n".join(
            [
                "References",
                "[1] First title. doi:10.1234/first.2026. PMID:11111111.",
                "[2] Second title. doi:10.1234/second.2026. PMID:22222222.",
            ]
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        calls.append(url)
        if "crossref" in url:
            return {"status": "ok", "message": {"title": ["First title"]}}
        if "openalex" in url:
            return {"id": "https://openalex.org/W1", "is_retracted": False}
        if "pubpeer" in url:
            return {"results": []}
        return {"result": {"11111111": {"title": "First title"}}}

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    analyze_references(
        source,
        AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache", external_lookup_limit=1),
    )

    assert sum("crossref" in url for url in calls) == 1
    assert sum("openalex" in url for url in calls) == 1
    assert sum("pubpeer" in url for url in calls) == 1
    assert sum("eutils.ncbi.nlm.nih.gov" in url for url in calls) == 1


def test_reference_audit_flags_openalex_reference_network_missing(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "\n".join(
            [
                "Current article DOI: 10.5555/current.2026",
                "References",
                "[1] Included title. doi:10.1234/included.2026.",
                "[2] Missing title. doi:10.1234/missing.2026.",
            ]
        ),
        encoding="utf-8",
    )

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        if "crossref" in url:
            if "included" in url:
                return {"status": "ok", "message": {"title": ["Included title"]}}
            return {"status": "ok", "message": {"title": ["Missing title"]}}
        if "openalex" in url:
            if "current" in url:
                return {
                    "id": "https://openalex.org/Wcurrent",
                    "is_retracted": False,
                    "referenced_works": ["https://openalex.org/Wref1"],
                }
            if "included" in url:
                return {"id": "https://openalex.org/Wref1", "is_retracted": False}
            return {"id": "https://openalex.org/Wref2", "is_retracted": False}
        if "pubpeer" in url:
            return {"results": []}
        raise AssertionError(url)

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    network = [finding for finding in result.findings if finding.check == "OpenAlex reference network missing"]
    assert len(network) == 1
    assert network[0].level == "low"
    assert network[0].target == "10.1234/missing.2026"
    assert "current_doi=10.5555/current.2026" in network[0].evidence


def test_reference_audit_skips_openalex_reference_network_without_current_doi(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "References\n[1] Missing title. doi:10.1234/missing.2026.",
        encoding="utf-8",
    )

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        if "crossref" in url:
            return {"status": "ok", "message": {"title": ["Missing title"]}}
        if "openalex" in url:
            return {"id": "https://openalex.org/Wref2", "is_retracted": False}
        if "pubpeer" in url:
            return {"results": []}
        raise AssertionError(url)

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    assert not any(finding.check == "OpenAlex reference network missing" for finding in result.findings)


def test_reference_audit_normalizes_pdf_glued_dois(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "References\n[1] Example title. doi:10.1002/jbt.22526PMID:32410268; PubMedCentral PMCID.",
        encoding="utf-8",
    )
    seen_urls: list[str] = []

    def fake_http_json(url: str, timeout: float = 8.0, contact_email: str = ""):
        seen_urls.append(url)
        if "crossref" in url:
            return {"status": "ok", "message": {"title": ["Example title"]}}
        return {"id": "https://openalex.org/W1", "is_retracted": False}

    monkeypatch.setattr("pcr_audit.product_detectors._http_json", fake_http_json)
    result = analyze_references(source, AuditConfig(external_lookups=True, lookup_cache_dir=tmp_path / "cache"))

    assert normalize_doi("10.1002/jbt.22526PMID:32410268;PubMedCentralPMCID") == "10.1002/jbt.22526"
    assert any("10.1002%2Fjbt.22526" in url for url in seen_urls)
    assert not any(f.check == "DOI external metadata unverifiable" for f in result.findings)


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
