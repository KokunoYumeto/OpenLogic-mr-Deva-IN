"""Bind review units to actual PDF destinations, stating heading-level precision."""
import hashlib
import json
import re
from pathlib import Path

import fitz


def group(text, position):
    assert text[position] == "{"
    depth, start = 1, position + 1
    position += 1
    while depth:
        assert position < len(text)
        if text[position] == "{" and (position == 0 or text[position - 1] != "\\"):
            depth += 1
        elif text[position] == "}" and (position == 0 or text[position - 1] != "\\"):
            depth -= 1
        position += 1
    return text[start:position - 1], position


def bind_units(root, manifest):
    build = root / "build/full"
    pdf_path = build / "openlogic-mr-full.pdf"
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    receipt = json.loads((build / "TEX_BUILD_RECEIPT.json").read_text(encoding="utf-8-sig"))
    assert receipt["result"] == "built-log-clean" and receipt["pdf"]["sha256"] == pdf_hash
    inputs = json.loads((build / "INPUTS.json").read_text(encoding="utf-8"))
    assert inputs["reader_sha256"] == receipt["texInputSha256"]
    assert hashlib.sha256((build / "openlogic-mr-full.tex").read_bytes()).hexdigest() == inputs["reader_sha256"]
    input_units = {row["unit_id"]: row for row in inputs["input_units"]}
    assert len(input_units) == 722 and set(input_units) == set(manifest)
    for uid, unit in manifest.items():
        binding = input_units[uid]
        assert binding["source_path"] == "upstream/" + unit["source_path"]
        assert binding["target_path"] == "mr/" + unit["source_path"]
        assert hashlib.sha256((root / binding["source_path"]).read_bytes()).hexdigest() == binding["source_sha256"]
        assert hashlib.sha256((root / binding["target_path"]).read_bytes()).hexdigest() == binding["target_sha256"], f"Reader must be rebuilt before binding revised unit {uid}"
    aux_path = build / "openlogic-mr-full.aux"
    aux_hash = hashlib.sha256(aux_path.read_bytes()).hexdigest()
    labels = {}
    for line in aux_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith(r"\newlabel{"):
            continue
        label, position = group(line, len(r"\newlabel"))
        if label.endswith("@cref"):
            continue
        contents, _ = group(line, position)
        fields, position = [], 0
        while position < len(contents) and contents[position] == "{":
            value, position = group(contents, position)
            fields.append(value)
        if len(fields) < 4:
            # Rotating-package RF labels carry no hyperlink destination.
            continue
        labels[label] = {"printed_page": fields[1], "destination": fields[3]}
    doc = fitz.open(pdf_path)
    destinations = doc.resolve_names()
    outline = doc.get_toc(simple=False)
    special = {
        "OLP-0001": "ओपन लॉजिक प्रकल्पाविषयी",
        "OLP-0002": "मूळ संपूर्ण-सामग्री चालकाची संपादकीय नोंद",
        "OLP-0004": "संच",
        "OLP-0274": "अपूर्णता",
        "OLP-0322": "द्वितीय-क्रम तर्कशास्त्र",
        "OLP-0660": "अंतःप्रज्ञावादी कट-निर्मूलनातील पूरक प्रसंग",
        "OLP-0705": "पूरक rules-G1i नियमसारणी",
        "OLP-0708": "पूरक rules-G3i नियमसारणी",
        "OLP-0709": "पूरक rules-LK नियमसारणी",
        "OLP-0710": "पूरक rules-mG3i नियमसारणी",
    }
    result, unresolved = {}, []
    for uid, unit in manifest.items():
        raw = (root / "mr" / unit["source_path"]).read_text(encoding="utf-8")
        raw = re.sub(r"(?m)^\s*%.*$", "", raw)
        candidates = []
        if "source-driver:" + uid in labels:
            candidates.append("source-driver:" + uid)
        # These two source drivers have no separate part heading in the
        # integrated route; point explicitly to the first included chapter.
        inherited_heading = {"OLP-0055": "pl:syn::chap", "OLP-0252": "tur:mac::chap"}
        if uid in inherited_heading:
            candidates.append(inherited_heading[uid])
        for parts in re.findall(r"\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}", raw):
            prefix = ":".join(parts) + ("-alt" if uid == "OLP-0643" else "")
            candidates.append(prefix + ":sec")
        for part, chapter in re.findall(r"\\olchapter\{([^}]+)\}\{([^}]+)\}", raw):
            candidates += [f"{part}:{chapter}:chap", f"{part}:{chapter}::chap"]
        for part in re.findall(r"\\olpart\{([^}]+)\}", raw):
            candidates += [f"{part}:part", f"{part}:::part"]
        if not candidates and uid not in special:
            for label in re.findall(r"\\ollabel\{([^}]+)\}", raw):
                matches = [key for key in labels if key.endswith(":" + label)]
                if len(matches) == 1:
                    candidates += matches
        chosen = next((key for key in candidates if key in labels), None)
        if chosen:
            entry = labels[chosen]
            destination = destinations.get(entry["destination"])
            assert destination is not None, (uid, chosen, entry)
            physical = destination.get("page", destination.get("pageno")) + 1
            assert 1 <= physical <= len(doc)
            printed = doc[physical - 1].get_label() or str(physical)
            provenance = (f"संकलित .aux मधील {chosen} आणि PDF मधील {entry['destination']} "
                          f"या प्रत्यक्ष स्थळाची पडताळणी; .aux SHA-256 {aux_hash}; .aux मधील पृष्ठनोंद {entry['printed_page']}. "
                          "हा एककाच्या शीर्षकाचा किंवा नियमसारणीचा निर्देश आहे; खंडाच्या ओळीचे तंतोतंत पृष्ठ नाही.")
            if uid in inherited_heading:
                provenance += " मूळ भाग-चालक येथे स्वतंत्र भागशीर्षकाशिवाय समाविष्ट आहे; निर्देश त्याच्या पहिल्या प्रकरणाचा आहे."
        elif uid in special:
            entries = [item for item in outline if re.sub(r"^\d+\s+", "", item[1]) == special[uid]
                       and (not re.search(r"\\olpart\{", raw) or item[0] == 1)]
            assert len(entries) == 1, (uid, special[uid], entries)
            physical = entries[0][2]
            # This reader uses the physical page number as its printed Arabic page label.
            page_labels = doc.get_page_labels()
            printed = doc[physical - 1].get_label() if page_labels else str(physical)
            provenance = (f"PDF च्या प्रत्यक्ष अनुक्रमणिकेतील ‘{special[uid]}’ शीर्षकाची सुरुवात. "
                          "हा शीर्षकाचा निर्देश आहे; खंडाच्या ओळीचे तंतोतंत पृष्ठ नाही.")
            chosen = "PDF outline: " + special[uid]
        else:
            unresolved.append({"unit_id": uid, "candidates": candidates})
            continue
        result[uid] = {"status": "available", "artifact_filename": "01-openlogic-mr-complete.pdf",
                       "artifact_sha256": pdf_hash, "profile": "complete-reader-heading",
                       "printed_page": printed, "assembled_pdf_page": physical,
                       "provenance": provenance}
    return result, unresolved, {"pdf_sha256": pdf_hash, "aux_sha256": aux_hash,
                                "bound_units": len(result), "unresolved_units": unresolved,
                                "precision": "प्रत्यक्ष शीर्षक किंवा नियमसारणी; शब्दाच्या ओळीचे तंतोतंत पृष्ठ नाही"}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    manifest = {row["unit_id"]: row for row in
                map(json.loads, (root / "provenance/SOURCE_MANIFEST.jsonl").read_text(encoding="utf-8").splitlines())}
    bindings, unresolved, report = bind_units(root, manifest)
    (root / "build/full/REVIEW_READER_BINDING.json").write_text(
        json.dumps({"units": bindings, "qa": report}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bound_units": len(bindings), "unresolved": unresolved}, ensure_ascii=False))
