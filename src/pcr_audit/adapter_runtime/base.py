from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from pcr_audit.models import TableResult, info_finding


@dataclass
class AuditRunContext:
    source: Path
    workdir: Path
    route_payload: dict[str, Any]
    payloads: list[dict[str, Any]]
    product_results: list[TableResult] = field(default_factory=list)
    extraction_manifest: dict[str, Any] | None = None


AuditAdapter = Callable[[AuditRunContext, str], None]


_ADAPTERS: dict[str, AuditAdapter] = {}


def register_adapter(tool_id: str, adapter: AuditAdapter) -> None:
    _ADAPTERS[tool_id] = adapter


def adapter_for(tool_id: str) -> AuditAdapter | None:
    return _ADAPTERS.get(tool_id)


def registered_tool_ids() -> set[str]:
    return set(_ADAPTERS)


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
