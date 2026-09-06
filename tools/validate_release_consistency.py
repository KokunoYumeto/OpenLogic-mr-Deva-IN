"""Fail when release provenance, review occurrences, targets, or reader diverge."""

import argparse
import hashlib
import json
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Surface:
    def __init__(self, root: Path | None = None, archive: Path | None = None):
        self.root = root
        self.archive_path = archive
        self.archive = zipfile.ZipFile(archive) if archive else None
        self.names = set(self.archive.namelist()) if self.archive else None

    def read(self, name: str) -> bytes:
        if self.archive:
            return self.archive.read(name)
        return (self.root / PurePosixPath(name)).read_bytes()

    def exists(self, name: str) -> bool:
        if self.archive:
            return name in self.names
        return (self.root / PurePosixPath(name)).is_file()

    def close(self):
        if self.archive:
            self.archive.close()


def jsonl(surface: Surface, name: str):
    return [
        json.loads(line)
        for line in surface.read(name).decode("utf-8-sig").splitlines()
        if line.strip()
    ]


def occurrence_target_paths(row):
    if row.get("target_path"):
        return [row["target_path"]]
    return [item["path"] for item in row.get("target_locations", [])]


parser = argparse.ArgumentParser()
parser.add_argument("--editable-zip", type=Path)
parser.add_argument("--review-zip", type=Path)
parser.add_argument("--reader-pdf", type=Path, default=ROOT / "build/core/openlogic-mr-core.pdf")
parser.add_argument("--receipt", type=Path)
args = parser.parse_args()

editable = Surface(archive=args.editable_zip) if args.editable_zip else Surface(root=ROOT)
review = Surface(archive=args.review_zip) if args.review_zip else Surface(root=ROOT)
try:
    manifest = jsonl(editable, "provenance/SOURCE_MANIFEST.jsonl")
    segments = jsonl(editable, "provenance/SEGMENT_CANON_USE.jsonl")
    sources = jsonl(editable, "provenance/CANON_SOURCES.jsonl")
    passages = jsonl(editable, "provenance/CANON_PASSAGES.jsonl")
    terms = jsonl(editable, "provenance/TERM_DECISIONS.jsonl")
    occurrence_name = (
        "legacy/EXPERT_REVIEW_OCCURRENCES.jsonl"
        if args.review_zip
        else "provenance/EXPERT_REVIEW_OCCURRENCES.jsonl"
    )
    decision_name = (
        "legacy/EXPERT_REVIEW_DECISIONS.jsonl"
        if args.review_zip
        else "provenance/EXPERT_REVIEW_DECISIONS.jsonl"
    )
    canonical_name = (
        "translation-decisions/DECISIONS.json"
        if args.review_zip
        else "provenance/translation-decisions/DECISIONS.json"
    )
    occurrences = jsonl(review, occurrence_name)
    decisions = jsonl(review, decision_name)
    canonical = json.loads(review.read(canonical_name).decode("utf-8-sig"))

    assert len(manifest) == 722
    manifest_by_unit = {row["unit_id"]: row for row in manifest}
    assert len(manifest_by_unit) == 722
    manifest_by_source = {row["source_path"]: row for row in manifest}
    assert len(manifest_by_source) == 722

    target_units = {
        row["unit_id"]
        for row in manifest
        if editable.exists("mr/" + row["source_path"])
    }
    segment_units = {row["unit_id"] for row in segments}
    occurrence_units = {row["unit_id"] for row in occurrences}
    assert target_units == segment_units == occurrence_units, {
        "targets_missing_from_segments": sorted(target_units - segment_units),
        "segments_missing_from_targets": sorted(segment_units - target_units),
        "targets_missing_from_occurrences": sorted(target_units - occurrence_units),
        "occurrences_missing_from_targets": sorted(occurrence_units - target_units),
        "target_count": len(target_units),
        "segment_count": len(segment_units),
        "occurrence_count": len(occurrence_units),
    }
    ordered_units = sorted(target_units)
    assert ordered_units == [
        f"OLP-{number:04d}"
        for number in range(4, int(ordered_units[-1].split("-")[1]) + 1)
    ]

    source_ids = {row["source_id"] for row in sources}
    passage_ids = {row["passage_id"] for row in passages}
    term_ids = {row["term_id"] for row in terms}
    assert len(source_ids) == len(sources)
    assert len(passage_ids) == len(passages)
    assert len(term_ids) == len(terms)
    assert {row["source_id"] for row in passages} <= source_ids
    assert {
        passage_id
        for row in terms
        for passage_id in row.get("passages", [])
    } <= passage_ids

    segment_ids = set()
    segments_by_unit = defaultdict(int)
    for row in segments:
        assert row["segment_id"] not in segment_ids
        segment_ids.add(row["segment_id"])
        segments_by_unit[row["unit_id"]] += 1
        assert set(row["canon_passages_actually_consulted"]) <= passage_ids
        assert set(row["unit_term_decision_index"]) <= term_ids
        manifest_row = manifest_by_unit[row["unit_id"]]
        source_path = row["source_path"].replace("\\", "/")
        target_path = row["translation_path"].replace("\\", "/")
        assert source_path == manifest_row["source_path"]
        assert target_path == "mr/" + manifest_row["source_path"]
        source_bytes = editable.read("upstream/" + source_path)
        target_bytes = editable.read(target_path)
        assert sha(source_bytes) == row["source_unit_sha256"] == manifest_row["source_sha256"]
        assert sha(target_bytes) == row["translation_unit_sha256"]
    assert set(segments_by_unit) == target_units

    decision_ids = {row.get("term_id") or row.get("issue_id") for row in decisions}
    assert len(decision_ids) == len(decisions)
    occurrence_ids = set()
    for row in occurrences:
        assert row["occurrence_id"] not in occurrence_ids
        occurrence_ids.add(row["occurrence_id"])
        assert row["decision_id"] in decision_ids
        expected_target = "mr/" + manifest_by_unit[row["unit_id"]]["source_path"]
        assert occurrence_target_paths(row), row["occurrence_id"]
        assert set(occurrence_target_paths(row)) == {expected_target}, row["occurrence_id"]

    canonical_occurrences = {
        occurrence["occurrence_id"]
        for decision in canonical["decisions"]
        for occurrence in decision["occurrences"]
    }
    assert canonical_occurrences == occurrence_ids

    available_hashes = {
        row["reader_pdf_sha256"]
        for row in occurrences
        if row.get("reader_pdf_pages")
    }
    assert len(available_hashes) == 1
    reader_hash = next(iter(available_hashes))
    for row in occurrences:
        if row.get("reader_pdf_pages"):
            assert row["reader_pdf_sha256"] == reader_hash
        else:
            assert row.get("reader_pdf_sha256") is None
            assert row.get("reader_page_label") in {None, "not yet paginated"}
            assert row.get("page_locator_precision") in {
                None,
                "unit not yet paginated",
            }
    if args.reader_pdf and args.reader_pdf.is_file():
        assert sha(args.reader_pdf.read_bytes()) == reader_hash

    canonical_available_hashes = {
        occurrence["reader_locator"].get("artifact_sha256")
        for decision in canonical["decisions"]
        for occurrence in decision["occurrences"]
        if occurrence["reader_locator"]["status"] == "available"
    }
    assert canonical_available_hashes == {reader_hash}

    result = {
        "schema": "openlogic-cross-package-consistency/1",
        "scope": {
            "source_manifest_units": len(manifest),
            "translated_units": len(target_units),
            "first_unit": ordered_units[0],
            "last_unit": ordered_units[-1],
            "aligned_segments": len(segments),
            "review_occurrences": len(occurrences),
            "canonical_decisions": len(canonical["decisions"]),
            "canon_sources": len(sources),
            "canon_passages": len(passages),
            "term_decisions": len(terms),
        },
        "set_equality": {
            "translated_target_units_equal_segment_units": True,
            "segment_units_equal_review_occurrence_units": True,
            "review_targets_match_manifest_targets": True,
        },
        "reference_integrity": {
            "source_manifest_exactly_722": True,
            "segment_source_and_target_hashes_replayed": len(segments),
            "canon_source_and_passage_references_resolved": True,
            "term_decision_references_resolved": True,
            "legacy_and_canonical_occurrence_ids_equal": True,
        },
        "reader_binding": {
            "sha256": reader_hash,
            "available_occurrences_share_one_reader_hash": True,
            "unpaginated_occurrences_have_no_fabricated_reader_hash_or_numeric_page": True,
            "reader_pdf_bytes_verified_when_supplied": bool(
                args.reader_pdf and args.reader_pdf.is_file()
            ),
        },
        "surfaces": {
            "editable": args.editable_zip.name if args.editable_zip else "working tree",
            "review": args.review_zip.name if args.review_zip else "working tree",
        },
        "result": "passed",
    }
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.receipt:
        args.receipt.write_bytes(encoded)
    print(encoded.decode("utf-8"), end="")
finally:
    editable.close()
    review.close()
