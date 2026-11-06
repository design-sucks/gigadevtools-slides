"""Conservative shape inheritance and color resolution regressions."""
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import copy
from source_shape import appearance

A='http://schemas.openxmlformats.org/drawingml/2006/main';P='http://schemas.openxmlformats.org/presentationml/2006/main';N={'a':A,'p':P}
def xml(s):return ET.fromstring(s)
def make(shape_xml,*,extra_theme='',extra_master=''):
 data=BytesIO()
 with ZipFile(data,'w') as z:
  z.writestr('ppt/slides/slide1.xml',f'<p:sld xmlns:p="{P}" xmlns:a="{A}"/>')
  z.writestr('ppt/slides/_rels/slide1.xml.rels','<Relationships><Relationship Type="x/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>')
  z.writestr('ppt/slideLayouts/slideLayout1.xml',f'<p:sldLayout xmlns:p="{P}"/>')
  z.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels','<Relationships><Relationship Type="x/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>')
  z.writestr('ppt/slideMasters/slideMaster1.xml',f'<p:sldMaster xmlns:p="{P}"><p:clrMap bg1="lt1"/>{extra_master}</p:sldMaster>')
  z.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels','<Relationships><Relationship Type="x/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Type="x/theme" Target="../theme/theme1.xml"/></Relationships>')
  z.writestr('ppt/theme/theme1.xml',f'<a:theme xmlns:a="{A}"><a:themeElements><a:clrScheme><a:lt1><a:srgbClr val="0C0D10"/></a:lt1></a:clrScheme><a:fmtScheme><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst><a:outerShdw/></a:effectLst></a:effectStyle></a:effectStyleLst>{extra_theme}</a:fmtScheme></a:themeElements></a:theme>')
 data.seek(0)
 class V:pass
 v=V();v.zip=ZipFile(data);v.canvas={'width':192000,'height':108000};return v,xml(shape_xml)

shape=f'''<p:sp xmlns:p="{P}" xmlns:a="{A}"><p:nvSpPr><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="100" y="200"/><a:ext cx="4000" cy="6000"/></a:xfrm><a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 5000"/></a:avLst></a:prstGeom><a:solidFill><a:schemeClr val="bg1"><a:lumMod val="25000"/><a:lumOff val="75000"/><a:alpha val="13000"/></a:schemeClr></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr><p:style><a:lnRef idx="1"><a:schemeClr val="bg1"><a:shade val="50000"/></a:schemeClr></a:lnRef><a:fillRef idx="1"><a:schemeClr val="bg1"/></a:fillRef><a:effectRef idx="0"/></p:style></p:sp>'''
v,s=make(shape);r=appearance(v,'ppt/slides/slide1.xml',s);assert r['fillRGBA']==[186,190,203,.13] and r['cornerRadiusEMU']==200 and r['line']=='none';v.zip.close()
def rejected(variant):
 v,s=make(variant)
 try:appearance(v,'ppt/slides/slide1.xml',s)
 except ValueError:pass
 else:raise AssertionError('unsupported shape accepted')
 finally:v.zip.close()
for bad in [shape.replace('<a:noFill/>','<a:gradFill/>'),shape.replace('<a:effectRef idx="0"/>','<a:effectRef idx="2"/>'),shape.replace('lumOff','satMod'),shape.replace('roundRect','ellipse'),shape.replace('val 5000','val 90000'),shape.replace('<a:ln>','<a:effectLst/><a:ln>'),shape.replace('bg1','unknown')]:rejected(bad)
v,s=make(shape.replace('<a:ln><a:noFill/></a:ln>','<a:ln/>'));r=appearance(v,'ppt/slides/slide1.xml',s);assert r['line']=={'rgba':[6,6,8,1], 'widthEMU':12700};v.zip.close()
unstyled=shape.replace('<p:nvPr/>','<p:cNvSpPr txBox="1"/><p:nvPr/>').replace('<a:solidFill><a:schemeClr val="bg1"><a:lumMod val="25000"/><a:lumOff val="75000"/><a:alpha val="13000"/></a:schemeClr></a:solidFill>','<a:noFill/>').replace('<a:ln><a:noFill/></a:ln>','<a:ln/>');unstyled=unstyled[:unstyled.index('<p:style>')]+'</p:sp>'
v,s=make(unstyled);r=appearance(v,'ppt/slides/slide1.xml',s);assert r['fillRGBA'] is None and r['line']=='none' and r['basis'].startswith('unstyled-textbox');v.zip.close()
for bad in [unstyled.replace('txBox="1"','txBox="0"'),unstyled.replace('<a:ln/>','<a:ln w="12700"/>'),unstyled.replace('<a:noFill/>','<a:solidFill/>'),unstyled.replace('<p:nvPr/>','<p:nvPr><p:ph/></p:nvPr>')]:rejected(bad)
# A missing direct fill may use a validated theme solid fill + phClr.
ref=shape.replace('<a:solidFill><a:schemeClr val="bg1"><a:lumMod val="25000"/><a:lumOff val="75000"/><a:alpha val="13000"/></a:schemeClr></a:solidFill>','')
v,s=make(ref);r=appearance(v,'ppt/slides/slide1.xml',s);assert r['fillRGBA']==[12,13,16,1] and r['basis'].startswith('theme-fill');v.zip.close()
print('PASS source shape: direct/theme fill, luminance and alpha; unsupported line/effect/color/geometry negatives')
