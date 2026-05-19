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
from pcr_audit.runner import run_audit, run_project_audit


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

    project = sub.add_parser("project", help="Run a multi-material project audit over a folder or manifest JSON.")
    project.add_argument("input")
    project.add_argument("--out")
    project.add_argument("--json", help="Optional merged JSON output path.")
    project.add_argument("--workdir", help="Temporary output directory. Defaults to <out>.parts.")
    project.add_argument("--external-lookups", action="store_true", help="Enable Crossref/OpenAlex/NCBI lookups. Project audits enable this by default.")
    project.add_argument("--no-external-lookups", action="store_true", help="Disable default Crossref/OpenAlex/NCBI lookups for project audits.")
    project.add_argument("--grobid-url", default="", help="Optional GROBID REST base URL, e.g. http://localhost:8070.")
    project.add_argument("--contact-email", default="", help="Contact email for polite scholarly metadata API requests.")
    project.add_argument("--rerun-code", dest="rerun_code", action="store_true", default=True, help="Rerun Python/R analysis scripts in a temporary local sandbox. Default.")
    project.add_argument("--no-rerun-code", dest="rerun_code", action="store_false", help="Skip script reruns and only scan analysis code.")
    project.add_argument("--code-timeout", type=int, default=60, help="Per-script sandbox timeout in seconds. Defaults to 60.")
    project.add_argument("--inspect", action="store_true", help="Inspect project materials and print JSON without running detectors.")
    project.add_argument("--init-manifest", action="store_true", help="Create pcr-project.json for a project folder and exit.")
    project.add_argument("--overwrite", action="store_true", help="Allow --init-manifest to overwrite an existing pcr-project.json.")

    provenance = sub.add_parser("provenance", help="Manage local append-only SHA-256 provenance ledgers.")
    provenance_sub = provenance.add_subparsers(dest="provenance_command", required=True)
    for name in ("init", "record", "verify", "diff"):
        item = provenance_sub.add_parser(name)
        item.add_argument("input")
        item.add_argument("--ledger", help="JSONL ledger path. Defaults to <project>/.pcr/provenance-ledger.jsonl.")
        item.add_argument("--json", help="Optional JSON output path.")
        if name == "record":
            item.add_argument("--operator", default="", help="Optional operator identifier recorded in ledger entries.")
        if name == "diff":
            item.add_argument("--left-batch", default="", help="Older batch id. Defaults to previous batch.")
            item.add_argument("--right-batch", default="", help="Newer batch id. Defaults to latest batch.")

    corpus = sub.add_parser("corpus", help="Build and screen local papermill-style corpus indexes.")
    corpus_sub = corpus.add_subparsers(dest="corpus_command", required=True)
    corpus_build = corpus_sub.add_parser("build")
    corpus_build.add_argument("input")
    corpus_build.add_argument("--out", required=True, help="Output corpus-index.json path.")
    corpus_screen = corpus_sub.add_parser("screen")
    corpus_screen.add_argument("input")
    corpus_screen.add_argument("--index", required=True, help="Corpus index JSON produced by pcr-audit corpus build.")
    corpus_screen.add_argument("--out", required=True)
    corpus_screen.add_argument("--json", help="Optional finding JSON output path.")

    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command not in {"run", "route", "project", "provenance", "corpus"}:
        parser.print_help()
        return 2
    try:
        source = source_path(args.input)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.command == "provenance":
        from pcr_audit.product.provenance import (
            provenance_diff,
            provenance_init,
            provenance_payload_to_result,
            provenance_record,
            provenance_verify,
        )

        ledger = Path(args.ledger).expanduser().resolve() if args.ledger else None
        if args.provenance_command == "init":
            payload = provenance_init(source, ledger)
        elif args.provenance_command == "record":
            payload = provenance_record(source, ledger, args.operator)
        elif args.provenance_command == "verify":
            payload = provenance_verify(source, ledger)
        else:
            payload = provenance_diff(source, ledger, args.left_batch, args.right_batch)
        if args.json:
            json_path = Path(args.json).expanduser().resolve()
            if args.provenance_command in {"verify", "diff"}:
                save_json(json_path, source, [provenance_payload_to_result(source, payload)])
            else:
                write_json(json_path, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "corpus":
        from pcr_audit.io import read_json
        from pcr_audit.product.corpus_signals import analyze_papermill_network_signals, build_corpus_index

        if args.corpus_command == "build":
            out = Path(args.out).expanduser().resolve()
            payload = build_corpus_index(source)
            write_json(out, payload)
            print(f"本地语料索引已生成：{out}")
            return 0
        index = read_json(Path(args.index).expanduser().resolve())
        result = analyze_papermill_network_signals(source, index)
        out = markdown_out(args.out)
        out.write_text(render_markdown(source, [result], ["本报告基于本地 corpus-index.json 进行跨稿件弱信号筛查。"]), encoding="utf-8")
        if args.json:
            save_json(Path(args.json).expanduser().resolve(), source, [result])
        print(f"本地语料筛查报告已生成：{out}")
        return 0

    if args.command == "project":
        if args.inspect:
            from pcr_audit.product.project_manifest import inspect_project_payload

            workdir = Path(args.workdir).expanduser().resolve() if args.workdir else None
            payload = inspect_project_payload(source, workdir)
            if args.json:
                write_json(Path(args.json).expanduser().resolve(), payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.init_manifest:
            from pcr_audit.product.project_manifest import init_manifest_payload

            try:
                payload = init_manifest_payload(source, args.overwrite)
            except (FileExistsError, ValueError) as exc:
                print(exc, file=sys.stderr)
                return 1
            if args.json:
                write_json(Path(args.json).expanduser().resolve(), payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if not args.out:
            print("project 审计需要 --out；若只想预检材料，请使用 --inspect。", file=sys.stderr)
            return 2
        out = markdown_out(args.out)
        workdir = Path(args.workdir).expanduser().resolve() if args.workdir else None
        json_out = Path(args.json).expanduser().resolve() if args.json else None
        code = run_project_audit(
            source,
            out,
            json_out,
            workdir,
            external_lookups=False if args.no_external_lookups else True,
            grobid_url=args.grobid_url,
            contact_email=args.contact_email,
            rerun_code=args.rerun_code,
            code_timeout=args.code_timeout,
        )
        if code != 0:
            print("没有生成任何可合并结果。", file=sys.stderr)
            return code
        print(f"项目审计报告已生成：{out}")
        return 0

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
