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
    routing_reason: str = "由确定性路由选择该工具。"
    method_limitations: str = "该结果只提示需要复核的风险信号，不构成数据风险校验判定。"
    raw_output_ref: str = ""
    detector_runtime: str = "python"
    dependency_status: str = "ready"
    meaning: str = ""
    normal_explanations: str = ""
    review_steps: str = ""
    confidence: str = "medium"
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
LEVEL_CN = {"high": "高", "medium": "中", "low": "低", "info": "提示"}


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
        finding.meaning = finding.summary or "该项表示检测器发现了需要人工复核的模式。"
    if not finding.normal_explanations:
        finding.normal_explanations = (
            "可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。"
        )
    if not finding.review_steps:
        finding.review_steps = finding.suggestion or "回看原始记录、统计脚本和数据处理日志，确认该信号是否有合理来源。"
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
            "基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。"
        )


def finding_from_mapping(source: str, raw: dict) -> Finding:
    finding = Finding(
        table=str(raw.get("table") or raw.get("source") or source),
        level=str(raw.get("level") or "info"),
        check=str(raw.get("check") or "运行记录"),
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
        confidence=str(raw.get("confidence") or ""),
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
        check="工具运行记录",
        target=tool_id,
        summary=summary,
        evidence=evidence,
        detail="",
        suggestion="安装或修复该 CLI 后重试；其他可用工具的结果不受影响。",
        tool_id=tool_id,
        tool_name=tool_id,
        module="routing",
        input_type=input_type,
        detector_runtime="cli",
        dependency_status=dependency_status,
        meaning=summary,
        normal_explanations="工具缺失、依赖缺失或路由跳过不是数据风险。",
        review_steps="检查 PATH、Rscript、对应 R 包安装状态和 route JSON。",
        confidence="low",
        false_positive_risk="low",
        evidence_id=f"{tool_id}:info:{source}",
        location=source,
        review_actions="检查 PATH、Rscript、对应 R 包安装状态和 route JSON。",
        confidence_basis="该项来自工具路由或依赖检查，不是数据风险信号。",
    )
    return finding
