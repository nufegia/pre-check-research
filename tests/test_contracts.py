from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from pcr_audit.adapters import AuditRunContext, adapter_for, registered_tool_ids
from pcr_audit.adapter_runtime import PYTHON_ADAPTER_ORDER, R_ADAPTER_ORDER
from pcr_audit.adapter_runtime.product import IMAGE_TOOL_IDS, product_adapter
from pcr_audit.cli import audit_main, raw_audit_main, report_main
from pcr_audit.models import TableResult


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "tools" / "common" / "schemas" / "finding.schema.json").read_text(encoding="utf-8"))


def _required_finding_fields() -> set[str]:
    return set(SCHEMA["properties"]["findings"]["items"]["required"])


def _validate_finding_items(payload: dict[str, Any]) -> None:
    required = _required_finding_fields()
    level_enum = set(SCHEMA["properties"]["findings"]["items"]["properties"]["level"]["enum"])
    if "results" in payload:
        finding_groups = [result.get("findings", []) for result in payload["results"]]
    else:
        for field in SCHEMA["required"]:
            assert field in payload
        finding_groups = [payload.get("findings", [])]
    for findings in finding_groups:
        for finding in findings:
            assert required.issubset(finding), sorted(required - set(finding))
            assert finding["level"] in level_enum
            assert finding["dependency_status"]


def test_cli_json_contracts_for_core_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    source = ROOT / "examples" / "summary_stat_sample.csv"
    raw_source = ROOT / "examples" / "suspicious_sample.csv"
    raw_json = tmp_path / "raw.json"
    raw_md = tmp_path / "raw.md"
    run_json = tmp_path / "run.json"
    run_md = tmp_path / "run.md"
    merged_json = tmp_path / "merged.json"
    merged_md = tmp_path / "merged.md"

    assert raw_audit_main([str(raw_source), "--out", str(raw_md), "--json", str(raw_json)]) == 0
    assert audit_main(["run", str(source), "--out", str(run_md), "--json", str(run_json)]) == 0
    assert report_main(["merge", str(raw_json), str(run_json), "--out", str(merged_md), "--json", str(merged_json)]) == 0

    for path in (raw_json, run_json, merged_json):
        _validate_finding_items(json.loads(path.read_text(encoding="utf-8")))


def test_project_provenance_and_corpus_contracts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)
    project = tmp_path / "project"
    corpus = tmp_path / "corpus"
    project.mkdir()
    corpus.mkdir()
    (project / "paper.md").write_text("Authors: A, B\nReferences\ndoi:10.1111/example.1\n", encoding="utf-8")
    pd.DataFrame({"subject": ["S1", "S2"], "value": [1.0, 2.0]}).to_csv(project / "data.csv", index=False)
    (corpus / "p1").mkdir()
    (corpus / "p1" / "paper.md").write_text("Authors: A, B\nReferences\ndoi:10.1111/example.1\n", encoding="utf-8")

    project_json = tmp_path / "project.json"
    project_md = tmp_path / "project.md"
    provenance_json = tmp_path / "provenance.json"
    index_json = tmp_path / "corpus-index.json"
    screen_json = tmp_path / "screen.json"
    screen_md = tmp_path / "screen.md"

    assert audit_main(["project", str(project), "--out", str(project_md), "--json", str(project_json), "--no-external-lookups"]) == 0
    assert audit_main(["provenance", "verify", str(project), "--json", str(provenance_json)]) == 0
    assert audit_main(["corpus", "build", str(corpus), "--out", str(index_json)]) == 0
    assert audit_main(["corpus", "screen", str(project), "--index", str(index_json), "--out", str(screen_md), "--json", str(screen_json)]) == 0

    for path in (project_json, provenance_json, screen_json):
        _validate_finding_items(json.loads(path.read_text(encoding="utf-8")))
    assert json.loads(index_json.read_text(encoding="utf-8"))["projects"]


def test_route_dry_run_and_adapter_registry_contract(tmp_path: Path) -> None:
    source = ROOT / "examples" / "summary_stat_sample.csv"
    out = tmp_path / "dry.md"
    route_json = tmp_path / "route.json"

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(route_json), "--dry-run"]) == 0
    route = json.loads(route_json.read_text(encoding="utf-8"))
    ready_tool_ids = {
        tool_id
        for table in route["tables"]
        for tool_id, decision in table["routing_decisions"].items()
        if decision["status"] == "ready"
    }

    assert not out.exists()
    assert ready_tool_ids
    assert all(adapter_for(tool_id) is not None for tool_id in ready_tool_ids)


def test_adapter_facade_and_order_contract() -> None:
    import pcr_audit.adapters as legacy_adapters
    from pcr_audit.adapter_runtime import AuditRunContext as RuntimeContext

    assert legacy_adapters.AuditRunContext is RuntimeContext
    assert set(PYTHON_ADAPTER_ORDER).isdisjoint(R_ADAPTER_ORDER)
    assert PYTHON_ADAPTER_ORDER[:3] == ["raw_data_rules", "p_value_distribution", "crosscheck"]
    assert R_ADAPTER_ORDER == ["r_statcheck", "r_scrutiny", "r_rsprite2"]
    assert set(PYTHON_ADAPTER_ORDER + R_ADAPTER_ORDER).issubset(registered_tool_ids())


def test_missing_adapter_is_reported_as_info(tmp_path: Path, monkeypatch) -> None:
    source = ROOT / "examples" / "summary_stat_sample.csv"
    out = tmp_path / "missing-adapter.md"
    run_json = tmp_path / "missing-adapter.json"

    monkeypatch.setattr("pcr_audit.runner.adapter_for", lambda _tool_id: None)

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(run_json)]) == 0
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result.get("findings", [])]
    adapter_findings = [finding for finding in findings if finding["dependency_status"] == "adapter_missing"]

    assert adapter_findings
    assert {finding["level"] for finding in adapter_findings} == {"info"}


def test_adapter_runtime_error_is_reported_without_blocking_report(tmp_path: Path, monkeypatch) -> None:
    source = ROOT / "examples" / "summary_stat_sample.csv"
    out = tmp_path / "adapter-error.md"
    run_json = tmp_path / "adapter-error.json"

    def raising_adapter(_context, _tool_id):
        raise RuntimeError("simulated detector failure")

    monkeypatch.setattr("pcr_audit.runner.adapter_for", lambda tool_id: raising_adapter if tool_id == "crosscheck" else None)

    assert audit_main(["run", str(source), "--out", str(out), "--json", str(run_json)]) == 0
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result.get("findings", [])]
    runtime_errors = [finding for finding in findings if finding["dependency_status"] == "runtime_error"]

    assert out.exists()
    assert any(finding["tool_id"] == "crosscheck" and finding["level"] == "info" for finding in runtime_errors)
    assert "simulated detector failure" in json.dumps(runtime_errors, ensure_ascii=False)


def test_project_detector_runtime_error_is_reported_without_blocking_report(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "paper.md").write_text("References\n[1] doi:10.1234/example.2026\n", encoding="utf-8")
    pd.DataFrame({"subject": ["S1", "S2"], "value": [1.0, 2.0]}).to_csv(project / "data.csv", index=False)
    out = tmp_path / "project.md"
    run_json = tmp_path / "project.json"

    def raising_reference_audit(*_args, **_kwargs):
        raise RuntimeError("reference detector unavailable")

    monkeypatch.setattr("pcr_audit.product.reference_audit.analyze_references", raising_reference_audit)
    monkeypatch.setattr("pcr_audit.tool_system.rscript_available", lambda: True)
    monkeypatch.setattr("pcr_audit.tool_system.r_package_available", lambda _package: False)

    assert audit_main(["project", str(project), "--out", str(out), "--json", str(run_json), "--no-external-lookups"]) == 0
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result.get("findings", [])]

    assert out.exists()
    assert any(
        finding["tool_id"] == "reference_audit"
        and finding["level"] == "info"
        and finding["dependency_status"] == "runtime_error"
        for finding in findings
    )
    assert "reference detector unavailable" in json.dumps(findings, ensure_ascii=False)


def test_project_manifest_parse_error_is_reported_without_blocking_report(tmp_path: Path) -> None:
    manifest = tmp_path / "pcr-project.json"
    manifest.write_text("{not valid json", encoding="utf-8")
    out = tmp_path / "bad-project.md"
    run_json = tmp_path / "bad-project.json"

    assert audit_main(["project", str(manifest), "--out", str(out), "--json", str(run_json)]) == 0
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    findings = [finding for result in payload["results"] for finding in result.get("findings", [])]

    assert out.exists()
    assert any(
        finding["tool_id"] == "project_audit"
        and finding["level"] == "info"
        and finding["dependency_status"] == "runtime_error"
        for finding in findings
    )


def test_product_image_adapter_runs_image_audit_once(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_analyze_images(source: Path, image_dir: Path) -> list[TableResult]:
        calls.append((source, image_dir))
        return [TableResult("image_extract", 0, 0, [])]

    monkeypatch.setattr("pcr_audit.product.image_audit.analyze_images", fake_analyze_images)
    context = AuditRunContext(
        source=ROOT / "examples" / "project_minimal",
        workdir=tmp_path,
        route_payload={},
        payloads=[],
    )

    for tool_id in sorted(IMAGE_TOOL_IDS):
        product_adapter(context, tool_id)

    assert len(calls) == 1
    assert len(context.product_results) == 1


def test_product_domain_modules_match_legacy_imports() -> None:
    from pcr_audit import product_detectors
    from pcr_audit.product import code_audit, corpus_signals, image_audit, project_manifest, provenance, reference_audit

    assert reference_audit.analyze_references is product_detectors.analyze_references
    assert image_audit.analyze_images is product_detectors.analyze_images
    assert provenance.provenance_record is product_detectors.provenance_record
    assert code_audit.analyze_code_files is product_detectors.analyze_code_files
    assert project_manifest.parse_project_spec is product_detectors.parse_project_spec
    assert corpus_signals.build_corpus_index is product_detectors.build_corpus_index
