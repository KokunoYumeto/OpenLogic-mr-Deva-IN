"""Audit the complete Marathi HTML reader and state every release blocker."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from complete_reader_topology import heading_inventory


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
HTML_DIR = BUILD / "html"
HTML = HTML_DIR / "index.html"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


build = json.loads((BUILD / "HTML_PROVISIONAL_REPORT.json").read_text(encoding="utf-8"))
assert sha(HTML) == build["html_sha256"]
reader = BUILD / "openlogic-mr-full.tex"
assert sha(reader) == build["source_tex_sha256"]
headings = heading_inventory(reader.read_text(encoding="utf-8"))
expected_headings = {tag: sum(row["command"] == command for row in headings)
                     for tag, command in (("h1", "part"), ("h2", "chapter"), ("h3", "section"))}
generated_heading_counts = {"h1": 1, "h2": 1, "h3": 0}
expected_headings = {tag: count + generated_heading_counts[tag]
                     for tag, count in expected_headings.items()}
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
if any(len(doc.select(tag)) != expected for tag, expected in expected_headings.items()):
    blockers.append("source heading topology")
if (len(doc.select("header#title-block-header h1.title")) != 1
        or len(doc.select("nav#TOC h2#toc-title")) != 1):
    blockers.append("generated title or contents heading")
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
success_path = BUILD / "TEX_SUCCESS_RECEIPT.json"
tex_receipt = json.loads(success_path.read_text(encoding="utf-8-sig")) if success_path.is_file() else {}
pdf_path = BUILD / "openlogic-mr-full.pdf"
if tex_receipt.get("result") != "built-log-clean" or not tex_receipt.get("pdf"):
    blockers.append("verified PDF source for exact math glyphs")
elif (not pdf_path.is_file()
      or tex_receipt["pdf"]["sha256"] != sha(pdf_path)
      or tex_receipt.get("texInputSha256") != sha(reader)):
    blockers.append("verified PDF and reader source hashes")
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
    "source_tex_sha256": sha(reader),
    "source_heading_inventory": headings,
    "source_heading_counts": expected_headings,
    "generated_heading_counts": generated_heading_counts,
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
