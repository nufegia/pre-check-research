#!/usr/bin/env python3
"""Local detector for suspicious traces in tabular research data.

The tool intentionally avoids making misconduct conclusions. It extracts or
loads tables, runs simple statistical and pattern checks, and writes a Markdown
report listing signals that need human review.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
from scipy import stats

from pcr_audit.config import DEFAULT_CONFIG


CONFIG = DEFAULT_CONFIG


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
    tool_id: str = "raw_data_rules"
    tool_name: str = "Basic Table Rules"
    module: str = "raw_observation_checks"
    input_type: str = "unknown"
    routing_reason: str = "Basic Table Rules detection process."
    method_limitations: str = "This result comes from rule-based screening; it only flags risk signals requiring review and does not constitute a data integrity verdict."
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


def clean_cell(value: Any) -> Any:
    if value is None:
        return np.nan
    if isinstance(value, str):
        value = value.strip()
        return np.nan if value == "" else value
    return value


def read_csv(path: Path) -> list[tuple[str, pd.DataFrame]]:
    encodings = ["utf-8-sig", "utf-8", "gb18030", "latin1"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            df = pd.read_csv(path, encoding=encoding)
            return [(path.stem, df)]
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"CSV read failed: {last_error}")


def read_excel(path: Path) -> list[tuple[str, pd.DataFrame]]:
    sheets = pd.read_excel(path, sheet_name=None)
    return [(str(name), df) for name, df in sheets.items()]


def read_docx_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    tables: list[tuple[str, pd.DataFrame]] = []
    for idx, tbl in enumerate(root.findall(".//w:tbl", ns), start=1):
        rows: list[list[str]] = []
        for tr in tbl.findall("./w:tr", ns):
            row: list[str] = []
            for tc in tr.findall("./w:tc", ns):
                texts = [node.text or "" for node in tc.findall(".//w:t", ns)]
                row.append("".join(texts).strip())
            if any(cell != "" for cell in row):
                rows.append(row)
        if not rows:
            continue
        width = max(len(r) for r in rows)
        normalized = [r + [""] * (width - len(r)) for r in rows]
        first = normalized[0]
        has_header = len(set(first)) == len(first) and any(not looks_numeric(x) for x in first)
        if has_header and len(normalized) > 1:
            df = pd.DataFrame(normalized[1:], columns=first)
        else:
            df = pd.DataFrame(normalized)
        tables.append((f"DOCX_table_{idx}", df))
    return tables


def read_pdf_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF table extraction requires pdfplumber: pip install pdfplumber") from exc

    tables: list[tuple[str, pd.DataFrame]] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            for table_no, table in enumerate(page.extract_tables() or [], start=1):
                rows = [[clean_cell(c) for c in row] for row in table if row]
                if not rows:
                    continue
                width = max(len(r) for r in rows)
                rows = [r + [np.nan] * (width - len(r)) for r in rows]
                first = ["" if pd.isna(x) else str(x) for x in rows[0]]
                has_header = len(set(first)) == len(first) and any(not looks_numeric(x) for x in first)
                if has_header and len(rows) > 1:
                    df = pd.DataFrame(rows[1:], columns=first)
                else:
                    df = pd.DataFrame(rows)
                tables.append((f"PDF_p{page_no}_table_{table_no}", df))
    return tables


def load_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return read_excel(path)
    if suffix == ".docx":
        return read_docx_tables(path)
    if suffix == ".pdf":
        return read_pdf_tables(path)
    raise RuntimeError(f"Unsupported file type: {suffix}. Please use CSV/XLSX/DOCX/PDF.")


def looks_numeric(value: Any) -> bool:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    text = str(value).strip()
    if text == "":
        return False
    text = text.replace(",", "").replace("%", "")
    try:
        float(text)
        return True
    except ValueError:
        return False


def coerce_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .replace({"": np.nan, "nan": np.nan, "None": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def numeric_columns(df: pd.DataFrame, min_numeric_ratio: float = 0.7) -> dict[str, pd.Series]:
    result: dict[str, pd.Series] = {}
    for col in df.columns:
        values = coerce_numeric(df[col])
        non_empty = df[col].notna().sum()
        if non_empty == 0:
            continue
        if values.notna().sum() / non_empty >= min_numeric_ratio:
            result[str(col)] = values
    return result


STRUCTURAL_INDEX_PATTERNS = [
    r"^id$",
    r"^no$",
    r"^num$",
    r"^number$",
    r"^index$",
    r"^order$",
    r"^row$",
    r"^item$",
    r"^item[_ ]?no$",
    r"^item[_ ]?number$",
    r"^question$",
    r"^question[_ ]?no$",
    r"^q[_ ]?no$",
    r"^seq$",
    r"^serial$",
    r"序号",
    r"编号",
    r"题号",
    r"原题号",
    r"问卷题",
    r"条目号",
    r"项目号",
    r"行号",
    r"排序",
]


def is_structural_index_column(col: str, values: pd.Series | None = None) -> bool:
    """Return True for columns that identify/order records rather than measure them."""
    name = normalize_name(col)
    raw = str(col).strip().lower()
    name_match = any(re.search(pattern, name) or re.search(pattern, raw) for pattern in STRUCTURAL_INDEX_PATTERNS)
    if not name_match:
        return False
    if values is None:
        return True
    clean = values.dropna()
    if clean.empty:
        return True
    numeric = clean.astype(float)
    integer_like = bool(np.all(np.isclose(numeric, np.round(numeric))))
    unique_share = float(numeric.nunique() / len(numeric)) if len(numeric) else 0.0
    return integer_like and unique_share >= 0.8


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
        finding.evidence_id = ""
        enrich_finding_explanation(finding)
    return findings


def enrich_finding_explanation(finding: Finding) -> None:
    """Populate user-facing interpretation fields when a detector did not."""
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
    if not finding.false_positive_risk:
        finding.false_positive_risk = "low" if finding.level == "high" else "medium"
    if not finding.evidence_id:
        finding.evidence_id = f"{finding.tool_id}:{finding.check}:{finding.target}".replace(" ", "_")
    if not finding.location:
        finding.location = finding.table
    if not finding.review_actions:
        finding.review_actions = finding.review_steps or finding.suggestion
    if not finding.confidence_basis:
        finding.confidence_basis = (
            "Generated from deterministic rules or reproducible formulas; still requires human judgment considering study design, original records, and material extraction quality."
        )


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def cap_small_sample(score: float, n: int, basis: str) -> tuple[float, str]:
    if n < 15:
        return min(score, 0.40), basis + "; small sample n<15 confidence capped at 0.40"
    return score, basis


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
    basis = ", ".join(f"{name}={value:.2g}(weight {weight:.0%})" for name, value, weight in parts)
    return score, f"{basis}; weighted total={score:.2f}"


def effect_strength(value: float, medium: float, high: float) -> float:
    if value >= high:
        return 1.0
    if value >= medium:
        return 0.7
    return 0.5


def p_value_strength(p_value: float, medium: float = 0.01, high: float = 0.001) -> float:
    if p_value <= high:
        return 1.0
    if p_value <= medium:
        return 0.7
    return 0.5


def pair_whitelisted(left: str, right: str) -> bool:
    pair = {normalize_name(left), normalize_name(right)}
    for white_left, white_right in CONFIG.column_relationship.whitelist_pairs:
        if pair == {normalize_name(white_left), normalize_name(white_right)}:
            return True
    return False


def data_rows(indexes: Iterable[Any], limit: int = 10) -> str:
    rows: list[str] = []
    for idx in list(indexes)[:limit]:
        if isinstance(idx, (int, np.integer)):
            rows.append(str(int(idx) + 1))
        else:
            rows.append(str(idx))
    return ", ".join(rows)


def compact_value(value: Any) -> str:
    if pd.isna(value):
        return "NA"
    text = str(value).replace("\n", " ").replace("|", "/").strip()
    return text if len(text) <= 60 else text[:57] + "..."


def compact_records(df: pd.DataFrame, limit: int = 3) -> str:
    if df.empty:
        return "No examples"
    pieces: list[str] = []
    for idx, row in df.head(limit).iterrows():
        cells = ", ".join(f"{col}={compact_value(value)}" for col, value in row.items())
        row_label = int(idx) + 1 if isinstance(idx, (int, np.integer)) else idx
        pieces.append(f"row {row_label}: {cells}")
    return "；".join(pieces)


def markdown_cell(value: str) -> str:
    return value.replace("\n", "<br>").replace("|", "\\|")


def normalize_name(name: Any) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"\s+", "", text)
    return text.replace("_", "").replace("-", "")


def columns_matching(df: pd.DataFrame, patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for col in df.columns:
        normalized = normalize_name(col)
        if any(re.search(pattern, normalized) for pattern in patterns):
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


def p_matches_report(computed: float, reported: tuple[str, float]) -> bool:
    op, value = reported
    if op == "<":
        return computed < value
    if op == "<=":
        return computed <= value
    if op == ">":
        return computed > value
    if op == ">=":
        return computed >= value
    if value < 0.01:
        return abs(computed - value) <= max(0.0005, value * 0.15)
    return abs(computed - value) <= 0.0055


def format_p(value: float) -> str:
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def check_table_level(table_name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    rows, cols = df.shape
    if rows == 0 or cols == 0:
        score, basis = weighted_confidence(
            [
                ("Detectable cells", 1.0, 0.60),
                ("Extraction completeness", 0.6, 0.40),
            ]
        )
        add_finding(
            findings,
            table_name,
            "high",
            "Empty table",
            "Entire table",
            "Table has no detectable data.",
            f"rows={rows}, cols={cols}",
            "Check whether file extraction failed, or try uploading original CSV/XLSX.",
            "No cells available for detection. If source is PDF/DOCX, common causes are table extraction failure or image-based tables in the document.",
            confidence_score=score,
            confidence_basis=basis,
        )
        return

    missing_rate = float(df.isna().mean().mean())
    if missing_rate >= 0.35:
        score, basis = weighted_confidence(
            [
                ("Table scale", sample_size_score(rows * max(cols, 1)), 0.25),
                ("Missing rate", effect_strength(missing_rate, 0.35, 0.55), 0.50),
                ("Column coverage", sample_size_score(cols), 0.25),
            ]
        )
        add_finding(
            findings,
            table_name,
            "medium",
            "Missing pattern",
            "Entire table",
            "Overall missing rate is high; may affect subsequent judgments.",
            f"Average missing rate={missing_rate:.1%}",
            "Check whether missing values stem from study design, data anonymization, table extraction failure, or manual deletion.",
            "Columns with most missing: "
            + "; ".join(
                f"{col}={rate:.1%}"
                for col, rate in df.isna().mean().sort_values(ascending=False).head(5).items()
            ),
            confidence_score=score,
            confidence_basis=basis,
        )

    duplicate_rows = int(df.duplicated().sum())
    if rows >= 10 and duplicate_rows >= 2 and duplicate_rows / rows >= 0.05:
        dup_samples = df[df.duplicated(keep=False)].head(6)
        dup_ratio = duplicate_rows / rows
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(rows), 0.25),
                ("Duplicate ratio", effect_strength(dup_ratio, 0.05, 0.15), 0.50),
                ("Duplicate row count", sample_size_score(duplicate_rows), 0.25),
            ]
        )
        add_finding(
            findings,
            table_name,
            "high",
            "Duplicate rows",
            "Entire table",
            "Found many fully duplicate rows.",
            f"Duplicate rows={duplicate_rows}/{rows} ({duplicate_rows / rows:.1%})",
            "Review original records to confirm whether copy-paste, duplicate entry, or sample ID reuse occurred.",
            f"Duplicate row examples (row numbers start from 1, excluding header): {compact_records(dup_samples)}",
            confidence_score=score,
            confidence_basis=basis,
        )

    duplicated_cols: list[tuple[str, str]] = []
    columns = list(df.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            if df[left].equals(df[right]):
                duplicated_cols.append((str(left), str(right)))
    if duplicated_cols:
        pairs = "; ".join(f"{a} = {b}" for a, b in duplicated_cols[:5])
        score, basis = weighted_confidence(
            [
                ("Row count adequacy", sample_size_score(rows), 0.40),
                ("Exact match", 1.0, 0.45),
                ("Matched column pair count", sample_size_score(len(duplicated_cols)), 0.15),
            ]
        )
        add_finding(
            findings,
            table_name,
            "medium",
            "Duplicate columns",
            "Entire table",
            "Found columns with identical content.",
            pairs,
            "Confirm whether these columns should be identical; if not, prioritize checking for table copy or column mapping errors.",
            f"Identical column pair count={len(duplicated_cols)}. Example pairs: {pairs}",
            confidence_score=score,
            confidence_basis=basis,
        )


def normalized_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def comparable_similarity(left: pd.Series, right: pd.Series) -> tuple[int, int, float, list[str]]:
    same = 0
    comparable = 0
    diffs: list[str] = []
    for col, left_value in left.items():
        right_value = right[col]
        left_text = normalized_cell(left_value)
        right_text = normalized_cell(right_value)
        if not left_text or not right_text:
            continue
        comparable += 1
        if left_text == right_text:
            same += 1
        elif len(diffs) < 5:
            diffs.append(str(col))
    ratio = same / comparable if comparable else 0.0
    return same, comparable, ratio, diffs


def row_tokens(row: pd.Series) -> set[str]:
    return {f"{col}={normalized_cell(value)}" for col, value in row.items() if normalized_cell(value)}


def candidate_row_pairs(df: pd.DataFrame, max_pairs: int) -> tuple[list[tuple[int, int]], int]:
    rows = len(df)
    all_pair_count = rows * (rows - 1) // 2
    if all_pair_count <= max_pairs:
        return [(left, right) for left in range(rows) for right in range(left + 1, rows)], all_pair_count

    buckets: dict[tuple[str, ...], list[int]] = {}
    token_size = max(1, CONFIG.similarity.row_bucket_token_size)
    for idx in range(rows):
        tokens = sorted(row_tokens(df.iloc[idx]))
        if len(tokens) < CONFIG.similarity.min_comparable_fields:
            continue
        for start in range(0, max(len(tokens) - token_size + 1, 1)):
            key = tuple(tokens[start : start + token_size])
            if len(key) == token_size:
                buckets.setdefault(key, []).append(idx)

    pairs: set[tuple[int, int]] = set()
    for indexes in sorted(buckets.values(), key=len):
        if len(indexes) < 2:
            continue
        unique_indexes = sorted(set(indexes))
        for pos, left in enumerate(unique_indexes):
            for right in unique_indexes[pos + 1 :]:
                pairs.add((left, right))
                if len(pairs) >= max_pairs:
                    return sorted(pairs), all_pair_count
    return sorted(pairs), all_pair_count


def check_high_similarity_rows(table_name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    rows, cols = df.shape
    if rows < 2 or cols < 3:
        return
    max_pairs = CONFIG.similarity.max_row_pairs
    hits: list[tuple[float, int, int, int, int, list[str]]] = []
    pairs, all_pair_count = candidate_row_pairs(df, max_pairs)
    checked = 0
    for left_idx, right_idx in pairs:
        checked += 1
        same, comparable, ratio, diffs = comparable_similarity(df.iloc[left_idx], df.iloc[right_idx])
        if (
            comparable >= CONFIG.similarity.min_comparable_fields
            and ratio >= CONFIG.similarity.row_threshold_low
            and ratio < 1.0
        ):
            hits.append((ratio, left_idx, right_idx, same, comparable, diffs))
    if not hits:
        return
    hits.sort(reverse=True, key=lambda item: item[0])
    best = hits[0][0]
    level = "high" if best >= CONFIG.similarity.row_threshold_high else (
        "medium" if best >= CONFIG.similarity.row_threshold_medium else "low"
    )
    sample_lines = []
    for ratio, left_idx, right_idx, same, comparable, diffs in hits[:8]:
        diff_text = f", diff fields: {', '.join(diffs)}" if diffs else ""
        sample_lines.append(f"row {left_idx + 1}↔row {right_idx + 1}: {same}/{comparable} cols identical ({ratio:.1%}){diff_text}")
    score, basis = weighted_confidence(
        [
            ("Sample size adequacy", sample_size_score(rows), 0.25),
                (
                    "Highest similarity",
                    1.0 if best >= CONFIG.similarity.row_threshold_high else 0.7 if best >= CONFIG.similarity.row_threshold_medium else 0.5,
                    0.45,
                ),
                ("Hit rarity", 1.0 if len(hits) <= 3 else 0.7 if len(hits) <= 10 else 0.5, 0.30),
        ]
    )
    score, basis = cap_small_sample(score, rows, basis)
    add_finding(
        findings,
        table_name,
        level,
        "Highly similar rows",
        "Entire table",
        "Found non-identical but highly similar row pairs.",
        "；".join(sample_lines),
        "Check each pair whether differing fields have experimental logic support; if many fields are identical with only a few differing, review original records.",
        f"Performed candidate bucket comparison across table rows; total pair space {all_pair_count} pairs, max {max_pairs} pairs checked; this run checked {checked} pairs, {len(hits)} pairs hit.",
        confidence_score=score,
        confidence_basis=basis,
    )


def check_high_similarity_cols(table_name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    if df.shape[0] < 5 or df.shape[1] < 2:
        return
    columns = [col for col in df.columns if not is_structural_index_column(str(col), coerce_numeric(df[col]))]
    hits: list[tuple[float, str, str, int, int, list[int]]] = []
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            if df[left].equals(df[right]):
                continue
            left_values = df[left]
            right_values = df[right]
            comparable_mask = left_values.notna() & right_values.notna()
            comparable = int(comparable_mask.sum())
            if comparable < CONFIG.similarity.min_comparable_rows:
                continue
            left_numeric = coerce_numeric(left_values[comparable_mask])
            right_numeric = coerce_numeric(right_values[comparable_mask])
            numeric_mask = left_numeric.notna() & right_numeric.notna()
            if int(numeric_mask.sum()) / comparable >= 0.90:
                denominator = np.maximum(
                    np.maximum(np.abs(left_numeric[numeric_mask]), np.abs(right_numeric[numeric_mask])),
                    1e-12,
                )
                relative_diff = np.abs(left_numeric[numeric_mask] - right_numeric[numeric_mask]) / denominator
                same_mask = pd.Series(False, index=left_values[comparable_mask].index)
                same_mask.loc[numeric_mask[numeric_mask].index] = (
                    relative_diff <= CONFIG.similarity.numeric_relative_tolerance
                ).to_numpy()
            else:
                same_mask = left_values[comparable_mask].astype(str).str.strip() == right_values[comparable_mask].astype(str).str.strip()
            same = int(same_mask.sum())
            ratio = same / comparable if comparable else 0.0
            if ratio >= CONFIG.similarity.col_threshold_medium:
                diff_rows = [int(idx) + 1 for idx in same_mask[~same_mask].index[:5]]
                hits.append((ratio, left, right, same, comparable, diff_rows))
    if not hits:
        return
    hits.sort(reverse=True, key=lambda item: item[0])
    best = hits[0][0]
    level = "high" if best >= CONFIG.similarity.col_threshold_high else "medium"
    sample_lines = []
    for ratio, left, right, same, comparable, diff_rows in hits[:8]:
        diff_text = f", diff rows: {', '.join(map(str, diff_rows))}" if diff_rows else ""
        sample_lines.append(f"{left}↔{right}: {same}/{comparable} rows identical ({ratio:.1%}){diff_text}")
    score, basis = weighted_confidence(
        [
            ("Sample size adequacy", sample_size_score(df.shape[0]), 0.25),
            ("Highest similarity", 1.0 if best >= CONFIG.similarity.col_threshold_high else 0.7, 0.50),
            ("Hit rarity", 1.0 if len(hits) <= 2 else 0.7 if len(hits) <= 6 else 0.5, 0.25),
        ]
    )
    score, basis = cap_small_sample(score, df.shape[0], basis)
    add_finding(
        findings,
        table_name,
        level,
        "Highly similar columns",
        "Entire table",
        "Found non-identical but highly similar column pairs.",
        "；".join(sample_lines),
        "Review original records for differing rows; confirm whether the two columns are independent measurements, legitimate derivations, or copy-with-partial-edit.",
        f"Compared {len(columns)} columns pairwise; {len(hits)} pairs hit with similarity >=90%.",
        confidence_score=score,
        confidence_basis=basis,
    )


def terminal_digit(value: float) -> int | None:
    if not np.isfinite(value):
        return None
    text = f"{value:.12g}"
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return int(digits[-1])


def decimal_places(value: Any) -> int | None:
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    if "e" in text.lower():
        try:
            text = f"{float(text):.12f}".rstrip("0").rstrip(".")
        except ValueError:
            return None
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1].rstrip("%"))


def check_terminal_digits(
    table_name: str, col: str, values: pd.Series, findings: list[Finding]
) -> None:
    clean = values.dropna().astype(float)
    if len(clean) < 30:
        return
    digits = [d for d in (terminal_digit(v) for v in clean) if d is not None]
    if len(digits) < 30:
        return
    counts = np.array([digits.count(i) for i in range(10)])
    chi2, p_value = stats.chisquare(counts)
    max_digit = int(np.argmax(counts))
    max_share = float(counts.max() / counts.sum())
    if p_value < 0.01 and max_share >= 0.22:
        distribution = ", ".join(f"{i}:{int(counts[i])}" for i in range(10))
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(digits)), 0.30),
                ("Chi-square significance", p_value_strength(float(p_value)), 0.35),
                ("Max terminal digit share", effect_strength(max_share, 0.22, 0.30), 0.35),
            ]
        )
        add_finding(
            findings,
            table_name,
            "medium",
            "Terminal digit distribution",
            col,
            "Terminal digit distribution is significantly uneven.",
            f"n={len(digits)}, chi-square p={p_value:.3g}, digit {max_digit} share {max_share:.1%}",
            "Check whether this column underwent uniform rounding, threshold truncation, formula generation, or shows signs of manual number fabrication.",
            f"0-9 terminal digit counts: {distribution}. Natural measurement data typically does not concentrate on a few terminal digits long-term, unless fixed precision, thresholds, or batch processing rules exist.",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_decimal_precision(
    table_name: str, col: str, raw: pd.Series, values: pd.Series, findings: list[Finding]
) -> None:
    mask = values.notna()
    if mask.sum() < 20:
        return
    places = [decimal_places(x) for x in raw[mask]]
    places = [p for p in places if p is not None]
    if len(places) < 20:
        return
    counts = Counter(places)
    place, count = counts.most_common(1)[0]
    share = count / len(places)
    if share >= 0.9 and place >= 2:
        distribution = ", ".join(f"{k}dp:{v}" for k, v in sorted(counts.items()))
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(places)), 0.30),
                ("Uniform decimal place share", effect_strength(share, 0.90, 0.98), 0.50),
                ("Precision digits", 1.0 if place >= 3 else 0.7, 0.20),
            ]
        )
        add_finding(
            findings,
            table_name,
            "low",
            "Decimal place pattern",
            col,
            "Decimal places in this column are highly uniform.",
            f"{place} decimal places account for {share:.1%}",
            "This may just be formatting; if this column should come from raw measurements, check whether it was batch-generated by formula or over-tidied.",
            f"Decimal place distribution: {distribution}. If this is a formatted publication table, it may be normal; if this is unprocessed raw data, confirm instrument precision or export format.",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_arithmetic_sequences(
    table_name: str, col: str, values: pd.Series, findings: list[Finding]
) -> None:
    clean = values.dropna().astype(float)
    if len(clean) < 8:
        return
    diffs = np.diff(clean.to_numpy())
    if len(diffs) < 7:
        return
    rounded = np.round(diffs, 10)
    counts = Counter(rounded)
    step, count = counts.most_common(1)[0]
    share = count / len(rounded)
    if count >= 7 and share >= 0.7 and abs(float(step)) > 0:
        matching = np.where(rounded == step)[0]
        start = int(matching[0])
        sample_pos = list(range(start, min(start + 6, len(clean))))
        sample = ", ".join(
            f"row {int(clean.index[pos]) + 1}={clean.iloc[pos]:.6g}" for pos in sample_pos
        )
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(clean)), 0.25),
                ("Fixed step share", effect_strength(share, 0.70, 0.90), 0.50),
                ("Consecutive segment length", sample_size_score(count + 1), 0.25),
            ]
        )
        score, basis = cap_small_sample(score, len(clean), basis)
        add_finding(
            findings,
            table_name,
            "high",
            "Arithmetic/fixed step",
            col,
            "Observing current row order, this column shows clear fixed-step changes.",
            f"Consecutive difference {float(step):.6g} appears {count}/{len(rounded)} times ({share:.1%})",
            "Check whether row order is meaningful; if not a gradient produced by study design, prioritize reviewing original record sources.",
            f"Trigger logic: consecutive row differences are heavily repeated. Sample segments: {sample}. If this column is not a design variable like time, dose, serial number, or standard curve, fixed steps may indicate formula fill or manual construction.",
            confidence_score=score,
            confidence_basis=basis,
        )

    zero_runs = longest_run(np.isclose(diffs, 0))
    if zero_runs >= 6:
        zero_positions = np.where(np.isclose(diffs, 0))[0]
        start = int(zero_positions[0]) if len(zero_positions) else 0
        sample_pos = list(range(start, min(start + 6, len(clean))))
        sample = ", ".join(
            f"row {int(clean.index[pos]) + 1}={clean.iloc[pos]:.6g}" for pos in sample_pos
        )
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(clean)), 0.25),
                ("Consecutive repeat length", sample_size_score(zero_runs + 1), 0.45),
                ("Repeat segment share", effect_strength((zero_runs + 1) / len(clean), 0.30, 0.60), 0.30),
            ]
        )
        score, basis = cap_small_sample(score, len(clean), basis)
        add_finding(
            findings,
            table_name,
            "medium",
            "Consecutive repeated values",
            col,
            "This column has long consecutive repeat segments.",
            f"Longest consecutive repeat difference length={zero_runs}",
            "Confirm whether consecutive repeats come from group design, detection limits, copy-fill, or data entry errors.",
            f"Sample segments: {sample}. Need to confirm whether these consecutive identical values come from real detection limits, group assignments, missing value encoding, or copy-fill.",
            confidence_score=score,
            confidence_basis=basis,
        )


def longest_run(flags: Iterable[bool]) -> int:
    best = current = 0
    for flag in flags:
        if flag:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def check_dominant_values(
    table_name: str, col: str, values: pd.Series, findings: list[Finding]
) -> None:
    clean = values.dropna()
    if len(clean) < 20:
        return
    counts = clean.round(12).value_counts()
    top_value = counts.index[0]
    share = float(counts.iloc[0] / len(clean))
    if share >= 0.5 and clean.nunique() > 1:
        hit_rows = clean[clean.round(12) == top_value].index
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(clean)), 0.30),
                ("Top value share", effect_strength(share, 0.50, 0.75), 0.50),
                ("Value diversity", 1.0 if clean.nunique() >= 5 else 0.6, 0.20),
            ]
        )
        add_finding(
            findings,
            table_name,
            "medium",
            "High frequency value",
            col,
            "A single value appears with disproportionately high frequency.",
            f"Value {top_value} appears {counts.iloc[0]}/{len(clean)} times ({share:.1%})",
            "Check whether this value is a default, detection limit, missing value encoding, copy-fill, or genuine concentration.",
            f"High-frequency value row examples: {data_rows(hit_rows)}. If this value represents a detection limit, default fill, or missing encoding, it should be documented in the data dictionary.",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_outliers(table_name: str, col: str, values: pd.Series, findings: list[Finding]) -> None:
    clean = values.dropna().astype(float)
    if len(clean) < 15:
        return
    median = float(np.median(clean))
    mad = float(stats.median_abs_deviation(clean, scale="normal"))
    if mad == 0:
        return
    robust_z = np.abs((clean - median) / mad)
    outliers = int((robust_z > 3.5).sum())
    if outliers >= 2 and outliers / len(clean) >= 0.05:
        sample = robust_z[robust_z > 3.5].sort_values(ascending=False).head(5)
        sample_text = "; ".join(
            f"row {int(idx) + 1}: value={clean.loc[idx]:.6g}, robust_z={z:.2f}" for idx, z in sample.items()
        )
        outlier_ratio = outliers / len(clean)
        max_z = float(sample.iloc[0]) if len(sample) else 0.0
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(clean)), 0.30),
                ("Outlier ratio", effect_strength(outlier_ratio, 0.05, 0.15), 0.35),
                ("Max robust Z", effect_strength(max_z, 3.5, 6.0), 0.35),
            ]
        )
        score, basis = cap_small_sample(score, len(clean), basis)
        add_finding(
            findings,
            table_name,
            "low",
            "Outliers",
            col,
            "Found multiple outliers with high robust Z-scores.",
            f"Outliers={outliers}/{len(clean)}, median={median:.6g}, MAD={mad:.6g}",
            "Outliers require confirmation against lab records whether they are genuine extreme values, unit errors, or data entry errors.",
            f"Outlier examples: {sample_text}",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_benford(table_name: str, col: str, values: pd.Series, findings: list[Finding]) -> None:
    clean = values.dropna().astype(float)
    clean = clean[np.isfinite(clean) & (clean > 0)]
    if len(clean) < 50:
        return
    if clean.max() / max(clean.min(), 1e-12) < 100:
        return
    first_digits: list[int] = []
    for value in clean:
        text = f"{value:.12g}".lstrip("0.")
        match = re.search(r"[1-9]", text)
        if match:
            first_digits.append(int(match.group(0)))
    if len(first_digits) < 50:
        return
    observed = np.array([first_digits.count(i) for i in range(1, 10)])
    expected_probs = np.array([math.log10(1 + 1 / d) for d in range(1, 10)])
    expected = expected_probs * observed.sum()
    chi2 = float(((observed - expected) ** 2 / expected).sum())
    p_value = float(stats.chi2.sf(chi2, df=8))
    if p_value < 0.01:
        distribution = ", ".join(f"{i}:{int(observed[i - 1])}" for i in range(1, 10))
        magnitude_span = float(clean.max() / max(clean.min(), 1e-12))
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(first_digits)), 0.30),
                ("Benford fit span", effect_strength(math.log10(magnitude_span), 2.0, 3.0), 0.30),
                ("Chi-square significance", p_value_strength(p_value), 0.40),
            ]
        )
        add_finding(
            findings,
            table_name,
            "low",
            "First digit distribution",
            col,
            "First digit distribution deviates from Benford expectation.",
            f"n={len(first_digits)}，chi-square p={p_value:.3g}",
            "Benford only suits natural data spanning multiple orders of magnitude; assess applicability first, then treat as weak signal review.",
            f"First digit counts: {distribution}. This check only suits positive data spanning multiple orders of magnitude; not suitable for proportions, scores, truncated ranges, or small-sample experimental data.",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_column_linear_transform(
    table_name: str,
    num_cols: dict[str, pd.Series],
    findings: list[Finding],
) -> None:
    cols = [(col, values) for col, values in num_cols.items() if not is_structural_index_column(col, values)]
    hits: list[tuple[float, str, str, float, float, int]] = []
    max_pairs = CONFIG.column_relationship.max_pairs
    checked = 0
    for i, (left, left_values) in enumerate(cols):
        for right, right_values in cols[i + 1 :]:
            if checked >= max_pairs:
                break
            if pair_whitelisted(left, right):
                continue
            checked += 1
            rows = pd.DataFrame({"x": left_values, "y": right_values}).dropna()
            if len(rows) < CONFIG.linear_transform.min_rows:
                continue
            if np.allclose(rows["x"], rows["y"], equal_nan=False):
                continue
            if float(rows["x"].std(ddof=0)) <= 1e-12:
                continue
            try:
                slope, intercept = np.polyfit(rows["x"].to_numpy(dtype=float), rows["y"].to_numpy(dtype=float), 1)
            except Exception:
                continue
            predicted = slope * rows["x"] + intercept
            ss_res = float(np.sum((rows["y"] - predicted) ** 2))
            ss_tot = float(np.sum((rows["y"] - float(rows["y"].mean())) ** 2))
            if ss_tot <= 1e-12:
                continue
            r2 = 1.0 - ss_res / ss_tot
            if r2 >= CONFIG.linear_transform.r2_threshold_medium:
                hits.append((float(r2), left, right, float(slope), float(intercept), len(rows)))
        if checked >= max_pairs:
            break
    if not hits:
        return
    hits.sort(reverse=True, key=lambda item: item[0])
    for r2, left, right, slope, intercept, n in hits[:8]:
        level = "high" if r2 >= CONFIG.linear_transform.r2_threshold_high else "medium"
        fixed_diff = abs(slope - 1.0) <= CONFIG.linear_transform.fixed_diff_slope_tolerance and abs(intercept) > 1e-9
        if fixed_diff and r2 >= CONFIG.linear_transform.r2_threshold_high:
            level = "high"
        slope_score = 0.5 if abs(slope) <= 0.01 or abs(slope - 1.0) <= 0.01 else 1.0
        fit_score = 1.0 if r2 >= CONFIG.linear_transform.r2_threshold_high else 0.7
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(n), 0.25),
                ("Goodness of fit", fit_score, 0.50),
                ("Slope deviation from special values", slope_score, 0.25),
            ]
        )
        score, basis = cap_small_sample(score, n, basis)
        relation = "Fixed difference pattern; " if fixed_diff else ""
        add_finding(
            findings,
            table_name,
            level,
            "Inter-column linear transform",
            f"{left} -> {right}",
            "Near-perfect linear transform relationship exists between two columns.",
            f"{relation}Valid rows N={n}, R²={r2:.6f}, regression: {right} = {slope:.6g} × {left} + {intercept:.6g}",
            "Confirm whether the two columns should have a functional relationship in the study design; if they should not be linearly related, review original measurement records.",
            f"Fitted linear models to all numeric column pairs; current pair R² exceeds {CONFIG.linear_transform.r2_threshold_medium:.3f} threshold; max {max_pairs} pairs checked, actual {checked} pairs checked.",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_column_high_correlation(
    table_name: str,
    num_cols: dict[str, pd.Series],
    findings: list[Finding],
) -> None:
    cols = [(col, values) for col, values in num_cols.items() if not is_structural_index_column(col, values)]
    if len(cols) < 2:
        return
    pair_count = 0
    high_count = 0
    correlations: list[float] = []
    hits: list[tuple[float, float, str, str, int]] = []
    checked = 0
    max_pairs = min(CONFIG.correlation.max_column_pairs, CONFIG.column_relationship.max_pairs)
    for i, (left, left_values) in enumerate(cols):
        for right, right_values in cols[i + 1 :]:
            if checked >= max_pairs:
                break
            if pair_whitelisted(left, right):
                continue
            checked += 1
            rows = pd.DataFrame({"x": left_values, "y": right_values}).dropna()
            if len(rows) < CONFIG.correlation.min_rows:
                continue
            if np.allclose(rows["x"], rows["y"], equal_nan=False):
                continue
            if float(rows["x"].std(ddof=0)) <= 1e-12 or float(rows["y"].std(ddof=0)) <= 1e-12:
                continue
            pearson = float(rows["x"].corr(rows["y"], method="pearson"))
            spearman = float(rows["x"].corr(rows["y"], method="spearman"))
            if not np.isfinite(pearson):
                continue
            abs_r = abs(pearson)
            correlations.append(abs_r)
            pair_count += 1
            if abs_r >= CONFIG.correlation.r_threshold_medium:
                high_count += 1
                hits.append((abs_r, abs(spearman) if np.isfinite(spearman) else float("nan"), left, right, len(rows)))
        if checked >= max_pairs:
            break
    hits.sort(reverse=True, key=lambda item: item[0])
    high_ratio = high_count / pair_count if pair_count else 0.0
    for abs_r, abs_spearman, left, right, n in hits[:8]:
        level = "high" if abs_r >= CONFIG.correlation.r_threshold_high else "medium"
        corr_score = 1.0 if abs_r >= CONFIG.correlation.r_threshold_high else 0.7
        rarity_score = 1.0 if high_ratio < CONFIG.correlation.table_ratio_threshold_medium else 0.6
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(n), 0.30),
                ("Correlation coefficient strength", corr_score, 0.40),
                ("Correlation pair rarity", rarity_score, 0.30),
            ]
        )
        score, basis = cap_small_sample(score, n, basis)
        add_finding(
            findings,
            table_name,
            level,
            "Inter-column high correlation",
            f"{left} ↔ {right}",
            "Abnormally high correlation exists between two columns.",
            f"Pearson |r|={abs_r:.4f}, Spearman |ρ|={abs_spearman:.4f}, valid rows N={n}",
            "Confirm the expected relationship between the two variables in the study design; if they should be independent, investigate whether they originate from the same data generation template.",
            "High correlation is a statistical dependency signal; requires judgment combining domain knowledge, variable semantics, and collection procedures.",
            confidence_score=score,
            confidence_basis=basis,
        )
    if pair_count and high_ratio >= CONFIG.correlation.table_ratio_threshold_medium:
        level = "high" if high_ratio >= CONFIG.correlation.table_ratio_threshold_high else "medium"
        median_r = float(np.median(correlations)) if correlations else 0.0
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(min(len(values.dropna()) for _, values in cols)), 0.30),
                ("High correlation ratio", 1.0 if high_ratio >= CONFIG.correlation.table_ratio_threshold_high else 0.7, 0.50),
                ("Matrix median correlation", 1.0 if median_r >= CONFIG.correlation.table_median_r_threshold else 0.6, 0.20),
            ]
        )
        add_finding(
            findings,
            table_name,
            level,
            "Correlation matrix structure anomaly",
            "Entire table",
            "Correlation among numeric columns is globally elevated.",
            f"Total {len(cols)} numeric columns; out of {pair_count} comparable pairs, {high_count} pairs ({high_ratio:.1%}) |r|>={CONFIG.correlation.r_threshold_medium:.2f}, median |r|={median_r:.4f}",
            "Verify whether measurement sources for all numeric variables are independent; if claimed to come from different instruments, methods, or time points, highly consistent correlation structure requires explanation.",
            "Globally elevated table correlation matrix may come from common-source variables, total/subscore relationships, or systematic construction; requires human review combined with semantics.",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_rare_categories(table_name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    rows = len(df)
    if rows < CONFIG.categorical.min_rows:
        return
    for col in df.columns:
        col_name = str(col)
        if is_structural_index_column(col_name, coerce_numeric(df[col])):
            continue
        series = df[col].dropna()
        if len(series) < CONFIG.categorical.min_rows:
            continue
        numeric = coerce_numeric(series)
        unique_count = int(series.nunique(dropna=True))
        is_low_cardinality_integer = (
            numeric.notna().sum() / len(series) >= 0.9
            and unique_count <= 20
            and bool(np.all(np.isclose(numeric.dropna(), np.round(numeric.dropna()))))
        )
        if pd.api.types.is_numeric_dtype(df[col]) and not is_low_cardinality_integer:
            continue
        if unique_count < CONFIG.categorical.min_categories or unique_count > CONFIG.categorical.max_categories:
            continue
        counts = series.astype(str).str.strip().value_counts()
        rare = counts[(counts <= CONFIG.categorical.rare_count) & (counts / len(series) < CONFIG.categorical.rare_ratio)]
        if rare.empty:
            continue
        level = "high" if len(rare) >= 2 or (int(rare.iloc[0]) == 1 and rare.iloc[0] / len(series) < 0.01) else "medium"
        rare_text = "；".join(f"{category}: {count}/{len(series)}({count/len(series):.1%})" for category, count in rare.items())
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(series)), 0.30),
                ("Category rarity", 1.0 if level == "high" else 0.7, 0.40),
                ("Category count fit", 1.0 if 3 <= unique_count <= 10 else 0.7, 0.30),
            ]
        )
        add_finding(
            findings,
            table_name,
            level,
            "Low-frequency category",
            col_name,
            "Isolated categories with extremely low frequency exist in categorical or low-cardinality variables.",
            rare_text,
            "Verify sample sources for isolated categories; confirm whether genuine rare cases, coding errors, cleaning residuals, or manual additions.",
            f"Total categories={unique_count}; distribution: " + "; ".join(f"{k}={v}" for k, v in counts.head(12).items()),
            confidence_score=score,
            confidence_basis=basis,
        )
def check_ordinal_extreme_concentration(table_name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
    for col in df.columns:
        col_name = str(col)
        if is_structural_index_column(col_name, coerce_numeric(df[col])):
            continue
        values = coerce_numeric(df[col]).dropna()
        if len(values) < CONFIG.ordinal.min_rows:
            continue
        if not np.all(np.isclose(values, np.round(values))):
            continue
        unique_values = sorted(float(value) for value in values.unique())
        if len(unique_values) <= 2 or len(unique_values) > CONFIG.ordinal.max_unique_values:
            continue
        name_suggests_ordinal = any(token in col_name.lower() for token in CONFIG.ordinal.keywords) or any(
            token in col_name for token in CONFIG.ordinal.keywords
        )
        if not name_suggests_ordinal and len(unique_values) > 10:
            continue
        counts = values.value_counts().sort_index()
        min_value = unique_values[0]
        max_value = unique_values[-1]
        extreme_count = int(counts.get(min_value, 0) + counts.get(max_value, 0))
        extreme_ratio = extreme_count / len(values)
        full_range = list(range(int(min_value), int(max_value) + 1)) if float(min_value).is_integer() and float(max_value).is_integer() else []
        missing_middle = [
            value
            for value in full_range[1:-1]
            if value not in {int(item) for item in unique_values}
        ]
        if extreme_ratio < CONFIG.ordinal.extreme_ratio_medium and not missing_middle:
            continue
        if extreme_ratio >= CONFIG.ordinal.extreme_ratio_high and missing_middle:
            level = "high"
        elif extreme_ratio >= CONFIG.ordinal.extreme_ratio_high or missing_middle:
            level = "medium"
        else:
            level = "low"
        score, basis = weighted_confidence(
            [
                ("Sample size adequacy", sample_size_score(len(values)), 0.25),
                ("Extreme-end concentration", 1.0 if extreme_ratio >= CONFIG.ordinal.extreme_ratio_high else 0.6, 0.45),
                ("Middle gap", 1.0 if missing_middle else 0.5, 0.30),
            ]
        )
        distribution = "；".join(f"{value:g}: {int(count)}({count/len(values):.1%})" for value, count in counts.items())
        gap_text = f", missing middle values={missing_middle}" if missing_middle else ""
        add_finding(
            findings,
            table_name,
            level,
            "Ordinal variable extreme concentration",
            col_name,
            "Ordinal or discrete variable values concentrated at extremes or showing middle gaps.",
            f"Extreme ends combined={extreme_ratio:.1%}{gap_text}",
            "Verify typical distribution of scale/ordinal variable in comparable populations, and spot-check original records for extreme-value samples.",
            f"Value distribution: {distribution}",
            confidence_score=score,
            confidence_basis=basis,
        )


def check_missing_by_group(table_name: str, df: pd.DataFrame, findings: list[Finding]) -> None:
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
                score, basis = weighted_confidence(
                    [
                        ("Sample size adequacy", sample_size_score(len(frame)), 0.30),
                        ("Missing rate difference", 1.0 if spread >= 0.50 else 0.7, 0.50),
                        ("Highest missing rate", 1.0 if float(rates.max()) >= 0.50 else 0.7, 0.20),
                    ]
                )
                add_finding(
                    findings,
                    table_name,
                    "medium",
                    "Missing concentrated by group",
                    f"{group_col} -> {value_col}",
                    "Missing values show large distribution differences across groups.",
                    evidence,
                    "Review whether missingness is caused by experimental procedures, inclusion/exclusion criteria, instrument batches, or subsequent exclusion, and document in the paper.",
                    f"Max group missing rate difference={spread:.1%}.",
                    confidence_score=score,
                    confidence_basis=basis,
                )
                return
def check_summary_stat_table(
    table_name: str,
    df: pd.DataFrame,
    num_cols: dict[str, pd.Series],
    findings: list[Finding],
) -> None:
    """Check internal consistency of already-summarized statistical tables."""
    if df.empty or not num_cols:
        return

    n_col = first_existing(
        columns_matching(df, [r"^n$", r"^sample[_ ]?size$", r"^cases?$", r"^number$", r"samplesize", r"样本量", r"例数", r"人数"])
    )
    mean_col = first_existing(columns_matching(df, [r"^mean$", r"^means$", r"^average$", r"均值", r"平均值", r"平均数"]))
    sd_col = first_existing(columns_matching(df, [r"^sd$", r"^std$", r"^stdev$", r"标准差", r"stdev"]))
    se_col = first_existing(columns_matching(df, [r"^se$", r"^sem$", r"^standard[_ ]?error$", r"标准误", r"standarderror"]))
    ci_low_col = first_existing(columns_matching(df, [r"cilow", r"cilower", r"lowerci", r"lcl", r"^lower$", r"下限", r"95%ci下"]))
    ci_high_col = first_existing(columns_matching(df, [r"cihigh", r"ciupper", r"upperci", r"ucl", r"^upper$", r"上限", r"95%ci上"]))
    p_cols = columns_matching(df, [r"^p$", r"p[_ ]?value", r"pvalue", r"^pval", r"p值"])
    t_col = first_existing(columns_matching(df, [r"^t$", r"t[_ ]?value", r"tvalue", r"t统计", r"tstat"]))
    f_col = first_existing(columns_matching(df, [r"^f$", r"f[_ ]?value", r"fvalue", r"f统计", r"fstat"]))
    chi_col = first_existing(columns_matching(df, [r"chi", r"χ", r"^chisq$", r"x2", r"chisquare", r"卡方"]))
    df_col = first_existing(columns_matching(df, [r"^df$", r"^dof$", r"自由度", r"degreeoffreedom"]))
    df1_col = first_existing(columns_matching(df, [r"df1", r"^df[_ ]?1$", r"分子自由度"]))
    df2_col = first_existing(columns_matching(df, [r"df2", r"^df[_ ]?2$", r"分母自由度"]))

    check_basic_summary_values(table_name, df, num_cols, findings, n_col, sd_col, se_col, p_cols)
    if n_col and sd_col and se_col:
        check_se_sd_n(table_name, df, n_col, sd_col, se_col, findings)
    if mean_col and se_col and ci_low_col and ci_high_col:
        check_ci_mean_se(table_name, df, mean_col, se_col, ci_low_col, ci_high_col, n_col, findings)
    if n_col:
        check_percent_count_consistency(table_name, df, num_cols, n_col, findings)
    if p_cols:
        check_reported_p_values(
            table_name,
            df,
            p_cols,
            t_col,
            f_col,
            chi_col,
            df_col,
            df1_col,
            df2_col,
            findings,
        )


def check_basic_summary_values(
    table_name: str,
    df: pd.DataFrame,
    num_cols: dict[str, pd.Series],
    findings: list[Finding],
    n_col: str | None,
    sd_col: str | None,
    se_col: str | None,
    p_cols: list[str],
) -> None:
    if n_col:
        n = coerce_numeric(df[n_col])
        bad = n[n.notna() & ((n <= 0) | (np.abs(n - np.round(n)) > 1e-9))]
        if not bad.empty:
            add_finding(
                findings,
                table_name,
                "high",
                "Summary table N anomaly",
                n_col,
                "Sample size column contains non-positive or non-integer values.",
                f"Abnormal cells={len(bad)}",
                "Sample size should usually be a positive integer; check for column identification errors, unit errors, or table entry errors.",
                f"Examples: {'; '.join(f'row {int(i)+1}: {v:g}' for i, v in bad.head(8).items())}",
            )

    for label, col in [("SD", sd_col), ("SE", se_col)]:
        if not col:
            continue
        values = coerce_numeric(df[col])
        bad = values[values.notna() & (values < 0)]
        if not bad.empty:
            add_finding(
                findings,
                table_name,
                "high",
                f"Summary table {label} anomaly",
                col,
                f"{label} column contains negative values.",
                f"Abnormal cells={len(bad)}",
                f"{label} should not be negative; check summary table generation formula or data entry.",
                f"Examples: {'; '.join(f'row {int(i)+1}: {v:g}' for i, v in bad.head(8).items())}",
            )

    for p_col in p_cols:
        parsed = df[p_col].map(parse_p_value)
        bad_indexes = []
        exact_extreme = []
        for idx, parsed_value in parsed.items():
            if parsed_value is None:
                continue
            op, value = parsed_value
            if value < 0 or value > 1:
                bad_indexes.append((idx, op, value))
            if op == "=" and value in {0, 1}:
                exact_extreme.append((idx, value))
        if bad_indexes:
            add_finding(
                findings,
                table_name,
                "high",
                "P-value range anomaly",
                p_col,
                "P-value column contains values outside [0, 1].",
                f"Abnormal cells={len(bad_indexes)}",
                "P-values must mathematically be between 0 and 1; check statistical software output or data entry.",
                "Examples: "
                + "; ".join(f"row {int(i)+1}: {op}{v:g}" for i, op, v in bad_indexes[:8]),
            )
        if exact_extreme:
            add_finding(
                findings,
                table_name,
                "low",
                "P-value format anomaly",
                p_col,
                "P-values contain exact 0 or 1.",
                f"Exact extremes={len(exact_extreme)}",
                "Many statistical packages output very small p-values as 0.000, but publication tables should usually report p<0.001.",
                "Examples: " + "; ".join(f"row {int(i)+1}: p={v:g}" for i, v in exact_extreme[:8]),
            )


def check_se_sd_n(
    table_name: str,
    df: pd.DataFrame,
    n_col: str,
    sd_col: str,
    se_col: str,
    findings: list[Finding],
) -> None:
    n = coerce_numeric(df[n_col])
    sd = coerce_numeric(df[sd_col])
    se = coerce_numeric(df[se_col])
    rows = pd.DataFrame({"n": n, "sd": sd, "se": se}).dropna()
    if rows.empty:
        return
    rows = rows[(rows["n"] > 1) & (rows["sd"] >= 0) & (rows["se"] >= 0)]
    if rows.empty:
        return
    expected = rows["sd"] / np.sqrt(rows["n"])
    tolerance = np.maximum(0.02, np.abs(expected) * 0.08)
    bad = rows[np.abs(rows["se"] - expected) > tolerance]
    if len(bad) >= 1 and len(bad) / len(rows) >= 0.15:
        sample = []
        for idx, row in bad.head(8).iterrows():
            exp = row["sd"] / math.sqrt(row["n"])
            sample.append(
                f"row {int(idx)+1}: n={row['n']:.6g}, SD={row['sd']:.6g}, SE={row['se']:.6g}, expected≈{exp:.6g}"
            )
        add_finding(
            findings,
            table_name,
            "high",
            "SE/SD/N consistency",
            f"{sd_col}, {se_col}, {n_col}",
            "SE inconsistent with SD/sqrt(N).",
            f"Inconsistent rows={len(bad)}/{len(rows)}",
            "If the SE column is truly standard error, review the statistical script; it may also be mislabeled, actually containing SD, CI, or other measures.",
            "Examples: " + "; ".join(sample),
        )


def check_ci_mean_se(
    table_name: str,
    df: pd.DataFrame,
    mean_col: str,
    se_col: str,
    low_col: str,
    high_col: str,
    n_col: str | None,
    findings: list[Finding],
) -> None:
    rows = pd.DataFrame(
        {
            "mean": coerce_numeric(df[mean_col]),
            "se": coerce_numeric(df[se_col]),
            "low": coerce_numeric(df[low_col]),
            "high": coerce_numeric(df[high_col]),
            "n": coerce_numeric(df[n_col]) if n_col else np.nan,
        }
    ).dropna(subset=["mean", "se", "low", "high"])
    if rows.empty:
        return

    inverted = rows[rows["low"] > rows["high"]]
    if not inverted.empty:
        add_finding(
            findings,
            table_name,
            "high",
            "CI interval anomaly",
            f"{low_col}, {high_col}",
            "CI lower bound greater than upper bound.",
            f"Abnormal rows={len(inverted)}",
            "Check whether CI lower/upper column order is reversed, or column misalignment occurred during table extraction.",
            "Examples: "
            + "; ".join(
                f"row {int(i)+1}: low={r['low']:.6g}, high={r['high']:.6g}"
                for i, r in inverted.head(8).iterrows()
            ),
        )

    valid_ci = rows[rows["low"] <= rows["high"]]
    if valid_ci.empty:
        return

    centered_diff = np.abs(valid_ci["mean"] - ((valid_ci["low"] + valid_ci["high"]) / 2))
    half_width = np.abs(valid_ci["high"] - valid_ci["low"]) / 2
    not_centered = valid_ci[centered_diff > np.maximum(0.03, half_width * 0.12)]
    if len(not_centered) >= 1 and len(not_centered) / len(rows) >= 0.15:
        add_finding(
            findings,
            table_name,
            "medium",
            "CI center consistency",
            f"{mean_col}, {low_col}, {high_col}",
            "Mean is not near the center of the confidence interval.",
            f"Abnormal rows={len(not_centered)}/{len(rows)}",
            "Symmetric mean CI should normally be centered on the mean; if using asymmetric intervals, back-transformed values, or ratio measures, this must be explained in methods.",
            "Examples: "
            + "; ".join(
                f"row {int(i)+1}: mean={r['mean']:.6g}, CI center={(r['low']+r['high'])/2:.6g}"
                for i, r in not_centered.head(8).iterrows()
            ),
        )

    ratio = half_width / valid_ci["se"].replace(0, np.nan)
    valid = valid_ci[ratio.notna() & np.isfinite(ratio)]
    if valid.empty:
        return
    ratio = ratio.loc[valid.index]
    far = valid[(ratio < 1.2) | (ratio > 3.2)]
    if len(far) >= 1 and len(far) / len(valid) >= 0.15:
        add_finding(
            findings,
            table_name,
            "medium",
            "CI/SE consistency",
            f"{se_col}, {low_col}, {high_col}",
            "CI half-width to SE ratio does not match common 95% CI range.",
            f"Abnormal rows={len(far)}/{len(valid)}",
            "95% CI half-width is usually about 1.96*SE; small-sample t-distribution would be larger; if ratio is too small or too large, check CI, SE, or confidence level.",
            "Examples: "
            + "; ".join(
                f"row {int(i)+1}: half_width={abs((r['high']-r['low'])/2):.6g}, SE={r['se']:.6g}, ratio={ratio.loc[i]:.3g}"
                for i, r in far.head(8).iterrows()
            ),
        )


def check_percent_count_consistency(
    table_name: str,
    df: pd.DataFrame,
    num_cols: dict[str, pd.Series],
    n_col: str,
    findings: list[Finding],
) -> None:
    percent_cols = [
        col
        for col in df.columns
        if "%" in str(col) or "percent" in normalize_name(col) or "percentage" in normalize_name(col) or "prop" in str(col)
    ]
    if not percent_cols:
        return
    count_cols = [
        col
        for col in num_cols
        if col != n_col
        and col not in percent_cols
        and not any(token in normalize_name(col) for token in ["mean", "sd", "std", "se", "sem", "ci", "pvalue"])
        and not any(token in str(col) for token in ["mean", "average", "sd", "se", "upper", "lower"])
    ]
    n = coerce_numeric(df[n_col])
    for pct_col in percent_cols[:6]:
        pct = coerce_numeric(df[pct_col])
        best: tuple[str, pd.DataFrame, pd.Series] | None = None
        for count_col in count_cols[:12]:
            count = coerce_numeric(df[count_col])
            rows = pd.DataFrame({"n": n, "count": count, "pct": pct}).dropna()
            rows = rows[(rows["n"] > 0) & (rows["count"] >= 0) & (rows["pct"] >= 0)]
            if len(rows) < 3:
                continue
            expected = rows["count"] / rows["n"] * 100
            diff = np.abs(rows["pct"] - expected)
            median_diff = float(diff.median())
            if best is None or median_diff < float(best[2].median()):
                best = (count_col, rows, diff)
        if best is None:
            continue
        count_col, rows, diff = best
        bad = rows[diff > 1.0]
        if len(bad) >= 1 and len(bad) / len(rows) >= 0.2:
            add_finding(
                findings,
                table_name,
                "medium",
                "Percent/count consistency",
                f"{count_col}, {pct_col}, {n_col}",
                "Percentage inconsistent with count/N back-calculation.",
                f"Inconsistent rows={len(bad)}/{len(rows)}, tolerance=1 percentage point",
                "If the percentage column corresponds to this count column, check rounding, denominator selection, or table entry; if not corresponding, this item can be ignored.",
                "Examples: "
                + "; ".join(
                    f"row {int(i)+1}: count={r['count']:.6g}, N={r['n']:.6g}, table %={r['pct']:.6g}, expected≈{r['count']/r['n']*100:.2f}%"
                    for i, r in bad.head(8).iterrows()
                ),
            )


def check_reported_p_values(
    table_name: str,
    df: pd.DataFrame,
    p_cols: list[str],
    t_col: str | None,
    f_col: str | None,
    chi_col: str | None,
    df_col: str | None,
    df1_col: str | None,
    df2_col: str | None,
    findings: list[Finding],
) -> None:
    for p_col in p_cols[:4]:
        p_parsed = df[p_col].map(parse_p_value)
        if t_col and df_col:
            rows = pd.DataFrame(
                {
                    "stat": coerce_numeric(df[t_col]),
                    "df": coerce_numeric(df[df_col]),
                    "p": p_parsed,
                }
            ).dropna()
            compare_computed_p(
                table_name,
                rows,
                f"{t_col}, {df_col}, {p_col}",
                "t-test p-value consistency",
                lambda r: float(2 * stats.t.sf(abs(r["stat"]), r["df"])),
                findings,
            )
        if f_col and df1_col and df2_col:
            rows = pd.DataFrame(
                {
                    "stat": coerce_numeric(df[f_col]),
                    "df1": coerce_numeric(df[df1_col]),
                    "df2": coerce_numeric(df[df2_col]),
                    "p": p_parsed,
                }
            ).dropna()
            compare_computed_p(
                table_name,
                rows,
                f"{f_col}, {df1_col}, {df2_col}, {p_col}",
                "F-test p-value consistency",
                lambda r: float(stats.f.sf(r["stat"], r["df1"], r["df2"])),
                findings,
            )
        if chi_col and df_col:
            rows = pd.DataFrame(
                {
                    "stat": coerce_numeric(df[chi_col]),
                    "df": coerce_numeric(df[df_col]),
                    "p": p_parsed,
                }
            ).dropna()
            compare_computed_p(
                table_name,
                rows,
                f"{chi_col}, {df_col}, {p_col}",
                "Chi-square p-value consistency",
                lambda r: float(stats.chi2.sf(r["stat"], r["df"])),
                findings,
            )


def compare_computed_p(
    table_name: str,
    rows: pd.DataFrame,
    target: str,
    check_name: str,
    compute,
    findings: list[Finding],
) -> None:
    if rows.empty:
        return
    bad: list[tuple[Any, float, tuple[str, float]]] = []
    usable = 0
    for idx, row in rows.iterrows():
        reported = row["p"]
        if not isinstance(reported, tuple):
            continue
        try:
            computed = compute(row)
        except Exception:
            continue
        if not np.isfinite(computed):
            continue
        usable += 1
        if not p_matches_report(computed, reported):
            bad.append((idx, computed, reported))
    if usable == 0:
        return
    if len(bad) >= 1 and len(bad) / usable >= 0.15:
        add_finding(
            findings,
            table_name,
            "high",
            check_name,
            target,
            "Back-calculated p-value from table statistics inconsistent with reported p-value.",
            f"Inconsistent rows={len(bad)}/{usable}",
            "Prioritize checking whether statistic, degrees of freedom, one/two-tailed test, and p-value columns match; such inconsistencies often come from copied tables, manual number changes, or mixed statistical conventions.",
            "Examples: "
            + "; ".join(
                f"row {int(idx)+1}: back-calc p={format_p(computed)}, reported p={op}{value:g}"
                for idx, computed, (op, value) in bad[:8]
            ),
        )


def numeric_precision(value: Any) -> int:
    places = decimal_places(value)
    return max(0, places or 0)


def rounded_interval(value: float, precision: int) -> tuple[float, float]:
    half = 0.5 * 10 ** (-precision)
    return value - half + 1e-12, value + half - 1e-12


def grim_possible(mean_value: float, n_value: int, precision: int, scale_min: int, scale_max: int) -> bool:
    low, high = rounded_interval(mean_value, precision)
    min_sum = n_value * scale_min
    max_sum = n_value * scale_max
    first = math.ceil(low * n_value)
    last = math.floor(high * n_value)
    return max(first, min_sum) <= min(last, max_sum)


def max_discrete_sd(n_value: int, mean_value: float, scale_min: int, scale_max: int) -> float:
    if n_value <= 1:
        return 0.0
    low_count = max(0, min(n_value, round((scale_max - mean_value) / (scale_max - scale_min) * n_value)))
    values = np.array([scale_min] * low_count + [scale_max] * (n_value - low_count), dtype=float)
    if len(values) != n_value:
        return 0.0
    return float(np.std(values, ddof=1))


def analyze_grim_grimmer_rules(
    name: str,
    df: pd.DataFrame,
    input_type: str = "likert_or_integer_scale_summary",
) -> TableResult:
    df = prepare_table(df)
    findings: list[Finding] = []
    n_col = first_existing(
        columns_matching(df, [r"^n$", r"^sample[_ ]?size$", r"^cases?$", r"^number$", r"samplesize", r"样本量", r"例数", r"人数"])
    )
    mean_col = first_existing(columns_matching(df, [r"^mean$", r"均值", r"平均值", r"平均数", r"score", r"评分", r"量表"]))
    sd_col = first_existing(columns_matching(df, [r"^sd$", r"^std$", r"^stdev$", r"标准差", r"stdev"]))
    if not n_col or not mean_col:
        return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)

    n_values = coerce_numeric(df[n_col])
    mean_values = coerce_numeric(df[mean_col])
    scale_min = 1
    scale_max = 5
    bad_grim: list[str] = []
    bad_boundary: list[str] = []
    for idx in df.index:
        n_raw = n_values.loc[idx]
        mean_raw = mean_values.loc[idx]
        if pd.isna(n_raw) or pd.isna(mean_raw) or n_raw <= 0 or abs(n_raw - round(n_raw)) > 1e-9:
            continue
        n_int = int(round(float(n_raw)))
        mean_float = float(mean_raw)
        precision = numeric_precision(df.loc[idx, mean_col])
        if not grim_possible(mean_float, n_int, precision, scale_min, scale_max):
            bad_grim.append(
                f"row {int(idx)+1}: N={n_int}, mean={mean_float:g}, default integer scale range={scale_min}-{scale_max}"
            )
        if sd_col:
            sd_value = coerce_numeric(pd.Series([df.loc[idx, sd_col]])).iloc[0]
            if pd.notna(sd_value) and sd_value >= 0:
                max_sd = max_discrete_sd(n_int, mean_float, scale_min, scale_max)
                if max_sd and float(sd_value) > max_sd + 10 ** (-(precision + 1)):
                    bad_boundary.append(
                        f"row {int(idx)+1}: N={n_int}, mean={mean_float:g}, SD={float(sd_value):g}, max feasible SD≈{max_sd:.4g}"
                    )

    if bad_grim:
        add_finding(
            findings,
            name,
            "high",
            "GRIM mean feasibility",
            f"{mean_col}, {n_col}",
            "Under discrete integer score conditions, some means and sample sizes are mathematically incompatible.",
            f"Failed rows={len(bad_grim)}",
            "Verify scale range, sample size, rounding rules, and original scores; if the variable is not integer scores, disable the GRIM/GRIMMER tool set.",
            "Examples: " + "; ".join(bad_grim[:8]),
        )
    if bad_boundary:
        add_finding(
            findings,
            name,
            "medium",
            "GRIMMER/SD boundary",
            f"{mean_col}, {sd_col}, {n_col}",
            "Under discrete score conditions, some SDs exceed rough feasible boundaries determined by mean and scale range.",
            f"Boundary anomaly rows={len(bad_boundary)}",
            "This is a conservative boundary check, not equivalent to full SPRITE enumeration; recommend human confirmation of scale range before review.",
            "Examples: " + "; ".join(bad_boundary[:8]),
        )

    tag_findings(
        findings,
        "discrete_summary_feasibility_python",
        "Python discrete summary feasibility rules",
        "discrete_summary_feasibility",
        input_type,
        "Discrete summary feasibility checks are for basic CLI scenarios; statistical consistency is primarily based on R scrutiny output.",
        "This Python function provides lightweight feasibility checks; full GRIM/GRIMMER/DEBIT review is based on R scrutiny output.",
    )
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)


def prepare_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    return df.map(clean_cell)


def analyze_raw_data_rules(name: str, df: pd.DataFrame, input_type: str = "raw_observation_table") -> TableResult:
    df = prepare_table(df)
    findings: list[Finding] = []
    check_table_level(name, df, findings)
    check_high_similarity_rows(name, df, findings)
    check_high_similarity_cols(name, df, findings)
    num_cols = numeric_columns(df)
    for col, values in num_cols.items():
        if is_structural_index_column(col, values):
            continue
        raw = df[col] if col in df.columns else pd.Series(dtype=object)
        check_dominant_values(name, col, values, findings)
        check_terminal_digits(name, col, values, findings)
        check_benford(name, col, values, findings)
        check_decimal_precision(name, col, raw, values, findings)
        check_arithmetic_sequences(name, col, values, findings)
        check_outliers(name, col, values, findings)
    check_column_linear_transform(name, num_cols, findings)
    check_column_high_correlation(name, num_cols, findings)
    check_rare_categories(name, df, findings)
    check_ordinal_extreme_concentration(name, df, findings)
    check_missing_by_group(name, df, findings)
    tag_findings(
        findings,
        "raw_data_rules",
        "Basic Table Rules",
        "raw_observation_checks",
        input_type,
        "User selected, and the current table can be scanned as raw observations/general table with rule-based checks.",
        "Basic rules detect anomaly patterns such as duplicates, missing values, digit distribution, inter-column relationships, fixed steps, outliers, and high-frequency fill values; normal study design, instrument thresholds, or data cleaning may also trigger.",
    )
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)


def analyze_table(name: str, df: pd.DataFrame) -> TableResult:
    df = prepare_table(df)
    findings = analyze_raw_data_rules(name, df).findings
    tag_findings(
        findings,
        "raw_data_rules",
        "Basic Table Rules",
        "raw_observation_checks",
        "unknown",
        "Basic Table Rules will run current built-in raw observation table checks.",
        "Basic Table Rules detect data patterns requiring human review; specific interpretation requires combining study design and original records.",
    )
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)


def overall_level(findings: list[Finding]) -> str:
    risk_findings = [finding for finding in findings if finding.level in {"high", "medium", "low"}]
    if not risk_findings:
        return "low"
    score = max(LEVEL_SCORE[f.level] for f in risk_findings)
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


def render_markdown(source: Path, results: list[TableResult], extraction_notes: list[str]) -> str:
    all_findings = [finding for result in results for finding in result.findings]
    level = overall_level(all_findings)
    counts = Counter(f.level for f in all_findings)
    lines = [
        "# Data Audit Report",
        "",
        "## Key Findings",
        "",
        f"- File: `{source.name}`",
        f"- Overall risk: {LEVEL_LABEL[level]}",
        f"- Tables examined: {len(results)}",
        f"- Risk signals: High {counts['high']} / Medium {counts['medium']} / Low {counts['low']} / Info {counts['info']}",
        "",
        "> This report only identifies anomaly patterns and artifact signals in data; it does not constitute a data integrity verification conclusion. High-risk items indicate priority for reviewing original records, lab notebooks, or statistical scripts.",
        "",
    ]
    if extraction_notes:
        lines += ["## Extraction Notes", ""]
        lines += [f"- {note}" for note in extraction_notes]
        lines.append("")

    lines += ["## Table Overview", "", "| Table | Rows | Columns | H | M | L |", "|---|---:|---:|---:|---:|---:|"]
    for result in results:
        counter = Counter(f.level for f in result.findings)
        lines.append(
            f"| {result.name} | {result.rows} | {result.columns} | {counter['high']} | {counter['medium']} | {counter['low']} |"
        )
    lines.append("")

    lines += ["## Finding List", ""]
    if not all_findings:
        lines += ["No obvious anomalous patterns found. Manual review against original records, study design, and statistical scripts is still recommended.", ""]
    else:
        ordered = sorted(all_findings, key=lambda f: LEVEL_SCORE[f.level], reverse=True)
        lines += [
            "| Risk | Table | Check | Target | Finding | Evidence | Suggestion |",
            "|---|---|---|---|---|---|---|",
        ]
        for f in ordered:
            lines.append(
                f"| {LEVEL_LABEL[f.level]} | {markdown_cell(f.table)} | {markdown_cell(f.check)} | {markdown_cell(f.target)} | {markdown_cell(f.summary)} | {markdown_cell(f.evidence)} | {markdown_cell(f.suggestion)} |"
            )
        lines.append("")

        lines += ["## Finding Details", ""]
        for idx, f in enumerate(ordered, start=1):
            lines += [
                f"### {idx}. {LEVEL_LABEL[f.level]} Risk: {f.check} ({f.target})",
                "",
                f"- Table: {f.table}",
                f"- Finding: {f.summary}",
                f"- Trigger evidence: {f.evidence}",
            ]
            if f.detail:
                lines.append(f"- Detail: {f.detail}")
            lines += [
                f"- Review suggestion: {f.suggestion}",
                "",
            ]

    lines += [
        "## Checks Run",
        "",
        "- Fully duplicate rows, fully duplicate columns",
        "- 高度重复行、高度重复列",
        "- 缺失比例与缺失模式",
        "- 高频默认值/复制填充值",
        "- 末位数字分布异常",
        "- 列间线性变换、列间过高相关性、相关矩阵结构异常",
        "- 低频类别、有序变量极端集中",
        "- 小数位数过度整齐",
        "- 等差数列、固定步长、连续重复值",
        "- 稳健离群值（MAD）",
        "- Benford 首位数字分布（仅在数据规模和数量级满足时启用）",
        "- 缺失值集中于分组",
        "- 统计汇总表内部一致性：N、SD、SE、CI、百分比、p 值",
        "- t/F/卡方统计量与报告 p 值反算一致性（检测到对应列时启用）",
        "",
        "## 下一步复核动作",
        "",
        "1. 优先打开高风险项涉及的原始数据行、实验日志和统计脚本。",
        "2. 对中风险项确认是否来自实验设计、仪器阈值、批量格式化或表格抽取误差。",
        "3. 若输入来自 PDF/DOCX，建议补充原始 CSV/XLSX 后重新检测。",
    ]
    return "\n".join(lines) + "\n"


def save_json(path: Path, source: Path, results: list[TableResult]) -> None:
    payload = {
        "source": str(source),
        "results": [
            {
                "name": result.name,
                "rows": result.rows,
                "columns": result.columns,
                "findings": [asdict(f) for f in result.findings],
            }
            for result in results
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="从 CSV/XLSX/DOCX/PDF 中提取表格并检查数据人工痕迹。"
    )
    parser.add_argument("input", help="输入文件：CSV/XLSX/DOCX/PDF")
    parser.add_argument(
        "-o",
        "--out",
        help="Markdown 报告输出路径。默认：<输入文件名>.data-trace-report.md",
    )
    parser.add_argument("--json", help="可选：同时输出 JSON 明细。")
    parser.add_argument(
        "--scenario",
        choices=["raw", "summary", "text", "image", "r-advanced"],
        default="raw",
        help="检测场景。CLI 当前支持表格类场景：raw、summary、r-advanced。",
    )
    parser.add_argument("--enable-r", action="store_true", help="启用 R 桥接检测模块。")
    parser.add_argument("--scale-min", type=int, default=1, help="R 离散量表最小值，默认 1。")
    parser.add_argument("--scale-max", type=int, default=5, help="R 离散量表最大值，默认 5。")
    parser.add_argument("--rounding-digits", type=int, default=2, help="报告均值/SD 默认四舍五入位数。")
    args = parser.parse_args(argv)

    source = Path(args.input).expanduser().resolve()
    if not source.exists():
        print(f"输入文件不存在：{source}", file=sys.stderr)
        return 2

    extraction_notes: list[str] = []
    try:
        tables = load_tables(source)
    except Exception as exc:
        print(f"读取失败：{exc}", file=sys.stderr)
        return 1

    if not tables:
        print("没有抽取到可检测表格。建议改用原始 CSV/XLSX。", file=sys.stderr)
        return 1

    if source.suffix.lower() in {".pdf", ".docx"}:
        extraction_notes.append(
            "当前输入来自文档抽取，表头、合并单元格和脚注可能影响解析；重要结论建议用原始 CSV/XLSX 复测。"
        )

    results: list[TableResult] = []
    for name, df in tables:
        if args.enable_r and args.scenario in {"summary", "r-advanced"}:
            try:
                if args.scenario == "summary":
                    from tool_system import TOOL_REGISTRY, dependency_status

                    dep_status, dep_reason = dependency_status(TOOL_REGISTRY["r_scrutiny"])
                    if dep_status != "ready":
                        raise RuntimeError(f"{dep_status}: {dep_reason}")
                    from detectors.r.adapters import run_r_scrutiny

                    results.append(run_r_scrutiny(name, df, "summary_statistics_table", args.scale_min, args.scale_max))
                else:
                    from tool_system import TOOL_REGISTRY, dependency_status

                    dep_status, dep_reason = dependency_status(TOOL_REGISTRY["r_rsprite2"])
                    if dep_status != "ready":
                        raise RuntimeError(f"{dep_status}: {dep_reason}")
                    from detectors.r.adapters import run_r_rsprite2

                    results.append(run_r_rsprite2(name, df, "likert_or_integer_scale_summary", args.scale_min, args.scale_max))
            except Exception as exc:
                text = str(exc)
                dep_status = "missing_r_package" if "missing_r_package" in text else "missing_r" if "missing_r" in text else "error"
                finding = Finding(
                    table=name,
                    level="info",
                    check="R桥接运行记录",
                    target="R 运行时",
                    summary=f"R 桥接未能完成：{exc}",
                    evidence=f"dependency_status={dep_status}",
                    detail="CLI 已保留 Python 基础表格检测结果；请检查 R、rpy2/Rscript 和 CRAN 包安装。",
                    suggestion="安装 R 包 scrutiny/rsprite2 后重试，或关闭 --enable-r。",
                    detector_runtime="r",
                    dependency_status=dep_status,
                    confidence="low",
                    false_positive_risk="low",
                )
                enrich_finding_explanation(finding)
                results.append(TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=[finding]))
        elif args.scenario in {"raw", "summary"}:
            results.append(analyze_table(name, df))
        else:
            finding = Finding(
                table=name,
                level="info",
                check="场景未运行",
                target=args.scenario,
                summary="该 CLI 场景需要 Web 上传或 R 参数配合，本次未运行检测。",
                evidence=f"scenario={args.scenario}",
                detail="image 场景请使用 Web 上传图片；r-advanced 请同时传入 --enable-r。",
                suggestion="选择 raw，或启用 --enable-r 后重试。",
            )
            enrich_finding_explanation(finding)
            results.append(TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=[finding]))
    out_path = (
        Path(args.out).expanduser().resolve()
        if args.out
        else source.with_suffix(source.suffix + ".data-trace-report.md")
    )
    out_path.write_text(render_markdown(source, results, extraction_notes), encoding="utf-8")
    if args.json:
        save_json(Path(args.json).expanduser().resolve(), source, results)
    print(f"报告已生成：{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
