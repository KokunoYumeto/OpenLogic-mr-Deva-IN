"""Assemble 60 complete Marathi chapters through OLP-0557 without TeX."""
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core546.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("एकोणसाठ संपूर्ण प्रकरणे") == 1
base = base.replace("एकोणसाठ संपूर्ण प्रकरणे", "साठ संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0546, एकूण 543 स्रोत-एकके आणि 470 वाचक-विभाग. उर्वरित 179"
new = "OLP-0004 ते OLP-0557, एकूण 554 स्रोत-एकके आणि 480 वाचक-विभाग. उर्वरित 168"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\newcommand{\Zminus}{\Z^{-}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" + "\n".join([
    r"\newcommand{\ZF}{\Th{ZF}}",
    r"\newcommand{\ZFminus}{\ZF^{-}}",
    r"\newcommand{\ordtype}[1]{\mathrm{ord}(#1)}",
    r"\newcommand{\ordsucc}[1]{#1^{+}}",
    r"\newcommand{\ordeq}[2]{#1 \cong #2}",
    r"\newcommand{\ordneq}[2]{#1 \ncong #2}",
    r"\newcommand{\isomorphic}{\cong}",
    r"\DeclareMathOperator*{\supstrict}{\mathrm{lsub}}",
]), 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]

folder = ROOT / "mr/content/set-theory/ordinals"
driver = selected((folder / "ordinals.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{ordinals}{क्रमसूचक संख्या}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction", "idea", "wo", "iso", "vn", "basic", "replacement",
    "milestone", "ordtype", "opps"
]
available.add("sth:ordinals:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "ordinals", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{क्रमसूचक संख्या}\label{sth:ordinals:chap}"]
cites = {
    r"\citeauthor{Burali-Forti1897}": "बुराली-फोर्ती",
    r"\citep[p.~105]{Heijenoort1967}": "(व्हान हायेनूर्ट 1967, पृ.~105)",
    r"\citeyear{Fraenkel1922}": "1922",
    r"\citet{Skolem1922}": "स्कोलेम (1922)",
}
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = content.replace("!!{bijection}s", "एकास-एक आच्छादने")
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
editorial = ("\n" + r"\paragraph{क्रम-समरूपणाच्या पुराव्यातील मुद्रित चूक.} "
             "मूळ इंग्रजी आवृत्तीत क्रम-समरूपणाच्या एका पुराव्यात $B_{b_2}$ ला "
             "फलनाचा प्रांत म्हटले आहे; प्रदर्शित $f:A_{a_2}\\to B_{b_2}$ नुसार तो "
             "सहप्रांत आहे. मराठी मजकुरात हा शब्द दुरुस्त केला आहे.\n")
out = before + "\n".join(chunks) + "\n" + marker + notes + editorial
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = out.replace(r"\readerexternalref{sth:ordinals::chap}", r"\ref{sth:ordinals:chap}")
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[546:557]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 554 and inputs[-1]["unit_id"] == "OLP-0557"
assert out.count(r"\chapter{") == 60
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 480
assert "554 स्रोत-एकके आणि 480 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(input_units=inputs,
    scope="554 source units, 480 reader sections, sixty complete chapters",
    external_reference_labels=sorted(external),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0547"])
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
    "sections": 480, "chapters": 60, "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
