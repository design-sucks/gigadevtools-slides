"""Build an offline HTML deck from a reviewed content project and a theme."""
from pathlib import Path
import argparse,base64,html,json,mimetypes,re,uuid,struct,hashlib,shutil
from urllib.parse import quote
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
ASSETS=Path(__file__).resolve().parent.parent/'assets'
import importlib.util
_list_spec=importlib.util.spec_from_file_location('gd_list_levels',Path(__file__).resolve().parent/'list_levels.py')
_list_module=importlib.util.module_from_spec(_list_spec);_list_spec.loader.exec_module(_list_module)
normalize_list_levels=_list_module.normalize_list_levels
DEFAULT={'name':'Neutral SB','themes':['dark'],'primary':'dark','font':'"SB Sans Text", Arial, sans-serif','displayFont':'"SB Sans Display", Arial, sans-serif','colors':{'dark':{'bg':'#050709','shell':'#050709','ink':'#F2F4F3','muted':'#B0BEBA','accent':'#A6E3BC','line':'#34433D'},'light':{'bg':'#F4F4F4','shell':'#F4F4F4','ink':'#202020','muted':'#585858','accent':'#21673D','line':'#D4D4D4'}},'css':''}
def safe_json(value):return json.dumps(value,ensure_ascii=False).replace('<','\\u003c')
class SourceTargets(HTMLParser):
 def __init__(self,source_id):super().__init__(convert_charrefs=True);self.source_id=source_id;self.stack=[];self.active=[];self.matches=[]
 def handle_starttag(self,tag,attrs):
  void={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
  if tag=='br':
   for node in self.active:node['text'].append('\n')
  if dict(attrs).get('data-source-id')==self.source_id:
   node={'tag':tag,'depth':len(self.stack),'text':[]};self.matches.append(node);self.active.append(node)
  if tag in void:return
  self.stack.append(tag)
 def handle_startendtag(self,tag,attrs):
  if dict(attrs).get('data-source-id')==self.source_id:self.matches.append({'tag':tag,'depth':len(self.stack),'text':[]})
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i]==tag:
    depth=i;self.stack=self.stack[:i];self.active=[node for node in self.active if node['depth']<depth];break
 def handle_data(self,data):
  for node in self.active:node['text'].append(data)
def plain_markup(value):return value.strip()
def validate_scoped_css(value):
 if re.search(r'</style|@(?:import|font-face)\b',value,re.I):raise ValueError('Scoped slide CSS cannot contain @import, @font-face or a style closing tag')
 for name in re.findall(r'@(?:-webkit-)?keyframes\s+([\w-]+)',value,re.I):
  if not name.startswith('gdslide-'):raise ValueError('Scoped animation names must start with gdslide-')
 depth=0;quote_char=None;comment=False;i=0
 while i<len(value):
  c=value[i];n=value[i+1] if i+1<len(value) else ''
  if comment:
   if c=='*' and n=='/':comment=False;i+=2;continue
  elif quote_char:
   if c=='\\':i+=2;continue
   if c==quote_char:quote_char=None
  elif c=='/' and n=='*':comment=True;i+=2;continue
  elif c in ('"',"'"):quote_char=c
  elif c=='\\':raise ValueError('CSS escapes outside strings are not supported in strict scoped CSS')
  elif c=='@':
   match=re.match(r'@([a-zA-Z-]+)',value[i:])
   if not match or match.group(1).lower() not in ('media','supports','container','keyframes','-webkit-keyframes'):raise ValueError('Global or unsupported CSS at-rule in strict scoped CSS')
   if match.group(1).lower() in ('keyframes','-webkit-keyframes'):
    rest=value[i+len(match.group(0)):]
    name=re.match(r'(?:\s|/\*.*?\*/)+([a-zA-Z_][\w-]*)',rest,re.S)
    if not name or not name.group(1).startswith('gdslide-'):raise ValueError('Scoped animation names must start with gdslide-')
  elif c=='{':depth+=1
  elif c=='}':
   depth-=1
   if depth<0:raise ValueError('Unbalanced slide CSS')
  i+=1
 if depth or quote_char or comment:raise ValueError('Unbalanced slide CSS')
def image_dimensions(path):
 data=path.read_bytes()
 if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>=24:return struct.unpack('>II',data[16:24])
 if data[:3]==b'GIF' and len(data)>=10:return struct.unpack('<HH',data[6:10])
 if data[:2]==b'\xff\xd8':
  i=2
  while i+4<len(data):
   if data[i]!=255:i+=1;continue
   while i<len(data) and data[i]==255:i+=1
   if i>=len(data):break
   marker=data[i];i+=1
   if marker in (0xd8,0xd9,0x01) or 0xd0<=marker<=0xd7:continue
   if i+2>len(data):break
   size=int.from_bytes(data[i:i+2],'big')
   if size<2 or i+size>len(data):break
   if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf) and size>=7:
    height,width=struct.unpack('>HH',data[i+3:i+7]);return width,height
   i+=size
 return None
def build(project,out,theme=None,typography="apply",final=False,composition_plan=None,external_media=False):
 if typography not in ("off","review","apply"):raise ValueError("Unknown typography mode")
 prepare_typography=None
 if typography!="off":
  import importlib.util
  spec=importlib.util.spec_from_file_location("gd_typography",Path(__file__).resolve().parent/"typography.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);prepare_typography=module.prepare
 project=Path(project);out=Path(out)
 if out.exists():raise ValueError('Use a new HTML output path')
 deck=json.loads(project.read_text());theme_path=Path(theme).resolve() if theme else ASSETS/'base-theme.json'
 style=json.loads(theme_path.read_text()) if theme or theme_path.exists() else DEFAULT
 isolation=deck.get('cssIsolation','legacy')
 if isolation not in ('legacy','strict'):raise ValueError('cssIsolation must be legacy or strict')
 if not deck.get('slides'):raise ValueError('Deck must contain at least one slide')
 version=deck.get('version',1)
 if not isinstance(version,int) or version<1:raise ValueError('Version must be a positive integer')
 title=str(deck.get('title') or project.stem);records={s['id']:s for s in deck['slides']};order=deck.get('order',list(records))
 if len(records)!=len(deck['slides']) or not order or len(set(order))!=len(order) or any(i not in records for i in order):raise ValueError('Duplicate/unknown/empty slide order')
 if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',i) for i in records):raise ValueError('Slide ids must be safe stable identifiers')
 if final:
  missing=[sid for sid in order if not records[sid].get('html', '').strip() and not records[sid].get('composition')]
  if missing:raise ValueError('Final build rejects assembly drafts: '+', '.join(missing))
  if not composition_plan:raise ValueError('Final build requires --composition-plan')
  import importlib.util
  spec=importlib.util.spec_from_file_location('gd_composition_plan',Path(__file__).resolve().parent/'composition_plan.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  plan_path=Path(composition_plan);module.validate(deck,json.loads(plan_path.read_text()),plan_path.parent,require_visual=True,project_sha256=hashlib.sha256(project.read_bytes()).hexdigest())
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
 external_files={};external_dir=out.parent/(out.stem+'_media')
 def embed(name):
  p=(project.parent/name).resolve()
  if not p.is_relative_to(project.parent.resolve()):raise ValueError('Assets must stay inside the project')
  mime=mimetypes.guess_type(p)[0] or 'application/octet-stream'
  if external_media and mime.startswith(('video/','audio/')):
   if p not in external_files:
    digest=hashlib.sha256()
    with p.open('rb') as stream:
     for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    external_files[p]=digest.hexdigest()+p.suffix.lower()
   return quote(external_dir.name)+'/'+quote(external_files[p])
  return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()
 def local_assets(markup):
  def sub(m):
   value=m[3]
   if value.startswith(('data:','#','http:','https:')):return m[0]
   if external_media and value.startswith(quote(external_dir.name)+'/') and value.split('/')[-1] in external_files.values():return m[0]
   return m[1]+m[2]+embed(value)+m[2]
  return re.sub(r'((?:src|poster)\s*=\s*)([\"\'])([^\"\']+)\2',sub,markup)
 def paragraph(p):
  rs=[]
  for r in p.get('runs',[{'text':p.get('text','')}]):
   v=html.escape(r.get('text','')).replace('\n','<br>')
   if r.get('bold'):v='<strong>'+v+'</strong>'
   if r.get('italic'):v='<em>'+v+'</em>'
   tracking=r.get('trackingPt')
   if isinstance(tracking,(int,float)) and not isinstance(tracking,bool) and -400<=tracking<=400:
    v=f'<span style="letter-spacing:{tracking}pt">'+v+'</span>'
   if r.get('link') and re.match(r'^(https?://|mailto:|tel:)',r['link']):v='<a href="'+html.escape(r['link'],quote=True)+'">'+v+'</a>'
   rs.append(v)
  return ''.join(rs)
 def source_attr(ident):
  return f' data-source-id="{html.escape(str(ident),quote=True)}"' if ident else ''
 def list_type(p):
  effective=p.get('effectiveList',{})
  if effective.get('status')=='resolved':return effective.get('kind') if effective.get('kind') in ('ul','ol') else None
  try: root=ET.fromstring(p.get('paragraphPropertiesXml',''))
  except ET.ParseError:return None
  names={e.tag.rsplit('}',1)[-1] for e in root}
  if 'buAutoNum' in names:return 'ol'
  if names.intersection(('buChar','buBlip')):return 'ul'
  return None
 def numbered_list_attrs(p):
  effective=p.get('effectiveList',{})
  if effective.get('status')=='resolved' and effective.get('kind')=='ol':
   kinds={'arabicPeriod':'1','alphaLcPeriod':'a','alphaUcPeriod':'A','romanLcPeriod':'i','romanUcPeriod':'I'}
   attrs=effective.get('attributes',{});typ=kinds.get(attrs.get('type'));start=attrs.get('startAt','1')
   return (' type="'+typ+'"' if typ else '')+(' start="'+start+'"' if str(start).isdigit() and int(start)>0 else '')
  try:root=ET.fromstring(p.get('paragraphPropertiesXml',''))
  except ET.ParseError:return ''
  bullet=next((e for e in root if e.tag.rsplit('}',1)[-1]=='buAutoNum'),None)
  if bullet is None:return ''
  kinds={'arabicPeriod':'1','alphaLcPeriod':'a','alphaUcPeriod':'A','romanLcPeriod':'i','romanUcPeriod':'I'}
  typ=kinds.get(bullet.get('type'));start=bullet.get('startAt','1')
  return (' type="'+typ+'"' if typ else '')+(' start="'+start+'"' if start.isdigit() and int(start)>0 else '')
 def draft_paragraphs(paragraphs,ident,tag):
  parts=[];stack=[];levels=normalize_list_levels(paragraphs,list_type)
  def close_level():
   kind=stack.pop();parts.append('</li></'+kind+'>')
  for i,p in enumerate(paragraphs,1):
   kind=list_type(p)
   if not kind:
    while stack:close_level()
    parts.append('<'+tag+source_attr(f'{ident}-p{i}' if ident else None)+'>'+paragraph(p)+'</'+tag+'>');continue
   normalized,opens=levels[i-1];depth=normalized+1
   while len(stack)>depth:close_level()
   if opens and len(stack)==depth:close_level()
   if len(stack)<depth:parts.append('<'+kind+(numbered_list_attrs(p) if kind=='ol' else '')+'>');stack.append(kind)
   else:parts.append('</li>')
   parts.append('<li'+source_attr(f'{ident}-p{i}' if ident else None)+'>'+paragraph(p))
  while stack:close_level()
  return '<div'+source_attr(ident)+'>'+''.join(parts)+'</div>'
 def draft_table(block):
  rows=block['rows']
  layout=block.get('tableLayout',{})
  attrs=[[cell.get('attributes',{}) for cell in row['cells']] for row in layout.get('rows',[])]
  attrs_valid=len(attrs)==len(rows) and all(len(a)==len(row) for a,row in zip(attrs,rows))
  continued=lambda a:any(a.get(key) in ('1','true') for key in ('hMerge','vMerge'))
  if attrs_valid and any(continued(a) and any(p.get('text','').strip() for p in cell)
                         for row,arow in zip(rows,attrs) for cell,a in zip(row,arow)):
   attrs_valid=False  # Retain nonempty continuation cells when the source is ambiguous.
  cols=layout.get('columnsEMU',[])
  grid=('<colgroup>'+''.join(f'<col style="width:{100*w/sum(cols):.4f}%">' for w in cols)+'</colgroup>') if cols and all(w>0 for w in cols) else ''
  output=[]
  for i,row in enumerate(rows):
   cells=[]
   for j,cell in enumerate(row):
    a=attrs[i][j] if attrs_valid else {}
    if continued(a):continue
    spans=''.join(f' {target}="{int(a.get(key,1))}"' for key,target in [('rowSpan','rowspan'),('gridSpan','colspan')]
                  if str(a.get(key,1)).isdigit() and int(a.get(key,1))>1)
    cells.append('<td'+spans+'>'+'<br>'.join(paragraph(p) for p in cell)+'</td>')
   output.append('<tr>'+''.join(cells)+'</tr>')
  return '<table'+source_attr(block.get('id'))+'>'+grid+''.join(output)+'</table>'
 def content(slide):
  if slide.get('composition'):
   if 'html' in slide:raise ValueError('Choose composition data or explicit html, not both')
   import importlib.util
   spec=importlib.util.spec_from_file_location('gd_compositions',ASSETS.parent/'scripts/compositions.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   c=slide['composition']
   if c['data'].get('sampleOnly') and deck.get('purpose')!='composition-library-demo':raise ValueError('Composition sample content is allowed only in a composition-library-demo deck; replace it with the actual input')
   return module.render(c['id'],c['data'],c.get('version'))
  if 'html' in slide:
   if 'data-gd-reference-only' in slide['html']:raise ValueError('Reference sample is not final slide content; replace sample text, art and paint and author the slide')
   return slide['html']
  result=[]
  for b in slide.get('blocks',[]):
   kind=b['kind']
   if kind=='text':
    paragraphs=b.get('paragraphs',[]);ident=b.get('id');tag='h2' if b.get('title') else 'p'
    if len(paragraphs)==1 and not list_type(paragraphs[0]):
     result.append(f'<{tag}'+source_attr(ident)+'>'+paragraph(paragraphs[0])+f'</{tag}>')
    elif paragraphs:
     result.append(draft_paragraphs(paragraphs,ident,tag))
   elif kind=='table':result.append(draft_table(b))
   elif kind=='image':result.append('<figure><img'+source_attr(b.get('id'))+' src="'+embed(b['asset'])+'" alt="'+html.escape(b.get('alt',''),quote=True)+'"></figure>')
   elif kind=='media':
    kind=b['mediaType']
    poster=' poster="'+embed(b['poster'])+'"' if kind=='video' and b.get('poster') else ''
    settings=b.get('mediaTiming',{}).get('settings',[])
    evidence=settings[0] if len(settings)==1 else {}
    muted=' muted' if evidence.get('mute') in ('1','true') else ''
    loop=' loop' if evidence.get('timeline',{}).get('repeatCount')=='indefinite' else ''
    raw_volume=evidence.get('vol','')
    volume=(' data-gd-volume="'+str(int(raw_volume)/100000)+'"') if str(raw_volume).isdigit() and 0<=int(raw_volume)<=100000 else ''
    result.append('<'+kind+source_attr(b.get('id'))+' controls preload="none"'+(' playsinline' if kind=='video' else '')+muted+loop+volume+poster+' src="'+embed(b['asset'])+'"></'+kind+'>')
   elif kind=='chart':
    for se in b.get('series',[]):
     cats=se.get('categories',[]);vals=se.get('values',[])
     result.append('<table><caption>'+html.escape(se.get('name',''))+'</caption>'+''.join('<tr><td>'+html.escape(cats[i] if i<len(cats) else str(i+1))+'</td><td>'+html.escape(value)+'</td></tr>' for i,value in enumerate(vals))+'</table>')
  return '\n'.join(result)
 import importlib.util
 nav_spec=importlib.util.spec_from_file_location('gd_navigation',Path(__file__).resolve().parent/'navigation.py')
 nav_module=importlib.util.module_from_spec(nav_spec);nav_spec.loader.exec_module(nav_module)
 navigation=nav_module.resolve(list(records.values()))
 role_spec=importlib.util.spec_from_file_location('gd_presentation_roles',Path(__file__).resolve().parent/'presentation_roles.py')
 role_module=importlib.util.module_from_spec(role_spec);role_spec.loader.exec_module(role_module)
 preparation=deck.get('preparationChanges',[])
 if not isinstance(preparation,list):raise ValueError('preparationChanges must be a list')
 preparation=list(preparation)
 existing_ids={item.get('id') for item in preparation if isinstance(item,dict) and isinstance(item.get('id'),str)}
 authored={}
 automatic_count=0
 slides=[]
 for sid,slide in records.items():
  body=role_module.prepare(slide,content(slide),deck.get('source',{}).get('canvas'),final)
  if isolation=='strict' and re.search(r'<(?:style|link)\b',body,re.I):raise ValueError('Strict slide content must not inject stylesheets; use slideCss or the theme')
  if typography!='off' and 'html' in slide:
   slide_changes=[item for item in preparation if isinstance(item,dict) and item.get('slide')==sid and isinstance(item.get('sourceId'),str)]
   # Fold safe mechanics into an existing applied text edit; keep one journal
   # target and preserve its original before string. Inline-marked blocks remain excluded.
   if typography=='apply':
    applied={item['sourceId']:item for item in slide_changes if item.get('kind')=='text' and item.get('status')=='applied' and item.get('actor') in ('llm','user')}
    body,merged=prepare_typography(body,set(),apply=True,include=set(applied))
    for change in merged:
     if applied[change['sourceId']].get('after')!=change['before']:
      raise ValueError(f"Typography merge precondition mismatch for {change['sourceId']}: applied correction is stale")
     applied[change['sourceId']]['after']=change['after']
   excluded={item['sourceId'] for item in slide_changes}
   body,changes=prepare_typography(body,excluded,apply=typography=='apply')
   for change in changes:
    automatic_count+=1
    change_id=f'typograf-{automatic_count}'
    while change_id in existing_ids:
     change_id+='-auto'
    existing_ids.add(change_id)
    preparation.append({**change,'id':change_id,'slide':sid,'actor':'typograf','kind':'typography',
                        'status':'applied' if typography=='apply' else 'pending','title':'Русская типографика'})
  authored[sid]=body
  body=local_assets(body)
  if re.search(r'<script\b|\son\w+\s*=|javascript\s*:',body,re.I):raise ValueError('Slide markup must contain content, not scripts/event handlers')
  section=html.escape(navigation[sid]['section']);topic=html.escape(navigation[sid]['topic']);header=slide.get('header','full')
  if header not in ['full','number','none']:raise ValueError('Unknown header mode')
  crumbs=(('<span>'+section+'</span>' if section else '')+('<i>·</i>' if section and topic else '')+('<span>'+topic+'</span>' if topic else '')) if header=='full' else ''
  chrome={e['role']:e for e in slide.get('sourceChrome',[])}
  def chrome_attr(role):
   entry=chrome.get(role)
   return (' data-gd-chrome-source="'+html.escape(entry['sourceId'],quote=True)+'" data-gd-chrome-role="'+role+'"') if entry else ''
  bg=slide.get('background');bg_markup=''
  if bg is not None:
   if not isinstance(bg,dict) or bg.get('type') not in ['color','gradient','image']:raise ValueError(f'Invalid background on slide {sid}')
   if bg.get('type')!='image' and 'wash' in bg:raise ValueError(f'Background wash requires image on slide {sid}')
   role=bg.get('role','decoration')
   if role not in ('decoration','content-frame') or (role=='content-frame' and bg['type']!='image'):raise ValueError(f'Invalid background role on slide {sid}')
   if bg['type']=='color':
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(bg.get('value',''))):raise ValueError(f'Invalid background color on slide {sid}')
    bg_markup=f'<div class="gd-slide-background" style="background:{bg["value"]}"></div>'
   elif bg['type']=='gradient':
    value=str(bg.get('value',''))
    if not re.fullmatch(r'(?:linear|radial)-gradient\([#a-zA-Z0-9.,%\s()-]+\)',value):raise ValueError(f'Invalid background gradient on slide {sid}')
    bg_markup=f'<div class="gd-slide-background" style="background:{html.escape(value,quote=True)}"></div>'
   else:
    wash=bg.get('wash')
    if 'wash' in bg and (role!='decoration' or not isinstance(wash,str) or not re.fullmatch(r'(?:linear|radial)-gradient\([#a-zA-Z0-9.,%\s()-]+\)',wash)):
     raise ValueError(f'Invalid image background wash on slide {sid}')
    path=str(bg.get('asset',''))
    if not path:raise ValueError(f'Image background needs asset on slide {sid}')
    if role=='content-frame':
     frame_path=(project.parent/path).resolve()
     if not frame_path.is_relative_to(project.parent.resolve()):raise ValueError('Assets must stay inside the project')
     dimensions=image_dimensions(frame_path)
     if not dimensions or not dimensions[1] or abs(dimensions[0]/dimensions[1]-16/9)>0.005:raise ValueError(f'{sid}: content-frame requires a verified 16:9 PNG, JPEG or GIF; adapt other source ratios without distortion')
    url=embed(path); focal=bg.get('focal',bg.get('position','50% 50%'));size=bg.get('size','cover')
    if not re.fullmatch(r'\d{1,3}%\s+\d{1,3}%',str(focal)) or size not in ['cover','contain','100% 100%']:raise ValueError(f'Invalid background focal/size on slide {sid}')
    frame_class=' gd-slide-background--content-frame' if role=='content-frame' else ''
    wash_attr=' data-gd-wash="1"' if wash is not None else ''
    wash_css='--gd-background-wash:'+html.escape(wash,quote=True)+';' if wash is not None else ''
    bg_markup=f'<div class="gd-slide-background{frame_class}"{wash_attr} style="background-image:url({url});background-position:{focal};background-size:{size};{wash_css}"></div>'
  if bg_markup:
   ident=bg.get('sourceId')
   if ident:bg_markup=bg_markup.replace('class="gd-slide-background','data-source-id="'+html.escape(ident,quote=True)+'" class="gd-slide-background',1)
   layers=bg.get('layers',[])
   if not isinstance(layers,list) or (layers and bg.get('role')=='content-frame'):raise ValueError('Background layers require decorative background paint')
   rendered_layers=[]
   for layer in layers:
    typ=layer.get('type');value=layer.get('value','');box=layer.get('box',[0,0,100,100])
    if typ=='color':
     if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(value)):raise ValueError('Invalid background layer color')
    elif typ=='gradient':
     if not re.fullmatch(r'(?:linear|radial)-gradient\([#a-zA-Z0-9.,%\s()-]+\)',str(value)):raise ValueError('Invalid background layer gradient')
    else:raise ValueError('Background layers support color/gradient only')
    if not isinstance(box,list) or len(box)!=4 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not 0<=x<=100 for x in box) or not box[2] or not box[3] or box[0]+box[2]>100.001 or box[1]+box[3]>100.001:raise ValueError('Invalid relative background layer box')
    attr=source_attr(layer.get('sourceId'));paint=f'position:absolute;left:{box[0]}%;top:{box[1]}%;width:{box[2]}%;height:{box[3]}%;pointer-events:none;background:{value}'
    rendered_layers.append('<div class="gd-background-layer"'+attr+' style="'+html.escape(paint,quote=True)+'"></div>')
   bg_markup=bg_markup[:-6]+''.join(rendered_layers)+'</div>'
  shell_ink=slide.get('shellInk','auto')
  if shell_ink not in ('auto','light','dark'):raise ValueError(f'Invalid shellInk on slide {sid}')
  media_frame=slide.get('mediaFrame','content')
  if media_frame not in ('content','full'):raise ValueError(f'Invalid mediaFrame on slide {sid}')
  if media_frame=='full':
   videos=re.findall(r'<video\b[^>]*>',body,re.I)
   if len(videos)!=1 or not re.search(r'\bposter\s*=',videos[0],re.I):raise ValueError(f'{sid}: full-frame media requires exactly one video with a poster')
  slides.append(f'<section class="slide" data-sk-id="{sid}" data-sk-section="{section}" data-sk-topic="{topic}" data-gd-header="{header}" data-gd-shell-ink="{shell_ink}" data-gd-media-frame="{media_frame}" data-gd-source-number="{int(slide.get("sourceNumber",0))}"><div class="gd-export-meta" data-header="{header}"><div class="gd-export-crumbs"{chrome_attr("navigation")}>{crumbs}</div><span class="slide-page"{chrome_attr("page-number")}>1</span></div><div class="slide-inner">{bg_markup}<div class="gd-content">{body}</div></div></section>')
 if deck.get('proofreadingStatus','not_checked') not in ['not_checked','reviewed','has_proposals']:raise ValueError('proofreadingStatus must be not_checked, reviewed, or has_proposals')
 seen=set()
 for item in preparation:
  if not isinstance(item,dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',str(item.get('id',''))) or item['id'] in seen:raise ValueError('Invalid/duplicate preparation change ID')
  seen.add(item['id'])
  if item.get('slide') not in records:raise ValueError('Unknown preparation slide')
  if item.get('actor') not in ['llm','typograf','user'] or item.get('kind') not in ['text','typography','layout'] or item.get('status') not in ['applied','pending','rejected']:raise ValueError('Invalid preparation actor/kind/status')
  if any(not isinstance(item.get(k),str) for k in ['title','before','after']):raise ValueError('Preparation text fields must be strings')
  if item['status']=='pending' and (not item.get('sourceId') or item['kind']=='layout' or not item['after'].strip()):raise ValueError('Pending proposal needs a sourceId and a nonempty text replacement')
  if item.get('sourceId'):
   parser=SourceTargets(str(item['sourceId']));parser.feed(authored[item['slide']]);targets=parser.matches
   if len(targets)!=1:raise ValueError(f'Preparation change {item["id"]} sourceId {item["sourceId"]!r} must target exactly one authored data-source-id on slide {item["slide"]}; found {len(targets)}')
   expected=item['after'] if item['status']=='applied' else item['before']
   if plain_markup(''.join(targets[0]['text']))!=plain_markup(expected):raise ValueError(f'Preparation change {item["id"]} sourceId text does not match expected {"after" if item["status"]=="applied" else "before"} text')
 settings={'theme':primary,'motion':deck.get('motion'),'screen':{'contrast':100,'shadows':100,'muted':0,'saturation':100}}
 restored=deck.get('restoredSettings')
 if restored is not None:
  bounds={'contrast':(80,135),'shadows':(100,160),'muted':(0,60),'saturation':(50,120)}
  if not isinstance(restored,dict) or set(restored)!={'theme','motion','screen'} or restored['theme'] not in themes or not isinstance(restored['motion'],bool) or not isinstance(restored['screen'],dict) or set(restored['screen'])!=set(bounds):raise ValueError('Invalid restoredSettings')
  if any(not isinstance(restored['screen'][k],(int,float)) or isinstance(restored['screen'][k],bool) or not bounds[k][0]<=restored['screen'][k]<=bounds[k][1] for k in bounds):raise ValueError('Invalid restoredSettings screen values')
  settings=restored

 proof_status='has_proposals' if preparation else deck.get('proofreadingStatus','not_checked')
 if not preparation and proof_status=='has_proposals':raise ValueError('proofreadingStatus has_proposals requires at least one preparation record')
 file_stem=deck.get('fileStem',re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',title))
 if not isinstance(file_stem,str) or not file_stem.strip() or re.search(r'[\\/:*?"<>|\x00-\x1f]',file_stem):raise ValueError('Invalid fileStem')
 history=deck.get('restoredHistory',[])
 if not isinstance(history,list) or any(not isinstance(item,dict) for item in history):raise ValueError('Invalid restoredHistory')
 meta={'slides':[{**{k:s[k] for k in ['id','sourceNumber','section','topic','header'] if k in s},'sourceLabel':s.get('sourceLabel',s.get('label',s.get('title','Слайд'))),'sourceTopic':s.get('sourceTopic',s.get('topic','')),'sourceSection':s.get('section',''),'section':navigation[s['id']]['baseSection'],'navigationSection':navigation[s['id']]['navigationSection'],'navigationRole':navigation[s['id']]['role'],'navigationSectionSourceId':navigation[s['id']]['sectionSourceId'],'navigationRemovedDuplicates':navigation[s['id']]['removedDuplicates'],'navigationTopic':navigation[s['id']]['baseTopic'],'label':navigation[s['id']]['baseLabel'],**navigation[s['id']]['overrides'],'sourceChrome':s.get('sourceChrome',[]),'number':i+1} for i,s in enumerate(records.values())],'order':order,'title':title,'fileStem':file_stem,'version':version,'settings':settings,'themes':themes,'primaryTheme':primary,'history':history,'preparationChanges':preparation,'proofreadingStatus':proof_status,'savedAt':0,'shellVersion':'v18.2'}
 shell=(ASSETS/'shell.html').read_text().replace('@@GD_SLIDES@@','\n'.join(slides)).replace('@@GD_TITLE@@',html.escape(title,quote=True)).replace('@@GD_VERSION@@','v'+str(version).zfill(2))
 base=':root{'+''.join(c['name']+':'+style.get('colors',DEFAULT['colors']).get(primary,DEFAULT['colors'][primary]).get(c['name'][5:],DEFAULT['colors'][primary][c['name'][5:]])+';' for c in palette)+'--gd-font:'+style.get('font',DEFAULT['font'])+';--gd-display-font:'+style.get('displayFont',style.get('font',DEFAULT['displayFont']))+';}'
 slide_css=style.get('slideCss','')
 if not isinstance(slide_css,str):raise ValueError('slideCss must be a CSS string')
 validate_scoped_css(slide_css)
 inline_css=style.get('css','')
 if not isinstance(inline_css,str):raise ValueError('Theme css must be a string')
 if isolation=='strict':validate_scoped_css(inline_css)
 css=(ASSETS/'slide-ui.css').read_text()+'\n'+((ASSETS/'compositions/compositions.css').read_text()+'\n' if any(s.get('composition') for s in records.values()) else '')+(('\n@scope (.gd-content) {\n'+inline_css+'\n}\n') if isolation=='strict' and inline_css else inline_css if isolation=='legacy' else '')+('\n@scope (.gd-content) {\n'+slide_css+'\n}\n' if slide_css else '')
 css_file=style.get('cssFile')
 if css_file:
  css_path=(theme_path.parent/css_file).resolve()
  if not css_path.is_relative_to(theme_path.parent.resolve()):raise ValueError('Theme cssFile must stay inside the theme directory')
  raw_css=css_path.read_text()
  if isolation=='strict':validate_scoped_css(raw_css)
  def css_asset(match):
   value=match.group(2).strip().strip('"\'')
   if value.startswith(('data:','#','http:','https:','//')):return match.group(0)
   asset=(css_path.parent/value.split('#',1)[0].split('?',1)[0]).resolve()
   if not asset.is_relative_to(css_path.parent.resolve()):raise ValueError('Theme CSS assets must stay inside its directory')
   encoded='data:'+(mimetypes.guess_type(asset)[0] or 'application/octet-stream')+';base64,'+base64.b64encode(asset.read_bytes()).decode()
   return 'url("'+encoded+'")'
  processed_css=re.sub(r'url\(([^)]*)\)',lambda m:css_asset(re.match(r'(url\()(.*?)(\))',m.group(0))),raw_css)
  css+=('\n@scope (.gd-content) {\n'+processed_css+'\n}\n') if isolation=='strict' else '\n'+processed_css
 if style.get('builtinFonts',True):
  supplied={(f['family'],f.get('weight',400)) for f in style.get('fonts',[])}
  for f in json.loads((ASSETS/'fonts/manifest.json').read_text())['faces']:
   if (f['family'],f['weight']) in supplied:continue
   data=base64.b64encode((ASSETS/f['path']).read_bytes()).decode()
   css+='\n@font-face{font-family:'+json.dumps(f['family'])+';font-weight:'+str(f['weight'])+';font-style:normal;font-display:swap;src:url(data:font/otf;base64,'+data+') format("opentype")}'
 for font in style.get('fonts',[]):css+='\n@font-face{font-family:'+json.dumps(font['family'])+';font-weight:'+str(font.get('weight',400))+';src:url('+embed(font['path'])+')}'
 scripts='\n'.join('<script id="'+('sk-controller' if n=='controller' else 'gd-'+n)+'">'+(ASSETS/(n+'.js')).read_text()+'</script>' for n in ['navigation','editor','flow','controller','journal','motion','adapter','tooltips','media','slide-ui','screen-content'])
 if len(themes)<2:shell=shell.replace('id="sk-theme"','id="sk-theme" hidden')
 output='<!doctype html><html lang="ru" data-gd-maker="1" data-sk-doc="gd-'+uuid.uuid4().hex+'" data-sk-theme="'+primary+'" data-sk-motion="on"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · v'+str(version).zfill(2)+'</title><style id="sk-ui-styles">'+(ASSETS/'ui.css').read_text()+'</style><style id="gd-deck-styles">'+(ASSETS/'deck.css').read_text()+'</style><style id="gd-style-pack">'+base+'\n'+css+'</style><style id="sk-colors"></style><script type="application/json" id="sk-color-registry">'+safe_json(palette)+'</script><script type="application/json" id="sk-deck-state">'+safe_json(meta)+'</script></head><body>'+shell+scripts+'</body></html>'
 out.parent.mkdir(parents=True,exist_ok=True)
 made_media=False
 try:
  if external_files:
   external_dir.mkdir(exist_ok=False);made_media=True
   for source,name in external_files.items():shutil.copy2(source,external_dir/name)
   manifest={'type':'offline-media-package','files':[{'path':name,'sha256':name.split('.')[0],'bytes':source.stat().st_size} for source,name in external_files.items()]}
   (external_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
  with out.open('x') as file:file.write(output)
 except Exception:
  if made_media:shutil.rmtree(external_dir)
  raise
 print(json.dumps({'status':'built','html':str(out.resolve()),'deliveryType':'offline-media-package' if external_files else 'standalone-html','mediaDirectory':str(external_dir.resolve()) if external_files else None,'slides':len(order),'available':len(records),'themes':themes,'bytes':out.stat().st_size,'visualApproval':False},ensure_ascii=False))
 return output
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('out');p.add_argument('--theme')
 p.add_argument('--typography',choices=['off','review','apply'],default='apply',help='safe Russian typography: apply by default; use review for exact-copy tasks or off to disable')
 p.add_argument('--final',action='store_true',help='reject assembly drafts and require a complete composition plan; visual review remains required')
 p.add_argument('--composition-plan',help='path to composition plan JSON')
 p.add_argument('--external-media',action='store_true',help='ship audio/video alongside HTML in a manifest-verified folder')
 a=p.parse_args();build(a.project,a.out,a.theme,a.typography,a.final,a.composition_plan,a.external_media)
