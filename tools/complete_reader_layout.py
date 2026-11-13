"""Return the plain LaTeX display for the complete reader."""

import re


EQUALITY_DISPLAY = re.compile(
    r"(?m)^\\ifdefined\\OLProvableEqualityDisplay\\else\n"
    r"  \\def\\OLProvableEqualityDisplay#1#2#3\{#1 \\eq\[#2\]\[#3\]\}[ \t]*%?\n"
    r"\\fi\n"
    r"\\OLProvableEqualityDisplay\{(?P<relation>[^\n]+)\}[ \t]*%?\n"
    r"  \{(?P<left>[^\n]+)\}[ \t]*%?\n"
    r"  \{(?P<right>[^\n]+)\}$"
)


def project_complete_reader_layout(source):
    """Use the default formula and leave existing source unchanged."""
    if r"\OLProvableEqualityDisplay" not in source:
        return source
    source, count = EQUALITY_DISPLAY.subn(
        lambda match: (
            match["relation"] + "\n"
            + r"\eq[" + match["left"] + "][" + match["right"] + "]"
        ),
        source,
    )
    if count != 1 or r"\OLProvableEqualityDisplay" in source:
        raise ValueError("Unrecognized provable equality display in complete-reader source")
    return source
