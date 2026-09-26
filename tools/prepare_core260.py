"""Assemble 25 complete Marathi chapters through OLP-0263 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core248.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

old_scope = "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, प्रतिमान उपपत्ती आणि संगणनक्षमता"
new_scope = "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, प्रतिमान उपपत्ती, संगणनक्षमता आणि ट्यूरिंग यंत्रे"
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
assert base.count("चोवीस संपूर्ण प्रकरणे") == 1
base = base.replace("चोवीस संपूर्ण प्रकरणे", "पंचवीस संपूर्ण प्रकरणे", 1)
old_coverage = "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0251, एकूण 248 स्रोत-एकके आणि 220 वाचक-विभाग. उर्वरित 474"
new_coverage = "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0263, एकूण 260 स्रोत-एकके आणि 230 वाचक-विभाग. उर्वरित 462"
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

tm_macros = r"""
\usetikzlibrary{automata}
\newcommand{\TMendtape}{\triangleright}
\newcommand{\TMblank}{0}
\newcommand{\TMstroke}{1}
\newcommand{\TMright}{R}
\newcommand{\TMleft}{L}
\newcommand{\TMstay}{N}
\NewDocumentCommand{\TMtrans}{m m m}{\ensuremath{#1, #2, #3}}
\newcommand{\fn}[1]{\mathrm{#1}}
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", tm_macros + r"\begin{document}", 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]

folder = ROOT / "mr/content/turing-machines/machines-computations"
driver = selected((folder / "machines-computations.tex").read_text(encoding="utf-8"))
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert len(imports) == 10, imports
chapter_label = "tur:mac::chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id, path
    parts = list(file_id.groups())
    # The frozen configuration section carries the inherited cmp/tur/con ID.
    # Keep it for all existing references and labels; its file path and chapter
    # driver, rather than the mismatched ID, determine reader placement.
    assert (parts[:2] == ["tur", "mac"]) or (name == "configuration" and parts == ["cmp", "tur", "con"]), path
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))

chunks = [r"\chapter{ट्यूरिंग यंत्रांवरील संगणने}\label{" + chapter_label + "}"]
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
tm_note = r"""
\item \textbf{OLTUR-001--OLTUR-007}: ट्यूरिंग यंत्रांच्या उदाहरणांतील
आरंभीची अवस्था, फितीचे टोक, रिकामे आदान, प्रदान आणि यंत्र-संयोजन
यांबद्दलची सात स्रोत-निरीक्षणे संरेखित स्रोतांत नोंदवली आहेत. मूळ
इंग्रजी बाइट्स जतन आहेत; मराठी वाचक-मजकूर मर्यादित स्पष्टता वापरतो.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", tm_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[251:263]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 260 and inputs[-1]["unit_id"] == "OLP-0263"
assert out.count(r"\chapter{") == 25
assert out.count(r"\section{") == 230
assert "260 स्रोत-एकके आणि 230 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCD]", out)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="260 source units, 230 reader sections, twenty-five complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [f"OLTUR-{i:03d}" for i in range(1, 8)],
    part_driver_units_not_rendered_as_sections=prior.get("part_driver_units_not_rendered_as_sections", []) + ["OLP-0252"],
    inherited_file_id_exception={"unit_id": "OLP-0257", "path": "mr/content/turing-machines/machines-computations/configuration.tex", "file_id": "cmp/tur/con"},
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs), "sections": 230, "chapters": 25, "external_references": len(external), "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
