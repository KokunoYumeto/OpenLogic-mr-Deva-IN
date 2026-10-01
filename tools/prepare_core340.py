"""Assemble 34 complete Marathi chapters through OLP-0340 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core335.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("तेहतीस संपूर्ण प्रकरणे") == 1
base = base.replace("तेहतीस संपूर्ण प्रकरणे", "चौतीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0335, एकूण 332 स्रोत-एकके "
    "आणि 292 वाचक-विभाग. उर्वरित 390"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0340, एकूण 337 स्रोत-एकके "
    "आणि 296 वाचक-विभाग. उर्वरित 385"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/second-order-logic/sol-and-set-theory"
driver = selected((folder / "sol-and-set-theory.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sol}{set}{द्वितीय-क्रम तर्कशास्त्र आणि संचसिद्धान्त}" in driver
chapter_note = re.search(
    r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S
)
assert chapter_note
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "comparing-sets",
    "cardinalities",
    "power-of-continuum",
]
chapter_label = "sol:set:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.groups()[:2] == ("sol", "set"), path
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
    r"\chapter{द्वितीय-क्रम तर्कशास्त्र आणि संचसिद्धान्त}\label{"
    + chapter_label
    + "}",
    replace_tokens(chapter_note.group()),
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = re.sub(
        r"!!(?:\^?a|\^)?\{bijective\}",
        "एकास-एक व आच्छादक",
        content,
    )
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
\item \textbf{OLINC-066--OLINC-072}: द्वितीय-क्रम
संचसिद्धान्तावरील मूळ प्रकरण स्वतःच निष्कर्षांत दोष
असू शकतात अशी सूचना देते. उपसंचांच्या अनंतता,
गणनीयता आणि अलेफ-एक यांसाठीची काही मूळ सूत्रे
अपेक्षित गुणधर्म व्यक्त करत नव्हती. मराठी सूत्रांत
\textbf{SOL6-A096--SOL6-A098} या दुरुस्त्या केल्या आहेत:
एकास-एक अट संबंधित उपसंचापुरती घेतली आहे; अनंतता,
गणनीयता आणि अलेफ-एक यांच्या अटी दुरुस्त केल्या आहेत;
सांतत्याचे सांकेतीकरण आणि पूर्ण प्रांताचे आकारमान
त्यांनुसार दुरुस्त केले आहे. निवडीसह संचसिद्धान्ताचा
आधी स्पष्ट केलेला संदर्भ लागू आहे. मूळ इंग्रजी बाइट्स
आणि ऐतिहासिक दोषनोंदी जतन आहेत.
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
for row in manifest[335:340]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 337 and inputs[-1]["unit_id"] == "OLP-0340"
assert out.count(r"\chapter{") == 34
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 296
assert "337 स्रोत-एकके आणि 296 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="337 source units, 296 reader sections, thirty-four complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(66, 73)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0336"],
    reader_token_projection={
        **prior.get("reader_token_projection", {}),
        "bijective": "एकास-एक व आच्छादक",
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
            "sections": 296,
            "chapters": 34,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
