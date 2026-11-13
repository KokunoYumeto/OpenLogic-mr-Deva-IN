"""Project the accepted PDF figure and table counters into the digital reader."""

import re


TABLE_CAPTIONS_LOST_BY_PANDOC = (
    "nml:tab:rul:tab:prop-rules",
    "int:tab:rul:tab:prop-rules",
    "int:tab:rul:tab:rules-lif-lnot",
    "pt:nor:red:tab:reduction-conversions",
    "pt:seq:int:tab:G3c",
    "pt:seq:supp:tab:mG3i",
)
UNLABELLED_FIGURES = {
    "figure.22.1": "अंतर्गत आंशिक समरूपण असलेली संरचना",
    "figure.42.1": "Ł₃ मधील निष्पत्तीचे उदाहरण",
}
CAPTION_MARKER = "table-caption-for-"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _caption_argument(tex, start):
    depth = 1
    for pos in range(start + 1, len(tex)):
        if tex[pos - 1] == "\\":
            continue
        if tex[pos] == "{":
            depth += 1
        elif tex[pos] == "}":
            depth -= 1
            if depth == 0:
                return tex[start + 1:pos], pos + 1
    raise ValueError(f"Unclosed table caption at source character {start}")


def preserve_table_captions(tex):
    """Carry captions that Pandoc drops through the normal TeX-to-MathML conversion."""
    insertions = {}
    for key in TABLE_CAPTIONS_LOST_BY_PANDOC:
        label = r"\label{" + key + "}"
        _require(tex.count(label) == 1, f"Expected exactly one source label for table {key}")
        label_at = tex.index(label)
        begin = tex.rfind(r"\begin{table}", 0, label_at)
        _require(begin >= 0 and tex.find(r"\end{table}", begin, label_at) < 0,
                 f"Missing source table environment for {key}")
        caption = tex.rfind(r"\caption{", begin, label_at)
        _require(caption >= 0, f"Missing source caption for table {key}")
        content, end = _caption_argument(tex, caption + len(r"\caption"))
        _require(not tex[end:label_at].strip(), f"Unexpected source between caption and label for {key}")
        # These system names are text-mode in the source caption. Pandoc's
        # MathML conversion needs the math-mode form after macro expansion.
        content = re.sub(r"\\Log\{(?:N1i|G3c|mG3i)\}", lambda match: "$" + match[0] + "$", content)
        marker = r"\hypertarget{" + CAPTION_MARKER + key + "}{" + content + "}\n\n"
        insertions[begin] = marker
    for begin, marker in sorted(insertions.items(), reverse=True):
        tex = tex[:begin] + marker + tex[begin:]
    return tex


def _prefix_caption(soup, caption, kind, number):
    _require(caption is not None and caption.select_one(".float-number") is None,
             f"Missing or already numbered caption for {kind} {number}")
    prefix = soup.new_tag("span", attrs={"class": "float-number"})
    prefix.string = ("आकृती" if kind == "figure" else "तक्ता") + f" {number}."
    caption.insert(0, " ")
    caption.insert(0, prefix)


def _figure_caption(soup, owner, destination):
    if owner is None:
        start = UNLABELLED_FIGURES.get(destination)
        _require(start, f"No binding for unlabelled native figure {destination}")
        matches = [
            caption for caption in soup.select("figure > figcaption")
            if " ".join(caption.get_text().split()).startswith(start)
        ]
        _require(len(matches) == 1, f"Expected one caption for unlabelled native figure {destination}")
        owner = matches[0].parent
        if not owner.get("id"):
            owner["id"] = destination.replace(".", "-")
    _require(owner.name == "figure", f"Expected figure element at {destination}")
    return owner, owner.find("figcaption", recursive=False)


def _table_caption(markers, owner, key):
    _require(key is not None, "Unlabelled native table")
    if key not in TABLE_CAPTIONS_LOST_BY_PANDOC:
        _require(owner is not None, f"Missing native table {key}")
        return owner, owner.select_one(":scope > table > caption")
    marker = markers.get(CAPTION_MARKER + key)
    _require(marker is not None, f"Missing converted source caption for table {key}")
    blocks = marker.find_all(recursive=False)
    _require(len(blocks) == 1 and blocks[0].name == "p" and blocks[0].get_text(strip=True),
             f"Unexpected caption markup for table {key}")
    caption = blocks[0]
    if owner is None:
        marker["id"] = key
        owner = marker
    else:
        _require(not owner.find(recursive=False) and not owner.get_text(strip=True),
                 f"Expected an empty table anchor for {key}")
        owner.append(caption.extract())
        marker.decompose()
    caption["class"] = ["native-table-caption"]
    return owner, caption


def project_floats(soup, pdf_numbers, labels):
    """Number native captions and known duplicate table presentations in place."""
    bindings = {
        destination: (key, number)
        for key, (number, destination) in labels.items()
        if destination.startswith(("figure.", "table."))
    }
    rows = []
    base_captions = {}
    nodes = {node["id"]: node for node in soup.find_all(id=True)}
    for kind in ("figure", "table"):
        for destination in pdf_numbers[kind]:
            suffix = destination.split(".", 1)[1]
            key, number = bindings.get(destination, (None, suffix))
            _require(number == suffix, f"PDF destination and printed number differ at {destination}")
            owner = nodes.get(key)
            if kind == "figure":
                owner, caption = _figure_caption(soup, owner, destination)
            else:
                owner, caption = _table_caption(nodes, owner, key)
                _require(caption is not None, f"Missing native caption at {key}")
                base_captions[key] = (caption.decode_contents(), number)
            _prefix_caption(soup, caption, kind, number)
            rows.append({"id": owner["id"], "number": number, "destination": destination})
    _require(set(bindings).issubset(row["destination"] for row in rows),
             "A native figure or table label is absent from the accepted PDF destination list")

    for caption in soup.select("div[id] > table > caption"):
        alias = re.fullmatch(r"(.+)-alt\d+", caption.parent.parent["id"])
        if alias is None or alias[1] not in base_captions:
            continue
        original, number = base_captions[alias[1]]
        _require(caption.decode_contents() == original, f"Table alias caption differs at {alias[0]}")
        _prefix_caption(soup, caption, "table", number)
    return rows
