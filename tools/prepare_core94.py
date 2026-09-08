"""Prepare the ten-chapter reader through OLP-0097 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
ns = runpy.run_path(str(P / "tools" / "prepare_core65.py"))
base = (B / "openlogic-mr-core.tex").read_text(encoding="utf-8")

old_scope = (
    "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, "
    "विधानीय तर्कशास्त्र आणि सिद्धता-पद्धती"
)
new_scope = (
    "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, "
    "विधानीय तर्कशास्त्र, सिद्धता-पद्धती, क्रमवर्ती कलन आणि नैसर्गिक निगमन"
)
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
base = base.replace("आठ संपूर्ण प्रकरणे", "दहा संपूर्ण प्रकरणे")
old_coverage = (
    "मूळ 722 विभागांपैकी OLP-0004 ते OLP-0068, एकूण 65 स्रोत-एकके "
    "आणि 56 वाचक-विभाग. उर्वरित 657"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0097, एकूण 94 स्रोत-एकके "
    "आणि 83 वाचक-विभाग. उर्वरित 628"
)
assert old_coverage in base
base = base.replace(old_coverage, new_coverage)

old_package = r"\usepackage{bussproofs}"
new_package = r"\usepackage{../../upstream/sty/bussproofs-extra}"
assert base.count(old_package) == 1
base = base.replace(old_package, new_package, 1)

additional_macros = r"""
\NewDocumentCommand{\lexists}{t{!} o o}{%
  \exists\IfBooleanT{#1}{\mathord{!}}%
  \IfNoValueF{#2}{#2}\IfNoValueF{#3}{\,#3}}
\NewDocumentCommand{\lforall}{o o}{%
  \IfNoValueTF{#1}{\forall}{\forall #1}\IfNoValueF{#2}{\,#2}}
\NewDocumentCommand{\eq}{t{/} o o}{%
  \IfNoValueTF{#3}{\IfBooleanTF{#1}{\neq}{=}}{%
    \IfBooleanTF{#1}{#2\neq#3}{#2=#3}}}
\NewDocumentCommand{\Atom}{m m}{\mathord{#1}(#2)}
\NewDocumentCommand{\Assign}{m m}{\mathord{#1^{\Struct{#2}}}}
\NewDocumentCommand{\Sat}{t{/} m m o}{%
  \IfBooleanTF{#1}{%
    \IfNoValueTF{#4}{\Struct{#2}\nvDash#3}{\Struct{#2},#4\nvDash#3}}{%
    \IfNoValueTF{#4}{\Struct{#2}\vDash#3}{\Struct{#2},#4\vDash#3}}}
\NewDocumentCommand{\varAssign}{m m m o}{%
  \IfNoValueTF{#4}{#1\sim_{#3}#2}{#1=#2[^{#4}/#3]}}
\NewDocumentCommand{\Value}{m m o}{%
  \IfNoValueTF{#3}{\mathrm{Val}^{\Struct{#2}}(#1)}{%
    \mathrm{Val}^{\Struct{#2}}_{#3}(#1)}}
\NewDocumentCommand{\Log}{m o}{%
  \ensuremath{\mathbf{#1}\IfNoValueF{#2}{_{#2}}}}
\newcommand{\Contraction}{\ensuremath{\mathrm{C}}}
\newcommand{\Exchange}{\ensuremath{\mathrm{X}}}
\newcommand{\Cut}{\ensuremath{\mathrm{Cut}}}
\newcommand{\FalseCl}{\ensuremath{\lfalse_C}}
\newenvironment{defish}{}{}
\newcommand{\readerexternalref}[1]{\textit{मूळ ग्रंथातील संबंधित विभाग}}
\makeatletter
\renewcommand{\@pnumwidth}{2em}
\renewcommand*{\l@section}{\@dottedtocline{1}{1.5em}{2.8em}}
\makeatother
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", additional_macros + r"\begin{document}", 1)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes

select_tags = ns["select_tags"]
replace_proof_tokens = ns["replace_tokens"]
true_tags = ns["true_tags"]
true_tags.add("FOL")


def tag_value(tag):
    tag = tag.strip()
    return tag[3:] not in true_tags if tag.startswith("not") else tag in true_tags


def select_tagprobs(text):
    pattern = re.compile(r"\\tagprob\{([^}]*)\}(.*?)\\tagendprob", re.S)
    while pattern.search(text):
        text = pattern.sub(
            lambda match: match.group(2)
            if any(tag_value(tag) for tag in match.group(1).split(","))
            else "",
            text,
            count=1,
        )
    return text


extra_singular = {
    "constant": "स्थिरांक",
    "identity": "एकरूपता",
    "main operator": "मुख्य संकारक",
    "nonderivability": "अनिष्पन्नता",
    "operator": "संकारक",
    "valuation": "सत्य-मूल्यांकन",
    "variable": "चल",
}
extra_plural = {
    "constant": "स्थिरांक",
    "operator": "संकारक",
    "valuation": "सत्य-मूल्यांकने",
    "variable": "चले",
}


def replace_extra_match(match):
    token = re.sub(r"\s+", " ", match.group("token")).strip()
    if token not in extra_singular:
        return match.group(0)
    suffix = match.group("suffix") or ""
    assert suffix != "d", token
    return extra_plural.get(token, extra_singular[token]) if suffix == "s" else extra_singular[token]


def replace_tokens(text):
    replacements = {
        r"\usetoken{S}{identity}": "एकरूपता",
        r"\usetoken{P}{identity}": "एकरूपता",
        r"\usetoken{S}{derivability}": "निष्पन्नता",
        r"\usetoken{P}{derivability}": "निष्पन्नता",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(
        r"!!(?:\^?a|\^)?\{(?P<token>[^{}]+)\}(?P<suffix>s|d)?",
        replace_extra_match,
        text,
        flags=re.S,
    )
    text = replace_proof_tokens(text)
    text = re.sub(r"\\Article\{[^{}]+\}\s*", "", text)
    grammar = {
        "वाक्ये ना": "वाक्यांना",
        "सत्य-मूल्यांकने चा": "सत्य-मूल्यांकनांचा",
        "सत्य-मूल्यांकने ची": "सत्य-मूल्यांकनांची",
        "सत्य-मूल्यांकने चे": "सत्य-मूल्यांकनांचे",
        "सत्य-मूल्यांकने च्या": "सत्य-मूल्यांकनांच्या",
        "चले चा": "चलांचा",
        "चले ची": "चलांची",
        "चले चे": "चलांचे",
        "चले च्या": "चलांच्या",
        "स्थिरांक चा": "स्थिरांकाचा",
        "स्थिरांक ची": "स्थिरांकाची",
        "स्थिरांक चे": "स्थिरांकाचे",
        "स्थिरांक च्या": "स्थिरांकाच्या",
    }
    for old, new in grammar.items():
        text = text.replace(old, new)
    return text


chapters = [
    {
        "key": "seq",
        "title": "क्रमवर्ती कलन",
        "label": "fol:seq::chap",
        "directory": P / "mr" / "content" / "first-order-logic" / "sequent-calculus",
        "driver": "sequent-calculus.tex",
        "imports": [
            "rules-and-proofs",
            "propositional-rules",
            "quantifier-rules",
            "structural-rules",
            "derivations",
            "proving-things",
            "proving-things-quant",
            "proof-theoretic-notions",
            "provability-consistency",
            "provability-propositional",
            "provability-quantifiers",
            "soundness",
            "identity",
            "soundness-identity",
        ],
    },
    {
        "key": "ntd",
        "title": "नैसर्गिक निगमन",
        "label": "fol:ntd::chap",
        "directory": P / "mr" / "content" / "first-order-logic" / "natural-deduction",
        "driver": "natural-deduction.tex",
        "imports": [
            "rules-and-proofs",
            "propositional-rules",
            "quantifier-rules",
            "derivations",
            "proving-things",
            "proving-things-quant",
            "proof-theoretic-notions",
            "provability-consistency",
            "provability-propositional",
            "provability-quantifiers",
            "soundness",
            "identity",
            "soundness-identity",
        ],
    },
]


def selected(text):
    text = re.sub(r"(?<!\\)%[^\n]*(?:\n|$)", "\n", text)
    return select_tags(select_tagprobs(text))


def strip_wrapper(text):
    text = re.sub(r"(?m)^[ \t]*%[^\n]*(?:\n|$)", "", text)
    text = re.sub(r"\\documentclass[^\n]*\n", "", text)
    return text.replace(r"\begin{document}", "").replace(r"\end{document}", "")


available = set(re.findall(r"\\label\{([^}]+)\}", before))
for chapter in chapters:
    available.add(chapter["label"])
    driver_text = selected(
        (chapter["directory"] / chapter["driver"]).read_text(encoding="utf-8")
    )
    imports = re.findall(r"\\olimport\{([^}]+)\}", driver_text)
    assert imports == chapter["imports"], (chapter["key"], imports)
    for name in imports:
        text = selected((chapter["directory"] / f"{name}.tex").read_text(encoding="utf-8"))
        file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", text)
        assert file_id and file_id.groups()[:2] == ("fol", chapter["key"]), name
        prefix = ":".join(file_id.groups())
        available.add(prefix + ":sec")
        available.update(prefix + ":" + key for key in re.findall(r"\\ollabel\{([^}]+)\}", text))

external_references = set()
projection_counts = {"OLSEQ-001": 0, "OLSEQ-002": 0}


def project_sequent_source_issues(name, text):
    if name != "proving-things":
        return text
    exchange_pattern = re.compile(
        r"(\\BinaryInf\$\s*\\lnot !A \\lor !B, !A \\fCenter !B\s*\$\s*)"
        r"\\RightLabel\{\\RightR\{\\Exchange\}\}"
    )
    text, projection_counts["OLSEQ-001"] = exchange_pattern.subn(
        r"\1\\RightLabel{\\LeftR{\\Exchange}}", text
    )
    anchor = r"आता \LeftR{\land} नियम पाहायचा"
    start = text.index(anchor)
    end = text.index("निवडू:", start) + len("निवडू:")
    paragraph = text[start:end]
    assert paragraph.count(r"\lnot !A \lor !B") == 2
    paragraph = paragraph.replace(r"\lnot !A \lor !B", r"\lnot !A \lor \lnot !B")
    projection_counts["OLSEQ-002"] = 2
    return text[:start] + paragraph + text[end:]


chunks = []
processed_ids = []
for chapter in chapters:
    chunks.append(r"\chapter{" + chapter["title"] + r"}\label{" + chapter["label"] + "}")
    driver_text = (chapter["directory"] / chapter["driver"]).read_text(encoding="utf-8")
    editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver_text, re.S)
    assert editorial
    chunks.append(replace_tokens(editorial.group()))
    for name in chapter["imports"]:
        text = strip_wrapper((chapter["directory"] / f"{name}.tex").read_text(encoding="utf-8"))
        text = selected(text)
        file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", text)
        assert file_id and file_id.groups()[:2] == ("fol", chapter["key"]), name
        prefix_parts = list(file_id.groups())
        prefix = ":".join(prefix_parts)
        processed_ids.append(prefix)
        text = text[: file_id.start()] + text[file_id.end() :]
        text = replace_tokens(text)
        text = project_sequent_source_issues(name, text) if chapter["key"] == "seq" else text
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
            parts = prefix_parts.copy()
            if options:
                parts[3 - len(options) :] = options
            key = ":".join(parts) + ":" + match.group(2)
            if key in available:
                return r"\ref{" + key + "}"
            external_references.add(key)
            return r"\readerexternalref{" + key + "}"

        text = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", reference, text)
        assert "!!" not in text, (chapter["key"], name)
        assert not re.search(
            r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
            r"usetoken|Article|olref|ollabel|olsection|olfileid)",
            text,
        ), (chapter["key"], name)
        chunks.append(text)

assert projection_counts == {"OLSEQ-001": 4, "OLSEQ-002": 2}

new_issue_notes = r"""
\item \textbf{OLSEQ-001}: OLP-0075 मधील चार पायऱ्यांत पूर्वपक्षातील
सूत्रांची अदलाबदल असूनही नियम-खूण उजवी अदलाबदल अशी आहे. या वाचकात त्या
चार खुणा डावी अदलाबदल अशा केल्या आहेत; संरेखित स्रोतांत मूळ रूप जतन आहे.
\item \textbf{OLSEQ-002}: त्याच उदाहरणातील दोन कथनसूत्रांत दुसऱ्या
सूत्रापूर्वीचे नकारचिन्ह गाळले आहे. लगतचे ध्येय, सममितीचे स्पष्टीकरण आणि
सिद्धता-वृक्ष यांनुसार या वाचकात ती दोन नकारचिन्हे पुनःस्थापित केली आहेत.
\item \textbf{OLSEQ-003}: OLP-0072 च्या शेवटच्या परिच्छेदातील ``पदावर
निर्बंध नाही'' याचा अर्थ पद बंद असण्याव्यतिरिक्त आणखी निर्बंध नाही असा आहे;
मराठी मजकूर ही आधी स्पष्ट केलेली अट सांगतो.
\item \textbf{OLND-001}: OLP-0087 मध्येही संख्यापक-नियमांसाठी पद बंद
असण्याची उभी अट शेवटच्या स्पष्टीकरणात स्पष्ट केली आहे.
\item \textbf{OLND-002}: OLP-0087 मधील आयगेन चलाचा एकत्रित सारांश सर्व
आधारविधानांतून चल वगळल्यासारखा वाचतो; मराठी सारांश प्रत्येक नियमाची योग्य
आधारविधान, निष्कर्ष आणि अमुक्त गृहीतकांची अट वेगवेगळी राखतो.
\item \textbf{OLND-003}: OLP-0089 मध्ये आकृतीतील उजवी शाखा चुकून डावी
म्हटली आहे; वाचकात आकृती आणि पुढील परिच्छेदाशी सुसंगत ``उजवीकडील'' आहे.
\item \textbf{OLND-004}: OLP-0089 मधील एकच अनुमान कधी नकार-विलोपन तर
कधी असत्यता-प्रवेशन असे खूणांकित आहे. अनुमान अर्थतः समान असल्याने मूळची
पर्यायी खूण जतन केली आहे.
\item \textbf{OLND-005}: OLP-0090 मधील आयगेन-चल तपासणीत मुख्य
आधारविधानातील नकार गाळला आहे आणि नियमाची व्याप्ती अपुरी सांगितली आहे;
मराठी मजकूर योग्य नकार व तात्पुरत्या गृहीतकाचा अपवाद स्पष्ट करतो.
\item \textbf{OLND-006}: OLP-0090 मधील सार्वत्रिक विलोपनासाठी ``कोणतेही
पद'' म्हणजे उभ्या नियमानुसार कोणतेही बंद पद; मराठी स्पष्टीकरण ती अट राखते.
\item \textbf{OLND-007}: OLP-0095 च्या एका सरावातील नियम-खूण
\verb|\Elim{\forall}| ही प्रकरणात इतरत्र असलेल्या
\verb|\Elim{\lforall}| शी दृश्यतः समतुल्य आहे. संरेखित रूप जतन केले आहे.
"""
assert r"\end{enumerate}" in notes
notes = notes.replace(r"\end{enumerate}", new_issue_notes + r"\end{enumerate}", 1)

out = before + "\n".join(chunks) + "\n" + notes
quantifier_layout_anchor = r"\subsection{$\lexists$ साठीचे नियम}"
assert out.count(quantifier_layout_anchor) == 2
out = out.replace(
    quantifier_layout_anchor,
    r"\enlargethispage{1pt}" + "\n" + quantifier_layout_anchor,
    1,
)
out = (
    out.replace(r"\formula{A}", r"\varphi")
    .replace(r"\formula{B}", r"\psi")
    .replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
assert len(processed_ids) == 27 and len(set(processed_ids)) == 27
assert "एकूण 94 स्रोत-एकके आणि 83 वाचक-विभाग" in out
assert out.count(r"\section{") == 83
assert out.count(r"\chapter{") == 10
assert "!!" not in out
assert "The rules for" not in out and "``prfND''``" not in out
assert not re.search(r"![ABCD]", out)
(B / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")

manifest = [
    json.loads(line)
    for line in (P / "provenance" / "SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]
inputs = []
for row in manifest[3:97]:
    path = P / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(P).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 94 and inputs[-1]["unit_id"] == "OLP-0097"
(B / "INPUTS.json").write_text(
    json.dumps(
        {
            "input_units": inputs,
            "scope": "94 source units, 83 reader sections, ten complete chapters",
            "conditional_decisions": [],
            "tag_profile": {
                "true": sorted(true_tags),
                "false": [
                    "defNot",
                    "defOr",
                    "defAnd",
                    "defIf",
                    "defIff",
                    "defTrue",
                    "defFalse",
                    "defEx",
                    "defAll",
                ],
            },
            "reader_projections": {
                "MRPRF-001": "two tableau true-conditional labels rendered as true-conjunction labels",
                "OLSEQ-001": "four antecedent-exchange labels rendered as left exchange",
                "OLSEQ-002": "two missing negations restored in the explanatory candidate sequents",
            },
            "source_issue_ids_added": [
                "OLSEQ-001",
                "OLSEQ-002",
                "OLSEQ-003",
                "OLND-001",
                "OLND-002",
                "OLND-003",
                "OLND-004",
                "OLND-005",
                "OLND-006",
                "OLND-007",
            ],
            "translation_repairs": [
                "OLP-0081 blocks 17 and 22 duplicated metavariables removed from ordinary prose before reader inclusion",
                "OLP-0082 block 8 ordinary prose translated before reader inclusion",
                "OLP-0084 block 6 duplicated quote marker removed before reader inclusion",
            ],
            "layout_adjustments": [
                "TOC page-number box widened for three-digit pages",
                "TOC section-number box widened for four-character section numbers",
                "Sequent-calculus quantifier-rule page enlarged by 1pt to avoid a fractional overfull page box",
            ],
            "external_reference_labels": sorted(external_references),
            "external_reference_rendering": "References to not-yet-included chapters are visibly described as a related section in the source book; their exact label remains in the editable reader source.",
            "source_issues": "Inherited notes through MRPRF-001 plus three Sequent Calculus and seven Natural Deduction findings; frozen English bytes remain unchanged.",
            "notation": "Function, cardinal-comparison, arithmetization equivalence-relation, generated-closure, propositional-semantic, sequent-calculus and natural-deduction macros follow the frozen upstream configuration; composition applies first argument then second.",
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 83,
            "chapters": 10,
            "processed_section_ids": len(processed_ids),
            "external_references": len(external_references),
            "reader_projections": projection_counts,
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
