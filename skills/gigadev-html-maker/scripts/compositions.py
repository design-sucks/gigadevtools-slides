"""Small, escaped, source-independent composition renderer. No shell/UI changes."""
from pathlib import Path
import argparse,html,json,re,math
ROOT=Path(__file__).resolve().parents[1]/'assets/compositions'
def catalog():return json.loads((ROOT/'catalog.json').read_text())
def text(value):return ' '.join(text(v) for v in value) if isinstance(value,list) else str(value.get('text','')) if isinstance(value,dict) else str(value or '')
def esc(value):return html.escape(text(value),quote=True)
def node(value,tag='p',cls=''):
 if isinstance(value,list):return ''.join(node(v,tag,cls)for v in value)
 ident=value.get('sourceId') if isinstance(value,dict) else None
 if ident and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',ident):raise ValueError('Invalid sourceId')
 content=esc(value).replace("\n","<br>")
 if isinstance(value,dict)and value.get('runs'):
  pieces=[]
  for run in value['runs']:
   piece=esc(run.get('text','')).replace('\n','<br>');url=run.get('link',run.get('href'))
   if url:
    if not re.match(r'^(https?://|mailto:|tel:|#)',url):raise ValueError('Unsafe run link')
    piece='<a href="'+html.escape(url,quote=True)+'">'+piece+'</a>'
   if run.get('bold'):piece='<strong>'+piece+'</strong>'
   if run.get('italic'):piece='<em>'+piece+'</em>'
   pieces.append(piece)
  content=''.join(pieces)
 if isinstance(value,dict)and value.get('href'):
  if not re.match(r'^(https?://|mailto:|tel:|#)',value['href']):raise ValueError('Unsafe content link')
  content='<a href="'+html.escape(value['href'],quote=True)+'">'+content+'</a>'
 return '<'+tag+(' class="'+cls+'"' if cls else '')+(' data-source-id="'+ident+'"' if ident else '')+'>'+content+'</'+tag+'>'
def glyph(item):
 ident=item.get('iconSourceId')
 if ident and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',ident):raise ValueError('Invalid iconSourceId')
 return '<img class="cp-icon"'+(' data-source-id="'+ident+'"'if ident else '')+' src="'+esc(item['icon'])+'" alt="'+esc(item.get('iconAlt',''))+'">'if item.get('icon')else ''
def tone(item):
 c=item.get('accent')
 if c and not re.fullmatch(r'#[0-9a-fA-F]{6}',c):raise ValueError('Item accent must be #RRGGBB')
 return ' style="--cp-item-accent:'+c+'"'if c else ''
def card(item,index=0,klass=''):
 return '<article class="cp-card '+klass+'"'+tone(item)+'>'+glyph(item)+(node(item['label'],'span','cp-label') if item.get('label') else '')+node(item['title'],'h3')+'<div class="cp-card-copy'+(' cp-card-copy--paragraphs'if isinstance(item.get('body'),list)else '')+'">'+node(item.get('body',''))+'</div></article>'
def validate(ident,data):
 specs={c['id']:c for c in catalog()['compositions']}
 if ident not in specs:raise ValueError('Unknown composition: '+ident)
 spec=specs[ident]
 unknown=set(data)-set(spec['required'])-set(spec.get('optional',[]))
 if unknown:raise ValueError('Unknown composition fields: '+','.join(sorted(unknown)))
 for key in spec['required']:
  if not data.get(key):raise ValueError(ident+': missing '+key)
 for field,limit in spec['limits'].items():
  if field in data and len(text(data[field]))>limit:raise ValueError(ident+': '+field+' exceeds '+str(limit)+' characters; choose another layout, do not truncate')
 for field,limits in spec.get('collections',{}).items():
  values=data.get(field,[])
  if not isinstance(values,list)or not limits[0]<=len(values)<=limits[1]:raise ValueError(ident+': '+field+' requires '+str(limits)+' items')
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k in ('body','detail')and len(text(v))>(360 if ident=='problem-cards'and len(data.get('items',[]))<=3 else spec.get('itemBodyMax',180)):raise ValueError(ident+': item body too long; use a denser pattern or explicit authored layout')
    walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(data)
 return spec
def render(ident,data,version=None):
 ident=catalog().get('aliases',{}).get(ident,ident)
 spec=validate(ident,data)
 if version and version!=spec['version']:raise ValueError('Composition version mismatch')
 title=node(data['title'],'h1' if ident in ('cover','divider') else 'h2','cp-title')
 lead=node(data['lead'],'p','cp-lead') if data.get('lead') else ''
 kicker=node(data['kicker'],'p','cp-kicker') if data.get('kicker') else ''
 head='<header class="cp-head">'+kicker+title+lead+'</header>'
 items=data.get('items',[]);body=''
 if ident in ('cover','divider'):
  body='<div class="cp-hero-copy">'+head+(node(data.get('detail',''),'p','cp-hero-detail')if data.get('detail')else '')+'</div>'
  if data.get('image'):body+='<figure class="cp-hero-media"><img src="'+esc(data['image'])+'" alt="'+esc(data.get('imageAlt',''))+'"></figure>'
  if data.get('actions'):body+='<div class="cp-actions">'+''.join(node(s,'span','cp-action')for s in data['actions'])+'</div>'
 elif ident=='agenda':body='<div class="cp-grid cp-grid--3">'+''.join(card(s,i)for i,s in enumerate(items))+'</div>'
 elif ident=='thesis-evidence':body='<div class="cp-split"><aside class="cp-thesis">'+node(data['thesis'],'h3')+node(data.get('detail',''))+'</aside><div class="cp-rows">'+''.join('<article class="cp-row">'+('<div class="cp-row-heading">'+node(s['label'],'span','cp-label')+node(s['title'],'h3')+'</div>'if s.get('label')else node(s['title'],'h3'))+node(s['body'])+'</article>'for s in items)+'</div></div>'
 elif ident=='role-process':body='<div class="cp-role-grid">'+''.join('<article class="cp-card">'+node(s.get('label',''),'span','cp-label')+node(s['title'],'h3')+node(s['body'])+'<div class="cp-node" aria-hidden="true"></div></article>'for s in items)+'</div><div class="cp-band">'+node(data.get('detail',''))+'</div>'
 elif ident=='problem-cards':body='<div class="cp-grid cp-grid--3">'+''.join(card(s,i,'is-key' if i==data.get('highlight',0) else '')for i,s in enumerate(items))+'</div>'
 elif ident=='architecture':
  body='<div class="cp-architecture"><div class="cp-arch-top">'+''.join(card(s,i)for i,s in enumerate(items[:2]))+'</div><div class="cp-connectors" aria-hidden="true"><i></i><i></i></div><div class="cp-arch-core">'+node(data['core']['title'],'h3')+node(data['core']['body'])+'</div><div class="cp-arch-note">'+node(data.get('detail',''))+'</div></div>'
 elif ident=='feature-map':body='<div class="cp-bento">'+''.join(card(s,i,'is-feature' if i==0 else '')for i,s in enumerate(items))+'</div>'
 elif ident=='comparison':
  columns=data['columns'];rows=data['rows'];highlight=data.get('highlightColumn')
  if highlight is not None and (not isinstance(highlight,int)or isinstance(highlight,bool)or not 0<=highlight<len(columns)):raise ValueError('highlightColumn must be a valid zero-based column index')
  table_id=data.get('tableSourceId')
  if table_id and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',table_id):raise ValueError('Invalid tableSourceId')
  body='<table class="cp-matrix"'+(' data-source-id="'+table_id+'"'if table_id else '')+'><thead><tr>'+''.join(node(s,'th','is-highlight'if i==highlight else '')for i,s in enumerate(columns))+'</tr></thead><tbody>'+''.join('<tr>'+''.join(node(c,'td','is-highlight'if i==highlight else '')for i,c in enumerate(row))+'</tr>'for row in rows)+'</tbody></table>'
  if any(len(row)!=len(columns)for row in rows):raise ValueError('Comparison rows must match columns')
 elif ident=='metrics':body='<div class="cp-metric-grid">'+''.join('<article class="cp-card '+('is-key'if i==0 else '')+'">'+node(s['value'],'p','cp-value')+node(s['title'],'h3')+node(s['body'])+'</article>'for i,s in enumerate(items))+'</div><div class="cp-secondary">'+''.join('<div>'+node(s['value'],'p','cp-small-value')+node(s['title'])+'</div>'for s in data.get('secondary',[]))+'</div>'
 elif ident=='trend':
  values=data['values']
  if any(not isinstance(v,(int,float))or not math.isfinite(v)or v<0 for v in values)or not max(values):raise ValueError('Trend needs nonnegative finite values and a positive maximum')
  if len(data['labels'])!=len(values):raise ValueError('Trend labels must match values')
  maximum=max(values);bars=[]
  for i,v in enumerate(values):
   height=round(100*v/maximum,4)
   bars.append('<div class="cp-bar-col">'+node(str(v),'span','cp-bar-value')+'<div class="cp-bar" style="height:'+str(height)+'%"></div>'+node(data['labels'][i],'span','cp-bar-label')+'</div>')
  if len(data['labels'])!=len(values):raise ValueError('Trend labels must match values')
  body='<div class="cp-trend"><div class="cp-chart">'+''.join(bars)+'</div><aside class="cp-trend-summary">'+node(data['metric'],'p','cp-value')+node(data['takeaway'],'h3')+node(data.get('detail',''))+'</aside></div>'
 elif ident=='progress':body='<div class="cp-grid cp-grid--2">'+''.join('<article class="cp-panel">'+node(s['title'],'h3')+'<div class="cp-status-list">'+''.join('<div>'+node(x['label'])+node(x['status'],'span','cp-status')+'</div>'for x in s['items'])+'</div></article>'for s in items)+'</div>'
 elif ident=='roadmap':
  periods=data['periods'];body='<div class="cp-roadmap"><div class="cp-roadmap-head"><span></span>'+''.join(node(x,'h3')for x in periods)+'</div>'
  for s in items:
   if len(s['cells'])!=len(periods):raise ValueError('Roadmap cells must match periods')
   body+='<div class="cp-roadmap-row">'+node(s['title'],'h3')+''.join(node(x,'p','cp-roadmap-cell')for x in s['cells'])+'</div>'
  body+='</div>'
 elif ident=='maturity':body='<div class="cp-ladder">'+''.join('<article><span class="cp-index">'+str(i+1).zfill(2)+'</span>'+node(s['title'],'h3')+node(s['body'])+'</article>'for i,s in enumerate(items))+'</div>'
 elif ident=='offer':body='<div class="cp-grid cp-grid--2">'+''.join('<article class="cp-card cp-offer">'+node(s.get('label',''),'p','cp-label')+node(s['title'],'h3')+node(s['value'],'p','cp-value')+node(s['body'])+'<ul>'+''.join(node(x,'li')for x in s['features'])+'</ul></article>'for s in items)+'</div><div class="cp-band">'+node(data.get('detail',''))+'</div>'
 elif ident=='demo':body='<div class="cp-demo"><figure class="cp-screen"><img src="'+esc(data['image'])+'" alt="'+esc(data.get('imageAlt',''))+'"></figure><aside>'+node(data['metric'],'p','cp-value')+node(data['takeaway'],'h3')+'<div class="cp-rows">'+''.join(node(s)for s in data.get('notes',[]))+'</div></aside></div>'
 elif ident=='gallery':body='<div class="cp-gallery-head">'+''.join('<div>'+node(s['value'],'p','cp-value')+node(s['title'])+'</div>'for s in data.get('metrics',[]))+'</div><div class="cp-gallery">'+''.join('<figure><img src="'+esc(s['image'])+'" alt="'+esc(s.get('alt',''))+'">'+node(s['caption'],'figcaption')+'</figure>'for s in items)+'</div>'
 elif ident=='scorecard':body='<div class="cp-scorecards">'+''.join('<article class="cp-scorecard"><div>'+node(s['value'],'p','cp-value')+node(s['title'],'h3')+'</div><div>'+''.join('<div class="cp-row">'+node(x['title'],'h3')+node(x['body'])+'</div>'for x in s['items'])+'</div></article>'for s in items)+'</div>'
 else:raise ValueError('Renderer missing for '+ident)
 footer=('<footer class="cp-foot">'+node(data['footer'])+'</footer>'if isinstance(data.get('footer'),list)else node(data.get('footer',''),'footer','cp-foot'))if data.get('footer')else ''
 main=body if ident in ('cover','divider') else head+'<div class="cp-body">'+body+'</div>'
 result='<div class="cp cp--'+ident+(' cp--long-title'if len(text(data['title']))>64 else '')+'" data-composition="'+ident+'" data-composition-version="'+spec['version']+'"'+(' data-composition-sample="true"'if data.get('sampleOnly')else '')+'>'+main+footer+'</div>'
 def retained(x):
  if isinstance(x,dict):
   for key,value in x.items():
    if key in ('icon','image') and value and esc(value) not in result:raise ValueError('Supplied graphic was not rendered; choose another composition or explicit HTML')
    if key in ('sourceId','iconSourceId','tableSourceId')and value and 'data-source-id="'+str(value)+'"'not in result:raise ValueError('Supplied sourceId was not rendered: '+str(value))
    retained(value)
  elif isinstance(x,list):
   for value in x:retained(value)
 retained(data)
 ids=re.findall(r'data-source-id="([^"]+)"',result)
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate sourceId targets')
 return result
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);a=sub.add_parser('list');a.add_argument('--intent');a=sub.add_parser('render');a.add_argument('id');a.add_argument('content');a.add_argument('out');a.add_argument('--version');args=p.parse_args()
 if args.command=='list':
  rows=catalog()['compositions'];rows=[r for r in rows if not args.intent or args.intent in r['intents']or args.intent in r['id']];print(json.dumps([{'id':r['id'],'name':r['name'],'version':r['version'],'useWhen':r['useWhen'],'collections':r.get('collections',{})}for r in rows],ensure_ascii=False,indent=2))
 else:
  out=Path(args.out)
  if out.exists():raise ValueError('Use a new output path')
  out.write_text(render(args.id,json.loads(Path(args.content).read_text()),args.version));print(json.dumps({'status':'rendered','composition':args.id,'out':str(out)}))
if __name__=='__main__':main()
