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
    """Make proof-rule macros used in prose explicit inline mathematics."""
    replacements = [
        (r"\RightR{\Weakening} नियम", r"$\RightR{\Weakening}$ नियम"),
        (r"\Intro{\lif} अनुमानाच्या", r"$\Intro{\lif}$ अनुमानाच्या"),
        (r"\FalseInt{} नियमामुळे", r"$\FalseInt{}$ नियमामुळे"),
    ]
    for old, new in replacements:
        count = tex.count(old)
        assert count >= 1, (old, count)
        tex = tex.replace(old, new)

    preamble, marker, body = tex.partition(r"\begin{document}")
    assert marker
    math_environments = (
        "math", "displaymath", "equation", "equation*", "align", "align*",
        "alignat", "alignat*", "gather", "gather*", "multline", "multline*",
    )
    argument_commands = {"LeftR", "RightR", "Intro", "Elim"}
    optional_argument_commands = {"Intro", "Elim"}
    bare_commands = {
        "FalseInt", "FalseCl", "Weakening", "Contraction", "Exchange", "Cut",
    }
    output = []
    cursor = 0
    while cursor < len(body):
        if body.startswith(r"\verb", cursor):
            delimiter_index = cursor + len(r"\verb")
            if delimiter_index < len(body) and body[delimiter_index] == "*":
                delimiter_index += 1
            delimiter = body[delimiter_index]
            end = body.index(delimiter, delimiter_index + 1) + 1
            output.append(body[cursor:end])
            cursor = end
            continue
        if body[cursor] == "$" and (cursor == 0 or body[cursor - 1] != "\\"):
            delimiter = "$$" if body.startswith("$$", cursor) else "$"
            end = cursor + len(delimiter)
            while True:
                end = body.index(delimiter, end)
                if body[end - 1] != "\\":
                    break
                end += len(delimiter)
            end += len(delimiter)
            output.append(body[cursor:end])
            cursor = end
            continue
        if body.startswith(r"\(", cursor) or body.startswith(r"\[", cursor):
            closing = r"\)" if body.startswith(r"\(", cursor) else r"\]"
            end = body.index(closing, cursor + 2) + 2
            output.append(body[cursor:end])
            cursor = end
            continue
        environment = next(
            (
                name for name in math_environments
                if body.startswith(r"\begin{" + name + "}", cursor)
            ),
            None,
        )
        if environment:
            closing = r"\end{" + environment + "}"
            end = body.index(closing, cursor) + len(closing)
            output.append(body[cursor:end])
            cursor = end
            continue
        if body[cursor] == "%" and (cursor == 0 or body[cursor - 1] != "\\"):
            end = body.find("\n", cursor)
            end = len(body) if end < 0 else end
            output.append(body[cursor:end])
            cursor = end
            continue
        command_match = re.match(r"\\([A-Za-z]+)", body[cursor:])
        if command_match and command_match.group(1) in argument_commands:
            command = command_match.group(1)
            end = cursor + len(command_match.group(0))
            while end < len(body) and body[end].isspace():
                end += 1
            assert body[end] == "{", body[cursor : cursor + 80]
            _, end = _balanced(body, end)
            if command in optional_argument_commands:
                optional_start = end
                while optional_start < len(body) and body[optional_start].isspace():
                    optional_start += 1
                if optional_start < len(body) and body[optional_start] == "[":
                    _, end = _balanced_square(body, optional_start)
            output.append("$" + body[cursor:end] + "$")
            cursor = end
            continue
        if command_match and command_match.group(1) in bare_commands:
            end = cursor + len(command_match.group(0))
            if body.startswith("{}", end):
                end += 2
            output.append("$" + body[cursor:end] + "$")
            cursor = end
            continue
        output.append(body[cursor])
        cursor += 1
    return preamble + marker + "".join(output)


def strip_proof_environments(tex):
    """Replace every proof graphic by a stable semantic-HTML placeholder."""
    pattern = re.compile(
        r"\\begin\{(?P<environment>prooftree|oltableau|defish)\}.*?"
        r"\\end\{(?P=environment)\}",
        re.S,
    )
    found = []
    pieces = []
    cursor = 0
    used_manual = set()
    automatic = 0
    for number, match in enumerate(pattern.finditer(tex), 1):
        pieces.append(tex[cursor : match.start()])
        block = match.group()
        environment = match.group("environment")
        manual = next(
            (
                spec
                for spec in PROOFS
                if spec["id"] not in used_manual
                and spec["environment"] == environment
                and all(required in block for required in spec["required"])
            ),
            None,
        )
        if manual:
            spec = dict(manual)
            spec["rows"] = [dict(row) for row in manual["rows"]]
            used_manual.add(spec["id"])
        else:
            assert environment in ("prooftree", "defish")
            automatic += 1
            spec = _generic_proof_spec(block, automatic, environment)
        placeholder = f"OPENLOGICPROOFPLACEHOLDER{number:04d}"
        spec["placeholder"] = placeholder
        found.append(spec)
        pieces.append("\n\n" + placeholder + "\n\n")
        cursor = match.end()
    pieces.append(tex[cursor:])
    output = "".join(pieces)
    assert used_manual == {spec["id"] for spec in PROOFS}
    assert len(found) == 143
    assert automatic == 140
    assert not re.search(r"\\begin\{(?:prooftree|oltableau|defish)\}", output)
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


def _balanced_square(text, start):
    assert text[start] == "["
    depth = 1
    cursor = start + 1
    while depth:
        escaped = cursor > 0 and text[cursor - 1] == "\\"
        if text[cursor] == "[" and not escaped:
            depth += 1
        elif text[cursor] == "]" and not escaped:
            depth -= 1
        cursor += 1
    return text[start + 1 : cursor - 1], cursor


def _replace_optional_math_command(text, command, formatter, allow_bang=False):
    marker = "\\" + command
    cursor = 0
    while True:
        start = text.find(marker, cursor)
        if start < 0:
            break
        after = start + len(marker)
        if after < len(text) and text[after].isalpha():
            cursor = after
            continue
        bang = False
        if allow_bang and after < len(text) and text[after] == "!":
            bang = True
            after += 1
        args = []
        while after < len(text) and text[after].isspace():
            after += 1
        while after < len(text) and text[after] == "[" and len(args) < 2:
            value, after = _balanced_square(text, after)
            args.append(value)
        replacement = formatter(args, bang)
        text = text[:start] + replacement + text[after:]
        cursor = start
    return text


def _strip_math_dollars(text):
    return text.replace("$", "").strip()


def _label_text(text):
    text = _strip_math_dollars(text).replace(r"\scriptsize", "")
    text = expand_proof_math_macros(text)
    replacements = {
        r"\land": "∧",
        r"\lor": "∨",
        r"\lif": "→",
        r"\to": "→",
        r"\lnot": "¬",
        r"\lfalse": "⊥",
        r"\top": "⊤",
        r"\forall": "∀",
        r"\exists": "∃",
        r"\neq": "≠",
        r"\vdash": "⊢",
        r"\nvdash": "⊬",
        r"\Rightarrow": "⇒",
        r"\Leftrightarrow": "⇔",
        r"\leftrightarrow": "↔",
        r"\bot": "⊥",
        r"\varphi": "φ",
        r"\psi": "ψ",
        r"\chi": "χ",
        r"\theta": "θ",
        r"\pi": "π",
        r"\delta": "δ",
        r"\Gamma": "Γ",
        r"\Delta": "Δ",
        r"\Theta": "Θ",
        r"\Lambda": "Λ",
        r"\quad": " ",
        r"\qquad": " ",
        r"\;": " ",
        r"\,": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\\(?:ensuremath|mathrm|text)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+", "", text)
    text = text.replace("{", "").replace("}", "").replace("_", "")
    return re.sub(r"\s+", " ", text).strip() or "नियम नोंदवलेला नाही"


def _proof_formula(text):
    text = _strip_math_dollars(text)
    if not text:
        return r"\text{रिकामी जागा}"
    text = text.replace(r"\Atom", r"\Atom")
    return expand_proof_math_macros(text)


def _read_command_argument(block, position, dollar_form):
    while position < len(block) and block[position].isspace():
        position += 1
    if dollar_form:
        assert position < len(block) and block[position] == "$", block[position : position + 80]
        end = position + 1
        while True:
            end = block.index("$", end)
            if block[end - 1] != "\\":
                break
            end += 1
        return block[position + 1 : end], end + 1
    assert position < len(block) and block[position] == "{", block[position : position + 80]
    return _balanced(block, position)


def _generic_proof_spec(block, number, environment):
    command_pattern = re.compile(
        r"\\(AxiomC?|UnaryInfC?|BinaryInfC?|TrinaryInfC?|DeduceC?|"
        r"RightLabel|LeftLabel|DischargeRule|DisplayProof|noLine|doubleLine)\b"
    )
    rows = []
    pending_labels = []
    group = 1
    group_rows = 0
    cursor = 0
    while True:
        match = command_pattern.search(block, cursor)
        if not match:
            break
        command = match.group(1)
        position = match.end()
        if command in ("RightLabel", "LeftLabel"):
            value, cursor = _read_command_argument(block, position, False)
            pending_labels.append(_label_text(value))
            continue
        if command == "DischargeRule":
            rule, position = _read_command_argument(block, position, False)
            label, cursor = _read_command_argument(block, position, False)
            pending_labels.append(_label_text(rule) + f"; गृहीतक {_label_text(label)} मुक्त")
            continue
        if command == "DisplayProof":
            if group_rows:
                group += 1
                group_rows = 0
            pending_labels.clear()
            cursor = position
            continue
        if command in ("noLine", "doubleLine"):
            pending_labels.append("रेषेविना" if command == "noLine" else "दुहेरी रेषा")
            cursor = position
            continue
        dollar_form = not command.endswith("C")
        value, cursor = _read_command_argument(block, position, dollar_form)
        base_command = command.removesuffix("C")
        if base_command == "Axiom":
            rule = "आरंभीची पायरी" if value.strip("$ ") else "अपूर्ण आरंभीची पायरी"
        elif pending_labels:
            rule = "; ".join(pending_labels)
        elif base_command == "Deduce":
            rule = "मधल्या पायऱ्या संक्षिप्त"
        else:
            rule = "अनुमान"
        pending_labels.clear()
        group_rows += 1
        rows.append(
            {
                "formula_tex": _proof_formula(value),
                "rule": rule,
                "group": group,
            }
        )
    assert rows, number
    groups = max(row["group"] for row in rows)
    caption = (
        "मूळ मजकुरातील नियम-आकृती; पायऱ्या स्रोतक्रमाने दिल्या आहेत"
        if environment == "defish"
        else "मूळ मजकुरातील सिद्धता-वृक्ष; पायऱ्या स्रोतक्रमाने दिल्या आहेत"
    )
    if groups > 1:
        caption += f"; {groups} स्वतंत्र सिद्धता-आकृत्या"
    return {
        "id": f"proof-auto-{number:03d}",
        "section_id": None,
        "caption": caption,
        "environment": environment,
        "required": [],
        "rows": rows,
        "groups": groups,
        "representation": "accessible source-order step table",
    }


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
            assert pos < len(text), (command, text[start : start + 80])
            if text[pos] == "{":
                value, pos = _balanced(text, pos)
            elif text[pos] == "\\":
                token = re.match(r"\\(?:[A-Za-z]+|.)", text[pos:])
                assert token, (command, text[start : start + 80])
                value = token.group()
                pos += len(value)
            else:
                value = text[pos]
                pos += 1
            args.append(value)
        opt = None
        if optional:
            while pos < len(text) and text[pos].isspace():
                pos += 1
            if pos < len(text) and text[pos] == "[":
                opt, pos = _balanced_square(text, pos)
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
    text = text.replace(r"\Contraction", r"\mathrm{C}")
    text = text.replace(r"\Exchange", r"\mathrm{X}")
    text = text.replace(r"\Cut", r"\mathrm{Cut}")
    text = text.replace(r"\FalseInt{}", r"\bot_I").replace(r"\FalseInt", r"\bot_I")
    text = text.replace(r"\FalseCl{}", r"\bot_C").replace(r"\FalseCl", r"\bot_C")
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
        "Subst",
        3,
        lambda args, _: args[0] + "[" + args[1] + "/" + args[2] + "]",
    )
    text = _replace_args(
        text,
        "Atom",
        2,
        lambda args, _: args[0] + "(" + args[1] + ")",
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
    text = _replace_optional_math_command(
        text,
        "lexists",
        lambda args, bang: r"\exists" + ("!" if bang else "")
        + ((" {" + args[0] + "}") if args else "")
        + (r"\," + args[1] if len(args) > 1 else ""),
        allow_bang=True,
    )
    text = _replace_optional_math_command(
        text,
        "lforall",
        lambda args, _: r"\forall"
        + ((" {" + args[0] + "}") if args else "")
        + (r"\," + args[1] if len(args) > 1 else ""),
    )
    text = _replace_optional_math_command(
        text,
        "eq",
        lambda args, _: (args[0] + "=" + args[1]) if len(args) == 2 else "=",
    )
    text = re.sub(r"\\Obj\s*([A-Za-z])", r"\\mathsf{\1}", text)
    text = text.replace(r"\lif", r"\to")
    text = text.replace(r"\tof", r"\leftrightarrow")
    text = text.replace(r"\lfalse", r"\bot").replace(r"\ltrue", r"\top")
    return text


def expand_reader_math_macros(text):
    """Expand reader-specific math commands to TeX understood by Pandoc."""
    verbatim = []

    def stash_verbatim(match):
        placeholder = f"OPENLOGICVERBATIMPLACEHOLDER{len(verbatim):04d}"
        verbatim.append((placeholder, match.group(0)))
        return placeholder

    text = re.sub(
        r"\\verb\*?(?P<delimiter>[^A-Za-z0-9\s]).*?(?P=delimiter)",
        stash_verbatim,
        text,
        flags=re.S,
    )
    text = text.replace(r"\readerexternalref", r"\readerExternalRef")
    text = re.sub(
        r"\\readerExternalRef\{[^{}]+\}",
        r"\\emph{मूळ ग्रंथातील संबंधित विभाग}",
        text,
    )
    text = re.sub(
        r"\\pValue\{([A-Za-z])([^{}]*)\}",
        r"\\overline{\\mathfrak{\1}\2}",
        text,
    )
    text = re.sub(r"\\pAssign\{([A-Za-z])([^{}]*)\}", r"\\mathfrak{\1}\2", text)
    text = text.replace(r"\pSat/", r"\pSatNeg")
    text = _replace_args(
        text,
        "pSatNeg",
        2,
        lambda args, _: r"\mathfrak{" + args[0] + r"}\nvDash " + args[1],
    )
    text = _replace_args(
        text,
        "pSat",
        2,
        lambda args, _: r"\mathfrak{" + args[0] + r"}\vDash " + args[1],
    )
    text = text.replace(r"\Sat/", r"\SatNeg")
    text = _replace_args(
        text,
        "SatNeg",
        2,
        lambda args, opt: r"\Struct{" + args[0] + "}"
        + (("," + opt) if opt else "")
        + r"\nvDash "
        + args[1],
        optional=True,
    )
    text = _replace_args(
        text,
        "Sat",
        2,
        lambda args, opt: r"\Struct{" + args[0] + "}"
        + (("," + opt) if opt else "")
        + r"\vDash "
        + args[1],
        optional=True,
    )
    text = _replace_args(
        text,
        "Assign",
        2,
        lambda args, _: args[0] + r"^{\Struct{" + args[1] + "}}",
    )
    text = _replace_args(
        text,
        "varAssign",
        3,
        lambda args, opt: (
            args[0] + "=" + args[1] + "[^{" + opt + "}/" + args[2] + "]"
            if opt
            else args[0] + r"\sim_{" + args[2] + "}" + args[1]
        ),
        optional=True,
    )
    text = _replace_args(
        text,
        "Value",
        2,
        lambda args, opt: r"\mathrm{Val}^{\Struct{" + args[1] + "}}"
        + ("_{" + opt + "}" if opt else "")
        + "(" + args[0] + ")",
        optional=True,
    )
    text = _replace_args(
        text,
        "Log",
        1,
        lambda args, opt: r"\mathbf{" + args[0] + "}"
        + ("_{" + opt + "}" if opt else ""),
        optional=True,
    )
    text = _replace_optional_math_command(
        text,
        "Frm",
        lambda args, _: r"\mathrm{Frm}"
        + (r"(\Lang{" + args[0] + "})" if args else ""),
    )
    text = expand_proof_math_macros(text)
    text = re.sub(r"\\Lang\{([A-Za-z])([^{}]*)\}", r"\\mathcal{\1}\2", text)
    text = re.sub(r"\\Lang\s+([A-Za-z])", r"\\mathcal{\1}", text)
    text = re.sub(r"\\Struct\{([A-Za-z])([^{}]*)\}", r"\\mathfrak{\1}\2", text)
    text = re.sub(r"\\Struct\s+([A-Za-z])", r"\\mathfrak{\1}", text)
    text = re.sub(r"\\Obj\s*([A-Za-z])", r"\\mathsf{\1}", text)
    text = text.replace(r"\Entails/", r"\nvDash")
    text = re.sub(r"\\Entails\b", r"\\vDash", text)
    text = text.replace(r"\ident", r"\equiv")
    for placeholder, original in verbatim:
        assert text.count(placeholder) == 1
        text = text.replace(placeholder, original)
    return text
