"""Assemble 57 complete Marathi chapters through OLP-0528 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
prior_namespace = runpy.run_path(str(ROOT / "tools/prepare_core521.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("छप्पन्न संपूर्ण प्रकरणे") == 1
base = base.replace("छप्पन्न संपूर्ण प्रकरणे", "सत्तावन्न संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0521, एकूण 518 स्रोत-एकके "
    "आणि 449 वाचक-विभाग. उर्वरित 204"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0528, एकूण 525 स्रोत-एकके "
    "आणि 455 वाचक-विभाग. उर्वरित 197"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
tikz_anchor = r"\usepackage{amsmath,amssymb,amsthm,nicefrac,graphicx,tikz}"
assert base.count(tikz_anchor) == 1
assert r"\usepackage{../../upstream/sty/ptolemaicastronomy}" not in base
base = base.replace(
    tikz_anchor,
    tikz_anchor + "\n" + r"\usepackage{../../upstream/sty/ptolemaicastronomy}",
    1,
)
assert r"\newcommand{\cif}" not in base
strict_anchor = r"\newcommand{\strictif}{\fishhookright}"
assert base.count(strict_anchor) == 1
assert r"\DeclareMathSymbol{\boxright}" not in base
base = base.replace(
    strict_anchor,
    strict_anchor + "\n"
    + r"\DeclareMathSymbol{\boxright}{\mathbin}{symbolsC}{128}" + "\n"
    + r"\newcommand{\cif}{\boxright}",
    1,
)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/counterfactuals/minimal-change-semantics"
driver = selected((folder / "minimal-change-semantics.tex").read_text(encoding="utf-8"))
assert r"\olchapter{cnt}{min}{किमान बदलाची चिन्हार्थमीमांसा}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction", "sphere-models", "true-false",
    "antecedent-strengthening", "transitivity", "contraposition",
]
available.add("cnt:min:chap")
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.group(2) == "min" and file_id.group(1) in {"cnt", "con"}, path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

chunks = [r"\chapter{किमान बदलाची चिन्हार्थमीमांसा}\label{cnt:min:chap}"]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda match: r"\label{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", lambda match: references(match, parts), content)
    content = re.sub(
        r"\\Olref\{([^}]+)\}",
        lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}",
        content,
    )
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
new_notes = r"""
\item \textbf{OLINC-239}: गोलक प्रतिमानाच्या
सत्यता-अटीतील ‘‘एखाद्या गोलकात
अट पूर्ण झाली, तर त्यातील
सर्व लहान गोलकांतही होते’’
हा मूळ इंग्रजी दावा अति-विस्तृत
आहे. पूर्वांग सत्य असलेले जग
धारण करणाऱ्या लहान गोलकांपुरताच
तो मराठीत मर्यादित केला आहे.
\item \textbf{OLINC-240}: बाह्य अवकाशातील
आगकाडीच्या उदाहरणात मूळ गद्य
दोनदा ‘‘पेटवणे’’ म्हणते; उद्धृत
अनुमान आणि अपेक्षित प्रयोग
यांच्यानुसार मराठीत ‘‘ओढणे’’
वापरले आहे.
\item \textbf{OLINC-241}: संक्रमणकतेच्या
प्रतिमानात \(q\lif r\) सर्व
संबंधित जगांत सत्य असूनही
मूळ सूत्रात पूर्तिचिन्हावर
निषेध आहे. मराठीत तो
निषेध काढला आहे.
\item \textbf{OLINC-242}: प्रतिपरिवर्तनाच्या
प्रतिमानात मूळ इंग्रजीत
एका जगाभोवतीची गोलक-प्रणाली
संपूर्ण फलन \(O\) म्हणून,
आणि घोषित \(M_1\) प्रतिमान
पुढे \(M\) म्हणून आले आहे;
मराठीत \(O_w\) व \(M_1\)
अशी सुसंगत नावे दिली आहेत.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_notes + r"\end{enumerate}", 1)
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
for row in manifest[521:528]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 525 and inputs[-1]["unit_id"] == "OLP-0528"
assert out.count(r"\chapter{") == 57
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 455
assert "525 स्रोत-एकके आणि 455 वाचक-विभाग" in out
assert "OLINC-242" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="525 source units, 455 reader sections, fifty-seven complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [
        "OLINC-239", "OLINC-240", "OLINC-241", "OLINC-242",
    ],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0522"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 455,
    "chapters": 57,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
