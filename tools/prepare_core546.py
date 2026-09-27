"""Assemble 59 complete Marathi chapters through OLP-0546 without TeX."""
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core536.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("अठ्ठावन्न संपूर्ण प्रकरणे") == 1
base = base.replace("अठ्ठावन्न संपूर्ण प्रकरणे", "एकोणसाठ संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0536, एकूण 533 स्रोत-एकके आणि 461 वाचक-विभाग. उर्वरित 189"
new = "OLP-0004 ते OLP-0546, एकूण 543 स्रोत-एकके आणि 470 वाचक-विभाग. उर्वरित 179"
assert base.count(old) == 1
base = base.replace(old, new, 1)
anchor = r"\newcommand{\stagesord}{\emph{टप्प्यांचा क्रम}}"
assert base.count(anchor) == 1
base = base.replace(anchor, anchor + "\n" +
    r"\newcommand{\stageshier}{\emph{टप्पे मूलभूत}}" + "\n" +
    r"\newcommand{\stagesacc}{\emph{टप्प्यांवरील संचय}}" + "\n" +
    r"\newcommand{\stagessucc}{\emph{टप्पे सुरूच राहतात}}" + "\n" +
    r"\newcommand{\stagesinf}{\emph{अनंत टप्पा}}" + "\n" +
    r"\newcommand{\Z}{\Th{Z}}" + "\n" +
    r"\newcommand{\Zminus}{\Z^{-}}", 1)

selected = prior_ns["selected"]
replace_tokens = prior_ns["replace_tokens"]
strip_wrapper = prior_ns["strip_wrapper"]
references = prior_ns["references"]
tag_references = prior_ns["tag_references"]
available = prior_ns["available"]
external = prior_ns["external"]
convert_section = prior_ns["convert_section"]
folder = ROOT / "mr/content/set-theory/z"
driver = selected((folder / "z.tex").read_text(encoding="utf-8"))
assert r"\olchapter{sth}{z}{$\Z$ कडे वाटचाल}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "story", "separation", "union", "pairs", "powerset",
    "infinity-again", "milestone", "nat", "arbintersections"
]
available.add("sth:z:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    raw = selected(path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1) == "sth" and match.group(2) == "z", path
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + x for x in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{$\Z$ कडे वाटचाल}\label{sth:z:chap}"]
cites = {
    r"\citet{Scott1974}": "Scott (1974)",
    r"\citet{ButtonLT1}": "Button (2021)",
    r"\citet{VonNeumann1925}": "फोन न्यूमन (1925)",
    r"\citeyear{Zermelo1908Untersuchungen}": "1908",
    r"\citet{Benacerraf1965}": "Benacerraf (1965)",
}
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = content.replace("!!{injection}", "एकास-एक फलन")
    content = content.replace("!!a{injection}", "एकास-एक फलन")
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: references(m, parts), content)
    content = re.sub(r"\\Olref\{([^}]+)\}",
        lambda m: r"\ref{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}",
        lambda m: " आणि ".join(r"\ref{" + x.strip() + "}" for x in m.group(1).split(",")),
        content)
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references, content, flags=re.S)
    for original, projection in cites.items():
        content = content.replace(original, projection)
    content = re.sub(
        r"\\citet\[Appendix\s+A\]\{Potter2004\}",
        "Potter (2004, Appendix A)", content
    )
    assert not re.search(r"\\cite(?:p|t|alt|author|year)?(?:\[[^]]*\])?\{", content)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref)", content
    )
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(marker) == 1
before, notes = base.split(marker, 1)
out = before + "\n".join(chunks) + "\n" + marker + notes
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
    lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0),
    out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
        .read_text(encoding="utf-8").splitlines() if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[536:546]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
    })
assert len(inputs) == 543 and inputs[-1]["unit_id"] == "OLP-0546"
assert out.count(r"\chapter{") == 59
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 470
assert "543 स्रोत-एकके आणि 470 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="543 source units, 470 reader sections, fifty-nine complete chapters",
    external_reference_labels=sorted(external),
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0537"]
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs), "sections": 470, "chapters": 59,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest()
}, ensure_ascii=False))
