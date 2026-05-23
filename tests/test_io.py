from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from pcr_audit.io import (
    clean_cell,
    extract_file,
    load_tables,
    markdown_out,
    read_csv,
    read_excel,
    read_json,
    read_text_source,
    safe_table_name,
    source_path,
    write_json,
)


class TestCleanCell:
    def test_none_returns_nan(self):
        result = clean_cell(None)
        assert pd.isna(result)

    def test_empty_string_returns_nan(self):
        result = clean_cell("")
        assert pd.isna(result)

    def test_whitespace_only_returns_nan(self):
        result = clean_cell("   ")
        assert pd.isna(result)

    def test_strips_whitespace(self):
        result = clean_cell("  hello  ")
        assert result == "hello"

    def test_preserves_non_empty_string(self):
        result = clean_cell("hello")
        assert result == "hello"


class TestSourcePath:
    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            source_path("/nonexistent/path/file.csv")

    def test_returns_resolved_path(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("a,b\n1,2")
        result = source_path(str(f))
        assert result.exists()
        assert result.name == "test.csv"


class TestWriteReadJson:
    def test_write_and_read_roundtrip(self, tmp_path):
        data = {"key": "value", "nested": {"a": 1}}
        p = tmp_path / "test.json"
        write_json(p, data)
        assert p.exists()
        loaded = read_json(p)
        assert loaded == data

    def test_write_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "deep" / "nested" / "test.json"
        write_json(p, {"x": 1})
        assert p.exists()


class TestMarkdownOut:
    def test_ensures_md_suffix(self):
        result = markdown_out("/tmp/report")
        assert result.suffix == ".md"

    def test_preserves_md_suffix(self):
        result = markdown_out("/tmp/report.md")
        assert result.suffix == ".md"


class TestReadCsv:
    def test_reads_simple_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("a,b,c\n1,2,3\n4,5,6")
        tables = read_csv(f)
        assert len(tables) == 1
        name, df = tables[0]
        assert name == "test"
        assert df.shape == (2, 3)
        assert list(df.columns) == ["a", "b", "c"]

    def test_handles_utf8_bom(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_bytes(b"\xef\xbb\xbfa,b\n1,2")
        tables = read_csv(f)
        assert len(tables) == 1


class TestReadExcel:
    def test_reads_single_sheet(self, tmp_path):
        f = tmp_path / "test.xlsx"
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        df.to_excel(f, index=False)
        tables = read_excel(f)
        assert len(tables) >= 1
        name, result_df = tables[0]
        assert result_df.shape == (2, 2)


class TestReadTextSource:
    def test_reads_txt_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world.")
        text = read_text_source(f)
        assert "Hello world." in text

    def test_reads_markdown_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nContent.")
        text = read_text_source(f)
        assert "Title" in text


class TestLoadTables:
    def test_loads_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("a,b\n1,2")
        tables = load_tables(f)
        assert len(tables) == 1

    def test_rejects_unsupported_type(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("data")
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_tables(f)


class TestSafeTableName:
    def test_preserves_alphanumeric(self):
        assert safe_table_name("hello_123", 1) == "hello_123"

    def test_replaces_special_chars(self):
        result = safe_table_name("sheet (1)", 1)
        assert "(" not in result

    def test_falls_back_to_index_for_empty(self):
        result = safe_table_name("   ", 5)
        assert result == "table_5"


class TestExtractFile:
    def test_extracts_csv_to_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("a,b\n1,2\n3,4")
        out_dir = tmp_path / "out"
        manifest = extract_file(f, out_dir)
        assert manifest["source"] == str(f)
        assert len(manifest["outputs"]) == 1
        assert manifest["outputs"][0]["kind"] == "table"
        csv_out = tmp_path / "out" / "01_test.csv"
        assert csv_out.exists()
