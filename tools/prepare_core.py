"""Prepare Sets, Relations and Functions without launching TeX."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parents[1];B=P/'build/core';B.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,str(P/'tools/prepare_foundations.py')],check=True,capture_output=True)
base=(P/'build/foundations/openlogic-mr-foundations.tex').read_text(encoding='utf-8')
base=base.replace('संच आणि संबंध','संच, संबंध आणि फलने').replace('दोन संपूर्ण प्रकरणे','तीन संपूर्ण प्रकरणे').replace('OLP-0019, एकूण 16 विभाग. उर्वरित 706','OLP-0026, एकूण 23 विभाग. उर्वरित 699')
extra=r'''\newcommand{\dom}[1]{\mathrm{dom}(#1)}
\newcommand{\ran}[1]{\mathrm{ran}(#1)}
\newcommand{\comp}[2]{#2\circ #1}
\newcommand{\pto}{\mathrel{\ooalign{\hfil$\mapstochar\mkern 5mu$\hfil\cr$\to$}}}
\newcommand{\fdefined}{\downarrow}
\newcommand{\fundefined}{\uparrow}
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
names=['function-basics','function-kinds','functions-relations','inverses','composition','partial-functions']
raw=[(P/'mr/content/sets-functions-relations/functions'/(n+'.tex')).read_text(encoding='utf-8') for n in names]
available=set(re.findall(r'\\label\{([^}]+)\}',before))
for t in raw:
    m=re.search(r'\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',t);prefix=':'.join(m.groups());available.add(prefix+':sec')
    available.update(prefix+':'+k for k in re.findall(r'\\ollabel\{([^}]+)\}',t))
absent={'sth:choice::chap'};decisions=[]
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
chunks=[r'\chapter{फलने}\label{sfr:fun::chap}']
words={'element':'घटक','surjective':'आच्छादक','surjection':'आच्छादन','injective':'एकास-एक','injection':'एकास-एक फलन','bijective':'एकास-एक व आच्छादक','bijection':'एकास-एक आच्छादन'}
for t in raw:
    t=re.sub(r'(?m)^%READERNOTE\{(.*)\}$',lambda m:'\\begin{quote}\\small\\textbf{स्रोतदुरुस्ती.} '+m[1]+'\\end{quote}',t)
    t=re.sub(r'(?m)^%.*$','',t);t=re.sub(r'\\documentclass[^\n]*\n','',t);t=t.replace('\\begin{document}','').replace('\\end{document}','')
    m=re.search(r'\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',t);prefix=list(m.groups());t=t[:m.start()]+t[m.end():]
    t=conditionals(t)
    t=re.sub(r'\\olsection\{([^}]+)\}',lambda m:'\\section{'+m[1]+'}\\label{'+':'.join(prefix)+':sec}',t)
    t=re.sub(r'\\ollabel\{([^}]+)\}',lambda m:'\\label{'+':'.join(prefix)+':'+m[1]+'}',t)
    def ref(m):
        options=re.findall(r'\[([^]]*)\]',m[1]);parts=prefix.copy()
        if options:parts[3-len(options):]=options
        return '\\ref{'+':'.join(parts)+':'+m[2]+'}'
    t=re.sub(r'\\olref((?:\[[^]]*\])*)\{([^}]+)\}',ref,t)
    for key,word in words.items():t=re.sub(r'!!\^?a?\{'+key+r'\}s?',word,t)
    assert '!!' not in t and '\\oliflabeldef' not in t
    chunks.append(t)
newnotes=r'''\item फलन प्रकरणातील OLFUN-001 ते OLFUN-005 या पाच
गोठवलेल्या-स्रोत निष्कर्षांची दुरुस्ती संबंधित परिच्छेदांलगत स्वतंत्र
``स्रोतदुरुस्ती'' नोंदींमध्ये दिली आहे. मूळ इंग्रजी बाइट्स बदललेले नाहीत.
'''
notes=notes.replace(r'\end{enumerate}',newnotes+r'\end{enumerate}',1)
out=before+'\n'.join(chunks)+'\n'+notes
assert 'एकूण 23 विभाग' in out and out.count(r'\section{')==20
(B/'openlogic-mr-core.tex').write_text(out,encoding='utf-8',newline='\n')
manifest=[json.loads(x) for x in (P/'provenance/SOURCE_MANIFEST.jsonl').read_text(encoding='utf-8').splitlines()]
inputs=[]
for r in manifest[3:26]:
    p=P/'mr'/r['source_path'];inputs.append({'unit_id':r['unit_id'],'path':p.relative_to(P).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(B/'INPUTS.json').write_text(json.dumps({'input_units':inputs,'scope':'23 source units, 20 reader sections, three chapters','conditional_decisions':decisions,'source_issues':'Three Relations and three Functions editorial notes; aligned source is unchanged','notation':'Function macros copied from frozen upstream/open-logic-config.sty; composition applies first argument then second'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'prepared':'build/core/openlogic-mr-core.tex','units':len(inputs),'sections':20,'sha256':hashlib.sha256(out.encode()).hexdigest()}))
