"""Extract the reader's two custom mathematical symbols as exact SVG outlines."""

import hashlib
from io import BytesIO
from pathlib import Path

import fitz
from fontTools.cffLib import CFFFontSet
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen


SYMBOLS = {
    "strict": ("txsyc", "strict-conditional.svg", "कठोर अभिव्यंजनाचे चिन्ह"),
    "squareright": ("txsyc", "counterfactual-conditional.svg", "प्रतिवास्तविक अभिव्यंजनाचे चिन्ह"),
    "leftrightarroweq": ("stmary10", "bisimulation-equivalence.svg", "द्विअनुकरणसदृशतेचे चिन्ह"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_symbols(pdf_path, output_dir):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    font_xrefs = {}
    for page in document:
        for xref, extension, kind, basefont, *_ in page.get_fonts(full=True):
            font_xrefs[xref] = (extension, kind, basefont)
    parsed_fonts = {}
    font_receipts = []
    for suffix in sorted({row[0] for row in SYMBOLS.values()}):
        needed = {name for name, row in SYMBOLS.items() if row[0] == suffix}
        for xref, (_, _, basefont) in font_xrefs.items():
            if not basefont.lower().endswith("+" + suffix):
                continue
            _, extension, _, data = document.extract_font(xref)
            if extension != "cff":
                continue
            cff = CFFFontSet()
            cff.decompile(BytesIO(data), None)
            top = cff[cff.fontNames[0]]
            if needed.issubset(top.CharStrings.keys()):
                parsed_fonts[suffix] = top
                font_receipts.append({
                    "suffix": suffix, "xref": xref,
                    "sha256": hashlib.sha256(data).hexdigest(),
                })
                break
        assert suffix in parsed_fonts, f"The PDF lacks the {suffix} symbols"
    glyphs = []
    for name, (suffix, filename, alt) in SYMBOLS.items():
        font = parsed_fonts[suffix]
        charstring = font.CharStrings[name]
        path_pen = SVGPathPen(font.CharStrings)
        bounds_pen = BoundsPen(font.CharStrings)
        charstring.draw(path_pen)
        charstring.draw(bounds_pen)
        x0, y0, x1, y1 = bounds_pen.bounds
        margin = 8
        width = x1 - x0 + 2 * margin
        height = y1 - y0 + 2 * margin
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{x0 - margin} {-y1 - margin} {width} {height}" '
            f'width="{width}" height="{height}" role="img">'
            f"<title>{alt}</title>"
            '<g transform="scale(1,-1)">'
            f'<path d="{path_pen.getCommands()}" fill="#202124"/>'
            "</g></svg>\n"
        )
        destination = output_dir / filename
        destination.write_text(svg, encoding="utf-8", newline="\n")
        glyphs.append({
            "name": name, "font": suffix, "filename": filename, "alt": alt,
            "bounds_font_units": [x0, y0, x1, y1],
            "sha256": sha(destination), "bytes": destination.stat().st_size,
        })
    return {
        "source_pdf_sha256": sha(pdf_path),
        "embedded_fonts": font_receipts,
        "glyphs": glyphs,
    }
