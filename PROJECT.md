# PCR mvp2 项目目标与架构

## 项目定位

`mvp2` 是面向 agent 的科研数据风险审计 CLI 工具链集合。它不是 Web 产品，也不是“造假判定器”。它的职责是把论文局部材料、原始数据、摘要统计表、正文统计文本等输入交给合适的本地或第三方 CLI 工具，输出可合并、可解释、可复核的风险信号。

所有报告措辞必须保持在“异常信号、证据、可能正常原因、复核建议”层面，不输出学术不端定性结论。

## 架构说明

```text
输入层
  论文局部材料 / 原始 CSV-XLSX / 摘要统计表 / 正文统计文本 / 图像材料
    ↓
抽取规范层
  pcr-extract 将异构文件转成 CSV/TXT/JSON 等可审计中间产物
    ↓
检测工具层
  Python CLI / R CLI / 未来第三方 CLI 独立运行
    ↓
统一结果层
  所有工具输出 finding JSON schema
    ↓
Agent 编排层
  agent 根据材料类型选择工具、合并发现、撰写审计说明
```

## 工具链分类

数据抽取与规范整理工具：

- `pcr-extract`：从 CSV、XLSX、DOCX、PDF 中抽取表格并规范为 CSV。
- 后续可增加 OCR、SPSS、RData、图表源数据抽取工具。

数据分析、统计一致性和风险核验工具：

- `pcr-raw-audit`：Python 原始数据规则和数字分布弱信号扫描。
- `pcr-statcheck`：R `statcheck` 原生 CLI，核验 APA/NHST 正文统计表达式与 p 值一致性。
- `pcr-scrutiny`：R `scrutiny` 原生 CLI，运行 GRIM、GRIMMER、DEBIT 摘要统计可行性检查。
- `pcr-sprite`：R `rsprite2` 原生 CLI，运行 SPRITE 离散摘要高级复核。
- `pcr-report merge`：合并多个 finding JSON 为 Markdown 报告。
- `pcr-audit run`：可选编排层，只在需要一键流水线时调用各语言原生 CLI。

## 扩展原则

- 能做成语言原生 CLI 的工具优先做成语言原生 CLI，不强行经 Python 中转。
- 每个工具必须声明适用输入、依赖状态、方法限制和误报风险。
- 每个工具必须输出统一 finding JSON，便于 agent 合并。
- 第三方商用工具后续应以独立 CLI/connector 形式接入，并记录数据上传合规边界。
- 工具缺失、依赖缺失和检测跳过只能记录为 `info`，不能计入数据风险。
