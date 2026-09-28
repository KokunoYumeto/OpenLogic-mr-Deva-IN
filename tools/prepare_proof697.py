"""Assemble five completed proof-theory chapters for guarded TeX diagnostics."""
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
    prior = runpy.run_path(str(ROOT / "tools/prepare_proof684.py"))
helpers = prior["helpers"]
base = (BUILD / "openlogic-mr-proof.tex").read_text(encoding="utf-8")
assert base.endswith("\\end{document}\n")
base = base.removesuffix("\\end{document}\n")
assert base.count(r"\usepackage{microtype}") == 1
base = base.replace(
    r"\usepackage{microtype}",
    r"\usepackage{cleveref}" + "\n" +
    r"\crefname{lem}{पूर्वप्रमेय}{पूर्वप्रमेये}" + "\n" +
    r"\usepackage{microtype}",
    1,
)

folder = ROOT / "mr/content/proof-theory/propositions-as-types"
driver_path = folder / "propositions-as-types.tex"
driver = helpers["selected"](driver_path.read_text(encoding="utf-8"))
assert r"\olchapter{int}{pty}{विधाने म्हणजे प्रकार}" in driver
active_driver = "\n".join(
    line for line in driver.splitlines() if not line.lstrip().startswith("%")
)
imports = re.findall(r"\\olimport\{([^}]+)\}", active_driver)
assert imports == [
    "introduction", "proof-terms", "proofs-to-terms", "terms-to-proofs",
    "types", "reduction", "type-preservation", "normalization",
]
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", active_driver, re.S)
assert editorial and "अतिशय प्रायोगिक" in editorial.group()

rule_paths = {
    "proof-terms": folder / "rules-tN2.tex",
    "types": folder / "rules-tN3.tex",
}
rule_content = {}
for section, path in rule_paths.items():
    raw = helpers["selected"](path.read_text(encoding="utf-8"))
    rule_content[section] = helpers["ns"]["strip_wrapper"](raw)
assert rule_content["proof-terms"].count(r"\ollabel{tab:tN2ip}") == 1
assert rule_content["types"].count(r"\ollabel{tab:tN3ip}") == 1

files = []
available = set(re.findall(r"\\label\{([^}]+)\}", base))
available.add("int:pty:chap")
for name in imports:
    path = folder / (name + ".tex")
    raw = helpers["selected"](path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1, 2) == ("int", "pty"), name
    parts = list(match.groups())
    prefix = ":".join(parts)
    if name in rule_paths:
        subfile_name = rule_paths[name].stem
        assert raw.count(r"\subfile{" + subfile_name + "}") == 1
        raw = raw.replace(r"\subfile{" + subfile_name + "}", rule_content[name])
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


chunks = [r"\chapter{विधाने म्हणजे प्रकार}\label{int:pty:chap}", editorial.group()]
for name, path, raw, parts, prefix in files:
    content = helpers["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    local_tokens = {
        "proof": "सिद्धता", "height": "उंची", "depth": "खोली",
        "derivation": "निष्पत्ती", "provable": "सिद्धतायोग्य",
        "prove": "सिद्ध", "proving": "सिद्ध करणे",
        "constant": "स्थिरांक", "element": "घटक",
        "introduction": "परिचय", "elimination": "निरसन",
    }
    content = content.replace(r"\usetoken{P}{derivation}", "निष्पत्ती")
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
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|olimport|subfile|usetoken)", active), name
    chunks.append(content)

out = base + "\n".join(chunks) + "\n" + r"\end{document}" + "\n"
assert out.count(r"\chapter{") == 5
assert len(re.findall(r"\\section\{", out)) == 30
assert out.count(r"\end{document}") == 1
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
assert r"\label{int:pty:ter:tab:tN2ip}" in out
assert r"\label{int:pty:typ:tab:tN3ip}" in out
tex = BUILD / "openlogic-mr-proof.tex"
tex.write_text(out, encoding="utf-8", newline="\n")
prior_inputs = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
inputs = {
    "schema": "openlogic-local-proof-reader-input/1",
    "through_unit": "OLP-0697",
    "chapter_drivers": prior_inputs["chapter_drivers"] + ["OLP-0690"],
    "chapter_imports": {
        **prior_inputs["chapter_imports"],
        "propositions-as-types": imports,
    },
    "paths": prior_inputs["paths"] + [
        driver_path.relative_to(ROOT).as_posix(),
        *[path.relative_to(ROOT).as_posix() for _, path, _, _, _ in files],
        *[path.relative_to(ROOT).as_posix() for path in rule_paths.values()],
    ],
    "sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
    "note": "Local five-chapter diagnostic input. The two term-rule tables are inlined, the commented sequent-natural-deduction import is excluded, and the source editorial warning is retained.",
}
(BUILD / "INPUTS.json").write_text(
    json.dumps(inputs, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8", newline="\n",
)
print(json.dumps({
    "prepared": str(tex), "chapters": 5, "sections": 30,
    "bytes": len(out.encode("utf-8")), "sha256": inputs["sha256"],
}, ensure_ascii=False))
