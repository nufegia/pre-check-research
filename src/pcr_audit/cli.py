from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pcr_audit import __version__
from pcr_audit.detectors.raw import analyze_raw_data_rules
from pcr_audit.io import extract_file, load_tables, markdown_out, source_path, write_json
from pcr_audit.reporting import merge_reports, render_markdown, save_json
from pcr_audit.router import build_route_payload
from pcr_audit.runner import run_audit


SCENARIOS = ["auto", "raw", "summary", "text", "r-advanced"]


def extract_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract tables from CSV/XLSX/DOCX/PDF into normalized CSV files.")
    parser.add_argument("input")
    parser.add_argument("--out", required=True, help="Output directory for normalized artifacts.")
    parser.add_argument("--json", help="Optional extraction manifest JSON path.")
    args = parser.parse_args(argv)
    try:
        payload = extract_file(source_path(args.input), Path(args.out).expanduser().resolve())
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"抽取失败：{exc}", file=sys.stderr)
        return 1
    if args.json:
        write_json(Path(args.json).expanduser().resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def raw_audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Python raw-data risk checks and write Markdown/JSON reports.")
    parser.add_argument("input", help="CSV/XLSX/XLS/DOCX/PDF input.")
    parser.add_argument("--out", required=True, help="Markdown report output path.")
    parser.add_argument("--json", help="Optional finding JSON output path.")
    args = parser.parse_args(argv)
    try:
        source = source_path(args.input)
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
    results = [analyze_raw_data_rules(name, df) for name, df in tables]
    notes = ["当前输入来自文档抽取，重要结论建议用原始 CSV/XLSX 复测。"] if source.suffix.lower() in {".pdf", ".docx"} else []
    out_path = markdown_out(args.out)
    out_path.write_text(render_markdown(source, results, notes), encoding="utf-8")
    if args.json:
        save_json(Path(args.json).expanduser().resolve(), source, results)
    print(f"报告已生成：{out_path}")
    return 0


def crosscheck_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run row-level mathematical cross-checks on summary statistics tables "
        "(SE/SD/√N, CI/SE, percent/count/N, p/t/df)."
    )
    parser.add_argument("input", help="CSV/XLSX/XLS/DOCX/PDF containing summary statistics.")
    parser.add_argument("--out", required=True, help="Markdown report output path.")
    parser.add_argument("--json", help="Optional finding JSON output path.")
    args = parser.parse_args(argv)
    try:
        source = source_path(args.input)
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

    from pcr_audit.crosscheck import crosscheck_table

    results = [crosscheck_table(name, df) for name, df in tables]
    notes = ["当前输入来自文档抽取，交叉验证结果建议用原始 CSV/XLSX 复测。"] if source.suffix.lower() in {".pdf", ".docx"} else []
    out_path = markdown_out(args.out)
    out_path.write_text(render_markdown(source, results, notes), encoding="utf-8")
    if args.json:
        save_json(Path(args.json).expanduser().resolve(), source, results)
    print(f"报告已生成：{out_path}")
    return 0


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
    try:
        merge_reports(
            args.finding_json,
            markdown_out(args.out),
            Path(args.json).expanduser().resolve() if args.json else None,
        )
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"合并失败：{exc}", file=sys.stderr)
        return 1
    print(f"合并报告已生成：{markdown_out(args.out)}")
    return 0


def audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic orchestration layer for PCR audit tools.")
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    sub = parser.add_subparsers(dest="command")

    route = sub.add_parser("route", help="Classify input and explain deterministic tool routing.")
    route.add_argument("input")
    route.add_argument("--scenario", choices=SCENARIOS, default="auto")
    route.add_argument("--json", help="Optional route JSON output path.")

    run = sub.add_parser("run", help="Run route-ready tools and merge outputs.")
    run.add_argument("input")
    run.add_argument("--scenario", choices=SCENARIOS, default="auto")
    run.add_argument("--out", required=True)
    run.add_argument("--json", help="Optional merged JSON output path.")
    run.add_argument("--workdir", help="Temporary output directory. Defaults to <out>.parts.")
    run.add_argument("--dry-run", action="store_true", help="Only print deterministic routing decisions; do not run detectors.")

    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command not in {"run", "route"}:
        parser.print_help()
        return 2
    try:
        source = source_path(args.input)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.command == "route" or args.dry_run:
        payload = build_route_payload(source, args.scenario)
        if args.json:
            write_json(Path(args.json).expanduser().resolve(), payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    out = markdown_out(args.out)
    workdir = Path(args.workdir).expanduser().resolve() if args.workdir else None
    json_out = Path(args.json).expanduser().resolve() if args.json else None
    code = run_audit(source, out, json_out, workdir, args.scenario, False)
    if code != 0:
        print("没有生成任何可合并结果。", file=sys.stderr)
        return code
    print(f"合并报告已生成：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(audit_main())
