# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`merged-findings.json`
- 总体风险：高
- 检测对象：3 组
- 风险信号：高 14 / 中 2 / 低 1
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
| summary_suspicious | table | 4 | 13 | likert_or_integer_scale_summary, summary_statistics_table | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | crosscheck | r_rsprite2 | r_scrutiny |
|---|---:|---:|---|---|---|
| summary_suspicious | 4 | 13 | 高9 中2 低1 | 高0 中0 低0 | 高0 中0 低0 |
| /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv | 0 | 0 | 高0 中0 低0 | 高4 中0 低0 | 高1 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| r_scrutiny | R scrutiny | summary_suspicious.csv:summary_suspicious | ready | ready | r | likert_or_integer_scale_summary | 确定性路由判定该工具适用于当前材料。 | 适用于报告均值、SD、N、比例或二元数据摘要；需确认量表范围、四舍五入规则和变量类型。 |
| r_rsprite2 | R rsprite2 | summary_suspicious.csv:summary_suspicious | ready | ready | r | likert_or_integer_scale_summary | 确定性路由判定该工具适用于当前材料。 | 需要明确量表范围、精度和约束；结果解释成本高，只作为专家复核入口。 |
| crosscheck | 行级数学交叉校验 | summary_suspicious.csv:summary_suspicious | ready | ready | python | likert_or_integer_scale_summary | 确定性路由判定该工具适用于当前材料。 | 只校验表内派生统计量的数学一致性；无法判断原始观测是否真实或统计模型是否合适。 |

## 覆盖缺口与未运行原因

本次路由上下文中未记录需要单列说明的未运行、依赖缺失或材料不足状态。

## 风险发现清单（问题清单）

| 风险 | 置信度 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |
|---|---:|---|---|---|---|---|---|---|
| 高 | 82% | unknown:SE/SD/√N一致性:行2 | summary_suspicious | SE/SD/√N一致性 | 行2 | 标准误SE与SD/√N不一致（偏差=85.1%） | SE报告=0.1，SD/√N=0.67082，N=20，SD=3 | 核对SE是否为标准误（非SD或CI半宽），确认统计脚本输出。 |
| 高 | 82% | unknown:百分比/计数一致性:行2 | summary_suspicious | 百分比/计数一致性 | 行2 | 百分比与count/N反算不一致（差值=15.000） | 报告=25，count/N×100=40，count=8，N=20 | 核对百分比的分母是否为该行的N；确认count是否正确。 |
| 高 | 82% | unknown:p值/t统计量一致性:行2 | summary_suspicious | p值/t统计量一致性 | 行2 | p值与t统计量(df)反算不一致（差值=0.1926） | 报告p=0.2（解析为0.2），t=3，df=19，反算p=0.00736172 | 核对t、df和p值是否来自同一次分析，是否为单侧检验。 |
| 高 | 82% | unknown:SE/SD/√N一致性:行3 | summary_suspicious | SE/SD/√N一致性 | 行3 | 标准误SE与SD/√N不一致（偏差=76.4%） | SE报告=0.1，SD/√N=0.424264，N=18，SD=1.8 | 核对SE是否为标准误（非SD或CI半宽），确认统计脚本输出。 |
| 高 | 82% | unknown:CI区间倒置:行3 | summary_suspicious | CI区间倒置 | 行3 | 置信区间下限大于上限。 | CI=[8.2, 7.8]，下限 > 上限 | CI列顺序可能写反，或表格抽取时发生错列。 |
| 高 | 82% | unknown:百分比/计数一致性:行3 | summary_suspicious | 百分比/计数一致性 | 行3 | 百分比与count/N反算不一致（差值=33.333） | 报告=50，count/N×100=16.6667，count=3，N=18 | 核对百分比的分母是否为该行的N；确认count是否正确。 |
| 高 | 82% | unknown:p值超出定义域:行3 | summary_suspicious | p值超出定义域 | 行3 | p值超出[0, 1]范围。 | 报告p值=1.2（p） | p值必须介于0到1之间；可能是录入错误或小数点位错。 |
| 高 | 82% | unknown:p值/t统计量一致性:行3 | summary_suspicious | p值/t统计量一致性 | 行3 | p值与t统计量(df)反算不一致（差值=1.0682） | 报告p=1.2（解析为1.2），t=1.8，df=5，反算p=0.131758 | 核对t、df和p值是否来自同一次分析，是否为单侧检验。 |
| 高 | 82% | unknown:p值/t统计量一致性:行4 | summary_suspicious | p值/t统计量一致性 | 行4 | p值与t统计量(df)反算不一致（差值=0.3434） | 报告p=0.0（解析为0），t=1，df=9，反算p=0.343436 | 核对t、df和p值是否来自同一次分析，是否为单侧检验。 |
| 高 | 85% | r_scrutiny:R_scrutiny_GRIMMER:行4 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv | R scrutiny GRIMMER | 行4 | GRIMMER 检查发现均值、SD 与样本量在离散评分条件下不可同时成立。 | N=10, mean=12.0, SD=-1.0 | 确认量表范围、四舍五入精度和变量类型；回看原始计数或统计脚本。 |
| 高 | 85% | r_rsprite2:R_rsprite2_SPRITE:行1 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv | R rsprite2 SPRITE | 行1 | SPRITE 未能找到匹配报告摘要统计的离散分布。 | N=25, mean=10.0, SD=2.0, scale=1-5；Error in calculating range of possible standard deviations | 确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。 |
| 高 | 85% | r_rsprite2:R_rsprite2_SPRITE:行2 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv | R rsprite2 SPRITE | 行2 | SPRITE 未能找到匹配报告摘要统计的离散分布。 | N=20, mean=5.0, SD=3.0, scale=1-5；Error in calculating range of possible standard deviations | 确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。 |
| 高 | 85% | r_rsprite2:R_rsprite2_SPRITE:行3 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv | R rsprite2 SPRITE | 行3 | SPRITE 未能找到匹配报告摘要统计的离散分布。 | N=18, mean=8.0, SD=1.8, scale=1-5；Error in calculating range of possible standard deviations | 确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。 |
| 高 | 85% | r_rsprite2:R_rsprite2_SPRITE:行4 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv | R rsprite2 SPRITE | 行4 | SPRITE 未能找到匹配报告摘要统计的离散分布。 | N=10, mean=12.0, SD=-1.0, scale=1-5；The standard deviation is not consistent with this mean and number of observations (fails GRIMMER test).<br>         For details, see ?GRIMMER_test. | 确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。 |
| 中 | 80% | unknown:CI宽度/SE一致性:行2 | summary_suspicious | CI宽度/SE一致性 | 行2 | CI宽度与SE×t临界值不一致（偏差=43.3%） | CI宽度=0.6，2×t(19)×SE=0.418605 | 核对CI的置信水平（通常95%）和SE是否对应。 |
| 中 | 80% | unknown:CI宽度/SE一致性:行4 | summary_suspicious | CI宽度/SE一致性 | 行4 | CI宽度与SE×t临界值不一致（偏差=20.4%） | CI宽度=1.8，2×t(9)×SE=2.26216 | 核对CI的置信水平（通常95%）和SE是否对应。 |
| 低 | 76% | unknown:自由度/样本量关系:行3 | summary_suspicious | 自由度/样本量关系 | 行3 | 自由度df与样本量N的关系不匹配常见检验设计。 | df=5，N=18（N-1=17，N-2=16） | 若检验设计非单样本或两独立样本等组设计，可忽略此项。 |

## 审计置信度摘要

| 方法学置信度 | 发现数 |
|---|---:|
| 高(>=75%) | 17 |
| 中(40%-75%) | 0 |
| 低(<40%) | 0 |

## 专家复核附录

### 1. 高风险：SE/SD/√N一致性（行2）

- 证据ID：unknown:SE/SD/√N一致性:行2
- 位置：summary_suspicious
- 发现：标准误SE与SD/√N不一致（偏差=85.1%）
- 触发证据：SE报告=0.1，SD/√N=0.67082，N=20，SD=3
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对SE是否为标准误（非SD或CI半宽），确认统计脚本输出。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 2. 高风险：百分比/计数一致性（行2）

- 证据ID：unknown:百分比/计数一致性:行2
- 位置：summary_suspicious
- 发现：百分比与count/N反算不一致（差值=15.000）
- 触发证据：报告=25，count/N×100=40，count=8，N=20
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对百分比的分母是否为该行的N；确认count是否正确。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 3. 高风险：p值/t统计量一致性（行2）

- 证据ID：unknown:p值/t统计量一致性:行2
- 位置：summary_suspicious
- 发现：p值与t统计量(df)反算不一致（差值=0.1926）
- 触发证据：报告p=0.2（解析为0.2），t=3，df=19，反算p=0.00736172
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对t、df和p值是否来自同一次分析，是否为单侧检验。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 4. 高风险：SE/SD/√N一致性（行3）

- 证据ID：unknown:SE/SD/√N一致性:行3
- 位置：summary_suspicious
- 发现：标准误SE与SD/√N不一致（偏差=76.4%）
- 触发证据：SE报告=0.1，SD/√N=0.424264，N=18，SD=1.8
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对SE是否为标准误（非SD或CI半宽），确认统计脚本输出。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 5. 高风险：CI区间倒置（行3）

- 证据ID：unknown:CI区间倒置:行3
- 位置：summary_suspicious
- 发现：置信区间下限大于上限。
- 触发证据：CI=[8.2, 7.8]，下限 > 上限
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：CI列顺序可能写反，或表格抽取时发生错列。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 6. 高风险：百分比/计数一致性（行3）

- 证据ID：unknown:百分比/计数一致性:行3
- 位置：summary_suspicious
- 发现：百分比与count/N反算不一致（差值=33.333）
- 触发证据：报告=50，count/N×100=16.6667，count=3，N=18
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对百分比的分母是否为该行的N；确认count是否正确。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 7. 高风险：p值超出定义域（行3）

- 证据ID：unknown:p值超出定义域:行3
- 位置：summary_suspicious
- 发现：p值超出[0, 1]范围。
- 触发证据：报告p值=1.2（p）
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：p值必须介于0到1之间；可能是录入错误或小数点位错。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 8. 高风险：p值/t统计量一致性（行3）

- 证据ID：unknown:p值/t统计量一致性:行3
- 位置：summary_suspicious
- 发现：p值与t统计量(df)反算不一致（差值=1.0682）
- 触发证据：报告p=1.2（解析为1.2），t=1.8，df=5，反算p=0.131758
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对t、df和p值是否来自同一次分析，是否为单侧检验。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 9. 高风险：p值/t统计量一致性（行4）

- 证据ID：unknown:p值/t统计量一致性:行4
- 位置：summary_suspicious
- 发现：p值与t统计量(df)反算不一致（差值=0.3434）
- 触发证据：报告p=0.0（解析为0），t=1，df=9，反算p=0.343436
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：82%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对t、df和p值是否来自同一次分析，是否为单侧检验。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.9(权重15%); 加权总分=0.82

### 10. 高风险：R scrutiny GRIMMER（行4）

- 证据ID：r_scrutiny:R_scrutiny_GRIMMER:行4
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv
- 发现：GRIMMER 检查发现均值、SD 与样本量在离散评分条件下不可同时成立。
- 触发证据：N=10, mean=12.0, SD=-1.0
- 工具：R scrutiny（r_scrutiny）
- 运行时/依赖：r / ready
- 输入类型：
- 置信度/误报风险：85%（high） / medium
- 详细说明：scale=1-5
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括变量不是离散/整数评分、量表范围设定错误、四舍五入规则不同或表格抽取错误。
- 复核动作：确认量表范围、四舍五入精度和变量类型；回看原始计数或统计脚本。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于 R scrutiny 可行性检验、样本量/量表字段可解析性和依赖状态生成；需确认量表范围、四舍五入规则和变量类型。

### 11. 高风险：R rsprite2 SPRITE（行1）

- 证据ID：r_rsprite2:R_rsprite2_SPRITE:行1
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv
- 发现：SPRITE 未能找到匹配报告摘要统计的离散分布。
- 触发证据：N=25, mean=10.0, SD=2.0, scale=1-5；Error in calculating range of possible standard deviations
- 工具：R rsprite2 SPRITE（r_rsprite2）
- 运行时/依赖：r / ready
- 输入类型：
- 置信度/误报风险：85%（high） / high
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括量表范围、均值/SD 小数精度、约束条件或 rsprite2 搜索参数设置不匹配。
- 复核动作：确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于 R rsprite2 SPRITE 搜索结果、输入字段可解析性和依赖状态生成；需确认量表范围、精度和约束条件。

### 12. 高风险：R rsprite2 SPRITE（行2）

- 证据ID：r_rsprite2:R_rsprite2_SPRITE:行2
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv
- 发现：SPRITE 未能找到匹配报告摘要统计的离散分布。
- 触发证据：N=20, mean=5.0, SD=3.0, scale=1-5；Error in calculating range of possible standard deviations
- 工具：R rsprite2 SPRITE（r_rsprite2）
- 运行时/依赖：r / ready
- 输入类型：
- 置信度/误报风险：85%（high） / high
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括量表范围、均值/SD 小数精度、约束条件或 rsprite2 搜索参数设置不匹配。
- 复核动作：确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于 R rsprite2 SPRITE 搜索结果、输入字段可解析性和依赖状态生成；需确认量表范围、精度和约束条件。

### 13. 高风险：R rsprite2 SPRITE（行3）

- 证据ID：r_rsprite2:R_rsprite2_SPRITE:行3
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv
- 发现：SPRITE 未能找到匹配报告摘要统计的离散分布。
- 触发证据：N=18, mean=8.0, SD=1.8, scale=1-5；Error in calculating range of possible standard deviations
- 工具：R rsprite2 SPRITE（r_rsprite2）
- 运行时/依赖：r / ready
- 输入类型：
- 置信度/误报风险：85%（high） / high
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括量表范围、均值/SD 小数精度、约束条件或 rsprite2 搜索参数设置不匹配。
- 复核动作：确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于 R rsprite2 SPRITE 搜索结果、输入字段可解析性和依赖状态生成；需确认量表范围、精度和约束条件。

### 14. 高风险：R rsprite2 SPRITE（行4）

- 证据ID：r_rsprite2:R_rsprite2_SPRITE:行4
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/summary_suspicious.csv
- 发现：SPRITE 未能找到匹配报告摘要统计的离散分布。
- 触发证据：N=10, mean=12.0, SD=-1.0, scale=1-5；The standard deviation is not consistent with this mean and number of observations (fails GRIMMER test).
         For details, see ?GRIMMER_test.
- 工具：R rsprite2 SPRITE（r_rsprite2）
- 运行时/依赖：r / ready
- 输入类型：
- 置信度/误报风险：85%（high） / high
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括量表范围、均值/SD 小数精度、约束条件或 rsprite2 搜索参数设置不匹配。
- 复核动作：确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于 R rsprite2 SPRITE 搜索结果、输入字段可解析性和依赖状态生成；需确认量表范围、精度和约束条件。

### 15. 中风险：CI宽度/SE一致性（行2）

- 证据ID：unknown:CI宽度/SE一致性:行2
- 位置：summary_suspicious
- 发现：CI宽度与SE×t临界值不一致（偏差=43.3%）
- 触发证据：CI宽度=0.6，2×t(19)×SE=0.418605
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：80%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对CI的置信水平（通常95%）和SE是否对应。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.7(权重15%); 加权总分=0.79

### 16. 中风险：CI宽度/SE一致性（行4）

- 证据ID：unknown:CI宽度/SE一致性:行4
- 位置：summary_suspicious
- 发现：CI宽度与SE×t临界值不一致（偏差=20.4%）
- 触发证据：CI宽度=1.8，2×t(9)×SE=2.26216
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：80%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对CI的置信水平（通常95%）和SE是否对应。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.7(权重15%); 加权总分=0.79

### 17. 低风险：自由度/样本量关系（行3）

- 证据ID：unknown:自由度/样本量关系:行3
- 位置：summary_suspicious
- 发现：自由度df与样本量N的关系不匹配常见检验设计。
- 触发证据：df=5，N=18（N-1=17，N-2=16）
- 工具：交叉验证（crosscheck）
- 运行时/依赖：python / ready
- 输入类型：summary_statistics_table
- 置信度/误报风险：76%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：若检验设计非单样本或两独立样本等组设计，可忽略此项。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：公式确定性=1(权重45%), 表规模=0.6(权重25%), 可解析字段=0.6(权重15%), 偏差等级=0.5(权重15%); 加权总分=0.76

## 人工复核任务表

| 序号 | 复核任务 | 涉及证据数 |
|---:|---|---:|
| 1 | 核对SE是否为标准误（非SD或CI半宽），确认统计脚本输出。 | 2 |
| 2 | 核对百分比的分母是否为该行的N；确认count是否正确。 | 2 |
| 3 | 核对t、df和p值是否来自同一次分析，是否为单侧检验。 | 3 |
| 4 | CI列顺序可能写反，或表格抽取时发生错列。 | 1 |
| 5 | p值必须介于0到1之间；可能是录入错误或小数点位错。 | 1 |
| 6 | 确认量表范围、四舍五入精度和变量类型；回看原始计数或统计脚本。 | 1 |
| 7 | 确认量表范围、均值/SD 小数精度、样本量和是否为离散评分摘要；高风险结果应由人工复核原始频数。 | 4 |
| 8 | 核对CI的置信水平（通常95%）和SE是否对应。 | 2 |
| 9 | 若检验设计非单样本或两独立样本等组设计，可忽略此项。 | 1 |

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| crosscheck | 12 |
| r_rsprite2 | 5 |
| r_scrutiny | 2 |

- `r_scrutiny`：R scrutiny 已运行。（GRIMMER候选行=4；DEBIT候选行=0；依赖状态=ready；输入类型=）
- `r_rsprite2`：R rsprite2 SPRITE 已运行。（尝试行数=4；依赖状态=ready；输入类型=）

