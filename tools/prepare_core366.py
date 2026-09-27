"""Assemble 36 complete Marathi chapters through OLP-0366 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core355.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("पस्तीस संपूर्ण प्रकरणे") == 1
base = base.replace("पस्तीस संपूर्ण प्रकरणे", "छत्तीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0355, एकूण 352 स्रोत-एकके "
    "आणि 309 वाचक-विभाग. उर्वरित 370"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0366, एकूण 363 स्रोत-एकके "
    "आणि 319 वाचक-विभाग. उर्वरित 359"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

macro_marker = r"\newcommand{\eqs}{\equiv}"
assert base.count(macro_marker) == 1
base = base.replace(
    macro_marker,
    macro_marker
    + "\n"
    + r"""
\newcommand{\FV}[1]{\mathrm{FV}(#1)}
\NewDocumentCommand{\rep}{m o}{%
  \IfNoValueTF{#2}{\underline{#1}}{{\underline{#1}}_{#2}}}
\newcommand{\aconvone}{\redone[\alpha]}
\newcommand{\aconv}{\red[\alpha]}
\newcommand{\aeq}{\equal[\alpha]}
\newcommand{\bred}{\red[\beta]}
\newcommand{\eredone}{\redone[\eta]}
\newcommand{\bered}{\red[\beta\eta]}
\newcommand{\ext}{\ensuremath{\mathit{ext}}}
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

folder = ROOT / "mr/content/lambda-calculus/syntax"
driver = selected((folder / "syntax.tex").read_text(encoding="utf-8"))
assert r"\olchapter{lam}{syn}{विन्यासमीमांसा}" in driver
imports = re.findall(r"\olimport\{([^}]+)\}", driver)
assert imports == [
    "terms",
    "unique-readability",
    "abbreviated-syntax",
    "free-variables",
    "substitution",
    "alpha",
    "de-bruijn",
    "term-revisited",
    "beta",
    "eta",
]
chapter_label = "lam:syn:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.group(1) == "lam", path
    parts = list(file_id.groups())
    if name == "beta":
        assert parts == ["lam", "int", "bet"], path
    else:
        assert parts[:2] == ["lam", "syn"], path
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(
        prefix + ":" + item
        for item in re.findall(r"\ollabel\{([^}]+)\}", content)
    )
    available.update(re.findall(r"\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{विन्यासमीमांसा}\label{" + chapter_label + "}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(
        r"\ollabel\{([^}]+)\}",
        lambda match: r"\label{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(
        r"\olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda match: references(match, parts),
        content,
    )
    content = re.sub(
        r"\Olref\{([^}]+)\}",
        lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(
        r"\(?:c|C)ref\{([^}]+)\}",
        lambda match: " आणि ".join(
            r"\ref{" + item.strip() + "}" for item in match.group(1).split(",")
        ),
        content,
    )
    content = re.sub(
        r"\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references,
        content,
        flags=re.S,
    )
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
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
\item \textbf{OLINC-082--OLINC-102}: लॅम्डा पदांच्या
विन्यासमीमांसेतील एकमेव वाचनीयता, मुक्त चर, आदेशन,
अल्फा-परिवर्तन, सममूल्यतावर्ग आणि ईटा नियम यांमधील
गोठवलेल्या इंग्रजी स्रोताच्या स्थानिक त्रुटी स्वतंत्र
स्रोत-नोंदीत नोंदवल्या आहेत. गणिती अर्थ स्पष्ट करणाऱ्या
मराठी दुरुस्त्या तिथे नेमक्या ओळखता येतात; मूळ इंग्रजी
बाइट्स बदललेले नाहीत. अल्फा-परिवर्तनाचा सरावातील
दोन सारख्या प्रश्नजोड्या स्रोताप्रमाणे राखल्या आहेत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = re.sub(
    r"\readerexternalref\{([^}]+)\}",
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
for row in manifest[355:366]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 363 and inputs[-1]["unit_id"] == "OLP-0366"
assert out.count(r"\chapter{") == 36
assert len(re.findall(r"\section(?:\[[^]]*\])?\{", out)) == 319
assert "363 स्रोत-एकके आणि 319 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="363 source units, 319 reader sections, thirty-six complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(82, 103)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0356"],
    reader_file_id_exceptions={
        **prior.get("reader_file_id_exceptions", {}),
        "OLP-0365": "lam/int/bet (frozen source identifier retained in syntax chapter)",
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
            "sections": 319,
            "chapters": 36,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
