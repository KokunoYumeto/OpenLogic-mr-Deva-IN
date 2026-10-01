"""Assemble 64 complete Marathi chapters through OLP-0585 without TeX."""
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core579.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

# The earlier reader's comment stripper left a paragraph break inside an
# align* environment after removing a nonrendered alternative equation.
bad_align_gap = "  \\alpha \\ordplus (\\beta \\ordplus  1)\n\n  &= \\ordtype{"
assert base.count(bad_align_gap) == 1
base = base.replace(bad_align_gap,
    "  \\alpha \\ordplus (\\beta \\ordplus  1)\n  &= \\ordtype{", 1)

assert base.count("त्रेसष्ट संपूर्ण प्रकरणे") == 1
base = base.replace("त्रेसष्ट संपूर्ण प्रकरणे", "चौसष्ट संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0579, एकूण 576 स्रोत-एकके आणि 499 वाचक-विभाग. उर्वरित 146"
new = "OLP-0004 ते OLP-0585, एकूण 582 स्रोत-एकके आणि 504 वाचक-विभाग. उर्वरित 140"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\newcommand{\rlexless}{\mathrel{\sphericalangle}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + "\n".join([
    r"\newcommand{\ZFC}{\Th{ZFC}}",
    r"\newcommand{\cardfont}[1]{\mathfrak{#1}}",
    r"\NewDocumentCommand{\fregenum}{m m}{\# #1\,#2}",
]), 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]

folder = ROOT / "mr/content/set-theory/cardinals"
driver = selected((folder / "cardinals.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{cardinals}{संचांक}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["cp", "cardsasords", "milestone", "classing", "hp"]
available.add("sth:cardinals:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "cardinals", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{संचांक}\label{sth:cardinals:chap}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = content.replace("!!{injection}", "एकास-एक फलन")
    content = content.replace("!!a{injection}", "एकास-एक फलन")
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
    for locator in (r"\citep[Pt.III Bk.1 \S1]{Hume1740}",
                    r"\citep[भाग III, पुस्तक 1, \S1]{Hume1740}"):
        content = content.replace(locator, r"(ह्यूम 1740, भाग III, पुस्तक 1, \S1)")
    content = content.replace(
        r"\citet[\S63]{Frege1884}", r"फ्रेगे (1884, \S63)")
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
    "\n" + r"\paragraph{सांततेच्या विधानातील अर्थदुरुस्ती.} "
    "मूळ इंग्रजीत $\\card{A}\\notin\\omega$ या अटीचा अर्थ चुकून "
    "“$A$ नैसर्गिक संख्या नाही” असा दिला आहे. सांत पण नैसर्गिक संख्या "
    "नसलेले संच असतात; म्हणून मराठीत “$A$ सांत नाही” असे म्हटले आहे.\n"
    + r"\paragraph{अनंत उत्तरवर्ती संख्येच्या पुराव्यातील मधला टप्पा.} "
    "मूळ पुरावा उत्तरवर्ती क्रमसूचक संख्या अनंत असल्यास तिची पूर्ववर्ती "
    "अनंत असते, यासाठी सांत क्रमसूचक संख्यांच्या तुल्यबलतेवरील प्रतिज्ञेचा "
    "संदर्भ देतो. तो संदर्भ एकटाच पुरेसा नाही. पूर्ववर्ती सांत असती "
    "तर तिची उत्तरवर्तीही सांत असती, हा आवश्यक टप्पा मराठीत स्पष्ट केला आहे.\n"
)
out = before + "\n".join(chunks) + "\n" + marker + notes + editorial
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
for row in manifest[579:585]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 582 and inputs[-1]["unit_id"] == "OLP-0585"
assert out.count(r"\chapter{") == 64
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 504
assert "582 स्रोत-एकके आणि 504 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="582 source units, 504 reader sections, sixty-four complete chapters",
    external_reference_labels=sorted(set(re.findall(
        r"\\readerexternalref\{([^}]+)\}", out))),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0580"])
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 504, "chapters": 64,
    "external_references": len(prior["external_reference_labels"]),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
