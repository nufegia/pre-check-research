from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path

from pcr_audit.io import read_json, write_json
from pcr_audit.models import Finding, LEVEL_CN, LEVEL_SCORE, TableResult, finding_from_mapping


def markdown_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def overall_level(findings: list[Finding]) -> str:
    risk_findings = [finding for finding in findings if finding.level in {"high", "medium", "low"}]
    if not risk_findings:
        return "low"
    score = max(LEVEL_SCORE[finding.level] for finding in risk_findings)
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


def render_markdown(source: Path, results: list[TableResult], extraction_notes: list[str]) -> str:
    all_findings = [finding for result in results for finding in result.findings]
    level = overall_level(all_findings)
    counts = Counter(finding.level for finding in all_findings)
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
        "> 本报告只识别数据中的异常模式和人工痕迹信号，不构成学术不端或造假鉴定。高风险项表示需要优先回看原始记录、实验日志或统计脚本。",
        "",
    ]
    if extraction_notes:
        lines += ["## 解析说明", ""]
        lines += [f"- {note}" for note in extraction_notes]
        lines.append("")

    lines += ["## 表格概览", "", "| 表格 | 行数 | 列数 | 高 | 中 | 低 |", "|---|---:|---:|---:|---:|---:|"]
    for result in results:
        counter = Counter(finding.level for finding in result.findings)
        lines.append(
            f"| {result.name} | {result.rows} | {result.columns} | {counter['high']} | {counter['medium']} | {counter['low']} |"
        )
    lines.append("")

    lines += ["## 问题清单", ""]
    if not all_findings:
        lines += ["未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。", ""]
    else:
        ordered = sorted(all_findings, key=lambda finding: LEVEL_SCORE[finding.level], reverse=True)
        lines += [
            "| 风险 | 表格 | 检查项 | 对象 | 发现 | 证据 | 建议 |",
            "|---|---|---|---|---|---|---|",
        ]
        for finding in ordered:
            lines.append(
                f"| {LEVEL_CN[finding.level]} | {markdown_cell(finding.table)} | {markdown_cell(finding.check)} | {markdown_cell(finding.target)} | {markdown_cell(finding.summary)} | {markdown_cell(finding.evidence)} | {markdown_cell(finding.suggestion)} |"
            )
        lines.append("")
        lines += ["## 问题详情", ""]
        for idx, finding in enumerate(ordered, start=1):
            lines += [
                f"### {idx}. {LEVEL_CN[finding.level]}风险：{finding.check}（{finding.target}）",
                "",
                f"- 表格：{finding.table}",
                f"- 发现：{finding.summary}",
                f"- 触发证据：{finding.evidence}",
            ]
            if finding.detail:
                lines.append(f"- 详细说明：{finding.detail}")
            lines += [f"- 复核建议：{finding.suggestion}", ""]

    lines += [
        "## 已运行检测",
        "",
        "- 工具运行记录来自确定性 route 结果和各 detector finding JSON。",
        "- 缺失工具、缺失依赖和跳过检测只记录为提示，不计入数据风险。",
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
                "findings": [asdict(finding) for finding in result.findings],
            }
            for result in results
        ],
    }
    write_json(path, payload)


def results_from_payload(payload: dict) -> list[TableResult]:
    source = str(payload.get("source") or "merged")
    if "results" in payload:
        return [
            TableResult(
                name=str(result.get("name") or source),
                rows=int(result.get("rows") or 0),
                columns=int(result.get("columns") or 0),
                findings=[finding_from_mapping(source, finding) for finding in result.get("findings", [])],
            )
            for result in payload["results"]
        ]
    return [
        TableResult(
            name=source,
            rows=0,
            columns=0,
            findings=[finding_from_mapping(source, finding) for finding in payload.get("findings", [])],
        )
    ]


def merge_reports(finding_json: list[str], out: Path, json_out: Path | None = None) -> None:
    all_results: list[TableResult] = []
    sources: list[str] = []
    for item in finding_json:
        payload = read_json(Path(item).expanduser().resolve())
        sources.append(str(payload.get("source") or item))
        all_results.extend(results_from_payload(payload))

    pseudo_source = Path(sources[0] if len(sources) == 1 else "merged-findings.json")
    out.write_text(render_markdown(pseudo_source, all_results, ["本报告由多个 CLI finding JSON 合并生成。"]), encoding="utf-8")
    if json_out:
        write_json(
            json_out,
            {
                "source": sources,
                "results": [
                    {
                        "name": result.name,
                        "rows": result.rows,
                        "columns": result.columns,
                        "findings": [asdict(finding) for finding in result.findings],
                    }
                    for result in all_results
                ],
            },
        )
