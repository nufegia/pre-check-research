from __future__ import annotations

import hashlib
import json
import math
import os
import re
import uuid
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import numpy as np

from pcr_audit.io import read_text_source
from pcr_audit.models import Finding, TableResult, enrich_finding_explanation

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
DOC_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
DATA_SUFFIXES = {".csv", ".xlsx", ".xls"}
CODE_SUFFIXES = {".py", ".r", ".R", ".do", ".sps", ".sas"}
MATERIAL_ROLES = {"manuscript", "raw_data", "analysis_code", "figures", "supplement", "references", "image", "unknown"}
SYSTEM_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SYSTEM_DIR_NAMES = {".git", ".pcr", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
PMID_RE = re.compile(r"\bPMID\s*:?\s*(\d{5,10})\b", re.I)
REFERENCE_LINE_RE = re.compile(r"^\s*(?:\[\d+\]|\d+\.|\(\d+\))?\s*(?P<body>.{25,})$", re.M)
CLAIM_WITH_CITATION_RE = re.compile(r"(?P<claim>[^.\n]{30,240}?\s*(?:\[[0-9,;\-\s]+\]|\([A-Za-z][^)]+,\s*\d{4}\)))")
TORTURED_PHRASES = {
    "counterfeit consciousness": "artificial intelligence",
    "bosom peril": "breast cancer",
    "colossal information": "big data",
    "fake treatment": "placebo",
    "irregular woodland": "random forest",
    "profound neural organization": "deep neural network",
    "man-made brainpower": "artificial intelligence",
}

TEXT_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.I)
AUTHOR_LINE_RE = re.compile(r"^\s*(?:authors?|作者)\s*[:：]\s*(?P<value>.+)$", re.I | re.M)
INSTITUTION_LINE_RE = re.compile(r"^\s*(?:affiliations?|institutions?|单位|机构)\s*[:：]\s*(?P<value>.+)$", re.I | re.M)


@dataclass
class AuditConfig:
    external_lookups: bool = False
    grobid_url: str = ""
    contact_email: str = ""
    lookup_cache_dir: Path | None = None


@dataclass
class Material:
    path: Path
    role: str = "unknown"
    declared_path: str = ""


@dataclass
class ProjectSpec:
    source: Path
    project_id: str = ""
    title: str = ""
    materials: list[Material] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_audit_material_path(path: Path, root: Path | None = None) -> bool:
    """Return False for hidden/system paths that should not enter audit scope."""
    try:
        parts = path.relative_to(root).parts if root is not None else path.parts
    except ValueError:
        parts = path.parts
    for part in parts:
        if part in SYSTEM_FILE_NAMES or part in SYSTEM_DIR_NAMES:
            return False
        if part.startswith("."):
            return False
    return True


def iter_audit_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and is_audit_material_path(path, root))


def finding(
    table: str,
    level: str,
    check: str,
    target: str,
    summary: str,
    evidence: str,
    suggestion: str,
    detail: str = "",
    tool_id: str = "unknown",
    tool_name: str = "Unknown",
    module: str = "product",
    input_type: str = "unknown",
    detector_runtime: str = "python",
    dependency_status: str = "ready",
    location: str = "",
    calculation_trace: str = "",
    external_records: str = "",
    confidence_basis: str = "",
) -> Finding:
    item = Finding(
        table=table,
        level=level,
        check=check,
        target=target,
        summary=summary,
        evidence=evidence,
        detail=detail,
        suggestion=suggestion,
        tool_id=tool_id,
        tool_name=tool_name,
        module=module,
        input_type=input_type,
        detector_runtime=detector_runtime,
        dependency_status=dependency_status,
        location=location or table,
        calculation_trace=calculation_trace,
        external_records=external_records,
        confidence_basis=confidence_basis,
    )
    enrich_finding_explanation(item)
    return item


def _http_json(url: str, timeout: float = 8.0, contact_email: str = "") -> dict[str, Any] | None:
    user_agent = f"pcr-audit/1.0.1 ({contact_email})" if contact_email else "pcr-audit/1.0.1"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _external_enabled(config: AuditConfig | None = None) -> bool:
    if config is not None:
        return bool(config.external_lookups)
    return os.environ.get("PCR_ENABLE_EXTERNAL_LOOKUPS", "").lower() in {"1", "true", "yes"}


def _env_config(workdir: Path | None = None) -> AuditConfig:
    return AuditConfig(
        external_lookups=_external_enabled(None),
        grobid_url=os.environ.get("PCR_GROBID_URL", ""),
        contact_email=os.environ.get("PCR_CONTACT_EMAIL", ""),
        lookup_cache_dir=(workdir / "lookup-cache") if workdir else None,
    )


def _cache_key(service: str, identifier: str) -> str:
    digest = hashlib.sha256(f"{service}:{identifier}".encode("utf-8")).hexdigest()[:24]
    return f"{service}-{digest}.json"


def _cached_lookup(
    service: str,
    identifier: str,
    url: str,
    config: AuditConfig,
    summary_fn,
) -> tuple[dict[str, Any] | None, str, bool]:
    cache_dir = config.lookup_cache_dir
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / _cache_key(service, identifier)
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return payload.get("response"), f"{service} cache_hit status={payload.get('status')} summary={payload.get('summary', '')}", True
    else:
        cache_path = None
    record: dict[str, Any] = {
        "service": service,
        "identifier": identifier,
        "url": url,
        "timestamp": _now_iso(),
        "status": "error",
        "summary": "",
    }
    response: dict[str, Any] | None = None
    try:
        response = _http_json(url, contact_email=config.contact_email)
        record["status"] = "ok"
        record["summary"] = summary_fn(response)
        record["response"] = response
    except Exception as exc:
        record["error"] = str(exc)
        record["summary"] = str(exc)[:180]
    if cache_path is not None:
        cache_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return response, f"{service} cache_miss status={record['status']} summary={record['summary']}", False


def _grobid_endpoint(base_url: str) -> str:
    return base_url.rstrip("/") + "/api/processFulltextDocument"


def extract_text_with_grobid(source: Path, config: AuditConfig, findings: list[Finding]) -> str:
    if not config.grobid_url or source.suffix.lower() != ".pdf":
        return ""
    try:
        boundary = "----pcr-audit-boundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="input"; filename="{source.name}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + source.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
        request = urllib.request.Request(
            _grobid_endpoint(config.grobid_url),
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "pcr-audit/1.0.1"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            tei = response.read().decode("utf-8", errors="ignore")
        root = ElementTree.fromstring(tei)
        text = " ".join(node.text or "" for node in root.iter() if node.text)
        if not text.strip():
            raise ValueError("GROBID returned TEI without text content")
        findings.append(
            finding(
                str(source), "info", "GROBID结构抽取", "PDF",
                "GROBID REST 抽取成功，已用于参考文献/正文辅助解析。",
                f"grobid_url={config.grobid_url}; extracted_chars={len(text)}",
                "GROBID 抽取仍需结合原文版式人工复核。",
                tool_id="grobid_extract", tool_name="GROBID REST结构抽取", input_type="paper_document",
            )
        )
        return text
    except Exception as exc:
        findings.append(
            finding(
                str(source), "info", "GROBID结构抽取", "PDF",
                "GROBID 不可用或返回内容无法解析，已回退到本地文本抽取。",
                str(exc),
                "确认 GROBID 服务地址、网络和PDF可解析性；该提示不计入数据风险。",
                tool_id="grobid_extract", tool_name="GROBID REST结构抽取", input_type="paper_document",
                dependency_status="grobid_unavailable",
                confidence_basis="外部抽取降级记录，不是数据风险信号。",
            )
        )
        return ""


def _extract_reference_text(source: Path, config: AuditConfig | None = None, findings: list[Finding] | None = None) -> str:
    if config is not None and findings is not None:
        grobid_text = extract_text_with_grobid(source, config, findings)
        if grobid_text:
            return grobid_text
    if source.suffix.lower() in DOC_SUFFIXES:
        try:
            return read_text_source(source)
        except Exception:
            return ""
    if source.suffix.lower() in {".bib", ".ris"}:
        return source.read_text(encoding="utf-8", errors="ignore")
    return ""


def analyze_references(source: Path, config: AuditConfig | None = None) -> TableResult:
    config = config or _env_config()
    findings: list[Finding] = []
    text = _extract_reference_text(source, config, findings)
    dois = sorted({doi.rstrip(".,);]") for doi in DOI_RE.findall(text)})
    pmids = sorted(set(PMID_RE.findall(text)))
    reference_lines = [m.group("body").strip() for m in REFERENCE_LINE_RE.finditer(text)]
    reference_lines = [line for line in reference_lines if DOI_RE.search(line) or PMID_RE.search(line) or re.search(r"\(\d{4}\)|\b20\d\d\b|\b19\d\d\b", line)]

    if not text:
        findings.append(
            finding(
                str(source), "info", "参考文献解析", "输入文本",
                "未能从输入中抽取可核验参考文献文本。",
                "支持 TXT/MD/DOCX/PDF/BibTeX/RIS；复杂PDF可能需要GROBID预处理。",
                "补充参考文献列表、BibTeX/RIS或开启GROBID服务后重试。",
                tool_id="reference_audit", tool_name="参考文献核验", input_type="reference_list",
                dependency_status="insufficient_material",
            )
        )
    elif not dois and not pmids:
        findings.append(
            finding(
                str(source), "low", "参考文献标识符缺失", "DOI/PMID",
                "未发现 DOI 或 PMID，自动核验覆盖受限。",
                f"候选参考文献行={len(reference_lines)}，DOI=0，PMID=0",
                "建议补充 DOI/PMID 或提供结构化参考文献表，以降低错引和虚假引用风险。",
                tool_id="reference_audit", tool_name="参考文献核验", input_type="reference_list",
            )
        )
    else:
        findings.append(
            finding(
                str(source), "info", "参考文献标识符解析", "DOI/PMID",
                "已解析出可核验的参考文献标识符。",
                f"DOI={len(dois)}，PMID={len(pmids)}，候选参考文献行={len(reference_lines)}",
                "对高风险引用建议人工核对题名、作者、年份和正文主张是否匹配。",
                tool_id="reference_audit", tool_name="参考文献核验", input_type="reference_list",
                calculation_trace="正则抽取 DOI 和 PMID；外部元数据查询需显式开启 PCR_ENABLE_EXTERNAL_LOOKUPS=1。",
            )
        )

    if not _external_enabled(config):
        if dois or pmids:
            findings.append(
                finding(
                    str(source), "info", "外部元数据核验未启用", "Crossref/OpenAlex/NCBI",
                    "默认本地/私有化运行未向外部API发送稿件或参考文献信息。",
                    "使用 --external-lookups 或设置 PCR_ENABLE_EXTERNAL_LOOKUPS=1 后才会查询 Crossref、OpenAlex 和 NCBI E-utilities。",
                    "如需生产环境启用，应配置缓存、速率限制和数据出境告知。",
                    tool_id="reference_audit", tool_name="参考文献核验", input_type="reference_list",
                    dependency_status="external_lookup_disabled",
                    confidence_basis="合规降级记录，不是数据风险信号。",
                )
            )
        return TableResult("reference_audit", 0, 0, findings)

    for doi in dois[:20]:
        encoded = urllib.parse.quote(doi, safe="")
        records: list[str] = []
        mailto = urllib.parse.quote(config.contact_email) if config.contact_email else ""
        crossref_url = f"https://api.crossref.org/works/{encoded}" + (f"?mailto={mailto}" if mailto else "")
        crossref, record, _cache_hit = _cached_lookup(
            "crossref",
            doi,
            crossref_url,
            config,
            lambda payload: "; ".join((payload or {}).get("message", {}).get("title", [])[:1])[:180],
        )
        records.append(record)
        if crossref:
            status = (crossref or {}).get("status")
            title = "; ".join((crossref or {}).get("message", {}).get("title", [])[:1])
            records.append(f"Crossref status={status}, title={title[:120]}")
        openalex, record, _cache_hit = _cached_lookup(
            "openalex",
            doi,
            f"https://api.openalex.org/works/https://doi.org/{encoded}",
            config,
            lambda payload: f"id={(payload or {}).get('id')}; retracted={(payload or {}).get('is_retracted')}",
        )
        records.append(record)
        if openalex:
            records.append(f"OpenAlex id={openalex.get('id')}, retracted={openalex.get('is_retracted')}")
            if openalex.get("is_retracted"):
                findings.append(
                    finding(
                        str(source), "medium", "撤稿引用信号", doi,
                        "OpenAlex 标记该 DOI 对应作品为撤稿或撤回。",
                        str(openalex.get("id") or doi),
                        "人工核对撤稿原因、引用语境和是否需要替换或说明。",
                        tool_id="reference_audit", tool_name="参考文献核验", input_type="reference_list",
                        external_records="; ".join(records),
                    )
                )
        if records and not any(f.target == doi for f in findings):
            findings.append(
                finding(
                    str(source), "info", "DOI元数据核验", doi,
                    "已尝试查询 DOI 外部元数据。",
                    "; ".join(records),
                    "若元数据不匹配，应人工比对参考文献题名、作者、年份和期刊。",
                    tool_id="reference_audit", tool_name="参考文献核验", input_type="reference_list",
                    external_records="; ".join(records),
                )
            )
    for pmid in pmids[:20]:
        url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
            + urllib.parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "json"})
        )
        ncbi, record, _cache_hit = _cached_lookup(
            "ncbi",
            pmid,
            url,
            config,
            lambda payload: ((payload or {}).get("result", {}).get(pmid, {}).get("title") or "")[:180],
        )
        findings.append(
            finding(
                str(source), "info", "PMID元数据核验", pmid,
                "已尝试查询 PMID 外部元数据。",
                record,
                "若元数据不匹配，应人工比对参考文献题名、作者、年份和期刊。",
                tool_id="reference_audit", tool_name="参考文献核验", input_type="reference_list",
                external_records=json.dumps((ncbi or {}).get("result", {}).get(pmid, {}), ensure_ascii=False)[:500],
            )
        )
    return TableResult("reference_audit", 0, 0, findings)


def analyze_citation_claims(source: Path, config: AuditConfig | None = None) -> TableResult:
    grobid_findings: list[Finding] = []
    text = _extract_reference_text(source, config, grobid_findings) if config else _extract_reference_text(source)
    matches = [m.group("claim").strip() for m in CLAIM_WITH_CITATION_RE.finditer(text or "")]
    findings: list[Finding] = grobid_findings
    if not matches:
        findings.append(
            finding(
                str(source), "info", "引用主张抽取", "正文引用",
                "未抽取到可自动复核的带引用主张。",
                "当前轻量规则识别数字方括号引用或作者-年份引用。",
                "如需引用支持关系复核，建议提供结构化正文和参考文献，或接入GROBID/RAG流程。",
                tool_id="citation_claim_check", tool_name="引用支持关系辅助复核", input_type="reference_list",
                dependency_status="insufficient_material",
            )
        )
    else:
        sample = "；".join(matches[:5])
        findings.append(
            finding(
                str(source), "info", "引用主张抽取", "正文引用",
                "已抽取带引用主张，供人工或RAG流程复核。",
                f"候选主张={len(matches)}；样例：{sample}",
                "逐条核对引用文献是否支持正文主张，尤其是强因果、临床有效性和机制性表述。",
                tool_id="citation_claim_check", tool_name="引用支持关系辅助复核", input_type="reference_list",
                calculation_trace="轻量正则抽取，不调用LLM；判断支持/反对需要人工或受控RAG证据片段。",
            )
        )
    return TableResult("citation_claim_check", 0, 0, findings)


def analyze_papermill_signals(source: Path, config: AuditConfig | None = None) -> TableResult:
    grobid_findings: list[Finding] = []
    text = _extract_reference_text(source, config, grobid_findings) if config else _extract_reference_text(source)
    findings: list[Finding] = grobid_findings
    lowered = text.lower()
    hits = [(phrase, intended) for phrase, intended in TORTURED_PHRASES.items() if phrase in lowered]
    if hits:
        evidence = "; ".join(f"{phrase} -> {intended}" for phrase, intended in hits[:10])
        findings.append(
            finding(
                str(source), "medium", "异常短语/论文工厂轻量信号", "正文",
                "发现疑似 tortured phrases 或机器替换短语。",
                evidence,
                "人工检查术语是否为领域内真实表达；若为异常替换，应回查文本来源和引用网络。",
                tool_id="papermill_light_signals", tool_name="论文工厂轻量信号", input_type="plain_text",
            )
        )
    elif text:
        findings.append(
            finding(
                str(source), "info", "论文工厂轻量信号", "正文",
                "轻量短语扫描完成，未发现内置异常短语。",
                f"扫描字符数={len(text)}，规则数={len(TORTURED_PHRASES)}",
                "该结果不等于无论文工厂风险；跨库相似性和投稿行为需要机构版数据。",
                tool_id="papermill_light_signals", tool_name="论文工厂轻量信号", input_type="plain_text",
            )
        )
    return TableResult("papermill_light_signals", 0, 0, findings)


def iter_image_files(source: Path) -> list[Path]:
    if source.is_dir():
        return [path for path in iter_audit_files(source) if path.suffix.lower() in IMAGE_SUFFIXES]
    return [source] if source.suffix.lower() in IMAGE_SUFFIXES else []


def extract_docx_images(source: Path, out_dir: Path) -> list[Path]:
    images: list[Path] = []
    if source.suffix.lower() != ".docx":
        return images
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as zf:
        for item in zf.namelist():
            if not item.startswith("word/media/"):
                continue
            suffix = Path(item).suffix.lower()
            if suffix not in IMAGE_SUFFIXES:
                continue
            out = out_dir / Path(item).name
            out.write_bytes(zf.read(item))
            images.append(out)
    return images


def extract_pdf_images(source: Path, out_dir: Path) -> tuple[list[Path], str]:
    images: list[Path] = []
    if source.suffix.lower() != ".pdf":
        return images, ""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import pdfplumber
    except Exception as exc:
        return images, f"pdfplumber_unavailable={exc}"
    Image = _pil_image_module()
    if Image is None:
        return images, "pillow_unavailable"
    notes: list[str] = []
    try:
        with pdfplumber.open(str(source)) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                for image_no, item in enumerate(page.images or [], start=1):
                    out = out_dir / f"{source.stem}_p{page_no}_img{image_no}.png"
                    saved = False
                    stream = item.get("stream")
                    if stream is not None:
                        try:
                            data = stream.get_data()
                            with Image.open(BytesIO(data)) as img:
                                img.save(out)
                            saved = True
                        except Exception:
                            pass
                    if not saved:
                        try:
                            bbox = (item["x0"], item["top"], item["x1"], item["bottom"])
                            rendered = page.crop(bbox).to_image(resolution=150).original
                            rendered.save(out)
                            saved = True
                        except Exception as exc:
                            notes.append(f"p{page_no}/img{image_no}:{exc}")
                    if saved:
                        images.append(out)
    except Exception as exc:
        return images, str(exc)
    return images, "; ".join(notes[:5])


def _pil_image_module():
    try:
        from PIL import Image
    except Exception:
        return None
    return Image


def _average_hash(path: Path, hash_size: int = 8) -> tuple[int, str] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((hash_size, hash_size))
            arr = np.asarray(gray, dtype=float)
    except Exception:
        return None
    avg = float(arr.mean())
    bits = 0
    for value in arr.flatten():
        bits = (bits << 1) | int(value >= avg)
    return bits, f"{bits:0{hash_size * hash_size // 4}x}"


def _difference_hash(path: Path, hash_size: int = 8) -> tuple[int, str] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((hash_size + 1, hash_size))
            arr = np.asarray(gray, dtype=float)
    except Exception:
        return None
    bits = 0
    for value in (arr[:, 1:] > arr[:, :-1]).flatten():
        bits = (bits << 1) | int(value)
    return bits, f"{bits:0{hash_size * hash_size // 4}x}"


def _phash_from_array(arr: np.ndarray, hash_size: int = 8) -> tuple[int, str]:
    from scipy.fftpack import dct

    dct_rows = dct(arr, axis=0, norm="ortho")
    dct_cols = dct(dct_rows, axis=1, norm="ortho")
    low = dct_cols[:hash_size, :hash_size]
    median = float(np.median(low[1:, 1:]))
    bits = 0
    for value in low.flatten():
        bits = (bits << 1) | int(value >= median)
    return bits, f"{bits:0{hash_size * hash_size // 4}x}"


def _perceptual_hash(path: Path, hash_size: int = 8) -> tuple[int, str] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((32, 32))
            arr = np.asarray(gray, dtype=float)
        return _phash_from_array(arr, hash_size)
    except Exception:
        return None


def image_fingerprints(path: Path) -> dict[str, Any]:
    fingerprints: dict[str, Any] = {}
    for name, fn in (("ahash", _average_hash), ("dhash", _difference_hash), ("phash", _perceptual_hash)):
        item = fn(path)
        if item is not None:
            fingerprints[name] = {"int": item[0], "hex": item[1]}
    return fingerprints


def _hamming(left: int, right: int) -> int:
    return int((left ^ right).bit_count())


def _hash_summary(hashes: dict[str, Any]) -> str:
    return ", ".join(f"{name}:{item.get('hex')}" for name, item in hashes.items())


def _transformed_phash_distances(left: Path, right: Path) -> tuple[str, int] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    left_hash = _perceptual_hash(left)
    if left_hash is None:
        return None
    transforms = {
        "original": lambda img: img,
        "flip_left_right": lambda img: img.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        "flip_top_bottom": lambda img: img.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
        "rotate_90": lambda img: img.rotate(90, expand=True),
        "rotate_180": lambda img: img.rotate(180, expand=True),
        "rotate_270": lambda img: img.rotate(270, expand=True),
    }
    best: tuple[str, int] | None = None
    try:
        with Image.open(right) as img:
            for name, transform in transforms.items():
                gray = transform(img).convert("L").resize((32, 32))
                arr = np.asarray(gray, dtype=float)
                right_hash, _right_hex = _phash_from_array(arr)
                distance = _hamming(left_hash[0], right_hash)
                if best is None or distance < best[1]:
                    best = (name, distance)
    except Exception:
        return None
    return best


def _orb_similarity(left: Path, right: Path) -> dict[str, Any] | None:
    try:
        import cv2
    except Exception:
        return None
    left_img = cv2.imread(str(left), cv2.IMREAD_GRAYSCALE)
    right_img = cv2.imread(str(right), cv2.IMREAD_GRAYSCALE)
    if left_img is None or right_img is None:
        return None
    orb = cv2.ORB_create(nfeatures=800)
    kp1, des1 = orb.detectAndCompute(left_img, None)
    kp2, des2 = orb.detectAndCompute(right_img, None)
    if des1 is None or des2 is None or not kp1 or not kp2:
        return {"good_matches": 0, "keypoints_left": len(kp1 or []), "keypoints_right": len(kp2 or [])}
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)
    good = [m for m in matches if m.distance <= 48]
    return {
        "good_matches": len(good),
        "keypoints_left": len(kp1),
        "keypoints_right": len(kp2),
        "median_distance": round(float(np.median([m.distance for m in good])), 2) if good else None,
    }


def _copy_move_matches(path: Path) -> dict[str, Any] | None:
    try:
        import cv2
    except Exception:
        return None
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    orb = cv2.ORB_create(nfeatures=1200)
    keypoints, descriptors = orb.detectAndCompute(img, None)
    if descriptors is None or len(keypoints) < 12:
        return {"matches": 0, "keypoints": len(keypoints or []), "samples": []}
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw_matches = matcher.knnMatch(descriptors, descriptors, k=3)
    samples = []
    vectors: list[tuple[int, int]] = []
    for matches in raw_matches:
        for match in matches:
            if match.queryIdx == match.trainIdx or match.distance > 36:
                continue
            p1 = keypoints[match.queryIdx].pt
            p2 = keypoints[match.trainIdx].pt
            spatial = math.dist(p1, p2)
            if spatial < 25:
                continue
            dx = int(round(p2[0] - p1[0]))
            dy = int(round(p2[1] - p1[1]))
            vectors.append((round(dx / 10) * 10, round(dy / 10) * 10))
            if len(samples) < 6:
                samples.append(
                    {
                        "from": [round(p1[0], 1), round(p1[1], 1)],
                        "to": [round(p2[0], 1), round(p2[1], 1)],
                        "distance": round(float(match.distance), 2),
                    }
                )
            break
    common = Counter(vectors).most_common(1)
    clustered = common[0][1] if common else 0
    return {"matches": len(vectors), "clustered_matches": clustered, "keypoints": len(keypoints), "samples": samples}


def _image_metadata_findings(source: Path, images: list[Path]) -> list[Finding]:
    Image = _pil_image_module()
    findings: list[Finding] = []
    if Image is None:
        return [
            finding(
                str(source), "info", "图像元数据依赖缺失", "Pillow",
                "缺少 Pillow，无法读取图像元数据与亮度质量信号。",
                "dependency_missing=Pillow",
                "安装受信任版本 Pillow 后重试；该提示不计入数据风险。",
                tool_id="image_metadata_audit", tool_name="图像元数据与质量初筛",
                input_type="scientific_figure", dependency_status="dependency_missing",
            )
        ]
    for path in images:
        try:
            with Image.open(path) as img:
                exif_count = len(img.getexif() or {})
                arr = np.asarray(img.convert("L"), dtype=float)
                width, height = img.size
                fmt = img.format or path.suffix.lstrip(".").upper()
                mode = img.mode
                mean = float(arr.mean())
                std = float(arr.std())
        except Exception as exc:
            findings.append(
                finding(
                    str(source), "info", "图像元数据读取失败", path.name,
                    "图片无法读取，已跳过元数据检查。",
                    str(exc),
                    "确认文件是否损坏或格式是否受支持。",
                    tool_id="image_metadata_audit", tool_name="图像元数据与质量初筛",
                    input_type="scientific_figure", dependency_status="read_failed",
                )
            )
            continue
        evidence = f"format={fmt}; size={width}x{height}; mode={mode}; exif_fields={exif_count}; gray_mean={mean:.1f}; gray_std={std:.1f}"
        if width < 80 or height < 80:
            level, summary = "low", "图片分辨率较低，可能限制图像取证和人工复核。"
        elif std < 4 or mean < 3 or mean > 252:
            level, summary = "low", "图片动态范围异常偏低或接近全黑/全白，需确认是否为导出或压缩流程导致。"
        elif exif_count == 0 and fmt in {"JPEG", "TIFF"}:
            level, summary = "info", "图片未包含可读 EXIF 元数据；这常见于论文排版或导出流程。"
        else:
            level, summary = "info", "图像元数据读取完成，未发现内置质量阈值信号。"
        findings.append(
            finding(
                str(source), level, "图像元数据与质量", path.name,
                summary,
                evidence,
                "结合原始仪器文件、导出流程和未压缩原图人工复核。",
                tool_id="image_metadata_audit", tool_name="图像元数据与质量初筛",
                input_type="scientific_figure",
            )
        )
    return findings


def analyze_images(source: Path, workdir: Path | None = None) -> list[TableResult]:
    workdir = workdir or source.with_suffix(".images")
    images = iter_image_files(source)
    if source.suffix.lower() == ".docx":
        images = extract_docx_images(source, workdir)
    pdf_note = ""
    if source.suffix.lower() == ".pdf":
        images, pdf_note = extract_pdf_images(source, workdir)
    findings_extract: list[Finding] = []
    findings_dup: list[Finding] = []
    findings_copy: list[Finding] = []
    findings_meta: list[Finding] = []
    findings_blot: list[Finding] = []

    if not images:
        findings_extract.append(
            finding(
                str(source), "info", "图像抽取", "figure",
                "未发现可直接检测的图片文件。",
                f"PDF 图像抽取为 best-effort；DOCX 可抽取 word/media 下图片。{pdf_note}",
                "若需要图像完整性初筛，请提供原始图、DOCX稿件或单独图片目录。",
                tool_id="image_extract", tool_name="图像抽取", input_type="scientific_figure",
                dependency_status="insufficient_material",
            )
        )
        return [TableResult("image_extract", 0, 0, findings_extract)]

    findings_extract.append(
        finding(
            str(source), "info", "图像抽取", "figure",
            "已发现可检测图片。",
            f"图片数={len(images)}；样例={', '.join(path.name for path in images[:8])}",
            "对命中的重复图或blot/gel图，建议回看原始未裁剪图片和图注说明。",
            tool_id="image_extract", tool_name="图像抽取", input_type="scientific_figure",
        )
    )

    hashes: list[tuple[Path, dict[str, Any]]] = []
    hash_missing = False
    for path in images:
        item = image_fingerprints(path)
        if not item:
            hash_missing = True
            continue
        hashes.append((path, item))
    if hash_missing:
        findings_dup.append(
            finding(
                str(source), "info", "图像依赖缺失或读取失败", "Pillow",
                "部分图片无法计算感知哈希。",
                "需要 Pillow 才能执行本地感知哈希；损坏或特殊格式图片也会跳过。",
                "安装受信任版本 Pillow 后重试；不要把该提示当作图像风险。",
                tool_id="image_duplicate_internal", tool_name="稿件内部重复图初筛",
                input_type="scientific_figure", dependency_status="dependency_missing",
            )
        )
    for i, (left_path, left_hashes) in enumerate(hashes):
        for right_path, right_hashes in hashes[i + 1:]:
            distances = {
                name: _hamming(left_hashes[name]["int"], right_hashes[name]["int"])
                for name in sorted(set(left_hashes).intersection(right_hashes))
            }
            best_name, best_distance = min(distances.items(), key=lambda item: item[1]) if distances else ("none", 999)
            transform = _transformed_phash_distances(left_path, right_path)
            orb = _orb_similarity(left_path, right_path)
            orb_good = int((orb or {}).get("good_matches") or 0)
            is_hit = best_distance <= 6 or (transform is not None and transform[1] <= 8 and transform[0] != "original") or orb_good >= 18
            if is_hit:
                transform_text = f"{transform[0]}:{transform[1]}" if transform else "unavailable"
                orb_text = f"orb_good={orb_good}, keypoints={int((orb or {}).get('keypoints_left') or 0)}/{int((orb or {}).get('keypoints_right') or 0)}" if orb else "orb=unavailable"
                findings_dup.append(
                    finding(
                        str(source), "medium", "内部重复图像", f"{left_path.name} / {right_path.name}",
                        "两张图片的本地图像指纹或局部特征高度相似，需人工复核是否为重复、裁剪、翻转或复用。",
                        f"best_hash={best_name}:{best_distance}; transform={transform_text}; {orb_text}; hashes_left={{{_hash_summary(left_hashes)}}}; hashes_right={{{_hash_summary(right_hashes)}}}",
                        "检查图注、实验条件和原始图；相似图可能来自同一样本、排版缩略图或真实重复实验。",
                        tool_id="image_duplicate_internal", tool_name="稿件内部重复图初筛",
                        input_type="scientific_figure",
                        calculation_trace="Pillow/numpy 本地 aHash/dHash/pHash；若 cv2 可用则附加 ORB 局部特征匹配；不上传图片。",
                    )
                )
    if not findings_dup:
        findings_dup.append(
            finding(
                str(source), "info", "内部重复图像", "figure",
                "内部重复图初筛完成，未发现高度相似图片对。",
                f"可哈希图片数={len(hashes)}",
                "该初筛不能排除局部复制、复杂旋转裁剪或跨稿件复用。",
                tool_id="image_duplicate_internal", tool_name="稿件内部重复图初筛", input_type="scientific_figure",
            )
        )

    for path in images:
        copy = _copy_move_matches(path)
        if copy is None:
            findings_copy.append(
                finding(
                    str(source), "info", "局部复制依赖缺失", "cv2",
                    "缺少 OpenCV，无法运行 ORB 局部 copy-move 初筛。",
                    "dependency_missing=cv2",
                    "安装 opencv-python-headless 后重试；该提示不计入图像风险。",
                    tool_id="image_copy_move_internal", tool_name="图像局部复制初筛",
                    input_type="scientific_figure", dependency_status="dependency_missing",
                )
            )
            break
        if int(copy.get("clustered_matches") or 0) >= 6:
            findings_copy.append(
                finding(
                    str(source), "medium", "疑似局部复制区域", path.name,
                    "单张图内部存在多组相似局部特征，需人工复核是否为 copy-move、重复纹理或图表元素。",
                    f"matches={copy.get('matches')}; clustered_matches={copy.get('clustered_matches')}; keypoints={copy.get('keypoints')}; samples={json.dumps(copy.get('samples'), ensure_ascii=False)}",
                    "打开原图检查命中坐标附近区域，要求作者提供原始未裁剪图和处理说明。",
                    tool_id="image_copy_move_internal", tool_name="图像局部复制初筛",
                    input_type="scientific_figure",
                    calculation_trace="OpenCV ORB 特征在同一图内部自匹配，过滤近邻点后按位移向量聚类。",
                )
            )
    if not findings_copy:
        findings_copy.append(
            finding(
                str(source), "info", "疑似局部复制区域", "figure",
                "局部 copy-move 初筛完成，未发现达到阈值的聚类匹配。",
                f"图片数={len(images)}",
                "该结果不能排除人工精修、低纹理区域或强压缩后的局部复制。",
                tool_id="image_copy_move_internal", tool_name="图像局部复制初筛",
                input_type="scientific_figure",
            )
        )

    findings_meta = _image_metadata_findings(source, images)

    blot_candidates = [path for path in images if re.search(r"blot|western|gel|wb|lane|膜|凝胶", path.name, re.I)]
    if blot_candidates:
        findings_blot.append(
            finding(
                str(source), "low", "Western blot/凝胶复核清单", "图像文件名",
                "发现疑似 Western blot 或凝胶图片文件名。",
                ", ".join(path.name for path in blot_candidates[:10]),
                "请作者提供原始 uncropped blot、曝光参数、拼接说明、loading control 和重复实验记录。",
                tool_id="western_blot_review_list", tool_name="Western blot复核清单", input_type="western_blot_or_gel_image",
            )
        )
    else:
        findings_blot.append(
            finding(
                str(source), "info", "Western blot/凝胶复核清单", "图像文件名",
                "未从文件名识别到 blot/gel 专项复核对象。",
                f"图片数={len(images)}",
                "若稿件包含 blot/gel 但文件名未标注，建议人工指定图像类型。",
                tool_id="western_blot_review_list", tool_name="Western blot复核清单", input_type="western_blot_or_gel_image",
            )
        )
    return [
        TableResult("image_extract", len(images), 0, findings_extract),
        TableResult("image_duplicate_internal", len(images), 0, findings_dup),
        TableResult("image_copy_move_internal", len(images), 0, findings_copy),
        TableResult("image_metadata_audit", len(images), 0, findings_meta),
        TableResult("western_blot_review_list", len(blot_candidates), 0, findings_blot),
    ]


def analyze_provenance(source: Path) -> TableResult:
    paths = [source] if source.is_file() else iter_audit_files(source)
    return analyze_provenance_paths(source, paths)


def _project_paths_for_provenance(source: Path) -> list[Path]:
    if source.is_file() and source.suffix.lower() == ".json":
        spec, _config = parse_project_spec(source)
        paths = [material.path for material in spec.materials]
    elif source.is_dir():
        spec, _config = parse_project_spec(source)
        paths = [material.path for material in spec.materials] if spec.materials else iter_audit_files(source)
    else:
        paths = [source]
    base = source.parent if source.is_file() else source
    return sorted(path for path in paths if path.is_file() and is_audit_material_path(path, base))


def _relative_to_project(source: Path, path: Path) -> str:
    base = source.parent if source.is_file() else source
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path.resolve())


def default_ledger_path(source: Path) -> Path:
    base = source.parent if source.is_file() else source
    return base / ".pcr" / "provenance-ledger.jsonl"


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _latest_ledger_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("event") != "record":
            continue
        latest[str(record.get("relative_path") or "")] = record
    return latest


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "size": int(stat.st_size),
        "mtime": int(stat.st_mtime),
        "suffix": path.suffix.lower(),
    }


def provenance_init(source: Path, ledger: Path | None = None) -> dict[str, Any]:
    ledger_path = ledger or default_ledger_path(source)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not ledger_path.exists():
        ledger_path.write_text("", encoding="utf-8")
    return {"ledger": str(ledger_path), "status": "ready", "records": len(_read_ledger(ledger_path))}


def provenance_record(source: Path, ledger: Path | None = None, operator: str = "") -> dict[str, Any]:
    ledger_path = ledger or default_ledger_path(source)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_ledger(ledger_path)
    latest = _latest_ledger_records(existing)
    batch_id = uuid.uuid4().hex
    now = _now_iso()
    records = []
    for path in _project_paths_for_provenance(source):
        rel = _relative_to_project(source, path)
        meta = _file_metadata(path)
        digest = _sha256_file(path)
        parent = latest.get(rel)
        record = {
            "event": "record",
            "record_id": uuid.uuid4().hex,
            "batch_id": batch_id,
            "project_id": source.stem if source.is_file() else source.name,
            "relative_path": rel,
            "path": str(path),
            "sha256": digest,
            "size": meta["size"],
            "mtime": meta["mtime"],
            "recorded_at": now,
            "parent_record_id": str(parent.get("record_id")) if parent else "",
            "role": infer_role(path),
            "operator": operator,
            "metadata": meta,
        }
        records.append(record)
    with ledger_path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {"ledger": str(ledger_path), "batch_id": batch_id, "records": records}


def provenance_verify(source: Path, ledger: Path | None = None) -> dict[str, Any]:
    ledger_path = ledger or default_ledger_path(source)
    records = _read_ledger(ledger_path)
    latest = _latest_ledger_records(records)
    current_paths = {_relative_to_project(source, path): path for path in _project_paths_for_provenance(source)}
    statuses = []
    for rel, record in latest.items():
        path = current_paths.get(rel)
        if path is None or not path.exists():
            statuses.append({"relative_path": rel, "status": "missing", "record_id": record.get("record_id"), "sha256": record.get("sha256")})
            continue
        digest = _sha256_file(path)
        meta = _file_metadata(path)
        matched = digest == record.get("sha256") and meta["size"] == int(record.get("size") or -1)
        statuses.append(
            {
                "relative_path": rel,
                "status": "matched" if matched else "changed",
                "record_id": record.get("record_id"),
                "sha256": digest,
                "expected_sha256": record.get("sha256"),
                "size": meta["size"],
                "expected_size": record.get("size"),
            }
        )
    for rel, path in current_paths.items():
        if rel not in latest:
            meta = _file_metadata(path)
            statuses.append({"relative_path": rel, "status": "new", "sha256": _sha256_file(path), "size": meta["size"]})
    return {"ledger": str(ledger_path), "records": len(records), "statuses": sorted(statuses, key=lambda item: item["relative_path"])}


def provenance_diff(source: Path, ledger: Path | None = None, left_batch: str = "", right_batch: str = "") -> dict[str, Any]:
    ledger_path = ledger or default_ledger_path(source)
    records = [record for record in _read_ledger(ledger_path) if record.get("event") == "record"]
    batches = []
    for record in records:
        batch = str(record.get("batch_id") or "")
        if batch and batch not in batches:
            batches.append(batch)
    if not left_batch and len(batches) >= 2:
        left_batch = batches[-2]
    if not right_batch and batches:
        right_batch = batches[-1]
    left = {str(record.get("relative_path")): record for record in records if record.get("batch_id") == left_batch}
    right = {str(record.get("relative_path")): record for record in records if record.get("batch_id") == right_batch}
    changes = []
    for rel in sorted(set(left).union(right)):
        if rel not in left:
            status = "added"
        elif rel not in right:
            status = "removed"
        elif left[rel].get("sha256") != right[rel].get("sha256") or left[rel].get("size") != right[rel].get("size"):
            status = "modified"
        else:
            status = "unchanged"
        changes.append({"relative_path": rel, "status": status, "left_record_id": left.get(rel, {}).get("record_id", ""), "right_record_id": right.get(rel, {}).get("record_id", "")})
    return {"ledger": str(ledger_path), "left_batch": left_batch, "right_batch": right_batch, "changes": changes}


def provenance_payload_to_result(source: Path, payload: dict[str, Any], tool_name: str = "哈希版本链核验") -> TableResult:
    findings: list[Finding] = []
    statuses = payload.get("statuses") or payload.get("changes") or []
    if not statuses:
        findings.append(
            finding(
                str(source), "info", tool_name, "ledger",
                "哈希版本链账本没有可报告的文件状态。",
                f"ledger={payload.get('ledger')}; records={payload.get('records', 0)}",
                "先运行 provenance record 登记项目材料，再执行 verify/diff。",
                tool_id="provenance_chain_verify", tool_name=tool_name, input_type="raw_file_bundle",
                dependency_status="insufficient_material",
            )
        )
    for item in statuses:
        status = str(item.get("status"))
        level = "info" if status in {"matched", "unchanged"} else ("medium" if status in {"changed", "modified"} else "low")
        findings.append(
            finding(
                str(source), level, tool_name, str(item.get("relative_path") or ""),
                f"哈希版本链状态：{status}",
                json.dumps(item, ensure_ascii=False, sort_keys=True),
                "对 changed/modified/missing/new 文件核对原始记录、上传批次和操作者说明。",
                tool_id="provenance_chain_verify", tool_name=tool_name, input_type="raw_file_bundle",
                calculation_trace="读取 JSONL 账本最新记录并对当前文件重新计算 SHA-256。",
                confidence_basis="SHA-256 与文件大小是确定性完整性证据；不证明实验真实性。",
            )
        )
    return TableResult("provenance_chain_verify", len(statuses), 0, findings)


def analyze_provenance_paths(source: Path, paths: list[Path]) -> TableResult:
    findings: list[Finding] = []
    for path in paths[:200]:
        digest = _sha256_file(path)
        stat = path.stat()
        findings.append(
            finding(
                str(source), "info", "SHA-256文件存证", path.name,
                "已计算文件哈希和基础元数据。",
                f"sha256={digest}; size={stat.st_size}; mtime={int(stat.st_mtime)}",
                "保存该JSON作为版本链证据；哈希只能证明文件后续未改动，不能证明实验真实发生。",
                tool_id="provenance_hash", tool_name="原始文件哈希存证", input_type="raw_file_bundle",
                calculation_trace="本地读取文件字节并计算 SHA-256。",
                confidence_basis="哈希是确定性文件完整性证据，但不是实验真实性证据。",
            )
        )
    return TableResult("provenance_hash", len(paths), 0, findings)


def analyze_code_files(source: Path) -> TableResult:
    paths = [source] if source.is_file() else [path for path in iter_audit_files(source) if path.suffix in CODE_SUFFIXES]
    findings: list[Finding] = []
    risky_patterns = {
        r"\bsetwd\s*\(": "脚本包含 setwd，复跑环境可能依赖本机路径。",
        r"read\.(csv|xlsx|table)\s*\(": "脚本读取外部数据，需核对输入文件是否纳入审计包。",
        r"dropna\s*\(|na\.omit\s*\(": "脚本存在缺失值剔除，需核对剔除规则和样本量变化。",
        r"p\s*<\s*0\.05": "脚本或注释出现显著性阈值筛选线索，需核对多重比较透明度。",
    }
    for path in paths[:100]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [message for pattern, message in risky_patterns.items() if re.search(pattern, text, re.I)]
        if hits:
            findings.append(
                finding(
                    str(source), "low", "分析代码复跑准备检查", path.name,
                    "脚本包含需要复跑前确认的输入、路径或剔除规则。",
                    "；".join(hits),
                    "在隔离环境中复跑前，确认依赖、输入文件、随机种子、剔除规则和输出统计量映射。",
                    tool_id="code_rerun_audit", tool_name="分析代码复跑审计", input_type="analysis_code",
                )
            )
    if not findings:
        findings.append(
            finding(
                str(source), "info", "分析代码复跑准备检查", "analysis_code",
                "未发现可扫描的分析代码，或未命中内置复跑风险规则。",
                f"代码文件数={len(paths)}",
                "如需复跑关键统计量，请提供脚本、锁定依赖和原始输入数据。",
                tool_id="code_rerun_audit", tool_name="分析代码复跑审计", input_type="analysis_code",
                dependency_status="insufficient_material" if not paths else "ready",
            )
        )
    return TableResult("code_rerun_audit", len(paths), 0, findings)


def payload_from_results(source: Path, results: list[TableResult], tool_id: str, tool_name: str, input_type: str) -> dict[str, Any]:
    return {
        "tool_id": tool_id,
        "tool_name": tool_name,
        "detector_runtime": "python",
        "dependency_status": "ready",
        "source": str(source),
        "input_type": input_type,
        "results": [
            {"name": result.name, "rows": result.rows, "columns": result.columns, "findings": [asdict(f) for f in result.findings]}
            for result in results
        ],
    }


def infer_role(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in DOC_SUFFIXES:
        return "manuscript"
    if suffix in DATA_SUFFIXES:
        return "raw_data"
    if suffix in IMAGE_SUFFIXES:
        return "figures"
    if path.suffix in CODE_SUFFIXES:
        return "analysis_code"
    return "unknown"


def role_summary(materials: list[Material]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for material in materials:
        counts[material.role] = counts.get(material.role, 0) + 1
    return counts


def inspect_project_payload(source: Path, workdir: Path | None = None) -> dict[str, Any]:
    spec, config = parse_project_spec(source, workdir=workdir)
    counts = role_summary(spec.materials)
    missing_core = []
    if not any(material.role == "manuscript" for material in spec.materials):
        missing_core.append("manuscript")
    if not any(material.role == "raw_data" for material in spec.materials):
        missing_core.append("raw_data")
    return {
        "source": str(source),
        "project_id": spec.project_id,
        "title": spec.title,
        "material_count": len(spec.materials),
        "role_counts": counts,
        "missing_core_roles": missing_core,
        "settings": {
            "external_lookups": config.external_lookups,
            "grobid_url": config.grobid_url,
            "contact_email": config.contact_email,
        },
        "materials": [
            {"path": str(material.path), "role": material.role, "exists": material.path.exists()}
            for material in spec.materials
        ],
        "findings": [asdict(item) for item in spec.findings],
    }


def init_manifest_payload(source: Path, overwrite: bool = False) -> dict[str, Any]:
    if not source.is_dir():
        raise ValueError("init-manifest 只支持项目文件夹。")
    manifest = source / "pcr-project.json"
    if manifest.exists() and not overwrite:
        raise FileExistsError(f"manifest 已存在：{manifest}")
    files = [path for path in iter_audit_files(source) if path.name != "pcr-project.json"]
    payload = {
        "project_id": source.name,
        "title": source.name,
        "materials": [
            {"path": str(path.relative_to(source)), "role": infer_role(path)}
            for path in files
            if infer_role(path) != "unknown"
        ],
        "settings": {
            "external_lookups": True,
            "grobid_url": "",
            "contact_email": "",
        },
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"manifest": str(manifest), "materials": len(payload["materials"]), "roles": role_summary([Material(source / item["path"], item["role"]) for item in payload["materials"]])}


def parse_project_spec(source: Path, config_overrides: AuditConfig | None = None, workdir: Path | None = None) -> tuple[ProjectSpec, AuditConfig]:
    findings: list[Finding] = []
    settings: dict[str, Any] = {}
    materials: list[Material] = []
    project_id = ""
    title = ""

    if source.is_file() and source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        base = source.parent
        project_id = str(payload.get("project_id") or "")
        title = str(payload.get("title") or "")
        settings = dict(payload.get("settings") or {})
        items = payload.get("materials") or payload.get("files") or payload.get("inputs") or []
        seen: set[Path] = set()
        for item in items:
            raw_path = item if isinstance(item, str) else item.get("path", "")
            role = infer_role(Path(raw_path)) if isinstance(item, str) else str(item.get("role") or infer_role(Path(raw_path)))
            if role not in MATERIAL_ROLES:
                findings.append(
                    finding(
                        str(source), "info", "Manifest材料角色", str(raw_path),
                        "manifest 中存在未知材料角色，已按 unknown 处理。",
                        f"role={role}",
                        "请使用 manuscript/raw_data/analysis_code/figures/supplement/references 等标准角色。",
                        tool_id="project_audit", tool_name="项目Manifest解析", input_type="project_manifest",
                        dependency_status="manifest_warning",
                    )
                )
                role = "unknown"
            path = Path(raw_path).expanduser()
            path = (path if path.is_absolute() else base / path).resolve()
            if not is_audit_material_path(path, base):
                continue
            if path in seen:
                findings.append(
                    finding(
                        str(source), "info", "Manifest重复材料", str(raw_path),
                        "manifest 中存在重复材料路径，已保留一份。",
                        str(path),
                        "删除重复条目以降低报告噪声。",
                        tool_id="project_audit", tool_name="项目Manifest解析", input_type="project_manifest",
                        dependency_status="manifest_warning",
                    )
                )
                continue
            seen.add(path)
            if not path.exists():
                findings.append(
                    finding(
                        str(source), "info", "Manifest材料缺失", str(raw_path),
                        "manifest 指向的材料不存在，已跳过。",
                        str(path),
                        "核对相对路径是否以 manifest 所在目录为基准。",
                        tool_id="project_audit", tool_name="项目Manifest解析", input_type="project_manifest",
                        dependency_status="missing_material",
                    )
                )
                continue
            if path.is_dir():
                for child in iter_audit_files(path):
                    materials.append(Material(child.resolve(), role if role != "unknown" else infer_role(child), raw_path))
            else:
                materials.append(Material(path, role, raw_path))
    elif source.is_dir():
        manifest = source / "pcr-project.json"
        if manifest.exists():
            return parse_project_spec(manifest, config_overrides, workdir)
        paths = iter_audit_files(source)
        materials = [Material(path.resolve(), infer_role(path), str(path.relative_to(source))) for path in paths]
    else:
        materials = [Material(source.resolve(), infer_role(source), source.name)]

    if not any(material.role == "manuscript" for material in materials):
        findings.append(
            finding(
                str(source), "info", "项目主稿缺失", "manuscript",
                "项目材料中未识别到主稿文件。",
                "可继续审计数据/代码/图像，但文献、引用和正文统计覆盖会受限。",
                "建议在 manifest 中声明 manuscript 材料。",
                tool_id="project_audit", tool_name="项目Manifest解析", input_type="project_manifest",
                dependency_status="missing_material",
            )
        )

    env = _env_config(workdir)
    config = AuditConfig(
        external_lookups=bool(settings.get("external_lookups", env.external_lookups)),
        grobid_url=str(settings.get("grobid_url") or env.grobid_url),
        contact_email=str(settings.get("contact_email") or env.contact_email),
        lookup_cache_dir=(workdir / "lookup-cache") if workdir else env.lookup_cache_dir,
    )
    if config_overrides:
        if config_overrides.external_lookups:
            config.external_lookups = True
        if config_overrides.grobid_url:
            config.grobid_url = config_overrides.grobid_url
        if config_overrides.contact_email:
            config.contact_email = config_overrides.contact_email
        if config_overrides.lookup_cache_dir:
            config.lookup_cache_dir = config_overrides.lookup_cache_dir

    return ProjectSpec(source, project_id, title, materials, settings, findings), config


def project_sources(source: Path) -> dict[str, list[Path]]:
    spec, _config = parse_project_spec(source)
    paths = [material.path for material in spec.materials]
    return {
        "documents": [m.path for m in spec.materials if m.role in {"manuscript", "references", "supplement"} and m.path.suffix.lower() in DOC_SUFFIXES],
        "data": [m.path for m in spec.materials if m.role == "raw_data" or m.path.suffix.lower() in DATA_SUFFIXES],
        "images": [m.path for m in spec.materials if m.role in {"figures", "image"} or m.path.suffix.lower() in IMAGE_SUFFIXES],
        "code": [m.path for m in spec.materials if m.role == "analysis_code" or m.path.suffix in CODE_SUFFIXES],
        "all": paths,
    }


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
