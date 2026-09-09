"""Prepare the guarded reader through the completed tableaux chapter."""

import hashlib
import json
import re
import runpy
from pathlib import Path


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
ns = runpy.run_path(str(P / "tools" / "prepare_core94.py"))
base = (B / "openlogic-mr-core.tex").read_text(encoding="utf-8")

old_scope = (
    "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, "
    "विधानीय तर्कशास्त्र, सिद्धता-पद्धती, क्रमवर्ती कलन आणि नैसर्गिक निगमन"
)
new_scope = (
    "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, "
    "विधानीय तर्कशास्त्र, सिद्धता-पद्धती, क्रमवर्ती कलन, नैसर्गिक निगमन आणि टॅब्लो"
)
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
assert base.count("दहा संपूर्ण प्रकरणे") == 1
base = base.replace("दहा संपूर्ण प्रकरणे", "अकरा संपूर्ण प्रकरणे")
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0097, एकूण 94 स्रोत-एकके "
    "आणि 83 वाचक-विभाग. उर्वरित 628"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0111, एकूण 108 स्रोत-एकके "
    "आणि 96 वाचक-विभाग. उर्वरित 614"
)
assert old_coverage in base
base = base.replace(old_coverage, new_coverage)

selected = ns["selected"]
replace_tokens = ns["replace_tokens"]
strip_wrapper = ns["strip_wrapper"]
true_tags = ns["true_tags"]
available = set(ns["available"])

chapter_dir = P / "mr" / "content" / "first-order-logic" / "tableaux"
driver = selected((chapter_dir / "tableaux.tex").read_text(encoding="utf-8"))
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert editorial
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
expected_imports = [
    "rules-and-proofs", "propositional-rules", "quantifier-rules", "derivations",
    "proving-things", "proving-things-quant", "proof-theoretic-notions",
    "provability-consistency", "provability-propositional", "provability-quantifiers",
    "soundness", "identity", "soundness-identity",
]
assert imports == expected_imports, imports

chapter_label = "fol:tab::chap"
available.add(chapter_label)
file_texts = {}
prefixes = {}
for name in imports:
    text = selected((chapter_dir / f"{name}.tex").read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", text)
    assert file_id and file_id.groups()[:2] == ("fol", "tab"), name
    prefix = ":".join(file_id.groups())
    prefixes[name] = (list(file_id.groups()), prefix)
    file_texts[name] = text
    available.add(prefix + ":sec")
    available.update(prefix + ":" + key for key in re.findall(r"\\ollabel\{([^}]+)\}", text))

external_references = set()
# The tableaux source contains a few deliberately long Marathi/mathematical
# definition lines.  Give only this appended reader chapter a little extra
# emergency stretch so the accessible PDF does not emit overfull boxes; the
# aligned source files and their line-level layout remain unchanged.
chunks = [
    r"\chapter{टॅब्लो}\label{fol:tab::chap}\begingroup\setlength{\emergencystretch}{3em}"
    r"\NewDocumentCommand{\sFmlaWide}{m m o}{\ensuremath{\IfNoValueTF{#3}{}{#3\,}\hbox to 1.2em{\ensuremath{#1}\hfil} #2}}",
    replace_tokens(editorial.group()),
]
for name in imports:
    text = strip_wrapper(file_texts[name])
    parts, prefix = prefixes[name]
    text = text[: re.search(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", text).start()] + text[re.search(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", text).end() :]
    text = replace_tokens(text)
    text = re.sub(
        r"\\olsection\{([^{}]*)\}",
        lambda match: r"\section{" + match.group(1) + r"}\label{" + prefix + r":sec}",
        text,
    )
    text = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda match: r"\label{" + prefix + ":" + match.group(1) + "}",
        text,
    )

    def reference(match):
        options = re.findall(r"\[([^]]*)\]", match.group(1))
        assert len(options) <= 3
        key_parts = parts.copy()
        if options:
            key_parts[3 - len(options) :] = options
        key = ":".join(key_parts) + ":" + match.group(2)
        if key in available:
            return r"\ref{" + key + "}"
        external_references.add(key)
        return r"\readerexternalref{" + key + "}"

    text = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", reference, text)
    assert "!!" not in text, name
    assert not re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"usetoken|Article|olref|ollabel|olsection|olfileid)", text
    ), name
    chunks.append(text)

chunks.append(r"\endgroup")

before, notes = base.split(r"\chapter*{स्रोतावरील संपादकीय नोंदी}", 1)
notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
notes = notes_marker + notes
new_issue_notes = r"""
\item \textbf{OLTAB-001--OLTAB-004}: टॅब्लो प्रकरणातील आधीच्या
उदाहरणांमध्ये विषय, बंद पदांची अट आणि एका ओळ-संदर्भाशी संबंधित स्रोतदोष
दुरुस्त किंवा स्पष्ट केले आहेत; संरेखित इंग्रजी आणि मराठी स्रोत-बाइट्स जतन आहेत.
\item \textbf{OLTAB-005--OLTAB-009}: टॅब्लो सिद्धतायोग्यता आणि सुसंगतता
विभागातील संच-लेखन, नियम-पूर्वपद, ओळ-संदर्भ आणि शाखा-वर्णनातील निश्चित
स्रोतदोषांचे मराठी रूपात मर्यादित निराकरण केले आहे; मूळ इंग्रजी बाइट्स जतन आहेत.
\item \textbf{OLTAB-010}: विधानीय परिणामांच्या आठ टॅब्लो नोड्समधील
चिन्हांकित-सूत्र मॅक्रोची गहाळ युक्ती-सिमा पुनर्स्थापित केली आहे; संरेखित
स्रोतांत गोठवलेले रूप जतन आहे.
\item \textbf{OLTAB-011}: टॅब्लो निर्दोषता सिद्धतेतील सार्वत्रिक नियमांच्या
पुनरावृत्त B/A रूपबंध-विसंगतीत निष्कर्ष आणि अर्थविषयक पायऱ्यांशी सुसंगत
A-रूप वापरले आहे; गोठवलेले रूप संरेखित स्रोतांत जतन आहे.
\item \textbf{OLTAB-012}: एकरूपता-टॅब्लोच्या सममिती आणि संक्रमकता
स्पष्टीकरणांत लगतच्या वृक्षांशी विसंगत असलेली दोन कथनसूत्रे दुरुस्त केली आहेत;
औपचारिक वृक्ष अपरिवर्तित आहेत.
"""
assert r"\end{enumerate}" in notes
notes = notes.replace(r"\end{enumerate}", new_issue_notes + r"\end{enumerate}", 1)

out = before + "\n".join(chunks) + "\n" + notes
out = (
    out.replace(r"\formula{A}", r"\varphi")
    .replace(r"\formula{B}", r"\psi")
    .replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
)
# A marked-formula macro contains a fixed-width label box, so TeX cannot
# break the two long inline sequences in the tableaux definition by itself.
# Add reader-only break opportunities at those exact prose boundaries.
out = out.replace(
    r"$\sFmla{S_1}{\varphi_1}$, \dots, $\sFmla{S_n}{\varphi_n}$ या गृहीतकांसाठीचा",
    r"$\sFmla{S_1}{\varphi_1}$, \dots,\linebreak $\sFmla{S_n}{\varphi_n}$ या गृहीतकांसाठीचा",
)
out = out.replace(
    r"असलेली $\sFmla{S_i}{\varphi_i}$ ही सूत्रे होत.",
    r"असलेली\linebreak $\sFmla{S_i}{\varphi_i}$ ही सूत्रे होत.",
)
out = out.replace(r"\sFmla{S_1}{\varphi_1}", r"\sFmlaWide{S_1}{\varphi_1}")
out = out.replace(r"\sFmla{S_n}{\varphi_n}", r"\sFmlaWide{S_n}{\varphi_n}")
out = out.replace(r"\sFmla{S_i}{\varphi_i}", r"\sFmlaWide{S_i}{\varphi_i}")
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (P / "provenance" / "SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = []
for row in manifest[3:111]:
    path = P / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(P).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 108 and inputs[-1]["unit_id"] == "OLP-0111"
assert out.count(r"\chapter{") == 11
assert out.count(r"\section{") == 96
assert "!!" not in out
assert "The rules for" not in out
assert not re.search(r"![ABCD]", out)

(B / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
(B / "INPUTS.json").write_text(
    json.dumps(
        {
            "input_units": inputs,
            "scope": "108 source units, 96 reader sections, eleven complete chapters",
            "conditional_decisions": [],
            "tag_profile": {"true": sorted(true_tags)},
            "reader_projections": {
                "OLSEQ-001": "four antecedent-exchange labels rendered as left exchange",
                "OLSEQ-002": "two missing negations restored in explanatory candidate sequents",
                "OLTAB-001--OLTAB-012": "bounded tableaux source corrections disclosed in the editorial notes",
            },
            "source_issue_ids_added": [f"OLTAB-{i:03d}" for i in range(1, 13)],
            "external_reference_labels": sorted(external_references),
            "external_reference_rendering": "References to not-yet-included chapters are visibly described as a related section in the source book; their exact label remains in the editable reader source.",
            "source_issues": "Inherited notes through OLTAB-012; frozen English bytes remain unchanged.",
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs), "sections": 96, "chapters": 11, "external_references": len(external_references), "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
