# CLI 工具说明

## pcr-extract

用途：从 CSV、XLSX、DOCX、PDF 中抽取表格，输出规范 CSV 与 manifest JSON。

```bash
pcr-extract input.xlsx --out build/extracted --json build/extracted.json
```

边界：DOCX/PDF 抽取受合并单元格、脚注、复杂版式影响，重要结论建议用原始 CSV/XLSX 复测。

## pcr-raw-audit

用途：检查原始表格中的重复、缺失、高频值、固定步长、连续重复、离群值、数字分布等弱信号。

```bash
pcr-raw-audit data.csv --out build/raw.md --json build/raw.json
```

边界：输出是需要复核的模式，不是造假结论。设计变量、仪器阈值、批量格式化和数据清洗可能触发误报。

## pcr-statcheck

用途：R `statcheck` 原生 CLI，核验 APA/NHST 正文统计表达式与报告 p 值是否一致。

```bash
pcr-statcheck results.txt --json build/statcheck.json
```

边界：只适合类似 `t(28)=2.2, p<.05` 的 APA/NHST 表达；不覆盖多数复杂表格和非标准医学统计报告。

## pcr-scrutiny

用途：R `scrutiny` 原生 CLI，运行 GRIM、GRIMMER、DEBIT 摘要统计可行性检查。

```bash
pcr-scrutiny summary.csv --scale-min 1 --scale-max 5 --json build/scrutiny.json
```

边界：需要正确的 N、mean、SD/比例列和量表范围。变量不是离散/整数评分时，GRIM/GRIMMER 结果不应强解释。

## pcr-sprite

用途：R `rsprite2` 原生 CLI，用 SPRITE 对离散评分摘要统计做高级分布反推。

```bash
pcr-sprite summary.csv --scale-min 1 --scale-max 5 --json build/sprite.json
```

边界：解释成本高，依赖量表范围、小数精度和搜索参数；仅作为专家复核信号。

## pcr-report merge

用途：合并多个工具的 finding JSON，生成 Markdown 审计报告。

```bash
pcr-report merge build/raw.json build/scrutiny.json --out build/report.md --json build/report.json
```

## pcr-audit run

用途：可选编排层，根据场景调用已安装 CLI 并合并结果。

```bash
pcr-audit run data.csv --scenario raw --out build/report.md --json build/report.json
```

边界：不是 R 工具必经路径；agent 能直接调用专用 CLI 时应优先直接调用。
