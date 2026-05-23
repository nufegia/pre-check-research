# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`merged-findings.json`
- 总体风险：低
- 检测对象：3 组
- 风险信号：高 0 / 中 0 / 低 0
- 运行提示：4 条

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
| paper_refs_and_claims.md | table |  |  | reference_list | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/paper_refs_and_claims.md |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | citation_claim_check | papermill_light_signals | reference_audit |
|---|---:|---:|---|---|---|
| reference_audit | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| citation_claim_check | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/paper_refs_and_claims.md | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| reference_audit | 参考文献核验 | paper_refs_and_claims.md | ready | ready | python | reference_list | 确定性路由判定该工具适用于当前材料。 | 默认不向外部 API 发送材料；外部元数据可能不完整，撤稿与争议信号需人工确认。 |
| citation_claim_check | 引用支持关系辅助复核 | paper_refs_and_claims.md | ready | ready | python | reference_list | 确定性路由判定该工具适用于当前材料。 | 轻量抽取不判断引用是否真正支持主张；必须保留证据片段并人工确认。 |
| papermill_light_signals | 论文工厂轻量信号 | paper_refs_and_claims.md | not_applicable | not_applicable | python |  | 当前数据类型不属于该工具包的适用范围。 | 轻量文本信号不能替代跨论文数据库、投稿行为和作者网络审查。 |

## 覆盖缺口与未运行原因

| 工具 | 材料/模块 | 状态 | 依赖状态 | 原因 | 对预审的影响 |
|---|---|---|---|---|---|
| papermill_light_signals | paper_refs_and_claims.md | not_applicable | not_applicable | 当前数据类型不属于该工具包的适用范围。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |

## 风险发现清单（问题清单）

未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。

## 专家复核附录

本次没有可展开的风险发现。

## 人工复核任务表

本次没有由风险发现聚合出的人工复核任务。

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| citation_claim_check | 1 |
| papermill_light_signals | 1 |
| reference_audit | 2 |

- `reference_audit`：已解析出可核验的参考文献标识符。（DOI=2，PMID=0，候选参考文献行=2；依赖状态=ready；输入类型=reference_list）
- `reference_audit`：默认本地/私有化运行未向外部API发送稿件或参考文献信息。（使用 --external-lookups 或设置 PCR_ENABLE_EXTERNAL_LOOKUPS=1 后才会查询 Crossref、OpenAlex 和 NCBI E-utilities。；依赖状态=external_lookup_disabled；输入类型=reference_list）
- `citation_claim_check`：已抽取带引用主张，供人工或RAG流程复核。（候选主张=2；样例：This retrospective study used a standardized method and identical inclusion criteria [1]；The outcome was assessed with the same imaging workflow and statistical model [2]；依赖状态=ready；输入类型=reference_list）
- `papermill_light_signals`：论文工厂轻量信号 未运行：not_applicable（当前数据类型不属于该工具包的适用范围。；依赖状态=not_applicable；输入类型=unknown）

