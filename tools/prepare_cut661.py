"""Assemble the complete supplemental cut-elimination chapter for local TeX QA."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/proof"
BUILD.mkdir(parents=True, exist_ok=True)
with redirect_stdout(StringIO()):
    prior = runpy.run_path(str(ROOT / "tools/prepare_core642.py"))
helpers = prior["helpers"]
base = (ROOT / "build/core/openlogic-mr-core.tex").read_text(encoding="utf-8")
preamble, marker, _ = base.partition(r"\begin{document}")
assert marker and r"\newcommand{\fn}" in preamble

folder = ROOT / "mr/content/proof-theory/cut-elimination"
driver = helpers["selected"]((folder / "cut-elimination.tex").read_text(encoding="utf-8"))
assert r"\olchapter{pt}{cut}{कट-निर्मूलन}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction", "ce-topmost", "ce-largest", "midsequent", "interpolation",
]

files = []
available = {"pt:cut:chap"}
for name in imports:
    path = folder / (name + ".tex")
    raw = helpers["selected"](path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1, 2) == ("pt", "cut"), name
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    files.append((name, path, raw, parts, prefix))

def reference(match, parts):
    options = re.findall(r"\[([^]]*)\]", match.group(1))
    assert len(options) <= 3
    key_parts = parts.copy()
    if options:
        key_parts[3 - len(options):] = options
    label = ":".join(key_parts) + ":" + match.group(2)
    if label in available:
        return r"\ref{" + label + "}"
    return r"\readerexternalref{" + label + "}"

chunks = [
    r"\chapter{कट-निर्मूलन}\label{pt:cut:chap}",
    r"\begin{editorial}हे पूर्ण अनुवादित पूरक प्रकरण स्थानिक निदानासाठी मांडले आहे. "
    r"मूळ माएहारा-सिद्धतेतील चर-पदाचा प्रसंग स्वतंत्रपणे दिलेला नाही; "
    r"हा उघडा स्रोत-दोष OLINC-344 मध्ये नोंदला आहे.\end{editorial}",
]
for name, path, raw, parts, prefix in files:
    content = helpers["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    local_tokens = {
        "height": "उंची",
        "proof": "सिद्धता",
        "provable": "सिद्धतायोग्य",
        "prove": "सिद्ध",
        "derivation": "निष्पत्ती",
    }
    content = re.sub(
        r"!!(?:\^?a|\^)?\{(height|proof|provable|prove|derivation)\}(?:s|d)?",
        lambda m: local_tokens[m.group(1)],
        content,
    )
    content = helpers["replace_tokens"](content)
    content = helpers["convert_section"](content, prefix)
    content = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}",
        content,
    )
    content = re.sub(
        r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: reference(m, parts),
        content,
    )
    active = "\n".join(line for line in content.splitlines() if not line.lstrip().startswith("%"))
    assert "!!" not in active, (name, set(re.findall(r"!![^\s,.)]*", active)))
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|olimport)", active), name
    chunks.append(content)

extras = "\n".join([
    r"\providecommand{\CutCS}{\ensuremath{\mathrm{Cut}_{\mathrm{CS}}}}",
    r"\providecommand{\maeh}[2]{{#1\mathrel{;}#2}}",
    r"\providecommand{\pheight}[1]{\fn{ht}(#1)}",
    r"\providecommand{\depth}[1]{\fn{dp}(#1)}",
    r"\providecommand{\cheight}[1]{\fn{ch}(#1)}",
    r"\providecommand{\cutr}[1]{\fn{cr}(#1)}",
    r"\providecommand{\cutrank}[1]{\fn{cr}(#1)}",
    r"\hypersetup{pdftitle={मुक्त तर्कशास्त्र: कट-निर्मूलन, स्थानिक निदान}}",
])
out = (
    preamble + extras + "\n" + r"\begin{document}" + "\n"
    + "\n".join(chunks) + "\n" + r"\end{document}" + "\n"
)
assert out.count(r"\chapter{") == 1
assert len(re.findall(r"\\section\{", out)) == 5
assert out.count(r"\end{document}") == 1
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
tex = BUILD / "openlogic-mr-proof.tex"
tex.write_text(out, encoding="utf-8", newline="\n")
inputs = {
    "schema": "openlogic-local-proof-reader-input/1",
    "through_unit": "OLP-0661",
    "chapter_driver": "OLP-0657",
    "section_imports": imports,
    "paths": [path.relative_to(ROOT).as_posix() for _, path, _, _, _ in files],
    "sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
    "note": "Local diagnostic input; excludes the standalone OLP-0660 fragment and other unpaginated supplemental units.",
}
(BUILD / "INPUTS.json").write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"prepared": str(tex), "sections": 5, "bytes": len(out.encode("utf-8")), "sha256": inputs["sha256"]}, ensure_ascii=False))
