#!/usr/bin/env python3
"""Local MVP for detecting suspicious traces in tabular research data.

The tool intentionally avoids making misconduct conclusions. It extracts or
loads tables, runs simple statistical and pattern checks, and writes a Markdown
report listing signals that need human review.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
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
    tool_id: str = "legacy"
    tool_name: str = "旧版综合规则"
    module: str = "legacy"
    input_type: str = "unknown"
    routing_reason: str = "旧版命令行综合检测流程。"
    method_limitations: str = "该结果来自规则筛查，只提示需要复核的风险信号，不构成数据风险校验判定。"
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
    raise RuntimeError(f"CSV 读取失败：{last_error}")


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
        tables.append((f"DOCX表格{idx}", df))
    return tables


def read_pdf_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF 表格抽取需要安装 pdfplumber：pip install pdfplumber") from exc

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
                tables.append((f"PDF第{page_no}页表格{table_no}", df))
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
    raise RuntimeError(f"暂不支持的文件类型：{suffix}。请使用 CSV/XLSX/DOCX/PDF。")


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
    r"^itemno$",
    r"^itemnumber$",
    r"^question$",
    r"^questionno$",
    r"^qno$",
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


def enrich_finding_explanation(finding: Finding) -> None:
    """Populate user-facing interpretation fields when a detector did not."""
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
        return "无样例"
    pieces: list[str] = []
    for idx, row in df.head(limit).iterrows():
        cells = ", ".join(f"{col}={compact_value(value)}" for col, value in row.items())
        row_label = int(idx) + 1 if isinstance(idx, (int, np.integer)) else idx
        pieces.append(f"行{row_label}: {cells}")
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
        add_finding(
            findings,
            table_name,
            "high",
            "空表",
            "整表",
            "表格没有可检测数据。",
            f"行数={rows}，列数={cols}",
            "核对文件是否抽取失败，或改用原始 CSV/XLSX 上传。",
            "没有任何可参与检测的单元格。若来源是 PDF/DOCX，常见原因是表格抽取失败或文档内为图片表格。",
        )
        return

    missing_rate = float(df.isna().mean().mean())
    if missing_rate >= 0.35:
        add_finding(
            findings,
            table_name,
            "medium",
            "缺失模式",
            "整表",
            "整表缺失比例较高，可能影响后续判断。",
            f"平均缺失比例={missing_rate:.1%}",
            "核对缺失是否来自实验设计、数据脱敏、表格抽取失败或人为删改。",
            "缺失最多的列："
            + "; ".join(
                f"{col}={rate:.1%}"
                for col, rate in df.isna().mean().sort_values(ascending=False).head(5).items()
            ),
        )

    duplicate_rows = int(df.duplicated().sum())
    if rows >= 10 and duplicate_rows >= 2 and duplicate_rows / rows >= 0.05:
        dup_samples = df[df.duplicated(keep=False)].head(6)
        add_finding(
            findings,
            table_name,
            "high",
            "重复行",
            "整表",
            "发现较多完全重复行。",
            f"重复行={duplicate_rows}/{rows} ({duplicate_rows / rows:.1%})",
            "回看原始记录，确认是否存在复制粘贴、重复录入或样本编号复用。",
            f"重复行样例（行号从 1 开始，不含表头）：{compact_records(dup_samples)}",
        )

    duplicated_cols: list[tuple[str, str]] = []
    columns = list(df.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            if df[left].equals(df[right]):
                duplicated_cols.append((str(left), str(right)))
    if duplicated_cols:
        pairs = "; ".join(f"{a} = {b}" for a, b in duplicated_cols[:5])
        add_finding(
            findings,
            table_name,
            "medium",
            "重复列",
            "整表",
            "发现内容完全相同的列。",
            pairs,
            "确认这些列是否本应相同；若不是，优先排查表格复制或列映射错误。",
            f"完全相同的列对数量={len(duplicated_cols)}。样例列对：{pairs}",
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
        add_finding(
            findings,
            table_name,
            "medium",
            "尾数分布",
            col,
            "末位数字分布明显不均匀。",
            f"n={len(digits)}，chi-square p={p_value:.3g}，数字 {max_digit} 占比 {max_share:.1%}",
            "核对该列是否经过统一四舍五入、阈值截断、公式生成，或存在人工编写数字的痕迹。",
            f"0-9 末位数字计数：{distribution}。自然测量数据通常不会长期集中到少数几个末位数字，除非存在固定精度、阈值或批量处理规则。",
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
        distribution = ", ".join(f"{k}位:{v}" for k, v in sorted(counts.items()))
        add_finding(
            findings,
            table_name,
            "low",
            "小数位模式",
            col,
            "该列小数位数高度一致。",
            f"{place} 位小数占 {share:.1%}",
            "这可能只是格式化结果；若该列应来自原始测量，建议检查是否由公式批量生成或过度整理。",
            f"小数位分布：{distribution}。如果这是论文整理表，可能正常；如果这是未经整理的原始观测值，则需要确认仪器精度或导出格式。",
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
            f"行{int(clean.index[pos]) + 1}={clean.iloc[pos]:.6g}" for pos in sample_pos
        )
        add_finding(
            findings,
            table_name,
            "high",
            "等差/固定步长",
            col,
            "按当前行顺序观察，该列存在明显固定步长变化。",
            f"连续差值 {float(step):.6g} 出现 {count}/{len(rounded)} 次 ({share:.1%})",
            "核对行顺序是否有意义；若不是实验设计产生的梯度，需重点复核原始记录来源。",
            f"触发逻辑：相邻两行差值大量重复。片段样例：{sample}。如果该列不是时间、剂量、编号、标准曲线等设计变量，固定步长可能提示公式填充或人工构造。",
        )

    zero_runs = longest_run(np.isclose(diffs, 0))
    if zero_runs >= 6:
        zero_positions = np.where(np.isclose(diffs, 0))[0]
        start = int(zero_positions[0]) if len(zero_positions) else 0
        sample_pos = list(range(start, min(start + 6, len(clean))))
        sample = ", ".join(
            f"行{int(clean.index[pos]) + 1}={clean.iloc[pos]:.6g}" for pos in sample_pos
        )
        add_finding(
            findings,
            table_name,
            "medium",
            "连续重复值",
            col,
            "该列存在较长连续重复片段。",
            f"最长连续重复差值长度={zero_runs}",
            "确认连续重复是否来自分组设计、检测下限、复制填充或录入错误。",
            f"片段样例：{sample}。需要确认这些连续相同值是否来自真实检测下限、分组赋值、缺失值编码，还是复制填充。",
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
        add_finding(
            findings,
            table_name,
            "medium",
            "高频数值",
            col,
            "单个数值出现比例过高。",
            f"值 {top_value} 出现 {counts.iloc[0]}/{len(clean)} 次 ({share:.1%})",
            "检查该值是否为默认值、检测下限、缺失值编码、复制填充或真实集中分布。",
            f"高频值所在行样例：{data_rows(hit_rows)}。如果该值代表检测下限、默认填充值或缺失编码，应在数据字典中说明。",
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
            f"行{int(idx) + 1}: 值={clean.loc[idx]:.6g}, robust_z={z:.2f}" for idx, z in sample.items()
        )
        add_finding(
            findings,
            table_name,
            "low",
            "离群值",
            col,
            "发现多个稳健 Z 分数较高的离群值。",
            f"离群点={outliers}/{len(clean)}，median={median:.6g}，MAD={mad:.6g}",
            "离群值需结合实验记录确认是否为真实极端值、单位错误或录入错误。",
            f"离群样例：{sample_text}",
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
        add_finding(
            findings,
            table_name,
            "low",
            "首位数字分布",
            col,
            "首位数字分布偏离 Benford 期望。",
            f"n={len(first_digits)}，chi-square p={p_value:.3g}",
            "Benford 只适合跨多个数量级的自然数据；先判断适用性，再作为弱信号复核。",
            f"首位数字计数：{distribution}。该检查只适合正数且跨多个数量级的数据，不适合比例、评分、截断范围或小样本实验数据。",
        )


def check_group_similarity(
    table_name: str,
    df: pd.DataFrame,
    num_cols: dict[str, pd.Series],
    findings: list[Finding],
) -> None:
    categorical_candidates = []
    for col in df.columns:
        unique_count = df[col].nunique(dropna=True)
        if 2 <= unique_count <= 8 and df[col].notna().sum() >= 10:
            categorical_candidates.append(str(col))
    for cat in categorical_candidates[:3]:
        groups = df[cat].astype(str)
        for num_col, values in list(num_cols.items())[:8]:
            frame = pd.DataFrame({"group": groups, "value": values}).dropna()
            grouped = [g["value"].astype(float).to_numpy() for _, g in frame.groupby("group")]
            grouped = [g for g in grouped if len(g) >= 5]
            if len(grouped) < 2:
                continue
            means = [float(np.mean(g)) for g in grouped]
            stds = [float(np.std(g, ddof=1)) for g in grouped if len(g) > 1]
            if len(stds) < 2:
                continue
            mean_cv = abs(statistics.pstdev(means) / (statistics.mean(means) or 1))
            std_cv = abs(statistics.pstdev(stds) / (statistics.mean(stds) or 1))
            if mean_cv < 0.01 and std_cv < 0.03 and len(frame) >= 20:
                group_lines = []
                for group_name, group_df in frame.groupby("group"):
                    arr = group_df["value"].astype(float)
                    group_lines.append(
                        f"{group_name}: n={len(arr)}, mean={arr.mean():.6g}, sd={arr.std(ddof=1):.6g}"
                    )
                add_finding(
                    findings,
                    table_name,
                    "medium",
                    "分组过度相似",
                    f"{cat} -> {num_col}",
                    "不同分组的均值/标准差异常接近。",
                    f"均值CV={mean_cv:.4f}，SD CV={std_cv:.4f}，分组数={len(grouped)}",
                    "核对分组是否独立生成；若理论上应有差异，需回看原始数据和分组编码。",
                    "分组统计："
                    + "; ".join(group_lines[:8])
                    + "。若这些组本应来自不同处理或不同样本来源，过度接近需要解释。",
                )


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
        columns_matching(df, [r"^n$", r"样本量", r"例数", r"人数", r"cases?", r"samplesize", r"number"])
    )
    mean_col = first_existing(columns_matching(df, [r"^mean$", r"均值", r"平均值", r"平均数"]))
    sd_col = first_existing(columns_matching(df, [r"^sd$", r"std", r"标准差", r"stdev"]))
    se_col = first_existing(columns_matching(df, [r"^se$", r"sem", r"标准误", r"standarderror"]))
    ci_low_col = first_existing(columns_matching(df, [r"cilow", r"lowerci", r"lcl", r"下限", r"95%ci下"]))
    ci_high_col = first_existing(columns_matching(df, [r"cihigh", r"upperci", r"ucl", r"上限", r"95%ci上"]))
    p_cols = columns_matching(df, [r"^p$", r"pvalue", r"p值", r"^pval"])
    t_col = first_existing(columns_matching(df, [r"^t$", r"tvalue", r"t统计", r"tstat"]))
    f_col = first_existing(columns_matching(df, [r"^f$", r"fvalue", r"f统计", r"fstat"]))
    chi_col = first_existing(columns_matching(df, [r"chi", r"χ", r"卡方", r"x2", r"chisquare"]))
    df_col = first_existing(columns_matching(df, [r"^df$", r"自由度", r"degreeoffreedom"]))
    df1_col = first_existing(columns_matching(df, [r"df1", r"分子自由度"]))
    df2_col = first_existing(columns_matching(df, [r"df2", r"分母自由度"]))

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
                "统计表N异常",
                n_col,
                "样本量列存在非正数或非整数。",
                f"异常单元格={len(bad)} 个",
                "样本量通常应为正整数；请核对是否列识别错误、单位错误或表格录入错误。",
                f"样例：{'; '.join(f'行{int(i)+1}: {v:g}' for i, v in bad.head(8).items())}",
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
                f"统计表{label}异常",
                col,
                f"{label} 列出现负数。",
                f"异常单元格={len(bad)} 个",
                f"{label} 不应为负数；请核对统计表生成公式或录入。",
                f"样例：{'; '.join(f'行{int(i)+1}: {v:g}' for i, v in bad.head(8).items())}",
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
                "P值范围异常",
                p_col,
                "p 值列存在超出 [0, 1] 的数值。",
                f"异常单元格={len(bad_indexes)} 个",
                "p 值数学上必须位于 0 到 1 之间；请核对统计软件输出或录入。",
                "样例："
                + "; ".join(f"行{int(i)+1}: {op}{v:g}" for i, op, v in bad_indexes[:8]),
            )
        if exact_extreme:
            add_finding(
                findings,
                table_name,
                "low",
                "P值格式异常",
                p_col,
                "p 值出现精确 0 或 1。",
                f"精确极值={len(exact_extreme)} 个",
                "很多统计软件会输出非常小的 p 值为 0.000，但论文表格中通常应写为 p<0.001。",
                "样例：" + "; ".join(f"行{int(i)+1}: p={v:g}" for i, v in exact_extreme[:8]),
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
                f"行{int(idx)+1}: n={row['n']:.6g}, SD={row['sd']:.6g}, SE={row['se']:.6g}, 应约={exp:.6g}"
            )
        add_finding(
            findings,
            table_name,
            "high",
            "SE/SD/N一致性",
            f"{sd_col}, {se_col}, {n_col}",
            "SE 与 SD/sqrt(N) 不一致。",
            f"不一致行={len(bad)}/{len(rows)}",
            "若表格中的 SE 确实是标准误，应回查统计脚本；也可能是列名误标，实际填的是 SD、CI 或其他指标。",
            "样例：" + "; ".join(sample),
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
            "CI区间异常",
            f"{low_col}, {high_col}",
            "置信区间下限大于上限。",
            f"异常行={len(inverted)}",
            "核对 CI 下限/上限是否列顺序写反，或表格抽取时发生错列。",
            "样例："
            + "; ".join(
                f"行{int(i)+1}: low={r['low']:.6g}, high={r['high']:.6g}"
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
            "CI中心一致性",
            f"{mean_col}, {low_col}, {high_col}",
            "均值没有位于置信区间中心附近。",
            f"异常行={len(not_centered)}/{len(rows)}",
            "对称均值 CI 通常应以均值为中心；若使用非对称区间、变换后回转或比例指标，需要在方法中说明。",
            "样例："
            + "; ".join(
                f"行{int(i)+1}: mean={r['mean']:.6g}, CI中心={(r['low']+r['high'])/2:.6g}"
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
            "CI/SE一致性",
            f"{se_col}, {low_col}, {high_col}",
            "CI 半宽与 SE 的比例不符合常见 95% CI 范围。",
            f"异常行={len(far)}/{len(valid)}",
            "95% CI 半宽通常约为 1.96*SE，小样本 t 分布会更大；若比例过小或过大，应核对 CI、SE 或置信水平。",
            "样例："
            + "; ".join(
                f"行{int(i)+1}: half_width={abs((r['high']-r['low'])/2):.6g}, SE={r['se']:.6g}, 比例={ratio.loc[i]:.3g}"
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
        if "%" in str(col) or "percent" in normalize_name(col) or "percentage" in normalize_name(col) or "比例" in str(col)
    ]
    if not percent_cols:
        return
    count_cols = [
        col
        for col in num_cols
        if col != n_col
        and col not in percent_cols
        and not any(token in normalize_name(col) for token in ["mean", "sd", "std", "se", "sem", "ci", "pvalue"])
        and not any(token in str(col) for token in ["均值", "平均", "标准差", "标准误", "上限", "下限"])
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
                "百分比/计数一致性",
                f"{count_col}, {pct_col}, {n_col}",
                "百分比与 count/N 反算结果不一致。",
                f"不一致行={len(bad)}/{len(rows)}，容差=1个百分点",
                "若百分比列对应的是该计数列，应核对四舍五入、分母选择或表格录入；若不是对应关系，可忽略该项。",
                "样例："
                + "; ".join(
                    f"行{int(i)+1}: count={r['count']:.6g}, N={r['n']:.6g}, 表内%={r['pct']:.6g}, 应约={r['count']/r['n']*100:.2f}%"
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
                "t检验P值一致性",
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
                "F检验P值一致性",
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
                "卡方P值一致性",
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
            "表内统计量反算 p 值与报告 p 值不一致。",
            f"不一致行={len(bad)}/{usable}",
            "优先核对统计量、自由度、单双侧检验和 p 值列是否匹配；这类不一致常来自复制表格、手工改数或统计口径混用。",
            "样例："
            + "; ".join(
                f"行{int(idx)+1}: 反算p={format_p(computed)}, 报告p={op}{value:g}"
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
        columns_matching(df, [r"^n$", r"样本量", r"例数", r"人数", r"cases?", r"samplesize", r"number"])
    )
    mean_col = first_existing(columns_matching(df, [r"^mean$", r"均值", r"平均值", r"平均数", r"score", r"评分", r"量表"]))
    sd_col = first_existing(columns_matching(df, [r"^sd$", r"std", r"标准差", r"stdev"]))
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
                f"行{int(idx)+1}: N={n_int}, mean={mean_float:g}, 默认整数评分范围={scale_min}-{scale_max}"
            )
        if sd_col:
            sd_value = coerce_numeric(pd.Series([df.loc[idx, sd_col]])).iloc[0]
            if pd.notna(sd_value) and sd_value >= 0:
                max_sd = max_discrete_sd(n_int, mean_float, scale_min, scale_max)
                if max_sd and float(sd_value) > max_sd + 10 ** (-(precision + 1)):
                    bad_boundary.append(
                        f"行{int(idx)+1}: N={n_int}, mean={mean_float:g}, SD={float(sd_value):g}, 最大可行SD约={max_sd:.4g}"
                    )

    if bad_grim:
        add_finding(
            findings,
            name,
            "high",
            "GRIM均值可行性",
            f"{mean_col}, {n_col}",
            "离散整数评分条件下，部分均值与样本量数学上不可同时成立。",
            f"不通过行={len(bad_grim)}",
            "核对量表范围、样本量、四舍五入规则和原始评分；若该变量不是整数评分，应关闭 GRIM/GRIMMER 工具包。",
            "样例：" + "; ".join(bad_grim[:8]),
        )
    if bad_boundary:
        add_finding(
            findings,
            name,
            "medium",
            "GRIMMER/SD边界",
            f"{mean_col}, {sd_col}, {n_col}",
            "离散评分条件下，部分 SD 超出由均值和量表范围决定的粗略可行边界。",
            f"边界异常行={len(bad_boundary)}",
            "该项是保守边界检查，不等同于完整 SPRITE 穷举；建议人工确认量表范围后复核。",
            "样例：" + "; ".join(bad_boundary[:8]),
        )

    tag_findings(
        findings,
        "r_scrutiny_legacy_python",
        "旧版 Python 离散摘要规则",
        "legacy_discrete_summary_feasibility",
        input_type,
        "命令行兼容函数保留；Web 产品化流程优先使用 R scrutiny。",
        "该旧版 Python 函数不在默认产品化路由中使用；正式统计一致性请以 R scrutiny 输出为准。",
    )
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)


def prepare_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    return df.map(clean_cell)


def analyze_raw_data_rules(name: str, df: pd.DataFrame, input_type: str = "raw_observation_table") -> TableResult:
    df = prepare_table(df)
    findings: list[Finding] = []
    check_table_level(name, df, findings)
    num_cols = numeric_columns(df)
    for col, values in num_cols.items():
        if is_structural_index_column(col, values):
            continue
        raw = df[col] if col in df.columns else pd.Series(dtype=object)
        check_dominant_values(name, col, values, findings)
        check_decimal_precision(name, col, raw, values, findings)
        check_arithmetic_sequences(name, col, values, findings)
        check_outliers(name, col, values, findings)
    check_group_similarity(name, df, num_cols, findings)
    tag_findings(
        findings,
        "raw_data_rules",
        "基础表格规则",
        "raw_observation_checks",
        input_type,
        "用户已勾选，且当前表格可作为原始观测/通用表格进行规则扫描。",
        "基础规则用于发现重复、缺失、固定步长、离群值和高频填充值等异常模式；正常实验设计、仪器阈值或数据清洗也可能触发。",
    )
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)


def analyze_digit_distribution_rules(
    name: str, df: pd.DataFrame, input_type: str = "raw_observation_table"
) -> TableResult:
    df = prepare_table(df)
    findings: list[Finding] = []
    num_cols = numeric_columns(df)
    for col, values in num_cols.items():
        if is_structural_index_column(col, values):
            continue
        check_terminal_digits(name, col, values, findings)
        check_benford(name, col, values, findings)
    tag_findings(
        findings,
        "digit_distribution",
        "数字分布检测",
        "digit_and_benford_checks",
        input_type,
        "用户已勾选，且当前表格存在可评估的数值列；每个具体检查仍会按样本量和数量级条件自动启停。",
        "尾数和 Benford 检查只适合作为弱风险信号；编号、百分比、评分、小样本或截断范围数据不应据此作强结论。",
    )
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)


def analyze_table(name: str, df: pd.DataFrame) -> TableResult:
    df = prepare_table(df)
    findings: list[Finding] = []
    for result in (
        analyze_raw_data_rules(name, df),
        analyze_digit_distribution_rules(name, df),
    ):
        findings.extend(result.findings)
    tag_findings(
        findings,
        "legacy",
        "旧版综合规则",
        "legacy_all_checks",
        "unknown",
        "命令行兼容模式会运行全部内置规则。",
        "旧版综合模式不会执行工具选择和智能路由；Web 报告请以工具包路由结果为准。",
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
        "# 数据审计报告",
        "",
        "## 结论先行",
        "",
        f"- 文件：`{source.name}`",
        f"- 总体风险：{LEVEL_CN[level]}",
        f"- 检测表格：{len(results)} 个",
        f"- 问题信号：高 {counts['high']} / 中 {counts['medium']} / 低 {counts['low']} / 提示 {counts['info']}",
        "",
        "> 本报告只识别数据中的异常模式和人工痕迹信号，不构成数据风险校验结论。高风险项表示需要优先回看原始记录、实验日志或统计脚本。",
        "",
    ]
    if extraction_notes:
        lines += ["## 解析说明", ""]
        lines += [f"- {note}" for note in extraction_notes]
        lines.append("")

    lines += ["## 表格概览", "", "| 表格 | 行数 | 列数 | 高 | 中 | 低 |", "|---|---:|---:|---:|---:|---:|"]
    for result in results:
        counter = Counter(f.level for f in result.findings)
        lines.append(
            f"| {result.name} | {result.rows} | {result.columns} | {counter['high']} | {counter['medium']} | {counter['low']} |"
        )
    lines.append("")

    lines += ["## 问题清单", ""]
    if not all_findings:
        lines += ["未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。", ""]
    else:
        ordered = sorted(all_findings, key=lambda f: LEVEL_SCORE[f.level], reverse=True)
        lines += [
            "| 风险 | 表格 | 检查项 | 对象 | 发现 | 证据 | 建议 |",
            "|---|---|---|---|---|---|---|",
        ]
        for f in ordered:
            lines.append(
                f"| {LEVEL_CN[f.level]} | {markdown_cell(f.table)} | {markdown_cell(f.check)} | {markdown_cell(f.target)} | {markdown_cell(f.summary)} | {markdown_cell(f.evidence)} | {markdown_cell(f.suggestion)} |"
            )
        lines.append("")

        lines += ["## 问题详情", ""]
        for idx, f in enumerate(ordered, start=1):
            lines += [
                f"### {idx}. {LEVEL_CN[f.level]}风险：{f.check}（{f.target}）",
                "",
                f"- 表格：{f.table}",
                f"- 发现：{f.summary}",
                f"- 触发证据：{f.evidence}",
            ]
            if f.detail:
                lines.append(f"- 详细说明：{f.detail}")
            lines += [
                f"- 复核建议：{f.suggestion}",
                "",
            ]

    lines += [
        "## 已运行检测",
        "",
        "- 完全重复行、完全重复列",
        "- 缺失比例与缺失模式",
        "- 高频默认值/复制填充值",
        "- 末位数字分布异常",
        "- 小数位数过度整齐",
        "- 等差数列、固定步长、连续重复值",
        "- 稳健离群值（MAD）",
        "- Benford 首位数字分布（仅在数据规模和数量级满足时启用）",
        "- 简单分组均值/标准差过度相似",
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
