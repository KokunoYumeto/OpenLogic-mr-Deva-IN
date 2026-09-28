"""Render the exact current diagram crops for visual review; never assert review."""
import hashlib
import json
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
for start in range(0, len(receipt["assets"]), 12):
    sheet = Image.new("RGB", (1100, 1500), "#dddddd")
    draw = ImageDraw.Draw(sheet)
    subset = receipt["assets"][start:start + 12]
    for index, row in enumerate(subset):
        pix = pdf[row["pdf_page"] - 1].get_pixmap(
            matrix=fitz.Matrix(2, 2), clip=fitz.Rect(row["pdf_crop_points"]), alpha=False
        )
        crop = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
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
          "diagram_receipt_sha256": sha(RECEIPT), "diagrams": 57, "sheets": sheets}
(BUILD / "HTML_DIAGRAM_VISUAL_QA.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"diagrams": 57, "sheets": len(sheets), "source_pdf_sha256": sha(PDF)}))
