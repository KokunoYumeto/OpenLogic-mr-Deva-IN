"""Render the generated SVG files in Chromium, independently of PDF clipping."""
import hashlib,json,math
from pathlib import Path
from io import BytesIO
from xml.etree import ElementTree as ET
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/full';OUT=BUILD/'diagram-svg-visual-current';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=BUILD/'HTML_DIAGRAM_RECEIPT.json';data=json.loads(receipt.read_text(encoding='utf-8'));rows=[]
with sync_playwright() as play:
 browser=play.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
 context=browser.new_context(viewport={'width':1200,'height':1200},device_scale_factor=2)
 page=context.new_page()
 for row in data['assets']:
  path=BUILD/'html/assets'/row['filename'];assert sha(path)==row['sha256']
  svg=ET.parse(path).getroot();_,_,w,h=map(float,svg.attrib['viewBox'].split())
  page.goto(path.as_uri(),wait_until='load')
  page.evaluate('(dims)=>{const s=document.documentElement;s.style.width=dims[0]+"px";s.style.height=dims[1]+"px";s.style.background="white"}',[w*2,h*2])
  target=OUT/(row['name']+'.png');page.locator('svg').screenshot(path=str(target),timeout=30000)
  rows.append({'name':row['name'],'source_svg_sha256':sha(path),'render_sha256':sha(target),'filename':target.name})
 browser.close()
sheets=[]
for start in range(0,len(rows),12):
 sheet=Image.new('RGB',(1100,1500),'#dddddd');draw=ImageDraw.Draw(sheet)
 for i,row in enumerate(rows[start:start+12]):
  crop=Image.open(OUT/row['filename']).convert('RGB');crop.thumbnail((520,215))
  x,y=(i%2)*550+15,(i//2)*250+25;sheet.paste(crop,(x+(520-crop.width)//2,y));draw.text((x,y-18),row['name']+' / actual SVG',fill='black')
 target=OUT/f'svg-sheet-{start//12+1}.png';sheet.save(target);sheets.append({'filename':target.name,'sha256':sha(target),'diagrams':[r['name'] for r in rows[start:start+12]]})
report={'schema':'openlogic-generated-svg-visual-review/1','status':'rendered_awaiting_inspection','diagram_receipt_sha256':sha(receipt),'assets':rows,'sheets':sheets}
(OUT/'SVG_VISUAL_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'assets':len(rows),'sheets':len(sheets)}))
