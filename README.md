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

## Commands

| CLI | Runtime | Input | Purpose |
|-----|---------|-------|---------|
| `pcr-extract` | Python | XLSX/DOCX/PDF | Extract tables → CSV |
| `pcr-raw-audit` | Python | CSV | Raw-data digit distribution scan |
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
