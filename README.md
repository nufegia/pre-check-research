# PCR mvp2

Agent-oriented CLI toolkit for research data risk auditing.

输出定位：把论文材料交给合适的 CLI 工具，输出可合并、可解释、可复核的风险信号。所有报告措辞保持在"异常信号、证据、可能正常原因、复核建议"层面，**不输出学术不端定性结论**。

## 架构

```
输入层
  论文材料 / 原始 CSV-XLSX / 摘要统计表 / 正文统计文本 / 图像
    ↓
抽取层（pcr-extract）
  异构文件 → CSV/TXT/JSON 中间产物
    ↓
确定性路由层
  tool_system.py / router.py / pcr-audit route
    ↓
薄执行器
  runner.py 只执行 route-ready 工具
    ↓
检测层（Python CLI / R CLI）
  detectors/raw.py / crosscheck.py / tools/r/*
    ↓
统一结果层
  models.py / reporting.py / finding JSON
    ↓
Agent 编排层
  阅读 route 和报告，补充人工复核叙述
```

## Install

```bash
python -m pip install -e ".[dev]"
```

R CLIs are executable `Rscript` files under `tools/r/`. Add them to `PATH`:

```bash
export PATH="$PWD/tools/r/pcr_statcheck:$PWD/tools/r/pcr_scrutiny:$PWD/tools/r/pcr_sprite:$PATH"
```

Optional R packages:

```r
install.packages(c("statcheck", "scrutiny", "rsprite2"))
```

## 使用方式

推荐先使用确定性路由层判断输入适合哪些检测工具，再运行审计。这样可以把“工具是否适用”和“工具是否缺依赖”记录进 JSON，避免由 agent 或人工临时猜测。

```bash
mkdir -p build
pcr-audit route examples/summary_stat_sample.csv --json build/route.json
pcr-audit run examples/summary_stat_sample.csv --scenario auto --out build/audit.md --json build/audit.json
```

`pcr-audit run` 会自动分类输入、执行 route-ready 工具，并把各工具输出合并为 Markdown 报告和统一 JSON。默认 `--scenario auto` 会按数据形态选择工具：

| 输入形态 | auto 场景默认动作 |
|----------|-------------------|
| 原始观测表、图表源数据 | 运行 Python 原始数据规则 `raw_data_rules` |
| 摘要统计表 | 运行行级数学交叉校验 `crosscheck`，并在 R 依赖可用时运行 `scrutiny` |
| Likert/整数评分摘要 | 运行 `crosscheck`、`scrutiny`，并在 R 依赖可用时运行 `rsprite2` |
| APA/NHST 正文统计文本 | 在 R 依赖可用时运行 `statcheck` |

也可以显式指定场景：

```bash
pcr-audit run data.csv --scenario raw --out build/raw.md --json build/raw.json
pcr-audit run summary.csv --scenario summary --out build/summary.md --json build/summary.json
pcr-audit run stats.txt --scenario text --out build/text.md --json build/text.json
pcr-audit run likert_summary.csv --scenario r-advanced --out build/sprite.md --json build/sprite.json
```

如果只想查看路由结果、不运行检测器：

```bash
pcr-audit run examples/summary_stat_sample.csv --out build/dry.md --json build/dry-route.json --dry-run
```

对 DOCX/PDF/XLSX 等材料，可先抽取中间产物，再对抽出的 CSV/TXT 运行对应工具：

```bash
pcr-extract examples/suspicious_sample.xlsx --out build/extracted --json build/extracted.json
pcr-raw-audit build/extracted/01_Sheet1.csv --out build/raw.md --json build/raw.json
```

抽取后的文件名以 `build/extracted.json` 里的 `outputs[].path` 为准；如果抽出的是摘要统计表，可将该 CSV 交给 `pcr-crosscheck` 或让 `pcr-audit run` 自动路由。

需要手动组合多个工具结果时，使用 `pcr-report merge`：

```bash
pcr-report merge build/raw.json build/crosscheck.json --out build/merged.md --json build/merged.json
```

结果解释边界：

- `level: info` 通常表示工具运行记录、缺少依赖、材料不足或跳过原因，不应当当作风险发现。
- `medium` / `high` 表示需要人工复核的风险信号，不是学术不端、造假或舞弊结论。
- PDF/DOCX 抽取可能引入表格识别错误；重要发现应优先回到原始 CSV/XLSX、统计脚本或原始数据复测。

## Commands

| CLI | Runtime | Input | Purpose |
|-----|---------|-------|---------|
| `pcr-extract` | Python | XLSX/DOCX/PDF | Extract tables → CSV |
| `pcr-raw-audit` | Python | CSV | Raw-data digit distribution scan |
| `pcr-crosscheck` | Python | CSV/XLSX/DOCX/PDF | Row-level summary-stat math cross-checks |
| `pcr-statcheck` | R | TXT | APA/NHST reporting consistency |
| `pcr-scrutiny` | R | CSV | GRIM/GRIMMER/DEBIT feasibility |
| `pcr-sprite` | R | CSV | SPRITE discrete reconstruction |
| `pcr-report merge` | Python | JSON | Merge findings → Markdown |
| `pcr-audit route` | Python | Mixed | Explain deterministic tool routing |
| `pcr-audit run` | Python | Mixed | Optional one-command pipeline |

```bash
pcr-audit route examples/summary_stat_sample.csv --json build/route.json
pcr-audit run examples/summary_stat_sample.csv --out build/auto.md --json build/auto.json
pcr-audit run examples/summary_stat_sample.csv --out build/route.md --json build/route.json --dry-run
pcr-extract examples/suspicious_sample.xlsx --out build/extracted --json build/extracted.json
pcr-raw-audit examples/suspicious_sample.csv --out build/raw.md --json build/raw.json
pcr-crosscheck examples/summary_stat_sample.csv --out build/crosscheck.md --json build/crosscheck.json
pcr-scrutiny examples/summary_stat_sample.csv --scale-min 1 --scale-max 5 --json build/scrutiny.json
pcr-report merge build/raw.json build/scrutiny.json --out build/merged.md --json build/merged.json
```

确定性情景优先使用 `pcr-audit route` / `pcr-audit run --scenario auto`。Agent 不直接猜测工具适用性，只读取路由结果并执行 `ready` 工具；只有多材料整理、报告叙述和人工复核建议交给 agent 编排。

## Python 模块

- `models.py`：finding/result 数据模型和解释字段补全。
- `io.py`：输入解析、表格读取、文本抽取和 extraction manifest。
- `tool_system.py`：工具注册表、数据分类、依赖状态和路由判定。
- `router.py`：构建稳定 route JSON。
- `runner.py`：执行 route-ready 工具并合并结果。
- `reporting.py`：Markdown/JSON 报告渲染与合并。
- `detectors/` 与 `crosscheck.py`：具体检测器实现。

## 扩展原则

- 能做成语言原生 CLI 的工具优先做成原生 CLI，不强行经 Python 中转。
- 每个工具必须声明适用输入、依赖状态、方法限制和误报风险。
- 可确定的数据形态识别和工具适用性判断必须进入 `tool_system.py`，不写死在 agent prompt/skill 中。
- 每个工具必须输出统一 finding JSON，便于 agent 合并。
- 第三方商用工具以独立 CLI/connector 形式接入，记录数据上传合规边界。
- 工具缺失、依赖缺失和检测跳过记录为 `info`，不计入数据风险。
