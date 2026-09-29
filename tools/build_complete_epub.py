"""Build a complete EPUB from accepted HTML, preserving its text and MathML."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from lxml import etree

import build_epub as base

ROOT = Path(__file__).resolve().parents[1]
X, M, E, O, D = base.XHTML_NS, base.MATHML_NS, base.EPUB_NS, base.OPF_NS, base.DC_NS
NS = {"x": X, "m": M, "opf": O, "dc": D}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base.json_bytes(value))

def rewrite_links(document, owners, current=None):
    for node in document.xpath(".//*[@href]"):
        href = node.get("href") or ""
        split = urlsplit(href)
        if not split.scheme and not split.netloc and not split.path and split.fragment:
            target = unquote(split.fragment)
            base.require(target in owners, f"Missing EPUB fragment owner: {target}")
            node.set("href", ("" if owners[target] == current else owners[target]) + "#" + target)

def normalize_math_glyphs(document, reader):
    """Replace HTML-only glyph images by valid MathML with a CSS fallback."""
    repairs = []
    for node in document.iter(f"{{{M}}}img"):
        before = dict(node.attrib)
        base.require(node.getparent().tag in {f"{{{M}}}mo", f"{{{M}}}mi"}, "Unexpected glyph owner")
        base.require(before.get("class") == "math-glyph", "Unexpected MathML image")
        match = re.fullmatch(r"height:([0-9.]+)em;vertical-align:([-0-9.]+)em", before["style"])
        base.require(match is not None, "Unexpected glyph dimensions")
        graphic = base.parse_xml((reader / before["src"]).read_bytes())
        _, _, width, height = map(float, graphic.get("viewBox").split())
        scale = float(match[1]) / height
        width_em = f"{width * scale:.6f}".rstrip("0").rstrip(".") + "em"
        height_em, valign = match[1] + "em", match[2] + "em"
        node.tag = f"{{{M}}}mglyph"
        node.attrib.clear()
        node.set("src", before["src"])
        node.set("alt", before["alt"])
        node.set("width", width_em)
        node.set("height", height_em)
        node.set("valign", valign)
        node.set("class", "epub-math-glyph")
        node.set("style", f"background-image:url({before['src']});width:{width_em};height:{height_em};vertical-align:{valign}")
        repairs.append({"source": before, "epub": dict(node.attrib)})
    return repairs

def make_tree(destination, reader, config):
    destination.mkdir(parents=True, exist_ok=True)
    oebps = destination / "OEBPS"
    oebps.mkdir()
    (destination / "META-INF").mkdir()
    payload = (reader / "index.html").read_bytes()
    source = base.parse_xml(payload)
    source_body = source.xpath("./x:body", namespaces=NS)[0]
    source_math = [sha(base.c14n(n)) for n in source.iter(f"{{{M}}}math")]
    original_ids = source.xpath("//@id")
    transformed = copy.deepcopy(source)
    glyph_repairs = normalize_math_glyphs(transformed, reader)
    original_text = base.normalized_text(transformed.xpath("./x:body", namespaces=NS)[0])
    original_math = [sha(base.c14n(n)) for n in transformed.iter(f"{{{M}}}math")]
    mapping, crosswalk = base.build_id_crosswalk(transformed)
    id_repairs = base.remap_ids_and_links(transformed, mapping)
    structure_repairs = base.normalize_content_structures(transformed)
    body = transformed.xpath("./x:body", namespaces=NS)[0]
    mains = body.xpath("./x:main", namespaces=NS)
    base.require(len(mains) == 1, "Accepted reader must have one main element")
    main = mains[0]
    base.require(all(n is main or etree.QName(n).localname == "a" for n in body), "Unexpected top-level reader structure")
    groups = [[]]
    for node in list(main):
        if etree.QName(node).localname in {"h1", "h2"} and groups[-1]:
            groups.append([])
        groups[-1].append(node)
    documents = []
    for index, group in enumerate(groups):
        filename = f"content-{index:03d}.xhtml"
        document = etree.Element(transformed.tag, attrib=dict(transformed.attrib), nsmap=transformed.nsmap)
        document.set("lang", config["language"])
        document.set(f"{{{base.XML_NS}}}lang", config["language"])
        document.text = transformed.text
        document.append(copy.deepcopy(transformed.xpath("./x:head", namespaces=NS)[0]))
        base.element("link", document.xpath("./x:head", namespaces=NS)[0], rel="stylesheet", href="epub-glyphs.css")
        document_body = etree.SubElement(document, body.tag, attrib=dict(body.attrib), nsmap=body.nsmap)
        document_body.tail = body.tail
        document_body.text = body.text if index == 0 else None
        if index == 0:
            for node in body:
                if node is not main:
                    document_body.append(copy.deepcopy(node))
        document_main = etree.Element(main.tag, nsmap=main.nsmap, attrib=dict(main.attrib))
        if index:
            document_main.attrib.pop("id", None)
            document_main.attrib.pop("data-source-id", None)
        document_main.text = main.text if index == 0 else None
        document_main.tail = main.tail if index + 1 == len(groups) else None
        for node in group:
            document_main.append(copy.deepcopy(node))
        document_body.append(document_main)
        documents.append((filename, document))
    owners = {}
    for filename, document in documents:
        for identifier in document.xpath("//@id"):
            base.require(identifier not in owners, f"Repeated ID across the reading spine: {identifier}")
            owners[identifier] = filename
    base.require(set(owners) == set(mapping.values()), "Spine split lost source IDs")
    text = " ".join(base.normalized_text(doc.xpath("./x:body", namespaces=NS)[0]) for _, doc in documents)
    base.require(text == original_text, "Spine split changed accepted semantic text")
    math = [sha(base.c14n(n)) for _, doc in documents for n in doc.xpath(".//m:math", namespaces=NS)]
    base.require(math == original_math, "Spine split changed accepted MathML trees")
    for filename, document in documents:
        rewrite_links(document, owners, filename)
        (oebps / filename).write_bytes(base.serialize(document))
    for path in sorted(reader.rglob("*")):
        if path.is_file() and path.name != "index.html":
            relative = path.relative_to(reader)
            base.require(relative.suffix.lower() in {".css", ".svg", ".ttf", ".txt"}, f"Unexpected reader asset: {relative}")
            target = oebps / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    (oebps / "epub-glyphs.css").write_text(
        "mglyph.epub-math-glyph{display:inline-block;background-size:100% 100%;background-repeat:no-repeat}\n"
        ".center{overflow-x:auto}\n"
        ".center>table{border-collapse:collapse;min-width:max-content}\n"
        ".center>table td{white-space:nowrap;padding:.1rem .5rem}\n",
        encoding="utf-8", newline="\n")
    nav = etree.Element(f"{{{X}}}html", nsmap={None: X, "epub": E})
    nav.set("lang", config["language"])
    nav.set(f"{{{base.XML_NS}}}lang", config["language"])
    head = base.element("head", nav)
    base.element("title", head).text = "अनुक्रमणिका — " + config["title"]
    base.element("link", head, rel="stylesheet", href="reader.css")
    nav_body = base.element("body", nav)
    base.element("h1", nav_body).text = config["title"]
    base.element("p", nav_body).text = "संपूर्ण मराठी EPUB: सर्व 722 स्रोत-एकके; मुख्य ग्रंथातील 79 प्रकरणे आणि 613 विभाग."
    toc = base.element("nav", nav_body, id="toc")
    toc.set(f"{{{E}}}type", "toc")
    toc.set("aria-label", "अनुक्रमणिका")
    base.element("h2", toc).text = "अनुक्रमणिका"
    source_nav = transformed.xpath(".//x:nav[@id='TOC']", namespaces=NS)
    base.require(len(source_nav) == 1, "Accepted TOC is missing")
    for child in source_nav[0]:
        if etree.QName(child).localname == "h2":
            continue
        clone = copy.deepcopy(child)
        for node in [clone, *clone.xpath(".//*[local-name()='ul']")]:
            if etree.QName(node).localname == "ul":
                node.tag = f"{{{X}}}ol"
        rewrite_links(clone, owners)
        toc.append(clone)
    landmarks = base.element("nav", nav_body)
    landmarks.set(f"{{{E}}}type", "landmarks")
    base.element("h2", landmarks).text = "प्रमुख ठिकाणे"
    listing = base.element("ol", landmarks)
    for label, href, kind in (("अनुक्रमणिका", "nav.xhtml#toc", "toc"),
                               ("मुख्य मजकूर", owners["main-content"] + "#main-content", "bodymatter")):
        link = base.element("a", base.element("li", listing), href=href)
        link.set(f"{{{E}}}type", kind)
        link.text = label
    (oebps / "nav.xhtml").write_bytes(base.serialize(nav))
    package = etree.Element(f"{{{O}}}package", nsmap={None: O, "dc": D})
    package.set("version", "3.0")
    package.set("unique-identifier", "pub-id")
    package.set(f"{{{base.XML_NS}}}lang", config["language"])
    package.set("prefix", "schema: http://schema.org/ rendition: http://www.idpf.org/vocab/rendition/#")
    metadata = etree.SubElement(package, f"{{{O}}}metadata")
    identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, "openlogic-complete-epub:" + sha(payload)))
    for key, value in (("identifier", "urn:uuid:" + identifier), ("title", config["title"]),
                       ("language", config["language"]), ("creator", "Open Logic Project"),
                       ("contributor", config["model_notice_mr"]), ("publisher", "OpenLogic भाषांतर प्रकल्प"),
                       ("date", config["modified"][:10]), ("description", config["description"]),
                       ("rights", "मजकूर व रूपांतर CC BY 4.0; स्वतंत्र घटकांचे परवाने जतन केले आहेत.")):
        element = etree.SubElement(metadata, f"{{{D}}}{key}")
        element.text = value
        if key == "identifier":
            element.set("id", "pub-id")
    for key, value in (("dcterms:modified", config["modified"]), ("rendition:layout", "reflowable"),
                       ("schema:accessMode", "textual"), ("schema:accessMode", "visual"),
                       ("schema:accessibilitySummary", config["accessibility_summary_mr"]),
                       *[("schema:accessibilityFeature", v) for v in ("MathML", "alternativeText", "readingOrder", "structuralNavigation", "tableOfContents")]):
        etree.SubElement(metadata, f"{{{O}}}meta", property=key).text = value
    manifest = etree.SubElement(package, f"{{{O}}}manifest")
    identifiers = {}
    for path in sorted(p for p in oebps.rglob("*") if p.is_file()):
        relative = PurePosixPath(path.relative_to(oebps).as_posix())
        identifier = base.item_id(relative)
        identifiers[relative.as_posix()] = identifier
        item = etree.SubElement(manifest, f"{{{O}}}item", id=identifier, href=relative.as_posix(), **{"media-type": base.media_type(relative)})
        properties = ["nav"] if relative.name == "nav.xhtml" else []
        if relative.suffix == ".xhtml":
            parsed = base.parse_xml(path.read_bytes())
            if parsed.xpath(".//m:math", namespaces=NS):
                properties.append("mathml")
            if parsed.xpath(".//*[namespace-uri()='http://www.w3.org/2000/svg']"):
                properties.append("svg")
        if properties:
            item.set("properties", " ".join(properties))
    spine = etree.SubElement(package, f"{{{O}}}spine")
    etree.SubElement(spine, f"{{{O}}}itemref", idref=identifiers["nav.xhtml"], linear="no")
    for filename, _ in documents:
        etree.SubElement(spine, f"{{{O}}}itemref", idref=identifiers[filename])
    (oebps / "package.opf").write_bytes(etree.tostring(package, encoding="utf-8", xml_declaration=True, pretty_print=True))
    container = etree.Element(f"{{{base.CONTAINER_NS}}}container", nsmap={None: base.CONTAINER_NS}, version="1.0")
    rootfiles = etree.SubElement(container, f"{{{base.CONTAINER_NS}}}rootfiles")
    etree.SubElement(rootfiles, f"{{{base.CONTAINER_NS}}}rootfile", **{"full-path": "OEBPS/package.opf", "media-type": "application/oebps-package+xml"})
    (destination / "META-INF/container.xml").write_bytes(etree.tostring(container, encoding="utf-8", xml_declaration=True))
    (destination / "mimetype").write_bytes(b"application/epub+zip")
    return {"reading_documents": len(documents), "semantic_text_sha256": sha(original_text.encode()),
            "mathml_sequence_sha256": sha("\n".join(original_math).encode()), "mathml_roots": len(math),
            "accepted_mathml_sequence_sha256": sha("\n".join(source_math).encode()),
            "mathml_glyph_projection": glyph_repairs,
            "mathml_roots_with_glyph_projection": sum(a != b for a, b in zip(source_math, original_math)),
            "source_ids": len(original_ids), "owners": owners, "id_crosswalk": crosswalk,
            "id_repairs": id_repairs, "structure_repairs": structure_repairs}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config_path.relative_to(ROOT)
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    base.require(config["schema"] == "openlogic-mr-complete-epub-config/1", "Wrong config")
    reader = base.resolve(config["reader_root"])
    base.require(sha((reader / "index.html").read_bytes()) == config["reader_html_sha256"], "Accepted HTML drift")
    build = base.resolve(config["build_root"])
    build.mkdir(parents=True, exist_ok=True)
    inventories, metrics, epub_bytes = [], [], []
    for name in ("canonical", "cold"):
        tree = build / (name + "-tree")
        base.safe_clear(tree, build)
        metrics.append(make_tree(tree, reader, config))
        inventories.append(base.inventory(tree))
        target = build / (name + ".epub")
        base.create_epub(tree, target, (*map(int, config["modified"][:10].split("-")), 0, 0, 0))
        epub_bytes.append(target.read_bytes())
    base.require(inventories[0] == inventories[1] and metrics[0] == metrics[1], "Cold package tree drift")
    base.require(epub_bytes[0] == epub_bytes[1], "Cold EPUB byte drift")
    output = base.resolve(config["output_epub"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(epub_bytes[0])
    receipt = {"schema": "openlogic-mr-complete-epub-build/1", "status": "built-pending-independent-QA",
               "epub": {"filename": output.name, "bytes": len(epub_bytes[0]), "sha256": sha(epub_bytes[0])},
               "reader_html_sha256": config["reader_html_sha256"], "config_sha256": sha(config_path.read_bytes()),
               "cold_epub_byte_identity": True, "cold_tree_byte_identity": True,
               "tree_sha256": base.inventory_digest(inventories[0]), "content": metrics[0]}
    save(base.resolve(config["build_receipt"]), receipt)
    print(json.dumps({"status": receipt["status"], "epub": receipt["epub"], "reading_documents": metrics[0]["reading_documents"], "mathml_roots": metrics[0]["mathml_roots"]}))

if __name__ == "__main__":
    main()
