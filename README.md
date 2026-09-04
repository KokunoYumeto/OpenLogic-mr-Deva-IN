# OpenLogic · मराठी (mr-Deva-IN)

मुक्त तर्कशास्त्राची मराठी आवृत्ती. संपूर्ण 722 स्रोत-विभागांच्या अनुवादाचे काम सुरू आहे.

सध्याच्या प्रकाशनात **संच आणि संबंध ही दोन संपूर्ण प्रकरणे** आहेत:
OLP-0004–OLP-0019, एकूण 16 स्रोत-विभाग, 14 मुख्य विभाग, सर्व उदाहरणे,
आकृत्यांचे मथळे आणि सराव. उर्वरित **706 विभागांचा अनुवाद अद्याप पूर्ण झालेला नाही**.
हे संपूर्ण ग्रंथाचे प्रकाशन नाही.

This is an independent Marathi edition of *The Open Logic Text*. The finite
commission covers all 722 content TeX units at upstream revision
`9620cc73f9c8e0ad003c514a5d3748f29611c4c0`. The cumulative release covers 16/722
units (190 content segments). Source IDs and paths remain aligned to the frozen corpus.

Editable work on the main branch has progressed through OLP-0033: **30/722 units**
and 365 aligned content blocks. The Functions chapter is complete in source form;
the first six reader sections of Size of Sets are translated. These fourteen additional units are not yet represented as
a rendered or released cumulative reader.

- **Current release:** [संच आणि संबंध — PDF, offline HTML and sources](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/foundations-v0.2).
- **DOI mirror:** [10.5281/zenodo.22307961](https://doi.org/10.5281/zenodo.22307961); [edition concept DOI](https://doi.org/10.5281/zenodo.22307960) for future versions.
- **PDF:** [22-page cumulative reader](releases/foundations-v0.2/openlogic-mr-foundations.pdf).
- **Offline HTML:** download and extract `openlogic-mr-foundations-html.zip`, then open `index.html`.
- **Editable Marathi:** [sets](mr/content/sets-functions-relations/sets/), [relations](mr/content/sets-functions-relations/relations/), [functions](mr/content/sets-functions-relations/functions/) and the [in-progress Size of Sets chapter](mr/content/sets-functions-relations/size-of-sets/).
- **Terminology and expert review:** [human-readable ledger](provenance/EXPERT_REVIEW_LOG.md) and [machine-readable decisions](provenance/EXPERT_REVIEW_DECISIONS.jsonl). It records provisional choices and precise questions without making review a completion gate.
- **Pristine English:** `upstream/`; this is source evidence, not translated coverage.
- **Current evidence:** `provenance/foundations-v0.2/`; root-level provenance remains the historical first release snapshot.
- **Earlier release:** [sets-v0.1](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/sets-v0.1), preserved unchanged.
- **International hub:** [OpenLogic translations](https://github.com/KokunoYumeto/OpenLogic-translations).
- **Original project and contributors:** [Open Logic Project](https://openlogicproject.org/people/),
  [source repository](https://github.com/OpenLogicProject/OpenLogic).

## Translation and evidence

Codex produced the machine translation and performed same-agent bilingual review.
No independent human or native-speaker review is claimed. The terminology uses
actual Marathi textbook pages and university philosophy usage, with explicitly
provisional extensions where evidence is sparse. Source mathematics takes
precedence over conventions in language witnesses: in particular, OpenLogic's
natural numbers include zero.

The two published chapters have 190 aligned content segments with consultation
records. Current editable source has 365 such records across 30 units.
Deterministic checks compare formulas, token identities, macro inventories,
labels, citations, links and source file references.
Visual, structural and semantic checks are documented in
`provenance/foundations-v0.2/QA-FOUNDATIONS-v0.2.json` and its review records.
Such checks do not establish the absence
of every possible translation error.
Two guarded builds on the same host produced identical PDF bytes with fixed
`SOURCE_DATE_EPOCH`; cross-platform byte identity has not been tested.

The offline HTML includes 846 MathML expressions with original TeX annotations,
six diagrams with Marathi alternatives, local fonts, a linked contents list and
keyboard-focusable formula regions. Exact conversion checks preserve prose and
formula content; internal references match PDF numbering. Browser layout and
assistive-technology behavior remain unverified because the available browser's
URL security policy denied local-file access. Static checks are not represented
as a browser test. Three inherited source notation issues in the published reader
are explained in a separate editorial section. The current expert-review ledger
also records five Functions corrections and five Size of Sets observations;
frozen English bytes remain unchanged.

Canon originals are local research evidence. They are **not redistributed here**.
Some government-site originals could not be downloaded; the index distinguishes
verified preserved PDF bytes from short observations and does not invent source
hashes. A dictionary label alone is not treated as complete semantic evidence.

## Rebuild the cumulative reader

Requirements: Python with `fonttools`, `PyMuPDF` and `beautifulsoup4`, Pandoc,
a current XeLaTeX installation and its standard packages, and PowerShell on Windows.
The licensed font files are included.

```powershell
python tools/prepare_foundations.py
./tools/build_guarded.ps1 -Target foundations
python tools/prepare_html.py
python tools/qa_html.py
```

The in-progress four-chapter reader can be prepared and built through OLP-0033 with:

```powershell
python tools/prepare_core.py
./tools/build_guarded.ps1 -Target core
```

The guarded builder reserves `Global\InterlanguageTeXSlotV1` with one bounded
timeout, captures its TeX process tree in a Windows job, holds the mutex through
both passes and log checks, and releases it in `finally`. A busy slot launches
no TeX. `SOURCE_DATE_EPOCH` is set for the child build and restored afterward.
The adapter includes all novice, mathematics and computing passages. Two original
cross-chapter conditionals take their original false branch in this chapter-only
reader; the complete translated TeX retains both original branches. The HTML
diagram crops are pinned to this 22-page PDF layout and must be reinspected if
pagination changes. The earlier sets-only build remains available through
`prepare_sets.py` and the builder's default `sets` target.

The reader uses the frozen upstream mathematical notation. Noto Serif Devanagari
is pinned by Git blob and SHA-256; static derivatives are renamed OpenLogic Marathi
Serif. Font provenance and SIL OFL are in `fonts/`.

## License and attribution

The Open Logic Project's source and this marked Marathi adaptation are distributed
under **CC BY 4.0**. See `LICENSE.md` and all inherited component notices inside
`upstream/`. The complete pristine archive retains those notices. Font files use
their separate SIL Open Font License. This independent translation is not an
endorsement by the Open Logic Project or the Marathi reference publishers.
