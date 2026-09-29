"""Publish exact canonical review bytes without exceeding GitHub's file limit."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
SOURCE = BUILD / "release-provenance"
TARGET = ROOT / "provenance"
BACKUP = BUILD / "pre-final-provenance"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

qa = read(SOURCE / "translation-decisions/TRANSLATION_DECISION_QA.json")
assert qa["status"] == "ready" and qa["source_units"] == 722
assert not qa["missing_localization"] and not qa["pending"]
assert qa["localized_term_decisions"] == 638 and qa["localized_source_issues"] == 655
assert qa["schema_errors"] == 0
bindings = read(SOURCE / "REVIEW_READER_BINDING.json")
assert len(bindings["units"]) == 722
pdf_hash = sha(BUILD / "openlogic-mr-full.pdf")
receipt = read(BUILD / "TEX_BUILD_RECEIPT.json")
assert receipt["result"] == "built-log-clean" and receipt["pdf"]["sha256"] == pdf_hash

# Preserve pre-existing local bytes before synchronizing these exact surfaces.
# The raw JSON remains on disk for validators and in the published ZIPs.
copied = []
for path in sorted(SOURCE.rglob("*")):
    if not path.is_file():
        continue
    name = path.relative_to(SOURCE).as_posix()
    destination = TARGET / name
    old = BACKUP / name
    if destination.is_file() and not old.exists():
        old.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(destination, old)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
    assert sha(destination) == sha(path)
    copied.append({"path": "provenance/" + name, "sha256": sha(destination), "bytes": destination.stat().st_size})

canonical = TARGET / "translation-decisions/DECISIONS.json"
compressed = canonical.with_suffix(".json.gz")
compressed.write_bytes(gzip.compress(canonical.read_bytes(), compresslevel=9, mtime=0))
assert gzip.decompress(compressed.read_bytes()) == canonical.read_bytes()
assert compressed.stat().st_size < 95_000_000
index = TARGET / "translation-decisions/CANONICAL_JSON_DOWNLOAD.json"
data = {
    "schema": "openlogic-mr-canonical-json-download/1",
    "description_mr": "संपूर्ण प्रमाणित निर्णय-JSON ची अचूक संकुचित प्रत. ZIP संग्रहांत DECISIONS.json हेच असंकुचित नाव आहे.",
    "compression": "gzip", "compressed_file": compressed.name,
    "compressed_bytes": compressed.stat().st_size, "compressed_sha256": sha(compressed),
    "uncompressed_file": "DECISIONS.json", "uncompressed_bytes": canonical.stat().st_size,
    "uncompressed_sha256": sha(canonical), "reader_pdf_sha256": pdf_hash,
    "schema_sha256": sha(TARGET / "translation-decisions/translation-decision.schema.json"),
    "review_bundle_url": "https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/download/complete-v1.0/05-openlogic-mr-complete-review.zip",
    "source_bundle_url": "https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/download/complete-v1.0/03-openlogic-mr-complete-editable-sources.zip",
}
index.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
notes = TARGET / "translation-decisions/CANONICAL_JSON_DOWNLOAD.md"
notes.write_text(
    "# संपूर्ण निर्णय-JSON\n\n"
    "GitHub च्या एका फाइलच्या आकारमर्यादेमुळे संपूर्ण निर्णय-JSON येथे "
    "[`DECISIONS.json.gz`](DECISIONS.json.gz) या अचूक संकुचित रूपात आहे. "
    "ती उघडल्यावर `DECISIONS.json` ही प्रमाणित फाइल मिळते. "
    "[पुनरावलोकन-संग्रहात](" + data["review_bundle_url"] + ") आणि "
    "[संपूर्ण स्रोत-संग्रहात](" + data["source_bundle_url"] + ") तिची असंकुचित प्रत आहे.\n\n"
    "Python वापरून असंकुचित प्रत तयार करण्यासाठी या निर्देशिकेतून चालवा:\n\n"
    "```sh\npython -c \"import gzip,pathlib; pathlib.Path('DECISIONS.json').write_bytes(gzip.open('DECISIONS.json.gz','rb').read())\"\n```\n\n"
    "असंकुचित फाइलचा SHA-256: `" + sha(canonical) + "`. "
    "दोन्ही रूपांची ओळख व वाचक-PDF चा हॅश "
    "[`CANONICAL_JSON_DOWNLOAD.json`](CANONICAL_JSON_DOWNLOAD.json) मध्ये आहेत.\n",
    encoding="utf-8",
)
start_here = TARGET / "translation-decisions/START_HERE.md"
start_before = start_here.read_bytes()
text = start_before.decode("utf-8").replace("\r\n", "\n")
assert text.count("[यंत्रवाचनीय नोंद](DECISIONS.json)") == 1
text = text.replace("[यंत्रवाचनीय नोंद](DECISIONS.json)",
                    "[संपूर्ण यंत्रवाचनीय नोंद उघडण्याची पद्धत](CANONICAL_JSON_DOWNLOAD.md)")
start_here.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
report = {
    "schema": "openlogic-mr-git-review-packaging/1", "status": "passed",
    "reader_pdf_sha256": pdf_hash, "synchronized": copied,
    "compressed_canonical_sha256": sha(compressed),
    "uncompressed_canonical_sha256": sha(canonical),
    "previous_local_provenance_preserved": True,
    "raw_canonical_json_retained_for_validators_and_release_zips": True,
    "git_navigation_adaptation": {
        "path": "provenance/translation-decisions/START_HERE.md",
        "canonical_bundle_view_sha256": hashlib.sha256(start_before).hexdigest(),
        "git_view_sha256": sha(start_here),
        "reason_mr": "Git मधील यंत्रवाचनीय नोंदीचा दुवा अचूक संकुचित प्रत उघडण्याच्या मार्गदर्शकाकडे नेला; निर्णयांचा मजकूर बदललेला नाही.",
    },
}
(BUILD / "GIT_REVIEW_PACKAGE_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "passed", "synchronized_files": len(copied),
                  "canonical_gzip_bytes": compressed.stat().st_size,
                  "canonical_json_sha256": sha(canonical)}))
