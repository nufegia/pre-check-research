# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`merged-findings.json`
- 总体风险：低
- 检测对象：2 组
- 风险信号：高 0 / 中 0 / 低 0
- 运行提示：2 条

> 本报告只识别数据、统计、图像、文献和流程材料中的风险信号，不构成数据风险校验结论。高风险项表示需要优先回看原始记录、实验日志、原始图或统计脚本。

## 解析说明

- 本报告由多个 CLI finding JSON 合并生成。

## 预审范围与判读口径

- 本报告为自动化预审底稿，只记录可复算的风险信号、运行状态和覆盖缺口。
- 风险等级仅表示人工复核优先级，不构成数据风险校验结论。
- `info` 记录为工具运行、依赖、材料不足或路由状态，不计入风险信号。
- 未运行或不适用的工具表示本次材料/依赖/路由条件不足，不表示相应风险不存在。

## 材料清单

| 材料 | 角色/来源 | 行数 | 列数 | 输入类型/分类 | 状态 | 路径 |
|---|---|---:|---:|---|---|---|
| Sheet1 | table | 1 | 4 | summary_statistics_table | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/paper_tables.xlsx |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | crosscheck | r_scrutiny |
|---|---:|---:|---|---|
| Sheet1 | 1 | 4 | 高0 中0 低0 | 高0 中0 低0 |
| /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.project_full.parts/data-1.parts/extracted/01_Sheet1.csv | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| r_scrutiny | R scrutiny | paper_tables.xlsx:Sheet1 | ready | ready | r | summary_statistics_table | 确定性路由判定该工具适用于当前材料。 | 适用于报告均值、SD、N、比例或二元数据摘要；需确认量表范围、四舍五入规则和变量类型。 |
| crosscheck | 行级数学交叉校验 | paper_tables.xlsx:Sheet1 | ready | ready | python | summary_statistics_table | 确定性路由判定该工具适用于当前材料。 | 只校验表内派生统计量的数学一致性；无法判断原始观测是否真实或统计模型是否合适。 |

## 覆盖缺口与未运行原因

本次路由上下文中未记录需要单列说明的未运行、依赖缺失或材料不足状态。

## 风险发现清单（问题清单）

未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。

## 专家复核附录

本次没有可展开的风险发现。

## 人工复核任务表

本次没有由风险发现聚合出的人工复核任务。

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| crosscheck | 1 |
| r_scrutiny | 1 |

- `crosscheck`：逐行交叉验证已完成，未发现统计量内部不一致。（检查行数=1；依赖状态=ready；输入类型=summary_statistics_table）
- `r_scrutiny`：R scrutiny 已运行。（GRIMMER候选行=1；DEBIT候选行=0；依赖状态=ready；输入类型=）

