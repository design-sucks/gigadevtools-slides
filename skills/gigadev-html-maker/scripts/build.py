"""Build an offline HTML deck from a reviewed content project and a theme."""
from pathlib import Path
import argparse,base64,html,json,mimetypes,re,uuid
ASSETS=Path(__file__).resolve().parent.parent/'assets'
DEFAULT={'name':'Neutral SB','themes':['dark'],'primary':'dark','font':'"SB Sans Text", Arial, sans-serif','displayFont':'"SB Sans Display", Arial, sans-serif','colors':{'dark':{'bg':'#050709','shell':'#050709','ink':'#F2F4F3','muted':'#B0BEBA','accent':'#A6E3BC','line':'#34433D'},'light':{'bg':'#F4F4F4','shell':'#F4F4F4','ink':'#202020','muted':'#585858','accent':'#21673D','line':'#D4D4D4'}},'css':''}
def safe_json(value):return json.dumps(value,ensure_ascii=False).replace('<','\\u003c')
def build(project,out,theme=None):
 project=Path(project);out=Path(out)
 if out.exists():raise ValueError('Use a new HTML output path')
 deck=json.loads(project.read_text());style=json.loads(Path(theme).read_text()) if theme else DEFAULT
 if not deck.get('slides'):raise ValueError('Deck must contain at least one slide')
 version=deck.get('version',1)
 if not isinstance(version,int) or version<1:raise ValueError('Version must be a positive integer')
 title=str(deck.get('title') or project.stem);records={s['id']:s for s in deck['slides']};order=deck.get('order',list(records))
 if len(records)!=len(deck['slides']) or not order or len(set(order))!=len(order) or any(i not in records for i in order):raise ValueError('Duplicate/unknown/empty slide order')
 if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',i) for i in records):raise ValueError('Slide ids must be safe stable identifiers')
 themes=style.get('themes',['dark'])
 if not themes or len(set(themes))!=len(themes) or any(t not in ['dark','light'] for t in themes):raise ValueError('Themes must be a nonempty subset of dark/light')
 primary=style.get('primary',themes[0])
 if primary not in themes:raise ValueError('Primary theme is not available')
 palette=[]
 for key in ['bg','ink','muted','accent','line','shell']:
  values={}
  for t in ['dark','light']:
   theme_colors=style.get('colors',{}).get(t,style.get('colors',{}).get(primary,{}))
   c=theme_colors.get(key,theme_colors.get('bg',DEFAULT['colors'][t][key]) if key=='shell' else DEFAULT['colors'][t][key])
   if not re.fullmatch(r'#[a-fA-F0-9]{6}',c):raise ValueError('Use #RRGGBB theme colors')
   values[t]=[int(c[i:i+2],16) for i in [1,3,5]]+[1]
  palette.append({'name':'--gd-'+key,**values,'muted':key=='muted'})
 def embed(name):
  p=(project.parent/name).resolve()
  if not p.is_relative_to(project.parent.resolve()):raise ValueError('Assets must stay inside the project')
  return 'data:'+(mimetypes.guess_type(p)[0] or 'application/octet-stream')+';base64,'+base64.b64encode(p.read_bytes()).decode()
 def local_assets(markup):
  def sub(m):
   value=m[3]
   if value.startswith(('data:','#','http:','https:')):return m[0]
   return m[1]+m[2]+embed(value)+m[2]
  return re.sub(r'((?:src|poster)\s*=\s*)([\"\'])([^\"\']+)\2',sub,markup)
 def paragraph(p):
  rs=[]
  for r in p.get('runs',[{'text':p.get('text','')}]):
   v=html.escape(r.get('text','')).replace('\n','<br>')
   if r.get('bold'):v='<strong>'+v+'</strong>'
   if r.get('italic'):v='<em>'+v+'</em>'
   if r.get('link') and re.match(r'^(https?://|mailto:|tel:)',r['link']):v='<a href="'+html.escape(r['link'],quote=True)+'">'+v+'</a>'
   rs.append(v)
  return ''.join(rs)
 def content(slide):
  if 'html' in slide:return slide['html']
  result=[]
  for b in slide.get('blocks',[]):
   kind=b['kind']
   if kind=='text':
    for p in b.get('paragraphs',[]):result.append(('<h2>' if b.get('title') else '<p>')+paragraph(p)+('</h2>' if b.get('title') else '</p>'))
   elif kind=='table':result.append('<table>'+''.join('<tr>'+''.join('<td>'+'<br>'.join(paragraph(p) for p in cell)+'</td>' for cell in row)+'</tr>' for row in b['rows'])+'</table>')
   elif kind=='image':result.append('<figure><img src="'+embed(b['asset'])+'" alt="'+html.escape(b.get('alt',''),quote=True)+'"></figure>')
   elif kind=='media':result.append('<'+b['mediaType']+' controls src="'+embed(b['asset'])+'"></'+b['mediaType']+'>')
   elif kind=='chart':
    for se in b.get('series',[]):
     cats=se.get('categories',[]);vals=se.get('values',[])
     result.append('<table><caption>'+html.escape(se.get('name',''))+'</caption>'+''.join('<tr><td>'+html.escape(cats[i] if i<len(cats) else str(i+1))+'</td><td>'+html.escape(value)+'</td></tr>' for i,value in enumerate(vals))+'</table>')
  return '\n'.join(result)
 slides=[]
 for sid,slide in records.items():
  body=local_assets(content(slide))
  if re.search(r'<script\b|\son\w+\s*=|javascript\s*:',body,re.I):raise ValueError('Slide markup must contain content, not scripts/event handlers')
  section=html.escape(str(slide.get('section','')));topic=html.escape(str(slide.get('topic') or slide.get('label') or ''));header=slide.get('header','full')
  if header not in ['full','number','none']:raise ValueError('Unknown header mode')
  crumbs=(('<span>'+section+'</span><i>·</i>') if section else '')+'<span>'+topic+'</span>' if header=='full' else ''
  slides.append(f'<section class="slide" data-sk-id="{sid}" data-sk-section="{section}" data-sk-topic="{topic}" data-gd-header="{header}" data-gd-source-number="{int(slide.get("sourceNumber",0))}"><div class="gd-export-meta" data-header="{header}"><div class="gd-export-crumbs">{crumbs}</div><span class="slide-page">1</span></div><div class="slide-inner"><div class="gd-content">{body}</div></div></section>')
 preparation=deck.get('preparationChanges',[])
 if not isinstance(preparation,list):raise ValueError('preparationChanges must be a list')
 seen=set()
 for item in preparation:
  if not isinstance(item,dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',str(item.get('id',''))) or item['id'] in seen:raise ValueError('Invalid/duplicate preparation change ID')
  seen.add(item['id'])
  if item.get('slide') not in records:raise ValueError('Unknown preparation slide')
  if item.get('actor') not in ['llm','typograf','user'] or item.get('kind') not in ['text','typography','layout'] or item.get('status') not in ['applied','pending','rejected']:raise ValueError('Invalid preparation actor/kind/status')
  if any(not isinstance(item.get(k),str) for k in ['title','before','after']):raise ValueError('Preparation text fields must be strings')
  if item['status']=='pending' and (not item.get('sourceId') or item['kind']=='layout' or not item['after'].strip()):raise ValueError('Pending proposal needs a sourceId and a nonempty text replacement')
 settings={'theme':primary,'motion':deck.get('motion'),'screen':{'contrast':100,'shadows':100,'muted':0,'saturation':100}}
 meta={'slides':[{**{k:s[k] for k in ['id','sourceNumber','section','topic','header'] if k in s},'label':s.get('label',s.get('title','Слайд')),'number':i+1} for i,s in enumerate(records.values())],'order':order,'title':title,'fileStem':re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',title),'version':version,'settings':settings,'themes':themes,'history':[],'preparationChanges':preparation,'savedAt':0,'shellVersion':'v17-preview'}
 shell=(ASSETS/'shell.html').read_text().replace('@@GD_SLIDES@@','\n'.join(slides)).replace('@@GD_TITLE@@',html.escape(title,quote=True)).replace('@@GD_VERSION@@','v'+str(version).zfill(2))
 base=':root{'+''.join(c['name']+':'+style.get('colors',DEFAULT['colors']).get(primary,DEFAULT['colors'][primary]).get(c['name'][5:],DEFAULT['colors'][primary][c['name'][5:]])+';' for c in palette)+'--gd-font:'+style.get('font',DEFAULT['font'])+';--gd-display-font:'+style.get('displayFont',style.get('font',DEFAULT['displayFont']))+';}'
 css=style.get('css','')
 if style.get('builtinFonts',True):
  supplied={(f['family'],f.get('weight',400)) for f in style.get('fonts',[])}
  for f in json.loads((ASSETS/'fonts/manifest.json').read_text())['faces']:
   if (f['family'],f['weight']) in supplied:continue
   data=base64.b64encode((ASSETS/f['path']).read_bytes()).decode()
   css+='\n@font-face{font-family:'+json.dumps(f['family'])+';font-weight:'+str(f['weight'])+';font-style:normal;font-display:swap;src:url(data:font/otf;base64,'+data+') format("opentype")}'
 for font in style.get('fonts',[]):css+='\n@font-face{font-family:'+json.dumps(font['family'])+';font-weight:'+str(font.get('weight',400))+';src:url('+embed(font['path'])+')}'
 scripts='\n'.join('<script id="'+('sk-controller' if n=='controller' else 'gd-'+n)+'">'+(ASSETS/(n+'.js')).read_text()+'</script>' for n in ['navigation','editor','flow','controller','journal','motion','adapter','tooltips'])
 output='<!doctype html><html lang="ru" data-gd-maker="1" data-sk-doc="gd-'+uuid.uuid4().hex+'" data-sk-theme="'+primary+'" data-sk-motion="on"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · v'+str(version).zfill(2)+'</title><style id="sk-ui-styles">'+(ASSETS/'ui.css').read_text()+'</style><style id="gd-deck-styles">'+(ASSETS/'deck.css').read_text()+'</style><style id="gd-style-pack">'+base+'\n'+css+'</style><style id="sk-colors"></style><script type="application/json" id="sk-color-registry">'+safe_json(palette)+'</script><script type="application/json" id="sk-deck-state">'+safe_json(meta)+'</script></head><body>'+shell+scripts+'</body></html>'
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(output)
 print(json.dumps({'status':'built','html':str(out.resolve()),'slides':len(order),'available':len(records),'themes':themes,'bytes':out.stat().st_size,'visualApproval':False},ensure_ascii=False))
 return output
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('out');p.add_argument('--theme');a=p.parse_args();build(a.project,a.out,a.theme)
