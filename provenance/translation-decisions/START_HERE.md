# Start here: Marathi translation decisions

This bundle is the expert-review entry point for the current Marathi
OpenLogic translation through OLP-0197. It covers 194/722 source units,
11 complete chapters, 406 applied decisions and
11,402 current decision-level occurrence records. The remaining 528 units are untranslated.
The paginated 11-chapter reader ends at OLP-0111; later translated units use pending PDF locators.

No independent human or native-speaker review is claimed. Every choice remains
reversible, and a review question is a request for useful evidence rather than
a publication or completion hold.

## Files

- `TRANSLATION_DECISIONS_FULL.md` is the readable complete applied-decision index.
- `PRIORITY_REVIEW.md` contains only urgent/high review items and their occurrences.
- `DECISION_OCCURRENCES.csv` has one UTF-8 row for each of 11,402 occurrences.
- `DECISIONS.json` is the canonical machine record validated against the shared schema.
- `translation-decision.schema.json` is the exact frozen shared schema.
- `TRANSLATION_DECISION_QA.json` records validation, counts and hashes.

The PDF page field is the current assembled-reader page or range. Unknown pages
must use schema status `pending`; none were guessed in this checkpoint. Source
and target locators contain current file SHA-256 values, exact line spans, byte
spans and excerpts. Every decision in the backward-compatible legacy ledger has at least one real occurrence in the current coverage; none are deferred from `DECISIONS.json`.
Decision-relevant spans are narrower than aligned context blocks where explicitly recorded. They may overlap when one construction realizes several choices and do not claim a disjoint token partition.

The full source-aligned Marathi edition remains the controlling deliverable. This
review bundle does not define a second regional or notation variant.
