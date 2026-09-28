"""Assemble six completed proof-theory chapters for one guarded TeX check."""
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
    prior = runpy.run_path(str(ROOT / "tools/prepare_proof697.py"))
helpers = prior["helpers"]
base = (BUILD / "openlogic-mr-proof.tex").read_text(encoding="utf-8")
assert base.endswith("\\end{document}\n")
base = base.removesuffix("\\end{document}\n")
assert base.count(r"\usepackage{microtype}") == 1
base = base.replace(
    r"\usepackage{microtype}",
    r"\usepackage{longtable}" + "\n" + r"\usepackage{microtype}",
    1,
)

local_tokens = {
    "proof": "सिद्धता", "height": "उंची", "depth": "खोली",
    "derivation": "निष्पत्ती", "provable": "सिद्धतायोग्य",
    "prove": "सिद्ध", "proving": "सिद्ध करणे",
    "constant": "स्थिरांक", "element": "घटक",
    "introduction": "परिचय", "elimination": "निरसन",
    "hp": "उंची जपून",
}

def expand_tokens(content):
    content = content.replace(r"\usetoken{P}{proof}", "सिद्धता")
    content = re.sub(
        r"!!(?:\^?a|\^)?\{(" + "|".join(local_tokens) + r")\}(?:s|d)?",
        lambda m: local_tokens[m.group(1)], content,
    )
    return helpers["replace_tokens"](content)

def table_content(path, prefix):
    content = helpers["ns"]["strip_wrapper"](helpers["selected"](path.read_text(encoding="utf-8")))
    content = expand_tokens(content)
    content = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content,
    )
    assert not re.search(r"\\(?:subfile|ollabel|olref|olfileid)\b|!!", content)
    return content

# The prior five-chapter input has two natural-deduction tables that were
# still represented as subfiles at the preceding diagnostic checkpoint.
nat_folder = ROOT / "mr/content/proof-theory/natural-deduction"
nat_rules = {
    "rules-N1": (nat_folder / "rules-N1.tex", "pt:nat:rp"),
    "rules-N2": (nat_folder / "rules-N2.tex", "pt:nat:seq"),
}
for name, (path, prefix) in nat_rules.items():
    marker = r"\subfile{" + name + "}"
    assert base.count(marker) == 1, name
    base = base.replace(marker, table_content(path, prefix), 1)

folder = ROOT / "mr/content/proof-theory/sequent-calculus"
driver_path = folder / "sequent-calculus.tex"
driver = helpers["selected"](driver_path.read_text(encoding="utf-8"))
assert r"\olchapter{pt}{seq}{क्रमवर्ती कलन}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction", "rules-proofs", "proof-examples",
    "interpretation-rules", "quantifiers", "admissible-derivable",
    "invertibility", "translations",
]
rule_paths = {
    "introduction": ["rules-G1c", "rules-G3c"],
    "interpretation-rules": ["rules-G2c"],
}
files = []
available = set(re.findall(r"\\label\{([^}]+)\}", base))
available.add("pt:seq:chap")
for name in imports:
    path = folder / (name + ".tex")
    raw = helpers["selected"](path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1, 2) == ("pt", "seq"), name
    parts = list(match.groups())
    prefix = ":".join(parts)
    if name == "introduction":
        conditional = r"\oliflabeldef{fol:seq::chap}"
        assert raw.count(conditional) == 1
        start = raw.index(conditional)
        end = raw.index("}{}", start) + 3
        raw = raw[:start] + raw[end:]
    for rule_name in rule_paths.get(name, []):
        rule = folder / (rule_name + ".tex")
        marker = r"\subfile{" + rule_name + "}"
        assert raw.count(marker) == 1
        raw = raw.replace(marker, table_content(rule, prefix), 1)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", raw))
    available.update(re.findall(r"\\label\{([^}]+)\}", raw))
    files.append((name, path, raw, parts, prefix))

def reference(match, parts):
    options = re.findall(r"\[([^]]*)\]", match.group(1))
    assert len(options) <= 3
    key_parts = parts.copy()
    if options:
        key_parts[3 - len(options):] = options
    label = ":".join(key_parts) + ":" + match.group(2)
    return (r"\ref{" if label in available else r"\readerexternalref{") + label + "}"

chunks = [r"\chapter{क्रमवर्ती कलन}\label{pt:seq:chap}"]
for name, path, raw, parts, prefix in files:
    content = helpers["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    content = expand_tokens(content)
    content = helpers["convert_section"](content, prefix)
    content = re.sub(
        r"\\ollabel\{([^}]+)\}",
        lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content,
    )
    content = re.sub(
        r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}",
        lambda m: reference(m, parts), content,
    )
    active = "\n".join(line for line in content.splitlines() if not line.lstrip().startswith("%"))
    assert "!!" not in active, (name, set(re.findall(r"!![^\s,.)]*", active)))
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|olimport|subfile|oliflabeldef|usetoken)\b", active), name
    chunks.append(content)

out = base + "\n".join(chunks) + "\n" + r"\end{document}" + "\n"
assert out.count(r"\chapter{") == 6
assert len(re.findall(r"\\section\{", out)) == 38
assert out.count(r"\end{document}") == 1
assert not re.search(r"\\(?:subfile|oliflabeldef)\b", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
out = re.sub(
    r"\\readerexternalref\{([^}]+)\}",
    lambda m: (r"\ref{" if m.group(1) in labels else r"\readerexternalref{") + m.group(1) + "}",
    out,
)
tex = BUILD / "openlogic-mr-proof.tex"
tex.write_text(out, encoding="utf-8", newline="\n")
prior_inputs = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
rule_files = [path for path, _ in nat_rules.values()]
rule_files += [folder / (name + ".tex") for names in rule_paths.values() for name in names]
inputs = {
    "schema": "openlogic-local-proof-reader-input/1",
    "through_unit": "OLP-0713",
    "chapter_drivers": prior_inputs["chapter_drivers"] + ["OLP-0712"],
    "chapter_imports": {**prior_inputs["chapter_imports"], "sequent-calculus": imports},
    "paths": prior_inputs["paths"] + [
        *[path.relative_to(ROOT).as_posix() for path in rule_files],
        driver_path.relative_to(ROOT).as_posix(),
        *[path.relative_to(ROOT).as_posix() for _, path, _, _, _ in files],
    ],
    "sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
    "note": "Local six-chapter diagnostic input. Includes previously pending N1/N2 tables and active G1c/G3c/G2c rule tables; FOL-LK optional cross-reference is excluded because that chapter is outside this input.",
}
(BUILD / "INPUTS.json").write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"prepared": str(tex), "chapters": 6, "sections": 38,
                  "bytes": len(out.encode("utf-8")), "sha256": inputs["sha256"]}, ensure_ascii=False))
