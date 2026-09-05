"""Build offline semantic HTML/MathML for the five-chapter core reader."""

import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import fitz
from bs4 import BeautifulSoup


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
O = B / "html"
A = O / "assets"
A.mkdir(parents=True, exist_ok=True)
PDF = B / "openlogic-mr-core.pdf"
TEX = B / "openlogic-mr-core.tex"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


receipt = json.loads((B / "TEX_SUCCESS_RECEIPT.json").read_text(encoding="utf-8-sig"))
assert receipt["result"] == "built-log-clean"
assert sha(PDF) == receipt["pdf"]["sha256"]
assert sha(TEX) == receipt["texInputSha256"]
assert receipt["pdf"]["sha256"] == "be37d13d3a9706975d03f52a5fa4af88a87011247527c27da31ae0b6e9d1a743"

document = fitz.open(PDF)
assert len(document) == 66, "Reinspect diagram coordinates when pagination changes"
specs = [
    ("union", 8, (176, 131, 417, 328), "A आणि B या दोन संचांचा संयोग. दोन्ही बंद वक्रांचा संपूर्ण भाग चिन्हांकित आहे; म्हणजे A किंवा B यांपैकी किमान एका संचातील सर्व घटक."),
    ("intersection", 8, (176, 485, 417, 682), "A आणि B या दोन संचांचा छेद. दोन बंद वक्रांचा फक्त सामाईक आच्छादित भाग चिन्हांकित आहे."),
    ("difference", 10, (176, 68, 417, 264), "A वजा B हा संचफरक. A च्या वक्रातील B च्या बाहेर राहणारा भाग चिन्हांकित आहे; सामाईक भाग वगळलेला आहे."),
    ("graph-four", 19, (227, 207, 368, 305), "दिशित आलेखाची चार शिखरे 1, 2, 3 आणि 4. कडा 1 ते 1, 1 ते 2, 1 ते 3 आणि 2 ते 3; शिखर 4 एकाकी आहे."),
    ("graph-three", 19, (227, 340, 312, 439), "दिशित आलेखाची शिखरे 1, 2 आणि 3. कडा 1 ते 1, 1 ते 2, 1 ते 3 आणि 2 ते 3; आधीच्या आलेखातील एकाकी शिखर 4 येथे नाही."),
    ("tree", 19, (241, 662, 354, 776), "सांत वृक्ष. सर्वांत खाली मूळ r; त्याची अपत्ये a आणि b; a ची अपत्ये c, d आणि e. पूर्वज संबंध कडांवरून वरच्या दिशेने वाचला जातो."),
    ("function", 23, (176, 67, 417, 201), "फलनाची आकृती. डावीकडील प्रांतातील प्रत्येक फलसाधकापासून उजवीकडील सहप्रांतातील नेमक्या एका मूल्याकडे बाण जातो."),
    ("surjective", 24, (176, 613, 418, 746), "आच्छादक फलन. सहप्रांतातील प्रत्येक लाल घटकाकडे प्रांतातील किमान एका करड्या घटकापासून बाण येतो."),
    ("injective", 25, (176, 67, 417, 221), "एकास-एक फलन. वेगवेगळ्या करड्या फलसाधकांचे बाण वेगवेगळ्या लाल मूल्यांकडे जातात; सहप्रांतातील काही घटक मूल्य नसू शकतात."),
    ("bijective", 25, (176, 613, 418, 746), "एकास-एक व आच्छादक फलन. प्रांतातील प्रत्येक करडा घटक आणि सहप्रांतातील प्रत्येक लाल घटक यांची नेमकी एक जोडी बाणाने जोडलेली आहे."),
    ("composition", 29, (135, 602, 457, 747), "फलन-संयोजन g वर्तुळ f. डावीकडील A मधून f चे बाण मधल्या B मध्ये, B मधून g चे बाण उजवीकडील C मध्ये, आणि तुटक बाह्य बाण A मधून थेट C मधील त्याच अंतिम मूल्यांकडे जातात."),
    ("root-two-square", 54, (214, 388, 367, 483), "वर्गमूळ दोनच्या अपरिमेयतेची भूमितीय आकृती. m बाजूच्या मोठ्या चौरसात n बाजूचे दोन आच्छादित चौरस आहेत; नारिंगी सामाईक चौरस आणि दोन न रंगवलेले कोपरे लहान समान रचना दाखवतात."),
]

assets = []
for name, page, rect, alt in specs:
    x0, y0, x1, y1 = rect
    svg = document[page - 1].get_svg_image(text_as_path=True)
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
            "alt": alt,
        }
    )

tex = TEX.read_text(encoding="utf-8")
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
assert r"\begin{tikzpicture}" not in tex
assert not re.search(r"\\olasset(?:\[[^]]+\])?\{assets/", tex)

# Pandoc's MathML writer does not understand the TeX implementation of the
# partial-function arrow. The standard right-harpoon glyph has the same
# mathematical role and converts to native MathML.
tex, count = re.subn(r"(?m)^\\newcommand\{\\pto\}.*$", "", tex)
assert count == 1
tex = tex.replace(r"\pto", r"\rightharpoonup")

# TeX permits ordinary prose between aligned rows via \intertext; Pandoc does
# not. Split this single prose-bearing display into two displays so the prose
# and its inline mathematics remain semantic HTML in their original order.
marker = r"\intertext{"
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
assert align_start >= 0 and "या परिमेय संख्यांवर" in intertext
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
assert r"\intertext" not in tex

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

html_input = B / "html-input.tex"
html_input.write_text(tex, encoding="utf-8", newline="\n")
font_dir = O / "fonts"
font_dir.mkdir(exist_ok=True)
for name in ["OLMarathiSerif-Regular.ttf", "OLMarathiSerif-Bold.ttf", "OFL.txt"]:
    shutil.copyfile(P / "fonts" / name, font_dir / name)

css = """@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Regular.ttf)}@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Bold.ttf);font-weight:bold}*{box-sizing:border-box}html{scroll-behavior:smooth;overflow-x:hidden}body{font-family:OLMarathi,serif;line-height:1.75;margin:0 auto;padding:2rem 1.25rem 5rem;max-width:58rem;color:#202124;background:#fff;overflow-wrap:break-word}h1,h2,h3{line-height:1.4;scroll-margin-top:1rem}h1{margin-top:3rem;border-bottom:2px solid #a81c21;padding-bottom:.6rem}a{color:#064c8c}a:focus-visible{outline:3px solid #a81c21;outline-offset:3px}a.uri{overflow-wrap:anywhere;word-break:break-word}img{max-width:100%;height:auto;display:block;margin:1rem auto}figure{margin:2rem 0}figcaption{font-size:.94rem;text-align:center}.math.display{display:block;overflow-x:auto;padding:.7rem 0}math{font-size:1.05em;max-width:100%}p math[display="inline"]{overflow-x:auto;overflow-y:hidden;vertical-align:middle}.proof{border-left:3px solid #ddd;padding-left:1rem}.defn,.ex,.prop,.thm,.lem,.cor,.prob{margin:1.2rem 0}.titlepage{border-bottom:1px solid #bbb;padding-bottom:1.5rem}#TOC{background:#f3f5f7;padding:1rem 1.5rem;border-radius:.3rem}code{overflow-wrap:anywhere}p{orphans:3;widows:3}.math-display{max-width:100%;overflow-x:auto;margin:1rem 0;padding:.5rem 0}.math-display math{margin:0 auto}figure img{width:auto}@media(max-width:600px){body{font-size:1.06rem;padding:.9rem}h1{font-size:1.7rem}h2{font-size:1.35rem}#TOC{padding:.8rem 1rem}}@media print{body{max-width:none}#TOC{page-break-after:always}a{color:inherit}}"""
(O / "reader.css").write_text(css + "\n", encoding="utf-8")

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
    "--metadata=title:मुक्त तर्कशास्त्र — संच, संबंध, फलने, संचांचे आकारमान आणि अंकगणितीकरण",
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

    def label(match, alt=asset["alt"]):
        tag = re.sub(r'\s+alt="[^"]*"', "", match.group(1))
        return tag + ' alt="' + html.escape(alt, quote=True) + '" loading="lazy"' + match.group(2)

    doc, count = re.subn(pattern, label, doc)
    assert count == 1, (asset["filename"], count)
doc = doc.replace(
    "<body>",
    '<body>\n<a class="skip-link" href="#main-content">मुख्य मजकुराकडे जा</a>\n<main id="main-content">',
    1,
).replace("</body>", "</main>\n</body>")

soup = BeautifulSoup(doc, "html.parser")
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
for node in soup.select("h1,h2,div.defn,div.ex,div.prop,div.thm,div.lem,div.cor"):
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
for link in soup.select("a[data-reference]"):
    if link["data-reference"] in numbered:
        link.string = numbered[link["data-reference"]]
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

doc = str(soup)
(O / "index.html").write_text(doc, encoding="utf-8", newline="\n")
report = {
    "schema": "openlogic-html-build/1",
    "scope": {"translation_source_units": 45, "reader_sections": 40, "complete_chapters": 5},
    "source_tex_sha256": sha(TEX),
    "source_pdf_sha256": sha(PDF),
    "html_sha256": sha(O / "index.html"),
    "html_bytes": (O / "index.html").stat().st_size,
    "diagram_assets": assets,
    "mathml_count": doc.count("<math "),
    "warnings": result.stderr,
    "validation": "Build complete; static and browser verification still required",
    "network_dependencies": [],
}
(B / "HTML_BUILD_RECEIPT.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
)
print(json.dumps({"html_bytes": report["html_bytes"], "mathml_count": report["mathml_count"], "diagrams": len(assets), "warnings": result.stderr}, ensure_ascii=False))
