"""Assemble the 24 complete Marathi chapters through OLP-0251 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
legacy = runpy.run_path(str(ROOT / "tools" / "prepare_core194.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

old_scope = (
    "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, "
    "विधानीय तर्कशास्त्र, चार सिद्धता-पद्धती, संपूर्णता, प्रथम-क्रम "
    "विन्यासमीमांसा व चिन्हार्थमीमांसा, प्रतिमाने व उपपत्ती आणि प्रतिमान उपपत्ती"
)
new_scope = (
    "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, "
    "प्रतिमान उपपत्ती आणि संगणनक्षमता"
)
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
assert base.count("वीस संपूर्ण प्रकरणे") == 1
base = base.replace("वीस संपूर्ण प्रकरणे", "चोवीस संपूर्ण प्रकरणे")
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0197, एकूण 194 स्रोत-एकके "
    "आणि 171 वाचक-विभाग. उर्वरित 528"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0251, एकूण 248 स्रोत-एकके "
    "आणि 220 वाचक-विभाग. उर्वरित 474"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage)
model_class_macro = r"""
\usetikzlibrary{arrows,positioning}
\NewDocumentCommand{\Mod}{o d() m}{%
  \IfNoValueTF{#2}{%
    \IfNoValueTF{#1}{\mathrm{Mod}(#3)}{\mathrm{Mod}^{\Lang{#1}}(#3)}}{%
    \IfNoValueTF{#1}{\mathrm{Mod}_{#2}(#3)}{\mathrm{Mod}_{#2}^{\Lang{#1}}(#3)}}}
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", model_class_macro + r"\begin{document}", 1)

selected = legacy["selected"]
replace_tokens = legacy["replace_reader_tokens"]
strip_wrapper = legacy["strip_wrapper"]
legacy["singular"].update({"c.e.": "संगणनक्षमपणे प्रगणनीय", "computably enumerable": "संगणनक्षमपणे प्रगणनीय"})
available = set(legacy["available"])
external = set(prior.get("external_reference_labels", []))

chapters = [
    ("mod", "int", "अंतर्वेशन प्रमेय", "model-theory/interpolation", "interpolation"),
    ("mod", "lin", "लिंडस्ट्रॉमचे प्रमेय", "model-theory/lindstrom", "lindstrom"),
    ("cmp", "rec", "पुनरावर्ती फलने", "computability/recursive-functions", "recursive-functions"),
    ("cmp", "thy", "संगणनक्षमतेचा सिद्धांत", "computability/computability-theory", "computability-theory"),
]
chapter_data = []
for part, key, title, directory, driver_name in chapters:
    folder = ROOT / "mr" / "content" / directory
    driver = selected((folder / (driver_name + ".tex")).read_text(encoding="utf-8"))
    imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
    assert imports, driver_name
    chapter_label = f"{part}:{key}::chap"
    available.add(chapter_label)
    files = []
    for name in imports:
        path = folder / (name + ".tex")
        content = selected(path.read_text(encoding="utf-8"))
        file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
        assert file_id and file_id.groups()[:2] == (part, key), path
        parts = list(file_id.groups())
        prefix = ":".join(parts)
        available.add(prefix + ":sec")
        available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
        available.update(re.findall(r"\\label\{([^}]+)\}", content))
        files.append((name, content, parts, prefix))
    chapter_data.append((title, chapter_label, driver, files))


def references(match, parts):
    options = re.findall(r"\[([^]]*)\]", match.group(1))
    assert len(options) <= 3
    key_parts = parts.copy()
    if options:
        key_parts[3 - len(options) :] = options
    label = ":".join(key_parts) + ":" + match.group(2)
    if label in available:
        return r"\ref{" + label + "}"
    external.add(label)
    return r"\readerexternalref{" + label + "}"


def tag_references(match):
    pairs = re.findall(r"([^,{}\s]+)/\{([^{}]+)\}", match.group(1))
    labels = [label for _, label in pairs if label in available]
    if labels:
        return ", ".join(r"\ref{" + label + "}" for label in labels)
    external.update(label for _, label in pairs)
    return r"\readerexternalref{tagrefs}"


chunks = []
section_count = 0
for title, chapter_label, driver, files in chapter_data:
    chunks.append(r"\chapter{" + title + r"}\label{" + chapter_label + "}")
    editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
    if editorial:
        chunks.append(replace_tokens(editorial.group()))
    for name, raw, parts, prefix in files:
        content = strip_wrapper(raw)
        content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
        assert removed == 1, (chapter_label, name)
        content = replace_tokens(content)
        content, converted = re.subn(
            r"\\olsection(?:\[[^]]*\])?\{([^{}]*)\}",
            lambda m: r"\section{" + m.group(1) + r"}\label{" + prefix + ":sec}",
            content,
        )
        if not converted:
            content, converted = re.subn(
                r"\\section\{([^{}]*)\}",
                lambda m: r"\section{" + m.group(1) + r"}\label{" + prefix + ":sec}",
                content,
                count=1,
            )
        assert converted == 1, (chapter_label, name, converted)
        section_count += 1
        content = re.sub(r"\\ollabel\{([^}]+)\}", lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
        content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", lambda m: references(m, parts), content)
        content = re.sub(r"\\Olref\{([^}]+)\}", lambda m: r"\ref{" + prefix + ":" + m.group(1) + "}", content)
        content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}", lambda m: " आणि ".join(r"\ref{" + item.strip() + "}" for item in m.group(1).split(",")), content)
        content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tag_references, content, flags=re.S)
        assert "!!" not in content, (chapter_label, name, re.findall(r"!!.{0,35}", content)[:8])
        leftover = re.search(
            r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
            r"usetoken|printtoken|Article|article|olref|Olref|ollabel|olsection|olfileid|tagrefs|Cref|cref)",
            content,
        )
        assert not leftover, (chapter_label, name, leftover.group(0) if leftover else "")
        chunks.append(content)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_notes = r"""
\item \textbf{OLCMP-001--OLCMP-024}: संगणनक्षमता प्रकरणांतील औपचारिक
मांडणी, चिन्हांकने आणि सिद्धतापायऱ्यांबद्दलच्या स्रोत-निरीक्षणांची संरेखित
स्रोतांत स्वतंत्र नोंद आहे. मूळ इंग्रजी बाइट्स जतन आहेत; मराठी वाचक-मजकूर
नोंदवलेल्या मर्यादित स्पष्टता आणि दुरुस्त्या वापरतो.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_notes + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = (
    out.replace(r"\formula{A}", r"\varphi")
    .replace(r"\formula{B}", r"\psi")
    .replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
)
for letter in "EFGHS":
    out = out.replace("!" + letter, r"\varphi_{" + letter + "}")
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[197:251]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 248 and inputs[-1]["unit_id"] == "OLP-0251"
assert section_count == 49, section_count
assert out.count(r"\chapter{") == 24
assert out.count(r"\section{") == 220
assert "248 स्रोत-एकके आणि 220 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCD]", out)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="248 source units, 220 reader sections, twenty-four complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [f"OLCMP-{i:03d}" for i in range(1, 25)],
    part_driver_units_not_rendered_as_sections=prior.get("part_driver_units_not_rendered_as_sections", []) + ["OLP-0208"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs), "sections": 220, "chapters": 24, "external_references": len(external), "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
