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
    "N":        [r"^n$", r"^sample[_ ]?size$", r"^cases?$", r"^number$", r"samplesize", r"样本量", r"例数", r"人数"],
    "Mean":     [r"^mean$", r"^means$", r"^average$", r"均值", r"均数", r"平均值", r"平均数"],
    "SD":       [r"^sd$", r"^std$", r"^stdev$", r"标准差", r"stdev"],
    "SE":       [r"^se$", r"^sem$", r"^standard[_ ]?error$", r"标准误", r"sterr"],
    "CI_low":   [r"cilow", r"cilower", r"ci[_\- ]?l", r"lcl", r"^lower$", r"置信区间下限", r"下限", r"^low$"],
    "CI_high":  [r"cihigh", r"ciupper", r"ci[_\- ]?u", r"ucl", r"^upper$", r"置信区间上限", r"上限", r"^high$"],
    "count":    [r"^count$", r"n[_\- ]?pos", r"^freq$", r"频数", r"计数"],
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


def sample_size_score(n: int) -> float:
    if n >= 100:
        return 1.0
    if n >= 60:
        return 0.8
    if n >= 30:
        return 0.6
    if n >= 15:
        return 0.4
    return 0.2


def weighted_confidence(parts: list[tuple[str, float, float]]) -> tuple[float, str]:
    total_weight = sum(weight for _, _, weight in parts) or 1.0
    score = sum(value * weight for _, value, weight in parts) / total_weight
    score = max(0.0, min(1.0, float(score)))
    basis = ", ".join(f"{name}={value:.2g} (weight {weight:.0%})" for name, value, weight in parts)
    return score, f"{basis}; weighted total={score:.2f}"


def level_confidence(level: str, row_count: int, parsable_fields: int = 2) -> tuple[float, str]:
    severity_score = {"high": 0.90, "medium": 0.70, "low": 0.50, "info": 0.20}.get(level, 0.60)
    score, basis = weighted_confidence(
        [
            ("Formula determinism", 1.0 if level != "info" else 0.4, 0.45),
            ("Table scale", sample_size_score(row_count), 0.25),
            ("Parsable fields", sample_size_score(parsable_fields * 15), 0.15),
            ("Deviation level", severity_score, 0.15),
        ]
    )
    if row_count < 15 and level != "info":
        score = min(score, 0.40)
        basis += "; small sample n<15 confidence capped at 0.40"
    return score, basis


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
    confidence_score: float | None = None,
    confidence_basis: str = "",
) -> None:
    finding = Finding(table, level, check, target, summary, evidence, detail, suggestion)
    if confidence_score is not None:
        finding.confidence_score = max(0.0, min(1.0, float(confidence_score)))
    if confidence_basis:
        finding.confidence_basis = confidence_basis
    else:
        finding.confidence_score, finding.confidence_basis = level_confidence(level, 30, 2)
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
        if not finding.confidence_basis:
            score, basis = level_confidence(finding.level, max(1, getattr(finding, "_row_count", 30)), 2)
            finding.confidence_score = score
            finding.confidence_basis = basis
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
        "SE/SD/√N consistency", f"row {row_idx}",
        f"Standard error SE inconsistent with SD/√N（deviation={rel_err:.1%}）",
        f"SE reported={se:.6g}，SD/√N={expected:.6g}，N={n:.6g}，SD={sd:.6g}",
        "Verify whether SE is standard error (not SD or CI half-width); confirm statistical script output.",
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
        "CI center consistency", f"row {row_idx}",
        f"Mean not centered in CI interval（deviation={rel_err:.1%} of CI half-width）",
        f"Mean={mean:.6g}，CI center={(ci_low + ci_high) / 2:.6g}，CI=[{ci_low:.6g}, {ci_high:.6g}]",
        "Symmetric CI should be centered on the mean; asymmetric CI must be explained in methods.",
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
        "CI width/SE consistency", f"row {row_idx}",
        f"CI width inconsistent with SE×t critical value（deviation={rel_err:.1%}）",
        f"CI width={ci_span:.6g}，2×t({df_for_t:.6g})×SE={expected_span:.6g}",
        "Verify CI confidence level (usually 95%) and whether SE corresponds.",
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
            "CI interval inverted", f"row {row_idx}",
            "CI lower bound greater than upper bound.",
            f"CI=[{ci_low:.6g}, {ci_high:.6g}], lower > upper",
            "CI column order may be reversed, or column misalignment occurred during table extraction.",
        )
        return
    mean = row.get("Mean")
    if mean is not None and not pd.isna(mean):
        eps = 1e-12 * abs(ci_high - ci_low)
        if mean < ci_low - eps or mean > ci_high + eps:
            add_finding(
                findings, table_name, "high",
                "Mean outside CI interval", f"row {row_idx}",
                "Mean not contained within the confidence interval.",
                f"Mean={mean:.6g}, CI=[{ci_low:.6g}, {ci_high:.6g}]",
                "Verify mean and CI are from the same analysis; CI may be reversed or mean may be mislabeled.",
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
        "Percent/count consistency", f"row {row_idx}",
        f"Percentage inconsistent with count/N back-calculation (diff={diff:.3f})",
        f"reported={pct:.6g}, count/N×{tol.pct_scale:.0f}={expected:.6g}, count={cnt:.6g}, N={n:.6g}",
        "Verify percentage denominator is the row N; confirm count is correct.",
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
            "P-value outside domain", f"row {row_idx}",
            f"P-value outside [0, 1] range.",
            f"Reported p-value={p_raw}（{p_col}）",
            "P-value must be between 0 and 1; may be data entry error or decimal point misplacement.",
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
            "P-value/t-statistic consistency", f"row {row_idx}",
            f"P-value inconsistent with t-statistic(df) back-calculation (diff={diff:.4f})",
            f"Reported p={p_raw} (parsed as {reported_p:.6g}), t={t_val:.6g}, df={df_val:.6g}, back-calculated p={computed_p:.6g}",
            "Verify t, df, and p-value are from the same analysis; check if one-tailed test.",
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
        "df/sample size relationship", f"row {row_idx}",
        "df and sample size N relationship does not match common test designs.",
        f"df={df_val:.6g}, N={n_val:.6g} (N-1={n_val - 1:.6g}, N-2={n_val - 2:.6g})",
        "If test design is not one-sample or two-independent-sample equal-group design, this can be ignored.",
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
                "OR/RR/HR-CI-p consistency", f"row {row_idx}",
                "Ratio-type effect size 95% CI contains 1, but p-value indicates significance.",
                f"effect={effect:.6g}, CI=[{ci_low:.6g}, {ci_high:.6g}], {p_col}={p_raw}",
                "Verify CI, p-value, and effect size are from the same model; null value for ratio-type measures is usually 1.",
            )
        if not ci_crosses_null and not significant and op in {"=", ">", ">="}:
            add_finding(
                findings, table_name, "medium",
                "OR/RR/HR-CI-p consistency", f"row {row_idx}",
                "Ratio-type effect size 95% CI does not contain 1, but p-value does not indicate significance.",
                f"effect={effect:.6g}, CI=[{ci_low:.6g}, {ci_high:.6g}], {p_col}={p_raw}",
                "Verify CI confidence level, p-value precision, and one/two-tailed test specification.",
            )
    if effect < ci_low or effect > ci_high:
        add_finding(
            findings, table_name, "medium",
            "Effect size/CI direction consistency", f"row {row_idx}",
            "Effect size point estimate not within confidence interval.",
            f"effect={effect:.6g}, CI=[{ci_low:.6g}, {ci_high:.6g}]",
            "Verify point estimate, CI columns, and direction for column misalignment or copy errors.",
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
                "CI-p significance direction", f"row {row_idx}",
                "CI contains 0, but p-value indicates significance.",
                f"CI=[{ci_low:.6g}, {ci_high:.6g}], {p_col}={p_raw}",
                "If this is a difference or regression coefficient, CI and p-value conclusions should agree; if null is not zero, explain in methods.",
            )


def _check_p_curve_weak_signal(name: str, p_values: list[float], findings: list[Finding]) -> None:
    if len(p_values) < 12:
        return
    edge = [p for p in p_values if 0.045 <= p <= 0.05]
    sig = [p for p in p_values if p < 0.05]
    if len(edge) >= 3 and len(edge) / max(len(sig), 1) >= 0.30:
        add_finding(
            findings, name, "medium",
            "Marginally significant p-value clustering", "p-value collection",
            "Multiple p-values concentrated in the 0.045-0.050 interval.",
            f"Marginally significant={len(edge)}, significant p-values={len(sig)}, total p-values={len(p_values)}",
            "This only indicates selective reporting or multiple comparison risk; requires human review combining methods, preregistration, and complete result tables.",
            "This rule does not judge p-hacking; only serves as a multiple comparison transparency review clue.",
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
            tool_name="Cross-check",
            module="crosscheck",
            input_type="summary_statistics_table",
            routing_reason="Row-level mathematical cross-check on summary statistics table.",
            method_limitations="Cross-check is based on mathematical definitions of statistics (SE=SD/√N, CI=mean±t×SE, etc.); does not make conclusive judgments. Outliers require human review.",
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
            "Cross-check run record", "Summary statistics table",
            "Row-level cross-check completed; no internal statistic inconsistencies found.",
            f"Rows checked={len(df)}",
            "If variable types or test designs do not match assumptions, manual review of original analysis is still recommended.",
        )

    tag_findings(
        findings,
        tool_id="crosscheck",
        tool_name="Cross-check",
        module="crosscheck",
        input_type="summary_statistics_table",
        routing_reason="Row-level mathematical cross-check on summary statistics table.",
        method_limitations="Cross-check is based on mathematical definitions of statistics (SE=SD/√N, CI=mean±t×SE, etc.); does not make conclusive judgments. Outliers require human review.",
    )
    return TableResult(name=name, rows=len(df), columns=len(df.columns), findings=findings)
