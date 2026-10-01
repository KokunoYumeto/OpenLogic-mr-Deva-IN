"""Assemble 62 complete Marathi chapters through OLP-0573 without TeX."""
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core564.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("एकसष्ट संपूर्ण प्रकरणे") == 1
base = base.replace("एकसष्ट संपूर्ण प्रकरणे", "बासष्ट संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0564, एकूण 561 स्रोत-एकके आणि 486 वाचक-विभाग. उर्वरित 161"
new = "OLP-0004 ते OLP-0573, एकूण 570 स्रोत-एकके आणि 494 वाचक-विभाग. उर्वरित 152"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\newcommand{\ZFminus}{\ZF^{-}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + "\n".join([
    r"\newcommand{\LT}{\Th{LT}}",
    r"\newcommand{\Zr}{\Th{Zr}}",
    r"\newcommand{\limofsize}{\emph{आकारमानाच्या मर्यादेचे तत्त्व}}",
    r"\newcommand{\stagesinex}{\emph{टप्पे निरपेक्षपणे अनंत आहेत}}",
    r"\newcommand{\stagescofin}{\emph{टप्पे संचांपलीकडे जातात}}",
]), 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]

folder = ROOT / "mr/content/set-theory/replacement"
driver = selected((folder / "replacement.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{replacement}{प्रतिस्थापन}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["introduction", "strength", "extrinsic", "limofsize",
                  "absinf", "ref", "refproofs", "finiteaxiomatizability"]
available.add("sth:replacement:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "replacement", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

citations = {
    ("citeauthor", "", "Maddy1988a"): "मॅडी",
    ("citeyear", "", "Maddy1988a"): "1988a",
    ("citeyear", "", "Maddy1988b"): "1988b",
    ("citep", "229", "Boolos1971"): "(बूलोस 1971, पृ.~229)",
    ("citet", "", "Montague1965"): "मॉन्टेग्यू (1965)",
    ("citet", "", "Scott1974"): "स्कॉट (1974)",
    ("citet", "", "Potter2004"): "पॉटर (2004)",
    ("citet", "", "ButtonLT1"): "बटन (2021)",
    ("citealt", "", "Potter2004"): "पॉटर (2004)",
    ("citealt", "", "ButtonLT1"): "बटन (2021)",
    ("citealt", r"\S13.2", "Potter2004"): r"पॉटर (2004, \S13.2)",
    ("citeyearpar", "p.~19", "Boolos1989"): "(1989, पृ.~19)",
    ("citet", r"\S13.2", "Potter2004"): r"पॉटर (2004, \S13.2)",
    ("cite", "", "Shoenfield:AST"): "शोनफेल्ड (1977)",
    ("citet", "p.~223", "Potter2004"): "पॉटर (2004, पृ.~223)",
    ("citeauthor", "", "Shoenfield:AST"): "शोनफेल्ड",
    ("citet", "90--5", "Incurvati2020"): "इनकुर्वाती (2020, पृ.~90--95)",
    ("citet", "", "Montague1961"): "मॉन्टेग्यू (1961)",
    ("citet", "", "Levy1960"): "लेव्ही (1960)",
    ("citet", "95--100", "Incurvati2020"): "इनकुर्वाती (2020, पृ.~95--100)",
    ("citet", "first part of Theorem 2", "Levy1960"): "लेव्ही (1960, प्रमेय 2 चा पहिला भाग)",
    ("citet", "प्रमेय 2 चा पहिला भाग", "Levy1960"): "लेव्ही (1960, प्रमेय 2 चा पहिला भाग)",
    ("citet", "Theorem 6", "Levy1960"): "लेव्ही (1960, प्रमेय 6)",
    ("citet", "प्रमेय 6", "Levy1960"): "लेव्ही (1960, प्रमेय 6)",
    ("citet", "223", "Potter2004"): "पॉटर (2004, पृ.~223)",
}

def localize_citation(match):
    kind = match.group(1)
    option = " ".join((match.group(2) or "").split())
    key = match.group(3)
    return citations[(kind, option, key)]

chunks = [r"\chapter{प्रतिस्थापन}\label{sth:replacement:chap}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = content.replace("!!{element}s", "सदस्य")
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\Olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}",
        lambda m: " आणि ".join(r"\ref{" + x.strip() + "}" for x in m.group(1).split(",")), content)
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references, content, flags=re.S)
    content = re.sub(r"\\crefrange\{sth:ordinals::chap\}\{sth:spine::chap\}",
        r"\\ref{sth:ordinals:chap}--\\ref{sth:spine:chap}", content)
    content = re.sub(r"\\crefrange\{sth:story::chap\}\{sth:z::chap\}",
        r"\\ref{sth:story:chap}--\\ref{sth:z:chap}", content)
    content = re.sub(r"\\(cite\w*)(?:\[([^]]*)\])?\{([^}]+)\}",
        localize_citation, content, flags=re.S)
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
editorial = (
    "\n" + r"\paragraph{प्रतिबिंबनाच्या पुराव्यातील सूत्रदुरुस्त्या.} "
    "मूळ इंग्रजीत साक्षीदार-टप्प्याच्या अटीत एक अतिरिक्त बंद कंस आणि "
    "$\\bigcup_{m<\\omega}S_n$ मध्ये निर्देशांक-विसंगती आहे; मराठी सूत्रे "
    "अनुक्रमे संतुलित कंस आणि $S_m$ वापरतात. प्रतिस्थापनाच्या प्रतिबिंबनाधारित "
    "पुराव्यातील प्रतिमा-संचाच्या अटीचा हरवलेला बंद कंसही पुरवला आहे.\n"
    + r"\paragraph{दुर्बल प्रतिबिंबनाचे नाव आणि सापेक्षीकरण.} "
    "मूळ मजकूर दुर्बल प्रतिबिंबनाची व्याख्या करण्याआधी चुकून प्रतिस्थापनाचे "
    "दुर्बल रूप म्हणतो; मराठी मांडणीत प्रतिबिंबन म्हटले आहे. पुढील परिशिष्टात "
    "$(\\exists N\\,\\psi(N))^M$ उलगडताना संक्रमकतेच्या अटीवरील "
    "चुकीचे $N$ अधिलेख $M$ केले आहे.\n"
    + r"\paragraph{विभक्तीकरणाविषयी मूळ पुराव्यातील त्रुटी.} "
    "सांत विस्ताराच्या पुराव्यात आणि त्यानंतरच्या प्रश्नात प्रत्येक संक्रमक "
    "संच विभक्तीकरणाचे प्रत्येक सापेक्षीकृत उदाहरण पूर्ण करतो, असा दावा आहे. "
    "तो खोटा आहे: $X=3=\\{0,1,2\\}$ हा संक्रमक संच घ्या. $A=2\\in X$ "
    "आणि $x=1$ निवडणारी अट घेतल्यास अपेक्षित $\\{1\\}\\notin X$. "
    "मराठी पुराव्यात आता लघुतम संक्रमक व उपसंच-समावेशक प्रतिमान "
    "वापरले आहे; प्रश्नाच्या विधानातही आवश्यक उपसंच-समावेशकत्वाची "
    "अट दिली आहे. प्रश्नाची सिद्धता वाचकांसाठी ठेवली आहे.\n"
)
out = before + "\n".join(chunks) + "\n" + marker + notes + editorial
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = out.replace(r"\readerexternalref{sth:replacement::chap}", r"\ref{sth:replacement:chap}")
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[564:573]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 570 and inputs[-1]["unit_id"] == "OLP-0573"
assert out.count(r"\chapter{") == 62
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 494
assert "570 स्रोत-एकके आणि 494 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="570 source units, 494 reader sections, sixty-two complete chapters",
    external_reference_labels=sorted(external),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0565"])
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 494, "chapters": 62, "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
