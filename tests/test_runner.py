from __future__ import annotations

from pathlib import Path

from pcr_audit.runner import (
    _exception_evidence,
    run_audit,
    run_project_audit,
)


class TestExceptionEvidence:
    def test_formats_simple_error(self):
        result = _exception_evidence(ValueError("bad input"))
        assert "ValueError" in result
        assert "bad input" in result

    def test_truncates_long_message(self):
        long_msg = "x" * 600
        result = _exception_evidence(RuntimeError(long_msg))
        assert "RuntimeError" in result
        assert len(result) < 520  # 500 limit + class prefix

    def test_handles_empty_message(self):
        result = _exception_evidence(Exception())
        assert "Exception" in result


class TestRunAudit:
    def test_returns_zero_for_valid_input(self, tmp_path: Path):
        source = tmp_path / "test.csv"
        source.write_text("a,b,c\n1,2,3\n4,5,6\n7,8,9\n10,11,12\n13,14,15\n16,17,18\n19,20,21\n22,23,24\n25,26,27\n28,29,30\n31,32,33")
        out = tmp_path / "report.md"
        json_out = tmp_path / "report.json"
        exit_code = run_audit(source, out, json_out, tmp_path / "work", "auto")
        assert exit_code == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "# Data Audit Report" in content

    def test_dry_run_writes_route_only(self, tmp_path: Path):
        source = tmp_path / "test.csv"
        source.write_text("a,b,c\n1,2,3\n4,5,6\n7,8,9")
        out = tmp_path / "report.md"
        json_out = tmp_path / "report.json"
        exit_code = run_audit(source, out, json_out, tmp_path / "work", "auto", dry_run=True)
        assert exit_code == 0
        assert json_out.exists()

    def test_returns_zero_with_info_when_no_tools_match(self, tmp_path: Path):
        source = tmp_path / "empty.unknown"
        source.write_text("nothing useful")
        out = tmp_path / "report.md"
        exit_code = run_audit(source, out, None, tmp_path / "work", "auto")
        assert exit_code == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "no applicable tools" in content.lower() or "info" in content.lower()

    def test_run_with_explicit_scenario(self, tmp_path: Path):
        source = tmp_path / "test.csv"
        source.write_text("n,mean,sd\n30,3.5,0.8\n25,4.1,1.2")
        out = tmp_path / "report.md"
        json_out = tmp_path / "report.json"
        exit_code = run_audit(source, out, json_out, tmp_path / "work", "summary")
        assert exit_code == 0
        assert out.exists()


class TestRunProjectAudit:
    def test_minimal_project_runs(self, tmp_path: Path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        manifest = project_dir / "pcr-project.json"
        import json
        manifest.write_text(json.dumps({
            "materials": [
                {"path": "data.csv", "role": "raw_data"},
            ],
        }))
        csv = project_dir / "data.csv"
        csv.write_text("a,b,c\n1,2,3\n4,5,6\n7,8,9\n10,11,12\n13,14,15\n16,17,18\n19,20,21\n22,23,24\n25,26,27\n28,29,30\n31,32,33")
        out = tmp_path / "project-report.md"
        json_out = tmp_path / "project-report.json"
        exit_code = run_project_audit(
            project_dir, out, json_out, tmp_path / "work",
            external_lookups=False, rerun_code=False,
        )
        assert exit_code == 0
        assert out.exists()

    def test_empty_project_with_no_materials(self, tmp_path: Path):
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()
        import json
        (project_dir / "pcr-project.json").write_text(json.dumps({"materials": []}))
        out = tmp_path / "report.md"
        exit_code = run_project_audit(
            project_dir, out, None, tmp_path / "work",
            external_lookups=False, rerun_code=False,
        )
        assert exit_code == 0
