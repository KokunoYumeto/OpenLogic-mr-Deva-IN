"""Assemble 37 complete Marathi chapters through OLP-0372 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core366.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("छत्तीस संपूर्ण प्रकरणे") == 1
base = base.replace("छत्तीस संपूर्ण प्रकरणे", "सदतीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0366, एकूण 363 स्रोत-एकके "
    "आणि 319 वाचक-विभाग. उर्वरित 359"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0372, एकूण 369 स्रोत-एकके "
    "आणि 324 वाचक-विभाग. उर्वरित 353"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

macro_marker = r"\newcommand{\ext}{\ensuremath{\mathit{ext}}}"
assert base.count(macro_marker) == 1
base = base.replace(
    macro_marker,
    macro_marker
    + "\n"
    + r"""
\newcommand{\xredone}{\redone[X]}
\newcommand{\xred}{\red[X]}
\newcommand{\beredone}{\redone[\beta\eta]}
\NewDocumentCommand{\redpar}{o}{%
  \IfNoValueTF{#1}{\Longrightarrow}{\mathrel{\stackrel{#1}{\Longrightarrow}}}}
\newcommand{\bredpar}{\redpar[\beta]}
\newcommand{\beredpar}{\redpar[\beta\eta]}
\newcommand{\bcd}[1]{{#1}^{*{\beta}}}
\newcommand{\becd}[1]{{#1}^{*{\beta\eta}}}
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

folder = ROOT / "mr/content/lambda-calculus/church-rosser"
driver = selected((folder / "church-rosser.tex").read_text(encoding="utf-8"))
assert r"\olchapter{lam}{cr}{चर्च–रॉसर गुणधर्म}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "definitions-and-properties",
    "parallel-beta-reduction",
    "beta-reduction",
    "parallel-beta-eta-reduction",
    "beta-eta-reduction",
]
chapter_label = "lam:cr:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.group(1) == "lam", path
    parts = list(file_id.groups())
    assert parts[:2] == ["lam", "cr"], path
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(
        prefix + ":" + item
        for item in re.findall(r"\\ollabel\{([^}]+)\}", content)
    )
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{चर्च–रॉसर गुणधर्म}\label{" + chapter_label + "}"]
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
\item \textbf{OLINC-103--OLINC-113}: चर्च–रॉसर प्रकरणातील
गोठवलेल्या इंग्रजी स्रोताच्या स्थानिक सूत्रचिन्ह, नियम,
चल आणि सिद्धता-अंतराच्या नोंदी स्वतंत्र स्रोत-नोंदीत
आहेत. दुरुस्त्या मराठी आवृत्तीत स्पष्ट केल्या आहेत;
बीटा–ईटा पूर्ण विकासातील आच्छादन-प्रकरणांची उणीव
\textbf{SOL6-A126} मध्ये दुरुस्त केली आहे: मुख्य
दावा आणि साहाय्यक दावा एकत्रित रचनात्मक विगमनाने
सिद्ध केले आहेत. मूळ इंग्रजी बाइट्स
बदललेले नाहीत.
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
for row in manifest[366:372]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 369 and inputs[-1]["unit_id"] == "OLP-0372"
assert out.count(r"\chapter{") == 37
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 324
assert "369 स्रोत-एकके आणि 324 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="369 source units, 324 reader sections, thirty-seven complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(103, 114)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0367"],
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 324,
            "chapters": 37,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
