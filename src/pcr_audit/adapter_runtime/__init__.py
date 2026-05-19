from __future__ import annotations

from pcr_audit.adapter_runtime.base import (
    AuditAdapter,
    AuditRunContext,
    adapter_for,
    info_payload,
    register_adapter,
    registered_tool_ids,
)
from pcr_audit.adapter_runtime.product import PRODUCT_ADAPTER_ORDER, product_adapter
from pcr_audit.adapter_runtime.r_cli import R_ADAPTER_ORDER, r_adapter
from pcr_audit.adapter_runtime.table import (
    TABLE_ADAPTER_ORDER,
    crosscheck_adapter,
    digit_adapter,
    p_value_adapter,
    raw_adapter,
)


PYTHON_ADAPTER_ORDER = [*TABLE_ADAPTER_ORDER, *PRODUCT_ADAPTER_ORDER]
ADAPTER_ORDER = [*PYTHON_ADAPTER_ORDER, *R_ADAPTER_ORDER]


def register_builtin_adapters() -> None:
    register_adapter("raw_data_rules", raw_adapter)
    register_adapter("digit_distribution", digit_adapter)
    register_adapter("p_value_distribution", p_value_adapter)
    register_adapter("crosscheck", crosscheck_adapter)
    for tool_id in PRODUCT_ADAPTER_ORDER:
        register_adapter(tool_id, product_adapter)
    for tool_id in R_ADAPTER_ORDER:
        register_adapter(tool_id, r_adapter)


register_builtin_adapters()


__all__ = [
    "ADAPTER_ORDER",
    "AuditAdapter",
    "AuditRunContext",
    "PYTHON_ADAPTER_ORDER",
    "R_ADAPTER_ORDER",
    "adapter_for",
    "info_payload",
    "register_adapter",
    "register_builtin_adapters",
    "registered_tool_ids",
]
