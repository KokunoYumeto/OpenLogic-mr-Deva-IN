"""Assemble 31 complete Marathi chapters through OLP-0321 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core311.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("तीस संपूर्ण प्रकरणे") == 1
base = base.replace("तीस संपूर्ण प्रकरणे", "एकतीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0311, एकूण 308 स्रोत-एकके "
    "आणि 272 वाचक-विभाग. उर्वरित 414"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0321, एकूण 318 स्रोत-एकके "
    "आणि 281 वाचक-विभाग. उर्वरित 404"
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

folder = ROOT / "mr/content/incompleteness/incompleteness-provability"
driver = selected((folder / "incompleteness-provability.tex").read_text(encoding="utf-8"))
assert r"\olchapter{inc}{inp}{अपूर्णता आणि सिद्धतायोग्यता}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "fixed-point-lemma",
    "first-incompleteness-thm",
    "rosser-thm",
    "godels-paper",
    "provability-conditions",
    "second-incompleteness-thm",
    "lob-thm",
    "tarski-thm",
]
chapter_label = "inc:inp:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.groups()[:2] == ("inc", "inp"), path
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

chunks = [r"\chapter{अपूर्णता आणि सिद्धतायोग्यता}\label{" + chapter_label + "}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    for token, word in {
        "axiomatizable": "स्वयंसिद्धकीकरणीय",
        "axiomatized": "स्वयंसिद्धकीकृत",
        "decidable": "निर्णेय",
    }.items():
        content = re.sub(
            r"!!(?:\^?a|\^)?\{" + token + r"\}",
            word,
            content,
        )
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    heading = re.search(r"\\section\{", content)
    assert heading, name
    at = heading.end()
    depth = 1
    while depth:
        assert at < len(content), name
        if content[at] == "{" and content[at - 1] != "\\":
            depth += 1
        elif content[at] == "}" and content[at - 1] != "\\":
            depth -= 1
        at += 1
    title = content[heading.end() : at - 1]
    if "$" in title:
        short = " ".join(title.replace(r"$\Th{PA}$", "PA").split())
        assert "$" not in short and "\\" not in short, (name, short)
        content = (
            content[: heading.start()]
            + r"\section["
            + short
            + "]{"
            + title
            + "}"
            + content[at:]
        )
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
            r"\ref{" + item.strip() + "}"
            for item in match.group(1).split(",")
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
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_note = r"""
\item \textbf{OLINC-055--OLINC-059}: अपूर्णता आणि सिद्धतायोग्यता
या प्रकरणातील मूळ इंग्रजीत वस्तुभाषेतील सिद्धतायोग्यता
विधेय, गोडेल-वाक्याचा संकेतनांक आणि सुसंगततेचे सूत्र
यांमध्ये आढळलेल्या विसंगती स्वतंत्र नोंदवल्या आहेत.
मराठी आवृत्तीत संबंधित सूत्रांची मर्यादित दुरुस्ती
केली आहे; मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = (
    out.replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
    .replace("!E", r"\mathsf{E}")
    .replace("!G", r"\mathsf{G}")
    .replace("!H", r"\mathsf{H}")
    .replace("!Q", r"\mathsf{Q}")
)
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
for row in manifest[311:321]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 318 and inputs[-1]["unit_id"] == "OLP-0321"
assert out.count(r"\chapter{") == 31
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 281
assert "318 स्रोत-एकके आणि 281 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCDEGQT]", out)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="318 source units, 281 reader sections, thirty-one complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(55, 60)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0312"],
    reader_symbol_projections={
        **prior.get("reader_symbol_projections", {}),
        "!G": r"\mathsf{G}",
        "!H": r"\mathsf{H}",
    },
    reader_heading_projection=(
        "Math-bearing section headings from previous chapters and OLP-0318 "
        "retain their displayed mathematics; TOC, bookmarks and running heads "
        "use text-only short titles for Q, ω and PA."
    ),
    reader_token_projection={
        **prior.get("reader_token_projection", {}),
        "axiomatizable": "स्वयंसिद्धकीकरणीय",
        "axiomatized": "स्वयंसिद्धकीकृत",
        "decidable": "निर्णेय",
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
            "sections": 281,
            "chapters": 31,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
