from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from pcr_audit.io import load_tables, read_text_source
from pcr_audit.tool_system import classify_table, classify_text, route_all_tools, source_kind


def selected_tools_for_scenario(scenario: str, input_types: list[str]) -> set[str]:
    if scenario == "auto":
        selected: set[str] = set()
        if "raw_observation_table" in input_types or "figure_source_data" in input_types:
            selected.add("raw_data_rules")
        if "summary_statistics_table" in input_types or "continuous_measure_summary" in input_types:
            selected.update({"r_scrutiny", "crosscheck"})
        if "likert_or_integer_scale_summary" in input_types:
            selected.update({"r_scrutiny", "r_rsprite2", "crosscheck"})
        if "apa_statistical_text" in input_types:
            selected.add("r_statcheck")
        return selected
    if scenario == "raw":
        return {"raw_data_rules"}
    if scenario == "summary":
        return {"r_scrutiny", "crosscheck"}
    if scenario == "r-advanced":
        return {"r_rsprite2"}
    if scenario == "text":
        return {"r_statcheck"}
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

    if source.suffix.lower() in {".txt", ".md"}:
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
    if route_payload.get("text"):
        items.append(route_payload["text"])
    for item in items:
        for tool_id, decision in (item.get("routing_decisions") or {}).items():
            if decision.get("selected_by_user"):
                selected.setdefault(tool_id, []).append(decision)
    return selected


def ready_tool_ids(route_payload: dict[str, Any]) -> set[str]:
    selected = selected_route_decisions(route_payload)
    return {tool_id for tool_id, decisions in selected.items() if any(d.get("status") == "ready" for d in decisions)}
