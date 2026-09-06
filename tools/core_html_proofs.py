"""Deterministic proof-system adaptations shared by core HTML build and QA."""

import re


PROOFS = [
    {
        "id": "sequent-calculus-proof",
        "section_id": "fol:prf:seq:sec",
        "anchor": "हे दाखवणारी निष्पत्ती पुढे दिली आहे:",
        "caption": "क्रमवर्ती कलनातील उदाहरण-निष्पत्ती",
        "environment": "prooftree",
        "required": [
            r"\Axiom$\varphi \fCenter \varphi$",
            r"\RightLabel{\LeftR{\land}}",
            r"\UnaryInf$\varphi \land \psi \fCenter \varphi$",
            r"\RightLabel{\RightR{\lif}}",
            r"\UnaryInf$\fCenter (\varphi \land \psi) \lif \varphi$",
        ],
        "rows": [
            {"formula_tex": r"\varphi \Rightarrow \varphi", "rule": "आरंभीची क्रमवर्ती"},
            {"formula_tex": r"\varphi \land \psi \Rightarrow \varphi", "rule": "∧L"},
            {"formula_tex": r"\Rightarrow (\varphi \land \psi) \to \varphi", "rule": "→R"},
        ],
    },
    {
        "id": "natural-deduction-proof",
        "section_id": "fol:prf:ntd:sec",
        "anchor": "हे दाखवणारी निष्पत्ती",
        "caption": "नैसर्गिक निगमनातील उदाहरण-निष्पत्ती",
        "environment": "prooftree",
        "required": [
            r"\AxiomC{$\Discharge{\varphi \land \psi}{1}$}",
            r"\RightLabel{\Elim{\land}}",
            r"\UnaryInfC{$\varphi$}",
            r"\DischargeRule{\Intro{\lif}}{1}",
            r"\UnaryInfC{$(\varphi \land \psi) \lif \varphi$}",
        ],
        "rows": [
            {"formula_tex": r"[\varphi \land \psi]^1", "rule": "गृहीतक"},
            {"formula_tex": r"\varphi", "rule": "∧Elim"},
            {"formula_tex": r"(\varphi \land \psi) \to \varphi", "rule": "→Intro; गृहीतक 1 मुक्त"},
        ],
    },
    {
        "id": "tableau-proof",
        "section_id": "fol:prf:tab:sec",
        "anchor": "हे दाखवणारा बंद टॅब्लो पुढे दिला आहे:",
        "caption": "बंद टॅब्लोचे उदाहरण; पाचव्या पायरीनंतर शाखा बंद होते",
        "environment": "oltableau",
        "required": [
            r"\sFmla{\False}{(\varphi \land \psi) \lif \varphi}",
            r"\sFmla{\True}{\varphi \land \psi}",
            r"\sFmla{\False}{\varphi}",
            r"\sFmla{\True}{\varphi}",
            r"\sFmla{\True}{\psi}",
            r"\TRule{\True}{\land}[2]",
            "close",
        ],
        "rows": [
            {"formula_tex": r"\mathbb{F}\,((\varphi \land \psi) \to \varphi)", "rule": "गृहीतक"},
            {"formula_tex": r"\mathbb{T}\,(\varphi \land \psi)", "rule": "→F 1"},
            {"formula_tex": r"\mathbb{F}\,\varphi", "rule": "→F 1"},
            {"formula_tex": r"\mathbb{T}\,\varphi", "rule": "∧T 2"},
            {"formula_tex": r"\mathbb{T}\,\psi", "rule": "∧T 2; शाखा बंद"},
        ],
    },
]


def adapt_prose_ensuremath(tex):
    """Make three proof-rule macros used in prose explicit inline mathematics."""
    replacements = [
        (r"\RightR{\Weakening} नियम", r"$\RightR{\Weakening}$ नियम"),
        (r"\Intro{\lif} अनुमानाच्या", r"$\Intro{\lif}$ अनुमानाच्या"),
        (r"\FalseInt{} नियमामुळे", r"$\FalseInt{}$ नियमामुळे"),
    ]
    for old, new in replacements:
        assert tex.count(old) == 1, (old, tex.count(old))
        tex = tex.replace(old, new)
    return tex


def strip_proof_environments(tex):
    """Remove three verified graphical proof blocks for semantic HTML replacement."""
    found = []
    output = tex
    for spec in PROOFS:
        pattern = re.compile(
            r"\\begin\{" + re.escape(spec["environment"]) + r"\}"
            r".*?\\end\{" + re.escape(spec["environment"]) + r"\}",
            re.S,
        )
        match = pattern.search(output)
        assert match, spec["id"]
        block = match.group()
        for required in spec["required"]:
            assert required in block, (spec["id"], required)
        found.append(spec)
        output = output[: match.start()] + output[match.end() :]
    assert not re.search(r"\\begin\{(?:prooftree|oltableau)\}", output)
    return output, found


def _balanced(text, start):
    assert text[start] == "{"
    depth = 1
    cursor = start + 1
    while depth:
        escaped = cursor > 0 and text[cursor - 1] == "\\"
        if text[cursor] == "{" and not escaped:
            depth += 1
        elif text[cursor] == "}" and not escaped:
            depth -= 1
        cursor += 1
    return text[start + 1 : cursor - 1], cursor


def _unwrap_ensuremath(text):
    while text.startswith(r"\ensuremath{") and text.endswith("}"):
        value, end = _balanced(text, len(r"\ensuremath"))
        if end != len(text):
            break
        text = value
    return text


def _replace_args(text, command, count, formatter, optional=False):
    marker = "\\" + command
    cursor = 0
    while True:
        start = text.find(marker, cursor)
        if start < 0:
            break
        after_name = start + len(marker)
        if after_name < len(text) and text[after_name].isalpha():
            cursor = after_name
            continue
        pos = after_name
        args = []
        for _ in range(count):
            while pos < len(text) and text[pos].isspace():
                pos += 1
            assert pos < len(text) and text[pos] == "{", (command, text[start : start + 80])
            value, pos = _balanced(text, pos)
            args.append(value)
        opt = None
        if optional:
            while pos < len(text) and text[pos].isspace():
                pos += 1
            if pos < len(text) and text[pos] == "[":
                end = text.index("]", pos + 1)
                opt = text[pos + 1 : end]
                pos = end + 1
        replacement = formatter(args, opt)
        text = text[:start] + replacement + text[pos:]
        cursor = start + len(replacement)
    return text


def expand_proof_math_macros(text):
    """Expand proof macros to ordinary TeX understood by Pandoc/texmath."""
    text = text.replace(r"\Proves/", r"\nvdash")
    text = re.sub(r"\\Proves\b", r"\\vdash", text)
    text = text.replace(r"\fCenter", r"\Rightarrow")
    text = text.replace(r"\Sequent", r"\Rightarrow")
    text = text.replace(r"\Weakening", r"\mathrm{W}")
    text = text.replace(r"\FalseInt{}", r"\bot_I").replace(r"\FalseInt", r"\bot_I")
    text = text.replace(r"\TAss", r"\text{गृहीतक}")
    text = _replace_args(
        text,
        "LeftR",
        1,
        lambda args, _: "{" + args[0] + r"}\mathrm{L}",
    )
    text = _replace_args(
        text,
        "RightR",
        1,
        lambda args, _: "{" + args[0] + r"}\mathrm{R}",
    )
    text = _replace_args(
        text,
        "Intro",
        1,
        lambda args, opt: "{" + args[0] + r"}\mathrm{Intro}" + ("_{" + opt + "}" if opt else ""),
        optional=True,
    )
    text = _replace_args(
        text,
        "Elim",
        1,
        lambda args, opt: "{" + args[0] + r"}\mathrm{Elim}" + ("_{" + opt + "}" if opt else ""),
        optional=True,
    )
    text = _replace_args(
        text,
        "Discharge",
        2,
        lambda args, _: "[" + args[0] + "]^{" + args[1] + "}",
    )
    text = _replace_args(
        text,
        "sFmla",
        2,
        lambda args, opt: (opt + r"\," if opt else "")
        + _unwrap_ensuremath(args[0])
        + r"\,"
        + args[1],
        optional=True,
    )
    text = _replace_args(
        text,
        "TRule",
        2,
        lambda args, opt: "{" + args[1] + "}{" + _unwrap_ensuremath(args[0]) + "}"
        + (r"\," + opt if opt else ""),
        optional=True,
    )
    text = text.replace(r"\True", r"\mathbb{T}").replace(r"\False", r"\mathbb{F}")
    text = text.replace(r"\ensuremath{\mathbb{T}}", r"\mathbb{T}")
    text = text.replace(r"\ensuremath{\mathbb{F}}", r"\mathbb{F}")
    return text
