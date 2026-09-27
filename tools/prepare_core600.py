"""Assemble 66 complete Marathi chapters through OLP-0600 without TeX."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
with redirect_stdout(StringIO()):
    prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core591.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("पासष्ट संपूर्ण प्रकरणे") == 1
base = base.replace("पासष्ट संपूर्ण प्रकरणे", "सहासष्ट संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0591, एकूण 588 स्रोत-एकके आणि 509 वाचक-विभाग. उर्वरित 134"
new = "OLP-0004 ते OLP-0600, एकूण 597 स्रोत-एकके आणि 517 वाचक-विभाग. उर्वरित 125"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\newcommand{\funfromto}[2]{{}^{#1}{#2}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + "\n".join([
    r"\newcommand{\cardnless}[2]{#1 \npreceq #2}",
    r"\newcommand{\onesphere}{\mathbf{S}}",
    r"\newcommand{\rotationsgroup}{R}",
]), 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]

bibliographic_names = {
    "Hartogs1915": ("हार्टोग्स", "1915"), "Potter2004": ("पॉटर", "2004"),
    "Cantor1883": ("कँटर", "1883"), "Zermelo1904": ("झर्मेलो", "1904"),
    "Dedekind1888": ("डेडेकिंड", "1888"), "Cohen1966": ("कोहेन", "1966"),
    "Cantor1878": ("कँटर", "1878"), "FefermanLevy1963": ("फेफरमन आणि लेव्ही", "1963"),
    "Russell1919": ("रसेल", "1919"), "BanachTarski1924": ("बानाख आणि टार्स्की", "1924"),
    "Wagon2016": ("वॅगन", "2016"), "Weston2003": ("वेस्टन", "2003"),
    "Robinson1947": ("रॉबिन्सन", "1947"), "Vitali1905": ("विताली", "1905"),
    "Hausdorff1914": ("हाउसडॉर्फ", "1914"),
}


def render_citation(match):
    command, options, key = match.groups()
    assert key in bibliographic_names, key
    author, year = bibliographic_names[key]
    locators = re.findall(r"\[([^]]*)\]", options)
    assert len(locators) <= 1, options
    locator = locators[0] if locators else ""
    locator = locator.replace("pp.~", "पृ.~").replace("p.~", "पृ.~")
    locator = locator.replace("chs.~", "प्रकरणे~").replace("Theorem ", "प्रमेय ")
    if re.fullmatch(r"\d+(?:--\d+)?", locator):
        locator = "पृ.~" + locator
    suffix = ", " + locator if locator else ""
    if command == "citeauthor":
        assert not locator
        return author
    if command == "citeyear":
        return year + suffix
    if command == "citet":
        return author + " (" + year + suffix + ")"
    assert command in {"cite", "citep"}, command
    return "(" + author + " " + year + suffix + ")"


folder = ROOT / "mr/content/set-theory/choice"
driver = selected((folder / "choice.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{choice}{निवड}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["introduction", "tarskiscott", "hartogs", "wellorderingproblem",
                   "countablechoice", "justifications", "banach", "vitali"]
available.add("sth:choice:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "choice", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{निवड}\label{sth:choice:chap}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = content.replace("!!{injection}", "एकास-एक फलन").replace("!!a{injection}", "एकास-एक फलन")
    content = content.replace("!!{surjection}", "आच्छादन").replace("!!a{surjection}", "आच्छादन")
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\crefrange\{([^}]+)\}\{([^}]+)\}",
        lambda m: r"\ref{" + m.group(1).replace("::chap", ":chap")
        + "}--" + r"\ref{" + m.group(2).replace("::chap", ":chap") + "}", content)
    content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}",
        lambda m: " आणि ".join(r"\ref{" + x.strip() + "}" for x in m.group(1).split(",")), content)
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tag_references, content, flags=re.S)
    content = re.sub(r"\\(cite[a-zA-Z]*)((?:\[[^]]*\])*)\{([^}]+)\}", render_citation, content)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref|crefrange|cite\w*)", content)
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(marker) == 1
before, notes = base.split(marker, 1)
bib_marker = r"\chapter*{संदर्भ}"
assert notes.count(bib_marker) == 1
note_body, bibliography = notes.split(bib_marker, 1)
editorial = (
    "\n" + r"\paragraph{टार्स्की--स्कॉटच्या आक्षेपातील रिक्त संच.} "
    "तुल्यबल संचांचे सर्व प्रतिनिधी एकत्र केल्यास प्रतांकाची मर्यादा राहत नाही, "
    "हा आक्षेप अरिक्त आधारसंचासाठी आहे. रिक्त आधारसंचाचा वर्ग मात्र एकघटकी संच आहे. "
    "मराठीत हा अपवाद स्पष्ट केला आहे.\n"
    + r"\paragraph{हार्टोग्सच्या पुराव्यातील संच आणि निर्देशांक.} "
    "मूळ पुराव्यात सुक्रमित आधारसंच हा संबंधाचा उपसंच असल्यासारखा छापला आहे; "
    "तो मूळ आधारसंचाचा उपसंच असतो. घूर्णनाशी संबंध नसलेल्या याच पुराव्यात "
    "फलनाने क्रम नेण्याच्या सूत्रात निश्चित क्रमसूचक संख्या आणि अंतर्गत निर्देशांक "
    "यांना एकच नाव दिले आहे. मराठीत वेगळी, प्रांतात बंधित नावे वापरली आहेत.\n"
    + r"\paragraph{निवडीच्या पुराव्यातील थांबण्याची व्याख्या.} "
    "मूळ पुढील-मूल्य अटीतील असमानतेची दिशा आधीच्या निवडी पुसून टाकते. "
    "ती दुरुस्त करून, एकास-एक आणि आच्छादक फलनाचा दावा फक्त थांबण्यापूर्वीच्या "
    "अंशासाठी केला आहे. रिक्त आधारसंचाचे प्रकरण आधी सोडवले आहे; "
    "न थांबण्याचा विरोधाभास प्रत्यक्ष आधारसंचावरील हार्टोग्स निष्कर्षाने मिळतो.\n"
    + r"\paragraph{गणनीय निवडीच्या मोजणीतील निर्देशांक.} "
    "आधीच्या उपसंचांच्या युतीकरणात मूळ स्रोत चालू निर्देशांक पुन्हा वापरतो. "
    "मराठीत युतीकरणाचा योग्य चल निर्देशांक वापरला आहे आणि शून्यवे प्रकरण वेगळे केले आहे. "
    "गणनीय युतीकरणाच्या पुराव्यात गणनीय निवड पुरेशी आहे; या विभागात उलटी सममूल्यता "
    "सिद्ध केलेली नाही, हेही स्पष्ट केले आहे.\n"
    + r"\paragraph{निवडसंच आणि प्रतिमा.} "
    "प्रत्येक सदस्याशी एकघटकी छेद असण्याच्या अटीत बाहेरील अतिरिक्त घटकांना बंदी नाही. "
    "निवडफलनाची प्रतिमा म्हणून ओळखण्याआधी ते अतिरिक्त घटक वगळले आहेत.\n"
    + r"\paragraph{भूमितीय विधानांचे प्रांत.} "
    "बानाख--टार्स्कीचे घनगोल येथे धन त्रिज्येचे आणि त्रिमितीय आहेत; "
    "वितालीची वर्तुळे धन त्रिज्येची आहेत. पृष्ठभागाच्या विघटनातून पृष्ठभागाच्या प्रती मिळतात, "
    "घन अंतर्भागाच्या नव्हेत. अंतरालावरील स्पर्शरेषा-फलनाच्या सूत्रातील अतिरिक्त बंद कंस काढला आहे.\n"
    + r"\paragraph{वितालीच्या घूर्णन गटाची दुरुस्ती.} "
    "परिमेय संख्येइतक्या रेडियनांची घूर्णने पूर्ण फेरीच्या मर्यादेत घेतल्यास "
    "व्यस्त आणि संयोजनासाठी संवरण मिळत नाही. म्हणून पूर्ण फेरीच्या परिमेय भागांची "
    "घूर्णने घेतली आहेत. शून्य घूर्णनाचा व्यस्त स्वतंत्रपणे हाताळला आहे. "
    "दोन अर्ध्यांना स्वतंत्र आधार म्हणण्याऐवजी जनक संच म्हटले आहे; प्रत्येक अर्ध्यावरील "
    "कोन-दुप्पट प्रतिचित्रण एकास-एक आणि आच्छादक असते. विभाजनातील अपरिभाषित पहिल्या-अर्ध्याचे "
    "नावही योग्य गटाच्या नावाने बदलले आहे.\n"
    + r"\paragraph{त्रिमितीय रूपरेषेतील उरलेली पुरावा-उणीव.} "
    "मूळ मजकूर प्रत्येक मुक्त गटासाठी दुप्पट विघटन सांगतो; "
    "येथे प्रत्यक्ष वापरलेले दोन जनकांवरील मुक्त गटाचे प्रकरण म्हटले आहे. "
    "पण त्रिमितीय घूर्णने त्यांच्या अक्षांवरील काही बिंदू स्थिर ठेवतात. "
    "वर्तुळावरील मुक्त क्रियेचा पुरावा त्या बिंदूंना थेट लागू होत नाही. "
    "त्यांचा स्वतंत्र विचार या रूपरेषेत दिलेला नाही; म्हणून ही पूर्ण पुरावा नसल्याची "
    "उणीव स्पष्ट ठेवली आहे.\n"
    + r"\paragraph{मापाच्या पुराव्यातील क्षेत्र आणि चल.} "
    "माप ऋणेतर असल्याची आवश्यक अट आणि अमापनीयता ही निश्चित मापाच्या क्षेत्राविषयी "
    "असल्याचा अर्थ स्पष्ट केला आहे. शेवटच्या पुराव्यात घूर्णनाचा चल चुकून "
    "निवडलेल्या बिंदूंच्या संचात घेतला होता; तो घूर्णन गटात घेतला आहे.\n"
)
out = before + "\n".join(chunks) + "\n" + marker + note_body + editorial + "\n" + bib_marker + bibliography
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = re.sub(r"\\readerexternalref\{([^{}]+)::chap\}",
    lambda m: r"\ref{" + m.group(1) + ":chap}"
    if m.group(1) + ":chap" in available else m.group(0), out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[591:600]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 597 and inputs[-1]["unit_id"] == "OLP-0600"
assert out.count(r"\chapter{") == 66
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 517
assert "597 स्रोत-एकके आणि 517 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
assert out.count(r"\end{document}") == 1 and out.rstrip().endswith(r"\end{document}")
assert out.index(r"\paragraph{त्रिमितीय रूपरेषेतील उरलेली पुरावा-उणीव.}") < out.index(bib_marker)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="597 source units, 517 reader sections, sixty-six complete chapters",
    external_reference_labels=sorted(set(re.findall(r"\\readerexternalref\{([^}]+)\}", out))),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0592"])
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 517, "chapters": 66, "external_references": len(prior["external_reference_labels"]),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
