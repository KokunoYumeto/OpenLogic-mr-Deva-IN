"""Assemble 30 complete Marathi chapters through OLP-0311 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core300.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("एकोणतीस संपूर्ण प्रकरणे") == 1
base = base.replace("एकोणतीस संपूर्ण प्रकरणे", "तीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0300, एकूण 297 स्रोत-एकके "
    "आणि 262 वाचक-विभाग. उर्वरित 425"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0311, एकूण 308 स्रोत-एकके "
    "आणि 272 वाचक-विभाग. उर्वरित 414"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
reader_macros = r"""
\NewDocumentCommand{\scode}{m}{\fn{c}_{#1}}
\NewDocumentCommand{\Gn}{m}{{^{\reflectbox{\tiny\#}}}{#1}{^{\mbox{\tiny\#}}}}
\NewDocumentCommand{\Prf}{o}{\mathrm{Prf}\IfNoValueF{#1}{_{#1}}}
\newcommand{\openTuple}{\langle}
\newcommand{\closeTuple}{\rangle}
\DeclareMathOperator\lcm{\mathrm{lcm}}
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", reader_macros + r"\begin{document}", 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/incompleteness/theories-computability"
driver = selected((folder / "theories-computability.tex").read_text(encoding="utf-8"))
assert r"\olchapter{inc}{tcp}{" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "q-is-ce",
    "oconsis-ext-of-q-undec",
    "extensions-of-q-not-decidable",
    "computably-axiomatizable",
    "complete-decidable",
    "first-incompleteness",
    "inseparability",
    "consis-with-q",
    "interpretability",
]
chapter_label = "inc:tcp:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.groups()[:2] == ("inc", "tcp"), path
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

chunks = [r"\chapter{उपपत्ती आणि संगणनक्षमता}\label{" + chapter_label + "}"]
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert editorial
chunks.append(replace_tokens(editorial.group()))
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
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
        short = " ".join(
            title.replace(r"$\Th{Q}$", "Q").replace(r"$\omega$", "ओमेगा").split()
        )
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
\item \textbf{OLINC-044--OLINC-054}: उपपत्ती आणि संगणनक्षमता या
प्रकरणातील मूळ इंग्रजीतील सूत्रे, गृहीतकांची व्याप्ती आणि
प्रतिमानातील सत्य यांबद्दलची स्रोत-निरीक्षणे स्वतंत्र नोंदवली
आहेत. संबंधित मराठी विभागांत त्यांची मर्यादित दुरुस्ती
किंवा स्पष्टता दिली आहे; मूळ इंग्रजी बाइट्स बदललेले नाहीत.
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
for row in manifest[300:311]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 308 and inputs[-1]["unit_id"] == "OLP-0311"
assert out.count(r"\chapter{") == 30
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 272
assert "308 स्रोत-एकके आणि 272 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCDEQT]", out)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="308 source units, 272 reader sections, thirty complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(44, 55)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0301"],
    reader_symbol_projections={
        **prior.get("reader_symbol_projections", {}),
        "!E": r"\mathsf{E}",
    },
    reader_heading_projection=(
        "Math-bearing section titles in OLP-0303, 0304, 0305, 0308, "
        "0309, 0310 and 0311 retain their displayed title; the table of "
        "contents, PDF bookmarks and running heads spell Q and omega as text."
    ),
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 272,
            "chapters": 30,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
