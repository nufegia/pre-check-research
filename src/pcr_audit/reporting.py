from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pcr_audit.public_report import public_path
from pcr_audit.io import read_json, write_json
from pcr_audit.models import Finding, LEVEL_LABEL, LEVEL_SCORE, TableResult, finding_from_mapping, validate_results


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


def _public_path(value: Any) -> str:
    return public_path(value)


def _public_finding_dict(finding: Finding) -> dict[str, Any]:
    payload = asdict(finding)
    for key in ("table", "location"):
        payload[key] = _public_path(payload.get(key) or "")
    return payload


def _confidence_percent(finding: Finding) -> str:
    return f"{max(0.0, min(1.0, float(finding.confidence_score))) * 100:.0f}%"


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
                                or "Deterministic routing determined this tool is applicable to the current material."
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
                        "path": _public_path(path),
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
                        "path": _public_path(source),
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
        "# Data Audit Report: Data Integrity and Statistical Consistency",
        "",
        "## Executive Summary",
        "",
        f"- File: `{source.name}`",
        f"- Overall risk: {LEVEL_LABEL[level]}",
        f"- Materials examined: {len(results)} groups",
        f"- Risk signals: High {counts['high']} / Medium {counts['medium']} / Low {counts['low']}",
        f"- Info records: {counts['info']}",
        "",
        "> This report only identifies risk signals in data, statistics, images, references, and process materials; it does not constitute a data integrity verification conclusion. High-risk items indicate priority for reviewing original records, lab notebooks, original figures, or statistical scripts.",
        "",
    ]
    if extraction_notes:
        lines += ["## Extraction Notes", ""]
        lines += [f"- {note}" for note in extraction_notes]
        lines.append("")

    lines += [
        "## Audit Scope and Interpretation Guide",
        "",
        "- This report is an automated pre-audit worksheet; it only records reproducible risk signals, run statuses, and coverage gaps.",
        "- Risk levels only indicate human review priority and do not constitute a data integrity verification conclusion.",
        "- `info` records are tool runs, dependency, insufficient materials, or routing statuses; they do not count as risk signals.",
        "- Tools not run or not applicable indicate insufficient materials, dependencies, or routing conditions for this audit; it does not mean the corresponding risks do not exist.",
        "",
        "## Material Inventory",
        "",
        "| Material | Role/Source | Rows | Columns | Input Type/Classification | Status | Path |",
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
    header = "| Material/Module | Rows | Columns |"
    sep = "|---|---:|---:|"
    for tool_id in tools_ordered:
        header += f" {tool_id} |"
        sep += "---|"
    lines += ["## Material Coverage Matrix", "", header, sep]
    for sheet_name in sheet_names_ordered:
        first_result = sheet_results[sheet_name][0]
        matrix_row = f"| {markdown_cell(sheet_name)} | {first_result.rows} | {first_result.columns} |"
        for tool_id in tools_ordered:
            c = sheet_tool_counts[sheet_name][tool_id]
            cell = f"H{c['high']} M{c['medium']} L{c['low']}"
            matrix_row += f" {cell} |"
        lines.append(matrix_row)
    lines.append("")

    lines += [
        "## Tool Run Details",
        "",
        "| Tool | Name | Material/Module | Status | Dependency | Runtime | Input Type | Routing/Run Basis | Method Limitations |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in tool_rows:
        lines.append(
            f"| {markdown_cell(row['tool_id'])} | {markdown_cell(_short_value(row['tool_name']))} | {markdown_cell(_short_value(row['material']))} | {markdown_cell(row['status'])} | {markdown_cell(row['dependency_status'])} | {markdown_cell(row['runtime'])} | {markdown_cell(row['input_type'])} | {markdown_cell(_short_value(row['reason']))} | {markdown_cell(_short_value(row['limitations']))} |"
        )
    lines.append("")

    lines += ["## Coverage Gaps and Skip Reasons", ""]
    if not gap_rows:
        lines += ["No unrun, dependency-missing, or material-insufficient states requiring separate explanation were recorded in this routing context.", ""]
    else:
        lines += [
            "| Tool | Material/Module | Status | Dependency | Reason | Audit Impact |",
            "|---|---|---|---|---|---|",
        ]
        for row in gap_rows:
            effect = "This tool produced no risk findings in this run; re-run after providing materials or dependencies to cover the corresponding checks."
            if row["status"] == "ready" and row["dependency_status"] != "ready":
                effect = "The tool produced run records, but dependency or material status limits coverage."
            lines.append(
                f"| {markdown_cell(row['tool_id'])} | {markdown_cell(_short_value(row['material']))} | {markdown_cell(row['status'])} | {markdown_cell(row['dependency_status'])} | {markdown_cell(_short_value(row['reason']))} | {markdown_cell(effect)} |"
            )
        lines.append("")

    lines += ["## Risk Finding List", ""]
    if not risk_findings:
        lines += ["No obvious anomalous patterns were found. Manual review against original records, study design, and statistical scripts is still recommended.", ""]
        lines += ["## Expert Review Appendix", "", "No risk findings to expand in this run.", ""]
        lines += ["## Manual Review Task List", "", "No manual review tasks were aggregated from risk findings in this run.", ""]
    else:
        ordered = sorted(risk_findings, key=lambda finding: LEVEL_SCORE[finding.level], reverse=True)
        lines += [
            "| Risk | Confidence | Evidence ID | Location | Check | Target | Finding | Evidence | Review Action |",
            "|---|---:|---|---|---|---|---|---|---|",
        ]
        for finding in ordered:
            low_confidence_note = " (Low confidence; recommend supplementing data and re-checking)" if finding.confidence_score < 0.40 else ""
            lines.append(
                f"| {LEVEL_LABEL[finding.level]} | {_confidence_percent(finding)}{low_confidence_note} | {markdown_cell(finding.evidence_id)} | {markdown_cell(_public_path(finding.location))} | {markdown_cell(finding.check)} | {markdown_cell(finding.target)} | {markdown_cell(finding.summary)} | {markdown_cell(finding.evidence)} | {markdown_cell(finding.review_actions or finding.suggestion)} |"
            )
        lines.append("")
        confidence_bins = Counter(
            "High (>=75%)" if finding.confidence_score >= 0.75 else "Medium (40%-75%)" if finding.confidence_score >= 0.40 else "Low (<40%)"
            for finding in ordered
        )
        lines += [
            "## Audit Confidence Summary",
            "",
            "| Methodological Confidence | Finding Count |",
            "|---|---:|",
        ]
        for label in ["High (>=75%)", "Medium (40%-75%)", "Low (<40%)"]:
            lines.append(f"| {label} | {confidence_bins.get(label, 0)} |")
        lines.append("")
        lines += ["## Expert Review Appendix", ""]
        for idx, finding in enumerate(ordered, start=1):
            lines += [
                f"### {idx}. {LEVEL_LABEL[finding.level]} Risk: {finding.check} ({finding.target})",
                "",
                f"- Evidence ID: {finding.evidence_id}",
                f"- Location: {_public_path(finding.location)}",
                f"- Finding: {finding.summary}",
                f"- Trigger evidence: {finding.evidence}",
                f"- Tool: {finding.tool_name or finding.tool_id} ({finding.tool_id})",
                f"- Runtime/Dependency: {finding.detector_runtime} / {finding.dependency_status}",
                f"- Input type: {finding.input_type}",
                f"- Confidence/False positive risk: {_confidence_percent(finding)} ({finding.confidence}) / {finding.false_positive_risk}",
            ]
            if finding.confidence_score < 0.40:
                lines.append("- Low confidence note: This signal has low confidence. Recommend supplementing data and re-running detection.")
            if finding.detail:
                lines.append(f"- Detail: {finding.detail}")
            if finding.calculation_trace:
                lines.append(f"- Calculation/Extraction trace: {finding.calculation_trace}")
            if finding.external_records:
                lines.append(f"- External records: {finding.external_records}")
            if finding.raw_output_ref:
                lines.append(f"- Raw output ref: {finding.raw_output_ref}")
            lines += [
                f"- Routing basis: {finding.routing_reason}",
                f"- Possible normal explanations: {finding.normal_explanations}",
                f"- Review actions: {finding.review_actions or finding.review_steps or finding.suggestion}",
                f"- Method limitations: {finding.method_limitations}",
                f"- Confidence basis: {finding.confidence_basis}",
                "",
            ]

        author_actions = []
        seen_actions = set()
        for finding in ordered:
            action = finding.review_actions or finding.review_steps or finding.suggestion
            if action and action not in seen_actions:
                seen_actions.add(action)
                author_actions.append(action)
        lines += ["## Manual Review Task List", ""]
        lines += ["| # | Review Task | Evidence Count |", "|---:|---|---:|"]
        for idx, action in enumerate(author_actions[:12], start=1):
            evidence_count = sum(
                1 for finding in ordered if (finding.review_actions or finding.review_steps or finding.suggestion) == action
            )
            lines.append(f"| {idx} | {markdown_cell(action)} | {evidence_count} |")
        lines.append("")

    lines += ["## Info Records (Not Risk)", ""]
    lines += ["| Tool | Record Count |", "|---|---:|"]
    for tool_id, count in sorted(tool_counts.items()):
        lines.append(f"| {markdown_cell(tool_id)} | {count} |")
    lines.append("")
    if info_findings:
        for finding in info_findings[:30]:
            lines.append(
                f"- `{finding.tool_id}`: {finding.summary} ({finding.evidence}; dependency={finding.dependency_status}; input_type={finding.input_type})"
            )
        if len(info_findings) > 30:
            lines.append(f"- The remaining {len(info_findings) - 30} info records are in JSON.")
        lines.append("")
    else:
        lines += ["No info records.", ""]

    return "\n".join(lines) + "\n"


def save_json(path: Path, source: Path, results: list[TableResult]) -> None:
    validate_results(results)
    payload = {
        "source": _public_path(source),
        "results": [
            {
                "name": result.name,
                "rows": result.rows,
                "columns": result.columns,
                "findings": [_public_finding_dict(finding) for finding in result.findings],
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
        sources.append(_public_path(payload.get("source") or item))
        all_results.extend(results_from_payload(payload))

    pseudo_source = Path(sources[0] if len(sources) == 1 else "merged-findings.json")
    audit_context = _collect_audit_context(finding_paths)
    out.write_text(
        render_markdown(pseudo_source, all_results, ["This report was generated by merging multiple CLI finding JSONs."], audit_context),
        encoding="utf-8",
    )
    if json_out:
        validate_results(all_results)
        write_json(
            json_out,
            {
                "source": sources,
                "results": [
                    {
                        "name": result.name,
                        "rows": result.rows,
                        "columns": result.columns,
                        "findings": [_public_finding_dict(finding) for finding in result.findings],
                    }
                    for result in all_results
                ],
            },
        )
