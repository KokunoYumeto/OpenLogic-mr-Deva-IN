"""Assemble 40 complete Marathi chapters through OLP-0397 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core391.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("एकोणचाळीस संपूर्ण प्रकरणे") == 1
base = base.replace("एकोणचाळीस संपूर्ण प्रकरणे", "चाळीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0391, एकूण 388 स्रोत-एकके "
    "आणि 340 वाचक-विभाग. उर्वरित 334"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0397, एकूण 394 स्रोत-एकके "
    "आणि 345 वाचक-विभाग. उर्वरित 328"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

logcl_definition = r"\newcommand{\LogCL}{\Log{C}}"
assert base.count(logcl_definition) == 1
new_macros = "\n".join(
    [
        r"\newcommand{\Undef}{\ensuremath{\mathbb{U}}}",
        r"\newcommand{\LogLuk}{\Log{\textbf{\L}}}",
        r"\newcommand{\LogGod}{\Log{G}}",
        r"\newcommand{\LogKs}{\Log{Ks}}",
        r"\newcommand{\LogKw}{\Log{Kw}}",
        r"\newcommand{\LogLP}{\Log{LP}}",
        r"\newcommand{\LogRM}{\Log{RM}}",
        r"\newcommand{\LogHal}{\Log{Hal}}",
    ]
)
for macro in ("Undef", "LogLuk", "LogGod", "LogKs", "LogKw", "LogLP", "LogRM", "LogHal"):
    assert "\\newcommand{\\" + macro + "}" not in base
base = base.replace(logcl_definition, logcl_definition + "\n" + new_macros, 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/many-valued-logic/three-valued-logics"
driver = selected((folder / "three-valued-logics.tex").read_text(encoding="utf-8"))
assert r"\olchapter{mvl}{thr}{त्रिमूल्य तर्कशास्त्रे}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "lukasiewicz",
    "kleene",
    "goedel",
    "multiple-designation",
]
available.add("mvl:thr:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["mvl", "thr"], path
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
    r"\chapter{त्रिमूल्य तर्कशास्त्रे}\label{mvl:thr:chap}",
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    if name == "multiple-designation":
        long_title = r"\section{$\True$ व्यतिरिक्तही मूल्य निर्दिष्ट करणे}"
        short_title = r"\section[इतर सत्यतामूल्येही निर्दिष्ट करणे]{$\True$ व्यतिरिक्तही मूल्य निर्दिष्ट करणे}"
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
\item \textbf{OLINC-132--OLINC-137}: त्रिमूल्य तर्कशास्त्रांच्या
गोठवलेल्या इंग्रजी मजकुरात संधीच्या समानतेतील पुनरावृत्ती,
एका सरावातील अतिरिक्त कंस, आगमनाच्या आधारातील अटीविना
दिलेली समानता आणि संधीच्या पुराव्यात दुसऱ्या घटकाऐवजी
पहिलाच घटक पुन्हा लिहिलेला आहे. मराठी आवृत्तीत स्पष्ट
गणिती दुरुस्त्या नोंदवून केल्या आहेत. R-Mingle च्या
मॅट्रिक्समध्ये अतिरिक्त असत्य-स्थिरांकाचे मूल्य स्पष्ट
दिलेले नाही; हा प्रश्न खुला ठेवला आहे. मूळ इंग्रजी
बाइट्स बदललेले नाहीत.
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
for row in manifest[391:397]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 394 and inputs[-1]["unit_id"] == "OLP-0397"
assert out.count(r"\chapter{") == 40
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 345
assert "394 स्रोत-एकके आणि 345 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="394 source units, 345 reader sections, forty complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(132, 138)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0392"],
    reader_heading_projection="Math-bearing section headings retain displayed mathematics; TOC, bookmarks and running heads use text-only short titles for Q, ω, PA, the classical-logic comparison and the multiple-designation section.",
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 345,
            "chapters": 40,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
