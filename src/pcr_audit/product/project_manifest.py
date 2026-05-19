from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pcr_audit.models import TableResult
from pcr_audit.product.common import (
    CODE_SUFFIXES,
    DATA_SUFFIXES,
    DOC_SUFFIXES,
    IMAGE_SUFFIXES,
    MATERIAL_ROLES,
    AuditConfig,
    Material,
    ProjectSpec,
    _env_config,
    finding,
    is_audit_material_path,
    iter_audit_files,
)

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
