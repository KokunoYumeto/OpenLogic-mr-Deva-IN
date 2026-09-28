"""Assemble 67 complete Marathi chapters through OLP-0612 without TeX."""
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
    ns = runpy.run_path(str(ROOT / "tools/prepare_core600.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("सहासष्ट संपूर्ण प्रकरणे") == 1
base = base.replace("सहासष्ट संपूर्ण प्रकरणे", "सदुसष्ट संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0600, एकूण 597 स्रोत-एकके आणि 517 वाचक-विभाग. उर्वरित 125"
new = "OLP-0004 ते OLP-0612, एकूण 609 स्रोत-एकके आणि 527 वाचक-विभाग. उर्वरित 113"
assert base.count(old) == 1
base = base.replace(old, new, 1)
# The Methods introduction explicitly explains these result labels.
base = base.replace(r"\newtheorem{prop}[defn]{प्रतिज्ञा}", r"\newtheorem{prop}[defn]{विधान}")
base = base.replace(r"\newtheorem{lem}[defn]{सहायक प्रमेय}", r"\newtheorem{lem}[defn]{पूर्वप्रमेय}")
base = base.replace(r"\newtheorem{cor}[defn]{निष्कर्ष}", r"\newtheorem{cor}[defn]{अनुप्रमेय}")
selected = ns["selected"]
replace_tokens = ns["replace_tokens"]
convert_section = ns["convert_section"]
available = ns["available"]
external = ns["external"]
ns["bibliographic_names"].update({
    "Solow2013": ("सोलो", "2013"), "Velleman2019": ("व्हेलमन", "2019"),
    "Hammack2013": ("हॅमॅक", "2013"), "Sandstrum2019": ("सँडस्ट्रम", "2019"),
    "Steinhart2018": ("स्टाइनहार्ट", "2018"), "Hutchings2003": ("हचिंग्ज", "2003"),
    "Cheng2004": ("चेंग", "2004"),
})
folder = ROOT / "mr/content/methods/proofs"
part_driver = selected((ROOT / "mr/content/methods/methods.tex").read_text(encoding="utf-8"))
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", part_driver, re.S)
assert editorial
driver = selected((folder / "proofs.tex").read_text(encoding="utf-8"))
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["introduction", "starting-proofs", "using-definitions", "inference-patterns",
                   "example-1", "example-2", "proof-by-contradiction", "reading-proofs", "cant-do-it", "resources"]
available.update({"mth:part", "mth:prf:chap"})
files = []
for name in imports:
    raw = selected((folder / (name + ".tex")).read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "mth" and match.group(2) == "prf", name
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)
chunks = [r"\part{पद्धती}\label{mth:part}", editorial.group(),
          r"\chapter{सिद्धता}\label{mth:prf:chap}"]
for name, raw, parts, prefix in files:
    content = ns["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1
    content = replace_tokens(content)
    if name == "resources":
        assert content.count(r"\section{इतर साधने}") == 1
        content = content.replace(r"\section{इतर साधने}",
            r"\section{इतर साधने}\label{" + prefix + ":sec}", 1)
    else:
        content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: ns["references"](m, parts), content)
    content = re.sub(r"\\(cite[a-zA-Z]*)((?:\[[^]]*\])*)\{([^}]+)\}", ns["render_citation"], content)
    for original, projection in prior["reader_symbol_projections"].items():
        content = content.replace(original, projection)
    assert "!!" not in content and not re.search(r"![A-Z]", content), name
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|cite\w*)", content), name
    chunks.append(content)
marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
bib_marker = r"\chapter*{संदर्भ}"
before, notes = base.split(marker, 1)
note_body, _ = notes.split(bib_marker, 1)
editorial_notes = (
    "\n" + r"\paragraph{सिद्धता-प्रकरणातील आवृत्ती आणि विभागक्रम.} "
    "मूळ इंग्रजी आवृत्तीतील नैसर्गिक भाषेचा उल्लेख या मराठी आवृत्तीसाठी स्पष्ट केला आहे. "
    "सिद्धतेचे प्रकार ताबडतोब पुढच्या विभागात येतात असे दोन उल्लेख आहेत; प्रत्यक्ष स्रोतक्रमात "
    "व्याख्यांचा विभाग आधी असल्यामुळे पुढील विभागांचा सामान्य निर्देश केला आहे. "
    "व्याख्यांच्या विभागाचा मूळ भाग-निर्देशांकही पद्धती भागाशी जुळवला आहे.\n"
    + r"\paragraph{अस्तित्ववाची विधानातील नव्या नावाचे कार्य.} "
    "निष्कर्षात नाव नसणे एवढेच पुरेसे नाही: नव्या वस्तूविषयी अतिरिक्त, मुक्त न केलेली गृहीतके "
    "वापरता कामा नयेत. तात्पुरते सदस्यत्व गृहीतक मुक्त केल्यावर मूळ अस्तित्ववाची विधान "
    "आणि इतर अनुमत गृहीतके यांचा आधार उरतो. मूळ स्पष्टीकरणात अरिक्त संचाऐवजी "
    "बंधित चलाचे नाव आले होते; संचाचे नाव वापरले आहे.\n"
    + r"\paragraph{संचांच्या उदाहरणांतील मुद्रणदोष.} "
    "एका संयोग-नॉनसमावेशनाच्या स्पष्टीकरणात अपरिभाषित संचाचे नाव आले होते; योग्य संयोग "
    "वापरला आहे. शोषणाच्या विस्तृत सिद्धतेत पहिला समावेशन-निष्कर्ष दोनदा दिला होता; "
    "दुसरा निष्कर्ष उलट समावेशनाने बदलला आहे. दोन उदाहरणांतील न जुळणारे कंस दुरुस्त केले आहेत.\n"
)
manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[600:612]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
bibliography, bib_audit = render_bibliography(ROOT, inputs)
out = before + "\n".join(chunks) + "\n" + marker + note_body + editorial_notes + "\n" + bibliography + "\n" + r"\end{document}" + "\n"
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
assert len(inputs) == 609 and inputs[-1]["unit_id"] == "OLP-0612"
assert out.count(r"\chapter{") == 67
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 527
assert "609 स्रोत-एकके आणि 527 वाचक-विभाग" in out
assert out.count(r"\end{document}") == 1 and out.rstrip().endswith(r"\end{document}")
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
assert set(bib_audit["cited_keys"]) == {x[4:] for x in labels if x.startswith("bib:")}
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="609 source units, 527 reader sections, sixty-seven complete chapters",
    external_reference_labels=sorted(set(re.findall(r"\\readerexternalref\{([^}]+)\}", out))),
    chapter_driver_units_not_rendered_as_sections=prior.get("chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0602"],
    part_driver_units_rendered_as_part_headings=prior.get("part_driver_units_rendered_as_part_headings", []) + ["OLP-0601"],
    bibliography_audit=bib_audit)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 527, "chapters": 67, "bibliography_entries": len(bib_audit["cited_keys"]),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
