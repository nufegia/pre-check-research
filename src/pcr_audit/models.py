from __future__ import annotations

from dataclasses import dataclass


VALID_LEVELS = {"high", "medium", "low", "info"}
VALID_DETECTOR_RUNTIMES = {"python", "r", "cli"}


@dataclass
class Finding:
    table: str
    level: str
    check: str
    target: str
    summary: str
    evidence: str
    detail: str
    suggestion: str
    tool_id: str = "unknown"
    tool_name: str = "Unknown tool"
    module: str = "unknown"
    input_type: str = "unknown"
    routing_reason: str = "This tool was selected by deterministic routing."
    method_limitations: str = "This result only flags risk signals that need human review and does not constitute a data integrity verdict."
    raw_output_ref: str = ""
    detector_runtime: str = "python"
    dependency_status: str = "ready"
    meaning: str = ""
    normal_explanations: str = ""
    review_steps: str = ""
    confidence: str = "medium"
    confidence_score: float = 0.6
    false_positive_risk: str = "medium"
    evidence_id: str = ""
    location: str = ""
    calculation_trace: str = ""
    external_records: str = ""
    review_actions: str = ""
    confidence_basis: str = ""


@dataclass
class TableResult:
    name: str
    rows: int
    columns: int
    findings: list[Finding]


LEVEL_SCORE = {"high": 3, "medium": 2, "low": 1, "info": 0}
LEVEL_LABEL = {"high": "High", "medium": "Medium", "low": "Low", "info": "Info"}


def validate_finding(finding: Finding) -> None:
    """Validate stable Finding contract fields before JSON serialization."""
    if finding.level not in VALID_LEVELS:
        raise ValueError(f"Invalid finding level: {finding.level!r}")
    if finding.detector_runtime and finding.detector_runtime not in VALID_DETECTOR_RUNTIMES:
        raise ValueError(f"Invalid detector runtime: {finding.detector_runtime!r}")
    for field_name in ("check", "target", "summary", "evidence", "detail", "suggestion"):
        if getattr(finding, field_name) is None:
            raise ValueError(f"Finding field {field_name} must not be None")


def validate_results(results: list[TableResult]) -> None:
    for result in results:
        for finding in result.findings:
            validate_finding(finding)


def enrich_finding_explanation(finding: Finding) -> None:
    if not finding.meaning:
        finding.meaning = finding.summary or "This item indicates the detector found a pattern requiring human review."
    if not finding.normal_explanations:
        finding.normal_explanations = (
            "Possible benign causes include study design, instrument thresholds, batch formatting, table extraction errors, or legitimate data cleaning."
        )
    if not finding.review_steps:
        finding.review_steps = finding.suggestion or "Review original records, statistical scripts, and data processing logs to confirm whether this signal has a legitimate source."
    if finding.confidence_score is None or (
        finding.confidence_score == 0.6 and finding.confidence == "medium" and finding.level != "medium"
    ):
        finding.confidence_score = {"high": 0.85, "medium": 0.6, "low": 0.3, "info": 0.1}.get(finding.level, 0.6)
    finding.confidence_score = max(0.0, min(1.0, float(finding.confidence_score)))
    if finding.confidence_score >= 0.75:
        finding.confidence = "high"
    elif finding.confidence_score >= 0.40:
        finding.confidence = "medium"
    else:
        finding.confidence = "low"
    if not finding.confidence:
        finding.confidence = "high" if finding.level == "high" else "medium"
    if not finding.false_positive_risk:
        finding.false_positive_risk = "low" if finding.level == "high" else "medium"
    if not finding.evidence_id:
        finding.evidence_id = f"{finding.tool_id}:{finding.check}:{finding.target}".replace(" ", "_")
    if not finding.location:
        finding.location = finding.table
    if not finding.review_actions:
        finding.review_actions = finding.review_steps
    if not finding.confidence_basis:
        finding.confidence_basis = (
            "Generated from deterministic rules or reproducible formulas; still requires human judgment considering study design, original records, and material extraction quality."
        )


def finding_from_mapping(source: str, raw: dict) -> Finding:
    raw_level = str(raw.get("level") or "info")
    raw_confidence = str(raw.get("confidence") or "")
    raw_score = raw.get("confidence_score")
    if raw_score is None:
        raw_score = {"high": 0.85, "medium": 0.6, "low": 0.3}.get(
            raw_confidence,
            {"high": 0.85, "medium": 0.6, "low": 0.3, "info": 0.1}.get(raw_level, 0.6),
        )
    finding = Finding(
        table=str(raw.get("table") or raw.get("source") or source),
        level=raw_level,
        check=str(raw.get("check") or "Run Record"),
        target=str(raw.get("target") or ""),
        summary=str(raw.get("summary") or ""),
        evidence=str(raw.get("evidence") or ""),
        detail=str(raw.get("detail") or ""),
        suggestion=str(raw.get("suggestion") or ""),
        tool_id=str(raw.get("tool_id") or ""),
        tool_name=str(raw.get("tool_name") or ""),
        module=str(raw.get("module") or ""),
        input_type=str(raw.get("input_type") or ""),
        detector_runtime=str(raw.get("detector_runtime") or ""),
        dependency_status=str(raw.get("dependency_status") or "ready"),
        meaning=str(raw.get("meaning") or ""),
        normal_explanations=str(raw.get("normal_explanations") or ""),
        review_steps=str(raw.get("review_steps") or ""),
        confidence=raw_confidence,
        confidence_score=float(raw_score),
        false_positive_risk=str(raw.get("false_positive_risk") or ""),
        evidence_id=str(raw.get("evidence_id") or ""),
        location=str(raw.get("location") or ""),
        calculation_trace=str(raw.get("calculation_trace") or ""),
        external_records=str(raw.get("external_records") or ""),
        review_actions=str(raw.get("review_actions") or ""),
        confidence_basis=str(raw.get("confidence_basis") or ""),
    )
    enrich_finding_explanation(finding)
    return finding


def info_finding(
    source: str,
    tool_id: str,
    summary: str,
    evidence: str,
    dependency_status: str = "dependency_missing",
    input_type: str = "unknown",
) -> Finding:
    finding = Finding(
        table=source,
        level="info",
        check="Tool Run Record",
        target=tool_id,
        summary=summary,
        evidence=evidence,
        detail="",
        suggestion="Install or repair this CLI and retry; results from other available tools are unaffected.",
        tool_id=tool_id,
        tool_name=tool_id,
        module="routing",
        input_type=input_type,
        detector_runtime="cli",
        dependency_status=dependency_status,
        meaning=summary,
        normal_explanations="Missing tool, missing dependency, or routing skip is not a data risk.",
        review_steps="Check PATH, Rscript, corresponding R package installation status, and route JSON.",
        confidence="low",
        confidence_score=0.1,
        false_positive_risk="low",
        evidence_id=f"{tool_id}:info:{source}",
        location=source,
        review_actions="Check PATH, Rscript, corresponding R package installation status, and route JSON.",
        confidence_basis="This item originates from tool routing or dependency checks and is not a data risk signal.",
    )
    return finding
