# OpenLogic · मराठी (mr-Deva-IN)

This repository contains the Marathi (Devanagari, `mr-Deva-IN`) adaptation of
the Open Logic Project text. The current coherent reader is
[eleven-chapters-v0.8](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/eleven-chapters-v0.8): 108 of 722 source units, 11 complete chapters, 96 reader sections, and 1,149 aligned translated content segments through OLP-0111.

The release includes a 157-page PDF, an offline HTML reader with native MathML,
editable Marathi sources, the frozen English source, review records, and
reproducibility manifests. The corresponding Zenodo version is
[10.5281/zenodo.22681530](https://doi.org/10.5281/zenodo.22681530), in the
existing concept-DOI lineage [10.5281/zenodo.22307960](https://doi.org/10.5281/zenodo.22307960).

Codex produced the machine translation and same-agent bilingual review. No
independent human or native-speaker linguistic review is claimed. The Open
Logic Project is credited as creator of the original text and does not endorse
this translation. The text and marked adaptation use CC BY 4.0; inherited
component notices and the SIL Open Font License remain with their components.

मुक्त तर्कशास्त्राची मराठी आवृत्ती. संपूर्ण 722 स्रोत-विभागांच्या अनुवादाचे काम सुरू आहे.

सध्याच्या प्रकाशनात **संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण,
अनंत संच, विन्यासमीमांसा व चिन्हार्थमीमांसा, सिद्धता-पद्धती, क्रमवर्ती कलन
आणि नैसर्गिक निगमन ही दहा संपूर्ण प्रकरणे** आहेत: OLP-0004–OLP-0097,
एकूण 94 स्रोत-विभाग, 83 मुख्य विभाग, सर्व उदाहरणे, आकृत्यांचे मथळे आणि
सराव. उर्वरित **628 विभागांचा अनुवाद अद्याप
पूर्ण झालेला नाही**.
हे संपूर्ण ग्रंथाचे प्रकाशन नाही.

This is an independent Marathi edition of *The Open Logic Text*. The finite
commission covers all 722 content TeX units at upstream revision
`9620cc73f9c8e0ad003c514a5d3748f29611c4c0`. The cumulative release covers 94/722
units (1,018 content segments). Source IDs and paths remain aligned to the frozen corpus.
The Sets, Relations, Functions, Size of Sets, Arithmetization, Infinite Sets,
Syntax and Semantics, Proof Systems, Sequent Calculus, and Natural Deduction
chapters are complete in source and reader form. The 133-page PDF was built twice
to identical bytes and every page was
inspected. Its offline HTML companion passed exact source-conversion, structure,
asset, proof-display and desktop/mobile browser checks.

The editable working tree now continues through OLP-0106 in the Tableaux chapter:
103/722 units and 1,103 aligned content segments. OLP-0098–OLP-0106 remain
intentionally outside the frozen 94-unit v0.7 reader, source checkpoint and
release archive. Translation resumes at OLP-0107.

- **Current release:** [दहा प्रकरणे — PDF, offline HTML, editable sources and review bundle](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/ten-chapters-v0.7).
- **DOI mirror:** [edition concept DOI 10.5281/zenodo.22307960](https://doi.org/10.5281/zenodo.22307960), which resolves to the latest version.
- **PDF:** [133-page cumulative reader](releases/ten-chapters-v0.7/openlogic-mr-ten-chapters.pdf).
- **Offline HTML:** download and extract `openlogic-mr-ten-chapters-html.zip`, then open `index.html`.
- **Editable Marathi:** [sets](mr/content/sets-functions-relations/sets/), [relations](mr/content/sets-functions-relations/relations/), [functions](mr/content/sets-functions-relations/functions/), [size of sets](mr/content/sets-functions-relations/size-of-sets/), [arithmetization](mr/content/sets-functions-relations/arithmetization/), [infinite sets](mr/content/sets-functions-relations/infinite/), [propositional syntax and semantics](mr/content/propositional-logic/syntax-and-semantics/), [first-order proof systems](mr/content/first-order-logic/proof-systems/), [sequent calculus](mr/content/first-order-logic/sequent-calculus/), [natural deduction](mr/content/first-order-logic/natural-deduction/), and [Tableaux](mr/content/first-order-logic/tableaux/).
- **Terminology and expert review:** begin with the [shared-schema review guide](provenance/translation-decisions/START_HERE.md), then use the [full applied-decision index](provenance/translation-decisions/TRANSLATION_DECISIONS_FULL.md), [priority review](provenance/translation-decisions/PRIORITY_REVIEW.md), [one-row-per-occurrence CSV](provenance/translation-decisions/DECISION_OCCURRENCES.csv), or [canonical JSON](provenance/translation-decisions/DECISIONS.json). The backward-compatible [decision ledger](provenance/EXPERT_REVIEW_LOG.md) and occurrence JSONL remain available. These surfaces record exact source/target scopes, current PDF page ranges, reversible choices and plain review questions without making review a completion gate.
- **Pristine English:** `upstream/`; this is source evidence, not translated coverage.
- **Current source-checkpoint evidence:** `provenance/source-checkpoint-94/`.
- **Current reader evidence:** `provenance/ten-chapters-v0.7/`.
- **Earlier cumulative release:** [eight-chapters-v0.6](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/eight-chapters-v0.6), preserved unchanged.
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

The ten published chapters have 1,018 aligned content segments with consultation
records across 94 units.
Deterministic checks compare formulas, token identities, macro inventories,
labels, citations, links and source file references.
Visual, structural and semantic checks are documented in
`provenance/ten-chapters-v0.7/` and the 94-unit source checkpoint.
Such checks do not establish the absence
of every possible translation error.
Two guarded builds on the same host produced identical PDF bytes with fixed
`SOURCE_DATE_EPOCH`; cross-platform byte identity has not been tested.

The offline HTML includes 5,608 MathML expressions with original TeX annotations,
thirteen diagrams with detailed Marathi alternatives, 143 semantic proof figures
with 674 formula rows, local fonts, a linked contents list and keyboard-focusable
formula regions. Exact conversion checks preserve ordinary prose, footnotes and
formulas; internal references match PDF numbering.
Browser inspection passed at 1280 × 720 and 390 × 844 CSS pixels with no page-level
horizontal overflow, all thirteen diagrams loaded, contained horizontal scrolling
for proof tables, working skip navigation and no console errors. Assistive-
technology behavior is not independently certified. Inherited source issues are
explained in a separate editorial section; frozen English bytes remain unchanged.
The evidence also preserves the formal retraction of a
shared OLSIZ-011 false-positive alert, which was not applied to Marathi. The frozen
94-unit source-checkpoint evidence explicitly distinguishes preserved original
pages from hash-pinned short web observations whose origin HTML bytes were
unavailable. The synchronized root provenance now covers 103 translated units and
1,103 aligned segments through OLP-0106. A bounded independent model audit of
OLP-0071–OLP-0072 found no
material mistranslation, prompted one standing-assumption clarification, and led
to narrower overlapping choice locators plus separate confidence records for
closed term, bound variable and eigenvariable vocabulary. This audit is not
native-speaker or human-expert testimony. A separate bounded audit of OLP-0087
confirmed the closed-term clarification and identified a defective source summary
that excluded the eigenvariable from every premise despite the displayed
universal-introduction premise $A(a)$. OLND-002 records the correction: the Marathi
summary now refers to the distinct rule-specific premise, conclusion and
undischarged-assumption restrictions, including the existential-elimination
temporary-assumption exception. The OLP-0077 compactness choice records
official mathematical evidence for संहतता while disclosing that proof-theory usage
was not directly attested; OLP-0078 records the corresponding finite-cut and
negation characterizations of provability and inconsistency, OLP-0079 records
the conjunction, disjunction and conditional derivations that follow, OLP-0080
records the strong-generalization and quantifier derivations, and OLP-0081 records
the semantic soundness induction and weak, entailment and consistency corollaries,
and OLP-0082 records identity initial sequents, equality substitution, symmetry
and transitivity, while OLP-0083 records the semantic soundness proof for
equality substitution. OLP-0084 records the natural-deduction chapter driver
and its conditional imports, OLP-0085 records assumptions, discharge, premises
and conclusions, and rule pairs, OLP-0086 records the propositional rule
schemata and the permissive interpretation of discharge annotations, and
OLP-0087 records quantifier rules, eigenvariable conditions and the documented
closed-term clarification OLND-001 plus eigenvariable-summary correction OLND-002,
OLP-0088 records the inductive finite-tree definition of derivations, provability
notation and optional-discharge examples, and OLP-0089 records worked proof search,
excluded middle and three exercise sets. Its OLND-003 correction reconciles a
left/right branch contradiction; OLND-004 preserves and discloses an equivalent
rule-label switch in the frozen source. OLP-0090 records three quantified worked
derivations and two exercise sets. OLND-005 restores a negation dropped from a
prose-side eigenvariable check and states the declared rule scope; OLND-006 retains
the standing closed-term restriction for universal elimination. OLP-0091 records
the natural-deduction definitions and proofs for theoremhood, derivability,
consistency, reflexivity, monotonicity, transitivity and compactness. OLP-0092
records the negation characterization of derivability and three resulting
inconsistency propositions. OLP-0093 records the basic conjunction, disjunction
and conditional derivations needed for completeness. OLP-0094 records strong
generalization, existential introduction and universal elimination. OLP-0095
proves natural-deduction soundness by induction on the last inference and records
its validity and consistency corollaries; OLND-007 documents an equivalent frozen
macro spelling in one exercise label. OLP-0096 adds identity introduction and
elimination, substitutability of identicals, and a quantified uniqueness example.
OLP-0097 proves that reflexive identity is valid and identity elimination preserves
truth under equal term values. OLP-0098 begins the Tableaux chapter, preserves its
conditional first-order imports, and corrects the copied source description of the
chapter as natural deduction under OLTAB-001. OLP-0099 defines signed formulas,
rule application along a branch, closed branches and the semantic force of a
closed tableau rooted at a false-signed sentence. OLP-0100 supplies the four
propositional rule pairs and cut; OLP-0101 supplies the quantifier rules, closed-term
and eigenvariable conditions, substitution examples and their soundness rationale.
OLTAB-002 makes the standing closed-term restriction explicit in the final
quantifier-rule contrast.
OLP-0102 defines tableaux as finite inductively generated trees and demonstrates
closure from opposite-signed formulas. OLP-0103 adds three complete propositional
construction examples, explains checkmarks and branch-wide rule application, and
preserves 24 exercises. OLP-0104 gives three quantified construction examples,
preserves 15 successive tableau trees and 9 exercises, and documents the standing
closed-term restriction and one bad source line reference. OLP-0105 defines
tableau theoremhood, derivability and consistency and proves reflexivity,
monotonicity, transitivity and compactness. OLP-0106 proves four further
derivability/consistency properties through finite closed-tableau transformations
and Cut, with its bounded source repairs recorded in OLTAB-006–OLTAB-009.
The records through OLP-0097 are included in the v0.7 reader and release archive;
OLP-0098–OLP-0106 are post-release working units. OLP-0107 is next.

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

The ten-chapter development reader can be prepared and built through OLP-0097 with:

```powershell
python tools/prepare_core94.py
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
both original branches. The HTML diagram crops are pinned to this 133-page PDF layout,
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
