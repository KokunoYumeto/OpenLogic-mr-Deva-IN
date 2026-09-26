"""Assemble 32 complete Marathi chapters through OLP-0329 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core321.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("एकतीस संपूर्ण प्रकरणे") == 1
base = base.replace("एकतीस संपूर्ण प्रकरणे", "बत्तीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0321, एकूण 318 स्रोत-एकके "
    "आणि 281 वाचक-विभाग. उर्वरित 404"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0329, एकूण 326 स्रोत-एकके "
    "आणि 287 वाचक-विभाग. उर्वरित 396"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
old_scope = (
    "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, प्रतिमान उपपत्ती, "
    "संगणनक्षमता, ट्यूरिंग यंत्रे, अनिर्णेयता आणि अपूर्णता"
)
new_scope = old_scope + " आणि द्वितीय-क्रम तर्कशास्त्र"
assert base.count(old_scope) == 3
base = base.replace(old_scope, new_scope)
reader_macros = r"""
\DeclareDocumentCommand{\TrmSOL}{o}{
  \IfNoValueTF{#1}{\mathrm{Trm}^2}{\mathrm{Trm}^2({\Lang #1})}}
\DeclareDocumentCommand{\FrmSOL}{o}{
  \IfNoValueTF{#1}{\mathrm{Frm}^2}{\mathrm{Frm}^2({\Lang #1})}}
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", reader_macros + r"\begin{document}", 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

part = selected(
    (ROOT / "mr/content/second-order-logic/second-order-logic.tex")
    .read_text(encoding="utf-8")
)
assert r"\olpart{sol}{द्वितीय-क्रम तर्कशास्त्र}" in part
part_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", part, re.S)
assert part_note
folder = ROOT / "mr/content/second-order-logic/syntax-and-semantics"
driver = selected((folder / "syntax-and-semantics.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sol}{syn}{विन्यासमीमांसा आणि चिन्हार्थमीमांसा}" in driver
chapter_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert chapter_note
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "terms-formulas",
    "satisfaction",
    "semantic-notions",
    "expressive-power",
    "inf-count",
]
chapter_label = "sol:syn:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.groups()[:2] == ("sol", "syn"), path
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
    r"\part{द्वितीय-क्रम तर्कशास्त्र}",
    r"\chapter{विन्यासमीमांसा आणि चिन्हार्थमीमांसा}\label{" + chapter_label + "}",
    replace_tokens(part_note.group()),
    replace_tokens(chapter_note.group()),
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
        r"usetoken|printtoken|Article|article|olref|Olref|ollabel|"
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
\item \textbf{OLINC-060--OLINC-061}: द्वितीय-क्रम चिन्हार्थमीमांसेच्या
मूळ इंग्रजीत संक्रमणाविषयी वापरलेले $R^*$ हे चिन्ह आधीच्या प्रकरणातील
व्याख्येशी विसंगत आहे; मराठी आवृत्तीत सकारात्मक संक्रमणासाठी $R^+$
ठेवले आहे. मर्यादित संचाच्या गणनेविषयीच्या सिद्धतेत शेवटच्या घटकाचे
फलनमूल्य स्पष्ट केले आहे. दोन्ही मुद्दे स्वतंत्र स्रोत-नोंदींत नोंदले आहेत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = out.replace("!A", r"\varphi").replace("!B", r"\psi")
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
for row in manifest[321:329]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 326 and inputs[-1]["unit_id"] == "OLP-0329"
assert out.count(r"\chapter{") == 32
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 287
assert "326 स्रोत-एकके आणि 287 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCDEGHQR]", out)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="326 source units, 287 reader sections, thirty-two complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + ["OLINC-060", "OLINC-061"],
    part_driver_units_not_rendered_as_sections=prior.get(
        "part_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0322"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0323"],
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 287,
            "chapters": 32,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
