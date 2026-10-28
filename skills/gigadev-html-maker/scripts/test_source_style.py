"""Focused style evidence and gate regression with a tiny PPTX fixture."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json, re
from extract_pptx import extract
from source_style import check

def run():
 with TemporaryDirectory() as tmp:
  r=Path(tmp); ppt=r/'test.pptx'; a='http://schemas.openxmlformats.org/drawingml/2006/main';p='http://schemas.openxmlformats.org/presentationml/2006/main'; rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'; svg='http://schemas.microsoft.com/office/drawing/2016/SVG/main'
  with ZipFile(ppt,'w') as z:
   z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{p}" xmlns:r="{rel}"><p:sldIdLst><p:sldId r:id="s"/></p:sldIdLst><p:sldSz cx="100" cy="100"/></p:presentation>')
   z.writestr('ppt/_rels/presentation.xml.rels','<Relationships><Relationship Id="s" Target="slides/slide1.xml" Type="x/slide"/></Relationships>')
   z.writestr('ppt/slides/slide1.xml',f'<p:sld xmlns:p="{p}" xmlns:a="{a}" xmlns:r="{rel}" xmlns:asvg="{svg}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="Shape"/></p:nvSpPr><p:spPr><a:solidFill><a:srgbClr val="123456"/></a:solidFill></p:spPr><p:txBody><a:p><a:r><a:rPr><a:solidFill><a:schemeClr val="accent1"/></a:solidFill><a:latin typeface="Example"/></a:rPr><a:t>Text</a:t></a:r></a:p></p:txBody></p:sp><p:pic><p:nvPicPr><p:cNvPr id="3" name="Icon"/></p:nvPicPr><p:blipFill><a:blip r:embed="png"><a:extLst><a:ext><asvg:svgBlip r:embed="svg"/></a:ext></a:extLst></a:blip></p:blipFill></p:pic></p:spTree></p:cSld></p:sld>')
   z.writestr('ppt/slides/_rels/slide1.xml.rels','<Relationships><Relationship Id="png" Target="../media/icon.png" Type="x/image"/><Relationship Id="svg" Target="../media/icon.svg" Type="x/image"/><Relationship Id="l" Target="../slideLayouts/slideLayout1.xml" Type="x/slideLayout"/></Relationships>')
   z.writestr('ppt/media/icon.png',b'PNG');z.writestr('ppt/media/icon.svg','<svg xmlns="http://www.w3.org/2000/svg"/>')
   z.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels','<Relationships><Relationship Id="m" Target="../slideMasters/slideMaster1.xml" Type="x/slideMaster"/></Relationships>');z.writestr('ppt/slideLayouts/slideLayout1.xml','<x/>')
   z.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels','<Relationships><Relationship Id="t" Target="../theme/theme1.xml" Type="x/theme"/></Relationships>');z.writestr('ppt/slideMasters/slideMaster1.xml','<x/>')
   z.writestr('ppt/theme/theme1.xml',f'<a:theme xmlns:a="{a}"><a:themeElements><a:clrScheme><a:accent1><a:srgbClr val="0055AA"/></a:accent1></a:clrScheme></a:themeElements></a:theme>')
  extract(ppt,r/'project'); inv=json.loads((r/'project/style-inventory.json').read_text()); assert any(c['resolvedBase']=='#0055AA' and c['role']=='text' for c in inv['colors']);assert any(c['resolvedBase']=='#123456' for c in inv['colors']);assert inv['fonts'][0]['typeface']=='Example';g=inv['graphics'][0];assert g['id']=='s1-o3' and g['asset'].endswith('.svg')
  h=r/'out.html';h.write_text(f'<style>:root{{--brand:#0055aa}} p{{color:var(--brand)}}</style><img src="{g["asset"]}">');e=next(c for c in inv['colors'] if c['role']=='text'); f=next(c for c in inv['colors'] if c['role']=='fill'); h.write_text(f'<style>:root{{--brand:#0055aa;--fill:#123456}} p{{color:var(--brand);background:var(--fill)}}</style><img src="{g["asset"]}">'); d={'mode':'improve-layout','palette':[{'role':'text','sourceEvidence':e['id'],'target':'--brand','targetColor':'#0055AA','decision':'retained'},{'role':'fill','sourceEvidence':f['id'],'target':'--fill','targetColor':'#123456','decision':'retained'}],'graphics':[{'sourceId':g['id'],'disposition':'retained','target':g['asset'],'reason':'Source illustration'}]};m=r/'decisions.json';m.write_text(json.dumps(d));assert check(r/'project',m,h)['status']=='pass'
  d['graphics'][0].update(disposition='omitted',target='',reason='decorative');m.write_text(json.dumps(d));assert check(r/'project',m,h)['status']=='fail'
  d['mode']='change-style';d['changeStyleAuthorization']='User explicitly requested new style';m.write_text(json.dumps(d));assert check(r/'project',m,h)['status']=='pass'
  h.write_text('<style>:root{--brand:#0055aa}</style>');assert check(r/'project',m,h)['status']=='fail'
  # A real second PPTX has one full-canvas cover and 17 separate SVG instances.
  ppt_many=r/'many.pptx'
  with ZipFile(ppt) as src, ZipFile(ppt_many,'w') as dst:
   for name in src.namelist():
    data=src.read(name)
    if name=='ppt/slides/slide1.xml':
     xml=data.decode(); pic=re.search(r'<p:pic>.*?</p:pic>',xml).group(); cover=pic.replace('id=\"3\"','id=\"30\"').replace('</p:pic>','<p:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"100\" cy=\"100\"/></a:xfrm></p:spPr></p:pic>'); icons=''.join(pic.replace('id=\"3\"',f'id=\"{i+3}\"') for i in range(17)); data=xml.replace(pic,cover+icons).encode()
    dst.writestr(name,data)
  extract(ppt_many,r/'many'); inv2=json.loads((r/'many/style-inventory.json').read_text()); cover=next(x for x in inv2['graphics'] if x['backgroundCandidate']); icons=[x for x in inv2['graphics'] if not x['backgroundCandidate']];assert len(icons)==17
  h.write_text('<style>:root{--brand:#0055aa;--fill:#123456} p{color:var(--brand);background:var(--fill)}</style><img src=\"cover\">'); d['mode']='improve-layout';d['graphics']=[{'sourceId':cover['id'],'disposition':'retained','target':'cover','reason':'cover'}]+[{'sourceId':x['id'],'disposition':'omitted','target':'','reason':'decorative'} for x in icons]; m.write_text(json.dumps(d)); result=check(r/'many',m,h);assert result['status']=='fail' and result['graphicsSummary']['nonBackgroundCounts']['omitted']==17 and result['warnings']
  # White alone cannot cover text and fill or preserve the source chromatic palette.
  d['palette']=[{'role':'text','sourceEvidence':e['id'],'target':'--brand','targetColor':'#FFFFFF','decision':'replaced','reason':'new color'}];m.write_text(json.dumps(d));result=check(r/'many',m,h);assert any('missing palette mapping' in x for x in result['errors']) and any('no chromatic' in x for x in result['errors'])
 print('PASS theme, explicit color, SVG instance, pass/fail decisions and unused token')
if __name__=='__main__':run()
