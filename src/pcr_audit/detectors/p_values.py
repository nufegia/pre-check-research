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
    basis = ", ".join(f"{name}={value:.2g} (weight {weight:.0%})" for name, value, weight in parts)
    return score, f"{basis}; weighted total={score:.2f}"


def _normalize_name(name: Any) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"\s+", "", text)
    return text.replace("_", "").replace("-", "")


def _p_columns(df: pd.DataFrame) -> list[str]:
    columns = []
    for col in df.columns:
        normalized = _normalize_name(col)
        raw = str(col).lower()
        if re.search(r"^p$", normalized) or re.search(r"pvalue", normalized) or re.search(r"p[_ ]?value", raw) or re.search(r"^pval", normalized):
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
            ("P-value count", _sample_size_score(effective_n), 0.30),
            ("Rule determinism", 1.0 if check == "P-value domain" else 0.6 if check == "Marginally significant p-value clustering" else 0.3, 0.40),
            ("Effect strength", effect_score, 0.30),
        ]
    )
    if effective_n < 15 and level != "info":
        score = min(score, 0.40)
        basis += "; small sample n<15 confidence capped at 0.40"
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
        tool_name="P-value Set Weak Signal Detection",
        module="p_value_distribution",
        input_type="p_value_collection",
        routing_reason="Pure p-value collection routed to p-value set weak signal detection by deterministic routing.",
        method_limitations="This check only examines p-value collection shape; it does not know test family, direction, correction method, or complete result space; marginal clustering only prompts human review.",
        confidence="medium" if level != "info" else "low",
        confidence_score=score,
        confidence_basis=basis,
        false_positive_risk="high" if check == "Marginally significant p-value clustering" else "medium",
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
                invalid.append(f"{col}:row {idx}={raw}")
                continue
            _op, value = parsed
            if value < 0 or value > 1:
                invalid.append(f"{col}:row {idx}={raw}")
                continue
            parsed_values.append(float(value))

    if invalid:
        findings.append(
            _finding(
                name,
                "high",
                "P-value domain",
                "p-value collection",
                "Found unparseable p-values or values outside [0, 1] range.",
                "；".join(invalid[:12]),
                "Check whether the p-value column contains statistics, percentages, formatting annotations, or table extraction errors.",
                f"Abnormal entry count={len(invalid)}.",
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
                "Marginally significant p-value clustering",
                "p-value collection",
                "Multiple p-values are concentrated in the 0.045-0.050 interval.",
                f"Marginally significant={len(edge)}, significant p-values={len(sig)}, valid p-values={len(parsed_values)}",
                "This only indicates selective reporting or multiple comparison transparency risk; requires human review combining methods, preregistration, and complete result tables.",
                "This rule does not judge p-hacking; it only serves as a review clue for multiple comparison transparency.",
                effective_n=len(parsed_values),
                effect_score=1.0 if len(edge) / max(len(sig), 1) >= 0.50 else 0.7,
            )
        )

    if not findings:
        findings.append(
            _finding(
                name,
                "info",
                "P-value set run record",
                "p-value collection",
                "P-value set weak signal detection completed; no domain anomalies or marginal clustering found.",
                f"p-value columns={len(columns)}, valid p-values={len(parsed_values)}",
                "If these p-values come from extensive exploratory testing, manual review against complete test inventory and multiple correction strategy is still recommended.",
                effective_n=len(parsed_values),
                effect_score=0.2,
            )
        )

    return TableResult(name, int(df.shape[0]), int(df.shape[1]), findings)
