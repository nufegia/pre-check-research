#!/usr/bin/env python3
"""Render a PCR Markdown delivery report into a stable standalone HTML page."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_DIR / "references" / "delivery-report-template.html"
BOUNDARY_PHRASE = "复核信号不等同于学术不端认定"


def break_long_tokens(escaped_text: str, chunk_size: int = 24) -> str:
    def break_match(match: re.Match[str]) -> str:
        token = match.group(0)
        return "<wbr>".join(
            token[index : index + chunk_size] for index in range(0, len(token), chunk_size)
        )

    return re.sub(r"[A-Za-z0-9_:/=.\-]{32,}", break_match, escaped_text)


def slugify(text: str, used: set[str]) -> str:
    base = re.sub(r"\s+", "-", text.strip().lower())
    base = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", base).strip("-")
    if not base:
        base = "section"
    slug = base
    index = 2
    while slug in used:
        slug = f"{base}-{index}"
        index += 1
    used.add(slug)
    return slug


def inline_markdown(text: str) -> str:
    code_values: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_values.append(break_long_tokens(html.escape(match.group(1))))
        return f"\x00CODE{len(code_values) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash_code, text)
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = break_long_tokens(escaped)

    for index, value in enumerate(code_values):
        escaped = escaped.replace(f"\x00CODE{index}\x00", f"<code>{value}</code>")
    return escaped


def split_report_metadata(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    lines = markdown.splitlines()
    if not lines or not re.match(r"^#\s+", lines[0].strip()):
        return markdown, []

    index = 1
    while index < len(lines) and not lines[index].strip():
        index += 1

    metadata_start = index
    metadata: list[tuple[str, str]] = []
    while index < len(lines):
        match = re.match(r"^-\s+\*\*(.+?)\*\*[:：]\s*(.+?)\s*$", lines[index].strip())
        if not match:
            break
        metadata.append((match.group(1), match.group(2)))
        index += 1

    if not metadata:
        return markdown, []

    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and lines[index].strip() == "---":
        index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1

    cleaned = lines[:metadata_start] + [""] + lines[index:]
    return "\n".join(cleaned), metadata


def build_report_meta(metadata: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for label, value in metadata:
        parts.append("<div class=\"meta-item\">")
        parts.append(f"<span class=\"meta-label\">{inline_markdown(label)}</span>")
        parts.append(f"<span class=\"meta-value\">{inline_markdown(value)}</span>")
        parts.append("</div>")
    return "\n".join(parts)


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    stripped = stripped[1:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def parse_table_rows(lines: list[str], start: int) -> tuple[list[str], list[list[str]], int]:
    header = split_table_row(lines[start])
    rows: list[list[str]] = []
    index = start + 2
    while index < len(lines):
        cells = split_table_row(lines[index])
        if not cells:
            break
        rows.append(cells)
        index += 1

    return header, rows, index


def parse_table(lines: list[str], start: int) -> tuple[str, int]:
    header, rows, index = parse_table_rows(lines, start)
    parts = ["<div class=\"table-wrap\"><table>"]
    parts.append("<thead><tr>")
    for cell in header:
        parts.append(f"<th>{inline_markdown(cell)}</th>")
    parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in rows:
        normalized = row + [""] * max(0, len(header) - len(row))
        parts.append("<tr>")
        for cell in normalized[: len(header)]:
            parts.append(f"<td>{inline_markdown(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts), index


def render_evidence_cards(header: list[str], rows: list[list[str]]) -> str:
    header_index = {name: idx for idx, name in enumerate(header)}

    def value(row: list[str], column: str) -> str:
        idx = header_index.get(column)
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    parts = ["<section class=\"evidence-card-grid\" aria-label=\"证据明细卡片\">"]
    for row in rows:
        priority = value(row, "复核优先级")
        check = value(row, "检查项")
        evidence_id = value(row, "证据ID")
        location = value(row, "位置")
        target = value(row, "对象")
        evidence = value(row, "证据")
        action = value(row, "复核动作")
        parts.append("<article class=\"evidence-card\">")
        parts.append("<div class=\"evidence-card__meta\">")
        if priority:
            parts.append(f"<span>{inline_markdown(priority)}</span>")
        if check:
            parts.append(f"<span>{inline_markdown(check)}</span>")
        parts.append("</div>")
        parts.append(
            f"<p class=\"evidence-card__title\">{inline_markdown(target or check or evidence_id or '证据记录')}</p>"
        )
        if location:
            parts.append(f"<p class=\"evidence-card__location\">{inline_markdown(location)}</p>")
        if evidence_id:
            parts.append(f"<p class=\"evidence-card__id\">{inline_markdown(evidence_id)}</p>")
        if evidence:
            parts.append(
                f"<div class=\"evidence-card__block\"><span>证据</span><p>{inline_markdown(evidence)}</p></div>"
            )
        if action:
            parts.append(
                f"<div class=\"evidence-card__block evidence-card__action\"><span>复核动作</span><p>{inline_markdown(action)}</p></div>"
            )
        parts.append("</article>")
    parts.append("</section>")
    return "".join(parts)


def is_evidence_table(header: list[str]) -> bool:
    required = {"证据ID", "复核优先级", "检查项", "位置", "对象", "证据", "复核动作"}
    return required.issubset(set(header))


def flush_paragraph(paragraph: list[str], output: list[str]) -> None:
    if not paragraph:
        return
    text = " ".join(part.strip() for part in paragraph).strip()
    if text:
        output.append(f"<p>{inline_markdown(text)}</p>")
    paragraph.clear()


def flush_list(list_items: list[tuple[str, str]], output: list[str]) -> None:
    if not list_items:
        return
    tag = "ol" if list_items[0][0] == "ol" else "ul"
    output.append(f"<{tag}>")
    for _, item in list_items:
        output.append(f"<li>{inline_markdown(item)}</li>")
    output.append(f"</{tag}>")
    list_items.clear()


def markdown_to_html(markdown: str) -> tuple[str, list[dict[str, str]]]:
    lines = markdown.splitlines()
    output: list[str] = []
    headings: list[dict[str, str]] = []
    paragraph: list[str] = []
    list_items: list[tuple[str, str]] = []
    used_slugs: set[str] = set()
    in_evidence_appendix = False
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph(paragraph, output)
            flush_list(list_items, output)
            index += 1
            continue

        if stripped == "---":
            flush_paragraph(paragraph, output)
            flush_list(list_items, output)
            output.append("<hr>")
            index += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading_match:
            flush_paragraph(paragraph, output)
            flush_list(list_items, output)
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            in_evidence_appendix = "附录：证据明细" in text
            section_id = slugify(re.sub(r"`([^`]+)`", r"\1", text), used_slugs)
            headings.append({"level": str(level), "text": text, "id": section_id})
            output.append(
                f"<h{level} id=\"{html.escape(section_id)}\">{inline_markdown(text)}</h{level}>"
            )
            index += 1
            continue

        if (
            stripped.startswith("|")
            and index + 1 < len(lines)
            and is_table_separator(lines[index + 1])
        ):
            flush_paragraph(paragraph, output)
            flush_list(list_items, output)
            header, rows, next_index = parse_table_rows(lines, index)
            if in_evidence_appendix and is_evidence_table(header):
                output.append(render_evidence_cards(header, rows))
                in_evidence_appendix = False
                index = next_index
            else:
                table_html, index = parse_table(lines, index)
                output.append(table_html)
            continue

        ul_match = re.match(r"^[-*]\s+(.+)$", stripped)
        ol_match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if ul_match or ol_match:
            flush_paragraph(paragraph, output)
            kind = "ul" if ul_match else "ol"
            if list_items and list_items[0][0] != kind:
                flush_list(list_items, output)
            list_items.append((kind, (ul_match or ol_match).group(1)))
            index += 1
            continue

        flush_list(list_items, output)
        paragraph.append(line)
        index += 1

    flush_paragraph(paragraph, output)
    flush_list(list_items, output)
    return "\n".join(output), headings


def build_toc(headings: list[dict[str, str]]) -> str:
    toc_items = [h for h in headings if h["level"] in {"2", "3"}]
    if not toc_items:
        return "<ol><li><a href=\"#top\">报告正文</a></li></ol>"
    parts = ["<ol>"]
    for heading in toc_items:
        level = html.escape(heading["level"])
        section_id = html.escape(heading["id"])
        text = inline_markdown(heading["text"])
        parts.append(f"<li class=\"level-{level}\"><a href=\"#{section_id}\">{text}</a></li>")
    parts.append("</ol>")
    return "\n".join(parts)


def markdown_stats(markdown: str) -> dict[str, int | bool]:
    lines = markdown.splitlines()
    heading_count = sum(1 for line in lines if re.match(r"^#{1,6}\s+", line.strip()))
    table_count = 0
    table_rows = 0
    evidence_table_count = 0
    evidence_rows = 0
    in_evidence_appendix = False
    index = 0
    while index < len(lines):
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", lines[index].strip())
        if heading_match:
            in_evidence_appendix = "附录：证据明细" in heading_match.group(2)
            index += 1
            continue
        if (
            lines[index].strip().startswith("|")
            and index + 1 < len(lines)
            and is_table_separator(lines[index + 1])
        ):
            header, rows, next_index = parse_table_rows(lines, index)
            table_count += 1
            table_rows += len(rows)
            if in_evidence_appendix and is_evidence_table(header):
                evidence_table_count += 1
                evidence_rows += len(rows)
                in_evidence_appendix = False
            index = next_index
            continue
        index += 1
    return {
        "headings": heading_count,
        "tables": table_count,
        "table_rows": table_rows,
        "regular_tables": table_count - evidence_table_count,
        "regular_table_rows": table_rows - evidence_rows,
        "evidence_rows": evidence_rows,
        "boundary_present": BOUNDARY_PHRASE in markdown,
    }


def html_stats(rendered_html: str) -> dict[str, int | bool]:
    return {
        "headings": len(re.findall(r"<h[1-6]\b", rendered_html)),
        "tables": rendered_html.count("<table>"),
        "table_rows": rendered_html.count("<tr>") - rendered_html.count("<thead><tr>"),
        "evidence_cards": rendered_html.count("class=\"evidence-card\""),
        "boundary_present": BOUNDARY_PHRASE in rendered_html,
    }


def validation_summary(markdown: str, body_html: str) -> tuple[str, list[str]]:
    md = markdown_stats(markdown)
    rendered = html_stats(body_html)
    failures: list[str] = []
    comparisons = (
        ("headings", md["headings"], rendered["headings"]),
        ("regular_tables", md["regular_tables"], rendered["tables"]),
        ("regular_table_rows", md["regular_table_rows"], rendered["table_rows"]),
        ("evidence_cards", md["evidence_rows"], rendered["evidence_cards"]),
    )
    for key, expected, actual in comparisons:
        if expected != actual:
            failures.append(f"{key}: markdown={expected} html={actual}")
    if md["boundary_present"] and not rendered["boundary_present"]:
        failures.append("boundary statement missing in HTML")
    if failures:
        return "未通过：" + "; ".join(failures), failures
    return (
        f"已通过：标题 {md['headings']}，普通表格 {md['regular_tables']}，普通表格行 {md['regular_table_rows']}，证据卡片 {md['evidence_rows']}",
        [],
    )


def extract_title(headings: list[dict[str, str]], fallback: str) -> str:
    for heading in headings:
        if heading["level"] == "1":
            return re.sub(r"`([^`]+)`", r"\1", heading["text"])
    return fallback


def render(markdown_path: Path, template_path: Path) -> tuple[str, str, list[str]]:
    markdown = markdown_path.read_text(encoding="utf-8")
    content_markdown, metadata = split_report_metadata(markdown)
    body_html, headings = markdown_to_html(content_markdown)
    title = extract_title(headings, markdown_path.stem)
    summary, failures = validation_summary(content_markdown, body_html)
    template = template_path.read_text(encoding="utf-8")

    page = (
        template.replace("{{TITLE}}", html.escape(title))
        .replace("{{REPORT_META}}", build_report_meta(metadata))
        .replace("{{TOC}}", build_toc(headings))
        .replace("{{REPORT_BODY}}", body_html)
    )
    return page, summary, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path, help="Source pcr.delivery-report.md path")
    parser.add_argument("--out", type=Path, help="Output HTML path")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--check-only", action="store_true", help="Validate without writing HTML")
    args = parser.parse_args(argv)

    out_path = args.out or args.markdown.with_suffix(".html")
    page, summary, failures = render(args.markdown, args.template)
    print(summary)
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 2
    if not args.check_only:
        out_path.write_text(page, encoding="utf-8")
        print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
