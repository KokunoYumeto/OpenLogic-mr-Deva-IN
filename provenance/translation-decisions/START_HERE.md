# Start here: Marathi translation decisions

This bundle is the expert-review entry point for the current Marathi 
OpenLogic translation through OLP-0069. It covers 66/722 source units, 
8 complete chapters, 210 applied decisions and 
4,696 exact current occurrences. The remaining 656 units are untranslated.
The paginated 8-chapter reader ends at OLP-0068; later translated units use pending PDF locators.

No independent human or native-speaker review is claimed. Every choice remains 
reversible, and a review question is a request for useful evidence rather than 
a publication or completion hold.

## Files

- `TRANSLATION_DECISIONS_FULL.md` is the readable complete applied-decision index.
- `PRIORITY_REVIEW.md` contains only urgent/high review items and their occurrences.
- `DECISION_OCCURRENCES.csv` has one UTF-8 row for each of 4,696 occurrences.
- `DECISIONS.json` is the canonical machine record validated against the shared schema.
- `translation-decision.schema.json` is the exact frozen shared schema.
- `TRANSLATION_DECISION_QA.json` records validation, counts and hashes.

The PDF page field is the current assembled-reader page or range. Unknown pages 
must use schema status `pending`; none were guessed in this checkpoint. Source 
and target locators contain current file SHA-256 values, exact line spans, byte 
spans and excerpts. 1 prospective terminology records (`T013`) 
remain in the backward-compatible legacy ledger but are deferred 
from `DECISIONS.json` because they have no occurrence in the current 66-unit 
coverage and the shared schema requires at least one real occurrence per decision.

The full source-aligned Marathi edition remains the controlling deliverable. This 
review bundle does not define a second regional or notation variant.
