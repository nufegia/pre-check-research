# 数据审计报告：数据完整性与统计一致性

## 导师摘要

- 文件：`analysis_manual.do`
- 总体风险：低
- 检测对象：2 组
- 风险信号：高 0 / 中 0 / 低 0
- 运行提示：3 条

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
| analysis_manual.do | code |  |  | analysis_code | routed | /Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/analysis_manual.do |

## 材料覆盖矩阵

| 材料/模块 | 行数 | 列数 | code_rerun_audit | code_rerun_execute |
|---|---:|---:|---|---|
| code_rerun_audit | 1 | 0 | 高0 中0 低0 | 高0 中0 低0 |
| code_rerun_execute | 0 | 0 | 高0 中0 低0 | 高0 中0 低0 |

## 工具运行明细

| 工具 | 名称 | 材料/模块 | 状态 | 依赖状态 | 运行时 | 输入类型 | 路由/运行依据 | 方法限制 |
|---|---|---|---|---|---|---|---|---|
| code_rerun_audit | 分析代码复跑审计 | analysis_manual.do | ready | ready | python | analysis_code | 确定性路由判定该工具适用于当前材料。 | 该工具只读扫描复跑准备风险；Python AST 和更强多语言解析可后续增强。实际 Python/R 执行由 code_rerun_execute 在临时项目副本中处理。 |
| code_rerun_execute | 分析脚本沙箱复跑 | analysis_manual.do | ready | ready | python | analysis_code | 确定性路由判定该工具适用于当前材料。 | 本地临时目录隔离不能替代强安全容器；脚本失败、超时或缺包只记录为运行提示。 |

## 覆盖缺口与未运行原因

本次路由上下文中未记录需要单列说明的未运行、依赖缺失或材料不足状态。

## 风险发现清单（问题清单）

未发现明显异常模式。建议仍结合原始记录、实验设计和统计脚本进行人工复核。

## 专家复核附录

本次没有可展开的风险发现。

## 人工复核任务表

本次没有由风险发现聚合出的人工复核任务。

## 运行提示（不计入风险）

| 工具 | 记录数 |
|---|---:|
| code_rerun_audit | 1 |
| code_rerun_execute | 2 |

- `code_rerun_audit`：未发现可扫描的分析代码，或未命中内置复跑风险规则。（代码文件数=1；依赖状态=ready；输入类型=analysis_code）
- `code_rerun_execute`：当前版本不执行 Stata/SPSS/SAS 等脚本。（/Users/daotuanwang/归档/项目/PreCheckResearch/mvp2/benchmark/inputs/analysis_manual.do；依赖状态=ready；输入类型=project_manifest）
- `code_rerun_execute`：未发现可复跑的 Python/R 脚本。（code_files=1；依赖状态=ready；输入类型=project_manifest）

