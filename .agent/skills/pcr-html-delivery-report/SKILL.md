---
name: pcr-html-delivery-report
description: Convert PCR delivery Markdown reports such as pcr.delivery-report.md into a professional, reliable, readable, and consistently styled standalone HTML client report. Use when the user asks to make an HTML/web version of a PCR delivery report, package a Markdown delivery report for client reading, or apply a stable web template to PCR report content.
---

# PCR HTML Delivery Report

## Purpose

Convert an existing `pcr.delivery-report.md` into a standalone HTML report for
client reading. The HTML version is a presentation layer only: it must preserve
the Markdown report's information, section order, evidence, tables, caveats, and
boundary statement without reinterpreting, shortening, or adding findings.

This skill is used after the Markdown delivery report has already been produced.
If the user needs the delivery report itself written first, use
`pcr-delivery-report` before this skill.

## Non-Negotiable Rules

1. Do not rewrite the source report content during HTML conversion.
2. Do not omit sections, bullets, table rows, evidence IDs, numeric values,
   file hashes, author questions, or boundary statements.
3. Do not upgrade risk signals into misconduct conclusions.
4. Keep `info` and service-boundary material as operational/service notes, not
   risk findings.
5. Use the fixed template in `references/delivery-report-template.html` for the
   outer page, CSS, layout, print style, and client-facing visual system.
6. If manual HTML edits are needed, edit only markup and presentation wrappers;
   preserve the source text exactly except for Markdown syntax conversion.

## Default Inputs And Outputs

- Default input: `output/pcr.delivery-report.md`
- Default output: same stem with `.html`, for example
  `output/pcr.delivery-report.html`
- Default template:
  `.agent/skills/pcr-html-delivery-report/references/delivery-report-template.html`
- Default renderer:
  `.agent/skills/pcr-html-delivery-report/scripts/render_delivery_html.py`

If the user gives a different Markdown path, write the HTML beside that file
unless they specify another output path.

## Recommended Workflow

1. Locate and read the source Markdown.
   - Confirm it is a finished PCR delivery report, not raw audit output.
   - Identify the title, major sections, tables, and final boundary statement.

2. Render deterministically.
   - Prefer the bundled renderer:

```bash
python3 .agent/skills/pcr-html-delivery-report/scripts/render_delivery_html.py \
  output/pcr.delivery-report.md \
  --out output/pcr.delivery-report.html
```

   - The renderer uses only Python standard library modules and injects the
     converted report body into the fixed HTML template.

3. Validate content alignment.
   - Re-run the renderer with `--check-only` or review the emitted validation
     summary.
   - Confirm at minimum:
     - Title-level delivery metadata such as `交付对象`, `预审材料`,
       `预审结果来源`, `报告日期`, `总体复核优先级`, and `投稿前状态判断`
       appears in the header metadata cards when present.
     - Markdown heading count equals HTML heading count.
     - Non-evidence Markdown table count equals HTML table count.
     - Non-evidence Markdown table body row count equals HTML table body row
       count.
     - Evidence-detail rows under `附录：证据明细` equal rendered evidence
       cards.
     - The strict boundary statement remains present.
     - The HTML contains all major sections from the Markdown source.

4. Inspect the HTML when possible.
   - Open the file locally or with the available browser tool.
   - Check desktop and narrow viewport readability.
   - Check print/PDF layout if the user plans to send or archive it.

5. Final response.
   - Report the generated HTML path.
   - Mention the validation results.
   - If any alignment check fails, do not present the report as complete; fix
     the conversion or explain the blocker.

## HTML Design Requirements

The generated page should feel like a professional research-service deliverable:

- Clean single-document layout with a clear header, report metadata area, sticky
  desktop table of contents, readable article body, and print-friendly styling.
- Header metadata cards must show client-facing delivery metadata from the
  Markdown report, not technical generation details such as source path,
  generation time, or validation text.
- Tables must be horizontally scrollable on small screens.
- Evidence-heavy appendix tables should render as readable evidence cards
  rather than compressed wide tables.
- Use restrained colors, high contrast, and stable spacing.
- Avoid decorative imagery, gradients, client-side dependencies, or remote
  assets. The HTML must be self-contained.
- Preserve Chinese punctuation and terminology from the Markdown report.

## Fidelity Checklist

Before handing off the HTML, verify:

- The H1 title is identical in meaning to the Markdown title.
- Every H2/H3 section appears in the same order.
- Each non-evidence Markdown table appears as one HTML table with the same
  headers and row count.
- The `附录：证据明细` evidence table, when present, appears as one card per
  evidence row with no loss of fields.
- Numbered author questions remain numbered.
- Inline code values such as `pcr.audit.json`, evidence IDs, and SHA-256 hashes
  remain visible.
- The final boundary statement is present and readable.
- No local absolute paths are newly exposed by the HTML wrapper.

## When Not To Use This Skill

- The user only wants raw detector output merged: use `data-risk-audit` or the
  `pcr-report` CLI.
- The user wants the narrative delivery report written or revised: use
  `pcr-delivery-report`.
- The user wants a DOCX/PDF instead of HTML: use the appropriate document or PDF
  workflow after the HTML/Markdown content has been validated.
