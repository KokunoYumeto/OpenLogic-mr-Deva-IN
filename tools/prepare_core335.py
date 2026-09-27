"""Assemble 33 complete Marathi chapters through OLP-0335 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core329.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("बत्तीस संपूर्ण प्रकरणे") == 1
base = base.replace("बत्तीस संपूर्ण प्रकरणे", "तेहतीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0329, एकूण 326 स्रोत-एकके "
    "आणि 287 वाचक-विभाग. उर्वरित 396"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0335, एकूण 332 स्रोत-एकके "
    "आणि 292 वाचक-विभाग. उर्वरित 390"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

# Two alternative reduction exercises carry the same frozen label. The
# cross-chapter reference uses the first; give the second a reader-only label.
duplicate_label = r"\label{sfr:siz:red:prob:nat-nat}"
assert base.count(duplicate_label) == 2
second_at = base.find(duplicate_label, base.find(duplicate_label) + 1)
base = (
    base[:second_at]
    + base[second_at:].replace(
        duplicate_label, r"\label{sfr:siz:red:prob:nat-nat-alt}", 1
    )
)
assert base.count(duplicate_label) == 1

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/second-order-logic/metatheory"
driver = selected((folder / "metatheory.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sol}{met}{द्वितीय-क्रम तर्कशास्त्राची अधिउपपत्ती}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "second-order-arithmetic",
    "undecidability-and-axiomatizability",
    "compactness",
    "loewenheim-skolem",
]
chapter_label = "sol:met:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.groups()[:2] == ("sol", "met"), path
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
    r"\chapter{द्वितीय-क्रम तर्कशास्त्राची अधिउपपत्ती}\label{"
    + chapter_label
    + "}"
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
\item \textbf{OLINC-062--OLINC-065}: द्वितीय-क्रम अंकगणितात
बेरीज परिभाषित करणाऱ्या सूत्रातील बांधलेला चल सुसंगत केला आहे.
स्वयंसिद्धकीकरणाच्या सिद्धतेतील तुटलेली गणित-सीमा दुरुस्त केली आहे.
संहततेच्या प्रमेयाला स्वतंत्र खूण दिली आहे आणि सांत उपसंचावरील
कमाल बंधाचा निर्देश त्या सांत उपसंचाकडेच केला आहे.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = out.replace("!A", r"\varphi").replace("!B", r"\psi").replace("!P", r"\mathsf{P}")
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
for row in manifest[329:335]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 332 and inputs[-1]["unit_id"] == "OLP-0335"
assert out.count(r"\chapter{") == 33
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 292
assert "332 स्रोत-एकके आणि 292 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABP]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="332 source units, 292 reader sections, thirty-three complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + ["OLINC-062", "OLINC-063", "OLINC-064", "OLINC-065"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0330"],
    reader_label_projection={
        "frozen_duplicate": "sfr:siz:red:prob:nat-nat",
        "second_occurrence": "sfr:siz:red:prob:nat-nat-alt",
        "reference_remains_on_first": True,
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
            "sections": 292,
            "chapters": 33,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
