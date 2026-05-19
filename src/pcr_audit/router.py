from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from pcr_audit.io import load_tables, read_text_source
from pcr_audit.tool_system import classify_table, classify_text, route_all_tools, source_kind


def selected_tools_for_scenario(scenario: str, input_types: list[str]) -> set[str]:
    if scenario == "auto":
        selected: set[str] = set()
        if "raw_observation_table" in input_types or "figure_source_data" in input_types:
            selected.update({"raw_data_rules", "digit_distribution"})
        if "summary_statistics_table" in input_types or "continuous_measure_summary" in input_types:
            selected.update({"r_scrutiny", "crosscheck"})
        if "likert_or_integer_scale_summary" in input_types:
            selected.update({"r_scrutiny", "r_rsprite2", "crosscheck"})
        if "apa_statistical_text" in input_types:
            selected.add("r_statcheck")
        if "reference_list" in input_types or "paper_document" in input_types:
            selected.update({"reference_audit", "citation_claim_check", "papermill_light_signals"})
        if any(item in input_types for item in ("scientific_image", "scientific_figure", "western_blot_or_gel_image")):
            selected.update({"image_extract", "image_duplicate_internal", "image_copy_move_internal", "image_metadata_audit", "western_blot_review_list"})
        if "analysis_code" in input_types:
            selected.update({"code_rerun_audit", "code_rerun_execute"})
        if "p_value_collection" in input_types:
            selected.add("p_value_distribution")
        return selected
    if scenario == "raw":
        return {"raw_data_rules"}
    if scenario == "summary":
        return {"r_scrutiny", "crosscheck"}
    if scenario == "r-advanced":
        return {"r_rsprite2"}
    if scenario == "text":
        return {"r_statcheck", "reference_audit", "citation_claim_check", "papermill_light_signals"}
    return set()


def routing_decisions_payload(decisions: dict[str, Any]) -> dict[str, Any]:
    return {tool_id: asdict(decision) for tool_id, decision in decisions.items()}


def build_route_payload(source: Path, scenario: str = "auto") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": str(source),
        "source_kind": source_kind(source),
        "scenario": scenario,
        "tables": [],
        "text": None,
    }

    if source.is_dir():
        classification = {"primary_type": "project_manifest", "input_types": ["project_manifest", "raw_file_bundle"], "signals": {}}
        selected = selected_tools_for_scenario(scenario, classification["input_types"])
        delegated = {
            "tables": ["raw_data_rules", "digit_distribution", "crosscheck", "r_scrutiny", "r_rsprite2", "p_value_distribution"],
            "documents": ["r_statcheck", "reference_audit", "citation_claim_check", "papermill_light_signals", "image_extract"],
            "images": ["image_extract", "image_duplicate_internal", "image_copy_move_internal", "image_metadata_audit", "western_blot_review_list"],
            "code": ["code_rerun_audit", "code_rerun_execute"],
        }
        selected.update({"provenance_hash", "provenance_chain_verify", "code_rerun_audit", "code_rerun_execute", "data_trace_crosscheck", "papermill_network_signals"})
        decisions = route_all_tools(selected, classification["input_types"], 0, [])
        payload["project"] = {
            "classification": classification,
            "delegated_material_tools": delegated,
            "delegation_note": "项目审计会先解析材料清单，再按每个文件的数据类型委派表格、文本、图像和代码工具；这里的 routing_decisions 只表示项目级工具。",
            "routing_decisions": routing_decisions_payload(decisions),
        }
        return payload

    if source.suffix.lower() == ".json":
        try:
            manifest = json.loads(source.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
        is_corpus = any(key in manifest for key in ("projects", "corpus", "items"))
        classification = {
            "primary_type": "corpus_manifest" if is_corpus else "project_manifest",
            "input_types": ["project_manifest", "raw_file_bundle"] if not is_corpus else ["project_manifest", "raw_file_bundle", "corpus_manifest"],
            "signals": {"corpus_manifest": is_corpus},
        }
        delegated = {
            "tables": ["raw_data_rules", "digit_distribution", "crosscheck", "r_scrutiny", "r_rsprite2", "p_value_distribution"],
            "documents": ["r_statcheck", "reference_audit", "citation_claim_check", "papermill_light_signals", "image_extract"],
            "images": ["image_extract", "image_duplicate_internal", "image_copy_move_internal", "image_metadata_audit", "western_blot_review_list"],
            "code": ["code_rerun_audit", "code_rerun_execute"],
        }
        selected = selected_tools_for_scenario(scenario, classification["input_types"])
        selected.update({"provenance_hash", "provenance_chain_verify", "papermill_network_signals", "data_trace_crosscheck", "code_rerun_audit", "code_rerun_execute"})
        decisions = route_all_tools(selected, classification["input_types"], 0, [])
        payload["project"] = {
            "classification": classification,
            "delegated_material_tools": delegated,
            "delegation_note": "项目审计会先解析材料清单，再按每个文件的数据类型委派表格、文本、图像和代码工具；这里的 routing_decisions 只表示项目级工具。",
            "routing_decisions": routing_decisions_payload(decisions),
        }
        return payload

    if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        primary = "western_blot_or_gel_image" if any(token in source.name.lower() for token in ("blot", "western", "gel", "wb")) else "scientific_image"
        input_types = [primary, "scientific_figure"]
        classification = {"primary_type": primary, "input_types": input_types, "signals": {"image_file": True}}
        selected = selected_tools_for_scenario(scenario, input_types)
        decisions = route_all_tools(selected, input_types, 1, [])
        payload["image"] = {
            "classification": classification,
            "routing_decisions": routing_decisions_payload(decisions),
        }
        return payload

    if source.suffix in {".py", ".r", ".R", ".do", ".sps", ".sas"}:
        classification = {"primary_type": "analysis_code", "input_types": ["analysis_code"], "signals": {"code_file": True}}
        selected = selected_tools_for_scenario(scenario, classification["input_types"])
        decisions = route_all_tools(selected, classification["input_types"], 1, [])
        payload["code"] = {
            "classification": classification,
            "routing_decisions": routing_decisions_payload(decisions),
        }
        return payload

    if source.suffix.lower() in {".txt", ".md", ".bib", ".ris"}:
        text = read_text_source(source)
        classification = classify_text(text)
        selected = selected_tools_for_scenario(scenario, classification["input_types"])
        decisions = route_all_tools(selected, classification["input_types"], 0, [])
        payload["text"] = {
            "length": len(text),
            "classification": classification,
            "routing_decisions": routing_decisions_payload(decisions),
        }
        return payload

    if source.suffix.lower() in {".pdf", ".docx"}:
        try:
            text = read_text_source(source)
        except Exception:
            text = ""
        if text:
            classification = classify_text(text)
            if "paper_document" not in classification["input_types"]:
                classification["input_types"].append("paper_document")
            selected = selected_tools_for_scenario(scenario, classification["input_types"])
            decisions = route_all_tools(selected, classification["input_types"], 0, [])
            payload["text"] = {
                "length": len(text),
                "classification": classification,
                "routing_decisions": routing_decisions_payload(decisions),
            }

    try:
        tables = load_tables(source)
    except Exception as exc:
        payload["table_error"] = str(exc)
        return payload

    for name, df in tables:
        classification = classify_table(df, source.suffix)
        selected = selected_tools_for_scenario(scenario, classification["input_types"])
        decisions = route_all_tools(selected, classification["input_types"], int(df.shape[0]), list(map(str, df.columns)))
        payload["tables"].append(
            {
                "name": name,
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
                "classification": classification,
                "routing_decisions": routing_decisions_payload(decisions),
            }
        )
    return payload


def selected_route_decisions(route_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    items = list(route_payload.get("tables") or [])
    for key in ("text", "image", "code", "project"):
        if route_payload.get(key):
            items.append(route_payload[key])
    for item in items:
        for tool_id, decision in (item.get("routing_decisions") or {}).items():
            if decision.get("selected_by_user"):
                selected.setdefault(tool_id, []).append(decision)
    return selected


def ready_tool_ids(route_payload: dict[str, Any]) -> set[str]:
    selected = selected_route_decisions(route_payload)
    return {tool_id for tool_id, decisions in selected.items() if any(d.get("status") == "ready" for d in decisions)}
