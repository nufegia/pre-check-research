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
    PMCID_RE,
    PMID_RE,
    REFERENCE_LINE_RE,
    TORTURED_PHRASES,
    AuditConfig,
    _cached_lookup,
    _env_config,
    _external_enabled,
    _extract_reference_text,
    finding,
    normalize_doi,
    positive_int,
)

_TITLE_TOKEN_RE = re.compile(r"[A-Za-z0-9]{3,}")
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_REFERENCE_HEADING_RE = re.compile(r"^\s*(references|bibliography|literature cited)\s*$", re.I | re.M)


def _external_lookup_limit(config: AuditConfig) -> int:
    return positive_int(config.external_lookup_limit, 20)


def _body_before_references(text: str) -> str:
    match = _REFERENCE_HEADING_RE.search(text or "")
    return text[: match.start()] if match else ""


def _current_work_doi(text: str) -> str:
    body = _body_before_references(text)
    if not body:
        return ""
    candidates = {normalize_doi(raw.rstrip(".,);]")) for raw in DOI_RE.findall(body)}
    candidates = {doi for doi in candidates if doi}
    return next(iter(candidates)) if len(candidates) == 1 else ""


def _openalex_work_key(value: Any) -> str:
    text = str(value or "").strip().rstrip("/")
    if not text:
        return ""
    return text.rsplit("/", 1)[-1].lower()


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


def _crossref_authors(payload: dict[str, Any] | None) -> list[str]:
    authors = ((payload or {}).get("message") or {}).get("author") or []
    names: list[str] = []
    for author in authors:
        family = str((author or {}).get("family") or "").strip()
        if family:
            names.append(family)
    return names


def _crossref_journal(payload: dict[str, Any] | None) -> str:
    containers = ((payload or {}).get("message") or {}).get("container-title") or []
    return str(containers[0]) if containers else ""


def _crossref_published_year(payload: dict[str, Any] | None) -> str:
    message = (payload or {}).get("message") or {}
    for key in ("published-print", "published-online", "published", "issued", "created", "deposited"):
        date_parts = (message.get(key) or {}).get("date-parts") or []
        if date_parts and date_parts[0]:
            year = str(date_parts[0][0])
            if _YEAR_RE.fullmatch(year):
                return year
    return ""


def _reference_author_prefix(reference_line: str) -> str:
    year_match = _YEAR_RE.search(reference_line or "")
    if not year_match:
        return ""
    prefix = reference_line[: year_match.start()]
    return prefix if len(_title_tokens(prefix)) >= 2 else ""


def _reference_has_journal_context(reference_line: str) -> bool:
    journal_cues = {
        "journal", "proceedings", "transactions", "letters", "annals", "archives",
        "bulletin", "review", "reviews", "reports", "medicine", "science",
    }
    return bool(_title_tokens(reference_line).intersection(journal_cues))


def _reference_years(reference_line: str) -> set[str]:
    clean = DOI_RE.sub("", reference_line or "")
    clean = PMID_RE.sub("", clean)
    clean = PMCID_RE.sub("", clean)
    return set(_YEAR_RE.findall(clean))


def _pubpeer_discussion_count(payload: Any) -> int:
    if payload is None:
        return 0
    if isinstance(payload, list):
        return sum(_pubpeer_discussion_count(item) for item in payload)
    if not isinstance(payload, dict):
        return 0
    for key in (
        "comments_count",
        "comment_count",
        "num_comments",
        "n_comments",
        "total_comments",
        "nb_comments",
        "comments",
    ):
        value = payload.get(key)
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, list):
            return len(value)
    if payload.get("has_comments") is True or payload.get("has_discussion") is True:
        return 1
    for key in ("results", "publications", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return sum(_pubpeer_discussion_count(item) for item in value)
        if isinstance(value, dict):
            count = _pubpeer_discussion_count(value)
            if count:
                return count
    return 0


def _ncbi_title(payload: dict[str, Any] | None, pmid: str) -> str:
    return str(((payload or {}).get("result") or {}).get(pmid, {}).get("title") or "")


def _metadata_failure_kind(records: list[str]) -> str:
    text = " ".join(records).lower()
    if not text:
        return ""
    if "http error 404" in text or "not found" in text:
        return "not_found"
    if "status=error" in text:
        return "service_error"
    if "error" in text or "timeout" in text or "temporarily" in text:
        return "service_unavailable"
    return ""


def analyze_references(source: Path, config: AuditConfig | None = None) -> TableResult:
    config = config or _env_config()
    findings: list[Finding] = []
    text = _extract_reference_text(source, config, findings)
    raw_dois = sorted({doi.rstrip(".,);]") for doi in DOI_RE.findall(text)})
    normalized_by_raw = {raw: normalize_doi(raw) for raw in raw_dois}
    dois = sorted({doi for doi in normalized_by_raw.values() if doi})
    skipped_dois = [raw for raw, doi in normalized_by_raw.items() if not doi]
    pmids = sorted(set(PMID_RE.findall(text)))
    pmcids = sorted({value if value.upper().startswith("PMC") else f"PMC{value}" for value in PMCID_RE.findall(text)})
    reference_lines = [m.group("body").strip() for m in REFERENCE_LINE_RE.finditer(text)]
    reference_lines = [
        line
        for line in reference_lines
        if DOI_RE.search(line) or PMID_RE.search(line) or PMCID_RE.search(line) or re.search(r"\(\d{4}\)|\b20\d\d\b|\b19\d\d\b", line)
    ]

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
    elif not dois and not pmids and not pmcids:
        findings.append(
            finding(
                str(source), "low", "Reference identifier missing", "DOI/PMID",
                "No DOI, PMID, or PMCID found; automatic verification coverage is limited.",
                f"Candidate reference lines={len(reference_lines)}, DOI=0, PMID=0, PMCID=0",
                "Supplement with DOI/PMID or provide structured reference tables to reduce miscitation and fabricated reference risks.",
                tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
            )
        )
    else:
        if skipped_dois:
            findings.append(
                finding(
                    str(source), "info", "DOI extraction normalization skipped", "DOI",
                    "Some DOI-like strings were excluded because they appear to be PDF extraction fragments or metadata-glued identifiers.",
                    f"skipped={len(skipped_dois)}; examples={skipped_dois[:5]}",
                    "Use editable references or a structured reference export to verify these identifiers.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                    confidence_basis="Extraction-quality record; not a review-priority signal.",
                )
            )
        findings.append(
            finding(
                str(source), "info", "Reference identifier parsing", "DOI/PMID",
                "Parseable reference identifiers found.",
                f"DOI={len(dois)}, skipped_doi_like={len(skipped_dois)}, PMID={len(pmids)}, PMCID={len(pmcids)}, candidate reference lines={len(reference_lines)}",
                "For high-risk citations, manually verify title, author, year, and in-text claim consistency.",
                tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                calculation_trace="Regex extraction of DOI and PMID; external metadata queries require PCR_ENABLE_EXTERNAL_LOOKUPS=1.",
            )
        )

    if not _external_enabled(config):
        if dois or pmids or pmcids:
            findings.append(
                finding(
                    str(source), "info", "External metadata verification not enabled", "Crossref/OpenAlex/PubPeer/NCBI",
                    "Default local/private runs do not send manuscript or reference information to external APIs.",
                    "Crossref, OpenAlex, PubPeer, and NCBI E-utilities are only queried after using --external-lookups or setting PCR_ENABLE_EXTERNAL_LOOKUPS=1.",
                    "For production use, configure caching, rate limiting, and data export disclosure.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                    dependency_status="external_lookup_disabled",
                    confidence_basis="Compliance downgrade record; not a data risk signal.",
                )
            )
        return TableResult("reference_audit", 0, 0, findings)

    current_doi = _current_work_doi(text)
    current_referenced_works: set[str] = set()
    current_openalex_record = ""
    if current_doi:
        encoded_current = urllib.parse.quote(current_doi, safe="")
        current_openalex, current_openalex_record, _cache_hit = _cached_lookup(
            "openalex_current_work",
            current_doi,
            f"https://api.openalex.org/works/https://doi.org/{encoded_current}",
            config,
            lambda payload: f"id={(payload or {}).get('id')}; referenced_works={len((payload or {}).get('referenced_works') or [])}",
        )
        current_referenced_works = {
            key
            for key in (_openalex_work_key(value) for value in ((current_openalex or {}).get("referenced_works") or []))
            if key
        }

    lookup_limit = _external_lookup_limit(config)
    reference_dois = [doi for doi in dois if doi != current_doi]
    for doi in reference_dois[:lookup_limit]:
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
            reference_work_key = _openalex_work_key(openalex.get("id"))
            if current_doi and doi != current_doi and current_referenced_works and reference_work_key and reference_work_key not in current_referenced_works:
                findings.append(
                    finding(
                        str(source), "low", "OpenAlex reference network missing", doi,
                        "The current work's OpenAlex referenced_works list does not include this reference DOI's OpenAlex work id.",
                        f"current_doi={current_doi}; reference_openalex_id={openalex.get('id')}; current_referenced_works_count={len(current_referenced_works)}",
                        "Treat this as a weak citation-network coverage signal. Manually verify the current work DOI, manuscript version, and reference list before drawing conclusions.",
                        tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                        external_records="; ".join(record for record in [current_openalex_record, *records] if record),
                        confidence_basis="Runs only when a unique DOI appears before the references section and OpenAlex returns a non-empty referenced_works list for that current work; OpenAlex reference coverage can be incomplete.",
                    )
                )
        pubpeer, pubpeer_record, _cache_hit = _cached_lookup(
            "pubpeer",
            doi,
            "https://pubpeer.com/api/search?" + urllib.parse.urlencode({"doi": doi}),
            config,
            lambda payload: f"discussion_count={_pubpeer_discussion_count(payload)}",
        )
        records.append(pubpeer_record)
        pubpeer_discussions = _pubpeer_discussion_count(pubpeer)
        if pubpeer_discussions:
            findings.append(
                finding(
                    str(source), "medium", "Post-publication discussion signal", doi,
                    "PubPeer search indicates this DOI has post-publication discussion records.",
                    f"pubpeer_discussion_count={pubpeer_discussions}; {pubpeer_record}",
                    "Review the PubPeer thread manually; comments may be minor, positive, unresolved, or answered by authors and should not be treated as a misconduct finding.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                    external_records=pubpeer_record,
                    confidence_basis="Counts recognizable PubPeer discussion/comment fields only; search hits without explicit discussion indicators are not treated as risk signals.",
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
        if crossref and reference_line:
            crossref_authors = _crossref_authors(crossref)
            author_prefix = _reference_author_prefix(reference_line)
            if crossref_authors and author_prefix:
                expected_author_tokens = {
                    token
                    for author in crossref_authors[:3]
                    for token in _title_tokens(author)
                }
                reported_author_tokens = _title_tokens(author_prefix)
                if expected_author_tokens and expected_author_tokens.isdisjoint(reported_author_tokens):
                    findings.append(
                        finding(
                            str(source), "medium", "DOI author mismatch", doi,
                            "Manuscript reference line author segment is inconsistent with Crossref returned authors.",
                            f"reported_authors={author_prefix[:140]}; crossref_authors={', '.join(crossref_authors[:5])}",
                            "Manually verify whether DOI is attached to the wrong reference or the author list was copied from another citation.",
                            tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                            external_records="; ".join(records),
                            confidence_basis="Compares normalized family-name tokens from the reference author segment before the year against Crossref family names; short or unstructured reference lines are skipped.",
                        )
                    )
            crossref_year = _crossref_published_year(crossref)
            reported_years = _reference_years(reference_line)
            if crossref_year and reported_years and crossref_year not in reported_years:
                findings.append(
                    finding(
                        str(source), "medium", "DOI publication date mismatch", doi,
                        "Manuscript reference line year is inconsistent with Crossref returned publication year.",
                        f"reported_years={sorted(reported_years)}; crossref_year={crossref_year}; reported_line={reference_line[:180]}",
                        "Manually verify whether DOI is attached to the wrong reference, the year is mistyped, or print/online publication dates need reconciliation.",
                        tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                        external_records="; ".join(records),
                    )
                )
            crossref_journal = _crossref_journal(crossref)
            if crossref_journal and _reference_has_journal_context(reference_line):
                overlap = _token_overlap(reference_line, crossref_journal)
                if overlap < 0.35:
                    findings.append(
                        finding(
                            str(source), "medium", "DOI journal mismatch", doi,
                            "Manuscript reference line journal/source appears inconsistent with Crossref returned container title.",
                            f"overlap={overlap:.2f}; reported_line={reference_line[:180]}; crossref_journal={crossref_journal[:180]}",
                            "Manually verify whether DOI is attached to the wrong source or the journal/source title was copied from another citation.",
                            tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                            external_records="; ".join(records),
                            confidence_basis="Only runs when the reference line contains journal/source cue words; missing journal fields are not treated as mismatches.",
                        )
                    )
        failure_kind = _metadata_failure_kind(records)
        if not crossref and not openalex and failure_kind == "not_found":
            findings.append(
                finding(
                    str(source), "medium", "DOI external metadata absent", doi,
                    "External metadata services returned a not-found response for this normalized DOI.",
                    "; ".join(records),
                    "Verify whether DOI is misspelled, unregistered, belongs to a record type not covered by the queried services, or represents a fabricated/unverifiable citation.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                    external_records="; ".join(records),
                    confidence_basis="External services returned a definitive not-found response after DOI normalization; treat as a review-priority citation verification signal rather than a tooling failure.",
                )
            )
        elif not crossref and not openalex and failure_kind:
            findings.append(
                finding(
                    str(source), "info", "DOI metadata lookup unresolved", doi,
                    "External DOI metadata lookup did not complete with a usable response.",
                    "; ".join(records),
                    "Retry with cache/network available or verify from the structured reference library.",
                    tool_id="reference_audit", tool_name="Reference Audit", input_type="reference_list",
                    dependency_status=failure_kind,
                    external_records="; ".join(records),
                    confidence_basis="External lookup status record; not a review-priority signal.",
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
    for pmid in pmids[:lookup_limit]:
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
