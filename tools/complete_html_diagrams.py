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


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
ASSETS = BUILD / "html/assets"
ASSETS.mkdir(parents=True, exist_ok=True)
PDF = BUILD / "openlogic-mr-full.pdf"


# Page numbers are physical PDF pages. Coordinates are PDF points and exclude
# captions, which remain in the surrounding semantic HTML.
CROPS = {
    "turing-machine": (335, 175, 65, 420, 240),
    "tikz-015": (279, 200, 641, 395, 738),
    "tikz-016": (287, 175, 550, 420, 675),
    "tikz-017": (336, 195, 164, 390, 216),
    "tikz-018": (336, 205, 315, 390, 400),
    "tikz-019": (337, 205, 492, 390, 580),
    "tikz-020": (338, 160, 565, 435, 733),
    "tikz-021": (341, 175, 675, 435, 743),
    "tikz-022": (342, 160, 100, 435, 353),
    "tikz-023": (342, 150, 450, 450, 715),
    "tikz-024": (343, 170, 630, 395, 778),
    "tikz-025": (344, 170, 115, 395, 247),
    "tikz-026": (345, 175, 65, 425, 224),
    "tikz-027": (346, 170, 235, 435, 301),
    "tikz-028": (346, 170, 372, 435, 550),
    "tikz-029": (347, 140, 72, 455, 358),
    "tikz-030": (351, 190, 70, 390, 152),
    "tikz-031": (351, 200, 150, 390, 232),
    "tikz-032": (351, 200, 283, 390, 365),
    "tikz-033": (525, 240, 60, 345, 200),
    "tikz-034": (527, 215, 205, 400, 325),
    "tikz-035": (532, 215, 645, 370, 740),
    "tikz-036": (534, 245, 665, 360, 718),
    "tikz-037": (541, 200, 60, 400, 193),
    "tikz-038": (555, 235, 367, 360, 441),
    "tikz-039": (555, 190, 598, 405, 714),
    "tikz-040": (557, 195, 60, 400, 235),
    "tikz-041": (573, 165, 635, 430, 676),
    "tikz-042": (573, 165, 676, 430, 745),
    "tikz-043": (573, 185, 394, 415, 605),
    "tikz-044": (577, 190, 211, 405, 349),
    "tikz-045": (577, 187, 388, 415, 564),
    "tikz-046": (593, 220, 355, 385, 445),
    "tikz-047": (609, 232, 70, 370, 252),
    "tikz-048": (611, 175, 60, 420, 219),
    "tikz-049": (614, 150, 306, 450, 495),
    "tikz-050": (648, 230, 62, 365, 188),
    "tikz-051": (649, 210, 60, 385, 215),
    "tikz-052": (650, 230, 72, 365, 199),
    "tikz-053": (650, 230, 250, 365, 378),
    "tikz-054": (650, 230, 426, 365, 555),
    "tikz-055": (650, 230, 603, 365, 732),
    "tikz-056": (651, 215, 60, 380, 215),
    "tikz-057": (651, 210, 575, 385, 741),
    "tikz-058": (653, 220, 565, 380, 741),
    "tikz-059": (658, 215, 180, 375, 337),
    "tikz-060": (659, 195, 60, 390, 219),
    "tikz-061": (669, 202, 525, 395, 546),
    "tikz-062": (669, 202, 597, 395, 620),
    "tikz-063": (669, 202, 704, 395, 727),
    "tikz-064": (703, 242, 710, 355, 773),
    "tikz-065": (859, 195, 435, 385, 625),
    "tikz-066": (861, 205, 248, 380, 359),
    "tikz-067": (862, 145, 490, 450, 695),
    "tikz-068": (865, 245, 60, 350, 165),
    "tikz-069": (865, 245, 217, 350, 322),
    "tikz-070": (865, 245, 433, 350, 534),
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
    "tikz-045": "मूळ पाच जगांचे तीन वर्गांत निस्यंदन; वर्गांमधील बाण आणि p ची सत्यता दाखवली आहे.",
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


inventory = json.loads((BUILD / "HTML_DIAGRAM_INVENTORY.json").read_text(encoding="utf-8"))
entries = {item["name"]: item for item in inventory}
assert len(entries) == 70
assert set(CROPS) == {"turing-machine"} | {f"tikz-{number:03d}" for number in range(15, 71)}
assert set(CROPS).issubset(entries)
assert set(ALT_OVERRIDE).issubset(CROPS)
tex_source = (BUILD / "openlogic-mr-full.tex").read_text(encoding="utf-8")
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
tex_receipt_path = BUILD / "TEX_BUILD_RECEIPT.json"
tex_receipt = json.loads(tex_receipt_path.read_text(encoding="utf-8-sig")) if tex_receipt_path.exists() else {}
verified_pdf = (
    tex_receipt.get("result") == "built-log-clean"
    and tex_receipt.get("pdf", {}).get("sha256") == pdf_sha
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
        assert not rect.intersects(clip) or clip.contains(rect), (name, list(rect))
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
