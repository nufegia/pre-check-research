# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`analysis_suspicious.py`
- 总体风险：低
- 检测对象：2 组
- 风险信号：高 0 / 中 0 / 低 1
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
| analysis_suspicious.py | code |  |  | analysis_code | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/analysis_suspicious.py |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | code_rerun_audit | code_rerun_execute |
|---|---:|---:|---|---|
| code_rerun_audit | 1 | 0 | 高0 中0 低1 | 高0 中0 低0 |
| code_rerun_execute | 1 | 0 | 高0 中0 低0 | 高0 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| code_rerun_audit | 分析代码复跑审计 | analysis_suspicious.py | ready | ready | python | analysis_code | 确定性路由判定该工具适用于当前材料。 | 该工具只读扫描复跑准备风险；Python AST 和更强多语言解析可后续增强。实际 Python/R 执行由 code_rerun_execute 在临时项目副本中处理。 |
| code_rerun_execute | 分析脚本沙箱复跑 | analysis_suspicious.py | ready | ready | python | analysis_code | 确定性路由判定该工具适用于当前材料。 | 本地临时目录隔离不能替代强安全容器；脚本失败、超时或缺包只记录为运行提示。 |

## 覆盖缺口与未运行原因

本次路由上下文中未记录需要单列说明的未运行、依赖缺失或材料不足状态。

## 风险发现清单（问题清单）

| 风险 | 置信度 | 证据ID | 位置 | 检查项 | 对象 | 发现 | 证据 | 复核动作 |
|---|---:|---|---|---|---|---|---|---|
| 低 | 30%（低置信度，建议补充数据后重检） | code_rerun_audit:分析代码复跑准备检查:analysis_suspicious.py | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/analysis_suspicious.py | 分析代码复跑准备检查 | analysis_suspicious.py | 脚本包含需要复跑前确认的输入、路径或剔除规则。 | 脚本存在缺失值剔除，需核对剔除规则和样本量变化。 | 在隔离环境中复跑前，确认依赖、输入文件、随机种子、剔除规则和输出统计量映射。 |

## 审计置信度摘要

| 方法学置信度 | 发现数 |
|---|---:|
| 高(>=75%) | 0 |
| 中(40%-75%) | 0 |
| 低(<40%) | 1 |

## 专家复核附录

### 1. 低风险：分析代码复跑准备检查（analysis_suspicious.py）

- 证据ID：code_rerun_audit:分析代码复跑准备检查:analysis_suspicious.py
- 位置：/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/analysis_suspicious.py
- 发现：脚本包含需要复跑前确认的输入、路径或剔除规则。
- 触发证据：脚本存在缺失值剔除，需核对剔除规则和样本量变化。
- 工具：分析代码复跑审计（code_rerun_audit）
- 运行时/依赖：python / ready
- 输入类型：analysis_code
- 置信度/误报风险：30%（low） / medium
- 低置信度提示：该信号置信度较低，建议补充数据后重新检测。
- 路由依据：由确定性路由选择该工具。
- 可能正常解释：可能的正常原因包括实验设计、仪器阈值、批量格式化、表格抽取误差或合理的数据清洗。
- 复核动作：在隔离环境中复跑前，确认依赖、输入文件、随机种子、剔除规则和输出统计量映射。
- 方法限制：该结果只提示需要复核的风险信号，不构成数据风险校验判定。
- 置信依据：基于确定性规则或可复算公式生成；仍需结合研究设计、原始记录和材料抽取质量人工判断。

## 人工复核任务表

| 序号 | 复核任务 | 涉及证据数 |
|---:|---|---:|
| 1 | 在隔离环境中复跑前，确认依赖、输入文件、随机种子、剔除规则和输出统计量映射。 | 1 |

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| code_rerun_audit | 1 |
| code_rerun_execute | 1 |

- `code_rerun_execute`：分析脚本沙箱复跑失败，已记录为运行提示。（returncode=1; changed_files=0; stdout=; stderr=handles = get_handle(
                   ^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.11/lib/python3.11/site-packages/pandas/io/common.py", line 873, in get_handle
    handle = open(
             ^^^^^
FileNotFoundError: [Errno 2] No such file or directory: 'project/data.csv'
；依赖状态=ready；输入类型=project_manifest）

