"""Read numbered and unnumbered headings from the assembled reader source."""
import re
from core_html_proofs import _balanced, _balanced_square


def heading_inventory(tex):
    body = tex.split(r"\begin{document}", 1)[1].rsplit(r"\end{document}", 1)[0]
    body = re.sub(r"(?<!\\)%[^\n]*", "", body)
    rows = []
    for match in re.finditer(r"(?<!\\)\\(part|chapter|section)(\*)?(?![A-Za-z])", body):
        position = match.end()
        while position < len(body) and body[position].isspace():
            position += 1
        if body[position:position + 1] == "[":
            _, position = _balanced_square(body, position)
            while position < len(body) and body[position].isspace():
                position += 1
        if body[position:position + 1] != "{":
            continue
        title, _ = _balanced(body, position)
        rows.append({"command": match[1], "unnumbered": bool(match[2]), "title_tex": title})
    return rows
