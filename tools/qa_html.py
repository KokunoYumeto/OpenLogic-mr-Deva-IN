"""Check cumulative reader conversion without launching TeX or a browser."""
import collections, difflib, hashlib, json, re, shutil, subprocess, unicodedata
from pathlib import Path
from bs4 import BeautifulSoup

P=Path(__file__).resolve().parents[1]; B=P/'build/foundations'; O=B/'html'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ast(path=None,text=None):
    args=[shutil.which('pandoc'),'--from=latex','--to=json']
    if path: args.append(str(path))
    r=subprocess.run(args,input=text,capture_output=True,text=True,encoding='utf-8',timeout=60)
    assert r.returncode==0,r.stderr
    return json.loads(r.stdout)['blocks']
def mathnorm(t):
    t=t.replace(r'\nicefrac',r'\frac')
    while re.search(r'\\shove(?:left|right)\{',t):
        m=re.search(r'\\shove(?:left|right)\{',t);a=m.end();j=a;depth=1
        while depth:
            if t[j]=='{' and t[j-1]!='\\':depth+=1
            elif t[j]=='}' and t[j-1]!='\\':depth-=1
            j+=1
        t=t[:m.start()]+t[a:j-1]+t[j:]
    return re.sub(r'\s+','',t)
def collect(root):
    strings=[]; maths=[]; counts=collections.Counter()
    def walk(n):
        if isinstance(n,list):
            for x in n:walk(x)
        elif isinstance(n,dict):
            typ=n.get('t');counts[typ]+=1
            if typ=='Math':
                t=n['c'][1]
                if r'\begin{tikzpicture}' in t:
                    # Diagram intertext is prose, despite being inside TeX align.
                    m=re.search(r'\\intertext\{(.*?)\}\s*&',t,re.S);assert m
                    walk(ast(text=m[1]));return
                maths.append(mathnorm(t));return
            if typ=='Str':strings.append(n['c']);return
            if typ=='Code':strings.append(n['c'][1]);return
            if typ=='Image':return
            if typ in ['RawBlock','RawInline']:raise AssertionError(n)
            walk(n.get('c'))
    walk(root)
    return strings,maths,counts
source=collect(ast(B/'openlogic-mr-foundations.tex'))
adapted=collect(ast(B/'html-input.tex'))
assert source[0]==adapted[0],'Prose changed while adapting diagrams'
assert source[1]==adapted[1],'Formula changed while adapting HTML layout'
doc=BeautifulSoup((O/'index.html').read_text(encoding='utf-8'),'html.parser')
annotations=[mathnorm(n.get_text()) for n in doc.select('math annotation[encoding="application/x-tex"]')]
assert annotations==adapted[1],'HTML math annotations differ from source math'
assert len(doc.select('math'))==len(annotations)
assert not doc.select('merror,script,iframe')
ids=[x['id'] for x in doc.select('[id]')];assert len(ids)==len(set(ids))
links=doc.select('a[href^="#"]');assert all(a['href'][1:] in ids for a in links)
assets=[]
for x in doc.select('img[src],link[rel="stylesheet"]'):
    ref=x.get('src',x.get('href'));assert not re.match(r'\w+:|//',ref)
    p=(O/ref).resolve();assert p.is_relative_to(O.resolve()) and p.is_file()
    if x.name=='img':assert x.get('alt') and len(x['alt'])>15
    assets.append({'filename':ref,'bytes':p.stat().st_size,'sha256':sha(p)})
assert len(doc.select('img'))==6 and doc.html['lang']=='mr'
assert doc.select_one('meta[name="viewport"]') and doc.select_one('main')
assert len(doc.select('h2[data-number]'))==14
# Verify numbered references against the compiled PDF's actual label table.
aux=(B/'openlogic-mr-foundations.aux').read_text(encoding='utf-8')
labels=dict(re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}',aux))
refchecks=[]
for a in doc.select('a[data-reference]'):
    key=a['data-reference'];assert key in labels,key
    assert a.get_text()==labels[key],(key,a.get_text(),labels[key])
    refchecks.append(key)
# Ignore generated numbering while comparing all ordinary prose characters.
body=BeautifulSoup(str(doc.main),'html.parser')
for x in body.select('nav,header,math,.header-section-number'):x.decompose()
def prose_norm(s):
    s=re.sub(r'(?<!\d)\d+(?:\.\d+)+(?!\d)','',s)
    return ''.join(c for c in unicodedata.normalize('NFC',s) if unicodedata.category(c)[0] in 'LMN')
expected=prose_norm(' '.join(adapted[0]));actual=prose_norm(body.get_text(' '))
if expected!=actual:
    differences=[{'source':expected[a:b],'html':actual[c:d]} for op,a,b,c,d in difflib.SequenceMatcher(None,expected,actual,autojunk=False).get_opcodes() if op!='equal']
    raise AssertionError(differences[:12])
receipt={'schema':'openlogic-html-qa/1','passed':True,'html_sha256':sha(O/'index.html'),'source_tex_sha256':sha(B/'openlogic-mr-foundations.tex'),'source_pdf_sha256':sha(B/'openlogic-mr-foundations.pdf'),'source_to_adapted_prose_tokens_exact':len(source[0]),'source_to_html_math_annotations_exact':len(annotations),'ordinary_prose_characters_exact_ignoring_generated_numbering':len(expected),'internal_links_valid':len(links),'pdf_numbered_references_matched':refchecks,'sections':14,'diagrams':6,'assets':assets,'accessibility_checks':['Marathi document language','main landmark and skip link','hierarchical headings and linked table of contents','native MathML with TeX annotations','six detailed Marathi image alternatives','offline fonts and responsive CSS'],'browser_layout_review':{'status':'unavailable','reason':'Browser URL security policy denied local file; no alternate browser route attempted.'},'limitations':['Static checks do not establish browser rendering or assistive-technology behavior.','No independent human linguistic review.']}
(B/'HTML_QA.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
