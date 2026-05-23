# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`merged-findings.json`
- 总体风险：高
- 检测对象：18 组
- 风险信号：高 2 / 中 3 / 低 7
- 运行提示：19 条

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
| paper.md | manuscript |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/paper.md |
| paper_tables.xlsx | supplement |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/paper_tables.xlsx |
| data.csv | raw_data |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/data.csv |
| analysis.py | analysis_code |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/analysis.py |
| western_blot_project_a.png | figures |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/figures/western_blot_project_a.png |
| western_blot_project_b.png | figures |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/figures/western_blot_project_b.png |
| Sheet1 | table | 1 | 4 | summary_statistics_table | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/paper_tables.xlsx |
| data | table | 4 | 1 | raw_observation_table | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full/data.csv |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | citation_claim_check | code_rerun_audit | code_rerun_execute | crosscheck | data_trace_crosscheck | image_copy_move_internal | image_duplicate_internal | image_extract | image_metadata_audit | papermill_light_signals | papermill_network_signals | provenance_chain_verify | provenance_hash | r_scrutiny | reference_audit | western_blot_review_list |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sheet1 | 1 | 4 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/reports/pcr.project_full.parts/data-1.parts/extracted/01_Sheet1.csv | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| data | 4 | 1 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| provenance_hash | 6 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| provenance_chain_verify | 6 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低6 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| code_rerun_audit | 1 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| code_rerun_execute | 1 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| data_trace_crosscheck | 6 | 7 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高2 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| papermill_network_signals | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| reference_audit | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| citation_claim_check | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| papermill_light_signals | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_extract | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_duplicate_internal | 2 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中1 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_copy_move_internal | 2 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中2 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_metadata_audit | 2 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| western_blot_review_list | 2 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低1 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| r_scrutiny | R scrutiny | paper_tables.xlsx:Sheet1 | ready | ready | r | summary_statistics_table | 确定性路由判定该工具适用于当前材料。 | 适用于报告均值、SD、N、比例或二元数据摘要；需确认量表范围、四舍五入规则和变量类型。 |
| crosscheck | 行级数学交叉校验 | paper_tables.xlsx:Sheet1 | ready | ready | python | summary_statistics_table | 确定性路由判定该工具适用于当前材料。 | 只校验表内派生统计量的数学一致性；无法判断原始观测是否真实或统计模型是否合适。 |
| raw_data_rules | 基础表格规则 | data.csv:data | ready | ready | python | raw_observation_table | 确定性路由判定该工具适用于当前材料。 | 用于发现数据形态、数字分布和列间关系异常；实验设计变量、仪器阈值、批量导出格式、合法派生变量可能触发误报。 |

## 覆盖缺口与未运行原因

本次路由上下文中未记录需要单列说明的未运行、依赖缺失或材料不足状态。

## 风险发现清单（问题清单）

| 风险 | 置信度 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |
|---|---:|---|---|---|---|---|---|---|
| 高 | 85% | data_trace_crosscheck:原始数据/稿件摘要统计对账:value_mean | data_trace_crosscheck | 原始数据/稿件摘要统计对账 | value mean | 稿件或脚本输出中的摘要统计量与原始数据自动汇总不一致。 | reported=99; raw=2.5; source=paper_tables.xlsx:Sheet1:row1; raw_source=data.csv:value | 核对变量名映射、分组筛选、缺失剔除规则和稿件表格是否来自同一版数据。 |
| 高 | 85% | data_trace_crosscheck:原始数据/稿件摘要统计对账:value_sd | data_trace_crosscheck | 原始数据/稿件摘要统计对账 | value sd | 稿件或脚本输出中的摘要统计量与原始数据自动汇总不一致。 | reported=1; raw=1.29099; source=paper_tables.xlsx:Sheet1:row1; raw_source=data.csv:value | 核对变量名映射、分组筛选、缺失剔除规则和稿件表格是否来自同一版数据。 |
| 中 | 60% | image_duplicate_internal:内部重复图像:western_blot_project_a.png_/_western_blot_project_b.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 内部重复图像 | western_blot_project_a.png / western_blot_project_b.png | 两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。 | best_hash=ahash:0; transform=original:0; orb_good=42, keypoints=42/42; hashes_left={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a}; hashes_right={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a} | 检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。 |
| 中 | 60% | image_copy_move_internal:疑似局部复制区域:western_blot_project_a.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 疑似局部复制区域 | western_blot_project_a.png | 单张图内部存在多组相似局部特征，需人工复核是否为 copy-move、重复纹理或图表元素。 | matches=20; clustered_matches=6; keypoints=42; samples=[{"from": [172.8, 43.2], "to": [158.4, 93.6], "distance": 31.0}, {"from": [158.4, 93.6], "to": [172.8, 43.2], "distance": 31.0}, {"from": [58.8, 104.4], "to": [115.2, 104.4], "distance": 7.0}, {"from": [76.8, 104.4], "to": [104.4, 104.4], "distance": 5.0}, {"from": [104.4, 104.4], "to": [76.8, 104.4], "distance": 5.0}, {"from": [115.2, 104.4], "to": [58.8, 104.4], "distance": 7.0}] | 打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。 |
| 中 | 60% | image_copy_move_internal:疑似局部复制区域:western_blot_project_b.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 疑似局部复制区域 | western_blot_project_b.png | 单张图内部存在多组相似局部特征，需人工复核是否为 copy-move、重复纹理或图表元素。 | matches=20; clustered_matches=6; keypoints=42; samples=[{"from": [172.8, 43.2], "to": [158.4, 93.6], "distance": 31.0}, {"from": [158.4, 93.6], "to": [172.8, 43.2], "distance": 31.0}, {"from": [58.8, 104.4], "to": [115.2, 104.4], "distance": 7.0}, {"from": [76.8, 104.4], "to": [104.4, 104.4], "distance": 5.0}, {"from": [104.4, 104.4], "to": [76.8, 104.4], "distance": 5.0}, {"from": [115.2, 104.4], "to": [58.8, 104.4], "distance": 7.0}] | 打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:analysis.py | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 哈希版本链核验 | analysis.py | 哈希版本链状态：new | {"relative_path": "analysis.py", "sha256": "a2251f7ae1655d155f9cdfe921818f0c0c0c07c37dd058c954bd0d52b8a6c4b5", "size": 192, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:data.csv | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 哈希版本链核验 | data.csv | 哈希版本链状态：new | {"relative_path": "data.csv", "sha256": "9eb13bdb1f6f9c2e47dac6249ebb882b2b395f0f236efed09e0ed2bae2b5d081", "size": 22, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:figures/western_blot_project_a.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 哈希版本链核验 | figures/western_blot_project_a.png | 哈希版本链状态：new | {"relative_path": "figures/western_blot_project_a.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:figures/western_blot_project_b.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 哈希版本链核验 | figures/western_blot_project_b.png | 哈希版本链状态：new | {"relative_path": "figures/western_blot_project_b.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:paper.md | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 哈希版本链核验 | paper.md | 哈希版本链状态：new | {"relative_path": "paper.md", "sha256": "7a58ef1bf3fbf28d559603f518887ad78642da737f089d570558e625169a9a97", "size": 165, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:paper_tables.xlsx | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | 哈希版本链核验 | paper_tables.xlsx | 哈希版本链状态：new | {"relative_path": "paper_tables.xlsx", "sha256": "ce628fbe5a5385ebd4f4357b9d685251b1a185ab79ecc0343e1046395820766e", "size": 5436, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | western_blot_review_list:Western_blot/凝胶复核清单:图像文件名 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full | Western blot/凝胶复核清单 | 图像文件名 | 发现疑似 Western blot 或凝胶图片文件名。 | western_blot_project_a.png, western_blot_project_b.png | 请作者提供原始 uncropped blot、曝光参数、拼接说明、loading control 和重复实验记录。 |

## 审计置信度摘要

| 方法学置信度 | 发现数 |
|---|---:|
| 高(>=75%) | 2 |
| 中(40%-75%) | 3 |
| 低(<40%) | 7 |

## 专家复核附录

### 1. 高风险：原始数据/稿件摘要统计对账（value mean）

- 证据ID：data_trace_crosscheck:原始数据/稿件摘要统计对账:value_mean
- 位置：data_trace_crosscheck
- 发现：稿件或脚本输出中的摘要统计量与原始数据自动汇总不一致。
- 触发证据：reported=99; raw=2.5; source=paper_tables.xlsx:Sheet1:row1; raw_source=data.csv:value
- 工具：跨材料数据对账（data_trace_crosscheck）
- 运行时/依赖：python / ready
- 输入类型：project_manifest
- 置信度/误报风险：85%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对变量名映射、分组筛选、缺失剔除规则和稿件表格是否来自同一版数据。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 2. 高风险：原始数据/稿件摘要统计对账（value sd）

- 证据ID：data_trace_crosscheck:原始数据/稿件摘要统计对账:value_sd
- 位置：data_trace_crosscheck
- 发现：稿件或脚本输出中的摘要统计量与原始数据自动汇总不一致。
- 触发证据：reported=1; raw=1.29099; source=paper_tables.xlsx:Sheet1:row1; raw_source=data.csv:value
- 工具：跨材料数据对账（data_trace_crosscheck）
- 运行时/依赖：python / ready
- 输入类型：project_manifest
- 置信度/误报风险：85%（high） / medium
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：核对变量名映射、分组筛选、缺失剔除规则和稿件表格是否来自同一版数据。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 3. 中风险：内部重复图像（western_blot_project_a.png / western_blot_project_b.png）

- 证据ID：image_duplicate_internal:内部重复图像:western_blot_project_a.png_/_western_blot_project_b.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。
- 触发证据：best_hash=ahash:0; transform=original:0; orb_good=42, keypoints=42/42; hashes_left={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a}; hashes_right={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a}
- 工具：稿件内部重复图初筛（image_duplicate_internal）
- 运行时/依赖：python / ready
- 输入类型：scientific_figure
- 置信度/误报风险：60%（medium） / medium
- 计算/抽取过程：Pillow/numpy 本地 aHash/dHash/pHash；若 cv2 可用则附加 ORB 局部特征匹配；不上传图片。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 4. 中风险：疑似局部复制区域（western_blot_project_a.png）

- 证据ID：image_copy_move_internal:疑似局部复制区域:western_blot_project_a.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：单张图内部存在多组相似局部特征，需人工复核是否为 copy-move、重复纹理或图表元素。
- 触发证据：matches=20; clustered_matches=6; keypoints=42; samples=[{"from": [172.8, 43.2], "to": [158.4, 93.6], "distance": 31.0}, {"from": [158.4, 93.6], "to": [172.8, 43.2], "distance": 31.0}, {"from": [58.8, 104.4], "to": [115.2, 104.4], "distance": 7.0}, {"from": [76.8, 104.4], "to": [104.4, 104.4], "distance": 5.0}, {"from": [104.4, 104.4], "to": [76.8, 104.4], "distance": 5.0}, {"from": [115.2, 104.4], "to": [58.8, 104.4], "distance": 7.0}]
- 工具：图像局部复制初筛（image_copy_move_internal）
- 运行时/依赖：python / ready
- 输入类型：scientific_figure
- 置信度/误报风险：60%（medium） / medium
- 计算/抽取过程：OpenCV ORB 特征在同一图内部自匹配，过滤近邻点后按位移向量聚类。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 5. 中风险：疑似局部复制区域（western_blot_project_b.png）

- 证据ID：image_copy_move_internal:疑似局部复制区域:western_blot_project_b.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：单张图内部存在多组相似局部特征，需人工复核是否为 copy-move、重复纹理或图表元素。
- 触发证据：matches=20; clustered_matches=6; keypoints=42; samples=[{"from": [172.8, 43.2], "to": [158.4, 93.6], "distance": 31.0}, {"from": [158.4, 93.6], "to": [172.8, 43.2], "distance": 31.0}, {"from": [58.8, 104.4], "to": [115.2, 104.4], "distance": 7.0}, {"from": [76.8, 104.4], "to": [104.4, 104.4], "distance": 5.0}, {"from": [104.4, 104.4], "to": [76.8, 104.4], "distance": 5.0}, {"from": [115.2, 104.4], "to": [58.8, 104.4], "distance": 7.0}]
- 工具：图像局部复制初筛（image_copy_move_internal）
- 运行时/依赖：python / ready
- 输入类型：scientific_figure
- 置信度/误报风险：60%（medium） / medium
- 计算/抽取过程：OpenCV ORB 特征在同一图内部自匹配，过滤近邻点后按位移向量聚类。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 6. 低风险：哈希版本链核验（analysis.py）

- 证据ID：provenance_chain_verify:哈希版本链核验:analysis.py
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "analysis.py", "sha256": "a2251f7ae1655d155f9cdfe921818f0c0c0c07c37dd058c954bd0d52b8a6c4b5", "size": 192, "status": "new"}
- 工具：哈希版本链核验（provenance_chain_verify）
- 运行时/依赖：python / ready
- 输入类型：raw_file_bundle
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 计算/抽取过程：读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。

### 7. 低风险：哈希版本链核验（data.csv）

- 证据ID：provenance_chain_verify:哈希版本链核验:data.csv
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "data.csv", "sha256": "9eb13bdb1f6f9c2e47dac6249ebb882b2b395f0f236efed09e0ed2bae2b5d081", "size": 22, "status": "new"}
- 工具：哈希版本链核验（provenance_chain_verify）
- 运行时/依赖：python / ready
- 输入类型：raw_file_bundle
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 计算/抽取过程：读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。

### 8. 低风险：哈希版本链核验（figures/western_blot_project_a.png）

- 证据ID：provenance_chain_verify:哈希版本链核验:figures/western_blot_project_a.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "figures/western_blot_project_a.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"}
- 工具：哈希版本链核验（provenance_chain_verify）
- 运行时/依赖：python / ready
- 输入类型：raw_file_bundle
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 计算/抽取过程：读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。

### 9. 低风险：哈希版本链核验（figures/western_blot_project_b.png）

- 证据ID：provenance_chain_verify:哈希版本链核验:figures/western_blot_project_b.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "figures/western_blot_project_b.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"}
- 工具：哈希版本链核验（provenance_chain_verify）
- 运行时/依赖：python / ready
- 输入类型：raw_file_bundle
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 计算/抽取过程：读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。

### 10. 低风险：哈希版本链核验（paper.md）

- 证据ID：provenance_chain_verify:哈希版本链核验:paper.md
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "paper.md", "sha256": "7a58ef1bf3fbf28d559603f518887ad78642da737f089d570558e625169a9a97", "size": 165, "status": "new"}
- 工具：哈希版本链核验（provenance_chain_verify）
- 运行时/依赖：python / ready
- 输入类型：raw_file_bundle
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 计算/抽取过程：读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。

### 11. 低风险：哈希版本链核验（paper_tables.xlsx）

- 证据ID：provenance_chain_verify:哈希版本链核验:paper_tables.xlsx
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "paper_tables.xlsx", "sha256": "ce628fbe5a5385ebd4f4357b9d685251b1a185ab79ecc0343e1046395820766e", "size": 5436, "status": "new"}
- 工具：哈希版本链核验（provenance_chain_verify）
- 运行时/依赖：python / ready
- 输入类型：raw_file_bundle
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 计算/抽取过程：读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。

### 12. 低风险：Western blot/凝胶复核清单（图像文件名）

- 证据ID：western_blot_review_list:Western_blot/凝胶复核清单:图像文件名
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/project_full
- 发现：发现疑似 Western blot 或凝胶图片文件名。
- 触发证据：western_blot_project_a.png, western_blot_project_b.png
- 工具：Western blot复核清单（western_blot_review_list）
- 运行时/依赖：python / ready
- 输入类型：western_blot_or_gel_image
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：请作者提供原始 uncropped blot、曝光参数、拼接说明、loading control 和重复实验记录。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

## 人工复核任务表

| 序号 | 复核任务 | 涉及证据数 |
|---:|---|---:|
| 1 | 核对变量名映射、分组筛选、缺失剔除规则和稿件表格是否来自同一版数据。 | 2 |
| 2 | 检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。 | 1 |
| 3 | 打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。 | 2 |
| 4 | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 | 6 |
| 5 | 请作者提供原始 uncropped blot、曝光参数、拼接说明、loading control 和重复实验记录。 | 1 |

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| citation_claim_check | 1 |
| code_rerun_audit | 1 |
| code_rerun_execute | 1 |
| crosscheck | 1 |
| data_trace_crosscheck | 2 |
| image_copy_move_internal | 2 |
| image_duplicate_internal | 1 |
| image_extract | 2 |
| image_metadata_audit | 2 |
| papermill_light_signals | 1 |
| papermill_network_signals | 1 |
| provenance_chain_verify | 6 |
| provenance_hash | 6 |
| r_scrutiny | 1 |
| reference_audit | 2 |
| western_blot_review_list | 1 |

- `crosscheck`：逐行交叉验证已完成，未发现统计量内部不一致。（检查行数=1；依赖状态=ready；输入类型=summary_statistics_table）
- `r_scrutiny`：R scrutiny 已运行。（GRIMMER候选行=1；DEBIT候选行=0；依赖状态=ready；输入类型=）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=7a58ef1bf3fbf28d559603f518887ad78642da737f089d570558e625169a9a97; size=165; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=ce628fbe5a5385ebd4f4357b9d685251b1a185ab79ecc0343e1046395820766e; size=5436; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=9eb13bdb1f6f9c2e47dac6249ebb882b2b395f0f236efed09e0ed2bae2b5d081; size=22; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=a2251f7ae1655d155f9cdfe921818f0c0c0c07c37dd058c954bd0d52b8a6c4b5; size=192; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca; size=759; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca; size=759; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `code_rerun_audit`：未发现可扫描的分析代码，或未命中内置复跑风险规则。（代码文件数=1；依赖状态=ready；输入类型=analysis_code）
- `code_rerun_execute`：分析脚本沙箱复跑完成。（returncode=0; changed_files=1; stdout=; stderr=；依赖状态=ready；输入类型=project_manifest）
- `papermill_network_signals`：未提供本地 corpus 索引，跨稿件论文工厂信号未运行。（使用 pcr-audit corpus build 生成 corpus-index.json 后再执行 screen。；依赖状态=insufficient_material；输入类型=project_manifest）
- `reference_audit`：已解析出可核验的参考文献标识符。（DOI=1，PMID=0，候选参考文献行=1；依赖状态=ready；输入类型=reference_list）
- `reference_audit`：默认本地/私有化运行未向外部API发送稿件或参考文献信息。（使用 --external-lookups 或设置 PCR_ENABLE_EXTERNAL_LOOKUPS=1 后才会查询 Crossref、OpenAlex 和 NCBI E-utilities。；依赖状态=external_lookup_disabled；输入类型=reference_list）
- `citation_claim_check`：已抽取带引用主张，供人工或RAG流程复核。（候选主张=1；样例：The outcome was assessed with the same imaging workflow and statistical model [1]；依赖状态=ready；输入类型=reference_list）
- `papermill_light_signals`：轻量短语扫描完成，未发现内置异常短语。（扫描字符数=165，规则数=7；依赖状态=ready；输入类型=plain_text）
- `image_extract`：未发现可直接检测的图片文件。（PDF 图像抽取为 best-effort；DOCX 可抽取 word/media 下图片。；依赖状态=insufficient_material；输入类型=scientific_figure）
- `image_extract`：已发现可检测图片。（图片数=2；样例=western_blot_project_a.png, western_blot_project_b.png；依赖状态=ready；输入类型=scientific_figure）
- `image_metadata_audit`：图像元数据读取完成，未发现内置质量阈值信号。（format=PNG; size=220x150; mode=RGB; exif_fields=0; gray_mean=203.5; gray_std=92.9；依赖状态=ready；输入类型=scientific_figure）
- `image_metadata_audit`：图像元数据读取完成，未发现内置质量阈值信号。（format=PNG; size=220x150; mode=RGB; exif_fields=0; gray_mean=203.5; gray_std=92.9；依赖状态=ready；输入类型=scientific_figure）

