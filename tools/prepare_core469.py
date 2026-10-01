"""Assemble 48 complete Marathi chapters through OLP-0469 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core459.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("सत्तेचाळीस संपूर्ण प्रकरणे") == 1
base = base.replace("सत्तेचाळीस संपूर्ण प्रकरणे", "अठ्ठेचाळीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0459, एकूण 456 स्रोत-एकके "
    "आणि 399 वाचक-विभाग. उर्वरित 266"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0469, एकूण 466 स्रोत-एकके "
    "आणि 408 वाचक-विभाग. उर्वरित 256"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

for command in (r"\newcommand{\Taut}", r"\newcommand{\PL}", r"\newcommand{\RK}"):
    assert base.count(command) == 1

selected_modal = prior_namespace["selected_modal"]
replace_tokens = prior_namespace["replace_tokens"]
token_singular = replace_tokens.__globals__["singular"]
token_plural = replace_tokens.__globals__["plural"]
assert "tableau" not in token_singular and "signed formula" not in token_singular
token_singular.update({"tableau": "टॅब्लो", "signed formula": "चिन्हांकित सूत्र"})
token_plural.update({"tableau": "टॅब्लो", "signed formula": "चिन्हांकित सूत्रे"})
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/normal-modal-logic/tableaux"
driver = selected_modal((folder / "tableaux.tex").read_text(encoding="utf-8"))
assert r"\olchapter{nml}{tab}{मोडल \usetoken{P}{tableau}}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "rules-for-K",
    "proofs-in-K",
    "soundness",
    "more-rules",
    "more-soundness",
    "simple-S5",
    "completeness",
    "countermodels",
]
available.add("nml:tab:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = path.read_text(encoding="utf-8")
    if name == "soundness":
        # The standalone source changes a tag mid-document. The reader
        # includes both modal variants and therefore removes that one
        # directive before the legacy static tag selector runs.
        assert raw.count(r"\tagfalse{prvDiamond}") == 1
        raw = raw.replace(r"\tagfalse{prvDiamond}", "")
    content = selected_modal(raw)
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["nml", "tab"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

title = replace_tokens(r"मोडल \usetoken{P}{tableau}")
assert "!!" not in title and r"\usetoken" not in title
chunks = [r"\chapter{" + title + r"}\label{nml:tab:chap}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}", lambda match: r"\label{" + prefix + ":" + match.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", lambda match: references(match, parts), content)
    content = re.sub(r"\\Olref\{([^}]+)\}", lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}", content)
    content = re.sub(
        r"\\(?:c|C)ref\{([^}]+)\}",
        lambda match: " आणि ".join(r"\ref{" + item.strip() + "}" for item in match.group(1).split(",")),
        content,
    )
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tag_references, content, flags=re.S)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
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
\item \textbf{OLINC-191--OLINC-208}: मोडल टॅब्लोच्या
नियमांतील चिन्हे व पूर्वचिन्हे, निर्दोषता आणि
संपूर्णतेच्या पुराव्यांतील काही सूत्रे, तसेच
प्रतिदृष्टांत प्रतिमानांच्या उदाहरणांतील
चुकीच्या खुणा मराठीत दुरुस्त केल्या आहेत.
\textbf{OLINC-204} मध्ये नोंदलेली सांत
\(\Gamma\) वरून सर्वसाधारण \(\Gamma\) कडे
जाणाऱ्या स्रोत-पुराव्यातील उणीव
\textbf{SOL6-A180} मध्ये दुरुस्त केली आहे.
असांत प्रकरणासाठी सांत उपसंचांची सुसंगतता,
आधीचे लिंडेनबाउम आणि सत्यता पूर्वप्रमेय
वापरले आहेत. मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(
    r"\\readerexternalref\{([^}]+)\}",
    lambda match: r"\ref{" + match.group(1) + "}" if match.group(1) in available else match.group(0),
    out,
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[459:469]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 466 and inputs[-1]["unit_id"] == "OLP-0469"
assert out.count(r"\chapter{") == 48
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 408
assert "466 स्रोत-एकके आणि 408 वाचक-विभाग" in out
assert "!!" not in out
assert not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="466 source units, 408 reader sections, forty-eight complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(191, 209)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0460"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 408,
    "chapters": 48,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
