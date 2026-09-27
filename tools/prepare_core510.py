"""Assemble 54 complete Marathi chapters through OLP-0510 without TeX."""

import hashlib
import json
import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "core"
prior_namespace = runpy.run_path(str(ROOT / "tools" / "prepare_core502.py"))
base = (BUILD / "openlogic-mr-core.tex").read_text(encoding="utf-8")
prior = json.loads((BUILD / "INPUTS.json").read_text(encoding="utf-8"))

assert base.count("त्रेपन्न संपूर्ण प्रकरणे") == 1
base = base.replace("त्रेपन्न संपूर्ण प्रकरणे", "चोपन्न संपूर्ण प्रकरणे", 1)
old_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0502, एकूण 499 स्रोत-एकके "
    "आणि 434 वाचक-विभाग. उर्वरित 223"
)
new_coverage = (
    "मूळ 722 स्रोत-एककांपैकी OLP-0004 ते OLP-0510, एकूण 507 स्रोत-एकके "
    "आणि 441 वाचक-विभाग. उर्वरित 215"
)
assert base.count(old_coverage) == 1
base = base.replace(old_coverage, new_coverage, 1)
card_anchor = r"\newcommand{\cardle}[2]{#1 \preceq #2}"
assert base.count(card_anchor) == 1
assert r"\newcommand{\card}[1]" not in base
base = base.replace(
    card_anchor,
    r"\newcommand{\card}[1]{\left|#1\right|}" + "\n" + card_anchor,
    1,
)
p_fmla_anchor = r"\NewDocumentCommand{\sFmla}{m m o}{\ensuremath{\IfNoValueTF{#3}{}{#3\,}\hbox to.8em{\ensuremath{#1}\hfil} #2}}"
assert base.count(p_fmla_anchor) == 1
assert r"\NewDocumentCommand{\pFmla}" not in base
base = base.replace(
    p_fmla_anchor,
    p_fmla_anchor + "\n" +
    r"\NewDocumentCommand{\pFmla}{m m m}{\ensuremath{\hskip 3em{\llap{$#3$}\,}\hbox to1.3em{\ensuremath{#1}\hfil} #2}}",
    1,
)

selected_modal = prior_namespace["selected_modal"]
replace_tokens = prior_namespace["replace_tokens"]
strip_wrapper = prior_namespace["strip_wrapper"]
references = prior_namespace["references"]
tag_references = prior_namespace["tag_references"]
available = prior_namespace["available"]
external = prior_namespace["external"]
convert_section = prior_namespace["convert_section"]

folder = ROOT / "mr/content/intuitionistic-logic/soundness-completeness"
driver = selected_modal((folder / "soundness-completeness.tex").read_text(encoding="utf-8"))
assert r"\olchapter{int}{sc}{निर्दोषता आणि संपूर्णता}" in driver
editorial = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", driver, re.S)
assert editorial
imports = re.findall(r"\\olimport\{([^}]+)\}", driver)
assert imports == [
    "soundness-axd",
    "soundness-nd",
    "lindenbaum",
    "canonical-model",
    "truth-lemma",
    "completeness-thm",
    "decidability",
]
available.add("int:sc:chap")
files = []
reader_note_count = 0
for name in imports:
    path = folder / (name + ".tex")
    raw = path.read_text(encoding="utf-8")
    if name == "decidability":
        note_pattern = r"(?m)^[ \t]*%READERNOTE\{(.*)\}$"

        def render_reader_note(match):
            global reader_note_count
            reader_note_count += 1
            assert match.group(1).startswith("OLINC-226:")
            return (
                r"\begin{quote}\small\textbf{स्रोतसिद्धतेची मर्यादा.} "
                + match.group(1)
                + r"\end{quote}"
            )

        raw = re.sub(note_pattern, render_reader_note, raw)
    content = selected_modal(raw)
    file_id = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert file_id and list(file_id.groups())[:2] == ["int", "sc"], path
    parts = list(file_id.groups())
    prefix = ":".join(parts)
    available.add(prefix + ":sec")
    available.update(prefix + ":" + item for item in re.findall(r"\\ollabel\{([^}]+)\}", content))
    available.update(re.findall(r"\\label\{([^}]+)\}", content))
    files.append((name, content, parts, prefix))
assert reader_note_count == 1
external.difference_update(available)

chunks = [
    r"\chapter{निर्दोषता आणि संपूर्णता}\label{int:sc:chap}",
    replace_tokens(editorial.group()),
]
for name, raw, parts, prefix in files:
    content = strip_wrapper(raw)
    content, removed = re.subn(r"\\olfileid\{[^}]+\}\{[^}]+\}\{[^}]+\}", "", content, count=1)
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
        lambda match: " आणि ".join(r"\ref{" + item.strip() + "}" for item in match.group(1).split(",")),
        content,
    )
    content = re.sub(r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}", tag_references, content, flags=re.S)
    assert "!!" not in content, (name, re.findall(r"!!.{0,35}", content)[:8])
    leftover = re.search(
        r"\\(?:iftag|tagitem|tagblock|tagenumerate|tagprob|tagendprob|"
        r"probtag|usetoken|printtoken|Article|article|olref|Olref|ollabel|"
        r"olsection|olfileid|tagrefs|Cref|cref)",
        content,
    )
    assert not leftover, (name, leftover.group(0) if leftover else "")
    chunks.append(content)

notes_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert base.count(notes_marker) == 1
before, notes = base.split(notes_marker, 1)
notes = notes_marker + notes
new_notes = r"""
\item \textbf{OLINC-220}: स्वयंसिद्धकीय निर्दोषतेच्या
गृहीतक-प्रसंगात मूळ इंग्रजीतील पूर्ति-सूत्राला
जादा \(\Gamma\) घटक आहे; मराठीत \(A_n\)
ची पूर्ति योग्य रूपात लिहिली आहे.
\item \textbf{OLINC-221--222}: नैसर्गिक
निगमनाच्या निर्दोषता-सिद्धतेत संधियोगाच्या
निष्कर्षात चुकीची सूत्रे, तसेच विकल्पयोगाच्या
प्रसंगात जगाचे स्थान आणि दोन एकघटक संच
चुकले आहेत; मराठीत संदर्भाशी जुळणारी
रूपे वापरली आहेत.
\item \textbf{OLINC-223--224}: लिंडेनबाउमच्या
रचनेतील निवडीसाठी परिमित आधीच्या
निर्देशांकांचा युक्तिवाद स्पष्ट केला आहे;
कॅनॉनिकल प्रतिमानातील एकस्वनिकतेसाठी
आगमनाचा विस्तार-लांबी हा निर्देशांक
स्पष्ट केला आहे.
\item \textbf{OLINC-225}: सत्यता पूर्वप्रमेयाच्या
प्रस्तावनेत प्रारंभीच्या \(\Delta\) ऐवजी
त्या जगाचा \(\Delta(\sigma)\) अभाज्य संच
उल्लेखिला आहे.
\item \textbf{OLINC-227}: आधीच्या मोडल
संपूर्णता प्रकरणात मूल्यांकन \(V^\Sigma\)
पुढील गद्य कंस चुकून गणितात गेला होता;
मराठीत कंस गणिताबाहेर ठेवला आहे.
\item \textbf{OLINC-226}: निर्णेयतेच्या
स्रोतसिद्धतेत जगांचे केवळ विधानचरांच्या
सत्यसंचांवर आधारित भागाकार सशर्त
सूत्राची सत्यता जपत नाही. मूळ दोन
जगे असंबद्ध असताना नव्या उपसंच-क्रमाने
त्यांत प्राप्यता निर्माण होऊ शकते.
विभागात दिसणारी टीप हा पुराव्यातील
दोष स्पष्ट करते; प्रमेय खोटे ठरवत नाही.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
"""
assert notes.count(r"\end{enumerate}") >= 1
notes = notes.replace(r"\end{enumerate}", new_notes + r"\end{enumerate}", 1)
out = before + "\n".join(chunks) + "\n" + notes
# Selecting the non-Diamond tag branch can leave a blank paragraph inside
# align*, which TeX rejects even though the remaining K axiom is well formed.
normal_k_align_gap = (
    r"\tag{\Ax{K}} & \Box(p \lif q) \lif (\Box p \lif \Box q),"
    + "\n\n  "
    + r"\end{align*}"
)
if normal_k_align_gap in out:
    assert out.count(normal_k_align_gap) == 1
    out = out.replace(
        normal_k_align_gap,
        normal_k_align_gap.replace("\n\n  ", "\n  "),
        1,
    )
else:
    # With both modal tags enabled the Dual axiom follows K in this display.
    assert out.count(r"\tag{\Dual} & \Diamond p \liff \lnot\Box\lnot p") == 1
# Conditional branch selection also leaves empty TeX paragraphs immediately
# inside several display-math environments. Paragraph tokens are illegal there.
display_pattern = re.compile(r"\\\[(.*?)\\\]", re.S)
display_blank_repairs = 0


def strip_display_blank_paragraphs(match):
    global display_blank_repairs
    body, count = re.subn(r"(?m)^[ \t]*\n", "", match.group(1))
    display_blank_repairs += count
    return r"\[" + body + r"\]"


out = display_pattern.sub(strip_display_blank_paragraphs, out)
assert display_blank_repairs >= 9
for original, projection in prior["reader_symbol_projections"].items():
    out = out.replace(original, projection)
out = re.sub(
    r"\\readerexternalref\{([^}]+)\}",
    lambda match: r"\ref{" + match.group(1) + "}" if match.group(1) in available else match.group(0),
    out,
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"

manifest = [
    json.loads(line)
    for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
inputs = list(prior["input_units"])
for row in manifest[502:510]:
    path = ROOT / "mr" / row["source_path"]
    inputs.append({
        "unit_id": row["unit_id"],
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
assert len(inputs) == 507 and inputs[-1]["unit_id"] == "OLP-0510"
assert out.count(r"\chapter{") == 54
assert len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)) == 441
assert "507 स्रोत-एकके आणि 441 वाचक-विभाग" in out
assert "स्रोतसिद्धतेची मर्यादा" in out
assert "!!" not in out and not re.search(r"![A-Z]", out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), "Cumulative reader labels must be unique"

(BUILD / "openlogic-mr-core.tex").write_text(out, encoding="utf-8", newline="\n")
prior.update(
    input_units=inputs,
    scope="507 source units, 441 reader sections, fifty-four complete chapters",
    external_reference_labels=sorted(external),
    source_issue_ids_added=prior.get("source_issue_ids_added", []) + [
        "OLINC-220", "OLINC-221", "OLINC-222", "OLINC-223",
        "OLINC-224", "OLINC-225", "OLINC-226", "OLINC-227",
    ],
    chapter_driver_units_not_rendered_as_sections=prior.get(
        "chapter_driver_units_not_rendered_as_sections", []
    ) + ["OLP-0503"],
)
(BUILD / "INPUTS.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "prepared": "build/core/openlogic-mr-core.tex",
    "units": len(inputs),
    "sections": 441,
    "chapters": 54,
    "external_references": len(external),
    "sha256": hashlib.sha256(out.encode()).hexdigest(),
}, ensure_ascii=False))
