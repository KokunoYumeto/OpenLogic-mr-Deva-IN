"""Assemble one full Marathi diagnostic reader from reviewed modular sources."""
import hashlib
import json
import re
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from complete_wrapper_notes import preserve_notes
from complete_reader_notes import preserve_reader_notes, project_note, verify_reader_notes

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
BUILD.mkdir(parents=True, exist_ok=True)

# These existing assemblers encode the reviewed source projections and keep
# their translated sections reproducible. Neither invokes TeX.
with redirect_stdout(StringIO()):
    core_ns = runpy.run_path(str(ROOT / "tools/prepare_core642.py"))
    proof_ns = runpy.run_path(str(ROOT / "tools/prepare_proof713.py"))
helpers = core_ns["helpers"]
core = (ROOT / "build/core/openlogic-mr-core.tex").read_text(encoding="utf-8")
proof = (ROOT / "build/proof/openlogic-mr-proof.tex").read_text(encoding="utf-8")
manifest = [json.loads(line) for line in (ROOT / "provenance/SOURCE_MANIFEST.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
by_unit = {row["unit_id"]: row for row in manifest}
assert len(by_unit) == 722

core_preamble, split, core_body = core.partition(r"\begin{document}")
proof_preamble, split_proof, proof_body = proof.partition(r"\begin{document}")
assert split and split_proof
proof_body, proof_end, proof_tail = proof_body.rpartition(r"\end{document}")
assert proof_end and not proof_tail.strip()
core_body, core_end, core_tail = core_body.rpartition(r"\end{document}")
assert core_end and not core_tail.strip()

extra_preamble = [
    r"\usepackage{longtable}",
    r"\usepackage{cleveref}",
    r"\usepackage{xurl}",
    r"\tikzset{initial text=सुरुवात}",
    r"\renewcommand{\tablename}{तक्ता}",
    r"\providecommand{\gitissue}[1]{\href{https://github.com/OpenLogicProject/OpenLogic/issues/#1}{मूळ स्रोताची नोंद #1}}",
    r"\crefname{lem}{पूर्वप्रमेय}{पूर्वप्रमेये}",
    r"\crefname{table}{तक्ता}{तक्ते}",
    r"\Crefname{table}{तक्ता}{तक्ते}",
    # The three-level number 67.10.1 needs more room in the contents.
    r"\makeatletter\renewcommand*\l@subsection{\@dottedtocline{2}{3.8em}{4.2em}}\makeatother",
    r"\newcommand{\lnand}{\mathbin{\uparrow}}",
    r"\newcommand{\lnor}{\mathbin{\downarrow}}",
    r"\providecommand{\CutCS}{\ensuremath{\mathrm{Cut}_{\mathrm{CS}}}}",
    r"\providecommand{\maeh}[2]{{#1\mathrel{;}#2}}",
    r"\providecommand{\pheight}[1]{\fn{ht}(#1)}",
    r"\providecommand{\depth}[1]{\fn{dp}(#1)}",
    r"\providecommand{\cheight}[1]{\fn{ch}(#1)}",
    r"\providecommand{\cutr}[1]{\fn{cr}(#1)}",
    r"\providecommand{\cutrank}[1]{\fn{cr}(#1)}",
    r"\NewDocumentCommand{\typeof}{m m}{#1^{#2}}",
    r"\NewDocumentCommand{\andi}{m m}{\tuple{#1, #2}}",
    r"\NewDocumentCommand{\ande}{m m}{\fn{p}_{#1}(#2)}",
    r"\NewDocumentCommand{\ori}{m m m}{\fn{in}_{#1}^{#2}(#3)}",
    r"\NewDocumentCommand{\ore}{m m m m m}{\fn{case}(#1, #2.#3, #4.#5)}",
    r"\NewDocumentCommand{\pair}{m m}{\tuple{#1,#2}}",
    r"\NewDocumentCommand{\proj}{m m}{\pi_{#1}(#2)}",
    r"\NewDocumentCommand{\dcase}{m m m m m}{\delta\, #1\, #2.#3\, #4.#5}",
    r"\NewDocumentCommand{\inj}{o m m}{\IfNoValueTF{#1}{\iota_{#2}(#3)}{\iota_{#2}^{#1}(#3)}}",
    r"\NewDocumentCommand{\abort}{m m}{\varepsilon^{#1}(#2)}",
    r"\NewDocumentCommand{\maxrank}{m}{\fn{mr}(#1)}",
]
for command in extra_preamble:
    if command not in core_preamble:
        core_preamble += command + "\n"
core_preamble = re.sub(
    r"\\hypersetup\{pdftitle=\{[^\n]*?\},pdfauthor=\{[^\n]*?\}\}",
    lambda _: r"\hypersetup{pdftitle={मुक्त तर्कशास्त्र: संपूर्ण मराठी आवृत्ती},pdfauthor={Open Logic Project; OpenAI Codex: GPT-5.6 Sol, GPT-6 Sol; corrective review GPT-6.1 Sol; Ultra effort}}",
    core_preamble,
    count=1,
)

titlepage = r"""\begin{titlepage}
\vspace*{2cm}
{\Huge\bfseries मुक्त तर्कशास्त्र\par}
\vspace{1cm}
{\Large ओपन लॉजिक प्रकल्पाची संपूर्ण मराठी आवृत्ती\par}
\vspace{1cm}
मूळ इंग्रजी मजकूर: Open Logic Project.\par
सर्व 722 स्रोत-एककांचे भाषांतर केले आहे. मुख्य अध्यायांबरोबर
पर्यायी आणि मूळ मार्गाबाहेरील विभाग पुढील पूरक भागात दिले आहेत.\par
यंत्रानुवाद, दुरुस्ती आणि तपासणी: OpenAI Codex —
GPT-5.6 Sol आणि GPT-6 Sol, दोन्ही Ultra effort.\par
दुरुस्ती-पुनरावलोकन: GPT-6.1 Sol, Ultra effort.\par
स्रोताशी तुलना, शब्दनिर्णय आणि यांत्रिक तपासण्या केल्या आहेत.
स्वतंत्र मानवी संपादनाचा दावा नाही.
काही तांत्रिक संज्ञा तज्ज्ञ-पुनरावलोकनासाठी खुल्या आहेत.\par
सर्व 722 एककांच्या 6,644 जुळवलेल्या मजकूरखंडांची नोंद आहे.
अधिक तपशीलवार शब्दनिर्णय-पुनरावलोकन 281 एककांपुरते आहे;
हा तपशीलवार पुनरावलोकनाचा दावा संपूर्ण ग्रंथासाठी केलेला नाही.\par
मूळ मजकूर आणि हे रूपांतर: Creative Commons Attribution 4.0.
मूळ घटकांचे स्वतंत्र परवाने लागू राहतात.\par
\url{https://github.com/OpenLogicProject/OpenLogic}\par
\url{https://github.com/KokunoYumeto/OpenLogic-translations}
\end{titlepage}"""
core_body, title_count = re.subn(
    r"\\begin\{titlepage\}.*?\\end\{titlepage\}",
    lambda _: titlepage,
    core_body,
    count=1,
    flags=re.S,
)
assert title_count == 1
about = (ROOT / "mr/content/open-logic-about.tex").read_text(encoding="utf-8")
assert about.count(r"\chapter*") == 1
core_body = core_body.replace(r"\tableofcontents", about + "\n" + r"\tableofcontents", 1)

complete_part = (ROOT / "mr/content/sets-functions-relations/sets-functions-relations-complete.tex").read_text(encoding="utf-8")
part_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", complete_part, re.S)
assert part_note
first_chapter = r"\chapter{संच}"
assert core_body.count(first_chapter) == 1
core_body = core_body.replace(
    first_chapter,
    r"\part{अनौपचारिक संचसिद्धान्त}\label{sfr:part}\label{sfr:::part}" + "\n" + part_note.group(0) + "\n" + first_chapter,
    1,
)

proof_part_driver = (ROOT / "mr/content/proof-theory/proof-theory.tex").read_text(encoding="utf-8")
proof_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", proof_part_driver, re.S)
assert proof_note
proof_part = (r"\part{सिद्धता उपपत्ती}\label{pt:part}" + "\n"
              + proof_note.group(0) + "\n" + proof_body.strip() + "\n")
history_marker = r"\part{इतिहास}\label{his:part}"
assert core_body.count(history_marker) == 1
core_body = core_body.replace(history_marker, proof_part + history_marker, 1)

supplement_units = [
    "OLP-0643", "OLP-0644", "OLP-0645", "OLP-0647", "OLP-0648",
    "OLP-0649", "OLP-0650", "OLP-0651", "OLP-0652", "OLP-0653",
    "OLP-0654", "OLP-0694", "OLP-0714", "OLP-0715", "OLP-0716",
    "OLP-0717", "OLP-0718", "OLP-0721",
]
available = set(re.findall(r"\\label\{([^}]+)\}", core_body))
for unit in supplement_units:
    raw = (ROOT / "mr" / by_unit[unit]["source_path"]).read_text(encoding="utf-8")
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw)
    assert match, unit
    source_prefix = ":".join(match.groups())
    prefix = source_prefix + ("-alt" if unit == "OLP-0643" else "")
    available.add(prefix + ":sec")
    available.update(prefix + ":" + label for label in re.findall(r"\\ollabel\{([^}]+)\}", raw))


def source_note(note):
    return r"\begin{quote}\small\textbf{स्रोतनोंद.} " + project_note(note) + r"\end{quote}"


def convert_unit(unit):
    raw = (ROOT / "mr" / by_unit[unit]["source_path"]).read_text(encoding="utf-8")
    notes = re.findall(r"(?m)^[ \t]*%READERNOTE\{(.*)\}[ \t]*$", raw)
    selected = helpers["selected"](raw)
    content = helpers["ns"]["strip_wrapper"](selected)
    match = re.search(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", content)
    assert match, unit
    parts = list(match.groups())
    source_prefix = ":".join(parts)
    prefix = source_prefix + ("-alt" if unit == "OLP-0643" else "")
    content = content[:match.start()] + content[match.end():]
    for source_token, translated in {
        "!!{sentences}": "वाक्ये",
        "!!a{bijective}": "एकास-एक व आच्छादक",
        "!!a{relational model}": "संबंधात्मक प्रतिमान",
        "!!{discharge}": "मुक्त करणे",
        "!!{undischarged}": "मुक्त न केलेली",
    }.items():
        content = content.replace(source_token, translated)
    content = helpers["replace_tokens"](content)
    if r"\olsection" in content:
        content = helpers["convert_section"](content, prefix)
    else:
        content, section_count = re.subn(
            r"\\section\{([^{}]+)\}",
            lambda m: m.group(0) + r"\label{" + prefix + ":sec}",
            content,
            count=1,
        )
        assert section_count == 1, unit
    content = re.sub(r"\\ollabel\{([^}]+)\}",
                     lambda m: r"\label{" + prefix + ":" + m.group(1) + "}", content)

    def reference(match):
        options = re.findall(r"\[([^]]*)\]", match.group(1))
        assert len(options) <= 3, unit
        key_parts = parts.copy()
        if options:
            key_parts[3 - len(options):] = options
        key = ":".join(key_parts) + ":" + match.group(2)
        alternate_key = key.replace(source_prefix + ":", prefix + ":", 1)
        if unit == "OLP-0643" and alternate_key in available:
            key = alternate_key
        return (r"\ref{" if key in available else r"\readerexternalref{") + key + "}"

    content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}", reference, content)
    def tagged_reference(match):
        choices = re.findall(r"([^,{}\s]+)/\{([^{}]+)\}", match.group(1))
        valid = [key for _, key in choices if key in available]
        if not valid:
            # The frozen maximally-consistent-sets section points to prv for
            # propositional provability facts housed in the ppr section.
            valid = [key.replace(":prv:prop:provability-", ":ppr:prop:provability-")
                     for _, key in choices
                     if key.replace(":prv:prop:provability-", ":ppr:prop:provability-") in available]
        if not valid and unit == "OLP-0644":
            # The remaining tagged facts occur only in the alternate
            # axiomatic provability section included immediately above.
            valid = ["fol:axd:prv-alt:prop:" + key.split(":prop:", 1)[1]
                     for _, key in choices
                     if "fol:axd:prv-alt:prop:" + key.split(":prop:", 1)[1] in available]
        assert valid, (unit, choices)
        return r"\ref{" + valid[0] + "}"

    content = re.sub(
        r"\\tagrefs\{((?:[^{}]|\{[^{}]*\})*)\}",
        tagged_reference,
        content,
    )
    for original, projection in core_ns["prior"]["reader_symbol_projections"].items():
        content = content.replace(original, projection)
    assert "!!" not in content and not re.search(r"![A-Z]", content), unit
    assert not re.search(r"\\(?:olfileid|olsection|olref|Olref|ollabel|tagitem|tagrefs|iftag|subfile)\b", content), unit
    if notes:
        content += "\n" + "\n".join(source_note(note) for note in notes) + "\n"
    return content


supplement = [
    r"\part{पूरक आणि पर्यायी विभाग}\label{supp:part}",
    r"\chapter{मूळ संकलनमार्गाबाहेरील विभाग}\label{supp:chap}",
    ("या विभागांचे स्रोत-एककांमध्ये भाषांतर केलेले आहे. मुख्य संकलनमार्गात "
     "नसलेली सामग्री येथे विषयानुसार पूरक स्वरूपात दिली आहे."),
]
for unit in supplement_units:
    supplement.append(convert_unit(unit))

fragment_units = ["OLP-0660", "OLP-0705", "OLP-0708", "OLP-0709", "OLP-0710"]
for unit in fragment_units:
    path = ROOT / "mr" / by_unit[unit]["source_path"]
    if unit == "OLP-0660":
        fragment = proof_ns["expand_tokens"](path.read_text(encoding="utf-8"))
        fragment = fragment.replace(
            r"\olref[seq][inv]{prop:G3c-cont-adm}",
            r"\ref{pt:seq:inv:prop:G3c-cont-adm}",
        )
        assert "!!" not in fragment
        supplement.append(r"\section{अंतःप्रज्ञावादी कट-निर्मूलनातील पूरक प्रसंग}" + "\n" + fragment)
    else:
        stem = path.stem
        fragment = proof_ns["table_content"](path, "pt:seq:supp")
        supplement.append(r"\section{पूरक " + stem + " नियमसारणी}" + "\n" + fragment)

raw_root = (ROOT / "mr/content/content.tex").read_text(encoding="utf-8")
root_note = re.search(r"\\begin\{editorial\}.*?\\end\{editorial\}", raw_root, re.S)
assert root_note
supplement.append(r"\section{मूळ संपूर्ण-सामग्री चालकाची संपादकीय नोंद}")
supplement.append("खालील नोंद गोठवलेल्या मूळ संपूर्ण-सामग्री चालकाची आहे; प्रस्तुत ग्रंथाच्या संपादकीय स्थितीचा ती नवा दावा करत नाही.")
supplement.append(root_note.group(0))

note_marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
assert core_body.count(note_marker) == 1
core_body = core_body.replace(note_marker, "\n".join(supplement) + "\n" + note_marker, 1)

out = core_preamble + r"\begin{document}" + core_body + r"\end{document}" + "\n"
# Reader-only typesetting repairs preserve the checked translation sources.
# Keep each projection narrow and fail if its expected source context changes.
def project(old, new, expected):
    global out
    assert out.count(old) == expected, (old, out.count(old), expected)
    out = out.replace(old, new)


# SOL6-A132 now fixes OLINC-126 in the aligned source itself. Require its
# exact reviewed display instead of applying the obsolete reader projection.
factorial_source = r"""\begin{align*}
  B &\ident \lambd[m][\fn{IsZero}\,m\,\num{1}
       (\fn{Mult}\,m\,(\fn{Fac}(\fn{Pred}\,m)))]\\
  \fn{Fac} &\ident \lambd[n][\fn{IsZero}\,n\,\num{1}
       (\fn{Mult}\,n\,(B(\fn{Pred}\,n)))]
\end{align*}"""
assert out.count(factorial_source) == 1
assert factorial_source.count(r"\fn{Fac}") == 2
# An unnumbered bibliography must not inherit the preceding section's marks.
project(r"\chapter*{संदर्भ}" + "\n\n" + r"\addcontentsline{toc}{chapter}{संदर्भ}",
        r"\chapter*{संदर्भ}" + "\n" + r"\markboth{संदर्भ}{संदर्भ}" + "\n\n"
        + r"\addcontentsline{toc}{chapter}{संदर्भ}", 1)

# A math accent inside \mathbf emitted missing control glyphs on page 415-417.
project(r"\Th{\bar Q}", r"\overline{\Th{Q}}", 9)
project(r"\Th{\bar" + "\n" + r"T}", r"\overline{\Th{T}}", 1)
project(r"\Th{\bar T}", r"\overline{\Th{T}}", 1)
# Put the two inference displays on separate lines in the identity rules.
project("एकरूपता असलेल्या निष्पत्त्या साठी अतिरिक्त अनुमाननियम आवश्यक असतात.\n"
        r"\begin{defish}",
        "एकरूपता असलेल्या निष्पत्त्या साठी अतिरिक्त अनुमाननियम आवश्यक असतात.\n"
        r"\par\medskip\noindent" + "\n" + r"\begin{defish}", 1)
project(r"\UnaryInfC{$\eq[t][t]$}" + "\n" + r"\DisplayProof" + "\n" + r"\hfill" + "\n" + r"\begin{tabular}{r}",
        r"\UnaryInfC{$\eq[t][t]$}" + "\n" + r"\DisplayProof" + "\n" + r"\par\medskip\noindent" + "\n" + r"\begin{tabular}{r}", 1)
# Table column widths must include LaTeX's padding and vertical rules.
project(r"p{.48\textwidth} || p{.48\textwidth}",
        r"p{.465\textwidth} || p{.465\textwidth}", 2)
project(r"p{.50\textwidth} || p{.43\textwidth}",
        r"p{.50\textwidth} || p{.44\textwidth}", 1)
# This one modal-correspondence table exceeds the measure by 2.847 pt.
# Leave its fixed inner box narrower than the column and reduce local padding,
# while preserving the caption and HTML anchor.
table_begin = r"\begin{tabular}{| p{.50\textwidth} || p{.44\textwidth} |}"
project(table_begin, r"\setlength{\tabcolsep}{4pt}" + "\n" + table_begin, 1)
# These three labels belong to lemmas sharing the definition counter;
# explicit references retain the correct Marathi noun.
project(r"\cref{pt:seq:inv:lem:G3c-invert,pt:seq:inv:lem:invert-quant}",
        r"पूर्वप्रमेय~\ref{pt:seq:inv:lem:G3c-invert} आणि~\ref{pt:seq:inv:lem:invert-quant}", 1)
project(r"\cref{pt:cut:inv:lem:inv-G3c-cut}",
        r"पूर्वप्रमेय~\ref{pt:cut:inv:lem:inv-G3c-cut}", 1)
# Let the long cut-elimination proof reflow around its inline formulae.
project("    विगमन गृहीतकाने\n    $\\Gamma_1 \\Sequent",
        "    \\begingroup\\sloppy\n    विगमन गृहीतकाने\n    $\\Gamma_1 \\Sequent", 1)
project("    घेता येते. पहिल्या प्रसंगात:\n    \\[",
        "    घेता येते. पहिल्या प्रसंगात:\\par\\endgroup\n    \\[", 1)
out, wrapper_note_qa = preserve_notes(ROOT, by_unit, out, helpers["selected"],
                                     helpers["replace_tokens"], core_ns["prior"]["reader_symbol_projections"])
out, reader_note_qa = preserve_reader_notes(ROOT, by_unit, out)
labels = re.findall(r"\\label\{([^}]+)\}", out)
assert len(labels) == len(set(labels)), [x for x in labels if labels.count(x) > 1][:10]
out = re.sub(r"\\readerexternalref\{([^}]+)\}",
             lambda m: r"\ref{" + m.group(1) + "}" if m.group(1) in labels else m.group(0), out)
assert "pl:syn:sem:prop:semanticalfacts" in labels
out = out.replace(
    r"\readerexternalref{pl:prp:sem:prop:semanticalfacts}",
    r"\ref{pl:syn:sem:prop:semanticalfacts}",
)
assert out.count(r"\end{document}") == 1
# The upstream style gives !A a special mathcode. The standalone reader uses
# Latin formula metavariables instead, so project that source shorthand here.
out = re.sub(r"(\\[A-Za-z]+)!([A-Z])", r"\1 \2", out)
out = re.sub(r"(?<![!\\])!([A-Z])", r"\1", out)
assert "!!" not in out and not re.search(r"![A-Z]", out), (
    re.findall(r".{0,40}!!.{0,40}", out)[:8], re.findall(r".{0,30}![A-Z].{0,30}", out)[:8]
)
out = "\n".join(line.rstrip() for line in out.splitlines()) + "\n"
tex = BUILD / "openlogic-mr-full.tex"
tex.write_text(out, encoding="utf-8", newline="\n")
(BUILD / "FINAL_READER_PROJECTION_QA.json").write_text(json.dumps({
    "schema": "openlogic-mr-final-reader-projections/1",
    "status": "ready-for-build",
    "reader_sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
    "factorial": {
        "issue_id": "OLINC-126", "unit_id": "OLP-0379", "occurrences": 1,
        "source_correction_id": "SOL6-A132",
        "aligned_source_correction_applied": True,
        "reader_projection_applied": False,
        "display_sha256": hashlib.sha256(factorial_source.encode("utf-8")).hexdigest(),
        "current_target_sha256": hashlib.sha256((ROOT / "mr/content/lambda-calculus/lambda-definability/fixpoints.tex").read_bytes()).hexdigest(),
        "recursive_fac_retained": True,
        "reason_mr": "SOL6-A132 ने aligned target मध्येच IsZero च्या दोन्ही शाखांची बाह्य लॅम्डा व्याप्ती दुरुस्त केली. दोन छोट्या helper equations मधील स्वसंदर्भ जपला. जुन्या reader-only projection ऐवजी या नेमक्या दुरुस्त source display ची पडताळणी केली.",
    },
    "bibliography": {"heading_mr": "संदर्भ", "running_marks_reset": True},
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
wrapper_note_qa["reader_sha256"] = hashlib.sha256(out.encode("utf-8")).hexdigest()
(BUILD / "DRIVER_EDITORIAL_QA.json").write_text(json.dumps(wrapper_note_qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
reader_note_qa["reader_sha256"] = hashlib.sha256(out.encode("utf-8")).hexdigest()
verify_reader_notes(ROOT, by_unit, out, reader_note_qa)
(BUILD / "READER_NOTE_QA.json").write_text(json.dumps(reader_note_qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
core_inputs = json.loads((ROOT / "build/core/INPUTS.json").read_text(encoding="utf-8"))
proof_inputs = json.loads((ROOT / "build/proof/INPUTS.json").read_text(encoding="utf-8"))
manifest_by_target = {"mr/" + row["source_path"]: row["unit_id"] for row in manifest}
core_ids = {row["unit_id"] for row in core_inputs["input_units"]}
proof_ids = {manifest_by_target[path] for path in proof_inputs["paths"] if path in manifest_by_target}
supplement_ids = set(supplement_units + fragment_units)
front_ids = {"OLP-0001", "OLP-0002", "OLP-0003"}
wrapper_ids = {"OLP-0646", "OLP-0657", "OLP-0664", "OLP-0685",
               "OLP-0719", "OLP-0720", "OLP-0722"}
routes = [core_ids, proof_ids, supplement_ids, front_ids, wrapper_ids]
assert sum(map(len, routes)) == len(set().union(*routes)) == 722
assert set().union(*routes) == set(by_unit)
receipt = {
    "schema": "openlogic-mr-full-reader-input/1",
    "frozen_revision": "9620cc73f9c8e0ad003c514a5d3748f29611c4c0",
    "source_units_translated": 722,
    "input_units": [
        {"unit_id": row["unit_id"], "source_path": "upstream/" + row["source_path"],
         "source_sha256": row["source_sha256"], "target_path": "mr/" + row["source_path"],
         "target_sha256": hashlib.sha256((ROOT / "mr" / row["source_path"]).read_bytes()).hexdigest()}
        for row in manifest
    ],
    "core_unit_count": len(core_inputs["input_units"]),
    "core_unit_ids": sorted(core_ids),
    "proof_unit_ids": sorted(proof_ids),
    "proof_paths": proof_inputs["paths"],
    "supplement_unit_ids": supplement_units + fragment_units,
    "front_matter_and_root_unit_ids": sorted(front_ids),
    "represented_wrapper_unit_ids": sorted(wrapper_ids),
    "represented_unit_count": 722,
    "reader_sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
    "reader_bytes": len(out.encode("utf-8")),
    "chapters": out.count(r"\chapter{"),
    "sections": len(re.findall(r"\\section(?:\[[^]]*\])?\{", out)),
    "remaining_external_refs": sorted(set(re.findall(r"\\readerexternalref\{([^}]+)\}", out))),
    "reader_reference_projection": {
        "pl:prp:sem:prop:semanticalfacts": "pl:syn:sem:prop:semanticalfacts",
        "reason": "The supplemental propositional soundness source uses its own prp chapter ID for a semantic-facts result whose translated section is in the syn chapter. The aligned source key is unchanged.",
    },
}
(BUILD / "INPUTS.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: receipt[key] for key in ("reader_sha256", "reader_bytes", "chapters", "sections", "remaining_external_refs")}, ensure_ascii=False))
