"""Conservative PPTX paragraph and Latin run-style inheritance with provenance.

Not a renderer. Unsupported placeholder matches and missing inheritance remain unresolved.
"""
from xml.etree import ElementTree as ET
P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
N={'p':P,'a':A}


def related(rels,kind,names):
 return next((v['target'] for v in rels.values() if v['type']==kind and not v['external'] and v['target'] in names),None)


def placeholder(shape):
 ph=shape.find('./p:nvSpPr/p:nvPr/p:ph',N)
 return None if ph is None else {'idx':ph.get('idx','0'),'type':ph.get('type','obj')}


def match_placeholder(tree,ref,allow_type=False):
 if tree is None or ref is None:return None
 shapes=[s for s in tree.findall('.//p:sp',N) if placeholder(s) is not None]
 exact=[s for s in shapes if placeholder(s)['idx']==ref['idx']]
 if len(exact)==1:
  candidate=placeholder(exact[0])
  if candidate['type']==ref['type'] or 'obj' in (candidate['type'],ref['type']):return exact[0]
 # Type fallback is appropriate for master, never a substitute for a missing layout index.
 typed=[s for s in shapes if placeholder(s)['type']==ref['type']] if allow_type else []
 return typed[0] if len(typed)==1 else None


def build_context(z, slide_rels, rels, presentation):
 names=set(z.namelist()); layout=related(slide_rels,'slideLayout',names)
 master=related(rels(layout),'slideMaster',names) if layout else None
 theme=related(rels(master),'theme',names) if master else None
 def read(part):return ET.fromstring(z.read(part)) if part else None
 themes={}; tt=read(theme)
 if tt is not None:
  for group,code in [('majorFont','mj'),('minorFont','mn')]:
   for name,suffix in [('latin','lt'),('ea','ea'),('cs','cs')]:
    e=tt.find(f'.//a:fontScheme/a:{group}/a:{name}',N)
    if e is not None and e.get('typeface'):themes['+'+code+'-'+suffix]=e.get('typeface')
 return {'layout':read(layout),'layoutPart':layout,'master':read(master),'masterPart':master,
         'themePart':theme,'theme':tt,'themeTokens':themes,'presentation':presentation,
         'themeOverride':any(v['type']=='themeOverride' for v in slide_rels.values()) or any(v['type']=='themeOverride' for part in (layout,master) if part for v in rels(part).values())}


def props(shape,level):
 if shape is None:return []
 result=[]
 paragraphs=shape.findall('p:txBody/a:p',N)
 # A sole placeholder paragraph is usable as a default; multiple paragraphs are ambiguous.
 p=paragraphs[0].find('a:pPr',N) if len(paragraphs)==1 else None
 if p is not None and int(p.get('lvl','0'))==level:result.append(p)
 ls=shape.find(f'p:txBody/a:lstStyle/a:lvl{level+1}pPr',N)
 if ls is not None:result.append(ls)
 return result


def styles(context,shape,ppr,level):
 result=[]
 if ppr is not None:result.append(('slide.paragraph',ppr))
 own=shape.find(f'p:txBody/a:lstStyle/a:lvl{level+1}pPr',N)
 if own is not None:result.append(('slide.textBody',own))
 ref=placeholder(shape)
 if ref is not None:
  lay=match_placeholder(context['layout'],ref)
  for node in props(lay,level):result.append(('layout.placeholder',node))
  masterref=placeholder(lay) if lay is not None else (ref if context['layout'] is None else None)
  mas=match_placeholder(context['master'],masterref,allow_type=True)
  for node in props(mas,level):result.append(('master.placeholder',node))
  kind=ref['type'];style='titleStyle' if kind in ('title','ctrTitle') else 'bodyStyle' if kind in ('body','subTitle','obj') else 'otherStyle'
  if context['master'] is not None:
   node=context['master'].find(f'p:txStyles/p:{style}/a:lvl{level+1}pPr',N)
   if node is not None:result.append(('master.'+style,node))
 # Non-placeholder shapes do not necessarily inherit master placeholder styles.
 if context['presentation'] is not None:
  node=context['presentation'].find(f'p:defaultTextStyle/a:lvl{level+1}pPr',N)
  if node is not None:result.append(('presentation.defaultTextStyle',node))
 return result


def list_chain(context, shape, chain, level):
 """Add list-only defPPr evidence without changing run-style inheritance."""
 if placeholder(shape) is not None or level != 0:return chain
 own=shape.find('p:txBody/a:lstStyle/a:defPPr',N)
 default=context['presentation'].find('p:defaultTextStyle/a:defPPr',N) if context.get('presentation') is not None else None
 result=[]; own_added=False
 for source,node in chain:
  if not source.startswith('slide.') and not own_added:
   if own is not None:result.append(('slide.textBody.default',own))
   own_added=True
  result.append((source,node))
 if not own_added and own is not None:result.append(('slide.textBody.default',own))
 if default is not None:result.append(('presentation.defaultTextStyle.default',default))
 return result


def infer_plain_text_default(context,shape,level):
 """Bounded inference for complete, ordinary text shapes, not placeholders/tables.

 A theme object default with an explicit bullet or extension is left unresolved:
 its full inheritance and theme overrides are outside this resolver's scope.
 """
 if shape.tag!='{'+P+'}sp' or placeholder(shape) is not None or level != 0:return False
 if any(context.get(k) is None for k in ('layout','master','theme','presentation')) or context.get('themeOverride',True):return False
 defaults=context['theme'].find('a:objectDefaults',N)
 if defaults is not None:
  for element in defaults.iter():
   if element.tag.rsplit('}',1)[-1] in ('buNone','buChar','buAutoNum','buBlip','extLst'):return False
 return True

def resolve_list(chain,level,default_none=False):
 for source,node in chain:
  for e in node:
   name=e.tag.rsplit('}',1)[-1]
   if name in ('buNone','buChar','buAutoNum','buBlip'):
    kind={'buNone':'none','buChar':'ul','buAutoNum':'ol','buBlip':'ul'}[name]
    return {'kind':kind,'level':level,'source':source,'bulletType':name,'attributes':dict(e.attrib),'status':'resolved'}
 if default_none:return {'kind':'none','level':level,'source':'inferred.terminalDefault','status':'resolved','inferred':True}
 return {'kind':'unresolved','level':level,'source':None,'status':'unresolved'}


def resolve_run(chain,rpr,tokens):
 defaults=[]
 if rpr is not None:defaults.append(('slide.run',rpr))
 for source,p in chain:
  node=p.find('a:defRPr',N)
  if node is not None:defaults.append((source+'.defRPr',node))
 out={}
 for key,attribute,convert in [('sizePt','sz',lambda v:float(v)/100),('bold','b',lambda v:v in ('1','true')),('italic','i',lambda v:v in ('1','true'))]:
  for source,node in defaults:
   if node.get(attribute) is not None:
    try:out[key]={'value':convert(node.get(attribute)),'source':source};break
    except ValueError:pass
 for source,node in defaults:
  font=node.find('a:latin',N)
  if font is not None and font.get('typeface'):
   value=font.get('typeface');resolved=tokens.get(value) if value.startswith('+') else value
   out['latin']={'declared':value,'family':resolved,'source':source,'themeTokenResolved':not value.startswith('+') or resolved is not None};break
 return {'properties':out,'status':'partial' if not all(k in out for k in ('sizePt','latin','bold','italic')) or not out.get('latin',{}).get('family') else 'resolved',
         'limitations':['Latin typeface only; script-specific substitutions and actual rendered glyphs require review.']}
