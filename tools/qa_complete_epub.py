"""Independently audit the complete EPUB against its accepted reader."""
from __future__ import annotations

import argparse
import copy
import json
import posixpath
import re
import subprocess
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from lxml import etree
import qa_epub as q

X, M, O = q.XHTML_NS, q.MATHML_NS, q.OPF_NS
NS = q.NS

def canonical_math(node):
    result = copy.deepcopy(node)
    for glyph in result.iter():
        if glyph.tag in {f"{{{M}}}img", f"{{{M}}}mglyph"}:
            # Only the declared image-to-mglyph representation differs.
            keep = {k: glyph.get(k) for k in ("src", "alt")}
            glyph.tag = f"{{{M}}}mglyph"
            glyph.attrib.clear()
            glyph.attrib.update(keep)
    return q.digest(q.c14n(result))

def text_with_glyph_alternatives(node):
    result = copy.deepcopy(node)
    for glyph in result.iter(f"{{{M}}}img"):
        glyph.tag = f"{{{M}}}mglyph"
    return q.normalized_text(result)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--epubcheck-jar", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    reader = q.resolve(config["reader_root"])
    epub = q.resolve(config["output_epub"])
    build = q.resolve(config["build_root"])
    receipt = json.loads(q.resolve(config["build_receipt"]).read_text(encoding="utf-8"))
    checks, failures = 0, []
    metrics = Counter()
    def check(condition, message, amount=1):
        nonlocal checks
        checks += amount
        if not condition:
            failures.append(message)
    source_bytes = (reader / "index.html").read_bytes()
    check(q.digest(source_bytes) == config["reader_html_sha256"], "स्वीकृत HTML चा हॅश बदलला")
    check(receipt["epub"]["sha256"] == q.digest(epub.read_bytes()), "EPUB बांधणीची हॅश-जुळणी चुकली")
    check(receipt["cold_epub_byte_identity"] and receipt["cold_tree_byte_identity"], "दुसरी स्थानिक बांधणी जुळली नाही")
    check(receipt["config_sha256"] == q.digest(config_path.read_bytes()), "बांधणीचे विन्यास-जुळण चुकले")
    source = q.parse_xml(source_bytes)
    with zipfile.ZipFile(epub) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        check(len(names) == len(set(names)), "ZIP मध्ये पुनरावृत्त नावे")
        check(names[0] == "mimetype" and infos[0].compress_type == zipfile.ZIP_STORED
              and archive.read("mimetype") == b"application/epub+zip", "EPUB mimetype चुकीचा")
        check(names[1:] == sorted(names[1:]), "ZIP क्रम अनिश्चित")
        for name in names:
            check(not name.startswith("/") and "\\" not in name and ".." not in PurePosixPath(name).parts, "असुरक्षित ZIP मार्ग: " + name)
        package = q.parse_xml(archive.read("OEBPS/package.opf"))
        container = q.parse_xml(archive.read("META-INF/container.xml"))
        check(container.xpath("//*[local-name()='rootfile']/@full-path") == ["OEBPS/package.opf"], "container मार्ग चुकला")
        check(package.get("version") == "3.0", "EPUB आवृत्ती चुकीची")
        check(package.xpath("./opf:metadata/dc:language/text()", namespaces=NS) == [config["language"]], "भाषेची नोंद चुकली")
        description = package.xpath("./opf:metadata/dc:description/text()", namespaces=NS)
        check(description == [config["description"]] and "722" in description[0], "संपूर्ण व्याप्तीची नोंद चुकली")
        items = package.xpath("./opf:manifest/opf:item", namespaces=NS)
        item_paths = {i.get("id"): "OEBPS/" + unquote(i.get("href")) for i in items}
        check(len(item_paths) == len(items), "manifest ID पुनरावृत्त")
        check(set(item_paths.values()) == {n for n in names if n.startswith("OEBPS/") and n != "OEBPS/package.opf"}, "manifest संसाधने अपूर्ण")
        nav_items = [i for i in items if "nav" in (i.get("properties") or "").split()]
        check(len(nav_items) == 1 and item_paths[nav_items[0].get("id")] == "OEBPS/nav.xhtml", "अनुक्रमणिका manifest चुकीचा")
        spine = package.xpath("./opf:spine/opf:itemref", namespaces=NS)
        check(all(n.get("idref") in item_paths for n in spine), "spine संदर्भ तुटले")
        spine_paths = [item_paths[n.get("idref")] for n in spine if n.get("linear", "yes") != "no"]
        check(spine_paths == sorted(n for n in names if re.fullmatch(r"OEBPS/content-\d{3}\.xhtml", n)), "वाचनक्रम चुकला")
        docs = {n: q.parse_xml(archive.read(n)) for n in names if n.endswith((".xhtml", ".svg"))}
        content = [docs[n] for n in spine_paths]
        check(all(d.get("lang") == config["language"] and
                  d.get(f"{{{q.XML_NS}}}lang") == config["language"] for d in content),
              "वाचनभागांची मराठी भाषानोंद चुकली", len(content))
        metrics["reading_documents"] = len(content)
        check(len(content) == receipt["content"]["reading_documents"] == 98, "पूर्ण spine ची व्याप्ती चुकली")
        bodies = [d.find(f"{{{X}}}body") for d in content]
        check(" ".join(text_with_glyph_alternatives(b) for b in bodies) == text_with_glyph_alternatives(source.find(f"{{{X}}}body")), "वाचनक्रमातील पूर्ण मजकूर बदलला")
        source_math = list(source.iter(f"{{{M}}}math"))
        output_math = [m for d in content for m in d.iter(f"{{{M}}}math")]
        check(len(source_math) == len(output_math) == 38456, "MathML सूत्रांची संख्या बदलली")
        check([canonical_math(m) for m in source_math] == [canonical_math(m) for m in output_math], "घोषित glyph रूपांतराबाहेरील MathML बदलला", len(source_math))
        raw_equal = sum(q.c14n(a) == q.c14n(b) for a, b in zip(source_math, output_math))
        metrics["mathml_roots"] = len(output_math)
        metrics["raw_mathml_roots_exact"] = raw_equal
        metrics["mathml_roots_with_declared_glyph_projection"] = len(output_math) - raw_equal
        source_glyphs = list(source.iter(f"{{{M}}}img"))
        output_glyphs = [g for d in content for g in d.iter(f"{{{M}}}mglyph")]
        check(len(source_glyphs) == len(output_glyphs) == 68, "विशेष glyph संख्या बदलली")
        for before, after in zip(source_glyphs, output_glyphs):
            check(all(before.get(k) == after.get(k) for k in ("src", "alt")), "glyph चिन्ह किंवा पर्यायी मजकूर बदलला")
            match = re.fullmatch(r"height:([0-9.]+)em;vertical-align:([-0-9.]+)em", before.get("style", ""))
            graphic = docs["OEBPS/" + before.get("src")]
            _, _, width, height = map(float, graphic.get("viewBox").split())
            check(match is not None and abs(float(after.get("width")[:-2]) / float(after.get("height")[:-2]) - width / height) < 0.00001
                  and after.get("height") == match[1] + "em" and after.get("valign") == match[2] + "em", "glyph चे माप किंवा उभे स्थान बदलले")
            check(after.get("class") == "epub-math-glyph" and before.get("src") in after.get("style", ""), "glyph दृश्य पर्याय गहाळ")
        metrics["mathml_glyphs"] = len(output_glyphs)
        annotations = lambda d: [n.text for n in d.iter(f"{{{M}}}annotation") if n.get("encoding") == "application/x-tex"]
        check(annotations(source) == [a for d in content for a in annotations(d)], "मूळ TeX annotations बदलल्या")
        metrics["tex_annotations"] = sum(len(annotations(d)) for d in content)
        for tag, expected in (("h1", 16), ("h2", 83), ("h3", 613), ("img", 70)):
            src = list(source.iter(f"{{{X}}}{tag}"))
            out = [n for d in content for n in d.iter(f"{{{X}}}{tag}")]
            check(len(src) == len(out) == expected, tag + " ची संख्या बदलली")
            check([text_with_glyph_alternatives(n) for n in src] == [text_with_glyph_alternatives(n) for n in out], tag + " चे मजकूर बदलले")
            metrics[tag] = len(out)
        proofs = lambda d: [n for n in d.iter(f"{{{X}}}figure") if "proof" in n.get("class", "").split()]
        source_proofs = proofs(source)
        output_proofs = [p for d in content for p in proofs(d)]
        check(len(source_proofs) == len(output_proofs) == 466, "सिद्धतांची संख्या बदलली")
        check([annotations(p) for p in source_proofs] == [annotations(p) for p in output_proofs], "सिद्धतेतील सूत्रक्रम बदलला")
        metrics["proof_formula_rows"] = sum(len(annotations(p)) for p in output_proofs)
        check(metrics["proof_formula_rows"] == 2527, "सिद्धतेतील सूत्रांची व्याप्ती बदलली")
        source_ids = source.xpath("//@id")
        output_ids = [identifier for d in content for identifier in d.xpath("//@id")]
        rows = receipt["content"]["id_crosswalk"]
        check([r["source_id"] for r in rows] == source_ids and [r["epub_id"] for r in rows] == output_ids, "ID crosswalk अपूर्ण")
        check(len(output_ids) == len(set(output_ids)) and all(q.SAFE_ID_RE.fullmatch(i) for i in output_ids), "EPUB ID चुकीचे")
        mapping = {r["source_id"]: r["epub_id"] for r in rows}
        owners = {i: n for n in spine_paths for i in docs[n].xpath("//@id")}
        check({i: n.removeprefix("OEBPS/") for i, n in owners.items()} == receipt["content"]["owners"], "ID मालकी चुकली")
        source_hrefs = [h for h in source.xpath("//@href") if h.startswith("#")]
        output_hrefs = [h for d in content for h in d.xpath("//@href")
                        if urlsplit(h).fragment and not urlsplit(h).scheme and not urlsplit(h).netloc
                        and (not urlsplit(h).path or re.fullmatch(r"content-\d{3}\.xhtml", urlsplit(h).path))]
        check([unquote(urlsplit(h).fragment) for h in output_hrefs] == [mapping[unquote(h[1:])] for h in source_hrefs], "अंतर्गत संदर्भक्रम बदलला")
        ids_by_doc = {n: set(d.xpath("//@id")) for n, d in docs.items()}
        for name, doc in docs.items():
            for node in doc.iter():
                for key, value in node.attrib.items():
                    if etree.QName(key).localname not in {"href", "src"}:
                        continue
                    split = urlsplit(value)
                    if split.scheme in {"http", "https", "mailto", "data"}:
                        metrics["external_links"] += 1
                        continue
                    target = name if not split.path else posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(split.path)))
                    check(not split.scheme and not split.netloc and target in names, "तुटलेले संसाधन: " + name + " -> " + value)
                    if split.fragment:
                        check(unquote(split.fragment) in ids_by_doc.get(target, set()), "तुटलेला खंड-संदर्भ: " + name + " -> " + value)
                        metrics["fragment_links"] += 1
                    metrics["local_links"] += 1
            if name.endswith(".xhtml"):
                check(not doc.xpath(".//x:script|.//x:iframe|.//x:object|.//x:embed", namespaces=NS), "सक्रिय सामग्री आढळली")
        for path in reader.rglob("*"):
            if path.is_file() and path.name != "index.html":
                check(archive.read("OEBPS/" + path.relative_to(reader).as_posix()) == path.read_bytes(), "स्वीकृत संसाधनाचे bytes बदलले")
        for name in names:
            if name.endswith(".css"):
                for url in re.findall(r"url\(([^)]+)\)", archive.read(name).decode("utf-8")):
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), url.strip("\"'")))
                    check(target in names, "CSS संसाधन तुटले: " + target)
        nav = docs["OEBPS/nav.xhtml"]
        source_toc = source.xpath(".//x:nav[@id='TOC']//x:a/@href", namespaces=NS)
        output_toc = nav.xpath(".//x:nav[@epub:type='toc']//x:a/@href", namespaces=NS)
        check([unquote(urlsplit(h).fragment) for h in output_toc] == [mapping[unquote(h[1:])] for h in source_toc], "पूर्ण अनुक्रमणिका बदलली")
        metrics["toc_links"] = len(output_toc)
    report = build / "EPUBCHECK.json"
    result = subprocess.run(["java", "-jar", str(args.epubcheck_jar.resolve()), "--json", str(report), str(epub)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    epubcheck = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    check(result.returncode == 0 and epubcheck.get("messages") == [], "EPUBCheck त्रुटी किंवा सूचना आढळल्या")
    check(epubcheck.get("checker", {}).get("checkerVersion") == "5.3.0", "EPUBCheck आवृत्ती चुकली")
    audit = {"schema": "openlogic-mr-complete-epub-qa/1", "status": "passed" if not failures else "failed", "checks": checks,
             "epub_sha256": q.digest(epub.read_bytes()), "reader_html_sha256": config["reader_html_sha256"],
             "metrics": dict(metrics), "failures": failures, "epubcheck_exit": result.returncode,
             "epubcheck_report_sha256": q.digest(report.read_bytes()) if report.exists() else None,
             "scope": {"source_units": 722, "aligned_segments": 6644, "main_chapters": 79, "reader_sections": 613},
             "preservation_mr": "संपूर्ण मजकूर, TeX annotations, सूत्रक्रम, सिद्धता, संसाधने आणि संदर्भ जतन आहेत. 68 HTML glyph-images चे घोषित MathML mglyph रूपांतर आहे; उर्वरित MathML मध्ये बदल नाही.",
             "limitations_mr": ["दृश्य नमुन्यांची तपासणी स्वतंत्र नोंदीत आहे.", "वाचन-प्रणालीनुसार MathML आधार बदलतो; स्वतंत्र मानवी भाषिक किंवा सुलभता-प्रमाणपत्राचा दावा नाही."]}
    (build / "EPUB_QA.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": audit["status"], "checks": checks, "metrics": dict(metrics), "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
