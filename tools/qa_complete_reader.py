"""Static QA for the assembled full reader; TeX/PDF checks are separate."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
tex_path = BUILD / "openlogic-mr-full.tex"
tex = tex_path.read_text(encoding="utf-8")
receipt = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert hashlib.sha256(tex_path.read_bytes()).hexdigest() == receipt["reader_sha256"]
assert receipt["represented_unit_count"] == 722
assert len(receipt["core_unit_ids"]) == 639
assert len(receipt["proof_unit_ids"]) == 50
assert len(receipt["supplement_unit_ids"]) == 23
assert len(receipt["front_matter_and_root_unit_ids"]) == 3
assert len(receipt["represented_wrapper_unit_ids"]) == 7
assert tex.count(r"\begin{document}") == tex.count(r"\end{document}") == 1
assert tex.count(r"\chapter{") == receipt["chapters"] == 79
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", tex)) == receipt["sections"] == 612

# Ignore ordinary source comments; a percent preceded by a backslash is a glyph.
active = re.sub(r"(?<!\\)%[^\n]*", "", tex)
labels = re.findall(r"\\label\{([^{}]+)\}", active)
assert len(labels) == len(set(labels))
target = set(labels)
ref_groups = re.findall(r"\\(?:ref|eqref|pageref|autoref|cref|Cref)\{([^{}]+)\}", active)
refs = [key.strip() for group in ref_groups for key in group.split(",")]
unresolved = sorted(set(refs) - target)
external = sorted(set(re.findall(r"\\readerexternalref\{([^{}]+)\}", active)))
assert external == receipt["remaining_external_refs"]
assert not re.search(r"\\(?:olfileid|olsection|ollabel|olref|Olref|olimport|subfile|iftag|tagitem|tagrefs|tagblock|usetoken)\b", active)
assert "!!" not in active and not re.search(r"![A-Z]", active)
assert r"\lnotA" not in active

report = {
    "schema": "openlogic-mr-full-reader-static-qa/1",
    "reader_sha256": receipt["reader_sha256"],
    "represented_source_units": receipt["represented_unit_count"],
    "chapter_count": receipt["chapters"],
    "section_count": receipt["sections"],
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
