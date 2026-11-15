"""Keep translation audit records in the build evidence and preserve the author's notes."""
import re

from complete_reader_notes import HEADING, active_text, legacy_variants, normalize, project_note, sha, source_notes

AUDIT_ID = re.compile(r"^(?:SOL6-A|OL(?:FOL|INC|CMP|SIZ|AXD|COM|FUN|NOTE)-|MR(?:ARITH|SIZ|PL)-)\d+\b")
QUOTE = re.compile(r"\\begin\{quote\}\\small\\textbf\{(?:स्रोतनोंद|स्रोतदुरुस्ती)\.\}\s*((?:(?!\\(?:begin|end)\{quote\}).)*)\\end\{quote\}", re.S)
BIBLIOGRAPHY = r"\chapter*{संदर्भ}"


def separate_notes(root, manifest, reader):
    notes = list(source_notes(root, manifest))
    lookup = {}
    for row, note in notes:
        for variant in [project_note(note), *legacy_variants(note)]:
            lookup[normalize(variant)] = row, note
    before, heading, tail = reader.partition(HEADING)
    appendix, bib, after = tail.partition(BIBLIOGRAPHY)
    if (not heading or not bib or HEADING in tail or BIBLIOGRAPHY in after
            or "या नोंदी अनुवादकाने" not in appendix):
        raise ValueError("Could not identify the translation team's own notes appendix")
    if re.search(r"\\(?:label|ollabel|include|input|chapter|olsection)\s*[\[{*]", appendix):
        raise ValueError("Translation notes appendix contains additional numbered or imported material")
    removed = []
    def keep_scholarly_quote(match):
        hit = lookup.get(normalize(match[1]))
        if not hit:
            raise ValueError("Source-note quotation has no matching original record")
        row, note = hit
        if not AUDIT_ID.match(note):
            return match[0]
        removed.append(row)
        return ""
    text = QUOTE.sub(keep_scholarly_quote, before) + bib + after
    ordinary = [(row, note) for row,note in notes if not AUDIT_ID.match(note)]
    missing = [project_note(note) for _,note in ordinary if normalize(project_note(note)) not in normalize(active_text(text))]
    if missing:
        text = text.replace(bib, r"\section*{अनुवादकाच्या नोंदी}"+"\n\n"+"\n\n".join(missing)+"\n\n"+bib, 1)
    return text, {"schema":"openlogic-mr-reader-note-separation/2",
                  "source_note_count":len(notes), "notes":[row for row,_ in notes],
                  "retained_scholarly_notes":len(ordinary), "inline_audit_quotes_removed":removed,
                  "historical_appendix_sha256":sha((heading+appendix).encode())}, heading+appendix


def verify_separation(root, manifest, reader, receipt):
    active = normalize(active_text(reader))
    expected = list(source_notes(root, manifest))
    if receipt["reader_sha256"] != sha(reader.encode()) or receipt["notes"] != [r for r,_ in expected]:
        raise ValueError("Current translated sources or the reader differ from note evidence")
    if HEADING in reader or receipt["source_note_count"] != len(expected):
        raise ValueError("Reader contains the historical audit appendix or its scope changed")
    # Compare original keyed notes against the finished active text, including
    # punctuation/spacing variants used by the historical assemblers.
    for _, note in expected:
        if AUDIT_ID.match(note):
            if AUDIT_ID.match(note)[0] in active:
                raise ValueError("Translation audit identifier remains in reader: "+AUDIT_ID.match(note)[0])
        elif normalize(project_note(note)) not in active:
            raise ValueError("A scholarly translator's note was lost")
    return len(expected)
