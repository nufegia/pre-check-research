from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pcr_audit import __version__
from pcr_audit.io import read_json, write_json

PUBLIC_EXPORT_SCHEMA_VERSION = "1.1"

PUBLIC_PATH_RE = re.compile(r"/Users/[^\s|,;)\]}]+")
MARKDOWN_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
PUBLIC_BANNED_PATTERNS = {
    "local_absolute_path": re.compile(r"/Users/"),
    "info_record_count": re.compile(r"\bInfo records?\b|info\s+运行记录|info-record count", re.I),
    "external_metadata_unverifiable": re.compile(r"DOI external metadata unverifiable|DOI 外部元数据不可核验", re.I),
    "pending_manual_review": re.compile(r"还需人工校验|需人工校验|manual review|human review", re.I),
    "markdown_code_style": re.compile(r"`[^`]+`"),
}

PUBLIC_EXCLUDED_STATUS_CHECKS = {
    "DOI extraction normalization skipped",
    "DOI metadata verification",
    "PMID metadata verification",
    "Reference identifier parsing",
    "External metadata verification not enabled",
    "Image extraction",
    "Analysis code rerun readiness check",
    "Insufficient materials for analysis script rerun",
    "Insufficient materials for cross-material reconciliation",
    "Local cross-corpus index missing",
    "SHA-256 File Record",
}
PUBLIC_FINDING_FIELDS = {
    "level",
    "table",
    "check",
    "target",
    "summary",
    "evidence",
    "detail",
    "suggestion",
    "tool_id",
    "tool_name",
    "input_type",
    "confidence_score",
    "evidence_id",
    "location",
    "external_records",
    "calculation_trace",
}
PUBLIC_LANGUAGE_REPLACEMENTS = (
    (re.compile(r"manual review needed to determine if", re.I), "source-material explanation is needed to determine whether"),
    (re.compile(r"manual review needed for", re.I), "source-material explanation is needed for"),
    (re.compile(r"requires human review", re.I), "requires source-material context"),
    (re.compile(r"need human review", re.I), "need source-material context"),
    (re.compile(r"human review", re.I), "source-material review"),
    (re.compile(r"manual review", re.I), "source-material review"),
    (re.compile(r"requires human judgment", re.I), "requires source-material context"),
)


def public_path(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    try:
        path = Path(text)
    except Exception:
        return text
    if path.is_absolute():
        return f"/{path.name}"
    return text


def sanitize_text(value: Any) -> str:
    text = str(value or "")

    def repl(match: re.Match[str]) -> str:
        return public_path(match.group(0))

    return PUBLIC_PATH_RE.sub(repl, text)


def sanitize_public_text(value: Any) -> str:
    text = sanitize_text(value)
    for pattern, replacement in PUBLIC_LANGUAGE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def sanitize_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_mapping(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_public_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_public_mapping(item) for key, item in value.items() if key in PUBLIC_FINDING_FIELDS}
    if isinstance(value, list):
        return [sanitize_public_mapping(item) for item in value]
    if isinstance(value, str):
        return sanitize_public_text(value)
    return value


def _iter_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if "results" in payload:
        for result in payload.get("results") or []:
            findings.extend(dict(finding) for finding in result.get("findings") or [])
    else:
        findings.extend(dict(finding) for finding in payload.get("findings") or [])
    return findings


def _service_boundary_from_info(finding: dict[str, Any]) -> str:
    check = str(finding.get("check") or "")
    summary = str(finding.get("summary") or "")
    dependency = str(finding.get("dependency_status") or "")
    if "Insufficient materials" in check or dependency in {"insufficient_material", "external_lookup_disabled"}:
        return sanitize_text(summary)
    return ""


def public_payload_from_audit(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source") or ""
    if isinstance(source, list):
        public_source: str | list[str] = [public_path(item) for item in source]
    else:
        public_source = public_path(source)

    exported_findings: list[dict[str, Any]] = []
    service_boundaries: list[str] = []
    for finding in _iter_findings(payload):
        level = str(finding.get("level") or "info")
        check = str(finding.get("check") or "")
        if level == "info":
            boundary = _service_boundary_from_info(finding)
            if boundary and boundary not in service_boundaries:
                service_boundaries.append(boundary)
            continue
        if check in PUBLIC_EXCLUDED_STATUS_CHECKS:
            continue
        item = sanitize_public_mapping(finding)
        for key in ("table", "location"):
            item[key] = public_path(item.get(key) or "")
        exported_findings.append(item)

    counts = Counter(str(finding.get("level") or "info") for finding in exported_findings)
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in exported_findings:
        clusters[str(finding.get("check") or "Unspecified")].append(finding)

    return {
        "schema_version": PUBLIC_EXPORT_SCHEMA_VERSION,
        "pcr_cli_version": __version__,
        "profile": "public",
        "source": public_source,
        "finding_counts": {
            "high": counts.get("high", 0),
            "medium": counts.get("medium", 0),
            "low": counts.get("low", 0),
        },
        "service_boundaries": service_boundaries,
        "signal_clusters": [
            {
                "check": check,
                "count": len(items),
                "levels": dict(Counter(str(item.get("level") or "") for item in items)),
                "representative_evidence": items[:5],
            }
            for check, items in sorted(clusters.items())
        ],
        "findings": exported_findings,
    }


def write_public_payload(audit_json: Path, out: Path) -> dict[str, Any]:
    payload = read_json(audit_json)
    public_payload = public_payload_from_audit(payload)
    write_json(out, public_payload)
    return public_payload


def lint_text(text: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for issue_id, pattern in PUBLIC_BANNED_PATTERNS.items():
        for match in pattern.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            issues.append({"id": issue_id, "severity": "error", "line": str(line_number), "message": match.group(0)[:120]})
            break
    for idx, text_line in enumerate(text.splitlines(), start=1):
        if not MARKDOWN_TABLE_RE.match(text_line):
            continue
        cells = [cell.strip() for cell in text_line.strip().strip("|").split("|")]
        if any(len(cell) > 160 for cell in cells):
            issues.append({"id": "long_markdown_table_cell", "severity": "error", "line": str(idx), "message": "Markdown table cell exceeds 160 characters."})
            break
    return issues


def lint_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    text = sanitize_text(str(payload))
    issues = lint_text(text)
    raw_text = str(payload)
    if "/Users/" in raw_text:
        issues.append({"id": "local_absolute_path", "severity": "error", "line": "0", "message": "Payload contains local absolute path."})
    if payload.get("profile") == "public":
        if "info" in payload.get("finding_counts", {}):
            issues.append({"id": "public_info_count", "severity": "error", "line": "0", "message": "Public payload finding_counts must not include info."})
        for finding in payload.get("findings") or []:
            if finding.get("level") == "info":
                issues.append({"id": "public_info_finding", "severity": "error", "line": "0", "message": "Public payload contains info finding."})
                break
    return issues


def lint_file(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".json":
        return lint_payload(read_json(path))
    return lint_text(path.read_text(encoding="utf-8"))
