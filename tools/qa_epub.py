"""Validate Marathi EPUB structure, semantic preservation, scope, links and MathML."""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
XHTML_NS = "http://www.w3.org/1999/xhtml"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
EPUB_NS = "http://www.idpf.org/2007/ops"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"x": XHTML_NS, "m": MATHML_NS, "opf": OPF_NS, "dc": DC_NS, "epub": EPUB_NS}
SAFE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise ValueError(f"path escapes repository: {relative}")
    return path


def parse_xml(payload: bytes) -> etree._Element:
    return etree.fromstring(payload, parser=etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))


def c14n(node: etree._Element) -> bytes:
    return etree.tostring(node, method="c14n", with_comments=True)


def normalized_text(node: etree._Element) -> str:
    return " ".join("".join(node.itertext()).split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--epubcheck-jar", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    epub = resolve(config["output_epub"])
    reader = resolve(config["reader_root"]) / "index.html"
    manifest_path = resolve(config["source_release_manifest"])
    html_qa_path = resolve(config["source_html_qa"])
    checkpoint_path = resolve(config["source_checkpoint"])
    build_receipt_path = resolve(config["build_receipt"])
    crosswalk_path = resolve(config["id_crosswalk"])
    qa_path = resolve(config["qa_receipt"])
    epubcheck_path = resolve(config["epubcheck_report"])
    build_receipt = json.loads(build_receipt_path.read_text(encoding="utf-8"))
    crosswalk = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    release_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    html_qa = json.loads(html_qa_path.read_text(encoding="utf-8"))
    expected = config["expected"]
    checks = 0
    failures: list[str] = []
    metrics: Counter[str] = Counter()

    def check(condition: bool, message: str, amount: int = 1) -> None:
        nonlocal checks
        checks += amount
        if not condition:
            failures.append(message)

    check(epub.is_file(), "EPUB artifact is missing")
    check(digest(reader.read_bytes()) == expected["reader_html_sha256"], "accepted reader hash drift")
    check(digest(checkpoint_path.read_bytes()) == expected["source_checkpoint_sha256"], "source checkpoint hash drift")
    check(digest(epub.read_bytes()) == build_receipt["epub"]["sha256"], "EPUB hash differs from build receipt")
    check(epub.stat().st_size == build_receipt["epub"]["bytes"], "EPUB size differs from build receipt")
    check(build_receipt["epub"]["byte_identical_cold_build"] is True, "cold EPUB build did not match")
    check(build_receipt["package_tree"]["byte_identical_cold_build"] is True, "cold package tree did not match")
    check(digest(crosswalk_path.read_bytes()) == build_receipt["id_crosswalk"]["sha256"], "ID crosswalk hash differs from build receipt")
    check(crosswalk["epub"]["sha256"] == digest(epub.read_bytes()), "ID crosswalk is bound to another EPUB")

    with zipfile.ZipFile(epub) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        check(len(names) == len(set(names)), "duplicate ZIP entry")
        check(names and names[0] == "mimetype", "mimetype is not the first ZIP entry")
        check(infos[0].compress_type == zipfile.ZIP_STORED, "mimetype is compressed")
        check(archive.read("mimetype") == b"application/epub+zip", "wrong mimetype payload")
        check(names[1:] == sorted(names[1:]), "ZIP entries after mimetype are not sorted")
        for name in names:
            parts = PurePosixPath(name).parts
            check(bool(name) and "\\" not in name and not name.startswith("/") and all(part not in {"", ".", ".."} for part in parts), f"unsafe ZIP entry: {name}")

        check("META-INF/container.xml" in names, "container.xml is missing")
        check("OEBPS/package.opf" in names, "package document is missing")
        check("OEBPS/content.xhtml" in names, "content document is missing")
        check("OEBPS/nav.xhtml" in names, "navigation document is missing")
        package = parse_xml(archive.read("OEBPS/package.opf"))
        content = parse_xml(archive.read("OEBPS/content.xhtml"))
        nav = parse_xml(archive.read("OEBPS/nav.xhtml"))
        source = parse_xml(reader.read_bytes())

        check(package.get("version") == "3.0", "package version is not EPUB 3")
        check(package.get(f"{{{XML_NS}}}lang") == config["language"], "package language/script tag mismatch")
        languages = package.xpath("./opf:metadata/dc:language/text()", namespaces=NS)
        check(languages == [config["language"]], "dc:language mismatch")
        metadata = {node.get("property"): (node.text or "") for node in package.xpath("./opf:metadata/opf:meta", namespaces=NS)}
        check(metadata.get("rendition:layout") == "reflowable", "EPUB is not declared reflowable")
        summaries = package.xpath("./opf:metadata/opf:meta[@property='schema:accessibilitySummary']/text()", namespaces=NS)
        check(bool(summaries) and "108 of 722" in summaries[0] and "incomplete" in summaries[0].lower(), "partial scope is not disclosed in accessibility metadata")

        manifest_items = package.xpath("./opf:manifest/opf:item", namespaces=NS)
        id_to_path: dict[str, PurePosixPath] = {}
        for item in manifest_items:
            path = PurePosixPath("OEBPS") / unquote(item.get("href") or "")
            id_to_path[item.get("id") or ""] = path
            check(path.as_posix() in names, f"manifest resource is missing: {path}")
        declared = {path.as_posix() for path in id_to_path.values()}
        actual_resources = {name for name in names if name.startswith("OEBPS/") and name != "OEBPS/package.opf"}
        check(declared == actual_resources, "manifest does not exactly cover OEBPS resources")
        nav_items = [item for item in manifest_items if "nav" in (item.get("properties") or "").split()]
        check(len(nav_items) == 1 and id_to_path[nav_items[0].get("id") or ""] == PurePosixPath("OEBPS/nav.xhtml"), "navigation manifest item mismatch")
        content_items = [item for item in manifest_items if id_to_path[item.get("id") or ""] == PurePosixPath("OEBPS/content.xhtml")]
        check(len(content_items) == 1 and "mathml" in (content_items[0].get("properties") or "").split(), "content MathML property missing")
        spine = package.xpath("./opf:spine/opf:itemref", namespaces=NS)
        spine_paths = [id_to_path.get(item.get("idref") or "") for item in spine]
        check(spine_paths == [PurePosixPath("OEBPS/nav.xhtml"), PurePosixPath("OEBPS/content.xhtml")], "spine order mismatch")
        check((spine[0].get("linear") or "yes") == "no" and (spine[1].get("linear") or "yes") == "yes", "linear reading order mismatch")

        source_body = source.xpath("./x:body", namespaces=NS)[0]
        content_body = content.xpath("./x:body", namespaces=NS)[0]
        check(normalized_text(source_body) == normalized_text(content_body), "accepted reader text changed in EPUB")
        metrics["body_c14n_bytes"] = len(c14n(content_body))
        source_math = source.xpath(".//m:math", namespaces=NS)
        content_math = content.xpath(".//m:math", namespaces=NS)
        check(len(source_math) == len(content_math) == expected["native_mathml"], "MathML root count drift")
        source_math_hashes = [digest(c14n(node)) for node in source_math]
        content_math_hashes = [digest(c14n(node)) for node in content_math]
        check(source_math_hashes == content_math_hashes, "MathML mathematical trees changed")
        check(all(etree.QName(node).namespace == MATHML_NS for node in content_math), "MathML namespace mismatch", len(content_math))
        annotations = content.xpath(".//m:math/m:semantics/m:annotation[@encoding='application/x-tex']", namespaces=NS)
        check(len(annotations) == expected["native_mathml"], "TeX annotation coverage drift")
        check(not content.xpath(".//x:script|.//x:iframe|.//x:object|.//x:embed", namespaces=NS), "active or embedded content survived")

        ids = [value for value in content.xpath("//@id") if value]
        check(len(ids) == len(set(ids)), "duplicate content IDs")
        check(all(SAFE_ID_RE.fullmatch(value) for value in ids), "content contains an EPUB-unsafe ID", len(ids))
        source_ids = [value for value in source.xpath("//@id") if value]
        rows = crosswalk.get("mappings", [])
        check(crosswalk.get("schema") == "openlogic-marathi-epub-id-crosswalk/1", "unexpected ID crosswalk schema")
        check(len(rows) == len(source_ids), "ID crosswalk is incomplete")
        check([row.get("source_id") for row in rows] == source_ids, "ID crosswalk source order differs")
        mapped_ids = [row.get("epub_id") for row in rows]
        check(mapped_ids == ids, "content IDs do not match the crosswalk")
        check(len(set(mapped_ids)) == len(mapped_ids), "ID crosswalk contains duplicate EPUB IDs")
        check(all(SAFE_ID_RE.fullmatch(value or "") for value in mapped_ids), "ID crosswalk contains an unsafe EPUB ID", len(mapped_ids))
        id_mapping = {row["source_id"]: row["epub_id"] for row in rows}
        remapped_rows = [row for row in rows if row.get("remapped")]
        check(len(remapped_rows) == crosswalk.get("remapped") == build_receipt["id_crosswalk"]["remapped"], "remapped-ID count drift")
        check(len(rows) - len(remapped_rows) == crosswalk.get("identity") == build_receipt["id_crosswalk"]["identity"], "identity-ID count drift")
        for row in rows:
            matches = content.xpath(".//*[@id=$value]", value=row["epub_id"])
            check(len(matches) == 1, f"crosswalk target owner mismatch: {row['source_id']!r}")
            if len(matches) == 1:
                expected_source_id = row["source_id"] if row.get("remapped") else None
                check(matches[0].get("data-source-id") == expected_source_id, f"source-ID marker mismatch: {row['source_id']!r}")
        source_fragment_hrefs = [value for value in source.xpath("//@href") if value.startswith("#")]
        output_fragment_hrefs = [value for value in content.xpath("//@href") if value.startswith("#")]
        expected_fragment_hrefs = ["#" + id_mapping[unquote(value[1:])] for value in source_fragment_hrefs]
        check(output_fragment_hrefs == expected_fragment_hrefs, "internal content links do not exactly follow the ID crosswalk", len(source_fragment_hrefs))
        content_ids = set(ids)
        chapter_headings = content.xpath(".//x:h1[@data-number]", namespaces=NS)
        section_headings = content.xpath(".//x:h2[@data-number]", namespaces=NS)
        proof_figures = content.xpath(".//x:figure[contains(concat(' ', normalize-space(@class), ' '), ' proof ')]", namespaces=NS)
        proof_rows = content.xpath(".//x:figure[contains(concat(' ', normalize-space(@class), ' '), ' proof ')]//m:annotation[@encoding='application/x-tex']", namespaces=NS)
        images = content.xpath(".//x:img", namespaces=NS)
        check(len(chapter_headings) == expected["complete_chapters"], "chapter count drift")
        check(len(section_headings) == expected["reader_sections"], "section count drift")
        check(len(proof_figures) == expected["semantic_proof_figures"], "semantic proof-figure count drift")
        check(len(proof_rows) == expected["proof_formula_rows"], "proof formula-row count drift")
        check(len(images) == expected["diagrams"], "diagram count drift")
        check(all(len((image.get("alt") or "").strip()) > 40 for image in images), "diagram alternative text missing")
        check(content.get("lang") == "mr" and content.get(f"{{{XML_NS}}}lang") == "mr", "accepted content language changed")
        body_text = " ".join("".join(content_body.itertext()).split())
        check("108 स्रोत-एकके" in body_text and "उर्वरित 614" in body_text and "अपूर्ण" in body_text, "visible partial-scope disclosure missing")

        parsed_documents = {PurePosixPath("OEBPS/content.xhtml"): content, PurePosixPath("OEBPS/nav.xhtml"): nav}
        ids_by_document = {path: set(doc.xpath("//@id")) for path, doc in parsed_documents.items()}
        local_links = fragment_links = external_links = 0
        for source_path, document in parsed_documents.items():
            for node in document.xpath(".//*[@href or @src]"):
                attribute = "href" if node.get("href") is not None else "src"
                value = node.get(attribute) or ""
                split = urlsplit(value)
                if split.scheme in {"http", "https", "mailto"}:
                    external_links += 1
                    continue
                check(not split.scheme and not split.netloc, f"unsupported link scheme: {source_path} -> {value}")
                target_path = source_path if not split.path else PurePosixPath(posixpath.normpath(posixpath.join(source_path.parent.as_posix(), unquote(split.path))))
                check(target_path.as_posix() in names, f"broken local resource: {source_path} -> {value}")
                if split.fragment:
                    fragment_links += 1
                    check(unquote(split.fragment) in ids_by_document.get(target_path, set()), f"broken fragment: {source_path} -> {value}")
                local_links += 1
        metrics["local_links"] = local_links
        metrics["fragment_links"] = fragment_links
        metrics["external_links"] = external_links
        check(fragment_links >= expected["internal_links"], "internal-link coverage fell below accepted HTML")
        toc_links = nav.xpath(".//x:nav[@epub:type='toc']//x:a", namespaces=NS)
        check(len(toc_links) >= expected["reader_sections"] + expected["complete_chapters"], "navigation omits chapter or section links")
        check(len(nav.xpath(".//x:nav[@epub:type='landmarks']//x:a", namespaces=NS)) == 2, "landmark navigation mismatch")

    check(release_manifest["coverage"]["translated_source_units"] == expected["translated_source_units"], "release unit coverage mismatch")
    check(release_manifest["coverage"]["total_source_units"] == expected["total_source_units"], "release corpus coverage mismatch")
    check(release_manifest["coverage"]["aligned_content_segments"] == expected["aligned_content_segments"], "release segment coverage mismatch")
    check(release_manifest["coverage"]["complete_edition"] is False, "partial release is marked complete")
    check(html_qa["passed"] is True and html_qa["html_sha256"] == expected["reader_html_sha256"], "accepted HTML QA binding mismatch")
    check(html_qa["source_to_html_main_math_annotations_exact"] == 5507, "source-to-MathML main-expression coverage drift")
    check(html_qa["proof_formula_annotations_verified"] == expected["proof_formula_rows"], "source-to-proof-formula coverage drift")

    epubcheck_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["java", "-jar", str(args.epubcheck_jar.resolve()), "--json", str(epubcheck_path), str(epub)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(result.returncode == 0, "EPUBCheck returned a failure status")
    check(epubcheck_path.is_file(), "EPUBCheck JSON report was not created")
    epubcheck = json.loads(epubcheck_path.read_text(encoding="utf-8")) if epubcheck_path.is_file() else {}
    check(epubcheck.get("messages") == [], "EPUBCheck reported messages")
    check(epubcheck.get("checker", {}).get("checkerVersion") == "5.3.0", "unexpected EPUBCheck version")

    receipt = {
        "schema": "openlogic-marathi-epub3-qa/1",
        "status": "passed" if not failures else "failed",
        "release": config["release"],
        "source_release": config["source_release"],
        "format": "reflowable EPUB 3",
        "language": config["language"],
        "scope": release_manifest["coverage"],
        "epub": {"path": config["output_epub"], "bytes": epub.stat().st_size, "sha256": digest(epub.read_bytes())},
        "checks": checks,
        "failures": failures,
        "metrics": dict(metrics),
        "epubcheck": {
            "version": epubcheck.get("checker", {}).get("checkerVersion"),
            "messages": len(epubcheck.get("messages", [])),
            "report": config["epubcheck_report"],
            "report_sha256": digest(epubcheck_path.read_bytes()) if epubcheck_path.is_file() else None,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        },
        "preservation": {
            "accepted_reader_semantic_text_exact": not any("reader text" in failure for failure in failures),
            "all_mathml_trees_exact": not any("MathML mathematical trees" in failure for failure in failures),
            "source_html_qa_bound": html_qa["html_sha256"] == expected["reader_html_sha256"],
            "source_checkpoint_bound": digest(checkpoint_path.read_bytes()) == expected["source_checkpoint_sha256"],
            "partial_scope_disclosed": not any("partial-scope" in failure for failure in failures),
        },
        "limitations": [
            "No independent human linguistic or accessibility review is claimed.",
            "Reading-system support for native MathML varies.",
            "Representative visual rendering is recorded separately from this structural audit."
        ],
    }
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
