"""Assemble 72 complete Marathi chapters through OLP-0642 without TeX."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
with redirect_stdout(StringIO()):
    prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core639.py"))
helpers = prior_ns["helpers"]
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("७० संपूर्ण प्रकरणे") == 1
base = base.replace("७० संपूर्ण प्रकरणे", "७२ संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0639, एकूण 636 स्रोत-एकके आणि 550 वाचक-विभाग. उर्वरित 86"
new = "OLP-0004 ते OLP-0642, एकूण 639 स्रोत-एकके आणि 550 वाचक-विभाग. उर्वरित 83"
assert base.count(old) == 1
base = base.replace(old, new, 1)

folder = ROOT / "mr/content/reference"
part = helpers["selected"]((folder / "reference.tex").read_text(encoding="utf-8"))
assert r"\olpart{ref}{संदर्भसामग्री}" in part
assert re.findall(r"\\olimport(?:\[[^]]+\])?\{([^}]+)\}", part) == [
    "greek-alphabet", "fraktur-alphabet",
]
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", part, re.S)
assert editorial and part.count(r"\begin{editorial}") == 1

chapters = [
    ("greek-alphabet", "grk", "ग्रीक वर्णमाला"),
    ("fraktur-alphabet", "frk", "फ्राक्टूर वर्णमाला"),
]
chunks = [r"\part{संदर्भसामग्री}\label{ref:part}", editorial.group(0)]
for dirname, key, title in chapters:
    path = folder / dirname / (dirname + ".tex")
    raw = helpers["selected"](path.read_text(encoding="utf-8"))
    heading = r"\olchapter{ref}{" + key + "}{" + title + "}"
    assert raw.count(heading) == 1
    content = helpers["ns"]["strip_wrapper"](raw)
    content = content.replace(heading, "", 1)
    assert r"\begin{center}" in content and r"\begin{tabular}" in content
    assert r"\end{tabular}" in content and r"\end{center}" in content
    assert r"\olchapter" not in content and r"\documentclass" not in content
    if key == "grk":
        assert all(name in content for name in ["अल्फा", "न्यू", "म्यू", "ओमेगा"])
        assert content.count(r"\\") == 11
    else:
        assert content.count(r"\mathfrak{") == 52
        assert content.count(r"\\") == 12
    chunks.append(r"\chapter{" + title + r"}\label{ref:" + key + ":chap}" + "\n" + content)

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(marker) == 1
before, after = base.split(marker, 1)
out = before + "\n".join(chunks) + "\n" + marker + after
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line) for line in
    (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[639:642]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 639 and inputs[-1]["unit_id"] == "OLP-0642"
assert out.count(r"\chapter{") == 72
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 550
assert "639 स्रोत-एकके आणि 550 वाचक-विभाग" in out
assert out.count(r"\end{document}") == 1 and out.rstrip().endswith(r"\end{document}")
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
assert set(prior["bibliography_audit"]["rendered_keys"]) == {
    label[4:] for label in labels if label.startswith("bib:")
}
assert out.count(r"\mathfrak{") >= 52
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="639 source units, 550 reader sections, seventy-two complete chapters",
    part_driver_units_not_rendered_as_sections=prior.get(
        "part_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0640"],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0641", "OLP-0642"],
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs), "sections": 550, "chapters": 72,
    "bibliography_entries": len(prior["bibliography_audit"]["rendered_keys"]),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
