from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript is not installed")


def test_scrutiny_cli_writes_standard_json_even_when_package_missing(tmp_path: Path) -> None:
    script = ROOT / "tools" / "r" / "pcr_scrutiny" / "pcr-scrutiny"
    source = ROOT / "examples" / "summary_stat_sample.csv"
    out = tmp_path / "scrutiny.json"

    proc = subprocess.run([str(script), str(source), "--json", str(out)], capture_output=True, text=True)

    assert proc.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tool_id"] == "r_scrutiny"
    assert payload["detector_runtime"] == "r"
    assert payload["findings"]


def test_statcheck_cli_writes_standard_json_even_when_package_missing(tmp_path: Path) -> None:
    script = ROOT / "tools" / "r" / "pcr_statcheck" / "pcr-statcheck"
    source = tmp_path / "stats.txt"
    source.write_text("A result was reported as t(28)=2.20, p<.05.", encoding="utf-8")
    out = tmp_path / "statcheck.json"

    proc = subprocess.run([str(script), str(source), "--json", str(out)], capture_output=True, text=True)

    assert proc.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tool_id"] == "r_statcheck"
    assert payload["detector_runtime"] == "r"
    assert payload["findings"]


def test_sprite_cli_writes_standard_json_even_when_package_missing(tmp_path: Path) -> None:
    script = ROOT / "tools" / "r" / "pcr_sprite" / "pcr-sprite"
    source = ROOT / "examples" / "summary_stat_sample.csv"
    out = tmp_path / "sprite.json"

    proc = subprocess.run([str(script), str(source), "--json", str(out)], capture_output=True, text=True)

    assert proc.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tool_id"] == "r_rsprite2"
    assert payload["detector_runtime"] == "r"
    assert payload["findings"]
