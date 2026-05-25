from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from pcr_audit.crosscheck import coerce_numeric
from pcr_audit.io import load_tables
from pcr_audit.models import Finding, TableResult, enrich_finding_explanation


STAT_NAMES = {
    "n": ("n", "sample_size", "cases", "samplesize", "number"),
    "mean": ("mean", "means", "average"),
    "sd": ("sd", "std", "stdev"),
    "se": ("se", "sem", "standard_error", "sterr"),
    "count": ("count", "freq", "frequency", "n_pos"),
    "percent": ("percent", "percentage", "prop", "rate"),
}


@dataclass(frozen=True)
class SummaryValue:
    source: Path
    table: str
    row: int
    variable: str
    stat: str
    value: float


@dataclass(frozen=True)
class RawStat:
    source: Path
    table: str
    variable: str
    n: float
    mean: float | None = None
    sd: float | None = None
    se: float | None = None


def _norm(text: Any) -> str:
    return "".join(ch.lower() for ch in str(text or "") if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")


def _role(name: Any) -> str | None:
    norm = _norm(name)
    for role, aliases in STAT_NAMES.items():
        normalized_aliases = [_norm(alias) for alias in aliases]
        if any(alias == norm for alias in normalized_aliases):
            return role
        if any(len(alias) > 1 and alias in norm for alias in normalized_aliases):
            return role
    return None


def _finding(
    level: str,
    check: str,
    target: str,
    summary: str,
    evidence: str,
    suggestion: str,
    detail: str = "",
    tool_id: str = "data_trace_crosscheck",
    tool_name: str = "Cross-Material Data Reconciliation",
    module: str = "data_trace",
) -> Finding:
    item = Finding(
        table="data_trace_crosscheck",
        level=level,
        check=check,
        target=target,
        summary=summary,
        evidence=evidence,
        detail=detail,
        suggestion=suggestion,
        tool_id=tool_id,
        tool_name=tool_name,
        module=module,
        input_type="project_manifest",
        routing_reason="Project-level audit has both documents/supplements and raw data or script outputs.",
        method_limitations="This module only performs deterministically matchable descriptive statistics reconciliation; when variable names, group names, or document extraction are unreliable, only review prompts are output.",
        detector_runtime="python",
        dependency_status="ready",
    )
    enrich_finding_explanation(item)
    return item


def _numeric_columns(df: pd.DataFrame) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    for col in df.columns:
        values = coerce_numeric(df[col])
        non_empty = df[col].notna().sum()
        if non_empty and values.notna().sum() / non_empty >= 0.7:
            out[str(col)] = values
    return out


def _raw_stats(paths: list[Path]) -> list[RawStat]:
    stats: list[RawStat] = []
    for path in paths:
        try:
            tables = load_tables(path)
        except Exception:
            continue
        for table, df in tables:
            for col, values in _numeric_columns(df).items():
                clean = values.dropna().astype(float)
                if clean.empty:
                    continue
                sd = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
                stats.append(
                    RawStat(
                        source=path,
                        table=table,
                        variable=str(col),
                        n=float(len(clean)),
                        mean=float(clean.mean()),
                        sd=sd,
                        se=float(sd / math.sqrt(len(clean))) if len(clean) > 1 else 0.0,
                    )
                )
    return stats


def _summary_values(paths: list[Path]) -> list[SummaryValue]:
    values: list[SummaryValue] = []
    for path in paths:
        try:
            tables = load_tables(path)
        except Exception:
            continue
        for table, df in tables:
            roles = {str(col): _role(col) for col in df.columns}
            stat_cols = {col: role for col, role in roles.items() if role}
            if not stat_cols:
                continue
            label_cols = [str(col) for col in df.columns if str(col) not in stat_cols]
            for row_number, (_idx, row) in enumerate(df.iterrows(), start=1):
                label = ""
                for col in label_cols:
                    raw = row.get(col)
                    if pd.notna(raw) and str(raw).strip():
                        label = str(raw).strip()
                        break
                label = label or table
                for col, role in stat_cols.items():
                    series_value = coerce_numeric(pd.Series([row.get(col)])).iloc[0]
                    if pd.notna(series_value):
                        values.append(SummaryValue(path, table, row_number, label, role, float(series_value)))
    return values


def _match_raw(summary: SummaryValue, raw: list[RawStat]) -> RawStat | None:
    label = _norm(summary.variable)
    candidates = [item for item in raw if label and (_norm(item.variable) in label or label in _norm(item.variable))]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates and len(raw) == 1:
        return raw[0]
    return None


def _close_enough(stat: str, reported: float, expected: float) -> bool:
    if stat == "n":
        return abs(reported - expected) <= 0.5
    tolerance = max(0.02, abs(expected) * 0.03)
    return abs(reported - expected) <= tolerance


def analyze_data_trace(documents: list[Path], raw_data: list[Path], derived_outputs: list[Path] | None = None) -> TableResult:
    derived_outputs = derived_outputs or []
    raw = _raw_stats(raw_data + derived_outputs)
    summaries = _summary_values(documents + derived_outputs)
    findings: list[Finding] = []
    if not raw or not summaries:
        findings.append(
            _finding(
                "info",
                "Insufficient materials for cross-material reconciliation",
                "project",
                "Insufficient raw data statistics or document summary statistics tables obtained; cross-material reconciliation not run.",
                f"raw_stats={len(raw)}; summary_values={len(summaries)}",
                "Retry after providing parseable raw CSV/XLSX, manuscript tables, or script output statistics tables.",
            )
        )
        return TableResult("data_trace_crosscheck", len(summaries), 0, findings)

    compared = 0
    unmatched: list[str] = []
    for summary in summaries:
        item = _match_raw(summary, raw)
        if item is None:
            if len(unmatched) < 8:
                unmatched.append(f"{summary.source.name}:{summary.table}:row {summary.row}:{summary.variable}/{summary.stat}")
            continue
        expected = getattr(item, summary.stat, None)
        if expected is None:
            continue
        compared += 1
        if not _close_enough(summary.stat, summary.value, float(expected)):
            findings.append(
                _finding(
                    "high" if summary.stat in {"n", "mean", "sd"} else "medium",
                    "Raw data/manuscript summary statistics reconciliation",
                    f"{summary.variable} {summary.stat}",
                    "Summary statistics in manuscript or script output are inconsistent with raw data auto-aggregation.",
                    f"reported={summary.value:.6g}; raw={float(expected):.6g}; source={summary.source.name}:{summary.table}:row{summary.row}; raw_source={item.source.name}:{item.variable}",
                    "Verify variable name mapping, group filtering, missing value exclusion rules, and whether manuscript tables come from the same version of data.",
                )
            )
    if compared == 0:
        findings.append(
            _finding(
                "info",
                "Insufficient cross-material variable matching",
                "summary/raw",
                "Summary statistics and raw data found, but unable to reliably match variable names.",
                "Unmatched examples: " + "; ".join(unmatched),
                "Align manuscript table variable names with raw data column names, or supplement group/variable mapping in manifest.",
            )
        )
    elif not findings:
        findings.append(
            _finding(
                "info",
                "Cross-material reconciliation complete",
                "summary/raw",
                "Matchable summary statistics are consistent with raw data auto-aggregation.",
                f"compared={compared}; unmatched={len(unmatched)}",
                "Manual review is still recommended for unmatched variables and complex groupings.",
            )
        )
    return TableResult("data_trace_crosscheck", len(summaries), len(raw), findings)


def _copy_project(source: Path, sandbox_root: Path) -> Path:
    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)
    sandbox_root.mkdir(parents=True, exist_ok=True)
    dest = sandbox_root / "project"
    if source.is_dir():
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".*", ".git", ".pcr", "*.parts", "__pycache__"))
    else:
        dest.mkdir()
        shutil.copy2(source, dest / source.name)
    return dest


def _is_visible_path(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return not any(part.startswith(".") or part in {"__pycache__"} for part in parts)


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    data: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        if path.is_file() and _is_visible_path(path, root):
            stat = path.stat()
            data[str(path.relative_to(root))] = (int(stat.st_mtime_ns), int(stat.st_size))
    return data


def _changed_files(before: dict[str, tuple[int, int]], root: Path) -> list[Path]:
    after = _snapshot(root)
    changed = []
    for rel, meta in after.items():
        if before.get(rel) != meta:
            changed.append(root / rel)
    return changed


def _script_command(path: Path) -> list[str] | None:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return [sys.executable, str(path)]
    if suffix == ".r":
        rscript = shutil.which("Rscript")
        return [rscript, str(path)] if rscript else None
    return None


def run_code_sandbox(project_source: Path, code_paths: list[Path], workdir: Path, timeout: int = 60, enabled: bool = True) -> tuple[TableResult, list[Path]]:
    findings: list[Finding] = []
    if not enabled:
        findings.append(_code_finding("info", "Analysis script rerun skipped", "analysis_code", "User disabled script sandbox rerun.", "rerun_code=false", "To rerun, enable --rerun-code."))
        return TableResult("code_rerun_execute", 0, 0, findings), []

    runnable = [path for path in code_paths if path.suffix.lower() in {".py", ".r"}]
    unsupported = [path for path in code_paths if path.suffix.lower() not in {".py", ".r"}]
    for path in unsupported[:20]:
        findings.append(_code_finding("info", "Analysis script rerun unsupported", path.name, "Current version does not execute Stata/SPSS/SAS scripts.", str(path), "Please manually rerun in a controlled statistical environment and provide output tables."))
    if not runnable:
        findings.append(_code_finding("info", "Insufficient materials for analysis script rerun", "analysis_code", "No rerunnable Python/R scripts found.", f"code_files={len(code_paths)}", "Retry after providing Python or R analysis scripts."))
        return TableResult("code_rerun_execute", 0, 0, findings), []

    sandbox_project = _copy_project(project_source, workdir / "code-sandbox")
    derived: list[Path] = []
    env = dict(os.environ)
    env.update(
        {
            "TMPDIR": str(workdir / "tmp"),
            "PCR_SANDBOX_HOME": str(workdir / "code-sandbox-home"),
            "PCR_NETWORK_DISABLED": "1",
        }
    )
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    Path(env["PCR_SANDBOX_HOME"]).mkdir(parents=True, exist_ok=True)
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    for original in runnable:
        try:
            rel = original.resolve().relative_to(project_source.resolve() if project_source.is_dir() else project_source.parent.resolve())
        except ValueError:
            rel = Path(original.name)
        script = sandbox_project / rel
        cmd = _script_command(script)
        if cmd is None:
            findings.append(_code_finding("info", "Analysis script interpreter missing", original.name, "Script runtime missing; rerun skipped.", str(original), "Retry after installing Python/Rscript and dependencies."))
            continue
        before = _snapshot(sandbox_project)
        try:
            proc = subprocess.run(cmd, cwd=sandbox_project, env=env, capture_output=True, text=True, timeout=timeout)
            changed = _changed_files(before, sandbox_project)
            derived.extend(path for path in changed if path.suffix.lower() in {".csv", ".xlsx", ".xls", ".txt", ".md", ".json"})
            level = "info"
            summary = "Analysis script sandbox rerun completed." if proc.returncode == 0 else "Analysis script sandbox rerun failed; recorded as info."
            evidence = f"returncode={proc.returncode}; changed_files={len(changed)}; stdout={proc.stdout[-300:]}; stderr={proc.stderr[-300:]}"
        except subprocess.TimeoutExpired as exc:
            level = "info"
            summary = "Analysis script sandbox rerun timed out; skipped."
            stdout = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            stderr = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
            evidence = f"timeout={timeout}s; stdout={stdout[-300:]}; stderr={stderr[-300:]}"
        findings.append(
            _code_finding(
                level,
                "Analysis script sandbox rerun",
                original.name,
                summary,
                evidence,
                "Verify script dependencies, input paths, random seeds, and generated outputs; sandbox failures do not count as data risks.",
            )
        )
    return TableResult("code_rerun_execute", len(runnable), 0, findings), sorted(set(derived))


def _code_finding(level: str, check: str, target: str, summary: str, evidence: str, suggestion: str) -> Finding:
    return _finding(
        level,
        check,
        target,
        summary,
        evidence,
        suggestion,
        tool_id="code_rerun_execute",
        tool_name="Analysis Script Sandbox Rerun",
        module="code_rerun_execute",
    )
