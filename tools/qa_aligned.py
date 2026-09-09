"""Source/translation structural comparison; semantic review remains separate."""
import re,collections,unicodedata
def blocks(t):return re.split(r'\n\s*\n',t.strip())
def mask_text(t):
    out='';start=0
    while True:
        m=re.search(r'\\(text|intertext|emph)\{',t[start:])
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
def inline_math_delimiters(t):
    return collections.Counter(re.findall(r'\\[()]',t))
def macros(t):return collections.Counter(re.findall(r'(?<!\\)\\[A-Za-z@]+\*?',t))
def tokens(t):return collections.Counter(re.findall(r'!!\^?a?\{[^{}]+\}s?',t))
def identifiers(t):
    commands=r'(?:ol)?(?:label|ref|cref|Cref|eqref|pageref)|cite[A-Za-z]*|url|href|input|include|includegraphics|IfFileExists|olimport|oliflabeldef'
    keys=re.findall(r'\\('+commands+r')(\*?(?:\[[^\]]*\])*)\{([^{}]*)\}',t)
    keys+=re.findall(r'(\\olfileid)(\{[^{}]*\}\{[^{}]*\})(\{[^{}]*\})',t)
    # Line-ending and indentation changes inside a command option do not alter
    # the identifier, citation, or reference being preserved.
    return collections.Counter(
        tuple(re.sub(r'\s+', ' ', part).strip() for part in key) for key in keys
    )
def check(a,b):
    delimiters=inline_math_delimiters(b)
    return {'formula_multiset_parity':maths(a)==maths(b),'inline_math_delimiter_parity':inline_math_delimiters(a)==delimiters and delimiters[r'\(']==delimiters[r'\)'],'macro_multiset_parity':macros(a)==macros(b),'token_identity_parity':tokens(a)==tokens(b),'identifier_and_ref_option_parity':identifiers(a)==identifiers(b),'no_replacement_character':'\ufffd' not in b,'no_placeholder':not bool(re.search(r'\b(TODO|TBD|PLACEHOLDER)\b',b)),'nfc':unicodedata.normalize('NFC',b)==b}


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
    'OLP-0039': [
        ('या यादीतील\n$n$ व्या चिन्हमालेतील $m$ वा अंक $s_n(m)$ असू द्या.',
         'या यादीतील\n$m$ व्या चिन्हमालेतील $n$ वा अंक $s_n(m)$ असू द्या.'),
        ('प्रत्येक $1$ चा $0$, तर\nप्रत्येक $0$ चा~$1$ करायचा.',
         'प्रत्येक $1$ चा $0$, तर\nप्रत्येक $1$ चा~$0$ करायचा.'),
    ],
    'OLP-0040': [
        ('चिन्हमाला~$s$ असू द्या', 'चिन्हमाला~$s_{k}$ असू द्या'),
        ('$s(n) = 1$', '$s_{k}(n) = 1$'),
        ('$s(n) = 0$', '$s_k(n) = 0$'),
    ],
    'OLP-0043': [
        ('म्हणजे $s - r$ हा', 'म्हणजे $r - s$ हा'),
    ],
    'OLP-0045': [
        ('\\Setabs{p \\times q}{0 \\leq p \\in \\alpha \\land 0 \\leq q \\in \\beta} \\cup 0_\\Real &',
         '\\Setabs{p \\times q}{0 \\leq p \\in \\alpha \\land 0 \\leq q \\in \\beta} \\cup 0^\\mathbb{R} &'),
    ],
    'OLP-0048': [
        ('\\equivrep{f}{}\\neq 0_\\Real',
         '\\equivrep{f}{}\\neq 0_\\Rat'),
    ],
    'OLP-0054': [
        ('\\cardeq{B}{C}',
         '\\cardeq{\\cardeq{A}{B}}{C}'),
    ],
    'OLP-0058': [
        ('$\\lnot !A \\lor !B$',
         '$\\lnot !A \\lor !B)$'),
    ],
    'OLP-0060': [
        ('$!A \\ident\n(!A_j \\land !A_k)$',
         '$!A \\equiv\n(!A_j \\land !A_k)$'),
    ],
    'OLP-0090': [
        ('$\\lexists[x][\\lnot !A(x)]$ किंवा निष्कर्ष',
         '$\\lexists[x][!A(x)]$ or conclusion'),
    ],
    'OLP-0104': [
        ('$1$ आणि~$4$',
         '$1$ आणि~$3$'),
    ],
    'OLP-0105': [
        ('$\\{!D_1, \\dots, !D_m\\} \\subseteq \\Gamma$',
         '$!D_1$, \\dots, $!D_m \\subseteq \\Gamma$'),
    ],
    'OLP-0106': [
        ('$\\Gamma_1\n  =\\{!C_1, \\dots, !C_m\\} \\subseteq \\Gamma$',
         '$\\Gamma_1\n  =\\{!C_1, \\dots, !C_n\\} \\subseteq \\Gamma$'),
        ('\\sFmla{\\True}{\\lnot !A} ला\n  \\TRule{\\True}{\\lnot} लावून मिळणारा',
         '\\sFmla{\\False}{!A} ला\n  \\TRule{\\True}{\\lnot} लावून मिळणारा'),
        ('$n+2$', '$n+1$'),
    ],
    'OLP-0107': [
        ('\\sFmla{\\True}{\\formula{A}},just={\\TRule{\\True}{\\land}[2]}',
         '\\sFmla{\\True{\\formula{A}}},just={\\TRule{\\True}{\\land}[2]}'),
        ('\\sFmla{\\True}{\\formula{B}},just={\\TRule{\\True}{\\land}[2]}',
         '\\sFmla{\\True{\\formula{B}}},just={\\TRule{\\True}{\\land}[2]}'),
        ('\\sFmla{\\False}{\\formula{A}},just={\\TRule{\\False}{\\lor}[1]}',
         '\\sFmla{\\False{\\formula{A}}},just={\\TRule{\\False}{\\lor}[1]}'),
        ('\\sFmla{\\False}{\\formula{B}},just={\\TRule{\\False}{\\lor}[1]}',
         '\\sFmla{\\False{\\formula{B}}},just={\\TRule{\\False}{\\lor}[1]}'),
    ],
    'OLP-0109': [
        ('\\sFmla{\\True}{\\lforall[x][!A(x)]} \\in \\Gamma',
         '\\sFmla{\\True}{\\lforall[x][!B(x)]} \\in \\Gamma'),
        ('\\sFmla{\\False}{\\lforall[x][!A(x)]} \\in \\Gamma',
         '\\sFmla{\\False}{\\lforall[x][!B(x)]} \\in \\Gamma'),
        ('\\Sat/{M}{\\lforall[x][!A(x)]}',
         '\\Sat/{M}{\\lforall[x][!B(x)]}'),
        ('\\Sat/{M}{!A(x)}[s]',
         '\\Sat/{M}{!B(x)}[s]'),
    ],
    'OLP-0110': [
        ('$\\sFmla{\\True}{!A(s_1)}$ या रूपातील दुसरे आधारविधान',
         '$\\sFmla{\\True}{!A(s_2)}$ या रूपातील दुसरे आधारविधान'),
        ('$\\eq[s_1][s_2]$ (म्हणजे ओळ~$2$)',
         '$\\eq[t_1][t_2]$ (म्हणजे ओळ~$2$)'),
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
