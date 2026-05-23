from __future__ import annotations

import subprocess

import pandas as pd

from pcr_audit.detectors.r import adapters


def _completed(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["Rscript"], returncode=0, stdout=stdout, stderr="")


def test_r_statcheck_adapter_adds_confidence_fields(monkeypatch) -> None:
    stdout = (
        "Error,Decision_Error,Raw,Reported_P_Value,Computed_P_Value\n"
        "TRUE,FALSE,\"t(18)=2.10,p=.05\",.05,.049\n"
    )
    monkeypatch.setattr(adapters, "_run_r", lambda *args, **kwargs: _completed(stdout))

    findings = adapters.run_r_statcheck("paper", "t(18)=2.10,p=.05", "apa_statistical_text")

    assert findings
    assert all(0.0 <= finding.confidence_score <= 1.0 for finding in findings)
    assert all(finding.confidence_basis for finding in findings)


def test_r_scrutiny_adapter_adds_confidence_fields(monkeypatch) -> None:
    stdout = "check,row,status,detail\nGRIM,1,inconsistent,\"N=20, mean=2.13\"\n"
    monkeypatch.setattr(adapters, "_run_r", lambda *args, **kwargs: _completed(stdout))
    df = pd.DataFrame({"N": [20], "Mean": [2.13]})

    result = adapters.run_r_scrutiny("summary", df, "summary_statistics_table")

    assert result.findings
    assert all(0.0 <= finding.confidence_score <= 1.0 for finding in result.findings)
    assert all(finding.confidence_basis for finding in result.findings)


def test_r_rsprite2_adapter_adds_confidence_fields(monkeypatch) -> None:
    stdout = "check,row,status,detail\nSPRITE,1,not_found,\"N=20, mean=2.13, SD=0.4\"\n"
    monkeypatch.setattr(adapters, "_run_r", lambda *args, **kwargs: _completed(stdout))
    df = pd.DataFrame({"N": [20], "Mean": [2.13], "SD": [0.4]})

    result = adapters.run_r_rsprite2("summary", df, "likert_or_integer_scale_summary")

    assert result.findings
    assert all(0.0 <= finding.confidence_score <= 1.0 for finding in result.findings)
    assert all(finding.confidence_basis for finding in result.findings)
