# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`merged-findings.json`
- 总体风险：低
- 检测对象：2 组
- 风险信号：高 0 / 中 0 / 低 0
- 运行提示：1 条

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
| data | table | 4 | 1 | raw_observation_table | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/data.csv |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | digit_distribution |
|---|---:|---:|---|
| data | 4 | 1 | 高0 中0 低0 |
| /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/data.csv | 0 | 0 | 高0 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| raw_data_rules | 基础表格规则 | data.csv:data | ready | ready | python | raw_observation_table | 确定性路由判定该工具适用于当前材料。 | 用于发现数据形态异常；实验设计变量、仪器阈值、批量导出格式可能触发误报。 |
| digit_distribution | 数字分布检测 | data.csv:data | insufficient_material | insufficient_material | python | raw_observation_table | 样本量/行数不足：需要至少 30 行，当前 4 行。 | 只适合样本量足够、变量类型合适的数值列；ID、百分比、评分、小样本和截断范围数据不适用。 |

## 覆盖缺口与未运行原因

| 工具 | 材料/模块 | 状态 | 依赖状态 | 原因 | 对预审的影响 |
|---|---|---|---|---|---|
| digit_distribution | data.csv:data | insufficient_material | insufficient_material | 样本量/行数不足：需要至少 30 行，当前 4 行。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |

## 风险发现清单（问题清单）

未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。

## 专家复核附录

本次没有可展开的风险发现。

## 人工复核任务表

本次没有由风险发现聚合出的人工复核任务。

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| digit_distribution | 1 |

- `digit_distribution`：数字分布检测 未运行：insufficient_material（样本量/行数不足：需要至少 30 行，当前 4 行。；依赖状态=insufficient_material；输入类型=raw_observation_table）

