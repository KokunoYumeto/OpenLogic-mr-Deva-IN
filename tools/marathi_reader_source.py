"""Project Marathi locale annotations into the standalone reader's source syntax."""

import re
from functools import lru_cache
from pathlib import Path

from complete_reader_layout import project_complete_reader_layout
from complete_reader_context_layout import project_complete_context_layout
from marathi_layout_projection import project_complete_layout


LOCALE_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "courses/sets-logic-computation/locale/open-logic-config.sty"
)
OBLIQUE_DECLARATION = re.compile(
    r"(?m)^[ \t]*\\mrsettokenoblique\{([^{}]+)\}\{([^{}]+)\}\{([^{}]+)\}"
    r"[ \t]*(?:%[^\n]*)?$"
)
ANNOTATION = re.compile(
    r"(?P<comment>(?<!\\)(?:\\\\)*%[^\n]*)"
    r"|(?<!\\)(?P<id>\\ol(?:file|chapter|part)id)\s*\[mr\]\s*(?=\{)"
    r"|(?<!\\)\\(?:use|print)token\s*"
    r"\{\s*(?P<form>oblique(?:\s+plural)?)\s*\}\s*\{(?P<token>[^{}]+)\}"
)


@lru_cache(maxsize=1)
def oblique_forms():
    """Read the same Marathi stem pairs as the course's LaTeX reader."""
    forms = {}
    for token, singular, plural in OBLIQUE_DECLARATION.findall(
        LOCALE_CONFIG.read_text(encoding="utf-8")
    ):
        if token in forms:
            raise ValueError(f"Duplicate Marathi oblique token {token!r} in {LOCALE_CONFIG}")
        forms[token] = (singular, plural)
    if not forms:
        raise ValueError(f"No Marathi oblique tokens in {LOCALE_CONFIG}")
    return forms


def project_locale(text):
    """Resolve explicit Marathi forms and keep the legacy three-part file IDs."""

    def replace(match):
        if match["comment"] is not None:
            return match[0]
        if match["id"] is not None:
            return match["id"]
        token = " ".join(match["token"].split())
        try:
            forms = oblique_forms()[token]
        except KeyError as error:
            raise ValueError(f"Unknown Marathi oblique token {token!r}") from error
        plural = " ".join(match["form"].split()) == "oblique plural"
        return forms[plural]

    return ANNOTATION.sub(replace, project_complete_context_layout(project_complete_layout(project_complete_reader_layout(text))))


def read_source(path):
    """Read projected text while leaving the source bytes available for receipts."""
    return project_locale(path.read_text(encoding="utf-8"))
