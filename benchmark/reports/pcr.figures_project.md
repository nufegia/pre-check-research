# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`figures`
- 总体风险：中
- 检测对象：12 组
- 风险信号：高 0 / 中 5 / 低 6
- 运行提示：13 条

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
| copy_move_panel.png | figures |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures/copy_move_panel.png |
| low_resolution_control.png | figures |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures/low_resolution_control.png |
| western_blot_panel_a.png | figures |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures/western_blot_panel_a.png |
| western_blot_panel_b.png | figures |  |  | project_material | listed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures/western_blot_panel_b.png |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | code_rerun_audit | code_rerun_execute | data_trace_crosscheck | image_copy_move_internal | image_duplicate_internal | image_extract | image_metadata_audit | papermill_network_signals | project_audit | provenance_chain_verify | provenance_hash | western_blot_review_list |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| project_manifest | 4 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| provenance_hash | 4 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| provenance_chain_verify | 4 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低4 | 高0 中0 低0 | 高0 中0 低0 |
| code_rerun_audit | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| code_rerun_execute | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| data_trace_crosscheck | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| papermill_network_signals | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_extract | 4 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_duplicate_internal | 4 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中3 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_copy_move_internal | 4 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中2 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| image_metadata_audit | 4 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低1 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 |
| western_blot_review_list | 2 | 0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低0 | 高0 中0 低1 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| project_audit | 项目Manifest解析 | project_manifest | recorded | missing_material | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| provenance_hash | 原始文件哈希存证 | provenance_hash | recorded | ready | python | raw_file_bundle | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| provenance_chain_verify | 哈希版本链核验 | provenance_chain_verify | recorded | ready | python | raw_file_bundle | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| code_rerun_audit | 分析代码复跑审计 | code_rerun_audit | recorded | insufficient_material | python | analysis_code | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| code_rerun_execute | 分析脚本沙箱复跑 | code_rerun_execute | recorded | ready | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| data_trace_crosscheck | 跨材料数据对账 | data_trace_crosscheck | recorded | ready | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| papermill_network_signals | 本地论文工厂跨库信号 | papermill_network_signals | recorded | insufficient_material | python | project_manifest | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| image_extract | 图像抽取 | image_extract | recorded | ready | python | scientific_figure | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| image_duplicate_internal | 稿件内部重复图初筛 | image_duplicate_internal | recorded | ready | python | scientific_figure | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| image_copy_move_internal | 图像局部复制初筛 | image_copy_move_internal | recorded | ready | python | scientific_figure | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| image_metadata_audit | 图像元数据与质量初筛 | image_metadata_audit | recorded | ready | python | scientific_figure | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |
| western_blot_review_list | Western blot复核清单 | western_blot_review_list | recorded | ready | python | western_blot_or_gel_image | 由确定性路由选择该工具。 | 该结果只提示需要复核的风险信号，不构成数据风险校验判定。 |

## 覆盖缺口与未运行原因

| 工具 | 材料/模块 | 状态 | 依赖状态 | 原因 | 对预审的影响 |
|---|---|---|---|---|---|
| project_audit | project_manifest | recorded | missing_material | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| provenance_hash | provenance_hash | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| provenance_chain_verify | provenance_chain_verify | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| code_rerun_audit | code_rerun_audit | recorded | insufficient_material | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| code_rerun_execute | code_rerun_execute | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| data_trace_crosscheck | data_trace_crosscheck | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| papermill_network_signals | papermill_network_signals | recorded | insufficient_material | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| image_extract | image_extract | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| image_duplicate_internal | image_duplicate_internal | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| image_copy_move_internal | image_copy_move_internal | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| image_metadata_audit | image_metadata_audit | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |
| western_blot_review_list | western_blot_review_list | recorded | ready | 由确定性路由选择该工具。 | 该工具本次未形成风险发现；需补齐材料或依赖后复跑，才能覆盖对应检查。 |

## 风险发现清单（问题清单）

| 风险 | 置信度 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |
|---|---:|---|---|---|---|---|---|---|
| 中 | 60% | image_duplicate_internal:内部重复图像:copy_move_panel.png_/_western_blot_panel_a.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 内部重复图像 | copy_move_panel.png / western_blot_panel_a.png | 两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。 | best_hash=ahash:0; transform=original:18; orb_good=6, keypoints=15/42; hashes_left={ahash:ffff00000081ffff, dhash:004d6d6d6d6d0300, phash:ee3e91c1a5c56e3e}; hashes_right={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a} | 检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。 |
| 中 | 60% | image_duplicate_internal:内部重复图像:copy_move_panel.png_/_western_blot_panel_b.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 内部重复图像 | copy_move_panel.png / western_blot_panel_b.png | 两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。 | best_hash=ahash:0; transform=original:18; orb_good=6, keypoints=15/42; hashes_left={ahash:ffff00000081ffff, dhash:004d6d6d6d6d0300, phash:ee3e91c1a5c56e3e}; hashes_right={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a} | 检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。 |
| 中 | 60% | image_duplicate_internal:内部重复图像:western_blot_panel_a.png_/_western_blot_panel_b.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 内部重复图像 | western_blot_panel_a.png / western_blot_panel_b.png | 两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。 | best_hash=ahash:0; transform=original:0; orb_good=42, keypoints=42/42; hashes_left={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a}; hashes_right={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a} | 检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。 |
| 中 | 60% | image_copy_move_internal:疑似局部复制区域:western_blot_panel_a.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 疑似局部复制区域 | western_blot_panel_a.png | 单张图内部存在多组相似局部特征，需人工复核是否为 copy-move、重复纹理或图表元素。 | matches=20; clustered_matches=6; keypoints=42; samples=[{"from": [172.8, 43.2], "to": [158.4, 93.6], "distance": 31.0}, {"from": [158.4, 93.6], "to": [172.8, 43.2], "distance": 31.0}, {"from": [58.8, 104.4], "to": [115.2, 104.4], "distance": 7.0}, {"from": [76.8, 104.4], "to": [104.4, 104.4], "distance": 5.0}, {"from": [104.4, 104.4], "to": [76.8, 104.4], "distance": 5.0}, {"from": [115.2, 104.4], "to": [58.8, 104.4], "distance": 7.0}] | 打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。 |
| 中 | 60% | image_copy_move_internal:疑似局部复制区域:western_blot_panel_b.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 疑似局部复制区域 | western_blot_panel_b.png | 单张图内部存在多组相似局部特征，需人工复核是否为 copy-move、重复纹理或图表元素。 | matches=20; clustered_matches=6; keypoints=42; samples=[{"from": [172.8, 43.2], "to": [158.4, 93.6], "distance": 31.0}, {"from": [158.4, 93.6], "to": [172.8, 43.2], "distance": 31.0}, {"from": [58.8, 104.4], "to": [115.2, 104.4], "distance": 7.0}, {"from": [76.8, 104.4], "to": [104.4, 104.4], "distance": 5.0}, {"from": [104.4, 104.4], "to": [76.8, 104.4], "distance": 5.0}, {"from": [115.2, 104.4], "to": [58.8, 104.4], "distance": 7.0}] | 打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:copy_move_panel.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 哈希版本链核验 | copy_move_panel.png | 哈希版本链状态：new | {"relative_path": "copy_move_panel.png", "sha256": "bc62648e696e3f6136b615ee1bc8d7598068d35c05e4be414a2ba3760f2e5c3d", "size": 563, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:low_resolution_control.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 哈希版本链核验 | low_resolution_control.png | 哈希版本链状态：new | {"relative_path": "low_resolution_control.png", "sha256": "efe28a2296d36cd51e70030ed482726f7c8e2969e3625e1eb3fb26ca9ac49239", "size": 160, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:western_blot_panel_a.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 哈希版本链核验 | western_blot_panel_a.png | 哈希版本链状态：new | {"relative_path": "western_blot_panel_a.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | provenance_chain_verify:哈希版本链核验:western_blot_panel_b.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 哈希版本链核验 | western_blot_panel_b.png | 哈希版本链状态：new | {"relative_path": "western_blot_panel_b.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"} | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 |
| 低 | 30%（低置信度，建议补充数据后重检） | image_metadata_audit:图像元数据与质量:low_resolution_control.png | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | 图像元数据与质量 | low_resolution_control.png | 图片分辨率较低，可能限制图像取证和人工复核。 | format=PNG; size=50x50; mode=RGB; exif_fields=0; gray_mean=255.0; gray_std=0.0 | 结合原始仪器文件、导出流程和未压缩原图人工复核。 |
| 低 | 30%（低置信度，建议补充数据后重检） | western_blot_review_list:Western_blot/凝胶复核清单:图像文件名 | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures | Western blot/凝胶复核清单 | 图像文件名 | 发现疑似 Western blot 或凝胶图片文件名。 | western_blot_panel_a.png, western_blot_panel_b.png | 请作者提供原始 uncropped blot、曝光参数、拼接说明、loading control 和重复实验记录。 |

## 审计置信度摘要

| 方法学置信度 | 发现数 |
|---|---:|
| 高(>=75%) | 0 |
| 中(40%-75%) | 5 |
| 低(<40%) | 6 |

## 专家复核附录

### 1. 中风险：内部重复图像（copy_move_panel.png / western_blot_panel_a.png）

- 证据ID：image_duplicate_internal:内部重复图像:copy_move_panel.png_/_western_blot_panel_a.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。
- 触发证据：best_hash=ahash:0; transform=original:18; orb_good=6, keypoints=15/42; hashes_left={ahash:ffff00000081ffff, dhash:004d6d6d6d6d0300, phash:ee3e91c1a5c56e3e}; hashes_right={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a}
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

### 2. 中风险：内部重复图像（copy_move_panel.png / western_blot_panel_b.png）

- 证据ID：image_duplicate_internal:内部重复图像:copy_move_panel.png_/_western_blot_panel_b.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。
- 触发证据：best_hash=ahash:0; transform=original:18; orb_good=6, keypoints=15/42; hashes_left={ahash:ffff00000081ffff, dhash:004d6d6d6d6d0300, phash:ee3e91c1a5c56e3e}; hashes_right={ahash:ffff00000081ffff, dhash:00494551514d0000, phash:ea6a959569c13a7a}
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

### 3. 中风险：内部重复图像（western_blot_panel_a.png / western_blot_panel_b.png）

- 证据ID：image_duplicate_internal:内部重复图像:western_blot_panel_a.png_/_western_blot_panel_b.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
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

### 4. 中风险：疑似局部复制区域（western_blot_panel_a.png）

- 证据ID：image_copy_move_internal:疑似局部复制区域:western_blot_panel_a.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
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

### 5. 中风险：疑似局部复制区域（western_blot_panel_b.png）

- 证据ID：image_copy_move_internal:疑似局部复制区域:western_blot_panel_b.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
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

### 6. 低风险：哈希版本链核验（copy_move_panel.png）

- 证据ID：provenance_chain_verify:哈希版本链核验:copy_move_panel.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "copy_move_panel.png", "sha256": "bc62648e696e3f6136b615ee1bc8d7598068d35c05e4be414a2ba3760f2e5c3d", "size": 563, "status": "new"}
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

### 7. 低风险：哈希版本链核验（low_resolution_control.png）

- 证据ID：provenance_chain_verify:哈希版本链核验:low_resolution_control.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "low_resolution_control.png", "sha256": "efe28a2296d36cd51e70030ed482726f7c8e2969e3625e1eb3fb26ca9ac49239", "size": 160, "status": "new"}
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

### 8. 低风险：哈希版本链核验（western_blot_panel_a.png）

- 证据ID：provenance_chain_verify:哈希版本链核验:western_blot_panel_a.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "western_blot_panel_a.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"}
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

### 9. 低风险：哈希版本链核验（western_blot_panel_b.png）

- 证据ID：provenance_chain_verify:哈希版本链核验:western_blot_panel_b.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：哈希版本链状态：new
- 触发证据：{"relative_path": "western_blot_panel_b.png", "sha256": "0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca", "size": 759, "status": "new"}
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

### 10. 低风险：图像元数据与质量（low_resolution_control.png）

- 证据ID：image_metadata_audit:图像元数据与质量:low_resolution_control.png
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：图片分辨率较低，可能限制图像取证和人工复核。
- 触发证据：format=PNG; size=50x50; mode=RGB; exif_fields=0; gray_mean=255.0; gray_std=0.0
- 工具：图像元数据与质量初筛（image_metadata_audit）
- 运行时/依赖：python / ready
- 输入类型：scientific_figure
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：结合原始仪器文件、导出流程和未压缩原图人工复核。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

### 11. 低风险：Western blot/凝胶复核清单（图像文件名）

- 证据ID：western_blot_review_list:Western_blot/凝胶复核清单:图像文件名
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/figures
- 发现：发现疑似 Western blot 或凝胶图片文件名。
- 触发证据：western_blot_panel_a.png, western_blot_panel_b.png
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
| 1 | 检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。 | 3 |
| 2 | 打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。 | 2 |
| 3 | 对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。 | 4 |
| 4 | 结合原始仪器文件、导出流程和未压缩原图人工复核。 | 1 |
| 5 | 请作者提供原始 uncropped blot、曝光参数、拼接说明、loading control 和重复实验记录。 | 1 |

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| code_rerun_audit | 1 |
| code_rerun_execute | 1 |
| data_trace_crosscheck | 1 |
| image_copy_move_internal | 2 |
| image_duplicate_internal | 3 |
| image_extract | 1 |
| image_metadata_audit | 4 |
| papermill_network_signals | 1 |
| project_audit | 1 |
| provenance_chain_verify | 4 |
| provenance_hash | 4 |
| western_blot_review_list | 1 |

- `project_audit`：项目材料中未识别到主稿文件。（可继续审计数据/代码/图像，但文献、引用和正文统计覆盖会受限。；依赖状态=missing_material；输入类型=project_manifest）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=bc62648e696e3f6136b615ee1bc8d7598068d35c05e4be414a2ba3760f2e5c3d; size=563; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=efe28a2296d36cd51e70030ed482726f7c8e2969e3625e1eb3fb26ca9ac49239; size=160; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca; size=759; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `provenance_hash`：已计算文件哈希和基础元数据。（sha256=0e202e24af20cbfe14f09ee413e0728ab9d7ff54819b1ef321b3ceb1ed3214ca; size=759; mtime=1779499974；依赖状态=ready；输入类型=raw_file_bundle）
- `code_rerun_audit`：未发现可扫描的分析代码，或未命中内置复跑风险规则。（代码文件数=0；依赖状态=insufficient_material；输入类型=analysis_code）
- `code_rerun_execute`：用户关闭了脚本沙箱复跑。（rerun_code=false；依赖状态=ready；输入类型=project_manifest）
- `data_trace_crosscheck`：未获得足够的原始数据统计量或文档摘要统计表，跨材料对账未运行。（raw_stats=0; summary_values=0；依赖状态=ready；输入类型=project_manifest）
- `papermill_network_signals`：未提供本地 corpus 索引，跨稿件论文工厂信号未运行。（使用 pcr-audit corpus build 生成 corpus-index.json 后再执行 screen。；依赖状态=insufficient_material；输入类型=project_manifest）
- `image_extract`：已发现可检测图片。（图片数=4；样例=copy_move_panel.png, low_resolution_control.png, western_blot_panel_a.png, western_blot_panel_b.png；依赖状态=ready；输入类型=scientific_figure）
- `image_metadata_audit`：图像元数据读取完成，未发现内置质量阈值信号。（format=PNG; size=220x150; mode=RGB; exif_fields=0; gray_mean=202.2; gray_std=97.9；依赖状态=ready；输入类型=scientific_figure）
- `image_metadata_audit`：图像元数据读取完成，未发现内置质量阈值信号。（format=PNG; size=220x150; mode=RGB; exif_fields=0; gray_mean=203.5; gray_std=92.9；依赖状态=ready；输入类型=scientific_figure）
- `image_metadata_audit`：图像元数据读取完成，未发现内置质量阈值信号。（format=PNG; size=220x150; mode=RGB; exif_fields=0; gray_mean=203.5; gray_std=92.9；依赖状态=ready；输入类型=scientific_figure）

