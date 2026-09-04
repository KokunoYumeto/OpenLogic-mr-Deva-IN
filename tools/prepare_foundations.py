"""Prepare the cumulative sets-and-relations reader. Never launches TeX."""
import ast,re,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parents[1];B=P/'build/foundations';B.mkdir(parents=True,exist_ok=True)
recipe=ast.parse((P/'tools/prepare_sets.py').read_text(encoding='utf-8'))
preamble=next(ast.literal_eval(n.value) for n in recipe.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='preamble' for t in n.targets))
preamble=preamble.replace('मुक्त तर्कशास्त्र: संच','मुक्त तर्कशास्त्र: संच आणि संबंध').replace('{\\LARGE संच\\par}','{\\LARGE संच आणि संबंध\\par}').replace('संपूर्ण संच प्रकरण','दोन संपूर्ण प्रकरणे').replace('हे प्रकाशन संच प्रकरणापुरते आहे: मूळ 722 विभागांपैकी OLP-0004 ते OLP-0010.','हे प्रकाशन संच आणि संबंध या प्रकरणांचे आहे: मूळ 722 विभागांपैकी OLP-0004 ते OLP-0019, एकूण 16 विभाग. उर्वरित 706 विभागांचे काम अपूर्ण आहे.')
extra=r'''\newenvironment{intro}{}{}
\newcommand{\Id}[1]{\mathord{\mathrm{Id}_{#1}}}
\newcommand{\emptyseq}{\Lambda}
\newcommand{\liff}{\mathbin{\leftrightarrow}}
\newcommand{\equivrep}[2]{[#1]_{#2}}
\newcommand{\equivclass}[2]{#1/_{\!{#2}}}
\newcommand{\funrestrictionto}[2]{#1\mathord{\restriction}_{#2}}
\newcommand{\funimage}[2]{#1[#2]}
\newcommand{\citeyear}[1]{\hyperref[bib:#1]{1965}}
'''
preamble=preamble.replace(r'\begin{document}',extra+r'\begin{document}',1)
def balanced(t,i):
    assert t[i]=='{';j=i+1;d=1
    while d:
        if t[j]=='{' and t[j-1]!='\\':d+=1
        elif t[j]=='}' and t[j-1]!='\\':d-=1
        j+=1
    return t[i+1:j-1],j
def conditional_false(t):
    while '\\oliflabeldef' in t:
        a=t.index('\\oliflabeldef');j=a+len('\\oliflabeldef');args=[]
        for _ in range(3):
            while t[j].isspace():j+=1
            x,j=balanced(t,j);args.append(x)
        assert args[0] in ['sfr:arith:real:realline','cumul:::part']
        t=t[:a]+args[2]+t[j:]
    return t
chapters=[('sets',['basics','subsets','important-sets','unions-and-intersections','pairs-and-products','russells-paradox']),('relations',['relations-as-sets','reflections','special-properties','equivalence-relations','orders','graphs','trees','operations'])]
chunks=[];inputs=[]
for chapter,names in chapters:
    if chapter=='relations':chunks.append('\\chapter{संबंध}\\label{sfr:rel::chap}')
    for name in names:
        p=P/'mr/content/sets-functions-relations'/chapter/(name+'.tex');t=p.read_text(encoding='utf-8');inputs.append({'path':p.relative_to(P).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        t=re.sub(r'(?m)^%.*$','',t);t=re.sub(r'\\documentclass[^\n]*\n','',t)
        t=t.replace('\\begin{document}','').replace('\\end{document}','')
        m=re.search(r'\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',t);prefix=list(m.groups());t=t[:m.start()]+t[m.end():]
        t=conditional_false(t)
        t=re.sub(r'\\olsection\{([^}]+)\}',lambda m:'\\section{'+m[1]+'}\\label{'+':'.join(prefix)+':sec}',t)
        t=re.sub(r'\\ollabel\{([^}]+)\}',lambda m:'\\label{'+':'.join(prefix)+':'+m[1]+'}',t)
        def ref(m):
            options=re.findall(r'\[([^]]*)\]',m[1]);parts=prefix.copy()
            if options:parts[3-len(options):]=options
            return '\\ref{'+':'.join(parts)+':'+m[2]+'}'
        t=re.sub(r'\\olref((?:\[[^]]*\])*)\{([^}]+)\}',ref,t)
        t=re.sub(r'\\begin\{tagblock\}\{[^}]+\}','',t).replace('\\end{tagblock}','')
        t=t.replace('!!{formula}s','सूत्रे')
        for key,word in {'element':'घटक','formula':'सूत्र','derivation':'निष्पत्ती'}.items():t=re.sub(r'!!\^?a?\{'+key+r'\}s?',word,t)
        assert '!!' not in t
        chunks.append(t)
notes=r'''\chapter*{स्रोतावरील संपादकीय नोंदी}
\addcontentsline{toc}{chapter}{स्रोतावरील संपादकीय नोंदी}
या नोंदी अनुवादकाने वेगळ्या जोडल्या आहेत; त्या मूळ मजकुराचा भाग नाहीत.
स्रोताशी जुळवलेल्या TeX फाइलांतील मूळ चिन्हे बदललेली नाहीत.
\begin{enumerate}
\item विभाग \ref{sfr:rel:set:sec} मधील $K=L\cup I$ आणि $H=G\cup I$ येथे
$I$ चे स्वतंत्र नामकरण राहिले आहे. आधीच्या कर्णाच्या चर्चेनुसार त्याचा अर्थ
$\Id{\Nat}$ हा एकरूपता संबंध असा घ्यावा.
\item विभाग \ref{sfr:rel:tre:sec} मधील शाखेच्या व्याख्येत $z\in X\setminus B$
असे छापले आहे. वृक्षाचा आधारसंच $A$ आहे; येथे $X$ ऐवजी $A$ अभिप्रेत दिसतो.
\item त्याच विभागातील आरंभीच्या खंडांनुसार बंद असणाऱ्या उपवृक्षाच्या उदाहरणात
$A$ अरिक्त असणे आवश्यक आहे: आधीच्या व्याख्येनुसार वृक्षाला मूळ असते,
म्हणून रिक्त संच त्या व्याख्येत बसत नाही.
\end{enumerate}
\chapter*{संदर्भ}
\addcontentsline{toc}{chapter}{संदर्भ}
\phantomsection\label{bib:Benacerraf1965}
Paul Benacerraf (1965). ``What numbers could not be.''
\textit{The Philosophical Review}, 74(1), 47--73.
'''
out=preamble+'\n'.join(chunks)+notes+'\n\\end{document}\n'
assert re.findall(r'\\citeyear\{([^}]+)\}',out)==['Benacerraf1965']
(B/'openlogic-mr-foundations.tex').write_text(out,encoding='utf-8',newline='\n')
(B/'INPUTS.json').write_text(json.dumps({'input_units':inputs,'scope':'16 source units, 14 sections; all selected tagged prose; separate source editorial notes','reference_resolution':'Right-aligned optional arguments, verified against frozen open-logic-referencing.sty','citation':'Benacerraf1965 metadata copied from frozen upstream/bib/open-logic.bib','unavailable_external_labels':['sfr:arith:real:realline','cumul:::part']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'prepared':'build/foundations/openlogic-mr-foundations.tex','sections':len(inputs),'sha256':hashlib.sha256(out.encode()).hexdigest()}))
