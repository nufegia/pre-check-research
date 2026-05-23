from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

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


def _selected_input_type(selected: dict[str, list[dict[str, Any]]], tool_id: str) -> str:
    decisions = selected.get(tool_id) or []
    for decision in decisions:
        input_type = str(decision.get("matched_input_type") or "")
        if input_type:
            return input_type
    return "unknown"


def _exception_evidence(exc: BaseException) -> str:
    message = str(exc).strip()
    if len(message) > 500:
        message = message[:499] + "…"
    return f"{exc.__class__.__name__}: {message or '<no message>'}"


def _append_runtime_error(payloads: list[dict[str, Any]], source: Path, tool_id: str, exc: BaseException, input_type: str = "unknown") -> None:
    payloads.append(
        info_payload(
            source,
            tool_id,
            f"{tool_id} 运行异常，已记录为运行提示并继续生成报告。",
            _exception_evidence(exc),
            "runtime_error",
            input_type,
        )
    )


def _run_adapter_safely(
    context: AuditRunContext,
    tool_id: str,
    selected: dict[str, list[dict[str, Any]]],
    adapter: Callable[[AuditRunContext, str], None],
) -> None:
    try:
        adapter(context, tool_id)
    except Exception as exc:
        _append_runtime_error(context.payloads, context.source, tool_id, exc, _selected_input_type(selected, tool_id))


def _run_product_result_payload(source: Path, json_path: Path, results: list[TableResult]) -> dict[str, Any]:
    save_json(json_path, source, results)
    return read_json(json_path)


def _append_result_safely(
    results: list[TableResult],
    source: Path,
    tool_id: str,
    fn: Callable[[], TableResult | list[TableResult]],
    input_type: str = "project_manifest",
) -> None:
    try:
        value = fn()
    except Exception as exc:
        payload = info_payload(source, tool_id, f"{tool_id} 运行异常，已跳过该模块。", _exception_evidence(exc), "runtime_error", input_type)
        results.extend(_payload_to_results(payload))
        return
    if isinstance(value, list):
        results.extend(value)
    else:
        results.append(value)


def _payload_to_results(payload: dict[str, Any]) -> list[TableResult]:
    from pcr_audit.reporting import results_from_payload

    return results_from_payload(payload)


def _deliver_payloads(source: Path, payloads: list[dict[str, Any]], out: Path, json_out: Path | None, workdir: Path, prefix: str) -> None:
    part_paths: list[str] = []
    for idx, payload in enumerate(payloads, start=1):
        path = workdir / f"{prefix}-{idx}.json"
        write_json(path, payload)
        part_paths.append(str(path))
    try:
        merge_reports(part_paths, out, json_out)
    except Exception as exc:
        fallback = workdir / f"{prefix}-delivery-error.json"
        write_json(fallback, info_payload(source, "pcr_audit_delivery", "结果合并失败，已生成交付失败诊断。", _exception_evidence(exc), "runtime_error"))
        merge_reports([str(fallback)], out, json_out)


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
        _run_adapter_safely(context, tool_id, selected, adapter)
    if context.product_results:
        try:
            payloads.append(_run_product_result_payload(source, workdir / "product-detectors.json", context.product_results))
        except Exception as exc:
            payloads.append(info_payload(source, "product_detectors", "产品级检测结果序列化失败，已记录为运行提示。", _exception_evidence(exc), "runtime_error"))
    for tool_id in R_ADAPTER_ORDER:
        if tool_id not in ready_tools:
            continue
        adapter = adapter_for(tool_id)
        if adapter is None:
            payloads.append(info_payload(source, tool_id, "工具 adapter 未注册，已跳过。", tool_id, "adapter_missing"))
            continue
        _run_adapter_safely(context, tool_id, selected, adapter)

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

    _deliver_payloads(source, payloads, out, json_out, workdir, "part")
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
    try:
        spec, config = parse_project_spec(source, config_override, workdir)
    except Exception as exc:
        _deliver_payloads(
            source,
            [
                info_payload(
                    source,
                    "project_audit",
                    "项目材料解析失败，已生成诊断报告。",
                    _exception_evidence(exc),
                    "runtime_error",
                    "project_manifest",
                )
            ],
            out,
            json_out,
            workdir,
            "project-part",
        )
        return 0
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
        try:
            if run_audit(data_source, part_out, part_json, workdir / f"data-{idx}.parts", "auto", False) == 0:
                payloads.append(read_json(part_json))
        except Exception as exc:
            payloads.append(
                info_payload(
                    data_source,
                    "pcr_audit_run",
                    "数据材料子审计运行异常，已记录为运行提示并继续项目审计。",
                    _exception_evidence(exc),
                    "runtime_error",
                    "raw_data",
                )
            )

    project_results: list[TableResult] = []
    if spec.findings:
        project_results.append(TableResult("project_manifest", len(spec.materials), 0, spec.findings))
    try:
        provenance = analyze_provenance_paths(source, sources["all"]) if sources["all"] else analyze_provenance(source)
    except Exception as exc:
        provenance = _payload_to_results(info_payload(source, "provenance_hash", "材料哈希计算异常，已跳过该模块。", _exception_evidence(exc), "runtime_error", "project_manifest"))[0]
    sandbox_source = source.parent if source.is_file() else source
    try:
        code_result, derived_outputs = run_code_sandbox(sandbox_source, sources["code"], workdir, code_timeout, rerun_code)
    except Exception as exc:
        code_result = _payload_to_results(info_payload(source, "code_rerun_execute", "分析脚本沙箱复跑异常，已跳过复跑。", _exception_evidence(exc), "runtime_error", "analysis_code"))[0]
        derived_outputs = []
    project_results.append(provenance)
    _append_result_safely(project_results, source, "provenance_chain_verify", lambda: provenance_payload_to_result(source, provenance_verify(source)))
    _append_result_safely(project_results, source, "code_rerun_audit", lambda: analyze_code_files(source), "analysis_code")
    project_results.append(code_result)
    _append_result_safely(project_results, source, "data_trace_crosscheck", lambda: analyze_data_trace(sources["documents"], sources["data"], derived_outputs))
    _append_result_safely(project_results, source, "papermill_network_signals", lambda: analyze_papermill_network_signals(source))
    for doc in sources["documents"][:20]:
        if doc.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}:
            _append_result_safely(project_results, doc, "reference_audit", lambda doc=doc: analyze_references(doc, config), "paper_document")
            _append_result_safely(project_results, doc, "citation_claim_check", lambda doc=doc: analyze_citation_claims(doc, config), "paper_document")
            _append_result_safely(project_results, doc, "papermill_light_signals", lambda doc=doc: analyze_papermill_signals(doc, config), "paper_document")
            _append_result_safely(project_results, doc, "image_extract", lambda doc=doc: analyze_images(doc, workdir / f"images-{doc.stem}"), "scientific_figure")
    if sources["images"]:
        _append_result_safely(project_results, source, "image_extract", lambda: analyze_images(source, workdir / "images-project"), "scientific_figure")
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
    try:
        save_json(project_json, source, project_results)
        payloads.append(read_json(project_json))
    except Exception as exc:
        payloads.append(info_payload(source, "project_detectors", "项目级检测结果序列化失败，已记录为运行提示。", _exception_evidence(exc), "runtime_error", "project_manifest"))

    if not payloads:
        return 1
    _deliver_payloads(source, payloads, out, json_out, workdir, "project-part")
    return 0
