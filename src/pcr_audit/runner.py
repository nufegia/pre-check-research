from __future__ import annotations

from pathlib import Path
from typing import Any

from pcr_audit.adapter_runtime import PYTHON_ADAPTER_ORDER, R_ADAPTER_ORDER, AuditRunContext, adapter_for, info_payload
from pcr_audit.io import read_json, write_json
from pcr_audit.models import TableResult, info_finding
from pcr_audit.reporting import merge_reports, save_json
from pcr_audit.router import build_route_payload, ready_tool_ids, selected_route_decisions


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


def _run_product_result_payload(source: Path, json_path: Path, results: list[TableResult]) -> dict[str, Any]:
    save_json(json_path, source, results)
    return read_json(json_path)


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
    from pcr_audit.product.common import AuditConfig
    from pcr_audit.product.code_audit import analyze_code_files
    from pcr_audit.product.corpus_signals import analyze_papermill_network_signals
    from pcr_audit.product.image_audit import analyze_images
    from pcr_audit.product.project_manifest import parse_project_spec
    from pcr_audit.product.provenance import (
        analyze_provenance,
        analyze_provenance_paths,
        provenance_payload_to_result,
        provenance_verify,
    )
    from pcr_audit.product.reference_audit import (
        analyze_citation_claims,
        analyze_papermill_signals,
        analyze_references,
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
