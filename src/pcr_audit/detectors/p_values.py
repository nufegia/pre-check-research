from __future__ import annotations

import re
from typing import Any

import pandas as pd

from pcr_audit.crosscheck import parse_p_value
from pcr_audit.models import Finding, TableResult, enrich_finding_explanation


def _sample_size_score(n: int) -> float:
    if n >= 100:
        return 1.0
    if n >= 60:
        return 0.8
    if n >= 30:
        return 0.6
    if n >= 15:
        return 0.4
    return 0.2


def _weighted_confidence(parts: list[tuple[str, float, float]]) -> tuple[float, str]:
    total_weight = sum(weight for _, _, weight in parts) or 1.0
    score = sum(value * weight for _, value, weight in parts) / total_weight
    score = max(0.0, min(1.0, float(score)))
    basis = ", ".join(f"{name}={value:.2g}(权重{weight:.0%})" for name, value, weight in parts)
    return score, f"{basis}; 加权总分={score:.2f}"


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
    effective_n: int = 0,
    effect_score: float = 0.6,
) -> Finding:
    score, basis = _weighted_confidence(
        [
            ("p值数量", _sample_size_score(effective_n), 0.30),
            ("规则确定性", 1.0 if check == "p值定义域" else 0.6 if check == "边缘显著p值聚集" else 0.3, 0.40),
            ("效应强度", effect_score, 0.30),
        ]
    )
    if effective_n < 15 and level != "info":
        score = min(score, 0.40)
        basis += "; 小样本n<15置信度封顶0.40"
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
        confidence_score=score,
        confidence_basis=basis,
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
                effective_n=len(parsed_values) + len(invalid),
                effect_score=1.0 if len(invalid) >= 3 else 0.7,
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
                effective_n=len(parsed_values),
                effect_score=1.0 if len(edge) / max(len(sig), 1) >= 0.50 else 0.7,
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
                effective_n=len(parsed_values),
                effect_score=0.2,
            )
        )

    return TableResult(name, int(df.shape[0]), int(df.shape[1]), findings)
