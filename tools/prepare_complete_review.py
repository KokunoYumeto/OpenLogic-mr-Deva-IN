"""Derive full-scope review locators from recorded consultation, without new claims."""
import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
PROV = BUILD / "release-provenance"
OUT = PROV / "translation-decisions"
OUT.mkdir(parents=True, exist_ok=True)
LOCALIZED = ROOT / "provenance/complete-v1.0/TERMINOLOGY_MR.jsonl"
SCHEMA = ROOT / "provenance/translation-decisions/translation-decision.schema.json"
SCHEMA_HASH = "50e7fa407b62c711f92f8b93be591d3b4a6e1c4adb1386c398bb5f76844d9f90"
MODELS = "OpenAI Codex — GPT-5.6 Sol आणि GPT-6 Sol, दोन्ही Ultra effort."

def digest(data):
    return hashlib.sha256(data).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def write_rows(path, value):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in value), encoding="utf-8")

def scrub(value):
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()
                if k not in {"local_path", "page_image", "observation_file", "ocr_path"}}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str) and re.match(r"^[A-Za-z]:[\\/]", value):
        return "[स्थानिक संशोधन-पथ वगळला]"
    return value

parser = argparse.ArgumentParser()
parser.add_argument("--state-dir", type=Path)
args = parser.parse_args()
if args.state_dir:
    issue_history = []
    for path in sorted(args.state_dir.glob("SOURCE_ISSUES-B*.json")):
        report = json.loads(path.read_text(encoding="utf-8-sig"))
        for issue in report.get("issues", []):
            issue_history.append({"batch_record": path.name, "issue": scrub(issue)})
    write_rows(PROV / "SOURCE_ISSUES.jsonl", issue_history)

terms = rows(PROV / "TERM_DECISIONS.jsonl")
segments = rows(PROV / "SEGMENT_CANON_USE.jsonl")
manifest = {row["unit_id"]: row for row in rows(PROV / "SOURCE_MANIFEST.jsonl")}
passages = {row["passage_id"]: row for row in rows(PROV / "CANON_PASSAGES.jsonl")}
sources = {row["source_id"]: row for row in rows(PROV / "CANON_SOURCES.jsonl")}
localized = {row["term_id"]: row for row in rows(LOCALIZED)}
assert len(terms) == 638 and len(manifest) == 722
assert set(localized) <= {row["term_id"] for row in terms}
assert digest(SCHEMA.read_bytes()) == SCHEMA_HASH
schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
(OUT / SCHEMA.name).write_bytes(SCHEMA.read_bytes())
by_term = defaultdict(list)
for segment in segments:
    for term in dict.fromkeys(segment["unit_term_decision_index"]):
        by_term[term].append(segment)
assert set(by_term) == {row["term_id"] for row in terms}

cache = {}
def blocks(path):
    if path not in cache:
        data = (ROOT / path).read_bytes()
        text = data.decode("utf-8")
        result, position = [], 0
        for block in re.split(r"\n\s*\n", text.strip()):
            start = text.find(block, position)
            assert start >= 0
            end = start + len(block)
            result.append((text.count("\n", 0, start) + 1,
                           text.count("\n", 0, end) + 1, digest(block.encode("utf-8"))))
            position = end
        cache[path] = (data, result)
    return cache[path]

def locator(path, unit, start, end, term, sense, context):
    data, _ = blocks(path)
    lines = data.splitlines(keepends=True)
    assert 1 <= start <= end <= len(lines), (path, start, end)
    byte_start = sum(map(len, lines[:start - 1]))
    byte_end = sum(map(len, lines[:end]))
    excerpt = data[byte_start:byte_end].decode("utf-8").rstrip("\r\n")
    assert excerpt.strip()
    return {"path": path, "file_id": f"{unit}:{path}", "file_sha256": digest(data),
            "line_span": {"status": "available", "start": start, "end": end},
            "byte_span": {"status": "available", "start": byte_start, "end_exclusive": byte_end},
            "printed_page": None, "excerpt": excerpt, "term": term,
            "intended_sense": sense, "context": context}

edition = {"edition_id": "openlogic-mr-Deva-IN", "language_tag": "mr-Deva-IN",
           "language_name": "मराठी", "script": "Deva", "territory": "IN", "locale": "mr-IN",
           "register_or_variant": "गणित व तत्त्वज्ञानाचे औपचारिक अध्यापनपर मराठी",
           "notation_profile": "गोठवलेल्या OpenLogic मधील गणितीय चिन्हे",
           "layer_type": "semantic_translation", "parent_semantic_edition_id": None}
pending_reader = {"status": "pending", "reason": "अंतिम स्वच्छ PDF शी पृष्ठ-निर्देश जोडणे बाकी; पृष्ठाचा अंदाज दिलेला नाही."}
decisions, occurrences, canonical, full_md, priority_md = [], [], [], [], []
ledger_ref = {"path_or_uri": "provenance/SEGMENT_CANON_USE.jsonl",
              "sha256": digest((PROV / "SEGMENT_CANON_USE.jsonl").read_bytes())}
for term in terms:
    tid = term["term_id"]
    translation = localized.get(tid, {})
    reason = translation.get("reason_mr", term["reason"])
    question = translation.get("review_question_mr") or (
        f"दिलेल्या औपचारिक संदर्भात ‘{term['marathi']}’ हा शब्दप्रयोग ठेवावा का? "
        "नमूद तांत्रिक अर्थ आणि पुराव्याच्या मर्यादा योग्य आहेत का? मराठी प्रामाण्यस्रोत द्या."
    )
    if term.get("review_question") and not translation.get("review_question_mr"):
        question = term["review_question"]
    authority_rows = []
    for pid in term.get("passages", []):
        passage = passages[pid]
        source = sources[passage["source_id"]]
        authority_rows.append({
            "authority_id": passage["source_id"], "citation": source.get("title", passage["source_id"]),
            "passage_id": pid, "locator": passage.get("locator") or f"PDF पृष्ठ {passage.get('pdf_page_1based')}",
            "source_sha256": passage.get("source_sha256") or source.get("sha256"),
            "passage_sha256": digest(json.dumps(passage, ensure_ascii=False, sort_keys=True).encode("utf-8")),
            "status": "checked_context_only",
            "note": "प्रत्यक्ष सल्लामसलतीची भूमिका मूळ निर्णयात नमूद आहे. येथे passage_sha256 हा प्रकाशित CANON_PASSAGES नोंदीचा हॅश आहे; पूर्ण PDF किंवा पृष्ठ-प्रतिमेचा हॅश नाही. नेमका शब्दप्रयोग प्रमाणित असल्याचा अतिरिक्त दावा नाही.",
        })
    if not authority_rows:
        authority_rows = [{"authority_id": "not-checked", "citation": "नेमक्या मराठी संज्ञेसाठी बाह्य प्रामाण्यस्रोत नाही",
                           "status": "not_checked", "note": "मूळ व्याख्येवर आधारित निर्णय; स्रोत पाहिल्याचा नवा दावा नाही."}]
    ids, canonical_occurrences = [], []
    for segment in by_term[tid]:
        unit = segment["unit_id"]
        source_path = "upstream/" + segment["source_path"].replace("\\", "/")
        target_path = segment["translation_path"].replace("\\", "/")
        source_data, source_blocks = blocks(source_path)
        target_data, target_blocks = blocks(target_path)
        assert digest(source_data) == segment["source_unit_sha256"] == manifest[unit]["source_sha256"]
        assert digest(target_data) == segment["translation_unit_sha256"]
        index = segment["block_index"] - 1
        source_span, target_span = source_blocks[index], target_blocks[index]
        assert source_span[2] == segment["source_segment_sha256"], segment["segment_id"]
        assert target_span[2] == segment["translation_segment_sha256"], segment["segment_id"]
        choice = segment.get("choice_line_spans", {}).get(tid)
        source_lines = choice["source"] if choice else source_span[:2]
        target_lines = choice["target"] if choice else target_span[:2]
        precision = "नोंदवलेल्या निर्णय-संबंधित ओळी; वेगवेगळ्या निवडींच्या ओळी एकमेकांवर येऊ शकतात" if choice else "एककातील शब्दनिर्णय-सूचकांकाने जोडलेला संदर्भखंड; अक्षरशः शब्दाची प्रत्येक आस्थिति असल्याचा दावा नाही"
        oid = f"{tid}-{segment['segment_id']}"
        ids.append(oid)
        source = locator(source_path, unit, *source_lines, term["english"], reason, precision)
        target = locator(target_path, unit, *target_lines, term["marathi"], reason, precision)
        canonical_occurrences.append({"occurrence_id": oid, "unit_id": unit,
            "semantic_unit_id": segment["segment_id"], "source": source, "target": target,
            "reader_locator": pending_reader, "evidence_refs": [ledger_ref]})
        occurrences.append({"schema": "openlogic-expert-review-occurrence/1", "occurrence_id": oid,
            "decision_id": tid, "record_kind": "terminology_decision", "unit_id": unit,
            "aligned_block": f"B{segment['block_index']:03d}", "source_path": source_path,
            "source_lines": f"{source_lines[0]}-{source_lines[1]}", "target_path": target_path,
            "target_lines": f"{target_lines[0]}-{target_lines[1]}", "choice_locator_precision": precision,
            "chosen_rendering": term["marathi"], "rationale": reason,
            "please_double_check_question": question, "script": "Deva", "locale": "mr-IN",
            "reader_pdf_sha256": None, "reader_pdf_pages": [], "reader_page_label": None,
            "page_locator_precision": "unit not yet paginated"})
    confidence = "low" if "sparse" in term.get("status", "") else "medium"
    priority = "high" if confidence == "low" else "normal"
    alternatives = [{"rendering": value, "disposition": "viable_alternative",
                     "reason": "मूळ निर्णयात नोंदवलेला पर्याय; आपोआप स्वीकारलेला नाही."}
                    for value in term.get("alternatives", [])]
    canonical.append({"decision_id": tid, "record_kind": "terminology",
        "recording_mode": "retrospective" if int(tid[1:]) <= 44 else "derived",
        "edition": edition, "source_term_or_construction": term["english"], "intended_sense": reason,
        "chosen_rendering": term["marathi"], "rationale": reason, "authorities_checked": authority_rows,
        "alternatives": alternatives, "confidence": confidence,
        "confidence_reason": "हा मूळ निर्णयातील पुराव्याच्या मर्यादांवर आधारित प्राथमिक पुनरावलोकन-सूचक आहे; स्वतंत्र तज्ज्ञ स्वीकृतीचा दावा नाही.",
        "provisional": True, "review_priority": priority, "expert_review_useful": True,
        "expert_review_reason": "शब्दरूप आणि तांत्रिक अर्थ दुरुस्तीसाठी खुले आहेत.",
        "please_double_check_question": question, "occurrences": canonical_occurrences})
    decisions.append({"schema": "openlogic-expert-review-decision/1", "record_kind": "terminology_decision",
        "term_id": tid, "english": term["english"], "chosen_marathi": term["marathi"],
        "rationale": reason, "precise_review_question": question, "occurrence_ids": ids,
        "open_to_correction": True, "historical_decision": term})
    item = [f"## {tid} — {term['marathi']}", "", f"मूळ संज्ञा: {term['english']}", "", reason, "", question, "",
            "पुरावा-निर्देश: " + ", ".join(term.get("passages", [])), "",
            f"संदर्भखंडांची संख्या: {len(ids)}. अचूक ओळी CSV/JSON मध्ये आहेत.", ""]
    full_md.extend(item)
    if priority == "high":
        priority_md.extend(item)

assert len(occurrences) == len({row["occurrence_id"] for row in occurrences})
assert len(occurrences) == sum(len(set(row["unit_term_decision_index"])) for row in segments)
assert {row["unit_id"] for row in occurrences} == set(manifest)
write_rows(PROV / "EXPERT_REVIEW_DECISIONS.jsonl", decisions)
write_rows(PROV / "EXPERT_REVIEW_OCCURRENCES.jsonl", occurrences)
with (PROV / "EXPERT_REVIEW_OCCURRENCES.csv").open("w", encoding="utf-8", newline="") as stream:
    fields = ["occurrence_id", "decision_id", "unit_id", "source_path", "source_lines", "target_path", "target_lines", "chosen_rendering", "choice_locator_precision"]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(occurrences)
release = {"release_tag": "complete-v1.0", "edition": edition,
           "repository": "https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN",
           "source_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
           "coverage_state": "audit_needed", "source_units": 722, "reader_units": 722}
register = {"schema_version": "openlogic-translation-decisions/1.0.0",
            "edition_release": release, "decisions": canonical}
errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(register))
assert not errors, [(list(error.path), error.message) for error in errors[:3]]
write_json(OUT / "DECISIONS.json", register)
missing = [term["term_id"] for term in terms if term["term_id"] not in localized
           or term.get("review_question") and not localized[term["term_id"]].get("review_question_mr")]
notice = ("# मराठी भाषांतरातील शब्दनिर्णय\n\n" + MODELS + "\n\n"
          f"सर्व 722 स्रोत-एककांच्या नोंदवलेल्या सल्लामसलतीवरून {len(occurrences):,} संदर्भ-निर्देश तयार केले आहेत. "
          "ते प्रत्येक शब्दाच्या अक्षरशः वापराची किंवा स्वतंत्र तज्ज्ञ परीक्षणाची प्रमाणपत्रे नाहीत. "
          "ऐतिहासिक अधिक तपशीलवार पुनरावलोकन 281 एकके आणि 14,221 नोंदींपुरते आहे.\n\n"
          f"मराठी कारणे तयार: {len(localized)}/638. अंतिम PDF पृष्ठ-निर्देश आणि स्रोतदुरुस्तींची सामायिक योजना जोडणे बाकी आहे. "
          "ही विकासावस्थेतील नोंद आहे; अंतिम प्रकाशनाची स्वीकृती नाही.\n\n"
          "[पूर्ण सूची](TRANSLATION_DECISIONS_FULL.md), [प्राधान्याने पाहायचे निर्णय](PRIORITY_REVIEW.md), "
          "[यंत्रवाचनीय नोंद](DECISIONS.json). मूलभूत ओळी ../EXPERT_REVIEW_OCCURRENCES.csv मध्ये आहेत.\n\n")
(OUT / "START_HERE.md").write_text(notice, encoding="utf-8")
(OUT / "TRANSLATION_DECISIONS_FULL.md").write_text(notice + "\n".join(full_md), encoding="utf-8")
(OUT / "PRIORITY_REVIEW.md").write_text(notice + "\n".join(priority_md), encoding="utf-8")
qa = {"schema": "openlogic-mr-complete-review-qa/1", "status": "incomplete",
      "source_units": 722, "term_decisions": 638, "context_occurrences": len(occurrences),
      "localized_term_decisions": len(localized), "missing_localization": missing,
      "historical_detailed_review_units": 281, "historical_detailed_review_occurrences": 14221,
      "schema_errors": 0, "schema_sha256": SCHEMA_HASH,
      "pending": ["final-reader-pages", "source-correction-schema-records", "remaining-Marathi-rationale-localization"]}
write_json(OUT / "TRANSLATION_DECISION_QA.json", qa)
print(json.dumps({key: qa[key] for key in ["status", "source_units", "term_decisions", "context_occurrences", "localized_term_decisions", "schema_errors"]}))
