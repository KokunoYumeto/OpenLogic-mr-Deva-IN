"""Render the exact current diagram crops for visual review; never assert review."""
import hashlib
import json
import math
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
RECEIPT = BUILD / "HTML_DIAGRAM_RECEIPT.json"
PDF = BUILD / "openlogic-mr-full.pdf"
OUT = BUILD / "diagram-visual-current"
OUT.mkdir(exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
assert receipt["source_pdf_sha256"] == sha(PDF)
pdf = fitz.open(PDF)
sheets = []
last_page_number = None
page_image = None
for start in range(0, len(receipt["assets"]), 12):
    sheet = Image.new("RGB", (1100, 1500), "#dddddd")
    draw = ImageDraw.Draw(sheet)
    subset = receipt["assets"][start:start + 12]
    for index, row in enumerate(subset):
        # Direct MuPDF clip rendering can inconsistently omit part of a shaped
        # Devanagari run. Render the complete page before cropping its pixels.
        if row["pdf_page"] != last_page_number:
            # Reusing a document's font cache across pages can drop shaped
            # Devanagari glyphs in raster output. Render each distinct page in
            # a fresh document, then crop its complete pixels.
            with fitz.open(PDF) as fresh_pdf:
                pix = fresh_pdf[row["pdf_page"] - 1].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            last_page_number = row["pdf_page"]
        x0, y0, x1, y1 = row["pdf_crop_points"]
        crop = page_image.crop((math.floor(x0 * 2), math.floor(y0 * 2),
                                math.ceil(x1 * 2), math.ceil(y1 * 2)))
        crop.thumbnail((520, 215))
        x, y = (index % 2) * 550 + 15, (index // 2) * 250 + 25
        sheet.paste(crop, (x + (520 - crop.width) // 2, y))
        draw.text((x, y - 18), f"{row['name']} / PDF {row['pdf_page']}", fill="black")
    path = OUT / f"crop-sheet-{start // 12 + 1}.png"
    sheet.save(path)
    sheets.append({"filename": path.name, "sha256": sha(path),
                   "diagram_names": [row["name"] for row in subset]})
pdf.close()
report = {"schema": "openlogic-mr-diagram-visual-qa/1",
          "result": "rendered-awaiting-inspection", "source_pdf_sha256": sha(PDF),
          "render_strategy": "complete_page_raster_then_pixel_crop",
          "diagram_receipt_sha256": sha(RECEIPT), "diagrams": 57, "sheets": sheets}
(BUILD / "HTML_DIAGRAM_VISUAL_QA.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"diagrams": 57, "sheets": len(sheets), "source_pdf_sha256": sha(PDF)}))
