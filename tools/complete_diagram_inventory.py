"""Describe diagram identities directly from the current assembled reader."""
import hashlib
import re
from bisect import bisect_right

from core_html_proofs import _balanced


def current_inventory(tex):
    asset_pattern = re.compile(r"\\olasset(?:\[[^]]+\])?\{assets/diagrams/([^}]+)\.tikz\}")
    tikz_pattern = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.S)
    assets = list(asset_pattern.finditer(tex))
    drawings = list(tikz_pattern.finditer(tex))
    assert len(assets) == 9 and len(drawings) == 61
    starts = [m.start() for m in re.finditer(r"\\begin\{figure\}(?:\[[^]]+\])?", tex)]
    ends = [m.start() for m in re.finditer(r"\\end\{figure\}", tex)]
    result = []
    for kind, matches in (("source-asset", assets), ("inline-tikz", drawings)):
        for match in matches:
            number = len(result) + 1
            entry = {"number": number, "kind": kind,
                     "name": match.group(1) if kind == "source-asset" else f"tikz-{number:03d}",
                     "source_line": tex.count("\n", 0, match.start()) + 1}
            if kind == "inline-tikz":
                entry["source_sha256"] = hashlib.sha256(match.group().encode("utf-8")).hexdigest()
                entry["source"] = match.group()
            a = bisect_right(starts, match.start()) - 1
            b = bisect_right(ends, match.start()) - 1
            begin = starts[a] if a >= 0 else -1
            previous_end = ends[b] if b >= 0 else -1
            if begin > previous_end:
                end = tex.index(r"\end{figure}", match.end())
                figure = tex[begin:end]
                caption = re.search(r"\\caption(?:\[[^]]+\])?\{", figure)
                if caption:
                    entry["caption_tex"], _ = _balanced(figure, caption.end() - 1)
                entry["figure_labels"] = re.findall(r"\\label\{([^}]+)\}", figure)
            result.append(entry)
    assert len(result) == 70 and len({entry['name'] for entry in result}) == 70
    return result
