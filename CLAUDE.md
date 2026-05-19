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

Claude Code can invoke the project skill `data-risk-audit` via the `/data-risk-audit` slash command or by calling `Skill` with the skill name `data-risk-audit`. The skill is defined in `.agent/skills/data-risk-audit/SKILL.md` and handles the full audit workflow (route → detect → report) for single files and project folders.

- **Single file audit**: `Skill("data-risk-audit", args="审计：<input> 输出到：<output>")`
- **Output naming**: All output files must use `pcr` as the filename prefix (e.g., `pcr.audit.md`, `pcr.audit.route.json`). Never derive filenames from the input name or generate custom descriptions.
- **Project folder audit**: Follow the SOP in the skill's SKILL.md

When a user asks to audit, inspect, check, or review research data, manuscripts, images, code, or mixed project materials, **invoke this skill first** rather than running individual CLI commands directly.

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
