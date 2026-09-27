"""Assemble 35 complete Marathi chapters through OLP-0355 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core340.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("चौतीस संपूर्ण प्रकरणे") == 1
base = base.replace("चौतीस संपूर्ण प्रकरणे", "पस्तीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0340, एकूण 337 स्रोत-एकके "
    "आणि 296 वाचक-विभाग. उर्वरित 385"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0355, एकूण 352 स्रोत-एकके "
    "आणि 309 वाचक-विभाग. उर्वरित 370"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
old_topics = "आणि अपूर्णता आणि द्वितीय-क्रम तर्कशास्त्र"
new_topics = old_topics + " आणि लॅम्डा कलन"
assert base.count(old_topics) == 3
base = base.replace(old_topics, new_topics)
macro_marker = r"\newcommand{\num}[1]{\overline{#1}}"
assert base.count(macro_marker) == 1
base = base.replace(
    macro_marker,
    macro_marker
    + "\n"
    + r"""
\newtheorem{conv}[defn]{संकेतनरूढी}
\NewDocumentCommand{\redone}{o}{%
  \IfNoValueTF{#1}{\xrightarrow{}}{\xrightarrow{#1}}}
\NewDocumentCommand{\xrightarrowdbl}{o m}{%
  \IfNoValueTF{#1}
  {\xrightarrow{#2}\mathrel{\mkern-14mu}\rightarrow}
  {\xrightarrow[#1]{#2}\mathrel{\mkern-14mu}\rightarrow}}
\NewDocumentCommand{\red}{o}{%
  \IfNoValueTF{#1}{\xrightarrowdbl{}}{\xrightarrowdbl{#1}}}
\newcommand{\bredone}{\redone[\beta]}
\NewDocumentCommand{\equal}{o}{%
  \IfNoValueTF{#1}{\eq}{\stackrel{#1}{\eq}}}
\newcommand{\eqs}{\equiv}
""".rstrip(),
    1,
)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]


def project_lambda_tokens(text):
    replacements = {
        r"\usetoken{S}{lambda definable}": "लॅम्डा-परिभाष्य",
        "!!{lambda define}s": "लॅम्डा-परिभाषित करते",
        "!!{lambda defined}": "लॅम्डा-परिभाषित",
        "!!{lambda definable}": "लॅम्डा-परिभाष्य",
        "!!{lambda define}": "लॅम्डा-परिभाषित",
    }
    for frozen, marathi in replacements.items():
        text = text.replace(frozen, marathi)
    return text


part_path = ROOT / "mr/content/lambda-calculus/lambda-calculus.tex"
folder = ROOT / "mr/content/lambda-calculus/introduction"
part_driver = selected(part_path.read_text(encoding="utf-8"))
driver = selected((folder / "introduction.tex").read_text(encoding="utf-8"))
assert r"\olpart{lam}{लॅम्डा कलन}" in part_driver
assert r"\olchapter{lam}{int}{परिचय}" in driver
assert re.findall(r"\\olimport\[[^]]+\]\{([^}]+)\}", part_driver) == [
    "introduction",
    "syntax",
    "church-rosser",
    "lambda-definability",
]
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "overview",
    "syntax",
    "reduction",
    "church-rosser",
    "currying",
    "lambda-definability",
    "lambda-computable",
    "computable-lambda",
    "basic-pr-lambda",
    "composition",
    "primitive-recursion",
    "fixed-point-combinator",
    "minimization",
]
part_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", part_driver, re.S)
chapter_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert part_note and chapter_note

chapter_label = "lam:int:chap"
available.add("lam:part")
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.group(1) == "lam", path
    parts = list(file_id.groups())
    if name == "currying":
        assert parts == ["lam", "rep", "cur"], path
    else:
        assert parts[:2] == ["lam", "int"], path
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
    r"\part{लॅम्डा कलन}\label{lam:part}",
    replace_tokens(part_note.group()),
    r"\chapter{परिचय}\label{" + chapter_label + "}",
    replace_tokens(chapter_note.group()),
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = replace_tokens(project_lambda_tokens(content))
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
\item \textbf{OLINC-073--OLINC-081}: लॅम्डा कलनाच्या
परिचयात एका विभागाचा जुना प्रकरण-संकेत, करीकरणाच्या
अंतिम आदेशनातील चुकलेले पद, फलनाच्या स्थानसंख्येतील
विसंगती, आणि आदिम पुनरावर्तन व लघुतमीकरणाच्या
पुराव्यांतील स्थानिक त्रुटी नोंदवल्या आहेत. मराठी
मजकुरातील नेमक्या दुरुस्त्या व स्पष्टीकरणे स्रोत-नोंदीत
दर्शवली आहेत; मूळ इंग्रजी बाइट्स बदललेले नाहीत.
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
for row in manifest[340:355]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 352 and inputs[-1]["unit_id"] == "OLP-0355"
assert out.count(r"\chapter{") == 35
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 309
assert "352 स्रोत-एकके आणि 309 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="352 source units, 309 reader sections, thirty-five complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(73, 82)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0342"],
    part_driver_units_not_rendered_as_sections=prior.get(
        "part_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0341"],
    reader_file_id_exceptions={
        **prior.get("reader_file_id_exceptions", {}),
        "OLP-0347": "lam/rep/cur (frozen source identifier retained)",
    },
    reader_token_projection={
        **prior.get("reader_token_projection", {}),
        "lambda definable": "लॅम्डा-परिभाष्य",
        "lambda defined": "लॅम्डा-परिभाषित",
        "lambda define": "लॅम्डा-परिभाषित",
    },
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 309,
            "chapters": 35,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
