"""Build offline semantic HTML/MathML for the current complete-chapter core reader."""

import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import fitz
from bs4 import BeautifulSoup
from core_html_proofs import (
    adapt_prose_ensuremath,
    expand_reader_math_macros,
    strip_proof_environments,
)


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
O = B / "html"
A = O / "assets"
A.mkdir(parents=True, exist_ok=True)
MATH_TEXT_FALLBACKS = P / "math-text-fallbacks"
PDF = B / "openlogic-mr-core.pdf"
TEX = B / "openlogic-mr-core.tex"
INPUTS = B / "INPUTS.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expand_logic_math_macros(text):
    """Expand the xparse/applytofirst shorthands Pandoc cannot parse."""
    return expand_reader_math_macros(text)


input_rows = json.loads(INPUTS.read_text(encoding="utf-8"))["input_units"]
section_driver_unit_ids = {
    "OLP-0004", "OLP-0011", "OLP-0020", "OLP-0027", "OLP-0041",
    "OLP-0049", "OLP-0055", "OLP-0056", "OLP-0063", "OLP-0069",
    "OLP-0084", "OLP-0098",
    "OLP-0112", "OLP-0126", "OLP-0138", "OLP-0139", "OLP-0149",
    "OLP-0159", "OLP-0167", "OLP-0174", "OLP-0182", "OLP-0183",
    "OLP-0191",
}
chapter_driver_unit_ids = section_driver_unit_ids - {"OLP-0055", "OLP-0138", "OLP-0182"}
scope = {
    "translation_source_units": len(input_rows),
    "reader_sections": len(input_rows) - sum(row["unit_id"] in section_driver_unit_ids for row in input_rows),
    "complete_chapters": sum(row["unit_id"] in chapter_driver_unit_ids for row in input_rows),
}
assert scope == {
    "translation_source_units": 194,
    "reader_sections": 171,
    "complete_chapters": 20,
}


receipt = json.loads((B / "TEX_SUCCESS_RECEIPT.json").read_text(encoding="utf-8-sig"))
assert receipt["result"] == "built-log-clean"
assert sha(PDF) == receipt["pdf"]["sha256"]
assert sha(TEX) == receipt["texInputSha256"]

document = fitz.open(PDF)
assert len(document) == 264
specs = [
    # Physical PDF page numbers after the expanded twenty-chapter table of contents.
    ("union", 14, (176, 131, 417, 328), "A आणि B या दोन संचांचा संयोग. दोन्ही बंद वक्रांचा संपूर्ण भाग चिन्हांकित आहे; म्हणजे A किंवा B यांपैकी किमान एका संचातील सर्व घटक."),
    ("intersection", 14, (176, 485, 417, 682), "A आणि B या दोन संचांचा छेद. दोन बंद वक्रांचा फक्त सामाईक आच्छादित भाग चिन्हांकित आहे."),
    ("difference", 16, (176, 68, 417, 264), "A वजा B हा संचफरक. A च्या वक्रातील B च्या बाहेर राहणारा भाग चिन्हांकित आहे; सामाईक भाग वगळलेला आहे."),
    ("graph-four", 25, (227, 207, 368, 305), "दिशित आलेखाची चार शिखरे 1, 2, 3 आणि 4. कडा 1 ते 1, 1 ते 2, 1 ते 3 आणि 2 ते 3; शिखर 4 एकाकी आहे."),
    ("graph-three", 25, (227, 340, 312, 439), "दिशित आलेखाची शिखरे 1, 2 आणि 3. कडा 1 ते 1, 1 ते 2, 1 ते 3 आणि 2 ते 3; आधीच्या आलेखातील एकाकी शिखर 4 येथे नाही."),
    ("tree", 25, (241, 662, 354, 776), "सांत वृक्ष. सर्वांत खाली मूळ r; त्याची अपत्ये a आणि b; a ची अपत्ये c, d आणि e. पूर्वज संबंध कडांवरून वरच्या दिशेने वाचला जातो."),
    ("function", 29, (176, 67, 417, 201), "फलनाची आकृती. डावीकडील प्रांतातील प्रत्येक फलसाधकापासून उजवीकडील सहप्रांतातील नेमक्या एका मूल्याकडे बाण जातो."),
    ("surjective", 30, (176, 613, 418, 746), "आच्छादक फलन. सहप्रांतातील प्रत्येक लाल घटकाकडे प्रांतातील किमान एका करड्या घटकापासून बाण येतो."),
    ("injective", 31, (176, 67, 417, 221), "एकास-एक फलन. वेगवेगळ्या करड्या फलसाधकांचे बाण वेगवेगळ्या लाल मूल्यांकडे जातात; सहप्रांतातील काही घटक मूल्य नसू शकतात."),
    ("bijective", 31, (176, 613, 418, 746), "एकास-एक व आच्छादक फलन. प्रांतातील प्रत्येक करडा घटक आणि सहप्रांतातील प्रत्येक लाल घटक यांची नेमकी एक जोडी बाणाने जोडलेली आहे."),
    ("composition", 35, (135, 602, 457, 747), "फलन-संयोजन g वर्तुळ f. डावीकडील A मधून f चे बाण मधल्या B मध्ये, B मधून g चे बाण उजवीकडील C मध्ये, आणि तुटक बाह्य बाण A मधून थेट C मधील त्याच अंतिम मूल्यांकडे जातात."),
    ("root-two-square", 60, (214, 388, 367, 483), "वर्गमूळ दोनच्या अपरिमेयतेची भूमितीय आकृती. m बाजूच्या मोठ्या चौरसात n बाजूचे दोन आच्छादित चौरस आहेत; नारिंगी सामाईक चौरस आणि दोन न रंगवलेले कोपरे लहान समान रचना दाखवतात."),
    ("hilberts-hotel", 71, (180, 575, 415, 650), "हिल्बर्टच्या हॉटेलमधील खोली बदल. वरच्या ओळीत जुने पाहुणे 1, 2, 3 आणि पुढे आहेत; प्रत्येक बाण पाहुणा n याला खालच्या ओळीतील खोली n अधिक 1 मध्ये हलवतो, त्यामुळे वर्तुळ केलेली खोली 1 नव्या पाहुण्यासाठी मोकळी होते."),
]

assets = []
for name, page, rect, alt in specs:
    x0, y0, x1, y1 = rect
    page_object = document[page - 1]
    crop = fitz.Rect(rect)
    crop_text_chars = len("".join(page_object.get_text("text", clip=crop).split()))
    vector_drawing_count = sum(
        fitz.Rect(item["rect"]).intersects(crop)
        for item in page_object.get_drawings()
    )
    # A shifted page can still produce a valid SVG containing nearby prose.
    # Require the crop to be drawing-dense and prose-light before accepting it.
    assert vector_drawing_count >= 5, (name, page, vector_drawing_count)
    assert crop_text_chars <= 64, (name, page, crop_text_chars)
    svg = page_object.get_svg_image(text_as_path=True)
    svg = re.sub(
        r"<svg\b[^>]*>",
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{(x1 - x0) * 2}" height="{(y1 - y0) * 2}" '
            f'viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" role="img" '
            f'aria-labelledby="desc-{name}" style="overflow:hidden">'
            f'<title id="desc-{name}">{html.escape(alt)}</title>'
        ),
        svg,
        count=1,
    )
    destination = A / f"{name}.svg"
    destination.write_text(svg, encoding="utf-8", newline="\n")
    assets.append(
        {
            "filename": f"assets/{destination.name}",
            "sha256": sha(destination),
            "bytes": destination.stat().st_size,
            "source_pdf_page": page,
            "source_pdf_crop": rect,
            "source_pdf_crop_text_chars": crop_text_chars,
            "source_pdf_vector_drawing_count": vector_drawing_count,
            "alt": alt,
        }
    )

tex = TEX.read_text(encoding="utf-8")
# The PDF-only layout helper uses a wider marked-formula label box.  For
# semantic MathML, its notation is identical to the canonical \sFmla macro.
tex = tex.replace(
    r"\NewDocumentCommand{\sFmlaWide}{m m o}{\ensuremath{\IfNoValueTF{#3}{}{#3\,}\hbox to 1.2em{\ensuremath{#1}\hfil} #2}}",
    "",
)
tex = tex.replace(r"\sFmlaWide", r"\sFmla")
tex, proof_specs = strip_proof_environments(tex)
tex = adapt_prose_ensuremath(tex)
for name in [
    "union",
    "intersection",
    "difference",
    "function",
    "surjective",
    "injective",
    "bijective",
    "composition",
]:
    pattern = r"\\olasset(?:\[[^]]+\])?\{assets/diagrams/" + name + r"\.tikz\}"
    tex, count = re.subn(pattern, r"\\includegraphics{assets/" + name + ".svg}", tex)
    assert count == 1, (name, count)

graph_pattern = r"\\begin\{align\*\}\s*&\s*\\begin\{tikzpicture\}.*?\\end\{align\*\}"
match = re.search(graph_pattern, tex, re.S)
assert match
graph = match.group()
intertext = re.search(r"\\intertext\{(.*?)\}\s*&", graph, re.S)
assert intertext
replacement = (
    r"\begin{center}\includegraphics{assets/graph-four.svg}\end{center}"
    + "\n\n"
    + intertext.group(1)
    + "\n\n"
    + r"\begin{center}\includegraphics{assets/graph-three.svg}\end{center}"
)
tex = tex[: match.start()] + replacement + tex[match.end() :]

tree_pattern = r"\\begin\{tikzpicture\}\[nodes=\{draw, circle\}, -\].*?\\end\{tikzpicture\}"
tex, count = re.subn(tree_pattern, r"\\includegraphics{assets/tree.svg}", tex, flags=re.S)
assert count == 1
square_pattern = r"\\begin\{tikzpicture\}\s*\\draw\[thick\] \(0,0\) rectangle \(3,3\);.*?\\end\{tikzpicture\}"
tex, count = re.subn(square_pattern, r"\\includegraphics{assets/root-two-square.svg}", tex, flags=re.S)
assert count == 1
hotel_pattern = r"\\begin\{tikzpicture\}\[scale\s*=\s*\.75\].*?\\end\{tikzpicture\}"
tex, count = re.subn(hotel_pattern, r"\\includegraphics{assets/hilberts-hotel.svg}", tex, flags=re.S)
assert count == 1
assert r"\begin{tikzpicture}" not in tex
assert not re.search(r"\\olasset(?:\[[^]]+\])?\{assets/", tex)

# Pandoc's MathML writer does not understand the TeX implementation of the
# partial-function arrow. The standard right-harpoon glyph has the same
# mathematical role and converts to native MathML.
tex, count = re.subn(r"(?m)^\\newcommand\{\\pto\}.*$", "", tex)
assert count == 1
tex = tex.replace(r"\pto", r"\rightharpoonup")

# TeX permits ordinary prose between aligned rows via \intertext; Pandoc does
# not. Split every remaining prose-bearing display so its prose and inline
# mathematics remain semantic HTML in their original order.
marker = r"\intertext{"
intertext_count = 0
expected_intertext_count = tex.count(marker)
while marker in tex:
    start = tex.index(marker)
    index = start + len(marker)
    depth = 1
    while depth:
        if tex[index] == "{" and tex[index - 1] != "\\":
            depth += 1
        elif tex[index] == "}" and tex[index - 1] != "\\":
            depth -= 1
        index += 1
    intertext = tex[start + len(marker) : index - 1]
    align_start = tex.rfind(r"\begin{align*}", 0, start)
    align_end = tex.index(r"\end{align*}", index) + len(r"\end{align*}")
    assert align_start >= 0
    before = tex[align_start + len(r"\begin{align*}") : start]
    after = tex[index : align_end - len(r"\end{align*}")]
    split_align = (
        r"\begin{align*}"
        + before.rstrip()
        + "\n"
        + r"\end{align*}"
        + "\n\n"
        + intertext
        + "\n\n"
        + r"\begin{align*}"
        + after.lstrip()
        + r"\end{align*}"
    )
    tex = tex[:align_start] + split_align + tex[align_end:]
    intertext_count += 1
assert intertext_count == expected_intertext_count

# These five row labels are text inside displayed mathematics. \text converts
# to MathML cleanly while retaining the same Marathi wording.
for label in ["सहचारिता", "क्रमनिरपेक्षता", "अविकारक", "बेरीज व्यस्त", "वितरणता", "गुणाकार व्यस्त"]:
    old = r"\emph{" + label + "}&&"
    if label == "गुणाकार व्यस्त":
        old = r"\emph{" + label + "}& &"
    new = r"\text{" + label + "}" + ("& &" if label == "गुणाकार व्यस्त" else "&&")
    tex, count = tex.replace(old, new), tex.count(old)
    assert count == 1, (label, count)

tex = tex.replace(r"\nicefrac", r"\frac")
while re.search(r"\\shove(?:left|right)\{", tex):
    match = re.search(r"\\shove(?:left|right)\{", tex)
    start = match.end()
    index = start
    depth = 1
    while depth:
        if tex[index] == "{" and tex[index - 1] != "\\":
            depth += 1
        elif tex[index] == "}" and tex[index - 1] != "\\":
            depth -= 1
        index += 1
    tex = tex[: match.start()] + tex[start : index - 1] + tex[index:]

# Only the document body needs expansion. Retaining the original preamble keeps
# the PDF source traceable while preventing substitutions inside definitions.
preamble, document_marker, body = tex.partition(r"\begin{document}")
assert document_marker
body = expand_logic_math_macros(body)
tex = preamble + document_marker + body
assertion_body = re.sub(
    r"\\verb\*?(?P<delimiter>[^A-Za-z0-9\s]).*?(?P=delimiter)",
    "",
    body,
    flags=re.S,
)
unexpanded_reader_macro = re.search(
    r"\\(?:Struct|Lang|Frm|Trm|Sent|Entails|pAssign|pValue|pSat|Sat|Assign|"
    r"varAssign|Value|Log|Atom|Subst|lexists|lforall|eq|elemequiv|iso|lambd|"
    r"mSat|OPrf|OCon|Domain|Theory|Expan|mModel|Th|QuantRank|num|PIso|Part|gn|"
    r"substruct|nszero|nssucc|nsplus|nstimes|nsless|concat|VDash|readerexternalref)"
    r"/?(?:\b|\[|\{)",
    assertion_body,
)
assert not unexpanded_reader_macro, assertion_body[
    max(0, unexpanded_reader_macro.start() - 120) : unexpanded_reader_macro.end() + 240
]

html_input = B / "html-input.tex"
html_input.write_text(tex, encoding="utf-8", newline="\n")
font_dir = O / "fonts"
font_dir.mkdir(exist_ok=True)
for name in ["OLMarathiSerif-Regular.ttf", "OLMarathiSerif-Bold.ttf", "OFL.txt"]:
    shutil.copyfile(P / "fonts" / name, font_dir / name)
# Keep the distributable license text byte-stable across platforms while
# preserving its wording exactly.
license_path = font_dir / "OFL.txt"
license_text = "\n".join(
    line.rstrip() for line in license_path.read_text(encoding="utf-8").splitlines()
) + "\n"
license_path.write_text(license_text, encoding="utf-8", newline="\n")

css = """@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Regular.ttf)}@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Bold.ttf);font-weight:bold}*{box-sizing:border-box}html{scroll-behavior:smooth;overflow-x:hidden}body{font-family:OLMarathi,serif;line-height:1.75;margin:0 auto;padding:2rem 1.25rem 5rem;max-width:58rem;color:#202124;background:#fff;overflow-wrap:break-word}h1,h2,h3{line-height:1.4;scroll-margin-top:1rem}h1{margin-top:3rem;border-bottom:2px solid #a81c21;padding-bottom:.6rem}a{color:#064c8c}a:focus-visible{outline:3px solid #a81c21;outline-offset:3px}a.uri{overflow-wrap:anywhere;word-break:break-word}img{max-width:100%;height:auto;display:block;margin:1rem auto}figure{margin:2rem 0}figcaption{font-size:.94rem;text-align:center}.math.display{display:block;overflow-x:auto;padding:.7rem 0}math{font-size:1.05em;max-width:100%}math mtext{font-family:OLMarathi,serif;font-style:normal}p math[display="inline"]{overflow-x:auto;overflow-y:hidden;vertical-align:middle}.proof{border-left:3px solid #ddd;padding-left:1rem;max-width:100%;overflow-x:auto}.proof-steps{border-collapse:collapse;margin:.75rem auto;min-width:30rem}.proof-steps th,.proof-steps td{border-bottom:1px solid #ddd;padding:.35rem .8rem;text-align:left;vertical-align:top;white-space:nowrap}.defn,.ex,.prop,.thm,.lem,.cor,.prob,.rem{margin:1.2rem 0}.titlepage{border-bottom:1px solid #bbb;padding-bottom:1.5rem}#TOC{background:#f3f5f7;padding:1rem 1.5rem;border-radius:.3rem}code{overflow-wrap:anywhere}p{orphans:3;widows:3}.math-display{max-width:100%;overflow-x:auto;margin:1rem 0;padding:.5rem 0}.math-display math{margin:0 auto}figure img{width:auto}@media(max-width:600px){body{font-size:1.06rem;padding:.9rem}h1{font-size:1.7rem}h2{font-size:1.35rem}#TOC{padding:.8rem 1rem}}@media print{body{max-width:none}#TOC{page-break-after:always}a{color:inherit}}"""
(O / "reader.css").write_text(css + "\n", encoding="utf-8", newline="\n")

pandoc = shutil.which("pandoc")
assert pandoc
args = [
    pandoc,
    str(html_input),
    "--from=latex",
    "--to=html5",
    "--standalone",
    "--mathml",
    "--toc",
    "--number-sections",
    "--metadata=lang:mr",
    "--metadata=title:मुक्त तर्कशास्त्र — वीस प्रकरणांची मराठी आवृत्ती",
    "--metadata=toc-title:अनुक्रमणिका",
    "--css=reader.css",
    "--output=" + str(O / "index.html"),
]
result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=180)
(B / "HTML_BUILD_LOG.txt").write_text(result.stderr, encoding="utf-8")
assert result.returncode == 0, result.stderr
assert not result.stderr, result.stderr

doc = (O / "index.html").read_text(encoding="utf-8")
for asset in assets:
    pattern = r'(<img\b[^>]*src="' + re.escape(asset["filename"]) + r'"[^>]*)(/?>)'
    image_id = "diagram-" + Path(asset["filename"]).stem
    x0, y0, x1, y1 = asset["source_pdf_crop"]
    intrinsic_width = int((x1 - x0) * 2)
    intrinsic_height = int((y1 - y0) * 2)

    def label(
        match,
        alt=asset["alt"],
        image_id=image_id,
        intrinsic_width=intrinsic_width,
        intrinsic_height=intrinsic_height,
    ):
        tag = re.sub(r'\s+alt="[^"]*"', "", match.group(1))
        return (
            tag
            + ' id="' + image_id + '"'
            + f' width="{intrinsic_width}" height="{intrinsic_height}"'
            + ' alt="' + html.escape(alt, quote=True) + '" loading="lazy"'
            + match.group(2)
        )

    doc, count = re.subn(pattern, label, doc)
    assert count == 1, (asset["filename"], count)
doc = doc.replace(
    "<body>",
    '<body>\n<a class="skip-link" href="#main-content">मुख्य मजकुराकडे जा</a>\n<main id="main-content">',
    1,
).replace("</body>", "</main>\n</body>")

soup = BeautifulSoup(doc, "html.parser")

proof_formulae = list(
    dict.fromkeys(row["formula_tex"] for spec in proof_specs for row in spec["rows"])
)
assert proof_formulae and all("$" not in formula for formula in proof_formulae)
proof_conversion = subprocess.run(
    [pandoc, "--from=markdown", "--to=html5", "--mathml"],
    input="\n\n".join("$" + formula + "$" for formula in proof_formulae),
    capture_output=True,
    text=True,
    encoding="utf-8",
    timeout=120,
)
assert proof_conversion.returncode == 0 and proof_conversion.stderr == "", proof_conversion.stderr
proof_nodes = BeautifulSoup(proof_conversion.stdout, "html.parser").find_all("math")
assert len(proof_nodes) == len(proof_formulae)
assert all(
    node.find("annotation", attrs={"encoding": "application/x-tex"})
    for node in proof_nodes
)
proof_math_html = dict(zip(proof_formulae, map(str, proof_nodes)))


def math_node(latex):
    return BeautifulSoup(proof_math_html[latex], "html.parser").find("math")


for spec in proof_specs:
    figure = soup.new_tag(
        "figure",
        attrs={
            "class": "proof",
            "id": spec["id"],
            "data-proof-id": spec["id"],
            "aria-labelledby": spec["id"] + "-caption",
        },
    )
    caption = soup.new_tag("figcaption", id=spec["id"] + "-caption")
    caption.string = spec["caption"]
    figure.append(caption)
    table = soup.new_tag("table")
    table["class"] = ["proof-steps"]
    thead = soup.new_tag("thead")
    header_row = soup.new_tag("tr")
    for label in ("पायरी", "सूत्र", "नियम किंवा कारण"):
        cell = soup.new_tag("th", scope="col")
        cell.string = label
        header_row.append(cell)
    thead.append(header_row)
    table.append(thead)
    tbody = soup.new_tag("tbody")
    group_totals = {}
    for row in spec["rows"]:
        group = row.get("group", 1)
        group_totals[group] = group_totals.get(group, 0) + 1
    group_seen = {}
    for number, row in enumerate(spec["rows"], 1):
        tr = soup.new_tag("tr")
        number_cell = soup.new_tag("td")
        group = row.get("group", 1)
        group_seen[group] = group_seen.get(group, 0) + 1
        number_cell.string = (
            f"{group}.{group_seen[group]}" if len(group_totals) > 1 else str(number)
        )
        formula_cell = soup.new_tag("td")
        formula_cell.append(math_node(row["formula_tex"]))
        rule_cell = soup.new_tag("td")
        rule_cell.string = row["rule"]
        tr.extend([number_cell, formula_cell, rule_cell])
        tbody.append(tr)
    table.append(tbody)
    figure.append(table)
    placeholder = next(
        (
            node
            for node in soup.find_all("p")
            if spec["placeholder"] in node.get_text(" ", strip=True)
        ),
        None,
    )
    assert placeholder is not None, spec["id"]
    if placeholder.get_text(" ", strip=True) == spec["placeholder"]:
        placeholder.replace_with(figure)
    else:
        # Pandoc can append a proof environment's QED square to the placeholder
        # paragraph. Put the semantic figure before that paragraph and retain
        # the marker as ordinary proof-ending text.
        placeholder.insert_before(figure)
        text_node = next(
            node for node in placeholder.find_all(string=True)
            if spec["placeholder"] in node
        )
        text_node.replace_with(text_node.replace(spec["placeholder"], "", 1).lstrip())

assert len(soup.select("figure.proof")) == len(proof_specs)

# Calibre and some other EPUB renderers lay out Indic text in MathML mtext one
# Unicode code point at a time.  Keep the native MathML and exact TeX
# annotation, but use a standards-valid mglyph whose outlined SVG preserves
# Devanagari shaping.  The glyph alt text retains the same Marathi wording.
fallback_manifest_path = MATH_TEXT_FALLBACKS / "MANIFEST.json"
fallback_manifest = json.loads(fallback_manifest_path.read_text(encoding="utf-8"))
assert fallback_manifest["schema"] == "openlogic-marathi-math-text-fallbacks/1"
fallback_font = P / fallback_manifest["font"]["path"]
assert fallback_font.is_file()
assert fallback_manifest["font"]["bytes"] == fallback_font.stat().st_size
assert fallback_manifest["font"]["sha256"] == sha(fallback_font)
fallback_entries = {entry["text"]: entry for entry in fallback_manifest["entries"]}
assert len(fallback_entries) == len(fallback_manifest["entries"])
fallback_output = A / "math-text"
if fallback_output.exists():
    shutil.rmtree(fallback_output)
fallback_output.mkdir()
copied_fallbacks = []
for entry in fallback_manifest["entries"]:
    source = MATH_TEXT_FALLBACKS / entry["filename"]
    assert source.is_file()
    assert entry["bytes"] == source.stat().st_size
    assert entry["sha256"] == sha(source)
    destination = fallback_output / entry["filename"]
    shutil.copyfile(source, destination)
    copied_fallbacks.append(
        {
            "filename": f"assets/math-text/{entry['filename']}",
            "bytes": destination.stat().st_size,
            "sha256": sha(destination),
            "text": entry["text"],
            "display_width": entry["display_width"],
            "display_height": entry["display_height"],
            "valign": entry["valign"],
        }
    )


def normalize_math_text(value):
    return " ".join(value.replace("\u00a0", " ").replace("\u2000", " ").split())


math_text_fallback_rows = []
used_fallbacks = set()
for text_node in soup.select("mtext"):
    source_text = text_node.get_text()
    if not re.search(r"[\u0900-\u097f]", source_text):
        continue
    assert not text_node.find(True), str(text_node)[:240]
    normalized = normalize_math_text(source_text)
    assert normalized in fallback_entries, normalized
    entry = fallback_entries[normalized]
    glyph = soup.new_tag(
        "mglyph",
        attrs={
            "src": f"assets/math-text/{entry['filename']}",
            "alt": normalized,
            "width": entry["display_width"],
            "height": entry["display_height"],
            "valign": entry["valign"],
        },
    )
    text_node.clear()
    text_node.append(glyph)
    used_fallbacks.add(normalized)
    math_text_fallback_rows.append(
        {
            "text": normalized,
            "filename": entry["filename"],
            "source_text_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        }
    )
assert len(math_text_fallback_rows) == 240
assert len(used_fallbacks) == len(fallback_entries) == 57
# Tie the stylesheet URL to its exact bytes so a browser that already opened an
# earlier development build cannot silently reuse stale responsive CSS.
stylesheet = soup.select_one('link[rel~="stylesheet"][href="reader.css"]')
assert stylesheet is not None
stylesheet["href"] = f"reader.css?v={sha(O / 'reader.css')[:16]}"
# The two deliberately retained standard/alternative reduction sections inherit
# the same upstream exercise label. HTML IDs must be unique; nothing references
# this exercise label, so suffix only the second generated ID.
duplicate_exercises = soup.select('[id="sfr:siz:red:prob:nat-nat"]')
assert len(duplicate_exercises) == 2
assert not soup.select('a[href="#sfr:siz:red:prob:nat-nat"]')
duplicate_exercises[1]["id"] = "sfr:siz:red:prob:nat-nat-alt"
section = None
counter = 0
numbered = {}
for node in soup.select("h1,h2,div.defn,div.ex,div.prop,div.thm,div.lem,div.cor,div.rem"):
    if node.name in ["h1", "h2"]:
        if node.name == "h2" and node.get("data-number"):
            section = node["data-number"]
            counter = 0
        elif node.name == "h1":
            section = None
        continue
    assert section, str(node)[:120]
    counter += 1
    number = f"{section}.{counter}"
    heading = node.find("strong")
    assert heading and re.search(r"\d+\.\d+", heading.get_text()), str(node)[:160]
    heading.string = re.sub(r"\d+\.\d+", number, heading.get_text(), count=1)
    if node.get("id"):
        numbered[node["id"]] = number
aux_text = (B / "openlogic-mr-core.aux").read_text(encoding="utf-8")
aux_labels = dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}", aux_text))
for link in soup.select("a[data-reference]"):
    key = link["data-reference"]
    if key in numbered:
        link.string = numbered[key]
    elif key in aux_labels:
        # Pandoc leaves references to numbered list items as [label-key]. The
        # settled TeX auxiliary file contains the exact printed item number.
        link.string = aux_labels[key]

# Pandoc retains labels on individual align rows in the TeX annotation but
# does not expose them as HTML fragment targets.  Add an adjacent HTML anchor
# for each label.  Keeping transport IDs outside MathML preserves the accepted
# MathML trees byte-for-byte when EPUB-safe fragment IDs are substituted.
math_row_anchors = []
existing_ids = {node["id"] for node in soup.select("[id]")}
for formula in soup.select("math"):
    annotation = formula.find("annotation", attrs={"encoding": "application/x-tex"})
    if annotation is None:
        continue
    source_math = annotation.get_text()
    for label_match in re.finditer(r"\\label\{([^}]+)\}", source_math):
        key = label_match.group(1)
        if key in existing_ids:
            continue
        row_index = len(re.findall(r"\\\\", source_math[: label_match.start()]))
        anchor = soup.new_tag("span", id=key)
        anchor["data-label"] = key
        formula.insert_before(anchor)
        existing_ids.add(key)
        math_row_anchors.append(
            {"label": key, "row_index": row_index, "target": "span-before-math"}
        )

all_ids = {node["id"] for node in soup.select("[id]")}
assert all(link["href"][1:] in all_ids for link in soup.select('a[href^="#"]'))
for formula in soup.select('math[display="block"]'):
    wrapper = soup.new_tag(
        "div",
        attrs={
            "class": "math-display",
            "tabindex": "0",
            "role": "region",
            "aria-label": "गणिती सूत्र; रुंद सूत्र आडवे सरकवता येते",
        },
    )
    formula.wrap(wrapper)

doc = "\n".join(line.rstrip() for line in str(soup).splitlines()) + "\n"
(O / "index.html").write_text(doc, encoding="utf-8", newline="\n")
report = {
    "schema": "openlogic-html-build/1",
    "scope": scope,
    "source_tex_sha256": sha(TEX),
    "source_pdf_sha256": sha(PDF),
    "html_sha256": sha(O / "index.html"),
    "html_bytes": (O / "index.html").stat().st_size,
    "diagram_assets": assets,
    "math_text_fallbacks": {
        "manifest": fallback_manifest_path.relative_to(P).as_posix(),
        "manifest_sha256": sha(fallback_manifest_path),
        "occurrences": len(math_text_fallback_rows),
        "unique_phrases": len(used_fallbacks),
        "used_phrases_sha256": hashlib.sha256(
            "\n".join(sorted(used_fallbacks)).encode("utf-8")
        ).hexdigest(),
        "assets": copied_fallbacks,
        "occurrence_map": math_text_fallback_rows,
    },
    "proof_representations": [
        {
            "id": spec["id"],
            "section_id": spec["section_id"],
            "caption": spec["caption"],
            "rows": spec["rows"],
        }
        for spec in proof_specs
    ],
    "math_row_anchors": math_row_anchors,
    "mathml_count": doc.count("<math "),
    "warnings": result.stderr,
    "validation": "Build complete; static and browser verification still required",
    "network_dependencies": [],
}
(B / "HTML_BUILD_RECEIPT.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
)
print(json.dumps({"html_bytes": report["html_bytes"], "mathml_count": report["mathml_count"], "diagrams": len(assets), "math_text_fallbacks": len(math_text_fallback_rows), "warnings": result.stderr}, ensure_ascii=False))
