"""Row-level mathematical cross-checks on summary statistics tables.

Validates derived statistics (SE, CI, percent, p) against primary statistics
(N, SD, Mean) using pure mathematical definitions. Every check operates per-row
and produces individual findings with quantitative evidence.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from pcr_audit.models import Finding, TableResult, enrich_finding_explanation

# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

COLUMN_PATTERNS: dict[str, list[str]] = {
    "N":        [r"^n$", r"samplesize", r"cases?", r"样本量", r"例数", r"人数", r"^number$"],
    "Mean":     [r"^mean$", r"^means$", r"均值", r"均数", r"平均值", r"平均数"],
    "SD":       [r"^sd$", r"^std$", r"标准差", r"stdev"],
    "SE":       [r"^se$", r"^sem$", r"标准误", r"sterr"],
    "CI_low":   [r"cilow", r"cilower", r"ci[_\- ]?l", r"lcl", r"置信区间下限", r"下限", r"^low$"],
    "CI_high":  [r"cihigh", r"ciupper", r"ci[_\- ]?u", r"ucl", r"置信区间上限", r"上限", r"^high$"],
    "count":    [r"^count$", r"n[_\- ]?pos", r"频数", r"计数"],
    "percent":  [r"percent", r"percentage", r"^prop$", r"^rate$", r"百分比", r"比例", r"率"],
    "effect":   [r"^or$", r"oddsratio", r"^rr$", r"riskratio", r"^hr$", r"hazardratio", r"效应量", r"比值比", r"风险比"],
    "t":        [r"^t$", r"t[_\- ]?value", r"t[_\- ]?stat", r"t统计"],
    "df":       [r"^df$", r"^dof$", r"自由度", r"degreeoffreedom"],
    "p":        [r"^p$", r"p[_\- ]?value", r"^pval$", r"p值"],
}


def coerce_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .replace({"": np.nan, "nan": np.nan, "None": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_name(name: Any) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"\s+", "", text)
    return text.replace("_", "").replace("-", "")


def columns_matching(df: pd.DataFrame, patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for col in df.columns:
        normalized = normalize_name(col)
        raw = str(col).lower()
        if any(re.search(pattern, normalized) or re.search(pattern, raw) for pattern in patterns):
            matches.append(str(col))
    return matches


def first_existing(candidates: list[str]) -> str | None:
    return candidates[0] if candidates else None


def parse_p_value(value: Any) -> tuple[str, float] | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower().replace(" ", "")
    if text in {"", "nan", "ns", "n.s.", "na", "n/a"}:
        return None
    match = re.match(r"^(<=|>=|<|>|=)?([0-9]*\.?[0-9]+(?:e[-+]?\d+)?)$", text)
    if not match:
        return None
    op = match.group(1) or "="
    try:
        return op, float(match.group(2))
    except ValueError:
        return None


def add_finding(
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
    finding = Finding(table, level, check, target, summary, evidence, detail, suggestion)
    enrich_finding_explanation(finding)
    findings.append(finding)


def tag_findings(
    findings: list[Finding],
    tool_id: str,
    tool_name: str,
    module: str,
    input_type: str,
    routing_reason: str,
    method_limitations: str,
    raw_output_ref: str = "",
    detector_runtime: str = "python",
    dependency_status: str = "ready",
) -> list[Finding]:
    for finding in findings:
        finding.tool_id = tool_id
        finding.tool_name = tool_name
        finding.module = module
        finding.input_type = input_type
        finding.routing_reason = routing_reason
        finding.method_limitations = method_limitations
        finding.raw_output_ref = raw_output_ref
        finding.detector_runtime = detector_runtime
        finding.dependency_status = dependency_status
        enrich_finding_explanation(finding)
    return findings


def _detect_columns(df: pd.DataFrame) -> dict[str, str | list[str] | None]:
    """Detect column names for each summary-statistics role.

    Returns a dict mapping role names to column names (str for single-column
    roles, list[str] for multi-column roles like 'p'), or None if not found.
    """
    detected: dict[str, str | list[str] | None] = {}
    for role, patterns in COLUMN_PATTERNS.items():
        matches = columns_matching(df, patterns)
        if role == "p":
            detected[role] = matches  # keep all matches for p columns
        else:
            detected[role] = matches[0] if matches else None
    return detected


def _detect_percent_scale(series: pd.Series) -> float:
    """Return 100.0 if values appear to be percentages (0-100), 1.0 if proportions (0-1)."""
    valid = series.dropna()
    if valid.empty:
        return 100.0
    return 100.0 if (valid.max() > 1.0) else 1.0


# ---------------------------------------------------------------------------
# Tolerance configuration
# ---------------------------------------------------------------------------


@dataclass
class CrosscheckTolerances:
    se_relative: float = 0.05        # relative error for SE vs SD/sqrt(N)
    ci_center_relative: float = 0.05  # |ci_center - mean| / ci_span
    ci_span_relative: float = 0.10    # |ci_span - 2*t_crit*SE| / (2*t_crit*SE)
    percent_absolute: float = 0.02    # |percent/scale - count/N|
    p_absolute_tight: float = 0.005   # medium threshold for p vs t(df)
    p_absolute_loose: float = 0.01    # high threshold for p vs t(df)
    confidence_level: float = 0.95    # for t_crit calculation
    pct_scale: float = 100.0          # 100.0 for percentages, 1.0 for proportions


# ---------------------------------------------------------------------------
# t critical value helper
# ---------------------------------------------------------------------------


def _t_crit(df_val: float | None, confidence_level: float = 0.95) -> float:
    """Two-tailed t critical value for the given confidence level.

    Falls back to z-score (normal quantile) when df is missing or invalid.
    """
    tail = (1.0 - confidence_level) / 2.0
    if df_val is not None and df_val > 0 and np.isfinite(df_val):
        try:
            return float(stats.t.ppf(1.0 - tail, df_val))
        except Exception:
            pass
    return float(stats.norm.ppf(1.0 - tail))


# ---------------------------------------------------------------------------
# Per-row check functions
# ---------------------------------------------------------------------------

def _check_se_sd_n(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    tol: CrosscheckTolerances,
) -> None:
    se = row.get("SE")
    sd = row.get("SD")
    n = row.get("N")
    if any(v is None or pd.isna(v) for v in (se, sd, n)):
        return
    if n <= 1 or sd < 0 or se < 0:
        return
    expected = sd / math.sqrt(n)
    if expected == 0.0 and se == 0.0:
        return
    rel_err = abs(se - expected) / max(expected, 1e-12)
    if rel_err <= tol.se_relative:
        return
    level = "high" if rel_err > tol.se_relative * 3 else "medium"
    add_finding(
        findings, table_name, level,
        "SE/SD/√N一致性", f"行{row_idx}",
        f"标准误SE与SD/√N不一致（偏差={rel_err:.1%}）",
        f"SE报告={se:.6g}，SD/√N={expected:.6g}，N={n:.6g}，SD={sd:.6g}",
        "核对SE是否为标准误（非SD或CI半宽），确认统计脚本输出。",
    )


def _check_ci_centering(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    tol: CrosscheckTolerances,
) -> None:
    ci_low = row.get("CI_low")
    ci_high = row.get("CI_high")
    mean = row.get("Mean")
    if any(v is None or pd.isna(v) for v in (ci_low, ci_high, mean)):
        return
    ci_center = (ci_low + ci_high) / 2.0
    ci_span = ci_high - ci_low
    if ci_span <= 0:
        return  # caught by _check_ci_validity
    rel_err = abs(ci_center - mean) / ci_span
    if rel_err <= tol.ci_center_relative:
        return
    level = "high" if rel_err > tol.ci_center_relative * 3 else "medium"
    add_finding(
        findings, table_name, level,
        "CI中心一致性", f"行{row_idx}",
        f"均值未位于CI区间中心（偏差={rel_err:.1%}的CI半宽）",
        f"均值={mean:.6g}，CI中心={(ci_low + ci_high) / 2:.6g}，CI=[{ci_low:.6g}, {ci_high:.6g}]",
        "对称CI应以均值为中心；非对称CI需在方法中说明。",
    )


def _check_ci_span_vs_se(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    tol: CrosscheckTolerances,
) -> None:
    ci_low = row.get("CI_low")
    ci_high = row.get("CI_high")
    se = row.get("SE")
    if any(v is None or pd.isna(v) for v in (ci_low, ci_high, se)):
        return
    ci_span = ci_high - ci_low
    if ci_span <= 0 or se <= 0:
        return
    df_val = row.get("df")
    n_val = row.get("N")
    df_for_t = df_val if df_val is not None and not pd.isna(df_val) and df_val > 0 else (
        n_val - 1 if n_val is not None and not pd.isna(n_val) and n_val > 1 else None
    )
    t = _t_crit(df_for_t, tol.confidence_level)
    expected_span = 2.0 * t * se
    rel_err = abs(ci_span - expected_span) / expected_span
    if rel_err <= tol.ci_span_relative:
        return
    add_finding(
        findings, table_name, "medium",
        "CI宽度/SE一致性", f"行{row_idx}",
        f"CI宽度与SE×t临界值不一致（偏差={rel_err:.1%}）",
        f"CI宽度={ci_span:.6g}，2×t({df_for_t:.6g})×SE={expected_span:.6g}",
        "核对CI的置信水平（通常95%）和SE是否对应。",
    )


def _check_ci_validity(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    _tol: CrosscheckTolerances,
) -> None:
    ci_low = row.get("CI_low")
    ci_high = row.get("CI_high")
    if ci_low is None or ci_high is None or pd.isna(ci_low) or pd.isna(ci_high):
        return
    if ci_low > ci_high:
        add_finding(
            findings, table_name, "high",
            "CI区间倒置", f"行{row_idx}",
            "置信区间下限大于上限。",
            f"CI=[{ci_low:.6g}, {ci_high:.6g}]，下限 > 上限",
            "CI列顺序可能写反，或表格抽取时发生错列。",
        )
        return
    mean = row.get("Mean")
    if mean is not None and not pd.isna(mean):
        eps = 1e-12 * abs(ci_high - ci_low)
        if mean < ci_low - eps or mean > ci_high + eps:
            add_finding(
                findings, table_name, "high",
                "均值不在CI区间内", f"行{row_idx}",
                "均值未包含在置信区间内。",
                f"均值={mean:.6g}，CI=[{ci_low:.6g}, {ci_high:.6g}]",
                "核对均值与CI是否来自同一分析；CI可能写反或均值可能标错。",
            )


def _check_percent_count(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    tol: CrosscheckTolerances,
) -> None:
    pct = row.get("percent")
    cnt = row.get("count")
    n = row.get("N")
    if any(v is None or pd.isna(v) for v in (pct, cnt, n)):
        return
    if n <= 0 or cnt < 0 or pct < 0:
        return
    expected = cnt / n * tol.pct_scale
    diff = abs(pct - expected)
    if diff <= tol.percent_absolute:
        return
    level = "high" if diff > tol.percent_absolute * 3 else "medium"
    add_finding(
        findings, table_name, level,
        "百分比/计数一致性", f"行{row_idx}",
        f"百分比与count/N反算不一致（差值={diff:.3f}）",
        f"报告={pct:.6g}，count/N×{tol.pct_scale:.0f}={expected:.6g}，count={cnt:.6g}，N={n:.6g}",
        "核对百分比的分母是否为该行的N；确认count是否正确。",
    )


def _check_p_validity(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    _tol: CrosscheckTolerances,
) -> None:
    for p_col, p_raw in row.get("_p_raw", {}).items():
        if p_raw is None:
            continue
        parsed = parse_p_value(p_raw)
        if parsed is None:
            continue
        _, p_val = parsed
        if 0.0 <= p_val <= 1.0:
            continue
        add_finding(
            findings, table_name, "high",
            "p值超出定义域", f"行{row_idx}",
            f"p值超出[0, 1]范围。",
            f"报告p值={p_raw}（{p_col}）",
            "p值必须介于0到1之间；可能是录入错误或小数点位错。",
        )


def _check_p_vs_t(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    tol: CrosscheckTolerances,
) -> None:
    t_val = row.get("t")
    df_val = row.get("df")
    if t_val is None or df_val is None or pd.isna(t_val) or pd.isna(df_val):
        return
    if df_val <= 0:
        return
    for p_col, p_raw in row.get("_p_raw", {}).items():
        if p_raw is None:
            continue
        parsed = parse_p_value(p_raw)
        if parsed is None:
            continue
        op, reported_p = parsed
        try:
            computed_p = 2.0 * stats.t.sf(abs(t_val), df_val)
        except Exception:
            continue
        diff = abs(reported_p - computed_p)
        if op in ("<", "<="):
            if reported_p >= computed_p:
                continue  # e.g., p<0.05 when computed=0.02 is fine
        if op in (">", ">="):
            if reported_p <= computed_p:
                continue  # e.g., p>0.05 when computed=0.08 is fine
        if diff <= tol.p_absolute_tight:
            continue
        level = "high" if diff > tol.p_absolute_loose else "medium"
        add_finding(
            findings, table_name, level,
            "p值/t统计量一致性", f"行{row_idx}",
            f"p值与t统计量(df)反算不一致（差值={diff:.4f}）",
            f"报告p={p_raw}（解析为{reported_p:.6g}），t={t_val:.6g}，df={df_val:.6g}，反算p={computed_p:.6g}",
            "核对t、df和p值是否来自同一次分析，是否为单侧检验。",
        )


def _check_df_vs_n(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    _tol: CrosscheckTolerances,
) -> None:
    df_val = row.get("df")
    n_val = row.get("N")
    if df_val is None or n_val is None or pd.isna(df_val) or pd.isna(n_val):
        return
    if n_val <= 0:
        return
    # common patterns: one-sample t-test df=n-1, independent t-test df=n1+n2-2
    if abs(df_val - (n_val - 1)) < 0.5:
        return
    if abs(df_val - (n_val - 2)) < 0.5:  # two-group with equal n
        return
    # Not an exact match for common patterns — note as low.
    add_finding(
        findings, table_name, "low",
        "自由度/样本量关系", f"行{row_idx}",
        "自由度df与样本量N的关系不匹配常见检验设计。",
        f"df={df_val:.6g}，N={n_val:.6g}（N-1={n_val - 1:.6g}，N-2={n_val - 2:.6g}）",
        "若检验设计非单样本或两独立样本等组设计，可忽略此项。",
    )


def _check_ratio_ci_p_direction(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    _tol: CrosscheckTolerances,
) -> None:
    effect = row.get("effect")
    ci_low = row.get("CI_low")
    ci_high = row.get("CI_high")
    if effect is None or ci_low is None or ci_high is None:
        return
    if any(pd.isna(v) for v in (effect, ci_low, ci_high)):
        return
    for p_col, p_raw in row.get("_p_raw", {}).items():
        parsed = parse_p_value(p_raw)
        if parsed is None:
            continue
        op, p_val = parsed
        significant = p_val < 0.05 if op in {"=", "<", "<="} else p_val <= 0.05
        ci_crosses_null = ci_low <= 1.0 <= ci_high
        if ci_crosses_null and significant:
            add_finding(
                findings, table_name, "high",
                "OR/RR/HR-CI-p一致性", f"行{row_idx}",
                "比值型效应量的95%CI包含1，但p值显示显著。",
                f"effect={effect:.6g}, CI=[{ci_low:.6g}, {ci_high:.6g}], {p_col}={p_raw}",
                "核对CI、p值和效应量是否来自同一模型；比值型指标的无效值通常为1。",
            )
        if not ci_crosses_null and not significant and op in {"=", ">", ">="}:
            add_finding(
                findings, table_name, "medium",
                "OR/RR/HR-CI-p一致性", f"行{row_idx}",
                "比值型效应量的95%CI未包含1，但p值未显示显著。",
                f"effect={effect:.6g}, CI=[{ci_low:.6g}, {ci_high:.6g}], {p_col}={p_raw}",
                "核对CI置信水平、p值精度和单双侧检验说明。",
            )
    if effect < ci_low or effect > ci_high:
        add_finding(
            findings, table_name, "medium",
            "效应量/CI方向一致性", f"行{row_idx}",
            "效应量点估计不在置信区间内。",
            f"effect={effect:.6g}, CI=[{ci_low:.6g}, {ci_high:.6g}]",
            "核对点估计、CI列和方向是否发生错列或复制错误。",
        )


def _check_mean_ci_p_direction(
    row: dict,
    row_idx: int,
    table_name: str,
    findings: list[Finding],
    _tol: CrosscheckTolerances,
) -> None:
    ci_low = row.get("CI_low")
    ci_high = row.get("CI_high")
    if ci_low is None or ci_high is None or pd.isna(ci_low) or pd.isna(ci_high):
        return
    crosses_zero = ci_low <= 0.0 <= ci_high
    for p_col, p_raw in row.get("_p_raw", {}).items():
        parsed = parse_p_value(p_raw)
        if parsed is None:
            continue
        op, p_val = parsed
        significant = p_val < 0.05 if op in {"=", "<", "<="} else p_val <= 0.05
        if crosses_zero and significant:
            add_finding(
                findings, table_name, "medium",
                "CI-p显著性方向", f"行{row_idx}",
                "CI包含0，但p值显示显著。",
                f"CI=[{ci_low:.6g}, {ci_high:.6g}], {p_col}={p_raw}",
                "若这是差值或回归系数，CI与p值结论应一致；若不是零为无效值的指标，请在方法中说明。",
            )


def _check_p_curve_weak_signal(name: str, p_values: list[float], findings: list[Finding]) -> None:
    if len(p_values) < 12:
        return
    edge = [p for p in p_values if 0.045 <= p <= 0.05]
    sig = [p for p in p_values if p < 0.05]
    if len(edge) >= 3 and len(edge) / max(len(sig), 1) >= 0.30:
        add_finding(
            findings, name, "medium",
            "边缘显著p值聚集", "p值集合",
            "多个p值集中在0.045-0.050区间。",
            f"边缘显著={len(edge)}，显著p值={len(sig)}，总p值={len(p_values)}",
            "这只能提示选择性报告或多重比较风险；需结合方法、预注册和完整结果表人工复核。",
            "该规则不判断p-hacking，只作为多重比较透明度复核线索。",
        )


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS = [
    _check_se_sd_n,
    _check_ci_centering,
    _check_ci_span_vs_se,
    _check_ci_validity,
    _check_percent_count,
    _check_p_validity,
    _check_p_vs_t,
    _check_df_vs_n,
    _check_ratio_ci_p_direction,
    _check_mean_ci_p_direction,
]


def crosscheck_table(
    name: str,
    df: pd.DataFrame,
    tolerances: CrosscheckTolerances | None = None,
) -> TableResult:
    """Run row-level mathematical cross-checks on a summary statistics table.

    Args:
        name: Table identifier for the result.
        df: DataFrame with summary statistics columns.
        tolerances: Optional tolerance thresholds.

    Returns:
        TableResult with per-row findings.
    """
    if tolerances is None:
        tolerances = CrosscheckTolerances()

    detected = _detect_columns(df)
    findings: list[Finding] = []

    p_cols: list[str] = detected.get("p") or []  # type: ignore[assignment]

    # Detect percent scale and set in tolerances
    pct_col = detected.get("percent")
    tolerances.pct_scale = _detect_percent_scale(coerce_numeric(df[pct_col])) if pct_col else 100.0

    if len(df) == 0:
        tag_findings(
            findings,
            tool_id="crosscheck",
            tool_name="交叉验证",
            module="crosscheck",
            input_type="summary_statistics_table",
            routing_reason="摘要统计表逐行数学交叉验证。",
            method_limitations="交叉验证基于统计量的数学定义（SE=SD/√N、CI=mean±t×SE等），不做结论性判定。离群值需人工复核。",
        )
        return TableResult(name=name, rows=0, columns=len(df.columns), findings=findings)

    # Build numeric series for detected columns
    numeric: dict[str, pd.Series | None] = {}
    for role in ["N", "Mean", "SD", "SE", "CI_low", "CI_high", "count", "effect", "t", "df"]:
        col = detected.get(role)
        numeric[role] = coerce_numeric(df[col]) if col else None

    pct_col_name = detected.get("percent")
    numeric["percent"] = coerce_numeric(df[pct_col_name]) if pct_col_name else None

    # Iterate rows
    for row_idx in range(len(df)):
        row: dict = {}
        for role, series in numeric.items():
            if series is not None:
                row[role] = series.iloc[row_idx]
        # raw p values (strings) for parsing
        raw_p: dict[str, str | None] = {}
        for pc in p_cols:
            raw_p[pc] = df[pc].iloc[row_idx] if pc in df.columns else None
        row["_p_raw"] = raw_p

        for check_fn in CHECK_FUNCTIONS:
            check_fn(row, row_idx + 1, name, findings, tolerances)  # 1-indexed rows

    parsed_p_values: list[float] = []
    for pc in p_cols:
        for raw in df[pc].tolist():
            parsed = parse_p_value(raw)
            if parsed is not None and parsed[0] in {"=", "<", "<="} and 0 <= parsed[1] <= 1:
                parsed_p_values.append(parsed[1])
    _check_p_curve_weak_signal(name, parsed_p_values, findings)

    if not findings:
        add_finding(
            findings, name, "info",
            "交叉验证运行记录", "摘要统计表",
            "逐行交叉验证已完成，未发现统计量内部不一致。",
            f"检查行数={len(df)}",
            "若变量类型或检验设计与假设不符，仍建议人工复核原始分析。",
        )

    tag_findings(
        findings,
        tool_id="crosscheck",
        tool_name="交叉验证",
        module="crosscheck",
        input_type="summary_statistics_table",
        routing_reason="摘要统计表逐行数学交叉验证。",
        method_limitations="交叉验证基于统计量的数学定义（SE=SD/√N、CI=mean±t×SE等），不做结论性判定。离群值需人工复核。",
    )
    return TableResult(name=name, rows=len(df), columns=len(df.columns), findings=findings)
