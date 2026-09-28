"""Assemble 68 complete Marathi chapters through OLP-0619 without TeX."""
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
    prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core612.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("सदुसष्ट संपूर्ण प्रकरणे") == 1
base = base.replace("सदुसष्ट संपूर्ण प्रकरणे", "६८ संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0612, एकूण 609 स्रोत-एकके आणि 527 वाचक-विभाग. उर्वरित 113"
new = "OLP-0004 ते OLP-0619, एकूण 616 स्रोत-एकके आणि 533 वाचक-विभाग. उर्वरित 106"
assert base.count(old) == 1
base = base.replace(old, new, 1)
folder = ROOT / "mr/content/methods/induction"
driver = prior_ns["selected"]((folder / "induction.tex").read_text(encoding="utf-8"))
assert r"\olchapter{mth}{ind}{विगमन}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["introduction", "induction-on-N", "strong-induction",
                   "inductive-definitions", "structural-induction", "relations"]
available = prior_ns["available"]
external = prior_ns["external"]
available.add("mth:ind:chap")
files = []
for name in imports:
    raw = prior_ns["selected"]((folder / (name + ".tex")).read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "mth" and match.group(2) == "ind", name
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)
chunks = [r"\chapter{विगमन}\label{mth:ind:chap}"]
for name, raw, parts, prefix in files:
    content = prior_ns["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = prior_ns["replace_tokens"](content)
    for original, projection in prior["reader_symbol_projections"].items():
        content = content.replace(original, projection)
    content = prior_ns["convert_section"](content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: prior_ns["ns"]["references"](m, parts), content)
    content = re.sub(r"\\(cite[a-zA-Z]*)((?:\[[^]]*\])*)\{([^}]+)\}",
        prior_ns["ns"]["render_citation"], content)
    assert "!!" not in content and not re.search(r"![A-Z]", content), name
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|cite\w*)", content), name
    chunks.append(content)
marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
bib_marker = r"\chapter*{संदर्भ}"
before, notes = base.split(marker, 1)
note_body, _ = notes.split(bib_marker, 1)
editorial_notes = (
    "\n" + r"\paragraph{नैसर्गिक संख्यांवरील विगमनाचे निर्देशांक.} "
    "मूळ विवेचनाच्या एका पायरीत $k$ हा चल असताना त्याच्या जागी $1$ ठेवण्याऐवजी "
    "दुसऱ्या चलाचे नाव आले आहे; योग्य पायरीचल वापरला आहे. फाशांच्या उदाहरणात "
    "शून्य फाशांचे प्रकरण प्रस्तावनेत असले, तरी औपचारिक विगमन $1$ पासून सुरू होते. "
    "शून्य फाशांच्या रिकाम्या बेरजेचे प्रकरण स्पष्टपणे जोडले आहे.\n"
    + r"\paragraph{प्रबल विगमनातील रिक्त पूर्वभाग.} "
    "$k=0$ असताना $l<0$ अशी कोणतीही नैसर्गिक संख्या नसते. "
    "या रिक्त पूर्वभागातील मूळ मजकुरात बंधित $l$ ऐवजी $P(0)$ छापले आहे; "
    "विगमनाच्या प्रत्यक्ष गृहीतकानुसार $P(l)$ वापरले आहे.\n"
    + r"\paragraph{उचित पूर्वखंडाच्या पुराव्याची व्याप्ती.} "
    "मूळ व्याख्येत रिकामी चिन्हमाला उचित पूर्वखंड ठरते, पण तीत उघडणारे आणि "
    "बंद करणारे कंस शून्य असतात. म्हणून कंसांची काटेकोर असमानता तिच्यासाठी असत्य आहे. "
    "मूळ पुराव्यातील पाचही प्रकरणे अरिक्त पूर्वखंडांचीच आहेत; मराठीत ती आवश्यक अट "
    "व्याख्या, विधान आणि पुराव्यात स्पष्ट केली आहे.\n"
)
manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[612:619]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 616 and inputs[-1]["unit_id"] == "OLP-0619"
bibliography, bib_audit = render_bibliography(ROOT, inputs)
out = before + "\n".join(chunks) + "\n" + marker + note_body + editorial_notes + "\n" + bibliography + "\n" + r"\end{document}" + "\n"
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
assert out.count(r"\chapter{") == 68
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 533
assert "616 स्रोत-एकके आणि 533 वाचक-विभाग" in out
assert out.count(r"\end{document}") == 1 and out.rstrip().endswith(r"\end{document}")
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
assert set(bib_audit["cited_keys"]) == {x[4:] for x in labels if x.startswith("bib:")}
assert r"\ref{mth:ind:sti:prop:initial}" in out
assert r"\ref{mth:ind:rel:defn:depth}" in out
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="616 source units, 533 reader sections, sixty-eight complete chapters",
    external_reference_labels=sorted(set(re.findall(r"\\readerexternalref\{([^}]+)\}", out))),
    chapter_driver_units_not_rendered_as_sections=prior.get("chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0613"],
    bibliography_audit=bib_audit)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 533, "chapters": 68, "bibliography_entries": len(bib_audit["cited_keys"]),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
