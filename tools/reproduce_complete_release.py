"""Rebuild the released PDF and complete offline HTML from the exact source ZIP."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
RELEASE = None

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

parser = argparse.ArgumentParser()
parser.add_argument("--attempt", type=int, required=True)
parser.add_argument("--release", choices=["complete-v1.0", "complete-v1.1"], default="complete-v1.0")
parser.add_argument("--pwsh", default=shutil.which("pwsh"))
args = parser.parse_args()
assert args.attempt > 0 and args.pwsh and Path(args.pwsh).is_file()
RELEASE = ROOT / "releases" / args.release
source_zip = RELEASE / "03-openlogic-mr-complete-editable-sources.zip"
html_zip = RELEASE / "04-openlogic-mr-complete-html.zip"
pdf = RELEASE / "01-openlogic-mr-complete.pdf"
tex = RELEASE / "02-openlogic-mr-complete.tex"
destination = ROOT / "build/source-replay" / f"{args.release}-{args.attempt}"
assert not destination.exists(), "Use a new bounded attempt after confirming the preceding process is terminal."
destination.resolve().relative_to(ROOT.resolve())
receipt_path = RELEASE / "RELEASE_REPRODUCIBILITY.json"
report = {
    "schema": "openlogic-mr-complete-release-reproduction/1", "status": "started",
    "source_zip_sha256": sha(source_zip), "html_zip_sha256": sha(html_zip),
    "released_pdf_sha256": sha(pdf), "released_tex_sha256": sha(tex),
    "source_date_epoch": "1788480000", "attempt": args.attempt,
    "scope_mr": "संपूर्ण प्रकाशित स्रोत-ZIP मधून नव्याने तयार केलेला PDF आणि ऑफलाइन HTML मधील प्रत्येक फाइल.",
}

def save():
    receipt_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if result.returncode:
        # Keep owned diagnostics local; public receipts contain only their hash.
        log = destination / "reproduction-error.txt"
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        report.update(status="failed", diagnostics_sha256=sha(log))
        save()
        raise RuntimeError("Source reproduction failed; inspect the owned reproduction-error.txt.")

save()
with zipfile.ZipFile(source_zip) as archive:
    names = archive.namelist()
    assert len(names) == len(set(names))
    for name in names:
        part = PurePosixPath(name)
        assert not part.is_absolute() and ".." not in part.parts and "\\" not in name
        assert ":" not in name
        mode = archive.getinfo(name).external_attr >> 16
        assert mode & 0o170000 != 0o120000
        (destination / Path(*part.parts)).resolve().relative_to(destination.resolve())
    archive.extractall(destination)
    assert archive.read("build/full/openlogic-mr-full.tex") == tex.read_bytes()
    for name in names:
        assert (destination / name).read_bytes() == archive.read(name)
    report["extracted_files_verified"] = len(names)
assert len(list((destination / "mr").rglob("*.tex"))) == 722
run([sys.executable, "-X", "utf8", "tools/prepare_complete.py"], destination)
rebuilt = destination / "build/full"
assert sha(rebuilt / "openlogic-mr-full.tex") == sha(tex)
report["regenerated_tex_sha256"] = sha(rebuilt / "openlogic-mr-full.tex")
run([args.pwsh, "-NoProfile", "-File", "tools/build_guarded.ps1", "-Target", "full",
     "-PrepareScript", "tools/prepare_complete.py", "-SlotTimeoutMilliseconds", "1500"], destination)
tex_receipt = load(rebuilt / "TEX_BUILD_RECEIPT.json")
report["guarded_build_result"] = tex_receipt["result"]
report["guarded_build_receipt_sha256"] = sha(rebuilt / "TEX_BUILD_RECEIPT.json")
if tex_receipt["result"] == "slot-occupied":
    report["status"] = "pending-later-natural-checkpoint"
    save()
    print(json.dumps({"status": report["status"], "guarded_build_result": "slot-occupied"}))
    sys.exit(0)
assert tex_receipt["result"] == "built-log-clean" and len(tex_receipt["passes"]) == 3
assert tex_receipt["texInputSha256"] == sha(tex)
assert sha(rebuilt / "openlogic-mr-full.pdf") == sha(pdf)
report["rebuilt_pdf_sha256"] = sha(rebuilt / "openlogic-mr-full.pdf")
for script in ("complete_html_diagrams.py", "prepare_complete_html.py", "qa_complete_html.py"):
    run([sys.executable, "-X", "utf8", "tools/" + script], destination)
html_root = rebuilt / "html"
actual_names = {p.relative_to(html_root).as_posix() for p in html_root.rglob("*")
                if p.is_file() and p.name != "mathglyph-smoke.html"}
verified = []
with zipfile.ZipFile(html_zip) as archive:
    assert actual_names == set(archive.namelist())
    for name in sorted(actual_names):
        local = html_root / name
        data = archive.read(name)
        assert local.read_bytes() == data, name
        verified.append({"filename": name, "bytes": len(data), "sha256": sha(local)})
assert len(verified) == 78
assert load(rebuilt / "HTML_QA.json")["result"] == "ready"
if args.release == "complete-v1.1":
    accepted = destination / "build/epub-complete-v1.1/accepted-html"
    accepted.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(html_zip) as archive:
        for name in archive.namelist():
            target = accepted / Path(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    assert sha(accepted / "index.html") == sha(html_root / "index.html")
    epub = RELEASE / "06-openlogic-mr-complete.epub"
    run([sys.executable, "-X", "utf8", "tools/build_complete_epub.py",
         "build/epub-complete-v1.1/EPUB_BUILD_CONFIG.json"], destination)
    rebuilt_epub = destination / "build/epub-complete-v1.1/openlogic-mr-complete.epub"
    assert sha(rebuilt_epub) == sha(epub)
    report["rebuilt_epub_sha256"] = sha(rebuilt_epub)
    report["epub_byte_identity"] = True
report.update(status="passed", html_files_verified=verified,
              rebuilt_html_sha256=sha(html_root / "index.html"),
              pdf_byte_identity=True, html_all_files_byte_identity=True)
save()
print(json.dumps({"status": "passed", "pdf_sha256": report["rebuilt_pdf_sha256"],
                  "html_files": len(verified), "receipt_sha256": sha(receipt_path)}))
