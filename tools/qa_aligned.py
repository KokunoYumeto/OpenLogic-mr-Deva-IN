"""Source/translation structural comparison; semantic review remains separate."""
import re,collections,unicodedata
def blocks(t):return re.split(r'\n\s*\n',t.strip())
def mask_text(t):
    out='';start=0
    while True:
        m=re.search(r'\\(text|textrm|intertext|emph|mbox)\{',t[start:])
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
    # A displayed formula may contain inline dollars inside \text{...}. Exclude
    # its span before finding inline formulae, then pair outer dollars only at
    # brace depth zero so nested text-math dollars do not close the formula.
    # A tabular line break such as \\[2ex] must not be mistaken for \[...\].
    display=re.compile(r'(?<!\\)\\\[(.*?)(?<!\\)\\\]|\\begin\{(?:align\*|multline\*|eqnarray\*)\}(.*?)\\end\{(?:align\*|multline\*|eqnarray\*)\}',re.S)
    parts=[]
    masked=list(t)
    for match in display.finditer(t):
        parts.append(match.group(1) if match.group(1) is not None else match.group(2))
        masked[match.start():match.end()]=[' ']*(match.end()-match.start())
    remaining=''.join(masked)
    i=0
    while i<len(remaining):
        if remaining[i]!='$' or (i>0 and remaining[i-1]=='\\'):
            i+=1
            continue
        start=i+1
        depth=0
        i=start
        while i<len(remaining):
            char=remaining[i]
            escaped=i>0 and remaining[i-1]=='\\'
            if char=='{' and not escaped:depth+=1
            elif char=='}' and not escaped:depth-=1
            elif char=='$' and not escaped and depth==0:
                parts.append(remaining[start:i])
                i+=1
                break
            i+=1
        else:
            raise AssertionError('unclosed inline math')
    return collections.Counter(re.sub(r'\s+','',mask_text(part)) for part in parts)
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
    'OLP-0119': [
        ('$\\Proves (!A \\lif !B) \\lif ((!B \\lif !C)\n  \\lif (!A \\lif !C))$;',
         '$\\Proves (!A \\lif !B) \\lif ((!B \\lif !C)\n  \\lif (!A \\lif !C)$;'),
    ],
    'OLP-0120': [
        ('& \\Proves ((!A \\land !C) \\lif \\lforall[x][!D(x)]) \\lif (!A \\lif (!C \\lif \\lforall[x][!D(x)])),\\\\',
         '& \\Proves ((!A \\land !C) \\lif \\lforall[x][!D(x)]) \\lif (!A \\lif (!C \\lif \\lforall[x][!D(x)]),\\\\'),
        ('म्हणजे $\\Gamma \\Proves !A \\lif !B$.', 'म्हणजे $\\Gamma \\Proves !B$.'),
    ],
    'OLP-0122': [
        ('\\olref[prp]{ax:land1} आणि \\olref[prp]{ax:land2}',
         '\\olref[prp]{ax:land1} आणि \\olref[prp]{ax:land1}'),
        ('\\olref[prp]{ax:lnot2} पासून $\\Proves',
         '\\olref[prp]{ax:lnot1} पासून $\\Proves'),
    ],
    'OLP-0124': [
        ('$!C \\lif \\lforall[x][!B(x)]$',
         '$!C \\lif \\lforall[x][B(x)]$'),
        ('\\Entails !B(c)$ असल्यामुळे $\\Sat{M\'}{!B(c)}$. $!B(c)$ हे',
         '\\Entails !B(c)$ असल्यामुळे $\\Sat{M\'}{B(c)}$. $!B(c)$ हे'),
    ],
    'OLP-0130': [
        ('$\\lforall[x_n][\\lnot !A_n(x_n)]$ ची व्याख्या',
         '$\\lforall[x_n][\\lnot !A_n]$ ची व्याख्या'),
    ],
    'OLP-0132': [
        ('$\\lforall[x][!B(x)] \\in \\Gamma^*$.',
         '$\\lforall[x][!A(x)] \\in \\Gamma^*$.'),
    ],
    'OLP-0133': [
        ('\\eq[\\Atom{f}{t_1,\\dots,t_{i-1},t,t_{i+1},\\dots,t_n}][\\Atom{f}{t_1,\\dots,t_{i-1},t\',t_{i+1},\\dots,t_n}]',
         '\\eq[\\Atom{f}{t_1,\\dots,t_{i-1},t,t_{i+1},,\\dots,t_n}][\\Atom{f}{t_1,\\dots,t_{i-1},t\',t_{i+1},\\dots,t_n}]'),
        ('$\\Sat/{M}{\\Atom{R}{t\'}}$', '$\\Sat/{M}{\\Atom{R}{t}}$'),
    ],
    'OLP-0140': [
        ('$\\lforall[x][(!A(x) \\lif !B(x))],\n\\lexists[x][!A(x)] \\Entails \\lexists[x][!B(x)]$',
         '$\\lforall[x][(!A(x) \\lif !B(x)),\n\\lexists[x][!A(x)] \\Entails \\lexists[x][!B(x)]]$'),
        ('निगमनातील !!{derivation} मध्ये $\\lforall[x][(!A(x) \\lif !B(x))]$ आणि\n$\\lexists[x][!A(x)]$ ही आधारविधाने आणि $\\lexists[x][!B(x)]$ हा',
         'निगमनातील !!{derivation} मध्ये $\\lforall[x][(!A(x) \\lif !B(x))$ आणि\n$\\lexists[x][!A(x)]$ ही आधारविधाने आणि $\\lexists[x][!B(x)]]$ हा'),
        ('केवळ तेव्हाच $\\lforall[x][(!A(x) \\lif !B(x))]$ आणि\n$\\lexists[x][!A(x)]$ ही दोन्ही मिळून\n$\\lexists[x][!B(x)]$ तार्किकरीत्या',
         'केवळ तेव्हाच $\\lforall[x][(!A(x) \\lif !B(x))$ आणि\n$\\lexists[x][!A(x)]$ ही दोन्ही मिळून\n$\\lexists[x][!B(x)]]$ तार्किकरीत्या'),
    ],
    'OLP-0143': [
        ('असतील, !!{predicate}s ना एकाहून अधिक स्थाने',
         'असतील, !!{constant}s ना एकाहून अधिक स्थाने'),
        ('$0$, $1$ किंवा~$2$', '$1$, $2$ किंवा~$3$'),
    ],
    'OLP-0146': [
        ('$\\lforall[\\Obj v_0][\\Atom{\\Obj P}{\\Obj v_0}]$',
         '$\\lforall[\\Obj v_0][\\Atom{\\Obj P}]{\\Obj v_0}$'),
    ],
    'OLP-0152': [
        ('$\\lnot !A \\lor !B$', '$\\lnot !A \\lor !B)$'),
    ],
    'OLP-0156': [
        ('$m_1,\\dotsc,m_k < i$', '$m_0,\\dotsc,m_k < i$'),
        ('$t_i \\ident f(t_{m_1},\\dotsc,t_{m_k})$',
         '$t_i \\ident f(t_{m_0},\\dotsc,t_{m_k})$'),
        ('$!A_n \\in \\Frm[L]$. त्याऐवजी',
         '$!A_n \\in \\Frm[L_0]$. त्याऐवजी'),
        ('$!A \\ident (!A_j \\land !A_k)$ असे समजा.',
         '$!A \\equiv (!A_j \\land !A_k)$ असे समजा.'),
        ('$!A_j$ आणि~$!A_k$ ही\n$\\Frm[L]$ मध्ये',
         '$!A_j$ आणि~$!A_k$ ही\n$\\Frm[L_0]$ मध्ये'),
    ],
    'OLP-0162': [
        ('\\Value{\\times(\\Obj{two}, +(\\Obj{three},\\Obj{zero}))}{M} \\\\',
         '\\Value{\\times(\\Obj{two}, +(\\Obj{three},\\Obj{zero}))}{M} =\\\\'),
    ],
    'OLP-0163': [
        ('\\iftag{prvEx}{किमान एका $m \\in \\Domain{M}$ साठी '
         '$\\Sat{M}{!B(m)}$}{प्रत्येक',
         '\\iftag{prvEx}{किमान एका $m \\in \\Domain{M}$ साठी}{प्रत्येक'),
        ('$\\tuple{1, 3} \\notin \\Assign{R}{M}$',
         '$\\tuple{1, 3} \\notin \\Assign{R}{M}[s]$'),
        ('$\\Sat/{M}{\\lforall[x][\\lnot(R(b,x) \\lor R(x,b))]}[s]$',
         '$\\Sat/{M}{\\lforall[x][\\lnot((R(b,x) \\lor R(x,b))]}[s]$'),
        ('$\\Sat{M}{\\lnot\\lforall[x][\\lnot(R(b,x) \\lor R(x,b))]}[s]$',
         '$\\Sat{M}{\\lnot\\lforall[x][\\lnot((R(b,x) \\lor R(x,b))]}[s]$'),
        ('\\Sat/{M}{\\lexists[x][(R(b,x) \\land R(x,b))]}[s].',
         '\\Sat/{M}{\\lexists[x][(R(b,x) \\land R(x,b))],}[s].'),
        ('$m = 2$, $3$ किंवा~$4$ साठी\n'
         '  $\\Sat/{M}{R(x,a)}[\\Subst{s}{m}{x}]$',
         '$m = 2$, $3$ किंवा~$4$ साठी\n'
         '  $\\Sat/{M}{R(a,x)}[\\Subst{s}{m}{x}]$'),
        ('रंजक प्रकरणे फक्त $m = 1$ आणि\n$m = 2$ ही आहेत.',
         'रंजक प्रकरणे फक्त $m = 1$ आणि\n$ = 2$ ही आहेत.'),
        ('प्रत्येक $m \\in \\Domain M$ साठी एकतर',
         'प्रत्येक $n \\in \\Domain M$ साठी एकतर'),
        ('आहे---पहिल्या मूल्यासाठी $n = 4$\nआणि दुसऱ्यासाठी $n = 1$---ज्यामुळे',
         'आहे, म्हणजेच $n = 4$, ज्यामुळे'),
    ],
    'OLP-0164': [
        ('\\langle \\Value{t_1}{M}[s_2], \\ldots, '
         '\\Value{t_k}{M}[s_2] \\rangle\n    \\in \\Assign{R}{M}',
         '\\langle \\Value{t_i}{M}[s_2], \\ldots, '
         '\\Value{t_k}{M}[s_2] \\rangle\n    \\in \\Assign{R}{M}'),
        ('म्हणून मनमाना $m \\in \\Domain{M}$ घेऊन\n'
         '      $s_1\' = \\Subst{s_1}{m}{x}$ आणि $s_2\' =\n'
         '      \\Subst{s_2}{m}{x}$ विचारात घ्या.',
         'म्हणून मनमाना $m \\in \\Domain{M}$ घेऊन\n'
         '      $s_1\' = \\Subst{s}{m}{x}$ आणि $s_2\' =\n'
         '      \\Subst{s}{m}{x}$ विचारात घ्या.'),
        ('$\\Gamma$ हा !!{sentence}s चा संच असेल',
         '$\\Gamma$ हा !!{sentence}s चा संच~$\\Gamma$ असेल'),
    ],
    'OLP-0165': [
        ('\\Value{\\Subst{t}{t\'}{x}}{M}[s] \\\\',
         '\\Value{\\Subst{t}{t\'}{x}}{M}[s]  = \\\\'),
    ],
    'OLP-0171': [
        ("$\\lexists[\\Obj\n  v_3][\\eq[(\\Obj v_1 + {\\Obj v_3}')][\\Obj v_2]]$",
         "$\\lexists[\\Obj\n  v_3][\\eq[(\\Obj v_1 + {\\Obj v_3}')][v_2]]$"),
    ],
    'OLP-0178': [
        ('प्रकार~$\\tau$ च्या कोणत्याही~$x$ साठी',
         'प्रकार~$\\sigma$ च्या कोणत्याही~$x$ साठी'),
    ],
    'OLP-0187': [
        ("\\Value{t}{M'}[h \\circ s] & = \\Assign{f}{M'}(",
         "\\Value{t}{M'}[h \\circ s] & = \\Assign{f}{M}("),
    ],
    'OLP-0189': [
        ('$x_1$, \\dots,~$x_k$',
         '$x_1$, \\dots,~$x_n$'),
    ],
    'OLP-0192': [
        ('$\\lexists[x][\\OPrf[\\Th{PA}](x, \\gn{\\lfalse})]$',
         '$\\lexists[x][\\OPrf[\\Th{PA}](\\gn{\\lfalse})]$'),
    ],
    'OLP-0194': [
        ('$x = \\Assign{c}{M^c}$', '$x = \\Assign{c}{M}$'),
    ],
    'OLP-0195': [
        ('$y = a$', '$y = b$'),
        ('(b \\nsplus a)^\\nssucc', '(b \\nsplus y)^\\nssucc'),
    ],
    'OLP-0196': [
        ('$x \\nsplus y = z \\nsplus z$', '$x \\oplus y = z \\oplus z$'),
        ('$x \\nsplus y = (z \\nsplus z)^\\nssucc$',
         '$x \\oplus y = (z \\oplus z)^\\nssucc$'),
    ],
    'OLP-0197': [
        ('\\Setabs{\\tuple{x,a}}{x \\in \\Domain{K}}',
         '\\Setabs{\\tuple{x,a}}{n \\in \\Domain{K}}'),
        ('$g(n) = n-1$', '$g(n) = n+1$'),
    ],
    'OLP-0200': [
        ('\\lforall[x][!C] \\Entails \\lnot !H',
         '\\lforall[x][!C] \\Entails \\lnot \\delta'),
    ],
    'OLP-0201': [
        ("\\Assign{P}{M} = h(\\Assign{P}{M'_1})",
         "\\Assign{P}{M} = h(\\Assign{P}{M'_2})"),
    ],
    'OLP-0202': [
        ("!D(P) \\land\n!D(P') \\Entails \\Atom{P}{c_1, \\dots, c_n} \\to \\Atom{P'}{c_1, \\dots, c_n}",
         "!D(P) \\land\n!D(P') \\Entails \\Atom{P}{c_1, \\dots, c_n} \\to P'c_1\\dots c_n"),
    ],
    'OLP-0206': [
        ('\\Struct{A}', '\\Struct{M}'),
        ('\\Domain{N}^*', '\\Domain{N}*'),
    ],
    'OLP-0207': [
        ('$\\Struct{M}_n$ चा उपअनुक्रम',
         '$\\Struct{M}$ चा उपअनुक्रम'),
        ('आहे, $\\Struct{M}_n \\models_L !E$,\n'
         '$\\Struct{N}_n \\not\\models_L !E$',
         'आहे, $\\Struct{M}_n \\models !E$,\n'
         '$\\Struct{N}_n \\not\\models !E$'),
        ('$\\Struct{A}^*$ मध्ये अशा उप',
         '$\\Struct{M^*}$ मध्ये अशा उप'),
        ('\\Struct{A}', '\\Struct{M}'),
    ],
    'OLP-0212': [
        ('$h(x_0, \\dots, x_{n-1}) = f(y_0, \\dots, y_{k-1})$',
         '$h(x_0, \\dots, x_{k-1}) = f(y_0, \\dots, y_{k-1})$'),
    ],
    'OLP-0218': [
        ('$m_R(\\vec{x}, y+1) = y+1$',
         '$m_R(\\vec{z}, y+1) = y+1$'),
    ],
    'OLP-0221': [
        ('$g_f(s, k) = f((s)_0) \\concat\n  \\dots \\concat f((s)_{k-1})$',
         '$g_f(s, k) = f((s)_0) \\concat\n  \\dots \\concat f((s)_k)$'),
        ('g(s, 0) & = \\emptyseq\\\\',
         'g(s, 0) & = f((s)_0)\\\\'),
        ('g(s, k+1) & = g(s, k) \\concat f((s)_k)',
         'g(s, k+1) & = g(s, k) \\concat f((s)_{k+1})'),
    ],
    'OLP-0232': [
        ('कार्यक्रम\n$s^m_n(e, a_0, \\dots, a_{m-1})$ परत',
         'कार्यक्रम\n$s^m_n(x, a_0, \\dots, a_{m-1})$ परत'),
        ('जर $e$ ला ट्यूरिंग', 'जर $x$ ला ट्यूरिंग'),
    ],
    'OLP-0236': [
        ('$S \\notin S$ असेल', '$X \\notin S$ असेल'),
    ],
    'OLP-0239': [
        ('$\\cfind{e}((z)_0) \\fdefined =\ny$',
         '$\\cfind{e}(x) \\fdefined =\ny$'),
    ],
    'OLP-0242': [
        ('$T(d, x, h(x))$', '$T(e, x, h(x))$'),
        ('$\\cfind{d}$ परिभाषित असते', '$\\cfind{e}$ परिभाषित असते'),
        ('$\\cfind{d}$ आणि $\\cfind{e}$', '$\\cfind{e}$ आणि $\\cfind{f}$'),
        ('$\\cfind{d}$ थांबले', '$\\cfind{e}$ थांबले'),
    ],
    'OLP-0243': [
        ('$K_0 = \\Setabs{\\tuple{e,x}}{x \\in W_e}$',
         '$K_0 = \\Setabs{\\tuple{x,e}}{x \\in W_e}$'),
    ],
    'OLP-0244': [
        ('$f\\colon \\Nat \\to \\Nat$ हे $A$ चे~$B$ कडे',
         '$f\\colon A \\to B$ हे'),
    ],
    'OLP-0255': [
        ('दिसते त्याप्रमाणे यंत्र $q_0$ अवस्थेत\nसुरू होते',
         'दिसते त्याप्रमाणे यंत्र पहिल्या अवस्थेत\nसुरू होते'),
    ],
    'OLP-0261': [
        ('\\text{$q \\in Q$ आणि $\\delta(q,\\sigma)$ परिभाषित असेल तर}',
         '\\text{if $q \\in Q$}'),
    ],
    'OLP-0270': [
        ("!A(x', y))) \\land {}", "!A(x, y))) \\land {}"),
    ],
    'OLP-0271': [
        ('$!T(M, w) \\Entails !E(M, w)$,',
         '$T(M, w) \\Entails !E(M, w)$,'),
        ('तेव्हाच, जेव्हा $M$ हे\nआदान~$w$ वर $n$ पायऱ्या',
         'तेव्हाच, जेव्हा $T$ हे\nआदान~$w$ वर $n$ पायऱ्या'),
        ('$\\tuple{q,\\sigma} \\in X$\nअसल्याने',
         '$\\tuple{q\',\\sigma\'} \\in X$\nअसल्याने'),
        ('$\\Obj Q_{q}(\\num{m}, \\num{n}) \\land \\Obj S_{\\sigma}(\\num{m},',
         '$\\Obj Q_{q\'}(\\num{m}, \\num{n}) \\land S_{\\sigma\'}(\\num{m},'),
        ('$n \\ge 0$ असे समजा', '$n > 0$ असे समजा'),
        ("!A(x', y))) \\land {}", "!A(x, y))) \\land {}"),
        ("!A(\\num{l}', \\num{n}))", "!A(\\num{l}, \\num{n}))"),
        ('\\Obj S_{\\sigma_0^{+}}', '\\Obj S_{\\sigma_0}'),
        ('\\Obj S_{\\sigma_k^{+}}', '\\Obj S_{\\sigma_k}'),
    ],
    'OLP-0272': [
        ('!!a{sentence} वाक्य~$!B$ दिले',
         '!!a{sentence} वाक्य~$B$ दिले'),
    ],
    'OLP-0273': [
        ('    $\\delta(q_0,\\TMblank) = \\tuple{q_0,\\TMblank,\\TMstay}$',
         '    $\\delta(q_0,\\TMblank) = \\tuple{q,\\TMblank,\\TMstay}$'),
        ("\\Assign{\\prime}{M''}(1) = 1",
         "\\Assign{\\prime}{M'}(1) = 1"),
        ("!A(x', y) \\land !B(y'))) \\land {}",
         "!A(x, y))) \\land {}"),
        ('n = \\max(k+1,\\len{w}+1)',
         'n = \\max(k,\\len{w})'),
        ("$\\Sat{M'}{!T'(M,w) \\land !E(M,w)}$\n  याची पडताळणी",
         "$\\Sat{M'}{!T'(M,w) \\land E(M,w)}$\n  याची पडताळणी"),
        ("$\\Sat{M'}{!T'(M,w) \\land !E(M,w)}$\n  हे सिद्ध करून",
         "$\\Sat{M'}{!T(M,w) \\land E(M,w)}$\n  हे सिद्ध करून"),
        ("हे~$!T'(M,w) \\land !E(M, w)$\n  चे प्रतिरूप आहे",
         "हे~$!T(M,w) \\land !E(M, w)$\n  चे प्रतिरूप आहे"),
    ],
    'OLP-0279': [
        ('$!A_n(\\num{n})$ च्या\nआधी',
         '$!A(\\num{n})$ च्या\nआधी'),
        ('$\\lnot !A_n(\\num{n}) \\in \\Gamma$ आहे का',
         '$\\lnot !A(\\num{n}) \\in \\Gamma$ आहे का'),
    ],
    'OLP-0286': [
        # OLINC-007: the frozen worked example has two surplus parentheses.
        (r'$\tuple{1, p_1, \Gn{\Sequent (!A \land !B) \lif !A}, 14}$',
         r'$\tuple{1, p_1, \Gn{\Sequent (!A \land !B) \lif !A)}, 14}$'),
        (r'\tuple{0, \Gn{!A \Sequent !A}}',
         r'\tuple{0, \Gn{!A \Sequent !A)}}'),
        # OLINC-008: normalize the two predicate names to their later uses.
        (r'\fn{EndSequent}(p) = (p)_{(p)_0+1}',
         r'\fn{EndSeq}(p) = (p)_{(p)_0+1}'),
        (r'\fn{InitialSeq}(s)', r'\fn{InitSeq}(s)'),
        # OLINC-011: identity uses closed terms; tagged LK has two more axioms.
        (r'\fn{ClTerm}(t) & \land', r'\fn{Term}(t) & \land'),
        ('  \\iftag{prvTrue}{या चिन्हांकित आवृत्तीत $s=\\tuple{0,\\tuple{\\Gn{\\ltrue}}}$\n'
         '  हीदेखील आरंभीची क्रमवर्ती आहे.}{}\n'
         '  \\iftag{prvFalse}{या चिन्हांकित आवृत्तीत $s=\\tuple{\\tuple{\\Gn{\\lfalse}},0}$\n'
         '  हीदेखील आरंभीची क्रमवर्ती आहे.}{}', ''),
        # OLINC-012: right existential introduction requires a closed term.
        (r'  & \qquad \fn{ClTerm}(t) \land {}\\' + '\n', ''),
        # OLINC-009: use the proposition's variable and close the predicate.
        (r'पहिली ओळ $p$ ची अंतिम क्रमवर्ती खरोखर',
         r'पहिली ओळ $d$ ची अंतिम क्रमवर्ती खरोखर'),
        (r'$\fn{Deriv}(p)$ तर आणि तरच',
         r'$\fn{Deriv}(d)$ तर आणि तरच'),
        (r'\fn{Correct}((\fn{SubtreeSeq}(p))_i)}',
         r'\fn{Correct}((\fn{SubtreeSeq}(p))_i}'),
        # OLINC-010: y, rather than derivation code x, codes the sentence.
        ('((\\fn{EndSequent}(x))_1)_0 =\ny$',
         '((\\fn{EndSequent}(x))_1)_0 =\nx$'),
    ],
    'OLP-0287': [
        # OLINC-013: the worked example must code the parenthesized conjunction.
        ('$d_0 = \\tuple{0,\n    \\Gn{(!A \\land !B)}, 1}$',
         '$d_0 = \\tuple{0,\n    \\Gn{!A \\land !B}, 1}$'),
        # OLINC-014: Sent applies to every Correct disjunct, as the prose says.
        (r'[(\fn{LastRule}(d) = 1 \land',
         r'(\fn{LastRule}(d) = 1 \land'),
        (r'\bexists{n<d}{\bexists{x<d}{(d = \tuple{0, x, n})}}].',
         r'\bexists{n<d}{\bexists{x<d}{(d = \tuple{0, x, n})}}.'),
        # OLINC-015: child codes occupy indices 1 through the child count.
        (r"\bexists{j<(d')_0}{d = (d')_{j+1}}",
         r"\bexists{j<(d')_0}{d = (d')_j}"),
        # OLINC-016: a zero-labelled assumption is open by definition.
        (r'(n=0 \lor \fn{DischargeLabel}((s)_i) \neq n))))',
         r'\fn{DischargeLabel}((s)_i) \neq n)))'),
    ],
    'OLP-0288': [
        # OLINC-018: axiom schemata range over formulas, not just sentences.
        (r'\fn{Frm}(b) \land \fn{Frm}(c)',
         r'\fn{Sent}(b) \land \fn{Sent}(c)'),
        # OLINC-019: the earlier QR rule permits formulas and j must be bound.
        ('!!{formula}~$!A$ असते', '!!{sentence}~$!A$ असते'),
        ('\\fn{QR}_1(d, i) \\defiff \\bexists{j<i}{\\bexists{b < (d)_i}{\\bexists{x <\n'
         '        (d)_i}{\\bexists{a < (d)_i}{\\bexists{c < (d)_j}{(}}}}}',
         '\\fn{QR}_1(d, i) \\defiff \\bexists{b < (d)_i}{\\bexists{x <\n'
         '        (d)_i}{\\bexists{a < (d)_i}{\\bexists{c < (d)_j}{(}}}}'),
        ('\\fn{Frm}(b)\n    \\land \\fn{Frm}(a)',
         '\\fn{Sent}(b)\n    \\land \\fn{Sent}(\\fn{Subst}(a,c,x))'),
        ('$c$ ची गोडेल\n  संख्या $j$ व्या ओळीवरील',
         '$a$ ची गोडेल\n  संख्या $j$ व्या ओळीवरील'),
        # OLINC-020: a derivation must contain a last line.
        ('\\fn{Deriv}(d) \\defiff \\len{d}>0 \\land\n  \\bforall',
         '\\fn{Deriv}(d) \\defiff \\bforall'),
        # OLINC-021/022: correct the recurrence arity and stated sentence scope.
        (r'\concat \fn{hCond}(s, y, n) \concat \Gn{)}',
         r'\concat \fn{Cond}(s, y, n) \concat \Gn{)}'),
        ('\\Prf[\\Gamma](x, y) & \\defiff \\fn{Sent}(y) \\land\n'
         '  \\bexists{s < \\fn{sequenceBound}(x,x)}{(}',
         '\\Prf[\\Gamma](x, y) & \\defiff \\bexists{s < \\fn{sequenceBound}(x,x)}{(}'),
    ],
    'OLP-0291': [
        # OLINC-024: use the already defined representing formula name.
        ('$!A_f(x_0, \\dots, x_k, y)$ असते की',
         '$!A(x_0, \\dots, x_k, y)$ असते की'),
        # OLINC-024: the output position is a numeral, not a bare number.
        ('$!A_f(\\num{n_0}, \\dots,\n'
         '\\num{n_k}, \\num{(s)_1})$ च्या !!a{derivation}',
         '$A_f(\\num{n_0}, \\dots,\n'
         '\\num{n_k}, (s)_1)$ च्या !!a{derivation}'),
    ],
    'OLP-0293': [
        # OLINC-027: the recurrence gives h the arguments (x-vector, y).
        ('$h(\\vec x,y)$', '$h(x,\\vec z)$'),
    ],
    'OLP-0294': [
        # Localized case label needs text mode for Devanagari shaping.
        ('\\text{अन्यथा}', 'otherwise'),
    ],
    'OLP-0295': [
        # OLINC-029: the exercise refers to both preceding propositions.
        ('\\olref[inc][req][cmp]{prop:rep1}',
         '\\olref[inc][req][cmp]{prop:rep2}'),
    ],
    'OLP-0296': [
        # OLINC-032: the existential witness for u is c, not c-prime.
        ("$c$ वर अस्तित्ववाचक", "$c'$ वर अस्तित्ववाचक"),
    ],
    'OLP-0300': [
        # OLINC-038: t_2 evaluates to m, not n.
        (r'$\Th{Q} \Proves \eq[t_2][\num m]$.' + '\n' + r'$n = m$',
         r'$\Th{Q} \Proves \eq[t_2][\num n]$.' + '\n' + r'$n = m$'),
        # OLINC-039: the Q_8 witness requires the successor numeral on the left.
        (r"$\Th{Q} \Proves \eq[{\num k}' + \num n][\num m]$",
         r"$\Th{Q} \Proves \eq[\num n + {\num k}'][\num m]$"),
        # OLINC-040: the argument obtains equality with zero and uses Q_2.
        (r"$\eq[z'][\Obj 0]$", r"$\eq/[z'][\Obj 0]$"),
        (r'$!Q_2$', r'$!Q_3$'),
        # OLINC-042/043: make the bounded and unbounded quantifier bodies explicit.
        (r'$\lnot \bexists{x<t}{!A(x)}$',
         r'$\lnot \bexists{x<t}!A(x)$'),
        (r'$\lexists[x][!A(x)]$ हे $\Struct{N}$',
         r'$\lexists{x}!A(x)$ हे $\Struct{N}$'),
    ],
    'OLP-0303': [
        # OLINC-045: retain the earlier formal notation for diagonal halting.
        (r'$K = \Setabs{x}{\cfind{x}(x) \fdefined}$',
         r'$K = \Setabs{x}{!A_x(x) \downarrow}$'),
        (r'$\cfind{x}(x) \fdefined$',
         r'$!A_x(x) \downarrow$'),
        # OLINC-046: f must code the arithmetic representative A_T, not T.
        (r'$\lexists[s][!A_T(\num x,\num x,s)]$',
         r'$\lexists[s][T(\num x,\num x,s)]$'),
        (r'$\lexists[s][!A_T(\num x,' + '\n' + r'  \num x, s)]$',
         r'$\lexists[s][T(\num x,' + '\n' + r'  \num x, s)]$'),
    ],
    'OLP-0305': [
        # OLINC-048: S is a metatheoretic relation on numbers, not on numerals.
        (r'S(n) & \lif & T \vdash !D_S(\num n)',
         r'S(\num n) & \lif & T \vdash !D_S(\num n)'),
        (r'\lnot S(n) & \lif & T \vdash \lnot !D_S(\num n)',
         r'\lnot S(\num n) & \lif & T \vdash \lnot !D_S(\num n)'),
    ],
    'OLP-0308': [
        # OLINC-049: effective axiomatizability, not bare axiomatization,
        # is the hypothesis needed by the cited decidability lemma.
        ('!!{axiomatizable} असेल, तर', '!!{axiomatized} असेल, तर'),
    ],
    'OLP-0309': [
        # OLINC-050: S is a metatheoretic relation on natural numbers.
        (r'S(n) & \lif & \Th{Q} \Proves !D_S(\num n)',
         r'S(\num n) & \lif & \Th{Q} \Proves !D_S(\num n)'),
        (r'\lnot S(n) & \lif & \Th{Q} \Proves \lnot !D_S(\num n)',
         r'\lnot S(\num n) & \lif & \Th{Q} \Proves \lnot !D_S(\num n)'),
        # OLINC-051: code D_S(u), the formula with free variable u.
        (r'$R(\#(!D_S(u)),y)$', r'$R(\#(!D_S(\num u)),y)$'),
    ],
    'OLP-0318': [
        # OLINC-055: OProv is an arithmetic formula, so its body uses the
        # representing formula OPrf rather than the metatheoretic relation Prf.
        (r'$\lexists[x][\OPrf[\Th{PA}](x,y)]$',
         r'$\lexists[x][\Prf[\Th{PA}](x,y)]$'),
    ],
    'OLP-0319': [
        # OLINC-059: use the same falsity code in OCon's definition and G2-9.
        (r'$\lnot' + '\n' + r'\OProv[\Th{PA}](\gn{\lfalse})$',
         r'$\lnot' + '\n' + r'\OProv[\Th{PA}](\gn{\eq[0][1]})$'),
        # OLINC-056: the surrounding argument uses the defined OProv formula.
        (r'$\lnot' + '\n' + r'\OProv[\Th{PA}](\gn{!G_\Th{PA}})$',
         r'$\lnot' + '\n' + r'\Prov[\Th{PA}](\gn{!G_\Th{PA}})$'),
        # OLINC-057: code the same marked Gödel sentence as in G2-5/G2-6.
        (r'$!A' + '\n' + r'\ident \OProv(\gn{!G})$',
         r'$!A' + '\n' + r'\ident \OProv(\gn{G})$'),
        # OLINC-058: keep the theorem's theory notation in its conclusion.
        (r'$\OCon[\Th{T}]$', r'$\OCon[T]$'),
    ],
    'OLP-0328': [
        # OLINC-060: the earlier relation chapter reserves R^* for the
        # reflexive transitive closure; this section defines positive
        # transitive closure, so its Marathi notation uses R^+.
        (r'R^+', r'R^*'),
    ],
    'OLP-0332': [
        # OLINC-062: the addition recurrence quantifies w, not x.
        (r"\lforall[w][u(w')=u" + '\n' + r" (w)']",
         r"\lforall[w][u(x')=u" + '\n' + r" (x)']"),
    ],
    'OLP-0334': [
        # OLINC-064: the source reuses the earlier undecidability label.
        (r'\ollabel{thm:sol-not-compact}',
         r'\ollabel{thm:sol-undecidable}'),
        # OLINC-065: the finite bound applies to Gamma_0, not all Gamma.
        (r'!A^{\ge n} \in \Gamma_0', r'!A^{\ge n} \in \Gamma'),
    ],
    'OLP-0340': [
        # OLINC-069: the coding relation in this proof is for X, not Z.
        (r'$s(X)$ चे उपसंच', r'$s(Z)$ चे उपसंच'),
    ],
    'OLP-0347': [
        # OLINC-074: the final nested substitution acts on the defined body N.
        (r'\Subst{\Subst{N}{M_1}{x_1}\ldots}{M_n}{x_n}',
         r'\Subst{\Subst{P}{M_1}{x_1}\ldots}{M_n}{x_n}'),
    ],
    'OLP-0348': [
        # OLINC-075: the displayed arity and all indexed inputs use k.
        (r'$k$-स्थानी आंशिक फलन', r'$n$-स्थानी आंशिक फलन'),
        # OLINC-076: the no-normal-form case applies F to the same inputs.
        (r'$F\, \num{n_0}\, \num{n_1}' + '\n' +
         r'\dots \num{n_{k-1}}$',
         r'$F, \num{n_0}\, \num{n_1}' + '\n' +
         r'\dots \num{n_{k-1}}$'),
    ],
    'OLP-0353': [
        # OLINC-077: F, not the already assigned H, defines f.
        (r'!!{lambda define}s असे पद $F$ हवे आहे',
         r'!!{lambda define}s असे पद $H$ हवे आहे'),
        # OLINC-078: h's first argument is the recursion index x.
        (r'h(x, f(x,\vec z), \vec z)',
         r'h(z, f(x,\vec z), \vec z)'),
        # Localize the two ordinary-language conjunctions inside math text.
        (r'\text{ आणि}', r'\text{ and}'),
    ],
    'OLP-0360': [
        # OLINC-083: the scope is the body occurrence M, not enclosing N.
        (r'त्यातील~$M$', r'त्यातील~$N$'),
    ],
    'OLP-0361': [
        # OLINC-085: in the abstraction case M=lambda-y.P, the body is P.
        (r'$x \notin \FV{P}$. त्यामुळे', r'$x \notin \FV{Q}$. त्यामुळे'),
        # OLINC-086: remove a stray closing parenthesis in the hypothesis.
        (r'$x \in \FV{M}$ असेल', r'$x \in \FV{M})$ असेल'),
        # OLINC-087: the application substitutes for x, not y.
        (r'$\Subst{(PQ)}{N}{x}$' + '\n' + '    परिभाषित',
         r'$\Subst{(PQ)}{N}{y}$' + '\n' + '    परिभाषित'),
        # OLINC-088: the theorem hypothesis concerns x in lambda-y.P.
        (r'$x \in' + '\n' + r'    \FV{\lambd[y][P]}$',
         r'$y \in' + '\n' + r'    \FV{\lambd[x][P]}$'),
        (r'$x \in \FV{P}$.' + '\n' + '    आता:',
         r'$y \in \FV{P}$.' + '\n' + '    आता:'),
        # OLINC-089: restore the frozen erroneous induction line for QA.
        (r'((\FV{P} \setminus \{x\}) \cup \FV{N}) \setminus \{y\}',
         r'((\FV{P} \setminus \{y\}) \cup (\FV{N} \setminus \{x\})'),
        (r'&& y \notin \FV{N}', r'&& x \notin \FV{N}'),
    ],
    'OLP-0362': [
        # OLINC-091: the first definition needs the same distinct-binder
        # condition as its two explicitly equivalent reformulations.
        (r'$x \neq y$, $y \notin \FV{N}$ असेल आणि' + '\n' +
         r'  $\Subst{N}{y}{x}$',
         r'$y \notin \FV{N}$ असेल आणि' + '\n' +
         r'  $\Subst{N}{y}{x}$'),
        # OLINC-093: use the FV macro consistently in formulae.
        (r'$x \in \FV{N}$ असेल, तर:', r'$x \in FV(N)$ असेल, तर:'),
        (r'$x \notin \FV{N}$ असेल, तर:', r'$x \notin FV(N)$ असेल, तर:'),
        (r'& = \FV{\Subst{N}{y}{x}} \setminus \{y\}',
         r'& = FV{\Subst{N}{y}{x}} \setminus \{y\}'),
        (r"$z \notin \FV{N'}$", r"$z \notin FV(N')$"),
        (r'$z \notin \FV{R}$', r'$z \notin FV(R)$'),
        # OLINC-094: after x is replaced by y, thm:clr clears x.
        (r'$x \notin' + '\n' + r'    \FV{\Subst{N}{y}{x}}$',
         r'$y \notin' + '\n' + r'    \FV{\Subst{N}{y}{x}}$'),
        # OLINC-095: the cited results yield alpha-equivalence, not identity.
        (r'&\aeq', r'&='),
        # OLINC-096: the second corollary pair needs both premises.
        (r"$R'' \aeq R$ अशी", r"$R''$ अशी"),
        (r"आणि $\Subst{M''}{R''}{y}$ परिभाषित",
         r"आणि $\Subst{M'}{R'}{y}$ परिभाषित"),
    ],
    'OLP-0364': [
        # OLINC-098: ordinary 'etc.' belongs in Marathi prose, not math.
        (r'$\rep{M}[0], \rep{M}[1]$ इत्यादी',
         r'$\rep{M}[0], \rep{M}[1], etc. $'),
    ],
    'OLP-0366': [
        # OLINC-099: eta-equivalence needs the general fresh-binder law.
        (r'\lambd[x][M x] \equal M \text{ जर } x \notin FV(M)',
         r'\lambd[x][f x] \equal f'),
        # OLINC-101: use the extensionality macro, not bare math 'ext'.
        (r'म्हणजे \ext{} नियमाने', r'म्हणजे $ext$ नियमाने'),
        (r'$\equal[\ext]$ मध्ये', r'$\equal[ext]$ मध्ये'),
    ],
    'OLP-0368': [
        # OLINC-103: the source proof names undefined P and Q where
        # the boundary paths end at P_m and Q_n.
        (r'$N_{m,0}$ हे $P_m$ आणि $N_{0,n}$ हे $Q_n$ आहे.',
         r'$N_{m,0}$ हे $P$ आणि $N_{0,n}$ हे $Q$ आहे.'),
    ],
    'OLP-0369': [
        # OLINC-105: abstraction closure must use parallel reduction.
        (r"\item \ollabel{defn:bredpar2} $N \bredpar N'$ असेल",
         r"\item \ollabel{defn:bredpar2} $N \xrightarrow{\beta} N'$ असेल"),
        # OLINC-106: the substitution induction case must use R' on
        # the right side, as the lemma premise and target already do.
        (r"\lambd[x][\Subst{N'}{R'}{y}]$",
         r"\lambd[x][\Subst{N'}{R}{y}]$"),
    ],
    'OLP-0370': [
        # OLINC-108: the fourth proof case lists N', not a second M'.
        (r"$x$, $N$, $N'$, $Q$, $Q'$ साठी",
         r"$x$, $N$, $M'$, $Q$, $Q'$ साठी"),
    ],
    'OLP-0371': [
        # OLINC-110: abstraction closure must use the beta-eta
        # parallel relation rather than an ordinary beta step.
        (r"\item \ollabel{defn:beredpar2} $N \beredpar N'$ असेल",
         r"\item \ollabel{defn:beredpar2} $N \xrightarrow{\beta} N'$ असेल"),
    ],
    'OLP-0372': [
        # OLINC-113: eta conversion uses the eta one-step relation.
        (r"$M \eredone M'$ हे $\eta$-परिवर्तनाचे प्रकरण",
         r"$M \bredone M'$ हे $\eta$-परिवर्तनाचे प्रकरण"),
    ],
    'OLP-0374': [
        # OLINC-114: the constant-function equation uses c_k.
        (r"$c_k(n) = k$", r"$c(n) = k$"),
    ],
    'OLP-0375': [
        # OLINC-117: the curried numeral needs two beta steps.
        (r"$\num{n}fx \red f^nx$", r"$\num{n}fx \redone f^nx$"),
        # OLINC-118: the displayed curried addition steps are
        # multi-step reductions, including the alternate definition.
        (r"(\lambd[{a}{b}][\lambd[fx][{a} f ({b} f x)]])\num n\,\num m & \red",
         r"(\lambd[{a}{b}][\lambd[fx][{a} f ({b} f x)]])\num n\,\num m & \redone"),
        (r"& \red \lambd[fx][\num{n}\, f (f^m x)]",
         r"& \redone \lambd[fx][\num{n}\, f (f^m x)]"),
        (r"& \red \lambd[fx][f^n (f^m x)]",
         r"& \redone \lambd[fx][f^n (f^m x)]"),
        (r"& \red \num{n}\, \fn{Succ}\, \num{m}.",
         r"& \redone \num{n}\, \fn{Succ}\, \num{m}."),
        # OLINC-116: multiplication must use both operands.
        (r"\fn{Mult}' \ident \lambd[ab][b (\fn{Add}\, a) \num{0}].",
         r"\fn{Mult}' \ident \lambd[ab][a (\fn{Add}\, a) \num{0}]."),
    ],
    'OLP-0377': [
        # OLINC-120: the relation's arity must match its k arguments.
        (r'$R \subseteq \Nat^k$', r'$R \subseteq \Nat^n$'),
    ],
    'OLP-0378': [
        # OLINC-121: the last composition term is G_{k-1}, not G_k.
        (r'$G_{k-1}$ या पदांनी', r'$G_k$ या पदांनी'),
        # OLINC-123: primitive recursion uses the step function g.
        (r'h(x_1, \dots, x_n, y+1) & = g(',
         r'h(x_1, \dots, x_n, y+1) & = h('),
    ],
    'OLP-0379': [
        # OLINC-124: repeated multiplication typo uses the second input.
        (r'\fn{Mult} \ident \lambd[ab][b (\fn{Add}\, a) 0]',
         r'\fn{Mult} \ident \lambd[ab][a (\fn{Add}\, a) 0]'),
        # OLINC-125: the weaker comparison concerns Church's Y_C.
        (r'कमकुवत आहे: $Y_Cg \equal[\beta] g(Y_Cg)$',
         r'कमकुवत आहे: $Yg \equal[\beta] g(Yg)$'),
        (r'$Y_Cg \bred g(Y_Cg)$', r'$Yg \bred g(Yg)$'),
    ],
    'OLP-0380': [
        # OLINC-127: the lemma result matches H and the proof's h.
        (r'h(x_1, \dots, x_k) = \umin{y}{f(x_1,\dots,x_k, y) = 0}',
         r'g(x_1, \dots, x_k) = \umin{y}{f(x_1,\dots,x_k, y) = 0}'),
        (r'याने परिभाषित केलेले $h$~देखील',
         r'याने परिभाषित केलेले $g$~देखील'),
        # OLINC-128: close the Search recursive-call parentheses.
        (r'(g\, \vec{x} (\fn{Succ}\, y))]]',
         r'(g\, \vec{x} (\fn{Succ}\, y)]]'),
    ],
    'OLP-0391': [
        # OLINC-131: the countervaluation satisfies Gamma, not entailment.
        (r'$\pSat{v}{\Gamma}[\Log L]$',
         r'$\pAssign v \Entails[\Log L] \Gamma$'),
        (r'$\pSat/{v}{!B}[\Log L]$',
         r'$\pAssign v \Entails/[\Log L] !B$'),
    ],
    'OLP-0394': [
        # OLINC-132: the conjunction display gives both input orders.
        (r'\tf{\land}(\Undef, \False) = \False.',
         r'\tf{\land}(\False, \Undef) = \False.'),
        # OLINC-133: remove the stray closing parenthesis.
        (r'$(\lnot p \land p) \lif q$',
         r'$(\lnot p \land p) \lif q)$'),
    ],
    'OLP-0397': [
        # OLINC-135/136: the second conjunct is C, not repeated B.
        (r'$\pValue v(!C)[\LogKs]  = \False$',
         r'$\pValue v(!B)[\LogKs]  = \False$'),
        (r'$\pValue v(!C)[\LogKs]  = \True$',
         r'$\pValue v(!B)[\LogKs]  = \True$'),
    ],
    'OLP-0399': [
        # OLINC-138: the rational denominator must be positive.
        (r'n,m \in \Nat \text{ आणि } 0<m \text{ आणि } n\le m',
         r'n,m \in \Nat \text{ and } n\le m'),
        # OLINC-139: exactly m values require n<m, not n<=m.
        (r'n \in \Nat \text{ आणि } n<m',
         r'n \in \Nat \text{ and } n\le m'),
    ],
    'OLP-0401': [
        # OLINC-141: remove inline math delimiters inside display math.
        (r'      1 & \text{जर } x =0\\',
         r'      $1$ & \text{if } x =0\\'),
        (r'      0 & \text{इतर वेळी}',
         r'      $0$ & \text{otherwise}'),
    ],
    'OLP-0403': [
        # OLINC-143: align the left-side last index with the conjunction.
        (r'!A_1, \dots, !A_m & \Sequent !B_1',
         r'!A_1, \dots, !A_n & \Sequent !B_1'),
        # OLINC-144: supply the omitted valuation argument.
        (r'किंवा $\pValue v(!A) = \False$ असते.',
         r'किंवा $\pValue(!A) = \False$ असते.'),
    ],
    'OLP-0404': [
        # OLINC-145: each position has its own formula sequence.
        (r'प्रत्येक $\Gamma_i$ ही', r'प्रत्येक $\Gamma_1$ ही'),
    ],
    'OLP-0410': [
        # OLINC-147: pair the conditional expansion's closing parenthesis.
        (r'$(\lnot !A \lor !B)$', r'$\lnot !A \lor !B)$'),
    ],
    'OLP-0411': [
        # OLINC-148: gate biconditional substitution on its own tag.
        (r'\tagitem{prvIff}{\indcase{!A}{(!B \liff',
         r'\tagitem{prvIf}{\indcase{!A}{(!B \liff'),
    ],
    'OLP-0413': [
        # OLINC-149: specify the world in the second duality proof.
        (r'$\mSat/{M}{\Box\lnot !A}[w]$.' + '\n' + r'      $\mSat{M}{\Box\lnot !A}[w]$',
         r'$\mSat/{M}{\Box\lnot !A}$.' + '\n' + r'      $\mSat{M}{\Box\lnot !A}[w]$'),
    ],
    'OLP-0416': [
        # OLINC-150: select the negation induction case with its own tag.
        (r'\tagitem{prvNot}{\indcase{!A}{\lnot !B}',
         r'\tagitem{prvFalse}{\indcase{!A}{\lnot !B}'),
        # OLINC-151: the last negation equivalence invokes modal satisfaction.
        (r'\text{मोडल पूर्तिच्या $\mSat{M}{}[w]$ व्याख्येवरून}.',
         r'\text{मोडल पूर्तिच्या $\pSat{v}{}$ व्याख्येवरून}.'),
        # OLINC-152: the biconditional case starts with a biconditional.
        (r'\pSat{v}{!B \liff !C} \Leftrightarrow {} &',
         r'\pSat{v}{!B \lif !C} \Leftrightarrow {} &'),
    ],
    'OLP-0418': [
        # OLINC-153: keep the modal model a triple in the simple countermodel.
        (r"\mModel{M'} =" + '\n' + r"  \tuple{W', R', V'}$",
         r"\mModel{M'} =" + '\n' + r"  \{W', R', V'\}$"),
    ],
    'OLP-0423': [
        # OLINC-157: evaluate Box A at the chosen world in the D proof.
        (r'$\mSat{M}{\Box !A}[w]$', r'$\mSat{M}{\Box !A}$'),
        # OLINC-158: close the parenthetical outside the valuation math.
        (r'$V(q) = \emptyset$)', r'$V(q) = \emptyset)$'),
    ],
    'OLP-0424': [
        # OLINC-159: A_n needs n edges, and its finite witness needs n+1 points.
        (r'\Atom{Q}{a_{n},a_{n+1}}', r'\Atom{Q}{a_{n-1},a_{n}}'),
        (r'\Domain{M_k} = \{1, \dots, k+1\}',
         r'\Domain{M_k} = \{1, \dots, k\}'),
        (r'\dots, k+1\}$ वरील', r'\dots, k\}$ वरील'),
    ],
    'OLP-0426': [
        # OLINC-162: the true case must translate true, not false.
        (r'\tagitem{prvTrue}{\indcase{!A}{\ltrue}',
         r'\tagitem{prvTrue}{\indcase{!A}{\lfalse}'),
        # OLINC-163: evaluate the free-variable translation under s.
        (r'\Atom{X}{y})] \lif \Atom{X}{x}}[s]$',
         r'\Atom{X}{y})] \lif \Atom{X}{x}}$'),
    ],
    'OLP-0430': [
        # OLINC-166: the inferred member is the K axiom formula.
        (r'$\Ax{K} \in \Sigma$', r'$K \in \Sigma$'),
    ],
    'OLP-0432': [
        # OLINC-167: remove the extra closing parenthesis in the RK result.
        (r'$\Log{K} \Proves \Box!A \lif (\Box !B \lif \Box(!A \land !B))$',
         r'$\Log{K} \Proves \Box!A \lif (\Box !B \lif \Box(!A \land !B)))$'),
        # OLINC-168: the replacement formula uses the marked B metavariable.
        (r'$\Log{K} \Proves \Subst{!C}{!B}{q}$.',
         r'$\Log{K} \Proves \Subst{!C}{B}{q}$'),
    ],
    'OLP-0433': [
        # OLINC-169: close the proof with the proposition's stated order.
        (r'$\Log{K} \Proves \Diamond(!A\lor!B) \lif (\Diamond!A \lor \Diamond!B)$',
         r'$\Log{K} \Proves \Diamond(!A\lor!B) \lif (\Diamond!B \lor \Diamond!A)$'),
    ],
    'OLP-0437': [
        # OLINC-171: KT derives the D axiom formula, not a logic named D.
        (r'\Log{KT} \Proves' + '\n' + r'  \Ax{D}',
         r'\Log{KT} \Proves' + '\n' + r'  \Log{D}'),
        # OLINC-172: nonderivability concerns the axiom formulas 4 and 5.
        (r'$\Log{KTB} \Proves/ \Ax{4}$ आणि $\Log{KTB} \Proves/ \Ax{5}$.',
         r'$\Log{KTB} \Proves/ \Log{4}$ and $\Log{KTB} \Proves/ \Log{5}$.'),
    ],
    'OLP-0440': [
        # OLINC-174: the proof invokes the consistency definition, not item b.
        ('सुसंगततेच्या व्याख्येवरून',
         r'\olref{prop:consistencyfacts-b} वरून'),
    ],
    'OLP-0443': [
        # OLINC-175: completeness yields the negated formula in the last step.
        (r'असल्याने $\lnot!A \in \Gamma$.',
         r'असल्याने $!A \in \Gamma$.'),
        # OLINC-176: the biconditional case assumes its own formula absent.
        (r'उलट $!A \liff !B \notin \Gamma$',
         r'उलट $!A \lif !B \notin \Gamma$'),
    ],
    'OLP-0444': [
        # OLINC-177: length-at-most-n ensures every indexed variable appears.
        (r'लांबी~$n$ पर्यंतची सर्व सूत्रे',
         r'लांबी~$n$ असलेली सर्व सूत्रे'),
    ],
    'OLP-0445': [
        # OLINC-178: the last premise is B_k, matching the finite list.
        (r'(!B_k \lif !A)\cdots)',
         r'(!B_n \lif !A)\cdots)'),
        (r'(\Box!B_k \lif \Box!A)\cdots)',
         r'(\Box!B_n \lif \Box!A)\cdots)'),
        # OLINC-179: the invoked lemma derives the sequent relative to Sigma.
        (r'\Box\Box^{-1}\Gamma \Proves[\Sigma] \Box!A',
         r'\Box\Box^{-1}\Gamma \Proves \Box!A'),
    ],
    'OLP-0447': [
        # OLINC-180: the exercise selector must match the probAnd branch.
        ('probNot,probAnd,probOr',
         'probNot,proband,probOr'),
    ],
    'OLP-0451': [
        # OLINC-181: a finite quotient may have finite as well as infinite classes.
        ('प्रत्येक वर्गात\nकदाचित अनंत जगे असतील,',
         'प्रत्येक वर्गात\nअनंत जगे असतील,'),
        # OLINC-183: the toy Box argument uses universal accessibility.
        ('प्रथम प्रत्येक जग प्रत्येक\nजगाला प्राप्य आहे असे\nसमजू.',
         'प्रथम प्राप्यता संबंध नाही असे\nसमजू.'),
        # OLINC-182: V* is a valuation function and needs its argument p.
        (r'$[w] \in V^*(p)$;' + '\n' + 'म्हणून',
         r'$[w] \in V^*$;' + '\n' + 'म्हणून'),
    ],
    'OLP-0454': [
        # OLINC-184: the source's Nat contains zero, outside W = PosInt.
        (r'V(p) = \Setabs{2n}{n \in' + '\n' + r'    \PosInt}',
         r'V(p) = \Setabs{2n}{n \in' + '\n' + r'    \Nat}'),
        # OLINC-185: keep both valuations inside the binary-tree world set;
        # the root 0 remains p-true as depicted in the source figure.
        (r'V(p) = \{0\} \cup \Setabs{\sigma' + '\n' + r'    0}{\sigma \in W}',
         r'V(p) = \Setabs{\sigma' + '\n' + r'    0}{\sigma \in \Bin^*}'),
        (r'V(q) = \Setabs{\sigma 1}{\sigma \in' + '\n' + r'    W}',
         r'V(q) = \Setabs{\sigma 1}{\sigma \in' + '\n' + r'    \Bin^* \setminus \{1\}}'),
    ],
    'OLP-0456': [
        # OLINC-186: the filtered world is [w], not the original world w.
        (r'$\mSat{M^*}{!A}[{[w]}]$',
         r'$\mSat{M^*}{!A}[w]$'),
    ],
    'OLP-0459': [
        # OLINC-188: forced arrows in a filtration connect quotient worlds.
        (r'मग $[w_2]$ आणि~$[w_5]$',
         r'मग $w_2$ आणि~$w_5$'),
        # OLINC-190: w2 needs a self-loop to make both displayed models
        # serial and Euclidean, matching the labels and captions.
        (r'    \draw[reflexive above] (w2) to (w2);' + '\n', ''),
    ],
    'OLP-0464': [
        # OLINC-191: a countermodel falsifies A at w.
        (r'पण $\mSat/{M}{!A}[w]$' + '\n' + r'  असेल',
         r'पण $\mSat{M}{!A}[w]$' + '\n' + r'  असेल'),
        # OLINC-192: the F-or rule premise retains its prefix.
        (r'\sFmla{\False}{!B \lor !C}[\sigma] \in \Gamma',
         r'\sFmla{\False}{!B \lor !C} \in \Gamma'),
        # OLINC-193: F Box introduces F B, not F A.
        (r'\TRule{\False}{\Box}$ लावून शाखा विस्तारित केली:' + '\n'
         + r'  \iftag{probBox}{सरावासाठी.}{शाखेवर' + '\n'
         + r'    $\sFmla{\False}{!B}[\sigma.n]$',
         r'\TRule{\False}{\Box}$ लावून शाखा विस्तारित केली:' + '\n'
         + r'  \iftag{probBox}{सरावासाठी.}{शाखेवर' + '\n'
         + r'    $\sFmla{\False}{!A}[\sigma.n]$'),
        # OLINC-194: T Diamond introduces T B, not T A.
        (r'\TRule{\True}{\Diamond}$ लावून शाखा विस्तारित' + '\n'
         + r'  केली: \iftag{probDiamond}{सरावासाठी.}{शाखेवर' + '\n'
         + r'    $\sFmla{\True}{!B}[\sigma.n]$',
         r'\TRule{\True}{\Diamond}$ लावून शाखा विस्तारित' + '\n'
         + r'  केली: \iftag{probDiamond}{सरावासाठी.}{शाखेवर' + '\n'
         + r'    $\sFmla{\True}{!A}[\sigma.n]$'),
        # OLINC-195: the corollary derives semantic entailment.
        (r'म्हणून $\Gamma \Entails !A$.',
         r'म्हणून $\Gamma \Proves !A$.'),
    ],
    'OLP-0466': [
        # OLINC-198: the Euclidean Box proof evaluates at f(sigma.n).
        (r'$\mSat{M}{\Box !B}[f(\sigma.n)]$' + '\n'
         + r'    असल्याने $\mSat{M}{!B}[w]$',
         r'$\mSat{M}{\Box !B}[f(\sigma).n]$' + '\n'
         + r'    असल्याने $\mSat{M}{!B}[w]$'),
        # OLINC-199: 4r-Diamond introduces F Diamond B.
        (r'$\sFmla{\False}{\Diamond!B}[\sigma]$ हे नवे',
         r'$\sFmla{\True}{\Box!B}[\sigma]$ हे नवे'),
        # OLINC-200: the Euclidean Diamond proof evaluates at f(sigma.n).
        (r'$\mSat/{M}{\Diamond !B}[f(\sigma.n)]$' + '\n'
         + r'    असल्याने $\mSat/{M}{!B}[w]$',
         r'$\mSat/{M}{\Diamond !B}[f(\sigma).n]$' + '\n'
         + r'    असल्याने $\mSat/{M}{!B}[w]$'),
    ],
    'OLP-0468': [
        # OLINC-201: repair the incomplete branch examples; project
        # each corrected example formula back to the exact frozen form.
        (r'$\sFmla{\True}{!B \land !C}[\sigma]$' + '\n' + r'असेल, तर',
         r'$\sFmla{\True}{!B \land !C}$' + '\n' + r'असेल, तर'),
        (r'$\sFmla{\True}{!B \lor !C}[\sigma]$' + '\n'
         + r'असेल, तर $\sFmla{\True}{!B}[\sigma]$',
         r'$\sFmla{\True}{!B \lor !C}[\sigma]$' + '\n'
         + r'असेल, तर $\sFmla{\False}{!B}[\sigma]$'),
        (r'\iftag{prvBox}' + '\n'
         + r'{$\sFmla{\False}{\Box !B}[\sigma]$}' + '\n'
         + r'{$\sFmla{\True}{\Diamond !B}[\sigma]$}',
         r'\iftag{prvBox}' + '\n'
         + r'{$\sFmla{\False}{\Box}[\sigma]$}' + '\n'
         + r'{$\sFmla{\True}{\Diamond}[\sigma]$}'),
        (r'\iftag{prvBox}{$\sFmla{\False}{!B}[\sigma.n]$}' + '\n'
         + r'{$\sFmla{\True}{!B}[\sigma.n]$}',
         r'\iftag{prvBox}{$\sFmla{\False}{\Box}[\sigma.n]$}' + '\n'
         + r'{$\sFmla{\True}{\Diamond}[\sigma.n]$}'),
        (r'\iftag{prvBox}{$\sFmla{\True}{\Box !B}[\sigma]$}' + '\n'
         + r'{$\sFmla{\False}{\Diamond !B}[\sigma]$}',
         r'\iftag{prvBox}{$\sFmla{\True}{\Box}[\sigma]$}' + '\n'
         + r'{$\sFmla{\False}{\Diamond}[\sigma]$}'),
        (r'\iftag{prvBox}{$\sFmla{\True}{!B}[\sigma.n]$}' + '\n'
         + r'{$\sFmla{\False}{!B}[\sigma.n]$}',
         r'\iftag{prvBox}{$\sFmla{\True}{\Box}[\sigma.n]$}' + '\n'
         + r'{$\sFmla{\False}{\Diamond}[\sigma.n]$}'),
        # OLINC-203: in each false connective case the second
        # induction-hypothesis judgment concerns C rather than B.
        (r'$\mSat/{M(\Delta)}{!B}[\sigma]$ किंवा' + '\n'
         + r'      $\mSat/{M(\Delta)}{!C}[\sigma]$',
         r'$\mSat/{M(\Delta)}{!B}[\sigma]$ किंवा' + '\n'
         + r'      $\mSat/{M(\Delta)}{!B}[\sigma]$'),
        (r'$\mSat/{M(\Delta)}{!B}[\sigma]$ आणि' + '\n'
         + r'      $\mSat/{M(\Delta)}{!C}[\sigma]$',
         r'$\mSat/{M(\Delta)}{!B}[\sigma]$ आणि' + '\n'
         + r'      $\mSat/{M(\Delta)}{!B}[\sigma]$'),
        (r'$\mSat{M(\Delta)}{!B}[\sigma]$ आणि' + '\n'
         + r'      $\mSat/{M(\Delta)}{!C}[\sigma]$',
         r'$\mSat{M(\Delta)}{!B}[\sigma]$ आणि' + '\n'
         + r'      $\mSat/{M(\Delta)}{!B}[\sigma]$'),
    ],
    'OLP-0469': [
        # OLINC-205: non-entailment concerns A, not an unmarked A.
        (r'शिवाय $\Entails/ !A$',
         r'शिवाय $\Entails/ A$'),
        # OLINC-206: the Diamond example uses F Diamond at line 3.
        (r'$\sFmla{\False}{\Diamond(p \land q)}[1]$',
         r'$\sFmla{\True}{\Diamond(p \land q)}[1]$'),
        (r'$\TRule{\False}{\Diamond}$ लावायचा असतो;',
         r'$\TRule{\True}{\Diamond}$ लावायचा असतो;'),
        # OLINC-207: keep the second diagram's root identical to
        # the initial and final tableau root formula.
        (r'दोन्हींसाठी:' + '\n' + r'  \begin{oltableau}' + '\n'
         + r'    [\pFmla{\False}{(\Diamond p \land \Diamond q) \lif \Diamond(p \land q)}{1},',
         r'दोन्हींसाठी:' + '\n' + r'  \begin{oltableau}' + '\n'
         + r'    [\pFmla{\False}{\Diamond(p \land q) \lif (\Diamond p \land \Diamond q)}{1},'),
        # OLINC-208: q is true at the 1.2 world on line 7.
        (r'$\sFmla{\True}{q}[1.2]$ आहे)',
         r'$\sFmla{\True}{q}[1.1]$ आहे)'),
    ],
    'OLP-0478': [
        # OLINC-209: the temporal language's formula clause must use
        # the same future operator as its preceding list and semantics.
        (r'$\Ftemp !A$', r'$F !A$'),
    ],
    'OLP-0488': [
        # OLINC-211: both agent quantifiers in the bisimulation
        # definition range over the chapter's agent-symbol set G.
        (r'$a \in G$', r'$a \in A$'),
    ],
    'OLP-0489': [
        # OLINC-212: the connective inventory must include the
        # biconditional already present in its formation rules.
        (r'  \iftag{prvIff}{\ycomma $\liff$ (!!{biconditional})}{}.' + '\n', ''),
    ],
    'OLP-0490': [
        # OLINC-213: the vacuity example must use the same marked
        # formula metavariable B as the announcement grammar.
        (r'$[!A] !B$', r'$[!A]B$'),
    ],
    'OLP-0495': [
        # OLINC-214: the curried construction's codomain is formula !C.
        (r'ही स्वतः फलन आहे: $!A \land !B$ च्या रचनांपासून' + '\n'
         + r'$!C$ च्या रचनांकडे जाणारे.',
         r'ही स्वतः फलन आहे: $!A \land !B$ च्या रचनांपासून' + '\n'
         + r'$C$ च्या रचनांकडे जाणारे.'),
        # OLINC-215: the left disjunction injection retains its input M_1.
        (r'ते $M_1$ ला $\tuple{1, M_1}$ कडे नेते.',
         r'ते $M_1$ ला $\tuple{1, M_2}$ कडे नेते.'),
    ],
    'OLP-0496': [
        # OLINC-216: the BHK pair's second component constructs A_2.
        (r'BHK अर्थनिर्धारणानुसार $!A_1 \land !A_2$ ची',
         r'BHK अर्थनिर्धारणानुसार $!A_1 \land !A_1$ ची'),
    ],
    'OLP-0501': [
        # Localize the ordinary-language conjunction inside the aligned display.
        (r'\text{ आणि}', r'\text{ and}'),
    ],
}


_SOURCE_QA_NORMALIZATIONS = {
    'OLP-0333': [
        # OLINC-063: the frozen source closes the math delimiter before
        # the second argument's brace, so even source-to-source QA fails.
        (r'$\Sat{M}{!P \lif !A$}', r'$\Sat{M}{!P \lif !A}$'),
    ],
    'OLP-0426': [
        # OLINC-161: the source closes the induction-case argument before
        # its inline math delimiter, so source-to-source QA cannot parse it.
        (r'\liff \ST_x(!C))}$.}{}',
         r'\liff \ST_x(!C))$.}}{}'),
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
    normalized_source = source
    source_normalizations = []
    for frozen, corrected in _SOURCE_QA_NORMALIZATIONS.get(unit_id, []):
        if frozen in normalized_source:
            normalized_source = normalized_source.replace(frozen, corrected)
            source_normalizations.append((frozen, corrected))
    result = check(normalized_source, projected)
    if source_normalizations and applied:
        result = {
            'formula_multiset_parity_after_documented_source_typo_normalization_and_correction_projection': result.pop('formula_multiset_parity'),
            'macro_multiset_parity_after_documented_source_correction_projection': result.pop('macro_multiset_parity'),
            **result,
            'documented_source_typo_normalization_applied': True,
            'documented_source_correction_projection_applied': True,
        }
    elif source_normalizations:
        result = {
            'formula_multiset_parity_after_documented_source_typo_normalization': result.pop('formula_multiset_parity'),
            **result,
            'documented_source_typo_normalization_applied': True,
        }
    elif applied:
        if unit_id == 'OLP-0054':
            result = {
                'formula_multiset_parity_after_documented_equivalence_projection': result.pop('formula_multiset_parity'),
                'macro_multiset_parity_after_documented_equivalence_projection': result.pop('macro_multiset_parity'),
                **result,
                'documented_equivalence_projection_applied': True,
            }
        else:
            result = {
                'formula_multiset_parity_after_documented_source_correction_projection': result.pop('formula_multiset_parity'),
                'macro_multiset_parity_after_documented_source_correction_projection': result.pop('macro_multiset_parity'),
                **result,
                'documented_source_correction_projection_applied': True,
            }
    return result
