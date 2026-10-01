"""Assemble 53 complete Marathi chapters through OLP-0502 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core497.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("बावन्न संपूर्ण प्रकरणे") == 1
base = base.replace("बावन्न संपूर्ण प्रकरणे", "त्रेपन्न संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0497, एकूण 494 स्रोत-एकके "
    "आणि 430 वाचक-विभाग. उर्वरित 228"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0502, एकूण 499 स्रोत-एकके "
    "आणि 434 वाचक-विभाग. उर्वरित 223"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

for command in (r"\newcommand{\Top}", r"\newcommand{\Interior}", r"\newcommand{\Prop}"):
    assert command not in base
macro_anchor = r"\newcommand{\mModel}[1]{\applytofirst{\mathfrak}{#1}}"
assert base.count(macro_anchor) == 1
topology_macros = "\n".join((
    r"\newcommand{\Top}[1]{\mathcal{#1}}",
    r"\newcommand{\Interior}[1]{\mathrm{Int}(#1)}",
    r"\newcommand{\Prop}[2]{{[\!\![} #2 {]\!\!]_{\mModel{#1}}}}",
))
base = base.replace(macro_anchor, macro_anchor + "\n" + topology_macros, 1)

selected_modal = prior_namespace["selected_modal"]
replace_tokens = prior_namespace["replace_tokens"]
token_scope = replace_tokens.__globals__
assert "relational model" not in token_scope["singular"]
token_scope["singular"]["relational model"] = "संबंधी प्रतिमान"
token_scope["plural"]["relational model"] = "संबंधी प्रतिमाने"
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/intuitionistic-logic/semantics"
driver = selected_modal((folder / "semantics.tex").read_text(encoding="utf-8"))
assert r"\olchapter{int}{sem}{चिन्हार्थमीमांसा}" in driver
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert editorial
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "relational-models",
    "semantic-notions",
    "topological-semantics",
]
available.add("int:sem:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected_modal(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["int", "sem"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

chunks = [
    r"\chapter{चिन्हार्थमीमांसा}\label{int:sem:chap}",
    replace_tokens(editorial.group()),
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}", lambda match: r"\label{" + prefix + ":" + match.group(1) + "}", content)
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", lambda match: references(match, parts), content)
    content = re.sub(r"\\Olref\{([^}]+)\}", lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}", content)
    content = re.sub(
        r"\\(?:c|C)ref\{([^}]+)\}",
        lambda match: " आणि ".join(r"\ref{" + item.strip() + "}" for item in match.group(1).split(",")),
        content,
    )
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tag_references, content, flags=re.S)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref)",
        content,
    )
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(notes_marker) == 1
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_note = r"""
\item \textbf{OLINC-217}: मूळ इंग्रजीत
स्थानिक निष्पन्नतेच्या दाव्याच्या सिद्धतेत
सर्व जगांतील सत्यतेचे अधिक बळकट गृहीतक
वापरले आहे; मराठीत आधी स्थानिक दावा
सिद्ध करून मग त्यावरून सर्व जगांतील
दावा मिळवला आहे.
\item \textbf{OLINC-218}: मूळ इंग्रजीत एका
ठिकाणी मूळ संच \(X\) लाच संस्थिति म्हटले
आहे. व्याख्येनुसार \(\mathcal O\) ही संस्थिति
आणि तिच्यासह \(X\) हा सांस्थितिक अवकाश आहे;
मराठीत हा भेद ठेवला आहे.
\item \textbf{OLINC-219}: मूळ इंग्रजीत
निष्पन्नता आणि सशर्त विधानाच्या दोन
अटींमध्ये \(\subset\) चिन्ह आहे.
या चिन्हाचा अर्थ संकेतपद्धतीनुसार बदलतो;
येथे समानताही चालते हे स्पष्ट करण्यासाठी
मराठीत \(\subseteq\) वापरले आहे.
उचित उपसंचच अभिप्रेत असल्याचा जुना
दोष-दावा मागे घेतला आहे.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(
    r"\\readerexternalref\{([^}]+)\}",
    lambda match: r"\ref{" + match.group(1) + "}" if match.group(1) in available else match.group(0),
    out,
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[497:502]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 499 and inputs[-1]["unit_id"] == "OLP-0502"
assert out.count(r"\chapter{") == 53
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 434
assert "499 स्रोत-एकके आणि 434 वाचक-विभाग" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="499 source units, 434 reader sections, fifty-three complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [
        "OLINC-217", "OLINC-218", "OLINC-219"
    ],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0498"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 434,
    "chapters": 53,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
