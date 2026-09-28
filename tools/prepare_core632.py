"""Assemble 69 complete Marathi chapters through OLP-0632 without TeX."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from reader_bibliography import parse_bib, render_bibliography

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core"
with redirect_stdout(StringIO()):
    prior_ns = runpy.run_path(str(ROOT / "tools/prepare_core619.py"))
prior_ns = prior_ns["prior_ns"]
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
assert base.count("६८ संपूर्ण प्रकरणे") == 1
base = base.replace("६८ संपूर्ण प्रकरणे", "६९ संपूर्ण प्रकरणे", 1)
old = "OLP-0004 ते OLP-0619, एकूण 616 स्रोत-एकके आणि 533 वाचक-विभाग. उर्वरित 106"
new = "OLP-0004 ते OLP-0632, एकूण 629 स्रोत-एकके आणि 544 वाचक-विभाग. उर्वरित 93"
assert base.count(old) == 1
base = base.replace(old, new, 1)

part_driver = prior_ns["selected"](
    (ROOT / "mr/content/history/history.tex").read_text(encoding="utf-8"))
assert r"\olpart{his}{इतिहास}" in part_driver
assert re.findall(r"\\olimport(?:\[[^]]+\])?\{([^}]+)\}", part_driver)[:1] == ["biographies"]
folder = ROOT / "mr/content/history/biographies"
driver = prior_ns["selected"]((folder / "biographies.tex").read_text(encoding="utf-8"))
assert r"\olchapter{his}{bio}{चरित्रे}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "georg-cantor", "alonzo-church", "gerhard-gentzen", "kurt-goedel",
    "emmy-noether", "rozsa-peter", "julia-robinson", "bertrand-russell",
    "alfred-tarski", "alan-turing", "ernst-zermelo",
]

records = parse_bib((ROOT / "upstream/bib/open-logic.bib").read_text(encoding="utf-8"))


def citation_name(key):
    person = records[key].get("author", records[key].get("editor", ""))
    assert person, key
    first = person.split(" and ")[0]
    if "," in first:
        surname = first.split(",", 1)[0]
    else:
        surname = first.split()[-1]
    return surname.strip("{}")


def render_citation(match):
    command, options, keys_arg = match.groups()
    keys = [key.strip() for key in keys_arg.split(",")]
    assert keys and all(key in records for key in keys), keys
    locators = re.findall(r"\[([^]]*)\]", options)
    assert len(locators) <= 1, (command, options)
    locator = locators[0] if locators else ""
    if re.fullmatch(r"\d+(?:--\d+)?", locator):
        locator = "पृ.~" + locator
    locator = locator.replace("pp.~", "पृ.~").replace("p.~", "पृ.~")
    suffix = ", " + locator if locator else ""
    names = [citation_name(key) for key in keys]
    years = [records[key]["year"] for key in keys]
    if command == "citeauthor":
        assert not locator and len(keys) == 1
        return names[0]
    if command in {"citeyear", "citeyearpar"}:
        assert len(keys) == 1
        value = years[0] + suffix
        return "(" + value + ")" if command == "citeyearpar" else value
    if command == "citet":
        if len(keys) == 1:
            return names[0] + " (" + years[0] + suffix + ")"
        if len(set(names)) == 1:
            return names[0] + " (" + "; ".join(years) + suffix + ")"
        return "; ".join(name + " (" + year + ")" for name, year in zip(names, years))
    assert command in {"cite", "citep", "citealt"}, command
    value = "; ".join(name + " " + year for name, year in zip(names, years)) + suffix
    return value if command == "citealt" else "(" + value + ")"


available = prior_ns["available"]
external = prior_ns["external"]
available.update({"his:part", "his:bio:chap"})
files = []
for name in imports:
    raw = prior_ns["selected"]((folder / (name + ".tex")).read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1, 2) == ("his", "bio"), name
    parts = list(match.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    files.append((name, raw, parts, prefix))
external.difference_update(available)

chunks = [r"\part{इतिहास}\label{his:part}", r"\chapter{चरित्रे}\label{his:bio:chap}"]
omitted_photos = []
for name, raw, parts, prefix in files:
    content = prior_ns["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = prior_ns["replace_tokens"](content)
    for original, projection in prior["reader_symbol_projections"].items():
        content = content.replace(original, projection)
    content = prior_ns["convert_section"](content, prefix)
    content = re.sub(r"\\ollabel\{([^}]+)\}",
                     lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)
    content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
                     lambda m: prior_ns["ns"]["references"](m, parts), content)

    def omit_photo(match):
        assert not (ROOT / "upstream/assets/photos" / match.group(1) /
                    (match.group(1) + "-large.png")).exists(), match.group(1)
        omitted_photos.append({"source_unit": name, "asset_id": match.group(1),
                               "caption": match.group(2)})
        return ""

    content = re.sub(r"\\olphoto\{([^{}]+)\}\{([^{}]+)\}", omit_photo, content)
    assert content.count(r"\begin{reading}") == 1
    assert content.count(r"\end{reading}") == 1
    content = content.replace(r"\begin{reading}", r"\paragraph{अधिक वाचन.} ", 1)
    content = content.replace(r"\end{reading}", "", 1)
    content = re.sub(r"\\(cite[a-zA-Z]*)((?:\[[^]]*\])*)\{([^}]+)\}",
                     render_citation, content)
    assert "!!" not in content and not re.search(r"![A-Z]", content), name
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|olphoto|cite\w*|begin\{reading\})",
                         content), name
    chunks.append(content)
assert len(omitted_photos) == 11

marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
bib_marker = r"\chapter*{संदर्भ}"
assert base.count(marker) == 1 and base.count(bib_marker) == 1
before, notes = base.split(marker, 1)
note_body, _ = notes.split(bib_marker, 1)
editorial_notes = (
    "\n" + r"\paragraph{इतिहासातील चरित्रविषयक दुरुस्त्या.} "
    "चर्च यांच्या प्रबंधाशी संबंधित गणनीयतेचे प्रतिपादन आणि प्रथम-क्रम निर्णय समस्येवरील "
    "त्यांचे प्रमेय यांतील भेद स्पष्ट केला आहे. पेटर यांच्या जन्मनावातील उलटलेला उल्लेख, "
    "ज्युलिया रॉबिन्सन यांच्या नॅशनल अकॅडमीतील निवडीचा गणित विभागाशी संबंध, "
    "ट्यूरिंगवरील चित्रपटातील कलाकारांची नावे आणि झर्मेलो यांच्या गॉटिंगेनमधील "
    "अभ्यासस्थानाची वर्तनी तपासून दुरुस्त केली आहे.\n"
)
manifest = [json.loads(line) for line in
            (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
inputs = list(prior["input_units"])
for row in manifest[619:632]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({"unit_id": row["unit_id"], "path": path.relative_to(ROOT).as_posix(),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
assert len(inputs) == 629 and inputs[-1]["unit_id"] == "OLP-0632"
bibliography, bib_audit = render_bibliography(ROOT, inputs)
out = before + "\n".join(chunks) + "\n" + marker + note_body + editorial_notes + "\n" + bibliography + "\n" + r"\end{document}" + "\n"
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
             lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in available else m.group(0), out)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
assert out.count(r"\chapter{") == 69
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 544
assert "629 स्रोत-एकके आणि 544 वाचक-विभाग" in out
assert out.count(r"\end{document}") == 1 and out.rstrip().endswith(r"\end{document}")
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
assert set(bib_audit["rendered_keys"]) == {label[4:] for label in labels if label.startswith("bib:")}
(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="629 source units, 544 reader sections, sixty-nine complete chapters",
    external_reference_labels=sorted(set(re.findall(r"\\readerexternalref\{([^}]+)\}", out))),
    part_driver_units_not_rendered_as_sections=prior.get("part_driver_units_not_rendered_as_sections", []) + ["OLP-0620"],
    chapter_driver_units_not_rendered_as_sections=prior.get("chapter_driver_units_not_rendered_as_sections", []) + ["OLP-0621"],
    biography_photo_assets_not_present=omitted_photos,
    biography_photo_policy="The frozen source references these 11 portraits, but their files are absent from the source assets; the local diagnostic reader omits the photo macros and records each omission.",
    bibliography_audit=bib_audit,
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"prepared": "build/core/openlogic-mr-core.tex", "units": len(inputs),
                  "sections": 544, "chapters": 69,
                  "bibliography_entries": len(bib_audit["rendered_keys"]),
                  "omitted_source_photos": len(omitted_photos),
                  "sha256": hashlib.sha256(out.encode()).hexdigest()}, ensure_ascii=False))
