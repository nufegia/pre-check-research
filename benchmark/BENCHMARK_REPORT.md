# PCR Benchmark 总报告

## 总体结论

本轮 benchmark 共运行 13 个测评用例，PASS 13 个，FAIL 0 个。整体通过。

- Benchmark 根目录：`benchmark`
- 联网测评：未执行（本次使用 --no-network）。
- 风险信号总数：66
- 运行/覆盖提示总数：47

结论：当前工程的核心检测链路可以被自动化 benchmark 稳定覆盖。确定性数学类、哈希溯源类和项目级对账类检查可作为较可靠的工程回归指标；图像、raw 表格中的数字分布/列间关系弱信号、论文工厂/跨稿件相似等能力适合衡量“是否能提出复核线索”，不能作为强结论指标。

## 覆盖结论

- 原始数据：覆盖重复/高度重复行列、固定步长、高频值、缺失分组集中、尾数分布、列间关系和非连续变量异常；干净对照保持 0 个风险信号。
- 摘要统计：覆盖 SE/SD/N、CI、百分比/计数、p/t/df、p 值定义域，以及 R scrutiny/SPRITE 可行性检查。
- 正文统计：覆盖 R statcheck 对 APA/NHST 表达式的 p 值一致性检查。
- 文献与联网：覆盖 DOI/PMID 解析、Crossref/OpenAlex/NCBI 元数据查询、引用主张抽取。
- 图像：覆盖图片发现、内部重复图、局部 copy-move、元数据质量、Western blot/凝胶复核清单。
- 代码与项目：覆盖 Python/R 脚本复跑、Stata/SPSS/SAS 只读提示、跨材料数据对账、项目 manifest、provenance 版本链和本地 corpus 筛查。

## 可靠性分层

| 层级 | 工具/能力 | Benchmark 判读 |
|---|---|---|
| 较可靠 | `crosscheck`, `p_value_distribution`, `data_trace_crosscheck`, `provenance_hash`, `provenance_chain_verify` | 数学、定义域或哈希规则明确，适合作为回归门槛。 |
| 中等可靠 | `raw_data_rules`, `r_statcheck`, `r_scrutiny`, `r_rsprite2`, `code_rerun_execute` | 对输入格式、列名、R 包版本、脚本依赖较敏感；适合作为覆盖和主要异常捕获指标。 |
| 弱信号 | `raw_data_rules` 中的数字分布/列间关系/非连续变量形态信号、图像重复/copy-move, `papermill_light_signals`, `papermill_network_signals` | 只能说明产生了人工复核线索，误报/漏报风险较高。 |

## 联网模块测试结论

未执行（本次使用 --no-network）。

## 用例矩阵

| 用例 | 类型 | 通过 | 秒 | 风险信号 | 提示 | 缺失工具 | 缺失检查 |
|---|---:|---:|---:|---:|---:|---|---|
| raw_suspicious | single_run | 是 | 3.71 | 16 | 0 |  |  |
| raw_clean_control | single_run | 是 | 1.175 | 0 | 0 |  |  |
| summary_suspicious | single_run | 是 | 2.499 | 17 | 2 |  |  |
| p_values_suspicious | single_run | 是 | 1.063 | 2 | 0 |  |  |
| apa_stats_suspicious | single_run | 是 | 2.228 | 2 | 0 |  |  |
| paper_refs_and_claims_offline | single_run | 是 | 1.095 | 0 | 4 |  |  |
| analysis_suspicious | single_run | 是 | 1.488 | 1 | 1 |  |  |
| analysis_manual_unsupported | single_run | 是 | 1.058 | 0 | 3 |  |  |
| figures_project | project | 是 | 2.909 | 11 | 13 |  |  |
| project_full | project | 是 | 2.694 | 12 | 19 |  |  |
| corpus_screen | corpus | 是 | 2.12 | 4 | 0 |  |  |
| provenance_change | provenance_change | 是 | 2.111 | 1 | 5 |  |  |
| external_refs_online | project_network | 是 | 0.0 | 0 | 0 |  |  |

## 工具覆盖

- `citation_claim_check`：2 个用例
- `code_rerun_audit`：4 个用例
- `code_rerun_execute`：4 个用例
- `crosscheck`：2 个用例
- `data_trace_crosscheck`：2 个用例
- `image_copy_move_internal`：2 个用例
- `image_duplicate_internal`：2 个用例
- `image_extract`：2 个用例
- `image_metadata_audit`：2 个用例
- `p_value_distribution`：1 个用例
- `papermill_light_signals`：2 个用例
- `papermill_network_signals`：3 个用例
- `project_audit`：1 个用例
- `provenance_chain_verify`：3 个用例
- `provenance_hash`：2 个用例
- `r_rsprite2`：1 个用例
- `r_scrutiny`：2 个用例
- `r_statcheck`：1 个用例
- `raw_data_rules`：1 个用例
- `reference_audit`：2 个用例
- `western_blot_review_list`：2 个用例

## 运行记录

- `raw_suspicious`: 合并报告已生成：benchmark/reports/pcr.raw_suspicious.md
- `raw_clean_control`: 合并报告已生成：benchmark/reports/pcr.raw_clean_control.md
- `summary_suspicious`: 合并报告已生成：benchmark/reports/pcr.summary_suspicious.md
- `p_values_suspicious`: 合并报告已生成：benchmark/reports/pcr.p_values_suspicious.md
- `apa_stats_suspicious`: 合并报告已生成：benchmark/reports/pcr.apa_stats_suspicious.md
- `paper_refs_and_claims_offline`: 合并报告已生成：benchmark/reports/pcr.paper_refs_and_claims_offline.md
- `analysis_suspicious`: 合并报告已生成：benchmark/reports/pcr.analysis_suspicious.md
- `analysis_manual_unsupported`: 合并报告已生成：benchmark/reports/pcr.analysis_manual_unsupported.md
- `figures_project`: 项目审计报告已生成：benchmark/reports/pcr.figures_project.md
- `project_full`: 项目审计报告已生成：benchmark/reports/pcr.project_full.md
- `corpus_screen`: 本地语料索引已生成：benchmark/reports/pcr.corpus_index.json | 本地语料筛查报告已生成：benchmark/reports/pcr.corpus_screen.md
- `provenance_change`: } | }
- `external_refs_online`: network case skipped by --no-network

## 判读边界

本报告中的 high/medium/low 是 benchmark 风险信号，不是学术不端、造假或舞弊结论。`info` 是运行状态、依赖状态、跳过原因或覆盖提示，不计入风险结论。
联网用例依赖 Crossref、OpenAlex、NCBI 的实时可用性、证书链和限流状态。若联网用例失败，应先查看 evidence 中的 HTTP/SSL/限流信息，再判断是否为检测器回归。
所有弱信号类工具只用于提示人工复核方向。最终复核应回到原始数据、脚本、图像原文件、文献元数据和审计日志。
