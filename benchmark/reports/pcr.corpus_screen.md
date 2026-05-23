# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`project_full`
- 总体风险：中
- 检测对象：1 组
- 风险信号：高 0 / 中 2 / 低 2
- 运行提示：0 条

> 本报告只识别数据、统计、图像、文献和流程材料中的风险信号，不构成数据风险校验结论。高风险项表示需要优先回看原始记录、实验日志、原始图或统计脚本。

## 解析说明

- 本报告基于本地 corpus-index.json 进行跨稿件弱信号筛查。

## 预审范围与判读口径

- 本报告为自动化预审底稿，只记录可复算的风险信号、运行状态和覆盖缺口。
- 风险等级仅表示人工复核优先级，不构成数据风险校验结论。
- `info` 记录为工具运行、依赖、材料不足或路由状态，不计入风险信号。
- 未运行或不适用的工具表示本次材料/依赖/路由条件不足，不表示相应风险不存在。

## 材料清单

| 材料 | 角色/来源 | 行数 | 列数 | 输入类型/分类 | 状态 | 路径 |
|---|---|---:|---:|---|---|---|
| papermill_network_signals | result | 2 | 0 |  | reported |  |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | papermill_network_signals |
|---|---:|---:|---|
| papermill_network_signals | 2 | 0 | 高0 中2 低2 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| papermill_network_signals | 本地论文工厂跨库信号 | papermill_network_signals | recorded | ready | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |

## 覆盖缺口与未运行原因

| 工具 | 材料/模块 | 状态 | 依赖状态 | 原因 | 对预审的影响 |
|---|---|---|---|---|---|
| papermill_network_signals | papermill_network_signals | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |

## 风险发现清单（问题清单）

| 风险 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |
|---|---|---|---|---|---|---|---|
| 中 | papermill_network_signals:跨稿件文本高度相似:project_a | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 跨稿件文本高度相似 | project_a | 当前项目与本地语料中的另一稿件存在较高文本模板相似性。 | jaccard=1.000; simhash_distance=0; other=/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/corpus/project_a | 人工比较摘要/方法/结果段，确认是否为合理系列研究、模板写作或异常复用。 |
| 中 | papermill_network_signals:跨稿件文本高度相似:project_b | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 跨稿件文本高度相似 | project_b | 当前项目与本地语料中的另一稿件存在较高文本模板相似性。 | jaccard=1.000; simhash_distance=0; other=/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/corpus/project_b | 人工比较摘要/方法/结果段，确认是否为合理系列研究、模板写作或异常复用。 |
| 低 | papermill_network_signals:作者/邮箱域网络重叠:project_a | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 作者/邮箱域网络重叠 | project_a | 本地语料中存在作者或邮箱域重叠，需结合机构和投稿背景复核。 | author_overlap=alice zhang, bob li; email_domain_overlap= | 确认是否为同一团队系列研究、通讯作者邮箱习惯或异常批量投稿线索。 |
| 低 | papermill_network_signals:作者/邮箱域网络重叠:project_b | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 作者/邮箱域网络重叠 | project_b | 本地语料中存在作者或邮箱域重叠，需结合机构和投稿背景复核。 | author_overlap=alice zhang, bob li; email_domain_overlap= | 确认是否为同一团队系列研究、通讯作者邮箱习惯或异常批量投稿线索。 |

## 专家复核附录

### 1. 中风险：跨稿件文本高度相似（project_a）

- 证据ID：papermill_network_signals:跨稿件文本高度相似:project_a
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：当前项目与本地语料中的另一稿件存在较高文本模板相似性。
- 触发证据：jaccard=1.000; simhash_distance=0; other=/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/corpus/project_a
- 工具：本地论文工厂跨库信号（papermill_network_signals）
- 运行时/依赖：python / ready
- 输入类型：project_manifest
- 置信度/误报风险：medium / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：人工比较摘要/方法/结果段，确认是否为合理系列研究、模板写作或异常复用。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 2. 中风险：跨稿件文本高度相似（project_b）

- 证据ID：papermill_network_signals:跨稿件文本高度相似:project_b
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：当前项目与本地语料中的另一稿件存在较高文本模板相似性。
- 触发证据：jaccard=1.000; simhash_distance=0; other=/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/corpus/project_b
- 工具：本地论文工厂跨库信号（papermill_network_signals）
- 运行时/依赖：python / ready
- 输入类型：project_manifest
- 置信度/误报风险：medium / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：人工比较摘要/方法/结果段，确认是否为合理系列研究、模板写作或异常复用。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 3. 低风险：作者/邮箱域网络重叠（project_a）

- 证据ID：papermill_network_signals:作者/邮箱域网络重叠:project_a
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：本地语料中存在作者或邮箱域重叠，需结合机构和投稿背景复核。
- 触发证据：author_overlap=alice zhang, bob li; email_domain_overlap=
- 工具：本地论文工厂跨库信号（papermill_network_signals）
- 运行时/依赖：python / ready
- 输入类型：project_manifest
- 置信度/误报风险：medium / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：确认是否为同一团队系列研究、通讯作者邮箱习惯或异常批量投稿线索。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 4. 低风险：作者/邮箱域网络重叠（project_b）

- 证据ID：papermill_network_signals:作者/邮箱域网络重叠:project_b
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：本地语料中存在作者或邮箱域重叠，需结合机构和投稿背景复核。
- 触发证据：author_overlap=alice zhang, bob li; email_domain_overlap=
- 工具：本地论文工厂跨库信号（papermill_network_signals）
- 运行时/依赖：python / ready
- 输入类型：project_manifest
- 置信度/误报风险：medium / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：确认是否为同一团队系列研究、通讯作者邮箱习惯或异常批量投稿线索。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

## 人工复核任务表

| 序号 | 复核任务 | 涉及证据数 |
|---:|---|---:|
| 1 | 人工比较摘要/方法/结果段，确认是否为合理系列研究、模板写作或异常复用。 | 2 |
| 2 | 确认是否为同一团队系列研究、通讯作者邮箱习惯或异常批量投稿线索。 | 2 |

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| papermill_network_signals | 4 |

无运行提示。

