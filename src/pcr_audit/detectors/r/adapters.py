"""Best-effort R detector adapters.

The adapters are deliberately defensive: missing R or missing CRAN packages are
handled by routing before these functions run, and any runtime/API mismatch is
reported as an info finding instead of failing the whole analysis.
"""

from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from pcr_audit.models import Finding, TableResult, enrich_finding_explanation
from pcr_audit.tool_system import TOOL_REGISTRY


def _info_finding(
    source_name: str,
    tool_id: str,
    module: str,
    summary: str,
    detail: str,
    input_type: str,
    dependency_status: str = "error",
) -> Finding:
    spec = TOOL_REGISTRY[tool_id]
    finding = Finding(
        table=source_name,
        level="info",
        check=f"{spec.display_name}运行记录",
        target="R 运行时",
        summary=summary,
        evidence=dependency_status,
        detail=detail,
        suggestion="确认 R、CRAN 包版本和输入格式后重试；本次报告已跳过该 R 模块。",
        tool_id=tool_id,
        tool_name=spec.display_name,
        module=module,
        input_type=input_type,
        routing_reason="用户已勾选 R 检测模块，且路由认为当前输入类型适用。",
        method_limitations=spec.method_limitations,
        detector_runtime="r",
        dependency_status=dependency_status,
        confidence="low",
        false_positive_risk="low",
    )
    enrich_finding_explanation(finding)
    return finding


def _run_r(script: str, args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".R", encoding="utf-8", delete=False) as handle:
        handle.write(script)
        script_path = handle.name
    try:
        return subprocess.run(["Rscript", script_path, *args], capture_output=True, text=True, timeout=timeout)
    finally:
        Path(script_path).unlink(missing_ok=True)


def _write_table(df: pd.DataFrame) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".csv", encoding="utf-8", newline="", delete=False)
    handle.close()
    df.to_csv(handle.name, index=False)
    return handle.name


def _rows_from_csv_stdout(text: str) -> list[dict[str, str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    return list(csv.DictReader(lines))


def run_r_statcheck(source_name: str, text: str, input_type: str) -> list[Finding]:
    script = r'''
args <- commandArgs(trailingOnly=TRUE)
txt_path <- args[[1]]
txt <- paste(readLines(txt_path, warn=FALSE, encoding="UTF-8"), collapse="\n")
suppressPackageStartupMessages(library(statcheck))
res <- tryCatch({
  out <- statcheck::statcheck(txt, messages=FALSE)
  if (is.list(out) && "results" %in% names(out)) out$results else out
}, error=function(e) {
  data.frame(error=conditionMessage(e), stringsAsFactors=FALSE)
})
write.csv(res, stdout(), row.names=FALSE, na="")
'''
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as handle:
        handle.write(text or "")
        txt_path = handle.name
    try:
        proc = _run_r(script, [txt_path])
    finally:
        Path(txt_path).unlink(missing_ok=True)
    spec = TOOL_REGISTRY["r_statcheck"]
    if proc.returncode != 0:
        return [_info_finding(source_name, "r_statcheck", "r_statcheck_runtime", "R statcheck 运行失败。", proc.stderr.strip(), input_type)]
    rows = _rows_from_csv_stdout(proc.stdout)
    if rows and "error" in rows[0]:
        return [_info_finding(source_name, "r_statcheck", "r_statcheck_api", "R statcheck API 调用失败。", rows[0].get("error", ""), input_type)]
    findings: list[Finding] = []
    for row in rows:
        error = str(row.get("Error", row.get("error", ""))).lower() in {"true", "1"}
        decision_error = str(row.get("Decision_Error", row.get("decision_error", ""))).lower() in {"true", "1"}
        if not (error or decision_error):
            continue
        level = "high" if decision_error else "medium"
        raw = row.get("Raw", row.get("raw", "")) or row.get("Source", "")
        finding = Finding(
            table=source_name,
            level=level,
            check="R statcheck正文统计一致性",
            target=raw[:120] or "APA统计表达式",
            summary="R statcheck 发现正文统计量与报告 p 值不一致。",
            evidence=f"报告p={row.get('Reported_P_Value', row.get('reported_p', ''))}，反算p={row.get('Computed_P_Value', row.get('computed_p', ''))}",
            detail=f"原始 R 输出字段：{row}",
            suggestion="优先核对统计量、自由度、单双侧检验和 p 值是否来自同一次分析。",
            tool_id="r_statcheck",
            tool_name=spec.display_name,
            module="r_statcheck_text",
            input_type=input_type,
            routing_reason="用户已勾选 R statcheck，且文档正文识别到 APA/NHST 统计表达式。",
            method_limitations=spec.method_limitations,
            detector_runtime="r",
            dependency_status="ready",
            confidence="high" if decision_error else "medium",
            false_positive_risk="medium",
        )
        enrich_finding_explanation(finding)
        findings.append(finding)
    if not findings:
        findings.append(_info_finding(source_name, "r_statcheck", "r_statcheck_text", "R statcheck 已运行，未发现可报告的不一致。", f"文本长度={len(text or '')}", input_type, "ready"))
    return findings


def run_r_scrutiny(name: str, df: pd.DataFrame, input_type: str, scale_min: int = 1, scale_max: int = 5) -> TableResult:
    csv_path = _write_table(df)
    script = r'''
args <- commandArgs(trailingOnly=TRUE)
csv_path <- args[[1]]
scale_min <- as.numeric(args[[2]])
scale_max <- as.numeric(args[[3]])
suppressPackageStartupMessages(library(scrutiny))
d <- read.csv(csv_path, check.names=FALSE, colClasses="character")
norm <- function(x) tolower(gsub("[ _-]", "", x))
as_num <- function(x) suppressWarnings(as.numeric(gsub(",", "", gsub("%", "", x))))
is_inconsistent <- function(x) length(x) == 1 && !is.na(x) && !as.logical(x)
cols <- names(d)
ncol <- cols[match(TRUE, norm(cols) %in% c("n", "samplesize", "cases", "样本量", "例数", "人数"))]
mcol <- cols[match(TRUE, norm(cols) %in% c("mean", "means", "均值", "均数", "平均值", "平均数"))]
sdcol <- cols[match(TRUE, norm(cols) %in% c("sd", "std", "标准差", "stdev"))]
propcol <- cols[match(TRUE, norm(cols) %in% c("proportion", "prop", "rate", "ratio", "percent", "percentage", "百分比", "比例", "率"))]
out <- data.frame(check=character(), row=integer(), status=character(), detail=character(), stringsAsFactors=FALSE)
add <- function(check, row, status, detail) {
  out <<- rbind(out, data.frame(check=check, row=row, status=status, detail=detail, stringsAsFactors=FALSE))
}
if (!is.na(ncol) && !is.na(mcol)) {
  for (i in seq_len(nrow(d))) {
    n <- as_num(d[[ncol]][i])
    m <- as_num(d[[mcol]][i])
    m_raw <- as.character(d[[mcol]][i])
    if (!is.na(n) && !is.na(m)) {
      ok <- tryCatch(suppressWarnings(scrutiny::grim(x=m_raw, n=as.integer(n), items=1)), error=function(e) NA)
      if (is_inconsistent(ok)) {
        add("GRIM", i, "inconsistent", paste0("N=", n, ", mean=", m_raw))
      } else if (length(ok) != 1 || is.na(ok)) {
        add("GRIM", i, "error", paste0("N=", n, ", mean=", m_raw, "；R scrutiny::grim 无法判断该行"))
      }
    }
  }
}
if (!is.na(ncol) && !is.na(mcol) && !is.na(sdcol)) {
  grimmer_cases <- 0
  debit_cases <- 0
  for (i in seq_len(nrow(d))) {
    n <- as_num(d[[ncol]][i])
    m <- as_num(d[[mcol]][i])
    sd <- as_num(d[[sdcol]][i])
    m_raw <- as.character(d[[mcol]][i])
    sd_raw <- as.character(d[[sdcol]][i])
    if (is.na(n) || is.na(m) || is.na(sd)) next
    grimmer_cases <- grimmer_cases + 1
    ok_g <- tryCatch(suppressWarnings(scrutiny::grimmer(x=m_raw, sd=sd_raw, n=as.integer(n), items=1)), error=function(e) NA)
    if (is_inconsistent(ok_g)) {
      add("GRIMMER", i, "inconsistent", paste0("N=", n, ", mean=", m_raw, ", SD=", sd_raw, ", scale=", scale_min, "-", scale_max))
    } else if (length(ok_g) != 1 || is.na(ok_g)) {
      add("GRIMMER", i, "error", paste0("N=", n, ", mean=", m_raw, ", SD=", sd_raw, "；R scrutiny::grimmer 无法判断该行"))
    }
    if (m >= 0 && m <= 1 && sd >= 0 && sd <= 0.5) {
      debit_cases <- debit_cases + 1
      ok_d <- tryCatch(suppressWarnings(scrutiny::debit(x=m_raw, sd=sd_raw, n=as.integer(n))), error=function(e) NA)
      if (is_inconsistent(ok_d)) {
        add("DEBIT", i, "inconsistent", paste0("N=", n, ", binary mean=", m_raw, ", SD=", sd_raw))
      } else if (length(ok_d) != 1 || is.na(ok_d)) {
        add("DEBIT", i, "error", paste0("N=", n, ", binary mean=", m_raw, ", SD=", sd_raw, "；R scrutiny::debit 无法判断该行"))
      }
    }
  }
  add("GRIMMER", 0, "ran", paste0("已自动检查 ", grimmer_cases, " 行 N/mean/SD 摘要。"))
  add("DEBIT", 0, "ran", paste0("已自动检查 ", debit_cases, " 行二元 mean/SD/N 摘要候选；非 0-1 均值或 SD>0.5 的行已跳过。"))
} else if (!is.na(ncol) && !is.na(sdcol) && !is.na(propcol)) {
  debit_cases <- 0
  for (i in seq_len(nrow(d))) {
    n <- as_num(d[[ncol]][i])
    x <- as_num(d[[propcol]][i])
    sd <- as_num(d[[sdcol]][i])
    x_raw <- as.character(d[[propcol]][i])
    sd_raw <- as.character(d[[sdcol]][i])
    if (is.na(n) || is.na(x) || is.na(sd)) next
    if (x > 1 && x <= 100) {
      x <- x / 100
      x_raw <- format(x, trim=TRUE, scientific=FALSE)
    }
    if (x >= 0 && x <= 1 && sd >= 0 && sd <= 0.5) {
      debit_cases <- debit_cases + 1
      ok_d <- tryCatch(suppressWarnings(scrutiny::debit(x=x_raw, sd=sd_raw, n=as.integer(n))), error=function(e) NA)
      if (is_inconsistent(ok_d)) {
        add("DEBIT", i, "inconsistent", paste0("N=", n, ", binary proportion=", x_raw, ", SD=", sd_raw))
      } else if (length(ok_d) != 1 || is.na(ok_d)) {
        add("DEBIT", i, "error", paste0("N=", n, ", binary proportion=", x_raw, ", SD=", sd_raw, "；R scrutiny::debit 无法判断该行"))
      }
    }
  }
  add("DEBIT", 0, "ran", paste0("已自动检查 ", debit_cases, " 行二元比例/SD/N 摘要候选。"))
}
write.csv(out, stdout(), row.names=FALSE, na="")
'''
    try:
        proc = _run_r(script, [csv_path, str(scale_min), str(scale_max)])
    finally:
        Path(csv_path).unlink(missing_ok=True)
    spec = TOOL_REGISTRY["r_scrutiny"]
    if proc.returncode != 0:
        finding = _info_finding(name, "r_scrutiny", "r_scrutiny_runtime", "R scrutiny 运行失败。", proc.stderr.strip(), input_type)
        return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=[finding])
    rows = _rows_from_csv_stdout(proc.stdout)
    findings: list[Finding] = []
    for row in rows:
        check = row.get("check", "scrutiny")
        status = row.get("status", "")
        if status == "inconsistent":
            level = "high"
            summary = f"R scrutiny 的 {check} 检查发现摘要统计在数学上不可行。"
        elif status == "error":
            level = "info"
            summary = f"R scrutiny 的 {check} 检查未能判断该行。"
        else:
            level = "info"
            summary = f"R scrutiny 记录：{check} 已自动运行。"
        finding = Finding(
            table=name,
            level=level,
            check=f"R scrutiny {check}",
            target=f"行{row.get('row', '')}",
            summary=summary,
            evidence=row.get("detail", ""),
            detail=f"R scrutiny 输出：{row}",
            suggestion="确认量表范围、四舍五入精度和变量类型；若是二元/离散摘要，回看原始计数或统计脚本。",
            tool_id="r_scrutiny",
            tool_name=spec.display_name,
            module="r_scrutiny_summary",
            input_type=input_type,
            routing_reason="用户已勾选 R scrutiny，且系统识别到摘要统计表结构。",
            method_limitations=spec.method_limitations,
            detector_runtime="r",
            dependency_status="ready",
            confidence="high" if level == "high" else "low",
            false_positive_risk="medium",
        )
        enrich_finding_explanation(finding)
        findings.append(finding)
    if not findings:
        findings.append(_info_finding(name, "r_scrutiny", "r_scrutiny_summary", "R scrutiny 已运行，未发现可报告的不一致。", f"行数={df.shape[0]}，列数={df.shape[1]}", input_type, "ready"))
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)


def run_r_rsprite2(name: str, df: pd.DataFrame, input_type: str, scale_min: int = 1, scale_max: int = 5) -> TableResult:
    spec = TOOL_REGISTRY["r_rsprite2"]
    csv_path = _write_table(df)
    script = r'''
args <- commandArgs(trailingOnly=TRUE)
csv_path <- args[[1]]
scale_min <- as.numeric(args[[2]])
scale_max <- as.numeric(args[[3]])
suppressPackageStartupMessages(library(rsprite2))
d <- read.csv(csv_path, check.names=FALSE, colClasses="character")
norm <- function(x) tolower(gsub("[ _-]", "", x))
as_num <- function(x) suppressWarnings(as.numeric(gsub(",", "", gsub("%", "", x))))
decimal_places <- function(x) {
  x <- as.character(x)
  if (is.na(x) || !grepl("\\.", x)) return(0)
  nchar(sub("^[^.]*\\.", "", x))
}
cols <- names(d)
ncol <- cols[match(TRUE, norm(cols) %in% c("n", "samplesize", "cases", "样本量", "例数", "人数"))]
mcol <- cols[match(TRUE, norm(cols) %in% c("mean", "means", "均值", "均数", "平均值", "平均数"))]
sdcol <- cols[match(TRUE, norm(cols) %in% c("sd", "std", "标准差", "stdev"))]
out <- data.frame(check=character(), row=integer(), status=character(), detail=character(), stringsAsFactors=FALSE)
add <- function(check, row, status, detail) {
  out <<- rbind(out, data.frame(check=check, row=row, status=status, detail=detail, stringsAsFactors=FALSE))
}
if (is.na(ncol) || is.na(mcol) || is.na(sdcol)) {
  add("SPRITE", 0, "skipped", "缺少 N、mean 或 SD 列，无法调用 rsprite2::set_parameters 与 find_possible_distribution。")
} else {
  cases <- 0
  for (i in seq_len(nrow(d))) {
    n <- as_num(d[[ncol]][i])
    m <- as_num(d[[mcol]][i])
    sd <- as_num(d[[sdcol]][i])
    m_raw <- as.character(d[[mcol]][i])
    sd_raw <- as.character(d[[sdcol]][i])
    if (is.na(n) || is.na(m) || is.na(sd)) next
    cases <- cases + 1
    res <- tryCatch({
      params <- rsprite2::set_parameters(
        mean=m,
        sd=sd,
        n_obs=as.integer(n),
        min_val=scale_min,
        max_val=scale_max,
        m_prec=decimal_places(m_raw),
        sd_prec=decimal_places(sd_raw)
      )
      dist <- rsprite2::find_possible_distribution(params, seed=20260517)
      if (is.list(dist)) {
        status <- ifelse(tolower(as.character(dist$outcome)) == "success", "possible", "not_found")
        detail <- paste0(
          "N=", n, ", mean=", m_raw, ", SD=", sd_raw, ", scale=", scale_min, "-", scale_max,
          ", outcome=", dist$outcome,
          ", reconstructed_mean=", signif(dist$mean, 6),
          ", reconstructed_sd=", signif(dist$sd, 6),
          ", iterations=", dist$iterations
        )
      } else {
        status <- "not_found"
        detail <- paste0("N=", n, ", mean=", m_raw, ", SD=", sd_raw, ", scale=", scale_min, "-", scale_max, "；未返回可行分布。")
      }
      list(status=status, detail=detail)
    }, error=function(e) {
      list(status="impossible", detail=paste0("N=", n, ", mean=", m_raw, ", SD=", sd_raw, ", scale=", scale_min, "-", scale_max, "；", conditionMessage(e)))
    })
    add("SPRITE", i, res$status, res$detail)
  }
  add("SPRITE", 0, "ran", paste0("已尝试对 ", cases, " 行 N/mean/SD 摘要调用 rsprite2 SPRITE 分布反推。"))
}
write.csv(out, stdout(), row.names=FALSE, na="")
'''
    try:
        proc = _run_r(script, [csv_path, str(scale_min), str(scale_max)], timeout=120)
    finally:
        Path(csv_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        finding = _info_finding(name, "r_rsprite2", "r_rsprite2_runtime", "R rsprite2 运行失败。", proc.stderr.strip(), input_type)
        return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=[finding])
    rows = _rows_from_csv_stdout(proc.stdout)
    findings: list[Finding] = []
    for row in rows:
        status = row.get("status", "")
        if status in {"impossible", "not_found"}:
            level = "high"
            summary = "R rsprite2 SPRITE 未能找到匹配报告摘要统计的离散分布。"
            confidence = "medium"
            false_positive_risk = "high"
        else:
            level = "info"
            summary = "R rsprite2 SPRITE 已实际运行。"
            confidence = "low"
            false_positive_risk = "medium"
        finding = Finding(
            table=name,
            level=level,
            check="R rsprite2 SPRITE",
            target=f"行{row.get('row', '')}",
            summary=summary,
            evidence=row.get("detail", ""),
            detail=f"R rsprite2 输出：{row}",
            suggestion="确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；SPRITE 高风险结果应由人工复核原始频数。",
            tool_id="r_rsprite2",
            tool_name=spec.display_name,
            module="r_rsprite2_sprite",
            input_type=input_type,
            routing_reason="用户选择高级 R 复核场景，且数据被识别为离散评分摘要。",
            method_limitations=spec.method_limitations,
            detector_runtime="r",
            dependency_status="ready",
            confidence=confidence,
            false_positive_risk=false_positive_risk,
        )
        enrich_finding_explanation(finding)
        findings.append(finding)
    if not findings:
        findings.append(_info_finding(name, "r_rsprite2", "r_rsprite2_sprite", "R rsprite2 已运行，但未返回可解析结果。", f"行数={df.shape[0]}，列数={df.shape[1]}", input_type, "ready"))
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)
