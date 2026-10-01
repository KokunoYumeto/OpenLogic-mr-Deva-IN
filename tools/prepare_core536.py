"""Assemble 58 complete Marathi chapters through OLP-0536 without TeX."""
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core528.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("सत्तावन्न संपूर्ण प्रकरणे") == 1
base = base.replace("सत्तावन्न संपूर्ण प्रकरणे", "अठ्ठावन्न संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0528, एकूण 525 स्रोत-एकके आणि 455 वाचक-विभाग. उर्वरित 197"
new = "OLP-0004 ते OLP-0536, एकूण 533 स्रोत-एकके आणि 461 वाचक-विभाग. उर्वरित 189"
assert base.count(old) == 1
base = base.replace(old, new, 1)
assert base.count("प्रतिवास्तविक विधाने या प्रकरणांचे आहे") == 1
base = base.replace(
    "प्रतिवास्तविक विधाने या प्रकरणांचे आहे",
    "प्रतिवास्तविक विधाने आणि संच उपपत्ती यांवरील प्रकरणांचे आहे", 1
)
assert base.count("प्रतिवास्तविक विधाने},pdfauthor") == 1
base = base.replace(
    "प्रतिवास्तविक विधाने},pdfauthor",
    "प्रतिवास्तविक विधाने आणि संच उपपत्ती},pdfauthor", 1
)
anchor = r"\newcommand{\cif}{\boxright}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" +
    r"\newtheorem{axiom}[defn]{स्वयंसिद्धक}" + "\n" +
    r"\newcommand{\stagesord}{\emph{टप्प्यांचा क्रम}}" + "\n" +
    r"\newcommand{\fregeext}[2]{\epsilon #1\, #2}", 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]
folder = ROOT / "mr/content/set-theory/story"
driver = selected((folder / "story.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{story}{संचांची क्रमिक संकल्पना}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "extensionality", "russells-paradox-again", "predicativity",
    "cumulative-approach", "urelements", "grundgesetze"
]
available.update({"sth:::part", "sth:part", "sth:story:chap"})
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "story", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [
    r"\part{संच उपपत्ती}\label{sth:::part}\label{sth:part}",
    r"\chapter{संचांची क्रमिक संकल्पना}\label{sth:story:chap}"
]
cites = {
    r"\citet[pp.~124--8]{Heijenoort1967}": "van Heijenoort (1967, पृ.~124--8)",
    r"\citep[p.~37]{WhiteheadRussell1910}": "(Whitehead आणि Russell, 1910, पृ.~37)",
    r"\citeauthor{Ramsey1925}": "रॅम्झी",
    r"\citep{Ramsey1925}": "(Ramsey, 1925)",
    r"\citet{Linnebo2010}": "Linnebo (2010)",
    r"\citep[p.~323]{Shoenfield:AST}": "(Shoenfield, 1977, पृ.~323)",
    r"\citep[p.~8]{Kunen1980}": "(Kunen, 1980, पृ.~8)",
    r"\citet[pp.\ 8--9]{Heck2012}": "Heck (2012, पृ.~8--9)",
}
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\Olref\{([^}]+)\}",
        lambda m: r"\ref{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}",
        lambda m: " आणि ".join(r"\ref{" + x.strip() + "}" for x in m.group(1).split(",")),
        content)
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references, content, flags=re.S)
    for original, projection in cites.items():
        content = content.replace(original, projection)
    content = re.sub(
        r"\\citealt\[pp\.~vi,\s*24,\s*50--1\]\{Potter2004\}",
        "Potter (2004, पृ.~vi, 24, 50--1)", content
    )
    assert not re.search(r"\\cite(?:p|t|alt|author|year)?(?:\[[^]]*\])?\{", content)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref)", content
    )
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(marker) == 1
before, notes = base.split(marker, 1)
notes = marker + notes
new_notes = r"""
\item \textbf{OLINC-243}: स्वसमावेशकतेवरील चर्चेत
रसेल संचाचे घटक वर्णन करताना मूळ इंग्रजीत
चुकून दुहेरी निषेध आला आहे. सूत्रानुसार
स्वतःचे सदस्य नसलेले संच अभिप्रेत आहेत;
मराठी गद्यात तेच स्पष्ट केले आहे.
\item \textbf{OLINC-244}: दुष्टचक्र तत्त्व
नाकारण्यानंतर मर्यादित संचरचनेची गरज येते,
असे मूळ गद्य उलटे म्हणते. उद्धृत तत्त्व
आणि पुढील युक्तिवादानुसार ते स्वीकारल्यावर
मर्यादा येते, असे मराठीत दुरुस्त केले आहे.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_notes + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0),
    out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
        .read_text(encoding="utf-8").splitlines() if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[528:536]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
    })
assert len(inputs) == 533 and inputs[-1]["unit_id"] == "OLP-0536"
assert out.count(r"\chapter{") == 58
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 461
assert "533 स्रोत-एकके आणि 461 वाचक-विभाग" in out
assert "OLINC-244" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="533 source units, 461 reader sections, fifty-eight complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + ["OLINC-243", "OLINC-244"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0529", "OLP-0530"]
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs), "sections": 461, "chapters": 58,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest()
}, ensure_ascii=False))
