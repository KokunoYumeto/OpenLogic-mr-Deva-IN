"""Assemble 43 complete Marathi chapters through OLP-0418 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core406.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("बेचाळीस संपूर्ण प्रकरणे") == 1
base = base.replace("बेचाळीस संपूर्ण प्रकरणे", "त्रेचाळीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0406, एकूण 403 स्रोत-एकके "
    "आणि 352 वाचक-विभाग. उर्वरित 319"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0418, एकूण 415 स्रोत-एकके "
    "आणि 362 वाचक-विभाग. उर्वरित 307"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
old_subjects = "लॅम्डा कलन आणि बहुमूल्य तर्कशास्त्र"
new_subjects = "लॅम्डा कलन, बहुमूल्य तर्कशास्त्र आणि सामान्य मोडल तर्कशास्त्र"
assert base.count(old_subjects) == 3
base = base.replace(old_subjects, new_subjects)

modal_macros = r"""
\newcommand{\mClass}[1]{\mathcal{#1}}
\newcommand{\mTrue}[1]{\ensuremath{#1}}
\newcommand{\mFalse}[1]{\ensuremath{\lnot #1}}
\NewDocumentCommand{\Ax}{m}{\ensuremath{\mathrm{#1}}}
\newcommand{\Dual}{\textsc{dual}}
\tikzset{
  modal/.style={>=stealth',shorten >=1pt,shorten <=1pt,auto,
    node distance=1.5cm,label distance=2pt,semithick},
  every label/.style={phantom,align=left},
  world/.style={circle,draw,minimum size=0.5cm,fill=gray!15},
  modal every node/.style={world},
  point/.style={circle,draw,inner sep=0.5mm,fill=black},
  phantom/.style={rectangle,inner sep=0pt,draw=none,fill=none},
  reflexive above/.style={->,loop,looseness=7,in=60,out=120},
  reflexive below/.style={->,loop,looseness=7,in=240,out=300},
  reflexive left/.style={->,loop,looseness=7,in=150,out=210},
  reflexive right/.style={->,loop,looseness=7,in=30,out=330}
}
"""
assert base.count(r"\begin{document}") == 1
for command in (r"\mClass", r"\mTrue", r"\mFalse", r"\Ax", r"\Dual"):
    assert command not in base.split(r"\begin{document}", 1)[0], command
base = base.replace(r"\begin{document}", modal_macros + r"\begin{document}", 1)

selected = prior_namespace["selected"]
true_tags = selected.__globals__["true_tags"]
true_tags.update({"prvBox", "prvDiamond"})
# The final selector delegates to the older tag parser, whose globals retain
# the original tag set rather than the copy made by prepare_core194.
selected.__globals__["selected_base"].__globals__["select_tags"].__globals__[
    "true_tags"
].update({"prvBox", "prvDiamond"})
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]


def select_probtag(text):
    pattern = re.compile(r"\\begin\{probtag\}\{([^}]*)\}(.*?)\\end\{probtag\}", re.S)
    while pattern.search(text):
        text = pattern.sub(
            lambda match: (
                r"\begin{prob}" + match.group(2) + r"\end{prob}"
                if match.group(1) in true_tags
                else ""
            ),
            text,
            count=1,
        )
    return text


def selected_modal(text):
    return selected(select_probtag(text))


part_path = ROOT / "mr/content/normal-modal-logic/normal-modal-logic.tex"
part = selected_modal(part_path.read_text(encoding="utf-8"))
assert r"\olpart{nml}{सामान्य मोडल तर्कशास्त्रे}" in part
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", part, re.S)
assert editorial

folder = ROOT / "mr/content/normal-modal-logic/syntax-and-semantics"
driver = selected_modal((folder / "syntax-and-semantics.tex").read_text(encoding="utf-8"))
assert r"\olchapter{nml}{syn}{विन्यासमीमांसा आणि चिन्हार्थमीमांसा}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "language-modal-logic",
    "substitution",
    "relational-models",
    "truth-at-w",
    "truth-in-model",
    "modal-validity",
    "tautological-instances",
    "schemas",
    "entailment",
]
available.update({"nml:part", "nml:syn:chap"})
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected_modal(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["nml", "syn"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(
        prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content)
    )
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

chunks = [
    r"\part{सामान्य मोडल तर्कशास्त्रे}\label{nml:part}",
    replace_tokens(editorial.group()),
    r"\chapter{विन्यासमीमांसा आणि चिन्हार्थमीमांसा}\label{nml:syn:chap}",
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda match: r"\label{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(
        r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda match: references(match, parts),
        content,
    )
    content = re.sub(
        r"\\Olref\{([^}]+)\}",
        lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(
        r"\\(?:c|C)ref\{([^}]+)\}",
        lambda match: " आणि ".join(
            r"\ref{" + item.strip() + "}" for item in match.group(1).split(",")
        ),
        content,
    )
    content = re.sub(
        r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references,
        content,
        flags=re.S,
    )
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref)",
        content,
    )
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(notes_marker) == 1
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_note = r"""
\item \textbf{OLINC-146--OLINC-153}: सामान्य मोडल
तर्कशास्त्रातील जगनिरपेक्ष अनिवार्यता, परिकर्मीची
कंसजोडी, द्विपक्षीय अभिव्यंजनाचा निवडक संकेत,
पूर्तीतील जगाचा निर्देशांक, आदेशन-दृष्टांतांची विगमन
सिद्धता आणि प्रतिमानाचे क्रमित त्रिक या ठिकाणी
गोठवलेल्या इंग्रजी स्रोताच्या मर्यादित दुरुस्त्या
मराठी मजकुरात नोंदल्या आहेत. मूळ इंग्रजी बाइट्स
बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(
    r"\\readerexternalref\{([^}]+)\}",
    lambda match: (
        r"\ref{" + match.group(1) + "}"
        if match.group(1) in available
        else match.group(0)
    ),
    out,
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[406:418]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 415 and inputs[-1]["unit_id"] == "OLP-0418"
assert out.count(r"\chapter{") == 43
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 362
assert "415 स्रोत-एकके आणि 362 वाचक-विभाग" in out
assert "!!" not in out
assert not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="415 source units, 362 reader sections, forty-three complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(146, 154)],
    part_driver_units_not_rendered_as_sections=prior.get(
        "part_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0407"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0408"],
)
prior["tag_profile"]["true"] = sorted(true_tags)
prior["tag_profile"]["false"] = sorted(
    set(prior["tag_profile"]["false"]) | {"probDiamond"}
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 362,
            "chapters": 43,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
