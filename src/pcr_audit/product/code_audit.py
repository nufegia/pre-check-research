from __future__ import annotations

import re
from pathlib import Path

from pcr_audit.models import Finding, TableResult
from pcr_audit.product.common import CODE_SUFFIXES, finding, iter_audit_files

def analyze_code_files(source: Path) -> TableResult:
    paths = [source] if source.is_file() else [path for path in iter_audit_files(source) if path.suffix in CODE_SUFFIXES]
    findings: list[Finding] = []
    risky_patterns = {
        r"\bsetwd\s*\(": "Script contains setwd; rerun environment may depend on local paths.",
        r"read\.(csv|xlsx|table)\s*\(": "Script reads external data; verify input files are included in the audit package.",
        r"dropna\s*\(|na\.omit\s*\(": "Script contains missing value removal; verify removal rules and sample size changes.",
        r"p\s*<\s*0\.05": "Script or comment shows significance threshold filtering clues; verify multiple comparison transparency.",
    }
    for path in paths[:100]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [message for pattern, message in risky_patterns.items() if re.search(pattern, text, re.I)]
        if hits:
            findings.append(
                finding(
                    str(source), "low", "Analysis code rerun readiness check", path.name,
                    "Script contains inputs, paths, or exclusion rules that need confirmation before rerun.",
                    "；".join(hits),
                    "Before rerunning in isolated environment, confirm dependencies, input files, random seeds, exclusion rules, and output statistic mappings.",
                    tool_id="code_rerun_audit", tool_name="Analysis code rerun audit", input_type="analysis_code",
                )
            )
    if not findings:
        findings.append(
            finding(
                str(source), "info", "Analysis code rerun readiness check", "analysis_code",
                "No scannable analysis code found, or no built-in rerun risk rules matched.",
                f"Code files={len(paths)}",
                "To rerun key statistics, provide scripts, locked dependencies, and original input data.",
                tool_id="code_rerun_audit", tool_name="Analysis code rerun audit", input_type="analysis_code",
                dependency_status="insufficient_material" if not paths else "ready",
            )
        )
    return TableResult("code_rerun_audit", len(paths), 0, findings)
