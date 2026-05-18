from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from pcr_audit.models import Finding, TableResult, enrich_finding_explanation, finding_from_mapping


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.strip().str.replace(",", "", regex=False).str.replace("%", "", regex=False),
        errors="coerce",
    )


def _add_extra_finding(
    findings: list[Finding],
    table: str,
    level: str,
    check: str,
    target: str,
    summary: str,
    evidence: str,
    suggestion: str,
    detail: str = "",
) -> None:
    finding = Finding(
        table=table,
        level=level,
        check=check,
        target=target,
        summary=summary,
        evidence=evidence,
        detail=detail,
        suggestion=suggestion,
        tool_id="raw_data_rules",
        tool_name="基础表格规则",
        module="raw_data_rules",
        input_type="raw_observation_table",
        routing_reason="原始观测表由确定性路由选择基础表格规则。",
        method_limitations="原始数据规则用于发现重复、缺失、排序、分组和平衡异常；结果需结合实验流程解释。",
    )
    enrich_finding_explanation(finding)
    findings.append(finding)


def _row_signature(row: pd.Series) -> tuple[str, ...]:
    return tuple("" if pd.isna(value) else str(value).strip().lower() for value in row)


def _append_near_duplicate_rows(name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    if len(df) < 10 or df.shape[1] < 3:
        return
    signatures = [_row_signature(row) for _, row in df.iterrows()]
    hits: list[str] = []
    for idx in range(len(signatures) - 1):
        left = signatures[idx]
        right = signatures[idx + 1]
        comparable = [(a, b) for a, b in zip(left, right, strict=False) if a or b]
        if len(comparable) < 3:
            continue
        same = sum(1 for a, b in comparable if a == b)
        if same / len(comparable) >= 0.85:
            hits.append(f"行{idx + 1}/行{idx + 2}: {same}/{len(comparable)}列相同")
    if len(hits) >= 2:
        _add_extra_finding(
            findings,
            name,
            "medium",
            "近似重复行",
            "相邻行",
            "发现多组相邻记录高度相似。",
            "；".join(hits[:8]),
            "核对是否存在复制粘贴后仅改动少数字段，或这些记录是否本应共享大量字段。",
            f"近似重复判定阈值为非空字段 85% 以上相同；命中组数={len(hits)}。",
        )


def _append_missing_by_group(name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    if len(df) < 20:
        return
    group_cols = [
        col
        for col in df.columns
        if 2 <= df[col].nunique(dropna=True) <= 8 and df[col].notna().sum() >= max(10, len(df) * 0.5)
    ]
    for group_col in group_cols[:3]:
        for value_col in df.columns:
            if value_col == group_col:
                continue
            frame = pd.DataFrame({"group": df[group_col].astype(str), "missing": df[value_col].isna()}).dropna()
            if frame.empty:
                continue
            rates = frame.groupby("group")["missing"].mean()
            if len(rates) < 2:
                continue
            spread = float(rates.max() - rates.min())
            if rates.max() >= 0.35 and spread >= 0.30:
                evidence = "; ".join(f"{group}: {rate:.1%}" for group, rate in rates.sort_values(ascending=False).items())
                _add_extra_finding(
                    findings,
                    name,
                    "medium",
                    "缺失集中于分组",
                    f"{group_col} -> {value_col}",
                    "缺失值在不同分组之间分布差异较大。",
                    evidence,
                    "复核缺失是否由实验流程、纳排标准、仪器批次或后续剔除造成，并在论文中说明。",
                    f"分组缺失率最大差={spread:.1%}。",
                )
                return


def _append_group_balance(name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    if len(df) < 20:
        return
    group_cols = [
        col
        for col in df.columns
        if 2 <= df[col].nunique(dropna=True) <= 6 and df[col].notna().sum() >= max(15, len(df) * 0.7)
    ]
    numeric = {str(col): _coerce_numeric(df[col]) for col in df.columns}
    numeric = {col: series for col, series in numeric.items() if series.notna().sum() >= 15}
    for group_col in group_cols[:3]:
        groups = df[group_col].astype(str)
        balanced: list[str] = []
        for col, series in numeric.items():
            if col == str(group_col):
                continue
            frame = pd.DataFrame({"group": groups, "value": series}).dropna()
            grouped = [g["value"].astype(float).to_numpy() for _, g in frame.groupby("group")]
            grouped = [arr for arr in grouped if len(arr) >= 5]
            if len(grouped) < 2:
                continue
            means = np.array([float(np.mean(arr)) for arr in grouped])
            sds = np.array([float(np.std(arr, ddof=1)) for arr in grouped if len(arr) > 1])
            if len(sds) < 2:
                continue
            mean_scale = max(abs(float(np.mean(means))), 1e-12)
            sd_scale = max(abs(float(np.mean(sds))), 1e-12)
            if float(np.std(means) / mean_scale) < 0.005 and float(np.std(sds) / sd_scale) < 0.02:
                balanced.append(col)
        if len(balanced) >= 3:
            _add_extra_finding(
                findings,
                name,
                "medium",
                "多变量分组异常均衡",
                str(group_col),
                "多个数值变量在分组间均值和方差都异常接近。",
                "命中变量：" + ", ".join(balanced[:10]),
                "随机化研究中基线均衡是期望结果，但多个变量过度相似也应复核随机化、分组编码和剔除流程。",
                f"当前规则要求至少 3 个变量同时满足均值CV<0.5%、SD CV<2%；命中={len(balanced)}。",
            )
            return


def analyze_raw_data_rules(name: str, df: pd.DataFrame, input_type: str = "raw_observation_table") -> TableResult:
    """Run the raw-data detector while keeping legacy implementation out of CLI code."""
    from pcr_audit.detectors.raw_legacy import analyze_raw_data_rules as legacy_analyze_raw_data_rules

    result = legacy_analyze_raw_data_rules(name, df, input_type)
    findings = [finding_from_mapping(name, asdict(finding)) for finding in result.findings]
    _append_near_duplicate_rows(name, df, findings)
    _append_missing_by_group(name, df, findings)
    _append_group_balance(name, df, findings)
    return TableResult(
        name=result.name,
        rows=result.rows,
        columns=result.columns,
        findings=findings,
    )
