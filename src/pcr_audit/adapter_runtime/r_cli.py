from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from pcr_audit.adapter_runtime.base import AuditRunContext, info_payload
from pcr_audit.io import extract_file, read_json, write_extracted_text


ROOT = Path(__file__).resolve().parents[3]
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
R_ADAPTER_ORDER = ["r_statcheck", "r_scrutiny", "r_rsprite2"]


def tool_available(path: Path) -> bool:
    return path.exists() and path.is_file()


def find_r_tool(tool_key: str) -> str | None:
    command = R_TOOL_COMMANDS[tool_key]
    path = shutil.which(command)
    if path:
        return path
    repo_path = R_TOOL_PATHS[tool_key]
    if tool_available(repo_path):
        return str(repo_path)
    return None


def run_r_tool_payload(source: Path, tool_id: str, input_path: Path, workdir: Path, payloads: list[dict[str, Any]]) -> None:
    tool_key = R_TOOL_BY_ID[tool_id]
    tool = find_r_tool(tool_key)
    out_json = workdir / f"{tool_key}.json"
    if not tool:
        payloads.append(info_payload(source, tool_id, "Corresponding R CLI not found; skipped.", R_TOOL_COMMANDS[tool_key]))
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
        payloads.append(info_payload(source, tool_id, "R CLI run failed; skipped.", proc.stderr.strip()))


def csv_inputs_for_r_tool(
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


def r_adapter(context: AuditRunContext, tool_id: str) -> None:
    if tool_id == "r_statcheck":
        run_r_tool_payload(context.source, tool_id, context.source, context.workdir, context.payloads)
        return
    try:
        r_inputs, context.extraction_manifest = csv_inputs_for_r_tool(
            context.source,
            context.workdir,
            context.route_payload,
            tool_id,
            context.extraction_manifest,
        )
    except Exception as exc:
        context.payloads.append(info_payload(context.source, tool_id, "Table extraction failed; R CLI skipped.", str(exc), "extract_failed"))
        return
    for idx, r_input in enumerate(r_inputs, start=1):
        tool_workdir = context.workdir / f"{tool_id}_{idx}"
        tool_workdir.mkdir(parents=True, exist_ok=True)
        run_r_tool_payload(context.source, tool_id, r_input, tool_workdir, context.payloads)
