"""Assemble 56 complete Marathi chapters through OLP-0521 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools/prepare_core515.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("पंचावन्न संपूर्ण प्रकरणे") == 1
base = base.replace("पंचावन्न संपूर्ण प्रकरणे", "छप्पन्न संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0515, एकूण 512 स्रोत-एकके "
    "आणि 445 वाचक-विभाग. उर्वरित 210"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0521, एकूण 518 स्रोत-एकके "
    "आणि 449 वाचक-विभाग. उर्वरित 204"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
old_subtitle = "तसेच अंतःप्रज्ञावादी तर्कशास्त्र\\par}"
new_subtitle = "तसेच अंतःप्रज्ञावादी तर्कशास्त्र आणि प्रतिवास्तविक विधाने\\par}"
assert base.count(old_subtitle) == 1
base = base.replace(old_subtitle, new_subtitle, 1)
old_description = "तसेच अंतःप्रज्ञावादी तर्कशास्त्र या प्रकरणांचे आहे:"
new_description = "तसेच अंतःप्रज्ञावादी तर्कशास्त्र आणि प्रतिवास्तविक विधाने या प्रकरणांचे आहे:"
assert base.count(old_description) == 1
base = base.replace(old_description, new_description, 1)
old_metadata = "आणि अंतःप्रज्ञावादी तर्कशास्त्र},pdfauthor="
new_metadata = "आणि अंतःप्रज्ञावादी तर्कशास्त्र व प्रतिवास्तविक विधाने},pdfauthor="
assert base.count(old_metadata) == 1
base = base.replace(old_metadata, new_metadata, 1)
assert r"\newcommand{\strictif}{\fishhookright}" in base

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

part_path = ROOT / "mr/content/counterfactuals/counterfactuals.tex"
part = selected(part_path.read_text(encoding="utf-8"))
assert r"\olpart{cnt}{प्रतिवास्तविक विधाने}" in part
folder = ROOT / "mr/content/counterfactuals/introduction"
driver = selected((folder / "introduction.tex").read_text(encoding="utf-8"))
assert r"\olchapter{cnt}{int}{प्रस्तावना}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["material-conditional", "paradoxes-material", "strict-conditional", "counterfactuals"]
available.update({"cnt:part", "cnt:int:chap"})
files = []
reader_note_count = 0
for name in imports:
    path = folder / (name + ".tex")
    raw = path.read_text(encoding="utf-8")
    if name == "counterfactuals":
        def render_reader_note(match):
            global reader_note_count
            reader_note_count += 1
            assert match.group(1).startswith("OLINC-238:")
            return (
                r"\begin{quote}\small\textbf{स्रोतविश्लेषणाची मर्यादा.} "
                + match.group(1)
                + r"\end{quote}"
            )
        raw = re.sub(r"(?m)^[ \t]*%READERNOTE\{(.*)\}$", render_reader_note, raw)
    content = selected(raw)
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["cnt", "int"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
assert reader_note_count == 1
external.difference_update(available)

chunks = [
    r"\part{प्रतिवास्तविक विधाने}\label{cnt:part}",
    r"\chapter{प्रस्तावना}\label{cnt:int:chap}",
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda match: r"\label{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", lambda match: references(match, parts), content)
    content = re.sub(
        r"\\Olref\{([^}]+)\}",
        lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}",
        content,
    )
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
new_notes = r"""
\item \textbf{OLINC-236}: कठोर अभिव्यंजनाच्या
एक अवैध निष्पन्नता-दाव्यात मूळ इंग्रजीत
वास्तविक अभिव्यंजनाचे निषेधन आले आहे.
मराठीत कठोर अभिव्यंजनाचे निषेधन वापरले आहे.
\item \textbf{OLINC-237}: कठोर अभिव्यंजन
आवश्यकतेने सत्य किंवा असत्य ठरते या दाव्याला
S5 ची व्याप्ती मराठीत स्पष्ट केली आहे.
\item \textbf{OLINC-238}: स्टालनाकर आणि
लुईस यांना एकच अद्वितीय सर्वाधिक जवळचे जग
गृहीत धरणारी सत्यता-अट देणे हे सुलभीकरण
आहे. लुईसच्या विश्लेषणात समसमान जवळची
अनेक जगे किंवा सर्वात जवळचे जग नसणेही
शक्य आहे. विभागात दिसणारी टीप ही मर्यादा
स्पष्ट करते. मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_notes + r"\end{enumerate}", 1)
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
for row in manifest[515:521]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 518 and inputs[-1]["unit_id"] == "OLP-0521"
assert out.count(r"\chapter{") == 56
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 449
assert "518 स्रोत-एकके आणि 449 वाचक-विभाग" in out
assert "स्रोतविश्लेषणाची मर्यादा" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="518 source units, 449 reader sections, fifty-six complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + ["OLINC-236", "OLINC-237", "OLINC-238"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0516", "OLP-0517"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 449,
    "chapters": 56,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
