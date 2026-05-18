from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from pcr_audit import __version__
from pcr_audit.data_trace_mvp import (
    Finding,
    TableResult,
    analyze_table,
    enrich_finding_explanation,
    load_tables,
    render_markdown,
    save_json,
)


ROOT = Path(__file__).resolve().parents[2]
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


def _source(path: str) -> Path:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"输入文件不存在：{source}")
    return source


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_table_name(name: str, index: int) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name.strip())
    return cleaned or f"table_{index}"


def extract_file(source: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = load_tables(source)
    outputs: list[dict[str, Any]] = []
    for idx, (name, df) in enumerate(tables, start=1):
        filename = f"{idx:02d}_{_safe_table_name(name, idx)}.csv"
        out_path = out_dir / filename
        df.to_csv(out_path, index=False)
        outputs.append(
            {
                "name": name,
                "kind": "table",
                "path": str(out_path),
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
            }
        )
    notes: list[str] = []
    if source.suffix.lower() in {".pdf", ".docx"}:
        notes.append("输入来自文档抽取，合并单元格、脚注和复杂版式可能需要人工复核。")
    return {
        "source": str(source),
        "tool_id": "pcr_extract",
        "tool_name": "PCR Extract",
        "detector_runtime": "python",
        "dependency_status": "ready",
        "outputs": outputs,
        "notes": notes,
    }


def extract_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract tables from CSV/XLSX/DOCX/PDF into normalized CSV files.")
    parser.add_argument("input")
    parser.add_argument("--out", required=True, help="Output directory for normalized artifacts.")
    parser.add_argument("--json", help="Optional extraction manifest JSON path.")
    args = parser.parse_args(argv)
    try:
        payload = extract_file(_source(args.input), Path(args.out).expanduser().resolve())
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"抽取失败：{exc}", file=sys.stderr)
        return 1
    if args.json:
        _write_json(Path(args.json).expanduser().resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def raw_audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Python raw-data risk checks and write Markdown/JSON reports.")
    parser.add_argument("input", help="CSV/XLSX/XLS/DOCX/PDF input.")
    parser.add_argument("--out", required=True, help="Markdown report output path.")
    parser.add_argument("--json", help="Optional finding JSON output path.")
    args = parser.parse_args(argv)
    try:
        source = _source(args.input)
        tables = load_tables(source)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"读取失败：{exc}", file=sys.stderr)
        return 1
    if not tables:
        print("没有抽取到可检测表格。", file=sys.stderr)
        return 1
    results = [analyze_table(name, df) for name, df in tables]
    notes = []
    if source.suffix.lower() in {".pdf", ".docx"}:
        notes.append("当前输入来自文档抽取，重要结论建议用原始 CSV/XLSX 复测。")
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_markdown(source, results, notes), encoding="utf-8")
    if args.json:
        save_json(Path(args.json).expanduser().resolve(), source, results)
    print(f"报告已生成：{out_path}")
    return 0


def _finding_from_payload(source: str, raw: dict[str, Any]) -> Finding:
    finding = Finding(
        table=str(raw.get("table") or raw.get("source") or source),
        level=str(raw.get("level") or "info"),
        check=str(raw.get("check") or "运行记录"),
        target=str(raw.get("target") or ""),
        summary=str(raw.get("summary") or ""),
        evidence=str(raw.get("evidence") or ""),
        detail=str(raw.get("detail") or ""),
        suggestion=str(raw.get("suggestion") or ""),
        tool_id=str(raw.get("tool_id") or ""),
        tool_name=str(raw.get("tool_name") or ""),
        module=str(raw.get("module") or ""),
        input_type=str(raw.get("input_type") or ""),
        detector_runtime=str(raw.get("detector_runtime") or ""),
        dependency_status=str(raw.get("dependency_status") or "ready"),
        meaning=str(raw.get("meaning") or ""),
        normal_explanations=str(raw.get("normal_explanations") or ""),
        review_steps=str(raw.get("review_steps") or ""),
        confidence=str(raw.get("confidence") or ""),
        false_positive_risk=str(raw.get("false_positive_risk") or ""),
    )
    enrich_finding_explanation(finding)
    return finding


def _results_from_payload(payload: dict[str, Any]) -> list[TableResult]:
    source = str(payload.get("source") or "merged")
    if "results" in payload:
        results: list[TableResult] = []
        for result in payload["results"]:
            findings = [_finding_from_payload(source, f) for f in result.get("findings", [])]
            results.append(
                TableResult(
                    name=str(result.get("name") or source),
                    rows=int(result.get("rows") or 0),
                    columns=int(result.get("columns") or 0),
                    findings=findings,
                )
            )
        return results
    findings = [_finding_from_payload(source, f) for f in payload.get("findings", [])]
    return [TableResult(name=source, rows=0, columns=0, findings=findings)]


def report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report utilities for PCR finding JSON files.")
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge", help="Merge finding JSON files into one Markdown report.")
    merge.add_argument("finding_json", nargs="+")
    merge.add_argument("--out", required=True)
    merge.add_argument("--json", help="Optional merged JSON output path.")
    args = parser.parse_args(argv)
    if args.command != "merge":
        return 2
    all_results: list[TableResult] = []
    sources: list[str] = []
    try:
        for item in args.finding_json:
            payload = _read_json(_source(item))
            sources.append(str(payload.get("source") or item))
            all_results.extend(_results_from_payload(payload))
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"合并失败：{exc}", file=sys.stderr)
        return 1
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pseudo_source = Path(sources[0] if len(sources) == 1 else "merged-findings.json")
    out_path.write_text(render_markdown(pseudo_source, all_results, ["本报告由多个 CLI finding JSON 合并生成。"]), encoding="utf-8")
    if args.json:
        payload = {
            "source": sources,
            "results": [
                {"name": r.name, "rows": r.rows, "columns": r.columns, "findings": [asdict(f) for f in r.findings]}
                for r in all_results
            ],
        }
        _write_json(Path(args.json).expanduser().resolve(), payload)
    print(f"合并报告已生成：{out_path}")
    return 0


def _tool_available(path: Path) -> bool:
    return path.exists() and path.is_file()


def _find_r_tool(tool_key: str) -> str | None:
    command = R_TOOL_COMMANDS[tool_key]
    path = shutil.which(command)
    if path:
        return path
    repo_path = R_TOOL_PATHS[tool_key]
    if _tool_available(repo_path):
        return str(repo_path)
    return None


def _info_payload(source: Path, tool_id: str, summary: str, evidence: str) -> dict[str, Any]:
    return {
        "tool_id": tool_id,
        "tool_name": tool_id,
        "detector_runtime": "cli",
        "dependency_status": "dependency_missing",
        "source": str(source),
        "input_type": "unknown",
        "findings": [
            {
                "level": "info",
                "check": "工具运行记录",
                "target": tool_id,
                "summary": summary,
                "evidence": evidence,
                "detail": "",
                "suggestion": "安装或修复该 CLI 后重试；其他可用工具的结果不受影响。",
                "meaning": summary,
                "normal_explanations": "工具缺失或依赖缺失不是数据风险。",
                "review_steps": "检查 PATH、Rscript 和对应 R 包安装状态。",
                "confidence": "low",
                "false_positive_risk": "low",
                "tool_id": tool_id,
                "detector_runtime": "cli",
                "dependency_status": "dependency_missing",
            }
        ],
    }


def audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optional orchestration layer for installed native CLI tools.")
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="Run a scenario and merge available tool outputs.")
    run.add_argument("input")
    run.add_argument("--scenario", choices=["auto", "raw", "summary", "text", "r-advanced"], default="auto")
    run.add_argument("--out", required=True)
    run.add_argument("--json", help="Optional merged JSON output path.")
    run.add_argument("--workdir", help="Temporary output directory. Defaults to <out>.parts.")
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command != "run":
        parser.print_help()
        return 2
    try:
        source = _source(args.input)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    workdir = Path(args.workdir).expanduser().resolve() if args.workdir else Path(args.out).expanduser().resolve().with_suffix(".parts")
    workdir.mkdir(parents=True, exist_ok=True)
    payloads: list[dict[str, Any]] = []
    if args.scenario in {"auto", "raw"}:
        raw_md = workdir / "raw-audit.md"
        raw_json = workdir / "raw-audit.json"
        code = raw_audit_main([str(source), "--out", str(raw_md), "--json", str(raw_json)])
        if code == 0:
            payloads.append(_read_json(raw_json))
    if args.scenario in {"summary", "r-advanced", "text"}:
        tool_key = "statcheck" if args.scenario == "text" else "sprite" if args.scenario == "r-advanced" else "scrutiny"
        tool = _find_r_tool(tool_key)
        out_json = workdir / f"{tool_key}.json"
        if not tool:
            payloads.append(_info_payload(source, f"pcr_{tool_key}", "对应 R CLI 不存在，已跳过。", R_TOOL_COMMANDS[tool_key]))
        else:
            cmd = [tool, str(source), "--json", str(out_json)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if out_json.exists():
                payloads.append(_read_json(out_json))
            elif proc.returncode != 0:
                payloads.append(_info_payload(source, f"pcr_{tool_key}", "R CLI 运行失败，已跳过。", proc.stderr.strip()))
    if not payloads:
        print("没有生成任何可合并结果。", file=sys.stderr)
        return 1
    part_paths: list[Path] = []
    for idx, payload in enumerate(payloads, start=1):
        path = workdir / f"part-{idx}.json"
        _write_json(path, payload)
        part_paths.append(path)
    args_for_merge = ["merge", *map(str, part_paths), "--out", args.out]
    if args.json:
        args_for_merge.extend(["--json", args.json])
    return report_main(args_for_merge)


if __name__ == "__main__":
    raise SystemExit(audit_main())
