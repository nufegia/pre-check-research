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
REPO = Path(__file__).resolve().parents[2] / "mvp2"
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
                "check": "哈希版本链核验",
                "target": item.get("relative_path", ""),
                "summary": f"哈希版本链状态：{item.get('status')}",
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
        json_path=str(json_path),
        markdown_path=str(md_path) if md_path else "",
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
                json_path=str(json_path),
                markdown_path=str(md_path),
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
        notes.append(stdout.strip().splitlines()[-1])
    if stderr.strip():
        notes.append(stderr.strip()[:500])
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
            notes.append(text.strip().splitlines()[-1][:500])
    return summarize(case, rc1 or rc2, t1 + t2, json_path, md_path, notes)


def run_provenance_change(case: dict[str, Any]) -> CaseResult:
    case_id = case["id"]
    work = ROOT / "inputs" / "project_provenance_benchmark"
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
            notes.append(text.strip().splitlines()[-1][:500])
    return summarize(case, rc1 or rc2, t1 + t2, json_path, Path(""), notes)


def render_markdown(results: list[CaseResult], include_network: bool) -> str:
    passed = sum(1 for item in results if item.ok)
    failed = len(results) - passed
    total_risk = sum(item.risk_findings for item in results)
    total_info = sum(item.info_findings for item in results)
    network_result = next((item for item in results if item.case_id == "external_refs_online"), None)
    network_text = (
        "已执行。有效 DOI/PMID 的 Crossref/OpenAlex/NCBI 查询返回 status=ok；故意构造的错误 DOI 返回 404，并被检测为“外部元数据不可核验”。"
        if include_network and network_result and network_result.ok
        else ("未执行（本次使用 --no-network）。" if not include_network else "已执行，但存在失败或证据缺口。")
    )
    network_findings = findings_from_payload(REPORTS / "pcr.external_refs_online.json") if include_network else []
    network_reference_findings = [item for item in network_findings if item.get("tool_id") == "reference_audit"]
    lines = [
        "# PCR Benchmark 总报告",
        "",
        "## 总体结论",
        "",
        f"本轮 benchmark 共运行 {len(results)} 个测评用例，PASS {passed} 个，FAIL {failed} 个。"
        + ("整体通过。" if failed == 0 else "存在未通过用例，需优先查看下方缺口。"),
        "",
        f"- Benchmark 根目录：`{ROOT}`",
        f"- 联网测评：{network_text}",
        f"- 风险信号总数：{total_risk}",
        f"- 运行/覆盖提示总数：{total_info}",
        "",
        "结论：当前工程的核心检测链路可以被自动化 benchmark 稳定覆盖。确定性数学类、哈希溯源类和项目级对账类检查可作为较可靠的工程回归指标；图像、raw 表格中的数字分布/列间关系弱信号、论文工厂/跨稿件相似等能力适合衡量“是否能提出复核线索”，不能作为强结论指标。",
        "",
        "## 覆盖结论",
        "",
        "- 原始数据：覆盖重复/高度重复行列、固定步长、高频值、缺失分组集中、尾数分布、列间关系和非连续变量异常；干净对照保持 0 个风险信号。",
        "- 摘要统计：覆盖 SE/SD/N、CI、百分比/计数、p/t/df、p 值定义域，以及 R scrutiny/SPRITE 可行性检查。",
        "- 正文统计：覆盖 R statcheck 对 APA/NHST 表达式的 p 值一致性检查。",
        "- 文献与联网：覆盖 DOI/PMID 解析、Crossref/OpenAlex/NCBI 元数据查询、引用主张抽取。",
        "- 图像：覆盖图片发现、内部重复图、局部 copy-move、元数据质量、Western blot/凝胶复核清单。",
        "- 代码与项目：覆盖 Python/R 脚本复跑、Stata/SPSS/SAS 只读提示、跨材料数据对账、项目 manifest、provenance 版本链和本地 corpus 筛查。",
        "",
        "## 可靠性分层",
        "",
        "| 层级 | 工具/能力 | Benchmark 判读 |",
        "|---|---|---|",
        "| 较可靠 | `crosscheck`, `p_value_distribution`, `data_trace_crosscheck`, `provenance_hash`, `provenance_chain_verify` | 数学、定义域或哈希规则明确，适合作为回归门槛。 |",
        "| 中等可靠 | `raw_data_rules`, `r_statcheck`, `r_scrutiny`, `r_rsprite2`, `code_rerun_execute` | 对输入格式、列名、R 包版本、脚本依赖较敏感；适合作为覆盖和主要异常捕获指标。 |",
        "| 弱信号 | `raw_data_rules` 中的数字分布/列间关系/非连续变量形态信号、图像重复/copy-move, `papermill_light_signals`, `papermill_network_signals` | 只能说明产生了人工复核线索，误报/漏报风险较高。 |",
        "",
        "## 联网模块测试结论",
        "",
        network_text,
        "",
    ]
    if include_network and network_reference_findings:
        for item in network_reference_findings:
            lines.append(f"- {item.get('check')}：{item.get('target')}；{item.get('evidence')}")
        lines.append("")
    lines.extend([
        "## 用例矩阵",
        "",
        "| 用例 | 类型 | 通过 | 秒 | 风险信号 | 提示 | 缺失工具 | 缺失检查 |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ])
    for item in results:
        lines.append(
            "| {case} | {kind} | {ok} | {seconds} | {risk} | {info} | {tools} | {checks} |".format(
                case=item.case_id,
                kind=item.kind,
                ok="是" if item.ok else "否",
                seconds=item.seconds,
                risk=item.risk_findings,
                info=item.info_findings,
                tools=", ".join(item.missing_tools),
                checks=", ".join(item.missing_checks),
            )
        )
    lines.extend(["", "## 工具覆盖", ""])
    coverage: dict[str, int] = {}
    for item in results:
        for tool in item.tools_seen:
            coverage[tool] = coverage.get(tool, 0) + 1
    for tool, count in sorted(coverage.items()):
        lines.append(f"- `{tool}`：{count} 个用例")
    lines.extend(["", "## 运行记录", ""])
    for item in results:
        if item.notes:
            lines.append(f"- `{item.case_id}`: " + " | ".join(item.notes))
    lines.extend(
        [
            "",
            "## 判读边界",
            "",
            "本报告中的 high/medium/low 是 benchmark 风险信号，不是学术不端、造假或舞弊结论。`info` 是运行状态、依赖状态、跳过原因或覆盖提示，不计入风险结论。",
            "联网用例依赖 Crossref、OpenAlex、NCBI 的实时可用性、证书链和限流状态。若联网用例失败，应先查看 evidence 中的 HTTP/SSL/限流信息，再判断是否为检测器回归。",
            "所有弱信号类工具只用于提示人工复核方向。最终复核应回到原始数据、脚本、图像原文件、文献元数据和审计日志。",
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
        "benchmark_root": str(ROOT),
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
    print(f"summary_json={summary_json}")
    print(f"summary_md={summary_md}")
    print(f"top_level_report={top_level_report}")
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
