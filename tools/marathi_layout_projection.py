"""Expand the shared Marathi source's complete-reader layout choices."""

import re


MARKERS = re.compile(
    r"(?m)^(?P<standalone>\\olmrdefinitionlayout\{\}|"
    r"\\olmrsourcecitation\{avigad-logic-and-computation\})\n"
    r"|(?P<comment>(?<!\\)(?:\\\\)*%[^\n]*)"
    r"|(?<!\\)\\(?P<layout>olmrdisplaybreak|olmrproofreasonbreak|olmrimplicationdisplay)(?![A-Za-z])"
)


def implication_arguments(text, offset):
    values = []
    for _ in range(4):
        while text[offset:offset + 1] in (" ", "\t", "\n", "\r"):
            offset += 1
        if text[offset:offset + 1] != "{":
            raise ValueError("Missing argument to Marathi implication layout")
        depth = 1
        start = offset = offset + 1
        while depth and offset < len(text):
            if text[offset] == "\\":
                offset += 2
                continue
            depth += (text[offset] == "{") - (text[offset] == "}")
            offset += 1
        if depth:
            raise ValueError("Unclosed argument to Marathi implication layout")
        values.append(text[start:offset - 1])
    return values, offset


def project_complete_layout(text):
    """Retain the inherited editorial and source notation in the full reader."""
    result = []
    offset = 0
    while match := MARKERS.search(text, offset):
        result.append(text[offset:match.start()])
        offset = match.end()
        if match["comment"] is not None:
            result.append(match[0])
        elif match["standalone"] is None:
            if match["layout"] == "olmrimplicationdisplay":
                (prefix, antecedent, left, right), offset = implication_arguments(text, offset)
                quantifiers = re.fullmatch(r"\\lforall\[([^\[\]]+)\]\\lforall\[([^\[\]]+)\]", prefix)
                if quantifiers is None:
                    raise ValueError(f"Unexpected Marathi implication quantifiers: {prefix}")
                a, x = quantifiers.groups()
                result.append(rf"\lforall[{a}][\lforall {x}][({antecedent} \lif" + "\n"
                              + rf"({left} \lor {right})]]")
            else:
                if text[offset:offset + 2] != "{}":
                    raise ValueError(f"Missing empty argument to {match['layout']}")
                offset += 2
                if match["layout"] == "olmrdisplaybreak":
                    result.append(" ")
                else:
                    result.append("\n    ")
    result.append(text[offset:])
    return "".join(result)
