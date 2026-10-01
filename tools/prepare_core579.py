"""Assemble 63 complete Marathi chapters through OLP-0579 without TeX."""
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core573.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("बासष्ट संपूर्ण प्रकरणे") == 1
base = base.replace("बासष्ट संपूर्ण प्रकरणे", "त्रेसष्ट संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0573, एकूण 570 स्रोत-एकके आणि 494 वाचक-विभाग. उर्वरित 152"
new = "OLP-0004 ते OLP-0579, एकूण 576 स्रोत-एकके आणि 499 वाचक-विभाग. उर्वरित 146"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\newcommand{\stagescofin}{\emph{टप्पे संचांपलीकडे जातात}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + "\n".join([
    r"\newcommand{\ordplus}{+}",
    r"\newcommand{\ordtimes}{\cdot}",
    r"\newcommand{\ordexpo}[2]{#1^{(#2)}}",
    r"\newcommand{\disjointsum}{\sqcup}",
    r"\newcommand{\rlexless}{\mathrel{\sphericalangle}}",
]), 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]

folder = ROOT / "mr/content/set-theory/ord-arithmetic"
driver = selected((folder / "ord-arithmetic.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{ord-arithmetic}{क्रमसूचक अंकगणित}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["introduction", "addition", "using-addition", "multiplication", "exponentiation"]
available.add("sth:ord-arithmetic:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "ord-arithmetic", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{क्रमसूचक अंकगणित}\label{sth:ord-arithmetic:chap}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = content.replace("!!{injection}", "एकास-एक फलन")
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\Olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}",
        lambda m: " आणि ".join(r"\ref{" + x.strip() + "}" for x in m.group(1).split(",")), content)
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references, content, flags=re.S)
    for locator in (r"\citep[p.~199]{Potter2004}", r"\citep[पृ.~199]{Potter2004}"):
        content = content.replace(locator, "(पॉटर 2004, पृ.~199)")
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
editorial = (
    "\n" + r"\paragraph{क्रमसूचक बेरजेच्या रचनेतील तीन दुरुस्त्या.} "
    "मूळ इंग्रजीत संबंधाच्या घटकजोड्या $D$ मधून घेतल्यासारख्या लिहिल्या "
    "आहेत; त्या $D\\times D$ मधून असतात. पुढे अनुक्रमक बेरीज उलगडताना "
    "दोन आधीच खूण केलेल्या घटकसंचांमध्ये पुन्हा विभक्त बेरीज लिहिली आहे; "
    "मराठीत साधे संघटन वापरले आहे. शून्याशी बेरीज करताना रिकाम्या "
    "घटकाऐवजी एकघटकी संच लिहिलेला आहे; तो रिक्त संच केला आहे.\n"
    + r"\paragraph{प्रतांकाच्या सरावातील चिन्ह.} "
    "मूळ दुसऱ्या सरावात अपेक्षित प्रतांक आणि वरची मर्यादा यांच्यामध्ये "
    "समानतेचे चिन्ह सुटले आहे; मराठीत ते पुरवले आहे. एका निष्क्रिय "
    "टिप्पणीत विसंगत गणित-सीमाचिन्हही जोडले आहे.\n"
    + r"\paragraph{क्रमसूचक गुणाकाराचे सीमा प्रकरण.} "
    "मूळ सार्वत्रिक सूत्रातील कठोर लघुतम ऊर्ध्वबंध शून्य डाव्या "
    "घटकासाठी चुकीचा परिणाम देतो. मराठी सूत्रात आधीच्या गुणाकारांचे "
    "संघटन वापरले आहे; त्यामुळे शून्याचे सीमा क्रमसूचक संख्येशी "
    "गुणाकार शून्य राहतो.\n"
    + r"\paragraph{क्रमसूचक घातांकनाचा फलनसंच आणि शून्य आधार.} "
    "मूळ रचनेत आधार आणि घातांक यांचा फलनसंचातील क्रम उलटा आहे. "
    "मराठी व्याख्या आणि सरावात घातांकावरून आधाराकडे जाणारी, केवळ सांत "
    "ठिकाणी अशून्य असणारी फलने घेतली आहेत. शून्य आधार आणि $\\omega$ घातांकासाठी मात्र "
    "मूळ सीमा-सूत्रात शून्य घातांकाचे मूल्य $1$ संघटित होते, तर "
    "फलनसंच रिकामा असतो. त्यामुळे मुख्य दोन्ही व्याख्या आणि सराव "
    "शून्येतर आधारापुरते केले आहेत; सरावाची सिद्धता दिलेली नाही.\n"
)
out = before + "\n".join(chunks) + "\n" + marker + notes + editorial
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
for row in manifest[573:579]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 576 and inputs[-1]["unit_id"] == "OLP-0579"
assert out.count(r"\chapter{") == 63
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 499
assert "576 स्रोत-एकके आणि 499 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="576 source units, 499 reader sections, sixty-three complete chapters",
    external_reference_labels=sorted(set(re.findall(
        r"\\readerexternalref\{([^}]+)\}", out))),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0574"])
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 499, "chapters": 63,
    "external_references": len(prior["external_reference_labels"]),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
