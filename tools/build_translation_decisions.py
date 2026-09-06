"""Adapt the Marathi expert-review ledger to the shared OpenLogic schema."""

import csv
import hashlib
import importlib.metadata
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


P = Path(__file__).resolve().parents[1]
PROV = P / "provenance"
OUT = PROV / "translation-decisions"
SCHEMA_PATH = OUT / "translation-decision.schema.json"
DECISION_INPUT = PROV / "EXPERT_REVIEW_DECISIONS.jsonl"
OCCURRENCE_INPUT = PROV / "EXPERT_REVIEW_OCCURRENCES.jsonl"
PDF = P / "build" / "core" / "openlogic-mr-core.pdf"
INPUTS = P / "build" / "core" / "INPUTS.json"

SCHEMA_SHA256 = "50e7fa407b62c711f92f8b93be591d3b4a6e1c4adb1386c398bb5f76844d9f90"
SCHEMA_BYTES = 10787
SOURCE_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
PDF_FILENAME = PDF.name
GENERATED_UTC = "2026-09-06T00:00:00Z"
DEFERRED_IDS = ["T009", "T013"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


PDF_SHA256 = sha(PDF)
input_rows = json.loads(INPUTS.read_text(encoding="utf-8"))["input_units"]
READER_UNITS = len(input_rows)
READER_LAST_UNIT = input_rows[-1]["unit_id"]
translated_unit_ids = sorted(
    {
        json.loads(line)["unit_id"]
        for line in OCCURRENCE_INPUT.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and json.loads(line).get("unit_id")
    }
)
SOURCE_UNITS = len(translated_unit_ids)
LAST_UNIT = translated_unit_ids[-1]
driver_names = {
    "sets.tex", "relations-complete.tex", "functions.tex",
    "size-of-sets-complete.tex", "arithmetization.tex", "infinite.tex",
    "syntax-and-semantics.tex",
}
COMPLETE_CHAPTERS = sum(Path(row["path"]).name in driver_names for row in input_rows)
PDF_PROFILE = f"{COMPLETE_CHAPTERS}-chapter cumulative reader through {READER_LAST_UNIT}"
RELEASE_TAG = f"development-through-{LAST_UNIT}"


def jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def write_text(path, text):
    Path(path).write_bytes(text.encode("utf-8"))


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def md(value):
    return str(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def span_locator(relative_path, unit_id, role, start, end, term, sense, context):
    relative_path = relative_path.replace("\\", "/")
    path = P / relative_path
    assert path.is_file(), path
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)
    assert 1 <= start <= end <= len(lines), (relative_path, start, end, len(lines))
    byte_start = sum(len(line) for line in lines[: start - 1])
    byte_end = sum(len(line) for line in lines[:end])
    excerpt = data[byte_start:byte_end].decode("utf-8").rstrip("\r\n")
    assert excerpt.strip(), (relative_path, start, end)
    return {
        "path": relative_path,
        "file_id": f"{unit_id}:{role}:{relative_path}",
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "line_span": {"status": "available", "start": start, "end": end},
        "byte_span": {
            "status": "available",
            "start": byte_start,
            "end_exclusive": byte_end,
        },
        "printed_page": None,
        "excerpt": excerpt,
        "term": term,
        "intended_sense": sense,
        "context": context,
    }


EDITION = {
    "edition_id": "openlogic-mr-Deva-IN",
    "language_tag": "mr-Deva-IN",
    "language_name": "Marathi",
    "script": "Deva",
    "territory": "IN",
    "locale": "mr-IN",
    "register_or_variant": "formal mathematical and philosophical didactic Marathi",
    "notation_profile": "frozen OpenLogic mathematical notation",
    "layer_type": "semantic_translation",
    "parent_semantic_edition_id": None,
}

CHAPTERS = {
    "1": "संच",
    "2": "संबंध",
    "3": "फलने",
    "4": "संचांचे आकारमान",
    "5": "अंकगणितीकरण",
    "6": "अनंत संच",
}


def reader_locator(legacy):
    pages = legacy.get("reader_pdf_pages") or []
    if not pages:
        return {
            "status": "pending",
            "reason": legacy.get("page_locator_precision")
            or "This occurrence has not yet been paginated in the coherent reader.",
        }
    return {
        "status": "available",
        "artifact_filename": PDF_FILENAME,
        "artifact_sha256": PDF_SHA256,
        "profile": PDF_PROFILE,
        "printed_page": legacy.get("reader_page_label"),
        "assembled_pdf_page": int(pages[0]),
        "provenance": (
            f"{legacy.get('page_locator_precision', 'current reader locator')}; "
            f"legacy reader scope: {legacy.get('reader_scope', 'not stated')}"
        ),
    }


def adapt_occurrence(legacy, evidence_ref):
    unit_id = legacy["unit_id"]
    section_number = legacy.get("section_number") or ""
    chapter = CHAPTERS.get(section_number.split(".", 1)[0])
    section_title = " ".join(
        value for value in [section_number, legacy.get("section_title")] if value
    ) or None
    sense = legacy["technical_sense"]
    granularity = legacy.get("occurrence_granularity", "legacy occurrence")

    if legacy["record_kind"] == "terminology_decision":
        source_match = re.fullmatch(r"(\d+)-(\d+)", legacy["source_lines"])
        target_match = re.fullmatch(r"(\d+)-(\d+)", legacy["target_lines"])
        assert source_match and target_match, legacy["occurrence_id"]
        semantic_id = f"{unit_id}-{legacy['aligned_block']}"
        source_context = (
            f"{granularity}; aligned block {legacy['aligned_block']}; "
            f"legacy occurrence {legacy['occurrence_id']}."
        )
        target_context = source_context
        source = span_locator(
            legacy["source_path"],
            unit_id,
            "source",
            int(source_match.group(1)),
            int(source_match.group(2)),
            legacy["source_term"],
            sense,
            source_context,
        )
        target = span_locator(
            legacy["target_path"],
            unit_id,
            "target",
            int(target_match.group(1)),
            int(target_match.group(2)),
            legacy["chosen_rendering"],
            sense,
            target_context,
        )
    else:
        source_locations = legacy["source_locations"]
        target_locations = legacy["target_locations"]
        assert source_locations and target_locations
        primary_source = source_locations[0]
        primary_target = target_locations[0]
        semantic_id = f"{unit_id}:source-issue:{legacy['decision_id']}"
        additional_sources = source_locations[1:]
        source_context = (
            f"{granularity}; legacy occurrence {legacy['occurrence_id']}. "
            f"The primary contiguous schema locator is shown here. "
            f"All legacy source ranges: {json.dumps(source_locations, ensure_ascii=False)}"
        )
        target_context = (
            f"{granularity}; legacy occurrence {legacy['occurrence_id']}. "
            f"All legacy target ranges: {json.dumps(target_locations, ensure_ascii=False)}"
        )
        if additional_sources:
            source_context += " Additional comparison files remain explicit in the context."
        source = span_locator(
            primary_source["path"],
            unit_id,
            "source",
            int(primary_source["line_start"]),
            int(primary_source["line_end"]),
            legacy["source_term"],
            sense,
            source_context,
        )
        target = span_locator(
            primary_target["path"],
            unit_id,
            "target",
            int(primary_target["line_start"]),
            int(primary_target["line_end"]),
            legacy["chosen_rendering"],
            sense,
            target_context,
        )

    return {
        "occurrence_id": legacy["occurrence_id"],
        "unit_id": unit_id,
        "semantic_unit_id": semantic_id,
        "part_title": None,
        "chapter_title": chapter,
        "section_title": section_title,
        "source": source,
        "target": target,
        "reader_locator": reader_locator(legacy),
        "evidence_refs": [evidence_ref],
    }


def term_authorities(decision_id, legacy):
    authorities = []
    for item in legacy["authorities_actually_checked"]:
        passage_sha = item.get("page_image_sha256") or item.get("observation_sha256")
        assert passage_sha
        citation = f"{item.get('title') or item.get('source_id')}. {item['url']}"
        if item.get("printed_page") is not None:
            citation += f"; printed page {item['printed_page']}"
        note = item.get("verification") or "Consulted for this decision."
        if item.get("limitation"):
            note += f" Limitation: {item['limitation']}"
        authorities.append(
            {
                "authority_id": item["passage_id"],
                "citation": citation,
                "passage_id": item["passage_id"],
                "locator": item["locator"],
                "source_sha256": (
                    item["source_sha256"].lower() if item.get("source_sha256") else None
                ),
                "passage_sha256": passage_sha.lower(),
                "status": "checked_supports",
                "note": note,
            }
        )
    if not authorities:
        authorities.append(
            {
                "authority_id": f"{decision_id}-NO-EXTERNAL-AUTHORITY",
                "citation": "No external Marathi authority is recorded for this exact label.",
                "passage_id": None,
                "locator": None,
                "source_sha256": None,
                "passage_sha256": None,
                "status": "not_checked",
                "note": legacy["authority_status"],
            }
        )
    return authorities


def source_issue_authority(decision_id, legacy, occurrence):
    source = occurrence["source"]
    passage_sha = hashlib.sha256(source["excerpt"].encode("utf-8")).hexdigest()
    line_span = source["line_span"]
    return [
        {
            "authority_id": f"{decision_id}-SOURCE-COMPARISON",
            "citation": (
                "Frozen OpenLogic English source and aligned Marathi target comparison "
                f"for {decision_id}."
            ),
            "passage_id": f"{decision_id}-SOURCE-PASSAGE",
            "locator": (
                f"{source['path']}:{line_span['start']}-{line_span['end']}"
            ),
            "source_sha256": source["file_sha256"],
            "passage_sha256": passage_sha,
            "status": "checked_context_only",
            "note": (
                json.dumps(legacy["authority_or_audit"], ensure_ascii=False, sort_keys=True)
                if isinstance(legacy["authority_or_audit"], dict)
                else legacy["authority_or_audit"]
            ),
        }
    ]


OUT.mkdir(parents=True, exist_ok=True)
assert SCHEMA_PATH.stat().st_size == SCHEMA_BYTES
assert sha(SCHEMA_PATH) == SCHEMA_SHA256
assert sha(PDF) == PDF_SHA256

legacy_decisions = jsonl(DECISION_INPUT)
legacy_occurrences = jsonl(OCCURRENCE_INPUT)
legacy_decision_ids = [item.get("term_id") or item.get("issue_id") for item in legacy_decisions]
assert len(legacy_decision_ids) == len(set(legacy_decision_ids))
assert len({item["occurrence_id"] for item in legacy_occurrences}) == len(legacy_occurrences)

occurrences_by_decision = defaultdict(list)
for item in legacy_occurrences:
    occurrences_by_decision[item["decision_id"]].append(item)

input_occurrence_ref = {
    "path_or_uri": "provenance/EXPERT_REVIEW_OCCURRENCES.jsonl",
    "bytes": OCCURRENCE_INPUT.stat().st_size,
    "sha256": sha(OCCURRENCE_INPUT),
    "version_or_ref": PDF_PROFILE,
}

confidence_rank = {"low": 0, "medium": 1, "high": 2}
priority_map = {"routine": "low", "medium": "normal", "high": "high"}
priority_rank = {"low": 0, "normal": 1, "high": 2, "urgent": 3}
canonical_decisions = []

for legacy in legacy_decisions:
    decision_id = legacy.get("term_id") or legacy.get("issue_id")
    old_occurrences = occurrences_by_decision[decision_id]
    if not old_occurrences:
        assert decision_id in DEFERRED_IDS
        continue
    occurrences = [adapt_occurrence(item, input_occurrence_ref) for item in old_occurrences]
    confidence = min(
        (item["confidence"] for item in old_occurrences),
        key=lambda value: confidence_rank[value],
    )
    review_priority = max(
        (priority_map[item["review_priority"]] for item in old_occurrences),
        key=lambda value: priority_rank[value],
    )

    if legacy["record_kind"] == "terminology_decision":
        source_term = legacy["english"]
        intended_sense = legacy["rationale"]
        chosen_rendering = legacy["chosen_marathi"]
        rationale = legacy["rationale"]
        authorities = term_authorities(decision_id, legacy)
        alternatives = [
            {
                "rendering": value,
                "disposition": "viable_alternative",
                "reason": (
                    "Recorded in the legacy decision ledger for expert comparison; "
                    "the current rationale favors the chosen rendering."
                ),
            }
            for value in legacy["alternatives_considered"]
        ]
        recording_mode = (
            "retrospective"
            if "retrospective" in legacy["rationale_provenance"].lower()
            else "contemporaneous"
        )
        confidence_reason = (
            f"Legacy status: {legacy['status_and_uncertainty']}. "
            f"Authority status: {legacy['authority_status']}"
        )
        recorded_utc = None
        record_kind = "terminology"
    else:
        source_term = legacy.get("classification") or f"source correction or observation {decision_id}"
        intended_sense = legacy["finding"]
        chosen_rendering = legacy["chosen_action"]
        rationale = (
            f"{legacy['finding']} Chosen action: {legacy['chosen_action']}"
        )
        authorities = source_issue_authority(decision_id, legacy, occurrences[0])
        alternatives = [
            {
                "rendering": value,
                "disposition": "rejected",
                "reason": "Not chosen; the source finding and recorded action control.",
            }
            for value in legacy["alternatives_considered"]
        ]
        recording_mode = "contemporaneous"
        confidence_reason = legacy["uncertainty"]
        recorded_utc = None
        record_kind = "source_correction"

    decision = {
        "decision_id": decision_id,
        "supersedes": [],
        "record_kind": record_kind,
        "recording_mode": recording_mode,
        "edition": dict(EDITION),
        "source_term_or_construction": source_term,
        "intended_sense": intended_sense,
        "chosen_rendering": chosen_rendering,
        "rationale": rationale,
        "authorities_checked": authorities,
        "alternatives": alternatives,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "provisional": any(item["provisional"] for item in old_occurrences),
        "review_priority": review_priority,
        "expert_review_useful": True,
        "expert_review_reason": (
            "Independent Marathi subject-matter review has not occurred; this "
            "reversible record gives the exact question and current locations."
        ),
        "please_double_check_question": old_occurrences[0][
            "please_double_check_question"
        ],
        "occurrences": occurrences,
    }
    if recorded_utc:
        decision["recorded_utc"] = recorded_utc
    canonical_decisions.append(decision)

assert len(canonical_decisions) == len(legacy_decisions) - len(DEFERRED_IDS)
assert sum(len(item["occurrences"]) for item in canonical_decisions) == len(legacy_occurrences)
assert [
    (item.get("term_id") or item.get("issue_id"))
    for item in legacy_decisions
    if not occurrences_by_decision[item.get("term_id") or item.get("issue_id")]
] == DEFERRED_IDS

canonical_count = len(canonical_decisions)
occurrence_count = len(legacy_occurrences)
remaining_units = 722 - SOURCE_UNITS

document = {
    "schema_version": "openlogic-translation-decisions/1.0.0",
    "edition_release": {
        "edition": dict(EDITION),
        "release_tag": RELEASE_TAG,
        "repository": "https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN",
        "doi": None,
        "source_revision": SOURCE_REVISION,
        "coverage_state": "partial",
        "source_units": SOURCE_UNITS,
        "reader_units": READER_UNITS,
    },
    "generated_utc": GENERATED_UTC,
    "generator": {
        "path_or_uri": "tools/build_translation_decisions.py",
        "bytes": Path(__file__).stat().st_size,
        "sha256": sha(__file__),
        "version_or_ref": PDF_PROFILE + " schema adapter",
    },
    "decisions": canonical_decisions,
}

decisions_path = OUT / "DECISIONS.json"
write_json(decisions_path, document)

start_lines = [
    "# Start here: Marathi translation decisions",
    "",
    "This bundle is the expert-review entry point for the current Marathi ",
    f"OpenLogic translation through {LAST_UNIT}. It covers {SOURCE_UNITS}/722 source units, ",
    f"{COMPLETE_CHAPTERS} complete chapters, {canonical_count} applied decisions and ",
    f"{occurrence_count:,} exact current occurrences. The remaining {remaining_units} units are untranslated.",
    f"The paginated {COMPLETE_CHAPTERS}-chapter reader ends at {READER_LAST_UNIT}; later translated units use pending PDF locators.",
    "",
    "No independent human or native-speaker review is claimed. Every choice remains ",
    "reversible, and a review question is a request for useful evidence rather than ",
    "a publication or completion hold.",
    "",
    "## Files",
    "",
    "- `TRANSLATION_DECISIONS_FULL.md` is the readable complete applied-decision index.",
    "- `PRIORITY_REVIEW.md` contains only urgent/high review items and their occurrences.",
    f"- `DECISION_OCCURRENCES.csv` has one UTF-8 row for each of {occurrence_count:,} occurrences.",
    "- `DECISIONS.json` is the canonical machine record validated against the shared schema.",
    "- `translation-decision.schema.json` is the exact frozen shared schema.",
    "- `TRANSLATION_DECISION_QA.json` records validation, counts and hashes.",
    "",
    "The PDF page field is the current assembled-reader page or range. Unknown pages ",
    "must use schema status `pending`; none were guessed in this checkpoint. Source ",
    "and target locators contain current file SHA-256 values, exact line spans, byte ",
    "spans and excerpts. Two prospective terminology records (`T009`, `T013`) ",
    "remain in the backward-compatible legacy ledger but are deferred ",
    f"from `DECISIONS.json` because they have no occurrence in the current {SOURCE_UNITS}-unit ",
    "coverage and the shared schema requires at least one real occurrence per decision.",
    "",
    "The full source-aligned Marathi edition remains the controlling deliverable. This ",
    "review bundle does not define a second regional or notation variant.",
]
write_text(OUT / "START_HERE.md", "\n".join(start_lines) + "\n")

full_lines = [
    "# Marathi OpenLogic translation decisions — full applied index",
    "",
    f"Coverage: {SOURCE_UNITS}/722 source units through {LAST_UNIT}; {canonical_count} applied decisions; {occurrence_count:,} occurrences.",
    "",
]
for decision in canonical_decisions:
    full_lines.extend(
        [
            f"## {md(decision['decision_id'])} — {md(decision['source_term_or_construction'])}",
            "",
            f"**Chosen rendering/action:** {md(decision['chosen_rendering'])}",
            "",
            f"**Kind:** `{decision['record_kind']}` · **recording:** `{decision['recording_mode']}` · "
            f"**confidence:** `{decision['confidence']}` · **priority:** `{decision['review_priority']}` · "
            f"**provisional:** `{str(decision['provisional']).lower()}`",
            "",
            f"**Intended sense:** {md(decision['intended_sense'])}",
            "",
            f"**Rationale:** {md(decision['rationale'])}",
            "",
            "**Authorities actually checked:**",
            "",
        ]
    )
    for authority in decision["authorities_checked"]:
        full_lines.append(
            f"- `{md(authority['authority_id'])}` — {md(authority['citation'])} "
            f"(`{authority['status']}`): {md(authority['note'])}"
        )
    full_lines.extend(["", "**Alternatives:**", ""])
    for alternative in decision["alternatives"]:
        full_lines.append(
            f"- {md(alternative['rendering'])} — `{alternative['disposition']}`: "
            f"{md(alternative['reason'])}"
        )
    full_lines.extend(
        [
            "",
            f"**Please double-check:** {md(decision['please_double_check_question'])}",
            "",
            "| Occurrence | Unit | Section | Source locator | Target locator | Reader page |",
            "|---|---|---|---|---|---|",
        ]
    )
    for occurrence in decision["occurrences"]:
        source = occurrence["source"]
        target = occurrence["target"]
        reader = occurrence["reader_locator"]
        reader_page = reader.get("printed_page") or reader["status"]
        full_lines.append(
            f"| `{md(occurrence['occurrence_id'])}` | `{occurrence['unit_id']}` | "
            f"{md(occurrence.get('section_title') or '')} | "
            f"`{md(source['path'])}:{source['line_span']['start']}-{source['line_span']['end']}` | "
            f"`{md(target['path'])}:{target['line_span']['start']}-{target['line_span']['end']}` | "
            f"{md(reader_page)} |"
        )
    full_lines.append("")

full_lines.extend(
    [
        "## Deferred prospective decisions",
        "",
        "The following legacy decisions have no occurrence in the current coverage and are not ",
        "fabricated into the canonical record: `T009`, `T011`, `T012`, `T013`. They remain ",
        "available in `../EXPERT_REVIEW_DECISIONS.jsonl` until translated source creates a real locator.",
        "",
    ]
)
write_text(OUT / "TRANSLATION_DECISIONS_FULL.md", "\n".join(full_lines))

priority_decisions = [
    item for item in canonical_decisions if item["review_priority"] in {"urgent", "high"}
]
priority_occurrences = [
    occurrence
    for decision in priority_decisions
    for occurrence in decision["occurrences"]
]
priority_lines = [
    "# Marathi OpenLogic priority review",
    "",
    f"This view contains {len(priority_decisions)} urgent/high decisions and ",
    f"{len(priority_occurrences)} current occurrences. Normal and low items remain in the full index.",
    "",
]
for decision in priority_decisions:
    priority_lines.extend(
        [
            f"## {md(decision['decision_id'])} — {md(decision['source_term_or_construction'])} → {md(decision['chosen_rendering'])}",
            "",
            f"**Priority:** `{decision['review_priority']}` · **confidence:** `{decision['confidence']}`",
            "",
            f"**Why:** {md(decision['confidence_reason'])}",
            "",
            f"**Please double-check:** {md(decision['please_double_check_question'])}",
            "",
            "| Occurrence | Unit | Section | Source line | Target line | PDF page |",
            "|---|---|---|---|---|---|",
        ]
    )
    for occurrence in decision["occurrences"]:
        source = occurrence["source"]
        target = occurrence["target"]
        reader = occurrence["reader_locator"]
        priority_lines.append(
            f"| `{md(occurrence['occurrence_id'])}` | `{occurrence['unit_id']}` | "
            f"{md(occurrence.get('section_title') or '')} | "
            f"{source['line_span']['start']}-{source['line_span']['end']} | "
            f"{target['line_span']['start']}-{target['line_span']['end']} | "
            f"{md(reader.get('printed_page') or reader['status'])} |"
        )
    priority_lines.append("")
write_text(OUT / "PRIORITY_REVIEW.md", "\n".join(priority_lines))

csv_path = OUT / "DECISION_OCCURRENCES.csv"
csv_fields = [
    "decision_id",
    "occurrence_id",
    "record_kind",
    "source_term_or_construction",
    "intended_sense",
    "chosen_rendering",
    "confidence",
    "provisional",
    "review_priority",
    "please_double_check_question",
    "unit_id",
    "semantic_unit_id",
    "chapter_title",
    "section_title",
    "source_path",
    "source_file_sha256",
    "source_line_start",
    "source_line_end",
    "source_byte_start",
    "source_byte_end_exclusive",
    "source_excerpt",
    "target_path",
    "target_file_sha256",
    "target_line_start",
    "target_line_end",
    "target_byte_start",
    "target_byte_end_exclusive",
    "target_excerpt",
    "reader_status",
    "reader_artifact_filename",
    "reader_artifact_sha256",
    "reader_page_label",
    "reader_assembled_pdf_page",
    "reader_locator_provenance",
    "evidence_path_or_uri",
    "evidence_sha256",
]
with csv_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=csv_fields, lineterminator="\n")
    writer.writeheader()
    for decision in canonical_decisions:
        for occurrence in decision["occurrences"]:
            source = occurrence["source"]
            target = occurrence["target"]
            reader = occurrence["reader_locator"]
            evidence = occurrence["evidence_refs"][0]
            writer.writerow(
                {
                    "decision_id": decision["decision_id"],
                    "occurrence_id": occurrence["occurrence_id"],
                    "record_kind": decision["record_kind"],
                    "source_term_or_construction": decision["source_term_or_construction"],
                    "intended_sense": decision["intended_sense"],
                    "chosen_rendering": decision["chosen_rendering"],
                    "confidence": decision["confidence"],
                    "provisional": str(decision["provisional"]).lower(),
                    "review_priority": decision["review_priority"],
                    "please_double_check_question": decision["please_double_check_question"],
                    "unit_id": occurrence["unit_id"],
                    "semantic_unit_id": occurrence["semantic_unit_id"],
                    "chapter_title": occurrence.get("chapter_title"),
                    "section_title": occurrence.get("section_title"),
                    "source_path": source["path"],
                    "source_file_sha256": source["file_sha256"],
                    "source_line_start": source["line_span"]["start"],
                    "source_line_end": source["line_span"]["end"],
                    "source_byte_start": source["byte_span"]["start"],
                    "source_byte_end_exclusive": source["byte_span"]["end_exclusive"],
                    "source_excerpt": source["excerpt"],
                    "target_path": target["path"],
                    "target_file_sha256": target["file_sha256"],
                    "target_line_start": target["line_span"]["start"],
                    "target_line_end": target["line_span"]["end"],
                    "target_byte_start": target["byte_span"]["start"],
                    "target_byte_end_exclusive": target["byte_span"]["end_exclusive"],
                    "target_excerpt": target["excerpt"],
                    "reader_status": reader["status"],
                    "reader_artifact_filename": reader.get("artifact_filename"),
                    "reader_artifact_sha256": reader.get("artifact_sha256"),
                    "reader_page_label": reader.get("printed_page"),
                    "reader_assembled_pdf_page": reader.get("assembled_pdf_page"),
                    "reader_locator_provenance": reader.get("provenance") or reader.get("reason"),
                    "evidence_path_or_uri": evidence["path_or_uri"],
                    "evidence_sha256": evidence["sha256"],
                }
            )

schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())
errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
assert not errors, "\n".join(
    f"{list(error.path)}: {error.message}" for error in errors[:20]
)

all_occurrences = [
    occurrence
    for decision in canonical_decisions
    for occurrence in decision["occurrences"]
]
for occurrence in all_occurrences:
    for role in ["source", "target"]:
        locator = occurrence[role]
        path = P / locator["path"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == locator["file_sha256"]
        start = locator["byte_span"]["start"]
        end = locator["byte_span"]["end_exclusive"]
        assert data[start:end].decode("utf-8").rstrip("\r\n") == locator["excerpt"]
    assert occurrence["evidence_refs"] == [input_occurrence_ref]

with csv_path.open("r", encoding="utf-8", newline="") as handle:
    csv_rows = list(csv.DictReader(handle))
assert len(csv_rows) == occurrence_count
assert len({row["occurrence_id"] for row in csv_rows}) == occurrence_count

priority_counts = Counter(
    decision["review_priority"]
    for decision in canonical_decisions
    for _ in decision["occurrences"]
)
assert sum(priority_counts.values()) == occurrence_count
assert len(priority_occurrences) == priority_counts.get("high", 0)

artifact_names = [
    "START_HERE.md",
    "TRANSLATION_DECISIONS_FULL.md",
    "PRIORITY_REVIEW.md",
    "DECISION_OCCURRENCES.csv",
    "DECISIONS.json",
    "translation-decision.schema.json",
]
qa = {
    "schema": "openlogic-translation-decision-qa/1",
    "generated_utc": GENERATED_UTC,
    "result": "passed",
    "canonical_schema": {
        "source": (
            "https://raw.githubusercontent.com/KokunoYumeto/OpenLogic-translations/"
            "811091d54be4989918864732073279a588340e6f/catalogue/translation-decisions/"
            "translation-decision.schema.json"
        ),
        "bytes": SCHEMA_BYTES,
        "sha256": SCHEMA_SHA256,
        "upstream_schema_qa_sha256": "7893e3f70105802478e07cd7f96620de234de1bfff2b2a5ef3627f7d950417b8",
        "upstream_valid_fixture_sha256": "0b12f85178d6a264edd59e78e4f7120c4c2fbe1fce718d97d0a4152d26092d2a",
    },
    "validation": {
        "draft": "2020-12",
        "library": f"jsonschema {importlib.metadata.version('jsonschema')}",
        "format_checker_enabled": True,
        "schema_errors": 0,
        "instance_errors": 0,
    },
    "coverage": {
        "source_units": SOURCE_UNITS,
        "total_source_units": 722,
        "complete_chapters": COMPLETE_CHAPTERS,
        "canonical_decisions_with_occurrences": canonical_count,
        "legacy_decisions_total": len(legacy_decisions),
        "legacy_prospective_decisions_deferred_without_fabricated_occurrences": DEFERRED_IDS,
        "occurrences": occurrence_count,
        "high_priority_occurrences": priority_counts.get("high", 0),
        "normal_priority_occurrences": priority_counts.get("normal", 0),
        "low_priority_occurrences": priority_counts.get("low", 0),
        "reader_locators_available": sum(
            occurrence["reader_locator"]["status"] == "available"
            for occurrence in all_occurrences
        ),
        "reader_locators_pending": sum(
            occurrence["reader_locator"]["status"] != "available"
            for occurrence in all_occurrences
        ),
    },
    "exactness_checks": {
        "globally_unique_occurrence_ids": True,
        "source_file_hashes_recomputed": occurrence_count,
        "target_file_hashes_recomputed": occurrence_count,
        "line_and_utf8_byte_spans_reproduced_exact_excerpts": 2 * occurrence_count,
        "csv_rows_equal_occurrences": True,
        "legacy_occurrence_ids_preserved": True,
        "unknown_pages_guessed": 0,
        "accepted_translation_prose_changed_by_adapter": False,
    },
    "inputs": {
        "provenance/EXPERT_REVIEW_DECISIONS.jsonl": {
            "bytes": DECISION_INPUT.stat().st_size,
            "sha256": sha(DECISION_INPUT),
            "records": len(legacy_decisions),
        },
        "provenance/EXPERT_REVIEW_OCCURRENCES.jsonl": {
            "bytes": OCCURRENCE_INPUT.stat().st_size,
            "sha256": sha(OCCURRENCE_INPUT),
            "records": occurrence_count,
        },
        "tools/build_translation_decisions.py": {
            "bytes": Path(__file__).stat().st_size,
            "sha256": sha(__file__),
        },
    },
    "outputs": {
        name: {
            "bytes": (OUT / name).stat().st_size,
            "sha256": sha(OUT / name),
        }
        for name in artifact_names
    },
    "review_policy": {
        "independent_human_review_claimed": False,
        "review_is_a_completion_hold": False,
        "regional_standard": "mr-Deva-IN / mr-IN",
        "speculative_variants_created": False,
    },
}
write_json(OUT / "TRANSLATION_DECISION_QA.json", qa)

print(
    json.dumps(
        {
            "result": "passed",
            "decisions": len(canonical_decisions),
            "legacy_deferred": DEFERRED_IDS,
            "occurrences": len(all_occurrences),
            "high_priority_occurrences": len(priority_occurrences),
            "schema_sha256": SCHEMA_SHA256,
            "decisions_json_bytes": decisions_path.stat().st_size,
            "decisions_json_sha256": sha(decisions_path),
            "qa_sha256": sha(OUT / "TRANSLATION_DECISION_QA.json"),
        },
        ensure_ascii=False,
        indent=2,
    )
)
