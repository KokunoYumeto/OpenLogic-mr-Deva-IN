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
        if m.group(1)=='intertext':
            body=t[start+m.end():j-1]
            inner=sorted(re.sub(r'\s+','',s) for s in re.findall(r'(?<!\\)\$(.*?)(?<!\\)\$',body,re.S))
            out+=t[start:a]+r'\intertext{TEXT MATH '+repr(inner)+'}'
        else:out+=t[start:a]+r'\text{TEXT}'
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
