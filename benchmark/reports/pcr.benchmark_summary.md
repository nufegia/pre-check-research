# PCR Benchmark 总报告

## 总体结论

本轮 benchmark 共运行 13 个测评用例，PASS 13 个，FAIL 0 个。整体通过。

- Benchmark 根目录：`/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark`
- 联网测评：已执行。有效 DOI/PMID 的 Crossref/OpenAlex/NCBI 查询返回 status=ok；故意构造的错误 DOI 返回 404，并被检测为“外部元数据不可核验”。
- 风险信号总数：68
- 运行/覆盖提示总数：60

结论：当前工程的核心检测链路可以被自动化 benchmark 稳定覆盖。确定性数学类、哈希溯源类和项目级对账类检查可作为较可靠的工程回归指标；图像、数字分布、论文工厂/跨稿件相似等弱信号工具适合衡量“是否能提出复核线索”，不能作为强结论指标。

## 覆盖结论

- 原始数据：覆盖重复行/列、固定步长、高频值、缺失分组集中、尾数分布；干净对照保持 0 个风险信号。
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
| 弱信号 | `digit_distribution`, 图像重复/copy-move, `papermill_light_signals`, `papermill_network_signals` | 只能说明产生了人工复核线索，误报/漏报风险较高。 |

## 联网模块测试结论

已执行。有效 DOI/PMID 的 Crossref/OpenAlex/NCBI 查询返回 status=ok；故意构造的错误 DOI 返回 404，并被检测为“外部元数据不可核验”。

- 参考文献标识符解析：DOI/PMID；DOI=2，PMID=1，候选参考文献行=2
- DOI题名不匹配：10.1038/495426a；overlap=0.00; reported_line=Van Noorden R. A randomized oncology survival trial with unrelated endpoints. Nature. 2013. doi:10.1038/495426a. PMID:23538808; crossref_title=Open access: The true cost of science publishing
- DOI元数据核验：10.1038/495426a；crossref cache_miss status=ok summary=Open access: The true cost of science publishing; Crossref status=ok, title=Open access: The true cost of science publishing; openalex cache_miss status=ok summary=id=https://openalex.org/W2441943932; retracted=False; OpenAlex id=https://openalex.org/W2441943932, retracted=False
- DOI外部元数据不可核验：10.9999/pcr-benchmark-missing-doi；crossref cache_miss status=error summary=HTTP Error 404: Not Found; openalex cache_miss status=error summary=HTTP Error 404: Not Found
- DOI元数据核验：10.9999/pcr-benchmark-missing-doi；crossref cache_miss status=error summary=HTTP Error 404: Not Found; openalex cache_miss status=error summary=HTTP Error 404: Not Found
- PMID题名不匹配：23538808；overlap=0.00; reported_line=Van Noorden R. A randomized oncology survival trial with unrelated endpoints. Nature. 2013. doi:10.1038/495426a. PMID:23538808; ncbi_title=Open access: The true cost of science publishing.
- PMID元数据核验：23538808；ncbi cache_miss status=ok summary=Open access: The true cost of science publishing.

## 用例矩阵

| 用例 | 类型 | 通过 | 秒 | 风险信号 | 提示 | 缺失工具 | 缺失检查 |
|---|---:|---:|---:|---:|---:|---|---|
| raw_suspicious | single_run | 是 | 1.17 | 14 | 0 |  |  |
| raw_clean_control | single_run | 是 | 1.064 | 0 | 0 |  |  |
| summary_suspicious | single_run | 是 | 2.403 | 17 | 2 |  |  |
| p_values_suspicious | single_run | 是 | 1.143 | 2 | 0 |  |  |
| apa_stats_suspicious | single_run | 是 | 1.579 | 2 | 0 |  |  |
| paper_refs_and_claims_offline | single_run | 是 | 1.057 | 0 | 4 |  |  |
| analysis_suspicious | single_run | 是 | 1.41 | 1 | 1 |  |  |
| analysis_manual_unsupported | single_run | 是 | 1.039 | 0 | 3 |  |  |
| figures_project | project | 是 | 1.192 | 11 | 13 |  |  |
| project_full | project | 是 | 2.504 | 12 | 20 |  |  |
| corpus_screen | corpus | 是 | 0.892 | 4 | 0 |  |  |
| provenance_change | provenance_change | 是 | 0.757 | 1 | 5 |  |  |
| external_refs_online | project_network | 是 | 5.795 | 4 | 12 |  |  |

## 工具覆盖

- `citation_claim_check`：3 个用例
- `code_rerun_audit`：5 个用例
- `code_rerun_execute`：5 个用例
- `crosscheck`：2 个用例
- `data_trace_crosscheck`：3 个用例
- `digit_distribution`：2 个用例
- `image_copy_move_internal`：2 个用例
- `image_duplicate_internal`：2 个用例
- `image_extract`：3 个用例
- `image_metadata_audit`：2 个用例
- `p_value_distribution`：1 个用例
- `papermill_light_signals`：3 个用例
- `papermill_network_signals`：4 个用例
- `project_audit`：1 个用例
- `provenance_chain_verify`：4 个用例
- `provenance_hash`：3 个用例
- `r_rsprite2`：1 个用例
- `r_scrutiny`：2 个用例
- `r_statcheck`：1 个用例
- `raw_data_rules`：1 个用例
- `reference_audit`：3 个用例
- `western_blot_review_list`：2 个用例

## 运行记录

- `raw_suspicious`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.raw_suspicious.md
- `raw_clean_control`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.raw_clean_control.md
- `summary_suspicious`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.summary_suspicious.md
- `p_values_suspicious`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.p_values_suspicious.md
- `apa_stats_suspicious`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.apa_stats_suspicious.md
- `paper_refs_and_claims_offline`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.paper_refs_and_claims_offline.md
- `analysis_suspicious`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.analysis_suspicious.md
- `analysis_manual_unsupported`: 合并报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.analysis_manual_unsupported.md
- `figures_project`: 项目审计报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.figures_project.md
- `project_full`: 项目审计报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.project_full.md
- `corpus_screen`: 本地语料索引已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.corpus_index.json | 本地语料筛查报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.corpus_screen.md
- `provenance_change`: } | }
- `external_refs_online`: 项目审计报告已生成：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.external_refs_online.md

## 判读边界

本报告中的 high/medium/low 是 benchmark 风险信号，不是学术不端、造假或舞弊结论。`info` 是运行状态、依赖状态、跳过原因或覆盖提示，不计入风险结论。
联网用例依赖 Crossref、OpenAlex、NCBI 的实时可用性、证书链和限流状态。若联网用例失败，应先查看 evidence 中的 HTTP/SSL/限流信息，再判断是否为检测器回归。
所有弱信号类工具只用于提示人工复核方向。最终复核应回到原始数据、脚本、图像原文件、文献元数据和审计日志。
