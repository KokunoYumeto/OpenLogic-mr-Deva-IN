"""Assemble 38 complete Marathi chapters through OLP-0382 without launching TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core372.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("सदतीस संपूर्ण प्रकरणे") == 1
base = base.replace("सदतीस संपूर्ण प्रकरणे", "अडतीस संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0372, एकूण 369 स्रोत-एकके "
    "आणि 324 वाचक-विभाग. उर्वरित 353"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0382, एकूण 379 स्रोत-एकके "
    "आणि 333 वाचक-विभाग. उर्वरित 343"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)

selected = prior_namespace["selected"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/lambda-calculus/lambda-definability"
driver = selected((folder / "lambda-definability.tex").read_text(encoding="utf-8"))
assert r"\olchapter{lam}{rep}{लॅम्डा-परिभाष्यता}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction",
    "arithmetical-functions",
    "pairs",
    "truth-values",
    "primitive-recursive-functions",
    "fixpoints",
    "minimization",
    "partial-recursive-functions",
    "lambda-definable-recursive",
]
chapter_label = "lam:rep:chap"
available.add(chapter_label)
files = []
for name in imports:
    path = folder / (name + ".tex")
    content = selected(path.read_text(encoding="utf-8"))
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and file_id.group(1) == "lam", path
    parts = list(file_id.groups())
    expected_ids = {
        "arithmetical-functions": ["lam", "rep", "arf"],
        "lambda-definable-recursive": ["lam", "dfl", "ldr"],
    }
    if name in expected_ids:
        assert parts == expected_ids[name], path
    else:
        assert parts[:2] == ["lam", "ldf"], path
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(
        prefix + ":" + item
        for item in re.findall(r"\\ollabel\{([^}]+)\}", content)
    )
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
external.difference_update(available)

editorial = re.search(r"\\begin\{editorial\}(.*?)\\end\{editorial\}", driver, re.S)
assert editorial, "Preserve the chapter's translated editorial caveat"
chunks = [
    r"\chapter{लॅम्डा-परिभाष्यता}\label{" + chapter_label + "}",
    "\\begin{quote}\n" + editorial.group(1).strip() + "\n\\end{quote}",
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(
        r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1
    )
    assert removed == 1, name
    content = replace_tokens(content)
    content = convert_section(content, prefix)
    content = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda match: r"\label{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(
        r"\\olref((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda match: references(match, parts),
        content,
    )
    content = re.sub(
        r"\\Olref\{([^}]+)\}",
        lambda match: r"\ref{" + prefix + ":" + match.group(1) + "}",
        content,
    )
    content = re.sub(
        r"\\(?:c|C)ref\{([^}]+)\}",
        lambda match: " आणि ".join(
            r"\ref{" + item.strip() + "}" for item in match.group(1).split(",")
        ),
        content,
    )
    content = re.sub(
        r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tag_references,
        content,
        flags=re.S,
    )
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref)",
        content,
    )
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(notes_marker) == 1
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_note = r"""
\item \textbf{OLINC-114--OLINC-128}: लॅम्डा-परिभाष्यता
प्रकरणातील सूत्रे, युक्तिवाद-संख्या, न्यूनीकरणाच्या पायऱ्या,
पुनरावर्तन आणि स्थिरबिंदू संयोजकांच्या नोंदी स्वतंत्र
स्रोत-नोंदीत आहेत. जिथे गणिती अर्थ स्पष्ट आहे तिथे
मराठीतील स्थानिक दुरुस्त्या नोंदवल्या आहेत.
क्रमगुणिताच्या स्व-आदेशानंतरच्या एका प्रदर्शित सूत्राची
मांडणी पुढील गणिती व टंकन-परीक्षणासाठी खुली आहे.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_note + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
out = re.sub(
    r"\\readerexternalref\{([^}]+)\}",
    lambda match: (
        r"\ref{" + match.group(1) + "}"
        if match.group(1) in available
        else match.group(0)
    ),
    out,
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[372:382]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append(
        {
            "unit_id": row["unit_id"],
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
assert len(inputs) == 379 and inputs[-1]["unit_id"] == "OLP-0382"
assert out.count(r"\chapter{") == 38
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 333
assert "379 स्रोत-एकके आणि 333 वाचक-विभाग" in out
assert "!!" not in out
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="379 source units, 333 reader sections, thirty-eight complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", [])
    + [f"OLINC-{index:03d}" for index in range(114, 129)],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    )
    + ["OLP-0373"],
    reader_file_id_exceptions={
        **prior.get("reader_file_id_exceptions", {}),
        "OLP-0375": "lam/rep/arf (frozen source identifier retained)",
        "OLP-0382": "lam/dfl/ldr (frozen source identifier retained)",
    },
)
(BUILD / "INPUTS.json").write_text(
    json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "prepared": "build/core/openlogic-mr-core.tex",
            "units": len(inputs),
            "sections": 333,
            "chapters": 38,
            "external_references": len(external),
            "sha256": hashlib.sha256(out.encode()).hexdigest(),
        },
        ensure_ascii=False,
    )
)
