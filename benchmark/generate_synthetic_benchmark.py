from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent


def reset() -> None:
    for name in ("inputs", "reports", "corpus"):
        path = ROOT / name
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def write_raw_tables(inputs: Path) -> None:
    rows = []
    rng = np.random.default_rng(7)
    for i in range(60):
        group = ["A", "B", "C"][i // 20]
        assay = 10 + i * 0.5
        terminal_7 = float(f"{20 + i}.{(i % 10)}7")
        dominant = 999.0 if i < 35 else 100 + float(rng.normal(0, 1))
        missing_by_group = np.nan if group == "C" and i % 2 == 0 else float(rng.normal(50, 3))
        rows.append(
            {
                "subject_id": f"S{i + 1:03d}",
                "group": group,
                "assay_step": assay,
                "terminal_digit_signal": terminal_7,
                "dominant_value_signal": dominant,
                "missing_by_group": missing_by_group,
                "baseline_a": 100 + (i % 20) * 0.1,
                "baseline_b": 100 + (i % 20) * 0.1,
                "notes": "routine",
            }
        )
    df = pd.DataFrame(rows)
    df = pd.concat([df, df.iloc[[5, 6, 7, 8]]], ignore_index=True)
    df.to_csv(inputs / "raw_suspicious.csv", index=False)

    clean = pd.DataFrame(
        {
            "subject_id": [f"C{i + 1:03d}" for i in range(80)],
            "group": np.repeat(["A", "B"], 40),
            "outcome": rng.normal(20, 4, 80),
            "biomarker": rng.lognormal(1.0, 0.5, 80),
            "age": rng.integers(22, 68, 80),
        }
    )
    clean.to_csv(inputs / "raw_clean_control.csv", index=False)


def write_summary_tables(inputs: Path) -> None:
    rows = [
        {
            "score": "scale_a",
            "variable": "value",
            "n": 25,
            "mean": 10.0,
            "sd": 2.0,
            "se": 0.40,
            "ci_low": 9.17,
            "ci_high": 10.83,
            "count": 5,
            "percent": 20.0,
            "t": 2.50,
            "df": 24,
            "p": 0.0198,
        },
        {
            "score": "scale_b",
            "variable": "value",
            "n": 20,
            "mean": 5.0,
            "sd": 3.0,
            "se": 0.10,
            "ci_low": 4.70,
            "ci_high": 5.30,
            "count": 8,
            "percent": 25.0,
            "t": 3.00,
            "df": 19,
            "p": 0.20,
        },
        {
            "score": "scale_c",
            "variable": "value",
            "n": 18,
            "mean": 8.0,
            "sd": 1.8,
            "se": 0.10,
            "ci_low": 8.20,
            "ci_high": 7.80,
            "count": 3,
            "percent": 50.0,
            "t": 1.80,
            "df": 5,
            "p": 1.20,
        },
        {
            "score": "scale_d",
            "variable": "value",
            "n": 10,
            "mean": 12.0,
            "sd": -1.0,
            "se": 0.50,
            "ci_low": 11.1,
            "ci_high": 12.9,
            "count": 2,
            "percent": 20.0,
            "t": 1.00,
            "df": 9,
            "p": 0.0,
        },
    ]
    pd.DataFrame(rows).to_csv(inputs / "summary_suspicious.csv", index=False)

    values = [0.046, 0.047, 0.048, 0.049, 0.12, 0.2, 0.3, 0.4, 0.5, 0.6, 1.2, "bad"]
    pd.DataFrame({"test": [f"H{i}" for i in range(1, len(values) + 1)], "p": values}).to_csv(
        inputs / "p_values_suspicious.csv", index=False
    )


def write_texts(inputs: Path) -> None:
    (inputs / "apa_stats_suspicious.txt").write_text(
        "Participants in the treatment arm improved, t(28)=2.20, p=.90. "
        "The secondary contrast was also reported as F(1, 30)=5.00, p=.80.\n",
        encoding="utf-8",
    )
    (inputs / "external_refs_online.md").write_text(
        "Authors: Benchmark Network Probe\n\n"
        "This reference list is intended to exercise customer-facing reference integrity checks, "
        "not only network connectivity.\n\n"
        "References\n"
        "[1] Van Noorden R. A randomized oncology survival trial with unrelated endpoints. "
        "Nature. 2013. doi:10.1038/495426a. PMID:23538808\n"
        "[2] Missing DOI example. This identifier is intentionally not registered. "
        "doi:10.9999/pcr-benchmark-missing-doi\n",
        encoding="utf-8",
    )
    (inputs / "paper_refs_and_claims.md").write_text(
        "Authors: Alice Zhang, Bob Li\n\n"
        "This retrospective study used a standardized method and identical inclusion criteria [1]. "
        "The outcome was assessed with the same imaging workflow and statistical model [2].\n\n"
        "References\n"
        "[1] Example Trial. doi:10.1111/example.1\n"
        "[2] Example Review. doi:10.1111/example.2\n",
        encoding="utf-8",
    )


def demo_image(path: Path, duplicate_patch: bool = False) -> None:
    image = Image.new("RGB", (220, 150), "white")
    draw = ImageDraw.Draw(image)
    for x in range(20, 190, 28):
        draw.rectangle((x, 30, x + 12, 105), fill=(20, 20, 20))
    draw.ellipse((145, 45, 195, 95), fill=(120, 120, 120))
    if duplicate_patch:
        patch = image.crop((18, 25, 95, 112))
        image.paste(patch, (115, 30))
    image.save(path)


def write_images(inputs: Path) -> None:
    figures = inputs / "figures"
    figures.mkdir(exist_ok=True)
    demo_image(figures / "western_blot_panel_a.png")
    shutil.copy2(figures / "western_blot_panel_a.png", figures / "western_blot_panel_b.png")
    demo_image(figures / "copy_move_panel.png", duplicate_patch=True)
    Image.new("RGB", (50, 50), "white").save(figures / "low_resolution_control.png")


def write_code(inputs: Path) -> None:
    (inputs / "analysis_suspicious.py").write_text(
        "import pandas as pd\n"
        "df = pd.read_csv('project/data.csv').dropna()\n"
        "sig = df[df['p'] < 0.05] if 'p' in df else df\n"
        "print('rows', len(sig))\n",
        encoding="utf-8",
    )
    (inputs / "analysis_manual.do").write_text('display "manual rerun required"\n', encoding="utf-8")


def write_project(inputs: Path) -> None:
    project = inputs / "project_full"
    project.mkdir(exist_ok=True)
    pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0]}).to_csv(project / "data.csv", index=False)
    pd.DataFrame({"variable": ["value"], "n": [4], "mean": [99.0], "sd": [1.0]}).to_excel(
        project / "paper_tables.xlsx", index=False
    )
    (project / "paper.md").write_text(
        "Authors: Alice Zhang, Bob Li\n"
        "The outcome was assessed with the same imaging workflow and statistical model [1].\n\n"
        "References\n[1] Example Trial. doi:10.1111/example.1\n",
        encoding="utf-8",
    )
    (project / "analysis.py").write_text(
        "import pandas as pd\n"
        "df = pd.read_csv('data.csv')\n"
        "pd.DataFrame({'variable':['value'], 'n':[len(df)], 'mean':[df.value.mean()], 'sd':[df.value.std()]}).to_csv('script_summary.csv', index=False)\n",
        encoding="utf-8",
    )
    figs = project / "figures"
    figs.mkdir(exist_ok=True)
    demo_image(figs / "western_blot_project_a.png")
    shutil.copy2(figs / "western_blot_project_a.png", figs / "western_blot_project_b.png")
    (project / "pcr-project.json").write_text(
        json.dumps(
            {
                "project_id": "synthetic-full",
                "title": "Synthetic full coverage project",
                "materials": [
                    {"path": "paper.md", "role": "manuscript"},
                    {"path": "paper_tables.xlsx", "role": "supplement"},
                    {"path": "data.csv", "role": "raw_data"},
                    {"path": "analysis.py", "role": "analysis_code"},
                    {"path": "figures", "role": "figures"},
                ],
                "settings": {"external_lookups": False},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    corpus = ROOT / "corpus"
    for name in ("project_a", "project_b"):
        item = corpus / name
        item.mkdir(parents=True, exist_ok=True)
        (item / "paper.md").write_text((project / "paper.md").read_text(encoding="utf-8"), encoding="utf-8")

    external = inputs / "project_external"
    external.mkdir(exist_ok=True)
    shutil.copy2(inputs / "external_refs_online.md", external / "paper.md")
    (external / "pcr-project.json").write_text(
        json.dumps(
            {
                "project_id": "synthetic-external",
                "title": "Synthetic external lookup coverage project",
                "materials": [{"path": "paper.md", "role": "manuscript"}],
                "settings": {"external_lookups": True},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def write_ground_truth() -> None:
    (ROOT / "ground_truth.json").write_text(
        json.dumps(
            {
                "expected_signal_tools": [
                    "raw_data_rules",
                    "crosscheck",
                    "p_value_distribution",
                    "r_statcheck",
                    "r_scrutiny",
                    "r_rsprite2",
                    "reference_audit",
                    "citation_claim_check",
                    "papermill_light_signals",
                    "image_duplicate_internal",
                    "image_copy_move_internal",
                    "image_metadata_audit",
                    "western_blot_review_list",
                    "code_rerun_audit",
                    "code_rerun_execute",
                    "data_trace_crosscheck",
                    "provenance_hash",
                    "provenance_chain_verify",
                    "papermill_network_signals",
                ],
                "known_limitations": [
                    "R 工具输出取决于 statcheck/scrutiny/rsprite2 对列名和文本格式的解析。",
                    "图像 copy-move 是弱信号，低纹理或规则重复图形可能产生误报/漏报。",
                    "项目级文献外部查询在此基准中关闭，未测试 Crossref/OpenAlex/NCBI 网络可靠性。",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    reset()
    inputs = ROOT / "inputs"
    write_raw_tables(inputs)
    write_summary_tables(inputs)
    write_texts(inputs)
    write_images(inputs)
    write_code(inputs)
    write_project(inputs)
    write_ground_truth()
    print(ROOT)


if __name__ == "__main__":
    main()
