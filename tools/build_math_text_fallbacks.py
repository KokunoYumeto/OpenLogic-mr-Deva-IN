"""Build deterministic SVG fallbacks for Devanagari text inside MathML.

Some EPUB renderers lay out ``mtext`` one Unicode code point at a time, which
separates Devanagari vowel signs from their base characters.  The accepted
reader keeps native MathML and its exact TeX annotation, while ``mglyph`` uses
these outlined SVGs as a visual fallback.  Each glyph also carries the exact
source text in its ``alt`` attribute.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "math-text-fallbacks" / "MANIFEST.json"
DEFAULT_WORK = ROOT / "build" / "core" / "math-text-fallbacks"
FONT = ROOT / "fonts" / "OLMarathiSerif-Regular.ttf"
DEVANAGARI = re.compile(r"[\u0900-\u097f]")
SVG_SIZE = re.compile(r"\bwidth='([0-9.]+)pt'\s+height='([0-9.]+)pt'")
# The reference phrase with full Devanagari ascenders has a 13.94 bp outline
# box at 12 pt and reads naturally at 0.8 em beside Calibre's MathML glyphs.
# Scale every asset by that same factor; normalizing every outline to one height
# would make short words without upper marks visibly oversized.
DISPLAY_EM_PER_BP = 0.8 / 13.94


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_phrase(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").replace("\u2000", " ").split())


def tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def short_version(command: list[str]) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=True,
    )
    return (result.stdout or result.stderr).splitlines()[0].strip()


@contextmanager
def tex_slot(timeout_ms: int = 120_000):
    """Acquire the repository-wide TeX slot on Windows."""
    if os.name != "nt":
        yield
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    create_mutex.restype = ctypes.c_void_p
    wait = kernel32.WaitForSingleObject
    wait.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    wait.restype = ctypes.c_uint32
    release = kernel32.ReleaseMutex
    release.argtypes = (ctypes.c_void_p,)
    release.restype = ctypes.c_bool
    close = kernel32.CloseHandle
    close.argtypes = (ctypes.c_void_p,)
    close.restype = ctypes.c_bool
    handle = create_mutex(None, False, r"Global\InterlanguageTeXSlotV1")
    if not handle:
        raise OSError(ctypes.get_last_error(), "CreateMutexW failed")
    acquired = False
    try:
        status = wait(handle, timeout_ms)
        if status not in (0x00000000, 0x00000080):
            if status == 0x00000102:
                raise TimeoutError("timed out waiting for Global\\InterlanguageTeXSlotV1")
            raise OSError(ctypes.get_last_error(), f"WaitForSingleObject returned {status:#x}")
        acquired = True
        yield
    finally:
        if acquired:
            release(handle)
        close(handle)


def discover(path: Path) -> list[str]:
    document = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    phrases = {
        normalize_phrase(node.get_text())
        for node in document.select("mtext")
        if DEVANAGARI.search(node.get_text())
    }
    if not phrases or "" in phrases:
        raise RuntimeError("no usable Devanagari mtext phrases found")
    return sorted(phrases, key=lambda text: (hashlib.sha256(text.encode("utf-8")).hexdigest(), text))


def format_em(value: float) -> str:
    return f"{value:.5f}".rstrip("0").rstrip(".") + "em"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--discover-from", type=Path)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    output_dir = manifest_path.parent
    work = args.work_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.discover_from:
        phrases = discover(args.discover_from.resolve())
    else:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        phrases = [entry["text"] for entry in existing["entries"]]
    if len(phrases) != len(set(phrases)):
        raise RuntimeError("fallback phrase list contains duplicates")

    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    font_path = FONT.resolve().as_posix()
    font_dir = FONT.resolve().parent.as_posix() + "/"
    tex = [
        r"\documentclass{article}",
        r"\usepackage{fontspec}",
        r"\usepackage[active,tightpage]{preview}",
        r"\setlength\PreviewBorder{0pt}",
        rf"\setmainfont{{{FONT.name}}}[Path={font_dir}]",
        r"\pagestyle{empty}",
        r"\begin{document}",
    ]
    for phrase in phrases:
        tex.append(
            r"\begin{preview}\fontsize{12pt}{14pt}\selectfont "
            + tex_escape(phrase)
            + r"\end{preview}"
        )
    tex.append(r"\end{document}")
    tex_path = work / "math-text-fallbacks.tex"
    tex_path.write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")

    xelatex = shutil.which("xelatex")
    dvisvgm = shutil.which("dvisvgm")
    if not xelatex or not dvisvgm:
        raise RuntimeError("xelatex and dvisvgm are required")
    with tex_slot():
        latex = subprocess.run(
            [xelatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    (work / "xelatex.stdout.log").write_text(latex.stdout, encoding="utf-8", newline="\n")
    (work / "xelatex.stderr.log").write_text(latex.stderr, encoding="utf-8", newline="\n")
    if latex.returncode:
        raise RuntimeError(f"xelatex failed with status {latex.returncode}:\n{latex.stdout[-4000:]}")
    pdf = work / "math-text-fallbacks.pdf"
    vector = subprocess.run(
        [
            dvisvgm,
            "--pdf",
            "--page=1-",
            "--no-fonts",
            "--exact-bbox",
            f"--output={work / 'page-%p.svg'}",
            str(pdf),
        ],
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    (work / "dvisvgm.stdout.log").write_text(vector.stdout, encoding="utf-8", newline="\n")
    (work / "dvisvgm.stderr.log").write_text(vector.stderr, encoding="utf-8", newline="\n")
    if vector.returncode:
        raise RuntimeError(f"dvisvgm failed with status {vector.returncode}:\n{vector.stderr[-4000:]}")

    entries = []
    expected_names = set()
    page_digits = len(str(len(phrases)))
    for page, phrase in enumerate(phrases, 1):
        source = work / f"page-{page:0{page_digits}d}.svg"
        if not source.is_file():
            raise RuntimeError(f"missing dvisvgm page {page}")
        svg = source.read_text(encoding="utf-8").replace("\r\n", "\n")
        svg = re.sub(r"<!-- This file was generated by dvisvgm [^>]+-->\n?", "", svg, count=1)
        match = SVG_SIZE.search(svg)
        if not match:
            raise RuntimeError(f"cannot read SVG dimensions for page {page}")
        width_bp, height_bp = map(float, match.groups())
        filename = "mtext-" + hashlib.sha256(phrase.encode("utf-8")).hexdigest()[:20] + ".svg"
        expected_names.add(filename)
        destination = output_dir / filename
        destination.write_text(svg.rstrip() + "\n", encoding="utf-8", newline="\n")
        entries.append(
            {
                "text": phrase,
                "filename": filename,
                "width_bp": round(width_bp, 5),
                "height_bp": round(height_bp, 5),
                "display_width": format_em(width_bp * DISPLAY_EM_PER_BP),
                "display_height": format_em(height_bp * DISPLAY_EM_PER_BP),
                "valign": "0em",
                "bytes": destination.stat().st_size,
                "sha256": digest(destination),
            }
        )
    for stale in output_dir.glob("mtext-*.svg"):
        if stale.name not in expected_names:
            stale.unlink()

    manifest = {
        "schema": "openlogic-marathi-math-text-fallbacks/1",
        "purpose": "Outlined visual fallbacks for Devanagari mtext in reading systems that do not shape Indic text in MathML.",
        "font": {
            "path": FONT.relative_to(ROOT).as_posix(),
            "bytes": FONT.stat().st_size,
            "sha256": digest(FONT),
            "size_pt": 12,
        },
        "rendering": {
            "tex_mutex": r"Global\InterlanguageTeXSlotV1",
            "xelatex": short_version([xelatex, "--version"]),
            "dvisvgm": short_version([dvisvgm, "--version"]),
            "dvisvgm_arguments": ["--pdf", "--page=1-", "--no-fonts", "--exact-bbox"],
            "display_em_per_bp": DISPLAY_EM_PER_BP,
            "source_tex": tex_path.relative_to(ROOT).as_posix(),
            "source_tex_sha256": digest(tex_path),
        },
        "entries": entries,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "manifest": manifest_path.relative_to(ROOT).as_posix(),
                "phrases": len(entries),
                "font": font_path,
                "manifest_sha256": digest(manifest_path),
                "svg_bytes": sum(entry["bytes"] for entry in entries),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
