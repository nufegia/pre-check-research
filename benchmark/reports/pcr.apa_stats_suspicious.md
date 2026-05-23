# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`apa_stats_suspicious.txt`
- 总体风险：高
- 检测对象：1 组
- 风险信号：高 2 / 中 0 / 低 0
- 运行提示：0 条

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
| apa_stats_suspicious.txt | table |  |  | apa_statistical_text | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/apa_stats_suspicious.txt |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | r_statcheck |
|---|---:|---:|---|
| /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/apa_stats_suspicious.txt | 0 | 0 | 高2 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| r_statcheck | R statcheck | apa_stats_suspicious.txt | ready | ready | r | apa_statistical_text | 确定性路由判定该工具适用于当前材料。 | 只适用于可被 statcheck 解析的 APA/NHST 表达式；中文全角标点、非标准统计报告和抽取失败文本会降低覆盖率。 |

## 覆盖缺口与未运行原因

本次路由上下文中未记录需要单列说明的未运行、依赖缺失或材料不足状态。

## 风险发现清单（问题清单）

| 风险 | 置信度 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |
|---|---:|---|---|---|---|---|---|---|
| 高 | 85% | r_statcheck:R_statcheck正文统计一致性:t(28)=2.20,_p=.90 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/apa_stats_suspicious.txt | R statcheck正文统计一致性 | t(28)=2.20, p=.90 | R statcheck 发现正文统计量与报告 p 值不一致。 | 报告p=0.9，反算p=0.0362254847788378 | 优先核对统计量、自由度、单双侧检验和 p 值是否来自同一次分析。 |
| 高 | 85% | r_statcheck:R_statcheck正文统计一致性:F(1,_30)=5.00,_p=.80 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/apa_stats_suspicious.txt | R statcheck正文统计一致性 | F(1, 30)=5.00, p=.80 | R statcheck 发现正文统计量与报告 p 值不一致。 | 报告p=0.8，反算p=0.0329363059256379 | 优先核对统计量、自由度、单双侧检验和 p 值是否来自同一次分析。 |

## 审计置信度摘要

| 方法学置信度 | 发现数 |
|---|---:|
| 高(>=75%) | 2 |
| 中(40%-75%) | 0 |
| 低(<40%) | 0 |

## 专家复核附录

### 1. 高风险：R statcheck正文统计一致性（t(28)=2.20, p=.90）

- 证据ID：r_statcheck:R_statcheck正文统计一致性:t(28)=2.20,_p=.90
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/apa_stats_suspicious.txt
- 发现：R statcheck 发现正文统计量与报告 p 值不一致。
- 触发证据：报告p=0.9，反算p=0.0362254847788378
- 工具：R statcheck（r_statcheck）
- 运行时/依赖：r / ready
- 输入类型：
- 置信度/误报风险：85%（high） / medium
- 详细说明：source=01; test_type=t; df1=NA; df2=28; test_comp==; test_value=2.2; p_comp==; reported_p=0.9; computed_p=0.0362254847788378; raw=t(28)=2.20, p=.90; error=TRUE; decision_error=TRUE; one_tailed_in_txt=FALSE; apa_factor=1
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括四舍五入、单双侧检验、统计量抽取错误或同一结果不同版本未同步。
- 复核动作：优先核对统计量、自由度、单双侧检验和 p 值是否来自同一次分析。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于 R statcheck 可解析表达式、统计量反算结果和依赖状态生成；需结合报告格式、单双侧检验和抽取质量人工判断。

### 2. 高风险：R statcheck正文统计一致性（F(1, 30)=5.00, p=.80）

- 证据ID：r_statcheck:R_statcheck正文统计一致性:F(1,_30)=5.00,_p=.80
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/apa_stats_suspicious.txt
- 发现：R statcheck 发现正文统计量与报告 p 值不一致。
- 触发证据：报告p=0.8，反算p=0.0329363059256379
- 工具：R statcheck（r_statcheck）
- 运行时/依赖：r / ready
- 输入类型：
- 置信度/误报风险：85%（high） / medium
- 详细说明：source=01; test_type=F; df1=1; df2=30; test_comp==; test_value=5; p_comp==; reported_p=0.8; computed_p=0.0329363059256379; raw=F(1, 30)=5.00, p=.80; error=TRUE; decision_error=TRUE; one_tailed_in_txt=FALSE; apa_factor=1
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括四舍五入、单双侧检验、统计量抽取错误或同一结果不同版本未同步。
- 复核动作：优先核对统计量、自由度、单双侧检验和 p 值是否来自同一次分析。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于 R statcheck 可解析表达式、统计量反算结果和依赖状态生成；需结合报告格式、单双侧检验和抽取质量人工判断。

## 人工复核任务表

| 序号 | 复核任务 | 涉及证据数 |
|---:|---|---:|
| 1 | 优先核对统计量、自由度、单双侧检验和 p 值是否来自同一次分析。 | 2 |

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| r_statcheck | 2 |

无运行提示。

