"""Assemble 51 complete Marathi chapters through OLP-0490 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core481.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("पन्नास संपूर्ण प्रकरणे") == 1
base = base.replace("पन्नास संपूर्ण प्रकरणे", "एक्कावन्न संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0481, एकूण 478 स्रोत-एकके "
    "आणि 417 वाचक-विभाग. उर्वरित 244"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0490, एकूण 487 स्रोत-एकके "
    "आणि 425 वाचक-विभाग. उर्वरित 235"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

for command in (r"\newcommand{\Taut}", r"\newcommand{\PL}", r"\newcommand{\RK}"):
    assert base.count(command) == 1
for command in ("Knows", "EKnows", "CKnows"):
    assert (r"\newcommand{\%s}" % command) not in base
epistemic_macros = "\n".join(
    r"\newcommand{\%s}{\mathord{\mathsf{%s}}}" % (command, symbol)
    for command, symbol in (("Knows", "K"), ("EKnows", "E"), ("CKnows", "C"))
)
assert r"\DeclareSymbolFont{symbolsC}" not in base
assert r"\DeclareMathSymbol{\fishhookright}" not in base
source_fishhook = (
    r"\DeclareSymbolFont{symbolsC}{U}{ntxsyc}{m}{n}" + "\n"
    + r"\DeclareMathSymbol{\fishhookright}{\mathbin}{symbolsC}{74}"
)
macro_anchor = r"\newcommand{\Until}{\mathord{\mathsf{U}}}"
assert base.count(macro_anchor) == 1
base = base.replace(macro_anchor, macro_anchor + "\n" + epistemic_macros + "\n" + source_fishhook, 1)

selected_modal = prior_namespace["selected_modal"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/applied-modal-logic/epistemic-logic"
driver = selected_modal((folder / "epistemic-logic.tex").read_text(encoding="utf-8"))
assert r"\olchapter{aml}{el}{ज्ञानविषयक तर्कशास्त्रे}" in driver
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert editorial
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "language-epistemic-logic",
    "relational-models",
    "truth-at-w",
    "properties-accessibility",
    "bisimulations",
    "public-announcement-logic-lang",
    "public-announcement-logic-semantics",
]
available.add("aml:el:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = path.read_text(encoding="utf-8")
    content = selected_modal(raw)
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["aml", "el"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

title = replace_tokens(r"ज्ञानविषयक तर्कशास्त्रे")
assert "!!" not in title and r"\usetoken" not in title
chunks = [
    r"\chapter{" + title + r"}\label{aml:el:chap}",
    replace_tokens(editorial.group()),
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}", lambda match: r"\label{" + prefix + ":" + match.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", lambda match: references(match, parts), content)
    content = re.sub(r"\\Olref\{([^}]+)\}", lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}", content)
    content = re.sub(
        r"\\(?:c|C)ref\{([^}]+)\}",
        lambda match: " आणि ".join(r"\ref{" + item.strip() + "}" for item in match.group(1).split(",")),
        content,
    )
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tag_references, content, flags=re.S)
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
assert notes.count(r"\end{enumerate}") >= 1
new_note = r"""
\item \textbf{OLINC-210}: मूळ इंग्रजी प्रस्तावनेत
\emph{Knowledge and Belief} या ग्रंथाच्या लेखकाचे
पहिले नाव ``Jaako'' असे आहे. विद्यापीठाच्या
ग्रंथसूचीनुसार योग्य स्पेलिंग ``Jaakko'' आहे;
मराठीत ``याक्को हिंटिक्का'' वापरले आहे.
\item \textbf{OLINC-211}: द्विअनुकरणाच्या ``पुढे'' आणि
``मागे'' या दोन्ही अटींमध्ये मूळ इंग्रजीत कर्त्यांचा
संच \(A\) आला आहे. प्रकरणात परिभाषित कर्तृचिन्हांचा
संच \(G\) असल्याने मराठी अटींमध्ये \(G\) वापरले आहे.
\item \textbf{OLINC-212}: सार्वजनिक घोषणा भाषेतील
संयोजकांच्या यादीत मूळ इंग्रजीत द्विसशर्त राहिला
आहे; त्याच विभागातील सूत्रनिर्मितीच्या नियमात तो
असल्याने मराठी यादीत समाविष्ट केला आहे.
\item \textbf{OLINC-213}: घोषणेच्या रिक्तपणे सत्य
असण्याच्या उदाहरणात मूळ इंग्रजीत उत्तरसूत्राचे
चिन्हांकन राहिले आहे. मराठीत व्याख्येनुसार
\([!A] !B\) हे रूप वापरले आहे.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(
    r"\\readerexternalref\{([^}]+)\}",
    lambda match: r"\ref{" + match.group(1) + "}" if match.group(1) in available else match.group(0),
    out,
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[481:490]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 487 and inputs[-1]["unit_id"] == "OLP-0490"
assert out.count(r"\chapter{") == 51
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 425
assert "487 स्रोत-एकके आणि 425 वाचक-विभाग" in out
assert "!!" not in out
assert not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="487 source units, 425 reader sections, fifty-one complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [
        "OLINC-210", "OLINC-211", "OLINC-212", "OLINC-213"
    ],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0482"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 425,
    "chapters": 51,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
