"""Freeze the complete source-aligned translation ledger for a full release.

The root repository's detailed expert-review bundle is historically scoped to
the earlier chapters. This export keeps its coverage separate from the
722-unit aligned translation and consultation ledger.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = Path(r"C:\interlanguage-task-state\openlogic-mr-Deva-IN")
OUT = ROOT / "build/full/release-provenance"
OUT.mkdir(parents=True, exist_ok=True)
NAMES = (
    "SOURCE_MANIFEST.jsonl", "SEGMENT_CANON_USE.jsonl",
    "CANON_SOURCES.jsonl", "CANON_PASSAGES.jsonl", "TERM_DECISIONS.jsonl",
)
PRIVATE_KEYS = {"local_path", "page_image", "observation_file", "ocr_path"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def scrub(value):
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items() if key not in PRIVATE_KEYS}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str) and re.match(r"^[A-Za-z]:[\\/]", value):
        return "[local research path omitted]"
    return value


data = {}
for name in NAMES:
    source = STATE / name
    assert source.is_file(), source
    data[name] = rows(source)
    serialized = "".join(
        json.dumps(scrub(row), ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in data[name]
    )
    assert not re.search(r"[A-Za-z]:[\\/]+Users[\\/]", serialized, re.I)
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+", serialized)
    (OUT / name).write_text(serialized, encoding="utf-8", newline="\n")

retrospective = ROOT / "provenance/complete-v1.1/CANON_RECHECK_101.json"
if retrospective.is_file():
    audit = json.loads(retrospective.read_text(encoding="utf-8"))
    assert len(audit["records"]) == 101 and audit["date"] == "2026-09-29"
    for name, expected_hash in audit["source_files_sha256"].items():
        assert sha(STATE / name) == expected_hash
    (OUT / "CANON_RECHECK_101.json").write_bytes(retrospective.read_bytes())

manifest = data["SOURCE_MANIFEST.jsonl"]
segments = data["SEGMENT_CANON_USE.jsonl"]
sources = data["CANON_SOURCES.jsonl"]
passages = data["CANON_PASSAGES.jsonl"]
terms = data["TERM_DECISIONS.jsonl"]
by_unit = {row["unit_id"]: row for row in manifest}
assert len(manifest) == len(by_unit) == 722
expected = {f"OLP-{number:04d}" for number in range(1, 723)}
assert set(by_unit) == expected
assert {row["unit_id"] for row in segments} == expected
assert len({row["segment_id"] for row in segments}) == len(segments)
source_ids = {row["source_id"] for row in sources}
passage_ids = {row["passage_id"] for row in passages}
term_ids = {row["term_id"] for row in terms}
assert len(source_ids) == len(sources)
assert len(passage_ids) == len(passages)
assert len(term_ids) == len(terms)
assert {row["source_id"] for row in passages} <= source_ids
assert {passage_id for row in terms for passage_id in row.get("passages", [])} <= passage_ids

checked_files = {}
for row in segments:
    unit = by_unit[row["unit_id"]]
    source_path = row["source_path"].replace("\\", "/")
    target_path = row["translation_path"].replace("\\", "/")
    assert source_path == unit["source_path"]
    assert target_path == "mr/" + source_path
    assert set(row["canon_passages_actually_consulted"]) <= passage_ids
    assert set(row["unit_term_decision_index"]) <= term_ids
    if row["unit_id"] not in checked_files:
        original = ROOT / "upstream" / source_path
        target = ROOT / target_path
        assert original.is_file() and target.is_file()
        assert sha(original) == row["source_unit_sha256"] == unit["source_sha256"]
        assert sha(target) == row["translation_unit_sha256"]
        checked_files[row["unit_id"]] = {
            "source": row["source_unit_sha256"],
            "target": row["translation_unit_sha256"],
        }
    else:
        assert checked_files[row["unit_id"]] == {
            "source": row["source_unit_sha256"],
            "target": row["translation_unit_sha256"],
        }

# The root file is the current full-scope derived review surface. The frozen
# historical detailed review was preserved separately before that expansion.
historical = ROOT / "build/full/pre-final-provenance"
review_rows = rows(historical / "EXPERT_REVIEW_OCCURRENCES.jsonl")
review_units = {row["unit_id"] for row in review_rows}
assert review_units <= expected
assert len(review_units) == 281
assert len(review_rows) == 14221
for name in ("EXPERT_REVIEW_DECISIONS.jsonl", "EXPERT_REVIEW_OCCURRENCES.jsonl",
             "EXPERT_REVIEW_OCCURRENCES.csv", "EXPERT_REVIEW_LOG.md",
             "EXPERT_REVIEW_OCCURRENCES.md", "EXPERT_REVIEW_PRIORITY.md"):
    (OUT / "historical-detailed-review" / name).parent.mkdir(parents=True, exist_ok=True)
    (OUT / "historical-detailed-review" / name).write_bytes((historical / name).read_bytes())
receipt = {
    "schema": "openlogic-complete-provenance-qa/1",
    "status": "passed",
    "source_units": len(manifest),
    "translated_units": len(checked_files),
    "aligned_segments": len(segments),
    "canon_sources": len(sources),
    "canon_passages": len(passages),
    "term_decisions": len(terms),
    "detailed_review_units": len(review_units),
    "detailed_review_occurrences": len(review_rows),
    "detailed_review_scope": [min(review_units), max(review_units)],
    "files": [
        {"name": name, "bytes": (OUT / name).stat().st_size, "sha256": sha(OUT / name)}
        for name in NAMES
    ],
}
(ROOT / "build/full/PROVENANCE_QA.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({key: receipt[key] for key in (
    "status", "source_units", "translated_units", "aligned_segments",
    "detailed_review_units", "detailed_review_occurrences",
)}, ensure_ascii=False))
