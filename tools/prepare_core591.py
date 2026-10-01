"""Assemble 65 complete Marathi chapters through OLP-0591 without TeX."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
with redirect_stdout(StringIO()):
    prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core585.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("चौसष्ट संपूर्ण प्रकरणे") == 1
base = base.replace("चौसष्ट संपूर्ण प्रकरणे", "पासष्ट संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0585, एकूण 582 स्रोत-एकके आणि 504 वाचक-विभाग. उर्वरित 140"
new = "OLP-0004 ते OLP-0591, एकूण 588 स्रोत-एकके आणि 509 वाचक-विभाग. उर्वरित 134"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\newcommand{\cardfont}[1]{\mathfrak{#1}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + "\n".join([
    r"\newcommand{\cardsucc}[1]{#1^{\oplus}}",
    r"\newcommand{\canonord}{\lhd}",
    r"\newcommand{\cardplus}{\oplus}",
    r"\newcommand{\cardtimes}{\otimes}",
    r"\newcommand{\cardexpo}[2]{#1^{#2}}",
    r"\newcommand{\funfromto}[2]{{}^{#1}{#2}}",
]), 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]

folder = ROOT / "mr/content/set-theory/card-arithmetic"
driver = selected((folder / "card-arithmetic.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{card-arithmetic}{संचांकांचे अंकगणित}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["opps", "simp", "expotough", "ch", "fix"]
available.add("sth:card-arithmetic:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "card-arithmetic", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{संचांकांचे अंकगणित}\label{sth:card-arithmetic:chap}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = content.replace("!!{injection}", "एकास-एक फलन")
    content = content.replace("!!a{injection}", "एकास-एक फलन")
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}",
        lambda m: " आणि ".join(r"\ref{" + x.strip() + "}" for x in m.group(1).split(",")), content)
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references, content, flags=re.S)
    for old_cite, rendered_cite in [
        (r"\citet{Godel1938}", "गोडेल (1938)"),
        (r"\citet{Cohen1963}", "कोहेन (1963)"),
        (r"\citet[\S15.6]{Potter2004}", r"पॉटर (2004, \S15.6)"),
        (r"\citep[p.~257]{Boolos2000}", "(बूलोस 2000, पृ.~257)"),
        (r"\citep[पृ.~257]{Boolos2000}", "(बूलोस 2000, पृ.~257)"),
        (r"\citep[p.~268]{Boolos2000}", "(बूलोस 2000, पृ.~268)"),
        (r"\citep[पृ.~268]{Boolos2000}", "(बूलोस 2000, पृ.~268)"),
    ]:
        content = content.replace(old_cite, rendered_cite)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref|crefrange|cite\w*)", content)
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(marker) == 1
before, notes = base.split(marker, 1)
old_note_intro = "स्रोताशी जुळवलेल्या TeX फाइलांतील मूळ चिन्हे बदललेली नाहीत."
assert notes.count(old_note_intro) == 1
notes = notes.replace(old_note_intro,
    "मूळ इंग्रजी स्रोताचे बाइट्स बदललेले नाहीत. मराठी TeX फाइलांतील "
    "नोंदवलेल्या स्रोतदुरुस्त्या या संपादकीय नोंदी आणि निर्णयनोंदवहीत स्पष्ट केल्या आहेत.", 1)
editorial = (
    "\n" + r"\paragraph{संचांक घातांकनाची संकेतरचना.} "
    "घातसंचाच्या संचांकावरील पुराव्यात आणि घातांकनाच्या मर्यादेत मूळ स्रोत "
    "साधी वरलिखित घात-संकेतरचना वापरतो. त्या ठिकाणी मराठीत संचांक "
    "घातांकनाची स्पष्ट संकेतरचना वापरली आहे.\n"
    + r"\paragraph{कॅनॉनिकल क्रमातील सांत प्रकरण.} "
    "आद्यखंडाच्या आकारमानाचा पुरावा मूळ स्रोत फक्त अनंत कमाल निर्देशांकासाठी "
    "स्पष्ट करतो. कमाल निर्देशांक सांत असेल तर आद्यखंड सांत असतो, "
    "हे आवश्यक प्रकरण मराठीत जोडले आहे.\n"
    + r"\paragraph{घातांकनाच्या पुराव्यातील फलनांचे प्रकार.} "
    "वियुक्त युतीवरील फलनाचे विभाजन दोन फलनांची क्रमित जोडी देते; "
    "त्यांच्या आलेखांचा कार्तीय गुणाकार देत नाही. तसेच पुनर्गटित फलनाचा "
    "प्रत्यक्ष प्रांत कार्तीय गुणाकार आहे, त्याचा संचांक-प्रतिनिधी नाही. "
    "मराठीत हे दोन्ही प्रकार दुरुस्त केले आहेत.\n"
    + r"\paragraph{शून्य घातांकाचा अपवाद.} "
    "अनंत संचांकाचा सांत घात स्वतः त्या संचांकाइतका असतो, या विधानात "
    "शून्य घातांक वगळावा लागतो. शून्य घाताचे मूल्य एक असते. "
    "GCH अंतर्गत पुढील घात-मर्यादेतही अनंत आधार आणि शून्येतर घातांक "
    "या आवश्यक अटी मराठीत स्पष्ट केल्या आहेत.\n"
    + r"\paragraph{अलेफ अनुक्रमाच्या पुराव्यातील टप्पे.} "
    "प्रत्येक अनंत संचांक अलेफ अनुक्रमात येतो, या पुराव्यात लघुतम अनंत "
    "संचांकाचे आधारप्रकरण आणि अनंत संचांकांपुरते विगमन आवश्यक आहे. "
    "हे आवश्यक टप्पे मराठीत स्पष्ट केले आहेत. एकमेवतेविषयीचा वैध "
    "मूळ संक्षिप्त तर्क स्वतंत्र विस्तार न करता जपला आहे.\n"
    + r"\paragraph{स्थिरबिंदू अनुक्रमातील वाढ.} "
    "मूळ अंतिम रचनेत प्रारंभिक संचांक आधीच बेथ-स्थिरबिंदू असेल तर "
    "पुनरावर्तन स्थिर राहते. त्यामुळे दावा केलेली काटेकोर वाढ आणि नंतरचे "
    "एकास-एक फलन मिळत नाही. मराठीत सुरुवात प्रारंभिक संचांकाच्या "
    "उत्तरवर्ती संचांकापासून केली आहे. पुढील अनुक्रमाचे शून्यवे मूल्य "
    "शून्य आहे; ते बेथ-स्थिरबिंदू नाही, हा अपवादही स्पष्ट केला आहे.\n"
)
# Earlier assemblers appended several editorial paragraphs after the
# document terminator. Put all accumulated notes in their actual chapter,
# ahead of the bibliography, so TeX renders them and the source gaps remain
# visible to readers.
assert notes.count(r"\end{document}") == 1
notes_body, trailing_notes = notes.split(r"\end{document}", 1)
bib_marker = r"\chapter*{संदर्भ}"
assert notes_body.count(bib_marker) == 1
note_body, bibliography = notes_body.split(bib_marker, 1)
out = (before + "\n".join(chunks) + "\n" + marker + note_body
    + trailing_notes + editorial + "\n" + bib_marker + bibliography
    + r"\end{document}" + "\n")
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = re.sub(r"\\readerexternalref\{([^{}]+)::chap\}",
    lambda m: r"\ref{" + m.group(1) + ":chap}"
    if m.group(1) + ":chap" in available else m.group(0), out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[585:591]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 588 and inputs[-1]["unit_id"] == "OLP-0591"
assert out.count(r"\chapter{") == 65
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 509
assert "588 स्रोत-एकके आणि 509 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
assert out.count(r"\end{document}") == 1 and out.rstrip().endswith(r"\end{document}")
assert out.index(r"\paragraph{विभक्तीकरणाविषयी मूळ पुराव्यातील त्रुटी.}") < out.index(bib_marker)
assert out.index(r"\paragraph{स्थिरबिंदू अनुक्रमातील वाढ.}") < out.index(bib_marker)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="588 source units, 509 reader sections, sixty-five complete chapters",
    external_reference_labels=sorted(set(re.findall(r"\\readerexternalref\{([^}]+)\}", out))),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0586"])
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 509, "chapters": 65, "external_references": len(prior["external_reference_labels"]),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
