from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

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


def _short_value(value: Any, limit: int = 180) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _route_items(route: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    items.extend(route.get("tables") or [])
    for key in ("text", "image", "code", "project"):
        item = route.get(key)
        if isinstance(item, dict):
            items.append(item)
    return items


def _classification_text(item: dict[str, Any]) -> str:
    classification = item.get("classification") or {}
    input_types = list(dict.fromkeys(map(str, classification.get("input_types") or [])))
    primary = classification.get("primary_type") or ""
    if primary and input_types and primary not in input_types:
        return f"{primary}; {', '.join(map(str, input_types))}"
    if input_types:
        return ", ".join(map(str, input_types))
    return str(primary or "")


def _decision_source_label(route: dict[str, Any], item: dict[str, Any]) -> str:
    source = str(route.get("source") or "")
    name = str(item.get("name") or "")
    if name:
        return f"{Path(source).name}:{name}" if source else name
    return Path(source).name if source else str(route.get("source_kind") or "source")


def _tool_run_rows(audit_context: dict[str, Any] | None, results: list[TableResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if audit_context:
        for route in audit_context.get("routes", []):
            for item in _route_items(route):
                for tool_id, decision in (item.get("routing_decisions") or {}).items():
                    if not decision.get("selected_by_user"):
                        continue
                    rows.append(
                        {
                            "tool_id": str(tool_id),
                            "tool_name": str(decision.get("tool_name") or tool_id),
                            "material": _decision_source_label(route, item),
                            "status": str(decision.get("status") or ""),
                            "dependency_status": str(decision.get("dependency_status") or ""),
                            "runtime": str(decision.get("detector_runtime") or ""),
                            "input_type": str(decision.get("matched_input_type") or ""),
                            "reason": str(
                                decision.get("skip_reason")
                                or decision.get("routing_reason")
                                or "确定性路由判定该工具适用于当前材料。"
                            ),
                            "limitations": str(decision.get("method_limitations") or ""),
                        }
                    )
    if rows:
        return rows

    seen: set[tuple[str, str, str]] = set()
    for result in results:
        for finding in result.findings:
            key = (finding.tool_id, result.name, finding.dependency_status)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "tool_id": finding.tool_id or result.name,
                    "tool_name": finding.tool_name or finding.tool_id or result.name,
                    "material": result.name,
                    "status": "recorded",
                    "dependency_status": finding.dependency_status,
                    "runtime": finding.detector_runtime,
                    "input_type": finding.input_type,
                    "reason": finding.routing_reason,
                    "limitations": finding.method_limitations,
                }
            )
    return rows


def _material_rows(audit_context: dict[str, Any] | None, results: list[TableResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    if audit_context:
        for project_route in audit_context.get("project_routes", []):
            for material in project_route.get("materials") or []:
                path = str(material.get("path") or "")
                role = str(material.get("role") or "")
                key = (path, role, "project")
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "name": Path(path).name or path,
                        "role": role,
                        "path": path,
                        "rows": "",
                        "columns": "",
                        "input_type": "project_material",
                        "status": "listed",
                    }
                )
        for route in audit_context.get("routes", []):
            source = str(route.get("source") or "")
            for item in _route_items(route):
                name = str(item.get("name") or Path(source).name or route.get("source_kind") or "source")
                key = (source, name, "route")
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "name": name,
                        "role": str(route.get("source_kind") or ""),
                        "path": source,
                        "rows": str(item.get("rows") or ""),
                        "columns": str(item.get("columns") or ""),
                        "input_type": _classification_text(item),
                        "status": "routed",
                    }
                )
    if rows:
        return rows

    for result in results:
        rows.append(
            {
                "name": result.name,
                "role": "result",
                "path": "",
                "rows": str(result.rows),
                "columns": str(result.columns),
                "input_type": "",
                "status": "reported",
            }
        )
    return rows


def _collect_audit_context(finding_paths: list[Path]) -> dict[str, Any]:
    route_paths: list[Path] = []
    project_route_paths: list[Path] = []
    for path in finding_paths:
        root = path.parent
        candidates = [root / "route.json"]
        candidates.extend(sorted(root.glob("**/route.json")))
        for candidate in candidates:
            if candidate not in route_paths:
                route_paths.append(candidate)
        project_candidates = [root / "project-route.json"]
        project_candidates.extend(sorted(root.glob("**/project-route.json")))
        for candidate in project_candidates:
            if candidate not in project_route_paths:
                project_route_paths.append(candidate)

    routes = [payload for path in route_paths if (payload := _read_json_if_exists(path))]
    project_routes = [payload for path in project_route_paths if (payload := _read_json_if_exists(path))]
    return {"routes": routes, "project_routes": project_routes}


def render_markdown(
    source: Path,
    results: list[TableResult],
    extraction_notes: list[str],
    audit_context: dict[str, Any] | None = None,
) -> str:
    all_findings = [finding for result in results for finding in result.findings]
    risk_findings = [finding for finding in all_findings if finding.level in {"high", "medium", "low"}]
    info_findings = [finding for finding in all_findings if finding.level == "info"]
    level = overall_level(all_findings)
    counts = Counter(finding.level for finding in all_findings)
    tool_counts = Counter(finding.tool_id or result.name for result in results for finding in result.findings)
    material_rows = _material_rows(audit_context, results)
    tool_rows = _tool_run_rows(audit_context, results)
    gap_rows = [row for row in tool_rows if row["status"] != "ready" or row["dependency_status"] not in {"", "ready"}]
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

    lines += [
        "## 预审范围与判读口径",
        "",
        "- 本报告为自动化预审底稿，只记录可复算的风险信号、运行状态和覆盖缺口。",
        "- 风险等级仅表示人工复核优先级，不构成数据风险校验结论。",
        "- `info` 记录为工具运行、依赖、材料不足或路由状态，不计入风险信号。",
        "- 未运行或不适用的工具表示本次材料/依赖/路由条件不足，不表示相应风险不存在。",
        "",
        "## 材料清单",
        "",
        "| 材料 | 角色/来源 | 行数 | 列数 | 输入类型/分类 | 状态 | 路径 |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for row in material_rows:
        lines.append(
            f"| {markdown_cell(_short_value(row['name']))} | {markdown_cell(row['role'])} | {markdown_cell(row['rows'])} | {markdown_cell(row['columns'])} | {markdown_cell(_short_value(row['input_type']))} | {markdown_cell(row['status'])} | {markdown_cell(_short_value(row['path'], 220))} |"
        )
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
    lines += ["## 材料覆盖矩阵", "", header, sep]
    for sheet_name in sheet_names_ordered:
        first_result = sheet_results[sheet_name][0]
        row = f"| {markdown_cell(sheet_name)} | {first_result.rows} | {first_result.columns} |"
        for tool_id in tools_ordered:
            c = sheet_tool_counts[sheet_name][tool_id]
            cell = f"高{c['high']} 中{c['medium']} 低{c['low']}"
            row += f" {cell} |"
        lines.append(row)
    lines.append("")

    lines += [
        "## 工具运行明细",
        "",
        "| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in tool_rows:
        lines.append(
            f"| {markdown_cell(row['tool_id'])} | {markdown_cell(_short_value(row['tool_name']))} | {markdown_cell(_short_value(row['material']))} | {markdown_cell(row['status'])} | {markdown_cell(row['dependency_status'])} | {markdown_cell(row['runtime'])} | {markdown_cell(row['input_type'])} | {markdown_cell(_short_value(row['reason']))} | {markdown_cell(_short_value(row['limitations']))} |"
        )
    lines.append("")

    lines += ["## 覆盖缺口与未运行原因", ""]
    if not gap_rows:
        lines += ["本次路由上下文中未记录需要单列说明的未运行、依赖缺失或材料不足状态。", ""]
    else:
        lines += [
            "| 工具 | 材料/模块 | 状态 | 依赖状态 | 原因 | 对预审的影响 |",
            "|---|---|---|---|---|---|",
        ]
        for row in gap_rows:
            effect = "该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。"
            if row["status"] == "ready" and row["dependency_status"] != "ready":
                effect = "工具已产生运行记录，但依赖或材料状态会限制覆盖范围。"
            lines.append(
                f"| {markdown_cell(row['tool_id'])} | {markdown_cell(_short_value(row['material']))} | {markdown_cell(row['status'])} | {markdown_cell(row['dependency_status'])} | {markdown_cell(_short_value(row['reason']))} | {markdown_cell(effect)} |"
            )
        lines.append("")

    lines += ["## 风险发现清单（问题清单）", ""]
    if not risk_findings:
        lines += ["未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。", ""]
        lines += ["## 专家复核附录", "", "本次没有可展开的风险发现。", ""]
        lines += ["## 人工复核任务表", "", "本次没有由风险发现聚合出的人工复核任务。", ""]
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
                f"- 工具：{finding.tool_name or finding.tool_id}（{finding.tool_id}）",
                f"- 运行时/依赖：{finding.detector_runtime} / {finding.dependency_status}",
                f"- 输入类型：{finding.input_type}",
                f"- 置信度/误报风险：{finding.confidence} / {finding.false_positive_risk}",
            ]
            if finding.detail:
                lines.append(f"- 详细说明：{finding.detail}")
            if finding.calculation_trace:
                lines.append(f"- 计算/抽取过程：{finding.calculation_trace}")
            if finding.external_records:
                lines.append(f"- 外部记录：{finding.external_records}")
            if finding.raw_output_ref:
                lines.append(f"- 原始输出引用：{finding.raw_output_ref}")
            lines += [
                f"- 路由依据：{finding.routing_reason}",
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
        lines += ["## 人工复核任务表", ""]
        lines += ["| 序号 | 复核任务 | 涉及证据数 |", "|---:|---|---:|"]
        for idx, action in enumerate(author_actions[:12], start=1):
            evidence_count = sum(
                1 for finding in ordered if (finding.review_actions or finding.review_steps or finding.suggestion) == action
            )
            lines.append(f"| {idx} | {markdown_cell(action)} | {evidence_count} |")
        lines.append("")

    lines += ["## 运行提示（不计入风险）", ""]
    lines += ["| 工具 | 记录数 |", "|---|---:|"]
    for tool_id, count in sorted(tool_counts.items()):
        lines.append(f"| {markdown_cell(tool_id)} | {count} |")
    lines.append("")
    if info_findings:
        for finding in info_findings[:30]:
            lines.append(
                f"- `{finding.tool_id}`：{finding.summary}（{finding.evidence}；依赖状态={finding.dependency_status}；输入类型={finding.input_type}）"
            )
        if len(info_findings) > 30:
            lines.append(f"- 其余运行提示 {len(info_findings) - 30} 条见 JSON。")
        lines.append("")
    else:
        lines += ["无运行提示。", ""]

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
    finding_paths: list[Path] = []
    for item in finding_json:
        path = Path(item).expanduser().resolve()
        finding_paths.append(path)
        payload = read_json(path)
        sources.append(str(payload.get("source") or item))
        all_results.extend(results_from_payload(payload))

    pseudo_source = Path(sources[0] if len(sources) == 1 else "merged-findings.json")
    audit_context = _collect_audit_context(finding_paths)
    out.write_text(
        render_markdown(pseudo_source, all_results, ["本报告由多个 CLI finding JSON 合并生成。"], audit_context),
        encoding="utf-8",
    )
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
