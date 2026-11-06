"""Resolve a narrow source-shape appearance for independent DOM comparison.

Unknown inheritance, gradients, transforms and effects raise ValueError. A
resolved record is not itself visual approval or permission to omit text.
"""
import colorsys, posixpath, re
from xml.etree import ElementTree as ET
from source_dispositions import A, NS

def need(ok,msg):
 if not ok:raise ValueError(msg)
def local(e):return e.tag.rsplit('}',1)[-1]
def related(z,part,kind):
 rp=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
 root=ET.fromstring(z.read(rp)); hits=[x for x in root if x.get('Type','').endswith('/'+kind) and x.get('TargetMode')!='External']
 need(len(hits)==1,'shape theme relationship unresolved: '+kind)
 target=hits[0].get('Target','');return target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part),target))

def appearance(verifier,part,shape,system_color_policy=None):
 z=verifier.zip;layout=related(z,part,'slideLayout');master=related(z,layout,'slideMaster');theme=related(z,master,'theme')
 slide=ET.fromstring(z.read(part));layout_xml=ET.fromstring(z.read(layout));master_xml=ET.fromstring(z.read(master));theme_xml=ET.fromstring(z.read(theme))
 for tree in (slide,layout_xml):
  override=tree.find('p:clrMapOvr',NS)
  need(override is None or (len(override)==1 and local(override[0])=='masterClrMapping'),'color-map override unsupported')
 cmap=master_xml.find('p:clrMap',NS);need(cmap is not None,'master color map missing')
 scheme=theme_xml.find('.//a:clrScheme',NS);fmt=theme_xml.find('.//a:fmtScheme',NS);need(scheme is not None and fmt is not None,'theme format scheme missing')
 system_colors=[]
 def color(node,placeholder=None):
  tag=local(node);val=node.get('val')
  if tag=='schemeClr':
   if val=='phClr':need(placeholder is not None,'placeholder color missing');rgb,alpha=placeholder
   else:
    entry=scheme.find('a:'+cmap.get(val,val),NS);need(entry is not None and len(entry)==1,'scheme color unresolved: '+str(val));base=entry[0]
    typ=local(base);need(len(base)==0,'theme color transforms unsupported')
    if typ=='sysClr':
     need(system_color_policy=='lastClr','system color requires explicit lastClr static contract');hexval=base.get('lastClr');system_colors.append({'system':base.get('val'),'lastClr':hexval,'policy':'lastClr'})
    else:need(typ=='srgbClr','theme color type unsupported');hexval=base.get('val')
    need(re.fullmatch('[0-9a-fA-F]{6}',hexval or '') is not None,'theme RGB unavailable');rgb=tuple(int(hexval[i:i+2],16)/255 for i in (0,2,4));alpha=1.
  elif tag=='srgbClr':
   need(re.fullmatch('[0-9a-fA-F]{6}',val or '') is not None,'invalid RGB');rgb=tuple(int(val[i:i+2],16)/255 for i in (0,2,4));alpha=1.
  else:raise ValueError('color type unsupported: '+tag)
  for transform in node:
   typ=local(transform);need(typ in ('lumMod','lumOff','alpha','shade'),'color transform unsupported: '+typ)
   try:f=int(transform.get('val'))/100000
   except (ValueError,TypeError):raise ValueError('invalid color transform')
   if typ=='alpha':need(0<=f<=1,'invalid alpha');alpha=f
   elif typ=='shade':need(0<=f<=1,'invalid shade');rgb=tuple(x*f for x in rgb)
   else:
    h,l,s=colorsys.rgb_to_hls(*rgb);l=max(0,min(1,l*f if typ=='lumMod' else l+f));rgb=colorsys.hls_to_rgb(h,l,s)
  return rgb,alpha
 def rgba(c):
  rgb,alpha=c;return [round(v*255) for v in rgb]+[round(alpha,5)]
 style=shape.find('p:style',NS);sp=shape.find('p:spPr',NS);unlinked=style is None
 need(sp is not None and shape.find('p:nvSpPr/p:nvPr/p:ph',NS) is None,'shape style/placeholder unresolved')
 if unlinked:
  # Unstyled, ungrouped text boxes have no shape style link or placeholder
  # master shape. Only the observed explicit noFill + empty line is covered:
  # MS-OI29500 20.1.8 default fill is noFill, also for an empty line's fill.
  nv=shape.find('p:nvSpPr/p:cNvSpPr',NS);line=sp.find('a:ln',NS)
  need(nv is not None and nv.get('txBox') in ('1','true') and sp.find('a:noFill',NS) is not None and line is not None and len(line)==0 and not line.attrib,'unstyled shape line/fill unresolved')
 need(all(local(x) in ('xfrm','prstGeom','noFill','solidFill','ln') for x in sp),'unsupported shape property')
 need(not any(sp.findall('.//a:'+x,NS) for x in ('effectLst','effectDag','scene3d','sp3d')),'explicit shape effect unresolved')
 ef=style.find('a:effectRef',NS) if style is not None else None
 if unlinked:ei=0
 else:
  need(ef is not None,'effect reference missing')
  try:ei=int(ef.get('idx'))
  except (TypeError,ValueError):raise ValueError('effect reference invalid')
 if ei:
  effects=fmt.find('a:effectStyleLst',NS);need(effects is not None and 1<=ei<=len(effects),'effect reference outside theme')
  effect=effects[ei-1];lst=effect.find('a:effectLst',NS);need(lst is not None and len(lst)==0 and len(effect)==1,'theme effect unsupported')
 fill_nodes=[x for x in sp if local(x) in ('noFill','solidFill','gradFill','pattFill','blipFill','grpFill')];need(len(fill_nodes)<=1,'ambiguous shape fill')
 fill=fill_nodes[0] if fill_nodes else None
 if fill is None:
  ref=style.find('a:fillRef',NS);need(ref is not None and len(ref)==1,'fill reference unresolved')
  idx=int(ref.get('idx','-1'));lst=fmt.find('a:fillStyleLst',NS);need(lst is not None and 1<=idx<=len(lst),'fill reference unsupported')
  fill=lst[idx-1];placeholder=color(ref[0])
 else:placeholder=None
 need(local(fill) in ('solidFill','noFill'),'shape fill unsupported: '+local(fill))
 fill_value=None if local(fill)=='noFill' else rgba(color(fill[0],placeholder)) if len(fill)==1 else None
 need(local(fill)=='noFill' or fill_value is not None,'shape solid fill invalid')
 line=sp.find('a:ln',NS);line_value=None
 if unlinked or (line is not None and len(line)==1 and local(line[0])=='noFill'):line_value='none'
 else:
  # Resolve only the common simple solid theme line. An absent/empty local
  # line inherits its properties; a local solid color may replace the color.
  ref=style.find('a:lnRef',NS);need(ref is not None and len(ref)==1,'line reference unresolved')
  try:li=int(ref.get('idx'))
  except (TypeError,ValueError):raise ValueError('line reference invalid')
  lines=fmt.find('a:lnStyleLst',NS);need(lines is not None and 1<=li<=len(lines),'line reference outside theme')
  themed=lines[li-1];need(local(themed)=='ln' and all(local(x) in ('solidFill','prstDash','miter') for x in themed),'theme line unsupported')
  need(themed.get('cap','flat')=='flat' and themed.get('cmpd','sng')=='sng' and themed.get('algn','ctr')=='ctr','theme line geometry unsupported')
  dash=themed.find('a:prstDash',NS);need(dash is None or dash.get('val')=='solid','theme dash unsupported')
  if line is not None:
   need(set(line.attrib)<=set(('w','cap','cmpd','algn')) and all(local(x)=='solidFill' for x in line),'local line overrides unsupported')
   need(line.get('cap','flat')=='flat' and line.get('cmpd','sng')=='sng' and line.get('algn','ctr')=='ctr','local line geometry unsupported')
  fill_line=line.find('a:solidFill',NS) if line is not None else None
  if fill_line is None:fill_line=themed.find('a:solidFill',NS)
  need(fill_line is not None and len(fill_line)==1,'line fill unresolved')
  try:width=int(line.get('w',themed.get('w','')) if line is not None else themed.get('w',''))
  except ValueError:raise ValueError('line width unresolved')
  need(width>0,'line width invalid');line_value={'rgba':rgba(color(fill_line[0],color(ref[0]))),'widthEMU':width}
 xf=sp.find('a:xfrm',NS);need(xf is not None and xf.get('rot','0')=='0' and xf.get('flipH','0') in ('0','false') and xf.get('flipV','0') in ('0','false'),'shape transform unsupported')
 need(set(xf.attrib)<=set(('rot','flipH','flipV')) and len(xf)==2 and all(local(x) in ('off','ext') for x in xf),'shape transform components unsupported')
 off=xf.find('a:off',NS);ext=xf.find('a:ext',NS);need(off is not None and ext is not None,'shape geometry missing')
 try:box={'x':int(off.get('x')),'y':int(off.get('y')),'width':int(ext.get('cx')),'height':int(ext.get('cy'))}
 except (TypeError,ValueError):raise ValueError('shape geometry invalid')
 need(box['width']>0 and box['height']>0,'shape geometry empty')
 geom=sp.find('a:prstGeom',NS);need(geom is not None and geom.get('prst') in ('rect','roundRect'),'shape preset unsupported')
 radius=0.
 if geom.get('prst')=='roundRect':
  gd=geom.findall('a:avLst/a:gd',NS);need(len(gd)==1 and gd[0].get('name')=='adj' and re.fullmatch(r'val \d+',gd[0].get('fmla','')),'roundRect adjustment unresolved')
  adj=int(gd[0].get('fmla').split()[1]);need(0<=adj<=50000,'roundRect adjustment invalid');radius=min(box['width'],box['height'])*adj/100000
 return {'part':part,'themePart':theme,'geometryEMU':box,'canvasEMU':verifier.canvas,'preset':geom.get('prst'),'cornerRadiusEMU':radius,'fillRGBA':fill_value,'line':line_value,'effects':'none','basis':'unstyled-textbox-explicit-nofill-default-line' if unlinked else 'explicit-fill-and-line' if placeholder is None else 'theme-fill-reference-and-explicit-line','systemColors':system_colors,'limitation':'DOM comparison and visual source review remain required; alpha/runs checked separately. lastClr is a fallback, not a resolved operating-system color.'}
