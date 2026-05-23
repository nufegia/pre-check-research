from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import numpy as np
import pandas as pd


def source_path(path: str) -> Path:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")
    return source


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_out(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if path.suffix != ".md":
        path = path.with_suffix(".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def clean_cell(value: Any) -> Any:
    if value is None:
        return np.nan
    if isinstance(value, str):
        value = value.strip()
        return np.nan if value == "" else value
    return value


def read_csv(path: Path) -> list[tuple[str, pd.DataFrame]]:
    encodings = ["utf-8-sig", "utf-8", "gb18030", "latin1"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return [(path.stem, pd.read_csv(path, encoding=encoding).map(clean_cell))]
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Cannot read CSV: {last_error}")


def read_excel(path: Path) -> list[tuple[str, pd.DataFrame]]:
    sheets = pd.read_excel(path, sheet_name=None)
    return [(name, df.map(clean_cell)) for name, df in sheets.items()]


def read_docx_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        document = zf.read("word/document.xml")
    root = ElementTree.fromstring(document)
    tables: list[tuple[str, pd.DataFrame]] = []
    for idx, table in enumerate(root.findall(".//w:tbl", ns), start=1):
        rows = []
        for tr in table.findall(".//w:tr", ns):
            cells = []
            for tc in tr.findall("./w:tc", ns):
                text_parts = [node.text or "" for node in tc.findall(".//w:t", ns)]
                cells.append("".join(text_parts).strip())
            if cells:
                rows.append(cells)
        if not rows:
            continue
        width = max(len(row) for row in rows)
        normalized = [row + [""] * (width - len(row)) for row in rows]
        header = normalized[0]
        body = normalized[1:] if len(normalized) > 1 else []
        tables.append((f"docx_table_{idx}", pd.DataFrame(body, columns=header).map(clean_cell)))
    return tables


def read_pdf_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    import pdfplumber

    tables: list[tuple[str, pd.DataFrame]] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            for table_idx, table in enumerate(page.extract_tables() or [], start=1):
                if not table:
                    continue
                width = max(len(row or []) for row in table)
                normalized = [(row or []) + [""] * (width - len(row or [])) for row in table]
                header = [str(item or "") for item in normalized[0]]
                body = normalized[1:] if len(normalized) > 1 else []
                tables.append((f"pdf_p{page_idx}_table_{table_idx}", pd.DataFrame(body, columns=header).map(clean_cell)))
    return tables


def load_tables(path: Path) -> list[tuple[str, pd.DataFrame]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return read_excel(path)
    if suffix == ".docx":
        return read_docx_tables(path)
    if suffix == ".pdf":
        return read_pdf_tables(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def read_text_source(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix in {".txt", ".md", ".bib", ".ris"}:
        return source.read_text(encoding="utf-8")
    if suffix == ".docx":
        with zipfile.ZipFile(str(source)) as zf:
            doc = zf.read("word/document.xml")
        root = ElementTree.fromstring(doc)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", ns):
            texts = [text.text or "" for text in paragraph.findall(".//w:t", ns)]
            paragraphs.append("".join(texts))
        return "\n".join(paragraphs)
    if suffix == ".pdf":
        import pdfplumber

        texts = []
        with pdfplumber.open(str(source)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
        return "\n".join(texts)
    return ""


def write_extracted_text(source: Path, workdir: Path) -> Path | None:
    if source.suffix.lower() not in {".pdf", ".docx"}:
        return None
    text = read_text_source(source)
    if not text:
        return None
    out_path = workdir / f"{source.stem}_extracted.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def safe_table_name(name: str, index: int) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name.strip())
    return cleaned or f"table_{index}"


def extract_file(source: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    for idx, (name, df) in enumerate(load_tables(source), start=1):
        out_path = out_dir / f"{idx:02d}_{safe_table_name(name, idx)}.csv"
        df.to_csv(out_path, index=False)
        outputs.append(
            {
                "name": name,
                "kind": "table",
                "path": str(out_path),
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
            }
        )
    notes = []
    if source.suffix.lower() in {".pdf", ".docx"}:
        notes.append("Input was extracted from a document; merged cells, footnotes, and complex layouts may require manual review.")
    return {
        "source": str(source),
        "tool_id": "pcr_extract",
        "tool_name": "PCR Extract",
        "detector_runtime": "python",
        "dependency_status": "ready",
        "outputs": outputs,
        "notes": notes,
    }
