"""Assemble 61 complete Marathi chapters through OLP-0564 without TeX."""
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core557.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("साठ संपूर्ण प्रकरणे") == 1
base = base.replace("साठ संपूर्ण प्रकरणे", "एकसष्ट संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0557, एकूण 554 स्रोत-एकके आणि 480 वाचक-विभाग. उर्वरित 168"
new = "OLP-0004 ते OLP-0564, एकूण 561 स्रोत-एकके आणि 486 वाचक-विभाग. उर्वरित 161"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\DeclareMathOperator*{\supstrict}{\mathrm{lsub}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + "\n".join([
    r"\newcommand{\trcl}[1]{\mathrm{trcl}(#1)}",
    r"\newcommand{\setrank}[1]{\mathrm{rank}(#1)}",
]), 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]

folder = ROOT / "mr/content/set-theory/spine"
driver = selected((folder / "spine.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{spine}{टप्पे आणि प्रतांक}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["idea", "recursion", "stagesbasics", "foundation", "zf", "rank"]
available.add("sth:spine:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "spine", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{टप्पे आणि प्रतांक}\label{sth:spine:chap}"]
cites = {r"\citet{ButtonLT1}": "Button (2021)"}
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
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
    for original, projection in cites.items():
        content = content.replace(original, projection)
    assert not re.search(r"\\cite(?:p|t|alt|author|year)?(?:\[[^]]*\])?\{", content), name
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref)", content)
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(marker) == 1
before, notes = base.split(marker, 1)
editorial = ("\n" + r"\paragraph{पुनरावर्तनातील आधारप्रकरण.} "
             "मूळ इंग्रजीत रिकाम्या प्रांताच्या फलनासाठी पुनरावर्तनाच्या व्याख्येत "
             "प्रकरण दिलेले नाही, तरी पुराव्यात त्या प्रकरणाचे मूल्य वापरले आहे. "
             "मराठी मांडणीत ते प्रकरण स्पष्ट केले आहे.\n"
             + r"\paragraph{पायाभूततेच्या पुराव्यातील बंधित चल.} "
             "मूळ सूत्रात आधी निश्चित केलेल्या $B$ ऐवजी अपरिभाषित $b$ आले आहे; "
             "मराठी सूत्रात $B$ वापरले आहे.\n"
             + r"\paragraph{प्रतांकावरील पुराव्यातील अट.} "
             "मूळ पुराव्यात $x\\in V_\\alpha$ मानून लगेच $x\\notin V_\\alpha$ "
             "असे म्हटले आहे. मराठी मजकुरात हा निष्कर्ष प्रतांक आणि टप्पा "
             "समान असल्याच्या प्रकरणापुरता स्पष्ट केला आहे.\n")
out = before + "\n".join(chunks) + "\n" + marker + notes + editorial
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = out.replace(r"\readerexternalref{sth:spine::chap}", r"\ref{sth:spine:chap}")
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[557:564]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 561 and inputs[-1]["unit_id"] == "OLP-0564"
assert out.count(r"\chapter{") == 61
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 486
assert "561 स्रोत-एकके आणि 486 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="561 source units, 486 reader sections, sixty-one complete chapters",
    external_reference_labels=sorted(external),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0558"])
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 486, "chapters": 61, "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
