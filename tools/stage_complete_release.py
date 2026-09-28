"""Stage and byte-check the complete Marathi reader release."""

import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
TAG = "complete-v1.0"
RELEASE = ROOT / "releases" / TAG
RELEASE.mkdir(parents=True, exist_ok=True)
FIXED_DATE = (2026, 9, 28, 0, 0, 0)
REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(path):
    return {"filename": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_zip(path, entries):
    assert len(entries) == len({name for name, _ in entries})
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, source in sorted(entries):
            data = source.read_bytes()
            info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == sorted(name for name, _ in entries)
        for name, source in entries:
            assert archive.read(name) == source.read_bytes(), name


def scan_private(entries):
    for name, source in entries:
        if source.suffix.lower() not in {".py", ".ps1", ".json", ".jsonl", ".md", ".tex", ".csv", ".html", ".txt"}:
            continue
        value = source.read_text(encoding="utf-8-sig")
        assert not re.search(r"[A-Za-z]:[\\/]+Users[\\/]", value, re.I), name
        assert "C:/interlanguage-task-state" not in value and "C:\\interlanguage-task-state" not in value, name
        assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+", value), name


tex_receipt = load(BUILD / "TEX_BUILD_RECEIPT.json")
inputs = load(BUILD / "INPUTS.json")
static_qa = load(BUILD / "STATIC_QA.json")
pdf_qa = load(BUILD / "PDF_QA.json")
html_qa = load(BUILD / "HTML_QA.json")
browser_qa = load(BUILD / "HTML_BROWSER_QA.json")
provenance_qa = load(BUILD / "PROVENANCE_QA.json")
diagram_receipt = load(BUILD / "HTML_DIAGRAM_RECEIPT.json")
assert tex_receipt["result"] == "built-log-clean" and len(tex_receipt["passes"]) == 3
assert tex_receipt["texInputSha256"] == inputs["reader_sha256"] == static_qa["reader_sha256"]
assert sha(BUILD / "openlogic-mr-full.tex") == inputs["reader_sha256"]
assert sha(BUILD / "openlogic-mr-full.pdf") == tex_receipt["pdf"]["sha256"]
assert static_qa["represented_source_units"] == 722 and not static_qa["unresolved_standard_reference_targets"]
assert pdf_qa["status"] == "ready" and pdf_qa["pdf_sha256"] == tex_receipt["pdf"]["sha256"]
assert pdf_qa["reader_sha256"] == inputs["reader_sha256"]
assert html_qa["result"] == "ready" and not html_qa["blockers"]
assert browser_qa["result"] == "passed"
assert provenance_qa["status"] == "passed" and provenance_qa["translated_units"] == 722
assert diagram_receipt["status"] == "final-source" and diagram_receipt["source_pdf_sha256"] == tex_receipt["pdf"]["sha256"]
assert html_qa["diagrams"] == 70 and html_qa["sections"] == 612
pdf_pages = len(fitz.open(BUILD / "openlogic-mr-full.pdf"))
assert pdf_pages >= 900
assert pdf_qa["pages"] == pdf_pages

manifest_rows = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines() if line]
assert len(manifest_rows) == len({row["unit_id"] for row in manifest_rows}) == 722
assert {row["unit_id"] for row in manifest_rows} == {f"OLP-{n:04d}" for n in range(1, 723)}
target_paths = {"mr/" + row["source_path"] for row in manifest_rows}
actual_targets = {path.relative_to(ROOT).as_posix() for path in (ROOT / "mr").rglob("*") if path.is_file()}
assert actual_targets == target_paths

notes = RELEASE / "SOURCE_PACKAGE_README.md"
notes.write_text(
    "# Editable complete Marathi source\n\n"
    "This archive contains all 722 Marathi TeX units and the frozen English source "
    f"at revision `{REVISION}`, fonts, and build tools. "
    "The `provenance/` directory contains the full aligned translation ledger. "
    "From the extracted root, run `tools/prepare_complete.py` to assemble the "
    "complete reader, then `tools/build_guarded.ps1 -Target full "
    "-PrepareScript tools/prepare_complete.py` on Windows with XeLaTeX available. "
    "The separate release TeX file is the exact assembled source.\n\n"
    "Codex produced this machine translation with source comparison and mechanical "
    "checks. Detailed decision and occurrence review covers 281 of 722 units; "
    "independent human review is not claimed. Original text: Open Logic Project. "
    "The text and adaptation use CC BY 4.0, with separate component notices and "
    "the SIL Open Font License retained.\n",
    encoding="utf-8",
)

tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout.decode("utf-8").split("\0")
tracked = [name.replace("\\", "/") for name in tracked if name]
source_entries = []
for name in tracked:
    if name.startswith(("upstream/", "fonts/", "tools/")) and name not in {
        "tools/prepare_complete_provenance.py", "tools/sync_release_provenance.py",
        "tools/stage_complete_release.py",
    }:
        source_entries.append((name, ROOT / name))
source_entries.extend((name, ROOT / name) for name in sorted(target_paths))
source_entries.extend((name, ROOT / name) for name in ("README.md", "LICENSE.md", ".gitignore", ".gitattributes"))
for filename in ("SOURCE_MANIFEST.jsonl", "SEGMENT_CANON_USE.jsonl", "CANON_SOURCES.jsonl", "CANON_PASSAGES.jsonl", "TERM_DECISIONS.jsonl"):
    source_entries.append(("provenance/" + filename, BUILD / "release-provenance" / filename))
source_entries.append(("SOURCE_PACKAGE_README.md", notes))
assert all(source.is_file() for _, source in source_entries)
scan_private(source_entries)

html_dir = BUILD / "html"
html_entries = [(path.relative_to(html_dir).as_posix(), path) for path in html_dir.rglob("*")
                if path.is_file() and path.name != "mathglyph-smoke.html"]
assert len(html_entries) == 78 and {name for name, _ in html_entries} >= {"index.html", "reader.css", "fonts/OFL.txt"}
scan_private(html_entries)

prefix = "openlogic-mr-complete"
pdf = RELEASE / (prefix + ".pdf")
tex = RELEASE / (prefix + ".tex")
pdf.write_bytes((BUILD / "openlogic-mr-full.pdf").read_bytes())
tex.write_bytes((BUILD / "openlogic-mr-full.tex").read_bytes())
html_zip = RELEASE / (prefix + "-html.zip")
source_zip = RELEASE / (prefix + "-editable-sources.zip")
make_zip(html_zip, html_entries)
make_zip(source_zip, source_entries)

coverage = {
    "translated_source_units": 722,
    "total_source_units": 722,
    "aligned_segments": provenance_qa["aligned_segments"],
    "reader_chapters": inputs["chapters"],
    "reader_sections": inputs["sections"],
    "detailed_review_units": provenance_qa["detailed_review_units"],
    "detailed_review_occurrences": provenance_qa["detailed_review_occurrences"],
}
qa = {
    "schema": "openlogic-mr-complete-release-qa/1",
    "release": TAG,
    "coverage": coverage,
    "pdf_pages": pdf_pages,
    "pdf_log_clean": True,
    "pdf_all_pages_structurally_checked": True,
    "html_ready": True,
    "desktop_and_mobile_browser_passed": True,
    "diagram_assets": html_qa["diagrams"],
    "mathml_nodes": html_qa["mathml_nodes"],
    "semantic_proof_tables": html_qa["proof_tables"],
    "source_hashes_verified": 722,
    "provenance_report_sha256": sha(BUILD / "PROVENANCE_QA.json"),
}
qa_path = RELEASE / "RELEASE_QA.json"
write_json(qa_path, qa)
assets = [artifact(path) for path in (pdf, tex, html_zip, source_zip, qa_path, notes,
                                      RELEASE / "RELEASE_NOTES.md")]
release_manifest = {
    "schema": "openlogic-release-manifest/1",
    "release": TAG,
    "description": "Complete Marathi translation of The Open Logic Text in PDF, offline HTML, and editable TeX.",
    "repository": "https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN",
    "upstream_revision": REVISION,
    "coverage": coverage,
    "reader": {"pdf_pages": pdf_pages, "native_mathml": html_qa["mathml_nodes"],
               "semantic_proof_figures": html_qa["proof_tables"], "diagrams": html_qa["diagrams"]},
    "assets": assets,
    "full_edition_complete": True,
}
manifest_path = RELEASE / "RELEASE_MANIFEST.json"
write_json(manifest_path, release_manifest)
checksums = RELEASE / "SHA256SUMS.txt"
checksums.write_text("".join(f"{sha(RELEASE / item['filename'])}  {item['filename']}\n"
                             for item in assets + [artifact(manifest_path)]), encoding="utf-8")
for item in assets + [artifact(manifest_path)]:
    assert sha(RELEASE / item["filename"]) == item["sha256"]
print(json.dumps({"release": TAG, "coverage": coverage, "pages": pdf_pages,
                  "assets": assets}, ensure_ascii=False))
