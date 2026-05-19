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
    risk_findings = [finding for finding in all_findings if finding.level in {"high", "medium", "low"}]
    info_findings = [finding for finding in all_findings if finding.level == "info"]
    level = overall_level(all_findings)
    counts = Counter(finding.level for finding in all_findings)
    tool_counts = Counter(finding.tool_id or result.name for result in results for finding in result.findings)
    lines = [
        "# 数据审计报告：数据完整性与统计一致性",
        "",
        "## 导师摘要",
        "",
        f"- 文件：`{source.name}`",
        f"- 总体风险：{LEVEL_CN[level]}",
        f"- 检测对象：{len(results)} 组",
        f"- 风险信号：高 {counts['high']} / 中 {counts['medium']} / 低 {counts['low']}",
        f"- 运行提示：{counts['info']} 条",
        "",
        "> 本报告只识别数据、统计、图像、文献和流程材料中的风险信号，不构成数据风险校验结论。高风险项表示需要优先回看原始记录、实验日志、原始图或统计脚本。",
        "",
    ]
    if extraction_notes:
        lines += ["## 解析说明", ""]
        lines += [f"- {note}" for note in extraction_notes]
        lines.append("")

    # Group results by sheet name
    sheet_names_ordered = []
    sheet_results: dict[str, list[TableResult]] = {}
    for result in results:
        if result.name not in sheet_results:
            sheet_names_ordered.append(result.name)
            sheet_results[result.name] = []
        sheet_results[result.name].append(result)

    # Collect all tool IDs across all results
    all_tools: set[str] = set()
    for result in results:
        for finding in result.findings:
            if finding.tool_id:
                all_tools.add(finding.tool_id)
    tools_ordered = sorted(all_tools)

    # Build tool-level counts per sheet: {sheet: {tool: Counter}}
    sheet_tool_counts: dict[str, dict[str, Counter]] = {}
    for sheet_name in sheet_names_ordered:
        sheet_tool_counts[sheet_name] = {}
        for tool_id in tools_ordered:
            sheet_tool_counts[sheet_name][tool_id] = Counter()
        for result in sheet_results[sheet_name]:
            for finding in result.findings:
                if finding.tool_id:
                    sheet_tool_counts[sheet_name][finding.tool_id][finding.level] += 1

    # Render matrix: sheet × tool
    header = "| 材料/模块 | 行数 | 列数 |"
    sep = "|---|---:|---:|"
    for tool_id in tools_ordered:
        header += f" {tool_id} |"
        sep += "---|"
    lines += ["## 审计矩阵", "", header, sep]
    for sheet_name in sheet_names_ordered:
        first_result = sheet_results[sheet_name][0]
        row = f"| {markdown_cell(sheet_name)} | {first_result.rows} | {first_result.columns} |"
        for tool_id in tools_ordered:
            c = sheet_tool_counts[sheet_name][tool_id]
            cell = f"高{c['high']} 中{c['medium']} 低{c['low']}"
            row += f" {cell} |"
        lines.append(row)
    lines.append("")

    lines += ["## 风险发现清单（问题清单）", ""]
    if not risk_findings:
        lines += ["未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。", ""]
    else:
        ordered = sorted(risk_findings, key=lambda finding: LEVEL_SCORE[finding.level], reverse=True)
        lines += [
            "| 风险 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for finding in ordered:
            lines.append(
                f"| {LEVEL_CN[finding.level]} | {markdown_cell(finding.evidence_id)} | {markdown_cell(finding.location)} | {markdown_cell(finding.check)} | {markdown_cell(finding.target)} | {markdown_cell(finding.summary)} | {markdown_cell(finding.evidence)} | {markdown_cell(finding.review_actions or finding.suggestion)} |"
            )
        lines.append("")
        lines += ["## 专家复核附录", ""]
        for idx, finding in enumerate(ordered, start=1):
            lines += [
                f"### {idx}. {LEVEL_CN[finding.level]}风险：{finding.check}（{finding.target}）",
                "",
                f"- 证据ID：{finding.evidence_id}",
                f"- 位置：{finding.location}",
                f"- 发现：{finding.summary}",
                f"- 触发证据：{finding.evidence}",
            ]
            if finding.detail:
                lines.append(f"- 详细说明：{finding.detail}")
            if finding.calculation_trace:
                lines.append(f"- 计算/抽取过程：{finding.calculation_trace}")
            if finding.external_records:
                lines.append(f"- 外部记录：{finding.external_records}")
            lines += [
                f"- 可能正常解释：{finding.normal_explanations}",
                f"- 复核动作：{finding.review_actions or finding.review_steps or finding.suggestion}",
                f"- 方法限制：{finding.method_limitations}",
                f"- 置信依据：{finding.confidence_basis}",
                "",
            ]

        author_actions = []
        seen_actions = set()
        for finding in ordered:
            action = finding.review_actions or finding.review_steps or finding.suggestion
            if action and action not in seen_actions:
                seen_actions.add(action)
                author_actions.append(action)
        lines += ["## 作者整改清单", ""]
        for idx, action in enumerate(author_actions[:12], start=1):
            lines.append(f"{idx}. {action}")
        lines.append("")

    lines += [
        "## 工具运行与材料覆盖",
        "",
        "| 工具 | 记录数 |",
        "|---|---:|",
    ]
    for tool_id, count in sorted(tool_counts.items()):
        lines.append(f"| {markdown_cell(tool_id)} | {count} |")
    lines.append("")
    if info_findings:
        lines += ["### 运行提示（不计入风险）", ""]
        for finding in info_findings[:30]:
            lines.append(f"- `{finding.tool_id}`：{finding.summary}（{finding.evidence}）")
        if len(info_findings) > 30:
            lines.append(f"- 其余运行提示 {len(info_findings) - 30} 条见 JSON。")
        lines.append("")

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
