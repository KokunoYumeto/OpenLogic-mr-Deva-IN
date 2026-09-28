"""Render cited entries from the frozen local BibTeX file without TeX."""
import hashlib
import re


def braced(text, start):
    assert text[start] == "{"
    depth, pos = 1, start + 1
    while depth:
        assert pos < len(text), text[start:start + 80]
        if text[pos] == "{" and text[pos - 1] != "\\":
            depth += 1
        elif text[pos] == "}" and text[pos - 1] != "\\":
            depth -= 1
        pos += 1
    return text[start + 1:pos - 1], pos


def parse_bib(text):
    records, pos = {}, 0
    while match := re.search(r"@([A-Za-z]+)\s*\{", text[pos:]):
        kind = match.group(1).lower()
        start = pos + match.end() - 1
        body, pos = braced(text, start)
        assert kind not in {"string", "preamble", "comment"}, kind
        key, body = body.split(",", 1)
        key = key.strip()
        assert key not in records, key
        fields, at = {}, 0
        while at < len(body):
            skip = re.match(r"[\s,]*", body[at:])
            at += skip.end()
            if at == len(body):
                break
            field = re.match(r"([A-Za-z]+)\s*=\s*", body[at:])
            assert field, (key, body[at:at + 80])
            name = field.group(1).lower()
            at += field.end()
            if body[at] == "{":
                value, at = braced(body, at)
            elif body[at] == '"':
                end = at + 1
                while body[end] != '"' or body[end - 1] == "\\":
                    end += 1
                value, at = body[at + 1:end], end + 1
            else:
                end = at
                while end < len(body) and body[end] != ",":
                    end += 1
                value, at = body[at:end].strip(), end
                assert re.fullmatch(r"\d+", value), (key, name, value)
            assert name not in fields or fields[name] == value, (key, name)
            fields[name] = re.sub(r"\s+", " ", value).strip()
        records[key] = {"kind": kind, **fields}
    return records


def citation_keys(text):
    return {key.strip()
            for match in re.finditer(r"\\cite[A-Za-z]*\*?(?:\[[^]]*\])*\{([^{}]+)\}", text)
            for key in match.group(1).split(",")}


def render_bibliography(root, inputs):
    path = root / "upstream/bib/open-logic.bib"
    records = parse_bib(path.read_text(encoding="utf-8"))
    cited_keys = set()
    for row in inputs:
        cited_keys.update(citation_keys((root / row["path"]).read_text(encoding="utf-8")))
    keys = set(cited_keys)
    assert keys <= records.keys(), sorted(keys - records.keys())
    # BibTeX notes sometimes cite another record. Render that transitive
    # closure too, or the local bibliography leaves visible [?] references.
    pending = list(keys)
    while pending:
        key = pending.pop()
        linked = set().union(*(citation_keys(value) for value in records[key].values()))
        assert linked <= records.keys(), (key, sorted(linked - records.keys()))
        for other in linked - keys:
            keys.add(other)
            pending.append(other)
    note_citation_links = 0

    def link_note_citation(match):
        nonlocal note_citation_links
        _command, options, keys_arg = match.groups()
        locator = ", ".join(re.findall(r"\[([^]]*)\]", options))
        rendered = []
        for key in (part.strip() for part in keys_arg.split(",")):
            assert key in keys, key
            rec = records[key]
            author = rec.get("author", rec.get("editor", ""))
            first = author.split(" and ")[0]
            surname = first.split(",", 1)[0] if "," in first else first.split()[-1]
            label = surname.strip("{}") + " " + rec["year"]
            if locator:
                label += ", " + locator
            rendered.append(r"\hyperref[bib:" + key + "]{" + label + "}")
            note_citation_links += 1
        return "; ".join(rendered)

    chunks = [
        r"\chapter*{संदर्भ}", r"\addcontentsline{toc}{chapter}{संदर्भ}",
        "खालील संदर्भ मूळ स्रोताच्या ग्रंथसूचीवरून घेतले आहेत. लेखकांची नावे, "
        "प्रकाशनांची मूळ शीर्षके आणि ग्रंथसूचीतील तपशील ओळखीसाठी मूळ भाषेत ठेवले आहेत. "
        "ही नोंद दुव्यांच्या सध्याच्या उपलब्धतेची पडताळणी नाही.\n",
    ]
    for key in sorted(keys, key=lambda k: (
            records[k].get("author", records[k].get("editor", "")).casefold(),
            records[k].get("year", ""), k)):
        rec = records[key]
        author = rec.get("author", rec.get("editor", ""))
        assert author and rec.get("title") and rec.get("year"), key
        if "author" not in rec:
            author += " (संपा.)"
        author = author.replace(" and ", "; ")
        parts = [author + " (" + rec["year"] + ").",
                 r"\emph{" + rec["title"] + "}."]
        if "booktitle" in rec:
            parts.append("मध्ये: " + r"\emph{" + rec["booktitle"] + "}.")
        if "journal" in rec:
            journal = r"\emph{" + rec["journal"] + "}"
            if "volume" in rec:
                journal += ", " + rec["volume"]
                if "number" in rec:
                    journal += "(" + rec["number"] + ")"
            if "pages" in rec:
                journal += ", " + rec["pages"]
            parts.append(journal + ".")
        elif "pages" in rec:
            parts.append("पृ.~" + rec["pages"] + ".")
        for name in ("edition", "publisher", "institution", "address", "note"):
            if name in rec:
                suffix = " आवृत्ती." if name == "edition" else "."
                parts.append(rec[name] + suffix)
        for name in ("url", "doi", "eprint"):
            if name in rec:
                value = rec[name]
                if name == "doi":
                    value = "https://doi.org/" + value
                elif name == "eprint":
                    value = "https://arxiv.org/abs/" + value
                parts.append(r"\url{" + value + "}.")
        entry = " ".join(parts)
        entry = re.sub(r"\\(cite[A-Za-z]*\*?)((?:\[[^]]*\])*)\{([^{}]+)\}",
                       link_note_citation, entry)
        assert not citation_keys(entry), key
        chunks.append(r"\par\medskip\phantomsection\label{bib:" + key + "}\n"
                      + entry)
    return "\n\n".join(chunks), {
        "source_bib": path.relative_to(root).as_posix(),
        "source_bib_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cited_keys": sorted(cited_keys), "rendered_keys": sorted(keys),
        "bibliography_note_citation_links_rendered": note_citation_links,
        "scope": "All citation keys in the source-aligned target inputs and their transitive bibliography-note citations; metadata copied from the frozen bibliography, not independently verified.",
    }
