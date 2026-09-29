"""Preserve editorial prose from every translated part and chapter driver."""
import hashlib
import re


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def group(text, start):
    assert text[start] == "{"
    position, depth = start + 1, 1
    while depth:
        if text[position] == "{" and text[position - 1] != "\\":
            depth += 1
        elif text[position] == "}" and text[position - 1] != "\\":
            depth -= 1
        position += 1
    return text[start + 1:position - 1], position


def preserve_notes(root, manifest, reader, selected, replace_tokens, projections):
    labels = set(re.findall(r"\\label\{([^}]+)\}", reader))
    missing, inventory, verified_notes = [], [], []
    for uid, unit in manifest.items():
        path = root / "mr" / unit["source_path"]
        raw = path.read_text(encoding="utf-8")
        header = re.search(r"\\ol(part|chapter)\{", raw)
        if not header:
            continue
        arguments, position = [], header.end() - 1
        for _ in range(2 if header[1] == "part" else 3):
            value, position = group(raw, position)
            arguments.append(value)
        parts = [arguments[0], "", ""] if header[1] == "part" else arguments[:2] + [""]
        title = replace_tokens(arguments[-1])
        blocks = []
        for index, match in enumerate(re.finditer(r"\\begin\{editorial\}(.*?)\\end\{editorial\}", selected(raw), re.S)):
            content = replace_tokens(match[1])
            for original, projection in projections.items():
                content = content.replace(original, projection)

            def reference(match):
                options = re.findall(r"\[([^]]*)\]", match[1])
                assert len(options) <= 3
                key_parts = parts.copy()
                if options:
                    key_parts[3 - len(options):] = options
                key = ":".join(key_parts) + ":" + match[2]
                assert key in labels, (uid, key)
                return r"\ref{" + key + "}"

            content = re.sub(r"\\(?:olref|Olref)((?:\[[^]]*\])*)\{([^}]+)\}", reference, content)
            assert not re.search(r"\\(?:olref|Olref|tagrefs|iftag|subfile)\b|!!", content), uid
            verified_notes.append((uid, content))
            present = normalize(content) in normalize(reader)
            inventory.append({"unit_id": uid, "editorial_block": index + 1,
                              "translation_path": path.relative_to(root).as_posix(),
                              "translation_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "projected_note_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                              "status": "already_in_reader" if present else "appended_to_supplement"})
            if not present:
                blocks.append(r"\begin{editorial}" + content + r"\end{editorial}")
        if blocks:
            missing += [r"\subsection{" + title + " — मूळ संपादकीय नोंद}" + r"\label{source-driver:" + uid + "}",
                        "\n".join(blocks)]
    if missing:
        addition = (r"\section{मूळ विभाग-चालकांच्या संपादकीय नोंदी}\label{source-driver:notes}" + "\n"
                    "खालील नोंदी मूळ विभाग आणि प्रकरण-चालकांमधील आहेत. त्या मूळ ग्रंथाच्या संकलनमार्गांविषयी सांगतात; प्रस्तुत आवृत्तीविषयी नवे संपादकीय दावे नाहीत.\n"
                    + "\n".join(missing) + "\n")
        marker = r"\chapter*{स्रोतावरील संपादकीय नोंदी}"
        assert reader.count(marker) == 1
        reader = reader.replace(marker, addition + marker, 1)
    # Replay every projected note after the repair, rather than counting drivers.
    for uid, content in verified_notes:
        assert normalize(content) in normalize(reader), uid
    return reader, {"schema": "openlogic-mr-driver-editorial-coverage/1",
                    "editorial_blocks": len(inventory), "appended_blocks": sum(row["status"] == "appended_to_supplement" for row in inventory),
                    "appended_units": sorted({row["unit_id"] for row in inventory if row["status"] == "appended_to_supplement"}),
                    "notes": inventory}
