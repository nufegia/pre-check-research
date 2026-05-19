from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pcr_audit.models import TableResult


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

