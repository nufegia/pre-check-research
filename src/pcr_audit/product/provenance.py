from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from pcr_audit.models import Finding, TableResult
from pcr_audit.product.common import _now_iso, finding, is_audit_material_path, iter_audit_files
from pcr_audit.product.project_manifest import infer_role, parse_project_spec

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


def provenance_payload_to_result(source: Path, payload: dict[str, Any], tool_name: str = "Hash Version Chain Verification") -> TableResult:
    findings: list[Finding] = []
    statuses = payload.get("statuses") or payload.get("changes") or []
    if not statuses:
        findings.append(
            finding(
                str(source), "info", tool_name, "ledger",
                "Hash version chain ledger has no reportable file statuses.",
                f"ledger={payload.get('ledger')}; records={payload.get('records', 0)}",
                "Run provenance record to register project materials first, then execute verify/diff.",
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
                f"Hash version chain status: {status}",
                json.dumps(item, ensure_ascii=False, sort_keys=True),
                "For changed/modified/missing/new files, verify original records, upload batches, and operator notes.",
                tool_id="provenance_chain_verify", tool_name=tool_name, input_type="raw_file_bundle",
                calculation_trace="Read JSONL ledger latest records and recompute SHA-256 for current files.",
                confidence_basis="SHA-256 and file size are deterministic integrity evidence; they do not prove experimental authenticity.",
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
                str(source), "info", "SHA-256 File Record", path.name,
                "File hash and basic metadata computed.",
                f"sha256={digest}; size={stat.st_size}; mtime={int(stat.st_mtime)}",
                "Save this JSON as version chain evidence; hashes only prove files have not changed subsequently, not that experiments actually occurred.",
                tool_id="provenance_hash", tool_name="Original File Hash Record", input_type="raw_file_bundle",
                calculation_trace="Local byte-read of file and SHA-256 computation.",
                confidence_basis="Hash is deterministic file integrity evidence, but not experimental authenticity evidence.",
            )
        )
    return TableResult("provenance_hash", len(paths), 0, findings)
