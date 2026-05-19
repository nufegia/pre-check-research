from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pcr_audit.models import Finding, TableResult
from pcr_audit.product.common import (
    AUTHOR_LINE_RE,
    DOC_SUFFIXES,
    DOI_RE,
    EMAIL_RE,
    IMAGE_SUFFIXES,
    INSTITUTION_LINE_RE,
    PMID_RE,
    TEXT_TOKEN_RE,
    AuditConfig,
    _now_iso,
    finding,
    is_audit_material_path,
    iter_audit_files,
)
from pcr_audit.product.image_audit import _hamming, image_fingerprints
from pcr_audit.product.project_manifest import parse_project_spec
from pcr_audit.product.reference_audit import _extract_reference_text

def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TEXT_TOKEN_RE.findall(text or "")]


def _shingles(tokens: list[str], width: int = 5) -> set[str]:
    if len(tokens) < width:
        return set(tokens)
    return {" ".join(tokens[idx: idx + width]) for idx in range(len(tokens) - width + 1)}


def _simhash(features: set[str]) -> int:
    vector = [0] * 64
    for feature in features:
        digest = int(hashlib.sha256(feature.encode("utf-8")).hexdigest()[:16], 16)
        for bit in range(64):
            vector[bit] += 1 if digest & (1 << bit) else -1
    value = 0
    for bit, score in enumerate(vector):
        if score >= 0:
            value |= 1 << bit
    return value


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def _extract_metadata_from_text(text: str) -> dict[str, Any]:
    authors: set[str] = set()
    institutions: set[str] = set()
    for match in AUTHOR_LINE_RE.finditer(text):
        authors.update(item.strip().lower() for item in re.split(r"[,;，；]", match.group("value")) if item.strip())
    for match in INSTITUTION_LINE_RE.finditer(text):
        institutions.update(item.strip().lower() for item in re.split(r"[,;，；]", match.group("value")) if item.strip())
    return {
        "authors": sorted(authors),
        "institutions": sorted(institutions),
        "email_domains": sorted({match.group(1).lower() for match in EMAIL_RE.finditer(text)}),
        "dois": sorted({doi.rstrip(".,);]").lower() for doi in DOI_RE.findall(text)}),
        "pmids": sorted(PMID_RE.findall(text)),
    }


def _project_texts(source: Path, config: AuditConfig | None = None) -> list[tuple[Path, str]]:
    spec, _config = parse_project_spec(source)
    docs = [m.path for m in spec.materials if m.role in {"manuscript", "references", "supplement"} and m.path.suffix.lower() in DOC_SUFFIXES]
    if not docs and source.is_file() and source.suffix.lower() in DOC_SUFFIXES:
        docs = [source]
    texts = []
    for doc in docs[:20]:
        text = _extract_reference_text(doc, config)
        if text:
            texts.append((doc, text))
    return texts


def _image_index_entries(source: Path) -> list[dict[str, Any]]:
    spec, _config = parse_project_spec(source)
    images = [m.path for m in spec.materials if m.role in {"figures", "image"} or m.path.suffix.lower() in IMAGE_SUFFIXES]
    entries = []
    for path in images[:200]:
        fingerprints = image_fingerprints(path)
        if fingerprints:
            entries.append({"path": str(path), "name": path.name, "fingerprints": {key: value["hex"] for key, value in fingerprints.items()}})
    return entries


def project_corpus_features(source: Path, config: AuditConfig | None = None) -> dict[str, Any]:
    texts = _project_texts(source, config)
    combined = "\n".join(text for _path, text in texts)
    tokens = _tokens(combined)
    shingles = _shingles(tokens)
    metadata = _extract_metadata_from_text(combined)
    title = ""
    if combined:
        title = next((line.strip("# ").strip() for line in combined.splitlines() if line.strip()), "")
    return {
        "project_id": source.stem if source.is_file() else source.name,
        "source": str(source),
        "title": title,
        "text_chars": len(combined),
        "token_count": len(tokens),
        "shingles": sorted(shingles)[:5000],
        "simhash": f"{_simhash(shingles):016x}" if shingles else "",
        "metadata": metadata,
        "images": _image_index_entries(source),
        "indexed_at": _now_iso(),
    }


def _corpus_project_paths(source: Path) -> list[Path]:
    if source.is_file() and source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        raw_items = payload.get("projects") or payload.get("corpus") or payload.get("items") or []
        base = source.parent
        paths = []
        for item in raw_items:
            raw_path = item if isinstance(item, str) else item.get("path", "")
            path = Path(raw_path).expanduser()
            paths.append((path if path.is_absolute() else base / path).resolve())
        return paths
    if source.is_dir():
        candidates = [path for path in source.iterdir() if path.is_dir() and is_audit_material_path(path, source)]
        if (source / "pcr-project.json").exists():
            return [source]
        return sorted(path for path in candidates if (path / "pcr-project.json").exists() or any(child.suffix.lower() in DOC_SUFFIXES | IMAGE_SUFFIXES for child in iter_audit_files(path)))
    return [source]


def build_corpus_index(source: Path) -> dict[str, Any]:
    projects = _corpus_project_paths(source)
    return {
        "tool_id": "papermill_network_signals",
        "tool_name": "本地论文工厂跨库信号",
        "detector_runtime": "python",
        "dependency_status": "ready",
        "source": str(source),
        "built_at": _now_iso(),
        "projects": [project_corpus_features(project) for project in projects if project.exists()],
    }


def _hex_hamming(left: str, right: str) -> int:
    if not left or not right:
        return 999
    return _hamming(int(left, 16), int(right, 16))


def analyze_papermill_network_signals(project: Path, index_payload: dict[str, Any] | None = None) -> TableResult:
    findings: list[Finding] = []
    current = project_corpus_features(project)
    projects = list((index_payload or {}).get("projects") or [])
    if not projects:
        findings.append(
            finding(
                str(project), "info", "本地跨库语料缺失", "corpus",
                "未提供本地 corpus 索引，跨稿件论文工厂信号未运行。",
                "使用 pcr-audit corpus build 生成 corpus-index.json 后再执行 screen。",
                "该提示不计入风险；无本地语料不能说明无论文工厂风险。",
                tool_id="papermill_network_signals", tool_name="本地论文工厂跨库信号",
                input_type="project_manifest", dependency_status="insufficient_material",
            )
        )
        return TableResult("papermill_network_signals", 0, 0, findings)
    current_shingles = set(current.get("shingles") or [])
    current_meta = current.get("metadata") or {}
    for other in projects:
        if str(other.get("source")) == str(project):
            continue
        other_shingles = set(other.get("shingles") or [])
        text_jaccard = _jaccard(current_shingles, other_shingles)
        sim_distance = _hex_hamming(str(current.get("simhash") or ""), str(other.get("simhash") or ""))
        if text_jaccard >= 0.35 or sim_distance <= 8:
            findings.append(
                finding(
                    str(project), "medium", "跨稿件文本高度相似", str(other.get("project_id") or other.get("source")),
                    "当前项目与本地语料中的另一稿件存在较高文本模板相似性。",
                    f"jaccard={text_jaccard:.3f}; simhash_distance={sim_distance}; other={other.get('source')}",
                    "人工比较摘要/方法/结果段，确认是否为合理系列研究、模板写作或异常复用。",
                    tool_id="papermill_network_signals", tool_name="本地论文工厂跨库信号",
                    input_type="project_manifest",
                )
            )
        other_meta = other.get("metadata") or {}
        doi_overlap = set(current_meta.get("dois") or []).intersection(other_meta.get("dois") or [])
        author_overlap = set(current_meta.get("authors") or []).intersection(other_meta.get("authors") or [])
        domain_overlap = set(current_meta.get("email_domains") or []).intersection(other_meta.get("email_domains") or [])
        if len(doi_overlap) >= 3:
            findings.append(
                finding(
                    str(project), "low", "跨稿件引用列表重叠", str(other.get("project_id") or other.get("source")),
                    "当前项目与本地语料中的另一稿件共享多个 DOI，需复核引用网络是否合理。",
                    f"overlap_doi_count={len(doi_overlap)}; examples={', '.join(sorted(doi_overlap)[:5])}",
                    "比较研究主题、引用语境和参考文献来源，排除同模板文献堆叠。",
                    tool_id="papermill_network_signals", tool_name="本地论文工厂跨库信号",
                    input_type="project_manifest",
                )
            )
        if len(author_overlap) >= 2 or domain_overlap.intersection({"qq.com", "163.com", "126.com", "gmail.com"}):
            findings.append(
                finding(
                    str(project), "low", "作者/邮箱域网络重叠", str(other.get("project_id") or other.get("source")),
                    "本地语料中存在作者或邮箱域重叠，需结合机构和投稿背景复核。",
                    f"author_overlap={', '.join(sorted(author_overlap)[:5])}; email_domain_overlap={', '.join(sorted(domain_overlap)[:5])}",
                    "确认是否为同一团队系列研究、通讯作者邮箱习惯或异常批量投稿线索。",
                    tool_id="papermill_network_signals", tool_name="本地论文工厂跨库信号",
                    input_type="project_manifest",
                )
            )
        for image in current.get("images") or []:
            for other_image in other.get("images") or []:
                distances = []
                for key, value in (image.get("fingerprints") or {}).items():
                    other_value = (other_image.get("fingerprints") or {}).get(key)
                    if other_value:
                        distances.append((key, _hex_hamming(value, other_value)))
                if distances and min(distance for _key, distance in distances) <= 6:
                    best = min(distances, key=lambda item: item[1])
                    findings.append(
                        finding(
                            str(project), "medium", "跨稿件图像指纹相似", f"{image.get('name')} / {other_image.get('name')}",
                            "当前项目图片与本地语料图片存在高度相似图像指纹。",
                            f"best_hash={best[0]}:{best[1]}; other_project={other.get('source')}; other_image={other_image.get('path')}",
                            "人工核对图注、实验条件和原始图，确认是否为合理复用、公共示意图或异常重复。",
                            tool_id="papermill_network_signals", tool_name="本地论文工厂跨库信号",
                            input_type="project_manifest",
                        )
                    )
    if not findings:
        findings.append(
            finding(
                str(project), "info", "本地跨库信号", "corpus",
                "本地 corpus 筛查完成，未发现达到阈值的文本、引用、作者或图像相似信号。",
                f"indexed_projects={len(projects)}; current_tokens={current.get('token_count')}",
                "该结果只覆盖提供的本地语料，不代表外部数据库无相似稿件。",
                tool_id="papermill_network_signals", tool_name="本地论文工厂跨库信号",
                input_type="project_manifest",
            )
        )
    return TableResult("papermill_network_signals", len(projects), 0, findings)
