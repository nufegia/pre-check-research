from __future__ import annotations

import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pcr_audit.adapters import AuditRunContext, adapter_for, register_adapter
from pcr_audit.detectors.raw import analyze_raw_data_rules
from pcr_audit.io import extract_file, load_tables, read_json, write_extracted_text, write_json
from pcr_audit.models import TableResult, info_finding
from pcr_audit.reporting import merge_reports, save_json
from pcr_audit.router import build_route_payload, ready_tool_ids, selected_route_decisions


ROOT = Path(__file__).resolve().parents[2]
R_TOOL_PATHS = {
    "statcheck": ROOT / "tools" / "r" / "pcr_statcheck" / "pcr-statcheck",
    "scrutiny": ROOT / "tools" / "r" / "pcr_scrutiny" / "pcr-scrutiny",
    "sprite": ROOT / "tools" / "r" / "pcr_sprite" / "pcr-sprite",
}
R_TOOL_COMMANDS = {
    "statcheck": "pcr-statcheck",
    "scrutiny": "pcr-scrutiny",
    "sprite": "pcr-sprite",
}
R_TOOL_BY_ID = {
    "r_statcheck": "statcheck",
    "r_scrutiny": "scrutiny",
    "r_rsprite2": "sprite",
}

PYTHON_ADAPTER_ORDER = [
    "raw_data_rules",
    "digit_distribution",
    "p_value_distribution",
    "crosscheck",
    "reference_audit",
    "citation_claim_check",
    "papermill_light_signals",
    "papermill_network_signals",
    "image_extract",
    "image_duplicate_internal",
    "image_copy_move_internal",
    "image_metadata_audit",
    "western_blot_review_list",
    "provenance_hash",
    "provenance_chain_verify",
    "code_rerun_audit",
    "code_rerun_execute",
]
R_ADAPTER_ORDER = ["r_statcheck", "r_scrutiny", "r_rsprite2"]


def info_payload(
    source: Path,
    tool_id: str,
    summary: str,
    evidence: str,
    dependency_status: str = "dependency_missing",
    input_type: str = "unknown",
) -> dict[str, Any]:
    finding = info_finding(str(source), tool_id, summary, evidence, dependency_status, input_type)
    return {
        "tool_id": tool_id,
        "tool_name": tool_id,
        "detector_runtime": "cli",
        "dependency_status": dependency_status,
        "source": str(source),
        "input_type": input_type,
        "findings": [asdict(finding)],
    }


def _tool_available(path: Path) -> bool:
    return path.exists() and path.is_file()


def _find_r_tool(tool_key: str) -> str | None:
    import shutil

    command = R_TOOL_COMMANDS[tool_key]
    path = shutil.which(command)
    if path:
        return path
    repo_path = R_TOOL_PATHS[tool_key]
    if _tool_available(repo_path):
        return str(repo_path)
    return None


def _append_non_ready_route_infos(source: Path, payloads: list[dict[str, Any]], selected: dict[str, list[dict[str, Any]]]) -> None:
    for tool_id, decisions in selected.items():
        if any(decision.get("status") == "ready" for decision in decisions):
            continue
        decision = decisions[0]
        payloads.append(
            info_payload(
                source,
                tool_id,
                f"{decision.get('tool_name') or tool_id} 未运行：{decision.get('status')}",
                str(decision.get("skip_reason") or "当前路由规则判定该工具不可运行。"),
                str(decision.get("dependency_status") or decision.get("status") or "not_applicable"),
                str(decision.get("matched_input_type") or "unknown"),
            )
        )


def _ready_tables_for_tool(source: Path, route_payload: dict[str, Any], tool_id: str):
    route_tables = route_payload.get("tables", [])
    for table_route, (name, df) in zip(route_tables, load_tables(source), strict=False):
        decision = table_route.get("routing_decisions", {}).get(tool_id, {})
        if decision.get("status") == "ready":
            yield name, df


def _run_raw_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    results = [analyze_raw_data_rules(name, df) for name, df in _ready_tables_for_tool(source, route_payload, "raw_data_rules")]
    save_json(json_path, source, results)
    return read_json(json_path)


def _run_crosscheck_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    from pcr_audit.crosscheck import crosscheck_table

    results = [crosscheck_table(name, df) for name, df in _ready_tables_for_tool(source, route_payload, "crosscheck")]
    save_json(json_path, source, results)
    return read_json(json_path)


def _run_digit_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    from pcr_audit.detectors.raw_legacy import analyze_digit_distribution_rules
    from pcr_audit.models import finding_from_mapping

    results = []
    for name, df in _ready_tables_for_tool(source, route_payload, "digit_distribution"):
        legacy = analyze_digit_distribution_rules(name, df)
        findings = [finding_from_mapping(name, asdict(item)) for item in legacy.findings]
        results.append(TableResult(name, legacy.rows, legacy.columns, findings))
    save_json(json_path, source, results)
    return read_json(json_path)


def _run_p_value_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    from pcr_audit.detectors.p_values import analyze_p_value_collection

    results = [analyze_p_value_collection(name, df) for name, df in _ready_tables_for_tool(source, route_payload, "p_value_distribution")]
    save_json(json_path, source, results)
    return read_json(json_path)


def _run_product_result_payload(source: Path, json_path: Path, results: list[TableResult]) -> dict[str, Any]:
    save_json(json_path, source, results)
    return read_json(json_path)


def _run_r_tool_payload(source: Path, tool_id: str, input_path: Path, workdir: Path, payloads: list[dict[str, Any]]) -> None:
    tool_key = R_TOOL_BY_ID[tool_id]
    tool = _find_r_tool(tool_key)
    out_json = workdir / f"{tool_key}.json"
    if not tool:
        payloads.append(info_payload(source, tool_id, "对应 R CLI 不存在，已跳过。", R_TOOL_COMMANDS[tool_key]))
        return

    actual_input = input_path
    if tool_key == "statcheck":
        text_file = write_extracted_text(input_path, workdir)
        if text_file:
            actual_input = text_file

    proc = subprocess.run([tool, str(actual_input), "--json", str(out_json)], capture_output=True, text=True)
    if out_json.exists():
        payloads.append(read_json(out_json))
    elif proc.returncode != 0:
        payloads.append(info_payload(source, tool_id, "R CLI 运行失败，已跳过。", proc.stderr.strip()))


def _csv_inputs_for_r_tool(
    source: Path,
    workdir: Path,
    route_payload: dict[str, Any],
    tool_id: str,
    extraction_manifest: dict[str, Any] | None,
) -> tuple[list[Path], dict[str, Any] | None]:
    ready_tables = [
        table
        for table in route_payload.get("tables", [])
        if table.get("routing_decisions", {}).get(tool_id, {}).get("status") == "ready"
    ]
    if not ready_tables:
        return [], extraction_manifest
    if source.suffix.lower() == ".csv":
        return [source], extraction_manifest
    if extraction_manifest is None:
        extraction_manifest = extract_file(source, workdir / "extracted")
    paths: list[Path] = []
    for table, item in zip(route_payload.get("tables", []), extraction_manifest.get("outputs", []), strict=False):
        decision = table.get("routing_decisions", {}).get(tool_id, {})
        if decision.get("status") == "ready" and item.get("kind") == "table":
            paths.append(Path(item["path"]))
    return paths, extraction_manifest


def _raw_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(_run_raw_payload(context.source, context.workdir / "raw-audit.json", context.route_payload))


def _digit_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(_run_digit_payload(context.source, context.workdir / "digit-distribution.json", context.route_payload))


def _p_value_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(_run_p_value_payload(context.source, context.workdir / "p-value-distribution.json", context.route_payload))


def _crosscheck_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(_run_crosscheck_payload(context.source, context.workdir / "crosscheck.json", context.route_payload))


def _product_adapter(context: AuditRunContext, tool_id: str) -> None:
    from pcr_audit.data_trace import run_code_sandbox
    from pcr_audit.product import code_audit, corpus_signals, image_audit, provenance, reference_audit

    if tool_id == "reference_audit":
        context.product_results.append(reference_audit.analyze_references(context.source))
    elif tool_id == "citation_claim_check":
        context.product_results.append(reference_audit.analyze_citation_claims(context.source))
    elif tool_id == "papermill_light_signals":
        context.product_results.append(reference_audit.analyze_papermill_signals(context.source))
    elif tool_id == "papermill_network_signals":
        context.product_results.append(corpus_signals.analyze_papermill_network_signals(context.source))
    elif tool_id in {"image_extract", "image_duplicate_internal", "image_copy_move_internal", "image_metadata_audit", "western_blot_review_list"}:
        if not any(result.name in {"image_extract", "image_duplicate_internal", "image_copy_move_internal", "image_metadata_audit", "western_blot_review_list"} for result in context.product_results):
            context.product_results.extend(image_audit.analyze_images(context.source, context.workdir / "images"))
    elif tool_id == "provenance_hash":
        context.product_results.append(provenance.analyze_provenance(context.source))
    elif tool_id == "provenance_chain_verify":
        context.product_results.append(provenance.provenance_payload_to_result(context.source, provenance.provenance_verify(context.source)))
    elif tool_id == "code_rerun_audit":
        context.product_results.append(code_audit.analyze_code_files(context.source))
    elif tool_id == "code_rerun_execute":
        code_result, _derived_outputs = run_code_sandbox(context.source, [context.source], context.workdir, 60, True)
        context.product_results.append(code_result)


def _r_adapter(context: AuditRunContext, tool_id: str) -> None:
    if tool_id == "r_statcheck":
        _run_r_tool_payload(context.source, tool_id, context.source, context.workdir, context.payloads)
        return
    try:
        r_inputs, context.extraction_manifest = _csv_inputs_for_r_tool(
            context.source,
            context.workdir,
            context.route_payload,
            tool_id,
            context.extraction_manifest,
        )
    except Exception as exc:
        context.payloads.append(info_payload(context.source, tool_id, "表格抽取失败，R CLI 已跳过。", str(exc), "extract_failed"))
        return
    for idx, r_input in enumerate(r_inputs, start=1):
        tool_workdir = context.workdir / f"{tool_id}_{idx}"
        tool_workdir.mkdir(parents=True, exist_ok=True)
        _run_r_tool_payload(context.source, tool_id, r_input, tool_workdir, context.payloads)


def _register_builtin_adapters() -> None:
    register_adapter("raw_data_rules", _raw_adapter)
    register_adapter("digit_distribution", _digit_adapter)
    register_adapter("p_value_distribution", _p_value_adapter)
    register_adapter("crosscheck", _crosscheck_adapter)
    for tool_id in PYTHON_ADAPTER_ORDER:
        if tool_id not in {"raw_data_rules", "digit_distribution", "p_value_distribution", "crosscheck"}:
            register_adapter(tool_id, _product_adapter)
    for tool_id in R_ADAPTER_ORDER:
        register_adapter(tool_id, _r_adapter)


_register_builtin_adapters()


def run_audit(
    source: Path,
    out: Path,
    json_out: Path | None = None,
    workdir: Path | None = None,
    scenario: str = "auto",
    dry_run: bool = False,
) -> int:
    workdir = workdir or out.with_suffix(".parts")
    workdir.mkdir(parents=True, exist_ok=True)

    route_payload = build_route_payload(source, scenario)
    write_json(workdir / "route.json", route_payload)
    if dry_run:
        if json_out:
            write_json(json_out, route_payload)
        print_json = False
        return 0 if not print_json else 0

    selected = selected_route_decisions(route_payload)
    ready_tools = ready_tool_ids(route_payload)
    payloads: list[dict[str, Any]] = []
    context = AuditRunContext(source=source, workdir=workdir, route_payload=route_payload, payloads=payloads)
    for tool_id in PYTHON_ADAPTER_ORDER:
        if tool_id not in ready_tools:
            continue
        adapter = adapter_for(tool_id)
        if adapter is None:
            payloads.append(info_payload(source, tool_id, "工具 adapter 未注册，已跳过。", tool_id, "adapter_missing"))
            continue
        adapter(context, tool_id)
    if context.product_results:
        payloads.append(_run_product_result_payload(source, workdir / "product-detectors.json", context.product_results))
    for tool_id in R_ADAPTER_ORDER:
        if tool_id not in ready_tools:
            continue
        adapter = adapter_for(tool_id)
        if adapter is None:
            payloads.append(info_payload(source, tool_id, "工具 adapter 未注册，已跳过。", tool_id, "adapter_missing"))
            continue
        adapter(context, tool_id)

    _append_non_ready_route_infos(source, payloads, selected)
    if not selected:
        payloads.append(
            info_payload(
                source,
                "pcr_audit_route",
                "确定性路由未找到适用工具。",
                "当前输入未匹配任何自动工具选择规则。",
                "not_applicable",
            )
        )
    if not payloads:
        return 1

    part_paths: list[str] = []
    for idx, payload in enumerate(payloads, start=1):
        path = workdir / f"part-{idx}.json"
        write_json(path, payload)
        part_paths.append(str(path))
    merge_reports(part_paths, out, json_out)
    return 0


def run_project_audit(
    source: Path,
    out: Path,
    json_out: Path | None = None,
    workdir: Path | None = None,
    external_lookups: bool = True,
    grobid_url: str = "",
    contact_email: str = "",
    rerun_code: bool = True,
    code_timeout: int = 60,
) -> int:
    from pcr_audit.product_detectors import (
        AuditConfig,
        analyze_citation_claims,
        analyze_code_files,
        analyze_images,
        analyze_papermill_network_signals,
        analyze_papermill_signals,
        analyze_provenance,
        analyze_provenance_paths,
        analyze_references,
        provenance_payload_to_result,
        provenance_verify,
        parse_project_spec,
    )
    from pcr_audit.data_trace import analyze_data_trace, run_code_sandbox

    workdir = workdir or out.with_suffix(".parts")
    workdir.mkdir(parents=True, exist_ok=True)
    config_override = AuditConfig(
        external_lookups=external_lookups,
        grobid_url=grobid_url,
        contact_email=contact_email,
        lookup_cache_dir=workdir / "lookup-cache",
    )
    spec, config = parse_project_spec(source, config_override, workdir)
    config.external_lookups = external_lookups
    sources = {
        "documents": [m.path for m in spec.materials if m.role in {"manuscript", "references", "supplement"} and m.path.suffix.lower() in {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".xls"}],
        "data": [m.path for m in spec.materials if m.role == "raw_data" or m.path.suffix.lower() in {".csv", ".xlsx", ".xls"}],
        "images": [m.path for m in spec.materials if m.role in {"figures", "image"} or m.path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}],
        "code": [m.path for m in spec.materials if m.role == "analysis_code" or m.path.suffix in {".py", ".r", ".R", ".do", ".sps", ".sas"}],
        "all": [m.path for m in spec.materials],
    }
    write_json(
        workdir / "project-route.json",
        {
            "source": str(source),
            "source_kind": "project",
            "project_id": spec.project_id,
            "title": spec.title,
            "counts": {key: len(value) for key, value in sources.items()},
            "materials": [{"path": str(material.path), "role": material.role} for material in spec.materials],
            "policy": {
                "external_lookups": "enabled" if config.external_lookups else "disabled",
                "grobid_url": config.grobid_url,
                "contact_email": config.contact_email,
                "pyMuPDF": "not_used_due_to_license_review",
                "imagehash": "not_used; local Pillow/numpy hash only",
            },
        },
    )
    payloads: list[dict[str, Any]] = []

    for idx, data_source in enumerate(sources["data"], start=1):
        part_out = workdir / f"data-{idx}.md"
        part_json = workdir / f"data-{idx}.json"
        if run_audit(data_source, part_out, part_json, workdir / f"data-{idx}.parts", "auto", False) == 0:
            payloads.append(read_json(part_json))

    project_results: list[TableResult] = []
    if spec.findings:
        project_results.append(TableResult("project_manifest", len(spec.materials), 0, spec.findings))
    provenance = analyze_provenance_paths(source, sources["all"]) if sources["all"] else analyze_provenance(source)
    sandbox_source = source.parent if source.is_file() else source
    code_result, derived_outputs = run_code_sandbox(sandbox_source, sources["code"], workdir, code_timeout, rerun_code)
    project_results.extend(
        [
            provenance,
            provenance_payload_to_result(source, provenance_verify(source)),
            analyze_code_files(source),
            code_result,
            analyze_data_trace(sources["documents"], sources["data"], derived_outputs),
            analyze_papermill_network_signals(source),
        ]
    )
    for doc in sources["documents"][:20]:
        if doc.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}:
            project_results.extend([analyze_references(doc, config), analyze_citation_claims(doc, config), analyze_papermill_signals(doc, config)])
            project_results.extend(analyze_images(doc, workdir / f"images-{doc.stem}"))
    if sources["images"]:
        project_results.extend(analyze_images(source, workdir / "images-project"))
    if not sources["documents"] and not sources["images"] and not sources["code"]:
        project_results.append(
            TableResult(
                "project_audit",
                0,
                0,
                [
                    info_finding(
                        str(source),
                        "project_audit",
                        "项目级审计未发现文档、图像或代码材料。",
                        "仍会对数据文件运行可用检测并计算哈希。",
                        "insufficient_material",
                        "project_manifest",
                    )
                ],
            )
        )
    project_json = workdir / "project-detectors.json"
    save_json(project_json, source, project_results)
    payloads.append(read_json(project_json))

    if not payloads:
        return 1
    part_paths: list[str] = []
    for idx, payload in enumerate(payloads, start=1):
        path = workdir / f"project-part-{idx}.json"
        write_json(path, payload)
        part_paths.append(str(path))
    merge_reports(part_paths, out, json_out)
    return 0
