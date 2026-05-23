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


def _r_confidence(tool_id: str, level: str, effective_n: int, status: str = "", parse_quality: float = 1.0) -> tuple[float, str]:
    tool_score = {
        "r_statcheck": 0.85,
        "r_scrutiny": 0.90,
        "r_rsprite2": 0.75,
    }.get(tool_id, 0.70)
    status_score = {
        "decision_error": 1.0,
        "error": 0.45,
        "inconsistent": 0.95,
        "impossible": 0.85,
        "not_found": 0.80,
        "ran": 0.25,
        "skipped": 0.15,
        "ready": 0.20,
    }.get(status, 0.70 if level != "info" else 0.20)
    severity_score = {"high": 0.90, "medium": 0.70, "low": 0.45, "info": 0.20}.get(level, 0.60)
    score, basis = _weighted_confidence(
        [
            ("R package method determinism", tool_score, 0.35),
            ("Effective input volume", _sample_size_score(effective_n), 0.20),
            ("Status evidence strength", status_score, 0.25),
            ("Parse quality", parse_quality, 0.10),
            ("Risk level consistency", severity_score, 0.10),
        ]
    )
    if effective_n < 15 and level != "info":
        score = min(score, 0.40)
        basis += "; small sample n<15 confidence capped at 0.40"
    return score, basis


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
    score, basis = _r_confidence(tool_id, "info", 0, dependency_status, 0.5 if dependency_status != "ready" else 1.0)
    finding = Finding(
        table=source_name,
        level="info",
        check=f"{spec.display_name} run record",
        target="R runtime",
        summary=summary,
        evidence=dependency_status,
        detail=detail,
        suggestion="Verify R, CRAN package versions, and input format, then retry; this R module has been skipped for this report.",
        tool_id=tool_id,
        tool_name=spec.display_name,
        module=module,
        input_type=input_type,
        routing_reason="User selected R detection modules, and routing determined current input type is applicable.",
        method_limitations=spec.method_limitations,
        detector_runtime="r",
        dependency_status=dependency_status,
        confidence="low",
        confidence_score=score,
        confidence_basis=basis,
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
        return [_info_finding(source_name, "r_statcheck", "r_statcheck_runtime", "R statcheck run failed.", proc.stderr.strip(), input_type)]
    rows = _rows_from_csv_stdout(proc.stdout)
    if rows and "error" in rows[0]:
        return [_info_finding(source_name, "r_statcheck", "r_statcheck_api", "R statcheck API call failed.", rows[0].get("error", ""), input_type)]
    findings: list[Finding] = []
    for row in rows:
        error = str(row.get("Error", row.get("error", ""))).lower() in {"true", "1"}
        decision_error = str(row.get("Decision_Error", row.get("decision_error", ""))).lower() in {"true", "1"}
        if not (error or decision_error):
            continue
        level = "high" if decision_error else "medium"
        raw = row.get("Raw", row.get("raw", "")) or row.get("Source", "")
        score, basis = _r_confidence(
            "r_statcheck",
            level,
            max(1, len(rows)),
            "decision_error" if decision_error else "inconsistent",
            1.0 if raw else 0.7,
        )
        finding = Finding(
            table=source_name,
            level=level,
            check="R statcheck in-text statistical consistency",
            target=raw[:120] or "APA statistical expression",
            summary="R statcheck found inconsistency between in-text statistics and reported p-value.",
            evidence=f"reported p={row.get('Reported_P_Value', row.get('reported_p', ''))}, computed p={row.get('Computed_P_Value', row.get('computed_p', ''))}",
            detail=f"Raw R output fields: {row}",
            suggestion="Prioritize checking whether statistic, df, one/two-tailed test, and p-value are from the same analysis.",
            tool_id="r_statcheck",
            tool_name=spec.display_name,
            module="r_statcheck_text",
            input_type=input_type,
            routing_reason="User selected R statcheck, and the document body was recognized as containing APA/NHST statistical expressions.",
            method_limitations=spec.method_limitations,
            detector_runtime="r",
            dependency_status="ready",
            confidence="high" if decision_error else "medium",
            confidence_score=score,
            confidence_basis=basis,
            false_positive_risk="medium",
        )
        enrich_finding_explanation(finding)
        findings.append(finding)
    if not findings:
        findings.append(_info_finding(source_name, "r_statcheck", "r_statcheck_text", "R statcheck ran; no reportable inconsistencies found.", f"text length={len(text or '')}", input_type, "ready"))
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
ncol <- cols[match(TRUE, norm(cols) %in% c("n", "samplesize", "cases", "n", "samplesize", "cases"))]
mcol <- cols[match(TRUE, norm(cols) %in% c("mean", "means", "mean", "means", "average"))]
sdcol <- cols[match(TRUE, norm(cols) %in% c("sd", "std", "sd", "std"))]
propcol <- cols[match(TRUE, norm(cols) %in% c("proportion", "prop", "rate", "ratio", "percent", "percentage", "proportion", "prop", "rate"))]
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
        add("GRIM", i, "error", paste0("N=", n, ", mean=", m_raw, "; R scrutiny::grim could not evaluate this row"))
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
      add("GRIMMER", i, "error", paste0("N=", n, ", mean=", m_raw, ", SD=", sd_raw, "; R scrutiny::grimmer could not evaluate this row"))
    }
    if (m >= 0 && m <= 1 && sd >= 0 && sd <= 0.5) {
      debit_cases <- debit_cases + 1
      ok_d <- tryCatch(suppressWarnings(scrutiny::debit(x=m_raw, sd=sd_raw, n=as.integer(n))), error=function(e) NA)
      if (is_inconsistent(ok_d)) {
        add("DEBIT", i, "inconsistent", paste0("N=", n, ", binary mean=", m_raw, ", SD=", sd_raw))
      } else if (length(ok_d) != 1 || is.na(ok_d)) {
        add("DEBIT", i, "error", paste0("N=", n, ", binary mean=", m_raw, ", SD=", sd_raw, "; R scrutiny::debit could not evaluate this row"))
      }
    }
  }
  add("GRIMMER", 0, "ran", paste0("Automatically checked ", grimmer_cases, " N/mean/SD summary rows."))
  add("DEBIT", 0, "ran", paste0("Automatically checked ", debit_cases, " binary mean/SD/N summary candidate rows; rows with non-0-1 mean or SD>0.5 were skipped."))
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
        add("DEBIT", i, "error", paste0("N=", n, ", binary proportion=", x_raw, ", SD=", sd_raw, "; R scrutiny::debit could not evaluate this row"))
      }
    }
  }
  add("DEBIT", 0, "ran", paste0("Automatically checked ", debit_cases, " binary proportion/SD/N summary candidate rows."))
}
write.csv(out, stdout(), row.names=FALSE, na="")
'''
    try:
        proc = _run_r(script, [csv_path, str(scale_min), str(scale_max)])
    finally:
        Path(csv_path).unlink(missing_ok=True)
    spec = TOOL_REGISTRY["r_scrutiny"]
    if proc.returncode != 0:
        finding = _info_finding(name, "r_scrutiny", "r_scrutiny_runtime", "R scrutiny run failed.", proc.stderr.strip(), input_type)
        return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=[finding])
    rows = _rows_from_csv_stdout(proc.stdout)
    findings: list[Finding] = []
    for row in rows:
        check = row.get("check", "scrutiny")
        status = row.get("status", "")
        if status == "inconsistent":
            level = "high"
            summary = f"R scrutiny {check} check found summary statistics are mathematically infeasible."
            confidence_status = "inconsistent"
        elif status == "error":
            level = "info"
            summary = f"R scrutiny {check} check could not evaluate this row."
            confidence_status = "error"
        else:
            level = "info"
            summary = f"R scrutiny record: {check} ran automatically."
            confidence_status = "ran"
        row_count = int(df.shape[0])
        score, basis = _r_confidence(
            "r_scrutiny",
            level,
            row_count,
            confidence_status,
            1.0 if row.get("detail", "") else 0.7,
        )
        finding = Finding(
            table=name,
            level=level,
            check=f"R scrutiny {check}",
            target=f"row {row.get('row', '')}",
            summary=summary,
            evidence=row.get("detail", ""),
            detail=f"R scrutiny output: {row}",
            suggestion="Verify scale range, rounding precision, and variable type; if binary/discrete summary, review original counts or statistical scripts.",
            tool_id="r_scrutiny",
            tool_name=spec.display_name,
            module="r_scrutiny_summary",
            input_type=input_type,
            routing_reason="User selected R scrutiny, and the system recognized a summary statistics table structure.",
            method_limitations=spec.method_limitations,
            detector_runtime="r",
            dependency_status="ready",
            confidence="high" if level == "high" else "low",
            confidence_score=score,
            confidence_basis=basis,
            false_positive_risk="medium",
        )
        enrich_finding_explanation(finding)
        findings.append(finding)
    if not findings:
        findings.append(_info_finding(name, "r_scrutiny", "r_scrutiny_summary", "R scrutiny ran; no reportable inconsistencies found.", f"rows={df.shape[0]}，columns={df.shape[1]}", input_type, "ready"))
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
ncol <- cols[match(TRUE, norm(cols) %in% c("n", "samplesize", "cases", "n", "samplesize", "cases"))]
mcol <- cols[match(TRUE, norm(cols) %in% c("mean", "means", "mean", "means", "average"))]
sdcol <- cols[match(TRUE, norm(cols) %in% c("sd", "std", "sd", "std"))]
out <- data.frame(check=character(), row=integer(), status=character(), detail=character(), stringsAsFactors=FALSE)
add <- function(check, row, status, detail) {
  out <<- rbind(out, data.frame(check=check, row=row, status=status, detail=detail, stringsAsFactors=FALSE))
}
if (is.na(ncol) || is.na(mcol) || is.na(sdcol)) {
  add("SPRITE", 0, "skipped", "Missing N, mean, or SD columns; cannot call rsprite2::set_parameters and find_possible_distribution.")
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
        detail <- paste0("N=", n, ", mean=", m_raw, ", SD=", sd_raw, ", scale=", scale_min, "-", scale_max, "; no feasible distribution found.")
      }
      list(status=status, detail=detail)
    }, error=function(e) {
      list(status="impossible", detail=paste0("N=", n, ", mean=", m_raw, ", SD=", sd_raw, ", scale=", scale_min, "-", scale_max, "; ", conditionMessage(e)))
    })
    add("SPRITE", i, res$status, res$detail)
  }
  add("SPRITE", 0, "ran", paste0("Attempted rsprite2 SPRITE distribution reconstruction on ", cases, " N/mean/SD summary rows."))
}
write.csv(out, stdout(), row.names=FALSE, na="")
'''
    try:
        proc = _run_r(script, [csv_path, str(scale_min), str(scale_max)], timeout=120)
    finally:
        Path(csv_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        finding = _info_finding(name, "r_rsprite2", "r_rsprite2_runtime", "R rsprite2 run failed.", proc.stderr.strip(), input_type)
        return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=[finding])
    rows = _rows_from_csv_stdout(proc.stdout)
    findings: list[Finding] = []
    for row in rows:
        status = row.get("status", "")
        if status in {"impossible", "not_found"}:
            level = "high"
            summary = "R rsprite2 SPRITE could not find a discrete distribution matching the reported summary statistics."
            confidence = "medium"
            false_positive_risk = "high"
        else:
            level = "info"
            summary = "R rsprite2 SPRITE ran successfully."
            confidence = "low"
            false_positive_risk = "medium"
        score, basis = _r_confidence(
            "r_rsprite2",
            level,
            int(df.shape[0]),
            status or "ran",
            1.0 if row.get("detail", "") else 0.7,
        )
        finding = Finding(
            table=name,
            level=level,
            check="R rsprite2 SPRITE",
            target=f"row {row.get('row', '')}",
            summary=summary,
            evidence=row.get("detail", ""),
            detail=f"R rsprite2 output: {row}",
            suggestion="Verify scale range, mean/SD decimal precision, sample size, and whether this is a discrete score summary; SPRITE high-risk results should be manually reviewed against original frequencies.",
            tool_id="r_rsprite2",
            tool_name=spec.display_name,
            module="r_rsprite2_sprite",
            input_type=input_type,
            routing_reason="User selected advanced R review scenario, and the data was recognized as a discrete score summary.",
            method_limitations=spec.method_limitations,
            detector_runtime="r",
            dependency_status="ready",
            confidence=confidence,
            confidence_score=score,
            confidence_basis=basis,
            false_positive_risk=false_positive_risk,
        )
        enrich_finding_explanation(finding)
        findings.append(finding)
    if not findings:
        findings.append(_info_finding(name, "r_rsprite2", "r_rsprite2_sprite", "R rsprite2 ran but returned no parseable results.", f"rows={df.shape[0]}，columns={df.shape[1]}", input_type, "ready"))
    return TableResult(name=name, rows=int(df.shape[0]), columns=int(df.shape[1]), findings=findings)
