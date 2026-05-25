from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from pcr_audit.io import load_tables, read_text_source
from pcr_audit.tool_system import classify_table, classify_text, route_all_tools, source_kind


AUTO_TOOL_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("raw_observation_table", "figure_source_data"), ("raw_data_rules",)),
    (("summary_statistics_table", "continuous_measure_summary"), ("r_scrutiny", "crosscheck")),
    (("likert_or_integer_scale_summary",), ("r_scrutiny", "r_rsprite2", "crosscheck")),
    (("apa_statistical_text",), ("r_statcheck",)),
    (("reference_list", "paper_document"), ("reference_audit", "citation_claim_check", "papermill_light_signals")),
    (("scientific_image", "scientific_figure", "western_blot_or_gel_image"), ("image_extract", "image_duplicate_internal", "image_copy_move_internal", "image_metadata_audit", "western_blot_review_list")),
    (("analysis_code",), ("code_rerun_audit", "code_rerun_execute")),
    (("p_value_collection",), ("p_value_distribution",)),
)

SCENARIO_TOOL_SELECTIONS: dict[str, set[str]] = {
    "raw": {"raw_data_rules"},
    "summary": {"r_scrutiny", "crosscheck"},
    "r-advanced": {"r_rsprite2"},
    "text": {"r_statcheck", "reference_audit", "citation_claim_check", "papermill_light_signals"},
}

PROJECT_LEVEL_TOOLS = {
    "provenance_hash",
    "provenance_chain_verify",
    "code_rerun_audit",
    "code_rerun_execute",
    "data_trace_crosscheck",
    "papermill_network_signals",
}

PROJECT_DELEGATED_MATERIAL_TOOLS = {
    "tables": ["raw_data_rules", "crosscheck", "r_scrutiny", "r_rsprite2", "p_value_distribution"],
    "documents": ["r_statcheck", "reference_audit", "citation_claim_check", "papermill_light_signals", "image_extract"],
    "images": ["image_extract", "image_duplicate_internal", "image_copy_move_internal", "image_metadata_audit", "western_blot_review_list"],
    "code": ["code_rerun_audit", "code_rerun_execute"],
}


def selected_tools_for_scenario(scenario: str, input_types: list[str]) -> set[str]:
    if scenario == "auto":
        selected: set[str] = set()
        for matched_types, tool_ids in AUTO_TOOL_RULES:
            if any(input_type in input_types for input_type in matched_types):
                selected.update(tool_ids)
        return selected
    return set(SCENARIO_TOOL_SELECTIONS.get(scenario, set()))


def project_delegated_material_tools() -> dict[str, list[str]]:
    return {key: list(value) for key, value in PROJECT_DELEGATED_MATERIAL_TOOLS.items()}


def routing_decisions_payload(decisions: dict[str, Any]) -> dict[str, Any]:
    return {tool_id: asdict(decision) for tool_id, decision in decisions.items()}


def _classification_input_types(classification: dict[str, Any]) -> list[str]:
    return list(classification.get("input_types") or [])


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
        input_types = _classification_input_types(classification)
        selected = selected_tools_for_scenario(scenario, input_types)
        selected.update(PROJECT_LEVEL_TOOLS)
        decisions = route_all_tools(selected, input_types, 0, [])
        payload["project"] = {
            "classification": classification,
            "delegated_material_tools": project_delegated_material_tools(),
            "delegation_note": "Project audit first parses the material manifest, then delegates table, text, image, and code tools per file data type; routing_decisions here only represent project-level tools.",
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
        input_types = _classification_input_types(classification)
        selected = selected_tools_for_scenario(scenario, input_types)
        selected.update(PROJECT_LEVEL_TOOLS)
        decisions = route_all_tools(selected, input_types, 0, [])
        payload["project"] = {
            "classification": classification,
            "delegated_material_tools": project_delegated_material_tools(),
            "delegation_note": "Project audit first parses the material manifest, then delegates table, text, image, and code tools per file data type; routing_decisions here only represent project-level tools.",
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
        input_types = _classification_input_types(classification)
        selected = selected_tools_for_scenario(scenario, input_types)
        decisions = route_all_tools(selected, input_types, 1, [])
        payload["code"] = {
            "classification": classification,
            "routing_decisions": routing_decisions_payload(decisions),
        }
        return payload

    if source.suffix.lower() in {".txt", ".md", ".bib", ".ris"}:
        text = read_text_source(source)
        classification = classify_text(text)
        input_types = _classification_input_types(classification)
        selected = selected_tools_for_scenario(scenario, input_types)
        decisions = route_all_tools(selected, input_types, 0, [])
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
            input_types = _classification_input_types(classification)
            if "paper_document" not in input_types:
                input_types.append("paper_document")
                classification["input_types"] = input_types
            selected = selected_tools_for_scenario(scenario, input_types)
            decisions = route_all_tools(selected, input_types, 0, [])
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
        input_types = _classification_input_types(classification)
        selected = selected_tools_for_scenario(scenario, input_types)
        decisions = route_all_tools(selected, input_types, int(df.shape[0]), list(map(str, df.columns)))
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
