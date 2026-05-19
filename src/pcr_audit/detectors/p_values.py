from __future__ import annotations

import re
from typing import Any

import pandas as pd

from pcr_audit.crosscheck import parse_p_value
from pcr_audit.models import Finding, TableResult, enrich_finding_explanation


def _normalize_name(name: Any) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"\s+", "", text)
    return text.replace("_", "").replace("-", "")


def _p_columns(df: pd.DataFrame) -> list[str]:
    columns = []
    for col in df.columns:
        normalized = _normalize_name(col)
        raw = str(col).lower()
        if re.search(r"^p$", normalized) or re.search(r"pvalue", normalized) or re.search(r"p值", raw) or re.search(r"^pval", normalized):
            columns.append(str(col))
    return columns


def _finding(
    table: str,
    level: str,
    check: str,
    target: str,
    summary: str,
    evidence: str,
    suggestion: str,
    detail: str = "",
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
        tool_id="p_value_distribution",
        tool_name="p值集合弱信号检测",
        module="p_value_distribution",
        input_type="p_value_collection",
        routing_reason="纯 p 值集合由确定性路由选择 p 值集合弱信号检测。",
        method_limitations="该检查只看 p 值集合形态，不知道检验族、方向、校正方式或完整结果空间；边缘显著聚集只能提示人工复核。",
        confidence="medium" if level != "info" else "low",
        false_positive_risk="high" if check == "边缘显著p值聚集" else "medium",
    )
    enrich_finding_explanation(item)
    return item


def analyze_p_value_collection(name: str, df: pd.DataFrame) -> TableResult:
    findings: list[Finding] = []
    columns = _p_columns(df)
    parsed_values: list[float] = []
    invalid: list[str] = []

    for col in columns:
        for idx, raw in enumerate(df[col].tolist(), start=1):
            if pd.isna(raw) or str(raw).strip() == "":
                continue
            parsed = parse_p_value(raw)
            if parsed is None:
                invalid.append(f"{col}:行{idx}={raw}")
                continue
            _op, value = parsed
            if value < 0 or value > 1:
                invalid.append(f"{col}:行{idx}={raw}")
                continue
            parsed_values.append(float(value))

    if invalid:
        findings.append(
            _finding(
                name,
                "high",
                "p值定义域",
                "p值集合",
                "发现无法解析或超出 [0, 1] 范围的 p 值。",
                "；".join(invalid[:12]),
                "核对 p 值列是否混入统计量、百分比、格式化注释或表格抽取错误。",
                f"异常条目数={len(invalid)}。",
            )
        )

    edge = [p for p in parsed_values if 0.045 <= p <= 0.05]
    sig = [p for p in parsed_values if p < 0.05]
    if len(parsed_values) >= 10 and len(edge) >= 3 and len(edge) / max(len(sig), 1) >= 0.30:
        findings.append(
            _finding(
                name,
                "medium",
                "边缘显著p值聚集",
                "p值集合",
                "多个 p 值集中在 0.045-0.050 区间。",
                f"边缘显著={len(edge)}，显著p值={len(sig)}，有效p值={len(parsed_values)}",
                "这只能提示选择性报告或多重比较透明度风险；需结合方法、预注册和完整结果表人工复核。",
                "该规则不判断 p-hacking，只作为复核线索。",
            )
        )

    if not findings:
        findings.append(
            _finding(
                name,
                "info",
                "p值集合运行记录",
                "p值集合",
                "p 值集合弱信号检测已完成，未发现定义域异常或边缘显著聚集。",
                f"p值列={len(columns)}，有效p值={len(parsed_values)}",
                "若这些 p 值来自大量探索性检验，仍建议结合完整检验清单和多重校正策略人工复核。",
            )
        )

    return TableResult(name, int(df.shape[0]), int(df.shape[1]), findings)
