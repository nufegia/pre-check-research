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

Optional local image forensics dependencies:

```bash
python -m pip install -e ".[image]"
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
| `pcr-audit project` | Python | Folder/manifest | Multi-material pre-submission audit |
| `pcr-audit provenance` | Python | Folder/manifest | Append-only SHA-256 JSONL ledger |
| `pcr-audit corpus` | Python | Folder/manifest | Local corpus index and cross-manuscript screening |

```bash
pcr-audit route examples/summary_stat_sample.csv --json build/route.json
pcr-audit run examples/summary_stat_sample.csv --out build/auto.md --json build/auto.json
pcr-audit project path/to/project_folder --out build/project.md --json build/project.json
pcr-audit project examples/project_minimal --out build/project-minimal.md --json build/project-minimal.json
pcr-audit provenance record examples/project_minimal --json build/provenance-record.json
pcr-audit provenance verify examples/project_minimal --json build/provenance-verify.json
pcr-audit corpus build examples --out build/corpus-index.json
pcr-audit corpus screen examples/project_minimal --index build/corpus-index.json --out build/corpus-screen.md --json build/corpus-screen.json
pcr-audit project examples/project_questionnaire --inspect --json build/project-questionnaire.inspect.json
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
- `product_detectors.py`：最终产品版增量能力，包括参考文献核验、引用主张抽取、论文工厂轻量信号、图像内部重复初筛、哈希存证和代码复跑准备检查。

## 最终产品版增量能力

`pcr-audit project <folder-or-manifest>` 会对一个项目包执行多材料审计：

- 数据文件：继续使用确定性路由运行原始数据规则、交叉验证和可用 R 工具。
- 文档/参考文献：解析 DOI/PMID、抽取带引用主张、扫描轻量论文工厂短语信号。
- 图像：从 DOCX 或图片目录发现图片，使用 Pillow/numpy/scipy 的 aHash/dHash/pHash 和可选 OpenCV ORB 做同稿件内部重复、旋转/翻转相似、局部 copy-move 初筛，并生成 blot/gel 复核清单。
- 代码：只读扫描 R/Python/Stata/SPSS/SAS 脚本中的路径、输入、缺失剔除和显著性筛选线索。
- 溯源：对项目内文件计算 SHA-256、文件大小和修改时间；可用 `pcr-audit provenance` 写入追加式 JSONL 版本链并验证 matched/changed/missing/new。
- 论文工厂本地信号：可用 `pcr-audit corpus build/screen` 对本地项目语料建立索引，筛查文本模板、引用重叠、作者/邮箱域重叠和跨稿件图像指纹相似。

v0.7 增加了项目预检和样例库：

```bash
pcr-audit project examples/project_questionnaire --inspect --json build/questionnaire.inspect.json
pcr-audit project path/to/new_project --init-manifest
```

内置样例覆盖三类常见服务场景：

- `examples/project_minimal`：最小项目包。
- `examples/project_questionnaire`：问卷/社科摘要统计和原始数据。
- `examples/project_biomed`：生物医学数据、图像材料清单和文献核验。

默认不会把稿件或参考文献信息发往外部 API。需要 Crossref/OpenAlex/NCBI 元数据核验时，显式设置：

```bash
pcr-audit project examples/project_minimal --out build/project.md --json build/project.json --external-lookups --contact-email you@example.org
```

项目 manifest 使用 `pcr-project.json`：

```json
{
  "project_id": "optional-id",
  "title": "optional title",
  "materials": [
    {"path": "paper.docx", "role": "manuscript"},
    {"path": "data.csv", "role": "raw_data"},
    {"path": "analysis.py", "role": "analysis_code"},
    {"path": "figures/", "role": "figures"}
  ],
  "settings": {
    "external_lookups": false,
    "grobid_url": "http://localhost:8070",
    "contact_email": ""
  }
}
```

可选 GROBID REST 服务通过 manifest、`PCR_GROBID_URL` 或 CLI 参数启用：

```bash
pcr-audit project examples/project_minimal --out build/project.md --json build/project.json --grobid-url http://localhost:8070
```

商业/私有化部署默认不引入 PyMuPDF、grobid-client、imagehash、unstructured、tabula-py；GROBID 以独立 REST 服务接入，外部查询会在 workdir 中记录缓存和合规元数据，不缓存完整稿件正文。

## 扩展原则

- 能做成语言原生 CLI 的工具优先做成原生 CLI，不强行经 Python 中转。
- 每个工具必须声明适用输入、依赖状态、方法限制和误报风险。
- 可确定的数据形态识别和工具适用性判断必须进入 `tool_system.py`，不写死在 agent prompt/skill 中。
- 每个工具必须输出统一 finding JSON，便于 agent 合并。
- 第三方商用工具以独立 CLI/connector 形式接入，记录数据上传合规边界。
- 工具缺失、依赖缺失和检测跳过记录为 `info`，不计入数据风险。
