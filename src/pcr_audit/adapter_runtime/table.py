from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from pcr_audit.adapter_runtime.base import AuditRunContext
from pcr_audit.detectors.raw import analyze_raw_data_rules
from pcr_audit.io import load_tables, read_json
from pcr_audit.models import TableResult
from pcr_audit.reporting import save_json


TABLE_ADAPTER_ORDER = ["raw_data_rules", "digit_distribution", "p_value_distribution", "crosscheck"]


def ready_tables_for_tool(source: Path, route_payload: dict[str, Any], tool_id: str):
    route_tables = route_payload.get("tables", [])
    for table_route, (name, df) in zip(route_tables, load_tables(source), strict=False):
        decision = table_route.get("routing_decisions", {}).get(tool_id, {})
        if decision.get("status") == "ready":
            yield name, df


def run_raw_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    results = [analyze_raw_data_rules(name, df) for name, df in ready_tables_for_tool(source, route_payload, "raw_data_rules")]
    save_json(json_path, source, results)
    return read_json(json_path)


def run_crosscheck_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    from pcr_audit.crosscheck import crosscheck_table

    results = [crosscheck_table(name, df) for name, df in ready_tables_for_tool(source, route_payload, "crosscheck")]
    save_json(json_path, source, results)
    return read_json(json_path)


def run_digit_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    from pcr_audit.detectors.raw_legacy import analyze_digit_distribution_rules
    from pcr_audit.models import finding_from_mapping

    results = []
    for name, df in ready_tables_for_tool(source, route_payload, "digit_distribution"):
        legacy = analyze_digit_distribution_rules(name, df)
        findings = [finding_from_mapping(name, asdict(item)) for item in legacy.findings]
        results.append(TableResult(name, legacy.rows, legacy.columns, findings))
    save_json(json_path, source, results)
    return read_json(json_path)


def run_p_value_payload(source: Path, json_path: Path, route_payload: dict[str, Any]) -> dict[str, Any]:
    from pcr_audit.detectors.p_values import analyze_p_value_collection

    results = [analyze_p_value_collection(name, df) for name, df in ready_tables_for_tool(source, route_payload, "p_value_distribution")]
    save_json(json_path, source, results)
    return read_json(json_path)


def raw_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(run_raw_payload(context.source, context.workdir / "raw-audit.json", context.route_payload))


def digit_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(run_digit_payload(context.source, context.workdir / "digit-distribution.json", context.route_payload))


def p_value_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(run_p_value_payload(context.source, context.workdir / "p-value-distribution.json", context.route_payload))


def crosscheck_adapter(context: AuditRunContext, _tool_id: str) -> None:
    context.payloads.append(run_crosscheck_payload(context.source, context.workdir / "crosscheck.json", context.route_payload))
