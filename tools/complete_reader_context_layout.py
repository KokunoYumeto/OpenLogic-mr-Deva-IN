"""Resolve the Marathi machine layout controls before complete-reader conversion."""

import re


CONDITION = r"\OLMarathiTMCondition"
ENTAILMENT = r"\OLMarathiVerificationEntailment"
DIAGRAM = (
    "  " + r"\ifdefined\SLCCombinedMachineLayout\SLCCombinedMachineLayout\fi"
)
CONDITION_DEFAULT = (
    r"\providecommand*{\OLMarathiTMCondition}[2]{\text{#1 #2}}"
)
ENTAILMENT_DEFAULT = (
    r"\providecommand*{\OLMarathiVerificationEntailment}[2]{\ensuremath{#1}#2}"
)
ARGUMENT_SPACE = re.compile(r"(?:\s+|%[^\n]*\n)*")


def take_argument(source, offset):
    offset = ARGUMENT_SPACE.match(source, offset).end()
    if source[offset:offset + 1] != "{":
        raise ValueError("Missing Marathi machine layout argument")
    start = offset + 1
    depth = 1
    offset = start
    while offset < len(source):
        token = source[offset]
        if token == "\\":
            offset += 2
            continue
        if token == "%":
            newline = source.find("\n", offset)
            if newline == -1:
                break
            offset = newline + 1
            continue
        depth += (token == "{") - (token == "}")
        if depth == 0:
            return source[start:offset], offset + 1
        offset += 1
    raise ValueError("Unclosed Marathi machine layout argument")


def remove_once(source, literal):
    pattern = r"(?m)^" + re.escape(literal) + r"\n{1,2}"
    source, count = re.subn(pattern, "", source)
    if count != 1:
        raise ValueError("Unrecognized Marathi machine layout declaration")
    return source


def project_complete_context_layout(source):
    """Expand native layout markers to ordinary math before PDF, HTML and EPUB."""
    if CONDITION in source:
        source = remove_once(source, CONDITION_DEFAULT)
        source = remove_once(source, DIAGRAM)
        for separator in (" ", "\n      "):
            start = source.index(CONDITION)
            first, end = take_argument(source, start + len(CONDITION))
            second, end = take_argument(source, end)
            source = source[:start] + r"\text{" + first + separator + second + "}" + source[end:]
    if ENTAILMENT in source:
        source = remove_once(source, ENTAILMENT_DEFAULT)
        start = source.index(ENTAILMENT)
        expression, end = take_argument(source, start + len(ENTAILMENT))
        punctuation, end = take_argument(source, end)
        if punctuation != "." or not expression.startswith(("%\n", "\n")):
            raise ValueError("Unrecognized Marathi verification entailment layout")
        inline = expression.removeprefix("%").strip()
        source = source[:start] + "$" + inline + "$" + punctuation + source[end:]
    if any(marker in source for marker in (CONDITION, ENTAILMENT, r"\SLCCombinedMachineLayout")):
        raise ValueError("Unexpected Marathi machine layout marker in complete-reader source")
    return source
