from pathlib import Path
import base64, json, html, random, math

ROOT=Path(__file__).resolve().parent
W,H=2560,1440
INK='#263238';MUTED='#536174';INDIGO='#3D4DD6'
BLUE='#D8EEFF';PURPLE='#E9E5FF';GREEN='#DDF4E4';YELLOW='#FFF0BE';PINK='#FADCE9'
def uri(data,mime='image/svg+xml'):return 'data:'+mime+';base64,'+base64.b64encode(data).decode()
FONT=uri((ROOT/'assets/Excalifont.woff2').read_bytes(),'font/woff2')
ICONS={
'user':'<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',
'upload':'<path d="M12 16V3m-5 5 5-5 5 5M3 15v6h18v-6"/>',
'spark':'<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/>',
'check':'<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m7 12 3 3 7-7"/>',
'record':'<path d="M5 2h10l5 5v15H5ZM14 2v6h6M8 12h9M8 17h6"/>',
'history':'<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v6l4 2"/>',
'clock':'<circle cx="12" cy="12" r="10"/><path d="M12 5v7l5 3"/>',
'receipt':'<path d="M5 2h14v20l-3-2-4 2-4-2-3 2ZM8 7h8M8 12h8M8 16h4"/>',
'heart':'<path d="M20 4c-3-3-7-1-8 2-1-3-5-5-8-2-5 5 1 10 8 17 7-7 13-12 8-17Z"/>',
'edit':'<path d="m4 16 12-12 4 4L8 20l-5 1ZM14 6l4 4M3 3h7M3 3v8"/>',
'export':'<path d="M14 3H3v18h18V10M12 12 22 2M14 2h8v8"/>',
'shield':'<path d="m12 2 9 4v6c0 5-5 8-9 10-4-2-9-5-9-10V6ZM7 12l3 3 7-7"/>',
'folder':'<path d="M2 7V4h8l3 3h9v14H2ZM2 10h20"/>',
'branch':'<circle cx="6" cy="4" r="2"/><circle cx="18" cy="4" r="2"/><circle cx="6" cy="20" r="2"/><path d="M6 6v12M18 6c0 7-12 3-12 9"/>',
'mail':'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 5 10 8L22 5"/>'}

class Drawing:
 def __init__(self,title):
  self.title=title;self.svg=[];self.elements=[];self.files={};self.n=0
  self.base('rectangle',0,0,W,H,backgroundColor='white',strokeColor='transparent',locked=True,roughness=0,roundness=None)
 def base(self,typ,x,y,w,h,**kw):
  self.n+=1
  e=dict(id=f'b{self.n}',type=typ,x=x,y=y,width=w,height=h,angle=0,strokeColor=INK,backgroundColor='transparent',fillStyle='solid',strokeWidth=2,strokeStyle='solid',roughness=1,opacity=100,groupIds=[],frameId=None,roundness={'type':3},seed=self.n*997,version=1,versionNonce=self.n*29,isDeleted=False,boundElements=None,updated=1,link=None,locked=False)
  e.update(kw);self.elements.append(e);return e
 def box(self,x,y,w,h,fill='white',dash=False):
  r=random.Random(self.n+32);j=lambda:r.uniform(-2,2)
  self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fill}" stroke="{INK}" stroke-width="2.5" '+('stroke-dasharray="14 12"' if dash else '')+'/>')
  if not dash:self.svg.append(f'<path d="M{x+16} {y+2+j()} Q{x+w/2} {y+j()} {x+w-15} {y+1+j()} Q{x+w+1} {y+4} {x+w+1} {y+20} L{x+w+j()} {y+h-15} Q{x+w} {y+h+2} {x+w-16} {y+h+1} L{x+18} {y+h+j()} Q{x-1} {y+h} {x-1} {y+h-18} L{x+j()} {y+18}" fill="none" stroke="{INK}" stroke-width="1" opacity=".45"/>')
  return self.base('rectangle',x,y,w,h,backgroundColor=fill,strokeStyle='dashed' if dash else 'solid')
 def text(self,x,y,lines,size=28,color=INK,width=600):
  if isinstance(lines,str):lines=lines.split('\n')
  for i,line in enumerate(lines):
   yy=y+i*size*1.36
   self.svg.append(f'<text data-max="{width}" x="{x}" y="{yy+size}" font-size="{size}" font-weight="{700 if size>=34 else 400}" fill="{color}">{html.escape(line)}</text>')
  content='\n'.join(lines)
  return self.base('text',x,y,width,len(lines)*size*1.36,strokeColor=color,backgroundColor='transparent',fontSize=size,fontFamily=5,text=content,originalText=content,textAlign='left',verticalAlign='top',containerId=None,autoResize=True,lineHeight=1.36,roughness=0)
 def image(self,x,y,w,h,path=None,data=None):
  raw=data if data is not None else Path(path).read_bytes();value=uri(raw)
  self.svg.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="{value}"/>')
  fid=f'asset{self.n+1}';self.files[fid]=dict(id=fid,dataURL=value,mimeType='image/svg+xml',created=1,lastRetrieved=1)
  self.base('image',x,y,w,h,fileId=fid,status='saved',scale=[1,1],crop=None,strokeColor='transparent',roundness=None)
 def icon(self,name,x,y,size=44,color=INDIGO):
  content=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
  self.image(x,y,size,size,data=content.encode())
 def logo(self,name,x,y,size=56):self.image(x,y,size,size,ROOT/'assets'/f'{name}.svg')
 def arrow(self,points,label=None,lx=None,ly=None,dash=False,color=INK):
  p=' '.join(f'{x},{y}' for x,y in points)
  self.svg.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" marker-end="url(#arrow)" '+('stroke-dasharray="10 10"' if dash else '')+'/>')
  x,y=points[0];self.base('arrow',x,y,max(abs(xx-x) for xx,yy in points),max(abs(yy-y) for xx,yy in points),points=[[xx-x,yy-y] for xx,yy in points],startBinding=None,endBinding=None,startArrowhead=None,endArrowhead='arrow',strokeColor=color,strokeStyle='dashed' if dash else 'solid',roundness={'type':2})
  if label:
   self.svg.append(f'<rect x="{lx-8}" y="{ly-2}" width="{len(label)*13+20}" height="38" fill="white"/>');self.text(lx,ly,label,24,width=600)
 def node(self,x,y,w,h,title,body,icon='record',fill=BLUE,num=None,dash=False):
  start=len(self.elements)
  self.box(x,y,w,h,fill,dash);self.icon(icon,x+24,y+25)
  self.text(x+82,y+25,title,36,width=w-104)
  if num:self.text(x+w-60,y+h-49,num,24,color=MUTED,width=45)
  self.text(x+26,y+88,body,32,width=w-52)
  group=f'node-{self.n}'
  for e in self.elements[start:]:e['groupIds']=[group]
 def header(self,title,subtitle,number):
  self.text(60,30,title,64,width=2110);self.text(62,112,subtitle,30,color=MUTED,width=2150)
  self.image(2280,40,46,60,ROOT/'assets/bindr.svg');self.text(2350,46,'bindr',38,width=140)
  self.text(2350,110,number,24,color=INDIGO,width=140)
 def finish(self,name):
  svg=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><title>{html.escape(self.title)}</title><defs><style>@font-face{{font-family:Excalifont;src:url({FONT}) format("woff2");}}text{{font-family:Excalifont,"Comic Sans MS",sans-serif;}}</style><marker id="arrow" viewBox="0 0 16 16" refX="13" refY="8" markerWidth="12" markerHeight="12" orient="auto"><path d="M2 2 13 8 2 14" fill="none" stroke="{INK}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></marker></defs><rect width="{W}" height="{H}" fill="white"/>'+''.join(self.svg)+'</svg>'
  (ROOT/f'{name}.svg').write_text(svg,encoding='utf-8')
  scene=dict(type='excalidraw',version=2,source='https://excalidraw.com',elements=self.elements,appState={'viewBackgroundColor':'#ffffff','gridSize':None},files=self.files)
  (ROOT/f'{name}.excalidraw').write_text(json.dumps(scene,ensure_ascii=False),encoding='utf-8')
  return svg

d=Drawing('Bindr — customer journey, updated 15 November 2026')
d.header('A promise. A deadline. A clear record.','From scattered messages to a reviewed record','USER')

d.box(60,180,2440,170,'white',True)
d.icon('user',90,215,60);d.text(174,204,'Aarav: Rs 4,999 refund',38,width=680)
d.text(174,264,'Returned headphones. Still waiting.',30,width=680)
d.icon('clock',930,215,60);d.text(1014,204,'Dates change. Proof scatters.',36,width=690)
d.text(1014,264,'What was promised? What is still owed?',30,width=690)
d.icon('record',1790,215,60);d.text(1874,204,'Bindr keeps it together.',36,width=590)
d.text(1874,264,'Account + proof + outcome.',30,width=590)

xs=[60,570,1080,1590,2100]
for i,(title,lines,icon,fill) in enumerate([
 ('Sign in',['Google / email','Optional MFA'],'user',BLUE),
 ('Add proof',['Text / image / PDF','Original + source date'],'upload',BLUE),
 ('AI suggests',['OCR + exact quotes','Review every promise'],'spark',PURPLE),
 ('You confirm',['Edit terms and dates','Choose what to track'],'check',YELLOW),
 ('Case record',['Proof + case history','Earlier versions stay'],'record',GREEN)]):
 d.node(xs[i],430,400,210,title,lines,icon,fill)
 if i<4:d.arrow([(xs[i]+410,530),(xs[i+1]-14,530)])

d.arrow([(1280,650),(1280,718),(1790,718),(1790,650)],dash=True)
d.text(1310,675,'Unclear? Retry / manual (v2)',27,width=480)

d.arrow([(2300,650),(2300,785),(335,785),(335,840)])
for xx in [965,1595,2225]:d.arrow([(xx,785),(xx,840)])
for x,title,lines,icon,fill,dashed in [
 (60,'Promise changes',['Compare → confirm revision','Both dates + sources stay'],'branch',PURPLE,False),
 (690,'Part received (v2)',['Rs 1,000 in → Rs 3,999 left','Each promise has a balance'],'receipt',YELLOW,True),
 (1320,'Ask this case (v2)',['Exact source + citation','Unclear? It abstains.'],'spark',BLUE,True),
 (1950,'Prepare a follow-up',['Draft from confirmed facts','You review the wording'],'edit',PURPLE,False)]:
 d.node(x,850,550,210,title,lines,icon,fill,dash=dashed)

d.arrow([(965,1070),(965,1100),(385,1100),(385,1170)])
d.arrow([(2225,1070),(2225,1130),(1285,1130),(1285,1170)])
d.arrow([(2508,535),(2530,535),(2530,1250),(2510,1250)],dash=True)
d.node(60,1180,650,150,'All received',['You confirm → Resolved'],'check',GREEN)
d.node(960,1180,650,150,'Private exports (v2)',['PDF / JSON / originals ZIP'],'export',BLUE,dash=True)
d.node(1860,1180,640,150,'Your controls (v2)',['Review deletion + cleanup'],'shield',PINK,dash=True)
d.text(65,1373,'Dashed = v2 tools; original-screen integration pending. Live AI/account checks open. Fictional example. Nothing auto-sent.',25,color=MUTED,width=2400)
user=d.finish('01-bindr-customer-journey')

d=Drawing('Bindr — technical architecture, updated 15 November 2026')
d.header('Behind the record.','The current stack, data boundaries and release work','TECH')

# Deployment path uses the actual Google Cloud target, not the old Render option.
d.box(60,185,2440,110,'#F6F7FB',True)
d.logo('github',90,208,54);d.text(163,212,'GitHub',34,width=230)
d.arrow([(400,240),(535,240)])
d.logo('docker',570,208,60);d.text(655,212,'Cloud Build + Docker',34,width=490)
d.arrow([(1160,240),(1295,240)])
d.logo('googlecloud',1330,208,60);d.text(1415,212,'Cloud Run: frontend + API',34,width=760)
d.text(2200,216,'HTTPS',30,color=INDIGO,width=230)

for x,w,fill in [(60,620,BLUE),(850,750,PURPLE),(1770,730,GREEN)]:d.box(x,350,w,360,fill)
for name,x,size in [('react',90,54),('typescript',165,48),('vitejs',235,48),('tailwindcss',305,48)]:d.logo(name,x,373,size)
d.text(90,445,'React + TypeScript',43,width=550)
d.text(90,520,['Original UI (source)','v1 main / v2 separate tools','Account-bound draft recovery'],32,width=555)
d.logo('fastapi',880,373,54);d.logo('python',960,373,54);d.logo('firebase',1040,373,54)
d.text(880,445,'FastAPI: v1 + v2',44,width=680)
d.text(880,520,['Firebase + revocable SQL sessions','CSRF / versions / replay keys','Human review → atomic write'],32,width=680)
d.icon('spark',1800,373,54)
d.text(1800,445,'AI + documents',44,width=660)
d.text(1800,520,['RapidOCR + structured Meta','Quotes + bounded proposals','Ask-case: cite or abstain'],32,width=660)
d.arrow([(690,500),(835,500)]);d.arrow([(1610,500),(1755,500)])
d.arrow([(1755,650),(1610,650)]);d.text(1618,670,'Proposals',24,width=145)

# Cloud stores and maintenance are separate trust/processing boundaries.
d.box(60,820,2440,470,'#F6F7FB',True)
d.logo('googlecloud',90,842,54);d.text(165,850,'Google Cloud',38,width=400)
for x,fill in [(90,BLUE),(700,PINK),(1310,YELLOW),(1920,PURPLE)]:d.box(x,940,550,300,fill)
d.logo('postgresql',115,967,48);d.text(180,968,'Cloud SQL',38,width=425)
d.text(115,1050,['PostgreSQL / schema 11','Accounts, cases, v2 ledger','Versions + operation replay'],30,width=500)
d.icon('folder',725,967,48);d.text(790,968,'Cloud Storage',36,width=430)
d.text(725,1050,['Private originals + SHA-256','PDF / JSON / selected ZIP','Authorized downloads'],30,width=500)
d.icon('clock',1335,967,48);d.text(1400,968,'Worker + queue',36,width=430)
d.text(1335,1050,['Cloud Run Job + SQL leases','Scheduler: every minute','Exports / expiry / deletion'],30,width=500)
d.icon('shield',1945,967,48);d.text(2010,968,'Secrets + IAM',36,width=430)
d.text(1945,1050,['Secret Manager references','Model / DB / signing keys','Server-side credentials'],30,width=500)
d.arrow([(1040,720),(1040,770),(650,770),(650,900),(365,900),(365,930)])
d.arrow([(1290,720),(1290,790),(975,790),(975,930)])
d.arrow([(1530,720),(1530,760),(1585,760),(1585,930)])
d.arrow([(2195,930),(2195,760),(1870,760),(1870,720)],dash=True)

d.text(65,1310,'Partial / deferred: mixed-PDF + email/audio • PWA/extension • Gmail/WhatsApp • external reminders + timestamps',26,color=MUTED,width=2400)
d.text(65,1373,'15 Nov 2026 • v2 services implemented; main-UI integration pending. Live model / auth / worker / restore checks remain open.',25,color=MUTED,width=2400)
tech=d.finish('02-bindr-technical-architecture')
style=f'html,body{{margin:0;background:#f4f6f8}}.sheet{{width:{W}px;height:{H}px;background:white;page-break-after:always}}@page{{size:{W}px {H}px;margin:0}}'
(ROOT/'print.html').write_text(f'<html><meta charset="utf-8"><style>{style}</style><div class="sheet">{user}</div><div class="sheet">{tech}</div></html>',encoding='utf-8')
print('Updated existing diagrams: concise 16:9 editions, 15 November 2026.')
