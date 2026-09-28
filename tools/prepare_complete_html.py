"""Prepare a provisional semantic HTML conversion of the complete reader.

The build report deliberately records missing diagram assets and MathML
fallbacks.  A conversion with either defect is not a releasable reader.
"""

import hashlib
import json
import re
import shutil
import subprocess
from bisect import bisect_right
from copy import deepcopy
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from complete_math_glyphs import extract_symbols
from core_html_proofs import (
    _replace_args,
    _replace_optional_math_command,
    _generic_proof_spec,
    expand_reader_math_macros,
    strip_proof_environments,
)


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
OUTPUT = BUILD / "html"
ASSETS = OUTPUT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_group(value, start, opening, closing):
    assert value[start] == opening
    depth = 1
    cursor = start + 1
    while depth:
        assert cursor < len(value), (opening, value[start:start + 80])
        if value[cursor] == opening and value[cursor - 1] != "\\":
            depth += 1
        elif value[cursor] == closing and value[cursor - 1] != "\\":
            depth -= 1
        cursor += 1
    return value[start + 1:cursor - 1], cursor


def expand_bare_assignment_macros(body):
    """Read xparse's single-token mandatory arguments in valuation notation."""
    for name in ("pValue", "pAssign"):
        pattern = re.compile(rf"\\{name}\b")
        cursor = 0
        while match := pattern.search(body, cursor):
            position = match.end()
            while position < len(body) and body[position].isspace():
                position += 1
            if body[position] == "{":
                argument, position = read_group(body, position, "{", "}")
            elif body[position] == "\\":
                command = re.match(r"\\(?:[A-Za-z]+|.)", body[position:])
                assert command
                argument = command.group()
                position += len(argument)
            else:
                argument = body[position]
                position += 1
            if argument and argument[0].isalpha():
                assignment = r"\mathfrak{" + argument[0] + "}" + argument[1:]
            else:
                assignment = r"\mathfrak{" + argument + "}"
            if name == "pAssign":
                replacement = assignment
            else:
                first_subscript = None
                expression = None
                second_subscript = None
                if position < len(body) and body[position] == "[":
                    first_subscript, position = read_group(body, position, "[", "]")
                if position < len(body) and body[position] == "(":
                    expression, position = read_group(body, position, "(", ")")
                if position < len(body) and body[position] == "[":
                    second_subscript, position = read_group(body, position, "[", "]")
                replacement = r"\overline{" + assignment + "}"
                subscript = first_subscript or second_subscript
                if subscript:
                    replacement += "_{" + subscript + "}"
                if expression is not None:
                    replacement += "(" + expression + ")"
            body = body[:match.start()] + replacement + body[position:]
            cursor = match.start() + len(replacement)
    return body


def expand_model_class_macro(body):
    pattern = re.compile(r"\\Mod\b")
    cursor = 0
    while match := pattern.search(body, cursor):
        position = match.end()
        language = None
        parameter = None
        if position < len(body) and body[position] == "[":
            language, position = read_group(body, position, "[", "]")
        if position < len(body) and body[position] == "(":
            parameter, position = read_group(body, position, "(", ")")
        if position >= len(body) or body[position] != "{":
            cursor = position
            continue
        formula, position = read_group(body, position, "{", "}")
        replacement = r"\mathrm{Mod}"
        if language:
            replacement += r"^{\mathcal{" + language + "}}"
        if parameter:
            replacement += "_{" + parameter + "}"
        replacement += "(" + formula + ")"
        body = body[:match.start()] + replacement + body[position:]
        cursor = match.start() + len(replacement)
    return body


def expand_complete_math_macros(body, preamble):
    """Project later-chapter xparse notation to equivalent plain TeX."""
    body = body.replace(r"\bottomAlignProof", "")
    body = body.replace(r"\Proves", r"\vdash")
    body = body.replace(r"\sFmlaWide", r"\sFmla")
    body = body.replace(r"\pto", r"\rightharpoonup")
    for command, glyph in (
        ("strictif", "\ue001"), ("fishhookright", "\ue001"),
        ("cif", "\ue002"), ("boxright", "\ue002"),
        ("leftrightarroweq", "\ue003"),
    ):
        body = re.sub(rf"\\{command}\b", lambda _, glyph=glyph: glyph, body)
    body = re.sub(
        r"\\inj\[([^]]+)\]\{([^{}]+)\}\{([^{}]+)\}",
        lambda match: r"\iota_{" + match.group(2) + "}^{" + match.group(1) + "}(" + match.group(3) + ")",
        body,
    )
    body = body.replace(r"\lnand", r"\uparrow")
    aliases = re.findall(
        r"\\newcommand\{\\(Log[A-Za-z]+)\}\{\\Log\{([^{}]+)\}\}",
        preamble,
    )
    aliases.append(("LogLuk", "Ł"))
    for name, label in aliases:
        symbol = r"\mathbf{" + label + "}"
        body = re.sub(
            rf"\\{name}\[([^]]+)\]",
            lambda match: symbol + "_{" + match.group(1) + "}",
            body,
        )
        body = re.sub(rf"\\{name}\b", lambda _: symbol, body)
    body = expand_bare_assignment_macros(body)
    body = expand_model_class_macro(body)
    argument_macros = (
        ("Proj", 2, lambda a, o: "P^{" + a[0] + "}_{" + a[1] + "}"),
        ("proj", 2, lambda a, o: r"\pi_{" + a[0] + "}(" + a[1] + ")"),
        ("cfind", 1, lambda a, o: r"\varphi_{" + a[0] + "}" + ("^{" + o + "}" if o else ""), True),
        ("tf", 1, lambda a, o: r"\widetilde{" + a[0] + "}" + ("_{" + o + "}" if o else ""), True),
        ("Ax", 1, lambda a, o: r"\mathrm{" + a[0] + "}"),
        ("Gn", 1, lambda a, o: r"{^{\#}}" + a[0] + r"^{\#}"),
        ("umin", 2, lambda a, o: r"\mu " + a[0] + r"\;" + a[1]),
        ("bmin", 2, lambda a, o: r"(\mathrm{min}\;" + a[0] + r")\," + a[1]),
        ("bexists", 2, lambda a, o: r"(\exists " + a[0] + r")\;" + a[1]),
        ("bforall", 2, lambda a, o: r"(\forall " + a[0] + r")\;" + a[1]),
        ("Complement", 1, lambda a, o: r"\overline{" + a[0] + "}"),
        ("scode", 1, lambda a, o: r"\mathrm{c}_{" + a[0] + "}"),
        ("fact", 1, lambda a, o: a[0] + r"\,!"),
        ("pair", 2, lambda a, o: r"\langle " + a[0] + "," + a[1] + r"\rangle"),
        ("andi", 2, lambda a, o: r"\langle " + a[0] + "," + a[1] + r"\rangle"),
        ("ande", 2, lambda a, o: r"\mathrm{p}_{" + a[0] + "}(" + a[1] + ")"),
        ("ori", 3, lambda a, o: r"\mathrm{in}_{" + a[0] + "}^{" + a[1] + "}(" + a[2] + ")"),
        ("ore", 5, lambda a, o: r"\mathrm{case}(" + a[0] + "," + a[1] + "." + a[2] + "," + a[3] + "." + a[4] + ")"),
        ("dcase", 5, lambda a, o: r"\delta " + a[0] + r"\," + a[1] + "." + a[2] + r"\," + a[3] + "." + a[4]),
        ("abort", 2, lambda a, o: r"\varepsilon^{" + a[0] + "}(" + a[1] + ")"),
        ("maxrank", 1, lambda a, o: r"\mathrm{mr}(" + a[0] + ")"),
        ("maeh", 2, lambda a, o: a[0] + r"\mathrel{;}" + a[1]),
        ("inj", 2, lambda a, o: r"\iota_{" + a[0] + "}(" + a[1] + ")"),
        ("Prop", 2, lambda a, o: r"{[\!\![}" + a[1] + r"{]\!\!]}_{\mathfrak{" + a[0] + "}}"),
        ("rep", 1, lambda a, o: r"\underline{" + a[0] + "}" + ("_{" + o + "}" if o else ""), True),
        ("fregenum", 2, lambda a, o: r"\# " + a[0] + r"\," + a[1]),
        ("TMtrans", 3, lambda a, o: a[0] + "," + a[1] + "," + a[2]),
    )
    for row in argument_macros:
        name, count, formatter, *optional = row
        body = _replace_args(body, name, count, formatter, optional=bool(optional))
    for name, base in (
        ("OProv", r"\mathsf{Prov}"),
        ("Prov", r"\mathrm{Prov}"),
        ("Prf", r"\mathrm{Prf}"),
        ("ORefut", r"\mathsf{Ref}"),
        ("Refut", r"\mathrm{Ref}"),
        ("ORProv", r"\mathsf{RProv}"),
    ):
        body = _replace_optional_math_command(
            body, name, lambda args, _, base=base:
            base + ("_{" + args[0] + "}" if args else ""),
        )
    for name in ("FrmSOL", "TrmSOL"):
        base = r"\mathrm{" + ("Frm" if name == "FrmSOL" else "Trm") + r"}^2"
        body = _replace_optional_math_command(
            body, name, lambda args, _, base=base:
            base + (r"(\mathcal{" + args[0] + "})" if args else ""),
        )
    return body


def split_align_intertext(body):
    """Preserve prose within aligned displays as ordinary HTML paragraphs."""
    marker = r"\intertext{"
    count = 0
    while marker in body:
        start = body.index(marker)
        prose, end = read_group(body, start + len(r"\intertext"), "{", "}")
        choices = [
            (body.rfind(r"\begin{" + env + "}", 0, start), env)
            for env in ("align*", "align", "alignat*", "alignat")
        ]
        align_start, env = max(choices)
        assert align_start >= 0, body[max(0, start - 120):start + 120]
        opening = r"\begin{" + env + "}"
        closing = r"\end{" + env + "}"
        assert body.rfind(closing, align_start, start) < 0
        align_end = body.index(closing, end) + len(closing)
        opening_end = align_start + len(opening)
        if env.startswith("alignat") and body[opening_end] == "{":
            _, opening_end = read_group(body, opening_end, "{", "}")
            opening = body[align_start:opening_end]
        before = body[opening_end:start]
        after = body[end:align_end - len(closing)]
        replacement = (
            opening + before.rstrip() + "\n" + closing + "\n\n"
            + prose + "\n\n"
            + opening + after.lstrip() + closing
        )
        body = body[:align_start] + replacement + body[align_end:]
        count += 1
    return body, count


def normalize_math_layout(body, aux_labels, unresolved_math_text_refs):
    for name in ("shoveleft", "shoveright", "smash"):
        pattern = re.compile(rf"\\{name}\{{")
        cursor = 0
        while match := pattern.search(body, cursor):
            inner, end = read_group(body, match.end() - 1, "{", "}")
            body = body[:match.start()] + inner + body[end:]
            cursor = match.start() + len(inner)
    raisebox_pattern = re.compile(r"\\raisebox\{")
    cursor = 0
    while match := raisebox_pattern.search(body, cursor):
        _, position = read_group(body, match.end() - 1, "{", "}")
        while position < len(body) and body[position].isspace():
            position += 1
        assert body[position] == "{"
        inner, end = read_group(body, position, "{", "}")
        body = body[:match.start()] + inner + body[end:]
        cursor = match.start() + len(inner)
    for label in (
        "सहचारिता", "क्रमनिरपेक्षता", "अविकारक",
        "बेरीज व्यस्त", "वितरणता", "गुणाकार व्यस्त",
    ):
        body = body.replace(r"\emph{" + label + "}", r"\text{" + label + "}")
    body = body.replace(r"\textsc{dual}", r"\mathrm{dual}")
    body = body.replace(r"\rangleP", r"\rangle P")
    body = re.sub(r"\\text\s+\{", lambda _: r"\text{", body)
    body = re.sub(r"\\text\{\\qquad\s*", lambda _: r"\qquad\text{", body)
    text_pattern = re.compile(r"\\text\{")
    cursor = 0
    while match := text_pattern.search(body, cursor):
        inner, end = read_group(body, match.end() - 1, "{", "}")
        original_inner = inner
        inner = re.sub(
            r"\\textsc\{([^{}]*)\}",
            lambda nested: nested.group(1),
            inner,
        )
        inner = inner.replace(r"\Taut", "taut").replace(r"\PL", "pl")
        for command, key in re.findall(r"\\(ref|cref|eqref)\{([^}]+)\}", inner):
            if key in aux_labels:
                number = aux_labels[key].strip("{}")
                if command == "eqref":
                    number = "(" + number + ")"
                inner = inner.replace("\\" + command + "{" + key + "}", number)
            else:
                unresolved_math_text_refs.add(key)
        if inner.count("$") >= 2 and inner.count("$") % 2 == 0:
            segments = inner.split("$")
            replacement = ""
            for index, segment in enumerate(segments):
                if index % 2 == 0:
                    if segment:
                        replacement += r"\text{" + segment + "}"
                else:
                    replacement += r"\," + segment + r"\,"
            body = body[:match.start()] + replacement + body[end:]
            cursor = match.start() + len(replacement)
        elif inner != original_inner:
            replacement = r"\text{" + inner + "}"
            body = body[:match.start()] + replacement + body[end:]
            cursor = match.start() + len(replacement)
        else:
            cursor = end
    tag_pattern = re.compile(r"\\tag(\*)?\{")
    cursor = 0
    while match := tag_pattern.search(body, cursor):
        inner, end = read_group(body, match.end() - 1, "{", "}")
        inner = inner.replace("$", "")
        replacement = r"\qquad " + (inner if match.group(1) else "(" + inner + ")")
        body = body[:match.start()] + replacement + body[end:]
        cursor = match.start() + len(replacement)
    return body


def localize_math_only_commands(body):
    def replace(segment):
        segment = segment.replace(r"\Dual", r"\mathrm{dual}")
        segment = segment.replace(r"\Nec", r"\mathrm{nec}")
        segment = re.sub(
            r"\\textsc\{([^{}]*)\}",
            lambda match: r"\mathrm{" + match.group(1) + "}",
            segment,
        )
        return re.sub(
            r"\\emph\{([^{}]*)\}",
            lambda match: r"\text{" + match.group(1) + "}",
            segment,
        )
    for env in ("align*", "align", "equation*", "equation", "gather*", "gather",
                "multline*", "multline", "cases", "array"):
        pattern = re.compile(
            r"(\\begin\{" + re.escape(env) + r"\})(.*?)(\\end\{" + re.escape(env) + r"\})",
            re.S,
        )
        body = pattern.sub(lambda match: match.group(1) + replace(match.group(2)) + match.group(3), body)
    for pattern in (
        re.compile(r"(?<!\\)\$((?:\\.|[^$])*)\$", re.S),
        re.compile(r"(?<!\\)\\\[(.*?)(?<!\\)\\\]", re.S),
        re.compile(r"(?<!\\)\\\((.*?)(?<!\\)\\\)", re.S),
    ):
        body = pattern.sub(
            lambda match: match.group().replace(match.group(1), replace(match.group(1)), 1),
            body,
        )
    return body


source = BUILD / "openlogic-mr-full.tex"
inputs = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert sha(source) == inputs["reader_sha256"]
tex = source.read_text(encoding="utf-8")
anchor_repairs = (
    "inc:inp:2in:G2-3", "inc:inp:2in:G2-5",
    "inc:inp:2in:G2-6", "inc:inp:2in:G2-8",
    "nml:tab:rul:tab:prop-rules",
    "int:tab:rul:tab:prop-rules", "int:tab:rul:tab:rules-lif-lnot",
    "pt:nor:red:tab:reduction-conversions", "pt:seq:int:tab:G3c",
)
for key in anchor_repairs:
    label = r"\label{" + key + "}"
    label_at = tex.index(label)
    candidates = []
    for env in ("table", "align", "align*", "equation", "equation*", "gather", "gather*"):
        opening = r"\begin{" + env + "}"
        closing = r"\end{" + env + "}"
        begin_at = tex.rfind(opening, 0, label_at)
        if begin_at >= 0 and tex.find(closing, begin_at, label_at) < 0:
            candidates.append(begin_at)
    assert candidates, key
    insert_at = max(candidates)
    tex = tex[:insert_at] + r"\hypertarget{" + key + "}{}" + "\n" + tex[insert_at:]
tex, proofs = strip_proof_environments(tex)
center_balance = (tex.count(r"\begin{center}"), tex.count(r"\end{center}"))
proof_command = re.compile(r"\\(?:AxiomC?|UnaryInfC?|BinaryInfC?|TrinaryInfC?)\b")
display_pattern = re.compile(r"(?<!\\)\\\[.*?(?<!\\)\\\]", re.S)
extra_displays = [match for match in display_pattern.finditer(tex) if proof_command.search(match.group())]
extra_proofs = []
for number, match in enumerate(extra_displays, 1):
    spec = _generic_proof_spec(match.group(), number, "display")
    spec["id"] = f"proof-display-{number:03d}"
    spec["placeholder"] = f"OPENLOGICEXTRAPROOFPLACEHOLDER{number:04d}"
    spec["labels"] = re.findall(r"\\label\{([^}]+)\}", match.group())
    extra_proofs.append(spec)
for match, spec in reversed(list(zip(extra_displays, extra_proofs))):
    tex = tex[:match.start()] + "\n\n" + spec["placeholder"] + "\n\n" + tex[match.end():]
assert (tex.count(r"\begin{center}"), tex.count(r"\end{center}")) == center_balance
for env in ("gather*", "gather", "multline*", "multline", "align*", "align"):
    pattern = re.compile(
        r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"\}",
        re.S,
    )
    matches = [match for match in pattern.finditer(tex) if proof_command.search(match.group())]
    specs = []
    for match in matches:
        number = len(extra_proofs) + len(specs) + 1
        spec = _generic_proof_spec(match.group(), number, "display")
        spec["id"] = f"proof-display-{number:03d}"
        spec["placeholder"] = f"OPENLOGICEXTRAPROOFPLACEHOLDER{number:04d}"
        spec["labels"] = re.findall(r"\\label\{([^}]+)\}", match.group())
        specs.append(spec)
    for match, spec in reversed(list(zip(matches, specs))):
        tex = tex[:match.start()] + "\n\n" + spec["placeholder"] + "\n\n" + tex[match.end():]
    extra_proofs.extend(specs)
proofs.extend(extra_proofs)
sideways_pattern = re.compile(r"\\begin\{sidewaysfigure\}.*?\\end\{sidewaysfigure\}", re.S)
sideways_proofs = [match for match in sideways_pattern.finditer(tex) if proof_command.search(match.group())]
assert len(sideways_proofs) == 1, len(sideways_proofs)
for number, match in reversed(list(enumerate(sideways_proofs, 1))):
    spec = _generic_proof_spec(match.group(), number, "sidewaysfigure")
    spec["id"] = f"proof-sideways-{number:03d}"
    spec["placeholder"] = f"OPENLOGICEXTRAPROOFPLACEHOLDER{len(extra_proofs) + number:04d}"
    spec["caption"] = "Ł₃ मधील निष्पत्तीचे उदाहरण"
    spec["labels"] = re.findall(r"\\label\{([^}]+)\}", match.group())
    proofs.append(spec)
    tex = tex[:match.start()] + "\n\n" + spec["placeholder"] + "\n\n" + tex[match.end():]

# Every drawing gets a stable reference to a PDF-derived SVG asset.  The
# eventual asset pass must supply a checked SVG and Marathi alt text for each.
diagrams = []
asset_pattern = re.compile(r"\\olasset(?:\[[^]]+\])?\{assets/diagrams/([^}]+)\.tikz\}")
def asset_ref(match):
    name = match.group(1)
    diagrams.append({"number": len(diagrams) + 1, "kind": "source-asset", "name": name})
    return r"\includegraphics{assets/" + name + ".svg}"
tex = asset_pattern.sub(asset_ref, tex)

tikz_pattern = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.S)
def tikz_ref(match):
    number = len(diagrams) + 1
    name = f"tikz-{number:03d}"
    diagrams.append({
        "number": number,
        "kind": "inline-tikz",
        "name": name,
        "source_sha256": hashlib.sha256(match.group().encode("utf-8")).hexdigest(),
        "source": match.group(),
    })
    return r"\includegraphics{assets/" + name + ".svg}"
tex = tikz_pattern.sub(tikz_ref, tex)
assert len(diagrams) == 70, len(diagrams)

# An align containing the two small graph drawings also contains prose
# between rows; Pandoc must see separate blocks to retain their order.
graph_pattern = re.compile(
    r"\\begin\{align\*\}\s*&\s*\\includegraphics\{assets/tikz-\d+\.svg\}.*?"
    r"\\intertext\{(?P<prose>.*?)\}\s*&\s*"
    r"\\includegraphics\{assets/tikz-\d+\.svg\}.*?\\end\{align\*\}",
    re.S,
)
graph_match = graph_pattern.search(tex)
if graph_match:
    graph_images = re.findall(r"\\includegraphics\{[^}]+\}", graph_match.group())
    assert len(graph_images) == 2
    replacement = (
        r"\begin{center}" + graph_images[0] + r"\end{center}" + "\n\n"
        + graph_match.group("prose") + "\n\n"
        + r"\begin{center}" + graph_images[1] + r"\end{center}"
    )
    tex = tex[:graph_match.start()] + replacement + tex[graph_match.end():]

tex, centered_diagrams = re.subn(
    r"\\\[\s*(\\includegraphics\{assets/[^}]+\.svg\})\s*\\\]",
    lambda match: r"\begin{center}" + match.group(1) + r"\end{center}",
    tex,
)
tex, centered_table_count = re.subn(
    r"\\\[\s*\\centering\s*(\\begin\{tabular\}.*?\\end\{tabular\})\s*\\\]",
    lambda match: r"\begin{center}" + match.group(1) + r"\end{center}",
    tex,
    flags=re.S,
)
assert centered_table_count == 1, centered_table_count

head, marker, body = tex.partition(r"\begin{document}")
assert marker
wide_definition = r"\NewDocumentCommand{\sFmlaWide}{m m o}"
wide_at = body.index(wide_definition)
wide_argument = body.index("{", wide_at + len(wide_definition))
_, wide_end = read_group(body, wide_argument, "{", "}")
body = body[:wide_at] + body[wide_end:]
for command, replacement in (
    ("redone", r"\xrightarrow{\1}"),
    ("redpar", r"\overset{\1}{\Longrightarrow}"),
    ("red", r"\overset{\1}{\Rightarrow}"),
    ("equal", r"\overset{\1}{\equiv}"),
):
    pattern = rf"\\{command}\[([^]]+)\]"
    head = re.sub(pattern, lambda match: replacement.replace(r"\1", match.group(1)), head)
    body = re.sub(pattern, lambda match: replacement.replace(r"\1", match.group(1)), body)
for command, replacement in (
    ("redone", r"\rightarrow"),
    ("redpar", r"\Longrightarrow"),
    ("red", r"\Rightarrow"),
    ("equal", r"\equiv"),
):
    body = re.sub(rf"\\{command}(?![A-Za-z])", lambda _: replacement, body)
body = body.replace(r"\nicefrac", r"\frac")
body = body.replace(r"\sFmlaWide", r"\sFmla")
body = body.replace(r"\LeftR\Weakening", r"\mathrm{W}\mathrm{L}")
body = expand_reader_math_macros(body)
body = expand_complete_math_macros(body, head)
aux_path = BUILD / "openlogic-mr-full.aux"
aux_text = aux_path.read_text(encoding="utf-8") if aux_path.exists() else ""
aux_labels = dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}", aux_text))
unresolved_math_text_refs = set()
body = normalize_math_layout(body, aux_labels, unresolved_math_text_refs)
body = body.replace(r"\/", "")
body, intertext_count = split_align_intertext(body)
body = localize_math_only_commands(body)
tex = head + marker + body
html_input = BUILD / "html-full-input.tex"
html_input.write_text(tex, encoding="utf-8", newline="\n")

for name in ("OLMarathiSerif-Regular.ttf", "OLMarathiSerif-Bold.ttf", "OFL.txt"):
    destination = OUTPUT / "fonts" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "fonts" / name, destination)

css = """
@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Regular.ttf)}
@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Bold.ttf);font-weight:bold}
*{box-sizing:border-box}html{scroll-behavior:smooth;overflow-x:hidden}
body{font-family:OLMarathi,serif;line-height:1.75;margin:0 auto;padding:2rem 1.25rem 5rem;max-width:62rem;color:#202124;background:#fff;overflow-wrap:break-word}
main{min-width:0;overflow-x:clip}
h1,h2,h3{line-height:1.4;scroll-margin-top:1rem}
a{color:#064c8c}a:focus-visible{outline:3px solid #a81c21;outline-offset:3px}
img{max-width:100%;height:auto;display:block;margin:1rem auto}
math img.math-glyph{display:inline;width:auto;margin:0;max-width:none}
math[display="block"]{display:block;max-width:100%;overflow-x:auto;padding:.7rem 0}
math:not([display="block"]){display:inline-block;max-width:100%;overflow-x:auto;vertical-align:middle}
math mtext{font-family:OLMarathi,serif;font-style:normal}
.proof{border-left:3px solid #ddd;padding-left:1rem;overflow-x:auto}
.proof-steps{border-collapse:collapse;margin:.75rem auto}
.proof-steps th,.proof-steps td{border-bottom:1px solid #ddd;padding:.35rem .8rem;text-align:left;vertical-align:top}
.inline-math-symbol{display:inline-block;margin:0 .08em;vertical-align:middle;height:.58em;width:auto}
.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:1rem;top:1rem;background:white;z-index:2}
#TOC{background:#f3f5f7;padding:1rem 1.5rem;border-radius:.3rem}
@media(max-width:600px){body{font-size:1.06rem;padding:.9rem}}
""".strip()
(OUTPUT / "reader.css").write_text(css + "\n", encoding="utf-8", newline="\n")
pandoc = shutil.which("pandoc")
assert pandoc
result = subprocess.run(
    [pandoc, str(html_input), "--from=latex", "--to=html5", "--standalone",
     "--mathml", "--toc", "--metadata=lang:mr",
     "--metadata=title:मुक्त तर्कशास्त्र — संपूर्ण मराठी आवृत्ती",
     "--metadata=toc-title:अनुक्रमणिका", "--css=reader.css",
     "--output=" + str(OUTPUT / "index.html")],
    capture_output=True, text=True, encoding="utf-8", timeout=300,
)
(BUILD / "HTML_BUILD_LOG.txt").write_text(result.stderr, encoding="utf-8")
assert result.returncode == 0, result.stderr[:4000]

soup = BeautifulSoup((OUTPUT / "index.html").read_text(encoding="utf-8"), "html.parser")
body_node = soup.body
assert body_node
main = soup.new_tag("main", id="main-content")
for child in list(body_node.contents):
    main.append(child.extract())
body_node.append(main)
skip = soup.new_tag("a", href="#main-content", attrs={"class": "skip-link"})
skip.string = "मुख्य मजकुराकडे जा"
body_node.insert(0, skip)
localized_proof_headings = 0
for emphasis in soup.find_all("em"):
    if emphasis.get_text(strip=True) == "Proof.":
        emphasis.string = "सिद्धता."
        localized_proof_headings += 1

core_assets = ROOT / "build/core/html/assets"
core_receipt = json.loads((ROOT / "build/core/HTML_BUILD_RECEIPT.json").read_text(encoding="utf-8"))
inherited = {Path(entry["filename"]).stem: entry for entry in core_receipt["diagram_assets"]}
inherited_names = {
    "union": "union", "intersection": "intersection", "difference": "difference",
    "function": "function", "surjective": "surjective", "injective": "injective",
    "bijective": "bijective", "composition": "composition",
    "tikz-010": "graph-four", "tikz-011": "graph-three",
    "tikz-012": "tree", "tikz-013": "root-two-square",
    "tikz-014": "hilberts-hotel",
}
for target, inherited_name in inherited_names.items():
    source_asset = core_assets / (inherited_name + ".svg")
    assert source_asset.is_file()
    assert sha(source_asset) == inherited[inherited_name]["sha256"]
    destination = ASSETS / (target + ".svg")
    shutil.copyfile(source_asset, destination)
    for image in soup.select('img[src="assets/' + target + '.svg"]'):
        image["alt"] = inherited[inherited_name]["alt"]

diagram_receipt_path = BUILD / "HTML_DIAGRAM_RECEIPT.json"
diagram_receipt = json.loads(diagram_receipt_path.read_text(encoding="utf-8"))
assert diagram_receipt["source_tex_sha256"] == sha(source)
diagram_assets = {entry["name"]: entry for entry in diagram_receipt["assets"]}
assert len(diagram_assets) == 57
for name, entry in diagram_assets.items():
    assert name in {diagram["name"] for diagram in diagrams}
    assert sha(ASSETS / entry["filename"]) == entry["sha256"]
for image in soup.select('img[src^="assets/"]'):
    name = Path(image.get("src", "")).stem
    if name in diagram_assets:
        image["alt"] = diagram_assets[name]["alt"]

glyph_source_pdf = BUILD / "openlogic-mr-full.pdf"
glyph_receipt = extract_symbols(glyph_source_pdf, ASSETS) if glyph_source_pdf.is_file() else None
assert glyph_receipt is not None
glyph_by_name = {entry["name"]: entry for entry in glyph_receipt["glyphs"]}
glyphs = {
    "\ue001": glyph_by_name["strict"],
    "\ue002": glyph_by_name["squareright"],
    "\ue003": glyph_by_name["leftrightarroweq"],
}
for annotation in soup.find_all("annotation", attrs={"encoding": "application/x-tex"}):
    if annotation.string:
        annotation.string.replace_with(
            str(annotation.string).replace("\ue001", r"\fishhookright")
            .replace("\ue002", r"\boxright")
            .replace("\ue003", r"\leftrightarroweq")
        )
for token in list(soup.select("math mi, math mo")):
    if token.get_text() not in glyphs:
        continue
    glyph = glyphs[token.get_text()]
    x0, y0, x1, y1 = glyph["bounds_font_units"]
    operator = soup.new_tag("mo", attrs={"class": "math-glyph-operator"})
    symbol = soup.new_tag("img", attrs={
        "src": "assets/" + glyph["filename"],
        "alt": glyph["alt"],
        "class": "math-glyph",
        "style": f"height:{(y1 - y0 + 16) / 1000:.3f}em;vertical-align:{y0 / 1000:.3f}em",
    })
    operator.append(symbol)
    token.replace_with(operator)
for string in list(soup.find_all(string=re.compile("[\ue001\ue002\ue003]"))):
    if string.parent.name in ("math", "mo", "mi", "annotation", "mglyph"):
        continue
    parts = re.split("([\ue001\ue002\ue003])", str(string))
    replacements = []
    for part in parts:
        if not part:
            continue
        if part not in glyphs:
            replacements.append(NavigableString(part))
            continue
        glyph = glyphs[part]
        image = soup.new_tag("img", attrs={
            "src": "assets/" + glyph["filename"],
            "alt": glyph["alt"],
            "class": "inline-math-symbol",
        })
        replacements.append(image)
    string.replace_with(*replacements)

combined_references = []
for link in list(soup.select('a[data-reference-type="ref+label"]')):
    keys = link.get("data-reference", "").split(",")
    if len(keys) < 2:
        continue
    replacement = []
    for index, key in enumerate(keys):
        target = soup.find(id=key)
        assert target is not None, key
        number = target.find("strong")
        if number is not None:
            visible = number.get_text(" ", strip=True)
        else:
            visible = "तक्ता " + key.rsplit(":", 1)[-1]
        anchor = soup.new_tag("a", href="#" + key)
        anchor.string = visible
        if index:
            replacement.append(NavigableString(" आणि "))
        replacement.append(anchor)
    link.replace_with(*replacement)
    combined_references.append(keys)

proof_formulae = list(dict.fromkeys(
    expand_complete_math_macros(expand_reader_math_macros(row["formula_tex"]), head)
    for spec in proofs for row in spec["rows"]
))
proof_conversion = subprocess.run(
    [pandoc, "--from=markdown", "--to=html5", "--mathml"],
    input="\n\n".join("$" + formula + "$" for formula in proof_formulae),
    capture_output=True, text=True, encoding="utf-8", timeout=120,
)
assert proof_conversion.returncode == 0 and not proof_conversion.stderr, proof_conversion.stderr[:4000]
proof_nodes = BeautifulSoup(proof_conversion.stdout, "html.parser").find_all("math")
assert len(proof_nodes) == len(proof_formulae)
proof_math = dict(zip(proof_formulae, proof_nodes))
placeholder_nodes = {}
for string in soup.find_all(string=re.compile(r"OPENLOGIC(?:EXTRA)?PROOFPLACEHOLDER[0-9]+")):
    found = re.search(r"OPENLOGIC(?:EXTRA)?PROOFPLACEHOLDER[0-9]+", str(string))
    if found:
        placeholder_nodes[found.group()] = string
assert len(placeholder_nodes) == len(proofs)
for spec in proofs:
    figure = soup.new_tag("figure", attrs={
        "class": "proof", "id": spec["id"],
        "aria-labelledby": spec["id"] + "-caption",
    })
    caption = soup.new_tag("figcaption", id=spec["id"] + "-caption")
    caption.string = spec["caption"]
    figure.append(caption)
    table = soup.new_tag("table", attrs={"class": "proof-steps"})
    header = soup.new_tag("tr")
    for label in ("पायरी", "सूत्र", "नियम किंवा कारण"):
        cell = soup.new_tag("th", scope="col")
        cell.string = label
        header.append(cell)
    thead = soup.new_tag("thead")
    thead.append(header)
    table.append(thead)
    tbody = soup.new_tag("tbody")
    for number, row in enumerate(spec["rows"], 1):
        tr = soup.new_tag("tr")
        number_cell = soup.new_tag("td")
        number_cell.string = str(number)
        formula_cell = soup.new_tag("td")
        formula_cell.append(deepcopy(proof_math[
            expand_complete_math_macros(expand_reader_math_macros(row["formula_tex"]), head)
        ]))
        rule_cell = soup.new_tag("td")
        rule_cell.string = row["rule"]
        tr.extend((number_cell, formula_cell, rule_cell))
        tbody.append(tr)
    table.append(tbody)
    figure.append(table)
    marker_text = placeholder_nodes[spec["placeholder"]]
    paragraph = marker_text.parent
    if paragraph.name == "p" and paragraph.get_text(" ", strip=True) == spec["placeholder"]:
        paragraph.replace_with(figure)
    else:
        paragraph.insert_before(figure)
        marker_text.replace_with(str(marker_text).replace(spec["placeholder"], "", 1))
    for label in spec.get("labels", []):
        anchor = soup.new_tag("span", id=label)
        anchor["data-label"] = label
        figure.insert_before(anchor)

math_row_anchors = []
existing_ids = {node["id"] for node in soup.select("[id]")}
for formula in soup.select("math"):
    annotation = formula.find("annotation", attrs={"encoding": "application/x-tex"})
    if annotation is None:
        continue
    for match in re.finditer(r"\\label\{([^}]+)\}", annotation.get_text()):
        key = match.group(1)
        if key in existing_ids:
            continue
        anchor = soup.new_tag("span", id=key)
        anchor["data-label"] = key
        formula.insert_before(anchor)
        existing_ids.add(key)
        math_row_anchors.append(key)

seen_ids = set()
renamed_duplicate_ids = []
for node in soup.select("[id]"):
    key = node["id"]
    if key not in seen_ids:
        seen_ids.add(key)
        continue
    suffix = 2
    while f"{key}-alt{suffix}" in seen_ids:
        suffix += 1
    new_key = f"{key}-alt{suffix}"
    node["id"] = new_key
    seen_ids.add(new_key)
    renamed_duplicate_ids.append({"original": key, "new": new_key})

ids = [node["id"] for node in soup.select("[id]")]
broken = [a["href"] for a in soup.select('a[href^="#"]') if a["href"][1:] not in ids]
fallbacks = re.findall(r"\[WARNING\] Could not convert TeX math", result.stderr)
missing_assets = [
    entry["name"] for entry in diagrams
    if not (ASSETS / (entry["name"] + ".svg")).is_file()
]
report = {
    "schema": "openlogic-full-html-build/1",
    "status": "provisional",
    "source_tex_sha256": sha(source),
    "html_input_sha256": sha(html_input),
    "html_sha256": None,
    "source_units": inputs["represented_unit_count"],
    "proof_representations": len(proofs),
    "display_proof_representations": len(extra_proofs),
    "localized_proof_headings": localized_proof_headings,
    "diagram_count": len(diagrams),
    "diagram_receipt_sha256": sha(diagram_receipt_path),
    "diagram_source_pdf_sha256": diagram_receipt["source_pdf_sha256"],
    "diagram_asset_count": len(diagram_assets),
    "custom_math_glyphs": glyph_receipt,
    "combined_references_split": combined_references,
    "html_aux_sha256": sha(aux_path) if aux_path.exists() else None,
    "unresolved_math_text_refs": sorted(unresolved_math_text_refs),
    "centered_diagrams": centered_diagrams,
    "intertext_paragraphs": intertext_count,
    "missing_diagram_assets": missing_assets,
    "mathml_count": len(soup.select("math")),
    "math_fallback_warnings": len(fallbacks),
    "math_row_anchors": math_row_anchors,
    "renamed_duplicate_ids": renamed_duplicate_ids,
    "duplicate_id_count": len(ids) - len(set(ids)),
    "broken_local_links": len(broken),
    "broken_local_link_examples": broken[:20],
}
(OUTPUT / "index.html").write_text(str(soup) + "\n", encoding="utf-8", newline="\n")
report["html_sha256"] = sha(OUTPUT / "index.html")
(BUILD / "HTML_PROVISIONAL_REPORT.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
original_tex = source.read_text(encoding="utf-8")
original_assets = list(asset_pattern.finditer(original_tex))
original_tikz = list(tikz_pattern.finditer(original_tex))
assert len(original_assets) == 9 and len(original_tikz) == 61
figure_starts = [match.start() for match in re.finditer(r"\\begin\{figure\}(?:\[[^]]+\])?", original_tex)]
figure_ends = [match.start() for match in re.finditer(r"\\end\{figure\}", original_tex)]
for kind, matches in (("source-asset", original_assets), ("inline-tikz", original_tikz)):
    entries = [entry for entry in diagrams if entry["kind"] == kind]
    assert len(entries) == len(matches)
    for entry, match in zip(entries, matches):
        assert kind == "source-asset" or entry["source_sha256"] == hashlib.sha256(
            match.group().encode("utf-8")
        ).hexdigest()
        entry["source_line"] = original_tex.count("\n", 0, match.start()) + 1
        figure_start_index = bisect_right(figure_starts, match.start()) - 1
        figure_end_index = bisect_right(figure_ends, match.start()) - 1
        figure_start = figure_starts[figure_start_index] if figure_start_index >= 0 else -1
        figure_end_before = figure_ends[figure_end_index] if figure_end_index >= 0 else -1
        if figure_start > figure_end_before:
            figure_end = original_tex.index(r"\end{figure}", match.end())
            figure = original_tex[figure_start:figure_end]
            caption_match = re.search(r"\\caption(?:\[[^]]+\])?\{", figure)
            if caption_match:
                caption, _ = read_group(figure, caption_match.end() - 1, "{", "}")
                entry["caption_tex"] = caption
            entry["figure_labels"] = re.findall(r"\\label\{([^}]+)\}", figure)
(BUILD / "HTML_DIAGRAM_INVENTORY.json").write_text(
    json.dumps(diagrams, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "status": report["status"],
    "source_units": report["source_units"],
    "proof_representations": report["proof_representations"],
    "diagram_count": report["diagram_count"],
    "missing_diagram_assets": len(report["missing_diagram_assets"]),
    "mathml_count": report["mathml_count"],
    "math_fallback_warnings": report["math_fallback_warnings"],
    "duplicate_id_count": report["duplicate_id_count"],
    "broken_local_links": report["broken_local_links"],
    "html_sha256": report["html_sha256"],
}, ensure_ascii=False))
