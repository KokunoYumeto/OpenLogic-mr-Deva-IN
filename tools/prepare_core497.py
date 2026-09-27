"""Assemble 52 complete Marathi chapters through OLP-0497 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core490.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("एक्कावन्न संपूर्ण प्रकरणे") == 1
base = base.replace("एक्कावन्न संपूर्ण प्रकरणे", "बावन्न संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0490, एकूण 487 स्रोत-एकके "
    "आणि 425 वाचक-विभाग. उर्वरित 235"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0497, एकूण 494 स्रोत-एकके "
    "आणि 430 वाचक-विभाग. उर्वरित 228"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
old_subtitle = "आणि सामान्य मोडल तर्कशास्त्र\\par}"
new_subtitle = "आणि सामान्य व उपयोजित मोडल तर्कशास्त्रे, तसेच अंतःप्रज्ञावादी तर्कशास्त्र\\par}"
assert base.count(old_subtitle) == 1
base = base.replace(old_subtitle, new_subtitle, 1)
old_description = "आणि सामान्य मोडल तर्कशास्त्र या प्रकरणांचे आहे:"
new_description = "आणि सामान्य व उपयोजित मोडल तर्कशास्त्रे, तसेच अंतःप्रज्ञावादी तर्कशास्त्र या प्रकरणांचे आहे:"
assert base.count(old_description) == 1
base = base.replace(old_description, new_description, 1)
old_metadata = "आणि सामान्य मोडल तर्कशास्त्र, तसेच उपयोजित मोडल तर्कशास्त्र},pdfauthor="
new_metadata = "सामान्य व उपयोजित मोडल तर्कशास्त्रे आणि अंतःप्रज्ञावादी तर्कशास्त्र},pdfauthor="
assert base.count(old_metadata) == 1
base = base.replace(old_metadata, new_metadata, 1)

selected_modal = prior_namespace["selected_modal"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

part_path = ROOT / "mr/content/intuitionistic-logic/intuitionistic-logic.tex"
part = selected_modal(part_path.read_text(encoding="utf-8"))
assert r"\olpart{int}{अंतःप्रज्ञावादी तर्कशास्त्र}" in part
folder = ROOT / "mr/content/intuitionistic-logic/introduction"
driver = selected_modal((folder / "introduction.tex").read_text(encoding="utf-8"))
assert r"\olchapter{int}{int}{प्रस्तावना}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "constructive-reasoning",
    "syntax",
    "bhk-interpretation",
    "natural-deduction",
    "axiomatic-derivations",
]
available.update({"int:part", "int:int:chap"})
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected_modal(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["int", "int"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

chunks = [
    r"\part{अंतःप्रज्ञावादी तर्कशास्त्र}\label{int:part}",
    r"\chapter{प्रस्तावना}\label{int:int:chap}",
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = replace_tokens(content)
    if name == "constructive-reasoning":
        heading = r"\section{रचनाशील तर्कविचार}"
        assert content.count(heading) == 1
        content = content.replace(heading, heading + r"\label{" + prefix + ":sec}", 1)
    else:
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
new_note = r"""
\item \textbf{OLINC-214}: BHK उदाहरणातील फलनाच्या
फलप्रदेशात मूळ इंग्रजीत एका ठिकाणी \(C\) आले
आहे; सूत्रानुसार मराठीत \(!C\) वापरले आहे.
\item \textbf{OLINC-215}: विकल्पयोगाच्या डाव्या
समावेशनात मूळ इंग्रजीत \(M_1\) चे प्रतिमान
\(\langle 1,M_2\rangle\) दिले आहे. योग्य
\(\langle 1,M_1\rangle\) मराठीत वापरले आहे.
\item \textbf{OLINC-216}: संयोगाच्या BHK स्पष्टीकरणात
मूळ इंग्रजीत \(!A_1\land !A_1\) आले आहे;
जोडीचा दुसरा घटक \(!A_2\) ची रचना असल्याने
मराठीत \(!A_1\land !A_2\) वापरले आहे.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
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
for row in manifest[490:497]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 494 and inputs[-1]["unit_id"] == "OLP-0497"
assert out.count(r"\chapter{") == 52
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 430
assert "494 स्रोत-एकके आणि 430 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="494 source units, 430 reader sections, fifty-two complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [
        "OLINC-214", "OLINC-215", "OLINC-216"
    ],
    part_driver_units_not_rendered_as_sections=prior.get(
        "part_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0491"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0492"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 430,
    "chapters": 52,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
