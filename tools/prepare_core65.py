"""Prepare the eight-chapter reader through OLP-0068 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
ns = runpy.run_path(str(P / "tools" / "prepare_core59.py"))
base = (B / "openlogic-mr-core.tex").read_text(encoding="utf-8")

old_scope = "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच आणि विधानीय तर्कशास्त्र"
new_scope = "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, विधानीय तर्कशास्त्र आणि सिद्धता-पद्धती"
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
base = base.replace("सात संपूर्ण प्रकरणे", "आठ संपूर्ण प्रकरणे")
old_coverage = "OLP-0062, एकूण 59 स्रोत-एकके आणि 51 वाचक-विभाग. उर्वरित 663"
new_coverage = "OLP-0068, एकूण 65 स्रोत-एकके आणि 56 वाचक-विभाग. उर्वरित 657"
assert old_coverage in base
base = base.replace(old_coverage, new_coverage)

package_anchor = r"\usepackage{amsmath,amssymb,amsthm,nicefrac,graphicx,tikz}"
proof_packages = package_anchor + "\n" + r"\usepackage{bussproofs}" + "\n" + r"\usepackage[tableaux]{prooftrees}"
assert base.count(package_anchor) == 1
base = base.replace(package_anchor, proof_packages, 1)

proof_macros = r"""
\newcommand{\Sequent}{\Rightarrow}
\renewcommand{\fCenter}{\ensuremath{\,\Sequent\,}}
\NewDocumentCommand{\LeftR}{m}{\ensuremath{{#1}\mathrm{L}}}
\NewDocumentCommand{\RightR}{m}{\ensuremath{{#1}\mathrm{R}}}
\newcommand{\Weakening}{\ensuremath{\mathrm{W}}}
\NewDocumentCommand{\Intro}{m o}{\ensuremath{{#1}\mathrm{Intro}\IfNoValueTF{#2}{}{_{#2}}}}
\NewDocumentCommand{\Elim}{m o}{\ensuremath{{#1}\mathrm{Elim}\IfNoValueTF{#2}{}{_{#2}}}}
\newcommand{\FalseInt}{\ensuremath{\lfalse_I}}
\NewDocumentCommand{\Discharge}{m m}{[#1]^{#2}}
\NewDocumentCommand{\DischargeRule}{m m}{\RightLabel{#1}\LeftLabel{\scriptsize $#2$}}
\NewDocumentCommand{\sFmla}{m m o}{\ensuremath{\IfNoValueTF{#3}{}{#3\,}\hbox to.8em{\ensuremath{#1}\hfil} #2}}
\NewDocumentCommand{\TRule}{m m o}{\ensuremath{{#2}{#1}\IfNoValueTF{#3}{}{\, #3}}}
\newcommand{\TAss}{\text{गृहीतक}}
\NewDocumentCommand{\Proves}{t{/} o}{%
  \IfBooleanTF{#1}{\IfNoValueTF{#2}{\nvdash}{\nvdash_{#2}}}{\IfNoValueTF{#2}{\vdash}{\vdash_{#2}}}}
\newcommand{\formula}[1]{#1}
\renewenvironment{prooftree}{\begin{center}\bottomAlignProof}{\DisplayProof\end{center}}
\newenvironment{oltableau}{\center\tableau{}}{\endtableau\endcenter}
\newenvironment{derivation}{~\begin{trivlist}\item\begin{tabular}[b]{@{}rll@{}}}{\end{tabular}\end{trivlist}}
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", proof_macros + r"\begin{document}", 1)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes

balanced = ns["balanced"]
select_tags = ns["select_tags"]
true_tags = ns["true_tags"]
true_tags.add("FOL")


def token_replace(match):
    token = re.sub(r"\s+", " ", match.group("token")).strip()
    suffix = match.group("suffix") or ""
    singular = {
        "derivability": "निष्पन्नता",
        "derivable": "निष्पन्न करता येण्याजोगे",
        "derivation": "निष्पत्ती",
        "derive": "निष्पन्न",
        "discharge": "मुक्त",
        "discharged": "मुक्त",
        "element": "घटक",
        "formula": "सूत्र",
        "sentence": "वाक्य",
        "signed formula": "चिन्हांकित सूत्र",
        "structure": "संरचना",
        "tableau": "टॅब्लो",
        "undischarged": "मुक्त न केलेली",
    }
    plurals = {
        "derivation": "निष्पत्त्या",
        "formula": "सूत्रे",
        "sentence": "वाक्ये",
        "signed formula": "चिन्हांकित सूत्रे",
        "structure": "संरचना",
        "tableau": "टॅब्लो",
    }
    assert token in singular, token
    if suffix == "s":
        return plurals.get(token, singular[token])
    if suffix == "d":
        assert token == "derive"
    return singular[token]


def replace_tokens(text):
    replacements = {
        r"\usetoken{S}{derivation}": "निष्पत्ती",
        r"\usetoken{P}{derivation}": "निष्पत्ती",
        r"\usetoken{P}{tableau}": "टॅब्लो",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    pattern = re.compile(
        r"!!(?:\^?a|\^)?\{(?P<token>[^{}]+)\}(?P<suffix>s|d)?", re.S
    )
    text = pattern.sub(token_replace, text)
    grammar = {
        "निष्पत्ती पद्धती": "निष्पत्ती-पद्धती",
        "निष्पत्त्या चा": "निष्पत्त्यांचा",
        "निष्पत्त्या ची": "निष्पत्त्यांची",
        "निष्पत्त्या चे": "निष्पत्त्यांचे",
        "निष्पत्त्या च्या": "निष्पत्त्यांच्या",
        "निष्पत्त्या ना": "निष्पत्त्यांना",
        "निष्पत्त्या मध्ये": "निष्पत्त्यांमध्ये",
        "निष्पत्ती चा": "निष्पत्तीचा",
        "निष्पत्ती ची": "निष्पत्तीची",
        "निष्पत्ती चे": "निष्पत्तीचे",
        "निष्पत्ती च्या": "निष्पत्तीच्या",
        "निष्पत्ती मध्ये": "निष्पत्तीमध्ये",
        "वाक्ये चा": "वाक्यांचा",
        "वाक्ये ची": "वाक्यांची",
        "वाक्ये चे": "वाक्यांचे",
        "वाक्ये च्या": "वाक्यांच्या",
        "वाक्ये पासून": "वाक्यांपासून",
        "वाक्ये पैकी": "वाक्यांपैकी",
        "वाक्ये चे": "वाक्यांचे",
        "वाक्य ला": "वाक्याला",
        "वाक्य चा": "वाक्याचा",
        "वाक्य ची": "वाक्याची",
        "वाक्य चे": "वाक्याचे",
        "वाक्य च्या": "वाक्याच्या",
        "सूत्रे चा": "सूत्रांचा",
        "सूत्रे ची": "सूत्रांची",
        "सूत्रे चे": "सूत्रांचे",
        "सूत्रे च्या": "सूत्रांच्या",
        "सूत्रे पासून": "सूत्रांपासून",
        "सूत्रे पैकी": "सूत्रांपैकी",
        "सूत्रे ने": "सूत्रांनी",
        "सूत्र ला": "सूत्राला",
        "सूत्र चा": "सूत्राचा",
        "सूत्र ची": "सूत्राची",
        "सूत्र चे": "सूत्राचे",
        "सूत्र च्या": "सूत्राच्या",
        "सूत्र मध्ये": "सूत्रामध्ये",
        "चिन्हांकित सूत्रे चा": "चिन्हांकित सूत्रांचा",
        "चिन्हांकित सूत्रे ची": "चिन्हांकित सूत्रांची",
        "चिन्हांकित सूत्रे च्या": "चिन्हांकित सूत्रांच्या",
        "चिन्हांकित सूत्रे पैकी": "चिन्हांकित सूत्रांपैकी",
        "चिन्हांकित सूत्रे ने": "चिन्हांकित सूत्रांनी",
        "चिन्हांकित सूत्र ला": "चिन्हांकित सूत्राला",
        "टॅब्लो चा": "टॅब्लोचा",
        "टॅब्लो ची": "टॅब्लोची",
        "टॅब्लो चे": "टॅब्लोचे",
        "टॅब्लो च्या": "टॅब्लोच्या",
        "टॅब्लो मध्ये": "टॅब्लोमध्ये",
        "टॅब्लो वर": "टॅब्लोवर",
        "संरचना चा": "संरचनेचा",
        "संरचना ची": "संरचनेची",
        "संरचना चे": "संरचनेचे",
        "संरचना च्या": "संरचनेच्या",
    }
    for old, new in grammar.items():
        text = text.replace(old, new)
    flexible_grammar = {
        r"निष्पत्ती\s+पद्धत": "निष्पत्ती-पद्धत",
        r"निष्पन्नता\s+मुळे": "निष्पन्नतेमुळे",
        r"निष्पत्त्या\s+ची": "निष्पत्त्यांची",
        r"निष्पत्त्या\s+वर": "निष्पत्त्यांवर",
        r"निष्पत्ती\s+मध्ये": "निष्पत्तीमध्ये",
        r"निष्पत्ती\s+मधील": "निष्पत्तीमधील",
        r"चिन्हांकित सूत्रे\s+वर": "चिन्हांकित सूत्रांवर",
        r"असे\s+निष्पत्ती": "अशी निष्पत्ती",
        r"ही\s+निष्पत्त्या": "या निष्पत्त्या",
        r"निष्पत्ती\s+हा": "निष्पत्ती ही",
        r"निष्पत्ती\s+हे\s+प्रस्थापित": "निष्पत्ती ही प्रस्थापित",
        r"दाखवणारे\s+निष्पत्ती": "दाखवणारी निष्पत्ती",
        r"चे(\s+)निष्पत्ती": r"ची\1निष्पत्ती",
        r"चे(\s+)अशी निष्पत्ती": r"ची\1अशी निष्पत्ती",
        r"दाखवणारी निष्पत्ती(\s+)पुढे दिले आहे": r"दाखवणारी निष्पत्ती\1पुढे दिली आहे",
        r"क्रमवर्ती कलनातील निष्पत्ती ही क्रमवर्तींचा वृक्ष असतो": "क्रमवर्ती कलनातील निष्पत्ती म्हणजे क्रमवर्तींचा वृक्ष होय",
        r"नैसर्गिक निगमनातील\s+निष्पत्ती ही सूत्रांचा वृक्ष असतो": "नैसर्गिक निगमनातील निष्पत्ती म्हणजे सूत्रांचा वृक्ष होय",
        r"निष्पत्ती ही प्रस्थापित करते की त्याची": "निष्पत्ती ही प्रस्थापित करते की तिची",
        r"तिची मुक्त न केलेली गृहीतके\s+त्याचा निष्कर्ष": "तिची मुक्त न केलेली गृहीतके तिचा निष्कर्ष",
        r"मुक्त न केलेली असलेले प्रत्येक पान": "मुक्त न केलेले प्रत्येक पान",
    }
    for pattern, replacement in flexible_grammar.items():
        text = re.sub(pattern, replacement, text)
    return text


directory = P / "mr" / "content" / "first-order-logic" / "proof-systems"
names = [
    "introduction",
    "sequent-calculus",
    "natural-deduction",
    "tableaux",
    "axiomatic-deduction",
]
raw = [(directory / f"{name}.tex").read_text(encoding="utf-8") for name in names]

available = set(re.findall(r"\\label\{([^}]+)\}", before))
available.add("fol:prf::chap")
processed_ids = []
for name, text in zip(names, raw):
    tagged = select_tags(text)
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", tagged)
    assert file_id and file_id.groups()[0] == "fol", (name, file_id.groups() if file_id else None)
    prefix = ":".join(file_id.groups())
    processed_ids.append(prefix)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + key for key in re.findall(r"\\ollabel\{([^}]+)\}", tagged))


def editorial(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", text, re.S)
    assert match
    return replace_tokens(match.group())


chunks = [r"\chapter{सिद्धता-पद्धती}\label{fol:prf::chap}"]
chunks.append(editorial(directory / "proof-systems.tex"))
for name, raw_text in zip(names, raw):
    text = re.sub(r"(?m)^[ \t]*%[^\n]*(?:\n|$)", "", raw_text)
    text = re.sub(r"\\documentclass[^\n]*\n", "", text)
    text = text.replace(r"\begin{document}", "").replace(r"\end{document}", "")
    text = select_tags(text)
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", text)
    assert file_id and file_id.groups()[0] == "fol", name
    prefix_parts = list(file_id.groups())
    prefix = ":".join(prefix_parts)
    text = text[: file_id.start()] + text[file_id.end() :]
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
        parts = prefix_parts.copy()
        if options:
            parts[3 - len(options) :] = options
        key = ":".join(parts) + ":" + match.group(2)
        assert key in available, (name, key)
        return r"\ref{" + key + "}"

    text = re.sub(r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}", reference, text)
    assert "!!" not in text, name
    assert not re.search(r"\\(?:iftag|tagitem|tagblock|tagenumerate|usetoken|olref|ollabel|olsection|olfileid)", text), name
    chunks.append(text)

proof_note = r"""\item \textbf{MRPRF-001}: गोठवलेल्या इंग्रजी टॅब्लो उदाहरणातील
शेवटच्या दोन पायऱ्या $\sFmla{\True}{\varphi \land \psi}$ चे घटक उलगडतात,
पण त्यांची नियम-खूण चुकून $\TRule{\True}{\lif}$ अशी आहे. या वाचकात ती
अर्थानुसार $\TRule{\True}{\land}$ केली आहे; संरेखित इंग्रजी आणि मराठी
स्रोत-बाइट्स बदललेले नाहीत.
"""
assert r"\end{enumerate}" in notes
notes = notes.replace(r"\end{enumerate}", proof_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
assert out.count(r"\TRule{\True}{\lif}[2]") == 2
out = out.replace(r"\TRule{\True}{\lif}[2]", r"\TRule{\True}{\land}[2]")
out = (
    out.replace(r"\formula{A}", r"\varphi")
    .replace(r"\formula{B}", r"\psi")
    .replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
assert "एकूण 65 स्रोत-एकके आणि 56 वाचक-विभाग" in out
assert out.count(r"\section{") == 56
assert out.count(r"\chapter{") == 8
assert "!!" not in out
(B / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")

manifest = [
    json.loads(line)
    for line in (P / "provenance" / "SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = []
for row in manifest[3:68]:
    path = P / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(P).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 65 and inputs[-1]["unit_id"] == "OLP-0068"
(B / "INPUTS.json").write_text(
    json.dumps(
        {
            "input_units": inputs,
            "scope": "65 source units, 56 reader sections, eight complete chapters",
            "conditional_decisions": [],
            "tag_profile": {
                "true": sorted(true_tags),
                "false": [
                    "defNot", "defOr", "defAnd", "defIf", "defIff",
                    "defTrue", "defFalse", "defEx", "defAll",
                ],
            },
            "source_issues": "Three Relations and five Functions notes; ten shared Size of Sets corrections and four Marathi-lane observations; twelve Arithmetization corrections or disclosures; three Infinite Sets observations or corrections; two Propositional Logic symbol corrections; one Proof Systems tableau-rule-label correction in the reader projection; one manager false positive retracted before application; aligned English and Marathi source bytes are unchanged for MRPRF-001",
            "notation": "Function, cardinal-comparison, arithmetization equivalence-relation, generated-closure, propositional-semantic and proof-system macros follow the frozen upstream configuration; composition applies first argument then second",
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
            "sections": 56,
            "chapters": 8,
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
