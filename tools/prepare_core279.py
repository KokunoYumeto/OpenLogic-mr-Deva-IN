"""Assemble 27 complete Marathi chapters through OLP-0279 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core273.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

old_scope = "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, प्रतिमान उपपत्ती, संगणनक्षमता, ट्यूरिंग यंत्रे आणि अनिर्णेयता"
new_scope = "संच व फलने, अनंत संच, विधानीय व प्रथम-क्रम तर्कशास्त्र, प्रतिमान उपपत्ती, संगणनक्षमता, ट्यूरिंग यंत्रे, अनिर्णेयता आणि अपूर्णता"
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
assert base.count("सव्वीस संपूर्ण प्रकरणे") == 1
base = base.replace("सव्वीस संपूर्ण प्रकरणे", "सत्तावीस संपूर्ण प्रकरणे", 1)
old_coverage = "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0273, एकूण 270 स्रोत-एकके आणि 239 वाचक-विभाग. उर्वरित 452"
new_coverage = "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0279, एकूण 276 स्रोत-एकके आणि 243 वाचक-विभाग. उर्वरित 446"
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
assert base.count(r"\setlength{\emergencystretch}{2em}") == 1
base = base.replace(r"\setlength{\emergencystretch}{2em}", r"\setlength{\emergencystretch}{3em}", 1)
assert base.count(r"\renewcommand{\chaptername}{प्रकरण}") == 1
base = base.replace(r"\renewcommand{\chaptername}{प्रकरण}", r"\renewcommand{\chaptername}{प्रकरण}" + "\n" + r"\renewcommand{\partname}{भाग}" + "\n" + r"\renewcommand{\thepart}{\arabic{part}}", 1)

extra_macros = r"""
\newcommand{\Zero}{\fn{zero}}
\newcommand{\Succ}{\fn{succ}}
\newcommand{\Add}{\fn{add}}
\newcommand{\Mult}{\fn{mult}}
\NewDocumentCommand{\Proj}{m m}{P^{#1}_{#2}}
\newcommand{\tsub}{\mathbin{\dot-}}
\newcommand{\defiff}{\Leftrightarrow}
\NewDocumentCommand{\umin}{m m}{\mu #1\;#2}
\NewDocumentCommand{\bmin}{m m}{(\fn{min}\;#1)\,#2}
\NewDocumentCommand{\bexists}{m m}{(\exists #1)\;#2}
\NewDocumentCommand{\bforall}{m m}{(\forall #1)\;#2}
\NewDocumentCommand{\cfind}{m o}{\IfNoValueTF{#2}{\varphi_{#1}}{\varphi_{#1}^{#2}}}
\NewDocumentCommand{\Complement}{m}{\overline{#1}}
\NewDocumentCommand{\fact}{m}{#1\,!}
\newcommand{\Char}[1]{\chi_{#1}}
\NewDocumentCommand{\Prov}{o}{\mathrm{Prov}\IfNoValueF{#1}{_{#1}}}
\NewDocumentCommand{\OProv}{o}{\mathsf{Prov}\IfNoValueF{#1}{_{#1}}}
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", extra_macros + r"\begin{document}", 1)
assert base.count(r"\usepackage{stmaryrd}") == 1
base = base.replace(r"\usepackage{stmaryrd}", r"\usepackage{stmaryrd}" + "\n" + r"\usepackage{mathdots}", 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
lexicon = replace_tokens.__globals__["singular"]
lexicon.update({
    "axiomatizability": "निर्णेय स्वयंसिद्धकसंचाने निरूपणयोग्यता",
    "axiomatizable": "निर्णेय स्वयंसिद्धकसंचाने निरूपणयोग्य",
    "decidable": "निर्णेय",
    "represents": "निरूपण",
})
replace_tokens.__globals__["plural"].update({"represents": "निरूपण"})

part = selected((ROOT / "mr/content/incompleteness/incompleteness.tex").read_text(encoding="utf-8"))
part_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", part, re.S)
assert part_note
folder = ROOT / "mr/content/incompleteness/introduction"
driver = selected((folder / "introduction.tex").read_text(encoding="utf-8"))
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["historical-background", "definitions", "overview", "undecidability"]
chapter_label = "inc:int::chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.groups()[:2] == ("inc", "int"), path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))

external.difference_update(available)
chunks = [r"\part{अपूर्णता}", r"\chapter{अपूर्णतेचा परिचय}\label{" + chapter_label + "}", replace_tokens(part_note.group())]
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
inc_note = r"""
\item \textbf{OLINC-001--OLINC-005}: अपूर्णतेच्या परिचयातील उद्दिष्टांची
क्रमवारी, प्रमेयांच्या गृहीतकांची व्याप्ती आणि संबंध-निरूपणातील उपपत्तीचा
निर्देश यांसंबंधीची निरीक्षणे नोंदवली आहेत. विकर्ण सिद्धतेतील दोन
वगळलेले निर्देशांक आणि विस्तारित उपपत्तींच्या सुसंगततेची अट मराठीत
स्पष्ट केली आहे; मूळ इंग्रजी मजकूर बदललेला नाही.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", inc_note + r"\end{enumerate}", 1)
assert notes.count(r"\item \textbf{OLCMP-001--OLCMP-024}:") == 1
notes = notes.replace(r"\item \textbf{OLCMP-001--OLCMP-024}:", r"\item \textbf{OLCMP-001--OLCMP-024}:\par", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
out = (
    out.replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
    .replace("!G", r"\mathsf{G}")
    .replace("!Q", r"\mathsf{Q}")
)
out = out.replace("स्वयंसिद्धकांनी निरूपणयोग्य निर्णेय स्वयंसिद्धकसंचाने निरूपणयोग्य", "निर्णेय स्वयंसिद्धकसंचाने निरूपणयोग्य")
out = out.replace(r"\emph{निरूपण} तेव्हाच की", r"\emph{निरूपण करते} तेव्हाच की")
out = out.replace("ची निष्पन्न करते", "निष्पन्न करते")
out = out.replace(r"\olasset{\olpath/assets/", r"\olasset{assets/")

manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[273:279]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 276 and inputs[-1]["unit_id"] == "OLP-0279"
assert out.count(r"\chapter{") == 27
assert out.count(r"\section{") == 243
assert "276 स्रोत-एकके आणि 243 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![ABCDGQ]", out)

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="276 source units, 243 reader sections, twenty-seven complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [f"OLINC-{i:03d}" for i in range(1, 6)],
    chapter_driver_units_not_rendered_as_sections=prior.get("chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0275"],
    part_driver_units_not_rendered_as_sections=prior.get("part_driver_units_not_rendered_as_sections", []) + ["OLP-0274"],
    reader_symbol_projections={**prior.get("reader_symbol_projections", {}), "!G": r"\mathsf{G}", "!Q": r"\mathsf{Q}"},
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs), "sections": 243, "chapters": 27, "external_references": len(external), "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
