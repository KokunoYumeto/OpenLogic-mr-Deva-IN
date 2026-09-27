"""Assemble 46 complete Marathi chapters through OLP-0449 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core440.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("पंचेचाळीस संपूर्ण प्रकरणे") == 1
base = base.replace("पंचेचाळीस संपूर्ण प्रकरणे", "सेहेचाळीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0440, एकूण 437 स्रोत-एकके "
    "आणि 382 वाचक-विभाग. उर्वरित 285"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0449, एकूण 446 स्रोत-एकके "
    "आणि 390 वाचक-विभाग. उर्वरित 276"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

for command in (r"\newcommand{\Taut}", r"\newcommand{\PL}", r"\newcommand{\RK}"):
    assert base.count(command) == 1

selected_modal = prior_namespace["selected_modal"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/normal-modal-logic/completeness"
driver = selected_modal((folder / "completeness.tex").read_text(encoding="utf-8"))
assert r"\olchapter{nml}{com}{संपूर्णता आणि कॅनॉनिकल प्रतिमाने}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "complete-consistent-sets",
    "lindenbaums-lemma",
    "modalities-ccs",
    "canonical-models",
    "truth-lemma",
    "completeness-K",
    "frame-completeness",
]
available.add("nml:com:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected_modal(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["nml", "com"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

title = replace_tokens(r"संपूर्णता आणि कॅनॉनिकल प्रतिमाने")
assert "!!" not in title and r"\usetoken" not in title
chunks = [r"\chapter{" + title + r"}\label{nml:com:chap}"]
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
\item \textbf{OLINC-175--OLINC-180}: संपूर्ण सुसंगत संचांचे
पुरावे, लिंडेनबाउमच्या प्रगणनातील लांबीची अट,
मोडल निष्पत्तींतील निर्देशांक आणि \(\Sigma\) ची खूण,
तसेच सत्यता पूर्वप्रमेयातील सराव-टॅग यांतील
गोठवलेल्या इंग्रजी स्रोताच्या मर्यादित दुरुस्त्या
मराठी मजकुरात नोंदल्या आहेत. मूळ इंग्रजी बाइट्स
बदललेले नाहीत.
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
for row in manifest[440:449]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 446 and inputs[-1]["unit_id"] == "OLP-0449"
assert out.count(r"\chapter{") == 46
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 390
assert "446 स्रोत-एकके आणि 390 वाचक-विभाग" in out
assert "!!" not in out
assert not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="446 source units, 390 reader sections, forty-six complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(175, 181)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0441"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 390,
    "chapters": 46,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
