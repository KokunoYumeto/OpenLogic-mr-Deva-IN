"""Project the accepted PDF's automatic equation numbers into HTML TeX input."""

import re
from collections import Counter

from core_html_proofs import _balanced, _balanced_square


TOKEN = re.compile(r"\\(?P<command>[A-Za-z]+|[^\n])|(?P<brace>[{}])")
DOCUMENT_EVENT = re.compile(
    r"(?<!\\)\\chapter\s*\{|(?<!\\)\\begin\{(align|equation)\}"
)
COMMENT = re.compile(r"(?<!\\)%[^\n]*")
VERBATIM = re.compile(r"\\begin\{verbatim\}.*?\\end\{verbatim\}", re.S)
NUMBER = re.compile(r"\d+\.\d+")


def mask_text(match):
    return re.sub(r"[^\n]", " ", match[0])


def braced_argument(text, position):
    while position < len(text) and text[position].isspace():
        position += 1
    if position == len(text) or text[position] != "{":
        raise ValueError(f"Missing equation command argument at offset {position}")
    return _balanced(text, position)


def equation_rows(text, start, end, environment):
    """Read top-level math rows and their numbering controls without expanding TeX."""
    rows = []
    depth = 0
    nested = []
    row_start = cursor = start
    labels = []
    controls = []
    while match := TOKEN.search(text, cursor, end):
        cursor = match.end()
        command = match["command"]
        if match["brace"]:
            depth += 1 if match["brace"] == "{" else -1
            if depth < 0:
                raise ValueError(f"Unbalanced equation row at offset {match.start()}")
            continue
        if command in {"begin", "end"}:
            nested_name, cursor = braced_argument(text, cursor)
            if command == "begin":
                nested.append(nested_name)
            elif not nested or nested.pop() != nested_name:
                raise ValueError(f"Unbalanced equation environment {nested_name} at offset {match.start()}")
            continue
        if depth or nested:
            continue
        if command == "label":
            key, cursor = braced_argument(text, cursor)
            labels.append(key)
        elif command in {"notag", "nonumber", "tag"}:
            controls.append(command)
            if command == "tag":
                if text[cursor:cursor + 1] == "*":
                    cursor += 1
                _, cursor = braced_argument(text, cursor)
        elif environment == "align" and command in {"\\", "intertext", "shortintertext"}:
            rows.append((row_start, match.start(), labels, controls))
            if command in {"intertext", "shortintertext"}:
                _, cursor = braced_argument(text, cursor)
            else:
                if text[cursor:cursor + 1] == "*":
                    cursor += 1
                if text[cursor:cursor + 1] == "[":
                    _, cursor = _balanced_square(text, cursor)
            row_start, labels, controls = cursor, [], []
    if depth or nested:
        raise ValueError(f"Unclosed equation row at offset {row_start}")
    rows.append((row_start, end, labels, controls))
    return rows


def project_equation_source(body, pdf_numbers, labels):
    """Add visible numbers to exact source rows and validate them against the PDF.

    ``pdf_numbers`` lists accepted visible numeric tags. Custom tags already in
    the source are preserved. ``labels`` maps AUX keys to (number, destination).
    """
    expected = {number.removeprefix("equation.") for number in pdf_numbers}
    if not expected or any(NUMBER.fullmatch(number) is None for number in expected):
        raise ValueError("Expected the accepted PDF's visible chapter.equation numbers")

    masked = VERBATIM.sub(mask_text, COMMENT.sub(mask_text, body))
    offsets = []
    inventory = []
    chapter = cursor = 0
    counter = Counter()
    while event := DOCUMENT_EVENT.search(masked, cursor):
        cursor = event.end()
        environment = event[1]
        if environment is None:
            chapter += 1
            continue
        closing = r"\end{" + environment + "}"
        end = masked.index(closing, cursor)
        rows = equation_rows(masked, cursor, end, environment)
        cursor = end + len(closing)
        for start, stop, keys, controls in rows:
            content = masked[start:stop].rstrip()
            if not content.strip():
                continue
            if len(keys) > 1 or ("tag" in controls and len(controls) > 1):
                raise ValueError(f"Ambiguous equation row at offset {start}")
            key = keys[0] if keys else None
            if controls:
                if key and key in labels and labels[key][1].startswith("equation."):
                    raise ValueError(f"AUX assigns an automatic number to suppressed row {key}")
                continue
            counter[chapter] += 1
            number = f"{chapter}.{counter[chapter]}"
            destination = f"equation.{number}"
            if key and labels.get(key) != (number, destination):
                raise ValueError(f"Equation numbering disagrees with AUX at {key}: {number}")
            offsets.append((start + len(content), r"\qquad\text{(" + number + ")}"))
            inventory.append({"number": number, "destination": destination, "key": key})

    actual = {row["number"] for row in inventory}
    if actual != expected or len(actual) != len(inventory):
        raise ValueError(f"Equation numbering differs from PDF: missing {sorted(expected - actual)}, "
                         f"unexpected {sorted(actual - expected)}")
    projected_keys = {row["key"] for row in inventory if row["key"] is not None}
    expected_keys = {key for key, (number, destination) in labels.items()
                     if destination.startswith("equation.") and number in expected}
    if projected_keys != expected_keys:
        raise ValueError(f"AUX equation labels are unbound: {sorted(expected_keys - projected_keys)}")

    for position, tag in reversed(offsets):
        body = body[:position] + tag + body[position:]
    return body, inventory
