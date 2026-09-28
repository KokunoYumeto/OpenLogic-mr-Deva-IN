"""Audit the complete Marathi HTML reader and state every release blocker."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
HTML_DIR = BUILD / "html"
HTML = HTML_DIR / "index.html"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


build = json.loads((BUILD / "HTML_PROVISIONAL_REPORT.json").read_text(encoding="utf-8"))
assert sha(HTML) == build["html_sha256"]
doc = BeautifulSoup(HTML.read_text(encoding="utf-8"), "html.parser")
ids = [node["id"] for node in doc.select("[id]")]
links = [link["href"][1:] for link in doc.select('a[href^="#"]')]
images = doc.select("img:not(.inline-math-symbol):not(.math-glyph)")
all_images = doc.select("img")
bad_images = [
    {
        "src": image.get("src"),
        "missing_file": not (HTML_DIR / image.get("src", "")).is_file(),
        "missing_description": not image.get("alt") or image.get("alt") == "image",
    }
    for image in all_images
    if not (HTML_DIR / image.get("src", "")).is_file()
    or not image.get("alt") or image.get("alt") == "image"
]
bad_math_glyphs = [
    glyph.get("src") for glyph in doc.select("img.math-glyph")
    if not glyph.get("alt") or not (HTML_DIR / glyph.get("src", "")).is_file()
]
text = doc.get_text(" ")
formulae = doc.select("math")
unannotated = [
    str(formula)[:160] for formula in formulae
    if not formula.find("annotation", attrs={"encoding": "application/x-tex"})
]
blockers = []
if build["source_units"] != 722:
    blockers.append("source-unit coverage")
if len(doc.select("h3")) != 612:
    blockers.append("section topology")
if len(doc.select("figure.proof")) != build["proof_representations"]:
    blockers.append("proof-table coverage")
if len(images) != build["diagram_count"]:
    blockers.append("diagram placement")
if build["missing_diagram_assets"] or bad_images:
    blockers.append("diagram assets or descriptions")
diagram_receipt_path = BUILD / "HTML_DIAGRAM_RECEIPT.json"
diagram_receipt = json.loads(diagram_receipt_path.read_text(encoding="utf-8"))
diagram_entries = diagram_receipt["assets"]
diagram_assets_valid = (
    build.get("diagram_receipt_sha256") == sha(diagram_receipt_path)
    and build.get("diagram_asset_count") == len(diagram_entries) == 57
    and all(
        (HTML_DIR / "assets" / entry["filename"]).is_file()
        and sha(HTML_DIR / "assets" / entry["filename"]) == entry["sha256"]
        and any(
            image.get("src") == "assets/" + entry["filename"]
            and image.get("alt") == entry["alt"]
            for image in images
        )
        for entry in diagram_entries
    )
)
if not diagram_assets_valid:
    blockers.append("diagram asset provenance")
if bad_math_glyphs:
    blockers.append("custom math glyph assets")
tex_receipt = json.loads((BUILD / "TEX_BUILD_RECEIPT.json").read_text(encoding="utf-8-sig"))
if tex_receipt["result"] != "built-log-clean" or not tex_receipt.get("pdf"):
    blockers.append("verified PDF source for exact math glyphs")
elif build["custom_math_glyphs"]["source_pdf_sha256"] != tex_receipt["pdf"]["sha256"]:
    blockers.append("custom math glyph source hash")
if (
    diagram_receipt["status"] != "final-source"
    or tex_receipt.get("pdf", {}).get("sha256") != diagram_receipt["source_pdf_sha256"]
):
    blockers.append("verified PDF source for diagrams")
if build["math_fallback_warnings"] or doc.select("span.math"):
    blockers.append("math conversion")
if build["unresolved_math_text_refs"]:
    blockers.append("formula prose references")
aux_path = BUILD / "openlogic-mr-full.aux"
if not aux_path.is_file() or build["html_aux_sha256"] != sha(aux_path):
    blockers.append("HTML auxiliary source")
if unannotated:
    blockers.append("MathML TeX annotations")
if len(ids) != len(set(ids)) or any(key not in ids for key in links):
    blockers.append("local anchors")
if "OPENLOGICPROOFPLACEHOLDER" in text or "OPENLOGICEXTRAPROOFPLACEHOLDER" in text:
    blockers.append("proof placeholders")
if any(char in text for char in ("\ue001", "\ue002", "\ue003")):
    blockers.append("unresolved custom symbol placeholders")
if doc.html.get("lang") != "mr":
    blockers.append("document language")
if any(str(node).strip() == "<em>Proof.</em>" for node in doc.find_all("em")):
    blockers.append("proof-heading localization")

report = {
    "schema": "openlogic-full-html-qa/1",
    "result": "ready" if not blockers else "blocked",
    "blockers": blockers,
    "html_sha256": sha(HTML),
    "parts": len(doc.select("h1")),
    "chapters": len(doc.select("h2")),
    "sections": len(doc.select("h3")),
    "proof_tables": len(doc.select("figure.proof")),
    "mathml_nodes": len(formulae),
    "mathml_without_tex_annotation": len(unannotated),
    "diagrams": len(images),
    "diagram_assets_verified": diagram_assets_valid,
    "bad_images": bad_images,
    "custom_math_glyphs": len(doc.select("img.math-glyph")),
    "bad_math_glyphs": bad_math_glyphs,
    "math_fallback_warnings": build["math_fallback_warnings"],
    "duplicate_ids": [key for key, count in Counter(ids).items() if count > 1],
    "broken_local_links": [key for key in links if key not in ids],
    "devanagari_chars": sum("\u0900" <= char <= "\u097f" for char in text),
}
(BUILD / "HTML_QA.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "result": report["result"],
    "blockers": blockers,
    "sections": report["sections"],
    "proof_tables": report["proof_tables"],
    "mathml_nodes": report["mathml_nodes"],
    "diagrams": report["diagrams"],
    "bad_images": len(bad_images),
    "broken_local_links": len(report["broken_local_links"]),
}, ensure_ascii=False))
