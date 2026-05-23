from __future__ import annotations

import json
import math
import re
import sys
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from pcr_audit.models import Finding, TableResult
from pcr_audit.product.common import IMAGE_SUFFIXES, finding, iter_audit_files

PDF_PAGE_IMAGE_MAX_COVERAGE = 0.72
PDF_PAGE_IMAGE_MIN_MARGIN = 18.0

def iter_image_files(source: Path) -> list[Path]:
    if source.is_dir():
        return [path for path in iter_audit_files(source) if path.suffix.lower() in IMAGE_SUFFIXES]
    return [source] if source.suffix.lower() in IMAGE_SUFFIXES else []


def extract_docx_images(source: Path, out_dir: Path) -> list[Path]:
    images: list[Path] = []
    if source.suffix.lower() != ".docx":
        return images
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as zf:
        for item in zf.namelist():
            if not item.startswith("word/media/"):
                continue
            suffix = Path(item).suffix.lower()
            if suffix not in IMAGE_SUFFIXES:
                continue
            out = out_dir / Path(item).name
            out.write_bytes(zf.read(item))
            images.append(out)
    return images


def _pdf_image_bbox(item: dict[str, Any]) -> tuple[float, float, float, float] | None:
    try:
        x0 = float(item["x0"])
        top = float(item["top"])
        x1 = float(item["x1"])
        bottom = float(item["bottom"])
    except Exception:
        return None
    if x1 <= x0 or bottom <= top:
        return None
    return x0, top, x1, bottom


def _pdf_image_coverage(page: Any, bbox: tuple[float, float, float, float]) -> float:
    page_width = float(getattr(page, "width", 0) or 0)
    page_height = float(getattr(page, "height", 0) or 0)
    page_area = page_width * page_height
    if page_area <= 0:
        return 0.0
    x0, top, x1, bottom = bbox
    return max(0.0, (x1 - x0) * (bottom - top)) / page_area


def _is_page_sized_pdf_image(page: Any, bbox: tuple[float, float, float, float]) -> bool:
    page_width = float(getattr(page, "width", 0) or 0)
    page_height = float(getattr(page, "height", 0) or 0)
    if page_width <= 0 or page_height <= 0:
        return False
    x0, top, x1, bottom = bbox
    near_edges = (
        x0 <= PDF_PAGE_IMAGE_MIN_MARGIN
        and top <= PDF_PAGE_IMAGE_MIN_MARGIN
        and page_width - x1 <= PDF_PAGE_IMAGE_MIN_MARGIN
        and page_height - bottom <= PDF_PAGE_IMAGE_MIN_MARGIN
    )
    return _pdf_image_coverage(page, bbox) >= PDF_PAGE_IMAGE_MAX_COVERAGE or near_edges


def extract_pdf_images(source: Path, out_dir: Path) -> tuple[list[Path], str]:
    images: list[Path] = []
    if source.suffix.lower() != ".pdf":
        return images, ""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import pdfplumber
    except Exception as exc:
        return images, f"pdfplumber_unavailable={exc}"
    Image = _pil_image_module()
    if Image is None:
        return images, "pillow_unavailable"
    notes: list[str] = []
    try:
        with pdfplumber.open(str(source)) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                for image_no, item in enumerate(page.images or [], start=1):
                    bbox = _pdf_image_bbox(item)
                    if bbox is None:
                        notes.append(f"p{page_no}/img{image_no}:invalid_bbox")
                        continue
                    if _is_page_sized_pdf_image(page, bbox):
                        notes.append(
                            f"p{page_no}/img{image_no}:skipped_page_sized_image coverage={_pdf_image_coverage(page, bbox):.2f}"
                        )
                        continue
                    out = out_dir / f"{source.stem}_p{page_no}_img{image_no}.png"
                    saved = False
                    stream = item.get("stream")
                    if stream is not None:
                        try:
                            data = stream.get_data()
                            with Image.open(BytesIO(data)) as img:
                                img.save(out)
                            saved = True
                        except Exception:
                            pass
                    if not saved:
                        try:
                            rendered = page.crop(bbox).to_image(resolution=150).original
                            rendered.save(out)
                            saved = True
                        except Exception as exc:
                            notes.append(f"p{page_no}/img{image_no}:{exc}")
                    if saved:
                        images.append(out)
    except Exception as exc:
        return images, str(exc)
    return images, "; ".join(notes[:5])


def _compat_extract_pdf_images(source: Path, out_dir: Path) -> tuple[list[Path], str]:
    facade = sys.modules.get("pcr_audit.product_detectors")
    override = getattr(facade, "extract_pdf_images", None) if facade is not None else None
    if override is not None and override is not extract_pdf_images and override is not _compat_extract_pdf_images:
        return override(source, out_dir)
    return extract_pdf_images(source, out_dir)


def _pil_image_module():
    try:
        from PIL import Image
    except Exception:
        return None
    return Image


def _average_hash(path: Path, hash_size: int = 8) -> tuple[int, str] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((hash_size, hash_size))
            arr = np.asarray(gray, dtype=float)
    except Exception:
        return None
    avg = float(arr.mean())
    bits = 0
    for value in arr.flatten():
        bits = (bits << 1) | int(value >= avg)
    return bits, f"{bits:0{hash_size * hash_size // 4}x}"


def _difference_hash(path: Path, hash_size: int = 8) -> tuple[int, str] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((hash_size + 1, hash_size))
            arr = np.asarray(gray, dtype=float)
    except Exception:
        return None
    bits = 0
    for value in (arr[:, 1:] > arr[:, :-1]).flatten():
        bits = (bits << 1) | int(value)
    return bits, f"{bits:0{hash_size * hash_size // 4}x}"


def _phash_from_array(arr: np.ndarray, hash_size: int = 8) -> tuple[int, str]:
    from scipy.fftpack import dct

    dct_rows = dct(arr, axis=0, norm="ortho")
    dct_cols = dct(dct_rows, axis=1, norm="ortho")
    low = dct_cols[:hash_size, :hash_size]
    median = float(np.median(low[1:, 1:]))
    bits = 0
    for value in low.flatten():
        bits = (bits << 1) | int(value >= median)
    return bits, f"{bits:0{hash_size * hash_size // 4}x}"


def _perceptual_hash(path: Path, hash_size: int = 8) -> tuple[int, str] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((32, 32))
            arr = np.asarray(gray, dtype=float)
        return _phash_from_array(arr, hash_size)
    except Exception:
        return None


def image_fingerprints(path: Path) -> dict[str, Any]:
    fingerprints: dict[str, Any] = {}
    for name, fn in (("ahash", _average_hash), ("dhash", _difference_hash), ("phash", _perceptual_hash)):
        item = fn(path)
        if item is not None:
            fingerprints[name] = {"int": item[0], "hex": item[1]}
    return fingerprints


def _hamming(left: int, right: int) -> int:
    return int((left ^ right).bit_count())


def _hash_summary(hashes: dict[str, Any]) -> str:
    return ", ".join(f"{name}:{item.get('hex')}" for name, item in hashes.items())


def _transformed_phash_distances(left: Path, right: Path) -> tuple[str, int] | None:
    Image = _pil_image_module()
    if Image is None:
        return None
    left_hash = _perceptual_hash(left)
    if left_hash is None:
        return None
    transforms = {
        "original": lambda img: img,
        "flip_left_right": lambda img: img.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        "flip_top_bottom": lambda img: img.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
        "rotate_90": lambda img: img.rotate(90, expand=True),
        "rotate_180": lambda img: img.rotate(180, expand=True),
        "rotate_270": lambda img: img.rotate(270, expand=True),
    }
    best: tuple[str, int] | None = None
    try:
        with Image.open(right) as img:
            for name, transform in transforms.items():
                gray = transform(img).convert("L").resize((32, 32))
                arr = np.asarray(gray, dtype=float)
                right_hash, _right_hex = _phash_from_array(arr)
                distance = _hamming(left_hash[0], right_hash)
                if best is None or distance < best[1]:
                    best = (name, distance)
    except Exception:
        return None
    return best


def _orb_similarity(left: Path, right: Path) -> dict[str, Any] | None:
    try:
        import cv2
    except Exception:
        return None
    left_img = cv2.imread(str(left), cv2.IMREAD_GRAYSCALE)
    right_img = cv2.imread(str(right), cv2.IMREAD_GRAYSCALE)
    if left_img is None or right_img is None:
        return None
    orb = cv2.ORB_create(nfeatures=800)
    kp1, des1 = orb.detectAndCompute(left_img, None)
    kp2, des2 = orb.detectAndCompute(right_img, None)
    if des1 is None or des2 is None or not kp1 or not kp2:
        return {"good_matches": 0, "keypoints_left": len(kp1 or []), "keypoints_right": len(kp2 or [])}
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)
    good = [m for m in matches if m.distance <= 48]
    return {
        "good_matches": len(good),
        "keypoints_left": len(kp1),
        "keypoints_right": len(kp2),
        "median_distance": round(float(np.median([m.distance for m in good])), 2) if good else None,
    }


def _copy_move_matches(path: Path) -> dict[str, Any] | None:
    try:
        import cv2
    except Exception:
        return None
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    orb = cv2.ORB_create(nfeatures=1200)
    keypoints, descriptors = orb.detectAndCompute(img, None)
    if descriptors is None or len(keypoints) < 12:
        return {"matches": 0, "keypoints": len(keypoints or []), "samples": []}
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw_matches = matcher.knnMatch(descriptors, descriptors, k=3)
    samples = []
    vectors: list[tuple[int, int]] = []
    for matches in raw_matches:
        for match in matches:
            if match.queryIdx == match.trainIdx or match.distance > 36:
                continue
            p1 = keypoints[match.queryIdx].pt
            p2 = keypoints[match.trainIdx].pt
            spatial = math.dist(p1, p2)
            if spatial < 25:
                continue
            dx = int(round(p2[0] - p1[0]))
            dy = int(round(p2[1] - p1[1]))
            vectors.append((round(dx / 10) * 10, round(dy / 10) * 10))
            if len(samples) < 6:
                samples.append(
                    {
                        "from": [round(p1[0], 1), round(p1[1], 1)],
                        "to": [round(p2[0], 1), round(p2[1], 1)],
                        "distance": round(float(match.distance), 2),
                    }
                )
            break
    common = Counter(vectors).most_common(1)
    clustered = common[0][1] if common else 0
    return {"matches": len(vectors), "clustered_matches": clustered, "keypoints": len(keypoints), "samples": samples}


def _image_metadata_findings(source: Path, images: list[Path]) -> list[Finding]:
    Image = _pil_image_module()
    findings: list[Finding] = []
    if Image is None:
        return [
            finding(
                str(source), "info", "Image metadata dependency missing", "Pillow",
                "Missing Pillow; cannot read image metadata and brightness quality signals.",
                "dependency_missing=Pillow",
                "Install a trusted version of Pillow and retry; this notice does not count as a data risk.",
                tool_id="image_metadata_audit", tool_name="Image Metadata & Quality Screening",
                input_type="scientific_figure", dependency_status="dependency_missing",
            )
        ]
    for path in images:
        try:
            with Image.open(path) as img:
                exif_count = len(img.getexif() or {})
                arr = np.asarray(img.convert("L"), dtype=float)
                width, height = img.size
                fmt = img.format or path.suffix.lstrip(".").upper()
                mode = img.mode
                mean = float(arr.mean())
                std = float(arr.std())
        except Exception as exc:
            findings.append(
                finding(
                    str(source), "info", "Image metadata read failed", path.name,
                    "Image could not be read; metadata check skipped.",
                    str(exc),
                    "Verify whether the file is corrupted or the format is supported.",
                    tool_id="image_metadata_audit", tool_name="Image Metadata & Quality Screening",
                    input_type="scientific_figure", dependency_status="read_failed",
                )
            )
            continue
        evidence = f"format={fmt}; size={width}x{height}; mode={mode}; exif_fields={exif_count}; gray_mean={mean:.1f}; gray_std={std:.1f}"
        if width < 80 or height < 80:
            level, summary = "low", "Image resolution is low; may limit image forensics and human review."
        elif std < 4 or mean < 3 or mean > 252:
            level, summary = "low", "Image dynamic range is abnormally low or near all-black/all-white; confirm whether caused by export or compression pipeline."
        elif exif_count == 0 and fmt in {"JPEG", "TIFF"}:
            level, summary = "info", "Image does not contain readable EXIF metadata; this is common in paper layout or export pipelines."
        else:
            level, summary = "info", "Image metadata read complete; no built-in quality threshold signals found."
        findings.append(
            finding(
                str(source), level, "Image metadata and quality", path.name,
                summary,
                evidence,
                "Review against original instrument files, export pipeline, and uncompressed original images.",
                tool_id="image_metadata_audit", tool_name="Image Metadata & Quality Screening",
                input_type="scientific_figure",
            )
        )
    return findings


def analyze_images(source: Path, workdir: Path | None = None) -> list[TableResult]:
    workdir = workdir or source.with_suffix(".images")
    images = iter_image_files(source)
    if source.suffix.lower() == ".docx":
        images = extract_docx_images(source, workdir)
    pdf_note = ""
    if source.suffix.lower() == ".pdf":
        images, pdf_note = _compat_extract_pdf_images(source, workdir)
    findings_extract: list[Finding] = []
    findings_dup: list[Finding] = []
    findings_copy: list[Finding] = []
    findings_meta: list[Finding] = []
    findings_blot: list[Finding] = []

    if not images:
        findings_extract.append(
            finding(
                str(source), "info", "Image extraction", "figure",
                "No directly detectable image files found.",
                f"PDF image extraction is best-effort; DOCX can extract images under word/media. {pdf_note}",
                "If image integrity screening is needed, provide original images, DOCX manuscript, or a separate image directory.",
                tool_id="image_extract", tool_name="Image extraction", input_type="scientific_figure",
                dependency_status="insufficient_material",
            )
        )
        return [TableResult("image_extract", 0, 0, findings_extract)]

    findings_extract.append(
        finding(
            str(source), "info", "Image extraction", "figure",
            "Detectable images found.",
            f"Image count={len(images)}; examples={', '.join(path.name for path in images[:8])}",
            "For flagged duplicate or blot/gel images, review original uncropped images and figure legends.",
            tool_id="image_extract", tool_name="Image extraction", input_type="scientific_figure",
        )
    )

    hashes: list[tuple[Path, dict[str, Any]]] = []
    hash_missing = False
    for path in images:
        item = image_fingerprints(path)
        if not item:
            hash_missing = True
            continue
        hashes.append((path, item))
    if hash_missing:
        findings_dup.append(
            finding(
                str(source), "info", "Image dependency missing or read failed", "Pillow",
                "Some images could not compute perceptual hash.",
                "Pillow is required for local perceptual hashing; corrupted or special-format images are also skipped.",
                "Install a trusted version of Pillow and retry; do not treat this notice as an image risk.",
                tool_id="image_duplicate_internal", tool_name="Internal Duplicate Image Screening",
                input_type="scientific_figure", dependency_status="dependency_missing",
            )
        )
    for i, (left_path, left_hashes) in enumerate(hashes):
        for right_path, right_hashes in hashes[i + 1:]:
            distances = {
                name: _hamming(left_hashes[name]["int"], right_hashes[name]["int"])
                for name in sorted(set(left_hashes).intersection(right_hashes))
            }
            best_name, best_distance = min(distances.items(), key=lambda item: item[1]) if distances else ("none", 999)
            transform = _transformed_phash_distances(left_path, right_path)
            orb = _orb_similarity(left_path, right_path)
            orb_good = int((orb or {}).get("good_matches") or 0)
            is_hit = best_distance <= 6 or (transform is not None and transform[1] <= 8 and transform[0] != "original") or orb_good >= 18
            if is_hit:
                transform_text = f"{transform[0]}:{transform[1]}" if transform else "unavailable"
                orb_text = f"orb_good={orb_good}, keypoints={int((orb or {}).get('keypoints_left') or 0)}/{int((orb or {}).get('keypoints_right') or 0)}" if orb else "orb=unavailable"
                findings_dup.append(
                    finding(
                        str(source), "medium", "Internal duplicate image", f"{left_path.name} / {right_path.name}",
                        "Two images have highly similar local fingerprints or features; manual review needed to determine if duplicated, cropped, flipped, or reused.",
                        f"best_hash={best_name}:{best_distance}; transform={transform_text}; {orb_text}; hashes_left={{{_hash_summary(left_hashes)}}}; hashes_right={{{_hash_summary(right_hashes)}}}",
                        "Check figure legends, experimental conditions, and original images; similar images may come from the same sample, layout thumbnails, or genuine replicate experiments.",
                        tool_id="image_duplicate_internal", tool_name="Internal Duplicate Image Screening",
                        input_type="scientific_figure",
                        calculation_trace="Pillow/numpy local aHash/dHash/pHash; if cv2 is available, ORB local feature matching is additionally applied; no image upload.",
                    )
                )
    if not findings_dup:
        findings_dup.append(
            finding(
                str(source), "info", "Internal duplicate image", "figure",
                "Internal duplicate image screening complete; no highly similar image pairs found.",
                f"Hashable images={len(hashes)}",
                "This screening cannot exclude local duplication, complex rotation/cropping, or cross-manuscript reuse.",
                tool_id="image_duplicate_internal", tool_name="Internal Duplicate Image Screening", input_type="scientific_figure",
            )
        )

    for path in images:
        copy = _copy_move_matches(path)
        if copy is None:
            findings_copy.append(
                finding(
                    str(source), "info", "Copy-move dependency missing", "cv2",
                    "Missing OpenCV; cannot run ORB local copy-move screening.",
                    "dependency_missing=cv2",
                    "Install opencv-python-headless and retry; this notice does not count as an image risk.",
                    tool_id="image_copy_move_internal", tool_name="Image Copy-Move Screening",
                    input_type="scientific_figure", dependency_status="dependency_missing",
                )
            )
            break
        if int(copy.get("clustered_matches") or 0) >= 6:
            findings_copy.append(
                finding(
                    str(source), "medium", "Suspected local copy-move region", path.name,
                    "Multiple groups of similar local features found within a single image; manual review needed for copy-move, repeated textures, or chart elements.",
                    f"matches={copy.get('matches')}; clustered_matches={copy.get('clustered_matches')}; keypoints={copy.get('keypoints')}; samples={json.dumps(copy.get('samples'), ensure_ascii=False)}",
                    "Open original image to inspect areas near hit coordinates; request original uncropped images and processing notes from authors.",
                    tool_id="image_copy_move_internal", tool_name="Image Copy-Move Screening",
                    input_type="scientific_figure",
                    calculation_trace="OpenCV ORB features self-matched within the same image, filtered for nearby points, then clustered by displacement vector.",
                )
            )
    if not findings_copy:
        findings_copy.append(
            finding(
                str(source), "info", "Suspected local copy-move region", "figure",
                "Local copy-move screening complete; no cluster matches reaching threshold found.",
                f"Image count={len(images)}",
                "This result cannot exclude local duplication after manual retouching, in low-texture regions, or under heavy compression.",
                tool_id="image_copy_move_internal", tool_name="Image Copy-Move Screening",
                input_type="scientific_figure",
            )
        )

    findings_meta = _image_metadata_findings(source, images)

    blot_candidates = [path for path in images if re.search(r"blot|western|gel|wb|lane", path.name, re.I)]
    if blot_candidates:
        findings_blot.append(
            finding(
                str(source), "low", "Western blot/gel review checklist", "Image filename",
                "Found filenames suggestive of Western blot or gel images.",
                ", ".join(path.name for path in blot_candidates[:10]),
                "Request original uncropped blots, exposure parameters, splicing notes, loading controls, and replicate experiment records from authors.",
                tool_id="western_blot_review_list", tool_name="Western Blot Review Checklist", input_type="western_blot_or_gel_image",
            )
        )
    else:
        findings_blot.append(
            finding(
                str(source), "info", "Western blot/gel review checklist", "Image filename",
                "No blot/gel-specific review targets identified from filenames.",
                f"Image count={len(images)}",
                "If the manuscript contains blots/gels but filenames are not labeled, manually specify image types.",
                tool_id="western_blot_review_list", tool_name="Western Blot Review Checklist", input_type="western_blot_or_gel_image",
            )
        )
    return [
        TableResult("image_extract", len(images), 0, findings_extract),
        TableResult("image_duplicate_internal", len(images), 0, findings_dup),
        TableResult("image_copy_move_internal", len(images), 0, findings_copy),
        TableResult("image_metadata_audit", len(images), 0, findings_meta),
        TableResult("western_blot_review_list", len(blot_candidates), 0, findings_blot),
    ]
