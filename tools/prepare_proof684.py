"""Assemble four completed proof-theory chapters for guarded TeX diagnostics."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/proof"
with redirect_stdout(StringIO()):
    prior = runpy.run_path(str(ROOT / "tools/prepare_proof678.py"))
helpers = prior["helpers"]
base = (BUILD / "openlogic-mr-proof.tex").read_text(encoding="utf-8")
assert base.endswith("\\end{document}\n")
base = base.removesuffix("\\end{document}\n")

folder = ROOT / "mr/content/proof-theory/proof-search"
driver_path = folder / "proof-search.tex"
driver = helpers["selected"](driver_path.read_text(encoding="utf-8"))
assert r"\olchapter{pt}{ps}{सिद्धता-शोध}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == ["introduction", "search-algorithm", "completeness", "tableaux"]

rule_path = folder / "rules-Tc.tex"
rule_raw = helpers["selected"](rule_path.read_text(encoding="utf-8"))
rule_content = helpers["ns"]["strip_wrapper"](rule_raw)
assert rule_content.count(r"\ollabel{tab:Tc}") == 1
assert not re.search(r"\\(?:documentclass|begin\{document\}|end\{document\})", rule_content)

files = []
available = set(re.findall(r"\\label\{([^}]+)\}", base))
available.add("pt:ps:chap")
for name in imports:
    path = folder / (name + ".tex")
    raw = helpers["selected"](path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1, 2) == ("pt", "ps"), name
    parts = list(match.groups())
    prefix = ":".join(parts)
    if name == "tableaux":
        assert raw.count(r"\subfile{rules-Tc}") == 1
        raw = raw.replace(r"\subfile{rules-Tc}", rule_content)
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


chunks = [r"\chapter{सिद्धता-शोध}\label{pt:ps:chap}"]
for name, path, raw, parts, prefix in files:
    content = helpers["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    local_tokens = {
        "proof": "सिद्धता", "height": "उंची", "depth": "खोली", "derivation": "निष्पत्ती",
        "provable": "सिद्धतायोग्य", "prove": "सिद्ध", "proving": "सिद्ध करणे",
        "constant": "स्थिरांक", "element": "घटक",
        "introduction": "परिचय", "elimination": "निरसन",
    }
    content = content.replace(r"\usetoken{P}{proof}", "सिद्धता")
    content = re.sub(
        r"!!(?:\^?a|\^)?\{(" + "|".join(local_tokens) + r")\}(?:s|d)?",
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
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|olimport|subfile)", active), name
    chunks.append(content)

out = base + "\n".join(chunks) + "\n" + r"\end{document}" + "\n"
assert out.count(r"\chapter{") == 4
assert len(re.findall(r"\\section\{", out)) == 22
assert out.count(r"\end{document}") == 1
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
assert r"\label{pt:ps:tab:tab:Tc}" in out
tex = BUILD / "openlogic-mr-proof.tex"
tex.write_text(out, encoding="utf-8", newline="\n")
prior_inputs = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
inputs = {
    "schema": "openlogic-local-proof-reader-input/1",
    "through_unit": "OLP-0684",
    "chapter_drivers": prior_inputs["chapter_drivers"] + ["OLP-0681"],
    "chapter_imports": {
        **prior_inputs["chapter_imports"],
        "proof-search": imports,
    },
    "paths": prior_inputs["paths"] + [
        driver_path.relative_to(ROOT).as_posix(),
        *[path.relative_to(ROOT).as_posix() for _, path, _, _, _ in files],
        rule_path.relative_to(ROOT).as_posix(),
    ],
    "sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
    "note": "Local four-chapter diagnostic input; includes the Tc table in the tableaux section and excludes separately translated standalone proof fragments.",
}
(BUILD / "INPUTS.json").write_text(
    json.dumps(inputs, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8", newline="\n",
)
print(json.dumps({
    "prepared": str(tex), "chapters": 4, "sections": 22,
    "bytes": len(out.encode("utf-8")), "sha256": inputs["sha256"],
}, ensure_ascii=False))
