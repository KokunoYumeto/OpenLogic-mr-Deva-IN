"""Assemble 29 complete Marathi chapters through OLP-0300 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core279.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("सत्तावीस संपूर्ण प्रकरणे") == 1
base = base.replace("सत्तावीस संपूर्ण प्रकरणे", "एकोणतीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0279, एकूण 276 स्रोत-एकके "
    "आणि 243 वाचक-विभाग. उर्वरित 446"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0300, एकूण 297 स्रोत-एकके "
    "आणि 262 वाचक-विभाग. उर्वरित 425"
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
replace_tokens.__globals__["singular"].update(
    {
        "discharge": "मुक्त",
        "discharged": "मुक्त केलेले",
        "undischarged": "मुक्त न केलेले",
    }
)

chapters = [
    (
        "art",
        "विन्यासमीमांसेचे अंकगणितीकरण",
        "arithmetization-syntax",
        "arithmetization-syntax",
        [
            "introduction",
            "coding-symbols",
            "coding-terms",
            "coding-formulas",
            "substitution",
            "proofs-in-lk",
            "proofs-in-nd",
            "proofs-in-ax",
        ],
    ),
    (
        "req",
        r"$\Th{Q}$ मधील निरूपणीयता",
        "representability-in-q",
        "representability-in-q",
        [
            "introduction",
            "representable-comp",
            "beta-function",
            "prim-rec",
            "basic-representable",
            "composition-representable",
            "minimization-representable",
            "comp-representable",
            "representing-relations",
            "undecidability",
            "sigma1-completeness",
        ],
    ),
]

chapter_data = []
for chapter_key, title, directory, driver_name, expected_imports in chapters:
    folder = ROOT / "mr" / "content" / "incompleteness" / directory
    driver = (folder / (driver_name + ".tex")).read_text(encoding="utf-8")
    assert r"\olchapter{inc}{" + chapter_key + "}{" in driver
    imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
    assert imports == expected_imports, (directory, imports)
    chapter_label = f"inc:{chapter_key}::chap"
    available.add(chapter_label)
    files = []
    for name in imports:
        path = folder / (name + ".tex")
        content = selected(path.read_text(encoding="utf-8"))
        file_id = re.search(
            r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content
        )
        assert file_id, path
        frozen_file_id_exception = (
            directory == "representability-in-q"
            and name == "sigma1-completeness"
            and file_id.groups() == ("inc", "inp", "s1c")
        )
        assert (
            file_id.groups()[:2] == ("inc", chapter_key)
            or frozen_file_id_exception
        ), path
        parts = list(file_id.groups())
        prefix = ":".join(parts)
        available.add(prefix + ":sec")
        available.update(
            prefix + ":" + item
            for item in re.findall(r"\\ollabel\{([^}]+)\}", content)
        )
        available.update(re.findall(r"\\label\{([^}]+)\}", content))
        files.append((name, content, parts, prefix))
    chapter_data.append((title, chapter_label, driver, files))
external.difference_update(available)


def convert_section(content, prefix):
    starts = list(re.finditer(r"\\olsection(?:\[[^]]*\])?\{", content))
    assert len(starts) == 1, (prefix, len(starts))
    start = starts[0]
    at = start.end()
    depth = 1
    while depth:
        assert at < len(content), prefix
        if content[at] == "{" and content[at - 1] != "\\":
            depth += 1
        elif content[at] == "}" and content[at - 1] != "\\":
            depth -= 1
        at += 1
    title = content[start.end() : at - 1]
    return (
        content[: start.start()]
        + r"\section{"
        + title
        + r"}\label{"
        + prefix
        + ":sec}"
        + content[at:]
    )


chunks = []
section_count = 0
for title, chapter_label, driver, files in chapter_data:
    chunks.append(r"\chapter{" + title + r"}\label{" + chapter_label + "}")
    editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
    if editorial:
        chunks.append(replace_tokens(editorial.group()))
    for name, raw, parts, prefix in files:
        content = strip_wrapper(raw)
        content, removed = re.subn(
            r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
        )
        assert removed == 1, (chapter_label, name)
        content = replace_tokens(content)
        content = convert_section(content, prefix)
        section_count += 1
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

assert section_count == 19
notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_note = r"""
\item \textbf{OLINC-006--OLINC-043}: विन्यासमीमांसेच्या
अंकगणितीकरणात आणि $Q$ मधील निरूपणीयतेत मूळ इंग्रजीतील
सूत्रे, संख्यांकांचे निर्देश, सिद्धतापायऱ्या व गृहीतके
यांबद्दलची स्रोत-निरीक्षणे स्वतंत्र नोंदवली आहेत.
संबंधित मराठी विभागांत त्यांची मर्यादित दुरुस्ती
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
    .replace("!T", r"\mathsf{T}")
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
for row in manifest[279:300]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 297 and inputs[-1]["unit_id"] == "OLP-0300"
assert out.count(r"\chapter{") == 29
assert out.count(r"\section{") == 262
assert "297 स्रोत-एकके आणि 262 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCDQT]", out)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="297 source units, 262 reader sections, twenty-nine complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(6, 44)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0280", "OLP-0289"],
    reader_symbol_projections={
        **prior.get("reader_symbol_projections", {}),
        "!T": r"\mathsf{T}",
        "!Q": r"\mathsf{Q}",
    },
    reader_file_id_exceptions={
        **prior.get("reader_file_id_exceptions", {}),
        "OLP-0300": "inc/inp/s1c (frozen source identifier retained)",
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
            "sections": 262,
            "chapters": 29,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
