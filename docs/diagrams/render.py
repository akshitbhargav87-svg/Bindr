from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import json,os,shutil
root=Path(__file__).resolve().parent
with sync_playwright() as p:
 candidates=[os.getenv('BINDR_CHROME_EXECUTABLE'),r'C:\Program Files\Google\Chrome\Application\chrome.exe',r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',shutil.which('google-chrome'),shutil.which('chromium')]
 chrome=next((v for v in candidates if v and Path(v).is_file()),None)
 if not chrome:raise RuntimeError('Set BINDR_CHROME_EXECUTABLE to the local Chrome/Chromium executable.')
 browser=p.chromium.launch(executable_path=chrome,headless=True)
 page=browser.new_page(viewport={'width':2560,'height':1440},device_scale_factor=1.5)
 page.goto((root/'print.html').as_uri());page.evaluate('async()=>{await document.fonts.ready;return true;}')
 issues=page.evaluate('''()=>Array.from(document.querySelectorAll('text')).map(t=>({text:t.textContent,width:t.getBBox().width,max:+t.dataset.max})).filter(t=>t.width>t.max+2)''')
 print(json.dumps(issues,ensure_ascii=True))
 if issues:raise RuntimeError('Diagram labels exceed their declared width. Shorten them before exporting.')
 for i,name in enumerate(['01-bindr-customer-journey','02-bindr-technical-architecture']):
  page.locator('.sheet').nth(i).screenshot(path=str(root/(name+'.png')))
  im=Image.open(root/(name+'.png'));im.thumbnail((1280,720));im.save(root/(name+'-preview.png'))
 page.pdf(path=str(root/'Bindr-flowcharts.pdf'),width='2560px',height='1440px',print_background=True,prefer_css_page_size=True)
 shutil.copyfile(root/'Bindr-flowcharts.pdf',root/'Bindr-flowcharts-16x9.pdf')
 browser.close()
