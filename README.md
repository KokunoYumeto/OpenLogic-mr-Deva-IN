# The Open Logic Text · मराठी (mr-Deva-IN)

This repository contains a complete Marathi translation of the 722 content TeX
units of [The Open Logic Text](https://github.com/OpenLogicProject/OpenLogic),
frozen at upstream revision
`9620cc73f9c8e0ad003c514a5d3748f29611c4c0`. The assembled reader has
79 chapters, including supplementary and alternative material, and 612
sections. It belongs to the
[OpenLogic translations lineage](https://github.com/KokunoYumeto/OpenLogic-translations).

The full translation and source-aligned ledger are complete locally. The
complete PDF and offline HTML reader are undergoing final build verification.
The latest **published** reader remains
[twenty-chapters-v0.9](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/twenty-chapters-v0.9),
which covers 194 units. It is also archived in the existing
[Marathi OpenLogic Zenodo lineage](https://doi.org/10.5281/zenodo.22307960).
These publication links will be updated when the complete reader passes its
release gates.

## Translation and review

The 722 translated units are aligned to 6,644 source and target segments. The
full ledger records source hashes, exact translated segments, canon passages
actually consulted, and terminology decisions. A separate detailed decision
and occurrence review currently covers 281 units and 14,221 occurrences; this
more intensive coverage is not claimed for the rest of the corpus. The
complete reader's assembly includes translated front matter, all main chapters,
formal proof material, and source units outside the main reading route without
duplicating chapters.

Codex produced the machine translation and performed source comparison,
terminology research, and mechanical checks. No independent human or
native-speaker linguistic review is claimed. Specialist choices remain open
to correction. The Open Logic Project created the original text and does not
endorse this independent adaptation.

The editable Marathi source is under [`mr/content/`](mr/content/), aligned by
path and OLP unit ID to the frozen original under [`upstream/`](upstream/).
The source manifest and review records are under [`provenance/`](provenance/).
Build and QA scripts are under [`tools/`](tools/). The complete release will
include a sanitized, versioned export of the full 722-unit ledger, distinct
from the historically narrower detailed-review bundle in this working tree.

## Rebuild the complete reader

With Python, XeLaTeX, Pandoc, and the dependencies used by the scripts
available, assemble the full TeX reader:

```sh
python tools/prepare_complete.py
python tools/qa_complete_reader.py
```

On Windows, compile only through the bounded shared TeX guard:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_guarded.ps1 -Target full -PrepareScript tools/prepare_complete.py
```

The compiled PDF is `build/full/openlogic-mr-full.pdf`. Once its build receipt
is clean, refresh the offline HTML and run its static and browser checks:

```sh
python tools/complete_html_diagrams.py
python tools/prepare_complete_html.py
python tools/qa_complete_html.py
python tools/qa_complete_html_browser.py
python tools/qa_complete_pdf.py
```

The HTML entry point is `build/full/html/index.html`. It uses native MathML,
semantic proof displays, Marathi diagram descriptions, and bundled fonts. It
has no network dependency. `tools/prepare_complete_provenance.py` verifies and
exports the full translation ledger from the durable production state; that
state is not part of a source-only checkout. Published release archives will
include the verified export.

## License and attribution

The original text and marked Marathi adaptation use
[Creative Commons Attribution 4.0](LICENSE.md). Inherited component notices
and the [SIL Open Font License](fonts/OFL.txt) remain with their components.
The upstream frozen source is preserved to make comparison and correction
possible.
