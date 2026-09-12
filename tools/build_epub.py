"""Build a deterministic reflowable EPUB 3 from an accepted Marathi reader."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import posixpath
import re
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
XHTML_NS = "http://www.w3.org/1999/xhtml"
MATHML_NS = "http://www.w3.org/1998/Math/MathML"
EPUB_NS = "http://www.idpf.org/2007/ops"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"x": XHTML_NS, "m": MATHML_NS, "opf": OPF_NS, "dc": DC_NS}
SAFE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def resolve(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    require(path == ROOT or ROOT in path.parents, f"path escapes repository: {relative}")
    return path


def parse_xml(payload: bytes) -> etree._Element:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True, remove_blank_text=False)
    return etree.fromstring(payload, parser=parser)


def c14n(node: etree._Element) -> bytes:
    return etree.tostring(node, method="c14n", with_comments=True)


def normalized_text(node: etree._Element) -> str:
    return " ".join("".join(node.itertext()).split())


def build_id_crosswalk(root: etree._Element) -> tuple[dict[str, str], list[dict]]:
    """Create a deterministic, collision-free EPUB-safe mapping for every source ID."""
    source_ids = [value for value in root.xpath("//@id") if value]
    require(len(source_ids) == len(set(source_ids)), "accepted reader contains duplicate IDs")
    occupied = set(source_ids)
    mapping: dict[str, str] = {}
    rows: list[dict] = []
    for source_id in source_ids:
        epub_id = source_id
        if not SAFE_ID_RE.fullmatch(source_id):
            hexdigest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
            length = 20
            epub_id = f"epub-{hexdigest[:length]}"
            while epub_id in occupied:
                length += 1
                require(length <= len(hexdigest), f"cannot derive unique EPUB ID for {source_id!r}")
                epub_id = f"epub-{hexdigest[:length]}"
            occupied.add(epub_id)
        mapping[source_id] = epub_id
        rows.append({"source_id": source_id, "epub_id": epub_id, "remapped": epub_id != source_id})
    require(len(set(mapping.values())) == len(mapping), "EPUB ID mapping collision")
    require(all(SAFE_ID_RE.fullmatch(value) for value in mapping.values()), "unsafe EPUB ID remains")
    return mapping, rows


def remap_ids_and_links(root: etree._Element, mapping: dict[str, str]) -> dict:
    remapped_ids = 0
    rewritten_links = 0
    for node in root.xpath(".//*[@id]"):
        source_id = node.get("id") or ""
        require(source_id in mapping, f"ID is absent from crosswalk: {source_id!r}")
        epub_id = mapping[source_id]
        if epub_id != source_id:
            node.set("data-source-id", source_id)
            node.set("id", epub_id)
            remapped_ids += 1
    for node in root.xpath(".//*[@href]"):
        href = node.get("href") or ""
        split = urlsplit(href)
        if not split.scheme and not split.netloc and not split.path and split.fragment:
            source_target = unquote(split.fragment)
            require(source_target in mapping, f"fragment target is absent from crosswalk: {href!r}")
            node.set("href", "#" + mapping[source_target])
            rewritten_links += 1
    return {"ids_remapped": remapped_ids, "fragment_links_rewritten": rewritten_links}


def normalize_content_structures(root: etree._Element) -> dict:
    """Lift block children from paragraphs without changing reading order."""
    block_names = {
        "address", "article", "aside", "blockquote", "div", "dl", "fieldset", "figure",
        "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main",
        "nav", "ol", "p", "pre", "section", "table", "ul",
    }
    lifted = 0
    while True:
        candidate: tuple[etree._Element, etree._Element] | None = None
        for paragraph in root.xpath(".//x:p", namespaces=NS):
            child = next((node for node in list(paragraph) if etree.QName(node).localname in block_names), None)
            if child is not None:
                candidate = paragraph, child
                break
        if candidate is None:
            break
        paragraph, child = candidate
        parent = paragraph.getparent()
        require(parent is not None, "orphan paragraph during EPUB normalization")
        paragraph_index = parent.index(paragraph)
        child_index = paragraph.index(child)
        following = etree.Element(
            f"{{{XHTML_NS}}}p",
            attrib={key: value for key, value in paragraph.attrib.items() if key not in {"id", "aria-labelledby"}},
        )
        following.text = child.tail
        child.tail = None
        for sibling in list(paragraph)[child_index + 1:]:
            paragraph.remove(sibling)
            following.append(sibling)
        paragraph.remove(child)
        after_paragraph = paragraph.tail
        paragraph.tail = None
        parent.insert(paragraph_index + 1, child)
        if (following.text and following.text.strip()) or len(following):
            following.tail = after_paragraph
            parent.insert(paragraph_index + 2, following)
        elif after_paragraph:
            child.tail = after_paragraph
        lifted += 1
    return {"block_children_lifted_from_paragraphs": lifted}


def inventory(root: Path) -> list[dict]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path.read_bytes()),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def inventory_digest(rows: list[dict]) -> str:
    frame = "".join(
        f"{row['sha256']}  {row['bytes']}  {row['path']}\n"
        for row in sorted(rows, key=lambda row: row["path"])
    )
    return digest(frame.encode("utf-8"))


def element(tag: str, parent: etree._Element | None = None, **attributes: str) -> etree._Element:
    node = etree.Element(f"{{{XHTML_NS}}}{tag}") if parent is None else etree.SubElement(parent, f"{{{XHTML_NS}}}{tag}")
    for key, value in attributes.items():
        node.set(key, value)
    return node


def serialize(root: etree._Element) -> bytes:
    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        doctype="<!DOCTYPE html>",
        method="xml",
        pretty_print=False,
    )


def safe_clear(path: Path, build_root: Path) -> None:
    require(path.parent == build_root, f"unsafe generated-tree target: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def media_type(path: PurePosixPath) -> str:
    return {
        ".xhtml": "application/xhtml+xml",
        ".css": "text/css",
        ".svg": "image/svg+xml",
        ".ttf": "font/ttf",
        ".txt": "text/plain",
    }[path.suffix.lower()]


def item_id(path: PurePosixPath) -> str:
    return "item-" + hashlib.sha256(path.as_posix().encode("utf-8")).hexdigest()[:16]


def build_navigation(source_root: etree._Element, config: dict, id_mapping: dict[str, str]) -> tuple[bytes, dict]:
    root = etree.Element(f"{{{XHTML_NS}}}html", nsmap={None: XHTML_NS, "epub": EPUB_NS})
    root.set("lang", config["language"])
    root.set(f"{{{XML_NS}}}lang", config["language"])
    head = element("head", root)
    title = element("title", head)
    title.text = "अनुक्रमणिका — " + config["title"]
    element("meta", head, charset="utf-8")
    element("link", head, rel="stylesheet", href="reader.css")
    body = element("body", root)
    body.set(f"{{{EPUB_NS}}}type", "frontmatter")
    header = element("header", body)
    heading = element("h1", header)
    heading.text = config["title"]
    status = element("p", header, **{"class": "edition-status"})
    status.text = "मराठी EPUB आवृत्ती · अकरा संपूर्ण प्रकरणे · पूर्ण ग्रंथ नाही"

    source_navs = source_root.xpath(".//x:nav[@id='TOC']", namespaces=NS)
    require(len(source_navs) == 1, "accepted reader must contain one TOC navigation")
    source_nav = source_navs[0]
    toc = element("nav", body, id="toc")
    toc.set(f"{{{EPUB_NS}}}type", "toc")
    toc.set("role", "doc-toc")
    toc.set("aria-label", "अनुक्रमणिका")
    toc_heading = element("h2", toc)
    toc_heading.text = "अनुक्रमणिका"
    for child in source_nav:
        if etree.QName(child).localname.lower() == "h2":
            continue
        clone = copy.deepcopy(child)
        for listing in clone.xpath(".//*[local-name()='ul' or local-name()='ol']"):
            listing.tag = f"{{{XHTML_NS}}}ol"
        if etree.QName(clone).localname in {"ul", "ol"}:
            clone.tag = f"{{{XHTML_NS}}}ol"
        for node in clone.xpath(".//*[@id]"):
            source_id = node.get("id") or ""
            require(source_id in id_mapping, f"navigation ID is absent from crosswalk: {source_id!r}")
            epub_id = id_mapping[source_id]
            if epub_id != source_id:
                node.set("data-source-id", source_id)
                node.set("id", epub_id)
        for anchor in clone.xpath(".//*[local-name()='a' and @href]"):
            href = anchor.get("href") or ""
            if href.startswith("#"):
                source_target = unquote(href[1:])
                require(source_target in id_mapping, f"navigation target is absent from crosswalk: {href!r}")
                anchor.set("href", "content.xhtml#" + id_mapping[source_target])
        toc.append(clone)

    landmarks = element("nav", body)
    landmarks.set(f"{{{EPUB_NS}}}type", "landmarks")
    landmarks.set("aria-label", "प्रकाशनातील प्रमुख ठिकाणे")
    landmark_heading = element("h2", landmarks)
    landmark_heading.text = "प्रमुख ठिकाणे"
    listing = element("ol", landmarks)
    for label, href, epub_type in (
        ("अनुक्रमणिका", "nav.xhtml#toc", "toc"),
        ("मुख्य मजकूर", "content.xhtml#main-content", "bodymatter"),
    ):
        li = element("li", listing)
        anchor = element("a", li, href=href)
        anchor.set(f"{{{EPUB_NS}}}type", epub_type)
        anchor.text = label

    payload = serialize(root)
    parsed = parse_xml(payload)
    links = parsed.xpath(".//x:nav[@epub:type='toc']//x:a", namespaces={**NS, "epub": EPUB_NS})
    return payload, {"toc_links": len(links), "landmarks": 2}


def build_package(config: dict, content_sha: str, resources: list[PurePosixPath]) -> bytes:
    nsmap = {None: OPF_NS, "dc": DC_NS}
    package = etree.Element(f"{{{OPF_NS}}}package", nsmap=nsmap)
    package.set("version", "3.0")
    package.set("unique-identifier", "pub-id")
    package.set(f"{{{XML_NS}}}lang", config["language"])
    package.set("prefix", "schema: http://schema.org/ rendition: http://www.idpf.org/vocab/rendition/# dcterms: http://purl.org/dc/terms/")
    metadata = etree.SubElement(package, f"{{{OPF_NS}}}metadata")

    def dc(name: str, value: str, identifier: str | None = None) -> None:
        node = etree.SubElement(metadata, f"{{{DC_NS}}}{name}")
        node.text = value
        if identifier:
            node.set("id", identifier)

    def meta(prop: str, value: str) -> None:
        node = etree.SubElement(metadata, f"{{{OPF_NS}}}meta")
        node.set("property", prop)
        node.text = value

    publication_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"openlogic-mr:{content_sha}:{config['source_release']}")
    dc("identifier", f"urn:uuid:{publication_uuid}", "pub-id")
    dc("title", config["title"], "title")
    dc("language", config["language"])
    dc("creator", "Open Logic Project and credited contributors")
    dc("contributor", "Marathi translation produced with OpenAI Codex")
    dc("publisher", "Open Logic Project")
    dc("date", config["modified"][:10])
    dc("type", "Textbook")
    dc("subject", "Mathematical logic")
    dc("description", config["description"])
    dc("source", f"The Open Logic Text revision 9620cc73f9c8e0ad003c514a5d3748f29611c4c0; Marathi source release {config['source_release']}")
    dc("rights", "Creative Commons Attribution 4.0 International (CC BY 4.0). Credits are preserved in the publication.")
    meta("dcterms:modified", config["modified"])
    meta("rendition:layout", "reflowable")
    meta("rendition:orientation", "auto")
    meta("rendition:spread", "auto")
    for mode in ("textual", "visual"):
        meta("schema:accessMode", mode)
    meta("schema:accessModeSufficient", "textual,visual")
    for feature in ("MathML", "alternativeText", "displayTransformability", "readingOrder", "structuralNavigation", "tableOfContents"):
        meta("schema:accessibilityFeature", feature)
    for hazard in ("noFlashingHazard", "noMotionSimulationHazard", "noSoundHazard"):
        meta("schema:accessibilityHazard", hazard)
    meta(
        "schema:accessibilitySummary",
        "Reflowable Marathi text with semantic headings, native presentation MathML, semantic proof tables, detailed Marathi alternatives for diagrams, and a navigable table of contents. This is an incomplete eleven-chapter edition covering 108 of 722 source units. Reading-system MathML support varies; automated checks are not human accessibility certification.",
    )

    manifest = etree.SubElement(package, f"{{{OPF_NS}}}manifest")
    identifiers: dict[PurePosixPath, str] = {}
    for path in sorted(resources, key=lambda value: value.as_posix()):
        identifier = item_id(path)
        identifiers[path] = identifier
        item = etree.SubElement(manifest, f"{{{OPF_NS}}}item")
        item.set("id", identifier)
        item.set("href", path.as_posix())
        item.set("media-type", media_type(path))
        properties: list[str] = []
        if path == PurePosixPath("nav.xhtml"):
            properties.extend(("nav", "mathml"))
        if path == PurePosixPath("content.xhtml"):
            properties.append("mathml")
        if properties:
            item.set("properties", " ".join(properties))

    spine = etree.SubElement(package, f"{{{OPF_NS}}}spine")
    nav_ref = etree.SubElement(spine, f"{{{OPF_NS}}}itemref")
    nav_ref.set("idref", identifiers[PurePosixPath("nav.xhtml")])
    nav_ref.set("linear", "no")
    content_ref = etree.SubElement(spine, f"{{{OPF_NS}}}itemref")
    content_ref.set("idref", identifiers[PurePosixPath("content.xhtml")])
    return etree.tostring(package, encoding="utf-8", xml_declaration=True, method="xml", pretty_print=True)


def build_tree(destination: Path, reader_root: Path, config: dict) -> dict:
    oebps = destination / "OEBPS"
    (destination / "META-INF").mkdir(parents=True)
    oebps.mkdir()
    source_payload = (reader_root / "index.html").read_bytes()
    source_root = parse_xml(source_payload)
    require(etree.QName(source_root).namespace == XHTML_NS, "reader is not XHTML")

    source_body = source_root.xpath("./x:body", namespaces=NS)[0]
    source_body_sha = digest(c14n(source_body))
    source_text_sha = digest(normalized_text(source_body).encode("utf-8"))
    source_ids = [value for value in source_root.xpath("//@id") if value]
    id_mapping, id_crosswalk = build_id_crosswalk(source_root)
    source_math_hashes = [digest(c14n(node)) for node in source_root.xpath(".//m:math", namespaces=NS)]
    styles = source_root.xpath("./x:head/x:link[@rel='stylesheet']", namespaces=NS)
    require(len(styles) == 1, "reader must contain one external stylesheet")
    styles[0].set("href", "reader.css")
    id_repairs = remap_ids_and_links(source_root, id_mapping)
    structure_repairs = normalize_content_structures(source_root)
    content_payload = serialize(source_root)
    content_root = parse_xml(content_payload)
    output_body = content_root.xpath("./x:body", namespaces=NS)[0]
    require(digest(normalized_text(output_body).encode("utf-8")) == source_text_sha, "reader text changed during EPUB normalization")
    output_ids = [value for value in content_root.xpath("//@id") if value]
    require(output_ids == [id_mapping[value] for value in source_ids], "reader ID crosswalk was not applied exactly")
    output_math_hashes = [digest(c14n(node)) for node in content_root.xpath(".//m:math", namespaces=NS)]
    require(source_math_hashes == output_math_hashes, "MathML changed during EPUB normalization")
    (oebps / "content.xhtml").write_bytes(content_payload)

    copied: list[dict] = []
    for path in sorted(reader_root.rglob("*")):
        if not path.is_file() or path == reader_root / "index.html":
            continue
        relative = path.relative_to(reader_root)
        require(relative.suffix.lower() in {".css", ".svg", ".ttf", ".txt"}, f"unexpected reader asset: {relative}")
        target = oebps / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        copied.append({"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())})

    nav_payload, nav_metrics = build_navigation(parse_xml(source_payload), config, id_mapping)
    (oebps / "nav.xhtml").write_bytes(nav_payload)
    resources = [
        PurePosixPath(path.relative_to(oebps).as_posix())
        for path in sorted(oebps.rglob("*"))
        if path.is_file()
    ]
    package_payload = build_package(config, digest(content_payload), resources)
    (oebps / "package.opf").write_bytes(package_payload)

    container = etree.Element(f"{{{CONTAINER_NS}}}container", nsmap={None: CONTAINER_NS})
    container.set("version", "1.0")
    rootfiles = etree.SubElement(container, f"{{{CONTAINER_NS}}}rootfiles")
    rootfile = etree.SubElement(rootfiles, f"{{{CONTAINER_NS}}}rootfile")
    rootfile.set("full-path", "OEBPS/package.opf")
    rootfile.set("media-type", "application/oebps-package+xml")
    (destination / "META-INF" / "container.xml").write_bytes(
        etree.tostring(container, encoding="utf-8", xml_declaration=True, pretty_print=True)
    )
    (destination / "mimetype").write_bytes(b"application/epub+zip")

    ids = [value for value in content_root.xpath("//@id") if value]
    return {
        "source_body_c14n_sha256": source_body_sha,
        "output_body_c14n_sha256": digest(c14n(output_body)),
        "source_semantic_text_sha256": source_text_sha,
        "output_semantic_text_sha256": digest(normalized_text(output_body).encode("utf-8")),
        "mathml_sequence_sha256": digest("\n".join(output_math_hashes).encode("ascii")),
        "structure_repairs": structure_repairs,
        "id_repairs": id_repairs,
        "id_crosswalk_rows": id_crosswalk,
        "content_xhtml_sha256": digest(content_payload),
        "content_xhtml_bytes": len(content_payload),
        "mathml_roots": len(content_root.xpath(".//m:math", namespaces=NS)),
        "ids": len(ids),
        "unique_ids": len(set(ids)),
        "copied_assets": copied,
        **nav_metrics,
    }


def create_epub(tree: Path, output: Path, zip_time: tuple[int, int, int, int, int, int]) -> dict:
    if output.exists():
        output.unlink()

    def info(name: str, compression: int) -> zipfile.ZipInfo:
        value = zipfile.ZipInfo(name, zip_time)
        value.compress_type = compression
        value.create_system = 3
        value.external_attr = 0o100644 << 16
        value.flag_bits |= 0x800
        return value

    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        archive.writestr(info("mimetype", zipfile.ZIP_STORED), b"application/epub+zip")
        for path in sorted(tree.rglob("*")):
            if not path.is_file() or path == tree / "mimetype":
                continue
            archive.writestr(info(path.relative_to(tree).as_posix(), zipfile.ZIP_DEFLATED), path.read_bytes())
    return {"bytes": output.stat().st_size, "sha256": digest(output.read_bytes())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == "openlogic-marathi-epub3-config/1", "unsupported EPUB config")
    reader_root = resolve(config["reader_root"])
    release_manifest_path = resolve(config["source_release_manifest"])
    html_qa_path = resolve(config["source_html_qa"])
    checkpoint_path = resolve(config["source_checkpoint"])
    output_epub = resolve(config["output_epub"])
    build_root = resolve(config["build_root"])
    receipt_path = resolve(config["build_receipt"])
    crosswalk_path = resolve(config["id_crosswalk"])
    require(reader_root.is_dir(), "missing accepted reader")
    require(digest((reader_root / "index.html").read_bytes()) == config["expected"]["reader_html_sha256"], "accepted reader hash drift")
    require(digest(checkpoint_path.read_bytes()) == config["expected"]["source_checkpoint_sha256"], "source checkpoint hash drift")

    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    html_qa = json.loads(html_qa_path.read_text(encoding="utf-8"))
    expected = config["expected"]
    require(release_manifest["coverage"]["translated_source_units"] == expected["translated_source_units"], "release unit scope drift")
    require(release_manifest["coverage"]["total_source_units"] == expected["total_source_units"], "corpus scope drift")
    require(release_manifest["coverage"]["aligned_content_segments"] == expected["aligned_content_segments"], "segment scope drift")
    require(html_qa["native_mathml_total"] == expected["native_mathml"], "source HTML MathML scope drift")

    build_root.mkdir(parents=True, exist_ok=True)
    canonical_tree = build_root / "epub-unpacked"
    cold_tree = build_root / "epub-cold-unpacked"
    safe_clear(canonical_tree, build_root)
    safe_clear(cold_tree, build_root)
    canonical_metrics = build_tree(canonical_tree, reader_root, config)
    cold_metrics = build_tree(cold_tree, reader_root, config)
    canonical_inventory = inventory(canonical_tree)
    cold_inventory = inventory(cold_tree)
    require(canonical_inventory == cold_inventory, "cold EPUB tree differs from canonical tree")
    require(canonical_metrics == cold_metrics, "cold EPUB metrics differ from canonical metrics")
    id_crosswalk_rows = canonical_metrics.pop("id_crosswalk_rows")
    cold_id_crosswalk_rows = cold_metrics.pop("id_crosswalk_rows")
    require(id_crosswalk_rows == cold_id_crosswalk_rows, "cold ID crosswalk differs")

    zip_time = (*map(int, config["modified"][:10].split("-")), 0, 0, 0)
    canonical_epub = build_root / "canonical.epub"
    cold_epub = build_root / "cold.epub"
    canonical_zip = create_epub(canonical_tree, canonical_epub, zip_time)
    cold_zip = create_epub(cold_tree, cold_epub, zip_time)
    require(canonical_zip == cold_zip and canonical_epub.read_bytes() == cold_epub.read_bytes(), "cold EPUB bytes differ")
    output_epub.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(canonical_epub, output_epub)
    require(digest(output_epub.read_bytes()) == canonical_zip["sha256"], "release EPUB copy drift")

    crosswalk = {
        "schema": "openlogic-marathi-epub-id-crosswalk/1",
        "release": config["release"],
        "source_reader": {
            "path": config["reader_root"] + "/index.html",
            "sha256": digest((reader_root / "index.html").read_bytes()),
        },
        "epub": {
            "path": config["output_epub"],
            "sha256": canonical_zip["sha256"],
            "content_xhtml_sha256": canonical_metrics["content_xhtml_sha256"],
        },
        "entries": len(id_crosswalk_rows),
        "remapped": sum(row["remapped"] for row in id_crosswalk_rows),
        "identity": sum(not row["remapped"] for row in id_crosswalk_rows),
        "mappings": id_crosswalk_rows,
    }
    crosswalk_path.parent.mkdir(parents=True, exist_ok=True)
    crosswalk_path.write_bytes(json_bytes(crosswalk))

    receipt = {
        "schema": "openlogic-marathi-epub3-build/1",
        "status": "built-deterministically; independent QA and EPUBCheck pending",
        "release": config["release"],
        "source_release": config["source_release"],
        "format": "reflowable EPUB 3",
        "language": config["language"],
        "modified": config["modified"],
        "config": config_path.relative_to(ROOT).as_posix(),
        "config_sha256": digest(config_path.read_bytes()),
        "reader": {
            "path": config["reader_root"] + "/index.html",
            "bytes": (reader_root / "index.html").stat().st_size,
            "sha256": digest((reader_root / "index.html").read_bytes()),
            "tree_sha256": inventory_digest(inventory(reader_root)),
        },
        "source_release_manifest": {"path": config["source_release_manifest"], "sha256": digest(release_manifest_path.read_bytes())},
        "source_html_qa": {"path": config["source_html_qa"], "sha256": digest(html_qa_path.read_bytes())},
        "source_checkpoint": {"path": config["source_checkpoint"], "sha256": digest(checkpoint_path.read_bytes())},
        "id_crosswalk": {
            "path": config["id_crosswalk"],
            "sha256": digest(crosswalk_path.read_bytes()),
            "entries": crosswalk["entries"],
            "remapped": crosswalk["remapped"],
            "identity": crosswalk["identity"],
        },
        "coverage": release_manifest["coverage"],
        "content": canonical_metrics,
        "package_tree": {
            "files": len(canonical_inventory),
            "sha256": inventory_digest(canonical_inventory),
            "cold_sha256": inventory_digest(cold_inventory),
            "byte_identical_cold_build": True,
        },
        "epub": {"path": config["output_epub"], **canonical_zip, "byte_identical_cold_build": True},
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(json_bytes(receipt))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
