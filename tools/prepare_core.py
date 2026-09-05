"""Prepare the completed six-chapter reader through OLP-0054 without launching TeX."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parents[1];B=P/'build/core';B.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,str(P/'tools/prepare_foundations.py')],check=True,capture_output=True)
base=(P/'build/foundations/openlogic-mr-foundations.tex').read_text(encoding='utf-8')
base=base.replace('संच आणि संबंध','संच, संबंध, फलने, संचांचे आकारमान, अंकगणितीकरण आणि अनंत संच').replace('दोन संपूर्ण प्रकरणे','सहा संपूर्ण प्रकरणे').replace('OLP-0019, एकूण 16 विभाग. उर्वरित 706','OLP-0054, एकूण 51 स्रोत-एकके आणि 45 वाचक-विभाग. उर्वरित 671')
extra=r'''\newcommand{\dom}[1]{\mathrm{dom}(#1)}
\newtheorem{cor}[defn]{निष्कर्ष}
\newcommand{\ran}[1]{\mathrm{ran}(#1)}
\newcommand{\comp}[2]{#2\circ #1}
\newcommand{\pto}{\mathrel{\ooalign{\hfil$\mapstochar\mkern 5mu$\hfil\cr$\to$}}}
\newcommand{\fdefined}{\downarrow}
\newcommand{\fundefined}{\uparrow}
\newcommand{\cardle}[2]{#1 \preceq #2}
\newcommand{\cardless}[2]{#1 \prec #2}
\newcommand{\cardeq}[2]{#1 \approx #2}
\newcommand{\cardneq}[2]{#1 \not\approx #2}
\newcommand{\Intequiv}{\sim}
\newcommand{\Ratequiv}{\backsim}
\newcommand{\Realequiv}{\Bumpeq}
\newcommand{\defis}{=}
\newcommand{\closureofunder}[2]{\mathrm{clo}_{#1}(#2)}
\newcommand{\Closureofunder}[2]{\mathrm{Clo}_{#1}(#2)}
\newtheorem{lem}[defn]{सहायक प्रमेय}
\newenvironment{editorial}{\begin{quote}\small\itshape}{\end{quote}}
\definecolor{oldiagcolorD}{HTML}{1973ba}
\newlength{\olphotowidth}\setlength{\olphotowidth}{0.35\textwidth}
'''
base=base.replace(r'\begin{document}',extra+r'\begin{document}',1)
base=base.replace(r'\newcommand{\olasset}[1]{\centering\resizebox{0.52\textwidth}{!}{\input{../../upstream/#1}}}',r'\newcommand{\olasset}[2][0.52\textwidth]{\centering\resizebox{#1}{!}{\input{../../upstream/#2}}}')
marker=r'\chapter*{स्रोतावरील संपादकीय नोंदी}';before,notes=base.split(marker);notes=marker+notes
def balanced(t,i):
    assert t[i]=='{';j=i+1;depth=1
    while depth:
        if t[j]=='{' and t[j-1]!='\\':depth+=1
        elif t[j]=='}' and t[j-1]!='\\':depth-=1
        j+=1
    return t[i+1:j-1],j
groups=[
    ('फलने','sfr:fun::chap',P/'mr/content/sets-functions-relations/functions',[
        'function-basics','function-kinds','functions-relations','inverses','composition','partial-functions'
    ],None),
    ('संचांचे आकारमान','sfr:siz::chap',P/'mr/content/sets-functions-relations/size-of-sets',[
        'introduction','enumerability','zig-zag','pairing','pairing-alt','non-enumerability',
        'reduction','equinumerous-sets','comparing-size','schroder-bernstein',
        'enumerability-alt','non-enumerability-alt','reduction-alt'
    ],None),
    ('अंकगणितीकरण','sfr:arith::chap',P/'mr/content/sets-functions-relations/arithmetization',[
        'integers','rationals','reals','cuts','reflections','checking-details','cauchy'
    ],'arithmetization'),
    ('अनंत संच','sfr:infinite::chap',P/'mr/content/sets-functions-relations/infinite',[
        'hilberts-hotel','dedekind-algebra','dedekind-induction','dedekinds-proof','card-sb'
    ],'infinite'),
]
raw=[]
for _,_,directory,names,_ in groups:
    raw.extend((directory/(name+'.tex')).read_text(encoding='utf-8') for name in names)
available=set(re.findall(r'\\label\{([^}]+)\}',before))
available.update(chapter_label for _,chapter_label,_,_,_ in groups)
for t in raw:
    m=re.search(r'\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',t);prefix=':'.join(m.groups());available.add(prefix+':sec')
    available.update(prefix+':'+k for k in re.findall(r'\\ollabel\{([^}]+)\}',t))
absent={'sth:choice::chap','sfr:cardinals:card-sb:sec','sfr:card-arithmetic:card-opps:sec','sth:::part','sth:ord-arithmetic::chap'};decisions=[]
def conditionals(t):
    while '\\oliflabeldef' in t:
        a=t.index('\\oliflabeldef');j=a+len('\\oliflabeldef');args=[]
        for _ in range(3):
            while t[j].isspace():j+=1
            v,j=balanced(t,j);args.append(v)
        key=args[0];assert key in available|absent,key
        selected=1 if key in available else 2;decisions.append({'label':key,'branch':'true' if selected==1 else 'false'})
        t=t[:a]+args[selected]+t[j:]
    return t
def reader_note(value):
    value=re.sub('〈([^〉]+)〉',lambda m:r'$\langle '+m[1]+r'\rangle$',value)
    value=value.replace('x∈A',r'$x\in A$')
    value=value.replace('√2',r'$\sqrt{2}$').replace('λ',r'$\lambda$')
    value=re.sub(r'\b0\^R\b',r'$0^R$',value)
    return value.replace('_',r'\_')
chunks=[]
words={'element':'घटक','surjective':'आच्छादक','surjection':'आच्छादन','injective':'एकास-एक','injection':'एकास-एक फलन','bijective':'एकास-एक व आच्छादक','bijection':'एकास-एक आच्छादन','enumerable':'गणनीय','nonenumerable':'अगणनीय'}
plural_words={'element':'घटक','surjection':'आच्छादक फलने','injection':'एकास-एक फलने','bijection':'एकास-एक आच्छादने'}
raw_index=0
for chapter,chapter_label,directory,names,preface in groups:
    chunks.append('\\chapter{'+chapter+'}\\label{'+chapter_label+'}')
    if preface:
        driver=(directory/(preface+'.tex')).read_text(encoding='utf-8')
        driver_preface=re.search(r'\\begin\{editorial\}.*?\\end\{editorial\}',driver,re.S)
        assert driver_preface
        chunks.append(driver_preface.group())
    for _ in names:
        t=raw[raw_index];raw_index+=1
        t=re.sub(r'(?m)^[ \t]*%READERNOTE\{(.*)\}$',lambda m:'\\begin{quote}\\small\\textbf{स्रोतदुरुस्ती.} '+reader_note(m[1])+'\\end{quote}',t)
        t=re.sub('〈([^〉]+)〉',lambda m:r'$\langle '+m[1]+r'\rangle$',t)
        t=re.sub(r'(?m)^[ \t]*%[^\n]*(?:\n|$)','',t);t=re.sub(r'\\documentclass[^\n]*\n','',t);t=t.replace('\\begin{document}','').replace('\\end{document}','')
        m=re.search(r'\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',t);prefix=list(m.groups());t=t[:m.start()]+t[m.end():]
        t=conditionals(t)
        t=t.replace(r'\[\small',r'\[')
        t=t.replace(r'\citep[\S70]{Frege1884}',r'(Frege, 1884, \S70)')
        t=t.replace(r'\citet[pp.~165--6]{Potter2004}',r'Potter (2004, pp.~165--6)')
        t=t.replace(r'\citet{Cantor1892}',r'Cantor (1892)')
        t=t.replace(r'\cite{Conway2006}',r'Conway (2006)')
        t=t.replace(r'\citealt{Benacerraf1965}',r'Benacerraf (1965)')
        t=t.replace(r'\citeauthor{OConnorRobertson:RN} \citeyear{OConnorRobertson:RN}',r"O'Connor आणि Robertson (2005) यांचा लेख")
        t=t.replace(r'\citealt{KatzKatz2012}',r'Katz आणि Katz (2012)')
        t=t.replace(r'\citealt[730]{EwaldSieg2013}',r'Ewald आणि Sieg (2013, p.~730)')
        t=t.replace(r'\citeyear{Dedekind1888}',r'1888')
        t=t.replace(r'\citealt[pp.~95--8]{Potter2004}',r'Potter (2004, pp.~95--8)')
        t=re.sub(r'\\citeyear\[Theorems\s+132--3\]\{Dedekind1888\}',r'1888, प्रमेये 132--3',t)
        t=t.replace(r'\citep[preface]{Dedekind1888}',r'(Dedekind, 1888, प्रस्तावना)')
        t=t.replace(r'\citep[\S66]{Dedekind1888}',r'(Dedekind, 1888, \S66)')
        t=t.replace(r'\citet[p.~23]{Potter2004}',r'Potter (2004, p.~23)')
        t=t.replace(r'\citet[pp.~157--8]{Potter2004}',r'Potter (2004, pp.~157--8)')
        t=t.replace(r'\printtoken{S}{nonenumerable}','अगणनीय').replace(r'\usetoken{S}{enumerable}','गणनीय')
        t=re.sub(r'\\olsection(?:\[[^]]*\])?\{([^}]+)\}',lambda m:'\\section{'+m[1]+'}\\label{'+':'.join(prefix)+':sec}',t)
        t=re.sub(r'\\ollabel\{([^}]+)\}',lambda m:'\\label{'+':'.join(prefix)+':'+m[1]+'}',t)
        def ref(m):
            options=re.findall(r'\[([^]]*)\]',m[1]);parts=prefix.copy()
            if options:parts[3-len(options):]=options
            key=':'.join(parts)+':'+m[2]
            return '\\ref{'+key+'}' if key in available else 'पर्यायी विभाग'
        t=re.sub(r'\\olref((?:\[[^]]*\])*)\{([^}]+)\}',ref,t)
        t=re.sub(r'\\cref\{([^}]+)\}',r'\\ref{\1}',t)
        for key,word in plural_words.items():t=re.sub(r'!!\^?a?\{'+key+r'\}s',word,t)
        for key,word in words.items():t=re.sub(r'!!\^?a?\{'+key+r'\}',word,t)
        assert '!!' not in t and '\\oliflabeldef' not in t and '\\olref' not in t and '\\cref' not in t
        assert not re.search(r'\\cite(?:author|year|alt|p|t)?(?:\[[^]]*\])?\{',t)
        chunks.append(t)
newnotes=r'''\item फलन प्रकरणातील OLFUN-001 ते OLFUN-005 या पाच
गोठवलेल्या-स्रोत निष्कर्षांची दुरुस्ती संबंधित परिच्छेदांलगत स्वतंत्र
``स्रोतदुरुस्ती'' नोंदींमध्ये दिली आहे. मूळ इंग्रजी बाइट्स बदललेले नाहीत.
\item संचांच्या आकारमानाच्या प्रकरणातील OLSIZ-001 ते OLSIZ-010
या दहा सामायिक गोठवलेल्या-स्रोत निष्कर्षांची आणि MRSIZ-001 ते MRSIZ-004
या चार स्थानिक निरीक्षणांची नोंद संबंधित परिच्छेदांलगत दिली आहे. मूळ
इंग्रजी बाइट्स बदललेले नाहीत.
\item सामायिक OLSIZ-011 सूचना अचूक बाइट-पुनर्तपासणीनंतर चुकीची ठरून
मागे घेण्यात आली; तिच्यावर आधारित कोणतीही मराठी दुरुस्ती केलेली नाही.
\item अंकगणितीकरण प्रकरणातील MRARITH-001 ते MRARITH-012 या बारा
गोठवलेल्या-स्रोत निरीक्षणांतील दुरुस्त्या किंवा स्पष्ट खुलासे संबंधित
परिच्छेदांलगत स्वतंत्र ``स्रोतदुरुस्ती'' नोंदींमध्ये दिले आहेत. मूळ
इंग्रजी बाइट्स बदललेले नाहीत.
\item अनंत संच प्रकरणातील MRINF-001 ते MRINF-003 या तीन स्रोत-निरीक्षणांची
नोंद ठेवली आहे. MRINF-001 मधील व्याकरणदोषाचा अभिप्रेत अर्थ थेट दिला आहे;
MRINF-002 मधील अप्रकट आधारसंचाचे गृहीतक तज्ज्ञ-पुनरावलोकनासाठी राखले आहे;
आणि MRINF-003 मधील विकृत निष्कर्ष संबंधित परिच्छेदालगत दुरुस्त केला आहे.
मूळ इंग्रजी बाइट्स बदललेले नाहीत.
'''
notes=notes.replace(r'\end{enumerate}',newnotes+r'\end{enumerate}',1)
newreferences=r'''\par\medskip
Gottlob Frege (1884). \textit{Die Grundlagen der Arithmetik}.
Wilhelm Koebner.

Georg Cantor (1892). ``Über eine elementare Frage der
Mannigfaltigkeitslehre.'' \textit{Jahresbericht der deutschen
Mathematiker-Vereinigung}, 1, 75--78.

Michael Potter (2004). \textit{Set Theory and its Philosophy}.
Oxford University Press.

John Conway (2006). ``The Power of Mathematics.'' In Alan Blackwell
and David MacKay (eds.), \textit{Power}, Darwin College Lectures.
Cambridge University Press.

John J. O'Connor and Edmund F. Robertson (2005). ``The real numbers:
Stevin to Hilbert.''
\url{http://www-history.mcs.st-and.ac.uk/HistTopics/Real_numbers_2.html}.

Karin Usadi Katz and Mikhail G. Katz (2012). ``Stevin Numbers and
Reality.'' \textit{Foundations of Science}, 17(2), 109--123.

Richard Dedekind (1888). \textit{Was sind und was sollen die Zahlen?}
Vieweg, Braunschweig.

David Hilbert (2013). \textit{David Hilbert's Lectures on the Foundations
of Arithmetic and Logic 1917--1933}. William Bragg Ewald and Wilfried Sieg
(eds.). Springer, Heidelberg.

'''
notes=notes.replace(r'\end{document}',newreferences+r'\end{document}',1)
out=before+'\n'.join(chunks)+'\n'+notes
out='\n'.join(line.rstrip() for line in out.splitlines())+'\n'
assert 'एकूण 51 स्रोत-एकके आणि 45 वाचक-विभाग' in out and out.count(r'\section{')==45
(B/'openlogic-mr-core.tex').write_text(out,encoding='utf-8',newline='\n')
manifest=[json.loads(x) for x in (P/'provenance/SOURCE_MANIFEST.jsonl').read_text(encoding='utf-8').splitlines()]
inputs=[]
for r in manifest[3:54]:
    p=P/'mr'/r['source_path'];inputs.append({'unit_id':r['unit_id'],'path':p.relative_to(P).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(B/'INPUTS.json').write_text(json.dumps({'input_units':inputs,'scope':'51 source units, 45 reader sections, six complete chapters','conditional_decisions':decisions,'source_issues':'Three Relations and five Functions notes; ten shared Size of Sets corrections and four Marathi-lane observations; twelve Arithmetization corrections or disclosures; three Infinite Sets observations or corrections; one manager false positive retracted before application; aligned English source is unchanged','notation':'Function, cardinal-comparison, arithmetization equivalence-relation and generated-closure macros copied from frozen upstream/open-logic-config.sty; composition applies first argument then second'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'prepared':'build/core/openlogic-mr-core.tex','units':len(inputs),'sections':45,'sha256':hashlib.sha256(out.encode()).hexdigest()}))
