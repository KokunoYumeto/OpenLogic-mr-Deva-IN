# OpenLogic · मराठी (mr-Deva-IN)

मुक्त तर्कशास्त्राची मराठी आवृत्ती. संपूर्ण 722 स्रोत-विभागांच्या अनुवादाचे काम सुरू आहे.

पहिल्या प्रकाशनात **संपूर्ण संच प्रकरण** आहे: OLP-0004–OLP-0010, सात स्रोत-विभाग,
सहा मुख्य विभाग, सर्व उदाहरणे, आकृत्यांचे मथळे आणि सराव. उर्वरित **715 विभागांचा
अनुवाद अद्याप पूर्ण झालेला नाही**. हे संपूर्ण ग्रंथाचे प्रकाशन नाही.

This is an independent Marathi edition of *The Open Logic Text*. The finite
commission covers all 722 content TeX units at upstream revision
`9620cc73f9c8e0ad003c514a5d3748f29611c4c0`. Work continues beyond this first complete
chapter tranche. Source IDs and paths remain aligned to the frozen corpus.

- **Reader:** [संच — complete sets chapter](releases/sets-v0.1/openlogic-mr-sets.pdf).
- **Editable Marathi:** [aligned TeX](mr/content/sets-functions-relations/sets/).
- **Pristine English:** `upstream/`; this is source evidence, not translated coverage.
- **Coverage, term decisions and consultation:** `provenance/`.
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

The first chapter has 86 aligned content segments with consultation records.
Deterministic checks compare formulas, token identities, macro inventories,
labels, citations, links and source file references.
Visual and semantic checks are documented in `provenance/QA-B001.json` and
`provenance/SEMANTIC_REVIEW-B001.json`. Such checks do not establish the absence
of every possible translation error.
Two guarded builds on the same host produced identical PDF bytes with fixed
`SOURCE_DATE_EPOCH`; cross-platform byte identity has not been tested.

Canon originals are local research evidence. They are **not redistributed here**.
Some government-site originals could not be downloaded; the index distinguishes
verified preserved PDF bytes from short observations and does not invent source
hashes. A dictionary label alone is not treated as complete semantic evidence.

## Rebuild the chapter

Requirements: Python with `fonttools`, a current XeLaTeX installation and its
standard packages, and PowerShell on Windows. The licensed font files are included.

```powershell
python tools/prepare_sets.py
./tools/build_guarded.ps1
```

The guarded builder reserves `Global\InterlanguageTeXSlotV1` with one bounded
timeout, captures its TeX process tree in a Windows job, holds the mutex through
both passes and log checks, and releases it in `finally`. A busy slot launches
no TeX. `SOURCE_DATE_EPOCH` is set for the child build and restored afterward.
The adapter includes all novice, mathematics and computing passages. Two original
cross-chapter conditionals take their original false branch in this chapter-only
reader; the complete translated TeX retains both original branches.

The reader uses the frozen upstream mathematical notation. Noto Serif Devanagari
is pinned by Git blob and SHA-256; static derivatives are renamed OpenLogic Marathi
Serif. Font provenance and SIL OFL are in `fonts/`.

## License and attribution

The Open Logic Project's source and this marked Marathi adaptation are distributed
under **CC BY 4.0**. See `LICENSE.md` and all inherited component notices inside
`upstream/`. The complete pristine archive retains those notices. Font files use
their separate SIL Open Font License. This independent translation is not an
endorsement by the Open Logic Project or the Marathi reference publishers.
