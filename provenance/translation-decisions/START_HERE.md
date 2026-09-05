# Start here: Marathi translation decisions

This bundle is the expert-review entry point for the five-chapter Marathi 
OpenLogic checkpoint through OLP-0048. It covers 45/722 source units, five 
complete chapters, 127 applied decisions and 3,743 exact current occurrences. 
The remaining 677 units are untranslated.

No independent human or native-speaker review is claimed. Every choice remains 
reversible, and a review question is a request for useful evidence rather than 
a publication or completion hold.

## Files

- `TRANSLATION_DECISIONS_FULL.md` is the readable complete applied-decision index.
- `PRIORITY_REVIEW.md` contains only urgent/high review items and their occurrences.
- `DECISION_OCCURRENCES.csv` has one UTF-8 row for each of 3,743 occurrences.
- `DECISIONS.json` is the canonical machine record validated against the shared schema.
- `translation-decision.schema.json` is the exact frozen shared schema.
- `TRANSLATION_DECISION_QA.json` records validation, counts and hashes.

The PDF page field is the current assembled-reader page or range. Unknown pages 
must use schema status `pending`; none were guessed in this checkpoint. Source 
and target locators contain current file SHA-256 values, exact line spans, byte 
spans and excerpts. Four prospective terminology records (`T009`, `T011`, 
`T012`, `T013`) remain in the backward-compatible legacy ledger but are deferred 
from `DECISIONS.json` because they have no occurrence in the current 45-unit 
coverage and the shared schema requires at least one real occurrence per decision.

The full source-aligned Marathi edition remains the controlling deliverable. This 
review bundle does not define a second regional or notation variant.
