"""Assemble 55 complete Marathi chapters through OLP-0515 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path
from complete_reader_notes import NOTE, project_note


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools/prepare_core510.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("चोपन्न संपूर्ण प्रकरणे") == 1
base = base.replace("चोपन्न संपूर्ण प्रकरणे", "पंचावन्न संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0510, एकूण 507 स्रोत-एकके "
    "आणि 441 वाचक-विभाग. उर्वरित 215"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0515, एकूण 512 स्रोत-एकके "
    "आणि 445 वाचक-विभाग. उर्वरित 210"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

selected = prior_namespace["selected_modal"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/intuitionistic-logic/tableaux"
driver = selected((folder / "tableaux.tex").read_text(encoding="utf-8"))
assert r"\olchapter{int}{tab}{अंतःप्रज्ञावादी \usetoken{P}{tableau}}" in driver
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert editorial
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["introduction", "rules", "proofs", "soundness"]
available.add("int:tab:chap")
files = []
reader_note_count = 0
expected_reader_notes = 0
for name in imports:
    path = folder / (name + ".tex")
    raw = path.read_text(encoding="utf-8")
    # SOL6-A204: later source repairs may add notes to any imported unit.
    expected_reader_notes += len(NOTE.findall(raw))

    def render_reader_note(match):
        global reader_note_count
        reader_note_count += 1
        return (r"\begin{quote}\small\textbf{स्रोतनोंद.} "
                + project_note(match.group(1)) + r"\end{quote}")

    raw = NOTE.sub(render_reader_note, raw)
    content = selected(raw)
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["int", "tab"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
assert reader_note_count == expected_reader_notes
external.difference_update(available)

title = replace_tokens(r"अंतःप्रज्ञावादी \usetoken{P}{tableau}")
assert "!!" not in title and r"\usetoken" not in title
chunks = [
    r"\chapter{" + title + r"}\label{int:tab:chap}",
    replace_tokens(editorial.group()),
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
\item \textbf{OLINC-228--230}: अंतःप्रज्ञावादी
टॅब्लो प्रकरणातील चुकून आलेला मोडल उल्लेख,
सत्याचा प्राप्य जगांमध्ये टिकाव, आणि
सशर्त सूत्रासाठीच्या शाखांवरील सत्य-असत्य
चिन्हे मराठीत संदर्भाशी जुळवली आहेत.
\item \textbf{OLINC-231}: उदाहरणातील
दोन संधियोग-नियमांच्या कारणनिर्देशांत
ओळ ४ ऐवजी त्या सूत्राची ओळ ७ दिली आहे.
\item \textbf{OLINC-232--235}: निर्दोषतेच्या
स्रोतसिद्धतेतील प्रतिप्रतिमानाचे चिन्ह,
दोन नियमांचे निष्कर्ष-संच आणि अंतिम
तार्किक निष्पन्नता यांतील चुका
दुरुस्त केल्या आहेत. \textbf{OLINC-233}
मधील मनमानी पूर्वचिन्ह-संचाविषयीची
व्याख्यात्मक उणीव दुरुस्त केली आहे:
सर्व वापरलेल्या पूर्वचिन्ह-विस्तारांसाठी
प्राप्यता आवश्यक आहे. नवे साक्षी-पूर्वचिन्ह
किंवा त्याचा विस्तार आधी वापरलेला नसावा,
या अटीने जुने अर्थनिर्धारण जपले जाते.
इतर नियमांच्या सिद्धता मूळप्रमाणे
स्वाध्याय आहेत. मूळ इंग्रजी बाइट्स
बदललेले नाहीत.
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
for row in manifest[510:515]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 512 and inputs[-1]["unit_id"] == "OLP-0515"
assert out.count(r"\chapter{") == 55
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 445
assert "512 स्रोत-एकके आणि 445 वाचक-विभाग" in out
assert "OLINC-233" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="512 source units, 445 reader sections, fifty-five complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [
        f"OLINC-{index:03d}" for index in range(228, 236)
    ],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0511"],
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 445,
    "chapters": 55,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
