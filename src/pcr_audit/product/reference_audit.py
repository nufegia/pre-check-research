from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

from pcr_audit.models import Finding, TableResult
from pcr_audit.product.common import (
    CLAIM_WITH_CITATION_RE,
    DOI_RE,
    PMID_RE,
    REFERENCE_LINE_RE,
    TORTURED_PHRASES,
    AuditConfig,
    _cached_lookup,
    _env_config,
    _external_enabled,
    _extract_reference_text,
    finding,
)

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
