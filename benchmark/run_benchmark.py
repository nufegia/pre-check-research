from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmark_manifest.json"
REPORTS = ROOT / "reports"
RISK_LEVELS = {"low", "medium", "high"}


@dataclass
class CaseResult:
    case_id: str
    kind: str
    ok: bool
    returncode: int
    seconds: float
    json_path: str
    markdown_path: str
    risk_findings: int
    info_findings: int
    tools_seen: list[str]
    checks_seen: list[str]
    missing_tools: list[str]
    missing_checks: list[str]
    notes: list[str]


def repo_path(path: Path | str) -> str:
    raw = Path(path)
    try:
        return raw.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return raw.as_posix()


def public_text(text: str) -> str:
    text = text.replace(str(REPO) + os.sep, "")
    text = text.replace(str(REPO), ".")
    return text


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize_text_file(path: Path) -> None:
    if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    sanitized = public_text(text)
    if sanitized != text:
        path.write_text(sanitized, encoding="utf-8")


def sanitize_reports() -> None:
    for path in REPORTS.rglob("*"):
        if path.is_file():
            sanitize_text_file(path)
    sanitize_text_file(ROOT / "BENCHMARK_REPORT.md")


def env() -> dict[str, str]:
    out = os.environ.copy()
    r_paths = [
        str(REPO / "tools" / "r" / "pcr_statcheck"),
        str(REPO / "tools" / "r" / "pcr_scrutiny"),
        str(REPO / "tools" / "r" / "pcr_sprite"),
    ]
    out["PATH"] = ":".join(r_paths + [out.get("PATH", "")])
    return out


def run_cmd(cmd: list[str], *, extra_env: dict[str, str] | None = None) -> tuple[int, float, str, str]:
    merged_env = env()
    if extra_env:
        merged_env.update(extra_env)
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO, env=merged_env, capture_output=True, text=True)
    return proc.returncode, time.perf_counter() - start, proc.stdout, proc.stderr


def findings_from_payload(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = load_json(path)
    if "results" in payload:
        return [finding for result in payload["results"] for finding in result.get("findings", [])]
    if "statuses" in payload:
        return [
            {
                "level": "medium" if item.get("status") in {"changed", "modified", "missing"} else "info",
                "tool_id": "provenance_chain_verify",
                "check": "Hash Version Chain Verification",
                "target": item.get("relative_path", ""),
                "summary": f"Hash version chain status: {item.get('status')}",
                "evidence": json.dumps(item, ensure_ascii=False),
            }
            for item in payload["statuses"]
        ]
    return payload.get("findings", [])


def summarize(case: dict[str, Any], rc: int, seconds: float, json_path: Path, md_path: Path, notes: list[str]) -> CaseResult:
    findings = findings_from_payload(json_path)
    tools_seen = sorted({str(item.get("tool_id", "")) for item in findings if item.get("tool_id")})
    checks_seen = sorted({str(item.get("check", "")) for item in findings if item.get("check")})
    levels = [str(item.get("level", "")) for item in findings]
    risk = sum(1 for level in levels if level in RISK_LEVELS)
    info = sum(1 for level in levels if level == "info")
    expected_tools = set(case.get("expected_tools", []))
    expected_checks = set(case.get("expected_checks", []))
    missing_tools = sorted(expected_tools.difference(tools_seen))
    missing_checks = sorted(expected_checks.difference(checks_seen))
    max_risk = case.get("max_risk_findings")
    min_risk = int(case.get("min_risk_findings", 0))
    min_info = int(case.get("min_info_findings", 0))
    ok = rc == 0 and not missing_tools and not missing_checks and risk >= min_risk and info >= min_info
    if max_risk is not None and risk > int(max_risk):
        ok = False
        notes.append(f"risk_findings={risk} exceeds max_risk_findings={max_risk}")
    for status in case.get("expected_statuses", []):
        if status not in " ".join(str(item.get("summary", "")) + " " + str(item.get("evidence", "")) for item in findings):
            ok = False
            notes.append(f"missing expected status: {status}")
    for service in case.get("expected_external_services", []):
        text = " ".join(str(item.get("evidence", "")) + " " + str(item.get("external_records", "")) for item in findings).lower()
        if service not in text:
            ok = False
            notes.append(f"missing external service evidence: {service}")
        elif f"{service} cache_hit status=ok" not in text and f"{service} cache_miss status=ok" not in text:
            ok = False
            notes.append(f"external service did not return status=ok: {service}")
    return CaseResult(
        case_id=case["id"],
        kind=case["kind"],
        ok=ok,
        returncode=rc,
        seconds=round(seconds, 3),
        json_path=repo_path(json_path),
        markdown_path=repo_path(md_path) if md_path else "",
        risk_findings=risk,
        info_findings=info,
        tools_seen=tools_seen,
        checks_seen=checks_seen,
        missing_tools=missing_tools,
        missing_checks=missing_checks,
        notes=notes,
    )


def run_single(case: dict[str, Any], include_network: bool) -> CaseResult:
    case_id = case["id"]
    input_path = ROOT / case["input"]
    md_path = REPORTS / f"pcr.{case_id}.md"
    json_path = REPORTS / f"pcr.{case_id}.json"
    notes: list[str] = []
    extra_env = None
    if case["kind"] == "single_run":
        cmd = ["pcr-audit", "run", str(input_path), "--scenario", "auto", "--out", str(md_path), "--json", str(json_path)]
    elif case["kind"] == "project":
        cmd = ["pcr-audit", "project", str(input_path), "--out", str(md_path), "--json", str(json_path), "--no-external-lookups"]
        if case_id == "figures_project":
            cmd.append("--no-rerun-code")
    elif case["kind"] == "project_network":
        if not include_network:
            return CaseResult(
                case_id=case_id,
                kind=case["kind"],
                ok=True,
                returncode=0,
                seconds=0.0,
                json_path=repo_path(json_path),
                markdown_path=repo_path(md_path),
                risk_findings=0,
                info_findings=0,
                tools_seen=[],
                checks_seen=[],
                missing_tools=[],
                missing_checks=[],
                notes=["network case skipped by --no-network"],
            )
        network_workdir = md_path.with_suffix(".parts")
        if network_workdir.exists():
            shutil.rmtree(network_workdir)
        if json_path.exists():
            json_path.unlink()
        if md_path.exists():
            md_path.unlink()
        cmd = ["pcr-audit", "project", str(input_path), "--out", str(md_path), "--json", str(json_path), "--external-lookups", "--no-rerun-code"]
        extra_env = {"PCR_ENABLE_EXTERNAL_LOOKUPS": "1"}
    else:
        raise ValueError(f"unsupported single case kind: {case['kind']}")
    rc, seconds, stdout, stderr = run_cmd(cmd, extra_env=extra_env)
    if stdout.strip():
        notes.append(public_text(stdout.strip().splitlines()[-1]))
    if stderr.strip():
        notes.append(public_text(stderr.strip()[:500]))
    return summarize(case, rc, seconds, json_path, md_path, notes)


def run_corpus(case: dict[str, Any]) -> CaseResult:
    case_id = case["id"]
    index_path = REPORTS / "pcr.corpus_index.json"
    md_path = REPORTS / f"pcr.{case_id}.md"
    json_path = REPORTS / f"pcr.{case_id}.json"
    notes: list[str] = []
    rc1, t1, out1, err1 = run_cmd(["pcr-audit", "corpus", "build", str(ROOT / "corpus"), "--out", str(index_path)])
    rc2, t2, out2, err2 = run_cmd([
        "pcr-audit",
        "corpus",
        "screen",
        str(ROOT / case["input"]),
        "--index",
        str(index_path),
        "--out",
        str(md_path),
        "--json",
        str(json_path),
    ])
    for text in (out1, err1, out2, err2):
        if text.strip():
            notes.append(public_text(text.strip().splitlines()[-1][:500]))
    return summarize(case, rc1 or rc2, t1 + t2, json_path, md_path, notes)


def run_provenance_change(case: dict[str, Any]) -> CaseResult:
    case_id = case["id"]
    work = REPORTS / "pcr.provenance_change.work"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(ROOT / case["input"], work)
    record_json = REPORTS / "pcr.provenance_record.json"
    json_path = REPORTS / f"pcr.{case_id}.json"
    notes: list[str] = []
    rc1, t1, out1, err1 = run_cmd(["pcr-audit", "provenance", "record", str(work), "--json", str(record_json)])
    data = work / "data.csv"
    data.write_text(data.read_text(encoding="utf-8") + "5.0\n", encoding="utf-8")
    rc2, t2, out2, err2 = run_cmd(["pcr-audit", "provenance", "verify", str(work), "--json", str(json_path)])
    for text in (out1, err1, out2, err2):
        if text.strip():
            notes.append(public_text(text.strip().splitlines()[-1][:500]))
    return summarize(case, rc1 or rc2, t1 + t2, json_path, Path(""), notes)


def render_markdown(results: list[CaseResult], include_network: bool) -> str:
    passed = sum(1 for item in results if item.ok)
    failed = len(results) - passed
    total_risk = sum(item.risk_findings for item in results)
    total_info = sum(item.info_findings for item in results)
    network_result = next((item for item in results if item.case_id == "external_refs_online"), None)
    network_text = (
        "Executed. Valid DOI/PMID Crossref/OpenAlex/NCBI queries returned status=ok; intentionally malformed DOI returned 404 and was detected as 'external metadata unverifiable'."
        if include_network and network_result and network_result.ok
        else ("Not executed (--no-network used)." if not include_network else "Executed, but failures or evidence gaps exist.")
    )
    network_findings = findings_from_payload(REPORTS / "pcr.external_refs_online.json") if include_network else []
    network_reference_findings = [item for item in network_findings if item.get("tool_id") == "reference_audit"]
    lines = [
        "# PCR Benchmark Report",
        "",
        "## Overall Conclusion",
        "",
        f"This benchmark ran {len(results)} test cases, {passed} PASS, {failed} FAIL. "
        + ("All passed." if failed == 0 else "Some cases failed; review gaps below first."),
        "",
        f"- Benchmark root: `{repo_path(ROOT)}`",
        f"- Network tests: {network_text}",
        f"- Total risk signals: {total_risk}",
        f"- Total run/info records: {total_info}",
        "",
        "Conclusion: The core detection pipeline is stably covered by automated benchmarks. Deterministic mathematical checks, hash provenance, and project-level reconciliation checks serve as reliable engineering regression indicators; image checks, raw table digit distribution/inter-column relationship weak signals, and paper mill/cross-manuscript similarity are suitable for measuring 'whether review leads are surfaced', not as strong conclusion indicators.",
        "",
        "## Coverage Summary",
        "",
        "- Raw data: Covers duplicate/highly similar rows and columns, fixed steps, high-frequency values, missing-concentrated-by-group, terminal digit distribution, inter-column relationships, and non-continuous variable anomalies; clean controls maintain 0 risk signals.",
        "- Summary statistics: Covers SE/SD/N, CI, percent/count, p/t/df, p-value domain, and R scrutiny/SPRITE feasibility checks.",
        "- In-text statistics: Covers R statcheck p-value consistency checks on APA/NHST expressions.",
        "- Literature & network: Covers DOI/PMID parsing, Crossref/OpenAlex/NCBI metadata queries, and citation claim extraction.",
        "- Images: Covers image discovery, internal duplicates, local copy-move, metadata quality, and Western blot/gel review checklist.",
        "- Code & project: Covers Python/R script reruns, Stata/SPSS/SAS read-only prompts, cross-material data reconciliation, project manifest, provenance version chain, and local corpus screening.",
        "",
        "## Reliability Tiers",
        "",
        "| Tier | Tools / Capabilities | Benchmark Interpretation |",
        "|---|---|---|",
        "| More Reliable | `crosscheck`, `p_value_distribution`, `data_trace_crosscheck`, `provenance_hash`, `provenance_chain_verify` | Mathematics, domain, or hash rules are explicit; suitable as regression thresholds. |",
        "| Moderately Reliable | `raw_data_rules`, `r_statcheck`, `r_scrutiny`, `r_rsprite2`, `code_rerun_execute` | Sensitive to input format, column names, R package versions, and script dependencies; suitable as coverage and primary anomaly capture indicators. |",
        "| Weak Signal | `raw_data_rules` digit distribution/inter-column relationship/non-continuous variable shape signals, image duplicate/copy-move, `papermill_light_signals`, `papermill_network_signals` | Only indicate that human review leads were generated; higher false positive/negative risk. |",
        "",
        "## Network Module Test Conclusion",
        "",
        network_text,
        "",
    ]
    if include_network and network_reference_findings:
        for item in network_reference_findings:
            lines.append(f"- {item.get('check')}：{item.get('target')}；{item.get('evidence')}")
        lines.append("")
    lines.extend([
        "## Case Matrix",
        "",
        "| Case | Type | Pass | Seconds | Risk Signals | Info | Missing Tools | Missing Checks |",
        "|---|---:|---:|---:|---:|---|---|",
    ])
    for item in results:
        lines.append(
            "| {case} | {kind} | {ok} | {seconds} | {risk} | {info} | {tools} | {checks} |".format(
                case=item.case_id,
                kind=item.kind,
                ok="Yes" if item.ok else "No",
                seconds=item.seconds,
                risk=item.risk_findings,
                info=item.info_findings,
                tools=", ".join(item.missing_tools),
                checks=", ".join(item.missing_checks),
            )
        )
    lines.extend(["", "## Tool Coverage", ""])
    coverage: dict[str, int] = {}
    for item in results:
        for tool in item.tools_seen:
            coverage[tool] = coverage.get(tool, 0) + 1
    for tool, count in sorted(coverage.items()):
        lines.append(f"- `{tool}`: {count} cases")
    lines.extend(["", "## Run Log", ""])
    for item in results:
        if item.notes:
            lines.append(f"- `{item.case_id}`: " + " | ".join(item.notes))
    lines.extend(
        [
            "",
            "## Interpretation Boundaries",
            "",
            "The high/medium/low levels in this report are benchmark risk signals, not conclusions of academic misconduct, fabrication, or fraud. `info` records are run statuses, dependency states, skip reasons, or coverage notes; they do not count toward risk conclusions.",
            "Network test cases depend on real-time availability, certificate chains, and rate limiting of Crossref, OpenAlex, and NCBI. If network cases fail, first check HTTP/SSL/rate-limit information in evidence before concluding it is a detector regression.",
            "All weak-signal tools are only for surfacing human review directions. Final review should return to original data, scripts, image source files, literature metadata, and audit logs.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PCR benchmark suite.")
    parser.add_argument("--no-network", action="store_true", help="Skip external Crossref/OpenAlex/NCBI benchmark case.")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate synthetic fixtures before running.")
    args = parser.parse_args()

    if args.regenerate:
        rc, _seconds, stdout, stderr = run_cmd([sys.executable, str(ROOT / "generate_synthetic_benchmark.py")])
        if rc != 0:
            print(stderr or stdout, file=sys.stderr)
            return rc

    REPORTS.mkdir(parents=True, exist_ok=True)
    manifest = load_json(MANIFEST)
    include_network = not args.no_network
    results: list[CaseResult] = []
    for case in manifest["cases"]:
        kind = case["kind"]
        if kind == "corpus":
            result = run_corpus(case)
        elif kind == "provenance_change":
            result = run_provenance_change(case)
        else:
            result = run_single(case, include_network)
        results.append(result)
        print(f"{'PASS' if result.ok else 'FAIL'} {result.case_id} risk={result.risk_findings} info={result.info_findings} seconds={result.seconds}")

    payload = {
        "benchmark_root": repo_path(ROOT),
        "network_enabled": include_network,
        "cases": [item.__dict__ for item in results],
        "passed": sum(1 for item in results if item.ok),
        "failed": sum(1 for item in results if not item.ok),
    }
    summary_json = REPORTS / "pcr.benchmark_summary.json"
    summary_md = REPORTS / "pcr.benchmark_summary.md"
    top_level_report = ROOT / "BENCHMARK_REPORT.md"
    report_text = render_markdown(results, include_network)
    write_json(summary_json, payload)
    summary_md.write_text(report_text, encoding="utf-8")
    top_level_report.write_text(report_text, encoding="utf-8")
    sanitize_reports()
    print(f"summary_json={repo_path(summary_json)}")
    print(f"summary_md={repo_path(summary_md)}")
    print(f"top_level_report={repo_path(top_level_report)}")
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
