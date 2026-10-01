"""Preserve every explicit READERNOTE in the full reader and verify its binding."""
import hashlib
import re

NOTE = re.compile(r'(?m)^[ \t]*%READERNOTE\{(.*)\}[ \t]*$')
HEADING = r'\chapter*{स्रोतावरील संपादकीय नोंदी}'
TOC_ENTRY = r'\addcontentsline{toc}{chapter}{स्रोतावरील संपादकीय नोंदी}'
MATH = {
    'δ':r'\delta', 'λ':r'\lambda', 'σ':r'\sigma',
    '→':r'\to', '∈':r'\in', '∉':r'\notin', '≈':r'\approx',
    '〈':r'\langle', '〉':r'\rangle', '−':'-', '√':r'\surd',
}
ESCAPES = {'\\':r'\textbackslash{}','{':r'\{','}':r'\}',
           '#':r'\#','_':r'\_','&':r'\&','%':r'\%','$':r'\$',
           '^':r'\textasciicircum{}','~':r'\textasciitilde{}','!':'{!}'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()

def active_text(tex):
    return re.sub(r'(?<!\\)%[^\n]*', '', tex)

def project_note(note):
    """Escape prose while retaining its explicit inline math and live hrefs."""
    protected = []
    def protect(tex):
        key = chr(0xE000 + len(protected))
        protected.append((key, tex))
        return key
    def href(match):
        url, label = match.groups()
        assert re.fullmatch(r'https://[^{}\s\\]+', url), url
        # Keep hyperref's URL argument intact. Labels use the same safe prose
        # projection; URLs cannot be mistaken for subscripts or TeX comments.
        escaped_url = url.replace('%',r'\%').replace('#',r'\#')
        return protect(r'\href{' + escaped_url + '}{' + project_note(label) + '}')
    note = re.sub(r'\\href\{([^{}]+)\}\{([^{}]+)\}', href, note)
    def live_url(match):
        url = match[1]
        assert re.fullmatch(r'https://[^{}\s\\]+', url), url
        # Only the URL command is retained; arbitrary note TeX stays escaped.
        # Hyperref handles URL underscores and tildes as URL characters.
        escaped_url = url.replace('%',r'\%').replace('#',r'\#')
        return protect(r'\url{' + escaped_url + '}')
    note = re.sub(r'\\url\{([^{}]+)\}', live_url, note)
    def inline_math(match):
        assert match[1] == 'n', ('Unsupported explicit READERNOTE math', match[1])
        return protect('$n$')
    note = re.sub(r'\$([^$]+)\$', inline_math, note)
    note = note.replace('√2', protect(r'\ensuremath{\sqrt{2}}'))
    note = ''.join(r'\ensuremath{' + MATH[c] + '}' if c in MATH else ESCAPES.get(c,c)
                   for c in note)
    for key, tex in protected:
        note = note.replace(key, tex)
    assert not re.search(r'[\uE000-\uF8FF]', note)
    return note

def legacy_variants(note):
    """Recognize only the exact historical projections used by the assemblers."""
    core = re.sub('〈([^〉]+)〉', lambda m:r'$\langle '+m[1]+r'\rangle$', note)
    core = core.replace('x∈A', r'$x\in A$').replace('√2', r'$\sqrt{2}$').replace('λ',r'$\lambda$')
    core = re.sub(r'\b0\^R\b', r'$0^R$', core).replace('_',r'\_')
    supplement = note
    for old,new in [('_',r'\_'),('^',r'\textasciicircum{}'),('&',r'\&'),('%',r'\%')]:
        supplement = supplement.replace(old,new)
    return [note,core,supplement]

def source_notes(root, manifest):
    for uid,unit in manifest.items():
        path = root/'mr'/unit['source_path']
        raw = path.read_bytes()
        for index,match in enumerate(NOTE.finditer(raw.decode('utf-8').replace('\r\n','\n')),1):
            note = match[1]
            yield {'unit_id':uid,'note_index':index,
                   'translation_path':path.relative_to(root).as_posix(),
                   'translation_sha256':sha(raw),
                   'source_note_sha256':sha(note.encode('utf-8')),
                   'projected_note_sha256':sha(project_note(note).encode('utf-8'))},note

def preserve_reader_notes(root, manifest, reader):
    inventory,missing = [],[]
    active = active_text(reader)
    normalized = normalize(active)
    for row,note in source_notes(root,manifest):
        projected = project_note(note)
        replacements = 0
        if normalize(projected) not in normalized:
            for variant in dict.fromkeys(legacy_variants(note)):
                pattern = r'\s+'.join(re.escape(s) for s in variant.split())
                # Search active text, never comments, before replacing a known
                # historical payload. The payload may wrap across TeX lines.
                if re.search(pattern,active):
                    reader,count = re.subn(pattern,lambda _:projected,reader)
                    assert count
                    replacements += count
                    active = active_text(reader)
                    normalized = normalize(active)
                    break
        present = normalize(projected) in normalized
        row['status'] = 'already_in_reader' if present else 'appended_to_notes'
        row['legacy_payload_replacements'] = replacements
        inventory.append(row)
        if not present:
            missing.append(r'\begin{quote}\small\textbf{'+row['unit_id']+' — स्रोतनोंद.} '
                           + projected + r'\end{quote}')
    if missing:
        assert reader.count(HEADING) == 1
        assert reader.count(TOC_ENTRY) == 1
        assert reader.index(HEADING) < reader.index(TOC_ENTRY)
        addition = (r'\section*{भाषांतरित स्रोत-एककांतील दुरुस्ती-नोंदी}'+'\n'
                    'खालील नोंदी भाषांतरित स्रोत-एककांतील स्पष्ट दुरुस्त्या आणि निवडी सांगतात. '
                    'विभागाजवळ आधीच दिसणाऱ्या नोंदी येथे पुन्हा दिलेल्या नाहीत.\n'
                    + '\n'.join(missing)+'\n')
        # Keep the contents entry beside the chapter opening. Inserting pages
        # before the old entry would move its page number and link destination.
        reader = reader.replace(TOC_ENTRY, '', 1)
        # Insert inside the editorial-note chapter, before its existing prose.
        reader = reader.replace(HEADING,HEADING+'\n'
                                +r'\markboth{स्रोतावरील संपादकीय नोंदी}{स्रोतावरील संपादकीय नोंदी}'
                                +'\n'+TOC_ENTRY+'\n'+addition,1)
    normalized = normalize(active_text(reader))
    for row,note in source_notes(root,manifest):
        assert normalize(project_note(note)) in normalized,row
    return reader,{'schema':'openlogic-mr-reader-note-coverage/1',
                   'notes':inventory,'source_note_count':len(inventory),
                   'appended_note_count':len(missing),
                   'legacy_payload_replacements':sum(r['legacy_payload_replacements'] for r in inventory)}

def verify_reader_notes(root, manifest, reader, receipt):
    """Replay coverage from current raw sources instead of trusting a count."""
    rows = list(source_notes(root,manifest))
    assert receipt['schema'] == 'openlogic-mr-reader-note-coverage/1'
    assert receipt['reader_sha256'] == sha(reader.encode('utf-8'))
    assert len(rows) == len(receipt['notes']) == receipt['source_note_count']
    active = normalize(active_text(reader))
    for (expected,note),stored in zip(rows,receipt['notes']):
        for key,value in expected.items():
            assert stored[key] == value,(expected['unit_id'],key)
        assert normalize(project_note(note)) in active,expected
    assert receipt['appended_note_count'] == sum(r['status']=='appended_to_notes' for r in receipt['notes'])
    if receipt['appended_note_count']:
        # Validate the ordering that determines the chapter's PDF navigation.
        assert reader.count(HEADING) == reader.count(TOC_ENTRY) == 1
        notes_heading = r'\section*{भाषांतरित स्रोत-एककांतील दुरुस्ती-नोंदी}'
        assert reader.index(HEADING) < reader.index(TOC_ENTRY) < reader.index(notes_heading)
    return len(rows)
