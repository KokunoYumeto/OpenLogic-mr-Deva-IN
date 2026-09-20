"""Prepare the twenty-chapter reader through OLP-0197 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
ns = runpy.run_path(str(P / "tools" / "prepare_core108.py"))
base = (B / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior_inputs = json.loads((B / "INPUTS.json").read_text(encoding="utf-8"))

old_scope = (
    "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, "
    "विधानीय तर्कशास्त्र, सिद्धता-पद्धती, क्रमवर्ती कलन, नैसर्गिक निगमन आणि टॅब्लो"
)
new_scope = (
    "संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण, अनंत संच, "
    "विधानीय तर्कशास्त्र, चार सिद्धता-पद्धती, संपूर्णता, प्रथम-क्रम "
    "विन्यासमीमांसा व चिन्हार्थमीमांसा, प्रतिमाने व उपपत्ती आणि प्रतिमान उपपत्ती"
)
assert base.count(old_scope) >= 2
base = base.replace(old_scope, new_scope)
assert base.count("अकरा संपूर्ण प्रकरणे") == 1
base = base.replace("अकरा संपूर्ण प्रकरणे", "वीस संपूर्ण प्रकरणे")
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0111, एकूण 108 स्रोत-एकके "
    "आणि 96 वाचक-विभाग. उर्वरित 614"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0197, एकूण 194 स्रोत-एकके "
    "आणि 171 वाचक-विभाग. उर्वरित 528"
)
assert old_coverage in base
base = base.replace(old_coverage, new_coverage)
old_scope_line = r"{\LARGE " + new_scope + r"\par}"
assert base.count(old_scope_line) == 1
base = base.replace(old_scope_line, r"{\Large " + new_scope + r"\par}", 1)
assert base.count("A≈B≈C") == 1
base = base.replace("A≈B≈C", r"$A\approx B\approx C$", 1)
assert base.count("B≈C") == 1
base = base.replace("B≈C", r"$B\approx C$", 1)
old_mrinf_note = r"""\item अनंत संच प्रकरणातील MRINF-001 ते MRINF-003 या तीन स्रोत-निरीक्षणांची
नोंद ठेवली आहे. MRINF-001 मधील व्याकरणदोषाचा अभिप्रेत अर्थ थेट दिला आहे;
MRINF-002 मधील अप्रकट आधारसंचाचे गृहीतक तज्ज्ञ-पुनरावलोकनासाठी राखले आहे;
आणि MRINF-003 मधील विकृत निष्कर्ष संबंधित परिच्छेदालगत दुरुस्त केला आहे.
मूळ इंग्रजी बाइट्स बदललेले नाहीत."""
assert base.count(old_mrinf_note) == 1
new_mrinf_note = r"""\item अनंत संच प्रकरणातील MRINF-001 ते MRINF-003 या तीन स्रोत-निरीक्षणांची
नोंद ठेवली आहे. MRINF-001 मधील व्याकरणदोषाचा अभिप्रेत अर्थ थेट दिला आहे;
MRINF-002 मधील अप्रकट आधारसंचाचे गृहीतक तज्ज्ञ-पुनरावलोकनासाठी राखले आहे;
MRINF-003 मधील स्रोतदोषाचा दावा पुनर्तपासणीनंतर चुकीचा ठरून मागे घेतला आहे.
अंतःस्थ \texttt{cardeq} रचना वैध आहे; मराठी निष्कर्ष सममूल्य केंद्रित
मांडणी म्हणून जतन केला आहे. मूळ इंग्रजी बाइट्स बदललेले नाहीत."""
base = base.replace(old_mrinf_note, new_mrinf_note, 1)

package_anchor = r"\usepackage{amsmath,amssymb,amsthm,nicefrac,graphicx,tikz}"
assert base.count(package_anchor) == 1
base = base.replace(package_anchor, package_anchor + "\n" + r"\usepackage{stmaryrd}", 1)

additional_macros = r"""
\newtheorem{rem}[defn]{टीप}
\newenvironment{history}{\begin{quote}\small}{\end{quote}}
\newcommand{\MP}{\textsc{mp}}
\newcommand{\QR}{\textsc{qr}}
\newcommand{\Hyp}{\textsc{Hyp}}
\newcommand{\Nec}{\textsc{nec}}
\newcommand{\Var}{\mathrm{Var}}
\NewDocumentCommand{\Trm}{o}{\IfNoValueTF{#1}{\mathrm{Trm}}{\mathrm{Trm}(\Lang{#1})}}
\NewDocumentCommand{\Sent}{o}{\IfNoValueTF{#1}{\mathrm{Sent}}{\mathrm{Sent}(\Lang{#1})}}
\newcommand{\Th}[1]{\mathbf{#1}}
\newcommand{\Theory}[1]{\mathrm{Th}(\Struct{#1})}
\newcommand{\substruct}{\subseteq}
\NewDocumentCommand{\elemequiv}{t{/} o}{%
  \IfBooleanTF{#1}{\IfNoValueTF{#2}{\not\equiv}{\not\equiv_{#2}}}{%
  \IfNoValueTF{#2}{\equiv}{\equiv_{#2}}}}
\NewDocumentCommand{\iso}{t{/} o}{%
  \IfBooleanTF{#1}{\IfNoValueTF{#2}{\not\simeq}{\not\simeq_{#2}}}{%
  \IfNoValueTF{#2}{\simeq}{\simeq_{#2}}}}
\newcommand{\QuantRank}[1]{\mathrm{qr}(#1)}
\newcommand{\Domain}[1]{\left|\Struct{#1}\right|}
\newcommand{\Expan}[2]{(\Struct{#1},#2)}
\newcommand{\nszero}{\mathbf{z}}
\newcommand{\nssucc}{*}
\newcommand{\nsplus}{\oplus}
\newcommand{\nstimes}{\otimes}
\newcommand{\nsless}{\varolessthan}
\newcommand{\concat}{\frown}
\NewDocumentCommand{\lambd}{o o}{%
  \IfNoValueTF{#1}{\lambda}{\lambda #1}\IfNoValueF{#2}{.\,#2}}
\newcommand{\num}[1]{\overline{#1}}
\newcommand{\mModel}[1]{\applytofirst{\mathfrak}{#1}}
\NewDocumentCommand{\mSat}{t{/} m m o}{%
  \IfBooleanTF{#1}{\IfNoValueTF{#4}{\mModel{#2}\nVdash#3}{\mModel{#2},#4\nVdash#3}}{%
  \IfNoValueTF{#4}{\mModel{#2}\Vdash#3}{\mModel{#2},#4\Vdash#3}}}
\RenewDocumentCommand{\indcase}{s t{!} m m +m}{%
  \renewcommand{\indfrm}{#3}%
  \def\indfrmp{#3}%
  \def\indcomplex{#4}%
  \IfBooleanTF{#1}{$#3$ हे आण्विक सूत्र आहे: }{$#3 \ident #4$: }%
  \IfBooleanTF{#2}{सराव.}{#5}}
\NewDocumentCommand{\OPrf}{o}{\mathsf{Prf}\IfNoValueF{#1}{_{#1}}}
\NewDocumentCommand{\OCon}{o}{\mathsf{Con}\IfNoValueF{#1}{_{#1}}}
\newcommand{\PAx}{\mathrm{Ax}_0}
\newcommand{\PIso}[1]{\mathcal{#1}}
\newcommand{\Part}[2]{\Atom{\Obj P}{#1,#2}}
\newcommand{\gn}[1]{\ulcorner #1\urcorner}
"""
assert base.count(r"\begin{document}") == 1
base = base.replace(r"\begin{document}", additional_macros + r"\begin{document}", 1)

selected_base = ns["selected"]
replace_base_tokens = ns["replace_tokens"]
strip_wrapper = ns["strip_wrapper"]
true_tags = set(ns["true_tags"])
available = set(ns["available"])


def tag_value(tag):
    tag = tag.strip()
    return tag[3:] not in true_tags if tag.startswith("not") else tag in true_tags


def select_probtag(text):
    pattern = re.compile(r"\\begin\{probtag\}\{([^}]*)\}(.*?)\\end\{probtag\}", re.S)
    while pattern.search(text):
        text = pattern.sub(
            lambda match: (
                r"\begin{prob}" + match.group(2) + r"\end{prob}"
                if any(tag_value(tag) for tag in match.group(1).split(","))
                else ""
            ),
            text,
            count=1,
        )
    return text


def select_extended_tagprobs(text):
    pattern = re.compile(
        r"\\tagprob(?:\[([^]]+)\])?\{([^}]*)\}(.*?)\\tagendprob",
        re.S,
    )
    while pattern.search(text):
        def choose(match):
            context = match.group(1)
            enabled = any(tag_value(tag) for tag in match.group(2).split(","))
            if context is not None:
                enabled = enabled and tag_value(context)
            return match.group(3) if enabled else ""

        text = pattern.sub(choose, text, count=1)
    return text


def strip_reader_notes_preserve_suffix(text):
    """Drop reader-note comments while retaining TeX closers after the note."""
    output = []
    marker = "%READERNOTE{"
    for line in text.splitlines(keepends=True):
        start = line.find(marker)
        if start < 0:
            output.append(line)
            continue
        index = start + len(marker)
        depth = 1
        while index < len(line) and depth:
            if line[index] == "{" and line[index - 1] != "\\":
                depth += 1
            elif line[index] == "}" and line[index - 1] != "\\":
                depth -= 1
            index += 1
        assert depth == 0, line
        suffix = line[index:].rstrip("\r\n")
        # OLFOL-020 sits inside an indcase nested in iftag and tagitem. Its
        # comment delimiter occupies one of the three original closing braces.
        if "OLFOL-020" in line:
            assert suffix == "}}", line
            suffix = "}}}"
        newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        output.append(line[:start] + suffix + newline)
    return "".join(output)


def normalize_two_argument_iftags(text):
    """The upstream corpus contains one legacy two-argument iftag call."""
    marker = r"\iftag"
    cursor = 0
    while True:
        start = text.find(marker, cursor)
        if start < 0:
            return text
        index = start + len(marker)
        for _ in range(2):
            while index < len(text) and text[index].isspace():
                index += 1
            assert index < len(text) and text[index] == "{", text[start : start + 100]
            depth = 1
            index += 1
            while depth:
                assert index < len(text), text[start : start + 200]
                escaped = text[index - 1] == "\\"
                if text[index] == "{" and not escaped:
                    depth += 1
                elif text[index] == "}" and not escaped:
                    depth -= 1
                index += 1
        probe = index
        while probe < len(text) and text[probe].isspace():
            probe += 1
        if probe >= len(text) or text[probe] != "{":
            text = text[:index] + "{}" + text[index:]
            cursor = index + 2
        else:
            cursor = index


def selected(text):
    text = strip_reader_notes_preserve_suffix(text)
    text = select_probtag(text)
    text = select_extended_tagprobs(text)
    text = normalize_two_argument_iftags(text)
    return selected_base(text)


singular = {
    "biconditional": "द्विशर्त",
    "bijection": "एकास-एक आच्छादन",
    "complete": "संपूर्ण",
    "conditional": "शर्त",
    "constant": "स्थिरांक",
    "denumerable": "गणनीय अनंत",
    "derivability": "निष्पन्नता",
    "derivable": "निष्पन्न करता येण्याजोगे",
    "derivation": "निष्पत्ती",
    "derive": "निष्पन्न",
    "domain": "प्रांत",
    "element": "घटक",
    "enumerable": "गणनीय",
    "falsity": "असत्यता",
    "formula": "सूत्र",
    "free for": "आदेशनासाठी मुक्त",
    "function": "फलन",
    "identity": "एकरूपता",
    "injective": "एकास-एक",
    "language": "भाषा",
    "main operator": "मुख्य संकारक",
    "nonderivability": "अनिष्पन्नता",
    "nonenumerable": "अगणनीय",
    "operator": "संकारक",
    "predicate": "विधेय",
    "propositional variable": "विधानीय चल",
    "sentence": "वाक्य",
    "structure": "संरचना",
    "subformula": "उपसूत्र",
    "surjective": "आच्छादक",
    "truth": "सत्यता",
    "valuation": "सत्य-मूल्यांकन",
    "value": "मूल्य",
    "variable": "चल",
}
plural = {
    "constant": "स्थिरांक",
    "derivation": "निष्पत्त्या",
    "domain": "प्रांत",
    "element": "घटक",
    "formula": "सूत्रे",
    "function": "फलने",
    "operator": "संकारक",
    "predicate": "विधेये",
    "propositional variable": "विधानीय चले",
    "sentence": "वाक्ये",
    "structure": "संरचना",
    "subformula": "उपसूत्रे",
    "valuation": "सत्य-मूल्यांकने",
    "value": "मूल्ये",
    "variable": "चले",
}


def token_word(token, suffix=""):
    token = re.sub(r"\s+", " ", token).strip()
    assert token in singular, token
    return plural.get(token, singular[token]) if suffix == "s" else singular[token]


def replace_reader_tokens(text):
    text = re.sub(
        r"!!(?:\^?a|\^)?\{(?P<token>[^{}]+)\}(?P<suffix>s|d)?",
        lambda match: token_word(match.group("token"), match.group("suffix") or ""),
        text,
        flags=re.S,
    )
    text = re.sub(
        r"\\(?:use|print)token\{[^{}]+\}\{([^{}]+)\}",
        lambda match: token_word(match.group(1)),
        text,
    )
    text = re.sub(r"\\(?:Article|article)\{[^{}]+\}\s*", "", text)
    text = replace_base_tokens(text)
    grammar = {
        "विधेये चा": "विधेयांचा",
        "विधेये ची": "विधेयांची",
        "विधेये चे": "विधेयांचे",
        "विधेये च्या": "विधेयांच्या",
        "फलने चा": "फलनांचा",
        "फलने ची": "फलनांची",
        "फलने चे": "फलनांचे",
        "फलने च्या": "फलनांच्या",
        "उपसूत्रे चा": "उपसूत्रांचा",
        "उपसूत्रे ची": "उपसूत्रांची",
        "उपसूत्रे चे": "उपसूत्रांचे",
        "उपसूत्रे च्या": "उपसूत्रांच्या",
        "मूल्ये चा": "मूल्यांचा",
        "मूल्ये ची": "मूल्यांची",
        "मूल्ये चे": "मूल्यांचे",
        "मूल्ये च्या": "मूल्यांच्या",
        "संरचना चा": "संरचनांचा",
        "संरचना ची": "संरचनांची",
        "संरचना चे": "संरचनांचे",
        "संरचना च्या": "संरचनांच्या",
        "संरचना मध्ये": "संरचनांमध्ये",
        "प्रांत चा": "प्रांताचा",
        "प्रांत ची": "प्रांताची",
        "प्रांत चे": "प्रांताचे",
        "प्रांत च्या": "प्रांताच्या",
    }
    for old, new in grammar.items():
        text = text.replace(old, new)
    return text


chapters = [
    {
        "key": "axd", "part": "fol", "title": "स्वयंसिद्धकीय निष्पत्ती",
        "label": "fol:axd::chap", "directory": P / "mr/content/first-order-logic/axiomatic-deduction",
        "driver": "axiomatic-deduction.tex",
        "imports": ["rules-and-proofs", "axioms-rules-propositional", "axioms-rules-quantifiers", "proving-things", "proving-things-quant", "proof-theoretic-notions", "deduction-theorem", "deduction-theorem-quantifiers", "provability-consistency", "provability-propositional", "provability-quantifiers", "soundness", "identity"],
    },
    {
        "key": "com", "part": "fol", "title": "संपूर्णता प्रमेय",
        "label": "fol:com::chap", "directory": P / "mr/content/first-order-logic/completeness",
        "driver": "completeness.tex",
        "imports": ["introduction", "outline", "complete-consistent-sets", "henkin-expansions", "lindenbaums-lemma", "construction-of-model", "identity", "completeness-thm", "compactness", "compactness-direct", "downward-ls"],
    },
    {
        "key": "int", "part": "fol", "title": "प्रथम-क्रम तर्कशास्त्राचा परिचय",
        "label": "fol:int::chap", "directory": P / "mr/content/first-order-logic/introduction",
        "driver": "introduction.tex",
        "imports": ["first-order-logic", "syntax", "formulas", "satisfaction", "sentences", "semantic-notions", "substitution", "models-theories", "soundness-completeness"],
    },
    {
        "key": "syn", "part": "fol", "title": "प्रथम-क्रम तर्कशास्त्राची विन्यासमीमांसा",
        "label": "fol:syn::chap", "directory": P / "mr/content/first-order-logic/syntax-and-semantics",
        "driver": "syntax.tex",
        "imports": ["intro-syntax", "first-order-languages", "terms-formulas", "unique-readability", "main-operator", "subformulas", "formation-sequences", "free-vars-sentences", "substitution"],
    },
    {
        "key": "sem", "file_key": "syn", "part": "fol", "title": "प्रथम-क्रम तर्कशास्त्राची चिन्हार्थमीमांसा",
        "label": "fol:sem::chap", "directory": P / "mr/content/first-order-logic/syntax-and-semantics",
        "driver": "semantics.tex",
        "imports": ["intro-semantics", "structures", "covered-structures", "satisfaction", "assignments", "extensionality", "semantic-notions"],
    },
    {
        "key": "mat", "part": "fol", "title": "उपपत्ती आणि त्यांची प्रतिमाने",
        "label": "fol:mat::chap", "directory": P / "mr/content/first-order-logic/models-theories",
        "driver": "models-theories.tex",
        "imports": ["introduction", "expressing-props-of-structures", "theories", "expressing-relations", "set-theory", "size-of-structures"],
    },
    {
        "key": "byd", "part": "fol", "title": "प्रथम-क्रम तर्कशास्त्रापलीकडे",
        "label": "fol:byd::chap", "directory": P / "mr/content/first-order-logic/beyond",
        "driver": "beyond.tex",
        "imports": ["introduction", "many-sorted-logic", "second-order-logic", "higher-order-logic", "intuitionistic-logic", "modal-logics", "other-logics"],
    },
    {
        "key": "bas", "part": "mod", "title": "प्रतिमान उपपत्तीची मूलतत्त्वे",
        "label": "mod:bas::chap", "directory": P / "mr/content/model-theory/basics",
        "driver": "basics.tex",
        "imports": ["reducts-and-expansions", "substructures", "overspill", "isomorphism", "theory-of-m", "partial-iso", "dlo"],
    },
    {
        "key": "mar", "part": "mod", "title": "अंकगणिताची प्रतिमाने",
        "label": "mod:mar::chap", "directory": P / "mr/content/model-theory/models-of-arithmetic",
        "driver": "models-of-arithmetic.tex",
        "imports": ["introduction", "standard-models", "non-standard-models", "models-of-q", "models-of-pa", "computable-models"],
    },
]

file_texts = {}
prefixes = {}
for chapter in chapters:
    available.add(chapter["label"])
    driver = selected((chapter["directory"] / chapter["driver"]).read_text(encoding="utf-8"))
    imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
    assert imports == chapter["imports"], (chapter["key"], imports)
    for name in imports:
        path = chapter["directory"] / f"{name}.tex"
        try:
            text = selected(path.read_text(encoding="utf-8"))
        except Exception as error:
            raise AssertionError(f"tag selection failed for {path}") from error
        file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", text)
        expected_file_key = chapter.get("file_key", chapter["key"])
        assert file_id and file_id.groups()[:2] == (chapter["part"], expected_file_key), (chapter["key"], name)
        parts = list(file_id.groups())
        prefix = ":".join(parts)
        prefixes[(chapter["key"], name)] = (parts, prefix)
        file_texts[(chapter["key"], name)] = text
        available.add(prefix + ":sec")
        available.update(prefix + ":" + key for key in re.findall(r"\\ollabel\{([^}]+)\}", text))
        available.update(re.findall(r"\\label\{([^}]+)\}", text))

external_references = set(prior_inputs.get("external_reference_labels", []))


def tagged_references(match):
    pairs = re.findall(r"([^,{}\s]+)/\{([^{}]+)\}", match.group(1))
    labels = [label for _, label in pairs if label in available]
    if not labels:
        external_references.update(label for _, label in pairs)
        return r"\readerexternalref{tagrefs}"
    return ", ".join(r"\ref{" + label + "}" for label in labels)


def direct_references(match):
    labels = [label.strip() for label in match.group(1).split(",")]
    return " आणि ".join(r"\ref{" + label + "}" for label in labels)


chunks = []
processed_prefixes = []
for chapter in chapters:
    chunks.append(r"\chapter{" + chapter["title"] + r"}\label{" + chapter["label"] + "}")
    driver = selected((chapter["directory"] / chapter["driver"]).read_text(encoding="utf-8"))
    editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
    if editorial:
        chunks.append(replace_reader_tokens(editorial.group()))
    for name in chapter["imports"]:
        text = strip_wrapper(file_texts[(chapter["key"], name)])
        parts, prefix = prefixes[(chapter["key"], name)]
        processed_prefixes.append(prefix)
        file_id = re.search(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", text)
        assert file_id
        text = text[: file_id.start()] + text[file_id.end() :]
        text = replace_reader_tokens(text)
        text, section_count = re.subn(
            r"\\olsection(?:\[[^]]*\])?\{([^{}]*)\}",
            lambda match: r"\section{" + match.group(1) + r"}\label{" + prefix + r":sec}",
            text,
        )
        if section_count == 0:
            text, section_count = re.subn(
                r"\\section\{([^{}]*)\}",
                lambda match: r"\section{" + match.group(1) + r"}\label{" + prefix + r":sec}",
                text,
                count=1,
            )
        if section_count == 0:
            text, section_count = re.subn(
                r"\\section\{([^\n]*)\}",
                lambda match: r"\section{" + match.group(1) + r"}\label{" + prefix + r":sec}",
                text,
                count=1,
            )
        assert section_count == 1, (chapter["key"], name, section_count)
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
        text = re.sub(r"\\Olref\{([^}]+)\}", lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}", text)
        text = re.sub(r"\\(?:c|C)ref\{([^}]+)\}", direct_references, text)
        text = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tagged_references, text, flags=re.S)
        citation_replacements = {
            r"\citep{Magnus2021}": "(Magnus आणि सहकारी, 2021)",
            r"\citep{Smullyan1968}": "(Smullyan, 1968)",
            r"\citet{Zuckerman1973}": "Zuckerman (1973)",
        }
        for old, new in citation_replacements.items():
            text = text.replace(old, new)
        assert "!!" not in text, (chapter["key"], name)
        leftover_command = re.search(
            r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
            r"usetoken|printtoken|Article|article|olref|Olref|ollabel|olsection|olfileid|tagrefs|Cref|cref)",
            text,
        )
        assert not leftover_command, (chapter["key"], name, leftover_command.group(0))
        assert not re.search(r"\\cite(?:author|year|alt|p|t)?(?:\[[^]]*\])?\{", text), (chapter["key"], name)
        chunks.append(text)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_issue_notes = r"""
\item \textbf{OLAXD-001--OLAXD-009}: स्वयंसिद्धकीय निष्पत्ती प्रकरणातील
कंस, अंतिम निष्कर्ष, स्वयंसिद्धक-संदर्भ, संख्यापक-नियम आणि जुनी
फाइल-माहिती यांतील नऊ निश्चित स्रोतदोष मराठी संरेखित स्रोतांत मर्यादितपणे
दुरुस्त केले आहेत; गोठवलेले इंग्रजी बाइट्स जतन आहेत.
\item \textbf{OLCOM-001--OLCOM-006}: संपूर्णता प्रकरणातील सूत्र-युक्तिवाद,
चल-सुसंगती, बंद-पद अट, विरामचिन्हे, प्रतिनिधी आणि टॅग-संदर्भ यांतील सहा
निश्चित स्रोतदोषांची दुरुस्ती किंवा स्पष्टता मराठी स्रोतांत नोंदवली आहे.
 \item \textbf{OLFOL-001--OLFOL-040}: प्रथम-क्रम तर्कशास्त्र आणि प्रतिमान
उपपत्तीच्या पुढील प्रकरणांतील एकोणचाळीस सूत्रात्मक, निर्देशांकविषयक,
अर्थविषयक आणि सिद्धताविषयक स्रोतदोष किंवा अपूर्ण पायऱ्या मर्यादितपणे
दुरुस्त किंवा स्पष्ट केल्या आहेत. OLFOL-009 मधील अतिरिक्त आकुंचित कंसाची
सूचना पुनर्तपासणीनंतर चुकीची ठरून मागे घेतली आहे; गोठवलेली रचना आधीपासून
संतुलित आहे. प्रत्येक नोंदीचा अचूक स्रोत-स्थान, पर्याय आणि
पुनरावलोकन-प्रश्न सोबतच्या तज्ज्ञ-पुनरावलोकन नोंदींत आहे.
"""
assert r"\end{enumerate}" in notes
notes = notes.replace(r"\end{enumerate}", new_issue_notes + r"\end{enumerate}", 1)
new_references = r"""
\par\medskip
P. D. Magnus, Tim Button, J. Robert Loftis, Aaron Thomas-Bolduc आणि
Richard Zach (2021). \textit{forall x: Calgary}. Fall 2021 आवृत्ती.

Raymond M. Smullyan (1968). \textit{First-Order Logic}. Springer.

M. M. Zuckerman (1973). ``On the Unique Readability of Formal Systems.''
\textit{Notre Dame Journal of Formal Logic}, 14(4), 546--548.
"""
assert notes.count(r"\end{document}") == 1
notes = notes.replace(r"\end{document}", new_references + r"\end{document}", 1)

out = before + "\n".join(chunks) + "\n" + notes
out = (
    out.replace(r"\formula{A}", r"\varphi")
    .replace(r"\formula{B}", r"\psi")
    .replace("!A", r"\varphi")
    .replace("!B", r"\psi")
    .replace("!C", r"\chi")
    .replace("!D", r"\theta")
)
old_predicate_congruence = r""" \item $\Gamma^* \Proves \eq[t][t']$ आणि
$\Gamma^* \Proves
\Atom{R}{t_1,\dots,t_{i-1},t,t_{i+1},\dots,t_n}$ असेल, तर
$\Gamma^* \Proves \Atom{R}{t_1,\dots,t_{i-1},t',t_{i+1},\dots,t_n}$
प्रत्येक $n$-स्थानी विधेय~$R$ आणि बंद पदे $t_1$, \dots,
$t_{i-1}$, $t_{i+1}$, \dots,~$t_n$ यांच्यासाठी."""
if old_predicate_congruence not in out:
    old_predicate_congruence = old_predicate_congruence[1:]
assert out.count(old_predicate_congruence) == 1
new_predicate_congruence = r"""\item $\Gamma^* \Proves \eq[t][t']$ आणि
$\Gamma^* \Proves
\Atom{R}{t_1,\dots,t_{i-1},t,t_{i+1},\dots,t_n}$ असेल, तर
\[
\Gamma^* \Proves
\Atom{R}{t_1,\dots,t_{i-1},t',t_{i+1},\dots,t_n}
\]
प्रत्येक $n$-स्थानी विधेय~$R$ आणि बंद पदे $t_1$, \dots,
$t_{i-1}$, $t_{i+1}$, \dots,~$t_n$ यांच्यासाठी."""
out = out.replace(old_predicate_congruence, new_predicate_congruence, 1)

old_partial_iso_function = r"""\item प्रत्येक $n$-स्थानी फलन $f$ साठी: $a_1$, \dots, $a_n$
    हे $p$ च्या प्रांतात असतील, तर $p(\Assign f M (a_1, \dots,a_n))
    = \Assign f N (p(a_1), \dots, p(a_n))$."""
assert out.count(old_partial_iso_function) == 1
new_partial_iso_function = r"""\item प्रत्येक $n$-स्थानी फलन $f$ साठी: $a_1$, \dots, $a_n$
    हे $p$ च्या प्रांतात असतील, तर
    \begin{multline*}
    p(\Assign f M (a_1, \dots,a_n))\\
    = \Assign f N (p(a_1), \dots, p(a_n)).
    \end{multline*}"""
out = out.replace(old_partial_iso_function, new_partial_iso_function, 1)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (P / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = []
for row in manifest[3:197]:
    path = P / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(P).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )

new_issue_ids = (
    [f"OLAXD-{i:03d}" for i in range(1, 10)]
    + [f"OLCOM-{i:03d}" for i in range(1, 7)]
    + [f"OLFOL-{i:03d}" for i in range(1, 41)]
)
assert len(inputs) == 194 and inputs[-1]["unit_id"] == "OLP-0197"
assert len(processed_prefixes) == 75 and len(set(processed_prefixes)) == 75
assert out.count(r"\chapter{") == 20
assert out.count(r"\section{") == 171
assert "194 स्रोत-एकके आणि 171 वाचक-विभाग" in out
assert "!!" not in out
assert not re.search(r"![ABCD]", out)

(B / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
(B / "INPUTS.json").write_text(
    json.dumps(
        {
            "input_units": inputs,
            "scope": "194 source units, 171 reader sections, twenty complete chapters",
            "conditional_decisions": prior_inputs.get("conditional_decisions", []),
            "tag_profile": {
                "true": sorted(true_tags),
                "false": ["defNot", "defOr", "defAnd", "defIf", "defIff", "defTrue", "defFalse", "defEx", "defAll"],
            },
            "reader_projections": {
                **prior_inputs.get("reader_projections", {}),
                "OLAXD-001--OLAXD-009": "bounded aligned-source corrections carried into the reader and disclosed in the editorial notes",
                "OLCOM-001--OLCOM-006": "bounded aligned-source corrections carried into the reader and disclosed in the editorial notes",
                "OLFOL-001--OLFOL-040": "bounded aligned-source corrections carried into the reader and disclosed in the editorial notes",
            },
            "source_issue_ids_added": new_issue_ids,
            "external_reference_labels": sorted(external_references),
            "external_reference_rendering": "References to not-yet-included chapters are visibly described as a related section in the source book; exact labels remain in the editable aligned sources.",
            "part_driver_units_not_rendered_as_sections": ["OLP-0138", "OLP-0182"],
            "source_issues": "Inherited notes through OLTAB-012 plus OLAXD-001--009, OLCOM-001--006 and OLFOL-001--040; OLFOL-009 is a retracted false positive, and frozen English bytes remain unchanged.",
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
            "sections": 171,
            "chapters": 20,
            "external_references": len(external_references),
            "source_issue_ids_added": len(new_issue_ids),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
