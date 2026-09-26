"""Assemble 26 complete Marathi chapters through OLP-0273 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core260.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

old_scope = "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, प्रतिमान उपपत्ती, संगणनक्षमता आणि ट्यूरिंग यंत्रे"
new_scope = "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, प्रतिमान उपपत्ती, संगणनक्षमता, ट्यूरिंग यंत्रे आणि अनिर्णेयता"
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
assert base.count("पंचवीस संपूर्ण प्रकरणे") == 1
base = base.replace("पंचवीस संपूर्ण प्रकरणे", "सव्वीस संपूर्ण प्रकरणे", 1)
old_coverage = "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0263, एकूण 260 स्रोत-एकके आणि 230 वाचक-विभाग. उर्वरित 462"
new_coverage = "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0273, एकूण 270 स्रोत-एकके आणि 239 वाचक-विभाग. उर्वरित 452"
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]

folder = ROOT / "mr/content/turing-machines/undecidability"
driver = selected((folder / "undecidability.tex").read_text(encoding="utf-8"))
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert len(imports) == 9, imports
chapter_label = "tur:und::chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.groups()[:2] == ("tur", "und"), path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))

external.difference_update(available)
chunks = [r"\chapter{अनिर्णेयता}\label{" + chapter_label + "}"]
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
if editorial:
    chunks.append(replace_tokens(editorial.group()))
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = replace_tokens(content)
    content, converted = re.subn(
        r"\\olsection(?:\[[^]]*\])?\{([^{}]*)\}",
        lambda m: r"\section{" + m.group(1) + r"}\label{" + prefix + ":sec}",
        content,
    )
    assert converted == 1, (name, converted)
    content = re.sub(r"\\ollabel\{([^}]+)\}", lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", lambda m: references(m, parts), content)
    content = re.sub(r"\\Olref\{([^}]+)\}", lambda m: r"\ref{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:c|C)ref\{([^}]+)\}", lambda m: " आणि ".join(r"\ref{" + item.strip() + "}" for item in m.group(1).split(",")), content)
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tag_references, content, flags=re.S)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|usetoken|printtoken|Article|article|olref|Olref|ollabel|olsection|olfileid|tagrefs|Cref|cref)", content)
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
und_note = r"""
\item \textbf{OLTUR-008--OLTUR-022}: अनिर्णेयता आणि सांत प्रतिरूपांच्या
प्रकरणातील स्रोत-निरीक्षणे संबंधित मराठी मजकुरालगत दिली आहेत. विशेषतः
यंत्र-चालक्रमाचे निरूपण, शेवटच्या पायरीचे स्थितिवर्णन आणि सांत प्रतिरूपाची
मर्यादा यांतील दुरुस्त्या मूळ इंग्रजी मजकूर न बदलता नोंदवल्या आहेत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", und_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
out = (
    out.replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
    .replace("!T", r"\mathsf{T}")
    .replace("!E", r"\mathsf{E}")
)

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[263:273]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 270 and inputs[-1]["unit_id"] == "OLP-0273"
assert out.count(r"\chapter{") == 26
assert out.count(r"\section{") == 239
assert "270 स्रोत-एकके आणि 239 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCD]", out), (
    re.findall(r".{0,45}!!.{0,45}", out)[:8],
    re.findall(r".{0,45}![ABCD].{0,45}", out)[:8],
)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="270 source units, 239 reader sections, twenty-six complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [f"OLTUR-{i:03d}" for i in range(8, 23)],
    chapter_driver_units_not_rendered_as_sections=prior.get("chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0264"],
    reader_symbol_projections={"!A": r"\varphi", "!B": r"\psi", "!C": r"\chi", "!D": r"\theta", "!T": r"\mathsf{T}", "!E": r"\mathsf{E}"},
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs), "sections": 239, "chapters": 26, "external_references": len(external), "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
