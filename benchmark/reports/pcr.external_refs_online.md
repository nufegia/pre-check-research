# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`project_external`
- 总体风险：中
- 检测对象：10 组
- 风险信号：高 0 / 中 3 / 低 1
- 运行提示：12 条

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
| paper.md | manuscript |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external/paper.md |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | citation_claim_check | code_rerun_audit | code_rerun_execute | data_trace_crosscheck | image_extract | papermill_light_signals | papermill_network_signals | provenance_chain_verify | provenance_hash | reference_audit |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|
| provenance_hash | 1 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| provenance_chain_verify | 1 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低1 | 高0 中0 低0 | 高0 中0 低0 |
| code_rerun_audit | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| code_rerun_execute | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| data_trace_crosscheck | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| papermill_network_signals | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| reference_audit | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中3 低0 |
| citation_claim_check | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| papermill_light_signals | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_extract | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| provenance_hash | 原始文件哈希存证 | provenance_hash | recorded | ready | python | raw_file_bundle | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| provenance_chain_verify | 哈希版本链核验 | provenance_chain_verify | recorded | ready | python | raw_file_bundle | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| code_rerun_audit | 分析代码复跑审计 | code_rerun_audit | recorded | insufficient_material | python | analysis_code | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| code_rerun_execute | 分析脚本沙箱复跑 | code_rerun_execute | recorded | ready | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| data_trace_crosscheck | 跨材料数据对账 | data_trace_crosscheck | recorded | ready | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| papermill_network_signals | 本地论文工厂跨库信号 | papermill_network_signals | recorded | insufficient_material | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| reference_audit | 参考文献核验 | reference_audit | recorded | ready | python | reference_list | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| citation_claim_check | 引用支持关系辅助复核 | citation_claim_check | recorded | insufficient_material | python | reference_list | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| papermill_light_signals | 论文工厂轻量信号 | papermill_light_signals | recorded | ready | python | plain_text | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| image_extract | 图像抽取 | image_extract | recorded | insufficient_material | python | scientific_figure | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |

## 覆盖缺口与未运行原因

| 工具 | 材料/模块 | 状态 | 依赖状态 | 原因 | 对预审的影响 |
|---|---|---|---|---|---|
| provenance_hash | provenance_hash | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| provenance_chain_verify | provenance_chain_verify | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| code_rerun_audit | code_rerun_audit | recorded | insufficient_material | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| code_rerun_execute | code_rerun_execute | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| data_trace_crosscheck | data_trace_crosscheck | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| papermill_network_signals | papermill_network_signals | recorded | insufficient_material | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| reference_audit | reference_audit | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| citation_claim_check | citation_claim_check | recorded | insufficient_material | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| papermill_light_signals | papermill_light_signals | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| image_extract | image_extract | recorded | insufficient_material | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |

## 风险发现清单（问题清单）

| 风险 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |
|---|---|---|---|---|---|---|---|
| 中 | reference_audit:DOI题名不匹配:10.1038/495426a | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external/paper.md | DOI题名不匹配 | 10.1038/495426a | 稿件参考文献行与 Crossref 返回题名明显不一致。 | overlap=0.00; reported_line=Van Noorden R. A randomized oncology survival trial with unrelated endpoints. Nature. 2013. doi:10.1038/495426a. PMID:23538808; crossref_title=Open access: The true cost of science publishing | 人工核对 DOI 是否贴错、参考文献题名是否误填，或排版/抽取是否错行。 |
| 中 | reference_audit:DOI外部元数据不可核验:10.9999/pcr-benchmark-missing-doi | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external/paper.md | DOI外部元数据不可核验 | 10.9999/pcr-benchmark-missing-doi | 该 DOI 在外部元数据服务中未能获得有效记录。 | crossref cache_miss status=error summary=HTTP Error 404: Not Found; openalex cache_miss status=error summary=HTTP Error 404: Not Found | 核对 DOI 是否拼写错误、是否为未注册标识符，或外部服务是否临时不可用。 |
| 中 | reference_audit:PMID题名不匹配:23538808 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external/paper.md | PMID题名不匹配 | 23538808 | 稿件参考文献行与 NCBI 返回题名明显不一致。 | overlap=0.00; reported_line=Van Noorden R. A randomized oncology survival trial with unrelated endpoints. Nature. 2013. doi:10.1038/495426a. PMID:23538808; ncbi_title=Open access: The true cost of science publishing. | 人工核对 PMID 是否贴错、参考文献题名是否误填，或排版/抽取是否错行。 |
| 低 | provenance_chain_verify:哈希版本链核验:paper.md | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external | 哈希版本链核验 | paper.md | 哈希版本链状态：new | {"relative_path": "paper.md", "sha256": "ccbd79ca365cbc8eb9e3b0b5b430e5fa5f5466c55770616faa5b7a161f6023b9", "size": 408, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |

## 专家复核附录

### 1. 中风险：DOI题名不匹配（10.1038/495426a）

- 证据ID：reference_audit:DOI题名不匹配:10.1038/495426a
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external/paper.md
- 发现：稿件参考文献行与 Crossref 返回题名明显不一致。
- 触发证据：overlap=0.00; reported_line=Van Noorden R. A randomized oncology survival trial with unrelated endpoints. Nature. 2013. doi:10.1038/495426a. PMID:23538808; crossref_title=Open access: The true cost of science publishing
- 工具：参考文献核验（reference_audit）
- 运行时/依赖：python / ready
- 输入类型：reference_list
- 置信度/误报风险：medium / medium
- 外部记录：crossref cache_miss status=ok summary=Open access: The true cost of science publishing; Crossref status=ok, title=Open access: The true cost of science publishing; openalex cache_miss status=ok summary=id=https://openalex.org/W2441943932; retracted=False; OpenAlex id=https://openalex.org/W2441943932, retracted=False
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：人工核对 DOI 是否贴错、参考文献题名是否误填，或排版/抽取是否错行。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 2. 中风险：DOI外部元数据不可核验（10.9999/pcr-benchmark-missing-doi）

- 证据ID：reference_audit:DOI外部元数据不可核验:10.9999/pcr-benchmark-missing-doi
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external/paper.md
- 发现：该 DOI 在外部元数据服务中未能获得有效记录。
- 触发证据：crossref cache_miss status=error summary=HTTP Error 404: Not Found; openalex cache_miss status=error summary=HTTP Error 404: Not Found
- 工具：参考文献核验（reference_audit）
- 运行时/依赖：python / ready
- 输入类型：reference_list
- 置信度/误报风险：medium / medium
- 外部记录：crossref cache_miss status=error summary=HTTP Error 404: Not Found; openalex cache_miss status=error summary=HTTP Error 404: Not Found
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对 DOI 是否拼写错误、是否为未注册标识符，或外部服务是否临时不可用。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 3. 中风险：PMID题名不匹配（23538808）

- 证据ID：reference_audit:PMID题名不匹配:23538808
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external/paper.md
- 发现：稿件参考文献行与 NCBI 返回题名明显不一致。
- 触发证据：overlap=0.00; reported_line=Van Noorden R. A randomized oncology survival trial with unrelated endpoints. Nature. 2013. doi:10.1038/495426a. PMID:23538808; ncbi_title=Open access: The true cost of science publishing.
- 工具：参考文献核验（reference_audit）
- 运行时/依赖：python / ready
- 输入类型：reference_list
- 置信度/误报风险：medium / medium
- 外部记录：{"uid": "23538808", "pubdate": "2013 Mar 28", "epubdate": "", "source": "Nature", "authors": [{"name": "Van Noorden R", "authtype": "Author", "clusterid": ""}], "lastauthor": "Van Noorden R", "title": "Open access: The true cost of science publishing.", "sorttitle": "open access the true cost of science publishing", "volume": "495", "issue": "7442", "pages": "426-9", "lang": ["eng"], "nlmuniqueid": "0410462", "issn": "0028-0836", "essn": "1476-4687", "pubtype": ["News"], "recordstatus": "PubMed 
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：人工核对 PMID 是否贴错、参考文献题名是否误填，或排版/抽取是否错行。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 4. 低风险：哈希版本链核验（paper.md）

- 证据ID：provenance_chain_verify:哈希版本链核验:paper.md
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_external
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "paper.md", "sha256": "ccbd79ca365cbc8eb9e3b0b5b430e5fa5f5466c55770616faa5b7a161f6023b9", "size": 408, "status": "new"}
- 工具：哈希版本链核验（provenance_chain_verify）
- 运行时/依赖：python / ready
- 输入类型：raw_file_bundle
- 置信度/误报风险：medium / medium
- 计算/抽取过程：读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。

## 人工复核任务表

| 序号 | 复核任务 | 涉及证据数 |
|---:|---|---:|
| 1 | 人工核对 DOI 是否贴错、参考文献题名是否误填，或排版/抽取是否错行。 | 1 |
| 2 | 核对 DOI 是否拼写错误、是否为未注册标识符，或外部服务是否临时不可用。 | 1 |
| 3 | 人工核对 PMID 是否贴错、参考文献题名是否误填，或排版/抽取是否错行。 | 1 |
| 4 | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 | 1 |

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| citation_claim_check | 1 |
| code_rerun_audit | 1 |
| code_rerun_execute | 1 |
| data_trace_crosscheck | 1 |
| image_extract | 1 |
| papermill_light_signals | 1 |
| papermill_network_signals | 1 |
| provenance_chain_verify | 1 |
| provenance_hash | 1 |
| reference_audit | 7 |

- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=ccbd79ca365cbc8eb9e3b0b5b430e5fa5f5466c55770616faa5b7a161f6023b9; size=408; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `code_rerun_audit`：未发现可扫描的分析代码，或未命中内置复跑风险规则。（代码文件数=0；依赖状态=insufficient_material；输入类型=analysis_code）
- `code_rerun_execute`：用户关闭了脚本沙箱复跑。（rerun_code=false；依赖状态=ready；输入类型=project_manifest）
- `data_trace_crosscheck`：未获得足够的原始数据统计量或文档摘要统计表，跨材料对账未运行。（raw_stats=0; summary_values=0；依赖状态=ready；输入类型=project_manifest）
- `papermill_network_signals`：未提供本地 corpus 索引，跨稿件论文工厂信号未运行。（使用 pcr-audit corpus build 生成 corpus-index.json 后再执行 screen。；依赖状态=insufficient_material；输入类型=project_manifest）
- `reference_audit`：已解析出可核验的参考文献标识符。（DOI=2，PMID=1，候选参考文献行=2；依赖状态=ready；输入类型=reference_list）
- `reference_audit`：已尝试查询 DOI 外部元数据。（crossref cache_miss status=ok summary=Open access: The true cost of science publishing; Crossref status=ok, title=Open access: The true cost of science publishing; openalex cache_miss status=ok summary=id=https://openalex.org/W2441943932; retracted=False; OpenAlex id=https://openalex.org/W2441943932, retracted=False；依赖状态=ready；输入类型=reference_list）
- `reference_audit`：已尝试查询 DOI 外部元数据。（crossref cache_miss status=error summary=HTTP Error 404: Not Found; openalex cache_miss status=error summary=HTTP Error 404: Not Found；依赖状态=ready；输入类型=reference_list）
- `reference_audit`：已尝试查询 PMID 外部元数据。（ncbi cache_miss status=ok summary=Open access: The true cost of science publishing.；依赖状态=ready；输入类型=reference_list）
- `citation_claim_check`：未抽取到可自动复核的带引用主张。（当前轻量规则识别数字方括号引用或作者-年份引用。；依赖状态=insufficient_material；输入类型=reference_list）
- `papermill_light_signals`：轻量短语扫描完成，未发现内置异常短语。（扫描字符数=408，规则数=7；依赖状态=ready；输入类型=plain_text）
- `image_extract`：未发现可直接检测的图片文件。（PDF 图像抽取为 best-effort；DOCX 可抽取 word/media 下图片。；依赖状态=insufficient_material；输入类型=scientific_figure）

