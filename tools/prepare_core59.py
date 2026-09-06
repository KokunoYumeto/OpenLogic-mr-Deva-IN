"""Prepare the seven-chapter reader through OLP-0062 without launching TeX."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
B.mkdir(parents=True, exist_ok=True)
subprocess.run(
    [sys.executable, str(P / "tools" / "prepare_core.py")],
    check=True,
    capture_output=True,
)
base = (B / "openlogic-mr-core.tex").read_text(encoding="utf-8")

old_scope = "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण आणि अनंत संच"
new_scope = "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच आणि विधानीय तर्कशास्त्र"
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
base = base.replace("सहा संपूर्ण प्रकरणे", "सात संपूर्ण प्रकरणे")
old_coverage = "OLP-0054, एकूण 51 स्रोत-एकके आणि 45 वाचक-विभाग. उर्वरित 671"
new_coverage = "OLP-0062, एकूण 59 स्रोत-एकके आणि 51 वाचक-विभाग. उर्वरित 663"
assert old_coverage in base
base = base.replace(old_coverage, new_coverage)

logic_macros = r"""
\newcommand{\applytofirst}[2]{{\expandafter#1#2}}
\newcommand{\Struct}[1]{\applytofirst{\mathfrak}{#1}}
\newcommand{\Lang}[1]{\applytofirst{\mathcal}{#1}}
\newcommand{\Obj}[1]{\mathsf{#1}}
\newcommand{\PVar}{\mathrm{At}_0}
\NewDocumentCommand{\Frm}{o}{\IfNoValueTF{#1}{\mathrm{Frm}}{\mathrm{Frm}(\Lang{#1})}}
\newcommand{\True}{\ensuremath{\mathbb{T}}}
\newcommand{\False}{\ensuremath{\mathbb{F}}}
\newcommand{\lfalse}{\bot}
\newcommand{\ltrue}{\top}
\newcommand{\ident}{\equiv}
\newcommand{\subst}[2]{#1/#2}
\newcommand{\SSubst}[2]{#1[#2]}
\newcommand{\Subst}[3]{#1[\subst{#2}{#3}]}
\NewDocumentCommand{\Entails}{t{/} o}{%
  \IfBooleanTF{#1}{\IfNoValueTF{#2}{\nvDash}{\nvDash_{#2}}}{\IfNoValueTF{#2}{\vDash}{\vDash_{#2}}}}
\newcommand{\pAssign}[1]{\applytofirst{\mathfrak}{#1}}
\NewDocumentCommand{\pValue}{m d()}{\overline{\pAssign{#1}}\IfNoValueF{#2}{(#2)}}
\NewDocumentCommand{\pSat}{t{/} m m}{\pAssign{#2}\IfBooleanTF{#1}{\nvDash}{\vDash}#3}
\newcommand{\indfrm}{}
\NewDocumentCommand{\indcase}{m m +m}{\renewcommand{\indfrm}{#1}$#1 \ident #2$: #3}
\def\startycommalist{\def\ycomma{\def\ycomma{, }}}
"""
base = base.replace(r"\begin{document}", logic_macros + r"\begin{document}", 1)

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
before, notes = base.split(marker, 1)
notes = marker + notes


def balanced(text, index):
    assert text[index] == "{"
    cursor = index + 1
    depth = 1
    while depth:
        slashes = 0
        back = cursor - 1
        while back >= 0 and text[back] == "\\":
            slashes += 1
            back -= 1
        escaped = slashes % 2 == 1
        if text[cursor] == "{" and not escaped:
            depth += 1
        elif text[cursor] == "}" and not escaped:
            depth -= 1
        cursor += 1
    return text[index + 1 : cursor - 1], cursor


true_tags = {
    "prvNot", "prvOr", "prvAnd", "prvIf", "prvIff", "prvTrue",
    "prvFalse", "prvEx", "prvAll", "limitClause",
}


def tag_value(tag):
    return tag[3:] not in true_tags if tag.startswith("not") else tag in true_tags


def expand_tag_command(text, command):
    marker = "\\" + command
    while marker in text:
        start = text.index(marker)
        cursor = start + len(marker)
        args = []
        for _ in range(3):
            while text[cursor].isspace():
                cursor += 1
            value, cursor = balanced(text, cursor)
            args.append(value)
        enabled = any(tag_value(tag.strip()) for tag in args[0].split(","))
        selected = args[1] if enabled else args[2]
        if command == "tagitem" and selected.strip():
            selected = r"\item " + selected
        text = text[:start] + selected + text[cursor:]
    return text


def select_tags(text):
    tagblock = re.compile(
        r"\\begin\{tagblock\}\{([^}]*)\}(.*?)\\end\{tagblock\}", re.S
    )
    while tagblock.search(text):
        text = tagblock.sub(
            lambda match: match.group(2)
            if any(tag_value(tag.strip()) for tag in match.group(1).split(","))
            else "",
            text,
            count=1,
        )
    text = re.sub(
        r"\\begin\{tagenumerate\}\{([^}]*)\}",
        lambda match: r"\begin{enumerate}"
        if sum(tag_value(tag.strip()) for tag in match.group(1).split(",")) > 1
        else "",
        text,
    )
    text = text.replace(r"\end{tagenumerate}", r"\end{enumerate}")
    text = expand_tag_command(text, "iftag")
    text = expand_tag_command(text, "tagitem")
    return text


def token_replace(match):
    token = re.sub(r"\s+", " ", match.group("token")).strip()
    plural = bool(match.group("plural"))
    singular = {
        "biconditional": "द्विशर्त",
        "conditional": "शर्त",
        "denumerable": "प्रगणनीय",
        "falsity": "असत्यता",
        "formula": "सूत्र",
        "operator": "संकारक",
        "propositional variable": "विधानीय चल",
        "structure": "संरचना",
        "truth": "सत्यता",
        "valuation": "सत्य-मूल्यांकन",
    }
    plurals = {
        "formula": "सूत्रे",
        "operator": "संकारक",
        "propositional variable": "विधानीय चले",
        "structure": "संरचना",
        "valuation": "सत्य-मूल्यांकने",
    }
    assert token in singular, token
    return plurals.get(token, singular[token]) if plural else singular[token]


def replace_tokens(text):
    text = text.replace(r"\usetoken{P}{formula}", "सूत्र")
    text = text.replace(r"\usetoken{P}{valuation}", "सत्य-मूल्यांकन")
    pattern = re.compile(
        r"!!(?:\^?a|\^)?\{(?P<token>[^{}]+)\}(?P<plural>s)?", re.S
    )
    text = pattern.sub(token_replace, text)
    grammar = {
        "सूत्रे चा": "सूत्रांचा",
        "सूत्रे ची": "सूत्रांची",
        "सूत्रे चे": "सूत्रांचे",
        "सूत्रे च्या": "सूत्रांच्या",
        "सूत्रे ना": "सूत्रांना",
        "सूत्रे पासून": "सूत्रांपासून",
        "सूत्रे पैकी": "सूत्रांपैकी",
        "सूत्रे वरील": "सूत्रांवरील",
        "सूत्रे खाली": "सूत्रांखाली",
        "विधानीय चले ना": "विधानीय चलांना",
        "विधानीय चले पासून": "विधानीय चलांपासून",
        "विधानीय चले चे": "विधानीय चलांचे",
        "विधानीय चले च्या": "विधानीय चलांच्या",
        "सत्य-मूल्यांकने विषयी": "सत्य-मूल्यांकनांविषयी",
        "यांचे सूत्रे": "यांची सूत्रे",
    }
    for old, new in grammar.items():
        text = text.replace(old, new)
    flexible_grammar = {
        r"सूत्रे\s+ची": "सूत्रांची",
        r"सूत्रे\s+च्या": "सूत्रांच्या",
        r"सूत्रे\s+साठी": "सूत्रांसाठी",
        r"सूत्रे\s+पासून": "सूत्रांपासून",
        r"सूत्र\s+चा": "सूत्राचा",
        r"सूत्र\s+ची": "सूत्राची",
        r"सूत्र\s+चे": "सूत्राचे",
        r"सूत्र\s+च्या": "सूत्राच्या",
        r"सूत्र\s+ला": "सूत्राला",
        r"सूत्र\s+मध्ये": "सूत्रामध्ये",
        r"विधानीय चल\s+चे": "विधानीय चलाचे",
        r"संकारक\s+खाली": "संकारकांखाली",
    }
    for pattern, replacement in flexible_grammar.items():
        text = re.sub(pattern, replacement, text)
    return text


directory = P / "mr" / "content" / "propositional-logic" / "syntax-and-semantics"
names = [
    "introduction", "formulas", "preliminaries", "formation-sequences",
    "valuations-sat", "semantic-notions",
]
raw = [(directory / f"{name}.tex").read_text(encoding="utf-8") for name in names]
available = set(re.findall(r"\\label\{([^}]+)\}", before))
available.add("pl:syn::chap")
for name, text in zip(names, raw):
    file_id = re.search(
        r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", text
    )
    assert file_id
    prefix = ":".join(file_id.groups())
    available.add(prefix + ":sec")
    available.update(prefix + ":" + key for key in re.findall(r"\\ollabel\{([^}]+)\}", text))


def reader_note(value):
    return value.replace("_", r"\_")


def editorial(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", text, re.S)
    assert match
    return replace_tokens(match.group())


chunks = [r"\chapter{विधानीय तर्कशास्त्र: विन्यासमीमांसा आणि चिन्हार्थमीमांसा}\label{pl:syn::chap}"]
chunks.append(editorial(P / "mr" / "content" / "propositional-logic" / "propositional-logic.tex"))
chunks.append(editorial(directory / "syntax-and-semantics.tex"))
conditional_decisions = []
for name, text in zip(names, raw):
    text = re.sub(
        r"(?m)^[ \t]*%READERNOTE\{(.*)\}$",
        lambda match: r"\begin{quote}\small\textbf{स्रोतदुरुस्ती.} "
        + reader_note(match.group(1))
        + r"\end{quote}",
        text,
    )
    text = re.sub(r"(?m)^[ \t]*%[^\n]*(?:\n|$)", "", text)
    text = re.sub(r"\\documentclass[^\n]*\n", "", text)
    text = text.replace(r"\begin{document}", "").replace(r"\end{document}", "")
    file_id = re.search(
        r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", text
    )
    assert file_id
    prefix = list(file_id.groups())
    text = text[: file_id.start()] + text[file_id.end() :]
    try:
        text = select_tags(text)
    except Exception as error:
        raise RuntimeError(f"Tag expansion failed in {name}.tex") from error
    text = replace_tokens(text)
    text = re.sub(
        r"\\olsection\{([^{}]*)\}",
        lambda match: r"\section{" + match.group(1) + r"}\label{" + ":".join(prefix) + r":sec}",
        text,
    )
    text = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda match: r"\label{" + ":".join(prefix) + ":" + match.group(1) + "}",
        text,
    )

    def reference(match):
        options = re.findall(r"\[([^]]*)\]", match.group(1))
        parts = prefix.copy()
        if options:
            parts[3 - len(options) :] = options
        key = ":".join(parts) + ":" + match.group(2)
        assert key in available, key
        return r"\ref{" + key + "}"

    text = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", reference, text)
    assert "!!" not in text
    assert not re.search(r"\\(?:iftag|tagitem|tagblock|tagenumerate|usetoken|olref|ollabel|olsection)", text)
    chunks.append(text)

pl_note = r"""\item विधानीय तर्कशास्त्र प्रकरणातील MRPL-001 आणि MRPL-002 या दोन
गोठवलेल्या-स्रोत चिन्हदोषांच्या दुरुस्त्या संबंधित परिच्छेदांलगत स्वतंत्र
``स्रोतदुरुस्ती'' नोंदींमध्ये दिल्या आहेत. मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert r"\end{enumerate}" in notes
notes = notes.replace(r"\end{enumerate}", pl_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = out.replace("!A", r"\varphi").replace("!B", r"\psi").replace("!C", r"\chi")
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
assert "एकूण 59 स्रोत-एकके आणि 51 वाचक-विभाग" in out
assert out.count(r"\section{") == 51
assert out.count(r"\chapter{") == 7
assert "!!" not in out
(B / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")

manifest = [
    json.loads(line)
    for line in (P / "provenance" / "SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = []
for row in manifest[3:62]:
    path = P / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(P).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 59 and inputs[-1]["unit_id"] == "OLP-0062"
(B / "INPUTS.json").write_text(
    json.dumps(
        {
            "input_units": inputs,
            "scope": "59 source units, 51 reader sections, seven complete chapters",
            "conditional_decisions": conditional_decisions,
            "tag_profile": {
                "true": sorted(true_tags),
                "false": [
                    "defNot", "defOr", "defAnd", "defIf", "defIff",
                    "defTrue", "defFalse", "defEx", "defAll",
                ],
            },
            "source_issues": "Three Relations and five Functions notes; ten shared Size of Sets corrections and four Marathi-lane observations; twelve Arithmetization corrections or disclosures; three Infinite Sets observations or corrections; two Propositional Logic symbol corrections; one manager false positive retracted before application; aligned English source is unchanged",
            "notation": "Function, cardinal-comparison, arithmetization equivalence-relation, generated-closure and propositional-semantic macros follow the frozen upstream configuration; composition applies first argument then second",
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
            "sections": 51,
            "chapters": 7,
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
