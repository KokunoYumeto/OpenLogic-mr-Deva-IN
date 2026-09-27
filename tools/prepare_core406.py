"""Assemble 42 complete Marathi chapters through OLP-0406 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core401.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("एक्केचाळीस संपूर्ण प्रकरणे") == 1
base = base.replace("एक्केचाळीस संपूर्ण प्रकरणे", "बेचाळीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0401, एकूण 398 स्रोत-एकके "
    "आणि 348 वाचक-विभाग. उर्वरित 324"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0406, एकूण 403 स्रोत-एकके "
    "आणि 352 वाचक-विभाग. उर्वरित 319"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

rotating_marker = r"\usepackage{flafter}"
assert base.count(rotating_marker) == 1
base = base.replace(rotating_marker, rotating_marker + "\n" + r"\usepackage{rotating}", 1)
sequent_marker = r"\newcommand{\Sequent}{\Rightarrow}"
assert base.count(sequent_marker) == 1
new_rule_macros = "\n".join(
    [
        r"\newcommand{\nSequent}{\mid}",
        r"\NewDocumentCommand{\iR}{m m o}{\ensuremath{{#1\IfNoValueTF{#3}{}{_{#3}}}{#2}}}",
    ]
)
assert "\\newcommand{\\nSequent}" not in base
assert "\\NewDocumentCommand{\\iR}" not in base
base = base.replace(sequent_marker, sequent_marker + "\n" + new_rule_macros, 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/many-valued-logic/sequent-calculus"
driver = selected((folder / "sequent-calculus.tex").read_text(encoding="utf-8"))
assert r"\olchapter{mvl}{seq}{क्रमवर्ती कलन}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "rules-and-proofs",
    "structural-rules",
    "propositional-rules",
]
available.add("mvl:seq:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["mvl", "seq"], path
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

chunks = [r"\chapter{क्रमवर्ती कलन}\label{mvl:seq:chap}"]
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
\item \textbf{OLINC-143--OLINC-145}: क्रमवर्ती कलनाच्या
गोठवलेल्या इंग्रजी मजकुरात डाव्या बाजूच्या सूत्रांची संख्या
क्रमवर्ती आणि संबंधित संधी यांत विसंगत आहे; एका
मूल्यनात मूल्यांकनाचा निर्देशांक गाळला आहे; आणि
$n$-बाजूंच्या क्रमवर्तीच्या प्रत्येक घटकाऐवजी फक्त
पहिल्या घटकाचा निर्देशांक लिहिला आहे. मराठी आवृत्तीत
या तीन गणिती नोंदी दुरुस्त केल्या आहेत. मूळ इंग्रजी
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
for row in manifest[401:406]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 403 and inputs[-1]["unit_id"] == "OLP-0406"
assert out.count(r"\chapter{") == 42
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 352
assert "403 स्रोत-एकके आणि 352 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="403 source units, 352 reader sections, forty-two complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(143, 146)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0402"],
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 352,
            "chapters": 42,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
