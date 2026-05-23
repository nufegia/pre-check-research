from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from pcr_audit.io import read_text_source
from pcr_audit.models import Finding, enrich_finding_explanation

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
DOC_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
DATA_SUFFIXES = {".csv", ".xlsx", ".xls"}
CODE_SUFFIXES = {".py", ".r", ".R", ".do", ".sps", ".sas"}
MATERIAL_ROLES = {"manuscript", "raw_data", "analysis_code", "figures", "supplement", "references", "image", "unknown"}
SYSTEM_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SYSTEM_DIR_NAMES = {".git", ".pcr", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
PMID_RE = re.compile(r"\bPMID\s*:?\s*(\d{5,10})\b", re.I)
REFERENCE_LINE_RE = re.compile(r"^\s*(?:\[\d+\]|\d+\.|\(\d+\))?\s*(?P<body>.{25,})$", re.M)
CLAIM_WITH_CITATION_RE = re.compile(r"(?P<claim>[^.\n]{30,240}?\s*(?:\[[0-9,;\-\s]+\]|\([A-Za-z][^)]+,\s*\d{4}\)))")
TORTURED_PHRASES = {
    "counterfeit consciousness": "artificial intelligence",
    "bosom peril": "breast cancer",
    "colossal information": "big data",
    "fake treatment": "placebo",
    "irregular woodland": "random forest",
    "profound neural organization": "deep neural network",
    "man-made brainpower": "artificial intelligence",
}

TEXT_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.I)
AUTHOR_LINE_RE = re.compile(r"^\s*(?:authors?|作者)\s*[:：]\s*(?P<value>.+)$", re.I | re.M)
INSTITUTION_LINE_RE = re.compile(r"^\s*(?:affiliations?|institutions?|单位|机构)\s*[:：]\s*(?P<value>.+)$", re.I | re.M)


@dataclass
class AuditConfig:
    external_lookups: bool = False
    grobid_url: str = ""
    contact_email: str = ""
    lookup_cache_dir: Path | None = None


@dataclass
class Material:
    path: Path
    role: str = "unknown"
    declared_path: str = ""


@dataclass
class ProjectSpec:
    source: Path
    project_id: str = ""
    title: str = ""
    materials: list[Material] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_audit_material_path(path: Path, root: Path | None = None) -> bool:
    """Return False for hidden/system paths that should not enter audit scope."""
    try:
        parts = path.relative_to(root).parts if root is not None else path.parts
    except ValueError:
        parts = path.parts
    for part in parts:
        if part in SYSTEM_FILE_NAMES or part in SYSTEM_DIR_NAMES:
            return False
        if part.startswith("."):
            return False
    return True


def iter_audit_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and is_audit_material_path(path, root))


def finding(
    table: str,
    level: str,
    check: str,
    target: str,
    summary: str,
    evidence: str,
    suggestion: str,
    detail: str = "",
    tool_id: str = "unknown",
    tool_name: str = "Unknown",
    module: str = "product",
    input_type: str = "unknown",
    detector_runtime: str = "python",
    dependency_status: str = "ready",
    location: str = "",
    calculation_trace: str = "",
    external_records: str = "",
    confidence_basis: str = "",
) -> Finding:
    item = Finding(
        table=table,
        level=level,
        check=check,
        target=target,
        summary=summary,
        evidence=evidence,
        detail=detail,
        suggestion=suggestion,
        tool_id=tool_id,
        tool_name=tool_name,
        module=module,
        input_type=input_type,
        detector_runtime=detector_runtime,
        dependency_status=dependency_status,
        location=location or table,
        calculation_trace=calculation_trace,
        external_records=external_records,
        confidence_basis=confidence_basis,
    )
    enrich_finding_explanation(item)
    return item


def _http_json(url: str, timeout: float = 8.0, contact_email: str = "") -> dict[str, Any] | None:
    user_agent = f"pcr-audit/1.1.0 ({contact_email})" if contact_email else "pcr-audit/1.1.0"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    context = None
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = None
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def _compat_http_json(url: str, timeout: float = 8.0, contact_email: str = "") -> dict[str, Any] | None:
    facade = sys.modules.get("pcr_audit.product_detectors")
    override = getattr(facade, "_http_json", None) if facade is not None else None
    if override is not None and override is not _http_json and override is not _compat_http_json:
        return override(url, timeout=timeout, contact_email=contact_email)
    return _http_json(url, timeout=timeout, contact_email=contact_email)


def _external_enabled(config: AuditConfig | None = None) -> bool:
    if config is not None:
        return bool(config.external_lookups)
    return os.environ.get("PCR_ENABLE_EXTERNAL_LOOKUPS", "").lower() in {"1", "true", "yes"}


def _env_config(workdir: Path | None = None) -> AuditConfig:
    return AuditConfig(
        external_lookups=_external_enabled(None),
        grobid_url=os.environ.get("PCR_GROBID_URL", ""),
        contact_email=os.environ.get("PCR_CONTACT_EMAIL", ""),
        lookup_cache_dir=(workdir / "lookup-cache") if workdir else None,
    )


def _cache_key(service: str, identifier: str) -> str:
    digest = hashlib.sha256(f"{service}:{identifier}".encode("utf-8")).hexdigest()[:24]
    return f"{service}-{digest}.json"


def _cached_lookup(
    service: str,
    identifier: str,
    url: str,
    config: AuditConfig,
    summary_fn,
) -> tuple[dict[str, Any] | None, str, bool]:
    cache_dir = config.lookup_cache_dir
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / _cache_key(service, identifier)
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return payload.get("response"), f"{service} cache_hit status={payload.get('status')} summary={payload.get('summary', '')}", True
    else:
        cache_path = None
    record: dict[str, Any] = {
        "service": service,
        "identifier": identifier,
        "url": url,
        "timestamp": _now_iso(),
        "status": "error",
        "summary": "",
    }
    response: dict[str, Any] | None = None
    try:
        response = _compat_http_json(url, contact_email=config.contact_email)
        record["status"] = "ok"
        record["summary"] = summary_fn(response)
        record["response"] = response
    except Exception as exc:
        record["error"] = str(exc)
        record["summary"] = str(exc)[:180]
    if cache_path is not None:
        cache_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return response, f"{service} cache_miss status={record['status']} summary={record['summary']}", False


def _grobid_endpoint(base_url: str) -> str:
    return base_url.rstrip("/") + "/api/processFulltextDocument"


def extract_text_with_grobid(source: Path, config: AuditConfig, findings: list[Finding]) -> str:
    if not config.grobid_url or source.suffix.lower() != ".pdf":
        return ""
    try:
        boundary = "----pcr-audit-boundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="input"; filename="{source.name}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + source.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
        request = urllib.request.Request(
            _grobid_endpoint(config.grobid_url),
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "pcr-audit/1.1.0"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            tei = response.read().decode("utf-8", errors="ignore")
        root = ElementTree.fromstring(tei)
        text = " ".join(node.text or "" for node in root.iter() if node.text)
        if not text.strip():
            raise ValueError("GROBID returned TEI without text content")
        findings.append(
            finding(
                str(source), "info", "GROBID structure extraction", "PDF",
                "GROBID REST extraction succeeded; used for reference/body text assisted parsing.",
                f"grobid_url={config.grobid_url}; extracted_chars={len(text)}",
                "GROBID extraction still requires human review against original document layout.",
                tool_id="grobid_extract", tool_name="GROBID REST structure extraction", input_type="paper_document",
            )
        )
        return text
    except Exception as exc:
        findings.append(
            finding(
                str(source), "info", "GROBID structure extraction", "PDF",
                "GROBID unavailable or returned unparseable content; fell back to local text extraction.",
                str(exc),
                "Verify GROBID service address, network, and PDF parsability; this notice does not count as a data risk.",
                tool_id="grobid_extract", tool_name="GROBID REST structure extraction", input_type="paper_document",
                dependency_status="grobid_unavailable",
                confidence_basis="External extraction downgrade record; not a data risk signal.",
            )
        )
        return ""


def _extract_reference_text(source: Path, config: AuditConfig | None = None, findings: list[Finding] | None = None) -> str:
    if config is not None and findings is not None:
        grobid_text = extract_text_with_grobid(source, config, findings)
        if grobid_text:
            return grobid_text
    if source.suffix.lower() in DOC_SUFFIXES:
        try:
            return read_text_source(source)
        except Exception:
            return ""
    if source.suffix.lower() in {".bib", ".ris"}:
        return source.read_text(encoding="utf-8", errors="ignore")
    return ""
