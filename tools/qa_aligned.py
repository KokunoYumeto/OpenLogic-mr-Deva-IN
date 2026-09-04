"""Source/translation structural comparison; semantic review remains separate."""
import re,collections,unicodedata
def blocks(t):return re.split(r'\n\s*\n',t.strip())
def mask_text(t):
    out='';start=0
    while True:
        m=re.search(r'\\(text|intertext)\{',t[start:])
        if not m:return out+t[start:]
        a=start+m.start();j=start+m.end();depth=1
        while depth and j<len(t):
            if t[j]=='{' and t[j-1]!='\\':depth+=1
            elif t[j]=='}' and t[j-1]!='\\':depth-=1
            j+=1
        assert depth==0
        body=t[start+m.end():j-1]
        inner=sorted(re.sub(r'\s+','',s) for s in re.findall(r'(?<!\\)\$(.*?)(?<!\\)\$',body,re.S))
        out+=t[start:a]+'\\'+m.group(1)+'{TEXT MATH '+repr(inner)+'}'
        start=j
def maths(t):
    parts=re.findall(r'(?<!\\)\$(.*?)(?<!\\)\$|\\\[(.*?)\\\]|\\begin\{(?:align\*|multline\*)\}(.*?)\\end\{(?:align\*|multline\*)\}',t,re.S)
    return collections.Counter(re.sub(r'\s+','',mask_text(''.join(p))) for p in parts)
def macros(t):return collections.Counter(re.findall(r'\\[A-Za-z@]+\*?',t))
def tokens(t):return collections.Counter(re.findall(r'!!\^?a?\{[^{}]+\}s?',t))
def identifiers(t):
    commands=r'(?:ol)?(?:label|ref|cref|Cref|eqref|pageref)|cite[A-Za-z]*|url|href|input|include|includegraphics|IfFileExists|olimport|oliflabeldef'
    keys=re.findall(r'\\('+commands+r')(\*?(?:\[[^\]]*\])*)\{([^{}]*)\}',t)
    keys+=re.findall(r'(\\olfileid)(\{[^{}]*\}\{[^{}]*\})(\{[^{}]*\})',t)
    return collections.Counter(keys)
def check(a,b):
    return {'formula_multiset_parity':maths(a)==maths(b),'macro_multiset_parity':macros(a)==macros(b),'token_identity_parity':tokens(a)==tokens(b),'identifier_and_ref_option_parity':identifiers(a)==identifiers(b),'no_replacement_character':'\ufffd' not in b,'no_placeholder':not bool(re.search(r'\b(TODO|TBD|PLACEHOLDER)\b',b)),'nfc':unicodedata.normalize('NFC',b)==b}


_DOCUMENTED_PROJECTIONS = {
    'OLP-0029': [
        ('0 & 1 & -1 & 2 & -2 & 3 & -3 & \\dots',
         '0 & 1 & -1 & 2 & -2 & 3 & \\dots'),
    ],
    'OLP-0032': [
        ('$\\tuple{3,m}$ जोड्या', '$\\tuple{2,m}$ जोड्या'),
    ],
    'OLP-0034': [
        ('अनुक्रम~$s$ असू द्या', 'अनुक्रम~$s_{k}$ असू द्या'),
        ('$s(n) = 1$', '$s_{k}(n) = 1$'),
        ('$s(n) = 0$', '$s_k(n) = 0$'),
        ('h(n) = \\underbrace{000\\dots0}_{\\text{$n$ वेळा $0$}}111\\dots',
         'h(n) = \\underbrace{000\\dots0}_{\\text{$n$ वेळा $0$}}'),
    ],
    'OLP-0035': [
        ('$f(x) = y$ अशी पूर्वप्रतिमा', '$g(x) = y$ अशी पूर्वप्रतिमा'),
    ],
    'OLP-0036': [
        ('प्रत्येक $x \\in A$ साठी $x \\in g(x)$',
         'प्रत्येक $x \\in \\overline{A}$ साठी $x \\in g(x)$'),
    ],
}


def project_documented_source_corrections(unit_id, text):
    projected = text
    applied = []
    for corrected, frozen in _DOCUMENTED_PROJECTIONS.get(unit_id, []):
        if corrected in projected:
            projected = projected.replace(corrected, frozen)
            applied.append((corrected, frozen))
    return projected, applied


def check_with_documented_source_corrections(unit_id, source, target):
    projected, applied = project_documented_source_corrections(unit_id, target)
    result = check(source, projected)
    if applied:
        result = {
            'formula_multiset_parity_after_documented_source_correction_projection': result.pop('formula_multiset_parity'),
            'macro_multiset_parity_after_documented_source_correction_projection': result.pop('macro_multiset_parity'),
            **result,
            'documented_source_correction_projection_applied': True,
        }
    return result
