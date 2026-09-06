# Start here: Marathi translation decisions

This bundle is the expert-review entry point for the current Marathi 
OpenLogic translation through OLP-0064. It covers 61/722 source units, 
7 complete chapters, 194 applied decisions and 
4,523 exact current occurrences. The remaining 661 units are untranslated.
The paginated 7-chapter reader ends at OLP-0062; later translated units use pending PDF locators.

No independent human or native-speaker review is claimed. Every choice remains 
reversible, and a review question is a request for useful evidence rather than 
a publication or completion hold.

## Files

- `TRANSLATION_DECISIONS_FULL.md` is the readable complete applied-decision index.
- `PRIORITY_REVIEW.md` contains only urgent/high review items and their occurrences.
- `DECISION_OCCURRENCES.csv` has one UTF-8 row for each of 4,523 occurrences.
- `DECISIONS.json` is the canonical machine record validated against the shared schema.
- `translation-decision.schema.json` is the exact frozen shared schema.
- `TRANSLATION_DECISION_QA.json` records validation, counts and hashes.

The PDF page field is the current assembled-reader page or range. Unknown pages 
must use schema status `pending`; none were guessed in this checkpoint. Source 
and target locators contain current file SHA-256 values, exact line spans, byte 
spans and excerpts. Two prospective terminology records (`T009`, `T013`) 
remain in the backward-compatible legacy ledger but are deferred 
from `DECISIONS.json` because they have no occurrence in the current 61-unit 
coverage and the shared schema requires at least one real occurrence per decision.

The full source-aligned Marathi edition remains the controlling deliverable. This 
review bundle does not define a second regional or notation variant.
