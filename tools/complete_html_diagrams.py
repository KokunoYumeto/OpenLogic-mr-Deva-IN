"""Extract complete-reader diagrams as PDF-faithful SVGs with source receipts.

The crop map is checked against the 722-unit source inventory. These SVGs are
provisional until the guarded complete PDF build succeeds; rerun this script
from that final PDF and rebuild HTML before release.
"""

import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

import fitz
from complete_diagram_inventory import current_inventory


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
ASSETS = BUILD / "html/assets"
ASSETS.mkdir(parents=True, exist_ok=True)
PDF = BUILD / "openlogic-mr-full.pdf"


# Page numbers are physical PDF pages. Coordinates are PDF points and exclude
# captions, which remain in the surrounding semantic HTML.
CROPS = {
    'turing-machine': (335, 178.017, 68.821, 416.106, 229.746),
    'tikz-015': (279, 210.5, 643.26, 384.777, 732.497),
    'tikz-016': (287, 182.153, 552.836, 413.125, 670.421),
    'tikz-017': (336, 218.141, 172.865, 380.472, 205.081),
    'tikz-018': (336, 216.048, 306.691, 379.125, 383.849),
    'tikz-019': (337, 216.048, 493.671, 379.125, 570.829),
    'tikz-020': (338, 167.152, 563.022, 428.022, 734.268),
    'tikz-021': (341, 175.966, 675.462, 418.101, 737.439),
    'tikz-022': (342, 163.101, 101.054, 430.966, 351.672),
    'tikz-023': (342, 152.743, 455.121, 442.513, 705.738),
    'tikz-024': (343, 216.048, 631.376, 379.125, 772.725),
    'tikz-025': (344, 206.043, 113.85, 388.023, 240.483),
    'tikz-026': (345, 190.08, 72.428, 408.535, 217.028),
    'tikz-027': (346, 175.966, 235.954, 418.101, 297.931),
    'tikz-028': (346, 178.456, 372.643, 420.158, 546.868),
    'tikz-029': (347, 143.905, 72.428, 451.27, 355.922),
    'tikz-030': (351, 216.048, 71.431, 379.125, 148.589),
    'tikz-031': (351, 216.048, 151.526, 379.125, 228.684),
    'tikz-032': (351, 216.048, 284.02, 379.125, 361.178),
    'tikz-033': (530, 252.349, 65.953, 343.225, 192.179),
    'tikz-034': (532, 219.684, 214.772, 375.093, 326.7),
    'tikz-035': (538, 232.241, 362.707, 363.332, 438.233),
    'tikz-036': (540, 249.426, 676.409, 348.881, 719.59),
    'tikz-037': (547, 210.3, 68.567, 384.977, 186.55),
    'tikz-038': (561, 249.013, 367.5, 349.292, 437.49),
    'tikz-039': (561, 203.459, 611.182, 392.115, 711.49),
    'tikz-040': (563, 208.362, 69.165, 386.914, 232.473),
    'tikz-041': (579, 170.716, 644.687, 422.569, 676.025),
    'tikz-042': (579, 172.757, 676.06, 422.522, 744.476),
    'tikz-043': (580, 192.64, 69.731, 400.666, 274.166),
    'tikz-044': (583, 201.11, 513.027, 394.165, 648.517),
    'tikz-045': (584, 189.856, 69.165, 405.42, 238.369),
    'tikz-046': (599, 229.199, 654.959, 366.374, 732.335),
    'tikz-047': (616, 237.256, 71.552, 361.653, 251.62),
    'tikz-048': (618, 185.119, 584.815, 410.158, 730.821),
    'tikz-049': (621, 153.91, 308.364, 440.97, 491.504),
    'tikz-050': (657, 239.727, 71.508, 354.425, 177.93),
    'tikz-051': (658, 218.383, 69.165, 376.892, 205.629),
    'tikz-052': (659, 239.727, 71.508, 354.425, 177.93),
    'tikz-053': (659, 239.231, 255.975, 353.929, 362.397),
    'tikz-054': (659, 239.727, 625.024, 354.425, 731.96),
    'tikz-055': (660, 239.727, 70.994, 354.425, 177.93),
    'tikz-056': (660, 226.004, 231.477, 369.271, 364.001),
    'tikz-057': (661, 220.214, 69.166, 375.062, 215.834),
    'tikz-058': (662, 229.406, 574.906, 368.904, 731.96),
    'tikz-059': (667, 224.594, 266.482, 367.243, 416.13),
    'tikz-060': (668, 207.586, 232.561, 384.252, 382.209),
    'tikz-061': (678, 206.747, 526.666, 388.503, 542.713),
    'tikz-062': (678, 208.408, 599.165, 386.87, 615.211),
    'tikz-063': (678, 206.748, 706.893, 388.504, 722.94),
    'tikz-064': (712, 247.644, 716.565, 347.624, 768.944),
    'tikz-065': (871, 214.476, 440.189, 377.558, 623.536),
    'tikz-066': (873, 218.018, 255.189, 374.014, 360.785),
    'tikz-067': (874, 156.262, 500.024, 439.018, 683.152),
    'tikz-068': (877, 255.688, 169.333, 339.588, 253.233),
    'tikz-069': (877, 255.688, 325.662, 339.588, 409.562),
    'tikz-070': (877, 255.688, 534.872, 339.588, 618.771),
}


ALT_OVERRIDE = {
    "turing-machine": "ट्यूरिंग यंत्राच्या फितीवरील तीन सलग स्थिती: शीर्षाखालील चिन्ह आणि अवस्था q1, q2, q3 बदलतात.",
    "tikz-015": "Γ आणि Δ यांची दोन स्वतंत्र वर्तुळे आहेत. विभागांवर C आणि ¬C अशी मूळ लेबले आहेत; सोबतच्या मजकुरात त्यांना विलग करणारे सूत्र χ म्हटले आहे.",
    "tikz-016": "संरचना A मधील M आणि N उपरचना; त्यांच्यामध्ये I हे अंतर्गत आंशिक समरूपण दाखवणारा दुतोंडी बाण.",
    "tikz-017": "दोन अवस्थांचे ट्यूरिंग यंत्र: q0 मधून q1 कडे जाताना रिकाम्या घरात रेघ लिहून उजवीकडे सरकते.",
    "tikz-018": "सम संख्येच्या रेघा ओळखणारे दोन अवस्थांचे ट्यूरिंग यंत्र; प्रत्येक रेघेनंतर q0 आणि q1 यांची अदलाबदल होते.",
    "tikz-019": "दोन्ही अवस्थांवर रिकाम्या चिन्हाचे पुनरावर्ती संक्रमण असलेले, कधीही न थांबणारे सम यंत्र.",
    "tikz-020": "दुप्पट करणाऱ्या ट्यूरिंग यंत्राचा सहा अवस्थांचा संक्रमण-आलेख.",
    "tikz-021": "f(x,y)=x+y संगणित करणाऱ्या तीन अवस्थांच्या यंत्राचा संक्रमण-आलेख.",
    "tikz-022": "f(x)=2x संगणित करणाऱ्या नऊ अवस्थांच्या यंत्राचा संक्रमण-आलेख.",
    "tikz-024": "सम यंत्रात q0 पासून स्वतंत्र स्वीकार-अवस्था h कडे जाणारा बाण जोडला आहे.",
    "tikz-025": "सम यंत्रात स्वीकार-अवस्था h आणि नकार-अवस्था r यांकडे जाणारे संक्रमण दाखवले आहे.",
    "tikz-027": "बेरीज-यंत्राच्या सुरुवातीच्या q0, q1, q2 अवस्थांचा आणि त्यांच्या संक्रमणांचा आलेख.",
    "tikz-028": "बेरीज-यंत्राला दुप्पट करणारे यंत्र जोडण्यासाठी q3 आणि q4 अवस्थांनी वाढवलेला आलेख.",
    "tikz-029": "बेरीज आणि दुप्पट करणाऱ्या यंत्रांचे जोडलेले दहा अवस्थांचे संक्रमण-आलेख.",
    "tikz-030": "q0 आणि q1 अवस्था तसेच रेघ आणि रिकामे चिन्ह वापरणारे सम यंत्र.",
    "tikz-031": "s आणि h अवस्था तसेच A आणि रिकामे चिन्ह वापरणारे सम यंत्र; मागील आलेखाशी रचनेने समान.",
    "tikz-032": "1 आणि 2 या नामांकित अवस्था आणि 2, 3 चिन्हे वापरणारे मानक सम यंत्र.",
    "tikz-033": "साधा मोडल प्रतिमान-आलेख: w1 पासून w2 आणि w3 कडे बाण; प्रत्येक जगाशी p आणि q ची सत्यता लिहिली आहे.",
    "tikz-034": "तीन जगांचा दिशित प्रतिमान-आलेख; जगांजवळ p1, p2, p3 ची सत्य-असत्य मूल्ये लिहिली आहेत.",
    "tikz-035": "p असत्य असलेल्या w1 पासून p सत्य असलेल्या w2 आणि w3 कडे बाण असलेले प्रतिदृष्टांत प्रतिमान.",
    "tikz-036": "w आणि w′ या दोन जगांदरम्यान दोन्ही दिशांचे बाण; A आणि ◇A ची पूर्ती दर्शवली आहे.",
    "tikz-038": "w1 आणि w2 ही एकमेकांना प्राप्य जगे; p पहिल्यात असत्य आणि दुसऱ्यात सत्य.",
    "tikz-039": "w1, w2, w3 ही शेजारी परस्पर प्राप्य जगे; प्रत्येकावर स्वबाण आणि p ची भिन्न सत्यता.",
    "tikz-040": "चार जगांचे प्रतिमान: मधल्या जगांत p सत्य, वरच्या आणि खालच्या जगांत असत्य; अनेक दिशित बाण.",
    "tikz-041": "अनंत प्रतिमानाची सुरुवात: 1, 2, 3, 4 अशी क्रमिक जगे; p सम क्रमांकांच्या जगांत सत्य आहे.",
    "tikz-042": "अनंत प्रतिमानाची दोन निस्यंदने: [1] आणि [2] यांच्यात दोन्ही दिशांचे बाण, दुसरीत [2] वर स्वबाण.",
    "tikz-043": "द्विआधारी वृक्ष-प्रतिमान: 0 पासून 00 आणि 01, मग 000, 001, 010, 011 अशी जगे फुटतात; p आणि q ची सत्यता दाखवली आहे.",
    "tikz-045": "मूळ पाच जगांचे चार वर्गांत निस्यंदन; वर्गांमधील बाण आणि p ची सत्यता दाखवली आहे.",
    "tikz-046": "मूळ जग 1 पासून 1.1 आणि 1.2 कडे बाण; एका शाखेत p असत्य व q सत्य, दुसरीत p सत्य व q असत्य.",
    "tikz-047": "ज्ञानविषयक प्रतिमानातील w1, w2, w3 जगे, a आणि b लेबलांचे प्राप्यता बाण आणि p, q ची सत्यता.",
    "tikz-048": "डावीकडील चार जगांचा आणि उजवीकडील दोन जगांचा द्विअनुकरणसदृश ज्ञानविषयक प्रतिमान-आलेख.",
    "tikz-049": "p ची सार्वजनिक घोषणा होण्यापूर्वीची डावीकडील जगे आणि त्यानंतर उरलेली उजवीकडील जगे.",
    "tikz-050": "केंद्रस्थानी w असलेले समकेंद्री गोलक आणि त्यांना छेदणारे A व B प्रस्तावांचे वक्र प्रदेश.",
    "tikz-051": "मध्यवर्ती w भोवती क्रमाने मोठे होत जाणारे गोलक; w1 ते w7 जगे आणि p सत्य असलेल्या w5, w6, w7 जगांचा प्रदेश.",
    "tikz-052": "समकेंद्री गोलकांवर A आणि B प्रदेशांचे छेद; जवळच्या A-जगांत B सत्य असल्याचे राखाडी क्षेत्र.",
    "tikz-053": "w भोवती समकेंद्री गोलक; A प्रदेश सर्व गोलकांच्या बाहेर असल्याने प्रतिवास्तविक विधान रिक्तपणे सत्य.",
    "tikz-054": "समकेंद्री गोलकांत जवळचा A प्रदेश राखाडी सत्य-क्षेत्राबाहेर छेदतो; प्रतिवास्तविक विधान असत्य.",
    "tikz-055": "समकेंद्री गोलकांत A प्रदेशाच्या काही भागांत B सत्य आणि काही भागांत असत्य; विरुद्ध उत्तरांग सत्य.",
    "tikz-056": "w भोवती अनेक गोलक आणि दुसऱ्या केंद्राभोवती गोलक; A व B प्रदेशांमधील छेद परिस्थितीवश सत्यता दाखवतो.",
    "tikz-057": "w, w1, w2 असलेल्या गोलक-प्रतिमानात p, q, r प्रदेश; पूर्वांग बळकट करण्याच्या नियमाचे प्रतिउदाहरण.",
    "tikz-058": "w, w1, w2 असलेल्या गोलक-प्रतिमानात p, q आणि त्यांचे निषेध; प्रतिपरिवर्तनाचे प्रतिउदाहरण.",
    "tikz-059": "संचांच्या संचयी पदानुक्रमाचे V-आकाराचे चित्र; तळाशी 0 आणि वर जाताना 1 ते 6 टप्पे.",
    "tikz-060": "मूलघटकांसह संचांचा संचयी पदानुक्रम; रुंद तळापासून वर वाढणारे 0 ते 6 टप्पे.",
    "tikz-061": "नैसर्गिक संख्यांचा क्रम: 0 < 1 < 2 < 3 < 4 < 5 < …",
    "tikz-062": "एक शेवटचा घटक असलेला क्रम: 1 < 2 < 3 < 4 < 5 < … < 0",
    "tikz-063": "सम संख्यांनंतर विषम संख्या: 0 < 2 < 4 < … < 1 < 3 < …",
    "tikz-064": "A ते B एकास-एक फलन, A ते |A| आणि B ते |B| दुतोंडी बाण, आणि |A| ते |B| तुटक बाण.",
    "tikz-065": "f(x)=x²/4+1/2 चा काळा आलेख आणि तीन वेगवेगळ्या अंतरांवरील रंगीत छेदक त्रिकोण.",
    "tikz-066": "मूलबिंदूवर कोन असलेला |x| या फलनाचा V-आकाराचा आलेख.",
    "tikz-067": "हिल्बर्टच्या अवकाशभरणाऱ्या वक्राच्या पहिल्या सहा पायऱ्या, दोन रांगांत क्रमाने.",
    "tikz-068": "दोन-बाय-दोन जाळीत हिल्बर्ट वक्राची पहिली U-आकाराची पायरी; लाल टोकांचे भाग दाखवले आहेत.",
    "tikz-069": "चार-बाय-चार जाळीत हिल्बर्ट वक्राची दुसरी पायरी; काळ्या वक्रांना हिरव्या जोडरेषा आणि लाल टोकांचे भाग.",
    "tikz-070": "आठ-बाय-आठ जाळीत हिल्बर्ट वक्राची तिसरी, अधिक गुंतागुंतीची पायरी.",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def intersects_including_lines(a, b):
    """PDF paths with zero height or width still contain visible strokes."""
    return a.x0 <= b.x1 and a.y0 <= b.y1 and a.x1 >= b.x0 and a.y1 >= b.y0


def contains_including_lines(a, b):
    return a.x0 <= b.x0 and a.y0 <= b.y0 and a.x1 >= b.x1 and a.y1 >= b.y1


tex_source = (BUILD / "openlogic-mr-full.tex").read_text(encoding="utf-8")
inventory = current_inventory(tex_source)
(BUILD / "HTML_DIAGRAM_INVENTORY.json").write_text(
    json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
entries = {item["name"]: item for item in inventory}
assert len(entries) == 70
assert set(CROPS) == {"turing-machine"} | {f"tikz-{number:03d}" for number in range(15, 71)}
assert set(CROPS).issubset(entries)
assert set(ALT_OVERRIDE).issubset(CROPS)
tikz_sources = list(re.finditer(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", tex_source, re.S))
assert len(tikz_sources) == 61
for number in range(10, 71):
    item = entries[f"tikz-{number:03d}"]
    match = tikz_sources[number - 10]
    assert item["source_sha256"] == hashlib.sha256(match.group().encode("utf-8")).hexdigest()
    item["source_line"] = tex_source.count("\n", 0, match.start()) + 1
asset_source = re.search(r"\\olasset(?:\[[^]]+\])?\{assets/diagrams/turing-machine\.tikz\}", tex_source)
assert asset_source
entries["turing-machine"]["source_line"] = tex_source.count("\n", 0, asset_source.start()) + 1

pdf = fitz.open(PDF)
pdf_sha = sha(PDF)
aux_source = (BUILD / "openlogic-mr-full.aux").read_text(encoding="utf-8")
label_pages = {label: int(page) for label, page in re.findall(
    r"\\newlabel\{([^}]+)\}\{\{[^}]*\}\{(\d+)\}", aux_source
)}
for name, crop in CROPS.items():
    for label in entries[name].get("figure_labels", []):
        if label in label_pages:
            assert label_pages[label] == crop[0], (name, label, label_pages[label], crop[0])
# A later bounded attempt may fail to acquire the slot. Only a successful
# compilation can establish the PDF source, and it must match this reader.
tex_receipt_path = BUILD / "TEX_SUCCESS_RECEIPT.json"
tex_receipt = json.loads(tex_receipt_path.read_text(encoding="utf-8-sig")) if tex_receipt_path.exists() else {}
verified_pdf = (
    tex_receipt.get("result") == "built-log-clean"
    and tex_receipt.get("pdf", {}).get("sha256") == pdf_sha
    and tex_receipt.get("texInputSha256") == sha(BUILD / "openlogic-mr-full.tex")
)
receipt = {
    "schema": "openlogic-full-html-diagram-assets/1",
    "source_pdf_sha256": pdf_sha,
    "source_tex_sha256": sha(BUILD / "openlogic-mr-full.tex"),
    "status": "final-source" if verified_pdf else "provisional",
    "assets": [],
}
for name, (page_number, x0, y0, x1, y1) in CROPS.items():
    item = entries[name]
    assert 1 <= page_number <= len(pdf), name
    assert 0 <= x0 < x1 <= pdf[page_number - 1].rect.width, name
    assert 0 <= y0 < y1 <= pdf[page_number - 1].rect.height, name
    caption = item.get("caption_tex")
    if name in ALT_OVERRIDE:
        alt = ALT_OVERRIDE[name]
    else:
        assert caption, f"Missing diagram description: {name}"
        caption = re.sub(r"\\ref\{[^}]+\}", "संबंधित प्रमेय", caption)
        caption = re.sub(r"\\Struct\{([^{}]+)\}", r"\1", caption)
        caption = re.sub(r"\\Ax\{([^{}]+)\}", r"\1", caption)
        caption = caption.replace(r"$\TMstroke$", "रेघ")
        caption = caption.replace(r"\lif", r"\to").replace(r"\Entails", r"\models")
        conversion = subprocess.run(
            ["pandoc", "--from=latex", "--to=plain"],
            input=caption, capture_output=True, text=True, encoding="utf-8", check=True,
        )
        alt = "आकृती: " + " ".join(conversion.stdout.split())
    assert len(alt) >= 15 and "\\" not in alt, (name, alt)
    clip = fitz.Rect(x0, y0, x1, y1)
    page = pdf[page_number - 1]
    # A crop must contain every label or vector path that it intersects.
    # This also catches a stray fragment of neighboring prose or diagrams.
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                rect = fitz.Rect(span["bbox"])
                assert not rect.intersects(clip) or clip.contains(rect), (name, span["text"], list(rect))
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        assert not intersects_including_lines(rect, clip) or contains_including_lines(clip, rect), (name, list(rect))
    cropped = fitz.open()
    cropped.new_page(width=clip.width, height=clip.height).show_pdf_page(
        fitz.Rect(0, 0, clip.width, clip.height), pdf, page_number - 1, clip=clip
    )
    svg = cropped[0].get_svg_image(text_as_path=True)
    close_of_root = svg.index(">")
    svg = (svg[:close_of_root] + ' role="img">' +
           "<title>" + html.escape(alt) + "</title>" + svg[close_of_root + 1:])
    destination = ASSETS / (name + ".svg")
    destination.write_text(svg, encoding="utf-8", newline="\n")
    receipt["assets"].append({
        "name": name, "filename": destination.name, "sha256": sha(destination),
        "bytes": destination.stat().st_size, "source_line": item["source_line"],
        "source_sha256": item.get("source_sha256"), "pdf_page": page_number,
        "pdf_crop_points": [x0, y0, x1, y1], "alt": alt,
    })
    cropped.close()
pdf.close()
(BUILD / "HTML_DIAGRAM_RECEIPT.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "assets": len(receipt["assets"]),
    "source_pdf_sha256": pdf_sha,
    "bytes": sum(row["bytes"] for row in receipt["assets"]),
}, ensure_ascii=False))
