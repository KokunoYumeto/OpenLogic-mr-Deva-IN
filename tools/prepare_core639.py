"""Assemble 70 complete Marathi chapters through OLP-0639 without TeX."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from reader_bibliography import render_bibliography

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
with redirect_stdout(StringIO()):
    prev = runpy.run_path(str(ROOT / "tools/prepare_core632.py"))
helpers = prev["prior_ns"]
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("६९ संपूर्ण प्रकरणे") == 1
base = base.replace("६९ संपूर्ण प्रकरणे", "७० संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0632, एकूण 629 स्रोत-एकके आणि 544 वाचक-विभाग. उर्वरित 93"
new = "OLP-0004 ते OLP-0639, एकूण 636 स्रोत-एकके आणि 550 वाचक-विभाग. उर्वरित 86"
assert base.count(old) == 1
base = base.replace(old, new, 1)

anchor = r"\usetikzlibrary{automata}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + r"\usetikzlibrary{lindenmayersystems}" + "\n"
                    + r"\pgfdeclarelindenmayersystem{Hilbert curve}{"
                    + "\n" + r"  \rule{L -> +RF-LFL-FR+}"
                    + "\n" + r"  \rule{R -> -LF+RFR+FL-}}" + "\n", 1)
anchor = r"\newcommand{\Nat}{\mathbb{N}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + r"\newcommand{\unitline}{\text{L}}"
                    + "\n" + r"\newcommand{\unitsquare}{\text{S}}", 1)
anchor = r"\definecolor{oldiagcolorD}{HTML}{1973ba}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n"
                    + r"\definecolor{oldiagcolorE}{HTML}{4d6f39}", 1)

folder = ROOT / "mr/content/history/set-theory"
driver = helpers["selected"]((folder / "set-theory.tex").read_text(encoding="utf-8"))
assert r"\olchapter{his}{set}{संच उपपत्तीचा इतिहास आणि दंतकथा}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "infinitesimals", "limits", "pathologies", "mythology",
    "cantor-plane", "hilbert-curve",
]
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert editorial and driver.count(r"\begin{editorial}") == 1
available = helpers["available"]
external = helpers["external"]
available.add("his:set:chap")
files = []
for name in imports:
    target_text = (folder / (name + ".tex")).read_text(encoding="utf-8")
    raw = helpers["selected"](target_text)
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1, 2) == ("his", "set"), name
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix, re.findall(r"%READERNOTE\{(OLINC-\d+):", target_text)))
external.difference_update(available)

chunks = [r"\chapter{संच उपपत्तीचा इतिहास आणि दंतकथा}\label{his:set:chap}",
          editorial.group(0)]
reader_note_ids = []
for name, raw, parts, prefix, note_ids in files:
    reader_note_ids.extend(note_ids)
    content = helpers["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    for token, color, word in [
        ("colorC", "oldiagcolorC", "लाल"),
        ("colorD", "oldiagcolorD", "निळा"),
        ("colorE", "oldiagcolorE", "हिरवा"),
    ]:
        content = content.replace("!!{" + token + "}",
                                  r"\textcolor{" + color + "}{" + word + "}")
    content = content.replace("!!a{injection}", "एकास-एक फलन")
    content = content.replace("!!a{surjection}", "आच्छादक फलन")
    content = helpers["replace_tokens"](content)
    for original, projection in prior["reader_symbol_projections"].items():
        content = content.replace(original, projection)
    content = helpers["convert_section"](content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
                     lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
                     lambda m: helpers["ns"]["references"](m, parts), content)
    content = re.sub(r"\\(cite[a-zA-Z]*)((?:\[[^]]*\])*)\{([^}]+)\}",
                     prev["render_citation"], content)

    def collect_reader_note(match):
        return ""

    content = re.sub(r"(?m)^%READERNOTE\{(OLINC-\d+):[^\n]*\}\n?",
                     collect_reader_note, content)
    assert "!!" not in content and not re.search(r"![A-Z]", content), name
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|cite\w*)",
                         content), name
    chunks.append(content)
assert sorted(reader_note_ids) == [
    "OLINC-314", "OLINC-317", "OLINC-318", "OLINC-319", "OLINC-320",
]

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
bib_marker = r"\chapter*{संदर्भ}"
assert base.count(marker) == 1 and base.count(bib_marker) == 1
before, notes = base.split(marker, 1)
note_body, _ = notes.split(bib_marker, 1)
editorial_notes = (
    "\n" + r"\paragraph{सीमेची व्याख्या आणि चित्रातील निर्देशांक.} "
    "मूळ मर्यादा-व्याख्येत $x=c$ वगळलेले नाही; तसे केल्याशिवाय सामान्य सीमेची "
    "अट मिळत नाही. मराठी सूत्रात $0<|x-c|$ ही अट स्पष्ट केली आहे. निरपेक्ष "
    "मूल्याच्या आलेखात $-1$ या बिंदूचे चिन्ह दुरुस्त केले आहे. तसेच आधीच्या "
    "अवकलज-सूत्रातील बदलत्या भागाकाराचा उल्लेख स्पष्ट केला आहे. "
    r"\paragraph{द्विमान विस्तार.} "
    "\\textbf{SOL6-A281} मध्ये द्विमान निरूपणांची एकच निवड ठरवून "
    "एकास-एक फलनाची अट पूर्ण केली आहे. मूळ missing-value उदाहरण "
    "या प्रांतावर प्रतिमेतच येते; त्याऐवजी प्रतिमेबाहेरचे $5/6$ उदाहरण "
    "दिले आहे. ऐतिहासिक दशमान प्रयत्न आणि त्याचे आधुनिक द्विमान "
    "रूपांतर वेगळे केले आहेत. "
    r"\paragraph{हिल्बर्ट वक्राच्या सिद्धतेची दुरुस्ती.} "
    "प्रांत एकक रेषा ठेवून \\textbf{SOL6-A282} मध्ये प्रत्येक स्तराचे "
    "समान बंद प्राचल-अंतराल आणि जाळी-घरांचे सुसंगत refinement दिले आहे. "
    "घरकर्णाच्या मर्यादेने समसमान अभिसरण मिळते. अंतर्भूत बंद अंतराल "
    "प्रत्येक चौरस-बिंदूची प्रतिमापूर्व साक्ष देतात; प्रत्येक आदान बिंदूवरील "
    "सातत्य epsilon-delta अटीने सिद्ध केले आहे. मूळ तीन आकृत्या "
    "तशाच जपल्या आहेत.\n"
)
manifest = [json.loads(line) for line in
            (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[632:639]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 636 and inputs[-1]["unit_id"] == "OLP-0639"
bibliography, bib_audit = render_bibliography(ROOT, inputs)
out = before + "\n".join(chunks) + "\n" + marker + note_body + editorial_notes + "\n" + bibliography + "\n" + r"\end{document}" + "\n"
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
             lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
assert out.count(r"\chapter{") == 70
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 550
assert "636 स्रोत-एकके आणि 550 वाचक-विभाग" in out
assert out.count(r"\end{document}") == 1 and out.rstrip().endswith(r"\end{document}")
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
assert set(bib_audit["rendered_keys"]) == {label[4:] for label in labels if label.startswith("bib:")}
assert r"\ref{his:set:cantorplane:thm:cantorplane}" in out
assert r"\ref{his:set:limits:sec}" in out
assert not re.search(r"%READERNOTE\{OLINC-3", out)
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="636 source units, 550 reader sections, seventy complete chapters",
    external_reference_labels=sorted(set(re.findall(r"\\readerexternalref\{([^}]+)\}", out))),
    chapter_driver_units_not_rendered_as_sections=prior.get("chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0633"],
    reader_note_ids_covered_in_editorial=sorted(reader_note_ids),
    history_set_theory_source_issues=["OLINC-" + str(i) for i in range(313, 321)],
    bibliography_audit=bib_audit,
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
                  "sections": 550, "chapters": 70,
                  "bibliography_entries": len(bib_audit["rendered_keys"]),
                  "reader_notes": sorted(reader_note_ids),
                  "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
