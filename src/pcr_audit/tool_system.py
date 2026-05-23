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
    reliability: str = "Stable"
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
    reliability: str = "Stable"


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "raw_data_rules": ToolSpec(
        tool_id="raw_data_rules",
        display_name="Basic Table Rules",
        category="Raw Data",
        description="Empty tables, missing values, duplicate/highly similar rows, digit distribution, inter-column relationships, high-frequency values, fixed steps, consecutive repeats, outliers, and other Python basic rules.",
        accepted_input_types=("raw_observation_table", "figure_source_data"),
        minimum_sample_size=2,
        default_enabled=True,
        reliability="Stable",
        method_limitations="Detects data shape, digit distribution, and inter-column relationship anomalies; study design variables, instrument thresholds, batch export formats, and legitimate derived variables may trigger false positives.",
    ),
    "r_scrutiny": ToolSpec(
        tool_id="r_scrutiny",
        display_name="R scrutiny",
        category="R Statistical Consistency",
        description="Run GRIM, GRIMMER, DEBIT, and other summary statistic feasibility checks via R scrutiny.",
        accepted_input_types=("summary_statistics_table", "continuous_measure_summary", "likert_or_integer_scale_summary"),
        default_enabled=False,
        r_package="scrutiny",
        detector_runtime="r",
        reliability="Requires R",
        method_limitations="Applies to reported means, SDs, Ns, proportions, or binary data summaries; requires confirmation of scale range, rounding rules, and variable types.",
    ),
    "r_statcheck": ToolSpec(
        tool_id="r_statcheck",
        display_name="R statcheck",
        category="R In-text Statistics",
        description="Check consistency between APA statistical expressions and p-values in manuscript text via R statcheck.",
        accepted_input_types=("apa_statistical_text",),
        default_enabled=False,
        r_package="statcheck",
        detector_runtime="r",
        reliability="Requires R",
        method_limitations="Only applies to APA/NHST expressions parseable by statcheck; Chinese full-width punctuation, non-standard statistical reporting, and extraction failures reduce coverage.",
    ),
    "r_rsprite2": ToolSpec(
        tool_id="r_rsprite2",
        display_name="R rsprite2",
        category="R Advanced Review",
        description="Run SPRITE discrete distribution reconstruction via R rsprite2, suitable for expert-level review.",
        accepted_input_types=("likert_or_integer_scale_summary",),
        default_enabled=False,
        r_package="rsprite2",
        detector_runtime="r",
        reliability="Advanced/Requires R",
        method_limitations="Requires clear scale range, precision, and constraints; high interpretation cost, intended as an expert review entry point only.",
    ),
    "crosscheck": ToolSpec(
        tool_id="crosscheck",
        display_name="Row-level Math Cross-check",
        category="Statistical Consistency",
        description="Run pure mathematical cross-checks on summary statistics tables: SE/SD/sqrt(N), CI/SE, percent/count/N, p/t/df.",
        accepted_input_types=("summary_statistics_table", "continuous_measure_summary", "likert_or_integer_scale_summary"),
        default_enabled=False,
        reliability="Stable",
        method_limitations="Only verifies mathematical consistency of derived statistics within a table; cannot determine whether original observations are real or whether the statistical model is appropriate.",
    ),
    "p_value_distribution": ToolSpec(
        tool_id="p_value_distribution",
        display_name="P-value Set Weak Signal Detection",
        category="Statistical Consistency",
        description="Check domain validity and marginally significant p-value clustering in pure p-value collections.",
        accepted_input_types=("p_value_collection",),
        minimum_sample_size=10,
        default_enabled=False,
        reliability="Weak Signal",
        method_limitations="Only checks p-value collection shape; does not know test family, direction, correction method, or full result space; marginal clustering is only a selective reporting review clue.",
    ),
    "image_forensics": ToolSpec(
        tool_id="image_forensics",
        display_name="Image Forensics",
        category="Image",
        description="ELA, metadata, ORB copy-move, and perceptual hash image weak signal checks.",
        accepted_input_types=("scientific_image", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="PIL",
        reliability="Weak Signal",
        method_limitations="Image forensics results cannot stand alone as strong conclusions; repeated textures, compression pipelines, and layout software can all cause false positives.",
    ),
    "reference_audit": ToolSpec(
        tool_id="reference_audit",
        display_name="Reference Audit",
        category="Literature & External Signals",
        description="Parse DOI/PMID and, when explicitly enabled, query Crossref, OpenAlex, NCBI metadata and retraction signals.",
        accepted_input_types=("reference_list", "paper_document", "plain_text", "apa_statistical_text"),
        default_enabled=False,
        reliability="Stable/External lookup requires opt-in",
        method_limitations="Does not send materials to external APIs by default; external metadata may be incomplete; retraction and dispute signals require human confirmation.",
    ),
    "citation_claim_check": ToolSpec(
        tool_id="citation_claim_check",
        display_name="Citation Support Review",
        category="Literature & External Signals",
        description="Extract in-text claims with citations and generate a checklist for human or controlled RAG review.",
        accepted_input_types=("reference_list", "paper_document", "plain_text", "apa_statistical_text"),
        default_enabled=False,
        reliability="Auxiliary",
        method_limitations="Lightweight extraction does not judge whether citations actually support claims; must preserve evidence snippets for human confirmation.",
    ),
    "image_extract": ToolSpec(
        tool_id="image_extract",
        display_name="Image Extraction",
        category="Image",
        description="Discover/extract figures and basic metadata from image files, DOCX, or PDF; PDF is best-effort.",
        accepted_input_types=("scientific_image", "scientific_figure", "paper_document"),
        default_enabled=False,
        reliability="Stable",
        method_limitations="Image file and DOCX extraction is relatively stable; PDF image extraction is best-effort; for complex layouts, provide original images or DOCX.",
    ),
    "image_duplicate_internal": ToolSpec(
        tool_id="image_duplicate_internal",
        display_name="Internal Duplicate Image Screening",
        category="Image",
        description="Screen for highly similar images within the same manuscript using multiple local image fingerprints and ORB features.",
        accepted_input_types=("scientific_image", "scientific_figure", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="PIL",
        reliability="Weak Signal",
        method_limitations="Only flags duplicate/reuse review clues; does not make determinations; complex cropping, low-quality compression, and repeated textures may affect results.",
    ),
    "image_copy_move_internal": ToolSpec(
        tool_id="image_copy_move_internal",
        display_name="Image Copy-Move Screening",
        category="Image",
        description="Screen for suspected copy-move local duplication signals within single images using local ORB features.",
        accepted_input_types=("scientific_image", "scientific_figure", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="cv2",
        reliability="Weak Signal",
        method_limitations="Local copy-move screening is sensitive to repeated textures, chart elements, and compression noise; hit regions must be reviewed by a human against the original image.",
    ),
    "image_metadata_audit": ToolSpec(
        tool_id="image_metadata_audit",
        display_name="Image Metadata & Quality Screening",
        category="Image",
        description="Read basic metadata: image format, dimensions, EXIF, color mode, and brightness dynamic range.",
        accepted_input_types=("scientific_image", "scientific_figure", "western_blot_or_gel_image"),
        default_enabled=False,
        dependency_module="PIL",
        reliability="Auxiliary",
        method_limitations="Metadata is easily cleared or rewritten by software; only serves as a file workflow review clue.",
    ),
    "western_blot_review_list": ToolSpec(
        tool_id="western_blot_review_list",
        display_name="Western Blot Review Checklist",
        category="Image",
        description="Identify blot/gel candidate images and generate an original material review checklist.",
        accepted_input_types=("scientific_image", "western_blot_or_gel_image", "scientific_figure"),
        default_enabled=False,
        reliability="Auxiliary",
        method_limitations="Generates a checklist based on filenames and material types; does not make professional image forensics conclusions.",
    ),
    "papermill_light_signals": ToolSpec(
        tool_id="papermill_light_signals",
        display_name="Paper Mill Light Signals",
        category="Paper Mill",
        description="Scan for light signals such as tortured phrases and templated text.",
        accepted_input_types=("plain_text", "apa_statistical_text", "paper_document"),
        default_enabled=False,
        reliability="Weak Signal",
        method_limitations="Lightweight text signals cannot replace cross-paper database, submission behavior, and author network review.",
    ),
    "papermill_network_signals": ToolSpec(
        tool_id="papermill_network_signals",
        display_name="Local Paper Mill Cross-Corpus Signals",
        category="Paper Mill",
        description="Screen for text, citation, author affiliation, and image fingerprint similarity based on local corpus index.",
        accepted_input_types=("project_manifest", "paper_document", "raw_file_bundle"),
        default_enabled=False,
        reliability="Weak Signal/Requires Local Corpus",
        method_limitations="Cross-corpus signals heavily depend on local corpus coverage; similar templates, shared methods, and serial studies from the same team can all produce normal similarity.",
    ),
    "provenance_hash": ToolSpec(
        tool_id="provenance_hash",
        display_name="Original File Hash Record",
        category="Provenance",
        description="Compute SHA-256, file size, and timestamp to generate version chain evidence.",
        accepted_input_types=("raw_file_bundle", "project_manifest", "raw_observation_table", "paper_document", "scientific_image"),
        default_enabled=False,
        reliability="Stable",
        method_limitations="Hashes only prove that files have not changed subsequently; they cannot prove that experiments actually occurred or that uploaded files are the earliest originals.",
    ),
    "provenance_chain_verify": ToolSpec(
        tool_id="provenance_chain_verify",
        display_name="Hash Version Chain Verification",
        category="Provenance",
        description="Read the append-only JSONL ledger and verify project file matched/changed/missing/new status.",
        accepted_input_types=("raw_file_bundle", "project_manifest"),
        default_enabled=False,
        reliability="Stable",
        method_limitations="Version chains can only prove integrity changes of registered files; they cannot prove the authenticity of material sources before registration.",
    ),
    "code_rerun_audit": ToolSpec(
        tool_id="code_rerun_audit",
        display_name="Analysis Code Rerun Audit",
        category="Code Review",
        description="Lightweight pattern/regex scan of R/Python/Stata/SPSS/SAS scripts for path, input, exclusion, and significance filtering clues.",
        accepted_input_types=("analysis_code", "project_manifest"),
        default_enabled=False,
        reliability="Auxiliary",
        method_limitations="This tool only read-scans rerun readiness risks; Python AST and stronger multi-language parsing can be enhanced later. Actual Python/R execution is handled by code_rerun_execute in a temporary project copy.",
    ),
    "code_rerun_execute": ToolSpec(
        tool_id="code_rerun_execute",
        display_name="Analysis Script Sandbox Rerun",
        category="Code Review",
        description="Execute Python/R scripts in a temporary project copy, capture output, and feed generated tables into cross-material reconciliation; Stata/SPSS/SAS are recorded as info with manual rerun prompts.",
        accepted_input_types=("analysis_code", "project_manifest"),
        default_enabled=False,
        reliability="Auxiliary/Local Sandbox",
        method_limitations="Local temporary directory isolation cannot replace strong security containers; script failures, timeouts, or missing packages are only recorded as info.",
    ),
    "data_trace_crosscheck": ToolSpec(
        tool_id="data_trace_crosscheck",
        display_name="Cross-Material Data Reconciliation",
        category="Statistical Consistency",
        description="Deterministically reconcile manuscript/supplement summary statistics, raw data auto-aggregations, and script output tables.",
        accepted_input_types=("project_manifest",),
        default_enabled=False,
        reliability="Stable",
        method_limitations="Only reconciles reliably matchable variables and statistics; complex groupings, derived variables, and extraction errors require human confirmation.",
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
            return "missing_r", "Rscript not detected; please install R and ensure Rscript is in PATH."
        if not r_package_available(spec.r_package):
            return "missing_r_package", f"Missing R package {spec.r_package}; run install.packages('{spec.r_package}') in R."
        return "ready", ""
    if spec.dependency_module and importlib.util.find_spec(spec.dependency_module) is None:
        return "dependency_missing", f"Missing Python dependency module {spec.dependency_module}; recorded but not run."
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

    n_cols = columns_matching(df, [r"^n$", r"^sample[_ ]?size$", r"^cases?$", r"^number$", r"samplesize", r"样本量", r"例数", r"人数"])
    mean_cols = columns_matching(df, [r"^mean$", r"^means$", r"^average$", r"均值", r"均数", r"平均值", r"平均数"])
    sd_cols = columns_matching(df, [r"^sd$", r"^std$", r"^stdev$", r"标准差", r"stdev"])
    se_cols = columns_matching(df, [r"^se$", r"^sem$", r"^standard[_ ]?error$", r"标准误", r"standarderror"])
    ci_cols = columns_matching(df, [r"(^|[^a-z])ci([^a-z]|$)", r"95%ci", r"^lcl$", r"^ucl$", r"^lower$", r"^upper$", r"置信区间", r"下限", r"上限", r"lcl", r"ucl"])
    p_cols = columns_matching(df, [r"^p$", r"^p[_ ]?value$", r"pvalue", r"^pval", r"p值"])
    stat_cols = columns_matching(df, [r"^t$", r"^f$", r"^chi", r"χ", r"^df$", r"^dof$", r"卡方", r"自由度"])
    score_cols = columns_matching(df, [r"score", r"likert", r"scale", r"rating", r"评分", r"量表", r"总分"])

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
    has_reference = bool(DOI_RE.search(text or "") or PMID_RE.search(text or "") or re.search(r"^\s*(references|bibliography|参考文献|参考|引用)\s*$", text or "", re.I | re.M))
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
            "User did not select this tool; it will not participate in this run.", matched, available_fields, spec.method_limitations,
            spec.detector_runtime, "not_selected", spec.reliability,
        )
    if not matched:
        return RoutingDecision(
            spec.tool_id, spec.display_name, spec.category, True, False, False, "not_applicable",
            "Current data type is outside this tool's applicable scope.", "", available_fields, spec.method_limitations,
            spec.detector_runtime, "not_applicable", spec.reliability,
        )
    if spec.minimum_sample_size and row_count < spec.minimum_sample_size:
        return RoutingDecision(
            spec.tool_id, spec.display_name, spec.category, True, False, False, "insufficient_material",
            f"Insufficient sample/row count: requires at least {spec.minimum_sample_size} rows, currently {row_count} rows.",
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
