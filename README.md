# OpenLogic · मराठी (mr-Deva-IN)

मुक्त तर्कशास्त्राची मराठी आवृत्ती. संपूर्ण 722 स्रोत-विभागांच्या अनुवादाचे काम सुरू आहे.

सध्याच्या प्रकाशनात **संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण,
अनंत संच, विन्यासमीमांसा व चिन्हार्थमीमांसा आणि सिद्धता-पद्धती ही आठ संपूर्ण
प्रकरणे** आहेत: OLP-0004–OLP-0068, एकूण 65 स्रोत-विभाग, 56 मुख्य विभाग,
सर्व उदाहरणे, आकृत्यांचे मथळे आणि सराव. उर्वरित **657 विभागांचा अनुवाद अद्याप
पूर्ण झालेला नाही**.
हे संपूर्ण ग्रंथाचे प्रकाशन नाही.

This is an independent Marathi edition of *The Open Logic Text*. The finite
commission covers all 722 content TeX units at upstream revision
`9620cc73f9c8e0ad003c514a5d3748f29611c4c0`. The cumulative release covers 65/722
units (747 content segments). Source IDs and paths remain aligned to the frozen corpus.
The Sets, Relations, Functions, Size of Sets, Arithmetization, Infinite Sets,
Syntax and Semantics, and Proof Systems chapters are complete in source and reader
form. The 89-page PDF was built twice to identical bytes and every page was
inspected. Its offline HTML companion passed exact source-conversion, structure,
asset, proof-display and desktop/mobile browser checks.

Editable source after that release has progressed through OLP-0078: **75/722
units** and 832 aligned content blocks. OLP-0069 is the Sequent Calculus chapter
driver; OLP-0070 defines its sequents, initial sequents, derivation trees and rule
classes; OLP-0071 and OLP-0072 give the propositional and quantifier rules;
OLP-0073–OLP-0076 cover structural rules, derivations and worked proofs,
OLP-0077 defines proof-theoretic notions, and OLP-0078 develops provability and
consistency consequences. These ten units are not yet part of the v0.6 reader or
release archive.

- **Current release:** [आठ प्रकरणे — PDF, offline HTML, editable sources and review bundle](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/eight-chapters-v0.6).
- **DOI mirror:** [edition concept DOI 10.5281/zenodo.22307960](https://doi.org/10.5281/zenodo.22307960), which resolves to the latest version.
- **PDF:** [89-page cumulative reader](releases/eight-chapters-v0.6/openlogic-mr-eight-chapters.pdf).
- **Offline HTML:** download and extract `openlogic-mr-eight-chapters-html.zip`, then open `index.html`.
- **Editable Marathi:** [sets](mr/content/sets-functions-relations/sets/), [relations](mr/content/sets-functions-relations/relations/), [functions](mr/content/sets-functions-relations/functions/), [size of sets](mr/content/sets-functions-relations/size-of-sets/), [arithmetization](mr/content/sets-functions-relations/arithmetization/), [infinite sets](mr/content/sets-functions-relations/infinite/), [propositional syntax and semantics](mr/content/propositional-logic/syntax-and-semantics/), [first-order proof systems](mr/content/first-order-logic/proof-systems/), and the in-progress [sequent calculus](mr/content/first-order-logic/sequent-calculus/).
- **Terminology and expert review:** begin with the [shared-schema review guide](provenance/translation-decisions/START_HERE.md), then use the [full applied-decision index](provenance/translation-decisions/TRANSLATION_DECISIONS_FULL.md), [priority review](provenance/translation-decisions/PRIORITY_REVIEW.md), [one-row-per-occurrence CSV](provenance/translation-decisions/DECISION_OCCURRENCES.csv), or [canonical JSON](provenance/translation-decisions/DECISIONS.json). The backward-compatible [decision ledger](provenance/EXPERT_REVIEW_LOG.md) and occurrence JSONL remain available. These surfaces record exact source/target scopes, current PDF page ranges, reversible choices and plain review questions without making review a completion gate.
- **Pristine English:** `upstream/`; this is source evidence, not translated coverage.
- **Current source-checkpoint evidence:** `provenance/source-checkpoint-65/`.
- **Current reader evidence:** `provenance/eight-chapters-v0.6/`.
- **Earlier cumulative release:** [seven-chapters-v0.5.1](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/seven-chapters-v0.5.1), preserved unchanged.
- **Earlier cumulative release:** [seven-chapters-v0.5](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/seven-chapters-v0.5), preserved unchanged.
- **Earlier cumulative release:** [six-chapters-v0.4](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/six-chapters-v0.4), preserved unchanged.
- **Released-reader evidence:** `provenance/foundations-v0.2/`; root-level provenance remains the historical first release snapshot.
- **Earlier cumulative release:** [foundations-v0.2](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/foundations-v0.2), preserved unchanged.
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

The eight published chapters have 747 aligned content segments with consultation
records across 65 units.
Deterministic checks compare formulas, token identities, macro inventories,
labels, citations, links and source file references.
Visual, structural and semantic checks are documented in
`provenance/eight-chapters-v0.6/` and the 65-unit source checkpoint.
Such checks do not establish the absence
of every possible translation error.
Two guarded builds on the same host produced identical PDF bytes with fixed
`SOURCE_DATE_EPOCH`; cross-platform byte identity has not been tested.

The offline HTML includes 3,521 MathML expressions with original TeX annotations,
thirteen diagrams with detailed Marathi alternatives, three semantic proof figures
with eleven formula rows, local fonts, a linked contents list and keyboard-focusable
formula regions. Exact conversion checks preserve ordinary prose, footnotes and
formulas; internal references match PDF numbering.
Browser inspection passed at 1280 × 720 and 390 × 844 CSS pixels with no page-level
horizontal overflow, all thirteen diagrams loaded, contained horizontal scrolling
for proof tables, working skip navigation and no console errors. Assistive-
technology behavior is not independently certified. Inherited source issues are
explained in a separate editorial section; frozen English bytes remain unchanged.
The evidence also preserves the formal retraction of a
shared OLSIZ-011 false-positive alert, which was not applied to Marathi. The frozen
65-unit source-checkpoint evidence explicitly distinguishes preserved original
pages from hash-pinned short web observations whose origin HTML bytes were
unavailable. The synchronized root provenance now covers the 75 translated units
through OLP-0078. A bounded independent model audit of OLP-0071–OLP-0072 found no
material mistranslation, prompted one standing-assumption clarification, and led
to narrower overlapping choice locators plus separate confidence records for
closed term, bound variable and eigenvariable vocabulary. This audit is not
native-speaker or human-expert testimony. The OLP-0077 compactness choice records
official mathematical evidence for संहतता while disclosing that proof-theory usage
was not directly attested; OLP-0078 records the corresponding finite-cut and
negation characterizations of provability and inconsistency. These later working records remain
outside the v0.6 reader and release archive.

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

The eight-chapter development reader can be prepared and built through OLP-0068 with:

```powershell
python tools/prepare_core65.py
./tools/build_guarded.ps1 -Target core
python tools/prepare_core_html.py
python tools/qa_core_html.py
```

The guarded builder reserves `Global\InterlanguageTeXSlotV1` with one bounded
timeout, captures its TeX process tree in a Windows job, holds the mutex through
both passes and log checks, and releases it in `finally`. A busy slot launches
no TeX. `SOURCE_DATE_EPOCH` is set for the child build and restored afterward.
The adapter includes all novice, mathematics and computing passages. Four
conditional occurrences whose referenced sections are not yet included take their
original false branches in this partial reader; the complete translated TeX retains
both original branches. The HTML diagram crops are pinned to this 89-page PDF layout,
guarded against prose-only crops, and must be reinspected if pagination changes.
The earlier sets-only build remains available through
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
