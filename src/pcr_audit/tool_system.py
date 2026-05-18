"""Tool registry, data classification, and routing for integrity checks."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    display_name: str
    category: str
    description: str
    accepted_input_types: tuple[str, ...]
    required_fields: tuple[str, ...] = ()
    minimum_sample_size: int = 0
    default_enabled: bool = False
    dependency_module: str | None = None
    r_package: str | None = None
    detector_runtime: str = "python"
    reliability: str = "稳定"
    method_limitations: str = ""


@dataclass
class RoutingDecision:
    tool_id: str
    tool_name: str
    category: str
    selected_by_user: bool
    applicable: bool
    ran: bool
    status: str
    skip_reason: str
    matched_input_type: str
    required_fields_found: list[str]
    method_limitations: str
    detector_runtime: str = "python"
    dependency_status: str = "ready"
    reliability: str = "稳定"


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "raw_data_rules": ToolSpec(
        tool_id="raw_data_rules",
        display_name="基础表格规则",
        category="原始数据",
        description="空表、缺失、重复、高频值、固定步长、连续重复、离群值等 Python 基础规则。",
        accepted_input_types=("raw_observation_table", "figure_source_data"),
        minimum_sample_size=2,
        default_enabled=True,
        reliability="稳定",
        method_limitations="用于发现数据形态异常；实验设计变量、仪器阈值、批量导出格式可能触发误报。",
    ),
    "r_scrutiny": ToolSpec(
        tool_id="r_scrutiny",
        display_name="R scrutiny",
        category="R 统计一致性",
        description="通过 R scrutiny 执行 GRIM、GRIMMER、DEBIT 等摘要统计可行性检查。",
        accepted_input_types=("summary_statistics_table", "continuous_measure_summary", "likert_or_integer_scale_summary"),
        default_enabled=False,
        r_package="scrutiny",
        detector_runtime="r",
        reliability="需 R",
        method_limitations="适用于报告均值、SD、N、比例或二元数据摘要；需确认量表范围、四舍五入规则和变量类型。",
    ),
    "r_statcheck": ToolSpec(
        tool_id="r_statcheck",
        display_name="R statcheck",
        category="R 正文统计",
        description="通过 R statcheck 检查论文正文 APA 统计表达式与 p 值一致性。",
        accepted_input_types=("apa_statistical_text",),
        default_enabled=False,
        r_package="statcheck",
        detector_runtime="r",
        reliability="需 R",
        method_limitations="只适用于可被 statcheck 解析的 APA/NHST 表达式；中文全角标点、非标准统计报告和抽取失败文本会降低覆盖率。",
    ),
    "r_rsprite2": ToolSpec(
        tool_id="r_rsprite2",
        display_name="R rsprite2",
        category="R 高级复核",
        description="通过 R rsprite2 进行 SPRITE 离散分布反推，适合专家级复核。",
        accepted_input_types=("likert_or_integer_scale_summary",),
        default_enabled=False,
        r_package="rsprite2",
        detector_runtime="r",
        reliability="高级/需 R",
        method_limitations="需要明确量表范围、精度和约束；结果解释成本高，只作为专家复核入口。",
    ),
    "crosscheck": ToolSpec(
        tool_id="crosscheck",
        display_name="行级数学交叉校验",
        category="统计一致性",
        description="对摘要统计表执行 SE/SD/√N、CI/SE、percent/count/N、p/t/df 等纯数学交叉校验。",
        accepted_input_types=("summary_statistics_table", "continuous_measure_summary", "likert_or_integer_scale_summary"),
        default_enabled=False,
        reliability="稳定",
        method_limitations="只校验表内派生统计量的数学一致性；无法判断原始观测是否真实或统计模型是否合适。",
    ),
    "digit_distribution": ToolSpec(
        tool_id="digit_distribution",
        display_name="数字分布检测",
        category="数字取证",
        description="尾数分布和 Benford 首位数字弱信号检查。",
        accepted_input_types=("raw_observation_table",),
        minimum_sample_size=30,
        default_enabled=False,
        reliability="弱信号",
        method_limitations="只适合样本量足够、变量类型合适的数值列；ID、百分比、评分、小样本和截断范围数据不适用。",
    ),
    "image_forensics": ToolSpec(
        tool_id="image_forensics",
        display_name="图像取证",
        category="图像",
        description="ELA、元数据、ORB copy-move 和感知哈希等图像弱信号检查。",
        accepted_input_types=("scientific_image", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="PIL",
        reliability="弱信号",
        method_limitations="图像取证结果不能单独作为强结论；重复纹理、压缩流程和排版软件都可能导致误报。",
    ),
    "reference_audit": ToolSpec(
        tool_id="reference_audit",
        display_name="参考文献核验",
        category="文献与外部信号",
        description="解析 DOI/PMID，并在显式启用时查询 Crossref、OpenAlex、NCBI 元数据和撤稿信号。",
        accepted_input_types=("reference_list", "paper_document", "plain_text", "apa_statistical_text"),
        default_enabled=False,
        reliability="稳定/外部查询需启用",
        method_limitations="默认不向外部 API 发送材料；外部元数据可能不完整，撤稿与争议信号需人工确认。",
    ),
    "citation_claim_check": ToolSpec(
        tool_id="citation_claim_check",
        display_name="引用支持关系辅助复核",
        category="文献与外部信号",
        description="抽取带引用的正文主张，生成需要人工或受控 RAG 复核的清单。",
        accepted_input_types=("reference_list", "paper_document", "plain_text", "apa_statistical_text"),
        default_enabled=False,
        reliability="辅助",
        method_limitations="轻量抽取不判断引用是否真正支持主张；必须保留证据片段并人工确认。",
    ),
    "image_extract": ToolSpec(
        tool_id="image_extract",
        display_name="图像抽取",
        category="图像",
        description="从 DOCX 或图片目录中发现/抽取 figure 和基础元数据。",
        accepted_input_types=("scientific_image", "scientific_figure", "paper_document"),
        default_enabled=False,
        reliability="稳定",
        method_limitations="PDF 图像抽取在当前版本仅作为后续能力记录；复杂版式需要人工复核。",
    ),
    "image_duplicate_internal": ToolSpec(
        tool_id="image_duplicate_internal",
        display_name="稿件内部重复图初筛",
        category="图像",
        description="使用多种本地图像指纹和 ORB 特征筛查同稿件内部高度相似图片。",
        accepted_input_types=("scientific_image", "scientific_figure", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="PIL",
        reliability="弱信号",
        method_limitations="只能提示重复/复用复核线索，不能证明篡改；复杂裁剪、低质量压缩和重复纹理可能影响结果。",
    ),
    "image_copy_move_internal": ToolSpec(
        tool_id="image_copy_move_internal",
        display_name="图像局部复制初筛",
        category="图像",
        description="使用本地 ORB 特征在单张图内部筛查疑似 copy-move 局部复制信号。",
        accepted_input_types=("scientific_image", "scientific_figure", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="cv2",
        reliability="弱信号",
        method_limitations="局部复制初筛对重复纹理、图表元素和压缩噪声敏感；命中区域必须由人工结合原图复核。",
    ),
    "image_metadata_audit": ToolSpec(
        tool_id="image_metadata_audit",
        display_name="图像元数据与质量初筛",
        category="图像",
        description="读取图像格式、尺寸、EXIF、色彩模式和亮度动态范围等基础元数据。",
        accepted_input_types=("scientific_image", "scientific_figure", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="PIL",
        reliability="辅助",
        method_limitations="元数据容易被清除或被软件重写，只能作为文件流程复核线索。",
    ),
    "western_blot_review_list": ToolSpec(
        tool_id="western_blot_review_list",
        display_name="Western blot复核清单",
        category="图像",
        description="识别 blot/gel 候选图并生成原始材料复核清单。",
        accepted_input_types=("scientific_image", "western_blot_or_gel_image", "scientific_figure"),
        default_enabled=False,
        reliability="辅助",
        method_limitations="基于文件名和材料类型生成清单，不做专业图像取证结论。",
    ),
    "papermill_light_signals": ToolSpec(
        tool_id="papermill_light_signals",
        display_name="论文工厂轻量信号",
        category="论文工厂",
        description="扫描 tortured phrases、模板化文本等轻量信号。",
        accepted_input_types=("plain_text", "apa_statistical_text", "paper_document"),
        default_enabled=False,
        reliability="弱信号",
        method_limitations="轻量文本信号不能替代跨论文数据库、投稿行为和作者网络审查。",
    ),
    "papermill_network_signals": ToolSpec(
        tool_id="papermill_network_signals",
        display_name="本地论文工厂跨库信号",
        category="论文工厂",
        description="基于本地 corpus 索引筛查文本、引用、作者机构和图像指纹相似性。",
        accepted_input_types=("project_manifest", "paper_document", "raw_file_bundle"),
        default_enabled=False,
        reliability="弱信号/需本地语料",
        method_limitations="跨库信号强依赖本地语料覆盖；相似模板、共同方法和同团队系列研究都可能产生正常相似。",
    ),
    "provenance_hash": ToolSpec(
        tool_id="provenance_hash",
        display_name="原始文件哈希存证",
        category="溯源",
        description="计算 SHA-256、文件大小和时间戳，生成版本链证据。",
        accepted_input_types=("raw_file_bundle", "project_manifest", "raw_observation_table", "paper_document", "scientific_image"),
        default_enabled=False,
        reliability="稳定",
        method_limitations="哈希只能证明文件后续未变化，不能证明实验真实发生或上传文件就是最早原始文件。",
    ),
    "provenance_chain_verify": ToolSpec(
        tool_id="provenance_chain_verify",
        display_name="哈希版本链核验",
        category="溯源",
        description="读取追加式 JSONL 账本并核验项目文件 matched/changed/missing/new 状态。",
        accepted_input_types=("raw_file_bundle", "project_manifest"),
        default_enabled=False,
        reliability="稳定",
        method_limitations="版本链只能证明登记后的文件完整性变化，不能证明登记前材料来源真实。",
    ),
    "code_rerun_audit": ToolSpec(
        tool_id="code_rerun_audit",
        display_name="分析代码复跑审计",
        category="代码复核",
        description="只读扫描 R/Python/Stata/SPSS/SAS 脚本中的路径、输入、剔除和显著性筛选线索。",
        accepted_input_types=("analysis_code", "project_manifest"),
        default_enabled=False,
        reliability="辅助",
        method_limitations="当前版本不执行脚本，只检查复跑准备风险；关键统计量复算需隔离环境和完整输入。",
    ),
}


def tool_specs_payload() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in TOOL_REGISTRY.values()]


def default_selected_tools() -> list[str]:
    return [tool_id for tool_id, spec in TOOL_REGISTRY.items() if spec.default_enabled]


def normalize_selected_tools(raw: list[str] | None) -> set[str]:
    selected = set(default_selected_tools() if raw is None else raw)
    return {tool_id for tool_id in selected if tool_id in TOOL_REGISTRY}


def rscript_available() -> bool:
    return shutil.which("Rscript") is not None


def r_package_available(package: str) -> bool:
    if not rscript_available():
        return False
    cmd = ["Rscript", "-e", f"quit(status = ifelse(requireNamespace('{package}', quietly=TRUE), 0, 1))"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15).returncode == 0


def dependency_status(spec: ToolSpec) -> tuple[str, str]:
    if spec.r_package:
        if not rscript_available():
            return "missing_r", "未检测到 Rscript；请先安装 R，并确保 Rscript 在 PATH 中。"
        if not r_package_available(spec.r_package):
            return "missing_r_package", f"缺少 R 包 {spec.r_package}；请在 R 中运行 install.packages('{spec.r_package}')。"
        return "ready", ""
    if spec.dependency_module and importlib.util.find_spec(spec.dependency_module) is None:
        return "dependency_missing", f"缺少 Python 依赖模块 {spec.dependency_module}，已记录但不运行。"
    return "ready", ""


def normalize_name(name: Any) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"\s+", "", text)
    return text.replace("_", "").replace("-", "")


def columns_matching(df: pd.DataFrame, patterns: list[str]) -> list[str]:
    matches: list[str] = []
    for col in df.columns:
        normalized = normalize_name(col)
        raw = str(col).lower()
        if any(re.search(pattern, normalized) or re.search(pattern, raw) for pattern in patterns):
            matches.append(str(col))
    return matches


def classify_table(df: pd.DataFrame, source_suffix: str = "") -> dict[str, Any]:
    suffix = source_suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        return {"primary_type": "scientific_image", "input_types": ["scientific_image"], "signals": {}}

    n_cols = columns_matching(df, [r"^n$", r"样本量", r"例数", r"人数", r"samplesize", r"cases?"])
    mean_cols = columns_matching(df, [r"^mean$", r"^means$", r"均值", r"均数", r"平均值", r"平均数"])
    sd_cols = columns_matching(df, [r"^sd$", r"^std$", r"标准差", r"stdev"])
    se_cols = columns_matching(df, [r"^se$", r"^sem$", r"标准误", r"standarderror"])
    ci_cols = columns_matching(df, [r"(^|[^a-z])ci([^a-z]|$)", r"95%ci", r"置信区间", r"下限", r"上限", r"lcl", r"ucl"])
    p_cols = columns_matching(df, [r"^p$", r"pvalue", r"p值", r"^pval"])
    stat_cols = columns_matching(df, [r"^t$", r"^f$", r"chi", r"χ", r"卡方", r"^df$", r"自由度"])
    score_cols = columns_matching(df, [r"score", r"likert", r"scale", r"评分", r"量表", r"总分"])

    summary_score = bool(n_cols and mean_cols and score_cols)
    summary_stats = bool(n_cols and (mean_cols or sd_cols or se_cols or ci_cols or p_cols or stat_cols))
    p_collection = bool(p_cols and len(df) >= 10 and not (mean_cols or sd_cols or se_cols or ci_cols))

    if summary_score:
        primary = "likert_or_integer_scale_summary"
    elif summary_stats:
        primary = "summary_statistics_table"
    elif p_collection:
        primary = "p_value_collection"
    else:
        primary = "raw_observation_table"

    input_types = [primary]
    if summary_stats and primary != "summary_statistics_table":
        input_types.append("summary_statistics_table")
    if p_collection and "p_value_collection" not in input_types:
        input_types.append("p_value_collection")

    return {
        "primary_type": primary,
        "input_types": input_types,
        "signals": {
            "n_columns": n_cols,
            "mean_columns": mean_cols,
            "sd_columns": sd_cols,
            "se_columns": se_cols,
            "ci_columns": ci_cols,
            "p_columns": p_cols,
            "statistic_columns": stat_cols,
            "score_columns": score_cols,
        },
    }


APA_STAT_RE = re.compile(
    r"\b(?:t|F|r|z|Q)\s*[\(（][^)）]{1,40}[\)）]\s*[=<>]\s*-?\d+(?:\.\d+)?|[χx]\s*[²2]\s*[\(（][^)）]{1,40}[\)）]\s*[=<>]\s*\d",
    re.IGNORECASE,
)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
PMID_RE = re.compile(r"\bPMID\s*:?\s*\d{5,10}\b", re.I)


def classify_text(text: str) -> dict[str, Any]:
    has_apa = bool(APA_STAT_RE.search(text or ""))
    has_reference = bool(DOI_RE.search(text or "") or PMID_RE.search(text or "") or re.search(r"^\s*(references|参考文献)\s*$", text or "", re.I | re.M))
    primary = "apa_statistical_text" if has_apa else ("reference_list" if has_reference else "plain_text")
    input_types = []
    if has_apa:
        input_types.append("apa_statistical_text")
    if has_reference:
        input_types.append("reference_list")
    if not input_types:
        input_types.append("plain_text")
    return {
        "primary_type": primary,
        "input_types": input_types,
        "signals": {"apa_statistical_expressions": has_apa, "reference_identifiers": has_reference},
    }


def route_tool(
    spec: ToolSpec,
    selected_tools: set[str],
    input_types: list[str],
    row_count: int,
    available_fields: list[str] | None = None,
) -> RoutingDecision:
    available_fields = available_fields or []
    selected = spec.tool_id in selected_tools
    matched = next((item for item in input_types if item in spec.accepted_input_types), "")
    if not selected:
        return RoutingDecision(
            spec.tool_id, spec.display_name, spec.category, False, False, False, "not_selected",
            "用户未勾选该工具包，本次不参与检测。", matched, available_fields, spec.method_limitations,
            spec.detector_runtime, "not_selected", spec.reliability,
        )
    if not matched:
        return RoutingDecision(
            spec.tool_id, spec.display_name, spec.category, True, False, False, "not_applicable",
            "当前数据类型不属于该工具包的适用范围。", "", available_fields, spec.method_limitations,
            spec.detector_runtime, "not_applicable", spec.reliability,
        )
    if spec.minimum_sample_size and row_count < spec.minimum_sample_size:
        return RoutingDecision(
            spec.tool_id, spec.display_name, spec.category, True, False, False, "insufficient_material",
            f"样本量/行数不足：需要至少 {spec.minimum_sample_size} 行，当前 {row_count} 行。",
            matched, available_fields, spec.method_limitations, spec.detector_runtime, "insufficient_material", spec.reliability,
        )
    dep_status, dep_reason = dependency_status(spec)
    if dep_status != "ready":
        return RoutingDecision(
            spec.tool_id, spec.display_name, spec.category, True, False, False, dep_status,
            dep_reason, matched, available_fields, spec.method_limitations, spec.detector_runtime, dep_status, spec.reliability,
        )
    return RoutingDecision(
        spec.tool_id, spec.display_name, spec.category, True, True, False, "ready", "",
        matched, available_fields, spec.method_limitations, spec.detector_runtime, "ready", spec.reliability,
    )


def route_all_tools(
    selected_tools: set[str],
    input_types: list[str],
    row_count: int,
    available_fields: list[str] | None = None,
) -> dict[str, RoutingDecision]:
    return {
        tool_id: route_tool(spec, selected_tools, input_types, row_count, available_fields)
        for tool_id, spec in TOOL_REGISTRY.items()
    }


def source_kind(path: Path) -> str:
    if path.is_dir():
        return "project"
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "manifest"
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        return "image"
    if suffix in {".py", ".r", ".do", ".sps", ".sas"}:
        return "code"
    if suffix in {".pdf", ".docx"}:
        return "document"
    return "table"
