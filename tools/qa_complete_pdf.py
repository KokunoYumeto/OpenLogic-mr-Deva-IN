"""Inspect every page of the complete reader PDF and render review samples."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
PDF = BUILD / "openlogic-mr-full.pdf"
IMAGES = BUILD / "pdf-visual-samples"
IMAGES.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt = json.loads((BUILD / "TEX_BUILD_RECEIPT.json").read_text(encoding="utf-8-sig"))
inputs = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
document = fitz.open(PDF)
assert not document.is_encrypted and len(document) >= 900
pages = []
fonts = Counter()
broken_destinations = []
for index, page in enumerate(document):
    text = page.get_text()
    blocks = [block for block in page.get_text("blocks") if len(block) >= 7 and block[6] == 0]
    outside = [tuple(round(value, 1) for value in block[:4]) for block in blocks
               if block[0] < -2 or block[1] < -2 or block[2] > page.rect.width + 2
               or block[3] > page.rect.height + 2]
    for font in page.get_fonts(full=True):
        fonts[font[3]] += 1
    for link in page.get_links():
        if link.get("kind") == fitz.LINK_GOTO and not (0 <= link.get("page", -1) < len(document)):
            broken_destinations.append({"from_page": index + 1, "target": link.get("page")})
    pages.append({
        "page": index + 1,
        "text_characters": len(text),
        "text_blocks": len(blocks),
        "outside_page_text_blocks": outside,
    })

sample_numbers = sorted({1, 24, 151, 255, 415, 501, 536, 630, 765, 841, len(document)})
samples = []
for number in sample_numbers:
    path = IMAGES / f"page-{number:03d}.png"
    document[number - 1].get_pixmap(matrix=fitz.Matrix(1.1, 1.1), alpha=False).save(path)
    samples.append({"page": number, "path": str(path), "sha256": sha(path)})

pdf_hash = sha(PDF)
source_matches_receipt = (
    receipt.get("texInputSha256") == inputs["reader_sha256"]
    and receipt.get("pdf", {}).get("sha256") == pdf_hash
)
stale_targets = [row["unit_id"] for row in inputs.get("input_units", [])
                 if sha(ROOT / row["target_path"]) != row["target_sha256"]]
problems = []
if len(inputs.get("input_units", [])) != 722:
    problems.append("reader lacks per-unit source/target build bindings")
if stale_targets:
    problems.append("source translations changed after reader assembly: " + ", ".join(stale_targets))
if not source_matches_receipt:
    problems.append("PDF does not match the current reader source and build receipt")
if receipt["result"] != "built-log-clean":
    problems.append("TeX log is not verified clean")
if broken_destinations:
    problems.append("broken internal PDF destinations")
if any(row["outside_page_text_blocks"] for row in pages):
    problems.append("text blocks outside the physical page")
if any(row["text_characters"] < 10 for row in pages):
    problems.append("nearly blank pages require visual review")

report = {
    "schema": "openlogic-mr-complete-pdf-qa/1",
    "status": "ready" if not problems else "provisional",
    "problems": problems,
    "pdf_sha256": pdf_hash,
    "reader_sha256": inputs["reader_sha256"],
    "pages": len(document),
    "metadata": {key: document.metadata.get(key) for key in ("title", "author", "creator", "producer")},
    "min_page_text_characters": min(row["text_characters"] for row in pages),
    "nearly_blank_pages": [row["page"] for row in pages if row["text_characters"] < 10],
    "outside_page_text": [row for row in pages if row["outside_page_text_blocks"]],
    "broken_destinations": broken_destinations,
    "embedded_fonts": sorted(fonts),
    "visual_samples": samples,
}
(BUILD / "PDF_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: report[key] for key in (
    "status", "problems", "pages", "min_page_text_characters",
    "nearly_blank_pages", "outside_page_text", "broken_destinations",
)}, ensure_ascii=False))
