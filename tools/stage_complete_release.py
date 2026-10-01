"""Stage and byte-check the complete Marathi reader release."""

import hashlib
import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path

import fitz
from complete_reader_notes import verify_reader_notes
from complete_reader_topology import heading_inventory


parser = argparse.ArgumentParser()
parser.add_argument("--tag", choices=["complete-v1.0", "complete-v1.1", "complete-v1.2"], default="complete-v1.2")
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
TAG = args.tag
WITH_EPUB = TAG in {"complete-v1.1", "complete-v1.2"}
CANON_RECHECK_RELATIVE = "provenance/" + ("complete-v1.2" if TAG == "complete-v1.2" else "complete-v1.1") + "/CANON_RECHECK_101.json"
CANON_RECHECK_PATH = ROOT / CANON_RECHECK_RELATIVE
EPUB_BUILD = ROOT / "build" / ("epub-" + TAG)
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
pdf_visual_qa = load(BUILD / "PDF_VISUAL_QA.json")
diagram_visual_qa = load(BUILD / "HTML_DIAGRAM_VISUAL_QA.json")
html_qa = load(BUILD / "HTML_QA.json")
browser_qa = load(BUILD / "HTML_BROWSER_QA.json")
html_visual_qa = load(BUILD / "HTML_VISUAL_QA.json")
provenance_qa = load(BUILD / "PROVENANCE_QA.json")
review_qa = load(BUILD / "release-provenance/translation-decisions/TRANSLATION_DECISION_QA.json")
diagram_receipt = load(BUILD / "HTML_DIAGRAM_RECEIPT.json")
projection_qa = load(BUILD / "FINAL_READER_PROJECTION_QA.json")
reader_note_qa = load(BUILD / "READER_NOTE_QA.json")
note_manifest = {row['unit_id']:row for row in (
    json.loads(line) for line in (ROOT/'provenance/SOURCE_MANIFEST.jsonl').read_text(encoding='utf-8').splitlines() if line.strip())}
reader_note_count = verify_reader_notes(ROOT, note_manifest, (BUILD/'openlogic-mr-full.tex').read_text(encoding='utf-8'), reader_note_qa)
assert tex_receipt["result"] == "built-log-clean" and len(tex_receipt["passes"]) == 3
assert tex_receipt["texInputSha256"] == inputs["reader_sha256"] == static_qa["reader_sha256"]
assert sha(BUILD / "openlogic-mr-full.tex") == inputs["reader_sha256"]
assert projection_qa["reader_sha256"] == inputs["reader_sha256"]
assert projection_qa["factorial"]["occurrences"] == 1
assert projection_qa["factorial"]["recursive_fac_retained"]
assert projection_qa["bibliography"]["running_marks_reset"]
assert sha(BUILD / "openlogic-mr-full.pdf") == tex_receipt["pdf"]["sha256"]
assert static_qa["represented_source_units"] == 722 and not static_qa["unresolved_standard_reference_targets"]
assert pdf_qa["status"] == "ready" and pdf_qa["pdf_sha256"] == tex_receipt["pdf"]["sha256"]
assert pdf_qa["reader_sha256"] == inputs["reader_sha256"]
assert pdf_visual_qa["result"] == "pass"
assert pdf_visual_qa["pdf_sha256"] == tex_receipt["pdf"]["sha256"]
assert diagram_visual_qa["result"] == "pass"
assert diagram_visual_qa["source_pdf_sha256"] == tex_receipt["pdf"]["sha256"]
assert html_qa["result"] == "ready" and not html_qa["blockers"]
assert browser_qa["result"] == "pass"
assert browser_qa["html_sha256"] == html_qa["html_sha256"] == sha(BUILD / "html/index.html")
assert html_visual_qa["result"] == "pass"
assert html_visual_qa["html_sha256"] == sha(BUILD / "html/index.html")
assert provenance_qa["status"] == "passed" and provenance_qa["translated_units"] == 722
assert review_qa["status"] == "ready" and review_qa["source_units"] == 722
assert not review_qa["missing_localization"] and not review_qa["pending"]
assert review_qa["schema_errors"] == 0
assert review_qa["release_tag"] == TAG
if WITH_EPUB:
    epub_config = load(EPUB_BUILD / "EPUB_BUILD_CONFIG.json")
    epub_build = load(EPUB_BUILD / "EPUB_BUILD_RECEIPT.json")
    epub_qa = load(EPUB_BUILD / "EPUB_QA.json")
    epub_visual_qa = load(EPUB_BUILD / "EPUB_VISUAL_QA.json")
    canon_recheck = load(CANON_RECHECK_PATH)
    assert epub_qa["status"] == "passed" and epub_qa["epubcheck_exit"] == 0
    assert epub_qa["epub_sha256"] == epub_build["epub"]["sha256"]
    assert epub_qa["reader_html_sha256"] == html_qa["html_sha256"] == epub_config["reader_html_sha256"]
    assert epub_qa["scope"]["source_units"] == 722 and epub_qa["metrics"]["mathml_roots"] == html_qa["mathml_nodes"]
    assert epub_visual_qa["status"] == "passed-representative-actual-image-inspection"
    assert epub_visual_qa["epub_sha256"] == epub_qa["epub_sha256"]
    assert len(epub_visual_qa["samples"]) == 5
    assert canon_recheck["scope"]["intake_segments"] == 101 and canon_recheck["status"] in {"reviewed-pending-combined-reader-publication", "published"}
    if TAG == "complete-v1.2":
        assert canon_recheck["attribution_erratum"]["id"] == "SOL6-A344"
        assert canon_recheck["attribution_erratum"]["historical_report_sha256"] == sha(ROOT / "provenance/complete-v1.1/CANON_RECHECK_101.json")
    assert epub_build["cold_epub_byte_identity"] and epub_build["cold_tree_byte_identity"]
assert diagram_receipt["status"] == "final-source" and diagram_receipt["source_pdf_sha256"] == tex_receipt["pdf"]["sha256"]
assert html_qa["diagrams"] == 70
reader_headings = heading_inventory((BUILD / "openlogic-mr-full.tex").read_text(encoding="utf-8"))
assert html_qa["generated_heading_counts"] == {"h1": 1, "h2": 1, "h3": 0}
for tag, command, metric in (("h1", "part", "parts"), ("h2", "chapter", "chapters"), ("h3", "section", "sections")):
    expected = sum(row["command"] == command for row in reader_headings) + html_qa["generated_heading_counts"][tag]
    assert html_qa[metric] == html_qa["source_heading_counts"][tag] == expected
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
    "# संपूर्ण संपादनयोग्य मराठी स्रोत\n\n"
    "या संग्रहात सर्व 722 मराठी TeX एकके, अक्षररूपे, संकलन-साधने आणि "
    f"`{REVISION}` या आवृत्तीत गोठवलेला इंग्रजी स्रोत आहे. "
    "`provenance/` मध्ये संपूर्ण जुळवलेली भाषांतर-नोंदवही आहे. "
    "संग्रह उघडल्यानंतर त्याच्या मूळ निर्देशिकेतून "
    "`python tools/prepare_complete.py` चालवा. Windows वर XeLaTeX उपलब्ध "
    "असताना `tools/build_guarded.ps1 -Target full -PrepareScript "
    "tools/prepare_complete.py` वापरून संकलन करा. स्वतंत्र थेट डाउनलोड "
    "LaTeX फाइल आणि `build/full/openlogic-mr-full.tex` मधील प्रत या "
    "प्रकाशित PDF च्या नेमक्या संकलित स्रोत-प्रती आहेत.\n\n"
    "HTML पुन्हा तयार करण्यासाठी संकलनानंतर "
    "`python tools/complete_html_diagrams.py` आणि "
    "`python tools/prepare_complete_html.py` चालवा. मूळच्या 13 आकृत्यांसाठी "
    "तपासलेली स्थिर सामग्री `build/core/html/assets/` मध्ये आहे. "
    "उर्वरित आकृत्यांचे स्थाननकाशे व ओळखी `build/full/` मध्ये आहेत.\n\n"
    "यंत्रानुवाद, दुरुस्ती आणि तपासणी: OpenAI Codex — GPT-5.6 Sol आणि "
    "GPT-6 Sol, दोन्ही Ultra effort. दुरुस्ती-पुनरावलोकन GPT-6.1 Sol, Ultra effort. स्रोताशी तुलना आणि यांत्रिक तपासण्या "
    "केल्या आहेत. अधिक तपशीलवार शब्दनिर्णय-पुनरावलोकन 722 पैकी 281 "
    "एककांपुरते आहे; स्वतंत्र मानवी पुनरावलोकनाचा दावा नाही. "
    "या नव्या दुरुस्ती-पुनरावलोकनात मागील GPT-6 Sol कामातील सर्व519 "
    "प्रभावित एकके प्रत्यक्ष वाचून 328 दुरुस्ती-निवडी नोंदल्या आहेत. "
    "हा सर्व722 एककांच्या नव्या अर्थपुनर्वाचनाचा दावा नाही. "
    "मूळ निर्माते Open Logic Project आहेत. मजकूर व रूपांतर CC BY 4.0 "
    "अंतर्गत आहेत. घटकांच्या स्वतंत्र परवाना-नोंदी आणि SIL Open Font "
    "License जतन केले आहेत.\n",
    encoding="utf-8",
)

tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout.decode("utf-8").split("\0")
tracked = [name.replace("\\", "/") for name in tracked if name]
pristine_core_tool = BUILD / "release-pristine-tools/prepare_core_html.py"
pristine_core_tool.parent.mkdir(parents=True, exist_ok=True)
pristine_core_tool.write_bytes(subprocess.run(
    ["git", "show", "HEAD:tools/prepare_core_html.py"], cwd=ROOT,
    check=True, capture_output=True).stdout)
source_entries = []
for name in tracked:
    if name.startswith(("upstream/", "fonts/", "tools/")) and name not in {
        "tools/prepare_complete_provenance.py", "tools/sync_release_provenance.py",
        "tools/stage_complete_release.py",
    }:
        source_entries.append((name, pristine_core_tool if name == "tools/prepare_core_html.py" else ROOT / name))
# Reproducibility depends on the actual required tools, including reviewed new
# helpers that have not been committed yet. Preserve the pristine core-HTML
# selection above and omit the same private-production-only exporters.
included_tools = {name for name, _ in source_entries}
for tool_path in sorted((ROOT / 'tools').iterdir()):
    name = tool_path.relative_to(ROOT).as_posix()
    if tool_path.is_file() and tool_path.suffix in {'.py', '.ps1'} and name not in included_tools and name not in {
        'tools/prepare_complete_provenance.py', 'tools/sync_release_provenance.py', 'tools/stage_complete_release.py',
    }:
        source_entries.append((name, tool_path))
source_entries.extend((name, ROOT / name) for name in sorted(target_paths))
source_entries.extend((name, ROOT / name) for name in ("README.md", "LICENSE.md", ".gitignore", ".gitattributes"))
for filename in ("SOURCE_MANIFEST.jsonl", "SEGMENT_CANON_USE.jsonl", "CANON_SOURCES.jsonl", "CANON_PASSAGES.jsonl", "TERM_DECISIONS.jsonl"):
    source_entries.append(("provenance/" + filename, BUILD / "release-provenance" / filename))
included_provenance = {name for name, _ in source_entries if name.startswith("provenance/")}
for path in (BUILD / "release-provenance").rglob("*"):
    if path.is_file():
        name = "provenance/" + path.relative_to(BUILD / "release-provenance").as_posix()
        if name not in included_provenance:
            source_entries.append((name, path))
if WITH_EPUB:
    source_entries.append((CANON_RECHECK_RELATIVE, CANON_RECHECK_PATH))
    source_entries.append((f"build/epub-{TAG}/EPUB_BUILD_CONFIG.json", EPUB_BUILD / "EPUB_BUILD_CONFIG.json"))
for path in sorted((ROOT / "provenance/sol6-reaudit").glob("*")):
    if path.is_file():
        source_entries.append((path.relative_to(ROOT).as_posix(), path))
source_entries.append(("provenance/complete-v1.0/TERMINOLOGY_MR.jsonl",
                       ROOT / "provenance/complete-v1.0/TERMINOLOGY_MR.jsonl"))
source_entries.append(("provenance/complete-v1.0/SOURCE_ISSUES_MR.jsonl",
                       ROOT / "provenance/complete-v1.0/SOURCE_ISSUES_MR.jsonl"))
source_entries.append(("SOURCE_PACKAGE_README.md", notes))
for name in ("INPUTS.json", "DRIVER_EDITORIAL_QA.json", "READER_NOTE_QA.json", "FINAL_READER_PROJECTION_QA.json", "PDF_VISUAL_QA.json", "HTML_VISUAL_QA.json", "HTML_DIAGRAM_VISUAL_QA.json", "HTML_DIAGRAM_INVENTORY.json", "HTML_DIAGRAM_RECEIPT.json",
             "TEX_BUILD_RECEIPT.json", "openlogic-mr-full.tex", "openlogic-mr-full.aux"):
    source_entries.append(("build/full/" + name, BUILD / name))
source_entries.append(("build/core/HTML_BUILD_RECEIPT.json", ROOT / "build/core/HTML_BUILD_RECEIPT.json"))
core_receipt = load(ROOT / "build/core/HTML_BUILD_RECEIPT.json")
for row in core_receipt["diagram_assets"]:
    filename = row["filename"].removeprefix("assets/")
    source_entries.append(("build/core/html/assets/" + filename,
                           ROOT / "build/core/html/assets" / filename))
assert all(source.is_file() for _, source in source_entries)
scan_private(source_entries)

html_dir = BUILD / "html"
html_entries = [(path.relative_to(html_dir).as_posix(), path) for path in html_dir.rglob("*")
                if path.is_file() and path.name != "mathglyph-smoke.html"]
assert len(html_entries) == 78 and {name for name, _ in html_entries} >= {"index.html", "reader.css", "fonts/OFL.txt"}
scan_private(html_entries)

prefix = "openlogic-mr-complete"
pdf = RELEASE / ("01-" + prefix + ".pdf")
tex = RELEASE / ("02-" + prefix + ".tex")
pdf.write_bytes((BUILD / "openlogic-mr-full.pdf").read_bytes())
tex.write_bytes((BUILD / "openlogic-mr-full.tex").read_bytes())
reader_source = tex.read_text(encoding="utf-8")
chapter_starts = list(re.finditer(r"\\chapter\{", reader_source))
assert len(chapter_starts) == 79
chapter_sources = []
chapter_manifest = []
for index, match in enumerate(chapter_starts):
    title_start = match.end()
    cursor, depth = title_start, 1
    while depth:
        assert cursor < len(reader_source)
        char = reader_source[cursor]
        if char == "{" and reader_source[cursor - 1] != "\\":
            depth += 1
        elif char == "}" and reader_source[cursor - 1] != "\\":
            depth -= 1
        cursor += 1
    title = reader_source[title_start:cursor - 1]
    end = chapter_starts[index + 1].start() if index + 1 < len(chapter_starts) else reader_source.index(r"\end{document}")
    body = reader_source[match.start():end]
    chapter = RELEASE / f"11-openlogic-mr-chapter-{index + 1:03d}.tex"
    header = (
        f"% संपूर्ण मराठी ग्रंथातील प्रकरण {index + 1}: {title}\n"
        "% हा संपादनयोग्य स्रोतखंड आहे. संकलनासाठी संपूर्ण स्रोतसंग्रहातील\n"
        "% अक्षररूपे, पूर्वभाग, चिन्हव्याख्या आणि आकृती-स्रोत आवश्यक आहेत.\n"
        "% मूळ: Open Logic Project; मजकूर आणि रूपांतर CC BY 4.0.\n"
        "% यंत्रानुवाद, दुरुस्ती आणि तपासणी: OpenAI Codex —\n"
        "% GPT-5.6 Sol आणि GPT-6 Sol, दोन्ही Ultra effort.\n"
        "% दुरुस्ती-पुनरावलोकन: GPT-6.1 Sol, Ultra effort.\n"
    )
    chapter.write_text(header + body, encoding="utf-8", newline="\n")
    assert chapter.read_text(encoding="utf-8")[len(header):] == body
    chapter_sources.append(chapter)
    chapter_manifest.append({"chapter": index + 1, "title_tex": title,
                             "source_kind_mr": "संचयी ग्रंथाचा प्रकरण-स्रोतखंड",
                             **artifact(chapter)})
    source_entries.append(("chapter-sources/" + chapter.name, chapter))
html_zip = RELEASE / ("04-" + prefix + "-html.zip")
source_zip = RELEASE / ("03-" + prefix + "-editable-sources.zip")
review_zip = RELEASE / ("05-" + prefix + "-review.zip")
make_zip(html_zip, html_entries)
make_zip(source_zip, source_entries)
review_entries = []
for path in (BUILD / "release-provenance/translation-decisions").rglob("*"):
    if path.is_file():
        review_entries.append(("translation-decisions/" + path.name, path))
for name in ("EXPERT_REVIEW_DECISIONS.jsonl", "EXPERT_REVIEW_OCCURRENCES.jsonl", "EXPERT_REVIEW_OCCURRENCES.csv",
             "EXPERT_REVIEW_LOG.md", "EXPERT_REVIEW_OCCURRENCES.md", "EXPERT_REVIEW_PRIORITY.md"):
    review_entries.append(("legacy/" + name, BUILD / "release-provenance" / name))
    if WITH_EPUB:
        review_entries.append(("historical-detailed-review/" + name,
                               BUILD / "release-provenance/historical-detailed-review" / name))
review_entries.append(("SOURCE_ISSUES.jsonl", BUILD / "release-provenance/SOURCE_ISSUES.jsonl"))
review_entries.append(("REVIEW_READER_BINDING.json", BUILD / "release-provenance/REVIEW_READER_BINDING.json"))
for name in ("TERMINOLOGY_MR.jsonl", "SOURCE_ISSUES_MR.jsonl"):
    review_entries.append(("complete-v1.0/" + name, ROOT / "provenance/complete-v1.0" / name))
if WITH_EPUB:
    review_entries.append((CANON_RECHECK_RELATIVE.removeprefix("provenance/"), CANON_RECHECK_PATH))
    review_entries.append((f"{TAG}/EPUB_VISUAL_QA.json", EPUB_BUILD / "EPUB_VISUAL_QA.json"))
for path in sorted((ROOT / "provenance/sol6-reaudit").glob("*")):
    if path.is_file():
        review_entries.append(("sol6-reaudit/" + path.name, path))
scan_private(review_entries)
make_zip(review_zip, review_entries)
subprocess.run(["python", str(ROOT / "tools/validate_release_consistency.py"),
                "--editable-zip", str(source_zip), "--review-zip", str(review_zip),
                "--reader-pdf", str(pdf), "--receipt", str(RELEASE / "RELEASE_CONSISTENCY.json")],
               cwd=ROOT, check=True)

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
    "review_context_occurrences": review_qa["context_occurrences"],
    "review_total_occurrences": review_qa["total_review_occurrences"],
    "corrective_decisions": review_qa.get("corrective_decisions", 0),
    "corrective_occurrences": review_qa.get("corrective_occurrences", 0),
    "localized_term_decisions": review_qa["localized_term_decisions"],
    "localized_source_issues": review_qa["localized_source_issues"],
    "final_reader_projection_qa_sha256": sha(BUILD / "FINAL_READER_PROJECTION_QA.json"),
    "source_reader_notes": reader_note_count,
    "reader_note_qa_sha256": sha(BUILD / "READER_NOTE_QA.json"),
    "reader_notice_mr": "सर्व 722 स्रोत-एककांची जुळवणी तपासली आहे. संदर्भ-निर्देश स्वतंत्र तज्ज्ञ स्वीकृतीची प्रमाणपत्रे नाहीत. ऐतिहासिक तपशीलवार पुनरावलोकन 281 एककांपुरते आहे.",
    "provenance_report_sha256": sha(BUILD / "PROVENANCE_QA.json"),
}
if TAG == "complete-v1.2":
    support = load(ROOT / "provenance/sol6-reaudit/SUPPORTING_ARTIFACT_AUDIT_361.json")
    qa["sol6_reaudit"] = {
        "affected_units_directly_read": 519,
        "additional_control_units": 2,
        "original_affected_tools_directly_read": 82,
        "supporting_paths_checked": support["scope"]["total_supporting_paths"],
        "corrective_choices": review_qa["corrective_decisions"],
        "pdf_pages_actually_viewed": len(pdf_visual_qa["samples"]),
        "current_svg_diagrams_actually_viewed": diagram_visual_qa["svg_assets_actually_viewed"],
        "scope_notice_mr": "सर्व519 प्रभावित स्रोत-एककांचे प्रत्यक्ष पुनर्वाचन; सर्व722 एककांच्या नव्या अर्थपुनर्वाचनाचा दावा नाही. दृश्यतपासणी निवडक PDF/HTML/EPUB नमुने आणि सर्व57 नव्या SVG आकृत्यांपुरती आहे. स्वतंत्र मानवी स्वीकृती नाही.",
    }
qa_path = RELEASE / "RELEASE_QA.json"
if WITH_EPUB:
    qa["retrospective_canon_recheck"] = {"contexts": 101, "sha256": sha(CANON_RECHECK_PATH)}
    qa["complete_epub"] = {"sha256": epub_qa["epub_sha256"], "qa_sha256": sha(EPUB_BUILD / "EPUB_QA.json"), "mathml_roots": epub_qa["metrics"]["mathml_roots"]}
write_json(qa_path, qa)
assets = [artifact(path) for path in (pdf, tex, source_zip, html_zip, review_zip, qa_path, notes,
                                      RELEASE / "RELEASE_NOTES.md", RELEASE / "RELEASE_CONSISTENCY.json")]
assets.extend(artifact(path) for path in chapter_sources)
if WITH_EPUB:
    epub_file = RELEASE / "06-openlogic-mr-complete.epub"
    epub_file.write_bytes((ROOT / epub_config["output_epub"]).read_bytes())
    epub_qa_file = RELEASE / "EPUB_QA.json"
    epub_qa_file.write_bytes((EPUB_BUILD / "EPUB_QA.json").read_bytes())
    canon_file = RELEASE / "CANON_RECHECK_101.json"
    canon_file.write_bytes(CANON_RECHECK_PATH.read_bytes())
    assets.extend(artifact(path) for path in (epub_file, epub_qa_file, canon_file))
reproduction_path = RELEASE / "RELEASE_REPRODUCIBILITY.json"
reproduction_verified = False
if reproduction_path.is_file():
    reproduction = load(reproduction_path)
    reproduction_verified = (
        reproduction["status"] == "passed"
        and reproduction["source_zip_sha256"] == sha(source_zip)
        and reproduction["html_zip_sha256"] == sha(html_zip)
        and reproduction["rebuilt_pdf_sha256"] == sha(pdf)
        and reproduction["regenerated_tex_sha256"] == sha(tex)
        and (not WITH_EPUB or (
            reproduction.get("epub_byte_identity") is True
            and reproduction.get("rebuilt_epub_sha256") == sha(RELEASE / "06-openlogic-mr-complete.epub")))
    )
    if reproduction_verified:
        assets.append(artifact(reproduction_path))
assert len(assets) + 2 <= 100, "Manifest and checksums also count toward the public file limit."
release_manifest = {
    "schema": "openlogic-release-manifest/1",
    "release": TAG,
    "description": "मुक्त तर्कशास्त्राची संपूर्ण मराठी आवृत्ती: PDF, संपादनयोग्य TeX, ऑफलाइन HTML आणि EPUB.",
    "ai_translation_correction_and_checks": {
        "models": ["gpt-5.6-sol", "gpt-6-sol", "gpt-6.1-sol"], "effort": "ultra",
        "reader_notice": "यंत्रानुवाद, दुरुस्ती आणि तपासणी: OpenAI Codex — GPT-5.6 Sol आणि GPT-6 Sol, दोन्ही Ultra effort; दुरुस्ती-पुनरावलोकन GPT-6.1 Sol, Ultra effort.",
    },
    "repository": "https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN",
    "upstream_revision": REVISION,
    "coverage": coverage,
    "reader": {"pdf_pages": pdf_pages, "native_mathml": html_qa["mathml_nodes"],
               "semantic_proof_figures": html_qa["proof_tables"], "diagrams": html_qa["diagrams"]},
    "assets": assets,
    "individual_chapter_sources": chapter_manifest,
    "full_edition_complete": True,
    "release_reproduction_verified": reproduction_verified,
}
if WITH_EPUB:
    release_manifest["epub"] = {"source_units": 722, "reading_documents": epub_qa["metrics"]["reading_documents"],
                                "mathml_roots": epub_qa["metrics"]["mathml_roots"],
                                "epubcheck_version": "5.3.0", "qa_sha256": sha(EPUB_BUILD / "EPUB_QA.json")}
    release_manifest["epub"]["visual_qa_sha256"] = sha(EPUB_BUILD / "EPUB_VISUAL_QA.json")
    release_manifest["retrospective_canon_recheck"] = {
        "date": "2026-09-29", "contexts": 101,
        "canon_sources": provenance_qa["canon_sources"], "canon_passages": provenance_qa["canon_passages"],
        "sha256": sha(CANON_RECHECK_PATH)}
manifest_path = RELEASE / "RELEASE_MANIFEST.json"
write_json(manifest_path, release_manifest)
checksums = RELEASE / "SHA256SUMS.txt"
checksums.write_text("".join(f"{sha(RELEASE / item['filename'])}  {item['filename']}\n"
                             for item in assets + [artifact(manifest_path)]), encoding="utf-8")
for item in assets + [artifact(manifest_path)]:
    assert sha(RELEASE / item["filename"]) == item["sha256"]
print(json.dumps({"release": TAG, "coverage": coverage, "pages": pdf_pages,
                  "assets": assets}, ensure_ascii=False))
