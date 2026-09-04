"""Build offline semantic HTML/MathML from the cumulative TeX reader, no TeX launch."""
import re,json,hashlib,subprocess,shutil,html
from pathlib import Path
import fitz
from bs4 import BeautifulSoup
P=Path(__file__).resolve().parents[1];B=P/'build/foundations';O=B/'html';A=O/'assets';A.mkdir(parents=True,exist_ok=True)
pdf=B/'openlogic-mr-foundations.pdf';receipt=json.loads((B/'TEX_SUCCESS_RECEIPT.json').read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(pdf)==receipt['pdf']['sha256'] and sha(B/'openlogic-mr-foundations.tex')==receipt['texInputSha256']
d=fitz.open(pdf);assert len(d)==22,'Reinspect diagram coordinates when pagination changes'
specs=[('union',7,(176,131,417,328),'दोन्ही संचांतील सर्व घटकांचा संयोग; दोन्ही आकृत्यांचा संपूर्ण भाग चिन्हांकित.'),('intersection',7,(176,485,417,682),'दोन्ही संचांचा छेद; फक्त सामाईक भाग चिन्हांकित.'),('difference',9,(176,68,417,264),'A मधील पण B मध्ये नसलेला भाग; सामाईक भाग वगळलेला.'),('graph-four',18,(227,207,368,305),'शिखरे 1, 2, 3, 4. दिशित कडा 1 ते 1, 1 ते 2, 1 ते 3, 2 ते 3. शिखर 4 एकाकी.'),('graph-three',18,(227,340,312,439),'शिखरे 1, 2, 3. दिशित कडा 1 ते 1, 1 ते 2, 1 ते 3, 2 ते 3. पहिल्या आलेखातील एकाकी शिखर 4 येथे नाही.'),('tree',18,(241,662,354,776),'मूळ r खाली आहे. r ची अपत्ये a आणि b. a ची अपत्ये c, d आणि e. कडा वरच्या दिशेने वाचल्यास पूर्वज संबंध मिळतो.')]
assets=[]
for name,page,rect,alt in specs:
    x0,y0,x1,y1=rect;svg=d[page-1].get_svg_image(text_as_path=True)
    svg=re.sub(r'<svg\b[^>]*>',f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{(x1-x0)*2}" height="{(y1-y0)*2}" viewBox="{x0} {y0} {x1-x0} {y1-y0}" role="img" aria-labelledby="desc" style="overflow:hidden"><title id="desc">{html.escape(alt)}</title>',svg,count=1)
    dest=A/(name+'.svg');dest.write_text(svg,encoding='utf-8',newline='\n');assets.append(dict(filename='assets/'+dest.name,sha256=sha(dest),source_pdf_page=page,source_pdf_crop=rect,alt=alt))
t=(B/'openlogic-mr-foundations.tex').read_text(encoding='utf-8')
for name in ['union','intersection','difference']:
    needle=r'\olasset{assets/diagrams/'+name+'.tikz}'
    assert t.count(needle)==1,needle
    t=t.replace(needle,r'\includegraphics{assets/'+name+'.svg}')
pattern=r'\\begin\{align\*\}\s*&\s*\\begin\{tikzpicture\}.*?\\end\{align\*\}'
m=re.search(pattern,t,re.S);assert m
g=m.group();im=re.search(r'\\intertext\{(.*?)\}\s*&',g,re.S);assert im
replacement=r'\begin{center}\includegraphics{assets/graph-four.svg}\end{center}'+'\n\n'+im[1]+'\n\n'+r'\begin{center}\includegraphics{assets/graph-three.svg}\end{center}'
t=t[:m.start()]+replacement+t[m.end():]
t,n=re.subn(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',lambda m:r'\includegraphics{assets/tree.svg}',t,flags=re.S);assert n==1
assert '\\begin{tikzpicture}' not in t
# HTML math layout uses equivalent fraction and grouping forms supported by MathML.
t=t.replace(r'\nicefrac',r'\frac')
while re.search(r'\\shove(?:left|right)\{',t):
    m=re.search(r'\\shove(?:left|right)\{',t);a=m.end();j=a;depth=1
    while depth:
        if t[j]=='{' and t[j-1]!='\\':depth+=1
        elif t[j]=='}' and t[j-1]!='\\':depth-=1
        j+=1
    t=t[:m.start()]+t[a:j-1]+t[j:]
# Retain prose/math order; only swap diagram representations, not content.
(B/'html-input.tex').write_text(t,encoding='utf-8',newline='\n')
fontdir=O/'fonts';fontdir.mkdir(exist_ok=True)
for name in ['OLMarathiSerif-Regular.ttf','OLMarathiSerif-Bold.ttf','OFL.txt']:shutil.copyfile(P/'fonts'/name,fontdir/name)
css='''@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Regular.ttf)}@font-face{font-family:OLMarathi;src:url(fonts/OLMarathiSerif-Bold.ttf);font-weight:bold}*{box-sizing:border-box}html{scroll-behavior:smooth}body{font-family:OLMarathi,serif;line-height:1.75;margin:0 auto;padding:2rem 1.25rem 5rem;max-width:58rem;color:#202124;background:#fff}h1,h2,h3{line-height:1.4;scroll-margin-top:1rem}h1{margin-top:3rem;border-bottom:2px solid #a81c21;padding-bottom:.6rem}a{color:#064c8c}a:focus-visible{outline:3px solid #a81c21;outline-offset:3px}img{max-width:100%;height:auto;display:block;margin:1rem auto}figure{margin:2rem 0}figcaption{font-size:.94rem;text-align:center}.math.display{display:block;overflow-x:auto;padding:.7rem 0}math{font-size:1.05em}.proof{border-left:3px solid #ddd;padding-left:1rem}.defn,.ex,.prop,.thm,.prob{margin:1.2rem 0}.titlepage{border-bottom:1px solid #bbb;padding-bottom:1.5rem}#TOC{background:#f3f5f7;padding:1rem 1.5rem;border-radius:.3rem}code{overflow-wrap:anywhere}p{orphans:3;widows:3}@media(max-width:600px){body{font-size:1.06rem;padding:.9rem}h1{font-size:1.7rem}h2{font-size:1.35rem}}@media print{body{max-width:none}#TOC{page-break-after:always}a{color:inherit}}'''
css+='\n.math-display{max-width:100%;overflow-x:auto;margin:1rem 0;padding:.5rem 0}.math-display math{margin:0 auto}figure img{width:auto}\n'
(O/'reader.css').write_text(css,encoding='utf-8')
pandoc=shutil.which('pandoc');assert pandoc
args=[pandoc,str(B/'html-input.tex'),'--from=latex','--to=html5','--standalone','--mathml','--toc','--number-sections','--metadata=lang:mr','--metadata=title:मुक्त तर्कशास्त्र — संच आणि संबंध','--metadata=toc-title:अनुक्रमणिका','--css=reader.css','--output='+str(O/'index.html')]
r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=90)
(B/'HTML_BUILD_LOG.txt').write_text(r.stderr,encoding='utf-8');assert r.returncode==0,r.stderr
doc=(O/'index.html').read_text(encoding='utf-8')
for a in assets:
    pattern=r'(<img\b[^>]*src="'+re.escape(a['filename'])+r'"[^>]*)(/?>)'
    def label(m):
        tag=re.sub(r'\s+alt="[^"]*"','',m[1]);return tag+' alt="'+html.escape(a['alt'],quote=True)+'" loading="lazy"'+m[2]
    doc,n=re.subn(pattern,label,doc);assert n==1,(a['filename'],n)
doc=doc.replace('<body>','<body>\n<a href="#main-content">मुख्य मजकुराकडे जा</a>\n<main id="main-content">',1).replace('</body>','</main>\n</body>')
# Pandoc shares theorem counters across a chapter. Match the PDF's per-section
# theorem numbering, retaining the chapter-wide exercise and figure counters.
soup=BeautifulSoup(doc,'html.parser'); section=None; counter=0; numbered={}
for node in soup.select('h1,h2,div.defn,div.ex,div.prop,div.thm'):
    if node.name in ['h1','h2']:
        if node.name=='h2' and node.get('data-number'):
            section=node['data-number'];counter=0
        elif node.name=='h1':section=None
        continue
    assert section,node
    counter+=1; number=f'{section}.{counter}'; head=node.find('strong')
    assert head and re.search(r'\d+\.\d+',head.get_text()),str(node)[:100]
    head.string=re.sub(r'\d+\.\d+',number,head.get_text(),count=1)
    if node.get('id'):numbered[node['id']]=number
for link in soup.select('a[data-reference]'):
    if link['data-reference'] in numbered:link.string=numbered[link['data-reference']]
for formula in soup.select('math[display="block"]'):
    wrapper=soup.new_tag('div',attrs={'class':'math-display','tabindex':'0','role':'region','aria-label':'गणिती सूत्र; रुंद सूत्र आडवे सरकवता येते'})
    formula.wrap(wrapper)
doc=str(soup)
(O/'index.html').write_text(doc,encoding='utf-8',newline='\n')
report={'schema':'openlogic-html-build/1','source_tex_sha256':sha(B/'openlogic-mr-foundations.tex'),'source_pdf_sha256':sha(pdf),'html_sha256':sha(O/'index.html'),'html_bytes':(O/'index.html').stat().st_size,'diagram_assets':assets,'mathml_count':doc.count('<math '),'warnings':r.stderr,'validation':'Build complete; browser/math/coverage verification still required','network_dependencies':[]}
(B/'HTML_BUILD_RECEIPT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'html_bytes':report['html_bytes'],'mathml_count':report['mathml_count'],'diagrams':len(assets),'warnings':r.stderr},ensure_ascii=False))
