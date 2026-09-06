"""Prepare a complete chapter build from the aligned editable translation.
No TeX process is launched here. All TeX must use build_guarded.ps1.
"""
import re,json,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
P=Path(__file__).resolve().parents[1]
B=P/'build'/'sets';B.mkdir(parents=True,exist_ok=True)
for suffix,weight in [('Regular',400),('Bold',700)]:
    dest=P/'fonts'/f'OLMarathiSerif-{suffix}.ttf'
    if not dest.exists():
        font=instantiateVariableFont(TTFont(P/'fonts'/'NotoSerifDevanagari.ttf'),{'wght':weight,'wdth':100},inplace=False)
        for rec in font['name'].names:
            names={1:'OpenLogic Marathi Serif',2:suffix,4:'OpenLogic Marathi Serif '+suffix,6:'OLMarathiSerif-'+suffix,16:'OpenLogic Marathi Serif',17:suffix}
            if rec.nameID in names:rec.string=names[rec.nameID].encode(rec.getEncoding())
        font.save(dest)
def balanced(t,start):
    assert t[start]=='{';level=1;i=start+1
    while level:
        assert i<len(t)
        if t[i]=='{' and t[i-1]!='\\':level+=1
        elif t[i]=='}' and t[i-1]!='\\':level-=1
        i+=1
    return t[start+1:i-1],i
def remove_external_conditionals(t):
    pos=0
    while '\\oliflabeldef' in t[pos:]:
        i=t.index('\\oliflabeldef',pos);j=i+len('\\oliflabeldef');args=[]
        for k in range(3):
            while t[j].isspace():j+=1
            v,j=balanced(t,j);args.append(v)
        # In this isolated chapter these exact external destinations are absent.
        assert args[0] in ('sfr:arith:real:realline','cumul:::part')
        t=t[:i]+args[2]+t[j:];pos=i
    return t
sources=['basics','subsets','important-sets','unions-and-intersections','pairs-and-products','russells-paradox']
chunks=[];receipts=[]
for name in sources:
    p=P/'mr'/'content'/'sets-functions-relations'/'sets'/(name+'.tex')
    t=p.read_text(encoding='utf-8')
    receipts.append({'path':str(p.relative_to(P)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    t=re.sub(r'(?m)^%.*$','',t)
    t=re.sub(r'\\documentclass[^\n]*\n','',t)
    t=t.replace('\\begin{document}','').replace('\\end{document}','')
    m=re.search(r'\\olfileid\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}',t);assert m
    prefix=':'.join(m.groups());t=t[:m.start()]+t[m.end():]
    t=remove_external_conditionals(t)
    t=re.sub(r'\\olsection\{([^}]+)\}',lambda m:'\\section{'+m[1]+'}\\label{'+prefix+':sec}',t)
    t=re.sub(r'\\ollabel\{([^}]+)\}',lambda m:'\\label{'+prefix+':'+m[1]+'}',t)
    def ref(m):
        groups=re.findall(r'\[([^]]*)\]',m[1]);parts=prefix.split(':')
        for i,v in enumerate(groups):parts[i]=v
        return '\\ref{'+':'.join(parts)+':'+m[2]+'}'
    t=re.sub(r'\\olref((?:\[[^]]*\])*)\{([^}]+)\}',ref,t)
    t=re.sub(r'\\begin\{tagblock\}\{[^}]+\}','',t).replace('\\end{tagblock}','')
    t=re.sub(r'!!\^?a?\{element\}s?','घटक',t)
    assert '!!' not in t
    chunks.append(t)
preamble=r'''\documentclass[11pt,a4paper,openany]{book}
\usepackage[margin=25mm]{geometry}
\usepackage{fontspec}
\setmainfont{OLMarathiSerif-Regular.ttf}[Path=../../fonts/,Script=Devanagari,Language=Marathi,BoldFont=OLMarathiSerif-Bold.ttf,ItalicFont=OLMarathiSerif-Regular.ttf]
\setsansfont{OLMarathiSerif-Regular.ttf}[Path=../../fonts/,Script=Devanagari,Language=Marathi,BoldFont=OLMarathiSerif-Bold.ttf]
\usepackage{amsmath,amssymb,amsthm,nicefrac,graphicx,tikz}
\usepackage{flafter}
\usepackage[unicode,colorlinks=true,linkcolor=blue,urlcolor=blue]{hyperref}
\usepackage{microtype}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.45em}
\linespread{1.18}
\setlength{\emergencystretch}{2em}
\renewcommand{\contentsname}{अनुक्रमणिका}
\renewcommand{\chaptername}{प्रकरण}
\renewcommand{\figurename}{आकृती}
\renewcommand{\proofname}{सिद्धता}
\theoremstyle{definition}
\newtheorem{defn}{व्याख्या}[section]
\newtheorem{ex}[defn]{उदाहरण}
\newtheorem{prop}[defn]{प्रतिज्ञा}
\newtheorem{thm}[defn]{प्रमेय}
\newtheorem{prob}{सराव}[chapter]
\newenvironment{explain}{}{}
\newenvironment{digress}{\par\smallskip}{\par\smallskip}
\newcommand{\Setabs}[2]{\{#1:#2\}}
\newcommand{\Pow}[1]{\wp(#1)}
\newcommand{\tuple}[1]{\langle #1\rangle}
\newcommand{\Nat}{\mathbb{N}}
\newcommand{\Int}{\mathbb{Z}}
\newcommand{\Rat}{\mathbb{Q}}
\newcommand{\Real}{\mathbb{R}}
\newcommand{\PosInt}{\mathbb{Z}^{+}}
\newcommand{\Bin}{\mathbb{B}}
\newcommand{\len}[1]{\mathrm{len}(#1)}
\newcommand{\lif}{\mathbin{\to}}
\colorlet{oldiagcolorA}{black}
\colorlet{oldiagcolorB}{gray}
\definecolor{oldiagcolorC}{HTML}{a81c21}
\newcommand{\olasset}[1]{\centering\resizebox{0.52\textwidth}{!}{\input{../../upstream/#1}}}
\hypersetup{pdftitle={मुक्त तर्कशास्त्र: संच},pdfauthor={Open Logic Project; Marathi machine translation by Codex}}
\begin{document}
\begin{titlepage}
\vspace*{2cm}
{\Huge\bfseries मुक्त तर्कशास्त्र\par}
\vspace{1cm}
{\LARGE संच\par}
\vspace{1cm}
{\large मराठी आवृत्ती · संपूर्ण संच प्रकरण\par}
\vfill
मूळ ग्रंथ: Open Logic Project, \textit{The Open Logic Text}.\par
या आवृत्तीची तांत्रिक स्रोत-ओळख प्रकल्पाच्या नोंदींत दिली आहे.\par
हे प्रकाशन संच प्रकरणापुरते आहे: मूळ 722 विभागांपैकी OLP-0004 ते OLP-0010.
संपूर्ण मराठी ग्रंथाचे काम सुरू आहे.\par
Codex कडून यंत्रानुवाद; स्रोताशी तुलना आणि यांत्रिक तपासण्या केल्या आहेत.
स्वतंत्र मानवी संपादनाचा दावा केलेला नाही. काही तांत्रिक संज्ञा तात्पुरत्या आहेत.\par
मूळ मजकूर आणि हे रूपांतर: Creative Commons Attribution 4.0.
मूळ घटकांचे स्वतंत्र परवाने लागू राहतात.\par
\url{https://github.com/OpenLogicProject/OpenLogic}\par
\url{https://github.com/KokunoYumeto/OpenLogic-translations}
\end{titlepage}
\tableofcontents
\chapter{संच}
'''
(B/'openlogic-mr-sets.tex').write_text(preamble+'\n'.join(chunks)+'\n\\end{document}\n',encoding='utf-8')
(B/'INPUTS.json').write_text(json.dumps({'input_units':receipts,'adapter_scope':'chapter only; source-aligned TeX retained separately; all novice/math/compsci blocks included; two upstream external-label conditionals take original false branch','font':'portable renamed static derivative of pinned Noto Serif Devanagari; SIL OFL'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'prepared':'build/sets/openlogic-mr-sets.tex','source_sections':len(sources)}))
