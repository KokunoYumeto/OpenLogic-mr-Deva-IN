"""Static QA for the assembled full reader; TeX/PDF checks are separate."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from complete_reader_notes import verify_reader_notes

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
tex_path = BUILD / "openlogic-mr-full.tex"
tex = tex_path.read_text(encoding="utf-8")
receipt = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert hashlib.sha256(tex_path.read_bytes()).hexdigest() == receipt["reader_sha256"]
manifest = {row["unit_id"]: row for row in (
    json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
)}
inputs_by_unit = {row["unit_id"]: row for row in receipt["input_units"]}
assert len(receipt["input_units"]) == len(inputs_by_unit) == 722
assert set(inputs_by_unit) == set(manifest)
for unit_id, row in inputs_by_unit.items():
    expected_path = manifest[unit_id]["source_path"]
    assert row["source_path"] == "upstream/" + expected_path
    assert row["target_path"] == "mr/" + expected_path
    assert hashlib.sha256((ROOT / row["source_path"]).read_bytes()).hexdigest() == row["source_sha256"] == manifest[unit_id]["source_sha256"]
    assert hashlib.sha256((ROOT / row["target_path"]).read_bytes()).hexdigest() == row["target_sha256"], f"Reader must be rebuilt after changes to {unit_id}"
assert receipt["represented_unit_count"] == 722
assert len(receipt["core_unit_ids"]) == 639
assert len(receipt["proof_unit_ids"]) == 50
assert len(receipt["supplement_unit_ids"]) == 23
assert len(receipt["front_matter_and_root_unit_ids"]) == 3
assert len(receipt["represented_wrapper_unit_ids"]) == 7
assert tex.count(r"\begin{document}") == tex.count(r"\end{document}") == 1
assert tex.count(r"\chapter{") == receipt["chapters"] == 79
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", tex)) == receipt["sections"] == 613
driver_qa = json.loads((BUILD / "DRIVER_EDITORIAL_QA.json").read_text(encoding="utf-8"))
reader_note_count = verify_reader_notes(ROOT, manifest, tex, json.loads((BUILD / "READER_NOTE_QA.json").read_text(encoding="utf-8")))
assert driver_qa["reader_sha256"] == receipt["reader_sha256"]
assert driver_qa["editorial_blocks"] == 44 and driver_qa["appended_blocks"] == 10
assert driver_qa["appended_units"] == ["OLP-0027", "OLP-0138", "OLP-0182", "OLP-0208", "OLP-0460", "OLP-0470", "OLP-0476", "OLP-0720", "OLP-0722"]

# Ignore ordinary source comments; a percent preceded by a backslash is a glyph.
active = re.sub(r"(?<!\\)%[^\n]*", "", tex)
labels = re.findall(r"\\label\{([^{}]+)\}", active)
assert len(labels) == len(set(labels))
target = set(labels)
ref_groups = re.findall(r"\\(?:ref|eqref|pageref|autoref|cref|Cref)\{([^{}]+)\}", active)
refs = [key.strip() for group in ref_groups for key in group.split(",")]
unresolved = sorted(set(refs) - target)
assert not unresolved, f"Unresolved internal reader references: {unresolved}"
external = sorted(set(re.findall(r"\\readerexternalref\{([^{}]+)\}", active)))
assert external == receipt["remaining_external_refs"]
assert not re.search(r"\\(?:olfileid|olsection|ollabel|olref|Olref|olimport|subfile|iftag|tagitem|tagrefs|tagblock|usetoken)\b", active)
assert "!!" not in active and not re.search(r"![A-Z]", active)
assert r"\lnotA" not in active

report = {
    "schema": "openlogic-mr-full-reader-static-qa/1",
    "reader_sha256": receipt["reader_sha256"],
    "represented_source_units": receipt["represented_unit_count"],
    "current_source_and_target_unit_hashes_verified": len(inputs_by_unit),
    "chapter_count": receipt["chapters"],
    "section_count": receipt["sections"],
    "source_driver_editorial_blocks": driver_qa["editorial_blocks"],
    "source_reader_notes": reader_note_count,
    "labels": len(labels),
    "reference_occurrences": len(refs),
    "unresolved_standard_reference_targets": unresolved,
    "explicit_external_reference_targets": external,
    "route_counts": {
        "core": len(receipt["core_unit_ids"]),
        "proof": len(receipt["proof_unit_ids"]),
        "supplement": len(receipt["supplement_unit_ids"]),
        "front_matter_root": len(receipt["front_matter_and_root_unit_ids"]),
        "wrapper": len(receipt["represented_wrapper_unit_ids"]),
    },
    "tex_compilation_verified": False,
}
(BUILD / "STATIC_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
