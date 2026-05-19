# PCR mvp2 — Research Data Risk Audit Workspace

Agent-oriented CLI toolkit for research data risk auditing. This workspace contains Python and R CLI tools that inspect research materials and emit structured risk-signal findings.

## Project Identity

- **Role**: Data risk audit toolchain, not a misconduct adjudicator
- **Output rules**: All reports stay at "anomalous signal → evidence → possible normal explanations → review steps." Never output misconduct conclusions.
- **Missing tools/deps**: Record as `level: info`, not as risk findings.

## Output Directory

All audit process documents (intermediate JSON, extracted CSV) and final reports (Markdown) **must** be placed under the project root `output/` directory. Use `--out output/<name>.md` and `--workdir output/<name>.parts` for `pcr-audit run`. All Markdown reports must have the `.md` extension.

## Setup

```bash
python -m pip install -e ".[dev]"
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages: `install.packages(c("statcheck", "scrutiny", "rsprite2"))`

## Project Skills

All skills are defined under `.agent/skills/<skill-name>/SKILL.md`. Invoke by calling `Skill` with the skill name, or by using the `/` slash command if registered.

### data-risk-audit

Primary audit skill. Handles the full workflow (route → detect → report) for single files and project folders.

- **When to use**: User asks to audit, inspect, check, or review research data, manuscripts, images, code, or mixed project materials. **Use this first** rather than running CLI commands directly.
- **Single file audit**: `Skill("data-risk-audit", args="审计：<input> 输出到：<output>")`
  - Internally runs `pcr-audit route` then `pcr-audit run --scenario auto`.
  - Input paths: single CSV, XLSX, DOCX, PDF, TXT, MD, image, or analysis code file.
- **Project folder audit**: Follow the SOP in `.agent/skills/data-risk-audit/SKILL.md`.
- **Output naming**: All files use `pcr` prefix (e.g., `pcr.audit.md`, `pcr.audit.route.json`). Never derive filenames from the input name.

### pcr-delivery-report

After audit results exist, converts them into a pre-submission decision report for PI/supervisor/author.

- **When to use**: User asks to write, polish, translate, summarize, or package pre-audit results into a non-technical delivery report that supports submission decisions.
- **Does not re-run detectors** — rewrites and prioritizes already-produced results.
- **Inputs**: `pcr.audit.json`, `pcr.audit.md`, or `pcr.audit.parts/*.json`.
- **Output**: Markdown delivery report following `.agent/skills/pcr-delivery-report/references/report-template.md`.
- **Key rules**:
  - Uses "复核优先级" instead of "风险等级".
  - Pre-submission status: one of "可继续推进投稿"/"建议补充说明后再投稿"/"建议暂缓投稿并补充材料复核"/"暂无法判断".
  - Aggregates findings into 2-5 signal clusters.
  - Includes 交付结论 table, 服务边界, 建议复核计划, 建议作者确认的问题, and 边界声明.
  - Never uses misconduct conclusions.

### pcr-html-delivery-report

Converts an existing Markdown delivery report (`pcr.delivery-report.md`) into a standalone HTML client report.

- **When to use**: User asks for an HTML/web version of the delivery report.
- **Prerequisite**: The Markdown delivery report must already exist (use `pcr-delivery-report` first).
- **Does not rewrite content** — presentation layer only.
- **Default pipeline**:
  ```bash
  python3 .agent/skills/pcr-html-delivery-report/scripts/render_delivery_html.py \
    output/pcr.delivery-report.md \
    --out output/pcr.delivery-report.html
  ```
- **Template**: `.agent/skills/pcr-html-delivery-report/references/delivery-report-template.html`
- **Fidelity**: Must preserve section order, tables, evidence IDs, numbers, boundary statement. No content reinterpretation.

## Commands

| CLI | Runtime | Purpose |
|-----|---------|---------|
| `pcr-extract` | Python | Extract tables from DOCX/PDF/XLSX → CSV |
| `pcr-raw-audit` | Python | Raw-data digit distribution scan |
| `pcr-statcheck` | R | APA/NHST text statistical consistency |
| `pcr-scrutiny` | R | GRIM/GRIMMER/DEBIT summary feasibility |
| `pcr-sprite` | R | SPRITE discrete distribution reconstruction |
| `pcr-report merge` | Python | Merge finding JSONs → Markdown |
| `pcr-audit run` | Python | Optional one-command pipeline |

## Unified Output Schema

All tools emit finding JSON conforming to `tools/common/schemas/finding.schema.json`.

## Source Layout

```
src/pcr_audit/          Python package (CLI entry points, detector adapters)
tools/r/                Standalone R CLI scripts
tools/python/           Python tool README
tools/common/schemas/   JSON Schema for finding payloads
skills/                 Legacy skill directory
.agent/skills/          Agent workspace skills (canonical location)
examples/               Sample input files
docs/                   Schema and tool documentation
tests/                  Pytest test suite
```

## Key Source Files

- `src/pcr_audit/cli.py` — Python CLI entry points (extract_main, raw_audit_main, report_main, audit_main)
- `src/pcr_audit/tool_system.py` — Tool system infrastructure
- `src/pcr_audit/data_trace_mvp.py` — Data trace MVP logic
- `src/pcr_audit/detectors/r/adapters.py` — R tool adapters
- `tools/r/pcr_statcheck/pcr-statcheck` — R statcheck CLI (standalone Rscript)
- `tools/r/pcr_scrutiny/pcr-scrutiny` — R scrutiny CLI (GRIM/GRIMMER/DEBIT)
- `tools/r/pcr_sprite/pcr-sprite` — R rsprite2 SPRITE CLI

## R CLI Conventions

All R CLIs follow the same pattern:
- Execute with `Rscript <script> <input> --json <output.json>`
- Handle missing R packages gracefully (emit info-level finding, exit 0)
- Accept `--scale-min` / `--scale-max` for scale-bounded tools
- Use `--json` flag to specify output file (stdout if omitted)
