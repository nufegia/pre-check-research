from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pcr_audit.crosscheck import coerce_numeric
from pcr_audit.io import load_tables
from pcr_audit.models import Finding, TableResult, enrich_finding_explanation


STAT_NAMES = {
    "n": ("n", "样本量", "例数", "人数", "cases", "samplesize", "number"),
    "mean": ("mean", "means", "均值", "均数", "平均值", "平均数"),
    "sd": ("sd", "std", "标准差", "stdev"),
    "se": ("se", "sem", "标准误", "sterr"),
    "count": ("count", "频数", "计数", "n_pos"),
    "percent": ("percent", "percentage", "prop", "rate", "百分比", "比例", "率"),
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
    tool_name: str = "跨材料数据对账",
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
        routing_reason="项目级审计同时存在文档/补充材料和原始数据或脚本输出。",
        method_limitations="该模块只做可确定匹配的描述统计对账；变量名、分组名或文档抽取不可靠时只输出复核提示。",
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
            for idx, row in df.iterrows():
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
                        values.append(SummaryValue(path, table, int(idx) + 1, label, role, float(series_value)))
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
                "跨材料对账材料不足",
                "project",
                "未获得足够的原始数据统计量或文档摘要统计表，跨材料对账未运行。",
                f"raw_stats={len(raw)}; summary_values={len(summaries)}",
                "补充可解析的原始 CSV/XLSX、稿件表格或脚本输出统计表后重试。",
            )
        )
        return TableResult("data_trace_crosscheck", len(summaries), 0, findings)

    compared = 0
    unmatched: list[str] = []
    for summary in summaries:
        item = _match_raw(summary, raw)
        if item is None:
            if len(unmatched) < 8:
                unmatched.append(f"{summary.source.name}:{summary.table}:行{summary.row}:{summary.variable}/{summary.stat}")
            continue
        expected = getattr(item, summary.stat, None)
        if expected is None:
            continue
        compared += 1
        if not _close_enough(summary.stat, summary.value, float(expected)):
            findings.append(
                _finding(
                    "high" if summary.stat in {"n", "mean", "sd"} else "medium",
                    "原始数据/稿件摘要统计对账",
                    f"{summary.variable} {summary.stat}",
                    "稿件或脚本输出中的摘要统计量与原始数据自动汇总不一致。",
                    f"reported={summary.value:.6g}; raw={float(expected):.6g}; source={summary.source.name}:{summary.table}:row{summary.row}; raw_source={item.source.name}:{item.variable}",
                    "核对变量名映射、分组筛选、缺失剔除规则和稿件表格是否来自同一版数据。",
                )
            )
    if compared == 0:
        findings.append(
            _finding(
                "info",
                "跨材料变量匹配不足",
                "summary/raw",
                "发现摘要统计和原始数据，但无法可靠匹配变量名。",
                "未匹配样例：" + "；".join(unmatched),
                "统一稿件表格变量名与原始数据列名，或在 manifest 中补充分组/变量映射。",
            )
        )
    elif not findings:
        findings.append(
            _finding(
                "info",
                "跨材料对账完成",
                "summary/raw",
                "可匹配的摘要统计量与原始数据自动汇总一致。",
                f"compared={compared}; unmatched={len(unmatched)}",
                "对未匹配变量和复杂分组仍建议人工复核。",
            )
        )
    return TableResult("data_trace_crosscheck", len(summaries), len(raw), findings)


def _copy_project(source: Path, sandbox_root: Path) -> Path:
    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)
    sandbox_root.mkdir(parents=True, exist_ok=True)
    dest = sandbox_root / "project"
    if source.is_dir():
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".git", ".pcr", "*.parts", "__pycache__"))
    else:
        dest.mkdir()
        shutil.copy2(source, dest / source.name)
    return dest


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    data: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        if path.is_file():
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
        findings.append(_code_finding("info", "分析脚本复跑跳过", "analysis_code", "用户关闭了脚本沙箱复跑。", "rerun_code=false", "如需复跑，请启用 --rerun-code。"))
        return TableResult("code_rerun_execute", 0, 0, findings), []

    runnable = [path for path in code_paths if path.suffix.lower() in {".py", ".r"}]
    unsupported = [path for path in code_paths if path.suffix.lower() not in {".py", ".r"}]
    for path in unsupported[:20]:
        findings.append(_code_finding("info", "分析脚本复跑不支持", path.name, "当前版本不执行 Stata/SPSS/SAS 等脚本。", str(path), "请在受控统计环境中人工复跑，并提供输出表。"))
    if not runnable:
        findings.append(_code_finding("info", "分析脚本复跑材料不足", "analysis_code", "未发现可复跑的 Python/R 脚本。", f"code_files={len(code_paths)}", "提供 Python 或 R 分析脚本后重试。"))
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
            findings.append(_code_finding("info", "分析脚本解释器缺失", original.name, "缺少脚本运行时，已跳过复跑。", str(original), "安装 Python/Rscript 及依赖后重试。"))
            continue
        before = _snapshot(sandbox_project)
        try:
            proc = subprocess.run(cmd, cwd=sandbox_project, env=env, capture_output=True, text=True, timeout=timeout)
            changed = _changed_files(before, sandbox_project)
            derived.extend(path for path in changed if path.suffix.lower() in {".csv", ".xlsx", ".xls", ".txt", ".md", ".json"})
            level = "info"
            summary = "分析脚本沙箱复跑完成。" if proc.returncode == 0 else "分析脚本沙箱复跑失败，已记录为运行提示。"
            evidence = f"returncode={proc.returncode}; changed_files={len(changed)}; stdout={proc.stdout[-300:]}; stderr={proc.stderr[-300:]}"
        except subprocess.TimeoutExpired as exc:
            level = "info"
            summary = "分析脚本沙箱复跑超时，已跳过。"
            evidence = f"timeout={timeout}s; stdout={(exc.stdout or '')[-300:]}; stderr={(exc.stderr or '')[-300:]}"
        findings.append(
            _code_finding(
                level,
                "分析脚本沙箱复跑",
                original.name,
                summary,
                evidence,
                "核对脚本依赖、输入路径、随机种子和生成输出；沙箱失败不计入数据风险。",
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
        tool_name="分析脚本沙箱复跑",
        module="code_rerun_execute",
    )
