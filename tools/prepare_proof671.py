"""Assemble cut elimination and natural deduction for a local proof-theory TeX check."""
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
    prior = runpy.run_path(str(ROOT / "tools/prepare_cut661.py"))
helpers = prior["helpers"]
base = (BUILD / "openlogic-mr-proof.tex").read_text(encoding="utf-8")
assert base.endswith("\\end{document}\n")
base = base.removesuffix("\\end{document}\n")
old_title = r"\hypersetup{pdftitle={मुक्त तर्कशास्त्र: कट-निर्मूलन, स्थानिक निदान}}"
new_title = r"\hypersetup{pdftitle={मुक्त तर्कशास्त्र: कट-निर्मूलन आणि नैसर्गिक निगमन, स्थानिक निदान}}"
assert base.count(old_title) == 1
base = base.replace(old_title, new_title, 1)

folder = ROOT / "mr/content/proof-theory/natural-deduction"
driver = helpers["selected"]((folder / "natural-deduction.tex").read_text(encoding="utf-8"))
assert r"\olchapter{pt}{nat}{नैसर्गिक निगमन}" in driver
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "introduction", "rules-proofs", "sequents", "quantifiers", "grafting",
    "translation-G2i", "translation-N2i",
]

files = []
available = set(re.findall(r"\\label\{([^}]+)\}", base))
available.add("pt:nat:chap")
for name in imports:
    path = folder / (name + ".tex")
    raw = helpers["selected"](path.read_text(encoding="utf-8"))
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match and match.group(1, 2) == ("pt", "nat"), name
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


chunks = [r"\chapter{नैसर्गिक निगमन}\label{pt:nat:chap}"]
for name, path, raw, parts, prefix in files:
    content = helpers["ns"]["strip_wrapper"](raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
    assert removed == 1, name
    local_tokens = {
        "proof": "सिद्धता", "height": "उंची", "derivation": "निष्पत्ती",
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
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|olimport)", active), name
    chunks.append(content)

out = base + "\n".join(chunks) + "\n" + r"\end{document}" + "\n"
assert out.count(r"\chapter{") == 2
assert len(re.findall(r"\\section\{", out)) == 12
assert out.count(r"\end{document}") == 1
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels))
tex = BUILD / "openlogic-mr-proof.tex"
tex.write_text(out, encoding="utf-8", newline="\n")
prior_inputs = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))
inputs = {
    "schema": "openlogic-local-proof-reader-input/1",
    "through_unit": "OLP-0671",
    "chapter_drivers": ["OLP-0657", "OLP-0664"],
    "chapter_imports": {
        "cut-elimination": prior_inputs["section_imports"],
        "natural-deduction": imports,
    },
    "paths": prior_inputs["paths"] + [path.relative_to(ROOT).as_posix() for _, path, _, _, _ in files],
    "sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
    "note": "Local two-chapter diagnostic input; excludes separately translated standalone proof fragments and tables.",
}
(BUILD / "INPUTS.json").write_text(
    json.dumps(inputs, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8", newline="\n",
)
print(json.dumps({
    "prepared": str(tex), "chapters": 2, "sections": 12,
    "bytes": len(out.encode("utf-8")), "sha256": inputs["sha256"],
}, ensure_ascii=False))
