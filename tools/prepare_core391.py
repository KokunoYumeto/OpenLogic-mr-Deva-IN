"""Assemble 39 complete Marathi chapters through OLP-0391 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core382.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("अडतीस संपूर्ण प्रकरणे") == 1
base = base.replace("अडतीस संपूर्ण प्रकरणे", "एकोणचाळीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0382, एकूण 379 स्रोत-एकके "
    "आणि 333 वाचक-विभाग. उर्वरित 343"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0391, एकूण 388 स्रोत-एकके "
    "आणि 340 वाचक-विभाग. उर्वरित 334"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

old_metadata = "आणि द्वितीय-क्रम तर्कशास्त्र आणि लॅम्डा कलन"
assert base.count(old_metadata) == 3
base = base.replace(old_metadata, "आणि द्वितीय-क्रम तर्कशास्त्र, लॅम्डा कलन आणि बहुमूल्य तर्कशास्त्र")

# The older reader only needed unparameterized propositional operations.
# Match the upstream optional logic parameter while accepting both source
# notational orders, \pValue{v}(A)[L] and \pValue v[L](A).
old_pvalue = r"\NewDocumentCommand{\pValue}{m d()}{\overline{\pAssign{#1}}\IfNoValueF{#2}{(#2)}}"
new_pvalue = (
    r"\NewDocumentCommand{\pValue}{m o d() o}{%" + "\n"
    r"  \overline{\pAssign{#1}}%" + "\n"
    r"  \IfNoValueTF{#2}{\IfNoValueF{#4}{_{#4}}}{_{#2}}%" + "\n"
    r"  \IfNoValueF{#3}{(#3)}}"
)
assert base.count(old_pvalue) == 1
base = base.replace(old_pvalue, new_pvalue, 1)

old_psat = r"\NewDocumentCommand{\pSat}{t{/} m m}{\pAssign{#2}\IfBooleanTF{#1}{\nvDash}{\vDash}#3}"
new_psat = (
    r"\NewDocumentCommand{\pSat}{t{/} m m o}{%" + "\n"
    r"  \pAssign{#2}\IfBooleanTF{#1}{\nvDash}{\vDash}%" + "\n"
    r"  \IfNoValueF{#4}{_{#4}}#3}"
)
assert base.count(old_psat) == 1
base = base.replace(old_psat, new_psat, 1)
tf_definition = (
    r"\NewDocumentCommand{\tf}{m o}{%" + "\n"
    r"  \widetilde{#1}\IfNoValueF{#2}{_{#2}}}"
)
assert "\\NewDocumentCommand{\\tf}" not in base
base = base.replace(new_psat, new_psat + "\n" + tf_definition, 1)
logcl_definition = r"\newcommand{\LogCL}{\Log{C}}"
log_marker = r"\NewDocumentCommand{\Log}{m o}{%"
assert base.count(log_marker) == 1
log_end = r"\ensuremath{\mathbf{#1}\IfNoValueF{#2}{_{#2}}}}"
assert base.count(log_end) == 1
base = base.replace(log_end, log_end + "\n" + logcl_definition, 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

part_path = ROOT / "mr/content/many-valued-logic/many-valued-logic.tex"
part = selected(part_path.read_text(encoding="utf-8"))
assert r"\olpart{mvl}{बहुमूल्य तर्कशास्त्र}" in part
part_editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", part, re.S)
assert part_editorial, "Preserve the draft-status note of the part"

folder = ROOT / "mr/content/many-valued-logic/syntax-and-semantics"
driver = selected((folder / "syntax-and-semantics.tex").read_text(encoding="utf-8"))
assert r"\olchapter{mvl}{syn}{विन्यासमीमांसा आणि चिन्हार्थमीमांसा}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "connectives",
    "formulas",
    "matrices",
    "valuations-sat",
    "semantic-notions",
    "sublogics",
]
available.add("mvl:part")
available.add("mvl:syn:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["mvl", "syn"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(
        prefix + ":" + item
        for item in re.findall(r"\\ollabel\{([^}]+)\}", content)
    )
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

chunks = [
    r"\part{बहुमूल्य तर्कशास्त्र}\label{mvl:part}",
    part_editorial.group(),
    r"\chapter{विन्यासमीमांसा आणि चिन्हार्थमीमांसा}\label{mvl:syn:chap}",
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    if name == "sublogics":
        long_title = r"\section{अभिजात तर्कशास्त्र~$\LogCL$ ची उपतर्कशास्त्रे म्हणून बहुमूल्य तर्कशास्त्रे}"
        short_title = (
            r"\section[अभिजात तर्कशास्त्राची उपतर्कशास्त्रे]"
            r"{अभिजात तर्कशास्त्र~$\LogCL$ ची उपतर्कशास्त्रे म्हणून बहुमूल्य तर्कशास्त्रे}"
        )
        assert content.count(long_title) == 1
        content = content.replace(long_title, short_title, 1)
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
\item \textbf{OLINC-129--OLINC-131}: बहुमूल्य तर्कशास्त्रातील
अभिजात तुलनेच्या गोठवलेल्या इंग्रजी प्रमेयाची व्याप्ती
अतिविस्तृत आहे आणि अंतिम सिद्धतेत पूर्तीऐवजी निष्पन्नतेची
चिन्हे चुकून वापरली आहेत. मराठी आवृत्तीत विधान सामाईक
चार-संयोजक खंडापुरते स्पष्ट केले आहे, सर्व विधानीय चलांसाठी
अभिजात मूल्यांची अट नमूद केली आहे आणि प्रत्युदाहरणातील
पूर्तीची चिन्हे दुरुस्त केली आहेत. मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
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
for row in manifest[382:391]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 388 and inputs[-1]["unit_id"] == "OLP-0391"
assert out.count(r"\chapter{") == 39
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 340
assert "388 स्रोत-एकके आणि 340 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="388 source units, 340 reader sections, thirty-nine complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + ["OLINC-129", "OLINC-130", "OLINC-131"],
    part_driver_units_not_rendered_as_sections=prior.get(
        "part_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0383"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0384"],
    reader_heading_projection="Math-bearing section headings retain displayed mathematics; TOC, bookmarks and running heads use text-only short titles for Q, ω, PA and the classical-logic comparison.",
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 340,
            "chapters": 39,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
