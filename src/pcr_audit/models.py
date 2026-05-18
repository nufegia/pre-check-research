from __future__ import annotations

from dataclasses import dataclass


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
    method_limitations: str = "该结果只提示需要复核的风险信号，不构成学术不端判断。"
    raw_output_ref: str = ""
    detector_runtime: str = "python"
    dependency_status: str = "ready"
    meaning: str = ""
    normal_explanations: str = ""
    review_steps: str = ""
    confidence: str = "medium"
    false_positive_risk: str = "medium"


@dataclass
class TableResult:
    name: str
    rows: int
    columns: int
    findings: list[Finding]


LEVEL_SCORE = {"high": 3, "medium": 2, "low": 1, "info": 0}
LEVEL_CN = {"high": "高", "medium": "中", "low": "低", "info": "提示"}


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
    )
    return finding
