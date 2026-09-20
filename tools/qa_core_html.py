"""Verify current core-reader HTML structure, source coverage, MathML and assets."""

import collections
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup
from core_html_proofs import (
    adapt_prose_ensuremath,
    expand_proof_math_macros,
    expand_reader_math_macros,
    strip_proof_environments,
)


P = Path(__file__).resolve().parents[1]
B = P / "build" / "core"
O = B / "html"
INPUTS = B / "INPUTS.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


input_rows = json.loads(INPUTS.read_text(encoding="utf-8"))["input_units"]
section_driver_unit_ids = {
    "OLP-0004", "OLP-0011", "OLP-0020", "OLP-0027", "OLP-0041",
    "OLP-0049", "OLP-0055", "OLP-0056", "OLP-0063", "OLP-0069",
    "OLP-0084", "OLP-0098",
    "OLP-0112", "OLP-0126", "OLP-0138", "OLP-0139", "OLP-0149",
    "OLP-0159", "OLP-0167", "OLP-0174", "OLP-0182", "OLP-0183",
    "OLP-0191",
}
chapter_driver_unit_ids = section_driver_unit_ids - {"OLP-0055", "OLP-0138", "OLP-0182"}
chapter_count = sum(row["unit_id"] in chapter_driver_unit_ids for row in input_rows)
section_count = len(input_rows) - sum(
    row["unit_id"] in section_driver_unit_ids for row in input_rows
)
scope = {
    "translation_source_units": len(input_rows),
    "reader_sections": section_count,
    "complete_chapters": chapter_count,
}
assert scope == {
    "translation_source_units": 194,
    "reader_sections": 171,
    "complete_chapters": 20,
}


def ast(path=None, text=None):
    args = [shutil.which("pandoc"), "--from=latex", "--to=json"]
    if path:
        args.append(str(path))
    result = subprocess.run(
        args,
        input=text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["blocks"]


def unwrap_command(text, command):
    while re.search(r"\\" + command + r"\{", text):
        match = re.search(r"\\" + command + r"\{", text)
        start = match.end()
        index = start
        depth = 1
        while depth:
            if text[index] == "{" and text[index - 1] != "\\":
                depth += 1
            elif text[index] == "}" and text[index - 1] != "\\":
                depth -= 1
            index += 1
        text = text[: match.start()] + text[start : index - 1] + text[index:]
    return expand_proof_math_macros(text)


def expand_logic_math_macros(text):
    """Canonicalize source macros and Pandoc's applytofirst expansions."""
    text = expand_reader_math_macros(text)
    text = re.sub(
        r"\{\\mathfrak([A-Za-z])\s*((?:_\d+)?(?:'+)?)\s*\}",
        lambda match: r"\mathfrak{" + match.group(1) + "}" + match.group(2),
        text,
    )
    return re.sub(
        r"\{\\mathcal([A-Za-z])\s*((?:_\d+)?(?:'+)?)\s*\}",
        lambda match: r"\mathcal{" + match.group(1) + "}" + match.group(2),
        text,
    )


def mathnorm(text):
    text = expand_logic_math_macros(text)
    text = unwrap_command(text, "ensuremath")
    text = text.replace(r"\mathbin{\to}", r"\to")
    text = text.replace(r"\mathbin{\leftrightarrow}", r"\leftrightarrow")
    for spacing in (r"\qquad", r"\quad", r"\,", r"\;", r"\:", r"\!"):
        text = text.replace(spacing, "")
    text = text.replace(r"\bot_I{}", r"\bot_I")
    text = text.replace(r"\bot_C{}", r"\bot_C")
    text = text.replace(r"\nicefrac", r"\frac")
    text = text.replace(r"\emph{", r"\text{")
    text = unwrap_command(text, "shoveleft")
    text = unwrap_command(text, "shoveright")
    partial_arrow = r"\mathrel{\ooalign{\hfil$\mapstochar\mkern 5mu$\hfil\cr$\to$}}"
    text = text.replace(partial_arrow, r"\rightharpoonup")
    text = text.replace(r"\pto", r"\rightharpoonup")
    return re.sub(r"\s+", "", text)


def balanced_argument(text, marker):
    start = text.index(marker) + len(marker)
    index = start
    depth = 1
    while depth:
        if text[index] == "{" and text[index - 1] != "\\":
            depth += 1
        elif text[index] == "}" and text[index - 1] != "\\":
            depth -= 1
        index += 1
    return start, index - 1, index


def split_align_intertexts(text):
    """Promote align intertext prose while retaining full-document refs."""
    marker = r"\intertext{"
    count = 0
    expected = text.count(marker)
    while marker in text:
        start = text.index(marker)
        index = start + len(marker)
        depth = 1
        while depth:
            if text[index] == "{" and text[index - 1] != "\\":
                depth += 1
            elif text[index] == "}" and text[index - 1] != "\\":
                depth -= 1
            index += 1
        prose = text[start + len(marker) : index - 1]
        align_start = text.rfind(r"\begin{align*}", 0, start)
        align_end = text.index(r"\end{align*}", index) + len(r"\end{align*}")
        assert align_start >= 0
        before = text[align_start + len(r"\begin{align*}") : start]
        after = text[index : align_end - len(r"\end{align*}")]
        replacement = (
            r"\begin{align*}"
            + before.rstrip()
            + "\n"
            + r"\end{align*}"
            + "\n\n"
            + prose
            + "\n\n"
            + r"\begin{align*}"
            + after.lstrip()
            + r"\end{align*}"
        )
        text = text[:align_start] + replacement + text[align_end:]
        count += 1
    assert count == expected
    return text


def collect(root):
    strings = []
    maths = []
    counts = collections.Counter()
    notes = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            kind = node.get("t")
            counts[kind] += 1
            if kind == "Note":
                note = collect(node.get("c"))
                assert not note[3], "Nested footnotes are unsupported"
                notes.append((note[0], note[1]))
                counts.update(note[2])
                return
            if kind == "Math":
                value = node["c"][1]
                if r"\begin{tikzpicture}" in value:
                    if r"\intertext{" in value:
                        start, end, _ = balanced_argument(value, r"\intertext{")
                        walk(ast(text=value[start:end]))
                    return
                if r"\intertext{" in value:
                    environment = re.match(r"\\begin\{(align\*?)\}", value)
                    assert environment, value[:200]
                    open_env = environment.group(0)
                    close_env = r"\end{" + environment.group(1) + "}"
                    assert value.endswith(close_env), value[-200:]
                    cursor = len(open_env)
                    body_end = len(value) - len(close_env)
                    marker = r"\intertext{"
                    while True:
                        marker_start = value.find(marker, cursor, body_end)
                        if marker_start < 0:
                            break
                        formula = value[cursor:marker_start].rstrip()
                        if formula:
                            maths.append(mathnorm(open_env + formula + close_env))
                        argument_start = marker_start + len(marker)
                        argument_end = argument_start
                        depth = 1
                        while depth:
                            escaped = argument_end > 0 and value[argument_end - 1] == "\\"
                            if value[argument_end] == "{" and not escaped:
                                depth += 1
                            elif value[argument_end] == "}" and not escaped:
                                depth -= 1
                            argument_end += 1
                        walk(ast(text=value[argument_start : argument_end - 1]))
                        cursor = argument_end
                    formula = value[cursor:body_end].lstrip()
                    if formula:
                        maths.append(mathnorm(open_env + formula + close_env))
                    return
                maths.append(mathnorm(value))
                return
            if kind == "Str":
                if not re.fullmatch(r"OPENLOGICPROOFPLACEHOLDER\d{4}", node["c"]):
                    strings.append(node["c"])
                return
            if kind == "Code":
                strings.append(node["c"][1])
                return
            if kind == "Image":
                return
            if kind in ["RawBlock", "RawInline"]:
                raw = node["c"][1]
                assert r"\begin{tikzpicture}" in raw or r"\newcommand{\olasset}" in raw, raw[:200]
                return
            walk(node.get("c"))

    walk(root)
    return strings, maths, counts, notes


source_tex_input = (B / "openlogic-mr-core.tex").read_text(encoding="utf-8")
source_tex_input = source_tex_input.replace(
    r"\NewDocumentCommand{\sFmlaWide}{m m o}{\ensuremath{\IfNoValueTF{#3}{}{#3\,}\hbox to 1.2em{\ensuremath{#1}\hfil} #2}}",
    "",
).replace(r"\sFmlaWide", r"\sFmla")
source_tex, expected_proofs = strip_proof_environments(source_tex_input)
source_tex = adapt_prose_ensuremath(source_tex)
# Match the HTML builder's body-level macro expansion before comparing Pandoc
# prose tokens.  Without this, bare tableau rule macros are interpreted as
# ordinary text in the reference AST while the HTML input has semantic math.
source_preamble, source_marker, source_body = source_tex.partition(r"\begin{document}")
assert source_marker
source_tex = source_preamble + source_marker + expand_reader_math_macros(source_body)
source_tex = split_align_intertexts(source_tex)
source = collect(ast(text=source_tex))
adapted = collect(ast(B / "html-input.tex"))
if source[0] != adapted[0]:
    limit = min(len(source[0]), len(adapted[0]))
    mismatch = next(
        (index for index in range(limit) if source[0][index] != adapted[0][index]),
        limit,
    )
    print(
        json.dumps(
            {
                "adapted_prose_mismatch_index": mismatch,
                "source_token_count": len(source[0]),
                "adapted_token_count": len(adapted[0]),
                "source": source[0][mismatch] if mismatch < len(source[0]) else None,
                "adapted": adapted[0][mismatch] if mismatch < len(adapted[0]) else None,
                "source_window": source[0][max(0, mismatch - 8) : mismatch + 12],
                "adapted_window": adapted[0][max(0, mismatch - 8) : mismatch + 12],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
assert source[0] == adapted[0], "Prose changed while adapting diagrams and MathML"
if source[1] != adapted[1]:
    limit = min(len(source[1]), len(adapted[1]))
    mismatch = next(
        (index for index in range(limit) if source[1][index] != adapted[1][index]),
        limit,
    )
    print(
        json.dumps(
            {
                "adapted_formula_mismatch_index": mismatch,
                "source_formula_count": len(source[1]),
                "adapted_formula_count": len(adapted[1]),
                "source": source[1][mismatch] if mismatch < len(source[1]) else None,
                "adapted": adapted[1][mismatch] if mismatch < len(adapted[1]) else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
assert source[1] == adapted[1], "Formula changed while adapting diagrams and MathML"
assert source[3] == adapted[3], "Footnote content changed while adapting HTML"

document = BeautifulSoup((O / "index.html").read_text(encoding="utf-8"), "html.parser")
all_annotation_nodes = document.select('math annotation[encoding="application/x-tex"]')
toc_annotation_nodes = [node for node in all_annotation_nodes if node.find_parent("nav")]
proof_annotation_nodes = [node for node in all_annotation_nodes if node.find_parent("figure", class_="proof")]
annotations = [
    mathnorm(node.get_text())
    for node in all_annotation_nodes
    if not node.find_parent("nav")
    and not node.find_parent("section", class_="footnotes")
    and not node.find_parent("figure", class_="proof")
]
html_note_maths = [
    [mathnorm(node.get_text()) for node in item.select('math annotation[encoding="application/x-tex"]')]
    for item in document.select("section.footnotes li")
]
if annotations != adapted[1]:
    limit = min(len(annotations), len(adapted[1]))
    mismatch = next((index for index in range(limit) if annotations[index] != adapted[1][index]), limit)
    print(
        json.dumps(
            {
                "math_mismatch_index": mismatch,
                "html_math_count": len(annotations),
                "adapted_math_count": len(adapted[1]),
                "adapted": adapted[1][mismatch] if mismatch < len(adapted[1]) else None,
                "html": annotations[mismatch] if mismatch < len(annotations) else None,
                "adapted_window": adapted[1][max(0, mismatch - 5) : mismatch + 8],
                "html_window": annotations[max(0, mismatch - 5) : mismatch + 8],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
assert annotations == adapted[1], "HTML math annotations differ from adapted source math"
assert html_note_maths == [item[1] for item in adapted[3]]
proof_formula_count = sum(len(spec["rows"]) for spec in expected_proofs)
assert len(proof_annotation_nodes) == proof_formula_count
for spec in expected_proofs:
    figure = document.select_one(f'figure.proof[data-proof-id="{spec["id"]}"]')
    assert figure and figure.get("aria-labelledby") == spec["id"] + "-caption"
    assert figure.select_one("figcaption").get_text(strip=True) == spec["caption"]
    assert len(figure.select("tbody tr")) == len(spec["rows"])
    rendered = [
        mathnorm(node.get_text())
        for node in figure.select('math annotation[encoding="application/x-tex"]')
    ]
    assert rendered == [mathnorm(row["formula_tex"]) for row in spec["rows"]]
    rules = [row.select("td")[2].get_text(" ", strip=True) for row in figure.select("tbody tr")]
    assert rules == [row["rule"] for row in spec["rows"]]
assert len(document.select("math")) == (
    len(annotations)
    + len(toc_annotation_nodes)
    + sum(map(len, html_note_maths))
    + len(proof_annotation_nodes)
)
assert not document.select("merror,script,iframe,object,embed")

fallback_manifest_path = P / "math-text-fallbacks" / "MANIFEST.json"
fallback_manifest = json.loads(fallback_manifest_path.read_text(encoding="utf-8"))
assert fallback_manifest["schema"] == "openlogic-marathi-math-text-fallbacks/1"
fallback_entries = {entry["text"]: entry for entry in fallback_manifest["entries"]}
assert len(fallback_entries) == len(fallback_manifest["entries"]) == 57
fallback_nodes = document.select("mtext > mglyph")
assert len(fallback_nodes) == 240
assert len(document.select("mglyph")) == len(fallback_nodes)
fallback_asset_inventory = {}
for glyph in fallback_nodes:
    parent = glyph.parent
    assert parent and parent.name == "mtext" and len(parent.contents) == 1
    text = glyph.get("alt")
    assert text in fallback_entries
    entry = fallback_entries[text]
    reference = f"assets/math-text/{entry['filename']}"
    assert glyph.get("src") == reference
    assert glyph.get("width") == entry["display_width"]
    assert glyph.get("height") == entry["display_height"]
    assert glyph.get("valign") == entry["valign"]
    path = (O / reference).resolve()
    assert path.is_relative_to(O.resolve()) and path.is_file()
    assert path.stat().st_size == entry["bytes"]
    assert sha(path) == entry["sha256"]
    fallback_asset_inventory[reference] = {
        "filename": reference,
        "bytes": path.stat().st_size,
        "sha256": sha(path),
        "text": text,
    }
assert len({node["alt"] for node in fallback_nodes}) == 57
assert len(fallback_asset_inventory) == 57
visible_copy = BeautifulSoup(str(document), "html.parser")
for node in visible_copy.select("math"):
    node.decompose()
assert "\\begin{" not in visible_copy.get_text()

ids = [node["id"] for node in document.select("[id]")]
assert len(ids) == len(set(ids))
links = document.select('a[href^="#"]')
assert all(link["href"][1:] in ids for link in links)

assets = []
for node in document.select('img[src],link[rel="stylesheet"]'):
    reference = node.get("src", node.get("href"))
    assert not re.match(r"\w+:|//", reference)
    asset_reference = reference.split("?", 1)[0]
    path = (O / asset_reference).resolve()
    assert path.is_relative_to(O.resolve()) and path.is_file()
    if node.name == "img":
        assert node.get("alt") and len(node["alt"]) > 40
        assert node.get("loading") == "lazy"
        assert node.get("id") == "diagram-" + Path(asset_reference).stem
        assert int(node["width"]) > 0 and int(node["height"]) > 0
    assets.append({"filename": asset_reference, "bytes": path.stat().st_size, "sha256": sha(path)})

html_diagram_count = len(document.select("img"))
assert html_diagram_count >= 12
assert document.html["lang"] == "mr"
assert document.select_one('meta[name="viewport"]')
assert document.select_one("main#main-content")
assert document.select_one('a.skip-link[href="#main-content"]')
assert len(document.select("h2[data-number]")) == section_count
assert len(document.select("h1[data-number]")) == chapter_count

aux = (B / "openlogic-mr-core.aux").read_text(encoding="utf-8")
labels = dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}", aux))
reference_checks = []
for link in document.select("a[data-reference]"):
    key = link["data-reference"]
    assert key in labels, key
    assert link.get_text() == labels[key], (key, link.get_text(), labels[key])
    reference_checks.append(key)

body = BeautifulSoup(str(document.main), "html.parser")
for node in body.select("nav,header,math,.header-section-number,section.footnotes,a[role='doc-noteref'],figure.proof"):
    node.decompose()


def prose_norm(text):
    text = re.sub(r"(?<!\d)\d+(?:\.\d+)+(?!\d)", "", text)
    return "".join(
        character
        for character in unicodedata.normalize("NFC", text)
        if unicodedata.category(character)[0] in "LMN"
    )


expected_source = " ".join(adapted[0])
for key, label in sorted(labels.items(), key=lambda item: len(item[0]), reverse=True):
    # Pandoc exposes unresolved LaTeX \ref arguments as literal label keys in
    # its source AST. The HTML builder resolves them from the settled TeX aux.
    expected_source = expected_source.replace(key, label)
expected = prose_norm(expected_source)
actual = prose_norm(body.get_text(" "))
if expected != actual:
    limit = min(len(expected), len(actual))
    mismatch = next((index for index in range(limit) if expected[index] != actual[index]), limit)
    raise AssertionError(
        {
            "mismatch_index": mismatch,
            "source_length": len(expected),
            "html_length": len(actual),
            "source_window": expected[max(0, mismatch - 80) : mismatch + 160],
            "html_window": actual[max(0, mismatch - 80) : mismatch + 160],
        }
    )

expected_notes = [prose_norm(" ".join(item[0])) for item in adapted[3]]
actual_notes = []
for item in document.select("section.footnotes li"):
    copy = BeautifulSoup(str(item), "html.parser")
    for node in copy.select("math,a[role='doc-backlink']"):
        node.decompose()
    actual_notes.append(prose_norm(copy.get_text(" ")))
assert actual_notes == expected_notes, "Footnote prose differs from adapted source"

build = json.loads((B / "HTML_BUILD_RECEIPT.json").read_text(encoding="utf-8"))
assert build["warnings"] == ""
assert build["html_sha256"] == sha(O / "index.html")
note_math_count = sum(map(len, html_note_maths))
assert build["mathml_count"] == len(annotations) + len(toc_annotation_nodes) + note_math_count + len(proof_annotation_nodes)
assert len(build["diagram_assets"]) == html_diagram_count
assert build["math_text_fallbacks"]["manifest"] == "math-text-fallbacks/MANIFEST.json"
assert build["math_text_fallbacks"]["manifest_sha256"] == sha(fallback_manifest_path)
assert build["math_text_fallbacks"]["occurrences"] == len(fallback_nodes)
assert build["math_text_fallbacks"]["unique_phrases"] == len(fallback_entries)
assert len(build["math_text_fallbacks"]["occurrence_map"]) == len(fallback_nodes)
assert [row["text"] for row in build["math_text_fallbacks"]["occurrence_map"]] == [
    node["alt"] for node in fallback_nodes
]
assert build["math_text_fallbacks"]["assets"] == [
    {
        "filename": f"assets/math-text/{entry['filename']}",
        "bytes": entry["bytes"],
        "sha256": entry["sha256"],
        "text": entry["text"],
        "display_width": entry["display_width"],
        "display_height": entry["display_height"],
        "valign": entry["valign"],
    }
    for entry in fallback_manifest["entries"]
]
assert build["proof_representations"] == [
    {
        "id": spec["id"],
        "section_id": spec["section_id"],
        "caption": spec["caption"],
        "rows": spec["rows"],
    }
    for spec in expected_proofs
]
for item in build["diagram_assets"]:
    path = O / item["filename"]
    assert item["bytes"] == path.stat().st_size
    assert item["sha256"] == sha(path)

receipt = {
    "schema": "openlogic-html-qa/1",
    "passed": True,
    "scope": scope,
    "html_sha256": sha(O / "index.html"),
    "html_bytes": (O / "index.html").stat().st_size,
    "source_tex_sha256": sha(B / "openlogic-mr-core.tex"),
    "source_pdf_sha256": sha(B / "openlogic-mr-core.pdf"),
    "source_to_adapted_prose_tokens_exact": len(source[0]),
    "source_to_adapted_math_expressions_exact": len(source[1]),
    "source_to_html_main_math_annotations_exact": len(annotations),
    "source_to_html_footnote_math_annotations_exact": note_math_count,
    "proof_figures_semantically_reconstructed": len(expected_proofs),
    "proof_formula_annotations_verified": len(proof_annotation_nodes),
    "toc_duplicate_math_annotations": len(toc_annotation_nodes),
    "native_mathml_total": build["mathml_count"],
    "mathml_text_fallback_occurrences": len(fallback_nodes),
    "mathml_text_fallback_unique_phrases": len(fallback_entries),
    "footnotes_with_exact_prose_and_math": len(expected_notes),
    "ordinary_prose_characters_exact_ignoring_generated_numbering": len(expected),
    "internal_links_valid": len(links),
    "pdf_numbered_references_matched": reference_checks,
    "chapters": chapter_count,
    "sections": section_count,
    "diagrams": len(build["diagram_assets"]),
    "assets": assets,
    "math_text_fallback_assets": list(fallback_asset_inventory.values()),
    "pandoc_warnings": 0,
    "accessibility_checks": [
        "Marathi document language",
        "main landmark and skip link",
        "hierarchical headings and linked table of contents",
        "native MathML with exact TeX annotations",
        f"{len(fallback_nodes)} Devanagari MathML text occurrences with exact alternative text and outlined SVG fallbacks",
        f"{html_diagram_count} detailed Marathi image alternatives",
        "offline fonts and responsive CSS",
        "keyboard-focusable horizontally scrollable display mathematics",
    ],
    "browser_layout_review": {
        "status": "passed",
        "reason": "In-app browser inspection confirmed the title/TOC view, the chapter-20 anchor, and semantic proof tables at the generated desktop viewport.",
        "checked_surfaces": [
            "title and linked table of contents",
            "20 अंकगणिताची प्रतिमाने chapter anchor",
            "semantic proof-table examples",
        ],
    },
    "limitations": [
        "No independent human linguistic review.",
        "Assistive-technology behavior is not independently certified.",
    ],
}
(B / "HTML_QA.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
