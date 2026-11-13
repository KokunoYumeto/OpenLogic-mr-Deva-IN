"""Project numbering and cross-references from the accepted complete PDF."""
import json
import re
from hashlib import sha256

import fitz
from bs4 import NavigableString

from core_html_proofs import _balanced


NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)*")
STATEMENTS = {"defn", "ex", "prop", "thm", "cor", "lem", "rem", "conv", "axiom"}
HEADING_KINDS = {"h1": "part", "h2": "chapter", "h3": "section", "h4": "subsection"}


def load_pdf_numbering(build, source):
    pdf_path = build / "openlogic-mr-full.pdf"
    receipt = json.loads((build / "TEX_SUCCESS_RECEIPT.json").read_text(encoding="utf-8-sig"))
    if (receipt.get("result") != "built-log-clean"
            or receipt.get("pdf", {}).get("sha256") != sha256(pdf_path.read_bytes()).hexdigest()
            or receipt.get("texInputSha256") != sha256(source.read_bytes()).hexdigest()):
        raise ValueError("PDF numbering requires the accepted PDF and its exact TeX")
    aux_path = build / "openlogic-mr-full.aux"
    aux = aux_path.read_text(encoding="utf-8")
    with fitz.open(pdf_path) as pdf:
        destinations = pdf.resolve_names()
        outline = [row[3].get("nameddest") for row in pdf.get_toc(simple=False)]
    ordered = {}
    for kind in {*HEADING_KINDS.values(), "defn", "prob", "equation", "figure", "table"}:
        matching = [name for name in destinations if name.split(".")[0] == kind]
        if kind in HEADING_KINDS.values():
            by_kind = [name for name in outline if name and name.split(".")[0] == kind]
            if set(by_kind) != set(matching):
                raise ValueError(f"PDF outline differs from named {kind} destinations")
            ordered[kind] = by_kind
        elif kind in {"figure", "table", "equation"}:
            ordered[kind] = sorted(matching, key=lambda name: tuple(map(int, name.split(".")[1:])))
        else:
            ordered[kind] = sorted(matching, key=lambda name: (
                destinations[name]["page"], -destinations[name]["to"][1], destinations[name]["to"][0],
            ))
    labels = {}
    for match in re.finditer(r"(?m)^\\newlabel\{([^{}]+)\}\{(?=\{)", aux):
        key = match[1]
        if key.endswith("@cref"):
            continue
        fields, _ = _balanced(aux, match.end() - 1)
        number, cursor = _balanced(fields, 0)
        for _ in range(2):
            _, cursor = _balanced(fields, cursor)
        destination, _ = _balanced(fields, cursor)
        if key in labels or destination not in destinations:
            raise ValueError(f"Duplicate or non-PDF auxiliary label: {key} ({destination})")
        kind = destination.split(".")[0]
        if kind in ordered and number != destination.split(".", 1)[1]:
            raise ValueError(f"Auxiliary and PDF counter values differ for {key}")
        labels[key] = (number.removeprefix("{").removesuffix("}"), destination)
    return ordered, labels


def project_headings(soup, pdf_numbers, labels):
    toc_links = {link["href"][1:]: link for link in soup.select('nav#TOC a[href^="#"]')}
    rows = []
    for tag, kind in HEADING_KINDS.items():
        headings = soup.select(f"main {tag}:not(.title):not(.unnumbered):not(#toc-title)")
        for heading, destination in zip(headings, pdf_numbers[kind], strict=True):
            identifier = heading["id"]
            number = destination.split(".", 1)[1]
            if identifier in labels and labels[identifier] != (number, destination):
                raise ValueError(f"PDF heading differs at {identifier}")
            toc = toc_links.get(identifier)
            for node in (heading, toc):
                if node is None:
                    continue
                prefix = soup.new_tag("span", attrs={"class": "pdf-heading-number"})
                prefix.string = number
                node.insert(0, prefix)
                node.insert(1, NavigableString(" "))
            heading["data-pdf-destination"] = destination
            rows.append({"id": identifier, "number": number, "destination": destination})
    for kind, classes in (("defn", STATEMENTS), ("prob", {"prob"})):
        blocks = soup.select(",".join(f"main div.{name}" for name in sorted(classes)))
        for block, destination in zip(blocks, pdf_numbers[kind], strict=True):
            key = block.get("id")
            number = destination.split(".", 1)[1]
            if key in labels and labels[key] != (number, destination):
                raise ValueError(f"PDF statement differs at {key}")
            heading = block.find("strong")
            if not heading or not heading.string or len(NUMBER.findall(str(heading.string))) != 1:
                raise ValueError(f"Could not find unique statement number for {key} ({destination})")
            heading.string.replace_with(NUMBER.sub(number, str(heading.string), count=1))
            block["data-pdf-destination"] = destination
            rows.append({"id": key, "number": number, "destination": destination})
    return rows


def project_prose_references(soup, labels, targets):
    rows = []
    for link in soup.select('a[data-reference][href^="#"]'):
        keys = link["data-reference"].split(",")
        if link.get("data-reference-type") == "ref+label" and len(keys) > 1:
            for index, key in enumerate(keys):
                number, destination = labels[key]
                if key not in targets:
                    raise ValueError(f"Missing digital target for {key}")
                anchor = soup.new_tag("a", href="#" + key, attrs={
                    "data-reference": key, "data-reference-type": "ref",
                    "data-pdf-reference": destination,
                })
                kind = destination.split(".")[0]
                if kind == "table":
                    anchor.string = "तक्ता " + number
                else:
                    strong = targets[key].find("strong")
                    if not strong or number not in strong.get_text(strip=True):
                        raise ValueError(f"Unexpected combined reference target {key}")
                    anchor.string = strong.get_text(" ", strip=True)
                if index:
                    link.insert_before(NavigableString(" आणि "))
                link.insert_before(anchor)
                rows.append({"key": key, "number": number, "destination": destination, "text": anchor.string})
            link.decompose()
            continue
        key = link["href"][1:]
        if keys != [key] or key not in targets:
            raise ValueError(f"Missing or mismatched digital target for {key}: {keys}")
        number, destination = labels[key]
        text = f"({number})" if link.get("data-reference-type") == "eqref" else number
        link.string = text
        link["data-pdf-reference"] = destination
        rows.append({"key": key, "number": number, "destination": destination, "text": text})
    return rows


def project_list_labels(soup, labels, targets):
    rows = []
    for key, (number, destination) in labels.items():
        if not destination.startswith("Item."):
            continue
        target = targets[key]
        item = target if target.name == "li" else target.find_parent("li")
        if item is None or item.parent.name != "ol":
            raise ValueError(f"Missing ordered list item for {key}")
        start = int(item.parent.get("start", 1))
        ordinal = int(item.get("value", start + len(item.find_previous_siblings("li"))))
        if str(ordinal) != number:
            if not re.fullmatch(r"[0-9]+[a-z]", number):
                raise ValueError(f"List number differs at {key}: {ordinal} != {number}")
            item["class"] = [*item.get("class", []), "pdf-list-item"]
            marker = soup.new_tag("span", attrs={"class": "pdf-item-number"})
            marker.string = number + ". "
            target.insert_after(marker)
        item["data-pdf-destination"] = destination
        rows.append({"id": key, "number": number, "destination": destination})
    return rows
