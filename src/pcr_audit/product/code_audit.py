from __future__ import annotations

import re
from pathlib import Path

from pcr_audit.models import Finding, TableResult
from pcr_audit.product.common import CODE_SUFFIXES, finding, iter_audit_files

def analyze_code_files(source: Path) -> TableResult:
    paths = [source] if source.is_file() else [path for path in iter_audit_files(source) if path.suffix in CODE_SUFFIXES]
    findings: list[Finding] = []
    risky_patterns = {
        r"\bsetwd\s*\(": "脚本包含 setwd，复跑环境可能依赖本机路径。",
        r"read\.(csv|xlsx|table)\s*\(": "脚本读取外部数据，需核对输入文件是否纳入审计包。",
        r"dropna\s*\(|na\.omit\s*\(": "脚本存在缺失值剔除，需核对剔除规则和样本量变化。",
        r"p\s*<\s*0\.05": "脚本或注释出现显著性阈值筛选线索，需核对多重比较透明度。",
    }
    for path in paths[:100]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [message for pattern, message in risky_patterns.items() if re.search(pattern, text, re.I)]
        if hits:
            findings.append(
                finding(
                    str(source), "low", "分析代码复跑准备检查", path.name,
                    "脚本包含需要复跑前确认的输入、路径或剔除规则。",
                    "；".join(hits),
                    "在隔离环境中复跑前，确认依赖、输入文件、随机种子、剔除规则和输出统计量映射。",
                    tool_id="code_rerun_audit", tool_name="分析代码复跑审计", input_type="analysis_code",
                )
            )
    if not findings:
        findings.append(
            finding(
                str(source), "info", "分析代码复跑准备检查", "analysis_code",
                "未发现可扫描的分析代码，或未命中内置复跑风险规则。",
                f"代码文件数={len(paths)}",
                "如需复跑关键统计量，请提供脚本、锁定依赖和原始输入数据。",
                tool_id="code_rerun_audit", tool_name="分析代码复跑审计", input_type="analysis_code",
                dependency_status="insufficient_material" if not paths else "ready",
            )
        )
    return TableResult("code_rerun_audit", len(paths), 0, findings)
