from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path
from typing import Any

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

_TITLE_TOKEN_RE = re.compile(r"[A-Za-z0-9]{3,}")


def _title_tokens(text: str) -> set[str]:
    stop = {
        "the", "and", "for", "with", "from", "this", "that", "reference", "references",
        "doi", "pmid", "nature", "journal", "article", "study", "trial", "open", "access",
    }
    return {token.lower() for token in _TITLE_TOKEN_RE.findall(text or "") if token.lower() not in stop}


def _token_overlap(left: str, right: str) -> float:
    left_tokens = _title_tokens(left)
    right_tokens = _title_tokens(right)
    if not left_tokens or not right_tokens:
        return 1.0
    return len(left_tokens.intersection(right_tokens)) / max(len(right_tokens), 1)


def _line_for_identifier(reference_lines: list[str], identifier: str) -> str:
    ident = identifier.lower()
    return next((line for line in reference_lines if ident in line.lower()), "")


def _crossref_title(payload: dict[str, Any] | None) -> str:
    titles = ((payload or {}).get("message") or {}).get("title") or []
    return str(titles[0]) if titles else ""


def _ncbi_title(payload: dict[str, Any] | None, pmid: str) -> str:
    return str(((payload or {}).get("result") or {}).get(pmid, {}).get("title") or "")


def _metadata_status_error(records: list[str]) -> bool:
    text = " ".join(records).lower()
    return "status=error" in text or "http error 404" in text or "not found" in text


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
                str(source), "info", "Reference parsing", "Input text",
                "Could not extract verifiable reference text from input.",
                "Supports TXT/MD/DOCX/PDF/BibTeX/RIS; complex PDF may require GROBID preprocessing.",
                "Supplement with reference list, BibTeX/RIS, or enable GROBID service and retry.",
                tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                dependency_status="insufficient_material",
            )
        )
    elif not dois and not pmids:
        findings.append(
            finding(
                str(source), "low", "Reference identifier missing", "DOI/PMID",
                "No DOI or PMID found; automatic verification coverage is limited.",
                f"Candidate reference lines={len(reference_lines)}, DOI=0, PMID=0",
                "Supplement with DOI/PMID or provide structured reference tables to reduce miscitation and fabricated reference risks.",
                tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
            )
        )
    else:
        findings.append(
            finding(
                str(source), "info", "Reference identifier parsing", "DOI/PMID",
                "Parseable reference identifiers found.",
                f"DOI={len(dois)}, PMID={len(pmids)}, candidate reference lines={len(reference_lines)}",
                "For high-risk citations, manually verify title, author, year, and in-text claim consistency.",
                tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                calculation_trace="Regex extraction of DOI and PMID; external metadata queries require PCR_ENABLE_EXTERNAL_LOOKUPS=1.",
            )
        )

    if not _external_enabled(config):
        if dois or pmids:
            findings.append(
                finding(
                    str(source), "info", "External metadata verification not enabled", "Crossref/OpenAlex/NCBI",
                    "Default local/private runs do not send manuscript or reference information to external APIs.",
                    "Crossref, OpenAlex, and NCBI E-utilities are only queried after using --external-lookups or setting PCR_ENABLE_EXTERNAL_LOOKUPS=1.",
                    "For production use, configure caching, rate limiting, and data export disclosure.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                    dependency_status="external_lookup_disabled",
                    confidence_basis="Compliance downgrade record; not a data risk signal.",
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
            title = _crossref_title(crossref)
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
                        str(source), "medium", "Retraction citation signal", doi,
                        "OpenAlex flags this DOI as retracted or withdrawn.",
                        str(openalex.get("id") or doi),
                        "Manually verify retraction reason, citation context, and whether replacement or clarification is needed.",
                        tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                        external_records="; ".join(records),
                    )
                )
        crossref_title = _crossref_title(crossref)
        reference_line = _line_for_identifier(reference_lines, doi)
        if crossref_title and reference_line:
            overlap = _token_overlap(reference_line, crossref_title)
            if overlap < 0.35:
                findings.append(
                    finding(
                        str(source), "medium", "DOI title mismatch", doi,
                        "Manuscript reference line is significantly inconsistent with Crossref returned title.",
                        f"overlap={overlap:.2f}; reported_line={reference_line[:180]}; crossref_title={crossref_title[:180]}",
                        "Manually verify whether DOI is misapplied, reference title is mis-entered, or layout/extraction caused line misalignment.",
                        tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                        external_records="; ".join(records),
                    )
                )
        if not crossref and not openalex and _metadata_status_error(records):
            findings.append(
                finding(
                    str(source), "medium", "DOI external metadata unverifiable", doi,
                    "This DOI could not retrieve a valid record from external metadata services.",
                    "; ".join(records),
                    "Verify whether DOI is misspelled, is an unregistered identifier, or external service is temporarily unavailable.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                    external_records="; ".join(records),
                )
            )
        if records:
            findings.append(
                finding(
                    str(source), "info", "DOI metadata verification", doi,
                    "Attempted to query DOI external metadata.",
                    "; ".join(records),
                    "If metadata does not match, manually compare reference title, author, year, and journal.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
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
        ncbi_title = _ncbi_title(ncbi, pmid)
        reference_line = _line_for_identifier(reference_lines, pmid)
        if ncbi_title and reference_line:
            overlap = _token_overlap(reference_line, ncbi_title)
            if overlap < 0.35:
                findings.append(
                    finding(
                        str(source), "medium", "PMID title mismatch", pmid,
                        "Manuscript reference line is significantly inconsistent with NCBI returned title.",
                        f"overlap={overlap:.2f}; reported_line={reference_line[:180]}; ncbi_title={ncbi_title[:180]}",
                        "Manually verify whether PMID is misapplied, reference title is mis-entered, or layout/extraction caused line misalignment.",
                        tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                        external_records=json.dumps((ncbi or {}).get("result", {}).get(pmid, {}), ensure_ascii=False)[:500],
                    )
                )
        findings.append(
            finding(
                str(source), "info", "PMID metadata verification", pmid,
                "Attempted to query PMID external metadata.",
                record,
                "If metadata does not match, manually compare reference title, author, year, and journal.",
                tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
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
                str(source), "info", "Citation claim extraction", "In-text citation",
                "No auto-reviewable citation-bearing claims extracted.",
                "Current lightweight rules recognize numeric bracket citations or author-year citations.",
                "For citation support review, provide structured text and references, or integrate GROBID/RAG pipeline.",
                tool_id="citation_claim_check", tool_name="Citation Support Review", input_type="reference_list",
                dependency_status="insufficient_material",
            )
        )
    else:
        sample = "；".join(matches[:5])
        findings.append(
            finding(
                str(source), "info", "Citation claim extraction", "In-text citation",
                "Citation-bearing claims extracted for human or RAG pipeline review.",
                f"Candidate claims={len(matches)}; examples: {sample}",
                "Check each citation for whether it supports the in-text claim, especially strong causal, clinical efficacy, and mechanistic statements.",
                tool_id="citation_claim_check", tool_name="Citation Support Review", input_type="reference_list",
                calculation_trace="Lightweight regex extraction; no LLM call; support/oppose judgments require human or controlled RAG evidence snippets.",
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
                str(source), "medium", "Abnormal phrase/paper mill light signal", "Body text",
                "Found suspected tortured phrases or machine-substituted phrases.",
                evidence,
                "Manually verify whether terms are genuine domain expressions; if abnormal substitution is found, review text provenance and citation network.",
                tool_id="papermill_light_signals", tool_name="Paper mill light signal", input_type="plain_text",
            )
        )
    elif text:
        findings.append(
            finding(
                str(source), "info", "Paper mill light signal", "Body text",
                "Lightweight phrase scan completed; no built-in abnormal phrases found.",
                f"Scanned chars={len(text)}, rules={len(TORTURED_PHRASES)}",
                "This result does not equal no paper mill risk; cross-corpus similarity and submission behavior require institutional data.",
                tool_id="papermill_light_signals", tool_name="Paper mill light signal", input_type="plain_text",
            )
        )
    return TableResult("papermill_light_signals", 0, 0, findings)
