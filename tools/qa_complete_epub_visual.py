"""Render selected documents extracted from the actual complete EPUB bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def resolve(value):
    path=(ROOT/value).resolve()
    path.relative_to(ROOT)
    return path

parser=argparse.ArgumentParser()
parser.add_argument('config',type=Path)
args=parser.parse_args()
config=json.loads(args.config.resolve().read_text(encoding='utf-8-sig'))
epub=resolve(config['output_epub'])
build=resolve(config['build_root'])
extracted=build/'actual-epub-visual-extract'
if extracted.exists():
    import build_epub as base
    base.safe_clear(extracted,build)
extracted.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(epub) as archive:
    for name in archive.namelist():
        part=PurePosixPath(name)
        assert not part.is_absolute() and '..' not in part.parts and '\\' not in name
        target=(extracted/Path(*part.parts)).resolve()
        target.relative_to(extracted.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(archive.read(name))
sample_specs=[
    ('cover','OEBPS/content-000.xhtml',1100,800,None),
    ('aristotle','OEBPS/content-030.xhtml',760,960,
     'कॅटेगरीज' if 'v1.1' in config['release'] else 'ॲरिस्टॉटल'),
    ('math-glyph','OEBPS/content-066.xhtml',760,640,'mglyph'),
    ('calculus','OEBPS/content-090.xhtml',760,960,'अवकलन'),
    ('greek','OEBPS/content-092.xhtml',420,860,None),
]
rows=[]
assert CHROME.is_file()
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=str(CHROME),headless=True)
    for label,name,width,height,selector in sample_specs:
        page=browser.new_page(viewport={'width':width,'height':height},locale='mr-IN')
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto((extracted/name).as_uri(),wait_until='load',timeout=90000)
        page.evaluate('document.fonts.ready')
        if selector=='mglyph':
            target=page.locator('mglyph').first
            assert target.count()==1
            target.scroll_into_view_if_needed(timeout=30000)
        elif selector:
            target=page.get_by_text(selector,exact=False).first
            assert target.count()==1
            target.scroll_into_view_if_needed(timeout=30000)
        page.wait_for_timeout(1200)
        screenshot=build/f'EPUB_VISUAL_{label.upper()}_{width}.png'
        page.screenshot(path=str(screenshot))
        measures=page.evaluate('''() => ({
          scroll_width:document.documentElement.scrollWidth,
          client_width:document.documentElement.clientWidth,
          font_status:document.fonts.status,
          image_failures:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).length,
          mathml_count:document.querySelectorAll('math').length,
          visible_glyphs:[...document.querySelectorAll('mglyph')].filter(e=>e.getBoundingClientRect().width>0).length,
          language:document.documentElement.getAttribute('lang')
        })''')
        assert measures['scroll_width']<=measures['client_width']+1
        assert measures['font_status']=='loaded' and measures['image_failures']==0
        assert measures['language']=='mr-Deva-IN' and not errors
        rows.append({'label':label,'xhtml':name,'viewport':[width,height],
                     'xhtml_sha256':sha(extracted/name),'screenshot':screenshot.name,
                     'screenshot_sha256':sha(screenshot),'measures':measures,'page_errors':errors})
        page.close()
    browser.close()
report={'schema':'openlogic-mr-complete-epub-visual/1','status':'rendered-pending-actual-image-inspection',
        'epub_sha256':sha(epub),'samples':rows,
        'scope_mr':'EPUB मधून काढलेल्या प्रत्यक्ष XHTML वर पाच निवडक desktop/narrow दृश्ये; सूत्रचिन्ह, इतिहास, अवकलन, ग्रीक वर्णमाला व अनुक्रमणिका.',
        'limitation_mr':'संपूर्ण EPUB च्या प्रत्येक वाचन-भागाची दृश्यतपासणी या नमुन्यांमधून सिद्ध होत नाही.'}
out=build/'EPUB_VISUAL_QA.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'status':report['status'],'epub_sha256':report['epub_sha256'],'samples':len(rows),
                  'screenshots':[r['screenshot'] for r in rows]},ensure_ascii=False))
